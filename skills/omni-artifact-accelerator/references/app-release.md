# Candidate release for native Apps

This extends existing A–F records. It does not add a questionnaire, orchestrator,
required worker pool or preferred layout. New `init` engagements containing an App
carry `app_release_policy: candidate-release-v1`. Historical engagements without
it remain unassessed in these additional lanes. Explicit adoption preserves their
old evidence and reopens only affected D/E/candidate checks. Never delete policy
to make a failing candidate pass.

For explicit historical adoption, record a fresh `run-start` with
`adopt_app_release_policy: true`, preserving the startup chain. Adoption is retained
in startup and subsequent stage records. Old E checkpoints must be refreshed under
the policy before building; A–C evidence remains available. Removing an already
recorded policy is rejected instead of silently relabeling the run as historical.
Engagements predating the workflow quality policy also require explicit
`adopt_quality_policy: true` and its execution contract in that same request.
An App-only adoption request cannot report success without persisting that setup.

## Entry and discovery

Before dispatch, use the trusted current source's [host-entry preflight](engagement-entry.md#inspect-the-host-entry-first).
Compare the actual loaded path with the requested checkout, pinned revision,
verified current main or explicit offline snapshot. Keep the receipt in the same
engagement and reuse it across specialists. Updating or activating an installation
requires its existing authorization. A host with unrestricted credential-bearing
shell/CLI access remains advisory until that real boundary is independently tested.

At D, recover the sourced user task, first useful action and outcome, first-use
focus and returning-use needs through the existing experience promise. Ask only
for an answer that materially changes the design. Keep target surface, workflow
mode and visual treatment separate. Preserve qualified A–C analysis and Topic
bindings. Frequency of use does not imply a compact dashboard composition.

## Show the first action in all three concepts

For each App concept manifest, add `action_sequence` alongside its existing
`representative` and `primary_interaction`:

```json
{
  "kind": "transition",
  "first_view": "Scoped observations",
  "action": "Inspect an observation",
  "result_view": "Observation evidence",
  "useful_result": "Explain the selected observation while retaining the scope"
}
```

The action must equal `primary_interaction`. Both view labels must appear in the
representative's labels and, for an original SVG, its actual text. One storyboard
may contain both views. This checks source structure, not visual quality or working
interaction. Retain source-only specimens as unrendered. For a deliberate static
monitoring view, use `kind: single_view`, identical view labels and a concrete
`single_view_rationale`. Filtering and other promised transitions still need their
own canonical journeys. Multi-surface concepts retain separate surface evidence.

Use the existing independent comparison and actual E selection. A list item saying
questions were asked, an agent recommendation or silence cannot supply a choice.
For a user-selected combination, retain one selected base option and add
`selection_adjustments` to the selected design's `experience_handoff`:

```json
{
  "response_path": "evidence/actual-user-response.json",
  "elements": [{
    "option_id": "option-2",
    "source_locator": "Evidence inspection state",
    "application": "Use this inspection flow within the selected base direction",
    "journey_ids": ["inspect-observation"]
  }]
}
```

The response must be the exact conversation-choice evidence already in E. Every
element names one of those same three options and a canonical selected journey.
The PO checks that the actual reply supports each amendment. These declarations
cannot authenticate intent or justify a newly invented combination. A materially
different mode reopens the existing selection instead of silently rewriting it.

The bounded engineer packet reuses the chosen concept, current promise, canonical
journeys, required dependencies and amendments. Host HTML guidance must distinguish
local report previews from a native Omni App. Preserve applicable sandbox rules
and the selected target's actual query bridge. Do not copy a host's sample layout
or embedded snapshot pattern into the product by default.

Task-relevant hybrid elements are included in the bounded experience summary.
Unrelated elements retain exact design pins, row hashes and pointers with a required
read before changing their linked journeys. Unchosen concept documents are not
copied into every worker's context.

## Candidate, data and review

Freeze the HTML and [visible data consumer manifest](../../omni-app-engineer/references/native-data-input.md)
as candidate artifacts. The manifest covers every visible analytical value and
interaction, with exact governed query, field and callback bindings or clearly
labeled snapshot/scenario provenance. The static checker can find unmapped markers;
the designer and QA must still find unmarked claims. It cannot execute JavaScript
or prove that a callback drives the display. Independent expectations and native
observations retain their own evidence lanes.

Use the chosen freshness answer. Test later tabs as well as headline figures.
Completion labels follow the relevant query outcomes, never an elapsed timer.
Denied/error/empty and out-of-order results must not silently display embedded
rows as fresh live data. A disconnected preview retains an explicit unavailable
state or a separately labeled intentional public snapshot. No added polling,
custom expiry or cache bypass is implied by this policy.

Review the first meaningful journey before expanding secondary pages. Final
PO/UI/UX fit still covers every promised destination and journey. For observed
journeys, fit evidence adds `journey_observations` rows containing `journey_id`,
`method` (`interaction_exercised` or `static_capture`), `context`, `steps` and
`evidence_paths` referencing the existing observation pins. A transition needs an
exercised interaction; a screenshot establishes appearance only. Test the chosen
devices and wide/narrow states where applicable, including return and recovery.
Source-only review remains available with rendered and native quality unverified.

## Write and verify the exact product

Use [native authoring preparation](../../omni-app-engineer/references/authoring-preflight.md).
Draft preview, immediate-publication creation and whole-draft publication have
different requests and authorization scopes. Publication includes the complete
query collection, controls, settings, metadata and HTML. Freeze the full draft
snapshot with the HTML before the four reviews. A last-minute query or setting
change invalidates that publication candidate.

An operator may integrate the first-party `native_write_gate.execute` boundary
with an already approved in-process host driver. It reconstructs the fixed request,
obtains exact-action authorization from that driver, checks the inputs again,
persists attempt intent, and invokes transport once. It never reads credentials or
loads a driver from a file. The driver owns authentication, bounded transport,
redirect rejection and actual permission verification. This integration is not
automatically active in any external host. Unmediated writes remain advisory and
cannot claim managed-path qualification. Unknown responses require reconciliation.

Read back the authorized target using its matching verifier. Exact supplied
captures establish consistency, not a rendered, runtime, access or human pass.
Keep observation limits visible after publication. Creating a demo immediately
publishes too; its pending review exceptions remain explicit.

## Qualification and efficient rollout

Use neutral private briefs for classic monitoring dashboards, monitoring Apps,
investigation/decision Apps and ambiguous requests. Confirm the chosen surface and
task fit instead of requiring one visual signature. Exercise stale installation,
missing E choice, changed candidate/query, direct-write denial and stale response
cases. Package tests cover local guards; qualify each host's actual write boundary
separately. A managed helper passing does not establish shell-wide enforcement.

Compare first-candidate hierarchy, branding, interaction, responsive composition
and numerical correctness against the chosen concept. Retain actual observations
at that same revision. Compare clarifying turns, model calls, corrections and
context reads with the same baseline using the existing usage receipts. Do not
claim savings from byte counts. Reuse A–C and unaffected reviews; no blanket agent
calls, model downgrades or universal 3D requirements are introduced.

Keep private plans, raw chats, rehearsals, customer rows and captures outside the
repository. Hold release for silent surface substitution, false live-data status
or a bypass in a host claimed enforced. Preserve prior evidence on adoption and
rollback. Any change to Omni's own AI layout guidance is a separate product change
with its own review and rollout; this package does not alter platform routing.
