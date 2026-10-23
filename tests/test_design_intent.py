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

    def experience_requirement(self):
        return {'id': 'experience-mode', 'category': 'experience',
                'purpose': 'Choose the opening and repeat-use journey for the investigation.',
                'surfaces': ['app'], 'required': True, 'origin': 'user', 'disposition': 'selected',
                'decision_ref': 'synthetic-user-choice: branded entry and focused workspace',
                'asset_ids': [], 'contexts': [{'id': 'entry', 'appearance': 'light', 'state': 'ready'}],
                'value': {'mode': 'branded-entry-workspace',
                    'first_use': {'promise': 'Find the change', 'action': 'Open investigation'},
                    'returning_use': {'route': 'Open workspace directly', 'retained_state': ['scope', 'selection']},
                    'art_direction': {'type': 'Large editorial heading; compact evidence labels',
                        'imagery': {'role': 'none', 'fallback': 'Typography carries the entry'},
                        'motion': {'purpose': 'Connect entry to investigation', 'static': 'Immediate workspace'}}}}

    def test_experience_decisions_reach_specialists_through_actual_packets(self):
        requirement = self.experience_requirement()
        self.value['requirements'].append(requirement)
        selected = self.select()['selection']
        for role in ('app-designer', 'app-engineer', 'motion-designer', 'data-storyteller'):
            with self.subTest(role=role):
                packet = D.P.packet(self.root, role, ['contracts/query.json'], self.root / f'tasks/{role}.json')
                context = packet['design_context']
                self.assertEqual(context['selected_intent'], selected)
                self.assertEqual(next(r for r in context['requirements'] if r['id'] == requirement['id']), requirement)
                inputs = {r['path']: r for r in packet['inputs']}
                self.assertEqual(inputs[selected['path']]['sha256'], selected['sha256'])
                self.assertEqual(inputs['contracts/resolved.json']['sha256'], self.fixture.sha('contracts/resolved.json'))
                self.assertEqual(context['open_questions'], [])
                self.assertFalse(packet['external_mutations_authorized'])
        state = D.check(self.root)
        with mock.patch.object(D, 'check', return_value=state):
            context = D.packet_context(self.root, 'motion-designer')
        context['selected_intent']['sha256'] = '0' * 64
        self.assertEqual(state['selected'], selected)

    def test_pending_experience_question_and_explicit_single_screen_no_image_choice(self):
        req = self.experience_requirement()
        req.update(disposition='unresolved', value=None, decision_ref=None, contexts=[])
        self.value.update(branding='none', website=None, assets=[], requirements=[req])
        project = D.P.load_project(self.root)[1]
        project['design_intent_draft'] = 'contracts/experience-draft.json'
        D.P.write_json(self.root / project['design_intent_draft'], self.value)
        D.P.write_json(self.root / 'project.json', project, replace=True)
        pending = D.P.packet(self.root, 'motion-designer', ['contracts/query.json'], self.root / 'tasks/pending.json')
        self.assertIsNone(pending['design_context']['selected_intent'])
        self.assertIn('Resolve: ' + req['purpose'], pending['design_context']['open_questions'])
        self.assertEqual(pending['design_context']['requirements'][0]['disposition'], 'unresolved')
        req.update(disposition='selected', decision_ref='synthetic-user-choice: direct workspace, no imagery',
                   contexts=[{'id': 'workspace', 'appearance': 'light', 'state': 'ready'}],
                   value={'mode': 'workspace-first', 'first_use': 'Open investigation',
                          'returning_use': 'Same single workspace, retain scope',
                          'art_direction': {'imagery': 'none', 'type': 'Aligned labels and tabular values'}})
        selected = self.select()['selection']
        packet = D.P.packet(self.root, 'app-designer', ['contracts/query.json'], self.root / 'tasks/workspace.json')
        self.assertEqual(packet['design_context']['selected_intent'], selected)
        self.assertEqual(packet['design_context']['requirements'], [req])
        self.assertEqual(packet['design_context']['open_questions'], [])
        self.assertEqual(D.check(self.root)['assets'], [])
        self.assertEqual(D.check(self.root)['status'], 'consistent')

    def test_resumed_packet_detects_supersession_without_rewriting_history(self):
        self.value['requirements'].append(self.experience_requirement())
        first = self.select()['selection']
        old_bytes = (self.root / first['path']).read_bytes()
        task = 'tasks/engineer-v1.json'
        D.P.packet(self.root, 'app-engineer', ['contracts/query.json'], self.root / task)
        self.assertEqual(D.P.packet_check(self.root, task)['status'], 'consistent')
        self.value['requirements'][-1]['value']['mode'] = 'direct-workspace'
        self.value['requirements'][-1]['decision_ref'] = 'synthetic revised user decision'
        second = self.select('two')['selection']
        report = D.P.packet_check(self.root, task)
        self.assertEqual(report['status'], 'inconsistent')
        self.assertIn('selected_intent_changed', {f['code'] for f in report['findings']})
        index = D.check(self.root)['current_context']
        self.assertEqual(index['selected_intent'], second)
        self.assertEqual(index['historical_intents'], [first])
        self.assertEqual((self.root / first['path']).read_bytes(), old_bytes)
        D.P.packet(self.root, 'app-engineer', ['contracts/query.json'], self.root / 'tasks/engineer-v2.json')
        self.assertEqual(D.P.packet_check(self.root, 'tasks/engineer-v2.json')['status'], 'consistent')

    def test_named_runtime_and_alias_paths_require_explicit_packet_inputs(self):
        req = self.experience_requirement()
        req['value']['runtime_path'] = 'contracts/input-runtime.json'
        req['value']['aliases_path'] = 'contracts/aliases.json'
        self.value['requirements'].append(req)
        paths = ['contracts/input-runtime.json', 'contracts/aliases.json', 'evidence/callback.json']
        for path in paths:
            (self.root / path).write_text('{"synthetic":true}')
            D.P.register(self.root, 'artifacts', path, path)
        self.select()
        plain = D.P.packet(self.root, 'app-engineer', ['contracts/query.json'], self.root / 'tasks/plain.json')
        self.assertTrue(set(paths).isdisjoint({p['path'] for p in plain['inputs']}))
        full = D.P.packet(self.root, 'app-engineer', ['contracts/query.json', *paths], self.root / 'tasks/full.json')
        self.assertTrue(set(paths) <= {p['path'] for p in full['inputs']})
        self.assertEqual(D.P.packet_check(self.root, 'tasks/full.json')['status'], 'consistent')
        (self.root / paths[1]).write_text('{"synthetic":"changed"}')
        self.assertEqual(D.P.packet_check(self.root, 'tasks/full.json')['status'], 'inconsistent')
        # No claim of dependency closure: descriptive links are deliberately not crawled.
        self.assertEqual(D.P.packet_check(self.root, 'tasks/plain.json')['dependency_completeness'], 'not_assessed')
        D.P.packet(self.root, 'data-analyst', ['contracts/query.json'], self.root / 'tasks/independent.json')
        self.assertEqual(D.P.packet_check(self.root, 'tasks/independent.json')['status'], 'consistent')

    def test_available_height_survives_handoff_and_mismatched_capture_cannot_close_it(self):
        self.value['requirements'][0]['contexts'][0]['viewport'] = [1180, 680]
        self.value['requirements'][0]['value'] = {
            'viewport_basis': 'available_app_content', 'host_chrome': 'excluded',
            'scroll': 'natural vertical scroll', 'first_view': ['identity', 'primary action']}
        self.select()
        packet = D.P.packet(self.root, 'app-designer', ['contracts/query.json'], self.root / 'tasks/laptop.json')
        self.assertEqual(packet['design_context']['requirements'][0]['contexts'][0]['viewport'], [1180, 680])
        self.fixture.value['captures'][0]['context']['viewport'] = [1180, 900]
        report = self.review()
        case = next(c for c in report['cases'] if c['id'] == 'logo-review')
        self.assertEqual(case['recorded_status'], 'not_run')
        self.assertIn('requirement_capture_context_mismatch', case['reasons'])

    def test_packet_context_cannot_be_changed_under_an_unchanged_selection_pin(self):
        self.value['requirements'].append(self.experience_requirement())
        self.select()
        task = 'tasks/altered.json'
        packet = D.P.packet(self.root, 'app-engineer', ['contracts/query.json'], self.root / task)
        packet['design_context']['requirements'][-1]['value']['mode'] = 'unselected-alternative'
        D.P.write_json(self.root / task, packet, replace=True)
        self.assertEqual(D.P.packet_check(self.root, task)['status'], 'inconsistent')

    def test_history_is_compact_metadata_and_cannot_bypass_packet_bound(self):
        selected = self.select()['selection']
        index = D.P.load_project(self.root)[1]
        index['design_intent_history'][0]['arbitrary_note'] = 'x' * D.P.PACKET_BYTES
        D.P.write_json(self.root / 'project.json', index, replace=True)
        self.assertEqual(D.check(self.root)['status'], 'inconsistent')
        self.assertEqual(D.check(self.root)['current_context']['historical_intents'], [])
        index['design_intent_history'] = [selected] + [
            {'path': f'contracts/historical-{i}.json', 'sha256': 'a' * 64, 'bytes': 100} for i in range(1500)]
        D.P.write_json(self.root / 'project.json', index, replace=True)
        with self.assertRaisesRegex(ValueError, 'packet metadata exceeds'):
            D.P.packet(self.root, 'app-engineer', ['contracts/query.json'], self.root / 'tasks/oversized-history.json')
        self.assertFalse((self.root / 'tasks/oversized-history.json').exists())

    def test_changed_experience_or_design_blocks_visual_packets_only(self):
        self.value['requirements'].append(self.experience_requirement())
        self.select()
        for path in ('contracts/intent-one.json', 'contracts/resolved.json'):
            with self.subTest(changed=path):
                file = self.root / path
                before = file.read_bytes()
                value = json.loads(before)
                if path.endswith('intent-one.json'):
                    value['requirements'][-1]['value']['mode'] = 'workspace-first'
                else:
                    value['task'] = 'Different opening and working composition'
                file.write_text(json.dumps(value))
                for role in ('app-designer', 'app-engineer', 'motion-designer', 'data-storyteller'):
                    output = self.root / ('tasks/blocked-' + role + '.json')
                    with self.assertRaisesRegex(ValueError, 'stale_or_invalid_packet_selection'):
                        D.P.packet(self.root, role, ['contracts/query.json'], output)
                    self.assertFalse(output.exists())
                for role in ('data-analyst', 'backend-handoff'):
                    output = self.root / ('tasks/' + Path(path).stem + '-' + role + '.json')
                    packet = D.P.packet(self.root, role, ['contracts/query.json'], output)
                    self.assertEqual([p['path'] for p in packet['inputs']], ['contracts/query.json'])
                    self.assertNotIn('design_context', packet)
                    self.assertIsNone(D.packet_context(self.root, role)['selected_intent'])
                file.write_bytes(before)

    def test_source_review_is_handed_off_but_cannot_fulfill_native_requirement(self):
        req = self.experience_requirement()
        self.value['requirements'].append(req)
        selected = self.select()['selection']
        path = 'evidence/source-experience-review.md'
        (self.root / path).write_text('Synthetic source review: entry/workspace state exists; native appearance unobserved.\n')
        packet = D.P.packet(self.root, 'qa-analyst', [path], self.root / 'tasks/source-review.json')
        self.assertEqual(packet['design_context']['selected_intent'], selected)
        evidence = next(p for p in packet['inputs'] if p['path'] == path)
        self.assertEqual(evidence['sha256'], self.fixture.sha(path))
        self.fixture.value['intent'] = selected
        self.fixture.value['captures'] = []
        case = copy.deepcopy(self.fixture.value['cases'][0])
        case.update(id='experience-source-review', requirement_id=req['id'], requirement_context='entry',
                    asset_ids=[], expected=req['purpose'], method='source_review', capture_ids=[],
                    evidence_paths=[path], observation='Source review completed; no native rendering or interaction observed.')
        self.fixture.value['cases'][0] = case
        report = self.fixture.freeze('source-only')
        result = next(c for c in report['cases'] if c['id'] == case['id'])
        self.assertEqual(result['reported_status'], 'pass')
        self.assertEqual(result['recorded_status'], 'not_run')
        self.assertIn('requirement_native_observation_missing', result['reasons'])
        row = next(r for r in report['intent_coverage']['requirements'] if r['requirement_id'] == req['id'])
        self.assertNotEqual(row['status'], 'recorded_fulfilled')
        self.assertEqual(row['observations'][0]['evidence_paths'], [path])
        self.assertEqual(report['coverage'], 'incomplete')
        self.assertEqual(report['native_verification'], 'not_assessed')
        self.assertEqual(next(c for c in report['cases'] if c['id'] == 'numerical')['recorded_status'], 'pass')

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

    def test_website_omission_survives_selection_without_hiding_pending_logo(self):
        self.value['website'] = None
        self.value['logo_sourcing'] = {'mode': 'supplied', 'authorization_ref': 'synthetic-user-supplied-original',
                                      'source': 'evidence/logo.png'}
        self.value['assets'][0].update(source='Original synthetic logo supplied for this exercise',
                                      sourcing_mode='original', authorization_ref='synthetic-user-supplied-original')
        self.assertIn('What is the official company website?', D.choice_report(self.value)[0])
        omission = {'id': 'brand-website', 'category': 'website', 'purpose': 'Use the supplied original identity without website research.',
                    'surfaces': ['app'], 'required': True, 'origin': 'user', 'disposition': 'explicitly_omitted',
                    'value': None, 'asset_ids': [], 'decision_ref': 'synthetic-user: no website research', 'contexts': []}
        self.value['requirements'].append(omission)
        self.select()
        current = D.check(self.root)
        self.assertEqual(current['status'], 'consistent')
        self.assertEqual(current['open_questions'], [])
        packet = D.P.packet(self.root, 'branding', ['contracts/query.json'], self.root / 'tasks/website-omission.json')
        self.assertEqual(packet['design_context']['requirements'][-1], omission)
        self.assertEqual(packet['design_context']['open_questions'], [])
        self.value['requirements'][0].update(disposition='unresolved', asset_ids=[], decision_ref=None, contexts=[])
        self.select('pending-logo')
        current = D.check(self.root)
        self.assertNotIn('What is the official company website?', current['open_questions'])
        self.assertIn('logo_asset_pending', {f['code'] for f in current['findings']})
        self.assertIn('requirement_unresolved', {f['code'] for f in current['findings']})
        self.value['logo_sourcing'] = {'mode': 'unresolved', 'authorization_ref': None, 'source': None}
        self.select('logo-question')
        current = D.check(self.root)
        self.assertNotIn('What is the official company website?', current['open_questions'])
        self.assertTrue(any('Which approved logo' in q for q in current['open_questions']))

    def test_website_omission_requires_explicit_authority_and_complete_surface_coverage(self):
        value = D.starter(['app', 'dashboard'], 'requested')
        omission = {'id': 'website-research', 'category': 'website', 'purpose': 'Omit website research for this synthetic brand.',
                    'surfaces': ['app', 'dashboard'], 'required': True, 'origin': 'user',
                    'disposition': 'explicitly_omitted', 'value': None, 'asset_ids': [],
                    'decision_ref': 'synthetic-user: no website research', 'contexts': []}
        question = 'What is the official company website?'
        for change in ({'origin': 'proposal'}, {'decision_ref': None}, {'decision_ref': '  '},
                       {'surfaces': ['app']}, {'disposition': 'unresolved'},
                       {'disposition': 'selected', 'value': 'No research',
                        'contexts': [{'id': 'ready', 'appearance': 'light', 'state': 'ready'}]},
                       {'category': 'experience'}):
            with self.subTest(change=change):
                req = dict(omission, **change)
                value['requirements'] = [value['requirements'][0], req]
                self.assertIn(question, D.choice_report(value)[0])
                if req['origin'] == 'proposal' or not D.text(req['decision_ref']):
                    with self.assertRaisesRegex(ValueError, 'omission_needs_user_decision'):
                        D.validate(value, {'surfaces': value['surfaces']})
                else:
                    D.validate(value, {'surfaces': value['surfaces']})
        value['requirements'] = [value['requirements'][0], dict(omission, surfaces=['app']),
                                 dict(omission, id='dashboard-website', surfaces=['dashboard'], origin='reused')]
        D.validate(value, {'surfaces': value['surfaces']})
        self.assertNotIn(question, D.choice_report(value)[0])
        self.assertTrue(any('Which approved logo' in q for q in D.choice_report(value)[0]))

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
