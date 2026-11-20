"""A late DMA packet takes semantic ownership inside the user's existing OAA project."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


def load(file, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = load('test_continuation.py', 'late_packet_fixtures')
C = F.c


class LateContinuation(unittest.TestCase):
    def setUp(self):
        self.f = F.ContinuationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.ap = C._analyst()

    def project(self, surface, mode, *, prior=False):
        ap = self.ap
        root = self.f.project
        ap.init(root, 'Existing field investigation', mode, surface, modeling_lane='omni-only')
        self.project_id = ap.load_project(root)[1]['id']
        ap.write_json(root / 'inputs/existing.json', {'selected_design': 'original', 'stage': 'in progress'})
        self.ctx = {'base_url': 'https://example.invalid', 'model_id': 'model-1', 'branch_id': 'branch-1',
                    'principal_id': 'member-1', 'workbook_model_id': None}
        self.route = None
        if prior:
            D = ap.routing_helper('dma_topics')
            def write(name, body):
                ap.write_json(root / name, body)
                return D.pin(root, name, ap)
            identity = write('evidence/principal.json', {'keyScope':'user', 'user':{'membershipId':'member-1'},
                              'rolesByModel':{'model-1':{'role':'MODELER'}}})
            models = write('evidence/models.json', {'model-1':{'id':'model-1','modelKind':'SHARED','connectionId':'c'},
                'branch-1':{'id':'branch-1','baseModelId':'model-1','modelKind':'BRANCH','connectionId':'c'}})
            inventory = write('evidence/inventory.json', {'kind':'omni_modeling_inventory','context':self.ctx,
                'connection_id':'c','identity':identity,'models':models,'topic_names':[],'suitability':{},
                'complete':True,'model_visibility':'complete','physical_status':'ready'})
            write('inputs/discovery.json', {'schema_version':1,'kind':'omni_modeling_discovery', 'context':self.ctx,
                  'topic_name':'prior_topic','inventory':inventory})
            self.route = ap.routing_helper('semantic_lane').execute(root, ap, 'route','inputs/discovery.json')
        return copy.deepcopy(ap.load_project(root)[1])

    def decision(self, *, name='decision', **overrides):
        packet = self.f.packet
        doc = {'role':'user','action':'adopt_dma_continuation','reference':'fixture/user-decision',
               'response_text':'Adopt this incoming DMA packet in the current engagement.',
               'project_id':self.project_id,'route':self.route,'prior_context':self.ctx if self.route else None,
               'packet_sha256':packet['sha256'],'topics':packet['topic_names'],'destination':packet['destination'], **overrides}
        path = 'contracts/' + name + '.json'
        self.ap.write_json(self.f.project / path,doc)
        return path

    def adopt(self, decision=None):
        return C.initiate(self.f.packet_path,self.f.project,decision=decision)

    def test_v1_adopts_existing_dashboard_and_retains_old_route_and_other_files(self):
        orig = self.project('dashboard','migration',prior=True)
        decision = self.decision()
        with self.assertRaisesRegex(ValueError,'explicit continuation adoption'):
            self.adopt()
        adopted = self.adopt(decision)
        self.assertFalse(adopted['reused'])
        self.assertEqual(adopted['project_id'], orig['id'])
        self.assertFalse(adopted['authorizes_target_write'] or adopted['native_verified'])
        obj = self.ap.load_project(self.f.project)[1]
        self.assertEqual((obj['mode'],obj['surfaces'],obj['name']),(orig['mode'],orig['surfaces'],orig['name']))
        self.assertEqual(json.loads((self.f.project / 'inputs/existing.json').read_text())['selected_design'],'original')
        self.assertTrue((self.f.project / self.route['path']).is_file())
        self.assertTrue(self.adopt()['reused'])
        self.assertEqual(self.ap.load_project(self.f.project)[1],obj)
        self.assertEqual(C.project_selection(self.f.project)['topic_names'],['orders'])
        self.assertEqual(self.ap.routing_helper('semantic_lane').execute(self.f.project,self.ap,'route','unused')['owner'],'dma')
        (self.f.project / decision).write_text('{}')
        with self.assertRaises(ValueError):
            C.project_selection(self.f.project)

    def test_v2_no_review_stays_provisional_and_destination_is_retained(self):
        self.f.v2(['app'],review=False)
        self.f.packet['destination'] = None
        self.f.save()
        self.project('app','net-new',prior=True)
        dest = {k:self.ctx[k] for k in ('base_url','model_id','branch_id')}
        with self.assertRaisesRegex(ValueError, 'reconcile the prior destination'):
            self.adopt(self.decision(name='omitted-prior-destination'))
        decision = self.decision(destination=dest)
        receipt = self.adopt(decision)
        self.assertIsNone(C.project_selection(self.f.project)['semantic_review'])
        self.assertEqual(C.project_selection(self.f.project)['destination'],dest)
        self.assertEqual(C.project_selection(self.f.project)['topic_names'],[])
        self.assertFalse(receipt['native_verified'])
        self.assertNotIn('dma_import',self.ap.load_project(self.f.project)[1])
        D = self.ap.routing_helper('dma_topics')
        self.assertIsNone(D.current(self.f.project,self.ap.load_project(self.f.project)[1],self.ap)[2])
        with self.assertRaisesRegex(ValueError,'dma_owner'):
            self.ap.routing_helper('semantic_lane').execute(self.f.project,self.ap,'candidate','unused')

    def test_undeployed_selected_topic_later_imports_candidate_without_reopening_standalone_ownership(self):
        self.f.v2(['app'], review=False)
        self.f.packet['topic_names'] = ['orders']
        self.f.save()
        self.project('app', 'net-new', prior=True)
        initial = self.adopt(self.decision())
        source = self.f.project / 'inputs/later-DMA-review.json'
        self.ap.write_json(source, self.f.review)
        self.assertEqual(self.ap.import_dma(self.f.project, source)['status'], 'imported_candidate')
        self.assertEqual(self.ap.import_dma(self.f.project, source)['status'], 'already_imported_candidate')
        replay = self.adopt()
        self.assertTrue(replay['reused'])
        self.assertEqual(replay['receipt_sha256'], initial['receipt_sha256'])
        obj = self.ap.load_project(self.f.project)[1]
        selection, _, catalog = self.ap.routing_helper('dma_topics').current(self.f.project, obj, self.ap)
        self.assertEqual(selection['topic_names'], ['orders'])
        self.assertIsNone(selection['semantic_review'])
        self.assertEqual([row['id'] for row in catalog['topics']], ['orders'])
        self.assertEqual(len([s for s in obj['sources'] if s['id'] == 'dma-catalog']), 1)

    def test_wrong_surface_mode_prior_and_file_collision_are_refused(self):
        before = self.project('app','net-new')
        with self.assertRaisesRegex(ValueError,'surfaces and task mode'):
            self.adopt(self.decision(name='wrong-surface'))
        self.f.v2(['app'])
        with self.assertRaisesRegex(ValueError,'prior route'):
            self.adopt(self.decision(name='wrong-project',project_id='another'))
        collision = self.f.project / 'inputs/dma-catalog.json'
        collision.write_text('unrelated')
        with self.assertRaisesRegex(ValueError,'different bytes'):
            self.adopt(self.decision(name='eligible'))
        self.assertEqual(collision.read_text(),'unrelated')
        self.assertEqual(self.ap.load_project(self.f.project)[1],before)

    def test_integrated_adoption_requires_runtime_and_retry_checks_current_scope(self):
        f = self.f
        f.packet = f.make_packet(mode='integrated')
        original = self.project('dashboard','migration')
        decision = self.decision()
        with self.assertRaisesRegex(ValueError,'trusted DMA runtime'):
            self.adopt(decision)
        self.assertEqual(self.ap.load_project(f.project)[1],original)
        with patch.object(C.dma,'trusted_dma',return_value=f.gw):
            receipt = C.initiate(f.packet_path,f.project,run_dir=f.root/'run',dma_scripts=f.runtime,decision=decision)
            self.assertIsNotNone(receipt['backend_context'])
            self.assertTrue(C.initiate(f.packet_path,f.project,run_dir=f.root/'run',dma_scripts=f.runtime)['reused'])
            f.state['snapshot']['naming'] = {'changed':True}
            with self.assertRaisesRegex(ValueError,'material changed'):
                C.initiate(f.packet_path,f.project,run_dir=f.root/'run',dma_scripts=f.runtime)

    def test_interrupted_publish_retries_identically_without_activating_ownership(self):
        before = self.project('dashboard','migration')
        decision = self.decision()
        old = C.os.link
        def interrupt(src, dest):
            if Path(dest).name == 'adoption-receipt.json':
                raise OSError('simulated interruption')
            old(src, dest)
        with patch.object(C.os,'link',side_effect=interrupt), self.assertRaises(OSError):
            self.adopt(decision)
        self.assertEqual(self.ap.load_project(self.f.project)[1], before)
        self.assertIsNone(C.project_selection(self.f.project))
        self.assertEqual(self.adopt(decision)['project_id'],self.project_id)
        self.assertTrue(self.adopt()['reused'])


if __name__ == '__main__':
    unittest.main()
