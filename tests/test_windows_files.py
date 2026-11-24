"""Filesystem qualification. Native NT tests require Windows 11 x64 on local NTFS."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'omni-artifact-accelerator' / 'scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


W = module('windows_files')
S = module('stage_gates')
P = S._helpers(None)


@unittest.skipUnless(os.name == 'nt', 'requires native Windows filesystem APIs')
class NativeWindowsFiles(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.parent = Path(folder.name)
        self.root = self.parent / 'private'
        self.assertEqual(W.check_workspace(self.parent)['filesystem'], 'NTFS')
        W.mkdir_private(self.root)

    def test_dacl_paths_and_no_clobber_directory_publish(self):
        self.assertEqual(W.check_private_project(self.root), self.root)
        with self.assertRaises(ValueError):
            W.check_private_project(self.parent)  # Standard temporary directory inherits its ACL.
        target = self.parent / 'engagement'
        source = self.root / 'facts.json'
        W.private_write(source, b'old')
        with self.assertRaises(FileExistsError):
            W.private_write(source, b'other')
        with self.assertRaises(FileNotFoundError):
            W.private_write(self.root / 'missing', b'other', replace=True)
        W.private_write(source, b'new', replace=True)
        W.publish_directory(self.root, target)
        self.assertFalse(self.root.exists())
        self.assertEqual(W.read_path(target / 'facts.json', 3), b'new')
        W.mkdir_private(self.root)
        with self.assertRaises(OSError):
            W.publish_directory(self.root, target)
        self.assertEqual(W.read_path(target / 'facts.json', 3), b'new')

    def test_shared_and_exclusive_admission_across_processes(self):
        lock = self.root / '.test-lock'
        code = """import importlib.util, sys
spec = importlib.util.spec_from_file_location('winfiles', sys.argv[1])
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
try:
    with backend.locked_path(sys.argv[2], shared=(sys.argv[3] == 'shared')):
        print('acquired')
except BlockingIOError:
    print('busy')
"""
        def probe(mode):
            result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(SCRIPTS / 'windows_files.py'),
                                     str(lock), mode], check=True, capture_output=True, text=True, timeout=20)
            return result.stdout.strip()
        with W.locked_path(lock, shared=True):
            self.assertEqual(probe('shared'), 'acquired')
            self.assertEqual(probe('exclusive'), 'busy')
        self.assertEqual(probe('exclusive'), 'acquired')

    def test_private_pair_and_journal_commit_preserve_old_state_on_failure(self):
        W.private_write(self.root / 'record', b'exists')
        with self.assertRaises(FileExistsError):
            W.write_pair(self.root, 'new-output', b'first', 'record', b'second')
        self.assertFalse((self.root / 'new-output').exists())
        with S._root_fd(self.root, P) as (_, cap):
            with S._locked(cap):
                S._atomic(cap, {'events': [1]}, P)
                with self.assertRaisesRegex(ValueError, 'stage_gate_busy'):
                    with S._locked(cap):
                        self.fail('second writer admitted')
                with patch.object(S._windows(), '_rename', side_effect=OSError('interruption')):
                    with self.assertRaises(OSError):
                        S._atomic(cap, {'events': [2]}, P)
            self.assertEqual(S._read(cap, S.JOURNAL, 128), b'{"events":[1]}\n')
        self.assertEqual(list(self.root.glob('.oaa-*')), [])

    def test_validation_snapshot_rereads_and_rejects_hardlinks(self):
        path = self.root / 'evidence'
        W.private_write(path, b'before')
        snapshot = P.validation_helper()
        with self.assertRaises(snapshot.Changed):
            with snapshot.operation(self.root):
                self.assertEqual(snapshot.read(path, 6), b'before')
                W.private_write(path, b'after!', replace=True)
        with self.assertRaises(ValueError):
            W.read_path(path, 3)
        os.link(path, self.root / 'second-name')
        with self.assertRaises(ValueError):
            W.read_path(path, 100)

    def test_directory_reparse_points_are_rejected_on_read_and_write(self):
        import _winapi
        destination, alias = self.parent / 'outside', self.root / 'junction'
        destination.mkdir()
        (destination / 'proof').write_bytes(b'retain')
        if not hasattr(_winapi, 'CreateJunction'):
            self.skipTest('runtime lacks the standard junction fixture helper')
        _winapi.CreateJunction(str(destination), str(alias))
        try:
            for operation in (lambda: W.no_links(alias / 'proof'), lambda: W.read_path(alias / 'proof', 16),
                              lambda: W.private_write(alias / 'proof', b'wrong', replace=True)):
                with self.assertRaises((ValueError, OSError)):
                    operation()
            self.assertEqual((destination / 'proof').read_bytes(), b'retain')
        finally:
            os.rmdir(alias)


    def test_native_separate_process_init_then_resume(self):
        root = self.parent / 'Analyst preview'
        cmd = [sys.executable, '-I', '-S', '-B', str(SCRIPTS / 'analyst_project.py')]
        preflight = subprocess.run(cmd + ['workspace-setup', '--workspace', str(self.parent),
            '--route', 'offline'], check=True, capture_output=True)
        self.assertEqual(json.loads(preflight.stdout)['workflow'], 'windows_preview')
        subprocess.run(cmd + ['init', '--output', str(root), '--name', 'Windows preview', '--mode',
            'migration', '--migration-treatment', 'preserve', '--surface', 'app', '--selection-policy',
            'conversation-evidence-v1'], check=True, capture_output=True)
        def resume():
            proc = subprocess.run(cmd + ['stage-status', '--project', str(root)], capture_output=True)
            self.assertIn(proc.returncode, (0, 1), proc.stderr)
            return json.loads(proc.stdout)
        first = resume()
        self.assertEqual(first['next_stage'], 'access')
        self.assertEqual(first['tail_sha256'], resume()['tail_sha256'])
        self.assertFalse(first['release_ready'])


if __name__ == '__main__':
    unittest.main()
