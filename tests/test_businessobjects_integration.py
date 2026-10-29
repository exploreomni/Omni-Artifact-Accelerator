"""Original WebI evidence through routing, A-F and backend handoff; no tenant calls."""
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
v = load('businessobjects_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
t = load('businessobjects_translator', 'skills/omni-artifact-translator/scripts/translate_artifact.py')
f = load('businessobjects_integration_fixture', 'tests/test_businessobjects_visual.py')
s = load('businessobjects_standalone', 'skills/omni-backend-handoff/scripts/standalone.py')
e = load('businessobjects_migration_fixture', 'tests/test_migration_e2e.py')
m = load('migration', 'skills/omni-backend-handoff/scripts/migration.py')
capture_fixture = load('businessobjects_capture_fixture', 'tests/test_businessobjects_capture.py')


def put(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value))


def setup_source(root):
    snapshot = f.snapshot_fixture()
    original = 'inputs/report-snapshot.json'
    put(root, original, snapshot)
    inventory = t.translate((root / original).read_bytes(), 'businessobjects-api')
    put(root, 'inputs/inventory.json', inventory)
    for path in (original, 'inputs/inventory.json'):
        ap.register(root, 'sources', path, path)
    v.prepare(root, original, 'inputs/inventory.json', 'contracts/visual.json')
    req = v.load(root, 'contracts/visual.json')
    req.update(route='reuse_existing', route_reference='Synthetic reviewed reuse route')
    put(root, 'contracts/visual.json', req)
    return original, inventory, req


class BusinessObjectsWorkflow(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic report workflow', 'migration', 'both')
        self.original, self.inventory, self.req = setup_source(self.root)

    def test_typed_scope_preserves_denominator_and_blocks_early_build(self):
        root, obj = ap.load_project(self.root)
        self.assertTrue(ap.businessobjects_scope(root, obj))
        req = v.requirements(root, 'contracts/visual.json')[1]
        self.assertEqual(len(req['items']), len(self.inventory['assets']))
        self.assertTrue(s.query_source_keys(req))
        missing = next(i for i in req['items'] if i['source_identity']['object_key'] == 'expected-control')
        self.assertEqual(missing['disposition'], 'defer')
        for item in req['items']:
            if not item['source_identity'].get('query_visual'):
                self.assertFalse(any(c['lane'] == 'numeric' for c in item['required_cases']))
            self.assertFalse(any(c['case_id'].endswith('/interaction/bookmark_state') for c in item['required_cases']))
        with self.assertRaises(ValueError):
            ap.stage_packet_gate(root, 'businessobjects-migrator', {'stage': 'discovery', 'outputs': ['app.js']})
        empty = root.parent / 'empty'
        ap.init(empty, 'BusinessObjects by name only', 'migration', 'both')
        self.assertFalse(ap.businessobjects_scope(*ap.load_project(empty)))
        with self.assertRaises(ValueError):
            ap.stage_packet_gate(empty, 'businessobjects-migrator', {'stage': 'discovery', 'outputs': []})

    def test_projection_and_registered_original_tampering_fail(self):
        edited = copy.deepcopy(self.inventory)
        edited['assets'].pop()
        put(self.root, 'inputs/edited.json', edited)
        with self.assertRaisesRegex(ValueError, 'projection_changed'):
            v.source_inventory(self.root, self.original, 'inputs/edited.json')
        file = self.root / self.original
        file.write_bytes(file.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            ap.businessobjects_scope(*ap.load_project(self.root))
        with self.assertRaises(ValueError):
            v.requirements(self.root, 'contracts/visual.json')

    def test_unresolved_scope_cannot_be_silently_promoted(self):
        req = copy.deepcopy(self.req)
        obligation = next(i for i in req['items'] if i['source_identity']['declared_disposition'] != 'include')
        self.assertEqual(obligation['disposition'], 'defer')
        obligation['disposition'] = 'migrate'
        put(self.root, 'contracts/unreviewed.json', req)
        with self.assertRaisesRegex(ValueError, 'businessobjects_source_review_required'):
            v.requirements(self.root, 'contracts/unreviewed.json')
        obligation['scope_decision'] = {'reason': 'Synthetic reviewed adaptation with original dependency retained',
                                        'reference': 'Synthetic explicit review decision'}
        put(self.root, 'contracts/reviewed.json', req)
        v.requirements(self.root, 'contracts/reviewed.json')

    def test_equal_numbers_cannot_claim_qualified_businessobjects_parity(self):
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
        self.assertIn('source.businessobjects_case_capture_required', result['gaps'])


class BusinessObjectsNumericWorkflow(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic state-bound comparison', 'migration', 'both')
        self.fixture = capture_fixture.capture_fixture(self.root / 'inputs/fixture')
        original = str(self.fixture['capture_path'].relative_to(self.root))
        inventory = t.translate(self.fixture['capture_path'].read_bytes(), 'businessobjects-capture')
        put(self.root, 'inputs/inventory.json', inventory)
        for path in (original, 'inputs/inventory.json'):
            ap.register(self.root, 'sources', path, path)
        v.prepare(self.root, original, 'inputs/inventory.json', 'contracts/visual.json')
        req = v.load(self.root, 'contracts/visual.json')
        req.update(route='reuse_existing', route_reference='Synthetic reviewed reuse route')
        item = next(i for i in req['items'] if i['source_identity']['object_key'] == self.fixture['object_key'])
        case = next(c for c in item['required_cases'] if c['lane'] == 'numeric')
        case['source_capture'] = v.pin(self.root, original)
        case['source_binding'] = {k: self.fixture['binding'][k] for k in
            ('definition_fingerprint', 'state_sha256', 'object_key', 'attachment_id')}
        put(self.root, 'contracts/visual.json', req)
        put(self.root, 'evidence/normalized.json', self.fixture['normalized'])
        put(self.root, 'evidence/target.json', self.fixture['normalized']['rows'])
        put(self.root, 'evidence/candidate.json', {'kind': 'synthetic_candidate'})
        context = {**capture_fixture.state(),
            **{k: x for k, x in capture_fixture.result_contract().items() if k != 'reference'},
            'population': 'all-districts', 'data_watermark': '2026-01-01', 'result_scope': 'query_result'}
        self.spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec',
            'case_id': case['case_id'], 'requirements': v.pin(self.root, 'contracts/visual.json'),
            'candidate': v.pin(self.root, 'evidence/candidate.json'),
            'persona_equivalence_reference': 'Synthetic independent persona review', 'keys': ['district'],
            'columns': [{'name': 'district', 'type': 'string', 'source': 'district', 'target': 'district'},
                        {'name': 'yield', 'type': 'number', 'source': 'yield', 'target': 'yield'}],
            'source': {'file': v.pin(self.root, 'evidence/normalized.json'), 'format': 'businessobjects-normalized',
                'raw_file': v.pin(self.root, str(self.fixture['raw_path'].relative_to(self.root))),
                'context': context, 'complete': True, 'completeness_reference': 'Synthetic full scoped results'},
            'target': {'file': v.pin(self.root, 'evidence/target.json'), 'format': 'json',
                'context': {**copy.deepcopy(context), 'cache': 'Independent target policy'},
                'complete': True, 'completeness_reference': 'Synthetic target completeness'}}

    def compare(self, spec, name):
        put(self.root, 'contracts/' + name + '.json', spec)
        path = 'evidence/' + name + '.json'
        v.compare(self.root, 'contracts/' + name + '.json', path)
        return v.load(self.root, path)

    def test_complete_bound_results_pass_local_comparison_with_independent_cache_policy(self):
        result = self.compare(self.spec, 'valid')
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['gaps'], [])
        self.assertEqual(self.fixture['normalized']['rows'][0]['yield'], '1.100000000000000001')

    def test_changed_value_fails_and_changed_state_or_subset_is_inconclusive(self):
        rows = copy.deepcopy(self.fixture['normalized']['rows'])
        rows[1]['yield'] = '9007199254740992'
        put(self.root, 'evidence/changed.json', rows)
        spec = copy.deepcopy(self.spec)
        spec['target']['file'] = v.pin(self.root, 'evidence/changed.json')
        self.assertEqual(self.compare(spec, 'different')['status'], 'fail')
        spec = copy.deepcopy(self.spec)
        spec['target']['context']['parameters']['contexts'].append({'id': 'other'})
        self.assertEqual(self.compare(spec, 'state')['status'], 'inconclusive')
        spec = copy.deepcopy(self.spec)
        spec['columns'] = spec['columns'][:1]
        result = self.compare(spec, 'subset')
        self.assertEqual(result['status'], 'inconclusive')
        self.assertIn('source.businessobjects_compared_columns_incomplete', result['gaps'])

    def test_resealed_normalized_values_cannot_replace_pinned_raw_values(self):
        normalized = copy.deepcopy(self.fixture['normalized'])
        normalized['rows'][0]['yield'] = '1.1'
        put(self.root, 'evidence/normalized-changed.json', normalized)
        spec = copy.deepcopy(self.spec)
        spec['source']['file'] = v.pin(self.root, 'evidence/normalized-changed.json')
        with self.assertRaisesRegex(ValueError, 'normalization_changed'):
            self.compare(spec, 'tampered')


class BusinessObjectsDmaJourney(e.MigrationJourney):
    def source(self):
        original, inventory, req = setup_source(self.root)
        req.update(route='omni_semantic_reconstruction')
        put(self.root, 'contracts/visual.json', req)
        self.source_paths = [original, 'inputs/inventory.json']
        self.source_pins = {p: e.sha(self.root / p) for p in self.source_paths}
        self.inventories, self.assets, self.source_gaps = [inventory], inventory['assets'], inventory['gaps']
        self.platform, self.route = 'businessobjects', 'omni_semantic_reconstruction'

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
            e.bridge.verify_businessobjects_inventory(self.root, ap.load_project(self.root)[1], self.source_paths[1])


if __name__ == '__main__':
    unittest.main()
