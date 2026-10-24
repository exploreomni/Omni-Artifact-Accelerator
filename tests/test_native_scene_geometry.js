/* Bounded first-party source/math tests. No renderer/browser/packages/assets. */
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,".."),scripts=path.join(root,"skills/omni-app-engineer/scripts");
for(const name of ["native_scene_contract.js","native_scene_geometry.js","native_scene_textures.js"])
  vm.runInThisContext(fs.readFileSync(path.join(scripts,name),"utf8"),{filename:name});
const C=globalThis.OAANativeSceneContract,G=globalThis.OAANativeSceneGeometry,T=globalThis.OAANativeSceneTextures;
const clone=x=>JSON.parse(JSON.stringify(x));
const box={id:"Box",kind:"box",width:2,height:3,depth:4};
function entity(id="Object"){return {id,label:id,geometry:"Box",material:"Mat",position:[0,0,0],rotation:[0,0,0],scale:[1,1,1],role:"decorative"};}
function scene(){return {schema_version:"oaa-native-scene-v1",units:"m",axes:"right-handed-y-up",fidelity:{kind:"illustrative",source:"Original test dimensions",notes:"No measured asset or analytical binding"},materials:[{id:"Mat",label:"Surface",color:"#AAbbCC",roughness:0.5,metalness:0}],geometries:[clone(box)],entities:[entity()],views:[],render:{width:301,height:127,dpr:1.25,shadows:false}};}
const sub=(a,b)=>a.map((x,i)=>x-b[i]),dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const tests=[];function test(name,fn){fn();tests.push(name);}
function inspectMesh(mesh){
  const {positions:p,normals:n,uvs:uv,indices:ix}=mesh;assert.equal(p.length,n.length);assert.equal(uv.length/2,p.length/3);
  for(const a of [p,n,uv])for(const v of a)assert(Number.isFinite(v));
  for(let i=0;i<n.length;i+=3)assert(Math.abs(Math.hypot(n[i],n[i+1],n[i+2])-1)<2e-6,"unit normal");
  for(const v of uv)assert(v>=-1e-6&&v<=1+1e-6,"UV range");
  for(let i=0;i<ix.length;i+=3){const ids=[ix[i],ix[i+1],ix[i+2]];for(const id of ids)assert(id<p.length/3);
    const points=ids.map(id=>Array.from(p.subarray(id*3,id*3+3))),face=cross(sub(points[1],points[0]),sub(points[2],points[0]));
    assert(Math.hypot(...face)>1e-8,"nondegenerate triangle");
    const normal=[0,1,2].map(axis=>ids.reduce((sum,id)=>sum+n[id*3+axis],0));assert(dot(face,normal)>1e-8,"winding agrees with outward normals");}
}
test("Five geometry families have finite unit normals, UVs and outward winding",()=>{
  const shapes=[box,{id:"Cone",kind:"cylinder",radiusTop:0,radiusBottom:1,height:2,radialSegments:12,capped:true},
    {id:"ReverseCone",kind:"cylinder",radiusTop:1,radiusBottom:0,height:2,radialSegments:12,capped:false},
    {id:"Cylinder",kind:"cylinder",radiusTop:1,radiusBottom:1,height:2,radialSegments:12,capped:true},
    {id:"Prism",kind:"extrusion",points:[[-1,-1],[2,-1],[2,1],[-1,1]],height:2},
    {id:"Tube",kind:"tube",path:[[0,0,0],[0,2,0],[2,3,0],[3,3,2]],radius:0.1,radialSegments:12,capped:true},
    {id:"Lathe",kind:"revolution",profile:[[0,-1],[0.8,-0.5],[1,0.4],[0.5,1],[0,1.5]],radialSegments:16,capped:true}];
  for(const shape of shapes){const mesh=G.build(shape);inspectMesh(mesh);const b=C.geometryInfo(shape).budget;
    assert.equal(mesh.positions.length/3,b.vertices);assert.equal(mesh.indices.length/3,b.triangles);assert.equal(mesh.positions.byteLength+mesh.normals.byteLength+mesh.uvs.byteLength+mesh.indices.byteLength,b.geometryBytes);}
  const mesh=G.build(box);for(let axis=0;axis<3;axis++){const values=Array.from(mesh.positions).filter((_,i)=>i%3===axis),size=[2,3,4][axis];assert.equal(Math.min(...values),-size/2);assert.equal(Math.max(...values),size/2);}
});
test("Known prism volume and capped cylinder volume have positive signed orientation",()=>{
  function volume(m){let total=0;for(let i=0;i<m.indices.length;i+=3){const p=[0,1,2].map(k=>Array.from(m.positions.subarray(m.indices[i+k]*3,m.indices[i+k]*3+3)));total+=dot(p[0],cross(p[1],p[2]))/6;}return total;}
  assert(Math.abs(volume(G.build(box))-24)<1e-7);
  assert(Math.abs(volume(G.build({id:"Prism",kind:"extrusion",points:[[-1,-1],[2,-1],[2,1],[-1,1]],height:2}))-12)<1e-7);
  const n=16;assert(Math.abs(volume(G.build({id:"Cylinder",kind:"cylinder",radiusTop:1,radiusBottom:1,height:2,radialSegments:n,capped:true}))-n*Math.sin(2*Math.PI/n))<1e-5);
});
test("Admission copies/freezes normalized data and accounts for mipmaps, backing pixels and selection",()=>{
  const input=scene();input.materials[0].texture={kind:"grid",size:16,background:"#ffffff",foreground:"#000000",repeat:4};
  const {scene:s,budget:b}=C.validate(input);assert(Object.isFrozen(s)&&Object.isFrozen(s.entities[0].position)&&Object.isFrozen(b));assert.equal(s.materials[0].color,"#aabbcc");
  input.entities[0].position[0]=99;assert.equal(s.entities[0].position[0],0);assert.equal(b.textureBytes,4*(256+64+16+4+1));assert.equal(b.backingWidth,377);assert.equal(b.backingHeight,159);
  assert.equal(b.backbufferBytes,377*159*8);assert.equal(b.selectionBytes,4096);assert.equal(b.estimatedGpuBytes,b.geometryBytes+b.textureBytes+b.backbufferBytes+4096);assert.equal(b.expandedTriangles,12);
});
test("Malformed/passive boundaries reject unknown fields, URLs, accessors, prototypes and functions",()=>{
  const changes=[s=>s.url="https://invalid.example",s=>s.materials[0].texture={kind:"grid",size:16,background:"#ffffff",foreground:"#000000",repeat:2,url:"x"},
    s=>s.fidelity.source="//invalid.example",s=>s.entities[0].position[0]=Infinity,s=>s.entities[0].scale[0]=0,s=>s.entities[0].role="script",
    s=>s.entities[0].binding={},s=>s.render.shadows=true,s=>s.render.target={},s=>s.geometries[0].code=()=>0,s=>Object.setPrototypeOf(s.materials[0],{extra:true})];
  for(const change of changes){const s=scene();change(s);assert.throws(()=>C.validate(s));}
  let called=false;const s=scene();Object.defineProperty(s.entities[0],"label",{get(){called=true;return "unsafe";},enumerable:true});assert.throws(()=>C.validate(s),/no_accessors/);assert.equal(called,false);
  const symbolic=scene();symbolic[Symbol("hidden")]=1;assert.throws(()=>C.validate(symbolic));
});
test("Hierarchy references, cycles, depth, cumulative scales and world bounds are checked",()=>{
  const mutations=[s=>s.entities[0].parent="Missing",s=>s.entities[0].parent="Object",
    s=>{s.entities=[entity("A"),entity("B")];s.entities[0].parent="B";s.entities[1].parent="A";},
    s=>{s.entities=Array.from({length:33},(_,i)=>entity("Node"+i));s.entities.forEach((e,i)=>{if(i)e.parent="Node"+(i-1);});},
    s=>{s.entities=[entity("A"),entity("B")];s.entities[1].parent="A";s.entities.forEach(e=>e.scale=[1000,1000,1000]);},
    s=>{s.entities=[entity("A"),entity("B")];s.entities[0].scale=[100,100,100];s.entities[1].position=[10000,10000,10000];s.entities[1].parent="A";}];
  for(const change of mutations){const s=scene();change(s);assert.throws(()=>C.validate(s));}
  const s=scene();s.entities.push({...entity("Child"),parent:"Object",position:[2,0,0]});assert.equal(C.validate(s).budget.hierarchyDepth,2);
});
test("Geometry ambiguity and degenerate paths fail before mesh allocation",()=>{
  for(const g of [{id:"Prism",kind:"extrusion",points:[[0,0],[0,1],[1,1],[1,0]],height:1},
    {id:"Concave",kind:"extrusion",points:[[0,0],[2,0],[1,0.2],[2,2],[0,2]],height:1},
    {id:"Tube",kind:"tube",path:[[0,0,0],[1,0,0],[0,0,0]],radius:0.1,radialSegments:8,capped:true},
    {id:"Tube",kind:"tube",path:[[0,0,0],[0.1,0,0]],radius:0.1,radialSegments:8,capped:true},
    {id:"Lathe",kind:"revolution",profile:[[1,0],[2,-1]],radialSegments:8,capped:true},
    {id:"FarTube",kind:"tube",path:[[10000,10000,10000],[9999,10000,10000]],radius:0.0001,radialSegments:16,capped:true},
    {id:"FarProfile",kind:"revolution",profile:[[1,9999],[1,9999.0002]],radialSegments:16,capped:true},
    {id:"FarPrism",kind:"extrusion",points:[[9999,0],[9999.0002,0],[9999.0002,1],[9999,1]],height:1}])assert.throws(()=>G.build(g));
});
test("Unique/expanded triangle, texture and backing-size budgets reject combined demand",()=>{
  const lathe={id:"Lathe",kind:"revolution",profile:Array.from({length:64},(_,i)=>[1,i/10]),radialSegments:128,capped:true};
  const unique=scene();unique.geometries=Array.from({length:7},(_,i)=>({...clone(lathe),id:"Lathe"+i}));unique.entities[0].geometry="Lathe0";assert.throws(()=>C.validate(unique),/unique_geometry_budget/);
  const expanded=scene();expanded.geometries=[lathe];expanded.entities=Array.from({length:13},(_,i)=>({...entity("E"+i),geometry:"Lathe"}));assert.throws(()=>C.validate(expanded),/expanded_triangle_budget/);
  const textures=scene();textures.materials[0].texture={kind:"grid",size:2048,repeat:2,background:"#ffffff",foreground:"#000000"};textures.materials.push({...clone(textures.materials[0]),id:"Second"});assert.throws(()=>C.validate(textures),/texture_budget/);
  const backing=scene();backing.render={width:4096,height:100,dpr:2,shadows:false};assert.throws(()=>C.validate(backing),/backing_dimensions/);
});
test("Canvas recipes remain deterministic local draw commands and reject before resize",()=>{
  for(const kind of ["stripes","grid","panels","label"]){const calls=[],ctx={save(){calls.push("save");},restore(){calls.push("restore");},fillRect(...a){assert(a.every(Number.isFinite));calls.push(["rect",...a]);},fillText(...a){calls.push(["text",...a]);}};
    const canvas={width:0,height:0,getContext(type){assert.equal(type,"2d");return ctx;}},r={kind,size:64,background:"#ffffff",foreground:"#000000",repeat:4};if(kind==="label")r.label="Illustrative panel";
    assert.equal(T.paint(r,canvas),canvas);assert.equal(canvas.width,64);assert.equal(canvas.height,64);assert.equal(calls[0],"save");assert.equal(calls.at(-1),"restore");if(kind==="label")assert.equal(calls.filter(x=>Array.isArray(x)&&x[0]==="text").length,4);}
  const canvas={width:7,height:9,getContext(){throw new Error("must not allocate");}};
  assert.throws(()=>T.paint({kind:"label",size:16,background:"#ffffff",foreground:"#000000",repeat:1,label:"https://invalid.example"},canvas),/plain_text/);assert.equal(canvas.width,7);
});
console.log(JSON.stringify({passed:tests.length,tests,rendered:false,native:false,qualification:"source_math_and_canvas_commands_only"},null,2));
