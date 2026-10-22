#!/usr/bin/env python3
"""Fixed-scope Looker evidence acquisition; no source lifecycle or target writes."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta, timezone
import fcntl
import importlib.util
import os
from pathlib import Path, PurePosixPath
import re
import signal
import sys
import threading
import time
import unicodedata
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

# Reuse the reviewed passive file boundary, not another platform's acquisition engine.
_spec = importlib.util.spec_from_file_location(
    "looker_passive_files", Path(__file__).with_name("powerbi_capture_files.py")
)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
CaptureError, need, sha, encoded = F.CaptureError, F.need, F.sha, F.encoded
REQUEST = "looker-visual-capture-request.v1"
ENVELOPE = "looker-visual-capture.v1"
DEFAULT_MAX_REQUESTS = 40
MAX_EMBEDDED_SOURCE_BYTES = 4_000_000
API = "/api/4.0"
BASE_GAPS = [
    "requested_state_is_not_observed_state",
    "result_completeness_not_established",
    "configuration_bracket_not_atomic_data_snapshot",
    "effective_access_not_verified",
    "semantic_models_not_acquired",
    "drill_links_and_source_actions_not_followed",
    "merged_result_execution_not_implemented",
    "native_and_business_acceptance_not_performed",
]


def utcnow():
    return datetime.now(timezone.utc)


def text(value, maximum=1000):
    return (
        type(value) is str
        and 0 < len(value) <= maximum
        and not any(ord(c) < 32 for c in value)
    )


def opaque(value):
    return (
        text(value, 512)
        and value not in (".", "..")
        and not any(c in value for c in ("/", "\\", "%", "?", "#"))
    )


def local_id(value):
    return (
        type(value) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", value) is not None
    )


def segment(value):
    need(opaque(value), "opaque_identity_rejected")
    return quote(value, safe="")


def validate_request(value, *, require_service=False):
    required = {
        "schema_version",
        "capture_id",
        "source_instance",
        "api_version",
        "dashboard_id",
        "principal_ref",
        "authorization_ref",
        "evidence_mode",
        "route",
        "route_reference",
        "target_surface",
        "views",
        "state",
        "renders",
        "queries",
    }
    defaults = {
        "expected_user_id": None,
        "source_revision": None,
        "max_requests_per_invocation": DEFAULT_MAX_REQUESTS,
        "max_total_requests": 500,
        "max_total_bytes": 64_000_000,
        "max_elapsed_seconds": 21600,
        "max_attempts_per_operation": 5,
        "max_response_bytes": F.MAX_FILE,
        "max_dependencies": 100,
        "expected_manifest": {
            "reference": "not_supplied",
            "completeness": "partial",
            "objects": [],
        },
    }
    need(
        type(value) is dict
        and value.get("schema_version") == REQUEST
        and required <= set(value)
        and not set(value) - required - set(defaults),
        "request_contract_required",
    )
    result = {**defaults, **copy.deepcopy(value)}
    need(
        local_id(result["capture_id"]) and result["api_version"] == "4.0",
        "request_identity_or_api_rejected",
    )
    origin = result["source_instance"]
    if origin is not None:
        need(text(origin, 512), "source_origin_required")
        parsed = urlsplit(origin)
        need(
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and parsed.port in (None, 443, 19999)
            and re.fullmatch(r"[A-Za-z0-9.-]+(?::(?:443|19999))?", parsed.netloc),
            "approved_https_origin_required",
        )
    need(
        (origin is not None or not require_service)
        and (
            opaque(result["dashboard_id"])
            or (result["dashboard_id"] is None and not require_service)
        ),
        "service_identity_required",
    )
    for key in ("principal_ref", "authorization_ref"):
        need(text(result[key]), "source_authorization_reference_required")
    need(
        result["expected_user_id"] is None or opaque(result["expected_user_id"]),
        "expected_user_identity_rejected",
    )
    need(
        result["source_revision"] is None or text(result["source_revision"]),
        "source_revision_rejected",
    )
    need(
        result["target_surface"] in ("dashboard", "app", "both"),
        "target_surface_required",
    )
    need(
        result["evidence_mode"]
        in ("synthetic_fixture", "live_tenant", "manual_transfer"),
        "evidence_mode_required",
    )
    need(
        result["route"]
        in (
            "unselected",
            "reuse_existing",
            "omni_semantic_reconstruction",
            "warehouse_first_refactor",
        )
        and (result["route"] == "unselected" or text(result["route_reference"])),
        "reviewed_route_required",
    )
    limits = {
        "max_requests_per_invocation": (1, 500),
        "max_total_requests": (1, 5000),
        "max_total_bytes": (1, 512_000_000),
        "max_elapsed_seconds": (1, 86400),
        "max_attempts_per_operation": (1, 20),
        "max_response_bytes": (1, F.MAX_FILE),
        "max_dependencies": (1, 500),
    }
    for key, (low, high) in limits.items():
        need(
            type(result[key]) is int and low <= result[key] <= high,
            "request_budget_rejected",
        )
    state = result["state"]
    need(
        type(state) is dict
        and set(state)
        == {
            "state_id",
            "filters",
            "parameters",
            "timezone",
            "locale",
            "principal",
            "data_time_policy",
        }
        and text(state["state_id"])
        and text(state["data_time_policy"]),
        "state_contract_required",
    )
    for key in ("filters", "parameters"):
        need(
            type(state[key]) is dict
            and len(state[key]) <= 100
            and all(
                text(k, 256) and type(v) is str and len(v) <= 4000
                for k, v in state[key].items()
            ),
            "state_values_rejected",
        )
    for key in ("timezone", "locale", "principal"):
        need(state[key] is None or text(state[key], 256), "state_context_rejected")
    views = result["views"]
    need(
        type(views) is list
        and len(views) <= 200
        and all(
            type(v) is dict
            and set(v) == {"element_id", "tab_id", "layout_id"}
            and all(x is None or opaque(x) for x in v.values())
            for v in views
        ),
        "view_scope_rejected",
    )
    need(len({sha(v) for v in views}) == len(views), "duplicate_view")
    renders = result["renders"]
    need(type(renders) is list and len(renders) <= 20, "render_scope_limit")
    ids = set()
    for row in renders:
        need(
            type(row) is dict
            and set(row)
            == {"render_id", "tab_ids", "width", "height", "dashboard_style", "theme"}
            and local_id(row["render_id"])
            and row["render_id"] not in ids,
            "render_contract_rejected",
        )
        ids.add(row["render_id"])
        need(
            type(row["tab_ids"]) is list
            and len(row["tab_ids"]) <= 50
            and all(opaque(v) for v in row["tab_ids"])
            and len(set(row["tab_ids"])) == len(row["tab_ids"]),
            "render_tabs_rejected",
        )
        need(
            all(
                type(row[k]) is int and 1 <= row[k] <= 8192 for k in ("width", "height")
            )
            and row["width"] * row["height"] <= 16_000_000,
            "render_dimensions_rejected",
        )
        need(
            row["dashboard_style"] in ("single_column", "tiled")
            and (row["theme"] is None or text(row["theme"], 256)),
            "render_options_rejected",
        )
    queries = result["queries"]
    need(type(queries) is list and len(queries) <= 100, "query_scope_limit")
    ids = set()
    for row in queries:
        need(
            type(row) is dict
            and {
                "binding_id",
                "element_id",
                "query_id",
                "inline_query",
                "context_reference",
                "options",
            }
            <= set(row)
            and not set(row)
            - {
                "binding_id",
                "element_id",
                "query_id",
                "inline_query",
                "context_reference",
                "options",
                "source_query_id",
            }
            and local_id(row["binding_id"])
            and row["binding_id"] not in ids
            and opaque(row["element_id"])
            and any(v["element_id"] == row["element_id"] for v in views)
            and text(row["context_reference"]),
            "query_binding_rejected",
        )
        ids.add(row["binding_id"])
        row.setdefault("source_query_id", row["query_id"])
        need(
            row["source_query_id"] is None or opaque(row["source_query_id"]),
            "source_query_identity_rejected",
        )
        need(
            (opaque(row["query_id"]) and row["inline_query"] is None)
            or (row["query_id"] is None and type(row["inline_query"]) is dict),
            "one_query_execution_mode_required",
        )
        options = row["options"]
        need(
            type(options) is dict
            and set(options)
            == {
                "limit",
                "cache",
                "cache_only",
                "force_production",
                "server_table_calcs",
            }
            and type(options["limit"]) is int
            and 1 <= options["limit"] <= 100000
            and all(type(options[k]) is bool for k in options if k != "limit"),
            "query_options_rejected",
        )
        body = row["inline_query"]
        if body is not None:
            permitted = {
                "model",
                "view",
                "fields",
                "pivots",
                "fill_fields",
                "filters",
                "filter_expression",
                "sorts",
                "limit",
                "column_limit",
                "total",
                "row_total",
                "subtotals",
                "vis_config",
                "filter_config",
                "dynamic_fields",
                "query_timezone",
            }
            need(
                not set(body) - permitted
                and text(body.get("model"), 256)
                and text(body.get("view"), 256)
                and type(body.get("fields")) is list
                and 0 < len(body["fields"]) <= 1000
                and all(text(v) for v in body["fields"])
                and body.get("filter_config") is None
                and len(encoded(body)) <= 256000,
                "inline_query_contract_rejected",
            )
            for key in ("limit", "column_limit"):
                if key in body:
                    need(
                        type(body[key]) is str
                        and body[key].isdigit()
                        and 1 <= int(body[key]) <= 100000,
                        "inline_query_limit_rejected",
                    )
    manifest = result["expected_manifest"]
    need(
        type(manifest) is dict
        and set(manifest) == {"reference", "completeness", "objects"}
        and text(manifest["reference"])
        and manifest["completeness"] in ("selected_dashboard", "partial")
        and type(manifest["objects"]) is list
        and len(manifest["objects"]) <= 5000
        and all(
            type(o) is dict
            and set(o) == {"object_id", "kind"}
            and text(o["object_id"])
            and text(o["kind"])
            for o in manifest["objects"]
        ),
        "expected_manifest_rejected",
    )
    need(
        len({o["object_id"] for o in manifest["objects"]}) == len(manifest["objects"]),
        "duplicate_expected_object",
    )
    F.secret_check(result)
    return result


def query_request(row):
    options = {
        **row["options"],
        "apply_formatting": False,
        "apply_vis": False,
        "rebuild_pdts": False,
    }
    suffix = urlencode(
        sorted(
            (k, str(v).lower() if type(v) is bool else v) for k, v in options.items()
        )
    )
    if row["query_id"] is not None:
        method, path, body = (
            "GET",
            API + "/queries/" + segment(row["query_id"]) + "/run/json_bi",
            None,
        )
    else:
        method, path, body = "POST", API + "/queries/run/json_bi", row["inline_query"]
    return {"method": method, "path": path + "?" + suffix, "body": body}


def dashboard(payload):
    if type(payload) is dict and payload.get("kind") == "looker_dashboard_export":
        need(
            payload.get("schema_version") == 1
            and re.fullmatch(r"4\.0(?:\.\d+)*", payload.get("api_version", "")),
            "dashboard_wrapper_rejected",
        )
        payload = payload.get("dashboard")
    need(
        type(payload) is dict and opaque(payload.get("id")),
        "dashboard_identity_required",
    )
    return payload


def references(kind, payload):
    found = set()

    def add(k, value):
        if value is not None:
            need(opaque(value), "dependency_identity_rejected")
            found.add((k, value))

    def query_ref(row):
        if type(row) is dict:
            add("query", row.get("query_id"))
            if type(row.get("query")) is dict:
                add("query", row["query"].get("id"))

    if kind == "dashboard":
        elements = payload.get("dashboard_elements", [])
        need(
            type(elements) is list
            and len(elements) <= 2000
            and all(type(e) is dict for e in elements),
            "dashboard_elements_rejected",
        )
        for row in elements:
            add("look", row.get("look_id"))
            add("merge_query", row.get("merge_result_id"))
            query_ref(row)
            look = row.get("look")
            if type(look) is dict:
                add("look", look.get("id"))
                query_ref(look)
            maker = row.get("result_maker")
            if type(maker) is dict:
                add("merge_query", maker.get("merge_result_id"))
                query_ref(maker)
    elif kind == "look":
        query_ref(payload)
    elif kind == "merge_query":
        rows = payload.get("source_queries", [])
        need(
            type(rows) is list
            and len(rows) <= 100
            and all(type(r) is dict for r in rows),
            "merge_sources_rejected",
        )
        for row in rows:
            add("query", row.get("query_id"))
    return sorted(found)


def fingerprints(source):
    pins = []
    if source.get("dashboard_file"):
        pins.append(
            {
                "kind": "dashboard",
                "id": dashboard(source["dashboard_export"])["id"],
                "sha256": source["dashboard_file"]["sha256"],
            }
        )
    pins.extend(
        {"kind": d["kind"], "id": d["id"], "sha256": d["file"]["sha256"]}
        for d in source["dependencies"]
    )
    pins.extend(
        {"kind": "supplied_file", "id": d["source_path"], "sha256": d["sha256"]}
        for d in source["supplied_files"]
    )
    return sha(sorted(pins, key=lambda p: (p["kind"], p["id"])))


def new_envelope(request, mode, now):
    return {
        "schema_version": ENVELOPE,
        "capture_id": request["capture_id"],
        "request": request,
        "request_sha256": sha(request),
        "created_at": now.isoformat(),
        "source": {
            "dashboard_export": None,
            "dashboard_export_sha256": None,
            "dashboard_file": None,
            "dependencies": [],
            "supplied_files": [],
            "state_observation": {"status": "unknown"},
            "identity": {
                "source_instance": request["source_instance"],
                "api_version": request["api_version"],
                "dashboard_id": request["dashboard_id"],
                "principal_ref": request["principal_ref"],
                "source_revision": request["source_revision"],
                "principal_verification": "supplied_unverified",
            },
        },
        "producer": {
            "name": "oaa-looker-capture",
            "mode": mode,
            "script_sha256": F.raw_sha(Path(__file__).read_bytes()),
            "file_validator_sha256": F.raw_sha(Path(F.__file__).read_bytes()),
            "documentation_reviewed": "2026-10-21",
        },
        "captures": [],
        "attachments": [],
        "operations": [],
        "jobs": {},
        "budget": {"requests": 0, "response_bytes": 0, "unmeasured_reserved_bytes": 0},
        "status": "partial",
        "gaps": list(BASE_GAPS),
        "evidence_mode": request["evidence_mode"],
        "journal_revision": 0,
        "previous_content_hash": None,
        "target_write_authority": False,
        "native_validation": "not_performed",
        "business_acceptance": "not_assessed",
    }


def save(root, state):
    state["previous_content_hash"] = state.pop("content_hash", None)
    state["journal_revision"] += 1
    state["gaps"] = list(dict.fromkeys(state["gaps"]))
    state["content_hash"] = sha(state)
    return (
        root
        / F.write_once(
            root,
            f"capture-{state['journal_revision']:06d}.json",
            encoded(state) + b"\n",
        )["path"]
    )


def set_identity(state):
    source, request = state["source"], state["request"]
    source["definition_fingerprint"] = fingerprints(source)
    source["identity"].update(
        identity_scope="service_dashboard"
        if request["source_instance"] and request["dashboard_id"]
        else "definition_only",
        namespace=(
            request["source_instance"]
            + "/dashboard/"
            + segment(request["dashboard_id"])
        )
        if request["source_instance"] and request["dashboard_id"]
        else "definition:" + source["definition_fingerprint"],
    )


def set_dashboard(root, state, raw, pin=None):
    need(len(raw) <= MAX_EMBEDDED_SOURCE_BYTES, "embedded_source_limit")
    payload = F.decode(raw)
    F.secret_check(payload)
    F.safe_text(raw)
    value = dashboard(payload)
    need(
        state["request"]["dashboard_id"] in (None, value["id"]),
        "dashboard_request_identity_mismatch",
    )
    state["source"].update(
        dashboard_export=payload,
        dashboard_export_sha256=sha(payload),
        dashboard_file=pin or F.write_once(root, "dashboard.json", raw),
    )
    for key in ("dashboard_elements", "dashboard_filters", "dashboard_layouts"):
        if key not in value:
            state["gaps"].append("dashboard_projection_missing:" + key)
    set_identity(state)


def file_pins(value):
    source = value["source"]
    result = list(value["attachments"]) + list(source["supplied_files"])
    if source.get("dashboard_file"):
        result.append(source["dashboard_file"])
    result.extend(d["file"] for d in source["dependencies"])
    result.extend(op["response"] for op in value["operations"] if op.get("response"))
    return result


def check_capture(path):
    path = F.no_links(path)
    value = F.decode(F.read_file(path, F.MAX_JSON))
    need(
        value.get("schema_version") == ENVELOPE
        and value.get("content_hash")
        == sha({k: v for k, v in value.items() if k != "content_hash"}),
        "capture_hash_changed",
    )
    need(
        value["request"] == validate_request(value["request"])
        and value["request_sha256"] == sha(value["request"]),
        "capture_request_changed",
    )
    need(
        value.get("target_write_authority") is False
        and value.get("native_validation") == "not_performed"
        and value.get("business_acceptance") == "not_assessed",
        "capture_authority_changed",
    )
    for pin in file_pins(value):
        raw = F.read_pin(path.parent, pin)
        if pin.get("content_utf8") is not None:
            need(raw == pin["content_utf8"].encode("utf-8"), "source_text_changed")
        if pin.get("format") == "png":
            F.png_info(raw)
    source = value["source"]
    if source.get("dashboard_file"):
        need(
            F.decode(F.read_pin(path.parent, source["dashboard_file"]))
            == source["dashboard_export"]
            and sha(source["dashboard_export"]) == source["dashboard_export_sha256"],
            "dashboard_payload_changed",
        )
    for dep in source["dependencies"]:
        need(
            F.decode(F.read_pin(path.parent, dep["file"])) == dep["payload"]
            and sha(dep["payload"]) == dep["payload_sha256"],
            "dependency_payload_changed",
        )
    if source.get("definition_fingerprint"):
        need(
            source["definition_fingerprint"] == fingerprints(source),
            "source_fingerprint_changed",
        )
    return value


def load_latest(root, request):
    paths = sorted(root.glob("capture-*.json"))
    need(paths and len(paths) <= 20000, "journal_required")
    previous = None
    for index, path in enumerate(paths, 1):
        value = F.decode(F.read_file(path, F.MAX_JSON))
        need(
            path.name == f"capture-{index:06d}.json"
            and value.get("journal_revision") == index
            and value.get("previous_content_hash") == previous
            and value.get("content_hash")
            == sha({k: v for k, v in value.items() if k != "content_hash"}),
            "journal_changed",
        )
        previous = value["content_hash"]
    value = check_capture(paths[-1])
    need(value["request"] == request, "capture_request_changed")
    need(
        value["producer"]["script_sha256"] == F.raw_sha(Path(__file__).read_bytes())
        and value["producer"]["file_validator_sha256"]
        == F.raw_sha(Path(F.__file__).read_bytes()),
        "capture_runtime_changed",
    )
    return value, paths[-1]


def import_api(request, payload_bytes, directory, *, allow_source_read=False):
    need(allow_source_read, "source_read_grant_required")
    request = validate_request(request)
    payload = F.decode(payload_bytes)
    F.secret_check(payload)
    F.safe_text(payload_bytes)
    value = dashboard(payload)
    need(
        request["dashboard_id"] in (None, value["id"]),
        "dashboard_request_identity_mismatch",
    )
    root = F.private_directory(directory)
    need(not list(root.iterdir()), "new_capture_directory_required")
    state = new_envelope(request, "supplied_api", utcnow())
    set_dashboard(root, state, payload_bytes)
    state["gaps"].append(
        "supplied_api_dependencies_renders_results_and_identity_not_authenticated"
    )
    output = save(root, state)
    return {"status": state["status"], "output": str(output), "capture": state}


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read, "source_read_grant_required")
    request = validate_request(request)
    source_root = F.no_links(source_root)
    destination = Path(directory).absolute()
    need(
        source_root.is_dir()
        and source_root != destination
        and source_root not in destination.parents,
        "source_directory_rejected",
    )
    files, prefixes, total, dashboards, embedded_bytes = [], {}, 0, [], 0
    for current, dirs, names in os.walk(source_root, followlinks=False):
        need(
            all(not (Path(current) / d).is_symlink() for d in dirs),
            "source_symlink_rejected",
        )
        for name in sorted(names):
            path = Path(current) / name
            relative = path.relative_to(source_root).as_posix()
            F.source_path(relative)
            parts = PurePosixPath(relative).parts
            for n in range(1, len(parts) + 1):
                prefix = "/".join(parts[:n])
                key = unicodedata.normalize("NFC", prefix).casefold()
                need(
                    key not in prefixes or prefixes[key] == prefix,
                    "source_path_collision",
                )
                prefixes[key] = prefix
            raw = F.read_file(path)
            total += len(raw)
            need(
                len(files) < F.MAX_FILES and total <= F.MAX_TOTAL,
                "supplied_inventory_limit",
            )
            suffix = path.suffix.lower()
            need(
                suffix
                in (
                    ".json",
                    ".lkml",
                    ".lookml",
                    ".dashboard",
                    ".yaml",
                    ".yml",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".pdf",
                ),
                "supplied_file_type_rejected",
            )
            content = None
            if suffix == ".png":
                F.png_info(raw)
            elif suffix in (".jpg", ".jpeg"):
                need(
                    raw.startswith(b"\xff\xd8") and raw.endswith(b"\xff\xd9"),
                    "jpeg_signature_rejected",
                )
            elif suffix == ".pdf":
                need(
                    raw.startswith(b"%PDF-") and b"%%EOF" in raw[-1024:],
                    "pdf_signature_rejected",
                )
            else:
                content = F.safe_text(raw)
                embedded_bytes += len(raw)
                need(
                    embedded_bytes <= MAX_EMBEDDED_SOURCE_BYTES, "embedded_source_limit"
                )
                if suffix == ".json":
                    payload = F.decode(raw)
                    F.secret_check(payload)
                    if type(payload) is dict and (
                        payload.get("kind") == "looker_dashboard_export"
                        or "dashboard_elements" in payload
                    ):
                        dashboard(payload)
                        dashboards.append(raw)
            files.append((relative, raw, content))
    need(files and len(dashboards) <= 1, "one_supplied_dashboard_or_lookml_required")
    if dashboards:
        need(
            request["dashboard_id"] in (None, dashboard(F.decode(dashboards[0]))["id"]),
            "dashboard_request_identity_mismatch",
        )
    root = F.private_directory(directory)
    need(not list(root.iterdir()), "new_capture_directory_required")
    state = new_envelope(request, "supplied_files", utcnow())
    for index, (name, raw, content) in enumerate(sorted(files), 1):
        pin = F.write_once(root, f"supplied-{index:04d}.bin", raw)
        state["source"]["supplied_files"].append(
            {**pin, "source_path": name, "content_utf8": content}
        )
    if dashboards:
        set_dashboard(root, state, dashboards[0])
    set_identity(state)
    state["gaps"].extend(
        [
            "supplied_files_not_authenticated_live_snapshot",
            "lookml_not_executed_or_compiled",
            "supplied_pdf_jpeg_are_unrendered_reference_bytes",
        ]
    )
    output = save(root, state)
    return {"status": state["status"], "output": str(output), "capture": state}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureError("source_redirect_refused")


def default_transport(method, url, token, body, maximum, timeout):
    need(
        timeout > 0
        and threading.current_thread() is threading.main_thread()
        and signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
        "deadline_context_rejected",
    )
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise TimeoutError("source_deadline")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": "token " + token,
                "Accept": "application/json, image/png",
                "Content-Type": "application/json",
            },
        )
        try:
            response = build_opener(ProxyHandler({}), NoRedirect()).open(
                request, timeout=timeout
            )
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read(maximum + 1)
            need(len(raw) <= maximum, "response_size_limit")
            headers = {
                k.lower(): v
                for k, v in response.headers.items()
                if k.lower()
                in (
                    "content-type",
                    "content-length",
                    "retry-after",
                    "etag",
                    "last-modified",
                    "location",
                )
            }
            if "content-length" in headers:
                need(
                    headers["content-length"].isdigit()
                    and int(headers["content-length"]) == len(raw),
                    "incomplete_transfer",
                )
            return response.status, headers, raw
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class StopCapture(Exception):
    pass


class Session:
    def __init__(self, root, state, token, transport, now):
        self.root, self.state, self.token, self.transport, self.now = (
            root,
            state,
            token,
            transport,
            now,
        )
        self.calls, self.started = 0, time.monotonic()

    def stop(self, code, blocked=False):
        self.state["status"] = "blocked" if blocked else "partial"
        self.state["gaps"].append(code)
        save(self.root, self.state)
        raise StopCapture(code)

    def call(self, key, method, path, payload=None, binary=False):
        state, request = self.state, self.state["request"]
        # Caller constructs only this operation allowlist; never use source URLs.
        base = path.split("?", 1)[0]
        allowed = method == "GET" and (
            base == API + "/user"
            or re.fullmatch(
                API + r"/(?:dashboards|looks|queries|merge_queries)/[^/]+", base
            )
            or re.fullmatch(API + r"/queries/[^/]+/run/json_bi", base)
            or re.fullmatch(API + r"/render_tasks/[^/]+(?:/results)?", base)
        )
        allowed = allowed or (
            method == "POST"
            and (
                base == API + "/queries/run/json_bi"
                or re.fullmatch(API + r"/render_tasks/dashboards/[^/]+/png", base)
            )
        )
        need(
            allowed and not urlsplit(path).netloc and not urlsplit(path).fragment,
            "operation_not_allowed",
        )
        url = request["source_instance"] + path
        need(
            urlsplit(url).netloc == urlsplit(request["source_instance"]).netloc,
            "fixed_origin_required",
        )
        body = None if payload is None else encoded(payload)
        identity = sha(
            {
                "method": method,
                "url": url,
                "body_sha256": F.raw_sha(body) if body is not None else None,
            }
        )
        matches = [o for o in state["operations"] if o["key"] == key]
        op = matches[0] if matches else None
        if op:
            need(op["operation_sha256"] == identity, "operation_request_changed")
            if op["status"] == "complete":
                return (
                    op["http_status"],
                    op["headers"],
                    F.read_pin(self.root, op["response"]),
                )
            if op["status"] in ("intent", "ambiguous", "failed"):
                self.stop("unresolved_operation_no_automatic_replay", True)
            if op.get("not_before") and self.now < datetime.fromisoformat(
                op["not_before"]
            ):
                self.stop("retry_after_not_elapsed")
            if op["attempts"] >= request["max_attempts_per_operation"]:
                self.stop("operation_attempt_limit", True)
        age = (
            (self.now - datetime.fromisoformat(state["created_at"])).total_seconds()
            + time.monotonic()
            - self.started
        )
        if age < 0 or age > request["max_elapsed_seconds"]:
            self.stop("capture_age_limit", True)
        if self.calls >= request["max_requests_per_invocation"]:
            self.stop("invocation_request_budget")
        if state["budget"]["requests"] >= request["max_total_requests"]:
            self.stop("total_request_budget", True)
        maximum = min(
            request["max_response_bytes"],
            request["max_total_bytes"]
            - state["budget"]["response_bytes"]
            - state["budget"]["unmeasured_reserved_bytes"],
        )
        if maximum <= 0:
            self.stop("total_byte_budget", True)
        need(
            type(self.token) is str
            and 8 <= len(self.token) <= 16384
            and re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", self.token),
            "injected_token_required",
        )
        if op is None:
            op = {
                "key": key,
                "method": method,
                "path": path,
                "operation_sha256": identity,
                "request_sha256": state["request_sha256"],
                "attempts": 0,
            }
            state["operations"].append(op)
        op.update(attempts=op["attempts"] + 1, status="intent")
        op.pop("not_before", None)
        state["budget"]["requests"] += 1
        self.calls += 1
        save(self.root, state)
        try:
            code, headers, raw = self.transport(
                method,
                url,
                self.token,
                body,
                maximum,
                min(30, request["max_elapsed_seconds"] - age),
            )
            need(
                type(code) is int
                and type(headers) is dict
                and type(raw) is bytes
                and len(raw) <= maximum,
                "transport_contract_rejected",
            )
            headers = {
                k.lower(): v
                for k, v in headers.items()
                if k.lower()
                in ("content-type", "retry-after", "etag", "last-modified", "location")
            }
            need(
                all(text(v, 4096) for v in headers.values()), "response_header_rejected"
            )
            need(
                self.token.encode() not in raw
                and all(self.token not in v for v in headers.values()),
                "response_contains_token",
            )
            need("location" not in headers, "source_location_not_followed")
            state["budget"]["response_bytes"] += len(raw)
            if code not in (200, 202):
                op.update(
                    status="retryable" if code == 429 else "failed",
                    http_status=code,
                    response_sha256=F.raw_sha(raw),
                    headers={k: v for k, v in headers.items() if k == "retry-after"},
                )
                if code == 429:
                    delay = headers.get("retry-after", "")
                    need(
                        delay.isdigit() and int(delay) <= 86400, "retry_after_required"
                    )
                    op["not_before"] = (
                        self.now + timedelta(seconds=int(delay))
                    ).isoformat()
                self.stop(
                    "source_throttled" if code == 429 else "source_http_rejected",
                    code != 429,
                )
            need(
                code == 200 or (binary and base.endswith("/results") and not raw),
                "unexpected_accepted_response",
            )
            if code == 200:
                if binary:
                    need(
                        headers.get("content-type", "").split(";")[0].strip().lower()
                        == "image/png",
                        "render_media_rejected",
                    )
                    F.png_info(raw)
                else:
                    need(
                        headers.get("content-type", "").split(";")[0].strip().lower()
                        == "application/json",
                        "json_media_rejected",
                    )
                    value = F.decode(raw)
                    F.secret_check(value)
                    F.safe_text(raw)
                    need(
                        self.token.encode() not in encoded(value),
                        "decoded_response_contains_token",
                    )
            pin = F.write_once(
                self.root,
                f"response-{len(state['operations']):05d}-{op['attempts']:02d}.bin",
                raw,
            )
            op.update(
                status="complete", http_status=code, headers=headers, response=pin
            )
            save(self.root, state)
            return code, headers, raw
        except StopCapture:
            raise
        except Exception:
            op["status"] = "ambiguous"
            state["budget"]["unmeasured_reserved_bytes"] += maximum
            self.stop("source_response_unresolved_no_automatic_replay", True)

    def json_call(self, *args, **kwargs):
        code, headers, raw = self.call(*args, **kwargs)
        return code, headers, F.decode(raw)

    def response_pin(self, key):
        return next(o["response"] for o in self.state["operations"] if o["key"] == key)

    def snapshot(self, label):
        request, state = self.state["request"], self.state
        key = label + ".dashboard"
        _, _, raw = self.call(
            key, "GET", API + "/dashboards/" + segment(request["dashboard_id"])
        )
        payload = F.decode(raw)
        value = dashboard(payload)
        need(
            value["id"] == request["dashboard_id"], "source_dashboard_identity_mismatch"
        )
        if label == "before" and state["source"]["dashboard_export"] is None:
            set_dashboard(self.root, state, raw, self.response_pin(key))
            save(self.root, state)
        queue, visited, deps = references("dashboard", value), set(), []
        while queue:
            kind, identity = queue.pop(0)
            if (kind, identity) in visited:
                continue
            visited.add((kind, identity))
            need(len(visited) <= request["max_dependencies"], "dependency_count_limit")
            key = label + ".dependency." + sha([kind, identity])[:24]
            plural = {
                "look": "looks",
                "query": "queries",
                "merge_query": "merge_queries",
            }[kind]
            _, _, dep_raw = self.call(
                key, "GET", API + "/" + plural + "/" + segment(identity)
            )
            data = F.decode(dep_raw)
            need(
                type(data) is dict and data.get("id") == identity,
                "dependency_response_identity_mismatch",
            )
            dep = {
                "kind": kind,
                "id": identity,
                "payload": data,
                "payload_sha256": sha(data),
                "file": self.response_pin(key),
            }
            need(
                len(raw) + sum(d["file"]["bytes"] for d in deps) + len(dep_raw)
                <= MAX_EMBEDDED_SOURCE_BYTES,
                "embedded_source_limit",
            )
            deps.append(dep)
            queue.extend(references(kind, data))
            if label == "before":
                state["source"]["dependencies"] = deps
                set_identity(state)
                save(self.root, state)
        snapshot = {
            "dashboard_sha256": F.raw_sha(raw),
            "dependencies": sorted(
                [
                    {"kind": d["kind"], "id": d["id"], "sha256": d["file"]["sha256"]}
                    for d in deps
                ],
                key=lambda d: (d["kind"], d["id"]),
            ),
        }
        state["source"]["metadata_" + label] = snapshot
        save(self.root, state)
        return value, deps, snapshot

    def render(self, row):
        state, request = self.state, self.state["request"]
        key = "render." + row["render_id"]
        if any(a.get("render_id") == row["render_id"] for a in state["attachments"]):
            return
        body = {
            "dashboard_filters": urlencode(request["state"]["filters"]),
            "dashboard_style": row["dashboard_style"],
            "tab_ids": row["tab_ids"],
        }
        options = {"width": row["width"], "height": row["height"]}
        if row["theme"] is not None:
            options["theme"] = row["theme"]
        if key not in state["jobs"]:
            _, _, value = self.json_call(
                key + ".submit",
                "POST",
                API
                + "/render_tasks/dashboards/"
                + segment(request["dashboard_id"])
                + "/png?"
                + urlencode(options),
                body,
            )
            need(
                type(value) is dict and opaque(value.get("id")),
                "render_task_identity_required",
            )
            state["jobs"][key] = {
                "id": value["id"],
                "polls": 0,
                "downloads": 0,
                "submission": value,
            }
            save(self.root, state)
        job = state["jobs"][key]
        if job.get("not_before") and self.now < datetime.fromisoformat(
            job["not_before"]
        ):
            self.stop("render_retry_after_not_elapsed")
        if not job.get("ready"):
            need(
                job["polls"] < request["max_attempts_per_operation"],
                "render_poll_limit",
            )
            # This counter is persisted only after call completion. A crash retries a cached receipt, never a new task.
            _, _, value = self.json_call(
                key + f".poll.{job['polls']}",
                "GET",
                API + "/render_tasks/" + segment(job["id"]),
            )
            need(
                type(value) is dict and value.get("id") == job["id"],
                "render_task_identity_mismatch",
            )
            for field, expected in (
                ("dashboard_id", request["dashboard_id"]),
                ("result_format", "png"),
                ("user_id", state["source"]["identity"]["observed_user_id"]),
            ):
                if value.get(field) is not None:
                    need(value[field] == expected, "render_task_scope_mismatch")
            if value.get("lookml_dashboard_id") is not None:
                need(
                    value["lookml_dashboard_id"] == request["dashboard_id"],
                    "render_task_scope_mismatch",
                )
            status = value.get("status")
            job.update(polls=job["polls"] + 1, last_status=value)
            save(self.root, state)
            if status in (
                "enqueued_for_query",
                "querying",
                "enqueued_for_render",
                "rendering",
            ):
                self.stop("render_pending")
            need(status == "success", "render_failed_or_unknown_status")
            job["ready"] = True
            save(self.root, state)
        need(
            job["downloads"] < request["max_attempts_per_operation"],
            "render_download_limit",
        )
        code, headers, raw = self.call(
            key + f".file.{job['downloads']}",
            "GET",
            API + "/render_tasks/" + segment(job["id"]) + "/results",
            binary=True,
        )
        job["downloads"] += 1
        if code == 202:
            delay = headers.get("retry-after", "")
            need(delay.isdigit() and int(delay) <= 86400, "render_retry_after_required")
            job["not_before"] = (self.now + timedelta(seconds=int(delay))).isoformat()
            self.stop("render_result_pending")
        pin = F.write_once(self.root, row["render_id"] + ".png", raw)
        record = {
            **pin,
            "format": "png",
            "media_type": "image/png",
            "render_id": row["render_id"],
            "render_task_id": job["id"],
            "dashboard_id": request["dashboard_id"],
            "tab_ids": row["tab_ids"],
            "request_sha256": state["request_sha256"],
            "state_sha256": sha(request["state"]),
            "render_request_sha256": sha({"body": body, "options": options}),
        }
        state["attachments"].append(record)
        state["captures"].append(
            {
                "kind": "render",
                "render_id": row["render_id"],
                "state_sha256": record["state_sha256"],
                "status": "complete",
                "attachments": [pin["path"]],
                "gaps": ["dashboard_or_tab_image_not_individual_tile_render"],
            }
        )
        save(self.root, state)


def query_quality(value, limit):
    need(type(value) is dict, "json_bi_object_required")
    flags = []
    stack = [value]
    count = 0
    while stack:
        item = stack.pop()
        count += 1
        need(count <= 200000, "result_structure_limit")
        if type(item) is dict:
            for key in (
                "error",
                "errors",
                "truncated",
                "limit_reached",
                "data_truncated",
                "columns_truncated",
            ):
                if item.get(key):
                    flags.append(key)
            stack.extend(v for v in item.values() if type(v) in (dict, list))
        elif type(item) is list:
            stack.extend(v for v in item if type(v) in (dict, list))
    rows = value.get("rows", value.get("data"))
    if type(rows) is list and len(rows) >= limit:
        flags.append("requested_row_limit_reached")
    return {
        "status": "partial" if flags else "unknown",
        "reference": None,
        "flags": sorted(set(flags)),
        "reason": "query_endpoint_does_not_establish_complete_dashboard_population",
    }


def validate_scope(request, dash, deps):
    elements = dash.get("dashboard_elements")
    need(type(elements) is list, "execution_requires_element_inventory")
    indexed = {}
    for item in elements:
        need(
            type(item) is dict and opaque(item.get("id")) and item["id"] not in indexed,
            "element_identity_ambiguous",
        )
        indexed[item["id"]] = item
    for view in request["views"]:
        need(
            view["element_id"] is None or view["element_id"] in indexed,
            "selected_element_missing",
        )
        if view["layout_id"] is not None:
            need(
                any(
                    type(layout) is dict and layout.get("id") == view["layout_id"]
                    for layout in dash.get("dashboard_layouts", [])
                ),
                "selected_layout_missing",
            )
    # Only check tab IDs against a supplied inventory; older dashboard responses
    # omit it. Requested render tab IDs remain unverified in that case.
    if type(dash.get("tabs")) is list:
        tab_ids = {tab.get("id") for tab in dash["tabs"] if type(tab) is dict}
        need(
            all(
                view["tab_id"] is None or view["tab_id"] in tab_ids
                for view in request["views"]
            )
            and all(
                tab in tab_ids
                for render in request["renders"]
                for tab in render["tab_ids"]
            ),
            "selected_tab_missing",
        )
    dep_index = {(d["kind"], d["id"]): d["payload"] for d in deps}
    for query in request["queries"]:
        element = indexed.get(query["element_id"])
        need(element is not None, "query_element_missing")
        queue, seen = references("dashboard", {"dashboard_elements": [element]}), set()
        while queue:
            key = queue.pop(0)
            if key not in seen:
                seen.add(key)
                if key in dep_index:
                    queue.extend(references(key[0], dep_index[key]))
        if query["query_id"] is not None:
            need(
                ("query", query["query_id"]) in seen,
                "query_not_source_element_dependency",
            )
        if query["source_query_id"] is not None:
            need(
                ("query", query["source_query_id"]) in seen,
                "inline_baseline_not_element_dependency",
            )


def capture(
    request,
    directory,
    *,
    token=None,
    transport=None,
    resume=False,
    allow_source_read=False,
    allow_source_query=False,
    now=None,
):
    need(allow_source_read, "source_read_grant_required")
    request = validate_request(request, require_service=True)
    need(
        not (request["queries"] or request["renders"]) or allow_source_query,
        "source_query_grant_required_for_queries_or_renders",
    )
    root = F.private_directory(directory)
    lock = F.no_links(root / ".capture.lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = now or utcnow()
        if resume:
            state, output = load_latest(root, request)
            if state["status"] in ("complete", "blocked"):
                return {
                    "status": state["status"],
                    "output": str(output),
                    "capture": state,
                }
        else:
            need(
                set(p.name for p in root.iterdir()) == {".capture.lock"},
                "new_capture_directory_required",
            )
            state = new_envelope(request, "rest", now)
            output = save(root, state)
        session = Session(root, state, token, transport or default_transport, now)
        try:
            _, _, user = session.json_call(
                "principal." + str(state["journal_revision"]),
                "GET",
                API + "/user?fields=id",
            )
            need(
                type(user) is dict and set(user) == {"id"} and opaque(user["id"]),
                "current_user_projection_rejected",
            )
            identity = state["source"]["identity"]
            need(
                request["expected_user_id"] in (None, user["id"])
                and identity.get("observed_user_id") in (None, user["id"]),
                "source_principal_changed",
            )
            identity.update(
                observed_user_id=user["id"],
                principal_verification="api_current_user_observed_not_effective_access",
            )
            save(root, state)
            dash, deps, before = session.snapshot("before")
            validate_scope(request, dash, deps)
            if (
                any(render["tab_ids"] for render in request["renders"])
                and type(dash.get("tabs")) is not list
            ):
                state["gaps"].append(
                    "render_tab_identity_not_in_received_dashboard_inventory"
                )
            for render in request["renders"]:
                session.render(render)
            for query in request["queries"]:
                if any(
                    a.get("binding_id") == query["binding_id"]
                    for a in state["attachments"]
                ):
                    continue
                spec = query_request(query)
                _, _, raw = session.call(
                    "query." + query["binding_id"],
                    spec["method"],
                    spec["path"],
                    spec["body"],
                )
                quality = query_quality(F.decode(raw), query["options"]["limit"])
                original = next(
                    (
                        d["payload"]
                        for d in deps
                        if d["kind"] == "query" and d["id"] == query["source_query_id"]
                    ),
                    None,
                )
                effective = (
                    query["inline_query"]
                    if query["inline_query"] is not None
                    else next(
                        d["payload"]
                        for d in deps
                        if d["kind"] == "query" and d["id"] == query["query_id"]
                    )
                )
                need(
                    len(encoded(effective))
                    + sum(
                        len(encoded(a.get("effective_query")))
                        for a in state["attachments"]
                        if a.get("effective_query") is not None
                    )
                    <= MAX_EMBEDDED_SOURCE_BYTES,
                    "embedded_query_limit",
                )
                pin = F.write_once(root, "query-" + query["binding_id"] + ".json", raw)
                record = {
                    **pin,
                    "format": "json_bi",
                    "media_type": "application/json",
                    "binding_id": query["binding_id"],
                    "element_id": query["element_id"],
                    "query_id": query["query_id"],
                    "dashboard_id": request["dashboard_id"],
                    "request_sha256": state["request_sha256"],
                    "state_sha256": sha(request["state"]),
                    "query_fingerprint": sha(spec),
                    "effective_query": copy.deepcopy(effective),
                    "effective_query_sha256": sha(effective),
                    "source_query_id": query["source_query_id"],
                    "source_query_sha256": sha(original)
                    if original is not None
                    else None,
                    "reviewed_binding_reference": query["context_reference"],
                    "query_differences": {
                        k: {"original": original.get(k), "effective": v}
                        for k, v in effective.items()
                        if original is not None and original.get(k) != v
                    },
                    "result_completeness": quality,
                    "rendered_state_equivalence": "not_established",
                }
                state["attachments"].append(record)
                state["captures"].append(
                    {
                        "kind": "query",
                        "binding_id": query["binding_id"],
                        "element_id": query["element_id"],
                        "state_sha256": record["state_sha256"],
                        "status": "partial"
                        if quality["status"] == "partial"
                        else "complete",
                        "attachments": [pin["path"]],
                        "gaps": quality["flags"],
                    }
                )
                save(root, state)
            _, _, after = session.snapshot("after")
            need(before == after, "source_configuration_changed")
            state["source"]["coherence"] = {
                "configuration": "unchanged_response_bracket",
                "data_snapshot": "not_established",
            }
            state["status"] = (
                "partial"
                if any(c["status"] != "complete" for c in state["captures"])
                or any(
                    g.startswith("dashboard_projection_missing:") for g in state["gaps"]
                )
                else "complete"
            )
            state["completion_meaning"] = (
                "requested acquisition and configuration bracket only; not applied state, completeness, effective access or parity"
            )
            output = save(root, state)
        except StopCapture:
            output = sorted(root.glob("capture-*.json"))[-1]
        except (ValueError, KeyError, TypeError, OSError, IndexError):
            state["status"] = "blocked"
            state["gaps"].append("source_contract_or_coherence_rejected")
            output = save(root, state)
        return {"status": state["status"], "output": str(output), "capture": state}
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "import-local", "import-api"):
        command = sub.add_parser(name)
        command.add_argument("--request", required=True, type=Path)
        command.add_argument("--directory", required=True, type=Path)
        command.add_argument("--allow-source-read", action="store_true")
        if name == "capture":
            command.add_argument("--allow-source-query", action="store_true")
            command.add_argument("--token-stdin", action="store_true")
            command.add_argument("--resume", action="store_true")
        elif name == "import-local":
            command.add_argument("--source-root", required=True, type=Path)
        else:
            command.add_argument("--response", required=True, type=Path)
    check = sub.add_parser("check")
    check.add_argument("--capture", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            value = check_capture(args.capture)
            result = {
                "status": value["status"],
                "output": str(F.no_links(args.capture)),
            }
        else:
            request = F.decode(F.read_file(args.request))
            if args.command == "capture":
                need(args.token_stdin, "injected_token_stdin_required")
                raw = sys.stdin.buffer.read(16385)
                need(len(raw) <= 16384, "token_input_limit")
                result = capture(
                    request,
                    args.directory,
                    token=raw.decode("ascii"),
                    resume=args.resume,
                    allow_source_read=args.allow_source_read,
                    allow_source_query=args.allow_source_query,
                )
            elif args.command == "import-local":
                result = import_local(
                    request,
                    args.source_root,
                    args.directory,
                    allow_source_read=args.allow_source_read,
                )
            else:
                result = import_api(
                    request,
                    F.read_file(args.response),
                    args.directory,
                    allow_source_read=args.allow_source_read,
                )
        print(encoded({k: result[k] for k in ("status", "output")}).decode())
        return 0
    except (ValueError, OSError, TypeError, KeyError):
        print(
            "Looker capture rejected; source boundary, grant, file or contract failed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
