"""Focused offline qualification checks using original synthetic records only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/omni-app-engineer/scripts/native_query_probe.py'
spec = importlib.util.spec_from_file_location('native_query_probe', SCRIPT)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class NativeQueryProbeTests(unittest.TestCase):
    def test_integer_requires_lossless_native_json_range(self):
        field = {'type': 'integer', 'nullable': False}
        self.assertTrue(P.valid_value(2 ** 53 - 1, field))
        self.assertFalse(P.valid_value(2 ** 53, field))
        self.assertFalse(P.valid_value(10 ** 100, field))
        self.assertFalse(P.valid_value(True, field))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.identity = dict(connection_id='synthetic-connection', database='REQUESTED_DB', schema='PUBLIC',
                             model_id='synthetic-workbook', query_name='Observed items')
        self.query = {'fields': ['items.id', 'items.amount', 'items.ready'],
                      'filters': {'items.group': {'type': 'string', 'kind': 'EQUALS', 'values': ['sample']}}, 'limit': 10}
        self.contract = {'schema_version': 1, 'kind': 'native_query_probe_contract', 'requested': self.identity,
                         'query': self.query, 'grain': ['items.id'], 'complete_status': 'done',
                         'fields': [{'key': 'items.id', 'type': 'string', 'nullable': False, 'metadata_type': 'TEXT'},
                                    {'key': 'items.amount', 'type': 'decimal_string', 'nullable': True, 'metadata_type': 'DECIMAL'},
                                    {'key': 'items.ready', 'type': 'boolean', 'nullable': False, 'metadata_type': 'BOOL'}],
                         'metadata': {'layout': 'list', 'name_key': 'name', 'type_key': 'type'},
                         'concurrency': {'mode': 'serialized', 'max_in_flight': 1, 'qualification': 'unavailable'},
                         'selectors': {key: '/' + key for key in P.SELECTORS}}
        self.evidence = {'lane': 'query_export', 'provenance': {'reference': 'synthetic capture'},
                         'binding': copy.deepcopy(self.identity), 'query': copy.deepcopy(self.query),
                         'status': 'done', 'limit': 10, 'truncated': False, 'exhaustive': True, 'total_rows': 3,
                         'columns': [{'name': f['key'], 'type': f['metadata_type']} for f in self.contract['fields']],
                         'rows': [{'items.id': 'one', 'items.amount': '0.10', 'items.ready': True},
                                  {'items.id': 'two', 'items.amount': None, 'items.ready': False},
                                  {'items.id': 'three', 'items.amount': '0.20', 'items.ready': True}]}
        source = {'n': 3, 'amount_sum': '0.30', 'amount_known': 2, 'ready': 2, 'ready_known': 3}
        raw = json.dumps(source).encode()
        (self.root / 'independent.json').write_bytes(raw)
        self.expected = {'schema_version': 1, 'kind': 'native_query_probe_expectations',
                         'provenance': {'method': 'independent_query', 'reference': 'independent.json',
                                        'sha256': hashlib.sha256(raw).hexdigest()},
                         'requested': copy.deepcopy(self.identity), 'filters': copy.deepcopy(self.query['filters']),
                         'rows': 3, 'rows_pointer': '/n',
                         'aggregates': [{'id': 'amount', 'op': 'sum', 'field': 'items.amount', 'expected': '0.30',
                                         'non_null_rows': 2, 'expected_pointer': '/amount_sum', 'non_null_pointer': '/amount_known'},
                                        {'id': 'ready', 'op': 'count_true', 'field': 'items.ready', 'expected': 2,
                                         'non_null_rows': 3, 'expected_pointer': '/ready', 'non_null_pointer': '/ready_known'}]}

    def check(self, evidence=None, expected=None, contract=None):
        return P.probe(contract or self.contract, evidence or self.evidence, expected or self.expected, self.root)

    def codes(self, result):
        return {f['code'] for f in result['findings']}

    def test_valid_exact_decimal_null_population_and_cli_stay_offline(self):
        result = self.check()
        self.assertEqual(result['status'], 'consistent')
        self.assertEqual(result['aggregate_comparisons'][0]['actual'], '0.30')
        self.assertFalse(result['native_execution_verified'])
        self.assertEqual(result['native_callback'], 'not_observed')
        self.assertEqual(result['recovery'], 'not_executed')
        for name, value in [('contract', self.contract), ('evidence', self.evidence), ('expectations', self.expected)]:
            (self.root / (name + '.json')).write_text(json.dumps(value))
        run = subprocess.run([sys.executable, '-I', '-S', '-B', str(SCRIPT), '--contract', str(self.root / 'contract.json'),
                              '--evidence', str(self.root / 'evidence.json'), '--expectations', str(self.root / 'expectations.json')],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertEqual(set(json.loads(run.stdout)['input_pins']), {'contract', 'evidence', 'expectations'})

    def test_wrong_source_narrowed_query_and_missing_metadata_fail(self):
        cases = [('binding_mismatch', lambda e: e['binding'].update(database='OTHER_DB')),
                 ('query_or_population_mismatch', lambda e: e['query']['filters'].clear()),
                 ('field_metadata_missing', lambda e: e.update(columns=[])),
                 ('field_metadata_type_mismatch', lambda e: e['columns'][1].update(type='TEXT')),
                 ('observation_missing', lambda e: e.pop('columns'))]
        for code, mutate in cases:
            with self.subTest(code=code):
                evidence = copy.deepcopy(self.evidence); mutate(evidence)
                self.assertIn(code, self.codes(self.check(evidence)))

    def test_unknown_types_nulls_duplicates_and_partial_population_fail(self):
        cases = [('row_type_or_null_mismatch', lambda e: e['rows'][0].update({'items.ready': 1})),
                 ('row_type_or_null_mismatch', lambda e: e['rows'][1].update({'items.amount': ''})),
                 ('grain_duplicate', lambda e: e['rows'][1].update({'items.id': 'one'})),
                 ('row_field_set_mismatch', lambda e: e['rows'][0].pop('items.amount')),
                 ('row_count_mismatch', lambda e: e['rows'].pop()),
                 ('truncation_not_excluded', lambda e: e.update(truncated=True)),
                 ('population_not_exhausted', lambda e: e.update(exhaustive=False))]
        for code, mutate in cases:
            with self.subTest(code=code):
                evidence = copy.deepcopy(self.evidence); mutate(evidence)
                self.assertIn(code, self.codes(self.check(evidence)))
        contract = copy.deepcopy(self.contract); contract['query']['limit'] = 3
        evidence = copy.deepcopy(self.evidence); evidence['limit'] = 3; evidence['query']['limit'] = 3
        self.assertIn('cap_reached_increase_limit_or_qualify_pagination', self.codes(self.check(evidence, contract=contract)))

    def test_independent_source_and_aggregate_denominators_cannot_be_replaced_by_flags(self):
        evidence = copy.deepcopy(self.evidence); evidence['rows'][0]['items.amount'] = '0.11'
        self.assertIn('aggregate_or_denominator_mismatch', self.codes(self.check(evidence)))
        expected = copy.deepcopy(self.expected); expected['aggregates'][0]['non_null_rows'] = 3
        self.assertIn('expectation_source_value_mismatch', self.codes(self.check(expected=expected)))
        (self.root / 'independent.json').unlink()
        self.assertIn('expectation_source_unavailable_or_invalid', self.codes(self.check()))
        self.assertIn('expectation_source_not_loaded', self.codes(P.probe(self.contract, self.evidence, self.expected)))

    def test_fixture_cannot_qualify_correlation_and_unqualified_work_must_serialize(self):
        contract = copy.deepcopy(self.contract)
        contract['concurrency'].update(mode='correlated', max_in_flight=2)
        with self.assertRaisesRegex(ValueError, 'otherwise serialize'):
            self.check(contract=contract)
        contract['concurrency'].update(qualification='native_observed', evidence_ref='missing-correlation.json',
                                       evidence_sha256='0' * 64)
        evidence = copy.deepcopy(self.evidence); evidence['lane'] = 'constructed_fixture'
        result = self.check(evidence, contract=contract)
        self.assertIn('correlation_requires_native_evidence', self.codes(result))
        self.assertIn('correlation_evidence_unavailable_or_invalid', self.codes(result))

    def test_unsafe_json_pointers_and_symlinks_are_rejected(self):
        for raw in ['{"x":1,"x":2}', '{"x":NaN}']:
            (self.root / 'bad.json').write_text(raw)
            with self.assertRaises(ValueError):
                P.read(self.root / 'bad.json')
        (self.root / 'alias.json').symlink_to(self.root / 'independent.json')
        with self.assertRaises(ValueError):
            P.read(self.root / 'alias.json')
        with self.assertRaises(ValueError):
            P.pointer({}, '/bad~2key')
        with self.assertRaises(ValueError):
            P.pointer({}, '/' + 'x' * 4096)


if __name__ == '__main__':
    unittest.main()
