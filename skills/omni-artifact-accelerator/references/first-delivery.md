# First-delivery workflow

Use for a substantial new App or material redesign. Reuse the selected brief and existing answers; a focused edit needs only affected checks, and a faithful migration retains its source behavior. The target is one customer brief followed by internal design, implementation, critique and repair. It is not a promise of one-generation quality.

## Recover, resolve, qualify

1. Identify the installed package used by the host. From the source checkout, run the read-only installer comparison described in the [how-to](../../../docs/HOW_TO.md#installation-and-updates). Retain its version and manifest identity with engagement evidence. Source/install parity does not prove the host reloaded a cached skill.
2. Read current intent, original request, source/query scope and tooling restrictions. Reuse the company website, approved asset sources, audience and experience decisions. Batch only material missing questions; do not repeatedly ask about authorized logo sourcing or require the user to choose routine CSS.
3. Translate reference qualities into concrete choices: focal point, hierarchy, imagery role, density, primary action, useful depth, interaction and first/repeat use. Compare the same task through alternative treatments when useful. An agent can recommend a direction; record that recommendation as a proposal rather than inventing user approval.
4. Map the [analytical questions and evidence](../../omni-data-analyst/references/analytical-coverage.md). Qualify the selected native callback and high-risk asset/media/live-refresh paths before the design depends on them. Follow [native capability checks](../../omni-app-engineer/references/native-capability-checks.md); unavailable observation remains explicit.
5. Assemble one opening → task → detail → return slice, with default/empty/error states and constrained-layout behavior. Review and repair it before expanding other destinations.

An immersive opening, photos, extra destinations and 3D are conditional design choices. Every added region must help the selected task. Richness comes from useful evidence and interaction, not a prescribed number of panels.

## Declare ownership and observable behavior

The existing intent specification accepts optional requirements[].delivery. Use it for material requirements in this workflow, not as another global questionnaire. The helper validates field types and references; missing content remains representable during provisional work.

| Field | Meaning |
| --- | --- |
| source_ref | Actual request/decision reference; identify agent proposals honestly. |
| owner | One existing role name, such as app-designer or data-analyst; null while unresolved. |
| behavior | Observable result. “Calendar” is insufficient: describe month navigation, actual date placement and selected-day detail. |
| destinations | Stable IDs in each affected surface's selected resolved design. One screen is valid. |
| dependency_paths | Explicit canonical engagement-relative files needed to implement/review this requirement. Automatically pinned with the selected intent and included in relevant packets. |
| capabilities | Applicable tags: insight, custom-visualization, motion, external-media, live-content, data-binding, brand-assets. |

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

In each selected design JSON, use a destinations list with stable id and meaningful purpose, primary_action, evidence, drill, return and responsive fields. Values can be strings or structured objects/lists. A purposeful absence can be explicit, for example “No drill: this monitoring task is complete in the current view.” Record richer state, imagery, camera, motion and focus decisions in that same resolved design, not a parallel specification.

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

Role suggestions are responsibilities, not a mandate to spawn one worker per role. For substantial Apps, a lead/integrator, an experience owner and independent verification are often sufficient. Add a bounded data or visualization worker when complexity or independence warrants it. Preserve the host's configured model and effort.

For actual parallel work use [scoped assignments](task-routing.md). Include current input bindings, exact owned output files, dependency readiness, public methods/events, style/state ownership, acceptance conditions and cleanup. Map assignment scope_ids to applicable requirement IDs. Reserve and record actual dispatch separately. Integrate the first working slice early; a packet is not evidence that a worker ran.

## Review the assembled experience

Return the exact candidate to the designer and an independent verifier. Reuse [experience critique](../../omni-design-systems/references/experience-review.md) and [design evidence](../../omni-qa-analyst/references/design-evidence.md). Inspect all consequential destinations plus a complete detail/return path, not only the opening.

Give each material request a disposition: implemented and observed in a named evidence lane, implemented but unobserved, blocked with a useful fallback, deferred, or explicitly omitted. A working external link does not fulfill inline playback. An agenda does not fulfill a month calendar. A decorative perspective does not establish camera interaction or measured height.

Tie native/media observations to the candidate, target, relevant settings, date and actual result. Keep separate numerical, local, native, rendered and human evidence. Source-only or simulated review can find defects but cannot establish visual polish. Respect CLI/MCP-only restrictions; do not route around them.

When observation is permitted, use representative phone/laptop/wide sizes selected for the task. Review available content height, meaningful defaults, readable labels, no accidental overflow, stable identity/filter state, focus/scroll return and reversible motion. Fix concrete issues, then recheck affected paths. Discover the supported preview/draft route instead of assuming it exists. Do not silently reset existing repair limits when an unavailable capability keeps failing.

Before completion, compare every requirement with the assembled result and list remaining differences. Preserve existing publication authority and readback requirements. Keep the usable entry link and current context in START_HERE.md.

## Transfer and qualification

A useful rehearsal gives a fresh worker the installed skills, a raw brief and minimal source artifacts from an unfamiliar domain, without the desired solution. Inspect its actual decisions, handoffs and candidate. Use a small contrasting set: non-spatial App, partial-data/blocked-capability case, and source-faithful or CLI-only migration. Store results outside the package.

Track repeated questions, customer corrective prompts, internal revisions and unresolved blockers. Do not invent a quality score or claim every host was exercised. Package checks and local rehearsals improve confidence; observed native execution and user acceptance remain distinct.
