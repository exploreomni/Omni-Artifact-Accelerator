"""CDT source -> workflow -> DMA contracts and fake native readback.

Synthetic source/target transport only. No dependency imports, live APIs, source
code execution, rendered acceptance or real DMA parser execution.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


e = load('periscope_journey_fixture', 'tests/test_migration_e2e.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
f = load('periscope_source_fixture', 'tests/test_periscope_capture.py')
b = load('periscope_adapter_fixture', 'tests/test_periscope_visual_bridge.py')
m = load('migration', 'skills/omni-backend-handoff/scripts/migration.py')
n = load('test_omni_native', 'tests/test_omni_native.py')
prior = load('test_standalone', 'tests/test_standalone.py')
looker_source = load('test_looker_visual_bridge', 'tests/test_looker_visual_bridge.py')
apps = load('periscope_app_fixture', 'tests/test_looker_app.py')
s = n.native._standalone_module()


def put(root, path, value):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value))


def setup_source(root, *, evidence=False):
    request, result = f.prepare(root / 'inputs')
    if evidence:
        (root / 'inputs/supplied/result.csv').write_bytes(b'place,value\nWest,1.10\nEast,2.20\n')
        result = f.C.import_evidence(Path(result['output']), f.evidence_spec(), root / 'inputs/supplied')
    original = str(Path(result['output']).relative_to(root))
    inventory = b.T.translate(Path(result['output']).read_bytes(), 'periscope-capture')
    put(root, 'inputs/periscope-inventory.json', inventory)
    for path in (original, 'inputs/periscope-inventory.json'):
        v.ap.register(root, 'sources', path, path)
    v.prepare(root, original, 'inputs/periscope-inventory.json', 'contracts/visual.json')
    req = v.load(root, 'contracts/visual.json')
    req.update(route='reuse_existing', route_reference='synthetic selected existing-model route')
    put(root, 'contracts/visual.json', req)
    return result, original, inventory, req


class PeriscopeWorkflow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'project'
        v.ap.init(self.root, 'Synthetic CDT workflow', 'migration', 'both')
        self.result, self.original, self.inventory, self.req = setup_source(self.root, evidence=True)

    def test_complete_denominator_controls_and_dependencies_remain_obligations(self):
        _, req = v.requirements(self.root, 'contracts/visual.json')
        self.assertEqual(len(req['items']), len(self.inventory['assets']))
        controls = s.control_source_keys(req)
        self.assertEqual(len(controls), 1)
        self.assertEqual(len(s.query_source_keys(req)), 3)  # visual and both placements
        for item in req['items']:
            kinds = {c['lane'] for c in item['required_cases']}
            if item['kind'] in ('content', 'definition'):
                self.assertNotIn('numeric', kinds)
        control = next(i for i in req['items'] if i['kind'] == 'control')
        self.assertTrue(any(c['case_id'].endswith('/effective_defaults_and_inheritance') for c in control['required_cases']))

    def test_typed_routing_does_not_turn_linux_title_into_cdt_or_waive_build_gate(self):
        self.assertTrue(v.ap.periscope_scope(self.root, v.load(self.root, 'project.json')))
        self.assertIn('periscope-migrator', {r['role'] for r in v.ap.plan(self.root)['roles']})
        gates = {'required': True, 'next_stage': 'access'}
        with patch.object(v.ap, 'stage_status', return_value=gates), \
             patch.object(v.ap, 'stage_require', side_effect=ValueError('build-choice-required')):
            with self.assertRaisesRegex(ValueError, 'build-choice-required'):
                v.ap.stage_packet_gate(self.root, 'periscope-migrator', {'stage': 'discovery', 'outputs': ['deliverables/app.html']})
        other = self.root.parent / 'linux'
        v.ap.init(other, 'Periscope label on Linux content', 'migration', 'dashboard')
        put(other, 'inputs/linux.json', {'kind': 'sisense_dashboard', 'name': 'Periscope example'})
        v.ap.register(other, 'sources', 'inputs/linux.json', 'sisense')
        self.assertFalse(v.ap.periscope_scope(other, v.load(other, 'project.json')))
        with self.assertRaisesRegex(ValueError, 'pinned CDT'):
            v.ap.stage_packet_gate(other, 'periscope-migrator')

    def comparison(self):
        captured = self.result['capture']
        a = captured['attachments'][0]
        item = next(i for i in self.req['items'] if i['source_id'] == 'quantity')
        case = next(c for c in item['required_cases'] if c['case_id'].endswith('/numeric/default'))
        case['source_capture'] = v.pin(self.root, self.original)
        case['source_binding'] = {'object_key': 'quantity', 'placement_key': None,
            'state_sha256': f.C.sha(captured['request']['state']),
            'definition_fingerprint': captured['source']['definition_fingerprint'], 'attachment_id': a['attachment_id']}
        put(self.root, 'contracts/visual.json', self.req)
        binding = {k: case['source_binding'][k] for k in ('object_key', 'state_sha256', 'definition_fingerprint', 'attachment_id')}
        binding.update(capture_content_hash=captured['content_hash'], attachment_sha256=a['sha256'])
        raw_path = str((Path(self.original).parent / a['path']))
        profile = {'schema_version': 1, 'format': 'csv', 'encoding': 'utf-8', 'subtotal_policy': 'preserve', 'headers': ['place', 'value'], 'columns': [
            {'ordinal': 0, 'name': 'place', 'type': 'string', 'nullable': False, 'null_tokens': []},
            {'ordinal': 1, 'name': 'quantity', 'type': 'number', 'nullable': False, 'null_tokens': [],
             'decimal_separator': '.', 'group_separator': None, 'percent': False}]}
        normalized = f.V.normalize_results((self.root / raw_path).read_bytes(), profile, binding)
        put(self.root, 'inputs/normalized.json', normalized)
        put(self.root, 'evidence/target.json', [{'place': 'West', 'quantity': '1.1'}, {'place': 'East', 'quantity': '2.2'}])
        put(self.root, 'evidence/candidate.json', {'kind': 'synthetic_candidate'})
        context = {k: copy.deepcopy(captured['request']['state'][k]) for k in
                   ('filters', 'parameters', 'daterange', 'aggregation', 'timezone', 'locale', 'principal')}
        context.update(population=a['population']['key'], data_watermark=a['freshness']['data_watermark'],
                       freshness_reference=a['freshness']['reference'], result_scope=a['result_scope'])
        return {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case['case_id'],
            'requirements': v.pin(self.root, 'contracts/visual.json'), 'candidate': v.pin(self.root, 'evidence/candidate.json'),
            'source': {'file': v.pin(self.root, 'inputs/normalized.json'), 'raw_file': v.pin(self.root, raw_path),
                       'format': 'periscope-normalized', 'context': context, 'complete': True, 'completeness_reference': 'synthetic two rows'},
            'target': {'file': v.pin(self.root, 'evidence/target.json'), 'format': 'json', 'context': copy.deepcopy(context),
                       'complete': True, 'completeness_reference': 'independent synthetic target count'},
            'persona_equivalence_reference': 'synthetic viewer equivalence', 'keys': ['place'], 'columns': [
                {'name': 'place', 'type': 'string', 'source': 'place', 'target': 'place'},
                {'name': 'quantity', 'type': 'number', 'source': 'quantity', 'target': 'quantity'}]}

    def compare(self, spec):
        put(self.root, 'contracts/compare.json', spec)
        (self.root / 'evidence/compare.json').unlink(missing_ok=True)
        v.compare(self.root, 'contracts/compare.json', 'evidence/compare.json')
        return v.load(self.root, 'evidence/compare.json')

    def test_equal_rows_need_same_population_state_and_freshness(self):
        spec = self.comparison()
        result = self.compare(spec)
        self.assertEqual(result['status'], 'pass', result)
        self.assertEqual(result['native_validation'], 'not_established')
        for field, changed in [('data_watermark', 'stale'), ('result_scope', 'displayed'), ('freshness_reference', None)]:
            bad = copy.deepcopy(spec)
            bad['target']['context'][field] = changed
            self.assertEqual(self.compare(bad)['status'], 'inconclusive')
        put(self.root, 'evidence/target.json', [{'place': 'West', 'quantity': '1.11'}, {'place': 'East', 'quantity': '2.2'}])
        spec['target']['file'] = v.pin(self.root, 'evidence/target.json')
        self.assertEqual(self.compare(spec)['status'], 'fail')

    def test_wrong_source_case_and_attachment_drift_reject(self):
        spec = self.comparison()
        case = next(c for i in self.req['items'] for c in i['required_cases'] if c['case_id'] == spec['case_id'])
        case['source_binding']['object_key'] = 'note'
        put(self.root, 'contracts/visual.json', self.req)
        with self.assertRaisesRegex(ValueError, 'object_or_state'):
            v.requirements(self.root, 'contracts/visual.json')
        case['source_binding']['object_key'] = 'quantity'
        put(self.root, 'contracts/visual.json', self.req)
        (self.root / spec['source']['raw_file']['path']).write_text('place,value\nWest,9\n')
        with self.assertRaises(ValueError):
            v.requirements(self.root, 'contracts/visual.json')


class PeriscopeDmaJourney(e.MigrationJourney):
    def source(self):
        self.result, original, inventory, req = setup_source(self.root)
        req.update(route='omni_semantic_reconstruction', route_reference='synthetic semantic route')
        put(self.root, 'contracts/visual.json', req)
        self.source_paths = [original, 'inputs/periscope-inventory.json']
        self.source_pins = {p: e.sha(self.root / p) for p in self.source_paths}
        self.inventories, self.assets, self.source_gaps = [inventory], inventory['assets'], inventory['gaps']
        self.platform, self.route = 'periscope', 'omni_semantic_reconstruction'

    def test_roundtrip_and_return_preserve_source_and_require_native_surface_evidence(self):
        self.source()
        migration, scope, units = self.scope()
        request = self.request(migration_scope_path='evidence/migration-scope-v1.json')
        self.assertEqual(request['migration_sources'][0]['original_source']['path'], self.source_paths[0])
        self.receive(self.response())
        selected = self.select()
        self.assertFalse(selected['accepted'])
        self.assertFalse(selected['authorizes_target_write'])
        self.assertEqual(selected['requirement_resolutions'][0]['status'], 'unresolved')
        self.frontend_records(selected)
        self.assertEqual(v.ap.project_check(self.root)['native_verification'], 'not_assessed')
        result = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(result['report']['candidate_coverage'], 'incomplete')
        self.assertIn({'code': 'missing_surface_delivery', 'surface': 'dashboard'}, result['report']['gaps'])
        attachment = self.result['capture']['source']['files'][0]
        (Path(self.result['output']).parent / attachment['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, 'evidence/return-v1.json')

    def test_source_route_cannot_expand_into_warehouse_work(self):
        self.source()
        self.request()
        with self.assertRaisesRegex(ValueError, 'violates selected route'):
            self.response(action='warehouse_and_semantic_candidate')


class PeriscopeNative(unittest.TestCase):
    setUp = prior.StandaloneTests.setUp
    write = prior.StandaloneTests.write

    def configure(self):
        result, original, inventory, req = setup_source(self.root)
        self.original = original
        self.write('requirements.json', req)
        self.fake = prior.SemanticOmni(self.root)
        self.adapter = n.native.NativeAdapter(self.root, self.target, runner=self.fake.runner, http=self.fake.http)
        config = {'field': 'orders.region', 'queries': ['2'], 'mode': 'single'}
        self.fake.state['controls']['data']['region'] = config
        self.fake.topic['topic']['views'][0]['dimensions'].append({'field_name': 'region', 'view_name': 'orders',
            'fully_qualified_name': 'orders.region', 'data_type': 'STRING', 'sql': '${TABLE}.region'})
        self.write('evidence/control-review.json', {'evidence': 'synthetic retained target control'})
        baseline = {'schema_version': 1, 'kind': 'analyst_existing_omni_baseline_spec', 'review_ref': 'synthetic control and query review',
            'requirements_path': 'requirements.json', 'payload_path': 'payload.json', 'ownership_path': 'ownership.json',
            'bindings': [{'source_asset_keys': sorted(s.query_source_keys(req)), 'query_key': '2', 'topic': 'orders',
                          'query': {'fields': ['orders.revenue']}, 'field_ids': ['orders.revenue']}],
            'control_bindings': [{'source_asset_keys': sorted(s.control_source_keys(req)), 'control_id': 'region',
                'expected_config': config, 'field_bindings': [{'topic': 'orders', 'field_id': 'orders.region', 'config_pointer': '/field'}],
                'target_query_keys': ['2'], 'scope_pointer': '/queries', 'compatibility_reference': 'synthetic control mapping',
                'evidence_paths': ['evidence/control-review.json']}]}
        self.write('baseline-spec.json', baseline)

    def test_fake_readback_is_not_migration_acceptance_and_control_drift_blocks_write(self):
        self.configure()
        with self.assertRaisesRegex(ValueError, 'typed current'):
            self.adapter.prepare('payload.json', ['requirements.json'], 'semantic.json', 'ownership.json', 'review')
        self.adapter.capture_baseline('baseline-spec.json', 'baseline.json')
        candidate = self.adapter.prepare('payload.json', ['requirements.json', self.original], 'baseline.json', 'ownership.json', 'review')
        self.fake.state['controls']['data']['region']['queries'] = ['1']
        with self.assertRaises(ValueError):
            self.adapter.execute(candidate['candidate_sha256'], 'synthetic authorization')
        self.assertEqual(self.fake.patch_count, 0)
        self.fake.state['controls']['data']['region']['queries'] = ['2']
        result = self.adapter.execute(candidate['candidate_sha256'], 'synthetic authorization')
        self.assertEqual(result['status'], 'readback_matched')
        v.coverage(self.root, 'requirements.json', candidate['path'], [], 'evidence/coverage.json')
        proof = s.verify_delivery(self.root, {'candidate_path': candidate['path'], 'execution_receipt_path':
            '.omni-native/executions/' + candidate['candidate_sha256'] + '/receipt.json', 'coverage_path': 'evidence/coverage.json'})
        self.assertFalse(proof['native_verified'])
        self.assertTrue(proof['gaps'])

    def test_control_cannot_be_hidden_in_query_bindings(self):
        self.configure()
        spec = v.load(self.root, 'baseline-spec.json')
        spec['bindings'][0]['source_asset_keys'] += spec.pop('control_bindings')[0]['source_asset_keys']
        self.write('baseline-spec.json', spec)
        with self.assertRaisesRegex(ValueError, 'retained_source_control_unbound'):
            self.adapter.capture_baseline('baseline-spec.json', 'baseline.json')

    def test_app_runtime_controls_and_separate_surface_readback(self):
        project = v.load(self.root, 'project.json')
        project['surfaces'] = ['dashboard', 'app']
        self.write('project.json', project)
        self.configure()
        config = apps.configure_app(self.root)
        adapter, fake = config['adapter'], config['fake']
        runtime = v.load(self.root, config['runtime_path'])
        self.assertEqual(len(runtime['controls']), 1)
        broken = copy.deepcopy(runtime)
        broken['controls'] = []
        self.write(config['runtime_path'], broken)
        with self.assertRaises(ValueError):
            adapter.capture_baseline(config['baseline_spec'], config['baseline_path'])
        self.write(config['runtime_path'], runtime)
        adapter.capture_baseline(config['baseline_spec'], config['baseline_path'])
        candidate = adapter.prepare(config['candidate_spec'])
        receipt = adapter.execute(candidate['candidate_sha256'], 'synthetic exact App authorization')
        self.assertEqual(receipt['status'], 'readback_matched')
        self.assertEqual(fake.patch_count, 1)
        v.coverage(self.root, 'requirements.json', candidate['path'], [], 'evidence/app-coverage.json')
        result = apps.app.verify_delivery(self.root, {'candidate_path': candidate['path'], 'execution_receipt_path':
            '.omni-app-native/executions/' + candidate['candidate_sha256'] + '/receipt.json', 'coverage_path': 'evidence/app-coverage.json'})
        self.assertEqual(result['surface'], 'app')
        self.assertFalse(result['native_verified'])
        self.assertTrue(result['gaps'])


if __name__ == '__main__':
    unittest.main()
