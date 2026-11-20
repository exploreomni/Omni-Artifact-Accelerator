"""Setup flow with synthetic release metadata. No network, CLI or installed files."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "omni_cli_setup", ROOT / "skills/omni-artifact-accelerator/scripts/omni_cli_setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.home = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        stack.enter_context(patch.object(setup.Path, "home", return_value=self.home))
        stack.enter_context(patch.dict(os.environ, {"PATH": ""}, clear=True))
        stack.enter_context(patch.object(setup.platform, "system", return_value="Linux"))
        stack.enter_context(patch.object(setup.platform, "machine", return_value="x86_64"))
        self.which = stack.enter_context(patch.object(setup.shutil, "which", return_value=None))

    def release(self, state, archive=b""):
        ext = "zip" if state["os"] == "windows" else "tar.gz"
        name = f"omni_1.2.3_{state['os']}_{state['arch']}.{ext}"
        return {"tag_name": "v1.2.3", "draft": False, "prerelease": False,
                "html_url": setup.REPOSITORY + "/releases/tag/v1.2.3",
                "assets": [{"name": name, "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
                            "browser_download_url": setup.REPOSITORY + "/releases/download/v1.2.3/" + name}]}

    def cli(self, *args):
        with patch.object(sys, "argv", ["omni_cli_setup", *map(str, args)]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            setup.main()
            return json.loads(output.getvalue())

    def test_other_routes_skip_probe(self):
        for route in ("mcp", "api", "offline"):
            self.assertEqual(self.cli("--route", route)["status"], "cli_not_needed")
        self.which.assert_not_called()

    def test_existing_and_stale_configuration_do_not_offer_install(self):
        self.which.return_value = "/example/bin/omni"
        self.assertEqual(self.cli("--route", "cli")["status"], "inspect_existing_cli")
        with patch.dict(os.environ, {"OAA_OMNI_CLI_PATH": "/missing/omni"}):
            self.assertEqual(self.cli("--route", "cli")["status"], "inspect_configured_cli")
        for key in ("OAA_OMNI_CLI_SHA256", "OAA_OMNI_RUNTIME_PATH", "OAA_OMNI_RUNTIME_SHA256"):
            with self.subTest(key=key), patch.dict(os.environ, {key: "previous-setting"}):
                self.assertEqual(self.cli("--route", "cli")["status"], "inspect_incomplete_pin")
        self.which.return_value = None
        destination = self.home / ".local/bin/omni"
        destination.parent.mkdir(parents=True)
        destination.symlink_to(self.home / "missing")
        self.assertEqual(self.cli("--route", "cli")["status"], "inspect_existing_cli")

    def test_platforms_match_official_release_matrix(self):
        for osname, machine, archive in (
                ("Darwin", "arm64", "darwin_arm64.tar.gz"), ("Darwin", "x86_64", "darwin_amd64.tar.gz"),
                ("Linux", "aarch64", "linux_arm64.tar.gz"), ("Linux", "x86_64", "linux_amd64.tar.gz"),
                ("Windows", "AMD64", "windows_amd64.zip"), ("Windows", "arm64", None), ("Linux", "i386", None)):
            with self.subTest(osname=osname, machine=machine), patch.object(setup.platform, "system", return_value=osname), \
                    patch.object(setup.platform, "machine", return_value=machine):
                state = setup.local_setup("cli")
                if archive:
                    plan = setup.release_plan(state, self.release(state))
                    self.assertEqual(plan["archive"], "omni_1.2.3_" + archive)
                    self.assertEqual(plan["status"], "awaiting_host_permission")
                else:
                    self.assertEqual(state["status"], "unsupported_platform")

    def test_release_identity_and_archive_digest_required(self):
        state = setup.local_setup("cli")
        for change in ({"prerelease": True}, {"draft": True}, {"html_url": "https://example.test"},
                       {"tag_name": "latest"}, {"assets": []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                setup.release_plan(state, {**self.release(state), **change})
        for change in ({"browser_download_url": "https://example.test/bin"}, {"digest": None}, {"digest": "bad"}):
            release = self.release(state)
            release["assets"][0].update(change)
            with self.assertRaises(ValueError):
                setup.release_plan(state, release)

    def test_plan_and_stage_both_formats_through_entrypoint(self):
        content = b"inert test bytes"
        for system in ("Linux", "Windows"):
            with self.subTest(system=system), patch.object(setup.platform, "system", return_value=system):
                folder = self.home / system
                folder.mkdir(mode=0o700)
                state = setup.local_setup("cli")
                archive = folder / "archive"
                if system == "Windows":
                    with zipfile.ZipFile(archive, "w") as pack:
                        pack.writestr(state["member"], content)
                else:
                    with tarfile.open(archive, "w:gz") as pack:
                        info = tarfile.TarInfo(state["member"])
                        info.size = len(content)
                        pack.addfile(info, io.BytesIO(content))
                meta = folder / "release.json"
                meta.write_text(json.dumps(self.release(state, archive.read_bytes())))
                base = ["--route", "cli", "--release-metadata", meta]
                plan = self.cli(*base)
                args = [*base, "--plan-sha256", plan["plan_sha256"], "--archive", archive, "--stage-in", folder]
                result = self.cli(*args)
                self.assertEqual(result["binary_sha256"], hashlib.sha256(content).hexdigest())
                staged = Path(result["path"])
                self.assertEqual(staged.read_bytes(), content)
                if os.name == "posix":
                    self.assertEqual(staged.stat().st_mode & 0o777, 0o600)
                self.assertFalse(Path(result["destination"]).exists())
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.cli(*args)

    def test_mismatch_or_link_member_cannot_stage(self):
        archive = self.home / "archive"
        with tarfile.open(archive, "w:gz") as pack:
            member = tarfile.TarInfo("omni")
            member.type = tarfile.SYMTYPE
            member.linkname = "other"
            pack.addfile(member)
        state = setup.local_setup("cli")
        plan = setup.release_plan(state, self.release(state, archive.read_bytes()))
        with self.assertRaisesRegex(ValueError, "changed"):
            setup.stage_archive(plan, "0" * 64, archive, self.home)
        with self.assertRaisesRegex(ValueError, "regular CLI"):
            setup.stage_archive(plan, plan["plan_sha256"], archive, self.home)
        archive.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            setup.stage_archive(plan, plan["plan_sha256"], archive, self.home)
        self.assertFalse((self.home / "omni.payload").exists())


if __name__ == "__main__":
    unittest.main()
