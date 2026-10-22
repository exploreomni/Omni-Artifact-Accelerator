"""Bounded Looker source evidence and typed result derivatives. No tenant IO.

API, DMA canonical, generic adapter and supplied dashboard YAML are distinct
contracts. Seals establish local integrity, never authenticated source state.
"""
import copy
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlencode

SCHEMA = "looker-visual-capture.v1"
MAX_BYTES = 8 * 1024 * 1024
ROUTES = {"unselected", "reuse_existing", "omni_semantic_reconstruction", "warehouse_first_refactor"}


def need(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and bool(value) and not any(ord(c) < 32 for c in value)


def module(name):
    spec = importlib.util.spec_from_file_location("looker_shared_" + name, Path(__file__).with_name(name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def decode(raw):
    return module("powerbi_visual").decode(raw)


def identity(value):
    return str(value) if type(value) in (str, int) and str(value) else None


def element_kind(element):
    maker = element.get("result_maker")
    owners = [element] + ([maker] if type(maker) is dict else [])
    if any(any(o.get(k) is not None for k in ("query", "query_id", "look", "look_id", "merge_result_id", "sql_query_id")) for o in owners):
        return "visual"
    if element.get("type") in ("text", "text_tile", "markdown", "image", "button", "note") or any(
            k in element for k in ("body_text", "body_text_as_html", "text")):
        return "content"
    return "unknown"


def enrich_api(result, payload, helpers):
    """Add independent placements/tabs/actions without changing original objects."""
    dashboard = payload["dashboard"] if payload.get("kind") == "looker_dashboard_export" else payload
    prefix = "/dashboard" if payload.get("kind") == "looker_dashboard_export" else ""
    did = identity(dashboard["id"])
    elements = {identity(e.get("id")): e for e in dashboard["dashboard_elements"] if identity(e.get("id"))}
    for asset in result["assets"]:
        is_element = asset["source_path"].startswith(prefix + "/dashboard_elements/") and asset["kind"] in ("visual", "content", "unknown")
        asset["source_identity"].update(source_platform="looker", dashboard_id=did, dashboard_payload_sha256=sha(dashboard),
            element_id=asset["source_id"] if is_element else None,
            query_visual=is_element and asset["kind"] == "visual")
        if is_element and asset["kind"] == "unknown":
            helpers["gap"](result, "looker.nonquery_element_unresolved", asset["source_path"])
    tab_ids = set()
    for collection in ("dashboard_tabs", "tabs"):
        if collection in dashboard:
            need(type(dashboard[collection]) is list, "looker.invalid_tabs")
            for i, tab in enumerate(dashboard[collection]):
                need(type(tab) is dict, "looker.invalid_tab")
                tab_id = identity(tab.get("id"))
                if tab_id is not None:
                    need(tab_id not in tab_ids, "looker.duplicate_tab_identity")
                    tab_ids.add(tab_id)
                helpers["add_asset"](result, "page", tab, prefix + "/" + collection + "/" + str(i), tab_id, did,
                    {"layout": helpers["facet"](tab, tuple(tab)), "content": helpers["facet"](tab, ("label", "title", "name"))},
                    source_identity={"source_platform": "looker", "dashboard_id": did, "tab_id": tab_id})
    for i, layout in enumerate(dashboard.get("dashboard_layouts") or []):
        lid = identity(layout.get("id"))
        for j, placement in enumerate(layout.get("dashboard_layout_components") or []):
            path = prefix + "/dashboard_layouts/" + str(i) + "/dashboard_layout_components/" + str(j)
            eid = identity(placement.get("dashboard_element_id"))
            tab = identity(placement.get("dashboard_tab_id", layout.get("dashboard_tab_id")))
            if tab is not None and tab not in tab_ids:
                helpers["gap"](result, "looker.placement_tab_unresolved", path)
            helpers["add_asset"](result, "placement", placement, path, placement.get("id"), did + "/" + str(lid),
                {"layout": helpers["facet"](placement, tuple(placement)), "interactions": {"status": "needs_review", "value": None}},
                source_identity={"source_platform": "looker", "dashboard_id": did, "element_id": eid,
                    "layout_id": lid, "tab_id": tab, "query_visual": eid in elements and element_kind(elements[eid]) == "visual"})
    # Actions and operational dependencies remain separate review obligations.
    for asset in list(result["assets"]):
        if asset["kind"] not in ("dashboard", "visual", "content", "unknown", "definition"):
            continue
        stack = [(asset["source_payload"], asset["source_path"])]
        while stack:
            item, path = stack.pop()
            if type(item) is dict:
                for key, value in item.items():
                    loc = path + "/" + key.replace("~", "~0").replace("/", "~1")
                    # Child assets are scanned independently; don't double count.
                    if key in ("dashboard_elements", "dashboard_layouts", "dashboard_filters", "query", "look", "result_maker"):
                        continue
                    if key in ("links", "drill_fields", "drill_url", "url", "actions", "scheduled_plans", "alerts", "embeds"):
                        helpers["add_asset"](result, "action", {key: value}, loc, None, did,
                            {"interactions": {"status": "needs_review", "value": value}},
                            source_identity={"source_platform": "looker", "dashboard_id": did,
                                             "element_id": asset["source_identity"].get("element_id")})
                        helpers["gap"](result, "looker.action_or_operation_requires_review", loc)
                    else:
                        stack.append((value, loc))
            elif type(item) is list:
                stack.extend((value, path + "/" + str(i)) for i, value in enumerate(item))
    return result


def safe_yaml(raw):
    need(type(raw) is bytes and len(raw) <= 2_000_000, "looker.yaml_size")
    try:
        import yaml
    except ImportError:
        raise ValueError("looker.optional_pyyaml_required_for_dashboard_yaml") from None
    try:
        decoded = raw.decode("utf-8-sig")
        depth = count = 0
        for event in yaml.parse(decoded, Loader=yaml.SafeLoader):
            count += 1
            need(count <= 20000, "looker.yaml_node_limit")
            need(not isinstance(event, yaml.AliasEvent) and not getattr(event, "anchor", None)
                 and not getattr(event, "tag", None), "looker.yaml_alias_anchor_or_tag")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                need(depth <= 32, "looker.yaml_depth_limit")
            if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        class UniqueLoader(yaml.SafeLoader):
            pass
        def mapping(loader, node):
            result = {}
            for key, value in node.value:
                name = loader.construct_object(key, deep=True)
                need(type(name) is str and name not in result and name != "<<", "looker.yaml_duplicate_or_nonstring_key")
                result[name] = loader.construct_object(value, deep=True)
            return result
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        value = yaml.load(decoded, Loader=UniqueLoader)
        # Reject implicit timestamps/nonfinite/custom scalar objects; no lossy coercion.
        encoded(value)
        need(type(value) is list and value and all(type(v) is dict and text(v.get("dashboard")) for v in value),
             "looker.yaml_dashboard_list_required")
        return value
    except (UnicodeError, yaml.YAMLError, TypeError, OverflowError):
        raise ValueError("looker.invalid_dashboard_yaml") from None


def yaml_assets(result, files, helpers, namespace):
    for file in files:
        path = file.get("source_path", file["path"])
        content = file.get("content_utf8")
        if not path.endswith((".dashboard", ".dashboard.lkml", ".dashboard.lookml")):
            helpers["add_asset"](result, "definition", file, "supplied/" + path, path, namespace,
                {"query": {"status": "needs_review", "value": content}}, id_kind="supplied_path")
            helpers["gap"](result, "looker.supplied_file_not_dashboard_yaml", path)
            continue
        need(type(content) is str, "looker.yaml_content_required")
        dashboards = safe_yaml(content.encode())
        for i, dashboard in enumerate(dashboards):
            did, base = dashboard["dashboard"], "supplied/" + path + "#/" + str(i)
            helpers["add_asset"](result, "dashboard", dashboard, base, did, namespace + "/" + path,
                {"layout": helpers["facet"](dashboard, ("layout", "preferred_viewer")),
                 "content": helpers["facet"](dashboard, ("title", "description"))}, id_kind="lookml_declared_name",
                source_identity={"source_platform": "looker", "dashboard_id": did, "source_file": path})
            for field, kind in (("elements", None), ("filters", "control")):
                values = dashboard.get(field, [])
                need(type(values) is list and all(type(v) is dict for v in values), "looker.yaml_invalid_collection")
                for j, value in enumerate(values):
                    locator = base + "/" + field + "/" + str(j)
                    query = any(k in value for k in ("model", "explore", "fields", "merged_queries"))
                    actual = kind or ("visual" if query else "content" if value.get("type") in
                        ("text", "text_tile", "button", "image", "markdown") else "unknown")
                    native = value.get("name")
                    helpers["add_asset"](result, actual, value, locator, native,
                        namespace + "/" + path + "/" + did,
                        {"query": helpers["facet"](value, ("model", "explore", "fields", "merged_queries", "dynamic_fields", "pivots", "sorts", "limit")),
                         "visual": helpers["facet"](value, ("type", "series_colors", "series_labels")),
                         "filters": helpers["facet"](value, ("filters", "listen", "default_value", "required")),
                         "layout": helpers["facet"](value, ("row", "col", "width", "height")),
                         "interactions": helpers["facet"](value, ("listen", "url", "links"), "needs_review")},
                        id_kind="lookml_declared_name", source_identity={"source_platform": "looker", "dashboard_id": did,
                        "element_id": native if field == "elements" else None, "query_visual": query,
                        "source_file": path, "lookml_effective_behavior": "not_evaluated"})
                    if field == "elements" and any(k in value for k in ("row", "col", "width", "height")):
                        helpers["add_asset"](result, "placement", {k: value[k] for k in ("row", "col", "width", "height") if k in value},
                            locator + "/placement", None, namespace + "/" + path + "/" + did,
                            {"layout": helpers["facet"](value, ("row", "col", "width", "height"))},
                            source_identity={"source_platform": "looker", "dashboard_id": did, "element_id": native,
                                             "query_visual": query, "source_file": path})
            helpers["gap"](result, "looker.lookml_effective_inheritance_liquid_access_unresolved", base)
    return result


def dma_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_canonical(value):
    need(type(value) is dict and value.get("schema_version") == 1 and value.get("kind") == "canonical_dashboard"
         and value.get("source", {}).get("platform") == "looker", "looker.canonical_contract")
    payload, source = value.get("source_payload"), value["source"]
    need(type(payload) is dict and source.get("payload_sha256") == dma_sha(payload), "looker.canonical_payload_hash")
    dashboard = payload.get("dashboard") if payload.get("kind") == "looker_dashboard_export" else payload
    need(source.get("dashboard_sha256") == dma_sha(dashboard) and source.get("dashboard_id") == identity(dashboard.get("id")),
         "looker.canonical_dashboard_mismatch")
    prefix = "/dashboard" if payload.get("kind") == "looker_dashboard_export" else ""
    for collection, native in (("tiles", "dashboard_elements"), ("filters", "dashboard_filters"), ("layouts", "dashboard_layouts")):
        rows = value.get(collection)
        need(type(rows) is list and len(rows) == len(dashboard.get(native) or []), "looker.canonical_denominator_mismatch")
        for index, row in enumerate(rows):
            original = dashboard[native][index]
            need(row.get("source_payload") == original and row.get("source_payload_sha256") == dma_sha(original)
                 and row.get("source_path") == prefix + "/" + native + "/" + str(index)
                 and row.get("id") == identity(original.get("id")), "looker.canonical_row_mismatch")
    return value


def parse_canonical(payload, raw, helpers, revision):
    validate_canonical(payload)
    result = helpers["parse_looker"](payload["source_payload"], encoded(payload["source_payload"]))
    original = helpers["base"](payload, raw, "looker", "supplied_looker_canonical_dashboard")
    result.update(source=original["source"], upstream_payload=copy.deepcopy(payload))
    result["source"]["producer"] = {"name": "DataModelAccelerator", "revision": revision,
        "revision_evidence": "operator_declared_not_authenticated"}
    result["looker_canonical_coverage"] = copy.deepcopy(payload.get("coverage"))
    for gap in payload.get("gaps", []):
        helpers["gap"](result, "looker.canonical_gap", gap.get("source_path"), gap)
    return result


def adapter_result(value):
    need(type(value) is dict and value.get("schema_version") == 1 and value.get("kind") == "source_adapter_result"
         and value.get("source") == "looker" and value.get("adapter_version") == 1
         and value.get("execution_performed") is False, "looker.generic_adapter_contract")
    files = value.get("source_files")
    need(type(files) is list and files and all(type(f) is dict and text(f.get("path")) and
         re.fullmatch("[a-f0-9]{64}", str(f.get("sha256"))) for f in files), "looker.adapter_files")
    index = {f["path"]: f for f in files}
    need(len(index) == len(files), "looker.adapter_duplicate_file")
    for path in index:
        module("tableau_visual").safe_path(path)
    for category in ("objects", "expressions", "dependencies", "gaps"):
        rows = value.get(category)
        need(type(rows) is list, "looker.adapter_collection_required")
        seen = set()
        for row in rows:
            evidence = row.get("evidence", {})
            need(evidence.get("path") in index and evidence.get("sha256") == index[evidence["path"]]["sha256"]
                 and text(evidence.get("locator")) and text(row.get("occurrence_id")), "looker.adapter_evidence_mismatch")
            need(row["occurrence_id"] not in seen, "looker.adapter_duplicate_occurrence")
            seen.add(row["occurrence_id"])
            if category == "expressions":
                need(type(row.get("text")) is str and row.get("content_sha256") == sha(row["text"].encode()),
                     "looker.adapter_expression_hash")
    return value


def parse_adapter(payload, raw, helpers, revision):
    adapter_result(payload)
    result = helpers["base"](payload, raw, "looker", "supplied_looker_source_adapter_result")
    result["source"]["producer"] = {"name": "DataModelAccelerator", "revision": revision,
        "revision_evidence": "operator_declared_not_authenticated"}
    # Actual DMA includes the exact JSON export as an expression. Reproject it
    # independently so its canonical wrapper cannot omit content/placements.
    projected = set()
    for expression in payload["expressions"]:
        evidence = expression["evidence"]
        if evidence["locator"] != "$source" or expression.get("language") != "json":
            continue
        path, text_source = evidence["path"], expression["text"]
        need(sha(text_source.encode()) == evidence["sha256"], "looker.adapter_original_hash")
        local = helpers["parse_looker"](decode(text_source.encode()), text_source.encode())
        for asset in local["assets"]:
            helpers["add_asset"](result, asset["kind"], asset["source_payload"], path + "#" + asset["source_path"],
                asset["source_id"], path + "/" + str(asset["source_identity"]["scope"]), copy.deepcopy(asset["facets"]),
                source_identity={**asset["source_identity"], "scope": path + "/" + str(asset["source_identity"]["scope"]),
                                 "adapter_source_file": path, "adapter_file_sha256": evidence["sha256"]})
        result["dependencies"].extend(local["dependencies"])
        projected.add(path)
    for row in payload["objects"]:
        evidence = row["evidence"]
        if evidence["path"] in projected:
            continue
        helpers["add_asset"](result, "definition", row, row["occurrence_id"], row.get("id"), evidence["path"],
            {"query": {"status": "declared", "value": row}, "security": {"status": "needs_review", "value": None}},
            id_kind="adapter_generated_id", source_identity={"source_platform": "looker", "native_id": row.get("native_id"),
                "evidence": evidence, "adapter_kind": row.get("kind")})
    for file in payload["source_files"]:
        if file["status"] != "parsed" or not any(r["evidence"]["path"] == file["path"] for r in payload["objects"]):
            helpers["add_asset"](result, "unknown", file, "/source_files/" + file["path"], file["path"], None,
                {"query": {"status": "needs_review", "value": file}}, id_kind="supplied_path")
    result["dependencies"].extend(copy.deepcopy(payload["dependencies"]))
    for gap in payload["gaps"]:
        helpers["gap"](result, "looker.adapter_gap", gap["evidence"]["path"], gap)
    helpers["gap"](result, "looker.adapter_declarations_not_complete_effective_dashboard")
    return result


def validate_capture(value):
    need(type(value) is dict and value.get("schema_version") == SCHEMA, "looker.capture_contract")
    need(value.get("content_hash") == sha({k: v for k, v in value.items() if k != "content_hash"}), "looker.capture_hash")
    need(value.get("target_write_authority") is False and value.get("native_validation") == "not_performed"
         and value.get("business_acceptance") == "not_assessed", "looker.capture_authority")
    capture = module("looker_capture")
    request = value.get("request")
    need(request == capture.validate_request(request) and value.get("request_sha256") == sha(request)
         and value.get("capture_id") == request["capture_id"], "looker.capture_request_hash")
    source = value.get("source")
    need(type(source) is dict, "looker.source_required")
    source_identity = source.get("identity", {})
    for key in ("source_instance", "api_version", "dashboard_id", "principal_ref", "source_revision"):
        need(source_identity.get(key) == request.get(key), "looker.source_identity_mismatch")
    if source_identity.get("observed_user_id") is not None:
        need(request.get("expected_user_id") in (None, source_identity["observed_user_id"]), "looker.observed_user_mismatch")
    dependencies, files = source.get("dependencies"), source.get("supplied_files")
    need(type(dependencies) is list and type(files) is list, "looker.source_files_required")
    seen = set()
    boundary = module("tableau_visual")
    for dep in dependencies:
        need(type(dep) is dict and dep.get("kind") in ("query", "look", "merge_query")
             and text(dep.get("id")) and type(dep.get("payload")) is dict
             and identity(dep["payload"].get("id")) == dep["id"]
             and dep.get("payload_sha256") == sha(dep["payload"]), "looker.dependency_identity_or_hash")
        key = (dep["kind"], dep["id"])
        need(key not in seen, "looker.duplicate_dependency")
        seen.add(key)
        boundary.file_pin(dep.get("file"))
    if files:
        module("powerbi_visual").definitions_index(files)
    if source.get("dashboard_export") is not None:
        need(source.get("dashboard_export_sha256") == sha(source["dashboard_export"]), "looker.dashboard_payload_hash")
        dash = capture.dashboard(source["dashboard_export"])
        need(request["dashboard_id"] in (None, identity(dash.get("id"))), "looker.dashboard_identity_mismatch")
        boundary.file_pin(source.get("dashboard_file"))
        # Partial projections preserve their expected obligations. Full selected
        # query association is checked only when element inventory is present.
        if type(dash.get("dashboard_elements")) is list:
            capture.validate_scope(request, dash, dependencies)
        tabs = {identity(t.get("id")) for key in ("tabs", "dashboard_tabs") for t in dash.get(key, []) if type(t) is dict}
        layouts = {identity(row.get("id")) for row in dash.get("dashboard_layouts", []) if type(row) is dict}
        for view in request["views"]:
            if view["tab_id"] is not None and tabs:
                need(view["tab_id"] in tabs, "looker.view_tab_mismatch")
            if view["layout_id"] is not None and layouts:
                need(view["layout_id"] in layouts, "looker.view_layout_mismatch")
        if tabs:
            need(all(tab in tabs for r in request["renders"] for tab in r["tab_ids"]), "looker.render_tab_mismatch")
    elif request["queries"] or request["renders"]:
        need(value.get("status") != "complete", "looker.false_capture_completion")
    empty_partial = (not source.get("dashboard_export") and not dependencies and not files and
                     value.get("status") in ("partial", "blocked") and not value.get("attachments"))
    need((empty_partial and source.get("definition_fingerprint") is None) or
         source.get("definition_fingerprint") == capture.fingerprints(source), "looker.definition_fingerprint")
    expected_namespace = (request["source_instance"] + "/dashboard/" + capture.segment(request["dashboard_id"])) if (
        request["source_instance"] and request["dashboard_id"]) else "definition:" + str(source.get("definition_fingerprint"))
    need((empty_partial and source_identity.get("namespace") is None) or
         source_identity.get("namespace") == expected_namespace, "looker.namespace_mismatch")
    query_index = {q["binding_id"]: q for q in request["queries"]}
    render_index = {r["render_id"]: r for r in request["renders"]}
    attachments = value.get("attachments")
    need(type(attachments) is list, "looker.attachments_required")
    indexed, folded = {}, {}
    for a in attachments:
        boundary.file_pin(a)
        key = unicodedata.normalize("NFC", a["path"]).casefold()
        need(key not in folded, "looker.attachment_collision")
        indexed[a["path"]], folded[key] = a, a["path"]
        need(a.get("request_sha256") == value["request_sha256"] and a.get("state_sha256") == sha(request["state"]),
             "looker.attachment_state_mismatch")
        need(a.get("dashboard_id") == request["dashboard_id"], "looker.attachment_dashboard_mismatch")
        if a.get("binding_id") is not None:
            q = query_index.get(a["binding_id"])
            need(q is not None and all(a.get(k) == q.get(k) for k in ("element_id", "query_id")) and
                 a.get("format") == "json_bi" and a.get("query_fingerprint") == sha(capture.query_request(q)),
                 "looker.attachment_query_mismatch")
            need(type(a.get("effective_query")) is dict, "looker.effective_query_required")
            if a.get("effective_query") is not None:
                need(a.get("effective_query_sha256") == sha(a["effective_query"]), "looker.effective_query_hash")
                if q["inline_query"] is not None:
                    need(a["effective_query"] == q["inline_query"], "looker.inline_effective_query_mismatch")
                else:
                    resolved = [d["payload"] for d in dependencies if d["kind"] == "query" and d["id"] == q["query_id"]]
                    need(len(resolved) == 1 and a["effective_query"] == resolved[0], "looker.saved_effective_query_mismatch")
            if a.get("source_query_id") is not None:
                need(a["source_query_id"] == q.get("source_query_id"), "looker.source_query_identity_mismatch")
                baseline = [d["payload"] for d in dependencies if d["kind"] == "query" and d["id"] == a["source_query_id"]]
                need(len(baseline) == 1 and a.get("source_query_sha256") == sha(baseline[0]), "looker.source_query_hash")
        elif a.get("render_id") is not None:
            r = render_index.get(a["render_id"])
            need(r is not None and a.get("format") == "png" and a.get("tab_ids") == r["tab_ids"],
                 "looker.attachment_render_mismatch")
            body = {"dashboard_filters": urlencode(request["state"]["filters"]), "dashboard_style": r["dashboard_style"], "tab_ids": r["tab_ids"]}
            options = {"width": r["width"], "height": r["height"]}
            if r["theme"] is not None:
                options["theme"] = r["theme"]
            need(a.get("render_request_sha256") == sha({"body": body, "options": options}), "looker.render_request_hash")
            job = value.get("jobs", {}).get("render." + r["render_id"], {})
            need(text(a.get("render_task_id")) and job.get("id") == a["render_task_id"] and
                 job.get("last_status", {}).get("id") == a["render_task_id"] and job["last_status"].get("status") == "success",
                 "looker.render_job_mismatch")
        else:
            raise ValueError("looker.unbound_attachment")
    need(value.get("status") in ("complete", "partial", "blocked") and type(value.get("gaps")) is list,
         "looker.capture_status")
    captures = value.get("captures")
    need(type(captures) is list, "looker.captures_required")
    observed = set()
    expected = {("query", q) for q in query_index} | {("render", r) for r in render_index}
    for row in captures:
        key = (row.get("kind"), row.get("binding_id") if row.get("kind") == "query" else row.get("render_id"))
        need(key in expected and key not in observed and row.get("state_sha256") == sha(request["state"])
             and row.get("status") in ("complete", "partial", "blocked"), "looker.capture_binding_mismatch")
        observed.add(key)
        need(type(row.get("attachments")) is list, "looker.capture_attachments_required")
        for path in row["attachments"]:
            need(path in indexed and indexed[path].get("binding_id" if key[0] == "query" else "render_id") == key[1],
                 "looker.capture_attachment_mismatch")
        if row["status"] == "complete":
            need(bool(row["attachments"]), "looker.empty_complete_capture")
    if value["status"] == "complete":
        need(observed == expected and all(r["status"] == "complete" for r in captures), "looker.false_capture_completion")
        need(source.get("metadata_before") == source.get("metadata_after"), "looker.complete_configuration_drift")
    return value


def verify_capture_files(value, root):
    validate_capture(value)
    boundary, capture = module("tableau_visual"), module("looker_capture")
    verified = {}
    for record in capture.file_pins(value):
        boundary.file_pin(record)
        raw = boundary.read_confined(root, record["path"])
        need(len(raw) == record["bytes"] and sha(raw) == record["sha256"], "looker.actual_file_mismatch")
        if record.get("content_utf8") is not None:
            need(raw == record["content_utf8"].encode(), "looker.actual_text_mismatch")
        if record.get("format") == "png":
            boundary.capture_files_module().png_info(raw)
        if record.get("format") == "json_bi":
            query = next(q for q in value["request"]["queries"] if q["binding_id"] == record["binding_id"])
            quality = capture.query_quality(decode(raw), query["options"]["limit"])
            recorded = record.get("result_completeness", {})
            need(not quality["flags"] or (recorded.get("status") != "complete" and
                 set(quality["flags"]) <= set(recorded.get("flags", []))), "looker.result_quality_contradiction")
        if record["path"] in verified:
            need(verified[record["path"]] == record["sha256"], "looker.conflicting_file_pin")
        verified[record["path"]] = record["sha256"]
    source = value["source"]
    if source.get("dashboard_file"):
        need(decode(boundary.read_confined(root, source["dashboard_file"]["path"])) == source["dashboard_export"],
             "looker.dashboard_original_mismatch")
    for dep in source["dependencies"]:
        need(decode(boundary.read_confined(root, dep["file"]["path"])) == dep["payload"], "looker.dependency_original_mismatch")
    return {"status": "verified_local_bytes", "files": verified, "native_validation": "not_performed"}


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    source, request = payload["source"], payload["request"]
    base = helpers["base"](payload, raw, "looker", "supplied_looker_visual_capture")
    if source.get("dashboard_export") is not None:
        original = source["dashboard_export"]
        dash = module("looker_capture").dashboard(original)
        if type(dash.get("dashboard_elements")) is list:
            result = helpers["parse_looker"](original, encoded(original), source["dependencies"])
            result.update(source=base["source"], upstream_payload=copy.deepcopy(payload))
        else:
            result = base
            helpers["add_asset"](result, "dashboard", original, "/dashboard_export", dash["id"], None)
            helpers["gap"](result, "looker.element_inventory_unavailable")
    else:
        result = base
    namespace = source["identity"].get("namespace") or "unobserved:" + payload["request_sha256"]
    result["source"].update(definition_fingerprint=source.get("definition_fingerprint"), capture_content_hash=payload["content_hash"])
    for asset in result["assets"]:
        asset["source_identity"].update(source_instance=request["source_instance"],
            definition_fingerprint=source["definition_fingerprint"], namespace=namespace,
            scope=namespace + "/" + str(asset["source_identity"].get("scope")))
    yaml_assets(result, source["supplied_files"], helpers, namespace)
    result["migration_context"] = {"route": None if request["route"] == "unselected" else request["route"],
                                   "route_reference": request.get("route_reference"), "target_surface": request["target_surface"]}
    for dep in source["dependencies"]:
        if dep["kind"] == "merge_query":
            helpers["add_asset"](result, "definition", dep["payload"], "/merged_dependencies/" + dep["id"], dep["id"], namespace + "/merge_query",
                {"query": {"status": "needs_review", "value": dep["payload"]}}, source_identity={"source_platform": "looker"})
            helpers["gap"](result, "looker.merged_execution_unqualified", "/merged_dependencies/" + dep["id"])
    known = {(a["source_path"] or "/"): a for a in result["assets"]}
    expected = {o["object_id"]: o for o in request["expected_manifest"]["objects"]}
    for path in sorted(set(expected) - set(known)):
        helpers["add_asset"](result, "unknown", {**expected[path], "missing_from_capture": True}, "/expected_missing/" + path,
            path, namespace, id_kind="expected_unobserved_locator", source_identity={"source_platform": "looker", "expected_kind": expected[path]["kind"]})
        helpers["gap"](result, "looker.expected_object_missing", path)
    mismatch = [p for p in set(known) & set(expected) if known[p]["kind"] != expected[p]["kind"]]
    for path in mismatch:
        helpers["gap"](result, "looker.expected_kind_mismatch", path)
    result["looker_coverage"] = {"expected_objects": len(expected), "observed_objects": len(known),
        "missing_expected": sorted(set(expected) - set(known)), "unexpected_objects": sorted(set(known) - set(expected)),
        "kind_mismatch": sorted(mismatch), "manifest_completeness": request["expected_manifest"]["completeness"],
        "definition_coverage": "reconciled_supplied_manifest" if expected and set(expected) == set(known) and not mismatch else "partial",
        "behavior_coverage": "not_verified"}
    for gap in payload["gaps"]:
        helpers["gap"](result, "looker.capture_gap", detail=gap)
    helpers["gap"](result, "looker.actual_files_require_verification")
    helpers["gap"](result, "looker.requested_state_is_not_observed_state")
    return result


def normalize_results(raw, profile, binding):
    need(type(raw) is bytes and len(raw) <= MAX_BYTES and type(profile) is dict
         and profile.get("schema_version") == 1 and profile.get("format") in ("csv", "json_bi")
         and profile.get("subtotal_policy") == "preserve", "looker.normalization_profile")
    need(type(binding) is dict and binding.get("attachment_sha256") == sha(raw)
         and all(text(binding.get(k)) for k in ("capture_content_hash", "element_id", "state_sha256", "binding_id", "query_fingerprint")),
         "looker.normalization_binding")
    headers, columns = profile.get("headers"), profile.get("columns")
    need(type(headers) is list and headers and all(text(h) for h in headers) and type(columns) is list
         and len(columns) == len(headers) and [c.get("ordinal") for c in columns] == list(range(len(headers)))
         and all(text(c.get("name")) for c in columns) and len({c["name"] for c in columns}) == len(columns),
         "looker.explicit_ordinal_mapping_required")
    if len(set(headers)) != len(headers):
        need(text(profile.get("duplicate_header_resolution_reference")) and profile["format"] == "csv",
             "looker.duplicate_headers_unresolved")
    if profile["format"] == "csv":
        need(profile.get("encoding") == "utf-8", "looker.csv_encoding_required")
        try:
            data = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
        except (UnicodeError, csv.Error):
            raise ValueError("looker.invalid_csv") from None
        need(data and data[0] == headers, "looker.csv_headers_mismatch")
        rows = data[1:]
    else:
        data = decode(raw)
        # The capture remains JSON bytes. Parse decimal tokens exactly for the
        # derivative rather than round them through a binary float.
        data = json.loads(raw.decode("utf-8-sig"), parse_float=Decimal)
        need(type(data) is dict, "looker.json_bi_object_required")
        need(not any(data.get(k) for k in ("pivots", "totals_data", "totals", "row_totals")),
             "looker.pivot_or_total_requires_separate_explicit_mapping")
        quality = module("looker_capture").query_quality(data, 100001)
        need(not any(k in quality["flags"] for k in ("error", "errors")), "looker.result_error")
        path = profile.get("rows_pointer")
        need(type(path) is str and (path == "" or path.startswith("/")), "looker.explicit_rows_pointer_required")
        for part in path.split("/")[1:]:
            if type(data) is dict:
                need("error" not in data and "errors" not in data, "looker.result_error")
                part = part.replace("~1", "/").replace("~0", "~")
                need(part in data, "looker.result_pointer_missing")
                data = data[part]
            elif type(data) is list:
                need(part.isdecimal() and int(part) < len(data), "looker.result_pointer_missing")
                data = data[int(part)]
            else:
                raise ValueError("looker.result_pointer_missing")
        need(type(data) is list, "looker.json_rows_or_columns_required")
        mode = profile.get("row_encoding", "object")
        need(mode in ("object", "json_string"), "looker.row_encoding_profile_required")
        if mode == "json_string":
            need(all(type(row) is str for row in data), "looker.encoded_row_required")
            for row in data:
                decode(row.encode())
            data = [json.loads(row, parse_float=Decimal) for row in data]
        need(all(type(r) is dict and set(r) == set(headers) for r in data), "looker.json_rows_or_columns_required")
        rows = [[r[h] for h in headers] for r in data]
        mode = profile.get("cell_mode")
        need(mode in ("scalar", "value_object"), "looker.explicit_cell_mode_required")
        if mode == "value_object":
            need(all(type(c) is dict and "value" in c for row in rows for c in row), "looker.value_cell_required")
            rows = [[c["value"] for c in row] for row in rows]
    need(len(rows) <= 100000, "looker.result_row_limit")
    output = []
    for row in rows:
        need(len(row) == len(columns), "looker.ragged_rows")
        converted = {}
        for col, value in zip(columns, row):
            need(type(col.get("null_tokens")) is list, "looker.explicit_null_mapping_required")
            if value is None or (type(value) is str and value in col["null_tokens"]):
                need(col.get("nullable") is True, "looker.unexpected_null")
                result = None
            elif col.get("type") == "string":
                need(type(value) is str, "looker.string_required")
                result = value
            elif col.get("type") == "boolean":
                need(type(value) is bool, "looker.boolean_required")
                result = value
            elif col.get("type") == "date":
                need(type(value) is str and text(col.get("date_format")), "looker.explicit_date_format_required")
                result = datetime.strptime(value, col["date_format"]).isoformat()
            elif col.get("type") == "number":
                need(type(value) in (str, int, float, Decimal), "looker.number_required")
                current = str(value)
                currency = col.get("currency")
                if currency is not None:
                    need(type(currency) is dict and type(currency.get("code")) is str and
                         re.fullmatch(r"[A-Z]{3}", currency["code"]) and
                         type(currency.get("prefix")) is str and type(currency.get("suffix")) is str and
                         type(currency.get("negative_parentheses")) is bool, "looker.explicit_currency_profile_required")
                    negative = current.startswith("(") and current.endswith(")")
                    if negative:
                        need(currency["negative_parentheses"], "looker.currency_parentheses_not_declared")
                        current = current[1:-1]
                    prefix, suffix = currency["prefix"], currency["suffix"]
                    need(current.startswith(prefix) and current.endswith(suffix), "looker.currency_symbol_mismatch")
                    current = current[len(prefix):len(current) - len(suffix) if suffix else None]
                    if negative:
                        need(not current.startswith(("-", "+")), "looker.ambiguous_currency_sign")
                        current = "-" + current
                separator, group = col.get("decimal_separator"), col.get("group_separator")
                need(separator in (".", ",") and group in (None, ".", ",", " ") and group != separator
                     and type(col.get("percent")) is bool, "looker.explicit_numeric_profile_required")
                if type(value) in (int, float, Decimal) and currency is None and col["percent"] is False:
                    need(separator == "." and group is None, "looker.typed_number_has_no_locale_format")
                    number = Decimal(str(value))
                    need(number.is_finite(), "looker.nonfinite_number")
                    converted[col["name"]] = str(number)
                    continue
                pattern = r"[+-]?(?:\d{1,3}(?:" + re.escape(group) + r"\d{3})+|\d+)" if group else r"[+-]?\d+"
                pattern += "(?:" + re.escape(separator) + r"\d+)?" + ("%" if col["percent"] else "")
                need(re.fullmatch(pattern, current) is not None, "looker.invalid_formatted_number")
                if col["percent"]:
                    current = current[:-1]
                if group:
                    current = current.replace(group, "")
                try:
                    number = Decimal(current.replace(separator, "."))
                    if col["percent"]:
                        parts = number.as_tuple()
                        number = Decimal((parts.sign, parts.digits, parts.exponent - 2))
                    need(number.is_finite(), "looker.nonfinite_number")
                    result = str(number)
                except InvalidOperation:
                    raise ValueError("looker.invalid_number") from None
            else:
                raise ValueError("looker.unsupported_column_type")
            converted[col["name"]] = result
        output.append(converted)
    return {"schema_version": 1, "kind": "looker_normalized_results", "raw_sha256": sha(raw),
            "parser_profile": copy.deepcopy(profile), "binding": copy.deepcopy(binding), "headers": headers,
            "row_count": len(output), "rows": output, "row_order": "preserved", "completeness": "not_established"}
