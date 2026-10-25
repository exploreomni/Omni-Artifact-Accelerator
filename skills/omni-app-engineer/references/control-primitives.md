# Optional native control bindings

Use these small primitives when the selected experience benefits from labeled search, native choices and explicit submitted scope. They supply behavior and a few opt-in control styles, not a framework, page shell, design system or required arrangement. Choose hierarchy, type roles, density and narrow layout from the selected design. For that judgment, read [control craft](../../omni-design-systems/references/control-craft.md).

`control_primitives.js` exposes `OAAControls` as a classic browser global, or the same CommonJS exports. It has no dependencies and performs no query execution, network, storage, SDK discovery or persistence. Copy [control-primitives.css](../assets/control-primitives.css) only if useful; all its rules are scoped to `.oaa-controls`. Define its color, radius and focus variables in the selected design and verify their contrast. The example tokens are not a customer theme.

## Search and clear

```js
const search = OAAControls.bindSearch({
  input: document.getElementById("search"),
  clearButton: document.getElementById("clear-search"),
  error: document.getElementById("search-error"), // optional visible error element
  maxLength: 80, // reviewed bound, not a default business rule
  onChange: (value, {reason}) => query.change("search", value)
});
// Explicit restoration does not simulate user input or execute a query.
search.set(savedValue); // {notify:false} by default
search.dispose();       // before retiring/replacing this view
```

Supply a visible `<label for>` and relevant `aria-describedby` hint/error IDs. The clear button needs its own accessible name. Search accepts exact single-line strings, preserving whitespace, case and Unicode; `maxLength` is 1–4096 UTF-16 code units, matching HTML maxlength. Control characters are rejected. There is no trim, tokenization, business matching rule or SQL interpolation. The input's native `maxlength` is also set. A rejected programmatic `set` throws without modifying the field; invalid user text remains visible with `aria-invalid`, native custom validity and the optional error message. It is not sent to `onChange`. Supply the error element when invalid input is possible so unchanged applied results cannot look like a successful new search.

The binding provides `set(value,{notify=false})`, `snapshot()` → `{value,composing,valid,message}`, and idempotent `dispose()`. Snapshot value is visible text, not proof that it was applied. `onChange(value,{reason})` uses `input`, `clear` or `set`; it fires for valid changed committed text only. Composition input is held until composition end, then the following duplicate input event is ignored. Clear commits one empty value and returns focus to the input. This requires an empty string to be permitted by the selected search contract. Silent `set` changes visible state without calling the application.

The binding owns input, composition and clear-click listeners; it does not stop propagation. Remove or skip an existing delegated handler for the same field so a committed change has one owner. Duplicate binding of the same input throws. Dispose before replacing view DOM. Query timing belongs to the caller: apply-on-submit, reviewed local filtering or bounded debounce are separate policies. Never debounce a composed intermediate string into a governed query.

## Native choices, actions and summaries

- `bindSelect({select,onChange})` requires a single native select with a current enabled option. `set(value,{notify=false})`, `snapshot()` and `dispose()` mirror the search lifecycle; the value must match an enabled current option. Use a real label and maintain the options from reviewed identities. Rebind if replacing the control itself.
- `bindRadios({fieldset,onChange})` requires one named group of native radio inputs, unique string values and exactly one enabled checked value. Supply a visible legend and labels. It provides the same methods, preserves native keyboard behavior, and does not replace radio inputs with clickable decorative boxes. Dispose/rebind if rebuilding group membership.
- `setButtonState(button,{busy=false,disabled=false,pressed})` reflects native `disabled = busy || disabled` and `aria-busy`; optional `pressed` is for a genuine toggle. It is stateless: supply the current baseline `disabled` condition on **every** update. Busy does not remember or later restore a previous permission/readiness state. Native disabled buttons suppress user activation, but this helper does not intercept programmatic calls or guarantee focused-button retention across browsers. The application owns duplicate-operation guards and meaningful focus recovery after success/error. Keep visible action and outcome wording. Use a separately reviewed `aria-disabled` strategy only with its own activation guard; this helper does not provide one.
- `setSummary(element,{shown,total=null,completeness,filters=[]})` writes text only. `completeness` is `complete`, `partial` or `unknown`, supplied from qualified evidence. `filters` contains display `{label,value}` strings for **applied** scope. Complete requires a known total; counts must be safe nonnegative integers with `total >= shown`. The summary labels supplied scope and never infers warehouse completeness from a successful request or local row count.

Native select/radios are sufficient for this module. A custom combobox is warranted only when the selected task needs capabilities they cannot provide; then adopt an existing audited implementation and verify its popup, keyboard, active-option, composition, focus and screen-reader behavior. These helpers do not implement or qualify a combobox.

CSS includes visible focus, native radio affordances, reduced-motion removal of its small color transitions and forced-color tokens. These are source affordances, not accessibility acceptance. Observe keyboard, zoom, contrast and focus in the actual selected browser/native candidate when that lane is available.

## Assembled control regressions

The opt-in stylesheet protects hidden elements only inside `.oaa-controls`. Custom
chapter selectors, badges, scope panels and chart chrome need the same contract in
their own application scope. Author rules such as `.scope { display:flex }` or
`.badge { display:inline-block }` can override the browser's ordinary `[hidden]`
styling even when JavaScript correctly sets `element.hidden = true`. Inspect the
final cascade, not only DOM state. For ordinary application-owned hidden elements,
an explicit scoped rule can preserve that contract:

```css
/* Use the actual application root; this is not a prescribed shell. */
.app-root [hidden]:not([hidden="until-found"]) { display: none !important; }
```

Use this only for elements whose visibility is owned by the App. `hidden="until-found"`
has different browser behavior and needs its own deliberate design. Do not hide
content merely to simulate access control. When retiring a focused panel, move
focus to the selected destination or its return control through the reviewed
interaction contract; CSS alone cannot provide meaningful focus recovery.

Choose a few consequential cases from the actual task and keep them in the existing
candidate-bound QA records:

| Case | Expected behavior and evidence |
| --- | --- |
| Custom scope and warning panels | Exercise visible → hidden → visible in the assembled App. Final computed display and actual layout agree with state; hidden controls are absent from keyboard traversal. A minimal DOM fixture proves the requested state only. |
| Destination-specific scope | A ride/detail selector, review-park selector or other domain control appears only where relevant. Its selected/applied scope matches the displayed headline, chart, evidence and return state. Do not expose unrelated controls on every chapter. |
| Complete, partial, failed and stale results | A complete result cannot simultaneously show a false cap/withheld warning. If the selected claim requires complete evidence, withhold it when incomplete; if a qualified partial claim is intentionally supported, label its exact population consistently. Retain genuine warnings, clear obsolete ones, and never relabel a capped population as complete. |
| Long identities and values | Use representative long labels, punctuation and large/signed values. Give flex/grid children a shrinkable width (`min-width:0` where needed); wrap intentionally or constrain a block with overflow/ellipsis. Inline text alone does not establish an ellipsis. Preserve full identity through accessible detail or another deliberate path; a hover-only title is insufficient on touch. |
| Constrained layout and return | At selected phone/short-laptop widths and heights, labels remain legible, controls do not collide with chart marks, and useful evidence remains reachable. Exercise selection, drill, return and focus with the actual rendered candidate. |

These are meaningful regression expectations, not a required layout or universal
case matrix. Source/CSS inspection and synthetic state tests catch specific defects;
they cannot close computed-layout, keyboard, screen-reader or visual-craft claims.
When rendering or native observation is unavailable or prohibited, retain those
cases as `not_run` and name the gap. Do not install a renderer or use a headless
workaround without the corresponding authorization.

## Query fields and result evidence

The existing [query controller](../scripts/query_controller.js) remains an **OAA abstraction**, not an Omni SDK. Its original enum/number contracts and `run`, `change`, `reset` methods remain supported. Legacy `onState` event shapes are preserved; opt into `includeInputState:true` for richer state, or call `snapshot()` yourself.

An optional local text definition is:

```js
{id:"search", mode:"governed_filter", type:"text", minLength:0, maxLength:80, default:""}
```

Bounds use the same UTF-16/control-character semantics as search. `minLength` defaults to zero; `maxLength` is required. No implicit normalization or value coercion occurs. Input validation is not SQL safety: map these IDs through a reviewed parameter/filter adapter, never concatenate text into SQL.

**Native support boundary:** the current bounded native initial-authoring `input_bindings` schema accepts enum/number, not text. This local controller extension does not change that schema, immutable runtime fragments or any vendor capability. A governed text input therefore needs separate evidence for a supported native adapter and exact callback correlation; otherwise report that native route unsupported. A search over an already supplied local sample is a separate local interaction, with that sample's completeness stated. Do not expand query schemas or manufacture SDK calls to make the demonstration deployable.

| Operation/state | Contract |
| --- | --- |
| `change(id,value)` | Validate atomically, edit draft, invalidate in-flight delivery and clear result; emit `stale`. It does not query. |
| `run()` | Submit a copy of the current draft; clear prior result; emit loading then ready/empty or error/restricted. |
| `reset()` | Existing behavior: restore reviewed defaults, emit reset, then submit them. Label this operation “Reset and apply” if that distinction matters. It is not a silent reset. |
| `retry()` | Resubmit last submitted `applied` fields. It does not replace newer draft edits. If the retry returns for an older scope, state remains `stale`, `dirty:true`, `resultMatchesDraft:false`; do not display those values as the new scope. Throws before any submission exists. |
| `restore(snapshot)` | Require matching queryKey, exact input IDs and valid draft/applied values. Validation is atomic. Invalidate any pending delivery and emit `restored`; no query and no result/scenario evidence is restored, even if included in the input snapshot. |
| `cancel()` | Invalidate late local delivery, clear result, emit `cancelled`, retain fields. This does **not** abort the actual native request. |
| `dispose()` | Invalidate delivery, clear results, stop callbacks; later mutations throw. Idempotent. Snapshot remains inspectable as disposed. |

Rich snapshots contain `state`, `queryKey`, local `generation`, `draft`, `applied`, `dirty`, `resultMatchesDraft`, `governed`, and `scenario`. `applied` means last **submitted** values, not successful result evidence; it is null before first submission. Dirty is true until draft matches a submitted scope, including before the first run. A restored applied value is historical field context only. Ready/empty with `resultMatchesDraft:true` establishes locally correlated current result; it still does not establish real native transport, permissions or completeness. Local scenarios remain separate from governed filters and require the existing reviewed derivation callback.

The controller ignores obsolete promise results after edits, a new submission, restore, cancel or disposal. The bridge must correlate its actual native callback to the request it resolves. An untagged late native callback cannot become trustworthy by assigning it to the latest local promise. This module neither supplies correlation missing from the host nor retries failures automatically. Use existing [resource](native-capability-checks.md) and [selection](experience-behaviors.md) controllers when freshness or partial-result identity is needed; do not duplicate them inside a control binding.

## Two original transfer examples

[control-studio.html](../assets/control-studio.html) and [control-studio.js](../assets/control-studio.js) use six invented archive records and an explicitly delayed local promise adapter. The **catalog workbench** has a horizontal filter band, sortable table and adjacent context rail; narrow mode focuses index or detail with explicit return. The **field guide** places a compact filter column beside a numbered reading index, then opens a full article. They differ in DOM structure, hierarchy, typography, spacing and navigation treatment—not only colors. Neither is a required shell, and the earlier behavior studio remains unchanged.

They share the query controller, current-result resource, original-ID selection/return controller and these native bindings. Search/clear, native selects, visible radios, applied filter summaries, local sort and retained return focus are real local paths. Explicit rehearsal actions exercise partial results, error/retry and field restoration. Saving fields is in memory only; reload clears them. No localStorage, network, assets, native API or fake production object is used. Initial loading is an explicit example policy, not a query-controller default. Resource age and the artificial delay are not performance evidence.

## Bounded checks

`python -m unittest discover -s tests -p test_control_primitives.py -v` runs text bounds and atomic restoration; out-of-order A/B, retry versus edited draft, cancel/reset/dispose; IME and clear deduplication; native choice and summary contracts; and the actual studio scripts in a minimal DOM with controlled timers. The studio check verifies both structures, sort, explicit selection/return, partial omission, restoration invalidating pending delivery, error/retry and cleanup. The existing `test_hex_app.InitialAppTests.test_controller_run_reset_errors_staleness_and_scenario` checks legacy controller event compatibility.

These tests do not render layouts, simulate real native callback transport, certify browser focus, screen readers, visual quality or performance. Retain those lanes as unobserved under CLI-only execution. Use candidate-bound independent review for the actual selected artifact.
