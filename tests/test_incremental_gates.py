"""Original synthetic opt-in continuity fixtures; no production acceptance claims."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('incremental_gate_fixture', ROOT / 'tests/test_stage_gates.py')
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
S, P = F.S, F.P
I = P.routing_helper('incremental_review')


class IncrementalGateTests(unittest.TestCase):
    def setUp(self):
        self.f = F.StageGateTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.checked = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.expiry = self.checked + timedelta(hours=1)
        for kind in I.REQUIRED_KINDS:
            self.f.write('evidence/fixed-' + kind + '.txt', 'Synthetic immutable ' + kind + ' receipt')

    def adopt(self, mode='enforce'):
        path = 'evidence/incremental-' + mode + '.txt'
        self.f.write(path, 'Synthetic explicit opt-in: ' + mode + '; no external authority')
        return I.adopt(self.root, {'mode': mode, 'expected_tail_sha256': self.f.inspect()['tail_sha256'],
            'evidence': {'policy_decision': path}}, P=P, provider=self.f.host)

    def freeze(self, ident, *, css='body { color: black; }', builders=None, missing=None, changed=None,
               expires=None, unknown=False):
        rows = []
        paths = []
        for name, content, scopes in (
                ('core', '<main>Same selected numerical product</main>', sorted(I.SCOPES)),
                ('css', css, ['qa', 'security', 'ui_ux'])):
            path = 'evidence/' + ident + '-' + name + '.txt'
            paths.append(path)
            self.f.write(path, content)
            rows.append({'id': name, 'kind': 'artifact', 'scopes': scopes, 'path': path,
                         'freshness': {'mode': 'immutable', 'checked_at': self.checked.isoformat(), 'expires_at': None}})
        for kind in sorted(I.REQUIRED_KINDS - ({missing} if missing else set())):
            path = 'evidence/fixed-' + kind + '.txt'
            if kind == changed:
                path = 'evidence/' + ident + '-' + kind + '.txt'
                self.f.write(path, 'Changed synthetic ' + kind)
            rows.append({'id': kind, 'kind': 'unknown' if unknown and kind == 'context' else kind,
                         'scopes': sorted(I.SCOPES), 'path': path,
                         'freshness': {'mode': 'until', 'checked_at': self.checked.isoformat(),
                                       'expires_at': (expires or self.expiry).isoformat()}})
        manifest = I.manifest_template(self.root, {'dependencies': rows}, P=P)
        path = 'evidence/' + ident + '-manifest.json'
        self.f.write(path, manifest)
        return self.f.record({'stage': 'candidate', 'iteration_id': ident, 'builders': builders or ['builder-worker'],
                              'artifacts': paths, 'review_manifest': path})

    def baseline(self, mode='enforce', outcome='resolved'):
        self.adopt(mode)
        self.f.through()
        self.freeze('one')
        self.f.reviews(outcome)

    def carry_request(self, scope):
        status = self.f.inspect()
        return {'scope': scope, 'source_review_sha256': status['incremental_review']['scopes'][scope]['source_review_sha256'],
                'iteration_sha256': status['candidate']['event_sha256'],
                'candidate_sha256': status['candidate_sha256'], 'expected_tail_sha256': status['tail_sha256'],
                'assessed_by': 'synthetic-impact-reviewer'}

    def carry(self, scope):
        return I.carry_forward(self.root, self.carry_request(scope), P=P, provider=self.f.host)

    def test_policy_is_opt_in_observation_does_not_skip_reviews(self):
        self.assertIsNone(self.f.inspect()['incremental_review']['policy'])
        self.baseline('observe')
        self.freeze('two')
        status = self.f.inspect()
        self.assertEqual(status['reviews'], {})
        self.assertEqual(status['incremental_review']['scopes']['qa']['action'], 'observe_reuse')
        with self.assertRaisesRegex(ValueError, 'enforcement_not_adopted'):
            self.carry('qa')

    def test_adoption_appends_and_is_idempotent(self):
        first = self.adopt('observe')
        retained = copy.deepcopy(self.f.journal()['events'])
        self.adopt('enforce')
        self.assertEqual(self.f.journal()['events'][:len(retained)], retained)
        event = self.f.journal()['events'][-1]
        request = {k: v for k, v in event['payload'].items() if k != 'request_sha256'}
        request['evidence'] = {k: v['path'] for k, v in request['evidence'].items()}
        self.assertTrue(I.adopt(self.root, request, P=P, provider=self.f.host)['recorded']['reused'])
        self.assertEqual(len(self.f.journal()['events']), 2)
        self.assertEqual(first['incremental_review']['mode'], 'observe')

    def test_modular_css_change_carries_product_coverage_without_relabeling_origin(self):
        self.baseline()
        old = self.f.inspect()
        old_review = old['reviews']['product_owner']
        self.freeze('two', css='body { color: navy; }')
        status = self.f.inspect()
        self.assertNotEqual(old['candidate_sha256'], status['candidate_sha256'])
        self.assertTrue(status['incremental_review']['scopes']['product_owner']['eligible'])
        for scope in ('ui_ux', 'qa', 'security'):
            self.assertFalse(status['incremental_review']['scopes'][scope]['eligible'])
        new = self.carry('product_owner')['reviews']['product_owner']
        self.assertEqual(new['origin_review_sha256'], old_review['event_sha256'])
        self.assertEqual(new['evidence'], old_review['evidence'])
        self.assertEqual(new['basis'], 'source')
        self.assertEqual(new['outcome'], old_review['outcome'])
        self.assertNotEqual(new['iteration_sha256'], old_review['iteration_sha256'])
        self.assertFalse(self.f.inspect()['release_ready'])

    def test_unobserved_and_findings_remain_unresolved_across_multiple_carries(self):
        self.baseline(outcome='unobserved')
        origin = self.f.inspect()['reviews']['qa']['event_sha256']
        self.freeze('two')
        for scope in I.SCOPES:
            self.carry(scope)
        self.assertFalse(self.f.inspect()['release_ready'])
        self.freeze('three')
        new = self.carry('qa')['reviews']['qa']
        self.assertEqual(new['origin_review_sha256'], origin)
        self.assertEqual(new['outcome'], 'unobserved')
        self.assertFalse(self.f.inspect()['review_assurance']['native_acceptance'])

    def test_changed_data_dependency_and_unknown_map_require_all_scopes(self):
        self.baseline()
        self.freeze('two', changed='data')
        self.assertTrue(all(not r['eligible'] for r in self.f.inspect()['incremental_review']['scopes'].values()))
        with self.assertRaisesRegex(ValueError, 'fresh_review_required'):
            self.carry('product_owner')
        self.f.reviews()
        self.freeze('three', unknown=True)
        self.assertTrue(all(not r['eligible'] for r in self.f.inspect()['incremental_review']['scopes'].values()))

    def test_missing_safety_context_is_unknown_and_changed_pin_rejected(self):
        self.baseline()
        self.freeze('two', missing='access')
        self.assertTrue(all('mandatory_safety_context_missing' in r['reasons'] for r in
                            self.f.inspect()['incremental_review']['scopes'].values()))
        self.f.reviews()
        original = I.manifest_template
        def changed_pin(root, request, **kwargs):
            result = original(root, request, **kwargs)
            result['dependencies'][0]['sha256'] = '0' * 64
            return result
        with patch.object(I, 'manifest_template', side_effect=changed_pin):
            with self.assertRaisesRegex(ValueError, 'dependency_changed'):
                self.freeze('three')

    def test_reviewer_becomes_builder_cannot_carry_independent_lane(self):
        self.baseline()
        self.freeze('two', builders=['qa-worker'])
        row = self.f.inspect()['incremental_review']['scopes']['qa']
        self.assertIn('reviewer_is_current_builder', row['reasons'])
        with self.assertRaisesRegex(ValueError, 'fresh_review_required'):
            self.carry('qa')

    def test_stale_tail_and_candidate_race_reject_and_same_request_is_idempotent(self):
        self.baseline()
        self.freeze('two')
        request = self.carry_request('qa')
        self.carry('security')
        with self.assertRaisesRegex(ValueError, 'tail_mismatch'):
            I.carry_forward(self.root, request, P=P, provider=self.f.host)
        request = self.carry_request('qa')
        first = I.carry_forward(self.root, request, P=P, provider=self.f.host)
        second = I.carry_forward(self.root, request, P=P, provider=self.f.host)
        self.assertEqual(first['recorded']['sha256'], second['recorded']['sha256'])
        self.assertTrue(second['recorded']['reused'])
        self.carry('ui_ux'); self.carry('product_owner')
        self.freeze('three')
        with self.assertRaisesRegex(ValueError, 'candidate_mismatch'):
            I.carry_forward(self.root, request, P=P, provider=self.f.host)

    def test_dependency_changed_during_commit_preserves_journal(self):
        self.baseline()
        self.freeze('two')
        request = self.carry_request('qa')
        before = (self.root / S.JOURNAL).read_bytes()
        original = S._report
        calls = 0
        def race(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.f.write('evidence/fixed-access.txt', 'Changed during commit')
            return original(*args, **kwargs)
        with patch.object(S, '_report', side_effect=race):
            with self.assertRaisesRegex(ValueError, 'evidence_changed_during_record'):
                self.f.record({'stage': 'review_carry_forward', **request})
        self.assertEqual((self.root / S.JOURNAL).read_bytes(), before)

    def test_expired_evidence_blocks_carry_without_corrupting_history(self):
        self.baseline()
        self.freeze('two', expires=datetime.now(timezone.utc) - timedelta(seconds=1))
        self.assertNotEqual(self.f.inspect()['status'], 'invalid')
        with self.assertRaisesRegex(ValueError, 'fresh_review_required'):
            self.carry('product_owner')
        self.assertFalse(self.f.inspect()['release_ready'])

    def test_owner_change_preserves_choice_but_live_independence_is_rechecked(self):
        self.adopt()
        self.f.through()
        before = self.f.inspect()['stage_bindings']['choice']
        execution_path = self.root / 'contracts/execution.json'
        execution = json.loads(execution_path.read_text())
        execution['responsibilities']['creative_review']['worker'] = 'new-independent-creative-owner'
        execution['specialists'] = {'motion-owner': {'role': 'motion-designer', 'worker': 'motion-worker',
            'mode': 'delegated', 'rationale': 'Synthetic optional staffing', 'requirement_ids': []}}
        execution_path.write_text(json.dumps(execution))
        status = self.f.inspect()
        self.assertEqual(status['stage_bindings']['choice'], before)
        self.assertEqual(status['next_stage'], 'candidate')
        execution['responsibilities']['creative_review']['worker'] = execution['responsibilities']['experience']['worker']
        execution_path.write_text(json.dumps(execution))
        self.assertNotIn('choice', self.f.inspect()['completed_stages'])


if __name__ == '__main__':
    unittest.main()
