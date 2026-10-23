"""Requirement routing and declared-dependency coverage on a synthetic engagement."""
import copy
import json
import subprocess
import sys
import unittest
import test_design_intent as fixture

D = fixture.D


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.IntentTests()
        self.base.setUp()
        self.addCleanup(self.base.tearDown)
        self.root = self.base.root
        self.base.value.update(branding="none", website=None, assets=[], requirements=[])
        self.req = {"id": "investigate", "category": "experience", "purpose": "Investigate a collection",
                    "surfaces": ["app"], "required": True, "origin": "user", "disposition": "selected",
                    "value": "An editorial investigation", "asset_ids": [], "decision_ref": "synthetic brief",
                    "contexts": [{"id": "workspace", "appearance": "light", "state": "ready"}],
                    "delivery": {"source_ref": "inputs/brief.txt: request", "owner": "app-designer",
                                 "behavior": "Select a collection, inspect the supporting records, then return with selection retained.",
                                 "destinations": ["investigation"], "dependency_paths": ["inputs/native-shape.json"],
                                 "capabilities": ["insight", "custom-visualization"]}}
        self.base.value["requirements"] = [self.req]
        (self.root / "inputs/native-shape.json").write_text('{"key":"collection.id","evidence":"synthetic"}')
        (self.root / "contracts/resolved.json").write_text(json.dumps({
            "brand_contract": "contracts/tokens.json", "destinations": [{
                "id": "investigation", "purpose": "Understand collection demand", "primary_action": "Select a collection",
                "evidence": "Request counts with exact records", "drill": "Open collection dossier",
                "return": "Restore the selection", "responsive": "One column and intentional scrolling"}]}))

    def test_routes_only_required_capabilities_and_pins_explicit_runtime_input(self):
        self.base.select()
        result = D.P.plan(self.root)
        roles = {r["role"]: r for r in result["roles"]}
        self.assertIn("data-storyteller", roles)
        self.assertNotIn("motion-designer", roles)
        self.assertEqual(roles["app-engineer"]["modules"], ["references/advanced-visualization.md"])
        self.assertEqual(result["delivery_coverage"]["status"], "ready_for_review")
        self.assertEqual(result["delivery_coverage"]["native_verification"], "not_assessed")
        packet = D.P.packet(self.root, "app-engineer", ["contracts/query.json"], self.root / "tasks/a.json")
        self.assertIn("inputs/native-shape.json", {r["path"] for r in packet["inputs"]})
        (self.root / "inputs/native-shape.json").write_text('{"key":"changed"}')
        self.assertEqual(D.P.packet_check(self.root, "tasks/a.json")["status"], "inconsistent")

    def test_incomplete_destination_and_requirement_are_reported_without_blocking_provisional_selection(self):
        self.req["delivery"].pop("behavior")
        self.req["delivery"]["destinations"].append("unknown")
        self.base.select()
        report = D.P.experience_check(self.root)
        self.assertEqual(report["status"], "incomplete")
        codes = {f["code"] for f in report["findings"]}
        self.assertIn("missing_behavior", codes)
        self.assertIn("destination_missing:app/unknown", codes)
        self.assertFalse(report["publication_authorized"])

    def test_legacy_intent_remains_valid_without_implied_delivery_completion(self):
        self.req.pop("delivery")
        self.base.select()
        self.assertEqual(D.check(self.root)["status"], "consistent")
        self.assertEqual(D.P.experience_check(self.root)["status"], "not_assessed")

    def test_unknown_owner_capability_and_unsafe_dependency_fail_before_selection(self):
        for key, value in (("owner", "invented-agent"), ("capabilities", ["automatic-approval"]),
                           ("dependency_paths", ["../secret"])):
            with self.subTest(key=key):
                spec = copy.deepcopy(self.base.value)
                spec["requirements"][0]["delivery"][key] = value
                with self.assertRaises(ValueError):
                    D.validate(spec, D.P.load_project(self.root)[1])

    def test_cli_and_assigned_packet_recheck_preserve_tracked_contract(self):
        self.base.select()
        ap = D.P
        raw = ap.packet(self.root, "app-engineer", ["contracts/query.json"], None)
        assignment = {"schema_version": 1, "task_id": "collection-view", "domain_id": "library", "stage": "app",
                      "role": "app-engineer", "scope_ids": ["investigate"], "objective": "Build the collection investigation",
                      "outputs": ["deliverables/collection.js"], "acceptance": ["Retain identity on return"],
                      "input_bindings": {r["path"]: r["sha256"] for r in raw["inputs"]}, "dependencies": {},
                      "unknowns": ["Native observation unavailable"], "authoring_mode": "provisional"}
        ap.packet(self.root, "app-engineer", ["contracts/query.json"], self.root / "tasks/assigned.json", assignment)
        self.assertEqual(ap.packet_check(self.root, "tasks/assigned.json")["status"], "consistent")
        saved = json.loads((self.root / "tasks/assigned.json").read_text())
        saved["assignment_sha256"] = "0" * 64
        (self.root / "tasks/assigned.json").write_text(json.dumps(saved))
        self.assertEqual(ap.packet_check(self.root, "tasks/assigned.json")["status"], "inconsistent")
        script = fixture.PATH.with_name("analyst_project.py")
        result = subprocess.run([sys.executable, str(script), "experience-check", "--project", str(self.root)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ready_for_review")

    def test_tracked_dispatch_rejects_superseded_selection_even_when_old_files_are_unchanged(self):
        self.base.select()
        ap = D.P
        raw = ap.packet(self.root, "app-engineer", ["contracts/query.json"], None)
        assignment = {"schema_version": 1, "task_id": "slice", "domain_id": "library", "stage": "app",
                      "role": "app-engineer", "scope_ids": ["investigate"], "objective": "Build the slice",
                      "outputs": ["deliverables/slice.js"], "acceptance": ["Retain selection"],
                      "input_bindings": {r["path"]: r["sha256"] for r in raw["inputs"]}, "dependencies": {},
                      "unknowns": [], "authoring_mode": "provisional"}
        ap.packet(self.root, "app-engineer", ["contracts/query.json"], self.root / "tasks/slice.json", assignment)
        ops = ap.routing_helper("task_operations")
        ops.claim(self.root, {"attempt_id": "slice-1", "packet": "tasks/slice.json"})
        self.req["delivery"]["behavior"] = "Inspect then return with selection and time scope retained."
        self.base.select("two")
        with self.assertRaisesRegex(ValueError, "context changed"):
            ops.prepare_dispatch(self.root, {"attempt_id": "slice-1"})

    def test_deferred_and_dashboard_requirements_do_not_force_app_specialists(self):
        self.req["delivery"]["capabilities"] = ["motion"]
        self.req["disposition"] = "deferred"
        self.base.select()
        plan = D.P.plan(self.root)
        self.assertNotIn("motion-designer", {r["role"] for r in plan["roles"]})
        self.assertEqual(plan["delivery_coverage"]["status"], "incomplete")
        self.assertIn("requirement_deferred", {r["code"] for r in plan["delivery_coverage"]["findings"]})
        q = D.P.experience_helper()
        state = {"status": "consistent", "selected": None, "selections": [], "findings": [],
                 "requirements": [copy.deepcopy(self.req)]}
        state["requirements"][0].update(surfaces=["dashboard"], disposition="selected")
        report = q.inspect(self.root, state, D.P)
        self.assertNotIn("motion-designer", report["role_requirements"])
        self.assertIn("app_capability_on_dashboard:motion", {f["code"] for f in report["findings"]})


if __name__ == "__main__":
    unittest.main()
