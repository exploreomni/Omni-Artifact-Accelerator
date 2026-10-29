"""Three source types through Report scope and DMA; synthetic, offline only."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
P=load('analyst_project','skills/omni-artifact-accelerator/scripts/analyst_project.py')
W=load('report_source_workflow','skills/omni-artifact-accelerator/scripts/visual_workflow.py')
T=load('report_source_translator','skills/omni-artifact-translator/scripts/translate_artifact.py')
R=load('report_source_rdl_fixture','tests/test_rdl_report.py')
C=load('report_source_crystal_fixture','tests/test_crystal_report.py')
F=load('report_source_capture_fixture','tests/test_report_source_capture.py')
M=load('report_source_migration','skills/omni-backend-handoff/scripts/migration.py')
S=load('standalone','skills/omni-backend-handoff/scripts/standalone.py')

def put(root,path,value):
    target=root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(value)); return target

def setup(root,platform='ssrs'):
    snapshot=C.snapshot_fixture() if platform=='crystal' else R.snapshot_fixture(platform)
    original='inputs/original.json'; put(root,original,snapshot)
    inventory=T.translate((root/original).read_bytes(),'crystal-report' if platform=='crystal' else 'rdl-report')
    put(root,'inputs/inventory.json',inventory)
    for path in (original,'inputs/inventory.json'): P.register(root,'sources',path,path)
    W.prepare(root,original,'inputs/inventory.json','contracts/visual.json')
    requirements=W.load(root,'contracts/visual.json'); requirements.update(route='reuse_existing',route_reference='Synthetic retained route decision')
    put(root,'contracts/visual.json',requirements)
    return original,inventory,requirements

def scope_spec(requirements):
    units=[]
    for item in requirements['items']:
        migrate=item['disposition']=='migrate'
        units.append({'unit_id':'unit-'+str(len(units)),'inventory_path':'inputs/inventory.json','asset_keys':[item['asset_key']],
            'disposition':'migrate' if migrate else 'defer','rationale':'Synthetic explicit obligation disposition; no source exclusion inferred',
            'frontend_asset_ids':[item['asset_key']] if migrate else [],'surfaces':['report'] if migrate else []})
    return {'schema_version':1,'kind':'analyst_migration_scope_spec','scope_id':'synthetic-report-scope',
        'decision_reference':'Synthetic scope review, not actual approval','inventory_paths':['inputs/inventory.json'],
        'backend_context_path':None,'units':units}

class ReportSourceIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.base=Path(self.tmp.name).resolve()
    def project(self,platform):
        root=self.base/platform; P.init(root,'Synthetic source report','migration','report','none'); return root
    def test_three_platforms_route_distinct_specialists_and_report_only(self):
        for platform,role in P.REPORT_SOURCE_ROLES.items():
            with self.subTest(platform=platform):
                root=self.project(platform); _,inventory,_=setup(root,platform)
                self.assertEqual(P.report_source_scope(*P.load_project(root)),{platform})
                req=W.requirements(root,'contracts/visual.json')[1]
                self.assertEqual(req['surface'],['report']); self.assertEqual(len(req['items']),len(inventory['assets']))
                self.assertTrue(S.query_source_keys(req,'report'))
                for item in req['items']:
                    if not item['source_identity'].get('query_visual'):
                        self.assertFalse(any(c['lane']=='numeric' for c in item['required_cases']))
                with self.assertRaises(ValueError): P.stage_packet_gate(root,role,{'stage':'discovery','outputs':['deliverables/source.rdl']})
                with self.assertRaises(ValueError): P.stage_packet_gate(root,'report-builder',{'stage':'report','outputs':['deliverables/report.json']})
    def test_title_only_never_selects_source_specialist(self):
        root=self.project('empty'); self.assertEqual(P.report_source_scope(*P.load_project(root)),set())
        for role in P.REPORT_SOURCE_ROLES.values():
            with self.assertRaises(ValueError): P.stage_packet_gate(root,role,{'stage':'discovery','outputs':[]})
    def test_original_reprojection_and_registered_bytes_drift_reject(self):
        for platform in P.REPORT_SOURCE_ROLES:
            with self.subTest(platform=platform):
                root=self.project(platform); original,inventory,_=setup(root,platform)
                changed=copy.deepcopy(inventory); changed['assets'].pop(); put(root,'inputs/edited.json',changed)
                with self.assertRaisesRegex(ValueError,'projection_changed'): W.source_inventory(root,original,'inputs/edited.json')
                with self.assertRaises(ValueError): M.cw.verify_report_source_inventory(root,P.load_project(root)[1],'inputs/edited.json')
                path=root/original; path.write_bytes(path.read_bytes()+b' ')
                with self.assertRaises(ValueError): P.report_source_scope(*P.load_project(root))
                with self.assertRaises(ValueError): W.requirements(root,'contracts/visual.json')
    def test_freeze_preserves_full_denominator_and_missing_report_delivery_gap(self):
        for platform in P.REPORT_SOURCE_ROLES:
            with self.subTest(platform=platform):
                root=self.project(platform); original,inventory,req=setup(root,platform); spec=scope_spec(req)
                put(root,'contracts/scope.json',spec); M.freeze(root,'contracts/scope.json','evidence/scope.json')
                project=P.load_project(root)[1]; scope=M.load_scope(root,project,'evidence/scope.json')
                self.assertEqual(len(scope['source_assets']),len(inventory['assets']))
                self.assertFalse(scope['authorizes_target_write']); self.assertEqual(scope['source_completeness'],'not_established')
                self.assertEqual(M.cw.verify_report_source_inventory(root,project,'inputs/inventory.json')['path'],original)
                deliveries,files,gaps,required=M.surface_deliveries(root,project,scope,{})
                self.assertTrue(required); self.assertEqual(deliveries,{})
                self.assertIn({'code':'missing_surface_delivery','surface':'report'},gaps)
                spec['units'].pop(); put(root,'contracts/incomplete.json',spec)
                with self.assertRaisesRegex(ValueError,'omits supplied source'): M.build_scope(root,project,'contracts/incomplete.json')
    def test_standalone_report_return_cannot_use_empty_delivery_or_dashboard_alias(self):
        root=self.project('ssrs'); _,_,req=setup(root); put(root,'contracts/scope.json',scope_spec(req))
        M.freeze(root,'contracts/scope.json','evidence/scope.json'); project=P.load_project(root)[1]; scope=M.load_scope(root,project,'evidence/scope.json')
        record={'schema_version':1,'kind':'analyst_standalone_migration_return_spec','surface':'report','scope_sha256':scope['sha256'],
            'surface_deliveries':{},'unresolved':['Native report delivery not run']}
        put(root,'contracts/return.json',record)
        with self.assertRaisesRegex(ValueError,'both_scope_required'): S.build_return(root,project,'evidence/scope.json','contracts/return.json',M)
        record['surface_deliveries']={'dashboard':{'candidate_path':'a','execution_receipt_path':'b','coverage_path':'c'}}
        put(root,'contracts/return.json',record)
        with self.assertRaisesRegex(ValueError,'outside selected migration scope'): S.build_return(root,project,'evidence/scope.json','contracts/return.json',M)
    def test_shared_normalized_results_rederive_raw_and_pinned_profile(self):
        root=self.project('numeric'); req,source,directory=F.prepare(root/'inputs'); F.C.import_local(req,source,directory); capture=F.add_results(directory,source)
        _,_,_,_,binding=F.comparison_fixture(capture); raw=source/'results.csv'
        normalized=F.C.normalize_results(raw.read_bytes(),F.profile(),binding)
        put(root,'evidence/normalized.json',normalized)
        record={'file':W.pin(root,'evidence/normalized.json'),'raw_file':W.pin(root,str(raw.relative_to(root))),'format':'report-normalized'}
        self.assertEqual(W.rows(root,record),normalized['rows'])
        normalized['rows'][0]['amount']='0'; put(root,'evidence/changed.json',normalized); record['file']=W.pin(root,'evidence/changed.json')
        with self.assertRaisesRegex(ValueError,'report_normalization_changed'): W.rows(root,record)

    def test_native_report_return_preserves_source_parity_and_unverified_observation(self):
        fixture=load('report_return_native_fixture','tests/test_report_native.py')
        root=self.base/'native'; fixture.setup(root); native=fixture.N
        for path in ('inputs/source.json','inputs/source-inventory.json'):
            P.register(root,'sources',path,path)
        requirements=W.load(root,'contracts/visual.json'); spec=scope_spec(requirements)
        spec['inventory_paths']=['inputs/source-inventory.json']
        for unit in spec['units']: unit['inventory_path']='inputs/source-inventory.json'
        put(root,'contracts/migration-scope.json',spec)
        M.freeze(root,'contracts/migration-scope.json','evidence/migration-scope.json')
        native.observe(root,fixture.observation_spec(),'evidence/readback.json')
        native.observe(root,fixture.observation_spec('export'),'evidence/export.json')
        native.coverage(root,'deliverables/candidate.json',['evidence/readback.json','evidence/export.json'],[],'evidence/coverage.json')
        scope=W.load(root,'evidence/migration-scope.json')
        put(root,'contracts/return.json',{'schema_version':1,'kind':'analyst_standalone_migration_return_spec','surface':'report',
            'scope_sha256':scope['sha256'],'surface_deliveries':{'report':{'candidate_path':'deliverables/candidate.json',
            'execution_receipt_path':'evidence/readback.json','coverage_path':'evidence/coverage.json'}},
            'unresolved':['Native execution, source parity and acceptance remain unqualified']})
        result=M.build_return(root,P.load_project(root)[1],'evidence/migration-scope.json','contracts/return.json')
        self.assertEqual(result['surface'],'report'); self.assertEqual(result['candidate_coverage'],'incomplete')
        self.assertFalse(result['migration_accepted']); self.assertFalse(result['authorizes_target_write'])
        self.assertEqual(result['native_verification'],'supplied_observation_only')
        self.assertEqual(result['remote_freshness'],'unverified_remote')
        self.assertIn('numeric',result['missing_lanes']); self.assertIn('report_output',result['missing_lanes'])
        self.assertEqual(set(result['surface_deliveries']),{'report'})

if __name__=='__main__': unittest.main()
