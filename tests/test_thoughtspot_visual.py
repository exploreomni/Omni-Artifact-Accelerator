"""Original synthetic JSON TML and observed-state fixtures; no vendor runtime."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-translator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('test_ts_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


V, T = load('thoughtspot_visual'), load('translate_artifact')
HELPERS = {'base': T.base, 'add_asset': T.add_asset, 'gap': T.gap, 'facet': T.facet}


def result_contract():
    return {'data_mode': 'full_data', 'row_limit': None, 'row_limit_stage': 'none',
            'aggregation_stage': 'native_report', 'reference': 'Synthetic observed result semantics'}


def compact_result_fixture():
    """Explicit native-style matrix pointers; synthetic IDs, not a vendor-shape inference."""
    raw = (b'{"result":{"columns":[{"column_id":"district-id"},{"column_id":"count-id"},'
           b'{"column_id":"volume-id"},{"column_id":"enabled-id"}],"data":'
           b'[["West",9007199254740993,1.100000000000000001,true],["East",0,null,false]]}}')
    numeric = {'type': 'number', 'null_tokens': [], 'nullable': True,
               'decimal_separator': '.', 'group_separator': None, 'percent': False}
    profile = {'schema_version': 1, 'format': 'json', 'shape': 'compact_matrix',
        'headers_pointer': '/result/columns', 'rows_pointer': '/result/data', 'header_id_key': 'column_id',
        'column_ids': ['district-id', 'count-id', 'volume-id', 'enabled-id'],
        'headers': ['district', 'count', 'volume', 'enabled'], 'subtotal_policy': 'preserve',
        'columns': [{'ordinal': 0, 'name': 'district', 'type': 'string', 'null_tokens': [], 'nullable': False},
            {'ordinal': 1, 'name': 'count', **numeric}, {'ordinal': 2, 'name': 'volume', **numeric},
            {'ordinal': 3, 'name': 'enabled', 'type': 'boolean', 'null_tokens': [], 'nullable': False}]}
    binding = {'capture_content_hash': '1' * 64, 'definition_fingerprint': '2' * 64, 'object_key': 'units',
        'attachment_id': 'matrix-one', 'state_sha256': '3' * 64, 'attachment_sha256': V.sha(raw)}
    return raw, profile, binding


def snapshot_fixture():
    """Known TML fields are source-shaped; all identifiers/data are original synthetic."""
    answer = {'name': 'Units by district', 'search_query': '[Units] [District]',
        'tables': [{'id': 'table-one', 'name': 'Garden', 'fqn': 'synthetic.garden'}],
        'formulas': [{'id': 'formula-one', 'name': 'Adjusted', 'expr': 'sum([Units]) + 1', 'properties': {}}],
        'answer_columns': [{'id': 'units', 'name': 'Units', 'custom_name': 'Units'}],
        'chart': {'type': 'COLUMN', 'chart_columns': [{'id': 'units'}], 'axis_configs': [], 'locked': True,
                  'client_state': '{"labels":{"visible":true}}'}, 'display_mode': 'CHART'}
    body = {'name': 'Garden operations', 'description': 'Synthetic only',
        'visualizations': [{'id': 'Viz_1', 'viz_guid': 'viz-one', 'answer': answer},
                           {'id': 'Note_2', 'viz_guid': 'note-two', 'note': {'text': 'Source note'}}],
        'layout': {'tabs': [{'name': 'Overview', 'tiles': [
            {'visualization_id': 'Viz_1', 'x': 0, 'y': 0, 'width': 4, 'height': 4},
            {'visualization_id': 'Viz_1', 'x': 4, 'y': 0, 'width': 4, 'height': 4},
            {'visualization_id': 'Note_2', 'x': 0, 'y': 4, 'size': 'SMALL'}]}]},
        'filters': [{'column': ['District', 'Linked district'], 'oper': 'IN', 'values': ['West'],
                     'excluded_visualizations': ['Note_2']}],
        'parameter_overrides': [{'key': 'threshold', 'value': {'name': 'Threshold', 'id': 'p-one', 'override_value': 3}}],
        'views': [{'view_guid': 'view-private', 'name': 'My view', 'is_public': False,
                   'view_filters': [], 'view_parameters': []},
                  {'view_guid': 'view-public', 'name': 'Shared view', 'is_public': True,
                   'view_filters': [], 'view_parameters': []}]}
    def row(key, kind, path, native=None, parent='board', **config):
        return {'key': key, 'kind': kind, 'parent_key': parent, 'native_id': native, 'definition_id': None,
                'disposition': 'include', 'reference': 'Synthetic independent source inventory', 'configuration': config,
                'source_mapping': {'object_kind': 'liveboard', 'object_id': 'board-one', 'pointer': path} if path is not None else None}
    items = [row('board', 'liveboard', '', 'board-one', None),
        row('units', 'visual', '/liveboard/visualizations/0', 'viz-one', result_contract=result_contract()),
        row('note', 'note', '/liveboard/visualizations/1', 'note-two'),
        row('tab-overview', 'tab', '/liveboard/layout/tabs/0'),
        row('left', 'placement', '/liveboard/layout/tabs/0/tiles/0', 'Viz_1', 'tab-overview', visual_key='units'),
        row('right', 'placement', '/liveboard/layout/tabs/0/tiles/1', 'Viz_1', 'tab-overview', visual_key='units'),
        row('note-place', 'placement', '/liveboard/layout/tabs/0/tiles/2', 'Note_2', 'tab-overview', content_key='note'),
        row('district', 'filter', '/liveboard/filters/0'),
        row('threshold', 'parameter', '/liveboard/parameter_overrides/0'),
        row('personal', 'view', '/liveboard/views/0', 'view-private'),
        row('public', 'view', '/liveboard/views/1', 'view-public'),
        row('external-python', 'unknown', None)]
    items[-1]['disposition'] = 'unsupported'
    return {'schema_version': V.SCHEMA,
        'identity': {'source_origin': 'https://thoughtspot.example.invalid', 'org_id': 'org-one',
            'product': 'cloud', 'version': '26.9-synthetic', 'principal_ref': 'synthetic-reader',
            'chart_generation': 'new', 'reference': 'Synthetic version evidence'},
        'root': {'kind': 'liveboard', 'id': 'board-one'},
        'objects': [{'kind': 'liveboard', 'id': 'board-one', 'payload': {'guid': 'board-one', 'liveboard': body},
                     'evidence_ref': 'synthetic-native-json'},
                    {'kind': 'table', 'id': 'table-one', 'payload': {'guid': 'table-one', 'table': {'name': 'Garden'}},
                     'evidence_ref': 'synthetic-table-json'}],
        'inventory': {'reference': 'Synthetic independent enumeration', 'completeness': 'selected_scope_declared', 'items': items},
        'gaps': ['Synthetic fixture; no actual tenant or user approval', 'Python visual unavailable in JSON TML']}


def prepare(root, transform=None):
    """Actual passive capture intake of original synthetic files for shared tests."""
    C = load('thoughtspot_capture')
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
    manifest = {'schema_version': 'thoughtspot-originals.v1', 'reference': 'Synthetic transfer', 'records': records}
    (supplied / 'snapshot.json').write_bytes(V.encoded(snapshot)); (supplied / 'originals.json').write_bytes(V.encoded(manifest))
    request = {'schema_version': C.REQUEST_SCHEMA, 'capture_id': 'synthetic-thoughtspot',
        'identity': copy.deepcopy(snapshot['identity']), 'root': copy.deepcopy(snapshot['root']),
        'authorization_ref': 'Synthetic intake only', 'credential_ref': None, 'evidence_mode': 'synthetic_fixture',
        'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': {'filters': {'district': 'West'}, 'parameters': {'threshold': 3}, 'timezone': 'UTC', 'locale': 'en-US',
                  'principal': 'synthetic-reader', 'cache': 'source-cache-disabled', 'reference': 'Synthetic requested state'},
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json'}
    out = C.import_local(request, supplied, root / 'capture', allow_source_read=True)
    return request, out


def add_results(root, request, out, transform=None):
    C = load('thoughtspot_capture')
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
    return raw, C.import_evidence(out['output'], {'schema_version': 'thoughtspot-supplied-evidence.v1', 'attachments': [row]}, source)


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


class ThoughtSpotVisualTests(unittest.TestCase):
    def test_native_inline_answer_placements_notes_controls_and_unknowns_survive(self):
        value = snapshot_fixture(); result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        indexed = {a['source_identity'].get('object_key'): a for a in result['assets']}
        self.assertEqual(result['thoughtspot_coverage']['independently_enumerated'], 12)
        self.assertEqual(result['thoughtspot_coverage']['native_unmapped'], 0)
        self.assertTrue(indexed['left']['source_identity']['query_visual'])
        self.assertTrue(indexed['right']['source_identity']['query_visual'])
        self.assertFalse(indexed['note-place']['source_identity']['query_visual'])
        self.assertIsNone(indexed['units']['source_identity']['answer_guid'])
        self.assertEqual(indexed['units']['source_identity']['viz_guid'], 'viz-one')
        self.assertEqual(indexed['units']['source_identity']['visualization_id'], 'Viz_1')
        self.assertEqual(indexed['external-python']['kind'], 'unknown')
        self.assertEqual(result['upstream_payload'], value)
        self.assertFalse(result['migration_context']['target_write_authority'])

    def test_omitted_native_note_view_and_placement_become_explicit_obligations(self):
        value = snapshot_fixture()
        value['inventory']['items'] = [r for r in value['inventory']['items'] if r['key'] not in ('right', 'personal', 'note-place')]
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        self.assertEqual(result['thoughtspot_coverage']['native_unmapped'], 3)
        obligations = [a for a in result['assets'] if a['source_identity']['id_kind'] == 'native_locator_unmapped']
        self.assertEqual(len(obligations), 3)
        self.assertTrue(any(a['source_identity']['restricted_private_scope'] for a in obligations))

    def test_private_native_view_cannot_be_relabelled_public_by_projection(self):
        value = snapshot_fixture(); private = value['inventory']['items'][9]
        private['configuration']['private_view'] = False; private['kind'] = 'content'
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        indexed = {a['source_identity'].get('object_key'): a for a in result['assets']}
        self.assertTrue(indexed['personal']['source_identity']['restricted_private_scope'])
        self.assertFalse(indexed['public']['source_identity']['restricted_private_scope'])
        private['configuration']['selection_reference'] = 'Synthetic explicit selection for this view only'
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        self.assertFalse(next(a for a in result['assets'] if a['source_identity'].get('object_key') == 'personal')['source_identity']['restricted_private_scope'])

    def test_wrong_native_identity_pointer_and_duplicate_mapping_rejected(self):
        for change in (lambda x: x['objects'][0]['payload'].update(guid='other'),
            lambda x: x['inventory']['items'][1].update(native_id='other'),
            lambda x: x['inventory']['items'][1]['source_mapping'].update(pointer='/missing'),
            lambda x: x['inventory']['items'][5]['source_mapping'].update(pointer='/liveboard/layout/tabs/0/tiles/0'),
            lambda x: x['inventory']['items'][5]['configuration'].update(visual_key='note')):
            value = snapshot_fixture(); change(value)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_scope_type_cycles_credentials_and_malformed_collections_rejected(self):
        for change in (lambda x: x['identity'].update(org_id=3), lambda x: x['identity'].update(source_origin='http://invalid.example'),
            lambda x: x['inventory']['items'][3].update(parent_key='left'),
            lambda x: x['inventory'].update(items={}),
            lambda x: x['objects'].append(copy.deepcopy(x['objects'][0])),
            lambda x: x['objects'][0]['payload'].update(password='synthetic-placeholder')):
            value = snapshot_fixture(); change(value)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_client_state_strict_json_and_inert_formulas_search_are_preserved(self):
        value = snapshot_fixture(); answer = value['objects'][0]['payload']['liveboard']['visualizations'][0]['answer']
        answer['formulas'][0]['expr'] = 'scriptlike(fetch("https://invalid.example"))'
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        visual = next(a for a in result['assets'] if a['source_identity'].get('object_key') == 'units')
        self.assertEqual(visual['facets']['visual']['value']['client_state'][0]['status'], 'json_data_only')
        self.assertEqual(visual['facets']['query']['status'], 'needs_review')
        self.assertFalse(result['source_execution'])
        for state in ('{"x":1,"x":2}', '{x: function(){return 2}}', '[1,2]'):
            answer['chart']['client_state'] = state
            result = V.parse_snapshot(value, V.encoded(value), HELPERS)
            self.assertIn('thoughtspot.client_state_opaque', {g['code'] for g in result['gaps']})

    def test_standalone_answer_keeps_saved_guid_without_fabricated_liveboard(self):
        value = snapshot_fixture(); answer = value['objects'][0]['payload']['liveboard']['visualizations'][0]['answer']
        value['root'] = {'kind': 'answer', 'id': 'answer-one'}
        value['objects'] = [{'kind': 'answer', 'id': 'answer-one', 'payload': {'guid': 'answer-one', 'answer': answer}, 'evidence_ref': 'Synthetic saved answer'}]
        row = value['inventory']['items'][0]
        row.update(kind='answer', native_id='answer-one', source_mapping={'object_kind': 'answer', 'object_id': 'answer-one', 'pointer': ''})
        value['inventory']['items'] = [row]
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        self.assertEqual([a['kind'] for a in result['assets']], ['visual'])
        self.assertEqual(result['assets'][0]['source_identity']['answer_guid'], 'answer-one')

    def test_unknown_native_shapes_and_fields_remain_original_not_dropped(self):
        value = snapshot_fixture(); board = value['objects'][0]['payload']['liveboard']
        board['visualizations'].append({'id': 'Future_3', 'future_widget': {'expression': 'not_executed'}})
        board['future_config'] = {'preserve': True}
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        self.assertEqual(result['thoughtspot_coverage']['native_unmapped'], 1)
        self.assertEqual(result['upstream_payload']['objects'][0]['payload']['liveboard']['future_config'], {'preserve': True})

    def test_unknown_object_or_future_subtree_cannot_be_promoted_to_query_visual(self):
        for unknown_object in (True, False):
            value = snapshot_fixture()
            native = {'answer': copy.deepcopy(value['objects'][0]['payload']['liveboard']['visualizations'][0]['answer'])}
            row = next(r for r in value['inventory']['items'] if r['key'] == 'external-python')
            row.update(kind='visual', disposition='include')
            if unknown_object:
                value['objects'].append({'kind': 'unknown', 'id': 'future-one', 'payload': native,
                    'evidence_ref': 'Synthetic unqualified object'})
                row['source_mapping'] = {'object_kind': 'unknown', 'object_id': 'future-one', 'pointer': ''}
            else:
                value['objects'][0]['payload']['liveboard']['future_widget'] = native
                row['source_mapping'] = {'object_kind': 'liveboard', 'object_id': 'board-one', 'pointer': '/liveboard/future_widget'}
            result = V.parse_snapshot(value, V.encoded(value), HELPERS)
            asset = next(a for a in result['assets'] if a['source_identity'].get('object_key') == row['key'])
            with self.subTest(unknown_object=unknown_object):
                self.assertFalse(asset['source_identity']['query_visual'])
                self.assertIn('thoughtspot.query_visual_definition_unqualified', {g['code'] for g in result['gaps']})
                self.assertEqual(result['upstream_payload'], value)

    def test_native_query_visual_cannot_be_hidden_as_content_or_note_promoted(self):
        for key, kind in [('units', 'content'), ('note', 'visual')]:
            value = snapshot_fixture()
            next(r for r in value['inventory']['items'] if r['key'] == key)['kind'] = kind
            with self.subTest(key=key), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_logical_data_and_excluded_filter_references_are_not_name_resolved(self):
        value = snapshot_fixture()
        value['objects'][0]['payload']['liveboard']['visualizations'][0]['answer']['tables'][0]['id'] = 'absent-table'
        value['objects'][0]['payload']['liveboard']['filters'][0]['excluded_visualizations'].append('absent-viz')
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        unknown = [d for d in result['dependencies'] if d['status'] == 'unresolved']
        self.assertEqual({d['kind'] for d in unknown}, {'logical_data_object', 'excluded_local_visual'})
        self.assertIn('thoughtspot.native_dependency_unresolved', {g['code'] for g in result['gaps']})

    def test_logical_dependency_requires_one_matching_logical_object_kind(self):
        for kind in ('answer', 'liveboard', 'unknown', 'table', 'worksheet', 'model', 'view'):
            value = snapshot_fixture()
            value['objects'][1] = {'kind': kind, 'id': 'table-one',
                'payload': {'guid': 'table-one', kind: {'name': 'Same identifier'}},
                'evidence_ref': 'Synthetic type resolution'}
            V.validate_snapshot(value)
            dependency = next(d for d in V.native_dependencies(value) if d['kind'] == 'logical_data_object')
            with self.subTest(kind=kind):
                self.assertEqual(dependency['status'], 'declared' if kind in ('table', 'worksheet', 'model', 'view') else 'unresolved')
        value = snapshot_fixture()
        value['objects'].append({'kind': 'model', 'id': 'table-one',
            'payload': {'guid': 'table-one', 'model': {}}, 'evidence_ref': 'Synthetic ambiguous identity'})
        self.assertEqual(next(d for d in V.native_dependencies(value) if d['kind'] == 'logical_data_object')['status'], 'unresolved')

    def test_private_ancestor_and_linked_target_restriction_propagates_to_placement(self):
        value = snapshot_fixture()
        rows = {r['key']: r for r in value['inventory']['items']}
        rows['units']['parent_key'] = 'personal'
        # A child declaration cannot select its private ancestor on the user's behalf.
        rows['units']['configuration']['selection_reference'] = 'Synthetic child-only declaration'
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        indexed = {a['source_identity'].get('object_key'): a for a in result['assets']}
        for key in ('personal', 'units', 'left', 'right'):
            with self.subTest(key=key):
                self.assertTrue(indexed[key]['source_identity']['restricted_private_scope'])
                self.assertFalse(indexed[key]['source_identity']['query_visual'])
                self.assertTrue(indexed[key]['facets']['security']['value']['restricted_private_scope'])
        rows['personal']['configuration']['selection_reference'] = 'Synthetic explicit private-view selection'
        result = V.parse_snapshot(value, V.encoded(value), HELPERS)
        indexed = {a['source_identity'].get('object_key'): a for a in result['assets']}
        self.assertTrue(indexed['left']['source_identity']['query_visual'])
        self.assertFalse(indexed['left']['source_identity']['restricted_private_scope'])

    def test_real_capture_roundtrip_preserves_pins_and_private_obligations(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out = prepare(tmp)
            self.assertEqual(V.verify_capture_files(out['capture'], Path(out['output']).parent)['status'], 'verified_local_bytes')
            result = V.parse_capture(out['capture'], V.encoded(out['capture']), HELPERS)
            self.assertEqual(result['source']['definition_fingerprint'], V.sha(out['capture']['source']['snapshot']))
            self.assertFalse(result['build_authority'])

    def test_numeric_identity_placement_and_raw_evidence_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp)
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target), [])
            changed = copy.deepcopy(asset); changed['source_identity']['org_id'] = 'other'
            with self.assertRaisesRegex(ValueError, 'case_identity'): V.case_binding(changed, case, capture)
            changed = copy.deepcopy(case); changed['source_binding']['placement_key'] = 'right'
            with self.assertRaisesRegex(ValueError, 'case_binding'): V.case_binding(asset, changed, capture)
            changed = copy.deepcopy(source); changed['file']['sha256'] = '0' * 64
            self.assertIn('source.thoughtspot_result_not_bound', V.comparison_gaps(capture, asset, case, changed, target))

    def test_target_cache_can_differ_but_population_and_watermark_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp)
            target['context']['cache'] = 'independently-selected-target-policy'
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target), [])
            target['context']['data_watermark'] = 'older'
            self.assertIn('context.data_watermark', V.comparison_gaps(capture, asset, case, source, target))
            source['context']['parameters'] = {}
            self.assertIn('source.thoughtspot_observed.parameters', V.comparison_gaps(capture, asset, case, source, target))

    def test_preview_limit_stage_and_missing_observation_keep_comparison_honest(self):
        def preview(value):
            value['inventory']['items'][1]['configuration']['result_contract'].update(
                data_mode='preview', row_limit=100, row_limit_stage='before_aggregation')
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp, preview)
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target), [])
            target['context']['row_limit_stage'] = 'after_aggregation'
            self.assertIn('context.row_limit_stage', V.comparison_gaps(capture, asset, case, source, target))
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp,
                evidence_transform=lambda row: row['observed_state'].pop('result_context'))
            self.assertIn('source.thoughtspot_observed_result_context_missing', V.comparison_gaps(capture, asset, case, source, target))

    def test_note_and_unselected_private_view_cannot_bind_numeric_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, _, case, _, _, _ = comparison_fixture(tmp)
            result = V.parse_capture(capture, V.encoded(capture), HELPERS)
            indexed = {a['source_identity'].get('object_key'): a for a in result['assets']}
            private_case = copy.deepcopy(case); private_case['source_binding'].update(object_key='personal', placement_key=None, attachment_id=None)
            with self.assertRaisesRegex(ValueError, 'case_scope'): V.case_binding(indexed['personal'], private_case, capture)
            note_case = copy.deepcopy(case); note_case['source_binding'].update(object_key='note', placement_key='note-place', attachment_id=None)
            with self.assertRaisesRegex(ValueError, 'case_numeric_evidence'): V.case_binding(indexed['note-place'], note_case, capture)

    def test_normalization_preserves_exact_decimal_and_original_binding(self):
        raw = b'district,units\nWest,1.100000000000000001\n'
        binding = {'capture_content_hash': '1' * 64, 'definition_fingerprint': '2' * 64, 'object_key': 'units',
            'attachment_id': 'result-one', 'state_sha256': '3' * 64, 'attachment_sha256': V.sha(raw)}
        profile = {'schema_version': 1, 'format': 'csv', 'encoding': 'utf-8', 'subtotal_policy': 'preserve',
            'headers': ['district', 'units'], 'columns': [
                {'ordinal': 0, 'name': 'district', 'type': 'string', 'null_tokens': [], 'nullable': False},
                {'ordinal': 1, 'name': 'units', 'type': 'number', 'null_tokens': [], 'nullable': False,
                 'decimal_separator': '.', 'group_separator': None, 'percent': False}]}
        normalized = V.normalize_results(raw, profile, binding)
        self.assertEqual(normalized['rows'][0]['units'], '1.100000000000000001')
        self.assertEqual(normalized['kind'], 'thoughtspot_normalized_results')
        binding['attachment_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'normalization_binding'): V.normalize_results(raw, profile, binding)

    def test_compact_matrix_normalization_preserves_ids_precision_and_raw_provenance(self):
        raw, profile, binding = compact_result_fixture()
        result = V.normalize_results(raw, profile, binding)
        self.assertEqual(result['rows'], [
            {'district': 'West', 'count': '9007199254740993', 'volume': '1.100000000000000001', 'enabled': True},
            {'district': 'East', 'count': '0', 'volume': None, 'enabled': False}])
        self.assertEqual(result['raw_sha256'], V.sha(raw))
        self.assertEqual(result['parser_profile'], profile)
        self.assertEqual(result['binding'], binding)
        self.assertEqual(result['completeness'], 'not_established')
        derived, _ = V.compact_projection(raw, profile)
        self.assertEqual(result['projection']['sha256'], V.sha(derived))
        self.assertEqual(result, V.normalize_results(raw, profile, binding))

    def test_compact_matrix_rejects_ambiguous_columns_ragged_data_and_non_json_numbers(self):
        raw, profile, binding = compact_result_fixture()
        profile_changes = [
            lambda p: p.update(headers_pointer='/missing'),
            lambda p: p.update(header_id_key='unknown-id'),
            lambda p: p.update(column_ids=['unknown-id', *p['column_ids'][1:]]),
            lambda p: p['column_ids'].reverse(),
            lambda p: p['column_ids'].__setitem__(1, p['column_ids'][0]),
            lambda p: p['headers'].__setitem__(1, p['headers'][0]),
            lambda p: p['columns'][1].update(type='guessed'),
            lambda p: p.update(shape='auto')]
        for change in profile_changes:
            changed = copy.deepcopy(profile); change(changed)
            with self.subTest(change=change), self.assertRaises(ValueError): V.normalize_results(raw, changed, binding)
        invalid = [raw.replace(b'9007199254740993,', b''),
                   raw.replace(b'9007199254740993', b'{"nested":1}'),
                   raw.replace(b'9007199254740993', b'NaN'),
                   raw.replace(b'"count-id"', b'"district-id"'),
                   raw.replace(b'{"column_id":"count-id"}', b'{"column_id":"count-id","column_id":"other"}')]
        for changed in invalid:
            with self.subTest(raw=changed), self.assertRaises(ValueError):
                V.normalize_results(changed, profile, {**binding, 'attachment_sha256': V.sha(changed)})

    def test_matrix_completeness_profile_is_bound_to_numeric_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp)
            raw, profile, _ = compact_result_fixture()
            folder = Path(tmp).resolve() / 'matrix'; folder.mkdir(); (folder / 'matrix.json').write_bytes(raw)
            fields = ('object_key', 'origin', 'result_scope', 'observed_state', 'population', 'freshness', 'completeness', 'reference')
            row = {k: copy.deepcopy(capture['attachments'][0][k]) for k in fields}
            row.update(attachment_id='matrix-one', format='json', source_path='matrix.json', member_path=None, parser_profile=profile)
            C = load('thoughtspot_capture')
            out = C.import_evidence(case['source_capture']['path'],
                {'schema_version': 'thoughtspot-supplied-evidence.v1', 'attachments': [row]}, folder)
            capture = out['capture']; attachment = capture['attachments'][-1]
            case['source_capture'] = {'path': out['output'], 'sha256': V.sha(Path(out['output']).read_bytes())}
            case['source_binding']['attachment_id'] = 'matrix-one'
            source.update(format='thoughtspot-normalized', raw_file={'path': attachment['path'], 'sha256': attachment['sha256']})
            binding = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': capture['source']['definition_fingerprint'],
                'object_key': 'units', 'attachment_id': 'matrix-one', 'state_sha256': V.sha(capture['request']['state']),
                'attachment_sha256': V.sha(raw)}
            normalized = V.normalize_results(raw, profile, binding)
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target, normalized), [])
            changed = copy.deepcopy(normalized); changed['parser_profile']['rows_pointer'] = '/other/result'
            self.assertIn('source.thoughtspot_observed_parser_profile_changed',
                          V.comparison_gaps(capture, asset, case, source, target, changed))


if __name__ == '__main__':
    unittest.main()
