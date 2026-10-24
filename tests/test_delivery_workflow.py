"""Startup, cohort-independent ownership and candidate-bound evidence regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))  # Only this repository's original fixtures; run with -I -S -B.
import test_experience_quality as fixture

W = fixture.D.P.routing_helper('delivery_workflow')
_gate_spec = importlib.util.spec_from_file_location('workflow_gate_fixture', ROOT / 'tests/stage_gate_fixture.py')
G = importlib.util.module_from_spec(_gate_spec)
_gate_spec.loader.exec_module(G)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.DeliveryTests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.root = self.base.root
        project = W.P.load_project(self.root)[1]
        project['stage_gate_policy'] = 'data-first-v1'
        W.P.write_json(self.root / 'project.json', project, replace=True)
        self.base.base.select()
        self.write('inputs/brief.txt', 'Investigate collection changes; preserve evidence and return context.')
        self.write('evidence/request-review.txt', 'Original request compared independently with investigate requirement.')
        self.write('inputs/source-profile.json', {'population': 'Supplied collection observations', 'synthetic': True})
        self.start_request = {'id': 'trial', 'source_mode': 'repository_only', 'entrypoint': 'explicit local skill',
            'brief': 'inputs/brief.txt', 'host': {'name': 'synthetic host', 'execution_mode': 'inline',
                'tools': ['local original helpers'], 'constraints': ['no browser or native calls']},
            'loaded_guidance': ['skills/omni-artifact-accelerator/SKILL.md'] +
                ['skills/omni-' + role + '/SKILL.md' for role in ('app-designer', 'branding', 'data-analyst',
                                                               'app-engineer', 'qa-analyst', 'data-storyteller')]}
        self.run = W.start(self.root, self.start_request)['path']
        roles = {'experience': 'app-designer', 'brand': 'branding', 'semantics': 'data-analyst',
                 'engineering': 'app-engineer', 'verification': 'qa-analyst',
                 'design_systems': 'app-designer', 'storytelling': 'data-storyteller'}
        self.execution = {'responsibilities': {name: {'role': role, 'worker': 'reviewer' if name == 'verification' else 'builder',
            'mode': 'inline', 'rationale': 'Synthetic responsibility; no real dispatch claim'} for name, role in roles.items()},
            'request_review': {'reviewer': 'reviewer', 'brief_sha256': W.P.digest((self.root / 'inputs/brief.txt').read_bytes()),
                'requirement_ids': ['investigate'], 'evidence_path': 'evidence/request-review.txt'}}
        self.save_execution()
        self.request = {'run': self.run, 'execution': 'contracts/execution.json'}
        self.gates = G.Lifecycle(self.root, W.P)
        self.provider_context = W.P.trusted_stage_provider(self.gates.host)
        self.provider_context.__enter__()
        self.addCleanup(self.provider_context.__exit__, None, None, None)
        self.gates.through()

    def write(self, path, content):
        (self.root / path).write_text(content if type(content) is str else json.dumps(content))

    def save_execution(self):
        self.write('contracts/execution.json', self.execution)

    def freeze(self, ident='initial'):
        result = W.freeze(self.root, {'id': ident, 'builders': ['builder'], 'artifacts': ['deliverables/app.html'],
            'context': [self.run, 'contracts/execution.json', 'evidence/request-review.txt', 'contracts/query.json']})
        self.gates.reviews()
        return result

    def evidence(self, candidate):
        evidence = {'candidate_sha256': W.P.digest((self.root / candidate).read_bytes()),
            'lanes': {name: {'status': 'not_run', 'method': '', 'observer': '', 'bindings': {},
                            'reason': 'No actual observation in this local test'} for name in W.LANES}}
        self.write('evidence/delivery.json', evidence)
        return evidence

    def inventory_request(self):
        return {'id': 'depth', 'inputs': ['inputs/source-profile.json'],
            'scope_rationale': 'Compare period demand and inspect records before choosing the final destinations.',
            'capabilities': [{'id': 'demand', 'requirement_ids': ['investigate'],
                'question': 'Which collection changed, and which observations explain it?',
                'source_refs': ['inputs/source-profile.json#collection'], 'population': 'Supplied collection observations',
                'grain': 'Collection and observation period',
                'available_depth': ['period comparison', 'exact observations'],
                'selected_depth': ['period comparison', 'exact observations'], 'disposition': 'selected',
                'rationale': 'Both comparison and inspection serve the original decision.',
                'remaining_gap': 'Native source completeness has not been observed.'}]}

    def select_inventory(self, path, version='inventoried'):
        self.base.base.value['product'] = {'schema_version': 1, 'scope': 'material_redesign',
            'discovery': 'reused_context', 'note_paths': ['inputs/brief.txt'], 'source_inventory_path': path}
        self.base.base.select(version)
        W.P.routing_helper('product_intent').generate(self.root, 'deliverables/north-star-' + version + '.md')

    def test_inventory_is_pinned_before_selection_and_stale_inputs_cannot_claim_readiness(self):
        captured = W.P.intent_helper().check(self.root)['selected']
        record = W.inventory(self.root, self.inventory_request())
        self.assertEqual(json.loads((self.root / record['path']).read_text())['intent_at_capture'], captured)
        self.assertFalse(record['scope_selected'])
        self.select_inventory(record['path'])
        result = W.inspect_run(self.root, self.request)
        self.assertEqual(result['source_inventory']['status'], 'consistent')
        self.assertNotIn('source_capability_inventory_missing', result['findings'])
        with self.assertRaises(ValueError):
            W.inventory(self.root, self.inventory_request())
        self.write('inputs/source-profile.json', '{"changed":true}')
        result = W.inspect_run(self.root, self.request)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['source_inventory']['status'], 'inconsistent')
        self.assertIn('source_capability_inventory_not_current', result['findings'])
        self.assertEqual(W.P.routing_helper('product_intent').check(self.root)['status'], 'inconsistent')

    def test_inventory_rejects_unknown_depth_and_preserves_nonselected_dispositions(self):
        request = self.inventory_request()
        request['capabilities'][0]['selected_depth'] = ['unavailable live prediction']
        with self.assertRaisesRegex(ValueError, 'absent from available'):
            W.inventory(self.root, request)
        self.assertFalse((self.root / 'evidence/source-capabilities-depth.json').exists())
        request = self.inventory_request()
        request['capabilities'][0].update(disposition='unsupported', available_depth=[], selected_depth=[],
            remaining_gap='The supplied evidence does not support the requested comparison.')
        record = W.inventory(self.root, request)
        self.select_inventory(record['path'])
        result = W.inspect_run(self.root, self.request)
        self.assertIn('source_capability_unsupported:demand', result['findings'])
        self.assertFalse(result['source_inventory']['scope_approved'])
        # Retain a rejected method without making the supported outcome wait for approval.
        request = self.inventory_request()
        request['id'] = 'with-alternative'
        unsupported = copy.deepcopy(request['capabilities'][0])
        unsupported.update(id='live-comparison', disposition='unsupported', selected_depth=[],
            alternative_id='demand', remaining_gap='Live delivery is unsupported; the selected observed-period comparison preserves the outcome.')
        request['capabilities'].append(unsupported)
        alternative = W.inventory(self.root, request)
        self.select_inventory(alternative['path'], 'alternative')
        result = W.inspect_run(self.root, self.request)
        self.assertNotIn('source_capability_unsupported:live-comparison', result['findings'])
        self.assertEqual(result['source_inventory']['capabilities'][1]['disposition'], 'unsupported')
        self.base.base.value['product'].pop('source_inventory_path')
        with self.assertRaisesRegex(ValueError, 'source_inventory_removed'):
            self.base.base.select('removed-inventory')

    def test_optional_specialist_has_actual_role_guidance_and_requirement_scope(self):
        self.execution['specialists'] = {'spatial': {'role': '3d-modeler', 'worker': 'geometry-worker',
            'mode': 'delegated', 'rationale': 'Bounded original geometry for selected inspection task',
            'requirement_ids': ['investigate']}}
        self.save_execution()
        result = W.inspect_run(self.root, self.request)
        self.assertIn('role_guidance_not_recorded:3d-modeler', result['findings'])
        self.start_request['id'] = 'with-specialist'
        self.start_request['loaded_guidance'].append('skills/omni-3d-modeler/SKILL.md')
        request = {**self.request, 'run': W.start(self.root, self.start_request)['path']}
        self.assertEqual(W.inspect_run(self.root, request)['status'], 'ready_for_review')
        self.execution['specialists']['spatial']['requirement_ids'] = ['invented']
        self.save_execution()
        with self.assertRaisesRegex(ValueError, 'scope invalid'):
            W.inspect_run(self.root, request)

    def test_delivery_projection_copies_explicit_facts_without_selecting_or_inventing(self):
        req = self.base.base.value['requirements'][0]
        req.pop('delivery')
        req['value'] = 'Select a collection, inspect exact observations, and return with the period retained.'
        req['contexts'][0]['applicability'] = [{'kind': 'destination', 'id': 'investigation',
                                               'lanes': {'craft': {'status': 'required'}}}]
        self.base.base.select('unannotated')
        selected = W.P.intent_helper().check(self.root)['selected']
        proposal = W.project_delivery(self.root, {'output': 'contracts/proposal.json', 'annotations': {}})
        value = json.loads((self.root / proposal['path']).read_text())['requirements'][0]['delivery']
        self.assertNotIn('owner', value)
        self.assertNotIn('behavior', value)
        self.assertEqual(value['destinations'], ['investigation'])
        self.assertEqual(value['source_ref'], req['decision_ref'])
        self.assertEqual(proposal['coverage']['status'], 'incomplete')
        self.assertEqual(W.P.intent_helper().check(self.root)['selected'], selected)
        resolved = W.project_delivery(self.root, {'output': 'contracts/resolved-proposal.json', 'annotations': {
            'investigate': {'owner': 'app-designer', 'behavior_from_value': True}}})
        self.assertEqual(resolved['coverage']['status'], 'ready_for_review')
        self.assertEqual(resolved['status'], 'proposal')
        self.assertTrue(resolved['selection_required'])
        self.assertEqual(W.P.intent_helper().check(self.root)['selected'], selected)
        with self.assertRaises(ValueError):
            W.project_delivery(self.root, {'output': 'contracts/unsafe-proposal.json', 'annotations': {
                'investigate': {'dependency_paths': ['../outside']}}})
        self.assertFalse((self.root / 'contracts/unsafe-proposal.json').exists())

    def test_evidence_template_keeps_source_review_separate_from_formal_design_coverage(self):
        candidate = self.freeze()['path']
        self.write('inputs/template-request.json', {'candidate': candidate, 'output': 'evidence/template.json'})
        command = subprocess.run([sys.executable, '-I', '-S', '-B',
            str(ROOT / 'skills/omni-artifact-accelerator/scripts/analyst_project.py'),
            'delivery-evidence-template', '--project', str(self.root), '--request', str(self.root / 'inputs/template-request.json')],
            capture_output=True, text=True)
        self.assertEqual(command.returncode, 0, command.stderr)
        result = json.loads(command.stdout)
        evidence = json.loads((self.root / result['path']).read_text())
        self.assertEqual(set(evidence['lanes']), W.LANES)
        self.assertEqual({r['status'] for r in evidence['lanes'].values()}, {'not_run'})
        self.assertEqual(result['design_requirement_review']['status'], 'not_assessed')
        evidence['lanes']['source'] = {'status': 'reported_pass', 'method': 'source_review', 'observer': 'reviewer',
            'bindings': W.pins(self.root, ['evidence/request-review.txt']), 'reason': 'Bounded original source critique'}
        self.write('evidence/template.json', evidence)
        assessment = W.assess(self.root, {**self.request, 'candidate': candidate, 'evidence': 'evidence/template.json'})
        self.assertEqual(assessment['review_assessments'], {'source_critique': 'reported_pass',
                                                         'requirement_context_design': 'not_assessed'})
        self.assertEqual(assessment['status'], 'candidate_with_gaps')
        self.assertIn('lane_rendered_not_run', assessment['findings'])
        self.write('deliverables/app.html', 'Changed candidate')
        with self.assertRaisesRegex(ValueError, 'current candidate selection|candidate changed'):
            W.evidence_template(self.root, {'candidate': candidate, 'output': 'evidence/stale.json'})

    def test_bootstrap_and_ownership_are_distinct_from_dispatch(self):
        r = W.inspect_run(self.root, self.request)
        self.assertEqual(r['status'], 'ready_for_review', r)
        self.assertFalse(r['agents_dispatched'])
        with self.assertRaisesRegex(ValueError, 'already recorded'):
            W.start(self.root, self.start_request)
        self.execution['responsibilities']['verification']['worker'] = 'builder'
        self.save_execution()
        self.assertIn('independent_verification_not_assigned', W.inspect_run(self.root, self.request)['findings'])

    def test_product_ownership_and_independent_creative_review_are_conditional(self):
        value = self.base.base.value
        value['product'] = {'schema_version': 1, 'scope': 'material_redesign',
                            'discovery': 'reused_context', 'note_paths': ['inputs/brief.txt']}
        self.base.base.select('product')
        W.P.routing_helper('product_intent').generate(self.root, 'deliverables/north-star-product.md')
        findings = W.inspect_run(self.root, self.request)['findings']
        self.assertIn('source_capability_inventory_missing', findings)
        self.assertIn('product_responsibility_missing:product_intent', findings)
        self.assertIn('product_responsibility_missing:creative_review', findings)
        self.execution['responsibilities'].update({
            'product_intent': {'role': 'product-owner', 'worker': 'coordinator', 'mode': 'inline',
                              'rationale': 'Reuse the original answers and reconcile current intent'},
            'creative_review': {'role': 'app-designer', 'worker': 'builder', 'mode': 'delegated',
                                'rationale': 'Review the representative journey against intent'}})
        self.save_execution()
        self.assertIn('independent_creative_review_not_assigned', W.inspect_run(self.root, self.request)['findings'])
        self.execution['responsibilities']['creative_review']['worker'] = 'creative-critic'
        self.save_execution()
        findings = W.inspect_run(self.root, self.request)['findings']
        self.assertNotIn('independent_creative_review_not_assigned', findings)
        self.assertIn('role_guidance_not_recorded:product-owner', findings)
        # A focused repair inherits current intent without a new mandatory discovery/critic role.
        value['product'].update(scope='focused_repair', discovery='focused_repair')
        self.base.base.select('repair')
        W.P.routing_helper('product_intent').generate(self.root, 'deliverables/north-star-repair.md')
        for key in ('product_intent', 'creative_review'):
            del self.execution['responsibilities'][key]
        self.save_execution()
        findings = W.inspect_run(self.root, self.request)['findings']
        self.assertFalse(any(f.startswith('product_responsibility_missing:') for f in findings))
        self.assertNotIn('source_capability_inventory_missing', findings)

    def test_original_request_and_package_drift_cannot_reuse_readiness(self):
        self.write('inputs/brief.txt', 'Additional requirement after intake')
        self.assertIn('original_request_changed', W.inspect_run(self.root, self.request)['findings'])
        with mock.patch.object(W, 'source_manifest', return_value={'changed': '0' * 64}):
            self.assertIn('package_changed_since_start', W.inspect_run(self.root, self.request)['findings'])
        self.execution['request_review']['requirement_ids'] = []
        self.save_execution()
        self.assertIn('original_request_review_scope_differs', W.inspect_run(self.root, self.request)['findings'])

    def test_capability_suggestions_can_be_assigned_to_app_stage(self):
        routing = W.P.routing_helper('task_routing')
        capabilities = W.P.experience_helper().CAPABILITIES
        for roles in capabilities.values():
            self.assertTrue(set(roles) <= routing.STAGE_ROLES['app'], roles)
        index = W.P.packet(self.root, 'data-storyteller', ['contracts/query.json'], None)
        assignment = {'schema_version': 1, 'task_id': 'story', 'domain_id': 'collection', 'stage': 'app',
            'role': 'data-storyteller', 'scope_ids': ['investigate'], 'objective': 'Explain the comparison',
            'outputs': ['deliverables/story.txt'], 'acceptance': ['Claims reflect the supplied population'],
            'input_bindings': {p['path']: p['sha256'] for p in index['inputs']}, 'dependencies': {},
            'unknowns': [], 'authoring_mode': 'provisional'}
        W.P.packet(self.root, 'data-storyteller', ['contracts/query.json'], self.root / 'tasks/story.json', assignment)
        self.assertEqual(W.P.packet_check(self.root, 'tasks/story.json')['status'], 'consistent')

    def test_first_bytes_survive_revision_and_old_evidence_becomes_stale(self):
        first = self.freeze()
        original = (self.root / 'deliverables/app.html').read_bytes()
        self.evidence(first['path'])
        self.write('deliverables/app.html', '<main>Revised original experience</main>')
        self.base.base.select('revised')
        self.gates.stage('design')
        next_candidate = self.freeze('revised')
        self.assertEqual(next_candidate['first'], first['first'])
        record = json.loads((self.root / first['path']).read_text())
        self.assertEqual((self.root / record['retained']['deliverables/app.html']).read_bytes(), original)
        r = W.assess(self.root, {**self.request, 'candidate': first['path'], 'evidence': 'evidence/delivery.json'})
        self.assertIn('candidate_artifacts_changed', r['findings'])
        self.assertEqual(r['status'], 'candidate_with_gaps')
        with self.assertRaisesRegex(ValueError, 'already recorded'):
            self.freeze()

    def test_simulation_cannot_be_reported_as_rendering(self):
        c = self.freeze()['path']; evidence = self.evidence(c)
        evidence['lanes']['rendered'] = {'status': 'reported_pass', 'method': 'constructed_fixture',
            'observer': 'reviewer', 'bindings': W.pins(self.root, ['evidence/request-review.txt']), 'reason': 'Synthetic test'}
        self.write('evidence/delivery.json', evidence)
        with self.assertRaisesRegex(ValueError, 'does not establish'):
            W.assess(self.root, {**self.request, 'candidate': c, 'evidence': 'evidence/delivery.json'})

    def test_unreviewed_artifact_cannot_borrow_selected_design_completion(self):
        self.write('deliverables/unreviewed.html', '<main>Unreviewed</main>')
        c = W.freeze(self.root, {'id': 'wrong', 'builders': ['builder'], 'artifacts': ['deliverables/unreviewed.html'],
            'context': [self.run, 'contracts/execution.json', 'evidence/request-review.txt']})['path']
        self.evidence(c)
        result = W.assess(self.root, {**self.request, 'candidate': c, 'evidence': 'evidence/delivery.json'})
        self.assertIn('delivery_artifacts_differ_from_selected_candidates', result['findings'])

    def test_final_assessment_rechecks_preserved_first_candidate(self):
        first = self.freeze()['path']; final = self.freeze('final')['path']
        record = json.loads((self.root / first).read_text())
        self.write(record['retained']['deliverables/app.html'], 'Corrupted historical bytes')
        self.evidence(final)
        result = W.assess(self.root, {**self.request, 'candidate': final, 'evidence': 'evidence/delivery.json'})
        self.assertIn('candidate_history_invalid', result['findings'])
        with self.assertRaisesRegex(ValueError, 'stage_gate_stale_iteration_evidence'):
            self.freeze('next')

    def test_delivery_cli_reports_unrun_lanes_with_failure_exit(self):
        c = self.freeze()['path']; self.evidence(c)
        request = {**self.request, 'candidate': c, 'evidence': 'evidence/delivery.json'}
        self.write('inputs/delivery-check.json', request)
        p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'skills/omni-artifact-accelerator/scripts/analyst_project.py'),
            'delivery-check', '--project', str(self.root), '--request', str(self.root / 'inputs/delivery-check.json')], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stderr)
        value = json.loads(p.stdout)
        self.assertFalse(value['publication_authorized'])
        self.assertIn('lane_native_not_run', value['findings'])
        self.assertIn('design_requirement_review_not_assessed', value['findings'])


if __name__ == '__main__':
    unittest.main()
