"""Original isolated fixtures; a test provider is not a qualified production host."""
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'stage_gates_under_test', ROOT / 'skills/omni-artifact-accelerator/scripts/stage_gates.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
P = S._helpers(None)


class FixtureHost:
    """Only a synthetic grant store for tests, deliberately outside production code."""
    def __init__(self):
        self.grants = {}

    def verify_choice(self, binding, receipt_ref):
        return self.grants.get((P.canonical(binding), receipt_ref))

    def fixture_user_selection(self, binding, receipt_ref='host-event-one'):
        self.grants[(P.canonical(binding), receipt_ref)] = 'fixture-user'
        return receipt_ref


class StageGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Original garden study', 'net-new', 'app', 'none')
        self.host = FixtureHost()
        names = {key for keys in S.EVIDENCE.values() for key in keys}
        for name in names:
            self.write('evidence/' + name + '.txt', 'Original fixture evidence: ' + name)
        for number in range(3):
            self.write('evidence/option-' + str(number) + '.txt', 'Different garden concept ' + str(number))
        self.requests = {
            'access': {'source_scope': 'Fixture garden observations only', 'user_identity': 'fixture-user'},
            'analysis': {'analyst': 'analyst-worker', 'bi_engineer': 'bi-worker'},
            'narrative': {'storyteller': 'story-worker', 'analyst': 'analyst-worker'},
            'brief': {},
            'options': {'options': [{'id': 'o' + str(i), 'thesis': 'Distinct garden thesis ' + str(i),
                                     'evidence': 'evidence/option-' + str(i) + '.txt'} for i in range(3)]},
            'design': {'resolved': True},
        }
        for stage, body in self.requests.items():
            body.update(stage=stage, evidence={k: 'evidence/' + k + '.txt' for k in S.EVIDENCE[stage]})

    def write(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) if type(value) is dict else value)

    def inspect(self, host=True):
        return S.inspect(self.root, P=P, provider=self.host if host else None)

    def record(self, request, host=True):
        return S.record(self.root, request, P=P, provider=self.host if host else None)

    def through(self, end='design'):
        for stage in S.STAGES:
            if stage == 'choice':
                binding = self.inspect()['choice_bindings']['o1']
                receipt = self.host.fixture_user_selection(binding)
                self.record({'stage': 'choice', 'option_id': 'o1', 'receipt_ref': receipt})
            else:
                self.record(self.requests[stage])
            if stage == end:
                break

    def candidate(self, ident='one', multiple=False):
        path = 'evidence/candidate-' + ident + '.html'
        self.write(path, '<main>Garden candidate ' + ident + '</main>')
        body = {'stage': 'candidate', 'iteration_id': ident, 'builders': ['builder-worker']}
        if multiple:
            data = 'evidence/data-' + ident + '.json'
            self.write(data, {'garden': ident})
            body['artifacts'] = [path, data]
        else:
            body['artifact'] = path
        return self.record(body)

    def reviews(self, outcome='resolved'):
        for scope in S.REVIEW_SCOPES:
            path = 'evidence/review-' + scope + '-' + str(len(self.journal()['events'])) + '.txt'
            self.write(path, scope + ' original fixture assessment: ' + outcome)
            self.record({'stage': 'review', 'scope': scope, 'reviewer': scope + '-worker',
                         'outcome': outcome, 'basis': 'source', 'evidence': {'review': path},
                         **self.review_target()})

    def review_target(self):
        candidate = self.inspect()['candidate']
        return {'iteration_sha256': candidate['event_sha256'],
                'candidate_sha256': candidate['candidate_sha256']}

    def journal(self):
        return json.loads((self.root / S.JOURNAL).read_text())

    def select_actual_intent(self, version):
        spec = P.intent_helper().starter(['app'], 'none')
        spec['product'] = {'schema_version': 1, 'scope': 'new_experience', 'discovery': 'sufficient',
                           'note_paths': ['inputs/notes.json']}
        self.write('inputs/notes.json', {'text': 'Original synthetic request'})
        path = 'contracts/spec-' + version + '.json'
        self.write(path, spec)
        P.intent_helper().select(self.root, self.root / path, 'contracts/selection-' + version + '.json')
        return P.load_project(self.root)[1]['design_intent']

    def test_sequence_requires_all_predecessors_and_never_accepts_future_fields(self):
        self.assertEqual(self.inspect()['next_stage'], 'access')
        self.assertTrue(self.inspect()['required'])
        for stage in ('analysis', 'narrative', 'brief', 'options', 'design'):
            with self.assertRaises(ValueError):
                self.record(self.requests[stage])
        invalid = dict(self.requests['access'], approved=True)
        with self.assertRaises(ValueError):
            self.record(invalid)
        self.assertFalse((self.root / S.JOURNAL).exists())
        self.through('narrative')
        result = self.inspect()
        self.assertEqual(result['next_stage'], 'brief')
        self.assertEqual(set(result['stage_bindings']), {'access', 'analysis', 'narrative'})

    def test_complete_source_lifecycle_preserves_assurance_limits(self):
        self.through()
        S.require_action(self.root, 'build', P=P, provider=self.host)
        first = self.candidate(multiple=True)
        self.assertEqual(first['candidate_sha256'], first['candidate']['candidate_sha256'])
        self.assertEqual(len(first['candidate']['artifacts']), 2)
        self.reviews()
        ready = S.require_action(self.root, 'release', P=P, provider=self.host)
        self.assertEqual(ready['status'], 'ready_for_release')
        self.assertTrue(ready['release_ready'])
        self.assertFalse(ready['claims_authenticated'])
        self.assertFalse(ready['external_mutations_authorized'])
        self.assertTrue(all(v['basis'] == 'source' and v['candidate_sha256'] == first['candidate_sha256']
                            for v in ready['reviews'].values()))
        self.assertEqual((self.root / S.JOURNAL).stat().st_mode & 0o777, 0o600)

    def test_no_provider_boolean_receipt_or_self_report_can_authorize_choice(self):
        self.through('options')
        request = {'stage': 'choice', 'option_id': 'o1', 'receipt_ref': 'arbitrary-file-or-claim'}
        for host in (True, False):
            with self.assertRaises(ValueError):
                self.record(request, host=host)
        with self.assertRaises(ValueError):
            self.record(dict(request, user_approved=True))
        class BooleanProvider:
            def verify_choice(self, binding, receipt_ref):
                return True
        with self.assertRaises(ValueError):
            S.record(self.root, request, P=P, provider=BooleanProvider())
        self.assertEqual(self.inspect()['next_stage'], 'choice')
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'build', P=P)

    def test_choice_is_reverified_against_exact_option_collection_and_subject(self):
        self.through()
        self.assertEqual(self.inspect(host=False)['next_stage'], 'choice')
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'build', P=P)
        self.host.grants.clear()
        self.assertIn('trusted_choice_unverified', self.inspect()['findings'])
        with self.assertRaises(ValueError):
            self.candidate()

    def test_option_revision_invalidates_choice_and_old_receipt(self):
        self.through()
        old = self.inspect()['choice_bindings']['o1']
        self.write('evidence/option-2.txt', 'Revised third feasible concept')
        self.assertEqual(self.inspect()['next_stage'], 'options')
        self.record(self.requests['options'])
        current = self.inspect()
        self.assertEqual(current['next_stage'], 'choice')
        self.assertNotEqual(old, current['choice_bindings']['o1'])
        with self.assertRaises(ValueError):
            self.record({'stage': 'choice', 'option_id': 'o1', 'receipt_ref': 'host-event-one'})
        self.assertNotIn('design', current['completed_stages'])

    def test_three_options_need_distinct_ids_theses_and_evidence_bytes(self):
        self.through('brief')
        for variant in ('count', 'id', 'thesis', 'bytes'):
            request = copy.deepcopy(self.requests['options'])
            if variant == 'count':
                request['options'].pop()
            elif variant in {'id', 'thesis'}:
                request['options'][2][variant] = request['options'][0][variant]
            else:
                request['options'][2]['evidence'] = request['options'][0]['evidence']
            with self.assertRaises(ValueError):
                self.record(request)
        self.assertEqual(self.inspect()['next_stage'], 'options')

    def test_stale_upstream_blocks_advancement_and_repair_invalidates_downstream(self):
        self.through('narrative')
        self.write('evidence/data.txt', 'Changed source observation')
        with self.assertRaises(ValueError):
            self.record(self.requests['brief'])
        self.assertEqual(self.inspect()['next_stage'], 'access')
        self.record(self.requests['access'])
        self.assertEqual(self.inspect()['completed_stages'], ['access'])
        self.assertEqual(self.inspect()['next_stage'], 'analysis')

    def test_iteration_requires_four_reviews_and_qa_ui_independence(self):
        self.through()
        self.candidate()
        with self.assertRaises(ValueError):
            self.candidate('two')
        with self.assertRaises(ValueError):
            self.record(self.requests['access'])  # upstream reset cannot skip pending reviews
        for scope in ('qa', 'ui_ux'):
            with self.assertRaisesRegex(ValueError, 'independent_reviewer_required'):
                self.record({'stage': 'review', 'scope': scope, 'reviewer': 'builder-worker',
                             'outcome': 'resolved', 'evidence': {'review': 'evidence/review.txt'},
                             **self.review_target()})
        self.reviews('changes_requested')
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'release', P=P, provider=self.host)
        old = self.inspect()['candidate']['event_sha256']
        second = self.candidate('two')
        self.assertEqual(second['candidate']['prior_iteration_sha256'], old)
        self.assertEqual(second['reviews'], {})
        self.assertFalse(second['release_ready'])
        self.reviews()
        with self.assertRaises(ValueError):
            self.candidate('two')  # unique identity required even after all reviews

    def test_review_request_cannot_be_replayed_or_restamped_for_new_candidate(self):
        self.through()
        self.candidate()
        request = {'stage': 'review', 'scope': 'qa', 'reviewer': 'qa-worker',
                   'outcome': 'resolved', 'basis': 'source',
                   'evidence': {'review': 'evidence/review.txt'}, **self.review_target()}
        self.record(request)
        self.reviews()
        self.candidate('two')
        prior = (self.root / S.JOURNAL).read_bytes()
        with self.assertRaisesRegex(ValueError, 'review_candidate_mismatch'):
            self.record(request)
        current = dict(request, **self.review_target())
        for key in ('iteration_sha256', 'candidate_sha256'):
            with self.assertRaisesRegex(ValueError, 'review_candidate_mismatch'):
                self.record(dict(current, **{key: '0' * 64}))
            missing = dict(current)
            del missing[key]
            with self.assertRaises(ValueError):
                self.record(missing)
        self.assertEqual((self.root / S.JOURNAL).read_bytes(), prior)
        self.assertEqual(self.inspect()['reviews'], {})
        self.record(current)
        self.assertEqual(self.inspect()['reviews']['qa']['candidate_sha256'], current['candidate_sha256'])

    def test_unobserved_consultation_gap_allows_correction_never_release(self):
        self.through()
        self.candidate()
        self.reviews('unobserved')
        self.assertFalse(self.inspect()['release_ready'])
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'release', P=P, provider=self.host)
        self.candidate('two')

    def test_candidate_or_review_edit_invalidates_release_and_correction(self):
        self.through()
        candidate = self.candidate(multiple=True)
        self.reviews()
        self.write(candidate['candidate']['artifacts'][1]['path'], 'Changed second artifact')
        self.assertIn('stale_iteration_evidence', self.inspect()['findings'])
        for action in ('release', 'build'):
            with self.assertRaises(ValueError):
                S.require_action(self.root, action, P=P, provider=self.host)

    def test_previous_review_pins_are_checked_after_upstream_revision(self):
        self.through()
        self.candidate()
        self.reviews()
        review_path = self.inspect()['reviews']['qa']['evidence']['review']['path']
        self.record(self.requests['design'])
        self.write(review_path, 'Changed review after recorded revision')
        with self.assertRaises(ValueError):
            self.candidate('two')
        self.assertIn('stale_iteration_evidence', self.inspect()['findings'])

    def test_review_supporting_prior_iteration_remains_a_current_dependency(self):
        self.through()
        self.candidate()
        self.reviews()
        old_review = self.inspect()['reviews']['qa']['evidence']['review']['path']
        self.candidate('two')
        self.reviews()
        self.assertTrue(self.inspect()['release_ready'])
        self.write(old_review, 'Changed earlier correction evidence')
        self.assertFalse(self.inspect()['release_ready'])
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'release', P=P, provider=self.host)

    def test_no_opt_out_unknown_policy_invalid_state_and_actual_legacy(self):
        project = P.load_project(self.root)[1]
        project.update(mode='enhancement', stage_gate_policy=S.POLICY)
        self.write('project.json', project)
        self.assertTrue(self.inspect()['required'])
        project['stage_gate_policy'] = 'off'
        self.write('project.json', project)
        self.assertEqual(self.inspect()['status'], 'invalid')
        # Deliberately reconstruct a pre-policy legacy fixture. New init calls in
        # every mode retain the policy; production exposes no opt-out operation.
        del project['stage_gate_policy']
        self.write('project.json', project)
        report = S.require_action(self.root, 'build', P=P)
        self.assertEqual(report['status'], 'not_applicable')
        self.assertFalse(report['release_ready'])
        project['mode'] = 'net-new'
        self.write('project.json', project)
        self.record(self.requests['access'])
        project['mode'] = 'enhancement'
        self.write('project.json', project)
        self.assertTrue(self.inspect()['required'])

    def test_real_selected_product_pointer_works_and_is_pinned(self):
        self.through()
        spec = P.intent_helper().starter(['app'], 'none')
        spec['product'] = {'schema_version': 1, 'scope': 'new_experience', 'discovery': 'sufficient',
                           'note_paths': ['inputs/notes.json']}
        self.write('inputs/notes.json', {'text': 'Original synthetic request'})
        self.write('contracts/selected-spec.json', spec)
        P.intent_helper().select(self.root, self.root / 'contracts/selected-spec.json', 'contracts/selection.json')
        pointer = P.load_project(self.root)[1]['design_intent']
        self.assertEqual(set(pointer), {'path', 'sha256', 'bytes'})
        self.assertNotEqual(self.inspect()['status'], 'invalid')
        self.write(pointer['path'], '{}')
        self.assertEqual(self.inspect()['status'], 'invalid')

    def test_design_pins_actual_selected_intent_and_reselection_requires_checkpoint(self):
        self.through('choice')
        first = self.select_actual_intent('one')
        self.record(self.requests['design'])
        self.assertEqual(self.journal()['events'][-1]['payload']['selected_intent'], first)
        S.require_action(self.root, 'build', P=P, provider=self.host)
        second = self.select_actual_intent('two')
        self.assertNotEqual(first, second)
        self.assertIn('selected_intent_changed', self.inspect()['findings'])
        self.assertEqual(self.inspect()['next_stage'], 'design')
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'build', P=P, provider=self.host)
        self.record(self.requests['design'])
        self.assertEqual(self.journal()['events'][-1]['payload']['selected_intent'], second)
        S.require_action(self.root, 'build', P=P, provider=self.host)
        self.candidate()
        self.select_actual_intent('three')
        with self.assertRaisesRegex(ValueError, 'iteration_reviews_required'):
            self.record(self.requests['design'])
        with self.assertRaises(ValueError):
            self.candidate('two')

    def test_standalone_null_design_pin_cannot_ignore_later_selection_or_be_supplied(self):
        self.through('choice')
        with self.assertRaises(ValueError):
            self.record(dict(self.requests['design'], selected_intent=None))
        self.record(self.requests['design'])
        self.assertIsNone(self.journal()['events'][-1]['payload']['selected_intent'])
        self.select_actual_intent('later')
        with self.assertRaises(ValueError):
            S.require_action(self.root, 'build', P=P, provider=self.host)
        self.record(self.requests['design'])
        S.require_action(self.root, 'build', P=P, provider=self.host)

    def test_selected_design_brand_and_original_spec_dependencies_must_remain_current(self):
        self.through('choice')
        spec = P.intent_helper().starter(['app'], 'requested')
        spec['selections'][0].update(design_path='contracts/chosen-design.json',
                                     brand_path='contracts/chosen-brand.json')
        self.write('contracts/chosen-design.json', {'brand_contract': 'contracts/chosen-brand.json',
                                                   'task': 'Inspect original garden observations'})
        self.write('contracts/chosen-brand.json', {'palette': ['green', 'white']})
        self.write('contracts/selected-spec.json', spec)
        P.intent_helper().select(self.root, self.root / 'contracts/selected-spec.json', 'contracts/selection.json')
        selected_bytes = (self.root / 'contracts/selection.json').read_bytes()
        # Unresolved product decisions are distinct from dependency integrity.
        self.assertTrue(P.intent_helper().check(self.root)['open_questions'])
        self.record(self.requests['design'])
        S.require_action(self.root, 'build', P=P, provider=self.host)
        for path in ('contracts/chosen-design.json', 'contracts/chosen-brand.json', 'contracts/selected-spec.json'):
            original = (self.root / path).read_bytes()
            self.write(path, {'changed': 'The selected record itself is still unchanged'})
            self.assertEqual((self.root / 'contracts/selection.json').read_bytes(), selected_bytes)
            self.assertEqual(P.intent_helper().check(self.root)['status'], 'inconsistent')
            with self.assertRaises(ValueError):
                S.require_action(self.root, 'build', P=P, provider=self.host)
            with self.assertRaisesRegex(ValueError, 'selected_dependency_changed'):
                self.record(self.requests['design'])
            (self.root / path).write_bytes(original)
            S.require_action(self.root, 'build', P=P, provider=self.host)

    def test_paths_symlinks_special_files_and_package_tree_are_rejected(self):
        outside = Path(self.temp.name).resolve() / 'outside.txt'
        outside.write_text('outside fixture')
        (self.root / 'evidence/link.txt').symlink_to(outside)
        os.mkfifo(self.root / 'evidence/pipe')
        for bad in ('../outside.txt', str(outside), 'evidence/link.txt', 'evidence/pipe'):
            request = copy.deepcopy(self.requests['access'])
            request['evidence']['data'] = bad
            with self.assertRaises((ValueError, OSError)):
                self.record(request)
        alias = Path(self.temp.name).resolve() / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(S.inspect(alias, P=P)['status'], 'invalid')
        self.assertEqual(S.inspect(ROOT, P=P)['status'], 'invalid')

    def test_atomic_failure_and_lock_contention_preserve_previous_checkpoint(self):
        self.record(self.requests['access'])
        original = (self.root / S.JOURNAL).read_bytes()
        with patch.object(S.os, 'replace', side_effect=OSError('fixture interruption')):
            with self.assertRaises(OSError):
                self.record(self.requests['analysis'])
        self.assertEqual((self.root / S.JOURNAL).read_bytes(), original)
        self.assertEqual(list(self.root.glob('.stage-gates-*')), [])
        with (self.root / S.LOCK).open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'stage_gate_busy'):
                self.record(self.requests['analysis'])
        self.assertEqual((self.root / S.JOURNAL).read_bytes(), original)

    def test_malformed_or_rehashed_skipped_journal_never_becomes_ready(self):
        self.through('analysis')
        journal = self.journal()
        event = journal['events'][1]
        event['predecessor_sha256'] = '0' * 64
        event['sha256'] = P.digest(P.canonical({k: v for k, v in event.items() if k != 'sha256'}))
        self.write(S.JOURNAL, journal)
        self.assertEqual(self.inspect()['status'], 'invalid')
        with self.assertRaises(ValueError):
            self.record(self.requests['access'])
        for bad in ('{"events":[],"events":[]}', '{"value":NaN}', '[]'):
            self.write(S.JOURNAL, bad)
            self.assertEqual(self.inspect()['status'], 'invalid')


if __name__ == '__main__':
    unittest.main()
