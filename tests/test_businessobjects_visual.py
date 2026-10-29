"""Original neutral synthetic Web Intelligence evidence, never a live source claim."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-translator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('test_bo_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


V, T = load('businessobjects_visual'), load('translate_artifact')
HELPERS = {'base': T.base, 'add_asset': T.add_asset, 'gap': T.gap, 'facet': T.facet}


def result_contract():
    return {'data_mode': 'full_data', 'row_limit': None, 'row_limit_stage': 'none',
            'aggregation_stage': 'native_report', 'reference': 'Synthetic explicit report result contract'}


def response(key, kind, body, route, report=None, provider=None):
    raw = body.encode() if type(body) is str else V.encoded(body)
    return {'key': key, 'kind': kind, 'report_id': report, 'provider_id': provider,
        'format': 'xml' if type(body) is str else 'json', 'encoding': 'utf-8', 'content': raw.decode(),
        'sha256': V.sha(raw), 'bytes': len(raw), 'reference': 'Synthetic original response, not tenant observation',
        'provenance': {'mode': 'supplied_rest', 'method': 'GET', 'resource_path': route, 'status': 200}}


def repin(row, body):
    raw = body.encode() if type(body) is str else V.encoded(body)
    row.update(content=raw.decode(), sha256=V.sha(raw), bytes=len(raw))


def snapshot_fixture():
    responses = [response('document', 'document', {'document': {'id': 100, 'name': 'Orchard operations',
        'cuid': 'fixture-document-cuid'}}, '/documents/100'),
        response('report', 'report', {'report': {'id': 1, 'name': 'Yield overview', 'reference': '1.RS',
            'pageSettings': {'records': {'@vertical': 100, '@horizontal': 20}}}}, '/documents/100/reports/1', '1'),
        response('table', 'element', {'element': {'@type': 'VTable', 'id': 7, 'reference': '1.7',
            'position': {'@x': 20, '@y': 40}, 'content': {'axes': {'axis': {'@role': 'Column', 'id': 1,
                'expressions': {'formula': {'@dataType': 'Numeric', '@dataObjectId': 'DP0.DO7', '$': '=[Yield]'}}}},
                'futureSetting': {'inert': 'Source-only configuration'}}}},
            '/documents/100/reports/1/elements/7', '1'),
        response('providers', 'dataproviders', '<dataproviders><dataprovider><id>DP0</id><name>Yield query</name>'
            '<dataSourceId>600</dataSourceId><dataSourceType>unx</dataSourceType><rowCount>3</rowCount>'
            '<isPartial>false</isPartial></dataprovider></dataproviders>', '/documents/100/dataproviders'),
        response('variable', 'variable', '<variable dataType="Numeric" qualification="Measure"><id>L9</id>'
            '<name>Plot share</name><definition>=Sum([Yield]) In ([Plot]) / Sum([Yield]) ForAll ([Plot])</definition>'
            '</variable>', '/documents/100/variables/L9'),
        response('spec', 'specification', '<REPORT rId="1" name="Yield overview"><PAGE_BODY bId="2">'
            '<VTABLE bId="21" name="Detailed yield" x="100" y="100"><ROWGROUP type="body"><TR>'
            '<TDCELL bId="213"><CONTENT>=[Plot]</CONTENT></TDCELL>'
            '<TDCELL bId="214"><CONTENT>=[Yield]</CONTENT></TDCELL></TR></ROWGROUP></VTABLE>'
            '</PAGE_BODY></REPORT>', '/documents/100/reports/1/specification', '1'),
        response('map', 'map', '<map><node reference="1.G.0" name="North" final="true"/>'
            '<node reference="1.G.1" name="South" final="true"/></map>', '/documents/100/reports/1/map', '1')]
    def row(key, kind, parent, native, rkey, locator, report=None, **configuration):
        return {'key': key, 'kind': kind, 'parent_key': parent, 'native_id': native, 'report_id': report,
            'disposition': 'include', 'reference': 'Synthetic independently supplied scope',
            'configuration': configuration, 'source_mapping': {'response_key': rkey, 'locator': locator} if rkey else None}
    rows = [row('root', 'document', None, '100', 'document', '/document'),
        row('report-one', 'report', 'root', '1', 'report', '/report', '1'),
        row('yield-table', 'visual', 'report-one', '7', 'table', '/element', '1', result_contract=result_contract()),
        row('provider', 'provider', 'root', 'DP0', 'providers', '/0'),
        row('variable', 'variable', 'root', 'L9', 'variable', '/'),
        row('spec-table', 'placement', 'report-one', '21', 'spec', '/0/0', '1'),
        row('north-instance', 'placement', 'report-one', None, 'map', '/0', '1'),
        row('south-instance', 'placement', 'report-one', None, 'map', '/1', '1'),
        row('expected-control', 'input_control', 'report-one', None, None, None, '1')]
    return {'schema_version': V.SCHEMA,
        'identity': {'source_origin': 'https://source.example.invalid:6405', 'product_version': '4.3', 'service_pack': 5,
            'principal_ref': 'fixture-reader', 'document_id': '100', 'cuid': 'fixture-document-cuid', 'report_engine': 'webi',
            'reference': 'Synthetic source identity, not authentication'}, 'responses': responses,
        'inventory': {'reference': 'Synthetic independent selected scope', 'completeness': 'selected_scope_declared', 'items': rows},
        'gaps': ['No live tenant, visual observation, access grant or execution evidence']}


def projected(value):
    return V.translate(value, V.encoded(value), HELPERS)


def link_fixture(as_json=False, collection=False):
    """Native Raylight link shape; original synthetic IDs/captions only."""
    value = snapshot_fixture()
    link = {'@dataType': 'String', '@qualification': 'Dimension', 'id': 'L6', 'name': 'Harvest season',
            'linkedExpressions': {'linkedExpression': [{'@id': 'DP0.DOseason'}, {'@id': 'DP1.DOseason'}]}}
    if as_json:
        body = {'links': {'link': [link]}} if collection else {'link': link}
        locator = '/links/link/0' if collection else '/link'
    else:
        body = '<link dataType="String" qualification="Dimension"><id>L6</id><name>Harvest season</name>' \
            '<linkedExpressions><linkedExpression id="DP0.DOseason"/><linkedExpression id="DP1.DOseason"/>' \
            '</linkedExpressions></link>'
        if collection: body = '<links>' + body + '</links>'
        locator = '/0' if collection else '/'
    value['responses'].append(response('links', 'merged_dimensions', body, '/documents/100/links' + ('' if collection else '/L6')))
    value['inventory']['items'].append({'key': 'season-link', 'kind': 'merged_dimension', 'parent_key': 'root',
        'native_id': 'L6', 'report_id': None, 'disposition': 'include', 'reference': 'Synthetic independent link enumeration',
        'configuration': {}, 'source_mapping': {'response_key': 'links', 'locator': locator}})
    return value


class BusinessObjectsVisualTests(unittest.TestCase):
    def test_native_objects_original_bytes_and_literal_expected_scope(self):
        value = snapshot_fixture(); result = projected(value)
        self.assertEqual(result['upstream_payload'], value)
        self.assertEqual(result['source']['definition_fingerprint'], V.sha(value))
        declared = {a['source_identity']['object_key']: a for a in result['assets'] if a['source_identity']['object_key']}
        self.assertEqual(set(declared), {'root', 'report-one', 'yield-table', 'provider', 'variable', 'spec-table',
                                       'north-instance', 'south-instance', 'expected-control'})
        self.assertEqual(declared['yield-table']['source_identity']['provider_ids'], ['DP0'])
        self.assertTrue(declared['yield-table']['source_identity']['query_visual'])
        self.assertEqual(declared['yield-table']['source_identity']['report_id'], '1')
        self.assertFalse(result['source_execution']); self.assertEqual(result['network_calls'], 0)
        self.assertFalse(result['migration_context']['target_write_authority'])
        self.assertEqual(result['export_completeness'], 'not_established')

    def test_report_spec_embedded_cells_not_lost_to_declared_inventory(self):
        result = projected(snapshot_fixture())
        native = [a['source_identity'] for a in result['assets'] if a['source_identity']['object_key'] is None]
        cells = [a for a in native if a['native_id'] in ('213', '214')]
        self.assertEqual(len(cells), 2)
        self.assertTrue(all(a['native_kind'] == 'visual' and a['declared_disposition'] == 'manual_review' for a in cells))
        self.assertTrue(all(not a['query_visual'] for a in cells))
        self.assertGreater(result['businessobjects_coverage']['additional_native_obligations'], 2)

    def test_repeated_instance_references_have_distinct_identity(self):
        result = projected(snapshot_fixture())
        rows = [a for a in result['assets'] if a['source_identity']['object_key'] in ('north-instance', 'south-instance')]
        self.assertEqual(len(rows), 2); self.assertNotEqual(rows[0]['asset_key'], rows[1]['asset_key'])
        self.assertEqual({a['source_payload']['native_node']['attributes']['reference'] for a in rows}, {'1.G.0', '1.G.1'})
        self.assertFalse(any(a['source_identity']['query_visual'] for a in rows))

    def test_context_formula_unknown_properties_and_missing_control_retained(self):
        result = projected(snapshot_fixture()); codes = {g['code'] for g in result['gaps']}
        self.assertIn('ForAll ([Plot])', result['upstream_payload']['responses'][4]['content'])
        self.assertIn('businessobjects.variable_semantics_require_review', codes)
        self.assertIn('businessobjects.expected_object_without_native_evidence', codes)
        self.assertIn('businessobjects.unqualified_source_results', codes)
        self.assertTrue(any(a['source_identity']['native_kind'] == 'unknown' for a in result['assets']))
        missing = next(a for a in result['assets'] if a['source_identity']['object_key'] == 'expected-control')
        self.assertTrue(missing['source_identity']['requires_source_review'])
        self.assertEqual(missing['source_identity']['declared_disposition'], 'include')

    def test_native_queryspec_preserves_context_and_provider(self):
        value = snapshot_fixture()
        value['responses'].append(response('query', 'query', '<queryspec:QuerySpec xmlns:queryspec="http://com.sap.sl.queryspec" '
            'dataProviderId="DP0"><queryParameters><maxRowsRetrievedProperty value="90000"/></queryParameters>'
            '</queryspec:QuerySpec>', '/documents/100/dataproviders/DP0/specification', provider='DP0'))
        row = copy.deepcopy(value['inventory']['items'][3]); row.update(key='query', kind='query',
            source_mapping={'response_key': 'query', 'locator': '/'})
        value['inventory']['items'].append(row)
        scope = V.scope_item(value, 'query')
        self.assertTrue(scope['query_visual']); self.assertEqual(scope['provider_ids'], ['DP0'])
        self.assertIn('90000', projected(value)['upstream_payload']['responses'][-1]['content'])

    def test_tampered_original_and_identity_and_route_fail_closed(self):
        for mutation in ('bytes', 'hash', 'id', 'document_route', 'report_route', 'provider'):
            value = snapshot_fixture()
            if mutation == 'bytes': value['responses'][0]['bytes'] += 1
            elif mutation == 'hash': value['responses'][0]['sha256'] = '0' * 64
            elif mutation == 'id': value['inventory']['items'][2]['native_id'] = '88'
            elif mutation == 'document_route': value['responses'][2]['provenance']['resource_path'] = '/documents/999/reports/1/elements/7'
            elif mutation == 'report_route': value['responses'][2]['provenance']['resource_path'] = '/documents/100/reports/2/elements/7'
            elif mutation == 'provider': value['responses'][3]['provider_id'] = 'DP9'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_wrapper_cannot_promote_modeled_unknown_or_namespace_spoof(self):
        value = snapshot_fixture(); value['responses'][2]['provenance']['mode'] = 'supplied_modeled'
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])
        value['responses'][2]['provenance']['mode'] = 'unknown'
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])
        value = snapshot_fixture(); value['responses'][2]['format'] = 'xml'
        repin(value['responses'][2], '<element xmlns="urn:unqualified" type="VTable"><id>7</id></element>')
        value['inventory']['items'][2].update(kind='unknown', source_mapping={'response_key': 'table', 'locator': '/'})
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])

    def test_version_and_engine_limits_are_obligations_not_whole_source_rejection(self):
        for engine, version, sp, expected in [('crystal_classic', '4.3', 4, 'crystal_classic_requires_4_3_SP05_or_later'),
                ('crystal_enterprise', '2025', None, 'crystal_enterprise_not_supported_2025'),
                ('webi', 'unknown', None, 'unqualified_product_version')]:
            value = snapshot_fixture(); value['identity'].update(report_engine=engine, product_version=version, service_pack=sp)
            result = projected(value)
            self.assertIn('businessobjects.' + expected, {g['code'] for g in result['gaps']})
            self.assertFalse(any(a['source_identity']['query_visual'] for a in result['assets']))
        value = snapshot_fixture(); value['identity'].update(product_version='2025', service_pack=None)
        repin(value['responses'][3], value['responses'][3]['content'].replace('unx', 'unv'))
        self.assertFalse(V.scope_item(value, 'provider')['query_visual'])
        self.assertIn('businessobjects.UNV_unavailable_2025', {g['code'] for g in projected(value)['gaps']})

    def test_declared_and_native_report_restrictions_inherit_even_when_reparented(self):
        value = snapshot_fixture(); value['inventory']['items'][1]['configuration']['private'] = True
        value['inventory']['items'][2]['parent_key'] = 'root'
        scope = V.scope_item(value, 'yield-table'); self.assertTrue(scope['restricted']); self.assertFalse(scope['query_visual'])
        omitted = [a for a in projected(value)['assets'] if a['source_identity']['native_id'] == '213']
        self.assertTrue(omitted[0]['source_identity']['restricted_private_scope'])
        value['inventory']['items'][1]['configuration']['selection_reference'] = 'Explicit synthetic selected private scope'
        self.assertTrue(V.scope_item(value, 'yield-table')['query_visual'])
        value['inventory']['items'][1]['configuration']['access'] = 'denied'
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])

    def test_selected_unknown_unmapped_and_manual_never_qualify_numeric_obligation(self):
        for disposition in ('manual_review', 'unsupported', 'unavailable', 'out_of_scope'):
            value = snapshot_fixture(); value['inventory']['items'][2]['disposition'] = disposition
            self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])
        value = snapshot_fixture(); value['inventory']['items'][2]['source_mapping'] = None
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])

    def test_inventory_missing_cycle_duplicate_locator_and_kind_contradiction_reject(self):
        for mutation in ('missing', 'cycle', 'duplicate', 'kind', 'empty'):
            value = snapshot_fixture()
            if mutation == 'missing': value['inventory']['items'][2]['parent_key'] = 'absent'
            elif mutation == 'cycle': value['inventory']['items'][1]['parent_key'] = 'yield-table'
            elif mutation == 'duplicate':
                row = copy.deepcopy(value['inventory']['items'][2]); row['key'] = 'copy'; value['inventory']['items'].append(row)
            elif mutation == 'kind': value['inventory']['items'][2]['kind'] = 'variable'
            else: value['inventory']['items'] = []
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_xml_entities_external_declarations_invalid_encoding_and_limits_reject(self):
        cases = [b'<!DOCTYPE report [<!ENTITY bomb "x">]><report/>', b'<!DOCTYPE report SYSTEM "https://invalid/x"><report/>',
            b'<report>&unknown;</report>', '<report/>'.encode('utf-16'), b'<?xml version="1.0" encoding="ISO-8859-1"?><report/>',
            ('<x>' * 65 + '</x>' * 65).encode(), ('<root>' + '<x/>' * 20001 + '</root>').encode(),
            b' ' * (V.MAX_RESPONSE_BYTES + 1)]
        for raw in cases:
            with self.subTest(prefix=raw[:20]), self.assertRaises(ValueError): V.inspect_xml(raw)

    def test_credentials_rejected_without_secret_value_in_error(self):
        for body in [{'document': {'id': 100, 'X-SAP-LogonToken': 'synthetic-secret'}},
                     '<document><id>100</id><logonToken>synthetic-secret</logonToken></document>',
                     {'attrs': {'attr': [{'@name': 'logonToken', '@type': 'string', '$': 'synthetic-secret'}]}},
                     '<attrs><attr name="logonToken" type="string">synthetic-secret</attr></attrs>',
                     {'serializedSession': 'synthetic-secret'}]:
            value = snapshot_fixture(); repin(value['responses'][0], body)
            value['responses'][0]['format'] = 'xml' if type(body) is str else 'json'
            with self.assertRaises(ValueError) as caught: V.validate_snapshot(value)
            self.assertNotIn('synthetic-secret', str(caught.exception))

    def test_external_links_and_scripts_stay_inert(self):
        value = snapshot_fixture(); repin(value['responses'][5], value['responses'][5]['content'].replace('</REPORT>',
            '<Custom href="https://invalid.example/never-fetch"><script>Do not execute</script></Custom></REPORT>'))
        result = projected(value)
        self.assertFalse(result['source_execution']); self.assertEqual(result['network_calls'], 0)
        self.assertIn('businessobjects.external_reference_not_followed', {g['code'] for g in result['gaps']})

    def test_raw_envelope_mismatch_and_malformed_json_reject(self):
        value = snapshot_fixture()
        with self.assertRaises(ValueError): V.translate(value, V.encoded({**value, 'gaps': []}), HELPERS)
        repin(value['responses'][0], '{"document":{"id":100,"id":101}}')
        with self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_https_origin_port_and_no_authority_flags(self):
        value = snapshot_fixture(); value['identity']['source_origin'] = 'https://[2001:db8::1]:6405'
        V.validate_snapshot(value)
        for origin in ('http://source.example.invalid', 'https://user:secret@example.invalid', 'https://example.invalid/path'):
            value['identity']['source_origin'] = origin
            with self.assertRaises(ValueError): V.validate_snapshot(value)
        value = snapshot_fixture(); value['grant'] = True
        with self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_element_endpoint_and_cuid_binding_cannot_drift(self):
        value = snapshot_fixture(); value['responses'][2]['provenance']['resource_path'] = '/documents/100/reports/1/elements/99'
        with self.assertRaisesRegex(ValueError, 'native_element_route_mismatch'): V.validate_snapshot(value)
        value = snapshot_fixture(); value['identity']['cuid'] = 'different-cuid'
        with self.assertRaisesRegex(ValueError, 'native_cuid_mismatch'): V.validate_snapshot(value)

    def test_known_child_inside_unknown_native_container_is_not_qualified(self):
        value = snapshot_fixture()
        body = {'unknownRoot': {'element': {'@type': 'VTable', 'id': 7, 'dataProviderId': 'DP0'}}}
        repin(value['responses'][2], body)
        value['inventory']['items'][2]['source_mapping']['locator'] = '/unknownRoot/element'
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])
        value = snapshot_fixture()
        repin(value['responses'][5], '<REPORT rId="1"><unknown><VTABLE bId="21"/></unknown></REPORT>')
        self.assertFalse(V.scope_item(value, 'spec-table')['query_visual'])

    def test_native_negative_access_cannot_be_relabelled_by_inventory(self):
        value = snapshot_fixture(); body = V.F.decode(value['responses'][1]['content'].encode())
        body['report']['isPrivate'] = True; repin(value['responses'][1], body)
        value['inventory']['items'][1]['configuration'] = {'private': False, 'access': 'allowed',
            'selection_reference': 'Cannot authenticate source access'}
        self.assertTrue(V.scope_item(value, 'yield-table')['restricted'])
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])

    def test_unv_2025_blocks_known_visual_consumer_without_discarding_original(self):
        value = snapshot_fixture(); value['identity'].update(product_version='2025', service_pack=None)
        repin(value['responses'][3], value['responses'][3]['content'].replace('unx', 'unv'))
        self.assertFalse(V.scope_item(value, 'yield-table')['query_visual'])
        result = projected(value)
        self.assertEqual(result['upstream_payload'], value)
        self.assertIn('businessobjects.unsupported_provider_dependency', {g['code'] for g in result['gaps']})

    def test_native_link_xml_json_and_collections_preserve_provider_dependencies(self):
        for as_json in (False, True):
            for collection in (False, True):
                with self.subTest(as_json=as_json, collection=collection):
                    value = link_fixture(as_json, collection); scope = V.scope_item(value, 'season-link')
                    self.assertEqual(scope['native_kind'], 'merged_dimension')
                    self.assertTrue(scope['node']['native']['native_shape'])
                    self.assertEqual(scope['provider_ids'], ['DP0', 'DP1'])
                    self.assertFalse(scope['query_visual'])
                    result = projected(value)
                    self.assertEqual(result['upstream_payload'], value)
                    dependencies = [r['reference'] for r in result['dependencies'] if r['source_object_key'] == 'season-link']
                    self.assertEqual(dependencies, ['DP0', 'DP1'])
                    self.assertIn('businessobjects.merged_dimension_semantics_require_review', {g['code'] for g in result['gaps']})

    def test_link_route_and_inventory_id_mismatches_reject(self):
        for as_json in (False, True):
            value = link_fixture(as_json); value['responses'][-1]['provenance']['resource_path'] = '/documents/100/links/L9'
            with self.assertRaisesRegex(ValueError, 'native_link_route_mismatch'): V.validate_snapshot(value)
            value = link_fixture(as_json); value['inventory']['items'][-1]['native_id'] = 'L9'
            with self.assertRaisesRegex(ValueError, 'native_identity_contradiction'): V.validate_snapshot(value)

    def test_visual_provider_closure_missing_and_unselected_definitions_block(self):
        for missing_definition in (False, True):
            value = snapshot_fixture()
            value['inventory']['items'] = [r for r in value['inventory']['items'] if r['key'] != 'provider']
            if missing_definition: value['responses'] = [r for r in value['responses'] if r['key'] != 'providers']
            scope = V.scope_item(value, 'yield-table')
            self.assertEqual(scope['provider_ids'], ['DP0']); self.assertFalse(scope['query_visual'])
            self.assertEqual(scope['missing_provider_ids'], ['DP0'])
            result = projected(value)
            table = next(a for a in result['assets'] if a['source_identity']['object_key'] == 'yield-table')
            self.assertTrue(table['source_identity']['requires_source_review'])
            self.assertIn('businessobjects.provider_dependency_unqualified', {g['code'] for g in result['gaps']})

    def test_visual_inherits_provider_unavailable_out_of_scope_private_and_denied(self):
        for mode in ('out_of_scope', 'unavailable', 'private', 'denied'):
            value = snapshot_fixture(); provider = value['inventory']['items'][3]
            if mode in ('out_of_scope', 'unavailable'): provider['disposition'] = mode
            elif mode == 'private': provider['configuration']['private'] = True
            else: provider['configuration']['access'] = 'denied'
            with self.subTest(mode=mode):
                scope = V.scope_item(value, 'yield-table')
                self.assertFalse(scope['query_visual']); self.assertTrue(scope['restricted'])
                self.assertEqual(scope['provider_ids'], ['DP0'])
                self.assertEqual(scope['restricted_provider_ids'], ['DP0'])

    def test_two_provider_visual_needs_both_independently_included_definitions(self):
        value = snapshot_fixture(); table = value['responses'][2]
        body = V.F.decode(table['content'].encode())
        expression = body['element']['content']['axes']['axis']['expressions']
        expression['formula'] = [expression['formula'], {'@dataType': 'Numeric', '@dataObjectId': 'DP1.DO7', '$': '=[Target]'}]
        repin(table, body)
        scope = V.scope_item(value, 'yield-table')
        self.assertEqual(scope['provider_ids'], ['DP0', 'DP1']); self.assertFalse(scope['query_visual'])
        self.assertEqual(scope['missing_provider_ids'], ['DP1'])
        provider_response = response('provider-two', 'dataprovider', '<dataprovider><id>DP1</id>'
            '<name>Target query</name><dataSourceType>unx</dataSourceType></dataprovider>',
            '/documents/100/dataproviders/DP1', provider='DP1')
        value['responses'].append(provider_response)
        provider = copy.deepcopy(value['inventory']['items'][3]); provider.update(key='provider-two', native_id='DP1',
            source_mapping={'response_key': 'provider-two', 'locator': '/'})
        value['inventory']['items'].append(provider)
        self.assertTrue(V.scope_item(value, 'yield-table')['query_visual'])
        self.assertTrue(V.scope_item(value, 'provider')['query_visual'])
        self.assertTrue(V.scope_item(value, 'provider-two')['query_visual'])


if __name__ == '__main__':
    unittest.main()
