#!/usr/bin/env python3
"""Source-pinned visual requirements, keyed numerical checks and evidence coverage.

Local files only. Results establish recorded evidence, never business acceptance.
"""
import argparse
import copy
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

import analyst_project as ap

KINDS = {"visual", "worksheet", "query", "cell", "placement"}
LANES = ("numeric", "interaction", "access", "visual", "accessibility", "performance")
ROUTES = {"unselected", "reuse_existing", "omni_semantic_reconstruction", "warehouse_first_refactor"}


def need(condition, code):
    ap.need(condition, code)


def pin(root, path):
    file = ap.relative_file(root, path)
    return {"path": path, "sha256": ap.digest(file.read_bytes())}


def check_pin(root, record):
    need(type(record) is dict and pin(root, record.get("path")) == record, "evidence.changed_file")
    return ap.relative_file(root, record["path"])


def load(root, path):
    return ap.read_json(ap.relative_file(root, path))[0]


def output(root, relative, value):
    p = Path(relative)
    need(not p.is_absolute() and ".." not in p.parts and "\\" not in relative
         and p.as_posix() == relative, "output.relative_path_required")
    ap.write_json(ap.no_links(root / p), value)
    return {"path": relative, "sha256": ap.digest((root / p).read_bytes())}


def tableau_module():
    path = Path(__file__).resolve().parents[2] / "omni-artifact-translator/scripts/tableau_visual.py"
    spec = importlib.util.spec_from_file_location("visual_tableau_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def powerbi_module():
    path = Path(__file__).resolve().parents[2] / "omni-artifact-translator/scripts/powerbi_visual.py"
    spec = importlib.util.spec_from_file_location("visual_powerbi_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def looker_module():
    path = Path(__file__).resolve().parents[2] / "omni-artifact-translator/scripts/looker_visual.py"
    spec = importlib.util.spec_from_file_location("visual_looker_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hex_module():
    path = Path(__file__).resolve().parents[2] / "omni-artifact-translator/scripts/hex_visual.py"
    spec = importlib.util.spec_from_file_location("visual_hex_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def item_surfaces(requirements, item):
    return item.get("target_surfaces", requirements.get("surface", ["dashboard", "app"]))


def surface_items(requirements, surface):
    need(surface in ("dashboard", "app"), "requirements.invalid_surface")
    return [i for i in requirements["items"] if i["disposition"] == "migrate"
            and surface in item_surfaces(requirements, i)]


def source_inventory(root, original, inventory):
    raw = ap.relative_file(root, original).read_bytes()
    data = load(root, inventory)
    need(data.get("kind") == "omni_analyst_source_inventory" and data.get("schema_version") == 1,
         "source.inventory_required")
    need(data["source"]["input_sha256"] == ap.digest(raw), "source.original_mismatch")
    original_value, _ = ap.read_json(ap.relative_file(root, original))
    need(data.get("upstream_payload") == original_value, "source.payload_mismatch")
    # A retained original hash alone does not protect a hand-edited projection.
    formats = {"supplied_sigma_migration_agent": "sigma-agent", "supplied_domo_migration_agent": "domo-agent",
               "supplied_dma_inventory": "dma-inventory", "looker_api_dashboard": "looker-api",
               "declared_normalized_inventory": "normalized-inventory",
               "supplied_tableau_visual_capture": "tableau-capture",
               "supplied_powerbi_visual_capture": "powerbi-capture",
               "supplied_powerbi_source_adapter_result": "powerbi-adapter",
               "supplied_looker_visual_capture": "looker-capture",
               "supplied_looker_canonical_dashboard": "looker-canonical",
               "supplied_looker_source_adapter_result": "looker-adapter",
               "supplied_hex_visual_capture": "hex-capture",
               "supplied_hex_source_adapter_result": "hex-adapter"}
    source_format = formats.get(data["source"].get("format"))
    need(source_format is not None, "source.unrecognized_projection")
    module_path = Path(__file__).resolve().parents[2] / "omni-artifact-translator/scripts/translate_artifact.py"
    spec = importlib.util.spec_from_file_location("visual_source_reprojection", module_path)
    translator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(translator)
    rebuilt = translator.translate(raw, source_format, data["source"].get("producer", {}).get("revision"))
    if "input_filename" in data["source"]:
        need(data["source"]["input_filename"] == Path(original).name, "source.filename_mismatch")
        rebuilt["source"]["input_filename"] = Path(original).name
    need(data == rebuilt, "source.projection_changed")
    if source_format == "tableau-capture":
        tableau_module().verify_capture_files(original_value, ap.relative_file(root, original).parent)
    elif source_format == "powerbi-capture":
        powerbi_module().verify_capture_files(original_value, ap.relative_file(root, original).parent)
    elif source_format == "looker-capture":
        looker_module().verify_capture_files(original_value, ap.relative_file(root, original).parent)
    elif source_format == "hex-capture":
        hex_module().verify_capture_files(original_value, ap.relative_file(root, original).parent)
    need(type(data.get("assets")) is list and bool(data["assets"]), "source.assets_required")
    need(len({a["asset_key"] for a in data["assets"]}) == len(data["assets"]), "source.duplicate_asset")
    return data


def capture_value(root, record):
    path = check_pin(root, record)
    value, raw = ap.read_json(path)
    if value.get("schema_version") == "tableau-visual-capture.v1":
        tableau_module().verify_capture_files(value, path.parent)
        return value
    if value.get("schema_version") == "powerbi-visual-capture.v1":
        powerbi_module().verify_capture_files(value, path.parent)
        return value
    if value.get("schema_version") == "looker-visual-capture.v1":
        looker_module().verify_capture_files(value, path.parent)
        return value
    if value.get("schema_version") == "hex-visual-capture.v1":
        hex_module().verify_capture_files(value, path.parent)
        return value
    need(value.get("schema_version") == "sigma-visual-capture.v1", "comparison.visual_capture_required")
    module_path = Path(__file__).resolve().parents[2] / "omni-artifact-translator/scripts/translate_artifact.py"
    spec = importlib.util.spec_from_file_location("visual_capture_validation", module_path)
    translator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(translator)
    # Same maintained producer contract as inventory import, including embedded bindings.
    translator.translate(raw, "sigma-agent", "f4eda45b0f49dc7335496d028665f7339ed82e8f")
    return value


def tableau_case_binding(asset, case, capture):
    request = capture["request"]
    identity = asset["source_identity"]
    need(identity.get("definition_sha256") == capture["source"]["definition"]["sha256"]
         and identity.get("site_id") == request["site_id"]
         and identity.get("workbook_id") == request["workbook_id"], "requirements.capture_source_mismatch")
    binding = case.get("source_binding")
    need(type(binding) is dict and binding.get("state_sha256") == tableau_module().sha(request["state"]),
         "requirements.capture_state_binding_required")
    expected_sheet = asset["source_id"] if asset["kind"] == "worksheet" else identity.get("worksheet_id")
    expected_object = expected_sheet or asset["source_id"]
    need(binding.get("worksheet_id") == expected_sheet and binding.get("placement_id") ==
         (asset["source_id"] if asset["kind"] == "placement" else None), "requirements.capture_placement_mismatch")
    mappings = request["identity_map"]["mappings"]
    need(any(m["view_id"] == binding.get("view_id") and m["status"] == "matched"
             and m["object_id"] == expected_object for m in mappings), "requirements.capture_view_mismatch")
    need(any(v["view_id"] == binding["view_id"] for v in request["views"]), "requirements.capture_view_missing")
    return binding


def powerbi_case_binding(asset, case, capture):
    request, identity = capture["request"], asset["source_identity"]
    need(identity.get("definition_fingerprint") == capture["source"]["definition_fingerprint"] and
         identity.get("workspace_id") == request["workspace_id"] and identity.get("report_id") == request["report_id"]
         and identity.get("dataset_id") == request.get("dataset_id"),
         "requirements.powerbi_capture_source_mismatch")
    binding = case.get("source_binding")
    need(type(binding) is dict and binding.get("state_sha256") == powerbi_module().sha(request["state"])
         and binding.get("page_id") == identity.get("page_id") and binding.get("visual_id") == identity.get("visual_id"),
         "requirements.powerbi_capture_visual_state_mismatch")
    views = request["views"] + request.get("queries", [])
    need(any((v["page_id"], v.get("visual_id")) == (binding["page_id"], binding.get("visual_id")) for v in views),
         "requirements.powerbi_capture_view_missing")
    if binding.get("query_id") is not None:
        need(any(q.get("query_id") == binding["query_id"] and (q.get("page_id"), q.get("visual_id")) ==
                 (binding["page_id"], binding.get("visual_id")) for q in request.get("queries", [])),
             "requirements.powerbi_capture_query_mismatch")
    return binding


def looker_case_binding(asset, case, capture):
    bridge = looker_module()
    request, identity = capture["request"], asset["source_identity"]
    export = capture["source"].get("dashboard_export")
    dashboard = export.get("dashboard") if type(export) is dict and export.get("kind") == "looker_dashboard_export" else export
    dashboard_id = request["dashboard_id"] or (dashboard.get("id") if type(dashboard) is dict else None)
    need(identity.get("dashboard_id") == dashboard_id, "requirements.looker_dashboard_mismatch")
    if identity.get("definition_fingerprint") is not None:
        need(identity["definition_fingerprint"] == capture["source"]["definition_fingerprint"] and
             identity.get("source_instance") == request["source_instance"], "requirements.looker_source_mismatch")
    else:
        export = capture["source"].get("dashboard_export")
        dashboard = export.get("dashboard") if type(export) is dict and export.get("kind") == "looker_dashboard_export" else export
        need(identity.get("dashboard_payload_sha256") == bridge.sha(dashboard), "requirements.looker_definition_mismatch")
    binding = case.get("source_binding")
    need(type(binding) is dict and binding.get("state_sha256") == bridge.sha(request["state"]),
         "requirements.looker_state_mismatch")
    expected = {"element_id": identity.get("element_id"), "placement_id": asset["source_id"] if asset["kind"] == "placement" else None,
                "layout_id": identity.get("layout_id"), "tab_id": identity.get("tab_id")}
    need(all(binding.get(k) == value for k, value in expected.items()), "requirements.looker_element_placement_mismatch")
    need(any(v.get("element_id") == expected["element_id"] and all(expected[k] is None or v.get(k) in (None, expected[k]) for k in ("tab_id", "layout_id"))
             for v in request["views"]), "requirements.looker_view_missing")
    if binding.get("binding_id") is not None:
        queries = [q for q in request["queries"] if q["binding_id"] == binding["binding_id"]]
        need(len(queries) == 1 and queries[0]["element_id"] == expected["element_id"] and
             binding.get("query_fingerprint") == bridge.sha(bridge.module("looker_capture").query_request(queries[0])),
             "requirements.looker_query_mismatch")
    return binding


def hex_case_binding(asset, case, capture):
    bridge = hex_module()
    identity = asset["source_identity"]
    binding = case.get("source_binding")
    need(type(binding) is dict, "requirements.hex_binding_required")
    expected = {"object_id": identity.get("object_id"), "project_id": identity.get("project_id"),
                "source_version_id": identity.get("source_version_id"), "cell_id": identity.get("cell_id")}
    need(all(binding.get(k) == value for k, value in expected.items()), "requirements.hex_object_mismatch")
    definitions = capture["source"]["definition_files"]
    need(any(d["source_path"] == identity.get("source_file") and d["sha256"] == identity.get("definition_sha256")
             for d in definitions), "requirements.hex_definition_mismatch")
    if identity.get("definition_fingerprint"):
        need(identity["definition_fingerprint"] == capture["source"]["definition_fingerprint"],
             "requirements.hex_definition_set_changed")
    need(binding.get("state_sha256") == bridge.sha(capture["request"]["state"]), "requirements.hex_state_mismatch")
    outputs = [o for o in capture["request"]["outputs"] if o["output_id"] == binding.get("output_id")]
    need(len(outputs) == 1 and all(outputs[0].get(k) == expected[k]
         for k in ("project_id", "source_version_id", "cell_id")), "requirements.hex_output_mismatch")
    return binding


def hex_comparison_gaps(root, source, target, capture, asset, case, columns=None):
    if case.get("source_capture") is None:
        return ["source.hex_case_capture_required"]
    binding = hex_case_binding(asset, case, capture)
    request, gaps = capture["request"], []
    output_record = next(o for o in request["outputs"] if o["output_id"] == binding["output_id"])
    if capture.get("status") == "blocked":
        gaps.append("source.hex_capture_blocked")
    if any(not binding.get(k) for k in ("project_id", "source_version_id", "cell_id")):
        gaps.append("source.hex_native_identity_unverified")
    if not request.get("source_origin") or not request.get("workspace_id"):
        gaps.append("source.hex_origin_workspace_unverified")
    if output_record["source_mode"] == "offline" or not output_record.get("run_id"):
        gaps.append("source.hex_run_version_unverified")
    observations = [o for o in capture["source"].get("state_observations", [])
                    if o.get("output_id") == binding["output_id"]]
    if len(observations) != 1:
        gaps.append("source.hex_value_observation_required")
    else:
        observed = observations[0]
        if observed.get("applied") is not True or not observed.get("reference"):
            gaps.append("source.hex_value_state_unverified")
        for field in ("project_id", "source_version_id", "cell_id", "output_id", "run_id", "source_mode"):
            if observed.get(field) != output_record.get(field):
                gaps.append("source.hex_observation." + field)
        if observed.get("state_sha256") != binding["state_sha256"]:
            gaps.append("source.hex_observation.state_sha256")
        for field in ("inputs", "filters", "timezone", "locale"):
            wanted = request["state"].get(field)
            if wanted is None or observed.get(field) != wanted or source["context"].get(field) != wanted:
                gaps.append("source.hex_observation." + field)
            if target["context"].get(field) != wanted:
                gaps.append("context." + field)
        principal = request["state"].get("principal")
        if not principal or observed.get("principal") != principal or source["context"].get("principal") != principal:
            gaps.append("source.hex_observation.principal")
        for field in ("data_watermark", "cache_reference", "population"):
            if not observed.get(field) or observed[field] != source["context"].get(field):
                gaps.append("source.hex_observation." + field)
        if not target["context"].get("principal") or not target["context"].get("cache_reference"):
            gaps.append("target.hex_equivalent_execution_context_required")
        # A draft session identifier can outlive one execution. Bind observed output
        # freshness to independent execution/source evidence, never just that ID.
        if not observed.get("execution_reference") or not observed.get("output_freshness_reference"):
            gaps.append("source.hex_output_freshness_unverified")
    file_record = source.get("raw_file") if source.get("format") == "hex-normalized" else source["file"]
    attachments = [a for a in capture["attachments"] if a.get("format") in ("csv", "json")
                   and a.get("output_id") == binding["output_id"] and a.get("sha256") == file_record.get("sha256")
                   and a.get("state_sha256") == binding["state_sha256"]]
    if len(attachments) != 1:
        gaps.append("source.hex_results_not_bound_to_capture")
    else:
        completeness = attachments[0].get("result_completeness", {})
        if completeness.get("status") != "complete" or not completeness.get("reference") or completeness.get("flags"):
            gaps.append("source.hex_result_completeness_unverified")
    if source.get("format") == "hex-normalized":
        normalized = load(root, source["file"]["path"])
        expected = {"capture_content_hash": capture["content_hash"], **{k: binding[k] for k in (
            "project_id", "source_version_id", "cell_id", "output_id", "state_sha256")},
            "attachment_sha256": file_record["sha256"]}
        if normalized.get("binding") != expected:
            gaps.append("source.hex_normalization_binding_mismatch")
        for field in normalized.get("parser_profile", {}).get("columns", []):
            currency = field.get("currency")
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get("source") == field["name"]]
                if len(mapped) != 1 or source["context"].get("currencies", {}).get(field["name"]) != currency["code"] or \
                        target["context"].get("currencies", {}).get(mapped[0]["target"]) != currency["code"]:
                    gaps.append("context.currency." + field["name"])
    return gaps


def cases(asset):
    scenarios = [("visual", "default"), ("visual", "narrow"), ("interaction", "default_filter_reset"),
                 ("access", "allowed"), ("access", "denied"), ("accessibility", "keyboard_labels")]
    numeric = asset["kind"] in KINDS
    if asset["source_identity"].get("source_platform") == "looker" and asset["kind"] == "placement":
        numeric = asset["source_identity"].get("query_visual") is True
    if asset["source_identity"].get("source_platform") == "looker" and asset["source_identity"].get("expected_kind") in KINDS:
        numeric = True
    if asset["source_identity"].get("source_platform") == "hex":
        numeric = asset["source_identity"].get("query_visual") is True
    if numeric:
        scenarios.extend([("numeric", "default"), ("numeric", "changed_filter"),
                          ("interaction", "drill_navigation"), ("performance", "representative_volume")])
    if asset["source_identity"].get("definition_sha256"):
        scenarios.extend([("interaction", "changed_parameter"), ("interaction", "empty_result"),
                          ("interaction", "action_state")])
    if asset["source_identity"].get("report_id") or asset["source_identity"].get("source_platform") == "powerbi":
        scenarios.extend([("interaction", "bookmark_state"), ("interaction", "slicer_crossfilter"),
                          ("interaction", "drillthrough_reset"), ("visual", "hidden_mobile_state")])
    if asset["source_identity"].get("source_platform") == "looker":
        scenarios.extend([("interaction", "filter_listener_exclusions"), ("interaction", "tab_navigation"),
                          ("visual", "content_and_custom_behavior")])
    if asset["source_identity"].get("source_platform") == "hex":
        kind = asset["kind"]
        if kind == "control":
            scenarios.extend([("interaction", "typed_input_defaults_options"), ("interaction", "downstream_scope_exclusions"),
                              ("interaction", "pending_run_reset"), ("interaction", "invalid_empty_denied")])
        elif kind == "action":
            scenarios.extend([("interaction", "effect_authority_and_recovery"), ("access", "action_denied")])
        elif kind in ("project", "page", "app", "screen", "generated_file"):
            scenarios.extend([("interaction", "complete_task_journey"), ("interaction", "conditional_navigation"),
                              ("interaction", "stale_error_out_of_order"), ("performance", "input_to_result")])
        if numeric:
            scenarios.extend([("numeric", "changed_input"), ("interaction", "source_run_and_refresh"),
                              ("interaction", "empty_error_stale_reset")])
    return [{"case_id": asset["asset_key"] + "/" + lane + "/" + scenario, "lane": lane,
             "expectation": None, "status": "not_run"} for lane, scenario in scenarios]


def prepare(root, original, inventory, destination, website=None):
    root, project = ap.load_project(root)
    source = source_inventory(root, original, inventory)
    if website is not None:
        parsed = urlsplit(website)
        need(parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username
             and not parsed.password, "brand.invalid_website")
    route = source.get("migration_context", {}).get("route") or "unselected"
    result = {"schema_version": 1, "kind": "analyst_visual_requirements", "project_id": project["id"],
              "source_files": [pin(root, original), pin(root, inventory)], "route": route,
              "route_reference": source.get("migration_context", {}).get("route_reference"),
              "surface": project["surfaces"],
              "brand": {"company_website_url": website, "approved_theme": None, "asset_refs": [],
                        "open_questions": [] if website else ["What is the company website URL?"]},
              "items": [], "source_gaps": copy.deepcopy(source.get("gaps", [])),
              "native_validation": "not_run", "business_acceptance": "not_recorded"}
    for asset in source["assets"]:
        result["items"].append({"asset_key": asset["asset_key"], "source_id": asset["source_id"],
            "source_identity": copy.deepcopy(asset["source_identity"]), "source_path": asset["source_path"],
            "source_payload_sha256": asset["source_payload_sha256"], "kind": asset["kind"],
            "source_facets": copy.deepcopy(asset["facets"]), "disposition": "migrate",
            "scope_decision": None, "target_surfaces": list(project["surfaces"]), "assignment_reference": None,
            "business_question": None, "target_binding": None,
            "implementation_route": None, "parity": {facet: "unknown" for facet in asset["facets"]},
            "design_changes": [], "required_cases": cases(asset)})
    return output(root, destination, result)


def requirements(root, path):
    root, project = ap.load_project(root)
    data = load(root, path)
    need(data.get("kind") == "analyst_visual_requirements" and data.get("schema_version") == 1
         and data.get("project_id") == project["id"], "requirements.invalid_contract")
    need(len(data.get("source_files", [])) == 2, "requirements.source_pins_required")
    for entry in data["source_files"]:
        check_pin(root, entry)
    source = source_inventory(root, *(p["path"] for p in data["source_files"]))
    assets = {a["asset_key"]: a for a in source["assets"]}
    items = data.get("items")
    need(type(items) is list and len(items) == len(assets)
         and {a.get("asset_key") for a in items} == set(assets), "requirements.coverage_changed")
    source_route = source.get("migration_context", {}).get("route")
    need(data.get("route") in ROUTES, "requirements.explicit_route_required")
    need(not source_route or data["route"] in (source_route, "unselected", "reuse_existing"),
         "requirements.source_route_conflict")
    need(data["route"] == "unselected" or bool(data.get("route_reference")), "requirements.route_reference_required")
    need(data.get("surface") == project["surfaces"], "requirements.engagement_surfaces_changed")
    for item in items:
        assigned = item_surfaces(data, item)
        need(type(assigned) is list and assigned and all(type(x) is str for x in assigned)
             and len(assigned) == len(set(assigned)) and set(assigned) <= set(data["surface"]),
             "requirements.invalid_surface_assignment")
        if set(assigned) != set(data["surface"]):
            need(type(item.get("assignment_reference")) is str and item["assignment_reference"].strip(),
                 "requirements.surface_assignment_reference_required")
        asset = assets[item["asset_key"]]
        for field in ("source_id", "source_identity", "source_path", "source_payload_sha256", "kind"):
            need(item.get(field) == asset[field], "requirements.source_identity_changed")
        need(item.get("source_facets") == asset["facets"], "requirements.source_facets_changed")
        need(item.get("disposition") in ("migrate", "defer", "exclude"), "requirements.invalid_disposition")
        if item["disposition"] != "migrate":
            decision = item.get("scope_decision")
            need(type(decision) is dict and decision.get("reason") and decision.get("reference"),
                 "requirements.scope_decision_required")
        expected = {(c["case_id"], c["lane"]) for c in cases(asset)}
        supplied = item.get("required_cases", [])
        need(type(supplied) is list and len(supplied) == len({c["case_id"] for c in supplied})
             and expected <= {(c["case_id"], c["lane"]) for c in supplied}, "requirements.required_cases_removed")
        need(all(c.get("lane") in LANES for c in supplied), "requirements.unknown_case_lane")
        for case in supplied:
            if case.get("source_capture") is not None:
                capture = capture_value(root, case["source_capture"])
                expected_provider = {"powerbi": "powerbi-visual-capture.v1", "tableau": "tableau-visual-capture.v1",
                                     "sigma": "sigma-visual-capture.v1", "looker": "looker-visual-capture.v1",
                                     "hex": "hex-visual-capture.v1"}.get(source["source"].get("platform"))
                need(expected_provider is not None and capture["schema_version"] == expected_provider,
                     "requirements.capture_provider_mismatch")
                if capture["schema_version"] == "tableau-visual-capture.v1":
                    tableau_case_binding(asset, case, capture)
                elif capture["schema_version"] == "powerbi-visual-capture.v1":
                    powerbi_case_binding(asset, case, capture)
                elif capture["schema_version"] == "looker-visual-capture.v1":
                    looker_case_binding(asset, case, capture)
                elif capture["schema_version"] == "hex-visual-capture.v1":
                    frozen_identity = source["source"].get("source_identity")
                    if frozen_identity is not None:
                        need(all(capture["source"]["identity"].get(k) == frozen_identity.get(k)
                                 for k in ("source_origin", "workspace_id")),
                             "requirements.hex_workspace_mismatch")
                    hex_case_binding(asset, case, capture)
                else:
                    request = capture["request"]
                    need(asset["source_id"] == request["element_id"] and
                         asset["source_identity"].get("page_id") == request["page_id"], "requirements.capture_placement_mismatch")
        need(set(item.get("parity", {})) == set(asset["facets"]) and all(
            x in ("exact", "adapted", "unsupported", "unknown") for x in item["parity"].values()),
            "requirements.invalid_parity")
        need(item.get("implementation_route") in (None, "native", "custom", "app"),
             "requirements.invalid_implementation_route")
    return root, data


def rows(root, record):
    file = check_pin(root, record["file"])
    if record.get("format") == "json":
        value, _ = ap.read_json(file)
        need(type(value) is list and all(type(r) is dict for r in value), "results.json_rows_required")
    elif record.get("format") == "csv":
        reader = csv.DictReader(io.StringIO(file.read_text(encoding="utf-8-sig"), newline=""))
        names = reader.fieldnames
        need(names and all(names) and len(names) == len(set(names)), "results.invalid_csv_header")
        value = list(reader)
        need(all(None not in r and None not in r.values() for r in value), "results.ragged_csv")
    elif record.get("format") == "tableau-normalized":
        value, _ = ap.read_json(file)
        need(type(value) is dict and value.get("kind") == "tableau_normalized_results",
             "results.tableau_normalization_required")
        raw = check_pin(root, record.get("raw_file")).read_bytes()
        rebuilt = tableau_module().normalize_results(raw, value.get("parser_profile"), value.get("binding"))
        need(value == rebuilt, "results.tableau_normalization_changed")
        value = value["rows"]
    elif record.get("format") == "powerbi-normalized":
        value, _ = ap.read_json(file)
        need(type(value) is dict and value.get("kind") == "powerbi_normalized_results", "results.powerbi_normalization_required")
        raw = check_pin(root, record.get("raw_file")).read_bytes()
        rebuilt = powerbi_module().normalize_results(raw, value.get("parser_profile"), value.get("binding"))
        need(value == rebuilt, "results.powerbi_normalization_changed")
        value = value["rows"]
    elif record.get("format") == "looker-normalized":
        value, _ = ap.read_json(file)
        need(type(value) is dict and value.get("kind") == "looker_normalized_results", "results.looker_normalization_required")
        raw = check_pin(root, record.get("raw_file")).read_bytes()
        rebuilt = looker_module().normalize_results(raw, value.get("parser_profile"), value.get("binding"))
        need(value == rebuilt, "results.looker_normalization_changed")
        value = value["rows"]
    elif record.get("format") == "hex-normalized":
        value, _ = ap.read_json(file)
        need(type(value) is dict and value.get("kind") == "hex_normalized_results", "results.hex_normalization_required")
        raw = check_pin(root, record.get("raw_file")).read_bytes()
        rebuilt = hex_module().normalize_results(raw, value.get("parser_profile"), value.get("binding"))
        need(value == rebuilt, "results.hex_normalization_changed")
        value = value["rows"]
    else:
        raise ValueError("results.unknown_format")
    need(len(value) <= 100000, "results.row_limit")
    return value


def tableau_comparison_gaps(root, source, target, original, asset, case):
    bridge = tableau_module()
    gaps = []
    if case.get("source_capture") is None:
        return ["source.tableau_case_capture_required"]
    binding = tableau_case_binding(asset, case, original)
    request = original["request"]
    observation = original["source"].get("state_observation", {})
    if not observation.get("reference"):
        gaps.append("source.applied_state_unobserved")
    for key in ("filters", "parameters", "locale", "timezone", "selected_marks", "action_state", "custom_view_id"):
        requested = request["state"].get(key)
        if key in ("selected_marks", "action_state", "custom_view_id") and key not in request["state"]:
            continue
        if requested is None or observation.get(key) != requested or source["context"].get(key) != requested:
            gaps.append("source.capture_context." + key)
        if source["context"].get(key) != target["context"].get(key):
            gaps.append("context." + key)
    if observation.get("principal") != request["principal_ref"] or source["context"].get("principal") != request["principal_ref"]:
        gaps.append("source.capture_context.principal")
    if not observation.get("data_watermark") or observation["data_watermark"] != source["context"].get("data_watermark"):
        gaps.append("source.data_time_not_bound_to_capture")
    if original.get("status") != "complete":
        gaps.append("source.capture_incomplete")
    if original["source"].get("metadata_before") != original["source"].get("metadata_after"):
        gaps.append("source.capture_configuration_changed")
    file_record = source.get("raw_file") if source.get("format") == "tableau-normalized" else source["file"]
    attachments = [a for a in original["attachments"] if a["format"] == "csv"
        and a.get("view_id") == binding["view_id"] and a.get("worksheet_id") == binding["worksheet_id"]
        and a.get("state_sha256") == binding["state_sha256"] and a["sha256"] == file_record.get("sha256")]
    if len(attachments) != 1:
        gaps.append("source.results_not_bound_to_capture")
    if source.get("format") == "tableau-normalized":
        normalized = load(root, source["file"]["path"])
        expected = {"capture_content_hash": original["content_hash"], "view_id": binding["view_id"],
                    "worksheet_id": binding["worksheet_id"], "state_sha256": bridge.sha(request["state"]),
                    "attachment_sha256": file_record["sha256"]}
        if normalized.get("binding") != expected:
            gaps.append("source.normalization_binding_mismatch")
    return gaps


def powerbi_comparison_gaps(root, source, target, original, asset, case, columns=None):
    if case.get("source_capture") is None:
        return ["source.powerbi_case_capture_required"]
    binding = powerbi_case_binding(asset, case, original)
    request = original["request"]
    gaps = []
    if original.get("status") == "blocked":
        gaps.append("source.powerbi_capture_blocked")
    if not binding.get("query_id"):
        gaps.append("source.powerbi_query_identity_missing")
    for observation_key in ("value_state_observation", "render_state_observation"):
        observed = original["source"].get(observation_key, {})
        if not isinstance(observed, dict) or observed.get("applied") is not True or not observed.get("reference"):
            gaps.append("source." + observation_key + ".unverified")
            continue
        for key in ("page_id", "visual_id", "state_sha256"):
            if observed.get(key) != binding.get(key):
                gaps.append("source." + observation_key + "." + key)
        if observation_key == "value_state_observation" and observed.get("query_id") != binding.get("query_id"):
            gaps.append("source.value_query_mismatch")
        for key in ("filters", "bookmark", "locale", "timezone"):
            desired = request["state"].get(key)
            if key not in observed or observed[key] != desired or source["context"].get(key) != desired:
                gaps.append("source." + observation_key + "." + key)
            if source["context"].get(key) != target["context"].get(key):
                gaps.append("context." + key)
        principal = request["state"].get("principal") or request["principal_ref"]
        if observed.get("principal") != principal or source["context"].get("principal") != principal:
            gaps.append("source." + observation_key + ".principal")
        if not observed.get("data_watermark") or observed["data_watermark"] != source["context"].get("data_watermark"):
            gaps.append("source." + observation_key + ".data_watermark")
    if original["source"].get("metadata_before") != original["source"].get("metadata_after"):
        gaps.append("source.powerbi_configuration_changed")
    after_fingerprint = original["source"].get("definition_after_fingerprint")
    if after_fingerprint is not None and after_fingerprint != original["source"]["definition_fingerprint"]:
        gaps.append("source.powerbi_definition_changed")
    file_record = source.get("raw_file") if source.get("format") == "powerbi-normalized" else source["file"]
    attachments = [a for a in original["attachments"] if a.get("format") in ("json", "csv")
        and all(a.get(k) == binding.get(k) for k in ("page_id", "visual_id", "query_id", "state_sha256"))
        and a["sha256"] == file_record.get("sha256")]
    if len(attachments) != 1:
        gaps.append("source.powerbi_results_not_bound_to_capture")
    else:
        completeness = attachments[0].get("result_completeness")
        if type(completeness) is not dict or completeness.get("status") != "complete" or not completeness.get("reference"):
            gaps.append("source.powerbi_result_completeness_unverified")
    if source.get("format") == "powerbi-normalized":
        normalized = load(root, source["file"]["path"])
        expected = {"capture_content_hash": original["content_hash"], "page_id": binding["page_id"],
                    "visual_id": binding["visual_id"], "query_id": binding.get("query_id"),
                    "state_sha256": binding["state_sha256"], "attachment_sha256": file_record["sha256"]}
        if normalized.get("binding") != expected:
            gaps.append("source.powerbi_normalization_binding_mismatch")
        for field in normalized.get("parser_profile", {}).get("columns", []):
            currency = field.get("currency")
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get("source") == field["name"]]
                code = currency.get("code")
                if len(mapped) != 1 or source["context"].get("currencies", {}).get(field["name"]) != code or \
                        target["context"].get("currencies", {}).get(mapped[0]["target"]) != code:
                    gaps.append("context.currency." + field["name"])
    return gaps


def looker_comparison_gaps(root, source, target, original, asset, case, columns=None):
    if case.get("source_capture") is None:
        return ["source.looker_case_capture_required"]
    binding = looker_case_binding(asset, case, original)
    request, gaps = original["request"], []
    executed = next((q for q in request["queries"] if q["binding_id"] == binding.get("binding_id")), None)
    if executed and executed["options"]["force_production"] is True and source["context"].get("execution_mode") != "production":
        gaps.append("source.looker_force_production_contradiction")
    if not binding.get("binding_id"):
        gaps.append("source.looker_query_identity_missing")
    if original.get("status") == "blocked":
        gaps.append("source.looker_capture_blocked")
    for key in ("value_state_observation", "render_state_observation"):
        observation = original["source"].get(key, {})
        if type(observation) is list:
            matches = [o for o in observation if o.get("element_id") == binding.get("element_id") and
                       o.get("binding_id") == binding.get("binding_id")]
            observation = matches[0] if len(matches) == 1 else {}
        if type(observation) is not dict or observation.get("applied") is not True or not observation.get("reference"):
            gaps.append("source." + key + ".unverified")
            continue
        for field in ("element_id", "state_sha256", "binding_id", "query_fingerprint"):
            if observation.get(field) != binding.get(field):
                gaps.append("source." + key + "." + field)
        for field in ("filters", "parameters", "locale", "timezone"):
            desired = request["state"].get(field)
            if field not in observation or observation[field] != desired or source["context"].get(field) != desired:
                gaps.append("source." + key + "." + field)
            if source["context"].get(field) != target["context"].get(field):
                gaps.append("context." + field)
        principal = request["state"].get("principal") or request["principal_ref"]
        if observation.get("principal") != principal or source["context"].get("principal") != principal:
            gaps.append("source." + key + ".principal")
        for field in ("data_watermark", "cache_reference", "execution_mode"):
            if not observation.get(field) or observation[field] != source["context"].get(field):
                gaps.append("source." + key + "." + field)
            if source["context"].get(field) != target["context"].get(field):
                gaps.append("context." + field)
    if original["source"].get("metadata_before") != original["source"].get("metadata_after"):
        gaps.append("source.looker_configuration_changed")
    file_record = source.get("raw_file") if source.get("format") == "looker-normalized" else source["file"]
    attachments = [a for a in original["attachments"] if a.get("format") == "json_bi" and
        all(a.get(k) == binding.get(k) for k in ("binding_id", "element_id", "state_sha256", "query_fingerprint")) and
        a["sha256"] == file_record.get("sha256")]
    if len(attachments) != 1:
        gaps.append("source.looker_results_not_bound_to_capture")
    else:
        completeness = attachments[0].get("result_completeness", {})
        if completeness.get("status") != "complete" or not completeness.get("reference") or completeness.get("flags"):
            gaps.append("source.looker_result_completeness_unverified")
        if not attachments[0].get("effective_query_sha256"):
            gaps.append("source.looker_effective_query_unverified")
        effective = attachments[0].get("effective_query", {})
        if any(effective.get(k) for k in ("pivots", "total", "row_total", "subtotals")):
            gaps.append("source.looker_pivot_totals_require_separate_reconciliation")
        for key in ("value_state_observation", "render_state_observation"):
            observation = original["source"].get(key, {})
            if type(observation) is list:
                matches = [o for o in observation if o.get("binding_id") == binding.get("binding_id")]
                observation = matches[0] if len(matches) == 1 else {}
            if observation.get("effective_query_sha256") != attachments[0].get("effective_query_sha256") or not observation.get("query_state_reference"):
                gaps.append("source." + key + ".effective_query_state")
    if source.get("format") == "looker-normalized":
        normalized = load(root, source["file"]["path"])
        expected = {"capture_content_hash": original["content_hash"], "element_id": binding["element_id"],
                    "binding_id": binding.get("binding_id"), "query_fingerprint": binding.get("query_fingerprint"),
                    "state_sha256": binding["state_sha256"], "attachment_sha256": file_record["sha256"]}
        if normalized.get("binding") != expected:
            gaps.append("source.looker_normalization_binding_mismatch")
        for field in normalized.get("parser_profile", {}).get("columns", []):
            currency = field.get("currency")
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get("source") == field["name"]]
                if len(mapped) != 1 or source["context"].get("currencies", {}).get(field["name"]) != currency["code"] or \
                        target["context"].get("currencies", {}).get(mapped[0]["target"]) != currency["code"]:
                    gaps.append("context.currency." + field["name"])
    return gaps


def cell(value, field):
    if value is None or (value == "" and field.get("empty_is_null") is True):
        need(field.get("nullable") is True, "results.unexpected_null")
        return None
    kind = field.get("type")
    if kind == "number":
        need(type(value) in (str, int, float) and not isinstance(value, bool), "results.number_required")
        try:
            number = Decimal(str(value))
            need(number.is_finite(), "results.nonfinite_number")
            return number
        except InvalidOperation:
            raise ValueError("results.invalid_number") from None
    if kind == "string":
        need(type(value) is str, "results.string_required")
    elif kind == "boolean":
        need(type(value) is bool, "results.boolean_required")
    else:
        raise ValueError("results.unknown_column_type")
    return value


def compare(root, spec_path, destination):
    root, _ = ap.load_project(root)
    spec = load(root, spec_path)
    need(spec.get("kind") == "analyst_numeric_comparison_spec" and spec.get("schema_version") == 1,
         "comparison.invalid_contract")
    check_pin(root, spec["requirements"])
    _, req = requirements(root, spec["requirements"]["path"])
    check_pin(root, spec["candidate"])
    applicable = [c for i in req["items"] if i["disposition"] == "migrate" for c in i["required_cases"]]
    need(any(c["case_id"] == spec.get("case_id") and c["lane"] == "numeric" for c in applicable),
         "comparison.unknown_numeric_case")
    source, target = spec["source"], spec["target"]
    for side in (source, target):
        need(type(side.get("context")) is dict, "comparison.context_required")
    gaps = []
    for key in ("filters", "timezone", "data_watermark", "population"):
        a, b = source["context"].get(key), target["context"].get(key)
        if a is None or b is None or a != b:
            gaps.append("context." + key)
    if not spec.get("persona_equivalence_reference"):
        gaps.append("context.persona_equivalence")
    for name, side in (("source", source), ("target", target)):
        if not side["context"].get("principal"):
            gaps.append(name + ".principal_missing")
        if side.get("complete") is not True or not side.get("completeness_reference"):
            gaps.append(name + ".completeness_unverified")
    original = load(root, req["source_files"][0]["path"])
    selected_case = next(c for c in applicable if c["case_id"] == spec["case_id"])
    inventory_source = load(root, req["source_files"][1]["path"])["source"]
    source_platform = inventory_source["platform"]
    if source_platform == "hex" and not all(inventory_source.get("source_identity", {}).get(k)
                                             for k in ("source_origin", "workspace_id")):
        gaps.append("source.hex_frozen_workspace_identity_unknown")
    if source_platform == "hex" and not spec.get("persona_equivalence_reference"):
        gaps.append("source.hex_persona_equivalence_required")
    if source_platform in ("looker", "hex") and selected_case.get("source_capture") is None:
        gaps.append("source." + source_platform + "_case_capture_required")
    if selected_case.get("source_capture") is not None:
        selected_capture = capture_value(root, selected_case["source_capture"])
        if original.get("schema_version") == "sigma-visual-capture.v1" and (
                selected_capture.get("source", {}).get("coherence_sha256") != original.get("source", {}).get("coherence_sha256")):
            gaps.append("source.capture_configuration_changed")
        original = selected_capture
    if original.get("schema_version") == "tableau-visual-capture.v1":
        selected = next(i for i in req["items"] if any(c["case_id"] == spec["case_id"] for c in i["required_cases"]))
        gaps.extend(tableau_comparison_gaps(root, source, target, original, selected, selected_case))
    if original.get("schema_version") == "powerbi-visual-capture.v1":
        selected = next(i for i in req["items"] if any(c["case_id"] == spec["case_id"] for c in i["required_cases"]))
        gaps.extend(powerbi_comparison_gaps(root, source, target, original, selected, selected_case, spec.get("columns")))
    if original.get("schema_version") == "looker-visual-capture.v1":
        selected = next(i for i in req["items"] if any(c["case_id"] == spec["case_id"] for c in i["required_cases"]))
        gaps.extend(looker_comparison_gaps(root, source, target, original, selected, selected_case, spec.get("columns")))
    if original.get("schema_version") == "hex-visual-capture.v1":
        selected = next(i for i in req["items"] if any(c["case_id"] == spec["case_id"] for c in i["required_cases"]))
        gaps.extend(hex_comparison_gaps(root, source, target, original, selected, selected_case, spec.get("columns")))
    if original.get("schema_version") == "sigma-visual-capture.v1":
        capture = original["request"]
        selected = next(i for i in req["items"] if any(c["case_id"] == spec["case_id"] for c in i["required_cases"]))
        if selected["source_id"] != capture["element_id"] or selected["source_identity"].get("page_id") != capture["page_id"]:
            gaps.append("source.capture_is_for_another_visual")
        for key, expected_value in (("parameters", capture["parameters"]), ("timezone", capture["timezone"]),
                                    ("principal", capture["expected_user_id"])):
            if source["context"].get(key) != expected_value:
                gaps.append("source.capture_context." + key)
        attachments = [a for a in original["attachments"] if a["format"] == "json"]
        if len(attachments) != 1 or source["file"]["sha256"] != attachments[0]["sha256"]:
            gaps.append("source.results_not_bound_to_capture")
        if original.get("status") != "complete":
            gaps.append("source.capture_incomplete")
        # A caller cannot upgrade an unrecorded data-as-of by merely repeating it on both sides.
        if not capture.get("data_as_of_reference") or source["context"].get("data_watermark") != capture["data_as_of_reference"]:
            gaps.append("source.data_time_not_bound_to_capture")
    columns, keys = spec.get("columns"), spec.get("keys")
    need(type(columns) is list and columns and type(keys) is list and keys, "comparison.columns_keys_required")
    names = [c.get("name") for c in columns]
    need(all(type(n) is str and n for n in names) and len(names) == len(set(names))
         and set(keys) <= set(names) and len(keys) == len(set(keys)), "comparison.invalid_keys")
    for c in columns:
        need(c.get("type") in ("number", "string", "boolean") and all(
            type(c.get(side)) is str and c[side] for side in ("source", "target")), "comparison.invalid_column")
        tolerance = Decimal(str(c.get("absolute_tolerance", 0)))
        need(tolerance.is_finite() and tolerance >= 0 and
             (tolerance == 0 or (c.get("type") == "number" and c.get("tolerance_basis"))),
             "comparison.tolerance_basis_required")
    indexed = []
    orders = []
    counts = []
    for name, side in (("source", source), ("target", target)):
        data, index = rows(root, side), {}
        counts.append(len(data))
        for row in data:
            need(all(c.get(name) in row for c in columns), "results.missing_column")
            converted = {c["name"]: cell(row[c[name]], c) for c in columns}
            key = tuple(converted[k] for k in keys)
            need(key not in index, "results.duplicate_key")
            index[key] = converted
        indexed.append(index)
        orders.append(list(index))
    expected, actual = indexed
    missing, extra = set(expected) - set(actual), set(actual) - set(expected)
    mismatches = []
    order_mode = spec.get("row_order", "unordered")
    need(order_mode in ("unordered", "exact"), "comparison.invalid_row_order")
    if order_mode == "exact":
        need(bool(spec.get("order_basis")), "comparison.order_basis_required")
    order_mismatch = order_mode == "exact" and orders[0] != orders[1]
    for key in expected.keys() & actual.keys():
        for col in columns:
            a, b = expected[key][col["name"]], actual[key][col["name"]]
            equal = a == b
            if isinstance(a, Decimal) and isinstance(b, Decimal):
                equal = abs(a - b) <= Decimal(str(col.get("absolute_tolerance", 0)))
            if not equal:
                mismatches.append({"key_sha256": hashlib.sha256(repr(key).encode()).hexdigest(),
                                   "column": col["name"]})
    result = {"schema_version": 1, "kind": "analyst_numeric_comparison", "case_id": spec["case_id"],
              "requirements": spec["requirements"], "candidate": spec["candidate"],
              "spec": pin(root, spec_path), "files": [source["file"], target["file"]],
              "lane": "numeric", "status": "inconclusive" if gaps else
              ("fail" if missing or extra or mismatches or order_mismatch else "pass"),
              "source_rows": counts[0], "target_rows": counts[1], "missing_keys": len(missing),
              "extra_keys": len(extra), "mismatch_count": len(mismatches),
              "mismatches": mismatches[:100], "gaps": gaps,
              "evidence_scope": "supplied_results_and_declared_context_only", "native_validation": "not_established"}
    if order_mode == "exact":
        result["order_mismatch"] = order_mismatch
    return output(root, destination, result)


def coverage(root, requirements_path, candidate_path, evidence_paths, destination):
    root, req = requirements(root, requirements_path)
    req_pin, target_pin = pin(root, requirements_path), pin(root, candidate_path)
    candidate = load(root, candidate_path)
    surface = candidate.get("surface")
    if candidate.get("contract") == "oaa-omni-native-v1":
        surface = "dashboard"
    selected_items = surface_items(req, surface) if surface in ("app", "dashboard") else [
        i for i in req["items"] if i["disposition"] == "migrate"]
    expected = {c["case_id"]: c for i in selected_items for c in i["required_cases"]}
    observed, evidence_pins = {}, []
    for path in evidence_paths:
        evidence = load(root, path)
        need(evidence.get("requirements") == req_pin and evidence.get("candidate") == target_pin,
             "coverage.stale_evidence")
        need(evidence.get("case_id") in expected and evidence["case_id"] not in observed, "coverage.unknown_duplicate_case")
        need(evidence.get("lane") == expected[evidence["case_id"]]["lane"], "coverage.lane_mismatch")
        if evidence.get("kind") == "analyst_numeric_comparison":
            check_pin(root, evidence["spec"])
            for record in evidence["files"]:
                check_pin(root, record)
            # Recompute instead of accepting an edited pass flag or a resealed summary.
            import tempfile
            with tempfile.TemporaryDirectory(dir=root / "evidence") as temporary:
                temp = str((Path(temporary) / "check.json").relative_to(root))
                compare(root, evidence["spec"]["path"], temp)
                need(load(root, temp) == evidence, "coverage.comparison_changed")
        else:
            need(evidence.get("kind") == "analyst_observed_case" and evidence.get("schema_version") == 1,
                 "coverage.invalid_evidence_kind")
            need(evidence.get("observer") and evidence.get("expected") and evidence.get("observed")
                 and evidence.get("execution_reference"), "coverage.observation_required")
            need(evidence.get("status") in ("pass", "fail", "blocked", "not_run", "not_applicable"),
                 "coverage.invalid_status")
            need(type(evidence.get("files")) is list and evidence["files"], "coverage.retained_evidence_required")
            for record in evidence["files"]:
                check_pin(root, record)
            if evidence["status"] == "not_applicable":
                need(evidence.get("decision_reference"), "coverage.na_decision_required")
        observed[evidence["case_id"]] = evidence["status"]
        evidence_pins.append(pin(root, path))
    pending = [case for case in expected if observed.get(case) not in ("pass", "not_applicable")]
    deferred = [i["asset_key"] for i in req["items"] if i["disposition"] == "defer"]
    unresolved = [i["asset_key"] for i in req["items"] if i["disposition"] != "exclude"
                  and (surface not in ("app", "dashboard") or surface in item_surfaces(req, i))
                  and any(v in ("unknown", "unsupported") for v in i["parity"].values())]
    report = {"schema_version": 1, "kind": "analyst_visual_coverage", "requirements": req_pin,
              "candidate": target_pin, "evidence": evidence_pins, "assets_received": len(req["items"]),
              "retained_assets": sum(i["disposition"] != "exclude" for i in req["items"]),
              "required_cases": len(expected), "recorded_cases": observed, "pending_cases": pending,
              "deferred_assets": deferred, "unresolved_assets": unresolved, "coverage_ledger": "complete",
              "evidence_coverage": "partial" if pending or deferred or unresolved else "recorded_for_selected_scope",
              "native_validation": "requires_independent_review", "business_acceptance": "not_recorded",
              "publication": "not_recorded", "observations_authenticated": False}
    return output(root, destination, report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("prepare")
    init.add_argument("--original", required=True)
    init.add_argument("--inventory", required=True)
    init.add_argument("--website")
    init.add_argument("--output", required=True)
    check = sub.add_parser("check")
    check.add_argument("--requirements", required=True)
    num = sub.add_parser("compare")
    num.add_argument("--spec", required=True)
    num.add_argument("--output", required=True)
    report = sub.add_parser("coverage")
    report.add_argument("--requirements", required=True)
    report.add_argument("--candidate", required=True)
    report.add_argument("--evidence", nargs="*", default=[])
    report.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.project, args.original, args.inventory, args.output, args.website)
        elif args.command == "check":
            _, req = requirements(args.project, args.requirements)
            result = {"status": "consistent", "assets": len(req["items"]), "route": req["route"], "native_validation": "not_run"}
        elif args.command == "compare":
            result = compare(args.project, args.spec, args.output)
        else:
            result = coverage(args.project, args.requirements, args.candidate, args.evidence, args.output)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError, InvalidOperation):
        print("Visual workflow rejected invalid, changed, unsupported or unavailable evidence.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
