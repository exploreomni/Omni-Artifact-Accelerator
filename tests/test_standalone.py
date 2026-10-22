"""Existing-model standalone contracts with independent transport responses, no DMA or tenant."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_omni_native as n

native = n.native
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/omni-backend-handoff/scripts'))
import migration as m  # noqa: E402 - package-owned standalone scripts


class SemanticOmni(n.FakeOmni):
    def __init__(self, root):
        super().__init__(root)
        self.models = {
            'model-1': {'id': 'model-1', 'modelKind': 'SHARED', 'baseModelId': 'schema-1', 'connectionId': 'connection-1', 'deletedAt': None},
            'branch-1': {'id': 'branch-1', 'modelKind': 'BRANCH', 'baseModelId': 'model-1', 'connectionId': 'connection-1', 'deletedAt': None},
            'workbook-1': {'id': 'workbook-1', 'modelKind': 'WORKBOOK', 'baseModelId': 'branch-1', 'connectionId': 'connection-1', 'deletedAt': None}}
        self.yaml = {'files': {'orders.view': 'measures:\n  revenue:\n    sql: ${TABLE}.amount\n    aggregate_type: sum\n',
                               'orders.topic': 'base_view: orders\n'}, 'version': 3,
                     'checksums': {'orders.view': 'opaque-vendor-checksum'}}
        self.topic = {'success': True, 'topic': {'name': 'orders', 'base_view_name': 'orders',
            'always_where_filters': {}, 'relationships': [], 'views': [{'name': 'orders', 'table_name': 'orders',
                'dimensions': [], 'measures': [{'field_name': 'revenue', 'view_name': 'orders',
                    'fully_qualified_name': 'orders.revenue', 'data_type': 'NUMBER', 'type': 'aggregation',
                    'aggregate_type': 'SUM', 'sql': '${TABLE}.amount'}]}]}}
        self.model_has_next = False
        self.semantic_reads = 0
        self.drift_after_write = False

    def runner(self, args, **kwargs):
        if len(args) > 2 and args[1] == 'models':
            self.calls.append((args, kwargs))
            assert kwargs['shell'] is False
            if '--help' in args:
                return subprocess.CompletedProcess(args, 0, b'Usage --modelid --pagesize --fullyresolved --includechecksums', b'')
            self.semantic_reads += 1
            assert args[args.index('--base-url') + 1] == 'https://tenant.omniapp.co'
            assert kwargs['env']['OMNI_API_TOKEN'] == 'test-placeholder-only'
            if args[2] == 'list':
                identifier = args[args.index('--modelid') + 1]
                assert args[args.index('--pagesize') + 1] == '2'
                result = {'pageInfo': {'hasNextPage': self.model_has_next}, 'records': [self.models[identifier]]}
            elif args[2] == 'yaml-get':
                assert args[3:10] == ['workbook-1', '--mode', 'combined', '--fullyresolved', 'true', '--includechecksums', 'true']
                result = self.yaml
            elif args[2] == 'get-topic':
                assert args[3:5] == ['workbook-1', 'orders']
                result = self.topic
            else:
                raise AssertionError(args)
            return subprocess.CompletedProcess(args, 0, json.dumps(result).encode(), b'')
        result = super().runner(args, **kwargs)
        if self.drift_after_write and '--help' not in args and len(args) > 2 and args[2] == 'v2-patch-draft-by-identifier':
            self.topic['topic']['always_where_filters'] = {'orders.region': 'East'}
        return result


class StandaloneTests(unittest.TestCase):
    setUp = n.NativeTests.setUp
    write = n.NativeTests.write

    def configure(self):
        self.fake = SemanticOmni(self.root)
        self.adapter = native.NativeAdapter(self.root, self.target, runner=self.fake.runner, http=self.fake.http)
        req = native.WORKFLOW.load(self.root, 'requirements.json')
        self.baseline_spec = {'schema_version': 1, 'kind': 'analyst_existing_omni_baseline_spec',
            'requirements_path': 'requirements.json', 'payload_path': 'payload.json', 'ownership_path': 'ownership.json',
            'review_ref': 'reviewed-existing-omni-definition-mapping', 'bindings': [{
                'source_asset_keys': [item['asset_key'] for item in req['items']],
                'query_key': '2', 'topic': 'orders', 'query': self.payload['queryPresentations']['data']['2']['query'],
                'field_ids': ['orders.revenue']}]}
        self.write('baseline-spec.json', self.baseline_spec)

    def capture(self):
        return self.adapter.capture_baseline('baseline-spec.json', 'baseline.json')

    def prepare(self):
        return self.adapter.prepare('payload.json', ['requirements.json', 'source.json'], 'baseline.json',
                                    'ownership.json', 'review-1')

    def execute(self):
        prepared = self.prepare()
        receipt = self.adapter.execute(prepared['candidate_sha256'], 'exact-candidate-authorization')
        self.assertEqual(receipt['status'], 'readback_matched')
        return prepared, receipt

    def complete(self, tableau=False):
        if tableau:
            import test_tableau_visual_bridge as tableau_fixture
            result = tableau_fixture.capture_fixture(self.root / 'inputs/tableau-capture')
            original = str(Path(result['output']).relative_to(self.root))
            self.write('inventory.json', result['inventory'])
            native.WORKFLOW.prepare(self.root, original, 'inventory.json', 'tableau-requirements.json')
            req = native.WORKFLOW.load(self.root, 'tableau-requirements.json')
            req.update(route='reuse_existing', route_reference='synthetic-tableau-reviewed-reuse')
            self.write('requirements.json', req)
        self.configure()
        # Explicitly retained adaptation assertions remain unverified declarations.
        req = native.WORKFLOW.load(self.root, 'requirements.json')
        for item in req['items']:
            item['parity'] = {k: 'adapted' for k in item['parity']}
        self.write('requirements.json', req)
        self.capture()
        prepared, receipt = self.execute()
        v = native.WORKFLOW
        self.write('listing.json', {'kind': 'synthetic-independent-inventory', 'assets': [i['asset_key'] for i in req['items']]})
        units = [{'unit_id': 'dashboard', 'inventory_path': 'inventory.json', 'asset_keys': [i['asset_key'] for i in req['items']],
                  'disposition': 'migrate', 'rationale': 'Synthetic selected dashboard', 'frontend_asset_ids': ['sales'], 'surfaces': ['dashboard']}]
        self.write('scope-spec.json', {'schema_version': 1, 'kind': 'analyst_migration_scope_spec', 'scope_id': 'standalone',
            'decision_reference': 'fixture-scope-review', 'inventory_paths': ['inventory.json'], 'units': units,
            'independent_source_listing_path': 'listing.json'})
        m.freeze(self.root, 'scope-spec.json', 'scope.json')
        self.write('observation.txt', {'fixture': 'independent test observations; no actual tenant'})
        self.write('source-rows.json', [{'region': 'West', 'revenue': 24}])
        self.write('target-rows.json', [{'region': 'West', 'revenue': 24.0}])
        evidence_paths = []
        for item in req['items']:
            for case in item['required_cases']:
                path = f'evidence/case-{len(evidence_paths)}.json'
                if case['lane'] == 'numeric':
                    context = {'filters': {}, 'timezone': 'UTC', 'data_watermark': 'synthetic-fixed-1',
                               'population': 'all_regions', 'principal': 'synthetic-viewer'}
                    spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case['case_id'],
                        'requirements': v.pin(self.root, 'requirements.json'), 'candidate': v.pin(self.root, prepared['path']),
                        'source': {'file': v.pin(self.root, 'source-rows.json'), 'format': 'json', 'context': context,
                                   'complete': True, 'completeness_reference': 'synthetic-whole-fixture'},
                        'target': {'file': v.pin(self.root, 'target-rows.json'), 'format': 'json', 'context': context,
                                   'complete': True, 'completeness_reference': 'synthetic-whole-fixture'},
                        'persona_equivalence_reference': 'synthetic-equivalence', 'keys': ['region'],
                        'columns': [{'name': 'region', 'source': 'region', 'target': 'region', 'type': 'string'},
                                    {'name': 'revenue', 'source': 'revenue', 'target': 'revenue', 'type': 'number'}]}
                    spec_path = f'contracts/compare-{len(evidence_paths)}.json'
                    self.write(spec_path, spec)
                    v.compare(self.root, spec_path, path)
                else:
                    self.write(path, {'schema_version': 1, 'kind': 'analyst_observed_case', 'case_id': case['case_id'],
                        'lane': case['lane'], 'requirements': v.pin(self.root, 'requirements.json'),
                        'candidate': v.pin(self.root, prepared['path']), 'status': 'pass', 'observer': 'synthetic-test',
                        'expected': 'Fixture expectation', 'observed': 'Fixture observation', 'execution_reference': 'synthetic-run',
                        'files': [v.pin(self.root, 'observation.txt')]})
                evidence_paths.append(path)
        v.coverage(self.root, 'requirements.json', prepared['path'], evidence_paths, 'coverage.json')
        scope = v.load(self.root, 'scope.json')
        self.return_spec = {'schema_version': 1, 'kind': 'analyst_standalone_migration_return_spec',
            'scope_sha256': scope['sha256'], 'baseline_path': 'baseline.json', 'requirements_path': 'requirements.json',
            'candidate_path': prepared['path'],
            'execution_receipt_path': f'.omni-native/executions/{prepared["candidate_sha256"]}/receipt.json',
            'coverage_path': 'coverage.json', 'unresolved': []}
        self.write('return-spec.json', self.return_spec)
        return prepared, receipt

    def test_capture_current_native_definitions_and_no_dma(self):
        self.configure()
        response = self.capture()
        baseline = native.WORKFLOW.load(self.root, 'baseline.json')
        self.assertEqual(response['status'], 'baseline_captured')
        self.assertNotIn('inspection', response)
        self.assertEqual(baseline['organization']['tenant_origin'], self.target.base_url)
        self.assertEqual(baseline['definitions'][0]['fields']['orders.revenue']['definition']['aggregate_type'], 'SUM')
        self.assertNotIn('dma_import', native.WORKFLOW.ap.load_project(self.root)[1])
        first = self.fake.semantic_reads
        prepared = self.prepare()
        self.assertGreater(self.fake.semantic_reads, first)
        candidate = native.WORKFLOW.load(self.root, prepared['path'])
        self.assertEqual(candidate['standalone_baseline']['sha256'], baseline['sha256'])
        self.assertFalse(baseline['native_verified'])

    def test_prepare_rejects_current_topic_field_model_context_drift(self):
        self.configure()
        self.capture()
        originals = copy.deepcopy((self.fake.topic, self.fake.yaml, self.fake.models, self.fake.identity))
        mutations = [lambda: self.fake.topic['topic']['views'][0]['measures'][0].update(aggregate_type='AVG'),
                     lambda: self.fake.topic['topic']['always_where_filters'].update(region='East'),
                     lambda: self.fake.yaml['files'].update({'orders.view': 'sql: changed'}),
                     lambda: self.fake.models['workbook-1'].update(baseModelId='other-model'),
                     lambda: self.fake.models['workbook-1'].update(baseModelId='model-1'),
                     lambda: self.fake.models['branch-1'].update(baseModelId='other-model'),
                     lambda: self.fake.identity.update(orgRole='ADMIN')]
        for mutate in mutations:
            self.fake.topic, self.fake.yaml, self.fake.models, self.fake.identity = copy.deepcopy(originals)
            mutate()
            with self.assertRaises(ValueError):
                self.prepare()
        self.assertEqual(self.fake.patch_count, 0)

    def test_execute_rereads_current_definitions_and_blocks_before_intent(self):
        self.configure()
        self.capture()
        prepared = self.prepare()
        self.fake.topic['topic']['views'][0]['measures'][0]['aggregate_type'] = 'AVG'
        with self.assertRaisesRegex(ValueError, 'context drift'):
            self.adapter.execute(prepared['candidate_sha256'], 'authorized')
        self.assertEqual(self.fake.patch_count, 0)
        self.assertFalse(list((self.root / '.omni-native/executions').glob('*/intent.json')))

    def test_after_write_semantic_race_is_unknown_and_not_replayed(self):
        self.configure()
        self.capture()
        prepared = self.prepare()
        self.fake.drift_after_write = True
        receipt = self.adapter.execute(prepared['candidate_sha256'], 'authorized')
        self.assertEqual(receipt['status'], 'outcome_unknown')
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            self.adapter.execute(prepared['candidate_sha256'], 'authorized-again')
        self.assertEqual(self.fake.patch_count, 1)
        self.assertEqual(self.adapter.reconcile(prepared['candidate_sha256'])['status'], 'semantic_context_drift_or_unavailable')

    def test_unsupported_and_missing_current_definitions_fail_closed(self):
        self.configure()
        for change in ('composite', 'field', 'pagination'):
            before = copy.deepcopy(self.fake.topic)
            if change == 'composite':
                self.fake.topic['topic']['is_composite'] = True
            elif change == 'field':
                self.fake.topic['topic']['views'][0]['measures'] = []
            else:
                self.fake.model_has_next = True
            with self.assertRaises(ValueError):
                self.capture()
            self.fake.topic = before
        self.assertEqual(self.fake.patch_count, 0)

    def test_exact_field_and_full_query_mapping_and_pins(self):
        self.configure()
        self.baseline_spec['bindings'][0]['field_ids'] = ['orders.other']
        self.write('baseline-spec.json', self.baseline_spec)
        with self.assertRaisesRegex(ValueError, 'field_mapping'):
            self.capture()
        self.baseline_spec['bindings'][0]['field_ids'] = ['orders.revenue']
        self.write('baseline-spec.json', self.baseline_spec)
        self.capture()
        self.payload['queryPresentations']['data']['2']['query']['limit'] = 1
        self.write('payload.json', self.payload)
        with self.assertRaisesRegex(ValueError, 'evidence_changed'):
            self.prepare()

    def test_standalone_return_recomputes_evidence_without_dma(self):
        self.complete()
        result = m.prepare_return(self.root, 'scope.json', 'return-spec.json', 'return.json')
        self.assertEqual(result['status'], 'frontend_evidence_prepared')
        receipt = native.WORKFLOW.load(self.root, 'return.json')
        self.assertEqual(receipt['kind'], 'analyst_standalone_migration_return')
        self.assertEqual(receipt['native_verification'], 'recorded_readback_only')
        self.assertFalse(receipt['migration_accepted'])
        self.assertNotIn('catalog', receipt)
        self.assertEqual(m.verify_return(self.root, 'return.json')['status'], 'consistent')
        self.assertNotIn('dma_import', native.WORKFLOW.ap.load_project(self.root)[1])

    def test_return_rejects_candidate_readback_baseline_coverage_and_result_drift(self):
        prepared, _ = self.complete()
        for path, mutate in [
            (prepared['path'], lambda x: x['payload'].update(name='changed')),
            (self.return_spec['execution_receipt_path'], lambda x: x['readback']['state'].update(name='changed')),
            ('baseline.json', lambda x: x['definitions'][0]['fields']['orders.revenue']['definition'].update(aggregate_type='AVG')),
            ('coverage.json', lambda x: x.update(pending_cases=['missing-case'])),
            ('target-rows.json', lambda x: x[0].update(revenue=240))]:
            original = native.WORKFLOW.load(self.root, path)
            changed = copy.deepcopy(original)
            mutate(changed)
            self.write(path, changed)
            with self.assertRaises(ValueError):
                m.build_return(*native.WORKFLOW.ap.load_project(self.root), 'scope.json', 'return-spec.json')
            self.write(path, original)

    def test_export_rejects_changed_semantics_before_submission_and_download(self):
        self.configure()
        self.capture()
        prepared, _ = self.execute()
        original = copy.deepcopy(self.fake.topic)
        self.fake.topic['topic']['always_where_filters'] = {'orders.region': 'East'}
        with self.assertRaisesRegex(ValueError, 'context drift'):
            self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'export-approval')
        self.assertFalse([x for x in self.fake.http_calls if x[0] == 'POST'])
        self.fake.topic = original
        started = self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'export-approval')
        self.adapter.export_status(started['export_id'])
        self.fake.topic['topic']['views'][0]['measures'][0]['aggregate_type'] = 'AVG'
        with self.assertRaisesRegex(ValueError, 'context drift'):
            self.adapter.export_file(started['export_id'])
        self.assertFalse((self.root / f'.omni-native/exports/{started["export_id"]}/artifact.json').exists())

    def test_download_rechecks_semantics_after_binary_response(self):
        self.configure()
        self.capture()
        prepared, _ = self.execute()
        started = self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'export-approval')
        self.adapter.export_status(started['export_id'])
        original_http = self.fake.http
        def drifting_http(method, url, token, body, max_bytes):
            response = original_http(method, url, token, body, max_bytes)
            if url.endswith('/download/job-1'):
                self.fake.yaml['files']['orders.view'] = 'sql: changed during response'
            return response
        self.adapter.http = drifting_http
        with self.assertRaisesRegex(ValueError, 'context drift'):
            self.adapter.export_file(started['export_id'])
        self.assertFalse((self.root / f'.omni-native/exports/{started["export_id"]}/artifact.json').exists())

    def test_capture_rejects_unsupported_query_grammar_and_missing_definitions(self):
        self.configure()
        self.payload['queryPresentations']['data']['2']['query']['calculations'] = [{'name': 'unqualified'}]
        self.baseline_spec['bindings'][0]['query'] = copy.deepcopy(self.payload['queryPresentations']['data']['2']['query'])
        self.write('payload.json', self.payload)
        self.write('baseline-spec.json', self.baseline_spec)
        with self.assertRaisesRegex(ValueError, 'unsupported_query_grammar'):
            self.capture()
        self.assertEqual(self.fake.semantic_reads, 0)

    def test_return_retains_unresolved_obligations_and_partial_coverage(self):
        self.complete()
        self.return_spec['unresolved'] = ['Effective access validation pending independent reviewer']
        self.write('return-spec.json', self.return_spec)
        result = m.prepare_return(self.root, 'scope.json', 'return-spec.json', 'return.json')
        self.assertEqual(result['report']['candidate_coverage'], 'incomplete')
        self.assertIn({'code': 'declared_unresolved', 'requirement': self.return_spec['unresolved'][0]}, result['report']['gaps'])
        receipt = native.WORKFLOW.load(self.root, 'return.json')
        self.assertFalse(receipt['migration_accepted'])
        self.assertFalse(receipt['origin_authenticated'])

    def test_actual_tableau_capture_to_standalone_return_without_dma(self):
        self.complete(tableau=True)
        m.prepare_return(self.root, 'scope.json', 'return-spec.json', 'return.json')
        receipt = native.WORKFLOW.load(self.root, 'return.json')
        inventory = native.WORKFLOW.load(self.root, 'inventory.json')
        self.assertEqual(inventory['source']['platform'], 'tableau')
        self.assertEqual(len(inventory['assets']), 12)
        self.assertEqual(m.verify_return(self.root, 'return.json')['status'], 'consistent')
        self.assertNotIn('dma_import', native.WORKFLOW.ap.load_project(self.root)[1])
        self.assertFalse(receipt['migration_accepted'])
        # This synthetic source retains explicit unknown-widget and semantic gaps.
        self.assertEqual(receipt['candidate_coverage'], 'incomplete')
        self.assertTrue(receipt['gaps'])
        self.assertEqual(receipt['native_verification'], 'recorded_readback_only')

    def test_tableau_arbitrary_semantic_pin_cannot_bypass_baseline(self):
        import test_tableau_visual_bridge as tableau_fixture
        result = tableau_fixture.capture_fixture(self.root / 'inputs/tableau-capture')
        self.write('inventory.json', result['inventory'])
        native.WORKFLOW.prepare(self.root, str(Path(result['output']).relative_to(self.root)),
                                'inventory.json', 'tableau-requirements.json')
        req = native.WORKFLOW.load(self.root, 'tableau-requirements.json')
        req.update(route='reuse_existing', route_reference='synthetic-review')
        self.write('requirements.json', req)
        with self.assertRaisesRegex(ValueError, 'typed current existing-Omni baseline'):
            self.adapter.prepare('payload.json', ['requirements.json'], 'semantic.json', 'ownership.json', 'review')
        self.assertEqual(self.fake.patch_count, 0)

    def test_target_cli_does_not_receive_tableau_session(self):
        from unittest.mock import patch
        self.configure()
        with patch.dict('os.environ', {'TABLEAU_SESSION_TOKEN': 'synthetic-source-secret'}):
            self.capture()
        self.assertTrue(self.fake.calls)
        self.assertTrue(all('TABLEAU_SESSION_TOKEN' not in options['env'] for _, options in self.fake.calls))

    def test_positive_export_keeps_current_baseline_and_private_output_receipt(self):
        self.configure()
        self.capture()
        prepared, _ = self.execute()
        started = self.adapter.export_start(prepared['candidate_sha256'], 'export.json', 'state.json', 'approved-export')
        self.adapter.export_status(started['export_id'])
        receipt = self.adapter.export_file(started['export_id'])
        self.assertEqual(receipt['status'], 'downloaded')
        self.assertEqual(receipt['standalone_baseline_check']['baseline_sha256'],
                         native.WORKFLOW.load(self.root, 'baseline.json')['sha256'])
        self.assertEqual((self.root / receipt['artifact']['path']).read_bytes(), self.fake.file)
        self.assertEqual((self.root / receipt['artifact']['path']).stat().st_mode & 0o777, 0o600)
        self.assertFalse(receipt['native_verified'])
        self.assertFalse(receipt['data_watermark_verified'])

    def test_selected_branch_requires_matching_workbook_ancestry_at_capture(self):
        self.configure()
        self.fake.models['workbook-1']['baseModelId'] = 'model-1'
        with self.assertRaisesRegex(ValueError, 'ancestry'):
            self.capture()
        self.assertFalse((self.root / 'baseline.json').exists())
        self.assertEqual(self.fake.patch_count, 0)

    def test_main_draft_uses_shared_model_ancestry_without_branch_guessing(self):
        self.configure()
        self.target = native.TargetConfig(**{**native.asdict(self.target), 'branch_id': None})
        self.fake.meta['branch'] = None
        self.fake.models['workbook-1']['baseModelId'] = 'model-1'
        self.adapter = native.NativeAdapter(self.root, self.target, runner=self.fake.runner, http=self.fake.http)
        self.capture()
        prepared, _ = self.execute()
        baseline = native.WORKFLOW.load(self.root, 'baseline.json')
        self.assertNotIn('branch-1', baseline['inspection']['semantic_snapshot']['models'])
        self.assertEqual(baseline['inspection']['semantic_snapshot']['draft_context']['branch'], None)
        self.assertTrue(prepared['candidate_sha256'])

    def test_missing_native_receipt_cannot_be_completed(self):
        _, receipt = self.complete()
        receipt.pop('standalone_baseline_check')
        self.write(self.return_spec['execution_receipt_path'], receipt)
        with self.assertRaisesRegex(ValueError, 'baseline_recheck_missing'):
            m.prepare_return(self.root, 'scope.json', 'return-spec.json', 'return.json')


if __name__ == '__main__':
    unittest.main()
