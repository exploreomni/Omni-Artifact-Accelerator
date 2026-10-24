"""Original conversation fixtures test workflow integrity, not authentication."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load('conversation_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = load('conversation_fixture', 'tests/stage_gate_fixture.py')


class ConversationChoiceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve() / 'engagement'
        P.init(self.root, 'Original garden study', 'net-new', 'app', 'none')
        self.gates = G.Lifecycle(self.root, P)
        self.gates.through('options')

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def policy(self):
        self.write('evidence/policy.json', {'source': 'Synthetic user request for chat workflow evidence'})
        return P.stage_record(self.root, {'stage': 'selection_policy',
            'selection_policy': 'conversation-evidence-v1',
            'expected_tail_sha256': P.stage_status(self.root)['tail_sha256'],
            'evidence': {'policy_decision': 'evidence/policy.json'}})

    def response(self, option='option-1'):
        binding = P.stage_status(self.root)['choice_bindings'][option]
        value = {'schema_version': 1, 'kind': 'oaa_conversation_choice',
            'source': {'host': 'fixture-host', 'conversation_ref': 'fixture-conversation',
                       'question_ref': 'fixture-question', 'response_ref': None, 'role': 'user'},
            'response_text': 'Choose the second garden concept.', 'selected_option_id': option,
            'expected_binding': binding, 'recorded_by': 'fixture-agent',
            'assurance': 'agent_attested_not_independently_authenticated'}
        self.write('evidence/response.json', value)
        request = {'stage': 'choice', 'basis': 'conversation_evidence', 'option_id': option,
                   'expected_binding': binding, 'evidence': {'user_response': 'evidence/response.json'}}
        return value, request

    def selected(self):
        self.policy()
        _, request = self.response()
        return P.stage_record(self.root, request)

    def test_cli_records_actual_workflow_evidence_and_requires_resolved_design(self):
        original = json.loads((self.root / 'stage-gates.json').read_text())['events']
        self.policy()
        _, request = self.response()
        self.write('requests/choice.json', request)
        result = subprocess.run([sys.executable, '-I', '-S', '-B', P.__file__, 'stage-record',
            '--project', str(self.root), '--request', str(self.root / 'requests/choice.json')],
            capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        status = P.stage_status(self.root)
        self.assertEqual(status['next_stage'], 'design')
        self.assertEqual(status['choice_assurance'], 'conversation_evidence')
        for key in ('choice_authenticated', 'claims_authenticated', 'external_mutations_authorized'):
            self.assertFalse(status[key])
        self.assertEqual(json.loads((self.root / 'stage-gates.json').read_text())['events'][:5], original)
        with self.assertRaisesRegex(ValueError, 'predecessor_incomplete'):
            P.stage_require(self.root, 'build')
        self.gates.stage('design')
        P.stage_require(self.root, 'build')

    def test_strict_policy_has_no_automatic_conversation_fallback(self):
        _, request = self.response()
        with self.assertRaisesRegex(ValueError, 'trusted_provider_required'):
            P.stage_record(self.root, request)
        self.assertEqual(P.stage_status(self.root)['selection_policy'], 'host-verified-v1')
        self.assertEqual(P.stage_status(self.root)['next_stage'], 'choice')

    def test_every_binding_field_is_checked_not_restamped(self):
        self.policy()
        value, request = self.response()
        for key in request['expected_binding']:
            bad = copy.deepcopy(request)
            bad['expected_binding'][key] += '-changed'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'choice_binding_mismatch'):
                P.stage_record(self.root, bad)
        value = copy.deepcopy(value)
        value['expected_binding']['option_id'] = 'option-2'
        self.write('evidence/response.json', value)
        with self.assertRaisesRegex(ValueError, 'response_binding_mismatch'):
            P.stage_record(self.root, request)

    def test_no_boolean_role_or_missing_provenance_can_replace_response(self):
        self.policy()
        value, request = self.response()
        variants = []
        for role in ('assistant', 'tool', 'system'):
            bad = copy.deepcopy(value)
            bad['source']['role'] = role
            variants.append(bad)
        for text in ('', '   ', True):
            bad = copy.deepcopy(value)
            bad['response_text'] = text
            variants.append(bad)
        bad = copy.deepcopy(value)
        bad['source']['question_ref'] = ''
        variants.append(bad)
        bad = copy.deepcopy(value)
        bad['assurance'] = 'host_verified'
        variants.append(bad)
        for bad in variants:
            self.write('evidence/response.json', bad)
            with self.assertRaises(ValueError):
                P.stage_record(self.root, request)
        self.write('evidence/response.json', value)
        with self.assertRaises(ValueError):
            P.stage_record(self.root, dict(request, approved=True))

    def test_changed_or_missing_response_blocks_downstream(self):
        self.selected()
        self.gates.stage('design')
        path = self.root / 'evidence/response.json'
        raw = path.read_bytes()
        path.write_text('{}')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')
        path.write_bytes(raw)
        P.stage_require(self.root, 'build')
        path.unlink()
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'design')

    def test_same_options_rerecorded_invalidate_previous_answer(self):
        self.policy()
        _, request = self.response()
        P.stage_record(self.root, request)
        self.gates.stage('design')
        self.gates.stage('options')
        self.assertEqual(P.stage_status(self.root)['next_stage'], 'choice')
        with self.assertRaisesRegex(ValueError, 'choice_binding_mismatch'):
            P.stage_record(self.root, request)

    def test_policy_transition_cannot_hide_prior_choice_or_stale_history(self):
        self.write('evidence/policy.json', {'source': 'Synthetic configuration'})
        request = {'stage': 'selection_policy', 'selection_policy': 'conversation-evidence-v1',
            'expected_tail_sha256': '0' * 64, 'evidence': {'policy_decision': 'evidence/policy.json'}}
        with self.assertRaisesRegex(ValueError, 'tail_mismatch'):
            P.stage_record(self.root, request)
        self.selected()
        with self.assertRaisesRegex(ValueError, 'already_fixed'):
            self.policy()
        self.write('evidence/policy.json', {'source': 'Changed decision'})
        with self.assertRaisesRegex(ValueError, 'stale_selection_policy'):
            P.stage_require(self.root, 'design')

    def test_policy_evidence_changed_during_record_never_commits(self):
        before = (self.root / 'stage-gates.json').read_bytes()
        gates = P.routing_helper('stage_gates')
        original = gates._pin
        changed = False

        def mutate_after_pin(fd, relative, helpers):
            nonlocal changed
            result = original(fd, relative, helpers)
            if relative == 'evidence/policy.json' and not changed:
                changed = True
                self.write(relative, {'source': 'Changed while policy was recording'})
            return result

        with patch.object(gates, '_pin', side_effect=mutate_after_pin):
            with self.assertRaisesRegex(ValueError, 'evidence_changed_during_record'):
                self.policy()
        self.assertEqual((self.root / 'stage-gates.json').read_bytes(), before)

    def test_conversation_candidate_still_requires_four_current_reviews(self):
        self.selected()
        self.gates.stage('design')
        self.write('deliverables/original.json', {'synthetic': 'candidate'})
        result = P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'one',
            'builders': ['builder'], 'artifacts': ['deliverables/original.json']})
        with self.assertRaisesRegex(ValueError, 'iteration_reviews_required'):
            P.stage_require(self.root, 'build')
        self.gates.reviews('unobserved')
        with self.assertRaisesRegex(ValueError, 'resolved_reviews_required'):
            P.stage_require(self.root, 'release')
        self.gates.reviews('resolved')
        ready = P.stage_require(self.root, 'release')
        self.assertEqual(ready['candidate_sha256'], result['candidate_sha256'])
        self.assertFalse(ready['external_mutations_authorized'])

    def test_explicit_new_chat_project_configuration_does_not_select_or_build(self):
        root = Path(self.folder.name).resolve() / 'new-chat'
        P.init(root, 'Another garden', 'net-new', 'app', 'none', selection_policy='conversation-evidence-v1')
        status = P.stage_status(root)
        self.assertEqual(status['selection_policy'], 'conversation-evidence-v1')
        self.assertEqual(status['next_stage'], 'access')
        self.assertIsNone(status['choice_assurance'])
        with self.assertRaises(ValueError):
            P.stage_require(root, 'build')


if __name__ == '__main__':
    unittest.main()
