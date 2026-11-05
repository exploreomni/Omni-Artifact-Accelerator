# Experience continuity

Use this contract when an engagement adopts experience continuity. It adds an index
to existing design intent, not another requirements ledger, approval process or
layout template. Historical intent without the index remains `not_assessed`.
The orchestrator controls whether a new stage requires adoption; the index itself
grants no execution, native-write or publication authority.

## Preserve the promise before selecting a design

Keep these decisions separate:

- **Target surface:** the existing `spec.surfaces` selection.
- **Experience promise:** the task, useful action and outcome, first encounter and
  repeat use that the product must preserve.
- **Experience mode:** a proposed or sourced organization of the work, such as a
  workspace, narrative, monitoring view, guided workflow, branded entry, custom
  mode or hybrid.
- **Visualization treatment and quality:** the existing visual-family, treatment
  and quality requirements. A dimensional treatment is not a workflow mode.

Recover attributable answers before asking again. Discovery can be sufficient when
the task and promise are sourced, while creative modes remain hypotheses for the
existing concept comparison. Do not require a second mode-selection ceremony.
A deliberate dashboard or single-screen monitoring experience is valid. An app
does not become a workspace merely by adding tabs or an introduction.

Add `product.experience_intent` to the canonical specification:

```json
{
  "schema_version": 1,
  "requirement_ids": ["record-investigation"],
  "mode_requirement_ids": ["workspace-hypothesis"]
}
```

The optional `delegation_requirement_id` references an actual user or reused
decision whose value is `{"delegation_scope":"experience_direction"}`. This
permits working proposals within its recorded surfaces. Styling delegation,
silence and an agent's recommendation do not establish that delegation.

Every indexed row remains in `requirements` with the existing attribution,
disposition, contexts and product acceptance fields. Its source references must
refer to the engagement's declared private product notes. Selected promises require
actual user/reused provenance or the explicit scoped delegation above. These are
recorded claims, not authenticated approval.

Promise values use this shape; all descriptive fields are nonblank text:

```json
{
  "kind": "experience_promise",
  "user_task": "Investigate a selected record",
  "promise": "Useful evidence with a recoverable return",
  "primary_action": "Inspect record",
  "success": "Understand the record in its original scope",
  "first_use": "Enter the scoped record list",
  "repeat_use": "Return directly to the investigation"
}
```

A promise remains a required obligation. Each adopted target surface needs an
active sourced or delegated promise. Explicit omissions retain their actual source;
removing the last promise for a surface leaves that surface unresolved.

Mode values use `kind: experience_mode`, `mode`, and `rationale`. Supported modes
are `workspace`, `narrative`, `monitoring`, `guided_workflow`, `branded_entry`,
`custom` and `hybrid`. Custom modes also name `custom_label`; hybrids name at least
two distinct `components`. These names organize intent, not implementation APIs.
Creative hypotheses can retain `origin: proposal` and `disposition: unresolved`
with a concrete proposed mode value. Their presence does not block discovery.
An unresolved actual user constraint remains an open decision.

## Bind the chosen design to behavior

The existing concept gate owns the actual selection. The selected design adds
`experience_intent_handoff` with:

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `context` | Exact `experience_context(spec)` projection of current sourced meaning |
| `selected_mode_ids` | Indexed mode requirement IDs chosen by the selected concept, one per surface; a hybrid is one mode |
| `journey_ids` | IDs from the canonical `design.journeys` inventory |

Selecting a creative hypothesis here does not rewrite discovery or turn its
proposal attribution into user authorship. Existing sourced mode constraints must
remain honored. The stage gate must bind these mode IDs and their current semantics
to the actual selected concept and full intent. Concept manifests retain
`experience_direction` with `context`, `mode_requirement_ids`, `authors` and a
`modes` list containing each full canonical mode requirement except `delivery`, in
the same order as `mode_requirement_ids`. This pins meaning, attribution and
disposition without making a proposal a new sourced discovery decision. IDs alone
are not a freshness check.

Link each active promise through its existing `delivery.journeys`; declare governed
source/contract paths through its existing `delivery.dependency_paths`. The selected
intent's normal file pinning and current-candidate checks remain necessary. A nested
path string alone does not pin a file or establish a qualified query.

Each linked canonical journey adds `experience_behavior`:

| Field | Contract |
| --- | --- |
| `kind` | `transition` or explicit `single_view` |
| `trigger` | `{control_id, action}`; action matches the linked promise's `primary_action` and canonical journey `action` |
| `before`, `after` | `{destination_id, state, evidence_ids}` using canonical destinations and declared evidence IDs |
| `useful_change` | What useful evidence, understanding or operation the action supplies |
| `evidence` | Nonempty `{id, binding_ids, meaning}` rows |
| `governed_bindings` | Nonempty `{id, path, reference}` rows; paths must be explicit promise dependencies; references identify the governed query/field or source contract |
| `context_preservation` | Relevant scope, selected identity, ordering, focus or other context and reset rules |
| `return` | `{destination_id, control_id, state}`; returning to another destination needs a named control |
| `recovery` | `{empty, error}` describing relevant outcomes and a safe next step; retain unsupported behavior explicitly |

States and evidence must refer to declared identities. A transition requires a
named control and a changed state or evidence set; merely reordering IDs is not a
change. This checks declaration consistency, not whether the difference is useful.
An independent reviewer must assess that against the promise and actual evidence.

For a legitimate `single_view`, add `single_view_rationale`, use identical before
and after meaning, null trigger/return control IDs, and return to that same state.
The promised task, governed evidence, context and recovery obligations remain.
This case is available to deliberate single-view work without a mandatory mode,
extra screen, image, motion or 3D requirement. It does not waive assessment of any
filtering, refreshing or other transitions the selected product actually promises.

## Freshness, scope and evidence limits

`experience_context(spec)` includes the promises, scoped delegation and sourced
mode constraints. It deliberately excludes creative hypotheses and later delivery
annotations, so resolving design after concept comparison does not invalidate
discovery. Full intent/design pins still govern those excluded fields. Changing a
promise, acceptance criterion or source attribution changes the experience context.

Once adopted, the index cannot disappear. Preserve its requirement IDs; reconcile
removal through an attributable explicit omission. A sourced selected promise
cannot silently become an agent proposal. New or changed source decisions remain
subject to the existing versioned intent and selection procedure.

The contract permits up to 16 promise IDs, 16 mode IDs, 32 handoff journeys and
64 KiB of indexed canonical requirements. Each journey's behavior is bounded to
64 KiB, with at most 32 evidence and 32 governed-binding rows. Exceeding a bound
requires coherent scope reduction or splitting; do not truncate promises.
Bounded specialist packets retain relevant canonical requirements and exact
dependency pins; the coordinator retains the complete obligation inventory.

A consistent handoff reports `behavior_observed: false`. Source checks establish
neither useful product fit nor rendered, native, accessibility, security, numerical
or human acceptance. Review the first complete journey early, then retain the
denominator of all consequential destinations and promised behavior. Permission
limits leave unobserved requirements pending; they do not lower the quality promise.

## Compare three selectable products

Each concept must honor sourced mode constraints and name one viable mode per
surface; a hybrid is one mode. Keep every concept at the accepted analytical scope
and quality bar. Difference may come from the task sequence, evidence relationships,
information architecture or composition. Three labels, palettes or differently sized
rectangles are not substantive alternatives. The existing representative-artifact
checks still apply; comparison does not replace the visual evidence.

For adopted continuity, E's `evidence.comparison` points to a JSON record with:

| Field | Contract |
| --- | --- |
| `schema_version`, `kind` | `1`, `analyst_experience_comparison` |
| `reviewer` | Actual assigned reviewer identity, separate from each concept's `authors` |
| `context` | Exact current `experience_context(spec)` |
| `options` | Exactly three rows with `option_id`, exact `concept: {path,sha256,bytes}`, `task_relationship`, `action_outcome`, `evidence_gained`, `composition_difference`, `visual_locator` |
| `assessment` | `distinct_supported`; resolve a revise finding before submitting the options |
| `rationale` | Why these products are meaningfully distinct and feasible for this task |

The coordinator obtains this comparison from the existing independent creative
responsibility. Declared identities and text cannot prove independent work or
aesthetic quality. Do not satisfy the fields with renamed boilerplate. Record the
reviewer's actual critique and revise deficient concepts. Only the user's existing
E selection authorizes the detailed direction; no additional mode vote is needed.
Changing selected mode meaning or attribution requires reopening options/selection.

## Assess the whole candidate

Review the first useful end-to-end journey early to detect a dashboard-shaped app
before expanding it. This is an early feedback point, not a delivery denominator.
Before source closure, product-owner and UI/UX review every active promise and every
canonical destination and journey, including secondary pages and empty/error/return
states relevant to the task. A complete, deliberate monitoring view can be excellent;
extra navigation, writeback or 3D does not make it an app automatically.

For these two F scopes, `evidence.review` points to JSON with:

| Field | Contract |
| --- | --- |
| `schema_version`, `kind` | `1`, `analyst_experience_fit` |
| `reviewer`, `scope`, `basis` | Exactly match the enclosing review; reviewer differs from candidate builders |
| `candidate_sha256` | Exact enclosing candidate hash |
| `context` | Exact current experience context |
| `requirements`, `destinations`, `journeys` | Complete rows of `{id,assessment,candidate_locator,observation,evidence_paths}` |
| `observations` | Supplied observation pins `{path,sha256,bytes}` used by rows |
| `rendered_quality` | `unobserved` or `recorded_observation` |

Each row's assessment is `matched`, `gap` or `unobserved`. A resolved review requires
all rows matched with concrete locators and findings. Non-source matched claims need
bound observation paths. A resolved rendered review requires recorded observation;
source basis must retain `rendered_quality: unobserved`. These are evidence claims,
not image authentication or automatic scoring. Security and independent numerical/
behavioral QA retain their existing separate scopes and requirements.

Keep native qualification and customer acceptance separate. If inspection is not
authorized, perform source review honestly and retain the rendered limitation. Do
not load a renderer, library or browser to turn a source pass into visual acceptance.

## Preserve efficiency and existing engagements

This contract uses the current requirement index, canonical journeys, startup and
A–F journal. It does not create another orchestrator, design ledger or required
worker pool. Bounded packets carry an exact shared promise summary, selected mode
meaning and applicable delegation for every role, including dashboard engineering.
Full canonical rows follow explicit task scope and linked journeys, destinations
or governed dependencies; original shared restrictions remain mandatory. Unchosen
creative alternatives stay in the pinned intent instead of being copied to every
worker. The summary includes source pins, row hashes and pointers for requesting
exact detail before changing another promised behavior; omitted detail is not
waived. The orchestrator owns the complete inventory. Request specific missing
evidence instead of rereading the conversation or entire curriculum. Existing
byte limits still reject genuinely oversized scoped work rather than truncating it.

Valid source reviews can still carry forward under the optional incremental policy.
Their original fit record and dependency pins are retained. Changed dependencies,
unknown impact, a reviewer becoming a builder, and observed acceptance still require
the appropriate fresh review. Model settings, analytical validation and the four
review perspectives remain unchanged. Do not claim cost savings from packet size
alone; use existing observed usage and retry metrics when available.

Adopt in an existing engagement by adding sourced canonical promises, preserving
actual choices and journal history, and recording the affected D/E checkpoints.
Unadopted history stays `not_assessed`; do not manufacture retrospective receipts.
New non-report engagements require the index at D. Report-only engagements retain
the report-specific workflow. Repository checks and synthetic contract tests do not
establish improved aesthetics or accuracy equivalence on real data.
