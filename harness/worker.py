"""Original pure worker functions, for a separately qualified isolated host.

No command-line execution route. Unit tests use only authored synthetic scenes.
Importing these functions does not establish isolation or execution permission.
"""
import hashlib
import json


def _unique(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False, ensure_ascii=True) + "\n").encode()


def compile_bytes(raw, compiler, validator):
    """Host passes pinned first-party compiler/validator, never names from input.

    The production host must independently validate outputs in another isolated
    worker. This result is local structural evidence, not a promotion receipt.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError("scene_byte_limit")
    try:
        spec = json.loads(raw, object_pairs_hook=_unique,
                          parse_constant=lambda _v: (_ for _ in ()).throw(ValueError("nonfinite_json")))
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_scene_json") from exc
    result = compiler(spec)
    summary = validator(result["glb"])
    scene = encode(result["scene"])
    manifest = {"schema_version": 1, "kind": "spatial_candidate_manifest",
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "scene_sha256": hashlib.sha256(scene).hexdigest(),
                "glb_sha256": hashlib.sha256(result["glb"]).hexdigest(),
                "model": result["manifest"], "validation": summary,
                "evidence_lane": "local_structure_only", "host_isolation": "not_attested",
                "native_verification": "not_run", "visual_verification": "not_run"}
    return {"model.glb": result["glb"], "scene.json": scene, "manifest.json": encode(manifest)}


if __name__ == "__main__":
    raise SystemExit("blocked: use a separately qualified and authorized isolated host")
