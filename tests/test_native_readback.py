"""Offline typed create/readback fixtures. No host navigation or data execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


def fixture_module():
    path = Path(__file__).with_name('test_native_create.py')
    spec = importlib.util.spec_from_file_location('readback_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeReadback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module = fixture_module()
        cls.fixture = module.NativeCreate()
        cls.addClassCleanup(cls.fixture.doCleanups)
        cls.fixture.setUp()
        tile = cls.fixture.spec['queryPresentations']['data']['1']
        tile['query']['filters'] = {'jobs.priority': {'kind': 'EQUALS', 'values': [3]}}
        cls.fixture.save_spec()
        cls.fixture.stage()
        cls.prepared = cls.fixture.prepare()
        cls.authoring = module.a
        cls.script = module.PATH

    def setUp(self):
        self.captures = self.fixture.captures(self.prepared)
        self.tile = self.captures[1]['body']['queryPresentations']['data']['1']
        self.settings = self.captures[2]['body']['settings']

    def verify(self, **extras):
        return self.authoring.verify_create_captures(
            self.prepared, self.prepared, *self.captures, project=self.fixture.root, **extras)

    def test_only_typed_server_additions_are_equivalent_and_inputs_are_preserved(self):
        exact = self.verify()
        self.assertEqual((exact['parity'], exact['differences']), ('exact', []))
        self.tile.update(aiConfig=None, automaticVis=False, filterOrder=[], prefersChart=False,
                         resultConfig={}, sourceQueryPresentationKey=None, subTitle=None,
                         visConfig={'chartType': None, 'fields': [], 'version': 0,
                                    'visConfig': {'config': {}, 'visType': None}})
        self.settings['allowLocalNetwork'] = False
        original = copy.deepcopy(self.captures)
        result = self.verify()
        self.assertEqual(self.captures, original)
        self.assertEqual(result['status'], 'equivalent_create_readback')
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['difference_count'], 9)
        self.assertEqual({d['classification'] for d in result['differences']}, {'equivalent'})
        self.assertTrue(all(d['expected'] == {'type': 'missing'} for d in result['differences']))
        self.assertEqual(result['capture_sha256']['app'], self.authoring.digest(original[2]))
        self.assertNotEqual(exact['capture_sha256']['app'], result['capture_sha256']['app'])

    def test_query_type_security_widening_and_unknown_defaults_are_unresolved(self):
        self.tile['query']['filters']['jobs.priority']['values'] = ['3']
        self.tile['query']['version'] = '5'
        self.tile['miniUuid'] = 'unknown'
        self.tile['visConfig'] = {'chartType': None, 'fields': [], 'version': False,
                                  'visConfig': {'config': {}, 'visType': None}}
        self.settings.update(allowLocalNetwork=0, allowDownloads=True, safeDomains=['example.invalid'])
        del self.settings['allowModals']
        result = self.verify()
        self.assertEqual((result['parity'], result['status']), ('unresolved', 'readback_mismatch'))
        deltas = {d['path']: d for d in result['differences']}
        self.assertEqual(len(deltas), 8)
        self.assertEqual({d['classification'] for d in deltas.values()}, {'unresolved'})
        prefix = '/document/queryPresentations/data/1/query'
        self.assertEqual(deltas[prefix + '/filters/jobs.priority/values/0']['expected']['type'], 'integer')
        self.assertEqual(deltas[prefix + '/filters/jobs.priority/values/0']['observed']['type'], 'string')
        self.assertEqual(deltas['/app/settings/allowLocalNetwork']['observed']['type'], 'integer')
        self.assertEqual(deltas['/app/settings/allowModals']['observed'], {'type': 'missing'})
        self.assertEqual(result['handoff']['html_identity'], 'matched')
        self.settings['allowLocalNetwork'] = True
        difference = next(d for d in self.verify()['differences'] if d['path'] == '/app/settings/allowLocalNetwork')
        self.assertEqual(difference['classification'], 'unresolved')

    def test_wrong_origin_login_redirect_and_simulated_viewer_never_observe_access_or_runtime(self):
        result = self.verify()
        url = 'https://synthetic.invalid/apps/original-new-app'
        self.assertEqual(result['handoff']['app_url'], url)
        self.assertIsNone(result['handoff']['observed_app_url'])
        nav = {'base_url': self.prepared['base_url'], 'method': 'GET', 'status': 200,
               'path': '/apps/original-new-app', 'body': {'final_url': url,
               'document_id': 'original-new-app', 'basis': 'native_host_navigation'}}
        for group, key, value in [(None, 'base_url', 'https://other.invalid'),
                                  (None, 'path', '/documents/original-new-app'),
                                  ('body', 'final_url', self.prepared['base_url'] + '/login'),
                                  ('body', 'document_id', 'another'),
                                  ('body', 'basis', 'local_simulation')]:
            altered = copy.deepcopy(nav)
            (altered if group is None else altered[group])[key] = value
            with self.subTest(key=key):
                handoff = self.verify(navigation=altered)['handoff']
                self.assertEqual(handoff['viewer_navigation'], 'unresolved_navigation_capture')
                self.assertIsNone(handoff['observed_app_url'])
        matched = self.verify(navigation=nav)
        self.assertEqual(matched['handoff']['observed_app_url'], url)
        for lane in ['host_viewport', 'query_reconciliation', 'effective_viewer_access',
                     'business_acceptance', 'native_interaction']:
            self.assertEqual(matched['handoff'][lane], 'not_observed')
        self.assertFalse(matched['native_verified'])
        self.captures[1]['body']['app']['url'] = '/api/v2/documents/other/app'
        self.assertIsNone(self.verify(navigation=nav)['handoff']['app_url'])

    def test_cli_binds_exact_capture_bytes_and_reports_unknown_filter_conversion(self):
        self.tile['query']['filters']['jobs.priority']['values'] = ['3']
        root = self.fixture.root
        request = {'html': self.fixture.html_path, 'spec': self.fixture.spec_path}
        file_hashes = {}
        for key, item in zip(('prepared', 'created', 'document', 'app'), (self.prepared, *self.captures)):
            path = root / ('readback-' + key + '.json')
            raw = (json.dumps(item, indent=2) + '\n').encode()
            path.write_bytes(raw)
            request[key] = path.name
            if key != 'prepared':
                file_hashes[key] = hashlib.sha256(raw).hexdigest()
        inputs, output = root / 'readback-input.json', root / 'readback-output.json'
        inputs.write_text(json.dumps(request))
        completed = subprocess.run([sys.executable, '-I', '-S', '-B', str(self.script), 'app-create-verify',
                                    '--input', str(inputs), '--output', str(output), '--project', str(root)],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        result = json.loads(output.read_text())
        self.assertEqual(result['parity'], 'unresolved')
        self.assertEqual(result['capture_file_sha256'], file_hashes)
        self.assertNotEqual(file_hashes['document'], result['capture_sha256']['document'])


if __name__ == '__main__':
    unittest.main()
