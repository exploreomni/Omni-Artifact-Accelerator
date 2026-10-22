"""Tableau case identity, applied-state gaps and deterministic result derivatives."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/omni-artifact-accelerator/scripts"))
import visual_workflow as v  # noqa: E402

spec = importlib.util.spec_from_file_location("tableau_workflow_fixture", ROOT / "tests/test_tableau_visual_bridge.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def profile(headers=None):
    return {"schema_version": 1, "format": "csv", "encoding": "utf-8", "headers": headers or ["Team", "Value"],
            "subtotal_policy": "preserve", "columns": [
                {"ordinal": 0, "name": "team", "type": "string", "null_tokens": [], "nullable": False},
                {"ordinal": 1, "name": "value", "type": "number", "null_tokens": ["NULL"], "nullable": True,
                 "decimal_separator": ".", "group_separator": None, "percent": False}]}


class TableauVisualWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / "project"
        v.ap.init(self.root, "Synthetic Tableau workflow", "migration", "dashboard")
        result = f.capture_fixture(self.root / "inputs/capture")
        self.capture = result["capture"]
        # Explicit synthetic observations for numerical unit qualification only.
        # Capture's real producer intentionally does not make these assertions.
        self.context = {"filters": {}, "parameters": {}, "timezone": "UTC", "locale": "en-US",
                        "data_watermark": "synthetic-fixed-1", "population": "all-teams", "principal": "synthetic-viewer"}
        self.capture["source"]["state_observation"] = {**copy.deepcopy(self.context), "reference": "synthetic-state-observation"}
        self.refresh_source()
        self.put("evidence/candidate.json", {"kind": "synthetic_candidate"})

    def put(self, relative, value):
        (self.root / relative).write_text(json.dumps(value))

    def refresh_source(self):
        f.reseal(self.capture)
        self.put("inputs/capture/original.json", self.capture)
        inventory = f.t.translate((self.root / "inputs/capture/original.json").read_bytes(), "tableau-capture")
        self.put("inputs/inventory.json", inventory)
        path = self.root / "contracts/visual.json"
        if path.exists():
            path.unlink()
        v.prepare(self.root, "inputs/capture/original.json", "inputs/inventory.json", "contracts/visual.json")
        self.req = v.load(self.root, "contracts/visual.json")
        self.item = next(i for i in self.req["items"] if i["source_id"] == f.P1)
        self.case = next(c for c in self.item["required_cases"] if c["case_id"].endswith("/numeric/default"))
        self.case["source_capture"] = v.pin(self.root, "inputs/capture/original.json")
        self.case["source_binding"] = {"worksheet_id": f.S, "placement_id": f.P1, "view_id": "sheet-0",
                                       "state_sha256": f.b.sha(self.capture["request"]["state"])}
        self.req.update(route="reuse_existing", route_reference="synthetic-reuse-review")
        self.put("contracts/visual.json", self.req)

    def comparison(self):
        self.put("evidence/target.json", [{"team": "A", "amount": 10}, {"team": "B", "amount": 20}])
        spec = {"schema_version": 1, "kind": "analyst_numeric_comparison_spec", "case_id": self.case["case_id"],
                "requirements": v.pin(self.root, "contracts/visual.json"), "candidate": v.pin(self.root, "evidence/candidate.json"),
                "source": {"file": v.pin(self.root, "inputs/capture/view-001.csv"), "format": "csv", "context": copy.deepcopy(self.context),
                           "complete": True, "completeness_reference": "synthetic-fixture-row-count-2"},
                "target": {"file": v.pin(self.root, "evidence/target.json"), "format": "json", "context": copy.deepcopy(self.context),
                           "complete": True, "completeness_reference": "synthetic-fixture-row-count-2"},
                "persona_equivalence_reference": "synthetic-persona-review", "keys": ["team"], "columns": [
                    {"name": "team", "type": "string", "source": "Team", "target": "team"},
                    {"name": "value", "type": "number", "source": "Value", "target": "amount"}]}
        return spec

    def compare(self, spec):
        self.put("contracts/compare.json", spec)
        path = self.root / "evidence/comparison.json"
        if path.exists():
            path.unlink()
        v.compare(self.root, "contracts/compare.json", "evidence/comparison.json")
        return v.load(self.root, "evidence/comparison.json")

    def test_complete_denominator_and_required_behavior_cases(self):
        _, req = v.requirements(self.root, "contracts/visual.json")
        self.assertEqual(len(req["items"]), len(f.EXPECTED))
        self.assertEqual(len([i for i in req["items"] if i["kind"] == "placement"]), 3)
        cases = {c["case_id"].split("/")[-1] for c in self.item["required_cases"]}
        self.assertTrue({"default", "changed_filter", "changed_parameter", "empty_result", "action_state"} <= cases)
        self.assertEqual(req["brand"]["open_questions"], ["What is the company website URL?"])

    def test_applied_observation_required_even_if_contexts_equal(self):
        self.capture["source"].pop("state_observation")
        self.refresh_source()
        report = self.compare(self.comparison())
        self.assertEqual(report["status"], "inconclusive")
        self.assertIn("source.applied_state_unobserved", report["gaps"])

    def test_correct_rows_and_explicit_observed_state_are_local_evidence_only(self):
        report = self.compare(self.comparison())
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["native_validation"], "not_established")
        v.coverage(self.root, "contracts/visual.json", "evidence/candidate.json", ["evidence/comparison.json"], "evidence/coverage.json")
        result = v.load(self.root, "evidence/coverage.json")
        self.assertEqual(result["evidence_coverage"], "partial")
        self.assertEqual(result["business_acceptance"], "not_recorded")

    def test_wrong_placement_view_or_state_rejects(self):
        for key, value in (("placement_id", f.P2), ("view_id", "dashboard-1"), ("state_sha256", "0" * 64)):
            req = copy.deepcopy(self.req)
            case = next(c for i in req["items"] for c in i["required_cases"] if c["case_id"] == self.case["case_id"])
            case["source_binding"][key] = value
            self.put("contracts/visual.json", req)
            with self.assertRaises(ValueError):
                v.requirements(self.root, "contracts/visual.json")

    def test_wrong_source_principal_parameter_and_locale_are_inconclusive(self):
        for key, changed in (("principal", "admin"), ("parameters", {"region": "west"}), ("locale", "de-DE")):
            spec = self.comparison()
            spec["source"]["context"][key] = changed
            spec["target"]["context"][key] = changed
            self.assertEqual(self.compare(spec)["status"], "inconclusive")

    def test_row_order_must_be_explicit_and_can_fail_independently(self):
        spec = self.comparison()
        self.put("evidence/target.json", [{"team": "B", "amount": 20}, {"team": "A", "amount": 10}])
        spec["target"]["file"] = v.pin(self.root, "evidence/target.json")
        self.assertEqual(self.compare(spec)["status"], "pass")
        spec["row_order"] = "exact"
        with self.assertRaisesRegex(ValueError, "order_basis"):
            self.compare(spec)
        spec["order_basis"] = "synthetic-rank-display-contract"
        report = self.compare(spec)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["order_mismatch"])

    def test_normalized_derivative_replay_and_binding(self):
        spec = self.comparison()
        raw = (self.root / "inputs/capture/view-001.csv").read_bytes()
        binding = {"capture_content_hash": self.capture["content_hash"], "view_id": "sheet-0", "worksheet_id": f.S,
                   "state_sha256": f.b.sha(self.capture["request"]["state"]), "attachment_sha256": f.b.sha(raw)}
        normalized = f.b.normalize_results(raw, profile(), binding)
        self.put("inputs/normalized.json", normalized)
        spec["source"].update(raw_file=spec["source"]["file"], file=v.pin(self.root, "inputs/normalized.json"), format="tableau-normalized")
        spec["columns"][0]["source"] = "team"
        spec["columns"][1]["source"] = "value"
        self.assertEqual(self.compare(spec)["status"], "pass")
        normalized["rows"][0]["value"] = "999"
        self.put("inputs/normalized.json", normalized)
        spec["source"]["file"] = v.pin(self.root, "inputs/normalized.json")
        with self.assertRaisesRegex(ValueError, "normalization_changed"):
            self.compare(spec)
        normalized = f.b.normalize_results(raw, profile(), {**binding, "view_id": "wrong-sheet"})
        self.put("inputs/normalized.json", normalized)
        spec["source"]["file"] = v.pin(self.root, "inputs/normalized.json")
        self.assertIn("source.normalization_binding_mismatch", self.compare(spec)["gaps"])

    def test_changed_actual_attachment_or_removed_projection_cannot_pass(self):
        (self.root / "inputs/capture/view-001.csv").write_text("Team,Value\nA,999\n")
        with self.assertRaisesRegex(ValueError, "bytes_mismatch"):
            v.requirements(self.root, "contracts/visual.json")
        inventory = v.load(self.root, "inputs/inventory.json")
        inventory["assets"] = [a for a in inventory["assets"] if a["source_id"] != f.P2]
        self.put("inputs/inventory.json", inventory)
        with self.assertRaises(ValueError):
            v.requirements(self.root, "contracts/visual.json")

    def test_duplicate_headers_percent_dates_null_blank_and_subtotals(self):
        raw = 'Name,Name\nCafe,"1.234,50%"\nTotal,NULL\n'.encode()
        selected = profile(["Name", "Name"])
        selected["columns"][1].update(decimal_separator=",", group_separator=".", percent=True)
        binding = {"capture_content_hash": "synthetic", "view_id": "sheet", "worksheet_id": f.S,
                   "state_sha256": "synthetic", "attachment_sha256": f.b.sha(raw)}
        with self.assertRaisesRegex(ValueError, "duplicate_headers"):
            f.b.normalize_results(raw, selected, binding)
        selected["duplicate_header_resolution_reference"] = "synthetic-reviewed-ordinal-mapping"
        result = f.b.normalize_results(raw, selected, binding)
        self.assertEqual(result["rows"], [{"team": "Cafe", "value": "12.3450"}, {"team": "Total", "value": None}])
        bad = raw.replace(b"NULL", b"")
        with self.assertRaisesRegex(ValueError, "formatted_number"):
            f.b.normalize_results(bad, selected, {**binding, "attachment_sha256": f.b.sha(bad)})
        raw = b"Team,Value\nA,21/10/2026\n"
        selected = profile()
        selected["columns"][1].update(type="date", date_format="%d/%m/%Y")
        result = f.b.normalize_results(raw, selected, {**binding, "attachment_sha256": f.b.sha(raw)})
        self.assertEqual(result["rows"][0]["value"], "2026-10-21T00:00:00")

    def test_percent_conversion_preserves_long_decimal_precision(self):
        raw = b"Team,Value\nA,123456789012345678901234567890.1234%\n"
        selected = profile()
        selected["columns"][1]["percent"] = True
        binding = {"capture_content_hash": "synthetic", "view_id": "sheet", "worksheet_id": f.S,
                   "state_sha256": "synthetic", "attachment_sha256": f.b.sha(raw)}
        result = f.b.normalize_results(raw, selected, binding)
        self.assertEqual(result["rows"][0]["value"], "1234567890123456789012345678.901234")


if __name__ == "__main__":
    unittest.main()
