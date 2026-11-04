"""Original offline contract tests. Fake child transport; no source runtime."""
import copy
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


H = module('domo_connected_host', 'skills/omni-artifact-accelerator/scripts/domo_host.py')
sys.modules['analyst_project'] = H.ap
W = module('domo_connected_workflow', 'skills/omni-artifact-accelerator/scripts/domo_workflow.py')
H = W.host
sys.modules['visual_workflow'] = W.wf
M = module('domo_connected_mcp', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
F = module('domo_connected_fixtures', 'tests/test_domo_evidence.py')


class ConnectedDomo(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'engagement'
        H.ap.init(self.root, 'Synthetic visual migration', 'migration', 'dashboard')
        self.source = {'origin': 'https://example.invalid', 'tenant_ref': 'tenant-ref://synthetic',
            'principal_ref': 'principal-ref://synthetic/reader', 'permission_context_ref': 'permission-ref://synthetic',
            'authorization_ref': 'user-authorization-ref://synthetic'}
        self.intake = {'schema_version': 'oaa-domo-intake.v1', 'source': self.source,
            'scope': {'page_ids': ['page-1'], 'include_portfolio': False},
            'route': 'reuse_existing', 'route_reference': 'review-ref://route',
            'target': {'origin': 'https://target.invalid', 'surface': 'dashboard', 'destination_reference': 'draft-ref://synthetic'},
            'observed_at': '2026-10-29T12:00:00+00:00', 'evidence_mode': 'synthetic_fixture'}

    def put(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(H.ap.canonical(value))
        return W.wf.pin(self.root, path)

    def request(self):
        self.put('inputs/intake.json', self.intake)
        return W.plan_value(self.root, 'inputs/intake.json')['requests'][0]

    def host(self, **changes):
        exe = self.base / 'inert-reviewed-cli'
        exe.write_bytes(b'not executable code; only fake transport sees this')
        exe.chmod(0o700)
        source_root = self.base / 'source'
        source_root.mkdir(exist_ok=True)
        source_file = source_root / 'owned.py'
        source_file.write_text('# inert first-party fixture\n')
        request = self.request()
        request['limits']['max_requests'] = 5
        for key, value in changes.items():
            request['scope'][key] = value
        caps = {'schema_version': 'domo-source-capabilities.v1', 'extension_name': 'domo-source-operations',
            'extension_version': '0.1.0', 'target_write_authority': False,
            'supported_commands': ['domo-acquire', 'domo-source-evidence', 'domo-inventory'],
            'implementation_files': [{'path': 'owned.py', 'sha256': H.ap.digest(source_file.read_bytes()),
                                      'bytes': source_file.stat().st_size}]}
        config = {'schema_version': 'oaa-domo-host.v1', 'runtime': {
            'executable': {'path': str(exe), 'sha256': H.ap.digest(exe.read_bytes())},
            'source_root': str(source_root), 'closure': [{'path': str(source_file), 'sha256': H.ap.digest(source_file.read_bytes())}]},
            'capabilities': self.put('inputs/capabilities.json', caps),
            'operations': [{'id': request['request_id'], 'request': self.put('inputs/request.json', request),
                            'directory': 'inputs/domo-source/operation-1'}],
            'credential_environment': {'product_token': 'DOMO_PRODUCT_TOKEN'},
            'max_invocations': 1, 'max_total_requests': 5, 'timeout_seconds': 120}
        self.put('inputs/host.json', config)
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[-1] == 'domo-capabilities':
                result = caps
            else:
                output = argv[argv.index('--output') + 1]
                payload = {'synthetic': True} if 'domo-acquire' in argv else {
                    'contract_version': 'omnikit.domo.evidence.v1', 'objects': [
                        {'tenant_ref': self.source['tenant_ref'], 'visibility_principal_ref': self.source['principal_ref']}]}
                Path(output).write_text(json.dumps(payload))
                result = {'output': output, 'target_write_authority': False}
            return subprocess.CompletedProcess(argv, 0, json.dumps(result).encode(), b'')
        obj = H.DomoOperations(self.root, 'inputs/host.json', allow_read=True, runner=runner)
        return obj, config, request, calls

    def test_intake_missing_source_does_not_invent_access_or_route(self):
        self.put('inputs/intake.json', {'schema_version': 'oaa-domo-intake.v1'})
        result = W.plan_value(self.root, 'inputs/intake.json')
        self.assertFalse(result['requests'])
        self.assertFalse(result['source_access_verified'])
        fields = {q['field'] for q in result['questions']}
        self.assertTrue({'source.origin', 'route', 'experience.cache_refresh_policy', 'experience.visual_preferences'} <= fields)

    def test_selected_scope_never_enumerates_portfolio_by_default(self):
        req = self.request()
        self.assertFalse(req['scope']['include_portfolio'])
        self.assertFalse(H.contract.bridge_request(req)['include_model_suggestions'])
        self.assertEqual(req['scope']['page_ids'], ['page-1'])

    def test_plan_tampering_cannot_expand_scope(self):
        self.request()
        W.plan(self.root, 'inputs/intake.json', 'contracts/plan.json')
        plan = W.wf.load(self.root, 'contracts/plan.json')
        plan['requests'][0]['scope']['page_ids'].append('other-page')
        self.put('contracts/plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'plan_changed'):
            W.materialize(self.root, 'contracts/plan.json', 'inputs/requests')

    def test_materialize_is_exclusive_and_keeps_original_request(self):
        req = self.request()
        W.plan(self.root, 'inputs/intake.json', 'contracts/plan.json')
        result = W.materialize(self.root, 'contracts/plan.json', 'inputs/requests')
        self.assertEqual(W.wf.load(self.root, result['operations'][0]['request']['path']), req)
        with self.assertRaisesRegex(ValueError, 'directory_exists'):
            W.materialize(self.root, 'contracts/plan.json', 'inputs/requests')

    def test_runtime_pins_checked_before_fake_transport(self):
        host, config, _, calls = self.host()
        Path(config['runtime']['closure'][0]['path']).write_text('different')
        with self.assertRaisesRegex(ValueError, 'pin mismatch'):
            host.describe()
        self.assertFalse(calls)

    def test_source_credentials_never_reach_offline_commands_or_disk(self):
        host, _, req, calls = self.host()
        with patch.dict(os.environ, {'DOMO_PRODUCT_TOKEN': 'synthetic-secret', 'OMNI_API_TOKEN': 'not-forwarded', 'PYTHONPATH': '/untrusted'}):
            result = host.run(req['request_id'])
        self.assertFalse(result['target_write_authority'])
        self.assertNotIn('DOMO_PRODUCT_TOKEN', calls[0][1]['env'])
        self.assertEqual(calls[1][1]['env']['DOMO_PRODUCT_TOKEN'], 'synthetic-secret')
        self.assertNotIn('DOMO_PRODUCT_TOKEN', calls[2][1]['env'])
        self.assertTrue(all('OMNI_API_TOKEN' not in k['env'] and 'PYTHONPATH' not in k['env'] for _, k in calls))
        self.assertNotIn('synthetic-secret', json.dumps(result))
        self.assertFalse(Path(calls[0][1]['env']['HOME']).exists())
        self.assertEqual(host.run(req['request_id'], True), result)
        self.assertEqual(len(calls), 3)

    def test_receipt_or_evidence_tamper_rejects_resume(self):
        host, _, req, _ = self.host()
        with patch.dict(os.environ, {'DOMO_PRODUCT_TOKEN': 'fixture'}):
            receipt = host.run(req['request_id'])
        self.put('inputs/domo-source/operation-1/operation.json', {**receipt, 'state': 'accepted'})
        with self.assertRaisesRegex(ValueError, 'resume_receipt_changed'):
            host.run(req['request_id'], True)

    def test_failure_reserves_budget_and_cannot_silently_retry(self):
        host, _, req, _ = self.host()
        def fail(*args, **kwargs):
            raise TimeoutError('fixture')
        host.runner = fail
        with self.assertRaises(TimeoutError):
            host.run(req['request_id'])
        again = H.DomoOperations(self.root, 'inputs/host.json', allow_read=True, runner=fail)
        with self.assertRaisesRegex(ValueError, 'existing_operation_requires_reconcile'):
            again.run(req['request_id'])
        with self.assertRaisesRegex(ValueError, 'resume_requires_recorded_outcome'):
            again.run(req['request_id'], True)
        ledger = next((self.root / 'evidence/domo-host').glob('*.json'))
        self.assertEqual(json.loads(ledger.read_text())['reserved_requests'], 5)

    def test_dataflow_needs_separate_startup_and_credential(self):
        with self.assertRaisesRegex(ValueError, 'separate_dataflow_grant'):
            self.host(include_dataflows=True)

    def test_fixed_operation_and_no_unconfigured_source_mcp(self):
        host, _, _, calls = self.host()
        with self.assertRaisesRegex(ValueError, 'operation_not_selected'):
            host.run('shell')
        self.assertFalse(calls)
        bridge = M.Bridge(self.root)
        names = {x['name'] for x in bridge.definitions()}
        self.assertIn('domo_import_capture', names)
        self.assertNotIn('domo_source_operation', names)
        with self.assertRaisesRegex(ValueError, 'unknown_or_disabled'):
            bridge.call('domo_source_operation', {'operation_id': 'any', 'resume': False})

    def test_request_rejects_bad_origin_credentials_and_count_claims(self):
        req = self.request()
        for origin in ('http://example.invalid', 'https://example.invalid/path', 'https://a:b@example.invalid', 'https://example.invalid?key=bad'):
            wrong = copy.deepcopy(req)
            wrong['source']['origin'] = origin
            with self.assertRaises(ValueError):
                H.contract.request(wrong)
        wrong = copy.deepcopy(req)
        wrong['source']['client_secret'] = 'do-not-retain'
        with self.assertRaises(ValueError):
            H.contract.request(wrong)
        req['completeness'] = {'expected_counts': {'cards': {'count': 4, 'source_ref': 'own-guess', 'channel': 'api'}}}
        with self.assertRaises(ValueError):
            H.contract.request(req)

    def test_request_window_and_stream_budgets_are_forwarded(self):
        req = self.request()
        req['completeness'] = {'expected_counts': {'cards': {'count': 4, 'source_ref': 'export-ref://independent',
            'channel': 'customer_operated_export'}}, 'request_window': {'start': '2026-10-29T09:00:00Z',
            'end': '2026-10-29T11:00:00Z', 'timezone': 'UTC'}}
        result = H.contract.bridge_request(req)
        self.assertEqual(result['connection']['auth']['expected_counts'], req['completeness']['expected_counts'])
        self.assertEqual(result['connection']['auth']['transport_limits'], req['limits'])
        req['completeness']['request_window']['end'] = '2027-01-01T12:00:00Z'
        with self.assertRaisesRegex(ValueError, 'request_window_order'):
            H.contract.request(req)

    def test_domo_routing_requires_retained_original_intake(self):
        self.assertFalse(H.ap.domo_scope(self.root, {'sources': []}))
        record = self.put('inputs/intake.json', self.intake)
        self.assertTrue(H.ap.domo_scope(self.root, {'sources': [record]}))
        record['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'registered source changed'):
            H.ap.domo_scope(self.root, {'sources': [record]})

    def test_build_cannot_run_before_concepts_choice(self):
        self.put('inputs/build.json', {'schema_version': 'oaa-domo-build-handoff-spec.v1'})
        with self.assertRaises(ValueError):
            W.build_handoff(self.root, 'inputs/build.json', 'contracts/build.json')
        self.assertFalse((self.root / 'contracts/build.json').exists())

    def test_import_checks_original_bytes_and_stays_offline(self):
        folder = self.root / 'inputs/capture'
        folder.mkdir()
        value = F.fixture(folder)
        self.put('inputs/capture/capture.json', value)
        M.Bridge(self.root).call('domo_import_capture', {'source': 'inputs/capture/capture.json', 'output': 'inputs/inventory.json'})
        inventory = W.wf.load(self.root, 'inputs/inventory.json')
        self.assertEqual(inventory['source']['platform'], 'domo')
        (folder / value['artifacts'][0]['file']['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            W.import_capture(self.root, 'inputs/capture/capture.json', 'inputs/rejected.json')

    def test_different_source_or_unselected_page_cannot_enter_build(self):
        folder = self.root / 'inputs/selection'
        folder.mkdir()
        capture = F.fixture(folder)
        W.check_selected_scope(self.intake, capture)
        changed = copy.deepcopy(self.intake)
        changed['scope']['page_ids'] = ['other-page']
        with self.assertRaisesRegex(ValueError, 'selected_source_missing'):
            W.check_selected_scope(changed, capture)
        capture['inventory']['items'].append({'key': 'other', 'kind': 'page', 'native_id': 'other-page',
            'parent_key': None, 'disposition': 'include'})
        with self.assertRaisesRegex(ValueError, 'unselected_artifact'):
            W.check_selected_scope(self.intake, capture)

    def source_return_fixture(self):
        def vendor(value, omit):
            return 'sha256:' + hashlib.sha256(json.dumps({k: v for k, v in value.items() if k != omit},
                sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        context = {'tenant_ref': self.source['tenant_ref'], 'run_id': 'run-1', 'migration_unit_id': 'unit-1',
            'validation_cycle_id': 'cycle-1', 'source_object_refs': ['source-ref://card-1'], 'created_at': '2026-10-29T12:00:00Z',
            'inventory_snapshot_ref': 'artifact-ref://inventory', 'source_object_graph_ref': 'artifact-ref://graph',
            'coverage_ledger_ref': 'artifact-ref://coverage', 'evidence_bundle_ref': 'artifact-ref://evidence',
            'source_scope': [{'system': 'domo', 'object_type': 'card', 'object_id': 'card-1', 'fingerprint': 'a' * 64},
                             {'system': 'snowflake', 'object_type': 'table', 'object_id': 'table-1', 'fingerprint': 'b' * 64}]}
        evidence = {'contract_version': 'omnikit.domo.evidence.v1', 'mode': 'manual', 'objects': [{
            'object_type': 'card', 'object_id': 'card-1', 'content_hash': 'sha256:' + 'a' * 64,
            'tenant_ref': self.source['tenant_ref'], 'attributes': {'definition': {'id': 'card-1'}},
            'redaction_state': 'not_required', 'definition_state': 'definition_complete', 'title': 'Synthetic card'}],
            'edges': [], 'coverage': [], 'manual_capture_queue': [], 'checkpoints': [], 'diagnostics': []}
        evidence['bundle_fingerprint'] = vendor(evidence, 'bundle_fingerprint')
        item = {'identity': {'object_type': 'card', 'object_id': 'stable-card-id', 'native_id': 'card-1'},
            'definition': {'content_hash': 'sha256:' + 'a' * 64}}
        item['object_hash'] = vendor(item, 'object_hash')
        portfolio = {'contract_version': 'domo-to-omni.portfolio-inventory.v1', 'immutable': True,
            'source_tenant_ref': context['tenant_ref'], 'run_id': context['run_id'], 'objects': [item],
            **{k: context[k] for k in ('inventory_snapshot_ref', 'source_object_graph_ref', 'coverage_ledger_ref', 'evidence_bundle_ref')}}
        portfolio['portfolio_hash'] = vendor(portfolio, 'portfolio_hash')
        return context, evidence, portfolio

    def test_native_and_portfolio_hashes_are_distinct_without_guessing(self):
        context, evidence, portfolio = self.source_return_fixture()
        bindings = W.source_bindings(context, evidence, None, 'native_content_hash')
        self.assertEqual(len(bindings), 1)  # unrelated warehouse evidence remains context, not dropped from original
        context['source_scope'][0].update(object_id='stable-card-id', fingerprint=portfolio['objects'][0]['object_hash'][7:])
        with self.assertRaises(ValueError):
            W.source_bindings(context, evidence, None, 'native_content_hash')
        mapped = W.source_bindings(context, evidence, portfolio, 'portfolio_object_hash')
        self.assertEqual(mapped[0]['object_id'], 'stable-card-id')
        self.assertEqual(mapped[0]['object_key'], 'card:card-1')
        self.assertNotEqual(mapped[0]['fingerprint'], mapped[0]['content_hash'][7:])
        portfolio['objects'][0]['identity']['native_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'portfolio_hash_changed'):
            W.source_bindings(context, evidence, portfolio, 'portfolio_object_hash')

    def test_missing_hash_or_wrong_run_cannot_create_source_binding(self):
        context, evidence, portfolio = self.source_return_fixture()
        evidence['objects'][0]['content_hash'] = None
        with self.assertRaisesRegex(ValueError, 'membership_changed'):
            W.source_bindings(context, evidence, None, 'native_content_hash')
        portfolio['run_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'original_portfolio_required'):
            W.source_bindings(context, evidence, portfolio, 'portfolio_object_hash')

    def test_frontend_return_is_one_combined_proposal_and_reverified(self):
        context, evidence, _ = self.source_return_fixture()
        ep = self.put('inputs/source.json', evidence)
        cp = self.put('inputs/context.json', context)
        translator = module('test_domo_return_translate', 'skills/omni-artifact-translator/scripts/translate_artifact.py')
        inventory = translator.translate(H.ap.canonical(evidence), 'domo-agent', F.D.PRODUCER_PIN)
        ip = self.put('inputs/inventory.json', inventory)
        scope = {'inventories': [ip], 'units': [{'disposition': 'migrate', 'asset_keys': [a['asset_key'] for a in inventory['assets']],
                                              'surfaces': ['dashboard', 'app']}]}
        sp = self.put('evidence/scope.json', scope)
        fp = self.put('evidence/frontend.json', {'scope': sp, 'source_files': [{**ep, 'bytes': len(H.ap.canonical(evidence))}],
                                               'gaps': [{'code': 'unverified_interaction'}]})
        spec = {'schema_version': 'oaa-domo-frontend-return-spec.v1', 'source_context': cp, 'source_evidence': ep,
            'frontend_receipt': fp, 'producer_revision': F.D.PRODUCER_PIN,
            'source_revision_profile': 'native_content_hash', 'source_portfolio': None}
        self.put('inputs/return-spec.json', spec)
        real_module = W.module
        calls = []
        def verified(root, path):
            calls.append(path)
            return {'status': 'consistent'}
        def mocked(name, path):
            return SimpleNamespace(verify_return=verified) if name == 'domo_return_migration' else real_module(name, path)
        with patch.object(W, 'module', mocked):
            result = W.frontend_return_value(self.root, 'inputs/return-spec.json')
            self.put('evidence/domo-return.json', result)
            self.assertEqual(W.check_frontend_return(self.root, 'inputs/return-spec.json', 'evidence/domo-return.json')['status'], 'consistent')
            self.assertEqual(len(calls), 2)
            self.assertEqual(len(result['target_artifacts']), 1)
            self.assertEqual(result['target_artifacts'][0]['surface'], 'both')
            self.assertTrue(all(type(gap) is str for gap in result['gaps']))
            self.assertFalse(result['acceptance_authority'])
            result['outcome'] = 'accepted'
            self.put('evidence/domo-return.json', result)
            with self.assertRaisesRegex(ValueError, 'frontend_return_changed'):
                W.check_frontend_return(self.root, 'inputs/return-spec.json', 'evidence/domo-return.json')

    def test_dma_handoff_rejects_modified_domo_projection(self):
        cw = module('test_domo_cowork', 'skills/omni-backend-handoff/scripts/cowork.py')
        folder = self.root / 'inputs/capture'
        folder.mkdir()
        capture = F.fixture(folder)
        cp = self.put('inputs/capture/capture.json', capture)
        W.import_capture(self.root, cp['path'], 'inputs/inventory.json')
        ip = W.wf.pin(self.root, 'inputs/inventory.json')
        project = {'sources': [cp, ip], 'artifacts': []}
        original = cw.verify_domo_inventory(self.root, project, ip['path'])
        self.assertEqual(original['sha256'], cp['sha256'])
        inventory = W.wf.load(self.root, ip['path'])
        inventory['assets'].pop()
        project['sources'][1] = self.put(ip['path'], inventory)
        with self.assertRaises(ValueError):
            cw.verify_domo_inventory(self.root, project, ip['path'])
        migration = module('test_domo_migration', 'skills/omni-backend-handoff/scripts/migration.py')
        self.put('inputs/freeze.json', {'schema_version': 1, 'kind': 'analyst_migration_scope_spec',
            'scope_id': 'synthetic', 'decision_reference': 'review-ref://scope', 'inventory_paths': [ip['path']]})
        with self.assertRaisesRegex(ValueError, 'source.projection_changed'):
            migration.build_scope(self.root, project, 'inputs/freeze.json')


if __name__ == '__main__':
    unittest.main()
