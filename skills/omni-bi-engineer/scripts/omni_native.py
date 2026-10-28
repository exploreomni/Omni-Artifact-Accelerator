#!/usr/bin/env python3
"""Bounded, evidence-pinned editing of one existing Omni development draft.

No create/publish/delete/model mutation or arbitrary command/URL surface is exposed.
Local ownership and approval records trust the operating-system account. A remote
host must authenticate its user and supply its own exact-candidate authorization.
See ../references/omni-build-export.md for the inspected vendor contracts.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zlib
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

CONTRACT = "oaa-omni-native-v1"
MAX_JSON = 8 * 1024 * 1024
MAX_FILE = 32 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA_SOURCES = [
    "https://docs.omni.co/api/documents-v2/patch-draft",
    "https://docs.omni.co/api/documents-v2/create-draft-and-patch-document",
    "https://docs.omni.co/api/documents-v2/get-draft-state",
    "https://docs.omni.co/api/documents/list-document-drafts",
    "https://docs.omni.co/api/who-am-i/get-current-identity-and-permissions",
    "https://docs.omni.co/api/dashboard-downloads/initiate-download",
    "https://docs.omni.co/api/dashboard-downloads/check-download-status",
    "https://docs.omni.co/api/dashboard-downloads/download-file",
    "https://docs.omni.co/api/models/list-models",
    "https://docs.omni.co/api/models/get-model-yaml",
    "https://docs.omni.co/api/topics/retrieve-a-topic",
]


def _workflow_module():
    """Load package-owned validation, never engagement code or a caller module."""
    directory = Path(__file__).resolve().parents[2] / "omni-artifact-accelerator/scripts"
    spec = importlib.util.spec_from_file_location("oaa_native_project", directory / "analyst_project.py")
    project = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(project)
    spec = importlib.util.spec_from_file_location("oaa_native_visual_workflow", directory / "visual_workflow.py")
    workflow = importlib.util.module_from_spec(spec)
    # visual_workflow has one package-local import. Supply exactly that file,
    # restore any host module alias immediately, and retain its module object.
    previous = sys.modules.get("analyst_project")
    sys.modules["analyst_project"] = project
    try:
        spec.loader.exec_module(workflow)
    finally:
        if previous is None:
            del sys.modules["analyst_project"]
        else:
            sys.modules["analyst_project"] = previous
    return workflow


WORKFLOW = _workflow_module()

_process_spec = importlib.util.spec_from_file_location("oaa_cli_process", Path(__file__).with_name("cli_process.py"))
CLI_PROCESS = importlib.util.module_from_spec(_process_spec)
_process_spec.loader.exec_module(CLI_PROCESS)


def _standalone_module():
    directory = Path(__file__).resolve().parents[2] / "omni-backend-handoff/scripts"
    spec = importlib.util.spec_from_file_location("oaa_native_standalone", directory / "standalone.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeError(ValueError):
    """A bounded operation rejected, failed, or needs reconciliation."""


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def export_identity(operation):
    """Audit labels and local filename aliases are not permission to repeat a job."""
    return {"candidate_sha256": operation["candidate_sha256"], "target": operation["target"],
            "request": operation["request"], "readback_sha256": operation["readback_sha256"]}


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise NativeError("Duplicate JSON key")
            result[key] = value
        return result
    if len(raw) > MAX_JSON:
        raise NativeError("JSON exceeds bounded size")
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(NativeError("Non-finite JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise NativeError("Invalid JSON response/file") from exc


def require_id(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise NativeError(f"Invalid {label}")
    return value


@dataclass(frozen=True)
class TargetConfig:
    base_url: str
    profile: str
    document_id: str
    draft_id: str
    model_id: str
    principal_id: str
    branch_id: str | None
    token_env: str = "OMNI_API_TOKEN"

    def __post_init__(self):
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.port not in (None, 443) or self.base_url.endswith("/")):
            raise NativeError("base_url must be an explicit HTTPS origin without a trailing slash")
        for field in ("profile", "document_id", "draft_id", "model_id", "principal_id"):
            require_id(getattr(self, field), field)
        if self.branch_id is not None:
            require_id(self.branch_id, "branch_id")
        if self.document_id == self.draft_id:
            raise NativeError("Document and draft identifiers must differ")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", self.token_env):
            raise NativeError("Invalid token environment variable name")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NativeError("Redirect refused; credentials never follow another URL")


def default_http(method, url, token, body=None, max_bytes=MAX_JSON):
    """Only called with internally constructed, fixed routes at the configured origin."""
    request = Request(url, data=encoded(body) if body is not None else None, method=method,
                      headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        response = build_opener(NoRedirect()).open(request, timeout=45)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise NativeError("HTTP response exceeds bounded size")
        return response.status, dict(response.headers), raw


def _container_nodes(containers):
    nodes = {}
    def visit(value):
        if isinstance(value, dict):
            if "instanceKey" in value:
                key = value["instanceKey"]
                require_id(key, "container instanceKey")
                if key in nodes:
                    raise NativeError("Duplicate container instanceKey")
                nodes[key] = value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(containers)
    return nodes


def _container_shape(value, root=True):
    if isinstance(value, dict):
        if not root and "instanceKey" in value:
            return {"instanceKey": value["instanceKey"]}
        return {key: _container_shape(item, False) for key, item in value.items()}
    if isinstance(value, list):
        return [_container_shape(item, False) for item in value]
    return value


def _container_placements(containers):
    placements, order = {}, {}
    def visit(value, path):
        if isinstance(value, dict):
            if "instanceKey" in value:
                key = value["instanceKey"]
                placements[key] = path
                order.setdefault(path, []).append(key)
                path = (*path, "@" + key)
            for field, item in value.items():
                visit(item, (*path, field))
        elif isinstance(value, list):
            for item in value:
                visit(item, path)
    visit(containers, ("containers",))
    return placements, order


def validate_ownership(ownership):
    fields = {"query_keys", "control_ids", "container_keys", "settings", "metadata", "tab_order", "control_order"}
    if not isinstance(ownership, dict) or set(ownership) != fields:
        raise NativeError("Ownership requires query_keys, control_ids, container_keys, settings, metadata, tab_order, control_order")
    for field in fields - {"tab_order", "control_order"}:
        if (not isinstance(ownership[field], list) or any(not isinstance(x, str) for x in ownership[field])
                or len(set(ownership[field])) != len(ownership[field])):
            raise NativeError("Ownership entries must be unique strings")
    if any(not re.fullmatch(r"[1-9][0-9]*", key) for key in ownership["query_keys"]):
        raise NativeError("Query keys must be positive-integer strings")
    if set(ownership["metadata"]) - {"name", "description"}:
        raise NativeError("Only name and description metadata are editable")
    for field in ("tab_order", "control_order"):
        if type(ownership[field]) is not bool:
            raise NativeError("Order ownership must be boolean")


def expected_state(before, payload, ownership):
    """Interpret documented PATCH merge rules, without inventing chart grammars."""
    validate_ownership(ownership)
    allowed = {"name", "description", "summary", "queryPresentations", "controls", "settings", "containers"}
    if not isinstance(payload, dict) or not payload or set(payload) - allowed:
        raise NativeError("Unsupported top-level PATCH fields; model/app/branch mutations are excluded")
    result = copy.deepcopy(before)
    for field in ("name", "description"):
        if field in payload:
            if field not in ownership["metadata"]:
                raise NativeError("Unowned document metadata")
            if not (isinstance(payload[field], str) or (field == "description" and payload[field] is None)):
                raise NativeError("Invalid document metadata")
            if field == "name" and not 1 <= len(payload[field]) <= 254:
                raise NativeError("Document name outside API cap")
            result[field] = payload[field]
    if "summary" in payload and (not isinstance(payload["summary"], str) or not 1 <= len(payload["summary"]) <= 255):
        raise NativeError("Summary outside API cap")
    for section, owned, order_owned in (("queryPresentations", "query_keys", "tab_order"),
                                         ("controls", "control_ids", "control_order")):
        if section not in payload:
            continue
        patch = payload[section]
        if not isinstance(patch, dict) or set(patch) - {"data", "order"}:
            raise NativeError("Unsupported content-section shape")
        data = patch.get("data", {})
        if not isinstance(data, dict) or set(data) - set(ownership[owned]):
            raise NativeError("PATCH changes unowned content")
        if section == "queryPresentations" and sum(value is not None for value in data.values()) > 48:
            raise NativeError("At most 48 non-null query presentations per PATCH")
        dest = result.setdefault(section, {"data": {}, "order": []})
        for key, value in data.items():
            if value is None:
                dest["data"].pop(key, None)
                continue
            if not isinstance(value, dict):
                raise NativeError("Tile/control must be an object")
            if section == "queryPresentations":
                if value.get("type") not in {"query", "blank", "linked"}:
                    raise NativeError("Only reviewed semantic query, blank and linked presentations are supported")
                if set(value) & {"model_extension_id", "foreignModelId", "fileUploadId", "miniUuid", "editingModelObjectName", "editingModelObjectNameChange"}:
                    raise NativeError("Read-only/model/source mutation fields are excluded")
                query = value.get("query")
                if value.get("isSql") is True or (isinstance(query, dict) and set(query) & {"sql", "rawSql", "raw_sql"}):
                    raise NativeError("Raw SQL presentations require a separately qualified path")
                if query is not None and (not isinstance(query, dict) or set(query) & {"modelId", "model_id", "branchId"}):
                    raise NativeError("Query model/branch must remain anchored to the selected draft")
                # Existing foreign/source/model-editor tabs cannot be converted through this helper.
                old = before.get(section, {}).get("data", {}).get(key)
                if old and old.get("type") not in {"query", "blank", "linked"}:
                    raise NativeError("Existing tab requires an unsupported conversion")
                # The API merges presentation keys, not fields inside a presentation.
                # A title-only replacement otherwise silently resets its query.
                if value.get("type") == "query":
                    if not isinstance(query, dict) or not isinstance(query.get("fields"), list) or not query["fields"]:
                        raise NativeError("Query presentation replacement requires its complete query and fields")
                    old_query = old.get("query") if old else None
                    if isinstance(old_query, dict) and set(old_query) - set(query):
                        raise NativeError("Query replacement omitted existing properties; retain explicit filters, sorts and limits")
            dest["data"][key] = copy.deepcopy(value)
        if "order" in patch:
            order = patch["order"]
            if not ownership[order_owned] or not isinstance(order, list) or any(not isinstance(k, str) for k in order):
                raise NativeError("Order replacement requires explicit ownership and string keys")
            if len(order) != len(set(order)) or set(order) != set(dest["data"]):
                raise NativeError("Order must contain every retained tile/control exactly once")
            # Reorder only owned items relative to the fixed unowned subsequence.
            old_unowned = [k for k in before.get(section, {}).get("order", []) if k not in ownership[owned]]
            if [k for k in order if k not in ownership[owned]] != old_unowned:
                raise NativeError("Unrelated tab/control order changed")
            dest["order"] = copy.deepcopy(order)
        elif set(dest["order"]) != set(dest["data"]):
            raise NativeError("Adding/deleting content requires an explicit complete order")
    if "settings" in payload:
        settings = payload["settings"]
        if not isinstance(settings, dict) or set(settings) - set(ownership["settings"]):
            raise NativeError("Unowned settings")
        result.setdefault("settings", {})
        for key, value in settings.items():
            if key == "controlBar":
                if not isinstance(value, dict):
                    raise NativeError("controlBar must be an object")
                result["settings"].setdefault(key, {}).update(value)
            else:
                result["settings"][key] = copy.deepcopy(value)
    if "containers" in payload:
        if not isinstance(payload["containers"], list) or any(not isinstance(v, dict) or "instanceKey" not in v for v in payload["containers"]):
            raise NativeError("Container replacement requires keyed layout objects")
        old_nodes, new_nodes = _container_nodes(before.get("containers", [])), _container_nodes(payload["containers"])
        for key in set(old_nodes) | set(new_nodes):
            if key not in ownership["container_keys"] and _container_shape(old_nodes.get(key)) != _container_shape(new_nodes.get(key)):
                raise NativeError("Container replacement changes unrelated layout")
        old_positions, old_orders = _container_placements(before.get("containers", []))
        new_positions, new_orders = _container_placements(payload["containers"])
        for key, position in old_positions.items():
            if key not in ownership["container_keys"] and new_positions.get(key) != position:
                raise NativeError("Unrelated container moved to another page or parent")
        for position in set(old_orders) | set(new_orders):
            old_order = [k for k in old_orders.get(position, []) if k not in ownership["container_keys"]]
            new_order = [k for k in new_orders.get(position, []) if k not in ownership["container_keys"]]
            if old_order != new_order:
                raise NativeError("Unrelated container order changed")
        result["containers"] = copy.deepcopy(payload["containers"])
    for tile in result["queryPresentations"]["data"].values():
        if tile.get("type") == "linked" and tile.get("sourceQueryPresentationKey") not in result["queryPresentations"]["data"]:
            raise NativeError("Linked tile points at a missing source key")
    if result == before:
        raise NativeError("Candidate has no content changes")
    return result


def readback_matches(candidate, actual):
    """No unreviewed semantic defaults: only owned server binding IDs may differ."""
    expected, observed = copy.deepcopy(candidate["expected_state"]), copy.deepcopy(actual)
    if not isinstance(observed, dict):
        return False
    for state in (expected, observed):
        presentations = state.get("queryPresentations")
        if not isinstance(presentations, dict) or not isinstance(presentations.get("data"), dict):
            return False
        for key in candidate["ownership"]["query_keys"]:
            tile = presentations["data"].get(key)
            if isinstance(tile, dict):
                # Explicitly documented as read-only and server-managed.
                tile.pop("model_extension_id", None)
    return expected == observed


class NativeAdapter:
    def __init__(self, workdir, target: TargetConfig, runner=None, http=None):
        self.root = Path(workdir).resolve(strict=True)
        if not self.root.is_dir():
            raise NativeError("Workspace must be a directory")
        self.target = target
        # Injection is a trusted in-process test/host hook, never artifact data.
        self.runner = runner
        self.http = http or default_http
        self.store = self.root / ".omni-native"
        if self.store.is_symlink():
            raise NativeError("Symlinked evidence store refused")
        self.store.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.store, 0o700)

    def _path(self, relative, exists=True):
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise NativeError("Evidence paths must be workspace-relative without traversal")
        path = self.root / relative
        cursor = path
        while cursor != self.root:
            if cursor.is_symlink():
                raise NativeError("Symlinked evidence paths refused")
            cursor = cursor.parent
        if exists and not path.is_file():
            raise NativeError("Required evidence file is missing")
        return path

    def _read(self, relative):
        with self._path(relative).open("rb") as stream:
            return decode(stream.read(MAX_JSON + 1))

    def _pin(self, relative):
        path = self._path(relative)
        if path.stat().st_size > MAX_FILE:
            raise NativeError("Evidence file exceeds bounded size")
        raw = path.read_bytes()
        return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    def _stage_gate(self, action, content=None, *, expected=None, execution=False):
        """Bind native authoring to the cooperating project's current iteration.

        Conversation-backed selection permits preparation, never native mutation.
        The strict path uses the host's choice verifier in process. Neither an
        authorization label nor a local prepared candidate supplies that authority.
        Historical pre-policy projects retain their existing authorization path.
        """
        try:
            _, project = WORKFLOW.ap.load_project(self.root)
            gate = WORKFLOW.ap.stage_require(self.root, action)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise NativeError("Native authoring stage gate rejected: " + str(exc)) from exc
        # Every native execute route calls this before lock/intent/transport and
        # again before its write. Workflow release readiness is not write authority.
        if action == "release" and (gate.get("selection_policy") == "conversation-evidence-v1" or
                                    gate.get("choice_assurance") == "conversation_evidence"):
            raise NativeError("Conversation evidence cannot authorize native mutation")
        if not gate["required"]:
            if expected is not None:
                raise NativeError("Prepared candidate stage policy changed")
            return None
        if content is None:
            return None  # Early gate, before reading candidate inputs or transport.
        candidate = gate.get("candidate")
        content_hash = hashlib.sha256(content).hexdigest()
        if candidate is None or not any(p["sha256"] == content_hash and p["bytes"] == len(content)
                                        for p in candidate["artifacts"]):
            raise NativeError("Native content must match a current staged candidate artifact")
        binding = {"project_id": project["id"], "candidate_sha256": gate["candidate_sha256"],
                   "iteration_sha256": candidate["event_sha256"], "content_sha256": content_hash}
        if execution and expected != binding:
            raise NativeError("Prepared candidate stage binding changed; prepare again")
        return binding

    def _requirements(self, source_files):
        paths = []
        for path in source_files:
            if path.endswith(".json"):
                value = self._read(path)
                if isinstance(value, dict) and value.get("kind") == "analyst_visual_requirements":
                    paths.append(path)
        if len(paths) != 1:
            raise NativeError("Exactly one source-pinned visual requirements file must be included in source_files")
        try:
            _, requirements = WORKFLOW.requirements(self.root, paths[0])
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise NativeError("Visual requirements or original source evidence failed validation") from exc
        if requirements.get("route") in (None, "unselected") or not requirements.get("route_reference"):
            raise NativeError("Target preparation requires an explicit source route and decision reference")
        if "dashboard" not in requirements.get("surface", []):
            raise NativeError("Native dashboard execution requires the selected dashboard surface")
        return {"file": self._pin(paths[0]), "route": requirements["route"],
                "route_reference": requirements["route_reference"], "source_files": requirements["source_files"]}

    def _write(self, relative, data, exclusive=False):
        path = self._path(relative, exists=False)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw = encoded(data) + b"\n"
        if len(raw) > MAX_JSON:
            raise NativeError("Evidence record exceeds bounded JSON size; reduce candidate scope")
        if exclusive:
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError as exc:
                raise NativeError("Operation already has an intent; reconcile, never replay") from exc
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            fd, name = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def _token(self):
        token = os.environ.get(self.target.token_env)
        if not token or "\n" in token or "\r" in token:
            raise NativeError("Configured token environment variable is missing or invalid")
        return token

    def _cli(self, args, body=None, auth=True, text=False):
        try:
            # Test doubles do not discover or execute a local CLI. Real calls
            # require host-selected exact bytes, not inherited PATH discovery.
            argv = (["omni"] if self.runner is not None else CLI_PROCESS.command(os.environ)) + list(args)
            if auth:
                argv += ["--base-url", self.target.base_url, "--profile", self.target.profile, "--format", "json"]
            if body is not None:
                argv += ["--body", "-"]
            payload = encoded(body) if body is not None else None
            if payload is not None and len(payload) > MAX_JSON:
                raise NativeError("CLI request exceeds bounded size")
            with tempfile.TemporaryDirectory(prefix="oaa-cli-") as folder:
                env = CLI_PROCESS.environment(folder, self._token() if auth else None)
                if self.runner is not None:
                    result = self.runner(argv, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         shell=False, timeout=60, env=env, cwd=folder)
                else:
                    result = CLI_PROCESS.run(argv, input=payload, env=env, cwd=folder, max_stdout=MAX_JSON)
        except CLI_PROCESS.ProcessError as exc:
            raise NativeError(str(exc)) from None
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NativeError("CLI failed or timed out; reconcile any write intent") from exc
        # Never copy stderr: it may contain auth or SQL material supplied by a driver.
        if result.returncode:
            raise NativeError(f"CLI operation failed (exit {result.returncode}); inspect vendor diagnostics privately")
        raw = result.stdout.encode() if isinstance(result.stdout, str) else result.stdout
        if len(raw) > MAX_JSON:
            raise NativeError("CLI response exceeds bounded size")
        try:
            return raw.decode("utf-8") if text else decode(raw)
        except UnicodeError:
            raise NativeError("CLI response is not UTF-8") from None

    def _rest(self, method, route, body=None, max_bytes=MAX_JSON):
        # route is always produced by this class, never by a payload or response URL.
        return self.http(method, self.target.base_url + "/api" + route, self._token(), body, max_bytes)

    def _identity(self):
        status, _, raw = self._rest("GET", "/v1/whoami?modelId=" + self.target.model_id)
        if status != 200:
            raise NativeError("Could not establish target identity")
        identity = decode(raw)
        if identity.get("keyScope") != "user" or identity.get("user", {}).get("membershipId") != self.target.principal_id:
            raise NativeError("Only the configured user-scoped principal is supported")
        return identity

    def capabilities(self):
        commands = [("documents", "v2-get-draft"), ("documents", "list-drafts"),
                    ("documents", "v2-patch-draft-by-identifier")]
        help_text = {" ".join(cmd): self._cli([*cmd, "--help"], auth=False, text=True) for cmd in commands}
        if "--body" not in help_text["documents v2-patch-draft-by-identifier"]:
            raise NativeError("Installed CLI lacks named-draft JSON PATCH support")
        result = {"contract": CONTRACT, "cli_version": self._cli(["--version"], auth=False, text=True).strip(),
                  "help": help_text, "schema_sources": SCHEMA_SOURCES, "schema_reviewed": "2026-10-21",
                  "tenant_exercised": False, "publication_supported": False}
        result["capability_sha256"] = digest(result)
        self._write(".omni-native/capabilities.json", result)
        return result

    def inspect(self):
        identity = self._identity()
        drafts = self._cli(["documents", "list-drafts", self.target.document_id])
        if not isinstance(drafts, list):
            raise NativeError("Unsupported draft-list envelope")
        selected = [d for d in drafts if isinstance(d, dict) and d.get("identifier") == self.target.draft_id]
        if len(selected) != 1:
            raise NativeError("Named development draft is missing or ambiguous")
        meta = selected[0]
        branch = meta.get("branch")
        if (meta.get("publishedIdentifier") != self.target.document_id or meta.get("status") != "active"
                or meta.get("draftOutOfDate") is not False or "branch" not in meta
                or (branch is not None and not isinstance(branch, dict))
                or (branch.get("id") if isinstance(branch, dict) else None) != self.target.branch_id):
            raise NativeError("Draft identity, branch, active status, or freshness mismatch")
        state = self._cli(["documents", "v2-get-draft", self.target.document_id, self.target.draft_id])
        if (not isinstance(state, dict) or state.get("modelId") != self.target.model_id
                or not state.get("workbookModelId") or state["workbookModelId"] != meta.get("workbookModelId")
                or not isinstance(state.get("queryPresentations"), dict)
                or not isinstance(state.get("queryPresentations", {}).get("data"), dict)
                or not isinstance(state.get("queryPresentations", {}).get("order"), list)
                or "app" in state):
            raise NativeError("Unsupported target readback or model identity mismatch")
        if "draftOf" in state and (not isinstance(state["draftOf"], dict) or state["draftOf"].get("identifier") != self.target.document_id):
            raise NativeError("Readback belongs to a different published document")
        result = {"state": state, "draft_context": meta, "identity": identity, "target": asdict(self.target)}
        result["snapshot_sha256"] = digest(result)
        self._write(".omni-native/inspection.json", result)
        return result

    def _semantic_snapshot(self, bindings, inspection, control_bindings=None):
        """Read complete bounded model/Topic context; never infer field definitions."""
        standalone = _standalone_module()
        control_bindings = control_bindings or []
        topics = sorted({b["topic"] for b in bindings} | {f["topic"] for c in control_bindings for f in c["field_bindings"]})
        if not topics or len(topics) > 16:
            raise NativeError("Existing-Omni baseline supports one to sixteen regular Topics")
        commands = [("models", "list"), ("models", "yaml-get"), ("models", "get-topic")]
        help_text = {" ".join(c): self._cli([*c, "--help"], auth=False, text=True) for c in commands}
        for command, flag in (("models list", "--modelid"), ("models yaml-get", "--fullyresolved")):
            if flag not in help_text[command]:
                raise NativeError("Installed CLI lacks reviewed semantic inspection support")
        workbook = require_id(inspection["state"]["workbookModelId"], "workbook model")
        ids = [self.target.model_id, workbook]
        if self.target.branch_id:
            ids.append(self.target.branch_id)
        if len(set(ids)) != len(ids):
            raise NativeError("Shared, workbook and branch model identities must differ")
        models = {}
        for model_id in ids:
            response = self._cli(["models", "list", "--modelid", model_id, "--pagesize", "2"])
            if (not isinstance(response, dict) or response.get("pageInfo", {}).get("hasNextPage") is not False
                    or not isinstance(response.get("records"), list) or len(response["records"]) != 1):
                raise NativeError("Exact native model lookup is missing, ambiguous or incomplete")
            row = response["records"][0]
            if not isinstance(row, dict) or row.get("id") != model_id or row.get("deletedAt") is not None:
                raise NativeError("Native model identity/deletion mismatch")
            # Modification timestamps alone do not define semantics. All other
            # returned metadata is retained, including connection/base-model IDs.
            models[model_id] = {k: v for k, v in row.items() if k not in {"createdAt", "updatedAt"}}
        shared = models[self.target.model_id]
        wb = models[workbook]
        if (shared.get("modelKind") not in {"SHARED", "SHARED_EXTENSION"}
                or not shared.get("connectionId") or wb.get("modelKind") != "WORKBOOK"
                or wb.get("baseModelId") != (self.target.branch_id or self.target.model_id)):
            raise NativeError("Unsupported shared/workbook model ancestry")
        if self.target.branch_id:
            branch = models[self.target.branch_id]
            if branch.get("modelKind") != "BRANCH" or branch.get("baseModelId") != self.target.model_id:
                raise NativeError("Branch is not based on the configured shared model")
        if any(m.get("connectionId") not in {None, shared["connectionId"]} for m in models.values()):
            raise NativeError("Native model connection ancestry differs")
        # The named draft's workbook model is the effective query model. A branch
        # flag is only documented for shared-model YAML reads, so do not add one.
        yaml = self._cli(["models", "yaml-get", workbook, "--mode", "combined",
                          "--fullyresolved", "true", "--includechecksums", "true"])
        if (not isinstance(yaml, dict) or not isinstance(yaml.get("files"), dict) or not yaml["files"]
                or any(not isinstance(k, str) or not isinstance(v, str) for k, v in yaml["files"].items())
                or type(yaml.get("version")) is not int):
            raise NativeError("Complete resolved native model YAML is unavailable")
        result = {"target": asdict(self.target), "identity": inspection["identity"],
                  "draft_context": {k: inspection["draft_context"].get(k) for k in
                    ("identifier", "publishedIdentifier", "workbookModelId", "branch", "status", "draftOutOfDate")},
                  "models": models, "resolved_model": yaml,
                  "topics": {topic: self._cli(["models", "get-topic", workbook, topic]) for topic in topics},
                  "capability_sha256": digest({"help": help_text,
                      "cli_version": self._cli(["--version"], auth=False, text=True).strip()})}
        if control_bindings:
            result["retained_controls"] = standalone.retained_controls(inspection, control_bindings)
        standalone.semantic_definitions(result, bindings, control_bindings)
        return result

    def capture_baseline(self, spec_path, output_relative):
        """Read-only capture of a source-bound, reviewed existing-model baseline."""
        standalone = _standalone_module()
        spec = self._read(spec_path)
        requirements = standalone.validate_spec(self.root, spec, WORKFLOW)
        before = self.inspect()
        expected_state(before["state"], self._read(spec["payload_path"]), self._read(spec["ownership_path"]))
        snapshot = self._semantic_snapshot(spec["bindings"], before, spec.get("control_bindings", []))
        _, project = WORKFLOW.ap.load_project(self.root)
        record = standalone.cw.sealed({"schema_version": 1, "kind": standalone.BASELINE_KIND,
            "project_id": project["id"], "route": requirements["route"], "route_reference": requirements["route_reference"],
            "organization": {"tenant_origin": self.target.base_url, "identifier_basis": "configured_https_tenant_origin"},
            "target": asdict(self.target), "spec": self._pin(spec_path),
            "requirements": self._pin(spec["requirements_path"]), "payload": self._pin(spec["payload_path"]),
            "ownership": self._pin(spec["ownership_path"]), "source_files": [self._pin(p["path"]) for p in requirements["source_files"]],
            "review_ref": spec["review_ref"], "bindings": spec["bindings"],
            "inspection": {"inspected_at": now(), "semantic_snapshot": snapshot, "native_document": before},
            "semantic_sha256": digest(snapshot), "definitions": standalone.semantic_definitions(snapshot, spec["bindings"], spec.get("control_bindings", [])),
            "limitations": ["Tenant HTTPS origin is the organization identifier; these APIs return no organization UUID.",
                "Regular Topics and explicit fields/filters/sorts/limit/table only; calculations, pivots, control edits and composite Topics require separate qualification.",
                "Workbook ancestry must directly identify the selected branch, or shared model when no branch is selected; other representations remain unqualified.",
                "Inspection proves recorded definitions, not query results, effective access for other users, or business acceptance.",
                "External data and user-attribute changes require independent numeric/access evidence; model definitions cannot establish their equivalence."],
            "authorizes_target_write": False, "native_verified": False, "business_accepted": False})
        if spec.get("control_bindings"):
            record.pop("sha256")
            record["control_bindings"] = spec["control_bindings"]
            record["control_evidence"] = [self._pin(path) for path in sorted(
                {path for c in spec["control_bindings"] for path in c["evidence_paths"]})]
            record = standalone.cw.sealed(record)
        backend = standalone.selected_backend(self.root, requirements, WORKFLOW)
        if backend is not None:
            record.pop("sha256")
            record["selected_backend"] = backend
            record = standalone.cw.sealed(record)
        self._write(output_relative, record, exclusive=True)
        return {"status": "baseline_captured", "baseline_sha256": record["sha256"],
                "file": self._pin(output_relative), "topics": len(snapshot["topics"]),
                "bindings": len(spec["bindings"]), "native_verified": False}

    def _baseline_check(self, semantic_file, requirements, payload_pin, ownership_pin, inspection, live=True):
        standalone = _standalone_module()
        try:
            value = self._read(semantic_file)
        except NativeError:
            # Legacy Sigma/DMA semantic inputs were arbitrary pinned files (for
            # example reviewed YAML). Only the new typed branch requires JSON.
            value = None
        if not isinstance(value, dict) or value.get("kind") != standalone.BASELINE_KIND:
            req = WORKFLOW.load(self.root, requirements["file"]["path"])
            inventory = WORKFLOW.load(self.root, req["source_files"][1]["path"])
            platform = inventory.get("source", {}).get("platform")
            if platform in {"looker", "hex", "periscope", "metabase"} or (platform in {"tableau", "powerbi"} and req["route"] == "reuse_existing"):
                raise NativeError("Tableau/Power BI reuse_existing and Looker/Hex/Periscope require a typed current existing-Omni baseline")
            return None
        baseline = standalone.load_baseline(self.root, semantic_file, WORKFLOW)
        if (baseline["target"] != asdict(self.target) or baseline["requirements"] != requirements["file"]
                or baseline["payload"] != payload_pin or baseline["ownership"] != ownership_pin):
            raise NativeError("Existing-Omni baseline target, requirements, payload or ownership changed")
        result = {"sha256": baseline["sha256"], "semantic_sha256": baseline["semantic_sha256"]}
        if live:
            snapshot = self._semantic_snapshot(baseline["bindings"], inspection, baseline.get("control_bindings", []))
            if snapshot != baseline["inspection"]["semantic_snapshot"] or digest(snapshot) != baseline["semantic_sha256"]:
                raise NativeError("Existing-Omni Topic, field, model or effective context drift; capture and review again")
            result["check"] = {"baseline_sha256": baseline["sha256"], "semantic_sha256": digest(snapshot),
                               "semantic_snapshot": snapshot, "checked_at": now()}
        return result

    def prepare(self, payload_path, source_files, semantic_file, ownership_path, review_ref):
        self._stage_gate("build")
        if not review_ref or not isinstance(review_ref, str):
            raise NativeError("A review reference is required")
        if not source_files or len(set(source_files)) != len(source_files):
            raise NativeError("Source evidence paths must be nonempty and unique")
        requirements = self._requirements(source_files)
        payload, ownership = self._read(payload_path), self._read(ownership_path)
        payload_bytes = self._path(payload_path).read_bytes()
        if encoded(decode(payload_bytes)) != encoded(payload):
            raise NativeError("Payload changed during preparation")
        engagement = self._stage_gate("build", payload_bytes)
        pins = {"source_files": [self._pin(p) for p in source_files], "semantic_file": self._pin(semantic_file),
                "payload_file": self._pin(payload_path), "ownership_file": self._pin(ownership_path)}
        caps, before = self.capabilities(), self.inspect()
        baseline = self._baseline_check(semantic_file, requirements, pins["payload_file"], pins["ownership_file"], before)
        candidate = {"contract": CONTRACT, "created_at": now(), "target": asdict(self.target), "pins": pins,
                     "visual_requirements": requirements,
                     "payload": payload, "ownership": ownership, "review_ref": review_ref, "before": before,
                     "expected_state": expected_state(before["state"], payload, ownership),
                     "capability_sha256": caps["capability_sha256"], "capabilities": caps,
                     "validation": "prepared_only", "native_verified": False, "business_accepted": False}
        if engagement is not None:
            candidate["engagement"] = engagement
        if baseline is not None:
            candidate["standalone_baseline"] = {k: v for k, v in baseline.items() if k != "check"}
            candidate["standalone_baseline_check"] = baseline["check"]
        candidate_hash = digest(candidate)
        candidate["candidate_sha256"] = candidate_hash
        self._stage_gate("build", payload_bytes, expected=engagement, execution=True)
        self._write(f".omni-native/candidates/{candidate_hash}.json", candidate, exclusive=True)
        return {"candidate_sha256": candidate_hash, "path": f".omni-native/candidates/{candidate_hash}.json",
                "status": "prepared", "native_verified": False}

    def _candidate(self, candidate_hash, check_evidence=True):
        if not isinstance(candidate_hash, str) or not HASH.fullmatch(candidate_hash):
            raise NativeError("Invalid candidate digest")
        candidate = self._read(f".omni-native/candidates/{candidate_hash}.json")
        content = {k: v for k, v in candidate.items() if k != "candidate_sha256"}
        if digest(content) != candidate_hash or candidate.get("candidate_sha256") != candidate_hash:
            raise NativeError("Candidate contents changed")
        if candidate.get("contract") != CONTRACT:
            raise NativeError("Unsupported native candidate contract")
        if candidate["target"] != asdict(self.target):
            raise NativeError("Candidate target does not match configured target")
        if check_evidence:
            pins = candidate["pins"]
            for pin in [*pins["source_files"], pins["semantic_file"], pins["payload_file"], pins["ownership_file"]]:
                if self._pin(pin["path"]) != pin:
                    raise NativeError("Source, semantic, payload, or ownership evidence changed; prepare again")
            if encoded(self._read(pins["payload_file"]["path"])) != encoded(candidate["payload"]):
                raise NativeError("Candidate payload differs from its pinned evidence")
            if self._requirements([p["path"] for p in pins["source_files"]]) != candidate["visual_requirements"]:
                raise NativeError("Visual source route or requirements changed; prepare again")
            baseline = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                pins["payload_file"], pins["ownership_file"], None, live=False)
            if baseline != candidate.get("standalone_baseline"):
                raise NativeError("Existing-Omni baseline binding changed")
        return candidate

    def _lock(self):
        path = self._path(".omni-native/execution.lock", exists=False)
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        stream = os.fdopen(fd, "a+")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            stream.close()
            raise NativeError("Another target operation holds the engagement lock") from exc
        return stream

    def execute(self, candidate_sha256, authorization_ref):
        self._stage_gate("release")
        if not isinstance(authorization_ref, str) or not authorization_ref.strip():
            raise NativeError("Explicit authorization for this candidate and target is required")
        with self._lock():
            candidate = self._candidate(candidate_sha256)
            payload_bytes = self._path(candidate["pins"]["payload_file"]["path"]).read_bytes()
            self._stage_gate("release", payload_bytes, expected=candidate.get("engagement"), execution=True)
            intent_path = f".omni-native/executions/{candidate_sha256}/intent.json"
            if self._path(intent_path, exists=False).exists():
                raise NativeError("Candidate already has a write intent; reconcile, never replay")
            if self.capabilities()["capability_sha256"] != candidate["capability_sha256"]:
                raise NativeError("CLI capability/schema fingerprint changed; prepare again")
            current = self.inspect()
            if current["snapshot_sha256"] != candidate["before"]["snapshot_sha256"]:
                raise NativeError("Draft, identity, permissions, or branch drift; prepare again")
            pins = candidate["pins"]
            baseline = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                pins["payload_file"], pins["ownership_file"], current)
            receipt = {"contract": CONTRACT, "candidate_sha256": candidate_sha256, "target": asdict(self.target),
                       "authorization_ref": authorization_ref, "started_at": now(), "status": "intent_persisted",
                       "native_verified": False, "business_accepted": False, "published": False}
            if baseline is not None:
                receipt["standalone_baseline_check"] = baseline["check"]
            self._stage_gate("release", payload_bytes, expected=candidate.get("engagement"), execution=True)
            self._write(intent_path, receipt, exclusive=True)
            try:
                response = self._cli(["documents", "v2-patch-draft-by-identifier", self.target.document_id,
                                      self.target.draft_id], body=candidate["payload"])
                receipt["response"] = response
                if not isinstance(response, dict) or response.get("identifier") != self.target.document_id or response.get("draftIdentifier") != self.target.draft_id:
                    raise NativeError("PATCH response target mismatch")
                after = self.inspect()
                receipt["readback"] = after
                if baseline is not None:
                    # The local lock cannot prevent a remote model editor. A
                    # second semantic read records detected races as unknown.
                    checked = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                        pins["payload_file"], pins["ownership_file"], after)
                    receipt["standalone_baseline_check"] = checked["check"]
                receipt["status"] = "readback_matched" if readback_matches(candidate, after["state"]) else "readback_mismatch"
            except (ValueError, OSError, TimeoutError, TypeError, AttributeError) as exc:
                receipt["status"] = "outcome_unknown"
                receipt["error_class"] = type(exc).__name__
            receipt["finished_at"] = now()
            self._write(f".omni-native/executions/{candidate_sha256}/receipt.json", receipt)
            return receipt

    def reconcile(self, candidate_sha256):
        with self._lock():
            # Source drift blocks writes/exports, but must not prevent read-only
            # reconciliation of an earlier ambiguous mutation at its known target.
            candidate = self._candidate(candidate_sha256, check_evidence=False)
            try:
                self._candidate(candidate_sha256)
                evidence_current = True
            except (NativeError, OSError):
                evidence_current = False
            intent = self._read(f".omni-native/executions/{candidate_sha256}/intent.json")
            current = self.inspect()
            status = "readback_matched" if readback_matches(candidate, current["state"]) else "conflict_or_partial"
            if current["state"] == candidate["before"]["state"]:
                status = "before_state_observed"
            if candidate.get("standalone_baseline"):
                pins = candidate["pins"]
                try:
                    checked = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                        pins["payload_file"], pins["ownership_file"], current)
                    intent["standalone_baseline_check"] = checked["check"]
                except (ValueError, OSError):
                    status = "semantic_context_drift_or_unavailable"
            receipt = {**intent, "status": status, "reconciled_at": now(), "readback": current,
                       "automatic_retry_allowed": False, "source_evidence_current": evidence_current}
            self._write(f".omni-native/executions/{candidate_sha256}/reconciliation.json", receipt)
            return receipt

    def export_start(self, candidate_sha256, request_path, state_path, authorization_ref):
        if not authorization_ref:
            raise NativeError("Export/query authorization reference required")
        with self._lock():
            candidate = self._candidate(candidate_sha256)
            state = self._read(state_path)
            required = {"state_id", "filters", "persona", "timezone", "data_watermark", "viewport"}
            if not isinstance(state, dict) or not required <= set(state):
                raise NativeError("Export state must identify state_id, filters, persona, timezone, data_watermark and viewport")
            body = self._read(request_path)
            _validate_export(body)
            if state["persona"] != self.target.principal_id or state["filters"] != body.get("filterConfig", {}):
                raise NativeError("Export persona/filters do not match the frozen state")
            current = self.inspect()
            if not readback_matches(candidate, current["state"]):
                raise NativeError("Export requires matching candidate readback")
            pins = candidate["pins"]
            baseline = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                pins["payload_file"], pins["ownership_file"], current)
            operation = {"candidate_sha256": candidate_sha256, "target": asdict(self.target), "request": body,
                         "state": state, "state_pin": self._pin(state_path), "request_pin": self._pin(request_path),
                         "readback_sha256": digest(current["state"]), "authorization_ref": authorization_ref}
            if baseline is not None:
                operation["standalone_baseline_check"] = baseline["check"]
            export_id = digest(export_identity(operation))
            relative = f".omni-native/exports/{export_id}"
            self._write(relative + "/intent.json", {**operation, "export_id": export_id, "created_at": now()}, exclusive=True)
            result = {**operation, "export_id": export_id, "status": "outcome_unknown", "native_verified": False}
            try:
                status, _, raw = self._rest("POST", self._export_route(), body)
                response = decode(raw)
                result["response"] = response
                if not isinstance(response, dict):
                    raise NativeError("Unsupported export response envelope")
                if status == 200:
                    result["job_id"] = require_id(response.get("job_id"), "export job ID")
                    result["status"] = "submitted"
                elif status == 409:
                    # Existing job may have different filters/content; do not adopt its output.
                    result["status"] = "conflict_existing_job"
                elif 400 <= status < 500 and status != 408:
                    result["status"] = "rejected"
                result["http_status"] = status
            except (ValueError, OSError, TimeoutError, TypeError, AttributeError) as exc:
                result["error_class"] = type(exc).__name__
            self._write(relative + "/receipt.json", result)
            return result

    def _export_route(self, job=None, status=False):
        route = "/v1/dashboards/" + self.target.draft_id + "/download"
        if job:
            route += "/" + require_id(job, "export job ID")
        if status:
            route += "/status"
        return route

    def _export(self, export_id):
        if not isinstance(export_id, str) or not HASH.fullmatch(export_id):
            raise NativeError("Invalid export ID")
        intent = self._read(f".omni-native/exports/{export_id}/intent.json")
        if digest(export_identity(intent)) != export_id or intent["target"] != asdict(self.target):
            raise NativeError("Export intent changed or target mismatch")
        candidate = self._candidate(intent["candidate_sha256"])
        for pin in (intent["state_pin"], intent["request_pin"]):
            if self._pin(pin["path"]) != pin:
                raise NativeError("Export request or state evidence changed")
        receipt = self._read(f".omni-native/exports/{export_id}/receipt.json")
        if not receipt.get("job_id") or receipt.get("export_id") != export_id:
            raise NativeError("No known job for this export; manual reconciliation required")
        return intent, receipt, candidate

    def export_status(self, export_id):
        with self._lock():
            intent, receipt, _ = self._export(export_id)
            self._identity()
            status, _, raw = self._rest("GET", self._export_route(receipt["job_id"], status=True))
            if status != 200:
                raise NativeError("Export status unavailable; do not resubmit")
            observed = decode(raw)
            if (not isinstance(observed, dict) or observed.get("job_id") != receipt["job_id"] or observed.get("format") != intent["request"]["format"]
                    or observed.get("status") not in {"in_progress", "complete", "error"}):
                raise NativeError("Export status identity/format/contract mismatch")
            receipt.update(status=observed["status"], status_response=observed, checked_at=now())
            self._write(f".omni-native/exports/{export_id}/receipt.json", receipt)
            return receipt

    def export_file(self, export_id):
        with self._lock():
            intent, receipt, candidate = self._export(export_id)
            if receipt["status"] != "complete":
                raise NativeError("Export file requires confirmed complete status")
            before = self.inspect()
            if digest(before["state"]) != intent["readback_sha256"]:
                raise NativeError("Draft changed during export; evidence cannot represent this candidate")
            pins = candidate["pins"]
            baseline = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                pins["payload_file"], pins["ownership_file"], before)
            status, headers, raw = self._rest("GET", self._export_route(receipt["job_id"]), max_bytes=MAX_FILE)
            if status != 200:
                raise NativeError("File unavailable or expired; do not resubmit automatically")
            fmt = intent["request"]["format"]
            _validate_media(fmt, headers, raw)
            after = self.inspect()
            if digest(after["state"]) != intent["readback_sha256"]:
                raise NativeError("Draft changed while downloading; discard unmatched evidence")
            if baseline is not None:
                checked = self._baseline_check(pins["semantic_file"]["path"], candidate["visual_requirements"],
                    pins["payload_file"], pins["ownership_file"], after)
                receipt["standalone_baseline_check"] = checked["check"]
            relative = f".omni-native/exports/{export_id}/artifact.{fmt}"
            path = self._path(relative, exists=False)
            if path.exists():
                if path.read_bytes() != raw:
                    raise NativeError("Existing exported bytes differ; retain original evidence")
            else:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            receipt.update(status="downloaded", artifact=self._pin(relative), downloaded_at=now(),
                           candidate_state_matched=True, data_watermark_verified=False, native_verified=False)
            self._write(f".omni-native/exports/{export_id}/receipt.json", receipt)
            return receipt


def _validate_export(body):
    allowed = {"format", "queryIdentifierMapKey", "filterConfig", "containerPages", "paperFormat", "paperOrientation",
               "hideTitle", "showFilters", "enableFormatting", "hideHiddenFields", "maxRowLimit", "cache"}
    if not isinstance(body, dict) or set(body) - allowed or body.get("format") not in {"png", "pdf", "json", "csv"}:
        raise NativeError("Supported exports: PNG/PDF or bounded single-tile JSON/CSV")
    if "filterConfig" in body and not isinstance(body["filterConfig"], dict):
        raise NativeError("filterConfig must be an object")
    tile = body.get("queryIdentifierMapKey")
    if tile is not None:
        require_id(tile, "tile map key")
    pages = body.get("containerPages")
    if pages is not None and (not isinstance(pages, list) or not pages or tile or body["format"] == "json"):
        raise NativeError("Invalid export page selection")
    if pages:
        for page in pages:
            require_id(page, "page instance key")
    if body["format"] == "png" and pages and len(pages) != 1:
        raise NativeError("PNG exports require exactly one selected page")
    if body["format"] in {"json", "csv"}:
        if not tile or type(body.get("maxRowLimit")) is not int or not 1 <= body["maxRowLimit"] <= 100000:
            raise NativeError("Numerical exports require a tile and explicit maxRowLimit <= 100000")


def _validate_media(fmt, headers, raw):
    if not raw or len(raw) > MAX_FILE:
        raise NativeError("Empty or oversized export")
    media = {k.lower(): v for k, v in headers.items()}.get("content-type", "").split(";")[0].lower().strip()
    expected = {"png": {"image/png"}, "pdf": {"application/pdf"},
                "json": {"application/json"}, "csv": {"text/csv", "application/csv"}}
    if media not in expected[fmt]:
        raise NativeError("Unexpected export media type")
    if fmt == "png":
        _validate_png(raw)
    if fmt == "pdf" and (not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]):
        raise NativeError("Invalid PDF signature/end marker")
    if fmt == "json":
        decode(raw)
    if fmt == "csv":
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise NativeError("CSV must be UTF-8") from exc
        if "\x00" in text or text.lstrip().lower().startswith(("<!doctype", "<html")):
            raise NativeError("Unexpected content masquerading as CSV")


def _validate_png(raw):
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise NativeError("Invalid PNG signature")
    offset, seen_header, seen_data = 8, False, False
    compressed, palette, stride, expected_bytes, color = [], False, 0, 0, None
    while offset + 12 <= len(raw):
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        end = offset + length + 12
        if end > len(raw):
            raise NativeError("Truncated PNG chunk")
        kind, data = raw[offset + 4:offset + 8], raw[offset + 8:end - 4]
        if zlib.crc32(kind + data) & 0xffffffff != struct.unpack(">I", raw[end - 4:end])[0]:
            raise NativeError("Invalid PNG chunk checksum")
        if not seen_header:
            if kind != b"IHDR" or length != 13:
                raise NativeError("Invalid PNG header")
            width, height = struct.unpack(">II", data[:8])
            if not width or not height or width > 16384 or height > 16384 or width * height > 64000000:
                raise NativeError("PNG dimensions exceed bounded preview size")
            depth, color, compression, filtering, interlace = data[8:]
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
            if color not in depths or depth not in depths[color] or compression or filtering or interlace:
                raise NativeError("Unsupported PNG encoding; non-interlaced standard PNG required")
            samples = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
            stride = (width * depth * samples + 7) // 8 + 1
            expected_bytes = stride * height
            if expected_bytes > 64 * 1024 * 1024:
                raise NativeError("PNG decoded content exceeds bounded size")
            seen_header = True
        elif kind == b"IHDR":
            raise NativeError("Duplicate PNG header")
        if kind == b"IDAT" and length:
            seen_data = True
            compressed.append(data)
        if kind == b"PLTE":
            if not length or length % 3 or length > 768 or seen_data:
                raise NativeError("Invalid PNG palette")
            palette = True
        if kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"} and kind[0] & 32 == 0:
            raise NativeError("Unsupported critical PNG chunk")
        if kind == b"IEND":
            if length or end != len(raw) or not seen_data:
                raise NativeError("Invalid PNG end marker")
            if color == 3 and not palette:
                raise NativeError("Indexed PNG requires a palette")
            try:
                inflater = zlib.decompressobj()
                pixels = inflater.decompress(b"".join(compressed), expected_bytes + 1)
                if (len(pixels) != expected_bytes or not inflater.eof or inflater.unconsumed_tail
                        or inflater.unused_data or any(pixels[n] > 4 for n in range(0, expected_bytes, stride))):
                    raise NativeError("Invalid PNG pixel rows or compressed stream")
            except zlib.error as exc:
                raise NativeError("Invalid PNG compressed stream") from exc
            return
        offset = end
    raise NativeError("Missing PNG end marker")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--target", required=True, help="Target configuration JSON, workspace-relative")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("capabilities", "inspect"):
        sub.add_parser(name)
    baseline = sub.add_parser("baseline-capture")
    baseline.add_argument("--spec", required=True)
    baseline.add_argument("--output", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--payload", required=True)
    prepare.add_argument("--source", action="append", required=True)
    prepare.add_argument("--semantic", required=True)
    prepare.add_argument("--ownership", required=True)
    prepare.add_argument("--review-ref", required=True)
    for name in ("execute", "reconcile", "export-start"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--candidate", required=True)
        if name != "reconcile":
            cmd.add_argument("--authorization-ref", required=True)
        if name == "export-start":
            cmd.add_argument("--request", required=True)
            cmd.add_argument("--state", required=True)
    for name in ("export-status", "export-file"):
        sub.add_parser(name).add_argument("--export-id", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.workspace).resolve(strict=True)
        target_path = root / args.target
        if Path(args.target).is_absolute() or ".." in Path(args.target).parts:
            raise NativeError("Target config must be an ordinary workspace-relative file")
        cursor = target_path
        while cursor != root:
            if cursor.is_symlink():
                raise NativeError("Symlinked target config paths refused")
            cursor = cursor.parent
        target = TargetConfig(**decode(target_path.read_bytes()))
        adapter = NativeAdapter(root, target)
        if args.command == "baseline-capture":
            result = adapter.capture_baseline(args.spec, args.output)
        elif args.command == "prepare":
            result = adapter.prepare(args.payload, args.source, args.semantic, args.ownership, args.review_ref)
        elif args.command == "execute":
            result = adapter.execute(args.candidate, args.authorization_ref)
        elif args.command == "reconcile":
            result = adapter.reconcile(args.candidate)
        elif args.command == "export-start":
            result = adapter.export_start(args.candidate, args.request, args.state, args.authorization_ref)
        elif args.command in {"export-status", "export-file"}:
            result = getattr(adapter, args.command.replace("-", "_"))(args.export_id)
        else:
            result = getattr(adapter, args.command)()
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        # Safe fixed validation messages; no raw transport exception/credential repr.
        print(json.dumps({"error": str(exc) if isinstance(exc, NativeError) else type(exc).__name__}), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
