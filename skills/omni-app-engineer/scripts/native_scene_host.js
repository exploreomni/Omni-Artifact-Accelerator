/* Optional original browser wiring, not a page template or an Omni SDK.
 * Caller owns authorized bridge, content layout and separately approved engine. */
(function (scope) {
  "use strict";
  function connect({session,canvas,container,document:doc=canvas.ownerDocument}) {
    const win=doc.defaultView,cleanups=[];let disposed=false,active=true;
    const need=(ok,message)=>{if(!ok)throw new Error(message);};
    need(session && canvas && container && win,"session and owned DOM required");
    const listen=(target,type,fn,options)=>{target.addEventListener(type,fn,options);cleanups.push(()=>target.removeEventListener(type,fn,options));};
    const oldTab=canvas.getAttribute("tabindex");
    canvas.setAttribute("tabindex","0");
    cleanups.push(()=>oldTab===null?canvas.removeAttribute("tabindex"):canvas.setAttribute("tabindex",oldTab));
    const resize=()=>{if(disposed)return;const r=container.getBoundingClientRect();session.resize(r.width,r.height,Math.min(win.devicePixelRatio||1,2));};
    const visibility=()=>{if(!disposed)session.setVisibility(active&&!doc.hidden);};
    const interrupt=()=>{if(!disposed)session.interrupt();};
    try {
      listen(doc,"visibilitychange",visibility);
      for(const event of ["pointerdown","wheel","keydown"])listen(canvas,event,interrupt,{capture:true,passive:true});
      if(typeof win.ResizeObserver==="function"){
        const observer=new win.ResizeObserver(resize);cleanups.push(()=>observer.disconnect());observer.observe(container);
      }else listen(win,"resize",resize);
      if(typeof win.IntersectionObserver==="function"){
        const observer=new win.IntersectionObserver(entries=>{
          if(!disposed)for(const entry of entries)if(entry.target===container)session.setOffscreen(!entry.isIntersecting);
        });cleanups.push(()=>observer.disconnect());observer.observe(container);
      }
      if(typeof win.matchMedia==="function"){
        const media=win.matchMedia("(prefers-reduced-motion: reduce)");
        const change=()=>{if(!disposed)session.setReducedMotion(media.matches);};
        listen(media,"change",change);change();
      }else session.setReducedMotion(true);
      visibility();resize();
    }catch(error){dispose();throw error;}
    function dispose(){if(disposed)return;disposed=true;for(const fn of cleanups.splice(0).reverse()){try{fn();}catch(_){}}session.dispose();}
    return Object.freeze({dispose,resize,setActive:value=>{active=Boolean(value);visibility();}});
  }

  // Useful plain controls, styled by the caller's reviewed design system. Labels
  // and details always use text nodes; no HTML/string-evaluating tooltip path.
  function controls({root,entities,views,onSelect,onView}) {
    if(!root || !Array.isArray(entities) || entities.length>1024 || !Array.isArray(views) || views.length>32 ||
        typeof onSelect!=="function" || typeof onView!=="function")throw new Error("bounded control contract required");
    const doc=root.ownerDocument,owned=[],buttons=new Map(),handlers=[];let disposed=false;
    function group(label,items,callback,selection){
      const region=doc.createElement("section"),heading=doc.createElement("h3"),list=doc.createElement("ul");
      heading.textContent=label;region.append(heading,list);root.append(region);owned.push(region);
      for(const item of items){
        const row=doc.createElement("li"),button=doc.createElement("button");
        button.type="button";button.textContent=item.label;button.dataset.entityId=item.id;
        if(selection){button.setAttribute("aria-pressed","false");buttons.set(item.id,button);}
        const fn=()=>{if(!disposed)callback(item.id);};button.addEventListener("click",fn);handlers.push(()=>button.removeEventListener("click",fn));
        row.append(button);list.append(row);
      }
    }
    group("Inspect objects",entities,onSelect,true);group("Camera views",views,onView,false);
    return Object.freeze({setSelection(id){for(const [key,b] of buttons)b.setAttribute("aria-pressed",String(key===id));},
      dispose(){if(disposed)return;disposed=true;handlers.splice(0).forEach(fn=>fn());owned.splice(0).forEach(node=>node.remove());buttons.clear();}});
  }
  scope.OAANativeSceneHost=Object.freeze({connect,controls});
})(typeof globalThis!=="undefined"?globalThis:this);
