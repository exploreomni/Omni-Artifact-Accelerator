/* OAA controller, NOT an Omni browser SDK. Inject a separately reviewed native
 * bridge for the exact workbook query. No fetch, SQL construction, credentials,
 * storage or governed query changes. The bridge owns real callback correlation. */
(function (scope) {
  "use strict";
  function createQueryController({queryKey, bridge, inputs, onState, deriveScenario, includeInputState = false}) {
    if (typeof queryKey !== "string" || !/^[1-9][0-9]*$/.test(queryKey) || typeof bridge !== "function" ||
        typeof onState !== "function" || !Array.isArray(inputs) || typeof includeInputState !== "boolean") throw new Error("invalid controller contract");
    const definitions = new Map(), values = new Map();
    const validate = (definition, value) => {
      if (definition.type === "number") {
        if (typeof value !== "number" || !Number.isFinite(value) || value < definition.minimum ||
            value > definition.maximum) throw new Error("input outside reviewed domain");
      } else if (definition.type === "enum") {
        if (!definition.allowedValues.includes(value)) throw new Error("input outside reviewed domain");
      } else if (definition.type === "text") {
        if (typeof value !== "string" || value.length < definition.minLength || value.length > definition.maxLength ||
            /[\u0000-\u001f\u007f-\u009f]/u.test(value)) throw new Error("input outside reviewed text domain");
      } else throw new Error("unsupported input type");
      return value;
    };
    for (const input of inputs) {
      if (!input || typeof input.id !== "string" || !/^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(input.id) || definitions.has(input.id) ||
          !["governed_filter", "local_scenario"].includes(input.mode)) throw new Error("invalid input contract");
      const definition = {...input, allowedValues: input.allowedValues?.slice()};
      if (definition.type === "number" && (!Number.isFinite(definition.minimum) ||
          !Number.isFinite(definition.maximum) || definition.minimum > definition.maximum)) throw new Error("invalid bounds");
      if (definition.type === "enum" && (!Array.isArray(definition.allowedValues) ||
          !definition.allowedValues.length || definition.allowedValues.some(v => typeof v !== "string"))) throw new Error("invalid values");
      if (definition.type === "text") {
        definition.minLength ??= 0;
        if (!Number.isSafeInteger(definition.minLength) || !Number.isSafeInteger(definition.maxLength) ||
            definition.minLength < 0 || definition.maxLength < 1 || definition.maxLength > 4096 ||
            definition.minLength > definition.maxLength) throw new Error("invalid text bounds");
      }
      definitions.set(input.id, definition);
      values.set(input.id, validate(definition, input.default));
    }
    if (inputs.some(input => input.mode === "local_scenario") && typeof deriveScenario !== "function")
      throw new Error("reviewed local scenario function required");
    let generation = 0, disposed = false, phase = "idle", applied = null, governedResult = null, scenario = null;
    const live = () => { if (disposed) throw new Error("query controller disposed"); };
    const draft = () => Object.fromEntries(values);
    const matches = () => applied !== null && [...values].every(([id, value]) => applied[id] === value);
    const snapshot = () => structuredClone({state:phase, queryKey, generation, draft:draft(), applied,
      dirty:!matches(), resultMatchesDraft:governedResult !== null && matches(), governed:governedResult, scenario});
    const emit = (state, extra = {}) => {
      phase=state;
      const result=governedResult===null ? {} : {governed:structuredClone(governedResult), scenario:structuredClone(scenario)};
      onState(includeInputState ? {...snapshot(), ...extra} : {state, queryKey, ...result, ...extra});
    };
    const invalidate = () => { ++generation; governedResult=null; scenario=null; };
    const checkedValues = source => {
      if (!source || typeof source !== "object" || Array.isArray(source) ||
          Object.keys(source).length !== definitions.size || [...definitions.keys()].some(id => !Object.hasOwn(source,id)) ||
          Object.keys(source).some(id => !definitions.has(id))) throw new Error("restoration inputs do not match contract");
      return Object.fromEntries([...definitions].map(([id, definition]) => [id, validate(definition, source[id])]));
    };
    async function execute(submitted) {
      live(); invalidate(); const ticket=generation;
      applied={...submitted};
      const filters=Object.create(null), scenarios=Object.create(null);
      for (const [id, value] of Object.entries(submitted))
        (definitions.get(id).mode === "governed_filter" ? filters : scenarios)[id]=value;
      emit("loading");
      if (disposed || ticket !== generation) return {ignored:true};
      try {
        // Local tickets protect this promise only. The injected bridge must attach
        // the correct native result to it; a late callback cannot be relabeled here.
        const result = await bridge({queryKey, filters:Object.freeze({...filters})});
        if (disposed || ticket !== generation) return {ignored:true};
        if (!result || !Array.isArray(result.rows)) throw new Error("invalid native result");
        governedResult=structuredClone(result);
        scenario=deriveScenario ? deriveScenario(structuredClone(governedResult), Object.freeze({...scenarios})) : null;
        // Retry may deliberately submit an older applied scope while edits remain.
        emit(matches() ? (result.rows.length ? "ready" : "empty") : "stale");
        return {ignored:false};
      } catch (error) {
        if (disposed || ticket !== generation) return {ignored:true};
        governedResult=null; scenario=null;
        emit(error?.code === "FORBIDDEN" ? "restricted" : "error");
        return {ignored:false};
      }
    }
    function run() { live(); return execute(draft()); }
    function change(id, value) {
      live(); if (!definitions.has(id)) throw new Error("unknown input");
      values.set(id, validate(definitions.get(id), value));
      invalidate(); emit("stale"); // Compatible: even an edit invalidates pending delivery.
    }
    function reset() {
      live(); for (const [id, definition] of definitions) values.set(id, definition.default);
      invalidate(); emit("reset", {values:draft()});
      return run(); // Existing reset contract explicitly submits defaults.
    }
    function retry() { live(); if (applied===null) throw new Error("no submitted scope to retry"); return execute(applied); }
    function restore(saved) {
      live(); if (!saved || saved.queryKey!==queryKey) throw new Error("restoration query does not match contract");
      const nextDraft=checkedValues(saved.draft), nextApplied=saved.applied===null ? null : checkedValues(saved.applied);
      invalidate(); for (const [id,value] of Object.entries(nextDraft)) values.set(id,value);
      applied=nextApplied; emit("restored"); return snapshot(); // Fields only, never result evidence.
    }
    function cancel() { live(); invalidate(); emit("cancelled"); return snapshot(); }
    function dispose() { if (!disposed) { invalidate(); disposed=true; phase="disposed"; } }
    return Object.freeze({run, change, reset, retry, restore, cancel, snapshot, dispose});
  }
  // Provider-neutral delivery boundary. decode owns the inspected vendor envelope;
  // this adapter never guesses an SDK method, status, scalar type or request ID.
  function createQueryDelivery({run, subscribe, decode, columns, grain, limit,
      onState, correlation, evidenceRef, runSettlement}) {
    const C = typeof module !== "undefined" && module.exports ? require("./experience_components.js") : scope.OAAExperience;
    const need = (ok, message) => { if (!ok) throw new Error(message); };
    need(C && [run, subscribe, decode, onState].every(fn => typeof fn === "function") &&
      Number.isSafeInteger(limit) && limit > 0 && limit <= 100000 &&
      Array.isArray(grain) && grain.length > 0 &&
      runSettlement === "after_terminal_delivery" &&
      ["provider_correlated", "serialized_unqualified"].includes(correlation) &&
      typeof evidenceRef === "string" && evidenceRef.trim(), "invalid delivery handoff");
    const fields = structuredClone(columns), identity = structuredClone(grain);
    C.mapRows([], fields, limit, {grain: identity});
    let active = null, disposed = false, usable = true;
    let state = {phase:"idle", rows:[], completeness:"unknown", busy:false, usable, correlation, evidenceRef, runSettlement};
    const snapshot = () => structuredClone(state);
    const emit = patch => { state = {...state, ...patch}; onState(snapshot()); };
    const clear = (phase, reason = null) => emit({phase, rows:[], completeness:"unknown", reason});
    function release(ticket) {
      if (ticket.unsubscribe) {
        const fn = ticket.unsubscribe; ticket.unsubscribe = null;
        const result = fn();
        if (result && typeof result.then === "function") {
          Promise.resolve(result).catch(() => {});
          throw new Error("synchronous subscription cleanup required");
        }
      }
    }
    function consume(ticket, raw) {
      if (disposed || active !== ticket || ticket.invalidated || raw === undefined) return;
      try {
        const value = decode(raw); // Explicit normalized statuses, not vendor strings.
        need(value && ["loading", "complete", "error", "restricted", "stale"].includes(value.phase), "invalid decoded status");
        if (value.phase === "loading") return;
        if (value.phase !== "complete") { ticket.invalidated = true; clear(value.phase, "source_state"); return; }
        need(Array.isArray(value.columns) && value.columns.every(key => typeof key === "string") &&
          new Set(value.columns).size === value.columns.length && fields.every(c => value.columns.includes(c.key)), "missing or duplicate result columns");
        need(value.truncated === false && Array.isArray(value.rows) && value.rows.length < limit &&
          ["complete", "partial", "unknown"].includes(value.completeness), "unqualified result extent");
        const rows = C.mapRows(value.rows, fields, limit, {grain: identity});
        const terminal = JSON.stringify({rows, completeness:value.completeness});
        if (ticket.terminal === terminal) return; // Listener/run-return duplication.
        need(ticket.terminal === null, "conflicting terminal results");
        ticket.terminal = terminal;
        emit({phase:value.completeness === "complete" ? (rows.length ? "ready" : "empty") : "partial",
          rows, completeness:value.completeness, reason:null});
      } catch (_) { ticket.invalidated = true; clear("error", "input_contract_mismatch"); }
    }
    async function refresh() {
      need(!disposed, "delivery disposed");
      if (!usable) return {started:false, reason:"subscription_unusable"};
      if (active) return {started:false, reason:"busy"};
      const ticket = {terminal:null, invalidated:false, unsubscribe:null, subscribed:false};
      active = ticket; emit({phase:"loading", rows:[], completeness:"unknown", busy:true, reason:null});
      if (disposed) { active = null; return {started:false, reason:"disposed"}; }
      try {
        ticket.unsubscribe = subscribe(raw => consume(ticket, raw));
        need(typeof ticket.unsubscribe === "function", "qualified subscription cleanup required");
        ticket.subscribed = true;
        if (disposed) return {started:false, reason:"disposed"};
        // Keep busy until the actual run settles, even if a subscription completes
        // first or invalidate clears the UI. A local token is not native correlation.
        const returned = await run();
        consume(ticket, returned);
        if (!disposed && !ticket.invalidated && ticket.terminal === null) clear("error", "missing_terminal_result");
      } catch (_) {
        if (!ticket.subscribed) usable = false; // Registration may have partly succeeded.
        if (!disposed && !ticket.invalidated) clear("error", "run_or_subscription_failed");
      }
      finally {
        try { release(ticket); }
        catch (_) {
          usable = false; ticket.invalidated = true;
          if (!disposed) clear("error", "subscription_cleanup_failed");
        }
        active = null; if (!disposed) emit({busy:false, usable});
      }
      return {started:true};
    }
    function invalidate(phase = "stale") {
      need(!disposed && ["stale", "restricted", "error"].includes(phase), "invalid delivery invalidation");
      if (active) active.invalidated = true;
      clear(phase, "invalidated"); // Does not pretend to cancel the pending native run.
    }
    function dispose() {
      if (disposed) return;
      disposed = true;
      state = {...state, phase:"disposed", rows:[], completeness:"unknown", busy:false, usable:false};
      if (active) {
        active.invalidated = true;
        try { release(active); } catch (_) { state.reason = "subscription_cleanup_failed"; }
      }
    }
    return Object.freeze({refresh, invalidate, snapshot, dispose});
  }
  const api = Object.freeze({createQueryController, createQueryDelivery});
  if (typeof module !== "undefined" && module.exports) module.exports=api;
  else scope.OAAQueryController=api;
})(globalThis);
