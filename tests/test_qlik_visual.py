"""Original neutral QIX/API fixtures; no Qlik runtime, tenant or approval evidence."""
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
    spec = importlib.util.spec_from_file_location('test_qlik_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


V, T = load('qlik_visual'), load('translate_artifact')
HELPERS = {'base': T.base, 'add_asset': T.add_asset, 'gap': T.gap, 'facet': T.facet}


def result_contract():
    return {'data_mode': 'full_data', 'row_limit': None, 'row_limit_stage': 'none',
            'aggregation_stage': 'native_report', 'reference': 'Synthetic observed result semantics'}


def snapshot_fixture():
    def obj(kind, oid, payload):
        return {'kind': kind, 'id': oid, 'payload': payload, 'evidence_ref': 'Synthetic original response'}
    objects = [obj('app', 'app-one', {'qFileName': 'app-one', 'qTitle': 'Orchard inventory'}),
        obj('sheet', 'sheet-one', {'qInfo': {'qId': 'sheet-one', 'qType': 'sheet'},
            'qMeta': {'published': True}, 'cells': [{'name': 'chart-one', 'col': 0, 'row': 0},
                {'name': 'chart-one', 'col': 6, 'row': 0}, {'name': 'note-one', 'col': 0, 'row': 6}]}),
        obj('visual', 'chart-one', {'qInfo': {'qId': 'chart-one', 'qType': 'barchart'}, 'qHandle': 55,
            'qHyperCubeDef': {'qStateName': '$', 'qDimensions': [{'qDef': {'qFieldDefs': ['District']}}],
                'qMeasures': [{'qLibraryId': 'measure-one'}], 'qInterColumnSortOrder': [0, 1]}}),
        obj('measure', 'measure-one', {'qInfo': {'qId': 'measure-one', 'qType': 'measure'},
            'qMeasure': {'qDef': "Sum({<Year={2026}>} Units)", 'qLabel': 'Units'}}),
        obj('unknown', 'note-one', {'qInfo': {'qId': 'note-one', 'qType': 'text-image'}, 'text': 'Original content'}),
        obj('bookmark', 'bookmark-private', {'qInfo': {'qId': 'bookmark-private', 'qType': 'bookmark'},
            'qMeta': {'published': False}, 'qBookmark': {'qStateData': []}})]
    def row(key, kind, okind, oid, path='', native=None, parent='app', **config):
        return {'key': key, 'kind': kind, 'parent_key': parent, 'native_id': native, 'definition_id': None,
            'disposition': 'include', 'reference': 'Synthetic independent enumeration', 'configuration': config,
            'source_mapping': {'object_kind': okind, 'object_id': oid, 'pointer': path} if okind else None}
    items = [row('app', 'app', 'app', 'app-one', native='app-one', parent=None),
        row('sheet', 'sheet', 'sheet', 'sheet-one', native='sheet-one'),
        row('units', 'visual', 'visual', 'chart-one', native='chart-one', result_contract=result_contract()),
        row('left', 'placement', 'sheet', 'sheet-one', '/cells/0', parent='sheet', visual_key='units'),
        row('right', 'placement', 'sheet', 'sheet-one', '/cells/1', parent='sheet', visual_key='units'),
        row('note', 'content', 'unknown', 'note-one', native='note-one'),
        row('note-place', 'placement', 'sheet', 'sheet-one', '/cells/2', parent='sheet', content_key='note'),
        row('district', 'filter', 'visual', 'chart-one', '/qHyperCubeDef/qDimensions/0'),
        row('units-reference', 'measure', 'visual', 'chart-one', '/qHyperCubeDef/qMeasures/0'),
        row('units-definition', 'measure', 'measure', 'measure-one', native='measure-one'),
        row('personal', 'bookmark', 'bookmark', 'bookmark-private', native='bookmark-private'),
        row('future', 'unknown', None, None)]
    return {'schema_version': V.SCHEMA, 'identity': {'source_origin': 'https://qlik.example.invalid',
        'tenant_id': 'tenant-one', 'product': 'cloud', 'version': 'synthetic-2026',
        'principal_ref': 'synthetic-reader', 'engine_version': 'synthetic-engine', 'reference': 'Synthetic version evidence'},
        'root': {'kind': 'app', 'id': 'app-one'}, 'objects': objects,
        'inventory': {'reference': 'Synthetic inventory', 'completeness': 'selected_scope_declared', 'items': items},
        'gaps': ['Synthetic only; no actual tenant or user authorization']}


def numeric_column(index, name):
    return {'ordinal': index, 'name': name, 'type': 'number', 'nullable': True,
        'null_tokens': [], 'decimal_separator': '.', 'group_separator': None, 'percent': False}


def string_column(index, name):
    return {'ordinal': index, 'name': name, 'type': 'string', 'nullable': False, 'null_tokens': []}


def qix_result_fixture(pivot=False):
    cube = {'qMode': 'P' if pivot else 'S', 'qSize': {'qcx': 2, 'qcy': 2},
        'qDimensionInfo': [{'qFallbackTitle': 'District', 'qGroupFieldDefs': ['District']}],
        'qMeasureInfo': [{'qFallbackTitle': 'Units', 'qLibraryId': 'measure-one'}], 'qColumnOrder': [0, 1],
        'qGrandTotalRow': [{'qText': 'Total', 'qNum': Decimal('9007199254740994.100000000000000001'), 'qIsTotalCell': True}]}
    if pivot:
        cube['qNoOfLeftDims'] = 1
        def axis(label, elem, typ='N'):
            return {'qText': label, 'qElemNo': elem, 'qType': typ, 'qSubNodes': [], 'qCanExpand': False}
        page = {'qArea': {'qTop': 0, 'qLeft': 0, 'qWidth': 2, 'qHeight': 2},
            'qLeft': [axis('West', 0), axis('Total', -1, 'T')], 'qTop': [axis('Units', 0), axis('Other', 1)],
            'qData': [[{'qText': '1.10', 'qNum': Decimal('1.100000000000000001'), 'qType': 'N'},
                {'qText': '9,007,199,254,740,993', 'qNum': 9007199254740993, 'qType': 'N'}],
                [{'qText': '-', 'qNum': 'NaN', 'qType': 'T', 'qIsNull': True},
                 {'qText': '0', 'qNum': 0, 'qType': 'T'}]]}
        cube['qPivotDataPages'] = [page]
        components = ['row_index', 'column_index', 'left_path', 'top_path', 'number', 'text', 'cell_type']
        columns = [numeric_column(i, name) if name in ('row_index', 'column_index', 'number') else string_column(i, name)
                   for i, name in enumerate(components)]
        mappings = [{'source_column': None, 'component': c} for c in components]
        pages = '/qHyperCube/qPivotDataPages'
    else:
        page = {'qArea': {'qTop': 0, 'qLeft': 0, 'qWidth': 2, 'qHeight': 2}, 'qMatrix': [
            [{'qText': 'West', 'qNum': 'NaN', 'qElemNumber': 0, 'qState': 'S'},
             {'qText': '1.10', 'qNum': Decimal('1.100000000000000001')}],
            [{'qText': 'East', 'qNum': 'NaN', 'qElemNumber': 1, 'qState': 'O'},
             {'qText': '9,007,199,254,740,993', 'qNum': 9007199254740993}]]}
        cube['qDataPages'] = [page]
        components = ['district', 'units', 'units_display', 'element', 'selection']
        columns = [string_column(0, 'district'), numeric_column(1, 'units'), string_column(2, 'units_display'),
                   numeric_column(3, 'element'), string_column(4, 'selection')]
        mappings = [{'source_column': 0, 'component': 'text'}, {'source_column': 1, 'component': 'number'},
            {'source_column': 1, 'component': 'text'}, {'source_column': 0, 'component': 'element_number'},
            {'source_column': 0, 'component': 'selection_state'}]
        pages = '/qHyperCube/qDataPages'
    raw = V.precise_json({'qHyperCube': cube})
    checked = V.F.decode(raw)['qHyperCube']
    info = checked['qDimensionInfo'] + checked['qMeasureInfo']
    profile = {'schema_version': 1, 'format': 'json', 'shape': 'qlik_pivot' if pivot else 'qlik_straight',
        'cube_pointer': '/qHyperCube', 'pages_pointer': pages, 'metadata_sha256': V.sha(V.cube_metadata(checked)),
        'expected_area': copy.deepcopy(page['qArea']), 'population_key': 'synthetic-all',
        'coverage_reference': 'Synthetic observed rectangle', 'column_bindings': [
            {'source_index': i, 'kind': 'dimension' if i == 0 else 'measure', 'metadata_sha256': V.sha(item)} for i, item in enumerate(info)],
        'headers': components, 'columns': columns, 'mappings': mappings, 'subtotal_policy': 'preserve'}
    binding = {'capture_content_hash': '1' * 64, 'definition_fingerprint': '2' * 64, 'object_key': 'units',
        'attachment_id': 'result-one', 'state_sha256': '3' * 64, 'attachment_sha256': V.sha(raw)}
    return raw, profile, binding


def repin_qix(data, profile, binding):
    """Pin modified synthetic native metadata so status tests reach the guard."""
    raw = V.precise_json(data)
    cube = V.F.decode(raw)['qHyperCube']
    profile = copy.deepcopy(profile)
    profile['metadata_sha256'] = V.sha(V.cube_metadata(cube))
    for row, info in zip(profile['column_bindings'], cube['qDimensionInfo'] + cube['qMeasureInfo']):
        row['metadata_sha256'] = V.sha(info)
    return raw, profile, {**binding, 'attachment_sha256': V.sha(raw)}


def prepare(root, transform=None):
    """Actual passive capture intake of original synthetic files for shared tests."""
    C = load('qlik_capture')
    root = Path(root).resolve(); supplied = root / 'supplied'; supplied.mkdir(parents=True)
    snapshot = snapshot_fixture()
    if transform:
        transform(snapshot)
    records = []
    for i, obj in enumerate(snapshot['objects']):
        name = 'object-%d.json' % i
        (supplied / name).write_bytes(V.encoded(obj['payload']))
        records.append({'source_path': name, 'source_kind': 'supplied_json', 'source_pointer': '',
            'target_pointer': '/objects/%d/payload' % i, 'mapping': 'exact_json', 'member_path': None,
            'reference': 'Synthetic original native JSON', 'mcp_evidence': None})
    (supplied / 'inventory.json').write_bytes(V.encoded(snapshot['inventory']))
    records.append({'source_path': 'inventory.json', 'source_kind': 'supplied_json', 'source_pointer': '',
        'target_pointer': '/inventory', 'mapping': 'exact_json', 'member_path': None,
        'reference': 'Synthetic independent inventory', 'mcp_evidence': None})
    manifest = {'schema_version': 'qlik-originals.v1', 'reference': 'Synthetic transfer', 'records': records}
    (supplied / 'snapshot.json').write_bytes(V.encoded(snapshot)); (supplied / 'originals.json').write_bytes(V.encoded(manifest))
    request = {'schema_version': C.REQUEST_SCHEMA, 'capture_id': 'synthetic-qlik',
        'identity': copy.deepcopy(snapshot['identity']), 'root': copy.deepcopy(snapshot['root']),
        'authorization_ref': 'Synthetic intake only', 'credential_ref': None, 'evidence_mode': 'synthetic_fixture',
        'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': {'filters': {'district': 'West'}, 'parameters': {'threshold': 3}, 'timezone': 'UTC', 'locale': 'en-US',
                  'principal': 'synthetic-reader', 'cache': 'source-cache-disabled', 'reference': 'Synthetic requested state'},
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json'}
    out = C.import_local(request, supplied, root / 'capture', allow_source_read=True)
    return request, out


def add_results(root, request, out, transform=None):
    C = load('qlik_capture')
    source = Path(root).resolve() / 'results'; source.mkdir()
    raw = b'district,units\nWest,1.100000000000000001\nEast,2.00\n'
    (source / 'rows.csv').write_bytes(raw)
    contract = next(r for r in out['capture']['source']['snapshot']['inventory']['items'] if r['key'] == 'units')['configuration']['result_contract']
    row = {'attachment_id': 'result-one', 'object_key': 'units', 'format': 'csv', 'source_path': 'rows.csv',
        'member_path': None, 'origin': 'full', 'result_scope': 'query_result',
        'observed_state': {'state': copy.deepcopy(request['state']), 'observed_at': '2026-01-01T00:00:00Z',
            'reference': 'Synthetic observation', 'placement_reference': 'Synthetic left/right applied state',
            'result_context': copy.deepcopy(contract)},
        'population': {'key': 'synthetic-all', 'description': 'All synthetic rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic freshness'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic complete export'},
        'reference': 'Synthetic CSV'}
    if transform:
        transform(row)
    return raw, C.import_evidence(out['output'], {'schema_version': 'qlik-supplied-evidence.v1', 'attachments': [row]}, source)


def comparison_fixture(root, snapshot_transform=None, evidence_transform=None):
    request, out = prepare(root, snapshot_transform)
    raw, out = add_results(root, request, out, evidence_transform)
    capture = out['capture']; result = V.parse_capture(capture, V.encoded(capture), HELPERS)
    asset = next(a for a in result['assets'] if a['source_identity'].get('object_key') == 'left')
    pin = capture['attachments'][0]
    case = {'lane': 'numeric', 'source_capture': {'path': out['output'], 'sha256': V.sha(Path(out['output']).read_bytes())},
        'source_binding': {'definition_fingerprint': capture['source']['definition_fingerprint'], 'state_sha256': V.sha(request['state']),
            'object_key': 'units', 'placement_key': 'left', 'attachment_id': pin['attachment_id']}}
    context = {**copy.deepcopy(request['state']), 'population': pin['population']['key'],
        'data_watermark': pin['freshness']['data_watermark'], 'freshness_reference': pin['freshness']['reference'],
        'result_scope': pin['result_scope']}
    rc = pin['observed_state'].get('result_context')
    if rc:
        context.update({k: v for k, v in rc.items() if k != 'reference'}); context['result_context_reference'] = rc['reference']
    source = {'format': 'csv', 'file': {'path': pin['path'], 'sha256': pin['sha256']}, 'context': context}
    target = {'format': 'csv', 'file': {'path': 'target.csv', 'sha256': pin['sha256']}, 'context': copy.deepcopy(context)}
    return request, capture, asset, case, source, target, raw


class QlikVisualTests(unittest.TestCase):
    def test_native_hierarchy_repeated_placements_content_and_inert_expression(self):
        value = snapshot_fixture(); result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        assets = {a['source_identity'].get('object_key'): a for a in result['assets']}
        self.assertEqual(result['qlik_coverage']['native_unmapped'], 0)
        self.assertTrue(assets['left']['source_identity']['query_visual'])
        self.assertTrue(assets['right']['source_identity']['query_visual'])
        self.assertFalse(assets['note-place']['source_identity']['query_visual'])
        self.assertFalse(assets['units']['source_identity']['session_handle_authority'])
        self.assertEqual(assets['units']['source_identity']['persistent_object_id'], 'chart-one')
        self.assertEqual(result['upstream_payload'], value)
        self.assertFalse(result['migration_context']['target_write_authority'])
        self.assertIn('Sum({<Year={2026}>} Units)', V.encoded(result).decode())

    def test_omitted_children_remain_unknown_obligations(self):
        value = snapshot_fixture()
        value['inventory']['items'] = [i for i in value['inventory']['items'] if i['key'] not in ('right', 'district')]
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        self.assertEqual(result['qlik_coverage']['native_unmapped'], 2)
        self.assertEqual(sum(a['kind'] == 'unknown' and a['source_identity']['id_kind'] == 'native_locator_unmapped'
                             for a in result['assets']), 2)

    def test_master_dependency_requires_correct_native_type(self):
        value = snapshot_fixture(); value['objects'][3]['kind'] = 'unknown'
        row = value['inventory']['items'][9]; row['source_mapping']['object_kind'] = 'unknown'
        deps = V.native_dependencies(value)
        self.assertEqual(deps[0]['status'], 'unresolved')

    def test_master_visual_reference_not_resolved_by_other_type(self):
        value = snapshot_fixture(); value['objects'][2]['payload']['qExtendsId'] = 'measure-one'
        dep = next(d for d in V.native_dependencies(value) if d['kind'] == 'master_visualization')
        self.assertEqual(dep['status'], 'unresolved')
        master = copy.deepcopy(value['objects'][2]); master['id'] = 'master-chart'
        master['payload']['qInfo']['qId'] = 'master-chart'; del master['payload']['qExtendsId']
        value['objects'].append(master); value['objects'][2]['payload']['qExtendsId'] = 'master-chart'
        dep = next(d for d in V.native_dependencies(value) if d['kind'] == 'master_visualization')
        self.assertEqual(dep['status'], 'declared')

    def test_unmapped_and_unrepresented_private_source_stays_restricted(self):
        value = snapshot_fixture(); value['objects'][1]['payload']['qMeta']['published'] = False
        value['inventory']['items'] = [r for r in value['inventory']['items'] if r['key'] not in ('right', 'personal')]
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        omitted = next(a for a in result['assets'] if (a['source_identity'].get('source_mapping') or {}).get('pointer') == '/cells/1')
        self.assertTrue(omitted['source_identity']['restricted_private_scope'])
        private_definition = next(a for a in result['assets'] if a['source_id'] == 'bookmark-private')
        self.assertTrue(private_definition['source_identity']['restricted_private_scope'])

    def test_private_native_flags_and_ancestor_cannot_be_relabelled(self):
        value = snapshot_fixture(); value['objects'][1]['payload']['qMeta']['published'] = False
        value['inventory']['items'][1]['configuration']['private'] = False
        value['inventory']['items'][3]['configuration']['selection_reference'] = 'Child only'
        self.assertTrue(V.scope_item(value, 'left')['restricted'])
        value['inventory']['items'][1]['configuration']['selection_reference'] = 'Explicit synthetic parent scope'
        self.assertFalse(V.scope_item(value, 'left')['restricted'])
        value['objects'][2]['payload']['qMeta'] = {'published': False}
        self.assertTrue(V.scope_item(value, 'left')['restricted'])

    def test_unknown_object_cannot_gain_query_authority_from_shape(self):
        value = snapshot_fixture(); value['objects'][2]['kind'] = 'unknown'
        for row in value['inventory']['items']:
            if row['source_mapping'] and row['source_mapping']['object_id'] == 'chart-one':
                row['source_mapping']['object_kind'] = 'unknown'
        self.assertFalse(V.scope_item(value, 'left')['query_visual'])

    def test_reject_session_handles_identity_cycles_and_malformed_inventory(self):
        mutations = [lambda v: v['objects'][2]['payload']['qInfo'].update(qId=55),
            lambda v: v['inventory']['items'][1].update(parent_key='left'),
            lambda v: v['inventory']['items'][3]['configuration'].update(visual_key='missing'),
            lambda v: v['inventory']['items'].append(copy.deepcopy(v['inventory']['items'][1])),
            lambda v: v['identity'].update(source_origin='https://user:secret@example.invalid')]
        for change in mutations:
            value = snapshot_fixture(); change(value)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_app_identity_requires_native_layout_filename(self):
        value = snapshot_fixture()
        self.assertEqual(V.validate_snapshot(value), value)
        value['objects'][0]['payload']['qAppId'] = value['objects'][0]['payload'].pop('qFileName')
        with self.assertRaisesRegex(ValueError, 'native_app_identity'): V.validate_snapshot(value)
        value['objects'][0]['payload']['qFileName'] = 'different-app'
        with self.assertRaisesRegex(ValueError, 'native_app_identity'): V.validate_snapshot(value)
        value = snapshot_fixture(); value['inventory']['items'][0]['native_id'] = 'different-app'
        with self.assertRaisesRegex(ValueError, 'native_identity_contradiction'): V.validate_snapshot(value)

    def test_original_capture_pins_and_distinct_route(self):
        with tempfile.TemporaryDirectory() as td:
            request, out = prepare(td)
            cap = out['capture']; V.verify_capture_files(cap, Path(out['output']).parent)
            result = V.parse_capture(cap, V.encoded(cap), HELPERS)
            self.assertEqual(result['source']['capture_content_hash'], cap['content_hash'])
            self.assertIsNone(result['migration_context']['route'])
            self.assertFalse(result['migration_context']['build_authority'])
            original = Path(out['output']).parent / cap['source']['originals'][0]['file']['path']
            original.write_bytes(b'{}')
            with self.assertRaises(ValueError): V.verify_capture_files(cap, Path(out['output']).parent)

    def test_numeric_case_placement_state_and_private_binding(self):
        with tempfile.TemporaryDirectory() as td:
            _, cap, asset, case, source, target, raw = comparison_fixture(td)
            self.assertEqual(V.comparison_gaps(cap, asset, case, source, target), [])
            for key, val in [('object_key', 'note'), ('placement_key', 'right'), ('state_sha256', '0' * 64)]:
                wrong = copy.deepcopy(case); wrong['source_binding'][key] = val
                with self.subTest(key=key), self.assertRaises(ValueError): V.case_binding(asset, wrong, cap)

    def test_matching_freshness_allows_independent_target_cache(self):
        with tempfile.TemporaryDirectory() as td:
            _, cap, asset, case, source, target, _ = comparison_fixture(td)
            target['context']['cache'] = 'User chose independent target refresh'
            self.assertEqual(V.comparison_gaps(cap, asset, case, source, target), [])
            target['context']['data_watermark'] = 'different'
            self.assertIn('context.data_watermark', V.comparison_gaps(cap, asset, case, source, target))
            source['context']['filters'] = {}
            self.assertIn('source.qlik_observed.filters', V.comparison_gaps(cap, asset, case, source, target))

    def test_straight_dual_decimal_element_selection_and_totals_preserved(self):
        raw, profile, binding = qix_result_fixture()
        result = V.normalize_results(raw, profile, binding)
        self.assertEqual(result['rows'][0]['units'], '1.100000000000000001')
        self.assertEqual(result['rows'][1]['units'], '9007199254740993')
        self.assertEqual(result['rows'][0]['units_display'], '1.10')
        self.assertEqual(result['rows'][0]['selection'], 'S')
        self.assertEqual(result['raw_sha256'], V.sha(raw))
        self.assertEqual(result['parser_profile'], profile)
        self.assertIn('9007199254740994.100000000000000001', result['projection']['native_totals_json'])
        self.assertEqual(len(result['projection']['native_cells']), 4)

    def test_straight_split_pages_reassemble_exact_coordinates(self):
        raw, profile, binding = qix_result_fixture()
        data = json.loads(raw, parse_float=Decimal); page = data['qHyperCube']['qDataPages'][0]
        data['qHyperCube']['qDataPages'] = [dict(qArea=dict(qTop=i, qLeft=0, qWidth=2, qHeight=1), qMatrix=[row])
                                          for i, row in reversed(list(enumerate(page['qMatrix'])))]
        modified = V.precise_json(data)
        result = V.normalize_results(modified, profile, {**binding, 'attachment_sha256': V.sha(modified)})
        self.assertEqual(result['rows'][0]['district'], 'West')
        self.assertEqual(result['rows'][1]['district'], 'East')

    def test_element_identity_variant_preserved_and_conflict_rejected(self):
        raw, profile, binding = qix_result_fixture()
        data = json.loads(raw, parse_float=Decimal)
        cell = data['qHyperCube']['qDataPages'][0]['qMatrix'][0][0]
        cell['qElemNo'] = cell.pop('qElemNumber')
        changed = V.precise_json(data)
        result = V.normalize_results(changed, profile, {**binding, 'attachment_sha256':V.sha(changed)})
        self.assertEqual(result['rows'][0]['element'], '0')
        cell['qElemNumber'] = 2; changed = V.precise_json(data)
        with self.assertRaisesRegex(ValueError, 'element_identity_conflict'):
            V.normalize_results(changed, profile, {**binding, 'attachment_sha256':V.sha(changed)})

    def test_qix_native_errors_reject_even_complete_repinned_rectangles(self):
        for pivot in (False, True):
            raw, profile, binding = qix_result_fixture(pivot)
            for location in ('cube', 'dimension', 'measure'):
                for error in ({'qErrorCode': 7000}, {'qErrorCode': 7005}, {}, {'qErrorCode': '0'}, {'qErrorCode': False}):
                    data = json.loads(raw, parse_float=Decimal); cube = data['qHyperCube']
                    node = cube if location == 'cube' else cube['qDimensionInfo' if location == 'dimension' else 'qMeasureInfo'][0]
                    node['qError'] = error
                    with self.subTest(pivot=pivot, location=location, error=error), self.assertRaisesRegex(ValueError, 'qix_(calculation_error|error_state_unqualified)'):
                        V.normalize_results(*repin_qix(data, profile, binding))

    def test_qix_active_condition_message_rejects_cube_and_column_results(self):
        raw, profile, binding = qix_result_fixture()
        for location in ('cube', 'dimension', 'measure'):
            for message in ('Select a district before calculating', False):
                data = json.loads(raw, parse_float=Decimal); cube = data['qHyperCube']
                node = cube if location == 'cube' else cube['qDimensionInfo' if location == 'dimension' else 'qMeasureInfo'][0]
                node['qCalcCondMsg'] = message
                with self.subTest(location=location, message=message), self.assertRaisesRegex(ValueError, 'qix_calculation_condition_'):
                    V.normalize_results(*repin_qix(data, profile, binding))

    def test_qix_ok_status_and_static_condition_definition_are_not_failures(self):
        for pivot in (False, True):
            raw, profile, binding = qix_result_fixture(pivot)
            expected = V.normalize_results(raw, profile, binding)['rows']
            for error in (None, {'qErrorCode': 0}):
                data = json.loads(raw, parse_float=Decimal); cube = data['qHyperCube']
                for node in [cube] + cube['qDimensionInfo'] + cube['qMeasureInfo']:
                    node.update(qError=error, qCalcCondMsg='')
                self.assertEqual(V.normalize_results(*repin_qix(data, profile, binding))['rows'], expected)
        snapshot = snapshot_fixture()
        definition = snapshot['objects'][2]['payload']['qHyperCubeDef']
        definition['qCalcCondition'] = {'qCond': {'qv': 'GetSelectedCount(District)>0'}, 'qMsg': {'qv': 'Select a district'}}
        self.assertEqual(V.validate_snapshot(snapshot), snapshot)
        self.assertTrue(V.scope_item(snapshot, 'units')['query_visual'])

    def test_straight_missing_duplicate_ragged_or_wrong_size_rejected(self):
        raw, profile, binding = qix_result_fixture()
        def missing(data):
            page = data['qHyperCube']['qDataPages'][0]; page['qArea']['qHeight'] = 1; page['qMatrix'].pop()
        def duplicate(data): data['qHyperCube']['qDataPages'].append(copy.deepcopy(data['qHyperCube']['qDataPages'][0]))
        def ragged(data): data['qHyperCube']['qDataPages'][0]['qMatrix'][0].pop()
        def badnum(data): data['qHyperCube']['qDataPages'][0]['qMatrix'][0][1]['qNum'] = True
        for change in (missing, duplicate, ragged, badnum):
            data = json.loads(raw, parse_float=Decimal); change(data); modified = V.precise_json(data)
            with self.subTest(change=change), self.assertRaises(ValueError):
                V.normalize_results(modified, profile, {**binding, 'attachment_sha256': V.sha(modified)})
        with self.assertRaises(ValueError): V.normalize_results(raw, {**profile, 'expected_area': dict(qTop=0,qLeft=0,qWidth=2,qHeight=1)}, binding)

    def test_metadata_mapping_rawhash_and_unsupported_numeric_profile_rejected(self):
        raw, profile, binding = qix_result_fixture()
        changes = [lambda p: p.update(metadata_sha256='0'*64),
            lambda p: p['column_bindings'].reverse(),
            lambda p: p['headers'].__setitem__(0, p['headers'][1]),
            lambda p: p['mappings'][0].update(source_column=6),
            lambda p: p['columns'][1].update(type='guess'),
            lambda p: p.update(subtotal_policy='drop')]
        for change in changes:
            p = copy.deepcopy(profile); change(p)
            with self.subTest(change=change), self.assertRaises(ValueError): V.normalize_results(raw, p, binding)
        with self.assertRaises(ValueError): V.normalize_results(raw, profile, {**binding, 'attachment_sha256': '0'*64})

    def test_pivot_paths_totals_nulls_and_coordinates_preserved(self):
        raw, profile, binding = qix_result_fixture(True)
        result = V.normalize_results(raw, profile, binding)
        self.assertEqual(len(result['rows']), 4)
        self.assertEqual(result['rows'][1]['number'], '9007199254740993')
        self.assertIsNone(result['rows'][2]['number'])
        self.assertEqual(result['rows'][3]['number'], '0')
        self.assertIn('"qType":"T"', result['rows'][2]['left_path'])
        self.assertEqual(result['projection']['coverage'], 'selected_rectangle')
        self.assertEqual(result['projection']['full_cube_completeness'], 'not_established')

    def test_pivot_missing_collapsed_or_contradictory_axis_rejected(self):
        raw, profile, binding = qix_result_fixture(True)
        changes = [lambda d: d['qHyperCube']['qPivotDataPages'][0]['qLeft'].pop(),
            lambda d: d['qHyperCube']['qPivotDataPages'][0]['qLeft'][0].update(qCanExpand=True),
            lambda d: d['qHyperCube']['qPivotDataPages'][0]['qTop'][0].update(qUp=1),
            lambda d: d['qHyperCube']['qPivotDataPages'][0]['qData'][0].pop()]
        for change in changes:
            data = json.loads(raw, parse_float=Decimal); change(data); changed = V.precise_json(data)
            with self.subTest(change=change), self.assertRaises(ValueError):
                V.normalize_results(changed, profile, {**binding, 'attachment_sha256': V.sha(changed)})
        p = copy.deepcopy(profile); p['mappings'][0]['component'] = 'is_null'
        with self.assertRaises(ValueError): V.normalize_results(raw, p, binding)

    def test_qix_capture_requires_exact_observed_parser_profile(self):
        with tempfile.TemporaryDirectory() as td:
            request, out = prepare(td)
            raw, profile, _ = qix_result_fixture()
            source = Path(td).resolve() / 'qix'; source.mkdir(); (source/'layout.json').write_bytes(raw)
            row = {'attachment_id':'qix-one','object_key':'units','format':'json','source_path':'layout.json',
                'member_path':None,'origin':'full','result_scope':'query_result','parser_profile':profile,
                'observed_state':{'state':copy.deepcopy(request['state']),'observed_at':'2026-01-01T00:00:00Z',
                    'reference':'Synthetic observation','placement_reference':'Synthetic placement state','result_context':result_contract()},
                'population':{'key':'synthetic-all','description':'All synthetic rows','reference':'Synthetic population'},
                'freshness':{'data_watermark':'2026-01-01','observed_at':'2026-01-01T00:00:00Z','reference':'Synthetic freshness'},
                'completeness':{'status':'complete','row_count':2,'reference':'Synthetic page coverage'},'reference':'Synthetic QIX pages'}
            out = load('qlik_capture').import_evidence(out['output'], {'schema_version':'qlik-supplied-evidence.v1','attachments':[row]}, source)
            capture = out['capture']; pin = capture['attachments'][0]
            V.verify_capture_files(capture, Path(out['output']).parent)
            self.assertEqual(pin['inspection']['row_count'], 2)
            b = {'capture_content_hash':capture['content_hash'],'definition_fingerprint':capture['source']['definition_fingerprint'],
                'object_key':'units','attachment_id':'qix-one','state_sha256':V.sha(request['state']),'attachment_sha256':V.sha(raw)}
            normalized = V.normalize_results(raw, profile, b)
            self.assertEqual(normalized['parser_profile'], pin['parser_profile'])

    def test_pivot_wrapper_complete_cannot_claim_full_cube_or_change_profile(self):
        with tempfile.TemporaryDirectory() as td:
            request, out = prepare(td)
            raw, profile, _ = qix_result_fixture(True)
            source_root = Path(td).resolve() / 'pivot'; source_root.mkdir(); (source_root/'pivot.json').write_bytes(raw)
            row = {'attachment_id':'pivot-one','object_key':'units','format':'json','source_path':'pivot.json',
                'member_path':None,'origin':'full','result_scope':'query_result','parser_profile':profile,
                'observed_state':{'state':copy.deepcopy(request['state']),'observed_at':'2026-01-01T00:00:00Z',
                    'reference':'Synthetic observation','placement_reference':'Synthetic placement state','result_context':result_contract()},
                'population':{'key':'synthetic-all','description':'Explicit rectangle','reference':'Synthetic population'},
                'freshness':{'data_watermark':'2026-01-01','observed_at':'2026-01-01T00:00:00Z','reference':'Synthetic freshness'},
                'completeness':{'status':'complete','row_count':4,'reference':'Synthetic rectangle only'},'reference':'Synthetic pivot pages'}
            out = load('qlik_capture').import_evidence(out['output'], {'schema_version':'qlik-supplied-evidence.v1','attachments':[row]}, source_root)
            capture, pin = out['capture'], out['capture']['attachments'][0]
            result = V.parse_capture(capture, V.encoded(capture), HELPERS)
            asset = next(a for a in result['assets'] if a['source_identity'].get('object_key') == 'left')
            case = {'lane':'numeric','source_capture':{'path':out['output'],'sha256':V.sha(Path(out['output']).read_bytes())},
                'source_binding':{'definition_fingerprint':capture['source']['definition_fingerprint'],
                    'state_sha256':V.sha(request['state']),'object_key':'units','placement_key':'left','attachment_id':'pivot-one'}}
            context = {**request['state'], 'population':'synthetic-all','data_watermark':'2026-01-01',
                'freshness_reference':'Synthetic freshness','result_scope':'query_result',
                **{k:v for k,v in result_contract().items() if k != 'reference'},
                'result_context_reference':result_contract()['reference']}
            source = {'format':'qlik-normalized','raw_file':{'path':pin['path'],'sha256':pin['sha256']},'context':context}
            target = {'format':'csv','context':copy.deepcopy(context)}
            binding = {'capture_content_hash':capture['content_hash'],'definition_fingerprint':capture['source']['definition_fingerprint'],
                'object_key':'units','attachment_id':'pivot-one','state_sha256':V.sha(request['state']),'attachment_sha256':V.sha(raw)}
            normalized = V.normalize_results(raw, profile, binding)
            gaps = V.comparison_gaps(capture, asset, case, source, target, normalized)
            self.assertEqual(gaps, ['source.qlik_pivot_full_cube_scope_unverified'])
            normalized['parser_profile']['coverage_reference'] = 'Different asserted rectangle'
            self.assertIn('source.qlik_observed_parser_profile_changed', V.comparison_gaps(capture, asset, case, source, target, normalized))


if __name__ == '__main__':
    unittest.main()
