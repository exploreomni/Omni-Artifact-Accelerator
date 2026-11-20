"""Branch request preparation against offline Omni-shaped captures."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/omni-bi-engineer/scripts"


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


B = module("semantic_branch")
M = module("semantic_modeler")


class BranchPlanTest(unittest.TestCase):
    def setUp(self):
        self.ctx = {"base_url": "https://example.omniapp.co", "model_id": "s", "branch_id": "b",
                    "principal_id": "member", "workbook_model_id": None}
        branch = {"modelKind": "BRANCH", "id": "b", "baseModelId": "s", "connectionId": "c",
                  "createdByPrincipal": json.dumps({"type":"USER", "userId":"user", "membershipId":"member"}),
                  "userId": "user", "hasGit": False}
        models = {"s": {"id": "s", "modelKind": "SHARED", "connectionId": "c"}, "b": branch}
        raw = {"version": 1, "checksums": {"items.view":"opaque"}, "files":{"items.view":"fields"}}
        review = {k: B.inventory(raw) for k in ("shared", "branch")}
        baseline_ref = "sha256:" + B.digest(review)
        self.spec = {"schema_version":1, "baseline":{"model_id":"s", "branch_id":"b",
            "evidence_ref":baseline_ref, "topic_names":[], "user_attributes":[], "access_grants":[],
            "views":{"items":{"dimensions":["category"],"measures":[],"physical_binding":"existing.items"}}},
            "topic":{"name":"inventory","label":"Inventory","base_view":"items","fields":["items.category"]},
            "policy":{"review_ref":"access-review","access_filters":[],"required_access_grants":[]}}
        self.wrapper = {"kind":"omni_modeling_candidate", "context":self.ctx, "topic_name":"inventory",
                        "candidate":M.build_candidate(self.spec)}
        self.snapshot = {"kind":"omni_semantic_branch_snapshot","schema_version":1, "context":self.ctx,
            "identity":{"keyScope":"user", "user":{"id":"user","membershipId":"member"},
                        "rolesByModel":{"s":{"baseRole":"CONNECTION_ADMIN","permissions":["UPDATE", "USE_IDE"],
                                             "connectionId":"c"}}},
            "models":models,"git_enabled":False,"current":{"shared":copy.deepcopy(raw),"branch":copy.deepcopy(raw)},
            "reviewed_baseline":review,"candidate_sha256":self.wrapper["candidate"]["candidate_sha256"],
            "baseline_ref":baseline_ref}

    def prepare(self):
        return B.prepare_branch(self.wrapper, self.snapshot)

    def test_one_branch_only_request(self):
        plan = self.prepare()
        self.assertEqual(plan["status"], "prepared_for_review")
        self.assertFalse(plan["authorizes_target_write"])
        self.assertFalse(plan["native_verified"])
        self.assertEqual(plan["requests"], [{"model_id":"s", "operation":"models yaml-create",
            "body":{"branchId":"b", "mode":"combined", "fileName":"inventory.topic",
                    "yaml":self.wrapper["candidate"]["files"]["inventory.topic"]}}])

    def test_inventory_and_ancestry_drift(self):
        raw = self.snapshot["current"]["branch"]
        raw["version"] = 2
        with self.assertRaisesRegex(ValueError, "branch_changed_since_review"):
            self.prepare()
        self.snapshot["reviewed_baseline"]["branch"] = B.inventory(raw)
        with self.assertRaisesRegex(ValueError, "not_pinned_by_candidate"):
            self.prepare()
        self.snapshot["models"]["b"]["baseModelId"] = "unrelated"
        with self.assertRaisesRegex(ValueError, "wrong_branch_ancestry"):
            self.prepare()

    def test_export_filenames_need_an_explicit_native_mapping(self):
        for path in ("inventory.topic.yml", "inventory.topic.yaml", "topics/inventory.topic"):
            with self.subTest(path=path):
                self.spec["topic"]["path"] = path
                self.wrapper["candidate"] = M.build_candidate(self.spec)
                self.assertIn(path, self.wrapper["candidate"]["files"])
                self.snapshot["candidate_sha256"] = self.wrapper["candidate"]["candidate_sha256"]
                with self.assertRaisesRegex(ValueError, "native_filename_required_rebuild_as_topic"):
                    self.prepare()

    def test_unknown_attempt_never_yields_requests(self):
        self.snapshot["previous_attempt"] = {"reference":"attempt-1","context":self.ctx,
            "candidate_sha256":self.wrapper["candidate"]["candidate_sha256"], "file_name":"inventory.topic"}
        raw = self.snapshot["current"]["branch"]
        raw["version"] = 2
        raw["files"]["inventory.topic"] = "normalized server bytes"
        raw["checksums"]["inventory.topic"] = "new"
        self.assertEqual(self.prepare()["status"], "reconcile_prior_attempt")
        self.assertEqual(self.prepare()["requests"], [])

    def test_existing_topic_requires_exact_additive_revision(self):
        path = "inventory.topic"
        original = self.wrapper["candidate"]["files"][path]
        for current in self.snapshot["current"].values():
            current["files"][path] = original
            current["checksums"][path] = "opaque-before"
        reviewed = {k: B.inventory(v) for k, v in self.snapshot["current"].items()}
        reference = "sha256:" + B.digest(reviewed)
        self.spec["baseline"].update(topic_names=["inventory"], topic_files={path:original}, evidence_ref=reference)
        self.snapshot.update(baseline_ref=reference, reviewed_baseline=reviewed)
        self.spec["update"] = {"expected_sha256":M.sha(original), "review_ref":"approved-addition"}
        self.wrapper["candidate"] = M.build_candidate(self.spec)
        self.snapshot["candidate_sha256"] = self.wrapper["candidate"]["candidate_sha256"]
        self.assertEqual(self.prepare()["status"], "unchanged")
        self.spec["baseline"]["views"]["items"]["dimensions"].append("status")
        self.spec["topic"]["fields"].append("items.status")
        self.wrapper["candidate"] = M.build_candidate(self.spec)
        self.snapshot["candidate_sha256"] = self.wrapper["candidate"]["candidate_sha256"]
        self.assertEqual(self.prepare()["requests"][0]["body"]["yaml"], self.wrapper["candidate"]["files"][path])
        self.snapshot["current"]["branch"]["files"][path] += "# concurrent revision"
        with self.assertRaisesRegex(ValueError, "branch_changed_since_review"):
            self.prepare()

    def test_organization_scope_is_operator_only_and_needs_native_creator(self):
        self.snapshot["identity"].update(keyScope="organization", orgRole="ORG_ADMIN")
        with self.assertRaisesRegex(ValueError, "intended_branch_author_required"):
            self.prepare()
        self.snapshot["branch_author"] = {"kind":"omni_branch_authorization", "role":"user",
            "context":self.ctx, "topic_name":"inventory", "reference":"conversation-1","response_text":"Test this branch."}
        self.assertEqual(self.prepare()["author_scope"], "organization_branch_author")
        self.snapshot["models"]["b"]["userId"] = "someone-else"
        with self.assertRaisesRegex(ValueError, "intended_branch_author_required"):
            self.prepare()

    def test_git_setting_is_bound_to_observed_target(self):
        self.snapshot["git_enabled"] = True
        with self.assertRaisesRegex(ValueError, "git_configuration_required"):
            self.prepare()
        self.snapshot["models"]["b"]["hasGit"] = True
        with self.assertRaisesRegex(ValueError, "commit_message"):
            self.prepare()
        self.snapshot["commit_message"] = "Develop inventory Topic"
        self.assertEqual(self.prepare()["requests"][0]["body"]["commitMessage"], "Develop inventory Topic")


if __name__ == "__main__":
    unittest.main()
