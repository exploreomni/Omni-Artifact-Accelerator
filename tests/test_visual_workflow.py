import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/omni-artifact-accelerator/scripts"))
import visual_workflow as v  # noqa: E402 - standalone skill modules live outside site-packages


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


f = module("visual_fixtures", "tests/test_migration_sources.py")


class VisualWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / "run"
        v.ap.init(self.root, "Synthetic visual workflow", "migration", "dashboard")
        source = f.sigma_snapshot()
        self.put("inputs/original.json", source)
        inventory = f.t.translate((self.root / "inputs/original.json").read_bytes(), "sigma-agent", f.SIGMA)
        self.put("inputs/inventory.json", inventory)
        v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", "contracts/visual.json")
        self.req = v.load(self.root, "contracts/visual.json")
        self.req["route"] = "reuse_existing"
        self.req["route_reference"] = "synthetic-review://reuse"
        self.put("contracts/visual.json", self.req)
        self.put("evidence/candidate.json", {"kind": "synthetic_native_candidate", "tile": "one"})
        self.case = next(c["case_id"] for i in self.req["items"] for c in i["required_cases"] if c["lane"] == "numeric")

    def put(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def spec(self):
        self.put("inputs/source-rows.json", [{"team": "A", "revenue": 100}, {"team": "B", "revenue": None}])
        self.put("evidence/target-rows.json", [{"group": "B", "amount": None}, {"group": "A", "amount": 100.0}])
        ctx = {"filters": {}, "timezone": "UTC", "data_watermark": "synthetic-fixed-1",
               "population": "all_teams", "principal": "synthetic-viewer"}
        result = {"schema_version": 1, "kind": "analyst_numeric_comparison_spec", "case_id": self.case,
                  "requirements": v.pin(self.root, "contracts/visual.json"),
                  "candidate": v.pin(self.root, "evidence/candidate.json"),
                  "source": {"file": v.pin(self.root, "inputs/source-rows.json"), "format": "json",
                             "context": ctx, "complete": True, "completeness_reference": "synthetic-full-file"},
                  "target": {"file": v.pin(self.root, "evidence/target-rows.json"), "format": "json",
                             "context": copy.deepcopy(ctx), "complete": True, "completeness_reference": "synthetic-full-file"},
                  "persona_equivalence_reference": "synthetic-persona-mapping", "keys": ["team"],
                  "columns": [{"name": "team", "source": "team", "target": "group", "type": "string"},
                              {"name": "revenue", "source": "revenue", "target": "amount", "type": "number", "nullable": True}]}
        self.put("contracts/compare.json", result)
        return result

    def run_compare(self, spec=None):
        if spec is not None:
            self.put("contracts/compare.json", spec)
        v.compare(self.root, "contracts/compare.json", "evidence/comparison.json")
        return v.load(self.root, "evidence/comparison.json")

    def test_requirements_retain_every_asset_and_brand_question(self):
        _, req = v.requirements(self.root, "contracts/visual.json")
        inv = v.load(self.root, "inputs/inventory.json")
        self.assertEqual(len(req["items"]), len(inv["assets"]))
        self.assertEqual(req["brand"]["open_questions"], ["What is the company website URL?"])
        self.assertTrue(any(c["case_id"].endswith("/access/denied") for i in req["items"] for c in i["required_cases"]))

    def test_website_alone_keeps_logo_choice_open(self):
        v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", "contracts/branded.json",
                  website="https://example.com")
        brand = v.load(self.root, "contracts/branded.json")["brand"]
        self.assertEqual(brand["company_website_url"], "https://example.com")
        self.assertTrue(any("logo" in q for q in brand["open_questions"]))
        self.assertEqual(brand["requirements"][0]["disposition"], "unresolved")

    def test_saved_official_site_authorization_is_reused_without_reasking(self):
        intent = v.ap.intent_helper().starter(["dashboard"], "requested", "https://example.com")
        intent["logo_sourcing"] = {"mode": "official_site", "authorization_ref": "customer-answer-1",
                                  "source": "https://example.com"}
        self.put("contracts/design-intent.json", intent)
        v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", "contracts/reused.json")
        brand = v.load(self.root, "contracts/reused.json")["brand"]
        self.assertEqual(brand["company_website_url"], "https://example.com")
        self.assertEqual(brand["open_questions"], [])
        self.assertTrue(any(f["code"] == "logo_asset_pending" for f in brand["findings"]))
        self.assertEqual(brand["logo_sourcing"]["authorization_ref"], "customer-answer-1")

    def test_explicit_no_branding_skips_asset_questions(self):
        self.put("contracts/design-intent.json", v.ap.intent_helper().starter(["dashboard"], "none"))
        v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", "contracts/plain.json")
        brand = v.load(self.root, "contracts/plain.json")["brand"]
        self.assertEqual(brand["requirements"], [])
        self.assertEqual(brand["open_questions"], [])

    def test_omitted_asset_and_removed_required_case_reject(self):
        for mutate in (lambda r: r["items"].pop(), lambda r: r["items"][0]["required_cases"].pop(),
                       lambda r: r["items"][0]["source_facets"].clear()):
            value = copy.deepcopy(self.req)
            mutate(value)
            self.put("contracts/visual.json", value)
            with self.assertRaises(ValueError):
                v.requirements(self.root, "contracts/visual.json")

    def test_original_drift_and_input_hash_mismatch_reject(self):
        self.put("inputs/original.json", {"different": True})
        with self.assertRaises(ValueError):
            v.requirements(self.root, "contracts/visual.json")
        with self.assertRaises(ValueError):
            v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", "contracts/new.json")

    def test_edited_projection_cannot_hide_original_visuals(self):
        value = v.load(self.root, "inputs/inventory.json")
        value["assets"] = [a for a in value["assets"] if a["kind"] != "visual"]
        self.put("inputs/inventory.json", value)
        with self.assertRaisesRegex(ValueError, "projection_changed"):
            v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", "contracts/new.json")

    def test_keyed_compare_reorders_and_preserves_null(self):
        self.spec()
        report = self.run_compare()
        self.assertEqual(report['arithmetic_status'], 'pass')
        self.assertEqual(report['status'], 'inconclusive')
        self.assertIn('source.sigma_case_capture_required', report['gaps'])
        self.assertEqual(report["native_validation"], "not_established")
        self.assertEqual((self.root / "evidence/comparison.json").stat().st_mode & 0o777, 0o600)

    def test_wrong_value_fails_and_unknown_population_is_inconclusive(self):
        spec = self.spec()
        self.put("evidence/target-rows.json", [{"group": "A", "amount": 90}])
        spec["target"]["file"] = v.pin(self.root, "evidence/target-rows.json")
        report = self.run_compare(spec)
        self.assertEqual(report['arithmetic_status'], 'fail')
        self.assertEqual(report['status'], 'inconclusive')
        self.assertEqual(report["missing_keys"], 1)
        self.assertEqual(report["mismatch_count"], 1)
        (self.root / "evidence/comparison.json").unlink()
        spec["target"]["context"]["data_watermark"] = "newer"
        report = self.run_compare(spec)
        self.assertEqual(report["status"], "inconclusive")

    def test_duplicate_keys_reject(self):
        spec = self.spec()
        self.put("evidence/target-rows.json", [{"group": "A", "amount": 100}] * 2)
        spec["target"]["file"] = v.pin(self.root, "evidence/target-rows.json")
        with self.assertRaises(ValueError):
            self.run_compare(spec)

    def test_tolerance_needs_basis(self):
        spec = self.spec()
        spec["columns"][1]["absolute_tolerance"] = 1
        with self.assertRaises(ValueError):
            self.run_compare(spec)

    def test_missing_completeness_never_passes(self):
        spec = self.spec()
        spec["source"]["complete"] = False
        self.assertEqual(self.run_compare(spec)["status"], "inconclusive")

    def test_csv_empty_requires_explicit_null_mapping(self):
        spec = self.spec()
        (self.root / "evidence/results.csv").write_text("group,amount\nA,100\nB,\n")
        spec["target"].update(file=v.pin(self.root, "evidence/results.csv"), format="csv")
        with self.assertRaises(ValueError):
            self.run_compare(spec)
        spec["columns"][1]["empty_is_null"] = True
        report = self.run_compare(spec)
        self.assertEqual(report['arithmetic_status'], 'pass')
        self.assertEqual(report['status'], 'inconclusive')

    def test_coverage_recomputes_comparison_and_preserves_partial(self):
        self.spec()
        self.run_compare()
        v.coverage(self.root, "contracts/visual.json", "evidence/candidate.json", ["evidence/comparison.json"], "evidence/coverage.json")
        report = v.load(self.root, "evidence/coverage.json")
        self.assertEqual(report["coverage_ledger"], "complete")
        self.assertEqual(report["evidence_coverage"], "partial")
        self.assertEqual(report["business_acceptance"], "not_recorded")
        changed = v.load(self.root, "evidence/comparison.json")
        changed["source_rows"] = 99
        self.put("evidence/comparison.json", changed)
        with self.assertRaisesRegex(ValueError, "comparison_changed"):
            v.coverage(self.root, "contracts/visual.json", "evidence/candidate.json", ["evidence/comparison.json"], "evidence/invalid.json")

    def test_candidate_change_invalidates_cases(self):
        self.spec()
        self.run_compare()
        self.put("evidence/candidate.json", {"tile": "changed"})
        with self.assertRaises(ValueError):
            v.coverage(self.root, "contracts/visual.json", "evidence/candidate.json", ["evidence/comparison.json"], "evidence/coverage.json")

    def test_deferred_remains_pending_exclusion_needs_decision(self):
        self.req["items"][0]["disposition"] = "defer"
        self.put("contracts/visual.json", self.req)
        with self.assertRaises(ValueError):
            v.requirements(self.root, "contracts/visual.json")
        self.req["items"][0]["scope_decision"] = {"reason": "Pilot later", "reference": "synthetic-decision"}
        self.put("contracts/visual.json", self.req)
        v.coverage(self.root, "contracts/visual.json", "evidence/candidate.json", [], "evidence/coverage.json")
        self.assertTrue(v.load(self.root, "evidence/coverage.json")["deferred_assets"])

    def test_safe_paths_and_existing_output(self):
        for dest in ("../escape.json", "contracts/visual.json"):
            with self.assertRaises((ValueError, OSError)):
                v.prepare(self.root, "inputs/original.json", "inputs/inventory.json", dest)
        (self.root / "inputs/link.json").symlink_to(self.root / "inputs/original.json")
        with self.assertRaises(ValueError):
            v.pin(self.root, "inputs/link.json")


if __name__ == "__main__":
    unittest.main()
