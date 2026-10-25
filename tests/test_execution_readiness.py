"""Original offline cases for source, phase routing and honest delivery claims."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness_project', ROOT / 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
W = P.routing_helper('delivery_workflow')


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Original synthetic collection', 'net-new', 'app')
        self.write('inputs/request.txt', 'Explain collection changes with deliberate visual hierarchy.')
        self.write('evidence/request-review.txt', 'Synthetic independent scope comparison.')
        roles = {'experience': 'app-designer', 'brand': 'branding', 'semantics': 'data-analyst',
                 'engineering': 'app-engineer', 'verification': 'qa-analyst', 'design_systems': 'design-systems',
                 'storytelling': 'data-storyteller', 'product_intent': 'product-owner', 'creative_review': 'app-designer'}
        self.execution = {'responsibilities': {name: {'role': role, 'worker': 'reviewer' if name in
            {'verification', 'creative_review'} else 'builder', 'mode': 'inline',
            'rationale': 'Original synthetic assignment, not a real dispatch.'} for name, role in roles.items()},
            'request_review': {'reviewer': 'reviewer', 'brief_sha256': P.digest((self.root / 'inputs/request.txt').read_bytes()),
                'requirement_ids': [r['id'] for r in P.intent_helper().check(self.root)['requirements']],
                'evidence_path': 'evidence/request-review.txt'}}
        self.write('contracts/execution.json', self.execution)
        self.request = {'id': 'initial', 'source_mode': 'repository_only', 'entrypoint': 'Original offline fixture',
            'brief': 'inputs/request.txt', 'execution': 'contracts/execution.json',
            'host': {'name': 'synthetic', 'execution_mode': 'inline', 'tools': ['original local helpers'],
                     'constraints': ['No external actions']},
            'loaded_guidance': ['skills/omni-artifact-accelerator/SKILL.md', 'skills/omni-data-analyst/SKILL.md']}

    def write(self, path, value):
        (self.root / path).write_text(value if type(value) is str else json.dumps(value))

    def all_guidance(self):
        return sorted(p for p in W.source_manifest(W.source_root()) if p.endswith('.md'))

    def start(self, all_guidance=False):
        if all_guidance:
            self.request['loaded_guidance'] = self.all_guidance()
        return W.start(self.root, self.request)

    def test_startup_required_before_first_work_and_context_is_automatically_bound(self):
        with self.assertRaisesRegex(ValueError, 'workflow_startup_missing'):
            W.require_phase(self.root, 'access')
        result = self.start()
        check = W.require_phase(self.root, 'access')
        self.assertEqual(check['status'], 'ready')
        self.assertEqual(check['context']['run']['path'], result['path'])
        self.assertIn('contracts/execution.json', check['paths'])
        self.assertFalse(check['publication_authorized'])

    def test_incremental_guidance_does_not_invalidate_completed_earlier_phase(self):
        self.start()
        before = W.require_phase(self.root, 'access')['context']
        self.assertEqual(W.phase_check(self.root, 'analysis')['status'], 'blocked')
        W.record_guidance(self.root, {'id': 'analysis', 'loaded_guidance': ['skills/omni-bi-engineer/SKILL.md']})
        self.assertEqual(W.require_phase(self.root, 'access')['context'], before)
        self.assertEqual(W.require_phase(self.root, 'analysis')['status'], 'ready')
        receipt = P.load_project(self.root)[1]['execution_guidance'][0]['path']
        self.write(receipt, {'tampered': True})
        self.assertEqual(W.phase_check(self.root, 'analysis')['status'], 'blocked')

    def test_required_design_duties_cannot_be_waived_by_generic_rationale(self):
        self.start(all_guidance=True)
        self.assertEqual(W.require_phase(self.root, 'options')['status'], 'ready')
        self.execution['responsibilities']['design_systems'].update(mode='not_required', worker='',
            rationale='No component library change.')
        self.write('contracts/execution.json', self.execution)
        self.assertEqual(W.phase_check(self.root, 'access')['status'], 'ready')
        with self.assertRaisesRegex(ValueError, 'required_responsibility_omitted:design_systems'):
            W.require_phase(self.root, 'options')

    def test_independent_creative_review_cannot_be_builder_or_original_designer(self):
        self.start(all_guidance=True)
        self.execution['responsibilities']['creative_review']['worker'] = 'builder'
        self.write('contracts/execution.json', self.execution)
        self.assertIn('independent_creative_review_not_assigned', W.phase_check(self.root, 'options')['findings'])

    def test_pinned_revision_rejects_stale_or_dirty_checkout_without_writing_receipt(self):
        self.request['source_expectation'] = {'kind': 'pinned_revision', 'revision': 'a' * 40}
        for git in ({'head': 'b' * 40, 'status': ''}, {'head': 'a' * 40, 'status': ' M source.py'}):
            with self.subTest(git=git), mock.patch.object(W, 'git_identity', return_value=git):
                with self.assertRaisesRegex(ValueError, 'does not match clean'):
                    self.start()
                self.assertFalse((self.root / 'evidence/run-initial.json').exists())

    def test_explicit_latest_main_read_is_bounded_and_does_not_fetch_or_activate(self):
        answers = [type('Result', (), {'returncode': 0, 'stdout': 'https://github.com/example/original.git\n'})(),
                   type('Result', (), {'returncode': 0, 'stdout': 'a' * 40 + '\trefs/heads/main\n'})()]
        with mock.patch.object(W.subprocess, 'run', side_effect=answers) as run, \
                mock.patch.object(W, 'git_identity', return_value={'head': 'a' * 40, 'status': ''}):
            result = W.verify_source(self.root, {'id': 'main'})
        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(calls), 2)
        self.assertIn('ls-remote', calls[-1])
        self.assertTrue(all('fetch' not in call and 'checkout' not in call and 'pull' not in call for call in calls))
        self.assertTrue(result['checkout_matches'])
        self.request['source_expectation'] = {'kind': 'latest_main', 'revision': 'a' * 40,
                                              'verification_path': result['path']}
        with mock.patch.object(W, 'git_identity', return_value={'head': 'a' * 40, 'status': ''}):
            self.start()
        self.assertFalse(result['claims_authenticated'])

    def test_current_checkout_never_claims_latest_and_source_drift_blocks_resume(self):
        result = self.start()
        saved = json.loads((self.root / result['path']).read_text())
        self.assertEqual(saved['source_expectation'], {'kind': 'current_checkout'})
        with mock.patch.object(W, 'source_manifest', return_value={'changed.py': 'changed'}):
            self.assertIn('package_changed_since_start', W.phase_check(self.root, 'access')['findings'])

    def test_late_startup_is_not_relabelled_contemporaneous(self):
        # Deliberately malformed prior work represents a hostile/old producer.
        self.write('stage-gates.json', {'events': [{'stage': 'access', 'sha256': 'prior'}]})
        result = self.start()
        self.assertEqual(json.loads((self.root / result['path']).read_text())['startup_timing'], 'late')
        self.assertIn('workflow_startup_recorded_late', W.phase_check(self.root, 'access')['findings'])
        second = dict(self.request, id='second')
        with self.assertRaisesRegex(ValueError, 'late startup cannot be converted'):
            W.start(self.root, second)
        second['adopt_quality_policy'] = True
        with self.assertRaisesRegex(ValueError, 'only to historical'):
            W.start(self.root, second)
        self.assertFalse((self.root / 'evidence/run-second.json').exists())

    def test_read_only_specialist_packets_require_actual_startup_and_current_guidance(self):
        for role in ('bi-engineer', 'qa-analyst', 'backend-handoff', 'artifact-translator'):
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, 'workflow_startup_missing'):
                P.packet_data(self.root, role, ['contracts/queries.json'])
        self.start()
        packet = P.packet_data(self.root, 'bi-engineer', ['contracts/queries.json'])
        self.assertEqual(packet['role'], 'bi-engineer')
        with mock.patch.object(W, 'source_manifest', return_value={'changed.py': 'changed'}):
            # The actual packet helper imports its own fixed first-party module;
            # phase source drift is independently checked through the same guard.
            with self.assertRaisesRegex(ValueError, 'package_changed_since_start'):
                W.require_phase(self.root, 'access')

    def test_missing_new_policy_preserves_historical_readability_only(self):
        project = P.load_project(self.root)[1]; project.pop('workflow_quality_policy')
        P.write_json(self.root / 'project.json', project, replace=True)
        result = W.phase_check(self.root, 'access')
        self.assertEqual(result['status'], 'not_assessed')
        self.assertFalse(result['publication_authorized'])

    def test_canonical_motion_and_3d_choices_require_specialists_without_delivery_annotation(self):
        self.start(all_guidance=True)
        state = {'status': 'consistent', 'requirements': [
            {'id': 'transition', 'disposition': 'selected', 'value': {'quality': 'motion', 'usage': 'included'}},
            {'id': 'comparison', 'disposition': 'selected', 'value': {'treatment': 'interactive_3d'}}]}
        snapshot = W.phase_snapshot(self.root)
        snapshot['state'] = state  # Only the canonical decision projection is under test.
        result = W.phase_check(self.root, 'options', _snapshot=snapshot)
        self.assertIn('specialist_scope_missing:motion-designer', result['findings'])
        self.assertIn('specialist_scope_missing:3d-modeler', result['findings'])
        snapshot['execution']['specialists'] = {
            role: {'role': role, 'worker': role, 'mode': 'inline', 'rationale': 'Synthetic responsibility',
                   'requirement_ids': [ident]}
            for role, ident in [('motion-designer', 'transition'), ('3d-modeler', 'comparison')]}
        self.assertEqual(W.phase_check(self.root, 'options', _snapshot=snapshot)['status'], 'ready')
        snapshot['execution']['specialists'] = {}
        state['requirements'][0]['value']['usage'] = 'omitted'
        state['requirements'][1]['value']['treatment'] = 'dimensional_styling'
        self.assertEqual(W.phase_check(self.root, 'options', _snapshot=snapshot)['status'], 'ready')

    def test_requalification_retains_original_request_and_phase_owners_only(self):
        self.start(all_guidance=True)
        old = W.require_phase(self.root, 'options')['context']
        with self.assertRaisesRegex(ValueError, 'new_startup'):
            W.requalify_context(self.root, old, 'options')
        self.request['id'] = 'upgrade'
        self.start(all_guidance=True)
        now = W.requalify_context(self.root, old, 'options')
        self.assertNotEqual(now['run'], old['run'])
        self.assertEqual(now['responsibilities'], old['responsibilities'])
        with self.assertRaisesRegex(ValueError, 'only_to_A_E'):
            W.requalify_context(self.root, old, 'candidate')
        self.execution['responsibilities']['experience']['worker'] = 'changed-designer'
        self.write('contracts/execution.json', self.execution)
        with self.assertRaisesRegex(ValueError, 'responsibilities_changed'):
            W.requalify_context(self.root, old, 'options')
        self.write('inputs/request.txt', 'A different request')
        with self.assertRaisesRegex(ValueError, 'original_request_changed'):
            W.requalify_context(self.root, old, 'options')

    def test_readback_and_source_pass_cannot_close_rendered_or_human_findings(self):
        lanes = {lane: 'not_run' for lane in W.LANES}
        lanes.update(source='reported_pass', publication='reported_pass')
        claims = W.assessment_claims(['lane_rendered_not_run', 'carried_craft_finding'], [], lanes,
                                    {'status': 'not_assessed'}, {'release_ready': True})
        self.assertTrue(claims['source_reviewed'])
        self.assertTrue(claims['published_readback_verified'])
        self.assertTrue(claims['preview_structurally_ready'])
        self.assertFalse(claims['rendered_verified'])
        self.assertFalse(claims['delivery_evidence_complete'])
        self.assertFalse(claims['user_acceptance_recorded'])
        self.assertFalse(claims['publication_authorized'])
        self.assertIn('carried_craft_finding', claims['remaining_findings'])

    def test_wrong_or_changed_candidate_suppresses_all_current_verification_claims(self):
        for finding in ('evidence_candidate_differs', 'candidate_selection_superseded',
                        'candidate_artifacts_changed', 'candidate_context_changed',
                        'delivery_artifacts_differ_from_selected_candidates'):
            with self.subTest(finding=finding):
                claims = W.assessment_claims([finding], [], {lane: 'reported_pass' for lane in W.LANES},
                    {'status': 'recorded_complete'}, {'release_ready': True})
                for key in ('source_reviewed', 'rendered_verified', 'native_verified', 'effective_access_verified',
                            'published_readback_verified', 'user_acceptance_recorded', 'preview_structurally_ready',
                            'current_candidate_evidence_bound', 'delivery_evidence_complete'):
                    self.assertFalse(claims[key], key)


if __name__ == '__main__':
    unittest.main()
