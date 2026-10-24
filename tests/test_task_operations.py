"""Local lifecycle qualification; synthetic host receipts are not live execution."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts'
spec = importlib.util.spec_from_file_location('operations_test_project', SCRIPTS / 'analyst_project.py')
ap = importlib.util.module_from_spec(spec); spec.loader.exec_module(ap)
ops = ap.routing_helper('task_operations')


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'project'
        ap.init(self.root, 'Synthetic commerce', 'migration', 'dashboard', branding='none')
        # Historical migration routing; A–F integration uses fresh gated projects separately.
        legacy = ap.load_project(self.root)[1]
        legacy.pop('stage_gate_policy')
        ap.write_json(self.root / 'project.json', legacy, replace=True)
        (self.root / 'inputs/orders.json').write_text('{"grain":"order"}')
        self.packet = self.prepare('orders')

    def prepare(self, name, path=None):
        # Legacy packet stays supported and provides the exact bounded input index.
        index = ap.packet(self.root, 'bi-engineer', ['inputs/orders.json'], None)
        assignment = {'schema_version': 1, 'task_id': name, 'domain_id': 'commerce', 'stage': 'dashboard',
                      'role': 'bi-engineer', 'scope_ids': ['orders'], 'objective': 'Bind order revenue to the Topic',
                      'outputs': ['deliverables/' + name + '.json'], 'acceptance': ['Preserve order grain and filters'],
                      'input_bindings': {r['path']: r['sha256'] for r in index['inputs']}, 'dependencies': {},
                      'unknowns': ['Native query results unverified'], 'authoring_mode': 'provisional'}
        path = path or 'tasks/' + name + '.json'
        ap.packet(self.root, 'bi-engineer', ['inputs/orders.json'], self.root / path, assignment)
        return path

    def claim(self, identity='attempt-1', packet=None):
        return ops.claim(self.root, {'attempt_id': identity, 'packet': packet or self.packet})

    def dispatch(self, identity='attempt-1'):
        return ops.record_dispatch(self.root, {'attempt_id': identity, 'host_run_reference': 'synthetic://builder',
            'observed_model': None, 'observed_effort': None, 'requested_model': None, 'requested_effort': None,
            'execution_mode': 'specialist', 'fallback_reason': None})

    def test_concurrent_duplicate_claims_reserve_only_one_worker_and_complete_reuses(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.claim, ['attempt-1', 'attempt-2']))
        self.assertEqual(sorted(r['action'] for r in results), ['already_active', 'dispatch'])
        identity = next(r['attempt_id'] for r in results if r['action'] == 'dispatch')
        self.assertEqual(ops.status(self.root)['tasks'][0]['status'], 'reserved')
        self.assertEqual(ops.prepare_dispatch(self.root, {'attempt_id': identity})['status'], 'ready')
        self.dispatch(identity)
        (self.root / 'deliverables/orders.json').write_text('{"topic":"orders"}')
        ops.checkpoint(self.root, {'attempt_id': identity, 'status': 'outputs_recorded', 'reason': 'Candidate retained',
                                  'outputs': ['deliverables/orders.json']})
        self.assertEqual(self.claim('attempt-3')['action'], 'reuse')
        self.assertFalse(ops.status(self.root)['execution_verified'])

    def test_interruption_resume_and_input_drift_do_not_reuse_stale_outputs(self):
        self.claim()
        ops.checkpoint(self.root, {'attempt_id': 'attempt-1', 'status': 'interrupted', 'reason': 'Host confirmed stopped', 'outputs': []})
        resumed = self.claim('attempt-2')
        self.assertEqual(resumed['resumes_attempt_id'], 'attempt-1')
        (self.root / 'inputs/orders.json').write_text('{"grain":"order","filter":"not_deleted"}')
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.dispatch('attempt-2')
        self.assertEqual(ops.status(self.root)['tasks'][0]['status'], 'stale')
        ops.checkpoint(self.root, {'attempt_id': 'attempt-2', 'status': 'interrupted', 'reason': 'Inputs revised; host stopped', 'outputs': []})
        revised = self.prepare('orders', 'tasks/orders-v2.json')
        self.assertEqual(self.claim('attempt-3', revised)['action'], 'dispatch')

    def test_missing_assignment_wrong_role_and_source_writes_are_rejected(self):
        packet, _ = ap.read_json(self.root / self.packet)
        for update in ({'role': 'app-engineer'}, {'outputs': ['inputs/orders.json']},
                       {'outputs': ['INPUTS/orders.json']}, {'outputs': ['TASKS/new.json']}, {'scope_ids': []}):
            value = copy.deepcopy(packet['assignment']); value.update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                ap.packet(self.root, 'bi-engineer', ['inputs/orders.json'], self.root / 'tasks/bad.json', value)
        legacy = 'tasks/legacy.json'
        ap.packet(self.root, 'bi-engineer', ['inputs/orders.json'], self.root / legacy)
        with self.assertRaisesRegex(ValueError, 'assignment'):
            self.claim(packet=legacy)
        self.assertFalse((self.root / 'task-operations.json').exists())

    def test_changed_packet_partial_completion_and_ownership_conflict_fail(self):
        self.claim()
        with self.assertRaisesRegex(ValueError, 'every assigned'):
            ops.checkpoint(self.root, {'attempt_id': 'attempt-1', 'status': 'outputs_recorded', 'reason': 'No files', 'outputs': []})
        packet, _ = ap.read_json(self.root / self.packet)
        packet['objective'] = 'Changed'
        (self.root / self.packet).write_text(json.dumps(packet))
        with self.assertRaisesRegex(ValueError, 'packet changed'):
            self.dispatch()
        with self.assertRaisesRegex(ValueError, 'packet changed'):
            ops.prepare_dispatch(self.root, {'attempt_id': 'attempt-1'})

    def test_review_consolidation_status_html_and_legacy_project_still_work(self):
        self.claim(); self.dispatch()
        (self.root / 'deliverables/orders.json').write_text('{"topic":"orders"}')
        result = ops.review_work(self.root, {'attempt_id': 'attempt-1', 'action': 'start'})
        self.assertEqual(result['decision']['action'], 'wait')
        for review in result['review']['plan']['reviews']:
            result = ops.review_work(self.root, {'attempt_id': 'attempt-1', 'action': 'record', 'result': {
                'review_id': review['id'], 'candidate_sha256': result['review']['candidate_sha256'], 'verdict': 'pass',
                'findings': [], 'reviewer_reference': 'synthetic://independent', 'execution_mode': 'specialist'}})
        self.assertEqual(result['decision']['action'], 'reviews_complete')
        summary = ops.status(self.root, 'TASK_PROGRESS.html')
        self.assertEqual(summary['tasks'][0]['review_status'], 'reviews_complete')
        self.assertIn('Snapshot', (self.root / 'TASK_PROGRESS.html').read_text())
        self.assertIn('Task progress and recorded outputs', (self.root / 'START_HERE.md').read_text())
        self.assertEqual(ap.project_check(self.root)['status'], 'consistent')

    def test_completed_candidate_correction_reserves_new_worker_and_checkpoint(self):
        self.claim(); self.dispatch()
        candidate = self.root / 'deliverables/orders.json'; candidate.write_text('{"topic":"orders"}')
        ops.checkpoint(self.root, {'attempt_id': 'attempt-1', 'status': 'outputs_recorded', 'reason': 'First candidate',
                                  'outputs': ['deliverables/orders.json']})
        result = ops.review_work(self.root, {'attempt_id': 'attempt-1', 'action': 'start'})
        for review in result['review']['plan']['reviews']:
            finding = {'id': 'filter', 'severity': 'blocking', 'message': 'Preserve the deleted filter',
                       'evidence': ['Source filter contract'], 'affected_ids': ['orders'], 'acceptance': 'Filter applied'}
            result = ops.review_work(self.root, {'attempt_id': 'attempt-1', 'action': 'record', 'result': {
                'review_id': review['id'], 'candidate_sha256': result['review']['candidate_sha256'], 'verdict': 'changes',
                'findings': [finding], 'reviewer_reference': 'synthetic://independent', 'execution_mode': 'specialist'}})
        ops.review_work(self.root, {'attempt_id': 'attempt-1', 'action': 'correct', 'correction_attempt_id': 'correction-1'})
        with self.assertRaisesRegex(ValueError, 'already reserved'):
            ops.review_work(self.root, {'attempt_id': 'attempt-1', 'action': 'correct', 'correction_attempt_id': 'correction-2'})
        self.dispatch('correction-1')
        candidate.write_text('{"topic":"orders","filter":"not_deleted"}')
        revised = ops.review_work(self.root, {'attempt_id': 'correction-1', 'action': 'revise'})
        self.assertEqual(revised['review']['correction_count'], 1)
        ops.checkpoint(self.root, {'attempt_id': 'correction-1', 'status': 'outputs_recorded', 'reason': 'Correction retained',
                                  'outputs': ['deliverables/orders.json']})
        self.assertEqual(self.claim('attempt-3')['action'], 'reuse')
        self.assertNotEqual(ops.status(self.root)['tasks'][0]['status'], 'stale')


if __name__ == '__main__':
    unittest.main()
