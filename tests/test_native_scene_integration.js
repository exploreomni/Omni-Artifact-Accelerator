"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
for(const name of ["native_scene_contract","native_scene_geometry","native_scene_textures","spatial_controller","native_scene_data","native_scene_renderer","native_scene_host"])
  require(`../skills/omni-app-engineer/scripts/${name}.js`);
require("../skills/omni-app-engineer/assets/native-scene-examples.js");
const E=OAANativeSceneExamples;
function dataSetup(onState=()=>{},now=()=>Date.parse("2026-10-23T12:00:00Z"),freshness={maxAgeMs:60000}){
  const scene=E.network(),selected=[],contract={queryId:"exact_saved_query",keyField:"assets.entity_key",grain:"one row per network node",
    ...freshness,fields:[{id:"telemetry.pressure",type:"number",unit:"kPa",aggregation:"latest observed at selected instant"}],
    bindings:scene.entities.filter(e=>e.role==="analytical").map(e=>({entityId:e.id,dataKey:e.id}))};
  const bridge=OAANativeSceneData.create({scene,contract,renderer:{setSelection:id=>selected.push(id)},onState,now});
  const sample={queryId:contract.queryId,status:"ready",complete:true,capturedAt:"2026-10-23T11:59:50Z",
    rows:contract.bindings.map((b,i)=>({"assets.entity_key":b.dataKey,"telemetry.pressure":i===1?null:i*10}))};
  return {bridge,sample,selected};
}
test("distinct scene examples meet bounded contract; source dimensions match independent product brief",()=>{
  for(const name of ["venue","network","product"]){const result=OAANativeSceneContract.validate(E[name]());assert.ok(result.budget.expandedTriangles>0);}
  const p=E.product(),body=OAANativeSceneGeometry.build(p.geometries[0]);
  const x=[],y=[];for(let i=0;i<body.positions.length;i+=3){x.push(body.positions[i]);y.push(body.positions[i+1]);}
  assert.ok(Math.abs(Math.max(...x)-Math.min(...x)-0.24)<0.001);
  assert.ok(Math.abs(Math.max(...y)-Math.min(...y)-0.4)<0.001);
  assert.equal(OAANativeSceneData.create({scene:E.venue()}),null);
  assert.throws(()=>OAANativeSceneData.create({scene:E.venue(),contract:{}}));
});
test("exact field identity, selection and stale generation survive data refresh; errors clear prior values",()=>{
  const {bridge:b,sample,selected}=dataSetup();b.select("consumer");const old=b.begin(),token=b.begin();
  assert.deepEqual(b.resolve(old,{bad:true}),{ignored:true});b.resolve(token,sample);
  assert.equal(b.snapshot().selection,"consumer");assert.equal(b.snapshot().values.supply["telemetry.pressure"],0);
  assert.equal(b.snapshot().values.junction_a["telemetry.pressure"],null);assert.deepEqual(selected,["consumer"]);
  sample.rows[0]={"entity_key":"supply","pressure":99};
  assert.throws(()=>b.resolve(b.begin(),sample));assert.equal(b.snapshot().dataStatus,"error");assert.deepEqual(b.snapshot().values,{});
});
test("partial, wrong query, expired and denied results cannot silently become ready",()=>{
  const {bridge:b,sample}=dataSetup();
  for(const patch of [{complete:false},{queryId:"other"},{capturedAt:"2026-10-23T14:00:00Z"}]){
    assert.throws(()=>b.resolve(b.begin(),{...sample,...patch}));assert.equal(b.snapshot().dataStatus,"error");
  }
  b.resolve(b.begin(),{...sample,capturedAt:"2026-10-23T11:00:00Z"});assert.equal(b.snapshot().dataStatus,"stale");
  b.resolve(b.begin(),{...sample,status:"restricted",rows:[]});assert.deepEqual(b.snapshot().values,{});
  b.dispose();assert.throws(()=>b.begin());
});
test("a failing UI observer cannot turn valid query results into a data error",()=>{
  const {bridge:b,sample}=dataSetup(state=>{if(state.dataStatus==="ready")throw new Error("display failure");});
  b.resolve(b.begin(),sample);assert.equal(b.snapshot().dataStatus,"ready");assert.equal(b.snapshot().values.supply["telemetry.pressure"],0);
  assert.deepEqual(b.snapshot().diagnostics,["on_state_failed"]);
});
test("freshness expires without a new query result and the host can announce it",()=>{
  let time=Date.parse("2026-10-23T12:00:00Z");const states=[];
  const {bridge:b,sample}=dataSetup(state=>states.push(state),()=>time);
  b.resolve(b.begin(),sample);assert.equal(b.snapshot().dataStatus,"ready");
  time+=50000;assert.equal(b.snapshot().dataStatus,"ready");
  time+=1;assert.equal(b.snapshot().dataStatus,"stale");b.checkFreshness();assert.equal(states.at(-1).dataStatus,"stale");
  assert.equal(b.snapshot().values.consumer["telemetry.pressure"],20);
});
test("absent or null expiry accepts historical snapshots without weakening data protections",()=>{
  for(const freshness of [{},{maxAgeMs:null}]){
    let time=Date.parse("2026-10-23T12:00:00Z");const states=[];
    const {bridge:b,sample}=dataSetup(state=>states.push(state),()=>time,freshness);
    sample.capturedAt="2026-10-20T12:00:00Z";
    b.select("consumer");const old=b.begin(),current=b.begin();
    assert.deepEqual(b.resolve(old,{bad:true}),{ignored:true});b.resolve(current,sample);
    time+=86400000*2;assert.equal(b.checkFreshness().dataStatus,"ready");
    assert.equal(states.at(-1).dataStatus,"ready");assert.equal(b.snapshot().selection,"consumer");
    assert.equal(b.snapshot().values.supply["telemetry.pressure"],0);
    assert.equal(b.snapshot().values.junction_a["telemetry.pressure"],null);
    for(const patch of [{complete:false},{queryId:"other"},{capturedAt:"invalid"},
      {capturedAt:new Date(time+6000).toISOString()}]){
      assert.throws(()=>b.resolve(b.begin(),{...sample,...patch}));
      assert.equal(b.snapshot().dataStatus,"error");assert.deepEqual(b.snapshot().values,{});
    }
    b.resolve(b.begin(),{...sample,status:"stale"});assert.equal(b.snapshot().dataStatus,"stale");
    for(const status of ["error","restricted"]){
      b.resolve(b.begin(),sample);b.resolve(b.begin(),{...sample,status,rows:[]});
      assert.equal(b.snapshot().dataStatus,status);assert.deepEqual(b.snapshot().values,{});
    }
    b.resolve(b.begin(),sample);time=NaN;assert.equal(b.snapshot().dataStatus,"stale");
    const count=states.length;b.dispose();b.checkFreshness();assert.equal(states.length,count+1);
    assert.throws(()=>b.begin());
  }
});
test("invalid explicit expiry limits are rejected rather than treated as no policy",()=>{
  for(const maxAgeMs of [0,-1,NaN,Infinity,"60000",false,0.5,86400001]){
    assert.throws(()=>dataSetup(undefined,undefined,{maxAgeMs}),/invalid freshness limit/);
  }
});

function target(){const events=new Map();return {events,addEventListener(n,f){if(!events.has(n))events.set(n,new Set());events.get(n).add(f);},removeEventListener(n,f){events.get(n)?.delete(f);},emit(n,event={}){for(const f of [...(events.get(n)||[])])f(event);}};}
function environment(){
  const observers=[],win=Object.assign(target(),{devicePixelRatio:2});
  class Observer{constructor(fn){this.fn=fn;this.disconnected=false;observers.push(this);}observe(node){this.node=node;}disconnect(){this.disconnected=true;}}
  win.ResizeObserver=Observer;win.IntersectionObserver=Observer;
  const media=Object.assign(target(),{matches:false});win.matchMedia=()=>media;
  const doc=Object.assign(target(),{hidden:false,defaultView:win});
  const attrs=new Map(),canvas=Object.assign(target(),{ownerDocument:doc,setAttribute:(k,v)=>attrs.set(k,v),getAttribute:k=>attrs.get(k)??null,removeAttribute:k=>attrs.delete(k)});
  const container={getBoundingClientRect:()=>({width:900,height:500})},calls=[];
  const session={};for(const key of ["resize","setVisibility","interrupt","setOffscreen","setReducedMotion","dispose"])session[key]=(...args)=>calls.push([key,...args]);
  return {win,doc,canvas,container,session,calls,media,observers,attrs};
}
test("DOM ownership respects inactive page, live reduced motion and disconnects observers/listeners",()=>{
  const e=environment(),host=OAANativeSceneHost.connect(e);host.setActive(false);
  e.doc.hidden=true;e.doc.emit("visibilitychange");e.doc.hidden=false;e.doc.emit("visibilitychange");
  assert.deepEqual(e.calls.filter(x=>x[0]==="setVisibility").at(-1),["setVisibility",false]);
  e.media.matches=true;e.media.emit("change");assert.deepEqual(e.calls.at(-1),["setReducedMotion",true]);
  e.canvas.emit("wheel");assert.deepEqual(e.calls.at(-1),["interrupt"]);
  host.dispose();host.dispose();assert.equal(e.calls.filter(x=>x[0]==="dispose").length,1);assert.ok(e.observers.every(o=>o.disconnected));
  assert.equal(e.attrs.has("tabindex"),false);const n=e.calls.length;e.doc.emit("visibilitychange");e.media.emit("change");assert.equal(e.calls.length,n);
});

function engineDouble(failMaterial=false){
  const allocations=[],disposed=[],render=[];
  class Resource{constructor(type){this.type=type;allocations.push(this);}dispose(){disposed.push(this);}}
  class V{constructor(x=0,y=0,z=0){this.set(x,y,z);}set(x,y,z){this.x=x;this.y=y;this.z=z;return this;}toArray(){return [this.x,this.y,this.z];}length(){return Math.hypot(this.x,this.y,this.z);}}
  class Object3D{constructor(){this.position=new V();this.rotation=new V();this.scale=new V(1,1,1);this.children=[];this.userData={};}add(...children){this.children.push(...children);}updateMatrixWorld(){}}
  class Geometry extends Resource{constructor(){super("geometry");}setAttribute(){}setIndex(){}computeBoundingSphere(){}}
  class Material extends Resource{constructor(){super("material");if(failMaterial)throw new Error("injected material failure");}}
  class Camera extends Object3D{constructor(fov,aspect,near,far){super();Object.assign(this,{fov,aspect,near,far});}updateProjectionMatrix(){}}
  class GPU extends Resource{constructor(){super("gpu");this.shadowMap={};this.sizes=[];}setPixelRatio(){throw new Error("non-atomic backing resize forbidden");}setSize(){throw new Error("non-atomic backing resize forbidden");}setDrawingBufferSize(w,h,ratio){this.size=[w*ratio,h*ratio];this.sizes.push(this.size);}render(){render.push(1);}forceContextLoss(){}}
  class Box{setFromObject(){return this;}getCenter(v){return v;}getSize(v){return v.set(1,1,1);}}
  class Helper extends Object3D{constructor(box){super();this.box=box;this.geometry=new Geometry();this.material=new Material();}}
  class Texture extends Resource{constructor(image){super("texture");this.image=image;}}
  class Controls{constructor(camera){Object.assign(this,target());this.target=new V();this.camera=camera;allocations.push(this);}listenToKeyEvents(){}update(){this.emit("change");}dispose(){disposed.push(this);}}
  const T={REVISION:"186",Scene:Object3D,Color:class{},PerspectiveCamera:Camera,WebGLRenderer:GPU,HemisphereLight:Object3D,DirectionalLight:Object3D,
    BufferGeometry:Geometry,BufferAttribute:class{},CanvasTexture:Texture,MeshStandardMaterial:Material,Mesh:Object3D,Box3Helper:Helper,Box3:Box,
    Vector3:V,Vector2:V,Raycaster:class{setFromCamera(){}intersectObjects(){return [];}},SRGBColorSpace:"srgb"};
  const canvas=Object.assign(target(),{getBoundingClientRect:()=>({width:500,height:300,left:0,top:0}),ownerDocument:{createElement(){return {getContext:()=>({save(){},restore(){},fillRect(){},fillText(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},measureText:()=>({width:10})})};}}});
  return {T,Controls,canvas,allocations,disposed,render};
}
test("adapter rejects unknown engine and oversized scene before GPU allocation",()=>{
  const e=engineDouble(),scene=E.network();assert.throws(()=>OAANativeSceneRenderer.mount({canvas:e.canvas,scene,THREE:{REVISION:"128"},OrbitControls:e.Controls}));
  scene.render.width=100000;assert.throws(()=>OAANativeSceneRenderer.mount({canvas:e.canvas,scene,THREE:e.T,OrbitControls:e.Controls}));
  assert.equal(e.allocations.length,0);
});
test("adapter shares geometry, bounds resize, handles selection/context loss and disposes once",()=>{
  const e=engineDouble(),scene=E.network();let losses=0;
  const r=OAANativeSceneRenderer.mount({canvas:e.canvas,scene,THREE:e.T,OrbitControls:e.Controls,onContextLost:()=>losses++});
  assert.equal(e.allocations.filter(x=>x.type==="geometry").length,scene.geometries.length+1);
  r.setSelection("supply");assert.equal(r.snapshot().selection,"supply");r.resize(5000,2500,2);
  const gpu=e.allocations.find(x=>x.type==="gpu");assert.ok(gpu.size.every(x=>x<=4096));assert.ok(gpu.size[0]*gpu.size[1]<=1280*720+1);
  r.resize(1280,720,1);assert.ok(gpu.sizes.every(pair=>pair.every(x=>x<=4096)&&pair[0]*pair[1]<=1280*720+1));
  e.canvas.emit("webglcontextlost",{preventDefault(){}});assert.equal(losses,1);assert.throws(()=>r.setSelection(null));
  r.dispose();r.dispose();assert.equal(new Set(e.disposed).size,e.disposed.length);assert.ok(e.allocations.every(x=>e.disposed.includes(x)));
});
test("failed initialization releases prior GPU, geometry and controls",()=>{
  const e=engineDouble(true);assert.throws(()=>OAANativeSceneRenderer.mount({canvas:e.canvas,scene:E.network(),THREE:e.T,OrbitControls:e.Controls}));
  assert.ok(e.allocations.filter(x=>x.type!=="material").every(x=>e.disposed.includes(x)));
});
test("admitted close views initialize and aspect-aware fit expands for narrow space",()=>{
  const e=engineDouble(),scene=E.product();scene.views[0].position=[0,0,0.0005];scene.views[0].target=[0,0,0];
  const r=OAANativeSceneRenderer.mount({canvas:e.canvas,scene,THREE:e.T,OrbitControls:e.Controls});assert.equal(r.getCamera().position[2],0.0005);r.dispose();
  const bounds={center:[0,0,0],radius:2},wide=OAANativeSceneRenderer.fitCamera(bounds,2),narrow=OAANativeSceneRenderer.fitCamera(bounds,0.25);
  assert.ok(Math.hypot(...narrow.position)>Math.hypot(...wide.position)*3);
  const h=2*Math.atan(Math.tan(Math.PI/8)*0.25);assert.ok(Math.hypot(...narrow.position)*Math.sin(h/2)>2);
  assert.throws(()=>OAANativeSceneRenderer.fitCamera({center:[0,0,0],radius:450000},1),/controls distance/);
});
