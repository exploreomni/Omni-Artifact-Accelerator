/* Original optional state adapter. No network, queries, storage, shaders or packages.
 * Host owns authorized native queries, accessible markup and renderer creation.
 * Input records are already reviewed aggregates; this adapter never aggregates. */
(function (scope) {
  "use strict";
  const need=(condition,message)=>{if(!condition)throw new Error(message);};
  const id=value=>typeof value==="string"&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$/.test(value);
  const label=value=>typeof value==="string"&&value.length>0&&value.length<=200&&!/[\u0000-\u001f\u007f]/u.test(value);
  const plain=value=>value!==null&&typeof value==="object"&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;
  const keys=(value,allowed)=>plain(value)&&Object.keys(value).every(k=>allowed.includes(k));
  const copy=value=>JSON.parse(JSON.stringify(value));
  function create({entities,views=[],bindings,metrics,renderer,onState=()=>{},reducedMotion=true}) {
    need(Array.isArray(entities)&&entities.length>0&&entities.length<=1024,"bounded entities required");
    need(Array.isArray(views)&&views.length<=32,"bounded views required");
    need(Array.isArray(bindings)&&bindings.length===entities.length,"complete bindings required");
    need(Array.isArray(metrics)&&metrics.length>0&&metrics.length<=32&&metrics.every(id)&&new Set(metrics).size===metrics.length,"metric keys required");
    need(renderer&&["setCamera","setSelection","resize","dispose"].every(k=>typeof renderer[k]==="function"),"renderer contract required");
    need(typeof onState==="function"&&typeof reducedMotion==="boolean","invalid callbacks/preferences");
    const catalog=new Map(),landmarks=new Map(),mapping=new Map(),dataKeys=new Set();
    for(const item of entities){need(keys(item,["id","label"])&&id(item.id)&&label(item.label)&&!catalog.has(item.id),"invalid entity");catalog.set(item.id,{...item});}
    for(const view of views){need(keys(view,["id","label"])&&id(view.id)&&label(view.label)&&!landmarks.has(view.id),"invalid view");landmarks.set(view.id,{...view});}
    for(const row of bindings){need(keys(row,["entityId","dataKey"])&&catalog.has(row.entityId)&&id(row.dataKey)&&!mapping.has(row.entityId)&&!dataKeys.has(row.dataKey),"invalid or ambiguous identity binding");mapping.set(row.entityId,row.dataKey);dataKeys.add(row.dataKey);}
    const fields=[...metrics];let disposed=false,sequence=0,pending=null;
    let state={selection:null,camera:null,tourIndex:null,reducedMotion,dataStatus:"idle",asOf:null,values:{},missing:[],rendererStatus:"ready"};
    const live=()=>need(!disposed,"spatial controller disposed");
    function snapshot(){return copy({...state,disposed,pending,entities:[...catalog.values()],views:[...landmarks.values()]});}
    const emit=()=>{const result=snapshot();onState(result);return result;};
    function camera(view){need(view===null||landmarks.has(view),"unknown camera view");renderer.setCamera(view);state.camera=view;}
    function select(entityId){live();need(entityId===null||catalog.has(entityId),"unknown entity");renderer.setSelection(entityId);state.selection=entityId;state.tourIndex=null;return emit();}
    function resolve(token,{status,rows=[],asOf=null}={}) {
      live();if(pending===null||!Number.isSafeInteger(token)||token!==pending)return {ignored:true};
      need(["ready","empty","restricted","error","stale"].includes(status),"invalid data status");
      need(asOf===null||(typeof asOf==="string"&&asOf.length<=64&&Number.isFinite(Date.parse(asOf))),"invalid data timestamp");
      need(Array.isArray(rows)&&rows.length<=entities.length,"bounded rows required");
      need(["ready","stale"].includes(status)||rows.length===0,"state cannot expose rows");
      const keyed=new Map();
      for(const row of rows){
        need(keys(row,["key","values"])&&dataKeys.has(row.key)&&!keyed.has(row.key)&&plain(row.values),"unknown or duplicate data identity");
        need(Object.keys(row.values).length===fields.length&&fields.every(k=>Object.hasOwn(row.values,k)),"metric shape mismatch");
        const values=Object.create(null);
        for(const field of fields){const value=row.values[field];need(value===null||(typeof value==="number"&&Number.isFinite(value)),"finite metric or null required");values[field]=value;}
        keyed.set(row.key,values);
      }
      need(status!=="ready"||rows.length>0,"empty results need empty status");
      const values=Object.create(null),missing=[];
      for(const [entity,key] of mapping){if(keyed.has(key))values[entity]=keyed.get(key);else missing.push(entity);}
      // Commit after validation. Refresh never calls the renderer or resets viewpoint.
      state={...state,dataStatus:status,asOf,values,missing};pending=null;return emit();
    }
    return Object.freeze({
      snapshot,select,
      showView(view){live();camera(view);state.tourIndex=null;return emit();},
      reset(){live();renderer.setSelection(null);camera(null);state.selection=null;state.tourIndex=null;return emit();},
      // Explicit user step only; no timers, autoplay or motion under reduced motion.
      stepTour(delta=1){live();need(delta===1||delta===-1,"tour step must be +/-1");const ids=[...landmarks.keys()];need(ids.length>0,"no named views");const next=state.tourIndex===null?(delta===1?0:ids.length-1):Math.max(0,Math.min(ids.length-1,state.tourIndex+delta));camera(ids[next]);state.tourIndex=next;return emit();},
      stopTour(){live();state.tourIndex=null;return emit();},
      setReducedMotion(value){live();need(typeof value==="boolean","boolean preference required");state.reducedMotion=value;state.tourIndex=null;return emit();},
      begin(){live();pending=++sequence;state.dataStatus="loading";emit();return pending;},
      resolve,
      invalidate(status="restricted"){live();need(["restricted","error","empty"].includes(status),"invalid clear state");pending=null;state={...state,dataStatus:status,values:{},missing:[...catalog.keys()],asOf:null};return emit();},
      rendererStatus(status){live();need(["ready","unavailable","context-lost","error"].includes(status),"invalid renderer status");state.rendererStatus=status;if(status!=="ready")state.tourIndex=null;return emit();},
      resize(){live();renderer.resize();},
      dispose(){if(disposed)return;disposed=true;pending=null;state.values={};state.asOf=null;state.tourIndex=null;try{renderer.dispose();}finally{emit();}}
    });
  }
  scope.OAASpatialController=Object.freeze({create});
})(typeof globalThis!=="undefined"?globalThis:this);
