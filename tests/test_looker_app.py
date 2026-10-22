"""Actual Looker producer → governed native App contract, synthetic Omni only.

The retained JavaScript is an explicit test fixture, not an asserted Omni SDK.
The adapter must inspect and preserve a real starter's runtime in a tenant.
"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

import test_standalone as prior
import test_looker_visual_bridge as source

spec = importlib.util.spec_from_file_location("test_app_native", Path(__file__).resolve().parents[1] /
    "skills/omni-app-engineer/scripts/omni_app_native.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
v, m = app.w, prior.m

HTML = '''<!doctype html><title>Fixture</title><main><!--owned:start--><h1>Old summary</h1><!--owned:end--></main>
<aside>Unrelated content</aside><script>
const result = syntheticNativeRead("2");
syntheticNativeFilter("2", "orders.region");
syntheticNativeReset("2");
</script>'''


class AppOmni(prior.SemanticOmni):
    def __init__(self, root, document_id="app-sales", draft_id="app-sales-draft"):
        super().__init__(root)
        self.document_id, self.draft_id = document_id, draft_id
        for key in ("containers", "controls", "settings"):
            self.state.pop(key)
        self.state["draftOf"] = {"identifier": document_id}
        self.state["app"] = {"url": f"/api/v2/documents/{document_id}/draft/{draft_id}/app"}
        self.meta.update(identifier=draft_id, publishedIdentifier=document_id)
        self.app = {"html": HTML, "settings": {"allowDownloads": False, "allowExternalNavigation": False}}
        self.topic["topic"]["views"][0]["dimensions"].append({"field_name": "region", "view_name": "orders",
            "fully_qualified_name": "orders.region", "data_type": "STRING", "sql": "${TABLE}.region"})

    def runner(self, args, **kwargs):
        if len(args) > 2 and args[1] == "documents" and "--help" not in args:
            self.calls.append((args, kwargs))
            assert kwargs["shell"] is False
            assert args[2] in {"list-drafts", "v2-get-draft"}  # No dashboard patch / auto draft / publish.
            assert args[3] == self.document_id
            if args[2] == "v2-get-draft":
                assert args[4] == self.draft_id
            value = [self.meta] if args[2] == "list-drafts" else self.state
            return subprocess.CompletedProcess(args, 0, json.dumps(value).encode(), b"")
        return super().runner(args, **kwargs)

    def http(self, method, url, token, body, max_bytes):
        if "/whoami?" in url:
            return super().http(method, url, token, body, max_bytes)
        self.http_calls.append((method, url, body))
        assert url == "https://tenant.omniapp.co" + self.state["app"]["url"]
        assert token == "test-placeholder-only"
        if method == "GET":
            return 200, {}, json.dumps(self.app).encode()
        assert method == "PATCH"
        intents = list((self.root / ".omni-app-native/executions").glob("*/intent.json"))
        assert intents and all(json.loads(p.read_text())["status"] == "intent_persisted" for p in intents)
        self.patch_count += 1
        payload = copy.deepcopy(body)
        assert set(payload) == {"htmlEdits"}
        for edit in payload["htmlEdits"]:
            assert self.app["html"].count(edit["search"]) == 1
            self.app["html"] = self.app["html"].replace(edit["search"], edit["replace"], 1)
        if self.mode == "unrelated_change":
            self.state["queryPresentations"]["data"]["1"]["name"] = "Concurrent edit"
        if self.mode == "settings_change":
            self.app["settings"]["allowDownloads"] = True
        if self.mode == "semantic_drift":
            self.topic["topic"]["always_where_filters"] = {"orders.region": "East"}
        if self.mode == "timeout":
            raise TimeoutError("synthetic ambiguous transport")
        result = {"identifier": self.document_id, "draftIdentifier": self.draft_id,
                  "name": self.state["name"], "description": self.state["description"], "app": {"settings": self.app["settings"]}}
        if self.mode == "wrong_response":
            result["draftIdentifier"] = "other"
        return 200, {}, json.dumps(result).encode()


def configure_app(root, requirements_path="requirements.json", prefix="app", document_id="app-sales", draft_id="app-sales-draft"):
    """Existing project + requirements, usable by the real DMA journey too.

    Returns adapter/fake/spec paths; no source or project mutation. Query semantics
    are deliberately synthetic and all source obligations remain in requirements.
    """
    root = Path(root)
    req = v.load(root, requirements_path)
    fake = AppOmni(root, document_id, draft_id)
    target = app.n.TargetConfig("https://tenant.omniapp.co", "migration", document_id, draft_id,
                               "model-1", "member-1", "branch-1", "OAA_TEST_TOKEN")
    adapter = app.AppNativeAdapter(root, target, runner=fake.runner, http=fake.http)
    def write(name, value):
        path = f"{prefix}-{name}.json"
        (root / path).write_text(json.dumps(value))
        return path
    review = write("runtime-review", {"kind": "synthetic-independent-review", "limitation": "Not a vendor SDK or native runtime validation"})
    runtime = {"schema_version": 1, "kind": "analyst_app_runtime_contract", "review_reference": "synthetic-review",
        "evidence_paths": [review], "state_contract": {k: "independent-case-required" for k in ("loading", "empty", "error", "restricted", "stale", "reset")},
        "components": [{"component_id": "summary", "query_key": "2", "runtime_fragment": 'const result = syntheticNativeRead("2");',
                        "query_reference": 'syntheticNativeRead("2")'}], "controls": []}
    controls = app.s.control_source_keys(req, "app")
    if controls:
        runtime["controls"] = [{"source_asset_keys": sorted(controls), "component_id": "summary", "query_keys": ["2"],
            "topic": "orders", "field_ids": ["orders.region"], "runtime_fragment": 'syntheticNativeFilter("2", "orders.region");',
            "reset_fragment": 'syntheticNativeReset("2");', "contract_reference": "synthetic-control-equivalence-review"}]
    runtime_path = write("runtime", runtime)
    baseline = {"schema_version": 1, "kind": "analyst_existing_omni_app_baseline_spec", "review_ref": "synthetic-existing-model",
        "requirements_path": requirements_path, "runtime_path": runtime_path, "bindings": [{"query_key": "2", "topic": "orders",
            "source_asset_keys": sorted(app.query_assets(req)), "query": {"fields": ["orders.revenue"]}, "field_ids": ["orders.revenue"]}]}
    baseline_spec = write("baseline-spec", baseline)
    patch_path = write("patch", {"htmlEdits": [{"search": "<h1>Old summary</h1>", "replace": "<h1>Reviewed summary</h1>"}]})
    baseline_path = f"{prefix}-baseline.json"
    candidate_spec = write("candidate-spec", {"schema_version": 1, "kind": "analyst_native_app_spec", "review_ref": "synthetic-app-review",
        "requirements_path": requirements_path, "baseline_path": baseline_path, "patch_path": patch_path,
        "owned_regions": [{"start": "<!--owned:start-->", "end": "<!--owned:end-->"}]})
    return {"adapter": adapter, "fake": fake, "baseline_spec": baseline_spec, "baseline_path": baseline_path,
            "candidate_spec": candidate_spec, "runtime_path": runtime_path, "runtime_review_path": review, "patch_path": patch_path}


class LookerAppTests(unittest.TestCase):
    setUp = prior.StandaloneTests.setUp
    write = prior.StandaloneTests.write

    def configure(self, surface="app"):
        project = v.load(self.root, "project.json")
        project["surfaces"] = ["dashboard", "app"] if surface == "both" else [surface]
        self.write("project.json", project)
        result = source.capture_fixture(self.root / "inputs/looker-capture")
        self.original = str(Path(result["output"]).relative_to(self.root))
        self.write("inventory.json", result["inventory"])
        v.prepare(self.root, self.original, "inventory.json", "looker-requirements.json")
        req = v.load(self.root, "looker-requirements.json")
        req.update(route="reuse_existing", route_reference="synthetic-existing-model")
        self.write("requirements.json", req)
        self.config = configure_app(self.root)
        self.adapter, self.fake = self.config["adapter"], self.config["fake"]
        return self.config

    def capture(self):
        return self.adapter.capture_baseline(self.config["baseline_spec"], self.config["baseline_path"])

    def prepare(self):
        return self.adapter.prepare(self.config["candidate_spec"])

    def execute(self):
        self.capture()
        candidate = self.prepare()
        receipt = self.adapter.execute(candidate["candidate_sha256"], "synthetic-exact-authorization")
        self.assertEqual(receipt["status"], "readback_matched")
        return candidate, receipt

    def delivery(self):
        candidate, _ = self.execute()
        v.coverage(self.root, "requirements.json", candidate["path"], [], "coverage.json")
        spec = {"candidate_path": candidate["path"], "execution_receipt_path":
                f'.omni-app-native/executions/{candidate["candidate_sha256"]}/receipt.json', "coverage_path": "coverage.json"}
        return candidate, spec

    def test_actual_source_named_app_write_readback_and_standalone_return(self):
        self.configure()
        before = copy.deepcopy(self.fake.state)
        candidate, spec = self.delivery()
        proof = app.verify_delivery(self.root, spec)
        self.assertEqual(proof["surface"], "app")
        self.assertTrue(proof["gaps"])
        self.assertFalse(proof["native_verified"])
        self.assertEqual(before, self.fake.state)
        self.assertIn("Reviewed summary", self.fake.app["html"])
        req = v.load(self.root, "requirements.json")
        self.assertEqual(len(app.query_assets(req)), 6)  # four queries, two repeated placements.
        self.write("scope-spec.json", {"schema_version": 1, "kind": "analyst_migration_scope_spec", "scope_id": "app-only",
            "decision_reference": "synthetic-scope", "inventory_paths": ["inventory.json"], "units": [{"unit_id": "app",
                "inventory_path": "inventory.json", "asset_keys": [i["asset_key"] for i in req["items"]], "disposition": "migrate",
                "rationale": "Synthetic App journey", "frontend_asset_ids": ["app-sales"], "surfaces": ["app"]}]})
        m.freeze(self.root, "scope-spec.json", "scope.json")
        self.write("return-spec.json", {"schema_version": 1, "kind": "analyst_standalone_migration_return_spec", "surface": "app",
            "scope_sha256": v.load(self.root, "scope.json")["sha256"], "baseline_path": self.config["baseline_path"],
            "requirements_path": "requirements.json", "unresolved": [], **spec})
        result = m.prepare_return(self.root, "scope.json", "return-spec.json", "return.json")
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        self.assertEqual(m.verify_return(self.root, "return.json")["status"], "consistent")
        self.assertNotIn("dma_import", v.load(self.root, "project.json"))
        self.assertEqual(self.fake.patch_count, 1)
        (self.root / self.original).write_bytes((self.root / self.original).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            app.verify_delivery(self.root, spec)
        self.assertTrue(candidate["candidate_sha256"])

    def test_missing_query_placement_control_runtime_and_states_block_baseline(self):
        self.configure()
        baseline = v.load(self.root, self.config["baseline_spec"])
        original = v.load(self.root, self.config["runtime_path"])
        for mutate in (lambda x: x.update(controls=[]), lambda x: x.update(components=[]),
                       lambda x: x["state_contract"].pop("restricted"),
                       lambda x: x["components"][0].update(query_reference='syntheticNativeRead("999")'),
                       lambda x: x["controls"][0].update(field_ids=["orders.missing"]),
                       lambda x: x["controls"][0].update(query_keys=["1"])):
            runtime = copy.deepcopy(original)
            mutate(runtime)
            self.write(self.config["runtime_path"], runtime)
            with self.assertRaises(ValueError):
                self.capture()
        self.write(self.config["runtime_path"], original)
        baseline["bindings"][0]["source_asset_keys"].pop()
        self.write(self.config["baseline_spec"], baseline)
        with self.assertRaisesRegex(ValueError, "source_query_unbound"):
            self.capture()
        self.assertEqual(self.fake.patch_count, 0)

    def test_exact_owned_edits_cannot_change_settings_queries_or_unowned_content(self):
        self.configure()
        self.capture()
        for patch in ({"htmlEdits": [{"search": "Unrelated content", "replace": "changed"}]},
                      {"htmlEdits": [{"search": "Old summary", "replace": "new"}], "settings": {}},
                      {"htmlEdits": [{"search": "Old summary", "replace": "new", "replaceAll": True}]},
                      {"htmlEdits": [{"search": "Old summary", "replace": "<!--owned:end-->"}]}):
            self.write(self.config["patch_path"], patch)
            with self.assertRaises(ValueError):
                self.prepare()
        self.assertEqual(self.fake.patch_count, 0)

    def test_matching_wrong_control_fragment_cannot_claim_a_different_query(self):
        self.configure()
        runtime = v.load(self.root, self.config["runtime_path"])
        original = copy.deepcopy(runtime)
        for name, function in (("runtime_fragment", "syntheticNativeFilter"), ("reset_fragment", "syntheticNativeReset")):
            runtime = copy.deepcopy(original)
            old = runtime["controls"][0][name]
            wrong = old.replace(function + '("2"', function + '("1"')
            runtime["controls"][0][name] = wrong
            self.fake.app["html"] = HTML.replace(old, wrong)
            self.write(self.config["runtime_path"], runtime)
            with self.assertRaisesRegex(ValueError, "control_query_reference_missing"):
                self.capture()
        self.assertEqual(self.fake.patch_count, 0)

    def test_control_component_must_belong_to_its_selected_query_scope(self):
        self.configure()
        runtime = v.load(self.root, self.config["runtime_path"])
        runtime["components"].append({"component_id": "other", "query_key": "3", "runtime_fragment": 'syntheticNativeRead("3");',
                                       "query_reference": 'syntheticNativeRead("3")'})
        runtime["controls"][0]["component_id"] = "other"
        self.write(self.config["runtime_path"], runtime)
        html = HTML.replace("</script>", 'syntheticNativeRead("3");</script>')
        binding = v.load(self.root, self.config["baseline_spec"])["bindings"][0]
        with self.assertRaisesRegex(ValueError, "control_scope_mismatch"):
            self.adapter._runtime(self.config["runtime_path"], v.load(self.root, "requirements.json"),
                                  [binding, {**binding, "query_key": "3"}], html)

    def test_model_topic_branch_query_and_runtime_drift_block_write(self):
        self.configure()
        self.capture()
        candidate = self.prepare()
        originals = copy.deepcopy((self.fake.topic, self.fake.models, self.fake.meta, self.fake.state, self.fake.app))
        mutations = [lambda: self.fake.topic["topic"]["views"][0]["measures"][0].update(aggregate_type="AVG"),
            lambda: self.fake.models["workbook-1"].update(baseModelId="model-1"),
            lambda: self.fake.meta["branch"].update(id="other"),
            lambda: self.fake.state["queryPresentations"]["data"]["2"]["query"].update(limit=1),
            lambda: self.fake.app.update(html=self.fake.app["html"].replace('syntheticNativeFilter("2"', 'syntheticNativeFilter("1"'))]
        for mutate in mutations:
            self.fake.topic, self.fake.models, self.fake.meta, self.fake.state, self.fake.app = copy.deepcopy(originals)
            mutate()
            with self.assertRaises(ValueError):
                self.adapter.execute(candidate["candidate_sha256"], "authorized")
        self.assertEqual(self.fake.patch_count, 0)

    def test_ambiguous_write_is_not_replayed_and_reconciles_known_target(self):
        self.configure()
        self.capture()
        candidate = self.prepare()
        self.fake.mode = "timeout"
        receipt = self.adapter.execute(candidate["candidate_sha256"], "authorized")
        self.assertEqual(receipt["status"], "outcome_unknown")
        with self.assertRaisesRegex(ValueError, "never_replay"):
            self.adapter.execute(candidate["candidate_sha256"], "different-reference")
        self.assertEqual(self.adapter.reconcile(candidate["candidate_sha256"])["status"], "readback_matched")
        self.assertEqual(self.fake.patch_count, 1)

    def test_dashboard_and_app_exports_cannot_be_substituted(self):
        self.configure()
        self.fake.state.pop("app")
        with self.assertRaisesRegex(ValueError, "existing_app_only"):
            self.capture()
        with self.assertRaisesRegex(ValueError, "no qualified contract"):
            self.adapter.export_start("any", "any", "any", "any")

    def test_unrelated_readback_and_semantic_race_never_pass(self):
        for mode in ("unrelated_change", "settings_change", "semantic_drift", "wrong_response"):
            with self.subTest(mode=mode):
                self.configure() if not hasattr(self, "config") else None
                self.capture()
                candidate = self.prepare()
                self.fake.mode = mode
                result = self.adapter.execute(candidate["candidate_sha256"], "authorized")
                self.assertNotEqual(result["status"], "readback_matched")
                # Fresh independent temporary engagement for each write boundary.
                self.doCleanups()
                self.setUp()
                if hasattr(self, "config"):
                    del self.config

    def test_tampered_readback_and_coverage_fail_local_proof(self):
        self.configure()
        _, spec = self.delivery()
        receipt = v.load(self.root, spec["execution_receipt_path"])
        receipt["readback"]["app"]["html"] += "tamper"
        self.write(spec["execution_receipt_path"], receipt)
        with self.assertRaises(ValueError):
            app.verify_delivery(self.root, spec)

    def test_rehashed_contradictory_draft_context_cannot_pass_local_proof(self):
        self.configure()
        _, spec = self.delivery()
        original = v.load(self.root, spec["execution_receipt_path"])
        for change in ({"publishedIdentifier": "different-document"}, {"draftOutOfDate": True},
                       {"branch": {"id": "other-branch"}}, {"identifier": "other-draft"},
                       {"workbookModelId": "other-workbook"}):
            receipt = copy.deepcopy(original)
            receipt["readback"]["draft_context"].update(change)
            readback = receipt["readback"]
            readback["snapshot_sha256"] = app.n.digest({k: val for k, val in readback.items() if k != "snapshot_sha256"})
            self.write(spec["execution_receipt_path"], receipt)
            with self.assertRaises(ValueError):
                app.verify_delivery(self.root, spec)

    def test_actual_standalone_both_aggregate_requires_separate_surface_proofs(self):
        import test_looker_native as dashboards
        self.configure(surface="both")
        _, app_proof = self.delivery()
        config = dashboards.configure_dashboard(self.root)
        adapter = config["adapter"]
        adapter.capture_baseline(config["baseline_spec"], config["baseline_path"])
        candidate = adapter.prepare(config["payload_path"], ["requirements.json", self.original], config["baseline_path"],
                                    config["ownership_path"], "synthetic-dashboard-review")
        self.assertEqual(adapter.execute(candidate["candidate_sha256"], "synthetic-dashboard-authorization")["status"], "readback_matched")
        v.coverage(self.root, "requirements.json", candidate["path"], [], "dashboard-coverage.json")
        dashboard_proof = {"candidate_path": candidate["path"], "coverage_path": "dashboard-coverage.json",
            "execution_receipt_path": f'.omni-native/executions/{candidate["candidate_sha256"]}/receipt.json'}
        req = v.load(self.root, "requirements.json")
        self.write("scope-spec.json", {"schema_version": 1, "kind": "analyst_migration_scope_spec", "scope_id": "both",
            "decision_reference": "synthetic-both", "inventory_paths": ["inventory.json"], "units": [{"unit_id": "summary",
                "inventory_path": "inventory.json", "asset_keys": [i["asset_key"] for i in req["items"]],
                "disposition": "migrate", "rationale": "Synthetic two-surface journey", "frontend_asset_ids": ["summary"],
                "surfaces": ["dashboard", "app"]}]})
        m.freeze(self.root, "scope-spec.json", "scope.json")
        spec = {"schema_version": 1, "kind": "analyst_standalone_migration_return_spec", "surface": "both",
            "scope_sha256": v.load(self.root, "scope.json")["sha256"], "surface_deliveries": {"app": app_proof}, "unresolved": []}
        self.write("both-spec.json", spec)
        partial = m.prepare_return(self.root, "scope.json", "both-spec.json", "partial-return.json")
        self.assertIn({"code": "missing_surface_delivery", "surface": "dashboard"}, partial["report"]["gaps"])
        spec["surface_deliveries"]["dashboard"] = dashboard_proof
        self.write("both-spec.json", spec)
        result = m.prepare_return(self.root, "scope.json", "both-spec.json", "both-return.json")
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        self.assertFalse(any(g["code"] == "missing_surface_delivery" for g in result["report"]["gaps"]))
        receipt = v.load(self.root, "both-return.json")
        self.assertEqual(set(receipt["surface_deliveries"]), {"dashboard", "app"})
        self.assertFalse(receipt["migration_accepted"])
        self.assertNotIn("dma_import", v.load(self.root, "project.json"))
        self.assertEqual(m.verify_return(self.root, "both-return.json")["status"], "consistent")
        spec["surface_deliveries"]["app"] = dashboard_proof
        self.write("both-spec.json", spec)
        with self.assertRaises(ValueError):
            m.prepare_return(self.root, "scope.json", "both-spec.json", "swapped-return.json")
        self.assertEqual(self.fake.patch_count, 1)
        self.assertEqual(config["fake"].patch_count, 1)


if __name__ == "__main__":
    unittest.main()
