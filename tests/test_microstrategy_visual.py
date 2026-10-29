"""Original synthetic MicroStrategy evidence; no tenant, renderer or source execution."""
import copy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-translator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('test_microstrategy_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


V, T = load('microstrategy_visual'), load('translate_artifact')
HELPERS = {'base': T.base, 'add_asset': T.add_asset, 'gap': T.gap, 'facet': T.facet}
D, A, FORM, M, P, PROJECT, INSTANCE = (c * 32 for c in '1234568')


def definition():
    return {'attributes': [{'id': A, 'name': 'District', 'type': 'Attribute', 'forms': [
        {'id': FORM, 'name': 'DESC', 'dataType': 'Char', 'baseFormCategory': 'DESC', 'baseFormType': 'Text'}]}],
        'metrics': [{'id': M, 'name': 'Yield', 'type': 'Metric', 'dataType': 'Real'}], 'thresholds': [], 'sorting': []}


def result_contract():
    return {'data_mode': 'full_data', 'row_limit': None, 'row_limit_stage': 'none',
            'aggregation_stage': 'native_report', 'reference': 'Synthetic complete source semantics'}


def state():
    return {'filters': {'report': [], 'chapter': [], 'view': [], 'metric_limit': []}, 'parameters': {'prompts': []},
            'timezone': 'UTC', 'locale': 'en-US', 'principal': 'fixture-reader', 'cache': 'source-default',
            'reference': 'Synthetic requested state'}


def snapshot_fixture():
    dossier = {'id': D, 'name': 'Orchard yield', 'chapters': [{'key': 'C1', 'name': 'Overview', 'pages': [
        {'key': 'P1', 'name': 'First view', 'visualizations': [{'key': 'V1', 'name': 'Yield'}]},
        {'key': 'P2', 'name': 'Second view', 'visualizations': [{'key': 'V1', 'name': 'Yield repeated'}]}],
        'filters': [{'key': 'F1', 'name': 'District selector', 'source': {'id': A, 'type': 12}}]}],
        'prompts': [{'key': 'Q1', 'id': P, 'name': 'First prompt'}, {'key': 'Q2', 'id': P, 'name': 'Second prompt'}],
        'unknownFuture': {'script': 'Never execute this source text'}}
    visual = {'key': 'V1', 'name': 'Yield', 'result': {'definition': definition()}}
    objects = [{'kind': kind, 'id': oid, 'payload': payload, 'evidence_ref': 'Synthetic original REST response'}
               for kind, oid, payload in [('dossier', D, dossier), ('visualization', 'V1', visual),
                   ('metric', M, {'id': M, 'name': 'Yield', 'expression': 'Sum(Yield){~}'})]]
    def row(key, kind, parent, okind, oid, pointer='', native=None, **config):
        return {'key': key, 'kind': kind, 'parent_key': parent, 'native_id': native, 'definition_id': None,
            'disposition': 'include', 'reference': 'Synthetic independent scope', 'configuration': config,
            'source_mapping': {'object_kind': okind, 'object_id': oid, 'pointer': pointer} if okind else None}
    rows = [row('root', 'dossier', None, 'dossier', D, native=D),
        row('chapter', 'chapter', 'root', 'dossier', D, '/chapters/0', 'C1'),
        row('page-one', 'page', 'chapter', 'dossier', D, '/chapters/0/pages/0', 'P1'),
        row('page-two', 'page', 'chapter', 'dossier', D, '/chapters/0/pages/1', 'P2'),
        row('yield', 'visual', 'root', 'visualization', 'V1', native='V1', result_contract=result_contract()),
        row('left', 'placement', 'page-one', 'dossier', D, '/chapters/0/pages/0/visualizations/0', 'V1', visual_key='yield'),
        row('right', 'placement', 'page-two', 'dossier', D, '/chapters/0/pages/1/visualizations/0', 'V1', visual_key='yield'),
        row('selector', 'selector', 'chapter', 'dossier', D, '/chapters/0/filters/0', 'F1'),
        row('prompt-one', 'prompt', 'root', 'dossier', D, '/prompts/0', 'Q1'),
        row('prompt-two', 'prompt', 'root', 'dossier', D, '/prompts/1', 'Q2'),
        row('future', 'unknown', 'root', None, None)]
    return {'schema_version': V.SCHEMA, 'identity': {'source_origin': 'https://source.example.invalid',
        'context_path': '/MicroStrategyLibrary', 'project_id': PROJECT, 'principal_ref': 'fixture-reader',
        'library_version': '2026.01', 'intelligence_server_version': '2026.01', 'model_generation': 'classic',
        'delivery_context': 'library', 'reference': 'Synthetic version and source identity'},
        'root': {'kind': 'dossier', 'id': D}, 'objects': objects,
        'inventory': {'reference': 'Synthetic independent expected scope', 'completeness': 'selected_scope_declared', 'items': rows},
        'gaps': ['Synthetic only; no actual user, source access or native proof']}


def numeric_column(index, name):
    return {'ordinal': index, 'name': name, 'type': 'number', 'nullable': True, 'null_tokens': [],
            'decimal_separator': '.', 'group_separator': None, 'percent': False}


def string_column(index, name):
    return {'ordinal': index, 'name': name, 'type': 'string', 'nullable': False, 'null_tokens': []}


def tree_fixture(kind='report'):
    children = []
    for i, (name, number, formatted) in enumerate([('West', Decimal('1.100000000000000001'), '1.10'),
                                                  ('East', 9007199254740993, '9,007,199,254,740,993')]):
        children.append({'depth': 0, 'element': {'attributeIndex': 0, 'formValues': {'DESC': name},
            'name': name, 'id': 'h%d;%s' % (i, A)}, 'metrics': {'Yield': {'rv': number, 'fv': formatted, 'mi': 0}}})
    response = {'key': 'V1', 'name': 'Yield'} if kind == 'visualization' else {'id': D, 'status': 1, 'instanceId': INSTANCE}
    response['result'] = {'definition': definition(), 'data': {'paging': {'total': 2, 'current': 2, 'offset': 0,
        'limit': -1, 'prev': None, 'next': None}, 'root': {'isPartial': False, 'children': children}}}
    headers = ['district', 'yield', 'yield_display', 'element_id', 'form', 'tree_path']
    columns = [numeric_column(i, name) if name == 'yield' else string_column(i, name) for i, name in enumerate(headers)]
    mappings = [dict(kind=k, index=i, component=c, form_id=f, form_key=fk) for k, i, c, f, fk in [
        ('attribute', 0, 'name', None, None), ('metric', 0, 'raw', None, None), ('metric', 0, 'formatted', None, None),
        ('attribute', 0, 'id', None, None), ('attribute', 0, 'form', FORM, 'DESC'), ('row', None, 'path', None, None)]]
    raw = V.precise_json(response)
    profile = {'schema_version': 1, 'format': 'json', 'shape': 'microstrategy_json_data', 'response_kind': kind,
        'response_pointer': '', 'definition_sha256': V.sha(definition()), 'object_id': 'V1' if kind == 'visualization' else D,
        'instance_id': INSTANCE, 'headers': headers, 'columns': columns, 'mappings': mappings, 'subtotal_policy': 'reject',
        'population_key': 'synthetic-all', 'coverage_reference': 'Synthetic exact full response'}
    binding = {'capture_content_hash': '1' * 64, 'definition_fingerprint': '2' * 64, 'object_key': 'yield',
        'attachment_id': 'result-one', 'state_sha256': V.sha(state()), 'attachment_sha256': V.sha(raw),
        'instance_id': INSTANCE, 'result_definition_sha256': V.sha(definition())}
    return raw, profile, binding


def repin(data, profile, binding):
    raw = V.precise_json(data); profile = copy.deepcopy(profile)
    profile['definition_sha256'] = V.sha(V.F.decode(raw)['result']['definition'])
    return raw, profile, {**binding, 'attachment_sha256': V.sha(raw), 'result_definition_sha256': profile['definition_sha256']}


def prepare(root, transform=None):
    C = load('microstrategy_capture')
    root = Path(root).resolve(); supplied = root / 'supplied'; supplied.mkdir(parents=True)
    snapshot = snapshot_fixture()
    if transform: transform(snapshot)
    records = []
    for i, obj in enumerate(snapshot['objects']):
        filename = 'object-%d.json' % i; (supplied / filename).write_bytes(V.encoded(obj['payload']))
        records.append({'source_path': filename, 'source_kind': 'supplied_json', 'source_pointer': '',
            'target_pointer': '/objects/%d/payload' % i, 'mapping': 'exact_json', 'member_path': None,
            'reference': 'Synthetic original native JSON', 'mcp_evidence': None})
    (supplied / 'inventory.json').write_bytes(V.encoded(snapshot['inventory']))
    records.append({'source_path': 'inventory.json', 'source_kind': 'supplied_json', 'source_pointer': '',
        'target_pointer': '/inventory', 'mapping': 'exact_json', 'member_path': None,
        'reference': 'Synthetic independent enumeration', 'mcp_evidence': None})
    manifest = {'schema_version': 'microstrategy-originals.v1', 'reference': 'Synthetic original transfer', 'records': records}
    (supplied / 'snapshot.json').write_bytes(V.encoded(snapshot)); (supplied / 'originals.json').write_bytes(V.encoded(manifest))
    request = {'schema_version': C.REQUEST_SCHEMA, 'capture_id': 'synthetic-microstrategy', 'identity': copy.deepcopy(snapshot['identity']),
        'root': copy.deepcopy(snapshot['root']), 'authorization_ref': 'Synthetic intake only', 'credential_ref': None,
        'evidence_mode': 'synthetic_fixture', 'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': state(), 'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json'}
    return request, C.import_local(request, supplied, root / 'capture', allow_source_read=True)


def add_results(root, request, out, transform=None):
    C = load('microstrategy_capture'); source = Path(root).resolve() / 'results'; source.mkdir()
    raw, profile, _ = tree_fixture('visualization'); (source / 'rows.json').write_bytes(raw)
    row = {'attachment_id': 'result-one', 'object_key': 'yield', 'format': 'json', 'source_path': 'rows.json', 'member_path': None,
        'parser_profile': profile, 'origin': 'full', 'result_scope': 'query_result',
        'observed_state': {'state': copy.deepcopy(request['state']), 'observed_at': '2026-01-01T00:00:00Z',
            'reference': 'Synthetic observed state', 'placement_reference': 'Synthetic repeated placement state',
            'instance_id': INSTANCE, 'result_definition_sha256': V.sha(definition()), 'definition_reference': 'Synthetic instance definition',
            'execution_status': 'completed', 'execution_reference': 'Synthetic separate instance execution observation',
            'result_context': result_contract()},
        'population': {'key': 'synthetic-all', 'description': 'All synthetic rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic freshness'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic full response'}, 'reference': 'Synthetic results'}
    if transform: transform(row)
    return raw, C.import_evidence(out['output'], {'schema_version': 'microstrategy-supplied-evidence.v1', 'attachments': [row]}, source)


def comparison_fixture(root, snapshot_transform=None, evidence_transform=None):
    request, out = prepare(root, snapshot_transform); raw, out = add_results(root, request, out, evidence_transform)
    capture = out['capture']; result = V.parse_capture(capture, V.encoded(capture), HELPERS)
    asset = next(a for a in result['assets'] if a['source_identity'].get('object_key') == 'left')
    pin = capture['attachments'][0]
    case = {'lane': 'numeric', 'source_capture': {'path': out['output'], 'sha256': V.sha(Path(out['output']).read_bytes())},
        'source_binding': {'definition_fingerprint': capture['source']['definition_fingerprint'], 'state_sha256': V.sha(request['state']),
            'object_key': 'yield', 'placement_key': 'left', 'attachment_id': pin['attachment_id']}}
    context = {**copy.deepcopy(request['state']), 'population': pin['population']['key'], 'data_watermark': pin['freshness']['data_watermark'],
        'freshness_reference': pin['freshness']['reference'], 'result_scope': pin['result_scope'],
        'instance_id': INSTANCE, 'result_definition_sha256': V.sha(definition()),
        **{k: v for k, v in result_contract().items() if k != 'reference'}, 'result_context_reference': result_contract()['reference']}
    source = {'format': 'microstrategy-normalized', 'raw_file': {'path': pin['path'], 'sha256': pin['sha256']}, 'context': context}
    target = {'format': 'csv', 'context': copy.deepcopy(context)}
    return request, capture, asset, case, source, target, raw


def normalized_for(capture, raw):
    pin = capture['attachments'][0]
    binding = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': capture['source']['definition_fingerprint'],
        'object_key': 'yield', 'attachment_id': pin['attachment_id'], 'state_sha256': V.sha(capture['request']['state']),
        'attachment_sha256': V.sha(raw), 'instance_id': INSTANCE, 'result_definition_sha256': V.sha(definition())}
    return V.normalize_results(raw, pin['parser_profile'], binding)


class MicroStrategyVisualTests(unittest.TestCase):
    def test_native_hierarchy_repeated_placements_prompts_and_opaque_fields(self):
        snapshot = snapshot_fixture(); result = V.parse_snapshot(snapshot, V.encoded(snapshot), HELPERS)
        assets = {a['source_identity'].get('object_key'): a for a in result['assets']}
        self.assertTrue(assets['left']['source_identity']['query_visual']); self.assertTrue(assets['right']['source_identity']['query_visual'])
        self.assertEqual(assets['prompt-one']['source_identity']['native_id'], 'Q1')
        self.assertEqual(assets['prompt-two']['source_identity']['native_id'], 'Q2')
        self.assertEqual(result['upstream_payload']['objects'][0]['payload']['unknownFuture'], snapshot['objects'][0]['payload']['unknownFuture'])
        self.assertFalse(result['migration_context']['build_authority']); self.assertFalse(result['source_execution'])

    def test_unknown_omitted_and_unavailable_remain_denominator(self):
        snapshot = snapshot_fixture(); snapshot['inventory']['items'] = [snapshot['inventory']['items'][0]]
        result = V.parse_snapshot(snapshot, V.encoded(snapshot), HELPERS)
        self.assertGreater(result['microstrategy_coverage']['native_unmapped'], 5)
        self.assertTrue(any(a['kind'] == 'definition' for a in result['assets']))
        snapshot = snapshot_fixture(); snapshot['inventory']['items'][-1]['disposition'] = 'unavailable'
        self.assertEqual(V.validate_snapshot(snapshot), snapshot)

    def test_private_parent_and_unrepresented_source_are_restricted(self):
        snapshot = snapshot_fixture(); snapshot['objects'][0]['payload']['private'] = True
        self.assertTrue(V.scope_item(snapshot, 'left')['restricted'])
        result = V.parse_snapshot(snapshot, V.encoded(snapshot), HELPERS)
        self.assertTrue(all(a['source_identity'].get('restricted_private_scope') for a in result['assets']))
        snapshot['inventory']['items'][0]['configuration']['selection_reference'] = 'Explicit synthetic root selection'
        self.assertFalse(V.scope_item(snapshot, 'left')['restricted'])

    def test_prompt_occurrences_and_four_filter_stages_cannot_collapse(self):
        value = state(); value['parameters']['prompts'] = [dict(key=k, id=P, answer_mode=m, value=None) for k, m in [('Q1','empty'),('Q2','omitted')]]
        self.assertEqual(V.validate_state(value), value)
        value['parameters']['prompts'][1]['key'] = 'Q1'
        with self.assertRaises(ValueError): V.validate_state(value)
        value = state(); value['filters'].pop('metric_limit')
        with self.assertRaises(ValueError): V.validate_state(value)

    def test_identity_cycles_unknown_query_and_malformed_mapping_rejected(self):
        changes = [lambda s: s['objects'][0]['payload'].update(id=M), lambda s: s['root'].update(id='not-guid'),
            lambda s: s['inventory']['items'][1].update(parent_key='left'),
            lambda s: s['inventory']['items'][5]['configuration'].update(visual_key='missing'),
            lambda s: s['inventory']['items'][4]['source_mapping'].update(pointer='/not-there')]
        for change in changes:
            value = snapshot_fixture(); change(value)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate_snapshot(value)
        snapshot = snapshot_fixture(); snapshot['objects'][1]['kind'] = 'unknown'
        snapshot['inventory']['items'][4]['source_mapping']['object_kind'] = 'unknown'
        self.assertFalse(V.scope_item(snapshot, 'yield')['query_visual'])

    def test_metric_dependency_cannot_resolve_to_wrong_native_object_type(self):
        snapshot = snapshot_fixture(); snapshot['objects'][2]['kind'] = 'attribute'
        result = V.parse_snapshot(snapshot, V.encoded(snapshot), HELPERS)
        match = next(d for d in result['dependencies'] if d.get('target_native_id') == M and d.get('expected_kind') == 'metric')
        self.assertEqual(match['status'], 'unresolved')

    def test_native_modeling_report_identity_and_units_without_synthetic_fields(self):
        snapshot = snapshot_fixture()
        payload = {'information': {'objectId': D, 'versionId': 'a'*32, 'subType': 'report_grid', 'name': 'Yield report'},
            'sourceType': 'normal', 'dataSource': {'dataTemplate': {'units': [
                {'type': 'metrics', 'elements': [{'id': M, 'name': 'Yield', 'subType': 'metric'}]}]}},
            'grid': {'viewTemplate': {'rows': {'units': [{'type': 'attribute', 'id': A}]},
                                      'columns': {'units': []}}}}
        snapshot['root']['kind'] = 'report'
        snapshot['objects'] = [{'kind': 'report', 'id': D, 'payload': payload, 'evidence_ref': 'Synthetic native Modeling response'}]
        root = snapshot['inventory']['items'][0]; snapshot['inventory']['items'] = [root]
        root['kind'] = root['source_mapping']['object_kind'] = 'report'
        result = V.parse_snapshot(snapshot, V.encoded(snapshot), HELPERS)
        self.assertTrue(V.scope_item(snapshot, 'root')['query_visual'])
        self.assertTrue(any(d.get('target_native_id') == M and d.get('expected_kind') == 'metric'
                            and d['status'] == 'unresolved' for d in result['dependencies']))
        self.assertTrue(any(d.get('target_native_id') == A and d.get('expected_kind') == 'attribute'
                            for d in result['dependencies']))
        self.assertEqual(result['upstream_payload']['objects'][0]['payload'], payload)
        self.assertNotIn('id', payload); self.assertNotIn('definition', payload)
        for changes in ({'id': M}, {'versionId': 'b'*32}):
            bad = copy.deepcopy(snapshot); bad['objects'][0]['payload'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): V.validate_snapshot(bad)
        payload['information']['subType'] = 'report_datamart'
        self.assertFalse(V.scope_item(snapshot, 'root')['query_visual'])

    def test_numeric_placement_needs_matching_original_occurrence(self):
        for change in (lambda s: s['inventory']['items'][5].update(source_mapping=None),
                       lambda s: (s['objects'][0]['payload']['chapters'][0]['pages'][0]['visualizations'][0].update(key='V2'),
                                  s['inventory']['items'][5].update(native_id='V2'))):
            with tempfile.TemporaryDirectory() as td:
                _, capture, asset, case, _, _, _ = comparison_fixture(td, change)
                self.assertFalse(asset['source_identity']['query_visual'])
                with self.assertRaisesRegex(ValueError, 'case_numeric_evidence'): V.case_binding(asset, case, capture)

    def test_tree_preserves_decimal_int64_dual_form_and_element_identity(self):
        raw, profile, binding = tree_fixture(); result = V.normalize_results(raw, profile, binding)
        self.assertEqual(result['rows'][0]['yield'], '1.100000000000000001')
        self.assertEqual(result['rows'][1]['yield'], '9007199254740993')
        self.assertEqual(result['rows'][0]['yield_display'], '1.10')
        self.assertEqual(result['rows'][0]['element_id'], 'h0;' + A)
        self.assertEqual(result['rows'][0]['form'], 'West'); self.assertIn('attributeIndex', result['rows'][0]['tree_path'])
        self.assertEqual(result['raw_sha256'], V.sha(raw)); self.assertEqual(result['parser_profile'], profile)

    def test_visualization_does_not_invent_instance_status(self):
        raw, profile, binding = tree_fixture('visualization'); result = V.normalize_results(raw, profile, binding)
        self.assertNotIn('status', json.loads(raw))
        self.assertEqual(result['projection']['execution_status'], 'requires_separate_observed_instance_evidence')
        data = json.loads(raw, parse_float=Decimal); data['status'] = 2
        with self.assertRaisesRegex(ValueError, 'result_not_ready'): V.normalize_results(*repin(data, profile, binding))

    def test_partial_pending_error_or_wrong_instance_cannot_normalize(self):
        raw, profile, binding = tree_fixture()
        changes = [lambda d: d.update(status=2), lambda d: d.update(status=True), lambda d: d.update(instanceId='9'*32),
            lambda d: d.update(error={'code':'failed'}), lambda d: d['result']['data']['root'].update(isPartial=True),
            lambda d: d['result']['data']['root']['children'][0].update(isPartial=True)]
        for change in changes:
            data = json.loads(raw, parse_float=Decimal); change(data)
            with self.subTest(change=change), self.assertRaises(ValueError): V.normalize_results(*repin(data, profile, binding))

    def test_limit_minus_one_does_not_override_paging_or_leaf_count(self):
        raw, profile, binding = tree_fixture()
        for change in [lambda d: d['result']['data']['paging'].update(total=3),
                       lambda d: d['result']['data']['paging'].update(offset=1),
                       lambda d: d['result']['data']['paging'].update(next='/next'),
                       lambda d: d['result']['data']['root']['children'].pop()]:
            data = json.loads(raw, parse_float=Decimal); change(data)
            with self.subTest(change=change), self.assertRaises(ValueError): V.normalize_results(*repin(data, profile, binding))

    def test_structural_errors_reject_but_error_captions_remain_data(self):
        raw, profile, binding = tree_fixture()
        paths = ['/result', '/result/data', '/result/definition', '/result/data/paging',
                 '/result/definition/attributes/0', '/result/definition/attributes/0/forms/0',
                 '/result/definition/metrics/0', '/result/data/root/children/0/element']
        for path in paths:
            data = json.loads(raw, parse_float=Decimal); V.pointer(data, path)['error'] = {'code': 'fixture-failure'}
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'result_error'):
                V.normalize_results(*repin(data, profile, binding))
        data = json.loads(raw, parse_float=Decimal)
        data['result']['definition']['metrics'][0]['name'] = 'error'
        for row in data['result']['data']['root']['children']:
            row['metrics']['error'] = row['metrics'].pop('Yield')
            row['element']['formValues']['error'] = 'A real form caption'
        self.assertEqual(len(V.normalize_results(*repin(data, profile, binding))['rows']), 2)

    def test_metric_index_and_unsupported_subtotal_fail_closed(self):
        raw, profile, binding = tree_fixture()
        for change in [lambda d: d['result']['data']['root']['children'][0]['metrics']['Yield'].update(mi=1),
                       lambda d: d['result']['data']['root']['children'][0]['metrics']['Yield'].update(rv='1.1'),
                       lambda d: d['result']['data']['root']['children'][0].update(isSubtotal=True),
                       lambda d: d['result']['definition'].update(hierarchies=[{'id':A}]),
                       lambda d: d['result']['definition'].update(prompts=[{'key':'Q1','id':P}])]:
            data = json.loads(raw, parse_float=Decimal); change(data)
            with self.subTest(change=change), self.assertRaises(ValueError): V.normalize_results(*repin(data, profile, binding))

    def test_nested_attribute_paths_are_exact_and_duplicate_paths_reject(self):
        raw, profile, binding = tree_fixture(); data = json.loads(raw, parse_float=Decimal)
        second = copy.deepcopy(data['result']['definition']['attributes'][0]); second['id'] = 'A'*32
        second['name'] = 'Plot'; data['result']['definition']['attributes'].append(second)
        parents = data['result']['data']['root']['children']
        for parent in parents:
            parent['children'] = [{'depth': 1, 'element': {'attributeIndex': 1, 'formValues': {'DESC':'Plot 1'},
                'name':'Plot 1', 'id':'h1;' + second['id']}, 'metrics':parent.pop('metrics')}]
        result = V.normalize_results(*repin(data, profile, binding))
        self.assertEqual(len(json.loads(result['rows'][0]['tree_path'])), 2)
        parents[1]['element'] = copy.deepcopy(parents[0]['element'])
        with self.assertRaisesRegex(ValueError, 'duplicate_element_path'): V.normalize_results(*repin(data, profile, binding))

    def test_null_and_formatted_markup_are_preserved_as_data(self):
        raw, profile, binding = tree_fixture(); data = json.loads(raw, parse_float=Decimal)
        cell = data['result']['data']['root']['children'][0]['metrics']['Yield']; cell.update(rv=None, fv='<span>Unavailable</span>')
        result = V.normalize_results(*repin(data, profile, binding))
        self.assertIsNone(result['rows'][0]['yield']); self.assertEqual(result['rows'][0]['yield_display'], '<span>Unavailable</span>')

    def test_original_hash_profile_definition_and_normalized_replay(self):
        raw, profile, binding = tree_fixture(); result = V.normalize_results(raw, profile, binding)
        self.assertEqual(V.verify_normalized_result(result, raw, profile, binding), result)
        result['rows'][0]['yield'] = '999'
        with self.assertRaisesRegex(ValueError, 'normalized_result_changed'): V.verify_normalized_result(result, raw, profile, binding)
        with self.assertRaises(ValueError): V.normalize_results(raw, profile, {**binding, 'attachment_sha256':'0'*64})
        with self.assertRaises(ValueError): V.normalize_results(raw, {**profile,'definition_sha256':'0'*64}, binding)
        with self.assertRaises(ValueError): V.normalize_results(raw, {**profile,'shape':'guess'}, binding)

    def test_original_capture_reprojection_and_byte_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            _, out = prepare(td); cap = out['capture']; V.verify_capture_files(cap, Path(out['output']).parent)
            parsed = V.parse_capture(cap, V.encoded(cap), HELPERS)
            self.assertFalse(parsed['migration_context']['target_write_authority'])
            pin = cap['source']['originals'][0]['file']; (Path(out['output']).parent / pin['path']).write_bytes(b'{}')
            with self.assertRaises(ValueError): V.verify_capture_files(cap, Path(out['output']).parent)

    def test_exact_capture_numeric_binding_and_independent_target_cache(self):
        with tempfile.TemporaryDirectory() as td:
            _, cap, asset, case, source, target, raw = comparison_fixture(td)
            normalized = normalized_for(cap, raw); target['context']['cache'] = 'different-target-policy'
            self.assertEqual(V.comparison_gaps(cap, asset, case, source, target, normalized), [])
            target['context']['data_watermark'] = 'different'
            self.assertIn('context.data_watermark', V.comparison_gaps(cap, asset, case, source, target, normalized))
            wrong = copy.deepcopy(case); wrong['source_binding']['placement_key'] = 'right'
            with self.assertRaises(ValueError): V.case_binding(asset, wrong, cap)

    def test_capture_instance_and_staged_filter_context_cannot_be_swapped(self):
        with tempfile.TemporaryDirectory() as td:
            _, cap, asset, case, source, target, raw = comparison_fixture(td); normalized = normalized_for(cap, raw)
            source['context']['instance_id'] = '9'*32
            self.assertIn('source.microstrategy_context.instance_id', V.comparison_gaps(cap, asset, case, source, target, normalized))
            source['context']['instance_id'] = INSTANCE; target['context']['filters']['view'] = [{'expression':'Yield > 1'}]
            self.assertIn('context.filters', V.comparison_gaps(cap, asset, case, source, target, normalized))
            normalized['binding']['instance_id'] = '9'*32
            self.assertIn('source.microstrategy_normalization_binding_mismatch', V.comparison_gaps(cap, asset, case, source, target, normalized))


if __name__ == '__main__': unittest.main()
