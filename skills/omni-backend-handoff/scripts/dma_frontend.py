#!/usr/bin/env python3
"""Optional local frontend evidence adapter; never runs a customer pipeline."""
import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

MAX_BYTES = 16 * 1024 * 1024
KINDS = {"analyst_frontend_scope": "analyst_migration_scope",
         "analyst_frontend_return": "analyst_frontend_return"}
SHA = re.compile(r"[a-f0-9]{64}\Z")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def seal(value):
    value = copy.deepcopy(value)
    value["sha256"] = digest(canonical(value))
    return value


def path(value):
    result = Path(value).absolute()
    need(not any(p.is_symlink() for p in (result, *result.parents)), "symlink paths are not allowed")
    need(".." not in result.parts, "parent traversal is not allowed")
    return result


def _pairs(rows):
    result = {}
    for key, value in rows:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(value):
    target = path(value)
    need(target.is_file() and target.stat().st_size <= MAX_BYTES, "missing or oversized JSON file")
    with target.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    need(len(raw) <= MAX_BYTES, "JSON file exceeds 16 MiB")
    value = json.loads(raw, object_pairs_hook=_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))
    need(type(value) is dict, "JSON object required")
    return value, raw


def check_seal(value, kind):
    need(type(value.get("schema_version")) is int and value["schema_version"] == 1
         and value.get("kind") == kind, "unsupported " + kind + " contract")
    need(value.get("sha256") == digest(canonical({k: v for k, v in value.items() if k != "sha256"})),
         "self-seal mismatch")


def trusted_dma(scripts):
    """Only an explicit host-selected installed/checkout path supplies Python code."""
    scripts = path(scripts)
    need(scripts.is_dir() and path(scripts / "guided_workflow.py").is_file(),
         "--dma-scripts must name a trusted existing DMA scripts directory")
    loaded = sys.modules.get("guided_workflow")
    need(loaded is None or Path(loaded.__file__).resolve() == scripts / "guided_workflow.py",
         "another DMA runtime is already loaded; use a fresh process")
    sys.path.insert(0, str(scripts))
    module = importlib.import_module("guided_workflow")
    need(all(callable(getattr(module, name, None)) for name in
             ("load_engagement", "assess_engagement", "record_evidence")), "unsupported DMA runtime")
    return module


def material(state):
    workflow = state.get("workflow", {})
    journey = workflow.get("domain_journey")
    selected = None
    if journey and journey.get("active_domain_id") is not None:
        found = [d for d in journey.get("domains", []) if d.get("id") == journey["active_domain_id"]]
        need(len(found) == 1, "selected DMA domain is missing or ambiguous")
        selected = found[0]
    # Deliberately conservative: the full design includes shared interfaces and
    # decisions. Task/evidence revisions and domain event history are excluded.
    return copy.deepcopy({"inputs": state["inputs"], "selected_domain": selected,
                          "design": workflow.get("design")})


def export(run_dir, output, *, dma_scripts):
    gw = trusted_dma(dma_scripts)
    state = gw.load_engagement(path(run_dir))
    snapshot = material(state)
    value = seal({"schema_version": 1, "kind": "analyst_dma_context",
        "engagement_id": state["engagement_id"], "revision": state["revision"],
        "state_sha256": state["state_sha256"], "migration_scope": state["answers"].get("migration_scope"),
        "selected_domain": snapshot["selected_domain"], "material": snapshot,
        "material_sha256": digest(canonical(snapshot)),
        "authority": "supporting_evidence_only", "origin_authenticated": False,
        "authorizes_target_write": False, "migration_accepted": False})
    raw = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    need(len(raw) <= MAX_BYTES, "context exceeds 16 MiB; use a bounded engagement")
    destination = path(output)
    need(destination.parent.is_dir(), "context output parent must already exist")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(destination), "sha256": digest(raw), "material_sha256": value["material_sha256"],
            "assurance": "saved_state_snapshot_only", "authorizes_target_write": False}


def check_context(context, state):
    check_seal(context, "analyst_dma_context")
    need(context.get("authority") == "supporting_evidence_only" and
         all(context.get(k) is False for k in ("origin_authenticated", "authorizes_target_write", "migration_accepted")),
         "context cannot confer authority")
    need(context.get("engagement_id") == state["engagement_id"], "context belongs to another DMA engagement")
    need(context.get("material_sha256") == digest(canonical(context.get("material"))), "invalid material fingerprint")
    need(context.get("selected_domain") == context["material"].get("selected_domain"), "inconsistent selected domain")
    need(context.get("migration_scope") == state["answers"].get("migration_scope"), "DMA migration scope changed")
    need(context["material_sha256"] == digest(canonical(material(state))), "DMA material or selected domain changed")


def check_receipt(receipt, kind, context, raw_context):
    need(kind in KINDS, "unsupported frontend evidence kind")
    check_seal(receipt, KINDS[kind])
    need(all(receipt.get(k) is False for k in
             ("origin_authenticated", "authorizes_target_write", "migration_accepted")),
         "frontend receipt cannot confer authority or acceptance")
    pin = receipt.get("backend_context")
    need(type(pin) is dict and type(pin.get("path")) is str and bool(pin["path"])
         and pin.get("sha256") == digest(raw_context), "frontend receipt has a different backend context")
    need(receipt.get("migration_scope") == context.get("migration_scope") == "full_dashboard",
         "frontend obligation must preserve DMA migration scope")
    if kind == "analyst_frontend_return":
        need(type(receipt.get("scope_sha256")) is str and SHA.fullmatch(receipt["scope_sha256"]),
             "frontend return requires its frozen scope digest")


def _registered_scope(state, receipt, raw_context):
    for entry in state["evidence"]:
        if entry.get("kind") != "analyst_frontend_scope" or entry.get("status") != "current":
            continue
        supplied = entry.get("receipt", {})
        try:
            scope, raw = read_json(supplied.get("path", ""))
            if scope.get("sha256") != receipt["scope_sha256"]:
                continue
            need(digest(raw) == supplied.get("sha256"), "registered frontend scope changed")
            check_seal(scope, "analyst_migration_scope")
            need(scope.get("backend_context") == receipt["backend_context"] and
                 scope.get("migration_scope") == receipt["migration_scope"], "return differs from registered scope")
            need(scope["backend_context"]["sha256"] == digest(raw_context), "registered scope has another context")
            return
        except (OSError, ValueError, TypeError):
            continue
    raise ValueError("frontend return requires a current registered frozen scope")


def check_frontend(frontend_project, receipt_path, receipt, state, dma_scripts):
    spec = importlib.util.spec_from_file_location("_dma_frontend_migration", Path(__file__).with_name("migration.py"))
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    root, project = migration.ap.load_project(path(frontend_project))
    need(receipt.get("project_id") == project["id"], "receipt belongs to another frontend project")
    try:
        relative = str(path(receipt_path).relative_to(root))
    except ValueError:
        raise ValueError("receipt must be inside its frontend project") from None
    if receipt["kind"] == "analyst_migration_scope":
        checked = migration.load_scope(root, project, relative)
        need(checked == receipt, "frontend scope changed during verification")
    else:
        migration.verify_return(root, relative)
    _, catalog = migration.cw.current_catalog(root, project)
    if catalog is not None:
        portal = importlib.import_module("delivery_portal")
        need(Path(portal.__file__).resolve() == path(dma_scripts) / "delivery_portal.py",
             "another DMA delivery runtime is loaded; use a fresh process")
        pins = catalog["pins"]
        expected = {"source_fingerprint": portal.source_fingerprint(state),
                    "context_sha256": portal.context_fingerprint(state),
                    "target": {key: state["answers"].get(key) for key in ("framework", "warehouse")}}
        need(all(pins.get(key) == value for key, value in expected.items()),
             "frontend semantic candidate belongs to another DMA context")
    return root


def record(run_dir, receipt_path, context_path, kind, *, dma_scripts, frontend_project):
    gw = trusted_dma(dma_scripts)
    context, raw_context = read_json(context_path)
    receipt, raw_receipt = read_json(receipt_path)
    state = gw.load_engagement(path(run_dir))
    check_context(context, state)
    check_receipt(receipt, kind, context, raw_context)
    if kind == "analyst_frontend_return":
        _registered_scope(state, receipt, raw_context)
    check_frontend(frontend_project, receipt_path, receipt, state, dma_scripts)
    # Refresh actual source/catalogue bytes through DMA's existing local scanner.
    # This may add an audit revision; no receipt is registered if drift is found.
    state = gw.assess_engagement(path(run_dir))
    check_context(context, state)
    if kind == "analyst_frontend_return":
        _registered_scope(state, receipt, raw_context)
    check_frontend(frontend_project, receipt_path, receipt, state, dma_scripts)
    need(read_json(context_path)[1] == raw_context and read_json(receipt_path)[1] == raw_receipt,
         "frontend inputs changed during review")
    state = gw.record_evidence(path(run_dir), path(receipt_path), kind,
                               depends_on=("source", "catalogue", "target", "runtime", "discovery"))
    check_context(context, state)
    evidence = state["evidence"][-1]
    need(evidence.get("receipt", {}).get("sha256") == digest(raw_receipt),
         "receipt changed during registration; evidence remains unverified")
    return {"status": "recorded_unverified", "evidence_id": evidence["id"], "kind": kind,
            "engagement_id": state["engagement_id"], "revision": state["revision"],
            "authorizes_target_write": False, "migration_accepted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dma-scripts", required=True, help="Explicitly trusted installed or checkout DMA scripts path")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("export")
    command.add_argument("--run", required=True)
    command.add_argument("--output", required=True)
    command = commands.add_parser("record")
    command.add_argument("--run", required=True)
    command.add_argument("--receipt", required=True)
    command.add_argument("--context", required=True)
    command.add_argument("--frontend-project", required=True)
    command.add_argument("--kind", choices=sorted(KINDS), required=True)
    args = parser.parse_args(argv)
    try:
        result = (export(args.run, args.output, dma_scripts=args.dma_scripts) if args.command == "export" else
                  record(args.run, args.receipt, args.context, args.kind,
                         dma_scripts=args.dma_scripts, frontend_project=args.frontend_project))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
        print("DMA frontend adapter: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
