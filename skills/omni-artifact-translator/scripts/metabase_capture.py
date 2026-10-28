#!/usr/bin/env python3
"""Scoped Metabase evidence capture; standard library and passive first-party IO.

No source writes, catalog dump, ad-hoc SQL, YAML interpretation or browser. REST
execution requires a host-injected authority for the exact request fingerprint.
Supplied MCP responses remain separately typed original evidence, never silently
promoted to REST observations. Declarations and hashes do not authenticate them.
"""
from __future__ import annotations

import argparse
import copy
import csv
import fcntl
import importlib.util
import io
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

_spec = importlib.util.spec_from_file_location('metabase_passive_files', Path(__file__).with_name('powerbi_capture_files.py'))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST_SCHEMA = 'metabase-visual-capture-request.v1'
SCHEMA = 'metabase-visual-capture.v1'
SNAPSHOT_SCHEMA = 'metabase-api-snapshot.v1'
MAX_JOURNAL = 64000000
BASE_GAPS = ['identity_version_and_principal_supplied_not_authenticated', 'effective_access_not_verified',
             'requested_state_is_not_observed_state', 'source_export_completeness_not_established',
             'source_python_r_and_serialization_not_executed', 'native_rendered_and_business_acceptance_not_assessed']


def text(value, maximum=1000):
    return type(value) is str and 0 < len(value) <= maximum and all(ord(c) >= 32 for c in value)


def local_id(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value) is not None


def identity(value):
    return type(value) is int and 0 < value <= 2**53 - 1


def digest(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def secret_check(value):
    """Reject structured credentials; preserve approved redaction markers only.

This is not a general secret scanner for arbitrary SQL/text/result values.
"""
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, val in item.items():
                normalized = re.sub('[^a-z]', '', key.lower())
                if normalized in {'password', 'passwd', 'pwd', 'dbpassword', 'accesstoken', 'refreshtoken',
                                  'clientsecret', 'authorization', 'apikey', 'xapikey', 'xmetabasesession',
                                  'sessiontoken', 'credentials', 'privatekey', 'secretkey', 'tunnelprivatekey',
                                  'tunnelpass', 'tunnelpassword', 'sslkey', 'sslkeyvalue'}:
                    need(val in (None, '', '[REDACTED]', '**MetabasePass**') or val == {'redacted': 'secret'},
                         'metabase.credential_bearing_input')
                stack.append(val)
        elif type(item) is list:
            stack.extend(item)


def origin(value):
    need(text(value, 512), 'metabase.https_origin_required')
    p = urlsplit(value)
    need(p.scheme == 'https' and p.hostname and not p.username and not p.password and not p.path
         and not p.query and not p.fragment and p.port in (None, 443)
         and value == 'https://' + p.netloc and re.fullmatch(r'[A-Za-z0-9.-]+(?::443)?', p.netloc),
         'metabase.https_origin_required')
    return value


def validate_state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'timezone', 'locale', 'principal', 'reference'}
         and type(value['filters']) is dict and type(value['parameters']) is list
         and len(value['filters']) <= 100 and len(value['parameters']) <= 100
         and text(value['reference']), 'metabase.state_contract')
    for key in ('timezone', 'locale', 'principal'):
        need(value[key] is None or text(value[key]), 'metabase.state_context')
    F.decode(encoded(value))
    secret_check(value)


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'source_origin', 'version', 'dashboard_id', 'principal_ref',
        'authorization_ref', 'credential_ref', 'evidence_mode', 'api_contract', 'route', 'route_reference',
        'target_surface', 'state', 'snapshot_path', 'originals_path', 'card_ids', 'metadata', 'queries'}
    defaults = {'max_requests_per_invocation': 20, 'max_total_requests': 500, 'max_total_bytes': 64000000,
                'max_response_bytes': 8000000, 'max_elapsed_seconds': 21600, 'max_attempts_per_operation': 3}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value.get('schema_version') == REQUEST_SCHEMA, 'metabase.request_contract')
    r = {**defaults, **copy.deepcopy(value)}
    origin(r['source_origin'])
    need(local_id(r['capture_id']) and identity(r['dashboard_id']) and text(r['version']), 'metabase.request_identity')
    need(all(text(r[k]) for k in ('principal_ref', 'authorization_ref')), 'metabase.review_references')
    need(r['credential_ref'] is None or text(r['credential_ref']), 'metabase.credential_ref')
    need(not require_service or r['credential_ref'] is not None, 'metabase.host_credential_ref_required')
    contract = r['api_contract']
    need(type(contract) is dict and set(contract) == {'reference', 'version', 'auth_header'}
         and text(contract['reference']) and contract['version'] == r['version']
         and contract['auth_header'] in ('x-api-key', 'X-Metabase-Session'), 'metabase.api_contract')
    need(r['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant'), 'metabase.evidence_mode')
    need(r['route'] in ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
         and (r['route'] == 'unselected' or text(r['route_reference'])), 'metabase.route')
    need(r['target_surface'] in ('app', 'dashboard', 'both'), 'metabase.target_surface')
    validate_state(r['state'])
    for key in ('snapshot_path', 'originals_path'):
        F.source_path(r[key])
    need(r['snapshot_path'] != r['originals_path'], 'metabase.distinct_intake_files')
    need(type(r['card_ids']) is list and len(r['card_ids']) <= 200
         and all(identity(x) for x in r['card_ids']) and len(set(r['card_ids'])) == len(r['card_ids']), 'metabase.card_scope')
    need(type(r['metadata']) is list and len(r['metadata']) <= 200, 'metabase.metadata_scope')
    seen = set()
    for row in r['metadata']:
        need(type(row) is dict and set(row) == {'kind', 'id'} and row['kind'] in ('database', 'table', 'field')
             and identity(row['id']) and (row['kind'], row['id']) not in seen, 'metabase.metadata_scope')
        seen.add((row['kind'], row['id']))
    need(type(r['queries']) is list and len(r['queries']) <= 50, 'metabase.query_scope')
    seen = set()
    for row in r['queries']:
        need(type(row) is dict and set(row) == {'query_id', 'card_id', 'body', 'definition_sha256', 'read_only_reference'}
             and local_id(row['query_id']) and row['query_id'] not in seen and identity(row['card_id'])
             and row['card_id'] in r['card_ids'] and digest(row['definition_sha256'])
             and text(row['read_only_reference']), 'metabase.saved_query_scope')
        body = row['body']
        need(type(body) is dict and {'parameters'} <= set(body) <= {'parameters', 'ignore_cache'}
             and type(body['parameters']) is list and len(body['parameters']) <= 100
             and ('ignore_cache' not in body or type(body['ignore_cache']) is bool), 'metabase.saved_query_body')
        # No arbitrary query, SQL, dataset or write/action endpoint is accepted.
        for parameter in body['parameters']:
            need(type(parameter) is dict and {'type', 'target', 'value'} <= set(parameter) <= {'type', 'target', 'value', 'id'}
                 and text(parameter['type']) and type(parameter['target']) is list, 'metabase.query_parameter')
        seen.add(row['query_id'])
    for key, low, high in [('max_requests_per_invocation', 1, 100), ('max_total_requests', 1, 2000),
            ('max_total_bytes', 1, 128000000), ('max_response_bytes', 1, F.MAX_FILE),
            ('max_elapsed_seconds', 1, 86400), ('max_attempts_per_operation', 1, 5)]:
        need(type(r[key]) is int and low <= r[key] <= high, 'metabase.budget')
    F.decode(encoded(r))
    secret_check(r)
    return r


def card_references(dashboard, cards=()):
    ids = set()
    for row in dashboard.get('dashcards', []):
        for candidate in [row.get('card_id'), (row.get('card') or {}).get('id')]:
            if identity(candidate):
                ids.add(candidate)
        for series in row.get('series', []):
            if type(series) is dict and identity(series.get('id')):
                ids.add(series['id'])
    for card in cards:
        stack = [card.get('dataset_query')]
        while stack:
            item = stack.pop()
            if type(item) is str and re.fullmatch(r'card__[1-9][0-9]*', item):
                ids.add(int(item[6:]))
            elif type(item) is dict:
                if 'source-card' in item:
                    need(identity(item['source-card']), 'metabase.source_card_reference')
                    ids.add(item['source-card'])
                if item.get('type') == 'card' and 'card-id' in item:
                    need(identity(item['card-id']), 'metabase.native_card_reference')
                    ids.add(item['card-id'])
                stack.extend(item.values())
            elif type(item) is list:
                stack.extend(item)
    return ids


def validate_snapshot(value, request=None):
    F.decode(encoded(value))  # Bound structure before walking arbitrary nested source configuration.
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'dashboard', 'cards', 'metadata', 'coverage', 'gaps'}
         and value['schema_version'] == SNAPSHOT_SCHEMA, 'metabase.snapshot_contract')
    ident = value['identity']
    need(type(ident) is dict and set(ident) == {'source_origin', 'version', 'principal_ref'}
         and text(ident['version']) and text(ident['principal_ref']), 'metabase.snapshot_identity')
    origin(ident['source_origin'])
    dashboard, cards, metadata = value['dashboard'], value['cards'], value['metadata']
    need(type(dashboard) is dict and identity(dashboard.get('id')), 'metabase.dashboard_identity')
    need(type(cards) is list and len(cards) <= 200 and type(metadata) is list and len(metadata) <= 200,
         'metabase.snapshot_bounds')
    coverage = value['coverage']
    need(type(coverage) is dict and set(coverage) == {'dashboard', 'cards', 'metadata', 'reference'}
         and all(coverage[k] in ('complete', 'partial') for k in ('dashboard', 'cards', 'metadata'))
         and text(coverage['reference']) and type(value['gaps']) is list and len(value['gaps']) <= 1000
         and all(text(g) for g in value['gaps']), 'metabase.snapshot_coverage')
    for key in ('tabs', 'dashcards', 'parameters'):
        need(key not in dashboard or (type(dashboard[key]) is list and len(dashboard[key]) <= 2000), 'metabase.dashboard_collection')
        need(coverage['dashboard'] != 'complete' or key in dashboard, 'metabase.dashboard_completeness')
    tab_ids, dash_ids, card_ids = set(), set(), set()
    def parameters(rows, require_ids=True):
        need(type(rows) is list and len(rows) <= 2000, 'metabase.parameters_collection')
        ids = set()
        for p in rows:
            need(type(p) is dict and p, 'metabase.parameter_record')
            if require_ids or 'id' in p:
                need((text(p.get('id'), 200) or identity(p.get('id'))) and str(p['id']) not in ids,
                     'metabase.parameter_identity')
                ids.add(str(p['id']))
    parameters(dashboard.get('parameters', []))
    for tab in dashboard.get('tabs', []):
        need(type(tab) is dict and identity(tab.get('id')) and tab['id'] not in tab_ids, 'metabase.tab_identity')
        tab_ids.add(tab['id'])
    for card in cards:
        need(type(card) is dict and identity(card.get('id')) and card['id'] not in card_ids, 'metabase.card_identity')
        card_ids.add(card['id'])
        parameters(card.get('parameters', []), require_ids=False)
        need(type(card.get('visualization_settings', {})) is dict, 'metabase.card_visualization_settings')
    card_index = {c['id']: c for c in cards}
    for row in dashboard.get('dashcards', []):
        need(type(row) is dict and identity(row.get('id')) and row['id'] not in dash_ids, 'metabase.dashcard_identity')
        dash_ids.add(row['id'])
        need(row.get('card_id') is None or identity(row['card_id']), 'metabase.dashcard_card_id')
        tab = row.get('dashboard_tab_id')
        need(tab is None or (identity(tab) and (tab in tab_ids or coverage['dashboard'] == 'partial')), 'metabase.dangling_tab')
        embedded = row.get('card')
        need(embedded is None or (type(embedded) is dict and identity(embedded.get('id'))), 'metabase.embedded_card')
        if embedded:
            need(row.get('card_id') in (None, embedded['id']), 'metabase.embedded_card_identity_conflict')
        need(type(row.get('series', [])) is list and len(row.get('series', [])) <= 100, 'metabase.series_collection')
        need(type(row.get('visualization_settings', {})) is dict
             and type(row.get('parameter_mappings', [])) is list
             and all(type(p) is dict and p for p in row.get('parameter_mappings', [])), 'metabase.placement_configuration')
        settings = row.get('visualization_settings', {})
        need('virtual_card' not in settings or type(settings['virtual_card']) is dict, 'metabase.virtual_card')
        series_ids = set()
        for series in row.get('series', []):
            need(type(series) is dict and identity(series.get('id')) and series['id'] not in series_ids,
                 'metabase.series_identity')
            series_ids.add(series['id'])
        for candidate in ([embedded] if embedded else []) + row.get('series', []):
            need(type(candidate) is dict and identity(candidate.get('id')), 'metabase.series_identity')
            full = card_index.get(candidate['id'])
            # A partial embedded card is allowed; conflicting retained fields are not silently merged.
            if full is not None:
                need(all(candidate[k] == full[k] for k in set(candidate) & set(full)), 'metabase.card_revision_conflict')
    references = card_references(dashboard, cards)
    need(coverage['cards'] != 'complete' or references <= card_ids, 'metabase.missing_card_dependencies')
    # Supplied card lists cannot expand into an unrelated catalog inventory.
    reachable, pending = card_references(dashboard), dict(card_index)
    while pending:
        current = set(pending) & reachable
        if not current:
            break
        reachable.update(card_references({}, [pending.pop(k) for k in current]))
    need(not pending, 'metabase.unscoped_card_dependency')
    meta_ids = set()
    for row in metadata:
        need(type(row) is dict and set(row) == {'kind', 'id', 'payload'} and row['kind'] in ('database', 'table', 'field')
             and identity(row['id']) and type(row['payload']) is dict and identity(row['payload'].get('id'))
             and row['payload']['id'] == row['id']
             and (row['kind'], row['id']) not in meta_ids, 'metabase.metadata_record')
        meta_ids.add((row['kind'], row['id']))
    if request is not None:
        need(ident == {k: request[k] for k in ident} and dashboard['id'] == request['dashboard_id'], 'metabase.snapshot_request_identity')
        need(card_ids <= set(request['card_ids']) and meta_ids <= {(x['kind'], x['id']) for x in request['metadata']},
             'metabase.snapshot_request_scope')
        if coverage['metadata'] == 'complete':
            need(meta_ids == {(x['kind'], x['id']) for x in request['metadata']}, 'metabase.metadata_completeness')
    F.decode(encoded(value))
    secret_check(value)
    return value


def pointer(value, path):
    need(type(path) is str and (path == '' or path.startswith('/')) and len(path) <= 1000, 'metabase.json_pointer')
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(part in value, 'metabase.json_pointer_missing')
            value = value[part]
        elif type(value) is list:
            need(part.isdigit() and str(int(part)) == part and int(part) < len(value), 'metabase.json_pointer_missing')
            value = value[int(part)]
        else:
            raise F.CaptureError('metabase.json_pointer_missing')
    return value


def validate_originals(value, snapshot):
    need(type(value) is dict and set(value) == {'schema_version', 'records'} and value['schema_version'] == 'metabase-originals.v1'
         and type(value['records']) is list and 1 <= len(value['records']) <= 500, 'metabase.originals_contract')
    targets = set()
    expected = {'/dashboard'} | {'/cards/%d' % i for i in range(len(snapshot['cards']))} | {
        '/metadata/%d/payload' % i for i in range(len(snapshot['metadata']))}
    for row in value['records']:
        need(type(row) is dict and set(row) == {'source_path', 'source_kind', 'source_pointer', 'target_pointer',
             'mapping', 'reference', 'tool_name', 'tool_call_id'} and text(row['reference']), 'metabase.original_record')
        F.source_path(row['source_path'])
        # One original REST/MCP response may evidence several explicitly mapped
        # objects. Each mapping is preserved, with a distinct immutable byte pin.
        need(row['source_kind'] in ('rest_response', 'mcp_tool_response', 'serialization_yaml'), 'metabase.original_source_kind')
        if row['source_kind'] == 'serialization_yaml':
            need(row['mapping'] == 'inert_unsupported' and row['target_pointer'] is None and row['source_pointer'] is None,
                 'metabase.serialization_not_interpreted')
        else:
            need(row['target_pointer'] in expected and row['target_pointer'] not in targets
                 and type(row['source_pointer']) is str and row['mapping'] in ('exact_json', 'explicit_normalized'),
                 'metabase.original_target_binding')
            targets.add(row['target_pointer'])
            if row['source_kind'] == 'rest_response':
                need(row['mapping'] == 'exact_json' and row['tool_name'] is None and row['tool_call_id'] is None,
                     'metabase.rest_original_exact')
            else:
                need(text(row['tool_name']) and text(row['tool_call_id']) and
                     all(snapshot['coverage'][k] == 'partial' for k in ('dashboard', 'cards', 'metadata')),
                     'metabase.mcp_provenance_or_partial_coverage_required')
    need(targets == expected, 'metabase.original_object_denominator')
    secret_check(value)
    return value


def validate_original_bytes(row, raw, snapshot):
    if row['source_kind'] == 'serialization_yaml':
        # Bytes are retained without loading yaml, pickle, Python, R or tags.
        F.safe_text(raw)
        return
    data = F.decode(raw)
    secret_check(data)
    original = pointer(data, row['source_pointer'])
    target = pointer(snapshot, row['target_pointer'])
    if row['mapping'] == 'exact_json':
        need(original == target, 'metabase.original_payload_mismatch')
    else:
        need(row['source_kind'] == 'mcp_tool_response', 'metabase.normalization_requires_mcp_crosswalk')
        # An explicit supplied normalization reference is retained, never certified.
        need(original is not None and row['reference'], 'metabase.mcp_normalization_evidence')


def file_pins(value):
    source = value['source']
    return ([source['snapshot_file']] if source.get('snapshot_file') else []) + \
        ([source['originals_manifest_file']] if source.get('originals_manifest_file') else []) + \
        [row['file'] for row in source['originals']] + value['attachments']


def definition_fingerprint(snapshot):
    return sha(snapshot)


def retained_bytes(root):
    paths = [p for p in Path(root).iterdir() if p.name != '.capture.lock' and not re.fullmatch(r'capture-[0-9]{6}\.json', p.name)]
    need(len(paths) <= 2000, 'metabase.retained_file_limit')
    for path in paths:
        need(F.no_links(path).is_file(), 'metabase.retained_regular_file_required')
    return sum(p.stat().st_size for p in paths)


def store(root, name, raw, request):
    need(len(raw) <= F.MAX_FILE and retained_bytes(root) + len(raw) <= request['max_total_bytes'],
         'metabase.retained_byte_limit')
    return F.write_once(root, name, raw)


def _save(root, value):
    value['saved_query_execution'] = ('attempted' if any(o['operation'] == 'query' for o in value['operations'])
                                    else 'not_run' if value['request']['queries'] else 'not_requested')
    value['journal_revision'] += 1
    value.pop('content_hash', None)
    value['content_hash'] = sha(value)
    raw = encoded(value)
    paths = list(root.glob('capture-*.json'))
    need(len(paths) < 3000 and sum(F.no_links(p).stat().st_size for p in paths) + len(raw) <= MAX_JOURNAL,
         'metabase.journal_budget')
    file = F.write_once(root, 'capture-%06d.json' % value['journal_revision'], raw)
    value['previous_capture'] = {'path': file['path'], 'sha256': file['sha256']}
    return root / file['path']


def _new(request):
    return {'schema_version': SCHEMA, 'capture_id': request['capture_id'], 'request': request, 'request_sha256': sha(request),
        'source': {'snapshot': None, 'snapshot_file': None, 'definition_fingerprint': None,
                   'originals': [], 'originals_manifest': None, 'originals_manifest_file': None},
        'attachments': [], 'operations': [], 'journal_revision': 0, 'previous_capture': None,
        'created_at_epoch': time.time(), 'request_count': 0, 'network_bytes': 0, 'retry_not_before_epoch': 0,
        'status': 'partial', 'gaps': list(BASE_GAPS), 'target_write_authority': False, 'arbitrary_source_code_execution': False,
        'saved_query_execution': 'not_run' if request['queries'] else 'not_requested',
        'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}


def result(path, value):
    # Return the sealed on-disk state, not the in-memory next-journal pointer.
    return {'status': value['status'], 'output': str(path), 'capture': F.decode(F.read_file(path, F.MAX_JSON))}


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read, 'metabase.source_read_grant_required')
    r = validate_request(request)
    root, supplied = F.private_directory(directory), F.no_links(source_root)
    need(supplied.is_dir() and not list(root.iterdir()), 'metabase.new_capture_directory_required')
    raw_snapshot = F.read_file(supplied / r['snapshot_path'])
    snapshot = validate_snapshot(F.decode(raw_snapshot), r)
    raw_manifest = F.read_file(supplied / r['originals_path'])
    manifest = validate_originals(F.decode(raw_manifest), snapshot)
    pending, total = [], len(raw_snapshot) + len(raw_manifest)
    for row in manifest['records']:
        raw = F.read_file(supplied / row['source_path'])
        validate_original_bytes(row, raw, snapshot)
        total += len(raw)
        need(total <= min(F.MAX_TOTAL, r['max_total_bytes']), 'metabase.source_byte_limit')
        pending.append((row, raw))
    value = _new(r)
    source = value['source']
    source.update(snapshot=snapshot, snapshot_file=store(root, 'snapshot-original.json', raw_snapshot, r),
                  definition_fingerprint=definition_fingerprint(snapshot), originals_manifest=manifest,
                  originals_manifest_file=store(root, 'originals-manifest.json', raw_manifest, r))
    for i, (row, raw) in enumerate(pending):
        source['originals'].append({**copy.deepcopy(row), 'file': store(root, 'original-%04d.bin' % i, raw, r),
                                    'acquisition': 'supplied', 'operation_key': None})
        if row['source_kind'] == 'mcp_tool_response':
            value['gaps'].append('mcp_normalization_supplied_not_rest_observation')
        elif row['source_kind'] == 'serialization_yaml':
            value['gaps'].append('serialization_yaml_inert_unsupported')
    return result(_save(root, value), value)


def inspect_attachment(raw, format):
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'metabase.attachment_bytes')
    if format == 'png':
        return F.png_info(raw)
    if format == 'pdf':
        need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'metabase.pdf_signature')
        return {'validation': 'signature_only_not_rendered'}
    if format == 'json':
        data = F.decode(raw)
        secret_check(data)
        # A successful execution status is not an export-completeness proof.
        count = len(data) if type(data) is list else None
        if type(data) is dict and type(data.get('data')) is dict and type(data['data'].get('rows')) is list:
            count = len(data['data']['rows'])
        need(count is None or count <= 100000, 'metabase.result_row_limit')
        containers = [data] if type(data) is dict else []
        if type(data) is dict and type(data.get('data')) is dict:
            containers.append(data['data'])
        incomplete = any(c.get('status') in ('failed', 'error', 'cancelled', 'canceled', 'running')
                         or bool(c.get('error')) or any(c.get(k) is True for k in ('rows_truncated', 'truncated'))
                         for c in containers)
        declared_counts = [c['row_count'] for c in containers if type(c.get('row_count')) is int]
        if count is not None:
            incomplete = incomplete or any(n != count for n in declared_counts)
        return {'row_count': count, 'explicit_incomplete': incomplete, 'validation': 'json_structure_only'}
    need(format == 'csv', 'metabase.attachment_format')
    try:
        value = raw.decode('utf-8-sig')
        need('\x00' not in value, 'metabase.csv_encoding')
        reader = csv.reader(io.StringIO(value), strict=True)
        headers = next(reader)
        need(1 <= len(headers) <= 1000, 'metabase.csv_headers')
        count = 0
        for row in reader:
            count += 1
            need(count <= 100000 and len(row) == len(headers), 'metabase.csv_rows')
        return {'row_count': count, 'headers': headers}
    except (UnicodeError, csv.Error, StopIteration):
        raise F.CaptureError('metabase.csv_invalid') from None


def object_keys(snapshot):
    dashboard = snapshot['dashboard']
    return {'dashboard:%d' % dashboard['id']} | {'card:%d' % c['id'] for c in snapshot['cards']} | \
        {'dashcard:%d' % c['id'] for c in dashboard.get('dashcards', [])} | \
        {'tab:%d' % t['id'] for t in dashboard.get('tabs', [])} | \
        {'parameter:' + str(p['id']) for p in dashboard.get('parameters', []) if type(p) is dict and p.get('id') is not None}


def validate_attachment(row, request, snapshot):
    required = {'attachment_id', 'object_key', 'card_id', 'dashcard_id', 'tab_id', 'format', 'origin', 'result_scope',
                'observed_state', 'population', 'freshness', 'completeness', 'reference'}
    derived = {'source_path', 'path', 'sha256', 'bytes', 'request_sha256', 'definition_fingerprint',
               'requested_state_sha256', 'inspection', 'acquisition', 'query_id', 'query_fingerprint', 'operation_key'}
    need(type(row) is dict and required <= set(row) <= required | derived and local_id(row['attachment_id'])
         and row['object_key'] in object_keys(snapshot) and row['format'] in ('png', 'pdf', 'csv', 'json')
         and text(row['reference']), 'metabase.attachment_contract')
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown')
         and row['result_scope'] in ('query_result', 'displayed', 'transformed', 'unknown'), 'metabase.result_origin')
    need(not (row['origin'] in ('displayed', 'transformed') and row['result_scope'] != row['origin']), 'metabase.result_origin_conflict')
    cards = {c['id'] for c in snapshot['cards']}
    dashcards = {c['id']: c for c in snapshot['dashboard'].get('dashcards', [])}
    tabs = {t['id'] for t in snapshot['dashboard'].get('tabs', [])}
    need(row['card_id'] is None or (identity(row['card_id']) and row['card_id'] in cards), 'metabase.attachment_card')
    need(row['dashcard_id'] is None or (identity(row['dashcard_id']) and row['dashcard_id'] in dashcards), 'metabase.attachment_dashcard')
    need(row['tab_id'] is None or (identity(row['tab_id']) and row['tab_id'] in tabs), 'metabase.attachment_tab')
    if row['object_key'].startswith('card:'):
        need(row['card_id'] == int(row['object_key'][5:]), 'metabase.attachment_identity')
    if row['object_key'].startswith('dashcard:'):
        need(row['dashcard_id'] == int(row['object_key'][9:]), 'metabase.attachment_identity')
    if row['dashcard_id'] is not None:
        dc = dashcards[row['dashcard_id']]
        refs = card_references({'dashcards': [dc]})
        need(row['card_id'] is None or row['card_id'] in refs, 'metabase.attachment_card_placement')
        need(row['tab_id'] == dc.get('dashboard_tab_id'), 'metabase.attachment_placement_tab')
    obs = row['observed_state']
    need(obs is None or (type(obs) is dict and {'state', 'observed_at', 'reference'} <= set(obs)
         <= {'state', 'observed_at', 'reference', 'placement_reference'}
         and text(obs['observed_at']) and text(obs['reference'])
         and ('placement_reference' not in obs or text(obs['placement_reference']))), 'metabase.observed_state')
    if obs is not None:
        validate_state(obs['state'])
    for key, fields in [('population', {'key', 'description', 'reference'}), ('freshness', {'data_watermark', 'observed_at', 'reference'})]:
        need(type(row[key]) is dict and set(row[key]) == fields
             and all(v is None or text(v) for v in row[key].values()), 'metabase.' + key)
    complete = row['completeness']
    need(type(complete) is dict and set(complete) == {'status', 'reference', 'row_count'}
         and complete['status'] in ('complete', 'partial', 'unknown')
         and (complete['reference'] is None or text(complete['reference']))
         and (complete['row_count'] is None or (type(complete['row_count']) is int and 0 <= complete['row_count'] <= 100000)),
         'metabase.completeness')
    if complete['status'] == 'complete':
        need(row['format'] in ('csv', 'json') and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and obs is not None and all(row['population'].values()) and all(row['freshness'].values())
             and text(complete['reference']) and type(complete['row_count']) is int, 'metabase.complete_evidence_required')
    secret_check(row)


def _load(directory, request=None):
    root = F.private_directory(directory)
    paths = sorted(root.glob('capture-*.json'))
    need(paths and len(paths) <= 3000 and sum(F.no_links(p).stat().st_size for p in paths) <= MAX_JOURNAL,
         'metabase.journal_bound_or_missing')
    previous = None
    for i, path in enumerate(paths, 1):
        need(path.name == 'capture-%06d.json' % i, 'metabase.journal_sequence')
        raw = F.read_file(path, F.MAX_JSON)
        value = validate_envelope(F.decode(raw))
        need(value['previous_capture'] == previous and value['journal_revision'] == i, 'metabase.journal_chain')
        previous = {'path': path.name, 'sha256': F.raw_sha(raw)}
    verify_capture_files(value, root)
    need(request is None or value['request'] == validate_request(request), 'metabase.resume_request_changed')
    value['previous_capture'] = previous
    return value, paths[-1]


def import_evidence(capture_path, spec, source_root):
    path = F.no_links(capture_path)
    root, supplied = F.private_directory(path.parent), F.no_links(source_root)
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        value, latest = _load(root)
        need(path == latest and value['source']['snapshot'] is not None, 'metabase.current_snapshot_required')
        need(type(spec) is dict and set(spec) == {'schema_version', 'attachments'}
             and spec['schema_version'] == 'metabase-supplied-evidence.v1'
             and type(spec['attachments']) is list and len(spec['attachments']) <= 100, 'metabase.evidence_spec')
        seen = {a['attachment_id'] for a in value['attachments']}
        need(len(seen) + len(spec['attachments']) <= 500, 'metabase.attachment_count')
        total, pending = retained_bytes(root), []
        for row in spec['attachments']:
            validate_attachment(row, value['request'], value['source']['snapshot'])
            need('source_path' in row and row['attachment_id'] not in seen, 'metabase.unique_supplied_attachment')
            need(row['attachment_id'] not in {q['query_id'] for q in value['request']['queries']},
                 'metabase.reserved_query_attachment_id')
            seen.add(row['attachment_id'])
            raw = F.read_file(supplied / F.source_path(row['source_path']))
            info = inspect_attachment(raw, row['format'])
            need(row['completeness']['row_count'] is None or info.get('row_count') == row['completeness']['row_count'],
                 'metabase.attachment_row_count')
            need(row['completeness']['status'] != 'complete' or not info.get('explicit_incomplete'),
                 'metabase.result_explicitly_incomplete')
            total += len(raw)
            need(total <= value['request']['max_total_bytes'], 'metabase.total_byte_limit')
            pending.append((row, raw, info))
        for row, raw, info in pending:
            record = {k: copy.deepcopy(v) for k, v in row.items() if k != 'source_path'}
            record.update(store(root, 'attachment-' + row['attachment_id'] + '.' + row['format'], raw, value['request']))
            record.update(request_sha256=value['request_sha256'], definition_fingerprint=value['source']['definition_fingerprint'],
                          requested_state_sha256=sha(value['request']['state']), inspection=info, acquisition='supplied',
                          query_id=None, query_fingerprint=None, operation_key=None)
            value['attachments'].append(record)
        return result(_save(root, value), value)
    finally:
        os.close(fd)


def validate_envelope(value):
    need(type(value) is dict and value.get('schema_version') == SCHEMA
         and value.get('content_hash') == sha({k: v for k, v in value.items() if k != 'content_hash'}), 'metabase.capture_hash_or_schema')
    r = validate_request(value.get('request'))
    need(r == value['request'] and value.get('request_sha256') == sha(r) and value.get('capture_id') == r['capture_id'], 'metabase.capture_request')
    need(value.get('target_write_authority') is False and value.get('arbitrary_source_code_execution') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed', 'metabase.capture_authority')
    source = value.get('source')
    need(type(source) is dict and set(source) == {'snapshot', 'snapshot_file', 'definition_fingerprint',
         'originals', 'originals_manifest', 'originals_manifest_file'}, 'metabase.capture_source')
    snapshot = source['snapshot']
    if snapshot is not None:
        validate_snapshot(snapshot, r)
        need(source['snapshot_file'] is not None and source['definition_fingerprint'] == definition_fingerprint(snapshot),
             'metabase.definition_fingerprint')
    else:
        need(source['snapshot_file'] is None and source['definition_fingerprint'] is None
             and source['originals'] == [], 'metabase.empty_source')
    need(type(source['originals']) is list and len(source['originals']) <= 500, 'metabase.original_count')
    operations = value.get('operations')
    need(type(operations) is list and len(operations) <= r['max_total_requests']
         and type(value.get('request_count')) is int and value['request_count'] == len(operations), 'metabase.operation_budget')
    for op in operations:
        need(type(op) is dict and text(op.get('key')) and op.get('operation') in ('read', 'query')
             and op.get('method') == ('GET' if op['operation'] == 'read' else 'POST')
             and digest(op.get('fingerprint_sha256')) and type(op.get('started_at_epoch')) in (int, float)
             and op.get('status') in ('pending', 'success', 'failed', 'rejected', 'uncertain'), 'metabase.operation_record')
        if 'http_status' in op:
            need(type(op['http_status']) is int and digest(op.get('response_sha256'))
                 and type(op.get('response_bytes')) is int and 0 <= op['response_bytes'] <= r['max_response_bytes'], 'metabase.operation_response')
        if op['status'] == 'success':
            need(op.get('http_status') == 200, 'metabase.operation_success')
    expected_execution = ('attempted' if any(o['operation'] == 'query' for o in operations)
                          else 'not_run' if r['queries'] else 'not_requested')
    need(value.get('saved_query_execution') == expected_execution, 'metabase.saved_query_execution_claim')
    if source['originals_manifest'] is not None:
        need(snapshot is not None and source['originals_manifest_file'] is not None, 'metabase.original_manifest_binding')
        validate_originals(source['originals_manifest'], snapshot)
        supplied = [{k: row[k] for k in source['originals_manifest']['records'][0]} for row in source['originals'] if row['acquisition'] == 'supplied']
        need(supplied == source['originals_manifest']['records'], 'metabase.supplied_originals_binding')
    for original in source['originals']:
        need(original.get('acquisition') in ('supplied', 'rest'), 'metabase.original_acquisition')
        if original['acquisition'] == 'rest':
            targets = {'dashboard.%d' % r['dashboard_id']: '/dashboard'}
            targets.update({'card.%d' % c['id']: '/cards/%d' % i for i, c in enumerate(snapshot['cards'])})
            targets.update({'%s.%d' % (m['kind'], m['id']): '/metadata/%d/payload' % i
                            for i, m in enumerate(snapshot['metadata'])})
            need(original.get('operation_key') in targets and original.get('target_pointer') == targets[original['operation_key']],
                 'metabase.original_identity_binding')
            need(original.get('source_kind') == 'rest_response' and original.get('mapping') == 'exact_json'
                 and original.get('source_pointer') == '' and original.get('tool_name') is None and original.get('tool_call_id') is None
                 and any(op['key'] == original.get('operation_key') and op['status'] == 'success'
                     and op.get('response_sha256') == original['file']['sha256']
                     and op.get('response_bytes') == original['file']['bytes'] for op in operations), 'metabase.original_operation_binding')
    if source['originals_manifest'] is None:
        need(source['originals_manifest_file'] is None and all(o['acquisition'] == 'rest' for o in source['originals']),
             'metabase.original_provenance')
        if snapshot is not None:
            expected = {'/dashboard'} | {'/cards/%d' % i for i in range(len(snapshot['cards']))} | {
                '/metadata/%d/payload' % i for i in range(len(snapshot['metadata']))}
            need(len(source['originals']) == len(expected) and {o['target_pointer'] for o in source['originals']} == expected,
                 'metabase.original_object_denominator')
    need(type(value.get('attachments')) is list and len(value['attachments']) <= 500, 'metabase.attachments')
    ids = set()
    for a in value['attachments']:
        need(snapshot is not None, 'metabase.attachment_without_snapshot')
        validate_attachment(a, r, snapshot)
        need(a['attachment_id'] not in ids and a.get('request_sha256') == value['request_sha256']
             and a.get('requested_state_sha256') == sha(r['state'])
             and a.get('definition_fingerprint') == source['definition_fingerprint']
             and a.get('acquisition') in ('supplied', 'saved_question_query'), 'metabase.attachment_binding')
        ids.add(a['attachment_id'])
        if a['acquisition'] == 'saved_question_query':
            queries = [q for q in r['queries'] if q['query_id'] == a.get('query_id')]
            need(len(queries) == 1 and a['card_id'] == queries[0]['card_id'] and a['object_key'] == 'card:%d' % a['card_id']
                 and a['format'] == 'json' and a['observed_state'] is None and a['completeness']['status'] == 'unknown'
                 and a['query_fingerprint'] == sha(query_operation(r, queries[0])), 'metabase.query_attachment_claim')
            need(any(c['id'] == queries[0]['card_id'] and sha(c) == queries[0]['definition_sha256']
                     for c in snapshot['cards']), 'metabase.query_definition_changed')
            expected = sha({'request_sha256': value['request_sha256'], **query_operation(r, queries[0])})
            need(any(op['key'] == a['operation_key'] and op['status'] == 'success' and op['fingerprint_sha256'] == expected
                 and op.get('response_sha256') == a['sha256'] and op.get('response_bytes') == a['bytes'] for op in operations),
                 'metabase.query_attachment_operation')
    need(type(value.get('network_bytes')) is int and 0 <= value['network_bytes'] <= r['max_total_bytes']
         and type(value.get('journal_revision')) is int and 1 <= value['journal_revision'] <= 3000
         and type(value.get('created_at_epoch')) in (int, float) and type(value.get('retry_not_before_epoch')) in (int, float),
         'metabase.capture_budgets')
    need(value.get('status') in ('partial', 'blocked', 'acquired_requested_operations')
         and type(value.get('gaps')) is list and set(BASE_GAPS) <= set(value['gaps']), 'metabase.capture_status')
    if value['status'] == 'acquired_requested_operations':
        need(snapshot is not None and {c['id'] for c in snapshot['cards']} == set(r['card_ids'])
             and {(x['kind'], x['id']) for x in snapshot['metadata']} == {(x['kind'], x['id']) for x in r['metadata']}
             and {a['query_id'] for a in value['attachments'] if a['acquisition'] == 'saved_question_query'} == {q['query_id'] for q in r['queries']},
             'metabase.false_acquisition_completion')
    seen = set()
    pins = file_pins(value)
    for pin in pins:
        need(type(pin) is dict and type(pin.get('path')) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', pin['path'])
             and pin['path'] not in seen and digest(pin.get('sha256')) and type(pin.get('bytes')) is int
             and 0 <= pin['bytes'] <= F.MAX_FILE, 'metabase.file_pin')
        seen.add(pin['path'])
    need(sum(p['bytes'] for p in pins) <= r['max_total_bytes'], 'metabase.retained_byte_limit')
    return value


def verify_capture_files(value, root):
    validate_envelope(value)
    root = Path(root)
    need(retained_bytes(root) <= value['request']['max_total_bytes'], 'metabase.retained_byte_limit')
    files = {p['path']: F.read_pin(root, p) for p in file_pins(value)}
    source = value['source']
    if source['snapshot'] is not None:
        need(F.decode(files[source['snapshot_file']['path']]) == source['snapshot'], 'metabase.snapshot_original_mismatch')
    if source['originals_manifest'] is not None:
        need(F.decode(files[source['originals_manifest_file']['path']]) == source['originals_manifest'], 'metabase.original_manifest_mismatch')
    for original in source['originals']:
        raw = files[original['file']['path']]
        if source['snapshot'] is not None:
            validate_original_bytes(original, raw, source['snapshot'])
        if original['acquisition'] == 'rest':
            kind, oid = original['operation_key'].split('.')
            expected = sha({'request_sha256': value['request_sha256'], 'method': 'GET',
                            'url': value['request']['source_origin'] + '/api/' + kind + '/' + oid, 'body_sha256': None})
            need(any(op['key'] == original['operation_key'] and op['status'] == 'success' and op['fingerprint_sha256'] == expected
                 and op.get('response_sha256') == original['file']['sha256'] for op in value['operations']), 'metabase.original_route_binding')
    for a in value['attachments']:
        info = inspect_attachment(files[a['path']], a['format'])
        need(info == a['inspection'] and (a['completeness']['row_count'] is None or info.get('row_count') == a['completeness']['row_count']),
             'metabase.attachment_inspection_mismatch')
        need(a['completeness']['status'] != 'complete' or not info.get('explicit_incomplete'),
             'metabase.result_explicitly_incomplete')
    return {'status': 'verified_local_bytes', 'files': {p['path']: p['sha256'] for p in file_pins(value)}, 'native_validation': 'not_performed'}


def check(path):
    path = F.no_links(path)
    if path.is_dir():
        value, latest = _load(path)
        return verify_capture_files(F.decode(F.read_file(latest, F.MAX_JSON)), path)
    return verify_capture_files(F.decode(F.read_file(path, F.MAX_JSON)), path.parent)


check_capture = check


def load_latest(directory, config=None):
    _, path = _load(directory, config)
    return F.decode(F.read_file(path, F.MAX_JSON)), path


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise F.CaptureError('metabase.redirect_rejected')


def default_transport(method, url, headers, body, maximum, timeout):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    start = time.monotonic()
    try:
        response = opener.open(Request(url, data=body, headers=headers, method=method), timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        need(response.geturl() == url and not 300 <= response.code < 400, 'metabase.redirect_rejected')
        chunks, total = [], 0
        while True:
            need(time.monotonic() - start < timeout, 'metabase.response_deadline')
            raw = response.read1(min(65536, maximum + 1 - total))
            if not raw:
                break
            total += len(raw)
            need(total <= maximum, 'metabase.response_byte_limit')
            chunks.append(raw)
        return response.code, dict(response.headers), b''.join(chunks)


def query_operation(request, query):
    return {'method': 'POST', 'url': request['source_origin'] + '/api/card/%d/query' % query['card_id'],
            'body_sha256': sha(query['body'])}


class StopCapture(Exception):
    pass


class Session:
    def __init__(self, root, value, authority, transport, now):
        self.root, self.value, self.authority, self.transport, self.now = root, value, authority, transport, now
        self.count = 0

    def call(self, key, operation, method, path, body=None):
        v, r, now = self.value, self.value['request'], self.now()
        previous = [o for o in v['operations'] if o['key'] == key]
        if (self.count >= r['max_requests_per_invocation'] or v['request_count'] >= r['max_total_requests']
            or len(previous) >= r['max_attempts_per_operation'] or now - v['created_at_epoch'] >= r['max_elapsed_seconds']
            or now < v['retry_not_before_epoch']):
            raise StopCapture()
        if method == 'POST' and any(o['status'] in ('pending', 'success', 'uncertain') for o in previous):
            if 'saved_question_submission_uncertain_no_blind_retry' not in v['gaps']:
                v['gaps'].append('saved_question_submission_uncertain_no_blind_retry')
                _save(self.root, v)
            raise StopCapture()
        allowed = {('/api/dashboard/%d' % r['dashboard_id'], 'GET')} | {('/api/card/%d' % c, 'GET') for c in r['card_ids']} | {
            ('/api/%s/%d' % (m['kind'], m['id']), 'GET') for m in r['metadata']} | {
            ('/api/card/%d/query' % q['card_id'], 'POST') for q in r['queries']}
        need((path, method) in allowed and operation == ('read' if method == 'GET' else 'query'), 'metabase.fixed_operation_scope')
        need((method == 'GET' and body is None) or (method == 'POST' and any(
            path == '/api/card/%d/query' % q['card_id'] and body == q['body'] for q in r['queries'])),
            'metabase.fixed_query_body')
        url = r['source_origin'] + path
        raw_body = None if body is None else encoded(body)
        fp = {'request_sha256': v['request_sha256'], 'method': method, 'url': url,
              'body_sha256': None if raw_body is None else F.raw_sha(raw_body)}
        token = self.authority(operation, fp)
        need(type(token) is str and 0 < len(token) <= 4096 and not any(c in token for c in '\r\n'), 'metabase.host_credential_required')
        headers = {'Accept': 'application/json', r['api_contract']['auth_header']: token}
        if raw_body is not None:
            headers['Content-Type'] = 'application/json'
        op = {'key': key, 'operation': operation, 'method': method, 'fingerprint_sha256': sha(fp),
              'started_at_epoch': now, 'status': 'pending'}
        v['operations'].append(op)
        v['request_count'] += 1
        self.count += 1
        _save(self.root, v)
        try:
            baseline = retained_bytes(self.root)
            maximum = min(r['max_response_bytes'], r['max_total_bytes'] - v['network_bytes'] - baseline)
            need(maximum > 0, 'metabase.byte_budget')
            status, response_headers, raw = self.transport(method, url, headers, raw_body, maximum,
                min(20, r['max_elapsed_seconds'] - (now - v['created_at_epoch'])))
            need(type(status) is int and type(raw) is bytes and len(raw) <= maximum and not 300 <= status < 400,
                 'metabase.response_or_redirect_rejected')
            v['network_bytes'] += len(raw)
            # Safe digest/count survive a credential or malformed-response rejection;
            # unsafe original bytes never reach the evidence directory.
            op.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw))
            need(token.encode() not in raw, 'metabase.credential_echo_rejected')
            if status == 200:
                secret_check(F.decode(raw))  # Reject before an unsafe original is written.
        except Exception:
            op['status'] = 'uncertain' if method == 'POST' else 'failed'
            v['gaps'].append('source_response_failed_or_sensitive_redacted')
            _save(self.root, v)
            raise StopCapture() from None
        op.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw),
                  status='success' if status == 200 else ('uncertain' if method == 'POST' and status >= 500 else 'rejected'))
        if status == 429:
            v['retry_not_before_epoch'] = now + 60
        _save(self.root, v)
        if status != 200:
            raise StopCapture()
        return raw


def _snapshot_update(root, value):
    r, source = value['request'], value['source']
    data = [(o, F.decode(F.read_pin(root, o['file']))) for o in source['originals'] if o['acquisition'] == 'rest']
    dashboards = [payload for row, payload in data if row['operation_key'] == 'dashboard.%d' % r['dashboard_id']]
    if not dashboards:
        return
    cards = [payload for row, payload in data if row['operation_key'].startswith('card.')]
    metadata = [{'kind': row['operation_key'].split('.')[0], 'id': payload['id'], 'payload': payload}
                for row, payload in data if row['operation_key'].split('.')[0] in ('database', 'table', 'field')]
    dash = dashboards[0]
    snapshot = {'schema_version': SNAPSHOT_SCHEMA, 'identity': {k: r[k] for k in ('source_origin', 'version', 'principal_ref')},
        'dashboard': dash, 'cards': cards, 'metadata': metadata, 'coverage': {
            'dashboard': 'complete' if all(type(dash.get(k)) is list for k in ('tabs', 'dashcards', 'parameters')) else 'partial',
            'cards': 'complete' if card_references(dash, cards) <= {c['id'] for c in cards} else 'partial',
            'metadata': 'complete' if {(m['kind'], m['id']) for m in metadata} == {(m['kind'], m['id']) for m in r['metadata']} else 'partial',
            'reference': 'received scoped REST objects only; not atomic data/access coverage'}, 'gaps': []}
    validate_snapshot(snapshot, r)
    need(len(encoded(snapshot)) <= F.MAX_FILE, 'metabase.snapshot_byte_limit')
    for row, payload in data:
        kind = row['operation_key'].split('.')[0]
        if kind == 'dashboard':
            row['target_pointer'] = '/dashboard'
        elif kind == 'card':
            row['target_pointer'] = '/cards/%d' % cards.index(payload)
        else:
            row['target_pointer'] = '/metadata/%d/payload' % next(i for i, m in enumerate(metadata) if m['kind'] == kind and m['id'] == payload['id'])
    source.update(snapshot=snapshot, definition_fingerprint=definition_fingerprint(snapshot),
                  snapshot_file=store(root, 'snapshot-%06d.json' % value['journal_revision'], encoded(snapshot), r))


def capture(request, directory, *, authority=None, transport=None, resume=False, now=None):
    need(callable(authority), 'metabase.host_authority_unconfigured')
    r = validate_request(request, require_service=True)
    root = F.private_directory(directory)
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if resume:
            value, output = _load(root, r)
            need(value['source']['originals_manifest'] is None, 'metabase.connected_run_distinct_from_supplied_snapshot')
        else:
            need({p.name for p in root.iterdir()} == {'.capture.lock'}, 'metabase.new_capture_directory_required')
            value = _new(r)
            if now is not None:
                value['created_at_epoch'] = now()
            output = _save(root, value)
        if value['status'] == 'blocked':
            return result(output, value)
        session = Session(root, value, authority, transport or default_transport, now or time.time)
        def get(kind, oid):
            key = '%s.%d' % (kind, oid)
            if any(o['operation_key'] == key for o in value['source']['originals']):
                return
            raw = session.call(key, 'read', 'GET', '/api/%s/%d' % (kind, oid))
            payload = F.decode(raw)
            need(type(payload) is dict and payload.get('id') == oid, 'metabase.rest_object_identity')
            previous_source = copy.deepcopy(value['source'])
            value['source']['originals'].append({'source_path': key + '.json', 'source_kind': 'rest_response',
                'source_pointer': '', 'target_pointer': None, 'mapping': 'exact_json', 'reference': r['api_contract']['reference'],
                'tool_name': None, 'tool_call_id': None, 'file': store(root, 'response-' + key + '.json', raw, r),
                'acquisition': 'rest', 'operation_key': key})
            try:
                _snapshot_update(root, value)
            except (ValueError, TypeError, KeyError, OSError):
                # Keep the last usable snapshot. The rejected safe response bytes and
                # operation digest remain diagnostic evidence, not a source binding.
                value['source'] = previous_source
                raise
            _save(root, value)
        try:
            get('dashboard', r['dashboard_id'])
            pending = set(r['card_ids']) - {c['id'] for c in value['source']['snapshot']['cards']}
            while pending:
                snapshot = value['source']['snapshot']
                eligible = pending & card_references(snapshot['dashboard'], snapshot['cards'])
                need(eligible, 'metabase.unscoped_card_request')
                for cid in sorted(eligible):
                    get('card', cid)
                    pending.remove(cid)
            for meta in r['metadata']:
                get(meta['kind'], meta['id'])
            for q in r['queries']:
                if any(a.get('query_id') == q['query_id'] for a in value['attachments']):
                    continue
                reviewed = next(c for c in value['source']['snapshot']['cards'] if c['id'] == q['card_id'])
                need(sha(reviewed) == q['definition_sha256'], 'metabase.query_definition_changed')
                raw = session.call('query.' + q['query_id'], 'query', 'POST', '/api/card/%d/query' % q['card_id'], q['body'])
                info = inspect_attachment(raw, 'json')
                pin = store(root, 'query-' + q['query_id'] + '.json', raw, r)
                value['attachments'].append({**pin, 'attachment_id': q['query_id'], 'object_key': 'card:%d' % q['card_id'],
                    'card_id': q['card_id'], 'dashcard_id': None, 'tab_id': None, 'format': 'json', 'origin': 'unknown',
                    'result_scope': 'query_result', 'observed_state': None,
                    'population': {'key': None, 'description': None, 'reference': None},
                    'freshness': {'data_watermark': None, 'observed_at': None, 'reference': None},
                    'completeness': {'status': 'unknown', 'reference': None, 'row_count': info.get('row_count')},
                    'reference': 'scoped saved question execution; dashboard application not established',
                    'request_sha256': value['request_sha256'], 'definition_fingerprint': value['source']['definition_fingerprint'],
                    'requested_state_sha256': sha(r['state']), 'inspection': info, 'acquisition': 'saved_question_query',
                    'query_id': q['query_id'], 'query_fingerprint': sha(query_operation(r, q)), 'operation_key': 'query.' + q['query_id']})
                _save(root, value)
            value['status'] = 'acquired_requested_operations'
            value['gaps'].append('scoped_rest_reads_not_atomic_configuration_or_data_snapshot')
            output = _save(root, value)
        except StopCapture:
            pass
        except (ValueError, TypeError, KeyError, OSError):
            value['status'] = 'blocked'
            value['gaps'].append('source_scope_or_contract_rejected')
            output = _save(root, value)
        output = sorted(root.glob('capture-*.json'))[-1]
        return result(output, value)
    finally:
        os.close(fd)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    local = sub.add_parser('import-local')
    for key in ('request', 'source-root', 'directory'):
        local.add_argument('--' + key, required=True, type=Path)
    local.add_argument('--allow-source-read', action='store_true')
    evidence = sub.add_parser('import-evidence')
    for key in ('capture', 'spec', 'source-root'):
        evidence.add_argument('--' + key, required=True, type=Path)
    checker = sub.add_parser('check')
    checker.add_argument('--capture', required=True, type=Path)
    args = p.parse_args(argv)
    try:
        if args.command == 'import-local':
            out = import_local(F.decode(F.read_file(args.request)), args.source_root, args.directory,
                               allow_source_read=args.allow_source_read)
        elif args.command == 'import-evidence':
            out = import_evidence(args.capture, F.decode(F.read_file(args.spec)), args.source_root)
        else:
            out = check(args.capture)
        print(encoded({'status': out['status'], 'native_validation': 'not_performed'}).decode())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        print('Metabase source capture rejected; review the scoped contract and retained evidence.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
