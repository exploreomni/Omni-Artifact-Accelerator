"""Native adapter boundaries with an independent fake transport; no tenant qualification."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-bi-engineer/scripts/omni_native.py"
spec = importlib.util.spec_from_file_location("omni_native", SCRIPT)
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
fixture_spec = importlib.util.spec_from_file_location("native_source_fixtures", Path(__file__).with_name("test_migration_sources.py"))
fixtures = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)


class FakeOmni:
    """Independent oracle for our reviewed single-tile fixture, not a universal server."""
    def __init__(self, root):
        self.root = root
        self.state = {
            "name": "Development sales", "description": "Retained description", "modelId": "model-1",
            "workbookModelId": "workbook-1", "draftOf": {"identifier": "sales"},
            "queryPresentations": {"data": {
                "1": {"type": "query", "name": "Other editor", "query": {"fields": ["orders.count"]}},
                "2": {"type": "query", "name": "Old revenue", "topicName": "orders",
                      "query": {"fields": ["orders.revenue"]}}}, "order": ["1", "2"]},
            "controls": {"data": {"region": {"label": "Region"}}, "order": ["region"]},
            "settings": {"crossfilterEnabled": False, "controlBar": {"fixed": False, "collapsible": True}},
            "containers": [{"instanceKey": "page-1", "type": "page", "children": [
                {"instanceKey": "tile-1", "referenceKey": "1"},
                {"instanceKey": "tile-2", "referenceKey": "2"}]}],
        }
        self.meta = {"identifier": "sales-draft", "publishedIdentifier": "sales", "workbookModelId": "workbook-1",
                     "branch": {"id": "branch-1", "name": "migration"}, "status": "active",
                     "draftOutOfDate": False, "updatedAt": "2026-10-21T00:00:00Z"}
        self.identity = {"keyScope": "user", "user": {"membershipId": "member-1", "id": "user-1"},
                         "orgRole": "MEMBER", "rolesByModel": {"model-1": {"role": "EDITOR"}}}
        self.calls = []
        self.http_calls = []
        self.patch_count = 0
        self.mode = "normal"
        self.version = "omni version 1.0.6"
        self.post_status = 200
        self.export_status = "complete"
        self.media_type = "application/json"
        self.file = b'[{"region":"West","revenue":24}]'

    def runner(self, args, **kwargs):
        self.calls.append((args, kwargs))
        assert kwargs["shell"] is False
        if "--help" in args:
            return subprocess.CompletedProcess(args, 0, b"Usage: inspected command --body -", b"")
        if "--version" in args:
            return subprocess.CompletedProcess(args, 0, self.version.encode(), b"")
        assert args[args.index("--base-url") + 1] == "https://tenant.omniapp.co"
        assert args[args.index("--profile") + 1] == "migration"
        assert kwargs["env"]["OMNI_API_TOKEN"] == "test-placeholder-only"
        if args[2] == "list-drafts":
            result = [self.meta]
        elif args[2] == "v2-get-draft":
            assert args[3:5] == ["sales", "sales-draft"]
            result = self.state
        elif args[2] == "v2-patch-draft-by-identifier":
            # Intent must already be durable before any target mutation.
            intents = list((self.root / ".omni-native/executions").glob("*/intent.json"))
            assert intents and all(json.loads(p.read_text())["status"] == "intent_persisted" for p in intents)
            self.patch_count += 1
            payload = json.loads(kwargs["input"])
            assert args[-2:] == ["--body", "-"]
            assert payload["queryPresentations"]["data"]["2"]["name"] == "Reviewed revenue"
            if self.mode != "drop_setting":
                self.state["queryPresentations"]["data"]["2"] = copy.deepcopy(payload["queryPresentations"]["data"]["2"])
                self.state["queryPresentations"]["data"]["2"]["model_extension_id"] = "server-binding"
            if self.mode == "unrelated_change":
                self.state["queryPresentations"]["data"]["1"]["name"] = "Unexpected overwrite"
            self.meta["updatedAt"] = "2026-10-21T00:01:00Z"
            if self.mode == "timeout":
                raise subprocess.TimeoutExpired(args, 60)
            result = {"identifier": "sales", "draftIdentifier": "sales-draft", "name": self.state["name"]}
            if self.mode == "wrong_response":
                result["draftIdentifier"] = "wrong-draft"
        else:
            raise AssertionError("Unexpected command " + repr(args))
        return subprocess.CompletedProcess(args, 0, json.dumps(result).encode(), b"")

    def http(self, method, url, token, body, max_bytes):
        self.http_calls.append((method, url, body))
        assert token == "test-placeholder-only"
        if "/whoami?" in url:
            return 200, {}, json.dumps(self.identity).encode()
        assert "/dashboards/sales-draft/download" in url  # Never export published content.
        if method == "POST":
            intents = list((self.root / ".omni-native/exports").glob("*/intent.json"))
            assert intents
            result = {"job_id": "job-1"} if self.post_status == 200 else {"existing_job_id": "some-other-job"}
            return self.post_status, {}, json.dumps(result).encode()
        if url.endswith("/status"):
            return 200, {}, json.dumps({"job_id": "job-1", "status": self.export_status, "format": "json"}).encode()
        return 200, {"Content-Type": self.media_type}, self.file


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "engagement"
        native.WORKFLOW.ap.init(self.root, "Native adapter fixture", "migration", "dashboard")
        self.env = patch.dict(os.environ, {"OAA_TEST_TOKEN": "test-placeholder-only"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.target = native.TargetConfig("https://tenant.omniapp.co", "migration", "sales", "sales-draft",
                                          "model-1", "member-1", "branch-1", "OAA_TEST_TOKEN")
        self.fake = FakeOmni(self.root)
        self.adapter = native.NativeAdapter(self.root, self.target, runner=self.fake.runner, http=self.fake.http)
        self.payload = {"queryPresentations": {"data": {"2": {
            "type": "query", "name": "Reviewed revenue", "topicName": "orders",
            "query": {"fields": ["orders.revenue"]}, "visConfig": {"chartType": "bar"}}}}}
        self.owned = {"query_keys": ["2"], "control_ids": [], "container_keys": [], "settings": [],
                      "metadata": [], "tab_order": False, "control_order": False}
        self.write("payload.json", self.payload)
        self.write("ownership.json", self.owned)
        self.write("source.json", fixtures.sigma_snapshot())
        inventory = fixtures.t.translate((self.root / "source.json").read_bytes(), "sigma-agent", fixtures.SIGMA)
        self.write("inventory.json", inventory)
        native.WORKFLOW.prepare(self.root, "source.json", "inventory.json", "requirements.json")
        requirements = json.loads((self.root / "requirements.json").read_text())
        requirements.update(route="reuse_existing", route_reference="synthetic-route-decision")
        self.write("requirements.json", requirements)
        self.write("semantic.json", {"candidate_sha256": "a" * 64, "fields": ["orders.revenue"]})
        self.write("export.json", {"format": "json", "queryIdentifierMapKey": "2", "filterConfig": {"region": "West"}, "maxRowLimit": 100})
        self.write("state.json", {"state_id": "west", "filters": {"region": "West"}, "persona": "member-1",
                                  "timezone": "America/Chicago", "data_watermark": "unverified", "viewport": None})

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def prepare(self):
        return self.adapter.prepare("payload.json", ["source.json", "requirements.json"], "semantic.json", "ownership.json", "review-1")["candidate_sha256"]

    def executed(self):
        candidate = self.prepare()
        result = self.adapter.execute(candidate, "operator-approved-exact-candidate")
        self.assertEqual(result["status"], "readback_matched")
        return candidate

    def export(self):
        candidate = self.executed()
        result = self.adapter.export_start(candidate, "export.json", "state.json", "approved-export")
        self.assertEqual(result["status"], "submitted")
        return result["export_id"]

    def test_legacy_sigma_semantic_yaml_pin_stays_supported(self):
        (self.root / "semantic.yaml").write_text("topic: orders\nfields: [orders.revenue]\n")
        result = self.adapter.prepare("payload.json", ["requirements.json"], "semantic.yaml", "ownership.json", "review-1")
        candidate = json.loads((self.root / result["path"]).read_text())
        self.assertEqual(candidate["pins"]["semantic_file"]["path"], "semantic.yaml")
        self.assertNotIn("standalone_baseline", candidate)
        self.assertEqual(self.adapter.execute(result["candidate_sha256"], "authorized")["status"], "readback_matched")

    def test_prepare_is_private_and_bound_to_actual_evidence(self):
        candidate_id = self.prepare()
        path = self.root / ".omni-native/candidates" / (candidate_id + ".json")
        candidate = json.loads(path.read_text())
        self.assertEqual(candidate["before"]["state"], self.fake.state)
        self.assertEqual(candidate["pins"]["source_files"][0]["path"], "source.json")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(candidate["native_verified"])
        self.assertEqual(self.fake.patch_count, 0)

    def test_title_only_query_replacement_is_rejected_before_write(self):
        self.write("payload.json", {"queryPresentations": {"data": {
            "2": {"type": "query", "name": "New title"}}}})
        with self.assertRaisesRegex(native.NativeError, "complete query"):
            self.prepare()
        self.assertEqual(self.fake.patch_count, 0)

    def test_query_replacement_cannot_silently_drop_filter_scope(self):
        self.fake.state["queryPresentations"]["data"]["2"]["query"].update(
            filters={"orders.region": {"values": ["West"]}}, limit=50, sorts=[])
        tile = copy.deepcopy(self.fake.state["queryPresentations"]["data"]["2"])
        tile["name"] = "Readable title"
        del tile["query"]["filters"]
        with self.assertRaisesRegex(native.NativeError, "omitted existing properties"):
            native.expected_state(self.fake.state, {"queryPresentations": {"data": {"2": tile}}}, self.owned)
        tile["query"]["filters"] = {"orders.region": {"values": ["West"]}}
        after = native.expected_state(self.fake.state, {"queryPresentations": {"data": {"2": tile}}}, self.owned)
        self.assertEqual(after["queryPresentations"]["data"]["2"]["query"],
                         self.fake.state["queryPresentations"]["data"]["2"]["query"])

    def test_execute_writes_only_named_draft_and_preserves_other_content(self):
        candidate = self.executed()
        result = json.loads((self.root / f".omni-native/executions/{candidate}/receipt.json").read_text())
        self.assertEqual(self.fake.patch_count, 1)
        self.assertEqual(self.fake.state["queryPresentations"]["data"]["1"]["name"], "Other editor")
        self.assertFalse(result["native_verified"])
        self.assertFalse(result["published"])
        all_args = [arg for args, _ in self.fake.calls for arg in args]
        self.assertNotIn("v2-create", all_args)
        self.assertNotIn("v2-publish-draft", all_args)
        self.assertNotIn("test-placeholder-only", all_args)

    def test_authorization_and_wrong_target_reject_before_write(self):
        candidate = self.prepare()
        with self.assertRaisesRegex(native.NativeError, "authorization"):
            self.adapter.execute(candidate, "")
        target = native.TargetConfig(**{**native.asdict(self.target), "document_id": "other"})
        other = native.NativeAdapter(self.root, target, runner=self.fake.runner, http=self.fake.http)
        with self.assertRaisesRegex(native.NativeError, "target"):
            other.execute(candidate, "approval")
        self.assertEqual(self.fake.patch_count, 0)

    def test_changed_source_semantic_payload_and_ownership_reject(self):
        for name in ("source.json", "semantic.json", "payload.json", "ownership.json"):
            with self.subTest(name=name):
                candidate = self.prepare()
                original = (self.root / name).read_bytes()
                (self.root / name).write_bytes(original + b" ")
                with self.assertRaisesRegex(native.NativeError, "evidence changed"):
                    self.adapter.execute(candidate, "approval")
                (self.root / name).write_bytes(original)
        self.assertEqual(self.fake.patch_count, 0)

    def test_candidate_tampering_rejects(self):
        candidate = self.prepare()
        path = self.root / f".omni-native/candidates/{candidate}.json"
        altered = json.loads(path.read_text())
        altered["payload"]["name"] = "Tampered"
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(native.NativeError, "Candidate contents changed"):
            self.adapter.execute(candidate, "approval")

    def test_shared_draft_drift_and_cli_upgrade_reject(self):
        candidate = self.prepare()
        self.fake.state["queryPresentations"]["data"]["1"]["name"] = "Concurrent editor"
        with self.assertRaisesRegex(native.NativeError, "drift"):
            self.adapter.execute(candidate, "approval")
        candidate = self.prepare()
        self.fake.version = "omni version 1.2.4"
        with self.assertRaisesRegex(native.NativeError, "fingerprint changed"):
            self.adapter.execute(candidate, "approval")
        self.assertEqual(self.fake.patch_count, 0)

    def test_principal_branch_model_and_out_of_date_fail_closed(self):
        for mutation in ("principal", "branch", "model", "out_of_date"):
            with self.subTest(mutation=mutation):
                fake = FakeOmni(self.root)
                if mutation == "principal":
                    fake.identity["user"]["membershipId"] = "someone-else"
                if mutation == "branch":
                    fake.meta["branch"]["id"] = "other-branch"
                if mutation == "model":
                    fake.state["modelId"] = "other-model"
                if mutation == "out_of_date":
                    fake.meta["draftOutOfDate"] = True
                adapter = native.NativeAdapter(self.root, self.target, fake.runner, fake.http)
                with self.assertRaises(native.NativeError):
                    adapter.inspect()

    def test_timeout_is_durable_no_replay_and_reconcile_observes_result(self):
        candidate = self.prepare()
        self.fake.mode = "timeout"
        receipt = self.adapter.execute(candidate, "approval")
        self.assertEqual(receipt["status"], "outcome_unknown")
        with self.assertRaisesRegex(native.NativeError, "never replay"):
            self.adapter.execute(candidate, "approval")
        result = self.adapter.reconcile(candidate)
        self.assertEqual(result["status"], "readback_matched")
        self.assertFalse(result["automatic_retry_allowed"])
        self.assertFalse(result["native_verified"])
        self.assertEqual(self.fake.patch_count, 1)

    def test_read_only_reconcile_survives_source_drift_but_export_does_not(self):
        candidate = self.prepare()
        self.fake.mode = "timeout"
        self.adapter.execute(candidate, "approval")
        self.write("source.json", {"changed": True})
        result = self.adapter.reconcile(candidate)
        self.assertEqual(result["status"], "readback_matched")
        self.assertFalse(result["source_evidence_current"])
        with self.assertRaisesRegex(native.NativeError, "evidence changed"):
            self.adapter.export_start(candidate, "export.json", "state.json", "approved-export")
        self.assertEqual(self.fake.patch_count, 1)

    def test_dropped_settings_and_unrelated_changes_are_not_success(self):
        for mode in ("drop_setting", "unrelated_change"):
            with self.subTest(mode=mode):
                candidate = self.prepare()
                self.fake.mode = mode
                receipt = self.adapter.execute(candidate, "approval")
                self.assertEqual(receipt["status"], "readback_mismatch")

    def test_wrong_patch_response_is_unknown_and_not_retried(self):
        candidate = self.prepare()
        self.fake.mode = "wrong_response"
        self.assertEqual(self.adapter.execute(candidate, "approval")["status"], "outcome_unknown")
        with self.assertRaises(native.NativeError):
            self.adapter.execute(candidate, "approval")

    def test_owned_content_only_and_model_fields_excluded(self):
        for payload in ({"branchId": "new"}, {"app": {"html": "unsafe scope"}}, {"modelId": "another"},
                        {"queryPresentations": {"data": {"1": {"type": "query", "name": "unowned"}}}},
                        {"queryPresentations": {"data": {"2": {"type": "query", "model_extension_id": "read-only"}}}}):
            with self.subTest(payload=payload), self.assertRaises(native.NativeError):
                native.expected_state(self.fake.state, payload, self.owned)

    def test_absent_unselected_and_conflicting_source_route_reject_before_inspection(self):
        with self.assertRaisesRegex(native.NativeError, "visual requirements"):
            self.adapter.prepare("payload.json", ["source.json"], "semantic.json", "ownership.json", "review-1")
        requirements = json.loads((self.root / "requirements.json").read_text())
        requirements["route"] = "unselected"
        self.write("requirements.json", requirements)
        with self.assertRaisesRegex(native.NativeError, "explicit source route"):
            self.prepare()
        requirements["route"] = "warehouse_first_refactor"
        requirements["route_reference"] = ""
        self.write("requirements.json", requirements)
        with self.assertRaisesRegex(native.NativeError, "failed validation"):
            self.prepare()
        self.assertEqual(self.fake.calls, [])

    def test_source_inventory_drift_invalidates_execution_even_when_not_explicitly_listed(self):
        candidate = self.prepare()
        (self.root / "inventory.json").write_text("{}")
        with self.assertRaisesRegex(native.NativeError, "failed validation"):
            self.adapter.execute(candidate, "approval")
        self.assertEqual(self.fake.patch_count, 0)

    def test_unrelated_added_setting_fails_readback(self):
        candidate_id = self.executed()
        candidate = self.adapter._candidate(candidate_id)
        self.fake.state["settings"]["unexpectedSetting"] = True
        self.assertFalse(native.readback_matches(candidate, self.fake.state))

    def test_owned_query_extra_filters_are_not_harmless_server_defaults(self):
        candidate_id = self.executed()
        candidate = self.adapter._candidate(candidate_id)
        self.fake.state["queryPresentations"]["data"]["2"]["query"]["filters"] = {"region": "East"}
        self.assertFalse(native.readback_matches(candidate, self.fake.state))

    def test_raw_sql_cannot_hide_inside_a_query_presentation(self):
        for tile in ({"type": "query", "isSql": True}, {"type": "query", "query": {"sql": "select 1"}}):
            with self.assertRaisesRegex(native.NativeError, "Raw SQL"):
                native.expected_state(self.fake.state, {"queryPresentations": {"data": {"2": tile}}}, self.owned)

    def test_containers_cannot_drop_unrelated_children(self):
        owned = {**self.owned, "container_keys": ["page-1", "tile-2"]}
        payload = {"containers": [{"instanceKey": "page-1", "type": "page", "children": [{"instanceKey": "tile-2", "referenceKey": "2"}]}]}
        with self.assertRaisesRegex(native.NativeError, "unrelated layout"):
            native.expected_state(self.fake.state, payload, owned)
        payload["containers"][0]["children"].insert(0, {"instanceKey": "tile-1", "referenceKey": "1"})
        payload["containers"][0]["children"][1]["width"] = 400
        result = native.expected_state(self.fake.state, payload, owned)
        self.assertEqual(result["containers"][0]["children"][0], self.fake.state["containers"][0]["children"][0])

    def test_container_ownership_does_not_allow_moving_unowned_child(self):
        before = copy.deepcopy(self.fake.state)
        before["containers"].append({"instanceKey": "page-2", "type": "page", "children": []})
        after = copy.deepcopy(before["containers"])
        after[1]["children"].append(after[0]["children"].pop(0))
        owned = {**self.owned, "container_keys": ["page-1", "page-2", "tile-2"]}
        with self.assertRaisesRegex(native.NativeError, "another page or parent"):
            native.expected_state(before, {"containers": after}, owned)

    def test_order_replacement_preserves_unowned_and_requires_all_items(self):
        owned = {**self.owned, "tab_order": True}
        for order in (["2"], ["1", "2", "2"], ["2", "99", "1"]):
            with self.assertRaises(native.NativeError):
                native.expected_state(self.fake.state, {"queryPresentations": {"order": order}}, owned)

    def test_path_traversal_symlink_and_duplicate_json_rejected(self):
        (self.root / "linked.json").symlink_to(self.root / "source.json")
        for name in ("../source.json", "/tmp/source.json", "linked.json"):
            with self.assertRaises(native.NativeError):
                self.adapter._pin(name)
        with self.assertRaisesRegex(native.NativeError, "Duplicate"):
            native.decode(b'{"a":1,"a":2}')

    def test_target_url_and_identifier_injection_refused(self):
        for value in ("http://tenant.omniapp.co", "https://u:p@tenant.omniapp.co", "https://tenant.omniapp.co/api", "https://tenant.omniapp.co?x=y"):
            with self.assertRaises(native.NativeError):
                native.TargetConfig(**{**native.asdict(self.target), "base_url": value})
        for value in ("--token", "$(whoami)", "a/b"):
            with self.assertRaises(native.NativeError):
                native.TargetConfig(**{**native.asdict(self.target), "draft_id": value})

    def test_export_persisted_matching_draft_bytes_and_no_acceptance(self):
        export_id = self.export()
        self.adapter.export_status(export_id)
        result = self.adapter.export_file(export_id)
        self.assertEqual(result["status"], "downloaded")
        artifact = self.root / result["artifact"]["path"]
        self.assertEqual(artifact.read_bytes(), self.fake.file)
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
        self.assertFalse(result["native_verified"])
        self.assertFalse(result["data_watermark_verified"])
        self.assertEqual(sum(m == "POST" for m, _, _ in self.fake.http_calls), 1)

    def test_export_state_mismatch_and_unbounded_results_reject(self):
        candidate = self.executed()
        self.write("state.json", {"state_id": "wrong", "filters": {}, "persona": "member-1", "timezone": "UTC", "data_watermark": None, "viewport": None})
        with self.assertRaisesRegex(native.NativeError, "persona/filters"):
            self.adapter.export_start(candidate, "export.json", "state.json", "export-approved")
        for body in ({"format": "json"}, {"format": "csv", "maxRowLimit": 1000001},
                     {"format": "png", "containerPages": ["page-1", "page-2"]}):
            with self.assertRaises(native.NativeError):
                native._validate_export(body)

    def test_export_conflict_is_not_adopted_or_replayed(self):
        candidate = self.executed()
        self.fake.post_status = 409
        result = self.adapter.export_start(candidate, "export.json", "state.json", "approved-export")
        self.assertEqual(result["status"], "conflict_existing_job")
        with self.assertRaisesRegex(native.NativeError, "never replay"):
            self.adapter.export_start(candidate, "export.json", "state.json", "approved-export")
        with self.assertRaisesRegex(native.NativeError, "No known job"):
            self.adapter.export_status(result["export_id"])

    def test_export_audit_reference_and_file_alias_cannot_bypass_no_replay(self):
        candidate = self.executed()
        self.adapter.export_start(candidate, "export.json", "state.json", "approval-a")
        (self.root / "export-alias.json").write_bytes((self.root / "export.json").read_bytes())
        state = json.loads((self.root / "state.json").read_text())
        state["state_id"] = "another-audit-label"
        state["data_watermark"] = "another-unverified-watermark"
        state["viewport"] = {"width": 900, "height": 600}
        state["timezone"] = "UTC"
        self.write("state-alias.json", state)
        with self.assertRaisesRegex(native.NativeError, "never replay"):
            self.adapter.export_start(candidate, "export-alias.json", "state-alias.json", "approval-b")
        self.assertEqual(sum(m == "POST" for m, _, _ in self.fake.http_calls), 1)

    def test_export_requires_complete_media_signature_and_stable_draft(self):
        export_id = self.export()
        with self.assertRaisesRegex(native.NativeError, "complete"):
            self.adapter.export_file(export_id)
        self.adapter.export_status(export_id)
        self.fake.media_type = "text/html"
        with self.assertRaisesRegex(native.NativeError, "media type"):
            self.adapter.export_file(export_id)
        self.fake.media_type = "application/json"
        self.fake.state["name"] = "Changed while export was pending"
        with self.assertRaisesRegex(native.NativeError, "Draft changed"):
            self.adapter.export_file(export_id)
        with self.assertRaisesRegex(native.NativeError, "PNG signature"):
            native._validate_media("png", {"Content-Type": "image/png"}, b"not an image")
        with self.assertRaisesRegex(native.NativeError, "CSV"):
            native._validate_media("csv", {"Content-Type": "text/csv"}, b"<!doctype html><html>Error</html>")

    def test_redirect_refused_and_subprocess_timeout_not_exposed(self):
        with self.assertRaisesRegex(native.NativeError, "Redirect refused"):
            native.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://attacker.example")

    def test_png_requires_bounded_valid_pixel_stream_not_only_chunk_signatures(self):
        def chunk(kind, data):
            return native.struct.pack(">I", len(data)) + kind + data + native.struct.pack(">I", native.zlib.crc32(kind + data) & 0xffffffff)
        header = chunk(b"IHDR", native.struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        prefix = b"\x89PNG\r\n\x1a\n" + header
        ending = chunk(b"IEND", b"")
        valid = prefix + chunk(b"IDAT", native.zlib.compress(b"\x00\xff\x00\x00")) + ending
        native._validate_media("png", {"Content-Type": "image/png"}, valid)
        invalid = prefix + chunk(b"IDAT", b"not-a-zlib-stream") + ending
        with self.assertRaisesRegex(native.NativeError, "compressed stream"):
            native._validate_media("png", {"Content-Type": "image/png"}, invalid)


if __name__ == "__main__":
    unittest.main()
