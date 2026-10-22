"""Optional actual Sigma producers under in-memory HTTP and a denied socket boundary.

Set OMNI_ARTIFACT_SIGMA_CHECKOUT to a trusted checkout and optionally
OMNI_ARTIFACT_SIGMA_PYTHON to its dependency-equipped Python. No tenant access.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-translator/scripts/translate_artifact.py'
spec = importlib.util.spec_from_file_location('sigma_visual_bridge_under_test', SCRIPT)
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
REVISION = 'f4eda45b0f49dc7335496d028665f7339ed82e8f'


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def parse(value):
    return t.translate(json.dumps(value, ensure_ascii=False, indent=2).encode(), 'sigma-agent', REVISION)


def reseal_bundle(value):
    order = [value['run_manifest'], *value['observations'], value['capability_matrix'],
             value['workbook_graph'], value['data_model_snapshot'], value['behavior_manifest']]
    hashes = {}
    for row in order:
        for ref in row['upstream_hashes']:
            if ref['artifact_id'] in hashes:
                ref['content_hash'] = hashes[ref['artifact_id']]
        row['content_hash'] = sha({k: v for k, v in row.items() if k != 'content_hash'})
        hashes[row['artifact_id']] = row['content_hash']


@unittest.skipUnless(os.environ.get('OMNI_ARTIFACT_SIGMA_CHECKOUT'), 'optional trusted Sigma checkout not selected')
class ActualSigmaBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        checkout = Path(os.environ['OMNI_ARTIFACT_SIGMA_CHECKOUT']).resolve()
        code = r'''
import importlib.util, json, socket, sys, tempfile
from pathlib import Path
checkout = Path(sys.argv[1]); engine = checkout / 'packages/omnikit-migration-engine'
sys.path.insert(0, str(engine / 'src'))
def denied(*args, **kwargs): raise AssertionError('network forbidden')
socket.getaddrinfo = denied
socket.socket.connect = denied
import httpx
from omni_migrator.extractors.sigma.api import SigmaApi

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value
api_fixture = module('sigma_actual_api_fixture', engine / 'tests/test_sigma_api.py')
cap_fixture = module('sigma_actual_cap_fixture', engine / 'tests/test_sigma_capability_spike.py')
def captured(aliases=False):
    def handler(request):
        response = api_fixture._handler(request)
        if response.status_code != 200 or request.url.path == '/v2/auth/token': return response
        body = response.json()
        if request.url.path == '/v2/workbooks/wb1/elements':
            body['entries'].append({'elementId':'bulk-only', 'pageId':'p1', 'type':'visualization', 'title':'Only bulk'})
        if aliases:
            def rename(value):
                if isinstance(value, dict):
                    for key in ('workbookId', 'dataModelId', 'pageId', 'elementId', 'controlId'):
                        # Only object identity endpoints; relationship references retain their keys.
                        if key in value and len([k for k in ('workbookId','dataModelId','pageId','elementId','controlId') if k in value]) == 1:
                            value['id'] = value.pop(key)
                    for child in value.values(): rename(child)
                elif isinstance(value, list):
                    for child in value: rename(child)
            # Exercise native identity aliases on selected inventory and page endpoint rows.
            if request.url.path in ('/v2/dataModels','/v2/workbooks','/v2/workbooks/wb1/pages'):
                rename(body)
        return httpx.Response(200, json=body)
    api = SigmaApi('https://api.example.invalid', 'synthetic', 'synthetic', httpx.MockTransport(handler))
    try: return api.snapshot(data_model_ids=['dm1'], workbook_ids=['wb1'])
    finally: api.close()
bundle, calls = cap_fixture._run(request=cap_fixture._request(evidence_mode='synthetic_fixture'))
visual_fixture = module('sigma_actual_visual_fixture', engine / 'tests/test_sigma_visual_capture.py')
visual, visual_results = {}, {}
for name in ('complete', 'partial', 'blocked', 'drift'):
    source = visual_fixture.Source()
    if name == 'partial': source.download_status = 404
    if name == 'blocked': source.organization = 'wrong-org'
    if name == 'drift': source.drift_after_png = True
    with tempfile.TemporaryDirectory(prefix='oaa-sigma-producer-', dir=str(Path(tempfile.gettempdir()).resolve())) as root:
        result = visual_fixture.run(source, Path(root))
        visual[name] = Path(result['output']).read_text()
        for attachment in result['capture']['attachments']:
            if attachment['format'] == 'json':
                visual_results[name] = (Path(root) / attachment['path']).read_text()
print(json.dumps({'ordinary':captured(), 'aliases':captured(True), 'bundle':bundle.model_dump(mode='json'), 'visual': visual, 'visual_results':visual_results}))
'''
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        response = subprocess.run([os.environ.get('OMNI_ARTIFACT_SIGMA_PYTHON', sys.executable), '-c', code, str(checkout)],
                                  capture_output=True, text=True, check=True, env=env)
        cls.produced = json.loads(response.stdout)

    def test_actual_snapshot_roundtrip_aliases_bulk_only_and_original_hash(self):
        for key in ('ordinary', 'aliases'):
            with self.subTest(profile=key):
                source = self.produced[key]
                before = copy.deepcopy(source)
                result = parse(source)
                self.assertEqual(source, before)
                self.assertEqual(result['upstream_payload'], source)
                self.assertEqual(result['source']['input_sha256'], hashlib.sha256(json.dumps(source, ensure_ascii=False, indent=2).encode()).hexdigest())
                self.assertEqual(result['migration_context']['original_source_sha256'], sha(source))
                self.assertEqual(result['migration_context']['snapshot_profile'], 'api_acquisition')
                visual = [x for x in result['assets'] if x['kind'] == 'visual']
                self.assertEqual({x['source_id'] for x in visual}, {'e1', 'bulk-only'})
                self.assertEqual(len(visual), 2)  # Nested and bulk e1 is one placement.
                bulk = next(x for x in visual if x['source_id'] == 'bulk-only')
                self.assertEqual(bulk['source_identity']['page_id'], 'p1')
                self.assertEqual(bulk['source_identity']['placement_evidence'], 'bulk_page_reference')
                self.assertEqual(result['coverage']['status'], 'partial_evidence')
                self.assertFalse(result['migration_context']['target_write_authority'])

    def test_real_context_preserves_marker_and_detects_stale_source(self):
        source = copy.deepcopy(self.produced['ordinary'])
        source['prepush_context'] = {'schema_version':'sigma-prepush-context.v1', 'source_sha256':sha(source),
            'workbook_id':'wb1', 'elements':{'bulk-only':{}}, 'controls':{}}
        self.assertIn('bulk-only', parse(source)['migration_context']['source_context']['elements'])
        source['_omnikit_acquisition']['definitionClass'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'context_stale'):
            parse(source)

    def test_actual_snapshot_conflicts_reject(self):
        for mutation, error in (
            (lambda s: s.update(snapshotContract='another-contract'), 'unsupported_snapshot'),
            (lambda s: s['workbooks'][0].update(id='another-workbook'), 'identity_alias'),
            (lambda s: s['_omnikit_acquisition'].update(selectedWorkbookIds=['other']), 'selection_mismatch'),
            (lambda s: s['workbooks'][0]['elements'][0].update(type='conflicting'), 'conflicting_element'),
            (lambda s: s['workbooks'][0]['elements'][-1].update(pageId='unknown'), 'orphan_element'),
        ):
            with self.subTest(error=error):
                source = copy.deepcopy(self.produced['ordinary'])
                mutation(source)
                with self.assertRaisesRegex(ValueError, error):
                    parse(source)

    def test_actual_capability_aggregate_projects_with_original_locators(self):
        source = self.produced['bundle']
        result = parse(source)
        self.assertEqual(result['upstream_payload'], source)
        self.assertEqual(result['migration_context']['source_contract'], source['schema_version'])
        self.assertTrue(any(a['source_path'].startswith('/workbook_graph/payload/nodes/') for a in result['assets']))
        self.assertTrue(any(a['source_path'] == '/data_model_snapshot/payload' for a in result['assets']))
        self.assertEqual(result['migration_context']['source_freeze'], source['run_manifest']['payload']['source_freeze'])
        self.assertEqual(result['coverage']['status'], 'partial_evidence')
        self.assertIsNone(result['migration_context']['route'])

    def test_capability_tampering_rejects_even_resealed_shared_bindings(self):
        for mutation, error in (
            (lambda s: s['workbook_graph'].update(scope_id='other-scope'), 'scope_mismatch'),
            (lambda s: s['workbook_graph']['payload'].update(workbook_id='other'), 'workbook_mismatch'),
            (lambda s: s['workbook_graph']['payload']['source_freeze'].update(workbook_tag_name='other'), 'freeze_mismatch'),
            (lambda s: s['observations'][0]['payload'].update(principal_ref='principal-ref://other'), 'principal_mismatch'),
            (lambda s: s['workbook_graph'].update(upstream_hashes=[]), 'upstream_mismatch'),
        ):
            with self.subTest(error=error):
                source = copy.deepcopy(self.produced['bundle'])
                mutation(source)
                reseal_bundle(source)
                with self.assertRaisesRegex(ValueError, error):
                    parse(source)
        source = copy.deepcopy(self.produced['bundle'])
        source['workbook_graph']['payload']['workbook_id'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'artifact_hash_mismatch'):
            parse(source)

    def test_actual_visual_serialization_and_incomplete_captures_remain_partial(self):
        for name, raw in self.produced['visual'].items():
            with self.subTest(capture=name):
                source = json.loads(raw)
                result = t.translate(raw.encode(), 'sigma-agent', REVISION)
                self.assertEqual(result['upstream_payload'], source)
                self.assertEqual(result['source']['input_sha256'], hashlib.sha256(raw.encode()).hexdigest())
                capture = result['migration_context']['visual_capture']
                self.assertEqual(capture['attachments'], source['attachments'])
                self.assertEqual(capture['status'], source['status'])
                self.assertEqual(result['coverage']['status'], 'partial_evidence')
                self.assertEqual(result['native_validation'], 'not_run')
                self.assertFalse(result['source_execution'])
                if name == 'complete':
                    self.assertEqual(len(capture['attachments']), 2)
                    self.assertEqual(len([a for a in result['assets'] if a['kind'] == 'visual']), 1)
                elif name == 'blocked':
                    self.assertFalse(result['assets'])

    def test_visual_resealed_attachment_swap_and_request_mismatch_reject(self):
        for mutation, error in (
            (lambda s: s['attachments'][0].update(capture_id='other'), 'attachment_identity'),
            (lambda s: s['attachments'][0].update(source_snapshot_sha256='a'*64), 'attachment_pin'),
            (lambda s: s['attachments'][0].update(query_id='other'), 'attachment_job'),
            (lambda s: s['attachments'][0].update(path='../outside.png'), 'attachment_path'),
            (lambda s: s['attachments'][1].update(path=s['attachments'][0]['path']), 'attachment_path_duplicate'),
            (lambda s: s['request']['parameters'].update(region='West'), 'request_hash'),
            (lambda s: s['source']['tagged_snapshot'].update(tag='different'), 'snapshot_hash'),
            (lambda s: s['source']['baseline']['identity'].update(displayName='changed'), 'baseline_hash'),
            (lambda s: s['source']['final_observation'].update(extra='changed'), 'final_observation_hash'),
            (lambda s: s.update(attachments=[]), 'downloaded_attachment'),
            (lambda s: s.update(target_write_authority=True), 'status_or_authority'),
        ):
            with self.subTest(error=error):
                source = json.loads(self.produced['visual']['complete'])
                mutation(source)
                source['content_hash'] = sha({k:v for k,v in source.items() if k != 'content_hash'})
                with self.assertRaisesRegex(ValueError, error):
                    parse(source)

    def test_actual_snapshot_requirements_and_backend_cowork_roundtrip(self):
        """Real source producer -> offline inventory -> requirements -> candidate handoff.

        The backend response is deliberately synthetic and unresolved: no native
        tenant, source semantic execution, source approval or business acceptance.
        """
        repo = SCRIPT.parents[3]
        def module(name, path):
            spec = importlib.util.spec_from_file_location(name, repo / path)
            value = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(value)
            return value
        journey_module = module('sigma_actual_journey', 'tests/test_migration_e2e.py')
        sys.path.insert(0, str(repo / 'skills/omni-artifact-accelerator/scripts'))
        try:
            workflow = module('sigma_actual_requirements', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
        finally:
            sys.path.pop(0)
        journey = journey_module.MigrationJourney('runTest')
        journey.setUp()
        self.addCleanup(journey.doCleanups)
        original_path, inventory_path = 'inputs/sigma-capture-source.json', 'inputs/sigma-capture-inventory.json'
        original = self.produced['ordinary']
        journey_module.write_json(journey.root / original_path, original)
        raw = (journey.root / original_path).read_bytes()
        inventory = t.translate(raw, 'sigma-agent', REVISION)
        journey_module.write_json(journey.root / inventory_path, inventory)
        for path in (original_path, inventory_path):
            journey_module.ap.register(journey.root, 'sources', path, path)
        workflow.prepare(journey.root, original_path, inventory_path, 'contracts/visual.json')
        req = workflow.load(journey.root, 'contracts/visual.json')
        self.assertEqual(len(req['items']), len(inventory['assets']))
        self.assertEqual({row['source_id'] for row in req['items'] if row['kind'] == 'visual'}, {'e1', 'bulk-only'})
        self.assertEqual(req['route'], 'unselected')
        req['route'] = 'omni_semantic_reconstruction'
        req['route_reference'] = 'synthetic-session://explicit-direct-route'
        journey_module.write_json(journey.root / 'contracts/visual.json', req)
        workflow.requirements(journey.root, 'contracts/visual.json')
        journey_module.ap.register(journey.root, 'artifacts', 'contracts/visual.json', 'visual-requirements')
        journey.inventories = [inventory]
        journey.source_paths = [original_path, inventory_path, 'contracts/visual.json']
        journey.source_pins = {path: journey_module.sha(journey.root / path) for path in journey.source_paths}
        journey.platform = 'sigma'
        journey.route = req['route']
        journey.assets = inventory['assets']
        journey.source_gaps = inventory['gaps']
        request = journey.request()
        self.assertEqual(request['spec']['route'], req['route'])
        self.assertIn('contracts/visual.json', {row['path'] for row in request['selected_inputs']})
        with self.assertRaisesRegex(ValueError, 'violates selected route'):
            journey.response(action='warehouse_and_semantic_candidate', name='wrong-route')
        journey.receive(journey.response())
        selected = journey.select()
        identities = journey.assert_local_boundary(selected)
        self.assertIn('bulk-only', {row['source_id'] for row in identities})
        self.assertEqual((journey.root / original_path).read_bytes(), raw)
        self.assertFalse(selected['accepted'])
        self.assertFalse(selected['authorizes_target_write'])

    def test_actual_visual_context_contradiction_cannot_pass_numeric_comparison(self):
        repo = SCRIPT.parents[3]
        sys.path.insert(0, str(repo / 'skills/omni-artifact-accelerator/scripts'))
        try:
            spec = importlib.util.spec_from_file_location('sigma_context_workflow', repo / 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
            workflow = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(workflow)
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory(prefix='oaa-sigma-context-', dir=str(Path(tempfile.gettempdir()).resolve())) as tmp:
            root = Path(tmp) / 'run'
            workflow.ap.init(root, 'Synthetic captured-context comparison', 'migration', 'dashboard')
            raw = self.produced['visual']['complete']
            original = json.loads(raw)
            (root / 'inputs/original.json').write_text(raw)
            (root / 'inputs/inventory.json').write_text(json.dumps(t.translate(raw.encode(), 'sigma-agent', REVISION)))
            workflow.prepare(root, 'inputs/original.json', 'inputs/inventory.json', 'contracts/visual.json')
            req = workflow.load(root, 'contracts/visual.json')
            case = next(c['case_id'] for i in req['items'] for c in i['required_cases'] if c['lane'] == 'numeric')
            (root / 'evidence/candidate.json').write_text('{"synthetic": true}')
            # Preserve the exact actual producer JSON bytes, not an assumed extract shape.
            for path in ('inputs/rows.json', 'evidence/rows.json'):
                (root / path).write_text(self.produced['visual_results']['complete'])
            context = {'filters': {'region': 'West'}, 'parameters': {'region': 'West'}, 'timezone': 'UTC',
                       'data_watermark': 'synthetic-fixed', 'population': 'selected',
                       'principal': original['request']['expected_user_id']}
            def side(path):
                return {'file': workflow.pin(root, path), 'format': 'json', 'context': copy.deepcopy(context),
                        'complete': True, 'completeness_reference': 'synthetic-review-declaration'}
            value = {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': case,
                     'requirements': workflow.pin(root, 'contracts/visual.json'),
                     'candidate': workflow.pin(root, 'evidence/candidate.json'),
                     'source': side('inputs/rows.json'), 'target': side('evidence/rows.json'),
                     'persona_equivalence_reference': 'synthetic-persona-mapping', 'keys': ['site'],
                     'columns': [{'name': name, 'source': name, 'target': name, 'type': kind}
                                 for name, kind in (('site', 'string'), ('available', 'number'))]}
            (root / 'contracts/compare.json').write_text(json.dumps(value))
            workflow.compare(root, 'contracts/compare.json', 'evidence/comparison.json')
            report = workflow.load(root, 'evidence/comparison.json')
            self.assertEqual(report['status'], 'inconclusive')
            self.assertIn('source.capture_context.parameters', report['gaps'])
            self.assertIn('source.capture_context.timezone', report['gaps'])
            self.assertNotIn('source.results_not_bound_to_capture', report['gaps'])
            self.assertEqual(report['mismatch_count'], 0)
            for name in ('source', 'target'):
                value[name]['context'].update(filters=original['request']['parameters'],
                    parameters=original['request']['parameters'], timezone=original['request']['timezone'])
            (root / 'contracts/compare.json').write_text(json.dumps(value))
            workflow.compare(root, 'contracts/compare.json', 'evidence/context-corrected.json')
            corrected = workflow.load(root, 'evidence/context-corrected.json')
            self.assertEqual(corrected['status'], 'inconclusive')
            self.assertEqual(corrected['gaps'], ['source.data_time_not_bound_to_capture'])


if __name__ == '__main__':
    unittest.main()
