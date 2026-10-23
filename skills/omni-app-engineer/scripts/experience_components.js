/* OAA application utilities, NOT an Omni SDK. No fetch, credentials, query
 * execution, provider API, policy changes, or native verification. */
(function (scope) {
  "use strict";
  const need = (ok, message) => { if (!ok) throw new Error(message); };
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const text = value => typeof value === "string" && value.trim().length > 0;
  const clone = value => structuredClone(value);

  function mapRows(rows, columns, maxRows = 10000) {
    need(Array.isArray(rows) && Number.isSafeInteger(maxRows) && maxRows > 0 && rows.length <= maxRows,
      "invalid or oversized row set");
    need(Array.isArray(columns) && columns.length > 0, "columns required");
    const keys = new Set(), outputs = new Set();
    for (const column of columns) {
      need(column && text(column.key) && text(column.as) && /^[a-z][a-z0-9_]*$/i.test(column.as) &&
        !["__proto__", "constructor", "prototype"].includes(column.as) &&
        !keys.has(column.key) && !outputs.has(column.as) &&
        ["string", "number", "integer", "boolean"].includes(column.type) &&
        typeof column.nullable === "boolean", "invalid column contract");
      keys.add(column.key); outputs.add(column.as);
    }
    return rows.map((row, index) => {
      need(row && typeof row === "object" && !Array.isArray(row), `invalid row ${index}`);
      const result = {};
      for (const column of columns) {
        need(Object.hasOwn(row, column.key), `missing input key ${column.key} in row ${index}`);
        const value = row[column.key];
        const valid = value === null ? column.nullable :
          column.type === "integer" ? Number.isSafeInteger(value) :
          column.type === "number" ? finite(value) : typeof value === column.type;
        need(valid, `invalid ${column.type} at ${column.key} in row ${index}`);
        result[column.as] = value;
      }
      return result;
    });
  }

  function createResource({validate, onState, now = Date.now, maxAgeMs}) {
    need(typeof validate === "function" && typeof onState === "function" &&
      typeof now === "function" && finite(maxAgeMs) && maxAgeMs > 0, "invalid resource contract");
    let active = null, sequence = 0, disposed = false;
    let state = {phase: "idle", contextKey: null, data: null, completeness: "unknown"};
    const snapshot = () => {
      const result = clone(state);
      if (["ready", "partial"].includes(result.phase)) {
        const instant = now(); need(finite(instant), "invalid retrieval clock");
        result.ageMs = Math.max(0, instant - result.fetchedAt);
        if (result.ageMs > maxAgeMs) result.phase = "stale";
      }
      return result;
    };
    const emit = () => { const result = snapshot(); onState(result); return result; };
    const current = ticket => !disposed && ticket === active;
    function begin(contextKey) {
      need(!disposed && text(contextKey), "disposed or invalid context");
      active = Object.freeze({sequence: ++sequence, contextKey});
      // Clear prior values. Retaining stale panels is a separate reviewed policy.
      state = {phase: "loading", contextKey, data: null, completeness: "unknown"};
      emit(); return active;
    }
    function accept(ticket, {data, completeness, evidenceRef, sourceAsOf = null}) {
      if (!current(ticket)) return false;
      need(["complete", "partial", "unknown"].includes(completeness) && text(evidenceRef) &&
        (sourceAsOf === null || text(sourceAsOf)), "invalid result evidence");
      const checked = validate(clone(data));
      const fetchedAt = now();
      need(finite(fetchedAt), "invalid retrieval clock");
      state = {phase: completeness === "complete" ? "ready" : "partial", contextKey: ticket.contextKey,
        data: clone(checked), completeness, evidenceRef, sourceAsOf, fetchedAt};
      active = null; emit(); return true;
    }
    function fail(ticket, phase, reason) {
      if (!current(ticket)) return false;
      need(["error", "restricted", "blocked"].includes(phase) && text(reason), "invalid failure");
      state = {phase, contextKey: ticket.contextKey, data: null, completeness: "unknown", reason};
      active = null; emit(); return true;
    }
    function dispose() { disposed = true; active = null; state = {phase: "disposed", data: null}; }
    return Object.freeze({begin, accept, fail, snapshot, refreshAge: () => disposed ? snapshot() : emit(), dispose});
  }

  function createMediaState({onState, stop = () => {}}) {
    need(typeof onState === "function" && typeof stop === "function", "invalid media contract");
    let token = null, disposed = false;
    let state = {phase: "idle", qualification: "unobserved"};
    const emit = () => { onState(clone(state)); return clone(state); };
    const current = ticket => !disposed && token === ticket;
    function begin(sourceKey) {
      need(!disposed && text(sourceKey), "disposed or invalid media source");
      stop(); token = Object.freeze({sourceKey});
      state = {phase: "loading", sourceKey, qualification: "unobserved"}; emit(); return token;
    }
    function frameLoaded(ticket) {
      if (!current(ticket)) return false;
      state.frameLoadObserved = true; emit(); return true; // Never marks ready.
    }
    function ready(ticket, evidence) {
      if (!current(ticket)) return false;
      need(evidence && ["simulation", "provider_event", "native_observation"].includes(evidence.method) &&
        text(evidence.reference), "readiness evidence required");
      state = {...state, phase: "ready", qualification: evidence.method, evidence: clone(evidence)};
      emit(); return true;
    }
    function unavailable(ticket, phase, reason) {
      if (!current(ticket)) return false;
      need(["blocked", "fallback"].includes(phase) && text(reason), "invalid media failure");
      stop(); token = null;
      state = {...state, phase, reason}; emit(); return true;
    }
    function dispose() { if (!disposed) { disposed = true; token = null; stop(); } }
    return Object.freeze({begin, frameLoaded, ready, unavailable, dispose, snapshot: () => clone(state)});
  }

  function weightedRate(rows) {
    need(Array.isArray(rows) && rows.length <= 10000, "invalid rate population");
    let eligible = 0, measuredEligible = 0, passed = 0;
    const seen = new Set(), missingIds = [];
    for (const row of rows) {
      need(row && text(row.id) && !seen.has(row.id) && Number.isSafeInteger(row.eligible) && row.eligible >= 0 &&
        (row.passed === null || (Number.isSafeInteger(row.passed) && row.passed >= 0 && row.passed <= row.eligible)),
      "invalid or duplicate rate observation");
      seen.add(row.id); eligible += row.eligible;
      if (row.passed === null) missingIds.push(row.id);
      else { measuredEligible += row.eligible; passed += row.passed; }
      need(Number.isSafeInteger(eligible) && Number.isSafeInteger(passed), "unsafe count total");
    }
    return {eligible, measuredEligible, passed, missingIds,
      rate: missingIds.length || eligible === 0 ? null : passed / eligible,
      measuredRate: measuredEligible === 0 ? null : passed / measuredEligible,
      coverage: eligible === 0 ? null : measuredEligible / eligible};
  }

  // Orthographic schematic coordinates. Caller owns meaning/units; no geography,
  // interpolation, height encoding or camera-derived business values are inferred.
  function projectScene(points, {width, height, yaw = 0, tilt = 35, padding = 30, bounds}) {
    need(Array.isArray(points) && points.length <= 1000 && finite(width) && finite(height) &&
      finite(padding) && padding >= 0 && width > 2 * padding && height > 2 * padding &&
      finite(yaw) && yaw >= -180 && yaw <= 180 && finite(tilt) && tilt >= 15 && tilt <= 80 &&
      bounds && [bounds.xMin, bounds.xMax, bounds.yMin, bounds.yMax].every(finite) &&
      bounds.xMin < bounds.xMax && bounds.yMin < bounds.yMax, "invalid scene frame");
    const a = yaw * Math.PI / 180, b = tilt * Math.PI / 180;
    const rotate = (x, y) => [x * Math.cos(a) - y * Math.sin(a),
      (x * Math.sin(a) + y * Math.cos(a)) * Math.sin(b)];
    const corners = [bounds.xMin, bounds.xMax].flatMap(x => [bounds.yMin, bounds.yMax].map(y => rotate(x, y)));
    const xs = corners.map(p => p[0]), ys = corners.map(p => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const scale = Math.min((width - 2 * padding) / (maxX - minX), (height - 2 * padding) / (maxY - minY));
    const seen = new Set();
    return points.map(point => {
      need(point && text(point.id) && !seen.has(point.id) && finite(point.x) && finite(point.y) &&
        point.x >= bounds.xMin && point.x <= bounds.xMax && point.y >= bounds.yMin && point.y <= bounds.yMax,
      "invalid, duplicate or out-of-bounds point");
      seen.add(point.id);
      const p = rotate(point.x, point.y);
      return {id: point.id, x: width / 2 + (p[0] - (minX + maxX) / 2) * scale,
        y: height / 2 + (p[1] - (minY + maxY) / 2) * scale};
    });
  }

  function monthCells(year, month) {
    need(Number.isInteger(year) && year >= 1900 && year <= 2200 && Number.isInteger(month) && month >= 1 && month <= 12,
      "invalid calendar month");
    const first = new Date(Date.UTC(year, month - 1, 1));
    const days = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const cells = Array(first.getUTCDay()).fill(null);
    for (let day = 1; day <= days; day++) cells.push(`${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
    while (cells.length % 7) cells.push(null);
    return cells;
  }

  function createCameraMotion({frame, cancelFrame, now, onFrame, durationMs = 180}) {
    need([frame, cancelFrame, now, onFrame].every(f => typeof f === "function") &&
      finite(durationMs) && durationMs >= 0 && durationMs <= 1000, "invalid camera motion contract");
    let pending = null, generation = 0, disposed = false;
    const cancel = () => { generation++; if (pending !== null) cancelFrame(pending); pending = null; };
    function move(from, to, reducedMotion = false) {
      need(!disposed && [from?.yaw, from?.tilt, to?.yaw, to?.tilt].every(finite) &&
        [from, to].every(p => p.yaw >= -180 && p.yaw <= 180 && p.tilt >= 15 && p.tilt <= 80) &&
        typeof reducedMotion === "boolean", "invalid camera transition");
      cancel(); const ticket = generation, started = now();
      need(finite(started), "invalid animation clock");
      if (reducedMotion || durationMs === 0) { onFrame({...to}); return; }
      const next = () => {
        if (disposed || ticket !== generation) return;
        pending = null;
        const instant = now(); need(finite(instant), "invalid animation clock");
        const t = Math.max(0, Math.min(1, (instant - started) / durationMs));
        const ease = 1 - (1 - t) ** 3;
        onFrame({yaw: from.yaw + (to.yaw - from.yaw) * ease, tilt: from.tilt + (to.tilt - from.tilt) * ease});
        if (!disposed && ticket === generation && t < 1) pending = frame(next);
      };
      pending = frame(next);
    }
    function dispose() { cancel(); disposed = true; }
    return Object.freeze({move, cancel, dispose});
  }

  const api = Object.freeze({mapRows, createResource, createMediaState, weightedRate, projectScene, monthCells, createCameraMotion});
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else scope.OAAExperience = api;
})(globalThis);
