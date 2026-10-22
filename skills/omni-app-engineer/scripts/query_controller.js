/* OAA controller, NOT an Omni browser SDK. Inject a separately reviewed native
 * bridge for the exact workbook query. This file never fetches, evaluates code,
 * discovers credentials, or changes governed query definitions. */
(function (scope) {
  "use strict";
  function createQueryController({queryKey, bridge, inputs, onState, deriveScenario}) {
    if (typeof queryKey !== "string" || !/^[1-9][0-9]*$/.test(queryKey) || typeof bridge !== "function" ||
        typeof onState !== "function" || !Array.isArray(inputs)) throw new Error("invalid controller contract");
    const definitions = new Map();
    const values = new Map();
    const validate = (definition, value) => {
      if (definition.type === "number") {
        if (typeof value !== "number" || !Number.isFinite(value) || value < definition.minimum ||
            value > definition.maximum) throw new Error("input outside reviewed domain");
      } else if (definition.type === "enum") {
        if (!definition.allowedValues.includes(value)) throw new Error("input outside reviewed domain");
      } else throw new Error("unsupported input type");
      return value;
    };
    for (const input of inputs) {
      if (!/^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(input.id) || definitions.has(input.id) ||
          !["governed_filter", "local_scenario"].includes(input.mode)) throw new Error("invalid input contract");
      const definition = {...input, allowedValues: input.allowedValues?.slice()};
      if (definition.type === "number" && (!Number.isFinite(definition.minimum) ||
          !Number.isFinite(definition.maximum) || definition.minimum > definition.maximum)) throw new Error("invalid bounds");
      if (definition.type === "enum" && (!Array.isArray(definition.allowedValues) ||
          !definition.allowedValues.length || definition.allowedValues.some(v => typeof v !== "string"))) throw new Error("invalid values");
      definitions.set(input.id, definition);
      values.set(input.id, validate(definition, input.default));
    }
    if (inputs.some(input => input.mode === "local_scenario") && typeof deriveScenario !== "function")
      throw new Error("reviewed local scenario function required");
    let generation = 0;
    let governedResult = null;
    const emit = (state, extra = {}) => onState({state, queryKey, ...extra});
    const partitions = () => {
      const filters = Object.create(null), scenarios = Object.create(null);
      for (const [id, value] of values) (definitions.get(id).mode === "governed_filter" ? filters : scenarios)[id] = value;
      return {filters, scenarios};
    };
    async function run() {
      const ticket = ++generation;
      const {filters, scenarios} = partitions();
      emit("loading");
      try {
        // The supplied bridge translates reviewed input IDs to the actual native
        // filter mechanism; it must enforce authorization through Omni.
        const result = await bridge({queryKey, filters: Object.freeze({...filters})});
        if (ticket !== generation) return {ignored: true};
        if (!result || !Array.isArray(result.rows)) throw new Error("invalid native result");
        governedResult = structuredClone(result);
        const scenario = deriveScenario ? deriveScenario(structuredClone(governedResult), Object.freeze({...scenarios})) : null;
        emit(result.rows.length ? "ready" : "empty", {governed: structuredClone(governedResult), scenario});
        return {ignored: false};
      } catch (error) {
        if (ticket !== generation) return {ignored: true};
        governedResult = null;
        emit(error?.code === "FORBIDDEN" ? "restricted" : "error");
        return {ignored: false};
      }
    }
    function change(id, value) {
      if (!definitions.has(id)) throw new Error("unknown input");
      values.set(id, validate(definitions.get(id), value));
      ++generation; // An edited input invalidates an outstanding result immediately.
      governedResult = null;
      emit("stale");
    }
    function reset() {
      for (const [id, definition] of definitions) values.set(id, definition.default);
      ++generation;
      governedResult = null;
      emit("reset", {values: Object.fromEntries(values)});
      return run();
    }
    return Object.freeze({run, change, reset});
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {createQueryController};
  else scope.OAAQueryController = Object.freeze({createQueryController});
})(globalThis);
