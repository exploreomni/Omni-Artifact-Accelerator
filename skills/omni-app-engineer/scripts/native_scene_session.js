/* Original renderer-neutral lifecycle/camera controller. No imports, DOM listeners,
 * network, shaders or native writes. The adapter owns pointer/wheel/key wiring,
 * visibility/offscreen signals, accessible controls and renderer qualification.
 * initialize() must return a renderer owned exclusively by this session; its
 * setCamera/resize/dispose methods are synchronous adapter operations.
 * Python/Node/local tests do not establish rendering or OS isolation. */
(function (scope) {
  'use strict';
  const need=(ok,message)=>{if(!ok)throw new Error('OAA scene session: '+message);};
  const finite=(n,lo,hi)=>typeof n==='number'&&Number.isFinite(n)&&n>=lo&&n<=hi;
  const vec=v=>{need(Array.isArray(v)&&v.length===3&&v.every(n=>finite(n,-1e9,1e9)),'finite bounded camera vector required');return [...v];};
  const sub=(a,b)=>a.map((n,i)=>n-b[i]);
  const add=(a,b)=>a.map((n,i)=>n+b[i]);
  const scale=(a,n)=>a.map(v=>v*n);
  const dot=(a,b)=>a.reduce((sum,n,i)=>sum+n*b[i],0);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const unit=v=>scale(v,1/Math.hypot(...v));
  const copyCamera=c=>c?{position:[...c.position],target:[...c.target]}:null;
  function camera(value) {
    need(value&&typeof value==='object'&&!Array.isArray(value),'camera record required');
    const position=vec(value.position),target=vec(value.target);
    need(Math.hypot(...sub(position,target))>1e-8,'camera position and target must differ');
    return {position,target};
  }
  // Interpolate direction on a sphere so opposing landmarks do not pass through
  // position == target. This is not an obstacle/collision-aware tour planner.
  function interpolate(from,to,t) {
    if(t<=0)return copyCamera(from);if(t>=1)return copyCamera(to);
    const a=sub(from.position,from.target),b=sub(to.position,to.target),u=unit(a),v=unit(b);
    const cosine=Math.max(-1,Math.min(1,dot(u,v))),angle=Math.acos(cosine);let direction;
    if(cosine>0.9995)direction=unit(add(scale(u,1-t),scale(v,t)));
    else if(cosine< -0.9995) {
      const axis=unit(cross(u,Math.abs(u[1])<0.9?[0,1,0]:[1,0,0]));
      direction=add(scale(u,Math.cos(Math.PI*t)),scale(cross(axis,u),Math.sin(Math.PI*t)));
    } else direction=scale(add(scale(u,Math.sin((1-t)*angle)),scale(v,Math.sin(t*angle))),1/Math.sin(angle));
    const target=from.target.map((n,i)=>n+(to.target[i]-n)*t);
    return {position:add(target,scale(direction,Math.hypot(...a)*(1-t)+Math.hypot(...b)*t)),target};
  }
  function defaultClock() {
    const now=()=>typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();
    const raf=typeof scope.requestAnimationFrame==='function'&&typeof scope.cancelAnimationFrame==='function';
    return {now,requestFrame:raf?fn=>scope.requestAnimationFrame(fn):fn=>setTimeout(fn,16),cancelFrame:raf?id=>scope.cancelAnimationFrame(id):id=>clearTimeout(id)};
  }
  function create({initialize,views,onState=()=>{},reducedMotion=true,clock=defaultClock()}={}) {
    need(typeof initialize==='function'&&typeof onState==='function','initialize and onState callbacks required');
    need(typeof reducedMotion==='boolean','boolean reducedMotion required');
    need(clock&&['now','requestFrame','cancelFrame'].every(k=>typeof clock[k]==='function'),'clock contract required');
    need(Array.isArray(views)&&views.length<=32,'zero to 32 named views required');
    const landmarks=new Map();
    for(const v of views) {
      need(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).every(k=>['id','label','position','target'].includes(k)),'invalid named view');
      need(typeof v.id==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(v.id)&&!landmarks.has(v.id),'invalid or duplicate view identity');
      need(typeof v.label==='string'&&v.label.trim().length>0&&v.label.length<=120&&!/[\x00-\x1f\x7f-\x9f]/.test(v.label),'invalid view label');
      landmarks.set(v.id,{id:v.id,label:v.label,...camera(v)});
    }
    let state='idle',generation=0,renderer=null,pending=null,visible=true,offscreen=false,stickyPause=false;
    let currentCamera=null,cameraKnown=false,viewId=null,size=null,motion=null,frame=null,motionEpoch=0;
    let error=null,pauseReason=null,emitting=false,queuedEmit=false;
    const diagnostics=[],released=new WeakSet();
    const record=code=>{diagnostics.push(code);if(diagnostics.length>8)diagnostics.shift();};
    const usable=()=>visible&&!offscreen&&(!size||(size.width>0&&size.height>0));
    const live=()=>state!=='disposed';
    function snapshot() {
      return {state,generation,visible,offscreen,reducedMotion,pauseReason,error,viewId,
        targetViewId:motion?motion.ids[motion.index]:null,camera:copyCamera(currentCamera),cameraKnown,
        size:size?{...size}:null,motion:motion?{kind:motion.kind,phase:motion.phase,index:motion.index,ids:[...motion.ids]}:null,
        views:[...landmarks.values()].map(v=>({id:v.id,label:v.label})),diagnostics:[...diagnostics]};
    }
    function emit() {
      if(emitting){queuedEmit=true;return;}
      emitting=true;let passes=0;
      do {queuedEmit=false;try{onState(snapshot());}catch(_){record('on_state_failed');}passes++;}while(queuedEmit&&passes<2);
      if(queuedEmit)record('reentrant_notification_suppressed');queuedEmit=false;emitting=false;
    }
    function disposeRenderer(candidate) {
      if(!candidate||(typeof candidate!=='object'&&typeof candidate!=='function')||released.has(candidate))return;
      released.add(candidate);
      try{if(typeof candidate.dispose==='function')candidate.dispose();}catch(_){record('renderer_cleanup_failed');}
    }
    function stopMotion() {
      motion=null;motionEpoch++;
      const owned=frame;frame=null;
      if(owned!==null)try{clock.cancelFrame(owned);}catch(_){record('clock_cancel_failed');}
    }
    function readCamera(candidate=renderer) {
      if(!candidate)return null;
      try {
        if(typeof candidate.getCamera!=='function')return null;
        const value=candidate.getCamera();return value==null?null:camera(value);
      } catch(_){record('camera_read_failed');return null;}
    }
    function captureCamera() {
      const observed=readCamera();
      if(observed){currentCamera=observed;cameraKnown=true;}
      return observed;
    }
    function fail(code) {
      if(!live())return false;
      stopMotion();generation++;const old=renderer;renderer=null;pending=null;state='error';error=code;pauseReason=null;
      disposeRenderer(old);emit();return false;
    }
    function writeCamera(value) {
      if(!renderer||!live())return false;
      const target=renderer,token=generation;
      try{if(target.setCamera(copyCamera(value))===false)throw new Error('rejected');}
      catch(_){return fail('camera_update_failed');}
      if(target!==renderer||token!==generation||!live())return false;
      currentCamera=copyCamera(value);cameraKnown=true;return true;
    }
    function time() {const value=clock.now();need(finite(value,0,Number.MAX_SAFE_INTEGER),'finite clock time required');return value;}
    function schedule() {
      if(!motion||frame!==null||state!=='ready'||!usable()||reducedMotion)return;
      const epoch=motionEpoch,token=generation;let requesting=true,synchronous=false;
      try {
        const handle=clock.requestFrame(()=>{
          if(requesting){synchronous=true;return;}
          if(epoch!==motionEpoch||token!==generation||!motion||state!=='ready'||!usable()||reducedMotion)return;
          frame=null;tick();
        });requesting=false;
        need(handle!==undefined&&handle!==null,'clock must return a cancellable handle');frame=handle;
        need(!synchronous,'clock must defer callbacks');
      } catch(_){requesting=false;fail('clock_schedule_failed');}
    }
    function prepareSegment(at) {
      if(!motion)return false;
      const active=motion,to=landmarks.get(motion.ids[motion.index]),observed=captureCamera();
      if(motion!==active)return false;
      motion.from=observed||(cameraKnown?copyCamera(currentCamera):null);motion.to=copyCamera(to);motion.started=at;motion.last=at;viewId=null;
      if(!motion.from||motion.duration===0) {
        if(!writeCamera(motion.to))return false;
        if(motion!==active)return false;
        viewId=to.id;
        if(motion.kind==='transition'){motion=null;return true;}
        motion.phase='dwell';
      } else motion.phase='move';
      return true;
    }
    function tick() {
      try {
        if(!motion)return;
        const active=motion,at=Math.max(time(),motion.last);motion.last=at;
        if(motion.phase==='move') {
          const progress=Math.min(1,Math.max(0,(at-motion.started)/motion.duration));
          if(!writeCamera(interpolate(motion.from,motion.to,progress*progress*(3-2*progress))))return;
          if(motion!==active)return;
          if(progress===1) {
            viewId=motion.ids[motion.index];
            if(motion.kind==='transition')motion=null;
            else {motion.phase='dwell';motion.started=at;}
            emit();
          }
        } else if(at-motion.started>=motion.dwell) {
          if(motion.index+1===motion.ids.length){motion=null;emit();}
          else {motion.index++;if(!prepareSegment(at))return;emit();}
        }
        schedule();
      } catch(_){fail('camera_timeline_failed');}
    }
    function resume() {
      if(!renderer||!usable()||!['ready','paused'].includes(state))return false;
      stickyPause=false;pauseReason=null;state='ready';return true;
    }
    function beginInitialization(explicitResume=false) {
      if(!live())return Promise.resolve(false);
      if(explicitResume&&usable())stickyPause=false;
      stopMotion();captureCamera();const old=renderer;renderer=null;disposeRenderer(old);
      const token=++generation;state='loading';error=null;pauseReason=null;
      const work=Promise.resolve().then(()=>{
        if(!live()||token!==generation)return null;
        return initialize();
      }).then(candidate=>{
        if(!live()||token!==generation){if(candidate!==renderer)disposeRenderer(candidate);return false;}
        try {need(candidate&&typeof candidate==='object'&&!released.has(candidate)&&['setCamera','resize','dispose'].every(k=>typeof candidate[k]==='function'),'fresh renderer protocol required');}
        catch(_){disposeRenderer(candidate);return fail('invalid_renderer');}
        renderer=candidate;
        if(size&&size.width>0&&size.height>0) {
          try{if(renderer.resize(size.width,size.height,size.dpr)===false)throw new Error('rejected');}
          catch(_){return fail('renderer_resize_failed');}
          if(!live()||token!==generation||renderer!==candidate)return false;
        }
        const first=[...landmarks.values()][0];
        const initial=(cameraKnown&&currentCamera)?currentCamera:(readCamera(candidate)||(first?copyCamera(first):null));
        if(!initial)return fail('initial_camera_unavailable');
        if(!writeCamera(initial))return false;
        if(first&&!viewId&&sameCamera(initial,first))viewId=first.id;
        state=usable()&&!stickyPause?'ready':'paused';pauseReason=state==='paused'?'explicit_resume_required':null;
        emit();return state==='ready';
      }).catch(()=>{if(!live()||token!==generation)return false;return fail('initialization_failed');}).finally(()=>{if(pending===work)pending=null;});
      pending=work;emit();return work;
    }
    function sameCamera(a,b) {return ['position','target'].every(k=>a[k].every((n,i)=>Math.abs(n-b[k][i])<1e-9));}
    function start() {
      if(!live())return Promise.resolve(false);
      if(state==='loading')return pending;
      if(renderer){const result=resume();if(result)emit();return Promise.resolve(result);}
      return beginInitialization(true);
    }
    function pause(reason) {
      stopMotion();captureCamera();stickyPause=true;pauseReason=reason;
      if(renderer&&['ready','paused'].includes(state))state='paused';
    }
    function selectView(id) {
      if(!live())return false;
      need(landmarks.has(id),'unknown view');if(!resume())return false;stopMotion();error=null;
      const target=landmarks.get(id);
      if(reducedMotion){if(!writeCamera(target))return false;viewId=id;emit();return true;}
      motion={kind:'transition',phase:'move',ids:[id],index:0,duration:400,dwell:0};
      try{if(!prepareSegment(time()))return false;}catch(_){return fail('camera_timeline_failed');}
      emit();schedule();return state==='ready';
    }
    function startTour(ids,{durationMs=650,dwellMs=1000}={}) {
      if(!live())return false;
      need(Array.isArray(ids)&&ids.length>0&&ids.length<=32&&ids.every(id=>landmarks.has(id)),'bounded known tour views required');
      need(finite(durationMs,0,10000)&&finite(dwellMs,0,60000),'bounded tour timing required');
      if(reducedMotion||!resume())return false;stopMotion();error=null;
      motion={kind:'tour',phase:'move',ids:[...ids],index:0,duration:durationMs,dwell:dwellMs};
      try{if(!prepareSegment(time()))return false;}catch(_){return fail('camera_timeline_failed');}
      emit();schedule();return state==='ready';
    }
    const api={
      start,retry(){return live()?beginInitialization(true):Promise.resolve(false);},snapshot,selectView,startTour,
      stopTour(){if(!live())return false;stopMotion();captureCamera();emit();return true;},
      interrupt(){if(!live())return false;stopMotion();cameraKnown=!!captureCamera();viewId=null;emit();return true;},
      setVisibility(value){if(!live())return false;need(typeof value==='boolean','boolean visibility required');visible=value;if(!value)pause('hidden');emit();return true;},
      setOffscreen(value){if(!live())return false;need(typeof value==='boolean','boolean offscreen required');offscreen=value;if(value)pause('offscreen');emit();return true;},
      setReducedMotion(value){if(!live())return false;need(typeof value==='boolean','boolean reducedMotion required');if(reducedMotion!==value){stopMotion();captureCamera();reducedMotion=value;}emit();return true;},
      resize(width,height,dpr=1){
        if(!live())return false;
        need(finite(width,0,16384)&&finite(height,0,16384)&&finite(dpr,0.1,8),'finite bounded size required');
        const next={width,height,dpr:Math.min(dpr,2)};
        if(size&&Object.keys(next).every(k=>next[k]===size[k]))return true;
        size=next;if(width===0||height===0){pause('zero-size');emit();return true;}
        if(renderer){const current=captureCamera()||(cameraKnown?copyCamera(currentCamera):null),target=renderer,token=generation;
          try{if(target.resize(width,height,next.dpr)===false)throw new Error('rejected');}catch(_){return fail('renderer_resize_failed');}
          if(!live()||token!==generation||renderer!==target)return false;
          if(current&&!writeCamera(current))return false;
        }emit();return true;
      },
      contextLost(){if(!live())return false;stopMotion();captureCamera();generation++;const old=renderer;renderer=null;pending=null;state='context-lost';error=null;pauseReason=null;disposeRenderer(old);emit();return true;},
      contextRestored(){return live()&&state==='context-lost'?beginInitialization():Promise.resolve(false);},
      dispose(){if(!live())return false;stopMotion();generation++;const old=renderer;renderer=null;pending=null;state='disposed';error=null;pauseReason=null;disposeRenderer(old);emit();return true;}
    };
    // Creation performs no initialization and owns no recurring clock.
    return Object.freeze(api);
  }
  scope.OAANativeSceneSession=Object.freeze({create});
  if(typeof module==='object'&&module.exports)module.exports=scope.OAANativeSceneSession;
})(typeof globalThis!=='undefined'?globalThis:this);
