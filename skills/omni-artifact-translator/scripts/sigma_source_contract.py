"""Pure consumer contracts for the versioned Sigma source-operation interface."""
import hashlib
import json
import re
from urllib.parse import urlsplit


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def need(ok, code):
    if not ok:
        raise ValueError('sigma.source.' + code)


def request(value):
    need(type(value) is dict and value.get("schema_version") == "sigma-source-operation-request.v1", "request_contract")
    required = {'schema_version', 'request_id', 'operation', 'api_base_url', 'approved_api_host',
                'expected_organization_id', 'expected_user_id', 'principal_ref', 'authorization_ref',
                'evidence_mode', 'max_requests', 'scope', 'options'}
    need(set(value) in (required, required | {'visual_capture_request'}) and len(canonical(value)) <= 256*1024,
         'request_fields_or_size')
    need(value.get("operation") in ("check", "inventory", "snapshot", "capture"), "operation_rejected")
    need(type(value['request_id']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value['request_id']), 'request_id')
    for key in ("request_id", "expected_organization_id", "expected_user_id", "principal_ref", "authorization_ref"):
        need(type(value.get(key)) is str and 0 < len(value[key]) <= 512
             and not any(ord(c) < 32 or ord(c) == 127 for c in value[key]), "identity_required")
    origin = value.get("api_base_url", "")
    try:
        parsed = urlsplit(origin)
        valid = (parsed.scheme == 'https' and parsed.hostname == value.get('approved_api_host')
                 and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', parsed.hostname or '')
                 and parsed.port in (None, 443) and not parsed.username and not parsed.password
                 and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                 and not any(c in origin for c in '\\\r\n'))
    except (ValueError, TypeError):
        valid = False
    need(valid, 'exact_origin_required')
    need(type(value.get("max_requests")) is int and 5 <= value["max_requests"] <= 500, "request_budget")
    need(type(value.get("scope")) is dict and set(value['scope']) == {'workbook_ids', 'data_model_ids'}, "scope_required")
    for key in ("workbook_ids", "data_model_ids"):
        ids = value["scope"].get(key)
        need(type(ids) is list and len(ids) <= 10
             and all(type(x) is str and re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._~-]{0,511}", x) for x in ids)
             and len(set(ids)) == len(ids), "scope_ids")
    need(value.get('evidence_mode') in ('synthetic_fixture', 'live_tenant')
         and re.fullmatch(r'principal-ref://[^\s?#]+', value['principal_ref'])
         and re.fullmatch(r'human-authorization-ref://[^\s?#]+', value['authorization_ref']), 'source_evidence_references')
    need(type(value.get('options')) is dict and set(value['options']) == {'include_contents_beta'}
         and type(value['options']['include_contents_beta']) is bool, 'source_options')
    operation = value['operation']
    if operation in ('snapshot', 'capture'):
        need(bool(value['scope']['workbook_ids']), 'selected_workbook_required')
    if operation == 'capture':
        child = value.get('visual_capture_request')
        need(type(child) is dict and child.get('schema_version') in
             ('sigma-visual-capture-request.v1', 'sigma-visual-capture-request.v2'), 'visual_request_required')
        need(len(value['scope']['workbook_ids']) == 1 and len(value['scope']['data_model_ids']) <= 1
             and not value['options']['include_contents_beta'], 'capture_scope')
        for key in ('api_base_url', 'approved_api_host', 'expected_organization_id', 'expected_user_id',
                    'principal_ref', 'authorization_ref', 'evidence_mode'):
            need(child.get(key) == value[key], 'nested_source_identity')
        need(child.get('workbook_id') == value['scope']['workbook_ids'][0]
             and ([child['data_model_id']] if child.get('data_model_id') else []) == value['scope']['data_model_ids']
             and child.get('max_requests_per_invocation', 100) == value['max_requests'], 'nested_source_scope_or_budget')
    else:
        need('visual_capture_request' not in value, 'unexpected_visual_request')
    need(not value['options']['include_contents_beta'] or operation == 'snapshot', 'beta_snapshot_only')
    # Source requests contain identifiers and references, never credentials.
    def scan(item):
        if isinstance(item, dict):
            for key, val in item.items():
                need(not re.search(r"(secret|password|access.?token|api.?key|authorization.?header)", key, re.I), "credential_field")
                scan(val)
        elif isinstance(item, list):
            for val in item:
                scan(val)
        elif isinstance(item, str):
            need(not re.search(r'(?i)\bBearer\s+\S+|(?:authorization|bearer|password|passwd|secret|api[_-]?key|api[_-]?token|access[_-]?token|refresh[_-]?token|credentials?)\s*[:=]\s*[^\s,}]+', item),
                 'credential_text')
    scan(value)
    return value


def envelope(value):
    need(type(value) is dict and value.get('schema_version') == 'sigma-source-operation.v1', 'envelope_contract')
    req = request(value.get('request'))
    result = value.get('result')
    need(type(result) is dict and value.get('operation') == req['operation'] and
         value.get('request_sha256') == digest(req) and value.get('result_sha256') == digest(result) and
         value.get('content_hash') == digest({k: v for k, v in value.items() if k != 'content_hash'}), 'source_operation_hash')
    need(value.get('evidence_mode') == req['evidence_mode'] and value.get('target_write_authority') is False and
         value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed', 'envelope_authority_or_mode')
    revision = value.get('journal_revision')
    need(type(revision) is int and 1 <= revision <= 65 and
         (value.get('previous_content_hash') is None if revision == 1 else
          type(value.get('previous_content_hash')) is str and re.fullmatch(r'[a-f0-9]{64}', value['previous_content_hash'])),
         'envelope_journal_shape')
    need(type(value.get('observed_at')) is str and value['observed_at'] and type(value.get('gaps')) is list and
         all(type(g) is str for g in value['gaps']), 'envelope_observation')
    if req['operation'] == 'capture':
        need(value.get('status') in ('pending', 'complete', 'partial', 'blocked') and set(result) == {'visual_capture'}, 'capture_envelope')
        child = result['visual_capture']
        need((child is None and value['status'] == 'pending') or type(child) is dict and
             set(child) == {'path', 'sha256', 'bytes', 'schema_version', 'status'} and
             child['schema_version'] == 'sigma-visual-capture.v1' and child['status'] == value['status'] and
             type(child['path']) is str and re.fullmatch(r'visual/capture-[0-9]{6}\.json', child['path']) and
             type(child['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', child['sha256']) and
             type(child['bytes']) is int and 0 < child['bytes'] <= 25*1024*1024, 'capture_receipt')
        return value
    need(value.get('status') == 'captured_requires_review', 'metadata_status')
    principal = value.get('observed_principal')
    need(type(principal) is dict and principal.get('organizationId') == req['expected_organization_id'] and
         principal.get('userId') == req['expected_user_id'], 'observed_principal')
    for collection, aliases, scope_key in [('workbooks', ('workbookId', 'id'), 'workbook_ids'),
                                           ('dataModels', ('dataModelId', 'id'), 'data_model_ids')]:
        rows = result.get(collection)
        need(type(rows) is list, 'result_collection')
        found = set()
        for row in rows:
            need(type(row) is dict, 'result_object')
            values = {str(row[k]) for k in aliases if row.get(k) is not None}
            need(len(values) == 1, 'result_identity_aliases')
            item = values.pop()
            need(item not in found, 'duplicate_result_identity')
            found.add(item)
        expected = set(req['scope'][scope_key])
        need(found == expected if req['operation'] != 'inventory' or expected else True, 'result_selected_scope')
    return value
