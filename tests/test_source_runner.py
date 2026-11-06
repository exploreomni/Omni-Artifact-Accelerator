"""Source-runner fail-closed controls; synthetic native bytes are never executed."""
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runner_under_test', ROOT / 'scripts/validate_source.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
T = R.load('source_runner_transport', 'skills/omni-bi-engineer/scripts/cli_process.py')


class SourceRunnerTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.binary = self.root / 'inert-native-fixture'
        self.binary.write_bytes(b'\x7fELFOriginal synthetic bytes, not an executable program')
        self.binary.chmod(0o700)
        self.selection = {'path': str(self.binary),
                          'sha256': hashlib.sha256(self.binary.read_bytes()).hexdigest()}

    def run_case(self, name, node=None, effect=None):
        with patch.object(T, 'run', side_effect=effect,
                          return_value=subprocess.CompletedProcess([], 0, b'synthetic result', b'')) as run, \
                contextlib.redirect_stderr(io.StringIO()):
            result = R.run_case(name, T, node)
        return result, run

    def test_exact_existing_native_pin_is_required(self):
        self.assertEqual(R.verify_node_runtime(self.selection), self.selection)
        for value in ({}, {'path': 'relative', 'sha256': self.selection['sha256']},
                      dict(self.selection, sha256='0' * 64),
                      dict(self.selection, sha256='not-a-hash')):
            with self.subTest(value=value), self.assertRaises(R.SourceRuntimeError):
                R.verify_node_runtime(value)

    def test_links_and_ancestor_links_are_rejected(self):
        link = self.root / 'runtime-link'; link.symlink_to(self.binary)
        parent = self.root / 'directory-link'; parent.symlink_to(self.root, target_is_directory=True)
        for path in (link, parent / self.binary.name):
            with self.subTest(path=path), self.assertRaises(R.SourceRuntimeError):
                R.verify_node_runtime(dict(self.selection, path=str(path)))

    def test_scripts_writable_nonexecutables_and_oversized_files_are_rejected(self):
        for mode in (0o600, 0o722):
            self.binary.chmod(mode)
            with self.subTest(mode=mode), self.assertRaises(R.SourceRuntimeError):
                R.verify_node_runtime(self.selection)
        self.binary.chmod(0o700)
        with patch.object(R, 'MAX_SOURCE_RUNTIME', 4), self.assertRaises(R.SourceRuntimeError):
            R.verify_node_runtime(self.selection)
        self.binary.write_bytes(b'#!/bin/sh\nexit 0\n')
        selection = dict(self.selection, sha256=hashlib.sha256(self.binary.read_bytes()).hexdigest())
        with self.assertRaisesRegex(R.SourceRuntimeError, 'native_executable'):
            R.verify_node_runtime(selection)

    def test_file_changed_during_hash_is_rejected(self):
        read = os.read
        changed = False
        def mutate(fd, size):
            nonlocal changed
            block = read(fd, size)
            if block and not changed:
                changed = True
                self.binary.write_bytes(b'\x7fELFchanged synthetic bytes')
            return block
        with patch.object(R.os, 'read', side_effect=mutate), self.assertRaises(R.SourceRuntimeError):
            R.verify_node_runtime(self.selection)

    def test_missing_node_is_failed_required_coverage_without_process_launch(self):
        result, run = self.run_case(R.NODE_CASE)
        self.assertFalse(result['passed'])
        self.assertEqual(result['detail'], 'existing_node_runtime_not_selected')
        run.assert_not_called()

    def test_wrong_pin_never_launches_a_child(self):
        result, run = self.run_case(R.NODE_CASE, dict(self.selection, sha256='0' * 64))
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'source_runtime_unavailable')
        run.assert_not_called()

    def test_missing_runtime_file_is_an_explicit_failure(self):
        self.binary.unlink()
        result, run = self.run_case(R.NODE_CASE, self.selection)
        self.assertFalse(result['passed'])
        self.assertEqual(result['detail'], 'source_runtime_file_unavailable')
        run.assert_not_called()

    def test_case_requires_explicit_paired_selection_and_ignores_ambient_values(self):
        for args in (['--case', R.NODE_CASE], ['--case', R.NODE_CASE, '--node-runtime', str(self.binary)]):
            prior_meta = list(sys.meta_path)
            try:
                with patch.object(sys, 'argv', ['validate_source.py', *args]), \
                        patch.dict(os.environ, {R.NODE_PATH_ENV: str(self.binary),
                                                R.NODE_SHA_ENV: self.selection['sha256']}), \
                        patch.object(R, 'load') as load, contextlib.redirect_stderr(io.StringIO()), \
                        self.assertRaises(SystemExit) as caught:
                    R.main()
                self.assertEqual(caught.exception.code, 2)
                load.assert_not_called()
            finally:
                sys.meta_path[:] = prior_meta

    def test_explicit_node_does_not_expand_path_or_other_python_cases(self):
        for name in (R.NODE_CASE, 'metadata'):
            result, run = self.run_case(name, self.selection)
            self.assertTrue(result['passed'])
            argv = run.call_args.args[0]
            options = run.call_args.kwargs
            self.assertEqual(argv[1:4], ['-I', '-S', '-B'])
            self.assertEqual(options['env']['PATH'], '/usr/bin:/bin')
            self.assertEqual(set(options['env']), {'PATH', 'LANG', 'LC_ALL', 'HOME', 'XDG_CONFIG_HOME', 'TMPDIR'})
            self.assertEqual(options['max_stdout'], 128 * 1024)
            self.assertEqual(options['max_stderr'], 128 * 1024)
            self.assertEqual('--node-runtime' in argv, name == R.NODE_CASE)
            self.assertEqual('runtime' in result, name == R.NODE_CASE)
            if name == R.NODE_CASE:
                self.assertEqual(argv[-4:], ['--node-runtime', str(self.binary),
                                             '--node-sha256', self.selection['sha256']])
                self.assertTrue(result['runtime']['bytes_verified_before_and_after'])

    def test_runtime_change_during_child_cannot_claim_success(self):
        def mutate(*args, **kwargs):
            self.binary.write_bytes(b'\x7fELFchanged during synthetic child')
            return subprocess.CompletedProcess([], 0, b'synthetic result', b'')
        result, run = self.run_case(R.NODE_CASE, self.selection, mutate)
        run.assert_called_once()
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'source_runtime_unavailable')
        self.assertNotIn('bytes_verified_before_and_after', result['runtime'])

    def test_child_failure_and_bounds_remain_failures(self):
        for result in (subprocess.CompletedProcess([], 9, b'failed fixture', b''),
                       T.ProcessError('CLI deadline exceeded; reconcile any write intent'),
                       OSError('synthetic private error')):
            def effect(*args, **kwargs):
                if isinstance(result, Exception):
                    raise result
                return result
            row, run = self.run_case('metadata', effect=effect)
            self.assertFalse(row['passed'])
            self.assertGreaterEqual(row['elapsed_seconds'], 0)
            self.assertEqual(row['timeout_seconds'], 30)
            self.assertNotIn('synthetic private error', str(row))


if __name__ == '__main__':
    unittest.main()
