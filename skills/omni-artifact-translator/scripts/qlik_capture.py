#!/usr/bin/env python3
"""Bounded Qlik evidence; passive originals and separately granted POSTs.

No login, app import, source authoring, arbitrary scripts, QIX transport or
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
    if name not in ('powerbi_capture_files', 'bounded_csv', 'qlik_visual'):
        raise ValueError('qlik.module_rejected')
    path = Path(__file__).with_name(name + '.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('qlik.module_symlink')
    spec = importlib.util.spec_from_file_location('qlik_' + name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


F = module('powerbi_capture_files')
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST = REQUEST_SCHEMA = 'qlik-visual-capture-request.v1'
SCHEMA = ENVELOPE = 'qlik-visual-capture.v1'
MAX_JOURNAL_BYTES = 128000000
BASE_GAPS = ['source_identity_and_authority_references_not_authenticated',
    'independent_inventory_is_declared_scope_not_tenant_completeness',
    'requested_state_is_not_observed_state', 'effective_access_not_verified',
    'native_rendering_and_business_acceptance_not_assessed',
    'connected_enrichment_does_not_replace_imported_snapshot',
    'qlik_layout_and_render_are_not_numerical_completeness']


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
    need(text(value, 2048), 'qlik.origin')
    p = urlsplit(value)
    need(p.scheme == 'https' and p.hostname and p.netloc == p.hostname and not p.path and not p.query
         and not p.fragment and not p.username and not p.password
         and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', p.hostname), 'qlik.https_origin_required')
    return value


def screen_text(value):
    F.safe_text(value.encode('utf-8'))
    names = r'(?:password|passwd|pwd|access[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?key|private[_-]?key)'
    need(not re.search(r'(?i)[\"\']?\b' + names + r'\b[\"\']?\s*[=:]\s*[\"\']?[^\s,;\"\'}<>]+', value)
         and not re.search(r'(?is)<\s*' + names + r'\b[^>]*>\s*[^<\s]+', value)
         and not re.search(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{12,}', value),
         'qlik.credential_bearing_text')


def screen_bytes(raw, granted=None):
    if granted:
        # Screen both full Authorization header value and its bearer credential.
        parts = [granted] + ([granted[7:]] if granted.startswith('Bearer ') else [])
        for part in parts:
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                need(part.encode(encoding) not in raw, 'qlik.credential_echo_rejected')
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
         and len(value['parameters']) <= 100 and text(value['reference']), 'qlik.state_contract')
    for key in ('timezone', 'locale', 'principal', 'cache'):
        need(value[key] is None or text(value[key]), 'qlik.state_context')
    F.decode(encoded(value)); F.secret_check(value)


state = validate_state



# Qlik-specific request, scope and asynchronous report rules are defined below.
PROFILE = 'cloud-reports-v1-20261028'


def validate_identity(value):
    keys = {'source_origin', 'tenant_id', 'product', 'version', 'principal_ref', 'engine_version', 'reference'}
    need(type(value) is dict and set(value) == keys and value['product'] in ('cloud', 'client_managed')
         and all(text(value[k]) for k in keys - {'product'}), 'qlik.identity')
    origin(value['source_origin'])


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'identity', 'root', 'authorization_ref', 'credential_ref', 'evidence_mode',
        'route', 'route_reference', 'target_surface', 'state', 'snapshot_path', 'originals_path'}
    defaults = {'api_profile': None, 'operations': [], 'max_requests_per_invocation': 8, 'max_total_requests': 100,
        'max_total_bytes': F.MAX_TOTAL, 'max_response_bytes': F.MAX_FILE, 'max_elapsed_seconds': 21600,
        'max_attempts_per_operation': 3, 'max_status_polls': 30, 'poll_interval_seconds': 2}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value['schema_version'] == REQUEST, 'qlik.request_contract')
    r = {**defaults, **copy.deepcopy(value)}
    validate_identity(r['identity']); validate_state(r['state'])
    need(local_id(r['capture_id']) and text(r['authorization_ref'])
         and (r['credential_ref'] is None or text(r['credential_ref'])), 'qlik.request_identity')
    need(type(r['root']) is dict and set(r['root']) == {'kind', 'id'} and r['root']['kind'] == 'app'
         and local_id(r['root']['id']), 'qlik.app_root')
    need(r['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant')
         and r['target_surface'] in ('app', 'dashboard', 'both'), 'qlik.request_mode')
    need(r['route'] in ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
         and (r['route'] == 'unselected' or text(r['route_reference'])), 'qlik.route')
    F.source_path(r['snapshot_path']); F.source_path(r['originals_path'])
    need(r['snapshot_path'] != r['originals_path'], 'qlik.distinct_source_records')
    for key, lo, hi in [('max_requests_per_invocation', 1, 30), ('max_total_requests', 1, 500),
        ('max_total_bytes', 1, F.MAX_TOTAL), ('max_response_bytes', 1, F.MAX_FILE), ('max_elapsed_seconds', 1, 86400),
        ('max_attempts_per_operation', 1, 5), ('max_status_polls', 1, 60), ('poll_interval_seconds', 1, 60)]:
        need(type(r[key]) is int and lo <= r[key] <= hi, 'qlik.budget')
    need(r['api_profile'] in (None, PROFILE) and type(r['operations']) is list and len(r['operations']) <= 20,
         'qlik.operation_profile')
    need(not r['operations'] or r['api_profile'] == PROFILE and r['identity']['product'] == 'cloud',
         'qlik.connected_cloud_only')
    ids, bodies = set(), set()
    for op in r['operations']:
        validate_operation(r, op)
        fingerprint = sha(op['body'])
        need(op['operation_id'] not in ids and fingerprint not in bodies, 'qlik.duplicate_operation')
        ids.add(op['operation_id']); bodies.add(fingerprint)
    need(not require_service or r['credential_ref'] is not None and bool(r['operations']), 'qlik.host_scope_required')
    F.secret_check(r); screen_bytes(encoded(r))
    return r


def validate_selections(value):
    need(type(value) is dict and len(value) <= 125, 'qlik.selection_states')
    total, fields = 0, 0
    for state_name, selections in value.items():
        need(text(state_name, 200) and type(selections) is list and len(selections) <= 125, 'qlik.selection_state')
        seen = set()
        for selection in selections:
            need(type(selection) is dict and set(selection) == {'fieldName', 'defaultIsNumeric', 'values'}
                 and text(selection['fieldName'], 500) and selection['fieldName'] not in seen
                 and type(selection['defaultIsNumeric']) is bool and type(selection['values']) is list
                 and 1 <= len(selection['values']) <= 1000, 'qlik.selection_field')
            seen.add(selection['fieldName']); fields += 1
            for selected in selection['values']:
                need(type(selected) is dict and set(selected) in ({'text', 'isNumeric'}, {'number', 'isNumeric'})
                     and type(selected['isNumeric']) is bool, 'qlik.selection_value')
                need((selected['isNumeric'] is False and set(selected) == {'text', 'isNumeric'}
                      and type(selected['text']) is str and len(selected['text']) <= 1000)
                     or (selected['isNumeric'] is True and set(selected) == {'number', 'isNumeric'}
                         and type(selected['number']) in (int, float)), 'qlik.selection_value_type')
                total += 1
    need(fields <= 125 and total <= 5000, 'qlik.selection_bound')
    F.decode(encoded(value))


def report_template(body):
    return body['senseImageTemplate'] if body['type'] == 'sense-image-1.0' else body['senseSheetTemplate']


def report_format(op):
    return 'png' if op['body']['output']['type'] == 'image' else 'pdf'


def validate_operation(request, op):
    need(type(op) is dict and set(op) == {'operation_id', 'kind', 'object_key', 'body', 'reference'}
         and local_id(op['operation_id']) and op['kind'] == 'report' and text(op['object_key'])
         and text(op['reference']) and type(op['body']) is dict, 'qlik.reviewed_report_required')
    body = op['body']; image = body.get('type') == 'sense-image-1.0'
    need(body.get('type') in ('sense-image-1.0', 'sense-sheet-1.0')
         and set(body) == {'type', 'output', 'senseImageTemplate' if image else 'senseSheetTemplate'}, 'qlik.report_body')
    template = report_template(body)
    base = {'appId', 'visualization' if image else 'sheet', 'selectionType', 'selectionStrategy'}
    need(type(template) is dict and template.get('appId') == request['root']['id']
         and template.get('selectionStrategy') == 'failOnErrors'
         and template.get('selectionType') in ('selectionsByState', 'persistentBookmark'), 'qlik.report_template')
    selection = 'selectionsByState' if template['selectionType'] == 'selectionsByState' else 'persistentBookmark'
    need(set(template) == base | {selection}, 'qlik.report_template_fields')
    if selection == 'selectionsByState':
        validate_selections(template[selection])
    else:
        need(type(template[selection]) is dict and set(template[selection]) == {'id'}
             and local_id(template[selection]['id']), 'qlik.persistent_bookmark')
    # The selected Reports profile cannot apply variable overrides safely.
    need(request['state']['parameters'] == {} and request['state']['filters'] ==
         {'selectionType': template['selectionType'], selection: template[selection]}, 'qlik.report_requested_state_mismatch')
    item = template['visualization' if image else 'sheet']
    keys = {'id', 'widthPx', 'heightPx'} | ({'type'} if image else set())
    need(type(item) is dict and set(item) == keys and local_id(item['id'])
         and (not image or item['type'] == 'visualization')
         and all(type(item[k]) is int and (5 if image else 20) <= item[k] <= 4000 for k in ('widthPx', 'heightPx')),
         'qlik.existing_object_only')
    output = body['output']
    need(type(output) is dict and local_id(output.get('outputId')) and output.get('type') in ('image', 'pdf')
         and (image or output['type'] == 'pdf'), 'qlik.output_type')
    if output['type'] == 'image':
        need(set(output) == {'type', 'outputId', 'imageOutput'} and output['imageOutput'] == {'outFormat': 'png'}, 'qlik.image_output')
    else:
        need(set(output) == {'type', 'outputId', 'pdfOutput'} and type(output['pdfOutput']) is dict
             and set(output['pdfOutput']) == {'size', 'orientation', 'resizeType'}
             and output['pdfOutput']['size'] in ('A4', 'A3', 'Letter')
             and output['pdfOutput']['orientation'] in ('P', 'L', 'A')
             and output['pdfOutput']['resizeType'] == 'autofit', 'qlik.pdf_output')
    need(len(encoded(body)) <= 65536, 'qlik.report_body_bound')


def validate_scope(request, snapshot):
    visual = module('qlik_visual')
    objects = {(row['kind'], row['id']): row for row in snapshot['objects']}
    indexed = {row['key']: row for row in snapshot['inventory']['items']}
    for op in request['operations']:
        row = indexed.get(op['object_key'])
        need(row is not None and row['disposition'] == 'include' and not visual.restricted(row, indexed, objects),
             'qlik.report_scope_not_selected')
        template = report_template(op['body']); image = op['body']['type'] == 'sense-image-1.0'
        kind = 'visual' if image else 'sheet'; mapping = row['source_mapping']
        need(row['kind'] == kind and mapping is not None and mapping['object_kind'] == kind
             and mapping['object_id'] == template['visualization' if image else 'sheet']['id'], 'qlik.report_native_object_binding')
        node = visual.mapped_node(row, objects)
        need(type(node) is dict and type(node.get('qInfo')) is dict
             and node['qInfo'].get('qId') == mapping['object_id'], 'qlik.report_native_qid')
        if image:
            need(visual.query_node(row, objects), 'qlik.report_query_visual_required')
        else:
            # A sheet render includes its children, not just the sheet metadata.
            # Qualify every native cell occurrence before releasing the render
            # grant. Unknown/container children remain supplied-render evidence.
            need(mapping['pointer'] == '' and node['qInfo'].get('qType') == 'sheet'
                 and type(node.get('cells')) is list, 'qlik.sheet_cells_required')
            members = [member for member in visual.native_members(snapshot)
                       if member['object']['kind'] == 'sheet' and member['object']['id'] == mapping['object_id']]
            need(len(members) == len(node['cells']) and all(member['kind'] == 'placement'
                 and member['pointer'] == '/cells/' + str(i) for i, member in enumerate(members)),
                 'qlik.sheet_unknown_child_requires_supplied_render')
            for i, cell in enumerate(node['cells']):
                need(type(cell) is dict and text(cell.get('name')), 'qlik.sheet_child_identity')
                expected = {'object_kind': 'sheet', 'object_id': mapping['object_id'], 'pointer': '/cells/' + str(i)}
                placements = [item for item in indexed.values() if item['source_mapping'] == expected]
                need(len(placements) == 1 and placements[0]['kind'] == 'placement'
                     and placements[0]['parent_key'] == row['key'] and placements[0]['disposition'] == 'include'
                     and not visual.restricted(placements[0], indexed, objects), 'qlik.sheet_child_not_selected')
                child = indexed.get(placements[0]['configuration'].get('visual_key'))
                need(child is not None and child['disposition'] == 'include' and child['native_id'] == cell['name']
                     and not visual.restricted(child, indexed, objects) and visual.query_node(child, objects),
                     'qlik.sheet_child_not_selected')
        if template['selectionType'] == 'persistentBookmark':
            bid = template['persistentBookmark']['id']
            need(any(x['kind'] == 'bookmark' and x['disposition'] == 'include' and x['source_mapping']
                 and x['source_mapping']['object_kind'] == 'bookmark' and x['source_mapping']['object_id'] == bid
                 and not visual.restricted(x, indexed, objects) for x in indexed.values()), 'qlik.bookmark_not_selected')


validate_operation_scope = validate_scope


def safe_output_url(config, location):
    need(text(location, 2048), 'qlik.output_location')
    parsed, expected = urlsplit(location), urlsplit(config['identity']['source_origin'])
    need(parsed.scheme == 'https' and parsed.hostname == expected.hostname and not parsed.username and not parsed.password
         and parsed.port in (None, 443) and not parsed.fragment and parsed.query in ('', 'inline=1')
         and re.fullmatch(r'/api/v1/temp-contents/[A-Za-z0-9][A-Za-z0-9_-]{0,100}', parsed.path),
         'qlik.output_route_requires_supplied_transfer')
    return config['identity']['source_origin'] + parsed.path + ('?' + parsed.query if parsed.query else '')


def operation_spec(config, op, phase='create', request_id=None, location=None):
    r = validate_request(config)
    need(op in r['operations'], 'qlik.operation_not_selected')
    base = r['identity']['source_origin']
    if phase == 'create':
        need(request_id is None and location is None, 'qlik.create_dynamic_fields')
        return {'scope': 'render', 'method': 'POST', 'url': base + '/api/v1/reports', 'body': copy.deepcopy(op['body'])}
    need(local_id(request_id), 'qlik.report_request_id')
    if phase in ('status', 'outputs'):
        need(location is None, 'qlik.unexpected_output_location')
        url = base + '/api/v1/reports/' + request_id + '/' + phase
    else:
        need(phase == 'download', 'qlik.report_phase')
        url = safe_output_url(r, location)
    return {'scope': 'render', 'method': 'GET', 'url': url, 'body': None}


def pointer(value, path):
    need(type(path) is str and len(path) <= 1000 and (path == '' or path.startswith('/'))
         and re.search(r'~(?![01])', path) is None, 'qlik.json_pointer')
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(part in value, 'qlik.pointer_missing'); value = value[part]
        elif type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', part) is not None and int(part) < len(value), 'qlik.pointer_missing')
            value = value[int(part)]
        else:
            raise F.CaptureError('qlik.pointer_missing')
    return value


def validate_originals(manifest, snapshot):
    need(type(manifest) is dict and set(manifest) == {'schema_version', 'reference', 'records'}
         and manifest['schema_version'] == 'qlik-originals.v1' and text(manifest['reference'])
         and type(manifest['records']) is list and 1 <= len(manifest['records']) <= 500, 'qlik.originals_manifest')
    expected = {'/inventory'} | {'/objects/%d/payload' % i for i in range(len(snapshot['objects']))}
    targets, paths, aliases = set(), set(), {}
    for row in manifest['records']:
        need(type(row) is dict and set(row) == {'source_path', 'source_kind', 'source_pointer', 'target_pointer', 'mapping',
             'member_path', 'reference', 'mcp_evidence'} and row['source_kind'] in
             ('rest_json', 'supplied_json', 'qix_json', 'mcp_json', 'script', 'zip', 'opaque') and text(row['reference'])
             and row['mapping'] in ('exact_json', 'opaque_preserved'), 'qlik.original_record')
        path = F.source_path(row['source_path'])
        folded = unicodedata.normalize('NFC', path).casefold()
        need(folded not in aliases or aliases[folded] == path, 'qlik.original_path_alias')
        need(not any(path != p and (path.startswith(p + '/') or p.startswith(path + '/')) for p in paths),
             'qlik.original_path_collision')
        aliases[folded] = path; paths.add(path)
        if row['member_path'] is not None:
            F.source_path(row['member_path'])
            need(row['source_kind'] == 'zip', 'qlik.member_requires_zip')
        target = row['target_pointer']
        need(target is None or (target in expected and target not in targets), 'qlik.original_target')
        if target is not None:
            targets.add(target)
        if row['mapping'] == 'exact_json':
            need(row['source_kind'] in ('rest_json', 'supplied_json', 'qix_json', 'mcp_json', 'zip') and target is not None
                 and type(row['source_pointer']) is str, 'qlik.exact_json_mapping')
        else:
            need(row['source_pointer'] is None and target != '/inventory', 'qlik.opaque_mapping')
        need(row['mcp_evidence'] is None or row['source_kind'] == 'mcp_json' and
             type(row['mcp_evidence']) is dict and set(row['mcp_evidence']) == {'reference', 'schema_reference', 'tool_name', 'call_id', 'server_version'}
             and all(text(v) for v in row['mcp_evidence'].values()), 'qlik.mcp_provenance')
    need(targets == expected, 'qlik.original_object_denominator')
    F.secret_check(manifest)
    return manifest


def zip_members(raw):
    """Bounded in-memory inventory; no filesystem extraction or YAML decoding."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            need(1 <= len(entries) <= 500, 'qlik.zip_member_limit')
            members, names, prefixes, total = {}, set(), {}, 0
            for item in entries:
                path = item.filename[:-1] if item.is_dir() else item.filename
                F.source_path(path)
                folded = unicodedata.normalize('NFC', path).casefold()
                need(folded not in names, 'qlik.zip_path_collision'); names.add(folded)
                parts = path.split('/')
                for i in range(1, len(parts) + 1):
                    prefix = '/'.join(parts[:i]); key = unicodedata.normalize('NFC', prefix).casefold()
                    need(key not in prefixes or prefixes[key] == prefix, 'qlik.zip_path_alias'); prefixes[key] = prefix
                mode = item.external_attr >> 16
                need(not item.flag_bits & 1 and item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                     and stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'qlik.zip_unsafe_member')
                if item.is_dir():
                    continue
                total += item.file_size
                need(total <= F.MAX_TOTAL and item.file_size <= F.MAX_FILE
                     and item.file_size <= max(1, item.compress_size) * 100, 'qlik.zip_expansion_limit')
                with archive.open(item) as stream:
                    content = stream.read(F.MAX_FILE + 1)
                need(len(content) == item.file_size <= F.MAX_FILE, 'qlik.zip_size_mismatch')
                suffix = Path(path).suffix.lower()
                screening = screen_bytes(content) if suffix in ('.yaml', '.yml', '.tml', '.json', '.txt', '.csv', '.xml', '.html', '.js') else screen_opaque(content)
                members[path] = {'bytes': len(content), 'sha256': F.raw_sha(content), 'credential_screening': screening, 'raw': content}
            file_names = {unicodedata.normalize('NFC', path).casefold() for path in members}
            need(not any(a != b and a.startswith(b + '/') for a in names for b in file_names), 'qlik.zip_file_directory_collision')
            return members
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        raise F.CaptureError('qlik.invalid_zip') from None


def inspect_original(row, raw, snapshot):
    content = raw
    inspection = {'interpretation': 'inert_bytes', 'source_code_execution': False}
    if row['source_kind'] == 'zip':
        members = zip_members(raw)
        inspection['members'] = [{'path': path, **{k: v for k, v in record.items() if k != 'raw'}} for path, record in members.items()]
        inspection['interpretation'] = 'zip_members_only'
        if row['member_path'] is not None:
            need(row['member_path'] in members, 'qlik.zip_member_missing')
            content = members[row['member_path']]['raw']
        else:
            need(row['mapping'] == 'opaque_preserved' and row['target_pointer'] is None, 'qlik.zip_member_mapping_required')
    elif row['source_kind'] in ('script', 'rest_json', 'supplied_json', 'qix_json', 'mcp_json'):
        inspection['credential_screening'] = screen_bytes(raw)
    else:
        inspection['credential_screening'] = screen_opaque(raw)
    if row['mapping'] == 'exact_json':
        original = F.decode(content); F.secret_check(original)
        selected = pointer(original, row['source_pointer'])
        need(selected == pointer(snapshot, row['target_pointer']), 'qlik.original_payload_mismatch')
        inspection['interpretation'] = 'exact_json_pointer'
    elif row['target_pointer'] is not None:
        expected = {'opaque_original': {'source_path': row['source_path'], 'member_path': row['member_path'],
                                       'sha256': F.raw_sha(content)}}
        need(pointer(snapshot, row['target_pointer']) == expected, 'qlik.opaque_placeholder_mismatch')
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
        need(type(pin) is dict and type(pin.get('path')) is str, 'qlik.file_pin')
        need(pin['path'] not in unique or unique[pin['path']] == pin, 'qlik.file_pin_collision')
        unique[pin['path']] = pin
    return list(unique.values())


def _save(root, value):
    value['journal_revision'] += 1
    value.pop('content_hash', None); value['content_hash'] = sha(value)
    raw = encoded(value)
    snapshots = list(root.glob('capture-*.json'))
    need(len(snapshots) < 3000 and len(raw) <= F.MAX_JSON and
         len(raw) + sum(F.no_links(p).stat().st_size for p in snapshots) <= MAX_JOURNAL_BYTES, 'qlik.journal_budget')
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
    module('qlik_visual').validate_snapshot(value)
    if request is not None:
        need(value['identity'] == request['identity'] and value['root'] == request['root'], 'qlik.snapshot_request_identity')
    F.secret_check(value)
    return value


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read is True, 'qlik.source_read_grant_required')
    r = validate_request(request)
    source_root, root = F.no_links(source_root), F.private_directory(directory)
    need(source_root.is_dir() and not list(root.iterdir()), 'qlik.new_directory_required')
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
        need(work <= 128000000, 'qlik.mapping_work_limit')
        info = inspect_original(row, raw, snapshot)
        need(total <= r['max_total_bytes'], 'qlik.source_byte_limit')
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
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'qlik.attachment_size')
    need(parser_profile is None or format == 'json' and type(parser_profile) is dict
         and parser_profile.get('format') == 'json' and parser_profile.get('shape') in ('qlik_straight', 'qlik_pivot'),
         'qlik.attachment_parser_profile')
    if format == 'png':
        return F.png_info(raw)
    if format == 'pdf':
        need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'qlik.pdf_signature')
        return {'validation': 'signature_only_not_rendered'}
    screen_bytes(raw)
    if format == 'json':
        value = F.decode(raw); F.secret_check(value)
        if parser_profile is not None:
            # Reuse the explicit QIX projection and typed normalizer. This
            # local inspection context is never emitted as capture/QA evidence.
            raw_hash = F.raw_sha(raw)
            binding = {k: raw_hash for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256')}
            binding.update(object_key='local-inspection-only', attachment_id='local-inspection-only')
            normalized = module('qlik_visual').normalize_results(raw, parser_profile, binding)
            return {'row_count': normalized['row_count'], 'interpretation': 'explicit_qix_matrix_profile',
                    'parser_profile_sha256': sha(parser_profile), 'completeness': 'not_inferred'}
        rows = value if type(value) is list and all(type(x) is dict for x in value) else None
        need(rows is None or len(rows) <= 100000, 'qlik.result_row_limit')
        # Vendor response wrappers stay original JSON. Their paging/result grain
        # cannot be inferred from the length of a wrapper list.
        flat = rows is not None and all(all(type(v) in (str, int, float, bool) or v is None for v in row.values()) for row in rows)
        return {'row_count': len(rows) if flat else None, 'interpretation': 'object_rows_json' if flat else 'native_json_unqualified',
                'completeness': 'not_inferred'}
    need(format == 'csv', 'qlik.attachment_format')
    try:
        header = next(csv.reader(io.StringIO(raw.decode('utf-8-sig')), strict=True))
        need(0 < len(header) <= 512 and len(set(header)) == len(header) and all(text(x) for x in header), 'qlik.csv_headers')
        count = 0
        for row in module('bounded_csv').rows(raw, header, 'qlik'):
            F.secret_check(dict(zip(header, row))); count += 1
        return {'headers': header, 'row_count': count, 'interpretation': 'utf8_comma_csv', 'completeness': 'not_inferred'}
    except (UnicodeError, csv.Error, StopIteration):
        raise F.CaptureError('qlik.invalid_csv') from None


def validate_attachment(row, request, snapshot):
    required = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
        'population', 'freshness', 'completeness', 'reference'}
    derived = {'source_path', 'path', 'sha256', 'bytes', 'request_sha256', 'definition_fingerprint',
        'requested_state_sha256', 'inspection', 'acquisition', 'member_path', 'archive_file', 'parser_profile'}
    inventory = {x['key']: x for x in snapshot['inventory']['items']}
    need(type(row) is dict and required <= set(row) <= required | derived and local_id(row['attachment_id'])
         and row['object_key'] in inventory and row['format'] in ('csv', 'json', 'png', 'pdf') and text(row['reference']),
         'qlik.attachment_contract')
    need('parser_profile' not in row or row['format'] == 'json' and type(row['parser_profile']) is dict
         and row['parser_profile'].get('format') == 'json' and row['parser_profile'].get('shape') in ('qlik_straight', 'qlik_pivot'),
         'qlik.attachment_parser_profile')
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown') and row['result_scope'] in
         ('query_result', 'transformed', 'displayed', 'unknown') and
         (row['origin'] not in ('displayed', 'transformed') or row['origin'] == row['result_scope']), 'qlik.result_origin')
    observed = row['observed_state']
    if observed is not None:
        need(type(observed) is dict and {'state', 'observed_at', 'reference'} <= set(observed) <=
             {'state', 'observed_at', 'reference', 'placement_reference', 'result_context', 'tab_id'}
             and text(observed['observed_at']) and text(observed['reference']), 'qlik.observed_state')
        validate_state(observed['state'])
        for key in ('placement_reference', 'tab_id'):
            need(key not in observed or text(observed[key]), 'qlik.observed_context_reference')
        if 'result_context' in observed:
            module('qlik_visual').result_context(observed['result_context'])
    for key, fields in (('population', {'key', 'description', 'reference'}),
                        ('freshness', {'data_watermark', 'observed_at', 'reference'})):
        need(type(row[key]) is dict and set(row[key]) == fields and all(v is None or text(v) for v in row[key].values()),
             'qlik.' + key)
    c = row['completeness']
    need(type(c) is dict and set(c) == {'status', 'reference', 'row_count'} and c['status'] in ('complete', 'partial', 'unknown')
         and (c['reference'] is None or text(c['reference'])) and
         (c['row_count'] is None or (type(c['row_count']) is int and 0 <= c['row_count'] <= 100000)), 'qlik.completeness')
    if c['status'] == 'complete':
        need(row['format'] in ('csv', 'json') and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and observed is not None and text(observed['state']['principal']) and all(row['population'].values())
             and all(row['freshness'].values()) and text(c['reference']) and type(c['row_count']) is int,
             'qlik.complete_result_evidence_required')
    F.secret_check(row)


def _lock(root):
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), 'qlik.lock_type')
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
             and spec['schema_version'] == 'qlik-supplied-evidence.v1' and type(spec['attachments']) is list
             and len(spec['attachments']) <= 100, 'qlik.evidence_import')
        seen = {a['attachment_id'] for a in value['attachments']}
        need(len(seen) + len(spec['attachments']) <= 500, 'qlik.attachment_count')
        keys = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
                'population', 'freshness', 'completeness', 'reference', 'source_path', 'member_path'}
        pending, total = [], sum(p['bytes'] for p in file_pins(value))
        for row in spec['attachments']:
            need(type(row) is dict and keys <= set(row) <= keys | {'parser_profile'}, 'qlik.supplied_attachment_fields')
            validate_attachment(row, value['request'], value['source']['snapshot'])
            need(row['attachment_id'] not in seen, 'qlik.duplicate_attachment'); seen.add(row['attachment_id'])
            original = F.read_file(source_root / F.source_path(row['source_path']))
            raw, archive = original, None
            if row['member_path'] is not None:
                F.source_path(row['member_path'])
                members = zip_members(original)
                need(row['member_path'] in members, 'qlik.zip_member_missing')
                raw, archive = members[row['member_path']]['raw'], original
            info = inspect_attachment(raw, row['format'], row.get('parser_profile'))
            need(row['completeness']['row_count'] is None or row['completeness']['row_count'] == info.get('row_count'),
                 'qlik.result_count_or_shape_unqualified')
            total += len(raw) + (len(archive) if archive is not None else 0)
            need(total <= value['request']['max_total_bytes'], 'qlik.retained_byte_limit')
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


def _execution_state(value):
    attempted = any(op['phase'] == 'create' and op.get('dispatched') is True for op in value['operations'])
    value['source_execution'] = attempted
    value['saved_query_execution'] = 'not_requested'
    value['render_execution'] = 'attempted' if attempted else 'not_run' if value['request']['operations'] else 'not_requested'


def no_business_errors(data):
    stack = [data]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, value in item.items():
                need(key not in ('errors', 'error', 'exportErrors', 'requestErrors', 'selectionErrors', 'appErrors') or not value,
                     'qlik.report_or_selection_error')
                stack.append(value)
        elif type(item) is list:
            stack.extend(item)


def inspect_response(raw, config, op, phase, request_id=None):
    if phase == 'download':
        format = report_format(op)
        return {'phase': phase, 'format': format, 'inspection': inspect_attachment(raw, format),
                'observed_state': None, 'numerical_completeness': 'not_established'}
    screen_bytes(raw); data = F.decode(raw); F.secret_check(data); no_business_errors(data)
    need(type(data) is dict, 'qlik.report_response_object')
    if phase == 'create':
        rid = data.get('requestId')
        need(local_id(rid), 'qlik.report_id_missing')
        if 'outputsUrl' in data:
            target = urlsplit(data['outputsUrl'])
            need(target.scheme == 'https' and target.hostname == urlsplit(config['identity']['source_origin']).hostname
                 and target.port in (None, 443) and not target.username and not target.password
                 and target.path == '/api/v1/reports/' + rid + '/outputs' and not target.query and not target.fragment,
                 'qlik.outputs_url_rejected')
        return {'phase': phase, 'request_id': rid, 'report_status': 'accepted', 'observed_state': None}
    if phase == 'status':
        status = data.get('status')
        need(status in ('queued', 'processing', 'visiting', 'done'), 'qlik.report_failed_or_unknown_status')
        return {'phase': phase, 'request_id': request_id, 'report_status': status, 'observed_state': None}
    need(phase == 'outputs' and type(data.get('data')) is list and len(data['data']) == 1,
         'qlik.single_output_required')
    output = data['data'][0]
    need(type(output) is dict and output.get('outputId') == op['body']['output']['outputId']
         and output.get('status') == 'done', 'qlik.output_not_done_or_scope_mismatch')
    location = safe_output_url(config, output.get('location'))
    if 'sizeBytes' in output:
        need(type(output['sizeBytes']) is int and 0 <= output['sizeBytes'] <= config['max_response_bytes'], 'qlik.output_size_bound')
    return {'phase': phase, 'request_id': request_id, 'output_id': output['outputId'], 'location': location,
            'declared_bytes': output.get('sizeBytes'), 'observed_state': None}


def next_operation(config, op, records, responses):
    """Derive a lifecycle step exclusively from preceding successful byte pins."""
    evidence = {row['attempt']: row['inspection'] for row in responses}
    previous = [(i, row, evidence[i]) for i, row in enumerate(records)
                if row['key'] == op['operation_id'] and row['status'] == 'success' and i in evidence]
    created = [info for _, row, info in previous if row['phase'] == 'create']
    need(len(created) <= 1, 'qlik.report_reposted')
    phase, rid, location = 'create', None, None
    if created:
        rid = created[0]['request_id']; phase = 'status'
        statuses = [info for _, row, info in previous if row['phase'] == 'status']
        if statuses and statuses[-1]['report_status'] == 'done':
            phase = 'outputs'
            outputs = [info for _, row, info in previous if row['phase'] == 'outputs']
            need(len(outputs) <= 1, 'qlik.outputs_reacquired')
            if outputs:
                phase, location = 'download', outputs[0]['location']
                if any(row['phase'] == 'download' for _, row, _ in previous):
                    return None
    spec = operation_spec(config, op, phase, rid, location)
    return {**spec, 'operation_id': op['operation_id'], 'phase': phase, 'request_id': rid, 'location': location}


def fingerprint(config, selected):
    return {'request_sha256': sha(config), 'operation_id': selected['operation_id'], 'phase': selected['phase'],
            'method': selected['method'], 'url': selected['url'], 'body_sha256': sha(selected['body'])}


def pending_operation_spec(config, envelope):
    value = validate_envelope(envelope); r = validate_request(config)
    need(value['request'] == r and value['operations'] and value['operations'][-1]['status'] == 'pending'
         and not any(o['status'] == 'pending' for o in value['operations'][:-1]), 'qlik.pending_operation_required')
    record = value['operations'][-1]
    op = next(o for o in r['operations'] if o['operation_id'] == record['key'])
    selected = next_operation(r, op, value['operations'][:-1], value['responses'])
    need(selected is not None and record['fingerprint_sha256'] == sha(fingerprint(r, selected)), 'qlik.pending_route_binding')
    return {key: selected[key] for key in ('scope', 'operation_id', 'phase', 'method', 'url', 'body')}


def validate_envelope(value):
    need(type(value) is dict and value.get('schema_version') == ENVELOPE and value.get('content_hash') ==
         sha({k: v for k, v in value.items() if k != 'content_hash'}), 'qlik.capture_hash_or_schema')
    r = validate_request(value.get('request'))
    need(r == value['request'] and value.get('request_sha256') == sha(r) and value.get('capture_id') == r['capture_id'],
         'qlik.capture_request')
    need(value.get('target_write_authority') is False and value.get('arbitrary_source_code_execution') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed', 'qlik.capture_authority')
    source = value.get('source')
    need(type(source) is dict and set(source) == {'snapshot', 'snapshot_file', 'definition_fingerprint', 'originals_manifest',
         'originals_manifest_file', 'originals'}, 'qlik.capture_source')
    validate_snapshot(source['snapshot'], r); validate_originals(source['originals_manifest'], source['snapshot']); validate_scope(r, source['snapshot'])
    need(source['definition_fingerprint'] == sha(source['snapshot']) and type(source['originals']) is list
         and len(source['originals']) == len(source['originals_manifest']['records']), 'qlik.source_originals')
    for declared, record in zip(source['originals_manifest']['records'], source['originals']):
        need(type(record) is dict and set(record) == set(declared) | {'file', 'inspection'}
             and all(record[k] == declared[k] for k in declared), 'qlik.original_record_changed')
    requested = {o['operation_id']: o for o in r['operations']}
    records, responses = value.get('operations'), value.get('responses')
    need(type(records) is list and len(records) <= r['max_total_requests'] and value.get('request_count') == len(records)
         and type(responses) is list and len(responses) <= len(records), 'qlik.operation_budget')
    success, seen = [], set()
    for response in responses:
        need(type(response) is dict and set(response) == {'attempt', 'file', 'inspection'}
             and type(response['attempt']) is int and 0 <= response['attempt'] < len(records)
             and response['attempt'] not in seen, 'qlik.response_record')
        seen.add(response['attempt'])
    for i, record in enumerate(records):
        need(type(record) is dict and record.get('key') in requested and record.get('status') in ('pending', 'success', 'rejected', 'uncertain', 'denied')
             and type(record.get('dispatched')) is bool and type(record.get('started_at_epoch')) in (int, float)
             and (record['status'] != 'denied' or record['dispatched'] is False and 'http_status' not in record)
             and (record['status'] not in ('success', 'rejected') and 'http_status' not in record
                  or record['dispatched'] is True), 'qlik.operation_record')
        selected = next_operation(r, requested[record['key']], records[:i], [x for x in responses if x['attempt'] < i])
        need(selected is not None and all(record.get(k) == selected[k] for k in ('phase', 'scope', 'method', 'request_id', 'location'))
             and record.get('fingerprint_sha256') == sha(fingerprint(r, selected)), 'qlik.operation_route_binding')
        if 'http_status' in record:
            need(type(record['http_status']) is int and digest(record.get('response_sha256'))
                 and type(record.get('response_bytes')) is int and 0 <= record['response_bytes'] <= r['max_response_bytes'], 'qlik.response_metadata')
        if record['status'] == 'success':
            response = next((x for x in responses if x['attempt'] == i), None)
            need(response is not None and record.get('http_status') == (202 if record['phase'] == 'create' else 200)
                 and response['file']['sha256'] == record['response_sha256'] and response['file']['bytes'] == record['response_bytes'],
                 'qlik.response_attempt_binding')
            success.append(i)
    need(set(success) == seen, 'qlik.response_denominator')
    execution = copy.deepcopy(value); _execution_state(execution)
    need(all(value.get(k) == execution[k] for k in ('source_execution', 'saved_query_execution', 'render_execution')), 'qlik.execution_claim')
    attachments = value.get('attachments')
    need(type(attachments) is list and len(attachments) <= 500, 'qlik.attachment_count')
    ids = set()
    for row in attachments:
        validate_attachment(row, r, source['snapshot'])
        need(row['attachment_id'] not in ids and row.get('request_sha256') == value['request_sha256']
             and row.get('definition_fingerprint') == source['definition_fingerprint'] and row.get('requested_state_sha256') == sha(r['state'])
             and row.get('acquisition') == 'supplied' and 'source_path' not in row
             and (row.get('member_path') is None) == (row.get('archive_file') is None), 'qlik.attachment_binding')
        ids.add(row['attachment_id'])
    need(type(value.get('network_bytes')) is int and value['network_bytes'] == sum(o.get('response_bytes', 0) for o in records)
         and 0 <= value['network_bytes'] <= r['max_total_bytes'] and type(value.get('journal_revision')) is int
         and 1 <= value['journal_revision'] <= 3000 and type(value.get('created_at_epoch')) in (int, float)
         and type(value.get('retry_not_before_epoch')) in (int, float), 'qlik.capture_budget')
    need(value.get('status') in ('partial', 'blocked', 'acquired_requested_operations') and type(value.get('gaps')) is list
         and set(BASE_GAPS) <= set(value['gaps']), 'qlik.capture_status')
    if value['status'] == 'acquired_requested_operations':
        need(requested and all(next_operation(r, op, records, responses) is None for op in requested.values()), 'qlik.false_acquisition_completion')
    for pin in file_pins(value):
        need(type(pin.get('path')) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', pin['path'])
             and digest(pin.get('sha256')) and type(pin.get('bytes')) is int and 0 <= pin['bytes'] <= F.MAX_FILE, 'qlik.file_pin')
    need(sum(p['bytes'] for p in file_pins(value)) <= r['max_total_bytes'], 'qlik.retained_byte_limit')
    return value


validate_capture = validate_envelope


def verify_capture_files(value, root):
    validate_envelope(value)
    raw = {p['path']: F.read_pin(F.no_links(root), p) for p in file_pins(value)}
    source = value['source']
    need(F.decode(raw[source['snapshot_file']['path']]) == source['snapshot'] and
         F.decode(raw[source['originals_manifest_file']['path']]) == source['originals_manifest'], 'qlik.original_snapshot_mismatch')
    work = 0
    for row in source['originals']:
        work += row['file']['bytes']; need(work <= 128000000, 'qlik.mapping_work_limit')
        need(inspect_original(row, raw[row['file']['path']], source['snapshot']) == row['inspection'], 'qlik.original_inspection_mismatch')
    for row in value['attachments']:
        content = raw[row['path']]
        if row.get('archive_file') is not None:
            members = zip_members(raw[row['archive_file']['path']])
            need(row['member_path'] in members and members[row['member_path']]['raw'] == content, 'qlik.attachment_member_mismatch')
        info = inspect_attachment(content, row['format'], row.get('parser_profile'))
        need(info == row['inspection'] and (row['completeness']['row_count'] is None or row['completeness']['row_count'] == info.get('row_count')),
             'qlik.attachment_inspection_mismatch')
    selected = {o['operation_id']: o for o in value['request']['operations']}
    for response in value['responses']:
        record = value['operations'][response['attempt']]
        info = inspect_response(raw[response['file']['path']], value['request'], selected[record['key']], record['phase'], record['request_id'])
        need(info == response['inspection'], 'qlik.response_inspection_mismatch')
    return {'status': 'verified_local_bytes', 'files': {p['path']: p['sha256'] for p in file_pins(value)}, 'native_validation': 'not_performed'}




def validate_transition(previous, current):
    """Hash-linked journal updates may extend evidence, never reset authority or attempts."""
    if previous is None:
        need(current['journal_revision'] == 1 and current['previous_capture'] is None
             and not current['operations'] and not current['responses'] and not current['attachments']
             and current['request_count'] == current['network_bytes'] == current['retry_not_before_epoch'] == 0
             and current['status'] == 'partial', 'qlik.initial_journal_state')
        return
    immutable = ('schema_version', 'capture_id', 'request', 'request_sha256', 'source', 'created_at_epoch',
        'target_write_authority', 'arbitrary_source_code_execution', 'native_validation', 'business_acceptance')
    need(all(current[key] == previous[key] for key in immutable), 'qlik.immutable_capture_changed')
    for key in ('request_count', 'network_bytes', 'retry_not_before_epoch'):
        need(current[key] >= previous[key], 'qlik.journal_counter_rollback')
    for key in ('responses', 'attachments', 'gaps'):
        need(len(current[key]) >= len(previous[key]) and current[key][:len(previous[key])] == previous[key],
             'qlik.journal_evidence_rewritten')
    before, after = previous['operations'], current['operations']
    need(len(before) <= len(after) <= len(before) + 1, 'qlik.journal_attempts_rewritten')
    changed = 0
    for old, new in zip(before, after):
        if old == new:
            continue
        changed += 1
        allowed = {'http_status', 'response_sha256', 'response_bytes'}
        need(old['status'] == 'pending' and new['status'] in ('success', 'rejected', 'uncertain', 'denied', 'pending')
             and set(new) <= set(old) | allowed
             and all(new.get(k) == v for k, v in old.items() if k not in ('status', 'dispatched'))
             and (old['dispatched'] == new['dispatched'] or old['dispatched'] is False and new['dispatched'] is True
                  and new['status'] == 'pending')
             and (new['status'] != 'pending' or old['dispatched'] is False and new['dispatched'] is True),
             'qlik.terminal_attempt_rewritten')
        if new['status'] == 'rejected':
            need(type(new.get('http_status')) is int and 400 <= new['http_status'] < 500,
                 'qlik.rejected_attempt_status')
    need(changed <= 1, 'qlik.multiple_attempt_resolution')
    if len(after) > len(before):
        new = after[-1]
        need(changed == 0 and not any(o['status'] == 'pending' or o['phase'] == 'create' and o['status'] == 'uncertain' for o in before)
             and new['status'] == 'pending' and set(new) ==
             {'key', 'phase', 'request_id', 'location', 'scope', 'method', 'fingerprint_sha256', 'started_at_epoch', 'status', 'dispatched'}
             and new['dispatched'] is False
             and new['started_at_epoch'] >= previous['retry_not_before_epoch']
             and sum(o['key'] == new['key'] and o['phase'] == new['phase'] for o in after) <= (current['request']['max_status_polls'] if new['phase'] == 'status' else current['request']['max_attempts_per_operation']),
             'qlik.unresolved_post_or_attempt_limit')


def _load(directory, config=None):
    root = F.private_directory(directory)
    paths = sorted(root.glob('capture-*.json'))
    need(paths and len(paths) <= 3000 and sum(F.no_links(p).stat().st_size for p in paths) <= MAX_JOURNAL_BYTES,
         'qlik.capture_journal_missing_or_limit')
    previous, previous_value = None, None
    for i, path in enumerate(paths, 1):
        raw = F.read_file(path, F.MAX_JSON); value = F.decode(raw)
        need(path.name == 'capture-%06d.json' % i and value.get('journal_revision') == i and
             value.get('previous_capture') == previous, 'qlik.journal_chain')
        validate_envelope(value)
        validate_transition(previous_value, value)
        previous_value = value
        previous = {'path': path.name, 'sha256': F.raw_sha(raw)}
    verify_capture_files(value, root)
    need(config is None or value['request'] == validate_request(config), 'qlik.resume_request_changed')
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
        raise F.CaptureError('qlik.redirect_rejected')


def default_transport(method, url, headers, body, maximum, timeout):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    try:
        response = opener.open(Request(url, data=body, headers=headers, method=method), timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        need(response.geturl() == url and not 300 <= response.code < 400, 'qlik.redirect_rejected')
        chunks, total = [], 0
        while True:
            need(time.monotonic() - started < timeout, 'qlik.response_deadline')
            data = response.read1(min(65536, maximum + 1 - total))
            if not data:
                break
            total += len(data)
            need(total <= maximum, 'qlik.response_byte_limit'); chunks.append(data)
        return response.code, dict(response.headers), b''.join(chunks)


def capture(request, directory, *, authority=None, transport=None, resume=True, now=None):
    r = validate_request(request, require_service=True)
    need(callable(authority) and resume is True, 'qlik.import_then_host_capture_required')
    root = F.private_directory(directory)
    transport, now = transport or default_transport, now or utcnow
    fd = _lock(root)
    try:
        value, latest = _load(root, r)
        # GET retries are safe to journal again; an uncertain create is never replayed.
        for record in value['operations']:
            if record['status'] == 'pending' and record['method'] == 'GET':
                record['status'] = 'uncertain'; latest = advance(root, value)
        count, stop = 0, False
        for op in r['operations']:
            while not stop:
                if any(o['phase'] == 'create' and o['status'] in ('pending', 'uncertain') for o in value['operations']):
                    value['status'] = 'blocked'
                    if 'uncertain_report_post_requires_resolution_no_blind_replay' not in value['gaps']:
                        value['gaps'].append('uncertain_report_post_requires_resolution_no_blind_replay')
                    stop = True; break
                selected = next_operation(r, op, value['operations'], value['responses'])
                if selected is None:
                    break
                moment = now(); phase = selected['phase']
                prior = [x for x in value['operations'] if x['key'] == op['operation_id'] and x['phase'] == phase]
                bound = r['max_status_polls'] if phase == 'status' else r['max_attempts_per_operation']
                base_bytes = sum(p['bytes'] for p in file_pins(value)) - sum(x['file']['bytes'] for x in value['responses'])
                maximum = min(r['max_response_bytes'], r['max_total_bytes'] - base_bytes - value['network_bytes'])
                if (count >= r['max_requests_per_invocation'] or value['request_count'] >= r['max_total_requests']
                    or len(prior) >= bound or maximum <= 0 or moment < value['retry_not_before_epoch']
                    or moment - value['created_at_epoch'] >= r['max_elapsed_seconds']):
                    stop = True; break
                record = {'key': op['operation_id'], **{key: selected[key] for key in ('phase', 'request_id', 'location', 'scope', 'method')},
                          'fingerprint_sha256': sha(fingerprint(r, selected)), 'started_at_epoch': moment, 'status': 'pending', 'dispatched': False}
                value['operations'].append(record); value['request_count'] += 1; count += 1
                _execution_state(value); latest = advance(root, value)
                # Host independently reads this pending journal and prior source pins.
                try:
                    grant = authority('render', copy.deepcopy(fingerprint(r, selected)))
                    need(type(grant) is dict and set(grant) == {'Authorization'} and text(grant['Authorization'], 8192)
                         and grant['Authorization'].startswith('Bearer ') and len(grant['Authorization']) > 7, 'qlik.host_bearer_required')
                except Exception:
                    # No request was sent; do not pretend a pending POST was dispatched.
                    record['status'] = 'denied'
                    value['gaps'].append('host_authority_rejected_no_dispatch'); latest = advance(root, value)
                    raise F.CaptureError('qlik.host_authority_rejected') from None
                record['dispatched'] = True; _execution_state(value); latest = advance(root, value)
                try:
                    timeout = min(20, r['max_elapsed_seconds'] - (moment - value['created_at_epoch']))
                    status, headers, raw = transport(selected['method'], selected['url'],
                        {'Accept': 'application/json,image/png,application/pdf', 'Content-Type': 'application/json', **grant},
                        encoded(selected['body']) if selected['body'] is not None else None, maximum, timeout)
                    need(type(status) is int and type(headers) is dict and type(raw) is bytes and len(raw) <= maximum, 'qlik.transport_contract')
                    record.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw))
                    value['network_bytes'] += len(raw)
                    for token in (grant['Authorization'], grant['Authorization'][7:]):
                        for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                            need(token.encode(encoding) not in raw, 'qlik.credential_echo_rejected')
                    need(not 300 <= status < 400, 'qlik.redirect_rejected')
                    if status != (202 if phase == 'create' else 200):
                        record['status'] = 'rejected' if 400 <= status < 500 else 'uncertain'
                        if status == 429:
                            value['retry_not_before_epoch'] = max(value['retry_not_before_epoch'], moment + 60)
                        value['gaps'].append('source_http_failure_redacted'); latest = advance(root, value); stop = True; break
                    inspection = inspect_response(raw, r, op, phase, selected['request_id'])
                    if phase == 'download':
                        prior_outputs = [x['inspection'] for x in value['responses'] if x['inspection'].get('phase') == 'outputs'
                                         and x['inspection'].get('request_id') == selected['request_id']]
                        need(len(prior_outputs) == 1 and prior_outputs[0]['declared_bytes'] in (None, len(raw)), 'qlik.download_size_mismatch')
                    pin = F.write_once(root, 'response-%06d.bin' % (len(value['operations']) - 1), raw)
                    value['responses'].append({'attempt': len(value['operations']) - 1, 'file': pin, 'inspection': inspection})
                    record['status'] = 'success'
                    if phase == 'status' and inspection['report_status'] != 'done':
                        value['retry_not_before_epoch'] = max(value['retry_not_before_epoch'], moment + r['poll_interval_seconds'])
                        stop = True
                    latest = advance(root, value)
                except Exception:
                    record['status'] = 'uncertain'; value['gaps'].append('source_response_uncertain_or_unsupported_transfer_redacted')
                    latest = advance(root, value); stop = True
        if any(o['phase'] == 'create' and o['status'] in ('pending', 'uncertain') for o in value['operations']):
            value['status'] = 'blocked'
        elif all(next_operation(r, op, value['operations'], value['responses']) is None for op in r['operations']):
            value['status'] = 'acquired_requested_operations'
        else:
            value['status'] = 'partial'
        return result(advance(root, value))
    finally:
        os.close(fd)


read_capture = load_latest


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
        print('Qlik capture rejected; review scoped evidence and authority.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
