"""Independent source/state/precision expectations for Looker visual evidence."""
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

spec = importlib.util.spec_from_file_location("looker_workflow_fixture", ROOT / "tests/test_looker_visual_bridge.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def profile():
    return {"schema_version": 1, "format": "json_bi", "rows_pointer": "/rows", "cell_mode": "value_object",
        "row_encoding": "object", "headers": ["stock.site", "stock.available"], "subtotal_policy": "preserve", "columns": [
            {"ordinal": 0, "name": "site", "type": "string", "nullable": False, "null_tokens": []},
            {"ordinal": 1, "name": "available", "type": "number", "nullable": True, "null_tokens": [],
             "decimal_separator": ".", "group_separator": None, "percent": False}]}


class SimpleTransport(f.p.Transport):
    def __call__(self, *args):
        code, headers, raw = super().__call__(*args)
        if "application/json" in headers.get("content-type", "") and "/run/" not in args[1]:
            data = json.loads(raw)
            def simplify(value):
                if isinstance(value, dict):
                    if "model" in value and "fields" in value:
                        for key in ("total", "row_total", "pivots", "subtotals"):
                            value.pop(key, None)
                    for item in value.values():
                        simplify(item)
                elif isinstance(value, list):
                    for item in value:
                        simplify(item)
            simplify(data)
            raw = json.dumps(data).encode()
        return code, headers, raw


class LookerVisualWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / "project"
        v.ap.init(self.root, "Synthetic Looker workflow", "migration", "dashboard")
        transport = SimpleTransport()
        transport.result = b'{"metadata":{"fields":{}},"rows":[{"stock.site":{"value":"West"},"stock.available":{"value":12345678901234567890.123456789}},{"stock.site":{"value":"East"},"stock.available":{"value":null}},{"stock.site":{"value":"North"},"stock.available":{"value":0}}]}'
        result = f.c.capture(f.request(), self.root / "inputs/capture", token=f.p.TOKEN, transport=transport,
            allow_source_read=True, allow_source_query=True, now=f.p.NOW)
        self.capture = result["capture"]
        self.attachment = next(a for a in self.capture["attachments"] if a.get("binding_id"))
        self.raw = (self.root / "inputs/capture" / self.attachment["path"]).read_bytes()
        self.context = {"filters": {"Site": "West & North"}, "parameters": {}, "locale": "en-US", "timezone": "UTC",
            "principal": "user1", "data_watermark": "fixture-v1", "cache_reference": "fixture-cache-v1",
            "execution_mode": "production", "population": "fixture-three-sites"}
        self.put("evidence/candidate.json", {"kind": "synthetic_candidate"})
        self.refresh()

    def put(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def refresh(self):
        f.reseal(self.capture)
        self.put("inputs/capture/derivative.json", self.capture)
        self.put("inputs/inventory.json", f.t.translate((self.root / "inputs/capture/derivative.json").read_bytes(), "looker-capture"))
        (self.root / "contracts/visual.json").unlink(missing_ok=True)
        v.prepare(self.root, "inputs/capture/derivative.json", "inputs/inventory.json", "contracts/visual.json")
        self.req = v.load(self.root, "contracts/visual.json")
        self.req.update(route="reuse_existing", route_reference="synthetic-existing-topic-review")
        self.item = next(i for i in self.req["items"] if i["source_id"] == "tile-kpi")
        self.case = next(c for c in self.item["required_cases"] if c["case_id"].endswith("/numeric/default"))
        self.binding = {"element_id": "tile-kpi", "placement_id": None, "tab_id": None, "layout_id": None,
            "binding_id": "available", "state_sha256": f.b.sha(self.capture["request"]["state"]),
            "query_fingerprint": self.attachment["query_fingerprint"]}
        self.case.update(source_capture=v.pin(self.root, "inputs/capture/derivative.json"), source_binding=self.binding)
        self.put("contracts/visual.json", self.req)

    def observed(self):
        self.attachment["result_completeness"] = {"status": "complete", "reference": "independent-fixture-three-sites", "flags": []}
        for key in ("value_state_observation", "render_state_observation"):
            self.capture["source"][key] = {**self.context, **self.binding, "applied": True, "reference": "synthetic-observer",
                "effective_query_sha256": self.attachment["effective_query_sha256"], "query_state_reference": "independently-reviewed-filter-population"}
        self.refresh()

    def comparison(self):
        self.put("evidence/target.json", [{"site": "West", "amount": "12345678901234567890.123456789"},
                                        {"site": "East", "amount": None}, {"site": "North", "amount": 0}])
        binding = {k: self.binding[k] for k in ("element_id", "binding_id", "state_sha256", "query_fingerprint")}
        binding.update(capture_content_hash=self.capture["content_hash"], attachment_sha256=f.b.sha(self.raw))
        normalized = f.b.normalize_results(self.raw, profile(), binding)
        self.put("inputs/normalized.json", normalized)
        return {"schema_version": 1, "kind": "analyst_numeric_comparison_spec", "case_id": self.case["case_id"],
            "requirements": v.pin(self.root, "contracts/visual.json"), "candidate": v.pin(self.root, "evidence/candidate.json"),
            "source": {"file": v.pin(self.root, "inputs/normalized.json"), "raw_file": v.pin(self.root, "inputs/capture/" + self.attachment["path"]),
                       "format": "looker-normalized", "context": copy.deepcopy(self.context), "complete": True, "completeness_reference": "fixture-3-rows"},
            "target": {"file": v.pin(self.root, "evidence/target.json"), "format": "json", "context": copy.deepcopy(self.context),
                       "complete": True, "completeness_reference": "fixture-3-rows"},
            "persona_equivalence_reference": "synthetic-viewer-equivalence", "keys": ["site"], "columns": [
                {"name": "site", "type": "string", "source": "site", "target": "site"},
                {"name": "available", "type": "number", "source": "available", "target": "amount", "nullable": True}]}

    def compare(self, spec):
        self.put("contracts/comparison.json", spec)
        (self.root / "evidence/comparison.json").unlink(missing_ok=True)
        v.compare(self.root, "contracts/comparison.json", "evidence/comparison.json")
        return v.load(self.root, "evidence/comparison.json")

    def test_actual_producer_requirements_have_all_assets_without_content_numeric(self):
        _, req = v.requirements(self.root, "contracts/visual.json")
        self.assertEqual(len(req["items"]), len(f.EXPECTED))
        note = next(i for i in req["items"] if i["source_id"] == "tile-note")
        self.assertFalse(any(c["lane"] == "numeric" for c in note["required_cases"]))
        self.assertTrue(any(i["kind"] == "control" for i in req["items"]))
        self.assertTrue(all(any(c["lane"] == "numeric" for c in i["required_cases"]) for i in req["items"] if i["kind"] == "placement"))
        merged = next(i for i in req["items"] if i["source_id"] == "tile-merged")
        self.assertTrue(any(c["lane"] == "numeric" for c in merged["required_cases"]))

    def test_unknown_state_and_completeness_cannot_pass_equal_rows(self):
        result = self.compare(self.comparison())
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("source.value_state_observation.unverified", result["gaps"])
        self.assertIn("source.looker_result_completeness_unverified", result["gaps"])

    def test_precision_null_zero_order_and_local_status(self):
        self.observed()
        spec = self.comparison()
        self.assertEqual(self.compare(spec)["status"], "pass")
        target = v.load(self.root, "evidence/target.json")
        target[0]["amount"] = "12345678901234567890.123456790"
        target[1]["amount"] = 0
        target[2]["amount"] = None
        self.put("evidence/target.json", target)
        spec["target"]["file"] = v.pin(self.root, "evidence/target.json")
        result = self.compare(spec)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["mismatch_count"], 3)
        self.assertEqual(result["native_validation"], "not_established")
        spec = self.comparison()
        self.put("evidence/target.json", list(reversed(v.load(self.root, "evidence/target.json"))))
        spec["target"]["file"] = v.pin(self.root, "evidence/target.json")
        spec.update(row_order="exact", order_basis="reviewed-source-query-sort")
        self.assertEqual(self.compare(spec)["status"], "fail")

    def test_wrong_element_state_provider_and_changed_source_never_bind(self):
        for key, value in (("element_id", "tile-trend"), ("state_sha256", "0" * 64), ("query_fingerprint", "0" * 64), ("placement_id", "place1")):
            bad = copy.deepcopy(self.req)
            case = next(c for i in bad["items"] for c in i["required_cases"] if c["case_id"] == self.case["case_id"])
            case["source_binding"][key] = value
            self.put("contracts/visual.json", bad)
            with self.assertRaises(ValueError):
                v.requirements(self.root, "contracts/visual.json")
        self.put("contracts/visual.json", self.req)
        with patch.object(v, "capture_value", return_value={"schema_version": "sigma-visual-capture.v1"}):
            with self.assertRaisesRegex(ValueError, "provider_mismatch"):
                v.requirements(self.root, "contracts/visual.json")
        self.capture["source"]["identity"]["source_instance"] = "https://other.invalid"
        f.reseal(self.capture)
        self.put("inputs/capture/derivative.json", self.capture)
        with self.assertRaises(ValueError):
            v.requirements(self.root, "contracts/visual.json")

    def test_legacy_api_comparison_without_case_capture_is_inconclusive(self):
        value = f.dashboard()
        self.put("inputs/api.json", value)
        self.put("inputs/api-inventory.json", f.t.translate((self.root / "inputs/api.json").read_bytes(), "looker-api"))
        v.prepare(self.root, "inputs/api.json", "inputs/api-inventory.json", "contracts/api-visual.json")
        req = v.load(self.root, "contracts/api-visual.json")
        item = next(i for i in req["items"] if i["source_id"] == "tile-kpi")
        case = next(c for c in item["required_cases"] if c["lane"] == "numeric")
        spec = self.comparison()
        spec.update(requirements=v.pin(self.root, "contracts/api-visual.json"), case_id=case["case_id"])
        self.assertIn("source.looker_case_capture_required", self.compare(spec)["gaps"])

    def test_result_derivative_edit_replay_and_incomplete_evidence(self):
        self.observed()
        for status in (False, "unknown", "partial"):
            self.attachment["result_completeness"]["status"] = status
            self.refresh()
            self.assertEqual(self.compare(self.comparison())["status"], "inconclusive")
        self.observed()
        spec = self.comparison()
        normalized = v.load(self.root, "inputs/normalized.json")
        normalized["rows"][0]["available"] = "999"
        self.put("inputs/normalized.json", normalized)
        spec["source"]["file"] = v.pin(self.root, "inputs/normalized.json")
        with self.assertRaisesRegex(ValueError, "normalization_changed"):
            self.compare(spec)

    def test_string_encoded_json_bi_rows_profile_and_totals_rejection(self):
        raw = b'{"rows":["{\\"stock.site\\":{\\"value\\":\\"West\\"},\\"stock.available\\":{\\"value\\":12345678901234567890.123456789}}"]}'
        pr = {**profile(), "row_encoding": "json_string"}
        binding = {"capture_content_hash": "a" * 64, "element_id": "tile-kpi", "state_sha256": "b" * 64,
                   "binding_id": "available", "query_fingerprint": "c" * 64, "attachment_sha256": f.b.sha(raw)}
        value = f.b.normalize_results(raw, pr, binding)
        self.assertEqual(value["rows"][0]["available"], "12345678901234567890.123456789")
        for extra in ({"pivots": ["West"]}, {"totals_data": {"stock.available": 1}}, {"errors": [{"message": "failure"}]}):
            original = json.loads(self.raw)
            original.update(extra)
            changed = json.dumps(original).encode()
            with self.assertRaises(ValueError):
                f.b.normalize_results(changed, profile(), {**binding, "attachment_sha256": f.b.sha(changed)})

    def test_forced_production_cannot_be_relabelled_development_on_both_sides(self):
        self.context["execution_mode"] = "development"
        self.observed()
        result = self.compare(self.comparison())
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("source.looker_force_production_contradiction", result["gaps"])

    def test_totals_cache_mode_and_population_gaps_remain_visible(self):
        self.observed()
        self.capture["source"]["render_state_observation"]["execution_mode"] = "development"
        self.refresh()
        self.assertIn("source.render_state_observation.execution_mode", self.compare(self.comparison())["gaps"])
        self.observed()
        spec = self.comparison()
        spec["target"]["context"]["population"] = "one-site"
        self.assertIn("context.population", self.compare(spec)["gaps"])


if __name__ == "__main__":
    unittest.main()
