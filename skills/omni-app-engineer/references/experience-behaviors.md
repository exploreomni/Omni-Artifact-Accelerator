# Neutral interaction behaviors

Use these optional controllers when a selected App needs identity-preserving detail/return, per-entity view choices, recorded observations or date navigation. They implement behavior, not a required layout, palette, navigation system, metric definition or cohort policy. A faithful migration retains its selected semantics. No prior engagement assets or application implementation are included.

[`experience_behaviors.js`](../scripts/experience_behaviors.js) exports `OAAExperienceBehaviors` in classic browser scripts and the same functions through CommonJS. Load [`experience_components.js`](../scripts/experience_components.js) first in the browser; the new module reuses its month-cell utility. Both are OAA code, **not an Omni SDK**. They perform no network requests, persistence, query execution, permission changes or native qualification. Keep the existing native bridge and immutable runtime fragments intact.

## Selection and return

```js
const selection = OAAExperienceBehaviors.createSelection({
  onChange: state => renderSelectedState(state),
  restore: (token, context) => restoreInCurrentLayout(token, context)
});
const ticket = selection.begin("reviewed-query-and-filter-generation");
selection.receive(ticket, {
  ids: ["record-a", "record-b"], completeness: "partial", access: "allowed"
});
selection.select("record-a", {focusKey: "row-record-a", scrollPosition: 120});
selection.returnToContext();
```

The host owns the result-to-ticket association; this controller cannot manufacture correlation absent from the real bridge. `begin(contextKey)` invalidates prior tickets and clears the supplied ID list. A selected original ID remains, with unknown availability. `receive(ticket,{ids,completeness,access})` accepts the current generation once; obsolete callbacks return false. Completeness is a qualified caller declaration, not inferred from row count or success.

| Current evidence | Selected availability | Appropriate interpretation |
| --- | --- | --- |
| Selected ID is in an allowed result | `available` | Present in the supplied scope. |
| Omitted from partial/paginated/unknown result | `unknown` | No exclusion or replacement may be inferred. |
| Omitted from a complete filtered result | `excluded` | Confirmed outside that result; ID is retained for explicit context handling. |
| Access denied | `denied` | Clear selected/origin identities and withhold detail; do not present a filter exclusion or empty-result conclusion. |
| No selected ID | `none` | No automatic first/peak entity is chosen. |

IDs must be unique nonblank strings of at most 240 characters, with at most 10,000 supplied IDs. Denied results require `ids:[]` and `completeness:"unknown"`; these prevent contradictory identity/coverage declarations, not unauthorized upstream access. Use one controller for one coherent identity namespace. A context key describes current scope, not a new namespace or authorization boundary.

`select(id,returnToken)` requires that ID in the current allowed result and an explicit structured-cloneable token. It saves the origin context and a defensive copy. `returnToContext()` calls the injected restoration callback with the token and `{originContextKey,current}`. Resolve focus/scroll against the **current** layout; if the old element is absent, use an explicitly chosen safe destination. No selector, scroll container or routing strategy is built into the core. `clear()` explicitly removes selection/origin; denied results do so automatically. `snapshot()` returns copied state; `dispose()` ignores late results and prevents further actions. The controller stores IDs only; the host must withhold restricted/stale detail values separately.

Use the same ordered identity list for the visible index and detail traversal.
`order(ids)` accepts only a reordering of the current allowed identity set;
`step(-1|1)` moves through that order without replacing the original return token.
At a boundary or when the selected identity is not currently available, it returns
false. Capture origin focus, scroll, page and sort once on the initial drill;
calling `select` for every next/previous step would incorrectly capture detail
scroll as the index origin. A new deliberate drill may capture a new origin.

`restoreFocus(keys,{resolve,isUsable,focus})` tries the caller's ordered fallback
keys and returns the first restored key, or null. Supply actual current-layout
resolution, a predicate rejecting disabled/hidden/disconnected targets, and the
native focus operation. Include an explicit focusable heading after the origin
and any alternate control: the opposite pagination button may also be disabled.
Use stable control IDs for a rerendering action, preserve selection/caret only for
the same surviving input, and restore scroll independently of focus. Abstract
callback tests verify selection logic, not browser focus or accessibility.

When a user can request a known source identity before its result arrives, retain that pending intent in the host before checking readiness. The selection controller's allowed-result rule still applies: a pending request is not evidence that the record is available or accessible. Resolve only the matching identity when its qualified inputs arrive; keep waiting, missing or denied treatment explicit. A later explicit choice supersedes the earlier request, while unrelated input or a first-use default must not replace it. Preserve the request across the selected return path; clear it only under the declared reset/cancellation rule. Keep query-generation correlation at the qualified bridge boundary.

## Per-entity choices

`createEntityChoices({validate,onChange,maxEntities=1000})` returns `set(id,value)`, `get(id)`, `forget(id)` and `dispose()`. `get` returns `{present,value}` so unset is distinct from an explicit null choice. The injected validator receives a copy plus the entity ID and must return the reviewed value; it owns valid measures/modes and scope changes. Values are copied on entry/exit. Capacity is bounded without silent eviction; call `forget` deliberately. There are no automatic defaults, business formulas, cohort comparisons or durable storage.

## Recorded observation playback

Preserve each source's era and selected population. A summary from a later period
is not the population represented by an older recording. Pass optional
`coverage:{era,selection,participants,observedOnly:true}` with nonblank strings to
`createRecordedPlayback`; the controller defensively retains it in each snapshot.
Render that context beside playback controls. `coverage:null` is explicitly
unqualified context, not evidence of complete or current coverage. State the
curated selection rule, measured axes/units, observed participants, omitted roles
and phases. Do not invent absent participants, height, objects, timestamps or
trajectories to fill an immersive scene. The controller validates declared shape;
it cannot establish whether the coverage statement is true.

`createRecordedPlayback({frames,clock,onFrame,reducedMotion=false,coverage=null})` takes:

```js
{
  frames: [
    {id:"frame-a", atMs:0, segment:"recording-1", observations:[{id:"sensor-1", value:3}]},
    {id:"frame-b", atMs:250, segment:"recording-1", observations:[]},
    {id:"frame-c", atMs:1000, segment:"recording-2", observations:[{id:"sensor-1", value:5}]}
  ],
  clock: {
    now: () => performance.now(),
    request: callback => requestAnimationFrame(callback),
    cancel: handle => cancelAnimationFrame(handle)
  },
  onFrame: state => renderRecordedState(state)
}
```

Frame IDs are unique; `atMs` is nonnegative, finite and strictly increasing. Each explicit segment is contiguous. These are elapsed recording milliseconds, not inferred wall-clock dates. Each frame contains unique observation IDs; absence means no supplied observation, not zero or disappearance in the real world. Limits are 10,000 frames, 1,000 observations per frame and 100,000 total observations; they are safety bounds, not measured rendering capacity.

Methods: `play({speed=1})`, `pause()`, `seek(index)`, `setReducedMotion(boolean)`, `series(entityId,throughIndex?)`, `snapshot()` and `dispose()`. Speed is 0.25–4. Playback emits supplied frames only, may skip intermediate frames when the injected clock advances, and never interpolates values. It stops with `phase:"gap"` at a segment boundary; `nextSegmentIndex` allows an explicit manual seek. Resume starts at the last selected recorded timestamp. Reaching the end does not loop or reset automatically. The caller labels the exact frame time and must not imply the last observation describes the interval after it.

`series` returns separate observed runs, splitting on segment boundaries **and** missing observations. A renderer must not connect those runs as if continuous or derive an unrecorded trajectory. The other local phases are idle, playing, paused, ended, error and disposed; they are not vendor events. Reduced motion cancels playback immediately; manual seek stays available. A new play/seek/pause or disposal invalidates queued callbacks. The clock must be monotonic. The host owns hidden-page policy, event cleanup and any camera; use the existing projection/camera utility rather than adding unrelated scene assumptions.

For playback in a detail view, hiding that view is a lifecycle transition even when its DOM and controller remain mounted. When controls become unavailable through index mode, a tab or another selected layout, pause playback and retain its frame and camera; returning must not resume automatically. Dispose only when the view is actually retired. If background continuation is intentionally required, resolve its visible controls and status explicitly in the selected design. Rehearse the actual hide/return actions with a controlled clock, rather than checking destination unmount alone.

Retain camera choices using the existing `createEntityChoices`, keyed separately
for the working view and each inspected entity. Its injected validator owns finite
values, bounds and supported camera fields. Save before renderer disposal and
restore before drawing; ordinary query refresh, selection or resize is not a reset.
Named views/reset controls deliberately replace the saved choice. Do not create
another camera store, persist values externally by default or encode a universal
camera/projection into the core. Test save/dispose/restore and explicit reset as
one interaction, retaining native rendering as a separate observation.

For any numeric geometry, derive one shared signed domain from qualified finite
values, including zero:
`minimum=min(0,values)` and `maximum=max(0,values)`. Anchor bars at that zero and
extend negative values in the opposite direction; absolute magnitude with a minus
label is not a signed encoding. NULL has no bar. Handle an all-zero domain without
division by zero and no valid values as unavailable. For a nonempty slice with no
eligible coordinates, choose a useful non-spatial comparison from qualified
fields and label the unlocated population; suppress empty camera controls and
retain exact records. A large decorative field is not evidence. If no alternative
measure is qualified, show an explicit unavailable state. These are encoding and
review rules, not a prescribed layout or automatic metric calculation.

## Time and event navigation

`normalizeEvents(events,timeZone)` retains each original record and adds `dayKey`, `instantMs` and `timeKind`. Each event has a unique ID and one explicit `time`:

- `{kind:"date",value:"2028-04-02"}`: calendar date, unaffected by timezone conversion.
- `{kind:"instant",value:"2028-04-02T00:30:00Z"}`: timestamp with seconds and an explicit `Z` or `±HH:MM` offset; fractional seconds up to three digits. Placement uses the selected IANA timezone. Offset-free local timestamps and invalid rollover dates are rejected, not guessed.
- `{kind:"unknown",reason:"Date not supplied"}`: undated, retained outside the grid. No fabricated placeholder date.

The bounded calendar supports years 1900–2200, offsets through ±14:00 and at most 10,000 events. It does not resolve recurrence, duration, all-day spans, locale parsing, ambiguous local times or provider status semantics. The source adapter must classify postponed/uncertain events as unknown when appropriate; ordinary event labels cannot decide that.

`createTimeNavigation({events,timeZone,month:"YYYY-MM",weekStartsOn:0..6,onChange})` provides `setMonth`, `shift(delta)`, `setTimeZone`, `replaceEvents`, `snapshot` and `dispose`. Week start defaults to Monday; choose it explicitly for the task. Snapshots contain month cells with exact event IDs, all normalized events, and `undatedIds`. Blank dates mean no supplied event, not complete absence. Invalid replacements leave the prior state intact. Event selection/return uses the selection controller; no automatic next-event/default selection is imposed. Agenda and calendar renderers can consume the same normalized records.

## Two original presentations, shared behavior

[`behavior-studio.html`](../assets/behavior-studio.html) loads the two helper scripts and [`behavior-studio.js`](../assets/behavior-studio.js). Keep these relative paths when copying the example, or use the reviewed build's explicit dependency order. It uses invented archive records, dates and numeric observation fixtures—no customer material, images, remote media or native bridge.

One selection controller drives a **table with adjacent detail** and a **sequential reading path**. The renderer adapters choose distinct DOM structures/styles and inject restoration targets. A per-record Summary/Provenance choice survives switching presentations; partial, excluded and denied states have different explanations. The date view contrasts a literal date with an instant that crosses a local day boundary. The recording demonstrates missing observations, a segment gap, reduced motion and cleanup. The studio's explicit UI choices are examples, not defaults in the core.

Use existing `createResource`/`createMediaState` from [native capability checks](native-capability-checks.md) for freshness and media. Do not duplicate them here or reinterpret frame-load success as readiness. A provider fallback remains a selected product decision.

## Focused verification

`python -m unittest discover -s tests -p test_experience_behaviors.py -v` exercises exact selection availability, stale generations/restoration, isolated choices, recording gaps/cancellation, date precision/timezone handling and the actual studio scripts through a minimal DOM double. It checks that both renderer structures use the shared behavior; it does not render layouts, evaluate aesthetics, reproduce browser focus/scroll behavior, measure performance or establish native/provider/accessibility acceptance. Observe the selected candidate's affected native/rendered paths when authorized; under source-only constraints retain those limits.
