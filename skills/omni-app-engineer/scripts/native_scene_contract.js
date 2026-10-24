/* Original first-party native scene admission. Separate from the optional GLB
 * harness. Passive JSON values only; no URLs, bindings, scripts or asset loaders.
 * Budgets are provisional engineering estimates, not measured GPU/performance
 * limits or a sandbox. The caller must bound raw JSON bytes before parsing. */
(function (scope) {
  "use strict";
  const MiB=1024*1024, EPS=1e-4;
  const LIMITS=Object.freeze({entities:1024,views:32,materials:64,geometries:128,
    uniqueTriangles:100000,expandedTriangles:200000,geometryBytes:64*MiB,
    textureBytes:32*MiB,estimatedGpuBytes:192*MiB,dimension:4096,dpr:2,
    inputNodes:100000,inputTextUnits:262144,hierarchyDepth:32,worldRadius:1e6});
  const need=(test,message)=>{if(!test)throw new Error("native_scene."+message);};
  function passive(value) {
    let nodes=0,text=0;const stack=[[value,0]],seen=new Set();
    while(stack.length){const [item,depth]=stack.pop();need(++nodes<=LIMITS.inputNodes&&depth<=16,"input_budget");
      if(typeof item==="string"){text+=item.length;need(text<=LIMITS.inputTextUnits,"text_budget");continue;}
      if(item===null||typeof item==="boolean"||typeof item==="number"){need(typeof item!=="number"||Number.isFinite(item),"finite_number");continue;}
      need(typeof item==="object"&&!seen.has(item),"passive_json_tree");seen.add(item);
      const array=Array.isArray(item);need(Object.getPrototypeOf(item)===(array?Array.prototype:Object.prototype),"plain_json_object");
      if(array)need(item.length<=4096,"array_budget");
      const keys=Reflect.ownKeys(item);need(keys.length<=(array?item.length+1:32),"object_budget");
      if(array)need(keys.length===item.length+1,"dense_array");
      for(const key of keys){need(typeof key==="string"&&key.length<=128,"plain_key");if(array&&key==="length")continue;
        const d=Object.getOwnPropertyDescriptor(item,key);need(d&&Object.hasOwn(d,"value")&&d.enumerable,"no_accessors");
        if(array)need(/^(0|[1-9][0-9]*)$/.test(key)&&Number(key)<item.length,"array_key");
        text+=key.length;need(text<=LIMITS.inputTextUnits,"text_budget");stack.push([d.value,depth+1]);}
    }return {inputNodes:nodes,inputTextUnits:text};
  }
  function shape(value,required,optional=[]){need(value&&typeof value==="object"&&!Array.isArray(value),"object_required");
    const keys=Object.keys(value);need(required.every(k=>Object.hasOwn(value,k))&&keys.every(k=>required.includes(k)||optional.includes(k)),"unknown_or_missing_field");}
  const num=(v,min,max)=>{need(typeof v==="number"&&Number.isFinite(v)&&v>=min&&v<=max,"number_range");return Object.is(v,-0)?0:v;};
  const integer=(v,min,max)=>{num(v,min,max);need(Number.isInteger(v),"integer_required");return v;};
  const id=v=>{need(typeof v==="string"&&/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(v),"id");return v;};
  const text=(v,max=120)=>{need(typeof v==="string"&&v.trim().length>0&&v.length<=max&&!/[\u0000-\u001f\u007f<>`]/u.test(v)&&!/(?:\/\/|\b(?:https?|data|javascript|blob|file):)/iu.test(v),"plain_text_no_url");return v.trim();};
  const color=v=>{need(typeof v==="string"&&/^#[0-9a-f]{6}$/i.test(v),"color");return v.toLowerCase();};
  const list=(v,min,max)=>{need(Array.isArray(v)&&v.length>=min&&v.length<=max,"list_size");return v;};
  const vector=(v,min=-1e4,max=1e4)=>list(v,3,3).map(n=>num(n,min,max));
  const length=v=>Math.hypot(...v),sub=(a,b)=>a.map((x,i)=>x-b[i]);
  const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
  const freeze=value=>{if(value&&typeof value==="object"){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
  function recipe(value){need(value&&typeof value==="object","texture_object");shape(value,["kind","size","background","foreground","repeat"],value.kind==="label"?["label"]:[]);
    need(["stripes","grid","panels","label"].includes(value.kind),"texture_kind");
    const size=integer(value.size,16,2048);need((size&(size-1))===0,"texture_power_two");
    const result={kind:value.kind,size,background:color(value.background),foreground:color(value.foreground),repeat:integer(value.repeat,1,64)};
    if(value.kind==="label")result.label=text(value.label);
    let bytes=0;for(let side=size;side>=1;side/=2)bytes+=side*side*4;
    return {recipe:result,budget:{textureBytes:bytes}};
  }
  function geometry(value){need(value&&typeof value==="object","geometry");const result={id:id(value.id),kind:value.kind};let vertices,triangles,radius;
    if(value.kind==="box"){shape(value,["id","kind","width","height","depth"]);for(const k of ["width","height","depth"])result[k]=num(value[k],EPS,1e4);
      vertices=24;triangles=12;radius=Math.hypot(result.width,result.height,result.depth)/2;
    }else if(value.kind==="cylinder"||value.kind==="revolution"){
      const cylinder=value.kind==="cylinder";shape(value,cylinder?["id","kind","radiusTop","radiusBottom","height","radialSegments","capped"]:["id","kind","profile","radialSegments","capped"]);
      result.radialSegments=integer(value.radialSegments,3,128);need(typeof value.capped==="boolean","capped_boolean");result.capped=value.capped;
      let profile;
      if(cylinder){result.radiusTop=num(value.radiusTop,0,1e4);result.radiusBottom=num(value.radiusBottom,0,1e4);result.height=num(value.height,EPS,1e4);
        need(Math.max(result.radiusTop,result.radiusBottom)>=EPS,"positive_radius");profile=[[result.radiusBottom,-result.height/2],[result.radiusTop,result.height/2]];
      }else{profile=list(value.profile,2,64).map(p=>{list(p,2,2);return [num(p[0],0,1e4),num(p[1],-1e4,1e4)];});result.profile=profile;}
      for(let i=0;i<profile.length;i++){need(profile[i][0]===0||profile[i][0]>=EPS,"radius_resolution");if(i)need(profile[i][1]-profile[i-1][1]>=EPS&&Math.fround(profile[i][1])-Math.fround(profile[i-1][1])>=EPS&&Math.max(profile[i][0],profile[i-1][0])>=EPS,"ordered_profile");}
      const caps=result.capped?Number(profile[0][0]>0)+Number(profile.at(-1)[0]>0):0;
      vertices=profile.length*(result.radialSegments+1)+caps*(result.radialSegments+2);triangles=caps*result.radialSegments;
      for(let i=1;i<profile.length;i++)triangles+=result.radialSegments*(profile[i][0]>0&&profile[i-1][0]>0?2:1);
      radius=Math.max(...profile.map(p=>Math.hypot(...p)));
    }else if(value.kind==="extrusion"){
      shape(value,["id","kind","points","height"]);result.height=num(value.height,EPS,1e4);
      result.points=list(value.points,3,64).map(p=>{list(p,2,2);return p.map(n=>num(n,-1e4,1e4));});const p=result.points,n=p.length;
      // Every other vertex must lie strictly left of each edge: simple, strictly
      // convex, counter-clockwise x/z profile, with no ambiguous collinear edge.
      for(const points of [p,p.map(q=>q.map(Math.fround))])for(let i=0;i<n;i++){const a=points[i],b=points[(i+1)%n],dx=b[0]-a[0],dz=b[1]-a[1];need(Math.hypot(dx,dz)>=EPS,"polygon_edge");
        for(let j=0;j<n;j++)if(j!==i&&j!==(i+1)%n)need(dx*(points[j][1]-a[1])-dz*(points[j][0]-a[0])>1e-8,"convex_ccw_polygon");}
      vertices=6*n;triangles=4*n-4;radius=Math.max(...p.map(q=>Math.hypot(q[0],result.height,q[1])));
    }else if(value.kind==="tube"){
      shape(value,["id","kind","path","radius","radialSegments","capped"]);result.path=list(value.path,2,64).map(p=>vector(p));result.radius=num(value.radius,EPS,1e4);
      result.radialSegments=integer(value.radialSegments,3,128);need(typeof value.capped==="boolean","capped_boolean");result.capped=value.capped;
      let previous=null;for(let i=1;i<result.path.length;i++){const d=sub(result.path[i],result.path[i-1]),n=length(d);need(n>=4*result.radius,"tube_radius_segment");
        const unit=d.map(x=>x/n);if(previous)need(dot(previous,unit)>=-1e-12,"tube_turn");previous=unit;}
      need(length(sub(result.path[0],result.path.at(-1)))>=EPS,"open_tube");
      // Distinct ring samples must survive Float32 storage at the path's local
      // coordinate magnitude. This is an admission guard, not world/render proof.
      const magnitude=Math.max(1,...result.path.flat().map(Math.abs))+result.radius;
      need(2*result.radius*Math.sin(Math.PI/result.radialSegments)>=8*magnitude*2**-23,"tube_float_precision");
      vertices=result.path.length*(result.radialSegments+1)+(result.capped?2*(result.radialSegments+2):0);
      triangles=2*(result.path.length-1)*result.radialSegments+(result.capped?2*result.radialSegments:0);radius=Math.max(...result.path.map(p=>length(p)))+result.radius;
    }else throw new Error("native_scene.geometry_kind");
    const bytes=vertices*8*4+triangles*3*4;need(triangles<=LIMITS.uniqueTriangles&&bytes<=LIMITS.geometryBytes,"geometry_budget");
    return {geometry:result,budget:{vertices,triangles,geometryBytes:bytes,boundRadius:radius}};
  }
  function validate(spec){const input=passive(spec);shape(spec,["schema_version","units","axes","fidelity","materials","geometries","entities","views","render"]);
    need(spec.schema_version==="oaa-native-scene-v1"&&spec.units==="m"&&spec.axes==="right-handed-y-up","schema_units_axes");
    shape(spec.fidelity,["kind","source","notes"]);need(["illustrative","reference-based"].includes(spec.fidelity.kind),"fidelity_kind");
    const scene={schema_version:spec.schema_version,units:spec.units,axes:spec.axes,fidelity:{kind:spec.fidelity.kind,source:text(spec.fidelity.source,240),notes:text(spec.fidelity.notes,1000)}};
    const materialIds=new Set();let textureBytes=0;
    scene.materials=list(spec.materials,1,LIMITS.materials).map(m=>{shape(m,["id","label","color","roughness","metalness"],["texture"]);const ident=id(m.id);need(!materialIds.has(ident),"duplicate_material");materialIds.add(ident);
      const out={id:ident,label:text(m.label),color:color(m.color),roughness:num(m.roughness,0,1),metalness:num(m.metalness,0,1)};
      if(Object.hasOwn(m,"texture")){const info=recipe(m.texture);out.texture=info.recipe;textureBytes+=info.budget.textureBytes;}return out;});
    need(textureBytes<=LIMITS.textureBytes,"texture_budget");
    const geometries=new Map();let uniqueVertices=0,uniqueTriangles=0,geometryBytes=0;
    scene.geometries=list(spec.geometries,1,LIMITS.geometries).map(g=>{const info=geometry(g);need(!geometries.has(info.geometry.id),"duplicate_geometry");geometries.set(info.geometry.id,info);
      uniqueVertices+=info.budget.vertices;uniqueTriangles+=info.budget.triangles;geometryBytes+=info.budget.geometryBytes;return info.geometry;});
    need(uniqueTriangles<=LIMITS.uniqueTriangles&&geometryBytes<=LIMITS.geometryBytes,"unique_geometry_budget");
    const entities=new Map();let expandedTriangles=0;
    scene.entities=list(spec.entities,1,LIMITS.entities).map(e=>{shape(e,["id","label","geometry","material","position","rotation","scale","role"],["parent"]);
      const ident=id(e.id);need(!entities.has(ident)&&geometries.has(e.geometry)&&materialIds.has(e.material),"entity_reference_or_duplicate");
      need(["decorative","analytical"].includes(e.role),"entity_role");const out={id:ident,label:text(e.label),geometry:e.geometry,material:e.material,
        position:vector(e.position),rotation:vector(e.rotation,-2*Math.PI,2*Math.PI),scale:vector(e.scale,EPS,1000),role:e.role};
      if(Object.hasOwn(e,"parent"))out.parent=id(e.parent);entities.set(ident,out);expandedTriangles+=geometries.get(e.geometry).budget.triangles;return out;});
    need(expandedTriangles<=LIMITS.expandedTriangles,"expanded_triangle_budget");
    let hierarchyDepth=0,worldRadiusUpperBound=0;
    for(const entity of scene.entities){const chain=[],seen=new Set();let node=entity;
      while(node){need(!seen.has(node.id)&&chain.length<LIMITS.hierarchyDepth,"hierarchy_cycle_or_depth");seen.add(node.id);chain.push(node);
        if(node.parent)need(entities.has(node.parent),"parent_missing");node=node.parent?entities.get(node.parent):null;}
      hierarchyDepth=Math.max(hierarchyDepth,chain.length);let maxScale=1,minScale=1,translation=0;
      for(const item of chain.reverse()){translation+=maxScale*length(item.position);maxScale*=Math.max(...item.scale);minScale*=Math.min(...item.scale);
        need(maxScale<=1e4&&minScale>=1e-8,"cumulative_scale");}
      const bound=translation+maxScale*geometries.get(entity.geometry).budget.boundRadius;need(bound<=LIMITS.worldRadius,"world_bounds");worldRadiusUpperBound=Math.max(worldRadiusUpperBound,bound);}
    const viewIds=new Set();scene.views=list(spec.views,0,LIMITS.views).map(v=>{shape(v,["id","label","position","target"]);const ident=id(v.id);need(!viewIds.has(ident),"duplicate_view");viewIds.add(ident);
      const position=vector(v.position),target=vector(v.target);need(length(sub(position,target))>=EPS,"view_direction");return {id:ident,label:text(v.label),position,target};});
    shape(spec.render,["width","height","dpr","shadows"]);need(spec.render.shadows===false,"shadows_unsupported");
    scene.render={width:integer(spec.render.width,1,4096),height:integer(spec.render.height,1,4096),dpr:num(spec.render.dpr,0.25,2),shadows:false};
    const backingWidth=Math.ceil(scene.render.width*scene.render.dpr),backingHeight=Math.ceil(scene.render.height*scene.render.dpr);
    need(backingWidth<=LIMITS.dimension&&backingHeight<=LIMITS.dimension,"backing_dimensions");const backbufferBytes=backingWidth*backingHeight*8;
    const selectionBytes=4096,estimatedGpuBytes=geometryBytes+textureBytes+backbufferBytes+selectionBytes;need(estimatedGpuBytes<=LIMITS.estimatedGpuBytes,"aggregate_gpu_estimate");
    return freeze({scene,budget:{...input,uniqueVertices,uniqueTriangles,expandedTriangles,geometryBytes,textureBytes,backingWidth,backingHeight,
      backbufferBytes,selectionBytes,estimatedGpuBytes,hierarchyDepth,worldRadiusUpperBound,qualification:"provisional_engineering_estimate_excludes_driver_overhead"}});
  }
  scope.OAANativeSceneContract=Object.freeze({validate,LIMITS,geometryInfo(value){passive(value);return freeze(geometry(value));},textureInfo(value){passive(value);return freeze(recipe(value));}});
})(globalThis);
