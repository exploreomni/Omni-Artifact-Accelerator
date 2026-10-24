'use strict';
// Synthetic first-party lifecycle/math checks only. No browser or renderer host.
const test=require('node:test');
const assert=require('node:assert/strict');
const Session=require('../skills/omni-app-engineer/scripts/native_scene_session.js');
const clone=value=>JSON.parse(JSON.stringify(value));
const views=[
  {id:'a',label:'Front',position:[0,0,10],target:[0,0,0]},
  {id:'b',label:'Side',position:[10,0,0],target:[0,0,0]},
  {id:'c',label:'Back',position:[0,0,-10],target:[0,0,0]}
];
function fakeClock(){
  let current=0,sequence=0,peak=0;const frames=new Map();
  return {now:()=>current,requestFrame(fn){const id=++sequence;frames.set(id,fn);peak=Math.max(peak,frames.size);return id;},cancelFrame:id=>frames.delete(id),
    step(delta){current+=delta;const scheduled=[...frames.values()];frames.clear();scheduled.forEach(fn=>fn(current));},
    get count(){return frames.size;},get peak(){return peak;},get callbacks(){return [...frames.values()];}};
}
function renderer(){
  const calls={camera:[],resize:[],dispose:0};let current={position:[0,0,10],target:[0,0,0]};
  return {calls,getCamera:()=>clone(current),manual(value){current=clone(value);},
    setCamera(value){calls.camera.push(clone(value));current=clone(value);},resize(...args){calls.resize.push(args);},dispose(){calls.dispose++;}};
}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}

test('initialization failure is recoverable and concurrent start owns one renderer',async()=>{
  const r=renderer(),clock=fakeClock();let attempts=0;
  const session=Session.create({views,clock,initialize:async()=>{attempts++;if(attempts===1)throw new Error('synthetic');return r;}});
  assert.equal(session.snapshot().state,'idle');assert.equal(await session.start(),false);
  assert.equal(session.snapshot().state,'error');assert.equal(session.snapshot().error,'initialization_failed');
  const pending=session.retry();assert.equal(session.start(),pending);assert.equal(await pending,true);assert.equal(attempts,2);
  assert.equal(session.snapshot().state,'ready');assert.equal(clock.count,0);session.dispose();assert.equal(r.calls.dispose,1);
});

test('scene-only empty views uses the renderer camera and rejects an empty tour',async()=>{
  const r=renderer(),clock=fakeClock(),session=Session.create({views:[],clock,reducedMotion:false,initialize:async()=>r});
  assert.equal(await session.start(),true);assert.deepEqual(session.snapshot().camera,r.getCamera());assert.equal(session.snapshot().viewId,null);
  assert.throws(()=>session.startTour([]),/bounded known tour/);assert.equal(clock.count,0);session.dispose();
  const missing=renderer();delete missing.getCamera;const unsupported=Session.create({views:[],initialize:async()=>missing});
  assert.equal(await unsupported.start(),false);assert.equal(unsupported.snapshot().error,'initial_camera_unavailable');assert.equal(missing.calls.dispose,1);unsupported.dispose();
  for(const id of ['1startsWithNumber','dot.id','colon:id','a'.repeat(65)])assert.throws(()=>Session.create({views:[{...views[0],id}],initialize:async()=>renderer()}),/identity/);
  assert.throws(()=>Session.create({views:[{...views[0],label:'x'.repeat(121)}],initialize:async()=>renderer()}),/label/);
});

test('disposal during pending initialization releases late results without camera work',async()=>{
  const late=deferred(),r=renderer(),session=Session.create({views,initialize:()=>late.promise});
  const pending=session.start();await Promise.resolve();assert.equal(session.snapshot().state,'loading');session.dispose();late.resolve(r);
  assert.equal(await pending,false);assert.equal(session.snapshot().state,'disposed');assert.equal(r.calls.dispose,1);assert.equal(r.calls.camera.length,0);
  assert.equal(await session.start(),false);assert.equal(await session.retry(),false);assert.equal(session.selectView('missing'),false);
});

test('retry supersedes pending generations and disposes only the stale renderer',async()=>{
  const old=deferred(),oldRenderer=renderer(),current=renderer();let attempts=0;
  const session=Session.create({views,initialize:()=>++attempts===1?old.promise:Promise.resolve(current)});
  const earlier=session.start();await Promise.resolve();assert.equal(await session.retry(),true);
  old.resolve(oldRenderer);assert.equal(await earlier,false);assert.equal(oldRenderer.calls.dispose,1);assert.equal(oldRenderer.calls.camera.length,0);
  assert.equal(current.calls.dispose,0);assert.equal(session.snapshot().state,'ready');session.dispose();assert.equal(current.calls.dispose,1);
});

test('two instances keep cameras and owned frame cancellation independent',async()=>{
  const clock=fakeClock(),one=renderer(),two=renderer();
  const a=Session.create({views,clock,initialize:async()=>one,reducedMotion:false}),b=Session.create({views,clock,initialize:async()=>two,reducedMotion:false});
  await Promise.all([a.start(),b.start()]);a.selectView('b');b.selectView('c');assert.equal(clock.count,2);
  clock.step(200);const held=one.calls.camera.length;a.dispose();assert.equal(clock.count,1);clock.step(200);
  assert.equal(one.calls.camera.length,held);assert.equal(b.snapshot().viewId,'c');assert.equal(two.calls.dispose,0);assert.equal(clock.count,0);b.dispose();
});

test('repeated mount/dispose leaves no frame and cannot restart disposed sessions',async()=>{
  const clock=fakeClock();let initialized=0;
  for(let i=0;i<4;i++){
    const r=renderer(),session=Session.create({views,clock,reducedMotion:false,initialize:async()=>{initialized++;return r;}});
    await session.start();session.startTour(['b','a'],{durationMs:100,dwellMs:50});assert.equal(clock.count,1);
    session.dispose();session.dispose();assert.equal(clock.count,0);assert.equal(r.calls.dispose,1);
    assert.equal(await session.retry(),false);assert.equal(session.resize(NaN,0),false);assert.equal(session.setVisibility(true),false);
  }
  assert.equal(initialized,4);assert.equal(clock.peak,1);
});

test('hidden and offscreen return stay paused with no camera drift or automatic tour',async()=>{
  const clock=fakeClock(),r=renderer(),session=Session.create({views,clock,reducedMotion:false,initialize:async()=>r});
  await session.start();session.startTour(['b','c'],{durationMs:100,dwellMs:50});clock.step(50);
  session.setVisibility(false);const frozen=clone(r.getCamera()),count=r.calls.camera.length;
  clock.step(50000);session.setVisibility(true);assert.equal(session.snapshot().state,'paused');assert.equal(clock.count,0);
  assert.equal(r.calls.camera.length,count);assert.deepEqual(r.getCamera(),frozen);
  await session.start();assert.equal(session.snapshot().state,'ready');assert.equal(session.snapshot().motion,null);assert.deepEqual(r.getCamera(),frozen);
  session.selectView('c');clock.step(50);session.setOffscreen(true);const held=r.calls.camera.length;
  session.setOffscreen(false);clock.step(10000);assert.equal(session.snapshot().state,'paused');assert.equal(r.calls.camera.length,held);
  session.dispose();
});

test('an explicit tour reaches each stop, dwells, completes and leaves no recurring frame',async()=>{
  const r=renderer(),clock=fakeClock(),session=Session.create({views,clock,reducedMotion:false,initialize:async()=>r});
  await session.start();session.startTour(['b','a'],{durationMs:100,dwellMs:50});
  clock.step(100);assert.equal(session.snapshot().viewId,'b');assert.equal(session.snapshot().motion.phase,'dwell');
  clock.step(49);assert.equal(session.snapshot().viewId,'b');assert.equal(session.snapshot().motion.index,0);
  clock.step(1);assert.equal(session.snapshot().targetViewId,'a');assert.equal(session.snapshot().motion.phase,'move');
  clock.step(100);assert.equal(session.snapshot().viewId,'a');clock.step(50);assert.equal(session.snapshot().motion,null);assert.equal(clock.count,0);
  assert.equal(clock.peak,1);const count=r.calls.camera.length;clock.step(5000);assert.equal(r.calls.camera.length,count);
  session.startTour(['b']);session.stopTour();assert.equal(clock.count,0);assert.equal(session.snapshot().motion,null);session.dispose();
});

test('interruption cancels stale callbacks and hands the current manual camera back',async()=>{
  const clock=fakeClock(),r=renderer(),session=Session.create({views,clock,reducedMotion:false,initialize:async()=>r});
  await session.start();session.selectView('b');clock.step(100);const stale=clock.callbacks[0];session.interrupt();
  const count=r.calls.camera.length;stale();assert.equal(r.calls.camera.length,count);assert.equal(clock.count,0);
  const manual={position:[4,3,8],target:[1,0,0]};r.manual(manual);session.selectView('c');clock.step(0);
  assert.deepEqual(r.getCamera(),manual);assert.equal(session.snapshot().targetViewId,'c');session.interrupt();assert.equal(clock.count,0);
  delete r.getCamera;r.manual({position:[12,4,9],target:[0,0,0]});session.interrupt();session.selectView('a');
  assert.equal(session.snapshot().viewId,'a');assert.equal(clock.count,0);assert.equal(session.snapshot().motion,null);session.dispose();
});

test('reduced-motion changes cancel active motion; named views remain instant',async()=>{
  const clock=fakeClock(),r=renderer(),session=Session.create({views,clock,initialize:async()=>r});
  await session.start();assert.equal(session.startTour(['b']),false);session.selectView('b');assert.equal(clock.count,0);assert.deepEqual(r.getCamera().position,[10,0,0]);
  session.setReducedMotion(false);session.selectView('a');clock.step(100);session.setReducedMotion(true);
  const count=r.calls.camera.length,held=r.getCamera();clock.step(10000);assert.equal(r.calls.camera.length,count);assert.deepEqual(r.getCamera(),held);
  session.selectView('c');assert.deepEqual(r.getCamera().position,[0,0,-10]);assert.equal(clock.count,0);
  session.setReducedMotion(false);assert.equal(clock.count,0);session.dispose();
});

test('context loss tears down motion and restoration retries without resuming a tour',async()=>{
  const clock=fakeClock(),renderers=[renderer(),renderer()];let initialized=0;
  const session=Session.create({views,clock,reducedMotion:false,initialize:async()=>renderers[initialized++]});
  await session.start();session.startTour(['b','c'],{durationMs:100,dwellMs:50});clock.step(25);const held=renderers[0].getCamera();
  session.contextLost();assert.equal(session.snapshot().state,'context-lost');assert.equal(clock.count,0);assert.equal(renderers[0].calls.dispose,1);
  assert.equal(await session.contextRestored(),true);assert.equal(initialized,2);assert.equal(session.snapshot().state,'ready');assert.equal(session.snapshot().motion,null);
  assert.deepEqual(renderers[1].getCamera(),held);assert.equal(clock.count,0);session.dispose();assert.equal(renderers[1].calls.dispose,1);
});

test('size validation is atomic, DPR is capped, and zero size requires explicit resume',async()=>{
  const clock=fakeClock(),r=renderer(),session=Session.create({views,clock,reducedMotion:false,initialize:async()=>r});
  for(const size of [[NaN,20,1],[-1,20,1],[20,Infinity,1],[20,20,0],[20,20,9],[16385,20,1]])assert.throws(()=>session.resize(...size),/bounded size/);
  assert.equal(session.snapshot().size,null);session.resize(800,400,8);await session.start();assert.deepEqual(r.calls.resize,[[800,400,2]]);
  session.selectView('b');session.resize(0,400,1);assert.equal(session.snapshot().state,'paused');assert.equal(clock.count,0);assert.equal(r.calls.resize.length,1);
  session.resize(400,300,1);assert.equal(session.snapshot().state,'paused');assert.deepEqual(r.calls.resize[1],[400,300,1]);
  await session.start();assert.equal(session.snapshot().state,'ready');assert.equal(clock.count,0);session.dispose();
});

test('callback/cleanup failures stay bounded and renderer failures allow a fresh retry',async()=>{
  const clock=fakeClock(),bad=renderer(),good=renderer();let count=0;
  bad.dispose=()=>{bad.calls.dispose++;throw new Error('synthetic cleanup');};
  const session=Session.create({views,clock,initialize:async()=>++count===1?bad:good,onState:()=>{throw new Error('synthetic observer');}});
  assert.equal(await session.start(),true);bad.setCamera=()=>{throw new Error('synthetic camera');};
  assert.equal(session.selectView('b'),false);assert.equal(session.snapshot().state,'error');assert.equal(bad.calls.dispose,1);
  assert.ok(session.snapshot().diagnostics.includes('on_state_failed'));assert.ok(session.snapshot().diagnostics.includes('renderer_cleanup_failed'));
  assert.equal(await session.retry(),true);session.dispose();assert.equal(session.snapshot().state,'disposed');assert.equal(good.calls.dispose,1);assert.equal(clock.count,0);
});

test('reentrant disposal and a failed frame cancellation never revive camera work',async()=>{
  let initialized=0,session;
  session=Session.create({views,initialize:async()=>{initialized++;return renderer();},onState:s=>{if(s.state==='loading')session.dispose();}});
  assert.equal(await session.start(),false);assert.equal(initialized,0);assert.equal(session.snapshot().state,'disposed');
  const clock=fakeClock(),r=renderer();clock.cancelFrame=()=>{throw new Error('synthetic cancel');};
  const active=Session.create({views,clock,reducedMotion:false,initialize:async()=>r});await active.start();active.selectView('b');
  active.setVisibility(false);const calls=r.calls.camera.length;clock.step(1000);
  assert.equal(r.calls.camera.length,calls);assert.equal(active.snapshot().state,'paused');assert.ok(active.snapshot().diagnostics.includes('clock_cancel_failed'));active.dispose();
});
