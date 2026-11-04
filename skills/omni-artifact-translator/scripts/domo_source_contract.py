"""Original, passive request contract for the reviewed Domo source CLI.

No engine imports, credentials, arbitrary commands or target operations.
"""
import copy
from datetime import datetime
import re
from urllib.parse import urlsplit

SCHEMA = 'oaa-domo-source-request.v1'
SCOPE_FIELDS = ('page_ids', 'card_ids', 'dataset_ids', 'dataflow_ids', 'app_ids', 'workflow_ids')
SOURCE_FIELDS = {'origin', 'tenant_ref', 'principal_ref', 'permission_context_ref', 'authorization_ref'}
LIMITS = {'max_requests': 10000, 'max_response_bytes': 25 * 1024 * 1024,
          'max_total_bytes': 100 * 1024 * 1024, 'max_elapsed_seconds': 300}


def need(ok, code):
    if not ok:
        raise ValueError('domo.request.' + code)


def text(value, maximum=2048):
    return type(value) is str and 0 < len(value) <= maximum and not any(ord(c) < 32 for c in value)


def origin(value):
    need(text(value), 'origin_required')
    parsed = urlsplit(value)
    need(parsed.scheme == 'https' and parsed.hostname and parsed.hostname == parsed.netloc
         and parsed.hostname.isascii() and parsed.hostname == parsed.hostname.lower()
         and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', parsed.hostname)
         and not parsed.path and not parsed.query and not parsed.fragment, 'exact_https_origin_required')
    return parsed.hostname


def reference(value):
    need(text(value) and not re.search(r'(?i)(?:bearer\s|[?&](?:token|key|signature)=)', value), 'reference_required')


def request(value):
    need(type(value) is dict and set(value) == {'schema_version', 'request_id', 'operation', 'source',
         'scope', 'completeness', 'limits', 'observed_at', 'evidence_mode'}, 'fields')
    need(value['schema_version'] == SCHEMA and value['operation'] in ('discover', 'capture'), 'operation')
    need(text(value['request_id'], 100) and re.fullmatch(r'[A-Za-z0-9_-]+', value['request_id']), 'identity')
    source = value['source']
    need(type(source) is dict and set(source) == SOURCE_FIELDS, 'source_fields')
    origin(source['origin'])
    for key in SOURCE_FIELDS - {'origin'}:
        reference(source[key])
    need(value['evidence_mode'] in ('synthetic_fixture', 'live_tenant', 'supplied_export'), 'evidence_mode')
    need(text(value['observed_at'], 80), 'timestamp')
    stamp = datetime.fromisoformat(value['observed_at'].replace('Z', '+00:00'))
    need(stamp.tzinfo is not None, 'timezone_required')
    scope = value['scope']
    need(type(scope) is dict and set(scope) == set(SCOPE_FIELDS) | {'include_portfolio',
         'include_dataflows', 'max_dependency_dataflows', 'max_dependency_datasets'}, 'scope_fields')
    for field in SCOPE_FIELDS:
        ids = scope[field]
        need(type(ids) is list and len(ids) <= 500 and all(text(x, 200) and
             re.fullmatch(r'[A-Za-z0-9_.:-]+', x) for x in ids) and len(ids) == len(set(ids)), 'distinct_safe_ids')
    for field in ('include_portfolio', 'include_dataflows'):
        need(type(scope[field]) is bool, 'explicit_scope_flags')
    for field, maximum in (('max_dependency_dataflows', 500), ('max_dependency_datasets', 1000)):
        need(type(scope[field]) is int and 0 <= scope[field] <= maximum, 'dependency_budget')
    need(value['operation'] != 'capture' or any(scope[k] for k in SCOPE_FIELDS), 'selected_capture_required')
    need(value['operation'] != 'discover' or scope['include_portfolio'], 'discovery_scope_required')
    need(not scope['dataflow_ids'] or scope['include_dataflows'], 'dataflow_enablement_required')
    context = value['completeness']
    need(type(context) is dict and set(context) <= {'expected_counts', 'request_window'}, 'completeness_fields')
    counts = context.get('expected_counts', {})
    need(type(counts) is dict and set(counts) <= {'pages', 'cards', 'datasets'}, 'expected_counts')
    for record in counts.values():
        need(type(record) is dict and set(record) == {'count', 'source_ref', 'channel'} and
             type(record['count']) is int and 0 <= record['count'] <= 10000000 and
             record['channel'] in ('domostats_connector', 'governance_connector', 'customer_operated_export'),
             'count_evidence_required')
        reference(record['source_ref'])
        ref = urlsplit(record['source_ref'])
        need(ref.scheme and ref.scheme.lower() not in ('http', 'secret', 'vault', 'credential',
             'secret-ref', 'vault-ref', 'credential-ref') and not ref.username and not ref.password
             and not ref.query and not ref.fragment and (ref.netloc or ref.path)
             and not any(c.isspace() for c in record['source_ref']), 'count_provenance_required')
    if context.get('request_window') is not None:
        window = context['request_window']
        need(type(window) is dict and set(window) == {'start', 'end', 'timezone'} and text(window['timezone']), 'request_window')
        start, end = (datetime.fromisoformat(window[k].replace('Z', '+00:00')) for k in ('start', 'end'))
        need(start.tzinfo is not None and end.tzinfo is not None and start <= end <= stamp, 'request_window_order')
    limits = value['limits']
    need(type(limits) is dict and set(limits) == set(LIMITS), 'transport_limits_required')
    need(all(type(limits[k]) is int and 1 <= limits[k] <= maximum for k, maximum in LIMITS.items())
         and limits['max_response_bytes'] <= limits['max_total_bytes'], 'finite_transport_limits')
    return value


def bridge_request(value):
    request(value)
    source, scope = value['source'], value['scope']
    return {'schema_version': 'omnikit.migration.bridge.v1', 'request_id': value['request_id'],
        'source': 'domo', 'mode': 'api', 'include_model_suggestions': False,
        'connection': {'base_url': source['origin'], 'auth': {
            'tenant_ref': source['tenant_ref'], 'visibility_principal_ref': source['principal_ref'],
            'permission_context_ref': source['permission_context_ref'], 'acquired_at': value['observed_at'],
            'environment': 'unknown', 'sensitivity': 'confidential', 'redaction_state': 'pending',
            **copy.deepcopy(value['completeness']), 'transport_limits': copy.deepcopy(value['limits'])}},
        'scope': {k: copy.deepcopy(scope[k]) for k in (*SCOPE_FIELDS, 'include_portfolio')}}
