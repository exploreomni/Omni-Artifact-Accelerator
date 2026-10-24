/* Original dependency-free renderer for oaa-glb-untextured-v1.
 * No network, imports, decoder, generated shader or promotion authority.
 * Parsing/GL calls are not a sandbox. See VIEWER.md before integration. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OAA3DViewer = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const PROFILE = 'oaa-glb-untextured-v1';
  const LIMIT = Object.freeze({bytes: 16777216, json: 2097152, nodes: 1024,
    geometries: 128, materials: 64, views: 32, triangles: 100000, expanded: 200000});
  const fail = message => { throw new Error('OAA viewer: ' + message); };
  const check = (ok, message) => { if (!ok) fail(message); };
  const number = (x, lo = -1000000, hi = 1000000) => {
    check(typeof x === 'number' && Number.isFinite(x) && x >= lo && x <= hi, 'invalid bounded number'); return x;
  };
  const integer = (x, lo, hi) => { number(x, lo, hi); check(Number.isInteger(x), 'invalid integer'); return x; };
  const vec = (v, n, lo, hi) => { check(Array.isArray(v) && v.length === n, 'invalid vector'); return v.map(x => number(x, lo, hi)); };
  const list = (v, lo, hi) => { check(Array.isArray(v) && v.length >= lo && v.length <= hi, 'collection limit'); return v; };
  const keys = (v, required, optional = []) => {
    check(v && !Array.isArray(v) && typeof v === 'object', 'expected record');
    const actual = Object.keys(v), allowed = required.concat(optional);
    check(required.every(k => Object.hasOwn(v, k)) && actual.every(k => allowed.includes(k)), 'unknown or missing fields');
  };
  const id = x => { check(typeof x === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(x), 'invalid identity'); return x; };
  const label = x => { check(typeof x === 'string' && x.length > 0 && x.length <= 120 && x.trim() && !/[\x00-\x1f\x7f-\x9f]/.test(x), 'invalid label'); return x; };
  const sub = (a, b) => a.map((x, i) => x - b[i]);
  const add = (a, b) => a.map((x, i) => x + b[i]);
  const scale = (a, s) => a.map(x => x * s);
  const dot = (a, b) => a.reduce((sum, x, i) => sum + x * b[i], 0);
  const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
  const unit = a => { const length = Math.hypot(...a); check(length > 1e-10 && Number.isFinite(length), 'degenerate direction'); return scale(a, 1 / length); };
  const identity = () => [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
  function multiply(a, b) {
    const out = Array(16).fill(0);
    for (let col=0; col<4; col++) for (let row=0; row<4; row++)
      for (let k=0; k<4; k++) out[col*4+row] += a[k*4+row]*b[col*4+k];
    return out;
  }
  function trs(n) {
    const [x,y,z,w] = vec(n.rotation,4,-1,1), [sx,sy,sz] = vec(n.scale,3,0.0001,10000);
    const [tx,ty,tz] = vec(n.translation,3,-10000,10000);
    check(Math.abs(x*x+y*y+z*z+w*w-1)<=1e-6,'nonunit quaternion');
    return [(1-2*y*y-2*z*z)*sx,(2*x*y+2*z*w)*sx,(2*x*z-2*y*w)*sx,0,
      (2*x*y-2*z*w)*sy,(1-2*x*x-2*z*z)*sy,(2*y*z+2*x*w)*sy,0,
      (2*x*z+2*y*w)*sz,(2*y*z-2*x*w)*sz,(1-2*x*x-2*y*y)*sz,0,tx,ty,tz,1];
  }
  const point = (m,p) => [0,1,2].map(r => m[r]*p[0]+m[4+r]*p[1]+m[8+r]*p[2]+m[12+r]);
  const emptyBounds = () => ({min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]});
  const extend = (b,p) => { p.forEach((x,i) => { b.min[i]=Math.min(b.min[i],x); b.max[i]=Math.max(b.max[i],x); }); };
  const close = (a,b) => Math.abs(a-b) <= 1e-7+1e-12*Math.max(Math.abs(a),Math.abs(b));
  const sameVector = (a,b) => vec(a,b.length).every((v,i) => close(v,b[i]));

  // A bounded JSON reader rejects duplicate keys before they can be overwritten.
  function strictJSON(text) {
    let at=0, count=0;
    const ws=() => { while (/[\x20\t\r\n]/.test(text[at] || '\0')) at++; };
    function string() {
      const start=at++;
      while (at<text.length) {
        const c=text[at++];
        if(c==='\\') { at++; continue; }
        if(c==='"') { let value; try { value=JSON.parse(text.slice(start,at)); } catch (_) { fail('invalid JSON string'); }
          check(value.length<=256,'JSON string limit'); return value; }
      }
      fail('unterminated JSON string');
    }
    function value(depth) {
      check(++count<=200000 && depth<=16,'JSON complexity limit'); ws(); const c=text[at];
      if(c==='"') return string();
      if(c==='{' || c==='[') {
        const object=c==='{', result=object?Object.create(null):[], end=object?'}':']'; at++; ws();
        if(text[at]===end) { at++; return result; }
        while(at<text.length) {
          if(object) { check(text[at]==='"','invalid object key'); const key=string();
            check(!Object.hasOwn(result,key),'duplicate JSON key'); ws(); check(text[at++]===':','invalid JSON object'); result[key]=value(depth+1);
          } else result.push(value(depth+1));
          ws(); if(text[at]===end) { at++; return result; }
          check(text[at++]===',','invalid JSON separator'); ws();
        }
        fail('unterminated JSON structure');
      }
      const token=/^(?:-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null)/.exec(text.slice(at));
      check(token,'invalid JSON value'); at+=token[0].length;
      const result=JSON.parse(token[0]); check(typeof result!=='number'||Number.isFinite(result),'nonfinite JSON'); return result;
    }
    const result=value(0); ws(); check(at===text.length,'trailing JSON'); return result;
  }
  function dataCopy(value, depth=0, budget={n:0}) {
    check(depth<=16 && ++budget.n<=30000,'manifest complexity limit');
    if(value===null || typeof value==='boolean') return value;
    if(typeof value==='number') return number(value,-1e9,1e9);
    if(typeof value==='string') { check(value.length<=256,'manifest string limit'); return value; }
    check(value && typeof value==='object','manifest must be data');
    const proto=Object.getPrototypeOf(value);
    check(Array.isArray(value) ? proto===Array.prototype : proto===Object.prototype||proto===null,'manifest must be plain data');
    const out=Array.isArray(value)?[]:Object.create(null), descriptors=Object.getOwnPropertyDescriptors(value);
    check(Reflect.ownKeys(descriptors).every(k=>typeof k==='string'),'manifest symbol');
    if(Array.isArray(value)) check(Object.keys(descriptors).length===value.length+1 && Object.keys(descriptors).every(k=>k==='length'||/^(0|[1-9][0-9]*)$/.test(k)&&Number(k)<value.length),'manifest sparse or extended array');
    for(const [key,d] of Object.entries(descriptors)) {
      if(Array.isArray(value)&&key==='length') continue;
      check(d.enumerable && Object.hasOwn(d,'value') && key.length<=64,'manifest accessor or key');
      Object.defineProperty(out,key,{value:dataCopy(d.value,depth+1,budget),enumerable:true,writable:true,configurable:true});
    }
    return out;
  }
  function view(v) {
    keys(v,['id','label','position','target','up']); id(v.id); label(v.label);
    const position=vec(v.position,3), target=vec(v.target,3), up=vec(v.up,3,-1,1), direction=unit(sub(target,position));
    check(Math.abs(dot(up,up)-1)<=1e-6 && dot(cross(direction,up),cross(direction,up))>1e-8,'invalid camera basis');
    return {id:v.id,label:v.label,position,target,up};
  }
  function parse(glb, manifest) {
    check(glb instanceof ArrayBuffer || glb instanceof Uint8Array,'bytes required');
    const incoming=glb instanceof ArrayBuffer?new Uint8Array(glb):glb;
    check(incoming.buffer instanceof ArrayBuffer && incoming.byteLength>=28 && incoming.byteLength<=LIMIT.bytes,'GLB byte limit');
    const bytes=new Uint8Array(incoming), reader=new DataView(bytes.buffer);
    check(reader.getUint32(0,true)===0x46546c67 && reader.getUint32(4,true)===2 && reader.getUint32(8,true)===bytes.length,'invalid GLB header');
    const jl=reader.getUint32(12,true), bo=20+jl;
    check(jl>0 && jl<=LIMIT.json && jl%4===0 && bo+8<=bytes.length && reader.getUint32(16,true)===0x4e4f534a,'invalid JSON chunk');
    const bl=reader.getUint32(bo,true), start=bo+8;
    check(bl>0 && bl%4===0 && start+bl===bytes.length && reader.getUint32(bo+4,true)===0x004e4942,'invalid BIN chunk');
    let text; try { text=new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(20,bo)); } catch (_) { fail('invalid UTF-8'); }
    const d=strictJSON(text);
    keys(d,['asset','scene','scenes','nodes','meshes','materials','accessors','bufferViews','buffers']);
    keys(d.asset,['version','generator']); check(d.asset.version==='2.0' && d.asset.generator==='OAA original SceneSpec compiler 1','unsupported profile');
    check(d.scene===0,'invalid scene'); list(d.buffers,1,1); keys(d.buffers[0],['byteLength']); check(d.buffers[0].byteLength===bl,'buffer length mismatch');
    list(d.scenes,1,1); const scene=d.scenes[0]; keys(scene,['nodes','extras']); keys(scene.extras,['units','axes','views']);
    check(scene.extras.units==='m' && scene.extras.axes==='right-handed-y-up','unsupported coordinates');
    const views=list(scene.extras.views,1,LIMIT.views).map(view); check(new Set(views.map(v=>v.id)).size===views.length,'duplicate camera');
    const materials=list(d.materials,1,LIMIT.materials).map(m=>{
      keys(m,['name','pbrMetallicRoughness']); id(m.name); const p=m.pbrMetallicRoughness;
      keys(p,['baseColorFactor','metallicFactor','roughnessFactor']); const color=vec(p.baseColorFactor,4,0,1);
      check(color[3]===1,'transparent material'); number(p.metallicFactor,0,1); number(p.roughnessFactor,0,1); return {id:m.name,color};
    }); check(new Set(materials.map(m=>m.id)).size===materials.length,'duplicate material');
    const buffers=list(d.bufferViews,1,LIMIT.geometries*3).map(v=>{
      keys(v,['buffer','byteOffset','byteLength','target']); check(v.buffer===0,'external buffer');
      integer(v.byteOffset,0,bl); integer(v.byteLength,4,bl); check(v.byteOffset%4===0&&v.byteLength%4===0&&v.byteOffset+v.byteLength<=bl&&[34962,34963].includes(v.target),'invalid buffer span'); return v;
    }); let cursor=0;
    for(const v of [...buffers].sort((a,b)=>a.byteOffset-b.byteOffset)) { check(v.byteOffset===cursor,'unclaimed or overlapping bytes'); cursor+=v.byteLength; }
    check(cursor===bl,'unclaimed buffer bytes'); const usedBuffers=new Set(); let floats=0;
    const access=list(d.accessors,1,LIMIT.geometries*3).map(a=>{
      keys(a,['bufferView','componentType','count','type'],['min','max']); const bi=integer(a.bufferView,0,buffers.length-1), b=buffers[bi];
      check(!usedBuffers.has(bi),'shared buffer view'); usedBuffers.add(bi); integer(a.count,1,LIMIT.triangles*3);
      const isFloat=a.componentType===5126&&a.type==='VEC3', isIndex=a.componentType===5125&&a.type==='SCALAR';
      check(isFloat||isIndex,'unsupported accessor'); const width=isFloat?3:1;
      check(b.byteLength===a.count*width*4 && b.target===(isFloat?34962:34963),'accessor span mismatch');
      if(isFloat) { floats+=a.count; check(floats<=LIMIT.triangles*6,'decoded float limit'); }
      const values=isFloat?new Float32Array(a.count*3):new Uint32Array(a.count);
      for(let i=0;i<values.length;i++) { const offset=start+b.byteOffset+i*4; values[i]=isFloat?number(reader.getFloat32(offset,true)):reader.getUint32(offset,true); }
      return {meta:a,values};
    }); check(usedBuffers.size===buffers.length,'unreferenced buffer');
    const usedAccess=new Set(), usedMaterials=new Set(), geometries=new Map(), meshPairs=new Set(); let unique=0;
    const meshes=list(d.meshes,1,LIMIT.nodes).map(m=>{
      keys(m,['primitives','extras']); keys(m.extras,['geometry_id']); const gid=id(m.extras.geometry_id), p=list(m.primitives,1,1)[0];
      keys(p,['attributes','indices','mode','material']); keys(p.attributes,['POSITION','NORMAL']); check(p.mode===4,'nontriangle mesh');
      const refs=[p.attributes.POSITION,p.attributes.NORMAL,p.indices].map(i=>integer(i,0,access.length-1)); check(new Set(refs).size===3,'aliased attributes');
      refs.forEach(i=>usedAccess.add(i)); const mat=integer(p.material,0,materials.length-1); usedMaterials.add(mat);
      const pair=gid+':'+mat;check(!meshPairs.has(pair),'duplicate geometry/material pair');meshPairs.add(pair);
      const [pa,na,ia]=refs.map(i=>access[i]), pos=pa.values, norm=na.values, ind=ia.values;
      keys(pa.meta,['bufferView','componentType','count','type','min','max']); keys(na.meta,['bufferView','componentType','count','type']); keys(ia.meta,['bufferView','componentType','count','type']);
      check(pa.meta.type==='VEC3'&&na.meta.type==='VEC3'&&ia.meta.type==='SCALAR'&&pos.length===norm.length&&pos.length===ind.length*3&&ind.length%3===0,'primitive mismatch');
      const b=emptyBounds(); for(let i=0;i<ind.length;i++) { check(ind[i]===i,'nonsequential indices'); extend(b,Array.from(pos.subarray(i*3,i*3+3))); }
      check(sameVector(pa.meta.min,b.min)&&sameVector(pa.meta.max,b.max),'position bounds mismatch');
      const signature=refs.join(':');
      if(geometries.has(gid)) check(geometries.get(gid)===signature,'conflicting geometry');
      else {
        check(![...geometries.values()].includes(signature) && geometries.size<LIMIT.geometries,'geometry alias or limit'); geometries.set(gid,signature);
        unique+=ind.length/3; check(unique<=LIMIT.triangles,'triangle limit');
        for(let i=0;i<pos.length;i+=9) {
          const face=unit(cross(sub(Array.from(pos.subarray(i+3,i+6)),Array.from(pos.subarray(i,i+3))),sub(Array.from(pos.subarray(i+6,i+9)),Array.from(pos.subarray(i,i+3)))));
          for(let j=i;j<i+9;j+=3) { const n=Array.from(norm.subarray(j,j+3)); check(Math.abs(dot(n,n)-1)<=1e-5 && dot(face,n)>1-1e-5,'invalid face normal'); }
        }
      }
      return {gid,mat,pos,count:ind.length};
    }); check(usedAccess.size===access.length&&usedMaterials.size===materials.length,'unreferenced geometry/material');
    const nodes=list(d.nodes,1,LIMIT.nodes), ids=new Set(), parents=new Map(), usedMeshes=new Set(); let expanded=0;
    nodes.forEach((n,i)=>{
      keys(n,['name','mesh','translation','rotation','scale','extras'],['children']); label(n.name); keys(n.extras,['entity_id']); id(n.extras.entity_id);
      check(!ids.has(n.extras.entity_id),'duplicate entity'); ids.add(n.extras.entity_id); const mi=integer(n.mesh,0,meshes.length-1); usedMeshes.add(mi); trs(n);
      expanded+=meshes[mi].count/3; check(expanded<=LIMIT.expanded,'expanded triangle limit');
      list(Object.hasOwn(n,'children')?n.children:[],0,nodes.length).forEach(c=>{ integer(c,0,nodes.length-1); check(c!==i&&!parents.has(c),'duplicate parent'); parents.set(c,i); });
    });
    const roots=list(scene.nodes,1,nodes.length); roots.forEach(i=>integer(i,0,nodes.length-1));
    check(new Set(roots).size===roots.length && roots.length===nodes.length-parents.size && roots.every(i=>!parents.has(i)) && usedMeshes.size===meshes.length,'unreachable graph');
    const visited=new Set(), entities=[], bounds=emptyBounds();
    function visit(i,parent,depth) {
      check(depth<=32&&!visited.has(i),'cyclic or deep graph'); visited.add(i); const n=nodes[i], mesh=meshes[n.mesh], world=multiply(parent,trs(n));
      world.forEach(x=>number(x)); const positions=new Float64Array(mesh.pos.length), normals=new Float32Array(mesh.pos.length), b=emptyBounds();
      for(let j=0;j<mesh.pos.length;j+=3) { const p=point(world,Array.from(mesh.pos.subarray(j,j+3))); p.forEach(x=>number(x)); positions.set(p,j); extend(b,p); }
      for(let j=0;j<positions.length;j+=9) { const p=Array.from(positions.subarray(j,j+3)), normal=unit(cross(sub(Array.from(positions.subarray(j+3,j+6)),p),sub(Array.from(positions.subarray(j+6,j+9)),p)));
        normals.set(normal,j); normals.set(normal,j+3); normals.set(normal,j+6); }
      extend(bounds,b.min); extend(bounds,b.max);
      entities.push({id:n.extras.entity_id,label:n.name,node:i,mesh:n.mesh,geometry:mesh.gid,material:materials[mesh.mat].id,color:materials[mesh.mat].color,positions,normals,bounds:b});
      for(const child of n.children||[]) visit(child,world,depth+1);
    }
    for(const i of roots) visit(i,identity(),1); check(visited.size===nodes.length,'unreachable cycle');
    const counts={triangles:unique,vertices:unique*3,expanded_triangles:expanded,entities:entities.length};
    const m=dataCopy(manifest); keys(m,['schema_version','profile','asset_sha256','asset_bytes','scene_sha256','input_sha256','units','axes','counts','bounds','entities','views','provenance','qualification']);
    check(m.schema_version===1&&m.profile===PROFILE&&m.asset_bytes===bytes.length&&m.units==='m'&&m.axes==='right-handed-y-up','manifest profile mismatch');
    check(['asset_sha256','scene_sha256','input_sha256'].every(k=>typeof m[k]==='string'&&/^[a-f0-9]{64}$/.test(m[k])),'manifest hash format');
    keys(m.counts,Object.keys(counts)); check(Object.keys(counts).every(k=>m.counts[k]===counts[k]),'manifest count mismatch');
    function matchBounds(a,b) { keys(a,['min','max']); check(sameVector(a.min,b.min)&&sameVector(a.max,b.max),'manifest bounds mismatch'); }
    matchBounds(m.bounds,bounds); list(m.entities,entities.length,entities.length); const mapped=new Set();
    for(const e of m.entities) { keys(e,['id','node','mesh','geometry','material','bounds']); const actual=entities.find(x=>x.id===e.id);
      check(actual&&!mapped.has(e.id)&&['node','mesh','geometry','material'].every(k=>e[k]===actual[k]),'manifest entity mismatch'); mapped.add(e.id); matchBounds(e.bounds,actual.bounds); }
    list(m.views,views.length,views.length); const named=new Set();
    for(const item of m.views) { const v=view(item), actual=views.find(x=>x.id===v.id); check(actual&&!named.has(v.id)&&actual.label===v.label&&['position','target','up'].every(k=>sameVector(v[k],actual[k])),'manifest camera mismatch'); named.add(v.id); }
    keys(m.provenance,['generator','textures','imported_assets']); check(m.provenance.generator==='original-repository-source'&&m.provenance.textures===false&&m.provenance.imported_assets===false,'unsupported provenance profile');
    keys(m.qualification,['rendered','native','isolation']); check(m.qualification.rendered==='not_assessed'&&m.qualification.native==='not_assessed'&&m.qualification.isolation==='not_established_by_compiler','unsupported compiler receipt');
    const center=bounds.min.map((x,i)=>(x+bounds.max[i])/2), radius=Math.max(Math.hypot(...sub(bounds.max,bounds.min))/2,1e-4);
    return {entities,views,bounds,center,radius,counts};
  }

  function lookAt(position,target,up) {
    const z=unit(sub(position,target)), x=unit(cross(up,z)), y=cross(z,x);
    return [x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,position),-dot(y,position),-dot(z,position),1];
  }
  function perspective(aspect,near,far) {
    number(aspect,0.0001,10000); check(near>0&&far>near,'invalid clip planes'); const f=1/Math.tan(Math.PI/8);
    return [f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0];
  }
  function fit(model,aspect=1) {
    const half=Math.min(Math.PI/8,Math.atan(Math.tan(Math.PI/8)*aspect));
    const distance=model.radius/Math.sin(half)*1.12, direction=unit([1,0.65,1]);
    return {position:add(model.center,scale(direction,distance)),target:[...model.center],up:[0,1,0]};
  }
  function ray(camera,x,y,aspect) {
    const forward=unit(sub(camera.target,camera.position)), right=unit(cross(forward,camera.up)), up=cross(right,forward), t=Math.tan(Math.PI/8);
    return {origin:camera.position,direction:unit(add(add(forward,scale(right,x*t*aspect)),scale(up,y*t)))};
  }
  function pick(model,r) {
    let best=Infinity, selected=null;
    for(const e of model.entities) for(let i=0;i<e.positions.length;i+=9) {
      const a=Array.from(e.positions.subarray(i,i+3)), e1=sub(Array.from(e.positions.subarray(i+3,i+6)),a), e2=sub(Array.from(e.positions.subarray(i+6,i+9)),a);
      const h=cross(r.direction,e2), det=dot(e1,h); if(Math.abs(det)<1e-12) continue;
      const s=sub(r.origin,a), u=dot(s,h)/det; if(u<0||u>1) continue;
      const q=cross(s,e1), v=dot(r.direction,q)/det; if(v<0||u+v>1) continue;
      const distance=dot(e2,q)/det; if(distance>0&&distance<best) { best=distance; selected=e.id; }
    }
    return selected;
  }

  const VERTEX = 'attribute vec3 aPosition; attribute vec3 aNormal; uniform mat4 uMVP; varying vec3 normal; void main(){normal=aNormal;gl_Position=uMVP*vec4(aPosition,1.0);}';
  const FRAGMENT = 'precision mediump float; uniform vec4 uColor; uniform float uSelected; varying vec3 normal; void main(){float light=0.32+0.68*abs(dot(normalize(normal),normalize(vec3(0.5,0.8,0.6))));vec3 base=uColor.rgb*light;gl_FragColor=vec4(mix(base,vec3(1.0,0.82,0.3),uSelected*0.30),1.0);}';
  function mount(options) {
    check(options && typeof options==='object','mount options required');
    const {canvas,glb,manifest}=options, onSelect=options.onSelect||(()=>{}), onStatus=options.onStatus||(()=>{});
    check(canvas&&typeof canvas.getContext==='function'&&typeof canvas.addEventListener==='function'&&typeof canvas.removeEventListener==='function','canvas required');
    check(typeof onSelect==='function'&&typeof onStatus==='function','callbacks required');
    let model;
    try {model=parse(glb,manifest);} catch(error) {onStatus({state:'error',profile:PROFILE,rendered:'unqualified',native:'unqualified'});throw error;}
    let gl=null, program=null, disposed=false, lost=false, selected=null, drag=null, camera=null, aspect=1, fitting=true;
    const buffers=[], shaders=[], listeners=[], draws=[];
    const notify=(state)=>onStatus({state,profile:PROFILE,rendered:'unqualified',native:'unqualified'});
    const listen=(type,fn,opts)=>{canvas.addEventListener(type,fn,opts);listeners.push([type,fn,opts]);};
    const originalTab=canvas.getAttribute?canvas.getAttribute('tabindex'):null;
    const addedTab=canvas.setAttribute&&originalTab===null; if(addedTab) canvas.setAttribute('tabindex','0');
    function endDrag() {
      if(drag&&canvas.hasPointerCapture&&canvas.hasPointerCapture(drag.id))canvas.releasePointerCapture(drag.id);
      drag=null;
    }
    function cleanup() {
      for(const [type,fn,opts] of listeners) canvas.removeEventListener(type,fn,opts); listeners.length=0;
      if(gl&&!lost) { for(const b of buffers) gl.deleteBuffer(b); for(const s of shaders) gl.deleteShader(s); if(program) gl.deleteProgram(program); }
      buffers.length=0; shaders.length=0; draws.length=0; endDrag();
      model.entities.length=0;model.views.length=0;
      if(addedTab&&canvas.removeAttribute) canvas.removeAttribute('tabindex');
    }
    let attributes, uniforms;
    function draw() {
      if(disposed||lost||!camera) return;
      const distance=Math.hypot(...sub(camera.position,model.center));
      const near=Math.max(model.radius*0.0001,distance-model.radius*1.5,0.00001), far=Math.max(near*2,distance+model.radius*3);
      const matrix=multiply(perspective(aspect,near,far),lookAt(sub(camera.position,model.center),sub(camera.target,model.center),camera.up));
      gl.viewport(0,0,canvas.width,canvas.height); gl.clearColor(0.045,0.055,0.07,1); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT); gl.useProgram(program);
      gl.uniformMatrix4fv(uniforms.mvp,false,new Float32Array(matrix));
      for(const d of draws) {
        gl.bindBuffer(gl.ARRAY_BUFFER,d.position); gl.vertexAttribPointer(attributes.position,3,gl.FLOAT,false,0,0); gl.enableVertexAttribArray(attributes.position);
        gl.bindBuffer(gl.ARRAY_BUFFER,d.normal); gl.vertexAttribPointer(attributes.normal,3,gl.FLOAT,false,0,0); gl.enableVertexAttribArray(attributes.normal);
        gl.uniform4fv(uniforms.color,d.entity.color); gl.uniform1f(uniforms.selected,d.entity.id===selected?1:0); gl.drawArrays(gl.TRIANGLES,0,d.entity.positions.length/3);
      }
    }
    function resize() {
      if(disposed||lost) return false;
      const rect=canvas.getBoundingClientRect?canvas.getBoundingClientRect():{width:canvas.width,height:canvas.height};
      if(!Number.isFinite(rect.width)||!Number.isFinite(rect.height)||rect.width<=0||rect.height<=0) return false;
      const host=canvas.ownerDocument&&canvas.ownerDocument.defaultView, dpr=Math.min(Math.max(Number(host?host.devicePixelRatio:1)||1,1),2);
      const factor=Math.min(dpr,4096/rect.width,4096/rect.height); canvas.width=Math.max(1,Math.round(rect.width*factor)); canvas.height=Math.max(1,Math.round(rect.height*factor)); aspect=canvas.width/canvas.height;
      if(!camera||fitting) camera=fit(model,aspect); draw(); return true;
    }
    function setCamera(request) {
      if(disposed||lost) return false;
      const named=typeof request==='string'?model.views.find(v=>v.id===request):null;
      if(named) { camera={position:[...named.position],target:[...named.target],up:[...named.up]}; fitting=false; }
      else { check(request===null||request==='fit'||request==='reset','unknown camera'); camera=fit(model,aspect); fitting=true; }
      draw(); return true;
    }
    function setSelection(entityId) {
      if(disposed||lost) return false;
      check(entityId===null||model.entities.some(e=>e.id===entityId),'unknown entity'); selected=entityId; draw(); return true;
    }
    function choose(entityId) { setSelection(entityId); onSelect(entityId); }
    function rotate(vector,axis,angle) { return add(add(scale(vector,Math.cos(angle)),scale(cross(axis,vector),Math.sin(angle))),scale(axis,dot(axis,vector)*(1-Math.cos(angle)))); }
    try {
      gl=canvas.getContext('webgl',{alpha:false,antialias:true,preserveDrawingBuffer:false}); check(gl,'WebGL unavailable');
      program=gl.createProgram(); check(program,'program allocation failed');
      for(const [type,source] of [[gl.VERTEX_SHADER,VERTEX],[gl.FRAGMENT_SHADER,FRAGMENT]]) {
        const shader=gl.createShader(type); check(shader,'shader allocation failed'); shaders.push(shader); gl.shaderSource(shader,source); gl.compileShader(shader);
        check(gl.getShaderParameter(shader,gl.COMPILE_STATUS),'fixed shader compilation failed'); gl.attachShader(program,shader);
      }
      gl.linkProgram(program); check(gl.getProgramParameter(program,gl.LINK_STATUS),'program link failed');
      attributes={position:gl.getAttribLocation(program,'aPosition'),normal:gl.getAttribLocation(program,'aNormal')};
      check(attributes.position>=0&&attributes.normal>=0,'missing shader attribute');
      uniforms={mvp:gl.getUniformLocation(program,'uMVP'),color:gl.getUniformLocation(program,'uColor'),selected:gl.getUniformLocation(program,'uSelected')};
      check(Object.values(uniforms).every(x=>x!==null),'missing shader uniform'); gl.enable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE);
      for(const entity of model.entities) {
        const local=new Float32Array(entity.positions.length); for(let i=0;i<local.length;i++) local[i]=entity.positions[i]-model.center[i%3];
        const pair=[]; for(const data of [local,entity.normals]) { const buffer=gl.createBuffer(); check(buffer,'buffer allocation failed'); buffers.push(buffer); pair.push(buffer); gl.bindBuffer(gl.ARRAY_BUFFER,buffer); gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW); }
        draws.push({entity,position:pair[0],normal:pair[1]});
      }
      listen('webglcontextlost',event=>{if(event.preventDefault)event.preventDefault();lost=true;endDrag();notify('context_lost');});
      listen('webglcontextrestored',()=>{if(!disposed)notify('remount_required');});
      listen('pointerdown',event=>{ if(disposed||lost||event.button!==0)return; drag={id:event.pointerId,x:event.clientX,y:event.clientY,moved:false}; if(canvas.setPointerCapture)canvas.setPointerCapture(event.pointerId); if(canvas.focus)canvas.focus(); });
      listen('pointermove',event=>{
        if(!drag||drag.id!==event.pointerId||disposed||lost||!camera)return;
        const dx=event.clientX-drag.x,dy=event.clientY-drag.y; if(Math.abs(dx)+Math.abs(dy)<1)return;
        drag.moved=true;drag.x=event.clientX;drag.y=event.clientY; let offset=rotate(sub(camera.position,camera.target),camera.up,-dx*0.008);
        const right=unit(cross(camera.up,offset)), candidate=rotate(offset,right,-dy*0.008);
        if(Math.abs(dot(unit(candidate),camera.up))<0.98)offset=candidate;
        camera.position=add(camera.target,offset);fitting=false;draw();
      });
      listen('pointerup',event=>{
        if(!drag||drag.id!==event.pointerId||disposed||lost)return;const wasMoved=drag.moved;drag=null;
        if(canvas.hasPointerCapture&&canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);
        if(!wasMoved&&camera) { const rect=canvas.getBoundingClientRect(); if(rect.width>0&&rect.height>0)choose(pick(model,ray(camera,2*(event.clientX-rect.left)/rect.width-1,1-2*(event.clientY-rect.top)/rect.height,aspect))); }
      });
      listen('pointercancel',endDrag);
      listen('wheel',event=>{if(disposed||lost||!camera)return;if(event.preventDefault)event.preventDefault();const delta=number(event.deltaY,-1e7,1e7), offset=sub(camera.position,camera.target), distance=Math.hypot(...offset);
        const next=Math.min(model.radius*100,Math.max(model.radius*0.02,distance*Math.exp(Math.max(-1,Math.min(1,delta*0.001)))));camera.position=add(camera.target,scale(offset,next/distance));fitting=false;draw();},{passive:false});
      listen('keydown',event=>{if(disposed||lost)return;
        if(['ArrowLeft','ArrowRight'].includes(event.key)) { if(event.preventDefault)event.preventDefault();const index=model.entities.findIndex(e=>e.id===selected), step=event.key==='ArrowRight'?1:-1;
          const next=index<0?(step>0?0:model.entities.length-1):(index+step+model.entities.length)%model.entities.length;choose(model.entities[next].id); }
        else if(event.key==='Home') {if(event.preventDefault)event.preventDefault();setCamera(null);}
      });
      camera=fit(model,aspect); resize(); notify('ready');
    } catch(error) {cleanup();disposed=true;notify(gl?'error':'unsupported');throw error;}
    return Object.freeze({setCamera,setSelection,resize,dispose(){if(disposed)return;disposed=true;cleanup();notify('disposed');},
      entities:Object.freeze(model.entities.map(e=>Object.freeze({id:e.id,label:e.label}))),
      views:Object.freeze(model.views.map(v=>Object.freeze({id:v.id,label:v.label})))});
  }
  return Object.freeze({mount,parse,math:Object.freeze({multiply,trs,point,lookAt,perspective,fit,ray,pick}),PROFILE});
});
