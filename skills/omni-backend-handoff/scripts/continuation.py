#!/usr/bin/env python3
"""Prepare or resume a host-authorized DMA frontend continuation, without dispatch.

Packet bytes are retained data, never Python modules or execution authority.
The host applies disclosure policy before invocation. No network or target writes.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

_DMA_SPEC = importlib.util.spec_from_file_location("_continuation_dma_frontend", Path(__file__).with_name("dma_frontend.py"))
dma = importlib.util.module_from_spec(_DMA_SPEC)
_DMA_SPEC.loader.exec_module(dma)

MAX_FILES = 128
MAX_TOTAL = 16 * 1024 * 1024
REQUIRED_SKILLS = ("omni-artifact-accelerator", "omni-backend-handoff", "omni-artifact-translator",
                   "omni-bi-engineer", "omni-dashboard-designer", "omni-data-analyst", "omni-qa-analyst")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}\Z")
FIELDS = {"schema_version", "kind", "continuation_id", "engagement_id", "domain_id", "mode", "choice",
          "request_reference", "scope_sha256", "semantic_review", "files", "dashboard_ids", "topic_names",
          "destination", "source_migration_scope", "unresolved", "allowed_actions", "authorizes_target_write",
          "disclosure_reference", "disclosure_assurance", "sha256"}


def _text(value):
    dma.need(type(value) is str and value.strip() == value and 0 < len(value) <= 2000
             and not any(ord(c) < 32 for c in value), "expected bounded continuation text")
    return value


def _id(value):
    dma.need(type(value) is str and ID.fullmatch(value), "invalid continuation identifier")
    return value


def _relative(value):
    _text(value)
    item = Path(value)
    dma.need(not item.is_absolute() and ".." not in item.parts and "\\" not in value
             and item.as_posix() == value and value != ".", "use canonical packet-relative paths")
    return value


def _strings(value):
    dma.need(type(value) is list and len(value) <= 20000, "expected bounded continuation list")
    for item in value: _text(item)
    dma.need(len(set(value)) == len(value), "duplicate continuation values")


def _destination(value):
    if value is None: return
    dma.need(type(value) is dict and set(value) == {"base_url", "model_id", "branch_id"},
             "destination requires exact origin, model and nullable branch identifiers")
    _text(value["base_url"])
    url = urlsplit(value["base_url"])
    dma.need(url.scheme == "https" and url.hostname and not url.username and not url.password
             and not url.query and not url.fragment and url.path in ("", "/"),
             "destination must be an HTTPS origin without credentials, paths or query strings")
    _id(value["model_id"])
    if value["branch_id"] is not None: _id(value["branch_id"])


def _analyst():
    script = Path(__file__).resolve().parents[2] / "omni-artifact-accelerator/scripts/analyst_project.py"
    spec = importlib.util.spec_from_file_location("_continuation_analyst_project", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _installation():
    """Check the installed bundle directly, including invocation without DMA discovery."""
    skill = dma.path(Path(__file__).absolute().parents[1])
    descriptor, _ = dma.read_json(skill / "capabilities.json")
    dma.need(descriptor.get("schema_version") == 1
             and 1 in descriptor.get("continuation_protocol_versions", [])
             and "omni-handoff-v1" in descriptor.get("semantic_handoff_versions", [])
             and descriptor.get("entrypoint") == "scripts/continuation.py"
             and descriptor.get("authorizes_target_write") is False, "incompatible continuation installation")
    for name in REQUIRED_SKILLS:
        dma.need(dma.path(skill.parent / name / "SKILL.md").is_file(), "missing required companion skill")
    for relative in ("omni-artifact-accelerator/scripts/analyst_project.py",
                     "omni-backend-handoff/scripts/dma_frontend.py",
                     "omni-backend-handoff/scripts/migration.py", "omni-backend-handoff/scripts/cowork.py"):
        dma.need(dma.path(skill.parent / relative).is_file(), "missing required companion runtime")


def validate_packet(packet_path):
    """Validate all retained bytes before creating a project; return captured bytes."""
    packet_path = dma.path(packet_path)
    packet, raw = dma.read_json(packet_path)
    dma.need(set(packet) == FIELDS, "invalid continuation packet fields")
    dma.check_seal(packet, "dma_frontend_continuation")
    for key in ("continuation_id", "engagement_id"): _id(packet[key])
    if packet["domain_id"] is not None: _id(packet["domain_id"])
    for key in ("request_reference", "disclosure_reference"): _text(packet[key])
    dma.need(packet["disclosure_assurance"] == "host_reported_not_authenticated", "unsupported disclosure assurance")
    dma.need(packet["mode"] in {"integrated", "independent"}
             and packet["choice"] in {"continue_now", "prepare_handoff"}, "unsupported continuation choice")
    dma.need(packet["source_migration_scope"] in {"model_only", "model_semantic", "full_dashboard"}, "invalid backend scope")
    dma.need(packet["mode"] != "integrated" or packet["source_migration_scope"] == "full_dashboard",
             "integrated continuation requires explicitly selected full_dashboard scope")
    dma.need(packet["authorizes_target_write"] is False
             and type(packet["allowed_actions"]) is list and len(packet["allowed_actions"]) == 2
             and set(packet["allowed_actions"]) == {"design", "candidate_artifacts"}, "continuation cannot grant target write authority")
    dma.need(type(packet["scope_sha256"]) is str and dma.SHA.fullmatch(packet["scope_sha256"]), "invalid scope pin")
    for key in ("dashboard_ids", "topic_names", "unresolved"): _strings(packet[key])
    _destination(packet["destination"])
    rows = packet["files"]
    dma.need(type(rows) is list and 0 < len(rows) <= MAX_FILES, "expected 1..128 retained packet files")
    captured, purposes, total = {}, {}, len(raw)
    for row in rows:
        dma.need(type(row) is dict and set(row) == {"path", "sha256", "purpose"}, "invalid retained file descriptor")
        relative = _relative(row["path"]); _text(row["purpose"])
        dma.need(relative not in captured, "duplicate retained file path")
        target = dma.path(packet_path.parent / relative)
        dma.need(target != packet_path and target.is_file() and target.stat().st_size <= MAX_TOTAL, "missing or oversized retained input")
        with target.open("rb") as stream: body = stream.read(MAX_TOTAL + 1)
        total += len(body)
        dma.need(total <= MAX_TOTAL and dma.digest(body) == row["sha256"], "retained input changed or packet exceeds 16 MiB")
        captured[relative] = body; purposes[relative] = row["purpose"]
    dma.need(not any(str(parent) in captured for name in captured for parent in Path(name).parents
                     if str(parent) != "."), "retained file paths overlap")
    contexts = [name for name, purpose in purposes.items() if purpose == "domain_context"]
    dma.need(len(contexts) == 1, "packet requires one pinned domain_context input")
    context = json.loads(captured[contexts[0]], object_pairs_hook=dma._pairs)
    dma.need(type(context) is dict and {"domain", "entity_ids", "design", "inputs", "source_coverage", "naming"} <= set(context)
             and dma.digest(dma.canonical(context)) == packet["scope_sha256"], "copied domain context does not match scope")
    domain = context.get("domain")
    dma.need(domain is None if packet["domain_id"] is None else
             type(domain) is dict and domain.get("id") == packet["domain_id"], "copied context belongs to another domain")
    review = packet["semantic_review"]
    catalog = None
    if review is not None:
        dma.need(type(review) is dict and set(review) == {"path", "sha256"}, "invalid semantic review descriptor")
        name = _relative(review["path"])
        dma.need(name in captured and dma.digest(captured[name]) == review["sha256"], "semantic review is not a retained pinned input")
        catalog = _analyst().dma_catalog(packet_path.parent / name)
        dma.need(catalog["source"]["original_sha256"] == review["sha256"], "semantic review changed during validation")
        dma.need(set(packet["topic_names"]) <= {r["id"] for r in catalog["topics"]}, "requested Topic is absent from retained semantic review")
    return packet, raw, captured, catalog


def _current(packet, run_dir, dma_scripts):
    if packet["mode"] != "integrated": return None
    dma.need(run_dir is not None and dma_scripts is not None, "integrated continuation requires a trusted DMA runtime and saved run")
    gw = dma.trusted_dma(dma_scripts)
    state = gw.assess_engagement(dma.path(run_dir))
    dma.need(state["engagement_id"] == packet["engagement_id"]
             and state["answers"].get("migration_scope") == packet["source_migration_scope"], "DMA engagement or scope differs from packet")
    snapshot = dma.scoped_material(state, packet["domain_id"], dma_scripts=dma_scripts)
    dma.need(dma.digest(dma.canonical(snapshot)) == packet["scope_sha256"], "DMA scoped material changed; reconcile a new continuation")
    return state


def _result(packet, project_id, context=None):
    return dma.seal({"schema_version": 1, "kind": "analyst_frontend_continuation_receipt",
        "continuation_id": packet["continuation_id"], "packet_sha256": packet["sha256"],
        "scope_sha256": packet["scope_sha256"], "engagement_id": packet["engagement_id"], "project_id": project_id,
        "mode": packet["mode"], "choice": packet["choice"], "backend_context": context,
        "status": "host_dispatch_pending" if packet["choice"] == "continue_now" else "handoff_prepared",
        "agents_dispatched": False, "authorizes_target_write": False, "native_verified": False,
        "topic_readiness": "supplied_unverified" if any(r["purpose"] == "topic_readback" for r in packet["files"]) else "not_assessed",
        "business_accepted": False, "scope_registered": False,
        "host_instruction": "Use $omni-artifact-accelerator in this linked project for the retained dashboard scope. Read only relevant per-task slices; preserve source IDs, selected Topics and unresolved decisions. Record actual host dispatch separately. Before live queries, verify exact destination/Topic readback through the existing native workflow. No publication is authorized.",
        "qualification": "Prepared local candidate context only. Disclosure is host-reported, not authenticated; Topic deployment and business acceptance remain separate."})


def _response(receipt, project, reused):
    # Runtime location/retry metadata is outside the immutable receipt seal.
    return {**{k: v for k, v in receipt.items() if k != "sha256"},
            "receipt_sha256": receipt["sha256"], "project": str(project), "reused": reused}


def initiate(packet_path, project, *, run_dir=None, dma_scripts=None):
    _installation()
    packet_path, project = dma.path(packet_path), dma.path(project)
    packet, raw, captured, catalog = validate_packet(packet_path)
    state = _current(packet, run_dir, dma_scripts)
    dma.need(project.parent.is_dir() and packet_path.parent != project and project not in packet_path.parents
             and packet_path.parent not in project.parents, "frontend project must be separate from retained packet inputs")
    if state is not None:
        scripts = dma.path(dma_scripts)
        spec = importlib.util.spec_from_file_location("_continuation_source_roots", scripts / "source_roots.py")
        roots = importlib.util.module_from_spec(spec); spec.loader.exec_module(roots)
        roots.ensure_output(state, project)
    ap = _analyst()
    prefix = "inputs/continuations/" + packet["continuation_id"]
    if project.exists():
        _, existing = ap.load_project(project)
        receipt, _ = dma.read_json(project / "continuation-receipt.json")
        dma.check_seal(receipt, "analyst_frontend_continuation_receipt")
        dma.need(receipt["packet_sha256"] == packet["sha256"] and receipt["project_id"] == existing["id"]
                 and existing.get("dma_continuation") == {"id": packet["continuation_id"], "packet_sha256": packet["sha256"]},
                 "existing project belongs to another continuation; retain a new version or use cowork")
        dma.need(ap.relative_file(project, prefix + "/packet.json").read_bytes() == raw, "retained packet changed")
        for name, body in captured.items():
            target = ap.relative_file(project, prefix + "/files/" + name)
            dma.need(target.read_bytes() == body, "retained continuation input changed")
        if packet["semantic_review"]:
            imported = existing.get("dma_import") or {}
            dma.need(imported.get("original_sha256") == packet["semantic_review"]["sha256"], "frontend baseline changed; use cowork for a new cycle")
            current, _ = ap.read_json(ap.relative_file(project, imported["catalog_path"]))
            expected = ap.dma_catalog(project / prefix / "files" / packet["semantic_review"]["path"])
            dma.need(current == expected, "retained semantic catalog changed")
        context_pin = receipt.get("backend_context")
        dma.need((context_pin is None) == (packet["mode"] == "independent"), "continuation context mode changed")
        if context_pin is not None:
            dma.need(type(context_pin) is dict and set(context_pin) == {"path", "sha256"}
                     and context_pin["path"] == prefix + "/backend-context.json", "invalid retained backend context path")
            context, body = dma.read_json(ap.relative_file(project, context_pin["path"]))
            dma.need(dma.digest(body) == receipt["backend_context"]["sha256"], "retained backend context changed")
            dma.check_context(context, state, dma_scripts=dma_scripts)
        dma.need(receipt == _result(packet, existing["id"], context_pin), "continuation receipt changed")
        return _response(receipt, project, True)
    # Publish a complete project once. An interrupted private staging directory
    # never becomes the resumable project or a second imported baseline.
    with tempfile.TemporaryDirectory(prefix=".dma-continuation-", dir=project.parent) as temporary:
        staged = Path(temporary) / "project"
        ap.init(staged, "DMA continuation " + packet["continuation_id"], "migration", "dashboard")
        retained = staged / prefix
        retained.mkdir(parents=True, mode=0o700)
        ap.private_write(retained / "packet.json", raw)
        for name, body in captured.items():
            target = retained / "files" / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            ap.private_write(target, body)
        context_pin = None
        if packet["mode"] == "integrated":
            location = prefix + "/backend-context.json"
            exported = dma.export(run_dir, staged / location, dma_scripts=dma_scripts,
                                  domain_id=packet["domain_id"], scoped=True)
            dma.need(exported["material_sha256"] == packet["scope_sha256"], "DMA context changed during initiation")
            context_pin = {"path": location, "sha256": exported["sha256"]}
        if catalog is not None:
            # This follows import_dma's catalog/source structure, with final
            # retained paths set before the atomic directory publication.
            catalog = copy.deepcopy(catalog)
            catalog["source"]["original_path"] = str(project / prefix / "files" / packet["semantic_review"]["path"])
            ap.write_json(staged / "inputs/dma-catalog.json", catalog)
        _, obj = ap.load_project(staged)
        obj["dma_continuation"] = {"id": packet["continuation_id"], "packet_sha256": packet["sha256"]}
        for name in captured:
            obj["sources"].append({"id": "continuation-input-" + dma.digest(name.encode())[:24],
                "path": prefix + "/files/" + name, "sha256": dma.digest(captured[name])})
        if catalog is not None:
            obj["dma_import"] = {**catalog["source"], "catalog_path": "inputs/dma-catalog.json"}
            obj["sources"].append({"id": "dma-catalog", "path": "inputs/dma-catalog.json",
                                   "sha256": dma.digest((staged / "inputs/dma-catalog.json").read_bytes())})
        ap.write_json(staged / "project.json", obj, replace=True)
        receipt = _result(packet, obj["id"], context_pin)
        ap.write_json(staged / "continuation-receipt.json", receipt)
        _current(packet, run_dir, dma_scripts)
        dma.need(not project.exists(), "frontend project appeared during initiation; retry against its retained receipt")
        os.rename(staged, project)
    return _response(receipt, project, False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("initiate")
    command.add_argument("--packet", required=True, help="Host disclosure-reviewed continuation JSON")
    command.add_argument("--project", required=True)
    command.add_argument("--run")
    command.add_argument("--dma-scripts", help="Explicitly trusted DMA scripts path; never taken from packet")
    args = parser.parse_args(argv)
    try:
        result = initiate(args.packet, args.project, run_dir=args.run, dma_scripts=args.dma_scripts)
        print(json.dumps(result, sort_keys=True)); return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        parser.exit(2, "Continuation preparation stopped: check packet pins, scope, trusted-runtime compatibility and retained project locally.\n")


if __name__ == "__main__":
    raise SystemExit(main())
