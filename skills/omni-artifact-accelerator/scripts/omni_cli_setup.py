"""Choose an Omni connection using the host's MCP discovery and local CLI inventory.

Staging checks a host-acquired archive and writes one inert payload. The host owns
permission, acquisition, installation and execution. No network or subprocess here.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import re
import shutil
import stat
import sys
import tarfile
import zipfile


REPOSITORY = "https://github.com/exploreomni/cli"
RELEASE_API = "https://api.github.com/repos/exploreomni/cli/releases/latest"
MAX_BYTES = 128 * 1024 * 1024


def inspect_cli():
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    machine = platform.machine().lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    member = "omni.exe" if system == "windows" else "omni"
    destination = Path.home() / ".local" / "bin" / member
    details = {"os": system, "arch": arch, "member": member, "destination": str(destination)}
    if system == "windows":
        details["version_check"] = "host_preview_only" if arch == "amd64" else "unavailable_for_architecture"
        details["bounded_adapter"] = "unavailable_native_windows"
    configured = os.environ.get("OAA_OMNI_CLI_PATH")
    if configured:
        return dict(details, status="inspect_configured_cli", path=configured)
    if any(os.environ.get(key) for key in ("OAA_OMNI_CLI_SHA256", "OAA_OMNI_RUNTIME_PATH", "OAA_OMNI_RUNTIME_SHA256")):
        return dict(details, status="inspect_incomplete_pin")
    # Inventory only. PATH can contain an unrelated program with the same name.
    found = shutil.which(member)
    if found or os.path.lexists(destination):
        return dict(details, status="inspect_existing_cli", path=found or str(destination))
    if not system or not arch or (system == "windows" and arch != "amd64"):
        return dict(details, status="unsupported_platform")
    if any(parent.is_symlink() or (parent.exists() and not parent.is_dir())
           for parent in destination.parents):
        return dict(details, status="inspect_destination")
    return dict(details, status="prepare_install_offer", release_metadata_url=RELEASE_API)


def local_setup(route="auto", *, mcp_tool=None, mcp_checked=False):
    if route in ("api", "offline"):
        return {"status": "cli_not_needed", "route": route}
    if route == "cli":
        return inspect_cli()
    # Only the host can see its connector registry and match a tool to the operation.
    if mcp_tool is not None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,256}", mcp_tool):
            raise ValueError("Expected an Omni MCP tool identifier from the host registry")
        return {"status": "use_mcp", "route": "mcp", "tool": mcp_tool}
    if route == "mcp":
        return {"status": "mcp_operation_unavailable" if mcp_checked else "inspect_host_mcp",
                "route": "mcp"}
    cli = inspect_cli()
    if cli["status"] in ("inspect_existing_cli", "inspect_configured_cli"):
        return dict(cli, route="cli")
    return {"status": "choose_connection" if mcp_checked else "inspect_host_mcp",
            "route": "auto", "cli_status": cli["status"]}


def read_bounded(path, limit):
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Expected a regular file within the input size limit")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Input exceeds size limit")
    return data


def windows_version_preview(setup):
    """Inspect one host-pinned EXE and describe a credential-free version check. Never launch it."""
    if setup.get("os") != "windows" or setup.get("arch") != "amd64":
        raise ValueError("The version preview requires a native Windows x64 host")
    if setup["status"] != "inspect_configured_cli":
        raise ValueError("Select the verified omni.exe with OAA_OMNI_CLI_PATH and OAA_OMNI_CLI_SHA256")
    if any(os.environ.get(k) for k in ("OAA_OMNI_RUNTIME_PATH", "OAA_OMNI_RUNTIME_SHA256")):
        raise ValueError("The Windows version preview requires a direct executable without an interpreter")
    expected = os.environ.get("OAA_OMNI_CLI_SHA256", "")
    if not re.fullmatch("[a-f0-9]{64}", expected):
        raise ValueError("Expected an explicit installed binary SHA-256")
    name = PureWindowsPath(setup["path"])
    if (not name.is_absolute() or not re.fullmatch("[A-Za-z]:", name.drive)
            or name.name.casefold() != "omni.exe" or ".." in name.parts
            or any(part.endswith((" ", ".")) or re.search(r'[<>:"|?*\x00-\x1f]', part)
                   or PureWindowsPath(part).is_reserved() for part in name.parts[1:])):
        raise ValueError("Select omni.exe by an absolute local drive path without aliases")
    path = Path(setup["path"])
    if sys.platform != "win32":
        raise ValueError("Inspect the executable on the intended Windows host")
    # The reader pins every directory handle and the final file while reading.
    # Launch is separate; the executing host must protect and recheck the pin.
    check_windows_image(read_windows_binary(path), expected)
    return {
        "status": "windows_version_preview", "route": "cli", "executed": False,
        "argv": [str(path), "--version"], "observed_binary_sha256": expected,
        "host_requirements": {
            "shell": False, "stdin": "closed", "timeout_seconds": 10,
            "max_stdout_bytes": 4096, "max_stderr_bytes": 4096,
            "on_limit_or_timeout": "terminate_process_tree",
            "stderr": "discard", "credentials": "none",
            "profile_and_temp": "private_empty_directories",
            "inherit_environment": False, "environment_overrides": {"OMNI_NO_UPDATE_NOTIFIER": "1"},
            "executable": "verify_official_origin_and_protect_pinned_path_through_launch",
        },
        "bounded_adapter": "unavailable_native_windows",
    }


def read_windows_binary(path):
    source = Path(__file__).with_name("windows_files.py")
    spec = importlib.util.spec_from_file_location("oaa_setup_windows_files", source)
    windows_files = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(windows_files)
    return windows_files.read_path(path, MAX_BYTES)


def check_windows_image(image, expected):
    if hashlib.sha256(image).hexdigest() != expected:
        raise ValueError("Installed Windows CLI binary pin differs")
    pe = int.from_bytes(image[60:64], "little")
    if len(image) < 64 or image[:2] != b"MZ" or pe < 64 or image[pe:pe + 6] != b"PE\0\0\x64\x86":
        raise ValueError("Expected a Windows x64 PE image")


def release_plan(setup, release):
    if setup["status"] != "prepare_install_offer":
        raise ValueError("Resolve the current setup status before offering installation")
    tag = release.get("tag_name")
    if (not isinstance(tag, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag)
            or release.get("draft") is not False or release.get("prerelease") is not False
            or release.get("html_url") != f"{REPOSITORY}/releases/tag/{tag}"):
        raise ValueError("Expected stable release metadata from exploreomni/cli")
    suffix = "zip" if setup["os"] == "windows" else "tar.gz"
    filename = f"omni_{tag[1:]}_{setup['os']}_{setup['arch']}.{suffix}"
    url = f"{REPOSITORY}/releases/download/{tag}/{filename}"
    listing = release.get("assets")
    if not isinstance(listing, list):
        raise ValueError("Expected a release asset list")
    assets = [a for a in listing if isinstance(a, dict) and a.get("name") == filename]
    if len(assets) != 1 or assets[0].get("browser_download_url") != url:
        raise ValueError("Expected exactly one matching official release archive")
    digest = assets[0].get("digest")
    if not isinstance(digest, str) or not re.fullmatch("sha256:[a-f0-9]{64}", digest):
        raise ValueError("An official SHA-256 release asset digest is required")
    plan = {"status": "awaiting_host_permission", "tag": tag, "archive": filename,
            "url": url, "archive_sha256": digest[7:], "member": setup["member"],
            "destination": setup["destination"], "actions": ["acquire", "verify", "install_new", "version_check"]}
    plan["plan_sha256"] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    return plan


def stage_archive(plan, expected_plan, archive, directory):
    if sys.platform == "win32":
        raise ValueError("Windows installation requires a qualified host to verify private ACLs and stage the binary")
    if plan["plan_sha256"] != expected_plan:
        raise ValueError("Release or destination changed since the install offer")
    raw = read_bounded(archive, MAX_BYTES)
    if hashlib.sha256(raw).hexdigest() != plan["archive_sha256"]:
        raise ValueError("Archive SHA-256 differs from the selected release")
    member = plan["member"]
    if plan["archive"].endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw)) as pack:
            entries = [e for e in pack.infolist() if e.filename == member]
            if (len(entries) != 1 or stat.S_IFMT(entries[0].external_attr >> 16) not in (0, stat.S_IFREG)
                    or not 0 < entries[0].file_size <= MAX_BYTES):
                raise ValueError("Expected a single regular CLI binary")
            payload = pack.read(entries[0])
    else:
        # Bound the expanded tar, including non-binary members and padding.
        tar_limit = MAX_BYTES + 8 * 1024 * 1024
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
            unpacked = compressed.read(tar_limit + 1)
        if len(unpacked) > tar_limit:
            raise ValueError("Expanded release archive exceeds size limit")
        with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as pack:
            entries = [e for e in pack if e.name == member]
            if len(entries) != 1 or not entries[0].isfile() or not 0 < entries[0].size <= MAX_BYTES:
                raise ValueError("Expected a single regular CLI binary")
            payload = pack.extractfile(entries[0]).read()
    if not directory.is_absolute() or directory.resolve(strict=True) != directory or not directory.is_dir():
        raise ValueError("Use a canonical private staging directory")
    if os.name == "posix" and (directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077):
        raise ValueError("Staging requires a user-owned private directory")
    path = directory / "omni.payload"
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o600), "wb") as out:
        out.write(payload)
    return {"status": "verified_payload_staged", "path": str(path),
            "binary_sha256": hashlib.sha256(payload).hexdigest(), "destination": plan["destination"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=("auto", "cli", "mcp", "api", "offline"), default="auto")
    inventory = parser.add_mutually_exclusive_group()
    inventory.add_argument("--omni-mcp-tool", metavar="NAME",
                           help="Actual tool the host found on its Omni connection for the next operation")
    inventory.add_argument("--no-matching-omni-mcp-tool", action="store_true",
                           help="Host checked its Omni tools and found none covering the next operation")
    parser.add_argument("--release-metadata", type=Path, help="Official release API JSON obtained by the host")
    parser.add_argument("--archive", type=Path, help="Archive acquired by the authorized host")
    parser.add_argument("--stage-in", type=Path, help="Private directory on the destination filesystem")
    parser.add_argument("--plan-sha256", help="Bind staging to the exact reviewed plan (integrity only)")
    parser.add_argument("--preview-windows-version", action="store_true",
                        help="Inspect the pinned Windows x64 omni.exe and return a host-run version plan")
    args = parser.parse_args()
    staging = (args.archive, args.stage_in, args.plan_sha256)
    if any(staging) and not (all(staging) and args.release_metadata):
        parser.error("Staging requires --release-metadata, --archive, --stage-in and --plan-sha256 together")
    if args.release_metadata and args.route != "cli":
        parser.error("Release setup applies only to the CLI route")
    if args.preview_windows_version and (args.route != "cli" or args.release_metadata
                                        or args.omni_mcp_tool or args.no_matching_omni_mcp_tool):
        parser.error("Use the Windows version preview with --route cli and no installation or MCP options")
    try:
        result = local_setup(args.route, mcp_tool=args.omni_mcp_tool,
                             mcp_checked=args.no_matching_omni_mcp_tool)
        if args.preview_windows_version:
            result = windows_version_preview(result)
        if args.release_metadata:
            release = json.loads(read_bounded(args.release_metadata, 2 * 1024 * 1024))
            if not isinstance(release, dict):
                raise ValueError("Expected a release object")
            result = release_plan(result, release)
            if args.archive:
                result = stage_archive(result, args.plan_sha256, args.archive, args.stage_in)
        print(json.dumps(result, indent=2))
    except (ValueError, TypeError, KeyError, OSError, EOFError, tarfile.TarError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Omni setup: {exc}\n")


if __name__ == "__main__":
    main()
