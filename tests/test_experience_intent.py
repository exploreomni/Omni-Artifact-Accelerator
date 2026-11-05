"""Original pure contract fixtures; no rendered, native or human-quality claims."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('experience_test_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E = load('experience_intent')
P = load('product_intent')


def requirement(ident, value, *, basis='user_statement', disposition='selected', required=True):
    return {'id': ident, 'category': 'experience', 'purpose': 'Preserve the requested investigation outcome',
            'surfaces': ['app'], 'required': required, 'origin': E.BASES[basis], 'disposition': disposition,
            'value': value, 'asset_ids': [], 'decision_ref': 'inputs/request.md#task',
            'contexts': [{'id': 'default', 'appearance': 'light', 'state': 'ready'}],
            'product': {'priority': 'must' if required else 'could', 'basis': basis,
                'source_refs': ['inputs/request.md#task'], 'acceptance': ['Inspect the selected record and preserve scope.'],
                'suggested_roles': ['app-designer']}}


def fixture():
    promise = requirement('record-investigation', {'kind': 'experience_promise',
        'user_task': 'Investigate a selected record', 'promise': 'Useful evidence with a recoverable return',
        'primary_action': 'Inspect record', 'success': 'Understand the selected record in its original scope',
        'first_use': 'Enter the scoped record list', 'repeat_use': 'Return directly to the investigation'})
    promise['delivery'] = {'source_ref': 'inputs/request.md#task', 'owner': 'app-designer',
        'behavior': 'Inspect scoped record evidence', 'destinations': ['workspace', 'detail'],
        'journeys': ['inspect-record'], 'dependency_paths': ['contracts/query.json']}
    mode = requirement('workspace-hypothesis', {'kind': 'experience_mode', 'mode': 'workspace',
        'rationale': 'Compare records, then inspect one without losing the list context'},
        basis='recommendation', disposition='unresolved', required=False)
    spec = {'surfaces': ['app'], 'requirements': [promise, mode], 'selections': [],
        'product': {'schema_version': 1, 'scope': 'new_experience', 'discovery': 'sufficient',
                    'note_paths': ['inputs/request.md'], 'experience_intent': {'schema_version': 1,
                    'requirement_ids': ['record-investigation'], 'mode_requirement_ids': ['workspace-hypothesis']}}}
    behavior = {'kind': 'transition', 'trigger': {'control_id': 'inspect-record', 'action': 'Inspect record'},
        'before': {'destination_id': 'workspace', 'state': 'browsing', 'evidence_ids': ['record-list']},
        'after': {'destination_id': 'detail', 'state': 'selected-record', 'evidence_ids': ['record-detail']},
        'useful_change': 'Expose the selected record history and exact values',
        'evidence': [{'id': 'record-list', 'binding_ids': ['records'], 'meaning': 'Scoped comparable records'},
                     {'id': 'record-detail', 'binding_ids': ['records'], 'meaning': 'Selected record evidence'}],
        'governed_bindings': [{'id': 'records', 'path': 'contracts/query.json', 'reference': 'records query; record identity and observations'}],
        'context_preservation': 'Preserve selected identity, period and record-list ordering',
        'return': {'destination_id': 'workspace', 'control_id': 'return-to-records', 'state': 'browsing'},
        'recovery': {'empty': 'Explain that this scope has no matching records; retain the scope.',
                     'error': 'Retain the requested scope and expose the qualified retry path.'}}
    design = {'destinations': [{'id': 'workspace', 'surface': 'app'}, {'id': 'detail', 'surface': 'app'}],
              'journeys': [{'id': 'inspect-record', 'destination_ids': ['workspace', 'detail'],
                            'action': 'Inspect record', 'experience_behavior': behavior}],
              'experience_intent_handoff': {'schema_version': 1, 'context': E.context(spec),
                    'selected_mode_ids': ['workspace-hypothesis'], 'journey_ids': ['inspect-record']}}
    return spec, design


class ExperienceIntentTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.design = fixture()

    def req(self, ident='record-investigation'):
        return next(r for r in self.spec['requirements'] if r['id'] == ident)

    def behavior(self):
        return self.design['journeys'][0]['experience_behavior']

    def refresh(self):
        self.design['experience_intent_handoff']['context'] = E.context(self.spec)

    def test_historical_missing_index_stays_unassessed(self):
        del self.spec['product']['experience_intent']
        self.assertIsNone(E.context(self.spec))
        self.assertEqual(E.report(self.spec)['status'], 'not_assessed')
        self.assertEqual(E.validate_handoff({}, self.spec)['status'], 'not_assessed')
        E.validate_transition({}, self.spec)

    def test_explicit_null_adoption_is_not_historical(self):
        self.spec['product']['experience_intent'] = None
        with self.assertRaisesRegex(ValueError, 'index_invalid'):
            E.validate(self.spec)

    def test_sourced_promise_ready_with_unresolved_creative_hypothesis(self):
        report = E.report(self.spec)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(report['creative_hypothesis_ids'], ['workspace-hypothesis'])
        self.assertFalse(report['concept_selected'])
        self.assertFalse(report['execution_authorized'])

    def test_no_mode_at_discovery_is_valid_but_handoff_needs_chosen_mode(self):
        self.spec['requirements'].pop()
        self.spec['product']['experience_intent']['mode_requirement_ids'] = []
        self.assertEqual(E.report(self.spec)['status'], 'ready')
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'chosen_mode_unknown'):
            E.validate_handoff(self.design, self.spec)

    def test_creative_resolution_does_not_rewrite_discovery_context(self):
        before = E.context(self.spec)
        self.req('workspace-hypothesis')['value']['rationale'] = 'A revised composition hypothesis'
        self.req('workspace-hypothesis')['disposition'] = 'selected'
        self.req()['delivery']['behavior'] = 'Resolved detail treatment'
        self.assertEqual(E.context(self.spec), before)
        before['requirements'][0]['value']['promise'] = 'mutated returned copy'
        self.assertNotEqual(E.context(self.spec), before)

    def test_promised_meaning_changes_invalidate_exact_handoff(self):
        self.req()['value']['promise'] = 'A changed experience promise'
        with self.assertRaisesRegex(ValueError, 'handoff_context_changed'):
            E.validate_handoff(self.design, self.spec)

    def test_unsourced_promise_does_not_become_ready_from_silence(self):
        self.req()['origin'] = 'proposal'
        self.req()['product']['basis'] = 'recommendation'
        self.assertEqual(E.report(self.spec)['status'], 'unresolved')
        self.assertIn('experience_promise_source_or_delegation_required',
                      [f['code'] for f in E.report(self.spec)['findings']])

    def test_actual_scoped_delegation_allows_working_promise(self):
        self.req()['origin'] = 'proposal'
        self.req()['product']['basis'] = 'recommendation'
        delegation = requirement('direction-delegation', {'delegation_scope': 'experience_direction'})
        self.spec['requirements'].append(delegation)
        self.spec['product']['experience_intent']['delegation_requirement_id'] = 'direction-delegation'
        self.assertEqual(E.report(self.spec)['status'], 'ready')
        delegation['product']['basis'], delegation['origin'] = 'recommendation', 'proposal'
        with self.assertRaisesRegex(ValueError, 'actual_source_required'):
            E.validate(self.spec)

    def test_wrong_scope_or_surface_delegation_rejected(self):
        delegation = requirement('direction-delegation', {'delegation_scope': 'comparison_treatment'})
        self.spec['requirements'].append(delegation)
        self.spec['product']['experience_intent']['delegation_requirement_id'] = 'direction-delegation'
        with self.assertRaisesRegex(ValueError, 'scoped_delegation_required'):
            E.validate(self.spec)

    def test_each_target_surface_needs_a_sourced_promise(self):
        self.spec['surfaces'].append('dashboard')
        self.assertEqual(E.report(self.spec)['status'], 'unresolved')
        self.assertIn({'code': 'experience_surface_promise_missing', 'surface': 'dashboard'}, E.report(self.spec)['findings'])

    def test_source_attribution_and_notes_are_exact(self):
        self.req()['decision_ref'] = 'invented approval'
        with self.assertRaisesRegex(ValueError, 'decision_source_required'):
            E.validate(self.spec)
        self.req()['decision_ref'] = 'inputs/request.md#task'
        self.req()['product']['source_refs'] = ['inputs/other.md#task']
        with self.assertRaisesRegex(ValueError, 'source_notes_required'):
            E.validate(self.spec)

    def test_visual_treatment_cannot_replace_workflow_mode(self):
        self.req('workspace-hypothesis')['value'] = {'treatment': 'refined_2d'}
        with self.assertRaisesRegex(ValueError, 'mode_invalid'):
            E.validate(self.spec)

    def test_custom_and_hybrid_modes_are_supported(self):
        for value in ({'kind': 'experience_mode', 'mode': 'custom', 'custom_label': 'Evidence notebook',
                       'rationale': 'Read and compare original observations'},
                      {'kind': 'experience_mode', 'mode': 'hybrid', 'components': ['narrative', 'workspace'],
                       'rationale': 'Explain the question, then permit investigation'}):
            with self.subTest(mode=value['mode']):
                self.req('workspace-hypothesis')['value'] = value
                self.assertEqual(E.validate_handoff(self.design, self.spec)['status'], 'consistent')

    def test_sourced_mode_constraint_cannot_be_silently_dropped(self):
        self.spec['requirements'].append(requirement('selected-mode', {'kind': 'experience_mode',
            'mode': 'narrative', 'rationale': 'The user asked for a guided explanation'}))
        self.spec['product']['experience_intent']['mode_requirement_ids'].append('selected-mode')
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'sourced_mode_constraint_dropped'):
            E.validate_handoff(self.design, self.spec)

    def test_conflicting_sourced_modes_are_open_not_silently_combined(self):
        for name in ('workspace', 'narrative'):
            self.spec['requirements'].append(requirement(name, {'kind': 'experience_mode',
                'mode': name, 'rationale': 'A recorded user direction'}))
            self.spec['product']['experience_intent']['mode_requirement_ids'].append(name)
        self.assertIn({'code': 'experience_mode_constraints_conflict', 'surface': 'app'}, E.report(self.spec)['findings'])

    def test_adopted_context_and_requirement_ids_cannot_disappear(self):
        old = copy.deepcopy(self.spec)
        del self.spec['product']['experience_intent']
        with self.assertRaisesRegex(ValueError, 'adopted_context_removed'):
            E.validate_transition(old, self.spec)
        self.spec = copy.deepcopy(old)
        self.spec['requirements'].pop()
        self.spec['product']['experience_intent']['mode_requirement_ids'] = []
        with self.assertRaisesRegex(ValueError, 'adopted_requirement_removed'):
            E.validate_transition(old, self.spec)

    def test_actual_omission_reconciles_mode_removal(self):
        old = copy.deepcopy(self.spec)
        req = self.req('workspace-hypothesis')
        req.update(origin='user', disposition='explicitly_omitted')
        req['product']['basis'] = 'user_statement'
        self.spec['product']['experience_intent']['mode_requirement_ids'] = []
        E.validate_transition(old, self.spec)
        req['origin'], req['product']['basis'] = 'proposal', 'recommendation'
        with self.assertRaisesRegex(ValueError, 'actual_source_required'):
            E.validate_transition(old, self.spec)

    def test_sourced_promise_cannot_be_replaced_by_proposal(self):
        old = copy.deepcopy(self.spec)
        self.req()['origin'], self.req()['product']['basis'] = 'proposal', 'recommendation'
        with self.assertRaisesRegex(ValueError, 'sourced_promise_replaced_by_proposal'):
            E.validate_transition(old, self.spec)

    def test_unindexed_active_modes_and_bounds_fail_closed(self):
        self.spec['product']['experience_intent']['mode_requirement_ids'] = []
        with self.assertRaisesRegex(ValueError, 'unindexed_experience_requirement'):
            E.validate(self.spec)
        self.spec, _ = fixture()
        with patch.object(E, 'MAX_CONTEXT_BYTES', 16):
            with self.assertRaisesRegex(ValueError, 'indexed_requirements_exceeds_bound'):
                E.validate(self.spec)

    def test_handoff_proves_only_declaration_not_quality(self):
        result = E.validate_handoff(self.design, self.spec)
        self.assertEqual(result['status'], 'consistent')
        self.assertFalse(result['behavior_observed'])
        self.assertFalse(result['claims_authenticated'])
        self.assertEqual(result['journey_ids'], ['inspect-record'])

    def test_transition_must_change_declared_state(self):
        self.behavior()['after'] = copy.deepcopy(self.behavior()['before'])
        with self.assertRaisesRegex(ValueError, 'transition_must_change_state'):
            E.validate_handoff(self.design, self.spec)

    def test_evidence_order_only_does_not_establish_a_transition(self):
        self.behavior()['before']['evidence_ids'] = ['record-list', 'record-detail']
        self.behavior()['after'] = copy.deepcopy(self.behavior()['before'])
        self.behavior()['after']['evidence_ids'].reverse()
        with self.assertRaisesRegex(ValueError, 'transition_must_change_state'):
            E.validate_handoff(self.design, self.spec)

    def test_trigger_and_canonical_action_cannot_drift(self):
        self.behavior()['trigger']['action'] = 'Show another total'
        with self.assertRaisesRegex(ValueError, 'promised_action'):
            E.validate_handoff(self.design, self.spec)
        self.behavior()['trigger']['action'] = 'Inspect record'
        self.design['journeys'][0]['action'] = 'Unrelated action'
        with self.assertRaisesRegex(ValueError, 'canonical_journey_action_mismatch'):
            E.validate_handoff(self.design, self.spec)

    def test_governed_bindings_require_explicit_pinned_dependencies(self):
        self.req()['delivery']['dependency_paths'] = []
        with self.assertRaisesRegex(ValueError, 'binding_path_must_be_explicit_dependency'):
            E.validate_handoff(self.design, self.spec)
        self.req()['delivery']['dependency_paths'] = ['../escape.json']
        self.behavior()['governed_bindings'][0]['path'] = '../escape.json'
        with self.assertRaisesRegex(ValueError, 'path_invalid'):
            E.validate_handoff(self.design, self.spec)

    def test_unknown_evidence_and_missing_recovery_fail(self):
        self.behavior()['after']['evidence_ids'] = ['unmapped-evidence']
        with self.assertRaisesRegex(ValueError, 'state_evidence_unknown'):
            E.validate_handoff(self.design, self.spec)
        self.behavior()['after']['evidence_ids'] = ['record-detail']
        del self.behavior()['recovery']['error']
        with self.assertRaisesRegex(ValueError, 'recovery_invalid'):
            E.validate_handoff(self.design, self.spec)

    def test_single_view_monitoring_is_legitimate_and_explicit(self):
        self.req('workspace-hypothesis')['value']['mode'] = 'monitoring'
        self.behavior().update(kind='single_view', after=copy.deepcopy(self.behavior()['before']),
            single_view_rationale='The selected task is reading the current scoped observations; no navigation is needed.')
        self.behavior()['trigger']['control_id'] = None
        self.behavior()['return']['control_id'] = None
        self.assertEqual(E.validate_handoff(self.design, self.spec)['status'], 'consistent')
        self.behavior()['after']['state'] = 'different'
        with self.assertRaisesRegex(ValueError, 'single_view_case_invalid'):
            E.validate_handoff(self.design, self.spec)

    def test_dashboard_target_remains_valid_without_an_app_template(self):
        self.spec['surfaces'] = ['dashboard']
        for req in self.spec['requirements']:
            req['surfaces'] = ['dashboard']
        for destination in self.design['destinations']:
            destination['surface'] = 'dashboard'
        self.refresh()
        self.assertEqual(E.validate_handoff(self.design, self.spec)['status'], 'consistent')

    def test_return_destination_cannot_escape_promised_surface(self):
        self.spec['surfaces'].append('dashboard')
        promise = copy.deepcopy(self.req())
        promise.update(id='dashboard-promise', surfaces=['dashboard'])
        self.spec['requirements'].append(promise)
        self.spec['product']['experience_intent']['requirement_ids'].append('dashboard-promise')
        mode = copy.deepcopy(self.req('workspace-hypothesis'))
        mode.update(id='dashboard-mode', surfaces=['dashboard'])
        self.spec['requirements'].append(mode)
        self.spec['product']['experience_intent']['mode_requirement_ids'].append('dashboard-mode')
        self.design['experience_intent_handoff']['selected_mode_ids'].append('dashboard-mode')
        self.design['destinations'].append({'id': 'dashboard-return', 'surface': 'dashboard'})
        self.design['journeys'][0]['destination_ids'].append('dashboard-return')
        self.behavior()['return']['destination_id'] = 'dashboard-return'
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'journey_surface_binding_invalid'):
            E.validate_handoff(self.design, self.spec)

    def test_product_integration_accepts_index_and_exports_api(self):
        P.validate(self.spec, E.need, E.relative, ['app-designer'])
        self.assertEqual(P.experience_context(self.spec), E.context(self.spec))
        self.assertEqual(P.experience_report(self.spec), E.report(self.spec))
        self.assertEqual(P.validate_experience_handoff(self.design, self.spec)['status'], 'consistent')
        P.validate_experience_transition(self.spec, self.spec)

    def test_readable_projection_preserves_promises_without_quality_claim(self):
        helper = type('FixtureIntent', (), {'read_record': lambda self, root, pin: {'spec': self_spec}})()
        self_spec = self.spec
        selected = {'path': 'contracts/selected.json', 'sha256': 'a' * 64}
        with patch.object(P.P, 'intent_helper', return_value=helper):
            rendered = P.render((Path('/original-fixture'), {'name': 'Original investigation'}),
                                {'selected': selected}, '2030-01-01T00:00:00Z').decode()
        self.assertIn('Experience promises: ready', rendered)
        self.assertIn('Creative mode hypotheses', rendered)
        self.assertIn('does not select a concept or certify product fit', rendered)


if __name__ == '__main__':
    unittest.main()
