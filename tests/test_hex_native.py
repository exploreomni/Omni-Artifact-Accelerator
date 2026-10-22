"""Hex actual source → exact existing dashboard controls and semantic baseline."""
import copy
from pathlib import Path
import unittest

import test_hex_capture as source
import test_looker_native as prior

n, s, v = prior.n, prior.s, prior.v


class HexNativeTests(unittest.TestCase):
    setUp = prior.LookerNativeTests.setUp
    write = prior.LookerNativeTests.write
    capture = prior.LookerNativeTests.capture
    prepare = prior.LookerNativeTests.prepare
    proof = prior.LookerNativeTests.proof
    test_arbitrary_semantic_pin_rejected = prior.LookerNativeTests.test_looker_cannot_use_arbitrary_semantic_pin
    test_control_cannot_hide_in_query_binding = prior.LookerNativeTests.test_missing_control_is_not_hidden_by_query_binding
    test_control_query_scope_order_model_drift = prior.LookerNativeTests.test_control_query_scope_order_and_model_drift_prevent_write

    def configure(self, both=False):
        if both:
            project = v.load(self.root, "project.json")
            project["surfaces"] = ["dashboard", "app"]
            self.write("project.json", project)
        result = source.capture_fixture(self.root / "inputs/hex-capture")
        self.original = str(Path(result["output"]).relative_to(self.root))
        inventory = source.module("translate_artifact").translate((self.root / self.original).read_bytes(), "hex-capture")
        self.write("inventory.json", inventory)
        v.prepare(self.root, self.original, "inventory.json", "hex-requirements.json")
        self.write("requirements.json", v.load(self.root, "hex-requirements.json"))
        self.config = prior.configure_dashboard(self.root)
        self.adapter, self.fake = self.config["adapter"], self.config["fake"]

    def test_actual_source_dashboard_preserves_controls_and_query_placement_denominator(self):
        self.configure()
        before = copy.deepcopy(self.fake.state["controls"])
        _, spec = self.proof()
        proof = s.verify_delivery(self.root, spec)
        req = v.load(self.root, "requirements.json")
        self.assertEqual(len(s.query_source_keys(req)), 8)  # chart plus seven distinct query placements
        self.assertEqual(before, self.fake.state["controls"])
        self.assertTrue(proof["gaps"])
        self.assertFalse(proof["native_verified"])
        self.assertFalse([g for g in proof["gaps"] if g["code"] in {"source_control_not_bound", "source_query_not_bound"}])

    def test_missing_placement_deferred_controls_remain_gaps(self):
        self.configure()
        req = v.load(self.root, "requirements.json")
        controls = s.control_source_keys(req)
        for item in req["items"]:
            if item["asset_key"] in controls:
                item.update(disposition="defer", scope_decision={"reason": "unqualified-control", "reference": "synthetic-review"})
        self.write("requirements.json", req)
        spec = v.load(self.root, self.config["baseline_spec"])
        spec.pop("control_bindings")
        omitted = spec["bindings"][0]["source_asset_keys"].pop()
        self.write(self.config["baseline_spec"], spec)
        _, proof_spec = self.proof()
        proof = s.verify_delivery(self.root, proof_spec)
        self.assertIn({"code": "source_query_not_bound", "asset_key": omitted}, proof["gaps"])
        self.assertTrue(all({"code": "deferred_source_asset", "asset_key": key} in proof["gaps"] for key in controls))

    def test_unqualified_legacy_cell_does_not_invent_query_obligation(self):
        req = {"surface": ["dashboard"], "items": [{"asset_key": "unknown-cell", "kind": "cell", "disposition": "migrate",
            "source_identity": {"source_platform": "hex"}}]}
        self.assertEqual(s.query_source_keys(req), set())
        req["items"][0]["source_identity"]["query_visual"] = True
        self.assertEqual(s.query_source_keys(req), {"unknown-cell"})

    def test_surface_assignments_do_not_require_app_only_controls_on_dashboard(self):
        self.configure(both=True)
        req = v.load(self.root, "requirements.json")
        control_keys = s.control_source_keys(req)
        for item in req["items"]:
            if item["asset_key"] in control_keys:
                item.update(target_surfaces=["app"], assignment_reference="reviewed-app-input")
        self.write("requirements.json", req)
        self.config = prior.configure_dashboard(self.root, prefix="assigned")
        self.adapter, self.fake = self.config["adapter"], self.config["fake"]
        self.assertEqual(s.control_source_keys(req), set())
        self.assertEqual(s.control_source_keys(req, "app"), control_keys)
        self.capture()
        candidate = self.prepare()
        self.assertEqual(self.adapter.execute(candidate["candidate_sha256"], "synthetic-exact-authority")["status"], "readback_matched")


if __name__ == "__main__":
    unittest.main()
