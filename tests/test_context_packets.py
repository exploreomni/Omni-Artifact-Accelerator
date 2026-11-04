"""Original local context fixtures; no host/model/isolation or release qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('bounded_context_tests',
    ROOT / 'skills/omni-artifact-accelerator/scripts/context_packets.py')
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
P = C.P


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic bounded work', 'enhancement', 'app', 'none')
        project = P.load_project(self.root)[1]
        project.pop('stage_gate_policy', None)
        project.pop('workflow_quality_policy', None)
        project.pop('context_policy', None)
        P.write_json(self.root / 'project.json', project, replace=True)
        self.original = 'inputs/original.txt'
        (self.root / self.original).write_text('Original observation A\nOriginal observation B\nUnrelated observation C\n')
        spec = P.intent_helper().starter(['app'], 'none')
        spec['requirements'] = [self.requirement('work', 'experience'),
                                self.requirement('shared-stop', 'restriction'),
                                self.requirement('elsewhere', 'experience')]
        (self.root / 'contracts/spec.json').write_text(json.dumps(spec))
        P.intent_helper().select(self.root, self.root / 'contracts/spec.json', 'contracts/selected.json')
        self.save_packet()

    def requirement(self, identity, category):
        return {'id': identity, 'category': category, 'purpose': 'Synthetic ' + identity,
                'surfaces': ['app'], 'required': True, 'origin': 'user', 'disposition': 'selected',
                'value': 'No external activation' if category == 'restriction' else 'Scoped observation',
                'asset_ids': [], 'decision_ref': 'inputs/original.txt',
                'contexts': [{'id': 'ready', 'appearance': 'light', 'state': 'ready'}]}

    def save_packet(self, role='data-analyst', filename='tasks/task.json', input_path=None):
        inputs = [input_path or self.original]
        preview = P.packet(self.root, role, inputs, None)
        assignment = {'schema_version': 1, 'task_id': 'bounded-task', 'domain_id': 'synthetic',
                      'stage': 'validation' if role == 'qa-analyst' else 'discovery', 'role': role,
                      'scope_ids': ['work'], 'objective': 'Check one original observation',
                      'outputs': ['deliverables/result.md'], 'acceptance': ['Cite original evidence'],
                      'input_bindings': {r['path']: r['sha256'] for r in preview['inputs']},
                      'dependencies': {}, 'unknowns': [], 'authoring_mode': 'provisional'}
        target = self.root / filename
        if target.exists():
            target.unlink()
        self.packet = P.packet(self.root, role, inputs, target, assignment)
        self.packet_path = filename
        self.request = {'schema_version': 1, 'kind': 'analyst_context_request',
            'packet': {'path': filename, 'sha256': C.digest(target.read_bytes())},
            'mode': 'initial', 'summary': 'Check observation A against the original.', 'decisions': [],
            'constraints': ['Use only selected evidence'], 'stop_conditions': list(self.packet['stop_conditions']),
            'shared_constraint_ids': ['shared-stop'], 'classification': 'internal',
            'disclosure': {'allowed_classifications': ['public', 'internal'], 'review_ref': 'synthetic-review'},
            'evidence': [{'id': 'original', 'path': inputs[0],
                'sha256': C.digest((self.root / inputs[0]).read_bytes()), 'classification': 'internal',
                'purpose': 'Independent original observation', 'ranges': [[1, 1]], 'review_original': True}]}

    def build(self, name='tasks/context-v1'):
        return C.build(self.root, self.request, name)

    def test_bounded_receipt_reports_only_paths_hashes_and_coverage(self):
        report = self.build()
        self.assertEqual(report['status'], 'consistent')
        self.assertEqual(C.check(self.root, 'tasks/context-v1')['status'], 'consistent')
        task = (self.root / report['task_path']).read_text()
        self.assertIn('Original observation A', task)
        self.assertNotIn('Unrelated observation C', task)
        self.assertNotIn('"id": "elsewhere"', task)
        self.assertIn('"id": "shared-stop"', task)
        self.assertIn('whole-source hashes', task)
        self.assertNotIn('Original observation A', json.dumps(report))
        receipt = json.loads((self.root / report['receipt_path']).read_text())
        self.assertFalse(receipt['source_coverage'][0]['complete_file_in_packet'])
        self.assertFalse(receipt['source_coverage'][0]['semantic_extraction_verified'])
        self.assertIn('instruction_versions', receipt)
        self.assertEqual((self.root / report['task_path']).stat().st_mode & 0o777, 0o600)

    def test_deterministic_repeat_and_immutable_output(self):
        first = self.build()
        before = (self.root / first['task_path']).stat().st_mtime_ns
        self.assertEqual(first, self.build())
        self.assertEqual(before, (self.root / first['task_path']).stat().st_mtime_ns)
        second = self.build('tasks/context-v2')
        self.assertEqual(first['task_sha256'], second['task_sha256'])
        self.request['summary'] += ' Changed scope.'
        with self.assertRaisesRegex(ValueError, 'immutable_context_exists'):
            self.build()

    def test_summary_and_total_overflow_are_rejected_without_partial_output(self):
        self.request['summary'] = 'x' * 8193
        with self.assertRaisesRegex(ValueError, 'summary_missing_or_over_8192'):
            self.build()
        self.request['summary'] = 'bounded'
        self.request['max_packet_bytes'] = 1024
        with self.assertRaisesRegex(ValueError, 'packet_exceeds_byte_budget'):
            self.build()
        self.assertFalse((self.root / 'tasks/context-v1').exists())
        self.request['max_packet_bytes'] = 65536
        with self.assertRaisesRegex(ValueError, 'larger_budget_reason_required'):
            self.build()
        self.request['budget_reason'] = 'Explicitly preserve two coherent cited evidence blocks.'
        self.assertEqual(self.build()['status'], 'consistent')

    def test_shared_restriction_and_stop_conditions_cannot_be_omitted(self):
        self.request['shared_constraint_ids'] = []
        with self.assertRaisesRegex(ValueError, 'missing_shared_restriction'):
            self.build()
        self.request['shared_constraint_ids'] = ['shared-stop']
        self.request['stop_conditions'] = ['Some unrelated stop']
        with self.assertRaisesRegex(ValueError, 'missing_shared_stop_condition'):
            self.build()

    def test_stale_originals_and_task_or_receipt_tampering_fail(self):
        report = self.build()
        task = self.root / report['task_path']
        original = task.read_bytes()
        task.write_bytes(original + b'Injected instruction')
        self.assertEqual(C.check(self.root, 'tasks/context-v1')['status'], 'inconsistent')
        task.write_bytes(original)
        receipt_path = self.root / report['receipt_path']
        receipt = json.loads(receipt_path.read_text())
        receipt['source_coverage'][0]['complete_file_in_packet'] = True
        receipt_path.write_text(json.dumps(receipt))
        self.assertEqual(C.check(self.root, 'tasks/context-v1')['status'], 'inconsistent')
        fresh = self.build('tasks/context-v2')
        (self.root / self.original).write_text('Changed original\n')
        self.assertEqual(C.check(self.root, fresh['receipt_path'])['status'], 'inconsistent')

    def delta(self, report):
        self.request['mode'] = 'delta'
        self.request['delta'] = {'baseline_receipt': {'path': report['receipt_path'],
              'sha256': C.digest((self.root / report['receipt_path']).read_bytes())},
            'changed_ids': ['work'], 'open_findings': ['Verify observation B'], 'reason': 'Narrow correction'}

    def test_delta_includes_actual_pinned_baseline_and_open_findings(self):
        report = self.build()
        self.delta(report)
        self.request['evidence'][0]['ranges'] = [[2, 2]]
        delta = self.build('tasks/delta')
        task = (self.root / delta['task_path']).read_text()
        self.assertIn('Original observation A', task)
        self.assertIn('Original observation B', task)
        self.assertIn('Verify observation B', task)
        self.assertEqual(C.check(self.root, 'tasks/delta')['status'], 'consistent')
        (self.root / report['task_path']).unlink()
        self.assertEqual(C.check(self.root, 'tasks/delta')['status'], 'inconsistent')
        with self.assertRaisesRegex(ValueError, 'missing_or_oversized_file'):
            self.build('tasks/missing-baseline')

    def test_delta_can_use_historical_baseline_with_new_current_originals(self):
        report = self.build()
        (self.root / self.original).write_text('New current observation\n')
        self.save_packet(filename='tasks/revised-task.json')
        self.delta(report)
        result = self.build('tasks/delta-current')
        self.assertEqual(result['status'], 'consistent')
        self.assertIn('New current observation', (self.root / result['task_path']).read_text())

    def test_repeated_deltas_fold_evidence_without_recursive_packet_growth(self):
        previous = self.build()
        sizes = []
        for index in range(6):
            self.delta(previous)
            self.request['delta']['open_findings'] = ['Open finding ' + str(index)]
            self.request['evidence'][0]['ranges'] = [[2, 2]]
            previous = self.build('tasks/delta-' + str(index))
            sizes.append(previous['task_bytes'])
        task = (self.root / previous['task_path']).read_text()
        self.assertEqual(task.count('# Bounded specialist task'), 1)
        self.assertIn('Original observation A', task)
        self.assertIn('Original observation B', task)
        self.assertIn('Open finding 0', task)
        self.assertIn('Open finding 5', task)
        self.assertLess(sizes[-1] - sizes[0], 2048)
        self.assertEqual(C.check(self.root, previous['receipt_path'])['status'], 'consistent')

    def test_path_escape_symlink_and_missing_baseline_rejected(self):
        for output in ('../escaped', '/tmp/escaped', 'tasks/../escaped'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                C.build(self.root, self.request, output)
        (self.root / 'tasks/linked').symlink_to(self.root / 'inputs', target_is_directory=True)
        with self.assertRaises(ValueError):
            self.build('tasks/linked/context')
        self.request['evidence'][0]['path'] = '../outside.txt'
        with self.assertRaisesRegex(ValueError, 'invalid_relative_path'):
            self.build()

    def test_independent_review_requires_original_not_only_worker_summary(self):
        (self.root / 'deliverables/worker-summary.txt').write_text('A worker summary\n')
        self.save_packet(role='qa-analyst', filename='tasks/review.json', input_path='deliverables/worker-summary.txt')
        with self.assertRaisesRegex(ValueError, 'independent_review_requires_original_evidence'):
            self.build()
        self.save_packet(role='qa-analyst', filename='tasks/review-original.json')
        self.assertEqual(self.build()['status'], 'consistent')

    def test_disclosure_secret_detection_ranges_and_binding(self):
        self.request['classification'] = 'public'
        with self.assertRaisesRegex(ValueError, 'evidence_disclosure_denied'):
            self.build()
        self.request['classification'] = 'internal'
        self.request['evidence'][0]['ranges'] = [[1, 99]]
        with self.assertRaisesRegex(ValueError, 'range_exceeds'):
            self.build()
        (self.root / self.original).write_text('api_key=' + 'SYNTHETIC' * 8 + '\n')
        self.save_packet(filename='tasks/secret.json')
        with self.assertRaisesRegex(ValueError, '^context.possible_secret_review_required$'):
            self.build()
        self.assertFalse((self.root / 'tasks/context-v1').exists())

    def test_opt_in_role_slice_keeps_shared_constraints_and_legacy_compatible(self):
        legacy = P.intent_helper().packet_context(self.root, 'app-designer')
        self.assertEqual(len(legacy['requirements']), 3)
        self.assertEqual(P.packet_check(self.root, self.packet_path)['status'], 'consistent')
        bounded = P.intent_helper().packet_context(self.root, 'data-analyst', bounded=True, scope_ids=['work'])
        self.assertEqual({r['id'] for r in bounded['requirements']}, {'work', 'shared-stop'})
        self.assertEqual(bounded['paths'], [])
        self.assertEqual(bounded['coverage']['total_requirement_count'], 3)
        product = P.routing_helper('product_intent').packet_context(self.root, 'data-analyst', bounded=True)
        self.assertNotIn('Read the complete current intent', product['note'])
        project = P.load_project(self.root)[1]
        project['context_policy'] = 'bounded-context-v1'
        P.write_json(self.root / 'project.json', project, replace=True)
        self.assertEqual(P.intent_helper().packet_context(self.root, 'data-analyst')['shared_constraint_ids'], ['shared-stop'])


if __name__ == '__main__':
    unittest.main()
