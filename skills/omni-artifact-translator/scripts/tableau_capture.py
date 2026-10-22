#!/usr/bin/env python3
"""Bounded Tableau source capture and official-MCP response intake; no target client.

REST uses only fixed GET routes and an injected, already-authorized source session.
No sign-in, credential discovery, arbitrary URL fetch or customer-code execution.
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import fcntl
import importlib.util
import io
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

_spec = importlib.util.spec_from_file_location("oaa_tableau_capture_files", Path(__file__).with_name("tableau_capture_files.py"))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
CaptureError, need, sha, encoded = F.CaptureError, F.need, F.sha, F.encoded
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
REQUEST = "tableau-visual-capture-request.v1"
ENVELOPE = "tableau-visual-capture.v1"
SOURCES = [
    "https://help.tableau.com/current/api/rest_api/en-us/REST/rest_api_ref_server.htm",
    "https://help.tableau.com/current/api/rest_api/en-us/REST/rest_api_ref_workbooks_and_views.htm",
    "https://tableau.github.io/tableau-mcp/docs/tools/views/get-view-data",
    "https://tableau.github.io/tableau-mcp/docs/tools/views/get-view-image",
    "https://tableau.github.io/tableau-mcp/docs/tools/workbooks/download-workbook",
]
BASE_GAPS = ["configuration_bracket_is_not_atomic_data_snapshot", "result_completeness_not_established",
             "locale_timezone_parameter_and_action_behavior_not_verified", "effective_access_and_business_acceptance_not_tested",
             "permission_filtered_view_listing_not_full_site_inventory", "semantic_inventory_not_attached"]


def utcnow():
    return datetime.now(timezone.utc)


def validate_request(value):
    need(type(value) is dict and value.get("schema_version") == REQUEST, "request_contract_required")
    required = {"schema_version", "capture_id", "origin", "api_version", "site_id", "expected_user_id",
                "workbook_id", "dashboard_view_id", "dashboard_id", "principal_ref", "authorization_ref",
                "evidence_mode", "views", "state", "expected_manifest", "identity_map"}
    defaults = {"max_requests_per_invocation": 100, "max_total_requests": 500, "max_total_bytes": 64_000_000,
                "max_elapsed_seconds": 3600, "max_attempts_per_operation": 3,
                "max_response_bytes": F.MAX_FILE, "image_options": {}, "definition_sha256": None}
    need(required <= set(value) and not set(value) - required - set(defaults), "request_fields_rejected")
    result = {**defaults, **copy.deepcopy(value)}
    for key in ("capture_id", "site_id", "expected_user_id", "workbook_id", "dashboard_view_id"):
        need(type(result[key]) is str and ID.fullmatch(result[key]), "request_identity_rejected")
    parsed = urlsplit(result["origin"])
    need(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
         and not parsed.path and not parsed.query and not parsed.fragment and parsed.port in (None, 443), "approved_https_origin_required")
    need(type(result["api_version"]) is str and re.fullmatch(r"3\.(?:[1-9]|[12][0-9]|30)", result["api_version"]), "api_version_unsupported")
    need(result["evidence_mode"] in ("synthetic_fixture", "live_tenant", "manual_transfer"), "evidence_mode_required")
    for key in ("principal_ref", "authorization_ref"):
        need(type(result[key]) is str and 0 < len(result[key]) <= 1000, "source_authorization_reference_required")
    limits = {"max_requests_per_invocation": (5, 500), "max_total_requests": (1, 5000),
              "max_total_bytes": (1, 512_000_000), "max_elapsed_seconds": (1, 21600),
              "max_attempts_per_operation": (1, 10), "max_response_bytes": (1, F.MAX_FILE)}
    for key, (low, high) in limits.items():
        need(type(result[key]) is int and low <= result[key] <= high, "request_budget_rejected")
    state = result["state"]
    need(type(state) is dict and set(state) == {"state_id", "filters", "parameters", "locale", "timezone", "data_time_policy"}, "state_contract_required")
    need(type(state["state_id"]) is str and state["state_id"] and type(state["data_time_policy"]) is str
         and state["data_time_policy"], "state_reference_required")
    for key in ("filters", "parameters"):
        need(type(state[key]) is dict and len(state[key]) <= 100 and all(
            type(k) is str and 0 < len(k) <= 256 and not k.startswith("vf_") and type(v) is str and len(v) <= 2000
            for k, v in state[key].items()), "state_values_rejected")
    for key in ("locale", "timezone"):
        need(state[key] is None or (type(state[key]) is str and 0 < len(state[key]) <= 256), "state_locale_rejected")
    need(type(result["views"]) is list and 1 <= len(result["views"]) <= 100, "view_scope_limit")
    seen = set()
    for view in result["views"]:
        need(type(view) is dict and set(view) == {"view_id", "role", "worksheet_id"}, "view_contract_required")
        need(type(view["view_id"]) is str and ID.fullmatch(view["view_id"]) and view["view_id"] not in seen, "view_identity_rejected")
        seen.add(view["view_id"])
        need(view["role"] in ("dashboard", "worksheet") and (view["worksheet_id"] is None or
             type(view["worksheet_id"]) is str and view["worksheet_id"].startswith("/workbook[1]/")), "view_mapping_rejected")
    need([v["view_id"] for v in result["views"] if v["role"] == "dashboard"] == [result["dashboard_view_id"]], "one_dashboard_required")
    need(result["dashboard_id"] is None or type(result["dashboard_id"]) is str and result["dashboard_id"].startswith("/workbook[1]/"), "dashboard_mapping_rejected")
    manifest = result["expected_manifest"]
    need(type(manifest) is dict and manifest.get("schema_version") == 1 and manifest.get("reference")
         and manifest.get("completeness") in ("selected_dashboard", "partial") and type(manifest.get("objects")) is list,
         "expected_manifest_required")
    need(len(manifest["objects"]) <= 5000 and all(type(o) is dict and type(o.get("object_id")) is str and type(o.get("kind")) is str for o in manifest["objects"]), "expected_manifest_rejected")
    need(len({o["object_id"] for o in manifest["objects"]}) == len(manifest["objects"]), "duplicate_expected_object")
    crosswalk = result["identity_map"]
    need(type(crosswalk) is dict and crosswalk.get("schema_version") == 1 and type(crosswalk.get("mappings")) is list, "identity_map_required")
    need(len(crosswalk["mappings"]) <= 100 and all(type(m) is dict for m in crosswalk["mappings"])
         and len({m.get("view_id") for m in crosswalk["mappings"]}) == len(crosswalk["mappings"]), "identity_map_rejected")
    for mapping in crosswalk["mappings"]:
        need(mapping.get("view_id") in seen and mapping.get("status") in ("matched", "unresolved"), "identity_map_scope")
        if mapping["status"] == "matched":
            need(type(mapping.get("object_id")) is str and mapping["object_id"].startswith("/workbook[1]/")
                 and mapping.get("evidence_reference"), "identity_mapping_evidence_required")
    options = result["image_options"]
    need(type(options) is dict and not set(options) - {"width", "height", "max_age_minutes"}, "image_options_rejected")
    need(("width" in options) == ("height" in options), "paired_image_dimensions_required")
    for key, number in options.items():
        need(type(number) is int and 1 <= number <= (8192 if key != "max_age_minutes" else 1440), "image_option_limit")
    if "width" in options:
        need(int(result["api_version"].split(".")[1]) >= 23, "image_dimensions_require_3_23")
    need(result["definition_sha256"] is None or type(result["definition_sha256"]) is str and HASH.fullmatch(result["definition_sha256"]), "definition_pin_rejected")
    need(len(encoded(result)) <= F.MAX_XML, "request_size_limit")
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureError("source_redirect_refused")


def default_transport(url, token, maximum, timeout):
    need(timeout > 0 and threading.current_thread() is threading.main_thread(), "source_deadline_main_thread_required")
    need(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), "existing_deadline_context_unsupported")
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise TimeoutError("source_request_deadline")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return _http_get(url, token, maximum, timeout)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _http_get(url, token, maximum, timeout):
    request = Request(url, headers={"X-Tableau-Auth": token, "Accept": "application/json"}, method="GET")
    try:
        response = build_opener(NoRedirect()).open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read(maximum + 1)
        need(len(raw) <= maximum, "source_response_size_limit")
        headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in
                   ("content-type", "content-length", "retry-after", "etag", "last-modified")}
        if "content-length" in headers:
            need(headers["content-length"].isdigit() and int(headers["content-length"]) == len(raw), "source_incomplete_transfer")
        return response.status, headers, raw


def new_envelope(request, method, now):
    return {"schema_version": ENVELOPE, "capture_id": request["capture_id"], "request": request,
            "request_sha256": sha(request), "created_at": now.isoformat(), "source": {},
            "producer": {"name": "oaa-tableau-capture", "method": method, "schema_reviewed": "2026-10-21",
                         "script_sha256": F.raw_sha(Path(__file__).read_bytes()), "file_validator_sha256": F.raw_sha(Path(F.__file__).read_bytes()),
                         "sources": SOURCES},
            "captures": [{**view, "state_sha256": sha(request["state"]), "status": "partial", "attachments": [], "gaps": []}
                         for view in request["views"]], "attachments": [], "operations": [],
            "budget": {"requests": 0, "response_bytes": 0, "unmeasured_reserved_bytes": 0}, "status": "partial", "gaps": list(BASE_GAPS),
            "evidence_mode": request["evidence_mode"], "journal_revision": 0, "previous_content_hash": None,
            "target_write_authority": False, "native_validation": "not_performed", "business_acceptance": "not_assessed"}


def save(root, state):
    state["previous_content_hash"] = state.pop("content_hash", None)
    state["journal_revision"] += 1
    state["gaps"] = list(dict.fromkeys(state["gaps"]))
    state["content_hash"] = sha(state)
    pin = F.write_once(root, f"capture-{state['journal_revision']:06d}.json", encoded(state) + b"\n")
    return root / pin["path"]


def load_latest(root, request):
    files = sorted(root.glob("capture-*.json"))
    need(files and len(files) <= 20000, "capture_journal_required")
    previous = None
    for index, path in enumerate(files, 1):
        need(path.name == f"capture-{index:06d}.json", "capture_journal_sequence")
        value = F.decode(F.no_links(path).read_bytes())
        need(value.get("content_hash") == sha({k: v for k, v in value.items() if k != "content_hash"})
             and value.get("previous_content_hash") == previous and value.get("journal_revision") == index, "capture_journal_changed")
        previous = value["content_hash"]
    need(value["schema_version"] == ENVELOPE and value["request"] == request and value["request_sha256"] == sha(request), "capture_request_changed")
    need(value.get("producer", {}).get("script_sha256") == F.raw_sha(Path(__file__).read_bytes())
         and value.get("producer", {}).get("file_validator_sha256") == F.raw_sha(Path(F.__file__).read_bytes()), "capture_runtime_changed")
    for pin in value["attachments"]:
        raw = F.read_pin(root, pin)
        if pin["format"] == "png":
            F.png_info(raw)
        elif pin["format"] == "csv":
            F.csv_info(raw)
    for key in ("definition", "original_definition"):
        if key in value["source"]:
            F.read_pin(root, value["source"][key])
    for operation in value["operations"]:
        if operation.get("response"):
            F.read_pin(root, operation["response"])
    return value, files[-1]


def add_attachment(root, state, raw, name, fmt, media, view=None, **extra):
    if fmt == "png":
        extra["actual_dimensions"] = F.png_info(raw)
    if fmt == "csv":
        extra.update(F.csv_info(raw))
    pin = F.write_once(root, name, raw)
    entry = {**pin, "format": fmt, "media_type": media, "view_id": view["view_id"] if view else None,
             "worksheet_id": view.get("worksheet_id") if view else None,
             "state_sha256": sha(state["request"]["state"]), "request_sha256": state["request_sha256"], **extra}
    state["attachments"].append(entry)
    if view is not None:
        view["attachments"].append(name)
    return entry


def set_definition(root, state, raw, name="definition"):
    parsed = F.definition(raw)
    if state["request"]["definition_sha256"]:
        need(F.raw_sha(parsed["xml"]) == state["request"]["definition_sha256"], "definition_fingerprint_mismatch")
    if parsed["format"] == "twbx":
        original = add_attachment(root, state, raw, name + ".twbx", "twbx", "application/octet-stream")
        state["source"]["original_definition"] = {k: original[k] for k in ("path", "sha256", "bytes")}
    pin = add_attachment(root, state, parsed["xml"], name + ".twb", "twb", "application/xml")
    state["source"]["definition"] = {**{k: pin[k] for k in ("path", "sha256", "bytes")}, "content_utf8": parsed["xml"].decode("utf-8")}
    state["source"]["definition_fingerprint"] = parsed["fingerprint"]
    state["source"]["package_members"] = parsed["members"]
    return parsed


def _rows(value):
    if type(value) is dict:
        value = [value]
    need(type(value) is list and all(type(row) is dict for row in value), "source_listing_shape")
    return value


def _session(raw, request):
    value = F.decode(raw)
    need(type(value) is dict, "source_session_shape")
    session = value.get("session", {})
    need(type(session) is dict and type(session.get("site")) is dict and type(session.get("user")) is dict, "source_session_shape")
    need(session.get("site", {}).get("id") == request["site_id"] and session.get("user", {}).get("id") == request["expected_user_id"], "session_identity_mismatch")
    # Preserve an exact hash, but persist only documented non-secret identity fields.
    return {"site_id": session["site"]["id"], "user_id": session["user"]["id"], "response_sha256": F.raw_sha(raw),
            "verification": "source_session_observed"}


def _metadata(workbook_raw, views_raw, request):
    workbook, views = F.decode(workbook_raw), F.decode(views_raw)
    need(type(workbook) is dict and type(workbook.get("workbook")) is dict
         and type(views) is dict and type(views.get("views")) is dict, "source_metadata_shape")
    need(workbook.get("workbook", {}).get("id") == request["workbook_id"], "source_workbook_mismatch")
    listed = _rows(views.get("views", {}).get("view", []))
    ids = [v.get("id") for v in listed]
    need(all(type(x) is str and ID.fullmatch(x) for x in ids) and len(ids) == len(set(ids)), "source_view_identity_ambiguous")
    need(all(v["view_id"] in ids for v in request["views"]), "selected_view_missing_or_denied")
    if "pagination" in views:
        p = views["pagination"]
        need(int(p.get("totalAvailable", -1)) == len(listed) and int(p.get("pageNumber", 1)) == 1, "partial_view_listing")
    return {"workbook": workbook, "views": views}


def _secret_free_json(value):
    if type(value) is dict:
        for key, item in value.items():
            need(not F.secret_name(key) or not item, "credential_bearing_response_rejected")
            _secret_free_json(item)
    elif type(value) is list:
        for item in value:
            _secret_free_json(item)


def _retry_after(headers, instant):
    raw = headers.get("retry-after", "")
    try:
        when = instant + timedelta(seconds=int(raw)) if raw.isdigit() else parsedate_to_datetime(raw)
        need(when.tzinfo is not None, "retry_after_timezone")
        seconds = (when - instant).total_seconds()
        if 0 <= seconds <= 3600:
            return when.isoformat()
    except (ValueError, TypeError, OverflowError):
        pass
    return None


class Pending(Exception):
    pass


def capture_rest(value, *, directory, session_token, transport=None, resume=False,
                 allow_source_read=False, allow_source_query=False, now=None):
    """One explicit source invocation. No retries in a request; resume is bounded."""
    request = validate_request(value)
    need(allow_source_read is True and allow_source_query is True, "source_authorization_flags_required")
    need(type(session_token) is str and 0 < len(session_token) <= 8192 and session_token.isascii()
         and not any(c.isspace() or ord(c) < 32 for c in session_token), "source_session_token_required")
    root = F.private_directory(directory)
    transport = transport or default_transport
    instant = now() if now else utcnow()
    clock_start, invocation_requests = time.monotonic(), 0
    with os.fdopen(os.open(root / ".capture.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if resume:
            state, path = load_latest(root, request)
            if state["status"] in ("complete", "blocked"):
                return {"status": state["status"], "output": str(path), "capture": state}
        else:
            need(not list(root.glob("capture-*.json")), "capture_exists_use_resume")
            state = new_envelope(request, "rest", instant)
            path = save(root, state)
        prefix = f"/api/{request['api_version']}"
        site = prefix + f"/sites/{request['site_id']}"

        def get(key, route, reusable=True):
            nonlocal path, invocation_requests
            operation = next((x for x in state["operations"] if x["key"] == key), None)
            if operation is not None and operation["status"] == "complete" and reusable:
                return F.read_pin(root, operation["response"]), operation["headers"]
            if operation is None:
                operation = {"key": key, "ordinal": len(state["operations"]) + 1,
                             "method": "GET", "route": route, "status": "planned", "attempts": 0}
                state["operations"].append(operation)
            need(operation["route"] == route, "operation_scope_changed")
            if operation["status"] in ("in_flight", "outcome_unknown"):
                state["gaps"].append("uncertain_source_export_requires_external_reconciliation")
                raise Pending()
            if operation.get("retry_not_before") and instant < datetime.fromisoformat(operation["retry_not_before"]):
                raise Pending()
            age = (instant - datetime.fromisoformat(state["created_at"])).total_seconds()
            need(0 <= age <= request["max_elapsed_seconds"], "capture_age_limit")
            need(age + time.monotonic() - clock_start < request["max_elapsed_seconds"], "capture_elapsed_limit")
            if invocation_requests >= request["max_requests_per_invocation"]:
                state["gaps"].append("invocation_request_budget_reached")
                raise Pending()
            need(state["budget"]["requests"] < request["max_total_requests"], "capture_request_budget_reached")
            need(operation["attempts"] < request["max_attempts_per_operation"], "source_attempt_limit")
            remaining = request["max_total_bytes"] - state["budget"]["response_bytes"]
            need(remaining > 0, "capture_byte_budget_reached")
            operation.update(status="in_flight", attempts=operation["attempts"] + 1, started_at=instant.isoformat())
            invocation_requests += 1
            state["budget"]["requests"] += 1
            path = save(root, state)
            allowance = min(request["max_response_bytes"], remaining)
            try:
                status, headers, raw = transport(request["origin"] + route, session_token,
                    allowance, min(45, request["max_elapsed_seconds"] - age - (time.monotonic() - clock_start)))
                need(type(raw) is bytes and len(raw) <= allowance, "response_byte_budget_reached")
                need(session_token.encode() not in raw, "credential_echo_rejected")
            except Exception:
                operation["status"] = "outcome_unknown"
                # Unknown transport outcomes reserve the full permitted response
                # size; repeated failures cannot evade the aggregate byte cap.
                state["budget"]["response_bytes"] += allowance
                state["budget"]["unmeasured_reserved_bytes"] += allowance
                state["gaps"].append("source_transport_outcome_unknown_no_automatic_replay")
                path = save(root, state)
                raise Pending() from None
            headers = {k.lower(): v for k, v in headers.items() if k.lower() in
                       ("content-type", "content-length", "retry-after", "etag", "last-modified")}
            need(not any(session_token in str(v) for v in headers.values()), "credential_header_echo_rejected")
            state["budget"]["response_bytes"] += len(raw)
            if "content-length" in headers:
                need(str(headers["content-length"]).isdigit() and int(headers["content-length"]) == len(raw), "source_incomplete_transfer")
            operation.update(http_status=status, response_sha256=F.raw_sha(raw), response_bytes=len(raw))
            if status != 200:
                operation["status"] = "throttled" if status == 429 else "unavailable"
                if status == 429:
                    operation["retry_not_before"] = _retry_after(headers, instant)
                    state["gaps"].append("source_throttled_explicit_resume_required")
                else:
                    state["status"] = "blocked"
                    state["gaps"].append("source_access_denied_or_unavailable")
                path = save(root, state)
                raise Pending()
            media = headers.get("content-type", "").split(";")[0].lower().strip()
            # Check the type before retaining any response body.
            if key.endswith("image"):
                need(media == "image/png", "source_png_media_required")
                F.png_info(raw)
            elif key.endswith("data"):
                need(media in ("text/csv", "application/csv"), "source_csv_media_required")
                F.csv_info(raw)
            elif "definition" in key:
                need(media in ("application/xml", "text/xml", "application/octet-stream", "application/zip"), "source_definition_media_required")
                F.definition(raw)
            else:
                need(media == "application/json", "source_json_media_required")
                _secret_free_json(F.decode(raw))
            operation["response"] = F.write_once(root, f"response-{operation['ordinal']:04d}-{operation['attempts']}.bin", raw)
            operation.update(status="complete", headers=headers)
            path = save(root, state)
            return raw, headers

        try:
            need(not request["state"]["parameters"], "parameter_execution_not_qualified_use_observed_transfer")
            # A fresh resume bracket is required before unfinished acquisition.
            suffix = f"resume-{state['journal_revision']}" if resume and "definition" in state["source"] else "before"
            session_raw, _ = get("session-" + suffix, prefix + "/sessions/current")
            identity = _session(session_raw, request)
            workbook_raw, _ = get("workbook-" + suffix, site + f"/workbooks/{request['workbook_id']}")
            views_raw, _ = get("views-" + suffix, site + f"/workbooks/{request['workbook_id']}/views")
            metadata = _metadata(workbook_raw, views_raw, request)
            definition_raw, _ = get("definition-" + suffix, site + f"/workbooks/{request['workbook_id']}/content?includeExtract=False")
            parsed = F.definition(definition_raw)
            if "definition" not in state["source"]:
                set_definition(root, state, definition_raw)
                state["source"].update(metadata_before=metadata, identity=identity)
                path = save(root, state)
            else:
                need(metadata == state["source"]["metadata_before"] and parsed["fingerprint"] == state["source"]["definition_fingerprint"], "source_definition_or_metadata_drift")
            filters = {"vf_" + key: value for key, value in request["state"]["filters"].items()}
            for index, view in enumerate(state["captures"]):
                options = request["image_options"]
                image_query = dict(filters)
                if "width" in options:
                    image_query.update(vizWidth=str(options["width"]), vizHeight=str(options["height"]))
                if "max_age_minutes" in options:
                    image_query["maxAge"] = str(options["max_age_minutes"])
                route = site + f"/views/{view['view_id']}/image"
                if image_query:
                    route += "?" + urlencode(sorted(image_query.items()))
                if not any(a["path"] in view["attachments"] and a["format"] == "png" for a in state["attachments"]):
                    raw, _ = get(f"view-{index}-image", route)
                    add_attachment(root, state, raw, f"view-{index:03d}.png", "png", "image/png", view,
                                   operation_key=f"view-{index}-image", requested_dimensions=options)
                    path = save(root, state)
                if view["role"] == "worksheet" and not any(a["path"] in view["attachments"] and a["format"] == "csv" for a in state["attachments"]):
                    query = dict(filters)
                    if "max_age_minutes" in options:
                        query["maxAge"] = str(options["max_age_minutes"])
                    route = site + f"/views/{view['view_id']}/data" + ("?" + urlencode(sorted(query.items())) if query else "")
                    raw, _ = get(f"view-{index}-data", route)
                    add_attachment(root, state, raw, f"view-{index:03d}.csv", "csv", "text/csv", view, operation_key=f"view-{index}-data")
                    path = save(root, state)
                view["status"] = "complete"
            final_key = "after"
            final_raw, _ = get("definition-" + final_key, site + f"/workbooks/{request['workbook_id']}/content?includeExtract=False")
            final_workbook, _ = get("workbook-" + final_key, site + f"/workbooks/{request['workbook_id']}")
            final_views, _ = get("views-" + final_key, site + f"/workbooks/{request['workbook_id']}/views")
            final_session, _ = get("session-" + final_key, prefix + "/sessions/current")
            _session(final_session, request)
            final = _metadata(final_workbook, final_views, request)
            state["source"]["metadata_after"] = final
            need(F.definition(final_raw)["fingerprint"] == state["source"]["definition_fingerprint"]
                 and final == state["source"]["metadata_before"], "source_definition_or_metadata_drift")
            state["source"]["coherence"] = "unchanged_before_after_not_atomic"
            state["status"] = "complete"
        except Pending:
            pass
        except (CaptureError, KeyError, TypeError, ValueError, OSError) as error:
            state["status"] = "blocked"
            state["gaps"].append(str(error) if isinstance(error, CaptureError) else "capture_boundary_failed_review_required")
        path = save(root, state)
        return {"status": state["status"], "output": str(path), "capture": state}


def _redacted_mcp(value):
    """Presigned URLs are bearer material. Retain their exact hash, not the query."""
    if type(value) is dict:
        result = {}
        for key, item in value.items():
            if key == "uri" and type(item) is str and item.startswith(("https://", "http://")):
                parsed = urlsplit(item)
                result[key] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
                result["uri_sha256"] = F.raw_sha(item.encode())
                result["uri_query_removed"] = bool(parsed.query)
            else:
                need(not F.secret_name(key) or not item, "credential_bearing_mcp_response")
                result[key] = _redacted_mcp(item)
        return result
    if type(value) is list:
        return [_redacted_mcp(item) for item in value]
    return value


def _mcp_payload(response):
    need(type(response) is dict and type(response.get("content")) is list, "mcp_result_required")
    need(len(response["content"]) <= 20 and all(type(b) is dict for b in response["content"]), "mcp_content_shape")
    need(not response.get("isError"), "mcp_tool_reported_error")
    return response["content"]


def import_mcp(value, intake, *, directory, transfer_directory=None, allow_source_read=False):
    """Import already-received official MCP responses; never access response URLs/paths.

    intake schema tableau-mcp-intake.v1: records [{record_id,tool,arguments,response,
    phase?:before|after,transfer?:{path,sha256,bytes,reference_sha256,provenance_reference}}].
    A transfer path is relative to an explicitly approved local transfer_directory.
    reference_sha256 hashes the exact remote resource URI or temp path. It is a
    declared transfer link, not authenticated host provenance.
    """
    request = validate_request(value)
    need(allow_source_read is True, "source_read_authorization_required")
    need(type(intake) is dict and intake.get("schema_version") == "tableau-mcp-intake.v1"
         and type(intake.get("records")) is list and 0 < len(intake["records"]) <= 500, "mcp_intake_contract")
    need(len(encoded(intake)) <= F.MAX_JSON, "mcp_intake_size")
    root = F.private_directory(directory)
    need(not list(root.glob("capture-*.json")), "capture_exists")
    state = new_envelope(request, "official_mcp_import", utcnow())
    state["source"]["identity_verification"] = "supplied_not_authenticated"
    state["gaps"].extend(["mcp_principal_and_site_not_independently_authenticated", "mcp_transfer_provenance_is_supplied_evidence"])
    state["source"]["intake_sha256"] = sha(intake)
    state["budget"]["response_bytes"] = len(encoded(intake))
    need(state["budget"]["response_bytes"] <= request["max_total_bytes"], "mcp_intake_byte_budget")
    seen = set()
    for index, record in enumerate(intake["records"]):
        need(type(record) is dict and type(record.get("record_id")) is str and ID.fullmatch(record["record_id"])
             and record["record_id"] not in seen, "mcp_record_identity")
        seen.add(record["record_id"])
        tool, args, response = record.get("tool"), record.get("arguments"), record.get("response")
        need(tool in ("get-workbook", "download-workbook", "get-view-image", "get-view-data")
             and type(args) is dict, "mcp_tool_outside_scope")
        allowed = {"get-workbook": {"workbookId"}, "download-workbook": {"workbookId", "includeExtract"},
                   "get-view-image": {"viewId", "viewFilters", "width", "height", "format"},
                   "get-view-data": {"viewId", "viewFilters"}}[tool]
        need(not set(args) - allowed, "mcp_arguments_outside_contract")
        clean = _redacted_mcp(response)
        response_pin = add_attachment(root, state, encoded(clean), f"mcp-{index:03d}.json", "json", "application/json",
                                      original_response_sha256=sha(response), redacted=clean != response)
        receipt = {"record_id": record["record_id"], "tool": tool, "arguments": args, "response": response_pin,
                   "status": "partial", "parts": []}
        state["operations"].append(receipt)
        try:
            content = _mcp_payload(response)
            if tool in ("get-workbook", "download-workbook"):
                need(args.get("workbookId") == request["workbook_id"], "mcp_workbook_mismatch")
            else:
                need(args.get("viewId") in {v["view_id"] for v in request["views"]}, "mcp_view_outside_scope")
                supplied = args.get("viewFilters", {})
                need(type(supplied) is dict, "mcp_filter_shape")
                filters = {k[3:] if k.startswith("vf_") else k: v for k, v in supplied.items()}
                need(len(filters) == len(supplied) and filters == request["state"]["filters"], "mcp_filter_state_mismatch")
            view = next((v for v in state["captures"] if v["view_id"] == args.get("viewId")), None)
            raw, media = None, None
            references = []
            for block in content:
                if block.get("type") == "resource_link":
                    references.append(block["uri"])
                elif block.get("type") == "text":
                    try:
                        parsed = F.decode(block.get("text", "").encode())
                    except CaptureError:
                        parsed = None
                    if type(parsed) is dict and type(parsed.get("path")) is str:
                        references.append(parsed["path"])
            if references:
                transfer = record.get("transfer")
                if not transfer:
                    state["gaps"].append("remote_resource_or_path_not_transferred")
                    continue
                need(transfer_directory is not None and len(references) == 1 and transfer.get("reference_sha256") == F.raw_sha(references[0].encode())
                     and transfer.get("provenance_reference"), "explicit_transfer_provenance_required")
                transfer_root = F.no_links(Path(transfer_directory).absolute())
                raw = F.read_pin(transfer_root, transfer)
                need(len(raw) <= request["max_response_bytes"], "mcp_transfer_size_limit")
                state["budget"]["response_bytes"] += len(raw)
                need(state["budget"]["response_bytes"] <= request["max_total_bytes"], "mcp_transfer_byte_budget")
                media = next((b.get("mimeType") for b in content if b.get("type") == "resource_link"), None)
                if media is None:
                    media = next(F.decode(b["text"].encode()).get("mimeType") for b in content if b.get("type") == "text")
                receipt["transfer"] = {k: transfer[k] for k in ("path", "sha256", "bytes", "reference_sha256", "provenance_reference")}
            if tool == "get-workbook":
                texts = [F.decode(b["text"].encode()) for b in content if b.get("type") == "text"]
                need(len(texts) == 1 and type(texts[0]) is dict, "mcp_workbook_shape")
                obj = texts[0].get("workbook", texts[0])
                need(obj.get("id") == request["workbook_id"], "mcp_workbook_identity")
                phase = record.get("phase")
                need(phase in ("before", "after") and "metadata_" + phase not in state["source"], "mcp_metadata_phase")
                state["source"]["metadata_" + phase] = texts[0]
            elif tool == "download-workbook":
                need(args.get("includeExtract") is False, "mcp_no_extract_request_required")
                need(raw is not None, "workbook_transfer_required")
                need("definition" not in state["source"], "duplicate_workbook_definition")
                set_definition(root, state, raw)
            elif tool == "get-view-image":
                options = request["image_options"]
                need(args.get("width") == options.get("width") and args.get("height") == options.get("height"), "mcp_image_dimensions_request_mismatch")
                if raw is None:
                    images = [b for b in content if b.get("type") == "image"]
                    need(len(images) == 1 and images[0].get("mimeType") == "image/png", "mcp_png_required")
                    try:
                        raw = base64.b64decode(images[0]["data"], validate=True)
                    except (ValueError, TypeError) as exc:
                        raise CaptureError("mcp_invalid_base64") from exc
                need(args.get("format", "PNG") == "PNG" and media in (None, "image/png"), "mcp_png_required")
                add_attachment(root, state, raw, f"mcp-{index:03d}.png", "png", "image/png", view, operation_key=record["record_id"])
            else:
                if raw is None:
                    texts = [F.decode(b["text"].encode()) for b in content if b.get("type") == "text"]
                    need(len(texts) == 1, "mcp_data_shape")
                    data = texts[0]
                    if type(data) is str:
                        raw = data.encode("utf-8")
                    else:
                        need(type(data) is list and int(request["api_version"].split(".")[1]) >= 30, "mcp_all_data_version_or_shape")
                        need(0 < len(data) <= 1000, "mcp_all_data_part_limit")
                        # Validate every part before retaining any derived CSV.
                        # A malformed multipart result is not a partial success.
                        for part in data:
                            need(type(part) is dict and type(part.get("sheetName")) is str and part.get("sheetStatus") in ("OK", "ERROR")
                                 and type(part.get("columns")) is list and type(part.get("rows")) is list, "mcp_all_data_part_shape")
                            need(len(part["columns"]) <= 1000 and len(part["rows"]) <= 50000
                                 and all(type(c) is str for c in part["columns"])
                                 and all(type(r) is list and len(r) == len(part["columns"]) and all(type(c) is str for c in r) for r in part["rows"]), "mcp_all_data_ragged_part")
                            need(part["sheetStatus"] != "ERROR" or (part["columns"] == [] and part["rows"] == []), "mcp_error_part_rows")
                        for part_index, part in enumerate(data):
                            need(type(part) is dict and type(part.get("sheetName")) is str and part.get("sheetStatus") in ("OK", "ERROR")
                                 and type(part.get("columns")) is list and type(part.get("rows")) is list, "mcp_all_data_part_shape")
                            saved_part = {"part_index": part_index, "sheet_name": part["sheetName"], "sheet_status": part["sheetStatus"], "source_part": part,
                                          "identity_status": "unresolved_no_caption_join"}
                            receipt["parts"].append(saved_part)
                            if part["sheetStatus"] == "ERROR":
                                need(part["columns"] == [] and part["rows"] == [], "mcp_error_part_rows")
                                state["gaps"].append("mcp_all_data_sheet_error")
                                continue
                            need(all(type(c) is str for c in part["columns"]) and all(type(r) is list and len(r) == len(part["columns"])
                                 and all(type(c) is str for c in r) for r in part["rows"]), "mcp_all_data_ragged_part")
                            stream = io.StringIO(newline="")
                            F.csv.writer(stream).writerows([part["columns"], *part["rows"]])
                            # Part order is identity. Never attribute duplicate or caption-only sheets to selected worksheets.
                            part_pin = add_attachment(root, state, stream.getvalue().encode(), f"mcp-{index:03d}-part-{part_index:03d}.csv", "csv", "text/csv",
                                                      operation_key=record["record_id"], part_index=part_index, sheet_name=part["sheetName"], source_view_id=view["view_id"])
                            saved_part["attachment"] = part_pin["path"]
                        state["gaps"].append("mcp_all_data_part_identity_mapping_required")
                if raw is not None:
                    need(media in (None, "text/csv", "application/csv"), "mcp_csv_media_required")
                    add_attachment(root, state, raw, f"mcp-{index:03d}.csv", "csv", "text/csv", view,
                                   operation_key=record["record_id"], coverage="first_worksheet_only" if view["role"] == "dashboard" else "selected_worksheet")
                    if view["role"] == "dashboard":
                        state["gaps"].append("legacy_dashboard_csv_covers_first_worksheet_only")
            receipt["status"] = "received"
        except (CaptureError, KeyError, TypeError, ValueError):
            receipt["status"] = "rejected"
            state["gaps"].append("mcp_record_invalid_or_unavailable")
    for view in state["captures"]:
        formats = {a["format"] for a in state["attachments"] if a["path"] in view["attachments"]}
        view["status"] = "complete" if {"png", *( ["csv"] if view["role"] == "worksheet" else [])} <= formats else "partial"
    before, after = state["source"].get("metadata_before"), state["source"].get("metadata_after")
    if before is not None and after is not None and before != after:
        state["status"] = "blocked"
        state["gaps"].append("mcp_metadata_drift")
    else:
        # MCP metadata alone does not re-download the definition after render.
        state["gaps"].append("mcp_definition_after_capture_not_verified")
        state["status"] = "partial"
    path = save(root, state)
    return {"status": state["status"], "output": str(path), "capture": state}


def enrich_dma(capture_path, *, checkout, executable, expected_reader_sha256, producer_revision, runner=None):
    """Explicit trusted DMA reader step, never import a workbook/customer repository.

    The configured checkout, executable and expected source SHA are operator trust
    inputs. Revision is retained as a declaration; the actual reader bytes are
    rechecked. Only a new private directory containing our pinned TWB is parsed.
    """
    path = F.no_links(capture_path)
    root = F.private_directory(path.parent)
    supplied = F.decode(path.read_bytes())
    request = validate_request(supplied["request"])
    with os.fdopen(os.open(root / ".capture.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state, latest = load_latest(root, request)
        need(path == latest, "latest_capture_required_for_enrichment")
        need("definition" in state["source"] and "semantic_inventory" not in state["source"], "one_definition_enrichment_required")
        checkout = F.no_links(checkout).resolve(strict=True)
        executable = Path(executable).absolute()
        F.no_links(executable.parent)
        resolved_executable = executable.resolve(strict=True)
        need(not checkout.is_relative_to(root) and not resolved_executable.is_relative_to(root)
             and resolved_executable.is_file() and os.access(executable, os.X_OK), "trusted_dma_location_required")
        reader = F.no_links(checkout / "skills/data-model-accelerator/scripts/tableau_source.py")
        need(type(expected_reader_sha256) is str and HASH.fullmatch(expected_reader_sha256)
             and F.raw_sha(reader.read_bytes()) == expected_reader_sha256, "trusted_dma_reader_changed")
        need(type(producer_revision) is str and re.fullmatch(r"[0-9a-f]{40}", producer_revision), "dma_revision_required")
        raw = F.read_pin(root, state["source"]["definition"])
        script = ("import importlib.util,json,sys;"
                  "s=importlib.util.spec_from_file_location('trusted_tableau_source',sys.argv[1]);"
                  "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                  "json.dump(m.inspect_repo(sys.argv[2]),sys.stdout,ensure_ascii=False,allow_nan=False)")
        # The fixed child reads one evidence-only folder. No customer Python,
        # project configuration, hooks, SQL or macros are executed by this step.
        with tempfile.TemporaryDirectory(prefix=".dma-read-", dir=root) as directory:
            folder = Path(directory)
            F.write_once(folder, "definition.twb", raw)
            with tempfile.TemporaryFile() as stdout:
                result = (runner or subprocess.run)([str(executable), "-I", "-B", "-c", script, str(reader), str(folder)],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.DEVNULL, shell=False, timeout=60,
                    env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"})
                need(result.returncode == 0, "dma_reader_failed")
                stdout.seek(0)
                inventory = F.decode(stdout.read(F.MAX_JSON + 1))
        need(inventory.get("schema_version") == 1 and inventory.get("kind") == "tableau_source_inventory", "dma_inventory_contract")
        need(any(a.get("path") == "definition.twb" and a.get("sha256") == F.raw_sha(raw) for a in inventory.get("assets", [])), "dma_definition_pin_mismatch")
        _secret_free_json(inventory)
        state["source"].update(semantic_inventory=inventory, semantic_inventory_sha256=sha(inventory),
            semantic_producer={"reader_sha256": expected_reader_sha256, "revision": producer_revision,
                               "revision_status": "operator_declared", "reader": str(reader)})
        state["gaps"] = [gap for gap in state["gaps"] if gap != "semantic_inventory_not_attached"]
        state["gaps"].append("dma_static_inventory_is_not_native_semantic_validation")
        output = save(root, state)
        return {"status": state["status"], "output": str(output), "capture": state}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "import-mcp"):
        p = sub.add_parser(name)
        p.add_argument("--request", type=Path, required=True)
        p.add_argument("--directory", type=Path, required=True)
        p.add_argument("--allow-source-read", action="store_true")
        if name == "capture":
            p.add_argument("--allow-source-query", action="store_true")
            p.add_argument("--session-token-stdin", action="store_true")
            p.add_argument("--resume", action="store_true")
        else:
            p.add_argument("--response", type=Path, required=True)
            p.add_argument("--transfer-directory", type=Path)
    enrich = sub.add_parser("enrich-dma")
    enrich.add_argument("--capture", type=Path, required=True)
    enrich.add_argument("--dma-checkout", type=Path, required=True)
    enrich.add_argument("--dma-python", type=Path, required=True)
    enrich.add_argument("--dma-reader-sha256", required=True)
    enrich.add_argument("--dma-revision", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "enrich-dma":
            result = enrich_dma(args.capture, checkout=args.dma_checkout, executable=args.dma_python,
                                expected_reader_sha256=args.dma_reader_sha256, producer_revision=args.dma_revision)
            print(encoded({"status": result["status"], "output": result["output"]}).decode())
            return 0
        request_path = F.no_links(args.request)
        need(request_path.stat().st_size <= F.MAX_XML, "request_size_limit")
        request = F.decode(request_path.read_bytes())
        if args.command == "capture":
            need(args.session_token_stdin, "session_token_stdin_required")
            token = sys.stdin.buffer.readline(8194)
            need(len(token) <= 8193, "source_token_size_limit")
            token = token.rstrip(b"\n").decode("ascii")
            result = capture_rest(request, directory=args.directory, session_token=token, resume=args.resume,
                                  allow_source_read=args.allow_source_read, allow_source_query=args.allow_source_query)
        else:
            response_path = F.no_links(args.response)
            need(response_path.stat().st_size <= F.MAX_JSON, "mcp_intake_size")
            result = import_mcp(request, F.decode(response_path.read_bytes()), directory=args.directory,
                                transfer_directory=args.transfer_directory, allow_source_read=args.allow_source_read)
        print(encoded({"status": result["status"], "output": result["output"]}).decode())
        return 0
    except (CaptureError, ValueError, OSError, KeyError, TypeError):
        print('{"status":"rejected","error":"tableau_source_boundary_failed"}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
