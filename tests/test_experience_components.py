"""Offline behavior of package-owned components; no native or visual assertions."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "skills/omni-app-engineer/scripts/experience_components.js"
EXAMPLE = ROOT / "skills/omni-app-engineer/assets/evidence-workbench.html"


class ExperienceComponentsTests(unittest.TestCase):
    def run_js(self, source):
        node = shutil.which("node")
        self.assertTrue(node, "Node is required for these package-owned JavaScript checks")
        completed = subprocess.run(
            [node, "-e", "const assert=require('node:assert/strict');"
             "const C=require(process.argv[1]);\n" + source, str(COMPONENTS), str(EXAMPLE)],
            text=True, capture_output=True, timeout=15, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_exact_input_keys_types_zero_and_null(self):
        self.run_js("""
const columns=[{key:'inspection.station',as:'id',type:'string',nullable:false},
 {key:'inspection.passed',as:'passed',type:'integer',nullable:true}];
assert.deepEqual(C.mapRows([{'inspection.station':'s-a','inspection.passed':0},
 {'inspection.station':'s-b','inspection.passed':null}],columns),[{id:'s-a',passed:0},{id:'s-b',passed:null}]);
assert.throws(()=>C.mapRows([{Station:'s-a',Passed:0}],columns),/missing input key/);
assert.throws(()=>C.mapRows([{'inspection.station':'s-a','inspection.passed':'0'}],columns),/invalid integer/);
assert.throws(()=>C.mapRows([{'inspection.station':'s-a','inspection.passed':Number.MAX_SAFE_INTEGER+1}],columns));
assert.throws(()=>C.mapRows([{},{}],columns,1),/oversized/);
""")

    def test_generations_partial_results_and_failed_refresh(self):
        self.run_js("""
let now=1000;const states=[];
const r=C.createResource({validate:rows=>C.mapRows(rows,[{key:'value',as:'value',type:'number',nullable:true}]),
 onState:s=>states.push(s),now:()=>now,maxAgeMs:100});
const a=r.begin('region-a'), b=r.begin('region-b');
assert.equal(r.accept(a,{data:[{value:99}],completeness:'complete',evidenceRef:'old'}),false);
r.accept(b,{data:[{value:0}],completeness:'unknown',evidenceRef:'simulation'});
assert.equal(r.snapshot().phase,'partial');assert.equal(r.snapshot().sourceAsOf,null);
now=1101;assert.equal(r.refreshAge().phase,'stale');
const c=r.begin('region-b');assert.equal(r.snapshot().data,null);
assert.throws(()=>r.accept(c,{data:[{bad:1}],completeness:'complete',evidenceRef:'simulation'}),/missing/);
r.fail(c,'restricted','Access denied');assert.equal(r.snapshot().data,null);
assert.equal(r.accept(c,{data:[{value:1}],completeness:'complete',evidenceRef:'late'}),false);
const count=states.length;r.dispose();r.refreshAge();assert.equal(states.length,count);
assert.throws(()=>r.begin('new'),/disposed/);
""")

    def test_media_load_is_not_readiness_and_cleanup_ignores_late_events(self):
        self.run_js("""
let stops=0;const states=[];
const m=C.createMediaState({onState:s=>states.push(s),stop:()=>stops++});
const first=m.begin('source-a');m.frameLoaded(first);
assert.equal(m.snapshot().phase,'loading');assert.equal(m.snapshot().qualification,'unobserved');
const second=m.begin('source-b');assert.equal(m.ready(first,{method:'native_observation',reference:'wrong-source'}),false);
assert.throws(()=>m.ready(second,{}),/evidence/);
m.ready(second,{method:'simulation',reference:'offline-double'});
assert.equal(m.snapshot().qualification,'simulation');
m.unavailable(second,'fallback','Provider blocked');assert.equal(m.snapshot().phase,'fallback');
const before=states.length;m.dispose();m.dispose();assert.equal(stops,4);
assert.equal(m.ready(second,{method:'provider_event',reference:'late'}),false);assert.equal(states.length,before);
""")

    def test_scene_population_calendar_and_interruptible_camera(self):
        self.run_js("""
const rows=[{id:'a',eligible:90,passed:72},{id:'b',eligible:10,passed:9},{id:'c',eligible:20,passed:null}];
const aggregate=C.weightedRate(rows);assert.equal(aggregate.rate,null);assert.equal(aggregate.measuredRate,.81);
assert.equal(aggregate.coverage,100/120);assert.deepEqual(aggregate.missingIds,['c']);
assert.equal(C.weightedRate([{id:'zero',eligible:0,passed:0}]).rate,null);
assert.throws(()=>C.weightedRate([rows[0],rows[0]]),/duplicate/);
const bounds={xMin:-1,xMax:4,yMin:-1,yMax:4}, points=[{id:'a',x:0,y:0},{id:'b',x:3,y:3}];
for(const yaw of [-90,0,90])for(const [width,height]of [[300,200],[900,320]]){
 const spec={width,height,padding:25,yaw,tilt:35,bounds};const projected=C.projectScene(points,spec);
 assert(projected.every(p=>p.x>=25&&p.x<=width-25&&p.y>=25&&p.y<=height-25));
 assert.deepEqual(C.projectScene([points[0]],spec)[0],projected[0]);
}
assert.throws(()=>C.projectScene([{id:'x',x:5,y:0}],{width:300,height:200,bounds}),/out-of-bounds/);
const feb=C.monthCells(2032,2);assert.equal(feb.filter(Boolean).length,29);assert.equal(feb[0],'2032-02-01');
let clock=0,id=0;const queue=new Map(), frames=[];
const motion=C.createCameraMotion({frame:fn=>{queue.set(++id,fn);return id},cancelFrame:key=>queue.delete(key),
 now:()=>clock,onFrame:value=>frames.push(value),durationMs:180});
motion.move({yaw:0,tilt:35},{yaw:30,tilt:35});const obsolete=[...queue.values()][0];
motion.move({yaw:0,tilt:35},{yaw:-30,tilt:80},true);obsolete();
assert.equal(queue.size,0);assert.deepEqual(frames,[{yaw:-30,tilt:80}]);
motion.move({yaw:-30,tilt:80},{yaw:0,tilt:35});motion.dispose();assert.equal(queue.size,0);
""")

    def test_assembled_example_selection_return_calendar_and_teardown(self):
        # Actual scripts, classic-script shared scope, no browser/render emulation.
        self.assertEqual(len(re.findall(r'<script\b', EXAMPLE.read_text())), 2)
        self.run_js(r"""
const fs=require('node:fs'),vm=require('node:vm'),html=fs.readFileSync(process.argv[2],'utf8');
class Element{
 constructor(){this.children=[];this.events=new Map();this.attrs={};this.value='';this.textContent='';}
 append(...items){for(const item of items){item.parentElement=this;this.children.push(item);}}
 replaceChildren(...items){this.children=[];this.append(...items);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 addEventListener(k,fn){if(!this.events.has(k))this.events.set(k,new Set());this.events.get(k).add(fn);}
 removeEventListener(k,fn){this.events.get(k)?.delete(fn);}
 emit(k,event={}){for(const fn of this.events.get(k)||[])fn({target:this,...event});}
 focus(){document.activeElement=this;}
}
const nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
nodes['scene-title'].parentElement=new Element();
const document={getElementById:id=>nodes[id],createElement:()=>new Element(),createElementNS:()=>new Element()};
const media=new Element();media.matches=false;let next=0;const pending=new Map();
const windowEvents=new Element();
const context={document,structuredClone,Intl,Date,performance:{now:()=>0},matchMedia:()=>media,
 requestAnimationFrame:fn=>{pending.set(++next,fn);return next},cancelAnimationFrame:id=>pending.delete(id),
 addEventListener:(...args)=>windowEvents.addEventListener(...args),removeEventListener:(...args)=>windowEvents.removeEventListener(...args)};
context.window=context;vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))if(match[1].trim())vm.runInContext(match[1],context);
assert.match(nodes.population.textContent,/81\/100 = 81.0%/);assert.match(nodes.population.textContent,/Unknown/);
const inspect=nodes['station-rows'].children[1].children[3].children[0];inspect.emit('click');
assert.equal(nodes['detail-title'].textContent,'Beryl');assert.equal(document.activeElement,nodes['detail-title']);
assert.equal(nodes.detail.children[0].textContent,'90.0%');nodes.back.emit('click');assert.equal(document.activeElement,inspect);
nodes.next.emit('click');assert.equal(nodes.month.textContent,'March 2030');nodes.previous.emit('click');assert.equal(nodes.month.textContent,'February 2030');
nodes['media-load'].emit('click');assert.match(nodes['media-status'].textContent,/loading: frame load alone/);
nodes.angle.emit('click');assert.equal(pending.size,1);media.matches=true;media.emit('change');assert.equal(pending.size,0);
context.OAAWorkbenchExample.destroy();assert.equal(pending.size,0);
assert.equal([...nodes.next.events.values()][0].size,0);assert.equal([...media.events.values()][0].size,0);
""")


if __name__ == "__main__":
    unittest.main()
