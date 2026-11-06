"""Original bounded packet fixtures; no host, rendered or native qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-accelerator/scripts'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = load('experience_scope_fixture', ROOT / 'tests/test_experience_intent.py')
C = load('experience_scope_context', SCRIPTS / 'context_packets.py')
P = C.P
D = P.intent_helper()
PRODUCT = P.routing_helper('product_intent')


class ExperiencePacketScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'engagement'
        self.spec, self.design = F.fixture()
        self.spec['requirements'].append(F.requirement('metric-a', {'meaning': 'Original governed observation'}, required=False))
        self.spec['requirements'][-1]['product']['suggested_roles'] = ['bi-engineer']
        shared = F.requirement('shared-stop', {'prohibition': 'No external activation'})
        shared['category'] = 'restriction'
        self.spec['requirements'].append(shared)
        delegation = F.requirement('direction-delegation', {'delegation_scope': 'experience_direction'})
        self.spec['requirements'].append(delegation)
        self.spec['product']['experience_intent']['delegation_requirement_id'] = delegation['id']
        self.design['experience_intent_handoff']['context'] = F.E.context(self.spec)

    def install(self, *, selected=True):
        P.init(self.root, 'Original bounded investigation', 'enhancement', 'app', branding='none', context_policy='bounded-context-v1')
        project = P.load_project(self.root)[1]
        for key in ('stage_gate_policy', 'workflow_quality_policy', 'experience_intent_policy'):
            project.pop(key, None)  # This fixture isolates packet mechanics.
        P.write_json(self.root / 'project.json', project, replace=True)
        starter = D.starter(['app'], 'none')
        starter.update({k: copy.deepcopy(v) for k, v in self.spec.items() if k != 'selections'})
        starter['selections'][0].update(design_path='contracts/design.json', brand_path='contracts/brand.json')
        self.design['brand_contract'] = 'contracts/brand.json'
        self.spec = starter
        (self.root / 'inputs/request.md').write_text('Original request: inspect records without losing governed scope.\n')
        (self.root / 'inputs/observations.txt').write_text('Original independent observation.\n')
        for path, value in [('contracts/design.json', self.design), ('contracts/query.json', {'query': 'records'}),
                            ('contracts/brand.json', {}), ('contracts/spec.json', self.spec)]:
            P.write_json(self.root / path, value, replace=(self.root / path).exists())
        if selected:
            D.select(self.root, self.root / 'contracts/spec.json', 'contracts/selected.json')
            PRODUCT.generate(self.root, 'deliverables/north-star.md')
        else:
            project['design_intent_draft'] = 'contracts/spec.json'
            P.write_json(self.root / 'project.json', project, replace=True)
        return D.check(self.root)

    def prepare(self, scope=('metric-a',), role='bi-engineer'):
        inputs = ['inputs/observations.txt']
        assignment = {'schema_version': 1, 'task_id': 'bounded-experience-task', 'domain_id': 'original',
            'stage': 'app' if role == 'app-engineer' else 'dashboard', 'role': role,
            'scope_ids': list(scope), 'objective': 'Inspect the assigned original observation',
            'outputs': ['deliverables/result.md'], 'acceptance': ['Retain original scope'],
            'input_bindings': {p: P.digest((self.root / p).read_bytes()) for p in inputs},
            'dependencies': {}, 'unknowns': [], 'authoring_mode': 'provisional'}
        # This fixture tests projection/freshness; strict A–F integration has its
        # own unchanged suite. No real authoring or host execution occurs here.
        with patch.object(P, 'stage_packet_gate', return_value={'required': False}):
            packet = P.packet(self.root, role, inputs, self.root / 'tasks/work.json', assignment)
        request = {'schema_version': 1, 'kind': 'analyst_context_request', 'packet': {'path': 'tasks/work.json',
            'sha256': P.digest((self.root / 'tasks/work.json').read_bytes())}, 'mode': 'initial',
            'summary': 'Check the assigned observation.', 'decisions': [], 'constraints': ['Preserve governed meaning'],
            'stop_conditions': packet['stop_conditions'], 'shared_constraint_ids': ['shared-stop'],
            'classification': 'internal', 'disclosure': {'allowed_classifications': ['internal'], 'review_ref': 'original fixture'},
            'evidence': [{'id': 'observation', 'path': inputs[0], 'sha256': assignment['input_bindings'][inputs[0]],
                'classification': 'internal', 'purpose': 'Original evidence', 'ranges': [[1, 1]], 'review_original': True}]}
        with patch.object(P, 'stage_packet_gate', return_value={'required': False}):
            raw, receipt = C.prepare(self.root, request)
        return packet, json.loads(raw[len(C.INSTRUCTIONS.encode()):]), raw, receipt

    def test_bi_engineer_receives_exact_shared_meaning_and_delegation(self):
        state = self.install()
        scoped = D.packet_context(self.root, 'bi-engineer', bounded=True, scope_ids=['metric-a'])
        summary = scoped['experience_summary']
        self.assertEqual(summary['promises'][0]['promise'], self.spec['requirements'][0]['value']['promise'])
        self.assertEqual(summary['delegation']['value'], {'delegation_scope': 'experience_direction'})
        self.assertEqual(summary['delegation']['basis'], 'user_statement')
        self.assertEqual(summary['source'], state['selected'])
        self.assertEqual({r['id'] for r in scoped['requirements']}, {'metric-a', 'shared-stop'})
        self.assertFalse(summary['claims_authenticated'])

    def test_hybrid_adjustments_reach_affected_worker_without_copying_other_designs(self):
        amendment = {'option_id': 'option-2', 'source_locator': 'Evidence inspection state',
                     'application': 'Keep this requested inspection flow.', 'journey_ids': ['inspect-record']}
        self.design['experience_handoff'] = {'selection_adjustments': {
            'response_path': 'inputs/request.md', 'elements': [amendment]}}
        self.install()
        _, task, raw, _ = self.prepare(scope=['record-investigation'], role='app-engineer')
        actual = task['product_constraints']['experience_summary']['selection_adjustments'][0]
        self.assertEqual(actual['selected_element'], amendment)
        self.assertEqual(actual['row_sha256'], P.digest(P.canonical(amendment)))
        other = D.packet_context(self.root, 'bi-engineer', bounded=True, scope_ids=['metric-a'])
        pointer = other['experience_summary']['selection_adjustments'][0]
        self.assertNotIn('selected_element', pointer)
        self.assertTrue(pointer['read_before_changing_linked_journey'])
        self.assertLess(len(raw), C.DEFAULT_BYTES)

    def test_full_scoped_promise_keeps_delegation_and_all_global_restrictions(self):
        state = self.install()
        experience = D.experience_packet_scope(self.root, state)
        selected = D.project_requirements(state['requirements'], 'app-engineer', ['record-investigation'], experience=experience)
        self.assertEqual({r['id'] for r in selected}, {'record-investigation', 'direction-delegation', 'shared-stop'})
        self.assertEqual(selected[0], self.spec['requirements'][0])

    def test_linked_destination_scope_selects_relevant_behavior(self):
        state = self.install()
        experience = D.experience_packet_scope(self.root, state)
        selected = D.project_requirements(state['requirements'], 'bi-engineer', ['detail'], experience=experience)
        self.assertIn('record-investigation', {r['id'] for r in selected})
        self.assertIn('direction-delegation', {r['id'] for r in selected})

    def test_explicit_role_assignment_does_not_pull_all_creative_alternatives(self):
        alternate = F.requirement('narrative-hypothesis', {'kind': 'experience_mode', 'mode': 'narrative',
            'rationale': 'An unchosen alternative'}, basis='recommendation', disposition='unresolved', required=False)
        alternate['product']['suggested_roles'] = ['app-engineer']
        self.spec['requirements'].append(alternate)
        self.spec['product']['experience_intent']['mode_requirement_ids'].append(alternate['id'])
        self.install()
        scoped = D.packet_context(self.root, 'app-engineer', bounded=True, scope_ids=['metric-a'])
        self.assertNotIn(alternate['id'], {r['id'] for r in scoped['requirements']})
        self.assertEqual([r['id'] for r in scoped['experience_summary']['selected_modes']], ['workspace-hypothesis'])
        self.assertIn(alternate['id'], {r['id'] for r in scoped['experience_summary']['original_requirements']})

    def test_original_pointers_and_hashes_match_full_canonical_rows(self):
        state = self.install()
        summary = D.experience_packet_scope(self.root, state)['summary']
        record = P.read_json(self.root / summary['source']['path'])[0]
        for original in summary['original_requirements']:
            position = int(original['pointer'].rsplit('/', 1)[1])
            row = record['spec']['requirements'][position]
            self.assertEqual(row['id'], original['id'])
            self.assertEqual(P.digest(P.canonical(row)), original['row_sha256'])

    def test_preselection_draft_supplies_meaning_without_claiming_a_selected_brief(self):
        state = self.install(selected=False)
        product = PRODUCT.packet_context(self.root, 'app-designer', bounded=True, scope_ids=['record-investigation'])
        self.assertIsNone(product['selected_intent'])
        self.assertIsNone(product['brief'])
        self.assertFalse(product['enabled'])
        self.assertEqual(product['experience_summary'], D.experience_packet_scope(self.root, state)['summary'])
        self.assertEqual(product['experience_summary']['source']['path'], 'contracts/spec.json')
        self.assertEqual(product['experience_summary']['selected_modes'], [])
        self.assertEqual(product['experience_summary']['design_pins'], [])
        self.assertFalse(product['experience_summary']['claims_authenticated'])
        self.assertTrue(all(r['pointer'].startswith('/requirements/') for r in
                            product['experience_summary']['original_requirements']))

    def test_all_callers_share_exact_projection_and_task_remains_bounded(self):
        self.install()
        design = D.packet_context(self.root, 'bi-engineer', bounded=True, scope_ids=['metric-a'])
        product = PRODUCT.packet_context(self.root, 'bi-engineer', bounded=True, scope_ids=['metric-a'])
        packet, task, raw, receipt = self.prepare()
        self.assertEqual(design['experience_summary'], product['experience_summary'])
        self.assertEqual(design['experience_summary'], packet['design_context']['experience_summary'])
        self.assertEqual(design['experience_summary'], task['product_constraints']['experience_summary'])
        self.assertIn('shared-stop', {r['id'] for r in task['requirements']})
        self.assertLess(len(raw), C.DEFAULT_BYTES)
        self.assertFalse(receipt['dispatch_authorized'])

    def test_near_limit_index_can_narrow_without_truncating_scoped_rows(self):
        for i in range(15):
            alternate = F.requirement('alternative-' + str(i), {'kind': 'experience_mode', 'mode': 'custom',
                'custom_label': 'Alternative ' + str(i), 'rationale': 'Distinct proposed treatment ' + 'x' * 1850},
                basis='recommendation', disposition='unresolved', required=False)
            alternate['product']['suggested_roles'] = ['app-engineer', 'bi-engineer']
            alternate['product']['acceptance'] = ['Retain a complete original acceptance ' + 'y' * 1250]
            self.spec['requirements'].append(alternate)
            self.spec['product']['experience_intent']['mode_requirement_ids'].append(alternate['id'])
        indexed = [r for r in self.spec['requirements'] if r['id'] != 'metric-a' and r['id'] != 'shared-stop']
        self.assertGreater(len(P.canonical(indexed)), 55000)
        self.install()
        _, task, raw, _ = self.prepare(scope=['record-investigation'], role='app-engineer')
        row = next(r for r in task['requirements'] if r['id'] == 'record-investigation')
        self.assertEqual(row, self.spec['requirements'][0])
        self.assertNotIn('alternative-0', {r['id'] for r in task['requirements']})
        self.assertLess(len(raw), C.DEFAULT_BYTES)

    def test_changed_selected_design_is_not_relabelled_as_current(self):
        state = self.install()
        design = self.root / 'contracts/design.json'
        value = P.read_json(design)[0]
        value['experience_intent_handoff']['selected_mode_ids'] = []
        P.write_json(design, value, replace=True)
        with self.assertRaisesRegex(ValueError, 'experience_design_changed'):
            D.experience_packet_scope(self.root, state)

    def test_draft_pin_comes_from_the_same_buffer_as_the_projection(self):
        state = self.install(selected=False)
        original_read = D.P.read_json
        expected, observed = {}, set()
        def read_then_change(path):
            value, raw = original_read(path)
            name = str(Path(path).relative_to(self.root))
            if name == 'contracts/spec.json' and name not in observed:
                observed.add(name)
                expected[name] = P.digest(raw)
                changed = copy.deepcopy(value)
                changed['requirements'][0]['value']['promise'] = 'Changed after the read'
                Path(path).write_text(json.dumps(changed))
            return value, raw
        with patch.object(D.P, 'read_json', side_effect=read_then_change):
            summary = D.experience_packet_scope(self.root, state)['summary']
        self.assertEqual(summary['source']['sha256'], expected['contracts/spec.json'])
        self.assertEqual(summary['design_pins'], [])
        self.assertEqual(summary['selected_modes'], [])
        self.assertNotEqual(summary['source']['sha256'], P.digest((self.root / 'contracts/spec.json').read_bytes()))
        self.assertEqual(summary['promises'][0]['promise'], self.spec['requirements'][0]['value']['promise'])

    def test_selected_design_pin_uses_the_same_buffer_as_the_projection(self):
        state = self.install()
        original_read = D.P.read_json
        expected = []
        def read_then_change(path):
            value, raw = original_read(path)
            if Path(path) == self.root / 'contracts/design.json' and not expected:
                expected.append(P.digest(raw))
                changed = copy.deepcopy(value)
                changed['experience_intent_handoff']['selected_mode_ids'] = []
                Path(path).write_text(json.dumps(changed))
            return value, raw
        with patch.object(D.P, 'read_json', side_effect=read_then_change):
            summary = D.experience_packet_scope(self.root, state)['summary']
        self.assertEqual(summary['design_pins'][0]['sha256'], expected[0])
        self.assertEqual([r['id'] for r in summary['selected_modes']], ['workspace-hypothesis'])
        with self.assertRaisesRegex(ValueError, 'experience_design_changed'):
            D.experience_packet_scope(self.root, state)

    def test_no_index_keeps_original_projection_and_packet_shape(self):
        self.spec['product'].pop('experience_intent')
        self.design.pop('experience_intent_handoff')
        state = self.install()
        expected = D.project_requirements(state['requirements'], 'app-engineer', ['metric-a'])
        scoped = D.packet_context(self.root, 'app-engineer', bounded=True, scope_ids=['metric-a'])
        self.assertEqual(P.canonical(scoped['requirements']), P.canonical(expected))
        self.assertNotIn('experience_summary', scoped)
        product = PRODUCT.packet_context(self.root, 'app-engineer', bounded=True, scope_ids=['metric-a'])
        self.assertNotIn('experience_summary', product)
        _, task, _, _ = self.prepare(role='app-engineer')
        self.assertNotIn('experience_summary', task['product_constraints'])
        self.assertEqual(P.canonical(task['requirements']), P.canonical(expected))


class StrictPreselectionPacketTests(unittest.TestCase):
    def test_actual_e_designer_packet_uses_adopted_draft_after_valid_d(self):
        integration = load('experience_scope_lifecycle', ROOT / 'tests/test_experience_continuity.py')
        fixture = integration.ExperienceContinuity('test_full_contract_route_preserves_choice_and_all_four_reviews')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        project = integration.P.load_project(fixture.root)[1]
        project['context_policy'] = 'bounded-context-v1'
        integration.P.write_json(fixture.root / 'project.json', project, replace=True)
        flow = fixture.prepare()
        with integration.P.trusted_stage_provider(flow.host):
            flow.through('brief')
            packet = integration.P.packet(fixture.root, 'app-designer', ['inputs/request.md'], None)
        self.assertIn('brief', integration.P.stage_status(fixture.root)['completed_stages'])
        self.assertIsNone(packet['design_context']['selected_intent'])
        self.assertEqual(packet['design_context']['experience_summary']['source']['path'], 'contracts/design-intent.json')
        self.assertEqual(packet['design_context']['experience_summary'], packet['product_context']['experience_summary'])
        self.assertEqual(packet['dispatch_status'], 'not_dispatched')


if __name__ == '__main__':
    unittest.main()
