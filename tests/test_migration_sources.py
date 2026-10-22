"""Synthetic Domo/Sigma contract bridges; never invokes either migration runtime."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-artifact-translator/scripts/translate_artifact.py"
spec = importlib.util.spec_from_file_location("analyst_translation_sources", SCRIPT)
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
DOMO = "55eba0ca0690fbf14f39eddbc8a04c94a720c155"
SIGMA = "f4eda45b0f49dc7335496d028665f7339ed82e8f"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def parse(value, platform):
    return t.translate(json.dumps(value).encode(), platform + "-agent", DOMO if platform == "domo" else SIGMA)


def seal(value, field, prefixed=False):
    value[field] = ("sha256:" if prefixed else "") + sha({k: v for k, v in value.items() if k != field})
    return value


def domo_bundle():
    common = {"tenant_ref": "tenant-ref://domo/fictional", "environment": "unknown",
        "visibility_principal_ref": "principal-ref://fictional/reader", "permission_context_ref": None,
        "acquired_at": "2026-10-21T10:00:00-05:00", "extraction_method": "manual_capture",
        "definition_state": "definition_partial", "channels": ["manual_capture"], "source_refs": ["evidence-ref://fictional/capture"],
        "content_hash": None, "sensitivity": "confidential", "redaction_state": "redacted", "provenance": {}}
    return seal({"contract_version": "omnikit.domo.evidence.v1", "mode": "manual",
        "objects": [{**common, "object_type": "card", "object_id": "urn:domo:card:c1", "title": "Revenue",
            "attributes": {"definition": {"formula": "SUM(`amount`)", "filters": [{"scope": "card", "value": "West"}], "drill": "detail-card"}}},
            {**common, "object_type": "page", "object_id": "p1", "title": "Executive", "attributes": {"layout": {"cards": ["urn:domo:card:c1"]}}}],
        "edges": [{"source_key": "page:p1", "target_key": "card:urn:domo:card:c1", "relation": "contains", "definition_state": "definition_complete", "source_refs": []}],
        "coverage": [{"capability": "selected_scope_dependency_closure", "status": "partial", "object_keys": ["page:p1", "card:urn:domo:card:c1"],
                      "gaps": ["PDP evidence pending"], "truncated": False, "source_refs": [], "provenance": {}}],
        "manual_capture_queue": [{"request_id": "capture-1", "object_key": "page:p1", "evidence_kind": "page_layout_interactions_visibility", "reason": "Drill fixture missing", "blocking": True, "accepted_formats": ["json"]}],
        "checkpoints": [], "diagnostics": []}, "bundle_fingerprint", True)


def envelope(bundle):
    return seal({"contract_version": "omnikit.domo.source-evidence.v1",
        "source_bundle_fingerprint": "sha256:" + "c" * 64,
        "evidence_bundle_fingerprint": bundle["bundle_fingerprint"],
        "evidence_ref": "domo-evidence://sha256/" + bundle["bundle_fingerprint"][7:],
        "payload_json": canonical(bundle)}, "envelope_fingerprint", True)


def domo_plan():
    fields = ("field", "measure", "grouping", "sort", "filter", "filter_context", "control", "interaction", "drill",
              "visualization", "formatting", "layout", "responsive", "security", "persona", "operation")
    denominator = {f + "_ids": ["b-" + f] for f in fields}
    denominator["denominator_hash"] = "sha256:" + "d" * 64
    return {"contract_version": "domo-to-omni.dashboard-rebuild-plan.v1", "plan_id": "plan-1", "run_id": "run-1",
        "scope_id": "scope-1", "migration_unit_id": "unit-1", "validation_cycle_id": "cycle-1",
        "source": {"context": {"run_id": "run-1", "scope_id": "scope-1", "migration_unit_id": "unit-1", "page_id": "graph-page-1",
                               "source_card_order": ["graph-card-1"], "source_placement_order": ["place-1"]},
            "page": {"object_id": "graph-page-1", "object_type": "page"},
            "cards": [{"card": {"object_id": "graph-card-1"}, "query_ids": ["query-1"]}],
            "placements": [{"placement_id": "place-1", "page_id": "graph-page-1", "card_id": "graph-card-1", "grid": {"x": 0, "y": 0, "width": 12, "height": 4}}],
            "queries": [{"query": {"object_id": "query-1"}, "card_id": "graph-card-1", "placement_ids": ["place-1"],
                "behaviors": [{"behavior_id": "b-" + f, "kind": f} for f in fields], "behavior_denominator": denominator}],
            "special_behaviors": [{"behavior_id": "app-1", "kind": "app", "parent_type": "page", "parent_id": "graph-page-1"}]},
        "card_mappings": [{"source_card_id": "graph-card-1", "target_card_id": "planned-card"}],
        "query_mappings": [{"query_id": "query-1", "filters": [{"stage": "dashboard", "operator": "is_not_null"}],
                            "security": [{"persona": "allowed-and-denied"}]}],
        "behavior_resolutions": [{"source_behavior_id": "app-1", "status": "pending", "owner_ref": "person-ref://fictional/owner"}],
        "plan_hash": "sha256:" + "a" * 64, "proposal_only": True, "authorizes_build": False,
        "authorizes_content_creation": False, "authorizes_source_decommission": False,
        "provenance": {"producer_ref": "agent-ref://domo_to_omni_architect"}, "security_metadata": {"classification": "confidential"}}


def handoff():
    return seal({"contract_version": "domo-to-omni.external-redesign-handoff.v1", "run_id": "run-1", "scope_id": "scope-1",
        "migration_unit_id": "unit-1", "handoff_id": "handoff-1", "handoff_ref": "handoff-ref://fictional/app",
        "capability": "application_redesign", "owner_ref": "person-ref://fictional/app-owner",
        "source_objects": [{"object_id": "graph-app", "object_type": "app_studio_app", "native_id": "native-app", "object_hash": "sha256:" + "a" * 64}],
        "analytic_outputs": [], "side_effect_kinds": ["external_write"], "evidence_refs": ["evidence-ref://fictional/app"],
        "accepted_decision": {"status": "accepted", "accepted_by_ref": "human-ref://fictional/owner", "decision_ref": "decision-ref://fictional/app", "accepted_at": "2026-10-21T10:00:00-05:00"},
        "assignment_only": True, "authorizes_build": False, "authorizes_target_write": False,
        "authorizes_tenant_acceptance": False, "authorizes_production_readiness": False,
        "authorizes_publication": False, "authorizes_cutover": False}, "handoff_hash", True)


def sigma_snapshot():
    value = {"snapshotContract": "sigma-api-v2", "synthetic": True, "connections": [],
        "dataModels": [{"dataModelId": "model-1", "spec": {"dataModelId": "model-1", "documentVersion": 2,
            "pages": [{"pageId": "model-page", "elements": [{"elementId": "table-1", "kind": "table",
                "columns": [{"columnId": "amount", "formula": "[Amount] * 2"}],
                "metrics": [{"metricId": "sum-1", "formula": "Sum([amount])"}],
                "relationships": [{"relationshipId": "join-1", "targetElementId": "other-table"}]}]}]}}],
        "workbooks": [{"workbookId": "workbook-1", "pages": [{"pageId": "page-1", "elements": [
            {"elementId": "chart-1", "type": "chart", "visualizationType": "column"},
            {"elementId": "chart-2", "type": "table"}]}],
            "controls": [{"controlId": "control-1", "values": ["East"]}], "grants": [{"role": "viewer"}]}]}
    value["prepush_context"] = {"schema_version": "sigma-prepush-context.v1", "source_sha256": sha(value),
        "evidence_ref": "fictional-fixture://context", "workbook_id": "workbook-1",
        "elements": {"chart-1": {"field_locators": ["data-model:model-1/element:table-1/metric:sum-1"], "layout": {"x": 0, "y": 0, "w": 12, "h": 10}}},
        "controls": {"control-1": {"target_element_ids": ["chart-1"], "values": ["East"]}}}
    return value


def sigma_envelope(schema, data):
    return seal({"schema_version": schema, "artifact_id": "artifact-1", "run_id": "run-1", "scope_id": "scope-1",
        "created_at": "2026-10-21T10:00:00-05:00", "producer": "agent-ref://fictional/source",
        "classification": "synthetic_fixture", "source_references": ["sigma://workbooks/workbook-1"],
        "upstream_hashes": [], "immutable": True, "supersession_state": "current", "supersedes_artifact_id": None,
        "superseded_by_artifact_id": None, "payload": data}, "content_hash")


def route(mode="omni_semantic_reconstruction"):
    return {"schema_version": "sigma-semantic-routing-decision-request.v1", "decision_id": "route-1",
        "run_id": "run-1", "scope_id": "scope-1", "migration_unit_id": "unit-1", "mode": mode,
        "comparison_scope_refs": ["sigma://workbooks/workbook-1", "sigma://dataModels/model-1"],
        "build_scope_refs": ["sigma://workbooks/workbook-1"],
        "target_environment_refs": ["environment-ref://omni/dev"] + (["environment-ref://dbt/dev"] if mode == "warehouse_first_refactor" else []),
        "decided_by_ref": "human-ref://fictional/owner", "decision_ref": "human-decision-ref://fictional/route",
        "decision_record_revision": "v1", "decision_record_sha256": "a" * 64,
        "source_context_bindings": [{"artifact_id": "artifact-1", "artifact_scope_id": "scope-1", "content_hash": "b" * 64}]}


class MigrationSourceTests(unittest.TestCase):
    def test_domo_evidence_preserves_native_urn_formula_edge_and_gaps(self):
        source = domo_bundle(); result = parse(source, "domo")
        self.assertEqual(result["upstream_payload"], source)
        card = next(a for a in result["assets"] if a["kind"] == "visual")
        self.assertEqual(card["source_id"], "urn:domo:card:c1")
        self.assertEqual(card["source_payload"]["attributes"]["definition"]["formula"], "SUM(`amount`)")
        self.assertEqual(result["dependencies"][0]["status"], "supplied_graph_binding")
        self.assertEqual(result["upstream_coverage"], source["coverage"])
        self.assertEqual(result["manual_capture_queue"], source["manual_capture_queue"])
        self.assertFalse(result["migration_context"]["target_write_authority"])

    def test_domo_envelope_integrity_and_no_credential_persistence(self):
        bundle = domo_bundle(); source = envelope(bundle)
        result = parse(source, "domo"); self.assertEqual(result["decoded_source_payload"], bundle)
        source["evidence_ref"] = "domo-evidence://sha256/" + "0" * 64
        seal(source, "envelope_fingerprint", True)
        with self.assertRaisesRegex(ValueError, "envelope_reference_mismatch"): parse(source, "domo")
        bundle = domo_bundle(); bundle["objects"][0]["attributes"]["api_token"] = "confidential-never-output"
        with self.assertRaisesRegex(ValueError, "credential_bearing"): parse(bundle, "domo")

    def test_domo_changed_fingerprint_and_unsanitized_state_rejected(self):
        source = domo_bundle(); source["objects"][0]["title"] = "Modified"
        with self.assertRaisesRegex(ValueError, "fingerprint_mismatch"): parse(source, "domo")
        source = domo_bundle(); source["objects"][0]["redaction_state"] = "pending"; seal(source, "bundle_fingerprint", True)
        with self.assertRaisesRegex(ValueError, "unsanitized_object"): parse(source, "domo")

    def test_domo_plan_keeps_exact_denominator_and_native_id_uncertainty(self):
        source = domo_plan(); result = parse(source, "domo")
        self.assertEqual(result["migration_context"]["source_denominator"], source["source"])
        self.assertEqual(result["migration_context"]["target_proposal"]["query_mappings"], source["query_mappings"])
        self.assertTrue(all(a["source_id"] is None for a in result["assets"]))
        self.assertIn("domo.special_behavior_unresolved", {g["code"] for g in result["gaps"]})
        self.assertEqual(result["migration_context"]["store_backed_readiness"], "not_verified")
        source["card_mappings"] = []
        self.assertIn("domo.incomplete_card_mappings", {g["code"] for g in parse(source, "domo")["gaps"]})

    def test_domo_plan_conflicting_membership_or_write_claim_rejected(self):
        source = domo_plan(); source["source"]["queries"][0]["card_id"] = "wrong-card"
        with self.assertRaisesRegex(ValueError, "query_mismatch"): parse(source, "domo")
        source = domo_plan(); source["authorizes_build"] = True
        with self.assertRaisesRegex(ValueError, "contradictory_authority"): parse(source, "domo")

    def test_domo_plan_cannot_silently_omit_query_security_or_filter_mapping(self):
        source = domo_plan(); mapping = source["query_mappings"][0]; mapping["outcome"] = "mapped"
        mapping["filters"] = []; mapping["security"] = []
        result = parse(source, "domo")
        missing_facets = {g.get("detail", {}).get("facet") for g in result["gaps"] if g["code"] == "domo.query_behavior_mapping_gap"}
        self.assertTrue({"security", "filters"} <= missing_facets)

    def test_external_handoff_is_assignment_only(self):
        source = handoff(); result = parse(source, "domo")
        self.assertEqual(result["assets"][0]["source_id"], "native-app")
        self.assertTrue(result["migration_context"]["assignment_only"])
        self.assertFalse(result["migration_context"]["build_authority"])
        self.assertEqual(result["migration_context"]["side_effect_kinds"], ["external_write"])
        source["accepted_decision"]["accepted_by_ref"] = "agent-ref://self-approval"; seal(source, "handoff_hash", True)
        with self.assertRaisesRegex(ValueError, "human_decision"): parse(source, "domo")

    def test_sigma_snapshot_preserves_model_behavior_context_and_no_default_route(self):
        source = sigma_snapshot(); result = parse(source, "sigma")
        self.assertEqual(result["upstream_payload"], source)
        self.assertEqual(result["migration_context"]["source_context"], source["prepush_context"])
        model_element = next(a for a in result["assets"] if a["source_id"] == "table-1")
        self.assertEqual(model_element["source_payload"]["relationships"][0]["relationshipId"], "join-1")
        self.assertEqual(model_element["source_payload"]["metrics"][0]["formula"], "Sum([amount])")
        self.assertIsNone(result["migration_context"]["route"])
        self.assertIn("sigma.target_design_waits_for_explicit_route", {g["code"] for g in result["gaps"]})
        self.assertTrue(result["migration_context"]["synthetic"])

    def test_sigma_stale_context_and_wrong_control_target_rejected(self):
        source = sigma_snapshot(); source["dataModels"][0]["spec"]["documentVersion"] = 3
        with self.assertRaisesRegex(ValueError, "context_stale"): parse(source, "sigma")
        source = sigma_snapshot(); source["prepush_context"]["controls"]["control-1"]["target_element_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "unknown_control_target"): parse(source, "sigma")

    def test_sigma_scope_does_not_drop_excluded_source(self):
        source = sigma_snapshot()
        source["_migration_scope"] = {"schema_version": "sigma-migration-scope.v1", "workbook_id": "workbook-1",
            "original_source_sha256": source["prepush_context"]["source_sha256"], "selected_chart_ids": ["chart-1"],
            "excluded_chart_ids": ["chart-2"], "issues": [], "target_write_authority": False}
        result = parse(source, "sigma")
        self.assertTrue({"chart-1", "chart-2"} <= {a["source_id"] for a in result["assets"]})
        self.assertIn("sigma.scope_exclusions_not_rederived_full_source_retained", {g["code"] for g in result["gaps"]})

    def test_sigma_graph_hash_nodes_edges_and_orphan_rejection(self):
        nodes = [{"node_id": "n1", "node_type": "page", "native_id": "page-1", "parent_node_id": None, "properties": {}, "source_refs": []},
                 {"node_id": "n2", "node_type": "element", "native_id": "chart-1", "parent_node_id": "n1", "properties": {"formula": "[Amount]"}, "source_refs": []}]
        data = {"workbook_id": "workbook-1", "source_freeze": {"strategy": "version_tag"}, "nodes": nodes,
            "edges": [{"from_node_id": "n1", "to_node_id": "n2", "relation": "contains"}],
            "exact_node_set_sha256": sha([{k: n[k] for k in ("node_id", "node_type", "native_id")} for n in nodes]),
            "unresolved_behavior": ["Control binding pending"]}
        source = sigma_envelope("sigma-workbook-graph.v1", data); result = parse(source, "sigma")
        self.assertEqual(result["assets"][1]["source_id"], "chart-1")
        self.assertEqual(result["dependencies"][0]["relation"], "contains")
        source["payload"]["edges"][0]["to_node_id"] = "missing"; seal(source, "content_hash")
        with self.assertRaisesRegex(ValueError, "orphan_or_duplicate"): parse(source, "sigma")

    def test_sigma_behavior_manifest_cannot_hide_open_action(self):
        data = {"workbook_id": "workbook-1", "behaviors": [{"behavior_id": "b1", "behavior_type": "action",
            "source_ref": "sigma://workbooks/workbook-1/actions/a1", "disposition": "external_redesign_required",
            "evidence_refs": [], "owner_ref": "human-ref://fictional/owner", "acceptance_test": "Verify approved side effect", "blocking": True}],
            "closed_denominator": False, "unresolved_behavior_ids": ["b1"], "analytical_build_authorized": False}
        source = sigma_envelope("sigma-behavior-manifest.v1", data); result = parse(source, "sigma")
        self.assertIn("sigma.blocking_behavior", {g["code"] for g in result["gaps"]})
        source["payload"]["closed_denominator"] = True; seal(source, "content_hash")
        with self.assertRaisesRegex(ValueError, "denominator_mismatch"): parse(source, "sigma")

    def test_sigma_snapshot_artifact_checks_specification_identity_and_hash(self):
        specification = {"dataModelId": "model-1", "documentVersion": 2, "pages": []}
        data = {"data_model_id": "model-1", "source_freeze": {"data_model_document_version": 2},
            "specification_state": "bound", "sanitized_specification": specification,
            "specification_sha256": sha(specification), "documented_omissions": ["no live query replay"],
            "source_bindings": [{"type": "table", "tableId": "table-1"}]}
        source = sigma_envelope("sigma-data-model-snapshot.v1", data); result = parse(source, "sigma")
        self.assertEqual(result["migration_context"]["source_bindings"], data["source_bindings"])
        source["payload"]["sanitized_specification"]["documentVersion"] = 3; seal(source, "content_hash")
        with self.assertRaisesRegex(ValueError, "specification_hash_mismatch"): parse(source, "sigma")

    def test_sigma_human_route_preserved_without_write_authority(self):
        for mode in ("omni_semantic_reconstruction", "warehouse_first_refactor"):
            result = parse(route(mode), "sigma")
            self.assertEqual(result["migration_context"]["route"], mode)
            self.assertFalse(result["migration_context"]["upstream_write_permitted"])
            self.assertEqual(result["migration_context"]["dbt_planning_applicable"], mode == "warehouse_first_refactor")
        source = route(); source["target_environment_refs"].append("environment-ref://dbt/dev")
        with self.assertRaisesRegex(ValueError, "target_mismatch"): parse(source, "sigma")
        source = route(); source.pop("mode")
        with self.assertRaisesRegex(ValueError, "explicit_route_required"): parse(source, "sigma")

    def test_sigma_package_manifest_is_not_os_review_or_source_verification(self):
        source = {"schema_version": "sigma-prepush-package.v1", "route": "omni_semantic_reconstruction",
            "source_sha256": "a" * 64, "target_sha256": "b" * 64,
            "files": {"source.json": "c" * 64, "target.json": "d" * 64, "omni/document.create.json": "e" * 64},
            "review": {"decision": "accept", "route": "omni_semantic_reconstruction", "source_sha256": "a" * 64, "target_sha256": "b" * 64, "actor": {"uid": 501}},
            "synthetic": True, "target_write_authority": False, "migration_accepted": False, "live_validation": "not_performed"}
        result = parse(source, "sigma")
        self.assertEqual(result["migration_context"]["route_status"], "supplied_local_review_not_authenticated")
        self.assertEqual(result["migration_context"]["source_reverification"], "not_performed")
        source["files"]["dbt/models/m.sql"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "direct_package_upstream_files"): parse(source, "sigma")

    def test_new_profiles_require_pin_and_never_upgrade_forged_readiness(self):
        with self.assertRaisesRegex(ValueError, "producer_revision"):
            t.translate(json.dumps(sigma_snapshot()).encode(), "sigma-agent", "0" * 40)
        source = sigma_snapshot(); source["ready"] = True; source["prepush_context"]["source_sha256"] = sha({k: v for k, v in source.items() if k != "prepush_context"})
        result = parse(source, "sigma")
        self.assertEqual(result["migration_context"]["store_backed_readiness"], "not_verified")
        self.assertEqual(result["native_validation"], "not_run")


if __name__ == "__main__":
    unittest.main()
