"""Exchange boundaries and stale-evidence behavior, with independent synthetic cases."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-backend-handoff/scripts/cowork.py"
spec = importlib.util.spec_from_file_location("cowork", SCRIPT)
cowork = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cowork)
ap = cowork.ap


class CoworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "frontend"
        ap.init(self.root, "Synthetic round trip", "migration", "both")
        self.review = {
            "schema_version": 1, "kind": "omni_semantic_handoff", "version": "omni-handoff-v1",
            "pins": {"source_fingerprint": "1" * 64, "context_sha256": "2" * 64,
                     "model_candidate_sha256": "3" * 64, "model_context_sha256": "4" * 64,
                     "target": {"warehouse": "snowflake", "framework": "dbt"}},
            "topics": [{"id": "orders", "base_view": "orders"}],
            "metrics": [{"id": "orders.revenue", "topic": "orders", "definition_sha256": "5" * 64}],
            "dictionary": [{"id": "orders.revenue", "topic": "orders", "kind": "measure", "definition_sha256": "5" * 64}],
            "dependencies": [], "decisions": [], "unknowns": [],
        }
        self.old = self.write_review("old.json", self.review)
        ap.import_dma(self.root, self.old)
        self.request_spec = {
            "schema_version": 1, "kind": "analyst_backend_request_spec", "request_id": "revenue-r1",
            "route": "warehouse_first_refactor", "route_reference": "synthetic-test-choice", "source_platform": "sigma",
            "requirements": [{"id": "net-revenue", "question": "Which refunds are excluded?", "change_class": "metric",
                "frontend_asset_ids": ["revenue-screen"], "metric_ids": ["orders.revenue"],
                "expected_cases": [{"case_id": "refund", "expectation": "A full refund produces zero net revenue."}]}],
            "consumer_bindings": [
                {"asset_id": "revenue-screen", "topic_ids": ["orders"], "field_ids": ["orders.revenue"], "dependency_complete": True},
                {"asset_id": "employee-screen", "topic_ids": ["people"], "field_ids": ["people.count"], "dependency_complete": True},
                {"asset_id": "unknown-screen", "topic_ids": [], "field_ids": [], "dependency_complete": False}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_review(self, name, value):
        value = copy.deepcopy(value)
        value.pop("handoff_sha256", None)
        value["handoff_sha256"] = ap.digest(ap.canonical(value))
        path = self.base / name
        path.write_text(json.dumps(value))
        return path

    def request(self, spec=None):
        value = spec or self.request_spec
        path = "contracts/" + value["request_id"] + ".json"
        (self.root / path).write_text(json.dumps(value))
        result = cowork.create_request(self.root, path, ["contracts/metrics.json"])
        return Path(result["path"])

    def resolutions(self, request, action="semantic_candidate"):
        value = json.loads(request.read_text())
        return {"schema_version": 1, "kind": "analyst_backend_resolutions", "request_sha256": value["sha256"],
            "backend_action": action, "requirements": [{"id": "net-revenue", "status": "proposed", "explanation": "Candidate defines refund treatment; verify independently."}]}

    def response(self, request, review=None, resolutions=None, name="response"):
        path = self.base / (name + "-resolutions.json")
        path.write_text(json.dumps(resolutions or self.resolutions(request)))
        output = self.base / name
        cowork.respond(request, review or self.old, path, output)
        return output

    def receive(self, request, response):
        return cowork.receive(self.root, str(request.relative_to(self.root)), response)

    def test_roundtrip_retains_old_evidence_without_acceptance(self):
        request = self.request()
        before = (self.root / "project.json").read_bytes()
        value = copy.deepcopy(self.review)
        value["pins"]["model_candidate_sha256"] = "a" * 64
        value["metrics"][0]["definition_sha256"] = "b" * 64
        value["dictionary"][0]["definition_sha256"] = "b" * 64
        response = self.response(request, self.write_review("new.json", value))
        received = self.receive(request, response)
        self.assertEqual(before, (self.root / "project.json").read_bytes())
        self.assertFalse(received["working_baseline_changed"])
        # Candidate hashes cover changes not visible in a minimized catalog: all declared consumers recheck.
        self.assertTrue(all(row["disposition"] == "recheck_required" for row in received["impact"]["consumer_impact"]))
        selected = cowork.select(self.root, "revenue-r1")
        self.assertFalse(selected["accepted"])
        self.assertFalse(selected["authorizes_target_write"])
        self.assertEqual(ap.project_check(self.root)["status"], "consistent")
        obj = json.loads((self.root / "project.json").read_text())
        self.assertEqual(len(obj["sources"]), 2)
        self.assertTrue((self.root / "inputs/dma-catalog.json").exists())
        self.assertEqual(cowork.select(self.root, "revenue-r1")["status"], "candidate_already_selected")
        packet = ap.packet(self.root, "bi-engineer", [selected["catalog_path"]], self.root / "tasks/current.json")
        self.assertEqual(packet["current_dma_catalog"], selected["catalog_path"])
        # New cycles pin the newly selected baseline, without resetting discovery.
        revised = copy.deepcopy(self.request_spec)
        revised["request_id"] = "revenue-r2"
        next_request = self.request(revised)
        self.assertEqual(json.loads(next_request.read_text())["baseline_catalog"]["path"], selected["catalog_path"])

    def test_unchanged_baseline_does_not_invalidate_known_independent_consumers(self):
        request = self.request()
        response = self.response(request, resolutions=self.resolutions(request, "clarification"))
        result = self.receive(request, response)
        impact = {row["asset_id"]: row for row in result["impact"]["consumer_impact"]}
        self.assertEqual(impact["employee-screen"]["disposition"], "no_detected_binding_change")
        self.assertEqual(impact["revenue-screen"]["disposition"], "recheck_required")
        self.assertIn("request_expectations_require_review", impact["revenue-screen"]["reasons"])
        self.assertEqual(impact["unknown-screen"]["disposition"], "recheck_required")
        self.assertFalse(impact["employee-screen"]["accepted"])

    def test_direct_route_refuses_warehouse_action_and_bad_resolution_accounting(self):
        self.request_spec["route"] = "omni_semantic_reconstruction"
        request = self.request()
        with self.assertRaisesRegex(ValueError, "violates selected route"):
            self.response(request, resolutions=self.resolutions(request, "warehouse_and_semantic_candidate"))
        for mutation in ("missing", "duplicate", "accepted"):
            resolutions = self.resolutions(request)
            if mutation == "missing":
                resolutions["requirements"] = []
            elif mutation == "duplicate":
                resolutions["requirements"] *= 2
            else:
                resolutions["requirements"][0]["status"] = "accepted"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.response(request, resolutions=resolutions)

    def test_reuse_and_unselected_cannot_hide_new_models_as_clarification(self):
        value = copy.deepcopy(self.review)
        value["pins"]["model_candidate_sha256"] = "c" * 64
        changed = self.write_review("changed.json", value)
        for route in ("reuse_existing", "unselected"):
            request_spec = copy.deepcopy(self.request_spec)
            request_spec.update(request_id=route, route=route)
            request = self.request(request_spec)
            with self.subTest(route=route), self.assertRaisesRegex(ValueError, "exact baseline"):
                self.response(request, changed, self.resolutions(request, "clarification"), route)

    def test_stale_frontend_inputs_refuse_receipt_and_selection(self):
        request = self.request()
        response = self.response(request)
        metrics = self.root / "contracts/metrics.json"
        old = metrics.read_bytes()
        metrics.write_text("{}")
        with self.assertRaisesRegex(ValueError, "frontend input changed"):
            self.receive(request, response)
        metrics.write_bytes(old)
        self.receive(request, response)
        metrics.write_text("{}")
        with self.assertRaisesRegex(ValueError, "frontend input changed"):
            cowork.select(self.root, "revenue-r1")

    def test_superseded_baseline_refuses_pending_response(self):
        first = self.request()
        spec = copy.deepcopy(self.request_spec)
        spec["request_id"] = "parallel-r2"
        second = self.request(spec)
        response1 = self.response(first)
        response2 = self.response(second, name="second-response")
        self.receive(first, response1)
        cowork.select(self.root, "revenue-r1")
        with self.assertRaisesRegex(ValueError, "superseded"):
            self.receive(second, response2)

    def test_response_tampering_wrong_request_and_changed_exchange_rejected(self):
        request = self.request()
        response = self.response(request)
        path = response / "response.json"
        original = path.read_bytes()
        value = json.loads(original)
        value["request_sha256"] = "0" * 64
        value.pop("sha256")
        path.write_text(json.dumps(cowork.sealed(value)))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.receive(request, response)
        path.write_bytes(original)
        review = response / "semantic-review.json"
        raw = review.read_bytes()
        review.write_text("{}")
        with self.assertRaisesRegex(ValueError, "candidate bytes changed"):
            self.receive(request, response)
        review.write_bytes(raw)
        self.receive(request, response)
        (self.root / "exchanges/revenue-r1/impact.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            cowork.select(self.root, "revenue-r1")

    def test_net_new_candidate_requires_explicit_route(self):
        self.root = self.base / "new-frontend"
        ap.init(self.root, "Net new", "net-new", "dashboard")
        self.request_spec["route"] = "unselected"
        request = self.request()
        with self.assertRaisesRegex(ValueError, "without a baseline"):
            self.response(request, resolutions=self.resolutions(request, "clarification"))
        revised = copy.deepcopy(self.request_spec)
        revised.update(request_id="selected-r2", route="warehouse_first_refactor")
        request = self.request(revised)
        self.receive(request, self.response(request, name="new-response"))
        self.assertEqual(cowork.select(self.root, "selected-r2")["status"], "local_candidate_selected")

    def test_registered_input_drift_and_request_size_rejected(self):
        p = self.root / "inputs/context.txt"
        p.write_text("original")
        ap.register(self.root, "sources", "inputs/context.txt", "source-context")
        p.write_text("different")
        with self.assertRaisesRegex(ValueError, "registered input changed"):
            cowork.file_pin(self.root, "inputs/context.txt", ap.load_project(self.root)[1])
        p = self.root / "inputs/large.txt"
        p.write_text("x" * ap.PACKET_BYTES)
        spec_path = self.root / "contracts/request.json"
        spec_path.write_text(json.dumps(self.request_spec))
        with self.assertRaisesRegex(ValueError, "exceed"):
            cowork.create_request(self.root, "contracts/request.json", ["inputs/large.txt"])

    def test_path_alias_cannot_bypass_registered_source_pin(self):
        path = self.root / "inputs/source.json"
        path.write_text('{"revision":1}')
        ap.register(self.root, "sources", "inputs/source.json", "frozen-source")
        path.write_text('{"revision":2}')
        spec_path = self.root / "contracts/request.json"
        spec_path.write_text(json.dumps(self.request_spec))
        for alias in ("inputs/./source.json", "inputs//source.json", "./inputs/source.json"):
            with self.subTest(alias=alias), self.assertRaisesRegex(ValueError, "canonical relative"):
                cowork.create_request(self.root, "contracts/request.json", [alias])
            with self.subTest(alias=alias), self.assertRaisesRegex(ValueError, "canonical relative"):
                ap.packet(self.root, "bi-engineer", [alias], self.root / "tasks/alias.json")
        self.assertEqual(ap.project_check(self.root)["status"], "inconsistent")

    def test_unknown_changed_backend_pin_requires_conservative_recheck(self):
        request = self.request()
        candidate = copy.deepcopy(self.review)
        candidate["pins"]["security_policy_sha256"] = "f" * 64
        response = self.response(request, self.write_review("security-change.json", candidate))
        result = self.receive(request, response)
        impact = {row["asset_id"]: row for row in result["impact"]["consumer_impact"]}
        self.assertEqual(impact["employee-screen"]["disposition"], "recheck_required")
        self.assertIn("changed_security_policy_sha256", impact["employee-screen"]["reasons"])


if __name__ == "__main__":
    unittest.main()
