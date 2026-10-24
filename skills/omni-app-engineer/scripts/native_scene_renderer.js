/* Original adapter SOURCE for a separately approved Three.js/OrbitControls pair.
 * No imports, acquisition, global engine discovery, network or authorization grant.
 * Runtime qualification remains pending. The trusted host owns exact byte approval. */
(function (scope) {
  "use strict";
  const need = (ok, message) => { if (!ok) throw new Error(message); };
  const vector = v => Array.isArray(v) && v.length === 3 && v.every(x => Number.isFinite(x) && Math.abs(x) <= 1e6);
  const notify = (fn,...args) => { try { fn(...args); } catch (_) { /* UI observers do not own GPU cleanup. */ } };
  function fitCamera({center,radius},aspect){
    need(vector(center)&&Number.isFinite(radius)&&radius>0&&Number.isFinite(aspect)&&aspect>0,"finite fit bounds required");
    const vertical=Math.PI/4,horizontal=2*Math.atan(Math.tan(vertical/2)*aspect);
    const distance=radius/Math.sin(Math.min(vertical,horizontal)/2)*1.1;
    need(distance<=1e6,"fit exceeds controls distance; choose a closer inspection view");
    const offset=distance/Math.sqrt(3),position=center.map(x=>x+offset);
    need(vector(position),"fit exceeds supported camera extent; choose a closer inspection view");
    return {position,target:[...center]};
  }
  function mount({canvas, scene:input, THREE:T, OrbitControls:Controls,
                  onSelect=()=>{}, onInterrupt=()=>{}, onContextLost=()=>{}, onStatus=()=>{}}) {
    need(T && String(T.REVISION) === "186" && typeof Controls === "function", "reviewed r186 engine/controls required; revision alone is not approval");
    need(canvas && typeof canvas.addEventListener === "function" && typeof canvas.getBoundingClientRect === "function", "canvas required");
    need([onSelect,onInterrupt,onContextLost,onStatus].every(f => typeof f === "function"), "callbacks required");
    const {scene:spec,budget} = scope.OAANativeSceneContract.validate(input);
    let disposed=false, lost=false, gpu=null, controls=null, selection=null;
    const cleanup=[], geometries=new Map(), materials=new Map(), textures=[], meshes=new Map();
    let world,camera,outline,ray,fitBounds;
    const listen=(object,event,handler,options)=>{
      object.addEventListener(event,handler,options);
      cleanup.push(()=>object.removeEventListener(event,handler,options));
    };
    const live=()=>need(!disposed && !lost,"renderer unavailable");
    const draw=()=>{if(!disposed && !lost && gpu){
      if(controls){const distance=Math.hypot(...camera.position.toArray().map((n,i)=>n-controls.target.toArray()[i]));
        camera.near=Math.max(1e-6,distance/10000);camera.far=Math.max(1,distance*10,budget.worldRadiusUpperBound*4);camera.updateProjectionMatrix();}
      gpu.render(world,camera);
    }};
    function dispose() {
      if(disposed)return;
      disposed=true;
      const attempt=f=>{try{f();}catch(_){}};
      cleanup.splice(0).reverse().forEach(attempt);
      if(controls)attempt(()=>controls.dispose());
      if(outline){attempt(()=>outline.geometry.dispose());attempt(()=>outline.material.dispose());}
      for(const g of geometries.values())attempt(()=>g.dispose());
      for(const m of materials.values())attempt(()=>m.dispose());
      for(const t of textures){attempt(()=>t.dispose());if(t.image){t.image.width=0;t.image.height=0;}}
      if(gpu){attempt(()=>gpu.dispose());attempt(()=>gpu.forceContextLoss());}
      meshes.clear();geometries.clear();materials.clear();textures.length=0;
    }
    function setCamera(view) {
      live();need(view && vector(view.position) && vector(view.target),"finite camera required");
      need(Math.hypot(...view.position.map((x,i)=>x-view.target[i]))>=1e-4,"camera must differ from target by at least 0.0001m");
      camera.position.set(...view.position);controls.target.set(...view.target);controls.update();draw();
    }
    function resize(width,height,dpr=1) {
      live();need([width,height,dpr].every(Number.isFinite) && width>0 && height>0 && dpr>0,"positive viewport required");
      // Fit actual available space within admitted framebuffer dimensions. No allocation growth.
      const ratio=Math.min(dpr,spec.render.dpr,4096/width,4096/height,
        Math.sqrt((spec.render.width*spec.render.height*spec.render.dpr**2)/(width*height)));
      // Atomic backing resize: setPixelRatio would first resize the old CSS
      // dimensions and can exceed admission during a large-to-small transition.
      gpu.setDrawingBufferSize(width,height,ratio);
      camera.aspect=width/height;camera.updateProjectionMatrix();draw();
    }
    try {
      world=new T.Scene();world.background=new T.Color("#11151a");
      camera=new T.PerspectiveCamera(45,spec.render.width/spec.render.height,0.000001,1e7);
      // Explicit non-MSAA, no shadows, no postprocess/render targets in this profile.
      canvas.width=1;canvas.height=1; // no inherited oversized backing allocation
      gpu=new T.WebGLRenderer({canvas,antialias:false,alpha:false,preserveDrawingBuffer:false});
      gpu.shadowMap.enabled=false;gpu.outputColorSpace=T.SRGBColorSpace;
      gpu.setDrawingBufferSize(spec.render.width,spec.render.height,spec.render.dpr);
      controls=new Controls(camera,canvas);
      controls.enableDamping=false;controls.autoRotate=false;controls.minDistance=1e-4;controls.maxDistance=1e6;
      controls.listenToKeyEvents(canvas);
      listen(controls,"change",draw);
      listen(controls,"start",()=>notify(onInterrupt,"controls"));
      const hemi=new T.HemisphereLight(0xffffff,0x334155,2);
      const key=new T.DirectionalLight(0xffffff,3);key.position.set(12,20,10);world.add(hemi,key);
      for(const descriptor of spec.geometries){
        const data=scope.OAANativeSceneGeometry.build(descriptor),g=new T.BufferGeometry();
        geometries.set(descriptor.id,g); // register before any fallible allocation
        g.setAttribute("position",new T.BufferAttribute(data.positions,3));
        g.setAttribute("normal",new T.BufferAttribute(data.normals,3));
        g.setAttribute("uv",new T.BufferAttribute(data.uvs,2));
        g.setIndex(new T.BufferAttribute(data.indices,1));g.computeBoundingSphere();
      }
      for(const descriptor of spec.materials){
        let map=null;
        if(descriptor.texture){
          const image=canvas.ownerDocument.createElement("canvas");
          scope.OAANativeSceneTextures.paint(descriptor.texture,image);
          map=new T.CanvasTexture(image);textures.push(map);map.colorSpace=T.SRGBColorSpace;
        }
        materials.set(descriptor.id,new T.MeshStandardMaterial({color:descriptor.color,
          roughness:descriptor.roughness,metalness:descriptor.metalness,map}));
      }
      for(const e of spec.entities){
        const mesh=new T.Mesh(geometries.get(e.geometry),materials.get(e.material));
        mesh.userData.entityId=e.id;mesh.position.set(...e.position);mesh.rotation.set(...e.rotation);mesh.scale.set(...e.scale);
        meshes.set(e.id,mesh);
      }
      for(const e of spec.entities)(e.parent?meshes.get(e.parent):world).add(meshes.get(e.id));
      world.updateMatrixWorld(true);
      const bounds=new T.Box3().setFromObject(world),center=bounds.getCenter(new T.Vector3()),size=bounds.getSize(new T.Vector3());
      fitBounds={center:center.toArray(),radius:Math.max(size.length()/2,0.0001)};
      if(spec.views.length)setCamera(spec.views[0]);
      else setCamera(fitCamera(fitBounds,spec.render.width/spec.render.height));
      // Add the helper after fit so its initial placeholder geometry cannot
      // distort the bounds of a small product scene without named views.
      outline=new T.Box3Helper(new T.Box3(),0xffffff);outline.visible=false;world.add(outline);
      ray=new T.Raycaster();
      let pointer=null;
      listen(canvas,"pointerdown",event=>{pointer={x:event.clientX,y:event.clientY,id:event.pointerId};notify(onInterrupt,"pointer");},true);
      listen(canvas,"pointercancel",()=>{pointer=null;});
      listen(canvas,"pointerup",event=>{
        const start=pointer;pointer=null;
        if(!start||start.id!==event.pointerId||Math.hypot(event.clientX-start.x,event.clientY-start.y)>5||disposed||lost)return;
        const rect=canvas.getBoundingClientRect();if(rect.width<=0||rect.height<=0)return;
        ray.setFromCamera(new T.Vector2((event.clientX-rect.left)/rect.width*2-1,1-(event.clientY-rect.top)/rect.height*2),camera);
        const hit=ray.intersectObjects([...meshes.values()],false)[0];
        notify(onSelect,hit?hit.object.userData.entityId:null);
      });
      listen(canvas,"wheel",()=>notify(onInterrupt,"wheel"),{capture:true,passive:true});
      listen(canvas,"keydown",()=>notify(onInterrupt,"key"),true);
      listen(canvas,"webglcontextlost",event=>{event.preventDefault();lost=true;notify(onStatus,"context-lost");notify(onContextLost);});
      resize(spec.render.width,spec.render.height,spec.render.dpr);
      notify(onStatus,"ready");
      return Object.freeze({budget,views:spec.views,entities:spec.entities.map(({id,label,role})=>Object.freeze({id,label,role})),
        setCamera,getCamera:()=>({position:camera.position.toArray(),target:controls.target.toArray()}),resize,dispose,
        fit(){live();setCamera(fitCamera(fitBounds,camera.aspect));},
        setSelection(id){live();need(id===null||meshes.has(id),"unknown entity");selection=id;
          outline.visible=id!==null;if(id!==null)outline.box.setFromObject(meshes.get(id));draw();},
        snapshot:()=>({disposed,contextLost:lost,selection})});
    } catch(error) {dispose();notify(onStatus,"error");throw error;}
  }
  scope.OAANativeSceneRenderer=Object.freeze({mount,fitCamera,compatibility:Object.freeze({engine:"three",candidateVersion:"0.186.1",revision:"186",qualified:false})});
})(typeof globalThis !== "undefined" ? globalThis : this);
