"""Original neutral Crystal extraction fixtures; no RPT decoder, SDK or execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


C = load('crystal_report_under_test', 'skills/omni-artifact-translator/scripts/crystal_report.py')
T = load('crystal_translator_under_test', 'skills/omni-artifact-translator/scripts/translate_artifact.py')


def extraction_fixture():
    return {'schema_version': C.EXTRACT_SCHEMA, 'report': {'name': 'Synthetic observation report'},
        'objects': [
            {'id': 'report', 'parent_id': None, 'kind': 'report', 'name': 'Synthetic report', 'properties': {}},
            {'id': 'detail', 'parent_id': 'report', 'kind': 'section', 'name': 'Detail', 'properties': {'suppress': 'When empty'}},
            {'id': 'data', 'parent_id': 'report', 'kind': 'query', 'name': 'Observations', 'properties': {'sql': 'SELECT observation_id, amount FROM synthetic_observations'}},
            {'id': 'chart', 'parent_id': 'detail', 'kind': 'chart', 'name': 'Observation totals', 'properties': {'display': 'bars'}},
            {'id': 'formula', 'parent_id': 'detail', 'kind': 'formula', 'name': 'Running label',
             'properties': {'syntax': 'Crystal', 'text': 'WhilePrintingRecords; Shared NumberVar observed; observed', 'suppressed': True}},
            {'id': 'footer', 'parent_id': 'report', 'kind': 'section', 'name': 'Report footer', 'properties': {'keep_together': True}}],
        'dependencies': [{'from_id': 'chart', 'target_id': 'data', 'kind': 'dataset_binding', 'reference': 'Synthetic supplier mapping'},
                         {'from_id': 'formula', 'target_id': None, 'kind': 'shared_variable', 'reference': 'External evaluation order unresolved'}]}


def identity():
    return {'source_platform': 'crystal', 'source_origin': None, 'product_version': 'unverified',
            'engine': 'crystal_classic', 'principal_ref': 'synthetic-supplier', 'report_id': None,
            'cuid': None, 'content_path': None, 'reference': 'Original synthetic extraction fixture'}


def snapshot_fixture():
    extract = extraction_fixture()
    inventory = {'reference': 'Independent synthetic expected-object inventory', 'completeness': 'selected_scope_declared',
        'items': [{'key': o['id'], 'object_id': o['id'], 'kind': o['kind'], 'disposition': 'include',
                   'reference': 'Synthetic object obligation', 'configuration': {}} for o in extract['objects']]}
    return C.make_snapshot(C.encoded(extract), identity(), inventory, 'Synthetic raw extraction')


def replace_extraction(snapshot, extracted):
    raw = C.encoded(extracted)
    snapshot['extraction'].update(content=raw.decode(), bytes=len(raw), sha256=C.sha(raw))
    return snapshot


def projected(snapshot=None):
    return T.translate(C.encoded(snapshot or snapshot_fixture()), 'crystal-report')


class CrystalReportTests(unittest.TestCase):
    def test_projection_is_inert_and_preserves_original_formula_and_dependencies(self):
        snapshot = snapshot_fixture(); result = projected(snapshot)
        self.assertEqual(result['upstream_payload'], snapshot)
        self.assertFalse(result['source_execution']); self.assertEqual(result['network_calls'], 0)
        self.assertFalse(result['migration_context']['build_authority'])
        formula = next(a for a in result['assets'] if a['source_identity']['extractor_object_id'] == 'formula')
        self.assertEqual(formula['source_payload']['object']['properties'], extraction_fixture()['objects'][4]['properties'])
        self.assertTrue(formula['source_identity']['requires_source_review'])
        self.assertIn('crystal.formula_not_compiled', {g['code'] for g in result['gaps']})
        self.assertEqual(result['dependencies'][1]['status'], 'unresolved_external_dependency')
        self.assertEqual(result['source']['provenance_assurance'], 'supplier_declared_not_authenticated')

    def test_missing_inventory_never_erases_original_object_obligations(self):
        snapshot = snapshot_fixture(); snapshot['inventory']['items'] = []
        result = projected(snapshot)
        self.assertEqual(len(result['assets']), len(extraction_fixture()['objects']))
        self.assertEqual(result['crystal_coverage']['additional_object_obligations'], len(extraction_fixture()['objects']))
        self.assertTrue(all(a['source_identity']['requires_source_review'] for a in result['assets']))
        self.assertTrue(all(a['source_identity']['declared_disposition'] == 'manual_review' for a in result['assets']))
        self.assertIn('crystal.extraction_completeness_not_established', {g['code'] for g in result['gaps']})

    def test_expected_missing_object_remains_an_explicit_obligation(self):
        snapshot = snapshot_fixture()
        snapshot['inventory']['items'].append({'key': 'missing-subreport', 'object_id': None, 'kind': 'subreport',
            'disposition': 'unavailable', 'reference': 'Independent expected subreport', 'configuration': {}})
        result = projected(snapshot)
        missing = next(a for a in result['assets'] if a['source_identity']['object_key'] == 'missing-subreport')
        self.assertTrue(missing['source_identity']['requires_source_review'])
        self.assertFalse(missing['source_identity']['query_visual'])
        self.assertIn('crystal.expected_object_without_extraction', {g['code'] for g in result['gaps']})

    def test_restricted_visual_parent_is_inherited(self):
        for config, disposition in [({'access': 'denied'}, 'include'), ({'private': True}, 'include'),
                                    ({}, 'out_of_scope'), ({}, 'exclude')]:
            snapshot = snapshot_fixture(); row = next(r for r in snapshot['inventory']['items'] if r['key'] == 'detail')
            row.update(configuration=config, disposition=disposition)
            with self.subTest(config=config, disposition=disposition):
                scope = C.scope_item(snapshot, 'chart')
                self.assertTrue(scope['restricted']); self.assertFalse(scope['query_visual'])
                asset = next(a for a in projected(snapshot)['assets'] if a['source_identity']['object_key'] == 'chart')
                self.assertTrue(asset['source_identity']['restricted_private_scope'])

    def test_restricted_dataset_parent_cannot_qualify_public_visual(self):
        snapshot = snapshot_fixture(); extracted = extraction_fixture()
        extracted['objects'].append({'id': 'restricted-data', 'parent_id': 'report', 'kind': 'section',
                                     'name': 'Restricted source section', 'properties': {}})
        next(o for o in extracted['objects'] if o['id'] == 'data')['parent_id'] = 'restricted-data'
        replace_extraction(snapshot, extracted)
        snapshot['inventory']['items'].append({'key': 'restricted-data', 'object_id': 'restricted-data', 'kind': 'section',
            'disposition': 'out_of_scope', 'reference': 'Independent source boundary', 'configuration': {}})
        self.assertFalse(C.scope_item(snapshot, 'chart')['query_visual'])

    def test_dataset_binding_requires_one_retained_included_query(self):
        self.assertTrue(C.scope_item(snapshot_fixture(), 'chart')['query_visual'])
        snapshot = snapshot_fixture(); snapshot['inventory']['items'] = [r for r in snapshot['inventory']['items'] if r['key'] != 'data']
        self.assertFalse(C.scope_item(snapshot, 'chart')['query_visual'])
        snapshot = snapshot_fixture(); extracted = extraction_fixture(); extracted['dependencies'] = []
        replace_extraction(snapshot, extracted)
        self.assertFalse(C.scope_item(snapshot, 'chart')['query_visual'])
        snapshot = snapshot_fixture(); extracted = extraction_fixture()
        extracted['dependencies'].append(copy.deepcopy(extracted['dependencies'][0])); replace_extraction(snapshot, extracted)
        self.assertFalse(C.scope_item(snapshot, 'chart')['query_visual'])

    def test_cycles_missing_parent_and_tampered_hash_reject(self):
        for parent in ('detail', 'missing-parent'):
            extracted = extraction_fixture(); extracted['objects'][0]['parent_id'] = parent
            with self.subTest(parent=parent), self.assertRaises(ValueError): C.read_extraction(C.encoded(extracted))
        snapshot = snapshot_fixture(); snapshot['extraction']['sha256'] = 'a' * 64
        with self.assertRaisesRegex(ValueError, 'extraction_hash'): C.validate_snapshot(snapshot)
        snapshot = snapshot_fixture(); snapshot['inventory']['items'][0]['kind'] = 'chart'
        with self.assertRaisesRegex(ValueError, 'inventory_kind_mismatch'): C.validate_snapshot(snapshot)

    def test_duplicate_json_credentials_and_binary_rpt_are_not_loaded(self):
        for raw in (b'{"x":1,"x":2}', b'\x00RPT\xffopaque', b'not-json'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): C.read_extraction(raw)
        extracted = extraction_fixture(); extracted['report']['password'] = 'synthetic-secret'
        with self.assertRaises(ValueError): C.read_extraction(C.encoded(extracted))
        snapshot = snapshot_fixture(); snapshot['identity']['source_origin'] = 'https://user:secret@example.invalid'
        with self.assertRaises(ValueError): C.validate_snapshot(snapshot)

    def test_engine_and_version_remain_qualification_gaps(self):
        for engine in ('crystal_classic', 'crystal_enterprise', 'unknown'):
            snapshot = snapshot_fixture(); snapshot['identity']['engine'] = engine
            result = projected(snapshot)
            with self.subTest(engine=engine):
                self.assertIn('crystal.engine_version_unqualified', {g['code'] for g in result['gaps']})
                self.assertEqual(result['native_validation'], 'not_run')
                self.assertEqual(result['export_completeness'], 'not_established')


if __name__ == '__main__': unittest.main()
