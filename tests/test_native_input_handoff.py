"""Executable native handoff/continuity checks with original sources and no DOM."""
import os
import importlib.util
import shutil
import subprocess
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/omni-app-engineer/scripts"
runtime_spec = importlib.util.spec_from_file_location(
    'handoff_source_runtime', Path(__file__).resolve().parents[1] / 'scripts/validate_source.py')
RUNTIME = importlib.util.module_from_spec(runtime_spec)
runtime_spec.loader.exec_module(RUNTIME)


class NativeInputHandoffTests(unittest.TestCase):
    def run_js(self, body):
        selected = os.environ.get(RUNTIME.NODE_PATH_ENV)
        digest = os.environ.get(RUNTIME.NODE_SHA_ENV)
        node = (RUNTIME.verify_node_runtime({'path': selected, 'sha256': digest})['path']
                if selected or digest else shutil.which('node'))
        self.assertTrue(node, "Existing Node is required for original-source checks")
        env = dict(os.environ)
        env.pop("NODE_OPTIONS", None)
        env.pop("NODE_PATH", None)
        program = """
const assert=require('node:assert/strict'),path=require('node:path');
const base=process.argv[1],C=require(path.join(base,'experience_components.js')),
 Q=require(path.join(base,'query_controller.js')),B=require(path.join(base,'experience_behaviors.js'));
const columns=[{key:'source.id',as:'id',type:'string',nullable:false},
 {key:'source.period',as:'period',type:'string',nullable:false},
 {key:'source.value',as:'value',type:'number',nullable:true,numericStrings:'decimal'}];
const result=value=>({phase:'complete',columns:columns.map(c=>c.key),truncated:false,completeness:'complete',
 rows:[{'source.id':'sensor-a','source.period':'period-a','source.value':value}]});
const contract={columns,grain:['id','period'],limit:20,decode:r=>r,
 correlation:'serialized_unqualified',evidenceRef:'synthetic-contract',runSettlement:'after_terminal_delivery'};
(async()=>{
""" + body + "\n})().catch(e=>{console.error(e);process.exitCode=1});"
        completed = subprocess.run([node, "-e", program, str(SCRIPTS)], env=env,
                                   capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_qualified_scalar_keys_null_and_composite_grain(self):
        self.run_js("""
const rows=result('-1.25e-2').rows;
assert.equal(C.mapRows(rows,columns,20,{grain:['id','period']})[0].value,-.0125);
assert.equal(C.mapRows(result(null).rows,columns)[0].value,null);
assert.equal(C.mapRows(result(0).rows,columns)[0].value,0);
for(const value of ['', ' ', '\\t', ' 1', '1 ', '1\\n', '1\\r', true, 'Infinity', '1,000', '1e-999'])
 assert.throws(()=>C.mapRows(result(value).rows,columns));
assert.equal(C.mapRows(result('0e-999').rows,columns)[0].value,0);
assert.equal(C.mapRows(result('5e-324').rows,columns)[0].value,5e-324);
assert.throws(()=>C.mapRows([{ID:'sensor-a',Period:'period-a',Value:4}],columns),/missing input key/);
assert.throws(()=>C.mapRows([...rows,...rows],columns,20,{grain:['id','period']}),/duplicate grain/);
assert.throws(()=>C.mapRows([{...rows[0],'source.id':' '}],columns,20,{grain:['id','period']}),/grain/);
assert.equal(C.mapRows([...rows,{...rows[0],'source.period':'period-b'}],columns,20,{grain:['id','period']}).length,2);
const integer=[{key:'id',as:'id',type:'integer',nullable:false,numericStrings:'decimal'}];
assert.equal(C.mapRows([{id:'42'}],integer)[0].id,42);
for(const id of ['9007199254740993','9007199254740991.1','4.0','4e1'])assert.throws(()=>C.mapRows([{id}],integer));
assert.throws(()=>C.mapRows(result('0').rows,columns.map(c=>{const d={...c};delete d.numericStrings;return d})),/invalid number/);
""")

    def test_listener_run_fallback_deduplication_and_serialized_refresh(self):
        self.run_js("""
let listener,settle,runs=0,cleanups=0;const states=[];
const d=Q.createQueryDelivery({...contract,onState:s=>states.push(s),
 subscribe:fn=>{listener=fn;return()=>cleanups++},run:()=>{runs++;return new Promise(resolve=>settle=resolve)}});
const first=d.refresh();listener(result('0'));
assert.equal(d.snapshot().rows[0].value,0);assert.equal(d.snapshot().busy,true);
assert.deepEqual(await d.refresh(),{started:false,reason:'busy'});assert.equal(runs,1);
settle(result(0));await first;assert.equal(cleanups,1);
assert.equal(states.filter(s=>s.phase==='ready'&&s.busy).length,1);
const count=states.length;listener(result(99));assert.equal(states.length,count);
const second=d.refresh();settle(result(8));await second;
assert.equal(d.snapshot().rows[0].value,8);assert.equal(cleanups,2); // Run-return fallback without listener.
""")

    def test_stale_restricted_and_dispose_clear_without_faking_cancellation(self):
        self.run_js("""
let listener,settle,cleanups=0;
const d=Q.createQueryDelivery({...contract,onState:()=>{},subscribe:fn=>{listener=fn;return()=>cleanups++},
 run:()=>new Promise(resolve=>settle=resolve)});
const first=d.refresh();listener(result(4));d.invalidate('stale');
assert.deepEqual(d.snapshot().rows,[]);assert.equal(d.snapshot().busy,true);
assert.equal((await d.refresh()).started,false);listener(result(9));settle(result(9));await first;
assert.equal(d.snapshot().phase,'stale');assert.deepEqual(d.snapshot().rows,[]);
const second=d.refresh();listener({phase:'restricted'});settle(result(5));await second;
assert.equal(d.snapshot().phase,'restricted');assert.deepEqual(d.snapshot().rows,[]);
const third=d.refresh();listener(result(2));d.dispose();
assert.equal(d.snapshot().phase,'disposed');assert.deepEqual(d.snapshot().rows,[]);
listener(result(7));settle(result(7));await third;assert.equal(cleanups,3);
assert.equal(d.snapshot().phase,'disposed');
""")

    def test_terminal_conflict_cap_and_missing_grain_fail_closed(self):
        self.run_js("""
async function deliver(first,last){let listener;const d=Q.createQueryDelivery({...contract,onState:()=>{},
 subscribe:fn=>{listener=fn;return()=>{}},run:async()=>{if(first)listener(first);return last;}});await d.refresh();return d.snapshot();}
assert.equal((await deliver(result(1),result(2))).phase,'error');
assert.equal((await deliver(null,{...result(1),truncated:true})).phase,'error');
const duplicate={...result(1),rows:[...result(1).rows,...result(1).rows]};
assert.deepEqual((await deliver(null,duplicate)).rows,[]);
assert.equal((await deliver(null,undefined)).reason,'missing_terminal_result');
assert.equal((await deliver(null,{...result(1),columns:['source.id']})).phase,'error');
assert.equal((await deliver(null,{...result(1),rows:Array(20).fill(result(1).rows[0])})).phase,'error');
""")

    def test_acknowledgment_only_and_failed_cleanup_do_not_reopen_delivery(self):
        self.run_js("""
const options={...contract,onState:()=>{},subscribe:()=>()=>{},run:async()=>result(1)};
assert.throws(()=>Q.createQueryDelivery({...options,runSettlement:undefined}),/handoff/);
let listener,runCount=0;
const early=Q.createQueryDelivery({...options,subscribe:fn=>{listener=fn;return()=>{}},run:async()=>undefined});
await early.refresh();listener(result(8));assert.equal(early.snapshot().reason,'missing_terminal_result');
assert.deepEqual(early.snapshot().rows,[]);
const broken=Q.createQueryDelivery({...options,subscribe:fn=>{listener=fn;return()=>{throw Error('cleanup')}} ,
 run:async()=>{runCount++;return result(2)}});
await broken.refresh();assert.equal(broken.snapshot().usable,false);
assert.equal(broken.snapshot().reason,'subscription_cleanup_failed');assert.deepEqual(broken.snapshot().rows,[]);
assert.deepEqual(await broken.refresh(),{started:false,reason:'subscription_unusable'});assert.equal(runCount,1);
listener(result(9));assert.deepEqual(broken.snapshot().rows,[]);
broken.dispose();assert.equal(broken.snapshot().usable,false);
const missing=Q.createQueryDelivery({...options,subscribe:()=>undefined});
await missing.refresh();assert.equal(missing.snapshot().usable,false);assert.equal((await missing.refresh()).started,false);
const asyncCleanup=Q.createQueryDelivery({...options,subscribe:()=>()=>Promise.reject(Error('async cleanup'))});
await asyncCleanup.refresh();assert.equal(asyncCleanup.snapshot().usable,false);
let synchronous,cleaned=0,unexpectedRuns=0;
synchronous=Q.createQueryDelivery({...options,onState:s=>{if(s.phase==='ready')synchronous.dispose()},
 subscribe:fn=>{fn(result(5));return()=>cleaned++},run:async()=>{unexpectedRuns++;return result(5)}});
await synchronous.refresh();assert.equal(unexpectedRuns,0);assert.equal(cleaned,1);
assert.equal(synchronous.snapshot().phase,'disposed');
""")

    def test_ordered_drill_return_focus_fallback_and_access_clear(self):
        self.run_js("""
let returned;const s=B.createSelection({onChange:()=>{},restore:token=>{returned=token;return true;}});
const ticket=s.begin('query-scope');s.receive(ticket,{ids:['a','b','c'],completeness:'complete',access:'allowed'});
s.order(['c','a','b']);s.select('c',{focus:'origin',scroll:80,page:2,sort:'score-desc'});
assert.equal(s.step(1),true);assert.equal(s.snapshot().selectedId,'a');s.step(1);assert.equal(s.step(1),false);
s.returnToContext();assert.deepEqual(returned,{focus:'origin',scroll:80,page:2,sort:'score-desc'});
assert.throws(()=>s.order(['a','b']),/preserve/);
const targets={disabled:{enabled:false},hidden:{enabled:false},heading:{enabled:true}};let focused=null;
assert.equal(B.restoreFocus(['missing','disabled','hidden','heading'],{resolve:k=>targets[k],isUsable:t=>t.enabled,focus:t=>{focused=t}}),'heading');
assert.equal(focused,targets.heading);
const denied=s.begin('restricted');s.receive(denied,{ids:[],completeness:'unknown',access:'denied'});
assert.equal(s.snapshot().selectedId,null);assert.equal(s.returnToContext(),false);assert.equal(s.step(1),false);
""")

    def test_coverage_and_per_context_camera_choices_are_retained(self):
        self.run_js("""
const coverage={era:'historical-period',selection:'first two qualifying events',participants:'observed sensors only',observedOnly:true};
const frames=[{id:'f1',atMs:0,segment:'a',observations:[{id:'sensor',x:1}]},{id:'f2',atMs:100,segment:'a',observations:[]}];
const p=B.createRecordedPlayback({frames,coverage,clock:{now:()=>0,request:()=>1,cancel:()=>{}},onFrame:()=>{}});
coverage.participants='mutated';assert.equal(p.snapshot().coverage.participants,'observed sensors only');
p.seek(1);assert.deepEqual(p.snapshot().frame.observations,[]); // No invented missing participant.
const cameras=B.createEntityChoices({validate:v=>{assert(Number.isFinite(v.yaw)&&v.zoom>=.5&&v.zoom<=2);return v;},onChange:()=>{}});
cameras.set('workspace',{yaw:20,zoom:1.2});cameras.set('detail-a',{yaw:80,zoom:1});
const recreated=cameras.get('workspace').value;assert.deepEqual(recreated,{yaw:20,zoom:1.2});
cameras.set('workspace',{yaw:0,zoom:1});assert.equal(cameras.get('detail-a').value.yaw,80);
assert.throws(()=>cameras.set('workspace',{yaw:0,zoom:20}));
""")

    def test_actual_classic_sources_share_the_qualified_boundary(self):
        self.run_js("""
const fs=require('node:fs'),vm=require('node:vm');const context={structuredClone};vm.createContext(context);
// Actual classic-script order, no document/window/DOM emulation or native SDK.
for(const name of ['experience_components.js','query_controller.js','experience_behaviors.js'])
 vm.runInContext(fs.readFileSync(path.join(base,name),'utf8'),context);
context.columns=columns;context.rows=result('-2').rows;
assert.equal(vm.runInContext("OAAExperience.mapRows(rows,columns,20,{grain:['id','period']})[0].value",context),-2);
assert.equal(vm.runInContext("typeof OAAQueryController.createQueryDelivery",context),'function');
assert.equal(vm.runInContext("typeof OAAQueryController.createConsumerDelivery",context),'function');
assert.equal(vm.runInContext("typeof OAAExperienceBehaviors.restoreFocus",context),'function');
""")

    def test_visible_consumers_update_later_tabs_and_wait_for_actual_refresh(self):
        self.run_js("""
const listeners={},settles={},seen=[],refreshes=[];
const d=Q.createConsumerDelivery({queries:['first','later'].map(queryKey=>({queryKey,delivery:{...contract,
 subscribe:fn=>{listeners[queryKey]=fn;return()=>{}},run:()=>new Promise(resolve=>settles[queryKey]=resolve)}})),
 consumers:[{id:'primary',mode:'live',queryKeys:['first']},{id:'detail',mode:'live',queryKeys:['later']},
 {id:'combined',mode:'live',queryKeys:['first','later']},{id:'estimate',mode:'scenario',label:'Scenario estimate',
  assumptionsRef:'reviewed-assumptions',baseConsumerIds:['primary','detail'],derive:b=>
   b.primary.rowsByQuery.first[0].value+b.detail.rowsByQuery.later[0].value}],
 onConsumer:s=>seen.push(s),onRefresh:s=>refreshes.push(s)});
const work=d.refresh();listeners.later(result(9));
assert.equal(d.snapshot().consumers.detail.rowsByQuery.later[0].value,9);
listeners.later(result(9));
assert.equal(seen.filter(s=>s.id==='detail'&&s.generation===1&&s.phase==='ready'&&s.busy).length,1);
assert.deepEqual(d.snapshot().consumers.combined.rowsByQuery,{});
assert.equal(d.snapshot().consumers.estimate.value,null);
listeners.first(result(3));assert.equal(d.snapshot().consumers.estimate.value,12);
assert.equal(d.snapshot().consumers.combined.rowsByQuery.later[0].value,9);
assert.equal(d.snapshot().refresh.success,false);
assert.deepEqual(await d.refresh(),{started:false,reason:'busy'});
settles.first(result(3));await Promise.resolve();assert.equal(d.snapshot().refresh.success,false);
settles.later(result(9));assert.deepEqual(await work,{started:true,success:true});
assert.equal(refreshes.filter(s=>s.phase==='complete').length,1);
assert(seen.some(s=>s.id==='detail'&&s.rowsByQuery.later?.[0].value===9));
const laterOld=listeners.later;const second=d.refresh();
assert.deepEqual(d.snapshot().consumers.combined.rowsByQuery,{});
listeners.first(result(5));laterOld(result(99));
assert.deepEqual(d.snapshot().consumers.detail.rowsByQuery,{});
listeners.later(result(2));listeners.later(result(2));
assert.equal(seen.filter(s=>s.id==='detail'&&s.generation===2&&s.phase==='ready'&&s.busy).length,1);
settles.later(result(2));settles.first(result(5));await second;
assert.equal(d.snapshot().consumers.estimate.value,7);
""")

    def test_denied_error_and_invalidation_remove_live_scenario_and_snapshot_rows(self):
        self.run_js("""
let listener,settle;const observed=[];
const d=Q.createConsumerDelivery({queries:[{queryKey:'1',delivery:{...contract,
 subscribe:fn=>{listener=fn;return()=>{}},run:()=>new Promise(resolve=>settle=resolve)}}],
 consumers:[{id:'observed',mode:'live',queryKeys:['1']},
 {id:'archive',mode:'snapshot',label:'Snapshot',period:'Period A',sourceRef:'retained-export',value:[{value:40}]},
 {id:'estimate',mode:'scenario',label:'Scenario estimate',assumptionsRef:'reviewed-assumptions',
 baseConsumerIds:['observed'],derive:b=>b.observed.rowsByQuery['1'][0]?.value*2}],
 onConsumer:s=>observed.push(s),onRefresh:()=>{}});
assert.equal(d.snapshot().consumers.archive.phase,'snapshot');
const work=d.refresh();listener(result(4));assert.equal(d.snapshot().consumers.estimate.value,8);
listener({phase:'restricted'});assert.equal(d.snapshot().consumers.observed.phase,'restricted');
assert.deepEqual(d.snapshot().consumers.observed.rowsByQuery,{});
assert.equal(d.snapshot().consumers.estimate.value,null);assert.equal(d.snapshot().consumers.archive.value,null);
assert.equal(d.snapshot().refresh.busy,true);listener(result(70));settle(result(70));await work;
assert.equal(d.snapshot().refresh.success,false);assert.equal(d.snapshot().refresh.phase,'restricted');
const retry=d.refresh();listener(result(6));d.invalidate('stale');listener(result(90));settle(result(90));await retry;
assert.equal(d.snapshot().consumers.observed.phase,'stale');assert.equal(d.snapshot().consumers.estimate.value,null);
const third=d.refresh();listener({phase:'error'});settle();await third;
assert.deepEqual(d.snapshot().consumers.observed.rowsByQuery,{});
assert.equal(d.snapshot().consumers.observed.phase,'error');assert.equal(d.snapshot().refresh.phase,'restricted');
const fourth=d.refresh();listener(result(5));d.dispose();settle(result(5));await fourth;
assert.equal(d.snapshot().refresh.phase,'disposed');assert.equal(d.snapshot().consumers.observed.phase,'disposed');
assert.equal(d.snapshot().consumers.archive.value,null);
""")

    def test_empty_partial_conflicting_terminals_and_scenario_failures_never_false_success(self):
        self.run_js("""
async function trial(first,last,derive=()=>0){let listener;const d=Q.createConsumerDelivery({
 queries:[{queryKey:'1',delivery:{...contract,subscribe:fn=>{listener=fn;return()=>{}},run:async()=>{listener(first);return last}}}],
 consumers:[{id:'main',mode:'live',queryKeys:['1']},{id:'estimate',mode:'scenario',label:'Scenario',
 assumptionsRef:'assumptions',baseConsumerIds:['main'],derive}],onConsumer:()=>{},onRefresh:()=>{}});
 await d.refresh();return d.snapshot()}
const empty={...result(0),rows:[]};let state=await trial(empty,empty);
assert.equal(state.consumers.main.phase,'empty');assert.equal(state.refresh.success,true);
state=await trial({...result(4),completeness:'partial'},undefined);
assert.equal(state.refresh.phase,'partial');assert.equal(state.refresh.success,false);
assert.deepEqual(state.consumers.main.rowsByQuery,{});assert.equal(state.consumers.estimate.value,null);
state=await trial(result(3),result(7));assert.equal(state.refresh.phase,'error');
assert.deepEqual(state.consumers.main.rowsByQuery,{});
state=await trial(result(3),result(3),()=>{throw new Error('bad scenario')});
assert.equal(state.consumers.estimate.phase,'error');assert.equal(state.refresh.success,false);
state=await trial(result(3),result(3),async()=>{throw new Error('async scenario')});
assert.equal(state.consumers.estimate.phase,'error');
""")

    def test_consumer_inventory_and_snapshot_only_contract(self):
        self.run_js("""
const args={queries:[{queryKey:'saved-query',delivery:{...contract,subscribe:()=>()=>{},run:async()=>result(1)}}],
 consumers:[{id:'main',mode:'live',queryKeys:['saved-query']}],onConsumer:()=>{},onRefresh:()=>{}};
assert.equal((await Q.createConsumerDelivery(args).refresh()).success,true);
assert.throws(()=>Q.createConsumerDelivery({...args,queries:[...args.queries,...args.queries]}),/duplicate/);
assert.throws(()=>Q.createConsumerDelivery({...args,consumers:[{id:'main',mode:'live',queryKeys:['unknown']}]}),/query missing/);
assert.throws(()=>Q.createConsumerDelivery({...args,consumers:[{id:'estimate',mode:'scenario',label:'Scenario',
 assumptionsRef:'reviewed-assumptions',baseConsumerIds:['estimate'],derive:()=>0}]}),/recursive/);
const snapshot=Q.createConsumerDelivery({...args,queries:[],consumers:[{id:'archive',mode:'snapshot',
 label:'Snapshot',period:'Period A',sourceRef:'export',value:[{value:1}]}]});
assert.deepEqual(await snapshot.refresh(),{started:false,reason:'no_live_queries'});
assert.equal(snapshot.snapshot().refresh.success,false);snapshot.invalidate('restricted');
assert.equal(snapshot.snapshot().consumers.archive.value,null);
""")

    def test_failed_visible_rendering_cannot_report_refresh_success(self):
        self.run_js("""
const args={queries:[{queryKey:'1',delivery:{...contract,subscribe:()=>()=>{},run:async()=>result(1)}}],
 consumers:[{id:'main',mode:'live',queryKeys:['1']}],onConsumer:()=>{},onRefresh:()=>{}};
let d=Q.createConsumerDelivery({...args,onConsumer:s=>{if(s.phase==='ready')throw new Error('renderer failed')}});
assert.equal((await d.refresh()).success,false);assert.equal(d.snapshot().refresh.busy,false);
assert.equal(d.snapshot().consumers.main.reason,'render_callback_failed');
assert.deepEqual(d.snapshot().consumers.main.rowsByQuery,{});
d=Q.createConsumerDelivery({...args,onRefresh:()=>{throw new Error('refresh renderer failed')}});
assert.equal((await d.refresh()).success,false);assert.equal(d.snapshot().refresh.busy,false);
""")

    def test_transient_snapshot_hold_recovers_only_after_all_explicit_refresh_runs_settle(self):
        self.run_js("""
const listeners={},settles={};
const d=Q.createConsumerDelivery({queries:['first','later'].map(queryKey=>({queryKey,delivery:{...contract,
 subscribe:fn=>{listeners[queryKey]=fn;return()=>{}},run:()=>new Promise(resolve=>settles[queryKey]=resolve)}})),
 consumers:[{id:'current',mode:'live',queryKeys:['first','later']},
 {id:'archive',mode:'snapshot',label:'Snapshot',period:'Period A',sourceRef:'retained-export',value:40},
 {id:'estimate',mode:'scenario',label:'Scenario estimate',assumptionsRef:'reviewed-assumptions',
 baseConsumerIds:['current','archive'],derive:b=>b.archive.value+b.current.rowsByQuery.later[0].value}],
 onConsumer:()=>{},onRefresh:()=>{}});
const first=d.refresh();listeners.first({phase:'error'});listeners.later(result(2));
settles.first();settles.later(result(2));await first;
assert.equal(d.snapshot().consumers.archive.value,null);assert.equal(d.snapshot().refresh.success,false);
const second=d.refresh();assert.equal(d.snapshot().consumers.archive.value,null);
listeners.later(result(5));listeners.first(result(3));
assert.equal(d.snapshot().consumers.archive.value,null);assert.equal(d.snapshot().consumers.estimate.value,null);
settles.later(result(5));await Promise.resolve();assert.equal(d.snapshot().consumers.archive.value,null);
assert.equal(d.snapshot().refresh.success,false);
settles.first(result(3));assert.deepEqual(await second,{started:true,success:true});
assert.equal(d.snapshot().consumers.archive.phase,'snapshot');assert.equal(d.snapshot().consumers.archive.value,40);
assert.equal(d.snapshot().consumers.estimate.value,45);
""")

    def test_snapshot_access_and_scope_holds_survive_later_errors_and_successes(self):
        self.run_js("""
for(const blocked of ['restricted','stale']) {
 const listeners={},settles={};
 const d=Q.createConsumerDelivery({queries:['first','later'].map(queryKey=>({queryKey,delivery:{...contract,
  subscribe:fn=>{listeners[queryKey]=fn;return()=>{}},run:()=>new Promise(resolve=>settles[queryKey]=resolve)}})),
  consumers:[{id:'current',mode:'live',queryKeys:['first','later']},
  {id:'archive',mode:'snapshot',label:'Snapshot',period:'Period A',sourceRef:'retained-export',value:40},
  {id:'estimate',mode:'scenario',label:'Scenario estimate',assumptionsRef:'reviewed-assumptions',
   baseConsumerIds:['archive'],derive:b=>b.archive.value*2}],onConsumer:()=>{},onRefresh:()=>{}});
 const first=d.refresh();listeners.first({phase:blocked});listeners.later({phase:'error'});
 settles.first(result(1));settles.later(result(2));await first;
 assert.equal(d.snapshot().consumers.archive.phase,blocked);
 const second=d.refresh();listeners.first(result(3));listeners.later(result(4));
 settles.first(result(3));settles.later(result(4));await second;
 assert.equal(d.snapshot().consumers.current.phase,'ready');assert.equal(d.snapshot().consumers.archive.phase,blocked);
 assert.equal(d.snapshot().consumers.archive.value,null);assert.equal(d.snapshot().consumers.estimate.value,null);
 assert.equal(d.snapshot().refresh.success,false);
}
""")


if __name__ == "__main__":
    unittest.main()
