"""The actual stage gate rechecks retained standalone delivery evidence on release."""
import importlib.util
from pathlib import Path
import unittest


FIXTURE = importlib.util.spec_from_file_location("semantic_release_fixture", Path(__file__).with_name("test_semantic_lane.py"))
LANE = importlib.util.module_from_spec(FIXTURE)
FIXTURE.loader.exec_module(LANE)
P = LANE.P


class SemanticReleaseTests(unittest.TestCase):
    def test_frozen_document_requires_current_persona_observation(self):
        fixture = LANE.SemanticLane()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.root
        spec, _, previous_queries, tile, cycle = fixture.bind(reuse=False)

        # The single query tile has no controls. Before the new document exists,
        # Stage A reviews only model checks. Stage F will identify its actual document.
        checks = fixture.load(spec["checks"])
        policy = fixture.load(checks["policy"])
        delivery_probes = {}
        for role, persona in policy["personas"].items():
            delivery_probes[role] = [p for p in persona["probes"] if p["kind"] == "document"]
            persona["probes"] = [p for p in persona["probes"] if p["kind"] in ("rights", "rows")]
        policy.pop("surfaces")
        checks["policy"] = fixture.put("evidence/release-model-policy.json", policy)
        spec["checks"] = fixture.put("contracts/release-model-checks.json", checks)
        access = fixture.run_request("access", spec, key="release-access")
        plan = fixture.load(fixture.load(previous_queries)["source"])
        plan["access"] = access
        plan["consumers"][0]["expectation"] = checks["policy"]
        queries = fixture.run_request("queries", plan, key="release-queries")

        with P.trusted_stage_provider(cycle.host):
            P.stage_record(root, {"stage":"access", "source_scope":"orders", "user_identity":"analyst",
                                 "evidence":{"data":access["path"], "user_access":spec["observation"]["path"]}})
            previous_evidence = cycle.evidence
            cycle.evidence = lambda name, content=None: (queries["path"] if name == "analysis-queries"
                                                        else previous_evidence(name, content))
            for stage in ("analysis", "narrative", "brief", "options"):
                cycle.stage(stage)
            binding = P.stage_status(root)["choice_bindings"]["option-1"]
            cycle.host.grants[(P.canonical(binding), "selected-one")] = "fixture-user"
            P.stage_record(root, {"stage":"choice", "option_id":"option-1", "receipt_ref":"selected-one"})
            cycle.stage("design")
            document = fixture.put("evidence/frozen-dashboard.json", {"id":"doc", "tiles":{"1":tile}})
            P.stage_record(root, {"stage":"candidate", "iteration_id":"one", "builders":["builder"],
                                 "artifact":document["path"]})
            artifact = P.stage_status(root)["candidate_sha256"]
            self.assertFalse(P.stage_status(root)["release_ready"])

            f_policy = {**{k:policy[k] for k in ("scope", "observed_at")}, "kind":"delivery_policy",
                        "source_ref":"review/frozen-doc", "policy_sha256":checks["policy"]["sha256"],
                        "artifact_sha256":artifact, "surfaces":{"document":{"resources":["doc"]},
                        "control":{"resources":[], "not_applicable_reason":"This dashboard has a single unfiltered tile."}},
                        "personas":delivery_probes}
            f_checks = {**checks, "delivery_policy":fixture.put("evidence/release-surface-policy.json", f_policy),
                        "access":[]}
            for evidence in checks["access"]:
                observation = fixture.load(evidence)
                observation["probes"] = [p for p in observation["probes"] if p["id"] != "control"]
                for probe in observation["probes"]:
                    if probe["id"] == "document":
                        probe["artifact_sha256"] = artifact
                f_checks["access"].append(fixture.put("evidence/release-" + observation["id"] + ".json", observation))

            def delivery(checks_pin, key):
                return fixture.run_request("delivery", {"access":access, "queries":queries,
                    "artifact_sha256":artifact, "checks":checks_pin}, key=key)

            # A freshly pinned packet with the wrong effective member still cannot satisfy F.
            wrong = {**f_checks, "access":list(f_checks["access"])}
            member = fixture.load(wrong["access"][1])
            member["identity"]["user"]["membershipId"] = "different-user"
            wrong["access"][1] = fixture.put("evidence/wrong-delivery-member.json", member)
            with self.assertRaisesRegex(ValueError, "delivery_observations_pending"):
                delivery(fixture.put("contracts/wrong-delivery-checks.json", wrong), "wrong-delivery")
            path = "contracts/semantic-delivery-" + artifact + ".json"
            self.assertFalse((root / path).exists())

            stored = delivery(fixture.put("contracts/final-delivery-checks.json", f_checks), "final-delivery")
            self.assertEqual(stored["path"], path)
            cycle.reviews()
            self.assertTrue(P.stage_status(root)["release_ready"])

            # A previous successful delivery receipt cannot hide a changed original.
            observed_pin = f_checks["access"][1]
            observation = fixture.load(observed_pin)
            next(p for p in observation["probes"] if p["id"] == "document")["document_id"] = "another-doc"
            fixture.put(observed_pin["path"], observation)
            status = P.stage_status(root)
            self.assertFalse(status["release_ready"])
            self.assertIn("standalone_topic_delivery_access_pending", status["findings"])


if __name__ == "__main__":
    unittest.main()
