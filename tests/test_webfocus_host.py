"""WebFOCUS local MCP and fixed operator scope; fake transport only."""
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
h = load('webfocus_host_tested', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('webfocus_host_fixture', 'tests/test_webfocus_capture.py')


class WebfocusHost(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic scoped source host', 'migration', 'both')
        self.req, self.result = f.prepare(self.root / 'inputs', connected=True)
        (self.root / 'inputs/request.json').write_bytes(f.C.encoded(self.req))

    def test_offline_tools_and_capture_integrity_without_network_grants(self):
        bridge = h.Bridge(self.root)
        names = {t['name'] for t in bridge.definitions()}
        self.assertTrue({'webfocus_import_local', 'webfocus_import_evidence', 'webfocus_translate',
            'webfocus_import_capture', 'webfocus_check_capture', 'webfocus_normalize_results'} <= names)
        self.assertFalse({'webfocus_capture', 'native_execute', 'app_execute'} & names)
        path = str(Path(self.result['output']).relative_to(self.root))
        bridge.call('webfocus_check_capture', {'source': path})
        bridge.call('webfocus_import_capture', {'source': path, 'output': 'inputs/projection.json'})
        self.assertEqual(v.load(self.root, 'inputs/projection.json')['source']['platform'], 'webfocus')
        with self.assertRaises(ValueError): bridge.call('webfocus_capture', {'resume': True})
        file = self.result['capture']['source']['files'][0]
        (Path(self.result['output']).parent / file['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError): bridge.call('webfocus_check_capture', {'source': path})

    def test_exact_action_origin_query_and_no_execution_capability(self):
        command = h.WebfocusCommand(self.root, 'inputs/request.json', 'inputs/capture')
        fingerprint = {'request_sha256': command.request_hash, 'method': 'GET', 'body_sha256': None,
            'url': f.C.operation_url(command.config, command.config['operations'][0])}
        with patch.dict(os.environ, {'WEBFOCUS_SESSION': 'SYNTHETICSESSION=fixture-never-retained'}):
            self.assertEqual(set(command.authorize('getContent', fingerprint)), {'Cookie'})
            for operation, change in [('runAdHocFex', {}), ('run', {}), ('getDetails', {}),
                ('getContent', {'url': fingerprint['url'] + '&IBIRS_action=runAdHocFex'}),
                ('getContent', {'url': fingerprint['url'].replace('.invalid/', '.invalid.evil.example/')}),
                ('getContent', {'method': 'POST'}), ('getContent', {'body_sha256': '0' * 64}),
                ('getContent', {'request_sha256': '0' * 64})]:
                with self.subTest(operation=operation, change=change), self.assertRaises(ValueError):
                    command.authorize(operation, {**fingerprint, **change})
        with self.assertRaisesRegex(ValueError, 'token_env'):
            h.WebfocusCommand(self.root, 'inputs/request.json', 'inputs/capture', token_env='OMNI_API_TOKEN')
        with self.assertRaisesRegex(ValueError, 'import_before_capture'): command.capture(False)

    def test_host_retains_reads_but_never_credentials_or_native_authority(self):
        fake = f.FakeTransport()
        command = h.WebfocusCommand(self.root, 'inputs/request.json', 'inputs/capture', transport=fake)
        bridge = h.Bridge(self.root, webfocus=command)
        with patch.dict(os.environ, {'WEBFOCUS_SESSION': 'SYNTHETICSESSION=fixture-never-retained',
                                    'OMNI_API_TOKEN': 'synthetic-target-only'}):
            result = bridge.call('webfocus_capture', {'resume': True})
        self.assertEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn('fixture-never-retained', json.dumps(result))
        capture = v.load(self.root, result['evidence']['path'])
        self.assertFalse(capture['target_write_authority']); self.assertFalse(capture['source_execution'])
        self.assertNotIn('synthetic-target-only', json.dumps(capture))
        with self.assertRaises(ValueError):
            bridge.call('webfocus_capture', {'resume': True, 'source_origin': 'https://other.example.invalid'})

    def test_request_and_runtime_drift_prevent_credential_dispatch(self):
        command = h.WebfocusCommand(self.root, 'inputs/request.json', 'inputs/capture')
        path = self.root / 'inputs/request.json'; original = path.read_bytes(); path.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'changed_file'): command.capture(True)
        path.write_bytes(original)
        runtime = next(iter(command.runtime)); command.runtime[runtime] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'runtime_changed'): command.capture(True)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError): command.check_scope()


if __name__ == '__main__':
    unittest.main()
