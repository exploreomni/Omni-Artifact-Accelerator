/* Original optional governed-data bridge. No fetching, query execution or storage.
 * The host supplies inspected query snapshots. Decoration needs no data contract. */
(function (scope) {
  "use strict";
  const need = (ok, message) => { if (!ok) throw new Error(message); };
  const plain = v => v && Object.getPrototypeOf(v) === Object.prototype;
  const keys = (v, allowed) => plain(v) && Object.keys(v).every(k => allowed.includes(k));
  const text = v => typeof v === "string" && v.length > 0 && v.length <= 200 && !/[\u0000-\u001f\u007f]/u.test(v);
  const metricId = v => typeof v === "string" && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$/u.test(v);
  const clone = v => JSON.parse(JSON.stringify(v));

  function create({scene, contract = null, renderer, onState = () => {}, now = () => Date.now()}) {
    const checked = scope.OAANativeSceneContract.validate(scene).scene;
    const entities = checked.entities.filter(e => e.role === "analytical").map(({id,label}) => ({id,label}));
    need(typeof onState === "function" && typeof now === "function", "invalid callbacks");
    if (!entities.length) {
      need(contract === null, "decorative scenes do not accept invented analytical bindings");
      return null;
    }
    need(keys(contract, ["queryId","keyField","fields","bindings","grain","maxAgeMs"]), "query contract required");
    need(text(contract.queryId) && text(contract.keyField) && text(contract.grain), "exact query, key and grain required");
    const expires = contract.maxAgeMs !== undefined && contract.maxAgeMs !== null;
    need(!expires || (Number.isSafeInteger(contract.maxAgeMs) && contract.maxAgeMs > 0 && contract.maxAgeMs <= 86400000), "invalid freshness limit");
    need(Array.isArray(contract.fields) && contract.fields.length > 0 && contract.fields.length <= 32, "bounded fields required");
    for (const f of contract.fields) {
      need(keys(f, ["id","type","unit","aggregation"]) && metricId(f.id) && f.type === "number" && text(f.unit) && text(f.aggregation), "numeric field contract required");
    }
    const fields = contract.fields.map(f => f.id);
    need(new Set(fields).size === fields.length && !fields.includes(contract.keyField), "ambiguous fields");
    need(renderer && typeof renderer.setSelection === "function", "selection renderer required");
    // Session owns camera and renderer lifetime. Disposing this bridge never disposes it.
    const c = clone(contract);
    const diagnostics=[];
    const decorate=state=>{
      let status=state.dataStatus;
      if(status==="ready"){
        let current;try{current=now();}catch(_){current=NaN;}
        const age=current-Date.parse(state.asOf);
        if(!Number.isFinite(age)||(expires&&age>c.maxAgeMs)||age< -5000)status="stale";
      }
      return {...state,dataStatus:status,diagnostics:[...diagnostics]};
    };
    const notify=state=>{try{onState(decorate(state));}catch(_){diagnostics.push("on_state_failed");if(diagnostics.length>8)diagnostics.shift();}};
    const control = scope.OAASpatialController.create({entities, bindings:c.bindings, metrics:fields,
      renderer:{setCamera(){},setSelection:id => renderer.setSelection(id),resize(){},dispose(){}},
      onState:notify});

    function resolve(token, snapshot) {
      const state = control.snapshot();
      need(!state.disposed, "data bridge disposed");
      if (token !== state.pending || state.pending === null) return {ignored:true};
      try {
        need(keys(snapshot, ["queryId","status","complete","capturedAt","rows"]) && snapshot.queryId === c.queryId, "snapshot query mismatch");
        need(["ready","empty","restricted","error","stale"].includes(snapshot.status), "invalid snapshot status");
        need(Array.isArray(snapshot.rows) && snapshot.rows.length <= entities.length, "bounded snapshot rows required");
        if (["restricted","error"].includes(snapshot.status)) {
          need(snapshot.rows.length === 0, "failure cannot expose data");
          return control.invalidate(snapshot.status);
        }
        need(snapshot.complete === true, "partial data cannot confirm this scene");
        const stamp = snapshot.capturedAt;
        need(typeof stamp === "string" && stamp.length <= 64, "timestamp required");
        const captured = Date.parse(stamp), current = now();
        need(Number.isFinite(current) && Number.isFinite(captured) && captured <= current + 5000, "invalid or future timestamp");
        const rows = snapshot.rows.map(row => {
          need(keys(row, [c.keyField, ...fields]) && Object.keys(row).length === fields.length + 1 && Object.hasOwn(row,c.keyField), "exact source fields required");
          const values = Object.create(null);
          for (const f of fields) { need(Object.hasOwn(row,f), "missing field"); values[f] = row[f]; }
          return {key:row[c.keyField], values:{...values}};
        });
        const status = snapshot.status === "ready" && expires && current - captured > c.maxAgeMs ? "stale" : snapshot.status;
        // The existing controller validates identities, duplicates, finite/null values.
        return decorate(control.resolve(token, {status, rows, asOf:stamp}));
      } catch (error) {
        control.invalidate("error"); // Never keep old values behind a failed refresh.
        throw error;
      }
    }
    return Object.freeze({begin:control.begin,resolve,invalidate:control.invalidate,select:id=>decorate(control.select(id)),
      snapshot:()=>decorate(control.snapshot()),
      // Only an explicit limit expires by age; a host may check it on resume.
      checkFreshness(){const state=control.snapshot();if(!state.disposed)notify(state);return decorate(state);},
      dispose:control.dispose,contract:() => clone(c)});
  }
  scope.OAANativeSceneData = Object.freeze({create});
})(typeof globalThis !== "undefined" ? globalThis : this);
