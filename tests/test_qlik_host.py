"""Qlik local MCP and fixed Reports host; original fixtures, fake transport only."""
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
h = load('qlik_host_tested', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('qlik_host_fixture', 'tests/test_qlik_capture.py')


class QlikHost(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic scoped source host', 'migration', 'both')
        self.req, self.result = f.prepare(self.root / 'inputs', connected=True)
        (self.root / 'inputs/request.json').write_bytes(f.C.encoded(self.req))

    def command(self, **kwargs):
        return h.QlikCommand(self.root, 'inputs/request.json', 'inputs/capture', allow_render=True, **kwargs)

    def test_offline_tools_and_capture_integrity_without_network_grants(self):
        bridge = h.Bridge(self.root)
        names = {t['name'] for t in bridge.definitions()}
        self.assertTrue({'qlik_import_local', 'qlik_import_evidence', 'qlik_translate', 'qlik_import_capture',
                         'qlik_check_capture', 'qlik_normalize_results', 'qlik_check_mcp'} <= names)
        self.assertFalse({'qlik_capture', 'native_execute', 'app_execute'} & names)
        path = str(Path(self.result['output']).relative_to(self.root))
        bridge.call('qlik_check_capture', {'source': path})
        bridge.call('qlik_import_capture', {'source': path, 'output': 'inputs/projection.json'})
        self.assertEqual(v.load(self.root, 'inputs/projection.json')['source']['platform'], 'qlik')
        with self.assertRaises(ValueError): bridge.call('qlik_capture', {'resume': True})
        pin = self.result['capture']['source']['originals'][0]['file']
        (Path(self.result['output']).parent / pin['path']).write_bytes(b'drift')
        with self.assertRaises(ValueError): bridge.call('qlik_check_capture', {'source': path})

    def test_render_grant_and_source_token_namespace_required(self):
        with self.assertRaisesRegex(ValueError, 'render_grant_required'):
            h.QlikCommand(self.root, 'inputs/request.json', 'inputs/capture')
        with self.assertRaisesRegex(ValueError, 'token_env'):
            self.command(token_env='OMNI_API_TOKEN')
        with self.assertRaisesRegex(ValueError, 'import_before_capture'):
            self.command().capture(False)

    def test_every_phase_recomputes_exact_pending_request_before_credentials(self):
        fake = f.FakeTransport(); command = self.command(transport=fake)
        original = command.authorize; observed = []

        def check(operation, fingerprint):
            observed.append(fingerprint['phase'])
            for change in ({'url': fingerprint['url'] + '/other'},
                           {'url': fingerprint['url'].replace('.invalid/', '.invalid.evil.example/')},
                           {'method': 'DELETE'}, {'body_sha256': '0' * 64},
                           {'request_sha256': '0' * 64}, {'operation_id': 'other'},
                           {'phase': 'unauthorized'}, {'extra': True}):
                with self.assertRaises(ValueError): original(operation, {**fingerprint, **change})
            for other in ('metadata', 'query', 'create_app'):
                with self.assertRaises(ValueError): original(other, fingerprint)
            return original(operation, fingerprint)

        with patch.object(command, 'authorize', side_effect=check), patch.dict(os.environ, {
                'QLIK_ACCESS_TOKEN': 'fixture-never-retained-token'}):
            result = command.capture(True)
        self.assertEqual(observed, ['create', 'status', 'outputs', 'download'])
        self.assertEqual(len(fake.calls), 4)
        self.assertEqual(result['status'], 'acquired_requested_operations')

    def test_host_retains_render_evidence_not_credentials_or_native_authority(self):
        fake = f.FakeTransport(); command = self.command(transport=fake)
        bridge = h.Bridge(self.root, qlik=command)
        with patch.dict(os.environ, {'QLIK_ACCESS_TOKEN': 'fixture-never-retained-token',
                                    'OMNI_API_TOKEN': 'synthetic-target-only'}):
            result = bridge.call('qlik_capture', {'resume': True})
            again = bridge.call('qlik_capture', {'resume': True})
        self.assertEqual(result['status'], again['status'])
        self.assertEqual(len(fake.calls), 4)
        capture = v.load(self.root, result['evidence']['path'])
        self.assertTrue(capture['source_execution'])
        self.assertFalse(capture['target_write_authority'])
        self.assertFalse(capture['arbitrary_source_code_execution'])
        self.assertEqual(capture['saved_query_execution'], 'not_requested')
        for secret in ('fixture-never-retained-token', 'synthetic-target-only'):
            self.assertNotIn(secret, json.dumps(capture))
            self.assertFalse(any(secret.encode() in path.read_bytes()
                                 for path in (self.root / 'inputs/capture').iterdir() if path.is_file()))
        with self.assertRaises(ValueError):
            bridge.call('qlik_capture', {'resume': True, 'source_origin': 'https://other.invalid'})

    def test_missing_source_credential_never_falls_back_to_target_credential(self):
        fake = f.FakeTransport(); command = self.command(transport=fake)
        with patch.dict(os.environ, {'OMNI_API_TOKEN': 'synthetic-target-only'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'host_authority_rejected'): command.capture(True)
        self.assertEqual(fake.calls, [])
        value, _ = f.C.load_latest(self.root / 'inputs/capture', self.req)
        self.assertFalse(value['source_execution'])
        self.assertEqual(value['operations'][-1]['status'], 'denied')
        self.assertFalse(value['operations'][-1]['dispatched'])

    def test_valid_replacement_source_is_rejected_after_startup(self):
        command = self.command()
        snapshot = f.snapshot(); snapshot['objects'][0]['payload']['qTitle'] = 'Changed source'
        f.supplied(self.root / 'replacement-supplied', snapshot)
        f.C.import_local(self.req, self.root / 'replacement-supplied', self.root / 'replacement', allow_source_read=True)
        (self.root / 'inputs/capture').rename(self.root / 'original-capture')
        (self.root / 'replacement').rename(self.root / 'inputs/capture')
        with self.assertRaisesRegex(ValueError, 'source_changed|changed_file'): command.capture(True)

    def test_known_journal_head_cannot_be_removed_to_repeat_dispatch(self):
        fake = f.FakeTransport(); command = self.command(transport=fake)
        with patch.dict(os.environ, {'QLIK_ACCESS_TOKEN': 'fixture-never-retained-token'}):
            command.capture(True)
            (self.root / command.journal_pin['path']).unlink()
            with self.assertRaises(ValueError): command.capture(True)
        self.assertEqual(len(fake.calls), 4)

    def test_request_and_runtime_drift_prevent_credential_dispatch(self):
        command = self.command()
        path = self.root / 'inputs/request.json'; original = path.read_bytes(); path.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'changed_file'): command.capture(True)
        path.write_bytes(original)
        runtime = next(iter(command.runtime)); command.runtime[runtime] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'runtime_changed'): command.capture(True)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError): command.check_scope()


if __name__ == '__main__':
    unittest.main()
