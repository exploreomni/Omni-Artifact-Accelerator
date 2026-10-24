#!/usr/bin/env python3
"""Check portable skill metadata, repository payload and local Markdown links."""
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", ".ruff_cache", ".pytest_cache"}


def metadata_scalars(text, keys, indent=""):
    """Read this repository's small scalar-only metadata profile, not general YAML.

    No tags, aliases, collections, duplicate keys or multiline scalars. Quoted
    strings use JSON spelling. Unsupported syntax requires review, not PyYAML.
    """
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(re.escape(indent) + r"([a-z_]+): (.+)", line)
        if not match or match[1] not in keys or match[1] in result:
            raise ValueError("unsupported or duplicate metadata field")
        value = match[2]
        if value.startswith('"'):
            value = json.loads(value)
        elif (not re.match(r"[A-Za-z0-9]", value) or ": " in value or " #" in value
              or any(c in value for c in "{}[]&*!|>")):
            raise ValueError("unsupported scalar metadata syntax")
        if type(value) is not str or not value.strip():
            raise ValueError("nonempty metadata string required")
        result[match[1]] = value
    if set(result) != set(keys):
        raise ValueError("missing metadata field")
    return result


def check(root=ROOT):
    package = json.loads((root / "package.json").read_text())
    names = package["skills"]
    errors, links = [], 0
    if len(names) != len(set(names)):
        errors.append("duplicate package skill")
    actual = {p.name for p in (root / "skills").iterdir() if p.is_dir()}
    if actual != set(names):
        errors.append("package skill list does not match folders")
    for name in names:
        path = root / "skills" / name / "SKILL.md"
        text = path.read_text()
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"{path.relative_to(root)}: missing frontmatter")
            continue
        try:
            header = metadata_scalars(text.split("---", 2)[1], {"name", "description"})
            if header["name"] != name:
                raise ValueError("skill name mismatch")
            interface = (path.parent / "agents/openai.yaml").read_text()
            if not interface.startswith("interface:\n"):
                raise ValueError("missing agent interface")
            metadata_scalars(interface.split("\n", 1)[1],
                             {"display_name", "short_description", "default_prompt"}, "  ")
        except (ValueError, OSError) as exc:
            errors.append(f"{name}: invalid metadata: {exc}")
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            errors.append(f"{relative}: symlink is not a portable package file")
            continue
        if not path.is_file():
            continue
        if (path.suffix.lower() in {".zip", ".pyc", ".pem", ".key"} or path.name.startswith(".env")
                or (relative.parts[0] == "docs" and (path.stem.endswith("-plan") or "roadmap" in path.stem))):
            errors.append(f"{relative}: excluded repository artifact")
        if path.suffix != ".md":
            continue
        content = path.read_text()
        if re.search(r"/Users/[A-Za-z0-9._-]+/", content):
            errors.append(f"{relative}: personal workstation path")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            links += 1
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"{relative}: missing or external local link {target}")
    return {"skills": len(names), "local_links": links, "errors": errors}


if __name__ == "__main__":
    report = check()
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report["errors"]))
