"""Optional real-DMA state/evidence integration; synthetic local files only."""
import importlib.util
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-backend-handoff/scripts/dma_frontend.py"
SPEC = importlib.util.spec_from_file_location("dma_frontend_integration", SCRIPT)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
DMA = os.environ.get("OMNI_ANALYST_DMA_CHECKOUT")


class ContextContractTests(unittest.TestCase):
    def test_self_seal_includes_unicode_and_rejects_mutation(self):
        sealed = adapter.seal({"schema_version": 1, "kind": "analyst_dma_context", "label": "Équipe"})
        adapter.check_seal(sealed, "analyst_dma_context")
        sealed["label"] = "Changed"
        with self.assertRaisesRegex(ValueError, "self-seal"):
            adapter.check_seal(sealed, "analyst_dma_context")

    def test_duplicate_json_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "context.json"
            source.write_text('{"kind":"one","kind":"two"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON"):
                adapter.read_json(source)
            link = root / "alias.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(ValueError, "symlink"):
                adapter.read_json(link)


@unittest.skipUnless(DMA, "set OMNI_ANALYST_DMA_CHECKOUT to a trusted inspected DMA checkout")
class DmaFrontendIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.scripts = Path(DMA).resolve() / "skills/data-model-accelerator/scripts"
        self.gw = adapter.trusted_dma(self.scripts)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "orders.sql").write_text("select 1 as order_id\n")
        self.run = self.root / "dma-run"
        self.catalogue = self.root / "catalogue.json"
        self.catalogue.write_text(json.dumps({"objects": {"orders": {"columns": ["order_id"]}}}))
        self.answers = {"engagement_type": "migration", "priority_domain": "Orders", "framework": "native_sql",
            "warehouse": "snowflake", "semantic_target": "omni", "migration_scope": "full_dashboard",
            "input_handling": "metadata_only", "execution_mode": "assessment_only", "deliverables": ["documentation"],
            "trusted_outputs": ["synthetic report:orders"], "retained_behavior": ["Preserve order count"], "corrected_behavior": []}
        self.gw.start_engagement(self.source, self.run, self.answers, self.catalogue)
        spec = importlib.util.spec_from_file_location("adapter_migration_fixture", SCRIPT.with_name("migration.py"))
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.frontend = self.root / "frontend"
        self.migration.ap.init(self.frontend, "Synthetic adapter frontend", "migration", "dashboard")
        self.context = self.frontend / "inputs/backend-context.json"
        inventory = {"schema_version": 1, "kind": "omni_analyst_source_inventory", "source": {"platform": "synthetic"},
            "assets": [{"asset_key": "report-orders", "kind": "dashboard", "source_id": "orders"}], "gaps": []}
        (self.frontend / "inputs/source-inventory.json").write_text(json.dumps(inventory))
        self.serial = 0
        self.scope_path = None

    def export(self):
        return adapter.export(self.run, self.context, dma_scripts=self.scripts)

    def receipt(self, kind="analyst_migration_scope", **changes):
        self.serial += 1
        destination = self.frontend / ("evidence/receipt-" + str(self.serial) + ".json")
        if kind == "analyst_migration_scope":
            value = {"schema_version": 1, "kind": "analyst_migration_scope_spec", "scope_id": "orders-" + str(self.serial),
                "decision_reference": "synthetic://scope", "inventory_paths": ["inputs/source-inventory.json"],
                "backend_context_path": "inputs/backend-context.json", "units": [{"unit_id": "orders",
                    "inventory_path": "inputs/source-inventory.json", "asset_keys": ["report-orders"], "disposition": "migrate",
                    "rationale": "Synthetic supplied denominator", "frontend_asset_ids": ["orders"], "surfaces": ["dashboard"]}]}
            spec = self.frontend / ("contracts/scope-" + str(self.serial) + ".json")
            spec.write_text(json.dumps(value))
            self.migration.freeze(self.frontend, str(spec.relative_to(self.frontend)), str(destination.relative_to(self.frontend)))
            self.scope_path = destination
        else:
            if self.scope_path is None:
                self.receipt()
            scope = json.loads(self.scope_path.read_text())
            spec = self.frontend / ("contracts/return-" + str(self.serial) + ".json")
            spec.write_text(json.dumps({"schema_version": 1, "kind": "analyst_migration_return_spec",
                "scope_sha256": scope["sha256"], "candidate_review_sha256": None, "assets": [], "lanes": [],
                "unresolved": ["Assessment only: candidate files and native evidence are unavailable"]}))
            self.migration.prepare_return(self.frontend, str(self.scope_path.relative_to(self.frontend)),
                                          str(spec.relative_to(self.frontend)), str(destination.relative_to(self.frontend)))
        value = json.loads(destination.read_text())
        value.pop("sha256")
        value.update(changes)
        value = adapter.seal(value)
        destination.write_text(json.dumps(value))
        return destination

    def record(self, receipt, kind="analyst_frontend_scope"):
        return adapter.record(self.run, receipt, self.context, kind, dma_scripts=self.scripts, frontend_project=self.frontend)

    def test_real_roundtrip_preserves_stages_and_evidence_revisions_do_not_stale(self):
        original = self.gw.load_engagement(self.run)
        self.export()
        self.assertEqual(self.gw.load_engagement(self.run)["revision"], original["revision"])
        scope = self.receipt()
        registered = self.record(scope)
        self.assertEqual(registered["status"], "recorded_unverified")
        unrelated = self.root / "observation.json"
        unrelated.write_text('{"note":"Synthetic observation, no acceptance"}')
        self.gw.record_evidence(self.run, unrelated, "synthetic_observation")
        result = self.receipt("analyst_frontend_return", scope_sha256=json.loads(scope.read_text())["sha256"])
        returned = self.record(result, "analyst_frontend_return")
        state = self.gw.load_engagement(self.run)
        self.assertGreater(state["revision"], original["revision"])
        self.assertEqual(state["workflow"], original["workflow"])
        self.assertEqual(state["evidence"][-1]["assurance"], "recorded_unverified")
        self.assertFalse(returned["migration_accepted"])
        self.assertFalse(state["delivery_assurance"]["acceptance_ready"])

    def test_source_drift_is_detected_by_real_refresh_before_recording(self):
        self.export()
        scope = self.receipt()
        (self.source / "orders.sql").write_text("select 2 as order_id\n")
        with self.assertRaisesRegex(ValueError, "material or selected domain changed"):
            self.record(scope)
        self.assertFalse(any(e["kind"] == "analyst_frontend_scope" for e in self.gw.load_engagement(self.run)["evidence"]))

    def test_changed_scope_and_wrong_engagement_reject(self):
        self.export()
        scope = self.receipt()
        self.gw.update_answers(self.run, {"migration_scope": "model_only"})
        with self.assertRaisesRegex(ValueError, "migration scope changed"):
            self.record(scope)
        other = self.root / "other-run"
        self.gw.start_engagement(self.source, other, self.answers, self.catalogue)
        with self.assertRaisesRegex(ValueError, "another DMA engagement"):
            adapter.record(other, scope, self.context, "analyst_frontend_scope",
                           dma_scripts=self.scripts, frontend_project=self.frontend)

    def test_backend_only_context_cannot_gain_full_dashboard_obligation(self):
        self.gw.update_answers(self.run, {"migration_scope": "model_only"})
        self.export()
        value = adapter.seal({"schema_version": 1, "kind": "analyst_migration_scope", "migration_scope": "model_only",
            "backend_context": {"path": "inputs/backend-context.json", "sha256": adapter.digest(self.context.read_bytes())},
            "authorizes_target_write": False, "origin_authenticated": False, "migration_accepted": False})
        scope = self.frontend / "evidence/forged-scope.json"
        scope.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "preserve DMA migration scope"):
            self.record(scope)

    def test_scope_cannot_be_registered_from_another_frontend_project(self):
        self.export()
        scope = self.receipt()
        other = self.root / "other-frontend"
        self.migration.ap.init(other, "Other synthetic frontend", "migration", "dashboard")
        before = len(self.gw.load_engagement(self.run)["evidence"])
        with self.assertRaisesRegex(ValueError, "another frontend project"):
            adapter.record(self.run, scope, self.context, "analyst_frontend_scope",
                           dma_scripts=self.scripts, frontend_project=other)
        self.assertEqual(len(self.gw.load_engagement(self.run)["evidence"]), before)

    def test_actual_domain_selection_change_invalidates_context(self):
        domains = {"schema_version": 1, "domains": [
            {"id": name, "name": name.title(), "description": "Synthetic " + name,
             "asset_ids": ["report:" + name], "source_paths": ["orders.sql"], "shared_dependency_ids": []}
            for name in ("orders", "service")]}
        state = self.gw.stage_action(self.run, "register-domains", document=domains)
        candidates = state["workflow"]["domain_journey"]["candidates_sha256"]
        self.gw.stage_action(self.run, "select-domain", document={"schema_version": 1, "domain_id": "orders",
            "candidates_sha256": candidates, "request_reference": "synthetic://user/orders"})
        self.export()
        scope = self.receipt()
        self.gw.stage_action(self.run, "pause-domain", document={"schema_version": 1, "domain_id": "orders",
            "request_reference": "synthetic://user/pause"})
        self.gw.stage_action(self.run, "select-domain", document={"schema_version": 1, "domain_id": "service",
            "candidates_sha256": candidates, "request_reference": "synthetic://user/service"})
        with self.assertRaisesRegex(ValueError, "material or selected domain changed"):
            self.record(scope)

    def test_actual_design_import_invalidates_material(self):
        self.export()
        scope = self.receipt()
        design = {"schema_version": 1, "id": "orders", "revision": 1, "entities": [
            {"id": "orders", "name": "orders", "domain": "orders", "layer": "gold", "grain": "One row per order",
             "keys": ["order_id"], "columns": [{"name": "order_id", "type": "integer", "description": "Synthetic key"}],
             "depends_on": [], "asset_ids": ["report:orders"], "security": "Synthetic", "history": "Current",
             "disposition": "create", "reuse": None, "source_paths": ["orders.sql"], "catalogue_pointers": ["/objects/orders"]}],
            "relationships": [], "assets": [{"id": "report:orders", "name": "Orders", "kind": "report", "mapping_status": "verified"}],
            "decisions": [], "existing_models": []}
        self.gw.stage_action(self.run, "import-design", document=design)
        with self.assertRaisesRegex(ValueError, "material or selected domain changed"):
            self.record(scope)

    def test_wrong_context_hash_authority_and_missing_scope_reject(self):
        self.export()
        for change, error in [({"authorizes_target_write": True}, "cannot confer authority"),
                              ({"backend_context": {"path": "inputs/context.json", "sha256": "0" * 64}}, "different backend context")]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, error):
                self.record(self.receipt(**change))
        self.receipt()
        with self.assertRaisesRegex(ValueError, "registered frozen scope"):
            self.record(self.receipt("analyst_frontend_return", scope_sha256="a" * 64), "analyst_frontend_return")

    def test_mutated_scope_and_export_overwrite_reject(self):
        self.export()
        with self.assertRaises(FileExistsError):
            self.export()
        scope = self.receipt()
        self.record(scope)
        scope_hash = json.loads(scope.read_text())["sha256"]
        returned = self.receipt("analyst_frontend_return", scope_sha256=scope_hash)
        scope.write_text(scope.read_text() + " \n")
        with self.assertRaisesRegex(ValueError, "registered frozen scope"):
            self.record(returned, "analyst_frontend_return")

    def test_composed_domo_real_dma_candidate_frontend_return_and_drift(self):
        # Reuse source translator fixtures, while exercising actual OAA helpers
        # and DMA state/builder APIs. No tenant or source pipeline is invoked.
        spec = importlib.util.spec_from_file_location("adapter_composed_journey",
            Path(__file__).with_name("test_migration_e2e.py"))
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        journey = fixtures.MigrationJourney("runTest")
        journey.setUp()
        self.addCleanup(journey.doCleanups)
        journey.source("domo")
        migration, _, units = journey.scope()
        context_path = journey.root / "inputs/backend-context.json"
        adapter.export(self.run, context_path, dma_scripts=self.scripts)
        scope_spec = json.loads((journey.root / "contracts/migration-scope-spec.json").read_text())
        scope_spec["backend_context_path"] = "inputs/backend-context.json"
        (journey.root / "contracts/dma-scope-spec.json").write_text(json.dumps(scope_spec))
        migration.freeze(journey.root, "contracts/dma-scope-spec.json", "evidence/dma-scope.json")
        scope_path = journey.root / "evidence/dma-scope.json"
        scope = json.loads(scope_path.read_text())
        adapter.record(self.run, scope_path, context_path, "analyst_frontend_scope",
                       dma_scripts=self.scripts, frontend_project=journey.root)
        sys.path.insert(0, str(Path(DMA).resolve() / "tests"))
        from test_omni_contract import files, context
        from omni_handoff import build_handoff, write_handoff, REVIEW_PATH
        import omni_contract
        if omni_contract.yaml is None or omni_contract.sqlglot is None:
            raise RuntimeError("Selected Python runtime needs trusted DMA YAML/SQL dependencies")
        state = self.gw.load_engagement(self.run)
        model_context = context()
        model_context["catalogue_sha256"] = state["inputs"]["catalogue"]["sha256"]
        candidate = build_handoff(state, files(), model_context)
        upstream = journey.base / "real-dma-candidate"
        write_handoff(candidate, upstream)
        journey.request()
        journey.receive(journey.response(review=upstream / REVIEW_PATH))
        selected = journey.select()
        journey.assert_local_boundary(selected)
        return_spec = journey.return_spec(selected, scope, units)
        (journey.root / "contracts/dma-return-spec.json").write_text(json.dumps(return_spec))
        migration.prepare_return(journey.root, "evidence/dma-scope.json", "contracts/dma-return-spec.json", "evidence/dma-return.json")
        returned = journey.root / "evidence/dma-return.json"
        result = adapter.record(self.run, returned, context_path, "analyst_frontend_return",
                                dma_scripts=self.scripts, frontend_project=journey.root)
        self.assertEqual(result["status"], "recorded_unverified")
        self.assertFalse(result["migration_accepted"])
        query_path = journey.root / "deliverables/queries-candidate-v1.json"
        original = query_path.read_bytes()
        query_path.write_bytes(original + b" ")
        before = len(self.gw.load_engagement(self.run)["evidence"])
        with self.assertRaisesRegex(ValueError, "changed"):
            adapter.record(self.run, returned, context_path, "analyst_frontend_return",
                           dma_scripts=self.scripts, frontend_project=journey.root)
        self.assertEqual(len(self.gw.load_engagement(self.run)["evidence"]), before)
        query_path.write_bytes(original)
        catalog_path = journey.root / selected["catalog_path"]
        original_catalog = catalog_path.read_bytes()
        catalog_path.write_bytes(original_catalog + b" ")
        with self.assertRaisesRegex(ValueError, "changed"):
            adapter.record(self.run, returned, context_path, "analyst_frontend_return",
                           dma_scripts=self.scripts, frontend_project=journey.root)
        catalog_path.write_bytes(original_catalog)
        # A real, structurally valid candidate from a different DMA context is
        # valid OAA input but cannot satisfy this engagement's frozen obligation.
        other_run = self.root / "other-context-run"
        other_state = self.gw.start_engagement(self.source, other_run,
            {**self.answers, "priority_domain": "Other synthetic context"}, self.catalogue)
        other_candidate = build_handoff(other_state, files(), model_context)
        other_output = journey.base / "other-context-candidate"
        write_handoff(other_candidate, other_output)
        journey.request(request_id="other-context-r2")
        journey.receive(journey.response(review=other_output / REVIEW_PATH, name="other-context-response"))
        changed_selection = journey.select()
        changed_catalog = json.loads((journey.root / changed_selection["catalog_path"]).read_text())
        changed_spec = copy.deepcopy(return_spec)
        changed_spec["candidate_review_sha256"] = changed_catalog["source"]["original_sha256"]
        for row in changed_spec["assets"]:
            row["candidate_review_sha256"] = changed_spec["candidate_review_sha256"]
        (journey.root / "contracts/other-context-return-spec.json").write_text(json.dumps(changed_spec))
        migration.prepare_return(journey.root, "evidence/dma-scope.json", "contracts/other-context-return-spec.json",
                                 "evidence/other-context-return.json")
        self.assertEqual(migration.verify_return(journey.root, "evidence/other-context-return.json")["status"], "consistent")
        before = len(self.gw.load_engagement(self.run)["evidence"])
        with self.assertRaisesRegex(ValueError, "candidate belongs to another DMA context"):
            adapter.record(self.run, journey.root / "evidence/other-context-return.json", context_path,
                           "analyst_frontend_return", dma_scripts=self.scripts, frontend_project=journey.root)
        self.assertEqual(len(self.gw.load_engagement(self.run)["evidence"]), before)


if __name__ == "__main__":
    unittest.main()
