"""Original Strategy fixtures across typed routing, A-F, comparison and DMA."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
f = load('ms_visual_fixture', 'tests/test_microstrategy_visual.py')
e = load('ms_migration_fixture', 'tests/test_migration_e2e.py')
m = load('migration', 'skills/omni-backend-handoff/scripts/migration.py')
s = load('ms_standalone', 'skills/omni-backend-handoff/scripts/standalone.py')


def put(root, path, value):
    file = root / path; file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value))


def setup_source(root, evidence=False, transform=None):
    request, out = f.prepare(root / 'inputs', transform)
    if evidence: _, out = f.add_results(root / 'inputs', request, out)
    original = str(Path(out['output']).relative_to(root))
    inventory = f.T.translate(Path(out['output']).read_bytes(), 'microstrategy-capture')
    inv_path = 'inputs/source-inventory.json'; put(root, inv_path, inventory)
    for path in (original, inv_path): ap.register(root, 'sources', path, path)
    v.prepare(root, original, inv_path, 'contracts/visual.json')
    req = v.load(root, 'contracts/visual.json')
    req.update(route='reuse_existing', route_reference='Synthetic existing-model route')
    put(root, 'contracts/visual.json', req)
    return request, out, original, inventory, req


class MicrostrategyWorkflow(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic source workflow', 'migration', 'both')
        self.request, self.out, self.original, self.inventory, self.req = setup_source(self.root, True)

    def test_denominator_and_specialist_do_not_bypass_choice_gate(self):
        root, obj = ap.load_project(self.root)
        self.assertTrue(ap.microstrategy_scope(root, obj))
        self.assertEqual(len(v.requirements(root, 'contracts/visual.json')[1]['items']), len(self.inventory['assets']))
        self.assertEqual(len(s.query_source_keys(self.req)), 3)
        self.assertEqual(len(s.control_source_keys(self.req)), 3)
        for item in self.req["items"]:
            if not item["source_identity"].get("query_visual"):
                self.assertFalse(any(c["lane"] == "numeric" for c in item["required_cases"]))
        item = next(x for x in self.req['items'] if x['source_id'] == 'left')
        self.assertTrue(any(c['case_id'].endswith('/interaction/prompt_key_and_selector_state') for c in item['required_cases']))
        with self.assertRaises(ValueError):
            ap.stage_packet_gate(root, 'microstrategy-migrator', {'stage': 'discovery', 'outputs': ['app.html']})

    def test_projection_tampering_and_raw_byte_drift_cannot_roundtrip(self):
        value = copy.deepcopy(self.inventory); value['assets'].pop()
        put(self.root, 'inputs/edited.json', value)
        with self.assertRaisesRegex(ValueError, 'projection_changed'):
            v.source_inventory(self.root, self.original, 'inputs/edited.json')
        pin = self.out['capture']['source']['originals'][0]['file']
        (Path(self.out['output']).parent / pin['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError): v.requirements(self.root, 'contracts/visual.json')

    def test_exact_normalization_is_replayed_in_shared_numeric_comparison(self):
        cap = self.out['capture']; pin = cap['attachments'][0]
        raw_path = str((Path(self.out['output']).parent / pin['path']).relative_to(self.root))
        raw = (self.root / raw_path).read_bytes(); normalized = f.normalized_for(cap, raw)
        put(self.root, 'evidence/normalized.json', normalized)
        record = {'format': 'microstrategy-normalized', 'file': v.pin(self.root, 'evidence/normalized.json'),
                  'raw_file': v.pin(self.root, raw_path)}
        rows = v.rows(self.root, record)
        self.assertEqual(rows[1]['yield'], '9007199254740993')
        self.assertEqual(rows[0]['yield'], '1.100000000000000001')
        item = next(i for i in self.req['items'] if i['source_id'] == 'left')
        case = next(c for c in item['required_cases'] if c['lane'] == 'numeric')
        case.update(source_capture=v.pin(self.root, self.original), source_binding={
            'object_key': 'yield', 'placement_key': 'left', 'state_sha256': f.V.sha(cap['request']['state']),
            'definition_fingerprint': cap['source']['definition_fingerprint'], 'attachment_id': pin['attachment_id']})
        put(self.root, 'contracts/visual.json', self.req)
        context = {**copy.deepcopy(self.request['state']), **{k: val for k, val in f.result_contract().items() if k != 'reference'},
            'result_context_reference': f.result_contract()['reference'], 'population': pin['population']['key'],
            'data_watermark': pin['freshness']['data_watermark'], 'freshness_reference': pin['freshness']['reference'],
            'result_scope': pin['result_scope'], 'instance_id': f.INSTANCE, 'result_definition_sha256': f.V.sha(f.definition())}
        put(self.root, 'evidence/target.json', [{'district': 'West', 'yield': '1.100000000000000001'},
                                              {'district': 'East', 'yield': '9007199254740993'}])
        put(self.root, 'evidence/candidate.json', {'kind': 'synthetic_candidate'})
        spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case['case_id'],
            'requirements': v.pin(self.root, 'contracts/visual.json'), 'candidate': v.pin(self.root, 'evidence/candidate.json'),
            'source': {**record, 'context': context, 'complete': True, 'completeness_reference': 'Synthetic full response'},
            'target': {'file': v.pin(self.root, 'evidence/target.json'), 'format': 'json', 'context': copy.deepcopy(context),
                       'complete': True, 'completeness_reference': 'Synthetic independent expectation'},
            'persona_equivalence_reference': 'Synthetic persona equivalence', 'keys': ['district'], 'columns': [
                {'name': 'district', 'type': 'string', 'source': 'district', 'target': 'district'},
                {'name': 'yield', 'type': 'number', 'source': 'yield', 'target': 'yield'}]}
        put(self.root, 'contracts/compare.json', spec)
        v.compare(self.root, 'contracts/compare.json', 'evidence/compare.json')
        self.assertEqual(v.load(self.root, 'evidence/compare.json')['status'], 'pass')
        spec['target']['context']['data_watermark'] = 'stale'; put(self.root, 'contracts/compare.json', spec)
        v.compare(self.root, 'contracts/compare.json', 'evidence/stale.json')
        self.assertEqual(v.load(self.root, 'evidence/stale.json')['status'], 'inconclusive')
        normalized['rows'][0]['yield'] = '1.1'; put(self.root, 'evidence/normalized.json', normalized)
        record['file'] = v.pin(self.root, 'evidence/normalized.json')
        with self.assertRaisesRegex(ValueError, 'normalization_changed'): v.rows(self.root, record)


class MicrostrategyDmaJourney(e.MigrationJourney):
    def source(self):
        _, self.out, original, inventory, req = setup_source(self.root, transform=lambda x: x['inventory']['items'][6]['configuration'].update(private=True))
        req.update(route='omni_semantic_reconstruction', route_reference='Synthetic semantic route')
        put(self.root, 'contracts/visual.json', req)
        self.source_paths = [original, 'inputs/source-inventory.json']
        self.source_pins = {p: e.sha(self.root / p) for p in self.source_paths}
        self.inventories, self.assets, self.source_gaps = [inventory], inventory['assets'], inventory['gaps']
        self.platform, self.route = 'microstrategy', 'omni_semantic_reconstruction'

    def request(self, *args, **kwargs):
        all_assets = self.assets
        self.assets = [a for a in all_assets if not a['source_identity'].get('restricted_private_scope')]
        try:
            return super().request(*args, **kwargs)
        finally:
            self.assets = all_assets

    def scope(self):
        units = []
        for a in self.assets:
            private = a['source_identity'].get('restricted_private_scope') is True
            units.append({'unit_id': 'u-' + str(len(units)), 'inventory_path': self.source_paths[1],
                'asset_keys': [a['asset_key']], 'disposition': 'defer' if private else 'migrate',
                'rationale': 'Synthetic private scope requires explicit selection',
                'frontend_asset_ids': [] if private else [a['asset_key']], 'surfaces': [] if private else ['dashboard']})
        spec = {'schema_version': 1, 'kind': 'analyst_migration_scope_spec', 'scope_id': 'synthetic-scope',
            'decision_reference': 'Synthetic scoped review', 'inventory_paths': [self.source_paths[1]], 'backend_context_path': None, 'units': units}
        put(self.root, 'contracts/scope-spec.json', spec)
        m.freeze(self.root, 'contracts/scope-spec.json', 'evidence/migration-scope-v1.json')
        return m, v.load(self.root, 'evidence/migration-scope-v1.json'), units

    def return_spec(self, selected, scope, units):
        return super().return_spec(selected, scope, [u for u in units if u['disposition'] == 'migrate'])

    def test_private_obligation_and_originals_survive_dma(self):
        self.source(); migration, scope, units = self.scope()
        request = self.request(migration_scope_path='evidence/migration-scope-v1.json')
        self.assertEqual(request['migration_sources'][0]['original_source']['path'], self.source_paths[0])
        self.receive(self.response()); selected = self.select()
        self.assertFalse(selected['accepted']); self.assertFalse(selected['authorizes_target_write'])
        self.frontend_records(selected)
        report = self.prepare_return(migration, self.return_spec(selected, scope, units))['report']
        self.assertEqual(report['candidate_coverage'], 'incomplete')
        self.assertIn({'code': 'missing_surface_delivery', 'surface': 'dashboard'}, report['gaps'])
        spec = v.load(self.root, 'contracts/scope-spec.json')
        unit = next(u for u in spec['units'] if u['disposition'] == 'defer')
        unit.update(disposition='migrate', frontend_asset_ids=unit['asset_keys'], surfaces=['dashboard'])
        put(self.root, 'contracts/private.json', spec)
        with self.assertRaisesRegex(ValueError, 'private source scope'): m.build_scope(self.root, ap.load_project(self.root)[1], 'contracts/private.json')

    def test_semantic_route_does_not_authorize_warehouse_changes(self):
        self.source(); self.scope(); self.request(migration_scope_path='evidence/migration-scope-v1.json')
        with self.assertRaisesRegex(ValueError, 'violates selected route'): self.response(action='warehouse_and_semantic_candidate')


if __name__ == '__main__': unittest.main()
