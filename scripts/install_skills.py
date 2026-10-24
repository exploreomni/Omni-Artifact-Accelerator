#!/usr/bin/env python3
"""Preview/install skills, or upgrade exact baseline files without losing customizations.

The archive manifest establishes byte consistency, not publisher authenticity.
Apply uses a cooperating-installer lock and rollback for caught failures. It is
not a crash-atomic bundle transaction; do not edit installed skills during apply.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE = 10 * 1024 * 1024
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_ENTRIES = 4096
PACKAGE_NAME = "omni-artifact-accelerator"
PREDECESSOR_NAME = "omni-analyst-accelerator"
PREDECESSOR_VERSIONS = {"0.1.0", "0.2.0"}
# This is a reviewed package rename, never archive-supplied destination metadata.
SKILL_RENAMES = {"omni-analyst-accelerator": "omni-artifact-accelerator"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_path(path):
    path = Path(path).absolute()
    need(".." not in path.parts and not any(p.is_symlink() for p in (path, *path.parents)),
         "use canonical paths without symlinks or parent traversal")
    return path


def read_regular(path, limit=MAX_FILE):
    path = canonical_path(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_size <= limit, "invalid or oversized regular file")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    need(len(raw) == before.st_size <= limit and before.st_mtime_ns == after.st_mtime_ns,
         "file changed while reading")
    return raw


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON metadata") from exc


def package_info(raw):
    value = decode(raw)
    need(type(value) is dict and type(value.get("name")) is str and value["name"] and
         type(value.get("version")) is str and value["version"], "invalid package metadata")
    names = value.get("skills")
    need(type(names) is list and names and all(type(n) is str and
         re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", n) for n in names), "invalid bundle skill list")
    need(len(names) == len(set(names)), "duplicate bundle skill")
    return value


def generated(path):
    return "__pycache__" in path.parts or path.name == ".DS_Store" or path.suffix == ".pyc"


def tree(path, ignore_generated=True):
    """Hash files and record directories, including empty customization folders."""
    path = canonical_path(path)
    need(path.is_dir(), "skill directory missing")
    result = {}
    for item in sorted(path.rglob("*")):
        if ignore_generated and generated(item.relative_to(path)):
            continue
        need(not item.is_symlink(), "symlink in skill tree")
        relative = item.relative_to(path).as_posix()
        mode = item.lstat().st_mode
        if stat.S_ISDIR(mode):
            result[relative + "/"] = None
        else:
            need(stat.S_ISREG(mode), "non-regular entry in skill tree")
            result[relative] = hashlib.sha256(read_regular(item)).hexdigest()
    return result


def safe_member(name, directory=False):
    need(type(name) is str and name and "\\" not in name and ":" not in name and
         not any(ord(c) < 32 for c in name), "unsafe archive path")
    value = name[:-1] if directory and name.endswith("/") else name
    parts = value.split("/")
    need(all(p and p not in (".", "..") for p in parts) and
         not PurePosixPath(value).is_absolute(), "noncanonical archive path")
    return value


def parents_of(paths):
    return {p.as_posix() for path in paths for p in PurePosixPath(path).parents if p.as_posix() != "."}


def filesystem_key(path):
    return unicodedata.normalize("NFC", path).casefold()


def baseline_archive(path, expected_package):
    """Verify every archived file without extraction or trusting ZIP path aliases."""
    raw = read_regular(path, MAX_ARCHIVE)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            need(0 < len(infos) <= MAX_ENTRIES, "archive entry limit")
            files, directories, folded, total = {}, set(), set(), 0
            for info in infos:
                name = safe_member(info.filename, info.is_dir())
                need(filesystem_key(name) not in folded, "duplicate or filesystem-ambiguous archive path")
                folded.add(filesystem_key(name))
                kind = stat.S_IFMT(info.external_attr >> 16)
                need(kind in (0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG),
                     "archive contains non-regular entry")
                need(not info.flag_bits & 1, "encrypted baseline archive unsupported")
                if info.is_dir():
                    need(info.file_size == 0, "invalid archive directory")
                    directories.add(name)
                    continue
                total += info.file_size
                need(0 <= info.file_size <= MAX_FILE and total <= MAX_ARCHIVE, "archive expanded-size limit")
                with archive.open(info) as stream:
                    content = stream.read(MAX_FILE + 1)
                need(len(content) == info.file_size, "archive size mismatch")
                files[name] = content
            need(files and len({n.split('/')[0] for n in files}) == 1 and
                 all('/' in n for n in files), "archive must have one package root")
            implied_dirs = parents_of(files)
            dir_keys = {filesystem_key(n) for n in implied_dirs}
            need(len(dir_keys) == len(implied_dirs) and
                 not {filesystem_key(n) for n in files} & dir_keys and directories <= implied_dirs,
                 "archive file/directory ambiguity")
            prefix = next(iter(files)).split('/')[0] + '/'
            payload = {n[len(prefix):]: content for n, content in files.items()}
            need("MANIFEST.json" in payload and "package.json" in payload, "missing archive manifest/package")
            manifest = decode(payload["MANIFEST.json"])
            package = package_info(payload["package.json"])
            predecessor = (expected_package == PACKAGE_NAME and package["name"] == PREDECESSOR_NAME and
                           package["version"] in PREDECESSOR_VERSIONS)
            need((package["name"] == expected_package or predecessor) and type(manifest) is dict and
                 manifest.get("package") == package["name"] and
                 manifest.get("version") == package["version"], "baseline package/version mismatch")
            records = manifest.get("files")
            need(type(records) is list, "invalid archive manifest")
            declared, aliases = set(), set()
            for record in records:
                need(type(record) is dict, "invalid manifest file record")
                name = safe_member(record.get("path"))
                need(name != "MANIFEST.json" and filesystem_key(name) not in aliases, "ambiguous manifest path")
                aliases.add(filesystem_key(name))
                declared.add(name)
                need(name in payload and type(record.get("bytes")) is int and
                     record["bytes"] == len(payload[name]) and
                     type(record.get("sha256")) is str and
                     re.fullmatch(r"[a-f0-9]{64}", record["sha256"]) and
                     record["sha256"] == hashlib.sha256(payload[name]).hexdigest(),
                     "baseline manifest hash/size mismatch")
            need(declared == set(payload) - {"MANIFEST.json"}, "manifest does not cover exact archive contents")
            names = package["skills"]
            if predecessor:
                need(all(old in names and new not in names for old, new in SKILL_RENAMES.items()),
                     "predecessor archive has an unexpected skill rename layout")
            need(all(len(n.split('/')) >= 3 and n.split('/')[1] in names
                     for n in payload if n.startswith("skills/")), "undeclared archived skill")
            trees = {}
            for name in names:
                skill_prefix = "skills/" + name + "/"
                selected = {n[len(skill_prefix):]: hashlib.sha256(content).hexdigest()
                            for n, content in payload.items() if n.startswith(skill_prefix)}
                need("SKILL.md" in selected, "baseline skill entrypoint missing")
                selected.update({n + '/': None for n in parents_of(selected)})
                trees[name] = selected
            return {"package": package["name"], "version": package["version"],
                    "sha256": hashlib.sha256(raw).hexdigest(), "trees": trees,
                    "skill_renames": dict(SKILL_RENAMES) if predecessor else {}}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ValueError("invalid or unsupported baseline archive") from exc


def existing_tree(path):
    if not os.path.lexists(path):
        return None
    need(not path.is_symlink() and path.is_dir(), "unsafe existing skill destination")
    return tree(path, ignore_generated=False)


def partial_tree(expected, children):
    return {p: value for p, value in expected.items() if p.split('/')[0] in children}


def apply_actions(destination, source, actions, expected, previous):
    lock = destination / ".omni-analyst-install.lock"
    lock_fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(lock_fd)
    staged, changes, preserve = None, [], False
    try:
        staged = Path(tempfile.mkdtemp(prefix=".omni-analyst-install-", dir=destination))
        (staged / "new").mkdir()
        (staged / "backup").mkdir()
        for action in actions:
            name = action["skill"]
            if action["action"] == "unchanged":
                continue
            shutil.copytree(source / "skills" / name, staged / "new" / name,
                            symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            need(tree(staged / "new" / name, False) == expected[name] == tree(source / "skills" / name),
                 "source changed or staged copy differs: " + name)
        # Recheck the whole bundle before the first mutation.
        for name, prior in previous.items():
            need(existing_tree(destination / name) == prior, "installed skill changed during planning: " + name)
        for action in actions:
            name = action["skill"]
            if action["action"] == "unchanged":
                continue
            original_name = action.get("from_skill", name)
            target, original = destination / name, destination / original_name
            backup = staged / "backup" / original_name
            need(existing_tree(target) == previous[name], "installed skill changed during apply: " + name)
            need(existing_tree(original) == previous[original_name],
                 "installed skill changed during apply: " + original_name)
            change = {"name": name, "target": target, "original": original,
                      "backup": backup, "inode": None, "children": set()}
            changes.append(change)
            if previous[original_name] is not None:
                os.rename(original, backup)
            target.mkdir()  # Reserve an absent destination; never replace a competing directory.
            change["inode"] = target.stat().st_ino
            for child in sorted((staged / "new" / name).iterdir()):
                os.rename(child, target / child.name)
                change["children"].add(child.name)
            need(tree(target, False) == expected[name], "installed tree differs: " + name)
    except Exception as original:
        failures = []
        for change in reversed(changes):
            try:
                target, name = change["target"], change["name"]
                if change["inode"] is not None:
                    need(not target.is_symlink() and target.stat().st_ino == change["inode"] and
                         tree(target, False) == partial_tree(expected[name], change["children"]),
                         "destination changed externally; preserving recovery files")
                    shutil.rmtree(target)
                if change["backup"].exists():
                    need(not os.path.lexists(change["original"]), "destination occupied; preserving backup")
                    os.rename(change["backup"], change["original"])
            except Exception as rollback_error:
                failures.append(str(rollback_error))
        if failures:
            preserve = True
            raise RuntimeError("install failed and rollback needs manual recovery; backups retained at " + str(staged)) from original
        raise
    finally:
        if staged is not None and not preserve:
            shutil.rmtree(staged)
        lock.unlink()


def install(destination, apply=False, source=ROOT, upgrade_from=None):
    if apply:
        raise ValueError("activation_blocked: no qualified host approval gate; preview/verify only")
    return _plan_install(destination, source, upgrade_from)


def _plan_install(destination, source=ROOT, upgrade_from=None):
    """Read-only planning. Repository code cannot authenticate an operator."""
    destination, source = canonical_path(destination), canonical_path(source)
    need(destination.is_dir(), "destination directory must already exist")
    package = package_info(read_regular(source / "package.json"))
    baseline = baseline_archive(upgrade_from, package["name"]) if upgrade_from is not None else None
    actions, expected, previous = [], {}, {}
    renames = SKILL_RENAMES if package["name"] == PACKAGE_NAME else {}
    active_renames = {}
    for old, new in renames.items():
        if new not in package["skills"]:
            continue
        need(old not in package["skills"], "bundle contains both names of a renamed skill")
        previous[old] = existing_tree(destination / old)
        if previous[old] is not None:
            need(not os.path.lexists(destination / new),
                 "conflicting old and new skill destinations; no files changed: " + old + ", " + new)
            need(baseline is not None and baseline["skill_renames"].get(old) == new and
                 previous[old] == baseline["trees"].get(old),
                 "customized or unverified predecessor skill; no files changed: " + old)
            active_renames[new] = old
    baseline_names = {new: old for old, new in baseline["skill_renames"].items()} if baseline else {}
    need(all(new in package["skills"] for new in baseline_names), "renamed skill missing from source package")
    for name in package["skills"]:
        src, dst = source / "skills" / name, destination / name
        need(not src.is_symlink() and (src / "SKILL.md").is_file(), "missing or unsafe source skill: " + name)
        expected[name], previous[name] = tree(src), existing_tree(dst)
        if name in active_renames:
            action = "rename_upgrade"
        elif previous[name] is None:
            action = "install"
        elif previous[name] == expected[name]:
            action = "unchanged"
        else:
            need(baseline is not None and previous[name] == baseline["trees"].get(baseline_names.get(name, name)),
                 "customized or unrelated existing skill; no files changed: " + name)
            action = "upgrade"
        record = {"skill": name, "action": action}
        if name in active_renames:
            record["from_skill"] = active_renames[name]
        actions.append(record)
    return {"applied": False, "destination": str(destination), "skills": actions,
            "baseline": None if baseline is None else {"package": baseline["package"],
                                                        "version": baseline["version"], "sha256": baseline["sha256"],
                                                        "publisher_authenticated": False}}


def verify(destination, source=ROOT):
    """Read-only comparison, including added files; package identity is not publisher trust."""
    destination, source = canonical_path(destination), canonical_path(source)
    need(destination.is_dir(), "destination directory must already exist")
    package_raw = read_regular(source / "package.json")
    package = package_info(package_raw)
    records, source_trees = [], {}
    for name in package["skills"]:
        expected = tree(source / "skills" / name)
        source_trees[name] = expected
        actual = existing_tree(destination / name)
        actual = {} if actual is None else actual
        records.append({"skill": name,
                        "missing": sorted(set(expected) - set(actual)),
                        "changed": sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p]),
                        "extra": sorted(set(actual) - set(expected))})
    matching = all(not any(r[k] for k in ("missing", "changed", "extra")) for r in records)
    identity = {"package_sha256": hashlib.sha256(package_raw).hexdigest(), "skills": source_trees}
    return {"status": "matching" if matching else "drift", "applied": False,
            "package": package["name"], "version": package["version"],
            "source_manifest_sha256": hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
            "destination": str(destination), "skills": records, "publisher_authenticated": False,
            "host_activation_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Disabled pending a qualified host approval gate")
    mode.add_argument("--verify", action="store_true", help="Read-only exact source/install comparison; exit 1 on drift")
    parser.add_argument("--upgrade-from", type=Path, help="Exact previous bundle ZIP with a verified file manifest")
    args = parser.parse_args()
    try:
        need(not (args.verify and args.upgrade_from), "verify does not use an upgrade baseline")
        result = verify(args.destination) if args.verify else install(args.destination, args.apply, upgrade_from=args.upgrade_from)
        print(json.dumps(result, indent=2))
        return 1 if args.verify and result["status"] != "matching" else 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        parser.exit(2, "error: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
