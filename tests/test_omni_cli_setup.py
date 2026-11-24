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
        for route in ("api", "offline"):
            self.assertEqual(self.cli("--route", route)["status"], "cli_not_needed")
        self.which.assert_not_called()

    def test_discovered_mcp_works_with_or_without_local_cli(self):
        for existing in (None, "/example/bin/omni"):
            self.which.return_value = existing
            self.assertEqual(self.cli("--omni-mcp-tool", "listTopics"),
                             {"status": "use_mcp", "route": "mcp", "tool": "listTopics"})
        self.which.assert_not_called()

    def test_auto_finds_cli_when_mcp_does_not_cover_operation(self):
        self.which.return_value = "/example/bin/omni"
        result = self.cli("--no-matching-omni-mcp-tool")
        self.assertEqual(result["route"], "cli")
        self.assertEqual(result["status"], "inspect_existing_cli")
        self.assertEqual(result["path"], self.which.return_value)

    def test_missing_routes_and_unknown_inventory_are_distinct(self):
        self.assertEqual(self.cli()["status"], "inspect_host_mcp")
        self.assertEqual(self.cli("--no-matching-omni-mcp-tool"),
                         {"status": "choose_connection", "route": "auto", "cli_status": "prepare_install_offer"})
        with patch.dict(os.environ, {"OAA_OMNI_CLI_SHA256": "previous-setting"}):
            self.assertEqual(self.cli("--no-matching-omni-mcp-tool")["cli_status"], "inspect_incomplete_pin")

    def test_explicit_route_is_respected(self):
        self.which.return_value = "/example/bin/omni"
        self.assertEqual(self.cli("--route", "mcp")["status"], "inspect_host_mcp")
        self.assertEqual(self.cli("--route", "mcp", "--no-matching-omni-mcp-tool")["status"],
                         "mcp_operation_unavailable")
        self.assertEqual(self.cli("--route", "mcp", "--omni-mcp-tool", "listTopics")["route"], "mcp")
        self.which.assert_not_called()
        self.assertEqual(self.cli("--route", "cli", "--omni-mcp-tool", "listTopics")["status"],
                         "inspect_existing_cli")

    def test_automatic_or_mcp_discovery_cannot_plan_install(self):
        for args in ((), ("--route", "mcp"), ("--no-matching-omni-mcp-tool",)):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.cli(*args, "--release-metadata", self.home / "release.json")
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
        if os.name == "nt":
            destination.write_bytes(b"existing candidate")
        else:
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
                if sys.platform == "win32":
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        self.cli(*args)
                    self.assertFalse((folder / "omni.payload").exists())
                    continue
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
        if sys.platform == "win32":
            with self.assertRaisesRegex(ValueError, "qualified host"):
                setup.stage_archive(plan, plan["plan_sha256"], archive, self.home)
            self.assertFalse((self.home / "omni.payload").exists())
            return
        with self.assertRaisesRegex(ValueError, "changed"):
            setup.stage_archive(plan, "0" * 64, archive, self.home)
        with self.assertRaisesRegex(ValueError, "regular CLI"):
            setup.stage_archive(plan, plan["plan_sha256"], archive, self.home)
        archive.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            setup.stage_archive(plan, plan["plan_sha256"], archive, self.home)
        self.assertFalse((self.home / "omni.payload").exists())

    def test_windows_discovery_distinguishes_host_preview_from_packaged_adapter(self):
        with patch.object(setup.platform, "system", return_value="Windows"):
            self.which.return_value = r"C:\Tools\omni.exe"
            found = self.cli("--no-matching-omni-mcp-tool")
            self.assertEqual(found["status"], "inspect_existing_cli")
            self.assertEqual(found["version_check"], "host_preview_only")
            self.assertEqual(found["bounded_adapter"], "unavailable_native_windows")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.cli("--route", "cli", "--preview-windows-version")
            with patch.object(setup.platform, "machine", return_value="ARM64"):
                self.assertEqual(self.cli("--route", "cli")["version_check"], "unavailable_for_architecture")

    def test_windows_preview_rejects_wrong_platform_route_and_unsafe_pins(self):
        for route in ("auto", "offline", "api", "mcp", "cli"):
            with self.subTest(route=route), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.cli("--route", route, "--preview-windows-version")
        state = {"os": "windows", "arch": "amd64", "status": "inspect_configured_cli"}
        with patch.dict(os.environ, {"OAA_OMNI_CLI_SHA256": "a" * 64}):
            for unsafe in (r"omni.exe", r"\\host\share\omni.exe", r"\\?\C:\tools\omni.exe",
                           r"C:\tools\..\omni.exe", r"C:\NUL\omni.exe", r"C:\tools.\omni.exe",
                           r"C:\tools:other\omni.exe", r"C:\tools\omni.cmd"):
                with self.subTest(path=unsafe), self.assertRaisesRegex(ValueError, "absolute local drive"):
                    setup.windows_version_preview({**state, "path": unsafe})
            with patch.dict(os.environ, {"OAA_OMNI_RUNTIME_PATH": "old"}), self.assertRaisesRegex(ValueError, "interpreter"):
                setup.windows_version_preview({**state, "path": r"C:\Tools\omni.exe"})

    def test_windows_image_observation_checks_bytes_and_architecture(self):
        x64_header = b"MZ" + bytes(58) + (64).to_bytes(4, "little") + b"PE\0\0\x64\x86"
        for raw in (b"other", x64_header[:-2] + b"\x64\xaa"):
            with self.assertRaisesRegex(ValueError, "x64 PE"):
                setup.check_windows_image(raw, hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError, "pin differs"):
            setup.check_windows_image(x64_header, "0" * 64)
        setup.check_windows_image(x64_header, hashlib.sha256(x64_header).hexdigest())

    def test_windows_preview_requires_execution_host_to_observe_the_pin(self):
        if sys.platform != "win32":
            state = {"os": "windows", "arch": "amd64", "status": "inspect_configured_cli",
                     "path": r"C:\Tools\omni.exe"}
            with patch.dict(os.environ, {"OAA_OMNI_CLI_SHA256": "a" * 64}), \
                    self.assertRaisesRegex(ValueError, "intended Windows host"):
                setup.windows_version_preview(state)
            return
        folder = self.home / "Omni Tools Ω"
        folder.mkdir()
        candidate = folder / "omni.exe"
        image = b"MZ" + bytes(58) + (64).to_bytes(4, "little") + b"PE\0\0\x64\x86"
        candidate.write_bytes(image)
        pin = hashlib.sha256(image).hexdigest()
        env = {"OAA_OMNI_CLI_PATH": str(candidate), "OAA_OMNI_CLI_SHA256": pin,
               "OMNI_API_TOKEN": "test-ambient-token"}
        with patch.dict(os.environ, env), patch.object(setup.platform, "system", return_value="Windows"):
            result = self.cli("--route", "cli", "--preview-windows-version")
        self.assertFalse(result["executed"])
        self.assertEqual(result["argv"], [str(candidate), "--version"])
        self.assertEqual(result["observed_binary_sha256"], pin)
        self.assertFalse(result["host_requirements"]["inherit_environment"])
        self.assertNotIn("test-ambient-token", json.dumps(result))

    def test_unqualified_windows_staging_stops_before_read_or_write(self):
        with patch.object(setup.sys, "platform", "win32"), patch.object(setup, "read_bounded") as read:
            with self.assertRaisesRegex(ValueError, "private ACLs"):
                setup.stage_archive({}, "unused", self.home / "archive", self.home)
            read.assert_not_called()
            self.assertFalse((self.home / "omni.payload").exists())

    def test_version_request_is_fixed_and_reparse_point_blocks_image_inspection(self):
        state = {"os": "windows", "arch": "amd64", "status": "inspect_configured_cli",
                 "path": r"C:\Omni Tools\omni.exe"}
        from pathlib import PureWindowsPath
        candidate = PureWindowsPath(state["path"])
        raw = b"MZ" + bytes(58) + (64).to_bytes(4, "little") + b"PE\0\0\x64\x86"
        pin = hashlib.sha256(raw).hexdigest()
        with patch.dict(os.environ, {"OAA_OMNI_CLI_SHA256": pin, "OMNI_API_TOKEN": "private-fixture"}), \
                patch.object(setup.sys, "platform", "win32"), patch.object(setup, "Path", return_value=candidate), \
                patch.object(setup, "read_windows_binary") as read:
            read.side_effect = ValueError("reparse point")
            with self.assertRaisesRegex(ValueError, "reparse"):
                setup.windows_version_preview(state)
            read.side_effect = None
            read.return_value = raw
            plan = setup.windows_version_preview(state)
            read.assert_called_with(candidate)
        self.assertFalse(plan["executed"])
        self.assertEqual(plan["argv"], [str(candidate), "--version"])
        self.assertEqual(plan["bounded_adapter"], "unavailable_native_windows")
        self.assertFalse(plan["host_requirements"]["inherit_environment"])
        self.assertEqual(plan["host_requirements"]["on_limit_or_timeout"], "terminate_process_tree")
        self.assertNotIn("private-fixture", json.dumps(plan))


if __name__ == "__main__":
    unittest.main()
