#!/usr/bin/env python3
"""Bounded MicroStrategy evidence; passive originals and separately granted POSTs.

No login, source authoring, arbitrary scripts, changesets, schema reload or
native target writes. Local pins establish continuity, never authenticity.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import copy
import csv
from datetime import datetime, timezone
import fcntl
import importlib.util
import io
import os
from pathlib import Path
import re
import stat
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import unicodedata
import zipfile


def module(name):
    if name not in ('powerbi_capture_files', 'bounded_csv', 'microstrategy_visual'):
        raise ValueError('microstrategy.module_rejected')
    path = Path(__file__).with_name(name + '.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('microstrategy.module_symlink')
    spec = importlib.util.spec_from_file_location('microstrategy_' + name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


F = module('powerbi_capture_files')
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST = REQUEST_SCHEMA = 'microstrategy-visual-capture-request.v1'
SCHEMA = ENVELOPE = 'microstrategy-visual-capture.v1'
MAX_JOURNAL_BYTES = 128000000
BASE_GAPS = ['source_identity_and_authority_references_not_authenticated',
    'independent_inventory_is_declared_scope_not_tenant_completeness',
    'requested_state_is_not_observed_state', 'effective_access_not_verified',
    'native_rendering_and_business_acceptance_not_assessed',
    'connected_enrichment_does_not_replace_imported_snapshot',
    'rendered_pixels_are_not_numerical_completeness', 'owned_instances_require_expiry_reconciliation_no_cleanup_route_qualified']


def text(value, maximum=1000):
    return type(value) is str and 0 < len(value) <= maximum and all(32 <= ord(c) != 127 for c in value)


def local_id(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value) is not None


def digest(value):
    return type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def native_id(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,200}', value) is not None


def utcnow():
    return datetime.now(timezone.utc).timestamp()


def origin(value):
    need(text(value, 2048), 'microstrategy.origin')
    p = urlsplit(value)
    need(p.scheme == 'https' and p.hostname and p.netloc == p.hostname and not p.path and not p.query
         and not p.fragment and not p.username and not p.password
         and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', p.hostname), 'microstrategy.https_origin_required')
    return value


def screen_text(value):
    F.safe_text(value.encode('utf-8'))
    names = r'(?:password|passwd|pwd|access[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?key|private[_-]?key|x-mstr-authtoken|jsessionid|isession)'
    need(not re.search(r'(?i)[\"\']?\b' + names + r'\b[\"\']?\s*[=:]\s*[\"\']?[^\s,;\"\'}<>]+', value)
         and not re.search(r'(?is)<\s*' + names + r'\b[^>]*>\s*[^<\s]+', value)
         and not re.search(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{12,}', value),
         'microstrategy.credential_bearing_text')


def screen_bytes(raw, granted=None):
    if granted:
        # Screen both full Authorization header value and its bearer credential.
        parts = [granted] + ([granted[7:]] if granted.startswith('Bearer ') else [])
        for part in parts:
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                need(part.encode(encoding) not in raw, 'microstrategy.credential_echo_rejected')
    encodings = ['utf-16'] if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else ['utf-8-sig', 'windows-1252']
    for encoding in encodings:
        try:
            value = raw.decode(encoding)
        except UnicodeError:
            continue
        screen_text(value)
        return 'recognized_text_patterns_only'
    return 'unknown_encoding_not_assessed'


def screen_opaque(raw):
    """Screen recognizable text without claiming arbitrary binary is safe."""
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return screen_bytes(raw)
    try:
        value = raw.decode('utf-8-sig')
    except UnicodeError:
        return 'opaque_bytes_not_assessed'
    if '\x00' in value or any(ord(c) < 32 and c not in '\r\n\t' for c in value):
        return 'opaque_bytes_not_assessed'
    screen_text(value)
    return 'recognized_text_patterns_only'


PROFILE = 'strategy-rest-selected-instance-v1-20261028'
FILTER_STAGES = ('report', 'chapter', 'view', 'metric_limit')
OP_KINDS = {'definition', 'create_instance', 'prompts', 'prompt_answers', 'selectors', 'state_readback', 'data', 'pdf'}


def guid(value):
    return type(value) is str and re.fullmatch(r'[A-Fa-f0-9]{32}', value) is not None


def validate_identity(value):
    keys = {'source_origin', 'context_path', 'project_id', 'principal_ref', 'library_version',
            'intelligence_server_version', 'model_generation', 'delivery_context', 'reference'}
    need(type(value) is dict and set(value) == keys and all(text(v) for v in value.values())
         and guid(value['project_id']) and value['model_generation'] in ('classic', 'mosaic')
         and value['delivery_context'] in ('library', 'embedded'), 'microstrategy.identity')
    origin(value['source_origin'])
    need(re.fullmatch(r'/[A-Za-z][A-Za-z0-9_-]{0,99}', value['context_path']) is not None,
         'microstrategy.context_path')


def validate_state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'timezone', 'locale', 'principal', 'cache', 'reference'}
         and type(value['filters']) is dict and set(value['filters']) == set(FILTER_STAGES)
         and all(type(v) is list and len(v) <= 100 for v in value['filters'].values())
         and type(value['parameters']) is dict and set(value['parameters']) == {'prompts'}
         and type(value['parameters']['prompts']) is list and len(value['parameters']['prompts']) <= 100
         and text(value['reference']), 'microstrategy.state_contract')
    seen = set()
    for prompt in value['parameters']['prompts']:
        need(type(prompt) is dict and set(prompt) == {'key', 'id', 'answer_mode', 'value'}
             and text(prompt['key']) and prompt['key'] not in seen and guid(prompt['id'])
             and prompt['answer_mode'] in ('explicit', 'default', 'empty', 'all', 'omitted', 'unresolved'),
             'microstrategy.prompt_state')
        seen.add(prompt['key'])
        if prompt['answer_mode'] in ('empty', 'omitted', 'unresolved'):
            need(prompt['value'] is None, 'microstrategy.prompt_mode_value')
    for key in ('timezone', 'locale', 'principal', 'cache'):
        need(value[key] is None or text(value[key]), 'microstrategy.state_context')
    F.decode(encoded(value)); F.secret_check(value)


state = validate_state


def known_version(value):
    # Pin a concrete declared deployment version, never infer support from a
    # marketing name or 'latest'. Host qualification is still separate.
    return type(value) is str and (re.fullmatch(r'20[2-9][0-9][.-](?:0[1-9]|1[0-2])(?:[.-][0-9]+)*', value)
        is not None or re.fullmatch(r'2021 Update (?:[7-9]|[1-9][0-9])', value) is not None)


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'identity', 'root', 'authorization_ref', 'credential_ref', 'evidence_mode',
        'route', 'route_reference', 'target_surface', 'state', 'snapshot_path', 'originals_path'}
    defaults = {'api_profile': None, 'operations': [], 'max_requests_per_invocation': 8, 'max_total_requests': 100,
        'max_total_bytes': F.MAX_TOTAL, 'max_response_bytes': F.MAX_FILE, 'max_elapsed_seconds': 21600,
        'max_attempts_per_operation': 3, 'poll_interval_seconds': 2}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value['schema_version'] == REQUEST, 'microstrategy.request_contract')
    r = {**defaults, **copy.deepcopy(value)}
    validate_identity(r['identity']); validate_state(r['state'])
    need(local_id(r['capture_id']) and text(r['authorization_ref']) and (r['credential_ref'] is None or text(r['credential_ref'])),
         'microstrategy.request_identity')
    need(type(r['root']) is dict and set(r['root']) == {'kind', 'id'} and r['root']['kind'] in ('dossier', 'report', 'document', 'cube')
         and guid(r['root']['id']), 'microstrategy.root')
    need(r['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant') and r['target_surface'] in ('app', 'dashboard', 'both'),
         'microstrategy.request_mode')
    need(r['route'] in ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
         and (r['route'] == 'unselected' or text(r['route_reference'])), 'microstrategy.route')
    for name in ('snapshot_path', 'originals_path'): F.source_path(r[name])
    need(r['snapshot_path'] != r['originals_path'], 'microstrategy.distinct_source_records')
    for key, lo, hi in [('max_requests_per_invocation', 1, 30), ('max_total_requests', 1, 500),
        ('max_total_bytes', 1, F.MAX_TOTAL), ('max_response_bytes', 1, F.MAX_FILE), ('max_elapsed_seconds', 1, 86400),
        ('max_attempts_per_operation', 1, 5), ('poll_interval_seconds', 1, 60)]:
        need(type(r[key]) is int and lo <= r[key] <= hi, 'microstrategy.budget')
    profile = r['api_profile']
    if profile is not None:
        need(type(profile) is dict and set(profile) == {'id', 'library_version', 'intelligence_server_version',
            'api_schema_path', 'api_schema_sha256', 'reference'} and profile['id'] == PROFILE
            and digest(profile['api_schema_sha256']) and text(profile['reference']), 'microstrategy.api_profile')
        F.source_path(profile['api_schema_path'])
        for key in ('library_version', 'intelligence_server_version'):
            need(profile[key] == r['identity'][key] and known_version(profile[key]), 'microstrategy.version_profile')
    need(type(r['operations']) is list and len(r['operations']) <= 100
         and (not r['operations'] or profile is not None and r['identity']['model_generation'] == 'classic'
              and r['root']['kind'] in ('dossier', 'report')), 'microstrategy.connected_profile_required')
    need(r['state']['principal'] in (None, r['identity']['principal_ref'])
         and (not r['operations'] or r['state']['principal'] is not None), 'microstrategy.state_principal_mismatch')
    ids = set(); previous = {}
    for op in r['operations']:
        validate_operation(r, op)
        need(op['operation_id'] not in ids, 'microstrategy.duplicate_operation'); ids.add(op['operation_id'])
        if op['kind'] not in ('definition', 'create_instance'):
            parent = previous.get(op['instance_from'])
            need(parent is not None and parent['kind'] == 'create_instance', 'microstrategy.owned_instance_dependency')
        previous[op['operation_id']] = op
    need(not require_service or r['credential_ref'] is not None and bool(r['operations']), 'microstrategy.host_scope_required')
    F.secret_check(r); screen_bytes(encoded(r))
    return r


def validate_operation(config, op):
    need(type(op) is dict and set(op) == {'operation_id', 'kind', 'object_key', 'instance_from', 'body', 'reference'}
         and local_id(op['operation_id']) and op['kind'] in OP_KINDS and text(op['object_key'])
         and text(op['reference']), 'microstrategy.reviewed_operation')
    kind, body = op['kind'], op['body']
    need((op['instance_from'] is None) == (kind in ('definition', 'create_instance'))
         and (op['instance_from'] is None or local_id(op['instance_from'])), 'microstrategy.instance_dependency')
    if kind in ('definition', 'create_instance', 'prompts'):
        need(body is None, 'microstrategy.empty_operation_body')
    elif kind == 'data':
        need(type(body) is dict and set(body) == {'offset', 'limit'}
             and type(body['offset']) is int and 0 <= body['offset'] <= 100000
             and type(body['limit']) is int and 1 <= body['limit'] <= 10000, 'microstrategy.bounded_data_page')
    elif kind == 'state_readback':
        need(type(body) is dict and set(body) == {'filter_pointers'} and type(body['filter_pointers']) is dict
             and set(body['filter_pointers']) == set(FILTER_STAGES)
             and all(type(v) is str and v.startswith('/') and len(v) <= 1000 for v in body['filter_pointers'].values()),
             'microstrategy.explicit_readback_crosswalk')
    elif kind == 'prompt_answers':
        need(type(body) is dict and set(body) == {'prompts'} and type(body['prompts']) is list and 1 <= len(body['prompts']) <= 100,
             'microstrategy.prompt_answers')
        desired = {p['key']: p for p in config['state']['parameters']['prompts']}; seen = set()
        for row in body['prompts']:
            need(type(row) is dict and {'key', 'type'} <= set(row) <= {'key', 'type', 'answers', 'useDefault'}
                 and row['key'] in desired and row['key'] not in seen and row['type'] in ('ELEMENTS', 'OBJECTS', 'VALUE'),
                 'microstrategy.prompt_answer_kind')
            seen.add(row['key']); wanted = desired[row['key']]
            if wanted['answer_mode'] == 'default':
                need(row == {'key': row['key'], 'type': row['type'], 'useDefault': True}, 'microstrategy.prompt_default')
            elif wanted['answer_mode'] == 'empty':
                need(row == {'key': row['key'], 'type': row['type']}, 'microstrategy.prompt_empty')
            else:
                need(wanted['answer_mode'] == 'explicit' and set(row) == {'key', 'type', 'answers'}
                     and row['answers'] == wanted['value'] and type(row['answers']) is list and 1 <= len(row['answers']) <= 1000,
                     'microstrategy.prompt_explicit')
                for answer in row['answers']:
                    if row['type'] == 'VALUE':
                        need(type(answer) in (str, int, float, bool) and (type(answer) is not str or len(answer) <= 1000), 'microstrategy.value_prompt')
                    elif row['type'] == 'ELEMENTS':
                        need(type(answer) is dict and set(answer) == {'id'} and text(answer['id']), 'microstrategy.element_prompt')
                    else:
                        need(type(answer) is dict and set(answer) == {'id', 'type'} and guid(answer['id'])
                             and type(answer['type']) is int and answer['type'] in (4, 12), 'microstrategy.object_prompt')
    elif kind == 'selectors':
        # Only supplied existing chapter selector payloads, no view-filter SQL
        # or ad-hoc expressions. Exact native semantics remain version-qualified.
        need(config['root']['kind'] == 'dossier' and body == config['state']['filters']['chapter']
             and type(body) is list and 1 <= len(body) <= 100, 'microstrategy.selector_state')
        seen = set()
        for row in body:
            need(type(row) is dict and {'key', 'currentSelection'} == set(row) and text(row['key']) and row['key'] not in seen,
                 'microstrategy.selector_subset')
            selected = row['currentSelection']
            need(type(selected) is dict and set(selected) == {'selectionStatus', 'allSelected', 'elements'}
                 and selected['selectionStatus'] == 'included' and selected['allSelected'] is False
                 and type(selected['elements']) is list and 1 <= len(selected['elements']) <= 1000
                 and all(type(x) is dict and set(x) == {'id'} and text(x['id']) for x in selected['elements']),
                 'microstrategy.selector_subset')
            seen.add(row['key'])
    elif kind == 'pdf':
        keys = {'pageHeight', 'pageWidth', 'orientation', 'pageOption', 'includeOverview', 'includeDetailedPages',
                'waitingTimeBeforeExport', 'includeHeader', 'includeFooter'}
        need(config['root']['kind'] == 'dossier' and type(body) is dict and set(body) == keys and body['pageOption'] == 'ALL'
             and body['orientation'] == 'AUTO'
             and body['waitingTimeBeforeExport'] == 0
             and all(type(body[k]) in (int, float) and 1 <= body[k] <= 30 for k in ('pageHeight', 'pageWidth'))
             and all(type(body[k]) is bool for k in ('includeOverview', 'includeDetailedPages', 'includeHeader', 'includeFooter')),
             'microstrategy.pdf_profile')
    need(len(encoded(body)) <= 65536, 'microstrategy.operation_body_bound')


def validate_scope(config, snapshot):
    visual = module('microstrategy_visual')
    indexed = {row['key']: row for row in snapshot['inventory']['items']}
    for op in config['operations']:
        scope = visual.scope_item(snapshot, op['object_key']); row, target = scope['item'], scope['target']
        need(row['disposition'] == target['disposition'] == 'include' and not scope['restricted'], 'microstrategy.scope_not_selected')
        if op['kind'] == 'data' and config['root']['kind'] == 'dossier':
            need(scope['query_visual'] and row['kind'] in ('visual', 'placement'), 'microstrategy.query_visual_required')
        else:
            need(target['kind'] == config['root']['kind'] and target['native_id'] == config['root']['id']
                 and target['source_mapping'] == {'object_kind': config['root']['kind'], 'object_id': config['root']['id'], 'pointer': ''},
                 'microstrategy.root_operation_scope')
        if config['root']['kind'] == 'report' and op['kind'] != 'definition':
            node = scope['node']; info = node.get('information', {})
            need(type(info) is dict and info.get('subType') == 'report_grid', 'microstrategy.ordinary_saved_report_only')
        if op['kind'] == 'pdf' and config['root']['kind'] == 'dossier':
            # Whole-dashboard export must not bypass a private or excluded child.
            for child in indexed.values():
                selected = visual.scope_item(snapshot, child['key'])
                need(child['disposition'] == 'include' and not selected['restricted'], 'microstrategy.whole_export_scope')
            # Unmapped native obligations are checked by the visual projection;
            # require every supplied native visual node to have a mapped row.
            root_node = scope['node']; chapters = root_node.get('chapters')
            need(type(chapters) is list, 'microstrategy.export_native_hierarchy')
            mapped = {(r['source_mapping']['object_kind'], r['source_mapping']['object_id'], r['source_mapping']['pointer'])
                      for r in indexed.values() if r['source_mapping']}
            for ci, chapter in enumerate(chapters):
                need(type(chapter.get('pages')) is list, 'microstrategy.export_native_pages')
                for pi, page in enumerate(chapter['pages']):
                    need(type(page.get('visualizations')) is list, 'microstrategy.export_native_visuals')
                    for vi, _ in enumerate(page['visualizations']):
                        need(('dossier', config['root']['id'], '/chapters/%d/pages/%d/visualizations/%d' % (ci, pi, vi)) in mapped,
                             'microstrategy.export_unmapped_native_visual')


validate_operation_scope = validate_scope


def successful_responses(envelope):
    return {envelope['operations'][r['attempt']]['key']: r['inspection'] for r in envelope['responses']}


def operation_spec(config, op, envelope=None):
    r = validate_request(config); need(op in r['operations'], 'microstrategy.operation_not_selected')
    kind, root = op['kind'], r['root']; oid = root['id']
    base = r['identity']['source_origin'] + r['identity']['context_path'] + '/api'
    scope, method, body, path = 'metadata', 'GET', None, None
    iid = None
    if kind not in ('definition', 'create_instance'):
        need(type(envelope) is dict and envelope.get('request_sha256') == sha(r), 'microstrategy.owned_instance_required')
        created = successful_responses(envelope).get(op['instance_from'])
        need(type(created) is dict and created.get('kind') == 'create_instance' and guid(created.get('instance_id'))
             and created.get('definition_id') == oid, 'microstrategy.owned_instance_required')
        iid = created['instance_id']
    if kind == 'definition':
        path = '/v2/dossiers/' + oid + '/definition' if root['kind'] == 'dossier' else '/model/reports/' + oid
    elif kind == 'create_instance':
        scope, method = 'execution', 'POST'
        path = '/' + ('dossiers' if root['kind'] == 'dossier' else 'reports') + '/' + oid + '/instances'
        body = {}
    elif kind in ('prompts', 'prompt_answers'):
        path = '/' + ('documents' if root['kind'] == 'dossier' else 'reports') + '/' + oid + '/instances/' + iid + '/prompts'
        if kind == 'prompt_answers':
            path += '/answers'; scope, method, body = 'execution', 'PUT', op['body']
    elif kind == 'selectors':
        path = '/dossiers/' + oid + '/instances/' + iid + '/filters'; scope, method, body = 'execution', 'PUT', op['body']
    elif kind == 'state_readback':
        path = '/v2/dossiers/' + oid + '/instances/' + iid + '/definition' if root['kind'] == 'dossier' else \
            '/v2/reports/' + oid + '/instances/' + iid + '?offset=0&limit=0'
        # Report state readback can fetch/finish report execution.
        scope = 'execution'
    elif kind == 'data':
        scope = 'execution'
        if root['kind'] == 'report':
            path = '/v2/reports/' + oid + '/instances/' + iid
        else:
            need(type(envelope) is dict and 'source' in envelope, 'microstrategy.source_scope_required')
            snapshot = envelope['source']['snapshot']; selected = module('microstrategy_visual').scope_item(snapshot, op['object_key'])
            indexed = {x['key']: x for x in snapshot['inventory']['items']}; row = selected['item']
            while row is not None and row['kind'] != 'chapter': row = indexed.get(row['parent_key'])
            need(row is not None and native_id(row['native_id']) and native_id(selected['native_id']), 'microstrategy.visual_chapter_binding')
            path = '/dossiers/' + oid + '/instances/' + iid + '/chapters/' + row['native_id'] + '/visualizations/' + selected['native_id']
        path += '?offset=%d&limit=%d' % (op['body']['offset'], op['body']['limit'])
    elif kind == 'pdf':
        scope, method, body = 'render', 'POST', op['body']
        path = '/documents/' + oid + '/instances/' + iid + '/pdf'
    need(path is not None, 'microstrategy.unsupported_operation')
    return {'scope': scope, 'operation_id': op['operation_id'], 'phase': kind, 'method': method,
            'url': base + path, 'body': copy.deepcopy(body), 'request_headers': {}, 'instance_id': iid}


def fingerprint(config, selected):
    return {'request_sha256': sha(validate_request(config)), 'operation_id': selected['operation_id'], 'phase': selected['phase'],
            'method': selected['method'], 'url': selected['url'], 'body_sha256': sha(selected['body']),
            'request_headers_sha256': sha(selected['request_headers'])}


def latest_instance_response(envelope, iid, kinds):
    found = [r['inspection'] for r in envelope['responses'] if r['inspection'].get('instance_id') == iid
             and r['inspection'].get('kind') in kinds]
    return found[-1] if found else None


def require_state(envelope, selected):
    iid, kind = selected['instance_id'], selected['phase']
    if kind == 'create_instance':
        need(any(r['inspection'].get('kind') == 'definition' and r['inspection'].get('definition_matches') is True
                 for r in envelope['responses']), 'microstrategy.definition_read_before_execution_required')
        return
    if kind in ('definition', 'prompts', 'state_readback'): return
    observations = [r['inspection'] for r in envelope['responses'] if r['inspection'].get('instance_id') == iid]
    if kind == 'prompt_answers':
        previous = latest_instance_response(envelope, iid, {'prompts'})
        need(previous is not None, 'microstrategy.prompt_definition_read_required')
        by_key = {r['key']: r for r in previous['prompts']}
        desired = {p['key']: p for p in envelope['request']['state']['parameters']['prompts']}
        for row in selected['body']['prompts']:
            seen = by_key.get(row['key']); wanted = desired[row['key']]
            need(seen is not None and seen['id'] == wanted['id'] and seen['type'] == row['type'], 'microstrategy.prompt_definition_changed')
            need(wanted['answer_mode'] != 'empty' or seen['required'] is False, 'microstrategy.required_prompt_empty')
        return
    if kind == 'selectors':
        previous = latest_instance_response(envelope, iid, {'state_readback'})
        need(previous is not None and all(row['key'] in previous['selector_keys'] for row in selected['body']),
             'microstrategy.selector_definition_read_required')
        return
    last_change = max((i for i, row in enumerate(observations) if row['kind'] in ('prompt_answers', 'selectors')), default=-1)
    reads = [row for i, row in enumerate(observations) if i > last_change and row['kind'] == 'state_readback' and row['state_matches']]
    prompts = [row for i, row in enumerate(observations) if i > last_change and row['kind'] == 'prompts' and row['prompts_resolved']]
    need(reads and prompts and reads[-1]['execution_status'] == 1,
         'microstrategy.observed_state_after_changes_required')
    # This is supplied/API consistency, not effective-access authentication.
    need(not any(p['answer_mode'] in ('unresolved', 'omitted', 'all') for p in envelope['request']['state']['parameters']['prompts']),
         'microstrategy.unqualified_prompt_mode')


def pending_operation_spec(config, envelope):
    validate_envelope(envelope)
    pending = [x for x in envelope['operations'] if x['status'] == 'pending']
    need(len(pending) == 1 and pending[0] is envelope['operations'][-1], 'microstrategy.pending_operation_required')
    op = next(x for x in envelope['request']['operations'] if x['operation_id'] == pending[0]['key'])
    selected = operation_spec(config, op, envelope); require_state(envelope, selected)
    return selected


def no_business_errors(data):
    stack = [data]
    while stack:
        row = stack.pop()
        if type(row) is dict:
            need(not row.get('error') and not row.get('errors') and row.get('success') is not False,
                 'microstrategy.business_error')
            # ErrorCode/code alone may be legitimate source data; only reject
            # recognizable top-level error envelopes, never arbitrary metrics.
            if row is data and 'code' in row and ('message' in row or 'iServerCode' in row):
                raise F.CaptureError('microstrategy.business_error')
            stack.extend(row.values())
        elif type(row) is list: stack.extend(row)


def prompt_readback(data, config):
    need(type(data) is list and len(data) <= 100, 'microstrategy.prompt_response')
    keys = set(); observed = []
    for row in data:
        need(type(row) is dict and text(row.get('key')) and row['key'] not in keys and guid(row.get('id'))
             and row.get('type') in ('ELEMENTS', 'OBJECTS', 'VALUE', 'EXPRESSION', 'LEVEL')
             and type(row.get('closed')) is bool and type(row.get('required')) is bool, 'microstrategy.prompt_response_identity')
        keys.add(row['key']); observed.append({k: copy.deepcopy(row.get(k)) for k in ('key', 'id', 'type', 'closed', 'required', 'answers', 'defaultAnswer')})
    desired = {p['key']: p for p in config['state']['parameters']['prompts']}
    resolved = keys == set(desired) and all(row['closed'] for row in observed)
    for row in observed:
        wanted = desired.get(row['key'])
        if wanted is None or row['id'] != wanted['id']: resolved = False; continue
        mode = wanted['answer_mode']; answers = row['answers']
        # Names may accompany native IDs. Compare the typed identity-bearing
        # fields, never convert a display name into an element/object ID.
        def canonical(v):
            if type(v) is list:
                return [{k: x[k] for k in ('id', 'type') if k in x} if type(x) is dict and 'id' in x else x for x in v]
            return v
        expected = row['defaultAnswer'] if mode == 'default' else wanted['value']
        if mode in ('explicit', 'default'):
            if expected is None or canonical(answers) != canonical(expected): resolved = False
        elif mode == 'empty':
            if row['required'] or answers not in (None, []): resolved = False
        else: resolved = False
    return observed, resolved


def pdf_bytes(raw):
    pdf = raw
    if not raw.startswith(b'%PDF-'):
        screen_bytes(raw); wrapper = F.decode(raw); F.secret_check(wrapper); no_business_errors(wrapper)
        need(type(wrapper) is dict and set(wrapper) == {'data'} and type(wrapper['data']) is str
             and len(wrapper['data']) <= (F.MAX_FILE * 4 // 3 + 8), 'microstrategy.pdf_wrapper')
        try: pdf = base64.b64decode(wrapper['data'], validate=True)
        except (ValueError, binascii.Error): raise F.CaptureError('microstrategy.pdf_base64') from None
    need(len(pdf) <= F.MAX_FILE, 'microstrategy.pdf_size')
    return pdf


def screen_granted_echo(raw, grant):
    secrets = [grant['X-MSTR-AuthToken'], grant['Cookie']] + [x.strip().split('=', 1)[1] for x in grant['Cookie'].split(';') if '=' in x]
    for secret in secrets:
        for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
            need(secret.encode(encoding) not in raw, 'microstrategy.credential_echo_rejected')


def inspect_response(raw, config, op, selected, envelope):
    kind, iid, oid = op['kind'], selected['instance_id'], config['root']['id']
    common = {'kind': kind, 'definition_id': oid, 'instance_id': iid, 'effective_access': 'not_verified'}
    if kind == 'pdf':
        pdf = pdf_bytes(raw)
        info = inspect_attachment(pdf, 'pdf')
        return {**common, 'format': 'pdf', 'pdf_sha256': F.raw_sha(pdf), 'pdf_bytes': len(pdf),
                'inspection': info, 'numerical_completeness': 'not_established'}
    if kind in ('prompt_answers', 'selectors'):
        need(raw in (b'', b'{}'), 'microstrategy.mutation_response')
        return common
    screen_bytes(raw); data = F.decode(raw); F.secret_check(data); no_business_errors(data)
    if kind == 'create_instance':
        need(type(data) is dict, 'microstrategy.instance_response')
        native = data.get('mid') if config['root']['kind'] == 'dossier' else data.get('instanceId')
        need(guid(native) and ('id' not in data or data['id'] == oid), 'microstrategy.created_instance_identity')
        return {**common, 'instance_id': native, 'execution_status': data.get('status'), 'ownership': 'created_by_this_capture'}
    if kind == 'prompts':
        prompts, resolved = prompt_readback(data, config)
        return {**common, 'prompts': prompts, 'prompts_resolved': resolved}
    need(type(data) is dict, 'microstrategy.response_object')
    if kind == 'definition':
        actual = data.get('id', data.get('information', {}).get('objectId'))
        need(actual == oid, 'microstrategy.definition_identity')
        original = next(o['payload'] for o in envelope['source']['snapshot']['objects']
                        if o['kind'] == config['root']['kind'] and o['id'] == oid)
        need(data == original, 'microstrategy.source_definition_drift')
        return {**common, 'definition_sha256': sha(data), 'definition_matches': True}
    if kind == 'state_readback':
        # Pointer crosswalks are pinned, explicit provenance, not automatic
        # interpretation of filter summaries or an assertion of authority.
        filters = {k: pointer(data, p) for k, p in op['body']['filter_pointers'].items()}
        need(all(type(v) is list for v in filters.values()), 'microstrategy.observed_filter_shape')
        if 'id' in data: need(data['id'] == oid, 'microstrategy.readback_definition')
        if 'instanceId' in data: need(data['instanceId'] == iid, 'microstrategy.readback_instance')
        if 'mid' in data: need(data['mid'] == iid, 'microstrategy.readback_instance')
        return {**common, 'state_matches': filters == config['state']['filters'], 'filters_sha256': sha(filters),
                'selector_keys': [x['key'] for x in filters['chapter'] if type(x) is dict and text(x.get('key'))],
                'raw_readback_sha256': F.raw_sha(raw), 'execution_status': data.get('status')}
    need(kind == 'data', 'microstrategy.response_kind')
    if config['root']['kind'] == 'report':
        need(data.get('id') == oid and data.get('instanceId') == iid and data.get('status') == 1, 'microstrategy.report_not_completed')
        definition, results = data.get('definition'), data.get('data')
    else:
        scope = module('microstrategy_visual').scope_item(envelope['source']['snapshot'], op['object_key'])
        need(data.get('key') == scope['native_id'] and type(data.get('result')) is dict, 'microstrategy.visualization_identity')
        definition, results = data['result'].get('definition'), data['result'].get('data')
    need(type(definition) is dict and type(results) is dict and type(results.get('paging')) is dict,
         'microstrategy.native_results_required')
    paging = results['paging']
    need(all(type(paging.get(k)) is int and paging[k] >= 0 for k in ('offset', 'limit', 'total', 'current'))
         and paging['offset'] == op['body']['offset'] and paging['limit'] == op['body']['limit']
         and paging['current'] <= paging['limit'] and paging['offset'] + paging['current'] <= paging['total'],
         'microstrategy.result_paging')
    return {**common, 'result_definition_sha256': sha(definition), 'paging': copy.deepcopy(paging),
            'execution_status': 'completed' if config['root']['kind'] == 'report' else 'not_established_by_visual_response',
            'numerical_completeness': 'not_established'}


def pointer(value, path):
    need(type(path) is str and len(path) <= 1000 and (path == '' or path.startswith('/'))
         and re.search(r'~(?![01])', path) is None, 'microstrategy.json_pointer')
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(part in value, 'microstrategy.pointer_missing'); value = value[part]
        elif type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', part) is not None and int(part) < len(value), 'microstrategy.pointer_missing')
            value = value[int(part)]
        else:
            raise F.CaptureError('microstrategy.pointer_missing')
    return value


def validate_originals(manifest, snapshot):
    need(type(manifest) is dict and set(manifest) == {'schema_version', 'reference', 'records'}
         and manifest['schema_version'] == 'microstrategy-originals.v1' and text(manifest['reference'])
         and type(manifest['records']) is list and 1 <= len(manifest['records']) <= 500, 'microstrategy.originals_manifest')
    expected = {'/inventory'} | {'/objects/%d/payload' % i for i in range(len(snapshot['objects']))}
    targets, paths, aliases = set(), set(), {}
    for row in manifest['records']:
        need(type(row) is dict and set(row) == {'source_path', 'source_kind', 'source_pointer', 'target_pointer', 'mapping',
             'member_path', 'reference', 'mcp_evidence'} and row['source_kind'] in
             ('rest_json', 'supplied_json', 'mcp_json', 'script', 'yaml', 'zip', 'opaque') and text(row['reference'])
             and row['mapping'] in ('exact_json', 'opaque_preserved'), 'microstrategy.original_record')
        path = F.source_path(row['source_path'])
        folded = unicodedata.normalize('NFC', path).casefold()
        need(folded not in aliases or aliases[folded] == path, 'microstrategy.original_path_alias')
        need(not any(path != p and (path.startswith(p + '/') or p.startswith(path + '/')) for p in paths),
             'microstrategy.original_path_collision')
        aliases[folded] = path; paths.add(path)
        if row['member_path'] is not None:
            F.source_path(row['member_path'])
            need(row['source_kind'] == 'zip', 'microstrategy.member_requires_zip')
        target = row['target_pointer']
        need(target is None or (target in expected and target not in targets), 'microstrategy.original_target')
        if target is not None:
            targets.add(target)
        if row['mapping'] == 'exact_json':
            need(row['source_kind'] in ('rest_json', 'supplied_json', 'mcp_json', 'zip') and target is not None
                 and type(row['source_pointer']) is str, 'microstrategy.exact_json_mapping')
        else:
            need(row['source_pointer'] is None and target != '/inventory', 'microstrategy.opaque_mapping')
        need((row['mcp_evidence'] is None and row['source_kind'] != 'mcp_json') or row['source_kind'] == 'mcp_json' and
             type(row['mcp_evidence']) is dict and set(row['mcp_evidence']) == {'reference', 'schema_reference', 'tool_name', 'call_id', 'server_version'}
             and all(text(v) for v in row['mcp_evidence'].values()), 'microstrategy.mcp_provenance')
    need(targets == expected, 'microstrategy.original_object_denominator')
    F.secret_check(manifest)
    return manifest


def zip_members(raw):
    """Bounded in-memory inventory; no filesystem extraction or YAML decoding."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            need(1 <= len(entries) <= 500, 'microstrategy.zip_member_limit')
            members, names, prefixes, total = {}, set(), {}, 0
            for item in entries:
                path = item.filename[:-1] if item.is_dir() else item.filename
                F.source_path(path)
                folded = unicodedata.normalize('NFC', path).casefold()
                need(folded not in names, 'microstrategy.zip_path_collision'); names.add(folded)
                parts = path.split('/')
                for i in range(1, len(parts) + 1):
                    prefix = '/'.join(parts[:i]); key = unicodedata.normalize('NFC', prefix).casefold()
                    need(key not in prefixes or prefixes[key] == prefix, 'microstrategy.zip_path_alias'); prefixes[key] = prefix
                mode = item.external_attr >> 16
                need(not item.flag_bits & 1 and item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                     and stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'microstrategy.zip_unsafe_member')
                if item.is_dir():
                    continue
                total += item.file_size
                need(total <= F.MAX_TOTAL and item.file_size <= F.MAX_FILE
                     and item.file_size <= max(1, item.compress_size) * 100, 'microstrategy.zip_expansion_limit')
                with archive.open(item) as stream:
                    content = stream.read(F.MAX_FILE + 1)
                need(len(content) == item.file_size <= F.MAX_FILE, 'microstrategy.zip_size_mismatch')
                suffix = Path(path).suffix.lower()
                screening = screen_bytes(content) if suffix in ('.yaml', '.yml', '.tml', '.json', '.txt', '.csv', '.xml', '.html', '.js') else screen_opaque(content)
                members[path] = {'bytes': len(content), 'sha256': F.raw_sha(content), 'credential_screening': screening, 'raw': content}
            file_names = {unicodedata.normalize('NFC', path).casefold() for path in members}
            need(not any(a != b and a.startswith(b + '/') for a in names for b in file_names), 'microstrategy.zip_file_directory_collision')
            return members
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        raise F.CaptureError('microstrategy.invalid_zip') from None


def inspect_original(row, raw, snapshot):
    content = raw
    inspection = {'interpretation': 'inert_bytes', 'source_code_execution': False}
    if row['source_kind'] == 'zip':
        members = zip_members(raw)
        inspection['members'] = [{'path': path, **{k: v for k, v in record.items() if k != 'raw'}} for path, record in members.items()]
        inspection['interpretation'] = 'zip_members_only'
        if row['member_path'] is not None:
            need(row['member_path'] in members, 'microstrategy.zip_member_missing')
            content = members[row['member_path']]['raw']
        else:
            need(row['mapping'] == 'opaque_preserved' and row['target_pointer'] is None, 'microstrategy.zip_member_mapping_required')
    elif row['source_kind'] in ('script', 'rest_json', 'supplied_json', 'mcp_json'):
        inspection['credential_screening'] = screen_bytes(raw)
    else:
        inspection['credential_screening'] = screen_opaque(raw)
    if row['mapping'] == 'exact_json':
        original = F.decode(content); F.secret_check(original)
        selected = pointer(original, row['source_pointer'])
        need(selected == pointer(snapshot, row['target_pointer']), 'microstrategy.original_payload_mismatch')
        inspection['interpretation'] = 'exact_json_pointer'
    elif row['target_pointer'] is not None:
        expected = {'opaque_original': {'source_path': row['source_path'], 'member_path': row['member_path'],
                                       'sha256': F.raw_sha(content)}}
        need(pointer(snapshot, row['target_pointer']) == expected, 'microstrategy.opaque_placeholder_mismatch')
    return inspection


def definition_fingerprint(snapshot):
    return sha(snapshot)


def file_pins(value):
    source = value['source']
    pins = [source['snapshot_file'], source['originals_manifest_file']] + [x['file'] for x in source['originals']] + \
           value['attachments'] + [x['archive_file'] for x in value['attachments'] if x.get('archive_file') is not None] + \
           [r['file'] for r in value['responses']] + ([source['api_schema_file']] if source.get('api_schema_file') else [])
    unique = {}
    for pin in pins:
        need(type(pin) is dict and type(pin.get('path')) is str, 'microstrategy.file_pin')
        need(pin['path'] not in unique or unique[pin['path']] == pin, 'microstrategy.file_pin_collision')
        unique[pin['path']] = pin
    return list(unique.values())


def _save(root, value):
    value['journal_revision'] += 1
    value.pop('content_hash', None); value['content_hash'] = sha(value)
    raw = encoded(value)
    snapshots = list(root.glob('capture-*.json'))
    need(len(snapshots) < 3000 and len(raw) <= F.MAX_JSON and
         len(raw) + sum(F.no_links(p).stat().st_size for p in snapshots) <= MAX_JOURNAL_BYTES, 'microstrategy.journal_budget')
    pin = F.write_once(root, 'capture-%06d.json' % value['journal_revision'], raw)
    return root / pin['path']


def advance(root, value):
    path = _save(root, value)
    value['previous_capture'] = {'path': path.name, 'sha256': F.raw_sha(F.read_file(path, F.MAX_JSON))}
    return path


def result(path):
    value = F.decode(F.read_file(path, F.MAX_JSON))
    return {'status': value['status'], 'output': str(path), 'capture': value}


def validate_snapshot(value, request=None):
    module('microstrategy_visual').validate_snapshot(value)
    if request is not None:
        need(value['identity'] == request['identity'] and value['root'] == request['root'], 'microstrategy.snapshot_request_identity')
    F.secret_check(value)
    return value


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read is True, 'microstrategy.source_read_grant_required')
    r = validate_request(request)
    source_root, root = F.no_links(source_root), F.private_directory(directory)
    need(source_root.is_dir() and not list(root.iterdir()), 'microstrategy.new_directory_required')
    raw_snapshot, raw_manifest = (F.read_file(source_root / r[k]) for k in ('snapshot_path', 'originals_path'))
    snapshot = validate_snapshot(F.decode(raw_snapshot), r)
    manifest = validate_originals(F.decode(raw_manifest), snapshot)
    validate_operation_scope(r, snapshot)
    api_schema = None
    if r['api_profile'] is not None:
        api_schema = F.read_file(source_root / r['api_profile']['api_schema_path'])
        validate_api_schema(api_schema, r)
    pending, total, cache, work = [], len(raw_snapshot) + len(raw_manifest) + (len(api_schema) if api_schema else 0), {}, 0
    for row in manifest['records']:
        if row['source_path'] not in cache:
            cache[row['source_path']] = F.read_file(source_root / row['source_path'])
            total += len(cache[row['source_path']])
        raw = cache[row['source_path']]
        work += len(raw)
        need(work <= 128000000, 'microstrategy.mapping_work_limit')
        info = inspect_original(row, raw, snapshot)
        need(total <= r['max_total_bytes'], 'microstrategy.source_byte_limit')
        pending.append((row, raw, info))
    source = {'snapshot': snapshot, 'snapshot_file': F.write_once(root, 'snapshot.json', raw_snapshot),
        'definition_fingerprint': definition_fingerprint(snapshot), 'originals_manifest': manifest,
        'originals_manifest_file': F.write_once(root, 'originals-manifest.json', raw_manifest), 'originals': [],
        'api_schema_file': F.write_once(root, 'api-schema.json', api_schema) if api_schema is not None else None}
    pins = {}
    for i, (row, raw, info) in enumerate(pending):
        if row['source_path'] not in pins:
            pins[row['source_path']] = F.write_once(root, 'original-%04d.bin' % i, raw)
        source['originals'].append({**copy.deepcopy(row), 'file': copy.deepcopy(pins[row['source_path']]), 'inspection': info})
    value = {'schema_version': ENVELOPE, 'capture_id': r['capture_id'], 'request': r, 'request_sha256': sha(r),
        'source': source, 'attachments': [], 'responses': [], 'operations': [], 'journal_revision': 0,
        'previous_capture': None, 'created_at_epoch': utcnow(), 'request_count': 0, 'network_bytes': 0,
        'retry_not_before_epoch': 0, 'status': 'partial', 'gaps': list(BASE_GAPS), 'target_write_authority': False,
        'arbitrary_source_code_execution': False, 'source_execution': False, 'saved_query_execution': 'not_requested',
        'render_execution': 'not_requested', 'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}
    _execution_state(value)
    return result(_save(root, value))


def inspect_attachment(raw, format, parser_profile=None):
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'microstrategy.attachment_size')
    need(parser_profile is None or format == 'json' and type(parser_profile) is dict
         and parser_profile.get('format') == 'json' and parser_profile.get('shape') in ('microstrategy_json_data',),
         'microstrategy.attachment_parser_profile')
    if format == 'png':
        return F.png_info(raw)
    if format == 'pdf':
        need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'microstrategy.pdf_signature')
        return {'validation': 'signature_only_not_rendered'}
    screen_bytes(raw)
    if format == 'json':
        value = F.decode(raw); F.secret_check(value)
        if parser_profile is not None:
            # Reuse the explicit native projection and typed normalizer. This
            # local inspection context is never emitted as capture/QA evidence.
            raw_hash = F.raw_sha(raw)
            binding = {k: raw_hash for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256')}
            binding.update(object_key='local-inspection-only', attachment_id='local-inspection-only',
                           instance_id=parser_profile.get('instance_id'), result_definition_sha256=parser_profile.get('definition_sha256'))
            normalized = module('microstrategy_visual').normalize_results(raw, parser_profile, binding)
            return {'row_count': normalized['row_count'], 'interpretation': 'explicit_native_tree_profile',
                    'parser_profile_sha256': sha(parser_profile), 'completeness': 'not_inferred'}
        rows = value if type(value) is list and all(type(x) is dict for x in value) else None
        need(rows is None or len(rows) <= 100000, 'microstrategy.result_row_limit')
        # Vendor response wrappers stay original JSON. Their paging/result grain
        # cannot be inferred from the length of a wrapper list.
        flat = rows is not None and all(all(type(v) in (str, int, float, bool) or v is None for v in row.values()) for row in rows)
        return {'row_count': len(rows) if flat else None, 'interpretation': 'object_rows_json' if flat else 'native_json_unqualified',
                'completeness': 'not_inferred'}
    need(format == 'csv', 'microstrategy.attachment_format')
    try:
        header = next(csv.reader(io.StringIO(raw.decode('utf-8-sig')), strict=True))
        need(0 < len(header) <= 512 and len(set(header)) == len(header) and all(text(x) for x in header), 'microstrategy.csv_headers')
        count = 0
        for row in module('bounded_csv').rows(raw, header, 'microstrategy'):
            F.secret_check(dict(zip(header, row))); count += 1
        return {'headers': header, 'row_count': count, 'interpretation': 'utf8_comma_csv', 'completeness': 'not_inferred'}
    except (UnicodeError, csv.Error, StopIteration):
        raise F.CaptureError('microstrategy.invalid_csv') from None


def validate_attachment(row, request, snapshot):
    required = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
        'population', 'freshness', 'completeness', 'reference'}
    derived = {'source_path', 'path', 'sha256', 'bytes', 'request_sha256', 'definition_fingerprint',
        'requested_state_sha256', 'inspection', 'acquisition', 'member_path', 'archive_file', 'parser_profile'}
    inventory = {x['key']: x for x in snapshot['inventory']['items']}
    need(type(row) is dict and required <= set(row) <= required | derived and local_id(row['attachment_id'])
         and row['object_key'] in inventory and row['format'] in ('csv', 'json', 'png', 'pdf') and text(row['reference']),
         'microstrategy.attachment_contract')
    need('parser_profile' not in row or row['format'] == 'json' and type(row['parser_profile']) is dict
         and row['parser_profile'].get('format') == 'json' and row['parser_profile'].get('shape') in ('microstrategy_json_data',),
         'microstrategy.attachment_parser_profile')
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown') and row['result_scope'] in
         ('query_result', 'transformed', 'displayed', 'unknown') and
         (row['origin'] not in ('displayed', 'transformed') or row['origin'] == row['result_scope']), 'microstrategy.result_origin')
    observed = row['observed_state']
    if observed is not None:
        need(type(observed) is dict and {'state', 'observed_at', 'reference'} <= set(observed) <=
             {'state', 'observed_at', 'reference', 'placement_reference', 'result_context', 'instance_id', 'result_definition_sha256', 'definition_reference', 'execution_status', 'execution_reference'}
             and text(observed['observed_at']) and text(observed['reference']), 'microstrategy.observed_state')
        validate_state(observed['state'])
        need(observed['state']['principal'] in (None, request['identity']['principal_ref']), 'microstrategy.observed_principal_mismatch')
        need('instance_id' not in observed or guid(observed['instance_id']), 'microstrategy.observed_instance')
        need('result_definition_sha256' not in observed or digest(observed['result_definition_sha256']), 'microstrategy.observed_definition_hash')
        need('execution_status' not in observed or observed['execution_status'] in ('completed', 'pending', 'failed', 'unknown'), 'microstrategy.observed_execution_status')
        for key in ('placement_reference', 'definition_reference', 'execution_reference'):
            need(key not in observed or text(observed[key]), 'microstrategy.observed_context_reference')
        if 'result_context' in observed:
            module('microstrategy_visual').result_context(observed['result_context'])
    for key, fields in (('population', {'key', 'description', 'reference'}),
                        ('freshness', {'data_watermark', 'observed_at', 'reference'})):
        need(type(row[key]) is dict and set(row[key]) == fields and all(v is None or text(v) for v in row[key].values()),
             'microstrategy.' + key)
    c = row['completeness']
    need(type(c) is dict and set(c) == {'status', 'reference', 'row_count'} and c['status'] in ('complete', 'partial', 'unknown')
         and (c['reference'] is None or text(c['reference'])) and
         (c['row_count'] is None or (type(c['row_count']) is int and 0 <= c['row_count'] <= 100000)), 'microstrategy.completeness')
    if c['status'] == 'complete':
        need(row['format'] in ('csv', 'json') and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and observed is not None and guid(observed.get('instance_id')) and digest(observed.get('result_definition_sha256'))
             and text(observed.get('definition_reference')) and observed.get('execution_status') == 'completed'
             and text(observed.get('execution_reference')) and text(observed['state']['principal']) and all(row['population'].values())
             and all(row['freshness'].values()) and text(c['reference']) and type(c['row_count']) is int,
             'microstrategy.complete_result_evidence_required')
    F.secret_check(row)


def _lock(root):
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), 'microstrategy.lock_type')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BaseException:
        os.close(fd); raise


def import_evidence(capture_path, spec, source_root):
    path = F.no_links(capture_path)
    root, source_root = F.private_directory(path.parent), F.no_links(source_root)
    fd = _lock(root)
    try:
        value, latest = _load(root)
        need(path == latest and type(spec) is dict and set(spec) == {'schema_version', 'attachments'}
             and spec['schema_version'] == 'microstrategy-supplied-evidence.v1' and type(spec['attachments']) is list
             and len(spec['attachments']) <= 100, 'microstrategy.evidence_import')
        seen = {a['attachment_id'] for a in value['attachments']}
        need(len(seen) + len(spec['attachments']) <= 500, 'microstrategy.attachment_count')
        keys = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
                'population', 'freshness', 'completeness', 'reference', 'source_path', 'member_path'}
        pending, total = [], sum(p['bytes'] for p in file_pins(value))
        for row in spec['attachments']:
            need(type(row) is dict and keys <= set(row) <= keys | {'parser_profile'}, 'microstrategy.supplied_attachment_fields')
            validate_attachment(row, value['request'], value['source']['snapshot'])
            need(row['attachment_id'] not in seen, 'microstrategy.duplicate_attachment'); seen.add(row['attachment_id'])
            original = F.read_file(source_root / F.source_path(row['source_path']))
            raw, archive = original, None
            if row['member_path'] is not None:
                F.source_path(row['member_path'])
                members = zip_members(original)
                need(row['member_path'] in members, 'microstrategy.zip_member_missing')
                raw, archive = members[row['member_path']]['raw'], original
            info = inspect_attachment(raw, row['format'], row.get('parser_profile'))
            need(row['completeness']['row_count'] is None or row['completeness']['row_count'] == info.get('row_count'),
                 'microstrategy.result_count_or_shape_unqualified')
            total += len(raw) + (len(archive) if archive is not None else 0)
            need(total <= value['request']['max_total_bytes'], 'microstrategy.retained_byte_limit')
            pending.append((row, raw, archive, info))
        for row, raw, archive, info in pending:
            record = {k: copy.deepcopy(v) for k, v in row.items() if k != 'source_path'}
            record.update(F.write_once(root, 'attachment-' + row['attachment_id'] + '.' + row['format'], raw))
            record.update(request_sha256=value['request_sha256'], definition_fingerprint=value['source']['definition_fingerprint'],
                requested_state_sha256=sha(value['request']['state']), inspection=info, acquisition='supplied',
                archive_file=None if archive is None else F.write_once(root, 'archive-' + row['attachment_id'] + '.zip', archive))
            value['attachments'].append(record)
        return result(advance(root, value))
    finally:
        os.close(fd)


def _load(directory, config=None):
    root = F.private_directory(directory)
    paths = sorted(root.glob('capture-*.json'))
    need(paths and len(paths) <= 3000 and sum(F.no_links(p).stat().st_size for p in paths) <= MAX_JOURNAL_BYTES,
         'microstrategy.capture_journal_missing_or_limit')
    previous, previous_value = None, None
    for i, path in enumerate(paths, 1):
        raw = F.read_file(path, F.MAX_JSON); value = F.decode(raw)
        need(path.name == 'capture-%06d.json' % i and value.get('journal_revision') == i and
             value.get('previous_capture') == previous, 'microstrategy.journal_chain')
        validate_envelope(value)
        validate_transition(previous_value, value)
        previous_value = value
        previous = {'path': path.name, 'sha256': F.raw_sha(raw)}
    verify_capture_files(value, root)
    need(config is None or value['request'] == validate_request(config), 'microstrategy.resume_request_changed')
    value['previous_capture'] = previous
    return value, paths[-1]


def load_latest(directory, config=None):
    _, path = _load(directory, config)
    return F.decode(F.read_file(path, F.MAX_JSON)), path


def check_capture(path):
    path = F.no_links(path)
    if path.is_dir():
        value, _ = load_latest(path)
        return verify_capture_files(value, path)
    return verify_capture_files(F.decode(F.read_file(path, F.MAX_JSON)), path.parent)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise F.CaptureError('microstrategy.redirect_rejected')


def default_transport(method, url, headers, body, maximum, timeout):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    try:
        response = opener.open(Request(url, data=body, headers=headers, method=method), timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        need(response.geturl() == url and not 300 <= response.code < 400, 'microstrategy.redirect_rejected')
        chunks, total = [], 0
        while True:
            need(time.monotonic() - started < timeout, 'microstrategy.response_deadline')
            data = response.read1(min(65536, maximum + 1 - total))
            if not data:
                break
            total += len(data)
            need(total <= maximum, 'microstrategy.response_byte_limit'); chunks.append(data)
        return response.code, dict(response.headers), b''.join(chunks)


def _execution_state(value):
    dispatched = [x for x in value['operations'] if x['dispatched']]
    executed = any(x['scope'] in ('execution', 'render') for x in dispatched)
    value['source_execution'] = executed
    value['saved_query_execution'] = 'attempted' if executed else 'not_run' if value['request']['operations'] else 'not_requested'
    value['render_execution'] = 'attempted' if any(x['scope'] == 'render' for x in dispatched) else \
        'not_run' if any(x['kind'] == 'pdf' for x in value['request']['operations']) else 'not_requested'


def prefix(value, count):
    return {**value, 'operations': value['operations'][:count],
            'responses': [r for r in value['responses'] if r['attempt'] < count]}


def next_requested(value):
    done = set(successful_responses(value))
    return next((op for op in value['request']['operations'] if op['operation_id'] not in done), None)


def schema_route(config, op):
    """Exact reviewed API path templates, not a wildcard Modeling API grant."""
    dossier = config['root']['kind'] == 'dossier'
    family = 'dossiers' if dossier else 'reports'
    routes = {
        'definition': ('get', '/v2/dossiers/{dossierId}/definition' if dossier else '/model/reports/{reportId}'),
        'create_instance': ('post', '/' + family + '/{objectId}/instances'),
        'prompts': ('get', '/' + ('documents' if dossier else 'reports') + '/{objectId}/instances/{instanceId}/prompts'),
        'prompt_answers': ('put', '/' + ('documents' if dossier else 'reports') + '/{objectId}/instances/{instanceId}/prompts/answers'),
        'selectors': ('put', '/dossiers/{dossierId}/instances/{instanceId}/filters'),
        'state_readback': ('get', '/v2/dossiers/{dossierId}/instances/{instanceId}/definition' if dossier else '/v2/reports/{reportId}/instances/{instanceId}'),
        'data': ('get', '/dossiers/{dossierId}/instances/{instanceId}/chapters/{chapterKey}/visualizations/{visualizationKey}' if dossier else '/v2/reports/{reportId}/instances/{instanceId}'),
        'pdf': ('post', '/documents/{documentId}/instances/{instanceId}/pdf')}
    return routes[op['kind']]


def validate_api_schema(raw, config):
    need(F.raw_sha(raw) == config['api_profile']['api_schema_sha256'], 'microstrategy.api_schema_hash')
    schema = F.decode(raw); F.secret_check(schema); screen_bytes(raw)
    need(type(schema) is dict and type(schema.get('paths')) is dict and schema['paths'], 'microstrategy.api_schema_document')
    # OpenAPI parameter names vary; preserve static path segments exactly.
    def canonical(path):
        return re.sub(r'\{[A-Za-z][A-Za-z0-9_]*\}', '{}', path.removeprefix('/api'))
    for op in config['operations']:
        method, path = schema_route(config, op)
        matches = [row for key, row in schema['paths'].items() if type(key) is str and canonical(key) == canonical(path)]
        need(len(matches) == 1 and type(matches[0]) is dict and type(matches[0].get(method)) is dict,
             'microstrategy.api_schema_route_not_qualified')


def validate_envelope(value):
    need(type(value) is dict and value.get('schema_version') == ENVELOPE and value.get('content_hash') ==
         sha({k: v for k, v in value.items() if k != 'content_hash'}), 'microstrategy.capture_hash_or_schema')
    r = validate_request(value.get('request'))
    need(r == value['request'] and value.get('request_sha256') == sha(r) and value.get('capture_id') == r['capture_id'], 'microstrategy.capture_request')
    need(value.get('target_write_authority') is False and value.get('arbitrary_source_code_execution') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed', 'microstrategy.capture_authority')
    source = value.get('source')
    need(type(source) is dict and set(source) == {'snapshot', 'snapshot_file', 'definition_fingerprint', 'originals_manifest',
         'originals_manifest_file', 'originals', 'api_schema_file'}, 'microstrategy.capture_source')
    validate_snapshot(source['snapshot'], r); validate_originals(source['originals_manifest'], source['snapshot']); validate_scope(r, source['snapshot'])
    need(source['definition_fingerprint'] == sha(source['snapshot']) and type(source['originals']) is list
         and len(source['originals']) == len(source['originals_manifest']['records'])
         and (source['api_schema_file'] is None) == (r['api_profile'] is None), 'microstrategy.source_originals')
    for declared, record in zip(source['originals_manifest']['records'], source['originals']):
        need(type(record) is dict and set(record) == set(declared) | {'file', 'inspection'}
             and all(record[k] == declared[k] for k in declared), 'microstrategy.original_record_changed')
    requested = {o['operation_id']: o for o in r['operations']}
    records, responses = value.get('operations'), value.get('responses')
    need(type(records) is list and len(records) <= r['max_total_requests'] and value.get('request_count') == len(records)
         and type(responses) is list and len(responses) <= len(records), 'microstrategy.operation_budget')
    seen = set()
    for response in responses:
        need(type(response) is dict and set(response) == {'attempt', 'file', 'inspection'}
             and type(response['attempt']) is int and 0 <= response['attempt'] < len(records)
             and response['attempt'] not in seen, 'microstrategy.response_record')
        seen.add(response['attempt'])
    success = set()
    for i, record in enumerate(records):
        need(type(record) is dict and record.get('key') in requested and record.get('status') in ('pending', 'success', 'rejected', 'uncertain', 'denied')
             and type(record.get('dispatched')) is bool and type(record.get('started_at_epoch')) in (int, float)
             and (record['status'] != 'denied' or record['dispatched'] is False and 'http_status' not in record)
             and (record['status'] not in ('success', 'rejected') and 'http_status' not in record or record['dispatched'] is True),
             'microstrategy.operation_record')
        prior = prefix(value, i); op = requested[record['key']]
        need(next_requested(prior) == op and not any(x['status'] == 'pending' or x['method'] != 'GET'
             and x['status'] in ('uncertain', 'rejected') for x in prior['operations']), 'microstrategy.operation_sequence')
        selected = operation_spec(r, op, prior); require_state(prior, selected)
        need(all(record.get(k) == selected[k] for k in ('phase', 'scope', 'method'))
             and record.get('fingerprint_sha256') == sha(fingerprint(r, selected)), 'microstrategy.operation_route_binding')
        if 'http_status' in record:
            need(type(record['http_status']) is int and digest(record.get('response_sha256')) and type(record.get('response_bytes')) is int
                 and 0 <= record['response_bytes'] <= r['max_response_bytes'], 'microstrategy.response_metadata')
        if record['status'] == 'success':
            response = next((x for x in responses if x['attempt'] == i), None)
            need(response is not None and record.get('http_status') == expected_status(selected)
                 and response['file']['sha256'] == record['response_sha256'] and response['file']['bytes'] == record['response_bytes'],
                 'microstrategy.response_attempt_binding'); success.add(i)
    need(success == seen, 'microstrategy.response_denominator')
    execution = copy.deepcopy(value); _execution_state(execution)
    need(all(value.get(k) == execution[k] for k in ('source_execution', 'saved_query_execution', 'render_execution')), 'microstrategy.execution_claim')
    attachments = value.get('attachments'); ids = set()
    need(type(attachments) is list and len(attachments) <= 500, 'microstrategy.attachment_count')
    for row in attachments:
        validate_attachment(row, r, source['snapshot'])
        need(row['attachment_id'] not in ids and row.get('request_sha256') == value['request_sha256']
             and row.get('definition_fingerprint') == source['definition_fingerprint'] and row.get('requested_state_sha256') == sha(r['state'])
             and row.get('acquisition') == 'supplied' and 'source_path' not in row
             and (row.get('member_path') is None) == (row.get('archive_file') is None), 'microstrategy.attachment_binding')
        ids.add(row['attachment_id'])
    need(type(value.get('network_bytes')) is int and value['network_bytes'] == sum(o.get('response_bytes', 0) for o in records)
         and 0 <= value['network_bytes'] <= r['max_total_bytes'] and type(value.get('journal_revision')) is int
         and 1 <= value['journal_revision'] <= 3000 and type(value.get('created_at_epoch')) in (int, float)
         and type(value.get('retry_not_before_epoch')) in (int, float), 'microstrategy.capture_budget')
    need(value.get('status') in ('partial', 'blocked', 'acquired_requested_operations') and type(value.get('gaps')) is list
         and all(text(x) for x in value['gaps']) and set(BASE_GAPS) <= set(value['gaps']), 'microstrategy.capture_status')
    if value['status'] == 'acquired_requested_operations':
        need(requested and next_requested(value) is None, 'microstrategy.false_acquisition_completion')
    for pin in file_pins(value):
        need(type(pin.get('path')) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', pin['path'])
             and digest(pin.get('sha256')) and type(pin.get('bytes')) is int and 0 <= pin['bytes'] <= F.MAX_FILE, 'microstrategy.file_pin')
    need(sum(p['bytes'] for p in file_pins(value)) <= r['max_total_bytes'], 'microstrategy.retained_byte_limit')
    return value


validate_capture = validate_envelope


def verify_capture_files(value, root):
    validate_envelope(value)
    raw = {p['path']: F.read_pin(F.no_links(root), p) for p in file_pins(value)}
    source = value['source']
    need(F.decode(raw[source['snapshot_file']['path']]) == source['snapshot'] and
         F.decode(raw[source['originals_manifest_file']['path']]) == source['originals_manifest'], 'microstrategy.original_snapshot_mismatch')
    if source['api_schema_file'] is not None:
        validate_api_schema(raw[source['api_schema_file']['path']], value['request'])
    work = 0
    for row in source['originals']:
        work += row['file']['bytes']; need(work <= 128000000, 'microstrategy.mapping_work_limit')
        need(inspect_original(row, raw[row['file']['path']], source['snapshot']) == row['inspection'], 'microstrategy.original_inspection_mismatch')
    for row in value['attachments']:
        content = raw[row['path']]
        if row.get('archive_file') is not None:
            members = zip_members(raw[row['archive_file']['path']])
            need(row['member_path'] in members and members[row['member_path']]['raw'] == content, 'microstrategy.attachment_member_mismatch')
        info = inspect_attachment(content, row['format'], row.get('parser_profile'))
        need(info == row['inspection'] and (row['completeness']['row_count'] is None or row['completeness']['row_count'] == info.get('row_count')),
             'microstrategy.attachment_inspection_mismatch')
    for response in value['responses']:
        record = value['operations'][response['attempt']]; prior = prefix(value, response['attempt'])
        op = next(x for x in value['request']['operations'] if x['operation_id'] == record['key'])
        selected = operation_spec(value['request'], op, prior)
        need(inspect_response(raw[response['file']['path']], value['request'], op, selected, prior) == response['inspection'],
             'microstrategy.response_inspection_mismatch')
    return {'status': 'verified_local_bytes', 'files': {p['path']: p['sha256'] for p in file_pins(value)}, 'native_validation': 'not_performed'}


def validate_transition(previous, current):
    if previous is None:
        need(current['journal_revision'] == 1 and current['previous_capture'] is None and not current['operations']
             and not current['responses'] and not current['attachments'] and current['request_count'] == current['network_bytes'] ==
             current['retry_not_before_epoch'] == 0 and current['status'] == 'partial', 'microstrategy.initial_journal_state')
        return
    immutable = ('schema_version', 'capture_id', 'request', 'request_sha256', 'source', 'created_at_epoch',
                 'target_write_authority', 'arbitrary_source_code_execution', 'native_validation', 'business_acceptance')
    need(all(current[k] == previous[k] for k in immutable), 'microstrategy.immutable_capture_changed')
    need(all(current[k] >= previous[k] for k in ('request_count', 'network_bytes', 'retry_not_before_epoch')), 'microstrategy.journal_counter_rollback')
    for key in ('responses', 'attachments', 'gaps'):
        need(len(current[key]) >= len(previous[key]) and current[key][:len(previous[key])] == previous[key], 'microstrategy.journal_evidence_rewritten')
    before, after = previous['operations'], current['operations']
    need(len(before) <= len(after) <= len(before) + 1, 'microstrategy.journal_attempts_rewritten')
    changed = 0
    for old, new in zip(before, after):
        if old == new: continue
        changed += 1
        need(old['status'] == 'pending' and new['status'] in ('success', 'rejected', 'uncertain', 'denied', 'pending')
             and set(new) <= set(old) | {'http_status', 'response_sha256', 'response_bytes'}
             and all(new.get(k) == v for k, v in old.items() if k not in ('status', 'dispatched'))
             and (old['dispatched'] == new['dispatched'] or not old['dispatched'] and new['dispatched'] and new['status'] == 'pending')
             and (new['status'] != 'pending' or not old['dispatched'] and new['dispatched']), 'microstrategy.terminal_attempt_rewritten')
        if new['status'] == 'rejected':
            need(type(new.get('http_status')) is int and 400 <= new['http_status'] < 500, 'microstrategy.rejected_attempt_status')
    need(changed <= 1, 'microstrategy.multiple_attempt_resolution')
    if len(after) > len(before):
        new = after[-1]
        need(changed == 0 and not any(o['status'] == 'pending' or o['method'] != 'GET' and o['status'] in ('uncertain', 'rejected') for o in before)
             and new['status'] == 'pending' and set(new) == {'key', 'phase', 'scope', 'method', 'fingerprint_sha256', 'started_at_epoch', 'status', 'dispatched'}
             and new['dispatched'] is False and new['started_at_epoch'] >= previous['retry_not_before_epoch']
             and sum(o['key'] == new['key'] for o in after) <= current['request']['max_attempts_per_operation'],
             'microstrategy.unresolved_mutation_or_attempt_limit')


def expected_status(selected):
    return 201 if selected['phase'] == 'create_instance' else 204 if selected['phase'] in ('prompt_answers', 'selectors') else 200


def capture(request, directory, *, authority=None, transport=None, resume=True, now=None):
    r = validate_request(request, require_service=True)
    need(callable(authority) and resume is True, 'microstrategy.import_then_host_capture_required')
    root = F.private_directory(directory); transport, now = transport or default_transport, now or utcnow
    fd = _lock(root)
    try:
        value, latest = _load(root, r)
        for record in value['operations']:
            if record['status'] == 'pending' and record['method'] == 'GET':
                record['status'] = 'uncertain'; latest = advance(root, value)
        count = 0
        while next_requested(value) is not None:
            if any(o['status'] == 'pending' or o['method'] != 'GET' and o['status'] in ('uncertain', 'rejected') for o in value['operations']):
                value['status'] = 'blocked'
                if 'uncertain_or_rejected_mutation_requires_resolution_no_blind_replay' not in value['gaps']:
                    value['gaps'].append('uncertain_or_rejected_mutation_requires_resolution_no_blind_replay')
                break
            if 'session_rotation_requires_host_requalification' in value['gaps']:
                value['status'] = 'blocked'; break
            op = next_requested(value)
            try:
                selected = operation_spec(r, op, value); require_state(value, selected)
            except (ValueError, TypeError, KeyError):
                value['status'] = 'blocked'
                if 'required_instance_state_unresolved' not in value['gaps']: value['gaps'].append('required_instance_state_unresolved')
                break
            moment = now(); prior = [x for x in value['operations'] if x['key'] == op['operation_id']]
            base_bytes = sum(p['bytes'] for p in file_pins(value)) - sum(x['file']['bytes'] for x in value['responses'])
            maximum = min(r['max_response_bytes'], r['max_total_bytes'] - base_bytes - value['network_bytes'])
            if (count >= r['max_requests_per_invocation'] or value['request_count'] >= r['max_total_requests']
                or len(prior) >= r['max_attempts_per_operation'] or maximum <= 0 or moment < value['retry_not_before_epoch']
                or moment - value['created_at_epoch'] >= r['max_elapsed_seconds']): break
            record = {'key': op['operation_id'], **{k: selected[k] for k in ('phase', 'scope', 'method')},
                'fingerprint_sha256': sha(fingerprint(r, selected)), 'started_at_epoch': moment, 'status': 'pending', 'dispatched': False}
            value['operations'].append(record); value['request_count'] += 1; count += 1
            _execution_state(value); latest = advance(root, value)
            try:
                grant = authority(selected['scope'], copy.deepcopy(fingerprint(r, selected)))
                need(type(grant) is dict and set(grant) == {'X-MSTR-AuthToken', 'Cookie', 'X-MSTR-ProjectID'}
                     and text(grant['X-MSTR-AuthToken'], 8192) and text(grant['Cookie'], 16384)
                     and all(re.fullmatch(r'[A-Za-z0-9_.-]+=[^;\r\n]+', part.strip()) for part in grant['Cookie'].split(';'))
                     and grant['X-MSTR-ProjectID'] == r['identity']['project_id'],
                     'microstrategy.host_session_required')
            except Exception:
                record['status'] = 'denied'; value['gaps'].append('host_authority_rejected_no_dispatch'); latest = advance(root, value)
                raise F.CaptureError('microstrategy.host_authority_rejected') from None
            record['dispatched'] = True; _execution_state(value); latest = advance(root, value)
            try:
                status, headers, raw = transport(selected['method'], selected['url'],
                    {'Accept': 'application/json,application/pdf', 'Content-Type': 'application/json', **grant},
                    encoded(selected['body']) if selected['body'] is not None else None, maximum,
                    min(20, r['max_elapsed_seconds'] - (moment - value['created_at_epoch'])))
                need(type(status) is int and type(headers) is dict and type(raw) is bytes and len(raw) <= maximum, 'microstrategy.transport_contract')
                record.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw)); value['network_bytes'] += len(raw)
                screen_granted_echo(raw, grant)
                if any(k.lower() in ('set-cookie', 'x-mstr-authtoken') for k in headers):
                    value['gaps'].append('session_rotation_requires_host_requalification')
                    raise F.CaptureError('microstrategy.session_rotation_requires_host_requalification')
                need(not 300 <= status < 400, 'microstrategy.redirect_rejected')
                if status != expected_status(selected):
                    record['status'] = 'rejected' if 400 <= status < 500 else 'uncertain'
                    if status == 429: value['retry_not_before_epoch'] = max(value['retry_not_before_epoch'], moment + 60)
                    value['gaps'].append('source_http_failure_redacted'); latest = advance(root, value); break
                if selected['phase'] == 'pdf':
                    screen_granted_echo(pdf_bytes(raw), grant)
                inspection = inspect_response(raw, r, op, selected, value)
                pin = F.write_once(root, 'response-%06d.bin' % (len(value['operations']) - 1), raw)
                value['responses'].append({'attempt': len(value['operations']) - 1, 'file': pin, 'inspection': inspection})
                record['status'] = 'success'; latest = advance(root, value)
            except Exception:
                record['status'] = 'uncertain'; value['gaps'].append('source_response_uncertain_redacted')
                latest = advance(root, value); break
        if next_requested(value) is None:
            value['status'] = 'acquired_requested_operations'
        elif any(o['method'] != 'GET' and o['status'] in ('pending', 'uncertain', 'rejected') for o in value['operations']) \
                or 'session_rotation_requires_host_requalification' in value['gaps']:
            value['status'] = 'blocked'
        return result(advance(root, value))
    finally:
        os.close(fd)


run_capture = capture


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    local = sub.add_parser('import-local')
    for name in ('request', 'source-root', 'directory'):
        local.add_argument('--' + name, required=True, type=Path)
    local.add_argument('--allow-source-read', action='store_true')
    evidence = sub.add_parser('import-evidence')
    for name in ('capture', 'spec', 'source-root'):
        evidence.add_argument('--' + name, required=True, type=Path)
    check = sub.add_parser('check'); check.add_argument('--capture', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-local':
            out = import_local(F.decode(F.read_file(args.request)), args.source_root, args.directory, allow_source_read=args.allow_source_read)
        elif args.command == 'import-evidence':
            out = import_evidence(args.capture, F.decode(F.read_file(args.spec)), args.source_root)
        else:
            out = check_capture(args.capture)
        print(encoded({'status': out['status'], 'native_validation': 'not_performed',
                       **({'journal': Path(out['output']).name} if 'output' in out else {})}).decode())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        print('MicroStrategy capture rejected; review scoped evidence and authority.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
