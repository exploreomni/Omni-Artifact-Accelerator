"""Power BI observed value/render state, result completeness and typed comparisons."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/omni-artifact-accelerator/scripts"))
import visual_workflow as v  # noqa: E402

spec = importlib.util.spec_from_file_location("powerbi_workflow_fixture", ROOT / "tests/test_powerbi_visual_bridge.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def profile():
    return {"schema_version": 1, "format": "json", "rows_pointer": "/results/0/tables/0/rows", "headers": ["Team", "Revenue"],
            "subtotal_policy": "preserve", "columns": [
                {"ordinal": 0, "name": "team", "type": "string", "nullable": False, "null_tokens": []},
                {"ordinal": 1, "name": "revenue", "type": "number", "nullable": True, "null_tokens": [],
                 "decimal_separator": ".", "group_separator": None, "percent": False}]}


class PowerBIVisualWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / "project"
        v.ap.init(self.root, "Synthetic Power BI workflow", "migration", "dashboard")
        result = f.capture_fixture(self.root / "inputs/capture")
        self.capture = result["capture"]
        self.context = {"filters": [], "bookmark": None, "locale": "en-US", "timezone": "UTC", "data_watermark": "fixture-v1",
                        "population": "all-teams", "principal": "synthetic-viewer"}
        self.raw = b'{"results":[{"tables":[{"rows":[{"Team":"A","Revenue":0},{"Team":"B","Revenue":null}]}]}]}'
        capture_view = self.capture["captures"][1]
        self.attachment = f.c.attachment(self.root / "inputs/capture", self.capture, self.raw, "synthetic-results.json", "json",
            "application/json", capture_view, query_id="q1", result_completeness={"status": "unknown", "reference": None})
        self.put("evidence/candidate.json", {"kind": "synthetic_candidate"})
        self.refresh()

    def put(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def refresh(self):
        f.reseal(self.capture)
        self.put("inputs/capture/derivative.json", self.capture)
        raw = (self.root / "inputs/capture/derivative.json").read_bytes()
        self.put("inputs/inventory.json", f.t.translate(raw, "powerbi-capture"))
        path = self.root / "contracts/visual.json"
        if path.exists():
            path.unlink()
        v.prepare(self.root, "inputs/capture/derivative.json", "inputs/inventory.json", "contracts/visual.json")
        self.req = v.load(self.root, "contracts/visual.json")
        self.req.update(route="reuse_existing", route_reference="reviewed-synthetic-existing-topic")
        self.item = next(i for i in self.req["items"] if i["kind"] == "visual" and i["source_id"] == "A")
        self.case = next(c for c in self.item["required_cases"] if c["case_id"].endswith("/numeric/default"))
        self.binding = {"page_id": "Main", "visual_id": "A", "query_id": "q1", "state_sha256": f.b.sha(self.capture["request"]["state"])}
        self.case.update(source_capture=v.pin(self.root, "inputs/capture/derivative.json"), source_binding=self.binding)
        self.put("contracts/visual.json", self.req)

    def observed(self):
        self.attachment["result_completeness"] = {"status": "complete", "reference": "independent-synthetic-row-denominator"}
        for key in ("value_state_observation", "render_state_observation"):
            self.capture["source"][key] = {**self.context, **self.binding, "applied": True, "reference": "synthetic-observer"}
        self.refresh()

    def comparison(self, selected_profile=None):
        self.put("evidence/target.json", [{"team": "A", "amount": 0}, {"team": "B", "amount": None}])
        normalized_binding = {**self.binding, "capture_content_hash": self.capture["content_hash"], "attachment_sha256": f.b.sha(self.raw)}
        normalized = f.b.normalize_results(self.raw, selected_profile or profile(), normalized_binding)
        self.put("inputs/normalized.json", normalized)
        return {"schema_version": 1, "kind": "analyst_numeric_comparison_spec", "case_id": self.case["case_id"],
            "requirements": v.pin(self.root, "contracts/visual.json"), "candidate": v.pin(self.root, "evidence/candidate.json"),
            "source": {"file": v.pin(self.root, "inputs/normalized.json"), "raw_file": v.pin(self.root, "inputs/capture/synthetic-results.json"),
                       "format": "powerbi-normalized", "context": copy.deepcopy(self.context), "complete": True, "completeness_reference": "fixture-2-rows"},
            "target": {"file": v.pin(self.root, "evidence/target.json"), "format": "json", "context": copy.deepcopy(self.context),
                       "complete": True, "completeness_reference": "fixture-2-rows"},
            "persona_equivalence_reference": "synthetic-viewer-equivalence", "keys": ["team"], "columns": [
                {"name": "team", "type": "string", "source": "team", "target": "team"},
                {"name": "revenue", "type": "number", "source": "revenue", "target": "amount", "nullable": True}]}

    def compare(self, spec):
        self.put("contracts/comparison.json", spec)
        path = self.root / "evidence/comparison.json"
        if path.exists():
            path.unlink()
        v.compare(self.root, "contracts/comparison.json", "evidence/comparison.json")
        return v.load(self.root, "evidence/comparison.json")

    def test_full_denominator_and_slicer_obligations(self):
        _, req = v.requirements(self.root, "contracts/visual.json")
        self.assertEqual(len(req["items"]), len(f.EXPECTED))
        self.assertEqual(len([i for i in req["items"] if i["kind"] == "visual"]), 4)
        slicer = next(i for i in req["items"] if i["kind"] == "visual" and i["source_id"] == "Slicer")
        self.assertEqual(slicer["source_facets"]["visual"]["value"]["visual"]["visualType"], "slicer")
        self.assertTrue(any(c["lane"] == "numeric" for c in slicer["required_cases"]))
        self.assertTrue(any(i["kind"] == "control" for i in req["items"]))

    def test_equal_query_rows_do_not_establish_rendered_state_or_complete_results(self):
        report = self.compare(self.comparison())
        self.assertEqual(report["status"], "inconclusive")
        self.assertIn("source.value_state_observation.unverified", report["gaps"])
        self.assertIn("source.render_state_observation.unverified", report["gaps"])
        self.assertIn("source.powerbi_result_completeness_unverified", report["gaps"])

    def test_typed_zero_and_null_distinct_and_recorded_pass_not_native_acceptance(self):
        self.observed()
        spec = self.comparison()
        self.assertEqual(self.compare(spec)["status"], "pass")
        self.put("evidence/target.json", [{"team": "A", "amount": None}, {"team": "B", "amount": 0}])
        spec["target"]["file"] = v.pin(self.root, "evidence/target.json")
        report = self.compare(spec)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["mismatch_count"], 2)
        self.assertEqual(report["native_validation"], "not_established")

    def test_nearby_high_precision_values_are_not_rounded_to_a_false_match(self):
        self.raw = b'{"results":[{"tables":[{"rows":[{"Team":"A","Revenue":12345678901234567890.123456789},{"Team":"B","Revenue":null}]}]}]}'
        (self.root / "inputs/capture/synthetic-results.json").write_bytes(self.raw)
        self.attachment.update(sha256=f.b.sha(self.raw), bytes=len(self.raw))
        self.observed()
        spec = self.comparison()
        for expected, outcome in (("12345678901234567890.123456789", "pass"), ("12345678901234567890.123456790", "fail")):
            self.put("evidence/target.json", [{"team": "A", "amount": expected}, {"team": "B", "amount": None}])
            spec["target"]["file"] = v.pin(self.root, "evidence/target.json")
            self.assertEqual(self.compare(spec)["status"], outcome)

    def test_false_partial_unknown_completeness_and_wrong_render_state_block_pass(self):
        self.observed()
        for state in (False, "partial", "unknown"):
            self.attachment["result_completeness"] = {"status": state, "reference": "declared"}
            self.refresh()
            self.assertEqual(self.compare(self.comparison())["status"], "inconclusive")
        self.attachment["result_completeness"] = {"status": "complete", "reference": "observed"}
        self.capture["source"]["render_state_observation"]["bookmark"] = {"name": "Different"}
        self.refresh()
        self.assertEqual(self.compare(self.comparison())["status"], "inconclusive")

    def test_partial_definition_drift_blocks_even_with_manually_recorded_observations(self):
        self.observed()
        self.capture["source"]["definition_after_fingerprint"] = "0" * 64
        self.refresh()
        self.assertIn("source.powerbi_definition_changed", self.compare(self.comparison())["gaps"])

    def test_source_query_visual_state_identity_is_exact(self):
        for key, value in (("page_id", "Hidden"), ("visual_id", "B"), ("query_id", "q2"), ("state_sha256", "0" * 64)):
            changed = copy.deepcopy(self.req)
            case = next(c for i in changed["items"] for c in i["required_cases"] if c["case_id"] == self.case["case_id"])
            case["source_binding"][key] = value
            self.put("contracts/visual.json", changed)
            with self.assertRaises(ValueError):
                v.requirements(self.root, "contracts/visual.json")

    def test_other_provider_cannot_replace_a_powerbi_case_capture(self):
        # Provider verification occurs after the capture-specific validator. Its
        # independently validated return cannot change the inventory's platform.
        sigma = {"schema_version": "sigma-visual-capture.v1", "request": {"element_id": "A", "page_id": "Main"}}
        for foreign in (sigma, {"schema_version": "tableau-visual-capture.v1"}):
            with patch.object(v, "capture_value", return_value=foreign):
                with self.assertRaisesRegex(ValueError, "capture_provider_mismatch"):
                    v.requirements(self.root, "contracts/visual.json")
        inventory = v.load(self.root, "inputs/inventory.json")
        inventory["source"]["format"] = "supplied_powerbi_source_adapter_result"
        with patch.object(v, "source_inventory", return_value=inventory), patch.object(v, "capture_value", return_value=sigma):
            with self.assertRaisesRegex(ValueError, "capture_provider_mismatch"):
                v.requirements(self.root, "contracts/visual.json")

    def test_result_derivative_replay_and_raw_attachment_drift(self):
        self.observed()
        spec = self.comparison()
        normalized = v.load(self.root, "inputs/normalized.json")
        normalized["rows"][0]["revenue"] = "999"
        self.put("inputs/normalized.json", normalized)
        spec["source"]["file"] = v.pin(self.root, "inputs/normalized.json")
        with self.assertRaisesRegex(ValueError, "normalization_changed"):
            self.compare(spec)
        (self.root / "inputs/capture/synthetic-results.json").write_text("[]")
        with self.assertRaisesRegex(ValueError, "actual_file_mismatch"):
            v.requirements(self.root, "contracts/visual.json")

    def test_omitted_visual_and_changed_route_cannot_disappear(self):
        inventory = v.load(self.root, "inputs/inventory.json")
        inventory["assets"] = [a for a in inventory["assets"] if a["source_id"] != "B"]
        self.put("inputs/inventory.json", inventory)
        with self.assertRaises(ValueError):
            v.requirements(self.root, "contracts/visual.json")
        self.capture["request"].update(route="warehouse_first_refactor", route_reference="reviewed-choice")
        self.refresh()
        self.req.update(route="omni_semantic_reconstruction", route_reference="other")
        self.put("contracts/visual.json", self.req)
        with self.assertRaisesRegex(ValueError, "source_route_conflict"):
            v.requirements(self.root, "contracts/visual.json")

    def test_currency_profiles_duplicate_columns_and_exact_decimal_json(self):
        selected = profile()
        selected.update(format="csv", encoding="utf-8", headers=["Name", "Name"], duplicate_header_resolution_reference="reviewed-ordinals")
        selected["columns"][1].update(currency={"code": "USD", "prefix": "$", "suffix": "", "negative_parentheses": True}, group_separator=",")
        raw = b'Name,Name\nA,"($1,234.50)"\nB,$0.00\n'
        binding = {**self.binding, "capture_content_hash": "fixture", "attachment_sha256": f.b.sha(raw)}
        value = f.b.normalize_results(raw, selected, binding)
        self.assertEqual([r["revenue"] for r in value["rows"]], ["-1234.50", "0.00"])
        selected.pop("duplicate_header_resolution_reference")
        with self.assertRaisesRegex(ValueError, "duplicate_headers"):
            f.b.normalize_results(raw, selected, binding)
        raw = b'{"results":[{"tables":[{"rows":[{"Team":"A","Revenue":12345678901234567890.123456789},{"Team":"B","Revenue":1e-8}]}]}]}'
        value = f.b.normalize_results(raw, profile(), {**binding, "attachment_sha256": f.b.sha(raw)})
        self.assertEqual([r["revenue"] for r in value["rows"]], ["12345678901234567890.123456789", "1E-8"])

    def test_currency_identity_and_order_are_independent_of_equal_values(self):
        self.observed()
        selected = profile()
        selected["columns"][1]["currency"] = {"code": "USD", "prefix": "", "suffix": "", "negative_parentheses": False}
        spec = self.comparison(selected)
        self.assertIn("context.currency.revenue", self.compare(spec)["gaps"])
        spec["source"]["context"]["currencies"] = {"revenue": "USD"}
        spec["target"]["context"]["currencies"] = {"amount": "USD"}
        self.assertEqual(self.compare(spec)["status"], "pass")
        spec["target"]["context"]["currencies"]["amount"] = "EUR"
        self.assertEqual(self.compare(spec)["status"], "inconclusive")
        spec["target"]["context"]["currencies"]["amount"] = "USD"
        self.put("evidence/target.json", [{"team": "B", "amount": None}, {"team": "A", "amount": 0}])
        spec["target"]["file"] = v.pin(self.root, "evidence/target.json")
        self.assertEqual(self.compare(spec)["status"], "pass")
        spec.update(row_order="exact", order_basis="reviewed-source-sort")
        result = self.compare(spec)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["order_mismatch"])

    def test_service_errors_and_missing_null_cells_cannot_normalize(self):
        for at in ("top", "result", "table"):
            for error_key in ("error", "errors"):
                value = json.loads(self.raw)
                container = value if at == "top" else value["results"][0]
                if at == "table":
                    container = container["tables"][0]
                container[error_key] = [{"code": "synthetic-service-error"}]
                raw = json.dumps(value).encode()
                with self.assertRaisesRegex(ValueError, "result_error"):
                    f.b.normalize_results(raw, profile(), {**self.binding, "capture_content_hash": "fixture",
                                                           "attachment_sha256": f.b.sha(raw)})
        value = json.loads(self.raw)
        del value["results"][0]["tables"][0]["rows"][1]["Revenue"]
        raw = json.dumps(value).encode()
        with self.assertRaisesRegex(ValueError, "json_rows_or_columns_required"):
            f.b.normalize_results(raw, profile(), {**self.binding, "capture_content_hash": "fixture",
                                                   "attachment_sha256": f.b.sha(raw)})


if __name__ == "__main__":
    unittest.main()
