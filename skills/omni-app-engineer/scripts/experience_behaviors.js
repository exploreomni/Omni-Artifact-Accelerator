/* Headless OAA behaviors. No DOM, styling, network, provider SDK, metric formulas,
 * storage or native qualification. Callers supply identities and evidence scope. */
(function (scope) {
  "use strict";
  const C = typeof module !== "undefined" && module.exports ? require("./experience_components.js") : scope.OAAExperience;
  const need = (ok, message) => { if (!ok) throw new Error(message); };
  const id = value => typeof value === "string" && value.trim().length > 0 && value.length <= 240;
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const copy = value => structuredClone(value);

  function createSelection({onChange, restore}) {
    need(typeof onChange === "function" && typeof restore === "function", "selection callbacks required");
    let disposed = false, ticket = null, generation = 0, origin = null;
    let state = {contextKey:null, selectedId:null, availability:"none", ids:[], completeness:"unknown", access:"unknown", pending:false};
    const snapshot = () => copy(state);
    const emit = () => { onChange(snapshot()); return snapshot(); };
    const live = () => need(!disposed, "selection disposed");
    function begin(contextKey) {
      live(); need(id(contextKey), "invalid context key");
      ticket = Object.freeze({generation:++generation});
      state = {...state, contextKey, ids:[], completeness:"unknown", access:"unknown", pending:true,
        availability:state.selectedId === null ? "none" : "unknown"};
      emit(); return ticket;
    }
    function receive(token, {ids, completeness, access}) {
      if (disposed || token !== ticket || ticket === null) return false;
      need(Array.isArray(ids) && ids.length <= 10000 && ids.every(id) && new Set(ids).size === ids.length &&
        ["complete","partial","unknown"].includes(completeness) && ["allowed","denied"].includes(access), "invalid result scope");
      need(access !== "denied" || (ids.length === 0 && completeness === "unknown"), "denied scope must not supply identities or completeness");
      const availability = access === "denied" ? "denied" : state.selectedId === null ? "none" :
        ids.includes(state.selectedId) ? "available" : completeness === "complete" ? "excluded" : "unknown";
      if (access === "denied") origin = null;
      state = {...state, selectedId:access === "denied" ? null : state.selectedId,
        ids:[...ids], completeness, access, pending:false, availability};
      ticket = null; emit(); return true;
    }
    function select(entityId, returnToken) {
      live(); need(id(entityId) && state.access === "allowed" && state.ids.includes(entityId), "selection not in current supplied results");
      need(returnToken !== undefined, "explicit return token required");
      const saved = copy(returnToken);
      origin = {contextKey:state.contextKey, token:saved};
      state = {...state, selectedId:entityId, availability:"available"}; emit();
    }
    function order(ids) {
      live(); need(state.access === "allowed" && Array.isArray(ids) && ids.length === state.ids.length &&
        new Set(ids).size === ids.length && ids.every(value => state.ids.includes(value)), "order must preserve supplied identity set");
      state = {...state, ids:[...ids]}; return emit();
    }
    function step(delta) {
      live(); need(delta === -1 || delta === 1, "step must be -1 or 1");
      if (origin === null || state.availability !== "available") return false;
      const index = state.ids.indexOf(state.selectedId), next = index + delta;
      if (index < 0 || next < 0 || next >= state.ids.length) return false;
      // Traversal follows the same supplied ordering and never captures a detail
      // page's focus/scroll as a new list origin.
      state = {...state, selectedId:state.ids[next]}; emit(); return true;
    }
    function clear() { live(); origin = null; state = {...state, selectedId:null, availability:"none"}; return emit(); }
    function returnToContext() {
      live(); if (origin === null) return false;
      // Restoration owns focus/scroll resolution and may choose an honest fallback.
      return restore(copy(origin.token), {originContextKey:origin.contextKey, current:snapshot()});
    }
    function dispose() { disposed = true; ticket = null; origin = null; }
    return Object.freeze({begin, receive, select, order, step, clear, returnToContext, snapshot, dispose});
  }

  function restoreFocus(keys, {resolve, isUsable, focus}) {
    need(Array.isArray(keys) && keys.length > 0 && keys.length <= 32 &&
      [resolve, isUsable, focus].every(fn => typeof fn === "function"), "invalid focus restoration contract");
    for (const key of keys) {
      if (key === null || key === undefined) continue;
      need(id(key), "invalid focus key");
      const target = resolve(key);
      if (target !== null && target !== undefined && isUsable(target)) { focus(target); return key; }
    }
    return null; // Caller must include a usable heading or another explicit fallback.
  }

  function createEntityChoices({validate, onChange, maxEntities = 1000}) {
    need(typeof validate === "function" && typeof onChange === "function" && Number.isInteger(maxEntities) &&
      maxEntities > 0 && maxEntities <= 10000, "invalid choice contract");
    const choices = new Map(); let disposed = false;
    const live = () => need(!disposed, "choices disposed");
    function set(entityId, value) {
      live(); need(id(entityId) && (choices.has(entityId) || choices.size < maxEntities), "invalid identity or choice capacity reached");
      const checked = copy(validate(copy(value), entityId));
      need(checked !== undefined, "choice validator must return a value");
      choices.set(entityId, checked); onChange({entityId, present:true, value:copy(checked)});
    }
    function get(entityId) { live(); need(id(entityId), "invalid entity identity"); return choices.has(entityId) ? {present:true,value:copy(choices.get(entityId))} : {present:false,value:null}; }
    function forget(entityId) { live(); need(id(entityId), "invalid entity identity"); const existed=choices.delete(entityId); if(existed)onChange({entityId,present:false,value:null}); return existed; }
    function dispose() { disposed=true; choices.clear(); }
    return Object.freeze({set, get, forget, dispose});
  }

  function createRecordedPlayback({frames, clock, onFrame, reducedMotion = false, coverage = null}) {
    need(Array.isArray(frames) && frames.length > 0 && frames.length <= 10000 && typeof onFrame === "function" &&
      clock && [clock.now,clock.request,clock.cancel].every(f=>typeof f === "function") && typeof reducedMotion === "boolean", "invalid recording contract");
    need(coverage === null || (coverage && ["era", "selection", "participants"].every(key => id(coverage[key])) &&
      coverage.observedOnly === true), "invalid recording coverage");
    const recordingCoverage = copy(coverage);
    const recording = copy(frames), ids = new Set(), segments = new Set();
    let priorTime = -1, priorSegment = null, totalObservations = 0;
    for(const frame of recording) {
      need(frame && id(frame.id) && !ids.has(frame.id) && id(frame.segment) && finite(frame.atMs) && frame.atMs >= 0 && frame.atMs > priorTime &&
        Array.isArray(frame.observations) && frame.observations.length <= 1000, "invalid or unordered frame");
      if(frame.segment !== priorSegment) { need(!segments.has(frame.segment), "segment must be contiguous"); segments.add(frame.segment); }
      need(frame.observations.every(o=>o && typeof o === "object" && !Array.isArray(o) && id(o.id)) &&
        new Set(frame.observations.map(o=>o.id)).size === frame.observations.length, "invalid observation identities");
      totalObservations += frame.observations.length; need(totalObservations <= 100000, "recording too large");
      ids.add(frame.id); priorTime=frame.atMs; priorSegment=frame.segment;
    }
    let index=0, phase="idle", reduced=reducedMotion, handle=null, generation=0, disposed=false, reason=null;
    const nextSegment = () => index+1 < recording.length && recording[index+1].segment !== recording[index].segment ? index+1 : null;
    const snapshot = () => copy({index, phase, frame:recording[index], coverage:recordingCoverage,
      reducedMotion:reduced, nextSegmentIndex:nextSegment(), reason});
    const emit = () => { onFrame(snapshot()); return snapshot(); };
    const live = () => need(!disposed, "recording disposed");
    function cancel() { generation++; if(handle !== null)clock.cancel(handle);handle=null; }
    function pause() { live(); cancel();phase="paused";reason=null;return emit(); }
    function seek(value) { live();need(Number.isInteger(value)&&value>=0&&value<recording.length,"invalid frame index");cancel();index=value;phase="paused";reason=null;return emit(); }
    function play({speed = 1} = {}) {
      live(); need(finite(speed)&&speed>=0.25&&speed<=4,"invalid playback speed");
      cancel(); reason=null;
      if(reduced) { phase="paused";reason="reduced_motion";emit();return false; }
      if(index === recording.length-1) { phase="ended";emit();return false; }
      if(nextSegment() !== null) { phase="gap";emit();return false; }
      const started=clock.now(); need(finite(started),"invalid playback clock");
      const at=recording[index].atMs, token=generation;
      phase="playing";emit();
      function tick() {
        if(disposed||token!==generation)return;
        handle=null;const instant=clock.now();
        if(!finite(instant)||instant<started) { cancel();phase="error";reason="invalid_clock";emit();return; }
        const target=at+(instant-started)*speed;let changed=false;
        while(index+1<recording.length&&recording[index+1].segment===recording[index].segment&&recording[index+1].atMs<=target) { index++;changed=true; }
        if(index===recording.length-1) { phase="ended";emit();return; }
        if(nextSegment()!==null) { phase="gap";emit();return; }
        if(changed)emit();
        if(!disposed&&token===generation)handle=clock.request(tick);
      }
      if(!disposed&&token===generation)handle=clock.request(tick);
      return true;
    }
    function setReducedMotion(value) { live();need(typeof value==="boolean","invalid motion preference");reduced=value;if(value)cancel();if(value&&phase==="playing")phase="paused";return emit(); }
    function series(entityId, throughIndex = index) {
      need(id(entityId)&&Number.isInteger(throughIndex)&&throughIndex>=0&&throughIndex<recording.length,"invalid series scope");
      const result=[];let current=[], segment=null;
      const flush=()=>{if(current.length)result.push(current);current=[];};
      for(const frame of recording.slice(0,throughIndex+1)) {
        if(segment!==frame.segment)flush();segment=frame.segment;
        const observation=frame.observations.find(o=>o.id===entityId);
        if(!observation)flush();else current.push({frameId:frame.id,atMs:frame.atMs,observation:copy(observation)});
      }
      flush();return result;
    }
    function dispose() { if(!disposed){cancel();disposed=true;phase="disposed";} }
    return Object.freeze({play,pause,seek,setReducedMotion,series,snapshot,dispose});
  }

  function validDate(value) {
    need(typeof value==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(value),"date-only value must be YYYY-MM-DD");
    const [year,month,day]=value.split("-").map(Number);
    need(year>=1900&&year<=2200&&month>=1&&month<=12&&day>=1&&day<=new Date(Date.UTC(year,month,0)).getUTCDate(),"invalid calendar date");
    return value;
  }
  function normalizeEvents(events,timeZone) {
    need(Array.isArray(events)&&events.length<=10000&&id(timeZone),"invalid event contract");
    const formatter=new Intl.DateTimeFormat("en-US",{timeZone,year:"numeric",month:"2-digit",day:"2-digit"});
    const seen=new Set();
    return events.map(event=>{
      need(event&&id(event.id)&&!seen.has(event.id)&&event.time&&["date","instant","unknown"].includes(event.time.kind),"invalid or duplicate event");
      seen.add(event.id);let dayKey=null,instantMs=null;
      const time=event.time;
      if(time.kind==="date")dayKey=validDate(time.value);
      else if(time.kind==="instant") {
        need(typeof time.value==="string","instant string required");
        const match=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,3})?(Z|[+-](\d{2}):(\d{2}))$/.exec(time.value);
        need(match,"instant requires seconds and an explicit offset");validDate(match[1]);
        need(+match[2]<24&&+match[3]<60&&+match[4]<60&&(!match[6]||(+match[6]<=14&&+match[7]<60&&(+match[6]<14||+match[7]===0))),"invalid instant time or offset");
        instantMs=Date.parse(time.value);need(finite(instantMs),"invalid instant");
        const parts=Object.fromEntries(formatter.formatToParts(new Date(instantMs)).map(p=>[p.type,p.value]));
        dayKey=validDate(`${parts.year}-${parts.month}-${parts.day}`);
      } else need(id(time.reason),"unknown date reason required");
      return {id:event.id,dayKey,instantMs,timeKind:time.kind,original:copy(event)};
    });
  }
  function createTimeNavigation({events,timeZone,month,weekStartsOn = 1,onChange}) {
    need(C&&typeof C.monthCells==="function"&&typeof onChange==="function"&&Number.isInteger(weekStartsOn)&&weekStartsOn>=0&&weekStartsOn<=6,"invalid time navigation contract");
    let disposed=false, source=copy(events), normalized=normalizeEvents(source,timeZone);
    function checkMonth(value) { need(typeof value==="string"&&/^\d{4}-\d{2}$/.test(value),"month must be YYYY-MM");validDate(value+"-01");return value; }
    let activeMonth=checkMonth(month),zone=timeZone;
    function snapshot() {
      const [year,m]=activeMonth.split("-").map(Number),dates=C.monthCells(year,m).filter(Boolean);
      const leading=(new Date(Date.UTC(year,m-1,1)).getUTCDay()-weekStartsOn+7)%7;
      const cells=Array(leading).fill(null).concat(dates);while(cells.length%7)cells.push(null);
      return copy({month:activeMonth,timeZone:zone,weekStartsOn,
        cells:cells.map(date=>date===null?null:{date,ids:normalized.filter(e=>e.dayKey===date).map(e=>e.id)}),
        events:normalized,undatedIds:normalized.filter(e=>e.dayKey===null).map(e=>e.id)});
    }
    const emit=()=>{const value=snapshot();onChange(value);return value;};
    const live=()=>need(!disposed,"time navigation disposed");
    function setMonth(value){live();activeMonth=checkMonth(value);return emit();}
    function shift(delta){live();need(Number.isInteger(delta)&&Math.abs(delta)<=120,"invalid month delta");const [year,m]=activeMonth.split("-").map(Number);const date=new Date(Date.UTC(year,m-1+delta,1));return setMonth(`${date.getUTCFullYear()}-${String(date.getUTCMonth()+1).padStart(2,"0")}`);}
    function setTimeZone(value){live();const result=normalizeEvents(source,value);zone=value;normalized=result;return emit();}
    function replaceEvents(value){live();const result=normalizeEvents(value,zone);source=copy(value);normalized=result;return emit();}
    function dispose(){disposed=true;}
    return Object.freeze({setMonth,shift,setTimeZone,replaceEvents,snapshot,dispose});
  }
  const api=Object.freeze({createSelection,restoreFocus,createEntityChoices,createRecordedPlayback,normalizeEvents,createTimeNavigation});
  if(typeof module!=="undefined"&&module.exports)module.exports=api;else scope.OAAExperienceBehaviors=api;
})(globalThis);
