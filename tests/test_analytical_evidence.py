"""Original result identity fixtures; no source-system or native execution."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts/analytical_evidence.py'
_spec = importlib.util.spec_from_file_location('analytical_test', SCRIPT)
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


class AnalyticalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        A.P.init(self.root, 'Original result contract', 'migration', 'dashboard', branding='none')

    def save(self, path, value):
        A.P.write_json(self.root / path, value)
        return {'path': path, 'sha256': A.P.digest((self.root / path).read_bytes())}

    def request(self, layout, data):
        return {'source': self.save('inputs/rows.json', data), 'layout': layout,
            'source_fields': ['entity', 'amount'], 'bindings': [{'source': 'entity', 'target': 'entity_id'},
            {'source': 'amount', 'target': 'value'}], 'output': 'evidence/normalized.json'}

    def test_object_order_does_not_rebind_values_and_zero_is_not_null(self):
        request = self.request('objects', [{'amount': 0, 'entity': 'first'}, {'entity': 'second', 'amount': None}])
        result = A.normalize(self.root, request)
        rows = A.P.read_json(self.root / result['output']['path'])[0]
        self.assertEqual(rows, [{'entity_id': 'first', 'value': 0}, {'entity_id': 'second', 'value': None}])
        self.assertFalse(result['values_transformed'])

    def test_column_metadata_controls_mapping(self):
        request = self.request('columnar', {'columns': ['amount', 'entity'], 'rows': [[-2, 'first'], [0, 'second']]})
        A.normalize(self.root, request)
        self.assertEqual(A.P.read_json(self.root / request['output'])[0][0], {'entity_id': 'first', 'value': -2})

    def test_unexpected_or_duplicate_fields_are_rejected(self):
        request = self.request('objects', [{'entity': 'first', 'amount': 2, 'new_field': 1}])
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            A.normalize(self.root, request)
        request['bindings'][1]['target'] = 'entity_id'
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            A.normalize(self.root, request)

    def test_positional_rows_without_metadata_are_rejected(self):
        request = self.request('columnar', [['first', 2]])
        with self.assertRaisesRegex(ValueError, 'column metadata'):
            A.normalize(self.root, request)

    def test_lossy_numeric_tokens_are_rejected_without_output(self):
        request = self.request('objects', [])
        raw = b'[{"entity":"first","amount":9007199254740993.0}]'
        (self.root / 'inputs/rows.json').write_bytes(raw)
        request['source']['sha256'] = A.P.digest(raw)
        with self.assertRaisesRegex(ValueError, 'Numeric precision'):
            A.normalize(self.root, request)
        self.assertFalse((self.root / request['output']).exists())

    def test_comparator_preserves_original_json_decimal_precision(self):
        raw = b'[{"amount":9007199254740993.0}]'
        path = 'inputs/decimal-results.json'
        (self.root / path).write_bytes(raw)
        workflow = A.P.routing_helper('visual_workflow')
        row = workflow.rows(self.root, {'file': {'path': path, 'sha256': A.P.digest(raw)}, 'format': 'json'})[0]
        self.assertEqual(str(workflow.cell(row['amount'], {'type': 'number'})), '9007199254740993.0')
        with self.assertRaisesRegex(ValueError, 'string_required'):
            workflow.cell(row['amount'], {'type': 'string'})

    def test_expanded_output_is_bounded_before_write(self):
        request = self.request('columnar', {'columns': ['entity', 'amount'], 'rows': [['a', 2]] * 6})
        request['bindings'][0]['target'] = 'long-field-name-' * 10
        with patch.object(A, 'MAX_OUTPUT_BYTES', 500):
            with self.assertRaisesRegex(ValueError, 'output exceeds byte budget'):
                A.normalize(self.root, request)
        self.assertFalse((self.root / request['output']).exists())

    def test_parsing_uses_exact_verified_buffer_not_a_second_read(self):
        request = self.request('objects', [{'entity': 'first', 'amount': 2}])
        original = Path.read_bytes
        reads = []
        def read(path):
            value = original(path)
            if path == self.root / 'inputs/rows.json':
                reads.append(path)
                path.write_bytes(b'[{"entity":"replaced","amount":9}]')
            return value
        with patch.object(Path, 'read_bytes', read):
            A.normalize(self.root, request)
        self.assertEqual(len(reads), 1)
        self.assertEqual(A.P.read_json(self.root / request['output'])[0][0]['entity_id'], 'first')

    def provenance(self):
        source = self.save('inputs/source-results.json', [{'value': 2}])
        target = self.save('inputs/target-results.json', [{'value': 2}])
        evidence = self.save('inputs/original-observation.json', {'fixture_only': True})
        provenance = {'source_basis': 'original_results',
            'source': {'system_ref': 'source-system', 'artifact_id': 'original-object', 'version': '1'},
            'target': {'system_ref': 'target-system', 'artifact_id': 'candidate-object', 'version': '1'},
            'original_results': source, 'execution_evidence': [evidence]}
        return {'source': {'file': source}, 'target': {'file': target}}, provenance

    def test_equal_result_bytes_are_valid_but_same_file_is_not_independent(self):
        spec, value = self.provenance()
        pin = self.save('inputs/provenance.json', value)
        self.assertFalse(A.validate_comparison_provenance(self.root, spec, pin)['source_execution_authenticated'])
        spec['target']['file'] = spec['source']['file']
        with self.assertRaisesRegex(ValueError, 'same result file'):
            A.validate_comparison_provenance(self.root, spec, pin)

    def test_target_self_consistency_and_stale_evidence_are_rejected(self):
        spec, value = self.provenance()
        value['source_basis'] = 'target_self_consistency'
        pin = self.save('inputs/provenance.json', value)
        with self.assertRaisesRegex(ValueError, 'not independent'):
            A.validate_comparison_provenance(self.root, spec, pin)
        (self.root / pin['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            A.validate_comparison_provenance(self.root, spec, pin)


if __name__ == '__main__':
    unittest.main()
