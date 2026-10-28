"""Original synthetic Metabase definitions. No source or native execution."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('test_metabase_' + name,
        ROOT / 'skills/omni-artifact-translator/scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


V, T = load('metabase_visual'), load('translate_artifact')


def snapshot():
    return {'schema_version': 'metabase-api-snapshot.v1',
        'identity': {'source_origin': 'https://bi.example.invalid', 'version': '0.64.1', 'principal_ref': 'synthetic-reader'},
        'dashboard': {'id': 1, 'name': 'Synthetic operations', 'tabs': [{'id': 2, 'name': 'Overview'}, {'id': 3, 'name': 'Detail'}],
            'parameters': [{'id': 'region', 'type': 'category', 'name': 'Region', 'default': ['West']}],
            'dashcards': [
                {'id': 100, 'card_id': 10, 'dashboard_tab_id': 2, 'row': 0, 'col': 0, 'size_x': 6, 'size_y': 4,
                 'parameter_mappings': [{'parameter_id': 'region', 'card_id': 10, 'target': ['dimension', ['field', 8, None]]}]},
                {'id': 101, 'card_id': 10, 'dashboard_tab_id': 3, 'row': 0, 'col': 0, 'size_x': 6, 'size_y': 4,
                 'parameter_mappings': [], 'visualization_settings': {'graph.colors': ['#123456']}},
                {'id': 102, 'card_id': None, 'dashboard_tab_id': 2,
                 'visualization_settings': {'virtual_card': {'display': 'text'}, 'text': 'Synthetic context'}}]},
        'cards': [{'id': 10, 'name': 'Quantity', 'display': 'bar',
                   'dataset_query': {'type': 'query', 'database': 1, 'query': {'source-table': 5,
                        'aggregation': [['sum', ['field', 7, None]]], 'breakout': [['field', 8, None]],
                        'filter': ['>', ['field', 7, None], 0]}}, 'visualization_settings': {}}],
        'metadata': [], 'coverage': {'dashboard': 'complete', 'cards': 'complete', 'metadata': 'partial',
                                    'reference': 'Synthetic explicit dashboard enumeration'}, 'gaps': ['metadata_not_supplied']}


def profile(format='csv'):
    return {'schema_version': 1, 'format': format, 'encoding': 'utf-8', 'subtotal_policy': 'preserve',
            'headers': ['place', 'value'], 'columns': [
                {'ordinal': 0, 'name': 'place', 'type': 'string', 'nullable': False, 'null_tokens': []},
                {'ordinal': 1, 'name': 'value', 'type': 'number', 'nullable': False, 'null_tokens': [],
                 'decimal_separator': '.', 'group_separator': None, 'percent': False}]}


class MetabaseProjection(unittest.TestCase):
    def project(self, value=None):
        return T.translate(json.dumps(value or snapshot()).encode(), 'metabase-api')

    def test_tabs_repeated_questions_parameters_and_text_remain_distinct(self):
        result = self.project()
        self.assertEqual(result['metabase_coverage']['placements'], 3)
        self.assertEqual(result['metabase_coverage']['tabs'], 2)
        self.assertEqual(sum(a['kind'] == 'visual' for a in result['assets']), 1)
        placements = [a for a in result['assets'] if a['kind'] == 'placement']
        self.assertNotEqual(placements[0]['facets']['filters'], placements[1]['facets']['filters'])
        self.assertFalse(placements[2]['source_identity']['query_visual'])
        self.assertEqual(result['upstream_payload'], snapshot())
        self.assertFalse(result['build_authority'])

    def test_native_sql_is_preserved_as_obligation_without_execution(self):
        value = snapshot()
        original = {'type': 'native', 'database': 1, 'native': {'query': 'select * from records where id = {{id}}',
                    'template-tags': {'id': {'id': 'id', 'type': 'number'}}}}
        value['cards'][0]['dataset_query'] = original
        result = self.project(value)
        self.assertEqual(len([a for a in result['assets'] if a['kind'] == 'placement']), 3)
        analysis = next(a for a in result['assets'] if a['kind'] == 'visual')['facets']['query']['value']['interpretation']
        self.assertEqual(analysis['original'], original)
        self.assertEqual(analysis['status'], 'needs_review')
        self.assertFalse(analysis['execution_performed'])

    def test_unsupported_clause_never_produces_partial_analytical_contract(self):
        query = snapshot()['cards'][0]['dataset_query']
        for change in ({'aggregation': [['sum', ['field', 7, None]], ['custom', 'inert']]},
                       {'filter': ['in-unknown-region', 1]}, {'filter': [[], 1]},
                       {'joins': []}, {'expressions': {'x': ['+', 1, 2]}},
                       {'source-table': 'card__11'}, {'source-query': {'source-table': 6}},
                       {'breakout': [['field', 8, {'temporal-unit': 'month'}]]}):
            value = copy.deepcopy(query)
            value['query'].update(change)
            analysis = V.question_analysis(value)
            self.assertEqual(analysis['status'], 'needs_review', change)
            self.assertNotIn('analytical_contract', analysis)
            self.assertEqual(analysis['original'], value)
        simple = V.question_analysis(query)
        self.assertEqual(simple['status'], 'interpreted_subset')
        self.assertEqual(simple['analytical_contract']['clauses'], query['query'])
        self.assertFalse(simple['target_compiled'])

    def test_multistage_never_reduces_to_final_stage(self):
        query = {'database': 1, 'lib/type': 'mbql/query', 'stages': [
            {'source-table': 5, 'filters': [['>', {}, 7, 0]]}, {'aggregation': [['count', {}]]}]}
        result = V.question_analysis(query)
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(len(result['original']['stages']), 2)
        self.assertNotIn('analytical_contract', result)

    def test_saved_question_dependencies_survive_native_and_modern_queries(self):
        for query in ({'type': 'native', 'database': 1, 'native': {'query': 'select * from {{#11}}',
                        'template-tags': {'#11': {'type': 'card', 'card-id': 11}}}},
                      {'database': 1, 'lib/type': 'mbql/query', 'stages': [{'source-card': 11}]}):
            value = snapshot()
            value['cards'][0]['dataset_query'] = query
            dependency = copy.deepcopy(snapshot()['cards'][0])
            dependency['id'] = 11
            value['cards'].append(dependency)
            result = self.project(value)
            references = [d for d in result['dependencies'] if d.get('kind') == 'card' and d.get('id') == 11]
            self.assertTrue(references)
            self.assertTrue(all(d['status'] == 'declared' for d in references))
            value['cards'].pop()
            value['coverage']['cards'] = 'partial'
            result = self.project(value)
            self.assertTrue(any(d.get('id') == 11 and d.get('status') == 'unresolved' for d in result['dependencies']))

    def test_missing_card_series_and_action_never_remove_placements(self):
        value = snapshot()
        value['dashboard']['dashcards'][0]['series'] = [{'id': 11}]
        value['dashboard']['dashcards'][1]['card_id'] = 12
        value['dashboard']['dashcards'][2]['action_id'] = 9
        value['coverage']['cards'] = 'partial'
        result = self.project(value)
        self.assertEqual(result['metabase_coverage']['placements'], 3)
        codes = {g['code'] for g in result['gaps']}
        self.assertIn('metabase.missing_card_definition', codes)
        self.assertIn('metabase.action_requires_separate_design_and_authority', codes)

    def binding(self, raw):
        return {'capture_content_hash': '1' * 64, 'definition_fingerprint': '2' * 64, 'object_key': 'card:10',
                'attachment_id': 'result-one', 'state_sha256': '3' * 64, 'attachment_sha256': V.sha(raw)}

    def test_csv_and_metabase_json_preserve_decimal_precision(self):
        raw = b'place,value\nWest,1.100000000000000001\n'
        result = V.normalize_results(raw, profile(), self.binding(raw))
        self.assertEqual(result['rows'][0]['value'], '1.100000000000000001')
        raw = b'{"status":"completed","data":{"cols":[{"name":"place"},{"name":"value"}],"rows":[["West",1.100000000000000001]]}}'
        result = V.normalize_results(raw, profile('metabase-json'), self.binding(raw))
        self.assertEqual(result['rows'][0]['value'], '1.100000000000000001')
        self.assertEqual(result['raw_sha256'], V.sha(raw))
        self.assertEqual(result['completeness'], 'not_established')
        self.assertEqual(result['kind'], 'metabase_normalized_results')

    def test_result_errors_duplicate_headers_and_wrong_raw_pin_reject(self):
        for raw in (b'{"status":"failed","error":"synthetic"}',
                    b'{"status":"completed","data":{"cols":[{"name":"place"},{"name":"place"}],"rows":[]}}',
                    b'{"status":"completed","data":{"cols":[{"name":"place"},{"name":"value"}],"rows":[["West"]]}}'):
            with self.assertRaises(ValueError):
                V.normalize_results(raw, profile('metabase-json'), self.binding(raw))
        raw = b'place,value\nWest,1\n'
        binding = self.binding(raw)
        binding['attachment_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'normalization_binding'):
            V.normalize_results(raw, profile(), binding)


if __name__ == '__main__':
    unittest.main()
