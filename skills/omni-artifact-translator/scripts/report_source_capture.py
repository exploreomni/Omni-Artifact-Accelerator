"""Immutable supplied RDL evidence and pure qualified-operation planning.

No HTTP, credentials, expression execution, report rendering or native writes.
Operation plans describe bounded requests; only a separately qualified host can
supply authority and execute them. Unknown effects remain explicit.
"""
import argparse
import copy
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote

SCHEMA='report-source-capture.v1'
REQUEST_SCHEMA='report-source-capture-request.v1'
MAX_BYTES=8*1024*1024
MAX_ATTACHMENTS=128


def need(ok,code):
    if not ok: raise ValueError('report_capture.'+code)

def module(name):
    need(name in ('rdl_report','crystal_report','powerbi_capture_files'),'module_rejected')
    path=Path(__file__).with_name(name+'.py')
    need(not any(p.is_symlink() for p in (path,*path.parents)),'module_symlink')
    spec=importlib.util.spec_from_file_location('report_capture_'+name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

F=module('powerbi_capture_files')
encoded=F.encoded

def sha(value): return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()
def text(value): return type(value) is str and 0<len(value)<=2048 and all(ord(c)>=32 for c in value)
def identifier(value): return text(value) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,150}',value) is not None
def local_file(root,path):
    need(type(path) is str and path and '\\' not in path,'relative_path')
    parts=PurePosixPath(path)
    need(not parts.is_absolute() and parts.as_posix()==path and all(p not in ('.','..') for p in parts.parts),'relative_path')
    result=F.no_links(Path(root)/path)
    need(result.is_relative_to(F.no_links(root)),'path_escape')
    return result


def source_module(snapshot):
    names={'rdl-report-snapshot.v1':'rdl_report','crystal-report-snapshot.v1':'crystal_report'}
    need(type(snapshot) is dict and snapshot.get('schema_version') in names,'snapshot_schema')
    return module(names[snapshot['schema_version']])


def definition(snapshot):
    return snapshot['report_xml'] if snapshot['schema_version']=='rdl-report-snapshot.v1' else snapshot['extraction']


def state(value):
    need(type(value) is dict and set(value)=={'filters','parameters','timezone','locale','principal','cache','reference'},'state_fields')
    need(type(value['filters']) is dict and set(value['filters'])=={'dataset','report','group'}
         and all(type(v) is list and len(v)<=128 for v in value['filters'].values()),'filter_stages')
    need(type(value['parameters']) is list and len(value['parameters'])<=128,'parameters')
    names=set()
    for p in value['parameters']:
        need(type(p) is dict and set(p)=={'name','answer_mode','values'} and text(p['name']) and p['name'] not in names
             and p['answer_mode'] in ('explicit','default','null','blank','omitted','unresolved') and type(p['values']) is list and len(p['values'])<=128,'parameter')
        need(all(v is None or type(v) in (str,int,bool) for v in p['values']),'parameter_values')
        need(p['answer_mode']!='null' or p['values']==[None],'parameter_null')
        need(p['answer_mode']!='blank' or p['values']==[''],'parameter_blank')
        need(p['answer_mode'] not in ('omitted','unresolved') or not p['values'],'parameter_omitted')
        names.add(p['name'])
    need(all(value[k] is None or text(value[k]) for k in ('timezone','locale','principal','cache')) and text(value['reference']),'state_context')
    F.secret_check(value); return value


def validate_request(value):
    need(type(value) is dict and set(value)=={'schema_version','capture_id','snapshot_path','definition_path','inventory_path',
         'evidence_mode','authorization_ref','route','route_reference','target_surface','state'} and value['schema_version']==REQUEST_SCHEMA,'request_fields')
    need(identifier(value['capture_id']) and value['evidence_mode'] in ('synthetic_fixture','manual_transfer','live_tenant')
         and text(value['authorization_ref']) and value['target_surface']=='report','request_identity')
    need(value['route'] in ('unselected','reuse_existing','omni_semantic_reconstruction','warehouse_first_refactor')
         and (value['route_reference'] is None if value['route']=='unselected' else text(value['route_reference'])),'route')
    for k in ('snapshot_path','definition_path','inventory_path'): local_file(Path('/'),value[k])
    state(value['state']); F.secret_check(value); module('rdl_report').screen(encoded(value)); return value


def result_context(value):
    need(type(value) is dict and set(value)=={'data_mode','row_limit','row_limit_stage','aggregation_stage','reference'},'result_context')
    need(value['data_mode'] in ('full_data','preview','test','unknown') and value['row_limit_stage'] in ('before_aggregation','after_aggregation','none','unknown')
         and value['aggregation_stage'] in ('dataset','in_report','unknown') and text(value['reference']),'result_semantics')
    limit=value['row_limit']; need(limit is None or type(limit) is int and limit>0,'row_limit')
    need(value['row_limit_stage']!='none' or limit is None,'row_limit_conflict')
    need(value['row_limit_stage'] not in ('before_aggregation','after_aggregation') or limit is not None,'row_limit_required')
    return value


def attachment(value,snapshot):
    need(type(value) is dict and set(value)=={'attachment_id','object_key','format','result_scope','observed_state','population',
        'freshness','completeness','reference','file','parser_profile'},'attachment_fields')
    need(identifier(value['attachment_id']) and text(value['object_key']) and value['format'] in ('csv','json','png','pdf')
         and value['result_scope'] in ('dataset_result','report_result','displayed','unknown') and text(value['reference']),'attachment_identity')
    source_module(snapshot).scope_item(snapshot,value['object_key'])
    need((type(value['parser_profile']) is dict and value['parser_profile'].get('format')==value['format']) if value['format'] in ('csv','json')
         else value['parser_profile'] is None,'attachment_parser_profile')
    for key,keys in [('population',{'key','description','reference'}),('freshness',{'data_watermark','observed_at','reference'})]:
        obj=value[key]; need(type(obj) is dict and set(obj)==keys and all(v is None or text(v) for v in obj.values()),key)
    complete=value['completeness']
    need(type(complete) is dict and set(complete)=={'status','row_count','reference'} and complete['status'] in ('complete','partial','unknown')
         and (complete['row_count'] is None or type(complete['row_count']) is int and complete['row_count']>=0)
         and (complete['reference'] is None or text(complete['reference'])),'completeness')
    observed=value['observed_state']
    if observed is not None:
        need(type(observed) is dict and set(observed)=={'state','observed_at','reference','execution_status','placement_reference','result_context'},'observed_state')
        state(observed['state']); need(text(observed['observed_at']) and text(observed['reference']) and observed['execution_status'] in ('completed','partial','failed','unknown')
            and (observed['placement_reference'] is None or text(observed['placement_reference'])),'observed_context')
        if observed['result_context'] is not None: result_context(observed['result_context'])
    if complete['status']=='complete' and value['format'] in ('csv','json'):
        need(observed is not None and observed['execution_status']=='completed' and complete['row_count'] is not None and text(complete['reference'])
             and all(text(v) for v in value['population'].values()) and all(text(v) for v in value['freshness'].values()),'complete_evidence_missing')
    pin=value['file']; need(type(pin) is dict and set(pin)=={'path','sha256','bytes'} and type(pin['bytes']) is int and 0<pin['bytes']<=MAX_BYTES
         and type(pin['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}',pin['sha256']) and identifier(pin['path']),'attachment_pin')
    return value


def validate_envelope(value):
    need(type(value) is dict and set(value)=={'schema_version','request','request_sha256','source','attachments','revision','previous_content_hash','gaps','content_hash'}
         and value['schema_version']==SCHEMA,'envelope_fields')
    need(len(encoded(value))<=MAX_BYTES,'envelope_size'); F.secret_check(value); module('rdl_report').screen(encoded(value))
    need(value['content_hash']==sha({k:v for k,v in value.items() if k!='content_hash'}),'content_hash')
    validate_request(value['request']); need(value['request_sha256']==sha(value['request']),'request_hash')
    need(type(value['revision']) is int and 1<=value['revision']<=64 and (value['previous_content_hash'] is None if value['revision']==1
         else type(value['previous_content_hash']) is str and re.fullmatch('[0-9a-f]{64}',value['previous_content_hash'])),'revision')
    source=value['source']; need(type(source) is dict and set(source)=={'snapshot','snapshot_file','definition_file','inventory_file','definition_fingerprint'},'source_fields')
    source_module(source['snapshot']).validate_snapshot(source['snapshot']); need(source['definition_fingerprint']==sha(source['snapshot']),'definition_fingerprint')
    need(type(value['attachments']) is list and len(value['attachments'])<=MAX_ATTACHMENTS,'attachment_limit')
    ids=set()
    for a in value['attachments']:
        attachment(a,source['snapshot']); need(a['attachment_id'] not in ids,'duplicate_attachment'); ids.add(a['attachment_id'])
    need(value['gaps']==['supplied_provenance_not_authenticated','native_render_and_effective_access_unverified','connected_execution_not_qualified'], 'required_gaps')
    return value


def _inspect(raw,fmt):
    need(type(raw) is bytes and 0<len(raw)<=MAX_BYTES,'attachment_size')
    if fmt=='png': F.png_info(raw)
    elif fmt=='pdf': need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-2048:],'pdf_signature')
    elif fmt=='json': F.decode(raw); module('rdl_report').screen(raw)
    else:
        module('rdl_report').screen(raw)
        try:
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8')),strict=True))
        except (UnicodeError,csv.Error): raise ValueError('report_capture.invalid_csv') from None
        need(0<len(rows)<=100001 and all(len(r)<=1024 for r in rows),'csv_shape_limit')
    # PNG/PDF checks establish byte envelope only; no runtime or visual claim.


def verify_capture_files(value,root):
    validate_envelope(value); source=value['source']; snapshot=source['snapshot']
    need(F.decode(F.read_pin(root,source['snapshot_file']))==snapshot,'snapshot_bytes_changed')
    need(F.read_pin(root,source['definition_file'])==definition(snapshot)['content'].encode('utf-8'),'definition_original_changed')
    need(F.decode(F.read_pin(root,source['inventory_file']))==snapshot['inventory'],'independent_inventory_changed')
    total=0
    for a in value['attachments']:
        raw=F.read_pin(root,a['file']); total+=len(raw); need(total<=32*1024*1024,'attachment_total_limit'); _inspect(raw,a['format'])
        if a['format'] in ('csv','json'):
            normalized=normalize_results(raw,a['parser_profile'],{'capture_content_hash':value['content_hash'],
                'definition_fingerprint':source['definition_fingerprint'],'state_sha256':sha(value['request']['state']),
                'object_key':a['object_key'],'attachment_id':a['attachment_id'],'attachment_sha256':a['file']['sha256']})
            need(a['completeness']['status']!='complete' or normalized['row_count']==a['completeness']['row_count'],'complete_row_count_mismatch')
    return value


def _sealed(value):
    value['content_hash']=sha(value); validate_envelope(value); return value


def _write(root,value):
    pin=F.write_once(root,'capture-%06d.json'%value['revision'],encoded(value))
    return {'status':'retained','output':str(root/pin['path']),'capture':value}


def import_local(request,source_root,directory):
    validate_request(request); source_root=F.no_links(source_root)
    snapshot_raw=F.read_file(local_file(source_root,request['snapshot_path']),MAX_BYTES)
    snapshot=F.decode(snapshot_raw); source_module(snapshot).validate_snapshot(snapshot)
    original_definition=F.read_file(local_file(source_root,request['definition_path']),MAX_BYTES)
    inventory=F.read_file(local_file(source_root,request['inventory_path']),MAX_BYTES)
    need(original_definition==definition(snapshot)['content'].encode('utf-8'),'definition_original_mismatch')
    need(F.decode(inventory)==snapshot['inventory'],'independent_inventory_mismatch')
    root=F.private_directory(directory); need(not any(root.iterdir()),'new_empty_capture_required')
    source={'snapshot':snapshot,'snapshot_file':F.write_once(root,'snapshot.json',snapshot_raw),
        'definition_file':F.write_once(root,'definition-original.bin',original_definition),'inventory_file':F.write_once(root,'inventory.json',inventory),
        'definition_fingerprint':sha(snapshot)}
    value=_sealed({'schema_version':SCHEMA,'request':copy.deepcopy(request),'request_sha256':sha(request),'source':source,
        'attachments':[],'revision':1,'previous_content_hash':None,
        'gaps':['supplied_provenance_not_authenticated','native_render_and_effective_access_unverified','connected_execution_not_qualified']})
    return _write(root,value)


def load_latest(directory,config=None):
    root=F.no_links(directory); paths=sorted(root.glob('capture-*.json'))
    need(0<len(paths)<=64,'capture_history_required'); previous=None; value=None
    for number,path in enumerate(paths,1):
        need(path.name=='capture-%06d.json'%number,'capture_history_gap')
        value=F.decode(F.read_file(path,MAX_BYTES)); verify_capture_files(value,root)
        need(value['revision']==number and value['previous_content_hash']==(previous['content_hash'] if previous else None),'capture_chain')
        if previous:
            need(value['request']==previous['request'] and value['source']==previous['source'] and value['attachments'][:-1]==previous['attachments']
                 and len(value['attachments'])==len(previous['attachments'])+1,'capture_history_mutation')
        previous=value
    if config is not None: need(config==value['request'],'capture_request_changed')
    return value,paths[-1]


def check_capture(path):
    path=F.no_links(path)
    if path.is_dir(): value,_=load_latest(path)
    else:
        value=F.decode(F.read_file(path,MAX_BYTES)); verify_capture_files(value,path.parent)
    return {'status':'verified_supplied_bytes','revision':value['revision'],'attachments':len(value['attachments']),
            'native_validation':'not_run','source_execution':False,'target_write_authority':False}
check=check_capture


def import_evidence(directory,evidence,source_root):
    value,_=load_latest(directory); root=F.no_links(directory)
    need(type(evidence) is dict and 'source_path' in evidence and 'file' not in evidence,'evidence_fields')
    raw=F.read_file(local_file(source_root,evidence['source_path']),MAX_BYTES); row={k:copy.deepcopy(v) for k,v in evidence.items() if k!='source_path'}
    _inspect(raw,row.get('format'))
    name='evidence-%06d.%s'%(value['revision'],row['format'])
    row['file']={'path':name,'sha256':sha(raw),'bytes':len(raw)}; attachment(row,value['source']['snapshot'])
    need(row['attachment_id'] not in {a['attachment_id'] for a in value['attachments']},'duplicate_attachment')
    new={k:copy.deepcopy(v) for k,v in value.items() if k!='content_hash'}
    new.update(revision=value['revision']+1,previous_content_hash=value['content_hash']); new['attachments'].append(row)
    new=_sealed(new)
    if row['format'] in ('csv','json'):
        normalized=normalize_results(raw,row['parser_profile'],{'capture_content_hash':new['content_hash'],'definition_fingerprint':new['source']['definition_fingerprint'],
            'state_sha256':sha(new['request']['state']),'object_key':row['object_key'],'attachment_id':row['attachment_id'],'attachment_sha256':row['file']['sha256']})
        need(row['completeness']['status']!='complete' or normalized['row_count']==row['completeness']['row_count'],'complete_row_count_mismatch')
    F.write_once(root,name,raw); return _write(root,new)


def parse_capture(payload,raw,helpers):
    validate_envelope(payload); need(F.decode(raw)==payload,'raw_capture_mismatch')
    snap=payload['source']['snapshot']; result=source_module(snap).translate(snap,encoded(snap),helpers)
    result['source'].update(helpers['base'](payload,raw,snap['identity']['source_platform'],'supplied_report_source_capture')['source'])
    result['source'].update(capture_content_hash=payload['content_hash'],definition_fingerprint=sha(snap))
    result['upstream_payload']=copy.deepcopy(payload)
    result['migration_context'].update(route=None if payload['request']['route']=='unselected' else payload['request']['route'],
        route_reference=payload['request']['route_reference'],target_surface='report')
    return result
translate=parse_capture


def case_binding(asset,case,capture):
    validate_envelope(capture); identity=asset.get('source_identity',{}); snapshot=capture['source']['snapshot']
    key=identity.get('object_key'); need(identity.get('definition_fingerprint')==sha(snapshot),'case_definition')
    scope=source_module(snapshot).scope_item(snapshot,key)
    need(scope['item']['disposition']=='include' and not scope['restricted'],'case_scope')
    binding=case.get('source_binding')
    need(type(binding) is dict and set(binding)=={'definition_fingerprint','state_sha256','object_key','attachment_id'}
         and binding['definition_fingerprint']==sha(snapshot) and binding['state_sha256']==sha(capture['request']['state']) and binding['object_key']==key,'case_binding')
    matches=[a for a in capture['attachments'] if a['attachment_id']==binding['attachment_id'] and a['object_key']==key]
    need(binding['attachment_id'] is None or len(matches)==1,'case_attachment')
    if case.get('lane')=='numeric': need(scope['query_visual'] and len(matches)==1 and matches[0]['format'] in ('csv','json'),'numeric_evidence')
    return binding


def normalize_results(raw,profile,binding):
    need(type(raw) is bytes and len(raw)<=MAX_BYTES and type(profile) is dict and set(profile)=={'schema_version','format','headers','columns','rows_pointer','subtotal_policy'}
         and type(profile['schema_version']) is int and profile['schema_version']==1 and profile['format'] in ('csv','json') and profile['subtotal_policy']=='preserve','normalization_profile')
    need(type(binding) is dict and set(binding)=={'capture_content_hash','definition_fingerprint','state_sha256','object_key','attachment_id','attachment_sha256'}
         and all(text(v) for v in binding.values()) and binding['attachment_sha256']==sha(raw),'normalization_binding')
    headers=profile['headers']; cols=profile['columns']
    need(type(headers) is list and 0<len(headers)<=1024 and all(text(h) for h in headers) and len(headers)==len(set(headers))
         and type(cols) is list and len(cols)==len(headers),'normalization_columns')
    for i,c in enumerate(cols):
        need(type(c) is dict and set(c)=={'ordinal','name','type','nullable','null_tokens'} and type(c['ordinal']) is int and c['ordinal']==i
             and text(c['name']) and c['type'] in ('string','decimal','integer','boolean') and type(c['nullable']) is bool
             and type(c['null_tokens']) is list and all(type(t) is str for t in c['null_tokens']),'column_profile')
    need(len({c['name'] for c in cols})==len(cols),'column_names')
    _inspect(raw,profile['format'])
    if profile['format']=='csv':
        need(profile['rows_pointer'] is None,'csv_pointer')
        source=list(csv.reader(io.StringIO(raw.decode('utf-8')),strict=True)); need(source and source[0]==headers,'headers_mismatch'); rows=source[1:]
    else:
        obj=json.loads(raw.decode('utf-8-sig'),parse_float=Decimal); pointer=profile['rows_pointer']
        need(type(pointer) is str and (pointer=='' or pointer.startswith('/')),'rows_pointer')
        for key in pointer.split('/')[1:]:
            need(type(obj) is dict and not {'error','errors'}&set(obj),'result_pointer_or_error'); key=key.replace('~1','/').replace('~0','~'); need(key in obj,'result_pointer'); obj=obj[key]
        need(type(obj) is list and all(type(r) is dict and set(r)==set(headers) for r in obj),'json_rows')
        rows=[[r[h] for h in headers] for r in obj]
    need(len(rows)<=100000,'row_limit'); output=[]
    for row in rows:
        need(len(row)==len(cols),'ragged_rows'); converted={}
        for c,v in zip(cols,row):
            if v is None or type(v) is str and v in c['null_tokens']:
                need(c['nullable'],'unexpected_null'); parsed=None
            elif c['type']=='string': need(type(v) is str,'string_required'); parsed=v
            elif c['type']=='boolean': need(type(v) is bool,'boolean_required'); parsed=v
            else:
                need(type(v) in (str,int,Decimal) and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',str(v)) is not None,'raw_numeric_required')
                try: number=Decimal(v)
                except InvalidOperation: raise ValueError('report_capture.number_invalid') from None
                need(number.is_finite() and abs(number.adjusted())<=1000,'number_range')
                if c['type']=='integer': need(number==number.to_integral_value(),'integer_fraction')
                parsed=str(number)  # Exact decimal/int64 lexical value, no float conversion.
            converted[c['name']]=parsed
        output.append(converted)
    return {'schema_version':1,'kind':'report_source_normalized_results','raw_sha256':sha(raw),'parser_profile':copy.deepcopy(profile),
        'binding':copy.deepcopy(binding),'row_count':len(output),'rows':output,'completeness':'not_inferred_from_rows'}


def verify_normalized_result(value,raw):
    need(type(value) is dict and value==normalize_results(raw,value.get('parser_profile'),value.get('binding')),'normalization_changed')
    return value


def comparison_gaps(capture,asset,case,source,target,normalized=None,columns=None):
    binding=case_binding(asset,case,capture); gaps=[]
    matches=[a for a in capture['attachments'] if a['attachment_id']==binding['attachment_id']]
    if len(matches)!=1: return ['source.rdl_result_attachment_required']
    a=matches[0]; pin=source.get('raw_file') if source.get('format')=='report-normalized' else source.get('file')
    if not pin or pin.get('sha256')!=a['file']['sha256']: gaps.append('source.rdl_result_not_bound')
    if not case.get('source_capture'): gaps.append('source.rdl_capture_required')
    observed=a['observed_state']; expected=capture['request']['state']
    if not observed or observed['execution_status']!='completed': gaps.append('source.rdl_execution_unverified')
    for k in ('filters','parameters','timezone','locale','principal','cache'):
        if expected[k] is None or not observed or observed['state'][k]!=expected[k] or source.get('context',{}).get(k)!=expected[k]: gaps.append('source.rdl_observed.'+k)
        if k not in ('principal','cache') and target.get('context',{}).get(k)!=expected[k]: gaps.append('context.'+k)
    if any(p['answer_mode'] in ('unresolved','omitted') for p in expected['parameters']): gaps.append('source.rdl_parameters_unresolved')
    if a['completeness']['status']!='complete': gaps.append('source.rdl_completeness_unverified')
    scope=source_module(capture['source']['snapshot']).scope_item(capture['source']['snapshot'],binding['object_key'])
    if scope['item']['kind']!='dataset' and (a['result_scope']!='report_result' or not observed or not observed['placement_reference']): gaps.append('source.rdl_report_calculation_or_placement_unverified')
    actual=observed.get('result_context') if observed else None; contract=scope['item']['configuration'].get('result_contract')
    if actual is None or contract is None: gaps.append('source.rdl_result_context_missing')
    else:
        result_context(contract)
        for k in ('data_mode','row_limit','row_limit_stage','aggregation_stage'):
            if actual[k]!=contract[k] or source.get('context',{}).get(k,'__missing__')!=actual[k] or target.get('context',{}).get(k,'__missing__')!=actual[k]: gaps.append('context.'+k)
        if actual['data_mode'] in ('unknown','test') or actual['row_limit_stage']=='unknown' or actual['aggregation_stage']=='unknown': gaps.append('source.rdl_result_semantics_unqualified')
        if scope['item']['kind']!='dataset' and actual['aggregation_stage']!='in_report': gaps.append('source.rdl_report_aggregation_required')
    for k,expected_value in {'population':a['population']['key'],'data_watermark':a['freshness']['data_watermark'],'result_scope':a['result_scope']}.items():
        if expected_value is None or source.get('context',{}).get(k)!=expected_value or target.get('context',{}).get(k)!=expected_value: gaps.append('context.'+k)
    if normalized is None or normalized.get('kind')!='report_source_normalized_results' or normalized.get('row_count')!=a['completeness']['row_count']: gaps.append('source.rdl_typed_rows_or_count_missing')
    else:
        expected_binding={**binding,'capture_content_hash':capture['content_hash'],'attachment_sha256':a['file']['sha256']}
        if normalized.get('binding')!=expected_binding or normalized.get('parser_profile')!=a['parser_profile']: gaps.append('source.rdl_normalization_binding')
        if (type(columns) is not list or any(type(c) is not dict for c in columns) or len(columns)!=len(a['parser_profile']['columns'])
            or {c.get('source') for c in columns}!={c['name'] for c in a['parser_profile']['columns']}): gaps.append('source.rdl_columns_not_fully_compared')
    return sorted(set(gaps))


def capture(*args,**kwargs): raise ValueError('report_capture.connected_execution_unqualified_use_reviewed_plan_only')


def plan_operation(profile,operation):
    """Pure request construction; references are not grants and no request runs."""
    need(type(profile) is dict and set(profile)=={'kind','source_origin','rest_path','runtime_version','qualification_ref','principal_ref','report_id','workspace_id','execution_ref','max_bytes','max_polls'},'operation_profile')
    need(profile['execution_ref'] is None or text(profile['execution_ref']),'execution_reference')
    need(profile['kind'] in ('ssrs2017-rest-v2','powerbi-paginated-rest-v1') and all(text(profile[k]) for k in ('runtime_version','qualification_ref','principal_ref')),'operation_qualification')
    need(type(profile['max_bytes']) is int and 1<=profile['max_bytes']<=MAX_BYTES and type(profile['max_polls']) is int and 1<=profile['max_polls']<=50,'operation_budget')
    need(type(operation) is dict and set(operation)<={'kind','body','export_id','catalog_scope_reference'} and text(operation.get('kind')),'operation_fields')
    kind=operation['kind']; body=operation.get('body'); method='GET'
    guid=r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}'
    need(type(profile['report_id']) is str and re.fullmatch(guid,profile['report_id']),'report_guid')
    if profile['kind']=='ssrs2017-rest-v2':
        need(module('rdl_report').origin(profile['source_origin']) and type(profile['rest_path']) is str
             and re.fullmatch(r'(?:/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)+',profile['rest_path']) and profile['workspace_id'] is None,'ssrs_route')
        need(kind in ('catalog','metadata','definition') and body is None and operation.get('export_id') is None,'ssrs_operation')
        if kind=='catalog':
            need(text(operation.get('catalog_scope_reference')),'catalog_scope_reference_required')
            url=profile['source_origin']+profile['rest_path']+'/Reports'
        else:
            need(operation.get('catalog_scope_reference') is None,'unexpected_catalog_scope')
            url=profile['source_origin']+profile['rest_path']+'/Reports('+profile['report_id']+')'+('/Content/$value' if kind=='definition' else '')
    else:
        need(profile['source_origin']=='https://api.powerbi.com' and profile['rest_path']=='/v1.0/myorg'
             and type(profile['workspace_id']) is str and re.fullmatch(guid,profile['workspace_id']),'powerbi_route')
        need(kind in ('metadata','definition','export_submit','export_status','export_file') and operation.get('catalog_scope_reference') is None,'powerbi_operation')
        url=profile['source_origin']+profile['rest_path']+'/groups/'+profile['workspace_id']+'/reports/'+profile['report_id']
        if kind=='definition': url+='/Export'
        elif kind=='export_submit':
            need(text(profile['execution_ref']),'render_execution_reference_required'); method='POST'; url+='/ExportTo'
            need(type(body) is dict and set(body)=={'format','paginatedReportConfiguration'} and body['format'] in ('PDF','XLSX'),'export_body')
            config=body['paginatedReportConfiguration']
            need(type(config) is dict and set(config)=={'parameterValues','locale'} and text(config['locale']) and type(config['parameterValues']) is list and len(config['parameterValues'])<=128,'export_configuration')
            need(all(type(p) is dict and set(p)=={'name','value'} and text(p['name']) and type(p['value']) is str and len(p['value'])<=2048 for p in config['parameterValues']),'export_parameters')
        elif kind in ('export_status','export_file'):
            job=operation.get('export_id'); need(text(job) and job not in ('.','..') and not any(c in job for c in '/\\?#'),'export_job')
            url+='/exports/'+quote(job,safe='')+('/file' if kind=='export_file' else '')
        if kind!='export_submit': need(body is None,'unexpected_body')
        if kind not in ('export_status','export_file'): need(operation.get('export_id') is None,'unexpected_job')
    F.secret_check(profile); F.secret_check(operation); module('rdl_report').screen(encoded([profile,operation]))
    request={'method':method,'url':url,'body':body}
    return {**request,'request_sha256':sha(request),'profile_sha256':sha(profile),'requires_host_authorization':True,
        'network_execution_supported':False,'requested_max_bytes':profile['max_bytes'],'requested_max_polls':profile['max_polls'],
        'gaps':['runtime_and_permissions_not_authenticated','no_transport_or_redirect_authority','export_job_must_be_bound_to_original_submit',
                'render_may_execute_queries','uncertain_POST_must_not_be_retried_automatically','catalog_page_does_not_establish_complete_inventory']}


def main():
    parser=argparse.ArgumentParser(description=__doc__); subs=parser.add_subparsers(dest='command',required=True)
    p=subs.add_parser('import-local'); p.add_argument('--request',required=True); p.add_argument('--source-root',required=True); p.add_argument('--directory',required=True)
    p=subs.add_parser('import-evidence'); p.add_argument('--directory',required=True); p.add_argument('--evidence',required=True); p.add_argument('--source-root',required=True)
    p=subs.add_parser('check'); p.add_argument('--capture',required=True)
    p=subs.add_parser('plan-operation'); p.add_argument('--profile',required=True); p.add_argument('--operation',required=True); p.add_argument('--output',required=True)
    args=parser.parse_args()
    try:
        if args.command=='import-local': r=import_local(F.decode(F.read_file(args.request,MAX_BYTES)),args.source_root,args.directory)
        elif args.command=='import-evidence': r=import_evidence(args.directory,F.decode(F.read_file(args.evidence,MAX_BYTES)),args.source_root)
        elif args.command=='check': r=check_capture(args.capture)
        else:
            r=plan_operation(F.decode(F.read_file(args.profile,MAX_BYTES)),F.decode(F.read_file(args.operation,MAX_BYTES)))
            target=F.no_links(args.output); F.write_once(F.private_directory(target.parent),target.name,encoded(r)); r={'status':'planned_unexecuted','output':str(target)}
        print(json.dumps({k:v for k,v in r.items() if k not in ('capture',)},sort_keys=True))
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'rejected','error':'report_source_input_rejected'})); raise SystemExit(1)

if __name__=='__main__': main()
