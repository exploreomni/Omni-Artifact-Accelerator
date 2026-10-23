# Controls that preserve the task

Use this reference when navigation, actions, choices, search or column behavior materially affect the selected task. Read only applicable sections. These are package recommendations derived from the [dated source guide](control-learning.md), not an Omni capability declaration, new schema or additional approval gate.

Keep detailed choices in the existing `contracts/design.json` or its selected version. Use an existing intent requirement's structured `value` for consequential behavior and optional `delivery` for ownership and declared dependencies. Do not duplicate an authoritative control ledger. Supporting files need explicit input/dependency pins; prose paths are not automatically pinned. Reuse [current intent and review obligations](../../omni-artifact-accelerator/references/design-intent.md).

## Choose the behavior before its appearance

| User's purpose | Candidate control | Decision that changes the choice |
| --- | --- | --- |
| Go to another destination/resource | Meaningful link or supported navigation control | Preserve destination, current-location indication and return context. A button-shaped link is still navigation. |
| Switch panels within one task | Tabs when separate panels help | Do not hide evidence needed for simultaneous comparison. In-page tabs need keyboard/selection semantics; visual styling alone does not justify them. |
| Execute an operation | Button with an action label | Distinguish primary, secondary and destructive consequences. Do not promote every action to primary or use color alone to signal consequence. |
| Change one binary setting | Checkbox or appropriate switch | State immediate versus submitted application. Toggle buttons need exposed pressed state, not just different fill. |
| Choose among known values | Visible radios for useful comparison; native select when collapsed choice fits | Consider frequency, label length and discoverability, not a universal option-count threshold. Keep the label distinct from its value. |
| Find an item in a long option set | Searchable choice only when needed | Decide select-only versus free text, stable option IDs, commitment and dismissal. Custom comboboxes carry additional keyboard and assistive-technology work. |
| Find matching records | Labeled search field/form with defined scope | Distinguish local filtering from a governed remote query. Specify live versus submitted application, matching, clear and cancel. |
| Refine analytical scope | Simplest supported filter and active-scope summary | Name affected results, defaults and reset. Selection, display preferences and data filters are different operations. |

Make actions understandable in relevant states. A disabled action needs a reason and recovery path when its prerequisite is not obvious. Busy feedback must not imply completion, allow duplicate operations or unexpectedly resize the control. Placeholder text is not the sole label; essential instructions must not be hover-only.

## Specify the selected control in the existing design

Capture applicable decisions in the selected design's control/state entry. This is a handoff checklist, not a required object shape or import format:

| Decision | What the designer and engineer agree |
| --- | --- |
| Purpose and surface | Task, destination/region, accessible label, semantic role and rationale; native dashboard versus App. |
| Binding and scope | Stable source ID/value, affected results/query, local versus complete governed scope, sort/match rules and capability evidence. Display aliases never become keys. |
| Application | Draft/applied input, commit trigger, clear/cancel/reset meanings, validation and limits. Clearing one field need not reset other filters. |
| Continuity | Selected ID, saved input, per-entity choices if needed, return focus/scroll, restoration and supersession/cancellation. Distinguish memory-only state from separately verified durable storage. |
| Result states | Idle, loading, ready, empty, no matches, failed, stale, partial and denied as applicable; what stays visible, is withheld or can retry. Do not multiply irrelevant states across all controls. |
| Input behavior | Keyboard/pointer paths, focus entry/return, activation, dismissal and announcements. For custom choices, distinguish active option from committed value. |
| Presentation | Semantic tokens, density, long labels, usable width/height, intentional scroll, normal/reduced motion and hidden-region cleanup. |
| Evidence | Exact candidate/context, expected result, owner and applicable source/local/rendered/native/accessibility lanes in existing QA. |

The implementation counterpart is [control primitives](../../omni-app-engineer/references/control-primitives.md). Its optional native-control adapters and [original control studio](../../omni-app-engineer/assets/control-studio.html) need no framework or CDN by default. They are OAA code, not an Omni SDK or permission to add dependencies. An illustrative search field does not prove remote search support.

## Search, pending input and restored context

Keep **draft** text separate from the **applied** query that produced displayed results. If they differ, make that clear or withhold a current-results claim. **Restored** state must reconcile visible input, draft/applied state and selected source ID; restoring text alone can mislabel old results. Restoration must not silently submit, broaden scope or replay an operation. Specify any deliberate re-query policy and qualify runtime support.

Include navigation, re-render and browser-restored/autofilled values in the selected synchronization policy. Read the current control value rather than assuming its initial markup still represents the user's input. Preserve an intentional empty value; do not treat it as permission to substitute a default.

For live search, choose delay/minimum length around query cost and the task. Debouncing reduces calls; it does not establish correctness. Respect text composition before committing live input, validate bounded text without inventing matching semantics, and keep keyboard submission and explicit Apply consistent. A display label is not a selected record.

The host owns genuine request/result correlation. Existing [selection and pending-intent behavior](../../omni-app-engineer/references/experience-behaviors.md) can reject obsolete tickets only when the bridge associates results with the correct request. Never infer correlation from arrival order, label an uncorrelated callback as the latest request, or assume cancellation prevents an already-running response. An older response cannot overwrite newer applied scope. Retry must identify the failed scope rather than quietly submitting an unrelated restored draft.

Reconcile selections by stable source ID. Omission from partial, paginated, limited or unknown results does not establish exclusion: show unconfirmed membership, and use a supported membership query only when authorized and available. A complete filtered result can establish exclusion from that scope. Keep an explicit pending selection through loading/error/return until declared cancellation or a later explicit choice; first-use defaults must not replace it. Retain old values only under the selected, clearly labeled stale-data policy. Local subset matches cannot support whole-population totals or ranks.

Access changes are separate from filtering. Withhold restricted identifiers and values, including old detail, suggestions, counts and cached presentation; do not label denial as no matches. UI state is not authorization. Preserve useful safe input where appropriate, without retaining sensitive content after access is lost.

## Semantic tokens without a house style

| Token family | Preserve across treatments | Choose for the engagement |
| --- | --- | --- |
| Action and text | Primary/secondary intent, readable labels, consequence distinctions | Color, border, shape, weight, icons and emphasis |
| Focus and selection | Visible focus; distinguish focus, selected, pressed, hover and disabled where applicable | Ring/outline, selected surface and non-color marker |
| Surfaces and status | Readable pairs; pending/error/stale/partial are not business outcomes | Surface depth, borders, placement and emphasis |
| Geometry and density | Usable targets, spacing relationships, alignment and labels at supported text sizes | Comfortable/dense rhythm, radius and contextual control sizes |
| Motion | Correct values, focus, completion and interruption without animation | Optional timing/easing and transitions that support the task |

Name tokens by meaning rather than hue or page. Brand accent is not automatically success, error or selection. Map tokens to actual App CSS or supported native settings; unsupported dashboard settings remain gaps, not injected CSS. Apply the selected accessibility standard: WCAG 2.2 AA target-size minimum is 24 × 24 CSS pixels with defined exceptions; a larger product target is a separate choice. Source values alone do not establish conformance.

## Page columns and data columns are different decisions

**Page composition:** allocate width by task and content needs; fixed, fluid or hybrid arrangements can work. Adapt to containing pane and usable height after host chrome, not only viewport width. Decide when regions wrap, collapse, disclose or become a deliberate detail/index mode. Preserve meaningful reading/focus order, selection and return context. Allow wrapping; avoid shrinking all type to rescue layout. Container queries need a usable fallback and actual host verification.

**Data comparison:** retain comparison columns, headers, units and exact values. Do not automatically convert rows to cards or remove important columns. Choose a named horizontal scroll region, explicit disclosure or a different narrow view as justified. Define sort direction/ties, subset versus complete-result sorting, totals, NULL display and coverage. Sticky headers/columns need host support and must not obscure focus/content.

For popups, specify collision/overflow, dismissal and focus return within available space. Do not assume a portal, native overlay API or adequate height. Narrow detail needs a clear return to index; hiding it stops nonessential motion/work under the selected cleanup policy. Reopening preserves useful context without automatically resuming playback. Source/DOM order can be checked locally; clipping, real focus, touch targets and perceived hierarchy require the relevant rendered/input observation.

## Surface and migration boundary

For a **native dashboard**, use the BI engineer's verified control/theme/filter bindings. Specify propagation to affected tiles/queries, defaults, allowed values, reset, exact-value access and layout behavior. App JS helpers do not implement these features. Unsupported native features remain a gap with a supported proposal; switching to an App requires an explicit scope change.

For an **App**, use qualified [native input contracts](../../omni-app-engineer/references/native-data-input.md); keep query execution, normalization and access separate from presentation. For **migration**, preserve source control/action IDs, scope, apply/reset behavior, sort, selection and accepted differences through existing [migration coverage](../../omni-qa-analyst/references/migration-behavior.md). A more attractive control cannot silently change meaning or narrow the retained coverage denominator.

## Focused critique and verification

Use existing [design QA](design-qa.md) and exact-candidate review records. Select consequential journeys: enter/change/apply/clear; late response after newer scope; partial omission versus exclusion; failure/retry; saved input and detail/index return; or keyboard commitment/dismissal. Freeze expected IDs and results independently of implementation. Check applicable states and affected regressions rather than every lane for every control.

Local controller/DOM checks establish bounded state and wiring. They do not establish rendered composition, real browser focus, assistive-technology compatibility, native callbacks, effective permissions or human usability. Keep those lanes explicit. Compare two original visual treatments only when that resolves a real uncertainty; shared behavior should survive different structures without requiring either as the default shell.
