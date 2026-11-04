"""Focused first-party workflow checks; no provider, native app or billing claims."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/omni-artifact-accelerator/scripts/analyst_project.py'
spec = importlib.util.spec_from_file_location('efficiency_tests', SCRIPT.with_name('execution_efficiency.py'))
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
P = E.P


class EfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic scoped migration', 'migration', 'dashboard', branding='none')
        project = P.load_project(self.root)[1]
        project.pop('stage_gate_policy')
        project.pop('workflow_quality_policy')
        P.write_json(self.root / 'project.json', project, replace=True)
        (self.root / 'inputs/original.txt').write_text('Order grain and regional access restrictions.\n')
        self.request = {'role': 'bi-engineer', 'inputs': ['inputs/original.txt'], 'output': 'tasks/scoped.json',
            'assignment': {'schema_version': 1, 'task_id': 'scope-a', 'domain_id': 'commerce', 'stage': 'dashboard',
                'role': 'bi-engineer', 'scope_ids': ['orders'], 'objective': 'Bind the approved metric',
                'outputs': ['deliverables/view.json'], 'acceptance': ['Preserve order grain and access'],
                'dependency_paths': ['inputs/original.txt'], 'unknowns': ['Native observations pending'],
                'authoring_mode': 'provisional'}}
        E.prepare(self.root, self.request)
        self.ops = E.operations()

    def context(self, output='tasks/context-a', summary='Implement only the approved metric binding.'):
        path = self.request['output']
        packet = P.read_json(self.root / path)[0]
        request = {'schema_version': 1, 'kind': 'analyst_context_request',
            'packet': {'path': path, 'sha256': P.digest((self.root / path).read_bytes())}, 'mode': 'initial',
            'summary': summary, 'decisions': ['Retain grain'],
            'constraints': ['Preserve regional access'], 'stop_conditions': packet['stop_conditions'],
            'evidence': [{'id': 'original', 'path': 'inputs/original.txt',
                'sha256': P.digest((self.root / 'inputs/original.txt').read_bytes()), 'classification': 'internal',
                'purpose': 'Original analytical requirements', 'ranges': [[1, 1]], 'review_original': True}],
            'classification': 'internal', 'disclosure': {'allowed_classifications': ['internal'], 'review_ref': 'synthetic-local-review'},
            'shared_constraint_ids': []}
        return P.routing_helper('context_packets').build(self.root, request, output)

    def claim(self, context=None, identity='attempt-a'):
        request = {'attempt_id': identity, 'packet': self.request['output']}
        if context:
            request['context_receipt'] = context['receipt_path']
        return self.ops.claim(self.root, request)

    def dispatch(self):
        return self.ops.record_dispatch(self.root, {'attempt_id': 'attempt-a', 'host_run_reference': 'synthetic://host-a',
            'observed_model': None, 'observed_effort': None, 'requested_model': None, 'requested_effort': None,
            'execution_mode': 'specialist', 'fallback_reason': None})

    def test_typed_preparation_is_idempotent_and_conflict_preserves_original(self):
        before = (self.root / 'tasks/scoped.json').read_bytes()
        self.assertEqual(E.prepare(self.root, self.request)['status'], 'reused')
        changed = copy.deepcopy(self.request)
        changed['assignment']['objective'] = 'Different task'
        with self.assertRaisesRegex(ValueError, 'different work'):
            E.prepare(self.root, changed)
        self.assertEqual(before, (self.root / 'tasks/scoped.json').read_bytes())

    def test_bounded_policy_requires_receipt_and_detects_tampering(self):
        E.configure(self.root, {'policy': 'bounded-context-v1', 'reason': 'Adopt bounded local work'})
        # Policy changes the packet projection, so prepare a new immutable version.
        self.request['output'] = 'tasks/scoped-bounded.json'
        E.prepare(self.root, self.request)
        with self.assertRaisesRegex(ValueError, 'receipt required'):
            self.claim()
        context = self.context()
        self.claim(context)
        ready = self.ops.prepare_dispatch(self.root, {'attempt_id': 'attempt-a'})
        self.assertEqual(ready['context_mode_requested'], 'fresh')
        self.assertFalse(ready['agents_dispatched'])
        (self.root / context['task_path']).write_text('Tampered briefing')
        with self.assertRaisesRegex(ValueError, 'Context receipt'):
            self.dispatch()

    def test_policy_migration_preserves_history_and_refuses_active_worker(self):
        self.claim()
        with self.assertRaisesRegex(ValueError, 'Checkpoint active'):
            E.configure(self.root, {'policy': 'bounded-context-v1', 'reason': 'Migration'})
        self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'interrupted', 'reason': 'Host stopped', 'outputs': []})
        E.configure(self.root, {'policy': 'bounded-context-v1', 'reason': 'Migration'})
        self.assertEqual(E.configure(self.root, {'policy': 'bounded-context-v1', 'reason': 'Migration'})['status'], 'unchanged')
        E.configure(self.root, {'policy': 'legacy-index-v1', 'reason': 'Explicit compatibility rollback'})
        self.assertEqual(len(P.load_project(self.root)[1]['context_policy_history']), 2)

    def test_observed_usage_is_pinned_nullable_and_never_double_counted(self):
        self.claim(); self.dispatch()
        p = self.root / 'evidence/host.json'
        p.write_text('{"synthetic":true,"input_tokens":20}')
        request = {'attempt_id': 'attempt-a', 'observation_id': 'obs-a', 'host_run_reference': 'synthetic://host-a',
            'context_mode': 'unknown', 'evidence': {'path': 'evidence/host.json', 'sha256': P.digest(p.read_bytes())},
            'usage': {'input_tokens': 20, 'cache_read_tokens': None}}
        E.record_usage(self.root, request)
        E.record_usage(self.root, request)
        report = E.report(self.root)
        self.assertEqual(report['observed_usage']['input_tokens'], 20)
        self.assertIsNone(report['observed_usage']['output_tokens'])
        self.assertIsNone(report['dollars'])
        with self.assertRaisesRegex(ValueError, 'double count'):
            E.record_usage(self.root, dict(request, observation_id='obs-b'))
        p.write_text('{}')
        self.assertIsNone(E.report(self.root)['observed_usage']['input_tokens'])
        self.assertEqual(E.report(self.root)['stale_usage_observations'], ['obs-a'])

    def test_usage_cannot_attach_to_unobserved_or_different_invocation(self):
        self.claim()
        request = {'attempt_id': 'attempt-a', 'observation_id': 'obs-a', 'host_run_reference': 'synthetic://other',
                   'context_mode': 'fresh', 'evidence': {'path': 'inputs/original.txt', 'sha256': '0' * 64}}
        with self.assertRaisesRegex(ValueError, 'recorded host invocation'):
            E.record_usage(self.root, request)
        self.dispatch()
        with self.assertRaisesRegex(ValueError, 'recorded host invocation'):
            E.record_usage(self.root, request)

    def test_usage_cannot_count_one_host_invocation_across_attempts(self):
        self.claim(); self.dispatch()
        evidence = {'path': 'inputs/original.txt', 'sha256': P.digest((self.root / 'inputs/original.txt').read_bytes())}
        request = {'attempt_id': 'attempt-a', 'observation_id': 'one', 'host_run_reference': 'synthetic://host-a',
                   'context_mode': 'unknown', 'evidence': evidence, 'usage': {'input_tokens': 20}}
        E.record_usage(self.root, request)
        self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'interrupted', 'reason': 'Host stopped', 'outputs': []})
        self.claim(identity='attempt-b')
        dispatch = dict(self.dispatch_request(), attempt_id='attempt-b')
        self.ops.record_dispatch(self.root, dispatch)
        with self.assertRaisesRegex(ValueError, 'another attempt'):
            E.record_usage(self.root, dict(request, attempt_id='attempt-b', observation_id='two'))
        self.assertEqual(E.report(self.root)['observed_usage']['input_tokens'], 20)

    def dispatch_request(self):
        return {'attempt_id': 'attempt-a', 'host_run_reference': 'synthetic://host-a',
            'observed_model': None, 'observed_effort': None, 'requested_model': None, 'requested_effort': None,
            'execution_mode': 'specialist', 'fallback_reason': None}

    def test_completed_result_cannot_reuse_different_context_with_same_assignment(self):
        context = self.context()
        self.claim(context); self.dispatch()
        (self.root / 'deliverables/view.json').write_text('{}')
        self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'outputs_recorded', 'reason': 'Candidate retained',
                                      'outputs': ['deliverables/view.json']})
        self.assertEqual(self.claim(context, identity='same')['action'], 'reuse')
        changed = self.context('tasks/context-b', 'The requested scope now needs an additional original-source comparison.')
        self.assertEqual(self.claim(changed, identity='attempt-b')['action'], 'dispatch')

    def test_context_rewording_does_not_reset_repeated_blocker(self):
        context = self.context()
        self.claim(context)
        for n in range(2):
            E.record_blocker(self.root, {'attempt_id': 'attempt-a', 'event_id': 'e-' + str(n),
                'error_family': 'missing_observation', 'detail': 'Observation missing'})
        self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'interrupted', 'reason': 'Host stopped', 'outputs': []})
        reworded = self.context('tasks/context-b', 'Same binding, phrased differently.')
        with self.assertRaisesRegex(ValueError, 'Repeated unchanged blocker'):
            self.claim(reworded, identity='attempt-b')

    def test_repeated_state_stops_dispatch_but_changed_evidence_can_resume(self):
        self.claim()
        event = {'attempt_id': 'attempt-a', 'event_id': 'error-a', 'error_family': 'missing_observation', 'detail': 'Observation missing'}
        self.assertEqual(E.record_blocker(self.root, event)['status'], 'correction_available')
        self.assertEqual(E.record_blocker(self.root, event)['attempts'], 1)
        self.assertEqual(E.record_blocker(self.root, dict(event, event_id='error-b'))['status'], 'stop')
        with self.assertRaisesRegex(ValueError, 'Repeated unchanged blocker'):
            self.ops.prepare_dispatch(self.root, {'attempt_id': 'attempt-a'})
        # A real output change yields a different state, never a fabricated pass.
        (self.root / 'deliverables/view.json').write_text('{"observation":"retained"}')
        self.assertEqual(self.ops.prepare_dispatch(self.root, {'attempt_id': 'attempt-a'})['status'], 'ready')

    def test_renaming_task_does_not_reset_unchanged_blocker(self):
        self.claim()
        for n in range(2):
            E.record_blocker(self.root, {'attempt_id': 'attempt-a', 'event_id': 'e-' + str(n),
                'error_family': 'unchanged', 'detail': 'Same blocker'})
        self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'interrupted', 'reason': 'Host stopped', 'outputs': []})
        self.request['assignment']['task_id'] = 'renamed'
        self.request['output'] = 'tasks/renamed.json'
        E.prepare(self.root, self.request)
        with self.assertRaisesRegex(ValueError, 'Repeated unchanged blocker'):
            self.claim(identity='attempt-renamed')

    def test_preflight_collects_multiple_blockers_without_dispatch(self):
        E.configure(self.root, {'policy': 'bounded-context-v1', 'reason': 'Test'})
        report = E.preflight(self.root, {'packet': 'tasks/missing.json'})
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual({f['area'] for f in report['blockers']}, {'packet', 'context'})
        self.assertFalse(report['agents_dispatched'])

    def test_equivalent_evidence_order_and_adjacent_ranges_do_not_reset_retry(self):
        # Signature comparison isolates the repeated-state decision. Normal dispatch
        # separately verifies the complete context receipt and source bindings.
        self.claim()
        record = P.read_json(self.root / 'task-operations.json')[0]['attempts'][0]
        path = self.root / 'tasks/retry-context.json'
        a = {'path': 'inputs/a.txt', 'sha256': 'a' * 64, 'ranges': [[1, 2]]}
        b = {'path': 'inputs/b.txt', 'sha256': 'b' * 64, 'ranges': [[4, 6]]}
        path.write_text(json.dumps({'request': {'evidence': [a, b]}}))
        record['context'] = {'receipt_path': 'tasks/retry-context.json'}
        record['assignment']['outputs'] = ['deliverables/a.json', 'deliverables/b.json']
        original = E.retry_key(self.root, record, 'same_error')
        a['ranges'] = [[1, 1], [2, 2]]
        path.write_text(json.dumps({'request': {'evidence': [b, a]}}))
        record['assignment']['outputs'].reverse()
        self.assertEqual(original, E.retry_key(self.root, record, 'same_error'))
        a['ranges'] = [[1, 3]]
        path.write_text(json.dumps({'request': {'evidence': [b, a]}}))
        self.assertNotEqual(original, E.retry_key(self.root, record, 'same_error'))

    def test_cli_new_project_defaults_bounded_without_changing_library_legacy(self):
        destination = self.root.parent / 'new-cli'
        r = subprocess.run([sys.executable, '-I', '-S', '-B', str(SCRIPT), 'init', '--output', str(destination),
            '--name', 'Synthetic new project', '--mode', 'net-new', '--surface', 'app'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(P.load_project(destination)[1]['context_policy'], 'bounded-context-v1')
        self.assertNotIn('context_policy', P.load_project(self.root)[1])


if __name__ == '__main__':
    unittest.main()
