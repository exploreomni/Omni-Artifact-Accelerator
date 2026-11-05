"""Serialization and local integration; no host cache or execution qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location('layout_context', Path(__file__).resolve().parents[1] /
    'skills/omni-artifact-accelerator/scripts/context_packets.py')
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


class ContextLayoutTests(unittest.TestCase):
    def test_absent_layout_preserves_exact_legacy_bytes(self):
        data = {'z': 'Dynamic\n', 'a': {'b': 2, 'a': 1}, 'external_mutations_authorized': False}
        expected = C.INSTRUCTIONS.encode() + (
            b'{\n  "a": {\n    "a": 1,\n    "b": 2\n  },\n'
            b'  "external_mutations_authorized": false,\n  "z": "Dynamic\\n"\n}\n')
        actual, metadata = C.serialize_task(data)
        self.assertEqual(actual, expected)
        self.assertIsNone(metadata)

    def data(self):
        return {'task_id': 'task-a', 'role': 'qa-analyst', 'summary': 'Review this candidate.',
                'assignment': {'objective': 'Check original evidence', 'outputs': ['deliverables/review.json']},
                'external_mutations_authorized': False, 'coverage_owner': 'orchestrator',
                'classification': 'confidential', 'disclosure': {'allowed_classifications': ['confidential'], 'review_ref': 'review'},
                'constraints': ['Do not broaden scope'], 'stop_conditions': ['Stop at missing evidence'],
                'shared_constraint_ids': ['access'], 'requirements': [{'id': 'access', 'required': True}],
                'product_constraints': {'quality_bar': {'ambition': 'Preserve all selected experience requirements'}},
                'selected_intent': {'path': 'contracts/intent.json', 'sha256': 'a' * 64},
                'evidence': [{'path': 'inputs/original.txt', 'source_sha256': 'b' * 64,
                              'lines': [1, 2], 'text': 'Exact original\nSecond line\n'}],
                'delta': {'changed_ids': ['metric'], 'open_findings': ['Check control propagation']},
                'baseline': {'data': {'requirements': [], 'evidence': []}}}

    def test_opt_in_preserves_all_fields_evidence_constraints_and_trust_text(self):
        data = self.data()
        legacy, _ = C.serialize_task(data)
        stable, meta = C.serialize_task(data, C.STABLE_LAYOUT)
        self.assertNotEqual(stable, legacy)
        self.assertTrue(stable.startswith(C.INSTRUCTIONS.encode()))
        self.assertEqual(json.loads(stable[len(C.INSTRUCTIONS.encode()):]), data)
        self.assertEqual(json.loads(legacy[len(C.INSTRUCTIONS.encode()):]), data)
        self.assertEqual(meta['prefix_sha256'], C.digest(stable[:meta['prefix_bytes']]))
        self.assertFalse(meta['provider_cache_configured'])

    def test_task_changes_keep_stable_prefix_but_constraint_changes_do_not(self):
        data = self.data()
        first, meta = C.serialize_task(data, C.STABLE_LAYOUT)
        changed = copy.deepcopy(data)
        changed.update(task_id='task-b', summary='A different exact correction.')
        changed['assignment']['objective'] = 'Check another candidate'
        changed['evidence'][0]['text'] = 'Changed source evidence\n'
        second, next_meta = C.serialize_task(changed, C.STABLE_LAYOUT)
        self.assertEqual(first[:meta['prefix_bytes']], second[:next_meta['prefix_bytes']])
        changed['constraints'].append('New global restriction')
        _, restricted = C.serialize_task(changed, C.STABLE_LAYOUT)
        self.assertNotEqual(meta['prefix_sha256'], restricted['prefix_sha256'])

    def test_layouts_keep_the_same_baseline_data_projection(self):
        data = self.data()
        one, _ = C.serialize_task(data)
        two, _ = C.serialize_task(data, C.STABLE_LAYOUT)
        offset = len(C.INSTRUCTIONS.encode())
        self.assertEqual(C.baseline_state(json.loads(one[offset:])), C.baseline_state(json.loads(two[offset:])))

    def test_unknown_layout_is_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, 'unsupported_layout'):
            C.serialize_task(self.data(), 'unrecognized-layout')


class ContextLayoutIntegrationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('layout_fixture', Path(__file__).with_name('test_context_packets.py'))
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        self.fixture = fixtures.ContextTests('test_deterministic_repeat_and_immutable_output')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.context = fixtures.C

    def test_opted_build_check_preserves_complete_legacy_task_data(self):
        fixture, context = self.fixture, self.context
        legacy = fixture.build('tasks/legacy')
        fixture.request['layout'] = context.STABLE_LAYOUT
        stable = fixture.build('tasks/stable')
        offset = len(context.INSTRUCTIONS.encode())
        legacy_data = json.loads((fixture.root / legacy['task_path']).read_bytes()[offset:])
        stable_data = json.loads((fixture.root / stable['task_path']).read_bytes()[offset:])
        self.assertEqual(stable_data, legacy_data)
        receipt = json.loads((fixture.root / stable['receipt_path']).read_text())
        self.assertEqual(receipt['layout']['version'], context.STABLE_LAYOUT)
        self.assertEqual(context.check(fixture.root, stable['receipt_path'])['status'], 'consistent')
        self.assertFalse(stable['dispatch_authorized'])

    def test_deltas_read_both_layouts_without_losing_originals_or_findings(self):
        fixture, context = self.fixture, self.context
        previous = fixture.build('tasks/legacy')
        for index, layout in enumerate((context.STABLE_LAYOUT, None)):
            fixture.delta(previous)
            fixture.request['evidence'][0]['ranges'] = [[2, 2]]
            if layout:
                fixture.request['layout'] = layout
            else:
                fixture.request.pop('layout', None)
            previous = fixture.build('tasks/delta-' + str(index))
            task = (fixture.root / previous['task_path']).read_text()
            self.assertIn('Original observation A', task)
            self.assertIn('Original observation B', task)
            self.assertIn('Verify observation B', task)
            self.assertEqual(context.check(fixture.root, previous['receipt_path'])['status'], 'consistent')

    def test_old_implementation_receipt_is_historical_not_current_dispatch(self):
        fixture, context = self.fixture, self.context
        previous = fixture.build('tasks/historical')
        path = fixture.root / previous['receipt_path']
        receipt = json.loads(path.read_text())
        receipt['instruction_versions']['implementation']['context_packets.py'] = '0' * 64
        path.write_text(json.dumps(receipt))
        self.assertEqual(context.check(fixture.root, previous['receipt_path'])['status'], 'inconsistent')
        current = fixture.build('tasks/refreshed')
        self.assertEqual(context.check(fixture.root, current['receipt_path'])['status'], 'consistent')
        fixture.delta(previous)
        fixture.request['layout'] = context.STABLE_LAYOUT
        historical_delta = fixture.build('tasks/historical-delta')
        self.assertEqual(context.check(fixture.root, historical_delta['receipt_path'])['status'], 'consistent')
        self.assertFalse(historical_delta['dispatch_authorized'])

    def test_opted_layout_does_not_relax_byte_limit(self):
        fixture = self.fixture
        fixture.request.update(layout=self.context.STABLE_LAYOUT, max_packet_bytes=1024)
        with self.assertRaisesRegex(ValueError, 'packet_exceeds_byte_budget'):
            fixture.build('tasks/oversized')
        self.assertFalse((fixture.root / 'tasks/oversized').exists())


if __name__ == '__main__':
    unittest.main()
