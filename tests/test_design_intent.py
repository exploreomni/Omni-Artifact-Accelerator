"""Synthetic local requirements: file integrity and recorded scope, never native proof."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock
import test_design_review as fixture

PATH = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts/design_intent.py'
spec = importlib.util.spec_from_file_location('intent_tests', PATH)
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.DesignReviewTests()
        self.fixture.setUp()
        self.fixture.remote_candidate()
        self.fixture.value['captures'][0]['kind'] = 'native'
        self.root = self.fixture.root
        self.value = D.starter(['app'], 'requested', 'https://brand.example.invalid')
        self.value['logo_sourcing'] = {'mode': 'official_site', 'authorization_ref': 'synthetic-user-request',
                                       'source': 'https://brand.example.invalid/logo'}
        self.value['assets'] = [{'id': 'logo', 'local_path': 'evidence/logo.png', 'remote_url': None,
            'source': 'https://brand.example.invalid/logo', 'authorization_ref': 'synthetic-user-request',
            'sourcing_mode': 'official_site', 'variant': 'symbol', 'placement': 'header',
            'appearance': 'light', 'loading_method': 'inline', 'size': '40 by 40 CSS px',
            'accessible_name': 'Synthetic brand', 'fallback': 'none; retain gap'}]
        (self.root / 'evidence/logo.png').write_bytes(fixture.PNG)
        self.value['selections'][0].update(design_path='contracts/resolved.json', brand_path='contracts/tokens.json',
            candidate_path='deliverables/app.html', target=copy.deepcopy(self.fixture.value['dependencies'][0]['target']))
        (self.root / 'contracts/resolved.json').write_text(json.dumps({'task': 'inspect', 'brand_contract': 'contracts/tokens.json'}))
        self.value['requirements'][0].update(disposition='selected', asset_ids=['logo'], decision_ref='synthetic-working-choice',
            contexts=[{'id': 'default', 'appearance': 'light', 'state': 'ready'}])
        self.fixture.value['cases'][0]['reviewed_dependencies']['design'] = self.fixture.sha('contracts/resolved.json')

    def tearDown(self):
        self.fixture.tearDown()

    def select(self, version='one'):
        path = self.root / ('contracts/intent-' + version + '.json')
        D.P.write_json(path, self.value)
        return D.select(self.root, path, 'contracts/selected-' + version + '.json')

    def review(self, version='one', named=True):
        if not (self.root / 'contracts/selected-one.json').exists():
            self.select()
        self.fixture.value['intent'] = D.check(self.root)['selected']
        if named:
            case = copy.deepcopy(self.fixture.value['cases'][0])
            case.update(id='logo-review', requirement_id='brand-logo', requirement_context='default', asset_ids=['logo'],
                        expected='Selected logo is visible in the header.')
            self.fixture.value['cases'] = [c for c in self.fixture.value['cases'] if c['id'] != 'logo-review'] + [case]
        return self.fixture.freeze(version)

    def test_starter_keeps_logo_open_and_grant_does_not_repeat_question(self):
        draft = D.starter(['app'], 'requested', 'https://brand.example.invalid')
        q, f = D.choice_report(draft)
        self.assertTrue(q)
        draft['logo_sourcing'] = self.value['logo_sourcing']
        q, f = D.choice_report(draft)
        self.assertEqual(q, [])
        self.assertIn('logo_asset_pending', {x['code'] for x in f})
        self.assertEqual(D.starter(['app'])['requirements'], [])
        self.assertEqual(D.starter(['app'], 'none', 'https://brand.example.invalid')['requirements'], [])

    def test_draft_is_unassessed_and_packet_reuses_defaults(self):
        project = D.P.load_project(self.root)[1]
        project['design_intent_draft'] = 'contracts/intent.json'
        D.P.write_json(self.root / 'contracts/intent.json', D.starter(['app'], 'requested'))
        D.P.write_json(self.root / 'project.json', project, replace=True)
        report = D.check(self.root)
        self.assertEqual(report['status'], 'not_assessed')
        self.assertTrue(report['open_questions'])
        packet = D.packet_context(self.root, 'app-engineer')
        self.assertIn('contracts/brand.json', packet['paths'])
        self.assertIn('contracts/intent.json', packet['paths'])
        self.assertEqual(D.summary(self.root, {})['status'], 'not_assessed')

    def test_only_pristine_unknown_draft_can_follow_changed_project_surfaces(self):
        project = D.P.load_project(self.root)[1]
        project['design_intent_draft'] = 'contracts/scope-draft.json'
        draft_path = self.root / project['design_intent_draft']
        pristine = D.starter(['dashboard'])
        D.P.write_json(draft_path, pristine)
        original = draft_path.read_bytes()
        for surfaces in (['app'], ['app', 'dashboard']):
            with self.subTest(pristine_surfaces=surfaces):
                project['surfaces'] = surfaces
                D.P.write_json(self.root / 'project.json', project, replace=True)
                project_bytes = (self.root / 'project.json').read_bytes()
                report = D.check(self.root)
                self.assertEqual(report['status'], 'not_assessed')
                self.assertEqual([s['surface'] for s in report['selections']], surfaces)
                self.assertIsNone(report['selected'])
                self.assertIn('unselected_starter_scope_refreshed', {f['code'] for f in report['findings']})
                self.assertIn(project['design_intent_draft'], D.packet_context(self.root, 'app-engineer')['paths'])
                self.assertEqual(draft_path.read_bytes(), original)
                self.assertEqual((self.root / 'project.json').read_bytes(), project_bytes)
        decisions = [
            {'logo_sourcing': copy.deepcopy(self.value['logo_sourcing'])},
            {'assets': copy.deepcopy(self.value['assets'])},
            {'website': 'https://brand.example.invalid'},
            {'selections': [dict(pristine['selections'][0], design_path='contracts/resolved.json')]},
            {'saved_decision': 'Do not automatically reinterpret this draft'},
        ]
        for decision in decisions:
            with self.subTest(decision=next(iter(decision))):
                value = copy.deepcopy(pristine)
                value.update(decision)
                D.P.write_json(draft_path, value, replace=True)
                before = draft_path.read_bytes()
                report = D.check(self.root)
                self.assertEqual(report['status'], 'inconsistent')
                self.assertNotIn('unselected_starter_scope_refreshed', {f['code'] for f in report['findings']})
                with self.assertRaisesRegex(ValueError, 'stale_or_invalid_packet_selection'):
                    D.packet_context(self.root, 'app-engineer')
                self.assertEqual(draft_path.read_bytes(), before)

    def test_selection_preserves_bytes_and_rejects_stale_brand_link(self):
        self.value['selections'][0]['brand_path'] = 'contracts/brand.json'
        with self.assertRaisesRegex(ValueError, 'design_brand_reference_mismatch'):
            self.select()
        self.assertFalse((self.root / 'contracts/selected-one.json').exists())
        self.assertNotIn('design_intent', D.P.load_project(self.root)[1])

    def test_declared_asset_change_blocks_visual_packet_not_backend(self):
        before = (self.root / 'contracts/resolved.json').read_bytes()
        self.select()
        self.assertEqual(before, (self.root / 'contracts/resolved.json').read_bytes())
        self.assertIn('evidence/logo.png', D.packet_context(self.root, 'bi-engineer')['paths'])
        (self.root / 'evidence/logo.png').write_bytes(fixture.PNG + b'new')
        self.assertEqual(D.check(self.root)['status'], 'inconsistent')
        with self.assertRaisesRegex(ValueError, 'changed_or_missing_file: evidence/logo.png'):
            D.packet_context(self.root, 'app-engineer')
        self.assertEqual(D.packet_context(self.root, 'backend-handoff')['paths'], [])

    def test_generic_craft_cannot_close_logo_but_named_review_can(self):
        report = self.review('generic', named=False)
        self.assertEqual(report['coverage'], 'incomplete')
        self.assertIn('design_requirement_unfulfilled', {g['code'] for g in report['gaps']})
        report = self.review('named')
        self.assertEqual(report['coverage'], 'complete')
        summary = D.summary(self.root, report)
        self.assertEqual(summary['status'], 'recorded_complete')
        self.assertFalse(summary['publication_authorized'])
        self.assertEqual(summary['native_verification'], 'not_assessed')
        row = summary['requirements'][0]
        self.assertEqual(row['purpose'], self.value['requirements'][0]['purpose'])
        self.assertEqual(row['asset_ids'], ['logo'])
        self.assertEqual(row['assets'][0]['file']['path'], 'evidence/logo.png')
        self.assertEqual(row['observations'][0]['captures'][0]['kind'], 'native')
        self.assertEqual(row['observations'][0]['evidence_paths'], ['evidence/review.txt'])

    def test_local_prototype_cannot_close_named_native_requirement(self):
        target = {'surface': 'app', 'state': 'local', 'document_id': None, 'draft_id': None}
        self.value['selections'][0]['target'] = copy.deepcopy(target)
        self.fixture.value['dependencies'][0]['target'] = copy.deepcopy(target)
        self.fixture.value['captures'][0]['kind'] = 'prototype'
        for case in self.fixture.value['cases']:
            case['target'] = copy.deepcopy(target)
        report = self.review()
        cases = {c['id']: c for c in report['cases']}
        self.assertEqual(cases['craft']['recorded_status'], 'pass')
        self.assertEqual(cases['numerical']['recorded_status'], 'pass')
        self.assertEqual(cases['logo-review']['recorded_status'], 'not_run')
        self.assertIn('requirement_native_observation_missing', cases['logo-review']['reasons'])
        self.assertEqual(report['intent_coverage']['status'], 'incomplete')

    def test_selected_logo_needs_size_accessible_name_and_fallback(self):
        for field in ('size', 'accessible_name', 'fallback'):
            with self.subTest(field=field):
                asset = self.value['assets'][0]
                saved = asset.pop(field)
                with self.assertRaisesRegex(ValueError, 'logo_asset_' + field + '_required'):
                    self.select(field)
                self.assertFalse((self.root / ('contracts/selected-' + field + '.json')).exists())
                asset[field] = saved

    def test_missing_website_question_prevents_recorded_complete(self):
        self.value['website'] = None
        report = self.review()
        self.assertEqual(report['intent_coverage']['status'], 'incomplete')
        self.assertIn('intent_choice_unresolved', {g['code'] for g in report['gaps']})

    def test_optional_decoration_does_not_require_review(self):
        req = copy.deepcopy(self.value['requirements'][0])
        req.update(id='optional-decoration', category='decoration', required=False,
                   disposition='unresolved', asset_ids=[], contexts=[])
        self.value['requirements'].append(req)
        report = self.review()
        self.assertEqual(report['intent_coverage']['status'], 'recorded_complete')

    def test_asset_drift_reopens_visual_not_numerical(self):
        self.review()
        (self.root / 'evidence/logo.png').write_bytes(fixture.PNG + b'changed')
        report = fixture.P.design_check(self.root)
        by = {c['id']: c for c in report['cases']}
        self.assertEqual(by['numerical']['recorded_status'], 'pass')
        self.assertEqual(by['logo-review']['recorded_status'], 'not_run')
        self.assertEqual(report['coverage'], 'incomplete')

    def test_wrong_requirement_context_and_asset_cannot_close(self):
        self.review()
        case = next(c for c in self.fixture.value['cases'] if c['id'] == 'logo-review')
        case['asset_ids'] = []
        case['requirement_context'] = 'not-selected'
        report = self.fixture.freeze('bad')
        self.assertEqual(report['intent_coverage']['status'], 'incomplete')
        self.assertEqual(report['cases'][-1]['recorded_status'], 'not_run')

    def test_omission_needs_user_decision_and_does_not_require_image(self):
        req = self.value['requirements'][0]
        req.update(disposition='explicitly_omitted', asset_ids=[], contexts=[])
        with self.assertRaisesRegex(ValueError, 'omission_needs_user_decision'):
            self.select()
        req.update(origin='user', decision_ref='user-selected-no-logo')
        self.select('valid')
        self.fixture.value['intent'] = D.check(self.root)['selected']
        report = self.fixture.freeze()
        self.assertEqual(report['intent_coverage']['requirements'][0]['status'], 'explicitly_omitted')

    def test_two_surfaces_cannot_be_silently_dropped(self):
        project = D.P.load_project(self.root)[1]
        project['surfaces'].append('dashboard')
        D.P.write_json(self.root / 'project.json', project, replace=True)
        with self.assertRaisesRegex(ValueError, 'project_surfaces_must_be_accounted'):
            self.select()

    def test_selection_history_and_required_denominator_retained(self):
        first = self.select()
        self.value['requirements'] = []
        self.value['branding'] = 'none'
        with self.assertRaisesRegex(ValueError, 'required_requirement_removed'):
            self.select('dropped')
        self.value['requirements'] = D.load_selected(self.root)['spec']['requirements']
        self.value['requirements'][0].update(origin='user', disposition='explicitly_omitted', decision_ref='no-logo-choice')
        self.select('two')
        history = D.P.load_project(self.root)[1]['design_intent_history']
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], first['selection'])

    def test_symlink_invalid_asset_and_partial_write_failure_do_not_select(self):
        (self.root / 'evidence/logo.png').unlink()
        (self.root / 'evidence/logo.png').symlink_to(self.root / 'evidence/capture.png')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.select()
        self.assertFalse((self.root / 'contracts/selected-one.json').exists())
        (self.root / 'evidence/logo.png').unlink()
        (self.root / 'evidence/logo.png').write_bytes(fixture.PNG)
        original = D.P.write_json
        def fail_index(path, value, replace=False):
            if Path(path).name == 'project.json':
                raise OSError('synthetic index failure')
            return original(path, value, replace)
        with mock.patch.object(D.P, 'write_json', side_effect=fail_index):
            with self.assertRaisesRegex(OSError, 'synthetic index failure'):
                self.select('interrupted')
        self.assertNotIn('design_intent', D.P.load_project(self.root)[1])
        self.assertTrue((self.root / 'contracts/selected-interrupted.json').exists())

    def test_remote_asset_stays_unverified_and_case_template_has_no_pass(self):
        asset = self.value['assets'][0]
        asset.update(local_path=None, remote_url='https://brand.example.invalid/logo.png')
        self.select()
        self.assertIn('remote_asset_bytes_unverified', {f['code'] for f in D.check(self.root)['findings']})
        template = D.case_templates(self.root)['cases'][0]
        self.assertEqual(template['status'], 'not_run')
        self.assertFalse(template['executed'])
        self.assertEqual(template['target']['state'], 'draft')


if __name__ == '__main__':
    unittest.main()
