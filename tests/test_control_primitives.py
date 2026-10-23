"""Opt-in DOM bindings and query lifecycle, with no browser or native execution."""
import shutil
import subprocess
import unittest
from pathlib import Path

ENGINEER = Path(__file__).resolve().parents[1] / "skills/omni-app-engineer"


class ControlPrimitiveTests(unittest.TestCase):
    def run_js(self, body):
        node = shutil.which("node")
        self.assertTrue(node, "Node required for local controller checks")
        program = "const assert=require('node:assert/strict'),path=require('node:path');const R=process.argv[1];const Q=require(path.join(R,'scripts/query_controller.js'));const C=require(path.join(R,'scripts/control_primitives.js'));\n" + body
        result = subprocess.run([node, "-e", program, str(ENGINEER)], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bounded_text_and_atomic_restore_do_not_infer_results(self):
        self.run_js(r"""
const states=[],calls=[];
const inputs=[{id:'search',mode:'governed_filter',type:'text',maxLength:12,default:''}];
const c=Q.createQueryController({queryKey:'4',inputs,bridge:r=>{calls.push(r);return Promise.resolve({rows:[]})},onState:s=>states.push(s),includeInputState:true});
for(const value of ['1234567890123','line\nbreak',12,'x\u0000'])assert.throws(()=>c.change('search',value));
c.change('search',' 東京 ');assert.equal(c.snapshot().draft.search,' 東京 ');assert.equal(calls.length,0);
const saved=c.snapshot();saved.applied={search:'earlier'};
c.restore(saved);assert.equal(c.snapshot().state,'restored');assert.equal(c.snapshot().governed,null);assert.equal(c.snapshot().resultMatchesDraft,false);assert.equal(calls.length,0);
saved.draft.search='mutated';assert.equal(c.snapshot().draft.search,' 東京 ');
for(const record of [{...c.snapshot(),queryKey:'8'},{...c.snapshot(),draft:{search:'ok',extra:'x'}},{...c.snapshot(),applied:{search:'too long a value'}}])assert.throws(()=>c.restore(record));
assert.equal(c.snapshot().draft.search,' 東京 ');
assert.throws(()=>Q.createQueryController({queryKey:'4',inputs:[{...inputs[0],maxLength:Infinity}],bridge:()=>{},onState:()=>{}}));
assert.throws(()=>Q.createQueryController({queryKey:'4',inputs:[{...inputs[0],minLength:2}],bridge:()=>{},onState:()=>{}}));
""")

    def test_stale_ab_retry_restore_cancel_reset_and_dispose(self):
        self.run_js(r"""
(async()=>{
const requests=[],states=[],pending=[];
const c=Q.createQueryController({queryKey:'4',inputs:[{id:'q',mode:'governed_filter',type:'text',maxLength:20,default:''}],includeInputState:true,
bridge:r=>{requests.push(r);return new Promise((resolve,reject)=>pending.push({resolve,reject}))},onState:s=>states.push(s)});
assert.throws(()=>c.retry(),/no submitted/);
c.change('q','A');const a=c.run();c.change('q','B');const b=c.run();
pending[1].resolve({rows:[{id:'B'}]});await b;pending[0].resolve({rows:[{id:'A'}]});assert.equal((await a).ignored,true);
assert.equal(c.snapshot().governed.rows[0].id,'B');assert.equal(c.snapshot().resultMatchesDraft,true);
c.change('q','C');const retry=c.retry();assert.equal(requests.at(-1).filters.q,'B');pending[2].resolve({rows:[{id:'B'}]});await retry;
assert.equal(c.snapshot().state,'stale');assert.equal(c.snapshot().draft.q,'C');assert.equal(c.snapshot().applied.q,'B');assert.equal(c.snapshot().resultMatchesDraft,false);
const pendingRestore=c.run(),saved=c.snapshot();c.restore(saved);pending[3].resolve({rows:[{id:'C'}]});assert.equal((await pendingRestore).ignored,true);assert.equal(c.snapshot().governed,null);
const cancelled=c.run();c.cancel();pending[4].reject(new Error('late error'));assert.equal((await cancelled).ignored,true);assert.equal(c.snapshot().state,'cancelled');
const reset=c.reset();assert.equal(requests.at(-1).filters.q,'');pending[5].reject({code:'FORBIDDEN',message:'private'});await reset;assert.equal(c.snapshot().state,'restricted');assert.equal(JSON.stringify(c.snapshot()).includes('private'),false);
const again=c.retry();pending[6].resolve({rows:[]});await again;assert.equal(c.snapshot().state,'empty');assert.equal(c.snapshot().dirty,false);
const dying=c.run();const count=states.length;c.dispose();pending[7].resolve({rows:[{id:'late'}]});assert.equal((await dying).ignored,true);assert.equal(states.length,count);
assert.equal(c.snapshot().state,'disposed');assert.throws(()=>c.change('q','x'),/disposed/);assert.throws(()=>c.restore(saved),/disposed/);
})().catch(e=>{console.error(e);process.exitCode=1});
""")

    def test_search_composition_clear_silent_restore_and_disposal(self):
        self.run_js(r"""
class E{constructor(tag){this.tagName=tag;this.value='';this.events={};this.attrs={}}addEventListener(k,f){(this.events[k]??=new Set()).add(f)}removeEventListener(k,f){this.events[k].delete(f)}setAttribute(k,v){this.attrs[k]=v}focus(){this.focused=true}emit(k,extra={}){for(const f of this.events[k]||[])f({target:this,...extra})}}
const input=new E('INPUT'),clearButton=new E('BUTTON'),error=new E('P'),changes=[];
const c=C.bindSearch({input,clearButton,error,maxLength:6,onChange:(value,context)=>changes.push({value,...context})});
assert.equal(clearButton.disabled,true);input.emit('compositionstart');input.value='東';input.emit('input',{isComposing:true});assert.equal(changes.length,0);
input.value='東京';input.emit('compositionend');input.emit('input');assert.deepEqual(changes,[{value:'東京',reason:'input'}]);
c.set('saved');assert.equal(changes.length,1);assert.equal(input.value,'saved');
input.value='toolong';input.emit('input');assert.equal(c.snapshot().valid,false);assert.equal(changes.length,1);assert.match(error.textContent,/at most/);
clearButton.emit('click');assert.equal(input.value,'');assert.equal(input.focused,true);assert.equal(changes.at(-1).reason,'clear');assert.equal(c.snapshot().valid,true);
assert.throws(()=>C.bindSearch({input,clearButton,maxLength:6,onChange:()=>{}}),/already bound/);
c.dispose();input.value='late';input.emit('input');assert.equal(changes.length,2);assert.throws(()=>c.set('x'),/disposed/);
C.bindSearch({input,clearButton,maxLength:6,onChange:()=>{}}).dispose();
""")

    def test_native_choice_bindings_and_truthful_summary(self):
        self.run_js(r"""
class E{constructor(tag){this.tagName=tag;this.events={};this.attrs={}}addEventListener(k,f){(this.events[k]??=new Set()).add(f)}removeEventListener(k,f){this.events[k].delete(f)}setAttribute(k,v){this.attrs[k]=v}emit(k){for(const f of this.events[k]||[])f({target:this})}}
const select=new E('SELECT');select.disabled=true;select.options=[{value:'name',parentElement:select},{value:'score'},{value:'unavailable',disabled:true},{value:'group-disabled',parentElement:{tagName:'OPTGROUP',disabled:true}}];select.value='name';const values=[];
const s=C.bindSelect({select,onChange:v=>values.push(v)});s.set('score');assert.deepEqual(values,[]);select.value='name';select.emit('change');assert.deepEqual(values,['name']);assert.throws(()=>s.set('unavailable'));assert.throws(()=>s.set('group-disabled'));select.disabled=false;
const a=new E('INPUT'),b=new E('INPUT');Object.assign(a,{name:'scope',value:'all',checked:true});Object.assign(b,{name:'scope',value:'one',checked:false});const fieldset=new E('FIELDSET');fieldset.querySelectorAll=()=>[a,b];
const radios=C.bindRadios({fieldset,onChange:v=>values.push(v)});radios.set('one',{notify:true});assert.equal(a.checked,false);assert.equal(b.checked,true);assert.equal(values.at(-1),'one');
const button=new E('BUTTON');C.setButtonState(button,{busy:true,pressed:false});assert.equal(button.disabled,true);assert.equal(button.attrs['aria-busy'],'true');
const label={};C.setSummary(label,{shown:1,total:null,completeness:'partial',filters:[{label:'Name',value:'<script>x</script>'}]});assert.match(label.textContent,/1 supplied · partial result/);assert.match(label.textContent,/<script>x<\/script>/);
assert.throws(()=>C.setSummary(label,{shown:1,completeness:'complete'}));
s.dispose();radios.dispose();assert.equal(a.events.change.size,0);
""")

    def test_actual_studio_two_structures_partial_selection_and_restoration(self):
        self.run_js(r"""
(async()=>{
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(path.join(R,'assets/control-studio.html'),'utf8');
let document;
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.events=new Map();this.textContent='';this.hidden=false;this.checked=false;this.disabled=false;this._value=null;}
 append(...items){for(const item of items){item.parentElement=this;this.children.push(item);}}
 replaceChildren(...items){this.children=[];this.append(...items);}
 setAttribute(k,v){this.attrs[k]=String(v);if(k==='id')this.id=v;if(k==='name')this.name=v;if(k==='value')this._value=v;if(k==='type')this.type=v;if(k==='hidden')this.hidden=true;if(k==='checked')this.checked=true;if(k==='disabled')this.disabled=true;}
 get options(){return this.all().filter(x=>x.tagName==='OPTION');}
 get value(){return this._value??(this.tagName==='SELECT'?this.options.find(o=>o.attrs.selected!==undefined)?.value??this.options[0]?.value??'':'');}
 set value(v){this._value=v;}
 all(){return this.children.flatMap(c=>[c,...c.all()]);}
 querySelectorAll(selector){assert.equal(selector,'input[type="radio"]');return this.all().filter(x=>x.tagName==='INPUT'&&x.type==='radio');}
 addEventListener(k,f){if(!this.events.has(k))this.events.set(k,new Set());this.events.get(k).add(f);}
 removeEventListener(k,f){this.events.get(k)?.delete(f);}
 emit(k,extra={}){if(this.disabled&&k==='click')return;for(const fn of [...(this.events.get(k)||[])])fn({target:this,preventDefault(){},...extra});}
 focus(){document.activeElement=this;}
}
document=new Element('document');document.createElement=tag=>new Element(tag);document.getElementById=id=>document.all().find(n=>n.id===id);
const stripped=html.replace(/<style[\s\S]*?<\/style>/g,'').replace(/<script[\s\S]*?<\/script>/g,'');
const stack=[document],voids=new Set(['META','LINK','INPUT','BR','HR']);
for(const token of stripped.matchAll(/<\/?([a-z][a-z0-9]*)([^>]*)>/gi)){
 if(token[0].startsWith('</')){if(stack.at(-1)?.tagName===token[1].toUpperCase())stack.pop();continue;}
 const el=new Element(token[1]);for(const attr of token[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g))el.setAttribute(attr[1],attr[2]??'');
 stack.at(-1).append(el);if(!voids.has(el.tagName))stack.push(el);
}
const $=id=>document.getElementById(id),timers=new Map(),events=new Element('window');let next=0;
const context={document,structuredClone,Intl,Date,setTimeout:fn=>{timers.set(++next,fn);return next},clearTimeout:id=>timers.delete(id),addEventListener:(...a)=>events.addEventListener(...a),removeEventListener:(...a)=>events.removeEventListener(...a)};
context.window=context;vm.createContext(context);
for(const match of html.matchAll(/<script src="([^"]+)"/g))vm.runInContext(fs.readFileSync(path.resolve(R,'assets',match[1]),'utf8'),context);
const flush=async()=>{for(const [id,fn] of [...timers]){timers.delete(id);fn();}await Promise.resolve();await Promise.resolve();};
const edit=(id,value)=>{$(id).value=value;$(id).emit(id.endsWith('search')?'input':'change');};
assert.equal(timers.size,1);assert.equal($('desk-apply').disabled,true);await flush();
assert.equal($('desk-rows').tagName,'TBODY');assert.equal($('reading-rows').tagName,'OL');assert.equal($('desk-rows').children.length,6);
$('desk-row-object-12').emit('click');assert.equal($('desk-detail-title').textContent,'Blue glaze bowl');assert.equal($('desk-split').attrs['data-mode'],'detail');
$('desk-return').emit('click');assert.equal(document.activeElement.id,'desk-row-object-12');assert.equal($('desk-split').attrs['data-mode'],'index');
edit('desk-kind','paper');assert.equal($('reading-kind').value,'paper');assert.match($('desk-state-line').textContent,/Fields changed/);
$('desk-form').emit('submit');await flush();assert.equal($('desk-rows').children.length,2);assert.match($('desk-detail').children[0].textContent,/outside this complete/);
$('show-reading').emit('click');assert.equal($('desk-presentation').hidden,true);$('reading-row-object-23').emit('click');assert.equal($('reading-index').hidden,true);assert.equal($('reading-detail-title').textContent,'Folded map');
$('reading-return').emit('click');assert.equal($('reading-index').hidden,false);assert.equal(document.activeElement.id,'reading-row-object-23');
edit('desk-search','x'.repeat(81));edit('desk-kind','all');assert.equal($('desk-search').value.length,81);assert.match($('desk-search-error').textContent,/at most/);
$('desk-reset').emit('click');await flush();assert.equal($('desk-search').value,'');edit('desk-sort','year');assert.equal($('desk-rows').children[0].children[0].textContent,'Woven ribbon');assert.equal($('reading-sort').value,'year');
$('show-desk').emit('click');$('desk-row-object-12').emit('click');$('partial-next').emit('click');$('desk-form').emit('submit');await flush();
assert.match($('desk-summary').textContent,/2 of 6 supplied · partial/);assert.match($('desk-detail').children[0].textContent,/availability is unknown/);
$('save-fields').emit('click');edit('desk-search','map');$('desk-form').emit('submit');assert.equal(timers.size,1);$('restore-fields').emit('click');await flush();
assert.match($('desk-state-line').textContent,/Fields restored only/);assert.equal($('desk-search').value,'');assert.match($('desk-summary').textContent,/completeness unknown/);
$('fail-next').emit('click');$('desk-form').emit('submit');await flush();assert.match($('desk-state-line').textContent,/failed/);$('desk-retry').emit('click');await flush();assert.equal($('desk-rows').children.length,6);
edit('desk-search','unapplied');$('desk-retry').emit('click');await flush();assert.match($('desk-state-line').textContent,/older submitted scope/);assert.equal($('desk-rows').children.length,1);assert.equal($('desk-search').value,'unapplied');
$('desk-form').emit('submit');context.OAAControlStudio.destroy();assert.equal(timers.size,0);assert.equal($('desk-search').events.get('input').size,0);await Promise.resolve();
})().catch(e=>{console.error(e);process.exitCode=1});
""")


if __name__ == '__main__':
    unittest.main()
