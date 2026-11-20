import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


modeler = module('modeler_test', 'skills/omni-bi-engineer/scripts/semantic_modeler.py')
translator = module('translator_for_semantic_test', 'skills/omni-artifact-translator/scripts/translate_artifact.py')


def fixture():
    guide = (ROOT / 'skills/omni-bi-engineer/references/semantic-modeler.md').read_text()
    return json.loads(guide.split('```json\n', 1)[1].split('\n```', 1)[0])


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def topic(raw):
    # The advertised YAML 1.2 subset has block keys and independent JSON flow
    # values. Decode the emitted data independently of the update code.
    obj = {}
    for line in raw.splitlines():
        if not line or line.startswith('#'):
            continue
        if line[0] != ' ':
            key, value = line.split(':', 1)
            obj[key] = value
        else:
            obj[key] += '\n' + line
    return {key: json.loads(value) for key, value in obj.items()}


def existing(spec, old):
    spec['baseline']['topic_names'].append('order_review')
    spec['baseline']['topic_files'] = {'order_review.topic': old}
    spec['update'] = {'expected_sha256': digest(old), 'review_ref': 'scoped-change-review'}


class SemanticModelerTests(unittest.TestCase):
    def assert_blocked(self, spec, code):
        result = modeler.build_candidate(spec)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertEqual(result['files'], {})
        self.assertEqual(result['changes'], [])
        self.assertIsNone(result['candidate_sha256'])
        self.assertIn(code, [item['code'] for item in result['gaps'] if item['blocking']])
        return result

    def test_real_shape_local_changes_do_not_edit_shared_views_or_global_relationships(self):
        spec = fixture()
        before = copy.deepcopy(spec)
        result = modeler.build_candidate(spec)
        self.assertEqual(result['status'], 'candidate')
        self.assertEqual(result['topic_name'], 'order_review')
        self.assertEqual(result['base_view'], 'orders')
        self.assertEqual(list(result['files']), ['order_review.topic'])
        raw = result['files']['order_review.topic']
        obj = topic(raw)
        self.assertEqual(obj['base_view'], 'orders')
        self.assertEqual(obj['views']['orders']['measures']['net_sales']['sql'], '${orders.net_amount}')
        self.assertEqual(obj['relationships'][0]['on_sql'], '${orders.account_id} = ${accounts.id}')
        self.assertEqual(obj['relationships'][0]['relationship_type'], 'many_to_one')
        self.assertEqual(obj['joins'], {'accounts': {}})
        self.assertEqual(obj['access_filters'], [{'field': 'orders.tenant_id', 'user_attribute': 'tenant'}])
        self.assertEqual(obj['required_access_grants'], ['analyst'])
        change, = result['changes']
        self.assertEqual((change['expected_sha256'], change['sha256']), (None, digest(raw)))
        self.assertEqual(result['rollback'][0], {'path': 'order_review.topic', 'operation': 'remove_created',
                         'expected_sha256': digest(raw), 'restore_text': None})
        self.assertEqual(spec, before)
        self.assertEqual(result, modeler.build_candidate(json.loads(json.dumps(spec))))
        self.assertFalse(result['native_verified'] or result['authorizes_target_write'])
        self.assertEqual(len(result['gaps']), 3)

    def test_candidate_identity_binds_exact_evidence_branch_and_semantic_scope(self):
        a = fixture()
        b = copy.deepcopy(a)
        b['baseline']['branch_id'] = 'another-development-branch'
        c = copy.deepcopy(a)
        c['measures'][0]['review_ref'] = 'updated-definition-reference'
        values = [modeler.build_candidate(x) for x in (a, b, c)]
        self.assertEqual(len({r['candidate_sha256'] for r in values}), 3)
        for value in values:
            material = {k: value[k] for k in ('destination', 'spec_sha256', 'files', 'changes')}
            self.assertEqual(value['candidate_sha256'], digest(json.dumps(material, sort_keys=True, separators=(',', ':'))))

    def test_reuse_existing_edge_or_refuse_ambiguous_graph(self):
        spec = fixture()
        edge = dict(spec['joins'][0]); edge.pop('review_ref')
        spec['baseline']['relationships'] = [edge]
        obj = topic(modeler.build_candidate(spec)['files']['order_review.topic'])
        self.assertNotIn('relationships', obj)
        self.assertIn('accounts', obj['joins'])
        spec['baseline']['relationships'].append(dict(edge))
        self.assert_blocked(spec, 'relationship_conflicts_with_baseline')
        spec['baseline']['relationships'] = [dict(edge, join_type='inner')]
        self.assert_blocked(spec, 'relationship_conflicts_with_baseline')
        del spec['baseline']['relationships']
        self.assert_blocked(spec, 'invalid_or_oversized_list')

    def test_fixed_policy_and_measure_filters_are_distinct_from_viewer_access(self):
        spec = fixture()
        spec['measures'][0]['filters'] = {'orders.account_id': {'is': 12}}
        spec['policy']['always_where_filters'] = {'accounts.region': {'is': 'West: "HQ"'}}
        obj = topic(modeler.build_candidate(spec)['files']['order_review.topic'])
        self.assertEqual(obj['always_where_filters'], spec['policy']['always_where_filters'])
        self.assertEqual(obj['views']['orders']['measures']['net_sales']['filters'], spec['measures'][0]['filters'])
        spec['policy']['access_filters'][0]['user_attribute'] = 'unknown'
        self.assert_blocked(spec, 'access_binding_unresolved')
        spec = fixture()
        spec['policy']['always_where_filters'] = {'orders.tenant_id': {'is': '${dynamic.tenant}'}}
        self.assert_blocked(spec, 'dynamic_filter_unsupported')

    def test_no_overwrite_for_logical_identity_in_different_folder_or_extension(self):
        spec = fixture()
        spec['baseline']['topic_files'] = {'elsewhere/order_review.topic.yml': 'existing bytes'}
        self.assert_blocked(spec, 'topic_name_collision')
        spec['baseline']['topic_files'] = {}
        spec['baseline']['topic_names'] = ['order_review']
        self.assert_blocked(spec, 'topic_name_collision')
        spec['topic']['path'] = '../order_review.topic'
        self.assert_blocked(spec, 'invalid_topic_filename')

    def test_additive_update_preserves_unrelated_bytes_and_rollback(self):
        spec = fixture()
        raw = '# keep comment\r\n' + modeler.build_candidate(spec)['files']['order_review.topic'].replace('\n', '\r\n')
        existing(spec, raw)
        self.assertEqual(modeler.build_candidate(spec)['changes'], [])
        spec['topic']['fields'].append('orders.account_id')
        result = modeler.build_candidate(spec)
        self.assertEqual(result['status'], 'candidate')
        updated = result['files']['order_review.topic']
        self.assertTrue(updated.startswith('# keep comment\r\n'))
        self.assertEqual(raw.partition('relationships:')[2], updated.partition('relationships:')[2])
        self.assertEqual(result['changes'][0]['expected_sha256'], digest(raw))
        self.assertEqual(result['rollback'][0]['restore_text'], raw)
        self.assertEqual(result['rollback'][0]['expected_sha256'], digest(updated))
        spec['update']['expected_sha256'] = '2' * 64
        self.assert_blocked(spec, 'update_baseline_hash_mismatch')

    def test_updates_never_drop_existing_properties_or_silently_replace_arbitrary_yaml(self):
        spec = fixture()
        raw = modeler.build_candidate(spec)['files']['order_review.topic']
        existing(spec, raw)
        spec['policy']['access_filters'] = []
        self.assert_blocked(spec, 'existing_topic_properties_omitted')
        spec = fixture()
        existing(spec, 'base_view: orders\nfields:\n  - orders.id\n')
        self.assert_blocked(spec, 'existing_yaml_requires_reviewed_manual_merge')
        spec = fixture()
        existing(spec, 'base_view: "orders"\n')
        self.assert_blocked(spec, 'implicit_topic_scope_requires_manual_merge')

    def test_source_adapter_preserves_native_and_unresolved_ids_and_original_semantics(self):
        payload = {'schema_version': 1, 'kind': 'omni_analyst_inventory_input', 'platform': 'looker', 'assets': [
            {'kind': 'definition', 'source_id': 'orders.net_sales', 'scope': 'model-22', 'evidence_refs': ['source-metadata'],
             'facets': {'query': {'status': 'observed', 'value': {'formula': 'SUM(net_order_amount)'}}}},
            {'kind': 'filter', 'source_id': None, 'evidence_refs': ['unknown-filter'], 'facets': {}}]}
        inventory = translator.translate(json.dumps(payload).encode(), 'normalized-inventory')
        spec = fixture()
        spec['source_inventory'] = inventory
        result = self.assert_blocked(spec, 'reviewed_source_mapping_required')
        self.assertEqual(len(result['crosswalk']), 2)
        binding = {'asset_key': inventory['assets'][0]['asset_key'], 'target': 'orders.net_sales',
                   'review_ref': 'formula-review', 'semantics': 'Sum net amounts once per order and currency.'}
        spec['source_bindings'] = [binding]
        result = modeler.build_candidate(spec)
        self.assertEqual(result['status'], 'candidate')
        mapped, other = result['crosswalk']
        self.assertEqual((mapped['source_id'], mapped['scope'], mapped['semantics']), ('orders.net_sales', 'model-22', binding['semantics']))
        self.assertEqual(mapped['source_payload_sha256'], inventory['assets'][0]['source_payload_sha256'])
        self.assertEqual(mapped['status'], 'reviewed_mapping')
        self.assertEqual(other['status'], 'unresolved')
        self.assertIsNone(other['source_id'])
        self.assertTrue(any(g['code'] == 'source_adapter_gap' for g in result['gaps']))
        spec['joins'][0]['relationship_type'] = 'many_to_many'
        held = self.assert_blocked(spec, 'unsupported_join_semantics')
        self.assertEqual([r['status'] for r in held['crosswalk']], ['unresolved', 'unresolved'])

    def test_stale_or_resealed_adapter_row_cannot_become_a_reviewed_mapping(self):
        payload = {'schema_version': 1, 'kind': 'omni_analyst_inventory_input', 'platform': 'sigma', 'assets': [
            {'kind': 'definition', 'source_id': 'calc-7', 'scope': 'workbook-1', 'evidence_refs': ['definition'],
             'facets': {'query': {'status': 'observed', 'value': {'aggregate': 'sum'}}}}]}
        original = translator.translate(json.dumps(payload).encode(), 'normalized-inventory')
        spec = fixture()
        spec['source_bindings'] = [{'asset_key': original['assets'][0]['asset_key'], 'target': 'orders.net_sales',
                                    'review_ref': 'definition', 'semantics': 'One contribution per order.'}]
        for part in ('source_payload', 'upstream_payload', 'resealed_row', 'scope', 'omitted'):
            with self.subTest(part=part):
                inv = copy.deepcopy(original)
                spec['source_inventory'] = inv
                row = inv['assets'][0]
                if part == 'upstream_payload':
                    inv['upstream_payload']['assets'][0]['facets']['query']['value']['aggregate'] = 'max'
                    code = 'adapter_upstream_payload_changed'
                elif part == 'omitted':
                    inv['assets'] = []
                    code = 'adapter_inventory_original_mismatch'
                elif part == 'scope':
                    row['source_identity']['scope'] = 'another-workbook'
                    code = 'adapter_asset_original_mismatch'
                else:
                    row['source_payload']['facets']['query']['value']['aggregate'] = 'max'
                    code = 'adapter_asset_payload_changed'
                    if part == 'resealed_row':
                        row['source_payload_sha256'] = translator.digest(row['source_payload'])
                        code = 'adapter_asset_original_mismatch'
                self.assert_blocked(spec, code)

    def test_adapter_review_obligation_with_a_named_locator_stays_unresolved(self):
        data = {'name': 'unobserved legacy calculation'}
        inv = translator.base(data, json.dumps(data).encode(), 'looker', 'supplied_looker_visual_capture')
        translator.add_asset(inv, 'definition', data, '/expected/calc', 'expected:calc', 'dashboard-3',
                             id_kind='expected_unobserved_locator')
        spec = fixture()
        spec['source_inventory'] = inv
        spec['source_bindings'] = [{'asset_key': inv['assets'][0]['asset_key'], 'target': 'orders.net_sales',
                                  'review_ref': 'a-review', 'semantics': 'An original calculation was requested.'}]
        result = self.assert_blocked(spec, 'reviewed_source_mapping_required')
        self.assertEqual(result['crosswalk'][0]['status'], 'unresolved')

    def test_looker_adapter_maps_query_evidence_but_holds_uncaptured_security(self):
        source = {'id': 'dash-1', 'title': 'Order analysis', 'dashboard_elements': [
            {'id': 'tile-3', 'title': 'Net sales', 'query': {'id': 'q-4', 'model': 'orders',
             'view': 'orders', 'fields': ['orders.net_sales']}}]}
        inv = translator.translate(json.dumps(source).encode(), 'looker-api')
        tile = next(row for row in inv['assets'] if row['source_id'] == 'tile-3')
        spec = fixture()
        spec['source_inventory'] = inv
        binding = {'asset_key': tile['asset_key'], 'target': 'orders.net_sales', 'review_ref': 'query-contract',
                   'semantics': 'A reviewed total in one currency at order grain.'}
        spec['source_bindings'] = [binding]
        candidate = modeler.build_candidate(spec)
        self.assertEqual(candidate['status'], 'candidate', candidate['gaps'])
        self.assertEqual(next(r for r in candidate['crosswalk'] if r['asset_key'] == tile['asset_key'])['status'], 'reviewed_mapping')
        binding['target'] = 'access_filter:orders.tenant_id:tenant'
        held = self.assert_blocked(spec, 'reviewed_source_mapping_required')
        self.assertTrue(all(row['status'] == 'unresolved' for row in held['crosswalk']))

    def test_native_normalization_and_semantically_different_readbacks(self):
        spec = fixture()
        expected = modeler.build_candidate(spec)['files']['order_review.topic']
        normalized = '''base_view: orders
label: Order review

joins:
  accounts: {}

fields: [ orders.id, orders.net_sales, accounts.region ]

relationships:
- join_from_view: orders
  join_to_view: accounts
  join_type: left
  on_sql: ${orders.account_id} = ${accounts.id}
  relationship_type: many_to_one

views:
  orders:
    measures:
      net_sales:
        sql: ${orders.net_amount}
        label: Net sales
        aggregate_type: sum
        description: |
          Sum of recorded net order amounts in the selected currency.

access_filters:
  - field: orders.tenant_id
    user_attribute: tenant

required_access_grants:
  - analyst
'''
        self.assertTrue(modeler.matches_readback(expected, expected))
        self.assertTrue(modeler.matches_readback(expected, normalized))
        wrapped = normalized.replace('fields: [ orders.id, orders.net_sales, accounts.region ]',
                                     'fields:\n  [\n    orders.id,\n    orders.net_sales,\n    accounts.region\n  ]').replace(
            'description: |\n          Sum of recorded net order amounts in the selected currency.',
            'description: Sum of recorded net order amounts\n          in the selected currency.')
        self.assertTrue(modeler.matches_readback(expected, wrapped))
        self.assertFalse(modeler.matches_readback(expected, wrapped.replace('orders.net_sales,', 'orders.gross_sales,')))
        self.assertTrue(modeler.matches_readback(expected, json.dumps(topic(expected))))
        mutations = [('= ${accounts.id}', '= ${accounts.other_id}'), ('many_to_one', 'one_to_one'),
                     ('aggregate_type: sum', 'aggregate_type: max'), ('${orders.net_amount}', '${orders.gross_amount}'),
                     ('field: orders.tenant_id', 'field: orders.id'), ('user_attribute: tenant', 'user_attribute: region'),
                     ('- analyst', '- admin'), ('label: Net sales', 'label: !custom Net sales'),
                     ('base_view: orders', 'base_view: orders\nbase_view: orders'),
                     ('base_view: orders', 'base_view: orders\nai_fields: [ orders.id ]')]
        for before, after in mutations:
            with self.subTest(before=before, after=after):
                self.assertFalse(modeler.matches_readback(expected, normalized.replace(before, after)))
        self.assertFalse(modeler.matches_readback(expected, ''))

    def test_readback_preserves_literal_policy_value_type(self):
        spec = fixture()
        spec['policy']['always_where_filters'] = {'orders.id': {'is': 1}}
        expected = modeler.build_candidate(spec)['files']['order_review.topic']
        document = topic(expected)
        document['always_where_filters']['orders.id']['is'] = True
        self.assertFalse(modeler.matches_readback(expected, json.dumps(document)))

    def test_invalid_fields_grants_operators_duplicates_or_external_code_never_generate(self):
        for where, key, value, code in [
            ('measure', 'field', 'orders.amount_unknown', 'measure_operand_unresolved'),
            ('measure', 'name', 'account_id', 'measure_name_collision'),
            ('measure', 'aggregate_type', 'arbitrary SQL', 'unsupported_measure_aggregation'),
            ('join', 'to_field', 'accounts.unreviewed', 'join_operand_unresolved'),
            ('join', 'relationship_type', 'one_to_many', 'unsupported_join_semantics'),
            ('policy', 'required_access_grants', ['unknown'], 'access_grant_unresolved'),
            ('policy', 'custom_sql', 'untrusted input', 'unsupported_property'),
            ('topic', 'fields', ['orders.id', 'orders.id'], 'unique_explicit_fields_required'),
            ('topic', 'fields', ['orders.*'], 'expected_view_field'),
        ]:
            with self.subTest(where=where, key=key, value=value):
                spec = fixture()
                target = {'measure': spec['measures'][0], 'join': spec['joins'][0], 'policy': spec['policy'], 'topic': spec['topic']}[where]
                target[key] = value
                self.assert_blocked(spec, code)


if __name__ == '__main__':
    unittest.main()
