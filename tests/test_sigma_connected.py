"""Original source-only integration fixtures. No source runtime or network loads."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


H = module('test_sigma_host_module', 'skills/omni-artifact-accelerator/scripts/sigma_host.py')
sys.modules['analyst_project'] = H.ap
W = module('test_sigma_workflow_module', 'skills/omni-artifact-accelerator/scripts/sigma_workflow.py')
sys.modules['visual_workflow'] = W.wf
M = module('test_sigma_mcp_module', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
F = module('test_sigma_bundle_fixtures', 'tests/test_sigma_evidence.py')
T = module('test_sigma_translator_module', 'skills/omni-artifact-translator/scripts/translate_artifact.py')


def hash_value(v):
    return H.ap.digest(H.ap.canonical(v))


class ConnectedSigma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'engagement'
        H.ap.init(self.root, 'Synthetic source migration', 'migration', 'dashboard')
        self.source = {'api_base_url': 'https://example.invalid', 'approved_api_host': 'example.invalid',
                       'expected_organization_id': 'organization-1', 'expected_user_id': 'user-1',
                       'principal_ref': 'principal-ref://synthetic/viewer',
                       'authorization_ref': 'human-authorization-ref://synthetic/source'}
        self.intake = {'schema_version': 'oaa-sigma-intake.v1', 'source': self.source,
                       'scope': {'workbook_ids': ['workbook-1'], 'data_model_ids': []},
                       'route': 'reuse_existing', 'route_reference': 'synthetic-route',
                       'target': {'origin': 'https://example.invalid', 'surface': 'dashboard', 'destination_reference': 'synthetic-draft'}}

    def put(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value))
        return {'path': path, 'sha256': H.ap.digest(p.read_bytes())}

    def request(self, operation='snapshot'):
        return {'schema_version': 'sigma-source-operation-request.v1', 'request_id': 'request-1',
                'operation': operation, **self.source, 'scope': copy.deepcopy(self.intake['scope']),
                'options': {'include_contents_beta': False}, 'evidence_mode': 'synthetic_fixture', 'max_requests': 5}

    def envelope(self, req, result):
        value = {'schema_version': 'sigma-source-operation.v1', 'operation': req['operation'],
                 'request': req, 'request_sha256': hash_value(req), 'result': result,
                 'result_sha256': hash_value(result), 'target_write_authority': False,
                 'native_validation': 'not_performed', 'business_acceptance': 'not_assessed',
                 'journal_revision': 1, 'previous_content_hash': None, 'gaps': [],
                 'observed_at': '2026-01-01T12:00:00+00:00', 'evidence_mode': req['evidence_mode'],
                 'status': 'complete' if req['operation'] == 'capture' else 'captured_requires_review'}
        if req['operation'] != 'capture':
            value['observed_principal'] = {'organizationId': 'organization-1', 'userId': 'user-1'}
        value['content_hash'] = hash_value(value)
        return value

    def host(self, operation='check', **kwargs):
        exe = self.base / 'reviewed-cli'
        exe.write_bytes(b'original inert fixture; never executed')
        exe.chmod(0o700)
        source = self.base / 'source'
        source.mkdir(exist_ok=True)
        impl = source / 'protocol.py'
        impl.write_bytes(b'# original inert fixture\n')
        files = {'protocol.py': H.ap.digest(impl.read_bytes())}
        caps = {'schema_version': 'sigma-source-capabilities.v1', 'extension_name': 'sigma-source-operations',
                'extension_version': '0.1.0', 'request_schema': 'sigma-source-operation-request.v1',
                'result_schema': 'sigma-source-operation.v1', 'operations': ['check', 'inventory', 'snapshot', 'capture'],
                'implementation_files': files, 'implementation_sha256': hash_value(files),
                'target_write_authority': False, 'terminal_review_bypass': False}
        req = {'schema_version': 'sigma-source-operation-request.v1', 'request_id': 'operation-1',
               'operation': operation, **self.source, 'scope': self.intake['scope'], 'options': {'include_contents_beta': False},
               'evidence_mode': 'synthetic_fixture', 'max_requests': 5}
        if operation == 'capture':
            req['visual_capture_request'] = {**self.source, 'schema_version': 'sigma-visual-capture-request.v2',
                'capture_id': 'capture-1', 'evidence_mode': 'synthetic_fixture', 'workbook_id': 'workbook-1',
                'max_requests_per_invocation': 5, 'target_kind': 'page', 'page_id': 'page-1', 'data_model_id': None}
        c = {'schema_version': 'oaa-sigma-host.v1', 'runtime': {
            'executable': {'path': str(exe), 'sha256': H.ap.digest(exe.read_bytes())},
            'source_root': str(source), 'closure': [{'path': str(impl), 'sha256': files['protocol.py']}]},
            'capabilities': self.put('inputs/capabilities.json', caps),
            'operations': [{'id': 'operation-1', 'request': self.put('inputs/request.json', req), 'directory': 'inputs/capture-1'}],
            'max_invocations': 2, 'max_total_requests': 10, 'timeout_seconds': 20}
        self.put('inputs/host.json', c)
        calls = []
        def runner(argv, **options):
            calls.append((argv, options))
            if argv[-1] == 'capabilities':
                return subprocess.CompletedProcess(argv, 0, json.dumps(caps).encode(), b'')
            envelope = self.envelope(req, {'workbooks': [{'workbookId': 'workbook-1', 'readable': True}], 'dataModels': []})
            out = self.put('inputs/capture-1/source-operation-000001.json', envelope)
            return subprocess.CompletedProcess(argv, 0, json.dumps({'output': str(self.root / out['path'])}).encode(), b'')
        obj = H.SigmaOperations(self.root, 'inputs/host.json', allow_read=True, runner=runner, **kwargs)
        return obj, c, caps, req, calls

    def test_intake_missing_questions_and_workbook_without_model(self):
        self.put('inputs/intake.json', {'schema_version': 'oaa-sigma-intake.v1', 'source': {}, 'scope': {}})
        W.plan(self.root, 'inputs/intake.json', 'contracts/missing.json')
        v = W.wf.load(self.root, 'contracts/missing.json')
        self.assertFalse(v['requests'])
        self.assertTrue(any(q['field'] == 'source.expected_user_id' for q in v['questions']))
        self.put('inputs/intake.json', self.intake)
        W.plan(self.root, 'inputs/intake.json', 'contracts/plan.json')
        v = W.wf.load(self.root, 'contracts/plan.json')
        self.assertEqual([r['operation'] for r in v['requests']], ['check', 'inventory', 'snapshot'])
        self.assertFalse(v['questions'])
        entries = W.materialize(self.root, 'contracts/plan.json', 'inputs/requests')
        self.assertEqual(len(entries['operations']), 3)
        self.assertEqual(W.wf.load(self.root, entries['operations'][2]['request']['path'])['scope']['data_model_ids'], [])
        with self.assertRaisesRegex(ValueError, 'exists_resume'):
            W.materialize(self.root, 'contracts/plan.json', 'inputs/requests')

    def test_modified_plan_cannot_expand_scope(self):
        self.put('inputs/intake.json', self.intake)
        W.plan(self.root, 'inputs/intake.json', 'contracts/plan.json')
        v = W.wf.load(self.root, 'contracts/plan.json')
        v['requests'][0]['scope']['workbook_ids'].append('unselected')
        self.put('contracts/plan.json', v)
        with self.assertRaisesRegex(ValueError, 'plan_changed'):
            W.materialize(self.root, 'contracts/plan.json', 'inputs/requests')

    def test_specialist_routing_ignores_unrelated_non_json_sources(self):
        notes = self.root / 'inputs' / 'requirements.md'
        notes.write_text('Source interview notes, not a Sigma declaration.')
        records = [{'path': 'inputs/requirements.md', 'sha256': H.ap.digest(notes.read_bytes())}]
        self.assertFalse(H.ap.sigma_scope(self.root, {'sources': records}))
        records.append(self.put('inputs/intake.json', self.intake))
        self.assertTrue(H.ap.sigma_scope(self.root, {'sources': records}))
        records[-1]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'registered source changed'):
            H.ap.sigma_scope(self.root, {'sources': records})

    def test_host_request_rejects_nested_identity_and_budget_changes(self):
        _, _, _, request, _ = self.host(operation='capture')
        for key, changed in [('expected_user_id', 'other'), ('max_requests_per_invocation', 500), ('workbook_id', 'other')]:
            value = copy.deepcopy(request)
            value['visual_capture_request'][key] = changed
            with self.assertRaisesRegex(ValueError, 'nested_source'):
                H.request(value)
        request['options']['include_contents_beta'] = True
        with self.assertRaisesRegex(ValueError, 'capture_scope'):
            H.request(request)

    def test_credentials_never_written_or_sent_to_capability_probe(self):
        obj, _, caps, _, calls = self.host()
        self.assertFalse(obj.describe()['runtime_loaded'])
        self.assertEqual(W.compatibility(caps)['status'], 'recognized_source_contract')
        with patch.dict(os.environ, {'SIGMA_CLIENT_ID': 'fixture-id', 'SIGMA_CLIENT_SECRET': 'fixture-secret',
                                     'OMNI_API_TOKEN': 'never-forward', 'PYTHONPATH': '/untrusted'}):
            result = obj.run('operation-1')
        self.assertEqual(result['status'], 'source_operation_recorded')
        self.assertNotIn('SIGMA_CLIENT_SECRET', calls[0][1]['env'])
        env = calls[1][1]['env']
        self.assertEqual(env['SIGMA_CLIENT_SECRET'], 'fixture-secret')
        self.assertNotIn('OMNI_API_TOKEN', env)
        self.assertNotIn('PYTHONPATH', env)
        self.assertFalse(Path(env['HOME']).exists())

    def test_wrong_executable_closure_or_request_pin_rejects(self):
        obj, config, _, _, calls = self.host()
        Path(config['runtime']['closure'][0]['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'pin mismatch'):
            obj.describe()
        self.assertFalse(calls)

    def test_query_grant_and_fixed_operation_scope(self):
        obj, _, _, _, calls = self.host(operation='capture')
        with self.assertRaisesRegex(ValueError, 'separate_query_grant'):
            obj.run('operation-1')
        with self.assertRaisesRegex(ValueError, 'operation_not_selected'):
            obj.run('other')
        self.assertFalse(calls)

    def test_failed_invocations_are_reserved_across_restart(self):
        obj, _, _, _, _ = self.host()
        def timeout(*args, **kwargs):
            raise TimeoutError('synthetic timeout')
        obj.runner = timeout
        for _ in range(2):
            with self.assertRaises(TimeoutError):
                obj.run('operation-1', True)
        resumed = H.SigmaOperations(self.root, 'inputs/host.json', allow_read=True, runner=timeout)
        with self.assertRaisesRegex(ValueError, 'budget_exhausted'):
            resumed.run('operation-1', True)

    def test_bundle_projects_full_inventory_and_verifies_actual_files(self):
        folder = self.root / 'inputs' / 'evidence'
        folder.mkdir()
        bundle = F.bundle_fixture(folder)
        self.put('inputs/evidence/capture.json', bundle)
        inv = T.translate(json.dumps(bundle).encode(), 'sigma-agent', 'oaa-sigma-evidence@1')
        self.put('inputs/inventory.json', inv)
        actual = W.wf.source_inventory(self.root, 'inputs/evidence/capture.json', 'inputs/inventory.json')
        self.assertEqual(len(actual['assets']), len(bundle['inventory']['items']))
        first = folder / bundle['artifacts'][0]['file']['path']
        first.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            W.wf.source_inventory(self.root, 'inputs/evidence/capture.json', 'inputs/inventory.json')

    def test_bundle_inherits_private_parent_for_all_lanes(self):
        folder = self.root / 'inputs' / 'restricted'
        folder.mkdir()
        bundle = F.bundle_fixture(folder)
        page = next(i for i in bundle['inventory']['items'] if i['kind'] == 'page')
        page['configuration']['private'] = True
        F.seal(bundle)
        inv = T.translate(json.dumps(bundle).encode(), 'sigma-agent', 'oaa-sigma-evidence@1')
        visual = next(a for a in inv['assets'] if a['kind'] == 'visual')
        self.assertTrue(visual['source_identity']['restricted_private_scope'])
        self.put('inputs/restricted/capture.json', bundle)
        self.put('inputs/inventory.json', inv)
        W.wf.prepare(self.root, 'inputs/restricted/capture.json', 'inputs/inventory.json', 'contracts/private.json')
        req = W.wf.load(self.root, 'contracts/private.json')
        req.update(route='reuse_existing', route_reference='synthetic')
        self.assertTrue(all(i['disposition'] == 'defer' for i in req['items'] if i['source_identity'].get('restricted_private_scope')))
        next(i for i in req['items'] if i['kind'] == 'visual')['disposition'] = 'migrate'
        self.put('contracts/private.json', req)
        with self.assertRaisesRegex(ValueError, 'private_scope_not_selected'):
            W.wf.requirements(self.root, 'contracts/private.json')

    def test_capture_receipt_uses_child_identity_without_inventing_outer_principal(self):
        folder = self.root / 'inputs' / 'outer'
        child_folder = folder / 'visual'
        child_folder.mkdir(parents=True)
        capture = F.v2_fixture(child_folder)
        self.put('inputs/outer/visual/capture-000001.json', capture)
        child_bytes = (child_folder / 'capture-000001.json').read_bytes()
        req = self.request('capture')
        req.update(visual_capture_request=capture['original_request'], max_requests=capture['original_request'].get('max_requests_per_invocation', 100))
        for key in self.source:
            req[key] = capture['original_request'][key]
        result = {'visual_capture': {'path': 'visual/capture-000001.json', 'sha256': H.ap.digest(child_bytes),
                  'bytes': len(child_bytes), 'schema_version': 'sigma-visual-capture.v1', 'status': capture['status']}}
        envelope = self.envelope(req, result)
        projected = T.translate(json.dumps(envelope).encode(), 'sigma-agent', 'sigma-source-operations@0.1.0')
        self.assertEqual(projected['assets'][0]['source_identity']['source_object_type'], 'capture')
        self.assertEqual(W.wf.verify_sigma_operation_files(envelope, folder), child_folder / 'capture-000001.json')
        result['visual_capture']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'receipt_mismatch'):
            W.wf.verify_sigma_operation_files(envelope, folder)

    def test_connected_tools_disabled_by_default_and_build_gate_not_bypassed(self):
        bridge = M.Bridge(self.root)
        names = {t['name'] for t in bridge.definitions()}
        self.assertIn('sigma_plan_source', names)
        self.assertNotIn('sigma_source_operation', names)
        with self.assertRaises(ValueError):
            bridge.call('sigma_source_operation', {'operation_id': 'operation-1', 'resume': False})
        self.put('inputs/handoff.json', {'schema_version': 'oaa-sigma-package-handoff.v1'})
        with self.assertRaisesRegex(ValueError, 'stage_gate|execution_phase_blocked'):
            W.package_handoff(self.root, 'inputs/handoff.json', 'evidence/handoff.json')

    def test_v2_page_capture_projection_and_pinned_source_operation(self):
        folder = self.root / 'inputs' / 'page'
        folder.mkdir()
        capture = F.v2_fixture(folder)
        inv = T.translate(json.dumps(capture).encode(), 'sigma-agent', 'sigma-source-operations@0.1.0')
        self.assertTrue(any(a['kind'] == 'page' for a in inv['assets']))
        self.assertEqual(inv['migration_context']['route'], None)
        F.S.verify_capture_files(capture, folder)
        snapshot = {'snapshotContract': 'sigma-api-v2', 'connections': [], 'dataModels': [],
                    'workbooks': [{'workbookId': 'workbook-1', 'pages': [{'pageId': 'page-1', 'elements': []}]}]}
        req = self.request()
        envelope = self.envelope(req, snapshot)
        projected = T.translate(json.dumps(envelope).encode(), 'sigma-agent', 'sigma-source-operations@0.1.0')
        self.assertTrue(all(a['source_path'].startswith('/result/') for a in projected['assets']))
        envelope['result']['workbooks'][0]['workbookId'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'source_operation_hash'):
            T.translate(json.dumps(envelope).encode(), 'sigma-agent', 'sigma-source-operations@0.1.0')
        # A public self-seal cannot legitimize a contradictory selection.
        envelope = self.envelope(req, snapshot)
        with self.assertRaisesRegex(ValueError, 'result_selected_scope'):
            T.translate(json.dumps(envelope).encode(), 'sigma-agent', 'sigma-source-operations@0.1.0')

    def test_capture_generation_cannot_expand_intake_workbook(self):
        folder = self.root / 'inputs' / 'outside'
        folder.mkdir()
        capture = F.v2_fixture(folder)['original_request']
        for key in self.source:
            capture[key] = self.source[key]
        capture['workbook_id'] = 'workbook-outside-selection'
        self.intake['capture_requests'] = [capture]
        self.put('inputs/intake.json', self.intake)
        with self.assertRaisesRegex(ValueError, 'outside_selected_intake'):
            W.plan(self.root, 'inputs/intake.json', 'contracts/plan.json')

    def test_full_bound_numeric_workflow_uses_verified_file_size(self):
        folder = self.root / 'inputs' / 'comparison'
        folder.mkdir()
        bundle, _, case, source, target, normalized, _ = F.comparison_fixture(folder)
        capture_pin = self.put('inputs/comparison/capture.json', bundle)
        inv = T.translate(json.dumps(bundle).encode(), 'sigma-agent', 'oaa-sigma-evidence@1')
        self.put('inputs/inventory.json', inv)
        W.wf.prepare(self.root, capture_pin['path'], 'inputs/inventory.json', 'contracts/visual.json')
        req = W.wf.load(self.root, 'contracts/visual.json')
        req.update(route='reuse_existing', route_reference='synthetic-route')
        visual = next(i for i in req['items'] if i['kind'] == 'visual')
        numeric = next(c for c in visual['required_cases'] if c['lane'] == 'numeric')
        numeric.update(source_capture=capture_pin, source_binding=case['source_binding'])
        requirement_pin = self.put('contracts/visual.json', req)
        source.update(file=self.put('inputs/normalized.json', normalized),
                      raw_file=W.wf.pin(self.root, 'inputs/comparison/' + source['raw_file']['path']),
                      complete=True, completeness_reference='synthetic-full')
        target.update(file=self.put('evidence/rows.json', normalized['rows']), complete=True, completeness_reference='synthetic-full')
        spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': numeric['case_id'],
                'requirements': requirement_pin, 'candidate': self.put('evidence/candidate.json', {'kind': 'synthetic'}),
                'source': source, 'target': target, 'persona_equivalence_reference': 'synthetic-persona', 'keys': ['zone'],
                'columns': [{'name': 'zone', 'source': 'zone', 'target': 'zone', 'type': 'string'},
                            {'name': 'count', 'source': 'count', 'target': 'count', 'type': 'number', 'nullable': True}]}
        self.put('contracts/compare.json', spec)
        W.wf.compare(self.root, 'contracts/compare.json', 'evidence/comparison.json')
        report = W.wf.load(self.root, 'evidence/comparison.json')
        self.assertEqual(report['gaps'], [])
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['sigma_execution_parity'], 'supplied_bound_evidence_only')


if __name__ == '__main__':
    unittest.main()
