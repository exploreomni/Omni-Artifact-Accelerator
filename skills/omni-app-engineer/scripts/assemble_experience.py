#!/usr/bin/env python3
"""Assemble explicitly selected local sources. No execution, fetching or native writes."""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024
NAME = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
TOKEN = re.compile(r"\{\{OAA:([A-Z][A-Z0-9_]{0,63})\}\}")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def invalid(_):
        raise ValueError("nonfinite JSON number")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid JSON encoding or depth") from exc


def relative(value):
    need(isinstance(value, str) and value and "\\" not in value and
         not any(ord(c) < 32 for c in value), "canonical relative path required")
    path = PurePosixPath(value)
    need(not path.is_absolute() and path.as_posix() == value and
         all(p not in {".", "..", ""} and ":" not in p for p in path.parts),
         "canonical relative path required")
    return path


def local_path(root, value):
    path = root
    for part in relative(value).parts:
        path = path / part
        need(not path.is_symlink(), "symlink not allowed")
    need(path.resolve().is_relative_to(root), "path outside project")
    return path


def fields(value, required, optional=()):
    need(type(value) is dict and set(required) <= value.keys() and
         value.keys() <= set(required) | set(optional), "unsupported or missing fields")


def assemble(root, manifest_path):
    root = Path(root).resolve(strict=True)
    need(root.is_dir(), "project directory required")
    source = local_path(root, manifest_path)
    need(source.is_file() and source.stat().st_size <= 256 * 1024, "manifest missing or oversized")
    manifest_bytes = source.read_bytes()
    spec = decode(manifest_bytes)
    fields(spec, ("schema_version", "template", "slots"), ("references", "max_output_bytes"))
    need(type(spec["schema_version"]) is int and spec["schema_version"] == 1, "unsupported manifest version")
    limit = spec.get("max_output_bytes", MAX_OUTPUT)
    need(type(limit) is int and 0 < limit <= MAX_OUTPUT, "invalid output budget")
    need(type(spec["slots"]) is list and len(spec["slots"]) <= 64, "invalid slot count")
    references = spec.get("references", [])
    need(type(references) is list and len(references) <= 32, "invalid references")
    inputs, total = [], 0

    def read(item, role):
        nonlocal total
        need(isinstance(item.get("sha256"), str) and re.fullmatch(r"[a-f0-9]{64}", item["sha256"]),
             "input hash required")
        path = local_path(root, item.get("path"))
        need(path.is_file() and path.stat().st_size <= MAX_FILE, "input missing or oversized")
        raw = path.read_bytes()
        total += len(raw)
        need(total <= MAX_TOTAL and len(raw) <= MAX_FILE, "input budget exceeded")
        need(hashlib.sha256(raw).hexdigest() == item["sha256"], "input hash changed: " + item["path"])
        inputs.append({"role": role, "path": item["path"], "bytes": len(raw), "sha256": item["sha256"]})
        return raw

    fields(spec["template"], ("path", "sha256"))
    template = read(spec["template"], "template").decode("utf-8")
    matches = list(TOKEN.finditer(template))
    names = [m.group(1) for m in matches]
    need(len(names) == len(set(names)), "each template slot must occur exactly once")
    slots, scripts, globals_seen = {}, [], set()
    for item in spec["slots"]:
        fields(item, ("name", "kind", "path", "sha256"), ("script_type", "requires", "provides", "mime"))
        name, kind = item["name"], item["kind"]
        need(isinstance(name, str) and NAME.fullmatch(name) and name not in slots, "invalid or duplicate slot name")
        need(type(kind) is str and kind in {"script", "style", "json", "asset"}, "unsupported slot kind")
        need(kind == "script" or not ({"script_type", "requires", "provides"} & item.keys()),
             "script metadata on non-script")
        need(kind == "asset" or "mime" not in item, "asset metadata on non-asset")
        raw = read(item, name)
        if kind == "asset":
            mime = item.get("mime")
            valid = ((mime == "image/png" and raw.startswith(b"\x89PNG\r\n\x1a\n")) or
                     (mime == "image/jpeg" and raw.startswith(b"\xff\xd8\xff")) or
                     (mime == "image/webp" and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"))
            need(valid, "unsupported asset type or signature")
            value = "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")
        else:
            value = raw.decode("utf-8")
            if kind == "json":
                value = json.dumps(decode(raw), ensure_ascii=True, allow_nan=False, separators=(",", ":"))
                value = value.replace("<", "\\u003c").replace("&", "\\u0026")
                value = '<script type="application/json" id="' + name + '">' + value + '</script>'
            elif kind == "style":
                need(not re.search(r"</style\b", value, re.I), "style contains an HTML closing tag")
                value = "<style>" + value + "</style>"
            else:
                need(item.get("script_type") == "classic", "explicit classic script_type required; module bundling is external")
                need(not re.search(r"</script\b|<!--|<script\b", value, re.I), "script contains HTML tokenizer delimiters")
                requires, provides = item.get("requires", []), item.get("provides", [])
                need(type(requires) is list and all(isinstance(n, str) for n in requires) and
                     len(requires) == len(set(requires)) and set(requires) <= set(scripts),
                     "scripts require earlier declared script slots")
                need(type(provides) is list and all(isinstance(n, str) and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", n)
                                                  for n in provides), "invalid declared globals")
                need(len(provides) == len(set(provides)) and not globals_seen.intersection(provides), "declared global collision")
                globals_seen.update(provides)
                scripts.append(name)
                value = "<script>" + value + "</script>"
        slots[name] = value
    need(set(slots) == set(names), "template and manifest slots differ")
    need([name for name in names if name in scripts] == scripts, "template changes declared script order")
    reference_roles = set()
    for ref in references:
        fields(ref, ("role", "path", "sha256"))
        need(isinstance(ref["role"], str) and ref["role"].strip() and ref["role"] not in reference_roles,
             "reference roles must be distinct")
        reference_roles.add(ref["role"])
        read(ref, "reference:" + ref["role"])
    html = TOKEN.sub(lambda match: slots[match.group(1)], template)
    need("{{OAA:" not in html, "unresolved reserved placeholder")
    raw_html = html.encode("utf-8")
    need(0 < len(raw_html) <= limit, "assembled output budget exceeded")
    receipt = {"kind": "local_experience_assembly", "schema_version": 1,
               "manifest": {"path": manifest_path, "sha256": hashlib.sha256(manifest_bytes).hexdigest()},
               "inputs": inputs, "script_order": scripts,
               "output": {"bytes": len(raw_html), "sha256": hashlib.sha256(raw_html).hexdigest()},
               "source_execution": False, "native_verification": "not_assessed", "rendered_verification": "not_assessed",
               "note": "Pins establish bytes only. Sources are authored code, not sanitized content. No SDK, permission or publication grant."}
    return html, receipt


def build(root, manifest_path, output):
    root = Path(root).resolve(strict=True)
    destination = local_path(root, output)
    need(destination.parent.is_dir() and not destination.exists(), "output must be a new directory under an existing parent")
    html, receipt = assemble(root, manifest_path)
    # Keep exact initial bytes before any review edits, including on subsequent builds.
    history = local_path(root, 'evidence/assembled-history')
    history.mkdir(mode=0o700, parents=True, exist_ok=True)
    snapshot = local_path(root, 'evidence/assembled-history/' + receipt['output']['sha256'] + '.html')
    if snapshot.exists():
        need(snapshot.is_file() and snapshot.read_bytes() == html.encode('utf-8'), 'retained assembly differs')
    else:
        with snapshot.open('xb') as stream:
            stream.write(html.encode('utf-8'))
        snapshot.chmod(0o600)
    first = local_path(root, 'evidence/assembled-history/first.json')
    if not first.exists():
        with first.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps({'path': snapshot.relative_to(root).as_posix(),
                                     'sha256': receipt['output']['sha256'], 'assembly': receipt}, indent=2) + '\n')
        first.chmod(0o600)
    else:
        need(first.is_file() and first.stat().st_size <= MAX_FILE, 'first assembly record unavailable')
        original = decode(first.read_bytes())
        need(type(original) is dict and type(original.get('sha256')) is str and
             re.fullmatch(r'[a-f0-9]{64}', original['sha256']), 'invalid first assembly record')
        retained = local_path(root, original.get('path'))
        need(retained.is_file() and retained.stat().st_size <= MAX_OUTPUT and
             hashlib.sha256(retained.read_bytes()).hexdigest() == original['sha256'], 'first assembly bytes changed')
    receipt['retained_candidate'] = snapshot.relative_to(root).as_posix()
    receipt['first_candidate_record'] = first.relative_to(root).as_posix()
    destination.mkdir(mode=0o700)
    created = []
    try:
        for name, value in (("index.html", html), ("assembly.json", json.dumps(receipt, indent=2) + "\n")):
            path = destination / name
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(value)
    except Exception:
        for path in created:
            path.unlink()
        destination.rmdir()
        raise
    return {"output_directory": str(destination), **receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--manifest", required=True, help="Project-relative pinned manifest")
    parser.add_argument("--output", required=True, help="New project-relative directory")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.project, args.manifest, args.output), indent=2))
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
