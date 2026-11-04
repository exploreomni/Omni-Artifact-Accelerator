"""Passive Domo visual/app evidence, never a Domo API or authorization schema.

Original producer contracts stay unchanged in pinned files. All evidence here is
supplied and unauthenticated; even complete manifests do not establish access,
native execution, business acceptance, or write authority. Source assets remain
inert. This module uses the standard library and original local helpers only.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

SCHEMA = 'oaa-domo-visual-capture.v1'
HANDOFF_SCHEMA = 'oaa-domo-app-handoff.v1'
PROFILE = 'oaa-domo-evidence@1'
PRODUCER_PIN = '55eba0ca0690fbf14f39eddbc8a04c94a720c155'
PRODUCER_PROFILES = {PRODUCER_PIN, 'domo-source-operations@0.1.0'}
CONTRACTS = {'omnikit.domo.evidence.v1', 'omnikit.domo.source-evidence.v1',
             'domo-to-omni.dashboard-rebuild-plan.v1', 'domo-to-omni.external-redesign-handoff.v1'}
MAX_BYTES, MAX_TOTAL, MAX_FILES = 8 * 1024 * 1024, 32 * 1024 * 1024, 512
STATE_KEYS = {'filters', 'variables', 'timezone', 'locale', 'cache', 'principal'}
KINDS = {'page', 'app', 'app_page', 'component', 'card', 'query', 'placement', 'dataset', 'asset', 'operation'}
ARTIFACT_KINDS = {'definition', 'page_render', 'component_render', 'results', 'request', 'response',
                  'source_asset', 'mcp_capture'}
CHANNELS = {'platform_api', 'product_api', 'app_framework_api', 'passive_mcp', 'native_export', 'supplied', 'unknown'}
FORMATS = {'json', 'csv', 'png', 'jpeg', 'webp', 'html', 'css', 'javascript', 'text', 'sql'}
BEHAVIOR_FACETS = {'query', 'visual', 'formatting', 'layout', 'responsive', 'filters', 'variables', 'drill',
                   'navigation', 'security', 'freshness', 'export', 'actions', 'motion', 'accessibility', 'state'}
DISPOSITIONS = {'preserved', 'adapted', 'deferred', 'unsupported', 'unverified', 'not_applicable'}
SECRET_KEYS = {'password', 'passwd', 'pwd', 'apitoken', 'apikey', 'accesstoken', 'refreshtoken', 'clientsecret',
               'authorization', 'cookie', 'setcookie', 'privatekey', 'credentials', 'credential', 'producttoken',
               'dataflowtoken', 'xdomodevelopertoken', 'developertoken', 'bearertoken'}
_MODULES = {}


def need(value, code):
    if not value:
        raise ValueError('domo.' + code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and 0 < len(value) <= 4096 and not any(ord(c) < 32 for c in value)


def digest(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def module(name):
    need(name in {'sigma_visual', 'powerbi_capture_files', 'translate_artifact'}, 'module_not_allowed')
    if name not in _MODULES:
        path = Path(__file__).with_name(name + '.py').absolute()
        need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
        spec = importlib.util.spec_from_file_location('domo_local_' + name, path)
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        _MODULES[name] = value
    return _MODULES[name]


def decode(raw):
    need(type(raw) is bytes and len(raw) <= MAX_BYTES, 'json_byte_limit')
    return module('powerbi_capture_files').decode(raw)


def _screen(value):
    stack, count = [(value, 0)], 0
    while stack:
        row, depth = stack.pop()
        count += 1
        need(depth <= 40 and count <= 100000, 'evidence_structure_limit')
        if type(row) is dict:
            need(all(type(k) is str for k in row), 'evidence_key_type')
            for key, val in row.items():
                normal = re.sub('[^a-z]', '', key.lower())
                need(normal not in SECRET_KEYS or val in (None, '', '[REDACTED]') or val == {'redacted': 'secret'},
                     'credential_bearing_evidence')
                if key.startswith('authorizes_') or key in {'target_write_authority', 'build_authority',
                                                            'publish_authority', 'acceptance_authority'}:
                    need(val is False, 'contradictory_authority')
                stack.append((val, depth + 1))
        elif type(row) is list:
            stack.extend((v, depth + 1) for v in row)
        elif type(row) is str:
            need(len(row) <= MAX_BYTES, 'evidence_text_limit')
            need(not re.search(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----', row),
                 'credential_bearing_evidence')
            pattern = r'''(?ix)(?:["']?(?:api[_-]?token|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|authorization|cookie|credentials?|x[-_]domo[-_]developer[-_]token|product[-_]?token|dataflow[-_]?token)["']?\s*[:=]\s*["']?)([^\s,;"'}&]+)'''
            for found in re.finditer(pattern, row):
                need(found.group(1) in ('[REDACTED]', 'null', 'None'), 'credential_bearing_evidence')
        else:
            need(row is None or type(row) in (bool, int, float), 'evidence_type')


def _bounded(value):
    _screen(value)
    try:
        need(len(encoded(value)) <= MAX_BYTES, 'manifest_byte_limit')
    except (ValueError, OverflowError, TypeError):
        raise ValueError('domo.manifest_encoding_or_limit') from None


def _strings(value, code, allow_empty=True):
    need(type(value) is list and all(text(v) for v in value) and len(set(value)) == len(value)
         and (allow_empty or bool(value)), code)


def validate_state(value):
    need(type(value) is dict and set(value) == STATE_KEYS, 'state')
    need(all(value[k] is None or type(value[k]) is dict for k in ('filters', 'variables')), 'state_controls')
    need(all(value[k] is None or text(value[k]) for k in ('timezone', 'locale', 'principal')), 'state_identity')
    need(value['cache'] is None or type(value['cache']) in (dict, str), 'state_cache')
    _screen(value)
    return value


def _selection(value):
    need(type(value) is dict and set(value) == {'scope_id', 'version', 'reference'} and text(value['scope_id'])
         and text(value['reference']) and (value['version'] is None or text(value['version'])), 'selection')


def _same_selection(left, right):
    return all(left[k] == right[k] for k in ('scope_id', 'version'))


def _pin(value):
    module('sigma_visual')._pin(value)


def _behavior(value):
    need(type(value) is dict and set(value) == BEHAVIOR_FACETS, 'component_behavior_denominator')
    for row in value.values():
        need(type(row) is dict and row.get('disposition') in DISPOSITIONS and text(row.get('owner_ref')),
             'behavior_disposition_owner')
        _strings(row.get('evidence_refs'), 'behavior_evidence', allow_empty=False)
        _strings(row.get('acceptance_refs'), 'behavior_acceptance', allow_empty=False)
        if row['disposition'] == 'adapted':
            need(text(row.get('decision_ref')), 'behavior_adaptation_decision')


def validate_app_handoff(value, inventory=None):
    _bounded(value)
    need(type(value) is dict and value.get('schema_version') == HANDOFF_SCHEMA and
         value.get('assignment_only') is True and value.get('mode') in {'read_only', 'operational'}, 'app_handoff')
    need(all(value.get(k) is False for k in ('build_authority', 'target_write_authority', 'publish_authority',
                                           'acceptance_authority')), 'app_handoff_authority')
    need(text(value.get('owner_ref')) and text(value.get('handoff_ref')), 'app_handoff_owner')
    _strings(value.get('app_keys'), 'app_handoff_app_keys', allow_empty=False)
    _strings(value.get('evidence_refs'), 'app_handoff_evidence', allow_empty=False)
    _strings(value.get('side_effect_kinds'), 'app_handoff_side_effects')
    ops = value.get('operations')
    need(type(ops) is list and all(type(o) is dict for o in ops), 'app_operations')
    seen = set()
    for op in ops:
        need(text(op.get('operation_id')) and op['operation_id'] not in seen and text(op.get('owner_ref')) and
             text(op.get('component_key')) and op.get('disposition') in DISPOSITIONS - {'not_applicable'}, 'app_operation')
        seen.add(op['operation_id'])
        for key in ('source_evidence_ref', 'target_ref', 'authorization_requirement_ref', 'retry_policy_ref',
                    'failure_behavior_ref', 'acceptance_ref'):
            need(text(op.get(key)), 'operation_' + key)
        need(op.get('execution_authorized') is False and op.get('side_effect_kind') in value['side_effect_kinds'],
             'operation_authority_or_effect')
    if value['mode'] == 'read_only':
        need(not ops and not value['side_effect_kinds'], 'read_only_app_has_side_effects')
    else:
        need(bool(ops) and {o['side_effect_kind'] for o in ops} == set(value['side_effect_kinds']), 'operation_denominator')
    if inventory is not None:
        index = {row['key']: row for row in inventory['items']}
        need(set(value['app_keys']) == {k for k, r in index.items() if r['kind'] == 'app' and r['disposition'] == 'include'},
             'app_handoff_scope')
        captured_ops = {r['native_id']: r for r in index.values() if r['kind'] == 'operation' and r['disposition'] == 'include'}
        need(set(captured_ops) == seen, 'app_operation_denominator')
        for op in ops:
            need(op['component_key'] in index and index[op['component_key']]['kind'] == 'component'
                 and index[op['component_key']]['disposition'] == 'include', 'operation_component')
            declared = captured_ops[op['operation_id']]['configuration']
            need(declared.get('component_key') == op['component_key'] and declared.get('side_effect_kind') == op['side_effect_kind'],
                 'operation_inventory_binding')
    return value


def _inventory(value):
    inv = value.get('inventory')
    need(type(inv) is dict and text(inv.get('reference')) and inv.get('completeness') in {'partial', 'selected_scope_declared'}
         and type(inv.get('items')) is list and 0 < len(inv['items']) <= 5000, 'independent_inventory')
    counts = inv.get('expected_counts')
    need(type(counts) is dict and set(counts) <= KINDS and all(type(n) is int and n >= 0 for n in counts.values()),
         'inventory_expected_counts')
    index, natives = {}, set()
    for row in inv['items']:
        need(type(row) is dict and text(row.get('key')) and row['key'] not in index and row.get('kind') in KINDS
             and text(row.get('native_id')) and text(row.get('reference')) and row.get('disposition') in
             {'include', 'out_of_scope', 'deferred', 'unknown'} and type(row.get('configuration')) is dict
             and 'parent_key' in row and (row['parent_key'] is None or text(row['parent_key'])), 'inventory_item')
        index[row['key']] = row
        for field in ('page_id', 'app_id', 'card_id', 'query_id', 'placement_id'):
            need(row.get(field) is None or text(row[field]), 'inventory_identity')
        key = (row['kind'], row.get('app_id'), row.get('page_id'), row['native_id'])
        need(key not in natives, 'duplicate_native_identity')
        natives.add(key)
        required = row.get('required_evidence_kinds')
        _strings(required, 'required_evidence_kinds', allow_empty=row['disposition'] != 'include')
        need(set(required) <= ARTIFACT_KINDS, 'required_evidence_kind')
        if row['kind'] == 'component':
            _behavior(row.get('behaviors'))
            need(text(row.get('app_id')) and text(row.get('page_id')), 'component_app_page_identity')
        if row['kind'] == 'app':
            need(row['configuration'].get('app_family') in {'app_studio', 'pro_code', 'brick', 'unknown'}
                 and 'version' in row['configuration'] and (row['configuration']['version'] is None or text(row['configuration']['version'])),
                 'app_family_version')
    actual = {kind: sum(row['kind'] == kind for row in inv['items']) for kind in KINDS}
    if inv['completeness'] == 'selected_scope_declared':
        need(all(kind in counts and counts[kind] == n for kind, n in actual.items() if n)
             and all(actual[kind] == n for kind, n in counts.items()), 'inventory_denominator_mismatch')
    for key, row in index.items():
        chain, parent, ancestors = {key}, row['parent_key'], []
        while parent is not None:
            need(parent in index and parent not in chain, 'inventory_parent_or_cycle')
            chain.add(parent)
            ancestors.append(index[parent])
            parent = index[parent]['parent_key']
        for kind, field in [('app', 'app_id'), ('app_page', 'page_id'), ('page', 'page_id')]:
            members = [r for r in ancestors if r['kind'] == kind]
            if members and row.get(field) is not None:
                need(row[field] == members[0]['native_id'], 'inventory_parent_identity_mismatch')
        if row['kind'] == 'placement':
            need(text(row.get('placement_id')) and row['placement_id'] == row['native_id'] and text(row.get('page_id')),
                 'placement_identity')
            target = row['configuration'].get('target_key')
            need(target in index and index[target]['kind'] in {'card', 'component'}, 'placement_target')
            if index[target]['kind'] == 'card':
                need(row.get('card_id') == index[target]['native_id'], 'placement_card_identity')
        if row['kind'] == 'query':
            need(row.get('query_id') == row['native_id'], 'query_identity')
            owner = row['configuration'].get('result_owner_key')
            need(owner in index and index[owner]['kind'] in {'card', 'component', 'dataset'}, 'query_result_owner')
            if index[owner]['kind'] == 'card':
                need(row.get('card_id') == index[owner]['native_id'], 'query_card_identity')
        if row['kind'] == 'asset':
            need(text(row.get('app_id')) and 'version' in row['configuration'], 'asset_app_version')
        if row['kind'] == 'operation':
            component = row['configuration'].get('component_key')
            need(component in index and index[component]['kind'] == 'component'
                 and text(row['configuration'].get('side_effect_kind')), 'operation_inventory_component')
    return index


def _result_evidence(a, value, index):
    need(a['format'] in {'json', 'csv'} and len(a['object_keys']) == 1 and type(a.get('parser_profile')) is dict
         and a['parser_profile'].get('format') == a['format'] and text(a.get('query_id')), 'result_profile_scope_query')
    complete = a.get('completeness')
    need(type(complete) is dict and complete.get('status') in {'complete', 'partial', 'unknown'}
         and (complete.get('row_count') is None or type(complete['row_count']) is int and complete['row_count'] >= 0),
         'result_completeness')
    _strings(complete.get('flags'), 'result_completeness_flags')
    need(complete.get('reference') is None or text(complete['reference']), 'result_completeness_reference')
    if complete['status'] == 'complete':
        need(complete['row_count'] is not None and text(complete['reference']) and not complete['flags'], 'complete_result_evidence')
    for name, fields in [('population', {'key', 'reference'}), ('freshness', {'observed_at', 'data_watermark', 'reference'})]:
        row = a.get(name)
        need(type(row) is dict and set(row) == fields and all(v is None or text(v) for v in row.values()), 'result_' + name)
    if a['freshness']['observed_at'] is not None:
        module('sigma_visual')._time(a['freshness']['observed_at'])
    observed = a.get('observed_state')
    if observed is not None:
        need(type(observed) is dict and text(observed.get('reference')) and digest(observed.get('definition_sha256'))
             and observed.get('execution_status') in {'completed', 'partial', 'unknown'}
             and observed.get('result_scope') in {'full_data', 'preview', 'sample', 'unknown'}
             and observed.get('execution_kind') in {'card', 'app_component', 'dataset', 'unknown'}, 'observed_result')
        validate_state(observed.get('state'))
        _selection(observed.get('selection'))
        need(observed.get('query_id') == a['query_id'] and observed['state']['principal'] in (None, value['identity']['principal_ref']),
             'observed_query_principal')
        need(observed.get('row_limit') is None or type(observed['row_limit']) is int and observed['row_limit'] > 0, 'observed_row_limit')
        need(observed.get('placement_id') is None or text(observed['placement_id']), 'observed_placement')
        for name in ('request_artifact_id', 'response_artifact_id'):
            need(observed.get(name) is None or text(observed[name]), 'observed_' + name)


def validate_capture(value):
    _bounded(value)
    need(type(value) is dict and value.get('schema_version') == SCHEMA, 'capture_schema')
    need(value.get('content_hash') == sha({k: v for k, v in value.items() if k != 'content_hash'}), 'capture_hash')
    need(value.get('status') in {'complete', 'partial', 'blocked'} and value.get('evidence_mode') in
         {'synthetic_fixture', 'supplied_capture'}, 'capture_status_mode')
    need(value.get('target_write_authority') is False and value.get('native_validation') == 'not_performed'
         and value.get('business_acceptance') == 'not_assessed', 'capture_authority')
    identity = value.get('identity')
    need(type(identity) is dict and set(identity) == {'source_origin', 'tenant_ref', 'principal_ref'}
         and all(text(v) for v in identity.values()), 'identity')
    module('sigma_visual')._origin(identity['source_origin'])
    _selection(value.get('selection'))
    validate_state(value.get('state'))
    need(value['state']['principal'] in (None, identity['principal_ref']), 'state_principal')
    producer = value.get('producer')
    need(type(producer) is dict and set(producer) == {'contract_version', 'revision', 'file'}
         and producer['contract_version'] in CONTRACTS and producer['revision'] in PRODUCER_PROFILES, 'producer_contract_revision')
    _pin(producer['file'])
    index = _inventory(value)
    artifacts = value.get('artifacts')
    need(type(artifacts) is list and 0 < len(artifacts) < MAX_FILES, 'artifacts')
    seen, total = set(), producer['file']['bytes']
    for a in artifacts:
        need(type(a) is dict and text(a.get('artifact_id')) and a['artifact_id'] != 'producer' and a['artifact_id'] not in seen
             and a.get('kind') in ARTIFACT_KINDS and a.get('source_channel') in CHANNELS and a.get('format') in FORMATS
             and text(a.get('reference')), 'artifact')
        seen.add(a['artifact_id'])
        _pin(a.get('file'))
        total += a['file']['bytes']
        _strings(a.get('object_keys'), 'artifact_scope', allow_empty=False)
        need(set(a['object_keys']) <= set(index), 'artifact_unknown_object')
        _selection(a.get('selection'))
        need(a.get('state_sha256') == sha(value['state']) and a.get('principal_ref') == identity['principal_ref'], 'artifact_state_principal')
        module('sigma_visual')._time(a.get('captured_at'))
        if a['kind'] in {'definition', 'request', 'mcp_capture'}:
            need(a['format'] == 'json', 'definition_request_response_json')
        if a['kind'] == 'response':
            need(a['format'] in {'json', 'csv'}, 'response_format')
        if a['kind'] in {'page_render', 'component_render'}:
            need(a['format'] in {'png', 'jpeg', 'webp'}, 'render_format')
            viewport = a.get('viewport')
            need(type(viewport) is dict and set(viewport) == {'width', 'height', 'device_scale'}
                 and all(type(viewport[k]) is int and 0 < viewport[k] <= 16384 for k in ('width', 'height'))
                 and type(viewport['device_scale']) in (int, float) and 0 < viewport['device_scale'] <= 4
                 and text(a.get('theme_ref')), 'render_viewport_theme')
        if a['kind'] == 'results':
            _result_evidence(a, value, index)
        if a['kind'] == 'mcp_capture':
            need(a['source_channel'] == 'passive_mcp' and type(a.get('mcp_evidence')) is dict and
                 all(text(a['mcp_evidence'].get(k)) for k in ('server_ref', 'tool_name', 'tool_schema_ref', 'session_ref')),
                 'mcp_provenance')
    need(total <= MAX_TOTAL, 'total_bytes')
    module('sigma_visual')._paths([producer['file']['path']] + [a['file']['path'] for a in artifacts])
    artifact_index = {a['artifact_id']: a for a in artifacts}
    for row in index.values():
        mapping = row.get('source_mapping')
        if mapping is not None:
            need(type(mapping) is dict and set(mapping) == {'artifact_id', 'pointer'}
                 and type(mapping['pointer']) is str and (mapping['pointer'] == '' or mapping['pointer'].startswith('/'))
                 and digest(row['configuration'].get('definition_sha256')), 'definition_mapping')
            if mapping['artifact_id'] != 'producer':
                a = artifact_index.get(mapping['artifact_id'])
                need(a is not None and a['kind'] == 'definition' and row['key'] in a['object_keys'], 'definition_artifact_binding')
    for a in artifacts:
        observed = a.get('observed_state')
        if a['kind'] == 'results':
            selected = index[a['object_keys'][0]]
            target_key = selected['configuration']['target_key'] if selected['kind'] == 'placement' else selected['key']
            queries = [r for r in index.values() if r['kind'] == 'query' and r['native_id'] == a['query_id']
                       and r['configuration']['result_owner_key'] == target_key]
            need(len(queries) == 1, 'result_query_membership')
        if a['kind'] == 'results' and observed is not None:
            for name, kind in [('request_artifact_id', 'request'), ('response_artifact_id', 'response')]:
                if observed.get(name) is not None:
                    raw = artifact_index.get(observed[name])
                    need(raw is not None and raw['kind'] == kind and raw['object_keys'] == a['object_keys']
                         and raw.get('query_id') == a['query_id'], 'execution_evidence_binding')
                    if kind == 'response':
                        need(all(raw['file'][k] == a['file'][k] for k in ('sha256', 'bytes')), 'response_result_bytes_mismatch')
    apps = [r for r in index.values() if r['kind'] == 'app' and r['disposition'] == 'include']
    if apps or value.get('app_handoff') is not None:
        validate_app_handoff(value.get('app_handoff'), value['inventory'])
    _strings(value.get('gaps'), 'capture_gaps')
    return value


def definition_fingerprint(value):
    return sha({k: value[k] for k in ('identity', 'producer', 'selection', 'inventory')})


def result_binding(value, artifact):
    return {'capture_content_hash': value['content_hash'], 'definition_fingerprint': definition_fingerprint(value),
            'object_key': artifact['object_keys'][0], 'attachment_id': artifact['artifact_id'],
            'state_sha256': sha(value['state']), 'attachment_sha256': artifact['file']['sha256']}


def normalize_results(raw, profile, binding):
    _screen(profile)
    if type(raw) is bytes:
        try:
            _screen(raw.decode('utf-8-sig'))
        except UnicodeError:
            raise ValueError('domo.result_utf8_required') from None
    result = module('sigma_visual').normalize_results(raw, profile, binding)
    result.update(kind='domo_normalized_results', qualification='supplied_arithmetic_only_until_execution_state_and_completeness_bound')
    return result


def evidence_gaps(value):
    """Manifest-only gaps. File verification adds byte-level and pointer evidence."""
    validate_capture(value)
    gaps = list(value['gaps'])
    index = {r['key']: r for r in value['inventory']['items']}
    if value['status'] != 'complete':
        gaps.append('domo.capture_' + value['status'])
    if value['inventory']['completeness'] != 'selected_scope_declared':
        gaps.append('domo.independent_inventory_partial')
    for row in index.values():
        if row['disposition'] == 'include':
            covered = {a['kind'] for a in value['artifacts'] if row['key'] in a['object_keys']}
            if row.get('source_mapping', {}).get('artifact_id') == 'producer':
                covered.add('definition')
            for kind in set(row['required_evidence_kinds']) - covered:
                gaps.append('domo.required_evidence_missing:' + row['key'] + ':' + kind)
            if not row.get('source_mapping'):
                gaps.append('domo.definition_evidence_missing:' + row['key'])
        for facet, behavior in row.get('behaviors', {}).items():
            if behavior['disposition'] in {'deferred', 'unsupported', 'unverified'}:
                gaps.append('domo.behavior_unresolved:' + row['key'] + ':' + facet)
        if row['kind'] in {'app', 'asset'} and row['configuration'].get('version') is None:
            gaps.append('domo.app_asset_version_unverified:' + row['key'])
    for a in value['artifacts']:
        if not _same_selection(a['selection'], value['selection']):
            gaps.append('domo.artifact_selection_mismatch:' + a['artifact_id'])
        if a['kind'] == 'source_asset':
            gaps.append('domo.source_asset_inert_not_security_qualified:' + a['artifact_id'])
        if a['kind'] == 'mcp_capture':
            gaps.append('domo.passive_mcp_not_execution_authority')
    for op in value.get('app_handoff', {}).get('operations', []):
        if op['disposition'] in {'deferred', 'unsupported', 'unverified'}:
            gaps.append('domo.operation_unresolved:' + op['operation_id'])
    return sorted(set(gaps))


def verify_capture_files(value, root):
    validate_capture(value)
    safe = module('sigma_visual')
    producer_raw = safe._read_pin(root, value['producer']['file'])
    producer = decode(producer_raw)
    _screen(producer)
    need(type(producer) is dict and producer.get('contract_version') == value['producer']['contract_version'], 'original_producer_contract')
    # This invokes only the already shipped passive parser, never the source engine.
    producer_projection = module('translate_artifact').translate(producer_raw, 'domo-agent', value['producer']['revision'])
    originals = {'producer': producer}
    verified = [{**value['producer']['file'], 'format': 'json', 'inspection': {'producer_contract': producer['contract_version']}}]
    gaps, total = evidence_gaps(value), len(producer_raw)
    for a in value['artifacts']:
        raw = safe._read_pin(root, a['file'])
        total += len(raw)
        need(total <= MAX_TOTAL, 'capture_total_bytes')
        need(not raw.startswith((b'PK\x03\x04', b'PK\x05\x06', b'\x1f\x8b', b'7z\xbc\xaf\x27\x1c'))
             and Path(a['file']['path']).suffix.lower() not in {'.zip', '.gz', '.tgz', '.tar', '.7z', '.rar', '.blend'},
             'archives_and_executable_containers_not_supported')
        info, fmt = {}, a['format']
        if fmt == 'png':
            info['actual_dimensions'] = module('powerbi_capture_files').png_info(raw)
        elif fmt == 'jpeg':
            need(len(raw) >= 4 and raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'), 'jpeg_signature')
            _screen(raw.decode('latin1'))
            gaps.append('domo.jpeg_decode_metadata_and_rendering_not_qualified')
        elif fmt == 'webp':
            need(len(raw) >= 16 and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'
                 and int.from_bytes(raw[4:8], 'little') + 8 == len(raw), 'webp_signature')
            _screen(raw.decode('latin1'))
            gaps.append('domo.webp_decode_metadata_and_rendering_not_qualified')
        elif fmt == 'json':
            data = decode(raw)
            _screen(data)
            need(type(data) in (dict, list), 'json_object_or_array_required')
            originals[a['artifact_id']] = data
        else:
            try:
                plain = raw.decode('utf-8-sig')
            except UnicodeError:
                raise ValueError('domo.text_utf8_required') from None
            need('\x00' not in plain, 'text_binary_rejected')
            _screen(plain)
            info['execution'] = 'never_executed'
        if a['kind'] == 'results':
            normalized = normalize_results(raw, a['parser_profile'], result_binding(value, a))
            count = a['completeness']['row_count']
            need(count is None or count == normalized['row_count'], 'result_row_count_mismatch')
            info['observed_rows'] = normalized['row_count']
        if a.get('actual_dimensions') is not None:
            need(info.get('actual_dimensions') == a['actual_dimensions'], 'image_dimensions_mismatch')
        verified.append({**a['file'], 'format': fmt, 'inspection': info})
    for row in value['inventory']['items']:
        mapping = row.get('source_mapping')
        if mapping is not None:
            node = safe._pointer(originals[mapping['artifact_id']], mapping['pointer'])
            need(type(node) is dict and sha(node) == row['configuration']['definition_sha256'], 'original_definition_hash')
    return {'schema_version': 1, 'kind': 'domo_file_verification', 'capture_content_hash': value['content_hash'],
            'definition_fingerprint': definition_fingerprint(value), 'verified_files': verified,
            'gaps': sorted(set(gaps)), 'producer_gaps': copy.deepcopy(producer_projection['gaps']),
            'provenance': 'supplied_not_authenticated', 'target_write_authority': False,
            'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}


def _selected(value, key):
    index = {r['key']: r for r in value['inventory']['items']}
    need(key in index, 'case_inventory_key')
    selected = index[key]
    target = index[selected['configuration']['target_key']] if selected['kind'] == 'placement' else selected
    for start in (selected, target):
        row = start
        while row is not None:
            need(row['disposition'] == 'include' and not row['configuration'].get('restricted')
                 and not row['configuration'].get('private'), 'case_scope_restricted')
            row = index.get(row['parent_key'])
    return selected, target


def case_binding(asset, case, capture):
    validate_capture(capture)
    binding, identity = case.get('source_binding'), asset.get('source_identity', {})
    need(type(binding) is dict and set(binding) == {'capture_content_hash', 'definition_fingerprint', 'object_key',
         'attachment_id', 'state_sha256', 'attachment_sha256'}, 'case_binding_required')
    key = identity.get('object_key', identity.get('inventory_key'))
    selected, target = _selected(capture, key)
    need(identity.get('definition_fingerprint') == definition_fingerprint(capture)
         and identity.get('tenant_ref') == capture['identity']['tenant_ref'], 'case_definition_identity')
    need(asset.get('source_id') == selected['native_id'], 'case_source_identity')
    expected = {'object_key': key, 'definition_fingerprint': definition_fingerprint(capture),
                'state_sha256': sha(capture['state']), 'capture_content_hash': capture['content_hash']}
    need(all(binding.get(k) == v for k, v in expected.items()), 'case_state_or_definition')
    matches = [a for a in capture['artifacts'] if a['artifact_id'] == binding.get('attachment_id') and a['object_keys'] == [key]]
    need(len(matches) == 1 and (case.get('lane') != 'numeric' or matches[0]['kind'] == 'results'), 'case_artifact')
    need(binding.get('attachment_sha256') == matches[0]['file']['sha256'], 'case_attachment_hash')
    return binding


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    a = next(a for a in capture['artifacts'] if a['artifact_id'] == binding['attachment_id'])
    need(a['kind'] == 'results', 'numeric_result_required')
    selected, item = _selected(capture, binding['object_key'])
    gaps = ['source.' + g for g in evidence_gaps(capture)]
    if not case.get('source_capture'):
        gaps.append('source.domo_case_capture_required')
    definition = item['configuration'].get('definition_sha256')
    if not digest(definition) or item.get('source_mapping') is None:
        gaps.append('source.domo_definition_evidence_missing')
    pin = source.get('raw_file') if source.get('format') == 'domo-normalized' else source.get('file')
    if type(pin) is not dict or any(pin.get(k) != a['file'][k] for k in ('sha256', 'bytes')):
        gaps.append('source.domo_result_bytes_not_bound')
    full = a['completeness']
    if full['status'] != 'complete' or not full['reference'] or full['flags']:
        gaps.append('source.domo_result_completeness_unqualified')
    if capture['selection']['version'] is None:
        gaps.append('source.domo_selection_unqualified')
    observed = a.get('observed_state')
    if observed is None:
        gaps.append('source.domo_observed_state_missing')
    else:
        if observed['execution_status'] != 'completed' or observed['result_scope'] != 'full_data':
            gaps.append('source.domo_execution_or_population_unqualified')
        expected_kind = {'card': 'card', 'component': 'app_component', 'dataset': 'dataset'}.get(item['kind'])
        if expected_kind is None or observed['execution_kind'] != expected_kind:
            gaps.append('source.domo_execution_kind_not_artifact_result')
        if observed['definition_sha256'] != definition:
            gaps.append('source.domo_observed_definition_mismatch')
        if not _same_selection(observed['selection'], capture['selection']):
            gaps.append('source.domo_observed_selection_mismatch')
        if observed.get('row_limit') is not None and full.get('row_count') is not None and full['row_count'] >= observed['row_limit']:
            gaps.append('source.domo_result_at_limit')
        if selected['kind'] == 'placement' and observed.get('placement_id') != selected['placement_id']:
            gaps.append('source.domo_placement_state_unqualified')
        for key in ('request_artifact_id', 'response_artifact_id'):
            if not observed.get(key):
                gaps.append('source.domo_original_execution_' + key + '_required')
        for key in STATE_KEYS:
            expected = capture['state'][key]
            if expected is None or observed['state'].get(key) != expected or source.get('context', {}).get(key) != expected:
                gaps.append('source.domo_state.' + key)
            if key not in {'principal', 'cache'} and target.get('context', {}).get(key) != expected:
                gaps.append('context.' + key)
    if not text(a['population']['reference']):
        gaps.append('source.domo_population_reference')
    for key, expected in {'population': a['population']['key'], 'data_watermark': a['freshness']['data_watermark'],
                          'freshness_reference': a['freshness']['reference']}.items():
        if not expected or not a['freshness']['observed_at'] or source.get('context', {}).get(key) != expected:
            gaps.append('source.domo_context.' + key)
        if key == 'freshness_reference':
            if not text(target.get('context', {}).get(key)):
                gaps.append('target.domo_freshness_reference')
        elif target.get('context', {}).get(key) != expected:
            gaps.append('context.' + key)
    if source.get('format') != 'domo-normalized' or type(normalized) is not dict or normalized.get('binding') != result_binding(capture, a):
        gaps.append('source.domo_normalization_binding_required')
    else:
        if normalized.get('parser_profile') != a['parser_profile'] or normalized.get('row_count') != full.get('row_count'):
            gaps.append('source.domo_parser_profile_or_row_count')
        fields = [c['name'] for c in a['parser_profile'].get('columns', [])]
        if type(columns) is not list or len(columns) != len(fields) or {c.get('source') for c in columns} != set(fields):
            gaps.append('source.domo_complete_column_mapping_required')
        for col in a['parser_profile'].get('columns', []):
            if col.get('currency') is not None:
                mapped = [c.get('target') for c in columns or [] if c.get('source') == col['name']]
                code = col['currency']['code']
                if len(mapped) != 1 or source.get('context', {}).get('currencies', {}).get(col['name']) != code or \
                        target.get('context', {}).get('currencies', {}).get(mapped[0]) != code:
                    gaps.append('context.currency.' + col['name'])
    return sorted(set(gaps))


def project_assets(value):
    validate_capture(value)
    index = {r['key']: r for r in value['inventory']['items']}
    query_owners = {r['configuration']['result_owner_key'] for r in index.values() if r['kind'] == 'query'}
    result = []
    for i, row in enumerate(value['inventory']['items']):
        kind = {'card': 'visual', 'component': 'visual' if row['key'] in query_owners else 'definition', 'app_page': 'page'}.get(row['kind'], row['kind'])
        if kind not in {'app', 'page', 'visual', 'layout', 'placement', 'query'}:
            kind = 'definition'
        target = row['configuration'].get('target_key', row['key'])
        restricted, current = False, row
        while current is not None:
            restricted = restricted or current['configuration'].get('restricted') is True or current['configuration'].get('private') is True
            current = index.get(current['parent_key'])
        behaviors = row.get('behaviors', {})
        control_required = any(behaviors.get(k, {}).get('disposition') not in (None, 'not_applicable') for k in ('filters', 'variables'))
        control_required = control_required or any(bool(row['configuration'].get(k)) for k in ('controls', 'variables'))
        identity = {'object_key': row['key'], 'inventory_kind': row['kind'], 'tenant_ref': value['identity']['tenant_ref'],
                    'definition_fingerprint': definition_fingerprint(value), 'disposition': row['disposition'],
                    'source_platform': 'domo', 'declared_disposition': row['disposition'],
                    'restricted_private_scope': restricted, 'query_visual': row['kind'] in {'card', 'component', 'placement'} and target in query_owners,
                    'control_required': control_required,
                    'requires_source_review': not row.get('source_mapping') or any(b['disposition'] in {'deferred', 'unsupported', 'unverified'} for b in behaviors.values()),
                    **{k: row.get(k) for k in ('app_id', 'page_id', 'card_id', 'query_id', 'placement_id')}}
        facets = {'visual': {'status': 'declared', 'value': copy.deepcopy(row['configuration'])},
                  'interactions': {'status': 'declared', 'value': copy.deepcopy(row.get('behaviors', {}))},
                  'filters': {'status': 'declared', 'value': {k: copy.deepcopy(behaviors[k]) for k in ('filters', 'variables') if k in behaviors}},
                  'security': {'status': 'needs_review', 'value': {'principal_ref': value['identity']['principal_ref']}},
                  'layout': {'status': 'declared', 'value': {'parent_key': row['parent_key'], 'placement_id': row.get('placement_id')}}}
        result.append({'kind': kind, 'source_id': row['native_id'], 'scope': value['identity']['tenant_ref'] + '/' + row['key'],
                       'source_identity': identity, 'facets': facets, 'source_path': '/inventory/items/' + str(i),
                       'source_payload': copy.deepcopy(row)})
    return result
