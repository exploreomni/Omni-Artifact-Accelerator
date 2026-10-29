"""Offline immutable Report capture tests with original synthetic RDL/results."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
F=load('report_capture_fixture','tests/test_rdl_report.py')
C=load('report_capture_under_test','skills/omni-artifact-translator/scripts/report_source_capture.py')

def state():
    return {'filters':{'dataset':[],'report':[],'group':[]},'parameters':[{'name':'Period','answer_mode':'explicit','values':['2025']}],
        'timezone':'UTC','locale':'en-US','principal':'fixture:principal','cache':'observed-existing','reference':'fixture:state'}

def prepare(root,platform='ssrs'):
    source=root/'supplied'; source.mkdir(); snapshot=F.snapshot_fixture(platform)
    (source/'snapshot.json').write_bytes(C.encoded(snapshot)); (source/'original.rdl').write_text(snapshot['report_xml']['content'])
    (source/'inventory.json').write_bytes(C.encoded(snapshot['inventory']))
    request={'schema_version':C.REQUEST_SCHEMA,'capture_id':'fixture-report','snapshot_path':'snapshot.json','definition_path':'original.rdl','inventory_path':'inventory.json',
        'evidence_mode':'synthetic_fixture','authorization_ref':'fixture:not-real-authorization','route':'unselected','route_reference':None,'target_surface':'report','state':state()}
    return request,source,root/'capture'

def profile():
    return {'schema_version':1,'format':'csv','headers':['id','amount'],'columns':[
        {'ordinal':0,'name':'id','type':'integer','nullable':False,'null_tokens':[]},
        {'ordinal':1,'name':'amount','type':'decimal','nullable':True,'null_tokens':['NULL']}], 'rows_pointer':None,'subtotal_policy':'preserve'}

def add_results(directory,source,key='data'):
    (source/'results.csv').write_bytes(b'id,amount\n9007199254740993,12.340000000000001\n2,NULL\n')
    evidence={'attachment_id':'result','object_key':key,'format':'csv','result_scope':'dataset_result','observed_state':{
        'state':state(),'observed_at':'2026-01-01T00:00:00Z','reference':'fixture:observed','execution_status':'completed','placement_reference':None,'result_context':F.result_contract()},
        'population':{'key':'selected-period','description':'Synthetic selected period','reference':'fixture:population'},
        'freshness':{'data_watermark':'2025-12-31','observed_at':'2026-01-01T00:00:00Z','reference':'fixture:freshness'},
        'completeness':{'status':'complete','row_count':2,'reference':'fixture:complete'},'reference':'fixture:csv','source_path':'results.csv','parser_profile':profile()}
    return C.import_evidence(directory,evidence,source)['capture']

def comparison_fixture(capture):
    inventory=C.parse_capture(capture,C.encoded(capture),vars(F.T)); asset=next(a for a in inventory['assets'] if a['source_identity']['object_key']=='data')
    attachment=capture['attachments'][0]
    binding={'definition_fingerprint':capture['source']['definition_fingerprint'],'state_sha256':C.sha(capture['request']['state']),'object_key':'data','attachment_id':'result'}
    case={'lane':'numeric','source_capture':{'path':'capture-000002.json','sha256':'fixture-pin'},'source_binding':binding}
    normalized_binding={**binding,'capture_content_hash':capture['content_hash'],'attachment_sha256':attachment['file']['sha256']}
    context={**state(),**F.result_contract(),'population':'selected-period','data_watermark':'2025-12-31','result_scope':'dataset_result'}
    source={'format':'report-normalized','file':{'path':'normalized.json'},'raw_file':attachment['file'],'context':context}
    target={'context':copy.deepcopy(context)}
    return asset,case,source,target,normalized_binding

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name).resolve()
        self.request,self.source,self.directory=prepare(self.root)
    def capture(self): return C.import_local(self.request,self.source,self.directory)['capture']
    def test_immutable_import_separate_definition_and_inventory_and_privacy(self):
        value=self.capture(); self.assertEqual(C.check_capture(self.directory)['status'],'verified_supplied_bytes')
        self.assertEqual((self.directory/'snapshot.json').stat().st_mode&0o777,0o600)
        self.assertEqual(C.load_latest(self.directory)[0],value)
        with self.assertRaisesRegex(ValueError,'new_empty'): self.capture()
    def test_no_traversal_symlink_or_original_mismatch(self):
        self.request['definition_path']='../escape.rdl'
        with self.assertRaises(ValueError): self.capture()
        self.request['definition_path']='original.rdl'; (self.source/'original.rdl').unlink(); (self.source/'original.rdl').symlink_to(self.source/'snapshot.json')
        with self.assertRaises(ValueError): self.capture()
    def test_changed_definition_or_independent_inventory_rejects(self):
        (self.source/'inventory.json').write_bytes(C.encoded({**F.snapshot_fixture()['inventory'],'items':[]}))
        with self.assertRaisesRegex(ValueError,'inventory_mismatch'): self.capture()
    def test_append_evidence_and_history_tampering(self):
        self.capture(); value=add_results(self.directory,self.source)
        self.assertEqual(value['revision'],2); self.assertEqual(C.check_capture(self.directory)['attachments'],1)
        (self.directory/value['attachments'][0]['file']['path']).write_text('changed')
        with self.assertRaises(ValueError): C.load_latest(self.directory)
    def test_exact_numeric_comparison_and_independent_target_cache(self):
        self.capture(); capture=add_results(self.directory,self.source); asset,case,source,target,binding=comparison_fixture(capture)
        raw=(self.source/'results.csv').read_bytes(); normalized=C.normalize_results(raw,profile(),binding)
        self.assertEqual(normalized['rows'][0],{'id':'9007199254740993','amount':'12.340000000000001'})
        target['context']['cache']='independently-selected-target-policy'
        self.assertEqual(C.comparison_gaps(capture,asset,case,source,target,normalized,[{'source':'id'},{'source':'amount'}]),[])
        target['context']['parameters']=[]; self.assertIn('context.parameters',C.comparison_gaps(capture,asset,case,source,target,normalized,[{'source':'id'},{'source':'amount'}]))
    def test_unknown_partial_state_and_wrong_result_count_never_pass(self):
        self.capture(); capture=add_results(self.directory,self.source); asset,case,source,target,binding=comparison_fixture(capture)
        normalized=C.normalize_results((self.source/'results.csv').read_bytes(),profile(),binding)
        normalized['row_count']=1
        self.assertIn('source.rdl_typed_rows_or_count_missing',C.comparison_gaps(capture,asset,case,source,target,normalized,[{'source':'id'},{'source':'amount'}]))
        source['context']['row_limit']=10
        self.assertIn('context.row_limit',C.comparison_gaps(capture,asset,case,source,target,normalized,[{'source':'id'},{'source':'amount'}]))
    def test_report_placement_cannot_use_dataset_csv_as_report_proof(self):
        self.capture(); capture=add_results(self.directory,self.source,key='first')
        projected=C.parse_capture(capture,C.encoded(capture),vars(F.T)); asset=next(a for a in projected['assets'] if a['source_identity']['object_key']=='first')
        case={'lane':'numeric','source_capture':{},'source_binding':{'definition_fingerprint':capture['source']['definition_fingerprint'],
            'state_sha256':C.sha(state()),'object_key':'first','attachment_id':'result'}}
        gaps=C.comparison_gaps(capture,asset,case,{'file':capture['attachments'][0]['file']},{})
        self.assertIn('source.rdl_report_calculation_or_placement_unverified',gaps)
    def test_normalizer_rejects_formatted_ragged_duplicate_and_inexact_numbers(self):
        binding={'capture_content_hash':'a','definition_fingerprint':'b','state_sha256':'c','object_key':'data','attachment_id':'result','attachment_sha256':'d'}
        for raw in (b'id,amount\n1,"$1,234"\n',b'id,amount\n1\n',b'id,id\n1,2\n',b'id,amount\n1,NaN\n'):
            binding['attachment_sha256']=C.sha(raw)
            with self.assertRaises(ValueError): C.normalize_results(raw,profile(),binding)
    def test_normalization_profile_tampering_and_missing_compared_column_reject(self):
        self.capture(); capture=add_results(self.directory,self.source); asset,case,source,target,binding=comparison_fixture(capture)
        normalized=C.normalize_results((self.source/'results.csv').read_bytes(),profile(),binding)
        gaps=C.comparison_gaps(capture,asset,case,source,target,normalized,[{'source':'id'}])
        self.assertIn('source.rdl_columns_not_fully_compared',gaps)
        normalized['parser_profile']['columns'][1]['type']='string'
        self.assertIn('source.rdl_normalization_binding',C.comparison_gaps(capture,asset,case,source,target,normalized,[{'source':'id'},{'source':'amount'}]))
        normalized['rows'][0]['amount']='99'
        with self.assertRaises(ValueError): C.verify_normalized_result(normalized,(self.source/'results.csv').read_bytes())

    def test_supplied_complete_wrong_row_count_and_credentials_reject(self):
        self.capture(); capture=add_results(self.directory,self.source)
        value=copy.deepcopy(capture); value['attachments'][0]['completeness']['row_count']=3
        value['content_hash']=C.sha({k:v for k,v in value.items() if k!='content_hash'})
        with self.assertRaisesRegex(ValueError,'row_count'): C.verify_capture_files(value,self.directory)
        self.request['authorization_ref']='Bearer syntheticInvalidToken123456'
        with self.assertRaises(ValueError): C.validate_request(self.request)

    def test_json_raw_numeric_precision_and_catalog_not_complete(self):
        raw=b'{"rows":[{"id":9007199254740993,"amount":1.0000000000000001}]}'
        p=profile(); p.update(format='json',rows_pointer='/rows')
        binding={'capture_content_hash':'a','definition_fingerprint':'b','state_sha256':'c','object_key':'data','attachment_id':'result','attachment_sha256':C.sha(raw)}
        normalized=C.normalize_results(raw,p,binding)
        self.assertEqual(normalized['rows'][0]['amount'],'1.0000000000000001')
        self.assertEqual(normalized['rows'][0]['id'],'9007199254740993')

    def test_fixed_operation_plans_never_execute_or_accept_tokens(self):
        p={'kind':'ssrs2017-rest-v2','source_origin':'https://source.example.invalid','rest_path':'/reports/api/v2.0','runtime_version':'2017-reviewed',
            'qualification_ref':'fixture:profile','principal_ref':'fixture:principal','report_id':'11111111-1111-4111-8111-111111111111',
            'workspace_id':None,'execution_ref':None,'max_bytes':1048576,'max_polls':5}
        planned=C.plan_operation(p,{'kind':'definition'}); self.assertTrue(planned['url'].endswith('/Content/$value')); self.assertFalse(planned['network_execution_supported'])
        p.update(kind='powerbi-paginated-rest-v1',source_origin='https://api.powerbi.com',rest_path='/v1.0/myorg',workspace_id='22222222-2222-4222-8222-222222222222')
        body={'format':'PDF','paginatedReportConfiguration':{'parameterValues':[{'name':'Period','value':'2025'}],'locale':'en-US'}}
        with self.assertRaises(ValueError): C.plan_operation(p,{'kind':'export_submit','body':body})
        p['execution_ref']='fixture:separate-query-approval'; planned=C.plan_operation(p,{'kind':'export_submit','body':body})
        self.assertEqual(planned['method'],'POST'); self.assertTrue(planned['requires_host_authorization'])
        body['paginatedReportConfiguration']['identities']=[{'identityBlob':'never-use'}]
        with self.assertRaises(ValueError): C.plan_operation(p,{'kind':'export_submit','body':body})
        with self.assertRaisesRegex(ValueError,'unqualified'): C.capture(p,self.directory)
    def test_cli_summary_and_existing_output_not_overwritten(self):
        request=self.source/'request.json'; request.write_bytes(C.encoded(self.request))
        command=[sys.executable,'-I','-S','-B',str(ROOT/'skills/omni-artifact-translator/scripts/report_source_capture.py'),'import-local','--request',str(request),'--source-root',str(self.source),'--directory',str(self.directory)]
        run=subprocess.run(command,capture_output=True,text=True); self.assertEqual(run.returncode,0,run.stdout)
        response=json.loads(run.stdout); self.assertEqual(set(response),{'status','output'}); self.assertNotIn('SELECT',run.stdout)
        again=subprocess.run(command,capture_output=True,text=True); self.assertEqual(again.returncode,1)

if __name__=='__main__': unittest.main()
