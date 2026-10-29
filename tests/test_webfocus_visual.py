"""Original synthetic WebFOCUS bridge fixtures; no DMA/vendor imports or calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-translator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('test_webfocus_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


V, T = load('webfocus_visual'), load('translate_artifact')
HELPERS = {'base': T.base, 'add_asset': T.add_asset, 'gap': T.gap, 'facet': T.facet}


def result_contract():
    return {'data_mode': 'full_data', 'row_limit': None, 'row_limit_stage': 'none',
            'aggregation_stage': 'native_report', 'reference': 'Synthetic observed result semantics'}


def report_fixture(extra_graph=False):
    """Hand-authored shape of the exact producer contract, not an executed producer."""
    source = 'TABLE FILE garden\nSUM QUANTITY BY REGION\nEND\n'
    if extra_graph:
        source += '''GRAPH FILE garden
SUM QUANTITY BY REGION
ON GRAPH SET STYLE *
TYPE=REPORT, COLOR='navy', $
TYPE=REPORT, COLOR='teal', $
*GRAPH_JS
{"legend":{"visible":true},"labels":["Region","Quantity"]}
*END
ENDSTYLE
END
'''
    blobs = {'apps/one/report.fex': source.encode(), 'unknown/layout.xml': b'<inert supplied="true" />'}
    def evidence(path, locator):
        return {'path': path, 'locator': locator, 'sha256': V.sha(blobs[path])}
    path = 'apps/one/report.fex'
    def obj(kind, name, locator, native_id=None, **details):
        return {'id': V._generated_id('object', path, locator, native_id if native_id is not None else name),
                'native_id': native_id, 'kind': kind, 'name': name, 'evidence': evidence(path, locator), 'details': details}
    procedure = obj('procedure', path, '$', source_path=path)
    request = obj('report_request', 'garden', 'line:1', parent_id=procedure['id'], native_source='garden')
    expressions = [{'id': V._generated_id('expression', path, '$source', source), 'object_id': None,
        'language': 'webfocus:fex', 'text': source, 'content_sha256': V.sha(source.encode()),
        'evidence': evidence(path, '$source'), 'details': {'interpretation': 'preserved_original'}}]
    dependencies = [{'source_id': request['id'], 'target': 'garden', 'evidence': evidence(path, 'line:1'),
        'details': {'kind': 'master_file', 'native_reference': 'garden', 'resolution': 'unresolved'}}]
    gaps = [{'code': 'webfocus.runtime_context_unverified', 'message': 'Synthetic runtime remains unverified.',
        'evidence': evidence(path, '$')}, {'code': 'webfocus.unsupported_format', 'message': 'Opaque XML retained.',
        'evidence': evidence('unknown/layout.xml', '$')}]
    value = {'schema_version': 1, 'kind': 'source_adapter_result', 'source': 'webfocus', 'adapter_version': 1,
        'source_files': [{'path': p, 'sha256': V.sha(raw), 'status': 'partial' if p.endswith('.fex') else 'unsupported',
                         'reason': 'Original synthetic source evidence'} for p, raw in blobs.items()],
        'coverage_summary': {'unit': 'supplied_source_files', 'expected': 2, 'observed': 2, 'missing': 0,
                             'statuses': {'parsed': 0, 'partial': 1, 'unsupported': 1}},
        'objects': [procedure, request], 'expressions': expressions, 'dependencies': dependencies, 'gaps': gaps,
        'export_completeness': 'not_established', 'native_validation': 'not_run', 'execution_performed': False,
        'limitations': ['Synthetic fixture; no native execution or actual tenant'], 'component_sha256': 'a' * 64}
    bind_occurrences(value)
    return blobs, value


def bind_occurrences(value):
    for category in ('objects', 'expressions', 'dependencies', 'gaps'):
        positions = {}
        for row in value[category]:
            e = row['evidence']; position = (e['path'], e['locator']); ordinal = positions.get(position, 0)
            material = json.dumps([category, *position, ordinal], ensure_ascii=True).encode()
            row['occurrence_id'] = 'webfocus:occurrence:' + hashlib.sha256(material).hexdigest()[:24]
            positions[position] = ordinal + 1


def prepare(root, with_adapter=True, inventory_transform=None):
    """Shared original synthetic capture for integration tests; no source runtime."""
    C = load('webfocus_capture')
    root = Path(root).resolve(); supplied = root / 'supplied'; supplied.mkdir(parents=True)
    blobs, report = report_fixture(True)
    for path, raw in blobs.items():
        (supplied / path).parent.mkdir(parents=True, exist_ok=True); (supplied / path).write_bytes(raw)
    originals = {'schema_version': 'webfocus-originals.v1', 'reference': 'Synthetic selected originals', 'records': [
        {'source_path': p, 'kind': 'fex' if p.endswith('.fex') else 'opaque', 'encoding': 'utf-8',
         'sha256': V.sha(raw), 'reference': 'Synthetic original bytes'} for p, raw in blobs.items()]}
    def item(key, kind, target=None):
        return {'key': key, 'kind': kind, 'name': key, 'parent_key': None if key == 'page' else 'page',
            'source_object_id': report['objects'][1]['id'] if with_adapter and kind == 'visual' else None,
            'disposition': 'include', 'disposition_reference': 'Synthetic requested scope',
            'evidence_reference': 'Synthetic independent listing', 'configuration': {'visual_key': target} if target else {}}
    inventory = {'schema_version': 'webfocus-source-enumeration.v1', 'method': 'separate_source_enumeration',
        'reference': 'Synthetic independent source listing', 'completeness': 'selected_scope_declared',
        'objects': [item('page', 'page'), item('quantity', 'visual'), item('left', 'placement', 'quantity'),
                    item('right', 'placement', 'quantity'), item('region', 'control'), item('note', 'content'),
                    item('note-place', 'placement', 'note'), item('unknown', 'unknown')]}
    inventory['objects'][1]['configuration']['result_contract'] = result_contract()
    inventory['objects'][6]['configuration'] = {'content_key': 'note'}
    if inventory_transform is not None:
        inventory_transform(inventory)
    crosswalk = {'schema_version': 'webfocus-identity-crosswalk.v1', 'reference': 'Synthetic scope crosswalk', 'rows': [
        {'key': o['key'], 'resource_path': '/WFC/Repository/synthetic/' + o['key'],
         'source_object_id': o['source_object_id'], 'reference': 'Synthetic resource identity'} for o in inventory['objects']]}
    req = {'schema_version': C.REQUEST, 'capture_id': 'synthetic-webfocus', 'product': 'webfocus',
        'source_origin': 'https://webfocus.example.invalid', 'product_version': '9-synthetic',
        'product_evidence_ref': 'Synthetic version evidence', 'principal_ref': 'synthetic-reader',
        'authorization_ref': 'Synthetic authorized supplied transfer', 'credential_ref': None,
        'evidence_mode': 'synthetic_fixture', 'source_revision': {'kind': 'supplied_snapshot', 'value': 'fixture-v1',
            'reference': 'Synthetic source revision'}, 'root_key': 'page', 'route': 'unselected', 'route_reference': None,
        'target_surface': 'both', 'state': {'filters': {'region': 'West'}, 'parameters': {'REGION': 'West'},
            'timezone': 'UTC', 'locale': 'en-US', 'principal': 'synthetic-reader', 'cache': 'source-cache-disabled',
            'reference': 'Synthetic requested state'}, 'originals_path': 'originals.json',
        'inventory_path': 'inventory.json', 'crosswalk_path': 'crosswalk.json'}
    for name, value in [('originals', originals), ('inventory', inventory), ('crosswalk', crosswalk)]:
        (supplied / (name + '.json')).write_bytes(V.encoded(value))
    if with_adapter:
        req.update(adapter_report_path='adapter.json', producer_revision=V.DMA_REVISION)
        (supplied / 'adapter.json').write_bytes(V.encoded(report))
    out = C.import_local(req, supplied, root / 'capture', allow_source_read=True)
    return req, out


def add_results(root, req, out, observation_transform=None):
    C = load('webfocus_capture')
    source = Path(root).resolve() / 'results'; source.mkdir()
    raw = b'region,quantity\nWest,1.100000000000000001\nEast,2.00\n'
    (source / 'rows.csv').write_bytes(raw)
    row = {'attachment_id': 'result-one', 'object_key': 'quantity', 'format': 'csv', 'source_path': 'rows.csv',
        'origin': 'full', 'result_scope': 'query_result',
        'observed_state': {'state': copy.deepcopy(req['state']), 'observed_at': '2026-01-01T00:00:00Z',
            'reference': 'Synthetic observed state', 'placement_reference': 'Synthetic left/right parameter application',
            'result_context': copy.deepcopy(next(o for o in out['capture']['source']['inventory']['objects']
                                                if o['key'] == 'quantity')['configuration']['result_contract'])},
        'population': {'key': 'synthetic-all-rows', 'description': 'All synthetic rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic watermark'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic full export'},
        'reference': 'Synthetic result export'}
    if observation_transform is not None:
        observation_transform(row)
    return raw, C.import_evidence(out['output'], {'schema_version': 'webfocus-supplied-evidence.v1', 'attachments': [row]}, source)


def comparison_fixture(root, inventory_transform=None, observation_transform=None):
    req, out = prepare(root, inventory_transform=inventory_transform)
    raw, out = add_results(root, req, out, observation_transform)
    capture = out['capture']
    projected = V.parse_capture(capture, V.encoded(capture), HELPERS)
    asset = next(a for a in projected['assets'] if a['source_identity'].get('object_key') == 'left')
    pin = capture['attachments'][0]
    binding = {'object_key': 'quantity', 'placement_key': 'left', 'state_sha256': V.sha(req['state']),
               'definition_fingerprint': capture['source']['definition_fingerprint'], 'attachment_id': pin['attachment_id']}
    case = {'lane': 'numeric', 'source_binding': binding, 'source_capture': {'path': out['output'],
            'sha256': V.sha(Path(out['output']).read_bytes())}}
    context = {**copy.deepcopy(req['state']), 'population': pin['population']['key'],
        'data_watermark': pin['freshness']['data_watermark'], 'freshness_reference': pin['freshness']['reference'],
        'result_scope': pin['result_scope']}
    observed_result = pin['observed_state'].get('result_context')
    if observed_result:
        context.update({k: v for k, v in observed_result.items() if k != 'reference'})
        context['result_context_reference'] = observed_result['reference']
    source = {'format': 'csv', 'file': {'path': pin['path'], 'sha256': pin['sha256']}, 'context': context}
    target = {'format': 'csv', 'file': {'path': 'target.csv', 'sha256': pin['sha256']}, 'context': copy.deepcopy(context)}
    return req, capture, asset, case, source, target, raw


class WebFOCUSVisualTests(unittest.TestCase):
    def test_exact_adapter_projects_obligations_and_preserves_identity(self):
        blobs, report = report_fixture(True)
        out = V.parse_adapter(report, V.encoded(report), HELPERS, V.DMA_REVISION)
        self.assertEqual(out['source']['platform'], 'webfocus')
        self.assertEqual(out['upstream_expressions'], report['expressions'])
        self.assertEqual(out['dependencies'], report['dependencies'])
        self.assertEqual(len(out['assets']), 4)
        self.assertTrue(all(a['kind'] == 'definition' and a['source_identity']['query_visual'] is False for a in out['assets']))
        self.assertTrue(any(a['source_identity'].get('report_obligation') for a in out['assets']))
        self.assertFalse(out['build_authority']); self.assertFalse(out['migration_context']['target_write_authority'])
        self.assertEqual(out['source']['producer']['component_sha256'], 'a' * 64)
        self.assertEqual(out['source']['producer']['reviewed_component_file_pins'], V.PRODUCERS[V.DMA_REVISION])
        self.assertIn('webfocus.visual_denominator_not_established', {g['code'] for g in out['gaps']})
        self.assertEqual(len(out['webfocus_visual_declarations'][0]['graph_requests']), 1)
        V.validate(report, V.PRIVATE_REVISION)

    def test_forged_producer_schema_claims_and_component_pin_rejected(self):
        _, report = report_fixture()
        with self.assertRaisesRegex(ValueError, 'producer_revision'): V.validate(report, '0' * 40)
        for key, val in [('source', 'tableau'), ('schema_version', True), ('adapter_version', 2),
                         ('execution_performed', True), ('native_validation', 'passed'),
                         ('export_completeness', 'complete'), ('component_sha256', 'bad')]:
            candidate = copy.deepcopy(report); candidate[key] = val
            with self.subTest(key=key), self.assertRaises(ValueError): V.validate(candidate, V.DMA_REVISION)

    def test_expression_occurrence_generated_identity_and_owner_integrity(self):
        _, report = report_fixture()
        mutations = [lambda x: x['expressions'][0].update(text='changed'),
            lambda x: x['expressions'][0].update(occurrence_id='webfocus:occurrence:' + 'a' * 24),
            lambda x: x['objects'][0].update(id='webfocus:object:' + 'b' * 24),
            lambda x: x['objects'][1]['details'].update(parent_id='absent'),
            lambda x: x['dependencies'][0].update(source_id='absent'),
            lambda x: x['dependencies'][0]['details'].update(resolution='resolved'),
            lambda x: x['expressions'][0]['evidence'].update(sha256='c' * 64)]
        for change in mutations:
            candidate = copy.deepcopy(report); change(candidate)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate(candidate, V.DMA_REVISION)

    def test_file_denominator_raw_source_and_credentials_fail_closed(self):
        _, report = report_fixture()
        for change in [lambda x: x['source_files'].pop(), lambda x: x['expressions'].clear(),
                       lambda x: x['source_files'][0].update(path='../report.fex'),
                       lambda x: x['objects'][0]['details'].update(password='synthetic-secret'),
                       lambda x: x['coverage_summary'].update(expected=999),
                       lambda x: x['source_files'][0].update(status='parsed')]:
            candidate = copy.deepcopy(report); change(candidate)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate(candidate, V.DMA_REVISION)

    def test_literal_graph_ordered_style_and_strict_json_preserved(self):
        _, report = report_fixture(True)
        declaration = V.visual_declarations(report)[0]
        graph = declaration['graph_requests'][0]
        self.assertEqual(graph['native_source'], 'garden')
        records = declaration['style_blocks'][0]['records']
        self.assertEqual([r['attributes'][1]['value'] for r in records], ["'navy'", "'teal'"])
        self.assertEqual([r['sequence'] for r in records], [0, 1])
        self.assertEqual(declaration['graph_js_blocks'][0]['data']['legend'], {'visible': True})
        self.assertEqual(declaration['graph_js_blocks'][0]['interpretation'], 'strict_json_data_only')
        self.assertFalse(declaration['execution_performed'])

    def test_dynamic_graph_custom_javascript_and_external_styles_remain_opaque(self):
        source = '''GRAPH FILE &SOURCE
ON GRAPH SET STYLE external.sty
-INCLUDE secret/profile
*GRAPH_JS
{legend: {visible: true}, callback: function(){ fetch('https://invalid.example'); }}
*END
END
'''
        out = V.inspect_fex(source, 'inert.fex')
        self.assertIsNone(out['graph_requests'][0]['native_source'])
        self.assertIsNone(out['graph_js_blocks'][0]['data'])
        codes = {g['code'] for g in out['gaps']}
        self.assertTrue({'webfocus.graph_dynamic_or_opaque', 'webfocus.external_or_opaque_style_not_loaded',
                         'webfocus.visual_runtime_context_opaque', 'webfocus.graph_js_opaque_or_dynamic'} <= codes)

    def test_duplicate_json_keys_unterminated_blocks_and_limits_are_gaps(self):
        for source, expected in [
            ('*GRAPH_JS\n{"a":1,"a":2}\n*END', 'webfocus.graph_js_opaque_or_dynamic'),
            ('*GRAPH_JS\n{"a":1}', 'webfocus.graph_js_unterminated'),
            ('ON GRAPH SET STYLE *\nTYPE=REPORT,COLOR=red,$', 'webfocus.style_unterminated'),
            ('ON GRAPH SET STYLE *\nTYPE=REPORT,COLOR=red\nENDSTYLE', 'webfocus.style_unterminated_record'),
            ('PRINT X\n' * 802, 'webfocus.visual_structure_limit'),
            ('ON GRAPH SET STYLE *\n' + 'TYPE=X,$' * 801 + '\nENDSTYLE', 'webfocus.style_malformed_literal')]:
            with self.subTest(expected=expected):
                out = V.inspect_fex(source, 'inert.fex')
                self.assertIn(expected, {g['code'] for g in out['gaps']})

    def test_legacy_graph_script_is_retained_without_interpretation(self):
        for ending in ('\n*END\nENDSTYLE', ''):
            source = 'GRAPH FILE garden\nON GRAPH SET STYLE *\n*GRAPH_SCRIPT\nsetDepth(3);\n\n-* inert legacy comment' + ending
            out = V.inspect_fex(source, 'legacy.fex')
            block = out['graph_script_blocks'][0]
            self.assertEqual(block['start_line'], 3)
            self.assertEqual(block['style_start_line'], 2)
            self.assertEqual(block['original_text'], 'setDepth(3);\n\n-* inert legacy comment')
            self.assertEqual(block['interpretation'], 'opaque')
            self.assertEqual(block['terminated'], bool(ending))
            codes = {g['code'] for g in out['gaps']}
            self.assertIn('webfocus.graph_script_unsupported', codes)
            if not ending: self.assertIn('webfocus.graph_script_unterminated', codes)
            self.assertFalse(out['execution_performed'])

    def test_independent_capture_counts_repeated_and_content_placements(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out = prepare(tmp)
            capture = out['capture']
            result = V.parse_capture(capture, V.encoded(capture), HELPERS)
            self.assertEqual(result['webfocus_coverage']['enumerated_objects'], 8)
            self.assertEqual(result['webfocus_coverage']['placements'], 3)
            selected = {a['source_identity'].get('object_key'): a for a in result['assets']}
            self.assertTrue(selected['left']['source_identity']['query_visual'])
            self.assertTrue(selected['right']['source_identity']['query_visual'])
            self.assertFalse(selected['note-place']['source_identity']['query_visual'])
            self.assertEqual(result['migration_context']['route'], None)
            self.assertFalse(result['migration_context']['target_write_authority'])
            self.assertEqual(V.verify_capture_files(capture, Path(out['output']).parent)['status'], 'verified_local_bytes')
        with tempfile.TemporaryDirectory() as tmp:
            _, out = prepare(tmp, with_adapter=False)
            result = V.parse_capture(out['capture'], V.encoded(out['capture']), HELPERS)
            self.assertEqual(len(result['assets']), 8)
            self.assertFalse(result['build_authority'])
            self.assertEqual(len(result['webfocus_visual_declarations'][0]['graph_requests']), 1)

    def test_nested_containers_and_standalone_report_preserve_native_hierarchy(self):
        def hierarchy(inv):
            rows = inv['objects']
            for key, kind in [('section', 'section'), ('container', 'container'), ('parameter', 'parameter'),
                              ('action', 'action')]:
                row = copy.deepcopy(rows[0]); row.update(key=key, kind=kind, name=key, parent_key='page')
                rows.append(row)
            next(r for r in rows if r['key'] == 'container')['parent_key'] = 'section'
            next(r for r in rows if r['key'] == 'left')['parent_key'] = 'container'
        with tempfile.TemporaryDirectory() as tmp:
            _, out = prepare(tmp, inventory_transform=hierarchy)
            result = V.parse_capture(out['capture'], V.encoded(out['capture']), HELPERS)
            indexed = {a['source_identity'].get('object_key'): a for a in result['assets']}
            for key in ('section', 'container'):
                self.assertEqual(indexed[key]['kind'], 'layout')
                self.assertEqual(indexed[key]['source_identity']['native_kind'], key)
            self.assertEqual(indexed['left']['facets']['layout']['value']['parent_key'], 'container')
            self.assertEqual(indexed['parameter']['kind'], 'parameter')
            self.assertEqual(indexed['action']['kind'], 'action')
        def standalone(inv):
            row = inv['objects'][0]
            row.update(kind='visual', configuration={'artifact_type': 'report', 'result_contract': result_contract()})
            inv['objects'] = [row]
        with tempfile.TemporaryDirectory() as tmp:
            _, out = prepare(tmp, with_adapter=False, inventory_transform=standalone)
            result = V.parse_capture(out['capture'], V.encoded(out['capture']), HELPERS)
            self.assertEqual([a['kind'] for a in result['assets']], ['visual'])
            self.assertTrue(result['assets'][0]['source_identity']['query_visual'])
            self.assertEqual(result['webfocus_coverage']['pages'], 0)

    def test_observed_state_placement_cache_and_population_gate_numeric_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, capture, asset, case, source, target, raw = comparison_fixture(tmp)
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target), [])
            changed = copy.deepcopy(source); changed['context']['parameters']['REGION'] = 'East'
            self.assertIn('source.webfocus_observed.parameters', V.comparison_gaps(capture, asset, case, changed, target))
            changed = copy.deepcopy(target); changed['context']['cache'] = 'different-user-selected-target-cache'
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, changed), [])
            changed['context']['data_watermark'] = '2025-12-01'
            self.assertIn('context.data_watermark', V.comparison_gaps(capture, asset, case, source, changed))
            changed_case = copy.deepcopy(case); changed_case['source_binding']['placement_key'] = 'right'
            with self.assertRaisesRegex(ValueError, 'placement_mismatch'):
                V.case_binding(asset, changed_case, capture)
            stale = copy.deepcopy(asset); stale['source_identity']['definition_fingerprint'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'identity_mismatch'): V.case_binding(stale, case, capture)

    def test_deliberate_preview_requires_observed_limit_stage_and_population(self):
        def preview(inv):
            inv['objects'][1]['configuration']['result_contract'].update(
                data_mode='preview', row_limit=100, row_limit_stage='before_aggregation')
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp, preview)
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target), [])
            target['context']['row_limit_stage'] = 'after_aggregation'
            self.assertIn('context.row_limit_stage', V.comparison_gaps(capture, asset, case, source, target))
            target['context']['row_limit_stage'] = 'before_aggregation'
            target['context']['population'] = 'different-subset'
            self.assertIn('context.population', V.comparison_gaps(capture, asset, case, source, target))
        def drift(row):
            row['observed_state']['result_context']['row_limit_stage'] = 'after_aggregation'
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp, preview, drift)
            self.assertIn('source.webfocus_requested_result.row_limit_stage',
                          V.comparison_gaps(capture, asset, case, source, target))

    def test_missing_test_unknown_and_in_document_results_do_not_claim_raw_parity(self):
        for mode in ('test', 'unknown'):
            def unqualified(inv):
                inv['objects'][1]['configuration']['result_contract']['data_mode'] = mode
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                _, capture, asset, case, source, target, _ = comparison_fixture(tmp, unqualified)
                self.assertIn('source.webfocus_result_semantics_unqualified',
                              V.comparison_gaps(capture, asset, case, source, target))
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp,
                observation_transform=lambda row: row['observed_state'].pop('result_context'))
            self.assertIn('source.webfocus_observed_result_context_missing',
                          V.comparison_gaps(capture, asset, case, source, target))
        def transformed(inv):
            inv['objects'][1]['configuration']['result_contract']['aggregation_stage'] = 'in_document'
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp, transformed)
            self.assertIn('source.webfocus_transformed_results_required',
                          V.comparison_gaps(capture, asset, case, source, target))
        with tempfile.TemporaryDirectory() as tmp:
            _, capture, asset, case, source, target, _ = comparison_fixture(tmp, transformed,
                lambda row: row.update(origin='transformed', result_scope='transformed'))
            self.assertEqual(V.comparison_gaps(capture, asset, case, source, target), [])

    def test_normalization_preserves_precision_and_ties_to_exact_capture(self):
        raw = b'region,quantity\nWest,1.100000000000000001\n'
        binding = {'capture_content_hash': '1' * 64, 'definition_fingerprint': '2' * 64, 'object_key': 'quantity',
            'attachment_id': 'result-one', 'state_sha256': '3' * 64, 'attachment_sha256': V.sha(raw)}
        profile = {'schema_version': 1, 'format': 'csv', 'encoding': 'utf-8', 'subtotal_policy': 'preserve',
            'headers': ['region', 'quantity'], 'columns': [
            {'ordinal': 0, 'name': 'region', 'type': 'string', 'null_tokens': [], 'nullable': False},
            {'ordinal': 1, 'name': 'quantity', 'type': 'number', 'null_tokens': [], 'nullable': False,
             'decimal_separator': '.', 'group_separator': None, 'percent': False}]}
        out = V.normalize_results(raw, profile, binding)
        self.assertEqual(out['kind'], 'webfocus_normalized_results')
        self.assertEqual(out['rows'][0]['quantity'], '1.100000000000000001')
        self.assertEqual(out['completeness'], 'not_established')
        binding['attachment_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'normalization_binding'): V.normalize_results(raw, profile, binding)


if __name__ == '__main__':
    unittest.main()
