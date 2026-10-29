"""Passive ThoughtSpot JSON evidence projection; no source or target execution.

Native JSON TML and independently enumerated scope are distinct evidence. This
module does not implement a DMA producer, SQL compiler, browser or tenant client.
"""
import copy
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def need(condition, code):
    if not condition:
        raise ValueError('thoughtspot.' + code)


def module(name):
    need(name in ('powerbi_capture_files', 'powerbi_visual', 'thoughtspot_capture'), 'module_rejected')
    path = Path(__file__).with_name(name + '.py')
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
    spec = importlib.util.spec_from_file_location('thoughtspot_visual_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F = module('powerbi_capture_files')
SCHEMA = SNAPSHOT_SCHEMA = 'thoughtspot-api-snapshot.v1'
OBJECT_KINDS = {'liveboard', 'answer', 'table', 'worksheet', 'model', 'view', 'unknown'}
KINDS = {'liveboard', 'dashboard', 'page', 'tab', 'group', 'layout', 'answer', 'visual',
         'placement', 'content', 'note', 'control', 'filter', 'parameter', 'view', 'private_view',
         'definition', 'unknown'}


def encoded(value):
    return F.encoded(value)


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value, maximum=2048):
    return type(value) is str and 0 < len(value) <= maximum and all(ord(c) >= 32 for c in value)


def digest(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def pointer(value, path):
    need(type(path) is str and (path == '' or path.startswith('/')) and len(path) <= 2048, 'json_pointer')
    for part in path.split('/')[1:] if path else []:
        need(not re.search(r'~(?![01])', part), 'json_pointer_escape')
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(part in value, 'json_pointer_missing')
            value = value[part]
        elif type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', part) and int(part) < len(value), 'json_pointer_index')
            value = value[int(part)]
        else:
            raise ValueError('thoughtspot.json_pointer_missing')
    return value


def result_context(value):
    need(type(value) is dict and set(value) == {'data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage', 'reference'}
         and value['data_mode'] in ('full_data', 'preview', 'test', 'unknown')
         and (value['row_limit'] is None or type(value['row_limit']) is int and value['row_limit'] > 0)
         and value['row_limit_stage'] in ('before_aggregation', 'after_aggregation', 'none', 'unknown')
         and value['aggregation_stage'] in ('native_report', 'raw_query', 'in_document', 'unknown')
         and text(value['reference']), 'result_context')
    need((value['row_limit_stage'] not in ('before_aggregation', 'after_aggregation') or value['row_limit'] is not None)
         and (value['row_limit_stage'] != 'none' or value['row_limit'] is None), 'result_limit_stage')
    return value


def client_state(value):
    """Strict JSON only; return review evidence instead of evaluating JS."""
    try:
        decoded = F.decode(value.encode()) if type(value) is str else F.decode(encoded(value))
        need(type(decoded) is dict, 'client_state_object')
        F.secret_check(decoded)
        return {'status': 'json_data_only', 'value': decoded, 'execution_performed': False}
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return {'status': 'opaque_requires_review', 'value': None, 'execution_performed': False}


def _objects(value):
    return {(row['kind'], row['id']): row for row in value['objects']}


def mapped_node(item, objects):
    mapping = item['source_mapping']
    return None if mapping is None else pointer(objects[(mapping['object_kind'], mapping['object_id'])]['payload'], mapping['pointer'])


def _is_private(row, node=None):
    if row['kind'] == 'private_view' or row['configuration'].get('private_view') is True:
        return True
    is_view = row['kind'] == 'view' or bool(row['source_mapping'] and '/views/' in row['source_mapping']['pointer'])
    return is_view and not (type(node) is dict and node.get('is_public') is True)


def restricted(item, indexed, objects):
    """Private selection must cover the actual view ancestor, not just a child."""
    seen = set()
    while item is not None:
        need(item['key'] not in seen, 'inventory_cycle')
        seen.add(item['key'])
        if _is_private(item, mapped_node(item, objects)) and not text(item['configuration'].get('selection_reference')):
            return True
        item = indexed.get(item['parent_key'])
    return False


def query_node(row, objects):
    node = mapped_node(row, objects)
    mapping = row['source_mapping']
    if row['kind'] not in ('answer', 'visual') or type(node) is not dict or mapping is None:
        return False
    if mapping['object_kind'] == 'answer' and mapping['pointer'] in ('', '/answer'):
        return type(node.get('answer')) is dict or ('search_query' in node and any(k in node for k in ('chart', 'table', 'tables')))
    if mapping['object_kind'] == 'liveboard' and re.fullmatch(r'/liveboard/visualizations/(0|[1-9][0-9]*)(/answer)?', mapping['pointer']):
        return mapping['pointer'].endswith('/answer') or type(node.get('answer')) is dict
    return False


def validate_snapshot(value):
    F.decode(encoded(value))
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'root', 'objects', 'inventory', 'gaps'}
         and value['schema_version'] == SCHEMA, 'snapshot_contract')
    identity = value['identity']
    need(type(identity) is dict and set(identity) == {'source_origin', 'org_id', 'product', 'version', 'principal_ref',
         'chart_generation', 'reference'} and all(text(identity[k]) for k in
         ('source_origin', 'org_id', 'version', 'principal_ref', 'reference'))
         and identity['product'] in ('cloud', 'software')
         and identity['chart_generation'] in ('classic', 'new', 'mixed', 'unknown'), 'identity_contract')
    origin = urlsplit(identity['source_origin'])
    need(origin.scheme == 'https' and origin.hostname and origin.netloc == origin.hostname
         and not origin.path and not origin.query and not origin.fragment and not origin.username, 'https_origin_required')
    root = value['root']
    need(type(root) is dict and set(root) == {'kind', 'id'} and root['kind'] in ('liveboard', 'answer')
         and text(root['id']), 'root_contract')
    need(type(value['objects']) is list and 1 <= len(value['objects']) <= 1000, 'objects_bound')
    objects = {}
    for row in value['objects']:
        need(type(row) is dict and set(row) == {'kind', 'id', 'payload', 'evidence_ref'}
             and row['kind'] in OBJECT_KINDS and text(row['id']) and text(row['evidence_ref'])
             and type(row['payload']) is dict and row['payload'], 'native_object')
        key, payload = (row['kind'], row['id']), row['payload']
        need(key not in objects, 'duplicate_native_object')
        if row['kind'] != 'unknown':
            need(payload.get('guid') == row['id'] and type(payload.get(row['kind'])) is dict,
                 'native_tml_identity_or_shape')
        objects[key] = row
    need((root['kind'], root['id']) in objects, 'root_definition_missing')
    inventory = value['inventory']
    need(type(inventory) is dict and set(inventory) == {'reference', 'completeness', 'items'}
         and text(inventory['reference']) and inventory['completeness'] in ('partial', 'selected_scope_declared')
         and type(inventory['items']) is list and 1 <= len(inventory['items']) <= 2500, 'independent_inventory')
    indexed, mapped = {}, set()
    for row in inventory['items']:
        need(type(row) is dict and set(row) == {'key', 'kind', 'parent_key', 'native_id', 'definition_id',
             'disposition', 'reference', 'configuration', 'source_mapping'} and text(row['key'])
             and row['key'] not in indexed and row['kind'] in KINDS and text(row['reference'])
             and type(row['configuration']) is dict and row['disposition'] in
             ('include', 'manual_review', 'unsupported', 'out_of_scope'), 'inventory_item')
        need(all(row[k] is None or text(row[k]) for k in ('native_id', 'definition_id', 'parent_key')), 'inventory_identity')
        mapping = row['source_mapping']
        if mapping is not None:
            need(type(mapping) is dict and set(mapping) == {'object_kind', 'object_id', 'pointer'}
                 and (mapping['object_kind'], mapping['object_id']) in objects, 'source_mapping_object')
            node = mapped_node(row, objects)
            need(type(node) is dict, 'source_mapping_object_required')
            locator = (mapping['object_kind'], mapping['object_id'], mapping['pointer'])
            need(locator not in mapped, 'duplicate_source_mapping')
            mapped.add(locator)
            ids = [node[k] for k in ('guid', 'viz_guid', 'visualization_id', 'view_guid', 'id') if k in node]
            if ids and row['native_id'] is not None:
                need(row['native_id'] in [str(v) for v in ids if type(v) in (str, int)], 'native_identity_contradiction')
        if 'result_contract' in row['configuration']:
            result_context(row['configuration']['result_contract'])
        if 'private_view' in row['configuration']:
            need(type(row['configuration']['private_view']) is bool, 'private_view_flag')
        indexed[row['key']] = row
    roots = [r for r in indexed.values() if r['parent_key'] is None]
    need(len(roots) == 1 and roots[0]['kind'] in ('liveboard', 'dashboard', 'answer', 'visual')
         and roots[0]['native_id'] == root['id'] and roots[0]['source_mapping'] is not None
         and roots[0]['source_mapping']['object_kind'] == root['kind']
         and roots[0]['source_mapping']['object_id'] == root['id']
         and roots[0]['source_mapping']['pointer'] in ('', '/' + root['kind']), 'inventory_root_binding')
    for row in indexed.values():
        parent, seen = row['parent_key'], {row['key']}
        while parent is not None:
            need(parent in indexed and parent not in seen, 'inventory_parent_or_cycle')
            seen.add(parent); parent = indexed[parent]['parent_key']
        if row['kind'] == 'placement':
            config = row['configuration']
            need(('visual_key' in config) != ('content_key' in config), 'placement_target_required')
            key = config.get('visual_key', config.get('content_key'))
            need(key in indexed and indexed[key]['kind'] in ('visual', 'answer', 'content', 'note', 'unknown'), 'placement_target')
            original, target = mapped_node(row, objects), mapped_node(indexed[key], objects)
            if type(original) is dict and 'visualization_id' in original and type(target) is dict and 'id' in target:
                need(original['visualization_id'] == target['id'], 'placement_local_visual_identity')
    native = {(r['object']['kind'], r['object']['id'], r['pointer']): r for r in native_members(value)}
    for row in indexed.values():
        mapping = row['source_mapping']
        record = native.get((mapping['object_kind'], mapping['object_id'], mapping['pointer'])) if mapping else None
        if record is not None and record['kind'] == 'visual':
            need(row['kind'] in ('visual', 'answer'), 'native_query_visual_reclassified')
        if record is not None and record['kind'] == 'unknown' and '/visualizations/' in record['pointer']:
            need(row['kind'] not in ('visual', 'answer', 'placement'), 'unknown_or_note_not_query_visual')
    need(type(value['gaps']) is list and len(value['gaps']) <= 1000 and all(text(g) for g in value['gaps']), 'gaps_contract')
    F.secret_check(value)
    return value


def native_members(snapshot):
    """Recognize bounded collection locations; unknown members never disappear."""
    records = []
    # JSON TML is not a complete runtime inventory. Only these declared container
    # paths are interpreted; every original field is still retained verbatim.
    collections = {'visualizations': 'visual', 'filters': 'filter', 'parameter_overrides': 'parameter', 'views': 'view'}
    for obj in snapshot['objects']:
        if obj['kind'] not in ('liveboard', 'answer'):
            continue
        body = obj['payload'][obj['kind']]
        queue = [(body, '/' + obj['kind'], collections)]
        if type(body.get('layout')) is dict:
            queue.append((body['layout'], '/' + obj['kind'] + '/layout', {'tabs': 'tab'}))
        while queue:
            container, prefix, known = queue.pop(0)
            for name, kind in known.items():
                if name not in container:
                    continue
                rows = container[name]
                if type(rows) is not list:
                    records.append({'object': obj, 'pointer': prefix + '/' + name, 'kind': 'unknown', 'payload': rows})
                    continue
                for i, row in enumerate(rows):
                    path = prefix + '/' + name + '/' + str(i)
                    actual = kind if type(row) is dict else 'unknown'
                    if kind == 'visual' and type(row) is dict and type(row.get('answer')) is not dict:
                        actual = 'unknown'
                    if kind == 'view' and type(row) is dict and row.get('is_public') is not True:
                        actual = 'private_view'
                    records.append({'object': obj, 'pointer': path, 'kind': actual, 'payload': row})
                    if type(row) is dict and kind == 'tab':
                        queue.append((row, path, {'tiles': 'placement'}))
    return records


def client_states(node):
    states, stack = [], [('', node)]
    while stack:
        prefix, value = stack.pop()
        if type(value) is dict:
            for key, child in value.items():
                path = prefix + '/' + key.replace('~', '~0').replace('/', '~1')
                if key == 'client_state':
                    states.append({'pointer': path, **client_state(child)})
                elif type(child) in (dict, list):
                    stack.append((path, child))
        elif type(value) is list:
            stack.extend((prefix + '/' + str(i), child) for i, child in enumerate(value))
    return states


def native_dependencies(snapshot):
    """Retain native references as obligations; never resolve by matching names."""
    dependencies = []
    native_kinds = {}
    for obj in snapshot['objects']:
        native_kinds.setdefault(obj['id'], []).append(obj['kind'])
    logical_kinds = {'table', 'worksheet', 'model', 'view'}
    for obj in snapshot['objects']:
        answers = []
        if obj['kind'] == 'answer':
            answers.append(('/answer', obj['payload']['answer']))
        if obj['kind'] == 'liveboard':
            body = obj['payload']['liveboard']
            visuals = body.get('visualizations', [])
            if type(visuals) is list:
                answers.extend(('/liveboard/visualizations/' + str(i) + '/answer', row['answer'])
                               for i, row in enumerate(visuals) if type(row) is dict and type(row.get('answer')) is dict)
            local_ids = {row['id'] for row in visuals if type(row) is dict and text(row.get('id'))} if type(visuals) is list else set()
            filters = body.get('filters', [])
            for i, row in enumerate(filters if type(filters) is list else []):
                excluded = row.get('excluded_visualizations', []) if type(row) is dict else []
                if type(excluded) is list:
                    for target in excluded:
                        dependencies.append({'object_id': obj['id'], 'pointer': '/liveboard/filters/' + str(i),
                            'kind': 'excluded_local_visual', 'target': copy.deepcopy(target),
                            'status': 'declared' if text(target) and target in local_ids else 'unresolved'})
        for path, answer in answers:
            tables = answer.get('tables', [])
            if type(tables) is not list:
                dependencies.append({'object_id': obj['id'], 'pointer': path + '/tables',
                    'kind': 'opaque_model_reference', 'target': copy.deepcopy(tables), 'status': 'unresolved'})
                continue
            for i, table in enumerate(tables):
                target = table.get('id') if type(table) is dict else None
                dependencies.append({'object_id': obj['id'], 'pointer': path + '/tables/' + str(i),
                    'kind': 'logical_data_object', 'target': copy.deepcopy(table),
                    'status': 'declared' if text(target) and len(native_kinds.get(target, [])) == 1
                    and native_kinds[target][0] in logical_kinds else 'unresolved'})
    return dependencies


def parse_snapshot(payload, raw, helpers):
    validate_snapshot(payload)
    result = helpers['base'](payload, raw, 'thoughtspot', 'supplied_thoughtspot_api_snapshot')
    identity, root, objects = payload['identity'], payload['root'], _objects(payload)
    namespace = identity['source_origin'] + '/org/' + identity['org_id'] + '/' + root['kind'] + '/' + root['id']
    fingerprint = sha(payload)
    result['source'].update(source_identity=copy.deepcopy(identity), namespace=namespace,
        root=copy.deepcopy(root), definition_fingerprint=fingerprint)
    result.update(build_authority=False, migration_context={'route': None, 'build_authority': False,
        'target_write_authority': False, 'native_validation': 'not_established', 'business_acceptance': 'not_assessed'})
    indexed = {r['key']: r for r in payload['inventory']['items']}
    represented, object_covered = set(), set()
    for i, row in enumerate(payload['inventory']['items']):
        key, config = row['key'], row['configuration']
        node, mapping = mapped_node(row, objects), row['source_mapping']
        if mapping:
            represented.add((mapping['object_kind'], mapping['object_id'], mapping['pointer']))
            object_covered.add((mapping['object_kind'], mapping['object_id']))
        target = indexed[config.get('visual_key', config.get('content_key'))] if row['kind'] == 'placement' else row
        private_scope = restricted(row, indexed, objects) or restricted(target, indexed, objects)
        query = query_node(target, objects) and not private_scope
        normalized_kind = {'liveboard': 'dashboard', 'answer': 'visual', 'tab': 'page', 'group': 'layout',
                           'note': 'content', 'view': 'layout', 'private_view': 'layout'}.get(row['kind'], row['kind'])
        original = node if node is not None else {}
        state = client_states(original)
        facets = {'visual': {'status': 'declared', 'value': {'configuration': copy.deepcopy(config),
                           'native': copy.deepcopy(original), 'client_state': state}},
            'query': {'status': 'needs_review', 'value': {'definition_id': row['definition_id'],
                        'interpretation': 'inert_search_formula_and_model_evidence_not_SQL'}},
            'layout': {'status': 'declared', 'value': {'parent_key': row['parent_key'], 'configuration': copy.deepcopy(config)}},
            'filters': {'status': 'needs_review', 'value': copy.deepcopy(config)},
            'interactions': {'status': 'needs_review', 'value': copy.deepcopy(original)},
            'content': {'status': 'declared', 'value': copy.deepcopy(original)},
            'security': {'status': 'needs_review', 'value': {'restricted_private_scope': private_scope}}}
        helpers['add_asset'](result, normalized_kind, row, '/inventory/items/' + str(i), key,
            namespace, facets, id_kind='independently_enumerated_source_key',
            source_identity={**copy.deepcopy(identity), 'source_platform': 'thoughtspot', 'root': copy.deepcopy(root),
                'object_key': key, 'native_kind': row['kind'], 'native_id': row['native_id'],
                'definition_id': row['definition_id'], 'source_mapping': copy.deepcopy(mapping),
                'viz_guid': original.get('viz_guid'), 'visualization_id': original.get('id', original.get('visualization_id')),
                'answer_guid': (mapping['object_id'] if mapping and mapping['object_kind'] == 'answer' else None),
                'tab_id': config.get('tab_id'), 'group_id': config.get('group_id'), 'view_id': config.get('view_id'),
                'query_visual': query, 'visual_key': target['key'] if query else None,
                'restricted_private_scope': private_scope, 'declared_disposition': row['disposition'],
                'definition_fingerprint': fingerprint, 'definition_sha256': fingerprint})
        if mapping is None:
            helpers['gap'](result, 'thoughtspot.expected_object_without_original_mapping', '/inventory/items/' + str(i))
        if target['kind'] in ('visual', 'answer') and not query_node(target, objects):
            helpers['gap'](result, 'thoughtspot.query_visual_definition_unqualified', '/inventory/items/' + str(i))
        if row['disposition'] != 'include' or row['kind'] == 'unknown':
            helpers['gap'](result, 'thoughtspot.source_object_disposition_requires_review', '/inventory/items/' + str(i))
        if private_scope:
            helpers['gap'](result, 'thoughtspot.private_view_not_selected_for_target', '/inventory/items/' + str(i))
        if any(s['status'] != 'json_data_only' for s in state):
            helpers['gap'](result, 'thoughtspot.client_state_opaque', '/inventory/items/' + str(i))
        if row['definition_id'] is not None:
            found = [o for o in payload['objects'] if o['id'] == row['definition_id']]
            result['dependencies'].append({'source_key': key, 'target_native_id': row['definition_id'],
                'status': 'declared' if len(found) == 1 else 'unresolved'})
    # Reconcile native lists independently of the caller's selected/mapped set.
    missing = 0
    for record in native_members(payload):
        obj, path = record['object'], record['pointer']
        if (obj['kind'], obj['id'], path) in represented:
            continue
        missing += 1
        helpers['add_asset'](result, 'unknown', {'native_payload': record['payload']},
            '/unmapped/' + obj['kind'] + '/' + obj['id'] + path, None, namespace,
            {'visual': {'status': 'needs_review', 'value': copy.deepcopy(record['payload'])}},
            id_kind='native_locator_unmapped', source_identity={'source_platform': 'thoughtspot',
                'native_kind': record['kind'], 'query_visual': False, 'definition_fingerprint': fingerprint,
                'restricted_private_scope': record['kind'] == 'private_view',
                'source_mapping': {'object_kind': obj['kind'], 'object_id': obj['id'], 'pointer': path}})
        helpers['gap'](result, 'thoughtspot.native_object_omitted_from_independent_inventory', path)
    for i, obj in enumerate(payload['objects']):
        if (obj['kind'], obj['id']) not in object_covered:
            helpers['add_asset'](result, 'definition', obj, '/objects/' + str(i), obj['id'], namespace,
                {'query': {'status': 'needs_review', 'value': copy.deepcopy(obj['payload'])}},
                source_identity={'source_platform': 'thoughtspot', 'native_kind': obj['kind'], 'query_visual': False,
                                 'definition_fingerprint': fingerprint, 'definition_sha256': sha(obj['payload'])})
    result['thoughtspot_coverage'] = {'independently_enumerated': len(indexed), 'native_unmapped': missing,
        'native_definitions': len(objects), 'declared_coverage': payload['inventory']['completeness'],
        'source_export_completeness': 'not_established', 'runtime_coverage': 'not_verified'}
    dependencies = native_dependencies(payload)
    result['dependencies'].extend(dependencies)
    for dependency in dependencies:
        if dependency['status'] == 'unresolved':
            helpers['gap'](result, 'thoughtspot.native_dependency_unresolved', dependency['pointer'])
    for gap in payload['gaps']:
        helpers['gap'](result, 'thoughtspot.supplied_gap', detail=gap)
    for code in ('TML_does_not_establish_visual_completeness', 'R_Python_custom_visuals_require_independent_evidence',
                 'formulas_search_tokens_and_model_semantics_require_review', 'effective_access_unverified',
                 'chart_generation_and_rendered_behavior_unverified', 'pinned_export_identifier_requires_version_contract',
                 'view_export_scope_depends_on_exporting_principal_not_all_visible_views'):
        helpers['gap'](result, 'thoughtspot.' + code)
    return result


def validate_capture(value):
    return module('thoughtspot_capture').validate_envelope(value)


def verify_capture_files(value, root):
    return module('thoughtspot_capture').verify_capture_files(value, root)


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    snapshot = payload['source']['snapshot']
    result = parse_snapshot(snapshot, encoded(snapshot), helpers)
    result['source'].update(helpers['base'](payload, raw, 'thoughtspot', 'supplied_thoughtspot_visual_capture')['source'])
    result['source']['capture_content_hash'] = payload['content_hash']
    need(result['source']['definition_fingerprint'] == payload['source']['definition_fingerprint'], 'capture_definition')
    result['upstream_payload'] = copy.deepcopy(payload)
    request = payload['request']
    result['migration_context'].update(route=None if request['route'] == 'unselected' else request['route'],
        route_reference=request['route_reference'], target_surface=request['target_surface'])
    for gap in payload['gaps']:
        helpers['gap'](result, 'thoughtspot.capture_gap', detail=gap)
    helpers['gap'](result, 'thoughtspot.actual_files_require_verification')
    return result


def case_binding(asset, case, capture):
    validate_capture(capture)
    snapshot, identity = capture['source']['snapshot'], asset.get('source_identity', {})
    need(identity.get('definition_fingerprint') == sha(snapshot) and identity.get('root') == snapshot['root']
         and all(identity.get(k) == snapshot['identity'][k] for k in
                 ('source_origin', 'org_id', 'product', 'version', 'principal_ref', 'chart_generation')), 'case_identity')
    indexed, objects = {r['key']: r for r in snapshot['inventory']['items']}, _objects(snapshot)
    selected = indexed.get(identity.get('object_key'))
    need(selected is not None and selected['disposition'] == 'include' and not restricted(selected, indexed, objects), 'case_scope')
    key = selected['configuration'].get('visual_key', selected['configuration'].get('content_key')) if selected['kind'] == 'placement' else selected['key']
    target = indexed[key]
    need(target['disposition'] == 'include' and not restricted(target, indexed, objects), 'case_target_scope')
    binding = case.get('source_binding')
    need(type(binding) is dict and set(binding) == {'definition_fingerprint', 'state_sha256', 'object_key', 'placement_key', 'attachment_id'}
         and binding['definition_fingerprint'] == sha(snapshot) and binding['state_sha256'] == sha(capture['request']['state'])
         and binding['object_key'] == key and binding['placement_key'] ==
         (selected['key'] if selected['kind'] == 'placement' else None), 'case_binding')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id']
               and a['object_key'] in (selected['key'], key)]
    need(binding['attachment_id'] is None or len(matches) == 1, 'case_attachment')
    if case.get('lane') == 'numeric':
        need(query_node(target, objects) and selected['source_mapping'] is not None
             and target['source_mapping'] is not None
             and len(matches) == 1 and matches[0]['format'] in ('csv', 'json'), 'case_numeric_evidence')
    return binding


def validate_case(value, capture):
    validate_capture(capture)
    binding = value.get('source_binding')
    need(type(binding) is dict and binding.get('definition_fingerprint') == capture['source']['definition_fingerprint']
         and binding.get('state_sha256') == sha(capture['request']['state']), 'case_capture_binding')
    return binding


def compact_projection(raw, profile):
    """Explicit COMPACT matrix -> object rows, preserving original numeric tokens.

    The pointers and column IDs are reviewed inputs, never vendor-shape guesses.
    The derivative is bounded and is not evidence of completeness or freshness.
    """
    keys = {'schema_version', 'format', 'shape', 'rows_pointer', 'headers_pointer', 'header_id_key',
            'column_ids', 'headers', 'columns', 'subtotal_policy'}
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE and type(profile) is dict and set(profile) == keys
         and profile['schema_version'] == 1 and profile['format'] == 'json'
         and profile['shape'] == 'compact_matrix' and profile['subtotal_policy'] == 'preserve', 'compact_profile')
    F.secret_check(F.decode(raw))  # Bounded structure, duplicate keys, non-JSON constants.
    data = json.loads(raw.decode('utf-8-sig'), parse_float=Decimal)
    headers, ids = profile['headers'], profile['column_ids']
    need(type(headers) is list and 1 <= len(headers) <= 512 and all(text(h) for h in headers)
         and len(set(headers)) == len(headers) and type(ids) is list and len(ids) == len(headers)
         and all(text(i) for i in ids) and len(set(ids)) == len(ids), 'compact_column_mapping')
    columns = profile['columns']
    need(type(columns) is list and len(columns) == len(headers) and all(type(c) is dict for c in columns)
         and [c.get('ordinal') for c in columns] == list(range(len(headers)))
         and all(text(c.get('name')) for c in columns) and len({c['name'] for c in columns}) == len(columns),
         'compact_column_types')
    id_key = profile['header_id_key']
    need(id_key is None or text(id_key), 'compact_header_id_key')
    native_headers = pointer(data, profile['headers_pointer'])
    need(type(native_headers) is list and len(native_headers) == len(ids), 'compact_header_count')
    if id_key is None:
        observed_ids = native_headers
    else:
        need(all(type(h) is dict and id_key in h for h in native_headers), 'compact_header_id_missing')
        observed_ids = [h[id_key] for h in native_headers]
    need(all(type(i) is str for i in observed_ids) and observed_ids == ids, 'compact_header_identity_or_order')
    rows = pointer(data, profile['rows_pointer'])
    need(type(rows) is list and len(rows) <= 100000, 'compact_rows_bound')
    # Serialize only the accepted scalar matrix. Decimal is emitted as its exact
    # JSON number rather than a float or an ambiguously formatted string.
    def scalar(value):
        need(type(value) in (str, int, Decimal, bool) or value is None, 'compact_scalar_cell_required')
        if type(value) is Decimal:
            need(value.is_finite(), 'compact_nonfinite_number')
            return str(value).encode('ascii')
        return encoded(value)
    names = [encoded(name) for name in headers]
    output = bytearray(b'[')
    for i, row in enumerate(rows):
        need(type(row) is list and len(row) == len(headers), 'compact_ragged_matrix')
        rendered = b'{' + b','.join(name + b':' + scalar(cell) for name, cell in zip(names, row)) + b'}'
        need(len(output) + len(rendered) + 2 <= F.MAX_FILE, 'compact_projection_byte_limit')
        if i:
            output.extend(b',')
        output.extend(rendered)
    output.extend(b']')
    derivative_profile = {'schema_version': 1, 'format': 'json', 'rows_pointer': '',
        'headers': copy.deepcopy(headers), 'columns': copy.deepcopy(columns), 'subtotal_policy': 'preserve'}
    return bytes(output), derivative_profile


def normalize_results(raw, profile, binding):
    fields = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id', 'state_sha256', 'attachment_sha256'}
    need(type(binding) is dict and set(binding) == fields and binding['attachment_sha256'] == sha(raw)
         and all(digest(binding[k]) for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'))
         and all(text(binding[k]) for k in ('object_key', 'attachment_id')), 'normalization_binding')
    need(type(profile) is dict and profile.get('format') in ('csv', 'json'), 'normalization_profile')
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
              'visual_id': binding['object_key'], 'query_id': binding['attachment_id'],
              'state_sha256': binding['state_sha256'], 'attachment_sha256': binding['attachment_sha256']}
    need('shape' not in profile or profile['format'] == 'json' and profile['shape'] in ('object_rows', 'compact_matrix'),
         'normalization_shape')
    if profile.get('shape') == 'compact_matrix':
        derivative, derivative_profile = compact_projection(raw, profile)
        result = module('powerbi_visual').normalize_results(derivative, derivative_profile,
            {**mapped, 'attachment_sha256': sha(derivative)})
        result['projection'] = {'kind': 'explicit_compact_matrix_to_object_rows', 'sha256': sha(derivative),
                                'bytes': len(derivative)}
    else:
        result = module('powerbi_visual').normalize_results(raw, profile, mapped)
    result.update(kind='thoughtspot_normalized_results', raw_sha256=sha(raw), parser_profile=copy.deepcopy(profile),
                  binding=copy.deepcopy(binding))
    return result


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    gaps = []
    if not case.get('source_capture'):
        gaps.append('source.thoughtspot_case_capture_required')
    if capture.get('status') == 'blocked':
        gaps.append('source.thoughtspot_capture_blocked')
    pin = source.get('raw_file') if source.get('format') == 'thoughtspot-normalized' else source.get('file')
    need(type(pin) is dict, 'comparison_raw_pin')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id']
               and a['format'] in ('csv', 'json') and a['sha256'] == pin.get('sha256')]
    if len(matches) != 1:
        return gaps + ['source.thoughtspot_result_not_bound']
    a = matches[0]
    if a['completeness']['status'] != 'complete' or not a['completeness'].get('reference') or a['completeness'].get('flags'):
        gaps.append('source.thoughtspot_completeness_unverified')
    if a['origin'] == 'unknown' or a['result_scope'] == 'unknown':
        gaps.append('source.thoughtspot_result_origin_unverified')
    state, observed = capture['request']['state'], a.get('observed_state')
    if observed is None:
        gaps.append('source.thoughtspot_observed_state_missing')
    else:
        for key in ('filters', 'parameters', 'timezone', 'locale', 'cache', 'principal'):
            wanted = state.get(key)
            if wanted is None or observed['state'].get(key) != wanted or source['context'].get(key) != wanted:
                gaps.append('source.thoughtspot_observed.' + key)
            if key not in ('principal', 'cache') and target['context'].get(key) != wanted:
                gaps.append('context.' + key)
    if asset['kind'] == 'placement' and not (observed or {}).get('placement_reference'):
        gaps.append('source.thoughtspot_placement_state_unverified')
    indexed = {r['key']: r for r in capture['source']['snapshot']['inventory']['items']}
    contract = indexed[binding['object_key']]['configuration'].get('result_contract')
    actual = (observed or {}).get('result_context')
    if contract is None:
        gaps.append('source.thoughtspot_result_contract_missing')
    if actual is None:
        gaps.append('source.thoughtspot_observed_result_context_missing')
    else:
        result_context(actual)
        for key in ('data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage'):
            if contract is not None and contract[key] != actual[key]:
                gaps.append('source.thoughtspot_requested_result.' + key)
            if source['context'].get(key, '__absent__') != actual[key]:
                gaps.append('source.thoughtspot_observed_result.' + key)
            if target['context'].get(key, '__absent__') != actual[key]:
                gaps.append('context.' + key)
        if actual['data_mode'] in ('test', 'unknown') or actual['row_limit_stage'] == 'unknown' or actual['aggregation_stage'] == 'unknown':
            gaps.append('source.thoughtspot_result_semantics_unqualified')
        if source['context'].get('result_context_reference') != actual['reference']:
            gaps.append('source.thoughtspot_result_context_reference')
        if not text(target['context'].get('result_context_reference')):
            gaps.append('target.thoughtspot_result_context_reference')
        if actual['aggregation_stage'] == 'in_document' and (a['origin'] != 'transformed' or a['result_scope'] != 'transformed'):
            gaps.append('source.thoughtspot_transformed_result_required')
    for key, wanted in {'population': a['population']['key'], 'data_watermark': a['freshness']['data_watermark'],
                        'freshness_reference': a['freshness']['reference'], 'result_scope': a['result_scope']}.items():
        if wanted is None or not a['freshness']['observed_at'] or source['context'].get(key) != wanted:
            gaps.append('source.thoughtspot_context.' + key)
        if key == 'freshness_reference':
            if not text(target['context'].get(key)):
                gaps.append('target.thoughtspot_freshness_reference')
        elif target['context'].get(key) != wanted:
            gaps.append('context.' + key)
    if source.get('format') == 'thoughtspot-normalized':
        expected = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': sha(capture['source']['snapshot']),
            'object_key': binding['object_key'], 'attachment_id': binding['attachment_id'],
            'state_sha256': binding['state_sha256'], 'attachment_sha256': pin['sha256']}
        if type(normalized) is not dict or normalized.get('binding') != expected:
            gaps.append('source.thoughtspot_normalization_binding_mismatch')
        if a.get('parser_profile') is not None and (normalized or {}).get('parser_profile') != a['parser_profile']:
            gaps.append('source.thoughtspot_observed_parser_profile_changed')
        for field in (normalized or {}).get('parser_profile', {}).get('columns', []):
            currency = field.get('currency')
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get('source') == field['name']]
                if len(mapped) != 1 or source['context'].get('currencies', {}).get(field['name']) != currency['code'] or \
                   target['context'].get('currencies', {}).get(mapped[0]['target']) != currency['code']:
                    gaps.append('context.currency.' + field['name'])
    return gaps
