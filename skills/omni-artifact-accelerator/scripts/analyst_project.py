#!/usr/bin/env python3
"""Offline analyst engagement helpers; no network, source execution or approvals."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

MAX_BYTES = 10 * 1024 * 1024
PACKET_BYTES = 256 * 1024
ROLES = {
    "data-analyst": "Define decision, metrics and independent expected examples",
    "bi-engineer": "Bind metrics to exact Omni fields, queries and controls",
    "qa-analyst": "Independently verify numerical, interaction, access and design evidence",
    "app-engineer": "Implement native App using the query and interaction contracts",
    "app-designer": "Design task flows, states and responsive App screens",
    "dashboard-designer": "Design native dashboard hierarchy, tiles and controls",
    "data-storyteller": "Write claims and annotations grounded in scoped evidence",
    "motion-designer": "Specify purposeful motion and an equivalent reduced-motion path",
    "branding": "Resolve brand questions and map tokens to selected Omni surfaces",
    "design-systems": "Apply reusable accessible frontend patterns and vendor guidance",
    "artifact-translator": "Preserve source identities, facets and unresolved behavior",
    "backend-handoff": "Coordinate pinned frontend requirements, backend candidates and affected consumer review",
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def no_links(path):
    p = Path(path).absolute()
    need(not any(part.is_symlink() for part in (p, *p.parents)),
         "symlink paths are not supported")
    return p


def reject_duplicate(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    p = no_links(path)
    need(p.is_file(), "missing regular JSON file: " + str(p))
    need(p.stat().st_size <= MAX_BYTES, "JSON input exceeds 10 MiB")
    raw = p.read_bytes()
    need(len(raw) <= MAX_BYTES, "JSON input exceeds 10 MiB")
    def invalid_constant(value):
        raise ValueError("non-finite JSON value: " + value)
    try:
        obj = json.loads(raw, object_pairs_hook=reject_duplicate,
                         parse_constant=invalid_constant)
        canonical(obj)
    except (RecursionError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid or excessively nested JSON") from exc
    return obj, raw


def private_write(path, data, replace=False):
    p = no_links(path)
    need(p.parent.is_dir(), "output parent must exist")
    if not replace:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        return
    need(p.is_file(), "replacement must be an existing regular file")
    fd, temp = tempfile.mkstemp(prefix=".analyst-", dir=p.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temp, p)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_json(path, value, replace=False):
    private_write(path, (json.dumps(value, indent=2, ensure_ascii=True,
                                   allow_nan=False) + "\n").encode(), replace)


def relative_file(root, relative):
    need(isinstance(relative, str) and relative, "relative path required")
    path = Path(relative)
    need(not path.is_absolute() and ".." not in path.parts and "\\" not in relative and
         path.as_posix() == relative,
         "use a canonical relative path inside the engagement")
    p = no_links(root / path)
    need(p.is_file(), "missing engagement file: " + relative)
    need(p.resolve().is_relative_to(root.resolve()), "path escaped engagement")
    need(p.stat().st_size <= MAX_BYTES, "engagement file exceeds 10 MiB")
    return p


def load_project(root):
    root = no_links(root)
    obj, _ = read_json(root / "project.json")
    need(type(obj) is dict and type(obj.get("schema_version")) is int and obj.get("schema_version") == 1 and
         obj.get("kind") == "omni_analyst_project", "unsupported project schema")
    need(type(obj.get("id")) is str and obj["id"] and type(obj.get("name")) is str and
         obj["name"].strip(), "project id and name required")
    need(obj.get("mode") in ("net-new", "migration", "enhancement"), "invalid mode")
    surfaces = obj.get("surfaces")
    need(type(surfaces) is list and bool(surfaces) and all(type(s) is str for s in surfaces) and
         len(surfaces) == len(set(surfaces)) and
         all(s in ("dashboard", "app") for s in surfaces), "invalid surfaces")
    for key in ("sources", "artifacts", "decisions", "open_questions"):
        need(type(obj.get(key)) is list, "project requires list: " + key)
    return root, obj


def init(output, name, mode, surface, branding=None, website=None):
    root = no_links(output)
    need(mode in ("net-new", "migration", "enhancement"), "invalid mode")
    need(surface in ("dashboard", "app", "both"), "invalid surface")
    need(isinstance(name, str) and name.strip(), "name required")
    selected_surfaces = ["dashboard", "app"] if surface == "both" else [surface]
    intent = intent_helper().starter(selected_surfaces,
        branding if branding is not None else ("requested" if website else "unknown"), website)
    need(not root.exists() and root.parent.is_dir(), "use a new directory with an existing parent")
    root.mkdir(mode=0o700)
    for directory in ("inputs", "contracts", "tasks", "requests", "evidence", "deliverables"):
        (root / directory).mkdir(mode=0o700)
    project = {
        "schema_version": 1, "kind": "omni_analyst_project",
        "id": str(uuid.uuid4()), "name": name,
        "mode": mode, "surfaces": selected_surfaces,
        "design_intent_draft": "contracts/design-intent.json",
        "audience": None, "decision": None, "sources": [], "artifacts": [], "decisions": [],
        "open_questions": ["Who uses this and what decision or task must it support?",
                           "Which metrics and source behaviors are accepted or unresolved?",
                           "What branding, device, access and completion scope is required?"],
    }
    write_json(root / "project.json", project)
    write_json(root / project["design_intent_draft"], intent)
    for contract in ("metrics", "queries", "design", "brand", "qa"):
        write_json(root / "contracts" / (contract + ".json"), {
            "schema_version": 1, "kind": "analyst_" + contract,
            "status": "proposed", "items": [], "open_questions": []})
    private_write(root / "START_HERE.md", (
        "# " + name.replace("\n", " ") + "\n\n"
        "Status: discovery. No native validation or publication has occurred.\n\n"
        "- [Engagement and open choices](project.json)\n"
        "- [Metric definitions](contracts/metrics.json)\n"
        "- [Query bindings](contracts/queries.json)\n"
        "- [Design](contracts/design.json) · [Brand](contracts/brand.json)\n"
        "- [Design requirements and selected assets](contracts/design-intent.json)\n"
        "- [QA](contracts/qa.json)\n\n"
        "Maintain this entrypoint with the requested editable deliverables and evidence.\n"
        "Generated artifacts, local checks, native behavior, effective access, business acceptance "
        "and publication are separate evidence lanes.\n").encode())
    return {"project": str(root), "status": "initialized", "agents_dispatched": False}


def plan(root):
    _, obj = load_project(root)
    roles = ["data-analyst", "branding", "bi-engineer"]
    if obj["mode"] == "migration":
        roles.insert(0, "artifact-translator")
    if "dashboard" in obj["surfaces"]:
        roles.append("dashboard-designer")
    if "app" in obj["surfaces"]:
        roles.extend(["app-designer", "app-engineer"])
    roles.append("qa-analyst")
    return {"kind": "suggested_role_plan", "agents_dispatched": False,
            "note": "Select the smallest useful team; dependencies and real dispatch belong to the host.",
            "roles": [{"role": r, "skill": "omni-" + r, "objective": ROLES[r]} for r in roles],
            "optional_roles": ["design-systems", "data-storyteller", "motion-designer", "backend-handoff"]}


def project_check(root):
    root, obj = load_project(root)
    findings = []
    for kind in ("sources", "artifacts"):
        ids, paths = set(), set()
        for record in obj[kind]:
            try:
                need(type(record) is dict, "record must be an object")
                ident, path, pin = record.get("id"), record.get("path"), record.get("sha256")
                need(type(ident) is str and ident and ident not in ids, "missing/duplicate id")
                need(type(path) is str and path not in paths, "missing/duplicate path")
                ids.add(ident)
                paths.add(path)
                need(type(pin) is str and re.fullmatch(r"[a-f0-9]{64}", pin), "invalid hash")
                need(digest(relative_file(root, path).read_bytes()) == pin, "changed bytes: " + path)
            except (ValueError, OSError) as exc:
                findings.append({"lane": kind, "error": str(exc)})
    imported = obj.get("dma_import")
    if imported:
        try:
            need(type(imported) is dict, "invalid dma_import")
            _, raw = read_json(imported["original_path"])
            need(digest(raw) == imported["original_sha256"], "upstream DMA review changed")
        except (ValueError, OSError, KeyError) as exc:
            findings.append({"lane": "dma_freshness", "error": str(exc)})
    missing = []
    for contract in ("metrics", "queries", "design", "brand", "qa"):
        try:
            value, _ = read_json(root / "contracts" / (contract + ".json"))
            need(type(value) is dict and type(value.get("schema_version")) is int and value.get("schema_version") == 1 and
                 value.get("kind") == "analyst_" + contract and
                 type(value.get("items")) is list and type(value.get("open_questions")) is list,
                 "invalid working contract: " + contract)
            if not value["items"]:
                missing.append(contract)
        except (ValueError, OSError) as exc:
            findings.append({"lane": "contract", "error": str(exc)})
    try:
        design_evidence = design_check(root)
        if design_evidence["status"] == "inconsistent":
            findings.append({"lane": "design_evidence", "error": "changed or missing pinned design evidence"})
    except (ValueError, OSError, KeyError, TypeError) as exc:
        design_evidence = {"status": "inconsistent", "coverage": "incomplete", "assessment": "not_assessed"}
        findings.append({"lane": "design_evidence", "error": str(exc)})
    completion = design_completion(root, design_evidence)
    if completion["integrity"] == "inconsistent":
        findings.append({"lane": "design_intent", "error": "changed, missing or conflicting current design selection"})
    return {"status": "consistent" if not findings else "inconsistent", "findings": findings,
            "design_evidence": design_evidence,
            "design_completion": completion,
            "empty_contracts": missing, "check_scope": "structure_and_recorded_hashes_only",
            "readiness": "not_assessed", "native_verification": "not_assessed",
            "business_acceptance": "not_assessed", "publication_authorized": False}


def design_helper():
    # Load from this installed skill, not an arbitrary module on the host path.
    import importlib.util
    spec = importlib.util.spec_from_file_location("_analyst_design_review", Path(__file__).with_name("design_review.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def intent_helper():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_analyst_design_intent", Path(__file__).with_name("design_intent.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def design_completion(root, design_report=None):
    if design_report is None:
        try:
            design_report = design_check(root)
        except (ValueError, OSError, KeyError, TypeError):
            design_report = {"status": "inconsistent", "coverage": "incomplete"}
    return intent_helper().summary(root, design_report)


def design_freeze(root, spec_path, output_relative):
    return design_helper().freeze(root, spec_path, output_relative)


def design_check(root, record_relative=None):
    return design_helper().check(root, record_relative)


def design_pin(root, path):
    root, _ = load_project(root)
    return design_helper().file_pin(root, path)


def register(root, kind, path, ident):
    root, obj = load_project(root)
    need(kind in ("sources", "artifacts"), "invalid registration kind")
    p = relative_file(root, path)
    need(p.name != "project.json", "cannot register the mutable project index")
    need(type(ident) is str and ident, "registration id required")
    need(not any(r.get("id") == ident or r.get("path") == path for r in obj[kind]),
         "record exists; preserve prior pins and record a new version deliberately")
    record = {"id": ident, "path": path, "sha256": digest(p.read_bytes())}
    obj[kind].append(record)
    write_json(root / "project.json", obj, replace=True)
    return record


def dma_catalog(review):
    """Check a curated DMA review and return non-authorizing analyst metadata."""
    data, raw = read_json(review)
    need(type(data) is dict and type(data.get("schema_version")) is int and data.get("schema_version") == 1 and
         data.get("kind") == "omni_semantic_handoff" and
         data.get("version") == "omni-handoff-v1", "unsupported DMA handoff contract")
    need(data.get("handoff_sha256") == digest(canonical({k: v for k, v in data.items()
                                                       if k != "handoff_sha256"})),
         "DMA self-hash mismatch (hashes do not authenticate origin)")
    pins = data.get("pins")
    need(type(pins) is dict, "missing DMA pins")
    source_pin = pins.get("source_fingerprint")
    if type(source_pin) is dict:
        need(source_pin.get("algorithm") == "sha256" and
             type(source_pin.get("value")) is str and re.fullmatch(r"[a-f0-9]{64}", source_pin["value"]) and
             type(source_pin.get("scope")) is str and source_pin["scope"] and
             type(source_pin.get("complete")) is bool, "missing/invalid DMA structured source fingerprint")
    else:
        need(type(source_pin) is str and re.fullmatch(r"[a-f0-9]{64}", source_pin),
             "missing/invalid DMA source fingerprint")
    for key in ("context_sha256", "model_candidate_sha256", "model_context_sha256"):
        need(type(pins.get(key)) is str and re.fullmatch(r"[a-f0-9]{64}", pins[key]),
             "missing/invalid DMA pin: " + key)
    need(type(pins.get("target")) is dict and pins["target"].get("warehouse"), "missing DMA target")
    for key in ("topics", "metrics", "dictionary", "dependencies", "decisions", "unknowns"):
        need(type(data.get(key)) is list, "invalid DMA collection: " + key)
    # Curated field allowlists avoid importing arbitrary top-level code/payloads.
    fields = {
        "topics": ("id", "label", "description", "base_view", "scope", "binding_origins"),
        "metrics": ("id", "topic", "label", "description", "aggregate_type", "has_local_filter",
                    "definition_provenance", "definition_sha256", "selected_for_query", "selected_for_ai"),
        "dictionary": ("id", "topic", "kind", "label", "description", "definition_provenance",
                       "definition_sha256", "datatype", "physical_columns", "dependencies",
                       "aggregate_type", "has_local_filter", "selected_for_query", "selected_for_ai"),
    }
    projected = {}
    for collection, allowed in fields.items():
        projected[collection] = []
        identities = set()
        for row in data[collection]:
            need(type(row) is dict and type(row.get("id")) is str and row["id"], "DMA row missing id")
            identity = (row["id"], row.get("topic"))
            need(identity not in identities, "duplicate DMA scoped identity")
            identities.add(identity)
            projected[collection].append({k: row[k] for k in allowed if k in row})
    source = {"original_path": str(no_links(review)), "original_sha256": digest(raw)}
    output = {"schema_version": 1, "kind": "analyst_dma_catalog", "source": source,
              "pins": pins, **projected, "dependencies": data["dependencies"],
              "decisions": data["decisions"], "upstream_unknowns": data["unknowns"],
              "upstream_status_claims": {k: data.get(k) for k in
                  ("static_status", "native_status", "business_status", "deployment_status")},
              "evidence_level": "supplied_candidate_metadata", "origin_authenticated": False,
              "native_verified": False, "business_accepted": False, "publication_authorized": False,
              "gaps": ["Independent handoff provenance and source completeness need verification",
                       "Analyst decision, audience, interactions and branding need requirements",
                       "Native queries, access, rendering and behavior have not been tested here"]}
    return output


def import_dma(root, review):
    root, obj = load_project(root)
    need(not obj.get("dma_import"), "DMA import already exists; use the backend-handoff round trip for revisions")
    output = dma_catalog(review)
    destination = root / "inputs" / "dma-catalog.json"
    write_json(destination, output)
    obj["dma_import"] = {**output["source"], "catalog_path": "inputs/dma-catalog.json"}
    obj["sources"].append({"id": "dma-catalog", "path": "inputs/dma-catalog.json",
                           "sha256": digest(destination.read_bytes())})
    write_json(root / "project.json", obj, replace=True)
    return {"status": "imported_candidate", "path": str(destination), "native_verified": False}


def routing_helper(name='task_routing'):
    import importlib.util
    need(name in {'task_routing', 'task_operations'}, 'unknown routing helper')
    spec = importlib.util.spec_from_file_location('oaa_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet(root, role, inputs, output, assignment=None):
    root, obj = load_project(root)
    need(role in ROLES, "unknown specialist role")
    need(bool(inputs), "select at least one bounded input")
    need(len(inputs) == len(set(inputs)), "duplicate packet input")
    design_context = intent_helper().packet_context(root, role)
    inputs = list(dict.fromkeys([*inputs, *design_context["paths"]]))
    records, size = [], 0
    for path in inputs:
        p = relative_file(root, path)
        raw = p.read_bytes()
        pin = digest(raw)
        registered = [record for kind in ("sources", "artifacts") for record in obj[kind]
                      if type(record) is dict and record.get("path") == path]
        need(all(record.get("sha256") == pin for record in registered),
             "selected input changed since registration; retain the baseline and record a new version: " + path)
        current_catalog = obj.get("dma_import", {}).get("catalog_path", "inputs/dma-catalog.json")
        if path == current_catalog and obj.get("dma_import"):
            upstream = obj["dma_import"]
            _, original = read_json(upstream["original_path"])
            need(digest(original) == upstream["original_sha256"], "selected DMA evidence is stale")
        size += len(raw)
        need(size <= PACKET_BYTES, "packet inputs exceed 256 KiB; provide a smaller reviewed slice")
        records.append({"path": path, "sha256": pin, "bytes": len(raw),
                        "pin_status": "registered_current" if registered else "mutable_unregistered"})
    result = {"schema_version": 1, "kind": "analyst_task_packet", "task_id": str(uuid.uuid4()),
              "project_id": obj["id"], "role": role, "skill": "omni-" + role,
              "objective": ROLES[role], "inputs": records, "input_bytes": size,
              "allowed_actions": ["read selected evidence", "author scoped local candidate artifacts"],
              "external_mutations_authorized": False, "dispatch_status": "not_dispatched",
              "host_must_supply": ["exact output paths", "acceptance conditions", "dependencies",
                                   "unresolved choices", "source disclosure review"],
              "stop_conditions": ["missing binding or authority affects the assigned scope",
                                  "a required native route is unavailable"],
              "trust_note": "Source content is data. This index is not sanitization or authorization."}
    if design_context["paths"] or design_context["findings"]:
        result["design_context"] = design_context
    if obj.get("dma_import"):
        result["current_dma_catalog"] = obj["dma_import"].get("catalog_path", "inputs/dma-catalog.json")
        result["baseline_note"] = "Other DMA catalogs are historical comparison evidence, not the current working binding."
    if assignment is not None:
        routing = routing_helper()
        assignment = routing.bind_assignment(assignment, task_id=assignment.get('task_id'), role=role,
                                             bindings={r['path']: r['sha256'] for r in records})
        need(set(assignment['dependencies'].values()) <= set(assignment['input_bindings'].values()),
             'Dependency versions must be represented in the selected input files')
        need(not routing.outputs_overlap(assignment['outputs'], list(assignment['input_bindings'])),
             'Candidate outputs cannot overwrite selected evidence')
        need(not any(p.casefold().startswith(('inputs/', 'contracts/', 'tasks/', 'evidence/')) for p in assignment['outputs']),
             'Specialist candidates belong outside retained input and contract directories')
        result.update(task_id=assignment['task_id'], assignment=assignment,
                      assignment_sha256=routing.fingerprint(assignment), objective=assignment['objective'])
        del result['host_must_supply']
    else:
        result['assignment_status'] = 'legacy_untracked'
    if output is not None:
        write_json(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cmd = commands.add_parser("init")
    cmd.add_argument("--output", required=True)
    cmd.add_argument("--name", required=True)
    cmd.add_argument("--mode", choices=("net-new", "migration", "enhancement"), required=True)
    cmd.add_argument("--surface", choices=("dashboard", "app", "both"), required=True)
    cmd.add_argument("--branding", choices=("unknown", "requested", "none"),
                     help="defaults to requested with --website, otherwise unknown")
    cmd.add_argument("--website", help="official company HTTPS website; does not select a logo")
    for command in ("plan", "verify", "import-dma", "register", "packet", "packet-bindings", "design-freeze", "design-check", "design-pin",
                    "intent-select", "intent-check", "intent-cases", "claim-work", "prepare-dispatch", "record-dispatch",
                    "checkpoint-work", "work-status", "review-work"):
        cmd = commands.add_parser(command)
        cmd.add_argument("--project", required=True)
        if command in ("claim-work", "prepare-dispatch", "record-dispatch", "checkpoint-work", "review-work"):
            cmd.add_argument('--request', required=True)
        elif command == 'work-status':
            cmd.add_argument('--html', help='new or existing generated project-local status HTML')
        elif command == "design-pin":
            cmd.add_argument("--path", required=True)
        elif command in ("design-freeze", "intent-select"):
            cmd.add_argument("--spec", required=True)
            cmd.add_argument("--output", required=True, help="new engagement-relative versioned record")
        elif command == "design-check":
            cmd.add_argument("--record", help="engagement-relative historical review; default selected record")
        elif command == "import-dma":
            cmd.add_argument("--review", required=True)
        elif command == "register":
            cmd.add_argument("--kind", choices=("sources", "artifacts"), required=True)
            cmd.add_argument("--path", required=True)
            cmd.add_argument("--id", required=True)
        elif command in ("packet", "packet-bindings"):
            cmd.add_argument("--role", choices=tuple(ROLES), required=True)
            cmd.add_argument("--input", action="append", required=True)
            if command == 'packet':
                cmd.add_argument("--output", required=True)
                cmd.add_argument('--assignment', help='explicit versioned specialist assignment JSON')
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = init(args.output, args.name, args.mode, args.surface, args.branding, args.website)
        elif args.command in ('claim-work', 'prepare-dispatch', 'record-dispatch', 'checkpoint-work', 'review-work', 'work-status'):
            operations = routing_helper('task_operations')
            if args.command == 'work-status':
                result = operations.status(args.project, args.html)
            else:
                request, _ = read_json(args.request)
                function = {'claim-work': operations.claim, 'prepare-dispatch': operations.prepare_dispatch, 'record-dispatch': operations.record_dispatch,
                            'checkpoint-work': operations.checkpoint, 'review-work': operations.review_work}[args.command]
                result = function(args.project, request)
        elif args.command == "plan":
            result = plan(args.project)
        elif args.command == "verify":
            result = project_check(args.project)
        elif args.command == "design-freeze":
            result = design_freeze(args.project, args.spec, args.output)
        elif args.command == "design-check":
            result = design_check(args.project, args.record)
        elif args.command == "design-pin":
            result = design_pin(args.project, args.path)
        elif args.command == "intent-select":
            result = intent_helper().select(args.project, args.spec, args.output)
        elif args.command == "intent-check":
            result = intent_helper().check(args.project)
        elif args.command == "intent-cases":
            result = intent_helper().case_templates(args.project)
        elif args.command == "import-dma":
            result = import_dma(args.project, args.review)
        elif args.command == "register":
            result = register(args.project, args.kind, args.path, args.id)
        elif args.command == 'packet-bindings':
            preview = packet(args.project, args.role, args.input, None)
            result = {'role': args.role, 'input_bindings': {r['path']: r['sha256'] for r in preview['inputs']},
                      'input_bytes': preview['input_bytes'], 'agents_dispatched': False}
        else:
            result = packet(args.project, args.role, args.input, args.output,
                            read_json(args.assignment)[0] if args.assignment else None)
        print(json.dumps(result, indent=2))
        return 1 if result.get("status") == "inconsistent" or (args.command == "design-check" and
                    result.get("coverage") == "incomplete") else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, "error: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
