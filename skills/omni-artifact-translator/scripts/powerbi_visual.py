"""Independent, bounded PBIR visual evidence. No DAX/M execution or tenant IO.

The semantic model is optional for enumeration. Original files and unsupported
properties survive; this reader is not the Power BI renderer or a schema engine.
"""
import copy
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import unicodedata

SCHEMA = "powerbi-visual-capture.v1"
MAX_FILES = 512
MAX_BYTES = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
ROUTES = {"unselected", "reuse_existing", "omni_semantic_reconstruction", "warehouse_first_refactor"}


def need(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and bool(value) and not any(ord(c) < 32 for c in value)


def common():
    spec = importlib.util.spec_from_file_location("powerbi_shared_files", Path(__file__).with_name("tableau_visual.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode(raw):
    need(type(raw) is bytes and len(raw) <= MAX_BYTES, "powerbi.json_size")
    def pairs(items):
        obj = {}
        for key, value in items:
            need(key not in obj, "powerbi.duplicate_json_key")
            obj[key] = value
        return obj
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("powerbi.nonfinite_json")))
        stack, count = [(value, 0)], 0
        while stack:
            item, depth = stack.pop()
            count += 1
            need(count <= 150000 and depth <= 48, "powerbi.structure_limit")
            if type(item) is dict:
                stack.extend((v, depth + 1) for v in item.values())
            elif type(item) is list:
                stack.extend((v, depth + 1) for v in item)
        return value
    except (UnicodeError, RecursionError, json.JSONDecodeError):
        raise ValueError("powerbi.invalid_json") from None


def definitions_index(files):
    need(type(files) is list and 0 < len(files) <= MAX_FILES, "powerbi.definition_files_required")
    total, index, paths, prefixes = 0, {}, set(), {}
    boundary = common()
    for file in files:
        boundary.file_pin(file)
        original = file.get("source_path", file["path"])
        parts = boundary.safe_path(original).parts
        key = unicodedata.normalize("NFC", original).casefold()
        need(key not in paths, "powerbi.definition_path_collision")
        for size in range(1, len(parts) + 1):
            prefix = "/".join(parts[:size])
            folded = unicodedata.normalize("NFC", prefix).casefold()
            need(folded not in prefixes or prefixes[folded] == prefix, "powerbi.definition_path_collision")
            need(size == len(parts) or folded not in paths, "powerbi.file_directory_collision")
            prefixes[folded] = prefix
        need(not any(p.startswith(key + "/") for p in paths), "powerbi.file_directory_collision")
        paths.add(key)
        need(file.get("content_utf8") is None or type(file["content_utf8"]) is str, "powerbi.definition_content_required")
        total += file["bytes"]
        need(file["bytes"] <= MAX_BYTES and total <= MAX_TOTAL, "powerbi.definition_hash_or_size")
        if file.get("content_utf8") is not None:
            raw = file["content_utf8"].encode("utf-8")
            need(len(raw) == file["bytes"] and sha(raw) == file["sha256"], "powerbi.definition_hash_or_size")
        index[original] = file
    return index


def definition_fingerprint(files):
    index = definitions_index(files)
    return sha([{"source_path": path, "sha256": index[path]["sha256"], "bytes": index[path]["bytes"]}
                for path in sorted(index)])


def pointer(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def inspect_definitions(files):
    """Enumerate every PBIR file without requiring PBIP/model.bim/TMDL binding."""
    index = definitions_index(files)
    objects, gaps, dependencies = [], [], []
    native_ids = set()
    def gap(code, path, locator="/"):
        entry = {"code": code, "source_path": path, "locator": locator}
        if entry not in gaps:
            gaps.append(entry)
    def add(kind, path, data, page_id=None, visual_id=None, locator="/", native_id=None, **extra):
        oid = path + "#" + locator
        if native_id is not None:
            key = (kind, page_id if kind == "visual" else None, native_id)
            if key in native_ids:
                gap("powerbi.duplicate_native_identity", path, locator)
            native_ids.add(key)
        row = {"object_id": oid, "kind": kind, "source_path": path, "locator": locator,
               "native_id": native_id, "page_id": page_id, "visual_id": visual_id,
               "native": copy.deepcopy(data), **extra}
        objects.append(row)
        return row
    parsed = {}
    for path, file in index.items():
        if file.get("content_utf8") is None:
            add("content", path, {"file_sha256": file["sha256"], "format": Path(path).suffix, "binary": True})
            gap("powerbi.binary_resource_requires_review", path)
        elif path.lower().endswith((".json", ".pbir", ".pbip", ".pbism", ".bim", ".platform")):
            try:
                parsed[path] = decode(file["content_utf8"].encode())
            except ValueError:
                add("unknown", path, {"unparsed_file_sha256": file["sha256"]})
                gap("powerbi.definition_json_unparsed", path)
        else:
            add("definition", path, {"file_sha256": file["sha256"], "format": Path(path).suffix})
            gap("powerbi.non_pbir_definition_retained", path)
    for path, data in parsed.items():
        if type(data) is not dict:
            add("unknown", path, data)
            gap("powerbi.definition_object_required", path)
            continue
        page_match = re.search(r"(?:^|/)definition/pages/([^/]+)/page\.json$", path)
        visual_match = re.search(r"(?:^|/)definition/pages/([^/]+)/visuals/([^/]+)/visual\.json$", path)
        if path.endswith("definition/report.json") or path == "report.json":
            row = add("dashboard", path, data)
            if path == "report.json":
                gap("powerbi.legacy_report_layout_uninterpreted", path)
        elif page_match:
            page_id = data.get("name") if text(data.get("name")) else None
            row = add("page", path, data, page_id=page_id, native_id=page_id)
            if page_id != page_match[1]:
                gap("powerbi.page_identity_path_mismatch", path)
        elif visual_match:
            page_id = visual_match[1]
            visual_id = data.get("name") if text(data.get("name")) else None
            visual = data.get("visual")
            # Query presence owns the numeric obligation, irrespective of role,
            # visual type, malformed projection or hidden/group/mobile state.
            kind = "layout" if "visualGroup" in data else "unknown"
            if type(visual) is dict:
                if "query" in visual:
                    kind = "visual"
                elif visual.get("visualType") in ("textbox", "image", "shape", "actionButton", "button"):
                    kind = "content"
                elif visual.get("visualType") == "slicer":
                    kind = "control"
                else:
                    gap("powerbi.nonquery_visual_type_unresolved", path)
            row = add(kind, path, data, page_id=page_id, visual_id=visual_id, native_id=visual_id,
                      query_visual=type(visual) is dict and "query" in visual)
            if visual_id != visual_match[2]:
                gap("powerbi.visual_identity_path_mismatch", path)
            if type(visual) is dict:
                gap("powerbi.visual_behavior_uninterpreted", path)
                if visual.get("visualType") == "slicer" and kind != "control":
                    add("control", path, visual, page_id, visual_id, "/visual", native_id=visual_id)
                if "query" in visual:
                    query = visual["query"]
                    roles = query.get("queryState") if type(query) is dict else None
                    row["query_roles"] = sorted(roles) if type(roles) is dict else []
                    if type(roles) is not dict:
                        gap("powerbi.query_roles_uninterpreted", path, "/visual/query")
                    gap("powerbi.query_semantics_require_binding", path, "/visual/query")
            parent = data.get("parentGroupName")
            if parent is not None:
                dependencies.append({"from": row["object_id"], "native_parent_group": parent, "page_id": page_id,
                                     "kind": "declared_visual_group", "resolution": "unverified"})
        elif "/bookmarks/" in path.lower() or path.lower().endswith("/bookmarks.json"):
            row = add("action", path, data, native_id=data.get("name") if text(data.get("name")) else None)
            gap("powerbi.bookmark_state_uninterpreted", path)
        elif "mobile" in path.lower():
            row = add("device_layout", path, data)
            gap("powerbi.mobile_layout_uninterpreted", path)
        elif "theme" in path.lower():
            row = add("definition", path, data)
            gap("powerbi.theme_translation_requires_review", path)
        else:
            row = add("definition", path, data)
        # Own scoped controls/filters/interactions separately; retain whole native
        # object too. Unknown properties cannot abort subsequent file enumeration.
        stack = [(data, "")]
        while stack:
            item, at = stack.pop()
            if type(item) is dict:
                for key, value in item.items():
                    loc = at + "/" + pointer(key)
                    if key == "filterConfig":
                        add("filter", path, value, row.get("page_id"), row.get("visual_id"), loc)
                        gap("powerbi.filter_behavior_uninterpreted", path, loc)
                    elif key in ("visualInteractions", "drillthrough", "drillThrough", "action", "navigation", "bookmarks", "syncGroup"):
                        add("action", path, value, row.get("page_id"), row.get("visual_id"), loc)
                        gap("powerbi.interaction_behavior_uninterpreted", path, loc)
                    elif key in ("mobileLayout", "mobileLayouts"):
                        add("device_layout", path, value, row.get("page_id"), row.get("visual_id"), loc)
                    stack.append((value, loc))
            elif type(item) is list:
                stack.extend((value, at + "/" + str(i)) for i, value in enumerate(item))
    pages = {o["page_id"] for o in objects if o["kind"] == "page" and o["page_id"]}
    for row in objects:
        if row["visual_id"] is not None and row["page_id"] not in pages:
            gap("powerbi.visual_page_unresolved", row["source_path"])
    for path, data in parsed.items():
        if path.endswith("definition/pages/pages.json") and type(data) is dict:
            order = data.get("pageOrder")
            if type(order) is list:
                if len([x for x in order if type(x) is str]) != len(order) or len(set(x for x in order if type(x) is str)) != len(order):
                    gap("powerbi.page_order_ambiguous", path)
                for ordinal, native in enumerate(order):
                    if not text(native):
                        continue
                    if native not in pages:
                        add("page", path, {"name": native, "missing_page_file": True}, page_id=native,
                            native_id=native, locator="/pageOrder/" + str(ordinal))
                        gap("powerbi.declared_page_file_missing", path)
                if pages - set(x for x in order if type(x) is str):
                    gap("powerbi.page_outside_declared_order", path)
            else:
                gap("powerbi.page_order_unavailable", path)
    need(len(objects) <= 5000, "powerbi.object_limit")
    return {"schema_version": 1, "kind": "powerbi_visual_structure", "objects": objects,
            "gaps": gaps, "dependencies": dependencies, "definition_fingerprint": definition_fingerprint(files),
            "semantic_interpretation": "not_performed", "native_validation": "not_performed"}


def adapter_result(value, files=None):
    need(type(value) is dict and value.get("kind") == "source_adapter_result" and value.get("schema_version") == 1
         and value.get("source") == "powerbi" and value.get("adapter_version") == 1,
         "powerbi.generic_adapter_contract")
    need(value.get("execution_performed") is False, "powerbi.generic_adapter_execution_claim")
    source = value.get("source_files")
    need(type(source) is list and all(type(x) is dict and text(x.get("path")) for x in source), "powerbi.adapter_files_required")
    index = {x["path"]: x for x in source}
    need(len(index) == len(source), "powerbi.adapter_duplicate_file")
    for category in ("objects", "expressions", "dependencies", "gaps"):
        rows = value.get(category)
        need(type(rows) is list and all(type(x) is dict for x in rows), "powerbi.adapter_collection_required")
        for row in rows:
            evidence = row.get("evidence")
            need(type(evidence) is dict and evidence.get("path") in index and text(evidence.get("locator"))
                 and evidence.get("sha256") == index[evidence["path"]].get("sha256"), "powerbi.adapter_evidence_mismatch")
            if files is not None and evidence["path"] in files:
                need(evidence["sha256"] == files[evidence["path"]]["sha256"], "powerbi.adapter_definition_mismatch")
            if category == "expressions":
                need(type(row.get("text")) is str and row.get("content_sha256") == sha(row["text"].encode()),
                     "powerbi.adapter_expression_hash")
    if files is not None:
        need(all(path in files and record.get("sha256") == files[path]["sha256"] for path, record in index.items()),
             "powerbi.adapter_source_file_mismatch")
    return value


def validate_capture(value):
    need(type(value) is dict and value.get("schema_version") == SCHEMA and value.get("content_hash") ==
         sha({k: v for k, v in value.items() if k != "content_hash"}), "powerbi.capture_schema_or_hash")
    need(value.get("target_write_authority") is False and value.get("native_validation") == "not_performed"
         and value.get("business_acceptance") == "not_assessed", "powerbi.capture_authority")
    request, source = value.get("request"), value.get("source")
    need(type(request) is dict and value.get("request_sha256") == sha(request) and request.get("capture_id") == value.get("capture_id"),
         "powerbi.request_hash")
    need(type(source) is dict and all(text(request.get(k)) for k in ("capture_id", "principal_ref")),
         "powerbi.source_identity_required")
    service_ids = (request.get("workspace_id"), request.get("report_id"))
    need(all(text(v) for v in service_ids) or service_ids == (None, None), "powerbi.partial_service_identity")
    identity = source.get("identity")
    need(type(identity) is dict and all(identity.get(k) == request.get(k)
         for k in ("workspace_id", "report_id", "principal_ref")), "powerbi.source_identity_mismatch")
    need(request.get("route") in ROUTES and (request["route"] == "unselected" or text(request.get("route_reference"))),
         "powerbi.explicit_route_required")
    state = request.get("state")
    need(type(state) is dict and text(state.get("state_id")) and type(state.get("filters")) is list,
         "powerbi.state_required")
    files = definitions_index(source.get("definition_files"))
    need(sum(path == "report.json" or path.endswith("definition/report.json") for path in files) == 1,
         "powerbi.exactly_one_report_required")
    need(source.get("definition_fingerprint") == definition_fingerprint(source["definition_files"]), "powerbi.definition_fingerprint")
    if service_ids == (None, None):
        need(identity.get("identity_scope") == "definition_only" and identity.get("namespace") ==
             "definition:" + source["definition_fingerprint"], "powerbi.definition_only_identity_required")
    elif identity.get("namespace") is not None:
        need(identity["namespace"] == "powerbi:" + request["workspace_id"] + ":" + request["report_id"],
             "powerbi.source_namespace_mismatch")
    structure = inspect_definitions(source["definition_files"])
    pages = {o["page_id"] for o in structure["objects"] if o["kind"] == "page" and
             not o["native"].get("missing_page_file")}
    visuals = {(o["page_id"], o["visual_id"]) for o in structure["objects"] if o["visual_id"] is not None}
    views = request.get("views")
    need(type(views) is list and all(type(v) is dict and text(v.get("page_id")) and
         (v.get("visual_id") is None or text(v["visual_id"])) for v in views), "powerbi.views_required")
    scope = {(v["page_id"], v.get("visual_id")) for v in views}
    need(len(scope) == len(views), "powerbi.duplicate_view")
    for page, visual in scope:
        need(page in pages and (visual is None or (page, visual) in visuals), "powerbi.view_definition_mismatch")
    queries = request.get("queries")
    need(type(queries) is list and all(type(q) is dict and text(q.get("query_id")) and text(q.get("query"))
         and (q.get("page_id"), q.get("visual_id")) in scope for q in queries), "powerbi.query_definition_mismatch")
    query_index = {q["query_id"]: q for q in queries}
    need(len(query_index) == len(queries), "powerbi.duplicate_query")
    manifest = request.get("expected_manifest")
    need(type(manifest) is dict and text(manifest.get("reference")) and manifest.get("completeness") in
         ("selected_report", "partial") and type(manifest.get("objects")) is list, "powerbi.expected_manifest_required")
    need(all(type(o) is dict and text(o.get("object_id")) and text(o.get("kind")) for o in manifest["objects"])
         and len({o["object_id"] for o in manifest["objects"]}) == len(manifest["objects"]), "powerbi.expected_manifest_ambiguous")
    attachments = value.get("attachments")
    need(type(attachments) is list, "powerbi.attachments_required")
    seen = set()
    boundary = common()
    for attachment in attachments:
        boundary.file_pin(attachment)
        key = unicodedata.normalize("NFC", attachment["path"]).casefold()
        need(key not in seen, "powerbi.attachment_collision")
        seen.add(key)
        if attachment.get("page_id") is not None:
            need((attachment["page_id"], attachment.get("visual_id")) in scope or
                 (attachment["page_id"], attachment.get("visual_id")) in {
                 (q.get("page_id"), q.get("visual_id")) for q in queries}, "powerbi.attachment_view_mismatch")
            need(attachment.get("state_sha256") == sha(state) and attachment.get("request_sha256") == value["request_sha256"],
                 "powerbi.attachment_state_mismatch")
        if attachment.get("query_id") is not None:
            query = query_index.get(attachment["query_id"])
            need(query is not None and all(attachment.get(k) == query.get(k) for k in ("page_id", "visual_id")),
                 "powerbi.attachment_query_mismatch")
            if attachment.get("query_sha256") is not None:
                need(attachment["query_sha256"] == sha({"queries": [{"query": query["query"]}],
                     "serializerSettings": {"includeNulls": True}}), "powerbi.attachment_query_hash_mismatch")
            if attachment.get("dataset_id") is not None:
                need(attachment["dataset_id"] == request.get("dataset_id"), "powerbi.attachment_dataset_mismatch")
    need(value.get("status") in ("complete", "partial", "blocked") and type(value.get("gaps")) is list,
         "powerbi.capture_status")
    captures = value.get("captures")
    need(type(captures) is list and all(type(c) is dict for c in captures), "powerbi.captures_required")
    pairs = {(c.get("page_id"), c.get("visual_id")) for c in captures}
    need(len(pairs) == len(captures) and pairs <= scope, "powerbi.capture_scope_mismatch")
    for capture in captures:
        need(capture.get("state_sha256") == sha(state) and capture.get("status") in ("complete", "partial", "blocked"),
             "powerbi.capture_state_mismatch")
        for path in capture.get("attachments", []):
            matched = [a for a in attachments if a["path"] == path]
            need(len(matched) == 1 and (matched[0].get("page_id"), matched[0].get("visual_id")) ==
                 (capture["page_id"], capture.get("visual_id")), "powerbi.capture_attachment_mismatch")
    if value["status"] == "complete":
        need(pairs == scope and all(c["status"] == "complete" for c in captures), "powerbi.false_capture_completion")
        if source.get("definition_after_fingerprint") is not None:
            need(source["definition_after_fingerprint"] == source["definition_fingerprint"], "powerbi.complete_definition_drift")
    if source.get("semantic_inventory") is not None:
        semantic = source["semantic_inventory"]
        need(type(semantic) is dict and semantic.get("kind") == "powerbi_source_inventory" and semantic.get("schema_version") == 1
             and source.get("semantic_inventory_sha256") == sha(semantic), "powerbi.legacy_semantic_contract")
        need(all(a.get("path") in files and a.get("sha256") == files[a["path"]]["sha256"] for a in semantic.get("assets", [])),
             "powerbi.legacy_semantic_definition_mismatch")
    if source.get("adapter_result") is not None:
        need(source.get("adapter_result_sha256") == sha(source["adapter_result"]), "powerbi.adapter_hash")
        adapter_result(source["adapter_result"], files)
    return value


def verify_capture_files(value, root):
    validate_capture(value)
    boundary = common()
    files = list(value["attachments"]) + value["source"]["definition_files"]
    files += [op["response"] for op in value.get("operations", []) if op.get("response") is not None]
    verified = {}
    for record in files:
        boundary.file_pin(record)
        raw = boundary.read_confined(root, record["path"])
        need(len(raw) == record["bytes"] and sha(raw) == record["sha256"], "powerbi.actual_file_mismatch")
        if record.get("format") == "png":
            boundary.capture_files_module().png_info(raw)
        verified[record["path"]] = record["sha256"]
    return {"status": "verified_local_bytes", "files": verified, "native_validation": "not_performed"}


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    result = helpers["base"](payload, raw, "powerbi", "supplied_powerbi_visual_capture")
    source, request = payload["source"], payload["request"]
    structure = inspect_definitions(source["definition_files"])
    known = {o["object_id"]: o for o in structure["objects"]}
    expected = {o["object_id"]: o for o in request["expected_manifest"]["objects"]}
    result["source"].update(definition_fingerprint=structure["definition_fingerprint"], capture_content_hash=payload["content_hash"])
    result["migration_context"] = {"route": None if request["route"] == "unselected" else request["route"],
                                   "route_reference": request.get("route_reference")}
    namespace = ("powerbi:" + request["workspace_id"] + ":" + request["report_id"]
                 if request["report_id"] else "definition:" + source["definition_fingerprint"])
    identities = [(o["kind"], o["page_id"], o["native_id"]) for o in structure["objects"]]
    for obj in structure["objects"]:
        native = obj["native"] if type(obj["native"]) is dict else {"value": obj["native"]}
        visual = native.get("visual", {})
        visual = visual if type(visual) is dict else {}
        facets = {"layout": helpers["facet"](native, ("position", "parentGroupName", "isHidden", "visualGroup", "visibility", "height", "width", "displayOption")),
                  "visual": helpers["facet"](native, ("visual", "objects", "themeCollection", "resourcePackages")),
                  "content": helpers["facet"](native, ("name", "displayName", "annotations")),
                  "query": helpers["facet"](visual, ("query",), "declared"),
                  "filters": helpers["facet"](native, ("filterConfig", "syncGroup")),
                  "interactions": helpers["facet"](native, ("visualInteractions", "pageBinding", "objects", "visual"), "needs_review"),
                  "security": {"status": "needs_review", "value": None}}
        native_unique = obj["native_id"] is not None and identities.count((obj["kind"], obj["page_id"], obj["native_id"])) == 1
        helpers["add_asset"](result, obj["kind"], obj, obj["object_id"], obj["native_id"] if native_unique else obj["object_id"],
            namespace + "/" + str(obj["page_id"]), facets,
            "native_id" if native_unique else "file_scoped_locator",
            {"workspace_id": request["workspace_id"], "report_id": request["report_id"], "page_id": obj["page_id"],
             "visual_id": obj["visual_id"], "definition_fingerprint": structure["definition_fingerprint"],
             "native_id": obj["native_id"], "dataset_id": request.get("dataset_id"),
             "source_file": obj["source_path"], "query_visual": obj.get("query_visual", False),
             "source_platform": "powerbi", "namespace": namespace})
    for oid in sorted(set(expected) - set(known)):
        helpers["add_asset"](result, "unknown", {**expected[oid], "missing_from_definition": True}, "/expected_missing/" + oid,
                             oid, namespace, id_kind="expected_unobserved_locator")
        helpers["gap"](result, "powerbi.expected_object_missing", oid)
    for oid in sorted(set(known) - set(expected)):
        helpers["gap"](result, "powerbi.object_outside_expected_manifest", oid)
    for oid in set(known) & set(expected):
        if known[oid]["kind"] != expected[oid]["kind"]:
            helpers["gap"](result, "powerbi.expected_kind_mismatch", oid)
    result["dependencies"] = structure["dependencies"]
    for gap in structure["gaps"]:
        helpers["gap"](result, gap["code"], gap["source_path"] + "#" + gap["locator"])
    for gap in payload["gaps"]:
        helpers["gap"](result, "powerbi.capture_gap", detail=gap)
    for key in ("semantic_inventory", "adapter_result"):
        if source.get(key) is not None:
            for gap in source[key].get("gaps", []):
                helpers["gap"](result, "powerbi." + key + "_gap", detail=gap)
    helpers["gap"](result, "powerbi.actual_files_require_verification")
    helpers["gap"](result, "powerbi.values_do_not_establish_rendered_state")
    result["powerbi_coverage"] = {"expected_objects": len(expected), "observed_objects": len(known),
        "missing_expected": sorted(set(expected) - set(known)), "unexpected_objects": sorted(set(known) - set(expected)),
        "definition_coverage": "reconciled_supplied_manifest" if set(expected) == set(known) and all(
            expected[k]["kind"] == known[k]["kind"] for k in known) else "partial",
        "manifest_completeness": request["expected_manifest"]["completeness"], "behavior_coverage": "not_verified"}
    return result


def parse_adapter(payload, raw, helpers, revision):
    adapter_result(payload)
    result = helpers["base"](payload, raw, "powerbi", "supplied_powerbi_source_adapter_result")
    result["source"]["producer"] = {"name": "DataModelAccelerator", "revision": revision,
        "revision_evidence": "operator_declared_not_authenticated"}
    for row in payload["objects"]:
        evidence = row["evidence"]
        kind = row["kind"] if row["kind"] in ("project", "page", "visual", "filter") else "definition"
        helpers["add_asset"](result, kind, row, row.get("occurrence_id") or row["id"], row["id"], evidence["path"],
            id_kind="adapter_generated_id", source_identity={"native_id": row.get("native_id"),
                "evidence": evidence, "adapter_kind": row["kind"], "adapter_occurrence_id": row.get("occurrence_id")})
    result["dependencies"] = copy.deepcopy(payload["dependencies"])
    for gap in payload["gaps"]:
        helpers["gap"](result, "powerbi.adapter_gap", gap["evidence"]["path"], gap)
    helpers["gap"](result, "powerbi.generic_adapter_is_not_complete_visual_inventory")
    return result


def normalize_results(raw, profile, binding):
    need(type(raw) is bytes and len(raw) <= MAX_BYTES and type(profile) is dict
         and profile.get("schema_version") == 1 and profile.get("format") in ("csv", "json")
         and profile.get("subtotal_policy") == "preserve", "powerbi.normalization_profile")
    need(type(binding) is dict and binding.get("attachment_sha256") == sha(raw)
         and all(text(binding.get(k)) for k in ("capture_content_hash", "page_id", "visual_id", "state_sha256", "query_id")),
         "powerbi.normalization_binding")
    headers, columns = profile.get("headers"), profile.get("columns")
    need(type(headers) is list and headers and all(text(h) for h in headers) and type(columns) is list
         and len(columns) == len(headers) and [c.get("ordinal") for c in columns] == list(range(len(headers)))
         and all(text(c.get("name")) for c in columns) and len({c["name"] for c in columns}) == len(columns),
         "powerbi.explicit_ordinal_mapping_required")
    if len(set(headers)) != len(headers):
        need(text(profile.get("duplicate_header_resolution_reference")) and profile["format"] == "csv",
             "powerbi.duplicate_headers_unresolved")
    if profile["format"] == "csv":
        need(profile.get("encoding") == "utf-8", "powerbi.csv_encoding_required")
        try:
            data = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
        except (UnicodeError, csv.Error):
            raise ValueError("powerbi.invalid_csv") from None
        need(data and data[0] == headers, "powerbi.csv_headers_mismatch")
        rows = data[1:]
    else:
        data = decode(raw)
        # The capture remains JSON bytes. Parse decimal tokens exactly for the
        # derivative rather than round them through a binary float.
        data = json.loads(raw.decode("utf-8-sig"), parse_float=Decimal)
        path = profile.get("rows_pointer")
        need(type(path) is str and (path == "" or path.startswith("/")), "powerbi.explicit_rows_pointer_required")
        for part in path.split("/")[1:]:
            if type(data) is dict:
                need("error" not in data and "errors" not in data, "powerbi.result_error")
                part = part.replace("~1", "/").replace("~0", "~")
                need(part in data, "powerbi.result_pointer_missing")
                data = data[part]
            elif type(data) is list:
                need(part.isdecimal() and int(part) < len(data), "powerbi.result_pointer_missing")
                data = data[int(part)]
            else:
                raise ValueError("powerbi.result_pointer_missing")
        need(type(data) is list and all(type(r) is dict and set(r) == set(headers) for r in data),
             "powerbi.json_rows_or_columns_required")
        rows = [[r[h] for h in headers] for r in data]
    need(len(rows) <= 100000, "powerbi.result_row_limit")
    output = []
    for row in rows:
        need(len(row) == len(columns), "powerbi.ragged_rows")
        converted = {}
        for col, value in zip(columns, row):
            need(type(col.get("null_tokens")) is list, "powerbi.explicit_null_mapping_required")
            if value is None or (type(value) is str and value in col["null_tokens"]):
                need(col.get("nullable") is True, "powerbi.unexpected_null")
                result = None
            elif col.get("type") == "string":
                need(type(value) is str, "powerbi.string_required")
                result = value
            elif col.get("type") == "boolean":
                need(type(value) is bool, "powerbi.boolean_required")
                result = value
            elif col.get("type") == "date":
                need(type(value) is str and text(col.get("date_format")), "powerbi.explicit_date_format_required")
                result = datetime.strptime(value, col["date_format"]).isoformat()
            elif col.get("type") == "number":
                need(type(value) in (str, int, float, Decimal), "powerbi.number_required")
                current = str(value)
                currency = col.get("currency")
                if currency is not None:
                    need(type(currency) is dict and type(currency.get("code")) is str and
                         re.fullmatch(r"[A-Z]{3}", currency["code"]) and
                         type(currency.get("prefix")) is str and type(currency.get("suffix")) is str and
                         type(currency.get("negative_parentheses")) is bool, "powerbi.explicit_currency_profile_required")
                    negative = current.startswith("(") and current.endswith(")")
                    if negative:
                        need(currency["negative_parentheses"], "powerbi.currency_parentheses_not_declared")
                        current = current[1:-1]
                    prefix, suffix = currency["prefix"], currency["suffix"]
                    need(current.startswith(prefix) and current.endswith(suffix), "powerbi.currency_symbol_mismatch")
                    current = current[len(prefix):len(current) - len(suffix) if suffix else None]
                    if negative:
                        need(not current.startswith(("-", "+")), "powerbi.ambiguous_currency_sign")
                        current = "-" + current
                separator, group = col.get("decimal_separator"), col.get("group_separator")
                need(separator in (".", ",") and group in (None, ".", ",", " ") and group != separator
                     and type(col.get("percent")) is bool, "powerbi.explicit_numeric_profile_required")
                if type(value) in (int, float, Decimal) and currency is None and col["percent"] is False:
                    need(separator == "." and group is None, "powerbi.typed_number_has_no_locale_format")
                    number = Decimal(str(value))
                    need(number.is_finite(), "powerbi.nonfinite_number")
                    converted[col["name"]] = str(number)
                    continue
                pattern = r"[+-]?(?:\d{1,3}(?:" + re.escape(group) + r"\d{3})+|\d+)" if group else r"[+-]?\d+"
                pattern += "(?:" + re.escape(separator) + r"\d+)?" + ("%" if col["percent"] else "")
                need(re.fullmatch(pattern, current) is not None, "powerbi.invalid_formatted_number")
                if col["percent"]:
                    current = current[:-1]
                if group:
                    current = current.replace(group, "")
                try:
                    number = Decimal(current.replace(separator, "."))
                    if col["percent"]:
                        parts = number.as_tuple()
                        number = Decimal((parts.sign, parts.digits, parts.exponent - 2))
                    need(number.is_finite(), "powerbi.nonfinite_number")
                    result = str(number)
                except InvalidOperation:
                    raise ValueError("powerbi.invalid_number") from None
            else:
                raise ValueError("powerbi.unsupported_column_type")
            converted[col["name"]] = result
        output.append(converted)
    return {"schema_version": 1, "kind": "powerbi_normalized_results", "raw_sha256": sha(raw),
            "parser_profile": copy.deepcopy(profile), "binding": copy.deepcopy(binding), "headers": headers,
            "row_count": len(output), "rows": output, "row_order": "preserved", "completeness": "not_established"}
