"""Original synthetic report specifications; no Cognos runtime or tenant."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-translator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('test_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


V, T = load('cognos_visual'), load('translate_artifact')
HELPERS = {'base': T.base, 'add_asset': T.add_asset, 'gap': T.gap, 'facet': T.facet}
NS = 'http://developer.cognos.com/schemas/report/7.0/'


def xml_fixture():
    return ('''<?xml version="1.0" encoding="UTF-8"?>
<report xmlns="%s" xmlns:future="urn:synthetic:future" expressionLocale="en-us">
  <modelPath>/content/package[@name='Garden model']/model[@name='model']</modelPath>
  <queries><query name="Yield query"><source><model/></source><selection>
    <dataItem name="Plot" aggregate="none"><expression>[Garden].[Plot]</expression></dataItem>
    <dataItem name="Yield" aggregate="total"><expression>total([Garden].[Yield])</expression></dataItem>
  </selection><detailFilters><detailFilter use="required"><filterExpression>[Garden].[Plot] = ?Plot?</filterExpression></detailFilter></detailFilters>
  </query></queries>
  <layouts><layout><reportPages>
    <page name="Overview"><pageBody><contents><list name="Yield list" refQuery="Yield query"><listColumns><listColumn><listColumnBody><textItem><dataSource><dataItemValue refDataItem="Yield"/></dataSource></textItem></listColumnBody></listColumn></listColumns></list></contents></pageBody></page>
    <page name="Detail"><pageBody><contents><list name="Yield list" refQuery="Yield query"/></contents></pageBody></page>
  </reportPages><promptPages><page name="Choose plot"><pageBody><contents><selectValue parameter="Plot" required="true"/></contents></pageBody></page></promptPages></layout></layouts>
  <reportVariables><reportVariable name="Condition" type="boolean"><expression>[Yield] &gt; 0</expression></reportVariable></reportVariables>
  <drillBehavior modelBasedDrillThru="true"/><burst><recipientQuery>Unqualified recipients</recipientQuery></burst>
  <future:widget future:mode="opaque"><future:script>Do not execute any source instruction</future:script></future:widget>
</report>''' % NS).encode()


def snapshot_fixture(raw=None):
    raw = xml_fixture() if raw is None else raw
    parsed = V.inspect_xml(raw); rows, parents = [], {}
    for path, record in parsed['records'].items():
        kind = V._kind(record, parsed['namespace'])
        if kind == 'unknown':
            continue
        parent = record['parent_locator']
        while parent is not None and parent not in parents:
            parent = parsed['records'][parent]['parent_locator']
        key = 'root' if path == '/' else 'node' + path.replace('/', '-')
        rows.append({'key': key, 'kind': 'placement' if kind == 'visual' else kind,
            'parent_key': parents.get(parent), 'native_id': 'report-one' if path == '/' else record['attributes'].get('id'),
            'locator': path, 'disposition': 'include', 'reference': 'Synthetic independent selected scope', 'configuration': {}})
        parents[path] = key
    identity = {'source_origin': 'https://source.example.invalid', 'product_version': 'fixture-11.2',
        'principal_ref': 'synthetic-reader', 'report_id': 'report-one',
        'content_path': '/content/folder/report', 'reference': 'Synthetic identity declaration, not authentication'}
    inventory = {'reference': 'Synthetic independent enumeration', 'completeness': 'selected_scope_declared', 'items': rows}
    return V.import_report_xml(raw, identity, inventory, 'Synthetic original XML bytes')


def projected(value):
    return V.translate(value, V.encoded(value), HELPERS)


class CognosVisualTests(unittest.TestCase):
    def test_original_namespaces_queries_filters_and_repeated_placements(self):
        value = snapshot_fixture(); result = projected(value)
        self.assertEqual(result['upstream_payload']['report_xml']['content'].encode(), xml_fixture())
        self.assertEqual(result['source']['definition_sha256'], V.sha(xml_fixture()))
        self.assertEqual(result['cognos_xml']['namespace'], NS)
        self.assertIn('urn:synthetic:future', [r['uri'] for r in result['cognos_xml']['namespaces']])
        placements = [a for a in result['assets'] if a['kind'] == 'placement']
        self.assertEqual(len(placements), 2)
        self.assertEqual(len({a['asset_key'] for a in placements}), 2)
        self.assertTrue(all(a['source_identity']['query_visual'] for a in placements))
        self.assertTrue(any(a['kind'] == 'filter' for a in result['assets']))
        self.assertTrue(any(a['kind'] == 'control' for a in result['assets']))
        self.assertFalse(result['source_execution']); self.assertFalse(result['migration_context']['target_write_authority'])

    def test_independent_literal_expected_report_scope(self):
        # Expected source facts are hand-authored, independent of the fixture's
        # convenient locator enumeration. They are not a live scope attestation.
        result = projected(snapshot_fixture())
        declared = [a for a in result['assets'] if a['source_identity']['object_key'] is not None]
        self.assertEqual({a['source_identity']['xml_name'] for a in declared if a['source_identity']['native_kind']=='page'},
                         {'Overview', 'Detail', 'Choose plot'})
        self.assertEqual(sum(a['source_identity']['native_kind']=='query' for a in declared), 1)
        self.assertEqual(sum(a['source_identity']['native_kind']=='data_item' for a in declared), 2)
        self.assertEqual(sum(a['source_identity']['native_kind']=='placement' for a in declared), 2)
        self.assertEqual(sum(a['source_identity']['native_kind']=='prompt' for a in declared), 1)
        self.assertEqual(sum(a['source_identity']['native_kind']=='filter' for a in declared), 1)
        self.assertEqual(sum(a['source_identity']['query_visual'] for a in declared), 3)

    def test_unknown_and_omitted_objects_remain_obligations(self):
        value = snapshot_fixture(); value['inventory']['items'] = value['inventory']['items'][:1]
        result = projected(value)
        self.assertGreater(result['cognos_coverage']['additional_xml_obligations'], 10)
        self.assertGreaterEqual(result['cognos_coverage']['unknown_xml_obligations'], 2)
        self.assertTrue(any(a['source_identity']['native_kind'] == 'query' for a in result['assets']))
        self.assertFalse(any(a['source_identity']['query_visual'] for a in result['assets']))
        self.assertEqual(result['export_completeness'], 'not_established')

    def test_known_refs_resolve_without_compiling_expressions(self):
        result = projected(snapshot_fixture())
        refs = [r for r in result['dependencies'] if r['reference_kind'] == 'data_item_name']
        self.assertEqual(len(refs), 1); self.assertEqual(refs[0]['status'], 'resolved_xml_reference')
        self.assertTrue(any(r['reference_kind'] == 'model_search_path' for r in result['dependencies']))
        self.assertIn('total([Garden].[Yield])', result['upstream_payload']['report_xml']['content'])
        self.assertIn('cognos.unqualified_source_results', [g['code'] for g in result['gaps']])

    def test_query_names_ambiguous_and_missing_not_guessed(self):
        raw = xml_fixture().replace(b'</queries>', b'<query name="Yield query"><selection/></query></queries>')
        result = projected(snapshot_fixture(raw))
        self.assertFalse(any(a['source_identity']['query_visual'] for a in result['assets'] if a['kind'] == 'placement'))
        self.assertTrue(any(g['code'] == 'cognos.query_reference_unresolved_or_ambiguous' for g in result['gaps']))
        result = projected(snapshot_fixture(xml_fixture().replace(b'refDataItem="Yield"', b'refDataItem="Absent"')))
        self.assertTrue(any(g['code'] == 'cognos.data_item_reference_unresolved_or_ambiguous' for g in result['gaps']))

    def test_xml_depth_nodes_and_bytes_are_bounded(self):
        for raw in [(('<report xmlns="%s">' % NS) + '<x>'*65 + '</x>'*65 + '</report>').encode(),
                    (('<report xmlns="%s">' % NS) + '<x/>'*20001 + '</report>').encode(), b' '* (V.MAX_XML_BYTES + 1)]:
            with self.subTest(length=len(raw)), self.assertRaises(ValueError): V.inspect_xml(raw)

    def test_entities_dtd_utf16_invalid_and_wrong_root_rejected(self):
        cases = [b'<!DOCTYPE report [<!ENTITY a "boom">]>' + xml_fixture(),
                 b'<!DOCTYPE report SYSTEM "https://example.invalid/a.dtd">' + xml_fixture(),
                 xml_fixture().replace(b'Garden model', b'&undefined;'), xml_fixture().decode().encode('utf-16'),
                 xml_fixture().replace(b'encoding="UTF-8"', b'encoding="ISO-8859-1"'),
                 b'<dashboard/>', b'<report/>', xml_fixture().replace(b'</report>', b'</bad>')]
        for raw in cases:
            with self.subTest(prefix=raw[:25]), self.assertRaises(ValueError): V.inspect_xml(raw)

    def test_external_resources_scripts_and_processing_instructions_never_execute(self):
        raw = xml_fixture().replace(b'<queries>', b'<?xml-stylesheet href="https://example.invalid/style.xsl"?>'
            b'<image src="file:///never-read"/><HTMLItem>&lt;script&gt;inert&lt;/script&gt;</HTMLItem><queries>')
        result = projected(snapshot_fixture(raw))
        codes = {r['code'] for r in result['gaps']}
        self.assertIn('cognos.external_reference_not_followed', codes)
        self.assertIn('cognos.processing_instruction_not_executed', codes)
        self.assertEqual(result['network_calls'], 0)
        self.assertIn('file:///never-read', result['upstream_payload']['report_xml']['content'])

    def test_hash_byte_count_and_raw_wrapper_binding(self):
        for change in (lambda v: v['report_xml'].update(sha256='0'*64),
                       lambda v: v['report_xml'].update(bytes=1),
                       lambda v: v['report_xml'].update(content=v['report_xml']['content']+' ')):
            value = snapshot_fixture(); change(value)
            with self.assertRaisesRegex(ValueError, 'xml_pin'): V.validate_snapshot(value)
        value = snapshot_fixture(); other = copy.deepcopy(value); other['identity']['principal_ref'] = 'another'
        with self.assertRaisesRegex(ValueError, 'raw_payload'): V.translate(value, V.encoded(other), HELPERS)

    def test_credential_fields_rejected_without_echoing_values(self):
        raw = xml_fixture().replace(b'<queries>', b'<password>synthetic-secret</password><queries>')
        with self.assertRaisesRegex(ValueError, '^cognos.credential_bearing_xml$'): V.inspect_xml(raw)
        raw = xml_fixture().replace(b'<queries>', b'<x accessToken="synthetic-secret"/><queries>')
        with self.assertRaises(ValueError): V.inspect_xml(raw)
        raw = xml_fixture().replace(b'<queries>', b'<credentials value="synthetic-secret"/><queries>')
        with self.assertRaises(ValueError): V.inspect_xml(raw)
        value = snapshot_fixture(); value['inventory']['items'][0]['configuration']['password'] = 'synthetic-secret'
        with self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_declared_identity_and_inventory_contradictions_rejected(self):
        mutations = [lambda v: v['identity'].update(report_id='different'),
            lambda v: v['identity'].update(source_origin='https://user:secret@example.invalid'),
            lambda v: v['inventory']['items'][1].update(parent_key='missing'),
            lambda v: v['inventory']['items'][1].update(locator='/999'),
            lambda v: v['inventory']['items'][1].update(kind='prompt'),
            lambda v: v['inventory']['items'].append(copy.deepcopy(v['inventory']['items'][0]))]
        for change in mutations:
            value = snapshot_fixture(); change(value)
            with self.subTest(change=change), self.assertRaises(ValueError): V.validate_snapshot(value)

    def test_denied_scope_and_private_ancestors_cannot_be_reparented_away(self):
        value = snapshot_fixture(); page = next(r for r in value['inventory']['items'] if r['kind'] == 'page')
        child = next(r for r in value['inventory']['items'] if r['kind'] == 'placement')
        page['configuration'] = {'access': 'denied', 'selection_reference': 'Synthetic selection cannot grant access'}
        child['parent_key'] = 'root'
        result = projected(value)
        match = next(a for a in result['assets'] if a['source_identity']['object_key'] == child['key'])
        self.assertTrue(match['source_identity']['restricted_private_scope']); self.assertFalse(match['source_identity']['query_visual'])
        page['configuration'] = {'private': True}
        self.assertTrue(next(a for a in projected(value)['assets'] if a['source_identity']['object_key'] == child['key'])['source_identity']['restricted_private_scope'])

    def test_unavailable_expected_object_and_conditional_burst_security_gaps(self):
        value = snapshot_fixture(); value['inventory']['items'].append({'key':'denied-report-part', 'kind':'unknown',
            'parent_key':'root', 'native_id':None, 'locator':None, 'disposition':'unavailable',
            'reference':'Synthetic denial evidence', 'configuration':{}})
        result = projected(value); asset = next(a for a in result['assets'] if a['source_identity']['object_key']=='denied-report-part')
        self.assertTrue(asset['source_identity']['restricted_private_scope'])
        codes = {g['code'] for g in result['gaps']}
        self.assertTrue({'cognos.condition_semantics_require_review','cognos.drill_semantics_require_review',
                         'cognos.burst_semantics_require_review','cognos.effective_access_unverified'} <= codes)

    def test_foreign_namespace_query_cannot_create_query_authority(self):
        raw = xml_fixture().replace(b'<future:widget', b'<future:query name="Opaque"/><future:widget')
        result = projected(snapshot_fixture(raw))
        foreign = [a for a in result['assets'] if a['source_identity']['xml_qname']=='{urn:synthetic:future}query']
        self.assertEqual(len(foreign),1); self.assertFalse(foreign[0]['source_identity']['query_visual'])
        with self.assertRaisesRegex(ValueError, 'report_namespace_required'):
            V.inspect_xml(xml_fixture().replace(NS.encode(), b'https://unrelated.example.invalid/schemas/report/7.0/'))

    def test_https_origin_custom_ports_are_explicit_and_cannot_smuggle_paths(self):
        for origin in ('https://source.example.invalid:9443', 'https://[2001:db8::1]:9300'):
            value = snapshot_fixture(); value['identity']['source_origin'] = origin
            self.assertEqual(V.validate_snapshot(value)['identity']['source_origin'], origin)
        for origin in ('https://source.example.invalid:0', 'https://source.example.invalid:65536',
                       'https://source.example.invalid:bad', 'https://source.example.invalid/path',
                       'https://source example.invalid', 'https://source.example.invalid?query=one'):
            value = snapshot_fixture(); value['identity']['source_origin'] = origin
            with self.subTest(origin=origin), self.assertRaisesRegex(ValueError, 'source_origin'):
                V.validate_snapshot(value)

    def test_missing_required_elements_remain_explicit_not_runtime_validation(self):
        result = projected(snapshot_fixture(('<report xmlns="%s"/>' % NS).encode()))
        missing = [g['detail'] for g in result['gaps'] if g['code']=='cognos.required_report_element_missing']
        self.assertEqual(set(missing), {'modelPath','queries','layouts'})
        self.assertEqual(result['native_validation'], 'not_run')


if __name__ == '__main__': unittest.main()
