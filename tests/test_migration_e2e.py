"""Composed offline migration journeys; never claims a live migration or acceptance.

Default cases use synthetic exports and a schema-valid synthetic semantic candidate.
Set OMNI_ANALYST_DMA_CHECKOUT to an inspected, trusted DMA checkout to additionally
exercise its real curated-handoff builder in an isolated subprocess. The selected
Python runtime must already contain DMA's pinned YAML/SQL dependencies. No source
runtime, warehouse, customer code, network, or native Omni tenant is invoked.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DMA = os.environ.get("OMNI_ANALYST_DMA_CHECKOUT")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load("migration_e2e_cowork", "skills/omni-backend-handoff/scripts/cowork.py")
ap = bridge.ap
fixtures = load("migration_e2e_fixtures", "tests/test_migration_sources.py")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MigrationJourney(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "frontend"
        ap.init(self.root, "Synthetic source-to-frontend journey", "migration", "both")

    def source(self, platform, route="warehouse_first_refactor"):
        """Freeze original bytes and actual translator outputs, including unknowns."""
        values = ([('capture', fixtures.domo_bundle()), ('page-plan', fixtures.domo_plan())]
                  if platform == "domo" else [('capture', fixtures.sigma_snapshot())])
        if platform == "sigma" and route != "unselected":
            values.append(('route', fixtures.route(route)))
        inventories, paths = [], []
        for name, value in values:
            raw_path = write_json(self.root / f"inputs/{platform}-{name}-source.json", value)
            raw = raw_path.read_bytes()
            inventory = fixtures.t.translate(raw, platform + "-agent",
                fixtures.DOMO if platform == "domo" else fixtures.SIGMA)
            inventory_path = write_json(self.root / f"inputs/{platform}-{name}-inventory.json", inventory)
            for path, role in ((raw_path, "original"), (inventory_path, "inventory")):
                relative = str(path.relative_to(self.root))
                ap.register(self.root, "sources", relative, f"{platform}-{name}-{role}")
                paths.append(relative)
            self.assertEqual(inventory["source"]["input_sha256"], sha(raw_path))
            self.assertEqual(inventory["upstream_payload"], value)
            self.assertFalse(inventory["migration_context"]["target_write_authority"])
            inventories.append(inventory)
        self.inventories = inventories
        self.source_paths = paths
        self.source_pins = {path: sha(self.root / path) for path in paths}
        self.platform = platform
        self.route = route
        self.assets = [asset for inventory in inventories for asset in inventory["assets"]]
        self.source_gaps = [gap for inventory in inventories for gap in inventory["gaps"]]
        return inventories

    def request(self, route=None, request_id="source-roundtrip", migration_scope_path=None):
        consumers = [{"asset_id": asset["asset_key"], "topic_ids": ["activity"],
                      "field_ids": ["events.total"], "dependency_complete": False}
                     for asset in self.assets if asset["kind"] in ("visual", "query", "worksheet", "placement")]
        self.assertTrue(consumers, "Fixture must contain real projected source consumers")
        spec = {"schema_version": 1, "kind": "analyst_backend_request_spec",
            "request_id": request_id, "route": route or self.route,
            "route_reference": "synthetic-session://route-review", "source_platform": self.platform,
            "requirements": [{"id": "source-population", "question": "Preserve the source population and expose unresolved behavior.",
                "change_class": "binding", "frontend_asset_ids": [row["asset_id"] for row in consumers],
                "metric_ids": ["events.total"], "expected_cases": [
                    {"case_id": "original-identities", "expectation": "Every selected source identity remains traceable."},
                    {"case_id": "unknown-access", "expectation": "Missing source access evidence remains unresolved, never accepted."}]}],
            "consumer_bindings": consumers}
        if migration_scope_path is not None:
            spec["migration_scope_path"] = migration_scope_path
        write_json(self.root / f"contracts/{request_id}-spec.json", spec)
        result = bridge.create_request(self.root, f"contracts/{request_id}-spec.json",
                                       [*self.source_paths, "contracts/metrics.json"])
        self.request_path = Path(result["path"])
        request = json.loads(self.request_path.read_text())
        self.assertEqual(request["dispatch_status"], "not_dispatched")
        self.assertFalse(request["authorizes_target_write"])
        indexed = {item["path"]: item["sha256"] for item in request["selected_inputs"]}
        for path, pin in self.source_pins.items():
            self.assertEqual(indexed[path], pin)
        return request

    def synthetic_review(self):
        """A contract stand-in only; the optional class below uses the real builder."""
        value = {"schema_version": 1, "kind": "omni_semantic_handoff", "version": "omni-handoff-v1",
            "pins": {"source_fingerprint": {"algorithm": "sha256",
                "value": self.source_pins[self.source_paths[0]], "scope": "selected_synthetic_source", "complete": False},
                "context_sha256": "2" * 64, "model_candidate_sha256": "3" * 64,
                "model_context_sha256": "4" * 64, "target": {"warehouse": "snowflake", "framework": "dbt"}},
            "topics": [{"id": "activity", "base_view": "events"}],
            "metrics": [{"id": "events.total", "topic": "activity", "definition_sha256": "5" * 64}],
            "dictionary": [{"id": "events.total", "topic": "activity", "kind": "measure", "definition_sha256": "5" * 64}],
            "dependencies": [], "decisions": [],
            "unknowns": [{"code": "synthetic_candidate_not_source_logic_translation"}],
            "static_status": "synthetic_contract_fixture", "native_status": "pending",
            "business_status": "pending", "deployment_status": "not_authorized"}
        value["handoff_sha256"] = ap.digest(ap.canonical(value))
        return write_json(self.base / "synthetic-review.json", value)

    def response(self, review=None, action="semantic_candidate", name="response"):
        request = json.loads(self.request_path.read_text())
        resolutions = {"schema_version": 1, "kind": "analyst_backend_resolutions",
            "request_sha256": request["sha256"], "backend_action": action,
            "requirements": [{"id": "source-population", "status": "unresolved",
                "explanation": "Synthetic candidate exercises the bridge; source logic, behavior and access require independent verification.",
                "source_gaps": copy.deepcopy(self.source_gaps)}]}
        resolutions_path = write_json(self.base / f"{name}-resolutions.json", resolutions)
        output = self.base / name
        bridge.respond(self.request_path, review or self.synthetic_review(), resolutions_path, output)
        return output

    def receive(self, response):
        return bridge.receive(self.root, str(self.request_path.relative_to(self.root)), response)

    def select(self):
        return bridge.select(self.root, json.loads(self.request_path.read_text())["request_id"])

    def frontend_records(self, selected):
        """Author actual working-contract shapes, never a native or accepted result."""
        request = json.loads(self.request_path.read_text())
        catalog_path = self.root / selected["catalog_path"]
        catalog = json.loads(catalog_path.read_text())
        self.assertTrue(any(row["id"] == "events.total" and row.get("topic") == "activity"
                            for row in catalog["dictionary"]))
        pins = {"request_sha256": request["sha256"], "catalog_path": selected["catalog_path"],
                "catalog_sha256": sha(catalog_path), "source_files": copy.deepcopy(self.source_pins)}
        identities = [{"source_asset_key": a["asset_key"], "source_id": a["source_id"],
                       "source_identity": copy.deepcopy(a["source_identity"]),
                       "source_payload_sha256": a["source_payload_sha256"]} for a in self.assets]
        query_items = [{**identity, "topic_id": "activity", "field_ids": ["events.total"],
                        "binding_status": "proposed_unverified", "workbook_id": None, "tab_id": None}
                       for identity, asset in zip(identities, self.assets) if asset["kind"] in ("visual", "query", "worksheet", "placement")]
        design_items = [{**identity, "surface": "dashboard", "status": "proposed",
                         "source_facets": copy.deepcopy(asset["facets"]), "accepted_difference": None}
                        for identity, asset in zip(identities, self.assets)]
        qa_items = [{"id": "source-gap-" + str(i), "status": "not_run", "source_gap": gap,
                     "evidence_category": "unresolved_source_behavior", "observed_result": None}
                    for i, gap in enumerate(self.source_gaps)]
        self.assertTrue(qa_items, "Test must retain actual translator uncertainty")
        for name, items in (("queries", query_items), ("design", design_items), ("qa", qa_items)):
            value = {"schema_version": 1, "kind": "analyst_" + name, "status": "proposed",
                     "items": items, "open_questions": ["Native behavior and business acceptance are untested"],
                     "evidence_pins": copy.deepcopy(pins)}
            write_json(self.root / f"contracts/{name}.json", value)
            # Immutable review snapshots preserve history while working contracts may evolve.
            path = f"deliverables/{name}-candidate-v1.json"
            write_json(self.root / path, value)
            ap.register(self.root, "artifacts", path, name + "-candidate-v1")
        return identities

    def assert_local_boundary(self, selected):
        self.assertFalse(selected["accepted"])
        self.assertFalse(selected["authorizes_target_write"])
        self.assertEqual(selected["requirement_resolutions"][0]["status"], "unresolved")
        identities = self.frontend_records(selected)
        for path, pin in self.source_pins.items():
            self.assertEqual(sha(self.root / path), pin, "The composed flow changed source bytes")
        qa = json.loads((self.root / "deliverables/qa-candidate-v1.json").read_text())
        self.assertEqual([row["source_gap"] for row in qa["items"]], self.source_gaps)
        checked = ap.project_check(self.root)
        self.assertEqual(checked["status"], "consistent", checked)
        self.assertEqual(checked["check_scope"], "structure_and_recorded_hashes_only")
        self.assertEqual(checked["readiness"], "not_assessed")
        self.assertEqual(checked["native_verification"], "not_assessed")
        self.assertEqual(checked["business_acceptance"], "not_assessed")
        self.assertFalse(checked["publication_authorized"])
        packet = ap.packet(self.root, "qa-analyst", [selected["catalog_path"],
            "deliverables/queries-candidate-v1.json", "deliverables/design-candidate-v1.json",
            "deliverables/qa-candidate-v1.json"], self.root / "tasks/independent-qa.json")
        self.assertEqual(packet["current_dma_catalog"], selected["catalog_path"])
        self.assertEqual(packet["dispatch_status"], "not_dispatched")
        return identities

    def scope(self):
        migration = load("migration_e2e_scope", "skills/omni-backend-handoff/scripts/migration.py")
        inventory_paths = [p for p in self.source_paths if p.endswith("-inventory.json")]
        units = []
        for path, inventory in zip(inventory_paths, self.inventories):
            for asset in inventory["assets"]:
                units.append({"unit_id": "unit-" + str(len(units)), "inventory_path": path,
                    "asset_keys": [asset["asset_key"]], "disposition": "migrate",
                    "rationale": "Synthetic explicit source-coverage selection; unresolved facets remain open.",
                    "frontend_asset_ids": [asset["asset_key"]], "surfaces": ["dashboard"]})
        scope_spec = {"schema_version": 1, "kind": "analyst_migration_scope_spec",
            "scope_id": "synthetic-full-scope", "decision_reference": "synthetic-session://coverage-review",
            "inventory_paths": inventory_paths, "backend_context_path": None, "units": units}
        write_json(self.root / "contracts/migration-scope-spec.json", scope_spec)
        migration.freeze(self.root, "contracts/migration-scope-spec.json", "evidence/migration-scope-v1.json")
        return migration, json.loads((self.root / "evidence/migration-scope-v1.json").read_text()), units

    def return_spec(self, selected, scope, units):
        catalog = json.loads((self.root / selected["catalog_path"]).read_text())
        candidate_sha = catalog["source"]["original_sha256"]
        implementation_path = "deliverables/dashboard-candidate-v1.json"
        write_json(self.root / implementation_path, {"kind": "synthetic_dashboard_candidate",
            "status": "proposed", "native_validation": "not_run", "source_asset_keys": [a["asset_key"] for a in self.assets],
            "query_contract": "deliverables/queries-candidate-v1.json", "unresolved": ["Native schema/runtime not verified"]})
        ap.register(self.root, "artifacts", implementation_path, "dashboard-candidate-v1")
        return {"schema_version": 1, "kind": "analyst_migration_return_spec", "scope_sha256": scope["sha256"],
            "candidate_review_sha256": candidate_sha,
            "assets": [{"asset_id": unit["frontend_asset_ids"][0], "surface": "dashboard",
                "unit_ids": [unit["unit_id"]], "candidate_review_sha256": candidate_sha,
                "files": {"query": ["deliverables/queries-candidate-v1.json"],
                    "design": ["deliverables/design-candidate-v1.json"], "implementation": [implementation_path],
                    "qa": ["deliverables/qa-candidate-v1.json"]}} for unit in units],
            "lanes": [{"lane": lane, "status": "not_run", "evidence_paths": [],
                "rationale": "Offline synthetic candidate only; no participant or native execution evidence."}
                for lane in [*bridge.LANES, "native", "operations", "business"]],
            "unresolved": ["Source behavior and security gaps remain open", "All candidate bindings need native qualification"]}

    def prepare_return(self, migration, spec, name="return-v1"):
        write_json(self.root / f"contracts/{name}-spec.json", spec)
        return migration.prepare_return(self.root, "evidence/migration-scope-v1.json",
                                        f"contracts/{name}-spec.json", f"evidence/{name}.json")


class MigrationE2ETests(MigrationJourney):
    def test_domo_export_roundtrip_retains_native_ids_page_denominator_and_unknowns(self):
        inventories = self.source("domo")
        self.request()
        received = self.receive(self.response())
        self.assertEqual(received["impact"]["coverage"], "declared_consumers_only")
        self.assertTrue(all(row["disposition"] == "recheck_required"
                            for row in received["impact"]["consumer_impact"]))
        identities = self.assert_local_boundary(self.select())
        self.assertIn("urn:domo:card:c1", {row["source_id"] for row in identities})
        self.assertIn("p1", {row["source_id"] for row in identities})
        self.assertIn("graph-card-1", {row["source_identity"].get("object_id") for row in identities})
        plan = inventories[1]["migration_context"]["source_denominator"]
        self.assertEqual(plan, fixtures.domo_plan()["source"])
        self.assertEqual(plan["placements"][0]["placement_id"], "place-1")
        self.assertIn("b-security", plan["queries"][0]["behavior_denominator"]["security_ids"])
        self.assertEqual(inventories[0]["manual_capture_queue"][0]["request_id"], "capture-1")
        self.assertIn("domo.special_behavior_unresolved", {gap["code"] for gap in self.source_gaps})

    def test_sigma_direct_route_preserves_behavior_and_refuses_warehouse_response(self):
        inventories = self.source("sigma", "omni_semantic_reconstruction")
        self.request()
        with self.assertRaisesRegex(ValueError, "violates selected route"):
            self.response(action="warehouse_and_semantic_candidate", name="wrong-action")
        self.receive(self.response())
        identities = self.assert_local_boundary(self.select())
        self.assertTrue({"model-1", "table-1", "workbook-1", "page-1", "chart-1", "chart-2", "control-1"}
                        <= {row["source_id"] for row in identities})
        self.assertEqual(inventories[0]["migration_context"]["source_context"]["controls"]["control-1"]["target_element_ids"], ["chart-1"])
        model = next(a for a in inventories[0]["assets"] if a["source_id"] == "table-1")
        self.assertEqual(model["source_payload"]["metrics"][0]["formula"], "Sum([amount])")
        self.assertFalse(inventories[1]["migration_context"]["dbt_planning_applicable"])

    def test_sigma_warehouse_route_allows_only_candidate_not_readiness(self):
        inventories = self.source("sigma", "warehouse_first_refactor")
        self.request()
        self.receive(self.response(action="warehouse_and_semantic_candidate"))
        self.assert_local_boundary(self.select())
        self.assertTrue(inventories[1]["migration_context"]["dbt_planning_applicable"])
        self.assertFalse(inventories[1]["migration_context"]["upstream_write_permitted"])

    def test_sigma_missing_route_cannot_promote_an_unbound_candidate(self):
        self.source("sigma", "unselected")
        self.request()
        with self.assertRaisesRegex(ValueError, "violates selected route"):
            self.response(action="semantic_candidate")
        with self.assertRaisesRegex(ValueError, "without a baseline"):
            self.response(action="clarification")

    def test_sigma_route_inventory_cannot_be_overridden_by_request_label(self):
        self.source("sigma", "omni_semantic_reconstruction")
        with self.assertRaisesRegex(ValueError, "route"):
            self.request(route="warehouse_first_refactor")

    def test_registered_route_cannot_be_hidden_by_omitting_selected_input(self):
        self.source("sigma", "omni_semantic_reconstruction")
        valid = self.request()
        for field, value, expected in (("route", "warehouse_first_refactor", "route"),
                                       ("source_platform", "domo", "platform")):
            spec = copy.deepcopy(valid["spec"])
            spec["request_id"] = "conflicting-" + field
            spec[field] = value
            path = f"contracts/{spec['request_id']}.json"
            write_json(self.root / path, spec)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, expected):
                bridge.create_request(self.root, path, ["contracts/metrics.json"])

    def test_migration_scope_link_pins_inventories_and_bounds_requested_consumers(self):
        self.source("domo")
        self.scope()
        valid = self.request(migration_scope_path="evidence/migration-scope-v1.json")
        spec = copy.deepcopy(valid["spec"])
        spec["request_id"] = "auto-scoped-inputs"
        write_json(self.root / "contracts/auto-scoped.json", spec)
        result = bridge.create_request(self.root, "contracts/auto-scoped.json", ["contracts/metrics.json"])
        request = json.loads(Path(result["path"]).read_text())
        pinned = {row["path"] for row in request["selected_inputs"]}
        self.assertIn("evidence/migration-scope-v1.json", pinned)
        self.assertTrue({p for p in self.source_paths if p.endswith("-inventory.json")} <= pinned)
        outside = copy.deepcopy(spec)
        outside["request_id"] = "outside-source-scope"
        outside["requirements"][0]["frontend_asset_ids"].append("not-a-selected-source-consumer")
        write_json(self.root / "contracts/outside-scope.json", outside)
        with self.assertRaisesRegex(ValueError, "outside migration scope"):
            bridge.create_request(self.root, "contracts/outside-scope.json", ["contracts/metrics.json"])

    def test_resealed_embedded_request_cannot_disagree_with_pinned_spec(self):
        self.source("sigma", "omni_semantic_reconstruction")
        request = self.request()
        request["spec"]["route"] = "warehouse_first_refactor"
        request.pop("sha256")
        write_json(self.request_path, bridge.sealed(request))
        response = self.response()
        with self.assertRaisesRegex(ValueError, "embedded request spec"):
            self.receive(response)

    def test_original_source_and_inventory_drift_block_receipt_and_selection(self):
        self.source("domo")
        self.request()
        response = self.response()
        source = self.root / self.source_paths[0]
        original = source.read_bytes()
        source.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.receive(response)
        source.write_bytes(original)
        self.receive(response)
        inventory = self.root / self.source_paths[1]
        inventory.write_bytes(inventory.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.select()
        self.assertEqual(ap.project_check(self.root)["status"], "inconsistent")

    def test_idempotent_selection_rechecks_frozen_source_inputs(self):
        self.source("sigma", "omni_semantic_reconstruction")
        self.request()
        self.receive(self.response())
        self.select()
        source = self.root / self.source_paths[0]
        source.write_bytes(source.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.select()

    def test_candidate_and_frontend_artifact_drift_remain_visible(self):
        self.source("sigma", "omni_semantic_reconstruction")
        self.request()
        response = self.response()
        candidate = response / "semantic-review.json"
        original = candidate.read_bytes()
        candidate.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "candidate bytes changed"):
            self.receive(response)
        candidate.write_bytes(original)
        self.receive(response)
        self.assert_local_boundary(self.select())
        design = self.root / "deliverables/design-candidate-v1.json"
        changed = json.loads(design.read_text())
        changed["items"] = []
        write_json(design, changed)
        self.assertEqual(ap.project_check(self.root)["status"], "inconsistent")
        with self.assertRaisesRegex(ValueError, "changed since registration"):
            ap.packet(self.root, "qa-analyst", [str(design.relative_to(self.root))], self.root / "tasks/stale-qa.json")

    def test_backend_revision_preserves_frontend_history_and_requires_recheck(self):
        self.source("domo")
        self.request(request_id="baseline-r1")
        self.receive(self.response())
        first = self.select()
        self.assert_local_boundary(first)
        snapshots = {path: path.read_bytes() for path in (self.root / "deliverables").glob("*-candidate-v1.json")}
        candidate = json.loads((self.root / "exchanges/baseline-r1/semantic-review.json").read_text())
        candidate["pins"]["model_candidate_sha256"] = "a" * 64
        candidate["dictionary"][0]["definition_sha256"] = "b" * 64
        candidate["metrics"][0]["definition_sha256"] = "b" * 64
        candidate.pop("handoff_sha256")
        candidate["handoff_sha256"] = ap.digest(ap.canonical(candidate))
        changed = write_json(self.base / "changed-review.json", candidate)
        self.request(request_id="semantic-change-r2")
        received = self.receive(self.response(review=changed, name="changed-response"))
        second = self.select()
        self.assertNotEqual(first["catalog_path"], second["catalog_path"])
        self.assertTrue(all(row["disposition"] == "recheck_required"
                            for row in received["impact"]["consumer_impact"]))
        for path, content in snapshots.items():
            self.assertEqual(path.read_bytes(), content, "Prior frontend evidence was overwritten")
            self.assertEqual(json.loads(content)["evidence_pins"]["catalog_path"], first["catalog_path"])
        # Structural consistency is deliberately weaker than full-scope completion.
        checked = ap.project_check(self.root)
        self.assertEqual(checked["status"], "consistent")
        self.assertEqual(checked["readiness"], "not_assessed")

    def test_domo_scope_return_reconciles_artifacts_without_acceptance(self):
        self.source("domo")
        migration, scope, units = self.scope()
        self.request()
        self.receive(self.response())
        selected = self.select()
        self.assert_local_boundary(selected)
        spec = self.return_spec(selected, scope, units)
        result = self.prepare_return(migration, spec)
        self.assertEqual(result["report"]["candidate_coverage"], "complete", result)
        self.assertEqual(result["report"]["acceptance"], "not_assessed")
        self.assertTrue(result["report"]["gaps"], "Source gaps must remain visible after all files exist")
        verified = migration.verify_return(self.root, "evidence/return-v1.json")
        self.assertEqual(verified["status"], "consistent")
        self.assertEqual(verified["native_verification"], "not_assessed")
        self.assertEqual(verified["business_acceptance"], "not_assessed")
        changed = self.root / self.source_paths[1]
        changed.write_bytes(changed.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")

    def test_scope_cannot_silently_omit_or_double_count_exported_assets(self):
        self.source("domo")
        migration, _, _ = self.scope()
        original = json.loads((self.root / "contracts/migration-scope-spec.json").read_text())
        for mutation in ("missing", "duplicate"):
            changed = copy.deepcopy(original)
            if mutation == "missing":
                changed["units"].pop()
            else:
                duplicated = copy.deepcopy(changed["units"][0])
                duplicated["unit_id"] = "duplicate-asset-unit"
                changed["units"].append(duplicated)
            path = f"contracts/{mutation}-scope-spec.json"
            write_json(self.root / path, changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                migration.freeze(self.root, path, f"evidence/{mutation}-scope.json")

    def test_resealed_scope_cannot_drop_units_from_unchanged_pinned_spec(self):
        self.source("domo")
        migration, scope, _ = self.scope()
        original_spec = (self.root / "contracts/migration-scope-spec.json").read_bytes()
        scope["units"] = []
        scope.pop("sha256")
        write_json(self.root / "evidence/migration-scope-v1.json", bridge.sealed(scope))
        root, project = ap.load_project(self.root)
        with self.assertRaises(ValueError):
            migration.load_scope(root, project, "evidence/migration-scope-v1.json")
        self.assertEqual((self.root / "contracts/migration-scope-spec.json").read_bytes(), original_spec)

    def test_return_reports_missing_coverage_and_refuses_mismatched_candidate_pins(self):
        self.source("sigma", "omni_semantic_reconstruction")
        migration, scope, units = self.scope()
        self.request()
        self.receive(self.response())
        selected = self.select()
        self.assert_local_boundary(selected)
        spec = self.return_spec(selected, scope, units)
        incomplete = copy.deepcopy(spec)
        incomplete["assets"].pop()
        incomplete["assets"][0]["files"]["qa"] = []
        incomplete["lanes"] = [row for row in incomplete["lanes"] if row["lane"] != "access"]
        result = self.prepare_return(migration, incomplete, "partial-return")
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        self.assertIn("access", result["report"]["missing_lanes"])
        for where in ("top", "asset"):
            changed = copy.deepcopy(spec)
            if where == "top":
                changed["candidate_review_sha256"] = "0" * 64
            else:
                changed["assets"][0]["candidate_review_sha256"] = "0" * 64
            with self.subTest(where=where), self.assertRaises(ValueError):
                self.prepare_return(migration, changed, "mismatched-" + where)

    def test_return_receipt_becomes_stale_after_new_backend_selection(self):
        self.source("sigma", "omni_semantic_reconstruction")
        migration, scope, units = self.scope()
        self.request(request_id="first-r1")
        self.receive(self.response())
        first = self.select()
        self.assert_local_boundary(first)
        spec = self.return_spec(first, scope, units)
        self.prepare_return(migration, spec)
        candidate = json.loads((self.root / "exchanges/first-r1/semantic-review.json").read_text())
        candidate["pins"]["model_candidate_sha256"] = "a" * 64
        candidate.pop("handoff_sha256")
        candidate["handoff_sha256"] = ap.digest(ap.canonical(candidate))
        review = write_json(self.base / "changed-review.json", candidate)
        self.request(request_id="second-r2")
        self.receive(self.response(review=review, name="changed-response"))
        self.select()
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")
        with self.assertRaises(ValueError):
            self.prepare_return(migration, spec, "stale-resubmission")

    def test_resealed_receipt_cannot_upgrade_incomplete_pinned_return(self):
        self.source("domo")
        migration, scope, units = self.scope()
        self.request()
        self.receive(self.response())
        selected = self.select()
        self.assert_local_boundary(selected)
        spec = self.return_spec(selected, scope, units)
        spec["assets"] = []
        result = self.prepare_return(migration, spec)
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        receipt_path = self.root / "evidence/return-v1.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["candidate_coverage"] = "complete"
        receipt.pop("sha256")
        write_json(receipt_path, bridge.sealed(receipt))
        with self.assertRaises(ValueError):
            migration.verify_return(self.root, "evidence/return-v1.json")


@unittest.skipUnless(DMA, "set OMNI_ANALYST_DMA_CHECKOUT to an inspected trusted DMA checkout")
class RealDmaMigrationE2ETests(MigrationJourney):
    def real_review(self):
        """Run trusted producer code out-of-process; never execute imported exports."""
        output = self.base / "real-dma-handoff"
        script = r'''
import json, sys
from pathlib import Path
dma, output, source_hash = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), sys.argv[3]
sys.path[:0] = [str(dma / "tests"), str(dma / "skills/data-model-accelerator/scripts")]
from test_omni_contract import files, context
from omni_handoff import build_handoff, write_handoff, REVIEW_PATH
import omni_contract
if omni_contract.yaml is None or omni_contract.sqlglot is None:
    raise RuntimeError("Selected runtime needs trusted DMA YAML/SQL dependencies")
ctx = context()
state = {"schema_version": 1, "engagement_id": "synthetic-migration-e2e", "revision": 1,
    "status": "discovery", "answers": {"framework": "dbt", "warehouse": "snowflake", "semantic_target": "omni"},
    "inputs": {"source": {"fingerprint": {"algorithm": "sha256", "value": source_hash,
        "scope": "selected_synthetic_source", "complete": False}}, "catalogue": {"sha256": ctx["catalogue_sha256"]}},
    "readiness": {"platform": {}}, "next_actions": ["Review source behavior and target bindings"]}
result = build_handoff(state, files(), ctx)
assert result["summary"]["native_verified"] is False
assert result["summary"]["acceptance_ready"] is False
write_handoff(result, output)
print(json.dumps({"review": str(output / REVIEW_PATH), "static_status": result["summary"]["static_status"]}))
'''
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-c", script, str(Path(DMA).resolve()),
            str(output), self.source_pins[self.source_paths[0]]], capture_output=True, text=True,
            env=environment, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        report = json.loads(result.stdout)
        self.assertEqual(report["static_status"], "passed")
        review = Path(report["review"])
        value = json.loads(review.read_text())
        self.assertEqual(value["pins"]["source_fingerprint"]["value"], self.source_pins[self.source_paths[0]])
        self.assertFalse(value["pins"]["source_fingerprint"]["complete"])
        return review

    def test_domo_through_real_dma_builder_and_frontend_records(self):
        self.source("domo")
        migration, scope, units = self.scope()
        self.request()
        review = self.real_review()
        original = review.read_bytes()
        self.receive(self.response(review=review))
        selected = self.select()
        self.assert_local_boundary(selected)
        returned = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(returned["report"]["candidate_coverage"], "complete")
        self.assertEqual(migration.verify_return(self.root, "evidence/return-v1.json")["business_acceptance"], "not_assessed")
        self.assertEqual(review.read_bytes(), original)

    def test_sigma_direct_through_real_dma_builder_and_frontend_records(self):
        self.source("sigma", "omni_semantic_reconstruction")
        migration, scope, units = self.scope()
        self.request()
        self.receive(self.response(review=self.real_review()))
        selected = self.select()
        self.assert_local_boundary(selected)
        returned = self.prepare_return(migration, self.return_spec(selected, scope, units))
        self.assertEqual(returned["report"]["candidate_coverage"], "complete")
        self.assertEqual(migration.verify_return(self.root, "evidence/return-v1.json")["native_verification"], "not_assessed")


if __name__ == "__main__":
    unittest.main()
