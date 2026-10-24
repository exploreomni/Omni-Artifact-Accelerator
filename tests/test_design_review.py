"""Synthetic, offline evidence coverage; passing receipts never certify design quality."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-artifact-accelerator/scripts/analyst_project.py"
spec = importlib.util.spec_from_file_location("project_design_tests", SCRIPT)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


class DesignReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "engagement"
        P.init(self.root, "Synthetic design review", "net-new", "app")
        # Existing pre-policy candidate: these tests exercise review evidence, not new-product gates.
        project = P.load_project(self.root)[1]
        project.update(mode='enhancement')
        project.pop('stage_gate_policy')
        P.write_json(self.root / 'project.json', project, replace=True)
        for path, raw in {"deliverables/app.html": b"<h1>Synthetic</h1>",
                          "contracts/resolved.json": b'{"task":"inspect an item"}',
                          "contracts/query.json": b'{"field":"synthetic.revenue"}',
                          "contracts/tokens.json": b'{"ink":"#111111"}',
                          "evidence/expected.json": b'{"synthetic_expected_total":42}',
                          "evidence/capture.png": PNG, "evidence/concept-a.png": PNG,
                          "evidence/concept-b.png": PNG,
                          "evidence/review.txt": b"Synthetic fixture only; no native or participant test."}.items():
            (self.root / path).write_bytes(raw)
        self.value = {"schema_version": 1, "kind": "analyst_design_review_spec", "id": "design-v1",
                      "scope": {"change": "material_new", "rationale": "New synthetic inspection task",
                                "surfaces": ["app"], "required_lanes": ["craft", "numerical"]},
                      "dependencies": [
                          {"id": "candidate", "kind": "candidate", "surface": "app", "path": "deliverables/app.html",
                           "target": {"surface": "app", "state": "local", "document_id": None, "draft_id": None}},
                          {"id": "design", "kind": "design", "surface": "app", "path": "contracts/resolved.json"},
                          {"id": "query", "kind": "query", "surface": "app", "path": "contracts/query.json"},
                          {"id": "expectation", "kind": "expectation", "surface": "app", "path": "evidence/expected.json"},
                          {"id": "brand", "kind": "brand", "surface": "app", "path": "contracts/tokens.json"}],
                      "concepts": [{"id": name, "surface": "app", "task": "Inspect an item", "composition": name,
                                    "tradeoffs": "Synthetic comparison", "render_paths": [f"evidence/concept-{name}.png"]}
                                   for name in ("a", "b")],
                      "selection": {"app": {"concept_id": "a", "status": "proposed", "rationale": "Working choice"}},
                      "captures": [{"id": "screen", "kind": "prototype", "candidate_id": "candidate",
                                    "candidate_sha256": self.sha("deliverables/app.html"), "path": "evidence/capture.png",
                                    "context": {"viewport": [1024, 768], "appearance": "light", "state": "ready"}}],
                      "cases": [], "deviations": [], "findings": []}
        for lane in ("craft", "numerical"):
            self.value["cases"].append({"id": lane, "surface": "app", "lane": lane, "candidate_id": "candidate",
                "status": "pass", "executed": True, "method": "designer_critique" if lane == "craft" else "source_query",
                "reviewer": "Synthetic reviewer", "reviewer_role": "app-designer", "independence": "independent",
                "observation": "Synthetic fixture report; no real execution claim", "target": copy.deepcopy(self.value["dependencies"][0]["target"]),
                "reviewed_dependencies": {d["id"]: self.sha(d["path"]) for d in self.value["dependencies"]},
                "capture_ids": ["screen"] if lane == "craft" else [], "evidence_paths": ["evidence/review.txt"]})

    def tearDown(self):
        self.temp.cleanup()

    def sha(self, path):
        return P.digest((self.root / path).read_bytes())

    def prepare_coverage(self):
        """Build valid new-format declarations for the existing focused review tests."""
        D = P.intent_helper()
        surfaces = P.load_project(self.root)[1]['surfaces']
        intent = D.starter(surfaces, 'none')
        lanes = self.value['scope']['required_lanes']
        self.value['scope'].setdefault('coverage', {'mode': 'whole_experience'})
        for selection in intent['selections']:
            surface = selection['surface']
            candidate = next(d for d in self.value['dependencies'] if d['kind'] == 'candidate' and d['surface'] == surface)
            design = next(d for d in self.value['dependencies'] if d['kind'] == 'design' and d['surface'] in {surface, 'shared'})
            design_value = json.loads((self.root / design['path']).read_text())
            design_value.update(brand_contract='contracts/tokens.json', destinations=[{'id': 'entry'}])
            (self.root / design['path']).write_text(json.dumps(design_value))
            selection.update(design_path=design['path'], brand_path='contracts/tokens.json',
                             candidate_path=candidate['path'], target=copy.deepcopy(candidate['target']))
            if not any(d['kind'] == 'brand' and d['surface'] in {surface, 'shared'} for d in self.value['dependencies']):
                self.value['dependencies'].append({'id': surface + '-brand', 'kind': 'brand',
                                                   'surface': surface, 'path': 'contracts/tokens.json'})
        rules = {lane: getattr(self, 'coverage_exclusions', {}).get(lane, {'status': 'required'}) for lane in lanes}
        intent['requirements'] = [{'id': 'review-scope', 'category': 'experience', 'purpose': 'Synthetic inspection',
            'required': True, 'surfaces': surfaces, 'origin': 'user', 'disposition': 'selected', 'value': {'mode': 'single'},
            'decision_ref': 'synthetic brief', 'asset_ids': [], 'delivery': {'destinations': ['entry']},
            'contexts': [{'id': 'default', 'appearance': 'light', 'state': 'ready', 'applicability': [
                {'kind': 'destination', 'id': 'entry', 'lanes': rules}]}]}]
        serial = getattr(self, 'intent_serial', 0) + 1
        self.intent_serial = serial
        path = self.root / f'contracts/fixture-intent-{serial}.json'
        path.write_text(json.dumps(intent))
        self.value['intent'] = D.select(self.root, path, f'contracts/fixture-selected-{serial}.json')['selection']
        for case in self.value['cases']:
            case.setdefault('expected', 'Inspect synthetic evidence')
            case.setdefault('obligation_ids', [f"review-scope/{case['surface']}/destination/entry/default/{case['lane']}"])
            case['reviewed_dependencies'].update({d['id']: self.sha(d['path']) for d in self.value['dependencies']
                                                if d['kind'] in {'design', 'brand'} and d['surface'] in {case['surface'], 'shared'}
                                                and (d['kind'] == 'brand' or d['id'] in case['reviewed_dependencies'])})
        for capture in self.value['captures']:
            capture.update(destination_id='entry', requirement_id='review-scope', requirement_context='default')
        for key in ('deviations', 'findings'):
            for row in self.value.get(key, []):
                row.setdefault('obligation_ids', [f"review-scope/{row['surface']}/destination/entry/default/craft"])

    def freeze(self, name="v1"):
        if 'intent' not in self.value or getattr(self, 'intent_serial', 0):
            self.prepare_coverage()
        path = self.root / f"contracts/spec-{name}.json"
        path.write_text(json.dumps(self.value))
        return P.design_freeze(self.root, path, f"contracts/review-{name}.json")["report"]

    def codes(self, report):
        return {g["code"] for g in report["gaps"]}

    def test_old_v1_readable_without_new_evidence(self):
        report = P.project_check(self.root)
        self.assertEqual(report["status"], "consistent")
        self.assertEqual(report["design_evidence"]["status"], "not_assessed")
        self.assertEqual(report["readiness"], "not_assessed")

    def test_complete_record_is_only_unauthenticated_evidence(self):
        report = self.freeze()
        self.assertEqual(report["coverage"], "complete")
        for key in ("assessment", "native_verification", "business_acceptance"):
            self.assertEqual(report[key], "not_assessed")
        self.assertFalse(report["publication_authorized"])
        self.assertTrue(all(not c["claim_authenticated"] for c in report["cases"]))

    def test_material_redesign_requires_actual_render_reference(self):
        self.value["scope"]["change"] = "material_redesign"
        self.value["concepts"][1]["render_paths"] = []
        report = self.freeze()
        self.assertIn("concept_render_missing", self.codes(report))
        self.assertEqual(report["coverage"], "incomplete")

    def test_direct_direction_does_not_require_a_manufactured_alternative(self):
        self.value["concepts"] = self.value["concepts"][:1]
        self.assertIn("rendered_alternatives_missing", self.codes(self.freeze("legacy")))
        self.value["selection"]["app"]["exploration"] = {
            "mode": "direct", "rationale": "The supplied design already resolves the composition."}
        self.assertEqual(self.freeze("direct")["coverage"], "complete")
        self.value["cases"][0]["executed"] = False
        self.assertEqual(self.freeze("unobserved")["coverage"], "incomplete")

    def test_comparison_choice_and_rationale_are_explicit(self):
        self.value["selection"]["app"]["exploration"] = {
            "mode": "compare", "rationale": "Compare disclosure for the same task."}
        self.value["concepts"] = self.value["concepts"][:1]
        self.assertIn("rendered_alternatives_missing", self.codes(self.freeze()))
        self.value["selection"]["app"]["exploration"] = {"mode": "direct", "rationale": "  "}
        with self.assertRaisesRegex(ValueError, "exploration rationale"):
            self.freeze("invalid")

    def test_text_claim_cannot_replace_image(self):
        self.value["concepts"][1]["render_paths"] = ["evidence/review.txt"]
        self.assertIn("concept_render_invalid_or_stale", self.codes(self.freeze()))

    def test_changed_capture_and_candidate_reopen_review(self):
        self.freeze()
        (self.root / "evidence/capture.png").write_bytes(PNG + b"changed")
        report = P.design_check(self.root)
        self.assertEqual(report["coverage"], "incomplete")
        self.assertEqual(report["cases"][0]["recorded_status"], "not_run")
        (self.root / "deliverables/app.html").write_text("new candidate")
        report = P.design_check(self.root)
        self.assertTrue(all(c["recorded_status"] == "not_run" for c in report["cases"]))
        self.assertEqual(P.project_check(self.root)["status"], "inconsistent")

    def test_brand_and_query_changes_reopen_distinct_lanes(self):
        self.freeze()
        (self.root / "contracts/tokens.json").write_text('{"ink":"#222"}')
        result = {c["id"]: c for c in P.design_check(self.root)["cases"]}
        self.assertEqual(result["craft"]["recorded_status"], "not_run")
        self.assertEqual(result["numerical"]["recorded_status"], "pass")
        (self.root / "contracts/query.json").write_text('{"field":"synthetic.cost"}')
        result = {c["id"]: c for c in P.design_check(self.root)["cases"]}
        self.assertEqual(result["numerical"]["recorded_status"], "not_run")

    def test_numeric_success_does_not_close_craft(self):
        self.value["cases"] = [self.value["cases"][1]]
        report = self.freeze()
        self.assertEqual(report["cases"][0]["recorded_status"], "pass")
        self.assertTrue(any(o['lane'] == 'craft' and o['status'] == 'missing'
                            for o in report['destination_coverage']['obligations']))

    def test_unexecuted_or_self_review_does_not_close_craft(self):
        self.value["cases"][0]["executed"] = False
        self.assertEqual(self.freeze()["cases"][0]["recorded_status"], "not_run")
        self.value["cases"][0]["executed"] = True
        self.value["cases"][0]["independence"] = "self_review"
        self.assertEqual(self.freeze("v2")["cases"][0]["recorded_status"], "not_run")

    def test_missing_case_pin_and_wrong_draft_are_not_review(self):
        self.value["dependencies"][0]["target"] = {"surface": "app", "state": "draft", "instance": "https://example.invalid", "document_id": "synthetic-doc", "draft_id": "draft-new"}
        for case in self.value["cases"]:
            case["target"] = dict(self.value["dependencies"][0]["target"], draft_id="draft-old")
        self.value["cases"][0]["reviewed_dependencies"].pop("design")
        report = self.freeze()
        self.assertTrue(all(c["recorded_status"] == "not_run" for c in report["cases"]))
        self.assertIn("target_identity_mismatch", report["cases"][0]["reasons"])

    def remote_candidate(self):
        target = {"surface": "app", "state": "draft", "instance": "https://example.invalid",
                  "document_id": "synthetic-doc", "draft_id": "draft-new"}
        self.value["dependencies"][0]["target"] = target
        for case in self.value["cases"]:
            case["target"] = copy.deepcopy(target)
        return target

    def test_remote_craft_requires_native_not_prototype_capture(self):
        self.remote_candidate()
        report = self.freeze()
        self.assertEqual(report["coverage"], "incomplete")
        self.assertIn("native_capture_identity_missing", report["cases"][0]["reasons"])
        self.value["captures"][0]["kind"] = "native"
        self.assertEqual(self.freeze("native")["coverage"], "complete")

    def test_whitespace_cannot_justify_applicability_or_review(self):
        self.value["cases"][1].update(status="not_applicable", executed=False, rationale=" \n\t")
        report = self.freeze()
        self.assertIn("applicability_unjustified", report["cases"][1]["reasons"])
        self.value["cases"][1]["rationale"] = "Synthetic layout-only scope; no metric or query changes."
        self.coverage_exclusions = {'numerical': {'status': 'not_applicable',
            'rationale': 'Synthetic layout-only scope', 'decision_ref': 'synthetic scope decision'}}
        self.assertEqual(self.freeze("justified")["coverage"], "complete")
        self.value["cases"][0]["observation"] = "   "
        self.assertIn("executed_review_evidence_missing", self.freeze("blank-review")["cases"][0]["reasons"])

    def test_malformed_reference_id_rejected_before_record_written(self):
        self.value["cases"][0]["candidate_id"] = ["candidate"]
        with self.assertRaisesRegex(ValueError, "candidate_id"):
            self.freeze()
        self.assertFalse((self.root / "contracts/review-v1.json").exists())

    def test_shared_remote_document_still_requires_surface_specific_capture(self):
        target = self.remote_candidate()
        project = json.loads((self.root / "project.json").read_text())
        project["surfaces"].append("dashboard")
        P.write_json(self.root / "project.json", project, replace=True)
        self.value["scope"].update(change="focused_edit", surfaces=["app", "dashboard"], required_lanes=["craft"])
        self.value["cases"] = self.value["cases"][:1]
        self.value["captures"][0]["kind"] = "native"
        (self.root / "deliverables/dashboard.json").write_text('{"title":"Synthetic dashboard"}')
        candidate = {"id": "dashboard", "kind": "candidate", "surface": "dashboard",
                     "path": "deliverables/dashboard.json", "target": dict(target, surface="dashboard")}
        design = {"id": "dashboard-design", "kind": "design", "surface": "dashboard", "path": "contracts/resolved.json"}
        self.value["dependencies"].extend([candidate, design])
        capture = dict(self.value["captures"][0], id="dashboard-screen", candidate_id="dashboard",
                       candidate_sha256=self.sha(candidate["path"]))
        self.value["captures"].append(capture)
        case = copy.deepcopy(self.value["cases"][0])
        case.update(id="dashboard-craft", surface="dashboard", candidate_id="dashboard",
                    target=candidate["target"], capture_ids=["dashboard-screen"],
                    reviewed_dependencies={d["id"]: self.sha(d["path"]) for d in (candidate, design)})
        self.value["cases"].append(case)
        self.assertEqual(self.freeze()["coverage"], "complete")
        case["capture_ids"] = ["screen"]
        report = self.freeze("wrong-surface")
        self.assertEqual(report["coverage"], "incomplete")
        self.assertIn("capture_invalid_or_stale", report["cases"][-1]["reasons"])

    def test_focused_edit_does_not_require_concepts(self):
        self.value["scope"]["change"] = "focused_edit"
        self.value["scope"]["required_lanes"] = ["craft"]
        self.value["cases"] = self.value["cases"][:1]
        self.value["concepts"] = []
        self.value.pop("selection")
        self.assertEqual(self.freeze()["coverage"], "complete")

    def test_unresolved_deviation_and_numeric_retest_cannot_close(self):
        deviation = {"id": "layout", "surface": "app", "candidate_id": "candidate",
                     "candidate_sha256": self.sha("deliverables/app.html"), "intended": "Side pane",
                     "actual": "Below list", "reason": "Constraint", "rationale": "Review adaptation",
                     "designer": "Synthetic reviewer", "designer_role": "app-designer",
                     "evidence_paths": ["evidence/review.txt"], "disposition": "unresolved"}
        self.value["deviations"] = [deviation]
        self.assertIn("unresolved_design_deviation", self.codes(self.freeze()))
        deviation.update(disposition="corrected", retest_case_id="numerical")
        self.assertIn("unresolved_design_deviation", self.codes(self.freeze("v2")))
        deviation["retest_case_id"] = "craft"
        self.assertEqual(self.freeze("v3")["coverage"], "complete")

    def test_faithful_migration_preserves_scope_and_no_forced_concepts(self):
        obj = json.loads((self.root / "project.json").read_text())
        obj["mode"] = "migration"
        P.write_json(self.root / "project.json", obj, replace=True)
        with self.assertRaisesRegex(ValueError, "scope_change_path"):
            self.freeze()
        self.value["scope"]["change"] = "faithful_migration"
        self.value["concepts"] = []
        self.assertIn("migration_source_obligations_missing", self.codes(self.freeze("v2")))
        self.value["scope"]["source_obligations_path"] = "evidence/review.txt"
        self.value["dependencies"].append({"id": "source", "kind": "source", "surface": "app", "path": "evidence/review.txt"})
        for case in self.value["cases"]:
            case["reviewed_dependencies"]["source"] = self.sha("evidence/review.txt")
        self.assertEqual(self.freeze("v3")["coverage"], "complete")

    def test_native_claim_cannot_be_local_simulation(self):
        case = copy.deepcopy(self.value["cases"][0])
        case.update(id="native", lane="native_behavior", method="local_test")
        self.value["cases"].append(case)
        self.value["scope"]["required_lanes"].append("native_behavior")
        report = self.freeze()
        self.assertIn("native_execution_missing", report["cases"][-1]["reasons"])

    def test_numerical_claim_requires_independent_expectation_input(self):
        self.value["dependencies"] = [d for d in self.value["dependencies"] if d["kind"] != "expectation"]
        report = self.freeze()
        self.assertEqual(report["cases"][1]["recorded_status"], "not_run")
        self.assertIn("query_and_independent_expectation_dependencies_missing", report["cases"][1]["reasons"])

    def test_material_finding_needs_same_lane_retest(self):
        self.value["findings"] = [{"id": "unreadable-chart", "surface": "app", "case_id": "craft",
                                   "problem": "Synthetic axis clips", "owner": "app-engineer", "impact": "material",
                                   "disposition": "corrected", "evidence_paths": ["evidence/review.txt"],
                                   "retest_case_id": "numerical"}]
        self.assertIn("open_design_finding", self.codes(self.freeze()))
        self.value["findings"][0]["retest_case_id"] = "craft"
        self.assertEqual(self.freeze("v2")["coverage"], "complete")

    def test_tampered_embedded_spec_cannot_drop_obligation(self):
        self.freeze()
        path = self.root / "contracts/review-v1.json"
        record = json.loads(path.read_text())
        record["spec"]["scope"]["required_lanes"].remove("numerical")
        record["content_sha256"] = P.digest(P.canonical({k: v for k, v in record.items() if k != "content_sha256"}))
        path.write_text(json.dumps(record))
        # An unselected historical record still verifies its pinned original specification.
        (self.root / "contracts/tampered.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "embedded spec"):
            P.design_check(self.root, "contracts/tampered.json")

    def test_cli_and_no_overwrite(self):
        self.freeze()
        result = subprocess.run([sys.executable, str(SCRIPT), "design-check", "--project", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["coverage"], "complete")
        with self.assertRaises(FileExistsError):
            self.freeze()
        (self.root / "evidence/capture.png").unlink()
        result = subprocess.run([sys.executable, str(SCRIPT), "design-check", "--project", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_symlink_evidence_rejected_before_record_written(self):
        (self.root / "evidence/capture.png").unlink()
        (self.root / "evidence/capture.png").symlink_to(self.root / "evidence/concept-a.png")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.freeze()
        self.assertFalse((self.root / "contracts/review-v1.json").exists())


if __name__ == "__main__":
    unittest.main()
