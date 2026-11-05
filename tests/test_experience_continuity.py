"""Original contract and lifecycle tests, not rendered or live-host qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    source = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(source)
    source.loader.exec_module(module)
    return module


P = load('continuity_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = load('continuity_gates', 'tests/stage_gate_fixture.py')
F = load('continuity_intent', 'tests/test_experience_intent.py')
R = P.routing_helper('experience_review')
W = P.routing_helper('delivery_workflow')


class ExperienceContinuity(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve() / 'engagement'
        P.init(self.root, 'Original record investigation fixture', 'net-new', 'app', 'none')

    def save(self, path, value):
        (self.root / path).write_text(json.dumps(value))
        return path

    def pin(self, path):
        data = (self.root / path).read_bytes()
        return {'path': path, 'sha256': P.digest(data), 'bytes': len(data)}

    def prepare(self):
        G.bootstrap(self.root, P, experience=True)
        spec = G.discovery_spec(self.root, P)
        experience, _ = F.fixture()
        spec['requirements'].extend(experience['requirements'])
        spec['product']['experience_intent'] = experience['product']['experience_intent']
        spec['product']['note_paths'].append('inputs/request.md')
        (self.root / 'inputs/request.md').write_text('Synthetic user request: inspect a record and return to its scope.')
        self.save('contracts/query.json', {'kind': 'synthetic_governed_binding', 'identity': 'record_key'})
        self.save('contracts/design-intent.json', spec)
        G.refresh_request_review(self.root, P)
        return G.Lifecycle(self.root, P)

    def current_spec(self):
        project = P.load_project(self.root)[1]
        return (P.intent_helper().load_selected(self.root)['spec'] if project.get('design_intent') else
                P.read_json(self.root / project['design_intent_draft'])[0])

    def options(self):
        spec = self.current_spec()
        options = G.concept_options(self.root, P, ['one', 'two', 'three'])
        modes = [r for r in spec['requirements'] if r['id'] == 'workspace-hypothesis']
        for option in options:
            path = option['evidence']
            concept = P.read_json(self.root / path)[0]
            concept['experience_direction'] = {'context': F.E.context(spec),
                'mode_requirement_ids': ['workspace-hypothesis'], 'modes': modes,
                'authors': ['fixture-experience']}
            self.save(path, concept)
        comparison = {'schema_version': 1, 'kind': 'analyst_experience_comparison',
            'reviewer': 'fixture-creative_review', 'context': F.E.context(spec),
            'assessment': 'distinct_supported', 'rationale': 'Original synthetic distinctions; not an aesthetic judgment.',
            'options': [{'option_id': o['id'], 'concept': self.pin(o['evidence']),
                'task_relationship': 'Inspect the same governed records and return to their scope.',
                'action_outcome': ['Select record to inspect', 'Select period to inspect records',
                                   'Select missing evidence to inspect its record'][index],
                'evidence_gained': 'Original record identity and recorded observations',
                'composition_difference': ['Record index anchors detail', 'Period sequence anchors detail',
                                           'Evidence issue index anchors detail'][index],
                'visual_locator': 'focal-chart and reading order'} for index, o in enumerate(options)]}
        return {'stage': 'options', 'options': options,
                'evidence': {'comparison': self.save('evidence/comparison.json', comparison)}}

    def handoff(self):
        def transform(spec, design):
            _, intent_design = F.fixture()
            destination = design['destinations'][0]
            journey = design['journeys'][0]
            design['destinations'] = [dict(destination, id=i, surface='app', journey_id='inspect-record')
                                      for i in ('workspace', 'detail')]
            design['journeys'] = [dict(journey, **intent_design['journeys'][0])]
            design['experience_intent_handoff'] = dict(intent_design['experience_intent_handoff'],
                                                       context=F.E.context(spec))
            for row in design['experience_handoff']['quality_coverage']:
                row['destination_ids'] = ['workspace', 'detail']
        return G.selected_handoff(self.root, P, {'evidence': 'evidence/concept-two.json'}, transform=transform)

    def advance(self, flow):
        flow.through('brief')
        P.stage_record(self.root, self.options())
        binding = P.stage_status(self.root)['choice_bindings']['two']
        flow.host.grants[(P.canonical(binding), 'synthetic-choice')] = 'fixture-user'
        P.stage_record(self.root, {'stage': 'choice', 'option_id': 'two', 'receipt_ref': 'synthetic-choice'})
        path = self.handoff()
        P.stage_record(self.root, {'stage': 'design', 'resolved': True, 'evidence': {'design': path}})
        return path

    def fit(self, candidate, scope='product_owner', basis='source'):
        spec = self.current_spec()
        design = P.read_json(self.root / spec['selections'][0]['design_path'])[0]
        def row(ident):
            return {'id': ident, 'assessment': 'matched', 'candidate_locator': 'main / inspect-record / return',
                    'observation': 'Source declares selected identity and return state; rendered behavior unobserved.',
                    'evidence_paths': []}
        return {'schema_version': 1, 'kind': 'analyst_experience_fit', 'scope': scope, 'basis': basis,
                'reviewer': scope + '-reviewer', 'candidate_sha256': candidate['candidate_sha256'],
                'context': F.E.context(spec), 'requirements': [row('record-investigation')],
                'destinations': [row(d['id']) for d in design['destinations']],
                'journeys': [row(j['id']) for j in design['journeys']],
                'observations': [], 'rendered_quality': 'unobserved'}

    def test_new_init_requires_experience_discovery_without_restarting_abc(self):
        G.bootstrap(self.root, P, experience=True)
        flow = G.Lifecycle(self.root, P)
        flow.through('narrative')
        with self.assertRaisesRegex(ValueError, 'experience_intent_required'):
            flow.stage('brief')
        self.assertEqual(P.stage_status(self.root)['completed_stages'], ['access', 'analysis', 'narrative'])

    def test_full_contract_route_preserves_choice_and_all_four_reviews(self):
        flow = self.prepare()
        with P.trusted_stage_provider(flow.host):
            self.advance(flow)
            self.assertEqual(P.stage_status(self.root)['experience_intent']['status'], 'ready')
            (self.root / 'deliverables/app.html').write_text('<main id="workspace">Original source specimen</main>')
            W.freeze(self.root, {'id': 'one', 'builders': ['engineer'], 'artifacts': ['deliverables/app.html'],
                                'context': ['contracts/query.json']})
            candidate = P.stage_status(self.root)['candidate']
            for scope in flow.S.REVIEW_SCOPES:
                path = (self.save('evidence/fit-' + scope + '.json', self.fit(candidate, scope))
                        if scope in {'product_owner', 'ui_ux'} else flow.evidence(scope))
                P.stage_record(self.root, {'stage': 'review', 'scope': scope, 'reviewer': scope + '-reviewer',
                    'iteration_sha256': candidate['event_sha256'], 'candidate_sha256': candidate['candidate_sha256'],
                    'outcome': 'resolved', 'basis': 'source', 'evidence': {'review': path}})
            status = P.stage_status(self.root)
            self.assertEqual(len(status['reviews']), 4)
            self.assertTrue(status['release_ready'])
            # Source closure is neither rendered assurance nor native authority.
            (self.root / 'evidence/fit-product_owner.json').write_text('{}')
            self.assertFalse(P.stage_status(self.root)['release_ready'])

    def test_no_comparison_prose_or_self_review_and_no_early_code(self):
        flow = self.prepare()
        flow.through('brief')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')
        request = self.options()
        path = request['evidence']['comparison']
        review = P.read_json(self.root / path)[0]
        for change in ({'reviewer': 'fixture-experience'}, {'reviewer': 'unassigned-reviewer'}, {'assessment': 'revise'},
                       {'options': review['options'][:2]}):
            self.save(path, dict(review, **change))
            with self.subTest(change=next(iter(change))), self.assertRaises(ValueError):
                P.stage_record(self.root, request)
        self.save(path, review)
        self.assertEqual(P.stage_record(self.root, request)['next_stage'], 'choice')

    def test_mode_meaning_change_requires_new_options_not_only_same_id(self):
        flow = self.prepare()
        with P.trusted_stage_provider(flow.host):
            flow.through('brief')
            P.stage_record(self.root, self.options())
            spec = self.current_spec()
            mode = next(r for r in spec['requirements'] if r['id'] == 'workspace-hypothesis')
            mode['value']['mode'] = 'monitoring'
            self.save('contracts/design-intent.json', spec)
            self.assertEqual(P.stage_status(self.root)['next_stage'], 'options')
            with self.assertRaisesRegex(ValueError, 'mode_changed_reopen_options'):
                P.routing_helper('product_intent').validate_concept(self.root, 'evidence/concept-two.json', spec, P)

    def test_fit_covers_all_destinations_and_journeys_and_cannot_claim_render_from_source(self):
        flow = self.prepare()
        with P.trusted_stage_provider(flow.host):
            self.advance(flow)
        candidate = {'candidate_sha256': 'a' * 64, 'builders': ['engineer']}
        value = self.fit(candidate)
        path = self.save('evidence/fit.json', value)
        request = dict(scope='product_owner', reviewer=value['reviewer'], basis='source', outcome='resolved')
        self.assertTrue(R.fit(self.root, path, self.current_spec(), candidate, request, P))
        for change, message in [({'destinations': value['destinations'][:1]}, 'complete_destinations'),
                                ({'journeys': []}, 'complete_journeys'),
                                ({'requirements': []}, 'complete_requirements'),
                                ({'rendered_quality': 'recorded_observation'}, 'source_is_not_rendered'),
                                ({'candidate_sha256': 'b' * 64}, 'candidate_binding')]:
            self.save(path, dict(value, **change))
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                R.fit(self.root, path, self.current_spec(), candidate, request, P)

    def test_source_review_cannot_hide_unresolved_or_unobserved_fit(self):
        flow = self.prepare()
        with P.trusted_stage_provider(flow.host):
            self.advance(flow)
        candidate = {'candidate_sha256': 'a' * 64, 'builders': ['engineer']}
        value = self.fit(candidate)
        request = dict(scope='product_owner', reviewer=value['reviewer'], basis='source', outcome='resolved')
        for assessment in ('gap', 'unobserved'):
            value['journeys'][0]['assessment'] = assessment
            path = self.save('evidence/fit.json', value)
            with self.assertRaisesRegex(ValueError, 'experience_findings_unresolved'):
                R.fit(self.root, path, self.current_spec(), candidate, request, P)
        request['outcome'] = 'changes_requested'
        self.assertTrue(R.fit(self.root, path, self.current_spec(), candidate, request, P))

    def test_legacy_does_not_acquire_fabricated_experience_receipts(self):
        flow = G.Lifecycle(self.root, P)
        flow.through('brief')
        before = P.read_json(self.root / flow.S.JOURNAL)[0]
        status = P.stage_status(self.root)
        self.assertEqual(status['experience_intent']['status'], 'not_assessed')
        self.assertEqual(before, P.read_json(self.root / flow.S.JOURNAL)[0])


class ContractBoundaries(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        (self.root / 'contracts').mkdir()
        (self.root / 'evidence').mkdir()
        self.spec, design = F.fixture()
        self.spec['selections'] = [{'design_path': 'contracts/design.json'}]
        (self.root / 'contracts/design.json').write_text(json.dumps(design))

    def direction(self, ids):
        rows = {r['id']: r for r in self.spec['requirements']}
        return {'context': F.E.context(self.spec), 'mode_requirement_ids': ids,
                'modes': [{k: v for k, v in rows[i].items() if k != 'delivery'} for i in ids], 'authors': ['designer']}

    def test_conflicting_or_unresolved_concept_modes_fail_before_selection(self):
        mode = copy.deepcopy(self.spec['requirements'][-1])
        mode['id'] = 'another-mode'
        mode['value']['mode'] = 'narrative'
        self.spec['requirements'].append(mode)
        self.spec['product']['experience_intent']['mode_requirement_ids'].append(mode['id'])
        with self.assertRaisesRegex(ValueError, 'one_chosen_mode_per_surface'):
            P.routing_helper('product_intent').validate_experience_direction(
                {'surface': 'app', 'experience_direction': self.direction(['workspace-hypothesis', 'another-mode'])}, self.spec, P)
        mode['product']['basis'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'chosen_mode_meaning_unresolved'):
            P.routing_helper('product_intent').validate_experience_direction(
                {'surface': 'app', 'experience_direction': self.direction(['another-mode'])}, self.spec, P)

    def test_rendered_basis_cannot_resolve_unobserved_render_quality(self):
        value = {'schema_version': 1, 'kind': 'analyst_experience_fit', 'reviewer': 'reviewer',
                 'scope': 'ui_ux', 'basis': 'rendered', 'candidate_sha256': 'a' * 64,
                 'context': F.E.context(self.spec), 'requirements': [], 'destinations': [], 'journeys': [],
                 'observations': [], 'rendered_quality': 'unobserved'}
        path = self.root / 'evidence/fit.json'
        path.write_text(json.dumps(value))
        review = dict(scope='ui_ux', reviewer='reviewer', basis='rendered', outcome='resolved')
        with self.assertRaisesRegex(ValueError, 'resolved_rendered_review_requires_observation'):
            R.fit(self.root, 'evidence/fit.json', self.spec,
                  {'candidate_sha256': 'a' * 64, 'builders': ['engineer']}, review, P)

    def test_bounded_projection_retains_experience_and_omits_unrelated_requirements(self):
        self.spec['requirements'].append(F.requirement('unrelated', {'note': 'Separate optional scope'}, required=False))
        self.spec['requirements'][-1]['product']['suggested_roles'] = ['data-analyst']
        rows = P.intent_helper().project_requirements(self.spec['requirements'], 'app-engineer',
            ['record-investigation'], experience={'index': self.spec['product']['experience_intent']})
        self.assertEqual({r['id'] for r in rows}, {'record-investigation'})
        self.assertNotIn('unrelated', {r['id'] for r in rows})

    def test_fit_reuse_preserves_dependencies_and_current_builder_independence(self):
        I = P.routing_helper('incremental_review')
        deps = [{'id': kind, 'kind': kind, 'scopes': sorted(I.SCOPES), 'path': 'evidence/' + kind,
                 'sha256': 'a' * 64, 'bytes': 1, 'freshness': {'mode': 'immutable',
                 'checked_at': '2020-01-01T00:00:00+00:00', 'expires_at': None}} for kind in I.REQUIRED_KINDS]
        now = {'sha256': 'b' * 64, 'payload': {'review_dependencies': deps, 'builders': ['engineer']}}
        old = {'sha256': 'c' * 64, 'payload': copy.deepcopy(now['payload'])}
        prior = {scope: {'sha256': str(index) * 64, 'payload': {'reviewer': scope + '-reviewer',
                 'basis': 'source', 'outcome': 'resolved', 'evidence': {}}} for index, scope in enumerate(sorted(I.SCOPES))}
        pin = {'path': 'evidence/fit.json', 'sha256': 'f' * 64, 'bytes': 4}
        prior['product_owner']['payload']['experience_dependencies'] = [pin]
        state = {'candidate': now, 'previous_candidate': old, 'previous_reviews': prior,
                 'incremental_policies': [{'payload': {'mode': 'enforce'}}]}
        self.assertTrue(I.impact_state(state)['scopes']['product_owner']['eligible'])
        request = {'scope': 'product_owner', 'source_review_sha256': prior['product_owner']['sha256']}
        carried = I.carry_payload(state, request)
        self.assertEqual(carried['experience_dependencies'], [pin])
        I.validate_carry(state, carried, datetime.now(timezone.utc))
        carried['experience_dependencies'] = []
        with self.assertRaisesRegex(ValueError, 'original_review_changed'):
            I.validate_carry(state, carried, datetime.now(timezone.utc))
        now['payload']['builders'] = ['product_owner-reviewer']
        self.assertIn('reviewer_is_current_builder', I.impact_state(state)['scopes']['product_owner']['reasons'])


if __name__ == '__main__':
    unittest.main()
