"""Bounded Tableau evidence reader. Local data only; no source or target execution.

Locators are version-scoped XML identities, never Tableau REST identifiers.
Capture seals establish integrity, not producer authenticity or applied state.
"""
import copy
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
import xml.etree.ElementTree as ET

SCHEMA = "tableau-visual-capture.v1"
MAX_XML_BYTES = 2_000_000
MAX_NODES = 5000
MAX_FILE_BYTES = 32 * 1024 * 1024


def need(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and bool(value) and not any(ord(c) < 32 for c in value)


def safe_path(value):
    need(text(value), "tableau.path_required")
    p = Path(value)
    need(not p.is_absolute() and ".." not in p.parts and "\\" not in value
         and p.as_posix() == value and ":" not in value, "tableau.unsafe_path")
    return p


def file_pin(value):
    need(type(value) is dict, "tableau.file_pin_required")
    safe_path(value.get("path"))
    need(type(value.get("sha256")) is str and re.fullmatch("[a-f0-9]{64}", value["sha256"])
         and type(value.get("bytes")) is int and 0 <= value["bytes"] <= MAX_FILE_BYTES,
         "tableau.invalid_file_pin")


def capture_files_module():
    path = Path(__file__).with_name("tableau_capture_files.py")
    spec = importlib.util.spec_from_file_location("tableau_shared_file_boundary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_xml(raw):
    """Use capture's shared bounded secret/DTD boundary; accept UTF-8 only."""
    need(type(raw) is bytes and len(raw) <= MAX_XML_BYTES, "tableau.xml_size_or_encoding")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError("tableau.invalid_xml") from None
    declaration = re.search(r"<\?xml[^>]*encoding\s*=\s*['\"]([^'\"]+)", decoded, re.I)
    need(not declaration or declaration[1].lower().replace("-", "") == "utf8", "tableau.xml_encoding")
    return capture_files_module().safe_xml(raw, workbook=True)


def inspect_workbook(raw_twb, source_path="workbook.twb"):
    """Return native visual objects with exact, definition-scoped locators.

    A source-declared zone worksheet name is resolved only when unique within
    the XML. No REST view identity is inferred from that name or a caption.
    """
    root = safe_xml(raw_twb)
    objects, gaps, nodes = [], [], {}
    stack = [(root, "/workbook[1]", None, None, None, None)]
    while stack:
        node, locator, parent, dashboard, device, sheet = stack.pop()
        nodes[locator] = node
        tag, kind = node.tag, None
        if tag == "workbook":
            kind = "workbook"
        elif tag == "worksheet" and re.fullmatch(r"/workbook\[1\]/worksheets\[\d+\]/worksheet\[\d+\]", locator):
            kind, sheet = "worksheet", locator
        elif tag == "dashboard" and re.fullmatch(r"/workbook\[1\]/dashboards\[\d+\]/dashboard\[\d+\]", locator):
            kind, dashboard = "dashboard", locator
        elif tag in ("devicelayout", "device-layout"):
            kind, device = "device_layout", locator
        elif tag == "zone":
            zone_type = node.get("type-v2", node.get("type", ""))
            if zone_type == "viz":
                kind = "placement"
            elif zone_type in ("filter", "paramctrl", "parameter", "filter-control"):
                kind = "control"
            elif zone_type in ("text", "title", "image", "web", "blank", "legend", "color", "size", "shape"):
                kind = "content"
            elif zone_type in ("layout-basic", "layout-flow", "layout-container"):
                kind = "layout"
            else:
                kind = "unknown"
                gaps.append({"code": "tableau.unknown_zone_type", "object_id": locator})
        elif tag == "action":
            kind = "action"
        elif tag == "column" and "param-domain-type" in node.attrib:
            kind = "parameter"
        elif tag in ("filter", "groupfilter"):
            kind = "filter"
        elif tag == "story":
            kind = "unknown"
            gaps.append({"code": "tableau.story_requires_review", "object_id": locator})
        if kind:
            simple = node.find("simple-id")
            repository = node.find("repository-location")
            native = (simple.get("uuid") if simple is not None else None) or node.get("id")
            if kind == "workbook" and repository is not None:
                native = repository.get("id")
            objects.append({"object_id": locator, "kind": kind, "parent_id": parent,
                "dashboard_id": dashboard, "device_id": device, "worksheet_id": sheet,
                "native_id": native, "name": node.get("name"), "attributes": dict(node.attrib),
                "tag": tag, "text": node.text,
                "raw_xml": ET.tostring(node, encoding="unicode") if kind in
                ("worksheet", "parameter", "filter", "action", "content", "unknown") else None})
            parent = locator
        counts = {}
        children = []
        for child in node:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            children.append((child, locator + "/" + child.tag + "[" + str(counts[child.tag]) + "]",
                             parent, dashboard, device, sheet))
        stack.extend(reversed(children))
    worksheets = {}
    for obj in objects:
        if obj["kind"] == "worksheet":
            worksheets.setdefault(obj["name"], []).append(obj["object_id"])
    for obj in objects:
        if obj["kind"] == "placement":
            matches = worksheets.get(obj["name"], [])
            obj["worksheet_id"] = matches[0] if len(matches) == 1 else None
            if len(matches) != 1:
                gaps.append({"code": "tableau.unresolved_worksheet_reference", "object_id": obj["object_id"]})
        if obj["kind"] == "action":
            references = []
            for element in nodes[obj["object_id"]].iter():
                declared = [(key, value) for key, value in element.attrib.items() if key in ("worksheet", "dashboard")]
                if element.tag in ("worksheet", "dashboard") and element.get("name"):
                    declared.append((element.tag, element.get("name")))
                for kind, name in declared:
                    matches = [o["object_id"] for o in objects if o["kind"] == kind and o["name"] == name]
                    references.append({"kind": kind, "name": name, "element": element.tag,
                                       "object_id": matches[0] if len(matches) == 1 else None,
                                       "status": "resolved_xml_reference" if len(matches) == 1 else "unresolved"})
                    if len(matches) != 1:
                        gaps.append({"code": "tableau.action_reference_unresolved", "object_id": obj["object_id"]})
            obj["references"] = references
            gaps.append({"code": "tableau.action_behavior_unverified", "object_id": obj["object_id"]})
    return {"schema_version": 1, "kind": "tableau_visual_structure", "source_path": source_path,
            "definition_sha256": sha(raw_twb), "objects": objects, "gaps": gaps,
            "identity_scope": "definition_sha256_and_xml_locator", "native_validation": "not_performed"}


def selected_objects(structure, dashboard_id):
    objects = structure["objects"]
    if dashboard_id is None:
        return objects
    need(any(o["object_id"] == dashboard_id and o["kind"] == "dashboard" for o in objects),
         "tableau.dashboard_identity_unknown")
    sheets = {o["worksheet_id"] for o in objects if o["dashboard_id"] == dashboard_id and o["worksheet_id"]}
    for action in objects:
        if action["kind"] == "action" and action["dashboard_id"] in (dashboard_id, None):
            sheets.update(ref["object_id"] for ref in action.get("references", [])
                          if ref["kind"] == "worksheet" and ref["object_id"])
    # Workbook-level parameters/actions are retained conservatively; unknown action
    # dependency targets cannot silently vanish from a selected dashboard slice.
    return [o for o in objects if o["dashboard_id"] == dashboard_id or o["worksheet_id"] in sheets
            or (o["dashboard_id"] is None and o["kind"] in ("workbook", "parameter", "action", "unknown"))]


def validate_capture(value):
    need(type(value) is dict and value.get("schema_version") == SCHEMA, "tableau.capture_schema")
    need(value.get("content_hash") == sha({k: v for k, v in value.items() if k != "content_hash"}),
         "tableau.capture_hash")
    need(value.get("target_write_authority") is False and value.get("native_validation") == "not_performed"
         and value.get("business_acceptance") == "not_assessed", "tableau.capture_authority")
    need(value.get("status") in ("complete", "partial", "blocked") and type(value.get("gaps")) is list,
         "tableau.capture_status")
    request = value.get("request")
    need(type(request) is dict and value.get("request_sha256") == sha(request)
         and request.get("capture_id") == value.get("capture_id") and text(value.get("capture_id")),
         "tableau.request_hash")
    for key in ("site_id", "workbook_id", "dashboard_view_id", "principal_ref", "authorization_ref"):
        need(text(request.get(key)), "tableau.request_identity_required")
    state = request.get("state")
    need(type(state) is dict and text(state.get("state_id")) and all(type(state.get(k)) is dict
         for k in ("filters", "parameters")), "tableau.state_required")
    source = value.get("source")
    need(type(source) is dict, "tableau.source_required")
    definition = source.get("definition")
    file_pin(definition)
    need(type(definition.get("content_utf8")) is str, "tableau.definition_content_required")
    raw = definition["content_utf8"].encode("utf-8")
    need(sha(raw) == definition["sha256"] and len(raw) == definition["bytes"], "tableau.definition_hash")
    need(request.get("definition_sha256") in (None, definition["sha256"]), "tableau.request_definition_mismatch")
    structure = inspect_workbook(raw, definition["path"])
    objects = selected_objects(structure, request.get("dashboard_id"))
    index = {o["object_id"]: o for o in objects}
    manifest = request.get("expected_manifest")
    need(type(manifest) is dict and manifest.get("schema_version") == 1 and text(manifest.get("reference"))
         and manifest.get("completeness") in ("selected_dashboard", "partial")
         and type(manifest.get("objects")) is list, "tableau.expected_manifest_required")
    expected = manifest["objects"]
    need(all(type(o) is dict and text(o.get("object_id")) and text(o.get("kind")) for o in expected)
         and len({o["object_id"] for o in expected}) == len(expected), "tableau.expected_manifest_ambiguous")
    crosswalk = request.get("identity_map")
    need(type(crosswalk) is dict and crosswalk.get("schema_version") == 1
         and type(crosswalk.get("mappings")) is list, "tableau.identity_map_required")
    mappings = crosswalk["mappings"]
    need(all(type(m) is dict and text(m.get("view_id")) and m.get("status") in ("matched", "unresolved")
             for m in mappings) and len({m["view_id"] for m in mappings}) == len(mappings),
         "tableau.identity_map_ambiguous")
    for mapping in mappings:
        if mapping["status"] == "matched":
            need(mapping.get("object_id") in index and text(mapping.get("evidence_reference")),
                 "tableau.identity_match_evidence_required")
        else:
            need(mapping.get("object_id") is None, "tableau.unresolved_identity_has_binding")
    views = request.get("views")
    need(type(views) is list and views and all(type(v) is dict and text(v.get("view_id")) and
         v.get("role") in ("dashboard", "worksheet") for v in views)
         and len({v["view_id"] for v in views}) == len(views), "tableau.views_required")
    maps = {m["view_id"]: m for m in mappings}
    for view in views:
        need(view["view_id"] in maps, "tableau.view_crosswalk_missing")
        mapping = maps[view["view_id"]]
        if mapping["status"] == "matched":
            obj = index[mapping["object_id"]]
            need(obj["kind"] == view["role"], "tableau.view_object_kind_mismatch")
            need(view.get("worksheet_id") == (obj["object_id"] if view["role"] == "worksheet" else None),
                 "tableau.view_worksheet_mismatch")
            if view["view_id"] == request["dashboard_view_id"]:
                need(obj["object_id"] == request.get("dashboard_id"), "tableau.dashboard_view_mismatch")
    attachments = value.get("attachments")
    need(type(attachments) is list, "tableau.attachments_required")
    paths = set()
    for attachment in attachments:
        file_pin(attachment)
        collision = unicodedata.normalize("NFC", attachment["path"]).casefold()
        need(collision not in paths, "tableau.attachment_collision")
        paths.add(collision)
        need(attachment.get("format") in ("png", "csv", "twb", "twbx", "json"), "tableau.attachment_format")
        if attachment["format"] in ("png", "csv"):
            need(attachment.get("view_id") in {v["view_id"] for v in views}
                 and attachment.get("request_sha256") == value["request_sha256"]
                 and attachment.get("state_sha256") == sha(state), "tableau.attachment_binding")
            view = next(v for v in views if v["view_id"] == attachment["view_id"])
            need(attachment.get("worksheet_id") == view.get("worksheet_id"), "tableau.attachment_worksheet")
    captures = value.get("captures")
    need(type(captures) is list and len({c.get("view_id") for c in captures}) == len(captures),
         "tableau.captures_required")
    for capture in captures:
        need(capture.get("view_id") in {v["view_id"] for v in views}
             and capture.get("status") in ("complete", "partial", "blocked")
             and capture.get("state_sha256") == sha(state), "tableau.capture_binding")
        selected = next(v for v in views if v["view_id"] == capture["view_id"])
        need(capture.get("role") == selected["role"] and capture.get("worksheet_id") == selected.get("worksheet_id"),
             "tableau.capture_view_mismatch")
        for path in capture.get("attachments", []):
            found = [a for a in attachments if a["path"] == path]
            need(len(found) == 1 and found[0].get("view_id") == capture["view_id"], "tableau.capture_attachment_missing")
    if value["status"] == "complete":
        need({c["view_id"] for c in captures} == {v["view_id"] for v in views}
             and all(c["status"] == "complete" for c in captures), "tableau.false_complete_capture")
        for view in views:
            formats = {a["format"] for a in attachments if a.get("view_id") == view["view_id"]}
            need({"png", "csv"} <= formats if view["role"] == "worksheet" else "png" in formats,
                 "tableau.false_complete_attachments")
    if source.get("semantic_inventory") is not None:
        semantic = source["semantic_inventory"]
        need(type(semantic) is dict and semantic.get("kind") == "tableau_source_inventory"
             and semantic.get("schema_version") == 1 and source.get("semantic_inventory_sha256") == sha(semantic),
             "tableau.semantic_inventory_hash")
        need(any(a.get("sha256") == definition["sha256"] for a in semantic.get("assets", [])),
             "tableau.semantic_definition_mismatch")
    return value


def read_confined(root, relative):
    path = safe_path(relative)
    base = Path(root).absolute()
    need(base.is_dir(), "tableau.capture_directory_required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in base.parts[1:] + path.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        with os.fdopen(os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd), "rb") as stream:
            before = os.fstat(stream.fileno())
            need(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE_BYTES, "tableau.invalid_attachment_file")
            raw = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(stream.fileno())
            need(len(raw) == before.st_size and before.st_mtime_ns == after.st_mtime_ns,
                 "tableau.attachment_changed_during_read")
        return raw
    finally:
        os.close(fd)


def verify_capture_files(value, root):
    validate_capture(value)
    files = list(value["attachments"]) + [value["source"]["definition"]]
    if value["source"].get("original_definition") is not None:
        files.append(value["source"]["original_definition"])
    for operation in value.get("operations", []):
        if operation.get("response") is not None:
            files.append(operation["response"])
    verified = {}
    boundary = capture_files_module()
    for record in files:
        file_pin(record)
        raw = read_confined(root, record["path"])
        need(sha(raw) == record["sha256"] and len(raw) == record["bytes"], "tableau.attachment_bytes_mismatch")
        if record.get("format") == "png":
            boundary.png_info(raw)
        elif record.get("format") == "csv":
            boundary.csv_info(raw)
        elif record.get("format") == "twbx" or record is value["source"].get("original_definition"):
            parsed = boundary.definition(raw)
            need(sha(parsed["xml"]) == value["source"]["definition"]["sha256"],
                 "tableau.package_definition_mismatch")
        verified[record["path"]] = record["sha256"]
    return {"status": "verified_local_bytes", "files": verified, "native_validation": "not_performed"}


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    result = helpers["base"](payload, raw, "tableau", "supplied_tableau_visual_capture")
    request, source = payload["request"], payload["source"]
    structure = inspect_workbook(source["definition"]["content_utf8"].encode("utf-8"), source["definition"]["path"])
    objects = selected_objects(structure, request.get("dashboard_id"))
    known = {o["object_id"]: o for o in objects}
    expected = {o["object_id"]: o for o in request["expected_manifest"]["objects"]}
    result["source"].update(definition_sha256=structure["definition_sha256"], capture_status=payload["status"],
                            capture_content_hash=payload["content_hash"])
    for obj in objects:
        matched = [m["view_id"] for m in request["identity_map"]["mappings"]
                   if m["status"] == "matched" and m["object_id"] == obj["object_id"]]
        facets = {"layout": helpers["facet"](obj, ("attributes", "parent_id", "device_id")),
                  "content": helpers["facet"](obj, ("name", "text")),
                  "query": {"status": "needs_review", "value": {"worksheet_id": obj["worksheet_id"]}},
                  "visual": helpers["facet"](obj, ("raw_xml", "attributes")),
                  "filters": {"status": "needs_review", "value": obj["raw_xml"] if obj["kind"] in ("control", "parameter", "filter") else None},
                  "interactions": {"status": "needs_review", "value": obj["raw_xml"] if obj["kind"] == "action" else None},
                  "security": {"status": "needs_review", "value": None}}
        helpers["add_asset"](result, obj["kind"], obj, obj["object_id"], obj["object_id"],
            structure["definition_sha256"], facets, "version_scoped_xml_locator",
            {"definition_sha256": structure["definition_sha256"], "site_id": request["site_id"],
             "workbook_id": request["workbook_id"], "dashboard_id": obj["dashboard_id"],
             "worksheet_id": obj["worksheet_id"], "parent_id": obj["parent_id"],
             "device_id": obj["device_id"], "native_id": obj["native_id"], "view_ids": matched})
        if obj["parent_id"] in known:
            result["dependencies"].append({"from": obj["object_id"], "to": obj["parent_id"], "kind": "xml_parent"})
        if obj["kind"] == "placement" and obj["worksheet_id"]:
            result["dependencies"].append({"from": obj["object_id"], "to": obj["worksheet_id"], "kind": "worksheet_definition"})
        for ref in obj.get("references", []):
            if ref["object_id"] in known:
                result["dependencies"].append({"from": obj["object_id"], "to": ref["object_id"], "kind": "declared_action_reference"})
    for object_id in sorted(set(expected) - set(known)):
        obj = {**expected[object_id], "name": None, "missing_from_definition": True}
        helpers["add_asset"](result, "unknown", obj, "/expected_missing" + object_id,
                             object_id, structure["definition_sha256"], id_kind="expected_unobserved_locator")
        helpers["gap"](result, "tableau.expected_object_missing", object_id)
    for object_id in sorted(set(known) - set(expected)):
        helpers["gap"](result, "tableau.object_outside_expected_manifest", object_id)
    for object_id in set(known) & set(expected):
        if known[object_id]["kind"] != expected[object_id]["kind"]:
            helpers["gap"](result, "tableau.expected_object_kind_mismatch", object_id)
    for row in structure["gaps"]:
        helpers["gap"](result, row["code"], row["object_id"])
    for mapping in request["identity_map"]["mappings"]:
        if mapping["status"] == "unresolved":
            helpers["gap"](result, "tableau.api_xml_identity_unresolved", mapping["view_id"])
    for code in payload["gaps"]:
        helpers["gap"](result, "tableau.capture_gap", detail=code)
    if source.get("semantic_inventory") is None:
        helpers["gap"](result, "tableau.semantic_inventory_not_supplied")
    else:
        for item in source["semantic_inventory"].get("gaps", []):
            helpers["gap"](result, "tableau.semantic_gap", detail=item)
    helpers["gap"](result, "tableau.actual_attachment_bytes_not_verified_by_projection")
    helpers["gap"](result, "tableau.applied_state_and_data_atomicity_unverified")
    result["tableau_coverage"] = {"expected_objects": len(expected), "definition_objects": len(objects),
        "missing_expected": sorted(set(expected) - set(known)), "unexpected_objects": sorted(set(known) - set(expected)),
        "definition_coverage": "reconciled_supplied_manifest" if set(expected) == set(known) and all(
            known[k]["kind"] == expected[k]["kind"] for k in known) else "partial",
        "manifest_completeness": request["expected_manifest"]["completeness"],
        "file_coverage": "not_verified", "capture_coverage": payload["status"], "behavior_coverage": "not_verified"}
    return result


def normalize_results(raw, profile, binding):
    """Explicit CSV derivative. Never guesses locale, headers, nulls or totals.

    The caller preserves raw bytes and pins this deterministic artifact; workflow
    verification replays normalization before trusting the derivative's rows.
    """
    need(type(raw) is bytes and len(raw) <= MAX_FILE_BYTES, "tableau.results_size")
    need(type(profile) is dict and profile.get("schema_version") == 1 and profile.get("format") == "csv"
         and profile.get("encoding") == "utf-8" and profile.get("subtotal_policy") == "preserve",
         "tableau.explicit_parser_profile_required")
    need(type(binding) is dict and binding.get("attachment_sha256") == sha(raw)
         and all(text(binding.get(k)) for k in ("capture_content_hash", "view_id", "worksheet_id", "state_sha256")),
         "tableau.normalization_binding")
    try:
        parsed = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error):
        raise ValueError("tableau.invalid_csv") from None
    need(parsed and len(parsed) <= 100001 and parsed[0] == profile.get("headers"), "tableau.csv_headers_mismatch")
    columns = profile.get("columns")
    need(type(columns) is list and len(columns) == len(parsed[0]) and all(type(c) is dict for c in columns)
         and [c.get("ordinal") for c in columns] == list(range(len(columns)))
         and all(text(c.get("name")) for c in columns)
         and len({c["name"] for c in columns}) == len(columns), "tableau.explicit_ordinal_mapping_required")
    if len(set(parsed[0])) != len(parsed[0]):
        need(text(profile.get("duplicate_header_resolution_reference")), "tableau.duplicate_headers_unresolved")
    output = []
    for row in parsed[1:]:
        need(len(row) == len(columns), "tableau.ragged_csv")
        item = {}
        for col, value in zip(columns, row):
            need(type(col.get("null_tokens")) is list and all(type(x) is str for x in col["null_tokens"]),
                 "tableau.explicit_null_tokens_required")
            if value in col["null_tokens"]:
                need(col.get("nullable") is True, "tableau.unexpected_null")
                converted = None
            elif col.get("type") == "string":
                converted = value
            elif col.get("type") == "date":
                need(text(col.get("date_format")), "tableau.explicit_date_format_required")
                try:
                    converted = datetime.strptime(value, col["date_format"]).isoformat()
                except ValueError:
                    raise ValueError("tableau.invalid_formatted_date") from None
            elif col.get("type") == "number":
                separator, grouping = col.get("decimal_separator"), col.get("group_separator")
                need(separator in (".", ",") and grouping in (None, ".", ",", " ") and grouping != separator
                     and type(col.get("percent")) is bool, "tableau.explicit_numeric_format_required")
                pattern = r"[+-]?(?:\d{1,3}(?:" + re.escape(grouping) + r"\d{3})+|\d+)" if grouping else r"[+-]?\d+"
                pattern += "(?:" + re.escape(separator) + r"\d+)?" + ("%" if col["percent"] else "")
                need(re.fullmatch(pattern, value) is not None, "tableau.invalid_formatted_number")
                normalized = value[:-1] if col["percent"] else value
                if grouping:
                    normalized = normalized.replace(grouping, "")
                try:
                    number = Decimal(normalized.replace(separator, "."))
                    if col["percent"]:
                        parts = number.as_tuple()
                        number = Decimal((parts.sign, parts.digits, parts.exponent - 2))
                    need(number.is_finite(), "tableau.nonfinite_number")
                    converted = str(number)
                except InvalidOperation:
                    raise ValueError("tableau.invalid_formatted_number") from None
            else:
                raise ValueError("tableau.unsupported_column_type")
            item[col["name"]] = converted
        output.append(item)
    return {"schema_version": 1, "kind": "tableau_normalized_results", "raw_sha256": sha(raw),
            "parser_profile": copy.deepcopy(profile), "binding": copy.deepcopy(binding),
            "headers": parsed[0], "row_count": len(output), "rows": output,
            "row_order": "preserved", "completeness": "not_established", "native_validation": "not_performed"}
