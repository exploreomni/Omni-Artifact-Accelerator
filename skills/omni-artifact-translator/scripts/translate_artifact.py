#!/usr/bin/env python3
"""Offline analyst evidence projection. Never executes source or calls a service.

Exit 0: bounded projection written; evidence gaps still require review.
Exit 1: rejected input/output. Only counts and error codes go to the console.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "1.1.0"
DMA_REVISION = "c513474e87af9c2c31deebd2ae675c8602955203"
MAX_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 150000
MAX_ASSETS = 5000
FACETS = ("visual", "query", "layout", "filters", "interactions", "security", "content")
KINDS = {"dashboard", "page", "visual", "filter", "layout", "app", "project", "cell",
         "workbook", "worksheet", "query", "definition", "parameter", "placement",
         "device_layout", "control", "action", "content", "unknown"}
STATUSES = {"observed", "declared", "unobserved", "unsupported", "needs_review"}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def bounded(value):
    stack, nodes = [(value, 0, frozenset())], 0
    while stack:
        item, depth, parents = stack.pop()
        nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH, "input.structure_limit")
        if type(item) in (dict, list):
            require(id(item) not in parents, "input.cyclic_value")
            require(len(item) <= MAX_NODES, "input.structure_limit")
            if type(item) is dict:
                require(all(type(key) is str for key in item), "input.invalid_key")
                values = [part for pair in item.items() for part in pair]
            else:
                values = item
            stack.extend((child, depth + 1, parents | {id(item)}) for child in values)
        elif type(item) is float:
            require(math.isfinite(item), "input.nonfinite_number")
        else:
            require(item is None or type(item) in (str, int, bool), "input.non_json_value")
    require(len(encoded(value)) <= MAX_BYTES, "input.byte_limit")


def decode(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, "input.byte_limit")

    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "input.duplicate_key")
            result[key] = value
        return result

    def reject_constant(_):
        raise ValueError("input.nonfinite_number")

    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                           parse_constant=reject_constant)
        bounded(value)
    except (UnicodeError, RecursionError, OverflowError, TypeError):
        raise ValueError("input.invalid_json") from None
    require(type(value) is dict, "input.object_required")
    return value


def identity(value):
    if type(value) is int and value >= 0:
        return str(value)
    if type(value) is str and value and len(value) <= 2048 and not any(ord(c) < 32 for c in value):
        return value
    return None


def rows(value, code):
    require(type(value) is list and len(value) <= MAX_ASSETS
            and all(type(row) is dict for row in value), code)
    return value


def facet(row, keys, status="observed"):
    values = {key: row[key] for key in keys if key in row}
    return {"status": status if values else "unobserved", "value": values,
            "interpretation": "preserved_only"}


def base(payload, raw, platform, source_format):
    return {"schema_version": 1, "kind": "omni_analyst_source_inventory",
            "source": {"platform": platform, "format": source_format,
                       "input_sha256": hashlib.sha256(raw).hexdigest(),
                       "payload_sha256": digest(payload), "projection_version": VERSION,
                       "acquisition": "supplied_local_artifact"},
            "assets": [], "dependencies": [], "gaps": [],
            "evidence_level": "static_supplied_evidence",
            "export_completeness": "not_established", "native_validation": "not_run",
            "source_execution": False, "network_calls": 0,
            "upstream_payload": copy.deepcopy(payload)}


def gap(result, code, path="", detail=None):
    item = {"code": code, "source_path": path, "status": "needs_review"}
    if detail is not None:
        item["detail"] = detail
    if item not in result["gaps"]:
        result["gaps"].append(item)


def add_asset(result, kind, row, path, source_id=None, scope=None, facets=None,
              id_kind="native_id", source_identity=None):
    require(len(result["assets"]) < MAX_ASSETS, "input.asset_limit")
    normalized_id = identity(source_id)
    if source_id is not None:
        require(normalized_id is not None, "input.invalid_source_id")
    key = "asset:" + digest([result["source"]["platform"], kind, path])[:24]
    record = {"asset_key": key, "kind": kind, "source_id": normalized_id,
              "source_identity": {"raw_id": source_id, "id_kind": id_kind,
                                  "scope": scope, **(source_identity or {})},
              "title": next((row[k] for k in ("title", "name", "label")
                             if type(row.get(k)) is str), None),
              "source_path": path, "source_payload_sha256": digest(row),
              "source_payload": copy.deepcopy(row), "facets": facets or {}}
    for name in FACETS:
        record["facets"].setdefault(name, {"status": "unobserved", "value": None})
        record["facets"][name]["interpretation"] = "preserved_only"
    if normalized_id is None:
        gap(result, "identity.native_id_unavailable", path)
    for prior in result["assets"]:
        require(prior["asset_key"] != key, "input.duplicate_locator")
        if normalized_id is not None and prior["kind"] == kind:
            require((prior["source_id"], prior["source_identity"]["scope"]) !=
                    (normalized_id, scope), "input.duplicate_identity")
    result["assets"].append(record)
    return record


def looker_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("analyst_looker_visual", Path(__file__).with_name("looker_visual.py"))
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    return bridge


def parse_looker(payload, raw, external_references=None):
    wrapped = payload.get("kind") == "looker_dashboard_export"
    if wrapped:
        require(type(payload.get("schema_version")) is int and payload["schema_version"] == 1,
                "looker.unsupported_wrapper")
        require(type(payload.get("api_version")) is str and
                re.fullmatch(r"4\.0(?:\.\d+)*", payload["api_version"]), "looker.unsupported_api_version")
        dashboard, prefix = payload.get("dashboard"), "/dashboard"
    else:
        require("kind" not in payload, "looker.unrecognized_envelope")
        dashboard, prefix = payload, ""
    require(type(dashboard) is dict and identity(dashboard.get("id")) is not None,
            "looker.dashboard_identity_required")
    elements = rows(dashboard.get("dashboard_elements"), "looker.elements_required")
    result = base(payload, raw, "looker", "looker_api_dashboard")
    result["source"]["api_version"] = payload.get("api_version") if wrapped else "4.0_declared_by_format_selection"
    did = identity(dashboard["id"])
    add_asset(result, "dashboard", dashboard, prefix, dashboard["id"], facets={
        "visual": facet(dashboard, ("background_color", "show_title", "title_color")),
        "layout": facet(dashboard, ("dashboard_layouts",)),
        "filters": facet(dashboard, ("dashboard_filters", "load_configuration")),
        "query": facet(dashboard, ("query_timezone", "model", "refresh_interval")),
        "interactions": facet(dashboard, ("crossfilter_enabled", "dashboard_filters", "load_configuration")),
        "security": facet(dashboard, ("can", "folder", "user_id", "content_metadata_id"), "declared"),
        "content": facet(dashboard, ("title", "description")),
    })
    registries = {"query": {}, "look": {}}

    def register(kind, obj, path):
        require(type(obj) is dict, "looker.invalid_reference_object")
        native_id = identity(obj.get("id"))
        if native_id is None:
            gap(result, "identity.reference_id_unavailable", path)
            return
        if native_id in registries[kind]:
            require(digest(registries[kind][native_id][0]) == digest(obj),
                    "looker.conflicting_reference_definition")
        else:
            registries[kind][native_id] = (obj, path)
        if kind == "look" and obj.get("query") is not None:
            if type(obj["query"]) is dict and obj.get("query_id") is not None and obj["query"].get("id") is not None:
                require(identity(obj["query_id"]) == identity(obj["query"]["id"]),
                        "looker.reference_identity_conflict")
            register("query", obj["query"], path + "/query")

    if wrapped:
        for plural, kind in (("queries", "query"), ("looks", "look")):
            for index, item in enumerate(rows(payload.get(plural, []), "looker.invalid_reference_collection")):
                register(kind, item, "/" + plural + "/" + str(index))
    for index, dependency in enumerate(external_references or []):
        if dependency["kind"] in registries:
            register(dependency["kind"], dependency["payload"], "/source/dependencies/" + str(index) + "/payload")
    owners = []
    for index, element in enumerate(elements):
        ep = prefix + "/dashboard_elements/" + str(index)
        local_owners = [(element, ep)]
        if element.get("result_maker") is not None:
            require(type(element["result_maker"]) is dict, "looker.invalid_result_maker")
            local_owners.append((element["result_maker"], ep + "/result_maker"))
        owners.extend(local_owners)
        for owner, path in local_owners:
            for kind in ("look", "query"):
                if owner.get(kind) is not None:
                    if type(owner[kind]) is dict and owner.get(kind + "_id") is not None and owner[kind].get("id") is not None:
                        require(identity(owner[kind + "_id"]) == identity(owner[kind]["id"]),
                                "looker.reference_identity_conflict")
                    register(kind, owner[kind], path + "/" + kind)
        embedded_query = (element.get("result_maker") or {}).get("query")
        if type(embedded_query) is dict and element.get("query_id") is not None and embedded_query.get("id") is not None:
            require(identity(element["query_id"]) == identity(embedded_query["id"]),
                    "looker.reference_identity_conflict")
    owners.extend(registries["look"].values())
    for owner, path in owners:
        for field, kind in (("query_id", "query"), ("look_id", "look"),
                            ("merge_result_id", "merge_result"), ("sql_query_id", "sql_query")):
            if owner.get(field) is not None:
                ref = identity(owner[field])
                require(ref is not None, "looker.invalid_reference_id")
                embedded = kind in registries and ref in registries[kind]
                result["dependencies"].append({"kind": kind, "source_id": ref,
                    "source_path": path + "/" + field,
                    "status": "embedded_evidence" if embedded else "unresolved"})
                if not embedded:
                    gap(result, "dependency." + kind + "_unresolved", path + "/" + field)
    for index, element in enumerate(elements):
        path = prefix + "/dashboard_elements/" + str(index)
        if element.get("dashboard_id") is not None:
            require(identity(element["dashboard_id"]) == did, "looker.dashboard_id_conflict")
        add_asset(result, looker_module().element_kind(element), element, path, element.get("id"), did, {
            "visual": facet(element, ("type", "vis_config", "result_maker", "query", "look")),
            "query": facet(element, ("query", "query_id", "look", "look_id", "result_maker", "merge_result_id", "sql_query_id")),
            "layout": facet(element, ("dashboard_layout_id", "group_id")),
            "filters": facet(element, ("listen", "result_maker", "query", "look")),
            "interactions": facet(element, ("listen", "result_maker", "query", "look")),
            "security": facet(element, ("can",), "declared"),
            "content": facet(element, ("title", "title_text", "subtitle_text", "body_text", "body_text_as_html", "note_text", "note_text_as_html")),
        })
    for collection, kind in (("dashboard_filters", "control"), ("dashboard_layouts", "layout")):
        if dashboard.get(collection) is None:
            gap(result, "source.collection_not_supplied", prefix + "/" + collection)
            continue
        for index, row in enumerate(rows(dashboard[collection], "looker.invalid_collection")):
            path = prefix + "/" + collection + "/" + str(index)
            if row.get("dashboard_id") is not None:
                require(identity(row["dashboard_id"]) == did, "looker.dashboard_id_conflict")
            add_asset(result, kind, row, path, row.get("id"), did,
                      {"filters" if kind == "control" else "layout": {"status": "observed", "value": row}})
            if kind == "layout":
                if row.get("dashboard_layout_components") is None:
                    gap(result, "layout.components_not_supplied", path)
                else:
                    for component in rows(row["dashboard_layout_components"], "looker.invalid_layout_components"):
                        ref = identity(component.get("dashboard_element_id"))
                        if ref is None or ref not in {identity(e.get("id")) for e in elements}:
                            gap(result, "layout.element_unresolved", path, {"component": component})
    for kind, registry in registries.items():
        for native_id, (row, path) in registry.items():
            add_asset(result, "definition", row, path,
                      row["id"], did + "/" + kind, {"query": {"status": "observed", "value": row}},
                      source_identity={"reference_kind": kind})
    for asset in result["assets"]:
        if asset["kind"] not in ("dashboard", "visual"):
            continue
        accounted = {"id", "dashboard_id", "dashboard_elements", "dashboard_filters", "dashboard_layouts"}
        for value in asset["facets"].values():
            if type(value.get("value")) is dict:
                accounted.update(value["value"])
        unknown = sorted(set(asset["source_payload"]) - accounted)
        asset["unmapped_fields"] = unknown
        if unknown:
            gap(result, "looker.unmapped_fields_preserved", asset["source_path"], {"fields": unknown})
    gap(result, "looker.behavior_not_translated", prefix,
        "Filters, dynamic fields, merged results, drill behavior, custom visuals, HTML and responsive layouts require explicit mapping and native parity evidence.")
    return looker_module().enrich_api(result, payload, {"add_asset": add_asset, "gap": gap, "facet": facet})


def parse_normalized(payload, raw):
    require(type(payload.get("schema_version")) is int and payload["schema_version"] == 1
            and payload.get("kind") == "omni_analyst_inventory_input", "inventory.unsupported_contract")
    platform = payload.get("platform")
    require(type(platform) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", platform),
            "inventory.invalid_platform")
    result = base(payload, raw, platform, "declared_normalized_inventory")
    for index, row in enumerate(rows(payload.get("assets"), "inventory.assets_required")):
        require(row.get("kind") in KINDS, "inventory.invalid_asset_kind")
        require("source_id" in row, "inventory.source_id_required")
        require(type(row.get("evidence_refs")) is list and row["evidence_refs"]
                and all(type(ref) is str and ref for ref in row["evidence_refs"]), "inventory.evidence_refs_required")
        facets = row.get("facets")
        require(type(facets) is dict and all(name in FACETS for name in facets), "inventory.invalid_facets")
        for value in facets.values():
            require(type(value) is dict and value.get("status") in STATUSES,
                    "inventory.invalid_facet_status")
            require("value" in value, "inventory.facet_value_required")
        require(row.get("scope") is None or type(row["scope"]) is str, "inventory.invalid_scope")
        path = "/assets/" + str(index)
        add_asset(result, row["kind"], row, path, row["source_id"], row.get("scope"),
                  copy.deepcopy(facets), id_kind="supplier_declared_id")
        for name in FACETS:
            if name not in facets or facets[name]["status"] in ("unobserved", "unsupported", "needs_review"):
                gap(result, "facet." + name + "_requires_review", path)
    gap(result, "inventory.supplier_evidence_not_authenticated")
    return result


DMA_COLLECTIONS = {
    "tableau_source_inventory": ("tableau", {"workbooks": "workbook", "dashboards": "dashboard",
        "worksheets": "worksheet", "parameters": "parameter"}),
    "powerbi_source_inventory": ("powerbi", {"projects": "project", "pages": "page", "visuals": "visual", "filters": "filter"}),
    "hex_source_inventory": ("hex", {"projects": "project", "cells": "cell"}),
}


def parse_dma(payload, raw, revision):
    require(revision == DMA_REVISION, "dma.unsupported_or_missing_producer_revision")
    require(type(payload.get("schema_version")) is int and payload["schema_version"] == 1
            and payload.get("kind") in DMA_COLLECTIONS, "dma.unsupported_inventory")
    platform, collections = DMA_COLLECTIONS[payload["kind"]]
    result = base(payload, raw, platform, "supplied_dma_inventory")
    result["source"]["producer"] = {"name": "DataModelAccelerator", "revision": revision,
        "revision_evidence": "operator_declared_not_authenticated"}
    for item in rows(payload.get("assets"), "dma.file_inventory_required"):
        require(type(item.get("path")) is str and item["path"]
                and type(item.get("sha256")) is str and re.fullmatch(r"[a-f0-9]{64}", item["sha256"]),
                "dma.invalid_file_evidence")
    result["source"]["upstream_files"] = copy.deepcopy(payload["assets"])
    result["upstream_gaps"] = copy.deepcopy(rows(payload.get("gaps"), "dma.gaps_required"))
    for index, item in enumerate(result["upstream_gaps"]):
        gap(result, "dma.upstream_gap", "/gaps/" + str(index), item)
    for collection, kind in collections.items():
        for index, row in enumerate(rows(payload.get(collection), "dma.collection_required")):
            path = "/" + collection + "/" + str(index)
            require(identity(row.get("id")) is not None, "dma.projected_identity_required")
            if platform == "tableau":
                native_id = row.get("native_id") if kind == "workbook" else row.get("name")
                id_kind = "native_id" if kind == "workbook" else "native_name"
                scope = row.get("workbook_id", row.get("path"))
            elif platform == "hex":
                native_id = row.get("project_id") if kind == "project" else row.get("cell_id")
                id_kind, scope = "native_id", row.get("project_id") if kind == "cell" else None
            else:
                require(type(row.get("native", {})) is dict, "dma.invalid_native_object")
                native_id = row.get("native", {}).get("name") if kind == "page" else row.get("id") if kind == "visual" else None
                id_kind, scope = "native_id", row.get("page", row.get("path"))
            facets = {
                "visual": facet(row, ("visual_type", "cell_type", "config", "marks", "shelves", "native")),
                "query": facet(row, ("projections", "source", "analysis", "selected_fields", "grouping", "fields", "table_calculations"), "declared"),
                "layout": facet(row, ("position", "zones", "attributes", "app_layout", "data_app_cell_ids", "native")),
                "filters": facet(row, ("filters", "shared_filters", "config", "native")),
                "interactions": {"status": "needs_review", "value": None},
                "security": {"status": "needs_review", "value": None},
                "content": facet(row, ("title", "name", "label", "meta")),
            }
            add_asset(result, kind, row, path, native_id, scope, facets, id_kind,
                      {"dma_id": row["id"], "dma_scoped_id": row.get("scoped_id"), "source_file": row.get("path"),
                       **({"query_visual": kind == "cell" and row.get("cell_type") in ("CHART", "CHARTV2", "TABLE_DISPLAY", "MAP", "METRIC", "PIVOT", "DBT_METRIC", "EXPLORE"),
                           "cell_type": row.get("cell_type"), "cell_id": row.get("cell_id"), "project_id": row.get("project_id"), "source_version_id": row.get("source_version_id")} if platform == "hex" else {})})
    gap(result, "dma.projection_is_not_source_reverification", "",
        "Only supplied inventory bytes were verified. Source file hashes and producer revision are retained declarations; re-run the pinned DMA extraction separately for source re-verification.")
    gap(result, "dma.analyst_behavior_requires_review", "",
        "Layout, chart styling, actions, filters, app interactions and security are not qualified by an engineering inventory. Omitted native fields cannot be reconstructed.")
    return result


def translate(raw, source_format, producer_revision=None):
    payload = decode(raw)
    if source_format == "looker-api":
        result = parse_looker(payload, raw)
    elif source_format in ("looker-capture", "looker-canonical", "looker-adapter"):
        bridge = looker_module()
        helpers = {"base": base, "add_asset": add_asset, "gap": gap, "facet": facet, "parse_looker": parse_looker}
        if source_format == "looker-capture":
            result = bridge.parse_capture(payload, raw, helpers)
        else:
            require(producer_revision == DMA_REVISION, "dma.unsupported_or_missing_producer_revision")
            result = (bridge.parse_canonical if source_format == "looker-canonical" else bridge.parse_adapter)(
                payload, raw, helpers, producer_revision)
    elif source_format in ("hex-capture", "hex-adapter"):
        import importlib.util
        spec = importlib.util.spec_from_file_location("analyst_hex_visual", Path(__file__).with_name("hex_visual.py"))
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        helpers = {"base": base, "add_asset": add_asset, "gap": gap, "facet": facet}
        result = (bridge.parse_capture(payload, raw, helpers) if source_format == "hex-capture" else
                  bridge.parse_adapter(payload, raw, helpers, producer_revision))
    elif source_format == "normalized-inventory":
        result = parse_normalized(payload, raw)
    elif source_format == "dma-inventory":
        result = parse_dma(payload, raw, producer_revision)
    elif source_format == "tableau-capture":
        import importlib.util
        spec = importlib.util.spec_from_file_location("analyst_tableau_visual", Path(__file__).with_name("tableau_visual.py"))
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        result = bridge.parse_capture(payload, raw,
            {"base": base, "add_asset": add_asset, "gap": gap, "facet": facet})
    elif source_format in ("powerbi-capture", "powerbi-adapter"):
        import importlib.util
        spec = importlib.util.spec_from_file_location("analyst_powerbi_visual", Path(__file__).with_name("powerbi_visual.py"))
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        helpers = {"base": base, "add_asset": add_asset, "gap": gap, "facet": facet}
        if source_format == "powerbi-capture":
            result = bridge.parse_capture(payload, raw, helpers)
        else:
            require(producer_revision == DMA_REVISION, "dma.unsupported_or_missing_producer_revision")
            result = bridge.parse_adapter(payload, raw, helpers, producer_revision)
    elif source_format in ("domo-agent", "sigma-agent"):
        # Load only our installed, local bridge. Never import the source engines.
        import importlib.util
        spec = importlib.util.spec_from_file_location("analyst_migration_sources", Path(__file__).with_name("migration_sources.py"))
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        result = bridge.parse_migration(payload, raw, source_format, producer_revision,
            {"base": base, "add_asset": add_asset, "gap": gap, "rows": rows,
             "require": require, "decode": decode, "facet": facet, "identity": identity})
    else:
        raise ValueError("input.unsupported_format")
    if result["source"]["platform"] == "looker":
        result["source"]["projection_version"] = "1.2.0"
    gap(result, "coverage.export_completeness_not_established")
    if not result["assets"]:
        gap(result, "coverage.no_assets_projected")
    gap(result, "security.effective_access_unverified")
    gap(result, "validation.native_and_business_parity_not_run")
    result["coverage"] = {"assets_received": len(result["assets"]),
        "denominator": "supplied_artifact_only", "status": "partial_evidence",
        "gaps": len(result["gaps"])}
    return result


def directory_fd(path):
    """Pin every directory; reject symlink ancestors and path replacement races."""
    path = Path(path).absolute()
    require(".." not in path.parts, "filesystem.parent_traversal")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_input(path):
    path = Path(path).absolute()
    fd = directory_fd(path.parent)
    try:
        with os.fdopen(os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd), "rb") as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_BYTES, "input.invalid_file")
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        require(len(raw) == before.st_size <= MAX_BYTES and before.st_mtime_ns == after.st_mtime_ns,
                "input.changed_or_oversized_file")
        return raw
    finally:
        os.close(fd)


def write_new(path, value):
    path = Path(path).absolute()
    data = encoded(value) + b"\n"
    require(len(data) <= MAX_BYTES * 6, "output.byte_limit")
    fd = directory_fd(path.parent)
    created = False
    try:
        handle = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        created = True
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if created:
            os.unlink(path.name, dir_fd=fd)
        raise
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", required=True, choices=("looker-api", "looker-capture", "looker-canonical", "looker-adapter", "hex-capture", "hex-adapter", "normalized-inventory", "dma-inventory", "domo-agent", "sigma-agent", "tableau-capture", "powerbi-capture", "powerbi-adapter"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--producer-revision")
    args = parser.parse_args(argv)
    try:
        result = translate(read_input(args.input), args.format, args.producer_revision)
        result["source"]["input_filename"] = args.input.name
        write_new(args.output, result)
        print(json.dumps({"status": "projected_with_review_gaps", "assets": len(result["assets"]),
                          "gaps": len(result["gaps"]), "native_validation": "not_run"}))
        return 0
    except (ValueError, OSError, TypeError, RecursionError, OverflowError, KeyError):
        print("Projection rejected: unsupported or malformed input, unsafe path, limit, or existing output. No source content printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
