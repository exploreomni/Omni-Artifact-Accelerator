# Visible design, resolved handoff and craft review

Use for substantial new experiences, material redesigns, or a stated visual-quality problem. This is the package's design method, not a vendor standard, native capability claim or another permission gate. Continue authorized sketches and prototypes. For a small correction, inspect the affected component/states; for faithful migration, retain source behavior and review supported adaptations without requiring divergent redesign.

## Establish the visual question

Reuse audience, task, brand website/authority, metrics and target decisions. Capture the reference qualities to borrow **and avoid**, density, principal content, supporting actions, selected appearances and representative widths. “Premium” or a famous brand name alone is not a design specification. Translate it into observable choices: a clear focal result, readable exact values, consistent action hierarchy, purposeful space and a task-specific next step. Marketing-site imagery is not a requirement for an analyst workspace.

For a new uncertain composition, render a small number of meaningfully different directions, normally two. Change information grouping or interaction, not just color. Compare them with the same representative scope, data, long labels and important state; retain the reasoned selection and rejected tradeoffs. Use static screens for visual questions and a clickable path for interaction uncertainty. Clearly label mockups, fixture data and missing native bindings. A prose concept or list of CSS tokens does not replace a visual artifact.

## Resolve the implementation handoff

Use the [current design-intent selection](../../omni-artifact-accelerator/references/design-intent.md) to bind this handoff to its brand, declared assets and surface candidate. The representative screen should contain the selected logo when required, realistic values, typography/fallback, density, primary action and consequential state together. Reuse an existing concept; a focused correction needs only its affected component. An agent's working choice is not customer acceptance.

Provide enough specificity to remove material aesthetic guesswork:

- Screens at the agreed wide and narrow sizes, with a page overview and readable detail; record the actual viewport and appearance.
- Content hierarchy, grid/containment, type roles, spacing, number treatment, chart anatomy and contextual control placement. Use resolved values in the candidate; retain justified responsive rules rather than vague ranges.
- Realistic labels/values and relevant empty/error/loading, selected/focus and partial states. Never manufacture a positive business result to make the composition compelling.
- The selected task sequence, useful information added by detail, query scope and state dependencies, return/focus behavior and reduced-motion equivalent.
- Native mapping and gaps. Confirm supported dashboard layout, theme, label/axis and interaction settings before freezing their use. HTML comps illustrate intent; they do not authorize native DOM/CSS injection or a surface substitution. A supported adaptation may change styling while preserving the intended hierarchy and task.

Use the existing engagement schema. These are minimum evidence concepts, not a second lifecycle or an import format:

```yaml
concept: {id: concept-a, surface: app, render_refs: [], context_ref: null}
selection: {concept_id: concept-a, rationale: null, authority: working_decision}
resolved: {screen_refs: [], tokens_ref: null, chart_specs_ref: null, state_bindings_ref: null}
deviation: {intended: null, actual: null, reason: null, candidate_pin: null, designer_disposition: unresolved}
craft_case: {candidate_pin: null, viewport: null, appearance: null, state: null,
             capture_ref: null, expected: null, observed: null, finding: null,
             status: not_run, reviewer: null, correction_ref: null, retest_ref: null}
```

## Designer return loop

Engineering returns actual native captures, exact candidate/version pins and material implementation deviations. The designer compares against the original named requirements and selected design, inspects the changed composition and records a disposition. Requirement-specific observations must identify the current asset/candidate, affected surface and state; a broad craft finding cannot stand in for an omitted logo, type treatment or primary task check. Independent QA evaluates applicable visual/behavior expectations; the implementer's own check is not independent review. Fix material findings and review the changed version. An earlier prototype capture cannot close the native lane.

| Craft question | Concrete evidence or correction |
| --- | --- |
| What matters first? | Opening content view exposes task, scope, focal result and next useful action. Rebalance competing cards or oversized identity areas; do not impose a universal header height. |
| Does grouping explain relationships? | Align related labels/values and give comparison enough width. Inspect the whole composition and individual panels; equal card geometry is a choice, not a default. |
| Is type doing useful work? | Deliberate title/body/label/value roles; readable chart labels, consistent units and numerals, long-label/fallback specimens. Fix optical alignment and ambiguous date ticks. |
| Does detail earn the interaction? | Detail adds evidence or a useful operation. Remove redundant disclosure or bind a justified additional query; do not invent analysis to fill it. |
| Does the brand shape the experience? | Show how typography, spacing, asset role and action vocabulary express the chosen direction while preserving data meaning. Color matching alone is insufficient. |
| Does the small layout preserve the task? | Actual narrow/zoom render plus keyboard route: selected identity, scope, useful return, contained table overflow and meaningful focus survive. |
| Are states coherent? | Selected, pending, current, empty, stale and failed remain distinct; visual polish must not obscure result or access uncertainty. |

Retain concrete findings and severity rather than a numerical beauty score. A materially unreadable chart, broken core task, hidden required scope or unresolved composition deviation keeps the affected craft case open. Lesser findings need explicit disposition. Report `pass`, `fail`, `blocked`, `not_run` or justified `not_applicable` per case. Craft completion does not close numerical, native interaction, access, performance, human usability, business acceptance or publication lanes. Let the orchestrator reconcile the requested completion scope; retain an honest candidate with gaps when prerequisites are unavailable.

Changing tokens/layout reopens affected visual/responsive cases; changing queries, filters or content also reopens affected analytical/interaction cases. Bind returned findings and retests to the exact revised version. No additional user approval is implied for already authorized reversible correction.

## Reusable patterns and provenance

The [pattern cards](craft-patterns.md) include an original [synthetic rendered specimen](../assets/craft-specimen.html). They illustrate decisions, not a universal theme or a passing native test. Sources and prior check dates remain in [vendor guidance](vendor-guidance.md); refresh implementation-sensitive claims when applying them. Link current designer/native captures into the engagement, not customer data into the reusable package.
