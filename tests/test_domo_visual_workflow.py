"""Source-only Domo integration: byte verification, parity and control coverage."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


F = module('domo_workflow_fixture', 'tests/test_domo_evidence.py')
sys.modules['analyst_project'] = module('domo_workflow_project_test', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
W = module('domo_visual_workflow_test', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
T = module('domo_translation_test', 'skills/omni-artifact-translator/scripts/translate_artifact.py')
S = module('domo_standalone_test', 'skills/omni-backend-handoff/scripts/standalone.py')


class DomoVisualWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'run'
        W.ap.init(self.root, 'Synthetic migration', 'migration', 'dashboard')
        self.folder = self.root / 'inputs' / 'capture'
        self.folder.mkdir()

    def put(self, path, value):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value))
        return W.pin(self.root, path)

    def prepare(self, capture=None):
        value = capture or F.fixture(self.folder)
        self.put('inputs/capture/capture.json', value)
        inv = T.translate((self.folder / 'capture.json').read_bytes(), 'domo-agent', F.D.PROFILE)
        self.put('inputs/inventory.json', inv)
        W.prepare(self.root, 'inputs/capture/capture.json', 'inputs/inventory.json', 'contracts/visual.json')
        req = W.load(self.root, 'contracts/visual.json')
        req.update(route='reuse_existing', route_reference='synthetic-route')
        self.put('contracts/visual.json', req)
        return value, req, inv

    def comparison(self):
        capture, _, source_case, source, target, normalized, _ = F.comparison_fixture(self.folder)
        capture, req, _ = self.prepare(capture)
        selected = next(i for i in req['items'] if i['source_identity']['object_key'] == 'place-a')
        case = next(c for c in selected['required_cases'] if c['lane'] == 'numeric')
        case.update(source_capture=W.pin(self.root, 'inputs/capture/capture.json'), source_binding=source_case['source_binding'])
        source.update(file=self.put('inputs/normalized.json', normalized),
                      raw_file=W.pin(self.root, 'inputs/capture/' + source['raw_file']['path']),
                      complete=True, completeness_reference='synthetic-complete')
        target.update(file=self.put('evidence/target.json', normalized['rows']), complete=True, completeness_reference='synthetic-complete')
        spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case['case_id'],
                'requirements': self.put('contracts/visual.json', req),
                'candidate': self.put('evidence/candidate.json', {'kind': 'synthetic'}), 'source': source, 'target': target,
                'persona_equivalence_reference': 'synthetic-persona', 'keys': ['zone'],
                'columns': [{'name': 'zone', 'source': 'zone', 'target': 'zone', 'type': 'string'},
                            {'name': 'amount', 'source': 'amount', 'target': 'amount', 'type': 'number'}]}
        self.put('contracts/comparison.json', spec)
        return capture, req, case, spec

    def test_source_inventory_rederives_projection_and_verifies_pinned_bytes(self):
        capture, req, inventory = self.prepare()
        rebuilt = W.source_inventory(self.root, 'inputs/capture/capture.json', 'inputs/inventory.json')
        self.assertEqual(rebuilt, inventory)
        self.assertEqual(len(req['items']), 5)
        (self.folder / 'originals/definitions.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'evidence_bytes_changed'):
            W.source_inventory(self.root, 'inputs/capture/capture.json', 'inputs/inventory.json')

    def test_bound_numeric_workflow_distinguishes_arithmetic_and_parity(self):
        self.comparison()
        W.compare(self.root, 'contracts/comparison.json', 'evidence/comparison.json')
        report = W.load(self.root, 'evidence/comparison.json')
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['arithmetic_status'], 'pass')
        self.assertEqual(report['domo_execution_parity'], 'supplied_bound_evidence_only')
        self.assertEqual(report['gaps'], [])
        self.assertEqual(report['native_validation'], 'not_established')

    def test_missing_capture_cannot_pass_even_when_rows_match(self):
        _, req, case, spec = self.comparison()
        case.pop('source_capture')
        spec['requirements'] = self.put('contracts/visual.json', req)
        self.put('contracts/comparison.json', spec)
        W.compare(self.root, 'contracts/comparison.json', 'evidence/comparison.json')
        report = W.load(self.root, 'evidence/comparison.json')
        self.assertEqual(report['status'], 'inconclusive')
        self.assertEqual(report['arithmetic_status'], 'pass')
        self.assertIn('source.domo_case_capture_required', report['gaps'])

    def test_resealed_normalized_rows_are_rederived_not_trusted(self):
        _, _, _, spec = self.comparison()
        normalized = W.load(self.root, spec['source']['file']['path'])
        normalized['rows'][0]['amount'] = '7'
        spec['source']['file'] = self.put('inputs/normalized.json', normalized)
        with self.assertRaisesRegex(ValueError, 'domo_normalization_changed'):
            W.rows(self.root, spec['source'])

    def test_parent_private_scope_cannot_be_changed_to_migrate(self):
        capture = F.fixture(self.folder)
        capture['inventory']['items'][0]['configuration']['private'] = True
        _, req, _ = self.prepare(F.seal(capture))
        self.assertTrue(all(i['disposition'] == 'defer' for i in req['items']))
        req['items'][1]['disposition'] = 'migrate'
        self.put('contracts/visual.json', req)
        with self.assertRaisesRegex(ValueError, 'private_scope_not_selected'):
            W.requirements(self.root, 'contracts/visual.json')

    def test_app_journey_cases_and_facets_cannot_vanish(self):
        capture = F.app_fixture(self.folder)
        _, req, _ = self.prepare(capture)
        component = next(i for i in req['items'] if i['source_identity']['inventory_kind'] == 'component')
        self.assertTrue(any(c['case_id'].endswith('complete_app_journey_and_persistent_state') for c in component['required_cases']))
        component['required_cases'] = [c for c in component['required_cases'] if not c['case_id'].endswith('complete_app_journey_and_persistent_state')]
        self.put('contracts/visual.json', req)
        with self.assertRaisesRegex(ValueError, 'required_cases_removed'):
            W.requirements(self.root, 'contracts/visual.json')

    def test_capture_has_no_detached_query_numeric_case(self):
        _, req, _ = self.prepare()
        query = next(i for i in req['items'] if i['source_identity']['inventory_kind'] == 'query')
        self.assertFalse(any(c['lane'] == 'numeric' for c in query['required_cases']))
        placements = [i for i in req['items'] if i['source_identity']['inventory_kind'] == 'placement']
        self.assertEqual(len(placements), 2)
        self.assertTrue(all(any(c['lane'] == 'numeric' for c in i['required_cases']) for i in placements))

    def test_legacy_producer_retains_import_and_arithmetic_only_status(self):
        capture = F.fixture(self.folder)
        raw = (self.folder / capture['producer']['file']['path']).read_bytes()
        source = F.D.decode(raw)
        self.put('inputs/original.json', source)
        inv = T.translate((self.root / 'inputs/original.json').read_bytes(), 'domo-agent', F.D.PRODUCER_PIN)
        self.put('inputs/inventory.json', inv)
        W.prepare(self.root, 'inputs/original.json', 'inputs/inventory.json', 'contracts/visual.json')
        req = W.load(self.root, 'contracts/visual.json')
        req.update(route='reuse_existing', route_reference='synthetic-route')
        card = next(i for i in req['items'] if i['kind'] == 'visual')
        self.assertEqual(card['disposition'], 'migrate')
        case = next(c for c in card['required_cases'] if c['lane'] == 'numeric')
        context = {'filters': {}, 'timezone': 'UTC', 'data_watermark': 'one', 'population': 'one', 'principal': 'synthetic-reader'}
        side = {'file': self.put('inputs/rows.json', [{'zone': 'one', 'amount': 5}]), 'format': 'json', 'context': context,
                'complete': True, 'completeness_reference': 'synthetic'}
        spec = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case['case_id'],
                'requirements': self.put('contracts/visual.json', req), 'candidate': self.put('evidence/candidate.json', {'kind': 'synthetic'}),
                'source': side, 'target': copy.deepcopy(side), 'persona_equivalence_reference': 'synthetic', 'keys': ['zone'],
                'columns': [{'name': 'zone', 'source': 'zone', 'target': 'zone', 'type': 'string'},
                            {'name': 'amount', 'source': 'amount', 'target': 'amount', 'type': 'number'}]}
        self.put('contracts/comparison.json', spec)
        W.compare(self.root, 'contracts/comparison.json', 'evidence/comparison.json')
        report = W.load(self.root, 'evidence/comparison.json')
        self.assertEqual(report['status'], 'inconclusive')
        self.assertEqual(report['arithmetic_status'], 'pass')
        self.assertIn('source.domo_execution_evidence_unqualified', report['gaps'])

    def test_legacy_and_current_control_obligations_are_not_dropped(self):
        requirements = {'surface': ['dashboard'], 'items': [
            {'asset_key': 'legacy-query', 'kind': 'query', 'disposition': 'migrate', 'target_surfaces': ['dashboard'],
             'source_identity': {'source_platform': 'domo'},
             'source_facets': {'filters': {'status': 'declared', 'value': {'control_ids': ['control-1']}}}},
            {'asset_key': 'component', 'kind': 'definition', 'disposition': 'migrate', 'target_surfaces': ['dashboard'],
             'source_identity': {'source_platform': 'domo', 'control_required': True}, 'source_facets': {}},
            {'asset_key': 'static-filter', 'kind': 'visual', 'disposition': 'migrate', 'target_surfaces': ['dashboard'],
             'source_identity': {'source_platform': 'domo'}, 'source_facets': {'filters': {'value': {'filters': ['static']}}}}]}
        with patch.object(S, '_native', return_value=SimpleNamespace(WORKFLOW=W)):
            self.assertEqual(S.control_source_keys(requirements), {'legacy-query', 'component'})
            self.put('inputs/controls.json', {'source': {'platform': 'domo'}})
            requirements['source_files'] = [{'path': 'inputs/original.json'}, {'path': 'inputs/controls.json'}]
            with self.assertRaisesRegex(ValueError, 'retained_source_control_unbound'):
                S.validate_control_bindings(self.root, {'bindings': [], 'control_bindings': []}, requirements, W)


if __name__ == '__main__':
    unittest.main()
