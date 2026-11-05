"""Neutral Topic selection, stage and native query guard regressions. No tenant operations."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name,ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


P = module('test_topic_project','skills/omni-artifact-accelerator/scripts/analyst_project.py')
D = P.routing_helper('dma_topics')
G = module('topic_lifecycle','tests/stage_gate_fixture.py')


class Fixture:
    def __init__(self, root):
        self.root = root
        P.init(root,'Inspection workbook','net-new','app')
        topics = ['instrument_readings','instrument_samples']
        self.topic = topics[0]
        self.ctx = {'base_url':'https://synthetic.omniapp.co','model_id':'shared',
                    'branch_id':'branch','workbook_model_id':None,'principal_id':'fixture-user'}
        self.review = {'schema_version':1,'kind':'omni_semantic_handoff','version':'omni-handoff-v1',
            'pins':{'source_fingerprint':'a'*64,'context_sha256':'b'*64,'model_candidate_sha256':'c'*64,
                    'model_context_sha256':'d'*64,'target':{'warehouse':'test'}},
            'topics':[{'id':t,'base_view':t+'_base','scope':{'views':[t+'_base','lab_group']}} for t in topics],
            'dictionary':[{'id':f,'topic':t,'selected_for_query':True,'kind':'dimension' if f == 'lab_group.name' else 'measure'}
                          for t in topics for f in (t+'_base.volume','lab_group.name')],
            'metrics':[],'dependencies':[],'decisions':[],'unknowns':[]}
        self.review['handoff_sha256'] = P.digest(P.canonical(self.review))
        rev = self.put('inputs/semantic-review.json',self.review)
        P.import_dma(root, root/rev['path'])
        self.ref = self.put('evidence/selection.json',{'kind':'dma_topic_choice','role':'user','reference':'offline-brief',
            'topics':[self.topic],'surfaces':['app'],'request_text':'Use the instrument readings Topic.',
            'destination':{k:self.ctx[k] for k in ('base_url','model_id','branch_id')}})
        self.query = {'fields':[self.topic+'_base.volume','lab_group.name'], 'table':self.topic+'_base','limit':20,
                      'join_paths_from_topic_name':self.topic}
        self.tile = {'type':'query','isSql':False,'topicName':self.topic,'name':'Volume','query':self.query}
        self.views = {t:self.response(t) for t in topics}
        self.obs = {'kind':'dma_topic_observation','schema_version':1,'context':self.ctx,
            'observed_at':'2025-01-01T00:00:00Z','review_sha256':rev['sha256'],
            'identity':self.put('evidence/whoami.json',{'keyScope':'user','user':{'membershipId':'fixture-user'},
                                                      'rolesByModel':{'shared':{'role':'QUERIER'}}}),
            'models':self.put('evidence/models.json',{'shared':{'id':'shared','modelKind':'SHARED','connectionId':'source-1'},
                                'branch':{'id':'branch','modelKind':'BRANCH','baseModelId':'shared'}}),
            'topics':{},'trials':{}}
        self.expected = self.put('evidence/expected.json',{'volume':12})
        for t in topics:
            self.obs['topics'][t] = self.put('evidence/topic-'+t+'.json',{'context':self.ctx,'effective_model_id':'branch',
                'topic_name':t,'response':self.views[t]})
            query = {'fields':[t+'_base.volume'],'table':t+'_base','limit':1}
            trial = {'context':self.ctx,'effective_model_id':'branch','topic':t,'query_ref':'supplied-trial-'+t}
            result = self.put('evidence/result-'+t+'.json', {**trial, 'kind':'omni_topic_trial_result',
                'status':'complete','query_sha256':P.digest(P.canonical(query)), 'columns':query['fields'],
                'rows':[{query['fields'][0]:12}]})
            self.obs['trials'][t] = self.put('evidence/trial-'+t+'.json',{**trial,'query':query,'result':result,'status':'succeeded'})
        self.obs['topics'].pop(topics[1]); self.obs['trials'].pop(topics[1])
        self.selection = {'kind':'dma_topic_selection','schema_version':1,'topics':[self.topic],'selection_evidence':self.ref,
            'context':self.ctx,'observation':self.put('evidence/observation.json',self.obs)}
        self.put('contracts/selection.json',self.selection)
        self.access = D.prepare(root,P,'contracts/selection.json','contracts/access.json')
        self.row = {'consumer_id':'volume-panel','surface':'app','document_id':'instrument-report','query_key':'1',
            'topic':self.topic,'question':'How many readings?','grain':'one lab group','population':'eligible readings',
            'access_case':'intended user with area restrictions','expectation_text':'12 for the permitted group',
            'expectation':self.expected,'disposition':'new','tile':self.tile}
        self.gap = {**self.row,'consumer_id':'calibration-panel','question':'How many were calibrated?',
            'fields':['instrument_readings_base.calibrated_count'],'disposition':'request','reason':'governed measure missing',
            'query_key':None,'tile':None}
        self.plan = {'kind':'dma_topic_consumer_plan','schema_version':1,'access':self.access,
                     'consumers':[self.row,self.gap],'controls':[]}
        self.put('contracts/plan.json',self.plan)
        self.analysis = D.prepare(root,P,'contracts/plan.json','contracts/analysis.json',True)
        self.cycle = G.Lifecycle(root,P)
        original = self.cycle.evidence
        paths = {'access-data':self.access['path'], 'access-user_access':self.selection['observation']['path'],
                 'analysis-queries':self.analysis['path']}
        self.cycle.evidence = lambda name, content=None: paths.get(name) or original(name,content)

    def response(self, t):
        return {'success':True,'topic':{'name':t,'base_view_name':t+'_base','always_where_filters':{'area':t},
            'views':[{'name':t+'_base','measures':[{'fully_qualified_name':t+'_base.volume'}]},
                     {'name':'lab_group','dimensions':[{'fully_qualified_name':'lab_group.name'}]}]}}

    def put(self,path,value):
        dest = self.root/path
        dest.write_text(json.dumps(value,sort_keys=True))
        return D.pin(self.root,path,P)

    def candidate(self, tile=None, **kwargs):
        context = kwargs.pop('context',self.ctx)
        return D.guard(self.root,P,surface='app',document_id='instrument-report',context=context,
                       presentations={'data':{'1':self.tile if tile is None else tile},'order':['1']},**kwargs)


class TopicPolicy(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.f = Fixture(Path(temp.name).resolve()/'project')

    def test_real_stages_candidate_against_selected_topic_and_gap(self):
        f = self.f
        f.cycle.through('analysis')
        proof = f.candidate()
        packet = P.packet_data(f.root, 'bi-engineer', [f.expected['path']])
        self.assertEqual(packet['dma_topic_context']['evidence']['analysis'],f.analysis)
        self.assertEqual(packet['dma_topic_context']['blocked'],['calibration-panel'])
        self.assertNotIn('dictionary',packet['dma_topic_context'])
        self.assertEqual(proof['access_sha256'], f.access['sha256'])
        result = D.read(f.root,f.analysis['path'],P)[0]
        request = result['backend_request']
        D.peer('cowork').check_spec(request)
        self.assertEqual([r['id'] for r in request['requirements']], ['calibration-panel'])
        gap = D.prepare_gap(f.root,P,f.analysis['path'],'contracts/gap.json')
        self.assertEqual(gap['status'],'request_prepared')
        self.assertEqual(D.prepare_gap(f.root,P,f.analysis['path'],'contracts/gap.json')['status'],'request_reused')
        for changed in [
            {**f.tile,'topicName':'instrument_samples'},
            {**f.tile,'query':{**f.query,'table':'instrument_samples_base'}},
            {**f.tile,'query':{**f.query,'fields':['instrument_samples_base.volume']}},
            {**f.tile,'queryType':'SQL'}, {**f.tile,'isSql':True},
        ]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                f.candidate(changed)
        with self.assertRaisesRegex(ValueError,'no_supported_queries'):
            D.guard(f.root,P,surface='app',document_id='unrelated',context=f.ctx,
                    presentations={'data':{'1':f.tile},'order':['1']})
        with self.assertRaisesRegex(ValueError,'native_context_changed'):
            f.candidate(context={**f.ctx,'branch_id':None})
        with self.assertRaisesRegex(ValueError,'effective_readback'):
            f.candidate(readback=True)
        wb = 'new-workbook'
        snapshot = {'identity':{'keyScope':'user','user':{'membershipId':'fixture-user'},'rolesByModel':{'shared':{}}},'target':{**f.ctx,'document_id':'instrument-report'},
                    'draft_context':{'workbookModelId':wb},'models':{**D.evidence(f.root,f.obs['models'],P),wb:{'modelKind':'WORKBOOK','id':wb,'baseModelId':'branch'}},'topics':{f.topic:f.views[f.topic]}}
        native = {**f.ctx,'workbook_model_id':wb}
        html = '<section id="lab-volume"></section><script>display("lab-volume","1")</script>'
        (f.root/'deliverables/app.html').write_text(html)
        f.put('contracts/panels.json',{'kind':'dma_topic_panels','html_path':'deliverables/app.html',
            'document_id':'instrument-report','panels':[{'element_id':'lab-volume','consumer_id':'volume-panel',
            'query_key':'1','script_fragment':'display("lab-volume","1")'}]})
        D.prepare_panels(f.root,P,'contracts/panels.json')
        self.assertEqual(f.candidate(readback=True,context=native,snapshot=snapshot,app_html=html)['queries_sha256'],proof['queries_sha256'])
        with self.assertRaisesRegex(ValueError,'panel_mapping_required'):
            f.candidate(readback=True,context=native,snapshot=snapshot,app_html=html.replace('"1"', '"2"'))
        drift = copy.deepcopy(snapshot)
        drift['topics'][f.topic]['topic']['always_where_filters'] = {}
        with self.assertRaisesRegex(ValueError,'verify_current_workbook'):
            f.candidate(readback=True,context=native,app_html=html)
        with self.assertRaisesRegex(ValueError,'live_topic_definition_changed'):
            f.candidate(readback=True,context=native,snapshot=drift,app_html=html)

    def test_stage_freshness_and_unsupported_predecessors(self):
        f = self.f
        f.cycle.stage('access')
        f.cycle.evidence = lambda name, content=None: f.expected['path']
        with self.assertRaises((KeyError,ValueError)):
            f.cycle.stage('analysis')
        pin = f.obs['topics'][f.topic]
        f.put(pin['path'],{'substitution':'same totals'})
        self.assertEqual(P.stage_status(f.root)['next_stage'],'access')

    def test_pending_ambiguity_stays_usable_only_for_deferred_scope(self):
        f = self.f
        f.put('contracts/ambiguous.json',{**f.selection,'topics':[], 'observation':None})
        receipt = D.prepare(f.root,P,'contracts/ambiguous.json','contracts/pending.json')
        self.assertTrue(D.read(f.root,receipt['path'],P)[0]['needs_selection'])
        f.put('contracts/pending-plan.json',{**f.plan,'access':receipt})
        with self.assertRaisesRegex(ValueError,'observed_topic_required'):
            D.prepare(f.root,P,'contracts/pending-plan.json','contracts/blocked.json',True)
        f.put('contracts/offline.json',{**f.selection,'observation':None})
        pending = D.prepare(f.root,P,'contracts/offline.json','contracts/offline-access.json')
        f.put('contracts/gap-only.json',{**f.plan,'access':pending,'consumers':[f.gap]})
        offline = D.prepare(f.root,P,'contracts/gap-only.json','contracts/scope.json',True)
        self.assertIsNotNone(D.read(f.root,offline['path'],P)[0]['backend_request'])

    def test_wrong_selection_kind_and_removed_continuation_are_rejected(self):
        f = self.f
        swapped = {**f.selection,'topics':['instrument_samples'],'observation':None}
        f.put('contracts/swap.json',swapped)
        with self.assertRaisesRegex(ValueError,'explicit_topic_choice_mismatch'):
            D.prepare(f.root,P,'contracts/swap.json','contracts/rejected.json')
        alternate = copy.deepcopy(f.review)
        next(d for d in alternate['dictionary'] if d['topic']==f.topic and d['id']=='lab_group.name')['kind']='measure'
        alternate['handoff_sha256'] = P.digest(P.canonical({k:v for k,v in alternate.items() if k != 'handoff_sha256'}))
        definitions = D.peer('standalone').semantic_definitions({'topics':{f.topic:f.views[f.topic]}},
            [{'topic':f.topic,'field_ids':['lab_group.name'],'query_key':'1','query':f.query}])
        with self.assertRaisesRegex(ValueError,'candidate_native_field_kind_changed'):
            D.check_kinds(alternate,f.topic,definitions[0]['fields'])
        project = P.load_project(f.root)[1]
        project['dma_continuation_selection'] = {'target_surfaces':['app']}
        P.write_json(f.root/'project.json',project,replace=True)
        with self.assertRaisesRegex(ValueError,'continuation identity missing'):
            D.current(f.root,project,P)

    def test_reuse_key_exception_and_controls_are_scoped(self):
        f = self.f
        alternate = 'instrument_samples'
        restored = {}
        for key,prefix in [('topics','topic'),('trials','trial')]:
            restored[key] = {**f.obs[key], alternate: D.pin(f.root,'evidence/'+prefix+'-'+alternate+'.json',P)}
        observation = f.put('evidence/alternate.json',{**f.obs,**restored})
        f.put('contracts/allow.json',{**f.selection,'observation':observation,'alternative_topics':[alternate]})
        access = D.prepare(f.root,P,'contracts/allow.json','contracts/allow-access.json')
        tile = {**f.tile,'topicName':alternate,'query':{'fields':[alternate+'_base.volume'],'table':alternate+'_base','limit':5,
                'join_paths_from_topic_name':alternate}}
        exception = {**f.row,'topic':alternate,'disposition':'exception','tile':tile,'query_key':'2','consumer_id':'diagnostic'}
        decision = {'kind':'dma_topic_exception','topic':alternate,'document_id':'instrument-report','surface':'app','query_key':'2',
                    'consumer_id':'diagnostic','reason':'separately selected scope','user_decision':f.ref,'access':access,
                    'query_sha256':P.digest(P.canonical(tile['query']))}
        decision['user_decision'] = f.put('evidence/user-choice.json',{
            **{k:decision[k] for k in ('consumer_id','surface','document_id','query_key','topic','access','query_sha256')},
            'role':'user','reference':'test-conversation','response_text':'Use the alternate source for this diagnostic only.'})
        exception['decision'] = f.put('evidence/exception.json',decision)
        saved = f.put('evidence/saved.json',{'context':f.ctx,'document_id':'instrument-report','query_key':'1','tile':f.tile})
        keep = {**f.row,'disposition':'reuse','saved_query':saved}
        control = {'control_key':'region','query_keys':['1'],'surface':'app','document_id':'instrument-report',
                   'config':{'component_id':'area','topic':f.topic,'query_keys':['1'],'field_ids':['lab_group.name']},
                   'field_bindings':[{'field_id':'lab_group.name','topic':f.topic,'pointer':'/field_ids/0'}]}
        plan = {**f.plan,'access':access,'consumers':[keep,exception],'controls':[control]}
        f.put('contracts/scoped.json',plan)
        D.prepare(f.root,P,'contracts/scoped.json','contracts/ok.json',True)
        for item in [dict(exception,query_key='3'),dict(keep,document_id='another')]:
            f.put('contracts/scoped.json',{**plan,'consumers':[item]})
            with self.assertRaises(ValueError):
                D.prepare(f.root,P,'contracts/scoped.json','contracts/rejected.json',True)

    def test_query_origin_for_new_and_historical_saved_tabs(self):
        f = self.f
        query = {k:v for k,v in f.query.items() if k != 'join_paths_from_topic_name'}
        tile = {**f.tile,'query':query}
        row = {**f.row,'tile':tile}
        def prepare(consumer):
            f.put('contracts/origin.json',{**f.plan,'consumers':[consumer]})
            return D.prepare(f.root,P,'contracts/origin.json','contracts/origin-result.json',True)
        with self.assertRaisesRegex(ValueError,'explicit_query_topic_required'):
            prepare(row)
        saved = {'context':f.ctx,'document_id':row['document_id'],'query_key':row['query_key'],'tile':tile,'query_ref':'legacy-tab-run'}
        def reuse(data):
            return prepare({**row,'disposition':'reuse','saved_query':f.put('evidence/legacy.json',data)})
        with self.assertRaisesRegex(ValueError,'saved_topic_execution_required'):
            reuse(saved)
        result = {'kind':'omni_topic_trial_result','status':'complete','context':f.ctx,'effective_model_id':'branch',
                  'topic':f.topic,'document_id':row['document_id'],'query_key':row['query_key'],'query_ref':saved['query_ref'],
                  'query_sha256':P.digest(P.canonical(query)),'columns':query['fields'],
                  'rows':[{'lab_group.name':'East',f.topic+'_base.volume':12}]}
        for key, value in [('topic','instrument_samples'),('query_key','another'),('query_sha256','a'*64)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'scoped_trial_result_changed'):
                reuse({**saved,'result':f.put('evidence/legacy-result.json',{**result,key:value})})
        self.assertIn('sha256',reuse({**saved,'result':f.put('evidence/legacy-result.json',result)}))

    def test_new_workbook_checks_version_on_originally_observed_model(self):
        f = self.f
        models = D.evidence(f.root,f.obs['models'],P)
        models['branch']['modelVersionId'] = 'selected-revision'
        models['workbook'] = {'id':'workbook','modelKind':'WORKBOOK','baseModelId':'branch','modelVersionId':'new-revision'}
        ctx = {**f.ctx,'workbook_model_id':'workbook','model_version_id':'selected-revision'}
        D.check_models(models,ctx,version_model_id='branch')
        models['branch']['modelVersionId'] = 'another-revision'
        with self.assertRaisesRegex(ValueError,'model_version_not_observed'):
            D.check_models(models,ctx,version_model_id='branch')

if __name__ == '__main__':
    unittest.main()
