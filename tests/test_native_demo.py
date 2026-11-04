"""Original synthetic demo contract checks; no execution or real approval."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TESTS = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('demo_authoring', TESTS.parent / 'skills/omni-app-engineer/scripts/native_authoring.py')
G = load('demo_gate_fixture', TESTS / 'stage_gate_fixture.py')
P = A.project_helper()


class NativeDemo(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic bounded demonstration', 'net-new', 'app', 'none',
               selection_policy='conversation-evidence-v1')
        self.gates = G.Lifecycle(self.root, P)
        self.gates.through('options')
        binding = P.stage_status(self.root)['choice_bindings']['option-1']
        response = {'schema_version': 1, 'kind': 'oaa_conversation_choice',
            'source': {'host': 'local-host', 'conversation_ref': 'synthetic-conversation',
                'question_ref': 'synthetic-question', 'response_ref': None, 'role': 'user'},
            'response_text': 'I choose option-1', 'selected_option_id': 'option-1',
            'expected_binding': binding, 'recorded_by': 'fixture-agent',
            'assurance': 'agent_attested_not_independently_authenticated'}
        evidence = self.gates.evidence('conversation-response', json.dumps(response))
        P.stage_record(self.root, {'stage': 'choice', 'basis': 'conversation_evidence',
            'option_id': 'option-1', 'expected_binding': binding, 'evidence': {'user_response': evidence}})
        self.html_path, self.spec_path, self.demo_path = 'deliverables/app.html', 'contracts/create-spec.json', 'contracts/demo-scope.json'
        (self.root / self.html_path).write_text('<!doctype html><p>Synthetic demonstration</p>')
        selected = P.read_json(self.root / 'contracts/design-intent.json')[0]
        selected['selections'][0]['candidate_path'] = self.html_path
        selected['selections'][0]['target'] = {'surface': 'app', 'state': 'local', 'document_id': None, 'draft_id': None}
        P.write_json(self.root / 'contracts/design-intent.json', selected, replace=True)
        self.gates.stage('design')
        self.spec = {'base_url': 'https://target.example', 'slug': 'synthetic-demo', 'model_id': 'model-1',
            'name': 'Synthetic demonstration', 'description': 'Original fixture only.',
            'queryPresentations': {'data': {'1': {'name': 'Observations', 'topicName': 'observations',
                'type': 'query', 'isSql': False, 'query': {'fields': ['observations.id'],
                'table': 'observations', 'limit': 10, 'userEditedSQL': ''}}}, 'order': ['1']}}
        self.save(self.spec_path, self.spec)
        proof = self.gates.evidence('minimum-proof', 'Synthetic source review only; not actual access or permission.')
        self.demo = {'schema_version': 1, 'kind': 'native_demo_scope',
            'html': self.pin(self.html_path), 'create_spec': self.pin(self.spec_path),
            'destination': {'origin': self.spec['base_url'], 'model_id': self.spec['model_id'],
                'document_id': self.spec['slug'], 'operation': 'initial_create',
                'principal': {'key_scope': 'user', 'user_id': 'test-user', 'membership_id': 'test-member'},
                'audience': {'kind': 'named_test_principal', 'membership_id': 'test-member'}},
            'minimums': {key: {'status': 'resolved', 'scope': 'Synthetic supplied minimum for checker testing.',
                              'evidence': [self.pin(proof)]} for key in ('security', 'numerical', 'permission', 'design')},
            'pending_observations': [
                {'scope': 'ui_ux', 'basis': 'rendered', 'reason': 'Actual render unavailable in source fixture.',
                 'required_observation': 'Inspect exact candidate in target runtime.'},
                {'scope': 'qa', 'basis': 'native', 'reason': 'Actual native interaction is unobserved.',
                 'required_observation': 'Exercise the selected candidate controls.'}]}

    def save(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def pin(self, path):
        return {'path': path, 'sha256': P.digest((self.root / path).read_bytes())}

    def stage(self, omit=None, override=None, artifacts=None, guarded=False):
        self.save(self.demo_path, self.demo)
        if guarded:
            P.routing_helper('delivery_workflow').freeze(self.root, {'id': 'demo-one',
                'builders': ['fixture-engineer'], 'artifacts': [self.html_path, self.spec_path, self.demo_path],
                'supporting_artifacts': [self.spec_path, self.demo_path], 'context': ['contracts/execution.json']})
        else:
            P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'demo-one',
                'builders': ['fixture-engineer'], 'artifacts': artifacts or [self.html_path, self.spec_path, self.demo_path]})
        current = P.stage_status(self.root)['candidate']
        for scope in ('security', 'ui_ux', 'product_owner', 'qa'):
            if scope == omit:
                continue
            outcome, basis = ('unobserved', 'rendered' if scope == 'ui_ux' else 'native') if scope in {'ui_ux', 'qa'} else ('resolved', 'source')
            if override and scope in override:
                outcome, basis = override[scope]
            P.stage_record(self.root, {'stage': 'review', 'scope': scope, 'reviewer': scope + '-reviewer',
                'iteration_sha256': current['event_sha256'], 'candidate_sha256': current['candidate_sha256'],
                'outcome': outcome, 'basis': basis, 'evidence': {'review': self.gates.evidence('review-' + scope)}})

    def prepare(self):
        return A.prepare_demo(project=self.root, artifact=self.html_path,
                              spec_artifact=self.spec_path, demo_artifact=self.demo_path)

    def captures(self, prepared):
        body, origin = prepared['request']['body'], prepared['base_url']
        route = '/api/v2/documents/' + body['identifier']
        def captured(method, path, status, value):
            return {'base_url': origin, 'method': method, 'path': path, 'status': status, 'body': copy.deepcopy(value)}
        return [captured('POST', '/api/v2/documents', 201, {k: body[k] for k in ('identifier', 'name', 'description')}),
                captured('GET', route, 200, {'app': {'url': route + '/app'}, 'description': body['description'],
                    'name': body['name'], 'modelId': body['modelId'], 'workbookModelId': 'workbook-1',
                    'queryPresentations': body['queryPresentations']}),
                captured('GET', route + '/app', 200, body['app']),
                captured('GET', '/api/v1/whoami?modelId=' + body['modelId'], 200,
                         {'keyScope': 'user', 'user': {'id': 'test-user', 'membershipId': 'test-member'}})]

    def verify(self, prepared, captures):
        return A.verify_demo(prepared, *captures, project=self.root, artifact=self.html_path,
                             spec_artifact=self.spec_path, demo_artifact=self.demo_path)

    def test_observation_only_demo_is_prepared_without_authority_or_release_claim(self):
        self.stage()
        prepared = self.prepare()
        self.assertEqual(prepared['kind'], 'native_demo_create_request')
        self.assertEqual(len(prepared['consultations']), 4)
        self.assertEqual(len(prepared['pending_observations']), 2)
        self.assertTrue(prepared['publishes_immediately'])
        for key in ('execution_authorized', 'publication_authorized', 'release_validated', 'native_verified',
                    'audience_verified', 'claims_authenticated'):
            self.assertIs(prepared[key], False)
        with self.assertRaises(ValueError):
            A.prepare_create(project=self.root, artifact=self.html_path, spec_artifact=self.spec_path)
        verified = self.verify(prepared, self.captures(prepared))
        self.assertEqual(verified['status'], 'exact_demo_readback')
        self.assertFalse(verified['release_validated']); self.assertFalse(verified['audience_verified'])

    def test_all_consultations_are_mandatory(self):
        self.stage(omit='qa')
        with self.assertRaisesRegex(ValueError, 'All four'):
            self.prepare()

    def test_missing_stage_or_unfrozen_supporting_scope_is_rejected(self):
        self.stage(artifacts=[self.html_path, self.spec_path])
        with self.assertRaisesRegex(ValueError, 'Freeze exact'):
            self.prepare()

    def test_known_review_defects_are_not_observation_gaps(self):
        self.stage(override={'qa': ('changes_requested', 'source')})
        with self.assertRaisesRegex(ValueError, 'Known review defects'):
            self.prepare()

    def test_unresolved_security_consultation_rejects_demo(self):
        self.stage(override={'security': ('unobserved', 'native')})
        with self.assertRaisesRegex(ValueError, 'Security and product-owner'):
            self.prepare()

    def test_source_review_gap_cannot_be_called_unobserved_runtime(self):
        self.demo['pending_observations'][1]['basis'] = 'source'
        self.stage(override={'qa': ('unobserved', 'source')})
        with self.assertRaisesRegex(ValueError, 'observation gaps'):
            self.prepare()

    def test_no_minimum_can_remain_pending(self):
        self.demo['minimums']['permission']['status'] = 'pending'
        self.stage()
        with self.assertRaisesRegex(ValueError, 'minimum blocks'):
            self.prepare()

    def test_changed_minimum_evidence_is_rejected(self):
        self.stage()
        self.prepare()
        proof = self.demo['minimums']['numerical']['evidence'][0]['path']
        (self.root / proof).write_text('Changed minimum observation')
        with self.assertRaisesRegex(ValueError, 'Demo evidence changed'):
            self.prepare()

    def test_named_audience_cannot_expand_or_change_principal(self):
        self.demo['destination']['audience']['membership_id'] = 'another-member'
        self.stage()
        with self.assertRaisesRegex(ValueError, 'audience'):
            self.prepare()

    def test_destination_cannot_contradict_create_specification(self):
        self.demo['destination']['model_id'] = 'other-model'
        self.stage()
        with self.assertRaisesRegex(ValueError, 'destination contradicts'):
            self.prepare()

    def test_query_changes_in_readback_are_not_normalized(self):
        self.stage()
        prepared = self.prepare()
        captures = self.captures(prepared)
        captures[1]['body']['queryPresentations']['data']['1']['query']['limit'] = 1
        self.assertIn('query_presentations_mismatch', self.verify(prepared, captures)['findings'])

    def test_principal_origin_and_prepared_bytes_are_exact(self):
        self.stage()
        prepared = self.prepare()
        captures = self.captures(prepared)
        captures[3]['body']['user']['membershipId'] = 'other-member'
        with self.assertRaisesRegex(ValueError, 'principal readback'):
            self.verify(prepared, captures)
        captures = self.captures(prepared)
        captures[3]['base_url'] = 'https://other.example'
        with self.assertRaises(ValueError):
            self.verify(prepared, captures)
        prepared['query_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Prepared create request drift'):
            self.verify(prepared, self.captures(prepared))

    def test_prep_does_not_accept_unselected_identical_artifact(self):
        self.stage()
        (self.root / 'deliverables/other.html').write_bytes((self.root / self.html_path).read_bytes())
        with self.assertRaisesRegex(ValueError, 'selected App artifact'):
            A.prepare_demo(project=self.root, artifact='deliverables/other.html',
                           spec_artifact=self.spec_path, demo_artifact=self.demo_path)

    def test_guarded_freeze_retained_snapshots_support_exact_demo_preparation_and_verification(self):
        self.stage(guarded=True)
        prepared = self.prepare()
        expected = {self.html_path, self.spec_path, self.demo_path}
        self.assertEqual(set(prepared['reviewed_artifacts']), expected)
        for original, retained in prepared['reviewed_artifacts'].items():
            self.assertNotEqual(original, retained['path'])
            self.assertTrue(retained['path'].startswith('evidence/candidate-history/demo-one/'))
            self.assertEqual(retained['sha256'], self.pin(original)['sha256'])
        self.assertEqual(self.verify(prepared, self.captures(prepared))['status'], 'exact_demo_readback')
        # Working files remain bound to retained original identities, not merely
        # any same-hash file included somewhere in the frozen envelope.
        (self.root / self.demo_path).write_text(json.dumps(dict(self.demo, kind='changed')))
        with self.assertRaisesRegex(ValueError, 'original bytes differ'):
            self.prepare()

    def test_cli_demo_prepare_and_verify_keep_authority_false_and_output_private(self):
        self.stage()
        request = self.root / 'evidence/demo-input.json'
        output = self.root / 'evidence/demo-prepared.json'
        request.write_text(json.dumps({'html': self.html_path, 'spec': self.spec_path, 'demo': self.demo_path}))
        command = [sys.executable, '-I', '-S', '-B', str(Path(A.__file__)), 'app-demo-prepare',
                   '--project', str(self.root), '--input', str(request), '--output', str(output)]
        result = subprocess.run(command, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(b'<html', result.stdout)
        prepared = P.read_json(output)[0]
        verify_input = {'html': self.html_path, 'spec': self.spec_path, 'demo': self.demo_path, 'prepared': str(output)}
        for key, capture in zip(('created', 'document', 'app', 'identity'), self.captures(prepared)):
            path = self.root / ('evidence/demo-' + key + '.json')
            path.write_text(json.dumps(capture))
            verify_input[key] = str(path)
        request.write_text(json.dumps(verify_input))
        command[5], command[-1] = 'app-demo-verify', str(self.root / 'evidence/demo-verified.json')
        result = subprocess.run(command, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        verified = P.read_json(Path(command[-1]))[0]
        self.assertEqual(verified['status'], 'exact_demo_readback')
        self.assertFalse(verified['publication_authorized'])
        self.assertFalse(verified['release_validated'])


if __name__ == '__main__':
    unittest.main()
