"""Offline Domo Pro-code control preservation and redesign scenarios."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts'
loader = importlib.util.spec_from_file_location('fidelity', SCRIPTS / 'migration_fidelity.py')
M = importlib.util.module_from_spec(loader)
loader.loader.exec_module(M)


class MigrationFidelity(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.source_file = 'source.js'
        self.target_file = 'native-observations.txt'
        (self.root / self.source_file).write_text('Original synthetic Domo dealer/date view')
        (self.root / self.target_file).write_text('Synthetic target result transcript')
        self.candidate = 'a' * 64
        view = {'id': 'sales', 'title': 'Dealer sales', 'layout': 'Selectors above sales and all-dealer total',
                'components': ['sales', 'all_dealers'], 'controls': ['dealer', 'date'], 'evidence': [self.source_file]}
        self.source = {
            'schema_version': 1, 'source_evidence': [self.source_file], 'views': [view], 'deviations': [],
            'controls': [self.control('dealer', 'choice', 'all', ['sales'], ['all_dealers']),
                         self.control('date', 'date_range', 'year', ['sales', 'all_dealers'], [])],
            'cases': [
                self.case('initial', ['dealer', 'date'], 'all', 'year', 120, 120),
                self.case('dealer_only', ['dealer'], 'north', 'year', 35, 120),
                self.case('date_only', ['date'], 'all', 'month', 20, 20),
                self.case('combined', ['dealer', 'date'], 'north', 'month', 6, 20),
                self.case('reset', ['dealer', 'date'], 'all', 'year', 120, 120)]}
        self.prepare()

    def control(self, key, kind, default, affected, exempt):
        return {'id': key, 'label': key.title(), 'kind': kind, 'default': default, 'affected': affected,
                'exempt': exempt, 'evidence': [self.source_file]}

    def case(self, key, controls, dealer, date, sales, all_dealers):
        return {'id': key, 'controls': controls, 'action': key.replace('_', ' '), 'persona': 'sales_viewer',
                'state': {'dealer': dealer, 'date': date}, 'outputs': {'sales': sales, 'all_dealers': all_dealers},
                'evidence': [self.source_file]}

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def prepare(self):
        self.write('base.json', self.source)
        self.base = M.baseline(self.root, 'base.json')
        self.target = {'schema_version': 1, 'baseline_sha256': self.base['baseline_sha256'],
                       'candidate_sha256': self.candidate, 'controls': [
                           {'id': row['id'], 'target_locator': 'omni:' + row['id'], 'evidence': [self.target_file]}
                           for row in self.source['controls']], 'cases': [
                           {**{k: copy.deepcopy(row[k]) for k in ('id', 'persona', 'state', 'outputs')},
                            'evidence': [self.target_file]} for row in self.source['cases']]}

    def compare(self):
        self.write('observed.json', self.target)
        return M.parity(self.root, 'base.json', 'observed.json', self.candidate)

    def test_controls_defaults_combined_and_reset_match(self):
        result = self.compare()
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(len(result['cases']), 5)
        self.assertFalse(result['native_verified'])
        self.assertEqual(self.base['baseline_sha256'], M.baseline(self.root, 'base.json')['baseline_sha256'])

    def test_dropped_control_and_case_remain_partial_despite_identical_default(self):
        self.target['controls'].pop(1)
        self.target['cases'].pop(3)
        result = self.compare()
        self.assertEqual(result['status'], 'partial')
        self.assertCountEqual(result['findings'], [{'kind': 'missing_control', 'id': 'date'},
                                                  {'kind': 'missing_case', 'id': 'combined'}])

    def test_wrong_exempt_result_and_context_are_reported(self):
        self.target['cases'][1]['outputs']['all_dealers'] = 35
        self.target['cases'][3]['persona'] = 'other_viewer'
        self.target['cases'][3]['state']['dealer'] = 'another_dealer'
        self.assertEqual(self.compare()['findings'], [
            {'kind': 'case_mismatch', 'id': 'dealer_only', 'fields': ['outputs']},
            {'kind': 'case_mismatch', 'id': 'combined', 'fields': ['persona', 'state']}])

    def test_source_or_candidate_drift_invalidates_prior_observations(self):
        self.target['candidate_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'stale_candidate'):
            self.compare()
        self.target['candidate_sha256'] = self.candidate
        (self.root / self.source_file).write_text('Changed Domo asset version')
        self.assertNotEqual(self.base['baseline_sha256'], M.baseline(self.root, 'base.json')['baseline_sha256'])
        with self.assertRaisesRegex(ValueError, 'stale_source'):
            self.compare()

    def test_redesign_can_adapt_presentation_but_must_preserve_dealer_and_date(self):
        (self.root / 'decision.txt').write_text('Use a searchable dealer picker; keep the analytical scope')
        self.source['deviations'] = [{'control_id': 'dealer', 'disposition': 'adapt', 'reason': 'Searchable picker',
                                     'decision_evidence': ['decision.txt']}]
        self.prepare()
        self.target['controls'][0]['target_locator'] = 'searchable-picker'
        self.assertEqual(self.compare()['status'], 'matched')
        self.target['controls'].pop(0)
        self.assertEqual(self.compare()['findings'], [{'kind': 'missing_control', 'id': 'dealer'}])

    def test_approved_omission_is_explicit_and_does_not_hide_mixed_case(self):
        (self.root / 'decision.txt').write_text('Retire the date control for the pinned reporting period')
        self.source['deviations'] = [{'control_id': 'date', 'disposition': 'omit', 'reason': 'Retire date picker',
                                     'decision_evidence': ['decision.txt']}]
        self.prepare()
        self.target['controls'].pop(1)
        self.target['cases'] = [row for row in self.target['cases'] if row['id'] not in {'date_only', 'combined'}]
        result = self.compare()
        self.assertEqual(result['findings'], [{'kind': 'missing_case', 'id': 'combined'}])
        self.assertIn({'case_id': 'date_only', 'status': 'excepted', 'control_ids': ['date']}, result['cases'])

    def test_cannot_drop_original_control_or_default_and_changed_cases(self):
        self.source['controls'].pop()
        self.write('base.json', self.source)
        with self.assertRaisesRegex(ValueError, 'source_view_controls'):
            M.baseline(self.root, 'base.json')
        self.source['controls'].append(self.control('date', 'range', 'year', ['sales', 'all_dealers'], []))
        self.source['cases'] = self.source['cases'][:2]
        self.write('base.json', self.source)
        with self.assertRaisesRegex(ValueError, 'default_and_changed_case_required'):
            M.baseline(self.root, 'base.json')

    def test_static_report_requires_evidenced_control_inventory_and_output_case(self):
        self.source['controls'] = []
        self.source['views'][0]['controls'] = []
        self.source['cases'] = [{**self.source['cases'][0], 'controls': [], 'state': {}}]
        self.write('base.json', self.source)
        with self.assertRaises(ValueError):
            M.baseline(self.root, 'base.json')
        self.source['no_controls_evidence'] = [self.source_file]
        self.prepare()
        self.assertEqual(self.compare()['status'], 'matched')
        self.target['cases'] = []
        self.assertEqual(self.compare()['status'], 'partial')

    def test_unresolved_source_behavior_stays_partial(self):
        self.source['unresolved'] = [{'id': 'unknown_export', 'reason': 'No source export observation',
                                     'evidence': [self.source_file]}]
        self.prepare()
        self.assertEqual(self.compare()['findings'], [{'kind': 'source_unresolved', 'id': 'unknown_export'}])

    def test_static_kpi_requires_a_source_expectation_even_when_other_controls_match(self):
        self.source['views'][0]['components'].append('headline_kpi')
        self.prepare()
        self.assertEqual(self.base['uncovered_components'], ['headline_kpi'])
        self.assertEqual(self.compare()['findings'], [{'kind': 'missing_source_expectation', 'id': 'headline_kpi'}])

    def test_exceptions_alone_do_not_establish_parity(self):
        (self.root / 'decision.txt').write_text('Both selectors may be omitted')
        self.source['deviations'] = [
            {'control_id': control['id'], 'disposition': 'omit', 'reason': 'Allow omission',
             'decision_evidence': ['decision.txt']} for control in self.source['controls']]
        self.prepare()
        self.target['controls'] = []
        self.target['cases'] = []
        self.assertEqual(self.compare()['findings'], [{'kind': 'no_compared_case', 'id': 'candidate'}])

    def test_multi_view_control_and_date_context_need_observations(self):
        detail = dict(self.source['views'][0], id='details', title='Detail', controls=['date'])
        self.source['views'].append(detail)
        self.source['cases'][3]['context'] = {'timezone': 'America/Chicago', 'grain': 'day'}
        self.prepare()
        self.target['controls'][1]['source_views'] = ['sales']
        self.target['cases'][3]['context'] = {'timezone': 'UTC', 'grain': 'day'}
        self.assertEqual(self.compare()['findings'], [
            {'kind': 'missing_control_in_view', 'id': 'date', 'view_id': 'details'},
            {'kind': 'case_mismatch', 'id': 'combined', 'fields': ['context']}])

    def test_cli_requires_journal_candidate_and_rechecks_frozen_bytes(self):
        # Exercise a real (synthetic) host-verified journal from the existing gate fixture.
        spec = importlib.util.spec_from_file_location('fidelity_gate_test', Path(__file__).with_name('test_stage_gates.py'))
        gates = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gates)
        fixture = gates.StageGateTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with self.assertRaisesRegex(ValueError, 'current_frozen_candidate_required'):
            M.frozen_candidate(fixture.root)
        fixture.through()
        fixture.candidate()
        gate = fixture.inspect()
        self.assertEqual(M.frozen_candidate(fixture.root), gate['candidate_sha256'])
        with self.assertRaisesRegex(ValueError, 'candidate_baseline_required'):
            M.frozen_candidate(fixture.root, 'unrelated-source.json')
        (fixture.root / gate['candidate']['artifacts'][0]['path']).write_text('Changed candidate')
        with self.assertRaises(ValueError):
            M.frozen_candidate(fixture.root)

    def test_duplicate_control_paths_and_recycled_source_evidence_are_rejected(self):
        self.target['controls'][1]['target_locator'] = self.target['controls'][0]['target_locator']
        with self.assertRaisesRegex(ValueError, 'duplicate_target_locator'):
            self.compare()
        self.prepare()
        self.target['cases'][0]['evidence'] = [self.source_file]
        with self.assertRaisesRegex(ValueError, 'independent_target_evidence'):
            self.compare()

    def test_no_filesystem_escape_or_self_references(self):
        (self.root / 'linked').symlink_to(self.root / self.source_file)
        for path in ('linked', '../outside', 'base.json'):
            with self.subTest(path=path):
                self.source['source_evidence'] = [path]
                self.write('base.json', self.source)
                with self.assertRaises((ValueError, OSError)):
                    M.baseline(self.root, 'base.json')


if __name__ == '__main__':
    unittest.main()
