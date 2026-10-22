"""Reviewed initial App construction: synthetic Omni transport, no customer JS."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

import test_looker_app as prior
import test_hex_capture as source

app, v = prior.app, prior.v
CONTROLLER = Path(__file__).resolve().parents[1] / "skills/omni-app-engineer/scripts/query_controller.js"


class InitialOmni(prior.AppOmni):
    def __init__(self, root, document_id="app-sales", draft_id="app-sales-draft"):
        super().__init__(root, document_id, draft_id)
        self.state.pop("app")
        self.app = None

    def http(self, method, url, token, body, max_bytes):
        if "/whoami?" in url:
            return super().http(method, url, token, body, max_bytes)
        self.http_calls.append((method, url, body))
        route = f"/api/v2/documents/{self.document_id}/draft/{self.draft_id}/app"
        assert url == "https://tenant.omniapp.co" + route
        if method == "GET":
            return (404, {}, b'{}') if self.app is None else (200, {}, json.dumps(self.app).encode())
        assert method == "PUT" and self.app is None
        intents = list((self.root / ".omni-app-native/executions").glob("*/intent.json"))
        assert intents and all(json.loads(p.read_text())["operation"] == "initial_put" for p in intents)
        self.patch_count += 1
        self.app = copy.deepcopy(body)
        self.state["app"] = {"url": route}
        if self.mode == "timeout":
            raise TimeoutError("synthetic ambiguous transport")
        if self.mode == "unrelated_change":
            self.state["queryPresentations"]["data"]["1"]["name"] = "Concurrent edit"
        if self.mode == "settings_change":
            self.app["settings"]["allowDownloads"] = True
        if self.mode == "default_settings":
            self.app["settings"] = {}
        if self.mode == "semantic_drift":
            self.topic["topic"]["always_where_filters"] = {"orders.region": "East"}
        result = {"identifier": self.document_id, "draftIdentifier": self.draft_id,
            "name": self.state["name"], "description": self.state["description"], "app": {"settings": self.app["settings"]}}
        if self.mode == "wrong_response":
            result["draftIdentifier"] = "other"
        return 200, {}, json.dumps(result).encode()


def configure_initial_app(root, requirements_path="requirements.json", prefix="initial", document_id="app-sales", draft_id="app-sales-draft"):
    """Actual source requirements + synthetic existing workbook; reusable by DMA tests."""
    root = Path(root)
    config = prior.configure_app(root, requirements_path, prefix, document_id, draft_id)
    fake = InitialOmni(root, document_id, draft_id)
    adapter = app.AppNativeAdapter(root, config["adapter"].target, runner=fake.runner, http=fake.http)
    def write(name, value):
        path = f"{prefix}-{name}.json"
        (root / path).write_text(json.dumps(value))
        return path
    req = v.load(root, requirements_path)
    controls = sorted(app.s.control_source_keys(req, "app"))
    component = 'const controller = OAAQueryController.createQueryController({queryKey:"2", bridge:syntheticReviewedBridge, inputs:inputDefinitions, onState});'
    change = 'function changeRegion(){ if (boundQuery !== "2") throw Error("scope"); const field="orders.region"; controller.change("region", document.getElementById("region").value); }'
    reset = 'function resetRegion(){ if (boundQuery !== "2") throw Error("scope"); document.getElementById("region").value="West"; return controller.reset("region"); }'
    states = {key: f'function show_{key}(){{ statusNode.textContent = "{key}"; }}' for key in
              ("loading", "empty", "error", "restricted", "stale", "reset", "run")}
    html = '<!doctype html><title>Reviewed initial App</title><select id="region"><option>West</option><option>East</option></select>'
    html += '<button id="run">Run</button><button id="reset">Reset</button><output id="status"></output><pre id="result"></pre><script>\n'
    html += CONTROLLER.read_text() + '\n'
    html += '''const boundQuery="2";
const statusNode=document.getElementById("status");
const inputDefinitions=[{id:"region",mode:"governed_filter",type:"enum",allowedValues:["West","East"],default:"West"}];
// TEST ONLY: a deterministic synthetic bridge. Replace through actual native bridge review, never ship this fixture as a vendor SDK.
async function syntheticReviewedBridge(request){ if(request.queryKey!==boundQuery) throw Error("scope"); return {rows:[{revenue:request.filters.region==="West"?100:75}]}; }
function onState(value){ const handlers={loading:show_loading,empty:show_empty,error:show_error,restricted:show_restricted,stale:show_stale,reset:show_reset}; if(handlers[value.state])handlers[value.state](); else statusNode.textContent=value.state; document.getElementById("result").textContent=JSON.stringify(value.governed||null); }
'''
    html += '\n'.join([component, change, reset, *states.values()])
    html += '\ndocument.getElementById("region").onchange=changeRegion; document.getElementById("run").onclick=()=>{show_run();return controller.run();}; document.getElementById("reset").onclick=resetRegion;\n</script>'
    runtime = v.load(root, config["runtime_path"])
    runtime["components"][0].update(runtime_fragment=component, query_reference='queryKey:"2"')
    runtime["controls"] = []
    inputs = []
    if controls:
        runtime["controls"] = [{"source_asset_keys": controls, "component_id": "summary", "query_keys": ["2"],
            "topic": "orders", "field_ids": ["orders.region"], "runtime_fragment": change, "reset_fragment": reset,
            "contract_reference": "synthetic-native-filter-bridge-review"}]
        inputs = [{"input_id": "region", "source_asset_keys": controls, "query_keys": ["2"], "mode": "governed_filter",
            "value_type": "enum", "default": "West", "allowed_values": ["West", "East"], "minimum": None, "maximum": None,
            "change_fragment": change, "reset_fragment": reset, "review_reference": "synthetic-input-equivalence"}]
    (root / config["runtime_path"]).write_text(json.dumps(runtime))
    body_path = write("body", {"html": html, "settings": copy.deepcopy(app.LOCKED_SETTINGS)})
    review_path = write("construction-review", {"schema_version": 1, "kind": "analyst_app_construction_review",
        "exclusive_draft_reference": "synthetic-exclusive-workbook-draft", "native_bridge_reference": "synthetic-not-a-vendor-sdk",
        "resource_policy_reference": "synthetic-locked-policy", "behavior_reference": "independent-native-cases-pending",
        "evidence_paths": [config["runtime_review_path"]], "input_bindings": inputs, "state_fragments": states})
    baseline_spec = v.load(root, config["baseline_spec"])
    baseline_spec.update(kind="analyst_initial_omni_app_baseline_spec", body_path=body_path, construction_review_path=review_path)
    (root / config["baseline_spec"]).write_text(json.dumps(baseline_spec))
    candidate_spec = write("candidate-spec", {"schema_version": 1, "kind": "analyst_native_app_initial_spec", "review_ref": "synthetic-full-body-review",
        "requirements_path": requirements_path, "baseline_path": config["baseline_path"], "body_path": body_path})
    return {**config, "adapter": adapter, "fake": fake, "candidate_spec": candidate_spec, "body_path": body_path,
            "construction_review_path": review_path}


class InitialAppTests(unittest.TestCase):
    setUp = prior.LookerAppTests.setUp
    write = prior.LookerAppTests.write

    def configure(self):
        project = v.load(self.root, "project.json")
        project["surfaces"] = ["app"]
        self.write("project.json", project)
        result = source.capture_fixture(self.root / "inputs/hex-capture")
        self.original = str(Path(result["output"]).relative_to(self.root))
        inventory = source.module("translate_artifact").translate((self.root / self.original).read_bytes(), "hex-capture")
        self.write("inventory.json", inventory)
        v.prepare(self.root, self.original, "inventory.json", "hex-requirements.json")
        self.write("requirements.json", v.load(self.root, "hex-requirements.json"))
        self.config = configure_initial_app(self.root)
        self.adapter, self.fake = self.config["adapter"], self.config["fake"]

    def capture(self):
        return self.adapter.capture_initial_baseline(self.config["baseline_spec"], self.config["baseline_path"])

    def prepare(self):
        return self.adapter.prepare_initial(self.config["candidate_spec"])

    def execute(self):
        self.capture()
        candidate = self.prepare()
        receipt = self.adapter.execute_initial(candidate["candidate_sha256"], "synthetic-initial-authority")
        return candidate, receipt

    def test_initial_put_preserves_queries_and_delivery_remains_pending(self):
        self.configure()
        before = copy.deepcopy(self.fake.state)
        candidate, receipt = self.execute()
        self.assertEqual(receipt["status"], "readback_matched")
        self.assertEqual({k: val for k, val in self.fake.state.items() if k != "app"}, before)
        self.assertEqual(self.fake.patch_count, 1)
        v.coverage(self.root, "requirements.json", candidate["path"], [], "initial-coverage.json")
        proof = app.verify_delivery(self.root, {"candidate_path": candidate["path"], "execution_receipt_path":
            f'.omni-app-native/executions/{candidate["candidate_sha256"]}/receipt.json', "coverage_path": "initial-coverage.json"})
        self.assertTrue(proof["gaps"])
        self.assertFalse(proof["native_verified"])

    def test_full_initial_standalone_return_recomputes_source_baseline_and_proof(self):
        self.configure()
        candidate, receipt = self.execute()
        self.assertEqual(receipt["status"], "readback_matched")
        v.coverage(self.root, "requirements.json", candidate["path"], [], "coverage.json")
        req = v.load(self.root, "requirements.json")
        self.write("scope-spec.json", {"schema_version": 1, "kind": "analyst_migration_scope_spec", "scope_id": "hex-app",
            "decision_reference": "synthetic-scope", "inventory_paths": ["inventory.json"], "units": [{"unit_id": "app",
                "inventory_path": "inventory.json", "asset_keys": [i["asset_key"] for i in req["items"]], "disposition": "migrate",
                "rationale": "Synthetic initial App journey", "frontend_asset_ids": ["app-sales"], "surfaces": ["app"]}]})
        prior.m.freeze(self.root, "scope-spec.json", "scope.json")
        self.write("return-spec.json", {"schema_version": 1, "kind": "analyst_standalone_migration_return_spec", "surface": "app",
            "scope_sha256": v.load(self.root, "scope.json")["sha256"], "baseline_path": self.config["baseline_path"],
            "requirements_path": "requirements.json", "unresolved": [], "candidate_path": candidate["path"],
            "execution_receipt_path": f'.omni-app-native/executions/{candidate["candidate_sha256"]}/receipt.json', "coverage_path": "coverage.json"})
        result = prior.m.prepare_return(self.root, "scope.json", "return-spec.json", "return.json")
        self.assertEqual(result["report"]["candidate_coverage"], "incomplete")
        self.assertEqual(prior.m.verify_return(self.root, "return.json")["status"], "consistent")
        self.assertNotIn("dma_import", v.load(self.root, "project.json"))
        self.assertEqual(self.fake.patch_count, 1)
        (self.root / self.original).write_bytes((self.root / self.original).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            prior.m.verify_return(self.root, "return.json")

    def test_initial_requires_separate_authority_and_no_replay(self):
        self.configure()
        self.capture()
        candidate = self.prepare()
        with self.assertRaisesRegex(ValueError, "separate_initial_authorization"):
            self.adapter.execute(candidate["candidate_sha256"], "edit-authority")
        self.assertEqual(self.fake.patch_count, 0)
        self.fake.mode = "timeout"
        receipt = self.adapter.execute_initial(candidate["candidate_sha256"], "initial-authority")
        self.assertEqual(receipt["status"], "outcome_unknown")
        with self.assertRaisesRegex(ValueError, "never_replay"):
            self.adapter.execute_initial(candidate["candidate_sha256"], "different-reference")
        self.assertEqual(self.adapter.reconcile_initial(candidate["candidate_sha256"])["status"], "readback_matched")
        self.assertEqual(self.fake.patch_count, 1)

    def test_existing_app_and_dashboard_cannot_be_replaced(self):
        self.configure()
        self.fake.app = {"html": "Existing App", "settings": {}}
        self.fake.state["app"] = {"url": "/api" + self.adapter._app_route()}
        with self.assertRaisesRegex(ValueError, "workbook_only"):
            self.capture()
        self.fake.app = None
        self.fake.state.pop("app")
        self.fake.state["containers"] = {"data": {}, "order": []}
        with self.assertRaises(ValueError):
            self.capture()
        self.assertEqual(self.fake.patch_count, 0)

    def test_stale_body_control_domain_and_external_resource_are_blocked(self):
        self.configure()
        review = v.load(self.root, self.config["construction_review_path"])
        review["input_bindings"][0]["default"] = "unreviewed"
        self.write(self.config["construction_review_path"], review)
        with self.assertRaisesRegex(ValueError, "input_default"):
            self.capture()
        review["input_bindings"][0]["default"] = "West"
        self.write(self.config["construction_review_path"], review)
        self.capture()
        candidate = self.prepare()
        body = v.load(self.root, self.config["body_path"])
        body["html"] += '<script src="https://unreviewed.invalid/code.js"></script>'
        self.write(self.config["body_path"], body)
        with self.assertRaises(ValueError):
            self.adapter.execute_initial(candidate["candidate_sha256"], "authority")
        with self.assertRaisesRegex(ValueError, "external_resource"):
            app.initial_body(body)
        self.assertEqual(self.fake.patch_count, 0)

    def test_concurrent_query_model_or_draft_changes_block_write(self):
        self.configure()
        self.capture()
        candidate = self.prepare()
        originals = copy.deepcopy((self.fake.state, self.fake.topic, self.fake.meta))
        for mutate in (lambda: self.fake.state["queryPresentations"]["data"]["1"].update(name="other edit"),
                       lambda: self.fake.topic["topic"]["views"][0]["measures"][0].update(sql="1"),
                       lambda: self.fake.meta.update(branch={"id": "different"})):
            self.fake.state, self.fake.topic, self.fake.meta = copy.deepcopy(originals)
            mutate()
            with self.assertRaises(ValueError):
                self.adapter.execute_initial(candidate["candidate_sha256"], "authority")
        self.assertEqual(self.fake.patch_count, 0)

    def test_write_readback_rejects_unowned_changes_and_policy_widening(self):
        for mode in ("unrelated_change", "settings_change", "semantic_drift", "default_settings"):
            with self.subTest(mode=mode):
                self.setUp()
                self.configure()
                self.fake.mode = mode
                _, receipt = self.execute()
                self.assertEqual(receipt["status"], "readback_matched" if mode == "default_settings" else
                                 "outcome_unknown" if mode == "semantic_drift" else "readback_mismatch")

    def test_local_scenario_is_typed_separate_from_governed_filter(self):
        self.configure()
        runtime = v.load(self.root, self.config["runtime_path"])
        review = v.load(self.root, self.config["construction_review_path"])
        body = v.load(self.root, self.config["body_path"])
        scenario_keys = [runtime["controls"][0]["source_asset_keys"].pop()]
        review["input_bindings"][0]["source_asset_keys"] = runtime["controls"][0]["source_asset_keys"]
        change = 'function changeGrowth(){ if(boundQuery!=="2") throw Error("scope"); controller.change("growth", Number(document.getElementById("growth").value)); }'
        reset = 'function resetGrowth(){ if(boundQuery!=="2") throw Error("scope"); document.getElementById("growth").value="10"; return controller.reset(); }'
        runtime["scenario_controls"] = [{"source_asset_keys": scenario_keys, "component_id": "summary", "query_keys": ["2"],
            "input_id": "growth", "minimum": 0, "maximum": 100, "default": 10, "formula_reference": "synthetic-local-percentage-not-governed",
            "runtime_fragment": change, "reset_fragment": reset}]
        review["input_bindings"].append({"input_id": "growth", "source_asset_keys": scenario_keys, "query_keys": ["2"],
            "mode": "local_scenario", "value_type": "number", "default": 10, "minimum": 0, "maximum": 100, "allowed_values": None,
            "change_fragment": change, "reset_fragment": reset, "review_reference": "synthetic-scenario-equivalence-native-pending"})
        body["html"] = body["html"].replace('<select id="region">', '<input id="growth" type="number" value="10"><select id="region">')
        old = runtime["components"][0]["runtime_fragment"]
        new = old.replace('onState});', 'onState, deriveScenario:(result,local)=>result.rows[0]?.revenue*(1+local.growth/100)});')
        runtime["components"][0]["runtime_fragment"] = new
        body["html"] = body["html"].replace(old, 'inputDefinitions.push({id:"growth",mode:"local_scenario",type:"number",minimum:0,maximum:100,default:10});\n'+new)
        body["html"] = body["html"].replace('</script>', change+'\n'+reset+'\ndocument.getElementById("growth").onchange=changeGrowth;\n</script>')
        self.write(self.config["runtime_path"], runtime)
        self.write(self.config["construction_review_path"], review)
        self.write(self.config["body_path"], body)
        self.capture()
        baseline = v.load(self.root, self.config["baseline_path"])
        self.assertEqual(len(baseline["semantic_selectors"]), 2)  # query + governed filter; no invented scenario field
        candidate = self.prepare()
        self.assertEqual(self.adapter.execute_initial(candidate["candidate_sha256"], "scenario-authority")["status"], "readback_matched")
        review["input_bindings"][1]["maximum"] = 99
        self.write(self.config["construction_review_path"], review)
        with self.assertRaisesRegex(ValueError, "scenario_domain_mismatch"):
            self.adapter._construction_review(self.config["construction_review_path"], body, runtime)

    def test_package_owned_initial_html_wires_controls_run_and_reset(self):
        self.configure()
        body = v.load(self.root, self.config["body_path"])
        # Execute only this test's generated template and package-owned controller;
        # no Hex source/genApp code, imported HTML, remote module or credentials.
        parser = app.Scripts()
        parser.feed(body["html"])
        program = r'''
const vm=require('node:vm'), assert=require('node:assert/strict'), fs=require('node:fs');
const script=JSON.parse(fs.readFileSync(0,'utf8'));
const nodes=Object.fromEntries(['region','run','reset','status','result'].map(id=>[id,{value:id==='region'?'West':'',textContent:''}]));
const context={document:{getElementById:id=>nodes[id]},structuredClone};
vm.runInNewContext(script, context,{timeout:1000});
(async()=>{
 await nodes.run.onclick(); assert.equal(JSON.parse(nodes.result.textContent).rows[0].revenue,100);
 nodes.region.value='East'; nodes.region.onchange(); assert.equal(nodes.status.textContent,'stale');
 await nodes.run.onclick(); assert.equal(JSON.parse(nodes.result.textContent).rows[0].revenue,75);
 await nodes.reset.onclick(); assert.equal(nodes.region.value,'West'); assert.equal(JSON.parse(nodes.result.textContent).rows[0].revenue,100);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([shutil.which("node"), "-e", program], input=json.dumps(parser.scripts[0]),
                                capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_freshness_and_missing_control_cannot_be_bypassed(self):
        self.configure()
        runtime = v.load(self.root, self.config["runtime_path"])
        saved = copy.deepcopy(runtime)
        runtime["controls"] = []
        self.write(self.config["runtime_path"], runtime)
        with self.assertRaisesRegex(ValueError, "source_control_unbound"):
            self.capture()
        self.write(self.config["runtime_path"], saved)
        self.capture()
        candidate = self.prepare()
        (self.root / self.original).write_bytes((self.root / self.original).read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            self.adapter.execute_initial(candidate["candidate_sha256"], "authority")
        self.assertEqual(self.fake.patch_count, 0)

    def test_initial_readback_context_tampering_rejected(self):
        self.configure()
        candidate, receipt = self.execute()
        self.assertEqual(receipt["status"], "readback_matched")
        value = v.load(self.root, candidate["path"])
        for change in ({"publishedIdentifier": "other"}, {"draftOutOfDate": True}, {"branch": {"id": "other"}}):
            observed = copy.deepcopy(receipt["readback"])
            observed["draft_context"].update(change)
            self.assertFalse(self.adapter.matches(value, observed))

    def test_controller_run_reset_errors_staleness_and_scenario(self):
        node = shutil.which("node")
        self.assertTrue(node, "Node required to run package-owned controller contract test")
        program = r'''
const assert = require('node:assert/strict');
const {createQueryController} = require(process.argv[1]);
(async () => {
 const calls = [], states = [], pending = [];
 const controller = createQueryController({queryKey:'2', inputs:[
  {id:'region',mode:'governed_filter',type:'enum',allowedValues:['All','East'],default:'All'},
  {id:'growth',mode:'local_scenario',type:'number',minimum:0,maximum:100,default:10}],
  bridge: request => { calls.push(request); return new Promise((resolve,reject)=>pending.push({resolve,reject})); },
  deriveScenario: (result, inputs) => result.rows[0]?.revenue * (1+inputs.growth/100),
  onState: state => states.push(state)});
 let first = controller.run();
 controller.change('region','East');
 let second = controller.run();
 pending[1].resolve({rows:[{revenue:100}]}); await second;
 pending[0].resolve({rows:[{revenue:999}]}); assert.equal((await first).ignored,true);
 assert.deepEqual(calls[1],{queryKey:'2',filters:{region:'East'}});
 assert.equal(states.at(-1).state,'ready'); assert.equal(states.at(-1).governed.rows[0].revenue,100);
 assert.ok(Math.abs(states.at(-1).scenario-110)<1e-9);
 assert.throws(()=>controller.change('growth',Infinity)); assert.throws(()=>controller.change('region','West'));
 let reset=controller.reset(); assert.equal(calls.at(-1).filters.region,'All');
 pending[2].resolve({rows:[]}); await reset; assert.equal(states.at(-1).state,'empty');
 let denied=controller.run(); pending[3].reject({code:'FORBIDDEN',message:'never expose secrets'}); await denied;
 assert.deepEqual(states.at(-1),{state:'restricted',queryKey:'2'});
 let error=controller.run(); pending[4].reject(new Error('private stack')); await error;
 assert.deepEqual(states.at(-1),{state:'error',queryKey:'2'});
 let stale=controller.run(); controller.change('growth',20); pending[5].resolve({rows:[{revenue:200}]});
 assert.equal((await stale).ignored,true); assert.equal(states.at(-1).state,'stale');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        completed = subprocess.run([node, "-e", program, str(CONTROLLER)], capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
