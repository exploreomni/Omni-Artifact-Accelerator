"""Synthetic declarations only: these tests cannot authenticate observation or craft."""
import copy
import json
import subprocess
import sys
import unittest
import test_design_review as fixture

P = fixture.P
D = P.intent_helper()


class DestinationCoverageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.DesignReviewTests()
        self.fixture.setUp()
        self.root, self.review = self.fixture.root, self.fixture.value
        self.intent = D.starter(['app'], 'none')
        self.design = {'brand_contract': 'contracts/tokens.json', 'destinations': [
            dict(id=i, purpose='Inspect synthetic evidence', primary_action='Inspect', evidence='Synthetic values',
                 drill='Select item', **{'return': 'Retain selection'}, responsive='Reflow')
            for i in ('entry', 'workspace')]}
        self.intent['selections'][0].update(design_path='contracts/resolved.json', brand_path='contracts/tokens.json',
            candidate_path='deliverables/app.html', target=copy.deepcopy(self.review['dependencies'][0]['target']))
        self.intent['requirements'] = [{'id': 'experience', 'category': 'experience', 'purpose': 'Inspect the whole experience',
            'surfaces': ['app'], 'required': True, 'origin': 'user', 'disposition': 'selected',
            'decision_ref': 'synthetic brief', 'value': {'mode': 'selected'}, 'asset_ids': [],
            'delivery': {'source_ref': 'synthetic brief', 'owner': 'app-designer', 'behavior': 'Inspect',
                         'destinations': ['entry', 'workspace']},
            'contexts': [{'id': 'default', 'appearance': 'light', 'state': 'ready', 'viewport': [1024, 768],
                'applicability': [{'kind': 'destination', 'id': ident,
                    'lanes': {lane: {'status': 'required'} for lane in ('craft', 'numerical')}}
                    for ident in ('entry', 'workspace')]}]}]
        self.review['scope']['coverage'] = {'mode': 'whole_experience'}
        self.select()
        for case in self.review['cases']:
            case['obligation_ids'] = [self.oid('entry', case['lane'])]
            case['expected'] = 'Inspect the synthetic evidence'
        self.review['captures'][0].update(destination_id='entry', requirement_id='experience', requirement_context='default')

    def tearDown(self):
        self.fixture.tearDown()

    def oid(self, target, lane='craft', kind='destination', context='default'):
        return '/'.join(('experience', 'app', kind, target, context, lane))

    def select(self, name='one'):
        (self.root / 'contracts/resolved.json').write_text(json.dumps(self.design))
        path = self.root / ('contracts/intent-' + name + '.json')
        path.write_text(json.dumps(self.intent))
        self.review['intent'] = D.select(self.root, path, 'contracts/selected-' + name + '.json')['selection']
        for case in self.review['cases']:
            case['reviewed_dependencies']['design'] = self.fixture.sha('contracts/resolved.json')

    def test_two_destinations_one_review_remains_incomplete(self):
        self.fixture.remote_candidate()
        self.intent['selections'][0]['target'] = copy.deepcopy(self.review['dependencies'][0]['target'])
        self.review['captures'][0]['kind'] = 'native'
        self.review['cases'][0].update(requirement_id='experience', requirement_context='default',
                                      asset_ids=[], expected='Inspect both destinations')
        self.select('native')
        self.assertEqual(P.experience_check(self.root)['status'], 'ready_for_review')
        report = self.fixture.freeze()
        self.assertEqual(report['coverage'], 'incomplete')
        coverage = report.get('destination_coverage', {})
        workspace = [o for o in coverage.get('obligations', []) if o['target_id'] == 'workspace']
        self.assertEqual(len(workspace), 2)
        self.assertTrue(all(o['status'] == 'missing' for o in workspace))
        self.assertEqual(report['intent_coverage']['status'], 'incomplete')


    def complete(self):
        case = copy.deepcopy(self.review['cases'][0])
        case.update(id='workspace', obligation_ids=[self.oid('workspace')], capture_ids=['workspace'])
        self.review['cases'].append(case)
        capture = dict(self.review['captures'][0], id='workspace', destination_id='workspace')
        self.review['captures'].append(capture)
        self.review['cases'][1]['obligation_ids'].append(self.oid('workspace', 'numerical'))

    def test_shared_numerical_local_craft_and_native_fulfillment_are_distinct(self):
        self.complete()
        report = self.fixture.freeze()
        self.assertEqual(report['coverage'], 'complete')
        self.assertEqual(report['destination_coverage']['status'], 'complete')
        numeric = next(c for c in report['cases'] if c['lane'] == 'numerical')
        self.assertEqual(numeric['recorded_status'], 'pass')
        self.assertEqual(len(numeric['obligation_ids']), 2)
        self.assertEqual(report['intent_coverage']['status'], 'incomplete')
        self.assertTrue(all(not o['native_recorded'] for o in report['destination_coverage']['obligations']))
        self.fixture.remote_candidate()
        self.intent['selections'][0]['target'] = copy.deepcopy(self.review['dependencies'][0]['target'])
        for capture in self.review['captures']:
            capture['kind'] = 'native'
        self.select('native')
        report = self.fixture.freeze('native')
        self.assertEqual(report['intent_coverage']['status'], 'recorded_complete')
        self.assertEqual(report['cases'][1]['recorded_status'], 'pass')
        self.assertEqual(report['native_verification'], 'not_assessed')

    def test_missing_applicability_cannot_shrink_inventory_or_lanes(self):
        self.complete()
        context = self.intent['requirements'][0]['contexts'][0]
        context['applicability'] = context['applicability'][:1]
        context['applicability'][0]['lanes'].pop('numerical')
        self.select('missing')
        report = self.fixture.freeze()
        self.assertEqual(len(report['destination_coverage']['inventory']), 2)
        self.assertTrue({'destination_context_missing', 'lane_applicability_missing'} <= self.fixture.codes(report))
        self.assertEqual(report['coverage'], 'incomplete')

    def test_typed_exclusion_needs_no_duplicate_execution(self):
        self.complete()
        self.review['cases'] = [c for c in self.review['cases'] if c['lane'] == 'craft']
        for row in self.intent['requirements'][0]['contexts'][0]['applicability']:
            row['lanes']['numerical'] = {'status': 'not_applicable', 'rationale': 'Only composition changes',
                                         'decision_ref': 'synthetic selected scope'}
        self.select('excluded')
        report = self.fixture.freeze()
        self.assertEqual(report['coverage'], 'complete')
        self.assertEqual([o['status'] for o in report['destination_coverage']['obligations'] if o['lane'] == 'numerical'],
                         ['not_applicable', 'not_applicable'])
        self.intent['requirements'][0]['contexts'][0]['applicability'][0]['lanes']['craft'] = {
            'status': 'not_applicable', 'rationale': 'No', 'decision_ref': 'No'}
        with self.assertRaisesRegex(ValueError, 'exclusion_unjustified'):
            self.select('invalid')

    def test_wrong_destination_context_and_unknown_obligation_reject_evidence(self):
        self.complete()
        self.review['captures'][1]['destination_id'] = 'entry'
        report = self.fixture.freeze()
        self.assertIn('destination_capture_context_mismatch:', ' '.join(report['cases'][-1]['reasons']))
        self.review['captures'][1].update(destination_id='workspace', requirement_context='other')
        self.assertIn('capture_destination_binding_invalid', self.fixture.codes(self.fixture.freeze('context')))
        self.review['cases'][-1]['obligation_ids'] = [self.oid('unknown')]
        self.assertIn('obligation_binding_missing_or_unknown', self.fixture.freeze('unknown')['cases'][-1]['reasons'])

    def test_wrong_destination_and_context_corrections_do_not_close(self):
        self.complete()
        self.review['findings'] = [{'id': 'clip', 'surface': 'app', 'case_id': 'workspace', 'retest_case_id': 'craft',
            'obligation_ids': [self.oid('workspace')], 'problem': 'Synthetic label clipped', 'owner': 'app-engineer',
            'impact': 'material', 'disposition': 'corrected', 'evidence_paths': ['evidence/review.txt']}]
        self.review['deviations'] = [{'id': 'layout', 'surface': 'app', 'candidate_id': 'candidate',
            'candidate_sha256': self.fixture.sha('deliverables/app.html'), 'designer': 'Synthetic reviewer',
            'designer_role': 'app-designer', 'intended': 'Side panel', 'actual': 'Below', 'reason': 'Constraint',
            'rationale': 'Synthetic correction', 'disposition': 'corrected', 'retest_case_id': 'craft',
            'obligation_ids': [self.oid('workspace')], 'evidence_paths': ['evidence/review.txt']}]
        self.assertIn('correction_obligation_mismatch', self.fixture.codes(self.fixture.freeze()))
        for key in ('findings', 'deviations'):
            self.review[key][0]['retest_case_id'] = 'workspace'
        self.assertEqual(self.fixture.freeze('correct')['coverage'], 'complete')
        self.review['findings'][0]['obligation_ids'] = [self.oid('workspace', context='narrow')]
        self.assertIn('correction_obligation_mismatch', self.fixture.codes(self.fixture.freeze('context')))

    def journey(self, same_screen=False):
        self.complete()
        self.review['scope']['required_lanes'] = ['craft']
        self.review['cases'] = [c for c in self.review['cases'] if c['lane'] == 'craft']
        journey = {'id': 'inspect', 'path': ['entry', 'entry' if same_screen else 'workspace'],
                   'action': 'Inspect selected item', 'start_state': 'ready', 'end_state': 'selected',
                   'retained_context': 'Item 42', 'return_behavior': 'Restore selected item'}
        self.design['journeys'] = [journey]
        self.intent['requirements'][0]['delivery']['journeys'] = ['inspect']
        self.intent['requirements'][0]['contexts'][0]['applicability'].append(
            {'kind': 'journey', 'id': 'inspect', 'lanes': {'craft': {'status': 'required'}}})
        self.select('journey')
        capture = copy.deepcopy(self.review['captures'][0])
        capture.update(id='end', destination_id=journey['path'][-1])
        capture['context']['state'] = 'selected'
        self.review['captures'].append(capture)
        case = copy.deepcopy(self.review['cases'][0])
        case.update(id='journey', obligation_ids=[self.oid('inspect', kind='journey')], capture_ids=['screen', 'end'])
        self.review['cases'].append(case)
        return case, journey

    def test_still_endpoints_do_not_close_journey_and_matching_note_does(self):
        case, journey = self.journey()
        self.assertIn('journey_execution_missing_or_mismatched:', ' '.join(self.fixture.freeze()['cases'][-1]['reasons']))
        observation = {k: v for k, v in journey.items() if k != 'id'}
        observation.update(obligation_id=case['obligation_ids'][0], method='local_execution',
                           observation='Synthetic test declaration only', evidence_paths=['evidence/capture.png'])
        case['journey_observations'] = [observation]
        self.assertEqual(self.fixture.freeze('image')['coverage'], 'incomplete')
        (self.root / 'evidence/fake.txt').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        observation['evidence_paths'] = ['evidence/fake.txt']
        self.assertEqual(self.fixture.freeze('svg')['coverage'], 'incomplete')
        observation['evidence_paths'] = ['evidence/review.txt']
        self.assertEqual(self.fixture.freeze('observed')['coverage'], 'complete')
        self.review['captures'][-1]['requirement_context'] = 'wrong'
        self.assertIn('journey_endpoint_capture_mismatch:', ' '.join(self.fixture.freeze('wrong')['cases'][-1]['reasons']))

    def test_same_screen_transition_is_supported_without_new_destination(self):
        case, journey = self.journey(same_screen=True)
        case['journey_observations'] = [dict({k: v for k, v in journey.items() if k != 'id'},
            obligation_id=case['obligation_ids'][0], method='local_execution',
            observation='Synthetic state transition', evidence_paths=['evidence/review.txt'])]
        self.assertEqual(self.fixture.freeze()['coverage'], 'complete')
        case['journey_observations'][0]['return_behavior'] = 'Lost selected item'
        self.assertEqual(self.fixture.freeze('wrong-return')['coverage'], 'incomplete')

    def test_focused_scope_keeps_inventory_and_changed_candidate_reopens_capture(self):
        self.review['scope']['coverage'] = {'mode': 'focused', 'affected_obligation_ids': [self.oid('entry')]}
        self.review['cases'] = self.review['cases'][:1]
        report = self.fixture.freeze()
        self.assertEqual(report['coverage'], 'scoped_complete')
        self.assertEqual(len(report['destination_coverage']['inventory']), 2)
        cli = subprocess.run([sys.executable, str(fixture.SCRIPT), 'design-check', '--project', str(self.root)],
                             capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout)['coverage'], 'scoped_complete')
        self.assertEqual(sum(o['status'] == 'out_of_scope' for o in report['destination_coverage']['obligations']), 3)
        (self.root / 'deliverables/app.html').write_text('Changed elsewhere, same file')
        report = P.design_check(self.root)
        self.assertEqual(report['coverage'], 'incomplete')
        self.assertEqual(report['cases'][0]['recorded_status'], 'not_run')

    def test_new_freeze_cannot_opt_out_and_old_immutable_record_stays_readable(self):
        self.complete()
        self.review['scope'].pop('coverage')
        report = self.fixture.freeze()
        self.assertIn('destination_review_scope_missing', self.fixture.codes(report))
        helper = P.design_helper()
        unbound = copy.deepcopy(self.review)
        unbound.pop('intent')
        unbound['destination_coverage_version'] = None  # User input cannot select legacy semantics.
        unbound_path = self.root / 'contracts/unbound-spec.json'
        unbound_path.write_text(json.dumps(unbound))
        unbound_report = P.design_freeze(self.root, unbound_path, 'contracts/unbound-review.json')['report']
        self.assertEqual(unbound_report['coverage'], 'incomplete')
        self.assertIn('destination_intent_missing_or_stale', self.fixture.codes(unbound_report))
        self.assertEqual(json.loads((self.root / 'contracts/unbound-review.json').read_text())['destination_coverage_version'], 1)
        old = copy.deepcopy(self.review)
        old.pop('intent')
        for case in old['cases']:
            case.pop('obligation_ids')
        old_path = 'contracts/historical-spec.json'
        (self.root / old_path).write_text(json.dumps(old))
        _, project = P.load_project(self.root)
        record = {'schema_version': 1, 'kind': 'analyst_design_review', 'project_id': project['id'],
            'project_mode': project['mode'], 'project_surfaces': project['surfaces'], 'spec': old,
            'spec_file': helper.file_pin(self.root, old_path), 'pins': [helper.file_pin(self.root, p)
                for p in helper.references(old, self.root)], 'authority': 'recorded_evidence_only'}
        record['content_sha256'] = P.digest(P.canonical(record))
        historical = self.root / 'contracts/historical-review.json'
        historical.write_text(json.dumps(record))
        before = historical.read_bytes()
        result = P.design_check(self.root, 'contracts/historical-review.json')
        self.assertEqual(result['coverage'], 'complete')
        self.assertEqual(result['destination_coverage']['status'], 'not_assessed')
        self.assertEqual(historical.read_bytes(), before)

    def test_case_generation_uses_actual_review_lanes_and_verify_exposes_gaps(self):
        path = self.root / 'contracts/generate.json'
        path.write_text(json.dumps(self.review))
        result = D.case_templates(self.root, 'contracts/generate.json')
        command = [sys.executable, str(fixture.SCRIPT), 'intent-cases', '--project', str(self.root),
                   '--review-spec', 'contracts/generate.json']
        cli = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(len(json.loads(cli.stdout)['cases']), 4)
        self.assertEqual(len(result['cases']), 4)
        self.assertEqual({c['lane'] for c in result['cases']}, {'craft', 'numerical'})
        self.assertEqual(len(D.case_templates(self.root)['cases']), 2)
        self.fixture.freeze()
        self.assertEqual(P.project_check(self.root)['design_evidence']['destination_coverage']['status'], 'incomplete')

    def test_deferred_and_omitted_requirements_are_not_passes(self):
        self.complete()
        req = self.intent['requirements'][0]
        req['disposition'] = 'deferred'
        self.select('deferred')
        self.assertIn('destination_requirement_deferred', self.fixture.codes(self.fixture.freeze()))
        req.update(disposition='explicitly_omitted', decision_ref='synthetic user omission')
        self.select('omitted')
        self.review['cases'] = []
        report = self.fixture.freeze('omitted')
        self.assertEqual(report['intent_coverage']['requirements'][0]['status'], 'explicitly_omitted')
        self.assertTrue(all(i['omissions'] for i in report['destination_coverage']['inventory']))
        self.assertEqual(report['destination_coverage']['obligations'], [])

    def test_deferred_requirement_preserves_justified_lane_exclusions(self):
        original_numeric = copy.deepcopy(self.review['cases'][1])
        req = self.intent['requirements'][0]
        req['disposition'] = 'deferred'
        self.review['scope']['required_lanes'] = ['craft', 'native_behavior', 'numerical', 'responsive']
        for application in req['contexts'][0]['applicability']:
            application['lanes'] = {
                'craft': {'status': 'required'}, 'native_behavior': {'status': 'required'},
                'numerical': {'status': 'not_applicable', 'rationale': 'No new calculation in this request',
                              'decision_ref': 'synthetic scope decision'},
                'responsive': {'status': 'not_applicable', 'rationale': 'No layout change in this request',
                               'decision_ref': 'synthetic scope decision'}}
        self.review.update(cases=[], captures=[])
        self.select('deferred-exclusions')
        spec_path = self.root / 'contracts/deferred-case-generation.json'
        spec_path.write_text(json.dumps(self.review))
        generated = D.case_templates(self.root, 'contracts/deferred-case-generation.json')
        self.assertEqual({c['lane'] for c in generated['cases']}, {'craft', 'native_behavior'})
        report = self.fixture.freeze('deferred-exclusions')
        obligations = report['destination_coverage']['obligations']
        self.assertEqual({o['status'] for o in obligations if o['lane'] in {'numerical', 'responsive'}},
                         {'not_applicable'})
        self.assertEqual({o['status'] for o in obligations if o['lane'] in {'craft', 'native_behavior'}},
                         {'deferred'})
        self.assertEqual(report['coverage'], 'incomplete')
        self.assertEqual(report['destination_coverage']['status'], 'incomplete')
        self.assertIn('destination_requirement_deferred', self.fixture.codes(report))
        incomplete = {g['obligation_id'] for g in report['gaps'] if g['code'] == 'destination_obligation_incomplete'}
        self.assertEqual(incomplete, {o['id'] for o in obligations if o['lane'] in {'craft', 'native_behavior'}})
        # A valid explicit exclusion case agrees with the selected rule; invalid
        # passing evidence cannot turn an excluded lane into a qualified result.
        original_numeric.update(status='not_applicable', executed=False, rationale='No calculation change')
        original_numeric['reviewed_dependencies']['design'] = self.fixture.sha('contracts/resolved.json')
        self.review['cases'] = [original_numeric]
        explicit = self.fixture.freeze('explicit-exclusion')
        excluded = next(o for o in explicit['destination_coverage']['obligations']
                        if o['id'] == self.oid('entry', 'numerical'))
        self.assertEqual(excluded['status'], 'not_applicable')
        original_numeric.update(status='pass', executed=True)
        invalid = self.fixture.freeze('invalid-excluded-evidence')
        self.assertEqual(invalid['cases'][0]['recorded_status'], 'not_run')
        self.assertIn('obligation_applicability_unresolved_or_excluded', invalid['cases'][0]['reasons'])
        self.assertEqual(invalid['coverage'], 'incomplete')


    def test_cross_surface_contexts_use_distinct_destinations_without_phantom_pairs(self):
        project = P.load_project(self.root)[1]
        project['surfaces'].append('dashboard')
        # This fixture has not reviewed the previous one-surface selection. Start an
        # independent two-surface selection rather than rewriting an immutable record.
        project.pop('design_intent')
        project['design_intent_history'] = []
        P.write_json(self.root / 'project.json', project, replace=True)
        self.intent['surfaces'] = ['app', 'dashboard']
        req = self.intent['requirements'][0]
        req['surfaces'] = ['app', 'dashboard']
        req['delivery']['destinations'] = ['entry', 'workspace', 'operations']
        req['contexts'][0]['id'] = 'app-default'
        for item in req['contexts'][0]['applicability']:
            item['surface'] = 'app'
        req['contexts'].append({'id': 'dashboard-default', 'appearance': 'light', 'state': 'ready',
            'applicability': [{'kind': 'destination', 'id': 'operations', 'surface': 'dashboard',
                'lanes': {'craft': {'status': 'required'}, 'numerical': {'status': 'required'}}}]})
        (self.root / 'contracts/dashboard.json').write_text(json.dumps(
            {'brand_contract': 'contracts/tokens.json', 'destinations': [{'id': 'operations'}]}))
        (self.root / 'deliverables/dashboard.json').write_text('{"title":"Synthetic"}')
        self.complete()
        target = self.fixture.remote_candidate()
        self.intent['selections'][0]['target'] = target
        dashboard_target = dict(target, surface='dashboard')
        self.intent['selections'].append({'surface': 'dashboard', 'design_path': 'contracts/dashboard.json',
            'brand_path': 'contracts/tokens.json', 'candidate_path': 'deliverables/dashboard.json', 'target': dashboard_target})
        self.review['scope'].update(change='focused_edit', surfaces=['app', 'dashboard'])
        for dep in self.review['dependencies']:
            if dep['kind'] in {'brand', 'query', 'expectation'}:
                dep['surface'] = 'shared'
        self.review['dependencies'] += [
            {'id': 'dashboard', 'kind': 'candidate', 'surface': 'dashboard', 'path': 'deliverables/dashboard.json', 'target': dashboard_target},
            {'id': 'dashboard-design', 'kind': 'design', 'surface': 'dashboard', 'path': 'contracts/dashboard.json'}]
        for case in self.review['cases']:
            case['obligation_ids'] = [i.replace('/default/', '/app-default/') for i in case['obligation_ids']]
        for capture in self.review['captures']:
            capture.update(kind='native', requirement_context='app-default')
        capture = dict(self.review['captures'][0], id='operations', destination_id='operations',
                       requirement_context='dashboard-default', candidate_id='dashboard',
                       candidate_sha256=self.fixture.sha('deliverables/dashboard.json'))
        self.review['captures'].append(capture)
        for lane in ('craft', 'numerical'):
            case = copy.deepcopy(next(c for c in self.review['cases'] if c['lane'] == lane))
            case.update(id='dashboard-' + lane, surface='dashboard', candidate_id='dashboard', target=dashboard_target,
                obligation_ids=['experience/dashboard/destination/operations/dashboard-default/' + lane],
                capture_ids=['operations'] if lane == 'craft' else [],
                reviewed_dependencies={d['id']: self.fixture.sha(d['path']) for d in self.review['dependencies']})
            self.review['cases'].append(case)
        self.select('two-surfaces')
        # select() only refreshes the original app design dependency in the helper.
        for case in self.review['cases']:
            case['reviewed_dependencies']['dashboard-design'] = self.fixture.sha('contracts/dashboard.json')
        report = self.fixture.freeze()
        self.assertEqual(report['coverage'], 'complete', report['gaps'])
        self.assertEqual(report['intent_coverage']['status'], 'recorded_complete')
        self.assertEqual([(r['surface'], r['context_id']) for r in report['intent_coverage']['requirements']],
                         [('app', 'app-default'), ('dashboard', 'dashboard-default')])

    def test_changed_selected_design_and_context_reopen_existing_observations(self):
        self.complete()
        self.fixture.freeze()
        self.intent['requirements'][0]['contexts'][0]['viewport'] = [800, 600]
        self.select('narrow')
        report = self.fixture.freeze('narrow')
        self.assertEqual(report['coverage'], 'incomplete')
        self.assertTrue(any('destination_capture_context_mismatch:' in ' '.join(c['reasons']) for c in report['cases']))
        self.design['destinations'].append({'id': 'unlinked'})
        self.select('added')
        self.assertIn('destination_without_requirement', self.fixture.codes(self.fixture.freeze('added')))


if __name__ == '__main__':
    unittest.main()
