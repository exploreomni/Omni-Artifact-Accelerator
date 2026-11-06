"""Original neutral policy regressions. No aesthetic or live-runtime claims."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


F = load('release_continuity_fixture', 'tests/test_experience_continuity.py')
C = load('release_chat_fixture', 'tests/test_conversation_choice.py')
A = load('release_authoring', 'skills/omni-app-engineer/scripts/native_authoring.py')
P = F.P


class ReleaseExperience(unittest.TestCase):
    def setUp(self):
        self.f = F.ExperienceContinuity()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root

    def adopt(self):
        metadata = P.load_project(self.root)[1]
        metadata['app_release_policy'] = 'candidate-release-v1'
        P.write_json(self.root / 'project.json', metadata, replace=True)

    def options(self, single=False):
        request = self.f.options()
        for option in request['options']:
            path = self.root / option['evidence']
            concept = json.loads(path.read_text())
            labels = concept['representative']['labels']
            concept['action_sequence'] = {'kind': 'single_view' if single else 'transition',
                'first_view': labels[0], 'action': concept['primary_interaction'],
                'result_view': labels[0] if single else labels[1],
                'useful_result': 'Understand scoped observations and missing evidence.'}
            if single:
                concept['action_sequence']['single_view_rationale'] = 'Deliberate monitoring of a fixed comparison.'
            self.f.save(option['evidence'], concept)
        # Review points to exact revised concepts.
        review_path = request['evidence']['comparison']
        review = json.loads((self.root / review_path).read_text())
        for row, option in zip(review['options'], request['options']):
            row['concept'] = self.f.pin(option['evidence'])
        self.f.save(review_path, review)
        return request

    def test_new_apps_adopt_policy(self):
        self.assertEqual(P.load_project(self.root)[1]['app_release_policy'], 'candidate-release-v1')

    def test_startup_retains_adoption_and_rejects_policy_removal(self):
        self.f.prepare()
        prior = json.loads((self.root / 'evidence/run-synthetic-fixture.json').read_text())
        request = {k: prior[k] for k in ('source_mode', 'host', 'entrypoint', 'brief', 'loaded_guidance', 'execution')}
        request.update(id='adopted-release', adopt_app_release_policy=True)
        P.routing_helper('delivery_workflow').start(self.root, request)
        metadata = P.load_project(self.root)[1]
        metadata.pop('app_release_policy')
        P.write_json(self.root / 'project.json', metadata, replace=True)
        with self.assertRaisesRegex(ValueError, 'recorded_app_release_policy_removed'):
            P.load_project(self.root)

    def test_adoption_reopens_old_options_without_discarding_analytical_stages(self):
        flow = self.f.prepare()
        with P.trusted_stage_provider(flow.host):
            self.f.advance(flow)
            self.adopt()
            status = P.stage_status(self.root)
            self.assertEqual(status['completed_stages'], ['access', 'analysis', 'narrative', 'brief'])
            self.assertEqual(status['next_stage'], 'options')
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')

    def test_legacy_adoption_requires_and_persists_quality_setup(self):
        self.f.prepare()
        prior = json.loads((self.root / 'evidence/run-synthetic-fixture.json').read_text())
        request = {k: prior[k] for k in ('source_mode', 'host', 'entrypoint', 'brief', 'loaded_guidance', 'execution')}
        request.update(id='legacy-adoption', adopt_app_release_policy=True)
        metadata = P.load_project(self.root)[1]
        for key in ('workflow_quality_policy', 'execution_start', 'execution_guidance', 'app_release_policy'):
            metadata.pop(key, None)
        P.write_json(self.root / 'project.json', metadata, replace=True)
        original = (self.root / 'project.json').read_bytes()
        workflow = P.routing_helper('delivery_workflow')
        with self.assertRaisesRegex(ValueError, 'requires current quality policy'):
            workflow.start(self.root, request)
        self.assertEqual(original, (self.root / 'project.json').read_bytes())
        self.assertFalse((self.root / 'evidence/run-legacy-adoption.json').exists())
        request['adopt_quality_policy'] = True
        self.assertEqual(workflow.start(self.root, request)['status'], 'recorded')
        current = P.load_project(self.root)[1]
        self.assertEqual(current['workflow_quality_policy'], workflow.QUALITY_POLICY)
        self.assertEqual(current['app_release_policy'], 'candidate-release-v1')
        run, pointer = workflow.active_run(self.root, current)
        self.assertEqual(run['app_release_policy'], current['app_release_policy'])
        self.assertEqual(pointer['path'], 'evidence/run-legacy-adoption.json')

    def test_recorded_policy_cannot_be_removed_after_a_stage(self):
        flow = self.f.prepare()
        self.adopt()
        flow.stage('access')
        metadata = P.load_project(self.root)[1]
        metadata.pop('app_release_policy')
        P.write_json(self.root / 'project.json', metadata, replace=True)
        self.assertEqual(P.stage_status(self.root)['status'], 'invalid')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')

    def test_first_view_without_action_result_cannot_advance_new_options(self):
        flow = self.f.prepare()
        self.adopt()
        flow.through('brief')
        with self.assertRaisesRegex(ValueError, 'first_view_and_result'):
            P.stage_record(self.root, self.f.options())
        result = P.stage_record(self.root, self.options())
        self.assertEqual(result['next_stage'], 'choice')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')

    def test_deliberate_single_view_can_use_same_evidence_without_forced_navigation(self):
        flow = self.f.prepare()
        self.adopt()
        flow.through('brief')
        self.assertEqual(P.stage_record(self.root, self.options(single=True))['next_stage'], 'choice')

    def test_screenshots_cannot_claim_exercised_journey(self):
        flow = self.f.prepare()
        with P.trusted_stage_provider(flow.host):
            self.f.advance(flow)
        self.adopt()
        candidate = {'candidate_sha256': 'a' * 64, 'builders': ['engineer']}
        value = self.f.fit(candidate, basis='rendered')
        self.f.save('evidence/observation.json', {'fixture': 'Synthetic wide/narrow observations; no real browser'})
        value['observations'] = [self.f.pin('evidence/observation.json')]
        value['rendered_quality'] = 'recorded_observation'
        for name in ('requirements', 'destinations', 'journeys'):
            for row in value[name]:
                row['evidence_paths'] = ['evidence/observation.json']
        request = {'scope': 'product_owner', 'reviewer': value['reviewer'], 'basis': 'rendered', 'outcome': 'resolved'}
        path = self.f.save('evidence/render-review.json', value)
        with self.assertRaisesRegex(ValueError, 'screenshot_does_not_establish_interaction'):
            F.R.fit(self.root, path, self.f.current_spec(), candidate, request, P)
        value['journey_observations'] = [{'journey_id': 'inspect-record', 'method': 'interaction_exercised',
            'context': 'Synthetic wide and narrow fixture', 'steps': 'Inspect then return with selected identity retained.',
            'evidence_paths': ['evidence/observation.json']}]
        self.f.save(path, value)
        self.assertTrue(F.R.fit(self.root, path, self.f.current_spec(), candidate, request, P))

    def test_current_policy_reaches_guarded_create_with_reviewed_consumers(self):
        flow = self.f.prepare()
        self.adopt()
        with P.trusted_stage_provider(flow.host), patch.object(A, 'project_helper', return_value=P):
            flow.through('brief')
            P.stage_record(self.root, self.options())
            binding = P.stage_status(self.root)['choice_bindings']['two']
            flow.host.grants[(P.canonical(binding), 'synthetic-choice')] = 'fixture-user'
            P.stage_record(self.root, {'stage': 'choice', 'option_id': 'two', 'receipt_ref': 'synthetic-choice'})
            path = self.f.handoff()
            P.stage_record(self.root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})
            P.stage_require(self.root, 'build')
            html = '<main id="total" data-oaa-consumer="total-panel"></main><script>bind("total-panel","1");</script>'
            (self.root / 'deliverables/app.html').write_text(html)
            spec = self.f.current_spec()
            spec['selections'][0]['candidate_path'] = 'deliverables/app.html'
            spec['selections'][0]['target'] = {'surface': 'app', 'state': 'local'}
            self.f.save('contracts/candidate-selected-spec.json', spec)
            P.intent_helper().select(self.root, self.root / 'contracts/candidate-selected-spec.json',
                                     'contracts/candidate-selected-intent.json')
            F.G.refresh_request_review(self.root, P)
            P.stage_record(self.root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})
            presentations = {'order': ['1'], 'data': {'1': {'name': 'Records', 'topicName': 'records',
                'type': 'query', 'isSql': False, 'query': {'fields': ['records.id'], 'table': 'records', 'limit': 10}}}}
            self.f.save('contracts/create.json', {'base_url': 'https://synthetic.invalid', 'slug': 'record-workspace',
                'model_id': 'model-1', 'name': 'Record workspace', 'description': 'Original fixture',
                'queryPresentations': presentations})
            self.f.save('evidence/independent.json', {'fixture_expectation': 12, 'basis': 'independent calculation'})
            expectation = self.f.pin('evidence/independent.json')
            expectation.pop('bytes')
            self.f.save('contracts/native-data-consumers.json', {'schema_version': 1, 'kind': 'native_data_consumers',
                'document_id': 'record-workspace', 'html_sha256': P.digest(html.encode()),
                'presentations_sha256': P.digest(P.canonical(presentations)),
                'refresh_policy': P.routing_helper('product_intent').refresh_report(self.f.current_spec())['policy'],
                'consumers': [{'id': 'total-panel', 'element_id': 'total', 'mode': 'live',
                    'expectation': expectation, 'expectation_basis': 'independent_calculation',
                    'sources': [{'query_key': '1', 'tile_sha256': P.digest(P.canonical(presentations['data']['1'])),
                        'fields': ['records.id'], 'script_fragment': 'bind("total-panel","1")'}]}]})
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'release', 'builders': ['engineer'],
                'artifacts': ['deliverables/app.html', 'contracts/create.json', 'contracts/native-data-consumers.json']})
            candidate = P.stage_status(self.root)['candidate']
            for scope in flow.S.REVIEW_SCOPES:
                evidence = (self.f.save('evidence/fit-' + scope + '.json', self.f.fit(candidate, scope))
                    if scope in {'product_owner', 'ui_ux'} else flow.evidence(scope))
                P.stage_record(self.root, {'stage': 'review', 'scope': scope, 'reviewer': scope + '-reviewer',
                    'iteration_sha256': candidate['event_sha256'], 'candidate_sha256': candidate['candidate_sha256'],
                    'outcome': 'resolved', 'basis': 'source', 'evidence': {'review': evidence}})
            result = A.prepare_create(project=self.root, artifact='deliverables/app.html', spec_artifact='contracts/create.json')
            self.assertEqual(result['data_consumers']['status'], 'source_bound')
            self.assertFalse(result['publication_authorized'])
            self.assertFalse(result['rendered_quality_verified'])


class HybridChoice(unittest.TestCase):
    def check_hybrid(self, response_path):
        fixture = C.ConversationChoiceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.selected()
        def transform(spec, design):
            design['experience_handoff']['selection_adjustments'] = {
                'response_path': response_path,
                'elements': [{'option_id': 'option-2', 'source_locator': 'Evidence inspection state',
                              'application': 'Retain the selected base and this requested detail flow.',
                              'journey_ids': [design['journeys'][0]['id']]}]}
        path = C.G.selected_handoff(fixture.root, C.P,
            {'evidence': 'evidence/concept-option-1.json'}, transform=transform)
        return C.P.stage_record(fixture.root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})

    def test_hybrid_elements_trace_the_existing_choice_and_canonical_journey(self):
        self.assertEqual(self.check_hybrid('evidence/response.json')['next_stage'], 'candidate')

    def test_hybrid_cannot_replace_user_reply_with_generic_brief(self):
        with self.assertRaisesRegex(ValueError, 'actual_choice_response'):
            self.check_hybrid('inputs/brief.txt')


if __name__ == '__main__':
    unittest.main()
