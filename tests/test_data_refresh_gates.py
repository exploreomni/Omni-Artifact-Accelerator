"""Synthetic refresh decisions through real gates; no user or native attestation."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load('refresh_gate_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = load('refresh_gate_fixture', 'tests/stage_gate_fixture.py')
N = P.routing_helper('product_intent')
S = P.routing_helper('stage_gates')


class DataRefreshGates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic garden refresh investigation', 'net-new', 'app', 'none')
        self.version = 0

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def flow(self, end='design'):
        flow = G.Lifecycle(self.root, P)
        with P.trusted_stage_provider(flow.host):
            flow.through(end)
        return flow

    def discovery(self):
        flow = self.flow('narrative')
        return flow, G.discovery_spec(self.root, P)

    @staticmethod
    def decision(spec):
        ident = spec['product']['data_refresh']['requirement_id']
        return next(row for row in spec['requirements'] if row['id'] == ident)

    @staticmethod
    def periodic():
        return {'kind': 'app_data_refresh', 'mode': 'custom', 'query_cache': 'inherit',
                'refresh_mode': 'interval', 'interval_ms': 60000, 'return_after_ms': None,
                'max_age_ms': None, 'hidden_behavior': 'pause', 'stale_display': 'timestamp',
                'recovery': 'Manual retry; clear denied or changed-scope results.'}

    def record_discovery(self, flow, spec):
        # Bypass the convenience fixture's default-answer insertion, not a gate.
        # Every reply in these files is explicitly synthetic test evidence.
        self.version += 1
        path = 'contracts/refresh-discovery-' + str(self.version) + '.json'
        draft = P.load_project(self.root)[1]['design_intent_draft']
        self.write(draft, spec)
        self.write(path, spec)
        G.refresh_request_review(self.root, P)
        return P.stage_record(self.root, {'stage': 'brief', 'discovery_version': 1,
            'evidence': {'brief': flow.evidence('refresh-brief-' + str(self.version)), 'intent': path}})

    def choose_and_design(self, flow):
        with P.trusted_stage_provider(flow.host):
            flow.stage('options')
            binding = P.stage_status(self.root)['choice_bindings']['option-1']
            receipt = 'synthetic-refresh-choice-not-real-user'
            flow.host.grants[(P.canonical(binding), receipt)] = 'fixture-user'
            P.stage_record(self.root, {'stage': 'choice', 'option_id': 'option-1', 'receipt_ref': receipt})
            flow.stage('design')
            return P.stage_require(self.root, 'build')

    def select_spec(self, spec, tag):
        path = 'contracts/refresh-selected-spec-' + tag + '.json'
        self.write(path, spec)
        P.intent_helper().select(self.root, self.root / path, 'contracts/refresh-selected-' + tag + '.json')
        G.refresh_request_review(self.root, P)

    def test_missing_interview_rejects_d_and_blocks_concepts_and_build(self):
        flow, spec = self.discovery()
        ident = spec['product'].pop('data_refresh')['requirement_id']
        spec['requirements'] = [row for row in spec['requirements'] if row['id'] != ident]
        with self.assertRaisesRegex(ValueError, 'data_refresh_interview_required'):
            self.record_discovery(flow, spec)
        self.assertEqual(P.stage_status(self.root)['completed_stages'], ['access', 'analysis', 'narrative'])
        with P.trusted_stage_provider(flow.host):
            for action in ('options', 'build'):
                with self.subTest(action=action), self.assertRaisesRegex(ValueError, 'predecessor_incomplete'):
                    P.stage_require(self.root, action)

    def test_unanswered_discovery_remains_open_before_options_or_build(self):
        flow, spec = self.discovery()
        row = self.decision(spec)
        row.update(origin='proposal', disposition='unresolved', value=None, decision_ref=None)
        row['product']['basis'] = 'unresolved'
        report = self.record_discovery(flow, spec)
        self.assertEqual(report['next_stage'], 'brief')
        self.assertEqual(report['data_refresh']['status'], 'unresolved')
        self.assertIn('data_refresh_interview_unresolved', report['findings'])
        with P.trusted_stage_provider(flow.host):
            for action in ('options', 'build'):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    P.stage_require(self.root, action)
        self.assertTrue(any('cache' in q for q in P.intent_helper().check(self.root)['open_questions']))

    def test_explicit_no_custom_policy_reaches_selected_design_without_expiry(self):
        flow = self.flow()
        with P.trusted_stage_provider(flow.host):
            status = P.stage_require(self.root, 'build')
        self.assertEqual(status['next_stage'], 'candidate')
        self.assertEqual(status['data_refresh']['status'], 'ready')
        policy = status['data_refresh']['policy']
        self.assertEqual((policy['query_cache'], policy['refresh_mode']), ('inherit', 'manual'))
        for key in ('interval_ms', 'return_after_ms', 'max_age_ms'):
            self.assertIsNone(policy[key])
        selected = P.intent_helper().load_selected(self.root)['spec']
        design = P.read_json(self.root / selected['selections'][0]['design_path'])[0]
        self.assertEqual(design['data_refresh_handoff']['context'], N.refresh_context(selected))
        brief = next(e for e in P.read_json(self.root / S.JOURNAL)[0]['events'] if e['stage'] == 'brief')
        self.assertEqual(brief['payload']['data_refresh_version'], 1)

    def test_periodic_refresh_does_not_require_expiry_or_cache_bypass(self):
        flow, spec = self.discovery()
        self.decision(spec)['value'] = self.periodic()
        self.write('inputs/refresh-fixture.json', {'fixture_only': True,
            'response': 'Refresh every minute while visible, keep Omni caching and impose no expiry.'})
        self.record_discovery(flow, spec)
        result = self.choose_and_design(flow)
        policy = result['data_refresh']['policy']
        self.assertEqual(policy['refresh_mode'], 'interval')
        self.assertEqual(policy['interval_ms'], 60000)
        self.assertEqual(policy['query_cache'], 'inherit')
        self.assertEqual(policy['hidden_behavior'], 'pause')
        self.assertIsNone(policy['max_age_ms'])
        self.assertIsNone(policy['return_after_ms'])

    def test_changed_selected_policy_stales_d_choice_and_existing_packet(self):
        flow = self.flow()
        N.generate(self.root, 'deliverables/refresh-north-star.md')
        with P.trusted_stage_provider(flow.host):
            before = P.stage_status(self.root)
            P.packet(self.root, 'app-engineer', ['contracts/metrics.json'], self.root / 'tasks/refresh-old.json')
            journal = P.read_json(self.root / S.JOURNAL)[0]
            spec = P.intent_helper().load_selected(self.root)['spec']
            self.decision(spec)['value'] = self.periodic()
            self.select_spec(spec, 'changed')
            after = P.stage_status(self.root)
            self.assertIn('stage_gate_data_refresh_changed_reopen_brief', after['findings'])
            self.assertEqual(after['next_stage'], 'brief')
            self.assertNotIn('choice', after['completed_stages'])
            self.assertNotEqual(after['stage_bindings'], before['stage_bindings'])
            self.assertEqual(P.read_json(self.root / S.JOURNAL)[0], journal)
            self.assertEqual(P.packet_check(self.root, 'tasks/refresh-old.json')['status'], 'inconsistent')
            for action in ('options', 'design', 'build'):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    P.stage_require(self.root, action)

    def test_missing_or_stale_design_handoff_cannot_open_build(self):
        flow = self.flow('choice')
        with P.trusted_stage_provider(flow.host):
            path = G.selected_handoff(self.root, P, {'evidence': 'evidence/concept-option-1.json'})
            original = P.read_json(self.root / path)[0]
            for kind, message in [('missing', 'design_handoff_required'), ('stale', 'design_policy_changed')]:
                design = copy.deepcopy(original)
                if kind == 'missing':
                    del design['data_refresh_handoff']
                else:
                    design['data_refresh_handoff']['context']['requirements'][0]['value'] = self.periodic()
                design_path = 'contracts/refresh-design-' + kind + '.json'
                self.write(design_path, design)
                spec = P.intent_helper().load_selected(self.root)['spec']
                for selection in spec['selections']:
                    selection['design_path'] = design_path
                self.select_spec(spec, kind)
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, message):
                    P.stage_record(self.root, {'stage': 'design', 'resolved': True,
                        'evidence': {'design': design_path}})
                with self.assertRaises(ValueError):
                    P.stage_require(self.root, 'build')
            flow.stage('design')
            P.stage_require(self.root, 'build')

    def test_specialist_packets_carry_exact_canonical_refresh_decision(self):
        flow = self.flow()
        N.generate(self.root, 'deliverables/refresh-north-star.md')
        spec = P.intent_helper().load_selected(self.root)['spec']
        expected = N.refresh_context(spec)
        with P.trusted_stage_provider(flow.host):
            for role in ('product-owner', 'app-engineer', 'bi-engineer', 'qa-analyst'):
                with self.subTest(role=role):
                    path = 'tasks/refresh-' + role + '.json'
                    packet = P.packet(self.root, role, ['contracts/metrics.json'], self.root / path)
                    self.assertEqual(packet['design_context']['data_refresh_context'], expected)
                    self.assertEqual(packet['design_context']['data_refresh']['policy'], N.refresh_report(spec)['policy'])
                    self.assertEqual(P.packet_check(self.root, path)['status'], 'consistent')

    def test_proposals_cannot_fake_no_custom_or_static_not_applicable_answer(self):
        flow, spec = self.discovery()
        row = self.decision(spec)
        row.update(origin='proposal', disposition='selected')
        row['product']['basis'] = 'recommendation'
        choices = [{'kind': 'app_data_refresh', 'mode': 'no_custom_policy'},
                   {'kind': 'app_data_refresh', 'mode': 'not_applicable',
                    'rationale': 'Agent proposes a static display; no actual user scope decision.'}]
        for value in choices:
            with self.subTest(mode=value['mode']):
                row['value'] = value
                report = self.record_discovery(flow, spec)
                self.assertEqual(report['data_refresh']['status'], 'unresolved')
                self.assertIn('data_refresh_actual_answer_or_delegation_required',
                              [f['code'] for f in N.refresh_report(spec)['findings']])
                with self.assertRaises(ValueError):
                    P.stage_require(self.root, 'options')

    def test_reused_answer_and_explicit_scoped_delegation_can_resolve_d(self):
        flow, spec = self.discovery()
        row = self.decision(spec)
        row.update(origin='reused')
        row['product']['basis'] = 'reused_decision'
        report = self.record_discovery(flow, spec)
        self.assertEqual(report['data_refresh']['status'], 'ready')
        P.stage_require(self.root, 'options')
        delegate = copy.deepcopy(row)
        delegate.update(id='refresh-delegation', origin='user', purpose='Synthetic explicit delegation',
                        value={'delegation_scope': 'app_data_refresh'})
        delegate['product']['basis'] = 'user_statement'
        spec['requirements'].append(delegate)
        spec['product']['data_refresh']['delegation_requirement_id'] = delegate['id']
        row.update(origin='proposal')
        row['product']['basis'] = 'recommendation'
        # Preserve earlier evidence, which remains immutable after D.
        new_note = 'inputs/refresh-delegation-fixture.json'
        self.write(new_note, {'fixture_only': True,
            'response': 'Explicitly delegate only this App refresh-policy choice.'})
        spec['product']['note_paths'].append(new_note)
        for req in (row, delegate):
            req['decision_ref'] = new_note
            req['product']['source_refs'] = [new_note]
        report = self.record_discovery(flow, spec)
        self.assertEqual(report['data_refresh']['status'], 'ready')
        P.stage_require(self.root, 'options')
        invalid = copy.deepcopy(spec)
        invalid['requirements'][-1]['value'] = {'delegation_scope': 'experience_quality'}
        with self.assertRaisesRegex(ValueError, 'scoped_delegation_required'):
            N.refresh_report(invalid)

    def test_explicit_bypass_and_expiry_are_distinct_validated_choices(self):
        value = dict(self.periodic(), query_cache='bypass', refresh_mode='interval_and_return',
                     return_after_ms=120000, max_age_ms=300000, stale_display='withhold')
        result = N.R.policy(value)
        self.assertEqual(result['query_cache'], 'bypass')
        self.assertEqual(result['interval_ms'], 60000)
        self.assertEqual(result['return_after_ms'], 120000)
        self.assertEqual(result['max_age_ms'], 300000)
        self.assertEqual(result['stale_display'], 'withhold')
        invalid = [({'interval_ms': None}, 'interval_requires_selected_trigger'),
                   ({'interval_ms': 0}, 'invalid_interval_ms'),
                   ({'interval_ms': -1}, 'invalid_interval_ms'),
                   ({'interval_ms': True}, 'invalid_interval_ms'),
                   ({'interval_ms': 1.5}, 'invalid_interval_ms'),
                   ({'return_after_ms': None}, 'return_threshold_requires_selected_trigger'),
                   ({'max_age_ms': -1}, 'invalid_max_age_ms'),
                   ({'max_age_ms': True}, 'invalid_max_age_ms'),
                   ({'max_age_ms': None}, 'withholding_requires_expiry'),
                   ({'stale_display': 'timestamp'}, 'expiry_requires_visible_stale_state')]
        for changes, message in invalid:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, message):
                N.R.policy(dict(value, **changes))
        with self.assertRaisesRegex(ValueError, 'no_custom_policy_has_overrides'):
            N.R.policy({'kind': 'app_data_refresh', 'mode': 'no_custom_policy', 'query_cache': 'bypass'})

    def test_historical_selected_continuation_reports_refresh_not_assessed(self):
        legacy = Path(self.temp.name).resolve() / 'historical'
        P.init(legacy, 'Historical selected synthetic App', 'enhancement', 'app', 'none')
        G.pre_policy_project(legacy, P)
        P.intent_helper().select(legacy, legacy / 'contracts/design-intent.json', 'contracts/selected-old.json')
        flow = G.Lifecycle(legacy, P, historical=True)
        with P.trusted_stage_provider(flow.host):
            flow.through('design')
            result = P.stage_require(legacy, 'build')
        self.assertTrue(result['historical_selected_continuation'])
        self.assertEqual(result['data_refresh']['status'], 'not_assessed')
        self.assertIsNone(result['data_refresh']['version'])
        self.assertEqual(N.refresh_report(P.intent_helper().load_selected(legacy)['spec'])['status'], 'not_assessed')

    def test_historical_selected_adoption_requires_refresh_handoff_without_quality_marker(self):
        # Use the original historical journal fixture, then adopt through actual
        # selection and stage-record APIs; never remove an adopted policy marker.
        legacy = Path(self.temp.name).resolve() / 'historical-adoption'
        P.init(legacy, 'Historical App adopts a refresh answer', 'enhancement', 'app', 'none')
        G.pre_policy_project(legacy, P)
        P.intent_helper().select(legacy, legacy / 'contracts/design-intent.json', 'contracts/selected-old.json')
        flow = G.Lifecycle(legacy, P, historical=True)
        with P.trusted_stage_provider(flow.host):
            flow.through('design')
            original_events = P.read_json(legacy / S.JOURNAL)[0]['events']
            spec = G.discovery_spec(self.root, P)
            spec['product']['scope'] = 'focused_repair'
            for path in spec['product']['note_paths']:
                (legacy / path).write_bytes((self.root / path).read_bytes())

            def select_design(path, design, version):
                (legacy / path).write_text(json.dumps(design))
                for selection in spec['selections']:
                    selection.update(design_path=path, brand_path=None)
                source = 'contracts/adoption-spec-' + version + '.json'
                (legacy / source).write_text(json.dumps(spec))
                P.intent_helper().select(legacy, legacy / source, 'contracts/adoption-selected-' + version + '.json')

            missing = 'contracts/adoption-design-missing.json'
            select_design(missing, {'destinations': [{'id': 'main'}]}, 'missing')
            snapshot = 'contracts/adoption-discovery.json'
            (legacy / snapshot).write_text(json.dumps(spec))
            discovery = P.stage_record(legacy, {'stage': 'brief', 'discovery_version': 1,
                'evidence': {'brief': flow.evidence('adoption-brief'), 'intent': snapshot}})
            self.assertEqual(discovery['data_refresh']['status'], 'ready')
            self.assertNotIn('workflow_quality_policy', P.load_project(legacy)[1])
            flow.stage('options')
            binding = P.stage_status(legacy)['choice_bindings']['option-1']
            receipt = 'synthetic-adopted-refresh-choice'
            flow.host.grants[(P.canonical(binding), receipt)] = 'fixture-user'
            P.stage_record(legacy, {'stage': 'choice', 'option_id': 'option-1', 'receipt_ref': receipt})
            with self.assertRaisesRegex(ValueError, 'design_handoff_required'):
                P.stage_record(legacy, {'stage': 'design', 'resolved': True, 'evidence': {'design': missing}})
            with self.assertRaises(ValueError):
                P.stage_require(legacy, 'build')

            correct = 'contracts/adoption-design-correct.json'
            design = {'destinations': [{'id': 'main'}], 'data_refresh_handoff': {
                'context': N.refresh_context(spec),
                'implementation': 'Inherit query caching and manual refresh with no display expiry.',
                'qa_cases': ['Check manual retry and access/scope clearing; no unsolicited polling.']}}
            select_design(correct, design, 'correct')
            with self.assertRaisesRegex(ValueError, 'refresh_handoff_must_match_app_design'):
                P.stage_record(legacy, {'stage': 'design', 'resolved': True, 'evidence': {'design': missing}})
            P.stage_record(legacy, {'stage': 'design', 'resolved': True, 'evidence': {'design': correct}})
            self.assertEqual(P.stage_require(legacy, 'build')['data_refresh']['status'], 'ready')
            self.assertNotIn('workflow_quality_policy', P.load_project(legacy)[1])
            events = P.read_json(legacy / S.JOURNAL)[0]['events']
            self.assertEqual(events[:len(original_events)], original_events)

            # An evidence edit cannot inherit the previous build clearance.
            design['data_refresh_handoff']['context']['requirements'][0]['value'] = self.periodic()
            (legacy / correct).write_text(json.dumps(design))
            with self.assertRaises(ValueError):
                P.stage_require(legacy, 'build')


if __name__ == '__main__':
    unittest.main()
