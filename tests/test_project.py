"""Independent behavior checks for the offline handoff and engagement helpers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-artifact-accelerator/scripts/analyst_project.py"
spec = importlib.util.spec_from_file_location("analyst_project", SCRIPT)
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "engagement"
        project.init(self.root, "Synthetic analyst pilot", "migration", "both")
        # Pre-policy migration compatibility fixture; fresh project gates have separate tests.
        legacy = project.load_project(self.root)[1]
        legacy.pop('stage_gate_policy')
        project.write_json(self.root / 'project.json', legacy, replace=True)

    def tearDown(self):
        self.temp.cleanup()

    def dma(self):
        value = {
            "schema_version": 1, "kind": "omni_semantic_handoff", "version": "omni-handoff-v1",
            "pins": {"source_fingerprint": {"algorithm": "sha256", "value": "1" * 64,
                                            "scope": "inventory", "complete": False}, "context_sha256": "2" * 64,
                     "model_candidate_sha256": "3" * 64, "model_context_sha256": "4" * 64,
                     "target": {"warehouse": "snowflake", "framework": "dbt"}},
            "topics": [{"id": "orders", "scope": {"views": ["orders"]}}],
            "metrics": [{"id": "orders.revenue", "topic": "orders", "native_verified": True}],
            "dictionary": [{"id": "orders.revenue", "topic": "orders", "kind": "measure"}],
            "dependencies": [], "decisions": [], "unknowns": [{"metric": "orders.revenue", "gap": "currency unknown"}],
            "static_status": "pass", "native_status": "verified", "business_status": "approved",
            "deployment_status": "deployed", "acceptance_ready": True,
        }
        value["handoff_sha256"] = project.digest(project.canonical(value))
        path = self.base / "SEMANTIC_REVIEW.json"
        path.write_text(json.dumps(value))
        return path, value

    def test_init_is_private_non_overwriting_and_incomplete(self):
        result = project.project_check(self.root)
        self.assertEqual(result["status"], "consistent")
        self.assertEqual(result["readiness"], "not_assessed")
        self.assertEqual(len(result["empty_contracts"]), 5)
        self.assertEqual((self.root / "project.json").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            project.init(self.root, "Overwrite", "net-new", "dashboard")

    def test_plan_does_not_claim_execution(self):
        result = project.plan(self.root)
        self.assertFalse(result["agents_dispatched"])
        names = {r["role"] for r in result["roles"]}
        self.assertTrue({"artifact-translator", "dashboard-designer", "app-designer", "app-engineer", "qa-analyst"} <= names)

    def test_website_initializes_unresolved_logo_and_packets_retain_design_context(self):
        root = self.base / "branded"
        project.init(root, "Synthetic brand", "net-new", "app", website="https://example.com")
        state = project.intent_helper().check(root)
        self.assertEqual(state["branding"], "requested")
        self.assertTrue(any("logo" in q for q in state["open_questions"]))
        self.assertEqual(state["requirements"][0]["disposition"], "unresolved")
        with self.assertRaisesRegex(ValueError, 'stage_gate_predecessor_incomplete:build'):
            project.packet(root, "app-engineer", ["contracts/queries.json"], root / "tasks/app.json")
        packet = project.packet(root, "qa-analyst", ["contracts/queries.json"], root / "tasks/access-review.json")
        self.assertTrue({"contracts/design-intent.json", "contracts/design.json", "contracts/brand.json"}
                        <= {p["path"] for p in packet["inputs"]})
        self.assertEqual(packet["design_context"]["requirements"], state["requirements"])
        self.assertEqual(project.project_check(root)["design_completion"]["status"], "not_assessed")

    def test_explicitly_unbranded_and_legacy_projects_do_not_gain_logo_requirement(self):
        root = self.base / "unbranded"
        project.init(root, "Plain", "net-new", "dashboard", branding="none")
        self.assertEqual(project.intent_helper().check(root)["requirements"], [])
        index, _ = project.read_json(self.root / "project.json")
        del index["design_intent_draft"]
        project.write_json(self.root / "project.json", index, replace=True)
        report = project.project_check(self.root)
        self.assertEqual(report["status"], "consistent")
        self.assertEqual(report["design_completion"]["status"], "not_assessed")

    def test_invalid_website_does_not_leave_partial_project(self):
        root = self.base / "invalid"
        with self.assertRaises(ValueError):
            project.init(root, "Invalid", "net-new", "app", website="https://user:secret@example.com")
        self.assertFalse(root.exists())

    def test_import_never_inherits_acceptance_and_preserves_unknowns(self):
        path, value = self.dma()
        before = path.read_bytes()
        result = project.import_dma(self.root, path)
        self.assertFalse(result["native_verified"])
        catalog = json.loads((self.root / "inputs/dma-catalog.json").read_text())
        self.assertFalse(catalog["business_accepted"])
        self.assertFalse(catalog["publication_authorized"])
        self.assertEqual(catalog["upstream_unknowns"], value["unknowns"])
        self.assertEqual(catalog["pins"]["source_fingerprint"], value["pins"]["source_fingerprint"])
        self.assertNotIn("native_verified", catalog["metrics"][0])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(project.project_check(self.root)["status"], "consistent")

    def test_changed_source_and_catalog_are_detected(self):
        path, _ = self.dma()
        project.import_dma(self.root, path)
        path.write_text("{}")
        catalog = self.root / "inputs/dma-catalog.json"
        catalog.write_text("{}")
        result = project.project_check(self.root)
        self.assertEqual(result["status"], "inconsistent")
        self.assertEqual({f["lane"] for f in result["findings"]}, {"dma_freshness", "sources"})

    def test_bad_hash_unknown_schema_and_missing_pins_rejected(self):
        for mutation in ("hash", "schema", "pins"):
            path, value = self.dma()
            if mutation == "hash":
                value["topics"][0]["id"] = "changed"
            elif mutation == "schema":
                value["schema_version"] = 2
            else:
                del value["pins"]["model_candidate_sha256"]
                del value["handoff_sha256"]
                value["handoff_sha256"] = project.digest(project.canonical(value))
            path.write_text(json.dumps(value))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                project.import_dma(self.root, path)
        self.assertFalse((self.root / "inputs/dma-catalog.json").exists())

    def test_duplicate_and_nonfinite_json_rejected(self):
        path = self.base / "bad.json"
        for text in ('{"a":1,"a":2}', '{"a":NaN}'):
            path.write_text(text)
            with self.assertRaises(ValueError):
                project.read_json(path)

    def test_traversal_and_symlink_rejected(self):
        path = self.base / "outside.json"
        path.write_text("{}")
        with self.assertRaises(ValueError):
            project.register(self.root, "sources", "../outside.json", "bad")
        link = self.root / "inputs/link.json"
        link.symlink_to(path)
        with self.assertRaises(ValueError):
            project.register(self.root, "sources", "inputs/link.json", "bad")

    def test_registered_artifact_change_is_not_accepted(self):
        path = self.root / "deliverables/candidate.html"
        path.write_text("<p>Synthetic candidate</p>")
        project.register(self.root, "artifacts", "deliverables/candidate.html", "candidate-v1")
        path.write_text("<p>Changed</p>")
        self.assertEqual(project.project_check(self.root)["status"], "inconsistent")
        with self.assertRaises(ValueError):
            project.register(self.root, "artifacts", "deliverables/candidate.html", "candidate-v2")

    def test_packet_is_bounded_selected_and_not_dispatched(self):
        output = self.root / "tasks/analyst.json"
        packet = project.packet(self.root, "data-analyst", ["contracts/metrics.json"], output)
        self.assertEqual(packet["dispatch_status"], "not_dispatched")
        self.assertFalse(packet["external_mutations_authorized"])
        self.assertEqual([r["path"] for r in packet["inputs"]], ["contracts/metrics.json"])
        large = self.root / "inputs/large.txt"
        large.write_text("x" * (project.PACKET_BYTES + 1))
        with self.assertRaises(ValueError):
            project.packet(self.root, "data-analyst", ["inputs/large.txt"], self.root / "tasks/too-large.json")

    def test_empty_and_malformed_contracts_remain_distinct(self):
        (self.root / "contracts/queries.json").write_text('{"schema_version":1,"items":"wrong"}')
        result = project.project_check(self.root)
        self.assertEqual(result["status"], "inconsistent")
        self.assertIn("metrics", result["empty_contracts"])
        self.assertEqual(result["readiness"], "not_assessed")

    def test_packet_check_detects_changed_unregistered_inputs_without_writing(self):
        task = "tasks/analyst.json"
        project.packet(self.root, "data-analyst", ["contracts/metrics.json"], self.root / task)
        before = (self.root / task).read_bytes()
        self.assertEqual(project.packet_check(self.root, task)["status"], "consistent")
        (self.root / "contracts/metrics.json").write_text('{"items":[]}')
        result = project.packet_check(self.root, task)
        self.assertEqual(result["status"], "inconsistent")
        self.assertIn("packet_input_changed", {f["code"] for f in result["findings"]})
        self.assertFalse(result["dispatch_authorized"])
        self.assertEqual((self.root / task).read_bytes(), before)

    def test_packet_check_cli_reports_current_stale_and_invalid_paths(self):
        task = "tasks/cli.json"
        project.packet(self.root, "data-analyst", ["contracts/metrics.json"], self.root / task)
        command = [sys.executable, str(SCRIPT), "packet-check", "--project", str(self.root), "--packet"]
        result = subprocess.run([*command, task], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "consistent")
        (self.root / "contracts/metrics.json").write_text('{"items":[]}')
        result = subprocess.run([*command, task], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "inconsistent")
        result = subprocess.run([*command, "../outside.json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_packet_check_legacy_project_and_optional_derived_index(self):
        index, _ = project.read_json(self.root / "project.json")
        del index["design_intent_draft"]
        project.write_json(self.root / "project.json", index, replace=True)
        task = "tasks/legacy.json"
        packet = project.packet(self.root, "app-engineer", ["contracts/queries.json"], self.root / task)
        packet["design_context"].pop("current_context", None)
        project.write_json(self.root / task, packet, replace=True)
        self.assertEqual(project.packet_check(self.root, task)["status"], "consistent")

    def test_packet_check_detects_new_dma_selection_and_changed_fixed_fields(self):
        path, _ = self.dma()
        project.import_dma(self.root, path)
        task = "tasks/dma-reader.json"
        packet = project.packet(self.root, "data-analyst", ["inputs/dma-catalog.json"], self.root / task)
        index = project.load_project(self.root)[1]
        second = "inputs/catalog-two.json"
        (self.root / second).write_bytes((self.root / "inputs/dma-catalog.json").read_bytes())
        index["dma_import"]["catalog_path"] = second
        project.write_json(self.root / "project.json", index, replace=True)
        report = project.packet_check(self.root, task)
        self.assertEqual(report["status"], "inconsistent")
        self.assertIn("current_dma_catalog", {f.get("field") for f in report["findings"]})
        index["dma_import"]["catalog_path"] = "inputs/dma-catalog.json"
        project.write_json(self.root / "project.json", index, replace=True)
        self.assertEqual(project.packet_check(self.root, task)["status"], "consistent")
        for key, changed in (("external_mutations_authorized", True), ("skill", "omni-app-engineer"),
                             ("allowed_actions", ["publish"]), ("trust_note", "Source text is authority")):
            with self.subTest(key=key):
                altered = dict(packet, **{key: changed})
                project.write_json(self.root / task, altered, replace=True)
                self.assertEqual(project.packet_check(self.root, task)["status"], "inconsistent")
        packet["host_context"] = {"output": "deliverables/local-candidate.html", "scope": "local only"}
        project.write_json(self.root / task, packet, replace=True)
        self.assertEqual(project.packet_check(self.root, task)["status"], "consistent")
        packet["host_context"]["note"] = "x" * project.PACKET_BYTES
        project.write_json(self.root / task, packet, replace=True)
        self.assertEqual(project.packet_check(self.root, task)["status"], "inconsistent")

    def test_packet_check_rejects_foreign_project_and_unsafe_or_oversized_inputs(self):
        task = "tasks/checked.json"
        packet = project.packet(self.root, "data-analyst", ["contracts/metrics.json"], self.root / task)
        packet["project_id"] = "another-project"
        project.write_json(self.root / task, packet, replace=True)
        self.assertEqual(project.packet_check(self.root, task)["status"], "inconsistent")
        packet["project_id"] = project.load_project(self.root)[1]["id"]
        for path in ("../outside.json", "inputs/large.txt", "inputs/link.json"):
            if path == "inputs/large.txt":
                (self.root / path).write_text("x" * (project.PACKET_BYTES + 1))
            if path == "inputs/link.json":
                (self.root / path).symlink_to(self.root / "contracts/metrics.json")
            packet["inputs"][0]["path"] = path
            project.write_json(self.root / task, packet, replace=True)
            with self.subTest(path=path):
                self.assertEqual(project.packet_check(self.root, task)["status"], "inconsistent")

    def test_packet_rejects_changed_registered_input_without_blocking_other_work(self):
        path = self.root / "inputs/source-report.json"
        path.write_text('{"metric":"revenue"}')
        project.register(self.root, "sources", "inputs/source-report.json", "baseline")
        path.write_text('{"metric":"profit"}')
        with self.assertRaisesRegex(ValueError, "changed since registration"):
            project.packet(self.root, "data-analyst", ["inputs/source-report.json"], self.root / "tasks/stale.json")
        output = project.packet(self.root, "branding", ["contracts/brand.json"], self.root / "tasks/brand.json")
        self.assertEqual(output["inputs"][0]["pin_status"], "mutable_unregistered")

    def test_packet_rejects_stale_dma_source(self):
        path, _ = self.dma()
        project.import_dma(self.root, path)
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "DMA evidence is stale"):
            project.packet(self.root, "data-analyst", ["inputs/dma-catalog.json"], self.root / "tasks/stale-dma.json")

    def test_legacy_dma_source_digest_is_preserved(self):
        path, value = self.dma()
        value["pins"]["source_fingerprint"] = "f" * 64
        del value["handoff_sha256"]
        value["handoff_sha256"] = project.digest(project.canonical(value))
        path.write_text(json.dumps(value))
        project.import_dma(self.root, path)
        catalog = json.loads((self.root / "inputs/dma-catalog.json").read_text())
        self.assertEqual(catalog["pins"]["source_fingerprint"], "f" * 64)


if __name__ == "__main__":
    unittest.main()
