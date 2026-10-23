/* Original synthetic renderer adapters. No provider/native API or business calculations. */
(function(scope) {
  "use strict";
  const B=scope.OAAExperienceBehaviors, $=key=>document.getElementById(key);
  const records=[{id:"archive-17",title:"Folded survey",material:"Paper",note:"A crease is described in the supplied note.",reference:"fixture-note-17"},
    {id:"archive-28",title:"Color study",material:"Glass",note:"The supplied note does not establish a condition rating.",reference:"fixture-note-28"},
    {id:"archive-39",title:"Spoken recollection",material:"Audio",note:"A transcript reference is present; no media is loaded.",reference:"fixture-note-39"}];
  let presentation="table", readingDetail=false, disposed=false;
  const listeners=[], rowListeners=[], detailListeners=[], buttons=new Map();
  const listen=(element,type,fn)=>{element.addEventListener(type,fn);listeners.push(()=>element.removeEventListener(type,fn));};
  const dynamic=(list,element,fn)=>{element.addEventListener("click",fn);list.push(()=>element.removeEventListener("click",fn));};
  const release=list=>{for(const remove of list.splice(0))remove();};
  const node=(tag,text)=>{const result=document.createElement(tag);if(text!==undefined)result.textContent=text;return result;};
  const choices=B.createEntityChoices({validate:value=>{if(!["summary","provenance"].includes(value))throw Error("Unknown local choice");return value;},onChange:()=>renderDetails()});
  const selection=B.createSelection({onChange:render,restore:(token,{current})=>{
    setPresentation(token.presentation,false);readingDetail=false;syncViews();
    // The injected adapter resolves identities in the currently rendered view.
    const button=buttons.get(token.presentation+":"+token.entityId);
    if(button&&current.ids.includes(token.entityId))button.focus();else $(token.presentation+"-results-title").focus();
    return {restored:button&&current.ids.includes(token.entityId)?"entity":"results_heading"};
  }});
  function syncViews() {
    $("table-presentation").hidden=presentation!=="table";$("reading-presentation").hidden=presentation!=="reading";
    $("reading-index").hidden=readingDetail;$("reading-detail-screen").hidden=!readingDetail;
    $("show-table").setAttribute("aria-pressed",String(presentation==="table"));$("show-reading").setAttribute("aria-pressed",String(presentation==="reading"));
  }
  function setPresentation(next,focus=true) {
    presentation=next;readingDetail=next==="reading"&&selection.snapshot().selectedId!==null;syncViews();
    if(focus)$(next+(next==="reading"&&readingDetail?"-detail-title":"-results-title")).focus();
  }
  function choose(entityId,origin) { selection.select(entityId,{presentation:origin,entityId});readingDetail=origin==="reading";syncViews();$(origin+"-detail-title").focus(); }
  function renderDetails() {
    release(detailListeners);
    const state=selection.snapshot(), record=records.find(r=>r.id===state.selectedId);
    for(const view of ["table","reading"]) {
      const detail=$(view+"-detail");detail.replaceChildren();
      $(view+"-detail-title").textContent=state.availability==="available"?record.title:"Record detail";
      if(state.availability!=="available") {
        detail.append(node("p",state.selectedId===null?"Choose a record. No default selection is imposed.":
          state.availability==="excluded"?"The complete current result excludes the selected identity. Choose another record or change the scope.":
          state.availability==="denied"?"Access is denied. Detail is withheld.":"Selection is retained, but current availability is unknown. An omitted page row does not prove exclusion."));
        continue;
      }
      const choice=choices.get(record.id),value=choice.present?choice.value:"summary";
      detail.append(node("p",value==="summary"?record.note:`Original identity: ${record.id}. Evidence: ${record.reference}. This is a synthetic source reference.`));
      const controls=node("div");controls.className="controls";
      for(const mode of ["summary","provenance"]) {
        const button=node("button",mode==="summary"?"Summary":"Provenance");button.type="button";button.setAttribute("aria-pressed",String(value===mode));
        dynamic(detailListeners,button,()=>{choices.set(record.id,mode);$(view+"-detail-title").focus();});controls.append(button);
      }
      detail.append(controls);
    }
  }
  function render(state) {
    release(rowListeners);
    buttons.clear();$("table-records").replaceChildren();$("reading-records").replaceChildren();
    $("scope-status").textContent=`Context: ${state.contextKey || "not selected"}; coverage: ${state.completeness}; selected availability: ${state.availability}.`;
    for(const entityId of state.ids) {
      const record=records.find(r=>r.id===entityId);
      for(const view of ["table","reading"]) {
        const button=node("button",`Open ${record.title}`);button.type="button";button.setAttribute("aria-pressed",String(state.selectedId===entityId));
        dynamic(rowListeners,button,()=>choose(entityId,view));buttons.set(view+":"+entityId,button);
        if(view==="table") {const row=node("tr"),action=node("td");row.append(node("td",record.title),node("td",record.material));action.append(button);row.append(action);$("table-records").append(row);}
        else {const item=node("li");item.append(node("h3",record.title),node("p",record.material+" · "+record.reference),button);$("reading-records").append(item);}
      }
    }
    renderDetails();syncViews();
  }
  function applyScope(kind) {
    const selected=selection.snapshot().selectedId,token=selection.begin("fixture:"+kind);
    selection.receive(token,{ids:kind==="denied"?[]:records.filter(r=>kind==="all"||r.id!==selected).map(r=>r.id),
      completeness:kind==="partial"?"partial":kind==="denied"?"unknown":"complete",access:kind==="denied"?"denied":"allowed"});
  }
  for(const view of ["table","reading"]) {listen($("show-"+view),"click",()=>setPresentation(view));listen($(view+"-return"),"click",()=>selection.returnToContext());}
  listen($("reading-browse"),"click",()=>{readingDetail=false;syncViews();$("reading-results-title").focus();});
  for(const kind of ["all","partial","excluded","denied"])listen($(kind),"click",()=>applyScope(kind));
  const events=[{id:"review-a",label:"Paper review",time:{kind:"date",value:"2028-04-02"}},
    {id:"review-b",label:"Remote handoff",time:{kind:"instant",value:"2028-04-02T00:30:00Z"}},
    {id:"review-c",label:"Audio review",time:{kind:"unknown",reason:"Date not supplied"}}];
  function renderTime(state) {
    $("month-label").textContent=state.month+" · "+state.timeZone;$("dates").replaceChildren();
    for(const cell of state.cells) {const element=node("div");element.className="date";
      if(cell){element.setAttribute("role","listitem");element.setAttribute("aria-label",cell.date+(cell.ids.length?": "+cell.ids.join(", "):"; no supplied event"));element.append(node("strong",String(Number(cell.date.slice(-2)))));for(const key of cell.ids)element.append(node("small",events.find(e=>e.id===key).label));}
      else element.setAttribute("aria-hidden","true");$("dates").append(element);
    }
    $("undated").textContent="Outside the date grid: "+state.undatedIds.map(key=>events.find(e=>e.id===key).label).join(", ");
  }
  const time=B.createTimeNavigation({events,timeZone:"America/New_York",month:"2028-04",weekStartsOn:1,onChange:renderTime});
  listen($("month-before"),"click",()=>time.shift(-1));listen($("month-after"),"click",()=>time.shift(1));listen($("time-zone"),"change",e=>time.setTimeZone(e.target.value));
  const preference=matchMedia("(prefers-reduced-motion: reduce)");$("reduced").checked=preference.matches;
  const frames=[{id:"f1",atMs:0,segment:"run-a",observations:[{id:"sample-q",value:3}]},
    {id:"f2",atMs:250,segment:"run-a",observations:[]},{id:"f3",atMs:500,segment:"run-a",observations:[{id:"sample-q",value:4}]},
    {id:"f4",atMs:1500,segment:"run-b",observations:[{id:"sample-q",value:7}]},{id:"f5",atMs:1750,segment:"run-b",observations:[{id:"sample-q",value:8}]}];
  function renderFrame(state) {
    $("recording-status").textContent=`${state.phase} · ${state.frame.id} · recorded ${state.frame.atMs} ms · ${state.frame.observations.length?"sample-q = "+state.frame.observations[0].value:"No supplied observation"}${state.phase==="gap"?". Segment gap: use Next frame to inspect the next segment.":""}`;
  }
  const playback=B.createRecordedPlayback({frames,reducedMotion:preference.matches,onFrame:renderFrame,
    clock:{now:()=>performance.now(),request:fn=>requestAnimationFrame(fn),cancel:key=>cancelAnimationFrame(key)}});
  listen($("play"),"click",()=>playback.play());listen($("pause"),"click",()=>playback.pause());
  listen($("frame-before"),"click",()=>playback.seek(Math.max(0,playback.snapshot().index-1)));
  listen($("frame-after"),"click",()=>playback.seek(Math.min(frames.length-1,playback.snapshot().index+1)));
  listen($("reduced"),"change",e=>playback.setReducedMotion(e.target.checked));
  listen(preference,"change",e=>{$("reduced").checked=e.matches;playback.setReducedMotion(e.matches);});
  listen(document,"visibilitychange",()=>{if(document.hidden)playback.pause();});
  function destroy(){if(disposed)return;disposed=true;selection.dispose();choices.dispose();playback.dispose();time.dispose();release(rowListeners);release(detailListeners);release(listeners);}
  listen(window,"pagehide",destroy);
  scope.OAABehaviorStudio=Object.freeze({destroy});
  applyScope("all");renderTime(time.snapshot());renderFrame(playback.snapshot());
})(globalThis);
