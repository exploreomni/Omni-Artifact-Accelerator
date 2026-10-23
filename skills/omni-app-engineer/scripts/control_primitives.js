/* Optional DOM bindings, NOT a UI framework or vendor SDK. Caller supplies
 * semantic markup, labels, design tokens and query policy. No network/storage. */
(function (scope) {
  "use strict";
  const need=(ok,message)=>{if(!ok)throw new Error(message);};
  const owners=new WeakMap();
  function binding(element, events, read, write) {
    need(!owners.has(element), "control already bound; dispose before rebinding");
    let disposed=false;
    const live=()=>need(!disposed,"control disposed");
    const token={}; owners.set(element,token);
    events.forEach(([node,type,listener])=>node.addEventListener(type,listener));
    return Object.freeze({
      set(value,options={}) {live();return write(value,options);},
      snapshot() {return {...read()};},
      dispose() {if(disposed)return;disposed=true;events.forEach(([node,type,listener])=>node.removeEventListener(type,listener));if(owners.get(element)===token)owners.delete(element);}
    });
  }
  function bindSearch({input,clearButton,onChange,maxLength,error=null}) {
    need(input?.tagName==="INPUT" && clearButton?.tagName==="BUTTON" && typeof onChange==="function" &&
      Number.isSafeInteger(maxLength) && maxLength>0 && maxLength<=4096,"invalid search contract");
    need(!owners.has(input),"control already bound; dispose before rebinding");
    input.maxLength=maxLength;clearButton.type="button";
    let composing=false,last=null,valid=true,message="";
    const check=value=>typeof value==="string" && value.length<=maxLength && !/[\u0000-\u001f\u007f-\u009f]/u.test(value);
    const read=()=>({value:input.value,composing,valid,message});
    function reflect() {
      valid=check(input.value);message=valid?"":`Use at most ${maxLength} characters without control characters.`;
      input.setAttribute("aria-invalid",String(!valid));input.setCustomValidity?.(message);
      if(error)error.textContent=message;
      clearButton.disabled=input.value.length===0;
    }
    function commit(reason,notify) {
      reflect();if(valid&&notify&&last!==input.value){last=input.value;onChange(input.value,{reason});}
      return read();
    }
    function set(value,{notify=false}={}) {
      need(check(value)&&typeof notify==="boolean","invalid search value");
      composing=false;input.value=value;
      if(!notify)last=value;
      return commit("set",notify);
    }
    const onInput=event=>{if(!composing&&!event.isComposing)commit("input",true);};
    const start=()=>{composing=true;};
    const end=()=>{composing=false;commit("input",true);};
    const clear=event=>{event.preventDefault?.();composing=false;input.value="";commit("clear",true);input.focus();};
    reflect();last=valid?input.value:null;
    return binding(input,[[input,"input",onInput],[input,"compositionstart",start],[input,"compositionend",end],[clearButton,"click",clear]],read,set);
  }
  function bindSelect({select,onChange}) {
    need(select?.tagName==="SELECT"&&!select.multiple&&typeof onChange==="function","single native select required");
    const choices=()=>Array.from(select.options);
    const valid=value=>typeof value==="string"&&choices().some(o=>o.value===value&&!o.disabled&&!(o.parentElement?.tagName==="OPTGROUP"&&o.parentElement.disabled));
    need(valid(select.value),"select needs an enabled current option");
    let last=select.value;
    const read=()=>({value:select.value});
    const change=()=>{need(valid(select.value),"value outside enabled select options");if(last!==select.value){last=select.value;onChange(last);}};
    return binding(select,[[select,"change",change]],read,(value,{notify=false}={})=>{
      need(valid(value)&&typeof notify==="boolean","value outside enabled select options");select.value=value;if(notify)change();else last=value;return read();
    });
  }
  function bindRadios({fieldset,onChange}) {
    need(fieldset?.tagName==="FIELDSET"&&typeof onChange==="function","native radio fieldset required");
    const radios=Array.from(fieldset.querySelectorAll('input[type="radio"]'));
    need(radios.length>0&&radios.every(r=>r.name&&r.name===radios[0].name)&&new Set(radios.map(r=>r.value)).size===radios.length&&
      radios.filter(r=>r.checked).length===1,"one named radio group with one checked value required");
    const valid=value=>typeof value==="string"&&radios.some(r=>r.value===value&&!r.disabled);
    let last=radios.find(r=>r.checked).value;
    need(valid(last),"checked radio must be enabled");
    const read=()=>({value:radios.find(r=>r.checked)?.value??null});
    const change=()=>{const value=read().value;need(valid(value),"value outside enabled radios");if(value!==last){last=value;onChange(value);}};
    return binding(fieldset,radios.map(r=>[r,"change",change]),read,(value,{notify=false}={})=>{
      need(valid(value)&&typeof notify==="boolean","value outside enabled radios");radios.forEach(r=>{r.checked=r.value===value;});if(notify)change();else last=value;return read();
    });
  }
  function setButtonState(button,{busy=false,disabled=false,pressed}={}) {
    need(button?.tagName==="BUTTON"&&typeof busy==="boolean"&&typeof disabled==="boolean"&&
      (pressed===undefined||typeof pressed==="boolean"),"invalid button state");
    button.disabled=busy||disabled;button.setAttribute("aria-busy",String(busy));
    if(pressed!==undefined)button.setAttribute("aria-pressed",String(pressed));
  }
  function setSummary(element,{shown,total=null,completeness,filters=[]}) {
    need(element&&Number.isSafeInteger(shown)&&shown>=0&&["complete","partial","unknown"].includes(completeness)&&
      (total===null||(Number.isSafeInteger(total)&&total>=shown))&&(completeness!=="complete"||total!==null)&&
      Array.isArray(filters)&&filters.every(f=>f&&typeof f.label==="string"&&typeof f.value==="string"),"invalid result summary");
    const count=total===null?`${shown} supplied`:`${shown} of ${total} supplied`;
    const coverage=completeness==="complete"?"complete supplied scope":completeness==="partial"?"partial result":"completeness unknown";
    const active=filters.length?filters.map(f=>`${f.label}: ${f.value}`).join(" · "):"No applied filters";
    element.textContent=`${count} · ${coverage}. ${active}.`;
    return element.textContent;
  }
  const api=Object.freeze({bindSearch,bindSelect,bindRadios,setButtonState,setSummary});
  if(typeof module!=="undefined"&&module.exports)module.exports=api;else scope.OAAControls=api;
})(globalThis);
