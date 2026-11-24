"""Migration selection, revision, and candidate-bound control checks on the real journal."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


P = module('migration_gate_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = module('migration_gate_fixture', 'tests/stage_gate_fixture.py')


class MigrationGateTests(unittest.TestCase):
    def setup_route(self, treatment, *, chat=False):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve() / 'engagement'
        P.init(self.root, 'Source transfer study', 'migration', 'dashboard', 'none',
               migration_treatment=treatment, selection_policy='conversation-evidence-v1' if chat else 'host-verified-v1')
        if treatment is None:
            G.bootstrap(self.root, P, historical_migration=False)
        self.flow = G.Lifecycle(self.root, P)
        self.flow.through('brief')
        self.source = self.flow.evidence('source', 'Original fixture report and observed count.')
        self.spec_path = 'contracts/source-baseline.json'
        self.write(self.spec_path, {'schema_version': 1, 'source_evidence': [self.source],
            'views': [{'id': 'summary', 'title': 'Summary', 'layout': 'Single amount',
                       'components': ['total'], 'controls': [], 'evidence': [self.source]}],
            'controls': [], 'no_controls_evidence': [self.source], 'deviations': [],
            'cases': [{'id': 'open', 'action': 'Open summary', 'controls': [], 'persona': 'reader',
                       'state': {}, 'outputs': {'total': 2}, 'evidence': [self.source]}]})

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def offer(self):
        return P.stage_record(self.root, {'stage': 'options', 'migration_treatment': 'preserve',
                                          'evidence': {'source_baseline': self.spec_path}})

    def test_strict_confirmation_binds_all_source_bytes_and_choice(self):
        self.setup_route('preserve')
        self.assertEqual(P.stage_status(self.root)['host_checkpoint']['action'], 'prepare_source_baseline')
        self.assertEqual(P.routing_helper('stage_gates').concept_preflight(self.root, {}, P)['status'], 'prepare_source_baseline')
        offer = self.offer()
        self.assertEqual(offer['host_checkpoint']['action'], 'confirm_source_baseline')
        self.assertEqual(set(offer['choice_bindings']), {'source-baseline'})
        with self.assertRaisesRegex(ValueError, 'predecessor_incomplete'):
            P.stage_require(self.root, 'build')
        choice = {'stage': 'choice', 'receipt_ref': 'receipt', 'option_id': 'source-baseline'}
        with self.assertRaisesRegex(ValueError, 'trusted_provider_required'):
            P.stage_record(self.root, choice)
        with P.trusted_stage_provider(self.flow.host):
            binding = offer['choice_bindings']['source-baseline']
            self.flow.host.grants[P.canonical(binding), 'receipt'] = 'fixture-source-owner'
            self.assertEqual(P.stage_record(self.root, choice)['next_stage'], 'design')
            (self.root / self.source).write_text('Updated original report')
            self.assertEqual(P.stage_status(self.root)['next_stage'], 'options')
            revised = self.offer()
            self.assertNotEqual(binding, revised['choice_bindings']['source-baseline'])
            with self.assertRaisesRegex(ValueError, 'trusted_choice_unverified'):
                P.stage_record(self.root, choice)

    def test_pending_cannot_enter_design_until_user_selects_treatment(self):
        self.setup_route(None)
        self.assertEqual(P.stage_status(self.root)['host_checkpoint']['action'], 'select_migration_treatment')
        with self.assertRaisesRegex(ValueError, 'migration_treatment_selection_required'):
            P.stage_require(self.root, 'options')
        P.select_migration_treatment(self.root, 'preserve')
        P.routing_helper('delivery_workflow').record_guidance(self.root, {'id': 'migration-route',
            'loaded_guidance': ['skills/omni-artifact-accelerator/references/migration-fidelity.md']})
        self.assertEqual(P.stage_status(self.root)['host_checkpoint']['action'], 'prepare_source_baseline')
        self.assertEqual(self.offer()['next_stage'], 'choice')

    def test_redesign_requires_source_and_keeps_three_concepts(self):
        self.setup_route('redesign')
        concepts = G.concept_options(self.root, P, ['one', 'two', 'three'])
        comparison = self.flow.evidence('comparison')
        request = {'stage': 'options', 'options': concepts, 'evidence': {'comparison': comparison}}
        with self.assertRaisesRegex(ValueError, 'options_must_match_migration_treatment'):
            P.stage_record(self.root, request)
        request.update(migration_treatment='redesign')
        request['evidence']['source_baseline'] = self.spec_path
        with self.assertRaisesRegex(ValueError, 'exactly_three'):
            P.stage_record(self.root, dict(request, options=concepts[:1]))
        receipt = P.routing_helper('migration_fidelity').baseline(self.root, self.spec_path)
        for row in concepts:
            manifest = json.loads((self.root / row['evidence']).read_text())
            manifest['migration_scope'] = {'source_baseline_sha256': receipt['baseline_sha256'],
                                           'view_ids': ['summary'], 'control_ids': []}
            self.write(row['evidence'], manifest)
        result = P.stage_record(self.root, request)
        self.assertEqual(result['host_checkpoint']['action'], 'request_design_choice')
        self.assertEqual(set(result['choice_bindings']), {'one', 'two', 'three'})
        self.assertEqual(result['migration_baseline']['baseline_sha256'], receipt['baseline_sha256'])

    def test_chat_baseline_to_frozen_candidate_and_partial_qa(self):
        self.setup_route('preserve', chat=True)
        offer = self.offer()
        binding = offer['choice_bindings']['source-baseline']
        response = 'evidence/source-confirmation.json'
        self.write(response, {'schema_version': 1, 'kind': 'oaa_conversation_choice',
            'source': {'host': 'fixture', 'conversation_ref': 'test', 'question_ref': 'confirm',
                       'response_ref': None, 'role': 'user'},
            'response_text': 'Confirm the original summary and its scope.',
            'selected_option_id': 'source-baseline', 'expected_binding': binding, 'recorded_by': 'fixture-agent',
            'assurance': 'agent_attested_not_independently_authenticated'})
        choice = P.stage_record(self.root, {'stage': 'choice', 'option_id': 'source-baseline',
            'basis': 'conversation_evidence', 'expected_binding': binding, 'evidence': {'user_response': response}})
        self.assertFalse(choice['external_mutations_authorized'])
        digest = offer['migration_baseline']['baseline_sha256']

        def source_design(spec, design):
            handoff = design['experience_handoff']
            del handoff['concept_manifest_path']
            handoff['treatment_coverage'] = [{'requirement_id': ident, 'destination_ids': ['main'],
                'implementation': 'Carry forward the approved comparison treatment in the main view.'}
                for ident in spec['product']['visual_experience']['follow_up']['requirement_ids']]
            handoff.update(schema_version=2, source_baseline_path=self.spec_path, source_baseline_sha256=digest,
                           view_coverage=[{'view_id': 'summary', 'destination_ids': ['main']}], control_coverage=[])

        path = G.selected_handoff(self.root, P, {'evidence': self.spec_path}, transform=source_design)
        P.stage_record(self.root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})
        artifact = self.flow.evidence('candidate')
        frozen = P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'one', 'builders': ['builder'],
                                             'artifacts': [artifact]})
        sha = frozen['candidate_sha256']
        req = {'stage': 'review', 'scope': 'qa', 'reviewer': 'independent', 'outcome': 'resolved',
            'basis': 'source', 'iteration_sha256': frozen['candidate']['event_sha256'], 'candidate_sha256': sha,
            'evidence': {'review': self.flow.evidence('qa')}}
        with self.assertRaisesRegex(ValueError, 'control_parity_unresolved'):
            P.stage_record(self.root, req)
        observations = 'evidence/observations.json'
        req['evidence']['migration_observations'] = observations
        check = {'schema_version': 1, 'baseline_sha256': digest, 'candidate_sha256': sha, 'controls': [], 'cases': []}
        self.write(observations, check)
        partial = P.stage_record(self.root, dict(req, outcome='changes_requested'))
        self.assertEqual(partial['migration_parity'], 'partial')
        self.assertFalse(partial['release_ready'])
        with self.assertRaisesRegex(ValueError, 'control_parity_unresolved'):
            P.stage_record(self.root, req)
        # Keep the original review and observation bytes available for replay.
        new_obs = 'evidence/target-summary.json'
        check['cases'] = [{'id': 'open', 'persona': 'reader', 'state': {}, 'outputs': {'total': 2},
                           'evidence': [self.flow.evidence('target', 'Rendered source-independent summary count = 2')]}]
        self.write(new_obs, check)
        req['evidence']['migration_observations'] = new_obs
        matched = P.stage_record(self.root, req)
        self.assertEqual(matched['migration_parity'], 'matched')
        self.assertFalse(matched['release_ready'])  # The other three scopes are still open.
        self.write(new_obs, {'unrelated': True})
        self.assertEqual(P.stage_status(self.root)['migration_parity'], 'stale')
        self.write(new_obs, check)
        for scope in ('security', 'product_owner', 'ui_ux'):
            P.stage_record(self.root, dict(req, scope=scope, evidence={'review': self.flow.evidence(scope)}))
        revised = P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'two', 'builders': ['builder'],
                                             'artifacts': [self.flow.evidence('changed-summary')]})
        self.assertNotEqual(revised['candidate_sha256'], sha)
        self.assertEqual(revised['migration_parity'], 'not_assessed')
        self.assertEqual(revised['incremental_review']['scopes']['qa']['action'], 'fresh_review')
        self.assertIn('candidate_bound_migration_observations_required',
                      revised['incremental_review']['scopes']['qa']['reasons'])
        current = {'candidate_sha256': revised['candidate_sha256'],
                   'iteration_sha256': revised['candidate']['event_sha256']}
        with self.assertRaisesRegex(ValueError, 'fresh_migration_qa_required'):
            P.stage_record(self.root, dict(current, stage='review_carry_forward', scope='qa', assessed_by='reviewer',
                source_review_sha256=matched['reviews']['qa']['event_sha256'], expected_tail_sha256=revised['tail_sha256']))
        with self.assertRaisesRegex(ValueError, 'stale_candidate'):
            P.stage_record(self.root, dict(req, **current))
        self.assertFalse(P.stage_status(self.root)['release_ready'])


if __name__ == '__main__':
    unittest.main()
