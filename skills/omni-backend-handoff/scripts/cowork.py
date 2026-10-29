#!/usr/bin/env python3
"""Offline, non-authorizing analyst/DMA request and candidate round trips."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "omni-artifact-accelerator/scripts"))
import analyst_project as ap

ROUTES = {
    "unselected": {"clarification"},
    "reuse_existing": {"clarification"},
    "omni_semantic_reconstruction": {"clarification", "semantic_candidate"},
    "warehouse_first_refactor": {"clarification", "semantic_candidate", "warehouse_and_semantic_candidate"},
}
CHANGE_CLASSES = {"clarification", "metric", "dimension", "binding", "security", "performance", "history"}
LANES = ["query_binding", "numeric", "interaction", "access", "visual", "narrative", "performance"]


def text(value):
    return type(value) is str and bool(value.strip())


def safe_id(value):
    ap.need(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value), "invalid request id")
    return value


def strings(values, label, nonempty=False):
    ap.need(type(values) is list and all(text(v) for v in values) and len(set(values)) == len(values), label)
    ap.need(not nonempty or bool(values), label + " must be nonempty")


def sealed(value):
    obj = copy.deepcopy(value)
    obj["sha256"] = ap.digest(ap.canonical(obj))
    return obj


def check_seal(value, kind):
    ap.need(type(value) is dict and type(value.get("schema_version")) is int and
            value["schema_version"] == 1 and value.get("kind") == kind, "unsupported exchange contract")
    ap.need(value.get("sha256") == ap.digest(ap.canonical({k: v for k, v in value.items() if k != "sha256"})),
            "exchange self-hash mismatch")


def check_spec(spec):
    ap.need(type(spec) is dict and type(spec.get("schema_version")) is int and spec["schema_version"] == 1 and
            spec.get("kind") == "analyst_backend_request_spec", "unsupported request specification")
    safe_id(spec.get("request_id"))
    ap.need(spec.get("route") in ROUTES, "explicit route required; use unselected when unknown")
    ap.need(spec["route"] == "unselected" or text(spec.get("route_reference")), "route decision reference required")
    ap.need(text(spec.get("source_platform")), "source platform required")
    requirements = spec.get("requirements")
    ap.need(type(requirements) is list and 0 < len(requirements) <= 100, "requirements required")
    ids = set()
    for req in requirements:
        ap.need(type(req) is dict and text(req.get("id")) and req["id"] not in ids, "duplicate/missing requirement id")
        ids.add(req["id"])
        ap.need(text(req.get("question")) and req.get("change_class") in CHANGE_CLASSES, "question/change class required")
        strings(req.get("frontend_asset_ids"), "frontend asset ids", nonempty=True)
        strings(req.get("metric_ids"), "metric ids")
        cases = req.get("expected_cases")
        ap.need(type(cases) is list and bool(cases) and all(type(c) is dict and text(c.get("case_id")) and
                text(c.get("expectation")) for c in cases), "independent expected cases/scenarios required")
        ap.need(len({c["case_id"] for c in cases}) == len(cases), "duplicate expected case id")
    consumers = spec.get("consumer_bindings")
    ap.need(type(consumers) is list, "consumer bindings required (empty means unknown coverage)")
    consumer_ids = set()
    for item in consumers:
        ap.need(type(item) is dict and text(item.get("asset_id")) and item["asset_id"] not in consumer_ids,
                "missing/duplicate consumer id")
        consumer_ids.add(item["asset_id"])
        strings(item.get("topic_ids"), "consumer topic ids")
        strings(item.get("field_ids"), "consumer field ids")
        ap.need(type(item.get("dependency_complete")) is bool, "consumer dependency completeness required")


def file_pin(root, path, obj):
    p = ap.relative_file(root, path)
    raw = p.read_bytes()
    pin = ap.digest(raw)
    records = [r for kind in ("sources", "artifacts") for r in obj[kind]
               if type(r) is dict and r.get("path") == path]
    ap.need(all(r.get("sha256") == pin for r in records), "registered input changed: " + path)
    return {"path": path, "sha256": pin, "bytes": len(raw)}


def current_catalog(root, obj):
    imported = obj.get("dma_import")
    if not imported:
        return None, None
    path = imported.get("catalog_path", "inputs/dma-catalog.json")
    pin = file_pin(root, path, obj)
    value, _ = ap.read_json(root / path)
    ap.need(value.get("kind") == "analyst_dma_catalog", "invalid current DMA catalog")
    _, raw = ap.read_json(imported["original_path"])
    ap.need(ap.digest(raw) == imported["original_sha256"], "current upstream DMA review changed")
    return pin, value


def verify_periscope_inventory(root, obj, path, inputs=()):
    """Reproject CDT originals and check capture attachments on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'periscope':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'Periscope inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original


def verify_metabase_inventory(root, obj, path, inputs=()):
    """Reproject Metabase originals and check capture attachments on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'metabase':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'Metabase inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original


def verify_report_source_inventory(root, obj, path, inputs=()):
    """Reproject every retained report original before a DMA round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') not in ('ssrs', 'powerbi_paginated', 'crystal'):
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = [file_pin(root, p, obj) for p in candidates if p.endswith('.json') and p != path
               and file_pin(root, p, obj)['sha256'] == expected]
    ap.need(bool(matches), 'Report inventory requires its pinned original source in the engagement')
    ap.routing_helper('visual_workflow').source_inventory(root, matches[0]['path'], path)
    return matches[0]


def verify_businessobjects_inventory(root, obj, path, inputs=()):
    """Reproject BusinessObjects originals and projection on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'businessobjects':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'BusinessObjects inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original


def verify_cognos_inventory(root, obj, path, inputs=()):
    """Reproject Cognos report original and projection on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'cognos':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'Cognos inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original


def verify_microstrategy_inventory(root, obj, path, inputs=()):
    """Reproject MicroStrategy originals and check capture attachments on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'microstrategy':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'MicroStrategy inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original



def verify_qlik_inventory(root, obj, path, inputs=()):
    """Reproject Qlik originals and check capture attachments on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'qlik':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'Qlik inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original



def verify_thoughtspot_inventory(root, obj, path, inputs=()):
    """Reproject ThoughtSpot originals and check capture attachments on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'thoughtspot':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'ThoughtSpot inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original


def verify_webfocus_inventory(root, obj, path, inputs=()):
    """Reproject WebFOCUS originals and check capture attachments on every round trip."""
    value, _ = ap.read_json(ap.relative_file(root, path))
    if value.get('source', {}).get('platform') != 'webfocus':
        return None
    expected = value['source'].get('input_sha256')
    candidates = list(dict.fromkeys([*inputs, *[r['path'] for r in obj['sources']]]))
    matches = []
    for candidate in candidates:
        if candidate.endswith('.json') and candidate != path:
            record = file_pin(root, candidate, obj)
            if record['sha256'] == expected:
                matches.append(record)
    ap.need(bool(matches), 'WebFOCUS inventory requires its pinned original source in the engagement')
    original = matches[0]
    workflow = ap.routing_helper('visual_workflow')
    workflow.source_inventory(root, original['path'], path)
    return original


def migration_sources(root, obj, spec, inputs):
    """Bind route checks to the selected export evidence, not just an action label."""
    explicit = spec.get("source_inventory_paths")
    if spec.get("migration_scope_path"):
        from migration import load_scope
        scope = load_scope(root, obj, spec["migration_scope_path"])
        scoped_paths = [row["path"] for row in scope["inventories"]]
        ap.need(explicit is None or explicit == scoped_paths, "request inventory selection conflicts with migration scope")
        explicit = scoped_paths
        allowed_assets = {asset for unit in scope["units"] if unit["disposition"] == "migrate"
                          for asset in unit["frontend_asset_ids"]}
        ap.need(all(set(row["frontend_asset_ids"]) <= allowed_assets for row in spec["requirements"]),
                "requested frontend asset is outside migration scope")
    if explicit is not None:
        strings(explicit, "source inventory paths", nonempty=True)
        paths = explicit
    else:
        paths = list(dict.fromkeys([*inputs, *[r["path"] for r in obj["sources"]]]))
    records = []
    for path in paths:
        if explicit is None and not path.endswith(".json"):
            continue
        pin = file_pin(root, path, obj)
        value, _ = ap.read_json(ap.relative_file(root, path))
        if type(value) is not dict or value.get("kind") != "omni_analyst_source_inventory":
            ap.need(explicit is None, "selected file is not a source inventory: " + path)
            continue
        ap.need(type(value.get("schema_version")) is int and value["schema_version"] == 1,
                "unsupported source inventory")
        platform = value.get("source", {}).get("platform")
        ap.need(platform == spec["source_platform"], "source platform conflicts with selected inventory")
        context = value.get("migration_context", {})
        route = context.get("route")
        # Unknown requests remain discovery only. Reuse narrows allowed work and cannot
        # create a model; neither silently switches a known direct/warehouse route.
        ap.need(route is None or spec["route"] in (route, "unselected", "reuse_existing"),
                "request route conflicts with selected source inventory")
        original = (verify_periscope_inventory(root, obj, path, inputs) if platform == 'periscope' else
                    verify_metabase_inventory(root, obj, path, inputs) if platform == 'metabase' else
                    verify_webfocus_inventory(root, obj, path, inputs) if platform == 'webfocus' else
                    verify_thoughtspot_inventory(root, obj, path, inputs) if platform == 'thoughtspot' else
                    verify_qlik_inventory(root, obj, path, inputs) if platform == 'qlik' else
                    verify_microstrategy_inventory(root, obj, path, inputs) if platform == 'microstrategy' else
                    verify_cognos_inventory(root, obj, path, inputs) if platform == 'cognos' else
                    verify_businessobjects_inventory(root, obj, path, inputs) if platform == 'businessobjects' else
                    verify_report_source_inventory(root, obj, path, inputs) if platform in ('ssrs', 'powerbi_paginated', 'crystal') else None)
        if platform in ('webfocus', 'thoughtspot', 'qlik', 'microstrategy', 'cognos', 'businessobjects', 'ssrs', 'powerbi_paginated', 'crystal'):
            restricted = {a['asset_key'] for a in value['assets'] if
                          a.get('source_identity', {}).get('restricted_private_scope') is True}
            requested = {key for r in spec['requirements'] for key in r['frontend_asset_ids']}
            requested.update(c['asset_id'] for c in spec['consumer_bindings'])
            ap.need(not requested.intersection(restricted), 'Unselected private source scope cannot migrate')
        records.append({**pin, "platform": platform, "route": route,
                        "route_status": context.get("route_status", "not_supplied"),
                        **({'original_source': original} if original else {})})
    return records


def create_request(project, spec_path, inputs):
    root, obj = ap.load_project(project)
    spec, _ = ap.read_json(ap.relative_file(root, spec_path))
    check_spec(spec)
    paths = list(dict.fromkeys([spec_path, *inputs]))
    if spec.get("migration_scope_path"):
        paths.append(spec["migration_scope_path"])
    sources = migration_sources(root, obj, spec, paths)
    paths = list(dict.fromkeys([*paths, *[row["path"] for row in sources],
                               *[row['original_source']['path'] for row in sources if row.get('original_source')]]))
    pins = [file_pin(root, path, obj) for path in paths]
    ap.need(sum(p["bytes"] for p in pins) <= ap.PACKET_BYTES, "request inputs exceed 256 KiB; select a narrower reviewed slice")
    baseline, catalog = current_catalog(root, obj)
    if baseline:
        ap.need(sum(p["bytes"] for p in pins) + baseline["bytes"] <= ap.PACKET_BYTES,
                "request plus baseline exceeds 256 KiB; select a smaller coherent engagement")
    request = sealed({"schema_version": 1, "kind": "analyst_backend_request",
        "request_id": spec["request_id"], "project_id": obj["id"], "spec": spec, "spec_path": spec_path,
        "selected_inputs": pins, "migration_sources": sources, "baseline_catalog": baseline,
        "baseline_pins": catalog["pins"] if catalog else None,
        "baseline_review_sha256": catalog["source"]["original_sha256"] if catalog else None,
        "authority": "proposal_exchange_only", "dispatch_status": "not_dispatched",
        "origin_authenticated": False, "authorizes_target_write": False})
    ap.write_json(root / "requests" / (spec["request_id"] + ".json"), request)
    return {"status": "request_prepared", "request_id": spec["request_id"], "sha256": request["sha256"],
            "path": str(root / "requests" / (spec["request_id"] + ".json")), "dispatch_status": "not_dispatched"}


def check_request(request):
    check_seal(request, "analyst_backend_request")
    check_spec(request.get("spec"))
    ap.need(request.get("request_id") == request["spec"]["request_id"] and text(request.get("project_id")),
            "request identity mismatch")
    ap.need(type(request.get("selected_inputs")) is list and bool(request["selected_inputs"]), "request input pins required")
    ap.need(request.get("authorizes_target_write") is False and request.get("origin_authenticated") is False and
            request.get("authority") == "proposal_exchange_only",
            "request cannot grant target authority")


def check_resolutions(value, request):
    ap.need(type(value) is dict and type(value.get("schema_version")) is int and value["schema_version"] == 1 and
            value.get("kind") == "analyst_backend_resolutions", "unsupported response resolutions")
    ap.need(value.get("request_sha256") == request["sha256"], "resolutions refer to a different request")
    action = value.get("backend_action")
    ap.need(action in ROUTES[request["spec"]["route"]], "backend action violates selected route")
    rows = value.get("requirements")
    ap.need(type(rows) is list and all(type(r) is dict and text(r.get("id")) and
            r.get("status") in ("proposed", "unresolved", "declined") and text(r.get("explanation")) for r in rows),
            "invalid requirement resolutions; acceptance is not a response status")
    expected = {r["id"] for r in request["spec"]["requirements"]}
    ap.need({r["id"] for r in rows} == expected and len(rows) == len(expected), "response must account for every requirement once")


def check_candidate(request, resolutions, catalog):
    # An action label cannot turn a new model into a clarification or reuse.
    if resolutions["backend_action"] == "clarification":
        ap.need(request.get("baseline_review_sha256") is not None and
                catalog["source"]["original_sha256"] == request["baseline_review_sha256"],
                "clarification must retain the exact baseline review; without a baseline resolve questions before candidate exchange")


def respond(request_path, review, resolutions_path, output):
    request, _ = ap.read_json(request_path)
    check_request(request)
    resolutions, _ = ap.read_json(resolutions_path)
    check_resolutions(resolutions, request)
    catalog = ap.dma_catalog(review)
    check_candidate(request, resolutions, catalog)
    _, raw = ap.read_json(review)
    ap.need(ap.digest(raw) == catalog["source"]["original_sha256"], "candidate changed during response")
    response = sealed({"schema_version": 1, "kind": "analyst_backend_response",
        "request_id": request["request_id"], "request_sha256": request["sha256"],
        "semantic_review": {"path": "semantic-review.json", "sha256": ap.digest(raw)},
        "resolutions": resolutions, "origin_authenticated": False, "authorizes_target_write": False})
    destination = ap.no_links(output)
    ap.need(not destination.exists() and destination.parent.is_dir(), "response needs a new directory")
    destination.mkdir(mode=0o700)
    ap.private_write(destination / "semantic-review.json", raw)
    ap.write_json(destination / "response.json", response)
    return {"status": "candidate_response_prepared", "path": str(destination), "sha256": response["sha256"],
            "native_verified": False, "requirements_accepted": False}


def fresh_request(root, obj, path):
    request, _ = ap.read_json(ap.relative_file(root, path))
    check_request(request)
    ap.need(request["project_id"] == obj["id"], "response belongs to another frontend engagement")
    for pin in request["selected_inputs"]:
        ap.need(file_pin(root, pin["path"], obj)["sha256"] == pin["sha256"], "selected frontend input changed; create a delta request")
    spec_path = request.get("spec_path", request["selected_inputs"][0]["path"])
    ap.need(spec_path in [pin["path"] for pin in request["selected_inputs"]], "request spec is not pinned")
    spec, _ = ap.read_json(ap.relative_file(root, spec_path))
    ap.need(spec == request["spec"], "embedded request spec differs from pinned input")
    sources = migration_sources(root, obj, spec, [p["path"] for p in request["selected_inputs"]])
    ap.need(sources == request.get("migration_sources", []), "migration source selection changed; create a delta request")
    return request


def local_request(root, obj, path):
    request = fresh_request(root, obj, path)
    baseline, catalog = current_catalog(root, obj)
    ap.need(baseline == request.get("baseline_catalog"), "request baseline was superseded; create a delta request")
    return request, catalog


def checked_response(directory, request):
    directory = ap.no_links(directory)
    response, raw = ap.read_json(directory / "response.json")
    check_seal(response, "analyst_backend_response")
    ap.need(response.get("request_id") == request["request_id"] and response.get("request_sha256") == request["sha256"],
            "response/request identity mismatch")
    ap.need(response.get("authorizes_target_write") is False and response.get("origin_authenticated") is False,
            "response cannot supply authority/authentication")
    check_resolutions(response.get("resolutions"), request)
    review_record = response.get("semantic_review")
    ap.need(type(review_record) is dict and review_record.get("path") == "semantic-review.json", "invalid response review path")
    review, review_bytes = ap.read_json(directory / "semantic-review.json")
    ap.need(ap.digest(review_bytes) == review_record.get("sha256"), "response candidate bytes changed")
    catalog = ap.dma_catalog(directory / "semantic-review.json")
    check_candidate(request, response["resolutions"], catalog)
    return response, raw, review_bytes, catalog


def changes(before, after, keys):
    def keyed(rows):
        return {tuple(r.get(k) for k in keys): r for r in rows}
    old, new = keyed(before), keyed(after)
    return sorted([k for k in old.keys() | new.keys() if old.get(k) != new.get(k)], key=lambda k: str(k))


def impact(request, baseline, candidate):
    old = baseline or {"dictionary": [], "metrics": [], "topics": [], "pins": {}, "dependencies": [], "upstream_unknowns": []}
    fields = set(changes(old["dictionary"], candidate["dictionary"], ("id", "topic")))
    fields.update(changes(old["metrics"], candidate["metrics"], ("id", "topic")))
    topics = {k[0] for k in changes(old["topics"], candidate["topics"], ("id",))}
    field_ids = {k[0] for k in fields}
    global_reasons = []
    # Unknown added/removed pins can describe security or execution context.
    # A minimized catalog cannot safely classify them as presentation-only.
    for key in sorted(set(old["pins"]) | set(candidate["pins"])):
        if old["pins"].get(key) != candidate["pins"].get(key):
            global_reasons.append("changed_" + key)
    for key in ("dependencies", "upstream_unknowns"):
        if old[key] != candidate[key]:
            global_reasons.append("changed_" + key)
    if not baseline:
        global_reasons.append("no_prior_backend_baseline")
    results = []
    consumers = {c["asset_id"]: c for c in request["spec"]["consumer_bindings"]}
    requested_assets = set()
    for req in request["spec"]["requirements"]:
        for asset in req["frontend_asset_ids"]:
            requested_assets.add(asset)
            consumers.setdefault(asset, {"asset_id": asset, "field_ids": [], "topic_ids": [], "dependency_complete": False})
    for consumer in consumers.values():
        reasons = list(global_reasons)
        if consumer["asset_id"] in requested_assets:
            reasons.append("request_expectations_require_review")
        if not consumer["dependency_complete"]:
            reasons.append("incomplete_consumer_dependencies")
        if field_ids.intersection(consumer["field_ids"]):
            reasons.append("changed_bound_field")
        if topics.intersection(consumer["topic_ids"]):
            reasons.append("changed_bound_topic")
        results.append({"asset_id": consumer["asset_id"], "disposition": "recheck_required" if reasons else "no_detected_binding_change",
                        "reasons": reasons, "reevaluate_lanes": LANES if reasons else [], "accepted": False})
    return {"schema_version": 1, "kind": "analyst_backend_impact", "request_sha256": request["sha256"],
            "changed_field_scopes": [{"id": k[0], "topic": k[1]} for k in sorted(fields, key=str)],
            "changed_topic_ids": sorted(topics), "global_recheck_reasons": global_reasons,
            "consumer_impact": results, "coverage": "declared_consumers_only",
            "native_validation": "not_assessed", "business_acceptance": "not_assessed",
            "warning": "Dependency completeness is supplied, not proven. Unlisted consumers remain unassessed."}


def receive(project, request_path, response_dir):
    root, obj = ap.load_project(project)
    request, baseline = local_request(root, obj, request_path)
    response, response_raw, review_raw, candidate = checked_response(response_dir, request)
    report = impact(request, baseline, candidate)
    report["requirement_resolutions"] = response["resolutions"]["requirements"]
    parent = ap.no_links(root / "exchanges")
    parent.mkdir(mode=0o700, exist_ok=True)
    destination = parent / safe_id(request["request_id"])
    ap.need(not destination.exists(), "exchange already received; preserve the immutable cycle")
    destination.mkdir(mode=0o700)
    ap.private_write(destination / "response.json", response_raw)
    ap.private_write(destination / "semantic-review.json", review_raw)
    candidate["source"]["original_path"] = str(destination / "semantic-review.json")
    ap.write_json(destination / "catalog.json", candidate)
    ap.write_json(destination / "impact.json", report)
    records = [{"path": n, "sha256": ap.digest((destination / n).read_bytes())}
               for n in ("response.json", "semantic-review.json", "catalog.json", "impact.json")]
    manifest = sealed({"schema_version": 1, "kind": "analyst_backend_exchange",
        "request_id": request["request_id"], "request_path": request_path, "request_sha256": request["sha256"],
        "files": records, "status": "received_candidate", "authorizes_target_write": False})
    ap.write_json(destination / "exchange.json", manifest)
    return {"status": "received_candidate", "path": str(destination), "impact": report,
            "working_baseline_changed": False}


def select(project, exchange_id):
    root, obj = ap.load_project(project)
    destination = ap.no_links(root / "exchanges" / safe_id(exchange_id))
    manifest, _ = ap.read_json(destination / "exchange.json")
    check_seal(manifest, "analyst_backend_exchange")
    ap.need(manifest.get("request_id") == exchange_id and manifest.get("authorizes_target_write") is False,
            "exchange identity/authority mismatch")
    expected_names = {"response.json", "semantic-review.json", "catalog.json", "impact.json"}
    records = manifest.get("files")
    ap.need(type(records) is list and len(records) == 4 and {r.get("path") for r in records} == expected_names,
            "invalid exchange inventory")
    for record in records:
        ap.need(ap.digest(ap.relative_file(destination, record["path"]).read_bytes()) == record["sha256"], "exchange artifact changed")
    if obj.get("dma_import", {}).get("exchange_id") == exchange_id:
        current_catalog(root, obj)
        request = fresh_request(root, obj, manifest["request_path"])
        ap.need(request["sha256"] == manifest["request_sha256"], "request changed after receipt")
        return {"status": "candidate_already_selected", "accepted": False}
    request, _ = local_request(root, obj, manifest["request_path"])
    ap.need(request["sha256"] == manifest["request_sha256"], "request changed after receipt")
    response, _, _, rebuilt = checked_response(destination, request)
    saved, _ = ap.read_json(destination / "catalog.json")
    ap.need(saved == rebuilt, "saved catalog differs from exact returned review")
    relative = str((destination / "catalog.json").relative_to(root))
    record = {"id": "dma-catalog-" + exchange_id, "path": relative, "sha256": ap.digest((destination / "catalog.json").read_bytes())}
    ap.need(not any(r.get("id") == record["id"] or r.get("path") == relative for r in obj["sources"]), "candidate already registered inconsistently")
    obj["sources"].append(record)
    obj["dma_import"] = {**saved["source"], "catalog_path": relative, "exchange_id": exchange_id}
    obj.setdefault("cowork_history", []).append({"exchange_id": exchange_id, "exchange_sha256": manifest["sha256"],
        "impact_path": str((destination / "impact.json").relative_to(root)), "selection": "local_candidate_only"})
    ap.write_json(root / "project.json", obj, replace=True)
    return {"status": "local_candidate_selected", "catalog_path": relative, "accepted": False,
            "authorizes_target_write": False, "requirement_resolutions": response["resolutions"]["requirements"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    cmd = subs.add_parser("request")
    cmd.add_argument("--project", required=True)
    cmd.add_argument("--spec", required=True)
    cmd.add_argument("--input", action="append", default=[])
    cmd = subs.add_parser("respond")
    for arg in ("request", "review", "resolutions", "output"):
        cmd.add_argument("--" + arg, required=True)
    cmd = subs.add_parser("receive")
    for arg in ("project", "request", "response"):
        cmd.add_argument("--" + arg, required=True)
    cmd = subs.add_parser("select")
    cmd.add_argument("--project", required=True)
    cmd.add_argument("--exchange", required=True)
    args = parser.parse_args()
    try:
        if args.command == "request":
            result = create_request(args.project, args.spec, args.input)
        elif args.command == "respond":
            result = respond(args.request, args.review, args.resolutions, args.output)
        elif args.command == "receive":
            result = receive(args.project, args.request, args.response)
        else:
            result = select(args.project, args.exchange)
        # Do not print source questions or potentially confidential result values.
        print(json.dumps({k: v for k, v in result.items() if k not in ("impact", "requirement_resolutions")}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, "error: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
