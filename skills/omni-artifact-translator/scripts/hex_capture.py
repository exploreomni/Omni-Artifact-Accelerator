#!/usr/bin/env python3
"""Bounded Hex definition/existing-image capture. Never executes project code."""

from __future__ import annotations

import argparse
import base64
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
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


def module(name):
    spec = importlib.util.spec_from_file_location(
        "hex_" + name, Path(__file__).with_name(name + ".py")
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


F = module("powerbi_capture_files")
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST = "hex-visual-capture-request.v1"
ENVELOPE = "hex-visual-capture.v1"
DEFAULT_MAX_REQUESTS = 20
MAX_SOURCE_BYTES = 4_000_000
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
BASE_GAPS = [
    "source_execution_not_performed",
    "principal_not_authenticated_by_capture",
    "requested_state_is_not_observed_state",
    "export_completeness_not_established",
    "native_and_business_acceptance_not_performed",
]


def text(value, maximum=1000):
    return (
        type(value) is str
        and 0 < len(value) <= maximum
        and all(ord(c) >= 32 for c in value)
    )


def uuid(value):
    return type(value) is str and UUID.fullmatch(value) is not None


def local_id(value):
    return (
        type(value) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", value) is not None
    )


def utcnow():
    return datetime.now(timezone.utc)


def validate_request(value, *, require_service=False):
    need(
        type(value) is dict and value.get("schema_version") == REQUEST,
        "hex.request_contract",
    )
    r = copy.deepcopy(value)
    defaults = {
        "exports": [],
        "outputs": [],
        "images": [],
        "expected_manifest": {
            "reference": "not_supplied",
            "objects": [],
            "completeness": "partial",
        },
        "max_requests_per_invocation": DEFAULT_MAX_REQUESTS,
        "max_total_requests": 200,
        "max_total_bytes": 64_000_000,
        "max_response_bytes": 8_000_000,
        "max_elapsed_seconds": 21600,
        "max_attempts_per_operation": 3,
    }
    for k, v in defaults.items():
        r.setdefault(k, v)
    required = {
        "schema_version",
        "capture_id",
        "source_origin",
        "workspace_id",
        "principal_ref",
        "authorization_ref",
        "evidence_mode",
        "route",
        "route_reference",
        "target_surface",
        "state",
    } | set(defaults)
    need(set(r) == required and local_id(r["capture_id"]), "hex.request_fields")
    origin = r["source_origin"]
    if origin is not None:
        p = urlsplit(origin)
        need(
            p.scheme == "https"
            and p.hostname
            and not p.username
            and not p.password
            and p.path == ""
            and not p.query
            and not p.fragment
            and p.port in (None, 443)
            and origin == "https://" + p.netloc,
            "hex.fixed_https_origin_required",
        )
    need(not require_service or origin is not None, "hex.source_origin_required")
    need(r["workspace_id"] is None or text(r["workspace_id"]), "hex.workspace_identity")
    need(
        text(r["principal_ref"]) and text(r["authorization_ref"]),
        "hex.review_references_required",
    )
    need(
        r["evidence_mode"] in ("synthetic_fixture", "manual_transfer", "live_tenant"),
        "hex.evidence_mode",
    )
    need(r["target_surface"] in ("dashboard", "app", "both"), "hex.target_surface")
    need(
        r["route"]
        in (
            "unselected",
            "reuse_existing",
            "omni_semantic_reconstruction",
            "warehouse_first_refactor",
        )
        and (r["route"] == "unselected" or text(r["route_reference"])),
        "hex.route_reference",
    )
    limits = {
        "max_requests_per_invocation": 500,
        "max_total_requests": 2000,
        "max_total_bytes": 256_000_000,
        "max_response_bytes": 8_000_000,
        "max_elapsed_seconds": 86400,
        "max_attempts_per_operation": 10,
    }
    for k, maximum in limits.items():
        need(type(r[k]) is int and 1 <= r[k] <= maximum, "hex.request_budget")
    s = r["state"]
    need(
        type(s) is dict
        and set(s)
        == {
            "state_id",
            "inputs",
            "filters",
            "timezone",
            "locale",
            "principal",
            "data_time_policy",
        }
        and text(s["state_id"])
        and text(s["data_time_policy"]),
        "hex.state_contract",
    )
    for key in ("inputs", "filters"):
        need(
            type(s[key]) is dict
            and len(s[key]) <= 100
            and len(encoded(s[key])) <= 32000,
            "hex.state_values",
        )
    for key in ("timezone", "locale", "principal"):
        need(s[key] is None or text(s[key]), "hex.state_context")
    need(
        type(r["exports"]) is list and 1 <= len(r["exports"]) <= 100, "hex.export_scope"
    )
    names = []
    for e in r["exports"]:
        need(
            type(e) is dict
            and set(e)
            == {"project_id", "version", "expected_source_version_id", "source_path"},
            "hex.export_fields",
        )
        need(e["project_id"] is None or uuid(e["project_id"]), "hex.project_identity")
        need(not require_service or uuid(e["project_id"]), "hex.live_project_identity")
        need(
            e["version"] in ("draft", "latest")
            or (type(e["version"]) is int and e["version"] >= 0),
            "hex.explicit_version",
        )
        need(
            e["expected_source_version_id"] is None
            or uuid(e["expected_source_version_id"]),
            "hex.version_identity",
        )
        F.source_path(e["source_path"])
        need(e["source_path"].endswith(".hex.yaml"), "hex.native_export_filename")
        names.append(e["source_path"])
    path_names(names)
    need(type(r["outputs"]) is list and len(r["outputs"]) <= 200, "hex.output_scope")
    ids = set()
    fields = {
        "output_id",
        "project_id",
        "source_version_id",
        "cell_id",
        "static_id",
        "run_id",
        "source_mode",
        "expected_project_version",
        "identity_reference",
    }
    for o in r["outputs"]:
        need(
            type(o) is dict
            and set(o) == fields
            and local_id(o["output_id"])
            and o["output_id"] not in ids,
            "hex.output_contract",
        )
        ids.add(o["output_id"])
        need(
            all(
                o[k] is None or uuid(o[k])
                for k in (
                    "project_id",
                    "source_version_id",
                    "cell_id",
                    "static_id",
                    "run_id",
                )
            ),
            "hex.output_identity",
        )
        need(
            o["source_mode"] in ("published", "draft", "offline")
            and text(o["identity_reference"])
            and (
                o["expected_project_version"] is None
                or text(o["expected_project_version"])
            ),
            "hex.output_context",
        )
        need(
            any(e["project_id"] == o["project_id"] for e in r["exports"]),
            "hex.output_project_not_selected",
        )
    need(type(r["images"]) is list and len(r["images"]) <= 100, "hex.image_scope")
    seen = set()
    for i in r["images"]:
        need(
            type(i) is dict
            and set(i) == {"output_id", "width", "height", "include_title"}
            and i["output_id"] in ids
            and i["output_id"] not in seen
            and type(i["include_title"]) is bool,
            "hex.image_contract",
        )
        seen.add(i["output_id"])
        need(
            (i["width"] is None and i["height"] is None)
            or all(
                type(i[k]) is int and 100 <= i[k] <= 2000 for k in ("width", "height")
            ),
            "hex.image_dimensions",
        )
        o = next(o for o in r["outputs"] if o["output_id"] == i["output_id"])
        need(
            all(
                uuid(o[k])
                for k in (
                    "project_id",
                    "source_version_id",
                    "cell_id",
                    "static_id",
                    "run_id",
                )
            )
            and text(o["expected_project_version"])
            and o["source_mode"] == "published",
            "hex.existing_published_run_scope_required",
        )
    m = r["expected_manifest"]
    need(
        type(m) is dict
        and set(m) == {"reference", "objects", "completeness"}
        and text(m["reference"])
        and m["completeness"] in ("selected_scope", "partial")
        and type(m["objects"]) is list
        and len(m["objects"]) <= 5000,
        "hex.expected_manifest",
    )
    need(
        all(
            type(o) is dict
            and set(o) == {"object_id", "kind"}
            and text(o["object_id"])
            and text(o["kind"])
            for o in m["objects"]
        )
        and len({o["object_id"] for o in m["objects"]}) == len(m["objects"]),
        "hex.expected_objects",
    )
    F.decode(encoded(r))
    F.secret_check(r)
    return r


def path_names(names):
    prefixes, files = {}, set()
    for name in names:
        F.source_path(name)
        parts = name.split("/")
        key = unicodedata.normalize("NFC", name).casefold()
        need(
            key not in files
            and not any(
                key.startswith(f + "/") or f.startswith(key + "/") for f in files
            ),
            "hex.path_collision",
        )
        for n in range(1, len(parts) + 1):
            prefix = "/".join(parts[:n])
            folded = unicodedata.normalize("NFC", prefix).casefold()
            need(
                folded not in prefixes or prefixes[folded] == prefix,
                "hex.path_collision",
            )
            prefixes[folded] = prefix
        files.add(key)


def read_native(raw):
    """Bounded YAML structure; not publisher-schema or runtime validation."""
    need(type(raw) is bytes and len(raw) <= 2_000_000, "hex.yaml_size")
    try:
        import yaml
    except ImportError:
        raise ValueError("hex.approved_pyyaml_required") from None
    decoded = F.safe_text(raw)
    depth = count = 0
    try:
        for event in yaml.parse(decoded, Loader=yaml.SafeLoader):
            count += 1
            need(
                count <= 50000
                and not isinstance(event, yaml.AliasEvent)
                and not getattr(event, "anchor", None)
                and not getattr(event, "tag", None),
                "hex.yaml_alias_tag_or_size",
            )
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                need(depth <= 28, "hex.yaml_depth")
            if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1

        class Loader(yaml.SafeLoader):
            pass

        def mapping(loader, node, deep=False):
            out = {}
            for k, v in node.value:
                k = loader.construct_object(k, deep=deep)
                need(
                    type(k) is str and k not in out and k != "<<",
                    "hex.yaml_duplicate_key",
                )
                out[k] = loader.construct_object(v, deep=deep)
            return out

        Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        value = yaml.load(decoded, Loader=Loader)
        F.decode(encoded(value))
        F.secret_check(value)
    except (yaml.YAMLError, UnicodeError, TypeError, OverflowError, RecursionError):
        raise ValueError("hex.invalid_yaml") from None
    need(
        type(value) is dict
        and type(value.get("schemaVersion")) is int
        and value["schemaVersion"] == 3
        and type(value.get("meta")) is dict,
        "hex.schema_v3_structure_required",
    )
    for key in ("projectId", "sourceVersionId"):
        need(
            value["meta"].get(key) is None or uuid(value["meta"][key]),
            "hex.invalid_native_identity",
        )
    cells = value.get("cells", [])
    need(
        type(cells) is list
        and len(cells) <= 2000
        and all(
            type(c) is dict
            and text(c.get("cellType"))
            and type(c.get("config")) is dict
            and (c.get("cellId") is None or uuid(c["cellId"]))
            for c in cells
        ),
        "hex.cells_structure",
    )
    generated = value.get("genAppFiles", [])
    need(type(generated) is list and len(generated) <= 200, "hex.generated_file_limit")
    path_names([g.get("path") for g in generated if type(g) is dict])
    for g in generated:
        need(
            type(g) is dict
            and set(g) == {"path", "contents"}
            and type(g["contents"]) is str,
            "hex.generated_file_contract",
        )
        need(not g["path"].startswith("app/"), "hex.generated_path_relative_to_app")
        F.safe_text(g["contents"].encode())
    for assets in (value.get("projectAssets", {}), value.get("sharedAssets", {})):
        need(type(assets) is dict, "hex.assets_structure")
        for env in assets.get("envVars", []):
            need(
                type(env) is dict
                and not (
                    re.search(
                        r"(?i)token|password|secret|credential|api.?key",
                        str(env.get("name", "")),
                    )
                    and env.get("value")
                ),
                "hex.credential_environment_value",
            )
    return value


def definition_fingerprint(files):
    return sha(
        sorted(
            [{k: f[k] for k in ("source_path", "sha256", "bytes")} for f in files],
            key=lambda f: f["source_path"],
        )
    )


def runtime():
    return {
        name: F.raw_sha(Path(__file__).with_name(name).read_bytes())
        for name in ("hex_capture.py", "hex_visual.py", "powerbi_capture_files.py")
    }


def new_envelope(request, mode, now):
    return {
        "schema_version": ENVELOPE,
        "capture_id": request["capture_id"],
        "request": request,
        "request_sha256": sha(request),
        "created_at": now.isoformat(),
        "producer": {"name": "oaa-hex-capture", "mode": mode, "runtime": runtime()},
        "source": {
            "definition_files": [],
            "definition_fingerprint": definition_fingerprint([]),
            "projects": [],
            "identity": {
                k: request[k]
                for k in ("source_origin", "workspace_id", "principal_ref")
            },
            "state_observation": {"status": "unknown"},
            "state_observations": [],
            "render_state_observations": [],
            "metadata_before": {},
            "metadata_after": {},
            "runs": {},
        },
        "attachments": [],
        "operations": [],
        "budget": {"requests": 0, "response_bytes": 0, "unmeasured_reserved_bytes": 0},
        "status": "partial",
        "gaps": list(BASE_GAPS),
        "journal_revision": 0,
        "previous_content_hash": None,
        "source_execution": False,
        "target_write_authority": False,
        "native_validation": "not_performed",
        "business_acceptance": "not_assessed",
    }


def save(root, value):
    value["source"]["identity"]["principal_verification"] = "supplied_unverified"
    value["previous_content_hash"] = value.pop("content_hash", None)
    value["journal_revision"] += 1
    value["gaps"] = list(dict.fromkeys(value["gaps"]))
    value["content_hash"] = sha(value)
    return (
        root
        / F.write_once(
            root,
            f"capture-{value['journal_revision']:06d}.json",
            encoded(value) + b"\n",
        )["path"]
    )


def add_definition(root, value, name, raw):
    files = value["source"]["definition_files"]
    existing = [f for f in files if f["source_path"] == name]
    if existing:
        need(existing[0]["sha256"] == F.raw_sha(raw), "hex.definition_changed")
        return
    path_names([f["source_path"] for f in files] + [name])
    need(
        len(files) < 256
        and sum(f["bytes"] for f in files) + len(raw) <= MAX_SOURCE_BYTES,
        "hex.definition_size_limit",
    )
    content = F.safe_text(raw)
    native = read_native(raw) if name.endswith(".hex.yaml") else None
    if name.endswith(".json"):
        F.secret_check(F.decode(raw))
    if native is not None:
        selected = [e for e in value["request"]["exports"] if e["source_path"] == name]
        need(len(selected) == 1, "hex.unselected_export")
        e, meta = selected[0], native["meta"]
        need(
            e["project_id"] in (None, meta.get("projectId"))
            and e["expected_source_version_id"] in (None, meta.get("sourceVersionId")),
            "hex.export_identity_mismatch",
        )
        value["source"]["projects"].append(
            {
                "source_path": name,
                "project_id": meta.get("projectId"),
                "source_version_id": meta.get("sourceVersionId"),
                "hex_type": meta.get("hexType"),
                "definition_sha256": F.raw_sha(raw),
            }
        )
        if not meta.get("projectId") or not meta.get("sourceVersionId"):
            value["gaps"].append("native_project_or_version_identity_missing:" + name)
    pin = F.write_once(root, f"definition-{len(files):04d}.bin", raw)
    files.append({**pin, "source_path": name, "content_utf8": content})
    value["source"]["definition_fingerprint"] = definition_fingerprint(files)


def output_definition(value, output):
    matches = []
    for f in value["source"]["definition_files"]:
        if not f["source_path"].endswith(".hex.yaml"):
            continue
        native = read_native(f["content_utf8"].encode())
        if (
            native["meta"].get("projectId") == output["project_id"]
            and native["meta"].get("sourceVersionId") == output["source_version_id"]
        ):
            matches.extend(
                (f, c)
                for c in native.get("cells", [])
                if c.get("cellId") == output["cell_id"]
            )
    need(len(matches) == 1, "hex.output_native_crosswalk_unresolved")
    return matches[0]


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read, "hex.source_read_grant_required")
    request = validate_request(request)
    source_root = F.no_links(source_root)
    need(
        source_root.is_dir()
        and source_root != Path(directory).absolute()
        and source_root not in Path(directory).absolute().parents,
        "hex.source_directory_rejected",
    )
    parts = []
    for current, dirs, names in os.walk(source_root, followlinks=False):
        need(
            all(not (Path(current) / d).is_symlink() for d in dirs),
            "hex.source_symlink",
        )
        for name in sorted(names):
            path = Path(current) / name
            relative = path.relative_to(source_root).as_posix()
            need(len(parts) < 256, "hex.file_limit")
            raw = F.read_file(path)
            need(
                sum(len(p[1]) for p in parts) + len(raw) <= MAX_SOURCE_BYTES,
                "hex.definition_size_limit",
            )
            parts.append((relative, raw))
    path_names([p[0] for p in parts])
    need(
        set(e["source_path"] for e in request["exports"]) <= {p[0] for p in parts},
        "hex.selected_export_missing",
    )
    root = F.private_directory(directory)
    need(not list(root.iterdir()), "hex.new_capture_directory_required")
    value = new_envelope(request, "supplied_files", utcnow())
    for name, raw in sorted(parts):
        add_definition(root, value, name, raw)
    value["gaps"].append("supplied_files_not_authenticated")
    path = save(root, value)
    return {"status": value["status"], "output": str(path), "capture": value}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("hex.redirect_rejected")


def default_transport(method, url, token, body, maximum, timeout):
    need(
        threading.current_thread() is threading.main_thread()
        and signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
        "hex.deadline_context",
    )
    previous = signal.getsignal(signal.SIGALRM)

    def expired(*_):
        raise TimeoutError("hex.deadline")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        req = Request(
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
            response = build_opener(ProxyHandler({}), NoRedirect()).open(
                req, timeout=timeout
            )
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(maximum + 1)
            need(len(raw) <= maximum, "hex.response_size_limit")
            headers = {
                k.lower(): v
                for k, v in response.headers.items()
                if k.lower()
                in ("content-type", "content-length", "retry-after", "location")
            }
            if "content-length" in headers:
                need(
                    headers["content-length"].isdigit()
                    and int(headers["content-length"]) == len(raw),
                    "hex.incomplete_response",
                )
            return response.status, headers, raw
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def operation_plan(request):
    result = {}
    for n, e in enumerate(request["exports"]):
        for phase in ("before", "after"):
            result[f"metadata.{n}.{phase}"] = (
                "GET",
                "/api/v1/projects/" + e["project_id"],
                None,
            )
            result[f"export.{n}.{phase}"] = (
                "POST",
                "/api/v1/projects/export",
                {"projectId": e["project_id"], "version": e["version"]},
            )
    for i in request["images"]:
        o = next(o for o in request["outputs"] if o["output_id"] == i["output_id"])
        path = "/api/v1/projects/" + o["project_id"] + "/runs/" + o["run_id"]
        result["run." + o["output_id"]] = ("GET", path, None)
        params = {"includeTitle": str(i["include_title"]).lower()}
        if i["width"] is not None:
            params.update(width=i["width"], height=i["height"])
        result["image." + o["output_id"]] = (
            "GET",
            path + "/cells/" + o["static_id"] + "/image?" + urlencode(params),
            None,
        )
    return result


class StopCapture(Exception):
    pass


class Session:
    def __init__(self, root, value, token, transport, now):
        self.root, self.value, self.token, self.transport, self.now = (
            root,
            value,
            token,
            transport,
            now,
        )
        self.count, self.started = 0, time.monotonic()

    def stop(self, reason, blocked=False):
        self.value["status"] = "blocked" if blocked else "partial"
        self.value["gaps"].append(reason)
        save(self.root, self.value)
        raise StopCapture(reason)

    def call(self, key):
        v, r = self.value, self.value["request"]
        need(key in operation_plan(r), "hex.operation_not_allowed")
        method, path, payload = operation_plan(r)[key]
        body = None if payload is None else encoded(payload)
        pin = sha({"method": method, "path": path, "body": payload})
        old = [o for o in v["operations"] if o["key"] == key]
        op = old[0] if old else None
        if op:
            need(op["operation_sha256"] == pin, "hex.operation_changed")
            if op["status"] == "complete":
                return F.decode(F.read_pin(self.root, op["response"]))
            if op["status"] != "retryable":
                self.stop("hex.unresolved_operation_no_replay", True)
            if self.now < datetime.fromisoformat(op["not_before"]):
                self.stop("hex.retry_after_not_elapsed")
            if op["attempts"] >= r["max_attempts_per_operation"]:
                self.stop("hex.attempt_limit", True)
        age = (
            (self.now - datetime.fromisoformat(v["created_at"])).total_seconds()
            + time.monotonic()
            - self.started
        )
        if age < 0 or age >= r["max_elapsed_seconds"]:
            self.stop("hex.age_limit", True)
        if self.count >= r["max_requests_per_invocation"]:
            self.stop("hex.invocation_budget")
        if v["budget"]["requests"] >= r["max_total_requests"]:
            self.stop("hex.total_request_budget", True)
        maximum = min(
            r["max_response_bytes"],
            r["max_total_bytes"]
            - v["budget"]["response_bytes"]
            - v["budget"]["unmeasured_reserved_bytes"],
        )
        if maximum <= 0:
            self.stop("hex.byte_budget", True)
        if op is None:
            op = {
                "key": key,
                "operation_sha256": pin,
                "method": method,
                "path": path,
                "body": payload,
                "attempts": 0,
            }
            v["operations"].append(op)
        op.update(status="intent", attempts=op["attempts"] + 1)
        v["budget"]["requests"] += 1
        self.count += 1
        save(self.root, v)
        try:
            code, headers, raw = self.transport(
                method,
                r["source_origin"] + path,
                self.token,
                body,
                maximum,
                min(30, r["max_elapsed_seconds"] - age),
            )
            need(
                type(code) is int
                and type(raw) is bytes
                and len(raw) <= maximum
                and type(headers) is dict,
                "hex.transport_contract",
            )
            headers = {k.lower(): val for k, val in headers.items()}
            need(
                all(type(k) is str and text(val, 4096) for k, val in headers.items()),
                "hex.headers_rejected",
            )
            need(
                "location" not in headers
                and self.token.encode() not in raw
                and self.token not in str(headers),
                "hex.redirect_or_token_echo",
            )
            v["budget"]["response_bytes"] += len(raw)
            if code != 200:
                op.update(
                    status="failed", http_status=code, response_sha256=F.raw_sha(raw)
                )
                if code == 429:
                    delay = headers.get("retry-after", "")
                    need(
                        delay.isdigit() and int(delay) <= 86400,
                        "hex.retry_after_required",
                    )
                    op.update(
                        status="retryable",
                        not_before=(
                            self.now + timedelta(seconds=int(delay))
                        ).isoformat(),
                    )
                self.stop("hex.source_http_" + str(code), code != 429)
            need(
                headers.get("content-type", "").split(";")[0].strip().lower()
                == "application/json",
                "hex.json_media_required",
            )
            result = F.decode(raw)
            F.secret_check(result)
            F.safe_text(raw)
            need(
                type(result) is dict and self.token not in encoded(result).decode(),
                "hex.invalid_response_or_token_echo",
            )
            if key.startswith("export."):
                need(type(result.get("content")) is str, "hex.export_content_required")
                read_native(result["content"].encode())
            op.update(
                status="complete",
                http_status=code,
                response=F.write_once(
                    self.root,
                    f"response-{len(v['operations']):04d}-{op['attempts']}.json",
                    raw,
                ),
            )
            save(self.root, v)
            return result
        except StopCapture:
            raise
        except Exception:
            op["status"] = "ambiguous"
            v["budget"]["unmeasured_reserved_bytes"] += maximum
            self.stop("hex.response_or_transport_unresolved", True)


def run_image(raw, output, dimensions):
    value = F.decode(raw) if type(raw) is bytes else raw
    need(
        type(value) is dict
        and all(
            value.get(k) == output[v]
            for k, v in (
                ("projectId", "project_id"),
                ("runId", "run_id"),
                ("staticId", "static_id"),
            )
        ),
        "hex.image_identity",
    )
    need(
        value.get("mimeType") == "image/png" and type(value.get("imageBase64")) is str,
        "hex.image_media",
    )
    try:
        data = base64.b64decode(value["imageBase64"], validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError("hex.invalid_image_base64") from None
    info = F.png_info(data)
    if dimensions["width"] is not None:
        need(
            info["width"] == dimensions["width"]
            and info["height"] == dimensions["height"],
            "hex.image_dimension_mismatch",
        )
    return data


def capture(
    request,
    directory,
    *,
    token=None,
    transport=None,
    resume=False,
    allow_source_read=False,
    now=None,
):
    need(allow_source_read, "hex.source_read_grant_required")
    request = validate_request(request, require_service=True)
    need(
        type(token) is str
        and 8 <= len(token) <= 16384
        and re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token),
        "hex.injected_token_required",
    )
    root = F.private_directory(directory)
    lock = os.open(root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = now or utcnow()
        if resume:
            value, path = load_latest(root)
            need(
                value["request"] == request
                and value["producer"]["runtime"] == runtime(),
                "hex.request_or_runtime_changed",
            )
        else:
            need(
                set(p.name for p in root.iterdir()) == {".lock"},
                "hex.new_capture_directory_required",
            )
            value = new_envelope(request, "rest", now)
            path = save(root, value)
        if value["status"] == "complete":
            return {"status": value["status"], "output": str(path), "capture": value}
        if value["status"] == "blocked":
            return {"status": value["status"], "output": str(path), "capture": value}
        session = Session(root, value, token, transport or default_transport, now)
        try:
            for n, e in enumerate(request["exports"]):
                metadata = session.call(f"metadata.{n}.before")
                need(metadata.get("id") == e["project_id"], "hex.metadata_identity")
                value["source"]["metadata_before"][e["source_path"]] = metadata
                data = session.call(f"export.{n}.before")
                F.source_path(data.get("filename"))
                add_definition(root, value, e["source_path"], data["content"].encode())
                save(root, value)
            for image in request["images"]:
                output = next(
                    o
                    for o in request["outputs"]
                    if o["output_id"] == image["output_id"]
                )
                _, cell = output_definition(value, output)
                need(
                    cell["cellType"] in ("CHART", "CHARTV2"), "hex.chart_cell_required"
                )
                run = session.call("run." + output["output_id"])
                need(
                    run.get("projectId") == output["project_id"]
                    and run.get("runId") == output["run_id"]
                    and str(run.get("projectVersion"))
                    == output["expected_project_version"]
                    and run.get("status") == "COMPLETED"
                    and text(run.get("startTime"))
                    and text(run.get("endTime")),
                    "hex.completed_run_identity_required",
                )
                value["source"]["runs"][output["output_id"]] = run
                response = session.call("image." + output["output_id"])
                raw = run_image(response, output, image)
                if not any(
                    a.get("output_id") == output["output_id"] and a["format"] == "png"
                    for a in value["attachments"]
                ):
                    pin = F.write_once(
                        root, "image-" + output["output_id"] + ".png", raw
                    )
                    value["attachments"].append(
                        {
                            **pin,
                            **output,
                            "format": "png",
                            "media_type": "image/png",
                            "state_sha256": sha(request["state"]),
                            "request_sha256": value["request_sha256"],
                            "provenance_reference": "retained_api_image_response",
                            "acquisition": "completed_run_api",
                            "result_completeness": {
                                "status": "unknown",
                                "reference": None,
                                "flags": [],
                            },
                        }
                    )
                save(root, value)
            for n, e in enumerate(request["exports"]):
                metadata = session.call(f"metadata.{n}.after")
                need(metadata.get("id") == e["project_id"], "hex.metadata_identity")
                value["source"]["metadata_after"][e["source_path"]] = metadata
                after = session.call(f"export.{n}.after")
                before = next(
                    f
                    for f in value["source"]["definition_files"]
                    if f["source_path"] == e["source_path"]
                )
                need(
                    F.raw_sha(after["content"].encode()) == before["sha256"],
                    "hex.definition_changed",
                )
                for key in ("id", "lastEditedAt", "lastPublishedAt"):
                    need(
                        metadata.get(key)
                        == value["source"]["metadata_before"][e["source_path"]].get(
                            key
                        ),
                        "hex.metadata_changed",
                    )
            value["status"] = "complete"
            path = save(root, value)
        except StopCapture:
            path = sorted(root.glob("capture-*.json"))[-1]
        except (ValueError, KeyError, TypeError):
            value["status"] = "blocked"
            value["gaps"].append("source_identity_shape_or_coherence_unresolved")
            path = save(root, value)
        return {"status": value["status"], "output": str(path), "capture": value}
    finally:
        os.close(lock)


def check_capture(path):
    path = F.no_links(path)
    value = F.decode(F.read_file(path, F.MAX_JSON))
    module("hex_visual").verify_capture_files(value, path.parent)
    return value


def load_latest(root):
    paths = sorted(root.glob("capture-*.json"))
    need(paths and len(paths) <= 20000, "hex.journal_required")
    previous = None
    for n, path in enumerate(paths, 1):
        v = F.decode(F.read_file(path, F.MAX_JSON))
        need(
            path.name == f"capture-{n:06d}.json"
            and v["journal_revision"] == n
            and v["previous_content_hash"] == previous
            and v["content_hash"]
            == sha({k: v for k, v in v.items() if k != "content_hash"}),
            "hex.journal_changed",
        )
        previous = v["content_hash"]
    return check_capture(paths[-1]), paths[-1]


def import_evidence(capture_path, spec, source_root):
    capture_path = F.no_links(capture_path)
    root = capture_path.parent
    lock = os.open(root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        value, latest = load_latest(root)
        need(value["producer"]["runtime"] == runtime(), "hex.runtime_changed")
        need(
            latest == capture_path
            and type(spec) is dict
            and set(spec)
            == {
                "schema_version",
                "kind",
                "capture_content_hash",
                "attachments",
                "state_observations",
                "render_state_observations",
            }
            and spec["schema_version"] == 1
            and spec["kind"] == "hex_evidence_import"
            and spec["capture_content_hash"] == value["content_hash"],
            "hex.evidence_import_baseline",
        )
        need(
            type(spec["attachments"]) is list and len(spec["attachments"]) <= 200,
            "hex.evidence_count",
        )
        F.secret_check(spec)
        source_root = F.no_links(source_root)
        outputs = {o["output_id"]: o for o in value["request"]["outputs"]}
        pending = []

        # Stage and validate every byte/declaration before writing any evidence.
        def stage(raw, suffix, scope):
            name = "evidence-" + F.raw_sha(scope.encode() + b"\0" + raw) + "." + suffix
            pending.append((name, raw))
            return {"path": name, "sha256": F.raw_sha(raw), "bytes": len(raw)}

        for row in spec["attachments"]:
            need(
                type(row) is dict
                and set(row)
                == {
                    "output_id",
                    "path",
                    "format",
                    "provenance_reference",
                    "result_completeness",
                }
                and row["output_id"] in outputs
                and text(row["provenance_reference"]),
                "hex.evidence_attachment",
            )
            output = outputs[row["output_id"]]
            output_definition(value, output)
            F.source_path(row["path"])
            raw = F.read_file(source_root / row["path"])
            kind = row["format"]
            need(
                kind in ("csv", "json", "png", "mcp-image", "pdf"),
                "hex.evidence_format",
            )
            original = None
            if kind == "mcp-image":
                need(output["source_mode"] == "draft", "hex.mcp_image_is_draft_only")
                response = F.decode(raw)
                F.secret_check(response)
                need(
                    type(response) is dict
                    and response.get("isError") is not True
                    and type(response.get("content")) is list,
                    "hex.mcp_response",
                )
                images = [
                    c
                    for c in response["content"]
                    if type(c) is dict and c.get("type") == "image"
                ]
                need(
                    len(images) == 1 and images[0].get("mimeType") == "image/png",
                    "hex.mcp_png_required",
                )
                original = stage(raw, "mcp.json", output["output_id"])
                raw = base64.b64decode(images[0]["data"], validate=True)
                kind = "png"
            if kind == "png":
                F.png_info(raw)
            elif kind == "pdf":
                need(raw.startswith(b"%PDF-"), "hex.pdf_signature")
            else:
                F.safe_text(raw)
                if kind == "json":
                    F.secret_check(F.decode(raw))
            pin = stage(raw, kind, output["output_id"])
            need(
                not any(a["path"] == pin["path"] for a in value["attachments"]),
                "hex.duplicate_evidence_attachment",
            )
            value["attachments"].append(
                {
                    **pin,
                    **output,
                    "format": kind,
                    "media_type": {
                        "png": "image/png",
                        "pdf": "application/pdf",
                        "csv": "text/csv",
                        "json": "application/json",
                    }[kind],
                    "request_sha256": value["request_sha256"],
                    "state_sha256": sha(value["request"]["state"]),
                    "provenance_reference": row["provenance_reference"],
                    "result_completeness": row["result_completeness"],
                    "acquisition": "transferred_mcp_image"
                    if original
                    else "supplied_file",
                    "original_response": original,
                }
            )
        need(
            sum(len(raw) for _, raw in pending) <= MAX_SOURCE_BYTES,
            "hex.evidence_batch_size",
        )
        all_pins = (
            value["source"]["definition_files"]
            + value["attachments"]
            + [
                a["original_response"]
                for a in value["attachments"]
                if a.get("original_response")
            ]
            + [o["response"] for o in value["operations"] if o.get("response")]
        )
        need(
            sum(p["bytes"] for p in all_pins) <= value["request"]["max_total_bytes"],
            "hex.evidence_total_size",
        )
        for key in ("state_observations", "render_state_observations"):
            need(
                type(spec[key]) is list and len(spec[key]) <= 200,
                "hex.observation_count",
            )
            value["source"][key].extend(copy.deepcopy(spec[key]))
        previous_hash = value["content_hash"]
        value["content_hash"] = sha(
            {k: v for k, v in value.items() if k != "content_hash"}
        )
        module("hex_visual").validate_capture(value)
        value["content_hash"] = previous_hash
        for name, raw in pending:
            if (root / name).exists():
                need(F.read_file(root / name) == raw, "hex.immutable_evidence_changed")
            else:
                F.write_once(root, name, raw)
        path = save(root, value)
        return {"status": value["status"], "output": str(path), "capture": value}
    finally:
        os.close(lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "import-local"):
        sub = commands.add_parser(name)
        sub.add_argument("--request", required=True)
        sub.add_argument("--directory", required=True)
        sub.add_argument("--allow-source-read", action="store_true")
        if name == "capture":
            sub.add_argument("--resume", action="store_true")
            sub.add_argument("--token-stdin", action="store_true")
        else:
            sub.add_argument("--source-root", required=True)
    sub = commands.add_parser("check")
    sub.add_argument("--capture", required=True)
    sub = commands.add_parser("import-evidence")
    sub.add_argument("--capture", required=True)
    sub.add_argument("--spec", required=True)
    sub.add_argument("--source-root", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            value = check_capture(args.capture)
            result = {
                "status": value["status"],
                "output": str(F.no_links(args.capture)),
            }
        elif args.command == "import-evidence":
            result = import_evidence(
                args.capture, F.decode(F.read_file(args.spec)), args.source_root
            )
        else:
            request = F.decode(F.read_file(args.request))
            if args.command == "capture":
                need(args.token_stdin, "hex.token_stdin_required")
                token = sys.stdin.buffer.read(16385).decode("ascii")
                result = capture(
                    request,
                    args.directory,
                    token=token,
                    resume=args.resume,
                    allow_source_read=args.allow_source_read,
                )
            else:
                result = import_local(
                    request,
                    args.source_root,
                    args.directory,
                    allow_source_read=args.allow_source_read,
                )
        print(encoded({k: result[k] for k in ("status", "output")}).decode())
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print('{"status":"rejected","error":"hex_capture_contract_or_io_failure"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
