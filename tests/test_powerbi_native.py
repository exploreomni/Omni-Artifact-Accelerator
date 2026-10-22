"""Actual local Power BI intake composed with a synthetic native Omni transport.

The control config is deliberately an opaque observed fixture, not an asserted
Omni control-creation grammar. No test grants native or business acceptance.
"""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import test_standalone as prior
import test_powerbi_visual_bridge as source

native, m = prior.native, prior.m


class PowerBINativeTests(unittest.TestCase):
    setUp = prior.StandaloneTests.setUp
    write = prior.StandaloneTests.write
    capture = prior.StandaloneTests.capture
    execute = prior.StandaloneTests.execute
    complete = prior.StandaloneTests.complete

    def configure(self):
        result = source.capture_fixture(self.root / 'inputs/powerbi-capture')
        self.original = str(Path(result['output']).relative_to(self.root))
        self.write('inventory.json', result['inventory'])
        native.WORKFLOW.prepare(self.root, self.original, 'inventory.json', 'powerbi-requirements.json')
        req = native.WORKFLOW.load(self.root, 'powerbi-requirements.json')
        req.update(route='reuse_existing', route_reference='synthetic-reviewed-existing-model')
        self.write('requirements.json', req)
        prior.StandaloneTests.configure(self)
        standalone = native._standalone_module()
        control_keys = standalone.control_source_keys(req)
        self.assertEqual(len(control_keys), 2)  # original slicer visual plus independent control obligation
        self.query_keys = [item['asset_key'] for item in req['items']
                           if item['kind'] == 'visual' and item['asset_key'] not in control_keys]
        self.assertEqual(len(self.query_keys), 3)
        self.baseline_spec['bindings'][0]['source_asset_keys'] = self.query_keys
        # Synthetic observation of an existing target config; never sent as mutation.
        control_config = {'syntheticField': 'orders.region', 'syntheticScope': ['2'], 'mode': 'single-select'}
        self.fake.state['controls'] = {'data': {'region': control_config, 'other': {'label': 'Retained other control'}},
                                       'order': ['region', 'other']}
        self.fake.topic['topic']['views'][0]['dimensions'].append({'field_name': 'region', 'view_name': 'orders',
            'fully_qualified_name': 'orders.region', 'data_type': 'STRING', 'sql': '${TABLE}.region'})
        self.write('control-review.json', {'kind': 'synthetic-independent-control-review',
            'limitation': 'Observed fixture fields and scope; no live interaction validation'})
        self.baseline_spec['control_bindings'] = [{'source_asset_keys': sorted(control_keys), 'control_id': 'region',
            'expected_config': copy.deepcopy(control_config),
            'field_bindings': [{'topic': 'orders', 'field_id': 'orders.region', 'config_pointer': '/syntheticField'}],
            'target_query_keys': ['2'], 'scope_pointer': '/syntheticScope',
            'compatibility_reference': 'synthetic-field-and-scope-review', 'evidence_paths': ['control-review.json']}]
        self.write('baseline-spec.json', self.baseline_spec)

    def prepare(self):
        return self.adapter.prepare('payload.json', ['requirements.json', self.original], 'baseline.json',
                                    'ownership.json', 'review-1')

    def test_actual_powerbi_to_standalone_native_readback_export_and_return(self):
        prepared, receipt = self.complete()
        self.assertEqual(receipt['status'], 'readback_matched')
        baseline = native.WORKFLOW.load(self.root, 'baseline.json')
        self.assertEqual(baseline['inspection']['semantic_snapshot']['retained_controls']['order'], ['region', 'other'])
        self.assertEqual(len(baseline['definitions']), 2)  # query measure and independently resolved control field
        started = self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'synthetic-export')
        self.adapter.export_status(started['export_id'])
        downloaded = self.adapter.export_file(started['export_id'])
        self.assertEqual(downloaded['status'], 'downloaded')
        result = m.prepare_return(self.root, 'scope.json', 'return-spec.json', 'return.json')
        self.assertEqual(result['report']['candidate_coverage'], 'incomplete')
        self.assertEqual(m.verify_return(self.root, 'return.json')['status'], 'consistent')
        inventory = native.WORKFLOW.load(self.root, 'inventory.json')
        self.assertEqual(len(inventory['assets']), 19)
        self.assertEqual(sum(i['kind'] == 'visual' for i in inventory['assets']), 4)
        self.assertNotIn('dma_import', native.WORKFLOW.ap.load_project(self.root)[1])
        self.assertFalse(native.WORKFLOW.load(self.root, 'return.json')['migration_accepted'])
        self.assertTrue(result['report']['gaps'])  # unknown source behavior remains explicit
        (self.root / self.original).write_bytes((self.root / self.original).read_bytes() + b' ')
        with self.assertRaises(ValueError):
            m.verify_return(self.root, 'return.json')

    def test_powerbi_arbitrary_semantic_file_cannot_bypass_current_baseline(self):
        self.configure()
        with self.assertRaisesRegex(ValueError, 'typed current existing-Omni baseline'):
            self.adapter.prepare('payload.json', ['requirements.json'], 'semantic.json', 'ownership.json', 'review')
        self.assertEqual(self.fake.patch_count, 0)

    def test_missing_slicer_binding_cannot_be_hidden_by_chart_binding(self):
        self.configure()
        self.baseline_spec['bindings'][0]['source_asset_keys'] += self.baseline_spec['control_bindings'][0]['source_asset_keys']
        self.baseline_spec.pop('control_bindings')
        self.write('baseline-spec.json', self.baseline_spec)
        with self.assertRaisesRegex(ValueError, 'retained_source_control_unbound'):
            self.capture()
        self.assertEqual(self.fake.semantic_reads, 0)

    def test_retained_control_requires_actual_field_scope_and_review_evidence(self):
        self.configure()
        original = copy.deepcopy(self.baseline_spec)
        mutations = [lambda b: b['field_bindings'][0].update(config_pointer='/mode'),
                     lambda b: b.update(target_query_keys=['1']),
                     lambda b: b['expected_config'].update(syntheticScope=['1']),
                     lambda b: b['field_bindings'][0].update(topic='foreign-topic'),
                     lambda b: b.update(evidence_paths=[]),
                     lambda b: b.update(source_asset_keys=b['source_asset_keys'][:1])]
        for mutate in mutations:
            self.baseline_spec = copy.deepcopy(original)
            mutate(self.baseline_spec['control_bindings'][0])
            self.write('baseline-spec.json', self.baseline_spec)
            with self.assertRaises(ValueError):
                self.capture()
        self.assertEqual(self.fake.patch_count, 0)

    def test_retained_control_does_not_authorize_creation_or_mutation(self):
        self.configure()
        self.payload['controls'] = {'data': {'region': {'anything': 'new'}}}
        self.write('payload.json', self.payload)
        with self.assertRaisesRegex(ValueError, 'control_mutation_requires_qualified_binding'):
            self.capture()
        self.assertEqual(self.fake.patch_count, 0)

    def test_control_config_order_and_definition_drift_block_prepare(self):
        self.configure()
        self.capture()
        original = copy.deepcopy((self.fake.state['controls'], self.fake.topic))
        mutations = [lambda: self.fake.state['controls']['data']['region'].update(mode='multi-select'),
                     lambda: self.fake.state['controls']['data']['region'].update(syntheticScope=['1', '2']),
                     lambda: self.fake.state['controls']['order'].reverse(),
                     lambda: self.fake.topic['topic']['views'][0]['dimensions'][0].update(sql='${TABLE}.other')]
        for mutate in mutations:
            self.fake.state['controls'], self.fake.topic = copy.deepcopy(original)
            mutate()
            with self.assertRaises(ValueError):
                self.prepare()
        self.assertEqual(self.fake.patch_count, 0)

    def test_control_and_evidence_drift_block_execute(self):
        self.configure()
        self.capture()
        prepared = self.prepare()
        self.fake.state['controls']['order'].reverse()
        with self.assertRaises(ValueError):
            self.adapter.execute(prepared['candidate_sha256'], 'synthetic-authorization')
        self.fake.state['controls']['order'].reverse()
        self.write('control-review.json', {'changed': True})
        with self.assertRaisesRegex(ValueError, 'evidence_changed'):
            self.adapter.execute(prepared['candidate_sha256'], 'synthetic-authorization')
        self.assertEqual(self.fake.patch_count, 0)

    def test_control_drift_blocks_export_submission_and_download(self):
        self.configure()
        self.capture()
        prepared, _ = self.execute()
        original = copy.deepcopy(self.fake.state['controls'])
        self.fake.state['controls']['data']['region']['mode'] = 'multi-select'
        with self.assertRaises(ValueError):
            self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'synthetic-export')
        self.assertFalse([call for call in self.fake.http_calls if call[0] == 'POST'])
        self.fake.state['controls'] = original
        started = self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'synthetic-export')
        self.adapter.export_status(started['export_id'])
        self.fake.state['controls']['order'].reverse()
        with self.assertRaises(ValueError):
            self.adapter.export_file(started['export_id'])
        self.assertFalse((self.root / f'.omni-native/exports/{started["export_id"]}/artifact.json').exists())

    def test_missing_query_binding_stays_return_gap(self):
        original = self.configure
        def incomplete_mapping():
            original()
            self.missing_key = self.baseline_spec['bindings'][0]['source_asset_keys'].pop()
            self.write('baseline-spec.json', self.baseline_spec)
        self.configure = incomplete_mapping
        self.complete()
        result = m.prepare_return(self.root, 'scope.json', 'return-spec.json', 'return.json')
        self.assertIn({'code': 'source_query_not_bound', 'asset_key': self.missing_key}, result['report']['gaps'])
        self.assertEqual(result['report']['candidate_coverage'], 'incomplete')

    def test_source_tokens_never_enter_native_child_environment(self):
        self.configure()
        with patch.dict('os.environ', {'FABRIC_ACCESS_TOKEN': 'synthetic-fabric', 'POWERBI_ACCESS_TOKEN': 'synthetic-powerbi'}):
            self.capture()
        self.assertTrue(self.fake.calls)
        self.assertTrue(all(not any(key.startswith(('FABRIC_', 'POWERBI_')) for key in options['env'])
                            for _, options in self.fake.calls))
