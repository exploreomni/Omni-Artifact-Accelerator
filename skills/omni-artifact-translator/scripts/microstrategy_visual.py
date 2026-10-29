"""Passive MicroStrategy JSON evidence projection; no source or target execution.

Native REST/API definitions and independently enumerated scope are distinct evidence. This
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
        raise ValueError('microstrategy.' + code)


def module(name):
    need(name in ('powerbi_capture_files', 'powerbi_visual', 'microstrategy_capture'), 'module_rejected')
    path = Path(__file__).with_name(name + '.py')
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
    spec = importlib.util.spec_from_file_location('microstrategy_visual_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F = module('powerbi_capture_files')
SCHEMA = SNAPSHOT_SCHEMA = 'microstrategy-api-snapshot.v1'
OBJECT_KINDS = {'dossier', 'report', 'document', 'cube', 'visualization', 'metric', 'attribute', 'filter', 'prompt', 'unknown'}
ROOT_KINDS = {'dossier', 'report', 'document', 'cube'}
KINDS = ROOT_KINDS | {'chapter', 'page', 'visual', 'placement', 'content', 'control', 'selector', 'prompt',
                     'filter', 'metric', 'attribute', 'dependency', 'unknown'}
IDENTITY_KEYS = {'source_origin', 'context_path', 'project_id', 'principal_ref', 'library_version',
                 'intelligence_server_version', 'model_generation', 'delivery_context', 'reference'}


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
            raise ValueError('microstrategy.json_pointer_missing')
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


def guid(value):
    return type(value) is str and re.fullmatch('[A-Fa-f0-9]{32}', value) is not None


def validate_state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'timezone', 'locale', 'principal', 'cache', 'reference'}, 'state_contract')
    need(type(value['filters']) is dict and set(value['filters']) == {'report', 'chapter', 'view', 'metric_limit'}
         and all(type(v) is list and len(v) <= 100 for v in value['filters'].values()), 'filter_stages_required')
    need(type(value['parameters']) is dict and set(value['parameters']) == {'prompts'}
         and type(value['parameters']['prompts']) is list and len(value['parameters']['prompts']) <= 100, 'prompt_state')
    seen = set()
    for row in value['parameters']['prompts']:
        need(type(row) is dict and set(row) == {'key', 'id', 'answer_mode', 'value'} and text(row['key'])
             and row['key'] not in seen and guid(row['id'])
             and row['answer_mode'] in ('explicit', 'default', 'empty', 'all', 'omitted', 'unresolved'), 'prompt_answer')
        seen.add(row['key'])  # IDs may repeat; the prompt key identifies an occurrence.
        if row['answer_mode'] in ('empty', 'omitted', 'unresolved'):
            need(row['value'] is None, 'prompt_mode_value')
    need(all(value[k] is None or text(value[k]) for k in ('timezone', 'locale', 'principal', 'cache'))
         and text(value['reference']), 'state_metadata')
    F.decode(encoded(value)); F.secret_check(value)
    return value


def _objects(value):
    return {(r['kind'], r['id']): r for r in value['objects']}


def mapped_node(item, objects):
    mapping = item['source_mapping']
    return None if mapping is None else pointer(objects[(mapping['object_kind'], mapping['object_id'])]['payload'], mapping['pointer'])


def native_object_id(node):
    if type(node) is not dict:
        return None
    info = node.get('information', {})
    need(type(info) is dict, 'native_information')
    ids = [v for v in (node.get('id'), node.get('objectId'), info.get('objectId')) if v is not None]
    need(not ids or all(v == ids[0] for v in ids), 'native_identity_contradiction')
    versions = [v for v in (node.get('versionId'), info.get('versionId')) if v is not None]
    need(not versions or all(text(v) and v == versions[0] for v in versions), 'native_version_contradiction')
    return ids[0] if ids else None


def native_id(node):
    # Prompt/visual occurrence keys are not the shared object GUID.
    return node['key'] if type(node) is dict and 'key' in node else native_object_id(node)


def _private(node):
    return type(node) is dict and (node.get('private') is True or node.get('isPrivate') is True)


def restricted(item, indexed, objects):
    seen = set()
    while item is not None:
        need(item['key'] not in seen, 'inventory_cycle'); seen.add(item['key'])
        mapping = item['source_mapping']
        original = objects[(mapping['object_kind'], mapping['object_id'])]['payload'] if mapping else None
        original_selected = mapping and any(r['source_mapping'] == {**mapping, 'pointer': ''}
            and text(r['configuration'].get('selection_reference')) for r in indexed.values())
        if ((_private(original) and not original_selected) or _private(mapped_node(item, objects)) or item['configuration'].get('private') is True) \
                and not text(item['configuration'].get('selection_reference')):
            return True
        item = indexed.get(item['parent_key'])
    return False


def _definition(node):
    if type(node) is not dict:
        return None
    result = node.get('result')
    return result.get('definition') if type(result) is dict else node.get('definition', node.get('units'))


def query_node(item, objects):
    mapping = item['source_mapping']
    if mapping is None or item['kind'] not in ('visual', 'report', 'cube'):
        return False
    if mapping['object_kind'] not in ('dossier', 'visualization', 'report', 'cube'):
        return False
    node = mapped_node(item, objects)
    # Modeling report definitions have information/grid/dataSource, not a
    # fabricated JSON Data definition. This identifies query obligations only;
    # result definition, instance, state and coverage are qualified separately.
    if mapping['object_kind'] == 'report' and type(node) is dict:
        info, grid, source = node.get('information'), node.get('grid'), node.get('dataSource')
        if type(info) is dict and info.get('subType') == 'report_grid' and type(grid) is dict and type(source) is dict:
            template = grid.get('viewTemplate', {})
            templates = [source.get('dataTemplate')]
            if type(template) is dict:
                templates.extend(template.get(k) for k in ('rows', 'columns'))
            for section in templates:
                if type(section) is not dict or type(section.get('units')) is not list:
                    continue
                for unit in section['units']:
                    if type(unit) is not dict:
                        continue
                    if unit.get('type') == 'attribute' and guid(unit.get('id')):
                        return True
                    if unit.get('type') == 'metrics' and type(unit.get('elements')) is list and unit['elements'] \
                            and all(type(m) is dict and guid(m.get('id')) for m in unit['elements']):
                        return True
    definition = _definition(node)
    return type(definition) is dict and type(definition.get('attributes')) is list \
        and type(definition.get('metrics')) is list and bool(definition['metrics']) \
        and all(type(r) is dict and guid(r.get('id')) for r in definition['attributes'] + definition['metrics'])


def scope_item(snapshot, key):
    validate_snapshot(snapshot)
    indexed, objects = {r['key']: r for r in snapshot['inventory']['items']}, _objects(snapshot)
    return _scope_item(snapshot, key, indexed, objects)


def _scope_item(snapshot, key, indexed, objects):
    need(key in indexed, 'scope_object_missing')
    selected = indexed[key]
    target = indexed[selected['configuration'].get('visual_key', selected['configuration'].get('content_key'))] \
        if selected['kind'] == 'placement' else selected
    query = query_node(target, objects)
    if selected['kind'] == 'placement':
        query = query and selected['source_mapping'] is not None \
            and native_id(mapped_node(selected, objects)) == native_id(mapped_node(target, objects))
    return {'item': selected, 'target': target, 'node': mapped_node(target, objects),
            'restricted': restricted(selected, indexed, objects) or restricted(target, indexed, objects),
            'query_visual': query, 'native_id': target['native_id']}


def validate_snapshot(value):
    F.decode(encoded(value)); F.secret_check(value)
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'root', 'objects', 'inventory', 'gaps'}
         and value['schema_version'] == SCHEMA, 'snapshot_contract')
    identity = value['identity']
    need(type(identity) is dict and set(identity) == IDENTITY_KEYS and all(text(identity[k]) for k in IDENTITY_KEYS)
         and guid(identity['project_id']) and identity['model_generation'] in ('classic', 'mosaic')
         and identity['delivery_context'] in ('library', 'embedded'), 'identity_contract')
    origin = urlsplit(identity['source_origin'])
    need(origin.scheme == 'https' and origin.hostname and origin.netloc == origin.hostname and not origin.path
         and not origin.query and not origin.fragment and not origin.username, 'https_origin_required')
    context = identity['context_path']
    need(re.fullmatch(r'/[A-Za-z][A-Za-z0-9_-]{0,99}', context) is not None, 'library_context_path')
    root = value['root']
    need(type(root) is dict and set(root) == {'kind', 'id'} and root['kind'] in ROOT_KINDS and guid(root['id']), 'root_contract')
    need(type(value['objects']) is list and 1 <= len(value['objects']) <= 1000, 'objects_bound')
    objects = {}
    for obj in value['objects']:
        need(type(obj) is dict and set(obj) == {'kind', 'id', 'payload', 'evidence_ref'} and obj['kind'] in OBJECT_KINDS
             and text(obj['id']) and text(obj['evidence_ref']) and type(obj['payload']) is dict and obj['payload'], 'native_object')
        key, node = (obj['kind'], obj['id']), obj['payload']
        need(key not in objects, 'duplicate_native_object')
        if obj['kind'] != 'unknown':
            field = 'key' if obj['kind'] in ('prompt', 'visualization') else 'id'
            need((node.get('key') if field == 'key' else native_object_id(node)) == obj['id'], 'native_object_identity')
            if field == 'id':
                need(guid(obj['id']), 'native_guid')
        objects[key] = obj
    need((root['kind'], root['id']) in objects, 'root_definition_missing')
    inventory = value['inventory']
    need(type(inventory) is dict and set(inventory) == {'reference', 'completeness', 'items'} and text(inventory['reference'])
         and inventory['completeness'] in ('partial', 'selected_scope_declared') and type(inventory['items']) is list
         and 1 <= len(inventory['items']) <= 2500, 'independent_inventory')
    indexed, mappings = {}, set()
    for row in inventory['items']:
        need(type(row) is dict and set(row) == {'key', 'kind', 'parent_key', 'native_id', 'definition_id', 'disposition',
             'reference', 'configuration', 'source_mapping'} and text(row['key']) and row['key'] not in indexed
             and row['kind'] in KINDS and text(row['reference']) and type(row['configuration']) is dict
             and row['disposition'] in ('include', 'manual_review', 'unsupported', 'unavailable', 'out_of_scope'), 'inventory_item')
        need(all(row[k] is None or text(row[k]) for k in ('parent_key', 'native_id', 'definition_id')), 'inventory_identity')
        mapping = row['source_mapping']
        if mapping is not None:
            need(type(mapping) is dict and set(mapping) == {'object_kind', 'object_id', 'pointer'}
                 and (mapping['object_kind'], mapping['object_id']) in objects, 'source_mapping_object')
            node = mapped_node(row, objects)
            need(type(node) is dict, 'source_mapping_object_required')
            locator = (mapping['object_kind'], mapping['object_id'], mapping['pointer'])
            need(locator not in mappings, 'duplicate_source_mapping'); mappings.add(locator)
            if native_id(node) is not None:
                need(row['native_id'] == native_id(node), 'native_identity_contradiction')
        if 'result_contract' in row['configuration']:
            result_context(row['configuration']['result_contract'])
        if 'private' in row['configuration']:
            need(type(row['configuration']['private']) is bool, 'private_flag')
        indexed[row['key']] = row
    roots = [r for r in indexed.values() if r['parent_key'] is None]
    need(len(roots) == 1 and roots[0]['kind'] == root['kind'] and roots[0]['native_id'] == root['id']
         and roots[0]['source_mapping'] == {'object_kind': root['kind'], 'object_id': root['id'], 'pointer': ''}, 'inventory_root_binding')
    for row in indexed.values():
        parent, seen = row['parent_key'], {row['key']}
        while parent is not None:
            need(parent in indexed and parent not in seen, 'inventory_parent_or_cycle'); seen.add(parent)
            parent = indexed[parent]['parent_key']
        if row['kind'] == 'placement':
            config = row['configuration']
            need(('visual_key' in config) != ('content_key' in config), 'placement_target_required')
            target = config.get('visual_key', config.get('content_key'))
            need(target in indexed and indexed[target]['kind'] in ('visual', 'report', 'cube', 'content', 'unknown'), 'placement_target')
    need(type(value['gaps']) is list and len(value['gaps']) <= 1000 and all(text(g) for g in value['gaps']), 'gaps_contract')
    return value


def native_members(snapshot):
    collections = {'chapters': 'chapter', 'pages': 'page', 'visualizations': 'visual', 'selectors': 'selector',
                   'prompts': 'prompt', 'filters': 'filter', 'attributes': 'attribute', 'metrics': 'metric',
                   'datasets': 'dependency', 'panels': 'unknown', 'panelStacks': 'unknown'}
    records = []
    for obj in snapshot['objects']:
        pending = [('', obj['payload'])]
        while pending:
            path, node = pending.pop()
            if type(node) is dict:
                # Modeling templates/expression trees use native object
                # references, not JSON Data attributes/metrics arrays.
                kind = node.get('subType', node.get('type'))
                if path and kind in ('metric', 'attribute', 'filter') and guid(native_object_id(node)):
                    records.append({'object': obj, 'pointer': path, 'kind': kind, 'payload': node})
                for name, child in node.items():
                    where = path + '/' + name.replace('~', '~0').replace('/', '~1')
                    if name in collections and type(child) is list:
                        for i, member in enumerate(child):
                            records.append({'object': obj, 'pointer': where + '/' + str(i),
                                            'kind': collections[name], 'payload': member})
                    if type(child) in (dict, list):
                        pending.append((where, child))
            elif type(node) is list:
                pending.extend((path + '/' + str(i), member) for i, member in enumerate(node))
    return list({(r['object']['kind'], r['object']['id'], r['pointer']): r for r in records}.values())


def parse_snapshot(payload, raw, helpers):
    validate_snapshot(payload)
    result = helpers['base'](payload, raw, 'microstrategy', 'supplied_microstrategy_api_snapshot')
    identity, root, objects = payload['identity'], payload['root'], _objects(payload)
    namespace = identity['source_origin'] + identity['context_path'] + '/project/' + identity['project_id'] + '/' + root['kind'] + '/' + root['id']
    fingerprint = sha(payload)
    result['source'].update(source_identity=copy.deepcopy(identity), namespace=namespace, root=copy.deepcopy(root), definition_fingerprint=fingerprint)
    result.update(build_authority=False, migration_context={'route': None, 'build_authority': False, 'target_write_authority': False,
                  'native_validation': 'not_established', 'business_acceptance': 'not_assessed'})
    indexed = {r['key']: r for r in payload['inventory']['items']}
    represented, covered = set(), set()
    for i, row in enumerate(payload['inventory']['items']):
        config, mapping = row['configuration'], row['source_mapping']
        node = mapped_node(row, objects)
        if mapping:
            represented.add((mapping['object_kind'], mapping['object_id'], mapping['pointer']))
            covered.add((mapping['object_kind'], mapping['object_id']))
        scope = _scope_item(payload, row['key'], indexed, objects)
        query = scope['query_visual'] and not scope['restricted'] and row['disposition'] == 'include'
        kind = {'dossier': 'dashboard', 'document': 'dashboard', 'report': 'visual', 'cube': 'definition', 'chapter': 'page',
                'selector': 'control', 'prompt': 'control', 'metric': 'definition', 'attribute': 'definition', 'dependency': 'definition'}.get(row['kind'], row['kind'])
        facets = {'visual': {'status': 'declared', 'value': {'configuration': copy.deepcopy(config), 'native': copy.deepcopy(node)}},
            'query': {'status': 'needs_review', 'value': {'native': copy.deepcopy(node), 'interpretation': 'inert_metrics_attributes_forms_and_expressions_not_SQL'}},
            'layout': {'status': 'declared', 'value': {'parent_key': row['parent_key'], 'configuration': copy.deepcopy(config)}},
            'filters': {'status': 'needs_review', 'value': {'native': copy.deepcopy(node), 'configuration': copy.deepcopy(config),
                'stages': ['report', 'chapter', 'view', 'metric_limit']}},
            'interactions': {'status': 'needs_review', 'value': copy.deepcopy(node)},
            'security': {'status': 'needs_review', 'value': {'restricted_private_scope': scope['restricted']}}}
        helpers['add_asset'](result, kind, row, '/inventory/items/' + str(i), row['key'], namespace, facets,
            id_kind='independently_enumerated_source_key', source_identity={**copy.deepcopy(identity), 'source_platform': 'microstrategy',
                'root': copy.deepcopy(root), 'object_key': row['key'], 'native_kind': row['kind'], 'native_id': row['native_id'],
                'definition_id': row['definition_id'], 'source_mapping': copy.deepcopy(mapping), 'query_visual': query,
                'visual_key': scope['target']['key'] if query else None, 'restricted_private_scope': scope['restricted'],
                'declared_disposition': row['disposition'], 'definition_fingerprint': fingerprint, 'definition_sha256': fingerprint})
        if mapping is None:
            helpers['gap'](result, 'microstrategy.expected_object_without_original_mapping', '/inventory/items/' + str(i))
        if row['disposition'] != 'include' or row['kind'] == 'unknown':
            helpers['gap'](result, 'microstrategy.source_disposition_requires_review', '/inventory/items/' + str(i))
        if scope['restricted']:
            helpers['gap'](result, 'microstrategy.private_scope_not_selected', '/inventory/items/' + str(i))
        if row['kind'] in ('visual', 'report', 'cube') and not scope['query_visual']:
            helpers['gap'](result, 'microstrategy.numeric_definition_unqualified', '/inventory/items/' + str(i))
        if row['definition_id'] is not None:
            found = [o for o in payload['objects'] if o['id'] == row['definition_id']]
            result['dependencies'].append({'source_key': row['key'], 'target_native_id': row['definition_id'],
                                           'status': 'declared' if len(found) == 1 else 'unresolved'})
    root_private = any(restricted(r, indexed, objects) for r in indexed.values() if r['parent_key'] is None)
    def inherited(obj, path=''):
        return root_private or _private(obj['payload']) or any(restricted(r, indexed, objects) for r in indexed.values()
            if r['source_mapping'] and r['source_mapping']['object_kind'] == obj['kind']
            and r['source_mapping']['object_id'] == obj['id'] and (path == r['source_mapping']['pointer'] or path.startswith(r['source_mapping']['pointer'] + '/')))
    missing = 0
    for record in native_members(payload):
        obj, path = record['object'], record['pointer']
        member = record['payload']
        if record['kind'] in ('metric', 'attribute', 'filter') and type(member) is dict and guid(native_object_id(member)):
            expected_kind = record['kind']
            member_id = native_object_id(member)
            resolved = (expected_kind, member_id) in objects
            result['dependencies'].append({'source_object_id': obj['id'], 'source_pointer': path,
                'target_native_id': member_id, 'expected_kind': expected_kind, 'status': 'declared' if resolved else 'unresolved'})
            if not resolved:
                helpers['gap'](result, 'microstrategy.semantic_dependency_unresolved', path)
        if (obj['kind'], obj['id'], path) in represented:
            continue
        missing += 1
        helpers['add_asset'](result, 'unknown', {'native_payload': record['payload']}, '/unmapped/' + obj['kind'] + '/' + obj['id'] + path,
            None, namespace, {'visual': {'status': 'needs_review', 'value': copy.deepcopy(record['payload'])}},
            id_kind='native_locator_unmapped', source_identity={'source_platform': 'microstrategy', 'native_kind': record['kind'],
                'query_visual': False, 'restricted_private_scope': inherited(obj, path) or _private(record['payload']),
                'definition_fingerprint': fingerprint, 'source_mapping': {'object_kind': obj['kind'], 'object_id': obj['id'], 'pointer': path}})
        helpers['gap'](result, 'microstrategy.native_member_omitted_from_inventory', path)
    for i, obj in enumerate(payload['objects']):
        if (obj['kind'], obj['id']) not in covered:
            helpers['add_asset'](result, 'definition', obj, '/objects/' + str(i), obj['kind'] + ':' + obj['id'], namespace,
                {'query': {'status': 'needs_review', 'value': copy.deepcopy(obj['payload'])}}, source_identity={
                    'source_platform': 'microstrategy', 'native_kind': obj['kind'], 'query_visual': False,
                    'restricted_private_scope': inherited(obj), 'definition_fingerprint': fingerprint})
    result['microstrategy_coverage'] = {'independently_enumerated': len(indexed), 'native_unmapped': missing,
        'native_definitions': len(objects), 'declared_coverage': payload['inventory']['completeness'],
        'source_export_completeness': 'not_established', 'runtime_coverage': 'not_verified'}
    for item in payload['gaps']:
        helpers['gap'](result, 'microstrategy.supplied_gap', detail=item)
    for code in ('no_DMA_producer_contract', 'effective_access_unverified', 'expressions_custom_code_and_embedded_content_inert',
                 'independent_enumeration_not_full_project_completeness', 'execution_can_have_warehouse_side_effects_requires_host_grant',
                 'rendered_behavior_and_server_version_unverified'):
        helpers['gap'](result, 'microstrategy.' + code)
    return result


def validate_capture(value):
    return module('microstrategy_capture').validate_envelope(value)


def verify_capture_files(value, root):
    return module('microstrategy_capture').verify_capture_files(value, root)


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    snapshot = payload['source']['snapshot']
    result = parse_snapshot(snapshot, encoded(snapshot), helpers)
    result['source'].update(helpers['base'](payload, raw, 'microstrategy', 'supplied_microstrategy_visual_capture')['source'])
    result['source']['capture_content_hash'] = payload['content_hash']
    need(result['source']['definition_fingerprint'] == payload['source']['definition_fingerprint'], 'capture_definition')
    result['upstream_payload'] = copy.deepcopy(payload)
    request = payload['request']
    result['migration_context'].update(route=None if request['route'] == 'unselected' else request['route'],
        route_reference=request['route_reference'], target_surface=request['target_surface'])
    for item in payload['gaps']:
        helpers['gap'](result, 'microstrategy.capture_gap', detail=item)
    helpers['gap'](result, 'microstrategy.actual_files_require_verification')
    return result


def required_cases(asset):
    return ['numeric', 'behavior', 'visual'] if asset.get('source_identity', {}).get('query_visual') else ['behavior', 'visual']


def case_binding(asset, case, capture):
    validate_capture(capture)
    snapshot, identity = capture['source']['snapshot'], asset.get('source_identity', {})
    need(identity.get('definition_fingerprint') == sha(snapshot) and identity.get('root') == snapshot['root']
         and all(identity.get(k) == snapshot['identity'][k] for k in IDENTITY_KEYS), 'case_identity')
    scope = scope_item(snapshot, identity.get('object_key'))
    selected, target = scope['item'], scope['target']
    need(selected['disposition'] == target['disposition'] == 'include' and not scope['restricted'], 'case_scope')
    binding = case.get('source_binding')
    need(type(binding) is dict and set(binding) == {'definition_fingerprint', 'state_sha256', 'object_key', 'placement_key', 'attachment_id'}
         and binding['definition_fingerprint'] == sha(snapshot) and binding['state_sha256'] == sha(capture['request']['state'])
         and binding['object_key'] == target['key'] and binding['placement_key'] ==
         (selected['key'] if selected['kind'] == 'placement' else None), 'case_binding')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id'] and a['object_key'] in (selected['key'], target['key'])]
    need(binding['attachment_id'] is None or len(matches) == 1, 'case_attachment')
    if case.get('lane') == 'numeric':
        need(scope['query_visual'] and len(matches) == 1 and matches[0]['format'] in ('csv', 'json'), 'case_numeric_evidence')
    return binding


def validate_case(value, capture):
    validate_capture(capture)
    binding = value.get('source_binding')
    need(type(binding) is dict and binding.get('definition_fingerprint') == capture['source']['definition_fingerprint']
         and binding.get('state_sha256') == sha(capture['request']['state']), 'case_capture_binding')
    return binding


def precise_json(value):
    if type(value) is Decimal:
        need(value.is_finite(), 'nonfinite_number')
        return str(value).encode('ascii')
    if type(value) is list:
        return b'[' + b','.join(precise_json(v) for v in value) + b']'
    if type(value) is dict:
        return b'{' + b','.join(encoded(k) + b':' + precise_json(v) for k, v in sorted(value.items())) + b'}'
    need(type(value) in (str, int, bool) or value is None, 'scalar_required')
    return encoded(value)


def result_node_clean(node):
    # Call only on known structural nodes, never on caption-keyed/form-value
    # maps: a metric or attribute named "error" remains ordinary data.
    need(type(node) is dict and not any(node.get(k) for k in ('error', 'errors', 'code')), 'result_error')


def json_data_projection(raw, profile):
    """Bounded classic JSON Data attributes-on-rows/metrics-on-columns profile.

    This is not the v2 tabular API or a compiler for subtotal/hierarchy reports.
    Original formatted text, element IDs, forms and tree paths remain inert.
    """
    keys = {'schema_version', 'format', 'shape', 'response_kind', 'response_pointer', 'definition_sha256',
            'object_id', 'instance_id', 'headers', 'columns', 'mappings', 'subtotal_policy', 'population_key', 'coverage_reference'}
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'result_byte_limit')
    need(type(profile) is dict and set(profile) == keys and profile['schema_version'] == 1 and profile['format'] == 'json'
         and profile['shape'] == 'microstrategy_json_data' and profile['response_kind'] in ('report', 'cube', 'visualization')
         and profile['subtotal_policy'] == 'reject' and digest(profile['definition_sha256']) and text(profile['object_id'])
         and guid(profile['instance_id']) and text(profile['population_key']) and text(profile['coverage_reference']), 'json_data_profile')
    checked = F.decode(raw); F.secret_check(checked)
    value = json.loads(raw.decode('utf-8-sig'), parse_float=Decimal)
    response = pointer(value, profile['response_pointer'])
    result_node_clean(response)
    visual = profile['response_kind'] == 'visualization'
    if visual:
        need(response.get('key') == profile['object_id'], 'result_visual_identity')
        # A visualization payload often lacks these fields. Never fabricate them.
        if 'status' in response:
            need(type(response['status']) is int and response['status'] == 1, 'result_not_ready')
        if 'instanceId' in response:
            need(response['instanceId'] == profile['instance_id'], 'result_instance_identity')
    else:
        need(response.get('id') == profile['object_id'] and guid(profile['object_id']), 'result_object_identity')
        need(type(response.get('status')) is int and response['status'] == 1, 'result_not_ready')
        need(response.get('instanceId') == profile['instance_id'], 'result_instance_identity')
    result = response.get('result')
    need(type(result) is dict and type(result.get('definition')) is dict and type(result.get('data')) is dict, 'json_data_shape')
    definition, data = result['definition'], result['data']
    for structural in (result, definition, data):
        result_node_clean(structural)
    checked_definition = pointer(checked, profile['response_pointer'])['result']['definition']
    need(sha(checked_definition) == profile['definition_sha256'], 'result_definition_changed')
    for key in ('subtotals', 'hierarchies', 'dimensions', 'consolidations', 'customGroups', 'compoundAttributes', 'pageBy', 'prompts'):
        need(not definition.get(key), 'unsupported_definition_' + key)
    attributes, metrics = definition.get('attributes'), definition.get('metrics')
    need(type(attributes) is list and len(attributes) <= 32 and type(metrics) is list and 1 <= len(metrics) <= 256
         and all(type(r) is dict and guid(r.get('id')) for r in attributes + metrics), 'result_definition_units')
    need(len({r['id'] for r in attributes}) == len(attributes) and len({r['id'] for r in metrics}) == len(metrics), 'duplicate_definition_identity')
    for unit in attributes + metrics:
        result_node_clean(unit)
    for attribute in attributes:
        forms = attribute.get('forms')
        need(type(forms) is list and 1 <= len(forms) <= 64 and all(type(f) is dict and guid(f.get('id')) for f in forms)
             and len({f['id'] for f in forms}) == len(forms), 'attribute_forms')
        for form in forms:
            result_node_clean(form)
    paging, root = data.get('paging'), data.get('root')
    need(type(paging) is dict and all(type(paging.get(k)) is int for k in ('total', 'current', 'offset', 'limit'))
         and 0 <= paging['total'] <= 100000 and paging['offset'] == 0 and paging['current'] == paging['total']
         and 'next' in paging and paging['next'] is None and 'prev' in paging and paging['prev'] is None, 'result_paging_incomplete')
    result_node_clean(paging)
    # limit=-1 is deliberately neither required nor treated as completeness.
    need(type(root) is dict and root.get('isPartial') is False, 'result_root_partial_or_unknown')
    rows, paths, identities, pending = [], [], set(), [(root, [], '')]
    while pending:
        node, path, locator = pending.pop()
        need(type(node) is dict and len(path) <= 32, 'result_tree_bound')
        result_node_clean(node)
        need(node.get('isPartial', False) is False and not node.get('error') and not node.get('errors'), 'result_partial_or_error')
        need(not any(node.get(k) for k in ('subtotal', 'isSubtotal', 'isTotal', 'isGrandTotal'))
             and node.get('subtotalIndex') is None, 'unsupported_subtotal')
        if 'element' in node:
            element = node['element']
            need(type(element) is dict and type(element.get('attributeIndex')) is int
                 and element['attributeIndex'] == len(path) and len(path) < len(attributes)
                 and type(node.get('depth')) is int and node['depth'] == len(path)
                 and text(element.get('id')) and type(element.get('name')) is str and type(element.get('formValues')) is dict,
                 'attribute_element_path')
            result_node_clean(element)
            path = path + [copy.deepcopy(element)]
        elif locator:
            need(False, 'attribute_element_missing')
        children = node.get('children', [])
        need(type(children) is list, 'result_children')
        if children:
            need(not node.get('metrics'), 'unsupported_internal_metrics_or_subtotal')
            pending.extend((child, path, locator + '/children/' + str(i)) for i, child in reversed(list(enumerate(children))))
            continue
        values = node.get('metrics')
        if values is None and not path and paging['total'] == 0:
            continue
        need(len(path) == len(attributes) and type(values) is dict and len(values) == len(metrics), 'result_leaf_shape')
        identity = tuple(element['id'] for element in path)
        need(identity not in identities, 'duplicate_element_path'); identities.add(identity)
        by_index = {}
        for caption, cell in values.items():
            need(type(caption) is str and type(cell) is dict and type(cell.get('mi')) is int
                 and 0 <= cell['mi'] < len(metrics) and cell['mi'] not in by_index and 'rv' in cell and 'fv' in cell,
                 'metric_index_binding')
            need(cell['rv'] is None or type(cell['rv']) in (int, Decimal), 'metric_raw_type')
            need(cell['fv'] is None or type(cell['fv']) is str, 'metric_formatted_type')
            result_node_clean(cell)
            by_index[cell['mi']] = cell
        need(len(rows) < 100000, 'result_row_bound')
        rows.append((path, by_index)); paths.append({'locator': locator, 'elements': path})
    need(len(rows) == paging['total'], 'result_leaf_count_mismatch')
    headers, columns, mappings = profile['headers'], profile['columns'], profile['mappings']
    need(type(headers) is list and 1 <= len(headers) <= 512 and all(text(h) for h in headers) and len(set(headers)) == len(headers)
         and type(columns) is list and len(columns) == len(headers) and all(type(c) is dict for c in columns)
         and [c.get('ordinal') for c in columns] == list(range(len(columns))) and type(mappings) is list and len(mappings) == len(headers), 'output_columns')
    need(len({encoded(m) for m in mappings}) == len(mappings), 'duplicate_output_mapping')
    for mapping in mappings:
        need(type(mapping) is dict and set(mapping) == {'kind', 'index', 'component', 'form_id', 'form_key'}, 'output_mapping')
        kind, index, component = mapping['kind'], mapping['index'], mapping['component']
        if kind == 'attribute':
            need(type(index) is int and 0 <= index < len(attributes) and component in ('id', 'name', 'form'), 'attribute_mapping')
            if component == 'form':
                forms = [f for f in attributes[index]['forms'] if f['id'] == mapping['form_id']]
                need(len(forms) == 1 and text(mapping['form_key']) and mapping['form_key'] in
                     (forms[0].get('name'), forms[0].get('baseFormCategory')), 'attribute_form_binding')
            else:
                need(mapping['form_id'] is None and mapping['form_key'] is None, 'attribute_mapping_extra')
        elif kind == 'metric':
            need(type(index) is int and 0 <= index < len(metrics) and component in ('raw', 'formatted')
                 and mapping['form_id'] is None and mapping['form_key'] is None, 'metric_mapping')
        else:
            need(kind == 'row' and index is None and component == 'path' and mapping['form_id'] is None and mapping['form_key'] is None, 'row_mapping')
    converted = []
    for path, values in rows:
        row = {}
        for header, mapping in zip(headers, mappings):
            kind, index, component = mapping['kind'], mapping['index'], mapping['component']
            if kind == 'row':
                value = precise_json(path).decode()
            elif kind == 'metric':
                value = values[index]['rv' if component == 'raw' else 'fv']
            elif component == 'form':
                need(mapping['form_key'] in path[index]['formValues'], 'attribute_form_value_missing')
                value = path[index]['formValues'][mapping['form_key']]
                need(value is None or type(value) in (str, int, Decimal, bool), 'attribute_form_value_type')
            else:
                value = path[index][component]
            row[header] = value
        converted.append(row)
    derivative = precise_json(converted)
    need(len(derivative) <= F.MAX_FILE, 'result_projection_byte_limit')
    target_profile = {'schema_version': 1, 'format': 'json', 'rows_pointer': '', 'headers': copy.deepcopy(headers),
                      'columns': copy.deepcopy(columns), 'subtotal_policy': 'preserve'}
    evidence = {'kind': 'explicit_microstrategy_json_data_tree', 'sha256': sha(derivative), 'bytes': len(derivative),
        'definition_sha256': profile['definition_sha256'], 'object_id': profile['object_id'], 'instance_id': profile['instance_id'],
        'population_key': profile['population_key'], 'coverage_reference': profile['coverage_reference'],
        'paging': copy.deepcopy(paging), 'native_tree_json': precise_json(root).decode(), 'native_paths_json': precise_json(paths).decode(),
        'execution_status': 'requires_separate_observed_instance_evidence' if visual else 'native_status_1',
        'completeness': 'single_response_row_coverage_only', 'subtotal_support': 'unsupported_retained_in_original'}
    return derivative, target_profile, evidence


def normalize_results(raw, profile, binding):
    fields = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id', 'state_sha256',
              'attachment_sha256', 'instance_id', 'result_definition_sha256'}
    need(type(binding) is dict and set(binding) == fields and binding['attachment_sha256'] == sha(raw)
         and all(digest(binding[k]) for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256', 'result_definition_sha256'))
         and guid(binding['instance_id']) and text(binding['object_key']) and text(binding['attachment_id']), 'normalization_binding')
    need(type(profile) is dict and profile.get('format') in ('csv', 'json'), 'normalization_profile')
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
              'visual_id': binding['object_key'], 'query_id': binding['attachment_id'], 'state_sha256': binding['state_sha256']}
    if profile.get('shape') == 'microstrategy_json_data':
        need(profile['instance_id'] == binding['instance_id'] and profile['definition_sha256'] == binding['result_definition_sha256'], 'result_binding_mismatch')
        derivative, target_profile, evidence = json_data_projection(raw, profile)
        result = module('powerbi_visual').normalize_results(derivative, target_profile, {**mapped, 'attachment_sha256': sha(derivative)})
        result['projection'] = evidence
    else:
        need(profile.get('format') == 'csv' and 'shape' not in profile, 'unsupported_result_shape')
        result = module('powerbi_visual').normalize_results(raw, profile, {**mapped, 'attachment_sha256': sha(raw)})
    result.update(kind='microstrategy_normalized_results', raw_sha256=sha(raw), parser_profile=copy.deepcopy(profile), binding=copy.deepcopy(binding))
    return result


def verify_normalized_result(normalized, raw, profile, binding):
    expected = normalize_results(raw, profile, binding)
    need(normalized == expected, 'normalized_result_changed')
    return expected


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    gaps = []
    if not case.get('source_capture'):
        gaps.append('source.microstrategy_case_capture_required')
    if capture.get('status') == 'blocked':
        gaps.append('source.microstrategy_capture_blocked')
    pin = source.get('raw_file') if source.get('format') == 'microstrategy-normalized' else source.get('file')
    need(type(pin) is dict, 'comparison_raw_pin')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding['attachment_id'] and a['format'] in ('csv', 'json') and a['sha256'] == pin.get('sha256')]
    if len(matches) != 1:
        return gaps + ['source.microstrategy_result_not_bound']
    attachment = matches[0]
    if attachment['completeness']['status'] != 'complete' or not attachment['completeness'].get('reference') or attachment['completeness'].get('flags'):
        gaps.append('source.microstrategy_completeness_unverified')
    if attachment['origin'] == 'unknown' or attachment['result_scope'] == 'unknown':
        gaps.append('source.microstrategy_result_origin_unverified')
    state, observed = capture['request']['state'], attachment.get('observed_state')
    validate_state(state)
    if any(p['answer_mode'] in ('omitted', 'unresolved') for p in state['parameters']['prompts']):
        gaps.append('source.microstrategy_prompt_answers_unresolved')
    if observed is None:
        gaps.append('source.microstrategy_observed_state_missing')
    else:
        for key in ('filters', 'parameters', 'timezone', 'locale', 'cache', 'principal'):
            wanted = state.get(key)
            if wanted is None or observed['state'].get(key) != wanted or source['context'].get(key) != wanted:
                gaps.append('source.microstrategy_observed.' + key)
            if key not in ('principal', 'cache') and target['context'].get(key) != wanted:
                gaps.append('context.' + key)
        if not guid(observed.get('instance_id')) or not digest(observed.get('result_definition_sha256')) or not text(observed.get('definition_reference')):
            gaps.append('source.microstrategy_instance_definition_unverified')
        if observed.get('execution_status') != 'completed' or not text(observed.get('execution_reference')):
            gaps.append('source.microstrategy_execution_unverified')
        for key in ('instance_id', 'result_definition_sha256'):
            if source['context'].get(key) != observed.get(key):
                gaps.append('source.microstrategy_context.' + key)
    if asset['kind'] == 'placement' and not (observed or {}).get('placement_reference'):
        gaps.append('source.microstrategy_placement_state_unverified')
    indexed = {r['key']: r for r in capture['source']['snapshot']['inventory']['items']}
    contract, actual = indexed[binding['object_key']]['configuration'].get('result_contract'), (observed or {}).get('result_context')
    if contract is None:
        gaps.append('source.microstrategy_result_contract_missing')
    if actual is None:
        gaps.append('source.microstrategy_observed_result_context_missing')
    else:
        result_context(actual)
        for key in ('data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage'):
            if contract is not None and contract[key] != actual[key]:
                gaps.append('source.microstrategy_requested_result.' + key)
            if source['context'].get(key, '__absent__') != actual[key]:
                gaps.append('source.microstrategy_observed_result.' + key)
            if target['context'].get(key, '__absent__') != actual[key]:
                gaps.append('context.' + key)
        if actual['data_mode'] in ('test', 'unknown') or actual['row_limit_stage'] == 'unknown' or actual['aggregation_stage'] == 'unknown':
            gaps.append('source.microstrategy_result_semantics_unqualified')
        if source['context'].get('result_context_reference') != actual['reference'] or not text(target['context'].get('result_context_reference')):
            gaps.append('context.result_context_reference')
        if actual['aggregation_stage'] == 'in_document' and (attachment['origin'] != 'transformed' or attachment['result_scope'] != 'transformed'):
            gaps.append('source.microstrategy_transformed_result_required')
    for key, wanted in {'population': attachment['population']['key'], 'data_watermark': attachment['freshness']['data_watermark'],
                        'freshness_reference': attachment['freshness']['reference'], 'result_scope': attachment['result_scope']}.items():
        if wanted is None or not attachment['freshness']['observed_at'] or source['context'].get(key) != wanted:
            gaps.append('source.microstrategy_context.' + key)
        if key == 'freshness_reference':
            if not text(target['context'].get(key)):
                gaps.append('target.microstrategy_freshness_reference')
        elif target['context'].get(key) != wanted:
            gaps.append('context.' + key)
    if source.get('format') == 'microstrategy-normalized':
        expected = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': sha(capture['source']['snapshot']),
            'object_key': binding['object_key'], 'attachment_id': binding['attachment_id'], 'state_sha256': binding['state_sha256'],
            'attachment_sha256': pin['sha256'], 'instance_id': (observed or {}).get('instance_id'),
            'result_definition_sha256': (observed or {}).get('result_definition_sha256')}
        if type(normalized) is not dict or normalized.get('binding') != expected:
            gaps.append('source.microstrategy_normalization_binding_mismatch')
        if attachment.get('parser_profile') is None or (normalized or {}).get('parser_profile') != attachment['parser_profile']:
            gaps.append('source.microstrategy_observed_parser_profile_changed')
        for field in (normalized or {}).get('parser_profile', {}).get('columns', []):
            currency = field.get('currency')
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get('source') == field['name']]
                if len(mapped) != 1 or source['context'].get('currencies', {}).get(field['name']) != currency['code'] or \
                        target['context'].get('currencies', {}).get(mapped[0]['target']) != currency['code']:
                    gaps.append('context.currency.' + field['name'])
    profile = attachment.get('parser_profile') or {}
    if profile.get('shape') == 'microstrategy_json_data':
        if source.get('format') != 'microstrategy-normalized' or normalized is None:
            gaps.append('source.microstrategy_typed_tree_normalization_required')
        if profile.get('population_key') != attachment['population']['key']:
            gaps.append('source.microstrategy_population_mismatch')
        scope = scope_item(capture['source']['snapshot'], binding['object_key'])
        expected_kind = scope['target']['kind'] if scope['target']['kind'] in ('report', 'cube') else 'visualization'
        if profile.get('response_kind') != expected_kind or profile.get('object_id') != scope['target']['native_id']:
            gaps.append('source.microstrategy_result_native_identity_mismatch')
    return gaps
