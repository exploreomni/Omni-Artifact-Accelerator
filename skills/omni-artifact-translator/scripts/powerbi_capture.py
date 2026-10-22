#!/usr/bin/env python3
"""Bounded source-only Power BI/Fabric capture. No source lifecycle or target writes."""

from __future__ import annotations
import argparse
import copy
from datetime import datetime, timedelta, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid

_spec = importlib.util.spec_from_file_location(
    "oaa_powerbi_capture_files", Path(__file__).with_name("powerbi_capture_files.py")
)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
CaptureError, need, sha, encoded = F.CaptureError, F.need, F.sha, F.encoded
REQUEST = "powerbi-visual-capture-request.v1"
ENVELOPE = "powerbi-visual-capture.v1"
FABRIC = "https://api.fabric.microsoft.com"
POWERBI = "https://api.powerbi.com"
BASE_GAPS = [
    "observed_state_unknown",
    "principal_and_effective_access_unverified",
    "configuration_bracket_is_not_atomic_data_snapshot",
    "refresh_watermark_unknown",
    "semantic_model_definition_not_acquired",
    "export_completeness_not_established",
    "sensitivity_label_not_in_fabric_definition",
    "native_and_business_acceptance_not_performed",
]


def utcnow():
    return datetime.now(timezone.utc)


def valid_id(value):
    return type(value) is str and bool(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value)
    )


def uuid_id(value):
    try:
        return type(value) is str and str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def validate_request(value, *, require_service=False):
    required = {
        "schema_version",
        "capture_id",
        "workspace_id",
        "report_id",
        "dataset_id",
        "principal_ref",
        "authorization_ref",
        "evidence_mode",
        "route",
        "route_reference",
        "views",
        "state",
        "queries",
    }
    defaults = {
        "max_requests_per_invocation": 20,
        "max_total_requests": 200,
        "max_total_bytes": 64_000_000,
        "max_elapsed_seconds": 21600,
        "max_attempts_per_operation": 3,
        "max_response_bytes": F.MAX_FILE,
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
        valid_id(result["capture_id"])
        and (
            (uuid_id(result["workspace_id"]) and uuid_id(result["report_id"]))
            or (
                not require_service
                and result["workspace_id"] is None
                and result["report_id"] is None
            )
        )
        and (result["dataset_id"] is None or uuid_id(result["dataset_id"])),
        "request_identity_rejected",
    )
    for key in ("principal_ref", "authorization_ref"):
        need(
            type(result[key]) is str and 0 < len(result[key]) <= 1000,
            "source_authorization_reference_required",
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
        and (
            result["route"] == "unselected"
            or type(result["route_reference"]) is str
            and bool(result["route_reference"])
        ),
        "explicit_route_required",
    )
    limits = {
        "max_requests_per_invocation": (1, 500),
        "max_total_requests": (1, 5000),
        "max_total_bytes": (1, 512_000_000),
        "max_elapsed_seconds": (1, 86400),
        "max_attempts_per_operation": (1, 20),
        "max_response_bytes": (1, F.MAX_FILE),
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
            "bookmark",
            "locale",
            "timezone",
            "principal",
            "data_time_policy",
        },
        "state_contract_required",
    )
    for key in ("state_id", "data_time_policy"):
        need(
            type(state[key]) is str and 0 < len(state[key]) <= 1000,
            "state_reference_required",
        )
    for key in ("locale", "timezone", "principal"):
        need(
            state[key] is None
            or type(state[key]) is str
            and 0 < len(state[key]) <= 1000,
            "state_value_rejected",
        )
    need(
        type(state["filters"]) is list
        and len(state["filters"]) <= 1
        and all(
            type(f) is dict
            and set(f) == {"filter"}
            and type(f["filter"]) is str
            and 0 < len(f["filter"]) <= 8000
            for f in state["filters"]
        ),
        "one_export_filter_supported",
    )
    bookmark = state["bookmark"]
    need(
        bookmark is None
        or type(bookmark) is dict
        and set(bookmark) in ({"name"}, {"state"})
        and all(type(v) is str and 0 < len(v) <= 32000 for v in bookmark.values()),
        "bookmark_rejected",
    )
    need(
        type(result["views"]) is list and 0 <= len(result["views"]) <= 100, "view_limit"
    )
    seen = set()
    for view in result["views"]:
        need(
            type(view) is dict
            and set(view) == {"page_id", "visual_id", "export_png"}
            and valid_id(view["page_id"])
            and (view["visual_id"] is None or valid_id(view["visual_id"]))
            and type(view["export_png"]) is bool,
            "view_contract_required",
        )
        key = (view["page_id"], view["visual_id"])
        need(key not in seen, "duplicate_view")
        seen.add(key)
        need(
            not (bookmark and view["visual_id"] and view["export_png"]),
            "bookmark_not_supported_for_single_visual_export",
        )
    need(
        type(result["queries"]) is list and len(result["queries"]) <= 50, "query_limit"
    )
    query_ids = set()
    for query in result["queries"]:
        need(
            type(query) is dict
            and set(query)
            == {"query_id", "query", "page_id", "visual_id", "context_reference"}
            and valid_id(query["query_id"])
            and query["query_id"] not in query_ids
            and result["dataset_id"]
            and type(query["query"]) is str
            and 0 < len(query["query"]) <= 64000
            and re.match(r"\s*(?:EVALUATE|DEFINE)\b", query["query"], re.I)
            and type(query["context_reference"]) is str
            and bool(query["context_reference"])
            and (query["page_id"], query["visual_id"]) in seen,
            "query_contract_required",
        )
        query_ids.add(query["query_id"])
    manifest = result["expected_manifest"]
    need(
        type(manifest) is dict
        and set(manifest) == {"reference", "completeness", "objects"}
        and type(manifest["reference"]) is str
        and manifest["reference"]
        and manifest["completeness"] in ("selected_report", "partial")
        and type(manifest["objects"]) is list
        and len(manifest["objects"]) <= 10000
        and all(
            type(o) is dict
            and set(o) == {"object_id", "kind"}
            and type(o["object_id"]) is str
            and type(o["kind"]) is str
            for o in manifest["objects"]
        ),
        "expected_manifest_rejected",
    )
    F.secret_check(result)
    F.safe_text(encoded(result))
    need(len(encoded(result)) <= 256000, "request_size_limit")
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureError("source_redirect_refused")


def default_transport(method, url, token, body, maximum, timeout):
    need(
        timeout > 0 and threading.current_thread() is threading.main_thread(),
        "deadline_main_thread_required",
    )
    need(
        signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
        "existing_deadline_context_unsupported",
    )
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise TimeoutError("source_request_deadline")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            response = build_opener(NoRedirect()).open(request, timeout=timeout)
        except HTTPError as error:
            response = error
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
                    "location",
                    "x-ms-operation-id",
                    "etag",
                    "last-modified",
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


def new_envelope(request, mode, now):
    return {
        "schema_version": ENVELOPE,
        "capture_id": request["capture_id"],
        "request": request,
        "request_sha256": sha(request),
        "created_at": now.isoformat(),
        "source": {
            "definition_files": [],
            "state_observation": {"status": "unknown"},
            "identity": {
                "workspace_id": request["workspace_id"],
                "report_id": request["report_id"],
                "principal_ref": request["principal_ref"],
                "principal_verification": "supplied_unverified",
            },
        },
        "producer": {
            "name": "oaa-powerbi-capture",
            "mode": mode,
            "script_sha256": F.raw_sha(Path(__file__).read_bytes()),
            "file_validator_sha256": F.raw_sha(Path(F.__file__).read_bytes()),
            "documentation_reviewed": "2026-10-21",
        },
        "captures": [
            {
                **view,
                "state_sha256": sha(request["state"]),
                "status": "partial",
                "attachments": [],
                "gaps": [],
            }
            for view in request["views"]
        ],
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


def load_latest(root, request):
    files = sorted(root.glob("capture-*.json"))
    need(files and len(files) <= 20000, "journal_required")
    previous = None
    for index, path in enumerate(files, 1):
        need(path.name == f"capture-{index:06d}.json", "journal_sequence")
        value = F.decode(F.read_file(path, F.MAX_JSON))
        need(
            value.get("journal_revision") == index
            and value.get("previous_content_hash") == previous
            and value.get("content_hash")
            == sha({k: v for k, v in value.items() if k != "content_hash"}),
            "journal_changed",
        )
        previous = value["content_hash"]
    need(
        value.get("schema_version") == ENVELOPE
        and value.get("request") == request
        and value.get("request_sha256") == sha(request),
        "capture_request_changed",
    )
    need(
        value["producer"]["script_sha256"] == F.raw_sha(Path(__file__).read_bytes())
        and value["producer"]["file_validator_sha256"]
        == F.raw_sha(Path(F.__file__).read_bytes()),
        "capture_runtime_changed",
    )
    for pin in value["attachments"]:
        raw = F.read_pin(root, pin)
        if pin["format"] == "png":
            F.png_info(raw)
        elif pin["format"] == "zip":
            F.image_parts(raw)
    for pin in value["source"]["definition_files"]:
        raw = F.read_pin(root, pin)
        if pin.get("content_utf8") is not None:
            need(raw == pin["content_utf8"].encode(), "definition_text_changed")
    for operation in value["operations"]:
        if operation.get("response"):
            F.read_pin(root, operation["response"])
    return value, files[-1]


def attachment(root, state, raw, name, fmt, media, view=None, **extra):
    pin = F.write_once(root, name, raw)
    value = {
        **pin,
        "format": fmt,
        "media_type": media,
        "page_id": view["page_id"] if view else None,
        "visual_id": view["visual_id"] if view else None,
        "state_sha256": sha(state["request"]["state"]),
        "request_sha256": state["request_sha256"],
        **extra,
    }
    state["attachments"].append(value)
    if view is not None:
        view["attachments"].append(name)
    return value


def set_definition(root, state, parts):
    need(not state["source"]["definition_files"], "definition_already_set")
    for index, part in enumerate(parts):
        name = f"definition-{index:04d}.bin"
        pin = F.write_once(root, name, part["raw"])
        state["source"]["definition_files"].append(
            {
                **pin,
                "source_path": part["source_path"],
                "content_utf8": part["content_utf8"],
            }
        )
    state["source"]["definition_fingerprint"] = sha(
        [
            {
                "source_path": p["source_path"],
                "sha256": p["sha256"],
                "bytes": p["bytes"],
            }
            for p in state["source"]["definition_files"]
        ]
    )
    identity = state["source"]["identity"]
    identity["namespace"] = (
        "powerbi:"
        + state["request"]["workspace_id"]
        + ":"
        + state["request"]["report_id"]
        if state["request"]["workspace_id"] is not None
        else "definition:" + state["source"]["definition_fingerprint"]
    )
    identity["identity_scope"] = (
        "supplied_service_ids"
        if state["request"]["workspace_id"] is not None
        else "definition_only"
    )


def parts_fingerprint(parts):
    return sha(
        [
            {
                "source_path": p["source_path"],
                "sha256": F.raw_sha(p["raw"]),
                "bytes": len(p["raw"]),
            }
            for p in parts
        ]
    )


def _import(request, directory, parts, mode, original=None):
    request = validate_request(request)
    root = F.private_directory(directory)
    need(not list(root.iterdir()), "new_capture_directory_required")
    state = new_envelope(request, mode, utcnow())
    set_definition(root, state, parts)
    if original is not None:
        attachment(
            root,
            state,
            encoded(original),
            "supplied-fabric-definition.json",
            "json",
            "application/json",
        )
    state["gaps"].append("supplied_definition_identity_and_freshness_not_authenticated")
    for view in state["captures"]:
        view["gaps"].append("requested_render_not_supplied")
    output = save(root, state)
    return {"status": state["status"], "output": str(output), "capture": state}


def import_local(request, definition_root, directory, *, allow_source_read=False):
    need(allow_source_read, "source_read_grant_required")
    root = F.no_links(definition_root)
    destination = Path(directory).absolute()
    need(
        root != destination and root not in destination.parents,
        "capture_inside_source_forbidden",
    )
    return _import(request, directory, F.local_parts(root), "supplied_local_definition")


def import_fabric_definition(request, payload, directory, *, allow_source_read=False):
    need(allow_source_read, "source_read_grant_required")
    parts = F.fabric_parts(payload)
    return _import(request, directory, parts, "supplied_fabric_definition", payload)


class StopCapture(Exception):
    pass


class Session:
    def __init__(self, root, state, tokens, transport, now):
        self.root, self.state, self.tokens, self.transport, self.now = (
            root,
            state,
            tokens,
            transport,
            now,
        )
        self.calls = 0
        self.started = time.monotonic()

    def stop(self, code, blocked=False):
        self.state["gaps"].append(code)
        self.state["status"] = "blocked" if blocked else "partial"
        save(self.root, self.state)
        raise StopCapture(code)

    def call(self, key, audience, method, path, payload=None, binary=False):
        state, request = self.state, self.state["request"]
        origins = {"fabric": FABRIC, "powerbi": POWERBI}
        need(audience in origins, "audience_rejected")
        url = origins[audience] + path
        parsed = urlsplit(url)
        need(
            parsed.netloc == urlsplit(origins[audience]).netloc and not parsed.fragment,
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
        matches = [op for op in state["operations"] if op["key"] == key]
        op = matches[0] if matches else None
        if op:
            need(op["operation_sha256"] == identity, "operation_request_changed")
            if op["status"] == "complete":
                raw = F.read_pin(self.root, op["response"])
                return op["http_status"], op["headers"], raw
            if op["status"] in ("intent", "ambiguous", "failed"):
                self.stop("unresolved_operation_requires_new_reviewed_capture", True)
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
        token = self.tokens.get(audience)
        if not (
            type(token) is str
            and 8 <= len(token) <= 16384
            and re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token)
        ):
            self.stop("configured_" + audience + "_token_required", True)
        if op is None:
            op = {
                "key": key,
                "audience": audience,
                "method": method,
                "path": path,
                "operation_sha256": identity,
                "request_sha256": state["request_sha256"],
                "attempts": 0,
            }
            state["operations"].append(op)
        op["attempts"] += 1
        op["status"] = "intent"
        op.pop("not_before", None)
        state["budget"]["requests"] += 1
        self.calls += 1
        save(self.root, state)
        try:
            code, headers, raw = self.transport(
                method,
                url,
                token,
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
                in (
                    "content-type",
                    "retry-after",
                    "location",
                    "x-ms-operation-id",
                    "etag",
                    "last-modified",
                )
            }
            need(
                all(type(v) is str and len(v) <= 4096 for v in headers.values()),
                "response_header_rejected",
            )
            for secret in self.tokens.values():
                if secret:
                    need(
                        secret.encode() not in raw
                        and all(secret not in v for v in headers.values()),
                        "response_contains_token",
                    )
            state["budget"]["response_bytes"] += len(raw)
            # Never persist unknown signed download URLs or server error bodies.
            need(
                not any(
                    urlsplit(v).query for k, v in headers.items() if k == "location"
                ),
                "signed_or_query_location_rejected",
            )
            if code in (200, 202) and not binary and raw:
                value = F.decode(raw)
                F.secret_check(value)
                F.safe_text(raw)
                for secret in self.tokens.values():
                    if secret:
                        need(
                            secret.encode() not in encoded(value),
                            "decoded_response_contains_token",
                        )
                if code == 200 and ("getDefinition" in path or key.endswith(".result")):
                    parts = F.fabric_parts(value)
                    for part in parts:
                        for secret in self.tokens.values():
                            if secret:
                                need(
                                    secret.encode() not in part["raw"],
                                    "definition_part_contains_token",
                                )
                if type(value) is dict and value.get("resourceLocation"):
                    need(
                        not urlsplit(value["resourceLocation"]).query,
                        "signed_resource_location_not_retained",
                    )
            if code not in (200, 202):
                op.update(
                    http_status=code,
                    headers={k: v for k, v in headers.items() if k == "retry-after"},
                    response_sha256=F.raw_sha(raw),
                    status="retryable" if code == 429 else "failed",
                )
                if code == 429:
                    delay = headers.get("retry-after", "")
                    need(
                        delay.isdigit() and 0 <= int(delay) <= 86400,
                        "retry_after_required",
                    )
                    op["not_before"] = (
                        self.now + timedelta(seconds=int(delay))
                    ).isoformat()
                self.stop(
                    "source_throttled" if code == 429 else "source_http_rejected",
                    code != 429,
                )
            pin = F.write_once(
                self.root,
                f"response-{len(state['operations']):05d}-{op['attempts']:02d}.bin",
                raw,
            )
            op.update(
                http_status=code, headers=headers, response=pin, status="complete"
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
        return code, headers, F.decode(raw) if raw else None

    def definition(self, label):
        state, request = self.state, self.state["request"]
        key = "definition." + label
        if key in state["jobs"] and state["jobs"][key].get("result"):
            return F.fabric_parts(
                F.decode(F.read_pin(self.root, state["jobs"][key]["result"]))
            )
        code, headers, value = self.json_call(
            key,
            "fabric",
            "POST",
            f"/v1/workspaces/{request['workspace_id']}/reports/{request['report_id']}/getDefinition?format=PBIR",
        )
        if code == 200:
            return F.fabric_parts(value)
        operation_id = headers.get("x-ms-operation-id")
        need(uuid_id(operation_id), "fabric_operation_id_required")
        path = "/v1/operations/" + operation_id
        need(
            headers.get("location") == FABRIC + path,
            "fabric_operation_location_mismatch",
        )
        job = state["jobs"].setdefault(
            key,
            {
                "operation_id": operation_id,
                "polls": 0,
                "request_sha256": state["request_sha256"],
            },
        )
        need(job["operation_id"] == operation_id, "fabric_operation_changed")
        if not job["polls"]:
            delay = headers.get("retry-after", "0")
            need(delay.isdigit() and int(delay) <= 86400, "retry_after_rejected")
            job.setdefault(
                "not_before", (self.now + timedelta(seconds=int(delay))).isoformat()
            )
        if self.now < datetime.fromisoformat(job["not_before"]):
            self.stop("definition_pending")
        if job["polls"] >= request["max_attempts_per_operation"]:
            self.stop("definition_poll_limit", True)
        job["polls"] += 1
        _, poll_headers, result = self.json_call(
            key + ".poll." + str(job["polls"]), "fabric", "GET", path
        )
        need(type(result) is dict, "fabric_status_contract")
        status = result.get("status")
        job["status"] = status
        if status in ("NotStarted", "Running"):
            delay = poll_headers.get("retry-after", "1")
            need(delay.isdigit() and int(delay) <= 86400, "retry_after_rejected")
            job["not_before"] = (self.now + timedelta(seconds=int(delay))).isoformat()
            self.stop("definition_pending")
        if status != "Succeeded":
            self.stop("definition_failed_or_unknown_status", True)
        _, _, raw = self.call(key + ".result", "fabric", "GET", path + "/result")
        job["result"] = next(
            op["response"] for op in state["operations"] if op["key"] == key + ".result"
        )
        return F.fabric_parts(F.decode(raw))

    def export(self, index, view):
        state, request = self.state, self.state["request"]
        key = f"export.{index}"
        if state["jobs"].get(key, {}).get("downloaded"):
            return
        config = {
            "pages": [
                {
                    "pageName": view["page_id"],
                    **({"visualName": view["visual_id"]} if view["visual_id"] else {}),
                }
            ]
        }
        if request["state"]["filters"]:
            config["reportLevelFilters"] = request["state"]["filters"]
        if request["state"]["bookmark"]:
            config["defaultBookmark"] = request["state"]["bookmark"]
        if request["state"]["locale"]:
            config["settings"] = {"locale": request["state"]["locale"]}
        prefix = f"/v1.0/myorg/groups/{request['workspace_id']}/reports/{request['report_id']}"
        code, _, value = self.json_call(
            key,
            "powerbi",
            "POST",
            prefix + "/ExportTo",
            {"format": "PNG", "powerBIReportConfiguration": config},
        )
        need(
            code == 202
            and type(value) is dict
            and value.get("reportId") == request["report_id"],
            "export_identity_mismatch",
        )
        export_id = value.get("id")
        need(
            type(export_id) is str
            and 0 < len(export_id) <= 1000
            and export_id not in (".", "..")
            and not any(ord(c) < 32 for c in export_id),
            "export_id_required",
        )
        job = state["jobs"].setdefault(
            key,
            {
                "export_id": export_id,
                "polls": 0,
                "request_sha256": state["request_sha256"],
                "view": {"page_id": view["page_id"], "visual_id": view["visual_id"]},
            },
        )
        need(job["export_id"] == export_id, "export_job_changed")
        if job.get("not_before") and self.now < datetime.fromisoformat(
            job["not_before"]
        ):
            self.stop("export_pending")
        if job["polls"] >= request["max_attempts_per_operation"]:
            self.stop("export_poll_limit", True)
        job["polls"] += 1
        path = prefix + "/exports/" + quote(export_id, safe="")
        _, headers, result = self.json_call(
            key + ".poll." + str(job["polls"]), "powerbi", "GET", path
        )
        need(
            type(result) is dict
            and result.get("id") == export_id
            and result.get("reportId") == request["report_id"],
            "export_status_identity_mismatch",
        )
        status = result.get("status")
        job["status"] = status
        if status in ("NotStarted", "Running"):
            delay = headers.get("retry-after", "1")
            need(delay.isdigit() and int(delay) <= 86400, "retry_after_rejected")
            job["not_before"] = (self.now + timedelta(seconds=int(delay))).isoformat()
            self.stop("export_pending")
        if status != "Succeeded":
            self.stop("export_failed_or_unknown_status", True)
        if result.get("resourceLocation"):
            need(
                result["resourceLocation"] == POWERBI + path + "/file",
                "export_file_location_mismatch",
            )
        code, headers, raw = self.call(
            key + ".file", "powerbi", "GET", path + "/file", binary=True
        )
        need(
            code == 200
            and headers.get("content-type", "").split(";")[0].lower()
            in ("image/png", "application/zip", "application/octet-stream"),
            "export_media_rejected",
        )
        images = F.image_parts(raw)
        # One exact page/visual per job: arbitrary ZIP contents never gain a guessed visual identity.
        need(len(images) == 1, "single_selected_export_has_ambiguous_images")
        if raw.startswith(b"PK"):
            attachment(
                self.root,
                state,
                raw,
                key + ".zip",
                "zip",
                "application/zip",
                view,
                export_id=export_id,
                members=[
                    {"source_path": p, "sha256": F.raw_sha(b), "bytes": len(b)}
                    for p, b, _ in images
                ],
            )
        name, image, dimensions = images[0]
        attachment(
            self.root,
            state,
            image,
            key + ".png",
            "png",
            "image/png",
            view,
            export_id=export_id,
            source_member=name,
            actual_dimensions=dimensions,
            observed_render_state="unknown",
            result_completeness={"status": "unknown", "reference": None},
        )
        job["downloaded"] = True
        view["status"] = "complete"
        save(self.root, state)


def query_result(value):
    need(type(value) is dict, "query_result_contract")
    if value.get("error") or value.get("errors"):
        return {"status": "partial", "reason": "query_response_error"}
    results = value.get("results")
    need(
        type(results) is list and len(results) == 1 and type(results[0]) is dict,
        "one_query_result_required",
    )
    result = results[0]
    if result.get("error") or result.get("errors"):
        return {"status": "partial", "reason": "query_result_error"}
    tables = result.get("tables")
    need(
        type(tables) is list and len(tables) == 1 and type(tables[0]) is dict,
        "one_query_table_required",
    )
    table = tables[0]
    if table.get("error") or table.get("errors"):
        return {"status": "partial", "reason": "query_table_error"}
    rows = table.get("rows")
    need(
        type(rows) is list
        and len(rows) <= 100000
        and all(type(r) is dict for r in rows),
        "query_rows_rejected",
    )
    values = sum(len(row) for row in rows)
    need(values <= 1000000, "query_values_limit")
    return {
        "status": "unknown",
        "reason": "endpoint_rows_not_independent_completeness_evidence",
        "observed_rows": len(rows),
        "observed_values": values,
    }


def capture(
    request,
    directory,
    *,
    fabric_token=None,
    powerbi_token=None,
    transport=None,
    resume=False,
    allow_source_read=False,
    allow_source_query=False,
    now=None,
):
    need(allow_source_read, "source_read_grant_required")
    request = validate_request(request, require_service=True)
    need(not request["queries"] or allow_source_query, "source_query_grant_required")
    root = F.private_directory(directory)
    now = now or utcnow()
    lock_path = F.no_links(root / ".capture.lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if resume:
            state, output = load_latest(root, request)
        else:
            need(
                not [p for p in root.iterdir() if p.name != ".capture.lock"],
                "new_capture_directory_required",
            )
            state = new_envelope(request, "fixed_rest", now)
            output = save(root, state)
        if state["status"] in ("complete", "blocked"):
            return {"status": state["status"], "output": str(output), "capture": state}
        session = Session(
            root,
            state,
            {"fabric": fabric_token, "powerbi": powerbi_token},
            transport or default_transport,
            now,
        )
        prefix = f"/v1.0/myorg/groups/{request['workspace_id']}/reports/{request['report_id']}"
        try:
            before = {}
            for label, suffix in (("report", ""), ("pages", "/pages")):
                _, _, value = session.json_call(
                    "before." + label, "powerbi", "GET", prefix + suffix
                )
                before[label] = value
            need(
                type(before["report"]) is dict
                and before["report"].get("id") == request["report_id"],
                "report_identity_mismatch",
            )
            if request["dataset_id"]:
                need(
                    before["report"].get("datasetId") == request["dataset_id"],
                    "dataset_binding_mismatch",
                )
            pages = (
                before["pages"].get("value") if type(before["pages"]) is dict else None
            )
            need(
                type(pages) is list
                and len(pages) <= 1000
                and all(type(p) is dict and valid_id(p.get("name")) for p in pages),
                "pages_contract_rejected",
            )
            names = [p["name"] for p in pages]
            need(len(names) == len(set(names)), "duplicate_page_identity")
            need(
                all(v["page_id"] in names for v in request["views"]),
                "selected_page_not_visible",
            )
            state["source"]["metadata_before"] = before
            parts = session.definition("before")
            if not state["source"]["definition_files"]:
                set_definition(root, state, parts)
            else:
                need(
                    state["source"]["definition_fingerprint"]
                    == parts_fingerprint(parts),
                    "definition_changed_on_resume",
                )
            save(root, state)
            for index, view in enumerate(state["captures"]):
                if view["export_png"]:
                    session.export(index, view)
                else:
                    view["gaps"] = ["render_not_requested"]
            for query in request["queries"]:
                if any(
                    a.get("query_id") == query["query_id"] for a in state["attachments"]
                ):
                    continue
                body = {
                    "queries": [{"query": query["query"]}],
                    "serializerSettings": {"includeNulls": True},
                }
                _, _, raw = session.call(
                    "query." + query["query_id"],
                    "powerbi",
                    "POST",
                    "/v1.0/myorg/datasets/" + request["dataset_id"] + "/executeQueries",
                    body,
                )
                quality = query_result(F.decode(raw))
                view = next(
                    v
                    for v in state["captures"]
                    if (v["page_id"], v["visual_id"])
                    == (query["page_id"], query["visual_id"])
                )
                attachment(
                    root,
                    state,
                    raw,
                    "query-" + query["query_id"] + ".json",
                    "json",
                    "application/json",
                    view,
                    query_id=query["query_id"],
                    dataset_id=request["dataset_id"],
                    query_sha256=sha(body),
                    context_reference=query["context_reference"],
                    result_profile="powerbi_execute_queries",
                    result_completeness={**quality, "reference": None},
                    rendered_state_equivalence="not_established",
                )
                if quality["status"] == "partial":
                    state["gaps"].append("query_partial:" + query["query_id"])
                save(root, state)
            after_parts = session.definition("after")
            state["source"]["definition_after_fingerprint"] = parts_fingerprint(
                after_parts
            )
            need(
                state["source"]["definition_fingerprint"]
                == state["source"]["definition_after_fingerprint"],
                "source_definition_changed_during_capture",
            )
            after = {}
            for label, suffix in (("report", ""), ("pages", "/pages")):
                _, _, value = session.json_call(
                    "after." + label, "powerbi", "GET", prefix + suffix
                )
                after[label] = value
            state["source"]["metadata_after"] = after
            need(before == after, "source_metadata_changed_during_capture")
            state["source"]["coherence"] = {
                "configuration": "unchanged_supplied_bracket",
                "data_snapshot": "not_established",
            }
            state["status"] = (
                "partial"
                if any(g.startswith("query_partial:") for g in state["gaps"])
                or any(c["status"] != "complete" for c in state["captures"])
                else "complete"
            )
            state["completion_meaning"] = (
                "requested files acquired and report configuration bracket unchanged; not observed state, security or parity"
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
    for command in ("capture", "import-local", "import-fabric"):
        p = sub.add_parser(command)
        p.add_argument("--request", required=True, type=Path)
        p.add_argument("--directory", required=True, type=Path)
        p.add_argument("--allow-source-read", action="store_true")
        if command == "capture":
            p.add_argument("--allow-source-query", action="store_true")
            p.add_argument("--tokens-stdin", action="store_true")
            p.add_argument("--resume", action="store_true")
        elif command == "import-local":
            p.add_argument("--definition-root", required=True, type=Path)
        else:
            p.add_argument("--response", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        request = F.decode(F.read_file(args.request))
        if args.command == "capture":
            need(args.tokens_stdin, "injected_tokens_stdin_required")
            raw = sys.stdin.buffer.read(40001)
            need(len(raw) <= 40000, "token_input_limit")
            tokens = F.decode(raw)
            need(
                type(tokens) is dict
                and not set(tokens) - {"fabric_token", "powerbi_token"},
                "token_contract_rejected",
            )
            result = capture(
                request,
                args.directory,
                **tokens,
                resume=args.resume,
                allow_source_read=args.allow_source_read,
                allow_source_query=args.allow_source_query,
            )
        elif args.command == "import-local":
            result = import_local(
                request,
                args.definition_root,
                args.directory,
                allow_source_read=args.allow_source_read,
            )
        else:
            result = import_fabric_definition(
                request,
                F.decode(F.read_file(args.response, F.MAX_JSON)),
                args.directory,
                allow_source_read=args.allow_source_read,
            )
        print(encoded({k: result[k] for k in ("status", "output")}).decode())
        return 0
    except (ValueError, OSError, TypeError, KeyError):
        print(
            "Power BI capture rejected; source boundary, grant, file or contract failed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
