"""Bounded, startup-selected Sigma source operations. Integrity is not authority.

Only a locally qualified host may activate this adapter after dependency review.
No target credentials, arbitrary command, HTTP server, install or publish path.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


HERE = Path(__file__).resolve().parent
ap = module("sigma_host_project", HERE / "analyst_project.py")
process = module("sigma_host_process", HERE.parents[1] / "omni-bi-engineer/scripts/cli_process.py")


def need(ok, code):
    if not ok:
        raise ValueError("sigma.host." + code)


def pin(root, record):
    need(type(record) is dict and set(record) == {"path", "sha256"}, "pin_required")
    path = ap.relative_file(root, record["path"])
    need(ap.digest(path.read_bytes()) == record["sha256"], "pin_changed")
    return path


contract = module('sigma_source_contract', HERE.parents[1] / 'omni-artifact-translator/scripts/sigma_source_contract.py')
request = contract.request


class SigmaOperations:
    """Configuration is fixed at process startup, never chosen by an MCP call.

    Budget reservations survive timeouts/restarts. Unknown export outcomes remain
    in the source journal and must not be restarted in another output directory.
    """
    def __init__(self, project, configuration, *, allow_read=False, allow_query=False, runner=None):
        need(allow_read is True, "source_read_grant_required")
        self.root, _ = ap.load_project(project)
        self.configuration = {"path": configuration,
                              "sha256": ap.digest(ap.relative_file(self.root, configuration).read_bytes())}
        self.config, _ = ap.read_json(pin(self.root, self.configuration))
        c = self.config
        need(c.get("schema_version") == "oaa-sigma-host.v1", "configuration_contract")
        self.allow_query = allow_query
        self.runner = runner or process.run
        self.runtime = c.get("runtime", {})
        need(type(self.runtime.get("closure")) is list and 0 < len(self.runtime["closure"]) <= 10000,
             "reviewed_runtime_closure_required")
        for key, bound in (("max_invocations", 200), ("max_total_requests", 10000), ("timeout_seconds", 300)):
            need(type(c.get(key)) is int and 1 <= c[key] <= bound, "finite_budget_required")
        self.expected_capabilities, _ = ap.read_json(pin(self.root, c.get("capabilities")))
        need(self.expected_capabilities.get("schema_version") == "sigma-source-capabilities.v1", "capabilities_contract")
        registry, _ = ap.read_json(HERE.parent / 'references/sigma-compatibility.json')
        for field in ('extension_name', 'extension_version', 'request_schema', 'result_schema'):
            need(self.expected_capabilities.get(field) == registry['connected_source'][field], 'unknown_capability_profile')
        need(self.expected_capabilities.get('operations') == ['check', 'inventory', 'snapshot', 'capture']
             and self.expected_capabilities.get('target_write_authority') is False
             and self.expected_capabilities.get('terminal_review_bypass') is False, 'source_capabilities_only')
        self.entries = {}
        operations = c.get("operations")
        need(type(operations) is list and 0 < len(operations) <= 100, "operations_required")
        directories = set()
        for entry in operations:
            need(type(entry) is dict and set(entry) == {"id", "request", "directory"}, "operation_entry")
            key = entry["id"]
            need(type(key) is str and re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", key) and key not in self.entries,
                 "unique_operation_required")
            value, _ = ap.read_json(pin(self.root, entry["request"]))
            request(value)
            need(value["request_id"] == key, "request_identity_mismatch")
            folder = Path(entry["directory"])
            need(not folder.is_absolute() and folder.as_posix() == entry["directory"]
                 and not any(x in (".", "..") for x in folder.parts) and "\\" not in str(folder), "output_scope")
            destination = ap.no_links(self.root / folder)
            need(destination != self.root and destination.is_relative_to(self.root), "output_scope")
            need(not any(destination == p or destination.is_relative_to(p) or p.is_relative_to(destination)
                         for p in directories), "overlapping_output_scope")
            directories.add(destination)
            self.entries[key] = (entry, value, destination)
        self.check_runtime()

    def check_runtime(self):
        pin(self.root, self.configuration)
        pin(self.root, self.config["capabilities"])
        for entry, _, _ in self.entries.values():
            pin(self.root, entry['request'])
        runtime = self.runtime
        exe = runtime.get("executable", {})
        env = {"OAA_OMNI_CLI_PATH": exe.get("path"), "OAA_OMNI_CLI_SHA256": exe.get("sha256")}
        if runtime.get("interpreter"):
            interpreter = runtime["interpreter"]
            env.update(OAA_OMNI_RUNTIME_PATH=interpreter.get("path"), OAA_OMNI_RUNTIME_SHA256=interpreter.get("sha256"))
        argv = process.command(env)
        if runtime.get("interpreter"):
            need(runtime.get("interpreter_kind") == "python", "python_interpreter_required")
            argv.insert(1, "-I")
        seen = set()
        for item in runtime["closure"]:
            need(type(item) is dict and set(item) == {"path", "sha256"} and item["path"] not in seen,
                 "closure_pin")
            seen.add(item["path"])
            process.pinned_file(item["path"], item["sha256"])
        source_root = Path(runtime.get('source_root', ''))
        need(source_root.is_absolute() and not any(p.is_symlink() for p in (source_root, *source_root.parents)), 'source_root_required')
        files = self.expected_capabilities.get('implementation_files')
        need(type(files) is dict and files and ap.digest(ap.canonical(files)) == self.expected_capabilities.get('implementation_sha256'),
             'implementation_manifest_changed')
        closure = {p['path']: p['sha256'] for p in runtime['closure']}
        for relative, digest in files.items():
            path = Path(relative)
            need(not path.is_absolute() and '..' not in path.parts and path.as_posix() == relative and '\\' not in relative,
                 'implementation_path')
            need(closure.get(str(source_root / path)) == digest, 'implementation_closure_incomplete')
        return argv

    def describe(self):
        self.check_runtime()
        return {"status": "source_configuration_checked", "operations": list(self.entries),
                "runtime_loaded": False, "source_access_verified": False,
                "dependency_approval_verified": False, "native_write_authority": False}

    def run(self, operation_id, resume=False):
        need(operation_id in self.entries and type(resume) is bool, "operation_not_selected")
        argv = self.check_runtime()
        entry, value, destination = self.entries[operation_id]
        request_path = pin(self.root, entry["request"])
        need(value["operation"] != "capture" or self.allow_query is True, "separate_query_grant_required")
        state_dir = ap.no_links(self.root / "evidence" / "sigma-host")
        state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Lock and reserve BEFORE any child runs. Changed configuration has a new
        # ledger, but the source operation journal still binds the output scope.
        key = self.configuration["sha256"]
        lockpath = ap.no_links(state_dir / (key + ".lock"))
        fd = os.open(lockpath, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ledger = ap.no_links(state_dir / (key + ".json"))
            state = ap.read_json(ledger)[0] if ledger.exists() else {"invocations": 0, "reserved_requests": 0}
            need(state["invocations"] < self.config["max_invocations"] and
                 state["reserved_requests"] + value["max_requests"] <= self.config["max_total_requests"], "budget_exhausted")
            state["invocations"] += 1
            state["reserved_requests"] += value["max_requests"]
            ap.write_json(ledger, state, replace=ledger.exists())
            with tempfile.TemporaryDirectory(prefix="sigma-source-", dir=state_dir) as home:
                env = process.environment(home)
                env.update(PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1")
                # Capabilities run without either provider's credentials.
                cap = self.runner(argv + ["capabilities"], env=env, cwd=home,
                                  timeout=self.config["timeout_seconds"], max_stdout=512*1024)
                need(cap.returncode == 0, "capabilities_failed")
                actual = json.loads(cap.stdout, object_pairs_hook=ap.reject_duplicate)
                need(actual == self.expected_capabilities, "capabilities_changed")
                self.check_runtime()
                pin(self.root, entry["request"])
                env = dict(env)
                for name in ("SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET"):
                    token = os.environ.get(name, "")
                    need(0 < len(token) <= 8192 and not any(c.isspace() for c in token), "source_credentials_required")
                    env[name] = token
                command = argv + ["source-operation", "--request", str(request_path),
                                  "--directory", str(destination), "--allow-source-read"]
                if self.allow_query:
                    command.append("--allow-source-query")
                if resume:
                    command.append("--resume")
                result = self.runner(command, env=env, cwd=home,
                                     timeout=self.config["timeout_seconds"], max_stdout=512*1024)
                need(result.returncode == 0, "source_requires_review_resume_existing_journal")
                answer = json.loads(result.stdout, object_pairs_hook=ap.reject_duplicate)
                saved = ap.no_links(Path(answer.get("output", "")))
                need(saved.is_absolute() and saved.is_relative_to(destination), "output_escaped")
                envelope, raw = ap.read_json(saved)
                contract.envelope(envelope)
                need(envelope.get("schema_version") == "sigma-source-operation.v1", "source_envelope_required")
                need(envelope.get("request_sha256") == ap.digest(ap.canonical(value)), "output_request_changed")
                need(envelope.get('request') == value and envelope.get('operation') == value['operation']
                     and envelope.get('result_sha256') == ap.digest(ap.canonical(envelope.get('result')))
                     and envelope.get('content_hash') == ap.digest(ap.canonical({k: v for k, v in envelope.items() if k != 'content_hash'}))
                     and envelope.get('target_write_authority') is False, 'output_integrity')
                return {"status": "source_operation_recorded", "operation_id": operation_id,
                        "evidence": {"path": str(saved.relative_to(self.root)), "sha256": ap.digest(raw)},
                        "native_validation": "not_run", "target_write_authority": False}
