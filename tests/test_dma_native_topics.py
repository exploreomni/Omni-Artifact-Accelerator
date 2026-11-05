"""Native boundaries against first-party synthetic transports; no live API or authenticated claims."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


TESTS = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Existing fixture transports run only synthetic, first-party operations.
dashboard = load("test_omni_native", TESTS / "test_omni_native.py")
create = load("topic_create_fixture", TESTS / "test_native_create.py")
demo = load("topic_demo_fixture", TESTS / "test_native_demo.py")
draft = load("topic_draft_fixture", TESTS / "test_native_authoring.py")


def standalone_fixture():
    backend = TESTS.parent / "skills/omni-backend-handoff/scripts"
    load("migration", backend / "migration.py")
    return load("test_standalone", TESTS / "test_standalone.py")


def app_fixtures():
    # Load exact first-party fixtures for the two existing-document routes.
    standalone_fixture()
    for name in ("test_looker_visual_bridge", "test_looker_app", "test_hex_capture", "test_hex_app"):
        load(name, TESTS / (name + ".py"))
    return sys.modules["test_looker_app"], sys.modules["test_hex_app"]


class TopicProbe:
    """Isolate the native call boundary from the separate real A/B evidence tests."""
    def __init__(self):
        self.calls = []
        self.revision = "a" * 64
        self.fail_readback = False

    def guard(self, root, project, **call):
        self.calls.append(copy.deepcopy(call))
        if call.get("readback") and self.fail_readback:
            raise ValueError("synthetic topic readback drift")
        return {"policy": "selected-topic-v1", "queries_sha256": self.revision, "access_sha256": "b" * 64,
                "surface": call["surface"], "document_id": call["document_id"]}


class NativeTopics(unittest.TestCase):
    def fixture(self, cls):
        case = cls()
        self.addCleanup(case.doCleanups)
        case.setUp()
        return case

    def probe(self, p):
        probe = TopicProbe()
        original = p.routing_helper
        module = original("dma_topics")
        module.guard = probe.guard
        hook = patch.object(p, "routing_helper", side_effect=lambda name: module if name == "dma_topics" else original(name))
        hook.start()
        self.addCleanup(hook.stop)
        return probe

    def test_dashboard_complete_state_rechecked_before_intent_and_after_transport(self):
        case = self.fixture(standalone_fixture().StandaloneTests)
        case.configure()
        case.capture()
        p = dashboard.native.WORKFLOW.ap
        probe = self.probe(p)
        candidate = case.prepare()["candidate_sha256"]
        captured = probe.calls[-1]
        self.assertEqual(captured["surface"], "dashboard")
        self.assertEqual(captured["document_id"], case.target.document_id)
        self.assertEqual(set(captured["presentations"]["data"]), {"1", "2"})
        self.assertEqual(captured["presentations"]["data"]["2"], case.payload["queryPresentations"]["data"]["2"])
        self.assertEqual(captured["controls"], case.fake.state["controls"])
        self.assertEqual(captured["context"], {"base_url": case.target.base_url, "model_id": case.target.model_id,
            "branch_id": case.target.branch_id, "principal_id": case.target.principal_id, "workbook_model_id": "workbook-1"})
        probe.revision = "c" * 64
        with self.assertRaisesRegex(ValueError, "prepare a new candidate"):
            case.adapter.execute(candidate, "fixture")
        self.assertEqual(case.fake.patch_count, 0)
        self.assertFalse((case.root / ".omni-native/executions" / candidate / "intent.json").exists())
        probe.revision = "a" * 64
        probe.fail_readback = True
        self.assertEqual(case.adapter.execute(candidate, "fixture")["status"], "outcome_unknown")
        self.assertTrue(probe.calls[-1]["readback"])
        self.assertEqual(case.adapter.reconcile(candidate)["status"], "semantic_context_drift_or_unavailable")
        self.assertEqual(case.fake.patch_count, 1)

    def test_real_guard_rejects_unqualified_import_before_native_preparation(self):
        case = self.fixture(dashboard.NativeTests)
        p = dashboard.native.WORKFLOW.ap
        _, project = p.load_project(case.root)
        project["dma_topic_policy"] = "selected-topic-v1"
        p.write_json(case.root / "project.json", project, replace=True)
        with self.assertRaisesRegex(ValueError, "complete_current_access_and_analysis_first"):
            case.prepare()
        self.assertEqual(case.fake.patch_count, 0)
        self.assertFalse((case.root / ".omni-native/candidates").exists())

    def test_legacy_semantic_file_cannot_dispatch_a_bound_dashboard(self):
        case = self.fixture(dashboard.NativeTests)
        self.probe(dashboard.native.WORKFLOW.ap)
        with self.assertRaisesRegex(ValueError, "typed current workbook"):
            case.prepare()
        self.assertEqual(case.fake.patch_count, 0)

    def test_direct_catalog_has_no_exchange_but_real_draft_binding_requires_current_topic_and_original(self):
        policy = load("native_real_topic_fixture", TESTS / "test_dma_topic_policy.py")
        with tempfile.TemporaryDirectory() as folder:
            f = policy.Fixture(Path(folder).resolve() / "engagement")
            f.cycle.through("analysis")
            standalone = dashboard.native._standalone_module()
            backend = standalone.selected_backend(f.root, {"route": "reuse_existing"}, dashboard.native.WORKFLOW)
            self.assertEqual(backend["catalog"]["path"], "inputs/dma-catalog.json")
            self.assertNotIn("exchange_id", backend)
            with self.assertRaisesRegex(ValueError, "selected_backend_exchange_required"):
                standalone.selected_backend(f.root, {"route": "warehouse_first_refactor"}, dashboard.native.WORKFLOW)
            identity = {"keyScope": "user", "user": {"membershipId": f.ctx["principal_id"]},
                        "rolesByModel": {f.ctx["model_id"]: {"role": "QUERIER"}}}
            wb = "observed-workbook"
            models = policy.D.evidence(f.root, f.obs["models"], policy.P)
            models[wb] = {"id": wb, "modelKind": "WORKBOOK", "baseModelId": f.ctx["branch_id"]}
            snapshot = {"target": {**f.ctx, "document_id": f.row["document_id"]},
                "identity": identity, "draft_context": {"workbookModelId": wb},
                "models": models,
                "topics": {f.topic: f.views[f.topic]}}
            observation = {"target": {"base_url": f.ctx["base_url"], "document_id": f.row["document_id"]},
                "identity": identity, "draft": {"branch": {"id": f.ctx["branch_id"]}},
                "document": {"modelId": f.ctx["model_id"], "workbookModelId": wb,
                    "queryPresentations": {"order": ["1"], "data": {"1": copy.deepcopy(f.tile)}}}}
            html = '<section id="lab-volume"></section><script>display("lab-volume","1")</script>'
            (f.root / "deliverables/app.html").write_text(html)
            f.put("contracts/panels.json", {"kind": "dma_topic_panels", "html_path": "deliverables/app.html",
                "document_id": f.row["document_id"], "panels": [{"element_id": "lab-volume",
                    "consumer_id": f.row["consumer_id"], "query_key": "1", "script_fragment": 'display("lab-volume","1")'}]})
            policy.D.prepare_panels(f.root, policy.P, "contracts/panels.json")
            actual = draft.a.draft_topics(policy.P, f.root, observation, html=html, semantic_snapshot=snapshot, readback=True)
            self.assertEqual(actual["dma_topics"]["queries_sha256"], f.analysis["sha256"])
            wrong = observation["document"]["queryPresentations"]["data"]["1"]
            alternate = "instrument_samples"
            wrong["topicName"] = alternate
            wrong["query"].update(join_paths_from_topic_name=alternate, table=alternate + "_base",
                                  fields=[alternate + "_base.volume", "lab_group.name"])
            with self.assertRaisesRegex(ValueError, "differs_from_selected_topic_plan"):
                draft.a.draft_topics(policy.P, f.root, observation, html=html, semantic_snapshot=snapshot, readback=True)
            f.put("inputs/semantic-review.json", {**f.review, "unknowns": ["changed original"]})
            with self.assertRaises(ValueError):
                standalone.selected_backend(f.root, {"route": "reuse_existing"}, dashboard.native.WORKFLOW)

    def test_sql_and_non_topic_discriminators_conflict_with_semantic_queries(self):
        case = self.fixture(dashboard.NativeTests)
        for key, value, nested in (("queryType", "VIEW", False), ("query_type", "sql", False),
                ("is_sql", True, False), ("userEditedSQL", "select 1", True), ("raw_sql", "select 1", False)):
            payload = copy.deepcopy(case.payload)
            tile = payload["queryPresentations"]["data"]["2"]
            (tile["query"] if nested else tile)[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "separately qualified"):
                dashboard.native.expected_state(case.fake.state, payload, case.owned)
        tile = case.payload["queryPresentations"]["data"]["2"]
        tile.update(queryType="TOPIC", isSql=False)
        tile["query"]["userEditedSQL"] = ""
        dashboard.native.expected_state(case.fake.state, case.payload, case.owned)
        grammar = dashboard.native._standalone_module().query_fields
        query = {**tile["query"], "join_paths_from_topic_name": "orders"}
        self.assertEqual(grammar(query, topic="orders"), ["orders.revenue"])
        with self.assertRaisesRegex(ValueError, "topic_or_sql_conflict"):
            grammar(query, topic="another_topic")

    def test_existing_app_initial_put_and_patch_revalidate_exact_saved_workbook(self):
        existing, initial = app_fixtures()
        for cls, is_initial in ((existing.LookerAppTests, False), (initial.InitialAppTests, True)):
            with self.subTest(initial_put=is_initial):
                case = self.fixture(cls)
                existing.LookerAppTests.configure(case)
                if is_initial:
                    # Both routes can consume the retained first-party JSON capture.
                    case.config = initial.configure_initial_app(case.root)
                    case.adapter, case.fake = case.config["adapter"], case.config["fake"]
                case.capture()
                probe = self.probe(existing.app.w.ap)
                candidate = case.prepare()["candidate_sha256"]
                self.assertEqual(probe.calls[-1]["surface"], "app")
                self.assertEqual(probe.calls[-1]["presentations"], case.fake.state["queryPresentations"])
                self.assertEqual(probe.calls[-1]["snapshot"]["topics"], {"orders": case.fake.topic})
                frozen = case.adapter._candidate(candidate)
                self.assertEqual(probe.calls[-1]["app_html"], frozen["expected_app"]["html"])
                runtime = case.adapter.baseline(frozen["baseline"]["path"])["runtime_contract"]
                expected_controls = {key: {k: row[k] for k in ("component_id", "query_keys", "topic", "field_ids")}
                    for row in runtime["controls"] for key in row["source_asset_keys"]}
                self.assertEqual(probe.calls[-1]["controls"]["data"], expected_controls)
                execute = case.adapter.execute_initial if is_initial else case.adapter.execute
                reconcile = case.adapter.reconcile_initial if is_initial else case.adapter.reconcile
                probe.revision = "c" * 64
                with self.assertRaisesRegex(ValueError, "prepare a new candidate"):
                    execute(candidate, "fixture")
                self.assertEqual(case.fake.patch_count, 0)
                probe.revision = "a" * 64
                probe.fail_readback = True
                self.assertEqual(execute(candidate, "fixture")["status"], "outcome_unknown")
                self.assertTrue(probe.calls[-1]["readback"])
                self.assertEqual(probe.calls[-1]["app_html"], case.fake.app["html"])
                self.assertEqual(reconcile(candidate)["status"], "conflict_or_stale_evidence")
                self.assertEqual(case.fake.patch_count, 1)

    def test_release_create_readback_requires_identity_and_forwards_new_workbook_snapshot(self):
        case = self.fixture(create.NativeCreate)
        case.stage()
        probe = self.probe(create.P)
        with patch.object(create.a, "project_helper", return_value=create.P):
            prepared = case.prepare()
            self.assertEqual(probe.calls[-1]["app_html"], prepared["request"]["body"]["app"]["html"])
            self.assertEqual(probe.calls[-1]["context"], {"base_url": case.spec["base_url"],
                "model_id": case.spec["model_id"], "branch_id": None})
            captures = case.captures(prepared)
            with self.assertRaisesRegex(ValueError, "model-scoped"):
                case.verify(prepared, captures)
            identity = {"base_url": case.spec["base_url"], "method": "GET", "status": 200,
                "path": "/api/v1/whoami?modelId=" + case.spec["model_id"],
                "body": {"keyScope": "user", "user": {"membershipId": "member-1"},
                         "rolesByModel": {case.spec["model_id"]: {"role": "EDITOR"}}}}
            snapshot = {"topics": {}, "models": {}}
            result = create.a.verify_create(prepared, *captures, project=case.root, artifact=case.html_path,
                spec_artifact=case.spec_path, identity=identity, snapshot=snapshot)
            self.assertTrue(probe.calls[-1]["readback"])
            self.assertEqual(probe.calls[-1]["app_html"], captures[2]["body"]["html"])
            self.assertEqual(probe.calls[-1]["snapshot"], snapshot)
            self.assertEqual(probe.calls[-1]["context"]["workbook_model_id"], captures[1]["body"]["workbookModelId"])
            self.assertEqual(probe.calls[-1]["context"]["principal_id"], "member-1")
            self.assertEqual(result["dma_topics"], prepared["dma_topics"])
            self.assertFalse(result["publication_authorized"])

    def test_demo_cannot_substitute_for_the_query_or_readback_guard(self):
        case = self.fixture(demo.NativeDemo)
        case.stage()
        probe = self.probe(demo.P)
        with patch.object(demo.A, "project_helper", return_value=demo.P):
            prepared = case.prepare()
            self.assertEqual(probe.calls[-1]["context"]["principal_id"], case.demo["destination"]["principal"]["membership_id"])
            captures = case.captures(prepared)
            probe.fail_readback = True
            with self.assertRaisesRegex(ValueError, "topic readback drift"):
                case.verify(prepared, captures)
            self.assertEqual(probe.calls[-1]["presentations"], captures[1]["body"]["queryPresentations"])

    def test_existing_html_only_readback_requires_original_project_and_observed_user(self):
        case = self.fixture(draft.Authoring)
        p = draft.a.project_helper()
        probe = self.probe(p)
        with patch.object(draft.a, "project_helper", return_value=p):
            target, before = draft.fixture()
            with self.assertRaisesRegex(ValueError, "user identity"):
                case.prepare(target, before, before)
            target["key_scope"] = before["identity"]["keyScope"] = "user"
            before["identity"]["rolesByModel"] = {target["model_id"]: {"role": "EDITOR"}}
            prepared = case.prepare(target, before, before)
            after = copy.deepcopy(before)
            after["app"]["html"] = prepared["request"]["body"]["html"]
            with self.assertRaisesRegex(ValueError, "requires the original engagement"):
                draft.a.verify_app(prepared, before, after)
            probe.fail_readback = True
            with self.assertRaisesRegex(ValueError, "topic readback drift"):
                draft.a.verify_app(prepared, before, after, project=case.root)
