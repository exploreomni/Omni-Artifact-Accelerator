import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/omni-artifact-accelerator/scripts"))
import visual_mcp as m  # noqa: E402 - standalone skill modules live outside site-packages


class Native:
    def __init__(self):
        self.executed = []

    def capabilities(self):
        return {"local_cli": True, "live": False}

    def execute(self, digest, reference):
        self.executed.append((digest, reference))
        return {"status": "recorded", "native_verified": False}


class HostBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "run"
        m.workflow.ap.init(self.root, "Host fixture", "migration", "dashboard")
        self.bridge = m.Bridge(self.root)

    def request(self, method, params=None, ident=1):
        return self.bridge.handle({"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}})

    def initialize(self):
        self.request("initialize", {"protocolVersion": m.PROTOCOL})
        self.bridge.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def test_initialization_and_only_local_tools_by_default(self):
        self.assertIn("error", self.request("tools/list"))
        self.initialize()
        tools = self.request("tools/list")["result"]["tools"]
        self.assertFalse(any(t["name"].startswith("native_") for t in tools))
        self.assertTrue(all("inputSchema" in t for t in tools))

    def test_unknown_tools_and_arbitrary_commands_rejected(self):
        self.initialize()
        for name, args in (("exec", {"command": "anything"}), ("native_execute", {"candidate_sha256": "a" * 64}),
                           ("visual_read", {"path": "project.json", "url": "https://other.invalid"})):
            result = self.request("tools/call", {"name": name, "arguments": args})
            self.assertTrue(result["result"]["isError"])

    def test_pinned_startup_authority_cannot_be_supplied_by_tool(self):
        native = Native()
        self.bridge = m.Bridge(self.root, native, "a" * 64, "operator-session-reference")
        self.initialize()
        for args in ({"candidate_sha256": "b" * 64}, {"candidate_sha256": "a" * 64, "authorization_reference": "invented"}):
            self.assertTrue(self.request("tools/call", {"name": "native_execute", "arguments": args})["result"]["isError"])
        self.assertFalse(native.executed)
        result = self.request("tools/call", {"name": "native_execute", "arguments": {"candidate_sha256": "a" * 64}})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(native.executed, [("a" * 64, "operator-session-reference")])

    def test_export_authority_is_separate_and_exact_request_is_pinned(self):
        request, state = "contracts/export.json", "contracts/state.json"
        for path in (request, state):
            m.workflow.ap.write_json(self.root / path, {"fixed": path})
        native = Native()
        draft_only = m.Bridge(self.root, native, "a" * 64, "draft-ref")
        self.assertFalse(any(t["name"].startswith("native_export") for t in draft_only.definitions()))
        bridge = m.Bridge(self.root, native, export_candidate="a" * 64, export_request=request,
                          export_state=state, export_authorization_reference="export-ref")
        calls = []
        def start(*args):
            calls.append(args)
            record = {"export_id": "b" * 64, "status": "submitted", "candidate_sha256": "a" * 64,
                      "request_pin": m.export_pin(self.root, request), "state_pin": m.export_pin(self.root, state),
                      "response": {"sensitive": "excluded from MCP response"}}
            folder = self.root / ".omni-native/exports" / record["export_id"]
            folder.mkdir(parents=True)
            m.workflow.ap.write_json(folder / "receipt.json", record)
            return record
        native.export_start = start
        result = bridge.call("native_export_start", {})
        self.assertEqual(calls, [("a" * 64, request, state, "export-ref")])
        self.assertNotIn("response", result)
        with self.assertRaises(ValueError):
            bridge.call("native_export_start", {"request": "contracts/other.json"})
        (self.root / request).write_text('{"changed":true}')
        with self.assertRaises(ValueError):
            bridge.call("native_export_start", {})
        self.assertEqual(len(calls), 1)

    def test_export_poll_rejects_unrelated_receipt_before_network_and_supports_restart(self):
        request, state = "contracts/export.json", "contracts/state.json"
        for path in (request, state):
            m.workflow.ap.write_json(self.root / path, {})
        native = Native()
        calls = []
        export_id = "b" * 64
        record = {"export_id": export_id, "status": "complete", "candidate_sha256": "a" * 64,
                  "request_pin": m.export_pin(self.root, request), "state_pin": m.export_pin(self.root, state)}
        folder = self.root / ".omni-native/exports" / export_id
        folder.mkdir(parents=True)
        m.workflow.ap.write_json(folder / "receipt.json", record)
        native.export_status = lambda ident: calls.append(ident) or record
        for _ in range(2):
            bridge = m.Bridge(self.root, native, export_candidate="a" * 64, export_request=request,
                              export_state=state, export_authorization_reference="export-ref")
            self.assertEqual(bridge.call("native_export_status", {"export_id": export_id})["status"], "complete")
        record["candidate_sha256"] = "c" * 64
        (folder / "receipt.json").write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            bridge.call("native_export_status", {"export_id": export_id})
        with self.assertRaises(ValueError):
            bridge.call("native_export_status", {"export_id": "../../other"})
        self.assertEqual(len(calls), 2)

    def test_read_artifact_rejects_other_files_and_traversal(self):
        self.initialize()
        for path in ("project.json", "../outside.json", "/etc/passwd"):
            self.assertTrue(self.request("tools/call", {"name": "visual_read", "arguments": {"path": path}})["result"]["isError"])
        m.workflow.ap.write_json(self.root / "contracts/read.json", {"kind": "analyst_numeric_comparison", "status": "not_run"})
        result = self.request("tools/call", {"name": "visual_read", "arguments": {"path": "contracts/read.json"}})
        data = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(data["content_authority"], "untrusted_data")

    def test_transport_delimits_json_and_ignores_notifications(self):
        messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": m.PROTOCOL}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
        stream = io.BytesIO(("\n".join(json.dumps(x) for x in messages) + "\n").encode())
        output = io.StringIO()
        m.serve(self.bridge, stream, output)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([r["id"] for r in records], [1, 2])

    def test_duplicate_key_and_oversized_frame_rejected(self):
        for raw in (b'{"method":"ping","method":"exec"}\n', b"x" * (m.MAX_MESSAGE + 1)):
            output = io.StringIO()
            m.serve(self.bridge, io.BytesIO(raw), output)
            self.assertIn("error", json.loads(output.getvalue()))

    def test_boolean_request_id_rejected(self):
        self.assertIn("error", self.request("ping", ident=True))

    def test_invalid_protocol_version_rejected_without_crash(self):
        self.assertIn("error", self.request("initialize", {"protocolVersion": {"unexpected": True}}))
        self.assertFalse(self.bridge.initialized)

    def test_invalid_decimal_case_returns_tool_error_and_server_survives(self):
        self.initialize()
        with patch.object(m.workflow, "compare", side_effect=m.workflow.InvalidOperation):
            result = self.request("tools/call", {"name": "numeric_compare", "arguments": {"spec": "contracts/case.json", "output": "evidence/result.json"}})
        self.assertTrue(result["result"]["isError"])
        self.assertEqual(self.request("ping")["result"], {})

    def test_source_capture_uses_fixed_command_and_rejects_changed_request(self):
        request = self.root / "inputs/capture.json"
        m.workflow.ap.write_json(request, {"capture_id": "one"})
        folder = self.root / "inputs/captured"
        folder.mkdir()
        captured = folder / "capture-000001.json"
        m.workflow.ap.write_json(captured, {"status": "partial"})
        calls = []
        def runner(argv, **options):
            calls.append((argv, options))
            return SimpleNamespace(returncode=0, stdout=json.dumps({"status": "partial", "output": str(captured)}).encode())
        source = m.SigmaCommand(self.root, sys.executable, "inputs/capture.json", "inputs/captured", runner)
        with patch.dict(os.environ, {"SIGMA_CLIENT_ID": "synthetic-id", "SIGMA_CLIENT_SECRET": "synthetic-secret",
                                     "OMNI_API_TOKEN": "target-secret", "TABLEAU_SESSION_TOKEN": "other-source-secret"}):
            self.assertEqual(source.capture(True)["status"], "partial")
        self.assertFalse(calls[0][1]["shell"])
        self.assertIn("--resume", calls[0][0])
        self.assertEqual(calls[0][1]["env"]["SIGMA_CLIENT_ID"], "synthetic-id")
        self.assertNotIn("OMNI_API_TOKEN", calls[0][1]["env"])
        self.assertNotIn("TABLEAU_SESSION_TOKEN", calls[0][1]["env"])
        request.write_text('{"capture_id":"different"}')
        with self.assertRaises(ValueError):
            source.capture(True)
        self.assertEqual(len(calls), 1)

    def test_batch_only_exposes_selected_ids_and_rejects_changed_scope(self):
        for ident in ("one", "two"):
            m.workflow.ap.write_json(self.root / f"inputs/{ident}.json", {"capture_id": ident})
        batch = {"kind": "analyst_sigma_capture_batch", "schema_version": 1, "max_total_requests": 200,
                 "max_invocations": 2, "captures": [
            {"capture_id": ident, "request": f"inputs/{ident}.json", "directory": f"inputs/capture-{ident}"}
            for ident in ("one", "two")]}
        m.workflow.ap.write_json(self.root / "inputs/batch.json", batch)
        sigma = m.SigmaBatch(self.root, sys.executable, "inputs/batch.json")
        bridge = m.Bridge(self.root, sigma=sigma)
        definition = next(t for t in bridge.definitions() if t["name"] == "sigma_capture")
        self.assertEqual(definition["inputSchema"]["properties"]["capture_id"]["enum"], ["one", "two"])
        with self.assertRaises(ValueError):
            bridge.call("sigma_capture", {"capture_id": "outside", "resume": False})
        with patch.object(sigma.commands["one"], "capture", return_value={"status": "partial"}) as called:
            sigma.capture(False, "one")
            sigma.capture(True, "one")
            with self.assertRaises(ValueError):
                sigma.capture(True, "one")
            self.assertEqual(called.call_count, 2)
        restarted = m.SigmaBatch(self.root, sys.executable, "inputs/batch.json")
        with self.assertRaises(ValueError):
            restarted.capture(False, "two")
        (self.root / "inputs/batch.json").write_text('{}')
        with self.assertRaises(ValueError):
            sigma.capture(False, "one")


if __name__ == "__main__":
    unittest.main()
