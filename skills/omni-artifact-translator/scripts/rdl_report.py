"""Bounded inert RDL evidence for SSRS and Power BI paginated reports.

No XSD fetch, expression evaluation, SQL execution, renderer or source mutation.
A namespace match identifies a reviewed dialect, not full schema conformance.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

SCHEMA = SNAPSHOT_SCHEMA = 'rdl-report-snapshot.v1'
MAX_XML_BYTES, MAX_NODES, MAX_DEPTH, MAX_ITEMS = 2 * 1024 * 1024, 12000, 64, 2000
NAMESPACES = {'http://schemas.microsoft.com/sqlserver/reporting/' + year + '/reportdefinition'
              for year in ('2003/10', '2005/01', '2008/01', '2010/01', '2016/01')}
KINDS = {'report','page','dataset','data_source','field','parameter','visual','placement','layout',
         'content','filter','sort','group','expression','action','subreport','resource','code','query','unknown'}
TAGS = {'Report':'report','ReportSection':'page','Page':'page','Body':'layout',
        'DataSet':'dataset','DataSource':'data_source','Field':'field','ReportParameter':'parameter',
        'QueryParameter':'parameter','Filter':'filter','SortExpression':'sort','Group':'group',
        'Grouping':'group','Tablix':'visual','Table':'visual','Matrix':'visual','List':'visual','Chart':'visual',
        'GaugePanel':'visual','Map':'visual','Rectangle':'layout','Textbox':'content','Image':'resource',
        'Subreport':'subreport','Action':'action','Drillthrough':'action','Code':'code',
        'CodeModule':'code','Class':'code','CustomReportItem':'code', 'Query':'query'}
NORMAL = {'report':'workbook','dataset':'query','data_source':'definition','field':'definition',
          'sort':'definition','group':'definition','expression':'definition','subreport':'action',
          'resource':'content','code':'unknown','query':'query'}
STRUCTURAL = set(('ReportSections ReportItems DataSources DataSets Fields Query ConnectionProperties '
    'DataProvider ConnectString IntegratedSecurity DataSourceReference SharedDataSet SharedDataSetReference '
    'SharedDataSets DataSourceName CommandType CommandText QueryParameters ReportParameters DataType '
    'Nullable AllowBlank MultiValue Prompt Hidden DefaultValue Values Value ValidValues DataSetReference '
    'DataSetName ValueField LabelField DataField Filters FilterExpression Operator FilterValues '
    'SortExpressions Direction GroupExpressions GroupExpression Parent Filters PageHeader PageFooter '
    'PageHeight PageWidth InteractiveHeight InteractiveWidth LeftMargin RightMargin TopMargin BottomMargin '
    'Height Width Top Left ZIndex Style Border Borders BorderColor BorderStyle BorderWidth Color FontFamily '
    'FontSize FontStyle FontWeight TextDecoration TextAlign VerticalAlign PaddingLeft PaddingRight PaddingTop '
    'PaddingBottom BackgroundColor BackgroundImage NumeralLanguage Language Format RepeatOnNewPage '
    'KeepTogether KeepWithGroup PageBreak BreakLocation Disabled ResetPageNumber PageName InitialPageName '
    'Visibility ToggleItem InitialToggleState CanGrow CanShrink HideDuplicates Paragraphs Paragraph '
    'TextRuns TextRun Label ToolTip Bookmark DocumentMapLabel ActionInfo Actions Hyperlink ReportName '
    'Parameters Parameter MergeTransactions NoRowsMessage NoRows KeepTogether ConsumeContainerWhitespace '
    'TablixBody TablixColumns TablixColumn TablixRows TablixRow TablixCells TablixCell CellContents '
    'TablixColumnHierarchy TablixRowHierarchy TablixMembers TablixMember TablixHeader Corner TablixCorner '
    'TablixCornerRows TablixCornerRow TablixCornerCells TablixCornerCell TableColumns TableColumn TableRows '
    'TableRow TableCells TableCell Header Footer Details TableGroups TableGroup MatrixColumns MatrixColumn '
    'MatrixRows MatrixRow MatrixCells MatrixCell ColumnGroupings ColumnGrouping RowGroupings RowGrouping '
    'DynamicColumns StaticColumns StaticColumn DynamicRows StaticRows StaticRow ListGroups ListGroup '
    'EmbeddedImages EmbeddedImage ImageData MIMEType Source Sizing CodeModules Classes ClassName '
    'InstanceName AutoRefresh Description Author DataElementName DataElementOutput DataElementStyle '
    'DataTransform DataSchema MustUnderstand DeferVariableEvaluation Variables Variable UserSort '
    'SortExpressionScope SortTarget ChartData ChartSeriesCollection ChartSeries ChartDataPoints '
    'ChartDataPoint ChartDataPointValues X Y Size High Low Start End Type Subtype ChartAreas ChartArea '
    'ChartCategoryHierarchy ChartSeriesHierarchy ChartMembers ChartMember ChartAxis ChartCategoryAxes '
    'ChartValueAxes ChartTitles ChartTitle Caption ChartLegend ChartLegends AxisLabel').split())


def need(ok, code):
    if not ok: raise ValueError('rdl.' + code)


def module(name):
    need(name in ('powerbi_capture_files','report_source_capture'), 'module_rejected')
    path=Path(__file__).with_name(name+'.py')
    need(not any(p.is_symlink() for p in (path,*path.parents)), 'module_symlink')
    spec=importlib.util.spec_from_file_location('rdl_'+name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


F=module('powerbi_capture_files')
encoded=F.encoded

def sha(value): return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()
def text(value): return type(value) is str and 0 < len(value) <= 2048 and all(ord(c)>=32 for c in value)
def local(tag): return tag.rsplit('}',1)[-1]
def namespace(tag): return tag[1:].split('}',1)[0] if tag.startswith('{') else ''
def origin(value):
    try:
        u=urlsplit(value)
        return (u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
                and not u.path and not u.query and not u.fragment and (u.port is None or 0<u.port<65536))
    except (TypeError,ValueError): return False


def screen(raw):
    F.safe_text(raw)
    need(not re.search(rb'(?i)(?:pwd|password|user\s*id|uid)\s*=\s*[^;<>\s]+',raw), 'credential_connection_string')


class Tree:
    def __init__(self):
        self.tree=ET.TreeBuilder(insert_comments=True,insert_pis=True)
        self.depth=self.count=0; self.namespaces=[]
    def start(self,tag,attrs):
        self.depth+=1; self.count+=1
        need(self.depth<=MAX_DEPTH and self.count<=MAX_NODES,'xml_structure_limit')
        need(len(attrs)<=128 and all(len(k)<=2048 and len(v)<=16384 for k,v in attrs.items()),'xml_attributes_limit')
        return self.tree.start(tag,attrs)
    def end(self,tag): self.depth-=1; return self.tree.end(tag)
    def data(self,value): return self.tree.data(value)
    def comment(self,value): self.count+=1; need(self.count<=MAX_NODES,'xml_structure_limit'); return self.tree.comment(value)
    def pi(self,target,value): self.count+=1; need(self.count<=MAX_NODES,'xml_structure_limit'); return self.tree.pi(target,value)
    def start_ns(self,prefix,uri):
        need(len(self.namespaces)<MAX_NODES and len(uri)<=2048,'xml_namespace_limit')
        self.namespaces.append({'prefix':prefix or '', 'uri':uri})
    def end_ns(self,prefix): pass
    def doctype(self,*args): raise ValueError('rdl.xml_doctype_rejected')
    def close(self): return self.tree.close()


def inspect_xml(raw):
    need(type(raw) is bytes and 0<len(raw)<=MAX_XML_BYTES and b'\x00' not in raw,'xml_byte_or_encoding_limit')
    source=screen(raw)
    try: source=raw.decode('utf-8')
    except UnicodeError: raise ValueError('rdl.utf8_required') from None
    need(not re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b',source,re.I),'xml_doctype_rejected')
    declaration=re.search(r'<\?xml\s[^>]*encoding\s*=\s*[\'"]([^\'"]+)',source,re.I)
    need(not declaration or declaration[1].lower().replace('-','')=='utf8','utf8_required')
    tree=Tree()
    try:
        parser=ET.XMLParser(target=tree); parser.feed(raw); root=parser.close()
    except (ET.ParseError,RecursionError,OverflowError): raise ValueError('rdl.invalid_xml') from None
    ns=namespace(root.tag)
    need(local(root.tag)=='Report' and ns in NAMESPACES,'namespace_or_report_root_unqualified')
    records={}; comments=[]; pending=[(root,'/',None)]
    while pending:
        node,path,parent=pending.pop(); children=[c for c in node if type(c.tag) is str]
        for name,val in [*node.attrib.items(),(local(node.tag),(node.text or '').strip())]:
            secret=re.sub('[^a-z]','',local(name).lower())
            need(secret not in {'password','pwd','authorization','accesstoken','refreshtoken','clientsecret','credentials','apikey'} or not val,'credential_xml')
        records[path]={'locator':path,'parent_locator':parent,'qname':node.tag,'namespace':namespace(node.tag),
            'local_name':local(node.tag),'attributes':dict(node.attrib),'text':node.text,'tail':node.tail,
            'children':[path.rstrip('/')+'/'+str(i) for i in range(len(children))]}
        comments.extend({'parent_locator':path,'kind':'comment' if c.tag is ET.Comment else 'processing_instruction','text':c.text,'tail':c.tail}
                        for c in node if type(c.tag) is not str)
        pending.extend((c,path.rstrip('/')+'/'+str(i),path) for i,c in reversed(list(enumerate(children))))
    return {'namespace':ns,'namespaces':tree.namespaces,'records':records,'comments_and_processing_instructions':comments,
            'xml_sha256':sha(raw),'schema_validation':'not_performed'}


def kind(record,ns):
    if record['namespace']!=ns: return 'unknown'
    if (record.get('text') or '').lstrip().startswith('='): return 'expression'
    return TAGS.get(record['local_name'],'unknown')


def _validate(value):
    try: raw=encoded(value)
    except (TypeError,ValueError,RecursionError): raise ValueError('rdl.invalid_snapshot') from None
    need(len(raw)<=8*1024*1024,'snapshot_byte_limit'); F.decode(raw); F.secret_check(value); screen(raw)
    need(type(value) is dict and set(value)=={'schema_version','identity','report_xml','inventory','gaps'} and value['schema_version']==SCHEMA,'snapshot_contract')
    identity=value['identity']
    need(type(identity) is dict and set(identity)=={'source_platform','source_origin','product_version','principal_ref','report_id','workspace_id','content_path','reference'},'identity_fields')
    need(identity['source_platform'] in ('ssrs','powerbi_paginated') and all(text(identity[k]) for k in ('product_version','principal_ref','reference')),'identity_values')
    need(all(identity[k] is None or text(identity[k]) for k in ('source_origin','report_id','workspace_id','content_path')),'identity_optional')
    need(identity['source_origin'] is None or origin(identity['source_origin']),'source_origin')
    need(identity['source_platform']!='ssrs' or identity['workspace_id'] is None,'ssrs_workspace_not_applicable')
    definition=value['report_xml']
    need(type(definition) is dict and set(definition)=={'encoding','content','bytes','sha256','reference'} and definition['encoding']=='utf-8'
         and type(definition['content']) is str and type(definition['bytes']) is int and text(definition['reference']),'definition_fields')
    try: xml=definition['content'].encode('utf-8')
    except UnicodeError: raise ValueError('rdl.utf8_required') from None
    need(len(xml)==definition['bytes'] and sha(xml)==definition['sha256'],'definition_pin_mismatch')
    parsed=inspect_xml(xml); records=parsed['records']; inv=value['inventory']
    need(type(inv) is dict and set(inv)=={'reference','completeness','items'} and text(inv['reference']) and inv['completeness'] in ('partial','selected_scope_declared')
         and type(inv['items']) is list and 0<len(inv['items'])<=MAX_ITEMS,'inventory_contract')
    indexed={}
    for row in inv['items']:
        need(type(row) is dict and set(row)=={'key','kind','parent_key','native_id','locator','disposition','reference','configuration'},'inventory_item_fields')
        need(text(row['key']) and row['key'] not in indexed and row['kind'] in KINDS and text(row['reference'])
             and row['disposition'] in ('include','manual_review','unsupported','unavailable','out_of_scope')
             and type(row['configuration']) is dict and all(row[k] is None or text(row[k]) for k in ('parent_key','native_id','locator')),'inventory_item')
        if row['locator'] is not None:
            need(row['locator'] in records,'inventory_locator_missing')
            actual=kind(records[row['locator']],parsed['namespace'])
            need(row['kind'] in (actual,'unknown') or (row['kind']=='placement' and actual in ('visual','content','layout','resource','subreport')),'inventory_kind_mismatch')
            native_name=records[row['locator']]['attributes'].get('Name')
            need(row['native_id'] is None or row['native_id']==native_name or (row['kind']=='report' and row['native_id']==identity['report_id']),'inventory_native_identity_mismatch')
        config=row['configuration']
        need('private' not in config or type(config['private']) is bool,'private_flag')
        need('access' not in config or config['access'] in ('allowed','denied','unavailable','unknown'),'access_flag')
        indexed[row['key']]=row
    for row in indexed.values():
        seen={row['key']}; current=row
        while current['parent_key'] is not None:
            key=current['parent_key']; need(key in indexed and key not in seen,'inventory_parent_or_cycle'); seen.add(key); current=indexed[key]
    need(type(value['gaps']) is list and len(value['gaps'])<=1000 and all(text(x) for x in value['gaps']),'gaps')
    return parsed,indexed


def validate_snapshot(value): _validate(value); return value


def make_snapshot(raw,identity,inventory,reference,gaps=None):
    inspect_xml(raw)
    value={'schema_version':SCHEMA,'identity':copy.deepcopy(identity),
        'report_xml':{'encoding':'utf-8','content':raw.decode('utf-8'),'bytes':len(raw),'sha256':sha(raw),'reference':reference},
        'inventory':copy.deepcopy(inventory),'gaps':copy.deepcopy([] if gaps is None else gaps)}
    return validate_snapshot(value)


def _restricted(row,indexed):
    while row:
        if row['disposition'] in ('unavailable','out_of_scope') or row['configuration'].get('access') in ('denied','unavailable'): return True
        if row['configuration'].get('private') is True and not text(row['configuration'].get('selection_reference')): return True
        row=indexed.get(row['parent_key'])
    return False


def _bindings(parsed):
    records=parsed['records']; ns=parsed['namespace']; datasets={}; sources={}
    for path,r in records.items():
        name=r['attributes'].get('Name')
        if r['namespace']==ns and text(name):
            if r['local_name']=='DataSet': datasets.setdefault(name,[]).append(path)
            if r['local_name']=='DataSource': sources.setdefault(name,[]).append(path)
    return datasets,sources


def _dataset(path,parsed,datasets):
    r=parsed['records'].get(path); ns=parsed['namespace']
    if not r or r['namespace']!=ns: return None
    if r['local_name']=='DataSet': return path
    names=[parsed['records'][p]['text'] for p in r['children'] if parsed['records'][p]['namespace']==ns and parsed['records'][p]['local_name']=='DataSetName']
    return datasets[names[0]][0] if len(names)==1 and len(datasets.get(names[0],[]))==1 else None


def _scope(parsed,indexed,key):
    need(key in indexed,'object_scope_missing'); row=indexed[key]
    datasets,_=_bindings(parsed); dataset=_dataset(row['locator'],parsed,datasets)
    matching=[r for r in indexed.values() if r['locator']==dataset and r['kind']=='dataset'] if dataset else []
    restricted=_restricted(row,indexed) or any(_restricted(other,indexed) for other in indexed.values()
        if row['locator'] is not None and other['locator'] is not None and
        (other['locator']=='/' or row['locator']==other['locator'] or row['locator'].startswith(other['locator']+'/')))
    native_query=bool(dataset and any(r['namespace']==parsed['namespace'] and (r.get('text') or '').strip()
        and r['local_name'] in ('CommandText','SharedDataSetReference') and p.startswith(dataset+'/')
        for p,r in parsed['records'].items()))
    eligible=(native_query and row['disposition']=='include' and not restricted and dataset is not None and len(matching)==1
              and matching[0]['disposition']=='include' and not _restricted(matching[0],indexed)
              and row['kind'] in ('dataset','visual','placement'))
    return {'item':row,'restricted':restricted,'query_visual':eligible,'dataset_locator':dataset,
            'requires_source_review':not eligible if row['kind'] in ('dataset','visual','placement') else row['locator'] is None}


def scope_item(value,key):
    parsed,indexed=_validate(value); return _scope(parsed,indexed,key)


def translate(payload,raw,helpers):
    parsed,indexed=_validate(payload); need(F.decode(raw)==payload,'raw_payload_mismatch')
    platform=payload['identity']['source_platform']; fingerprint=sha(payload); xml_hash=payload['report_xml']['sha256']
    result=helpers['base'](payload,raw,platform,'supplied_rdl_report_snapshot')
    result['source'].update(definition_fingerprint=fingerprint,definition_sha256=xml_hash,source_identity=copy.deepcopy(payload['identity']))
    result['rdl_xml']=parsed
    result['migration_context']={'route':None,'route_reference':None,'target_surface':'report','build_authority':False,
        'target_write_authority':False,'native_validation':'not_run','business_acceptance':'not_assessed'}
    records=parsed['records']; ns=parsed['namespace']; datasets,sources=_bindings(parsed)
    represented={r['locator'] for r in indexed.values() if r['locator'] is not None}
    def emit(row,path,declared):
        rec=records.get(path); scope=_scope(parsed,indexed,row['key']) if declared else None
        inherited=any(_restricted(r,indexed) for r in indexed.values() if path is not None and r['locator'] is not None
                      and (r['locator']=='/' or path==r['locator'] or path.startswith(r['locator']+'/')))
        restricted=inherited or bool(scope and scope['restricted']); dataset=scope['dataset_locator'] if scope else None
        identity={'source_platform':platform,'object_key':row['key'] if declared else None,'native_kind':row['kind'],
            'native_id':row['native_id'],'xml_locator':path,'xml_name':rec['attributes'].get('Name') if rec else None,
            'definition_fingerprint':fingerprint,'definition_sha256':xml_hash,'report_id':payload['identity']['report_id'],
            'workspace_id':payload['identity']['workspace_id'],'dataset_locator':dataset,
            'query_visual':bool(scope and scope['query_visual'] and not restricted), 'restricted_private_scope':restricted,
            'declared_disposition':row['disposition'],'requires_source_review':not declared or not rec or bool(scope and scope['requires_source_review'])}
        facets={k:{'status':'needs_review','value':{'xml_locator':path,'definition_sha256':xml_hash,'node':copy.deepcopy(rec)}} for k in helpers['FACETS']}
        source={'name':identity['xml_name'] or row['key'] or path,'inventory':copy.deepcopy(row),'xml_node':copy.deepcopy(rec)}
        helpers['add_asset'](result,NORMAL.get(row['kind'],row['kind']) if declared else 'unknown',source,
            '/inventory/'+row['key'] if declared else '/xml'+path,row['key'] if declared else None,fingerprint,facets,
            id_kind='independent_inventory_key' if declared else 'xml_occurrence',source_identity=identity)
        if restricted: helpers['gap'](result,'rdl.restricted_source_scope',path or '')
        if declared and not rec: helpers['gap'](result,'rdl.expected_object_without_source','/inventory/'+row['key'])
        if declared and row['kind'] in ('dataset','visual','placement') and not identity['query_visual']:
            helpers['gap'](result,'rdl.query_binding_or_dataset_scope_unqualified',path or '')
    for row in indexed.values(): emit(row,row['locator'],True)
    additional=0
    for path,rec in records.items():
        k=kind(rec,ns)
        if path not in represented and (k!='unknown' or rec['namespace']!=ns or rec['local_name'] not in STRUCTURAL):
            additional+=1; emit({'key':None,'kind':k,'native_id':None,'disposition':'manual_review'},path,False)
            helpers['gap'](result,'rdl.native_occurrence_not_independently_dispositioned',path)
        label=rec['local_name']; txt=rec['text'] or ''
        if k in ('expression','code','subreport','action'):
            helpers['gap'](result,'rdl.'+k+'_preserved_not_executed',path)
        if rec['namespace']!=ns: helpers['gap'](result,'rdl.extension_namespace_unqualified',path)
        if label in ('DataSourceName','DataSetName') and rec['namespace']==ns:
            candidates=(sources if label=='DataSourceName' else datasets).get(txt,[])
            result['dependencies'].append({'source_locator':path,'reference_kind':label,'reference':txt,'target_locators':candidates,
                'status':'resolved_xml_reference' if len(candidates)==1 else 'unresolved'})
            if len(candidates)!=1: helpers['gap'](result,'rdl.named_dependency_missing_or_ambiguous',path)
        if label in ('DataSourceReference','SharedDataSetReference','ReportName','CodeModule','ConnectString','DataTransform','DataSchema'):
            result['dependencies'].append({'source_locator':path,'reference_kind':label,'reference':txt,'status':'external_dependency_not_acquired'})
            helpers['gap'](result,'rdl.external_dependency_unqualified',path)
        if label in ('Hyperlink','ImageData') or '://' in txt or any('://' in v or local(k) in ('href','src','schemaLocation') for k,v in rec['attributes'].items()):
            helpers['gap'](result,'rdl.resource_not_fetched_or_decoded',path)
    result['rdl_coverage']={'independent_objects':len(indexed),'xml_elements':len(records),'additional_occurrence_obligations':additional,
        'declared_scope':payload['inventory']['completeness'],'export_completeness':'not_established'}
    for g in payload['gaps']: helpers['gap'](result,'rdl.supplied_gap',detail=g)
    for g in ('no_schema_or_expression_compilation','no_connected_or_rendered_qualification','source_identity_not_authenticated','no_DMA_producer',
              'unqualified_source_results','external_datasets_resources_and_security_require_review'):
        helpers['gap'](result,'rdl.'+g)
    return result


parse_snapshot=translate

def validate_capture(value): return module('report_source_capture').validate_envelope(value)
def verify_capture_files(value,root): return module('report_source_capture').verify_capture_files(value,root)
def parse_capture(payload,raw,helpers): return module('report_source_capture').parse_capture(payload,raw,helpers)
def case_binding(asset,case,capture): return module('report_source_capture').case_binding(asset,case,capture)
def comparison_gaps(*args,**kwargs): return module('report_source_capture').comparison_gaps(*args,**kwargs)
def normalize_results(*args,**kwargs): return module('report_source_capture').normalize_results(*args,**kwargs)
