"""Original neutral RDL fixtures; supplied evidence, never tenant/schema proof."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
R=load('test_rdl_reader','skills/omni-artifact-translator/scripts/rdl_report.py')
T=load('test_rdl_translator','skills/omni-artifact-translator/scripts/translate_artifact.py')
XML='''<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2008/01/reportdefinition">
<DataSources><DataSource Name="Source"><ConnectionProperties><DataProvider>SQL</DataProvider><ConnectString>Data Source=example.invalid;Initial Catalog=Fixture</ConnectString><IntegratedSecurity>true</IntegratedSecurity></ConnectionProperties></DataSource></DataSources>
<DataSets><DataSet Name="Measurements"><Query><DataSourceName>Source</DataSourceName><CommandText>SELECT sample_key, amount FROM fixture_measurements</CommandText></Query><Fields><Field Name="Amount"><DataField>amount</DataField></Field></Fields></DataSet></DataSets>
<ReportParameters><ReportParameter Name="Period"><DataType>String</DataType><DefaultValue><Values><Value>2025</Value></Values></DefaultValue><MultiValue>false</MultiValue></ReportParameter></ReportParameters>
<Body><ReportItems><Tablix Name="TableA"><DataSetName>Measurements</DataSetName><Height>1in</Height><Width>3in</Width></Tablix><Tablix Name="TableB"><DataSetName>Measurements</DataSetName><Height>1in</Height><Width>3in</Width></Tablix></ReportItems><Height>4in</Height></Body>
<Width>6in</Width><Page><PageHeight>11in</PageHeight><PageWidth>8.5in</PageWidth><LeftMargin>1in</LeftMargin><RightMargin>1in</RightMargin></Page></Report>'''

def result_contract():
    return {'data_mode':'full_data','row_limit':None,'row_limit_stage':'none','aggregation_stage':'dataset','reference':'fixture:source-result-contract'}

def snapshot_fixture(platform='ssrs'):
    raw=XML.encode()
    def item(key,kind,locator,parent='report',native=None):
        return {'key':key,'kind':kind,'parent_key':parent,'native_id':native,'locator':locator,'disposition':'include','reference':'fixture:independent-'+key,'configuration':{}}
    items=[item('report','report','/',None),item('data','dataset','/1/0',native='Measurements'),
        item('first','placement','/3/0/0',native='TableA'),item('second','placement','/3/0/1',native='TableB'),
        item('period','parameter','/2/0',native='Period')]
    items[1]['configuration']['result_contract']=result_contract()
    return {'schema_version':R.SCHEMA,'identity':{'source_platform':platform,'source_origin':None,'product_version':'supplied-unverified',
        'principal_ref':'fixture:principal','report_id':None,'workspace_id':None,'content_path':None,'reference':'fixture:identity'},
        'report_xml':{'encoding':'utf-8','content':XML,'bytes':len(raw),'sha256':R.sha(raw),'reference':'fixture:original-rdl'},
        'inventory':{'reference':'fixture:independent-list','completeness':'partial','items':items},'gaps':['Synthetic source only']}

def set_xml(snapshot,xml):
    snapshot['report_xml'].update(content=xml,bytes=len(xml.encode()),sha256=R.sha(xml.encode()))

def project(snapshot): return R.translate(snapshot,R.encoded(snapshot),vars(T))

class RdlTests(unittest.TestCase):
    def test_independent_scope_repeated_placements_and_raw_queries(self):
        s=snapshot_fixture(); p=project(s)
        selected={a['source_identity']['object_key']:a for a in p['assets'] if a['source_identity']['object_key']}
        self.assertNotEqual(selected['first']['asset_key'],selected['second']['asset_key'])
        self.assertEqual(selected['first']['source_identity']['dataset_locator'],'/1/0')
        self.assertTrue(selected['data']['source_identity']['query_visual'])
        self.assertIn('SELECT sample_key',p['upstream_payload']['report_xml']['content'])
        self.assertEqual(p['source']['platform'],'ssrs'); self.assertFalse(p['migration_context']['target_write_authority'])
        self.assertGreater(p['rdl_coverage']['additional_occurrence_obligations'],0)

    def test_powerbi_paginated_separate_from_pbir(self):
        p=project(snapshot_fixture('powerbi_paginated'))
        self.assertEqual(p['source']['platform'],'powerbi_paginated')
        self.assertEqual(p['source']['format'],'supplied_rdl_report_snapshot')
        self.assertEqual(p['migration_context']['target_surface'],'report')

    def test_original_and_raw_snapshot_pins(self):
        s=snapshot_fixture(); s['report_xml']['content']=s['report_xml']['content'].replace('TableA','Changed')
        with self.assertRaisesRegex(ValueError,'definition_pin'): R.validate_snapshot(s)
        s=snapshot_fixture()
        with self.assertRaisesRegex(ValueError,'raw_payload'): R.translate(s,R.encoded({'different':True}),vars(T))

    def test_namespace_spoof_extension_and_unknown_dialect(self):
        with self.assertRaisesRegex(ValueError,'namespace'): R.inspect_xml(XML.replace('/2008/01/','/9999/01/').encode())
        s=snapshot_fixture(); set_xml(s,XML.replace('<Tablix Name="TableA">','<Tablix xmlns="urn:custom" Name="TableA">'))
        with self.assertRaisesRegex(ValueError,'kind_mismatch'): R.validate_snapshot(s)
        s['inventory']['items'][2]['kind']='unknown'; p=project(s)
        self.assertFalse(next(a for a in p['assets'] if a['source_identity']['object_key']=='first')['source_identity']['query_visual'])
        self.assertTrue(any(g['code']=='rdl.extension_namespace_unqualified' for g in p['gaps']))

    def test_unsafe_xml_entities_encoding_and_bounds(self):
        cases=[b'<!DOCTYPE Report [<!ENTITY x SYSTEM "file:///etc/passwd">]>'+XML.encode(),
            XML.encode().replace(b'<Width>6in</Width>',b'<Width>&bad;</Width>'),
            XML.encode('utf-16'), b'x'*(R.MAX_XML_BYTES+1),
            XML.replace('<Width>6in</Width>','<x>'*70+'a'+'</x>'*70).encode()]
        for raw in cases:
            with self.subTest(size=len(raw)),self.assertRaises(ValueError): R.inspect_xml(raw)

    def test_credentials_reject_but_code_remains_inert_obligation(self):
        with self.assertRaises(ValueError): R.inspect_xml(XML.replace('Initial Catalog=Fixture','Password=not-a-real-secret').encode())
        s=snapshot_fixture(); set_xml(s,XML.replace('</Report>','<Code>def dangerous(): pass</Code><Subreport Name="Child"><ReportName>/private/child</ReportName></Subreport><Textbox Name="Caption"><Value>=Sum(Fields!Amount.Value)</Value></Textbox></Report>'))
        p=project(s)
        self.assertTrue(any(g['code']=='rdl.code_preserved_not_executed' for g in p['gaps']))
        self.assertTrue(any(g['code']=='rdl.expression_preserved_not_executed' for g in p['gaps']))
        self.assertTrue(any(d['reference_kind']=='ReportName' for d in p['dependencies']))
        self.assertFalse(p['source_execution'])

    def test_missing_or_ambiguous_dataset_keeps_query_obligations(self):
        for mode in ('missing','ambiguous','excluded'):
            s=snapshot_fixture()
            if mode=='missing': set_xml(s,XML.replace('<DataSetName>Measurements</DataSetName>','<DataSetName>Absent</DataSetName>'))
            elif mode=='ambiguous': set_xml(s,XML.replace('</DataSets>','<DataSet Name="Measurements"><Query><CommandText>SELECT 2</CommandText></Query></DataSet></DataSets>'))
            else: s['inventory']['items'][1]['disposition']='out_of_scope'
            p=project(s); first=next(a for a in p['assets'] if a['source_identity']['object_key']=='first')
            self.assertFalse(first['source_identity']['query_visual']); self.assertTrue(first['source_identity']['requires_source_review'])

    def test_missing_expected_object_and_inherited_private_scope(self):
        s=snapshot_fixture(); s['inventory']['items'][0]['configuration']={'private':True}
        s['inventory']['items'][2]['locator']=None; p=project(s)
        self.assertTrue(all(a['source_identity']['restricted_private_scope'] for a in p['assets']))
        self.assertTrue(any(g['code']=='rdl.expected_object_without_source' for g in p['gaps']))
        self.assertFalse(any(a['source_identity']['query_visual'] for a in p['assets']))

    def test_empty_dataset_is_not_query_evidence_and_snapshot_helper_preserves_bytes(self):
        s=snapshot_fixture(); original=s['report_xml']['content'].encode()
        self.assertEqual(R.make_snapshot(original,s['identity'],s['inventory'],'fixture:original-rdl',s['gaps']),s)
        set_xml(s,XML.replace('SELECT sample_key, amount FROM fixture_measurements',''))
        self.assertFalse(R.scope_item(s,'data')['query_visual'])
        self.assertFalse(R.scope_item(s,'first')['query_visual'])

    def test_malformed_inventory_ids_parents_and_source_identity(self):
        mutations=[lambda s:s['inventory']['items'][1].update(native_id='Wrong'),lambda s:s['inventory']['items'][1].update(parent_key='absent'),
            lambda s:s['inventory']['items'][0].update(parent_key='data'),lambda s:s['identity'].update(source_platform='powerbi'),
            lambda s:s['identity'].update(source_origin='https://user:password@example.invalid'),lambda s:s['identity'].update(workspace_id='invented-ssrs-workspace')]
        for change in mutations:
            s=snapshot_fixture(); change(s)
            with self.assertRaises(ValueError): R.validate_snapshot(s)

if __name__=='__main__': unittest.main()
