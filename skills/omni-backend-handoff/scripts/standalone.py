#!/usr/bin/env python3
"""Typed existing-Omni baselines and non-authorizing standalone migration returns.

Native reads belong to the configured NativeAdapter. This module validates retained
contracts offline; neither a self-hash nor a reported observation authenticates its
origin or grants business acceptance. Legacy DMA returns remain in migration.py.
"""
import copy
import importlib.util
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cowork as cw

ap = cw.ap
BASELINE_KIND = "analyst_existing_omni_baseline"
RETURN_KIND = "analyst_standalone_migration_return"


def _native():
    path = Path(__file__).resolve().parents[2] / "omni-bi-engineer/scripts/omni_native.py"
    spec = importlib.util.spec_from_file_location("oaa_standalone_native", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _app_module():
    path = Path(__file__).resolve().parents[2] / "omni-app-engineer/scripts/omni_app_native.py"
    spec = importlib.util.spec_from_file_location("oaa_standalone_app_native", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def query_fields(query):
    """Bounded documented semantic grammar; calculations/pivots need qualification."""
    ap.need(type(query) is dict and set(query) <= {"fields", "filters", "sorts", "limit", "table"},
            "standalone.unsupported_query_grammar")
    cw.strings(query.get("fields"), "standalone.query_fields", nonempty=True)
    filters = query.get("filters", {})
    ap.need(type(filters) is dict and all(cw.text(k) for k in filters), "standalone.invalid_filters")
    sorts = query.get("sorts", [])
    ap.need(type(sorts) is list, "standalone.invalid_sorts")
    for sort in sorts:
        ap.need(type(sort) is dict and set(sort) == {"column_name", "sort_descending"} and
                cw.text(sort["column_name"]) and type(sort["sort_descending"]) is bool,
                "standalone.unsupported_sort")
    if "limit" in query:
        ap.need(type(query["limit"]) is int and 0 < query["limit"] <= 100000,
                "standalone.invalid_query_limit")
    if "table" in query:
        ap.need(cw.text(query["table"]), "standalone.invalid_query_table")
    return sorted(set(query["fields"]) | set(filters) | {s["column_name"] for s in sorts})


def query_source_keys(requirements, surface="dashboard"):
    return {item["asset_key"] for item in _native().WORKFLOW.surface_items(requirements, surface) if
            item.get("source_identity", {}).get("query_visual") is not False and
            (item.get("source_identity", {}).get("source_platform") != "hex" or
             item.get("source_identity", {}).get("query_visual") is True) and
            (item["kind"] in {"visual", "worksheet", "query", "cell"} or
             (item["kind"] == "placement" and item.get("source_identity", {}).get("query_visual") is not False))}


def control_source_keys(requirements, surface="dashboard"):
    """Source-denominator obligations; a slicer visual and its control may both exist."""
    result = set()
    for item in _native().WORKFLOW.surface_items(requirements, surface):
        visual = item.get("source_facets", {})
        for key in ("visual", "value", "visual", "visualType"):
            visual = visual.get(key) if isinstance(visual, dict) else None
        if item["disposition"] == "migrate" and (item["kind"] == "control" or visual == "slicer" or
                (item.get("source_identity", {}).get("source_platform") in {"periscope", "metabase", "webfocus", "thoughtspot", "qlik", "microstrategy", "cognos", "businessobjects", "ssrs", "powerbi_paginated", "crystal"} and
                 item["kind"] in {"filter", "parameter"})):
            result.add(item["asset_key"])
    return result


def pointer(value, path):
    """Read a reviewed RFC 6901 location; no executable path or schema inference."""
    ap.need(cw.text(path) and path.startswith("/") and len(path) <= 1024, "standalone.control_pointer_required")
    for part in path[1:].split("/"):
        ap.need(not re.search(r"~(?![01])", part), "standalone.control_pointer_invalid")
        key = part.replace("~1", "/").replace("~0", "~")
        if type(value) is dict:
            ap.need(key in value, "standalone.control_pointer_missing")
            value = value[key]
        elif type(value) is list and re.fullmatch(r"0|[1-9][0-9]*", key):
            ap.need(int(key) < len(value), "standalone.control_pointer_missing")
            value = value[int(key)]
        else:
            raise ValueError("standalone.control_pointer_missing")
    return value


def validate_control_bindings(root, spec, requirements, workflow):
    controls = spec.get("control_bindings", [])
    ap.need(type(controls) is list and len(controls) <= 48, "standalone.control_bindings_invalid")
    inventory = workflow.load(root, requirements["source_files"][1]["path"])
    required = control_source_keys(requirements)
    query_topics = {b["query_key"]: b["topic"] for b in spec["bindings"]}
    seen, bound = set(), set()
    for control in controls:
        ap.need(type(control) is dict and set(control) == {"source_asset_keys", "control_id", "expected_config",
                "field_bindings", "target_query_keys", "scope_pointer", "compatibility_reference", "evidence_paths"},
                "standalone.control_binding_shape")
        ident = control["control_id"]
        ap.need(cw.text(ident) and len(ident) <= 254 and ident not in seen, "standalone.control_id_invalid")
        seen.add(ident)
        cw.strings(control["source_asset_keys"], "standalone.control_sources", nonempty=True)
        ap.need(set(control["source_asset_keys"]) <= required and not bound.intersection(control["source_asset_keys"]),
                "standalone.control_source_binding_mismatch")
        bound.update(control["source_asset_keys"])
        cw.strings(control["target_query_keys"], "standalone.control_query_keys", nonempty=True)
        ap.need(set(control["target_query_keys"]) <= set(query_topics), "standalone.control_query_outside_candidate")
        ap.need(type(control["expected_config"]) is dict and bool(control["expected_config"]),
                "standalone.existing_control_config_required")
        scope = pointer(control["expected_config"], control["scope_pointer"])
        if isinstance(scope, str):
            scope = [scope]
        elif isinstance(scope, dict):
            scope = list(scope)
        ap.need(type(scope) is list and all(type(x) is str for x in scope) and
                sorted(scope) == sorted(control["target_query_keys"]), "standalone.control_query_scope_mismatch")
        fields = control["field_bindings"]
        ap.need(type(fields) is list and 0 < len(fields) <= 100, "standalone.control_fields_required")
        seen_fields = set()
        for field in fields:
            ap.need(type(field) is dict and set(field) == {"topic", "field_id", "config_pointer"} and
                    cw.text(field["topic"]) and cw.text(field["field_id"]), "standalone.control_field_shape")
            ap.need((field["topic"], field["field_id"]) not in seen_fields, "standalone.duplicate_control_field")
            seen_fields.add((field["topic"], field["field_id"]))
            ap.need(pointer(control["expected_config"], field["config_pointer"]) == field["field_id"],
                    "standalone.control_field_location_mismatch")
            ap.need(all(query_topics[key] == field["topic"] for key in control["target_query_keys"]),
                    "standalone.control_topic_outside_query")
        ap.need(cw.text(control["compatibility_reference"]), "standalone.control_compatibility_review_required")
        cw.strings(control["evidence_paths"], "standalone.control_evidence_required", nonempty=True)
        for path in control["evidence_paths"]:
            workflow.pin(root, path)
    if inventory.get("source", {}).get("platform") in {"powerbi", "looker", "hex", "periscope", "metabase", "webfocus", "thoughtspot", "qlik", "microstrategy", "cognos", "businessobjects", "ssrs", "powerbi_paginated", "crystal"}:
        ap.need(bound == required, "standalone.retained_source_control_unbound")
    return controls


def retained_controls(inspection, controls):
    """Verify actual existing configs and order. Compatibility remains reviewed evidence."""
    if not controls:
        return None
    state = inspection["state"]["controls"]
    ap.need(type(state.get("data")) is dict and type(state.get("order")) is list and
            len(state["order"]) == len(set(state["order"])), "standalone.native_control_shape")
    selected = {}
    for binding in controls:
        ident = binding["control_id"]
        ap.need(state["data"].get(ident) == binding["expected_config"] and ident in state["order"],
                "standalone.native_control_changed_or_missing")
        selected[ident] = copy.deepcopy(state["data"][ident])
    return {"data": selected, "order": copy.deepcopy(state["order"]),
            "assurance": "exact_retained_config_and_reviewed_field_locations_only"}


def validate_spec(root, spec, workflow):
    ap.need(type(spec) is dict and type(spec.get("schema_version")) is int and spec["schema_version"] == 1 and
            spec.get("kind") == "analyst_existing_omni_baseline_spec", "standalone.invalid_baseline_spec")
    ap.need(cw.text(spec.get("review_ref")), "standalone.review_required")
    _, requirements = workflow.requirements(root, spec.get("requirements_path"))
    inventory = workflow.load(root, requirements["source_files"][1]["path"])
    if inventory.get("source", {}).get("platform") in {"looker", "hex", "periscope", "metabase", "webfocus", "thoughtspot", "qlik", "microstrategy", "cognos", "businessobjects", "ssrs", "powerbi_paginated", "crystal"}:
        ap.need(requirements["route"] != "unselected", "standalone.explicit_route_required")
        selected_backend(root, requirements, workflow)
    else:
        ap.need(requirements["route"] == "reuse_existing", "standalone.reuse_existing_required")
    payload = workflow.load(root, spec.get("payload_path"))
    ownership = workflow.load(root, spec.get("ownership_path"))
    # Exact payload/ownership pins are retained, in addition to individual fields.
    # Controls can introduce independent query bindings; retain existing controls
    # until their complete API grammar is separately qualified for this path.
    ap.need(not payload.get("controls") and not ownership.get("control_ids"),
            "standalone.control_mutation_requires_qualified_binding")
    presentations = payload.get("queryPresentations", {}).get("data", {})
    queries = {key: value for key, value in presentations.items()
               if type(value) is dict and value.get("type") == "query"}
    bindings = spec.get("bindings")
    ap.need(type(bindings) is list and 0 < len(bindings) <= 48, "standalone.bindings_required")
    migrated = {i["asset_key"] for i in workflow.surface_items(requirements, "dashboard")}
    seen = set()
    for binding in bindings:
        ap.need(type(binding) is dict and set(binding) ==
                {"source_asset_keys", "query_key", "topic", "query", "field_ids"}, "standalone.invalid_binding")
        key = binding["query_key"]
        ap.need(type(key) is str and re.fullmatch(r"[1-9][0-9]*", key) and key not in seen and key in queries,
                "standalone.query_binding_mismatch")
        seen.add(key)
        cw.strings(binding["source_asset_keys"], "standalone.source_asset_keys", nonempty=True)
        ap.need(set(binding["source_asset_keys"]) <= migrated, "standalone.source_binding_outside_scope")
        topic = binding["topic"]
        ap.need(cw.text(topic) and len(topic) <= 254 and not topic.startswith("-") and
                not any(ord(c) < 32 for c in topic), "standalone.invalid_topic")
        ap.need(queries[key].get("topicName") == topic and queries[key].get("query") == binding["query"],
                "standalone.payload_query_changed")
        cw.strings(binding["field_ids"], "standalone.field_ids", nonempty=True)
        ap.need(sorted(binding["field_ids"]) == query_fields(binding["query"]),
                "standalone.field_mapping_incomplete")
    ap.need(seen == set(queries), "standalone.query_binding_incomplete")
    validate_control_bindings(root, spec, requirements, workflow)
    return requirements


def selected_backend(root, requirements, workflow):
    """A current model inspection cannot stand in for a selected DMA response."""
    root, project = ap.load_project(root)
    imported = project.get("dma_import", {})
    if requirements["route"] == "reuse_existing" and not imported:
        return None
    ap.need(cw.text(imported.get("exchange_id")), "standalone.selected_backend_exchange_required")
    # Already-selected branch rechecks original source inputs and exchange pins;
    # it cannot select another candidate or synthesize an import.
    result = cw.select(root, imported["exchange_id"])
    ap.need(result["status"] == "candidate_already_selected", "standalone.existing_backend_selection_required")
    pin, _ = cw.current_catalog(root, project)
    return {"catalog": pin, "exchange_id": imported["exchange_id"]}


def semantic_definitions(snapshot, bindings, control_bindings=None):
    """Select exact resolved field objects from native regular-Topic responses."""
    control_bindings = control_bindings or []
    topics = snapshot.get("topics")
    expected_topics = {b["topic"] for b in bindings} | {f["topic"] for c in control_bindings for f in c["field_bindings"]}
    ap.need(type(topics) is dict and set(topics) == expected_topics,
            "standalone.topic_snapshot_mismatch")
    definitions = []
    selectors = list(bindings)
    for control in control_bindings:
        for field in control["field_bindings"]:
            selectors.append({"query_key": None, "control_id": control["control_id"], "topic": field["topic"],
                              "query": {}, "field_ids": [field["field_id"]]})
    for binding in selectors:
        response = topics[binding["topic"]]
        ap.need(type(response) is dict and response.get("success") is True and
                type(response.get("topic")) is dict, "standalone.topic_unavailable")
        topic = response["topic"]
        ap.need(topic.get("is_composite") is not True and topic.get("name") == binding["topic"] and
                type(topic.get("views")) is list, "standalone.regular_topic_required")
        if "table" in binding["query"]:
            ap.need(binding["query"]["table"] in {topic.get("name"), topic.get("base_view_name")},
                    "standalone.query_table_outside_topic")
        fields = {}
        for view in topic["views"]:
            ap.need(type(view) is dict, "standalone.invalid_topic_view")
            for kind in ("dimensions", "measures", "filter_only_fields"):
                ap.need(type(view.get(kind, [])) is list, "standalone.invalid_topic_fields")
                for field in view.get(kind, []):
                    ap.need(type(field) is dict, "standalone.invalid_field_definition")
                    name = field.get("fully_qualified_name")
                    if name is None:
                        continue  # Never synthesize unreturned field IDs or timeframe aliases.
                    ap.need(type(name) is str and name not in fields, "standalone.ambiguous_field_definition")
                    fields[name] = {"kind": kind, "definition": copy.deepcopy(field)}
        ap.need(set(binding["field_ids"]) <= set(fields), "standalone.native_field_missing")
        definition = {"query_key": binding["query_key"], "topic": binding["topic"],
                      "fields": {name: fields[name] for name in sorted(binding["field_ids"])}}
        if "control_id" in binding:
            definition["control_id"] = binding["control_id"]
        definitions.append(definition)
    return definitions


def load_baseline(root, path, workflow):
    root, project = ap.load_project(root)
    baseline = workflow.load(root, path)
    cw.check_seal(baseline, BASELINE_KIND)
    ap.need(baseline.get("project_id") == project["id"] and baseline.get("route") in
            {"reuse_existing", "omni_semantic_reconstruction", "warehouse_first_refactor"} and
            baseline.get("authorizes_target_write") is False and baseline.get("native_verified") is False and
            baseline.get("business_accepted") is False, "standalone.baseline_identity_or_authority")
    for pin in [baseline["spec"], baseline["requirements"], baseline["payload"], baseline["ownership"],
                *baseline["source_files"], *baseline.get("control_evidence", [])]:
        ap.need(cw.file_pin(root, pin["path"], project) == pin, "standalone.baseline_evidence_changed")
    spec = workflow.load(root, baseline["spec"]["path"])
    requirements = validate_spec(root, spec, workflow)
    ap.need(baseline["route"] == requirements["route"] and
            baseline.get("selected_backend") == selected_backend(root, requirements, workflow),
            "standalone.selected_backend_changed")
    ap.need(baseline["bindings"] == spec["bindings"] and baseline["review_ref"] == spec["review_ref"] and
            baseline["requirements"]["path"] == spec["requirements_path"] and
            baseline["payload"]["path"] == spec["payload_path"] and
            baseline["ownership"]["path"] == spec["ownership_path"] and
            baseline["route_reference"] == requirements["route_reference"], "standalone.baseline_spec_changed")
    ap.need(baseline["source_files"] == [cw.file_pin(root, p["path"], project) for p in requirements["source_files"]],
            "standalone.baseline_source_changed")
    controls = spec.get("control_bindings", [])
    ap.need(baseline.get("control_bindings", []) == controls, "standalone.control_bindings_changed")
    evidence = sorted({path for c in controls for path in c["evidence_paths"]})
    ap.need(baseline.get("control_evidence", []) == [cw.file_pin(root, path, project) for path in evidence],
            "standalone.control_evidence_changed")
    snapshot = baseline["inspection"]["semantic_snapshot"]
    ap.need(snapshot.get("retained_controls") == retained_controls(baseline["inspection"]["native_document"], controls),
            "standalone.control_context_changed")
    ap.need(cw.text(baseline["inspection"].get("inspected_at")) and
            baseline["semantic_sha256"] == ap.digest(ap.canonical(snapshot)) and
            baseline["definitions"] == semantic_definitions(snapshot, baseline["bindings"], controls),
            "standalone.baseline_definition_changed")
    ap.need(snapshot.get("target") == baseline["target"] and
            baseline["organization"] == {"tenant_origin": baseline["target"]["base_url"],
                                         "identifier_basis": "configured_https_tenant_origin"},
            "standalone.baseline_context_changed")
    return baseline


def verify_delivery(root, spec):
    """Recompute one dashboard surface proof locally for standalone or DMA returns."""
    root, project = ap.load_project(root)
    native = _native()
    workflow = native.WORKFLOW
    candidate = workflow.load(root, spec["candidate_path"])
    baseline_path = candidate["pins"]["semantic_file"]["path"]
    baseline = load_baseline(root, baseline_path, workflow)
    requirements_path = baseline["requirements"]["path"]
    spec = {**spec, "baseline_path": baseline_path, "requirements_path": requirements_path}
    _, requirements = workflow.requirements(root, requirements_path)
    target = native.TargetConfig(**baseline["target"])
    adapter = native.NativeAdapter(root, target)
    # Local candidate checks perform no remote access or token read.
    ap.need(adapter._candidate(candidate.get("candidate_sha256")) == candidate and
            spec["candidate_path"] == f'.omni-native/candidates/{candidate["candidate_sha256"]}.json',
            "standalone.candidate_changed")
    ap.need(candidate.get("standalone_baseline", {}).get("sha256") == baseline["sha256"] and
            candidate["pins"]["semantic_file"] == cw.file_pin(root, spec["baseline_path"], project),
            "standalone.candidate_baseline_mismatch")
    receipt = workflow.load(root, spec["execution_receipt_path"])
    ap.need(receipt.get("contract") == native.CONTRACT and
            receipt.get("candidate_sha256") == candidate["candidate_sha256"] and
            receipt.get("target") == baseline["target"] and receipt.get("status") == "readback_matched" and
            receipt.get("published") is False and receipt.get("native_verified") is False and
            receipt.get("business_accepted") is False and cw.text(receipt.get("authorization_ref")),
            "standalone.native_receipt_missing_or_mismatched")
    recorded = root / ".omni-native/executions" / candidate["candidate_sha256"]
    ap.need(ap.relative_file(root, spec["execution_receipt_path"]) in
            [recorded / "receipt.json", recorded / "reconciliation.json"], "standalone.native_receipt_location")
    intent = workflow.load(root, str((recorded / "intent.json").relative_to(root)))
    ap.need(intent.get("contract") == native.CONTRACT and intent.get("status") == "intent_persisted" and
            intent.get("candidate_sha256") == candidate["candidate_sha256"] and intent.get("target") == baseline["target"] and
            intent.get("authorization_ref") == receipt["authorization_ref"], "standalone.native_intent_mismatch")
    readback = receipt.get("readback")
    ap.need(type(readback) is dict and readback.get("target") == baseline["target"] and
            readback.get("snapshot_sha256") == native.digest({k: v for k, v in readback.items() if k != "snapshot_sha256"}) and
            native.readback_matches(candidate, readback.get("state")) and
            readback.get("identity") == baseline["inspection"]["semantic_snapshot"]["identity"] and
            all(readback.get("draft_context", {}).get(k) == value for k, value in
                baseline["inspection"]["semantic_snapshot"]["draft_context"].items()), "standalone.native_readback_mismatch")
    check = receipt.get("standalone_baseline_check")
    ap.need(type(check) is dict and check.get("baseline_sha256") == baseline["sha256"] and
            check.get("semantic_sha256") == baseline["semantic_sha256"] and
            check.get("semantic_snapshot") == baseline["inspection"]["semantic_snapshot"] and cw.text(check.get("checked_at")),
            "standalone.native_baseline_recheck_missing")
    coverage = workflow.load(root, spec["coverage_path"])
    ap.need(coverage.get("requirements") == workflow.pin(root, spec["requirements_path"]) and
            coverage.get("candidate") == workflow.pin(root, spec["candidate_path"]), "standalone.coverage_binding_mismatch")
    with tempfile.TemporaryDirectory(dir=root / "evidence") as temporary:
        temp = str((Path(temporary) / "coverage.json").relative_to(root))
        workflow.coverage(root, spec["requirements_path"], spec["candidate_path"],
                          [p["path"] for p in coverage["evidence"]], temp)
        ap.need(workflow.load(root, temp) == coverage, "standalone.coverage_changed")
    bound = {key for b in baseline["bindings"] for key in b["source_asset_keys"]}
    controls = {key for b in baseline.get("control_bindings", []) for key in b["source_asset_keys"]}
    gaps = [{"code": "pending_case", "case_id": case} for case in coverage["pending_cases"]]
    gaps += [{"code": "deferred_source_asset", "asset_key": key} for key in coverage["deferred_assets"]]
    gaps += [{"code": "unresolved_source_parity", "asset_key": key} for key in coverage["unresolved_assets"]]
    gaps += [{"code": "source_query_not_bound", "asset_key": key} for key in sorted(query_source_keys(requirements) - bound - controls)]
    gaps += [{"code": "source_control_not_bound", "asset_key": key} for key in sorted(control_source_keys(requirements) - controls)]
    return {"surface": "dashboard", "target": baseline["target"], "candidate_sha256": candidate["candidate_sha256"],
            "requirements": adapter._pin(requirements_path), "baseline": adapter._pin(baseline_path),
            "candidate": adapter._pin(spec["candidate_path"]), "execution_receipt": adapter._pin(spec["execution_receipt_path"]),
            "coverage": adapter._pin(spec["coverage_path"]), "gaps": gaps,
            "native_verification": "recorded_readback_only", "native_verified": False, "migration_accepted": False}


def build_both_return(root, project, scope_relative, spec_path, migration):
    """Aggregate independently recomputed surface evidence, without DMA."""
    scope = migration.load_scope(root, project, scope_relative)
    ap.need(scope["migration_scope"] == "standalone_frontend" and scope["backend_context"] is None and
            not project.get("dma_import"), "standalone.no_dma_scope_required")
    spec, _ = ap.read_json(ap.relative_file(root, spec_path))
    migration.envelope(spec, "analyst_standalone_migration_return_spec")
    ap.need(set(spec) == {"schema_version", "kind", "surface", "scope_sha256", "surface_deliveries", "unresolved"} and
            spec["surface"] in ("both", "report") and spec["scope_sha256"] == scope["sha256"], "standalone.both_return_shape")
    selected = {surface for unit in scope["units"] if unit["disposition"] == "migrate" for surface in unit["surfaces"]}
    expected = {"app", "dashboard"} if spec["surface"] == "both" else {"report"}
    ap.need(selected == expected and bool(spec["surface_deliveries"]), "standalone.both_scope_required")
    cw.strings(spec["unresolved"], "standalone.unresolved_required")
    deliveries, files, gaps, _ = migration.surface_deliveries(root, project, scope, spec)
    # Each received surface has already checked its current baseline, source,
    # candidate, intent/readback, coverage and selected frozen scope denominator.
    gaps += [{"code": "declared_unresolved", "requirement": text} for text in spec["unresolved"]]
    gaps += [{"code": "deferred_source_unit", "unit_id": unit["unit_id"]}
             for unit in scope["units"] if unit["disposition"] == "defer"]
    source_gaps = [{"inventory_path": inv["path"], "gaps": inv["gaps"]} for inv in scope["inventories"]]
    if any(row["gaps"] for row in source_gaps):
        gaps.append({"code": "retained_source_gaps"})
    if not scope["independent_source_listing"]:
        gaps.append({"code": "independent_source_listing_missing"})
    sources = {}
    for delivery in deliveries.values():
        requirements, _ = ap.read_json(ap.relative_file(root, delivery["requirements"]["path"]))
        for pin in requirements["source_files"]:
            sources[pin["path"]] = cw.file_pin(root, pin["path"], project)
    missing_lanes = {gap['case_id'].split('/')[-2] for gap in gaps if gap['code'] == 'pending_case'}
    missing_lanes.update(gap['lane'] for gap in gaps if gap['code'] == 'pending_report_source_parity')
    if any(gap['code'] == 'pending_report_case' for gap in gaps):
        missing_lanes.add('report_output')
    report_only = spec['surface'] == 'report'
    return cw.sealed({"schema_version": 1, "kind": RETURN_KIND, "surface": spec["surface"], "project_id": project["id"],
        "scope": cw.file_pin(root, scope_relative, project), "scope_sha256": scope["sha256"],
        "migration_scope": "standalone_frontend", "backend_context": None, "spec": cw.file_pin(root, spec_path, project),
        "surface_deliveries": deliveries, "files": list(files.values()), "source_files": list(sources.values()),
        "source_gaps": source_gaps, "candidate_coverage": "complete" if not gaps else "incomplete", "gaps": gaps,
        "coverage_basis": "recomputed_source_scope_independent_surface_evidence",
        "missing_lanes": sorted(missing_lanes),
        "unresolved": spec["unresolved"], "acceptance": "not_assessed",
        "native_verification": "supplied_observation_only" if report_only else "recorded_readback_only",
        "business_acceptance": "not_assessed", "source_completeness": "not_established",
        "remote_freshness": "unverified_remote" if report_only else "last_recorded_native_inspection_only", "authorizes_target_write": False,
        "origin_authenticated": False, "migration_accepted": False})


def build_return(root, project, scope_relative, spec_path, migration):
    supplied, _ = ap.read_json(ap.relative_file(root, spec_path))
    if supplied.get("surface") in ("both", "report"):
        return build_both_return(root, project, scope_relative, spec_path, migration)
    if supplied.get("surface") == "app":
        return _app_module().build_return(root, project, scope_relative, spec_path, migration)
    native = _native()
    workflow = native.WORKFLOW
    scope = migration.load_scope(root, project, scope_relative)
    ap.need(scope["migration_scope"] == "standalone_frontend" and scope["backend_context"] is None and
            not project.get("dma_import"), "standalone.no_dma_scope_required")
    spec = workflow.load(root, spec_path)
    migration.envelope(spec, "analyst_standalone_migration_return_spec")
    ap.need(spec.get("scope_sha256") == scope["sha256"], "standalone.scope_changed")
    baseline = load_baseline(root, spec["baseline_path"], workflow)
    _, requirements = workflow.requirements(root, spec["requirements_path"])
    ap.need(cw.file_pin(root, spec["requirements_path"], project) == baseline["requirements"],
            "standalone.requirements_changed")
    inventory = requirements["source_files"][1]
    ap.need(len(scope["inventories"]) == 1 and all(scope["inventories"][0][k] == inventory[k] for k in inventory),
            "standalone.scope_inventory_mismatch")
    dispositions = {i["asset_key"]: i["disposition"] for i in requirements["items"]}
    ap.need(all(dispositions[key] == unit["disposition"] for unit in scope["units"] for key in unit["asset_keys"]),
            "standalone.scope_disposition_mismatch")
    verify_delivery(root, spec)
    candidate = workflow.load(root, spec["candidate_path"])
    ap.need(candidate["pins"]["semantic_file"] == cw.file_pin(root, spec["baseline_path"], project),
            "standalone.candidate_baseline_mismatch")
    recorded = root / ".omni-native/executions" / candidate["candidate_sha256"]
    coverage = workflow.load(root, spec["coverage_path"])
    cw.strings(spec.get("unresolved"), "standalone.unresolved_required")
    gaps = [{"code": "pending_case", "case_id": case} for case in coverage["pending_cases"]]
    gaps += [{"code": "deferred_source_asset", "asset_key": key} for key in coverage["deferred_assets"]]
    gaps += [{"code": "unresolved_source_parity", "asset_key": key} for key in coverage["unresolved_assets"]]
    gaps += [{"code": "declared_unresolved", "requirement": text} for text in spec["unresolved"]]
    bound_assets = {key for binding in [*baseline["bindings"], *baseline.get("control_bindings", [])]
                    for key in binding["source_asset_keys"]}
    control_bound = {key for binding in baseline.get("control_bindings", []) for key in binding["source_asset_keys"]}
    if workflow.load(root, inventory["path"]).get("source", {}).get("platform") in {"powerbi", "looker", "hex", "periscope", "metabase", "webfocus", "thoughtspot", "qlik", "microstrategy", "cognos", "businessobjects", "ssrs", "powerbi_paginated", "crystal"} or baseline.get("control_bindings"):
        gaps += [{"code": "source_control_not_bound", "asset_key": key}
                 for key in sorted(control_source_keys(requirements) - control_bound)]
    gaps += [{"code": "source_query_not_bound", "asset_key": key}
             for key in sorted(query_source_keys(requirements) - bound_assets)]
    other_surfaces = sorted({surface for unit in scope["units"] if unit["disposition"] == "migrate"
                             for surface in unit["surfaces"]} - {"dashboard"})
    gaps += [{"code": "other_surface_requires_separate_receipt", "surface": surface} for surface in other_surfaces]
    if not scope["independent_source_listing"]:
        gaps.append({"code": "independent_source_listing_missing"})
    source_gaps = [{"inventory_path": inv["path"], "gaps": inv["gaps"]} for inv in scope["inventories"]]
    if any(row["gaps"] for row in source_gaps):
        gaps.append({"code": "retained_source_gaps"})
    paths = [spec[k] for k in ("baseline_path", "requirements_path", "candidate_path", "execution_receipt_path", "coverage_path")]
    paths += [str((recorded / "intent.json").relative_to(root))]
    files = [cw.file_pin(root, path, project) for path in paths]
    return cw.sealed({"schema_version": 1, "kind": RETURN_KIND, "project_id": project["id"],
        "scope": cw.file_pin(root, scope_relative, project), "scope_sha256": scope["sha256"],
        "migration_scope": "standalone_frontend", "backend_context": None, "route": "reuse_existing",
        "route_reference": baseline["route_reference"],
        "spec": cw.file_pin(root, spec_path, project), "baseline_sha256": baseline["sha256"],
        "candidate_sha256": candidate["candidate_sha256"], "target": baseline["target"], "files": files,
        "source_files": baseline["source_files"], "source_gaps": source_gaps,
        "candidate_coverage": "complete" if not gaps else "incomplete",
        "coverage_basis": "recomputed_source_scope_baseline_native_readback_and_case_evidence",
        "gaps": gaps, "missing_lanes": sorted({case.split("/")[-2] for case in coverage["pending_cases"]}),
        "unresolved": spec["unresolved"], "acceptance": "not_assessed", "native_verification": "recorded_readback_only",
        "business_acceptance": "not_assessed", "source_completeness": "not_established",
        "remote_freshness": "last_recorded_native_inspection_only", "authorizes_target_write": False,
        "origin_authenticated": False, "migration_accepted": False})


def verify_return(project_path, receipt_relative, migration):
    root, project = ap.load_project(project_path)
    receipt, _ = ap.read_json(ap.relative_file(root, receipt_relative))
    cw.check_seal(receipt, RETURN_KIND)
    ap.need(receipt == build_return(root, project, receipt["scope"]["path"], receipt["spec"]["path"], migration),
            "standalone.return_changed")
    return {"status": "consistent", "candidate_coverage": receipt["candidate_coverage"],
            "design_completion": ap.design_completion(root),
            "native_verification": receipt.get("native_verification", "recorded_readback_only"), "business_acceptance": "not_assessed",
            "remote_freshness": receipt.get("remote_freshness", "last_recorded_native_inspection_only"),
            "migration_accepted": False, "authorizes_target_write": False}
