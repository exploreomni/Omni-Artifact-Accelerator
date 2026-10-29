#!/usr/bin/env python3
"""Bounded ThoughtSpot evidence; passive originals and separately granted POSTs.

No login, TML import, source authoring, sharing, arbitrary search/query text or
native target writes. Local pins establish continuity, never authenticity.
"""
from __future__ import annotations

import argparse
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
    if name not in ('powerbi_capture_files', 'bounded_csv', 'thoughtspot_visual'):
        raise ValueError('thoughtspot.module_rejected')
    path = Path(__file__).with_name(name + '.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('thoughtspot.module_symlink')
    spec = importlib.util.spec_from_file_location('thoughtspot_' + name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


F = module('powerbi_capture_files')
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST = REQUEST_SCHEMA = 'thoughtspot-visual-capture-request.v1'
SCHEMA = ENVELOPE = 'thoughtspot-visual-capture.v1'
MAX_JOURNAL_BYTES = 128000000
BASE_GAPS = ['source_identity_and_authority_references_not_authenticated',
    'independent_inventory_is_declared_scope_not_tenant_completeness',
    'requested_state_is_not_observed_state', 'effective_access_not_verified',
    'native_rendering_and_business_acceptance_not_assessed',
    'connected_enrichment_does_not_replace_imported_snapshot',
    'json_default_page_is_not_export_completeness']


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
    need(text(value, 2048), 'thoughtspot.origin')
    p = urlsplit(value)
    need(p.scheme == 'https' and p.hostname and p.netloc == p.hostname and not p.path and not p.query
         and not p.fragment and not p.username and not p.password
         and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', p.hostname), 'thoughtspot.https_origin_required')
    return value


def screen_text(value):
    F.safe_text(value.encode('utf-8'))
    names = r'(?:password|passwd|pwd|access[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?key|private[_-]?key)'
    need(not re.search(r'(?i)[\"\']?\b' + names + r'\b[\"\']?\s*[=:]\s*[\"\']?[^\s,;\"\'}<>]+', value)
         and not re.search(r'(?is)<\s*' + names + r'\b[^>]*>\s*[^<\s]+', value)
         and not re.search(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{12,}', value),
         'thoughtspot.credential_bearing_text')


def screen_bytes(raw, granted=None):
    if granted:
        # Screen both full Authorization header value and its bearer credential.
        parts = [granted] + ([granted[7:]] if granted.startswith('Bearer ') else [])
        for part in parts:
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                need(part.encode(encoding) not in raw, 'thoughtspot.credential_echo_rejected')
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


def validate_state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'timezone', 'locale', 'principal', 'cache', 'reference'}
         and type(value['filters']) is dict and len(value['filters']) <= 100 and type(value['parameters']) is dict
         and len(value['parameters']) <= 100 and text(value['reference']), 'thoughtspot.state_contract')
    for key in ('timezone', 'locale', 'principal', 'cache'):
        need(value[key] is None or text(value[key]), 'thoughtspot.state_context')
    F.decode(encoded(value)); F.secret_check(value)


state = validate_state


def validate_identity(value):
    need(type(value) is dict and set(value) == {'source_origin', 'org_id', 'product', 'version', 'principal_ref',
         'chart_generation', 'reference'} and native_id(value['org_id']) and value['product'] in ('cloud', 'software')
         and value['chart_generation'] in ('classic', 'new', 'mixed', 'unknown')
         and all(text(value[k]) for k in ('version', 'principal_ref', 'reference')), 'thoughtspot.identity')
    origin(value['source_origin'])


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'identity', 'root', 'authorization_ref', 'credential_ref', 'evidence_mode',
        'route', 'route_reference', 'target_surface', 'state', 'snapshot_path', 'originals_path'}
    defaults = {'api_profile': None, 'operations': [], 'max_requests_per_invocation': 10, 'max_total_requests': 100,
        'max_total_bytes': F.MAX_TOTAL, 'max_response_bytes': F.MAX_FILE, 'max_elapsed_seconds': 21600,
        'max_attempts_per_operation': 3}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value.get('schema_version') == REQUEST, 'thoughtspot.request_contract')
    r = {**defaults, **copy.deepcopy(value)}
    need(local_id(r['capture_id']) and text(r['authorization_ref']) and
         (r['credential_ref'] is None or text(r['credential_ref'])), 'thoughtspot.request_identity')
    validate_identity(r['identity'])
    need(type(r['root']) is dict and set(r['root']) == {'kind', 'id'} and r['root']['kind'] in ('liveboard', 'answer')
         and native_id(r['root']['id']), 'thoughtspot.root')
    need(r['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant'), 'thoughtspot.evidence_mode')
    need(r['target_surface'] in ('app', 'dashboard', 'both'), 'thoughtspot.target_surface')
    need(r['route'] in ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
         and (r['route'] == 'unselected' or text(r['route_reference'])), 'thoughtspot.route')
    validate_state(r['state'])
    F.source_path(r['snapshot_path']); F.source_path(r['originals_path'])
    need(r['snapshot_path'] != r['originals_path'], 'thoughtspot.distinct_source_records')
    bounds = {'max_requests_per_invocation': (1, 60), 'max_total_requests': (1, 500), 'max_total_bytes': (1, F.MAX_TOTAL),
        'max_response_bytes': (1, F.MAX_FILE), 'max_elapsed_seconds': (1, 86400), 'max_attempts_per_operation': (1, 5)}
    for key, (lo, hi) in bounds.items():
        need(type(r[key]) is int and lo <= r[key] <= hi, 'thoughtspot.budget')
    need(type(r['operations']) is list and len(r['operations']) <= 100, 'thoughtspot.operation_bound')
    need(r['api_profile'] in (None, 'rest2-cloud-26.10.v1'), 'thoughtspot.unknown_api_profile')
    need(not r['operations'] or (r['api_profile'] == 'rest2-cloud-26.10.v1' and r['identity']['product'] == 'cloud'
         and r['identity']['version'] == '26.10.0.cl'), 'thoughtspot.connected_version_not_qualified')
    seen, bodies = set(), set()
    for op in r['operations']:
        validate_operation(r, op)
        need(op['operation_id'] not in seen, 'thoughtspot.duplicate_operation_id')
        signature = sha({'kind': op['kind'], 'body': op['body']})
        need(signature not in bodies, 'thoughtspot.duplicate_operation_body')
        seen.add(op['operation_id']); bodies.add(signature)
    need(not require_service or (r['credential_ref'] is not None and bool(r['operations'])), 'thoughtspot.host_scope_required')
    F.secret_check(r)
    return r


def _pagination(body, maximum=100000):
    need(type(body.get('record_offset')) is int and 0 <= body['record_offset'] <= 1000000
         and type(body.get('record_size')) is int and 1 <= body['record_size'] <= maximum, 'thoughtspot.bounded_pagination')


def _metadata(body):
    rows = body.get('metadata')
    need(type(rows) is list and 1 <= len(rows) <= 100, 'thoughtspot.explicit_metadata_ids_required')
    seen = set()
    for row in rows:
        need(type(row) is dict and set(row) == {'identifier', 'type'} and native_id(row['identifier'])
             and row['type'] in ('LIVEBOARD', 'ANSWER', 'LOGICAL_TABLE'), 'thoughtspot.metadata_selection')
        key = (row['identifier'], row['type'])
        need(key not in seen, 'thoughtspot.duplicate_metadata_selection'); seen.add(key)


def _overrides(body):
    for name in ('runtime_filter', 'runtime_param_override', 'runtime_sort'):
        if name in body:
            need(type(body[name]) is dict and len(body[name]) <= 100, 'thoughtspot.runtime_override')
            F.decode(encoded(body[name])); F.secret_check(body[name])
    need(len(encoded(body)) <= 65536, 'thoughtspot.operation_body_limit')


def _validate_search(request, body):
    need(set(body) == {'metadata', 'record_offset', 'record_size'}, 'thoughtspot.metadata_search_body')
    _metadata(body); _pagination(body, 1000)


def _validate_tml(request, body):
    need(set(body) == {'metadata', 'export_associated', 'export_fqn', 'edoc_format', 'export_schema_version'}
         and type(body['export_associated']) is bool and body['export_fqn'] is True
         and body['edoc_format'] == 'JSON' and body['export_schema_version'] in ('v1', 'v2'), 'thoughtspot.tml_export_body')
    _metadata(body)


def _validate_data(request, body, liveboard):
    required = {'metadata_identifier', 'data_format', 'record_offset', 'record_size'} | ({'visualization_identifiers'} if liveboard else set())
    need(required <= set(body) <= required | {'runtime_filter', 'runtime_param_override', 'runtime_sort'}
         and native_id(body['metadata_identifier']) and body['data_format'] == 'COMPACT', 'thoughtspot.saved_data_body')
    _pagination(body); _overrides(body)
    if liveboard:
        _identifiers(body['visualization_identifiers'])


def _identifiers(rows):
    need(type(rows) is list and 1 <= len(rows) <= 100 and all(native_id(x) for x in rows)
         and len(set(rows)) == len(rows), 'thoughtspot.explicit_identifier_list')


def _validate_render(request, body, liveboard):
    required = {'metadata_identifier', 'file_format'} | ({'visualization_identifiers'} if liveboard else {'type'})
    optional = {'runtime_filter', 'runtime_param_override', 'runtime_sort'} | ({'tab_identifiers', 'personalised_view_identifier'} if liveboard else set())
    need(required <= set(body) <= required | optional and native_id(body['metadata_identifier'])
         and body['file_format'] in ('PNG', 'PDF'), 'thoughtspot.saved_render_body')
    _overrides(body)
    if liveboard:
        _identifiers(body['visualization_identifiers'])
        if 'tab_identifiers' in body:
            _identifiers(body['tab_identifiers'])
        need(body['file_format'] != 'PNG' or len(body.get('tab_identifiers', [])) == 1,
             'thoughtspot.png_exact_one_tab_required')
        need('personalised_view_identifier' not in body or native_id(body['personalised_view_identifier']), 'thoughtspot.view_identifier')
    else:
        need(body['type'] == 'SAVED', 'thoughtspot.pinned_or_unsaved_answer_not_qualified')


# Fixed documented 26.10 Cloud profiles. Request references cannot add endpoints.
OPERATIONS = {
    'metadata_search': {'scope': 'metadata', 'path': '/api/rest/2.0/metadata/search', 'validate': _validate_search},
    'tml_export': {'scope': 'metadata', 'path': '/api/rest/2.0/metadata/tml/export', 'validate': _validate_tml},
    'liveboard_data': {'scope': 'query', 'path': '/api/rest/2.0/metadata/liveboard/data', 'validate': lambda r, b: _validate_data(r, b, True)},
    'answer_data': {'scope': 'query', 'path': '/api/rest/2.0/metadata/answer/data', 'validate': lambda r, b: _validate_data(r, b, False)},
    'liveboard_render': {'scope': 'render', 'path': '/api/rest/2.0/report/liveboard', 'validate': lambda r, b: _validate_render(r, b, True)},
    'answer_render': {'scope': 'render', 'path': '/api/rest/2.0/report/answer', 'validate': lambda r, b: _validate_render(r, b, False)},
}


def validate_operation(request, op):
    need(type(op) is dict and set(op) == {'operation_id', 'kind', 'body', 'reference'} and local_id(op['operation_id'])
         and op['kind'] in OPERATIONS and type(op['body']) is dict and text(op['reference']), 'thoughtspot.reviewed_operation_required')
    # Profile-specific validation is installed below; no generic POST proxy.
    OPERATIONS[op['kind']]['validate'](request, op['body'])


def operation_spec(config, op):
    r = validate_request(config)
    need(op in r['operations'], 'thoughtspot.operation_not_selected')
    profile = OPERATIONS[op['kind']]
    return {'scope': profile['scope'], 'method': 'POST',
            'url': r['identity']['source_origin'] + profile['path'], 'body': copy.deepcopy(op['body'])}


def validate_operation_scope(request, snapshot):
    visual = module('thoughtspot_visual')
    objects = {(o['kind'], o['id']): o for o in snapshot['objects']}
    indexed = {row['key']: row for row in snapshot['inventory']['items']}
    allowed = [row for row in indexed.values() if row['disposition'] == 'include' and not visual.restricted(row, indexed, objects)]
    def within(row, selected):
        while row is not None:
            if row['native_id'] in selected:
                return True
            row = indexed.get(row['parent_key'])
        return False
    def visualization_guid(row):
        mapping = row['source_mapping']
        if (mapping is None or mapping['object_kind'] != 'liveboard'
            or mapping['object_id'] != snapshot['root']['id']
            or not re.fullmatch(r'/liveboard/visualizations/(0|[1-9][0-9]*)(/answer)?', mapping['pointer'])):
            return None
        # Layout-local IDs such as Viz_1 are not REST selectors. Only the exact
        # retained native viz_guid is qualified; no name or inferred-ID fallback.
        path = mapping['pointer'].removesuffix('/answer')
        node = visual.pointer(objects[('liveboard', mapping['object_id'])]['payload'], path)
        value = node.get('viz_guid') if type(node) is dict else None
        return value if native_id(value) else None
    for op in request['operations']:
        kind, body = op['kind'], op['body']
        if kind in ('metadata_search', 'tml_export'):
            native_types = {'liveboard': 'LIVEBOARD', 'answer': 'ANSWER', 'table': 'LOGICAL_TABLE',
                            'worksheet': 'LOGICAL_TABLE', 'model': 'LOGICAL_TABLE', 'view': 'LOGICAL_TABLE'}
            selected = {(native_types[k], oid) for k, oid in objects if k in native_types}
            need(all((row['type'], row['identifier']) in selected for row in body['metadata']), 'thoughtspot.metadata_outside_imported_scope')
            continue
        target_kind = 'liveboard' if kind.startswith('liveboard_') else 'answer'
        need((target_kind, body['metadata_identifier']) in objects, 'thoughtspot.saved_object_outside_scope')
        if target_kind == 'answer':
            need(any(row['native_id'] == body['metadata_identifier'] and visual.query_node(row, objects)
                 and row['source_mapping']['object_kind'] == 'answer'
                 and row['source_mapping']['object_id'] == body['metadata_identifier']
                 and row['source_mapping']['pointer'] in ('', '/answer') for row in allowed),
                 'thoughtspot.answer_not_selected')
            continue
        need(snapshot['root'] == {'kind': 'liveboard', 'id': body['metadata_identifier']}, 'thoughtspot.liveboard_root_mismatch')
        available = [row for row in allowed if visual.query_node(row, objects) and visualization_guid(row) is not None]
        need(set(body['visualization_identifiers']) <= {visualization_guid(row) for row in available}, 'thoughtspot.note_or_unselected_visualization')
        if 'tab_identifiers' in body:
            tabs = set(body['tab_identifiers'])
            need(tabs <= {row['native_id'] for row in allowed if row['kind'] == 'tab'}, 'thoughtspot.tab_outside_selected_scope')
            for vid in body['visualization_identifiers']:
                keys = {row['key'] for row in available if visualization_guid(row) == vid}
                occurrences = [row for row in allowed if row['key'] in keys or
                    (row['kind'] == 'placement' and row['configuration'].get('visual_key') in keys)]
                need(any(within(row, tabs) for row in occurrences), 'thoughtspot.visualization_outside_selected_tab')
        if 'personalised_view_identifier' in body:
            vid = body['personalised_view_identifier']
            need(any(row['native_id'] == vid and row['kind'] in ('view', 'private_view')
                 and text(row['configuration'].get('selection_reference')) for row in allowed), 'thoughtspot.view_selection_required')


def _execution_state(value):
    requested = {OPERATIONS[op['kind']]['scope'] for op in value['request']['operations']}
    attempted = {op['scope'] for op in value['operations']}
    for scope, field in (('query', 'saved_query_execution'), ('render', 'render_execution')):
        value[field] = 'attempted' if scope in attempted else 'not_run' if scope in requested else 'not_requested'
    value['source_execution'] = bool(attempted & {'query', 'render'})


def pointer(value, path):
    need(type(path) is str and len(path) <= 1000 and (path == '' or path.startswith('/'))
         and re.search(r'~(?![01])', path) is None, 'thoughtspot.json_pointer')
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(part in value, 'thoughtspot.pointer_missing'); value = value[part]
        elif type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', part) is not None and int(part) < len(value), 'thoughtspot.pointer_missing')
            value = value[int(part)]
        else:
            raise F.CaptureError('thoughtspot.pointer_missing')
    return value


def validate_mcp_evidence(value, identity=None):
    keys = {'tool_name', 'tool_call_id', 'session_ref', 'observed_at', 'principal_ref', 'org_id', 'reference', 'capabilities',
            'server_version', 'tool_schema_sha256', 'schema_reference', 'provenance_reference'}
    need(type(value) is dict and set(value) == keys and all(text(value[k]) for k in keys - {'capabilities'})
         and type(value['capabilities']) is list and len(value['capabilities']) <= 100
         and all(text(x) for x in value['capabilities']) and len(set(value['capabilities'])) == len(value['capabilities']),
         'thoughtspot.mcp_evidence')
    need(digest(value['tool_schema_sha256']), 'thoughtspot.mcp_schema_hash')
    if identity is not None:
        need(value['org_id'] == identity['org_id'] and value['principal_ref'] == identity['principal_ref'],
             'thoughtspot.mcp_identity_mismatch')
    F.secret_check(value)
    return value


def validate_originals(manifest, snapshot):
    need(type(manifest) is dict and set(manifest) == {'schema_version', 'reference', 'records'}
         and manifest['schema_version'] == 'thoughtspot-originals.v1' and text(manifest['reference'])
         and type(manifest['records']) is list and 1 <= len(manifest['records']) <= 500, 'thoughtspot.originals_manifest')
    expected = {'/inventory'} | {'/objects/%d/payload' % i for i in range(len(snapshot['objects']))}
    targets, paths, aliases = set(), set(), {}
    for row in manifest['records']:
        need(type(row) is dict and set(row) == {'source_path', 'source_kind', 'source_pointer', 'target_pointer', 'mapping',
             'member_path', 'reference', 'mcp_evidence'} and row['source_kind'] in
             ('rest_json', 'supplied_json', 'mcp_json', 'yaml', 'zip', 'opaque') and text(row['reference'])
             and row['mapping'] in ('exact_json', 'native_json_tml', 'opaque_preserved'), 'thoughtspot.original_record')
        path = F.source_path(row['source_path'])
        folded = unicodedata.normalize('NFC', path).casefold()
        need(folded not in aliases or aliases[folded] == path, 'thoughtspot.original_path_alias')
        need(not any(path != p and (path.startswith(p + '/') or p.startswith(path + '/')) for p in paths),
             'thoughtspot.original_path_collision')
        aliases[folded] = path; paths.add(path)
        if row['member_path'] is not None:
            F.source_path(row['member_path'])
            need(row['source_kind'] == 'zip', 'thoughtspot.member_requires_zip')
        target = row['target_pointer']
        need(target is None or (target in expected and target not in targets), 'thoughtspot.original_target')
        if target is not None:
            targets.add(target)
        if row['mapping'] in ('exact_json', 'native_json_tml'):
            need(row['source_kind'] in ('rest_json', 'supplied_json', 'mcp_json', 'zip') and target is not None
                 and type(row['source_pointer']) is str, 'thoughtspot.exact_json_mapping')
            need(row['mapping'] != 'native_json_tml' or target.startswith('/objects/'), 'thoughtspot.tml_object_only')
        else:
            need(row['source_pointer'] is None and target != '/inventory', 'thoughtspot.opaque_mapping')
        if row['source_kind'] == 'mcp_json':
            validate_mcp_evidence(row['mcp_evidence'], snapshot['identity'])
        else:
            need(row['mcp_evidence'] is None, 'thoughtspot.mcp_kind_mismatch')
    need(targets == expected, 'thoughtspot.original_object_denominator')
    F.secret_check(manifest)
    return manifest


def zip_members(raw):
    """Bounded in-memory inventory; no filesystem extraction or YAML decoding."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            need(1 <= len(entries) <= 500, 'thoughtspot.zip_member_limit')
            members, names, prefixes, total = {}, set(), {}, 0
            for item in entries:
                path = item.filename[:-1] if item.is_dir() else item.filename
                F.source_path(path)
                folded = unicodedata.normalize('NFC', path).casefold()
                need(folded not in names, 'thoughtspot.zip_path_collision'); names.add(folded)
                parts = path.split('/')
                for i in range(1, len(parts) + 1):
                    prefix = '/'.join(parts[:i]); key = unicodedata.normalize('NFC', prefix).casefold()
                    need(key not in prefixes or prefixes[key] == prefix, 'thoughtspot.zip_path_alias'); prefixes[key] = prefix
                mode = item.external_attr >> 16
                need(not item.flag_bits & 1 and item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                     and stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'thoughtspot.zip_unsafe_member')
                if item.is_dir():
                    continue
                total += item.file_size
                need(total <= F.MAX_TOTAL and item.file_size <= F.MAX_FILE
                     and item.file_size <= max(1, item.compress_size) * 100, 'thoughtspot.zip_expansion_limit')
                with archive.open(item) as stream:
                    content = stream.read(F.MAX_FILE + 1)
                need(len(content) == item.file_size <= F.MAX_FILE, 'thoughtspot.zip_size_mismatch')
                suffix = Path(path).suffix.lower()
                screening = screen_bytes(content) if suffix in ('.yaml', '.yml', '.tml', '.json', '.txt', '.csv', '.xml', '.html', '.js') else screen_opaque(content)
                members[path] = {'bytes': len(content), 'sha256': F.raw_sha(content), 'credential_screening': screening, 'raw': content}
            file_names = {unicodedata.normalize('NFC', path).casefold() for path in members}
            need(not any(a != b and a.startswith(b + '/') for a in names for b in file_names), 'thoughtspot.zip_file_directory_collision')
            return members
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        raise F.CaptureError('thoughtspot.invalid_zip') from None


def inspect_original(row, raw, snapshot):
    content = raw
    inspection = {'interpretation': 'inert_bytes', 'source_code_execution': False}
    if row['source_kind'] == 'zip':
        members = zip_members(raw)
        inspection['members'] = [{'path': path, **{k: v for k, v in record.items() if k != 'raw'}} for path, record in members.items()]
        inspection['interpretation'] = 'zip_members_only'
        if row['member_path'] is not None:
            need(row['member_path'] in members, 'thoughtspot.zip_member_missing')
            content = members[row['member_path']]['raw']
        else:
            need(row['mapping'] == 'opaque_preserved' and row['target_pointer'] is None, 'thoughtspot.zip_member_mapping_required')
    elif row['source_kind'] in ('yaml', 'rest_json', 'supplied_json', 'mcp_json'):
        inspection['credential_screening'] = screen_bytes(raw)
    else:
        inspection['credential_screening'] = screen_opaque(raw)
    if row['mapping'] in ('exact_json', 'native_json_tml'):
        original = F.decode(content); F.secret_check(original)
        selected = pointer(original, row['source_pointer'])
        if row['mapping'] == 'native_json_tml':
            need(type(selected) is str, 'thoughtspot.native_json_tml_string_required')
            selected = F.decode(selected.encode('utf-8')); F.secret_check(selected)
            need(type(selected) is dict, 'thoughtspot.native_json_tml_object_required')
        need(selected == pointer(snapshot, row['target_pointer']), 'thoughtspot.original_payload_mismatch')
        inspection['interpretation'] = 'native_json_tml_pointer' if row['mapping'] == 'native_json_tml' else 'exact_json_pointer'
    elif row['target_pointer'] is not None:
        expected = {'opaque_original': {'source_path': row['source_path'], 'member_path': row['member_path'],
                                       'sha256': F.raw_sha(content)}}
        need(pointer(snapshot, row['target_pointer']) == expected, 'thoughtspot.opaque_placeholder_mismatch')
    return inspection


def definition_fingerprint(snapshot):
    return sha(snapshot)


def file_pins(value):
    source = value['source']
    pins = [source['snapshot_file'], source['originals_manifest_file']] + [x['file'] for x in source['originals']] + \
           value['attachments'] + [x['archive_file'] for x in value['attachments'] if x.get('archive_file') is not None] + \
           [r['file'] for r in value['responses']]
    unique = {}
    for pin in pins:
        need(type(pin) is dict and type(pin.get('path')) is str, 'thoughtspot.file_pin')
        need(pin['path'] not in unique or unique[pin['path']] == pin, 'thoughtspot.file_pin_collision')
        unique[pin['path']] = pin
    return list(unique.values())


def _save(root, value):
    value['journal_revision'] += 1
    value.pop('content_hash', None); value['content_hash'] = sha(value)
    raw = encoded(value)
    snapshots = list(root.glob('capture-*.json'))
    need(len(snapshots) < 3000 and len(raw) <= F.MAX_JSON and
         len(raw) + sum(F.no_links(p).stat().st_size for p in snapshots) <= MAX_JOURNAL_BYTES, 'thoughtspot.journal_budget')
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
    module('thoughtspot_visual').validate_snapshot(value)
    if request is not None:
        need(value['identity'] == request['identity'] and value['root'] == request['root'], 'thoughtspot.snapshot_request_identity')
    F.secret_check(value)
    return value


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read is True, 'thoughtspot.source_read_grant_required')
    r = validate_request(request)
    source_root, root = F.no_links(source_root), F.private_directory(directory)
    need(source_root.is_dir() and not list(root.iterdir()), 'thoughtspot.new_directory_required')
    raw_snapshot, raw_manifest = (F.read_file(source_root / r[k]) for k in ('snapshot_path', 'originals_path'))
    snapshot = validate_snapshot(F.decode(raw_snapshot), r)
    manifest = validate_originals(F.decode(raw_manifest), snapshot)
    validate_operation_scope(r, snapshot)
    pending, total, cache, work = [], len(raw_snapshot) + len(raw_manifest), {}, 0
    for row in manifest['records']:
        if row['source_path'] not in cache:
            cache[row['source_path']] = F.read_file(source_root / row['source_path'])
            total += len(cache[row['source_path']])
        raw = cache[row['source_path']]
        work += len(raw)
        need(work <= 128000000, 'thoughtspot.mapping_work_limit')
        info = inspect_original(row, raw, snapshot)
        need(total <= r['max_total_bytes'], 'thoughtspot.source_byte_limit')
        pending.append((row, raw, info))
    source = {'snapshot': snapshot, 'snapshot_file': F.write_once(root, 'snapshot.json', raw_snapshot),
        'definition_fingerprint': definition_fingerprint(snapshot), 'originals_manifest': manifest,
        'originals_manifest_file': F.write_once(root, 'originals-manifest.json', raw_manifest), 'originals': []}
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
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'thoughtspot.attachment_size')
    need(parser_profile is None or format == 'json' and type(parser_profile) is dict
         and parser_profile.get('format') == 'json' and parser_profile.get('shape') == 'compact_matrix',
         'thoughtspot.attachment_parser_profile')
    if format == 'png':
        return F.png_info(raw)
    if format == 'pdf':
        need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'thoughtspot.pdf_signature')
        return {'validation': 'signature_only_not_rendered'}
    screen_bytes(raw)
    if format == 'json':
        value = F.decode(raw); F.secret_check(value)
        if parser_profile is not None:
            # Reuse the explicit matrix projection and typed normalizer. This
            # local inspection context is never emitted as capture/QA evidence.
            raw_hash = F.raw_sha(raw)
            binding = {k: raw_hash for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256')}
            binding.update(object_key='local-inspection-only', attachment_id='local-inspection-only')
            normalized = module('thoughtspot_visual').normalize_results(raw, parser_profile, binding)
            return {'row_count': normalized['row_count'], 'interpretation': 'explicit_compact_matrix_profile',
                    'parser_profile_sha256': sha(parser_profile), 'completeness': 'not_inferred'}
        rows = value if type(value) is list and all(type(x) is dict for x in value) else None
        need(rows is None or len(rows) <= 100000, 'thoughtspot.result_row_limit')
        # Vendor response wrappers stay original JSON. Their paging/result grain
        # cannot be inferred from the length of a wrapper list.
        flat = rows is not None and all(all(type(v) in (str, int, float, bool) or v is None for v in row.values()) for row in rows)
        return {'row_count': len(rows) if flat else None, 'interpretation': 'object_rows_json' if flat else 'native_json_unqualified',
                'completeness': 'not_inferred'}
    need(format == 'csv', 'thoughtspot.attachment_format')
    try:
        header = next(csv.reader(io.StringIO(raw.decode('utf-8-sig')), strict=True))
        need(0 < len(header) <= 512 and len(set(header)) == len(header) and all(text(x) for x in header), 'thoughtspot.csv_headers')
        count = 0
        for row in module('bounded_csv').rows(raw, header, 'thoughtspot'):
            F.secret_check(dict(zip(header, row))); count += 1
        return {'headers': header, 'row_count': count, 'interpretation': 'utf8_comma_csv', 'completeness': 'not_inferred'}
    except (UnicodeError, csv.Error, StopIteration):
        raise F.CaptureError('thoughtspot.invalid_csv') from None


def validate_attachment(row, request, snapshot):
    required = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
        'population', 'freshness', 'completeness', 'reference'}
    derived = {'source_path', 'path', 'sha256', 'bytes', 'request_sha256', 'definition_fingerprint',
        'requested_state_sha256', 'inspection', 'acquisition', 'member_path', 'archive_file', 'parser_profile'}
    inventory = {x['key']: x for x in snapshot['inventory']['items']}
    need(type(row) is dict and required <= set(row) <= required | derived and local_id(row['attachment_id'])
         and row['object_key'] in inventory and row['format'] in ('csv', 'json', 'png', 'pdf') and text(row['reference']),
         'thoughtspot.attachment_contract')
    need('parser_profile' not in row or row['format'] == 'json' and type(row['parser_profile']) is dict
         and row['parser_profile'].get('format') == 'json' and row['parser_profile'].get('shape') == 'compact_matrix',
         'thoughtspot.attachment_parser_profile')
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown') and row['result_scope'] in
         ('query_result', 'transformed', 'displayed', 'unknown') and
         (row['origin'] not in ('displayed', 'transformed') or row['origin'] == row['result_scope']), 'thoughtspot.result_origin')
    observed = row['observed_state']
    if observed is not None:
        need(type(observed) is dict and {'state', 'observed_at', 'reference'} <= set(observed) <=
             {'state', 'observed_at', 'reference', 'placement_reference', 'result_context', 'tab_id'}
             and text(observed['observed_at']) and text(observed['reference']), 'thoughtspot.observed_state')
        validate_state(observed['state'])
        for key in ('placement_reference', 'tab_id'):
            need(key not in observed or text(observed[key]), 'thoughtspot.observed_context_reference')
        if 'result_context' in observed:
            module('thoughtspot_visual').result_context(observed['result_context'])
    for key, fields in (('population', {'key', 'description', 'reference'}),
                        ('freshness', {'data_watermark', 'observed_at', 'reference'})):
        need(type(row[key]) is dict and set(row[key]) == fields and all(v is None or text(v) for v in row[key].values()),
             'thoughtspot.' + key)
    c = row['completeness']
    need(type(c) is dict and set(c) == {'status', 'reference', 'row_count'} and c['status'] in ('complete', 'partial', 'unknown')
         and (c['reference'] is None or text(c['reference'])) and
         (c['row_count'] is None or (type(c['row_count']) is int and 0 <= c['row_count'] <= 100000)), 'thoughtspot.completeness')
    if c['status'] == 'complete':
        need(row['format'] in ('csv', 'json') and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and observed is not None and text(observed['state']['principal']) and all(row['population'].values())
             and all(row['freshness'].values()) and text(c['reference']) and type(c['row_count']) is int,
             'thoughtspot.complete_result_evidence_required')
    F.secret_check(row)


def _lock(root):
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), 'thoughtspot.lock_type')
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
             and spec['schema_version'] == 'thoughtspot-supplied-evidence.v1' and type(spec['attachments']) is list
             and len(spec['attachments']) <= 100, 'thoughtspot.evidence_import')
        seen = {a['attachment_id'] for a in value['attachments']}
        need(len(seen) + len(spec['attachments']) <= 500, 'thoughtspot.attachment_count')
        keys = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
                'population', 'freshness', 'completeness', 'reference', 'source_path', 'member_path'}
        pending, total = [], sum(p['bytes'] for p in file_pins(value))
        for row in spec['attachments']:
            need(type(row) is dict and keys <= set(row) <= keys | {'parser_profile'}, 'thoughtspot.supplied_attachment_fields')
            validate_attachment(row, value['request'], value['source']['snapshot'])
            need(row['attachment_id'] not in seen, 'thoughtspot.duplicate_attachment'); seen.add(row['attachment_id'])
            original = F.read_file(source_root / F.source_path(row['source_path']))
            raw, archive = original, None
            if row['member_path'] is not None:
                F.source_path(row['member_path'])
                members = zip_members(original)
                need(row['member_path'] in members, 'thoughtspot.zip_member_missing')
                raw, archive = members[row['member_path']]['raw'], original
            info = inspect_attachment(raw, row['format'], row.get('parser_profile'))
            need(row['completeness']['row_count'] is None or row['completeness']['row_count'] == info.get('row_count'),
                 'thoughtspot.result_count_or_shape_unqualified')
            total += len(raw) + (len(archive) if archive is not None else 0)
            need(total <= value['request']['max_total_bytes'], 'thoughtspot.retained_byte_limit')
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


def inspect_response(raw, op):
    kind, body = op['kind'], op['body']
    if OPERATIONS[kind]['scope'] == 'render':
        format = body['file_format'].lower()
        return {'format': format, 'inspection': inspect_attachment(raw, format),
                'completeness': 'not_inferred', 'observed_state': None}
    screen_bytes(raw)
    data = F.decode(raw); F.secret_check(data)
    objects = [data] if type(data) is dict else data if type(data) is list else []
    need(objects and all(type(x) is dict for x in objects) or data == [], 'thoughtspot.response_shape')
    failed = any(x.get('error') or x.get('errors') or str(x.get('status', '')).lower() in
                 ('error', 'failed', 'failure', 'denied', 'partial') for x in objects)
    # Export reports per-object status inside info.status, even for HTTP 200.
    for obj in objects:
        reports = [obj.get('status')]
        if type(obj.get('info')) is dict:
            reports.append(obj['info'].get('status'))
        for report in reports:
            if type(report) is dict and 'status_code' in report:
                failed = failed or report['status_code'] not in ('OK', 'SUCCESS')
    need(not failed, 'thoughtspot.business_error')
    return {'format': 'json', 'inspection': 'retained_native_response', 'completeness': 'not_inferred', 'observed_state': None}


def validate_envelope(value):
    need(type(value) is dict and value.get('schema_version') == ENVELOPE and value.get('content_hash') ==
         sha({k: v for k, v in value.items() if k != 'content_hash'}), 'thoughtspot.capture_hash_or_schema')
    r = validate_request(value.get('request'))
    need(r == value['request'] and value.get('request_sha256') == sha(r) and value.get('capture_id') == r['capture_id'],
         'thoughtspot.capture_request')
    need(value.get('target_write_authority') is False and value.get('arbitrary_source_code_execution') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed',
         'thoughtspot.capture_authority')
    source = value.get('source')
    need(type(source) is dict and set(source) == {'snapshot', 'snapshot_file', 'definition_fingerprint',
        'originals_manifest', 'originals_manifest_file', 'originals'}, 'thoughtspot.capture_source')
    validate_snapshot(source['snapshot'], r); validate_originals(source['originals_manifest'], source['snapshot'])
    validate_operation_scope(r, source['snapshot'])
    need(source['definition_fingerprint'] == definition_fingerprint(source['snapshot']) and type(source['originals']) is list
         and len(source['originals']) == len(source['originals_manifest']['records']), 'thoughtspot.definition_originals')
    for declared, record in zip(source['originals_manifest']['records'], source['originals']):
        need(type(record) is dict and set(record) == set(declared) | {'file', 'inspection'}
             and all(record[k] == declared[k] for k in declared), 'thoughtspot.original_record_changed')
    requested = {op['operation_id']: op for op in r['operations']}
    operations = value.get('operations')
    need(type(operations) is list and len(operations) <= r['max_total_requests'] and
         type(value.get('request_count')) is int and value['request_count'] == len(operations), 'thoughtspot.operation_budget')
    for op in operations:
        need(type(op) is dict and op.get('key') in requested, 'thoughtspot.operation_record')
        expected = operation_spec(r, requested[op['key']])
        fingerprint = {'request_sha256': value['request_sha256'], 'method': expected['method'], 'url': expected['url'],
                       'body_sha256': F.raw_sha(encoded(expected['body']))}
        need(op.get('method') == 'POST' and op.get('scope') == expected['scope'] and
             op.get('fingerprint_sha256') == sha(fingerprint) and type(op.get('started_at_epoch')) in (int, float)
             and op.get('status') in ('pending', 'success', 'rejected', 'uncertain'), 'thoughtspot.operation_route_binding')
        if 'http_status' in op:
            need(type(op['http_status']) is int and digest(op.get('response_sha256')) and
                 type(op.get('response_bytes')) is int and 0 <= op['response_bytes'] <= r['max_response_bytes'], 'thoughtspot.operation_response')
        if op['status'] == 'success':
            need(op.get('http_status') == 200, 'thoughtspot.operation_success')
    execution = copy.deepcopy(value); _execution_state(execution)
    need(all(value.get(k) == execution[k] for k in ('source_execution', 'saved_query_execution', 'render_execution')),
         'thoughtspot.execution_claim')
    responses = value.get('responses')
    need(type(responses) is list and len(responses) <= len(requested), 'thoughtspot.responses')
    seen_response = set()
    for response in responses:
        need(type(response) is dict and set(response) == {'operation_id', 'file', 'inspection'}
             and response['operation_id'] in requested and response['operation_id'] not in seen_response, 'thoughtspot.response_record')
        seen_response.add(response['operation_id'])
        need(any(op['key'] == response['operation_id'] and op['status'] == 'success' and
             op.get('response_sha256') == response['file']['sha256'] and op.get('response_bytes') == response['file']['bytes']
             for op in operations), 'thoughtspot.response_operation_binding')
    need({op['key'] for op in operations if op['status'] == 'success'} == seen_response, 'thoughtspot.response_denominator')
    attachments = value.get('attachments')
    need(type(attachments) is list and len(attachments) <= 500, 'thoughtspot.attachment_count')
    ids = set()
    for row in attachments:
        validate_attachment(row, r, source['snapshot'])
        need(row['attachment_id'] not in ids and row.get('request_sha256') == value['request_sha256']
             and row.get('definition_fingerprint') == source['definition_fingerprint']
             and row.get('requested_state_sha256') == sha(r['state']) and row.get('acquisition') == 'supplied'
             and ('source_path' not in row) and (row.get('member_path') is None) == (row.get('archive_file') is None),
             'thoughtspot.attachment_binding')
        ids.add(row['attachment_id'])
    need(type(value.get('network_bytes')) is int and value['network_bytes'] == sum(op.get('response_bytes', 0) for op in operations)
         and 0 <= value['network_bytes'] <= r['max_total_bytes'] and type(value.get('journal_revision')) is int
         and 1 <= value['journal_revision'] <= 3000 and type(value.get('created_at_epoch')) in (int, float)
         and type(value.get('retry_not_before_epoch')) in (int, float), 'thoughtspot.capture_budgets')
    need(value.get('status') in ('partial', 'blocked', 'acquired_requested_operations')
         and type(value.get('gaps')) is list and set(BASE_GAPS) <= set(value['gaps']), 'thoughtspot.capture_status')
    if value['status'] == 'acquired_requested_operations':
        need(requested and set(requested) == seen_response, 'thoughtspot.false_acquisition_completion')
    for pin in file_pins(value):
        need(type(pin.get('path')) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', pin['path'])
             and digest(pin.get('sha256')) and type(pin.get('bytes')) is int and 0 <= pin['bytes'] <= F.MAX_FILE,
             'thoughtspot.file_pin')
    need(sum(p['bytes'] for p in file_pins(value)) <= r['max_total_bytes'], 'thoughtspot.retained_byte_limit')
    return value


validate_capture = validate_envelope


def verify_capture_files(value, root):
    validate_envelope(value)
    raw = {p['path']: F.read_pin(F.no_links(root), p) for p in file_pins(value)}
    source = value['source']
    need(F.decode(raw[source['snapshot_file']['path']]) == source['snapshot'] and
         F.decode(raw[source['originals_manifest_file']['path']]) == source['originals_manifest'], 'thoughtspot.source_record_original_mismatch')
    work = 0
    for row in source['originals']:
        work += row['file']['bytes']
        need(work <= 128000000, 'thoughtspot.mapping_work_limit')
        need(inspect_original(row, raw[row['file']['path']], source['snapshot']) == row['inspection'], 'thoughtspot.original_inspection_mismatch')
    for row in value['attachments']:
        content = raw[row['path']]
        if row.get('archive_file') is not None:
            members = zip_members(raw[row['archive_file']['path']])
            need(row['member_path'] in members and members[row['member_path']]['raw'] == content, 'thoughtspot.attachment_member_mismatch')
        info = inspect_attachment(content, row['format'], row.get('parser_profile'))
        need(info == row['inspection'] and (row['completeness']['row_count'] is None or
             row['completeness']['row_count'] == info.get('row_count')), 'thoughtspot.attachment_inspection_mismatch')
    requested = {op['operation_id']: op for op in value['request']['operations']}
    for row in value['responses']:
        need(inspect_response(raw[row['file']['path']], requested[row['operation_id']]) == row['inspection'], 'thoughtspot.response_inspection_mismatch')
    return {'status': 'verified_local_bytes', 'files': {p['path']: p['sha256'] for p in file_pins(value)},
            'native_validation': 'not_performed'}


def validate_transition(previous, current):
    """Hash-linked journal updates may extend evidence, never reset authority or attempts."""
    if previous is None:
        need(current['journal_revision'] == 1 and current['previous_capture'] is None
             and not current['operations'] and not current['responses'] and not current['attachments']
             and current['request_count'] == current['network_bytes'] == current['retry_not_before_epoch'] == 0
             and current['status'] == 'partial', 'thoughtspot.initial_journal_state')
        return
    immutable = ('schema_version', 'capture_id', 'request', 'request_sha256', 'source', 'created_at_epoch',
        'target_write_authority', 'arbitrary_source_code_execution', 'native_validation', 'business_acceptance')
    need(all(current[key] == previous[key] for key in immutable), 'thoughtspot.immutable_capture_changed')
    for key in ('request_count', 'network_bytes', 'retry_not_before_epoch'):
        need(current[key] >= previous[key], 'thoughtspot.journal_counter_rollback')
    for key in ('responses', 'attachments', 'gaps'):
        need(len(current[key]) >= len(previous[key]) and current[key][:len(previous[key])] == previous[key],
             'thoughtspot.journal_evidence_rewritten')
    before, after = previous['operations'], current['operations']
    need(len(before) <= len(after) <= len(before) + 1, 'thoughtspot.journal_attempts_rewritten')
    changed = 0
    for old, new in zip(before, after):
        if old == new:
            continue
        changed += 1
        allowed = {'http_status', 'response_sha256', 'response_bytes'}
        need(old['status'] == 'pending' and new['status'] in ('success', 'rejected', 'uncertain')
             and set(new) <= set(old) | allowed
             and all(new.get(k) == v for k, v in old.items() if k != 'status'),
             'thoughtspot.terminal_attempt_rewritten')
        if new['status'] == 'rejected':
            need(type(new.get('http_status')) is int and 400 <= new['http_status'] < 500,
                 'thoughtspot.rejected_attempt_status')
    need(changed <= 1, 'thoughtspot.multiple_attempt_resolution')
    if len(after) > len(before):
        new = after[-1]
        need(changed == 0 and not any(o['status'] in ('pending', 'uncertain') for o in before)
             and new['status'] == 'pending' and set(new) ==
             {'key', 'scope', 'method', 'fingerprint_sha256', 'started_at_epoch', 'status'}
             and new['started_at_epoch'] >= previous['retry_not_before_epoch']
             and sum(o['key'] == new['key'] for o in after) <= current['request']['max_attempts_per_operation'],
             'thoughtspot.unresolved_post_or_attempt_limit')


def _load(directory, config=None):
    root = F.private_directory(directory)
    paths = sorted(root.glob('capture-*.json'))
    need(paths and len(paths) <= 3000 and sum(F.no_links(p).stat().st_size for p in paths) <= MAX_JOURNAL_BYTES,
         'thoughtspot.capture_journal_missing_or_limit')
    previous, previous_value = None, None
    for i, path in enumerate(paths, 1):
        raw = F.read_file(path, F.MAX_JSON); value = F.decode(raw)
        need(path.name == 'capture-%06d.json' % i and value.get('journal_revision') == i and
             value.get('previous_capture') == previous, 'thoughtspot.journal_chain')
        validate_envelope(value)
        validate_transition(previous_value, value)
        previous_value = value
        previous = {'path': path.name, 'sha256': F.raw_sha(raw)}
    verify_capture_files(value, root)
    need(config is None or value['request'] == validate_request(config), 'thoughtspot.resume_request_changed')
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
        raise F.CaptureError('thoughtspot.redirect_rejected')


def default_transport(method, url, headers, body, maximum, timeout):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    try:
        response = opener.open(Request(url, data=body, headers=headers, method=method), timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        need(response.geturl() == url and not 300 <= response.code < 400, 'thoughtspot.redirect_rejected')
        chunks, total = [], 0
        while True:
            need(time.monotonic() - started < timeout, 'thoughtspot.response_deadline')
            data = response.read1(min(65536, maximum + 1 - total))
            if not data:
                break
            total += len(data)
            need(total <= maximum, 'thoughtspot.response_byte_limit'); chunks.append(data)
        return response.code, dict(response.headers), b''.join(chunks)


def capture(request, directory, *, authority=None, transport=None, resume=True, now=None):
    r = validate_request(request, require_service=True)
    need(callable(authority) and resume is True, 'thoughtspot.import_then_host_capture_required')
    root = F.private_directory(directory)
    transport, now = transport or default_transport, now or utcnow
    fd = _lock(root)
    try:
        value, latest = _load(root, r)
        count = 0
        for operation in r['operations']:
            key = operation['operation_id']
            if any(row['operation_id'] == key for row in value['responses']):
                continue
            prior = [o for o in value['operations'] if o['key'] == key]
            if any(o['status'] in ('pending', 'uncertain') for o in prior):
                value['status'] = 'blocked'
                if 'uncertain_post_requires_operator_resolution_no_blind_replay' not in value['gaps']:
                    value['gaps'].append('uncertain_post_requires_operator_resolution_no_blind_replay')
                break
            moment = now()
            base_bytes = sum(p['bytes'] for p in file_pins(value)) - sum(x['file']['bytes'] for x in value['responses'])
            maximum = min(r['max_response_bytes'], r['max_total_bytes'] - base_bytes - value['network_bytes'])
            if (count >= r['max_requests_per_invocation'] or value['request_count'] >= r['max_total_requests']
                or len(prior) >= r['max_attempts_per_operation'] or maximum <= 0
                or moment < value['retry_not_before_epoch'] or moment - value['created_at_epoch'] >= r['max_elapsed_seconds']):
                break
            selected = operation_spec(r, operation)
            raw_body = encoded(selected['body'])
            fingerprint = {'request_sha256': value['request_sha256'], 'method': selected['method'], 'url': selected['url'],
                           'body_sha256': F.raw_sha(raw_body)}
            try:
                grant = authority(selected['scope'], copy.deepcopy(fingerprint))
            except Exception:
                raise F.CaptureError('thoughtspot.host_authority_rejected') from None
            need(type(grant) is dict and set(grant) == {'Authorization'} and text(grant['Authorization'], 8192)
                 and grant['Authorization'].startswith('Bearer ') and len(grant['Authorization']) > 7, 'thoughtspot.host_bearer_required')
            record = {'key': key, 'scope': selected['scope'], 'method': 'POST', 'fingerprint_sha256': sha(fingerprint),
                      'started_at_epoch': moment, 'status': 'pending'}
            value['operations'].append(record); value['request_count'] += 1; count += 1; _execution_state(value)
            latest = advance(root, value)  # Pending POST survives interruption before a response.
            try:
                timeout = min(20, r['max_elapsed_seconds'] - (moment - value['created_at_epoch']))
                status, response_headers, raw = transport('POST', selected['url'],
                    {'Accept': 'application/json,image/png,application/pdf', 'Content-Type': 'application/json', **grant}, raw_body, maximum, timeout)
                need(type(status) is int and type(response_headers) is dict and type(raw) is bytes and len(raw) <= maximum,
                     'thoughtspot.transport_contract')
                record.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw))
                value['network_bytes'] += len(raw)
                # Raw binary render bytes cannot be decoded for text screening;
                # exact credential echoes are still denied before any persistence.
                for token in (grant['Authorization'], grant['Authorization'][7:]):
                    for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                        need(token.encode(encoding) not in raw, 'thoughtspot.credential_echo_rejected')
                need(not 300 <= status < 400, 'thoughtspot.redirect_rejected')
                if status != 200:
                    record['status'] = 'uncertain' if status >= 500 else 'rejected'
                    if status == 429:
                        value['retry_not_before_epoch'] = moment + 60
                    value['gaps'].append('source_http_failure_redacted')
                    latest = advance(root, value); break
                info = inspect_response(raw, operation)
                # Repeated page responses are retained but never imply progress.
                earlier_pages = [x for x in value['operations'][:-1] if x.get('response_sha256') == F.raw_sha(raw)
                                 and x['scope'] == record['scope'] and x['status'] == 'success']
                if earlier_pages and 'record_offset' in operation['body']:
                    value['gaps'].append('repeated_page_response_requires_review')
                pin = F.write_once(root, 'response-' + key + '.bin', raw)
                value['responses'].append({'operation_id': key, 'file': pin, 'inspection': info})
                record['status'] = 'success'; latest = advance(root, value)
            except Exception:
                record['status'] = 'uncertain'
                value['gaps'].append('source_response_uncertain_redacted')
                latest = advance(root, value); break
        if any(o['status'] in ('pending', 'uncertain') for o in value['operations']):
            value['status'] = 'blocked'
        elif {o['operation_id'] for o in r['operations']} == {x['operation_id'] for x in value['responses']}:
            value['status'] = 'acquired_requested_operations'
        else:
            value['status'] = 'partial'
        return result(advance(root, value))
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    local = sub.add_parser('import-local')
    for key in ('request', 'source-root', 'directory'):
        local.add_argument('--' + key, required=True, type=Path)
    local.add_argument('--allow-source-read', action='store_true')
    evidence = sub.add_parser('import-evidence')
    for key in ('capture', 'spec', 'source-root'):
        evidence.add_argument('--' + key, required=True, type=Path)
    checker = sub.add_parser('check'); checker.add_argument('--capture', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-local':
            out = import_local(F.decode(F.read_file(args.request)), args.source_root, args.directory,
                               allow_source_read=args.allow_source_read)
        elif args.command == 'import-evidence':
            out = import_evidence(args.capture, F.decode(F.read_file(args.spec)), args.source_root)
        else:
            out = check_capture(args.capture)
        print(encoded({'status': out['status'], 'native_validation': 'not_performed',
                       **({'journal': Path(out['output']).name} if 'output' in out else {})}).decode())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        print('ThoughtSpot capture rejected; review scoped evidence and authority.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
