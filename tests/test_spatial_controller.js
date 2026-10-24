"use strict";
const assert=require('node:assert/strict');
const test=require('node:test');
require('../skills/omni-app-engineer/scripts/spatial_controller.js');
function setup(overrides={}) {
  const calls=[],states=[];
  const renderer={setCamera:v=>calls.push(['camera',v]),setSelection:id=>calls.push(['select',id]),resize:()=>calls.push(['resize']),dispose:()=>calls.push(['dispose'])};
  const options={entities:[{id:'part-a',label:'Component A'},{id:'part-b',label:'Component B'}],
    views:[{id:'top',label:'Top inspection'},{id:'reset',label:'Named reset view'}],
    bindings:[{entityId:'part-a',dataKey:'record-2'},{entityId:'part-b',dataKey:'record-1'}],
    metrics:['count','rate'],renderer,onState:s=>states.push(s),...overrides};
  return {controller:OAASpatialController.create(options),calls,states};
}
test('stable keyed refresh preserves camera/selection and rejects superseded replies',()=>{
  const {controller:c,calls}=setup();c.select('part-b');c.showView('top');
  const old=c.begin(),current=c.begin();
  assert.deepEqual(c.resolve(old,{status:'ready',rows:[]}),{ignored:true});
  c.resolve(current,{status:'ready',rows:[{key:'record-2',values:{count:4,rate:null}},{key:'record-1',values:{count:0,rate:0}}]});
  const s=c.snapshot();assert.equal(s.selection,'part-b');assert.equal(s.camera,'top');
  assert.deepEqual(s.values['part-b'],{count:0,rate:0});assert.equal(s.values['part-a'].rate,null);
  assert.deepEqual(calls,[['select','part-b'],['camera','top']]);
  s.values['part-b'].count=999;assert.equal(c.snapshot().values['part-b'].count,0);
});
test('malformed rows do not partially commit; restricted scope clears old values',()=>{
  const {controller:c}=setup();let token=c.begin();
  c.resolve(token,{status:'ready',rows:[{key:'record-2',values:{count:5,rate:0.5}}]});
  assert.deepEqual(c.snapshot().missing,['part-b']);token=c.begin();
  assert.throws(()=>c.resolve(token,{status:'ready',rows:[{key:'record-2',values:{count:6,rate:Infinity}}]}));
  assert.equal(c.snapshot().values['part-a'].count,5);
  c.invalidate('restricted');assert.deepEqual(c.snapshot().values,{});
  assert.deepEqual(c.resolve(token,{status:'empty'}),{ignored:true});
  assert.deepEqual(c.resolve(null,{status:'empty'}),{ignored:true});
  token=c.begin();assert.throws(()=>c.resolve(token,{status:'restricted',rows:[{key:'record-1',values:{count:1,rate:1}}]}));
});
test('named camera aliases, explicit tour and lifecycle preserve the data boundary',()=>{
  const {controller:c,calls}=setup();c.showView('reset');c.reset();
  assert.deepEqual(calls.slice(0,3),[['camera','reset'],['select',null],['camera',null]]);
  c.stepTour();assert.equal(c.snapshot().camera,'top');c.stepTour();assert.equal(c.snapshot().camera,'reset');
  c.setReducedMotion(true);assert.equal(c.snapshot().tourIndex,null);
  c.rendererStatus('context-lost');assert.equal(c.snapshot().rendererStatus,'context-lost');
  c.dispose();c.dispose();assert.equal(calls.filter(x=>x[0]==='dispose').length,1);
  assert.throws(()=>c.begin());assert.throws(()=>c.select('part-a'));assert.equal(c.snapshot().disposed,true);
});
test('incomplete/ambiguous bindings and unknown model or metric identities fail',()=>{
  assert.throws(()=>setup({bindings:[]}));
  assert.throws(()=>setup({bindings:[{entityId:'part-a',dataKey:'same'},{entityId:'part-b',dataKey:'same'}]}));
  const {controller:c}=setup();assert.throws(()=>c.select('array-index-0'));assert.throws(()=>c.showView('unknown'));
  const token=c.begin();
  assert.throws(()=>c.resolve(token,{status:'ready',rows:[{key:'unknown',values:{count:1,rate:1}}]}));
  assert.throws(()=>c.resolve(token,{status:'ready',rows:[{key:'record-1',values:{count:1,rate:1,hidden:2}}]}));
});
