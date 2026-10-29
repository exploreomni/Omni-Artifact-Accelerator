"""Original report evidence through routing, A-F and backend handoff; no tenant calls."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('cognos_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
t = load('cognos_translator', 'skills/omni-artifact-translator/scripts/translate_artifact.py')
f = load('cognos_integration_fixture', 'tests/test_cognos_visual.py')
s = load('cognos_standalone', 'skills/omni-backend-handoff/scripts/standalone.py')
e = load('cognos_migration_fixture', 'tests/test_migration_e2e.py')
m = load('migration', 'skills/omni-backend-handoff/scripts/migration.py')


def put(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value))


def setup_source(root):
    snapshot = f.snapshot_fixture()
    original = 'inputs/report-snapshot.json'
    put(root, original, snapshot)
    inventory = t.translate((root / original).read_bytes(), 'cognos-report')
    put(root, 'inputs/inventory.json', inventory)
    for path in (original, 'inputs/inventory.json'):
        ap.register(root, 'sources', path, path)
    v.prepare(root, original, 'inputs/inventory.json', 'contracts/visual.json')
    req = v.load(root, 'contracts/visual.json')
    req.update(route='reuse_existing', route_reference='Synthetic reviewed reuse route')
    put(root, 'contracts/visual.json', req)
    return original, inventory, req


class CognosWorkflow(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic report workflow', 'migration', 'both')
        self.original, self.inventory, self.req = setup_source(self.root)

    def test_typed_scope_preserves_denominator_and_blocks_early_build(self):
        root, obj = ap.load_project(self.root)
        self.assertTrue(ap.cognos_scope(root, obj))
        req = v.requirements(root, 'contracts/visual.json')[1]
        self.assertEqual(len(req['items']), len(self.inventory['assets']))
        self.assertTrue(s.query_source_keys(req))
        self.assertTrue(s.control_source_keys(req))
        for item in req['items']:
            if not item['source_identity'].get('query_visual'):
                self.assertFalse(any(c['lane'] == 'numeric' for c in item['required_cases']))
            self.assertFalse(any(c['case_id'].endswith('/interaction/bookmark_state') for c in item['required_cases']))
        with self.assertRaises(ValueError):
            ap.stage_packet_gate(root, 'cognos-migrator', {'stage': 'discovery', 'outputs': ['app.js']})
        empty = root.parent / 'empty'
        ap.init(empty, 'Cognos by name only', 'migration', 'both')
        self.assertFalse(ap.cognos_scope(*ap.load_project(empty)))
        with self.assertRaises(ValueError):
            ap.stage_packet_gate(empty, 'cognos-migrator', {'stage': 'discovery', 'outputs': []})

    def test_projection_and_registered_original_tampering_fail(self):
        edited = copy.deepcopy(self.inventory)
        edited['assets'].pop()
        put(self.root, 'inputs/edited.json', edited)
        with self.assertRaisesRegex(ValueError, 'projection_changed'):
            v.source_inventory(self.root, self.original, 'inputs/edited.json')
        file = self.root / self.original
        file.write_bytes(file.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            ap.cognos_scope(*ap.load_project(self.root))
        with self.assertRaises(ValueError):
            v.requirements(self.root, 'contracts/visual.json')

    def test_unresolved_scope_cannot_be_silently_promoted(self):
        req = copy.deepcopy(self.req)
        obligation = next(i for i in req['items'] if i['source_identity']['declared_disposition'] != 'include')
        self.assertEqual(obligation['disposition'], 'defer')
        obligation['disposition'] = 'migrate'
        put(self.root, 'contracts/unreviewed.json', req)
        with self.assertRaisesRegex(ValueError, 'cognos_source_review_required'):
            v.requirements(self.root, 'contracts/unreviewed.json')
        obligation['scope_decision'] = {'reason': 'Synthetic reviewed adaptation with original dependency retained',
                                        'reference': 'Synthetic explicit review decision'}
        put(self.root, 'contracts/reviewed.json', req)
        v.requirements(self.root, 'contracts/reviewed.json')

    def test_equal_numbers_cannot_claim_qualified_cognos_parity(self):
        case = next(c for item in self.req['items'] for c in item['required_cases'] if c['lane'] == 'numeric')
        for name in ('source', 'target'):
            put(self.root, 'evidence/' + name + '.json', [{'region': 'North', 'value': '9007199254740993'}])
        put(self.root, 'evidence/candidate.json', {'kind': 'synthetic_candidate'})
        context = {'filters': {}, 'timezone': 'UTC', 'data_watermark': 'synthetic-watermark',
                   'population': 'synthetic-population', 'principal': 'synthetic-principal'}
        spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec',
                'case_id': case['case_id'], 'requirements': v.pin(self.root, 'contracts/visual.json'),
                'candidate': v.pin(self.root, 'evidence/candidate.json'),
                'persona_equivalence_reference': 'Synthetic personas', 'keys': ['region'],
                'columns': [{'name': 'region', 'type': 'string', 'source': 'region', 'target': 'region'},
                            {'name': 'value', 'type': 'number', 'source': 'value', 'target': 'value'}]}
        for name in ('source', 'target'):
            spec[name] = {'file': v.pin(self.root, 'evidence/' + name + '.json'), 'format': 'json',
                          'context': context, 'complete': True, 'completeness_reference': 'Synthetic declaration'}
        put(self.root, 'contracts/compare.json', spec)
        v.compare(self.root, 'contracts/compare.json', 'evidence/compare.json')
        result = v.load(self.root, 'evidence/compare.json')
        self.assertEqual(result['status'], 'inconclusive')
        self.assertIn('source.cognos_result_binding_unqualified', result['gaps'])


class CognosDmaJourney(e.MigrationJourney):
    def source(self):
        original, inventory, req = setup_source(self.root)
        req.update(route='omni_semantic_reconstruction')
        put(self.root, 'contracts/visual.json', req)
        self.source_paths = [original, 'inputs/inventory.json']
        self.source_pins = {p: e.sha(self.root / p) for p in self.source_paths}
        self.inventories, self.assets, self.source_gaps = [inventory], inventory['assets'], inventory['gaps']
        self.platform, self.route = 'cognos', 'omni_semantic_reconstruction'

    def request(self, *args, **kwargs):
        original = self.assets
        self.assets = [a for a in original if not a['source_identity'].get('restricted_private_scope')]
        try:
            return super().request(*args, **kwargs)
        finally:
            self.assets = original

    def scope(self):
        units = []
        for asset in self.assets:
            restricted = asset['source_identity'].get('restricted_private_scope') is True
            units.append({'unit_id': 'u-' + str(len(units)), 'inventory_path': self.source_paths[1],
                'asset_keys': [asset['asset_key']], 'disposition': 'defer' if restricted else 'migrate',
                'rationale': 'Synthetic selected scope with unresolved dependencies',
                'frontend_asset_ids': [] if restricted else [asset['asset_key']],
                'surfaces': [] if restricted else ['dashboard']})
        spec = {'schema_version': 1, 'kind': 'analyst_migration_scope_spec', 'scope_id': 'synthetic-scope',
            'decision_reference': 'Synthetic selected-scope review', 'inventory_paths': [self.source_paths[1]],
            'backend_context_path': None, 'units': units}
        put(self.root, 'contracts/scope-spec.json', spec)
        m.freeze(self.root, 'contracts/scope-spec.json', 'evidence/migration-scope-v1.json')
        return m, v.load(self.root, 'evidence/migration-scope-v1.json'), units

    def test_backend_handoff_keeps_original_and_does_not_grant_publication(self):
        self.source()
        self.scope()
        request = self.request(migration_scope_path='evidence/migration-scope-v1.json')
        self.assertEqual(request['migration_sources'][0]['original_source']['path'], self.source_paths[0])
        self.receive(self.response())
        selected = self.select()
        self.assertFalse(selected['accepted'])
        self.assertFalse(selected['authorizes_target_write'])
        self.assertEqual(selected['requirement_resolutions'][0]['status'], 'unresolved')

    def test_semantic_only_route_rejects_warehouse_work_and_edited_inventory(self):
        self.source()
        self.scope()
        self.request(migration_scope_path='evidence/migration-scope-v1.json')
        with self.assertRaisesRegex(ValueError, 'violates selected route'):
            self.response(action='warehouse_and_semantic_candidate')
        value = v.load(self.root, self.source_paths[1])
        value['assets'].pop()
        put(self.root, self.source_paths[1], value)
        with self.assertRaises(ValueError):
            e.bridge.verify_cognos_inventory(self.root, ap.load_project(self.root)[1], self.source_paths[1])


if __name__ == '__main__':
    unittest.main()
