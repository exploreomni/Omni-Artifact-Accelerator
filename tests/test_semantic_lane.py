"""Exercise the ordinary project commands and the saved App/dashboard query guard."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


P = module('lane_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
V = module('lane_access_cases', 'tests/test_semantic_verification.py')
F = module('lane_dma_cases', 'tests/test_dma_topic_policy.py')
S = P.routing_helper('semantic_lane')
D = P.routing_helper('dma_topics')


class SemanticLane(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        self.setup_project()

    def setup_project(self, *, surface='dashboard', branch='dev'):
        P.init(self.root, 'Operations review', 'net-new', surface, modeling_lane='omni-only')
        self.context = {'base_url':'https://example.omni.test','model_id':'model','branch_id':branch,
                        'workbook_model_id':None,'principal_id':'analyst'}
        self.topic = 'orders'
        self.models = {'model':{'id':'model','connectionId':'conn','modelKind':'SHARED'},
                       'dev':{'id':'dev','baseModelId':'model','connectionId':'conn','modelKind':'BRANCH'}}
        self.who = {'keyScope':'user','user':{'membershipId':'analyst'},
                    'rolesByModel':{'model':{'permissions':['USE_IDE','UPDATE']}}}
        self.inventory = {'kind':'omni_modeling_inventory', 'context':self.context, 'connection_id':'conn',
            'identity':self.put('evidence/model-user.json',self.who),'models':self.put('evidence/models.json',self.models),
            'model_visibility':'complete','complete':True,'physical_status':'ready','topic_names':[],'suitability':{}}
        self.baseline = {'model_id':'model','branch_id':branch,'evidence_ref':'readback-1','topic_names':[],
            'views':{'orders':{'physical_binding':'ANALYTICS.ORDERS','dimensions':['id','total'],'measures':[]}},
            'user_attributes':[],'access_grants':[]}
        self.inventory['baseline'] = self.put('evidence/baseline.json', self.baseline)
        self.definition = {'schema_version':1,'topic':{'name':'orders','base_view':'orders','label':'Orders','fields':['orders.n']},
            'policy':{'review_ref':'policy-1','access_filters':[],'required_access_grants':[]},
            'measures':[{'view':'orders','name':'n','aggregate_type':'count','field':'orders.id','review_ref':'definition-1'}]}
        self.response = {'success':True,'topic':{'name':'orders','base_view_name':'orders',
            'views':[{'name':'orders','measures':[{'fully_qualified_name':'orders.n','aggregate_type':'count'}]}]}}
        self.query = {'fields':['orders.n'],'table':'orders','limit':2,'join_paths_from_topic_name':'orders'}

    def put(self, path, obj):
        P.write_json(self.root / path, obj, replace=(self.root / path).exists())
        return D.pin(self.root, path, P)

    def load(self, pin):
        return D.evidence(self.root, pin, P)

    def run_request(self, op, obj, *, key=None):
        key = key or op
        path = 'inputs/' + key + '.json'
        self.put(path, obj)
        output = None if op in ('route','delivery','panels') else 'contracts/' + key + '-receipt.json'
        return S.execute(self.root, P, op, path, output)

    def route(self, decision=None, *, previous=None, key='route-input', source_inventory=None):
        inventory = self.put('evidence/'+key+'-inventory.json', self.inventory)
        req = {'kind':'omni_modeling_discovery','schema_version':1,'context':self.context,
               'topic_name':self.topic,'inventory':inventory,'previous':previous}
        if source_inventory is not None:
            req['source_inventory'] = source_inventory
        if decision:
            req['choice'] = self.put('evidence/'+key+'-choice.json',{'role':'user','reference':'chat/choice','response_text':'Prepare this Topic',
                                            'context':self.context,'topic_name':self.topic,'action':decision})
        return self.run_request('route',req,key=key)

    def candidate(self, route):
        definition = self.put('contracts/definition.json',self.definition)
        return self.run_request('candidate',{'route':route,'definition':definition})

    def test_route_replay_pending_and_ownership(self):
        offer = self.route()
        self.assertEqual(self.load(offer)['route'],'offer_create_topic')
        self.assertEqual(self.route(),offer)
        with self.assertRaisesRegex(ValueError,'authoring_required'):
            self.candidate(offer)
        self.inventory['model_visibility'] = 'limited'
        pending = self.route('create_topic',previous=offer,key='unknown')
        self.assertEqual(self.load(pending)['route'],'discovery_pending')
        self.inventory['model_visibility'] = 'complete'
        accepted = self.route('create_topic',previous=pending,key='chosen')
        candidate = self.load(self.candidate(accepted))
        self.assertEqual(candidate['candidate']['status'],'candidate',candidate)
        self.assertEqual(set(candidate['candidate']['files']),{'orders.topic'})
        with self.assertRaisesRegex(ValueError,'current_route_required'):
            self.candidate(offer)
        self.assertFalse(candidate['authorizes_target_write'])

    def test_missing_physical_routes_upstream_and_ambiguity_stays_pending(self):
        self.inventory['physical_status'] = 'missing'
        self.assertEqual(self.load(self.route())['route'],'upstream_required')

    def test_selected_mcp_tool_and_cli_reuse_the_same_receipt(self):
        expected = self.route()
        host = module('semantic_test_mcp', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
        bridge = host.Bridge(self.root, tool_profile='selected', enabled_tools=['semantic_model_prepare'])
        actual = bridge.call('semantic_model_prepare', {'operation':'route','request':'inputs/route-input.json'})
        self.assertEqual(actual, expected)

    def test_translation_requires_a_disposition_for_every_scoped_source_item(self):
        translator = module('semantic_source_test', 'skills/omni-artifact-translator/scripts/translate_artifact.py')
        export = {'schema_version':1, 'kind':'omni_analyst_inventory_input', 'platform':'looker', 'assets':[
            {'kind':'definition','source_id':'order_count','scope':'model','evidence_refs':['model-metric'],
             'facets':{'query':{'status':'observed','value':{'formula':'COUNT(id)'}}}},
            {'kind':'filter','source_id':None,'evidence_refs':['unknown-filter'],'facets':{}}]}
        inventory = translator.translate(json.dumps(export).encode(), 'normalized-inventory')
        inventory_pin = self.put('inputs/translated.json', inventory)
        route = self.route('translate_semantics', source_inventory=inventory_pin)
        self.assertEqual(self.load(route)['route'], 'translate_semantics')
        metric, unknown = (row['asset_key'] for row in inventory['assets'])
        self.definition['source_bindings'] = [{'asset_key':metric,'target':'orders.n','review_ref':'review-1',
                                              'semantics':'One count for each nonnull order ID.'}]
        definition = self.put('contracts/translation.json', self.definition)
        scope = {'inventory':inventory_pin,'reference':'owner-scope','required':[metric], 'deferred':{}}
        def prepare(key):
            source_scope = self.put('contracts/' + key + '-scope.json', scope)
            result = self.run_request('candidate', {'route':route,'definition':definition,'source_scope':source_scope}, key=key)
            return self.load(result)['candidate']
        with self.assertRaisesRegex(ValueError, 'source_dispositions'):
            prepare('incomplete')
        scope['required'].append(unknown)
        blocked = prepare('unresolved')
        self.assertEqual(blocked['files'], {})
        self.assertEqual(blocked['status'], 'blocked')
        scope.update(required=[metric], deferred={unknown:'Unidentified source filter belongs to a different report.'})
        ready = prepare('agreed-scope')
        self.assertEqual(ready['status'], 'candidate')
        self.assertEqual(set(ready['files']), {'orders.topic'})

    def test_user_with_limited_model_visibility_can_reuse_but_cannot_declare_absence(self):
        self.who['rolesByModel']['model']['permissions'] = ['READ']
        self.inventory['identity'] = self.put('evidence/model-user.json', self.who)
        pending = self.route('create_topic')
        self.assertEqual(self.load(pending)['route'], 'discovery_pending')
        self.inventory.update(topic_names=['orders'], suitability={'orders':{'status':'suitable','reason':'verified scope'}})
        reusable = self.route(previous=pending, key='reuse-observed')
        self.assertEqual(self.load(reusable)['route'], 'reuse_existing')

    def test_unsuitable_existing_topic_offers_a_scoped_edit(self):
        self.inventory.update(topic_names=['orders'], suitability={
            'orders':{'status':'unsuitable','reason':'Missing the approved order-count measure'}})
        initial = self.route()
        self.assertEqual(self.load(initial)['route'], 'offer_extend_topic')
        selected = self.route('extend_topic', previous=initial, key='approved-extension')
        self.assertEqual(self.load(selected)['route'], 'extend_topic')

    def test_unavailable_original_is_pending(self):
        spec, _, _, _, _ = self.bind(True)
        checks = self.load(spec['checks'])
        checks['policy'] = {'path':'evidence/future-policy.json','sha256':'0' * 64}
        spec['checks'] = self.put('contracts/incomplete-checks.json', checks)
        assessment = self.load(self.run_request('verify', spec))
        self.assertEqual(assessment['status'], 'pending')
        self.assertFalse(assessment['model_ready'])

    def test_late_dma_adoption_and_replay(self):
        route = self.route('create_topic')
        incoming = F.Fixture(self.root.parent/'foreign')
        review = self.root/'inputs/incoming.json'
        P.write_json(review,incoming.review)
        with self.assertRaisesRegex(ValueError,'record_late_dma_reconciliation'):
            P.import_dma(self.root,review)
        self.assertFalse((self.root/'inputs/dma-catalog.json').exists())
        pin = self.put('contracts/adoption.json',{'role':'user','reference':'chat/late','response_text':'Adopt this DMA review',
                  'prior_context':self.context,'destination':self.context,'action':'adopt_dma','route':route,
                  'handoff_sha256':P.digest(review.read_bytes()),'topics':[incoming.topic]})
        self.assertEqual(P.import_dma(self.root,review,pin['path'])['status'],'imported_candidate')
        self.assertEqual(P.import_dma(self.root,review)['status'],'already_imported_candidate')
        self.assertEqual(S.execute(self.root,P,'route','unused')['owner'],'dma')
        with self.assertRaisesRegex(ValueError,'dma_owner'):
            self.candidate(route)

    def bind(self, reuse):
        surface = P.load_project(self.root)[1]['surfaces'][0]
        if reuse:
            self.inventory.update(topic_names=['orders'],suitability={'orders':{'status':'suitable','reason':'exact scope and access'}})
            route = self.route()
            self.assertEqual(self.load(route)['route'],'reuse_existing')
            digest = P.digest(P.canonical(self.response))
            cand = None
        else:
            route = self.route('create_topic')
            cand = self.candidate(route)
            digest = self.load(cand)['candidate']['candidate_sha256']
        application = None
        if cand:
            raw = self.load(cand)['candidate']['files']
            original = self.put('evidence/branch-yaml.json', {'version': 1, 'files':raw, 'checksums':{k:'native-revision' for k in raw}})
            application = self.put('evidence/branch-file.json', {'kind':'omni_branch_file_readback','model_id':'dev',
                'candidate_sha256':digest, 'context':self.context, 'source_ref':'original/branch-model','yaml_response':original})
        case = V.Case(self.context['branch_id'])
        for key in case.refs:
            def edit(r):
                r['scope']['candidate_sha256'] = digest
                if key == 'readback':
                    r['response'] = self.response
                if key == 'policy':
                    r['topic_response_sha256'] = P.digest(P.canonical(self.response))
                    if surface == 'app':
                        r['surfaces']['control'] = {'resources':[],'not_applicable_reason':'No controls on the App.'}
                        for persona in r['personas'].values():
                            persona['probes'] = [p for p in persona['probes'] if p['kind'] != 'control']
                if surface == 'app' and key in ('allowed','restricted','default'):
                    r['probes'] = [p for p in r['probes'] if p['id'] != 'control']
            case.edit(key,edit)
        for path, data in case.originals.items():
            (self.root/path).write_bytes(data)
        effective_model = self.context['branch_id'] or self.context['model_id']
        scope = {'context':self.context,'effective_model_id':effective_model,'topic':'orders','query_ref':'trial/1'}
        trial = {**scope,'query':self.query,'status':'succeeded',
                 'result':self.put('evidence/trial-result.json',{**scope,'kind':'omni_topic_trial_result','status':'complete',
                     'query_sha256':P.digest(P.canonical(self.query)),'columns':['orders.n'],'rows':[{'orders.n':3}]})}
        obs = {'schema_version':1,'kind':'omni_topic_observation','review_sha256':digest,'context':self.context,
               'observed_at':'2026-10-01T16:00:00Z','identity':self.inventory['identity'],'models':self.inventory['models'],
               'topics':{'orders':self.put('evidence/topic.json',{'context':self.context,'effective_model_id':effective_model,
                                                                 'topic_name':'orders','response':self.response})},
               'trials':{'orders':self.put('evidence/trial.json',trial)}}
        obs_pin = self.put('evidence/observation.json',obs)
        spec = {'kind':'omni_modeling_access','route':route,'candidate':cand,'topic_response_sha256':digest,
                'application':application,'checks':self.put('contracts/checks.json',case.spec),'observation':obs_pin,'fields':['orders.n']}
        access = self.run_request('access',spec)
        self.assertEqual(self.load(access)['kind'],'omni_topic_access')
        tile = {'type':'query','isSql':False,'topicName':'orders','query':self.query}
        row = {'consumer_id':'count','document_id':'doc','query_key':'1','surface':surface,'topic':'orders',
               'question':'How many orders?','grain':'order','population':'orders','access_case':'assigned audience',
               'expectation_text':'Three orders','expectation':case.refs['policy'],'disposition':'new','tile':tile}
        queries = self.run_request('queries',{'kind':'omni_topic_consumer_plan','schema_version':1,'access':access,
                                              'consumers':[row],'controls':[]})
        cycle = F.G.Lifecycle(self.root,P)
        original = cycle.evidence
        files = {'access-data':access['path'],'access-user_access':obs_pin['path'],'analysis-queries':queries['path']}
        cycle.evidence = lambda name, content=None: files.get(name) or original(name, content)
        # Lifecycle's default fixture sets fixture-user. Use the real scoped principal in the gate.
        return spec, access, queries, tile, cycle

    def check_binding(self,reuse):
        spec, access, queries, tile, cycle = self.bind(reuse)
        data={'source_scope':'orders','user_identity':'analyst','evidence':{'data':access['path'],'user_access':spec['observation']['path']}}
        P.stage_record(self.root,dict(data,stage='access'))
        cycle.stage('analysis')
        params = dict(surface='dashboard',document_id='doc',context=self.context,presentations={'data':{'1':tile},'order':['1']})
        self.assertEqual(D.guard(self.root,P,**params)['policy'],'omni-modeling-v1')
        bad = copy.deepcopy(tile)
        bad['topicName'] = 'other'
        params['presentations']['data']['1'] = bad
        with self.assertRaises(ValueError):
            D.guard(self.root,P,**params)
        wrong = dict(spec, fields=['orders.missing'])
        with self.assertRaisesRegex(ValueError,'field_missing'):
            self.run_request('access',wrong,key='wrong')

    def test_reused_topic_through_saved_consumer(self):
        self.check_binding(True)

    def test_authored_topic_through_saved_consumer(self):
        self.check_binding(False)

    def test_shared_standalone_topic_prepares_native_app_from_sparse_plan(self):
        self.root = self.root.with_name('shared-app')
        self.setup_project(surface='app', branch=None)
        spec, access, queries, tile, cycle = self.bind(True)
        P.stage_record(self.root, {'stage':'access','source_scope':'orders','user_identity':'analyst',
            'evidence':{'data':access['path'],'user_access':spec['observation']['path']}})
        cycle.stage('analysis')
        def delivery(artifact):
            checks = self.load(spec['checks'])
            observations = []
            for pin in checks['access']:
                observed = self.load(pin)
                document = next(probe for probe in observed['probes'] if probe['id'] == 'document')
                document['artifact_sha256'] = artifact
                observations.append(self.put('evidence/delivery-'+observed['id']+'.json', observed))
            checks['access'] = observations
            self.run_request('delivery', {'access':access,'queries':queries,'artifact_sha256':artifact,
                'checks':self.put('contracts/checked-app-delivery.json', checks)})
        F.assert_shared_app_create(self, cycle, self.context, tile, 'count', 'doc', queries, 'omni-modeling-v1',
                                   delivery=delivery)


if __name__ == '__main__':
    unittest.main()
