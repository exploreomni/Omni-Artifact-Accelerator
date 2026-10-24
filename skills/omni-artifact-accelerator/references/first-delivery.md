# First-delivery workflow

Use for a substantial new App or dashboard, or a material redesign. Reuse the selected brief and existing answers; a focused edit needs only affected checks, and a faithful migration retains its source behavior. The target is one customer brief followed by internal design, implementation, critique and repair. It is not a promise of one-generation quality.

## Recover, resolve, qualify

Use the [product-owner intake and North Star](product-intent.md) for substantial
product decisions. It reuses prior answers, preserves attributable private notes
and returns prioritized intent to the orchestrator. The North Star is a checked
projection of selected intent, not a second authoritative brief. Focused fixes keep
their current context; routine design choices need no additional user approval.

1. Identify the actual source mode with the [execution entry procedure](execution-workflow.md). For installed-skill work, use the read-only installer comparison described in the [how-to](../../../docs/HOW_TO.md#installation-and-updates). For an explicitly repository-only trial, record the working-tree manifest and do not consult installed copies, prior outputs or memory. For a connected repository link, establish what files were actually read; a URL is not activation. Source/install parity does not prove the host reloaded a cached skill.
2. Read current intent, original request, source/query scope and tooling restrictions. Reuse the company website, approved asset sources, audience and experience decisions. Batch only material missing questions; do not repeatedly ask about authorized logo sourcing or require the user to choose routine CSS.
3. Translate reference qualities into concrete choices: focal point, hierarchy, imagery role, density, primary action, useful depth, interaction and first/repeat use. Compare the same task through alternative treatments when useful. In design-review selections, record `exploration: {mode: "direct"|"compare", rationale: "..."}` per surface; a direct choice needs no manufactured alternative and still needs actual candidate critique. An agent can recommend a direction; record that recommendation as a proposal rather than inventing user approval.
4. Map the [analytical questions and evidence](../../omni-data-analyst/references/analytical-coverage.md). Before final destination scope, inventory usable sources beyond the first query: questions, populations/eras, grain, available and selected depth, unsupported/deferred possibilities and rationale. Use the [source inventory](execution-workflow.md#qualify-and-build-one-journey) to preserve the experience ambition and record why scope expands or remains bounded. Qualify the selected native callback and high-risk asset/media/live-refresh paths before the design depends on them. Follow [native capability checks](../../omni-app-engineer/references/native-capability-checks.md); unavailable observation remains explicit.
5. Declare the selected destinations and applicable contexts/lanes before generating review cases. Keep a full inventory even for a focused edit. Choose only combinations needed to assess the actual task; missing applicability remains a gap.
6. Assemble one ambitious representative task slice, carrying the defining experience qualities as well as relevant default/empty/error states and constrained-layout behavior. If the task includes detail and return, exercise that path; a static dashboard needs no invented App journey. A reduced technical demo cannot qualify omitted experience requirements. Review and repair the slice before expanding other destinations.

An immersive opening, photos, extra destinations and 3D are conditional design choices. Every added region must help the selected task. Richness comes from useful evidence and interaction, not a prescribed number of panels.

Conditional does not mean disposable after selection. When technology is unavailable,
retain the original outcome and evaluate supported treatments that preserve its
ambition. Record the alternative and remaining difference in current intent. A
no-render restriction limits evidence; it is not a reason to lower the design bar.

For each consequential destination, have the experience owner resolve the [destination specimen and state ownership](../../omni-design-systems/references/experience-brief.md#implement-the-selected-experience) before treating implementation as complete. Critique the main evidence's prominence, useful first state, role-appropriate depth and constrained-space journey separately from numerical correctness. A no-rendering restriction leaves visual quality unobserved, but does not prevent an independent source review from finding a buried scene, missing comparison, generic role fallback or lost exceptional selection. Repair those concrete omissions without inventing a visual pass.

## Component quality within the first journey

When controls are new or materially changed, have design systems resolve the relevant [control families](../../omni-design-systems/references/control-craft.md) before the first slice: task-fit choice, emphasis/anatomy, states, density and responsive rules. Carry the shared definition once in the selected design and reference it from affected destinations. Use [optional control primitives](../../omni-app-engineer/references/control-primitives.md) only when they fit the selected implementation. They do not choose the shell, navigation, palette or query semantics.

Review search → refine → inspect → return only when that task exists. Include reset/recovery and preserved identity, distinguish local filtering of supplied rows from a governed warehouse search, and inspect the input and result state together. Remote free text needs a supported reviewed bridge and bounded domain; a DOM input or local controller does not establish native support. Course references are optional learning aids, not an extra discovery or approval step. A focused correction reuses the existing design and reviews only affected obligations while retaining the full inventory.

## Declare ownership and observable behavior

The existing intent specification accepts optional requirements[].delivery. Use it for material requirements in this workflow, not as another global questionnaire. The helper validates field types and references; missing content remains representable during provisional work.

| Field | Meaning |
| --- | --- |
| source_ref | Actual request/decision reference; identify agent proposals honestly. |
| owner | One existing role name, such as app-designer or data-analyst; null while unresolved. |
| behavior | Observable result. “Calendar” is insufficient: describe month navigation, actual date placement and selected-day detail. |
| destinations | Stable IDs in each affected surface's selected resolved design. One screen is valid. |
| journeys | Optional stable IDs in each affected surface's selected design, for actual state transitions or paths the requirement needs. No journey is needed for a static task. |
| dependency_paths | Explicit canonical engagement-relative files needed to implement/review this requirement. Automatically pinned with the selected intent and included in relevant packets. |
| capabilities | Applicable tags: insight, custom-visualization, spatial-modeling, motion, external-media, live-content, data-binding, brand-assets. |

Example fragment inside an existing requirement, using original synthetic context:

~~~json
{
  "delivery": {
    "source_ref": "inputs/brief.txt: collection investigation request",
    "owner": "app-designer",
    "behavior": "Select a collection, inspect its exact demand records, and return with that selection retained.",
    "destinations": ["investigation"],
    "dependency_paths": ["contracts/input-shape.json", "contracts/runtime.json"],
    "capabilities": ["insight"]
  }
}
~~~

Keep required/optional, origin, disposition, value, decision_ref and contexts in the existing requirement. This annotation does not replace them or grant authority. Selected intent freezes explicit dependency bytes; revise and reselect after a material input changes. Arbitrary descriptive links nested in value remain uncrawled. Keep packets within their existing 256 KiB bounds; do not silently drop large dependencies.

Use `delivery-project` to avoid rebuilding a second requirement list. It copies the
current selected specification into a **new, unselected proposal**, retains all
requirements and dispositions, and carries existing delivery annotations. It can
derive `source_ref` from the exact decision reference and destination/journey IDs
from explicit context applicability. It does not guess aliases from free prose,
turn suggested roles into owners, infer runtime dependencies or treat acceptance
goals as implemented behavior. Supply only the remaining explicit annotations:

```json
{
  "output":"contracts/intent-with-delivery-v2.json",
  "annotations":{
    "investigate":{"owner":"app-designer","behavior_from_value":true}
  }
}
```

Run `python3 -I -S -B "$OAA_HELPER" delivery-project --project "$OAA_RUN" --request projection.json`.
`behavior_from_value: true` explicitly copies a textual requirement value; use it
only when that value already states the observable behavior. Otherwise supply an
explicit `behavior` string. All ordinary delivery fields can be supplied per
existing requirement ID. Missing owners, behavior or applicability stay missing
and appear in the returned coverage report. The helper returns field provenance,
source intent and proposal hash; it does not select, dispatch, approve or rewrite
the readable North Star. Reconcile against current intent, select a new version
with the existing `intent-select`, then regenerate the North Star. Regenerate a
proposal if its source selection changes.

In each selected design JSON, use a destinations list with stable id and meaningful purpose, primary_action, evidence, drill, return and responsive fields. Values can be strings or structured objects/lists. A purposeful absence can be explicit, for example “No drill: this monitoring task is complete in the current view.” Record richer state, imagery, camera, motion and focus decisions in that same resolved design, not a parallel specification.

Author those keys once in the canonical selected design. Descriptive alternatives
such as `analytical_depth` are useful additional detail but are not automatically
equivalent to an evidence/drill/return contract. Reconcile the selected design
directly rather than maintaining another manually synchronized resolved copy.

~~~json
{
  "brand_contract": "contracts/brand-v1.json",
  "destinations": [{
    "id": "investigation",
    "purpose": "Explain changes in collection demand",
    "primary_action": "Select a collection",
    "evidence": "Trend, contribution and exact records with source period",
    "drill": "Open its dossier and selected-period detail",
    "return": "Retain collection, period, focus and scroll position",
    "responsive": {
      "first_view": "Selected subject and main action remain readable",
      "narrow": "List/detail stages; exact evidence remains reachable",
      "height": "Intentional scrolling; do not shrink labels to fit everything"
    }
  }]
}
~~~

Resolved designs and references are candidate decisions, not production acceptance.

## Check and route

Run from the installed helper or source checkout using the same Python environment as setup:

~~~sh
python "$OAA_HELPER" experience-check --project "$OAA_RUN"
python "$OAA_HELPER" plan --project "$OAA_RUN"
~~~

experience-check reports:
- not_assessed: no active delivery annotations; existing legacy records remain valid.
- incomplete: missing declaration, destination detail, selection or explicit dependency.
- inconsistent: stale/invalid selected context.
- ready_for_review: declared structural coverage is present. It never means the app is polished, numerically correct, native-verified or approved.

The command exits 1 for incomplete/not_assessed/inconsistent, 2 for malformed invocation/input, and 0 for ready_for_review. It cannot discover requirements omitted from both the brief translation and the records. The experience lead must compare the original request with the candidate.

plan adds owners and specialists from applicable capabilities, with requirement IDs. Deferred/explicitly omitted requirements do not activate implementation specialists. App-only capabilities on dashboard-only requirements remain findings; they do not silently change the target surface. Custom visualization loads the App engineer's [advanced module](../../omni-app-engineer/references/advanced-visualization.md), not a new permanent role.

For selected reusable App interactions, engineering can load [behavior controllers](../../omni-app-engineer/references/experience-behaviors.md) and [local assembly](../../omni-app-engineer/references/portable-assembly.md). They share state/lifecycle and build mechanics; the selected design still owns composition, visual identity and domain meaning. A valid result may use none of these capabilities.

Role suggestions are responsibilities, not a mandate to spawn one worker per role. For substantial Apps, a lead/integrator, an experience owner and independent verification are often sufficient. Add a bounded data or visualization worker when complexity or independence warrants it. Preserve the host's configured model and effort.

The execution record supports optional `specialists` with existing role names,
actual workers and requirement IDs; use that slot for conditional modeling or
motion work without inventing a new mandatory core responsibility.

For actual parallel work use [scoped assignments](task-routing.md). Include current input bindings, exact owned output files, dependency readiness, public methods/events, style/state ownership, acceptance conditions and cleanup. Map assignment scope_ids to applicable requirement IDs. Reserve and record actual dispatch separately. Integrate the first working slice early; a packet is not evidence that a worker ran.

## Review the assembled experience

Generate the required observation set from the current design and intent before collecting evidence. Do not build the denominator from submitted cases or screenshots. Account for every selected destination/context and selected lane, using a justified applicability exclusion only where valid; craft cannot be excluded. A focused review names its affected obligations and reports scoped coverage, not a whole-experience pass.

Return the exact candidate, original brief, selected direction and generated obligations to the designer and an independent verifier. Reuse [experience critique](../../omni-design-systems/references/experience-review.md) and [design evidence](../../omni-qa-analyst/references/design-evidence.md). Inspect all consequential destinations and a complete task slice, including detail/return only when selected.

Keep three questions distinct: the PO recommends whether the product promise is
preserved; a creative reviewer different from the builder and originating designer
critiques its realization; QA verifies correctness. One suitable independent worker
may perform both review disciplines with separate findings. No result grants
runtime/publication authority or substitutes for unobserved customer acceptance.

For final bookkeeping, use the [delivery evidence template](execution-workflow.md#assess-delivery-without-upgrading-claims)
on the frozen exact candidate. Source critique and requirement-by-context rendered
assessment remain separate results. A source review can resolve concrete code
findings while the formal design record stays `not_assessed`; retain that accurate
result rather than presenting source inspection as observation of a screen.

Give each material request a disposition: implemented and observed in a named evidence lane, implemented but unobserved, blocked with a useful fallback, deferred, or explicitly omitted. A working external link does not fulfill inline playback. An agenda does not fulfill a month calendar. A decorative perspective does not establish camera interaction or measured height.

Tie native/media observations to the candidate, target, relevant settings, date and actual result. Keep separate numerical, local, native, rendered and human evidence. Source-only or simulated review can find defects but cannot establish visual polish. Respect CLI/MCP-only restrictions; do not route around them.

When observation is permitted, use representative phone/laptop/wide sizes selected for the task. Review available content height, meaningful defaults, readable labels, no accidental overflow, stable identity/filter state, focus/scroll return and reversible motion. Fix concrete issues, then recheck affected paths. Discover the supported preview/draft route instead of assuming it exists. Do not silently reset existing repair limits when an unavailable capability keeps failing.

Give each internal finding the affected obligation, observation, effect on the task, specific repair and evidence needed. Correct it within existing authority and repair limits. A passing retest must cover the same destination/context or journey and exact current candidate; an unrelated screen pass cannot close it. Do not refresh pins to reuse an old observation after the candidate changes.

Before first delivery, the lead checks whether every consequential destination fulfills its purpose and chosen direction; whether detail supplies supported information and return preserves the investigation; whether required brand and responsive treatments were actually observed; and whether every material finding has a matching retest or a clearly stated remaining gap. Compare every requirement with the assembled result and list remaining differences. Preserve existing publication authority and readback requirements. Keep the usable entry link and current context in START_HERE.md.

## Transfer and qualification

A useful rehearsal gives a fresh worker the installed skills, a raw brief and minimal source artifacts from an unfamiliar domain, without the desired solution. Inspect its actual decisions, handoffs and candidate. Use a small contrasting set: non-spatial App, partial-data/blocked-capability case, and source-faithful or CLI-only migration. Store results outside the package.

Retain the initial generated candidate and the internally reviewed first delivery, each with exact hashes. Keep a compact engagement run log linked to review evidence: initial brief/message reference, material clarification batches and their reasons, repeated questions, customer corrective prompts for dropped requirements, new preferences/scope, internal findings, revisions and remaining blockers. Internal revisions are part of the work, not extra customer prompts. Never invent customer feedback or count an agent evaluator as a human participant.

For a bounded qualification trial, aim for zero repeated questions, zero customer corrections for already-supplied requirements, and at most one consolidated material clarification batch. These are trial targets, not a service guarantee; never suppress a necessary question to improve a count. Routine spacing, chart finish and implementation choices stay with the specialists.

Use three original contrasting briefs when qualifying a material revision: a branded exploration App, a native operational dashboard, and a constrained migration/investigation. Supply typed data and independently derived expectations; do not supply an expected layout. Run sequentially, retaining one unseen holdout until the package is stable. Discover permitted rendering/native observation before building around it. If unavailable, complete independent engineering/specification work and report qualification as pending. Keep inputs, generated artifacts and run evidence outside the repository. Do not invent a quality score or claim every host was exercised. Package checks and local rehearsals improve confidence; observed native execution and user acceptance remain distinct.

Include a demanding experience brief and a deliberately short ambiguous brief when
evaluating product-intent transfer. Withhold historical code/layout, not the user's
actual quality requirements. Check appropriate clarification, reuse of answers,
North Star freshness, unsupported-method alternatives and independent creative
findings. An unattended run with no customer correction cannot establish that no
correction was needed; record feedback as unobserved. See [qualification cases](../../../docs/TESTING.md#product-intent-and-premium-experience-transfer).
