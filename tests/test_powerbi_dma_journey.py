"""Power BI capture through real DMA handoff, using isolated synthetic data only."""
import json
import os
from pathlib import Path
import unittest

import test_migration_e2e as e
import test_powerbi_visual_bridge as p

v = e.load("powerbi_dma_workflow", "skills/omni-artifact-accelerator/scripts/visual_workflow.py")


@unittest.skipUnless(os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"), "requires trusted DMA checkout and dependencies")
class PowerBIDmaJourney(e.MigrationJourney):
    def source(self):
        request = p.request()
        request.update(route="omni_semantic_reconstruction", route_reference="synthetic-session://semantic-only")
        captured = p.capture_fixture(self.root / "inputs/powerbi-capture", supplied_request=request)
        original = Path(captured["output"])
        inventory_path = self.root / "inputs/powerbi-inventory.json"
        inventory_path.write_bytes(p.b.encoded(captured["inventory"]))
        self.source_paths = [str(original.relative_to(self.root)), str(inventory_path.relative_to(self.root))]
        for index, path in enumerate(self.source_paths):
            e.ap.register(self.root, "sources", path, "powerbi-" + str(index))
        self.source_pins = {path: e.sha(self.root / path) for path in self.source_paths}
        self.inventories = [captured["inventory"]]
        self.assets = captured["inventory"]["assets"]
        self.source_gaps = captured["inventory"]["gaps"]
        self.platform, self.route = "powerbi", "omni_semantic_reconstruction"
        self.assertEqual({(a["source_path"], a["kind"]) for a in self.assets}, set(p.EXPECTED))
        self.assertTrue(any(a["source_id"] == "Slicer" for a in self.assets))
        v.prepare(self.root, *self.source_paths, "contracts/visual.json", "https://synthetic.example")
        draft = v.load(self.root, "contracts/visual.json")
        draft["route_reference"] = "synthetic-session://semantic-only"
        (self.root / "contracts/visual.json").write_bytes(p.b.encoded(draft))
        _, requirements = v.requirements(self.root, "contracts/visual.json")
        self.assertEqual(requirements["route"], self.route)
        self.assertEqual({item["asset_key"] for item in requirements["items"]}, {a["asset_key"] for a in self.assets})

    def test_source_freeze_real_candidate_and_return_preserve_all_objects_and_gaps(self):
        self.source()
        migration, scope, units = self.scope()
        request = self.request(migration_scope_path="evidence/migration-scope-v1.json")
        self.assertLessEqual(sum(pin["bytes"] for pin in request["selected_inputs"]), 256 * 1024)
        self.receive(self.response(review=e.RealDmaMigrationE2ETests.real_review(self)))
        selected = self.select()
        self.assert_local_boundary(selected)
        result = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(result["report"]["candidate_coverage"], "complete")
        self.assertTrue(result["report"]["gaps"])
        checked = migration.verify_return(self.root, "evidence/return-v1.json")
        self.assertEqual(checked["native_verification"], "not_assessed")
        self.assertEqual(checked["business_acceptance"], "not_assessed")
        # Source evidence changing after candidate selection invalidates the return.
        original = self.root / self.source_paths[0]
        original.write_bytes(original.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")

    def test_scope_cannot_drop_control_or_widen_semantic_route(self):
        self.source()
        migration, _, _ = self.scope()
        spec_path = self.root / "contracts/migration-scope-spec.json"
        spec = json.loads(spec_path.read_text())
        control = next(a["asset_key"] for a in self.assets if a["kind"] == "control")
        spec["units"] = [unit for unit in spec["units"] if control not in unit["asset_keys"]]
        spec_path.write_bytes(p.b.encoded(spec))
        with self.assertRaises(ValueError):
            migration.freeze(self.root, "contracts/migration-scope-spec.json", "evidence/missing-control.json")
        self.request()
        with self.assertRaises(ValueError):
            self.response(review=e.RealDmaMigrationE2ETests.real_review(self), action="warehouse_refactor")


if __name__ == "__main__":
    unittest.main()
