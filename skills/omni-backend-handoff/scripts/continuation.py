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
SURFACES = ("dashboard", "app")
TASK_MODES = {"net-new", "migration", "enhancement"}
EVIDENCE_PURPOSES = ("native_validation", "topic_readback")
V2_FIELDS = FIELDS | {"target_surfaces", "task_mode", "app_ids", *EVIDENCE_PURPOSES}


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


def _destination(value, version=1):
    if value is None: return
    keys = {"base_url", "model_id", "branch_id"}
    dma.need(type(value) is dict and keys <= set(value) <= (keys | ({"model_version_id"} if version == 2 else set())),
             "destination requires exact origin, model and nullable branch identifiers")
    _text(value["base_url"])
    url = urlsplit(value["base_url"])
    dma.need(url.scheme == "https" and url.hostname and not url.username and not url.password
             and not url.query and not url.fragment and url.path in ("", "/"),
             "destination must be an HTTPS origin without credentials, paths or query strings")
    _id(value["model_id"])
    if value["branch_id"] is not None: _id(value["branch_id"])
    if value.get("model_version_id") is not None: _id(value["model_version_id"])


def _analyst():
    script = Path(__file__).resolve().parents[2] / "omni-artifact-accelerator/scripts/analyst_project.py"
    spec = importlib.util.spec_from_file_location("_continuation_analyst_project", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _installation(version=1, surfaces=("dashboard",), task_mode='migration'):
    """Check the installed bundle directly, including invocation without DMA discovery."""
    skill = dma.path(Path(__file__).absolute().parents[1])
    descriptor, _ = dma.read_json(skill / "capabilities.json")
    dma.need(type(descriptor.get("schema_version")) is int and descriptor["schema_version"] == 1
             and descriptor.get("kind") == "omni_frontend_capabilities"
             and version in descriptor.get("continuation_protocol_versions", [])
             and "omni-handoff-v1" in descriptor.get("semantic_handoff_versions", [])
             and descriptor.get("entrypoint") == "scripts/continuation.py"
             and descriptor.get("authorizes_target_write") is False, "incompatible continuation installation")
    required = list(REQUIRED_SKILLS)
    if version == 2:
        dma.need(all(s in descriptor.get("target_surfaces", []) for s in surfaces)
                 and task_mode in descriptor.get("task_modes", []), "unsupported continuation surfaces or task")
        required.extend(("omni-product-owner", "omni-design-systems"))
        if "dashboard" not in surfaces:
            required.remove("omni-dashboard-designer")
        if "app" in surfaces:
            required.extend(("omni-app-designer", "omni-app-engineer"))
    for name in required:
        dma.need(dma.path(skill.parent / name / "SKILL.md").is_file(), "missing required companion skill")
    for relative in ("omni-artifact-accelerator/scripts/analyst_project.py",
                     "omni-backend-handoff/scripts/dma_frontend.py",
                     "omni-backend-handoff/scripts/migration.py", "omni-backend-handoff/scripts/cowork.py"):
        dma.need(dma.path(skill.parent / relative).is_file(), "missing required companion runtime")


def _checked_evidence(packet, captured, catalog):
    for purpose in EVIDENCE_PURPOSES:
        pins = [r for r in packet["files"] if r["purpose"] == purpose]
        dma.need(len(pins) <= 1, "select one current file per evidence purpose")
        pin = {k: pins[0][k] for k in ("path", "sha256")} if pins else None
        dma.need(packet[purpose] == pin, "continuation evidence descriptor differs from retained file")
        if pin is None:
            continue
        evidence = json.loads(captured[pin["path"]], object_pairs_hook=dma._pairs)
        dma.need(type(evidence) is dict, "continuation evidence must be an object")
        if purpose == "topic_readback":
            continue  # A pinned readback is supplied context. The current-readback verifier owns qualification.
        dma.need(evidence.get("kind") == "omni_native_receipt" and type(evidence.get("schema_version")) is int
                 and evidence["schema_version"] == 1 and evidence.get("contract_version") == "omni-native-v1-2026-10-05"
                 and evidence.get("operation") in ("validate", "update_and_validate"), "invalid native validation receipt")
        dest, target = packet["destination"], evidence.get("target")
        dma.need(type(target) is dict and dest is not None and
                 [target.get(k) for k in ("instance_url", "model_id", "branch_id")] ==
                 [dest[k] for k in ("base_url", "model_id", "branch_id")], "native validation destination mismatch")
        dma.need(catalog is not None and evidence.get("candidate_sha256") == catalog["pins"]["model_candidate_sha256"]
                 and evidence.get("context_sha256") == catalog["pins"]["model_context_sha256"], "native validation candidate mismatch")
        mode, status = evidence.get("execution_mode"), evidence.get("status")
        dma.need(mode in ("live", "simulation") and status in ("passed", "simulated_passed", "blocked", "failed", "pending")
                 and evidence.get("native_verified") is (mode == "live" and status == "passed")
                 and (status != "passed" or mode == "live") and (status != "simulated_passed" or mode == "simulation"),
                 "inconsistent native validation evidence")


def validate_packet(packet_path, *, retained_files=None):
    """Validate all retained bytes before creating a project; return captured bytes."""
    packet_path = dma.path(packet_path)
    ap = _analyst()
    raw = ap.read_bytes(packet_path, MAX_TOTAL)
    packet = json.loads(raw, object_pairs_hook=dma._pairs)
    dma.need(type(packet) is dict, 'invalid continuation packet')
    version = packet.get("schema_version")
    dma.need(type(version) is int and version in (1, 2) and set(packet) == (FIELDS if version == 1 else V2_FIELDS),
             "invalid continuation packet fields or unsupported protocol")
    dma.need(packet["kind"] == "dma_frontend_continuation" and packet["sha256"] ==
             dma.digest(dma.canonical({k: v for k, v in packet.items() if k != "sha256"})), "continuation self-seal mismatch")
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
    _destination(packet["destination"], version)
    if version == 2:
        _strings(packet["app_ids"]); _strings(packet["target_surfaces"])
        surfaces = packet["target_surfaces"]
        dma.need(surfaces and surfaces == [s for s in SURFACES if s in surfaces]
                 and type(packet["task_mode"]) is str and packet["task_mode"] in TASK_MODES, "unsupported target surfaces or task mode")
        integrated = packet["source_migration_scope"] == "full_dashboard" and "dashboard" in surfaces
        dma.need((packet["mode"] == "integrated") == integrated, "continuation mode differs from the selected backend and frontend scope")
    rows = packet["files"]
    dma.need(type(rows) is list and 0 < len(rows) <= MAX_FILES, "expected 1..128 retained packet files")
    captured, purposes, total = {}, {}, len(raw)
    files_root = packet_path.parent if retained_files is None else dma.path(retained_files)
    for row in rows:
        dma.need(type(row) is dict and set(row) == {"path", "sha256", "purpose"}, "invalid retained file descriptor")
        relative = _relative(row["path"]); _text(row["purpose"])
        if version == 2:
            dma.need(Path(relative).suffix == '.json' and row['purpose'] in
                     {'source_inventory', 'independent_source_listing', 'requirements', 'decisions', 'expectations',
                      'mapping', 'domain_context', 'semantic_review', *EVIDENCE_PURPOSES}, 'unsupported retained context purpose')
        dma.need(relative not in captured, "duplicate retained file path")
        target = dma.path(files_root / relative)
        dma.need(target != packet_path and target.is_file() and target.stat().st_size <= MAX_TOTAL, "missing or oversized retained input")
        body = ap.read_bytes(target, MAX_TOTAL)
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
        catalog = ap.dma_catalog(files_root / name)
        dma.need(catalog["source"]["original_sha256"] == review["sha256"], "semantic review changed during validation")
        dma.need(set(packet["topic_names"]) <= {r["id"] for r in catalog["topics"]}, "requested Topic is absent from retained semantic review")
    if version == 2:
        expected = [r for r in rows if r['purpose'] == 'semantic_review']
        dma.need(len(expected) == (1 if review else 0) and (not review or review == {k: expected[0][k] for k in ('path','sha256')}),
                 'semantic review purpose differs from retained file')
        _checked_evidence(packet, captured, catalog)
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
    if packet['schema_version'] == 2:
        rows = state.get('workflow', {}).get('frontend_continuations', {}).get('items', [])
        current = [row for row in rows if row.get('id') == packet['continuation_id']]
        dma.need(len(current) == 1 and current[0].get('scope_sha256') == packet['scope_sha256']
                 and current[0].get('mode') == packet['mode'], 'current DMA continuation choice is absent or stale')
        request = current[0]['request']
        dma.need(request.get('schema_version') == 2 and all(request.get(key) == packet[key] for key in
                 ('domain_id', 'choice', 'request_reference', 'target_surfaces', 'task_mode', 'dashboard_ids',
                  'app_ids', 'topic_names', 'destination')), 'current DMA continuation selection changed')
        for purpose in EVIDENCE_PURPOSES:
            requested = [r['sha256'] for r in request.get('context_files', []) if r['purpose'] == purpose]
            supplied = [packet[purpose]['sha256']] if packet[purpose] is not None else []
            dma.need(requested == supplied, 'current DMA evidence selection changed')
    return state


def _result(packet, project_id, context=None):
    value = {"schema_version": 1, "kind": "analyst_frontend_continuation_receipt",
        "continuation_id": packet["continuation_id"], "packet_sha256": packet["sha256"],
        "scope_sha256": packet["scope_sha256"], "engagement_id": packet["engagement_id"], "project_id": project_id,
        "mode": packet["mode"], "choice": packet["choice"], "backend_context": context,
        "status": "host_dispatch_pending" if packet["choice"] == "continue_now" else "handoff_prepared",
        "agents_dispatched": False, "authorizes_target_write": False, "native_verified": False,
        "topic_readiness": "supplied_unverified" if any(r["purpose"] == "topic_readback" for r in packet["files"]) else "not_assessed",
        "business_accepted": False, "scope_registered": False,
        "host_instruction": "Use $omni-artifact-accelerator in this linked project for the retained dashboard scope. Read only relevant per-task slices; preserve source IDs, selected Topics and unresolved decisions. Record actual host dispatch separately. Before live queries, verify exact destination/Topic readback through the existing native workflow. No publication is authorized.",
        "qualification": "Prepared local candidate context only. Disclosure is host-reported, not authenticated; Topic deployment and business acceptance remain separate."}
    if packet['schema_version'] == 2:
        value.update(protocol_version=2, target_surfaces=packet['target_surfaces'], task_mode=packet['task_mode'],
                     native_validation_assurance='supplied_unverified' if packet['native_validation'] else 'not_assessed',
                     host_instruction='Continue the retained ' + packet['task_mode'] + ' task for ' + ' and '.join(packet['target_surfaces']) +
                     ' with $omni-artifact-accelerator. Preserve selected Topics, source IDs and destination. Verify current Topic evidence before native work.')
    return dma.seal(value)


def _selection(packet, raw):
    prefix = 'inputs/continuations/' + _id(packet['continuation_id'])
    def local(pin):
        return {'path': prefix + '/files/' + pin['path'], 'sha256': pin['sha256']} if pin else None
    readbacks = [local(r) for r in packet['files'] if r['purpose'] == 'topic_readback']
    return {'protocol_version': packet['schema_version'], 'continuation_id': packet['continuation_id'],
            'packet': {'path': prefix + '/packet.json', 'sha256': dma.digest(raw)},
            'target_surfaces': list(packet.get('target_surfaces', ['dashboard'])), 'task_mode': packet.get('task_mode', 'migration'),
            'topic_names': list(packet['topic_names']), 'destination': copy.deepcopy(packet['destination']),
            'semantic_review': local(packet['semantic_review']), 'native_validation': local(packet.get('native_validation')),
            'topic_readback': readbacks[0] if len(readbacks) == 1 else None,
            **({'additional_topic_readbacks': readbacks} if len(readbacks) > 1 else {})}


def project_selection(root):
    """Derive selection from the retained packet, rechecking receipt and original project-relative bytes."""
    ap = _analyst()
    root, project = ap.load_project(root)
    identity = project.get('dma_continuation')
    if identity is None:
        dma.need('dma_continuation_selection' not in project and not (root / 'continuation-receipt.json').exists(),
                 'continuation identity missing')
        return None
    dma.need(type(identity) is dict and set(identity) == {'id', 'packet_sha256'}, 'invalid continuation identity')
    prefix = 'inputs/continuations/' + _id(identity['id'])
    packet, raw, _, _ = validate_packet(ap.relative_file(root, prefix + '/packet.json'), retained_files=root / prefix / 'files')
    dma.need(identity == {'id': packet['continuation_id'], 'packet_sha256': packet['sha256']}, 'retained continuation changed')
    selection = _selection(packet, raw)
    dma.need(project['surfaces'] == selection['target_surfaces'] and project['mode'] == selection['task_mode'],
             'project surface or task mode differs from continuation')
    if packet['schema_version'] == 2 or 'dma_continuation_selection' in project:
        dma.need(project.get('dma_continuation_selection') == selection, 'continuation selection changed')
    receipt, _ = ap.read_json(ap.relative_file(root, 'continuation-receipt.json'))
    context = receipt.get('backend_context')
    dma.need((context is not None) == (packet['mode'] == 'integrated'), 'continuation context mode changed')
    if context is not None:
        dma.need(type(context) is dict and set(context) == {'path','sha256'} and context['path'] == prefix + '/backend-context.json',
                 'invalid continuation context pin')
        _, body = ap.read_json(ap.relative_file(root, context['path']))
        dma.need(context['sha256'] == dma.digest(body), 'continuation context changed')
    dma.need(receipt == _result(packet, project['id'], context), 'continuation receipt changed')
    return selection


def _response(receipt, project, reused):
    # Runtime location/retry metadata is outside the immutable receipt seal.
    return {**{k: v for k, v in receipt.items() if k != "sha256"},
            "receipt_sha256": receipt["sha256"], "project": str(project), "reused": reused}


def initiate(packet_path, project, *, run_dir=None, dma_scripts=None):
    packet_path, project = dma.path(packet_path), dma.path(project)
    packet, raw, captured, catalog = validate_packet(packet_path)
    surfaces = packet.get('target_surfaces', ['dashboard'])
    _installation(packet['schema_version'], surfaces, packet.get('task_mode', 'migration'))
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
        dma.need(ap.read_bytes(ap.relative_file(project, prefix + "/packet.json"), MAX_TOTAL) == raw, "retained packet changed")
        dma.need(existing['surfaces'] == surfaces and existing['mode'] == packet.get('task_mode', 'migration'),
                 'project surface or task mode differs from continuation')
        if packet['schema_version'] == 2 or 'dma_continuation_selection' in existing:
            dma.need(existing.get('dma_continuation_selection') == _selection(packet, raw), 'continuation selection changed')
        for name, body in captured.items():
            target = ap.relative_file(project, prefix + "/files/" + name)
            dma.need(ap.read_bytes(target, MAX_TOTAL) == body, "retained continuation input changed")
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
        ap.init(staged, "DMA continuation " + packet["continuation_id"], packet.get('task_mode', 'migration'),
                'both' if len(surfaces) == 2 else surfaces[0])
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
        obj['dma_topic_policy'] = 'selected-topic-v1'
        if packet['schema_version'] == 2:
            obj['dma_continuation_selection'] = _selection(packet, raw)
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
