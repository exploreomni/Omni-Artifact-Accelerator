"""WebFOCUS source continuity through shared workflow, DMA and fake native gates.

Original synthetic fixtures only. No source execution, live tenant, dependency
installation, rendered acceptance or authenticated producer qualification.
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


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
f = load('webfocus_fixture', 'tests/test_webfocus_visual.py')
e = load('webfocus_journey', 'tests/test_migration_e2e.py')
m = load('migration', 'skills/omni-backend-handoff/scripts/migration.py')
n = load('test_omni_native', 'tests/test_omni_native.py')
prior = load('test_standalone', 'tests/test_standalone.py')
looker_source = load('test_looker_visual_bridge', 'tests/test_looker_visual_bridge.py')
apps = load('webfocus_app_fixture', 'tests/test_looker_app.py')
s = n.native._standalone_module()


def put(root, path, value):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value))


def setup_source(root, *, evidence=False, inventory_transform=None):
    request, result = f.prepare(root / 'inputs', inventory_transform=inventory_transform)
    if evidence:
        _, result = f.add_results(root / 'inputs', request, result)
    original = str(Path(result['output']).relative_to(root))
    inventory = f.T.translate(Path(result['output']).read_bytes(), 'webfocus-capture')
    put(root, 'inputs/webfocus-inventory.json', inventory)
    for path in (original, 'inputs/webfocus-inventory.json'):
        v.ap.register(root, 'sources', path, path)
    v.prepare(root, original, 'inputs/webfocus-inventory.json', 'contracts/visual.json')
    req = v.load(root, 'contracts/visual.json')
    req.update(route='reuse_existing', route_reference='Synthetic selected existing-model route')
    put(root, 'contracts/visual.json', req)
    return result, original, inventory, req


class WebfocusWorkflow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        v.ap.init(self.root, 'Synthetic workflow', 'migration', 'both')
        self.result, self.original, self.inventory, self.req = setup_source(self.root, evidence=True)

    def test_full_denominator_routes_specialist_and_keeps_controls(self):
        _, req = v.requirements(self.root, 'contracts/visual.json')
        self.assertEqual(len(req['items']), len(self.inventory['assets']))
        root, obj = v.ap.load_project(self.root)
        self.assertTrue(v.ap.webfocus_scope(root, obj))
        self.assertEqual(len(s.control_source_keys(req)), 1)
        self.assertEqual(len(s.query_source_keys(req)), 3)
        placement = next(i for i in req['items'] if i['source_id'] == 'left')
        self.assertTrue(any(c['case_id'].endswith('/interaction/drill_autolink_parameter_scope') for c in placement['required_cases']))
        with self.assertRaises(ValueError):
            v.ap.stage_packet_gate(root, 'webfocus-migrator', {'stage': 'discovery', 'outputs': ['app.html']})

    def test_edited_projection_and_original_bytes_cannot_continue(self):
        bad = copy.deepcopy(self.inventory); bad['assets'].pop()
        put(self.root, 'inputs/edited.json', bad)
        with self.assertRaisesRegex(ValueError, 'projection_changed'):
            v.source_inventory(self.root, self.original, 'inputs/edited.json')
        pin = self.result['capture']['source']['files'][0]
        (Path(self.result['output']).parent / pin['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError):
            v.requirements(self.root, 'contracts/visual.json')

    def test_numeric_comparison_binds_case_and_actual_source_bytes(self):
        cap = self.result['capture']; attachment = cap['attachments'][0]
        item = next(i for i in self.req['items'] if i['source_id'] == 'left')
        case = next(c for c in item['required_cases'] if c['lane'] == 'numeric')
        case.update(source_capture=v.pin(self.root, self.original), source_binding={
            'object_key': 'quantity', 'placement_key': 'left', 'state_sha256': f.V.sha(cap['request']['state']),
            'definition_fingerprint': cap['source']['definition_fingerprint'], 'attachment_id': attachment['attachment_id']})
        put(self.root, 'contracts/visual.json', self.req)
        context = {**copy.deepcopy(cap['request']['state']), **copy.deepcopy(attachment['observed_state'].get('result_context', {})), 'population': attachment['population']['key'],
            'data_watermark': attachment['freshness']['data_watermark'], 'freshness_reference': attachment['freshness']['reference'],
            'result_scope': attachment['result_scope'],
            'result_context_reference': attachment['observed_state']['result_context']['reference']}
        raw_path = str((Path(self.result['output']).parent / attachment['path']).relative_to(self.root))
        put(self.root, 'evidence/target.json', [{'region': 'West', 'quantity': '1.100000000000000001'},
                                             {'region': 'East', 'quantity': '2.00'}])
        put(self.root, 'evidence/candidate.json', {'kind': 'synthetic_candidate'})
        spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case['case_id'],
            'requirements': v.pin(self.root, 'contracts/visual.json'), 'candidate': v.pin(self.root, 'evidence/candidate.json'),
            'source': {'file': v.pin(self.root, raw_path), 'format': 'csv', 'context': context,
                       'complete': True, 'completeness_reference': 'Synthetic complete export'},
            'target': {'file': v.pin(self.root, 'evidence/target.json'), 'format': 'json', 'context': copy.deepcopy(context),
                       'complete': True, 'completeness_reference': 'Independent synthetic target'},
            'persona_equivalence_reference': 'Synthetic persona contract', 'keys': ['region'], 'columns': [
                {'name': 'region', 'type': 'string', 'source': 'region', 'target': 'region'},
                {'name': 'quantity', 'type': 'number', 'source': 'quantity', 'target': 'quantity'}]}
        put(self.root, 'contracts/compare.json', spec)
        v.compare(self.root, 'contracts/compare.json', 'evidence/numeric.json')
        self.assertEqual(v.load(self.root, 'evidence/numeric.json')['status'], 'pass')
        spec['target']['context']['data_watermark'] = 'stale'
        put(self.root, 'contracts/compare.json', spec)
        v.compare(self.root, 'contracts/compare.json', 'evidence/stale.json')
        self.assertEqual(v.load(self.root, 'evidence/stale.json')['status'], 'inconclusive')


class WebfocusScopeTests(unittest.TestCase):
    def source(self, key=None, disposition='include'):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve() / 'engagement'
        v.ap.init(root, 'Synthetic scope', 'migration', 'both')
        def transform(inventory):
            if key is not None:
                next(o for o in inventory['objects'] if o['key'] == key)['disposition'] = disposition
        result, original, inventory, requirements = setup_source(root, inventory_transform=transform)
        return root, result, original, inventory, requirements

    def test_in_scope_objects_keep_migrate_without_invented_review(self):
        root, _, _, inventory, requirements = self.source()
        v.requirements(root, 'contracts/visual.json')
        self.assertEqual(len(requirements['items']), len(inventory['assets']))
        self.assertTrue(all(i['disposition'] == 'migrate' for i in requirements['items']))
        self.assertFalse(any(i['source_identity'].get('restricted_private_scope') for i in requirements['items']))
        self.assertFalse(any(i['source_identity'].get('requires_source_review') for i in requirements['items']))

    def test_out_of_scope_direct_parent_and_referenced_objects_cannot_be_promoted(self):
        for key, affected in [('left', {'left'}), ('quantity', {'quantity', 'left', 'right'}),
                              ('page', {'page', 'quantity', 'left', 'right', 'region', 'note', 'note-place', 'unknown'}),
                              ('note', {'note', 'note-place'})]:
            with self.subTest(key=key):
                root, result, _, inventory, requirements = self.source(key, 'out_of_scope')
                v.requirements(root, 'contracts/visual.json')
                self.assertEqual(len(requirements['items']), len(inventory['assets']))
                indexed = {i['source_identity'].get('object_key'): i for i in requirements['items']}
                restricted = {k for k, i in indexed.items() if k is not None and
                              i['source_identity'].get('restricted_private_scope')}
                self.assertEqual(restricted, affected)
                for target in affected:
                    item = indexed[target]
                    self.assertEqual(item['disposition'], 'defer')
                    item.update(disposition='migrate', scope_decision={'reason': 'Synthetic attempted override',
                                                                     'reference': 'Synthetic review cannot change original scope'})
                    put(root, 'contracts/visual.json', requirements)
                    with self.assertRaisesRegex(ValueError, 'private_scope_not_selected'):
                        v.requirements(root, 'contracts/visual.json')
                    item['disposition'] = 'defer'
                if 'left' in affected:
                    asset = next(a for a in inventory['assets'] if a['source_identity'].get('object_key') == 'left')
                    capture = result['capture']
                    case = {'lane': 'visual', 'source_binding': {'object_key': 'quantity', 'placement_key': 'left',
                        'state_sha256': f.V.sha(capture['request']['state']),
                        'definition_fingerprint': capture['source']['definition_fingerprint'], 'attachment_id': None}}
                    with self.assertRaisesRegex(ValueError, 'case_object_scope'):
                        f.V.case_binding(asset, case, capture)

    def test_manual_or_unsupported_dependency_needs_explicit_review(self):
        for disposition in ('manual_review', 'unsupported'):
            with self.subTest(disposition=disposition):
                root, _, _, _, requirements = self.source('quantity', disposition)
                indexed = {i['source_identity'].get('object_key'): i for i in requirements['items']}
                for key in ('quantity', 'left', 'right'):
                    self.assertEqual(indexed[key]['disposition'], 'defer')
                    self.assertTrue(indexed[key]['source_identity']['requires_source_review'])
                    self.assertFalse(indexed[key]['source_identity']['restricted_private_scope'])
                item = indexed['left']; item['disposition'] = 'migrate'
                put(root, 'contracts/visual.json', requirements)
                with self.assertRaisesRegex(ValueError, 'webfocus_source_review_required'):
                    v.requirements(root, 'contracts/visual.json')
                item['scope_decision'] = {'reason': 'Synthetic explicit adaptation review retains unsupported evidence',
                                          'reference': 'Synthetic reviewed source disposition'}
                put(root, 'contracts/visual.json', requirements)
                v.requirements(root, 'contracts/visual.json')
                self.assertEqual(indexed['quantity']['source_identity']['declared_disposition'], disposition)
                self.assertEqual(indexed['left']['source_identity']['declared_disposition'], 'include')

    def test_restricted_placement_cannot_enter_dma_scope_or_direct_request(self):
        root, _, original, inventory, _ = self.source('quantity', 'out_of_scope')
        units = []
        for asset in inventory['assets']:
            restricted = asset['source_identity'].get('restricted_private_scope') is True
            units.append({'unit_id': 'unit-' + str(len(units)), 'inventory_path': 'inputs/webfocus-inventory.json',
                'asset_keys': [asset['asset_key']], 'disposition': 'defer' if restricted else 'migrate',
                'rationale': 'Synthetic original scope retained', 'frontend_asset_ids': [] if restricted else [asset['asset_key']],
                'surfaces': [] if restricted else ['dashboard']})
        spec = {'schema_version': 1, 'kind': 'analyst_migration_scope_spec', 'scope_id': 'synthetic-scope',
            'decision_reference': 'Synthetic scope review', 'inventory_paths': ['inputs/webfocus-inventory.json'],
            'backend_context_path': None, 'units': units}
        put(root, 'contracts/scope.json', spec)
        obj = v.ap.load_project(root)[1]
        m.build_scope(root, obj, 'contracts/scope.json')
        asset = next(a for a in inventory['assets'] if a['source_identity'].get('object_key') == 'left')
        selected = next(u for u in units if u['asset_keys'] == [asset['asset_key']])
        selected.update(disposition='migrate', frontend_asset_ids=selected['asset_keys'], surfaces=['dashboard'])
        put(root, 'contracts/scope.json', spec)
        with self.assertRaisesRegex(ValueError, 'private source scope'):
            m.build_scope(root, obj, 'contracts/scope.json')
        direct = {'source_platform': 'webfocus', 'route': 'reuse_existing',
            'source_inventory_paths': ['inputs/webfocus-inventory.json'],
            'requirements': [{'frontend_asset_ids': [asset['asset_key']]}], 'consumer_bindings': []}
        with self.assertRaisesRegex(ValueError, 'private source scope'):
            m.cw.migration_sources(root, obj, direct, [original, 'inputs/webfocus-inventory.json'])
        direct['requirements'] = []
        direct['consumer_bindings'] = [{'asset_id': asset['asset_key']}]
        with self.assertRaisesRegex(ValueError, 'private source scope'):
            m.cw.migration_sources(root, obj, direct, [original, 'inputs/webfocus-inventory.json'])


class WebfocusDmaJourney(e.MigrationJourney):
    def source(self):
        self.result, original, inventory, req = setup_source(self.root)
        req.update(route='omni_semantic_reconstruction', route_reference='Synthetic semantic route')
        put(self.root, 'contracts/visual.json', req)
        self.source_paths = [original, 'inputs/webfocus-inventory.json']
        self.source_pins = {p: e.sha(self.root / p) for p in self.source_paths}
        self.inventories, self.assets, self.source_gaps = [inventory], inventory['assets'], inventory['gaps']
        self.platform, self.route = 'webfocus', 'omni_semantic_reconstruction'

    def test_roundtrip_preserves_source_and_requires_native_surface_evidence(self):
        self.source()
        migration, scope, units = self.scope()
        request = self.request(migration_scope_path='evidence/migration-scope-v1.json')
        self.assertEqual(request['migration_sources'][0]['original_source']['path'], self.source_paths[0])
        self.receive(self.response()); selected = self.select()
        self.assertFalse(selected['accepted']); self.assertFalse(selected['authorizes_target_write'])
        self.assertEqual(selected['requirement_resolutions'][0]['status'], 'unresolved')
        self.frontend_records(selected)
        result = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(result['report']['candidate_coverage'], 'incomplete')
        self.assertIn({'code': 'missing_surface_delivery', 'surface': 'dashboard'}, result['report']['gaps'])
        original = self.result['capture']['source']['files'][0]
        (Path(self.result['output']).parent / original['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError): migration.verify_return(self.root, 'evidence/return-v1.json')

    def test_source_route_cannot_expand_into_warehouse_work(self):
        self.source(); self.request()
        with self.assertRaisesRegex(ValueError, 'violates selected route'):
            self.response(action='warehouse_and_semantic_candidate')


class WebfocusNative(unittest.TestCase):
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
