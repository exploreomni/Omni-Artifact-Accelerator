"""Original synthetic host exercises; no real model, tenant or authority."""
import copy
import importlib.util
from pathlib import Path
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = load('runtime_test_fixtures', ROOT / 'tests/test_execution_efficiency.py')
R = load('runtime_test_source', F.SCRIPT.with_name('execution_runtime.py'))


class ObservedDriver:
    def __init__(self):
        self.payloads = []
        self.outcome = 'active'
        self.fail_after_launch = False
        self.extra_tool = False

    def result(self, payload):
        return {'launch_id': payload['launch_id'], 'status': self.outcome,
            'host_run_reference': 'synthetic-invocation-' + payload['launch_id'],
            'task_sha256': payload['task_sha256'], 'context_mode': 'fresh',
            'observed_model': None, 'observed_effort': None,
            'tool_scope': ['file_read'] + (['unexpected'] if self.extra_tool else []),
            'evidence_reference': 'synthetic-process-observation'}

    def launch(self, payload):
        self.payloads.append(copy.deepcopy(payload))
        if self.fail_after_launch:
            raise TimeoutError('A sensitive driver message must not be returned')
        return self.result(payload)

    def reconcile(self, launch_id):
        return self.result(next(p for p in self.payloads if p['launch_id'] == launch_id))


class RuntimeTests(F.EfficiencyTests):
    # Inherited setup only; base cases remain in their original focused suite.
    def setUp(self):
        super().setUp()
        F.E.configure(self.root, {'policy': 'bounded-context-v1', 'reason': 'Bounded test'})
        self.request['output'] = 'tasks/bounded.json'
        F.E.prepare(self.root, self.request)
        self.receipt = self.context()
        self.claim(self.receipt)
        self.driver = ObservedDriver()
        self.binding = {'adapter_id': 'synthetic-observer', 'adapter_version': '1', 'host_version': '1',
            'configuration_sha256': 'a' * 64, 'tool_scope': ['file_read'], 'context_mode': 'fresh',
            'model': None, 'effort': None}
        self.runtime = R.Runtime(self.root, self.driver, self.binding)

    def test_launch_sends_actual_bounded_bytes_and_never_launches_twice(self):
        result = self.runtime.launch('attempt-a')
        self.assertEqual(result['status'], 'active')
        self.assertEqual(self.driver.payloads[0]['task_utf8'], (self.root / self.receipt['task_path']).read_text())
        self.assertFalse(result['host_isolation_verified'])
        self.assertEqual(self.runtime.launch('attempt-a')['status'], 'reconcile_required')
        self.assertEqual(len(self.driver.payloads), 1)

    def test_concurrent_launches_share_one_durable_intent(self):
        outcomes, failures = [], []
        def run():
            try:
                outcomes.append(self.runtime.launch('attempt-a'))
            except Exception as exc:
                failures.append(exc)
        workers = [threading.Thread(target=run) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
        self.assertFalse(failures)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(len(self.driver.payloads), 1)

    def test_reconciliation_cannot_mark_absent_during_launch(self):
        entered, release = threading.Event(), threading.Event()
        original = self.driver.launch
        def blocked(payload):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('Fixture timed out')
            return original(payload)
        self.driver.launch = blocked
        worker = threading.Thread(target=lambda: self.runtime.launch('attempt-a'))
        worker.start()
        self.assertTrue(entered.wait(5))
        try:
            self.assertEqual(self.runtime.reconcile('attempt-a')['status'], 'busy')
            with self.assertRaisesRegex(ValueError, 'termination'):
                self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'interrupted', 'outputs': [], 'reason': 'Not actually absent'})
        finally:
            release.set()
            worker.join(5)
        self.assertEqual(len(self.driver.payloads), 1)

    def test_inline_reservation_cannot_launch_a_hidden_worker(self):
        # Inline execution remains a separate reported workflow; it is not a way
        # to bypass the specialist concurrency limit through this adapter.
        with self.ops.locked(self.root) as (_, _, state):
            state['attempts'][0]['execution_mode'] = 'inline'
        with self.assertRaisesRegex(ValueError, 'specialist reservation'):
            self.runtime.launch('attempt-a')
        self.assertEqual(self.driver.payloads, [])

    def test_timeout_after_launch_keeps_reservation_until_reconciliation(self):
        self.driver.fail_after_launch = True
        result = self.runtime.launch('attempt-a')
        self.assertEqual(result['status'], 'unknown')
        self.assertNotIn('sensitive', str(result))
        with self.assertRaisesRegex(ValueError, 'termination'):
            self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'interrupted', 'outputs': [], 'reason': 'Lost connection'})
        self.assertEqual(self.runtime.launch('attempt-a')['status'], 'reconcile_required')
        self.driver.outcome = 'completed'
        self.assertEqual(self.runtime.reconcile('attempt-a')['status'], 'completed')
        (self.root / 'deliverables/view.json').write_text('{"result":1}')
        self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'outputs_recorded', 'outputs': ['deliverables/view.json'], 'reason': 'Observed complete'})
        self.assertEqual(self.claim(self.receipt, 'later')['action'], 'reuse')
        self.assertEqual(len(self.driver.payloads), 1)

    def test_unexpected_tool_scope_is_unknown_not_a_verified_dispatch(self):
        self.driver.extra_tool = True
        self.assertEqual(self.runtime.launch('attempt-a')['status'], 'unknown')
        self.assertIsNone(F.P.read_json(self.root / 'task-operations.json')[0]['attempts'][0]['dispatch'])

    def test_restart_reconciles_original_invocation(self):
        self.runtime.launch('attempt-a')
        restarted = R.Runtime(self.root, self.driver, self.binding)
        self.driver.outcome = 'completed'
        self.assertEqual(restarted.reconcile('attempt-a')['status'], 'completed')
        self.assertEqual(len(self.driver.payloads), 1)

    def test_changed_configuration_cannot_take_over(self):
        self.runtime.launch('attempt-a')
        changed = copy.deepcopy(self.binding)
        changed['configuration_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'Original host'):
            R.Runtime(self.root, self.driver, changed).reconcile('attempt-a')

    def test_manual_receipt_cannot_poison_managed_reconciliation(self):
        self.driver.fail_after_launch = True
        self.runtime.launch('attempt-a')
        with self.assertRaisesRegex(ValueError, 'host reconciliation'):
            self.dispatch()
        self.driver.outcome = 'completed'
        self.assertEqual(self.runtime.reconcile('attempt-a')['status'], 'completed')

    def test_terminal_observation_remains_possible_at_history_bound(self):
        self.runtime.launch('attempt-a')
        with self.ops.locked(self.root) as (_, _, state):
            launch = state['attempts'][0]['host_launch']
            launch['observations'] = [copy.deepcopy(launch['observations'][0]) for _ in range(100)]
        self.assertEqual(self.runtime.reconcile('attempt-a')['status'], 'active')
        self.driver.outcome = 'completed'
        self.assertEqual(self.runtime.reconcile('attempt-a')['status'], 'completed')

    def test_explicit_model_or_effort_cannot_silently_change(self):
        binding = dict(self.binding, model='configured-model', effort='configured-effort')
        runtime = R.Runtime(self.root, self.driver, binding)
        self.assertEqual(runtime.launch('attempt-a')['status'], 'unknown')
        self.assertIsNone(F.P.read_json(self.root / 'task-operations.json')[0]['attempts'][0]['dispatch'])

    def test_stale_task_denies_launch_before_any_side_effect(self):
        (self.root / 'inputs/original.txt').write_text('Changed source')
        with self.assertRaises(ValueError):
            self.runtime.launch('attempt-a')
        self.assertEqual(self.driver.payloads, [])

    def test_same_blocker_stops_launch(self):
        for identity in ('one', 'two'):
            F.E.record_blocker(self.root, {'attempt_id': 'attempt-a', 'event_id': identity,
                'error_family': 'missing_evidence', 'detail': 'No relevant change'})
        with self.assertRaisesRegex(ValueError, 'Repeated unchanged'):
            self.runtime.launch('attempt-a')
        self.assertEqual(self.driver.payloads, [])

    def test_failed_worker_cannot_claim_completed_outputs(self):
        self.driver.outcome = 'failed'
        self.runtime.launch('attempt-a')
        (self.root / 'deliverables/view.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'observed host completion'):
            self.ops.checkpoint(self.root, {'attempt_id': 'attempt-a', 'status': 'outputs_recorded', 'outputs': ['deliverables/view.json'], 'reason': 'Wrong completion'})


# Avoid rerunning the parent fixture's tests with a different setup.
for _name in list(F.EfficiencyTests.__dict__):
    if _name.startswith('test_') and _name not in RuntimeTests.__dict__:
        setattr(RuntimeTests, _name, None)


if __name__ == '__main__':
    unittest.main()
