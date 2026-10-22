"""Optional compatibility test using the real, explicitly selected DMA builder."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

DMA = os.environ.get("OMNI_ANALYST_DMA_CHECKOUT")


@unittest.skipUnless(DMA, "set OMNI_ANALYST_DMA_CHECKOUT to a trusted inspected DMA checkout")
class DmaIntegrationTests(unittest.TestCase):
    def test_real_curated_handoff_import(self):
        # This opt-in loads trusted local DMA modules, never customer input code.
        dma = Path(DMA).resolve()
        sys.path[:0] = [str(dma / "tests"), str(dma / "skills/data-model-accelerator/scripts")]
        from test_omni_contract import files, context
        from test_delivery_portal import fixture
        from omni_handoff import build_handoff, write_handoff, REVIEW_PATH
        import omni_contract
        if omni_contract.yaml is None or omni_contract.sqlglot is None:
            raise RuntimeError("Selected Python runtime needs the trusted DMA checkout's YAML/SQL dependencies")
        script = Path(__file__).resolve().parents[1] / "skills/omni-artifact-accelerator/scripts/analyst_project.py"
        spec = importlib.util.spec_from_file_location("analyst_bridge_integration", script)
        project = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(project)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            state, _ = fixture(root)
            ctx = context()
            state["inputs"]["catalogue"]["sha256"] = ctx["catalogue_sha256"]
            result = build_handoff(state, files(), ctx)
            upstream = root / "dma-handoff"
            write_handoff(result, upstream)
            run = root / "analyst"
            project.init(run, "Synthetic DMA compatibility test", "migration", "both")
            imported = project.import_dma(run, upstream / REVIEW_PATH)
            self.assertEqual(imported["status"], "imported_candidate")
            self.assertFalse(imported["native_verified"])
            self.assertEqual(project.project_check(run)["status"], "consistent")
            script = Path(__file__).resolve().parents[1] / "skills/omni-backend-handoff/scripts/cowork.py"
            spec = importlib.util.spec_from_file_location("cowork_real_dma", script)
            bridge = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bridge)
            request_spec = {
                "schema_version": 1, "kind": "analyst_backend_request_spec", "request_id": "real-builder-clarification",
                "route": "reuse_existing", "route_reference": "synthetic-integration-choice", "source_platform": "fixture",
                "requirements": [{"id": "metric-context", "question": "Confirm the metric context without changing definitions.",
                    "change_class": "clarification", "frontend_asset_ids": ["test-dashboard"], "metric_ids": [],
                    "expected_cases": [{"case_id": "reuse", "expectation": "Definitions remain identical."}]}],
                "consumer_bindings": []}
            (run / "contracts/request.json").write_text(json.dumps(request_spec))
            request = bridge.create_request(run, "contracts/request.json", ["contracts/metrics.json"])
            resolutions = {"schema_version": 1, "kind": "analyst_backend_resolutions", "request_sha256": request["sha256"],
                "backend_action": "clarification", "requirements": [{"id": "metric-context", "status": "unresolved",
                "explanation": "Synthetic compatibility only; customer interpretation requires independent evidence."}]}
            (root / "resolutions.json").write_text(json.dumps(resolutions))
            response = root / "response"
            bridge.respond(request["path"], upstream / REVIEW_PATH, root / "resolutions.json", response)
            bridge.receive(run, "requests/real-builder-clarification.json", response)
            selected = bridge.select(run, "real-builder-clarification")
            self.assertFalse(selected["accepted"])
            self.assertEqual(project.project_check(run)["status"], "consistent")


if __name__ == "__main__":
    unittest.main()
