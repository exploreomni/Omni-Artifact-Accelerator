"""Exercise the App and dashboard writers' shared backend lookup against real A/B evidence."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


lane = load("native_model_lane_fixture", "tests/test_semantic_lane.py")
dashboard = load("native_model_dashboard", "skills/omni-bi-engineer/scripts/omni_native.py")
app = load("native_model_app", "skills/omni-app-engineer/scripts/omni_app_native.py")


class NativeModelSelection(unittest.TestCase):
    def setUp(self):
        self.case = lane.SemanticLane()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root = self.case.root
        self.source = {"route": "omni_semantic_reconstruction"}
        self.backend = dashboard._standalone_module()

    def qualified(self, reuse):
        spec, access, queries, tile, cycle = self.case.bind(reuse)
        lane.P.stage_record(self.root, {"stage": "access", "source_scope": "orders", "user_identity": "analyst",
            "evidence": {"data": access["path"], "user_access": spec["observation"]["path"]}})
        cycle.stage("analysis")
        return {"source": "standalone_omni_model", "route": spec["route"], "access": access, "queries": queries}, tile

    def test_writers_bind_the_authored_topic_then_reject_stale_source_evidence(self):
        expected, _ = self.qualified(False)
        for module, workflow in ((self.backend, dashboard.WORKFLOW), (app.s, app.w)):
            self.assertEqual(module.selected_backend(self.root, self.source, workflow), expected)
        self.case.put("evidence/branch-yaml.json", {"files": {}})
        with self.assertRaises(ValueError):
            app.s.selected_backend(self.root, self.source, app.w)

    def test_dashboard_baseline_for_a_previously_reuse_only_source(self):
        expected, tile = self.qualified(False)
        item = {"asset_key": "source-visual", "disposition": "migrate", "kind": "visual"}
        requirements = {**self.source, "source_files": [{}, {"path": "inventory"}], "items": [item]}
        files = {"inventory": {"source": {"platform": "sigma"}}, "payload": {"queryPresentations": {
            "data": {"1": tile}}}, "ownership": {}}
        workflow = Mock()
        workflow.requirements.return_value = "requirements", requirements
        workflow.load.side_effect = lambda root, path: files[path]
        workflow.surface_items.side_effect = dashboard.WORKFLOW.surface_items
        spec = {"schema_version": 1, "kind": "analyst_existing_omni_baseline_spec", "review_ref": "review",
            "requirements_path": "requirements", "payload_path": "payload", "ownership_path": "ownership",
            "bindings": [{"source_asset_keys": ["source-visual"], "query_key": "1", "topic": "orders",
                          "query": tile["query"], "field_ids": ["orders.n"]}]}
        self.assertEqual(self.backend.validate_spec(self.root, spec, workflow), requirements)
        self.assertEqual(self.backend.selected_backend(self.root, requirements, workflow), expected)

    def test_discovery_alone_cannot_select_a_backend_and_warehouse_work_stays_external(self):
        self.case.route("create_topic")
        with self.assertRaisesRegex(ValueError, "complete_current_access_and_analysis_first"):
            self.backend.selected_backend(self.root, self.source, dashboard.WORKFLOW)
        for route in ("unselected", "warehouse_first_refactor"):
            with self.assertRaisesRegex(ValueError, "selected_backend_exchange_required"):
                self.backend.selected_backend(self.root, {"route": route}, dashboard.WORKFLOW)

    def test_existing_qualified_topic_retains_its_local_pins(self):
        expected, _ = self.qualified(True)
        self.assertEqual(app.s.selected_backend(self.root, {"route": "reuse_existing"}, app.w), expected)


if __name__ == "__main__":
    unittest.main()
