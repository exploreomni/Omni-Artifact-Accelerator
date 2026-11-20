"""Synthetic, offline semantic comparison and access evidence cases."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills/omni-bi-engineer/scripts/semantic_verification.py"
IMPORT = importlib.util.spec_from_file_location("semantic_verification", MODULE)
V = importlib.util.module_from_spec(IMPORT)
IMPORT.loader.exec_module(V)
TOPIC = "orders"
CANDIDATE = "a" * 64
ARTIFACT = "b" * 64


def result(rows):
    return {"status": "complete", "truncated": False, "columns": ["group", "n"], "rows": rows}


def user(principal):
    return {"keyScope": "user", "user": {"membershipId": principal, "isOrgAdmin": False}}


class Case:
    def __init__(self, branch="dev"):
        model = branch or "model"
        self.context = {"base_url": "https://example.omni.test", "model_id": "model", "branch_id": branch,
                        "principal_id": "analyst"}
        self.scope = {k: v for k, v in self.context.items() if k != "principal_id"}
        self.scope.update(topic_name=TOPIC, candidate_sha256=CANDIDATE)
        self.spec = {"schema_version": 1, "queries": [], "access": []}
        self.originals = {}
        self.refs = {}
        response = {"success": True, "topic": {"name": TOPIC, "views": [{"name": "orders", "measures": [{"fully_qualified_name": "orders.n"}]}]}}
        bases = {"model": {"id": "model", "modelKind": "SHARED", "connectionId": "conn"}}
        if branch:
            bases[branch] = {"id": branch, "modelKind": "BRANCH", "baseModelId": "model"}
        policy = {"topic_response_sha256": V.fingerprint(response), "comparisons": [], "personas": {},
                  "surfaces": {"document": {"resources": ["doc"]}, "control": {"resources": ["region"]}}}
        for level, rows in [("total", [{"group": "all", "n": 3}]),
                            ("slice", [{"group": "A", "n": 1}, {"group": "B", "n": 2}])]:
            query = {"fields": ["n"] if level == "total" else ["group", "n"]}
            policy["comparisons"].append({"id": level, "level": level, "query": query, "expected": result(rows)})
            self.spec["queries"].append(self.pin(level, "query", {"id": level, "identity": user("analyst"),
                "query_id": "run-" + level, "query": query, "result": result(list(reversed(rows)))}))
        self.spec["identity"] = self.pin("identity", "identity", {"identity": user("analyst"), "models": bases})
        self.spec["readback"] = self.pin("readback", "readback", {"identity": user("analyst"), "model_id": model,
                                                                  "response": response})
        self.spec["validation"] = self.pin("validation", "validation", {"identity": user("analyst"), "model_id": model,
                                            "status": "complete", "errors": [], "run_id": "validate-1"})
        for role, groups in [("allowed", ["A", "B"]), ("restricted", ["A"]), ("default", [])]:
            principal = role + "-user"
            plan = {"principal_id": principal, "attributes": {} if role == "default" else {"role": role}, "probes": []}
            actual = {"id": role, "identity": user(principal), "attributes": plan["attributes"], "probes": []}
            for kind, resource, op in (("rights", TOPIC, "query"), ("rows", TOPIC, "query-rows"),
                                       ("document", "doc", "open"), ("control", "region", "choices")):
                req = {"resource": resource, "operation": op}
                if kind == "control":
                    req["document_id"] = "doc"
                exp = "allowed" if kind == "rights" else "visible"
                body = {"http_status": 200, "resource": resource}
                if kind in ("rows", "control"):
                    exp = result([{"group": k, "n": 1} for k in groups])
                    body["result"] = exp
                if role == "default" and kind in ("document", "control"):
                    exp, body = "denied", {"http_status": 403}
                plan["probes"].append({"id": kind, "kind": kind, "request": req, "expected": exp})
                obs = {"id": kind, "request": req, "operation_id": role + "-" + kind, "response": body}
                if kind in ("document", "control"):
                    obs.update(document_id="doc", artifact_sha256=ARTIFACT)
                actual["probes"].append(obs)
            policy["personas"][role] = plan
            self.spec["access"].append(self.pin(role, "access", actual))
        self.spec["policy"] = self.pin("policy", "policy", policy)

    def pin(self, key, kind, obj):
        record = {"kind": kind, "scope": self.scope, "observed_at": "2026-10-01T16:00:00Z",
                  "source_ref": "source/" + key, **obj}
        path = "evidence/" + key + ".json"
        data = V.canonical(record)
        self.originals[path] = data
        self.refs[key] = {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
        return self.refs[key]

    def edit(self, key, update):
        ref = self.refs[key]
        record = json.loads(self.originals[ref["path"]])
        update(record)
        data = V.canonical(record)
        self.originals[ref["path"]] = data
        ref["sha256"] = hashlib.sha256(data).hexdigest()

    def verify(self, **overrides):
        args = {"context": self.context, "topic_name": TOPIC, "candidate_sha256": CANDIDATE,
                "originals": self.originals, "artifact_sha256": ARTIFACT, "document_ids": ["doc"]}
        return V.verify_topic(self.spec, **{**args, **overrides})


class SemanticVerificationTests(unittest.TestCase):
    def test_complete_candidate_and_shared_reuse(self):
        for branch in ("dev", None):
            case = Case(branch)
            result = case.verify()
            self.assertEqual(result["status"], "verified", result)
            self.assertTrue(result["model_ready"] and result["delivery_ready"])
            self.assertFalse(result["write_authorized"])
            self.assertEqual(result["documents"], ["doc"])
            self.assertEqual(result["topic_response_sha256"], json.loads(
                case.originals[case.refs["policy"]["path"]])["topic_response_sha256"])

    def test_no_originals_or_boolean_claims_never_pass(self):
        c = Case()
        self.assertEqual(c.verify(originals={})["status"], "pending")
        for key in ("identity", "validation", "readback"):
            c = Case()
            c.originals[c.refs[key]["path"]] = b'{"verified":true}'
            self.assertEqual(c.verify()["status"], "failed")
            c.refs[key]["sha256"] = hashlib.sha256(b'{"verified":true}').hexdigest()
            self.assertFalse(c.verify()["model_ready"])

    def test_scope_hash_identity_and_actual_model_validation(self):
        for key, change in [
            ("readback", lambda r: r["response"]["topic"].update(hiddenLabel="changed")),
            ("identity", lambda r: r["models"]["dev"].update(baseModelId="another")),
            ("validation", lambda r: r.update(errors=["unknown field"])),
            ("slice", lambda r: r["scope"].update(topic_name="other")),
            ("allowed", lambda r: r["identity"]["user"].update(membershipId="other")),
        ]:
            with self.subTest(key=key):
                c = Case()
                c.edit(key, change)
                self.assertEqual(c.verify()["status"], "failed")
                self.assertFalse(c.verify()["model_ready"])

    def test_partial_missing_or_elevated_persona_stays_pending(self):
        for key, change in [
            ("allowed", lambda r: r["identity"].update(keyScope="organization")),
            ("restricted", lambda r: r["identity"]["user"].update(isOrgAdmin=True)),
            ("slice", lambda r: r["result"].update(truncated=True)),
            ("default", lambda r: r.pop("attributes")),
        ]:
            c = Case()
            c.edit(key, change)
            self.assertEqual(c.verify()["status"], "pending")
            self.assertFalse(c.verify()["model_ready"])

    def test_successful_transport_cannot_mask_denied_topic_query(self):
        c = Case()
        c.edit("allowed", lambda r: r["probes"][0]["response"].update(success=False, error="denied"))
        self.assertFalse(c.verify()["model_ready"])

    def test_independent_values_and_numeric_types_must_agree(self):
        for change in [lambda r: r["result"]["rows"][0].update(n=True),
                       lambda r: r["result"]["rows"].append(r["result"]["rows"][0]),
                       lambda r: r.update(source_ref="source/policy"),
                       lambda r: r["query"].update(filters={"unexpected": 1})]:
            c = Case()
            c.edit("slice", change)
            self.assertEqual(c.verify()["status"], "failed")

    def test_restricted_rows_and_default_denial(self):
        c = Case()
        c.edit("restricted", lambda r: r["probes"][1]["response"]["result"]["rows"].append({"group":"B","n":1}))
        self.assertFalse(c.verify()["model_ready"])
        c = Case()
        c.edit("default", lambda r: r["probes"][2]["response"].update(http_status=200, resource="doc"))
        result = c.verify()
        self.assertTrue(result["model_ready"])
        self.assertFalse(result["delivery_ready"])
        self.assertEqual(result["status"], "failed")

    def test_stage_a_survives_missing_document_controls(self):
        c = Case()
        for role in V.PERSONAS:
            c.edit(role, lambda r: r.update(probes=r["probes"][:2]))
        report = c.verify(artifact_sha256=None, document_ids=None)
        self.assertTrue(report["model_ready"])
        self.assertFalse(report["delivery_ready"])
        self.assertEqual(report["status"], "pending")

    def test_wrong_revision_destination_or_unknown_control_never_certifies_delivery(self):
        for change in [lambda r: r["probes"][2].update(artifact_sha256="f"*64),
                       lambda r: r["probes"][3].update(document_id="other"),
                       lambda r: r["probes"][3]["response"].update(http_status=404)]:
            c = Case()
            c.edit("allowed", change)
            report = c.verify()
            self.assertTrue(report["model_ready"])
            self.assertFalse(report["delivery_ready"])
        self.assertFalse(Case().verify(document_ids=["another"])["delivery_ready"])

    def test_policy_can_precede_new_document_identity_without_reopening_model_decisions(self):
        c = Case()
        original_policy = json.loads(c.originals[c.refs["policy"]["path"]])
        def model_only(p):
            p.pop("surfaces")
            for row in p["personas"].values():
                row["probes"] = [probe for probe in row["probes"] if probe["kind"] in ("rows", "rights")]
        c.edit("policy", model_only)
        model_pin = c.refs["policy"]["sha256"]
        self.assertTrue(c.verify(artifact_sha256=None, document_ids=None)["model_ready"])
        supplement = {"policy_sha256": model_pin, "artifact_sha256": ARTIFACT, "surfaces": original_policy["surfaces"],
                      "personas": {key: val["probes"][2:] for key, val in original_policy["personas"].items()}}
        c.spec["delivery_policy"] = c.pin("delivery", "delivery_policy", supplement)
        self.assertTrue(c.verify()["delivery_ready"], c.verify())
        c.edit("delivery", lambda x: x.update(policy_sha256="0" * 64))
        self.assertFalse(c.verify()["delivery_ready"])
        self.assertTrue(c.verify()["model_ready"])

    def test_allowed_model_denial_cannot_supply_readiness(self):
        c = Case()
        def denied(p):
            p["personas"]["allowed"]["probes"][0]["expected"] = "denied"
            p["personas"]["allowed"]["probes"][1]["expected"] = "denied"
        c.edit("policy", denied)
        c.edit("allowed", lambda r: [x.update(response={"http_status":403}) for x in r["probes"][:2]])
        self.assertFalse(c.verify()["model_ready"])

    def test_uniform_public_policy_requires_documented_exception_and_actual_default(self):
        c = Case(None)
        def uniform(p):
            p["audience"] = {"mode": "uniform", "basis_ref": "public-policy/1", "reason": "uniform public role"}
            p["personas"]["restricted"] = {"not_applicable_reason": "No restricted audience in approved policy"}
        c.edit("policy", uniform)
        c.spec["access"].pop(1)
        self.assertTrue(c.verify()["model_ready"])
        c.spec["access"].pop()
        self.assertFalse(c.verify()["model_ready"])


if __name__ == "__main__":
    unittest.main()
