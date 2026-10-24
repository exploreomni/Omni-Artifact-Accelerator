"""Synthetic discovery journeys test cooperating gates, not user or native claims."""
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


P = load('visual_gate_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = load('visual_gate_fixtures', 'tests/stage_gate_fixture.py')
S = P.routing_helper('stage_gates')


class VisualDiscoveryGates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic operational observations', 'net-new', 'app', 'none')
        self.flow = G.Lifecycle(self.root, P)
        self.flow.through('narrative')
        self.spec = G.discovery_spec(self.root, P)

    def write_spec(self):
        (self.root / 'contracts/design-intent.json').write_text(json.dumps(self.spec))

    def brief(self):
        self.write_spec()
        return self.flow.stage('brief')

    def ready(self):
        self.brief()
        self.flow.stage('options')
        binding = P.stage_status(self.root)['choice_bindings']['option-1']
        self.flow.host.grants[(P.canonical(binding), 'test-choice')] = 'fixture-user'
        with P.trusted_stage_provider(self.flow.host):
            P.stage_record(self.root, {'stage': 'choice', 'option_id': 'option-1', 'receipt_ref': 'test-choice'})
            self.flow.stage('design')

    def test_unanswered_comparison_is_retained_but_blocks_concepts_and_coding(self):
        self.spec['product']['visual_experience']['follow_up']['disposition'] = 'unresolved'
        req = self.spec['requirements'][-1]
        req.update(disposition='unresolved', origin='proposal', value=None)
        req['product']['basis'] = 'unresolved'
        result = self.brief()
        self.assertEqual(result['visual_discovery']['status'], 'unresolved')
        self.assertEqual(result['next_stage'], 'brief')
        for action in ('options', 'build'):
            with self.assertRaises(ValueError):
                P.stage_require(self.root, action)
        req.update(disposition='selected', origin='user', value={'treatment': 'dimensional_styling'})
        req['product']['basis'] = 'user_statement'
        self.spec['product']['visual_experience']['follow_up']['disposition'] = 'answered'
        self.assertEqual(self.brief()['visual_discovery']['status'], 'ready')
        self.flow.stage('options')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')

    def test_snapshot_pins_notes_and_later_design_paths_are_independent(self):
        self.ready()
        with P.trusted_stage_provider(self.flow.host):
            P.stage_require(self.root, 'build')
            self.spec['selections'][0]['design_path'] = 'contracts/new-design.json'
            self.write_spec()
            P.stage_require(self.root, 'build')
            note = self.root / 'inputs/visual-fixture.json'
            original = note.read_bytes()
            note.write_text('Changed answer')
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')
            note.write_bytes(original)
            P.stage_require(self.root, 'build')
        event = json.loads((self.root / S.JOURNAL).read_text())['events'][3]
        self.assertEqual(event['payload']['discovery_dependencies'][0]['path'], 'inputs/visual-fixture.json')

    def test_new_style_reopens_d_and_invalidates_old_option_choice(self):
        self.ready()
        with P.trusted_stage_provider(self.flow.host):
            old = P.stage_status(self.root)['choice_bindings']['option-1']
            self.spec['requirements'][-1]['value'] = {'treatment': 'interactive_3d'}
            self.write_spec()
            report = P.stage_status(self.root)
            self.assertEqual(report['next_stage'], 'brief')
            self.assertIn('stage_gate_visual_discovery_changed_reopen_brief', report['findings'])
            self.brief()
            self.flow.stage('options')
            new = P.stage_status(self.root)
            self.assertNotEqual(old, new['choice_bindings']['option-1'])
            self.assertEqual(new['next_stage'], 'choice')
            with self.assertRaises(ValueError):
                P.stage_record(self.root, {'stage': 'choice', 'option_id': 'option-1', 'receipt_ref': 'test-choice'})

    def test_style_delegation_does_not_supply_the_product_selection(self):
        self.spec['product']['visual_experience']['follow_up']['disposition'] = 'delegated'
        self.spec['requirements'][-1]['value'] = {'treatment': 'delegated', 'delegation_scope': 'comparison_treatment'}
        self.assertEqual(self.brief()['visual_discovery']['status'], 'ready')
        self.flow.stage('options')
        self.assertEqual(P.stage_status(self.root)['next_stage'], 'choice')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')

    def test_illustrative_object_skips_only_the_comparison_follow_up(self):
        self.spec['requirements'][0]['value'] = {'family': 'objects_environments'}
        self.spec['requirements'][-1]['value'] = {'rationale': 'Synthetic user requests only an illustrative assembly.'}
        self.spec['product']['visual_experience']['follow_up']['disposition'] = 'not_applicable'
        report = self.brief()
        self.assertEqual(report['visual_discovery']['families'], ['objects_environments'])
        self.flow.stage('options')
        self.assertFalse(P.stage_status(self.root)['external_mutations_authorized'])

    def test_legacy_brief_write_and_unknown_payload_versions_are_rejected(self):
        request = {'stage': 'brief', 'evidence': {'brief': self.flow.evidence('legacy')}}
        with self.assertRaisesRegex(ValueError, 'visual_discovery_required'):
            P.stage_record(self.root, request)
        request = G.discovery_request(self.root, P, self.flow.evidence('new'))
        for version in (True, 2, '1'):
            with self.assertRaises(ValueError):
                P.stage_record(self.root, dict(request, discovery_version=version))
        with self.assertRaises(ValueError):
            P.stage_record(self.root, dict(request, discovery_dependencies=[]))

    def test_source_snapshot_cannot_claim_different_current_preferences(self):
        request = G.discovery_request(self.root, P, self.flow.evidence('snapshot'))
        self.spec['requirements'][-1]['value'] = {'treatment': 'dimensional_styling'}
        self.write_spec()
        with self.assertRaisesRegex(ValueError, 'visual_discovery_changed'):
            P.stage_record(self.root, request)
        self.assertEqual(P.stage_status(self.root)['next_stage'], 'brief')

    def historical_journal(self):
        """Construct pre-upgrade bytes only in a private synthetic test fixture."""
        self.ready()
        path = self.root / S.JOURNAL
        journal = json.loads(path.read_text())
        previous = P.digest(P.canonical({'project_id': journal['project_id'],
            'engagement': str(self.root), 'policy': S.POLICY}))
        stages = {}
        for event in journal['events']:
            stage = event['stage']
            if stage == 'brief':
                event['payload'] = {'evidence': {'brief': event['payload']['evidence']['brief']}}
            event['previous_sha256'] = previous
            event['predecessor_sha256'] = stages[S.STAGES[S.STAGES.index(stage) - 1]]['sha256'] if stage != 'access' else None
            body = {k: v for k, v in event.items() if k != 'sha256'}
            event['sha256'] = P.digest(P.canonical(body))
            previous = event['sha256']
            stages[stage] = event
        path.write_text(json.dumps(journal))
        # Current historical spec had no visual discovery index.
        (self.root / 'contracts/design-intent.json').write_text(json.dumps(P.intent_helper().starter(['app'], 'none')))
        binding = S._binding(self.root, P.load_project(self.root)[1], stages['options'], 'option-1')
        self.flow.host.grants[(P.canonical(binding), 'test-choice')] = 'fixture-user'
        return path.read_bytes()

    def test_selected_legacy_is_readable_without_rehashing_but_new_options_upgrade(self):
        original = self.historical_journal()
        with P.trusted_stage_provider(self.flow.host):
            report = P.stage_require(self.root, 'build')
            self.assertEqual(report['visual_discovery']['status'], 'not_assessed')
            self.assertEqual((self.root / S.JOURNAL).read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'upgrade_visual_discovery'):
                self.flow.stage('options')
            self.spec = G.discovery_spec(self.root, P)
            self.brief()
            self.assertEqual(P.stage_status(self.root)['next_stage'], 'options')
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')

    def test_adopted_discovery_cannot_be_stripped_from_draft(self):
        self.ready()
        del self.spec['product']['visual_experience']
        self.write_spec()
        with P.trusted_stage_provider(self.flow.host):
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')
            self.assertEqual(P.stage_status(self.root)['next_stage'], 'brief')

    def test_delivery_annotations_do_not_reopen_discovery_or_lose_choice(self):
        self.ready()
        with P.trusted_stage_provider(self.flow.host):
            choice = P.stage_status(self.root)['stage_bindings']['choice']
            path = self.root / 'contracts/first-selected-spec.json'
            path.write_text(json.dumps(self.spec))
            P.intent_helper().select(self.root, path, 'contracts/first-selected.json')
            self.flow.stage('design')
            row = self.spec['requirements'][-1]
            row['delivery'] = {'owner': 'app-engineer'}
            row['contexts'].append({'id': 'loading-small', 'appearance': 'light', 'state': 'loading',
                                    'viewport': [375, 650]})
            row['product']['suggested_roles'].append('app-engineer')
            path = self.root / 'contracts/resolved-selected-spec.json'
            path.write_text(json.dumps(self.spec))
            P.intent_helper().select(self.root, path, 'contracts/resolved-selected.json')
            report = P.stage_status(self.root)
            self.assertEqual(report['stage_bindings']['choice'], choice)
            self.assertEqual(report['next_stage'], 'design')
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')
            self.flow.stage('design')
            self.assertEqual(P.stage_require(self.root, 'build')['stage_bindings']['choice'], choice)

    def test_unindexed_new_treatment_cannot_bypass_changed_intent(self):
        self.ready()
        extra = copy.deepcopy(self.spec['requirements'][-1])
        extra.update(id='new-treatment', value={'treatment': 'interactive_3d'})
        self.spec['requirements'].append(extra)
        self.write_spec()
        with P.trusted_stage_provider(self.flow.host):
            with self.assertRaises(ValueError):
                P.stage_require(self.root, 'build')

    def test_d_adoption_cannot_be_replaced_by_deleting_prior_optional_decision(self):
        self.spec['requirements'][-1]['required'] = False
        self.spec['requirements'][-1]['product']['priority'] = 'could'
        self.brief()
        # No intent-select operation has happened: D itself adopted these IDs.
        self.spec['requirements'][-1]['id'] = 'replacement-style'
        self.spec['product']['visual_experience']['follow_up']['requirement_ids'] = ['replacement-style']
        self.write_spec()
        with self.assertRaisesRegex(ValueError, 'removed'):
            self.brief()


if __name__ == '__main__':
    unittest.main()
