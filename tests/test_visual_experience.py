"""Original synthetic intent cases; no interview, rendering or approval claims."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location('visual_product_tests', ROOT / 'skills/omni-artifact-accelerator/scripts/product_intent.py')
N = importlib.util.module_from_spec(_s)
_s.loader.exec_module(N)
D = N.P.intent_helper()
V = N.V


def requirement(ident, value, basis='user_statement', disposition='selected', surfaces=None):
    origin = {'user_statement': 'user', 'reused_decision': 'reused', 'recommendation': 'proposal',
              'inference': 'proposal', 'unresolved': 'proposal'}[basis]
    ref = 'inputs/visual-notes.json#' + ident
    return {'id': ident, 'category': 'visual_experience', 'purpose': 'Explore measured garden observations.',
            'surfaces': surfaces or ['app'], 'required': True, 'origin': origin,
            'disposition': disposition, 'value': value, 'asset_ids': [],
            'decision_ref': ref if disposition in {'selected', 'explicitly_omitted'} else None,
            'contexts': [{'id': 'ready', 'appearance': 'light', 'state': 'ready'}],
            'product': {'priority': 'must', 'basis': basis, 'source_refs': [ref],
                        'acceptance': ['Original observations remain readable and traceable.'],
                        'suggested_roles': ['product-owner', 'app-designer']}}


def specimen():
    spec = D.starter(['app'], 'none')
    spec['product'] = {'schema_version': 1, 'scope': 'new_experience', 'discovery': 'sufficient',
        'note_paths': ['inputs/visual-notes.json'], 'visual_experience': {
            'schema_version': 1, 'family_requirement_ids': ['family'],
            'follow_up': {'disposition': 'answered', 'requirement_ids': ['treatment']}}}
    spec['requirements'] = [requirement('family', {'family': 'compare_track'}),
                            requirement('treatment', {'treatment': 'refined_2d'})]
    return spec


class VisualExperienceTests(unittest.TestCase):
    def setUp(self):
        self.spec = specimen()

    @property
    def meta(self):
        return self.spec['product']['visual_experience']

    def validate(self):
        return D.validate(self.spec, {'surfaces': self.spec['surfaces']})

    def test_real_answer_and_reused_answer_preserve_canonical_values(self):
        self.validate()
        self.assertEqual(N.visual_report(self.spec), {'status': 'ready', 'families': ['compare_track'],
            'follow_up': {'disposition': 'answered', 'requirement_ids': ['treatment']},
            'requirement_ids': ['family', 'treatment'], 'findings': []})
        self.meta['follow_up']['disposition'] = 'reused'
        self.spec['requirements'][1] = requirement('treatment', {'treatment': 'interactive_3d'}, 'reused_decision')
        self.validate()
        self.assertEqual(N.visual_report(self.spec)['status'], 'ready')

    def test_open_follow_up_is_valid_draft_and_blocks_readiness(self):
        self.meta['follow_up'] = {'disposition': 'unresolved', 'requirement_ids': []}
        self.spec['requirements'].pop()
        self.validate()
        report = N.visual_report(self.spec)
        self.assertEqual(report['status'], 'unresolved')
        self.assertTrue(report['findings'][0]['comparison_in_scope'])
        self.assertTrue(any('comparison treatment' in q for q in D.choice_report(self.spec)[0]))
        self.meta['follow_up']['requirement_ids'] = ['open-treatment']
        self.spec['requirements'].append(requirement('open-treatment', None, 'unresolved', 'unresolved'))
        self.validate()
        self.assertEqual(N.visual_report(self.spec)['status'], 'unresolved')

    def test_recommended_family_requires_real_family_delegation(self):
        self.spec['requirements'][0] = requirement('family', {'family': 'compare_track'}, 'recommendation')
        self.validate()
        self.assertEqual(N.visual_report(self.spec)['status'], 'unresolved')
        self.meta['family_delegation_requirement_id'] = 'family-delegation'
        self.spec['requirements'].append(requirement('family-delegation', {'delegation_scope': 'visual_families'}))
        self.validate()
        self.assertEqual(N.visual_report(self.spec)['status'], 'ready')
        self.assertIn('family-delegation', N.visual_report(self.spec)['requirement_ids'])
        self.meta['follow_up'] = {'disposition': 'unresolved', 'requirement_ids': []}
        self.spec['requirements'] = [r for r in self.spec['requirements'] if r['id'] != 'treatment']
        self.assertEqual(N.visual_report(self.spec)['status'], 'unresolved')  # families never imply styling delegation

    def test_treatment_delegation_is_distinct_from_family_delegation(self):
        self.meta['follow_up']['disposition'] = 'delegated'
        self.spec['requirements'][1] = requirement('treatment', {
            'treatment': 'delegated', 'delegation_scope': 'comparison_treatment'})
        self.validate()
        self.assertEqual(N.visual_report(self.spec)['status'], 'ready')
        self.spec['requirements'][0] = requirement('family', {'family': 'compare_track'}, 'recommendation')
        self.assertEqual(N.visual_report(self.spec)['status'], 'unresolved')
        self.spec['requirements'][1]['value']['delegation_scope'] = 'visual_families'
        with self.assertRaisesRegex(ValueError, 'treatment_delegation_scope_invalid'):
            self.validate()

    def test_agent_cannot_claim_delegation_or_reuse(self):
        for disposition, value in [('delegated', {'treatment': 'delegated', 'delegation_scope': 'comparison_treatment'}),
                                   ('reused', {'treatment': 'refined_2d'})]:
            with self.subTest(disposition=disposition):
                self.spec = specimen()
                self.meta['follow_up']['disposition'] = disposition
                self.spec['requirements'][1] = requirement('treatment', value, 'recommendation')
                with self.assertRaisesRegex(ValueError, 'attributable_answer_or_delegation'):
                    self.validate()
        self.spec = specimen()
        self.meta['family_delegation_requirement_id'] = 'claimed-delegation'
        self.spec['requirements'].append(requirement('claimed-delegation', {'delegation_scope': 'visual_families'}, 'inference'))
        with self.assertRaisesRegex(ValueError, 'attributable_answer_or_delegation'):
            self.validate()

    def test_not_applicable_cannot_hide_requested_or_recommended_comparisons(self):
        for basis in ['user_statement', 'recommendation', 'inference']:
            with self.subTest(basis=basis):
                self.spec = specimen()
                self.spec['requirements'][0] = requirement('family', {'family': 'compare_track'}, basis)
                self.meta['follow_up']['disposition'] = 'not_applicable'
                self.spec['requirements'][1]['value'] = {'rationale': 'No comparison style is needed.'}
                with self.assertRaisesRegex(ValueError, 'cannot_be_not_applicable'):
                    self.validate()

    def test_noncomparison_scope_accepts_sourced_rationale(self):
        for family in ['locations', 'objects_environments', 'movement_flow', 'atmosphere_context']:
            with self.subTest(family=family):
                self.spec = specimen()
                self.spec['requirements'][0]['value'] = {'family': family}
                self.meta['follow_up']['disposition'] = 'not_applicable'
                self.spec['requirements'][1]['value'] = {'rationale': 'The sourced choice is an illustrative garden visit without comparisons.'}
                self.validate()
                self.assertEqual(N.visual_report(self.spec)['status'], 'ready')
        self.spec['requirements'][1]['product']['source_refs'] = []
        with self.assertRaises(ValueError):
            self.validate()

    def test_custom_family_is_bounded_and_declares_comparison_applicability(self):
        self.spec['requirements'][0]['value'] = {'family': 'custom', 'custom_label': 'Tactile specimen explorer',
                                               'includes_comparisons': True}
        self.validate()
        self.meta['follow_up']['disposition'] = 'not_applicable'
        self.spec['requirements'][1]['value'] = {'rationale': 'An original spatial form.'}
        with self.assertRaisesRegex(ValueError, 'cannot_be_not_applicable'):
            self.validate()
        self.spec['requirements'][0]['value']['includes_comparisons'] = False
        self.validate()
        self.spec['requirements'][0]['value']['custom_label'] = 'x' * 121
        with self.assertRaisesRegex(ValueError, 'custom_family'):
            self.validate()

    def test_index_cannot_exclude_an_active_comparison_recommendation(self):
        self.spec['requirements'][0]['value'] = {'family': 'locations'}
        self.spec['requirements'].append(requirement('hidden-comparison', {'family': 'compare_track'}, 'recommendation'))
        with self.assertRaisesRegex(ValueError, 'family_requirement_missing_from_index'):
            self.validate()

    def test_unrelated_requirement_values_are_not_reinterpreted_as_visual_families(self):
        typography = requirement('typography', {'family': 'Serif example'})
        typography['category'] = 'typography'
        self.spec['requirements'].append(typography)
        self.validate()
        self.assertNotIn('typography', N.visual_report(self.spec)['requirement_ids'])

    def test_active_known_treatment_cannot_hide_outside_follow_up_index(self):
        for basis in ['user_statement', 'recommendation']:
            for value in [{'treatment': 'interactive_3d'},
                          {'treatment': 'delegated', 'delegation_scope': 'comparison_treatment'},
                          {'treatment': 'delegated', 'delegation_scope': 'comparison_treatment', 'extra': 'invalid'}]:
                with self.subTest(basis=basis, value=value):
                    self.spec = specimen()
                    self.spec['requirements'].append(requirement('hidden-treatment', value, basis))
                    with self.assertRaisesRegex(ValueError, 'treatment_requirement_missing_from_index'):
                        self.validate()

    def test_unindexed_historical_treatment_requires_sourced_omission(self):
        old = requirement('old-treatment', {'treatment': 'interactive_3d'}, disposition='explicitly_omitted')
        self.spec['requirements'].append(old)
        self.validate()
        self.assertEqual(N.visual_report(self.spec)['status'], 'ready')
        old['decision_ref'] = 'inputs/visual-notes.json#unrelated'
        with self.assertRaisesRegex(ValueError, 'unindexed_omission_must_reference_its_source'):
            self.validate()

    def test_unrelated_treatment_values_do_not_enter_visual_discovery(self):
        before = N.visual_context(self.spec)
        other = requirement('horticulture', {'treatment': 'watering schedule'})
        other['category'] = 'horticulture'
        self.spec['requirements'].append(other)
        self.validate()
        self.assertEqual(before, N.visual_context(self.spec))

    def test_versions_fields_refs_and_values_fail_precisely(self):
        mutations = [
            (lambda s: s['product'].__setitem__('visual_experience', None), 'fields_invalid'),
            (lambda s: s['product']['visual_experience'].__setitem__('schema_version', True), 'version_invalid'),
            (lambda s: s['product']['visual_experience'].__setitem__('schema_version', 2), 'version_invalid'),
            (lambda s: s['product']['visual_experience'].__setitem__('authority', 'approved'), 'fields_invalid'),
            (lambda s: s['product']['visual_experience'].__setitem__('family_requirement_ids', ['missing']), 'dangling_requirement_reference'),
            (lambda s: s['product']['visual_experience']['follow_up'].__setitem__('disposition', 'approved'), 'disposition_invalid'),
            (lambda s: s['requirements'][1].__setitem__('value', {'treatment': 'designer_mix'}), 'treatment_value_invalid'),
            (lambda s: s['requirements'][0]['value'].__setitem__('treatment', 'refined_2d'), 'family_fields_invalid'),
            (lambda s: s['requirements'][1].__setitem__('decision_ref', 'inputs/visual-notes.json#different'), 'decision_must_reference_its_source'),
        ]
        for change, message in mutations:
            with self.subTest(message=message):
                self.spec = specimen(); change(self.spec)
                with self.assertRaisesRegex(ValueError, message):
                    self.validate()

    def test_surface_specific_answers_and_delegation_cannot_overreach(self):
        self.spec['surfaces'].append('dashboard')
        self.spec['selections'].append({'surface': 'dashboard', 'design_path': None, 'brand_path': None,
                                        'candidate_path': None, 'target': None})
        self.spec['requirements'][0]['surfaces'].append('dashboard')
        with self.assertRaisesRegex(ValueError, 'comparison_treatment_surface_missing'):
            self.validate()
        self.spec['requirements'][1]['surfaces'].append('dashboard')
        self.spec['requirements'][0] = requirement('family', {'family': 'compare_track'}, 'recommendation',
                                                  surfaces=['app', 'dashboard'])
        self.meta['family_delegation_requirement_id'] = 'delegation'
        self.spec['requirements'].append(requirement('delegation', {'delegation_scope': 'visual_families'}))
        with self.assertRaisesRegex(ValueError, 'family_delegation_surface_missing'):
            self.validate()
        self.spec['requirements'][2]['surfaces'].append('dashboard')
        self.validate()

    def test_semantic_snapshot_ignores_later_design_bytes_and_does_not_alias(self):
        before = N.visual_context(self.spec)
        self.spec['selections'][0].update(design_path='contracts/later-design.json', brand_path='contracts/later-brand.json')
        self.spec['product']['note_paths'].append('inputs/unrelated.json')
        self.assertEqual(before, N.visual_context(self.spec))
        before['requirements'][0]['value']['family'] = 'locations'
        self.assertEqual(self.spec['requirements'][0]['value']['family'], 'compare_track')
        self.assertEqual(N.visual_context(self.spec)['note_paths'], ['inputs/visual-notes.json'])

    def test_delivery_and_review_context_enrichment_preserve_discovery(self):
        previous = copy.deepcopy(self.spec)
        before = N.visual_context(self.spec)
        req = self.spec['requirements'][0]
        req['delivery'] = {'source_ref': req['decision_ref'], 'owner': 'app-engineer',
            'behavior': 'Bind selection to the retained observation.', 'destinations': ['garden'],
            'dependency_paths': ['contracts/runtime.json'], 'capabilities': ['custom-visualization'],
            'journeys': ['inspect-return']}
        req['product']['suggested_roles'] = ['app-engineer', 'qa-analyst']
        req['contexts'][0]['id'] = 'default-reviewed'
        req['contexts'][0]['applicability'] = [{'kind': 'destination', 'id': 'garden',
            'surface': 'app', 'lanes': {'craft': {'status': 'required'}}}]
        req['contexts'].append({'id': 'error-narrow', 'appearance': 'light', 'state': 'error',
                                'viewport': [320, 480]})
        self.validate()  # real delivery/applicability fields, not a synthetic unknown annotation
        self.assertEqual(before, N.visual_context(self.spec))
        self.assertEqual(N.visual_report(previous), N.visual_report(self.spec))
        self.assertIsNone(N.validate_visual_transition(previous, self.spec))
        projected = N.visual_context(self.spec)['requirements'][0]
        self.assertNotIn('contexts', projected)
        self.assertNotIn('delivery', projected)
        self.assertNotIn('suggested_roles', projected['product'])

    def test_discovery_projection_retains_substantive_decisions_and_provenance(self):
        mutations = [
            ('treatment', lambda s: s['requirements'][1].__setitem__('value', {'treatment': 'interactive_3d'})),
            ('required', lambda s: (s['requirements'][0].__setitem__('required', False),
                                    s['requirements'][0]['product'].__setitem__('priority', 'should'))),
            ('scope', lambda s: s['product'].__setitem__('scope', 'material_redesign')),
            ('purpose', lambda s: s['requirements'][0].__setitem__('purpose', 'Prioritize seasonal change.')),
            ('category', lambda s: s['requirements'][0].__setitem__('category', 'experience')),
            ('acceptance', lambda s: s['requirements'][0]['product']['acceptance'].append('Readable on a 320px phone.')),
            ('provenance', lambda s: (s['requirements'][0].__setitem__('decision_ref', 'inputs/visual-notes.json#revised'),
                                      s['requirements'][0]['product'].__setitem__('source_refs', ['inputs/visual-notes.json#revised']))),
            ('origin', lambda s: (s['requirements'][0].__setitem__('origin', 'reused'),
                                 s['requirements'][0]['product'].__setitem__('basis', 'reused_decision'))),
            ('alternative', lambda s: s['requirements'][0]['product'].__setitem__('alternative', {
                'unavailable_method': 'Requested runtime', 'preserved_outcome': 'Exact comparisons',
                'feasible_alternative': 'Refined vector treatment', 'remaining_gap': 'Camera navigation unqualified'})),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                self.spec = specimen()
                before = N.visual_context(self.spec)
                mutate(self.spec)
                self.validate()
                self.assertNotEqual(before, N.visual_context(self.spec))

    def test_public_transition_wrapper_protects_an_unselected_d_checkpoint(self):
        previous = copy.deepcopy(self.spec)  # raw canonical discovery, no selected-record wrapper
        del self.spec['product']['visual_experience']
        with self.assertRaisesRegex(ValueError, 'context_removed_reconcile_scope_instead'):
            N.validate_visual_transition(previous, self.spec)

    def test_adoption_cannot_be_stripped_but_explicit_sourced_omission_can_revise_scope(self):
        previous = copy.deepcopy(self.spec)
        del self.spec['product']['visual_experience']
        with self.assertRaisesRegex(ValueError, 'context_removed'):
            V.validate_transition(previous, self.spec)
        self.spec = specimen()
        for req in self.spec['requirements']:
            req['disposition'] = 'explicitly_omitted'
        self.spec['requirements'] += [requirement('new-family', {'family': 'locations'}),
            requirement('new-na', {'rationale': 'The user removed comparisons and chose locations only.'})]
        self.meta['family_requirement_ids'] = ['new-family']
        self.meta['follow_up'] = {'disposition': 'not_applicable', 'requirement_ids': ['new-na']}
        self.validate()
        V.validate_transition(previous, self.spec)
        self.assertEqual(N.visual_report(self.spec)['status'], 'ready')
        self.spec['requirements'] = self.spec['requirements'][1:]
        with self.assertRaisesRegex(ValueError, 'requirement_index_removed'):
            V.validate_transition(previous, self.spec)

    def test_optional_previous_reference_still_requires_attributable_omission(self):
        previous = specimen()
        previous['requirements'][1].update(required=False)
        previous['requirements'][1]['product']['priority'] = 'could'
        self.spec['requirements'][0]['value'] = {'family': 'locations'}
        self.spec['requirements'][1] = requirement('new-na', {'rationale': 'No comparisons in revised scope.'})
        self.meta['follow_up'] = {'disposition': 'not_applicable', 'requirement_ids': ['new-na']}
        with self.assertRaisesRegex(ValueError, 'requirement_index_removed'):
            V.validate_transition(previous, self.spec)
        omitted = requirement('treatment', {'treatment': 'refined_2d'}, 'recommendation', 'explicitly_omitted')
        self.spec['requirements'].append(omitted)
        with self.assertRaisesRegex(ValueError, 'attributable_answer_or_delegation'):
            V.validate_transition(previous, self.spec)

    def test_legacy_is_not_assessed_without_changing_the_spec(self):
        del self.spec['product']['visual_experience']
        raw = copy.deepcopy(self.spec)
        self.assertIsNone(N.visual_context(self.spec))
        self.assertEqual(N.visual_report(self.spec)['status'], 'not_assessed')
        self.assertEqual(raw, self.spec)


if __name__ == '__main__':
    unittest.main()
