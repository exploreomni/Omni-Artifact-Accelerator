#!/usr/bin/env python3
"""Passive SAP BusinessObjects evidence and externally granted metadata reads.

No login, refresh, render, SDK loading, source save, schedule or session cleanup.
Hashes prove local continuity, not source authenticity or runtime qualification.
"""
from __future__ import annotations
import argparse
import base64
import copy
from decimal import Decimal
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


def module(name):
    if name not in {'powerbi_capture_files', 'bounded_csv', 'businessobjects_visual'}:
        raise ValueError('businessobjects.module_rejected')
    path = Path(__file__).with_name(name + '.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('businessobjects.module_symlink')
    spec = importlib.util.spec_from_file_location('bo_' + name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


F = module('powerbi_capture_files')
encoded = F.encoded
SCHEMA = 'businessobjects-visual-capture.v1'
REQUEST = 'businessobjects-visual-capture-request.v1'
PROFILE = 'webi-qualified-metadata-get.v1'
# Match translator intake; embedded originals/base64 count toward this budget.
MAX_ENVELOPE_BYTES = 8 * 1024 * 1024


def intake_bytes(value):
    # The shared translator escapes non-ASCII text when checking its budget.
    # Keep that conservative bound without changing the evidence hash encoding.
    return len(json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode('utf-8'))


FILTER_STAGES = {'query', 'report', 'block', 'input_controls', 'drill'}
BASE_GAPS = ['source_identity_and_authority_references_not_authenticated',
    'independent_inventory_is_declared_scope_not_tenant_completeness',
    'requested_state_is_not_observed_state', 'effective_access_not_verified',
    'connected_metadata_does_not_replace_imported_snapshot',
    'refresh_render_cleanup_and_source_writes_not_supported',
    'native_rendering_and_business_acceptance_not_assessed']


def need(ok, code):
    F.need(ok, 'businessobjects.' + code)


def sha(value):
    return F.raw_sha(value) if type(value) is bytes else F.sha(value)


def text(value):
    return type(value) is str and 0 < len(value) <= 2000 and all(32 <= ord(c) != 127 for c in value)


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def key(value):
    return type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value) is not None


def screen(raw, secret=None, opaque=False):
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'file_limit')
    if secret:
        for token in {secret, secret.strip('"')}:
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                need(token.encode(encoding) not in raw, 'credential_echo')
    undecoded = False
    try:
        value = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig')
    except UnicodeError:
        need(opaque, 'utf8_required')
        value = raw.decode('latin-1'); undecoded = True
    names = r'(?:password|passwd|pwd|access[_-]?token|client[_-]?secret|api[_-]?key|logonToken|X-SAP-LogonToken|authorization|cookie|serializedSession)'
    need(not re.search(r'(?i)["\']?\b' + names + r'\b["\']?\s*[=:]\s*["\']?[^\s,;"\'}<>]+', value)
         and not re.search(r'(?is)<\s*' + names + r'\b[^>]*>\s*[^<\s]+', value)
         and not re.search(r'(?is)<[^>]+\b(?:name|key)\s*=\s*["\']' + names + r'["\']', value)
         and not re.search(r'(?i)Bearer\s+[A-Za-z0-9._~-]{12,}|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----', value), 'credential_bearing_source')
    if not undecoded and value.lstrip().startswith(('{', '[')):
        try: structured = F.decode(value.encode('utf-8'))
        except (ValueError, UnicodeError): structured = None
        pending = [structured]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                need(not any(re.fullmatch(names, str(k).lstrip('@'), re.I) for k in item), 'credential_bearing_source')
                need(not any(type(item.get(k)) is str and re.fullmatch(names, item[k], re.I)
                             for k in ('name', '@name', 'key', '@key')), 'credential_bearing_source')
                pending.extend(item.values())
            elif type(item) is list: pending.extend(item)
    if undecoded: return 'opaque_bytes_not_assessed'
    if '\x00' in value or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        need(opaque, 'text_control_character')
        return 'opaque_bytes_not_assessed'
    return 'recognized_text_patterns_only'


def validate_state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'timezone', 'locale', 'principal', 'cache', 'reference'}
         and type(value['filters']) is dict and set(value['filters']) == FILTER_STAGES
         and all(type(v) is list and len(v) <= 200 for v in value['filters'].values())
         and type(value['parameters']) is dict and set(value['parameters']) == {'prompts', 'contexts'}
         and type(value['parameters']['contexts']) is list and len(value['parameters']['contexts']) <= 200
         and text(value['reference']), 'state')
    for name in ('timezone', 'locale', 'principal', 'cache'):
        need(value[name] is None or text(value[name]), 'state_context')
    for group in ('prompts', 'contexts'):
        prompts = value['parameters'][group]
        need(type(prompts) is list and len(prompts) <= 200, 'prompts')
        seen = set()
        for prompt in prompts:
            need(type(prompt) is dict and set(prompt) == {'id', 'provider_id', 'answer_mode', 'value'}
                 and text(prompt['id']) and (prompt['provider_id'] is None or text(prompt['provider_id']))
                 and prompt['answer_mode'] in ('explicit', 'default', 'empty', 'all', 'omitted', 'unresolved'), 'prompt')
            identity = (prompt['provider_id'], prompt['id'])
            need(identity not in seen, 'duplicate_prompt'); seen.add(identity)
            if prompt['answer_mode'] in ('omitted', 'unresolved', 'empty'):
                need(prompt['value'] is None, 'prompt_value')
    F.decode(encoded(value)); F.secret_check(value); screen(encoded(value))


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'identity', 'state', 'snapshot_path', 'originals_path',
        'authorization_ref', 'evidence_mode', 'route', 'route_reference', 'target_surface'}
    defaults = {'api_profile': None, 'operations': [], 'max_requests': 30, 'max_response_bytes': F.MAX_FILE,
        'max_total_bytes': F.MAX_TOTAL, 'max_elapsed_seconds': 1800}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value['schema_version'] == REQUEST and key(value['capture_id']), 'request')
    result = {**defaults, **copy.deepcopy(value)}
    need(type(result['identity']) is dict and text(result['identity'].get('principal_ref')), 'request_identity')
    validate_state(result['state'])
    need(result['state']['principal'] in (None, result['identity']['principal_ref']), 'principal_mismatch')
    for name in ('snapshot_path', 'originals_path'): F.source_path(result[name])
    need(result['snapshot_path'] != result['originals_path'] and text(result['authorization_ref']), 'source_paths')
    need(result['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant') and
         result['target_surface'] in ('app', 'dashboard', 'both', 'report') and result['route'] in
         ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor') and
         (result['route'] == 'unselected' or text(result['route_reference'])), 'request_scope')
    for name, high in [('max_requests', 100), ('max_response_bytes', F.MAX_FILE),
                       ('max_total_bytes', F.MAX_TOTAL), ('max_elapsed_seconds', 86400)]:
        need(type(result[name]) is int and 1 <= result[name] <= high, 'budget')
    need(type(result['operations']) is list and len(result['operations']) <= result['max_requests'], 'operations')
    if require_service or result['operations']:
        identity, profile = result['identity'], result['api_profile']
        p = urlsplit(identity.get('source_origin') or '')
        try: port = p.port
        except ValueError: raise F.CaptureError('businessobjects.https_origin') from None
        need(p.scheme == 'https' and p.hostname and p.netloc == p.hostname + (':' + str(port) if port else '')
             and (port is None or 1 <= port <= 65535) and not p.path and not p.query and not p.fragment
             and re.fullmatch('[a-z0-9][a-z0-9.-]*', p.hostname), 'https_origin')
        need(identity.get('report_engine') == 'webi' and identity.get('product_version') in ('4.3', '2025')
             and type(identity.get('service_pack')) is int and identity['service_pack'] >= 0
             and re.fullmatch('[1-9][0-9]*', identity.get('document_id', ''))
             and result['state']['principal'] == identity['principal_ref'], 'connected_version_or_identity')
        need(type(profile) is dict and set(profile) == {'id', 'product_version', 'service_pack', 'rest_path', 'build', 'qualification_reference', 'reference'}
             and profile['id'] == PROFILE and text(profile['reference']) and all(profile[k] == identity[k]
             for k in ('product_version', 'service_pack')) and text(profile['build']) and text(profile['qualification_reference'])
             and type(profile['rest_path']) is str and len(profile['rest_path']) <= 256
             and re.fullmatch(r'(?:/[A-Za-z0-9][A-Za-z0-9_-]*)+', profile['rest_path']), 'metadata_profile')
    ids, specs = set(), set()
    for op in result['operations']:
        spec = _operation_spec(result, op)
        need(op['operation_id'] not in ids and spec['url'] not in specs, 'duplicate_operation')
        ids.add(op['operation_id']); specs.add(spec['url'])
    F.secret_check(result); screen(encoded(result))
    return result


def _operation_spec(config, op):
    fields = {'operation_id', 'kind', 'report_id', 'element_id', 'provider_id', 'reference'}
    need(type(op) is dict and set(op) == fields and key(op['operation_id']) and text(op['reference']), 'operation')
    rid, eid, pid = op['report_id'], op['element_id'], op['provider_id']
    for part in (rid, eid, pid):
        need(part is None or (type(part) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', part)), 'operation_id')
    paths = {'document_details': ('', False, False, False), 'reports': ('/reports', False, False, False),
        'report_details': ('/reports/' + str(rid), True, False, False),
        'elements': ('/reports/' + str(rid) + '/elements', True, False, False),
        'element_details': ('/reports/' + str(rid) + '/elements/' + str(eid), True, True, False),
        'dataproviders': ('/dataproviders', False, False, False),
        'dataprovider_details': ('/dataproviders/' + str(pid), False, False, True),
        'parameters': ('/parameters?lovInfo=false', False, False, False)}
    need(op['kind'] in paths, 'operation_not_metadata')
    suffix, r, e, p = paths[op['kind']]
    need((rid is not None) == r and (eid is not None) == e and (pid is not None) == p, 'operation_extra_selector')
    return {'operation_id': op['operation_id'], 'scope': 'metadata', 'method': 'GET',
        'url': config['identity']['source_origin'] + config['api_profile']['rest_path'] + '/raylight/v1/documents/' + config['identity']['document_id'] + suffix,
        'headers': {'Accept': 'application/json'}, 'body': None}


def operation_spec(config, op):
    config = validate_request(config, require_service=True)
    need(op in config['operations'], 'operation_not_selected')
    return _operation_spec(config, op)


def fingerprint(config, spec, envelope=None):
    return {'request_sha256': sha(validate_request(config)), 'operation_id': spec['operation_id'],
        'scope': spec['scope'], 'method': spec['method'], 'url': spec['url'], 'body_sha256': sha(spec['body']),
        'headers_sha256': sha(spec['headers']), 'identity_sha256': sha(config['identity']),
        'qualification_sha256': sha(config['api_profile']),
        'source_fingerprint': None if envelope is None else envelope['source']['definition_fingerprint']}


def blob(raw):
    return {'content_base64': base64.b64encode(raw).decode('ascii'), 'sha256': sha(raw), 'bytes': len(raw)}


def unblob(record):
    need(type(record.get('content_base64')) is str and len(record['content_base64']) <= (F.MAX_FILE + 2) // 3 * 4, 'embedded_size')
    try: raw = base64.b64decode(record['content_base64'], validate=True)
    except (ValueError, TypeError): raise F.CaptureError('businessobjects.invalid_base64') from None
    need(record.get('sha256') == sha(raw) and record.get('bytes') == len(raw) <= F.MAX_FILE, 'embedded_bytes_changed')
    return raw


def validate_source(source, request):
    need(type(source) is dict and set(source) == {'snapshot', 'definition_fingerprint', 'originals'}, 'source')
    snapshot = source['snapshot']; module('businessobjects_visual').validate_snapshot(snapshot)
    need(snapshot['identity'] == request['identity'] and source['definition_fingerprint'] == sha(snapshot), 'source_identity_changed')
    records = source['originals']; need(type(records) is list and 1 <= len(records) <= 512, 'original_count')
    responses = {r['key']: r for r in snapshot['responses']}
    covered, paths, inventories = set(), set(), 0
    for row in records:
        need(type(row) is dict and set(row) == {'source_path', 'kind', 'response_key', 'reference', 'content_base64', 'sha256', 'bytes', 'screening'}, 'original_record')
        F.source_path(row['source_path']); folded = row['source_path'].casefold()
        need(folded not in paths and text(row['reference']), 'original_collision'); paths.add(folded)
        raw = unblob(row)
        need(row['screening'] == screen(raw, opaque=row['kind'] == 'opaque'), 'screening_changed')
        if row['kind'] == 'response':
            rkey = row['response_key']; need(rkey in responses and rkey not in covered, 'original_response')
            need(raw == responses[rkey]['content'].encode('utf-8'), 'response_original_mismatch'); covered.add(rkey)
        elif row['kind'] == 'inventory':
            need(row['response_key'] is None and F.decode(raw) == snapshot['inventory'], 'inventory_original_mismatch'); inventories += 1
        else:
            need(row['kind'] == 'opaque' and row['response_key'] is None, 'original_kind')
    need(covered == set(responses) and inventories == 1, 'complete_original_crosswalk_required')
    if request['operations']:
        visual = module('businessobjects_visual')
        scoped = [visual.scope_item(snapshot, r['key']) for r in snapshot['inventory']['items']]
        roots = [s for s in scoped if s['item']['parent_key'] is None]
        need(len(roots) == 1 and roots[0]['item']['disposition'] == 'include' and not roots[0]['restricted'], 'metadata_document_scope')
        for op in request['operations']:
            candidates = [s for s in scoped if s['item']['disposition'] == 'include' and not s['restricted'] and s['node'] is not None]
            if op['report_id'] is not None:
                candidates = [s for s in candidates if s['report_id'] == op['report_id']]
                need(candidates, 'metadata_report_scope')
            if op['element_id'] is not None:
                need(any(s['item']['native_id'] == op['element_id'] and s['native_kind'] in ('visual', 'layout', 'content') for s in candidates), 'metadata_element_scope')
            if op['provider_id'] is not None:
                need(any(op['provider_id'] in s['provider_ids'] for s in candidates), 'metadata_provider_scope')


def normalized_binding(binding, raw):
    keys = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id', 'state_sha256', 'attachment_sha256'}
    need(type(binding) is dict and set(binding) == keys and all(digest(binding[k]) for k in
         keys - {'object_key', 'attachment_id'}) and text(binding['object_key']) and key(binding['attachment_id'])
         and binding['attachment_sha256'] == sha(raw), 'normalization_binding')


def normalize_results(raw, profile, binding):
    """Explicit raw scalar CSV/object rows; no SAP formula or formatted-number coercion."""
    normalized_binding(binding, raw); screen(raw)
    common = {'schema_version', 'format', 'headers', 'columns', 'subtotal_policy', 'value_representation', 'reference'}
    need(type(profile) is dict and profile.get('schema_version') == 1 and profile.get('format') in ('csv', 'json')
         and profile.get('value_representation') == 'raw' and profile.get('subtotal_policy') == 'preserve'
         and text(profile.get('reference')), 'normalization_profile')
    need(set(profile) == common | ({'encoding'} if profile['format'] == 'csv' else {'rows_pointer'}), 'profile_fields')
    headers, cols = profile['headers'], profile['columns']
    need(type(headers) is list and 1 <= len(headers) <= 512 and all(text(h) for h in headers)
         and len(headers) == len(set(headers)) and type(cols) is list and len(cols) == len(headers), 'result_columns')
    names = set()
    for i, col in enumerate(cols):
        need(type(col) is dict and set(col) == {'ordinal', 'name', 'type', 'nullable', 'null_tokens', 'error_tokens'}
             and type(col['ordinal']) is int and col['ordinal'] == i and text(col['name']) and col['name'] not in names
             and col['type'] in ('number', 'string', 'boolean') and type(col['nullable']) is bool
             and type(col['null_tokens']) is list and all(type(t) is str for t in col['null_tokens'])
             and type(col['error_tokens']) is list and all(text(t) for t in col['error_tokens'])
             and not set(col['null_tokens']) & set(col['error_tokens']), 'column_profile')
        names.add(col['name'])
    if profile['format'] == 'csv':
        need(profile['encoding'] == 'utf-8', 'csv_encoding')
        rows = module('bounded_csv').rows(raw, headers, 'businessobjects')
    else:
        tree = F.decode(raw); F.secret_check(tree)
        stack = [tree]
        while stack:
            node = stack.pop()
            if type(node) is dict:
                need(not any(k.lower() in ('error', 'errors', 'error_code') for k in node), 'source_result_error')
                stack.extend(node.values())
            elif type(node) is list: stack.extend(node)
        tree = json.loads(raw.decode('utf-8-sig'), parse_float=Decimal)
        pointer = profile['rows_pointer']; need(type(pointer) is str and (pointer == '' or pointer.startswith('/')), 'rows_pointer')
        for part in pointer.split('/')[1:]:
            need(re.search('~(?![01])', part) is None, 'pointer_escape')
            part = part.replace('~1', '/').replace('~0', '~')
            if type(tree) is dict:
                need(part in tree, 'rows_pointer_missing'); tree = tree[part]
            else:
                need(type(tree) is list and re.fullmatch('0|[1-9][0-9]*', part) and int(part) < len(tree), 'rows_pointer_missing')
                tree = tree[int(part)]
        need(type(tree) is list and len(tree) <= 100000 and all(type(r) is dict and set(r) == set(headers) for r in tree), 'object_rows')
        rows = ([r[h] for h in headers] for r in tree)
    output, cells = [], 0
    for row in rows:
        cells += len(row); need(cells <= 1000000, 'cell_limit'); current = {}
        F.secret_check(dict(zip(headers, row)))
        for col, value in zip(cols, row):
            need(not (type(value) is str and (value in col['error_tokens'] or re.match(r'^#(?:ERROR|MULTIVALUE|DIV/0|UNAVAILABLE|DATASYNC|TOREFRESH|PARTIALRESULT|OVERFLOW|CONTEXT|INCOMPATIBLE|SYNTAX|N/A|COMPUTATION|EXTERNAL|NODATA|RECURSIVE)', value, re.I))), 'source_cell_error')
            if value is None or type(value) is str and value in col['null_tokens']:
                need(col['nullable'], 'unexpected_null'); result = None
            elif col['type'] == 'number':
                need(type(value) in (str, int, Decimal) and len(str(value)) <= 1000 and re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', str(value)), 'raw_number_required')
                number = Decimal(str(value)); need(number.is_finite(), 'nonfinite_number'); result = str(number)
            elif col['type'] == 'boolean':
                need(type(value) is bool, 'raw_boolean_required'); result = value
            else:
                need(type(value) is str, 'raw_string_required'); result = value
            current[col['name']] = result
        output.append(current)
    result = {'schema_version': 1, 'kind': 'businessobjects_normalized_results', 'raw_sha256': sha(raw),
        'parser_profile': copy.deepcopy(profile), 'binding': copy.deepcopy(binding), 'headers': copy.deepcopy(headers),
        'row_count': len(output), 'rows': output, 'row_order': 'preserved', 'completeness': 'not_established'}
    need(intake_bytes(result) <= MAX_ENVELOPE_BYTES, 'normalized_output_byte_limit')
    return result


def result_context(value):
    need(type(value) is dict and set(value) == {'data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage', 'reference'}
         and value['data_mode'] in ('full_data', 'preview', 'test', 'unknown')
         and (value['row_limit'] is None or type(value['row_limit']) is int and 0 < value['row_limit'] <= 100000)
         and value['row_limit_stage'] in ('before_aggregation', 'after_aggregation', 'none', 'unknown')
         and value['aggregation_stage'] in ('raw_query', 'native_report', 'in_document', 'unknown')
         and text(value['reference']), 'result_context')
    need(value['row_limit_stage'] != 'none' or value['row_limit'] is None, 'result_limit_contradiction')
    need(value['row_limit_stage'] not in ('before_aggregation', 'after_aggregation') or value['row_limit'] is not None, 'result_limit_missing')


def validate_attachment(row, envelope):
    fields = {'attachment_id', 'object_key', 'format', 'reference', 'origin', 'result_scope', 'observed_state',
        'population', 'freshness', 'completeness', 'parser_profile', 'content_base64', 'sha256', 'bytes'}
    need(type(row) is dict and set(row) == fields and key(row['attachment_id']) and text(row['reference'])
         and row['format'] in ('csv', 'json', 'png', 'pdf', 'opaque'), 'attachment')
    snapshot = envelope['source']['snapshot']
    scope = module('businessobjects_visual').scope_item(snapshot, row['object_key'])
    need(scope['item']['disposition'] == 'include' and not scope['restricted'], 'attachment_scope')
    raw = unblob(row); screen(raw, opaque=row['format'] in ('png', 'pdf', 'opaque'))
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown') and row['result_scope'] in
         ('query_result', 'transformed', 'displayed', 'unknown') and (row['origin'] not in ('displayed', 'transformed')
         or row['origin'] == row['result_scope']), 'result_scope')
    for name, keys in [('population', {'key', 'description', 'reference'}), ('freshness', {'data_watermark', 'observed_at', 'reference'})]:
        need(type(row[name]) is dict and set(row[name]) == keys and all(v is None or text(v) for v in row[name].values()), name)
    observed = row['observed_state']
    if observed is not None:
        keys = {'state', 'observed_at', 'reference', 'execution_status', 'execution_reference', 'provider_states', 'definition_fingerprint'}
        need(type(observed) is dict and keys <= set(observed) <= keys | {'placement_reference', 'result_context'} and
             text(observed['observed_at']) and text(observed['reference']) and text(observed['execution_reference'])
             and observed['execution_status'] in ('completed', 'pending', 'partial', 'failed', 'unknown')
             and observed['definition_fingerprint'] == sha(snapshot), 'observed_state')
        validate_state(observed['state'])
        if 'placement_reference' in observed: need(text(observed['placement_reference']), 'placement_reference')
        if 'result_context' in observed: result_context(observed['result_context'])
        need(observed['state']['principal'] in (None, snapshot['identity']['principal_ref']), 'observed_principal')
        providers = observed['provider_states']; need(type(providers) is list and len(providers) <= 200, 'provider_states')
        seen = set()
        for p in providers:
            need(type(p) is dict and set(p) == {'provider_id', 'status', 'reference'} and text(p['provider_id'])
                 and p['provider_id'] not in seen and p['status'] in ('completed', 'partial', 'failed', 'unknown')
                 and text(p['reference']), 'provider_state'); seen.add(p['provider_id'])
    complete = row['completeness']
    need(type(complete) is dict and set(complete) == {'status', 'row_count', 'reference'} and
         complete['status'] in ('complete', 'partial', 'unknown') and (complete['reference'] is None or text(complete['reference']))
         and (complete['row_count'] is None or type(complete['row_count']) is int and 0 <= complete['row_count'] <= 100000), 'completeness')
    if row['format'] in ('csv', 'json'):
        need(scope['query_visual'] and type(row['parser_profile']) is dict and row['parser_profile']['format'] == row['format'], 'numeric_profile_required')
        binding = {k: sha(raw) for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256')}
        binding.update(object_key=row['object_key'], attachment_id=row['attachment_id'])
        normalized = normalize_results(raw, row['parser_profile'], binding)
        need(complete['row_count'] is None or complete['row_count'] == normalized['row_count'], 'row_count_mismatch')
    else:
        need(row['parser_profile'] is None and complete['status'] != 'complete', 'non_numeric_completeness')
        if row['format'] == 'png': F.png_info(raw)
        if row['format'] == 'pdf': need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'pdf_signature')
    if complete['status'] == 'complete':
        needed = set(scope.get('provider_ids') or [])
        need(needed and observed is not None and observed['execution_status'] == 'completed'
             and {p['provider_id'] for p in observed['provider_states']} == needed
             and all(p['status'] == 'completed' for p in observed['provider_states'])
             and observed['state'] == envelope['request']['state'] and text(observed['state']['principal'])
             and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and all(row['population'].values()) and all(row['freshness'].values())
             and text(complete['reference']) and type(complete['row_count']) is int, 'complete_evidence_required')


def validate_envelope(value):
    need(intake_bytes(value) <= MAX_ENVELOPE_BYTES, 'capture_byte_limit')
    keys = {'schema_version', 'request', 'request_sha256', 'source', 'attachments', 'events', 'created_at',
        'journal_revision', 'previous_capture', 'status', 'gaps', 'content_hash'}
    need(type(value) is dict and set(value) == keys and value['schema_version'] == SCHEMA, 'capture_contract')
    need(value['content_hash'] == sha({k: v for k, v in value.items() if k != 'content_hash'}), 'capture_seal')
    config = validate_request(value['request']); need(value['request'] == config and value['request_sha256'] == sha(config), 'request_changed')
    validate_source(value['source'], config)
    need(type(value['journal_revision']) is int and 1 <= value['journal_revision'] <= 256
         and type(value['created_at']) in (int, float) and value['created_at'] > 0
         and type(value['gaps']) is list and all(text(v) for v in value['gaps']) and set(BASE_GAPS) <= set(value['gaps']), 'capture_metadata')
    need(type(value['attachments']) is list and len(value['attachments']) <= 100, 'attachment_limit')
    ids = set()
    for row in value['attachments']:
        need(row.get('attachment_id') not in ids, 'duplicate_attachment'); ids.add(row['attachment_id'])
        validate_attachment(row, value)
    events = value['events']; need(type(events) is list and len(events) <= config['max_requests'] * 2, 'event_limit')
    pending, finished, last_time = None, set(), value['created_at']
    for event in events:
        need(type(event) is dict and set(event) == {'operation_id', 'phase', 'fingerprint', 'at', 'response', 'error'}
             and event['phase'] in ('pending', 'completed', 'failed', 'uncertain')
             and type(event['at']) in (int, float) and event['at'] >= last_time, 'event')
        last_time = event['at']
        ops = [o for o in config['operations'] if o['operation_id'] == event['operation_id']]
        need(len(ops) == 1 and event['fingerprint'] == fingerprint(config, operation_spec(config, ops[0]), value), 'event_operation')
        if event['phase'] == 'pending':
            need(pending is None and event['operation_id'] not in finished and event['response'] is None and event['error'] is None, 'dispatch_replay')
            pending = event['operation_id']
        else:
            need(pending == event['operation_id'], 'terminal_without_pending'); pending = None; finished.add(event['operation_id'])
            if event['phase'] == 'completed':
                need(event['error'] is None and type(event['response']) is dict, 'response')
                response = event['response']; need(set(response) == {'status', 'content_base64', 'sha256', 'bytes'} and response['status'] == 200, 'response_contract')
                raw = unblob(response); screen(raw); F.secret_check(F.decode(raw))
            else:
                need(event['response'] is None and event['error'] == 'metadata_acquisition_stopped', 'redacted_error')
    expected = 'blocked' if pending or any(e['phase'] in ('failed', 'uncertain') for e in events) else 'ready'
    need(value['status'] == expected, 'status_changed')
    retained = sum(x['bytes'] for x in value['source']['originals'] + value['attachments']) + sum(e['response']['bytes'] for e in events if e['response'])
    need(retained <= config['max_total_bytes'], 'total_bytes')
    F.secret_check(value)
    return value


validate_capture = validate_envelope


def verify_capture_files(value, root=None):
    # All raw evidence is embedded and revalidated; no external attachment reads.
    return validate_envelope(value)


def _lock(directory):
    root = F.private_directory(directory)
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), 'lock_type'); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd); raise
    return root, fd


def save(root, value, previous=None):
    value = copy.deepcopy(value)
    value['previous_capture'] = previous
    value['content_hash'] = sha({k: v for k, v in value.items() if k != 'content_hash'})
    validate_envelope(value)
    pin = F.write_once(root, 'capture-%06d.json' % value['journal_revision'], encoded(value))
    return value, root / pin['path']


def load_latest(directory, config=None):
    root = F.private_directory(directory); paths = sorted(root.glob('capture-*.json'))
    need(1 <= len(paths) <= 256 and sum(F.no_links(p).stat().st_size for p in paths) <= 128000000, 'journal_limit_or_missing')
    previous, old = None, None
    for i, path in enumerate(paths, 1):
        raw = F.read_file(path, F.MAX_JSON); value = F.decode(raw); validate_envelope(value)
        need(path.name == 'capture-%06d.json' % i and value['journal_revision'] == i and value['previous_capture'] == previous, 'journal_chain')
        if old:
            need(all(old[k] == value[k] for k in ('request', 'request_sha256', 'source', 'created_at', 'gaps'))
                 and value['attachments'][:len(old['attachments'])] == old['attachments']
                 and value['events'][:len(old['events'])] == old['events']
                 and len(value['attachments']) + len(value['events']) > len(old['attachments']) + len(old['events']), 'journal_transition')
        previous = {'path': path.name, 'sha256': sha(raw)}; old = value
    need(config is None or value['request'] == validate_request(config), 'resume_request_changed')
    return value, paths[-1]


def advance(root, value, previous_path):
    previous = {'path': previous_path.name, 'sha256': sha(F.read_file(previous_path, F.MAX_JSON))}
    value['journal_revision'] += 1
    return save(root, value, previous)


def summary(value, path):
    return {'path': str(path), 'status': value['status'], 'content_hash': value['content_hash'],
        'attachments': len(value['attachments']), 'metadata_requests': sum(e['phase'] == 'pending' for e in value['events']),
        'source_execution': 'not_requested_runtime_effects_unverified', 'source_writes': False}


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read is True, 'source_read_authorization_required')
    config = validate_request(request); source_root = F.no_links(source_root)
    snapshot = F.decode(F.read_file(source_root / config['snapshot_path']))
    manifest = F.decode(F.read_file(source_root / config['originals_path']))
    need(type(manifest) is dict and set(manifest) == {'schema_version', 'reference', 'records'}
         and manifest['schema_version'] == 'businessobjects-originals.v1' and text(manifest['reference'])
         and type(manifest['records']) is list and 1 <= len(manifest['records']) <= 512, 'original_manifest')
    originals = []
    for row in manifest['records']:
        need(type(row) is dict and set(row) == {'source_path', 'kind', 'response_key', 'reference'}, 'original_manifest_record')
        raw = F.read_file(source_root / F.source_path(row['source_path']))
        originals.append({**copy.deepcopy(row), **blob(raw), 'screening': screen(raw, opaque=row['kind'] == 'opaque')})
    value = {'schema_version': SCHEMA, 'request': config, 'request_sha256': sha(config),
        'source': {'snapshot': snapshot, 'definition_fingerprint': sha(snapshot), 'originals': originals},
        'attachments': [], 'events': [], 'created_at': time.time(), 'journal_revision': 1,
        'previous_capture': None, 'status': 'ready', 'gaps': list(BASE_GAPS), 'content_hash': ''}
    root, fd = _lock(directory)
    try:
        need(not list(root.glob('capture-*.json')), 'capture_exists')
        return summary(*save(root, value))
    finally: os.close(fd)


def check_capture(path):
    path = F.no_links(path)
    if path.is_dir(): return summary(*load_latest(path))
    value, latest = load_latest(path.parent)
    need(latest == path, 'latest_capture_required')
    return summary(value, path)


def import_evidence(capture_path, spec, source_root):
    path, source_root = F.no_links(capture_path), F.no_links(source_root)
    root, fd = _lock(path.parent)
    try:
        value, latest = load_latest(root); need(path == latest, 'latest_capture_required')
        need(type(spec) is dict and set(spec) == {'schema_version', 'attachments'} and
             spec['schema_version'] == 'businessobjects-supplied-evidence.v1' and type(spec['attachments']) is list
             and 1 <= len(spec['attachments']) <= 100, 'supplied_evidence')
        for row in spec['attachments']:
            need(type(row) is dict and 'source_path' in row, 'attachment_source')
            raw = F.read_file(source_root / F.source_path(row['source_path']))
            attachment = {k: copy.deepcopy(v) for k, v in row.items() if k != 'source_path'}
            need(not {'content_base64', 'sha256', 'bytes'} & set(attachment), 'attachment_derived_fields')
            value['attachments'].append({**attachment, **blob(raw)})
        return summary(*advance(root, value, latest))
    finally: os.close(fd)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise F.CaptureError('businessobjects.redirect_rejected')


def transport(method, url, headers, body, maximum, timeout):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    request = Request(url, headers=headers, method=method, data=body)
    try:
        with opener.open(request, timeout=timeout) as response:
            need(response.geturl() == url, 'response_url_changed')
            raw = response.read(maximum + 1); need(len(raw) <= maximum, 'response_size')
            return response.status, dict(response.headers), raw
    except HTTPError:
        raise F.CaptureError('businessobjects.metadata_acquisition_stopped') from None


def pending_operation_spec(config, envelope):
    need(envelope['events'] and envelope['events'][-1]['phase'] == 'pending', 'pending_operation_required')
    opid = envelope['events'][-1]['operation_id']
    return operation_spec(config, next(o for o in config['operations'] if o['operation_id'] == opid))


def capture(request, directory, *, authority=None, transport=None, resume=True):
    config = validate_request(request, require_service=True)
    need(resume is True and callable(authority), 'external_runtime_authority_required')
    root, fd = _lock(directory)
    try:
        value, latest = load_latest(root, config)
        need(value['status'] != 'blocked' and time.time() - value['created_at'] <= config['max_elapsed_seconds'], 'capture_blocked_or_expired')
        for op in config['operations']:
            if any(e['operation_id'] == op['operation_id'] for e in value['events']): continue
            need(time.time() - value['created_at'] <= config['max_elapsed_seconds'], 'capture_expired')
            selected = operation_spec(config, op)
            event = {'operation_id': op['operation_id'], 'phase': 'pending', 'fingerprint': fingerprint(config, selected, value),
                     'at': time.time(), 'response': None, 'error': None}
            value['events'].append(event); value['status'] = 'blocked'; value, latest = advance(root, value, latest)
            terminal = {**event, 'at': time.time(), 'phase': 'uncertain', 'error': 'metadata_acquisition_stopped'}
            try:
                granted = authority('metadata', event['fingerprint'])
                need(type(granted) is dict and set(granted) == {'X-SAP-LogonToken'} and text(granted['X-SAP-LogonToken']), 'host_logon_token_required')
                token = granted['X-SAP-LogonToken']; headers = {**selected['headers'], **granted}
                retained = sum(x['bytes'] for x in value['source']['originals'] + value['attachments']) + sum(e['response']['bytes'] for e in value['events'] if e['response'])
                maximum = min(config['max_response_bytes'], config['max_total_bytes'] - retained)
                need(maximum > 0, 'network_byte_budget')
                status, response_headers, raw = (transport or globals()['transport'])('GET', selected['url'], headers, None,
                    maximum, 30)
                need(type(response_headers) is dict and not any(k.lower() in ('location', 'set-cookie', 'x-sap-logontoken') for k in response_headers), 'session_or_redirect_response')
                need(status == 200 and type(raw) is bytes and len(raw) <= maximum, 'metadata_status_or_size'); screen(raw, token)
                payload = F.decode(raw); F.secret_check(payload)
                need(type(payload) is dict and not {'error', 'errors'} & set(payload), 'metadata_error')
                terminal.update(phase='completed', response={'status': status, **blob(raw)}, error=None)
            except Exception:
                # Do not persist source errors, secrets or unqualified bodies.
                pass
            terminal['at'] = max(time.time(), event['at']); value['events'].append(terminal)
            value['status'] = 'ready' if terminal['phase'] == 'completed' else 'blocked'
            value, latest = advance(root, value, latest)
            if value['status'] == 'blocked': break
        return summary(value, latest)
    finally: os.close(fd)


run_capture = capture


def translate(payload, raw, helpers):
    validate_envelope(payload)
    result = module('businessobjects_visual').parse_snapshot(payload['source']['snapshot'], encoded(payload['source']['snapshot']), helpers)
    result['source'].update(helpers['base'](payload, raw, 'businessobjects', 'supplied_businessobjects_visual_capture')['source'])
    result['source'].update(definition_fingerprint=payload['source']['definition_fingerprint'], capture_content_hash=payload['content_hash'])
    result['upstream_payload'] = copy.deepcopy(payload)
    result['migration_context'].update(route=None if payload['request']['route'] == 'unselected' else payload['request']['route'],
        route_reference=payload['request']['route_reference'], target_surface=payload['request']['target_surface'])
    for gap in payload['gaps']: helpers['gap'](result, 'businessobjects.capture_gap', detail=gap)
    return result


parse_capture = translate


def case_binding(asset, case, capture):
    validate_envelope(capture)
    snapshot, identity = capture['source']['snapshot'], asset.get('source_identity', {})
    object_key = identity.get('object_key', identity.get('inventory_key'))
    need(identity.get('definition_fingerprint') == sha(snapshot), 'case_definition')
    scope = module('businessobjects_visual').scope_item(snapshot, object_key)
    need(scope['item']['disposition'] == 'include' and not scope['restricted'], 'case_scope')
    binding = case.get('source_binding')
    need(type(binding) is dict and set(binding) == {'definition_fingerprint', 'state_sha256', 'object_key', 'attachment_id'}
         and binding['definition_fingerprint'] == sha(snapshot) and binding['state_sha256'] == sha(capture['request']['state'])
         and binding['object_key'] == object_key, 'case_binding')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id'] and a['object_key'] == object_key]
    need(binding['attachment_id'] is None or len(matches) == 1, 'case_attachment')
    if case.get('lane') == 'numeric': need(scope['query_visual'] and len(matches) == 1 and matches[0]['format'] in ('csv', 'json'), 'numeric_evidence')
    return binding


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture); gaps = []
    if not case.get('source_capture'): gaps.append('source.businessobjects_capture_required')
    if capture['status'] == 'blocked': gaps.append('source.businessobjects_capture_blocked')
    pin = source.get('raw_file') if source.get('format') == 'businessobjects-normalized' else source.get('file')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id'] and a['sha256'] == (pin or {}).get('sha256')]
    if len(matches) != 1: return gaps + ['source.businessobjects_result_not_bound']
    attachment = matches[0]; observed = attachment['observed_state']; state = capture['request']['state']
    if attachment['completeness']['status'] != 'complete': gaps.append('source.businessobjects_completeness_unverified')
    if observed is None: gaps.append('source.businessobjects_observed_state_missing')
    for k in ('filters', 'parameters', 'timezone', 'locale', 'principal', 'cache'):
        if state[k] is None or (observed or {}).get('state', {}).get(k) != state[k] or source.get('context', {}).get(k) != state[k]:
            gaps.append('source.businessobjects_observed.' + k)
        if k not in ('principal', 'cache') and target.get('context', {}).get(k) != state[k]: gaps.append('context.' + k)
    if any(p['answer_mode'] in ('omitted', 'unresolved') for group in ('prompts', 'contexts') for p in state['parameters'][group]):
        gaps.append('source.businessobjects_prompt_answers_unresolved')
    if (observed or {}).get('execution_status') != 'completed': gaps.append('source.businessobjects_execution_unverified')
    if asset.get('kind') == 'placement' and not (observed or {}).get('placement_reference'): gaps.append('source.businessobjects_placement_unverified')
    scope = module('businessobjects_visual').scope_item(capture['source']['snapshot'], binding['object_key'])
    visual = module('businessobjects_visual')
    for response in capture['source']['snapshot']['responses']:
        if response['kind'] not in ('dataproviders', 'dataprovider'): continue
        parsed = visual.decode_response(response)
        for record in parsed['records'].values():
            if record['label'] != 'dataprovider': continue
            def field(name):
                if 'payload' in record: return record['payload'].get(name, record['payload'].get('@' + name))
                if name in record['attributes']: return record['attributes'][name]
                found = [parsed['records'][p]['text'] for p in record['children'] if parsed['records'][p]['label'] == name]
                return found[0] if len(found) == 1 else None
            if str(field('id')) in scope['provider_ids'] and field('isPartial') in (True, 'true', '1', 1):
                gaps.append('source.businessobjects_native_partial_provider')
    contract = scope['item']['configuration'].get('result_contract')
    actual = (observed or {}).get('result_context')
    if contract is None: gaps.append('source.businessobjects_result_contract_missing')
    else: result_context(contract)
    if actual is None: gaps.append('source.businessobjects_result_context_missing')
    else:
        result_context(actual)
        for k in ('data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage'):
            if contract is None or contract[k] != actual[k] or source.get('context', {}).get(k, '__absent__') != actual[k]:
                gaps.append('source.businessobjects_result_context.' + k)
            if target.get('context', {}).get(k, '__absent__') != actual[k]: gaps.append('context.' + k)
        if actual['data_mode'] in ('test', 'unknown') or actual['row_limit_stage'] == 'unknown' or actual['aggregation_stage'] == 'unknown':
            gaps.append('source.businessobjects_result_semantics_unqualified')
        if actual['aggregation_stage'] == 'in_document' and attachment['result_scope'] != 'transformed':
            gaps.append('source.businessobjects_transformed_scope_required')
    for k, expected in {'population': attachment['population']['key'], 'data_watermark': attachment['freshness']['data_watermark'],
                        'result_scope': attachment['result_scope']}.items():
        if expected is None or source.get('context', {}).get(k) != expected: gaps.append('source.businessobjects.' + k)
        if target.get('context', {}).get(k) != expected: gaps.append('context.' + k)
    if source.get('format') != 'businessobjects-normalized':
        gaps.append('source.businessobjects_typed_normalization_required')
    else:
        expected = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': sha(capture['source']['snapshot']),
            'state_sha256': binding['state_sha256'], 'object_key': binding['object_key'], 'attachment_id': binding['attachment_id'],
            'attachment_sha256': attachment['sha256']}
        if normalized != normalize_results(unblob(attachment), attachment['parser_profile'], expected):
            gaps.append('source.businessobjects_normalization_changed')
        declared = [c['name'] for c in attachment['parser_profile']['columns']]
        compared = [c.get('source') for c in (columns or [])]
        if len(compared) != len(set(compared)) or set(compared) != set(declared):
            gaps.append('source.businessobjects_compared_columns_incomplete')
    return gaps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('import-local'); p.add_argument('request'); p.add_argument('--source-root', required=True); p.add_argument('--directory', required=True); p.add_argument('--allow-source-read', action='store_true')
    p = sub.add_parser('import-evidence'); p.add_argument('capture'); p.add_argument('--spec', required=True); p.add_argument('--source-root', required=True)
    p = sub.add_parser('check'); p.add_argument('capture')
    p = sub.add_parser('normalize'); p.add_argument('source'); p.add_argument('--profile', required=True); p.add_argument('--binding', required=True); p.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'import-local': result = import_local(F.decode(F.read_file(args.request)), args.source_root, args.directory, allow_source_read=args.allow_source_read)
        elif args.command == 'import-evidence': result = import_evidence(args.capture, F.decode(F.read_file(args.spec)), args.source_root)
        elif args.command == 'normalize':
            result = normalize_results(F.read_file(args.source), F.decode(F.read_file(args.profile)), F.decode(F.read_file(args.binding)))
            output = F.no_links(args.output); F.write_once(F.private_directory(output.parent), output.name, encoded(result))
            result = {'path': str(output), 'row_count': result['row_count'], 'completeness': 'not_established'}
        else: result = check_capture(args.capture)
        print(encoded(result).decode())
    except Exception:
        parser.exit(2, 'BusinessObjects evidence operation rejected; review the bounded source contract.\n')


if __name__ == '__main__': main()
