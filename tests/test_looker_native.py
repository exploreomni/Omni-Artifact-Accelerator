"""Looker current-model/dashboard contracts with actual capture and fake Omni."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_standalone as prior
import test_looker_visual_bridge as source

n, m = prior.native, prior.m
v = n.WORKFLOW
s = n._standalone_module()


def configure_dashboard(root, requirements_path="requirements.json", prefix="dashboard"):
    """Existing project/requirements fixture; compatible with an actual DMA import."""
    root = Path(root)
    req = v.load(root, requirements_path)
    fake = prior.SemanticOmni(root)
    target = n.TargetConfig("https://tenant.omniapp.co", "migration", "sales", "sales-draft",
                            "model-1", "member-1", "branch-1", "OAA_TEST_TOKEN")
    adapter = n.NativeAdapter(root, target, runner=fake.runner, http=fake.http)
    def write(name, value):
        path = f"{prefix}-{name}.json"
        (root / path).write_text(json.dumps(value))
        return path
    payload = {"queryPresentations": {"data": {"2": {"type": "query", "name": "Reviewed revenue", "topicName": "orders",
        "query": {"fields": ["orders.revenue"]}, "visConfig": {"chartType": "bar"}}}}}
    ownership = {"query_keys": ["2"], "control_ids": [], "container_keys": [], "settings": [], "metadata": [],
                 "tab_order": False, "control_order": False}
    payload_path, ownership_path = write("payload", payload), write("ownership", ownership)
    baseline = {"schema_version": 1, "kind": "analyst_existing_omni_baseline_spec", "review_ref": "synthetic-existing-model",
        "requirements_path": requirements_path, "payload_path": payload_path, "ownership_path": ownership_path,
        "bindings": [{"source_asset_keys": sorted(s.query_source_keys(req)), "query_key": "2", "topic": "orders",
            "query": {"fields": ["orders.revenue"]}, "field_ids": ["orders.revenue"]}]}
    controls = s.control_source_keys(req)
    if controls:
        observed = {"syntheticField": "orders.region", "syntheticScope": ["2"], "mode": "single"}
        fake.state["controls"] = {"data": {"region": observed, "other": {"label": "unowned"}}, "order": ["region", "other"]}
        fake.topic["topic"]["views"][0]["dimensions"].append({"field_name": "region", "view_name": "orders",
            "fully_qualified_name": "orders.region", "data_type": "STRING", "sql": "${TABLE}.region"})
        evidence = write("control-review", {"limitation": "Synthetic observed config; no asserted creation grammar or native validation"})
        baseline["control_bindings"] = [{"source_asset_keys": sorted(controls), "control_id": "region", "expected_config": copy.deepcopy(observed),
            "field_bindings": [{"topic": "orders", "field_id": "orders.region", "config_pointer": "/syntheticField"}],
            "target_query_keys": ["2"], "scope_pointer": "/syntheticScope", "compatibility_reference": "synthetic-reviewed-control",
            "evidence_paths": [evidence]}]
    baseline_spec = write("baseline-spec", baseline)
    return {"adapter": adapter, "fake": fake, "baseline_spec": baseline_spec, "baseline_path": f"{prefix}-baseline.json",
            "payload_path": payload_path, "ownership_path": ownership_path, "requirements_path": requirements_path}


class LookerNativeTests(unittest.TestCase):
    setUp = prior.StandaloneTests.setUp
    write = prior.StandaloneTests.write

    def configure(self):
        result = source.capture_fixture(self.root / "inputs/looker-capture")
        self.original = str(Path(result["output"]).relative_to(self.root))
        self.write("inventory.json", result["inventory"])
        v.prepare(self.root, self.original, "inventory.json", "looker-requirements.json")
        req = v.load(self.root, "looker-requirements.json")
        req.update(route="reuse_existing", route_reference="synthetic-existing-model")
        self.write("requirements.json", req)
        self.config = configure_dashboard(self.root)
        self.adapter, self.fake = self.config["adapter"], self.config["fake"]

    def capture(self):
        return self.adapter.capture_baseline(self.config["baseline_spec"], self.config["baseline_path"])

    def prepare(self):
        return self.adapter.prepare(self.config["payload_path"], ["requirements.json", self.original], self.config["baseline_path"],
                                    self.config["ownership_path"], "synthetic-reviewed-candidate")

    def proof(self):
        self.capture()
        candidate = self.prepare()
        receipt = self.adapter.execute(candidate["candidate_sha256"], "synthetic-authorized")
        self.assertEqual(receipt["status"], "readback_matched")
        v.coverage(self.root, "requirements.json", candidate["path"], [], "coverage.json")
        spec = {"candidate_path": candidate["path"], "execution_receipt_path":
            f'.omni-native/executions/{candidate["candidate_sha256"]}/receipt.json', "coverage_path": "coverage.json"}
        return candidate, spec

    def test_source_to_current_dashboard_readback_and_recomputed_delivery(self):
        self.configure()
        controls = copy.deepcopy(self.fake.state["controls"])
        _, spec = self.proof()
        result = s.verify_delivery(self.root, spec)
        self.assertEqual(result["surface"], "dashboard")
        self.assertEqual(controls, self.fake.state["controls"])
        self.assertFalse(result["native_verified"])
        self.assertTrue(result["gaps"])
        self.assertEqual(len(s.query_source_keys(v.load(self.root, "requirements.json"))), 6)
        self.assertFalse([g for g in result["gaps"] if g["code"] in {"source_control_not_bound", "source_query_not_bound"}])

    def test_looker_cannot_use_arbitrary_semantic_pin(self):
        self.configure()
        with self.assertRaisesRegex(ValueError, "typed current"):
            self.adapter.prepare(self.config["payload_path"], ["requirements.json"], "semantic.json", self.config["ownership_path"], "review")
        self.assertEqual(self.fake.patch_count, 0)

    def test_missing_control_is_not_hidden_by_query_binding(self):
        self.configure()
        spec = v.load(self.root, self.config["baseline_spec"])
        spec["bindings"][0]["source_asset_keys"] += spec["control_bindings"][0]["source_asset_keys"]
        spec.pop("control_bindings")
        self.write(self.config["baseline_spec"], spec)
        with self.assertRaisesRegex(ValueError, "retained_source_control_unbound"):
            self.capture()

    def test_control_query_scope_order_and_model_drift_prevent_write(self):
        self.configure()
        self.capture()
        candidate = self.prepare()
        originals = copy.deepcopy((self.fake.state, self.fake.models, self.fake.topic))
        for mutate in (lambda: self.fake.state["controls"]["order"].reverse(),
                       lambda: self.fake.state["controls"]["data"]["region"].update(syntheticScope=["1"]),
                       lambda: self.fake.models["workbook-1"].update(baseModelId="model-1"),
                       lambda: self.fake.topic["topic"]["views"][0]["dimensions"][0].update(sql="${TABLE}.other")):
            self.fake.state, self.fake.models, self.fake.topic = copy.deepcopy(originals)
            mutate()
            with self.assertRaises(ValueError):
                self.adapter.execute(candidate["candidate_sha256"], "authorized")
        self.assertEqual(self.fake.patch_count, 0)

    def test_missing_placement_binding_and_deferred_control_remain_gaps(self):
        self.configure()
        req = v.load(self.root, "requirements.json")
        control = next(i for i in req["items"] if i["kind"] == "control")
        control.update(disposition="defer", scope_decision={"reason": "synthetic-defer", "reference": "synthetic-review"})
        self.write("requirements.json", req)
        spec = v.load(self.root, self.config["baseline_spec"])
        spec.pop("control_bindings")
        self.omitted = spec["bindings"][0]["source_asset_keys"].pop()
        self.write(self.config["baseline_spec"], spec)
        _, proof_spec = self.proof()
        proof = s.verify_delivery(self.root, proof_spec)
        self.assertIn({"code": "source_query_not_bound", "asset_key": self.omitted}, proof["gaps"])
        self.assertIn({"code": "deferred_source_asset", "asset_key": control["asset_key"]}, proof["gaps"])

    def test_nonquery_placement_does_not_require_query_mapping(self):
        items = [{"asset_key": "content-placement", "kind": "placement", "disposition": "migrate",
                  "source_identity": {"source_platform": "looker", "query_visual": False}}]
        self.assertEqual(s.query_source_keys({"items": items, "surface": ["dashboard"]}), set())

    def test_reuse_route_still_pins_an_existing_selected_backend(self):
        self.configure()
        project = v.load(self.root, "project.json")
        project["dma_import"] = {"exchange_id": "fixture-exchange"}
        self.write("project.json", project)
        catalog = {"path": "fixture-catalog.json", "sha256": "a" * 64, "bytes": 1}
        # This isolates the route guard; real exchange composition is covered by
        # test_looker_dma_journey and the maintained cowork implementation.
        with patch.object(s.cw, "select", return_value={"status": "candidate_already_selected"}) as selected, \
             patch.object(s.cw, "current_catalog", return_value=(catalog, {})) as current:
            self.capture()
            baseline = v.load(self.root, self.config["baseline_path"])
            self.assertEqual(baseline["selected_backend"]["catalog"], catalog)
            self.assertTrue(selected.called)
            self.assertTrue(current.called)
            current.return_value = ({**catalog, "sha256": "b" * 64}, {})
            with self.assertRaises(ValueError):
                self.prepare()
        self.assertEqual(self.fake.patch_count, 0)


if __name__ == "__main__":
    unittest.main()
