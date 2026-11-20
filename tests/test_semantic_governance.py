"""Review-only governance planning against a synthetic inspected branch."""
import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/omni-bi-engineer/scripts/semantic_governance.py"
IMPORT = importlib.util.spec_from_file_location("semantic_governance", SCRIPT)
G = importlib.util.module_from_spec(IMPORT)
IMPORT.loader.exec_module(G)
CONTEXT = {"base_url":"https://example.omni.test", "model_id":"shared", "branch_id":"dev", "principal_id":"operator"}
TOPIC = "orders"


def fixture():
    ctrl = {"id":"area-filter", "field":"orders.area", "consumer_ids":["sales", "volume"]}
    def attribute(val, other):
        return {"evidence_ref":"inspection/attributes", "complete":True, "value_mode":"exact",
                "missing_value_behavior":"deny", "group_values":{"g-1":[val], "g-2":[other]},
                "default_values":[], "individual_values":[]}
    current = {"context":dict(CONTEXT), "topic_name":TOPIC, "evidence_ref":"inspection/branch",
               "groups":{"g-1":"scoped_group", "g-2":"scoped_group", "org":"organization"},
               "attributes":{"tier":attribute("business", "consumer"), "region":attribute("north", "south")},
               "fields":{"orders.area":{"kind":"dimension","equality_attributes":["region"],"required_access_grants":[], "bound_topics":[TOPIC]}},
               "model_grant_syntax_ref":"model/inspected-access-grant-format",
               "grant_usage":{"complete":True, "evidence_ref":"model/grant-references", "bindings":{}},
               "access_grants":{}, "topic":{"required_access_grants":[], "access_filters":[]},
               "documents":{"d-1":{"evidence_ref":"acl/d-1","complete":True,"read_only_roles":["VIEWER"],
                                   "direct":{},"inherited":{},"effective":{"g-1":None},"controls":{"area-filter":copy.deepcopy(ctrl)}}}}
    request = {"request_ref":"decision/12","group_id":"g-1",
               "grant":{"name":"business_users","user_attribute":"tier","allowed_values":["business"],"target":"topic"},
               "row_filter":{"field":"orders.area","user_attribute":"region"},
               "documents":[{"document_id":"d-1","source":"direct","role":"VIEWER","controls":[ctrl]}]}
    return {"schema_version":1, "current":current, "request":request}


def plan(spec):
    return G.plan_access(spec, context=CONTEXT, topic_name=TOPIC)


class GovernanceTests(unittest.TestCase):
    def test_exact_missing_grant_and_named_document(self):
        spec = fixture()
        original = copy.deepcopy(spec)
        out = plan(spec)
        self.assertEqual(out["status"], "proposal", out)
        self.assertEqual(out["model_snippets"], {"model":{"access_grants":{"business_users":{
            "user_attribute":"tier","allowed_values":["business"]}}},"topic":{
            "required_access_grants":["business_users"], "access_filters":[{"field":"orders.area","user_attribute":"region"}]}})
        self.assertEqual([(p["document_id"],p["group_id"],p["role"]) for p in out["document_proposals"]],
                         [("d-1","g-1","VIEWER")])
        self.assertEqual(out["controls"][0]["consumer_ids"], ["sales","volume"])
        self.assertFalse(out["authorizes_target_write"] or out["native_verified"])
        self.assertEqual(spec, original)
        self.assertEqual(plan(spec), out)

    def test_exact_existing_entitlement_and_inherited_read_reuse(self):
        spec = fixture()
        cur, req = spec["current"], spec["request"]
        cur["access_grants"]["business_users"] = {"user_attribute":"tier","allowed_values":["business"]}
        cur["topic"].update(required_access_grants=["business_users"], access_filters=[req["row_filter"]])
        req["documents"][0]["source"] = "inherited"
        cur["documents"]["d-1"]["inherited"]["g-1"] = "VIEWER"
        cur["documents"]["d-1"]["effective"]["g-1"] = "VIEWER"
        out = plan(spec)
        self.assertEqual(out["status"], "reuse_existing", out)
        self.assertEqual(out["model_snippets"], {})
        self.assertEqual(out["document_proposals"], [])
        self.assertEqual(len(out["reused"]), 4)

    def test_ambiguous_attribute_or_policy_stays_pending_without_partial_proposals(self):
        cases = [
            lambda c: c["attributes"]["tier"]["group_values"].update({"g-2":["business"]}),
            lambda c: c["attributes"]["tier"].update(default_values=["business"]),
            lambda c: c["attributes"]["tier"].update(individual_values=["business"]),
            lambda c: c["attributes"]["tier"].update(complete=False),
            lambda c: c["attributes"]["region"].update(missing_value_behavior="unknown"),
            lambda c: c["access_grants"].update(business_users={"user_attribute":"tier","allowed_values":["consumer"]}),
            lambda c: c["topic"].update(required_access_grants=["other"]),
            lambda c: c["topic"].update(access_filters=[{"field":"orders.area","user_attribute":"other"}]),
            lambda c: c["grant_usage"]["bindings"].update(business_users=["topic:unrelated"]),
            lambda c: c["fields"]["orders.area"].update(equality_attributes=[]),
            lambda c: c["fields"].clear(),
        ]
        for change in cases:
            spec = fixture()
            change(spec["current"])
            self.assert_pending(plan(spec))

    def assert_pending(self, out):
        self.assertEqual(out["status"], "pending", out)
        self.assertTrue(out["gaps"])
        self.assertEqual(out["model_snippets"], {})
        self.assertEqual(out["document_proposals"], [])
        self.assertFalse(out["authorizes_target_write"])

    def test_preserves_larger_existing_or_inherited_roles(self):
        for change in [
            lambda d: d["direct"].update({"g-1":"OWNER"}),
            lambda d: d["inherited"].update({"g-1":"VIEWER"}),
            lambda d: d.update(complete=False),
            lambda d: d["effective"].update({"g-1":"VIEWER"}),
            lambda d: d["controls"]["area-filter"].update(consumer_ids=["unrelated"]),
        ]:
            spec = fixture()
            change(spec["current"]["documents"]["d-1"])
            self.assert_pending(plan(spec))
        spec = fixture()
        spec["request"]["documents"][0]["source"] = "inherited"
        self.assert_pending(plan(spec))
        spec["request"]["documents"][0].update(source="direct",role="ADMIN")
        spec["current"]["documents"]["d-1"]["read_only_roles"] = ["ADMIN"]
        self.assert_pending(plan(spec))

    def test_wildcards_scope_drift_and_unscoped_principals(self):
        spec = fixture()
        spec["current"]["attributes"]["tier"]["group_values"]["g-1"] = ["*"]
        spec["request"]["grant"]["allowed_values"] = ["*"]
        self.assert_pending(plan(spec))
        spec = fixture()
        spec["current"]["context"]["branch_id"] = "different"
        self.assert_pending(plan(spec))
        for target in ("org","missing"):
            spec = fixture()
            spec["request"]["group_id"] = target
            self.assert_pending(plan(spec))

    def test_field_requirement_needs_known_scope_of_impact(self):
        spec = fixture()
        spec["request"]["grant"]["target"] = "orders.area"
        out = plan(spec)
        self.assertEqual(out["status"], "proposal", out)
        self.assertEqual(out["model_snippets"]["fields"]["orders.area"], {"required_access_grants":["business_users"]})
        self.assertNotIn("required_access_grants", out["model_snippets"]["topic"])
        spec["current"]["fields"]["orders.area"]["bound_topics"].append("customers")
        self.assert_pending(plan(spec))

    def test_document_only_and_no_unrequested_access(self):
        spec = fixture()
        spec["request"].update(grant=None, row_filter=None)
        del spec["current"]["attributes"], spec["current"]["access_grants"], spec["current"]["topic"]
        out = plan(spec)
        self.assertEqual(out["status"],"proposal")
        self.assertEqual(out["model_snippets"],{})
        spec["request"]["documents"][0]["controls"][0]["consumer_ids"].append("extra")
        self.assert_pending(plan(spec))


if __name__ == "__main__":
    unittest.main()
