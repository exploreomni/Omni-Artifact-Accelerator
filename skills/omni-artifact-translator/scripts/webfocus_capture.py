#!/usr/bin/env python3
"""Passive WebFOCUS originals and separately granted repository GET evidence.

No FEX/SQL/JavaScript execution, credential acquisition, source authoring or
native-target writes. Local hashes protect byte continuity, not authenticity.
"""
from __future__ import annotations

import argparse
import copy
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
import unicodedata
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import xml.etree.ElementTree as ET
import zipfile


def module(name):
    need_name = name in ('powerbi_capture_files', 'bounded_csv', 'webfocus_visual')
    if not need_name:
        raise ValueError('webfocus.module_rejected')
    path = Path(__file__).with_name(name + '.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('webfocus.module_symlink')
    spec = importlib.util.spec_from_file_location('webfocus_' + name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


F = module('powerbi_capture_files')
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST = REQUEST_SCHEMA = 'webfocus-visual-capture-request.v1'
ENVELOPE = SCHEMA = 'webfocus-visual-capture.v1'
MAX_JOURNAL_BYTES = 128000000
BASE_GAPS = ['source_identity_and_authority_references_not_authenticated',
    'independent_inventory_is_declared_scope_not_tenant_completeness',
    'requested_state_is_not_observed_state', 'effective_access_not_verified',
    'source_code_not_executed', 'native_validation_not_performed',
    'rendered_quality_and_business_acceptance_not_assessed']


def text(value, maximum=1000):
    return type(value) is str and 0 < len(value) <= maximum and all(ord(c) >= 32 for c in value)


def local_id(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value) is not None


def digest(value):
    return type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def screen_text(content):
    """Bounded credential-pattern screening, not proof of absence of secrets."""
    F.safe_text(content.encode('utf-8'))
    names = r'(?:password|passwd|pwd|access[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?key|private[_-]?key)'
    need(not re.search(r'(?i)[\"\']?\b' + names + r'\b[\"\']?\s*[=:]\s*[\"\']?[^\s,;\"\'}<>]+', content)
         and not re.search(r'(?is)<\s*' + names + r'\b[^>]*>\s*[^<\s]+', content)
         and not re.search(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{12,}', content),
         'webfocus.credential_bearing_text')


def screen_bytes(raw, encoding=None, granted=None):
    if granted is not None:
        for name in ('utf-8', 'utf-16-le', 'utf-16-be'):
            need(granted.encode(name) not in raw, 'webfocus.credential_echo_rejected')
    candidates = [encoding] if encoding else (['utf-16'] if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else ['utf-8-sig', 'windows-1252'])
    for name in candidates:
        try:
            value = raw.decode(name)
        except UnicodeError:
            continue
        screen_text(value)
        return 'recognized_text_patterns_only'
    return 'unknown_encoding_not_assessed'


def utcnow():
    return datetime.now(timezone.utc).timestamp()


def origin(value):
    need(text(value, 2048), 'webfocus.origin')
    p = urlsplit(value)
    need(p.scheme == 'https' and p.hostname and p.netloc == p.hostname
         and not p.path and not p.query and not p.fragment and not p.username and not p.password
         and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', p.hostname), 'webfocus.https_origin_required')
    return value


def resource_path(value):
    need(text(value, 1000) and value.startswith('/WFC/Repository/')
         and not any(c in value for c in ('%', '?', '#', '\\', ':'))
         and all(p and p not in ('.', '..') for p in value.split('/')[1:]), 'webfocus.repository_resource_path')
    return value


def validate_state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'timezone', 'locale', 'principal',
         'cache', 'reference'} and type(value['filters']) is dict and len(value['filters']) <= 100
         and type(value['parameters']) is dict and len(value['parameters']) <= 100, 'webfocus.state_contract')
    for key in ('timezone', 'locale', 'principal', 'cache'):
        need(value[key] is None or text(value[key]), 'webfocus.state_context')
    need(text(value['reference']), 'webfocus.state_reference')
    F.decode(encoded(value))
    F.secret_check(value)


state = validate_state


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'product', 'source_origin', 'product_version', 'product_evidence_ref',
        'principal_ref', 'authorization_ref', 'credential_ref', 'evidence_mode', 'source_revision', 'root_key',
        'route', 'route_reference', 'target_surface', 'state', 'originals_path', 'inventory_path', 'crosswalk_path'}
    defaults = {'adapter_report_path': None, 'producer_revision': None, 'operations': [],
        'api_contract': None, 'max_requests_per_invocation': 20, 'max_total_requests': 200,
        'max_total_bytes': 32000000, 'max_response_bytes': 8000000, 'max_elapsed_seconds': 21600,
        'max_attempts_per_operation': 3}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value.get('schema_version') == REQUEST and value.get('product') == 'webfocus', 'webfocus.request_contract')
    r = {**defaults, **copy.deepcopy(value)}
    need(local_id(r['capture_id']) and local_id(r['root_key']), 'webfocus.request_identity')
    origin(r['source_origin'])
    for key in ('product_version', 'product_evidence_ref', 'principal_ref', 'authorization_ref'):
        need(text(r[key]), 'webfocus.evidence_reference')
    need(r['credential_ref'] is None or text(r['credential_ref']), 'webfocus.credential_reference')
    rev = r['source_revision']
    need(type(rev) is dict and set(rev) == {'kind', 'value', 'reference'} and text(rev['reference'])
         and rev['kind'] in ('git_commit', 'supplied_snapshot', 'unknown'), 'webfocus.source_revision')
    need((rev['kind'] == 'unknown' and rev['value'] is None) or
         (rev['kind'] == 'supplied_snapshot' and text(rev['value'])) or
         (rev['kind'] == 'git_commit' and type(rev['value']) is str and re.fullmatch(r'[a-f0-9]{40}', rev['value'])),
         'webfocus.source_revision_value')
    paths = [r[k] for k in ('originals_path', 'inventory_path', 'crosswalk_path')]
    for path in paths:
        F.source_path(path)
    need(len(set(paths)) == len(paths), 'webfocus.distinct_source_records')
    need((r['adapter_report_path'] is None) == (r['producer_revision'] is None), 'webfocus.report_revision_pair')
    if r['adapter_report_path'] is not None:
        F.source_path(r['adapter_report_path'])
        need(r['adapter_report_path'] not in paths and type(r['producer_revision']) is str
             and re.fullmatch(r'[a-f0-9]{40}', r['producer_revision']), 'webfocus.report_revision')
    need(r['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant'), 'webfocus.evidence_mode')
    need(r['target_surface'] in ('app', 'dashboard', 'both'), 'webfocus.target_surface')
    need(r['route'] in ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
         and (r['route'] == 'unselected' or text(r['route_reference'])), 'webfocus.route')
    validate_state(r['state'])
    bounds = {'max_requests_per_invocation': (1, 60), 'max_total_requests': (1, 1000),
        'max_total_bytes': (1, F.MAX_TOTAL), 'max_response_bytes': (1, F.MAX_FILE),
        'max_elapsed_seconds': (1, 86400), 'max_attempts_per_operation': (1, 5)}
    for key, (lo, hi) in bounds.items():
        need(type(r[key]) is int and lo <= r[key] <= hi, 'webfocus.budget')
    need(type(r['operations']) is list and len(r['operations']) <= 200, 'webfocus.operations_bound')
    ids, identities = set(), set()
    for op in r['operations']:
        need(type(op) is dict and set(op) == {'operation_id', 'action', 'resource_path', 'reference'}
             and local_id(op['operation_id']) and op['operation_id'] not in ids
             and op['action'] in ('get', 'getContent', 'properties') and text(op['reference']), 'webfocus.read_operation')
        resource_path(op['resource_path'])
        need(op['action'] != 'getContent' or op['resource_path'].lower().endswith(('.fex', '.url')),
             'webfocus.get_content_type_not_qualified')
        identity = (op['action'], op['resource_path'])
        need(identity not in identities, 'webfocus.duplicate_operation')
        ids.add(op['operation_id']); identities.add(identity)
    api = r['api_contract']
    if api is not None:
        need(type(api) is dict and set(api) == {'context_path', 'wrapper', 'auth_header', 'reference'}
             and api['context_path'] == '/ibi_apps' and api['wrapper'] == 'ibfsrpc.v1'
             and api['auth_header'] in ('Cookie', 'Authorization')
             and text(api['reference']), 'webfocus.reviewed_api_contract')
    need(not r['operations'] or api is not None, 'webfocus.api_contract_required')
    need(not require_service or (r['credential_ref'] is not None and r['operations']), 'webfocus.host_scope_required')
    F.secret_check(r)
    return r


def operation_url(request, operation):
    r = validate_request(request)
    need(operation in r['operations'] and r['api_contract'] is not None, 'webfocus.operation_not_reviewed')
    path = resource_path(operation['resource_path'])
    base = r['source_origin'] + r['api_contract']['context_path'] + '/rs'
    if operation['action'] == 'properties':
        return base + '?' + urlencode({'IBIRS_path': path, 'IBIRS_action': 'properties', 'IBIRS_service': 'ibfs'})
    return base + '/ibfs' + quote(path, safe='/') + '?' + urlencode({'IBIRS_action': operation['action']})


def validate_originals(value):
    need(type(value) is dict and set(value) == {'schema_version', 'reference', 'records'}
         and value['schema_version'] == 'webfocus-originals.v1' and text(value['reference'])
         and type(value['records']) is list and 1 <= len(value['records']) <= F.MAX_FILES, 'webfocus.originals_manifest')
    seen, prefixes = set(), {}
    for row in value['records']:
        need(type(row) is dict and set(row) == {'source_path', 'kind', 'encoding', 'sha256', 'reference'}
             and row['kind'] in ('fex', 'mas', 'acx', 'sty', 'html', 'js', 'cm_zip', 'opaque')
             and row['encoding'] in ('utf-8', 'utf-8-sig', 'utf-16', 'windows-1252', 'iso-8859-1', 'binary', 'unknown')
             and digest(row['sha256']) and text(row['reference']), 'webfocus.original_record')
        path = F.source_path(row['source_path'])
        folded = unicodedata.normalize('NFC', path).casefold()
        need(folded not in seen and not any(folded.startswith(p + '/') or p.startswith(folded + '/') for p in seen),
             'webfocus.original_path_collision')
        seen.add(folded)
        parts = path.split('/')
        for i in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:i]); key = unicodedata.normalize('NFC', prefix).casefold()
            need(key not in prefixes or prefixes[key] == prefix, 'webfocus.original_path_alias')
            prefixes[key] = prefix
        need(row['kind'] != 'cm_zip' or row['encoding'] == 'binary', 'webfocus.zip_encoding')
    F.secret_check(value)
    return value


def validate_inventory(value, request, report=None):
    need(type(value) is dict and set(value) == {'schema_version', 'method', 'reference', 'completeness', 'objects'}
         and value['schema_version'] == 'webfocus-source-enumeration.v1' and value['method'] == 'separate_source_enumeration'
         and text(value['reference']) and value['completeness'] in ('partial', 'selected_scope_declared')
         and type(value['objects']) is list and 1 <= len(value['objects']) <= 2000, 'webfocus.independent_enumeration')
    adapter = {o['id']: o for o in report['objects']} if report is not None else {}
    indexed = {}
    for row in value['objects']:
        need(type(row) is dict and set(row) == {'key', 'kind', 'name', 'parent_key', 'source_object_id',
             'disposition', 'disposition_reference', 'evidence_reference', 'configuration'}
             and local_id(row['key']) and row['key'] not in indexed and row['kind'] in
             ('page', 'visual', 'control', 'placement', 'content', 'unknown', 'section', 'container',
              'app', 'dashboard', 'parameter', 'action') and text(row['name'])
             and row['disposition'] in ('include', 'manual_review', 'unsupported', 'out_of_scope')
             and text(row['disposition_reference']) and text(row['evidence_reference'])
             and type(row['configuration']) is dict, 'webfocus.inventory_record')
        need(row['source_object_id'] is None or (text(row['source_object_id']) and row['source_object_id'] in adapter),
             'webfocus.inventory_adapter_binding')
        if 'result_contract' in row['configuration']:
            validate_result_context(row['configuration']['result_contract'])
        indexed[row['key']] = row
    need(request['root_key'] in indexed and indexed[request['root_key']]['kind'] in
         ('page', 'app', 'dashboard', 'visual', 'content', 'unknown')
         and indexed[request['root_key']]['parent_key'] is None, 'webfocus.root_artifact_required')
    for key, row in indexed.items():
        parent, seen = row['parent_key'], {key}
        while parent is not None:
            need(parent in indexed and parent not in seen, 'webfocus.inventory_parent_or_cycle')
            seen.add(parent); parent = indexed[parent]['parent_key']
        need(request['root_key'] in seen, 'webfocus.inventory_outside_selected_scope')
        if row['kind'] == 'placement':
            need(('visual_key' in row['configuration']) != ('content_key' in row['configuration']), 'webfocus.placement_identity')
            target = row['configuration'].get('visual_key', row['configuration'].get('content_key'))
            need(target in indexed and indexed[target]['kind'] in ('visual', 'content', 'unknown'), 'webfocus.placement_target')
    F.secret_check(value)
    return indexed


def validate_crosswalk(value, inventory, report=None):
    need(type(value) is dict and set(value) == {'schema_version', 'reference', 'rows'}
         and value['schema_version'] == 'webfocus-identity-crosswalk.v1' and text(value['reference'])
         and type(value['rows']) is list and len(value['rows']) <= 2000, 'webfocus.identity_crosswalk')
    indexed = {}
    for row in value['rows']:
        need(type(row) is dict and set(row) == {'key', 'resource_path', 'source_object_id', 'reference'}
             and row['key'] in inventory and row['key'] not in indexed and text(row['reference'])
             and row['source_object_id'] == inventory[row['key']]['source_object_id'], 'webfocus.crosswalk_record')
        if row['resource_path'] is not None:
            resource_path(row['resource_path'])
        indexed[row['key']] = row
    need(set(indexed) == set(inventory), 'webfocus.crosswalk_denominator')
    return indexed


def inspect_zip(raw):
    """Inventory members without extraction or executing/decoding any content."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            need(1 <= len(members) <= F.MAX_FILES, 'webfocus.zip_member_limit')
            rows, names, total = [], set(), 0
            for item in members:
                path = item.filename[:-1] if item.is_dir() else item.filename
                F.source_path(path)
                name = unicodedata.normalize('NFC', path).casefold()
                need(name not in names, 'webfocus.zip_path_collision')
                names.add(name)
                mode = item.external_attr >> 16
                need(not (item.flag_bits & 1) and item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                     and (stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR)), 'webfocus.zip_unsafe_member')
                if item.is_dir():
                    continue
                need(item.file_size <= F.MAX_FILE and item.file_size <= max(1, item.compress_size) * 100,
                     'webfocus.zip_expansion_limit')
                total += item.file_size
                need(total <= F.MAX_TOTAL, 'webfocus.zip_total_limit')
                with archive.open(item) as stream:
                    data = stream.read(F.MAX_FILE + 1)
                need(len(data) == item.file_size <= F.MAX_FILE, 'webfocus.zip_size_mismatch')
                suffix = Path(path).suffix.lower()
                scan = screen_bytes(data) if suffix in ('.fex', '.mas', '.acx', '.sty', '.html', '.htm', '.js',
                    '.json', '.xml', '.txt', '.csv', '.url', '.css', '.ini', '.cfg', '.yaml', '.yml', '.sql') else 'opaque_bytes_not_assessed'
                rows.append({'path': path, 'bytes': len(data), 'sha256': F.raw_sha(data), 'credential_screening': scan})
            files = [unicodedata.normalize('NFC', row['path']).casefold() for row in rows]
            need(not any(a.startswith(b + '/') for a in names for b in files if a != b), 'webfocus.zip_file_directory_collision')
            return {'interpretation': 'cm_zip_members_inventoried_only', 'members': rows,
                    'expanded_bytes': total, 'execution_performed': False}
    except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError):
        raise F.CaptureError('webfocus.invalid_zip') from None


def inspect_original(row, raw):
    need(F.raw_sha(raw) == row['sha256'], 'webfocus.original_source_hash_mismatch')
    if row['kind'] == 'cm_zip':
        return inspect_zip(raw)
    if row['encoding'] not in ('binary', 'unknown'):
        try:
            content = raw.decode(row['encoding'])
            screen_text(content)
        except UnicodeError:
            raise F.CaptureError('webfocus.declared_encoding_mismatch') from None
    result = {'interpretation': 'inert_bytes', 'encoding': row['encoding'], 'execution_performed': False,
              'credential_screening': 'recognized_text_patterns_only' if row['encoding'] not in ('binary', 'unknown') else 'opaque_bytes_not_assessed'}
    if row['kind'] == 'fex' and row['encoding'] not in ('binary', 'unknown'):
        result['visual_declarations'] = module('webfocus_visual').inspect_fex(content, row['source_path'])
    return result


def source_fingerprint(source):
    return sha({k: source[k] for k in ('originals_sha256', 'inventory_sha256', 'crosswalk_sha256',
                                      'adapter_report_sha256', 'files')})


def file_pins(value):
    source = value['source']
    pins = [source[k] for k in ('originals_file', 'inventory_file', 'crosswalk_file')]
    if source['adapter_report_file'] is not None:
        pins.append(source['adapter_report_file'])
    return pins + source['files'] + value['attachments'] + [p['file'] for p in value['api_pages']]


def _save(root, value):
    value['journal_revision'] += 1
    value.pop('content_hash', None)
    value['content_hash'] = sha(value)
    raw = encoded(value)
    snapshots = list(root.glob('capture-*.json'))
    need(len(snapshots) < 3000 and len(raw) <= F.MAX_JSON and
         len(raw) + sum(F.no_links(p).stat().st_size for p in snapshots) <= MAX_JOURNAL_BYTES, 'webfocus.journal_budget')
    pin = F.write_once(root, 'capture-%06d.json' % value['journal_revision'], raw)
    return root / pin['path']


def advance(root, value):
    path = _save(root, value)
    value['previous_capture'] = {'path': path.name, 'sha256': F.raw_sha(F.read_file(path, F.MAX_JSON))}
    return path


def result(path):
    value = F.decode(F.read_file(path, F.MAX_JSON))
    return {'status': value['status'], 'output': str(path), 'capture': value}


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read is True, 'webfocus.source_read_grant_required')
    r = validate_request(request)
    source_root, root = F.no_links(source_root), F.private_directory(directory)
    need(source_root.is_dir() and not list(root.iterdir()), 'webfocus.new_directory_required')
    names = ['originals', 'inventory', 'crosswalk'] + (['adapter_report'] if r['adapter_report_path'] else [])
    blobs = {k: F.read_file(source_root / r[k + '_path']) for k in names}
    values = {k: F.decode(v) for k, v in blobs.items()}
    originals = validate_originals(values['originals'])
    report = values.get('adapter_report')
    if report is not None:
        module('webfocus_visual').validate(report, r['producer_revision'])
    indexed = validate_inventory(values['inventory'], r, report)
    crosswalk = validate_crosswalk(values['crosswalk'], indexed, report)
    need({op['resource_path'] for op in r['operations']} <= {row['resource_path'] for row in crosswalk.values()},
         'webfocus.operation_outside_crosswalk')
    pending, total = [], sum(map(len, blobs.values()))
    for row in originals['records']:
        raw = F.read_file(source_root / row['source_path'])
        info = inspect_original(row, raw)
        total += len(raw)
        need(total <= r['max_total_bytes'], 'webfocus.source_byte_limit')
        pending.append((row, raw, info))
    if report is not None:
        manifest = {row['source_path']: row for row in originals['records']}
        need(all(f['path'] in manifest and f['sha256'] == manifest[f['path']]['sha256'] for f in report['source_files']),
             'webfocus.adapter_originals_mismatch')
    source = {'adapter_report': None, 'adapter_report_sha256': None, 'adapter_report_file': None, 'files': []}
    for key in names:
        source[key] = values[key]; source[key + '_sha256'] = sha(values[key])
        source[key + '_file'] = F.write_once(root, key + '.json', blobs[key])
    for i, (row, raw, info) in enumerate(pending):
        source['files'].append({**F.write_once(root, 'source-%04d.bin' % i, raw), 'source_path': row['source_path'],
                                'interpretation': 'inert_bytes', 'inspection': info})
    source['definition_fingerprint'] = source_fingerprint(source)
    value = {'schema_version': ENVELOPE, 'capture_id': r['capture_id'], 'request': r, 'request_sha256': sha(r),
        'source': source, 'attachments': [], 'api_pages': [], 'operations': [], 'status': 'partial',
        'journal_revision': 0, 'previous_capture': None, 'created_at_epoch': utcnow(), 'request_count': 0,
        'network_bytes': 0, 'retry_not_before_epoch': 0, 'gaps': list(BASE_GAPS), 'target_write_authority': False,
        'source_execution': False, 'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}
    return result(_save(root, value))


def inspect_attachment(raw, format):
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'webfocus.attachment_size')
    if format == 'csv':
        import csv
        try:
            content = raw.decode('utf-8-sig')
            need('\x00' not in content, 'webfocus.invalid_csv')
            header = next(csv.reader(io.StringIO(content), strict=True))
            need(0 < len(header) <= 512 and len(set(header)) == len(header)
                 and all(text(x) for x in header), 'webfocus.csv_headers')
            screen_text(content)
            count = 0
            for row in module('bounded_csv').rows(raw, header, 'webfocus'):
                F.secret_check(dict(zip(header, row)))
                count += 1
            return {'headers': header, 'row_count': count, 'interpretation': 'utf8_comma_csv'}
        except (UnicodeError, csv.Error, StopIteration):
            raise F.CaptureError('webfocus.invalid_csv') from None
    if format == 'json':
        value = F.decode(raw)
        F.secret_check(value)
        need(type(value) is list and len(value) <= 100000 and all(type(row) is dict for row in value),
             'webfocus.json_object_rows_required')
        headers = list(value[0]) if value else []
        need(len(headers) <= 512 and len(headers) * len(value) <= 1000000
             and all(set(row) == set(headers) and all(type(v) in (str, int, float, bool) or v is None for v in row.values())
                     for row in value), 'webfocus.json_row_shape')
        return {'headers': headers, 'row_count': len(value), 'interpretation': 'object_rows_json'}
    if format == 'png':
        return F.png_info(raw)
    need(format == 'pdf' and raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'webfocus.invalid_pdf')
    return {'validation': 'signature_only_no_pdf_decoder_or_render'}


def validate_attachment(row, request, inventory):
    required = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
        'population', 'freshness', 'completeness', 'reference'}
    derived = {'source_path', 'path', 'sha256', 'bytes', 'request_sha256', 'definition_fingerprint',
        'requested_state_sha256', 'inspection', 'acquisition'}
    need(type(row) is dict and required <= set(row) <= required | derived and local_id(row['attachment_id'])
         and row['object_key'] in inventory and row['format'] in ('csv', 'json', 'png', 'pdf')
         and text(row['reference']), 'webfocus.attachment_contract')
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown')
         and row['result_scope'] in ('query_result', 'transformed', 'displayed', 'unknown')
         and (row['origin'] not in ('displayed', 'transformed') or row['origin'] == row['result_scope']),
         'webfocus.result_origin')
    observed = row['observed_state']
    if observed is not None:
        need(type(observed) is dict and {'state', 'observed_at', 'reference'} <= set(observed)
             <= {'state', 'observed_at', 'reference', 'placement_reference', 'result_context'} and text(observed['observed_at'])
             and text(observed['reference']) and ('placement_reference' not in observed or text(observed['placement_reference'])),
             'webfocus.observed_state')
        validate_state(observed['state'])
        if 'result_context' in observed:
            validate_result_context(observed['result_context'])
    for key, keys in (('population', {'key', 'description', 'reference'}),
                      ('freshness', {'data_watermark', 'observed_at', 'reference'})):
        need(type(row[key]) is dict and set(row[key]) == keys and
             all(v is None or text(v) for v in row[key].values()), 'webfocus.' + key)
    c = row['completeness']
    need(type(c) is dict and set(c) == {'status', 'reference', 'row_count'}
         and c['status'] in ('complete', 'partial', 'unknown') and (c['reference'] is None or text(c['reference']))
         and (c['row_count'] is None or (type(c['row_count']) is int and 0 <= c['row_count'] <= 100000)),
         'webfocus.result_completeness')
    if c['status'] == 'complete':
        need(row['format'] in ('csv', 'json') and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and observed is not None and text(observed['state']['principal']) and all(row['population'].values())
             and all(row['freshness'].values()) and text(c['reference']) and type(c['row_count']) is int,
             'webfocus.complete_result_evidence_required')
    F.secret_check(row)


def validate_result_context(value):
    need(type(value) is dict and set(value) == {'data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage', 'reference'}
         and value['data_mode'] in ('full_data', 'preview', 'test', 'unknown')
         and (value['row_limit'] is None or (type(value['row_limit']) is int and value['row_limit'] > 0))
         and value['row_limit_stage'] in ('before_aggregation', 'after_aggregation', 'none', 'unknown')
         and value['aggregation_stage'] in ('native_report', 'raw_query', 'in_document', 'unknown')
         and text(value['reference']), 'webfocus.result_context')
    need((value['row_limit_stage'] not in ('before_aggregation', 'after_aggregation') or value['row_limit'] is not None)
         and (value['row_limit_stage'] != 'none' or value['row_limit'] is None), 'webfocus.result_limit_stage')
    return value


def _lock(root):
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), 'webfocus.lock_file_type')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BaseException:
        os.close(fd)
        raise


def import_evidence(capture_path, spec, source_root):
    path = F.no_links(capture_path)
    root, source_root = F.private_directory(path.parent), F.no_links(source_root)
    fd = _lock(root)
    try:
        value, latest = _load(root)
        need(path == latest and type(spec) is dict and set(spec) == {'schema_version', 'attachments'}
             and spec['schema_version'] == 'webfocus-supplied-evidence.v1' and type(spec['attachments']) is list
             and len(spec['attachments']) <= 100, 'webfocus.evidence_import')
        inventory = {o['key']: o for o in value['source']['inventory']['objects']}
        seen = {a['attachment_id'] for a in value['attachments']}
        need(len(seen) + len(spec['attachments']) <= 500, 'webfocus.attachment_count')
        pending, total = [], sum(p['bytes'] for p in file_pins(value))
        supplied_keys = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
                        'population', 'freshness', 'completeness', 'reference', 'source_path'}
        for row in spec['attachments']:
            need(type(row) is dict and set(row) == supplied_keys, 'webfocus.supplied_attachment_fields')
            validate_attachment(row, value['request'], inventory)
            need(row['attachment_id'] not in seen, 'webfocus.duplicate_attachment')
            seen.add(row['attachment_id'])
            raw = F.read_file(source_root / F.source_path(row['source_path']))
            info = inspect_attachment(raw, row['format'])
            need(row['completeness']['row_count'] is None or row['completeness']['row_count'] == info.get('row_count'),
                 'webfocus.result_count_contradiction')
            total += len(raw)
            need(total <= value['request']['max_total_bytes'], 'webfocus.retained_byte_limit')
            pending.append((row, raw, info))
        for row, raw, info in pending:
            record = {k: copy.deepcopy(v) for k, v in row.items() if k != 'source_path'}
            record.update(F.write_once(root, 'attachment-' + row['attachment_id'] + '.' + row['format'], raw))
            record.update(request_sha256=value['request_sha256'], definition_fingerprint=value['source']['definition_fingerprint'],
                requested_state_sha256=sha(value['request']['state']), inspection=info, acquisition='supplied')
            value['attachments'].append(record)
        return result(advance(root, value))
    finally:
        os.close(fd)


def inspect_response(raw, action, content_type):
    """Only a bounded known XML envelope is interpreted; nothing is rendered."""
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'webfocus.response_size')
    # Reject declarations before the stdlib parser, including UTF-16 spelling.
    probe = raw.replace(b'\x00', b'').upper()
    need(b'<!DOCTYPE' not in probe and b'<!ENTITY' not in probe, 'webfocus.xml_dtd_entity_rejected')
    screening = screen_bytes(raw)
    media = content_type.split(';', 1)[0].strip().lower()
    xml_like = probe.lstrip().startswith((b'<?XML', b'<IBFSRPC'))
    if action == 'getContent' and media == 'text/plain' and not xml_like:
        return {'interpretation': 'original_content_bytes_only', 'business_success': True,
                'execution_performed': False, 'credential_screening': screening}
    if media not in ('application/xml', 'text/xml') and not xml_like:
        return {'interpretation': 'unsupported_response_wrapper', 'business_success': None,
                'execution_performed': False, 'credential_screening': screening}
    try:
        parser = ET.XMLPullParser(events=('start', 'end'))
        depth = count = 0
        element = None
        for i in range(0, len(raw), 4096):
            parser.feed(raw[i:i + 4096])
            for event, node in parser.read_events():
                if event == 'start':
                    depth += 1; count += 1
                    need(depth <= 48 and count <= 20000 and len(node.attrib) <= 100, 'webfocus.xml_structure_limit')
                    sensitive = {'password', 'passwd', 'pwd', 'accesstoken', 'refreshtoken', 'clientsecret',
                                 'apikey', 'privatekey', 'authorization', 'cookie', 'sessionid'}
                    need(all(re.sub('[^a-z]', '', k.lower()) not in sensitive or not v.strip() for k, v in node.attrib.items()),
                         'webfocus.credential_bearing_xml')
                    if element is None:
                        element = node
                else:
                    need(re.sub('[^a-z]', '', node.tag.lower()) not in sensitive or not (node.text or '').strip(),
                         'webfocus.credential_bearing_xml')
                    depth -= 1
        parser.close()
        need(element is not None, 'webfocus.empty_xml')
    except ET.ParseError:
        raise F.CaptureError('webfocus.invalid_xml') from None
    if (element.tag != 'ibfsrpc' or 'returncode' not in element.attrib or 'subreturncode' not in element.attrib
        or element.attrib.get('version') not in (None, '1', '1.0')):
        return {'interpretation': 'unsupported_response_wrapper', 'business_success': None,
                'execution_performed': False, 'credential_screening': screening}
    rc, sub = element.attrib['returncode'], element.attrib['subreturncode']
    need(re.fullmatch(r'-?\d{1,10}', rc) and re.fullmatch(r'-?\d{1,10}', sub), 'webfocus.xml_returncode')
    return {'interpretation': 'ibfsrpc.v1', 'business_success': rc == '10000' and sub == '0',
            'returncode': int(rc), 'subreturncode': int(sub), 'execution_performed': False, 'credential_screening': screening}


def validate_capture(value):
    need(type(value) is dict and value.get('schema_version') == ENVELOPE
         and value.get('content_hash') == sha({k: v for k, v in value.items() if k != 'content_hash'}), 'webfocus.capture_hash_or_schema')
    r = validate_request(value.get('request'))
    need(r == value['request'] and value.get('request_sha256') == sha(r) and value.get('capture_id') == r['capture_id'],
         'webfocus.capture_request')
    need(value.get('target_write_authority') is False and value.get('source_execution') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed',
         'webfocus.capture_authority')
    source = value.get('source')
    keys = {'originals', 'originals_sha256', 'originals_file', 'inventory', 'inventory_sha256', 'inventory_file',
        'crosswalk', 'crosswalk_sha256', 'crosswalk_file', 'adapter_report', 'adapter_report_sha256', 'adapter_report_file',
        'files', 'definition_fingerprint'}
    need(type(source) is dict and set(source) == keys, 'webfocus.capture_source')
    validate_originals(source['originals'])
    report = source['adapter_report']
    if report is not None:
        module('webfocus_visual').validate(report, r['producer_revision'])
    need((report is None) == (r['adapter_report_path'] is None), 'webfocus.report_request_binding')
    for key in ('originals', 'inventory', 'crosswalk', 'adapter_report'):
        need((source[key] is None and source[key + '_sha256'] is None and source[key + '_file'] is None)
             or (source[key] is not None and sha(source[key]) == source[key + '_sha256']
                 and type(source[key + '_file']) is dict), 'webfocus.source_record_hash')
    indexed = validate_inventory(source['inventory'], r, report)
    crosswalk = validate_crosswalk(source['crosswalk'], indexed, report)
    need({o['resource_path'] for o in r['operations']} <= {x['resource_path'] for x in crosswalk.values()},
         'webfocus.operation_outside_crosswalk')
    originals = {x['source_path']: x for x in source['originals']['records']}
    need(type(source['files']) is list and len(source['files']) == len(originals)
         and {x.get('source_path') for x in source['files']} == set(originals), 'webfocus.original_denominator')
    for pin in source['files']:
        need(pin.get('interpretation') == 'inert_bytes' and pin.get('sha256') == originals[pin['source_path']]['sha256'],
             'webfocus.original_pin')
    if report is not None:
        need(all(f['path'] in originals and f['sha256'] == originals[f['path']]['sha256'] for f in report['source_files']),
             'webfocus.adapter_originals_mismatch')
    need(source['definition_fingerprint'] == source_fingerprint(source), 'webfocus.definition_fingerprint')
    operations = value.get('operations')
    need(type(operations) is list and len(operations) <= r['max_total_requests']
         and type(value.get('request_count')) is int and value['request_count'] == len(operations), 'webfocus.operation_budget')
    requested = {o['operation_id']: o for o in r['operations']}
    for op in operations:
        need(type(op) is dict and op.get('key') in requested and op.get('operation') == requested[op['key']]['action']
             and op.get('method') == 'GET' and type(op.get('started_at_epoch')) in (int, float)
             and op.get('status') in ('pending', 'success', 'failed', 'rejected', 'retained_uninterpreted'), 'webfocus.operation_record')
        expected = {'request_sha256': value['request_sha256'], 'method': 'GET',
            'url': operation_url(r, requested[op['key']]), 'body_sha256': None}
        need(op.get('fingerprint_sha256') == sha(expected), 'webfocus.operation_route_binding')
        if 'http_status' in op:
            need(type(op['http_status']) is int and digest(op.get('response_sha256'))
                 and type(op.get('response_bytes')) is int and 0 <= op['response_bytes'] <= r['max_response_bytes'],
                 'webfocus.operation_response')
        if op['status'] in ('success', 'retained_uninterpreted'):
            need(op.get('http_status') == 200, 'webfocus.operation_http_success')
    pages = value.get('api_pages')
    need(type(pages) is list and len(pages) <= len(r['operations']), 'webfocus.api_page_limit')
    page_ids = set()
    for page in pages:
        need(type(page) is dict and set(page) == {'operation_id', 'content_type', 'file', 'inspection'}
             and page['operation_id'] in requested and page['operation_id'] not in page_ids
             and type(page['content_type']) is str and len(page['content_type']) <= 200, 'webfocus.api_page')
        page_ids.add(page['operation_id'])
        expected_status = ('success' if page['inspection'].get('business_success') is True else
                           'rejected' if page['inspection'].get('business_success') is False else 'retained_uninterpreted')
        need(any(op['key'] == page['operation_id'] and op['status'] == expected_status
                 and op.get('response_sha256') == page['file']['sha256'] and op.get('response_bytes') == page['file']['bytes']
                 for op in operations), 'webfocus.api_page_operation_binding')
    need({op['key'] for op in operations if op['status'] in ('success', 'retained_uninterpreted')} <= page_ids,
         'webfocus.missing_retained_response')
    attachments = value.get('attachments')
    need(type(attachments) is list and len(attachments) <= 500, 'webfocus.attachment_bound')
    ids = set()
    for row in attachments:
        validate_attachment(row, r, indexed)
        need(row['attachment_id'] not in ids and row.get('request_sha256') == value['request_sha256']
             and row.get('definition_fingerprint') == source['definition_fingerprint']
             and row.get('requested_state_sha256') == sha(r['state']) and row.get('acquisition') == 'supplied',
             'webfocus.attachment_binding')
        ids.add(row['attachment_id'])
    need(type(value.get('network_bytes')) is int and value['network_bytes'] == sum(op.get('response_bytes', 0) for op in operations)
         and 0 <= value['network_bytes'] <= r['max_total_bytes'] and type(value.get('journal_revision')) is int
         and 1 <= value['journal_revision'] <= 3000 and type(value.get('created_at_epoch')) in (int, float)
         and type(value.get('retry_not_before_epoch')) in (int, float), 'webfocus.capture_budgets')
    need(value.get('status') in ('partial', 'blocked', 'acquired_requested_operations') and type(value.get('gaps')) is list
         and set(BASE_GAPS) <= set(value['gaps']), 'webfocus.capture_status')
    if value['status'] == 'acquired_requested_operations':
        need(requested and set(requested) <= {o['key'] for o in operations if o['status'] == 'success'},
             'webfocus.false_acquisition_completion')
    seen = set()
    for pin in file_pins(value):
        need(type(pin) is dict and type(pin.get('path')) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', pin['path'])
             and pin['path'] not in seen and digest(pin.get('sha256')) and type(pin.get('bytes')) is int
             and 0 <= pin['bytes'] <= F.MAX_FILE, 'webfocus.file_pin')
        seen.add(pin['path'])
    need(sum(p['bytes'] for p in file_pins(value)) <= r['max_total_bytes'], 'webfocus.retained_byte_limit')
    return value


def verify_capture_files(value, root):
    validate_capture(value)
    root = F.no_links(root)
    raw = {p['path']: F.read_pin(root, p) for p in file_pins(value)}
    source = value['source']
    for key in ('originals', 'inventory', 'crosswalk', 'adapter_report'):
        if source[key] is not None:
            need(F.decode(raw[source[key + '_file']['path']]) == source[key], 'webfocus.source_record_original_mismatch')
    manifest = {r['source_path']: r for r in source['originals']['records']}
    for pin in source['files']:
        need(inspect_original(manifest[pin['source_path']], raw[pin['path']]) == pin.get('inspection'), 'webfocus.original_inspection_mismatch')
    requested = {o['operation_id']: o for o in value['request']['operations']}
    for page in value['api_pages']:
        info = inspect_response(raw[page['file']['path']], requested[page['operation_id']]['action'], page['content_type'])
        need(info == page['inspection'], 'webfocus.response_inspection_mismatch')
    for a in value['attachments']:
        info = inspect_attachment(raw[a['path']], a['format'])
        need(info == a.get('inspection') and (a['completeness']['row_count'] is None
             or a['completeness']['row_count'] == info.get('row_count')), 'webfocus.attachment_inspection_mismatch')
    return {'status': 'verified_local_bytes', 'files': {p['path']: p['sha256'] for p in file_pins(value)},
            'native_validation': 'not_performed'}


def _load(directory, config=None):
    root = F.private_directory(directory)
    paths = sorted(root.glob('capture-*.json'))
    need(paths and len(paths) <= 3000 and sum(F.no_links(p).stat().st_size for p in paths) <= MAX_JOURNAL_BYTES,
         'webfocus.capture_journal_missing_or_limit')
    previous = None
    for i, path in enumerate(paths, 1):
        raw = F.read_file(path, F.MAX_JSON)
        value = F.decode(raw)
        need(path.name == 'capture-%06d.json' % i and value.get('journal_revision') == i
             and value.get('previous_capture') == previous, 'webfocus.journal_chain')
        validate_capture(value)
        previous = {'path': path.name, 'sha256': F.raw_sha(raw)}
    verify_capture_files(value, root)
    need(config is None or value['request'] == validate_request(config), 'webfocus.resume_request_changed')
    value['previous_capture'] = previous
    return value, paths[-1]


def load_latest(directory, config=None):
    _, path = _load(directory, config)
    return F.decode(F.read_file(path, F.MAX_JSON)), path


def check_capture(path):
    path = F.no_links(path)
    if path.is_dir():
        value, selected = load_latest(path)
        out = verify_capture_files(value, path)
    else:
        selected = path
        out = verify_capture_files(F.decode(F.read_file(path, F.MAX_JSON)), path.parent)
    return {**out, 'output': str(selected)}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise F.CaptureError('webfocus.redirect_rejected')


def default_transport(method, url, headers, body, maximum, timeout):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    try:
        response = opener.open(Request(url, data=body, headers=headers, method=method), timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        need(response.geturl() == url and not 300 <= response.code < 400, 'webfocus.redirect_rejected')
        chunks, total = [], 0
        while True:
            need(time.monotonic() - started < timeout, 'webfocus.response_deadline')
            raw = response.read1(min(65536, maximum + 1 - total))
            if not raw:
                break
            total += len(raw)
            need(total <= maximum, 'webfocus.response_byte_limit')
            chunks.append(raw)
        return response.code, dict(response.headers), b''.join(chunks)


def capture(request, directory, *, authority=None, transport=None, resume=True, now=None):
    """Enrich imported scope with exact reviewed GETs. Host supplies authority."""
    r = validate_request(request, require_service=True)
    need(callable(authority) and resume is True, 'webfocus.import_then_host_capture_required')
    transport, now = transport or default_transport, now or utcnow
    root = F.private_directory(directory)
    fd = _lock(root)
    try:
        value, latest = _load(root, r)
        count = 0
        for operation in r['operations']:
            key = operation['operation_id']
            if any(p['operation_id'] == key for p in value['api_pages']):
                continue
            previous = [o for o in value['operations'] if o['key'] == key]
            moment = now()
            base_bytes = sum(p['bytes'] for p in file_pins(value)) - sum(p['file']['bytes'] for p in value['api_pages'])
            maximum = min(r['max_response_bytes'], r['max_total_bytes'] - base_bytes - value['network_bytes'])
            if (count >= r['max_requests_per_invocation'] or value['request_count'] >= r['max_total_requests']
                or len(previous) >= r['max_attempts_per_operation'] or maximum <= 0
                or moment < value['retry_not_before_epoch'] or moment - value['created_at_epoch'] >= r['max_elapsed_seconds']):
                break
            url = operation_url(r, operation)
            fingerprint = {'request_sha256': value['request_sha256'], 'method': 'GET', 'url': url, 'body_sha256': None}
            # Do not retain host callback exceptions or credentials anywhere.
            try:
                grant = authority(operation['action'], copy.deepcopy(fingerprint))
            except Exception:
                raise F.CaptureError('webfocus.host_authority_rejected') from None
            header = r['api_contract']['auth_header']
            need(type(grant) is dict and set(grant) == {header} and text(grant[header], 8192), 'webfocus.host_credential_header_required')
            headers = {'Accept': 'text/plain,application/xml,text/xml', **grant}
            record = {'key': key, 'operation': operation['action'], 'method': 'GET', 'fingerprint_sha256': sha(fingerprint),
                      'started_at_epoch': moment, 'status': 'pending'}
            value['operations'].append(record); value['request_count'] += 1; count += 1
            latest = advance(root, value)
            try:
                timeout = min(20, r['max_elapsed_seconds'] - (moment - value['created_at_epoch']))
                status, response_headers, raw = transport('GET', url, headers, None, maximum, timeout)
                need(type(status) is int and type(response_headers) is dict and type(raw) is bytes and len(raw) <= maximum,
                     'webfocus.transport_contract')
                record.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw))
                value['network_bytes'] += len(raw)
                screen_bytes(raw, granted=grant[header])
                need(not 300 <= status < 400, 'webfocus.redirect_rejected')
                if status != 200:
                    record['status'] = 'rejected'
                    if status == 429:
                        value['retry_not_before_epoch'] = moment + 60
                    value['gaps'].append('source_http_failure_redacted')
                    latest = advance(root, value)
                    break
                content_type = next((v for k, v in response_headers.items() if k.lower() == 'content-type'), '')
                need(type(content_type) is str and len(content_type) <= 200, 'webfocus.response_content_type')
                info = inspect_response(raw, operation['action'], content_type)
                page = {'operation_id': key, 'content_type': content_type, 'inspection': info,
                        'file': F.write_once(root, 'response-' + key + '.bin', raw)}
                value['api_pages'].append(page)
                success = info['business_success']
                record['status'] = 'success' if success is True else 'rejected' if success is False else 'retained_uninterpreted'
                if success is not True:
                    value['gaps'].append('source_business_error_redacted' if success is False else 'unsupported_response_wrapper_retained_opaque')
                latest = advance(root, value)
            except Exception:
                record['status'] = 'failed'
                value['gaps'].append('source_response_rejected_redacted')
                latest = advance(root, value)
                break
        successes = {o['key'] for o in value['operations'] if o['status'] == 'success'}
        value['status'] = 'acquired_requested_operations' if {o['operation_id'] for o in r['operations']} <= successes else 'partial'
        latest = advance(root, value)
        return result(latest)
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
    checker = sub.add_parser('check')
    checker.add_argument('--capture', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-local':
            out = import_local(F.decode(F.read_file(args.request)), args.source_root, args.directory,
                               allow_source_read=args.allow_source_read)
        elif args.command == 'import-evidence':
            out = import_evidence(args.capture, F.decode(F.read_file(args.spec)), args.source_root)
        else:
            out = check_capture(args.capture)
        print(encoded({'status': out['status'], 'output': out['output'], 'native_validation': 'not_performed'}).decode())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        print('WebFOCUS capture rejected; review the scoped contract and retained evidence.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
