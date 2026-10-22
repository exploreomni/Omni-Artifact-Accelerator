"""Hex capture through the actual DMA builder; isolated synthetic data only."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_migration_e2e as e
import test_hex_capture as p

v = e.load("hex_dma_workflow", "skills/omni-artifact-accelerator/scripts/visual_workflow.py")


@unittest.skipUnless(os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"), "requires trusted DMA checkout and dependencies")
class HexDmaJourney(e.MigrationJourney):
    def scope(self, surfaces=("dashboard",)):
        migration = e.load("hex_journey_migration", "skills/omni-backend-handoff/scripts/migration.py")
        units = [{"unit_id": "unit-" + str(index), "inventory_path": self.source_paths[1],
            "asset_keys": [asset["asset_key"]], "disposition": "migrate", "rationale": "Synthetic explicit surface scope",
            "frontend_asset_ids": [asset["asset_key"]], "surfaces": list(surfaces)} for index, asset in enumerate(self.assets)]
        e.write_json(self.root / "contracts/migration-scope-spec.json", {"schema_version": 1,
            "kind": "analyst_migration_scope_spec", "scope_id": "hex-full-scope", "decision_reference": "synthetic-scope",
            "inventory_paths": [self.source_paths[1]], "backend_context_path": None, "units": units})
        migration.freeze(self.root, "contracts/migration-scope-spec.json", "evidence/migration-scope-v1.json")
        return migration, v.load(self.root, "evidence/migration-scope-v1.json"), units

    def source(self):
        request = p.request()
        request.update(route="omni_semantic_reconstruction", route_reference="synthetic-session://semantic-only",
                       target_surface="both")
        native = p.native()
        native["appLayout"]["tabs"] = native["appLayout"]["tabs"][:1]
        # One-domain DMA packet; the full seven-tab denominator has its own tests.
        with patch.object(p, "native", return_value=native):
            captured = p.capture_fixture(self.root / "inputs/hex-capture", supplied_request=request)
        captured["inventory"] = p.module("translate_artifact").translate(Path(captured["output"]).read_bytes(), "hex-capture")
        original = Path(captured["output"])
        inventory_path = self.root / "inputs/hex-inventory.json"
        inventory_path.write_bytes(p.C.encoded(captured["inventory"]))
        self.source_paths = [str(original.relative_to(self.root)), str(inventory_path.relative_to(self.root))]
        for index, path in enumerate(self.source_paths):
            e.ap.register(self.root, "sources", path, "hex-" + str(index))
        self.source_pins = {path: e.sha(self.root / path) for path in self.source_paths}
        self.inventories = [captured["inventory"]]
        self.assets = captured["inventory"]["assets"]
        self.source_gaps = captured["inventory"]["gaps"]
        self.platform, self.route = "hex", "omni_semantic_reconstruction"
        self.assertGreater(len(self.assets), 10)
        v.prepare(self.root, *self.source_paths, "contracts/visual.json", "https://synthetic.example")
        draft = v.load(self.root, "contracts/visual.json")
        draft["route_reference"] = "synthetic-session://semantic-only"
        (self.root / "contracts/visual.json").write_bytes(p.C.encoded(draft))
        _, requirements = v.requirements(self.root, "contracts/visual.json")
        self.assertEqual(requirements["route"], self.route)
        self.assertEqual({item["asset_key"] for item in requirements["items"]}, {a["asset_key"] for a in self.assets})

    def test_capture_real_dma_candidate_retains_source_obligations_and_needs_surface_proof(self):
        self.source()
        migration, scope, units = self.scope()
        request = self.request(migration_scope_path="evidence/migration-scope-v1.json")
        self.assertLessEqual(sum(pin["bytes"] for pin in request["selected_inputs"]), 256 * 1024)
        self.receive(self.response(review=e.RealDmaMigrationE2ETests.real_review(self)))
        selected = self.select()
        self.assert_local_boundary(selected)
        result = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        self.assertIn({"code": "missing_surface_delivery", "surface": "dashboard"}, result["report"]["gaps"])
        checked = migration.verify_return(self.root, "evidence/return-v1.json")
        self.assertEqual(checked["native_verification"], "not_assessed")
        self.assertEqual(checked["business_acceptance"], "not_assessed")
        original = self.root / self.source_paths[0]
        original.write_bytes(original.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")

    def test_scope_cannot_drop_content_or_widen_semantic_route(self):
        self.source()
        migration, _, _ = self.scope()
        spec_path = self.root / "contracts/migration-scope-spec.json"
        spec = json.loads(spec_path.read_text())
        content = next(a["asset_key"] for a in self.assets if a["kind"] == "content")
        spec["units"] = [unit for unit in spec["units"] if content not in unit["asset_keys"]]
        spec_path.write_bytes(p.C.encoded(spec))
        with self.assertRaises(ValueError):
            migration.freeze(self.root, "contracts/migration-scope-spec.json", "evidence/missing-content.json")
        self.request()
        with self.assertRaises(ValueError):
            self.response(review=e.RealDmaMigrationE2ETests.real_review(self), action="warehouse_refactor")

    def target_evidence(self, surface, collision=False):
        """Real target helper; independent synthetic native state uses DMA field IDs.

        This verifies orchestration/freshness, not semantic deployment or parity.
        All appearance/interaction/access cases deliberately remain unobserved.
        """
        import test_hex_app as apps
        import test_looker_native as dashboards
        prefix = ("collision-" if collision else "") + surface
        extra = {"document_id": "sales", "draft_id": "sales-app-draft"} if collision else {}
        config = (apps.configure_initial_app if surface == "app" else dashboards.configure_dashboard)(
            self.root, "contracts/visual.json", prefix="contracts/" + prefix, **extra)
        fake, adapter = config["fake"], config["adapter"]
        def remap(value):
            if isinstance(value, str):
                if value == "orders":
                    return "activity"
                return value.replace("orders.revenue", "events.total").replace("orders.region", "events.tenant_id")
            if isinstance(value, list):
                return [remap(x) for x in value]
            if isinstance(value, dict):
                return {k: remap(x) for k, x in value.items()}
            return value
        for key in ("baseline_spec", "runtime_path", "payload_path", "body_path", "construction_review_path"):
            if key in config:
                path = self.root / config[key]
                e.write_json(path, remap(json.loads(path.read_text())))
        fake.state = remap(fake.state)
        if surface == "app":
            fake.app = remap(fake.app)
        fake.topic = {"success": True, "topic": {"name": "activity", "base_view_name": "events",
            "always_where_filters": {}, "relationships": [], "views": [{"name": "events", "table_name": "EVENTS",
                "dimensions": [{"field_name": "tenant_id", "view_name": "events", "fully_qualified_name": "events.tenant_id",
                    "data_type": "STRING", "sql": '"TENANT_ID"'}],
                "measures": [{"field_name": "total", "view_name": "events", "fully_qualified_name": "events.total",
                    "data_type": "NUMBER", "type": "aggregation", "aggregate_type": "SUM", "sql": '${value}'}]}]}}
        fake.yaml = {"files": {"events.view": 'measures:\n  total:\n    sql: ${value}\n    aggregate_type: sum\n',
            "activity.topic": "base_view: events\n"}, "version": 3, "checksums": {"events.view": "synthetic-checksum"}}
        original_runner = adapter.runner
        def runner(args, **options):
            # The existing fixture checks its original requested topic name;
            # the returned resolved topic and target query use real DMA IDs.
            if len(args) > 4 and args[1:3] == ["models", "get-topic"] and args[4] == "activity":
                args = list(args)
                args[4] = "orders"
            return original_runner(args, **options)
        adapter.runner = runner
        with patch.dict(os.environ, {"OAA_TEST_TOKEN": "test-placeholder-only"}):
            if surface == "app":
                adapter.capture_initial_baseline(config["baseline_spec"], config["baseline_path"])
                candidate = adapter.prepare_initial(config["candidate_spec"])
            else:
                adapter.capture_baseline(config["baseline_spec"], config["baseline_path"])
                candidate = adapter.prepare(config["payload_path"], ["contracts/visual.json", self.source_paths[0]],
                    config["baseline_path"], config["ownership_path"], "synthetic-reviewed-dashboard")
            execute = adapter.execute_initial if surface == "app" else adapter.execute
            receipt = execute(candidate["candidate_sha256"], "synthetic-exact-" + surface)
        self.assertEqual(receipt["status"], "readback_matched")
        coverage = "evidence/" + prefix + "-coverage.json"
        v.coverage(self.root, "contracts/visual.json", candidate["path"], [], coverage)
        store = ".omni-app-native" if surface == "app" else ".omni-native"
        return {"candidate_path": candidate["path"], "execution_receipt_path":
            f'{store}/executions/{candidate["candidate_sha256"]}/receipt.json', "coverage_path": coverage}

    def return_with_surfaces(self, selected, scope, units, deliveries):
        if not hasattr(self, "base_return"):
            self.base_return = self.return_spec(selected, scope, units)
        result = copy.deepcopy(self.base_return)
        result["assets"] = [{**row, "surface": surface,
            "files": {**row["files"], "implementation": [deliveries[surface]["candidate_path"]] if surface in deliveries
                else row["files"]["implementation"]}}
            for row, unit in zip(result["assets"], units) for surface in unit["surfaces"]]
        result["surface_deliveries"] = deliveries
        return result

    def test_real_dma_app_only_with_native_readback_and_current_candidate_binding(self):
        self.source()
        migration, scope, units = self.scope(("app",))
        self.request(migration_scope_path="evidence/migration-scope-v1.json")
        self.receive(self.response(review=e.RealDmaMigrationE2ETests.real_review(self)))
        selected = self.select()
        self.assert_local_boundary(selected)
        proof = self.target_evidence("app")
        result = self.prepare_return(migration, self.return_with_surfaces(selected, scope, units, {"app": proof}))
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        self.assertFalse(any(g["code"] == "missing_surface_delivery" for g in result["report"]["gaps"]))
        receipt = v.load(self.root, "evidence/return-v1.json")
        self.assertEqual(set(receipt["surface_deliveries"]), {"app"})
        baseline = v.load(self.root, receipt["surface_deliveries"]["app"]["baseline"]["path"])
        self.assertTrue(baseline["selected_backend"])
        self.assertEqual(baseline["bindings"][0]["field_ids"], ["events.total"])
        self.assertEqual(migration.verify_return(self.root, "evidence/return-v1.json")["status"], "consistent")
        candidate = self.root / proof["candidate_path"]
        candidate.write_bytes(candidate.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")

    def test_real_dma_both_surfaces_need_distinct_proofs_and_cannot_swap_receipts(self):
        self.source()
        migration, scope, units = self.scope(("dashboard", "app"))
        self.request(migration_scope_path="evidence/migration-scope-v1.json")
        self.receive(self.response(review=e.RealDmaMigrationE2ETests.real_review(self)))
        selected = self.select()
        self.assert_local_boundary(selected)
        app_proof = self.target_evidence("app")
        partial = self.return_with_surfaces(selected, scope, units, {"app": app_proof})
        report = self.prepare_return(migration, partial, "partial")["report"]
        self.assertIn({"code": "missing_surface_delivery", "surface": "dashboard"}, report["gaps"])
        dashboard = self.target_evidence("dashboard")
        result = self.return_with_surfaces(selected, scope, units, {"app": app_proof, "dashboard": dashboard})
        report = self.prepare_return(migration, result)["report"]
        self.assertFalse(any(g["code"] == "missing_surface_delivery" for g in report["gaps"]))
        self.assertEqual(report["candidate_coverage"], "incomplete")  # Required native cases remain unknown.
        self.assertTrue(any(g["code"] == "retained_source_inventory_gaps" for g in report["gaps"]))
        self.assertTrue(any(g["code"] == "declared_unresolved" for g in report["gaps"]))
        checked = migration.verify_return(self.root, "evidence/return-v1.json")
        self.assertFalse(checked["migration_accepted"])
        collision = self.target_evidence("app", collision=True)
        invalid = self.return_with_surfaces(selected, scope, units, {"app": collision, "dashboard": dashboard})
        with self.assertRaisesRegex(ValueError, "separate target documents"):
            self.prepare_return(migration, invalid, "collision")
        result["surface_deliveries"]["app"]["execution_receipt_path"] = dashboard["execution_receipt_path"]
        with self.assertRaises(ValueError):
            self.prepare_return(migration, result, "swapped")

    def test_oversized_result_evidence_needs_explicit_dependency_complete_packet_selection(self):
        self.source()
        _, scope, _ = self.scope()
        request = self.request(migration_scope_path="evidence/migration-scope-v1.json")
        large = "inputs/optional-row-detail.json"
        # Rows retained for analyst QA are not needed to convey this identity/
        # semantic request. The complete capture/definition/inventory/scope stay.
        e.write_json(self.root / large, {"scope_sha256": scope["sha256"], "rows": ["synthetic detail"] * 20000})
        e.ap.register(self.root, "sources", large, "optional-row-detail")
        with self.assertRaisesRegex(ValueError, "256 KiB"):
            e.bridge.create_request(self.root, "contracts/source-roundtrip-spec.json",
                [*self.source_paths, "contracts/metrics.json", large])
        self.assertEqual({i["path"] for i in request["migration_sources"]}, {self.source_paths[1]})
        self.assertEqual(sum(len(u["asset_keys"]) for u in scope["units"]), len(self.assets))
        self.receive(self.response(review=e.RealDmaMigrationE2ETests.real_review(self)))
        self.assertFalse(self.select()["accepted"])


if __name__ == "__main__":
    unittest.main()
