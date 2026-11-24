"""Routing and lifecycle checks. Kernel behavior requires a native Windows run."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/omni-artifact-accelerator/scripts/analyst_project.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WorkspaceSetupTests(unittest.TestCase):
    def setUp(self):
        self.ap = load('test_platform_entry', SCRIPT)
        self.setup = self.ap.routing_helper('workspace_setup')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name).resolve()

    def test_posix_report_requires_no_windows_module_or_host_connection(self):
        with mock.patch.object(sys, 'platform', 'darwin'):
            loader = mock.Mock(wraps=self.ap.routing_helper)
            result = self.setup.inspect(self.folder, 'offline', None, False, loader)
        self.assertEqual(result['workflow'], 'existing_posix_route')
        self.assertFalse(result['native_write_authorized'])
        self.assertEqual(loader.call_args_list, [mock.call('omni_cli_setup')])

    def test_blocked_local_workspace_retains_the_observed_mcp_route(self):
        nt_files = mock.Mock()
        nt_files.check_workspace.side_effect = ValueError('fixed_local_ntfs_volume_required')
        modules = {'windows_files': nt_files, 'omni_cli_setup': self.ap.routing_helper('omni_cli_setup')}
        with mock.patch.object(sys, 'platform', 'win32'):
            result = self.setup.inspect(self.folder, 'auto', 'omni_list_topics', True, modules.__getitem__)
        self.assertEqual(result['workflow'], 'blocked')
        self.assertEqual(result['connection']['route'], 'mcp')
        self.assertEqual(result['reason'], 'fixed_local_ntfs_volume_required')
        self.assertFalse(result['native_write_authorized'])
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_windows_init_checks_before_mkdir_and_exposes_only_complete_project(self):
        native = mock.Mock()
        native.no_links.side_effect = lambda p: Path(p).absolute()
        native.mkdir_private.side_effect = lambda p: p.mkdir()
        native.publish_directory.side_effect = lambda p, dest: p.rename(dest)
        normal = self.ap.routing_helper
        def route(name):
            return native if name == 'windows_files' else normal(name)
        target = self.folder / 'My project'
        opts = (target, 'Local preview', 'net-new', 'app')
        with mock.patch.object(self.ap, 'routing_helper', route), mock.patch.object(self.ap, 'os', wraps=os) as env:
            env.name = 'nt'
            native.check_workspace.side_effect = ValueError('unsupported_test_host')
            with self.assertRaisesRegex(ValueError, 'unsupported_test_host'):
                self.ap.init(*opts)
            self.assertEqual(list(self.folder.iterdir()), [])
            native.check_workspace.side_effect = None
            with mock.patch.object(self.ap, '_populate_project', side_effect=ValueError('interrupted')):
                with self.assertRaisesRegex(ValueError, 'Inspect private staging'):
                    self.ap.init(*opts)
            self.assertFalse(target.exists())
            native.publish_directory.assert_not_called()
            with mock.patch.object(self.ap, '_populate_project', return_value={'status': 'initialized'}):
                self.assertEqual(self.ap.init(*opts)['project'], str(target))
            with self.assertRaisesRegex(ValueError, 'use a new directory'):
                self.ap.init(*opts)
            self.assertEqual(native.publish_directory.call_count, 1)

    def test_windows_write_gate_stops_before_consulting_the_host_or_creating_files(self):
        gate = load('preview_write_gate', ROOT / 'skills/omni-app-engineer/scripts/native_write_gate.py')
        host = mock.Mock()
        with mock.patch.object(gate, 'os', wraps=os) as env:
            env.name = 'nt'
            with self.assertRaisesRegex(ValueError, 'await qualification'):
                gate.execute(self.folder, {}, host=host)
        self.assertEqual(host.mock_calls, [])
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_windows_evidence_paths_and_native_backend_boundary(self):
        native = self.ap.routing_helper('windows_files')
        self.assertEqual(native._parts('inputs/Observed values.json'), ['inputs', 'Observed values.json'])
        for unsafe in ('../data', 'x:y', 'NUL.txt', 'folder\\evidence', 'data. '):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                native._parts(unsafe)
        with mock.patch.object(native, 'os', wraps=os) as env:
            env.name = 'posix'
            with self.assertRaisesRegex(ValueError, 'native_windows_api_unavailable'):
                native.WindowsAPI()


if __name__ == '__main__':
    unittest.main()
