"""Bounded first-party byte-copy mechanics for a trusted isolated validator.

These functions do not authenticate approval or authorize publication. No CLI
promotion route exists. The production broker must keep its roots inaccessible
to the worker and authenticate its independent validation result.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

FILES = {"model.glb": 16 * 1024 * 1024, "scene.json": 1024 * 1024,
         "manifest.json": 2 * 1024 * 1024}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("nonfinite_json")


def inspect_outputs(outputs, validator, compiler, expected_input):
    """Recompute derived claims from original bytes held by the trusted caller.

    Run this parser/compiler only inside the separately isolated validation
    worker. Neither this comparison nor the caller's digest grants authority.
    """
    if type(expected_input) is not bytes or not 0 < len(expected_input) <= 1024 * 1024:
        raise ValueError("expected_input_bytes_required")
    expected_input_sha256 = hashlib.sha256(expected_input).hexdigest()
    if type(outputs) is not dict or set(outputs) != set(FILES):
        raise ValueError("output_set_invalid")
    for name, raw in outputs.items():
        if type(raw) is not bytes or not 0 < len(raw) <= FILES[name]:
            raise ValueError("output_limit")
    # The caller supplies pinned code; job data never chooses a validator.
    structure = validator(outputs["model.glb"])
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in outputs.items()}
    try:
        from_json = json.loads(outputs["manifest.json"], object_pairs_hook=_unique, parse_constant=_invalid_constant)
        scene = json.loads(outputs["scene.json"], object_pairs_hook=_unique, parse_constant=_invalid_constant)
        original = json.loads(expected_input, object_pairs_hook=_unique, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("output_json_invalid") from exc
    if (type(from_json) is not dict or type(scene) is not dict
            or from_json.get("schema_version") != 1
            or from_json.get("kind") != "spatial_candidate_manifest"
            or from_json.get("input_sha256") != expected_input_sha256
            or from_json.get("glb_sha256") != hashes["model.glb"]
            or from_json.get("scene_sha256") != hashes["scene.json"]):
        raise ValueError("output_binding_mismatch")
    # A worker can change scene.json and its own hash together, or echo a public
    # input digest. Recompile the original host-held input, not worker claims.
    reconstructed = compiler(original)
    if (reconstructed["glb"] != outputs["model.glb"]
            or reconstructed["scene"] != scene
            or reconstructed["manifest"] != from_json.get("model")
            or structure != from_json.get("validation")):
        raise ValueError("output_reconstruction_mismatch")
    expected_fields = {"schema_version", "kind", "input_sha256", "scene_sha256", "glb_sha256",
                       "model", "validation", "evidence_lane", "host_isolation",
                       "native_verification", "visual_verification"}
    if (set(from_json) != expected_fields or from_json["evidence_lane"] != "local_structure_only"
            or from_json["host_isolation"] != "not_attested"
            or from_json["native_verification"] != "not_run"
            or from_json["visual_verification"] != "not_run"):
        raise ValueError("unsupported_worker_claim")
    return {"hashes": hashes, "structure": structure,
            "status": "structurally_checked", "promotion_authorized": False}


def copy_exact(outputs, destination, expected_hashes):
    """Copy exact inspected bytes to a fresh private directory; not promotion.

    No overwrite, links or worker-selected paths. Files stay untrusted unless
    the host has separately authenticated validation and granted consumption.
    """
    if (type(outputs) is not dict or set(outputs) != set(FILES)
            or type(expected_hashes) is not dict or set(expected_hashes) != set(FILES)):
        raise ValueError("output_set_invalid")
    for name, raw in outputs.items():
        if (type(raw) is not bytes or not 0 < len(raw) <= FILES[name]
                or hashlib.sha256(raw).hexdigest() != expected_hashes[name]):
            raise ValueError("output_changed")
    destination = Path(destination).absolute()
    if ".." in destination.parts or any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError("output_path_invalid")
    # Trusted parent must be exclusive to the host. Descriptor-relative writes
    # protect entry names; host root ownership is not proven by this helper.
    parent = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    folder = None
    created = []
    try:
        os.mkdir(destination.name, mode=0o700, dir_fd=parent)
        folder = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        for name in sorted(outputs):
            fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
            created.append(name)
            with os.fdopen(fd, "w+b") as stream:
                stream.write(outputs[name])
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                raw = stream.read(FILES[name] + 1)
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or hashlib.sha256(raw).hexdigest() != expected_hashes[name]:
                    raise ValueError("copy_hash_mismatch")
    except BaseException:
        if folder is not None:
            for name in created:
                os.unlink(name, dir_fd=folder)
            os.rmdir(destination.name, dir_fd=parent)
        raise
    finally:
        if folder is not None:
            os.close(folder)
        os.close(parent)
    return {"status": "copied_unpromoted", "hashes": dict(expected_hashes),
            "promotion_authorized": False}
