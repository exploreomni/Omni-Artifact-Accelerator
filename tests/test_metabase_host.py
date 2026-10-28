"""Metabase host authority boundary; original synthetic responses only."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
h = load('metabase_host_tested', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('metabase_host_fixture', 'tests/test_metabase_capture.py')


class MetabaseHost(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'project'
        ap.init(self.root, 'Synthetic source host', 'migration', 'both')

    def prepare(self, query=False):
        req, result = f.prepare(self.root / 'inputs', query=query)
        (self.root / 'inputs/request.json').write_bytes(f.C.encoded(req))
        return req, result

    def test_offline_tools_need_no_source_or_target_network_grant(self):
        req, result = self.prepare()
        bridge = h.Bridge(self.root)
        names = {t['name'] for t in bridge.definitions()}
        self.assertTrue({'metabase_import_local', 'metabase_import_evidence', 'metabase_translate',
            'metabase_import_capture', 'metabase_check_capture', 'metabase_normalize_results'} <= names)
        self.assertFalse({'metabase_capture', 'native_execute', 'app_execute'} & names)
        source = str(Path(result['output']).relative_to(self.root))
        bridge.call('metabase_check_capture', {'source': source})
        bridge.call('metabase_import_capture', {'source': source, 'output': 'inputs/inventory.json'})
        self.assertEqual(v.load(self.root, 'inputs/inventory.json')['source']['platform'], 'metabase')
        with self.assertRaises(ValueError):
            bridge.call('metabase_capture', {'resume': True})
        pin = result['capture']['source']['originals'][0]['file']
        (Path(result['output']).parent / pin['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            bridge.call('metabase_import_capture', {'source': source, 'output': 'inputs/changed.json'})

    def test_query_grant_exact_url_body_and_separate_credential(self):
        req, _ = self.prepare(query=True)
        with self.assertRaisesRegex(ValueError, 'query_grant'):
            h.MetabaseCommand(self.root, 'inputs/request.json', 'inputs/live')
        with self.assertRaisesRegex(ValueError, 'token_env'):
            h.MetabaseCommand(self.root, 'inputs/request.json', 'inputs/live', token_env='OMNI_API_TOKEN', allow_query=True)
        command = h.MetabaseCommand(self.root, 'inputs/request.json', 'inputs/live', allow_query=True)
        fingerprint = {'request_sha256': command.request_hash, 'method': 'GET',
            'url': req['source_origin'] + '/api/dashboard/1', 'body_sha256': None}
        with patch.dict(os.environ, {'METABASE_API_KEY': 'synthetic-source', 'OMNI_API_TOKEN': 'synthetic-target'}):
            self.assertEqual(command.authorize('read', fingerprint), 'synthetic-source')
            for change in ({'url': req['source_origin'] + '.evil.example/api/dashboard/1'},
                           {'url': req['source_origin'] + '/api/dashboard/1?other=1'},
                           {'url': req['source_origin'] + '/api/dashboard/2'},
                           {'request_sha256': '0' * 64}, {'method': 'POST'}, {'body_sha256': '0' * 64}):
                with self.assertRaises(ValueError):
                    command.authorize('read', {**fingerprint, **change})
            query = {**fingerprint, 'method': 'POST', 'url': req['source_origin'] + '/api/card/10/query',
                     'body_sha256': f.C.sha(req['queries'][0]['body'])}
            self.assertEqual(command.authorize('query', query), 'synthetic-source')
            for change in ({'body_sha256': '0' * 64}, {'url': req['source_origin'] + '/api/dataset'}, {'method': 'GET'}):
                with self.assertRaises(ValueError):
                    command.authorize('query', {**query, **change})

    def test_fresh_capture_returns_evidence_without_secret_or_acceptance(self):
        self.prepare()
        fake = f.FakeTransport()
        def transport(method, url, headers, body, maximum, timeout):
            self.assertNotIn('synthetic-target', repr(headers))
            return fake(method, url, headers, body, maximum, timeout)
        command = h.MetabaseCommand(self.root, 'inputs/request.json', 'inputs/live', transport=transport)
        bridge = h.Bridge(self.root, metabase=command)
        with patch.dict(os.environ, {'METABASE_API_KEY': 'synthetic-host-credential', 'OMNI_API_TOKEN': 'synthetic-target'}):
            result = bridge.call('metabase_capture', {'resume': False})
        self.assertEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual(len(fake.calls), 4)
        self.assertNotIn('synthetic-host-credential', json.dumps(result))
        self.assertEqual(result['native_validation'], 'not_run')
        envelope = v.load(self.root, result['evidence']['path'])
        self.assertFalse(envelope['target_write_authority'])
        with self.assertRaises(ValueError):
            bridge.call('metabase_capture', {'resume': True, 'source_origin': 'https://other.example.invalid'})

    def test_startup_request_and_runtime_pins_are_rechecked(self):
        self.prepare()
        command = h.MetabaseCommand(self.root, 'inputs/request.json', 'inputs/live')
        file = self.root / 'inputs/request.json'
        saved = file.read_bytes()
        file.write_bytes(saved + b' ')
        with self.assertRaisesRegex(ValueError, 'changed_file'):
            command.capture(False)
        file.write_bytes(saved)
        path = next(iter(command.runtime))
        command.runtime[path] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'runtime_changed'):
            command.capture(False)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError):
                command.check_scope()


if __name__ == '__main__':
    unittest.main()
