"""Original local report fixtures; no Report renderer, tenant or publication claims."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
D = P.intent_helper()
R = P.routing_helper('task_routing')
Q = load('report_review', 'skills/omni-artifact-accelerator/scripts/design_review.py')
C = load('report_coverage', 'skills/omni-artifact-accelerator/scripts/destination_coverage.py')
G = load('report_stage_fixture', 'tests/stage_gate_fixture.py')
H = load('report_contract_fixture', 'tests/test_report_contract.py')


def local_target():
    return {'surface': 'report', 'state': 'local', 'document_id': None, 'draft_id': None}


def remote_target():
    return {'surface': 'report', 'state': 'published', 'instance': 'https://target.example.invalid',
            'document_id': 'fixture-report-document', 'draft_id': None,
            'capability_evidence_path': 'evidence/report-capability.json'}


def assignment(role='report-builder', stage='report', output='deliverables/layout.rdlx-json'):
    return {'schema_version': 1, 'task_id': 'build-report', 'domain_id': 'synthetic', 'stage': stage,
        'role': role, 'scope_ids': ['one-page'], 'objective': 'Create a synthetic report candidate',
        'outputs': [output], 'acceptance': ['Retain selected report geometry and independent totals'],
        'input_bindings': {'contracts/report.json': 'a' * 64}, 'dependencies': {},
        'unknowns': ['Native Report rendering is not tested'], 'authoring_mode': 'provisional'}


class ReportRoutingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.base = Path(folder.name).resolve()
        self.root = self.base / 'report'
        P.init(self.root, 'Synthetic one-page report', 'net-new', 'report', 'none')

    def test_unrelated_sources_do_not_load_report_projection_helpers(self):
        # A file-loaded analyst_project need not be registered under its normal
        # import name merely to plan an engagement without report-source evidence.
        with patch.object(P, 'routing_helper', side_effect=AssertionError('Unexpected projection import')):
            self.assertEqual(P.report_source_scope(*P.load_project(self.root)), set())
        path = 'inputs/unrelated.json'
        P.write_json(self.root / path, {'schema_version': 1, 'kind': 'synthetic_non_report_evidence'})
        P.register(self.root, 'sources', path, 'Synthetic unrelated evidence')
        with patch.object(P, 'routing_helper', side_effect=AssertionError('Unexpected projection import')):
            self.assertEqual(P.report_source_scope(*P.load_project(self.root)), set())
            self.assertFalse(P.businessobjects_scope(*P.load_project(self.root)))
        routing_helper = P.routing_helper

        def no_visual_projection(name='task_routing'):
            if name == 'visual_workflow':
                raise AssertionError('Unexpected projection import')
            return routing_helper(name)

        # Exercise the public planning path, not just either specialist detector.
        with patch.object(P, 'routing_helper', side_effect=no_visual_projection):
            result = P.plan(self.root)
            self.assertEqual(result['kind'], 'suggested_role_plan')
            self.assertFalse(result['agents_dispatched'])
            self.assertNotIn('businessobjects-migrator', {r['role'] for r in result['roles']})
            P.write_json(self.root / path, {'kind': 'changed'}, replace=True)
            with self.assertRaisesRegex(ValueError, 'registered source changed'):
                P.plan(self.root)

    def test_report_is_distinct_and_every_new_mode_keeps_stage_gates(self):
        for mode in ('net-new', 'migration', 'enhancement'):
            root = self.base / mode
            P.init(root, 'Synthetic report', mode, 'report', 'none')
            project = P.load_project(root)[1]
            self.assertEqual(project['surfaces'], ['report'])
            self.assertEqual(project['stage_gate_policy'], 'data-first-v1')
            self.assertEqual(project['workflow_quality_policy'], 'experience-evidence-v1')
            self.assertTrue(P.stage_status(root)['required'])
            with self.assertRaises(ValueError): P.stage_require(root, 'build')
        legacy = self.base / 'both'
        P.init(legacy, 'Synthetic pair', 'net-new', 'both', 'none')
        self.assertEqual(P.load_project(legacy)[1]['surfaces'], ['dashboard', 'app'])
        self.assertEqual(D.starter(['report'])['selections'][0]['surface'], 'report')
        # Reports are new: a hand-edited project cannot invoke the historical exemption.
        project = P.load_project(self.root)[1]
        del project['stage_gate_policy']
        P.write_json(self.root / 'project.json', project, replace=True)
        with self.assertRaisesRegex(ValueError, 'report_requires_current'):
            P.load_project(self.root)

    def test_report_roles_keep_independent_semantic_security_and_experience_review(self):
        reviewed = R.route_reviews(R.validate_assignment(assignment()), changes=['report'])
        self.assertEqual({r['id'] for r in reviewed['reviews']}, {'semantic', 'security', 'experience'})
        self.assertEqual({r['role'] for r in reviewed['reviews']}, {'qa-analyst'})
        self.assertNotIn('report-builder', {r['role'] for r in reviewed['reviews']})
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            R.validate_assignment(assignment(stage='discovery'))
        owners = P.routing_helper('delivery_workflow').ROLE_OWNERS
        self.assertIn('report-designer', owners['experience'])
        self.assertIn('report-designer', owners['creative_review'])
        self.assertIn('report-builder', owners['engineering'])

    def test_report_builder_json_and_disguised_bi_definitions_cannot_build_early(self):
        life = G.Lifecycle(self.root, P)
        life.stage('access')
        # An ordinary read-only analysis packet is possible after access.
        packet = P.packet(self.root, 'bi-engineer', ['contracts/metrics.json'], None)
        self.assertFalse(packet['external_mutations_authorized'])
        for role, stage, output in [('report-builder', 'report', 'deliverables/report.json'),
                                    ('bi-engineer', 'report', 'deliverables/report.json'),
                                    *[('bi-engineer', 'discovery', 'deliverables/source' + suffix)
                                      for suffix in ('.rdlx-json', '.RDL', '.rdlc')]]:
            with self.subTest(role=role, output=output), self.assertRaisesRegex(ValueError, 'stage_gate_'):
                P.stage_packet_gate(self.root, role, {'stage': stage, 'outputs': [output],
                                                     'authoring_mode': 'provisional'})
        historical = self.base / 'historical'
        P.init(historical, 'Synthetic historical App', 'enhancement', 'app', 'none')
        project = P.load_project(historical)[1]
        del project['stage_gate_policy']
        del project['workflow_quality_policy']
        P.write_json(historical / 'project.json', project, replace=True)
        self.assertFalse(P.stage_packet_gate(historical, 'bi-engineer')['required'])
        with self.assertRaisesRegex(ValueError, 'stage_gate_report_build_requires_current_policy'):
            P.stage_packet_gate(historical, 'bi-engineer', {'stage': 'discovery', 'outputs': ['deliverables/print.rdl']})

    def test_three_options_do_not_grant_report_build_before_actual_choice(self):
        life = G.Lifecycle(self.root, P)
        life.through('options')
        status = P.stage_status(self.root)
        self.assertEqual(status['next_stage'], 'choice')
        self.assertEqual(len(status['choice_bindings']), 3)
        with self.assertRaisesRegex(ValueError, 'stage_gate_'):
            P.stage_packet_gate(self.root, 'report-builder', assignment(output='deliverables/report.json'))
        with self.assertRaisesRegex(ValueError, 'stage_gate_'):
            P.stage_require(self.root, 'design')
        # The report designer can prepare concepts without conferring build authority.
        packet = P.packet(self.root, 'report-designer', ['contracts/metrics.json'], None)
        self.assertEqual(packet['skill'], 'omni-report-designer')
        self.assertFalse(packet['external_mutations_authorized'])
        roles = {r['role'] for r in P.plan(self.root)['roles']}
        self.assertNotIn('app-designer', roles)
        self.assertNotIn('dashboard-designer', roles)

    def test_selected_report_handoff_allows_build_and_query_drift_blocks_it(self):
        life = G.Lifecycle(self.root, P)
        original_handoff = G.selected_handoff

        def report_handoff(root, project_api, option, version=None):
            path = original_handoff(root, project_api, option, version)
            spec = copy.deepcopy(D.load_selected(root)['spec'])
            design = P.read_json(root / path)[0]
            design['report_contract'] = H.fixture()
            design['report_contract']['capabilities'][0]['requirement_ids'] = [
                r['id'] for r in spec['requirements'] if 'report' in r['surfaces']]
            P.write_json(root / 'inputs/query.json', {'fixture_only': True, 'rows': 0})
            (root / 'inputs/decision.txt').write_text('Synthetic report preferences; no actual user approval.')
            P.write_json(root / path, design, replace=True)
            spec_path = 'contracts/report-selected-spec.json'
            P.write_json(root / spec_path, spec)
            D.select(root, root / spec_path, 'contracts/report-selected-intent.json')
            G.refresh_request_review(root, project_api)
            return path

        # Only the synthetic fixture is wrapped; actual gate/intent validation executes.
        with P.trusted_stage_provider(life.host), patch.object(G, 'selected_handoff', report_handoff):
            life.through('design')
            result = P.stage_packet_gate(self.root, 'report-builder', assignment())
            self.assertIn('design', result['completed_stages'])
            self.assertFalse(result['external_mutations_authorized'])
            self.assertFalse(result['release_ready'])
            self.assertNotIn('app-engineer', {r['role'] for r in P.plan(self.root)['roles']})
            P.write_json(self.root / 'inputs/query.json', {'fixture_only': True, 'rows': 1}, replace=True)
            with self.assertRaisesRegex(ValueError, 'stage_gate_'):
                P.stage_packet_gate(self.root, 'report-builder', assignment())

    def test_remote_reports_are_observations_with_pinned_capability_not_draft_authority(self):
        D.validate_report_target(local_target())
        D.validate_report_target(remote_target())
        Q.target(remote_target(), 'report')
        for changed in ({**remote_target(), 'state': 'draft', 'draft_id': 'invented'},
                        {k: v for k, v in remote_target().items() if k != 'capability_evidence_path'},
                        {**remote_target(), 'capability_evidence_path': '../capability.json'},
                        {**remote_target(), 'report_id': 'invented-second-id'},
                        {**remote_target(), 'instance': 'https://user:secret@target.example.invalid'},
                        {**remote_target(), 'instance': 'https://target.example.invalid?token=value'},
                        {**local_target(), 'document_id': 'unverified-remote-document'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError): D.validate_report_target(changed)
        spec = D.starter(['report'], 'none')
        spec['selections'][0].update(candidate_path='deliverables/report.rdlx-json', target=remote_target())
        D.validate(spec, P.load_project(self.root)[1])
        self.assertIn('evidence/report-capability.json', D.references(spec))
        with self.assertRaisesRegex(ValueError, 'missing engagement file'):
            D.pin(self.root, 'evidence/report-capability.json')
        review = {'dependencies': [{'kind': 'candidate', 'surface': 'report', 'path': 'deliverables/report.rdlx-json',
                                   'target': remote_target()}], 'scope': {}, 'captures': []}
        self.assertIn('evidence/report-capability.json', Q.references(review))

    def test_one_page_report_has_real_single_destination_lifecycle_coverage(self):
        design = {'destinations': [{'id': 'summary', 'kind': 'page'}], 'journeys': [{
            'id': 'render-summary', 'path': ['summary'], 'action': 'Render the selected parameters',
            'start_state': 'configured', 'end_state': 'rendered', 'retained_context': 'Parameter selection',
            'return_behavior': 'Return to the same report parameters'}]}
        P.write_json(self.root / 'contracts/one-page.json', design)
        selected = {'path': 'contracts/selected.json', 'sha256': 'a' * 64}
        requirement = {'id': 'summary-page', 'required': True, 'disposition': 'selected', 'purpose': 'One-page summary',
            'surfaces': ['report'], 'delivery': {'destinations': ['summary'], 'journeys': ['render-summary']},
            'contexts': [{'id': 'paper', 'appearance': 'light', 'state': 'rendered', 'applicability': [
                {'kind': kind, 'id': ident, 'surface': 'report', 'lanes': {'craft': {'status': 'required'}}}
                for kind, ident in [('destination', 'summary'), ('journey', 'render-summary')]]}]}
        state = {'selected': selected, 'status': 'consistent', 'open_questions': [], 'findings': [],
                 'selections': [{'surface': 'report', 'design_path': 'contracts/one-page.json'}],
                 'requirements': [requirement]}
        spec = {'intent': selected, 'scope': {'surfaces': ['report'], 'required_lanes': ['craft'],
                                            'coverage': {'mode': 'whole_experience'}}}
        derived = C.derive(self.root, spec, state, P)
        self.assertEqual(derived['gaps'], [])
        self.assertEqual(len(derived['obligations']), 2)
        self.assertFalse(derived['claims_authenticated'])
        # The report-specific exception does not weaken App journey validation.
        changed_state = copy.deepcopy(state); changed_spec = copy.deepcopy(spec)
        changed_state['selections'][0]['surface'] = 'app'
        changed_state['requirements'][0]['surfaces'] = ['app']
        for item in changed_state['requirements'][0]['contexts'][0]['applicability']: item['surface'] = 'app'
        changed_spec['scope']['surfaces'] = ['app']
        self.assertIn('destination_inventory_invalid', {g['code'] for g in C.derive(self.root, changed_spec, changed_state, P)['gaps']})

    def test_report_visual_requirements_select_only_report_items(self):
        W = P.routing_helper('visual_workflow')
        req = {'surface': ['report', 'app'], 'items': [
            {'asset_key': 'printed', 'disposition': 'migrate', 'target_surfaces': ['report']},
            {'asset_key': 'interactive', 'disposition': 'migrate', 'target_surfaces': ['app']},
            {'asset_key': 'deferred', 'disposition': 'defer', 'target_surfaces': ['report']}]}
        self.assertEqual([x['asset_key'] for x in W.surface_items(req, 'report')], ['printed'])
        candidate = self.root / 'deliverables/candidate.json'; P.write_json(candidate, {'surface': 'app'})
        path = 'contracts/visuals.json'; P.write_json(self.root / path, {})
        with patch.object(W, 'requirements', return_value=(self.root, {'surface': ['report'], 'items': []})):
            with self.assertRaisesRegex(ValueError, 'report_candidate_surface_required'):
                W.coverage(self.root, path, 'deliverables/candidate.json', [], 'evidence/coverage.json')
        self.assertFalse((self.root / 'evidence/coverage.json').exists())


if __name__ == '__main__': unittest.main()
