"""Fixed preparation equivalence, partial recovery and safe structural telemetry."""
import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-accelerator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('preparation_test_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


R = load('execution_preparation')
B = load('execution_bridge')
C = load('execution_contracts')
O = load('execution_observability')
P = R.P


class PreparationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        P.init(self.root, 'Original preparation case', 'migration', 'dashboard', branding='none', context_policy='bounded-context-v1')
        project = P.load_project(self.root)[1]
        # Legacy mechanics fixture; separate strict lifecycle test exercises A–F.
        project.pop('stage_gate_policy')
        project.pop('workflow_quality_policy')
        P.write_json(self.root / 'project.json', project, replace=True)
        (self.root / 'inputs/original.txt').write_text('Orders are counted at order grain.\n')
        self.work = {'role': 'bi-engineer', 'inputs': ['inputs/original.txt'], 'output': 'tasks/work.json',
            'assignment': {'schema_version': 1, 'task_id': 'original-work', 'domain_id': 'orders', 'stage': 'dashboard',
                'role': 'bi-engineer', 'scope_ids': ['orders'], 'objective': 'Bind original order evidence',
                'outputs': ['deliverables/result.json'], 'acceptance': ['Keep original order grain'],
                'dependency_paths': ['inputs/original.txt'], 'unknowns': ['Native behavior unobserved'], 'authoring_mode': 'provisional'}}
        self.context = {'schema_version': 1, 'kind': 'analyst_context_request', 'mode': 'initial',
            'summary': 'Bind only the scoped original metric.', 'decisions': ['Retain grain'],
            'constraints': ['No external work'], 'evidence': [{'id': 'original', 'path': 'inputs/original.txt',
                'sha256': P.digest((self.root / 'inputs/original.txt').read_bytes()), 'classification': 'internal',
                'purpose': 'Independent source requirement', 'ranges': [[1, 1]], 'review_original': True}],
            'classification': 'internal', 'disclosure': {'allowed_classifications': ['internal'], 'review_ref': 'original-fixture'}}
        self.recipe = {'schema_version': 1, 'idempotency_key': 'original-request', 'work': self.work,
            'context': self.context, 'context_output': 'tasks/context', 'action': 'build', 'attempt_id': 'attempt-a'}

    def test_equivalent_to_manual_steps_and_repeat_does_not_duplicate(self):
        efficiency = P.routing_helper('execution_efficiency')
        prepared = efficiency.prepare(self.root, self.work)
        packet = P.read_json(self.root / prepared['packet'])[0]
        context = dict(self.context, packet={'path': prepared['packet'], 'sha256': prepared['packet_sha256']},
                       stop_conditions=packet['stop_conditions'], shared_constraint_ids=[])
        receipt = P.routing_helper('context_packets').build(self.root, context, 'tasks/context')
        expected_bytes = (self.root / receipt['task_path']).read_bytes()
        first = R.prepare(self.root, self.recipe)
        repeated = R.prepare(self.root, self.recipe)
        self.assertEqual(first['status'], 'ready')
        self.assertEqual(repeated['reservation']['action'], 'already_active')
        self.assertEqual(expected_bytes, (self.root / receipt['task_path']).read_bytes())
        self.assertFalse(first['agents_dispatched'])
        self.assertEqual(len(P.read_json(self.root / 'task-operations.json')[0]['attempts']), 1)

    def test_failure_before_reservation_retains_files_and_resumes(self):
        original = R.P.routing_helper
        helper = original('execution_efficiency')
        with patch.object(helper, 'preflight', side_effect=OSError('original synthetic interruption')):
            with patch.object(R.P, 'routing_helper', side_effect=lambda name='task_routing': helper if name == 'execution_efficiency' else original(name)):
                with self.assertRaises(OSError):
                    R.prepare(self.root, self.recipe)
        task = (self.root / 'tasks/context/TASK.md').read_bytes()
        self.assertFalse((self.root / 'task-operations.json').exists())
        result = R.prepare(self.root, self.recipe)
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(result['resumed'])
        self.assertEqual(task, (self.root / 'tasks/context/TASK.md').read_bytes())

    def test_identity_cannot_be_reused_with_different_work_or_source(self):
        R.prepare(self.root, self.recipe)
        changed = copy.deepcopy(self.recipe)
        changed['context']['summary'] = 'A materially different task'
        with self.assertRaisesRegex(ValueError, 'identity or inputs changed'):
            R.prepare(self.root, changed)
        (self.root / 'inputs/original.txt').write_text('Changed grain\n')
        with self.assertRaisesRegex(ValueError, 'identity or inputs changed'):
            R.prepare(self.root, self.recipe)

    def test_changed_input_between_preflight_and_claim_prevents_reservation(self):
        original = R.P.routing_helper
        helper = original('execution_efficiency')
        preflight = helper.preflight
        def change(root, request):
            result = preflight(root, request)
            (root / 'inputs/original.txt').write_text('Changed after validation\n')
            return result
        with patch.object(helper, 'preflight', side_effect=change):
            with patch.object(R.P, 'routing_helper', side_effect=lambda name='task_routing': helper if name == 'execution_efficiency' else original(name)):
                with self.assertRaisesRegex(ValueError, 'changed before reservation'):
                    R.prepare(self.root, self.recipe)
        self.assertFalse((self.root / 'task-operations.json').exists())

    def test_preflight_blockers_do_not_create_a_reservation(self):
        original = R.P.routing_helper
        helper = original('execution_efficiency')
        with patch.object(helper, 'preflight', return_value={'status': 'blocked', 'blockers': [{'code': 'original_fixture_gap'}]}):
            with patch.object(R.P, 'routing_helper', side_effect=lambda name='task_routing': helper if name == 'execution_efficiency' else original(name)):
                result = R.prepare(self.root, self.recipe)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['reservation_created'])
        self.assertFalse((self.root / 'task-operations.json').exists())

    def test_configuration_does_not_turn_declared_settings_into_observations(self):
        value = B.configuration(self.root, None, {'tool_profile': 'execution', 'tool_names': ['execution_status']})
        self.assertEqual(value['recent_observations'], [])
        self.assertIsNone(value['configured_worker'])
        self.assertFalse(value['settings_changed'])
        self.assertFalse(value['host_isolation_verified'])

    def test_contract_diagnostics_exclude_unknown_names_and_values(self):
        with self.assertRaises(ValueError) as caught:
            C.validate('execution_prepare', 'work', {'role': 'bi-engineer'})
        diagnostic = B.safe_error('execution_prepare', {'operation': 'work'}, caught.exception)
        self.assertEqual(diagnostic['code'], 'execution_missing_field')
        for message in ('secret-sentinel', 'execution.contract.string_required|secret-sentinel'):
            self.assertNotIn('secret-sentinel', str(B.safe_error('execution_prepare', {'operation': 'work'}, ValueError(message))))
        # Envelope descriptions preserve the existing review contract shape.
        C.validate('execution_record', 'review', {'attempt_id': 'a', 'action': 'start', 'changes': ['metrics'], 'dependency_state': 'known'})
        C.validate('execution_analysis', 'compare', {'comparison': {'path': 'evidence/comparison.json', 'sha256': 'a' * 64},
            'provenance': {'path': 'evidence/provenance.json', 'sha256': 'b' * 64}, 'output': 'evidence/result.json'})

    def test_local_measurements_keep_payloads_private_and_never_infer_cost(self):
        outcome = O.record(self.root, tool='execution_prepare', operation='recipe',
            arguments={'private': 'source-secret-sentinel'}, result={'private': 'result-secret-sentinel'},
            started_ns=time.monotonic_ns(), outcome='returned', configuration={'profile': 'execution'}, counters={'file_reads': 2, 'verification_bytes': 42})
        self.assertEqual(outcome, 'recorded')
        raw = '\n'.join(p.read_text() for p in (self.root / '.execution-observations').glob('*.json'))
        self.assertNotIn('secret-sentinel', raw)
        report = O.report(self.root)
        self.assertEqual(report['observed_calls'], 1)
        self.assertEqual(report['totals']['file_reads'], 2)
        self.assertEqual(report['totals']['verification_bytes'], 42)
        self.assertIsNone(report['dollars'])
        self.assertIsNone(report['totals']['read_reuses'])
        event = next((self.root / '.execution-observations').glob('*.json'))
        forged = json.loads(event.read_text())
        forged['operation'] = 'secret_sentinel'
        event.write_text(json.dumps(forged))
        inspected = O.report(self.root)
        self.assertEqual(inspected['invalid_observations'], 1)
        self.assertNotIn('secret_sentinel', str(inspected))

    def test_measurement_failure_is_nonfatal_and_limits_are_explicit(self):
        with patch.object(O, 'MAX_EVENTS', 0):
            self.assertEqual(O.record(self.root, tool='execution_status', operation=None, arguments={}, result={},
                started_ns=time.monotonic_ns(), outcome='returned', configuration={}), 'limit_reached')
            self.assertTrue(O.report(self.root)['collection_limit_reached'])

    def test_concurrent_measurements_do_not_exceed_collection_limit(self):
        def record(_):
            return O.record(self.root, tool='execution_status', operation=None, arguments={}, result={},
                started_ns=time.monotonic_ns(), outcome='returned', configuration={})
        with patch.object(O, 'MAX_EVENTS', 1):
            with ThreadPoolExecutor(max_workers=4) as pool:
                outcomes = list(pool.map(record, range(8)))
            self.assertEqual(outcomes.count('recorded'), 1)
            self.assertEqual(len(list((self.root / '.execution-observations').glob('*.json'))), 1)
            self.assertEqual(record(None), 'limit_reached')


if __name__ == '__main__':
    unittest.main()
