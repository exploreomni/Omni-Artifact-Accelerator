"""ThoughtSpot local MCP and fixed operator scope; fake transport only."""
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
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
h = load('thoughtspot_host_tested', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('thoughtspot_host_fixture', 'tests/test_thoughtspot_capture.py')


class ThoughtspotHost(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic scoped source host', 'migration', 'both')
        self.req, self.result = f.prepare(self.root / 'inputs', connected=True)
        (self.root / 'inputs/request.json').write_bytes(f.C.encoded(self.req))

    def test_offline_tools_and_capture_integrity_without_network_grants(self):
        bridge = h.Bridge(self.root)
        names = {t['name'] for t in bridge.definitions()}
        self.assertTrue({'thoughtspot_import_local', 'thoughtspot_import_evidence', 'thoughtspot_translate',
            'thoughtspot_import_capture', 'thoughtspot_check_capture', 'thoughtspot_normalize_results'} <= names)
        self.assertFalse({'thoughtspot_capture', 'native_execute', 'app_execute'} & names)
        path = str(Path(self.result['output']).relative_to(self.root))
        bridge.call('thoughtspot_check_capture', {'source': path})
        bridge.call('thoughtspot_import_capture', {'source': path, 'output': 'inputs/projection.json'})
        self.assertEqual(v.load(self.root, 'inputs/projection.json')['source']['platform'], 'thoughtspot')
        with self.assertRaises(ValueError): bridge.call('thoughtspot_capture', {'resume': True})
        file = self.result['capture']['source']['originals'][0]['file']
        (Path(self.result['output']).parent / file['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError): bridge.call('thoughtspot_check_capture', {'source': path})

    def test_exact_body_origin_and_no_source_write_capability(self):
        command = h.ThoughtspotCommand(self.root, 'inputs/request.json', 'inputs/capture')
        spec = f.C.operation_spec(command.config, command.config['operations'][0])
        fingerprint = {'request_sha256': command.request_hash, 'method': 'POST',
                       'body_sha256': f.C.sha(spec['body']), 'url': spec['url']}
        with patch.dict(os.environ, {'THOUGHTSPOT_ACCESS_TOKEN': 'fixture-never-retained-token'}):
            self.assertEqual(set(command.authorize('metadata', fingerprint)), {'Authorization'})
            for operation, change in [('query', {}), ('render', {}), ('create_dashboard', {}),
                ('metadata', {'url': fingerprint['url'] + '/other'}),
                ('metadata', {'url': fingerprint['url'].replace('.invalid/', '.invalid.evil.example/')}),
                ('metadata', {'method': 'GET'}), ('metadata', {'body_sha256': '0' * 64}),
                ('metadata', {'request_sha256': '0' * 64})]:
                with self.subTest(operation=operation, change=change), self.assertRaises(ValueError):
                    command.authorize(operation, {**fingerprint, **change})
        with self.assertRaisesRegex(ValueError, 'token_env'):
            h.ThoughtspotCommand(self.root, 'inputs/request.json', 'inputs/capture', token_env='OMNI_API_TOKEN')
        with self.assertRaisesRegex(ValueError, 'import_before_capture'): command.capture(False)

    def test_query_and_render_require_separate_startup_grants(self):
        req = f.request(True)
        req['operations'].extend([f.operation('liveboard_data', 'query-one'), f.operation('liveboard_render', 'render-one')])
        (self.root / 'inputs/expanded.json').write_bytes(f.C.encoded(req))
        with self.assertRaisesRegex(ValueError, 'query_grant_required'):
            h.ThoughtspotCommand(self.root, 'inputs/expanded.json', 'inputs/capture')
        with self.assertRaisesRegex(ValueError, 'render_grant_required'):
            h.ThoughtspotCommand(self.root, 'inputs/expanded.json', 'inputs/capture', allow_query=True)
        with self.assertRaises(ValueError):
            h.ThoughtspotCommand(self.root, 'inputs/expanded.json', 'inputs/capture', allow_query=True, allow_render=True)
        f.prepare(self.root / 'expanded', req=req)
        command = h.ThoughtspotCommand(self.root, 'inputs/expanded.json', 'expanded/capture', allow_query=True, allow_render=True)
        with patch.dict(os.environ, {'THOUGHTSPOT_ACCESS_TOKEN': 'fixture-never-retained-token'}):
            for op in req['operations']:
                spec = f.C.operation_spec(command.config, op)
                fingerprint = {'request_sha256': command.request_hash, 'method': spec['method'],
                               'body_sha256': f.C.sha(spec['body']), 'url': spec['url']}
                self.assertEqual(set(command.authorize(spec['scope'], fingerprint)), {'Authorization'})
                with self.assertRaises(ValueError):
                    command.authorize(spec['scope'], {**fingerprint, 'body_sha256': f.C.sha({**spec['body'], 'unknown': 1})})

    def test_host_retains_reads_but_never_credentials_or_native_authority(self):
        fake = f.FakeTransport()
        command = h.ThoughtspotCommand(self.root, 'inputs/request.json', 'inputs/capture', transport=fake)
        bridge = h.Bridge(self.root, thoughtspot=command)
        with patch.dict(os.environ, {'THOUGHTSPOT_ACCESS_TOKEN': 'fixture-never-retained-token',
                                    'OMNI_API_TOKEN': 'synthetic-target-only'}):
            result = bridge.call('thoughtspot_capture', {'resume': True})
        self.assertEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn('fixture-never-retained', json.dumps(result))
        capture = v.load(self.root, result['evidence']['path'])
        self.assertFalse(capture['target_write_authority']); self.assertFalse(capture['source_execution'])
        self.assertNotIn('synthetic-target-only', json.dumps(capture))
        with self.assertRaises(ValueError):
            bridge.call('thoughtspot_capture', {'resume': True, 'source_origin': 'https://other.example.invalid'})

    def test_valid_replacement_source_is_rejected_after_startup(self):
        command = h.ThoughtspotCommand(self.root, 'inputs/request.json', 'inputs/capture')
        snapshot = f.snapshot(); snapshot['objects'][0]['payload']['liveboard']['name'] = 'Changed source'
        f.supplied(self.root / 'replacement-supplied', snapshot)
        f.C.import_local(self.req, self.root / 'replacement-supplied', self.root / 'replacement', allow_source_read=True)
        (self.root / 'inputs/capture').rename(self.root / 'original-capture')
        (self.root / 'replacement').rename(self.root / 'inputs/capture')
        with self.assertRaisesRegex(ValueError, 'source_changed|changed_file'): command.capture(True)

    def test_known_journal_head_cannot_be_removed_to_repeat_dispatch(self):
        fake = f.FakeTransport()
        command = h.ThoughtspotCommand(self.root, 'inputs/request.json', 'inputs/capture', transport=fake)
        with patch.dict(os.environ, {'THOUGHTSPOT_ACCESS_TOKEN': 'fixture-never-retained-token'}):
            command.capture(True)
            self.assertEqual(len(fake.calls), 1)
            (self.root / command.journal_pin['path']).unlink()
            with self.assertRaises(ValueError): command.capture(True)
        self.assertEqual(len(fake.calls), 1)

    def test_request_and_runtime_drift_prevent_credential_dispatch(self):
        command = h.ThoughtspotCommand(self.root, 'inputs/request.json', 'inputs/capture')
        path = self.root / 'inputs/request.json'; original = path.read_bytes(); path.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'changed_file'): command.capture(True)
        path.write_bytes(original)
        runtime = next(iter(command.runtime)); command.runtime[runtime] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'runtime_changed'): command.capture(True)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError): command.check_scope()


if __name__ == '__main__':
    unittest.main()
