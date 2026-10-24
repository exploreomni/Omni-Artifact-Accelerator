#!/usr/bin/env python3
"""Prepare a pinned job request. No sandbox, execution or package acquisition.

Standard library only. A production launcher needs an independently installed,
human-authorized host gate. A request is never an approval token.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parent
MAX_SCENE = 1024 * 1024
TOOLCHAIN = ("model_core.py", "asset_checks.py", "worker.py", "quarantine.py")


def read_regular(path, limit):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or ".." in path.parts:
        raise ValueError("noncanonical_or_link_path")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("regular_bounded_file_required")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or len(raw) > limit or before.st_mtime_ns != after.st_mtime_ns:
        raise ValueError("file_changed_or_oversized")
    return raw


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def capabilities():
    return {"schema_version": 1, "kind": "spatial_harness_capabilities",
            "prepare": True, "execute": False, "promote": False,
            "package_acquisition": False, "host_fallback": False,
            "host_gate": "not_integrated", "isolation": "not_qualified",
            "reason": "explicit_runtime_signoff_and_qualified_host_gate_required"}


def prepare(scene_path):
    raw = read_regular(scene_path, MAX_SCENE)
    # Do not parse/compile arbitrary supplied scene data in the host coordinator.
    pins = {name: digest(read_regular(ROOT / name, MAX_SCENE)) for name in TOOLCHAIN}
    return {"schema_version": 1, "kind": "spatial_job_request", "scene_sha256": digest(raw),
            "scene_bytes": len(raw), "toolchain": pins,
            "operation": "compile_and_validate", "profile": "oaa-glb-untextured-v1",
            "required_isolation": {"boundary": "approved_disposable_vm",
                                   "network": "deny", "credentials": "none",
                                   "host_mounts": "none", "gpu": "deny",
                                   "root_filesystem": "read_only", "scratch": "ephemeral",
                                   "cpu_seconds": 30, "wall_seconds": 60,
                                   "memory_bytes": 536870912, "pids": 32,
                                   "scratch_bytes": 67108864, "output_bytes": 33554432},
            "limits_status": "proposed_enforcement_profile_not_host_verified",
            "authorization": "not_granted", "runtime_image": None,
            "status": "blocked", "blocker": capabilities()["reason"]}


def execute(_request=None, **_untrusted_options):
    # An imported function, CLI flag, environment variable or caller JSON cannot
    # prove a human grant or isolation. No dynamic runner/plugin escape hatch.
    raise PermissionError("execution_blocked: qualified_host_gate_unavailable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    p = sub.add_parser("prepare")
    p.add_argument("--scene", required=True)
    sub.add_parser("execute")
    sub.add_parser("promote")
    args = parser.parse_args()
    try:
        if args.command in {"execute", "promote"}:
            execute()
        value = capabilities() if args.command == "capabilities" else prepare(args.scene)
        print(json.dumps(value, indent=2))
        return 0
    except (ValueError, OSError):
        # No source paths or input values in error messages.
        print(json.dumps({"status": "blocked", "reason": "request_or_host_gate_unavailable"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
