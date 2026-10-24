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


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.DeliveryTests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.root = self.base.root
        self.base.base.select()
        self.write('inputs/brief.txt', 'Investigate collection changes; preserve evidence and return context.')
        self.write('evidence/request-review.txt', 'Original request compared independently with investigate requirement.')
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

    def write(self, path, content):
        (self.root / path).write_text(content if type(content) is str else json.dumps(content))

    def save_execution(self):
        self.write('contracts/execution.json', self.execution)

    def freeze(self, ident='initial'):
        return W.freeze(self.root, {'id': ident, 'artifacts': ['deliverables/app.html'],
            'context': [self.run, 'contracts/execution.json', 'evidence/request-review.txt', 'contracts/query.json']})

    def evidence(self, candidate):
        evidence = {'candidate_sha256': W.P.digest((self.root / candidate).read_bytes()),
            'lanes': {name: {'status': 'not_run', 'method': '', 'observer': '', 'bindings': {},
                            'reason': 'No actual observation in this local test'} for name in W.LANES}}
        self.write('evidence/delivery.json', evidence)
        return evidence

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
        c = W.freeze(self.root, {'id': 'wrong', 'artifacts': ['deliverables/unreviewed.html'],
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
        with self.assertRaisesRegex(ValueError, 'historical bytes'):
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
