"""Strategy host security boundaries with injected protocol fixtures only.

The synthetic filter/status response tests host gates, not vendor API coverage.
"""
import copy
import importlib.util
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
h = load('ms_host_tested', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('ms_capture_fixture', 'tests/test_microstrategy_capture.py')


class MicrostrategyHostTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'; ap.init(self.root, 'Synthetic host boundaries', 'migration', 'both')
        self.req, self.out = f.prepare(self.root / 'inputs', connected=True)
        (self.root / 'inputs/request.json').write_bytes(f.C.encoded(self.req))

    def command(self, **kw):
        return h.MicrostrategyCommand(self.root, 'inputs/request.json', 'inputs/capture', allow_execution=True, **kw)

    def environment(self):
        return patch.dict(os.environ, {'MICROSTRATEGY_AUTH_TOKEN': 'fixture-token-not-real',
            'MICROSTRATEGY_COOKIES': 'SESSION=fixture-cookie-not-real; LB=fixture-balancer-not-real'}, clear=True)

    def test_local_tools_never_enable_native_or_remote_capture(self):
        bridge = h.Bridge(self.root); names = {t['name'] for t in bridge.definitions()}
        self.assertTrue({'microstrategy_import_local', 'microstrategy_translate', 'microstrategy_import_capture',
            'microstrategy_import_evidence', 'microstrategy_normalize_results', 'microstrategy_check_mcp'} <= names)
        self.assertFalse({'microstrategy_capture', 'native_execute', 'app_execute'} & names)
        source = str(Path(self.out['output']).relative_to(self.root))
        bridge.call('microstrategy_check_capture', {'source': source})
        bridge.call('microstrategy_import_capture', {'source': source, 'output': 'inputs/projected.json'})
        self.assertEqual(v.load(self.root, 'inputs/projected.json')['source']['platform'], 'microstrategy')
        with self.assertRaises(ValueError): bridge.call('microstrategy_capture', {'resume': True})

    def test_execution_and_source_credential_namespaces_are_explicit(self):
        with self.assertRaisesRegex(ValueError, 'execution_grant_required'):
            h.MicrostrategyCommand(self.root, 'inputs/request.json', 'inputs/capture')
        with self.assertRaisesRegex(ValueError, 'token_env'): self.command(token_env='OMNI_API_TOKEN')
        with self.assertRaisesRegex(ValueError, 'cookie_env'): self.command(cookie_env='OMNI_COOKIE')
        with self.assertRaisesRegex(ValueError, 'import_before_capture'): self.command().capture(False)

    def test_token_and_all_cookies_only_released_for_exact_pending_scope(self):
        fake = f.FakeTransport(self.root / 'inputs/capture', self.req)
        command = self.command(transport=fake); authorize = command.authorize; observed = []
        def checked(scope, fingerprint):
            observed.append(scope)
            for change in ({'url': fingerprint['url'] + '/other'}, {'method': 'DELETE'},
                           {'body_sha256': '0' * 64}, {'request_headers_sha256': '0' * 64},
                           {'request_sha256': '0' * 64}, {'operation_id': 'other'}, {'phase': 'other'}):
                with self.assertRaises(ValueError): authorize(scope, {**fingerprint, **change})
            with self.assertRaises(ValueError): authorize('cleanup', fingerprint)
            granted = authorize(scope, fingerprint)
            self.assertEqual(set(granted), {'X-MSTR-AuthToken', 'Cookie', 'X-MSTR-ProjectID'})
            self.assertIn('LB=fixture-balancer-not-real', granted['Cookie'])
            return granted
        with patch.object(command, 'authorize', side_effect=checked), self.environment():
            result = command.capture(True)
        self.assertEqual(result['status'], 'acquired_requested_operations')
        tool = next(t for t in h.Bridge(self.root, microstrategy=command).definitions() if t["name"] == "microstrategy_capture")
        self.assertTrue(tool["annotations"]["openWorldHint"])
        self.assertEqual(observed, ['metadata', 'execution', 'metadata', 'execution', 'execution'])
        for file in (self.root / 'inputs/capture').iterdir():
            if file.is_file():
                for secret in (b'fixture-token-not-real', b'fixture-cookie-not-real', b'fixture-balancer-not-real'):
                    self.assertNotIn(secret, file.read_bytes())

    def test_token_without_cookies_cannot_fallback_to_omni(self):
        fake = f.FakeTransport(self.root / 'inputs/capture', self.req); command = self.command(transport=fake)
        with patch.dict(os.environ, {'MICROSTRATEGY_AUTH_TOKEN': 'fixture-token-not-real', 'OMNI_API_TOKEN': 'target-only'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'host_authority_rejected'): command.capture(True)
        self.assertEqual(fake.calls, [])

    def test_request_runtime_and_journal_drift_block_later_dispatch(self):
        command = self.command(); path = self.root / 'inputs/request.json'; original = path.read_bytes()
        path.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'changed_file'): command.capture(True)
        path.write_bytes(original)
        first = next(iter(command.runtime)); command.runtime[first] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'runtime_changed'): command.capture(True)
        fake = f.FakeTransport(self.root / 'inputs/capture', self.req); command = self.command(transport=fake)
        with self.environment(): command.capture(True)
        count = len(fake.calls); (self.root / command.journal_pin['path']).unlink()
        with self.environment(), self.assertRaises(ValueError): command.capture(True)
        self.assertEqual(len(fake.calls), count)


if __name__ == '__main__': unittest.main()
