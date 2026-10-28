/* Original synthetic control study. Local promise adapter only, not a native API. */
(function (scope) {
  "use strict";
  const C=scope.OAAControls,B=scope.OAAExperienceBehaviors,Q=scope.OAAQueryController,E=scope.OAAExperience;
  const $=id=>document.getElementById(id),bindings=[],listeners=[],timers=new Map();
  const fixtures=[
    {id:"object-12",title:"Blue glaze bowl",kind:"ceramic",year:1971,state:"reviewed",note:"A shallow bowl with a matte edge and an uneven blue interior."},
    {id:"object-23",title:"Folded map",kind:"paper",year:1956,state:"reviewed",note:"A hand-drawn map folded along routes marked in pencil."},
    {id:"object-34",title:"Linen sample",kind:"textile",year:1982,state:"draft",note:"Loose woven cloth with a stitched corner and a retained maker label."},
    {id:"object-45",title:"Pocket notebook",kind:"paper",year:1964,state:"draft",note:"Blank leaves alternate with small sketches of everyday tools."},
    {id:"object-56",title:"Stoneware cup",kind:"ceramic",year:1990,state:"reviewed",note:"A thick-walled cup, with a short handle and unglazed foot."},
    {id:"object-67",title:"Woven ribbon",kind:"textile",year:1948,state:"reviewed",note:"A narrow ribbon with repeating stripes and an unfinished end."}
  ];
  let layout="desk",mode="index",sort="title",saved=null,nextResult="complete",rows=[],queryState=null,selectionTicket=null,disposed=false;
  const fields={};
  const listen=(element,type,fn)=>{element.addEventListener(type,fn);listeners.push([element,type,fn]);};
  const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
  const resource=E.createResource({validate:value=>{
    if(!Array.isArray(value)||value.some(r=>!fixtures.some(f=>f.id===r.id)))throw Error("unexpected fixture identity");return value;
  },onState:()=>{},maxAgeMs:null}); // No automatic expiry in this synthetic studio.
  const selection=B.createSelection({onChange:()=>renderDetail(),restore:(token)=>{
    mode="index";setLayout(token.layout);renderResults();const target=$(`${token.layout}-row-${token.id}`)||$(`${token.layout}-results-title`);target.focus();return true;
  }});
  function currentRows(){return [...rows].sort(sort==="year"?(a,b)=>a.year-b.year||a.id.localeCompare(b.id):(a,b)=>a.title.localeCompare(b.title)||a.id.localeCompare(b.id));}
  function renderDetail(){
    const selected=selection.snapshot(),record=selected.availability==="available"?rows.find(r=>r.id===selected.selectedId):null;
    for(const prefix of ["desk","reading"]){
      $(`${prefix}-detail-title`).textContent=record?record.title:"Selected record";
      const host=$(`${prefix}-detail`);host.replaceChildren();
      if(record){host.append(node("p",`${record.kind} · ${record.year} · ${record.state}`),node("p",record.note),node("small",`Original identity: ${record.id}. Synthetic record, no inferred history.`));}
      else {const p=node("p",selected.selectedId===null?"Choose an object from the supplied result.":selected.availability==="excluded"?"The selected identity is outside this complete supplied scope. Return to change filters or choose another object.":selected.availability==="denied"?"Access is denied; details are withheld.":"The selected identity is retained, but availability is unknown in the current partial or waiting scope. No replacement was chosen.");p.className="selection-note";host.append(p);}
      C.setButtonState($(`${prefix}-return`),{disabled:selected.selectedId===null});
    }
    $("desk-split").setAttribute("data-mode",mode);$("reading-index").hidden=mode==="detail";$("reading-detail-screen").hidden=mode!=="detail";
  }
  function open(record,prefix){mode="detail";selection.select(record.id,{layout:prefix,id:record.id});$(`${prefix}-detail-title`).focus();}
  function renderResults(){
    for(const prefix of ["desk","reading"]){
      const host=$(`${prefix}-rows`);host.replaceChildren();
      for(const record of currentRows()){
        const item=node(prefix==="desk"?"tr":"li"),openButton=node("button",prefix==="desk"?"Inspect":"Read this record");
        openButton.type="button";openButton.className="oaa-button";openButton.id=`${prefix}-row-${record.id}`;
        // These short-lived row listeners are retired with their row DOM, not global listeners.
        openButton.addEventListener("click",()=>{if(!disposed)open(record,prefix);});
        if(prefix==="desk"){const action=node("td");action.append(openButton);item.append(node("td",record.title),node("td",String(record.year)),action);}
        else{const body=node("div");body.append(node("h3",record.title),node("p",record.note),openButton);item.append(body);}
        host.append(item);
      }
      if(!rows.length){const empty=node(prefix==="desk"?"tr":"li");if(prefix==="desk"){const cell=node("td",queryState?.state==="empty"?"No objects match the applied scope.":"No current result. Apply the fields or retry a submitted scope.");cell.colSpan=3;empty.append(cell);}else empty.append(node("p",queryState?.state==="empty"?"No objects match the applied scope.":"No current result. Update the index or retry."));host.append(empty);}
    }
    renderDetail();
  }
  function setLayout(value){layout=value;$("desk-presentation").hidden=value!=="desk";$("reading-presentation").hidden=value!=="reading";C.setButtonState($("show-desk"),{pressed:value==="desk"});C.setButtonState($("show-reading"),{pressed:value==="reading"});renderDetail();}
  function onQuery(state){
    queryState=state;
    const displayable=["ready","empty"].includes(state.state)&&state.resultMatchesDraft;
    if(!displayable){rows=[];selectionTicket=selection.begin(`local-query-${state.generation}`);}
    else {rows=state.governed.rows;selection.receive(selectionTicket,{ids:rows.map(r=>r.id),completeness:state.governed.completeness,access:"allowed"});}
    if(state.state==="restricted")selection.receive(selectionTicket,{ids:[],completeness:"unknown",access:"denied"});
    for(const prefix of ["desk","reading"]){
      const f=fields[prefix];if(f){if(f.search.snapshot().valid||["reset","restored"].includes(state.state))f.search.set(state.draft.search);f.kind.set(state.draft.kind);f.state.set(state.draft.status);}
      const labels={loading:"Loading the submitted scope…",ready:"Applied scope is current.",empty:"Applied scope returned no records.",stale:state.governed?"Retry returned the older submitted scope. Newer edits remain unapplied; old rows are withheld.":"Fields changed. Apply to update results.",restored:"Fields restored only. Apply to obtain current results.",cancelled:"Waiting cancelled locally. Fields retained; no result accepted.",error:"Local simulated request failed. Retry submits the last applied scope.",restricted:"Access denied; no details available.",reset:"Default fields restored; submitting them now."};
      $(`${prefix}-state-line`).textContent=labels[state.state]||"Apply fields to begin.";
      C.setButtonState($(`${prefix}-apply`),{busy:state.state==="loading"});C.setButtonState($(`${prefix}-retry`),{busy:state.state==="loading",disabled:state.applied===null});C.setButtonState($(`${prefix}-cancel`),{disabled:state.state!=="loading"});
      const applied=state.applied;
      C.setSummary($(`${prefix}-summary`),{shown:rows.length,total:displayable?state.governed.total:null,completeness:displayable?state.governed.completeness:"unknown",filters:applied?[{label:"Applied search",value:applied.search||"Any"},{label:"Material",value:applied.kind},{label:"Status",value:applied.status}]:[]});
    }
    renderResults();
  }
  function syntheticBridge({filters}){
    const resultKind=nextResult;nextResult="complete";const ticket=resource.begin(JSON.stringify(filters));
    return new Promise((resolve,reject)=>{
      const handle=scope.setTimeout(()=>{
        timers.delete(handle);
        if(resultKind==="error"){resource.fail(ticket,"error","Explicit local simulated failure");reject(Error("local fixture failure"));return;}
        const filtered=fixtures.filter(r=>(filters.kind==="all"||r.kind===filters.kind)&&(filters.status==="all"||r.state===filters.status)&&`${r.title} ${r.note}`.toLowerCase().includes(filters.search.toLowerCase()));
        const supplied=resultKind==="partial"?filtered.slice(1,3):filtered;
        resource.accept(ticket,{data:supplied,completeness:resultKind,evidenceRef:"control-studio:synthetic-local-records"});
        resolve({rows:supplied,total:filtered.length,completeness:resultKind});
      },250);timers.set(handle,reject);
    });
  }
  const query=Q.createQueryController({queryKey:"1",bridge:syntheticBridge,includeInputState:true,onState:onQuery,inputs:[
    {id:"search",mode:"governed_filter",type:"text",maxLength:80,default:""},
    {id:"kind",mode:"governed_filter",type:"enum",allowedValues:["all","paper","ceramic","textile"],default:"all"},
    {id:"status",mode:"governed_filter",type:"enum",allowedValues:["all","reviewed"],default:"all"}
  ]});
  for(const prefix of ["desk","reading"]){
    const f=fields[prefix]={};
    f.search=C.bindSearch({input:$(`${prefix}-search`),clearButton:$(`${prefix}-clear`),error:$(`${prefix}-search-error`),maxLength:80,onChange:value=>query.change("search",value)});
    f.kind=C.bindSelect({select:$(`${prefix}-kind`),onChange:value=>query.change("kind",value)});
    f.state=C.bindRadios({fieldset:$(`${prefix}-state`),onChange:value=>query.change("status",value)});
    f.sort=C.bindSelect({select:$(`${prefix}-sort`),onChange:value=>{sort=value;for(const other of Object.values(fields))other.sort?.set(value);renderResults();}});
    bindings.push(...Object.values(f));
    listen($(`${prefix}-form`),"submit",event=>{event.preventDefault();if(f.search.snapshot().valid)query.run();});
    listen($(`${prefix}-reset`),"click",()=>query.reset());listen($(`${prefix}-retry`),"click",()=>query.retry());listen($(`${prefix}-cancel`),"click",()=>query.cancel());
    listen($(`${prefix}-return`),"click",()=>selection.returnToContext());
  }
  listen($("show-desk"),"click",()=>setLayout("desk"));listen($("show-reading"),"click",()=>setLayout("reading"));
  listen($("save-fields"),"click",()=>{saved=query.snapshot();$("restore-fields").disabled=false;$("rehearsal-status").textContent="Fields kept in this page instance only.";});
  listen($("restore-fields"),"click",()=>{if(saved)query.restore(saved);});
  listen($("partial-next"),"click",()=>{nextResult="partial";$("rehearsal-status").textContent="Next local request will return a partial page.";});
  listen($("fail-next"),"click",()=>{nextResult="error";$("rehearsal-status").textContent="Next local request will fail explicitly.";});
  function destroy(){if(disposed)return;disposed=true;query.dispose();selection.dispose();resource.dispose();bindings.forEach(b=>b.dispose());listeners.forEach(([el,type,fn])=>el.removeEventListener(type,fn));for(const [handle,reject] of timers){scope.clearTimeout(handle);reject(Error("studio disposed"));}timers.clear();scope.removeEventListener("pagehide",destroy);}
  scope.addEventListener("pagehide",destroy);scope.OAAControlStudio=Object.freeze({destroy});
  query.run(); // Explicit example first-use policy, not a controller default.
})(globalThis);
