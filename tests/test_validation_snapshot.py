"""Original local byte/lock fixtures; no host, gate or native qualification claims."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts'
spec = importlib.util.spec_from_file_location('snapshot_project_fixture', SCRIPTS / 'analyst_project.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
V = P.validation_helper()
O = P.routing_helper('task_operations')
W = P.routing_helper('delivery_workflow')


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        self.root.mkdir()
        self.input = self.root / 'input.json'
        self.input.write_text('{"value":1}')

    def test_repeated_reads_and_json_derivations_are_reused_then_verified(self):
        with P.validation_operation(self.root) as scope:
            first, raw = P.read_json(self.input)
            first['value'] = 999
            second, other = P.read_json(self.input)
            self.assertEqual(second, {'value': 1})
            self.assertEqual(raw, other)
        counters = scope.counters()
        self.assertEqual(counters['file_reads'], 1)
        self.assertEqual(counters['read_reuses'], 1)
        self.assertEqual(counters['derivation_reuses'], 1)
        self.assertEqual(counters['verification_reads'], 1)
        self.assertEqual(counters['file_bytes'], len(raw))
        self.assertTrue(all(type(v) in (int, float) for v in counters.values()))

    def test_same_size_changed_bytes_with_restored_mtime_fail_final_verification(self):
        stamp = self.input.stat()
        with self.assertRaisesRegex(V.Changed, 'evidence_changed'):
            with P.validation_operation(self.root):
                self.assertEqual(P.read_json(self.input)[0]['value'], 1)
                self.input.write_text('{"value":2}')
                os.utime(self.input, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                # A repeat is the operation's retained snapshot, not a new claim
                # about the path. The enclosing operation must not return it.
                self.assertEqual(P.read_json(self.input)[0]['value'], 1)

    def test_relative_path_tracks_legacy_direct_reader_evidence(self):
        with self.assertRaisesRegex(V.Changed, 'evidence_changed'):
            with P.validation_operation(self.root):
                path = P.relative_file(self.root, 'input.json')
                self.assertEqual(path.read_bytes(), b'{"value":1}')
                self.input.write_text('{"value":2}')

    def test_stage_checks_are_fresh_and_final_observers_are_deduplicated(self):
        calls = []
        def require(root, action, provider):
            calls.append(action)
            return {'status': 'ready', 'value': P.read_json(self.input)[0]['value']}
        stage = SimpleNamespace(require_action=require, _host_provider_context=SimpleNamespace(get=lambda: None))
        with patch.object(P, 'routing_helper', return_value=stage):
            with P.validation_operation(self.root) as scope:
                P.stage_require(self.root, 'analysis')
                P.stage_require(self.root, 'analysis')
                self.assertEqual(calls, ['analysis', 'analysis'])
                self.assertEqual(len(scope._observers), 1)
        self.assertEqual(calls, ['analysis', 'analysis', 'analysis'])
        self.assertEqual(scope.counters()['verification_reads'], 2)

    def test_final_stage_observer_detects_evidence_outside_ledger_reader(self):
        def inspect(root, provider):
            return {'status': 'ready', 'source': self.input.read_text()}
        stage = SimpleNamespace(inspect=inspect, _host_provider_context=SimpleNamespace(get=lambda: None))
        with patch.object(P, 'routing_helper', return_value=stage):
            with self.assertRaisesRegex(V.Changed, 'authoritative_state_changed'):
                with P.validation_operation(self.root):
                    P.stage_status(self.root)
                    self.input.write_text('{"value":2}')

    def test_final_stage_observer_does_not_reuse_provider_decision(self):
        decisions = iter([{'status': 'ready'}, {'status': 'blocked'}])
        stage = SimpleNamespace(inspect=lambda root, provider: next(decisions),
                                _host_provider_context=SimpleNamespace(get=lambda: object()))
        with patch.object(P, 'routing_helper', return_value=stage):
            with self.assertRaisesRegex(V.Changed, 'authoritative_state_changed'):
                with P.validation_operation(self.root):
                    P.stage_status(self.root)

    def test_new_operation_and_nested_scope_do_not_reuse_old_bytes(self):
        with P.validation_operation(self.root) as outer:
            P.read_json(self.input)
            with P.validation_operation(self.root):
                P.read_json(self.input)
        self.assertEqual(outer.counters()['file_reads'], 2)
        self.input.write_text('{"value":2}')
        with P.validation_operation(self.root) as next_scope:
            self.assertEqual(P.read_json(self.input)[0]['value'], 2)
        self.assertEqual(next_scope.counters()['read_reuses'], 0)
        with self.assertRaisesRegex(ValueError, 'scope_closed'):
            next_scope.read(self.input, 100)

    def test_threads_do_not_inherit_read_snapshots(self):
        seen = []
        with P.validation_operation(self.root):
            P.read_json(self.input)
            thread = threading.Thread(target=lambda: seen.append(V.active()))
            thread.start()
            thread.join(2)
        self.assertEqual(seen, [None])

    def test_scope_is_shared_by_fixed_first_party_helper_instances(self):
        self.assertIs(P.validation_helper(), O.ap.validation_helper())
        self.assertIs(P.validation_helper(), W.P.validation_helper())
        with P.validation_operation(self.root) as scope:
            P.read_json(self.input)
            O.ap.read_json(self.input)
        self.assertEqual(scope.counters()['file_reads'], 1)

    def test_input_limit_and_nonregular_or_symlink_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'bounded_regular'):
            P.read_bytes(self.input, 2)
        link = self.root / 'link.json'
        link.symlink_to(self.input)
        with self.assertRaises(OSError):
            P.read_bytes(link)
        fifo = self.root / 'pipe'
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'bounded_regular'):
            P.read_bytes(fifo)
        directory_link = self.root / 'linked'
        directory_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            P.read_bytes(directory_link / 'input.json')

    def test_path_replaced_by_symlink_fails_at_final_boundary(self):
        other = self.root / 'other.json'
        other.write_bytes(self.input.read_bytes())
        with self.assertRaisesRegex(V.Changed, 'unavailable'):
            with P.validation_operation(self.root):
                P.read_json(self.input)
                self.input.unlink()
                self.input.symlink_to(other)

    def test_read_scope_cannot_write_or_enter_mutation_ledger(self):
        with P.validation_operation(self.root):
            with self.assertRaises(V.MutationDenied):
                P.private_write(self.root / 'output.txt', b'no write')
            with self.assertRaises(V.MutationDenied):
                with O.locked(self.root):
                    pass
        self.assertFalse((self.root / 'output.txt').exists())
        self.assertFalse((self.root / '.task-operations.lock').exists())

    def test_absent_project_or_journal_creation_invalidates_operation(self):
        with self.assertRaisesRegex(V.Changed, 'inventory_changed'):
            with P.validation_operation(self.root):
                (self.root / 'stage-gates.json').write_text('{}')

    def test_expiry_crossing_is_detected_without_reusing_a_gate_decision(self):
        self.input.write_text('{"expires_at":"2030-01-01T00:00:00+00:00"}')
        before = datetime(2029, 1, 1, tzinfo=timezone.utc)
        after = datetime(2031, 1, 1, tzinfo=timezone.utc)
        with patch.object(V, 'datetime', wraps=datetime) as clock:
            clock.now.side_effect = [before, after]
            with self.assertRaisesRegex(V.Changed, 'expired_during_operation'):
                with P.validation_operation(self.root):
                    P.read_json(self.input)

    def test_source_manifest_reuses_hashes_but_detects_inventory_additions(self):
        package = Path(self.temp.name).resolve() / 'package'
        package.mkdir()
        (package / 'package.json').write_text('{}')
        (package / 'skills').mkdir()
        (package / 'skills' / 'first.py').write_text('# original fixture\n')
        expected = W.source_manifest(package)
        with P.validation_operation(self.root) as scope:
            self.assertEqual(W.source_manifest(package), expected)
            self.assertEqual(W.source_manifest(package), expected)
        self.assertEqual(scope.counters()['file_reads'], 2)
        self.assertGreaterEqual(scope.counters()['derivation_reuses'], 1)
        with self.assertRaisesRegex(V.Changed, 'inventory_changed'):
            with P.validation_operation(self.root):
                W.source_manifest(package)
                (package / 'skills' / 'new.py').write_text('# new fixture\n')

    def test_package_content_change_and_budget_fail_closed(self):
        with patch.object(V, 'MAX_RETAINED_BYTES', 2):
            with self.assertRaisesRegex(ValueError, 'budget_exceeded'):
                with P.validation_operation(self.root):
                    P.read_json(self.input)
        with P.validation_operation(self.root) as scope:
            self.assertEqual(P.read_bytes(self.input), b'{"value":1}')
            with self.assertRaisesRegex(ValueError, 'file_too_large'):
                scope.read(self.input, 2)


class StatusSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = {'schema_version': 1, 'kind': 'omni_analyst_project', 'id': 'original-fixture',
            'name': 'Original status fixture', 'mode': 'enhancement', 'surfaces': ['app'],
            'sources': [], 'artifacts': [], 'decisions': [], 'open_questions': []}
        (self.root / 'project.json').write_text(json.dumps(self.project))
        (self.root / 'START_HERE.md').write_text('# Original fixture\n')
        (self.root / 'input.txt').write_bytes(b'original')
        self.input_sha = P.digest(b'original')
        self.assignment = {'domain_id': 'observations', 'stage': 'app', 'role': 'app-engineer',
            'authoring_mode': 'provisional', 'outputs': ['candidate.json'], 'unknowns': []}
        self.state = {'schema_version': 1, 'project_id': self.project['id'], 'max_workers': 2,
            'reuse_count': 0, 'attempts': [{'attempt_id': 'attempt-one', 'task_id': 'task-one',
            'assignment': self.assignment, 'packet': 'packet.json', 'packet_sha256': 'a' * 64,
            'status': 'active', 'outputs': {}, 'dispatch': None}]}
        (self.root / 'task-operations.json').write_text(json.dumps(self.state))
        self.calls = 0
        self.patch = patch.object(O, 'read_packet', side_effect=self.read_packet)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def read_packet(self, root, project, path):
        self.calls += 1
        P.need(P.digest(P.read_bytes(root / 'input.txt')) == self.input_sha, 'Fixture input changed')
        return copy.deepcopy(self.assignment), 'a' * 64

    def writer(self, value):
        with O.locked(self.root) as (_, _, state):
            state['reuse_count'] = value

    def test_equivalent_task_rows_and_html_are_preserved(self):
        expected = O._status_rows(self.root, self.project, self.state)['tasks']
        result = O.status(self.root, 'progress.html')
        self.assertEqual(result['tasks'], expected)
        self.assertEqual(result['status'], 'consistent')
        self.assertFalse(result['incomplete'])
        self.assertIn('Original', (self.root / 'START_HERE.md').read_text())
        self.assertIn('Task progress', (self.root / 'progress.html').read_text())
        self.assertEqual(P.read_json(self.root / 'task-operations.json')[0], self.state)

    def test_expensive_validation_does_not_hold_writer_lock_and_retries_once(self):
        def validate(root, project, path):
            value = self.read_packet(root, project, path)
            if self.calls == 1:
                done = threading.Event()
                worker = threading.Thread(target=lambda: (self.writer(1), done.set()))
                worker.start()
                self.assertTrue(done.wait(2), 'Writer was blocked by the status validator')
                worker.join(2)
            return value
        with patch.object(O, 'read_packet', side_effect=validate):
            result = O.status(self.root)
        self.assertEqual(result['retry_count'], 1)
        self.assertEqual(result['reuse_count'], 1)
        self.assertEqual(self.calls, 2)
        self.assertEqual(result['status'], 'consistent')

    def test_continuous_ledger_changes_return_incomplete_without_task_claims(self):
        def validate(root, project, path):
            value = self.read_packet(root, project, path)
            worker = threading.Thread(target=self.writer, args=(self.calls,))
            worker.start()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            return value
        with patch.object(O, 'read_packet', side_effect=validate):
            result = O.status(self.root)
        self.assertEqual(self.calls, 2)
        self.assertEqual(result['status'], 'changed')
        self.assertTrue(result['incomplete'])
        self.assertEqual(result['tasks'], [])
        self.assertFalse(result['execution_verified'])

    def test_changed_evidence_retries_then_marks_the_task_stale(self):
        def validate(root, project, path):
            value = self.read_packet(root, project, path)
            if self.calls == 1:
                source = root / 'input.txt'
                before = source.stat()
                source.write_bytes(b'replaced')
                os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
            return value
        with patch.object(O, 'read_packet', side_effect=validate):
            result = O.status(self.root)
        self.assertEqual(result['retry_count'], 1)
        self.assertEqual(result['status'], 'consistent')
        self.assertEqual(result['tasks'][0]['status'], 'stale')

    def test_preflight_uses_read_scope_and_never_takes_mutation_lock(self):
        with patch.object(O, 'check_context', return_value=None), \
                patch.object(O.ap, 'routing_helper') as routing:
            routing.return_value.require_no_loop.return_value = None
            with P.validation_operation(self.root):
                result = O.prepare_dispatch(self.root, {'attempt_id': 'attempt-one'})
        self.assertEqual(result['status'], 'ready')
        self.assertFalse(result['agents_dispatched'])
        self.assertEqual(P.read_json(self.root / 'task-operations.json')[0], self.state)

    def test_partial_interrupted_outputs_keep_existing_status_semantics(self):
        state = copy.deepcopy(self.state)
        state['attempts'][0].update(status='interrupted', outputs={'candidate.json': 'b' * 64})
        (self.root / 'task-operations.json').write_text(json.dumps(state))
        result = O.status(self.root)
        self.assertEqual(result['tasks'][0]['status'], 'interrupted')

    def test_interrupted_missing_review_outputs_keep_task_and_review_states_separate(self):
        state = copy.deepcopy(self.state)
        state['attempts'][0].update(status='interrupted', outputs={'candidate.json': 'b' * 64},
                                    review={'state': 'original incomplete review'})
        (self.root / 'task-operations.json').write_text(json.dumps(state))
        result = O.status(self.root)
        self.assertEqual(result['tasks'][0]['status'], 'interrupted')
        self.assertEqual(result['tasks'][0]['review_status'], 'stale')


if __name__ == '__main__':
    unittest.main()
