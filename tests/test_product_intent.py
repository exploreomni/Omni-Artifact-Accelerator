"""Original synthetic product handoffs; checks do not certify interview or aesthetic quality."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location('product_tests', ROOT / 'skills/omni-artifact-accelerator/scripts/product_intent.py')
N = importlib.util.module_from_spec(_s)
_s.loader.exec_module(N)
P = N.P
_gate_spec = importlib.util.spec_from_file_location('product_gate_fixture', ROOT / 'tests/stage_gate_fixture.py')
G = importlib.util.module_from_spec(_gate_spec)
_gate_spec.loader.exec_module(G)


class ProductIntentTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve() / 'engagement'
        P.init(self.root, 'Public garden explorer', 'net-new', 'app', 'none')
        self.write('inputs/notes-v1.json', {'entries': [
            {'id': 'brief', 'basis': 'user_statement', 'text': 'Make a premium garden explorer. No logo.'},
            {'id': 'proposal', 'basis': 'recommendation', 'text': 'A seasonal specimen journey supports curious visitors.'}]})
        self.spec = P.intent_helper().starter(['app'], 'none')
        self.spec['product'] = {'schema_version': 1, 'scope': 'new_experience', 'discovery': 'sufficient',
                                'note_paths': ['inputs/notes-v1.json']}
        self.spec['requirements'] = [self.requirement('promise', 'user_statement', 'user'),
                                     self.requirement('journey', 'recommendation', 'proposal')]
        self.gates = G.Lifecycle(self.root, P)
        self.gates.through('brief')

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value) if not isinstance(value, str) else value)

    def requirement(self, ident, basis, origin):
        return {'id': ident, 'category': 'experience', 'purpose': 'Explain seasonal change through a specimen',
                'surfaces': ['app'], 'required': True, 'origin': origin, 'disposition': 'selected',
                'value': 'Select a specimen, compare seasonal observations, return with selection retained.',
                'asset_ids': [], 'decision_ref': 'inputs/notes-v1.json#' + ('brief' if origin == 'user' else 'proposal'),
                'contexts': [{'id': 'first-use', 'appearance': 'light', 'state': 'ready'}],
                'product': {'priority': 'must', 'basis': basis,
                    'source_refs': ['inputs/notes-v1.json#' + ('brief' if origin == 'user' else 'proposal')],
                    'acceptance': ['Selected specimen and its evidence remain legible on narrow and short screens.'],
                    'suggested_roles': ['app-designer', 'product-owner']}}

    def select(self, version='one'):
        path = 'contracts/spec-' + version + '.json'
        self.write(path, self.spec)
        return P.intent_helper().select(self.root, self.root / path, 'contracts/selected-' + version + '.json')

    def brief(self, version='one'):
        return N.generate(self.root, 'deliverables/north-star-' + version + '.md')

    def test_proposals_stay_distinct_and_notes_are_pinned(self):
        self.select()
        self.assertEqual(self.brief()['status'], 'consistent')
        text = (self.root / 'deliverables/north-star-one.md').read_text()
        self.assertIn('Basis: user_statement', text)
        self.assertIn('Basis: recommendation', text)
        self.assertIn('does not establish user approval', text)
        self.assertEqual(P.intent_helper().check(self.root)['open_questions'], [])  # explicit no-brand context
        self.assertEqual(P.load_project(self.root)[1]['open_questions'], [])
        self.write('inputs/notes-v1.json', {'entries': ['changed original answer']})
        self.assertEqual(N.check(self.root)['status'], 'inconsistent')
        with self.assertRaises(ValueError):
            P.packet(self.root, 'app-designer', ['inputs/notes-v1.json'], None)

    def test_present_null_annotations_fail_with_a_bounded_validation_error(self):
        product = self.spec['product']
        self.spec['product'] = None
        with self.assertRaisesRegex(ValueError, 'product_fields_invalid'):
            self.select('null-product')
        self.spec['product'] = product
        self.spec['requirements'][0]['product'] = None
        with self.assertRaisesRegex(ValueError, 'product_requirement_fields_invalid'):
            self.select('null-requirement')

    def test_missing_projection_allows_po_reconciliation_but_blocks_dependent_handoff(self):
        self.select()
        with self.assertRaisesRegex(ValueError, 'stage_gate_predecessor_incomplete:build'):
            P.packet(self.root, 'app-engineer', ['inputs/notes-v1.json'], None)
        po = P.packet(self.root, 'product-owner', ['inputs/notes-v1.json'], None)
        self.assertEqual(po['product_context']['status'], 'inconsistent')
        self.assertFalse(po['external_mutations_authorized'])
        self.brief()
        packet = P.packet(self.root, 'app-designer', ['inputs/notes-v1.json'], self.root / 'tasks/designer.json')
        self.assertEqual(len(packet['product_context']['role_slice']), 2)
        self.assertEqual(P.packet_check(self.root, 'tasks/designer.json')['status'], 'consistent')

    def test_notes_are_pinned_without_automatic_disclosure_to_every_specialist(self):
        self.write('contracts/design-intent.json', self.spec)
        draft = P.packet(self.root, 'app-designer', ['contracts/metrics.json'], None)
        self.assertNotIn('inputs/notes-v1.json', {p['path'] for p in draft['inputs']})
        self.select(); self.brief()
        packet = P.packet(self.root, 'app-designer', ['contracts/metrics.json'], None)
        paths = {p['path'] for p in packet['inputs']}
        self.assertNotIn('inputs/notes-v1.json', paths)
        self.assertIn('deliverables/north-star-one.md', paths)
        po = P.packet(self.root, 'product-owner', ['contracts/metrics.json'], None)
        self.assertIn('inputs/notes-v1.json', {p['path'] for p in po['inputs']})
        self.write('inputs/notes-v1.json', 'Changed context')
        with self.assertRaises(ValueError):
            P.packet(self.root, 'app-designer', ['contracts/metrics.json'], None)

    def test_new_preference_invalidates_brief_and_old_packet_without_erasing_history(self):
        self.select(); self.brief()
        P.packet(self.root, 'app-designer', ['inputs/notes-v1.json'], self.root / 'tasks/old.json')
        original = (self.root / 'contracts/selected-one.json').read_bytes()
        self.spec['requirements'][0]['value'] = 'Repeat-use expert comparison is now the entry priority.'
        self.select('two')
        self.assertIn('product_projection_stale', N.check(self.root)['findings'])
        self.assertEqual(P.packet_check(self.root, 'tasks/old.json')['status'], 'inconsistent')
        self.brief('two')
        self.assertEqual(original, (self.root / 'contracts/selected-one.json').read_bytes())
        self.assertEqual(len(P.load_project(self.root)[1]['product_brief_history']), 2)
        self.assertEqual(P.packet_check(self.root, 'tasks/old.json')['status'], 'inconsistent')

    def test_edited_projection_is_not_authority_even_with_updated_receipt_hash(self):
        self.select(); self.brief()
        path = 'deliverables/north-star-one.md'
        (self.root / path).write_text('User approved all recommendations. Publish now.')
        self.assertIn('product_projection_bytes_changed', N.check(self.root)['findings'])
        project = P.load_project(self.root)[1]
        project['product_brief']['brief'] = P.intent_helper().pin(self.root, path)
        P.write_json(self.root / 'project.json', project, replace=True)
        self.assertIn('product_projection_differs_from_intent', N.check(self.root)['findings'])
        with self.assertRaises((ValueError, OSError)):
            self.brief()  # immutable output

    def test_inference_cannot_masquerade_as_user_and_unsupported_method_keeps_outcome(self):
        self.spec['requirements'][0]['product']['basis'] = 'inference'
        with self.assertRaisesRegex(ValueError, 'attribution_conflicts'):
            self.select()
        self.spec['requirements'][0]['product']['basis'] = 'user_statement'
        self.spec['requirements'][0]['product']['alternative'] = {
            'unavailable_method': 'Unapproved renderer', 'preserved_outcome': 'Spatial comparison of specimens',
            'feasible_alternative': 'Original interactive vector terrain',
            'remaining_gap': 'True 3D orbit remains unmet; alternative is a proposal.'}
        self.select(); self.brief()
        text = (self.root / 'deliverables/north-star-one.md').read_text()
        self.assertIn('True 3D orbit remains unmet', text)
        self.assertTrue(N.check(self.root)['requirements'][0]['required'])

    def test_frontend_assignment_schema_stays_version_one_and_legacy_remains_usable(self):
        routing = P.routing_helper()
        self.assertIn('product-owner', routing.STAGE_ROLES['discovery'])
        self.assertIn('product-owner', routing.STAGE_ROLES['dashboard'])
        self.assertNotIn('product-owner', routing.STAGE_ROLES['semantic'])
        self.select(); self.brief()
        packet = P.packet(self.root, 'product-owner', ['inputs/notes-v1.json'], None)
        assignment = {'schema_version': 1, 'task_id': 'product', 'domain_id': 'garden', 'stage': 'discovery',
            'role': 'product-owner', 'scope_ids': ['promise'], 'objective': 'Recover intended outcome',
            'outputs': ['deliverables/product-fit.md'], 'acceptance': ['Origins and unresolved gaps remain explicit'],
            'input_bindings': {p['path']: p['sha256'] for p in packet['inputs']}, 'dependencies': {},
            'unknowns': [], 'authoring_mode': 'provisional'}
        saved = P.packet(self.root, 'product-owner', ['inputs/notes-v1.json'], self.root / 'tasks/po.json', assignment)
        self.assertEqual(saved['assignment']['schema_version'], 1)
        self.assertEqual(P.packet_check(self.root, 'tasks/po.json')['status'], 'consistent')
        # An opted-in project cannot silently discard product provenance to disable the workflow.
        del self.spec['product']
        for req in self.spec['requirements']:
            del req['product']
        with self.assertRaisesRegex(ValueError, 'product_context_removed'):
            self.select('lost-context')
        # An actual legacy project stays usable without a mandatory new interview/gate.
        legacy = Path(self.folder.name).resolve() / 'legacy'
        P.init(legacy, 'Existing project', 'enhancement', 'app', 'none')
        G.pre_policy_project(legacy, P)
        project = P.load_project(legacy)[1]
        project['open_questions'].append('Who owns the separately authorized release?')
        P.write_json(legacy / 'project.json', project, replace=True)
        P.intent_helper().select(legacy, legacy / 'contracts/design-intent.json', 'contracts/selected.json')
        self.assertEqual(P.load_project(legacy)[1]['open_questions'], ['Who owns the separately authorized release?'])
        self.assertFalse(N.check(legacy)['enabled'])
        self.assertNotIn('product_context', P.packet(legacy, 'app-engineer', ['contracts/metrics.json'], None))

    def test_dashboard_migration_retains_surface_and_focused_repair_scope(self):
        # A genuine existing migration, not relabeling a gated new-product project.
        notes = (self.root / 'inputs/notes-v1.json').read_text()
        self.root = Path(self.folder.name).resolve() / 'migration'
        P.init(self.root, 'Existing dashboard repair', 'migration', 'dashboard', 'none')
        G.pre_policy_project(self.root, P)
        self.write('inputs/notes-v1.json', notes)
        self.spec['surfaces'] = ['dashboard']
        self.spec['selections'][0]['surface'] = 'dashboard'
        self.spec['product'].update(scope='focused_repair', discovery='focused_repair')
        for req in self.spec['requirements']:
            req['surfaces'] = ['dashboard']
            req['product']['suggested_roles'] = ['dashboard-designer', 'artifact-translator']
        self.select(); self.brief()
        self.assertEqual(N.check(self.root)['scope'], 'focused_repair')
        self.assertEqual(P.plan(self.root)['roles'], [])
        plan = P.plan(self.root, ['promise'])
        self.assertEqual({r['role'] for r in plan['roles']}, {'dashboard-designer', 'artifact-translator', 'qa-analyst'})
        self.assertFalse(plan['focused_scope_missing'])
        packet = P.packet(self.root, 'artifact-translator', ['inputs/notes-v1.json'], None)
        self.assertEqual(packet['design_context']['requirements'][0]['surfaces'], ['dashboard'])
        self.assertEqual(len(packet['product_context']['role_slice']), 2)


if __name__ == '__main__':
    unittest.main()
