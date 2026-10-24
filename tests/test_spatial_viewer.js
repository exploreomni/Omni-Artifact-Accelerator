'use strict';
// Original synthetic inputs; built-in Node modules and first-party source only.
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const V = require('../harness/viewer.js');

function fixture(change = () => {}, jsonChange = x => x) {
  const binary = Buffer.alloc(84);
  [0,0,0, 1,0,0, 0,1,0, 0,0,1, 0,0,1, 0,0,1].forEach((n,i)=>binary.writeFloatLE(n,i*4));
  [0,1,2].forEach((n,i)=>binary.writeUInt32LE(n,72+i*4));
  const views=[{id:'face',label:'Face inspection',position:[0.5,0.5,3],target:[0.5,0.5,0],up:[0,1,0]}];
  const doc={asset:{version:'2.0',generator:'OAA original SceneSpec compiler 1'},scene:0,
    scenes:[{nodes:[0],extras:{units:'m',axes:'right-handed-y-up',views}}],
    nodes:[{name:'Panel',mesh:0,translation:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1],extras:{entity_id:'panel'}}],
    meshes:[{primitives:[{attributes:{POSITION:0,NORMAL:1},indices:2,mode:4,material:0}],extras:{geometry_id:'triangle'}}],
    materials:[{name:'blue',pbrMetallicRoughness:{baseColorFactor:[0.1,0.3,0.8,1],metallicFactor:0,roughnessFactor:0.7}}],
    accessors:[{bufferView:0,componentType:5126,count:3,type:'VEC3',min:[0,0,0],max:[1,1,0]},
      {bufferView:1,componentType:5126,count:3,type:'VEC3'}, {bufferView:2,componentType:5125,count:3,type:'SCALAR'}],
    bufferViews:[{buffer:0,byteOffset:0,byteLength:36,target:34962},{buffer:0,byteOffset:36,byteLength:36,target:34962},{buffer:0,byteOffset:72,byteLength:12,target:34963}],
    buffers:[{byteLength:84}]};
  const manifest={schema_version:1,profile:V.PROFILE,asset_sha256:'',asset_bytes:0,scene_sha256:'0'.repeat(64),input_sha256:'0'.repeat(64),units:'m',axes:'right-handed-y-up',
    counts:{triangles:1,vertices:3,expanded_triangles:1,entities:1},bounds:{min:[0,0,0],max:[1,1,0]},
    entities:[{id:'panel',node:0,mesh:0,geometry:'triangle',material:'blue',bounds:{min:[0,0,0],max:[1,1,0]}}],views:JSON.parse(JSON.stringify(views)),
    provenance:{generator:'original-repository-source',textures:false,imported_assets:false},
    qualification:{rendered:'not_assessed',native:'not_assessed',isolation:'not_established_by_compiler'}};
  change(doc,manifest,binary);
  let json=Buffer.from(jsonChange(JSON.stringify(doc)),'utf8'); json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
  const glb=Buffer.alloc(28+json.length+binary.length);
  [0x46546c67,2,glb.length,json.length,0x4e4f534a].forEach((n,i)=>glb.writeUInt32LE(n,i*4)); json.copy(glb,20);
  glb.writeUInt32LE(binary.length,20+json.length);glb.writeUInt32LE(0x004e4942,24+json.length);binary.copy(glb,28+json.length);
  manifest.asset_bytes=glb.length;manifest.asset_sha256=crypto.createHash('sha256').update(glb).digest('hex');
  return {glb,manifest};
}
function fakeGL() {
  const calls={draws:0,deletedBuffers:0,deletedShaders:0,deletedPrograms:0,uploads:0};
  const gl={calls,VERTEX_SHADER:1,FRAGMENT_SHADER:2,COMPILE_STATUS:3,LINK_STATUS:4,ARRAY_BUFFER:5,STATIC_DRAW:6,DEPTH_TEST:7,CULL_FACE:8,FLOAT:9,TRIANGLES:10,COLOR_BUFFER_BIT:16,DEPTH_BUFFER_BIT:32,
    createProgram:()=>({}),createShader:()=>({}),createBuffer:()=>({}),
    getShaderParameter:()=>true,getProgramParameter:()=>true,getAttribLocation:(_,name)=>name==='aPosition'?0:1,getUniformLocation:(_,name)=>({name}),
    deleteBuffer:()=>calls.deletedBuffers++,deleteShader:()=>calls.deletedShaders++,deleteProgram:()=>calls.deletedPrograms++,
    bufferData:()=>calls.uploads++,drawArrays:()=>calls.draws++};
  for(const method of ['shaderSource','compileShader','attachShader','linkProgram','enable','disable','bindBuffer','viewport','clearColor','clear','useProgram','uniformMatrix4fv','vertexAttribPointer','enableVertexAttribArray','uniform4fv','uniform1f'])gl[method]=()=>{};
  return gl;
}
function fakeCanvas(gl=fakeGL()) {
  const events=new Map(), attrs=new Map(), captures=new Set();
  return {gl,events,attrs,captures,width:1,height:1,rect:{left:0,top:0,width:500,height:250},ownerDocument:{defaultView:{devicePixelRatio:3}},
    getContext:()=>gl,addEventListener:(type,fn)=>events.set(type,fn),removeEventListener:type=>events.delete(type),
    getAttribute:key=>attrs.has(key)?attrs.get(key):null,setAttribute:(key,value)=>attrs.set(key,value),removeAttribute:key=>attrs.delete(key),
    getBoundingClientRect(){return this.rect;},setPointerCapture:id=>captures.add(id),hasPointerCapture:id=>captures.has(id),releasePointerCapture:id=>captures.delete(id),focus:()=>{},
    emit(type,props={}){const fn=events.get(type);if(fn)fn({preventDefault(){},...props});}};
}

test('actual isolated Python producer output is accepted with its required input digest',()=>{
  const source = [
    'import base64, hashlib, json, sys',
    'from pathlib import Path',
    'sys.path.insert(0, str(Path.cwd()))',
    'from harness.model_core import compile_scene',
    'spec = {"schema_version":1,"units":"m","axes":"right-handed-y-up",',
    ' "materials":[{"id":"neutral","base_color":[0.3,0.4,0.5,1],"metallic":0,"roughness":0.7}],',
    ' "geometries":[{"id":"box","type":"box","size":[2,4,6]}],',
    ' "entities":[{"id":"object","label":"Original box","geometry":"box","material":"neutral","transform":{"translation":[10,0,0]}}],',
    ' "views":[{"id":"front","label":"Front","position":[10,0,12],"target":[10,0,0],"up":[0,1,0]}]}',
    'result = compile_scene(spec)',
    'canonical = json.dumps(spec, sort_keys=True, separators=(",",":"), ensure_ascii=True, allow_nan=False).encode()',
    'print(json.dumps({"glb":base64.b64encode(result["glb"]).decode(),"manifest":result["manifest"],"expected_input_sha256":hashlib.sha256(canonical).hexdigest()}))'
  ].join('\n');
  const run=spawnSync('python3',['-I','-S','-B','-c',source],{
    cwd:path.resolve(__dirname,'..'),env:{PATH:process.env.PATH},encoding:'utf8',timeout:10000,maxBuffer:1048576,shell:false
  });
  assert.ifError(run.error);assert.equal(run.status,0,run.stderr);
  const emitted=JSON.parse(run.stdout), glb=Buffer.from(emitted.glb,'base64'), manifest=emitted.manifest;
  assert.equal(manifest.asset_sha256,crypto.createHash('sha256').update(glb).digest('hex'));
  assert.equal(manifest.input_sha256,emitted.expected_input_sha256);
  const model=V.parse(glb,manifest);
  assert.deepEqual(model.counts,{triangles:12,vertices:36,expanded_triangles:12,entities:1});
  assert.deepEqual(model.bounds,{min:[9,-2,-3],max:[11,2,3]});
  assert.equal(model.entities[0].id,'object');assert.equal(model.views[0].id,'front');
  const missing={...manifest};delete missing.input_sha256;assert.throws(()=>V.parse(glb,missing),/unknown or missing fields/);
  assert.throws(()=>V.parse(glb,{...manifest,input_sha256:'not-a-digest'}),/manifest hash format/);
});

test('strict original triangle parses with preserved identity and independent byte snapshot',()=>{
  const input=fixture(), model=V.parse(input.glb,input.manifest);
  assert.deepEqual(model.counts,{triangles:1,vertices:3,expanded_triangles:1,entities:1});
  assert.deepEqual(model.bounds,{min:[0,0,0],max:[1,1,0]}); assert.equal(model.entities[0].id,'panel');
  input.glb.fill(0);assert.equal(model.entities[0].positions[3],1);
});

test('malformed profile fields, references and binary content fail closed',()=>{
  const mutations=[
    d=>{d.buffers[0].uri='https://invalid.example/mesh.bin';},
    d=>{d.meshes[0].primitives[0].material=20;},
    d=>{d.accessors[0].bufferView=99;},
    d=>{d.bufferViews[1].byteOffset=0;},
    d=>{d.nodes[0].children=null;},
    d=>{d.extensionsUsed=['unapproved'];},
    (d,m,b)=>{b.writeUInt32LE(12,72);},
    (d,m,b)=>{b.writeFloatLE(NaN,0);},
    d=>{d.nodes[0].scale=[-1,1,1];}
  ];
  for(const mutation of mutations){const input=fixture(mutation);assert.throws(()=>V.parse(input.glb,input.manifest),/OAA viewer:/);}
  const duplicate=fixture(()=>{},x=>x.replace('"scene":0','"scene":0,"scene":0'));
  assert.throws(()=>V.parse(duplicate.glb,duplicate.manifest),/duplicate JSON key/);
  const length=fixture();length.glb.writeUInt32LE(length.glb.length-4,8);assert.throws(()=>V.parse(length.glb,length.manifest),/header/);
});

test('manifest IDs/views are checked against the asset; getters are never invoked',()=>{
  let input=fixture();input.manifest.entities[0].id='substitute';assert.throws(()=>V.parse(input.glb,input.manifest),/entity mismatch/);
  input=fixture();input.manifest.views[0].target=[0,0,4];assert.throws(()=>V.parse(input.glb,input.manifest),/camera mismatch/);
  input=fixture();input.manifest.approved=true;assert.throws(()=>V.parse(input.glb,input.manifest),/unknown or missing/);
  input=fixture();let ran=false;Object.defineProperty(input.manifest,'profile',{enumerable:true,get(){ran=true;return V.PROFILE;}});
  assert.throws(()=>V.parse(input.glb,input.manifest),/manifest accessor/);assert.equal(ran,false);
});

test('hierarchical TRS preserves known world bounds and rejects a cyclic graph',()=>{
  const input=fixture((d,m)=>{
    d.nodes[0].translation=[2,0,0];d.nodes[0].children=[1];
    d.nodes.push({name:'Child',mesh:0,translation:[0,0,0],rotation:[0,0,0,1],scale:[2,1,1],extras:{entity_id:'child'}});
    m.counts.entities=2;m.counts.expanded_triangles=2;m.bounds={min:[2,0,0],max:[4,1,0]};m.entities[0].bounds={min:[2,0,0],max:[3,1,0]};
    m.entities.push({id:'child',node:1,mesh:0,geometry:'triangle',material:'blue',bounds:{min:[2,0,0],max:[4,1,0]}});
  });
  const model=V.parse(input.glb,input.manifest);assert.deepEqual(model.bounds,{min:[2,0,0],max:[4,1,0]});
  assert.deepEqual(Array.from(model.entities.find(e=>e.id==='child').positions.slice(3,6)),[4,0,0]);
  const canvas=fakeCanvas(), chosen=[], mounted=V.mount({...input,canvas,onSelect:x=>chosen.push(x)});
  canvas.emit('keydown',{key:'ArrowLeft'});canvas.emit('keydown',{key:'ArrowRight'});
  assert.deepEqual(chosen,['child','panel']);mounted.dispose();
  const bad=fixture(d=>{d.nodes[0].children=[0];});assert.throws(()=>V.parse(bad.glb,bad.manifest),/duplicate parent/);
  const m=V.math.trs({translation:[2,3,4],rotation:[0,0,Math.SQRT1_2,Math.SQRT1_2],scale:[2,1,1]});
  const p=V.math.point(m,[1,0,0]);assert.ok(Math.abs(p[0]-2)<1e-12&&Math.abs(p[1]-5)<1e-12&&p[2]===4);
});

test('perspective framing fits both aspects and a ray selects the actual triangle',()=>{
  const input=fixture(), model=V.parse(input.glb,input.manifest);
  for(const aspect of [0.5,2]){
    const c=V.math.fit(model,aspect), matrix=V.math.multiply(V.math.perspective(aspect,0.01,100),V.math.lookAt(c.position,c.target,c.up));
    for(const p of [[0,0,0],[1,0,0],[0,1,0],[1,1,0]]){
      const clip=[0,1,2,3].map(r=>matrix[r]*p[0]+matrix[4+r]*p[1]+matrix[8+r]*p[2]+matrix[12+r]);
      assert.ok(clip[3]>0&&Math.abs(clip[0]/clip[3])<1&&Math.abs(clip[1]/clip[3])<1);
    }
  }
  const camera={position:[1/3,1/3,3],target:[1/3,1/3,0],up:[0,1,0]};
  assert.equal(V.math.pick(model,V.math.ray(camera,0,0,1)),'panel');
  assert.equal(V.math.pick(model,V.math.ray(camera,1,1,1)),null);
});

test('actual mount API selects stable IDs, caps DPR, preserves controls and disposes once',()=>{
  const input=fixture(), canvas=fakeCanvas(), selected=[], status=[];
  const api=V.mount({...input,canvas,onSelect:x=>selected.push(x),onStatus:x=>status.push(x.state)});
  assert.deepEqual([canvas.width,canvas.height],[1000,500]);assert.equal(status[0],'ready');assert.equal(api.entities[0].label,'Panel');
  api.setCamera('face');api.setSelection('panel');assert.equal(selected.length,0);assert.throws(()=>api.setSelection('unknown'),/unknown entity/);
  canvas.emit('keydown',{key:'ArrowRight'});assert.deepEqual(selected,['panel']);
  canvas.rect={left:0,top:0,width:250,height:500};api.resize();assert.deepEqual([canvas.width,canvas.height],[500,1000]);
  api.setCamera('reset');api.setCamera(null);assert.throws(()=>api.setCamera('missing'),/unknown camera/);
  canvas.emit('pointerdown',{button:0,pointerId:7,clientX:20,clientY:20});assert.ok(canvas.captures.has(7));
  api.dispose();api.dispose();assert.equal(canvas.events.size,0);assert.equal(canvas.captures.size,0);assert.equal(canvas.attrs.has('tabindex'),false);
  assert.deepEqual([canvas.gl.calls.deletedBuffers,canvas.gl.calls.deletedShaders,canvas.gl.calls.deletedPrograms],[2,2,1]);
  const draws=canvas.gl.calls.draws;assert.equal(api.setCamera('face'),false);assert.equal(api.resize(),false);assert.equal(canvas.gl.calls.draws,draws);
  assert.equal(status.filter(x=>x==='disposed').length,1);
});

test('context loss stops drawing and restoration requires an explicit remount',()=>{
  const input=fixture(), canvas=fakeCanvas(), status=[];
  const api=V.mount({...input,canvas,onStatus:x=>status.push(x.state)}), before=canvas.gl.calls.draws;
  canvas.emit('webglcontextlost');assert.equal(api.setSelection('panel'),false);assert.equal(api.resize(),false);assert.equal(canvas.gl.calls.draws,before);
  canvas.emit('webglcontextrestored');assert.deepEqual(status,['ready','context_lost','remount_required']);
  api.dispose();assert.equal(canvas.events.size,0);
});

test('unsupported WebGL and partial shader failures report status and clean up',()=>{
  const input=fixture(), unsupported=fakeCanvas(null), states=[];
  assert.throws(()=>V.mount({...input,canvas:unsupported,onStatus:x=>states.push(x.state)}),/WebGL unavailable/);
  assert.deepEqual(states,['unsupported']);assert.equal(unsupported.attrs.size,0);
  const gl=fakeGL();gl.getShaderParameter=()=>false;const canvas=fakeCanvas(gl);
  assert.throws(()=>V.mount({...input,canvas}),/shader compilation/);
  assert.deepEqual([gl.calls.deletedShaders,gl.calls.deletedPrograms],[1,1]);assert.equal(canvas.events.size,0);assert.equal(canvas.attrs.size,0);
  const invalid=fixture();invalid.manifest.entities[0].id='wrong';const invalidStates=[], untouched=fakeCanvas();
  assert.throws(()=>V.mount({...invalid,canvas:untouched,onStatus:x=>invalidStates.push(x.state)}),/entity mismatch/);
  assert.deepEqual(invalidStates,['error']);assert.equal(untouched.gl.calls.uploads,0);
});
