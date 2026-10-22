import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/install_skills.py"
spec = importlib.util.spec_from_file_location("install_skills", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.destination = self.root / "installed"
        self.destination.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def make_source(self, name, version, contents, package_name="omni-analyst-accelerator"):
        source = self.root / name
        source.mkdir()
        (source / "package.json").write_text(json.dumps({"name": package_name,
            "version": version, "skills": list(contents)}))
        for skill, text in contents.items():
            folder = source / "skills" / skill
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(text)
            (folder / "references").mkdir()
            (folder / "references/context.md").write_text("Reference " + text)
        return source

    def archive(self, source, name="baseline.zip", extra=None, corrupt=None):
        files = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        package = json.loads(files["package.json"])
        manifest = {"package": package["name"], "version": package["version"], "files": [
            {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for path, raw in files.items()]}
        files["MANIFEST.json"] = json.dumps(manifest).encode()
        if corrupt:
            files[corrupt] += b"modified without updating manifest"
        path = self.root / name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for member, raw in files.items():
                    archive.writestr("OmniAnalystAccelerator/" + member, raw)
                for member, raw in extra or []:
                    archive.writestr(member, raw)
        return path

    def upgrade_fixture(self):
        old = self.make_source("old", "0.1.0", {"omni-alpha": "Old alpha", "omni-beta": "Old beta"})
        new = self.make_source("new", "0.2.0", {"omni-alpha": "New alpha", "omni-beta": "New beta", "omni-gamma": "New gamma"})
        baseline = self.archive(old)
        installer.install(self.destination, apply=True, source=old)
        return old, new, baseline

    def rename_fixture(self, suffix, version="0.2.0"):
        old = self.make_source("old-" + suffix, version,
            {"omni-analyst-accelerator": "Old orchestrator", "omni-beta": "Old beta"})
        new = self.make_source("new-" + suffix, "0.3.0",
            {"omni-artifact-accelerator": "New orchestrator", "omni-beta": "New beta", "omni-gamma": "New gamma"},
            package_name="omni-artifact-accelerator")
        destination = self.root / ("installed-" + suffix)
        destination.mkdir()
        baseline = self.archive(old, "baseline-" + suffix + ".zip")
        installer.install(destination, apply=True, source=old)
        return old, new, baseline, destination

    def test_preview_install_and_identical_reinstall(self):
        count = len(json.loads((installer.ROOT / "package.json").read_text())["skills"])
        preview = installer.install(self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual(len(preview["skills"]), count)
        installed = installer.install(self.destination, apply=True)
        self.assertTrue(installed["applied"])
        again = installer.install(self.destination, apply=True)
        self.assertTrue(all(row["action"] == "unchanged" for row in again["skills"]))
        self.assertEqual(len(list(self.destination.iterdir())), count)

    def test_existing_different_skill_leaves_everything_unchanged(self):
        skill = self.destination / "omni-qa-analyst"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Existing unrelated skill")
        with self.assertRaises(ValueError):
            installer.install(self.destination, apply=True)
        self.assertEqual([p.name for p in self.destination.iterdir()], ["omni-qa-analyst"])
        self.assertEqual((skill / "SKILL.md").read_text(), "Existing unrelated skill")

    def test_symlink_destination_rejected(self):
        link = self.root / "linked"
        link.symlink_to(self.destination, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.install(link, apply=True)

    def test_exact_upgrade_preview_apply_and_current_mix(self):
        _, new, baseline = self.upgrade_fixture()
        unrelated = self.destination / "other-skill"
        unrelated.mkdir()
        (unrelated / "custom.txt").write_text("Preserve me")
        # One skill may already match the new version in a partially upgraded bundle.
        (self.destination / "omni-beta/SKILL.md").write_text("New beta")
        (self.destination / "omni-beta/references/context.md").write_text("Reference New beta")
        before = installer.tree(self.destination, False)
        result = installer.install(self.destination, source=new, upgrade_from=baseline)
        self.assertEqual([r["action"] for r in result["skills"]], ["upgrade", "unchanged", "install"])
        self.assertEqual(installer.tree(self.destination, False), before)
        installer.install(self.destination, apply=True, source=new, upgrade_from=baseline)
        for name in json.loads((new / "package.json").read_text())["skills"]:
            self.assertEqual(installer.tree(self.destination / name, False), installer.tree(new / "skills" / name))
        self.assertEqual((unrelated / "custom.txt").read_text(), "Preserve me")
        self.assertFalse(result["baseline"]["publisher_authenticated"])

    def test_customized_skill_and_empty_extra_directory_refuse_without_mutation(self):
        _, new, baseline = self.upgrade_fixture()
        for change in ("edited_file", "extra_directory"):
            with self.subTest(change=change):
                skill = self.destination / "omni-alpha"
                if change == "edited_file":
                    (skill / "SKILL.md").write_text("Local customization")
                else:
                    (skill / "SKILL.md").write_text("Old alpha")
                    (skill / "personal-notes").mkdir()
                before = installer.tree(self.destination, False)
                with self.assertRaises(ValueError):
                    installer.install(self.destination, apply=True, source=new, upgrade_from=baseline)
                self.assertEqual(installer.tree(self.destination, False), before)
                self.assertFalse((self.destination / "omni-gamma").exists())

    def test_baseline_corruption_and_manifest_coverage_rejected(self):
        old, new, _ = self.upgrade_fixture()
        before = installer.tree(self.destination, False)
        archives = [self.archive(old, "corrupt.zip", corrupt="skills/omni-alpha/SKILL.md"),
                    self.archive(old, "extra.zip", extra=[("OmniAnalystAccelerator/unlisted.txt", b"extra")])]
        malformed = self.root / "invalid.zip"
        malformed.write_bytes(b"not a zip")
        for archive in archives + [malformed]:
            with self.subTest(archive=archive.name), self.assertRaises(ValueError):
                installer.install(self.destination, apply=True, source=new, upgrade_from=archive)
            self.assertEqual(installer.tree(self.destination, False), before)

    def test_archive_paths_duplicates_case_and_symlink_rejected(self):
        old, new, _ = self.upgrade_fixture()
        symlink = zipfile.ZipInfo("OmniAnalystAccelerator/link")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        cases = ["OmniAnalystAccelerator/../escape", "OmniAnalystAccelerator//alias",
                 "OmniAnalystAccelerator/package.json", "OmniAnalystAccelerator/PACKAGE.json",
                 "OmniAnalystAccelerator/skills/omni-alpha/SKILL.md/child",
                 "OmniAnalystAccelerator/SKILLS/omni-alpha/extra", symlink]
        for index, member in enumerate(cases):
            with self.subTest(member=str(member)):
                archive = self.archive(old, str(index) + ".zip", extra=[(member, b"invalid")])
                with self.assertRaises(ValueError):
                    installer.install(self.destination, apply=True, source=new, upgrade_from=archive)
        self.assertFalse((self.root / "escape").exists())

    def test_replacement_failure_rolls_back_prior_upgrades_and_new_install(self):
        _, new, baseline = self.upgrade_fixture()
        # Put a new install before the failure so both action kinds must roll back.
        package = json.loads((new / "package.json").read_text())
        package["skills"] = ["omni-gamma", "omni-alpha", "omni-beta"]
        (new / "package.json").write_text(json.dumps(package))
        before = installer.tree(self.destination, False)
        real_rename = installer.os.rename
        def fail_mid_replacement(src, dst):
            if "new" in Path(src).parts and Path(dst).parent.name == "omni-beta":
                raise OSError("simulated replacement failure")
            return real_rename(src, dst)
        with mock.patch.object(installer.os, "rename", side_effect=fail_mid_replacement):
            with self.assertRaises(OSError):
                installer.install(self.destination, apply=True, source=new, upgrade_from=baseline)
        self.assertEqual(installer.tree(self.destination, False), before)
        self.assertFalse(any(p.name.startswith('.omni-analyst') for p in self.destination.iterdir()))

    def test_rollback_failure_preserves_backup_for_manual_recovery(self):
        _, new, baseline = self.upgrade_fixture()
        real_rename = installer.os.rename
        def fail_install_and_restore(src, dst):
            if "new" in Path(src).parts and Path(dst).parent.name == "omni-beta":
                raise OSError("simulated replacement failure")
            if Path(src).parent.name == "backup" and Path(src).name == "omni-alpha":
                raise OSError("simulated rollback failure")
            return real_rename(src, dst)
        with mock.patch.object(installer.os, "rename", side_effect=fail_install_and_restore):
            with self.assertRaisesRegex(RuntimeError, "backups retained"):
                installer.install(self.destination, apply=True, source=new, upgrade_from=baseline)
        recovery = list(self.destination.glob('.omni-analyst-install-*'))
        self.assertEqual(len(recovery), 1)
        self.assertEqual((recovery[0] / "backup/omni-alpha/SKILL.md").read_text(), "Old alpha")
        self.assertFalse((self.destination / ".omni-analyst-install.lock").exists())

    def test_known_package_rename_migrates_main_without_duplicate(self):
        for version in ("0.1.0", "0.2.0"):
            with self.subTest(version=version):
                _, new, baseline, destination = self.rename_fixture(version, version)
                unrelated = destination / "other-skill"
                unrelated.mkdir()
                (unrelated / "custom.txt").write_text("Preserve me")
                before = installer.tree(destination, False)
                preview = installer.install(destination, source=new, upgrade_from=baseline)
                self.assertEqual(preview["skills"][0], {"skill": "omni-artifact-accelerator",
                    "action": "rename_upgrade", "from_skill": "omni-analyst-accelerator"})
                self.assertEqual(installer.tree(destination, False), before)
                installer.install(destination, apply=True, source=new, upgrade_from=baseline)
                self.assertFalse((destination / "omni-analyst-accelerator").exists())
                for name in json.loads((new / "package.json").read_text())["skills"]:
                    self.assertEqual(installer.tree(destination / name, False), installer.tree(new / "skills" / name))
                self.assertEqual((unrelated / "custom.txt").read_text(), "Preserve me")
                again = installer.install(destination, apply=True, source=new, upgrade_from=baseline)
                self.assertTrue(all(row["action"] == "unchanged" for row in again["skills"]))

    def test_rename_refuses_customized_unverified_and_conflicting_main(self):
        for mode in ("customized", "extra_directory", "no_baseline", "conflicting_current"):
            with self.subTest(mode=mode):
                _, new, baseline, destination = self.rename_fixture(mode)
                legacy = destination / "omni-analyst-accelerator"
                if mode == "customized":
                    (legacy / "SKILL.md").write_text("Local customization")
                elif mode == "extra_directory":
                    (legacy / "personal-notes").mkdir()
                elif mode == "conflicting_current":
                    installer.shutil.copytree(new / "skills/omni-artifact-accelerator", destination / "omni-artifact-accelerator")
                before = installer.tree(destination, False)
                with self.assertRaises(ValueError):
                    installer.install(destination, apply=True, source=new,
                                      upgrade_from=None if mode == "no_baseline" else baseline)
                self.assertEqual(installer.tree(destination, False), before)

    def test_rename_rejects_unknown_predecessor_package_or_version(self):
        for mode in ("package", "version"):
            with self.subTest(mode=mode):
                old, new, _, destination = self.rename_fixture(mode)
                package = json.loads((old / "package.json").read_text())
                package["name" if mode == "package" else "version"] = "unrelated-package" if mode == "package" else "0.9.0"
                (old / "package.json").write_text(json.dumps(package))
                archive = self.archive(old, mode + ".zip")
                before = installer.tree(destination, False)
                with self.assertRaisesRegex(ValueError, "package/version mismatch"):
                    installer.install(destination, apply=True, source=new, upgrade_from=archive)
                self.assertEqual(installer.tree(destination, False), before)

    def test_rename_failure_restores_original_name_and_other_skills(self):
        for failed_skill in ("omni-artifact-accelerator", "omni-beta"):
            with self.subTest(failed_skill=failed_skill):
                _, new, baseline, destination = self.rename_fixture(failed_skill)
                package = json.loads((new / "package.json").read_text())
                package["skills"] = ["omni-gamma", "omni-artifact-accelerator", "omni-beta"]
                (new / "package.json").write_text(json.dumps(package))
                before = installer.tree(destination, False)
                real_rename = installer.os.rename
                def fail_replacement(src, dst):
                    if "new" in Path(src).parts and Path(dst).parent.name == failed_skill:
                        raise OSError("simulated renamed install failure")
                    return real_rename(src, dst)
                with mock.patch.object(installer.os, "rename", side_effect=fail_replacement):
                    with self.assertRaises(OSError):
                        installer.install(destination, apply=True, source=new, upgrade_from=baseline)
                self.assertEqual(installer.tree(destination, False), before)
                self.assertTrue((destination / "omni-analyst-accelerator").is_dir())
                self.assertFalse((destination / "omni-artifact-accelerator").exists())


if __name__ == "__main__":
    unittest.main()
