#!/usr/bin/env python3
"""Check portable skill metadata, repository payload and local Markdown links."""
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", ".ruff_cache", ".pytest_cache"}


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
        header = yaml.safe_load(text.split("---", 2)[1])
        if (not isinstance(header, dict) or header.get("name") != name
                or not isinstance(header.get("description"), str) or not header["description"].strip()):
            errors.append(f"{path.relative_to(root)}: invalid skill metadata")
        metadata = yaml.safe_load((path.parent / "agents/openai.yaml").read_text())
        if not isinstance(metadata, dict) or not isinstance(metadata.get("interface"), dict):
            errors.append(f"{name}: missing agent interface")
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
