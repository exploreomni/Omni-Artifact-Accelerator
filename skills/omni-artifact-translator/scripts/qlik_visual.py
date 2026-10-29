"""Passive Qlik JSON evidence projection; no source or target execution.

Native QIX/API definitions and independently enumerated scope are distinct evidence. This
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
        raise ValueError('qlik.' + code)


def module(name):
    need(name in ('powerbi_capture_files', 'powerbi_visual', 'qlik_capture'), 'module_rejected')
    path = Path(__file__).with_name(name + '.py')
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
    spec = importlib.util.spec_from_file_location('qlik_visual_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F = module('powerbi_capture_files')
SCHEMA = SNAPSHOT_SCHEMA = 'qlik-api-snapshot.v1'
OBJECT_KINDS = {'app', 'sheet', 'visual', 'dimension', 'measure', 'variable', 'bookmark', 'unknown'}
KINDS = {'app', 'sheet', 'visual', 'placement', 'content', 'control', 'filter', 'parameter',
         'bookmark', 'alternate_state', 'dimension', 'measure', 'master_item', 'layout', 'extension', 'unknown'}


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
            raise ValueError('qlik.json_pointer_missing')
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


def _objects(value):
    return {(r['kind'], r['id']): r for r in value['objects']}


def mapped_node(item, objects):
    m = item['source_mapping']
    return None if m is None else pointer(objects[(m['object_kind'], m['object_id'])]['payload'], m['pointer'])


def native_id(node):
    if type(node) is not dict:
        return None
    info = node.get('qInfo', {})
    return info.get('qId') if type(info) is dict else None


def _private(node):
    if type(node) is not dict:
        return False
    return node.get('private') is True or node.get('published') is False or node.get('approved') is False or \
        any(type(node.get(k)) is dict and (node[k].get('published') is False or node[k].get('approved') is False)
            for k in ('qMeta', 'qMetaDef'))


def restricted(item, indexed, objects):
    """Supplied scope cannot relabel native unpublished/private source as public."""
    seen = set()
    while item is not None:
        need(item['key'] not in seen, 'inventory_cycle')
        seen.add(item['key'])
        m = item['source_mapping']
        original = objects[(m['object_kind'], m['object_id'])]['payload'] if m else None
        private = item['configuration'].get('private') is True or _private(mapped_node(item, objects)) or _private(original)
        if private and not text(item['configuration'].get('selection_reference')):
            return True
        item = indexed.get(item['parent_key'])
    return False


def query_node(item, objects):
    m = item['source_mapping']
    if item['kind'] != 'visual' or m is None or m['object_kind'] != 'visual' or m['pointer'] != '':
        return False
    node = mapped_node(item, objects)
    # A layout alone or an extension name is not a query-definition substitute.
    cube = node.get('qHyperCubeDef') if type(node) is dict else None
    return type(node) is dict and native_id(node) == m['object_id'] and type(cube) is dict and \
        all(type(cube.get(k, [])) is list and all(type(r) is dict for r in cube.get(k, []))
            for k in ('qDimensions', 'qMeasures')) and bool(cube.get('qDimensions') or cube.get('qMeasures'))


def scope_item(snapshot, key):
    validate_snapshot(snapshot)
    indexed, objects = {r['key']: r for r in snapshot['inventory']['items']}, _objects(snapshot)
    need(key in indexed, 'scope_object_missing')
    selected = indexed[key]
    target = indexed[selected['configuration'].get('visual_key', selected['configuration'].get('content_key'))] \
        if selected['kind'] == 'placement' else selected
    return {'item': selected, 'target': target, 'node': mapped_node(target, objects),
        'restricted': restricted(selected, indexed, objects) or restricted(target, indexed, objects),
        'query_visual': query_node(target, objects), 'native_id': target['native_id']}


def original_restricted(snapshot, obj, path=''):
    """Generated obligations retain enclosing privacy without inventing ancestry."""
    indexed, objects = {r['key']: r for r in snapshot['inventory']['items']}, _objects(snapshot)
    ancestors = []
    for item in indexed.values():
        mapping = item['source_mapping']
        if item['parent_key'] is None or mapping and mapping['object_kind'] == obj['kind'] and mapping['object_id'] == obj['id'] \
                and (mapping['pointer'] == path or path.startswith(mapping['pointer'] + '/')):
            ancestors.append(item)
    return _private(obj['payload']) or any(restricted(r, indexed, objects) for r in ancestors)


def validate_snapshot(value):
    F.decode(encoded(value))
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'root', 'objects', 'inventory', 'gaps'}
         and value['schema_version'] == SCHEMA, 'snapshot_contract')
    identity = value['identity']
    keys = {'source_origin', 'tenant_id', 'product', 'version', 'principal_ref', 'engine_version', 'reference'}
    need(type(identity) is dict and set(identity) == keys and all(text(identity[k]) for k in keys)
         and identity['product'] in ('cloud', 'client_managed'), 'identity_contract')
    origin = urlsplit(identity['source_origin'])
    need(origin.scheme == 'https' and origin.hostname and origin.netloc == origin.hostname
         and not origin.path and not origin.query and not origin.fragment and not origin.username, 'https_origin_required')
    root = value['root']
    need(type(root) is dict and set(root) == {'kind', 'id'} and root['kind'] == 'app' and text(root['id']), 'root_contract')
    need(type(value['objects']) is list and 1 <= len(value['objects']) <= 1000, 'objects_bound')
    objects = {}
    for obj in value['objects']:
        need(type(obj) is dict and set(obj) == {'kind', 'id', 'payload', 'evidence_ref'} and obj['kind'] in OBJECT_KINDS
             and text(obj['id']) and text(obj['evidence_ref']) and type(obj['payload']) is dict and obj['payload'], 'native_object')
        key, node = (obj['kind'], obj['id']), obj['payload']
        need(key not in objects, 'duplicate_native_object')
        if obj['kind'] == 'app':
            # Native NxAppLayout uses qFileName for the Enterprise app GUID.
            need(node.get('qFileName') == obj['id'], 'native_app_identity')
        elif obj['kind'] != 'unknown':
            need(native_id(node) == obj['id'] and text(node['qInfo'].get('qType')), 'native_persistent_identity')
        # qHandle is retained as inert session evidence, never used as identity.
        objects[key] = obj
    need(('app', root['id']) in objects, 'root_definition_missing')
    inventory = value['inventory']
    need(type(inventory) is dict and set(inventory) == {'reference', 'completeness', 'items'} and text(inventory['reference'])
         and inventory['completeness'] in ('partial', 'selected_scope_declared') and type(inventory['items']) is list
         and 1 <= len(inventory['items']) <= 2500, 'independent_inventory')
    indexed, mappings = {}, set()
    for item in inventory['items']:
        need(type(item) is dict and set(item) == {'key', 'kind', 'parent_key', 'native_id', 'definition_id', 'disposition',
             'reference', 'configuration', 'source_mapping'} and text(item['key']) and item['key'] not in indexed
             and item['kind'] in KINDS and text(item['reference']) and type(item['configuration']) is dict
             and item['disposition'] in ('include', 'manual_review', 'unsupported', 'out_of_scope'), 'inventory_item')
        need(all(item[k] is None or text(item[k]) for k in ('parent_key', 'native_id', 'definition_id')), 'inventory_identity')
        m = item['source_mapping']
        if m is not None:
            need(type(m) is dict and set(m) == {'object_kind', 'object_id', 'pointer'}
                 and (m['object_kind'], m['object_id']) in objects, 'source_mapping_object')
            node = mapped_node(item, objects)
            need(type(node) is dict, 'source_mapping_object_required')
            locator = (m['object_kind'], m['object_id'], m['pointer'])
            need(locator not in mappings, 'duplicate_source_mapping'); mappings.add(locator)
            expected = node.get('qFileName') if m['object_kind'] == 'app' and m['pointer'] == '' else native_id(node)
            if expected is not None:
                need(item['native_id'] == expected, 'native_identity_contradiction')
            if m['object_kind'] == 'visual' and m['pointer'] == '' and type(node.get('qHyperCubeDef')) is dict:
                need(item['kind'] == 'visual', 'native_query_reclassified')
        if 'result_contract' in item['configuration']:
            result_context(item['configuration']['result_contract'])
        if 'private' in item['configuration']:
            need(type(item['configuration']['private']) is bool, 'private_flag')
        indexed[item['key']] = item
    roots = [r for r in indexed.values() if r['parent_key'] is None]
    need(len(roots) == 1 and roots[0]['kind'] == 'app' and roots[0]['native_id'] == root['id']
         and roots[0]['source_mapping'] == {'object_kind': 'app', 'object_id': root['id'], 'pointer': ''}, 'inventory_root_binding')
    for item in indexed.values():
        parent, seen = item['parent_key'], {item['key']}
        while parent is not None:
            need(parent in indexed and parent not in seen, 'inventory_parent_or_cycle')
            seen.add(parent); parent = indexed[parent]['parent_key']
        if item['kind'] == 'placement':
            config = item['configuration']
            need(('visual_key' in config) != ('content_key' in config), 'placement_target_required')
            key = config.get('visual_key', config.get('content_key'))
            need(key in indexed and indexed[key]['kind'] in ('visual', 'content', 'extension', 'unknown'), 'placement_target')
            node = mapped_node(item, objects)
            if type(node) is dict and 'name' in node and text(node['name']):
                need(node['name'] == indexed[key]['native_id'], 'placement_object_identity')
    need(type(value['gaps']) is list and len(value['gaps']) <= 1000 and all(text(g) for g in value['gaps']), 'gaps_contract')
    F.secret_check(value)
    return value


def native_members(snapshot):
    """Only known QIX collection locations; opaque children remain obligations."""
    records = []
    collections = {'cells': 'placement', 'qItems': 'unknown', 'qChildren': 'unknown',
                   'qDimensions': 'dimension', 'qMeasures': 'measure'}
    for obj in snapshot['objects']:
        pending = [('', obj['payload'])]
        while pending:
            prefix, node = pending.pop()
            if type(node) is not dict:
                continue
            for name, child in node.items():
                path = prefix + '/' + name.replace('~', '~0').replace('/', '~1')
                if name in collections:
                    if type(child) is not list:
                        records.append({'object': obj, 'pointer': path, 'kind': 'unknown', 'payload': child})
                    else:
                        for i, row in enumerate(child):
                            records.append({'object': obj, 'pointer': path + '/' + str(i),
                                'kind': collections[name] if type(row) is dict else 'unknown', 'payload': row})
                elif type(child) is dict:
                    pending.append((path, child))
    return records


def native_dependencies(snapshot):
    records, objects = [], _objects(snapshot)
    for obj in snapshot['objects']:
        pending = [('', obj['payload'])]
        while pending:
            path, node = pending.pop()
            if type(node) is dict:
                if text(node.get('qExtendsId')):
                    target = node['qExtendsId']
                    records.append({'object_id': obj['id'], 'pointer': path + '/qExtendsId', 'kind': 'master_visualization',
                        'target': target, 'expected_kind': 'visual',
                        'status': 'declared' if ('visual', target) in objects else 'unresolved'})
                if text(node.get('qLibraryId')):
                    kind = 'dimension' if '/qDimensions/' in path else 'measure' if '/qMeasures/' in path else None
                    target = node['qLibraryId']
                    records.append({'object_id': obj['id'], 'pointer': path + '/qLibraryId', 'kind': 'master_item',
                        'target': target, 'expected_kind': kind,
                        'status': 'declared' if kind and (kind, target) in objects else 'unresolved'})
                pending.extend((path + '/' + k.replace('~', '~0').replace('/', '~1'), v) for k, v in node.items()
                               if type(v) in (dict, list))
            elif type(node) is list:
                pending.extend((path + '/' + str(i), v) for i, v in enumerate(node))
    return records




def parse_snapshot(payload, raw, helpers):
    validate_snapshot(payload)
    result = helpers['base'](payload, raw, 'qlik', 'supplied_qlik_api_snapshot')
    identity, root, objects = payload['identity'], payload['root'], _objects(payload)
    namespace = identity['source_origin'] + '/tenant/' + identity['tenant_id'] + '/' + root['kind'] + '/' + root['id']
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
        normalized_kind = {'app': 'dashboard', 'sheet': 'page', 'bookmark': 'control', 'alternate_state': 'control',
                           'master_item': 'definition', 'dimension': 'definition', 'measure': 'definition', 'extension': 'unknown'}.get(row['kind'], row['kind'])
        original = node if node is not None else {}
        facets = {'visual': {'status': 'declared', 'value': {'configuration': copy.deepcopy(config),
                           'native': copy.deepcopy(original)}},
            'query': {'status': 'needs_review', 'value': {'definition_id': row['definition_id'],
                        'interpretation': 'inert_Qlik_expression_set_analysis_and_selection_not_SQL'}},
            'layout': {'status': 'declared', 'value': {'parent_key': row['parent_key'], 'configuration': copy.deepcopy(config)}},
            'filters': {'status': 'needs_review', 'value': copy.deepcopy(config)},
            'interactions': {'status': 'needs_review', 'value': copy.deepcopy(original)},
            'content': {'status': 'declared', 'value': copy.deepcopy(original)},
            'security': {'status': 'needs_review', 'value': {'restricted_private_scope': private_scope}}}
        helpers['add_asset'](result, normalized_kind, row, '/inventory/items/' + str(i), key,
            namespace, facets, id_kind='independently_enumerated_source_key',
            source_identity={**copy.deepcopy(identity), 'source_platform': 'qlik', 'root': copy.deepcopy(root),
                'object_key': key, 'native_kind': row['kind'], 'native_id': row['native_id'],
                'definition_id': row['definition_id'], 'source_mapping': copy.deepcopy(mapping),
                'persistent_object_id': native_id(original), 'session_handle_authority': False,
                'query_visual': query, 'visual_key': target['key'] if query else None,
                'restricted_private_scope': private_scope, 'declared_disposition': row['disposition'],
                'definition_fingerprint': fingerprint, 'definition_sha256': fingerprint})
        if mapping is None:
            helpers['gap'](result, 'qlik.expected_object_without_original_mapping', '/inventory/items/' + str(i))
        if target['kind'] == 'visual' and not query_node(target, objects):
            helpers['gap'](result, 'qlik.query_visual_definition_unqualified', '/inventory/items/' + str(i))
        if row['disposition'] != 'include' or row['kind'] == 'unknown':
            helpers['gap'](result, 'qlik.source_object_disposition_requires_review', '/inventory/items/' + str(i))
        if private_scope:
            helpers['gap'](result, 'qlik.private_scope_not_selected_for_target', '/inventory/items/' + str(i))
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
            id_kind='native_locator_unmapped', source_identity={'source_platform': 'qlik',
                'native_kind': record['kind'], 'query_visual': False, 'definition_fingerprint': fingerprint,
                'restricted_private_scope': _private(record['payload']) or original_restricted(payload, obj, path),
                'source_mapping': {'object_kind': obj['kind'], 'object_id': obj['id'], 'pointer': path}})
        helpers['gap'](result, 'qlik.native_object_omitted_from_independent_inventory', path)
    for i, obj in enumerate(payload['objects']):
        if (obj['kind'], obj['id']) not in object_covered:
            helpers['add_asset'](result, 'definition', obj, '/objects/' + str(i), obj['id'], namespace,
                {'query': {'status': 'needs_review', 'value': copy.deepcopy(obj['payload'])}},
                source_identity={'source_platform': 'qlik', 'native_kind': obj['kind'], 'query_visual': False,
                                 'restricted_private_scope': original_restricted(payload, obj),
                                 'definition_fingerprint': fingerprint, 'definition_sha256': sha(obj['payload'])})
    result['qlik_coverage'] = {'independently_enumerated': len(indexed), 'native_unmapped': missing,
        'native_definitions': len(objects), 'declared_coverage': payload['inventory']['completeness'],
        'source_export_completeness': 'not_established', 'runtime_coverage': 'not_verified'}
    dependencies = native_dependencies(payload)
    result['dependencies'].extend(dependencies)
    for dependency in dependencies:
        if dependency['status'] == 'unresolved':
            helpers['gap'](result, 'qlik.native_dependency_unresolved', dependency['pointer'])
    for gap in payload['gaps']:
        helpers['gap'](result, 'qlik.supplied_gap', detail=gap)
    for code in ('independent_enumeration_not_full_tenant_completeness',
                 'expressions_set_analysis_reload_script_and_extensions_inert', 'effective_access_unverified',
                 'rendered_behavior_and_engine_version_unverified', 'no_DMA_producer_contract'):
        helpers['gap'](result, 'qlik.' + code)
    return result


def validate_capture(value):
    return module('qlik_capture').validate_envelope(value)


def verify_capture_files(value, root):
    return module('qlik_capture').verify_capture_files(value, root)


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    snapshot = payload['source']['snapshot']
    result = parse_snapshot(snapshot, encoded(snapshot), helpers)
    result['source'].update(helpers['base'](payload, raw, 'qlik', 'supplied_qlik_visual_capture')['source'])
    result['source']['capture_content_hash'] = payload['content_hash']
    need(result['source']['definition_fingerprint'] == payload['source']['definition_fingerprint'], 'capture_definition')
    result['upstream_payload'] = copy.deepcopy(payload)
    request = payload['request']
    result['migration_context'].update(route=None if request['route'] == 'unselected' else request['route'],
        route_reference=request['route_reference'], target_surface=request['target_surface'])
    for gap in payload['gaps']:
        helpers['gap'](result, 'qlik.capture_gap', detail=gap)
    helpers['gap'](result, 'qlik.actual_files_require_verification')
    return result


def case_binding(asset, case, capture):
    validate_capture(capture)
    snapshot, identity = capture['source']['snapshot'], asset.get('source_identity', {})
    need(identity.get('definition_fingerprint') == sha(snapshot) and identity.get('root') == snapshot['root']
         and all(identity.get(k) == snapshot['identity'][k] for k in
                 ('source_origin', 'tenant_id', 'product', 'version', 'principal_ref', 'engine_version')), 'case_identity')
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


def precise_json(value):
    """Serialize parsed numeric tokens exactly, without binary-float conversion."""
    if type(value) is Decimal:
        need(value.is_finite(), 'nonfinite_number')
        return str(value).encode('ascii')
    if type(value) is list:
        return b'[' + b','.join(precise_json(v) for v in value) + b']'
    if type(value) is dict:
        return b'{' + b','.join(encoded(k) + b':' + precise_json(v) for k, v in sorted(value.items())) + b'}'
    need(type(value) in (str, int, bool) or value is None, 'scalar_required')
    return encoded(value)


def cube_metadata(cube):
    """Pin dimensional order/size independently of result-page bytes."""
    need(type(cube) is dict, 'cube_object')
    return {k: cube.get(k) for k in ('qSize', 'qDimensionInfo', 'qMeasureInfo', 'qNoOfLeftDims',
        'qColumnOrder', 'qMode', 'qEffectiveInterColumnSortOrder')}


def _calculation_ready(node):
    """Check runtime layout status, not static qCalcCondition.qMsg definitions.

    QIX NxLocalizedErrorCode 0 is OK. A nonempty layout qCalcCondMsg is the
    displayed unmet-condition message; rectangle coverage cannot override it.
    Never include source error context or internal server messages in failures.
    """
    error = node.get('qError')
    if error is not None:
        need(type(error) is dict and type(error.get('qErrorCode')) is int, 'qix_error_state_unqualified')
        need(error['qErrorCode'] == 0, 'qix_calculation_error')
    message = node.get('qCalcCondMsg')
    need(message is None or type(message) is str, 'qix_calculation_condition_unqualified')
    need(message is None or message == '', 'qix_calculation_condition_failed')


def _area(value):
    need(type(value) is dict and set(value) == {'qTop', 'qLeft', 'qWidth', 'qHeight'}
         and all(type(v) is int and 0 <= v <= 100000 for v in value.values())
         and value['qWidth'] <= 512 and value['qWidth'] * value['qHeight'] <= 100000, 'area_bound')
    need(value['qWidth'] > 0, 'area_width')
    return value


def _pivot_paths(nodes):
    need(type(nodes) is list, 'pivot_axis_required')
    leaves, pending = [], [(n, [], 0) for n in reversed(nodes)]
    while pending:
        node, parent, depth = pending.pop()
        need(type(node) is dict and depth <= 32 and len(leaves) <= 100000, 'pivot_axis_bound')
        need(type(node.get('qText')) is str and type(node.get('qElemNo')) is int
             and text(node.get('qType')), 'pivot_axis_identity')
        # Partial/collapsed trees cannot silently become a complete dimension path.
        need(not node.get('qCanExpand') and not node.get('qUp') and not node.get('qDown'), 'pivot_axis_partial')
        children = node.get('qSubNodes', [])
        need(type(children) is list, 'pivot_axis_children')
        path = parent + [{k: copy.deepcopy(v) for k, v in node.items() if k != 'qSubNodes'}]
        if children:
            pending.extend((child, path, depth + 1) for child in reversed(children))
        else:
            leaves.append(path)
    return leaves


def qix_projection(raw, profile):
    """Explicit QIX straight/pivot pages to typed rows; never executes expressions.

    Straight pages must cover qSize exactly. Pivot coverage is only the reviewed
    rectangle and axis paths, never a universal full-cube completeness assertion.
    """
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'qix_raw_byte_limit')
    keys = {'schema_version', 'format', 'shape', 'cube_pointer', 'pages_pointer', 'metadata_sha256',
            'expected_area', 'population_key', 'coverage_reference', 'column_bindings', 'headers', 'columns',
            'mappings', 'subtotal_policy'}
    need(type(profile) is dict and set(profile) == keys and profile['schema_version'] == 1
         and profile['format'] == 'json' and profile['shape'] in ('qlik_straight', 'qlik_pivot')
         and profile['subtotal_policy'] == 'preserve' and digest(profile['metadata_sha256'])
         and text(profile['population_key']) and text(profile['coverage_reference']), 'qix_profile')
    checked = F.decode(raw); F.secret_check(checked)
    data = json.loads(raw.decode('utf-8-sig'), parse_float=Decimal)
    cube = pointer(data, profile['cube_pointer'])
    need(sha(cube_metadata(pointer(checked, profile['cube_pointer']))) == profile['metadata_sha256'], 'qix_metadata_changed')
    expected, pages = _area(profile['expected_area']), pointer(data, profile['pages_pointer'])
    need(type(pages) is list and len(pages) <= 1000, 'qix_pages_bound')
    pivot = profile['shape'] == 'qlik_pivot'
    need(type(cube.get('qDimensionInfo')) is list and type(cube.get('qMeasureInfo')) is list
         and all(type(r) is dict for r in cube['qDimensionInfo'] + cube['qMeasureInfo']), 'qix_column_metadata')
    info = cube['qDimensionInfo'] + cube['qMeasureInfo']
    for node in [cube] + info:
        _calculation_ready(node)
    bindings = profile['column_bindings']
    need(type(bindings) is list and len(bindings) == len(info), 'qix_column_bindings')
    checked_info = pointer(checked, profile['cube_pointer'])['qDimensionInfo'] + pointer(checked, profile['cube_pointer'])['qMeasureInfo']
    for i, binding in enumerate(bindings):
        kind = 'dimension' if i < len(cube['qDimensionInfo']) else 'measure'
        need(type(binding) is dict and set(binding) == {'source_index', 'kind', 'metadata_sha256'}
             and binding['source_index'] == i and binding['kind'] == kind
             and binding['metadata_sha256'] == sha(checked_info[i]), 'qix_column_identity_or_order')
    if not pivot:
        size = cube.get('qSize')
        need(type(size) is dict and set(size) == {'qcx', 'qcy'}
             and all(type(v) is int and v >= 0 for v in size.values())
             and expected == {'qTop': 0, 'qLeft': 0, 'qWidth': size['qcx'], 'qHeight': size['qcy']}
             and size['qcx'] == len(info), 'straight_full_size_required')
        need(cube.get('qMode') == 'S', 'straight_mode')
    else:
        need(cube.get('qMode') == 'P' and type(cube.get('qNoOfLeftDims')) is int
             and 0 <= cube['qNoOfLeftDims'] <= len(info), 'pivot_mode_or_left_dimensions')
    headers, columns, mappings = profile['headers'], profile['columns'], profile['mappings']
    need(type(headers) is list and 1 <= len(headers) <= 512 and all(text(h) for h in headers)
         and len(set(headers)) == len(headers) and type(columns) is list and len(columns) == len(headers)
         and all(type(c) is dict for c in columns) and [c.get('ordinal') for c in columns] == list(range(len(columns)))
         and type(mappings) is list and len(mappings) == len(headers), 'qix_output_columns')
    components = {'text', 'number', 'element_number', 'selection_state', 'is_null', 'cell_type'}
    for mapping in mappings:
        need(type(mapping) is dict and set(mapping) == {'source_column', 'component'}, 'qix_mapping')
        if pivot:
            need(mapping['source_column'] is None and mapping['component'] in components | {'row_index', 'column_index', 'left_path', 'top_path'}, 'pivot_mapping')
        else:
            need(type(mapping['source_column']) is int and 0 <= mapping['source_column'] < expected['qWidth']
                 and mapping['component'] in components, 'straight_mapping')
    need(len({(m['source_column'], m['component']) for m in mappings}) == len(mappings), 'duplicate_component_mapping')
    if pivot:
        need({'row_index', 'column_index', 'left_path', 'top_path'} <= {m['component'] for m in mappings}, 'pivot_coordinates_required')
    cells, left_paths, top_paths, native = {}, {}, {}, []
    for page in pages:
        need(type(page) is dict and 'qArea' in page, 'qix_page')
        area = _area(page['qArea'])
        need(area['qHeight'] * area['qWidth'] <= 10000, 'qix_page_cell_limit')
        need(area['qTop'] >= expected['qTop'] and area['qLeft'] >= expected['qLeft']
             and area['qTop'] + area['qHeight'] <= expected['qTop'] + expected['qHeight']
             and area['qLeft'] + area['qWidth'] <= expected['qLeft'] + expected['qWidth'], 'qix_page_outside_rectangle')
        matrix = page.get('qData' if pivot else 'qMatrix')
        need(type(matrix) is list and len(matrix) == area['qHeight']
             and all(type(row) is list and len(row) == area['qWidth'] for row in matrix), 'qix_ragged_matrix')
        if pivot:
            left, top = _pivot_paths(page.get('qLeft')), _pivot_paths(page.get('qTop'))
            need(len(left) == area['qHeight'] and len(top) == area['qWidth'], 'pivot_axis_coverage')
            for destination, paths, start in ((left_paths, left, area['qTop']), (top_paths, top, area['qLeft'])):
                for i, path in enumerate(paths):
                    need(start + i not in destination or destination[start + i] == path, 'pivot_axis_contradiction')
                    destination[start + i] = path
        for r, row in enumerate(matrix):
            for c, cell in enumerate(row):
                key = (area['qTop'] + r, area['qLeft'] + c)
                need(key not in cells and type(cell) is dict, 'qix_duplicate_or_invalid_cell')
                need(type(cell.get('qText')) is str, 'qix_cell_display_required')
                number = cell.get('qNum')
                need(number is None or type(number) in (int, Decimal) or number == 'NaN', 'qix_numeric_token')
                if 'qIsNull' in cell:
                    need(type(cell['qIsNull']) is bool, 'qix_null_flag')
                for elem in ('qElemNumber', 'qElemNo'):
                    need(elem not in cell or type(cell[elem]) is int, 'qix_element_identity')
                need('qElemNumber' not in cell or 'qElemNo' not in cell or cell['qElemNumber'] == cell['qElemNo'],
                     'qix_element_identity_conflict')
                need('qState' not in cell or type(cell['qState']) is str, 'qix_selection_state')
                cells[key] = cell
                native.append({'row': key[0], 'column': key[1], 'cell_json': precise_json(cell).decode()})
    need(len(cells) == expected['qHeight'] * expected['qWidth'], 'qix_incomplete_rectangle')
    def component(cell, name):
        null = cell.get('qIsNull') is True or cell.get('qElemNumber') == -2 or cell.get('qElemNo') == -2
        if name == 'number':
            return None if null or cell.get('qNum') == 'NaN' else cell.get('qNum')
        if name == 'is_null':
            return null
        if name == 'element_number':
            return cell.get('qElemNumber', cell.get('qElemNo'))
        return cell.get({'text': 'qText', 'element_number': 'qElemNumber', 'selection_state': 'qState', 'cell_type': 'qType'}[name])
    rows = []
    for r in range(expected['qTop'], expected['qTop'] + expected['qHeight']):
        indices = range(expected['qLeft'], expected['qLeft'] + expected['qWidth']) if pivot else [None]
        for c in indices:
            values = []
            for m in mappings:
                name = m['component']
                if pivot and name in ('row_index', 'column_index', 'left_path', 'top_path'):
                    value = r if name == 'row_index' else c if name == 'column_index' else \
                        precise_json(left_paths[r] if name == 'left_path' else top_paths[c]).decode()
                else:
                    value = component(cells[(r, c if pivot else m['source_column'])], name)
                values.append(value)
            rows.append(dict(zip(headers, values)))
    derivative = precise_json(rows)
    need(len(derivative) <= F.MAX_FILE, 'qix_projection_byte_limit')
    derivative_profile = {'schema_version': 1, 'format': 'json', 'rows_pointer': '', 'headers': copy.deepcopy(headers),
        'columns': copy.deepcopy(columns), 'subtotal_policy': 'preserve'}
    evidence = {'kind': 'explicit_qix_pages_to_object_rows', 'sha256': sha(derivative), 'bytes': len(derivative),
        'coverage': 'selected_rectangle' if pivot else 'straight_qSize', 'area': copy.deepcopy(expected),
        'population_key': profile['population_key'], 'coverage_reference': profile['coverage_reference'],
        'full_cube_completeness': 'not_established' if pivot else 'coordinates_verified_not_population_freshness',
        'native_cells': native, 'native_totals_json': precise_json(cube.get('qGrandTotalRow')).decode(),
        'native_axis_json': precise_json({'left': left_paths, 'top': top_paths}).decode() if not pivot else
            precise_json({'left': {str(k): v for k, v in left_paths.items()}, 'top': {str(k): v for k, v in top_paths.items()}}).decode()}
    return derivative, derivative_profile, evidence


def normalize_results(raw, profile, binding):
    fields = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id', 'state_sha256', 'attachment_sha256'}
    need(type(binding) is dict and set(binding) == fields and binding['attachment_sha256'] == sha(raw)
         and all(digest(binding[k]) for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'))
         and all(text(binding[k]) for k in ('object_key', 'attachment_id')), 'normalization_binding')
    need(type(profile) is dict and profile.get('format') in ('csv', 'json'), 'normalization_profile')
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
        'visual_id': binding['object_key'], 'query_id': binding['attachment_id'], 'state_sha256': binding['state_sha256'],
        'attachment_sha256': binding['attachment_sha256']}
    need('shape' not in profile or profile['format'] == 'json' and profile['shape'] in ('object_rows', 'qlik_straight', 'qlik_pivot'), 'normalization_shape')
    if profile.get('shape') in ('qlik_straight', 'qlik_pivot'):
        derivative, derivative_profile, evidence = qix_projection(raw, profile)
        result = module('powerbi_visual').normalize_results(derivative, derivative_profile, {**mapped, 'attachment_sha256': sha(derivative)})
        result['projection'] = evidence
    else:
        result = module('powerbi_visual').normalize_results(raw, profile, mapped)
    result.update(kind='qlik_normalized_results', raw_sha256=sha(raw), parser_profile=copy.deepcopy(profile), binding=copy.deepcopy(binding))
    return result




def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    gaps = []
    if not case.get('source_capture'):
        gaps.append('source.qlik_case_capture_required')
    if capture.get('status') == 'blocked':
        gaps.append('source.qlik_capture_blocked')
    pin = source.get('raw_file') if source.get('format') == 'qlik-normalized' else source.get('file')
    need(type(pin) is dict, 'comparison_raw_pin')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id']
               and a['format'] in ('csv', 'json') and a['sha256'] == pin.get('sha256')]
    if len(matches) != 1:
        return gaps + ['source.qlik_result_not_bound']
    a = matches[0]
    if a['completeness']['status'] != 'complete' or not a['completeness'].get('reference') or a['completeness'].get('flags'):
        gaps.append('source.qlik_completeness_unverified')
    if a['origin'] == 'unknown' or a['result_scope'] == 'unknown':
        gaps.append('source.qlik_result_origin_unverified')
    state, observed = capture['request']['state'], a.get('observed_state')
    if observed is None:
        gaps.append('source.qlik_observed_state_missing')
    else:
        for key in ('filters', 'parameters', 'timezone', 'locale', 'cache', 'principal'):
            wanted = state.get(key)
            if wanted is None or observed['state'].get(key) != wanted or source['context'].get(key) != wanted:
                gaps.append('source.qlik_observed.' + key)
            if key not in ('principal', 'cache') and target['context'].get(key) != wanted:
                gaps.append('context.' + key)
    if asset['kind'] == 'placement' and not (observed or {}).get('placement_reference'):
        gaps.append('source.qlik_placement_state_unverified')
    indexed = {r['key']: r for r in capture['source']['snapshot']['inventory']['items']}
    contract = indexed[binding['object_key']]['configuration'].get('result_contract')
    actual = (observed or {}).get('result_context')
    if contract is None:
        gaps.append('source.qlik_result_contract_missing')
    if actual is None:
        gaps.append('source.qlik_observed_result_context_missing')
    else:
        result_context(actual)
        for key in ('data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage'):
            if contract is not None and contract[key] != actual[key]:
                gaps.append('source.qlik_requested_result.' + key)
            if source['context'].get(key, '__absent__') != actual[key]:
                gaps.append('source.qlik_observed_result.' + key)
            if target['context'].get(key, '__absent__') != actual[key]:
                gaps.append('context.' + key)
        if actual['data_mode'] in ('test', 'unknown') or actual['row_limit_stage'] == 'unknown' or actual['aggregation_stage'] == 'unknown':
            gaps.append('source.qlik_result_semantics_unqualified')
        if source['context'].get('result_context_reference') != actual['reference']:
            gaps.append('source.qlik_result_context_reference')
        if not text(target['context'].get('result_context_reference')):
            gaps.append('target.qlik_result_context_reference')
        if actual['aggregation_stage'] == 'in_document' and (a['origin'] != 'transformed' or a['result_scope'] != 'transformed'):
            gaps.append('source.qlik_transformed_result_required')
    for key, wanted in {'population': a['population']['key'], 'data_watermark': a['freshness']['data_watermark'],
                        'freshness_reference': a['freshness']['reference'], 'result_scope': a['result_scope']}.items():
        if wanted is None or not a['freshness']['observed_at'] or source['context'].get(key) != wanted:
            gaps.append('source.qlik_context.' + key)
        if key == 'freshness_reference':
            if not text(target['context'].get(key)):
                gaps.append('target.qlik_freshness_reference')
        elif target['context'].get(key) != wanted:
            gaps.append('context.' + key)
    if source.get('format') == 'qlik-normalized':
        expected = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': sha(capture['source']['snapshot']),
            'object_key': binding['object_key'], 'attachment_id': binding['attachment_id'],
            'state_sha256': binding['state_sha256'], 'attachment_sha256': pin['sha256']}
        if type(normalized) is not dict or normalized.get('binding') != expected:
            gaps.append('source.qlik_normalization_binding_mismatch')
        if a.get('parser_profile') is not None and (normalized or {}).get('parser_profile') != a['parser_profile']:
            gaps.append('source.qlik_observed_parser_profile_changed')
        for field in (normalized or {}).get('parser_profile', {}).get('columns', []):
            currency = field.get('currency')
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get('source') == field['name']]
                if len(mapped) != 1 or source['context'].get('currencies', {}).get(field['name']) != currency['code'] or \
                   target['context'].get('currencies', {}).get(mapped[0]['target']) != currency['code']:
                    gaps.append('context.currency.' + field['name'])
    profile = a.get('parser_profile') or {}
    if profile.get('shape') in ('qlik_straight', 'qlik_pivot'):
        if source.get('format') != 'qlik-normalized' or normalized is None:
            gaps.append('source.qlik_typed_qix_normalization_required')
        if profile.get('population_key') != a['population']['key']:
            gaps.append('source.qlik_rectangle_population_mismatch')
        if profile.get('shape') == 'qlik_pivot' and (actual or {}).get('data_mode') == 'full_data':
            gaps.append('source.qlik_pivot_full_cube_scope_unverified')
    return gaps
