"""Neutral behavior contracts and two renderer adapters, executed offline only."""
import shutil
import subprocess
import unittest
from pathlib import Path


ENGINEER = Path(__file__).resolve().parents[1] / "skills/omni-app-engineer"
BEHAVIORS = ENGINEER / "scripts/experience_behaviors.js"
STUDIO = ENGINEER / "assets/behavior-studio.html"


class ExperienceBehaviorTests(unittest.TestCase):
    def run_js(self, body):
        node = shutil.which("node")
        self.assertTrue(node, "Node is required for the package-owned behavior checks")
        result = subprocess.run(
            [node, "-e", "const assert=require('node:assert/strict');const B=require(process.argv[1]);\n" + body,
             str(BEHAVIORS), str(STUDIO)],
            capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_selection_distinguishes_partial_excluded_denied_and_restores_origin(self):
        self.run_js("""
const states=[],restores=[];
const c=B.createSelection({onChange:s=>states.push(s),restore:(token,context)=>{restores.push({token,context});return 'resolved'}});
let ticket=c.begin('all');c.receive(ticket,{ids:['a','b'],access:'allowed',completeness:'complete'});
const origin={focus:'original-a',scroll:82};c.select('a',origin);origin.focus='mutated';
const obsolete=c.begin('older-page');ticket=c.begin('partial-page');
assert.equal(c.receive(obsolete,{ids:[],access:'allowed',completeness:'complete'}),false);
c.receive(ticket,{ids:['b'],access:'allowed',completeness:'partial'});
assert.equal(c.snapshot().selectedId,'a');assert.equal(c.snapshot().availability,'unknown');
assert.equal(c.returnToContext(),'resolved');assert.equal(restores[0].token.focus,'original-a');
assert.equal(restores[0].context.originContextKey,'all');assert.equal(restores[0].context.current.contextKey,'partial-page');
ticket=c.begin('complete-filter');c.receive(ticket,{ids:['b'],access:'allowed',completeness:'complete'});
assert.equal(c.snapshot().availability,'excluded');assert.equal(c.snapshot().selectedId,'a');
ticket=c.begin('restricted');assert.throws(()=>c.receive(ticket,{ids:['a'],access:'denied',completeness:'complete'}));
c.receive(ticket,{ids:[],access:'denied',completeness:'unknown'});assert.equal(c.snapshot().availability,'denied');
assert.throws(()=>c.select('a',{}),/not in current/);
const n=states.length;c.dispose();assert.equal(c.receive(ticket,{ids:[],access:'allowed',completeness:'complete'}),false);
assert.equal(states.length,n);assert.throws(()=>c.returnToContext(),/disposed/);
""")

    def test_entity_choices_are_isolated_without_implicit_defaults(self):
        self.run_js("""
const c=B.createEntityChoices({validate:(v,id)=>{if(!['detail','source'].includes(v.mode))throw Error('invalid mode');return v},onChange:()=>{},maxEntities:2});
assert.deepEqual(c.get('a'),{present:false,value:null});const value={mode:'source'};c.set('a',value);value.mode='detail';
c.set('b',{mode:'detail'});assert.equal(c.get('a').value.mode,'source');
const result=c.get('a');result.value.mode='detail';assert.equal(c.get('a').value.mode,'source');
assert.throws(()=>c.set('a',{mode:'invented'}));assert.equal(c.get('a').value.mode,'source');
assert.throws(()=>c.set('c',{mode:'source'}),/capacity/);c.forget('b');c.set('c',{mode:'source'});
c.dispose();assert.throws(()=>c.get('a'),/disposed/);
""")

    def test_recorded_playback_gaps_missing_observations_and_cancellation(self):
        self.run_js("""
let instant=0,next=0;const pending=new Map(),observed=[];
const clock={now:()=>instant,request:fn=>{pending.set(++next,fn);return next},cancel:key=>pending.delete(key)};
const frames=[{id:'f0',atMs:0,segment:'one',observations:[{id:'q',value:2}]},
 {id:'f1',atMs:100,segment:'one',observations:[]},{id:'f2',atMs:200,segment:'one',observations:[{id:'q',value:6}]},
 {id:'f3',atMs:800,segment:'two',observations:[{id:'q',value:9}]},{id:'f4',atMs:900,segment:'two',observations:[{id:'q',value:10}]}];
const c=B.createRecordedPlayback({frames,clock,onFrame:s=>observed.push(s)});
const tick=at=>{instant=at;const [key,fn]=pending.entries().next().value;pending.delete(key);fn()};
c.play();tick(50);assert.equal(c.snapshot().frame.id,'f0');assert.equal(c.snapshot().frame.observations[0].value,2);
tick(100);assert.deepEqual(c.snapshot().frame.observations,[]);tick(250);
assert.equal(c.snapshot().phase,'gap');assert.equal(c.snapshot().index,2);assert.equal(c.snapshot().nextSegmentIndex,3);assert.equal(pending.size,0);
assert.deepEqual(c.series('q',4).map(part=>part.map(x=>x.frameId)),[['f0'],['f2'],['f3','f4']]);
c.seek(3);c.play();const stale=[...pending.values()][0];c.setReducedMotion(true);assert.equal(pending.size,0);stale();assert.equal(c.snapshot().index,3);
assert.equal(c.play(),false);c.seek(4);assert.equal(c.snapshot().frame.observations[0].value,10);
c.setReducedMotion(false);c.seek(0);c.play();const last=[...pending.values()][0];c.dispose();const count=observed.length;last();assert.equal(observed.length,count);
assert.throws(()=>B.createRecordedPlayback({frames:[frames[1],frames[0]],clock,onFrame:()=>{}}),/unordered/);
assert.throws(()=>B.createRecordedPlayback({frames:[frames[0],{...frames[1],observations:[{id:'q'},{id:'q'}]}],clock,onFrame:()=>{}}),/identities/);
""")

    def test_time_navigation_preserves_date_precision_and_unknowns(self):
        self.run_js("""
const events=[{id:'date',time:{kind:'date',value:'2028-04-02'}},
 {id:'instant',time:{kind:'instant',value:'2028-04-02T00:30:00Z'}},
 {id:'offset',time:{kind:'instant',value:'2028-03-12T01:30:00-05:00'}},
 {id:'unknown',time:{kind:'unknown',reason:'Not scheduled'}}];
const c=B.createTimeNavigation({events,timeZone:'America/New_York',month:'2028-04',weekStartsOn:1,onChange:()=>{}});
const initial=c.snapshot();assert.equal(initial.events.find(e=>e.id==='date').dayKey,'2028-04-02');
assert.equal(initial.events.find(e=>e.id==='instant').dayKey,'2028-04-01');assert.deepEqual(initial.undatedIds,['unknown']);
assert.equal(initial.cells.find(x=>x?.date==='2028-04-01').ids[0],'instant');
c.setTimeZone('UTC');assert.equal(c.snapshot().events.find(e=>e.id==='instant').dayKey,'2028-04-02');
assert.equal(c.snapshot().events.find(e=>e.id==='date').dayKey,'2028-04-02');
c.setMonth('2028-02');assert.equal(c.snapshot().cells.filter(Boolean).length,29);c.shift(1);assert.equal(c.snapshot().month,'2028-03');
assert.throws(()=>c.replaceEvents([{id:'bad',time:{kind:'date',value:'2027-02-29'}}]));
assert.equal(c.snapshot().events.length,4);assert.throws(()=>c.setTimeZone('invalid/timezone'));assert.equal(c.snapshot().timeZone,'UTC');
for(const value of ['2028-04-02T01:00:00','2028-04-02T24:00:00Z','2028-04-02T01:00:00+14:30'])
 assert.throws(()=>B.normalizeEvents([{id:'x',time:{kind:'instant',value}}],'UTC'));
assert.throws(()=>B.normalizeEvents([events[0],events[0]],'UTC'),/duplicate/);
""")

    def test_actual_studio_uses_shared_selection_in_two_layouts(self):
        self.run_js(r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),html=fs.readFileSync(process.argv[2],'utf8');
class Element{
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.events=new Map();this.textContent='';this.hidden=false;this.value='';this.checked=false;}
 append(...children){for(const child of children){child.parentElement=this;this.children.push(child);}}
 replaceChildren(...children){this.children=[];this.append(...children);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 addEventListener(k,f){if(!this.events.has(k))this.events.set(k,new Set());this.events.get(k).add(f);}
 removeEventListener(k,f){this.events.get(k)?.delete(f);}
 emit(k,event={}){for(const fn of [...(this.events.get(k)||[])])fn({target:this,...event});}
 focus(){document.activeElement=this;}
}
const nodes=Object.fromEntries([...html.matchAll(/<([a-z0-9]+)[^>]*\bid="([^"]+)"/g)].map(m=>[m[2],new Element(m[1])]));
const document=new Element();document.getElementById=key=>nodes[key];document.createElement=tag=>new Element(tag);document.hidden=false;
const preference=new Element();preference.matches=false;const windowEvents=new Element();let next=0;const pending=new Map();
const context={document,structuredClone,Intl,Date,performance:{now:()=>0},matchMedia:()=>preference,
 requestAnimationFrame:fn=>{pending.set(++next,fn);return next},cancelAnimationFrame:key=>pending.delete(key),
 addEventListener:(...args)=>windowEvents.addEventListener(...args),removeEventListener:(...args)=>windowEvents.removeEventListener(...args)};
context.window=context;vm.createContext(context);
for(const match of html.matchAll(/<script src="([^"]+)"/g))vm.runInContext(fs.readFileSync(path.resolve(path.dirname(process.argv[2]),match[1]),'utf8'),context);
assert.equal(nodes['table-records'].tagName,'TBODY');assert.equal(nodes['reading-records'].tagName,'OL');
const tableButton=()=>nodes['table-records'].children[1].children[2].children[0];
tableButton().emit('click');assert.equal(nodes['table-detail-title'].textContent,'Color study');
nodes['table-detail'].children[1].children[1].emit('click');assert.match(nodes['table-detail'].children[0].textContent,/archive-28/);
nodes['show-reading'].emit('click');assert.equal(nodes['reading-index'].hidden,true);
assert.match(nodes['reading-detail'].children[0].textContent,/archive-28/);nodes['reading-return'].emit('click');
assert.equal(nodes['table-presentation'].hidden,false);assert.equal(document.activeElement,tableButton());
nodes['partial'].emit('click');assert.match(nodes['scope-status'].textContent,/availability: unknown/);
nodes['table-return'].emit('click');assert.equal(document.activeElement,nodes['table-results-title']);
nodes['excluded'].emit('click');assert.match(nodes['scope-status'].textContent,/availability: excluded/);
nodes['all'].emit('click');assert.match(nodes['table-detail'].children[0].textContent,/archive-28/);
nodes['show-reading'].emit('click');nodes['reading-browse'].emit('click');assert.equal(nodes['reading-index'].hidden,false);
const readingButton=index=>nodes['reading-records'].children[index].children[2];
readingButton(0).emit('click');assert.equal(nodes['reading-detail-title'].textContent,'Folded survey');
assert.doesNotMatch(nodes['reading-detail'].children[0].textContent,/Original identity/);
nodes['reading-return'].emit('click');assert.equal(nodes['reading-index'].hidden,false);assert.equal(document.activeElement,readingButton(0));
readingButton(1).emit('click');assert.match(nodes['reading-detail'].children[0].textContent,/archive-28/);
nodes['reading-return'].emit('click');assert.equal(document.activeElement,readingButton(1));
nodes['play'].emit('click');assert.equal(pending.size,1);nodes['reduced'].checked=true;nodes['reduced'].emit('change');assert.equal(pending.size,0);
nodes['denied'].emit('click');assert.match(nodes['table-detail'].children[0].textContent,/Access is denied/);
context.OAABehaviorStudio.destroy();assert.equal([...nodes.all.events.values()][0].size,0);assert.equal(pending.size,0);
""")


if __name__ == '__main__':
    unittest.main()
