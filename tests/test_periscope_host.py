"""CDT MCP host scope and credential boundaries; fake transports only."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
h = load('periscope_mcp_test', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('periscope_host_source', 'tests/test_periscope_capture.py')


class PeriscopeHost(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'project'
        ap.init(self.root, 'Synthetic source host', 'migration', 'dashboard')

    def prepare(self, render=False, inventory=False):
        req, result = f.prepare(self.root / 'inputs', render=render, list_dashboards=inventory)
        (self.root / 'inputs/request.json').write_bytes(f.C.encoded(req))
        return req, result

    def test_offline_tools_are_available_without_any_network_or_native_grant(self):
        req, result = self.prepare()
        bridge = h.Bridge(self.root)
        names = {t['name'] for t in bridge.definitions()}
        self.assertTrue({'periscope_import_local', 'periscope_import_evidence', 'periscope_translate',
                         'periscope_check_capture', 'periscope_import_capture', 'periscope_normalize_results'} <= names)
        self.assertFalse({'periscope_capture', 'native_execute', 'app_execute'} & names)
        source = str(Path(result['output']).relative_to(self.root))
        bridge.call('periscope_check_capture', {'source': source})
        bridge.call('periscope_import_capture', {'source': source, 'output': 'inputs/inventory.json'})
        self.assertEqual(v.load(self.root, 'inputs/inventory.json')['source']['platform'], 'periscope')
        with self.assertRaises(ValueError):
            bridge.call('periscope_capture', {'resume': True})
        original = self.root / 'inputs/capture' / result['capture']['source']['files'][0]['path']
        original.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            bridge.call('periscope_check_capture', {'source': source})

    def test_render_authority_is_separate_and_cross_host_routes_fail_closed(self):
        self.prepare(render=True, inventory=True)
        with self.assertRaisesRegex(ValueError, 'render_grant'):
            h.PeriscopeCommand(self.root, 'inputs/request.json', 'inputs/capture')
        with self.assertRaisesRegex(ValueError, 'token_env'):
            h.PeriscopeCommand(self.root, 'inputs/request.json', 'inputs/capture', token_env='OMNI_API_TOKEN', allow_render=True)
        command = h.PeriscopeCommand(self.root, 'inputs/request.json', 'inputs/capture', allow_render=True)
        request = {'request_sha256': command.request_hash, 'method': 'GET',
                   'url': 'https://app.periscopedata.com/api/v1/dashboards', 'body_sha256': None}
        with patch.dict(os.environ, {'PERISCOPE_API_KEY': 'synthetic-source-only'}):
            self.assertEqual(command.authorize('inventory', request), 'synthetic-source-only')
            for change in ({'url': 'https://app.periscopedata.com.evil.example/api/v1/dashboards'},
                           {'url': 'https://app.periscopedata.com/api/v1/dashboards?other=1'},
                           {'request_sha256': '0' * 64}, {'method': 'POST'}, {'body_sha256': '0' * 64}):
                with self.assertRaises(ValueError):
                    command.authorize('inventory', {**request, **change})
            with self.assertRaisesRegex(ValueError, 'render_scope'):
                command.authorize('render', {**request, 'method': 'POST',
                    'url': 'https://api.periscopedata.com/api/v1/screenshot_requests', 'body_sha256': '0' * 64})
            self.assertTrue(command.authorize('download', {**request,
                'url': 'https://periscope-render-virginia.s3.amazonaws.com/review.pdf?signature=synthetic'}))

    def test_capture_never_returns_source_credentials_or_signed_download_urls(self):
        req, initial = self.prepare(render=True, inventory=True)
        calls = []
        signed = 'https://periscope-render-virginia.s3.amazonaws.com/review.pdf?signature=synthetic-sensitive'
        def transport(method, url, headers, body, maximum, timeout):
            calls.append((method, url, headers, body))
            if method == 'POST':
                self.assertEqual(json.loads(body)['data']['dashboard_id'], 123)
                return 200, {}, f.C.encoded({'url': signed})
            if 's3.amazonaws.com' in url:
                self.assertNotIn('HTTP-X-PARTNER-AUTH', headers)
                return 200, {}, b'%PDF-1.4\nsynthetic inert PDF\n%%EOF'
            return 200, {}, f.C.encoded({'next_page_start': None, 'total_items': 1, 'items_this_page': 1,
                                        'dashboards': [{'id': 'api-board-uuid', 'name': 'Synthetic'}]})
        command = h.PeriscopeCommand(self.root, 'inputs/request.json', 'inputs/capture', allow_render=True, transport=transport)
        bridge = h.Bridge(self.root, periscope=command)
        with patch.dict(os.environ, {'PERISCOPE_API_KEY': 'synthetic-source-only', 'OMNI_API_TOKEN': 'synthetic-target-only'}):
            result = bridge.call('periscope_capture', {'resume': True})
        self.assertEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0][2]['HTTP-X-PARTNER-AUTH'], 'synthetic-site:synthetic-source-only')
        self.assertNotIn('synthetic-target-only', repr(calls))
        self.assertNotIn('synthetic-source-only', json.dumps(result))
        self.assertNotIn('signature=', json.dumps(result))
        envelope = v.load(self.root, result['evidence']['path'])
        self.assertNotIn('signature=', json.dumps(envelope))
        self.assertFalse(envelope['target_write_authority'])
        with self.assertRaises(ValueError):
            bridge.call('periscope_capture', {'resume': True, 'site_name': 'other'})

    def test_changed_request_source_or_runtime_cannot_use_startup_grant(self):
        req, result = self.prepare(inventory=True)
        command = h.PeriscopeCommand(self.root, 'inputs/request.json', 'inputs/capture')
        original_request = (self.root / 'inputs/request.json').read_bytes()
        (self.root / 'inputs/request.json').write_bytes(original_request + b' ')
        with self.assertRaisesRegex(ValueError, 'changed_file'):
            command.capture(True)
        (self.root / 'inputs/request.json').write_bytes(original_request)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError):
                command.check_scope()
        pin = result['capture']['source']['files'][0]
        (self.root / 'inputs/capture' / pin['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            command.capture(True)

    def test_direct_isolated_entrypoints_work_without_site_packages(self):
        for name in ('visual_workflow.py', 'visual_mcp.py'):
            path = ROOT / 'skills/omni-artifact-accelerator/scripts' / name
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(path), '--help'],
                                    capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
