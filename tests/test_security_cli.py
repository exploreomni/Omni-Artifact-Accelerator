"""Bounded first-party transport checks. No vendor CLI, secrets or network."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("security_native", ROOT / "skills/omni-bi-engineer/scripts/omni_native.py")
native = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = native
SPEC.loader.exec_module(native)
transport = native.CLI_PROCESS


class SecurityCliTests(unittest.TestCase):
    def test_environment_is_allowlisted_and_help_has_no_credential(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append(kwargs)
            self.assertTrue(Path(kwargs["cwd"]).is_dir())
            self.assertEqual(kwargs["cwd"], kwargs["env"]["HOME"])
            return subprocess.CompletedProcess(argv, 0, b'{}', b'')
        ambient = {"AWS_SECRET_ACCESS_KEY": "synthetic", "GITHUB_TOKEN": "synthetic",
                   "SIGMA_CLIENT_SECRET": "synthetic", "LOOKER_TOKEN": "synthetic",
                   "NODE_OPTIONS": "synthetic", "NODE_PATH": "synthetic", "PYTHONPATH": "synthetic",
                   "OMNI_API_TOKEN": "synthetic-target", "HOME": "/not-the-real-home", "PATH": "/untrusted"}
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, ambient, clear=True):
            target = native.TargetConfig("https://test.example", "test", "doc", "draft", "model", "member", None)
            adapter = native.NativeAdapter(folder, target, runner=fake)
            adapter._cli(["--help"], auth=False)
            adapter._cli(["documents", "list-drafts", "doc"])
        expected = {"PATH", "LANG", "LC_ALL", "HOME", "XDG_CONFIG_HOME", "TMPDIR"}
        self.assertEqual(set(calls[0]["env"]), expected)
        self.assertEqual(set(calls[1]["env"]), expected | {"OMNI_API_TOKEN"})
        self.assertEqual(calls[1]["env"]["OMNI_API_TOKEN"], "synthetic-target")
        self.assertTrue(all(not Path(c["cwd"]).exists() for c in calls))

    def test_real_transport_requires_pinned_canonical_files_and_explicit_runtime(self):
        with self.assertRaises(transport.ProcessError):
            transport.command({})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            script, runtime = root / "entry.js", root / "runtime"
            script.write_bytes(b'#!/usr/bin/env node\n/* original inert fixture */')
            runtime.write_bytes(b'original nonexecuted runtime fixture')
            script.chmod(0o700); runtime.chmod(0o700)
            env = {"OAA_OMNI_CLI_PATH": str(script), "OAA_OMNI_CLI_SHA256": hashlib.sha256(script.read_bytes()).hexdigest()}
            with self.assertRaisesRegex(transport.ProcessError, "interpreter"):
                transport.command(env)
            env.update(OAA_OMNI_RUNTIME_PATH=str(runtime), OAA_OMNI_RUNTIME_SHA256=hashlib.sha256(runtime.read_bytes()).hexdigest())
            self.assertEqual(transport.command(env), [str(runtime), str(script)])
            runtime.write_bytes(b'changed')
            with self.assertRaisesRegex(transport.ProcessError, "pin mismatch"):
                transport.command(env)
            link = root / "link"; link.symlink_to(script)
            with self.assertRaisesRegex(transport.ProcessError, "canonical"):
                transport.command({**env, "OAA_OMNI_CLI_PATH": str(link)})

    def child(self, source, folder, **kwargs):
        return transport.run([sys.executable, "-I", "-S", "-B", "-c", source],
                             env=transport.environment(folder), cwd=folder, **kwargs)

    def test_concurrent_input_output_and_stderr_are_drained_without_deadlock(self):
        with tempfile.TemporaryDirectory() as folder:
            data = b'x' * 200000
            result = self.child("import sys; sys.stdout.buffer.write(b'a'*100000); sys.stdout.flush(); "
                                "sys.stderr.write('bounded private diagnostic'); "
                                "raw=sys.stdin.buffer.read(); sys.stdout.write(str(len(raw)))",
                                folder, input=data, timeout=3, max_stdout=300000)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'a' * 100000 + b'200000')
            self.assertEqual(result.stderr, b'')

    def test_stdout_and_stderr_limit_stop_child_without_echoing_content(self):
        with tempfile.TemporaryDirectory() as folder:
            for stream in ("stdout", "stderr"):
                with self.subTest(stream=stream):
                    started = time.monotonic()
                    with self.assertRaisesRegex(transport.ProcessError, stream + " limit") as caught:
                        self.child("import sys,time; sys." + stream + ".write('synthetic-secret'*1000); "
                                   "sys." + stream + ".flush(); time.sleep(30)", folder,
                                   timeout=3, max_stdout=64, max_stderr=64)
                    self.assertLess(time.monotonic() - started, 3)
                    self.assertNotIn('synthetic-secret', str(caught.exception))

    def test_deadline_reaps_child(self):
        with tempfile.TemporaryDirectory() as folder:
            started = time.monotonic()
            with self.assertRaisesRegex(transport.ProcessError, "deadline"):
                self.child("import os,time; open('pid','w').write(str(os.getpid())); time.sleep(30)",
                           folder, timeout=.5)
            self.assertLess(time.monotonic() - started, 3)
            pid = int((Path(folder) / "pid").read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_early_stdin_close_cannot_claim_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(transport.ProcessError, "input closed"):
                self.child("import os,time; os.close(0); os.write(1,b'{}'); time.sleep(.2)",
                           folder, input=b'x' * 2000000, max_stdout=3000000, timeout=3)

    def test_nonzero_status_and_utf8_errors_are_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.child("import sys; sys.stderr.write('synthetic-private'); sys.exit(7)", folder)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stderr, b'')
            target = native.TargetConfig("https://test.example", "test", "doc", "draft", "model", "member", None)
            adapter = native.NativeAdapter(folder, target, runner=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, b'\xff', b''))
            with self.assertRaisesRegex(native.NativeError, "UTF-8"):
                adapter._cli(["--help"], auth=False, text=True)


if __name__ == "__main__":
    unittest.main()
