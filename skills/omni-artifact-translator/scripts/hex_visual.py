"""Hex visual evidence projection. Original code is data, never a runtime."""

from __future__ import annotations
import copy
from pathlib import Path
import re

import importlib.util


def module(name):
    spec = importlib.util.spec_from_file_location(
        "hex_visual_" + name, Path(__file__).with_name(name + ".py")
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C = module("hex_capture")
F, need, text = C.F, C.need, C.text
SCHEMA = C.ENVELOPE
DMA_REVISION = "c513474e87af9c2c31deebd2ae675c8602955203"


def sha(value):
    return F.raw_sha(value) if type(value) is bytes else F.sha(value)


def file_pin(value):
    need(
        type(value) is dict
        and type(value.get("bytes")) is int
        and 0 <= value["bytes"] <= F.MAX_JSON
        and type(value.get("sha256")) is str
        and re.fullmatch("[a-f0-9]{64}", value["sha256"]),
        "hex.file_pin",
    )
    F.source_path(value.get("path"))


def definitions(files):
    need(type(files) is list and len(files) <= 256, "hex.definition_files")
    C.path_names([f.get("source_path") for f in files if type(f) is dict])
    C.path_names([f.get("path") for f in files if type(f) is dict])
    result = []
    for f in files:
        file_pin(f)
        content = f.get("content_utf8")
        need(
            type(content) is str
            and len(content.encode()) == f["bytes"]
            and sha(content.encode()) == f["sha256"],
            "hex.definition_text_hash",
        )
        F.safe_text(content.encode())
        result.append(
            (
                f,
                C.read_native(content.encode())
                if f["source_path"].endswith(".hex.yaml")
                else None,
            )
        )
    need(sum(f["bytes"] for f in files) <= C.MAX_SOURCE_BYTES, "hex.definition_size")
    return result


def inspect_definitions(files):
    """Enumerate source declarations independently of semantic extraction success."""
    parsed = definitions(files)
    fingerprint = C.definition_fingerprint(files)
    objects, relationships, gaps = [], [], []

    def gap(code, object_id, detail=None):
        gaps.append({"code": code, "object_id": object_id, "detail": detail})

    projects, components = {}, []
    for f, native in parsed:
        name, digest = f["source_path"], f["sha256"]
        if native is None:
            objects.append(
                {
                    "object_id": name + "#",
                    "kind": "unknown",
                    "native_id": None,
                    "payload": {
                        "source_path": name,
                        "sha256": digest,
                        "uninterpreted_supplied_file": True,
                    },
                    "source_identity": {
                        "source_platform": "hex",
                        "object_id": name + "#",
                        "source_file": name,
                        "definition_sha256": digest,
                        "definition_fingerprint": fingerprint,
                        "query_visual": False,
                        "project_id": None,
                        "source_version_id": None,
                        "cell_id": None,
                        "static_cell_id": None,
                    },
                }
            )
            gap("hex.companion_file_requires_review", name + "#")
            continue
        meta = native["meta"]
        pid, version = meta.get("projectId"), meta.get("sourceVersionId")
        base = {
            "source_platform": "hex",
            "source_file": name,
            "project_id": pid,
            "source_version_id": version,
            "definition_sha256": digest,
            "definition_fingerprint": fingerprint,
            "namespace": "definition:" + digest,
            "cell_id": None,
            "static_cell_id": None,
            "query_visual": False,
        }

        def add(pointer, kind, payload, native_id=None, **extra):
            oid = name + "#" + pointer
            objects.append(
                {
                    "object_id": oid,
                    "kind": kind,
                    "native_id": native_id,
                    "payload": copy.deepcopy(payload),
                    "source_identity": {**base, "object_id": oid, **extra},
                }
            )
            return oid

        project = add(
            "",
            "project" if meta.get("hexType") != "COMPONENT" else "definition",
            {"schemaVersion": native["schemaVersion"], "meta": meta},
            pid,
            is_component=meta.get("hexType") == "COMPONENT",
        )
        if pid:
            projects.setdefault(pid, []).append((version, project, meta.get("hexType")))
        if not pid or not version:
            gap("hex.native_project_or_version_identity_missing", project)
        if meta.get("hexType") not in ("PROJECT", "COMPONENT"):
            gap("hex.project_kind_requires_review", project)
        cells = native.get("cells", [])
        if not cells:
            gap("hex.cells_missing_or_empty", project)
        cell_index, cell_objects, visible = (
            {},
            {},
            set(native.get("dataAppCellIds") or []),
        )

        def walk(value):
            if type(value) is dict:
                yield value
                for v in value.values():
                    yield from walk(v)
            elif type(value) is list:
                for v in value:
                    yield from walk(v)

        for element in walk(native.get("appLayout")):
            if element.get("cellId") and not element.get("hideOutput", False):
                visible.add(element["cellId"])
        visual_types = {
            "CHART",
            "CHARTV2",
            "TABLE_DISPLAY",
            "MAP",
            "METRIC",
            "PIVOT",
            "DBT_METRIC",
            "EXPLORE",
        }
        for n, cell in enumerate(cells):
            cid, typ, config = cell.get("cellId"), cell["cellType"], cell["config"]
            cell_index.setdefault(cid, []).append(cell)
            if typ in visual_types or (typ in ("SQL", "CODE") and cid in visible):
                kind = "visual"
            elif typ in ("INPUT", "FILTER"):
                kind = "control"
            elif typ in ("MARKDOWN", "TEXT"):
                kind = "content"
            elif typ == "WRITEBACK":
                kind = "action"
            elif typ in ("SQL", "CODE", "COMPONENT_IMPORT"):
                kind = "definition"
            else:
                kind = "unknown"
            oid = add(
                "/cells/" + str(n),
                kind,
                cell,
                cid,
                cell_id=cid,
                cell_type=typ,
                query_visual=kind == "visual",
                declared_in_app=cid in visible,
                parent_object_id=project,
            )
            cell_objects.setdefault(cid, []).append(oid)
            if cid is None:
                gap("hex.cell_native_identity_missing", oid)
            if typ not in (
                "SQL",
                "CODE",
                "INPUT",
                "COMPONENT_IMPORT",
                "CHARTV2",
                "TEXT",
                "MARKDOWN",
            ):
                gap("hex.cell_behavior_not_semantically_interpreted", oid, typ)
            if typ in ("CODE", "SQL"):
                gap("hex.code_not_executed", oid)
            if typ == "INPUT":
                gap("hex.input_runtime_values_and_dependencies_unknown", oid)
                if config.get("inputType") in ("BUTTON", "FILE_UPLOAD", "TABLE"):
                    add(
                        "/cells/" + str(n) + "/config/inputType",
                        "action",
                        {"inputType": config["inputType"]},
                        parent_object_id=oid,
                        cell_id=cid,
                        cell_type=typ,
                        operation_unverified=True,
                    )
            if typ == "WRITEBACK":
                gap("hex.external_mutation_requires_separate_authority", oid)
            if typ == "COMPONENT_IMPORT":
                components.append((oid, config.get("component") or {}))
        for cid, rows in cell_index.items():
            if cid is not None and len(rows) > 1:
                gap("hex.duplicate_cell_identity", project, cid)
        layout = native.get("appLayout")
        if layout is not None:
            need(
                type(layout) is dict and type(layout.get("tabs")) is list,
                "hex.layout_structure",
            )
            add(
                "/appLayout",
                "layout",
                {k: v for k, v in layout.items() if k != "tabs"},
                parent_object_id=project,
            )
            for tn, tab in enumerate(layout["tabs"]):
                need(
                    type(tab) is dict and type(tab.get("rows")) is list,
                    "hex.tab_structure",
                )
                tp = "/appLayout/tabs/" + str(tn)
                tabid = add(
                    tp,
                    "page",
                    {k: v for k, v in tab.items() if k != "rows"},
                    parent_object_id=project,
                )
                for rn, row in enumerate(tab["rows"]):
                    need(
                        type(row) is dict and type(row.get("columns")) is list,
                        "hex.row_structure",
                    )
                    rp = tp + "/rows/" + str(rn)
                    rowid = add(
                        rp,
                        "layout",
                        {k: v for k, v in row.items() if k != "columns"},
                        parent_object_id=tabid,
                    )
                    for cn, column in enumerate(row["columns"]):
                        need(
                            type(column) is dict
                            and type(column.get("elements")) is list,
                            "hex.column_structure",
                        )
                        cp = rp + "/columns/" + str(cn)
                        colid = add(
                            cp,
                            "layout",
                            {k: v for k, v in column.items() if k != "elements"},
                            parent_object_id=rowid,
                        )
                        for en, element in enumerate(column["elements"]):
                            need(type(element) is dict, "hex.element_structure")
                            cid = element.get("cellId")
                            candidates = cell_index.get(cid, []) if cid else []
                            resolved = len(candidates) == 1
                            target = cell_objects[cid][0] if resolved else None
                            typ = candidates[0]["cellType"] if resolved else None
                            query = (
                                resolved
                                and (typ in visual_types or typ in ("SQL", "CODE"))
                                and not element.get("hideOutput", False)
                            )
                            oid = add(
                                cp + "/elements/" + str(en),
                                "placement",
                                element,
                                parent_object_id=colid,
                                tab_object_id=tabid,
                                cell_id=cid,
                                cell_object_id=target,
                                cell_type=typ,
                                query_visual=query,
                                shared_filter_id=element.get("sharedFilterId"),
                            )
                            relationships.append(
                                {
                                    "from": oid,
                                    "to": target,
                                    "kind": "placement_cell",
                                    "native_target": cid,
                                    "resolution": "declared_reference"
                                    if resolved
                                    else "unresolved",
                                }
                            )
                            if not resolved:
                                gap("hex.placement_target_unresolved", oid)
        elif not native.get("dataAppCellIds") and not native.get("genAppFiles"):
            gap("hex.app_layout_not_supplied", project)
        selected = native.get("dataAppCellIds", [])
        need(type(selected) is list, "hex.data_app_cell_ids")
        for n, cid in enumerate(selected):
            targets = cell_objects.get(cid, [])
            oid = add(
                "/dataAppCellIds/" + str(n),
                "placement",
                {"cellId": cid},
                cell_id=cid,
                cell_object_id=targets[0] if len(targets) == 1 else None,
                query_visual=False,
                generated_app_binding=True,
            )
            relationships.append(
                {
                    "from": oid,
                    "to": targets[0] if len(targets) == 1 else None,
                    "kind": "generated_app_cell",
                    "native_target": cid,
                    "resolution": "declared_reference"
                    if len(targets) == 1
                    else "unresolved",
                }
            )
            if len(targets) != 1:
                gap("hex.data_app_cell_unresolved", oid)
        filters = native.get("sharedFilters", [])
        need(type(filters) is list, "hex.shared_filters_structure")
        for n, filt in enumerate(filters):
            need(type(filt) is dict, "hex.shared_filter_structure")
            oid = add(
                "/sharedFilters/" + str(n),
                "control",
                filt,
                shared_filter=True,
                parent_object_id=project,
            )
            gap("hex.shared_filter_crosswalk_and_effective_scope_unverified", oid)
            for key in ("manualLinks", "autoLinks"):
                for index, link in enumerate(filt.get(key) or []):
                    need(type(link) is dict, "hex.shared_filter_link_structure")
                    lid = add(
                        "/sharedFilters/" + str(n) + "/" + key + "/" + str(index),
                        "definition",
                        link,
                        parent_object_id=oid,
                    )
                    relationships.append(
                        {
                            "from": oid,
                            "to": lid,
                            "kind": key,
                            "resolution": "declared_only",
                        }
                    )
        generated = native.get("genAppFiles", [])
        for n, g in enumerate(generated):
            add(
                "/genAppFiles/" + str(n),
                "definition",
                g,
                generated_file=True,
                generated_path=g["path"],
                parent_object_id=project,
            )
        if generated:
            oid = add(
                "/unresolved/generated_interface",
                "unknown",
                {
                    "reason": "Conditional screens, events and custom charts require independent interface inventory"
                },
                generated_interface_unobserved=True,
                id_kind="review_obligation",
            )
            gap("hex.generated_interface_inventory_unverified", oid)
        for key in ("sharedAssets", "projectAssets"):
            for category, entries in native.get(key, {}).items():
                add(
                    "/" + key + "/" + category,
                    "definition",
                    {category: entries},
                    parent_object_id=project,
                )
        known = {
            "schemaVersion",
            "meta",
            "cells",
            "appLayout",
            "dataAppCellIds",
            "genAppFiles",
            "sharedAssets",
            "projectAssets",
            "sharedFilters",
        }
        for key in sorted(set(native) - known):
            oid = add(
                "/" + key.replace("~", "~0").replace("/", "~1"),
                "unknown",
                {key: native[key]},
                parent_object_id=project,
            )
            gap("hex.unknown_project_field", oid)
    for pid, matches in projects.items():
        if len(matches) != 1:
            gap("hex.multiple_project_versions_require_selection", matches[0][1], pid)
    for oid, ref in components:
        matches = projects.get(ref.get("id"), [])
        targets = [
            target
            for version, target, typ in matches
            if version == ref.get("version")
            and version is not None
            and typ == "COMPONENT"
        ]
        relationships.append(
            {
                "from": oid,
                "to": targets[0] if len(targets) == 1 else None,
                "kind": "component_reference",
                "native_target": copy.deepcopy(ref),
                "resolution": "supplied_version" if len(targets) == 1 else "unresolved",
            }
        )
        gap(
            "hex.component_runtime_unverified"
            if len(targets) == 1
            else "hex.component_missing_or_version_mismatch",
            oid,
        )
    need(len(objects) <= 5000, "hex.object_limit")
    return {
        "schema_version": 1,
        "kind": "hex_visual_structure",
        "definition_fingerprint": fingerprint,
        "objects": objects,
        "dependencies": relationships,
        "gaps": gaps,
    }


def validate_adapter(value):
    need(
        type(value) is dict
        and value.get("kind") == "source_adapter_result"
        and value.get("schema_version") == 1
        and value.get("source") == "hex"
        and value.get("adapter_version") == 1,
        "hex.dma_adapter_contract",
    )
    for key in ("source_files", "objects", "expressions", "dependencies", "gaps"):
        need(
            type(value.get(key)) is list and len(value[key]) <= 20000,
            "hex.dma_collection",
        )
    source = {}
    for f in value["source_files"]:
        F.source_path(f.get("path"))
        need(
            f["path"] not in source
            and re.fullmatch("[a-f0-9]{64}", f.get("sha256", "")),
            "hex.dma_file_identity",
        )
        source[f["path"]] = f
    C.path_names(list(source))
    ids = set()
    for category in ("objects", "expressions", "dependencies", "gaps"):
        for row in value[category]:
            evidence = row.get("evidence", {})
            need(
                evidence.get("path") in source
                and evidence.get("sha256") == source[evidence["path"]]["sha256"]
                and text(evidence.get("locator")),
                "hex.dma_evidence_mismatch",
            )
            if category in ("objects", "expressions"):
                need(
                    text(row.get("id")) and row["id"] not in ids,
                    "hex.dma_duplicate_object",
                )
                ids.add(row["id"])
            if category == "expressions":
                need(
                    type(row.get("text")) is str
                    and row.get("content_sha256") == sha(row["text"].encode()),
                    "hex.dma_expression_hash",
                )
    return value


def adapter_definitions(value):
    validate_adapter(value)
    result, seen = [], set()
    for e in value["expressions"]:
        if (
            e.get("language") == "hex_yaml"
            and e.get("details", {}).get("interpretation") == "original_export"
        ):
            path, raw = e["evidence"]["path"], e["text"].encode()
            need(
                path not in seen and e["evidence"]["sha256"] == sha(raw),
                "hex.dma_original_export_mismatch",
            )
            seen.add(path)
            # An unsupported schema remains an unknown source-file obligation.
            try:
                C.read_native(raw)
            except ValueError:
                continue
            result.append(
                {
                    "path": path,
                    "source_path": path,
                    "content_utf8": e["text"],
                    "sha256": sha(raw),
                    "bytes": len(raw),
                }
            )
    originals = {
        f["source_path"]: C.read_native(f["content_utf8"].encode()) for f in result
    }
    for obj in value["objects"]:
        native = originals.get(obj["evidence"]["path"])
        if native is None:
            continue
        locator, details = obj["evidence"]["locator"], obj.get("details", {})
        if obj.get("kind") in ("hex_project", "hex_component"):
            need(
                locator == "$.meta"
                and obj.get("native_id") == native["meta"].get("projectId")
                and details.get("source_version_id")
                == native["meta"].get("sourceVersionId")
                and details.get("native_properties")
                == {k: v for k, v in native.items() if k != "cells"},
                "hex.dma_project_contradiction",
            )
        elif obj.get("kind") == "hex_cell":
            match = re.fullmatch(r"\$\.cells\[(\d+)\]", locator)
            need(
                match is not None and int(match[1]) < len(native.get("cells", [])),
                "hex.dma_cell_locator",
            )
            cell = native["cells"][int(match[1])]
            need(
                obj.get("native_id") == cell.get("cellId")
                and details.get("native_properties") == cell
                and details.get("cell_type") == cell["cellType"],
                "hex.dma_cell_contradiction",
            )
    return result


def validate_capture(value):
    need(
        type(value) is dict
        and value.get("schema_version") == SCHEMA
        and value.get("content_hash")
        == sha({k: v for k, v in value.items() if k != "content_hash"}),
        "hex.capture_hash",
    )
    r = value.get("request")
    need(
        r == C.validate_request(r)
        and value.get("request_sha256") == sha(r)
        and value.get("capture_id") == r["capture_id"],
        "hex.capture_request",
    )
    need(
        value.get("source_execution") is False
        and value.get("target_write_authority") is False
        and value.get("native_validation") == "not_performed"
        and value.get("business_acceptance") == "not_assessed",
        "hex.capture_authority",
    )
    source = value.get("source")
    need(type(source) is dict, "hex.source_required")
    need(
        all(
            source.get("identity", {}).get(k) == r[k]
            for k in ("source_origin", "workspace_id", "principal_ref")
        )
        and source["identity"].get("principal_verification") == "supplied_unverified",
        "hex.identity_mismatch",
    )
    parsed = definitions(source.get("definition_files"))
    need(
        source.get("definition_fingerprint")
        == C.definition_fingerprint(source["definition_files"]),
        "hex.definition_fingerprint",
    )
    expected_projects = []
    for f, native in parsed:
        if native is None:
            continue
        e = [e for e in r["exports"] if e["source_path"] == f["source_path"]]
        need(
            len(e) == 1
            and e[0]["project_id"] in (None, native["meta"].get("projectId"))
            and e[0]["expected_source_version_id"]
            in (None, native["meta"].get("sourceVersionId")),
            "hex.export_identity_mismatch",
        )
        expected_projects.append(
            {
                "source_path": f["source_path"],
                "project_id": native["meta"].get("projectId"),
                "source_version_id": native["meta"].get("sourceVersionId"),
                "hex_type": native["meta"].get("hexType"),
                "definition_sha256": f["sha256"],
            }
        )
    need(source.get("projects") == expected_projects, "hex.project_identity_mismatch")
    outputs = {o["output_id"]: o for o in r["outputs"]}
    need(
        type(value.get("attachments")) is list and len(value["attachments"]) <= 1000,
        "hex.attachments_required",
    )
    paths = []
    for a in value["attachments"]:
        file_pin(a)
        paths.append(a["path"])
        o = outputs.get(a.get("output_id"))
        need(
            o is not None
            and all(a.get(k) == v for k, v in o.items())
            and a.get("request_sha256") == value["request_sha256"]
            and a.get("state_sha256") == sha(r["state"]),
            "hex.attachment_binding",
        )
        C.output_definition(value, o)
        kind = a.get("format")
        need(
            kind in ("png", "pdf", "json", "csv")
            and a.get("media_type")
            == {
                "png": "image/png",
                "pdf": "application/pdf",
                "json": "application/json",
                "csv": "text/csv",
            }[kind]
            and text(a.get("provenance_reference")),
            "hex.attachment_media",
        )
        complete = a.get("result_completeness", {})
        need(
            type(complete) is dict
            and complete.get("status") in ("complete", "partial", "unknown")
            and type(complete.get("flags")) is list
            and all(type(f) is str for f in complete["flags"])
            and (
                complete.get("status") != "complete"
                or (text(complete.get("reference")) and not complete["flags"])
            ),
            "hex.result_completeness",
        )
        if a.get("original_response") is not None:
            file_pin(a["original_response"])
        if a.get("acquisition") == "transferred_mcp_image":
            need(
                kind == "png"
                and o["source_mode"] == "draft"
                and a.get("original_response"),
                "hex.mcp_draft_image",
            )
        if a.get("acquisition") == "completed_run_api":
            need(
                kind == "png" and o["source_mode"] == "published", "hex.run_image_mode"
            )
            run = source.get("runs", {}).get(o["output_id"], {})
            need(
                run.get("status") == "COMPLETED"
                and run.get("projectId") == o["project_id"]
                and run.get("runId") == o["run_id"]
                and str(run.get("projectVersion")) == o["expected_project_version"],
                "hex.run_image_identity",
            )
    C.path_names(paths)
    for key in ("state_observations", "render_state_observations"):
        need(
            type(source.get(key)) is list and len(source[key]) <= 1000,
            "hex.observation_list",
        )
        for obs in source[key]:
            need(
                type(obs) is dict
                and obs.get("output_id") in outputs
                and type(obs.get("applied")) is bool
                and text(obs.get("reference"))
                and obs.get("state_sha256") == sha(r["state"]),
                "hex.observation_binding",
            )
            o = outputs[obs["output_id"]]
            need(
                all(
                    obs.get(k) == o[k]
                    for k in (
                        "project_id",
                        "source_version_id",
                        "cell_id",
                        "run_id",
                        "source_mode",
                    )
                ),
                "hex.observation_identity",
            )
    for name in ("adapter_result", "semantic_inventory"):
        p = source.get(name)
        if p is not None:
            need(
                source.get(name + "_sha256") == sha(p)
                and source.get("dma_producer_revision") == DMA_REVISION,
                "hex.dma_payload_pin",
            )
            if name == "adapter_result":
                validate_adapter(p)
                pins = p["source_files"]
            else:
                need(
                    p.get("kind") == "hex_source_inventory"
                    and p.get("schema_version") == 1,
                    "hex.legacy_kind",
                )
                pins = p.get("assets", [])
            index = {f["source_path"]: f for f in source["definition_files"]}
            need(
                all(
                    f.get("path") in index
                    and f.get("sha256") == index[f["path"]]["sha256"]
                    for f in pins
                ),
                "hex.dma_source_hash_mismatch",
            )
    need(
        value.get("status") in ("complete", "partial", "blocked")
        and type(value.get("gaps")) is list,
        "hex.capture_status",
    )
    if value["status"] == "complete":
        need(
            value["producer"].get("mode") == "rest"
            and set(e["source_path"] for e in r["exports"])
            <= {f["source_path"] for f in source["definition_files"]},
            "hex.false_acquisition_completion",
        )
        for e in r["exports"]:
            before, after = (
                source.get("metadata_before", {}).get(e["source_path"]),
                source.get("metadata_after", {}).get(e["source_path"]),
            )
            need(
                type(before) is dict
                and type(after) is dict
                and before.get("id") == after.get("id") == e["project_id"]
                and all(
                    before.get(k) == after.get(k)
                    for k in ("lastEditedAt", "lastPublishedAt")
                ),
                "hex.metadata_coherence",
            )
        need(
            all(
                any(
                    a.get("output_id") == i["output_id"]
                    and a.get("acquisition") == "completed_run_api"
                    for a in value["attachments"]
                )
                for i in r["images"]
            ),
            "hex.missing_image",
        )
        plan = C.operation_plan(r)
        ops = value.get("operations", [])
        need(
            {o.get("key") for o in ops if o.get("status") == "complete"} == set(plan),
            "hex.complete_operations_required",
        )
    return value


def verify_capture_files(value, root):
    validate_capture(value)
    root = F.no_links(root)
    pins = list(value["source"]["definition_files"]) + list(value["attachments"])
    pins.extend(
        a["original_response"]
        for a in value["attachments"]
        if a.get("original_response")
    )
    pins.extend(
        op["response"] for op in value.get("operations", []) if op.get("response")
    )
    for pin in pins:
        file_pin(pin)
        raw = F.read_pin(root, pin)
        if pin.get("content_utf8") is not None:
            need(raw == pin["content_utf8"].encode(), "hex.source_file_changed")
        if pin.get("format") == "png":
            F.png_info(raw)
        elif pin.get("format") in ("json", "csv"):
            F.safe_text(raw)
            if pin["format"] == "json":
                data = F.decode(raw)
                F.secret_check(data)
                if pin["result_completeness"]["status"] == "complete":
                    stack = [data]
                    while stack:
                        current = stack.pop()
                        if type(current) is dict:
                            need(
                                not any(
                                    current.get(k)
                                    for k in (
                                        "error",
                                        "errors",
                                        "truncated",
                                        "isTruncated",
                                    )
                                ),
                                "hex.complete_result_has_errors_or_truncation",
                            )
                            stack.extend(current.values())
                        elif type(current) is list:
                            stack.extend(current)
    operations = {o["key"]: o for o in value.get("operations", [])}
    if value["producer"].get("mode") == "rest":
        plan = C.operation_plan(value["request"])
        need(len(operations) == len(value["operations"]), "hex.duplicate_operation")
        for key, op in operations.items():
            need(key in plan, "hex.operation_not_allowed")
            method, path, body = plan[key]
            need(
                op.get("operation_sha256")
                == sha({"method": method, "path": path, "body": body})
                and op.get("method") == method
                and op.get("path") == path
                and op.get("body") == body,
                "hex.operation_request_changed",
            )
        for n, e in enumerate(value["request"]["exports"]):
            for phase in ("before", "after"):
                op = operations.get(f"export.{n}.{phase}", {})
                if op.get("status") == "complete":
                    response = F.decode(F.read_pin(root, op["response"]))
                    found = [
                        f
                        for f in value["source"]["definition_files"]
                        if f["source_path"] == e["source_path"]
                    ]
                    # In a blocked journal the after response may honestly contain drift.
                    if found and (phase == "before" or value["status"] == "complete"):
                        need(
                            sha(response["content"].encode()) == found[0]["sha256"],
                            "hex.export_response_mismatch",
                        )
        for n, e in enumerate(value["request"]["exports"]):
            for phase in ("before", "after"):
                op = operations.get(f"metadata.{n}.{phase}", {})
                if op.get("status") == "complete":
                    data = F.decode(F.read_pin(root, op["response"]))
                    recorded = (
                        value["source"]
                        .get("metadata_" + phase, {})
                        .get(e["source_path"])
                    )
                    if recorded is not None:
                        need(data == recorded, "hex.metadata_response_mismatch")
        for a in value["attachments"]:
            if a.get("acquisition") == "completed_run_api":
                output = next(
                    o
                    for o in value["request"]["outputs"]
                    if o["output_id"] == a["output_id"]
                )
                image = next(
                    i
                    for i in value["request"]["images"]
                    if i["output_id"] == a["output_id"]
                )
                runop = operations.get("run." + a["output_id"], {})
                need(
                    runop.get("status") == "complete"
                    and F.decode(F.read_pin(root, runop["response"]))
                    == value["source"]["runs"][a["output_id"]],
                    "hex.run_response_mismatch",
                )
                op = operations.get("image." + a["output_id"], {})
                need(op.get("status") == "complete", "hex.image_operation_required")
                decoded = C.run_image(F.read_pin(root, op["response"]), output, image)
                need(sha(decoded) == a["sha256"], "hex.image_response_changed")
    for a in value["attachments"]:
        if a.get("acquisition") == "transferred_mcp_image":
            import base64

            response = F.decode(F.read_pin(root, a["original_response"]))
            need(response.get("isError") is not True, "hex.mcp_response_error")
            images = [
                c for c in response.get("content", []) if c.get("type") == "image"
            ]
            need(
                len(images) == 1
                and images[0].get("mimeType") == "image/png"
                and sha(base64.b64decode(images[0]["data"], validate=True))
                == a["sha256"],
                "hex.mcp_image_bytes_mismatch",
            )
    return {
        "status": "verified_local_bytes",
        "files": len(pins),
        "origin_authenticated": False,
    }


def project_structure(result, structure, helpers):
    for row in structure["objects"]:
        identity = row["source_identity"]
        helpers["add_asset"](
            result,
            row["kind"],
            row["payload"],
            row["object_id"],
            row["native_id"],
            identity.get("project_id"),
            {
                "visual": helpers["facet"](row["payload"], ("cellType", "config")),
                "layout": helpers["facet"](
                    row["payload"],
                    (
                        "start",
                        "end",
                        "height",
                        "hideOutput",
                        "showSource",
                        "fullWidth",
                        "visibleMetadataFields",
                    ),
                ),
                "query": helpers["facet"](row["payload"], ("config",), "declared"),
                "filters": helpers["facet"](
                    row["payload"],
                    ("config", "manualLinks", "autoLinks", "defaultValue", "options"),
                ),
                "content": helpers["facet"](
                    row["payload"], ("cellLabel", "name", "meta", "contents")
                ),
                "interactions": {"status": "needs_review", "value": None},
                "security": {"status": "needs_review", "value": None},
            },
            "native_id"
            if row["native_id"] is not None
            else identity.get("id_kind", "structural_locator"),
            identity,
        )
        result["assets"][-1]["asset_key"] = (
            "asset:"
            + sha(
                [
                    "hex",
                    identity["definition_fingerprint"],
                    row["object_id"],
                    row["kind"],
                ]
            )[:24]
        )
    result["dependencies"] = copy.deepcopy(structure["dependencies"])
    for g in structure["gaps"]:
        helpers["gap"](result, g["code"], g["object_id"], g.get("detail"))


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    result = helpers["base"](payload, raw, "hex", "supplied_hex_visual_capture")
    structure = inspect_definitions(payload["source"]["definition_files"])
    project_structure(result, structure, helpers)
    result["source"]["definition_fingerprint"] = payload["source"][
        "definition_fingerprint"
    ]
    result["source"]["source_identity"] = copy.deepcopy(payload["source"]["identity"])
    result["migration_context"] = {
        k: payload["request"][k] for k in ("route", "route_reference", "target_surface")
    }
    actual = {a["source_path"] for a in result["assets"]}
    for expected in payload["request"]["expected_manifest"]["objects"]:
        if expected["object_id"] not in actual:
            helpers["add_asset"](
                result,
                "unknown",
                {"missing_from_capture": True, "expected": expected},
                expected["object_id"],
                None,
                source_identity={
                    "source_platform": "hex",
                    "object_id": expected["object_id"],
                    "expected_kind": expected["kind"],
                    "definition_fingerprint": payload["source"][
                        "definition_fingerprint"
                    ],
                    "query_visual": expected["kind"] == "visual",
                },
            )
            helpers["gap"](result, "hex.expected_object_missing", expected["object_id"])
    for g in payload["gaps"]:
        helpers["gap"](result, "hex.capture_gap", detail=g)
    for name in ("semantic_inventory", "adapter_result"):
        if payload["source"].get(name):
            for g in payload["source"][name].get("gaps", []):
                helpers["gap"](result, "hex.dma_upstream_gap", detail=g)
            if name == "adapter_result":
                result["dependencies"].extend(
                    {"kind": "dma_candidate", "evidence": copy.deepcopy(d)}
                    for d in payload["source"][name]["dependencies"]
                )
    result["hex_coverage"] = {
        "expected_manifest": copy.deepcopy(payload["request"]["expected_manifest"]),
        "missing_expected": [
            o["object_id"]
            for o in payload["request"]["expected_manifest"]["objects"]
            if o["object_id"] not in actual
        ],
        "denominator_authenticated": False,
    }
    return result


def parse_adapter(payload, raw, helpers, revision):
    need(revision == DMA_REVISION, "hex.unsupported_dma_revision")
    files = adapter_definitions(payload)
    result = helpers["base"](payload, raw, "hex", "supplied_hex_source_adapter_result")
    result["source"]["producer"] = {
        "name": "DataModelAccelerator",
        "revision": revision,
        "revision_evidence": "operator_declared_not_authenticated",
    }
    structure = inspect_definitions(files)
    project_structure(result, structure, helpers)
    covered = {f["source_path"] for f in files}
    for f in payload["source_files"]:
        if f["path"] not in covered:
            helpers["add_asset"](
                result,
                "unknown",
                f,
                f["path"] + "#",
                None,
                source_identity={
                    "source_platform": "hex",
                    "source_file": f["path"],
                    "object_id": f["path"] + "#",
                    "definition_sha256": f["sha256"],
                    "definition_fingerprint": structure["definition_fingerprint"],
                    "query_visual": False,
                },
            )
            helpers["gap"](result, "hex.dma_uninterpreted_source_file", f["path"])
    result["dependencies"].extend(
        {"kind": "dma_candidate", "evidence": copy.deepcopy(d)}
        for d in payload["dependencies"]
    )
    for g in payload["gaps"]:
        helpers["gap"](result, "hex.dma_upstream_gap", detail=g)
    return result


def normalize_results(raw, profile, binding):
    fields = {
        "capture_content_hash",
        "project_id",
        "source_version_id",
        "cell_id",
        "output_id",
        "state_sha256",
        "attachment_sha256",
    }
    need(
        type(binding) is dict
        and set(binding) == fields
        and binding["attachment_sha256"] == sha(raw)
        and all(
            C.uuid(binding[k]) for k in ("project_id", "source_version_id", "cell_id")
        )
        and C.local_id(binding["output_id"])
        and all(
            re.fullmatch("[a-f0-9]{64}", str(binding[k]))
            for k in ("capture_content_hash", "state_sha256", "attachment_sha256")
        ),
        "hex.normalization_binding",
    )
    mapped = {
        "capture_content_hash": binding["capture_content_hash"],
        "page_id": binding["project_id"],
        "visual_id": binding["cell_id"],
        "query_id": binding["output_id"],
        "state_sha256": binding["state_sha256"],
        "attachment_sha256": binding["attachment_sha256"],
    }
    normalized = module("powerbi_visual").normalize_results(raw, profile, mapped)
    normalized.update(kind="hex_normalized_results", binding=copy.deepcopy(binding))
    return normalized
