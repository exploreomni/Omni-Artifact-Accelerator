"""Original stdlib fixtures for offline create preparation and capture comparison.

No provider, credentials, tenant, transport, HTML execution or producer commands.
Synthetic captures establish checker behavior, not the vendor's live behavior.
"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TESTS = Path(__file__).resolve().parent
PATH = TESTS.parent / 'skills/omni-app-engineer/scripts/native_authoring.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


a = load('native_create_authoring', PATH)
G = load('native_create_fixture', TESTS / 'stage_gate_fixture.py')
P = a.project_helper()
HTML = '<!doctype html><html><body><main>Original synthetic candidate</main></body></html>'


class NativeCreate(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic new App', 'net-new', 'app', 'none',
               selection_policy='conversation-evidence-v1')
        self.gates = G.Lifecycle(self.root, P)
        self.gates.through('options')
        binding = P.stage_status(self.root)['choice_bindings']['option-1']
        response = {'schema_version': 1, 'kind': 'oaa_conversation_choice',
            'source': {'host': 'codex', 'conversation_ref': 'synthetic-conversation',
                'question_ref': 'synthetic-question', 'response_ref': None, 'role': 'user'},
            'response_text': 'I choose option-1', 'selected_option_id': 'option-1',
            'expected_binding': binding, 'recorded_by': 'fixture-agent',
            'assurance': 'agent_attested_not_independently_authenticated'}
        evidence = self.gates.evidence('conversation-response', json.dumps(response))
        P.stage_record(self.root, {'stage': 'choice', 'basis': 'conversation_evidence',
            'option_id': 'option-1', 'expected_binding': binding, 'evidence': {'user_response': evidence}})
        self.html_path, self.spec_path = 'deliverables/app.html', 'contracts/create-spec.json'
        (self.root / self.html_path).write_text(HTML)
        draft = P.read_json(self.root / 'contracts/design-intent.json')[0]
        draft['selections'][0]['candidate_path'] = self.html_path
        draft['selections'][0]['target'] = {'surface': 'app', 'state': 'local', 'document_id': None, 'draft_id': None}
        P.write_json(self.root / 'contracts/design-intent.json', draft, replace=True)
        self.gates.stage('design')
        self.spec = {'base_url': 'https://synthetic.invalid', 'slug': 'original-new-app',
            'model_id': 'model-1', 'name': 'Original synthetic App', 'description': 'A synthetic fixture.',
            'queryPresentations': {'data': {'1': {'name': 'Jobs', 'topicName': 'jobs',
                'type': 'query', 'isSql': False,
                'query': {'fields': ['jobs.id'], 'table': 'jobs', 'limit': 10, 'userEditedSQL': '',
                          'filters': {}, 'sorts': [], 'calculations': [], 'version': 5}}}, 'order': ['1']}}
        self.save_spec()

    def save_spec(self):
        (self.root / self.spec_path).write_text(json.dumps(self.spec))

    def stage(self, reviews=True, artifacts=None):
        P.stage_record(self.root, {'stage': 'candidate', 'iteration_id': 'one',
            'builders': ['fixture-engineer'], 'artifacts': artifacts or [self.html_path, self.spec_path]})
        if reviews:
            self.gates.reviews()

    def prepare(self):
        return a.prepare_create(project=self.root, artifact=self.html_path, spec_artifact=self.spec_path)

    def test_frozen_supporting_spec_is_reviewed_and_cannot_borrow_other_candidate_evidence(self):
        workflow = P.routing_helper('delivery_workflow')
        frozen = workflow.freeze(self.root, {'id': 'with-create-spec', 'builders': ['fixture-engineer'],
            'artifacts': [self.html_path, self.spec_path], 'supporting_artifacts': [self.spec_path],
            'context': ['contracts/execution.json']})
        self.gates.reviews()
        prepared = self.prepare()
        self.assertFalse(prepared['publication_authorized'])
        candidate = P.read_json(self.root / frozen['path'])[0]
        self.assertEqual(candidate['artifact_roles'], {self.html_path: 'primary', self.spec_path: 'supporting'})
        self.assertEqual(set(candidate['retained']), {self.html_path, self.spec_path})
        workflow.evidence_template(self.root, {'candidate': frozen['path'], 'output': 'evidence/delivery-fixture.json'})
        evidence = P.read_json(self.root / 'evidence/delivery-fixture.json')[0]
        note = self.gates.evidence('supplied-observation', 'Synthetic checker input, not actual publication or source review.')
        for lane, method in [('source', 'source_review'), ('publication', 'exact_readback')]:
            evidence['lanes'][lane] = {'status': 'reported_pass', 'method': method, 'observer': 'synthetic-observer',
                'bindings': workflow.pins(self.root, [note]), 'reason': 'Synthetic report testing checker bindings only.'}
        P.write_json(self.root / 'evidence/delivery-fixture.json', evidence, replace=True)
        request = {'run': P.load_project(self.root)[1]['execution_start']['path'],
            'execution': 'contracts/execution.json', 'candidate': frozen['path'], 'evidence': 'evidence/delivery-fixture.json'}
        result = workflow.assess(self.root, request)
        self.assertNotIn('delivery_artifacts_differ_from_selected_candidates', result['findings'])
        self.assertTrue(result['claims']['published_readback_verified'])
        self.assertFalse(result['claims']['rendered_verified'])
        original_hash = evidence['candidate_sha256']
        evidence['candidate_sha256'] = '0' * 64
        P.write_json(self.root / 'evidence/delivery-fixture.json', evidence, replace=True)
        result = workflow.assess(self.root, request)
        self.assertIn('evidence_candidate_differs', result['findings'])
        self.assertFalse(result['claims']['source_reviewed'])
        self.assertFalse(result['claims']['published_readback_verified'])
        self.assertFalse(result['claims']['preview_structurally_ready'])
        evidence['candidate_sha256'] = original_hash
        P.write_json(self.root / 'evidence/delivery-fixture.json', evidence, replace=True)
        self.spec['name'] = 'Changed unreviewed create specification'
        self.save_spec()
        result = workflow.assess(self.root, request)
        self.assertIn('candidate_artifacts_changed', result['findings'])
        self.assertFalse(result['claims']['published_readback_verified'])
        with self.assertRaises(ValueError):
            self.prepare()

    def captures(self, prepared):
        body, origin = prepared['request']['body'], prepared['base_url']
        identifier = body['identifier']
        route = '/api/v2/documents/' + identifier
        def capture(method, path, status, value):
            return {'base_url': origin, 'method': method, 'path': path, 'status': status,
                    'body': copy.deepcopy(value)}
        created = capture('POST', '/api/v2/documents', 201, {
            'identifier': identifier, 'name': body['name'], 'description': body['description']})
        document = capture('GET', route, 200, {
            'app': {'url': route + '/app'}, 'description': body['description'], 'name': body['name'],
            'modelId': body['modelId'], 'workbookModelId': 'server-workbook-1',
            'queryPresentations': body['queryPresentations']})
        app = capture('GET', route + '/app', 200, body['app'])
        return created, document, app

    def verify(self, prepared, captures):
        return a.verify_create(prepared, *captures, project=self.root,
                               artifact=self.html_path, spec_artifact=self.spec_path)

    def test_conversation_release_prepares_fixed_new_personal_create_without_authority(self):
        self.stage()
        prepared = self.prepare()
        self.assertEqual(prepared['request']['method'], 'POST')
        self.assertEqual(prepared['request']['path'], '/api/v2/documents')
        self.assertEqual(set(prepared['request']['body']),
                         {'identifier', 'name', 'description', 'modelId', 'queryPresentations', 'app'})
        self.assertEqual(prepared['request']['body']['app']['html'], HTML)
        self.assertEqual(prepared['request']['body']['app']['settings'], a.CREATE_SETTINGS)
        self.assertTrue(prepared['publishes_immediately'])
        self.assertFalse(prepared['publication_authorized'])
        self.assertFalse(prepared['native_verified'])
        self.assertFalse(P.stage_status(self.root)['choice_authenticated'])
        result = self.verify(prepared, self.captures(prepared))
        self.assertEqual(result['status'], 'exact_create_readback')
        self.assertEqual(result['derived_identifiers']['workbook_model'], 'server-workbook-1')
        self.assertFalse(result['native_verified'])
        (self.root / 'deliverables/unselected.html').write_text(HTML)
        with self.assertRaisesRegex(ValueError, 'selected App artifact'):
            a.prepare_create(project=self.root, artifact='deliverables/unselected.html', spec_artifact=self.spec_path)

    def test_missing_reviews_and_unpinned_spec_cannot_prepare(self):
        with self.assertRaises(ValueError):
            self.prepare()
        self.stage(reviews=False, artifacts=[self.html_path])
        with self.assertRaises(ValueError):
            self.prepare()
        self.gates.reviews()
        with self.assertRaisesRegex(ValueError, 'exact HTML and create specification'):
            self.prepare()

    def test_changed_source_and_review_evidence_fail_current_release_gate(self):
        self.stage()
        prepared = self.prepare()
        (self.root / self.html_path).write_text(HTML + 'changed')
        with self.assertRaises(ValueError):
            self.prepare()
        with self.assertRaises(ValueError):
            self.verify(prepared, self.captures(prepared))
        (self.root / self.html_path).write_text(HTML)
        # Locate an actual review pin instead of depending on a fixture scope label.
        review = next(iter(P.stage_status(self.root)['reviews'].values()))
        (self.root / review['evidence']['review']['path']).write_text('Changed original review')
        with self.assertRaises(ValueError):
            self.prepare()

    def test_historical_project_exemption_cannot_prepare_new_create(self):
        metadata = P.load_project(self.root)[1]
        metadata.pop('stage_gate_policy')
        metadata.pop('workflow_quality_policy', None)
        P.write_json(self.root / 'project.json', metadata, replace=True)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_spec_rejects_widening_routes_permissions_settings_sql_and_model_overrides(self):
        original = copy.deepcopy(self.spec)
        for key, value in [('folderId', 'shared'), ('document_id', 'existing'), ('permissions', []),
                           ('settings', {'allowDownloads': True}), ('endpoint', '/api/v2/documents/existing'),
                           ('app', {'html': 'other'}), ('credentials', {'token': 'synthetic'}), ('results', [])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                a.create_spec_check({**original, key: value})
        for bad in ('http://synthetic.invalid', 'https://user:secret@synthetic.invalid',
                    'https://synthetic.invalid/api', 'https://synthetic.invalid\n'):
            with self.subTest(origin=bad), self.assertRaises(ValueError):
                a.create_spec_check({**original, 'base_url': bad})
        for bad in ('Uppercase', 'trailing-', '../existing', 'new/app'):
            with self.subTest(identifier=bad), self.assertRaises(ValueError):
                a.create_spec_check({**original, 'slug': bad})
        for key, value in [('sql', 'SELECT secret'), ('modelId', 'another-model'),
                           ('userEditedSQL', 'SELECT secret'), ('limit', True), ('results', []),
                           ('credentials', {'token': 'synthetic'})]:
            spec = copy.deepcopy(original)
            spec['queryPresentations']['data']['1']['query'][key] = value
            with self.subTest(query_key=key), self.assertRaises(ValueError):
                a.create_spec_check(spec)
        spec = copy.deepcopy(original)
        spec['queryPresentations']['order'].append('1')
        with self.assertRaises(ValueError):
            a.create_spec_check(spec)

    def test_base_table_and_topic_are_distinct_but_explicit_join_context_must_match(self):
        tile = self.spec['queryPresentations']['data']['1']
        tile['query']['table'] = 'warehouse_jobs_view'
        tile['query']['join_paths_from_topic_name'] = 'jobs'
        self.save_spec()
        self.stage()
        prepared = self.prepare()
        actual = prepared['request']['body']['queryPresentations']['data']['1']
        self.assertEqual(actual['query']['table'], 'warehouse_jobs_view')
        self.assertEqual(actual['topicName'], 'jobs')
        self.assertEqual(self.verify(prepared, self.captures(prepared))['status'], 'exact_create_readback')
        tile['query']['join_paths_from_topic_name'] = 'different_topic'
        with self.assertRaises(ValueError):
            a.create_spec_check(self.spec)

    def test_prepared_mutation_cannot_be_repaired_by_local_rehash(self):
        self.stage()
        prepared = self.prepare()
        for change in ('html', 'model', 'endpoint', 'method', 'settings', 'origin', 'authorization'):
            altered = copy.deepcopy(prepared)
            if change == 'html':
                altered['request']['body']['app']['html'] += '<p>Unreviewed</p>'
            elif change == 'model':
                altered['request']['body']['modelId'] = 'other-model'
            elif change == 'endpoint':
                altered['request']['path'] += '/existing'
            elif change == 'method':
                altered['request']['method'] = 'PUT'
            elif change == 'settings':
                altered['request']['body']['app']['settings']['allowDownloads'] = True
            elif change == 'origin':
                altered['base_url'] = 'https://another.invalid'
            else:
                altered['publication_authorized'] = True
            altered['request_sha256'] = a.digest(altered['request']['body'])
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'request drift'):
                self.verify(altered, self.captures(prepared))

    def test_changed_readback_fields_are_not_normalized(self):
        self.stage()
        prepared = self.prepare()
        changes = [
            (1, lambda d: d.update(modelId='other-model'), 'document_metadata_or_model_mismatch'),
            (1, lambda d: d['queryPresentations']['data']['1']['query'].update(limit=100), 'query_presentations_mismatch'),
            (1, lambda d: d['queryPresentations']['data']['1'].update(miniUuid='unknown'), 'query_presentations_mismatch'),
            (1, lambda d: d['queryPresentations']['data']['1']['query'].update(newDefault=[]), 'query_presentations_mismatch'),
            (1, lambda d: d.update(permissions=[]), 'unsupported_document_readback_fields'),
            (1, lambda d: d['app'].update(url='/api/v2/documents/existing/app'), 'app_route_mismatch'),
            (2, lambda d: d.update(html=HTML + 'changed'), 'html_readback_mismatch'),
            (2, lambda d: d['settings'].pop('allowModals'), 'settings_readback_mismatch'),
            (2, lambda d: d['settings'].update(allowDownloads=0), 'settings_readback_mismatch'),
            (2, lambda d: d['settings'].update(safeDomains=['unreviewed.invalid']), 'settings_readback_mismatch'),
            (0, lambda d: d.update(warnings=['Inspect this']), 'create_warnings_require_review'),
        ]
        for index, mutate, finding in changes:
            captures = self.captures(prepared)
            mutate(captures[index]['body'])
            with self.subTest(finding=finding):
                result = self.verify(prepared, captures)
                self.assertEqual(result['status'], 'readback_mismatch')
                self.assertIn(finding, result['findings'])

    def test_capture_routes_and_success_status_are_required(self):
        self.stage()
        prepared = self.prepare()
        for index, field, value in [(0, 'status', 200), (0, 'status', 409), (1, 'method', 'POST'),
                                    (1, 'path', '/api/v2/documents/existing'),
                                    (2, 'base_url', 'https://another.invalid')]:
            captures = self.captures(prepared)
            captures[index][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                self.verify(prepared, captures)
        captures = self.captures(prepared)
        captures[0]['body']['identifier'] = 'different-created-document'
        with self.assertRaises(ValueError):
            self.verify(prepared, captures)

    def test_cli_private_prepare_and_verify_and_denial_before_output(self):
        self.stage()
        request = self.root / 'requests/create.json'
        request.write_text(json.dumps({'html': self.html_path, 'spec': self.spec_path}))
        output = self.root / 'deliverables/create-prepared.json'
        command = [sys.executable, '-I', '-S', '-B', str(PATH), 'app-create-prepare',
                   '--project', str(self.root), '--input', str(request), '--output', str(output)]
        result = subprocess.run(command, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(HTML.encode(), result.stdout)
        self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
        prepared = json.loads(output.read_text())
        verify_input = {'html': self.html_path, 'spec': self.spec_path, 'prepared': str(output)}
        for key, capture in zip(('created', 'document', 'app'), self.captures(prepared)):
            path = self.root / ('evidence/' + key + '.json')
            path.write_text(json.dumps(capture))
            verify_input[key] = str(path)
        request.write_text(json.dumps(verify_input))
        verify_output = self.root / 'evidence/verified.json'
        command[5] = 'app-create-verify'
        command[-1] = str(verify_output)
        result = subprocess.run(command, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(verify_output.read_text())['status'], 'exact_create_readback')
        request.write_text(json.dumps({'html': self.html_path, 'spec': self.spec_path, 'method': 'PUT'}))
        command[5], command[-1] = 'app-create-prepare', str(self.root / 'evidence/rejected.json')
        self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
        self.assertFalse(Path(command[-1]).exists())


if __name__ == '__main__':
    unittest.main()
