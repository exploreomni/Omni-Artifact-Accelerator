"""Real Tableau producer through frontend scope and real DMA candidate exchange.

Uses only maintained/synthetic local definitions and fixture target contracts.
Does not run a source tenant, warehouse, or native Omni mutation.
"""
import json
import os
from pathlib import Path
import unittest

import test_migration_e2e as e
import test_tableau_visual_bridge as t

v = e.load("tableau_dma_workflow", "skills/omni-artifact-accelerator/scripts/visual_workflow.py")


@unittest.skipUnless(os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"), "requires inspected trusted DMA checkout and dependencies")
class TableauDmaJourney(e.MigrationJourney):
    def source(self):
        captured = t.capture_fixture(self.root / "inputs/tableau-capture", os.environ["OMNI_ANALYST_DMA_CHECKOUT"], rich=True)
        original = Path(captured["output"])
        inventory = self.root / "inputs/tableau-inventory.json"
        inventory.write_bytes(t.b.encoded(captured["inventory"]))
        self.source_paths = [str(original.relative_to(self.root)), str(inventory.relative_to(self.root))]
        for index, path in enumerate(self.source_paths):
            e.ap.register(self.root, "sources", path, "tableau-" + str(index))
        self.source_pins = {path: e.sha(self.root / path) for path in self.source_paths}
        self.inventories = [captured["inventory"]]
        self.assets = captured["inventory"]["assets"]
        self.source_gaps = captured["inventory"]["gaps"]
        self.platform, self.route = "tableau", "omni_semantic_reconstruction"
        self.assertTrue(captured["capture"]["source"]["semantic_inventory"]["worksheets"])
        v.prepare(self.root, *self.source_paths, "contracts/visual.json", "https://synthetic.example")
        requirements = v.load(self.root, "contracts/visual.json")
        requirements.update(route=self.route, route_reference="synthetic-session://semantic-only")
        (self.root / "contracts/visual.json").write_bytes(t.b.encoded(requirements))
        v.requirements(self.root, "contracts/visual.json")
        self.assertEqual({i["asset_key"] for i in requirements["items"]}, {a["asset_key"] for a in self.assets})

    def test_actual_source_scope_dma_response_selection_and_checked_return(self):
        self.source()
        migration, scope, units = self.scope()
        request = self.request(migration_scope_path="evidence/migration-scope-v1.json")
        self.assertLessEqual(sum(p["bytes"] for p in request["selected_inputs"]), 256 * 1024)
        review = e.RealDmaMigrationE2ETests.real_review(self)
        self.receive(self.response(review=review))
        selected = self.select()
        self.assert_local_boundary(selected)
        returned = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(returned["report"]["candidate_coverage"], "complete")
        self.assertTrue(returned["report"]["gaps"])
        checked = migration.verify_return(self.root, "evidence/return-v1.json")
        self.assertEqual(checked["native_verification"], "not_assessed")
        self.assertEqual(checked["business_acceptance"], "not_assessed")
        # A candidate-bound return must not survive changed source evidence.
        original = self.root / self.source_paths[0]
        original.write_bytes(original.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")

    def test_full_scope_cannot_drop_placement_or_widen_semantic_route(self):
        self.source()
        migration, scope, units = self.scope()
        spec_path = self.root / "contracts/migration-scope-spec.json"
        spec = json.loads(spec_path.read_text())
        placement_key = next(a["asset_key"] for a in self.assets if a["kind"] == "placement")
        spec["units"] = [unit for unit in spec["units"] if placement_key not in unit["asset_keys"]]
        spec_path.write_bytes(t.b.encoded(spec))
        with self.assertRaises(ValueError):
            migration.freeze(self.root, "contracts/migration-scope-spec.json", "evidence/omitted.json")
        self.request()
        with self.assertRaises(ValueError):
            self.response(review=e.RealDmaMigrationE2ETests.real_review(self), action="warehouse_refactor")


if __name__ == "__main__":
    unittest.main()
