"""Original synthetic workflow fixtures; no real user, native or craft acceptance."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load('experience_enforcement_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = load('experience_enforcement_fixture', 'tests/stage_gate_fixture.py')
S = P.routing_helper('stage_gates')


class ExperienceEnforcement(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic garden comparison', 'net-new', 'app', 'none')

    def flow(self, end='brief'):
        lifecycle = G.Lifecycle(self.root, P)
        with P.trusted_stage_provider(lifecycle.host):
            lifecycle.through(end)
        return lifecycle

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def options(self):
        return {'stage': 'options', 'evidence': {'comparison': self.evidence('comparison')},
                'options': G.concept_options(self.root, P, ['one', 'two', 'three'])}

    def evidence(self, name):
        path = 'evidence/' + name + '.txt'
        (self.root / path).write_text('Original synthetic evidence; not real access or human approval.')
        return path

    def test_startup_required_before_access_and_supported_authoring(self):
        for action in ('access', 'analysis', 'build', 'candidate', 'release'):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, 'workflow_startup_missing'):
                P.stage_require(self.root, action)
        request = {'stage': 'access', 'source_scope': 'synthetic only', 'user_identity': 'fixture only',
                   'evidence': {'data': self.evidence('data'), 'user_access': self.evidence('access')}}
        with self.assertRaisesRegex(ValueError, 'workflow_startup_missing'):
            P.stage_record(self.root, request)
        self.assertFalse((self.root / S.JOURNAL).exists())

    def test_phase_roles_are_scoped_and_current_role_changes_stale_evidence(self):
        flow = G.Lifecycle(self.root, P)
        execution = P.read_json(self.root / 'contracts/execution.json')[0]
        full = copy.deepcopy(execution)
        execution['responsibilities'] = {'semantics': execution['responsibilities']['semantics']}
        self.write('contracts/execution.json', execution)
        flow.stage('access')
        flow.stage('analysis')
        with self.assertRaisesRegex(ValueError, 'responsibility_missing:storytelling'):
            flow.stage('narrative')
        # Later roles do not alter phase A's semantic projection.
        self.write('contracts/execution.json', full)
        self.assertEqual(P.stage_status(self.root)['completed_stages'], ['access', 'analysis'])
        flow.stage('narrative')
        full['responsibilities']['semantics']['worker'] = 'different-fixture-analyst'
        self.write('contracts/execution.json', full)
        self.assertIn('stale_workflow_context:access', P.stage_status(self.root)['findings'])
        with self.assertRaises(ValueError):
            flow.stage('brief')

    def test_d_requires_quality_choices_with_current_attribution(self):
        flow = G.Lifecycle(self.root, P)
        flow.through('narrative')
        spec = G.discovery_spec(self.root, P)
        spec['product'].pop('quality_bar')
        spec['requirements'] = [r for r in spec['requirements'] if r['category'] != 'experience_quality']
        self.write('contracts/design-intent.json', spec)
        self.write('contracts/no-quality.json', spec)
        with self.assertRaisesRegex(ValueError, 'experience_quality_required'):
            P.stage_record(self.root, {'stage': 'brief', 'discovery_version': 1,
                'evidence': {'brief': self.evidence('brief'), 'intent': 'contracts/no-quality.json'}})

    def test_three_text_files_do_not_satisfy_concept_evidence(self):
        self.flow()
        request = self.options()
        request['options'][0]['evidence'] = self.evidence('text-only-option')
        with self.assertRaises(ValueError):
            P.stage_record(self.root, request)
        self.assertEqual(P.stage_status(self.root)['next_stage'], 'options')

    def test_concepts_require_comparable_scope_distinct_visuals_and_exact_ids(self):
        self.flow()
        request = self.options()
        one, two = [self.root / o['evidence'] for o in request['options'][:2]]
        first, original = json.loads(one.read_text()), json.loads(two.read_text())
        for change, message in [({'analytical_scope': 'Different unsupported population'}, 'comparable_concept_scope'),
                                ({'option_id': 'not-two'}, 'option_id_mismatch'),
                                ({'representative': first['representative']}, 'distinct_representative'),
                                ({'structure': first['structure'], 'primary_interaction': first['primary_interaction']},
                                 'distinct_product_structures')]:
            altered = copy.deepcopy(original); altered.update(change)
            two.write_text(json.dumps(altered))
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                P.stage_record(self.root, request)
        two.write_text(json.dumps(original))
        self.assertEqual(P.stage_record(self.root, request)['next_stage'], 'choice')

    def test_visual_and_quality_source_changes_invalidate_downstream_options(self):
        self.flow('options')
        path = self.root / 'evidence/concept-option-0.svg'
        original = path.read_text()
        path.write_text(original.replace('Garden 1', 'Changed garden'))
        self.assertIn('stale_evidence:options', P.stage_status(self.root)['findings'])
        path.write_text(original)
        spec = P.read_json(self.root / 'contracts/design-intent.json')[0]
        row = next(r for r in spec['requirements'] if r['id'] == 'quality-fixture-composition')
        row['value']['direction'] = 'A different dense multi-panel scope.'
        self.write('contracts/design-intent.json', spec)
        self.assertIn('stage_gate_experience_quality_changed_reopen_brief', P.stage_status(self.root)['findings'])

    def test_selected_handoff_must_match_actual_choice(self):
        flow = self.flow('choice')
        path = G.selected_handoff(self.root, P, {'evidence': 'evidence/concept-option-0.json'})
        with P.trusted_stage_provider(flow.host), self.assertRaisesRegex(ValueError, 'match_selected_concept'):
            P.stage_record(self.root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})
        with P.trusted_stage_provider(flow.host):
            flow.stage('design')
            P.stage_require(self.root, 'build')

    def test_both_surfaces_keep_three_options_with_concrete_per_surface_evidence(self):
        root = Path(self.temp.name).resolve() / 'both'
        P.init(root, 'Synthetic paired surfaces', 'net-new', 'both', 'none')
        flow = G.Lifecycle(root, P)
        with P.trusted_stage_provider(flow.host):
            flow.through('design')
            report = P.stage_require(root, 'build')
        self.assertEqual(len(report['choice_bindings']), 3)
        self.assertEqual(report['next_stage'], 'candidate')

    def test_both_surface_handoff_cannot_leave_another_selected_design_unvalidated(self):
        root = Path(self.temp.name).resolve() / 'both'
        P.init(root, 'Synthetic paired surfaces', 'net-new', 'both', 'none')
        flow = G.Lifecycle(root, P)
        with P.trusted_stage_provider(flow.host):
            flow.through('choice')
            path = G.selected_handoff(root, P, {'evidence': 'evidence/concept-option-1.json'})
            spec = P.intent_helper().load_selected(root)['spec']
            other = 'contracts/other-surface-design.json'
            (root / other).write_bytes((root / path).read_bytes())
            spec['selections'][1]['design_path'] = other
            (root / 'contracts/split-spec.json').write_text(json.dumps(spec))
            P.intent_helper().select(root, root / 'contracts/split-spec.json', 'contracts/split-selected.json')
            with self.assertRaisesRegex(ValueError, 'handoff_must_cover_all_selected_surfaces'):
                P.stage_record(root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})

    def resume(self, ident='source-upgrade'):
        workflow = P.routing_helper('delivery_workflow')
        previous = P.load_project(self.root)[1]['execution_start']
        run = P.read_json(self.root / previous['path'])[0]
        request = {k: run[k] for k in ('source_mode', 'host', 'entrypoint', 'brief', 'loaded_guidance', 'execution')}
        request['id'] = ident
        workflow.start(self.root, request)
        return {'stage': 'workflow_requalification', 'expected_tail_sha256': P.stage_status(self.root)['tail_sha256'],
                'previous_start': previous}

    def test_explicit_requalification_preserves_choice_and_retires_current_f_claims(self):
        flow = self.flow('design')
        (self.root / 'deliverables/candidate.html').write_text('<main>Original synthetic candidate</main>')
        with P.trusted_stage_provider(flow.host):
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'one', 'builders': ['builder'],
                'artifacts': ['deliverables/candidate.html']})
            flow.reviews()
            before = P.stage_status(self.root)
            journal = P.read_json(self.root / S.JOURNAL)[0]['events']
            request = self.resume()
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')
            result = P.stage_record(self.root, request)
            self.assertEqual(result['stage_bindings'], before['stage_bindings'])
            self.assertEqual(result['choice_bindings'], before['choice_bindings'])
            self.assertEqual(result['completed_stages'], list(S.STAGES))
            self.assertIsNone(result['candidate'])
            self.assertEqual(result['reviews'], {})
            self.assertFalse(result['release_ready'])
            self.assertFalse(result['external_mutations_authorized'])
            self.assertEqual(result['review_assurance']['status'], 'not_assessed')
            self.assertEqual(P.read_json(self.root / S.JOURNAL)[0]['events'][:-1], journal)
            P.stage_require(self.root, 'build')
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'two', 'builders': ['builder'],
                'artifacts': ['deliverables/candidate.html']})
            second = self.resume('source-upgrade-two')
            with self.assertRaisesRegex(ValueError, 'iteration_reviews_required'):
                P.stage_record(self.root, second)

    def test_requalification_rejects_changed_tail_owners_choice_and_concept(self):
        flow = self.flow('design')
        with P.trusted_stage_provider(flow.host):
            request = self.resume()
            with self.assertRaisesRegex(ValueError, 'tail_mismatch'):
                P.stage_record(self.root, dict(request, expected_tail_sha256='0' * 64))
            with self.assertRaisesRegex(ValueError, 'invalid_requalification_fields'):
                P.stage_record(self.root, dict(request, phase_contexts={'approved': True}))
            execution = P.read_json(self.root / 'contracts/execution.json')[0]
            original = copy.deepcopy(execution)
            execution['responsibilities']['semantics']['worker'] = 'changed-owner'
            self.write('contracts/execution.json', execution)
            with self.assertRaisesRegex(ValueError, 'responsibilities_changed'):
                P.stage_record(self.root, request)
            self.write('contracts/execution.json', original)
            grants = flow.host.grants.copy()
            flow.host.grants.clear()
            with self.assertRaisesRegex(ValueError, 'trusted_choice_unverified'):
                P.stage_record(self.root, request)
            flow.host.grants = grants
            path = self.root / 'evidence/concept-option-0.svg'
            path.write_text(path.read_text().replace('Garden 1', 'Different scope'))
            with self.assertRaisesRegex(ValueError, 'current_evidence_required'):
                P.stage_record(self.root, request)

    def test_requalification_rejects_missing_current_guidance_and_changed_original_request(self):
        flow = self.flow('design')
        with P.trusted_stage_provider(flow.host):
            previous = P.load_project(self.root)[1]['execution_start']
            run = P.read_json(self.root / previous['path'])[0]
            startup = {k: run[k] for k in ('source_mode', 'host', 'entrypoint', 'brief', 'loaded_guidance', 'execution')}
            startup.update(id='incomplete-upgrade', loaded_guidance=['skills/omni-artifact-accelerator/SKILL.md'])
            P.routing_helper('delivery_workflow').start(self.root, startup)
            request = {'stage': 'workflow_requalification', 'previous_start': previous,
                       'expected_tail_sha256': P.stage_status(self.root)['tail_sha256']}
            with self.assertRaisesRegex(ValueError, 'guidance_not_recorded'):
                P.stage_record(self.root, request)
            (self.root / 'inputs/brief.txt').write_text('Changed synthetic source request')
            previous = P.load_project(self.root)[1]['execution_start']
            startup.update(id='changed-request-upgrade', loaded_guidance=run['loaded_guidance'])
            P.routing_helper('delivery_workflow').start(self.root, startup)
            request = {'stage': 'workflow_requalification', 'previous_start': previous,
                       'expected_tail_sha256': P.stage_status(self.root)['tail_sha256']}
            with self.assertRaisesRegex(ValueError, 'original_request_changed'):
                P.stage_record(self.root, request)

    def test_direct_candidate_cannot_skip_handoff_or_original_request_coverage(self):
        flow = self.flow('choice')
        (self.root / 'deliverables/candidate.html').write_text('<main>Synthetic candidate</main>')
        request = {'stage': 'candidate', 'iteration_id': 'one', 'builders': ['builder'],
                   'artifacts': ['deliverables/candidate.html']}
        with P.trusted_stage_provider(flow.host):
            with self.assertRaises(ValueError):
                P.stage_record(self.root, request)
            flow.stage('design')
            execution = P.read_json(self.root / 'contracts/execution.json')[0]
            execution['request_review']['requirement_ids'] = []
            self.write('contracts/execution.json', execution)
            with self.assertRaisesRegex(ValueError, 'original_request_review_scope_differs'):
                P.stage_record(self.root, request)

    def test_quality_adoption_cannot_be_removed_or_caller_injected(self):
        flow = self.flow('access')
        project = P.load_project(self.root)[1]
        project.pop('workflow_quality_policy')
        self.write('project.json', project)
        self.assertEqual(P.stage_status(self.root)['status'], 'invalid')
        project['workflow_quality_policy'] = S.QUALITY_POLICY
        self.write('project.json', project)
        request = {'stage': 'analysis', 'analyst': 'fixture', 'bi_engineer': 'fixture',
                   'evidence': {k: self.evidence(k) for k in S.EVIDENCE['analysis']},
                   'workflow_context': {'approved': True}, 'workflow_quality_policy': S.QUALITY_POLICY}
        with self.assertRaisesRegex(ValueError, 'invalid_analysis_fields'):
            P.stage_record(self.root, request)

    def test_source_only_reviews_keep_compatibility_and_narrow_claims(self):
        flow = self.flow('design')
        (self.root / 'deliverables/candidate.html').write_text('<main>Original synthetic candidate</main>')
        with P.trusted_stage_provider(flow.host):
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'one', 'builders': ['builder'],
                'artifacts': ['deliverables/candidate.html']})
            flow.reviews()
            report = P.stage_require(self.root, 'release')
        self.assertEqual(report['status'], 'ready_for_release')
        self.assertTrue(report['release_ready'])
        self.assertEqual(report['review_assurance']['status'], 'source_only')
        self.assertEqual(report['review_assurance']['resolved_scopes_by_basis']['source'], sorted(S.REVIEW_SCOPES))
        self.assertFalse(report['review_assurance']['native_acceptance'])
        self.assertFalse(report['review_assurance']['human_acceptance'])
        self.assertFalse(report['external_mutations_authorized'])

    def test_resumed_run_reconciles_current_stages_without_rewriting_prior_iteration(self):
        flow = self.flow('design')
        artifact = self.root / 'deliverables/candidate.html'
        artifact.write_text('<main>Original synthetic candidate</main>')
        with P.trusted_stage_provider(flow.host):
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'one', 'builders': ['builder'],
                'artifacts': ['deliverables/candidate.html']})
            flow.reviews()
            journal_before = P.read_json(self.root / S.JOURNAL)[0]['events']
            run = P.read_json(self.root / P.load_project(self.root)[1]['execution_start']['path'])[0]
            request = {k: run[k] for k in ('source_mode', 'host', 'entrypoint', 'brief', 'loaded_guidance', 'execution')}
            request['id'] = 'resumed-synthetic-run'
            P.routing_helper('delivery_workflow').start(self.root, request)
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'release')
            flow.through('design')
            P.stage_require(self.root, 'build')
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'two', 'builders': ['builder'],
                'artifacts': ['deliverables/candidate.html']})
        journal_after = P.read_json(self.root / S.JOURNAL)[0]['events']
        self.assertEqual(journal_after[:len(journal_before)], journal_before)


if __name__ == '__main__':
    unittest.main()
