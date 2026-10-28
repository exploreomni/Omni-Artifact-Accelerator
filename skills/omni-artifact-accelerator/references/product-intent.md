# Product discovery and the North Star

Use for a substantial new experience, material redesign or migration requiring
product decisions. The [product owner](../../omni-product-owner/SKILL.md) recovers
prior answers, interviews only for material gaps, and preserves the audience,
outcomes, priorities and experience promise. The orchestrator owns dispatch and
integration. Focused repairs reuse current intent without another interview.

For new products, follow the [data-first A–F workflow](data-first-product-workflow.md).
Intake can recover known preferences and source/access questions, but the artifact
interview follows verified data access, analysis and a reusable narrative. The PO
then coordinates three viable product options and retains the user's actual
selection before detailed design. This overrides generic permission to choose a
working design directly; a helper's selected flag is not a user decision.

## Adaptive front door

Begin with the original request and current decisions, not a blank questionnaire.
At stage D, clarify only what changes the next useful design: audience and outcome, first versus
repeat use, meaningful depth, brand authority/website/assets, relevant usable space
and delivery constraints. Reuse explicit no-logo, no-research and supplied-brand
choices. Specialists route new questions through this shared intake rather than
repeating discovery. Routine composition and implementation choices stay with them.

Translate quality ambition into observable experience intent without choosing a
universal shell. Designers own composition; branding owns assets; analysts own
metric meaning. Distinguish unavailable technology from the intended outcome. A
supported alternative must name what it preserves and what remains missing. Do not
silently substitute a smaller analytical task for an ambitious experience. CLI-only
constraints limit observation; they do not lower the requested quality bar.

Before final destination selection, have the analyst and experience owner inventory
relevant source capabilities against the requested tasks. The first saved query is
an input, not the scope ceiling. Record usable populations/eras and grain, useful
comparison/detail depth, selected/unsupported/deferred dispositions, reasons and
remaining gaps. Preserve a strong first journey without requiring extra screens,
sports-specific features, media or 3D. Use [source-inventory](execution-workflow.md#qualify-and-build-one-journey)
to pin this bounded evidence before the revised scope selection. Missing coverage
remains a question or gap; an inventory does not prove source exhaustiveness.

Keep attributable, minimal notes under the engagement's `inputs/` or `evidence/`,
outside the repository and skill installation. Retain source references, actual
decisions and uncertainty; omit unrelated transcripts, personal details and secrets.
See [notes and bounded handoff](../../omni-product-owner/references/intent-handoff.md).

## Add product context to existing intent

The selected versioned design intent remains canonical. These additive fields opt
an engagement into product-intent checks; legacy records remain usable and are
reported `not_assessed`. Do not create a second requirements ledger.
Once selected, product context and the attribution of required product requirements
cannot silently disappear in a later selection. Reconcile the scope and explicit
requirement dispositions; a focused repair can reuse that context without a new interview.

For guided visual discovery, also use the optional [visual experience index](#visual-experience-index).
It is required by new D checkpoints; historical selected engagements remain readable.

Add this fragment to the existing intent specification, using real private notes:

```json
{
  "product": {
    "schema_version": 1,
    "scope": "new_experience",
    "discovery": "sufficient",
    "note_paths": ["inputs/brief.txt", "evidence/discovery.md"]
  }
}
```

`scope` is `new_experience`, `material_redesign`, `migration` or `focused_repair`.
`discovery` is `sufficient`, `material_questions_open`, `reused_context` or
`focused_repair`. Record actual sufficiency, not user approval. Each note path must
be a real engagement file under `inputs/` or `evidence/`; these paths are pinned
with the selected intent. Keep independent work moving when a material question
blocks only part of the engagement.

The optional `product.source_inventory_path` names the generated private evidence
file. It is pinned with intent and shown as an evidence reference in the North Star;
its source inputs are rechecked for freshness without automatically forwarding
their raw contents. Review the inventory summary before sharing it. New/material
product `run-check` reports a missing inventory as incomplete. Legacy selection
and focused repairs stay valid without a new inventory; an existing inventory
cannot silently disappear, and stale inventory cannot establish current scope.

Annotate material product requirements inside the existing `requirements` list:

```json
{
  "product": {
    "priority": "must",
    "basis": "user_statement",
    "source_refs": ["inputs/brief.txt#experience"],
    "acceptance": ["Returning users can enter the investigation without repeating the introduction."],
    "suggested_roles": ["app-designer", "app-engineer"]
  }
}
```

This example adds metadata to a complete existing requirement, not a new schema
or ready-to-import file. `must` needs `required: true`; priorities also include
`should` and `could`. A priority never overrides the requirement's disposition.
`basis` must agree with `origin`: `user_statement` → `user`, `reused_decision` →
`reused`, and `inference`, `recommendation` or `unresolved` → `proposal`.
Source references point to declared note paths, optionally with attributable
fragments. The helper checks the path relationship, not the truth of a citation.
Acceptance statements and suggested existing roles are nonempty lists. Existing
technical requirements may remain unannotated; they do not disappear from scope.

## Data-refresh index

For an App, follow the [cache/refresh interview](../../omni-product-owner/references/data-refresh-policy.md)
after A–C. Source cadence informs D; it does not choose caching, polling or expiry.
Use this index over the existing required `interaction` requirement:

```json
{"data_refresh":{"schema_version":1,"requirement_id":"app-data-refresh"}}
```

This fragment belongs inside `product`. The referenced row has `surfaces: ["app"]`,
normal product source references to declared notes, observable acceptance, and its
actual decision reference. Its ID remains stable after adoption. Unanswered/deferred
rows remain unresolved; a neutral implementation posture is not a user answer.

The requirement's structured `value` uses `kind: "app_data_refresh"` and one mode:

- `no_custom_policy`: only `kind` and `mode`. This actual answer means inherited
  caching, initial/manual loading and no added polling, return refresh or age cutoff.
- `not_applicable`: only `kind`, `mode` and a nonempty `rationale` identifying the
  data-free App scope. Do not use this to skip policy discovery for a query-backed App.
- `custom`: `kind`, `mode` and exactly the following fields.

| Custom field | Accepted meaning |
| --- | --- |
| `query_cache` | `inherit` or `bypass`; a bypass still needs qualified native support. |
| `refresh_mode` | `manual`, `on_return`, `interval` or `interval_and_return`. |
| `interval_ms` | Positive safe integer only for an interval trigger; otherwise null. |
| `return_after_ms` | Positive safe integer only for a return trigger; otherwise null. |
| `max_age_ms` | Null for no client expiry, otherwise a positive safe integer. Qualify the chosen value against the actual helper/runtime limits. |
| `hidden_behavior` | `pause` or `continue`; continue requires an interval trigger. |
| `stale_display` | `timestamp`, `label` or `withhold`. An expiry requires label/withhold; withhold requires expiry. |
| `recovery` | Nonempty explanation of the selected retry/recovery behavior. |

Periodic refresh does not imply bypass or expiry. The selected policy is not a
provider payload, a backend TTL setting, or a guarantee of upstream freshness.
Helper expiry marks retained values stale; the App implements the selected display
and recovery behavior. Error/access and changed-scope clearing remain required.

User/reused decisions must be attributable. A selected agent recommendation needs
the optional index field `delegation_requirement_id`, pointing to a separate
required App interaction row with an actual selected user/reused decision and
value `{"delegation_scope":"app_data_refresh"}`. Other design delegation does
not delegate this policy. Attribution checks validate record structure, not the
authenticity of a human response or permission for native writes.

Readiness is `ready`, `unresolved`, `not_applicable` or historical `not_assessed`.
New App D checkpoints record the versioned context automatically; new dependent
concept work needs the resolved contract. Historical selected products stay
readable without invented decisions. Once adopted, the index and its stable
requirement cannot silently disappear. Reuse attributable answers when upgrading.

After E selection, the design must include `data_refresh_handoff` with exactly:
`context` equal to the helper's `data_refresh.context(spec)` projection,
`implementation` as a nonempty behavior explanation, and `qa_cases` as a nonempty
list of specific cases. This pins the same interview meaning through F rather
than asking engineering to infer another policy. The context includes source
references and decision meaning, excluding delivery ownership and implementation
contexts. A changed policy reopens affected D/E work; later implementation-only
annotations do not manufacture a new interview. Full design/candidate freshness
checks still apply. North Star and worker packets carry policy status and context.

## Visual experience index

Use the [guided questions](../../omni-product-owner/references/visual-experience-discovery.md)
after A–C. This index references the existing `requirements` list; it does not store
a second copy of user answers. The outer intent/product schema remains version 1.

```json
{
  "visual_experience": {
    "schema_version": 1,
    "family_requirement_ids": ["comparison-experience"],
    "follow_up": {
      "disposition": "answered",
      "requirement_ids": ["comparison-treatment"]
    }
  }
}
```

Add this fragment inside `product`; referenced complete requirement rows need the
usual purpose, surfaces, contexts, origin, disposition, decision reference and
product attribution/acceptance. Their values are:

| Requirement | Exact value shape |
| --- | --- |
| Experience family | `{"family":"compare_track"}`; other names: `locations`, `objects_environments`, `movement_flow`, `atmosphere_context` |
| User-defined family | `{"family":"custom","custom_label":"...","includes_comparisons":true}`; the boolean explicitly determines the conditional styling question |
| Answered or reused comparison treatment | `{"treatment":"dimensional_styling"}`, `interactive_3d`, or `refined_2d` |
| Explicit treatment delegation | `{"treatment":"delegated","delegation_scope":"comparison_treatment"}` |
| Not-applicable rationale | `{"rationale":"User selected an illustrative object inspection, with no comparative charts."}` |
| Optional explicit family delegation | `{"delegation_scope":"visual_families"}` |

`follow_up.disposition` is `answered`, `reused`, `delegated`, `not_applicable` or
`unresolved`. Answered rows require user-statement attribution; reused rows require
reused-decision attribution; delegated rows require an actual user/reused source.
The selected decision reference must be one of the row's source references. The
helper checks structure, not whether a note truly records a human answer.

An unresolved follow-up can have no referenced row yet, or open rows with a null
value or a proposed supported treatment. A not-applicable rationale must reference
source notes and is invalid while a non-omitted comparison family exists. Active
comparison proposals also trigger the question. Treatment coverage must include
each affected surface; an App answer does not silently cover a dashboard.

To let the designer recommend families, add optional
`family_delegation_requirement_id` to the index, pointing to the separately
attributed family-delegation requirement. Proposed family rows remain proposals;
they become usable for discovery only within the explicit delegation's scope.
Choosing “recommend a mix” for families alone does not delegate chart styling.

All active recognized visual family and treatment rows must be indexed. A prior
row may leave the index only when retained as an explicit omission backed by a
user or reused source. Unknown nested fields/versions, dangling
references, mismatched attribution and false not-applicable decisions fail. New
requirements preserve current intent history; explicit removal uses an attributable
omission rather than deleting a prior requirement. The North Star and worker
packets include the current visual-discovery state without forwarding all raw notes.

Use the versioned [D checkpoint](stage-gates.md#visual-discovery-at-d) to pin the
specification and its sources. Ready visual discovery permits new concepts, not
coding: E still needs exactly three concepts and the user's actual choice.

D compares discovery decisions and their attribution: requirement identity,
category, purpose, value, surfaces, required status, origin, disposition, decision
reference, priority, basis, sources, acceptance and any outcome-preserving
alternative. Record substantive user constraints in those canonical fields.
Later delivery ownership, suggested roles, asset/runtime bindings, review
annotations and implementation contexts (such as viewport and loading states)
do not reopen D. They still participate in full intent, detailed-design and
candidate freshness checks; this narrower D comparison does not waive those
checks. Actual visual preference or scope changes require a new D checkpoint.

For an unavailable method, the optional requirement `product.alternative` contains
exactly `unavailable_method`, `preserved_outcome`, `feasible_alternative` and
`remaining_gap`, each a nonempty explanation. Preserve the original requirement and
its status. A proposal or fallback is not customer acceptance. Escalate material
outcome/scope changes; ordinary reversible design choices need no extra approval.

## Quality bar in canonical requirements

For newly adopted quality policy, D also records the distinguishing qualities of
the experience. Recover supplied answers first. Ask only consequential gaps about
composition, imagery, depth, interaction, motion, spatial treatment, qualities to
borrow/avoid, or first versus repeat use. These are useful prompts, not mandatory
features. An analyst persona does not imply a simple interface; an immersive
request does not imply a particular library, 3D runtime or template.

Add `product.quality_bar` as an index, without copying requirement text:

```json
{"schema_version":1,"requirement_ids":["focal-composition","useful-inspection"]}
```

Each indexed row has the existing origin, disposition, source reference, surfaces,
priority and observable acceptance. Its value is
`{"quality":"composition","direction":"A focal comparison keeps its hierarchy when evidence opens."}`.
Other quality names are `typography`, `depth`, `interaction`, `spatial`,
`reference_qualities`, `use_cadence`, `imagery`, `motion`, and `custom`.
Custom adds a bounded `custom_label`. Imagery and motion add
`usage: "included"|"omitted"`, so omission is a recorded choice rather than a guess
from prose. Their inclusion is never required universally. Reference-quality
directions explain what to borrow and avoid; a brand name alone is insufficient.

Real user statements and reused decisions can resolve these rows. A recommendation
remains a proposal. It is ready only with optional
`delegation_requirement_id` pointing to a separately sourced selected requirement
whose value is `{"delegation_scope":"experience_quality"}` and whose surfaces
cover the recommendations. A styling/family delegation does not silently delegate
the quality bar. Source references must point to declared notes, and a selected
decision reference must be among its row's sources. These checks validate
attribution structure, not whether an author faithfully captured a human reply.

Empty or open decisions remain valid drafts with `unresolved` readiness. Each
product surface needs active quality decisions. Historical absence returns
`not_assessed`; it is not evidence of failure or permission to bypass newly
adopted policy. Active recognized quality rows must remain indexed. After adoption,
removing the index or deleting a prior indexed requirement is invalid; retain an
explicit user/reused sourced omission when scope genuinely changes.

`quality_context(spec)` uses the same semantic D boundary described above: values,
scope, provenance, priority and acceptance matter; later delivery ownership,
assets, suggested roles and context/review scaffolding do not reopen discovery.
Full selected-intent and candidate freshness still govern the latter. The North
Star and worker packet carry quality readiness and current indexed decisions.

## Concrete concept evidence and selected handoff

Each new E option names a bounded JSON `analyst_concept_manifest` with
`schema_version: 1`, `option_id`, `surface`, `analytical_scope`, `structure`,
`primary_interaction`, `responsive`, `quality_coverage`, `treatment_coverage`,
`representative`, and `constraints`. Coverage rows contain `requirement_id`,
`implementation` and `visual_locator`. Every active quality requirement for that
surface and every selected comparison-treatment requirement must be covered;
reused or recommended decisions cannot disappear between options.

The representative contains `path`, `evidence_kind`, `state` and a nonempty `labels`
list. `static_source` accepts an original, bounded SVG with actual graphic elements
and text labels. It rejects active content and external references; local paint
servers and embedded PNG/JPEG images are supported. `rendered_capture` accepts
PNG/JPEG plus a pinned local `observation_path` (`.json` or `.md`). The helper checks
file structure and dependency bytes, not pixels, evidence authenticity or visual
quality. A source specimen must never be described as an observed render.

Constraints contain nonempty `feasibility`, `assets`, `dependencies` and
`observation_limits`. Name actual data/runtime/asset gaps. Labels, comparative
scope and consequential state must be truthful and representative. A prose-only
file, ASCII layout or token palette does not establish concept evidence. Passing
structural checks alone cannot determine whether a specimen is useful or whether
three ideas are genuinely distinct; the reviewer still makes that judgment.

For an App plus dashboard product, each of the three options can use one
`analyst_concept_set`: `schema_version`, `kind`, `option_id`, `analytical_scope`,
`structure`, `primary_interaction`, and `surface_manifests`. The list contains one
single-surface manifest per required surface, with the same option identity and
analytical scope and a distinct concrete specimen per surface. Nested sets are
invalid. The stage layer retains exactly three comparable products and binds the
user's choice to their exact transitive bytes.

After choice, use the existing selected design's canonical `destinations` and
`journeys`; do not create a second screen or journey list. Add `experience_handoff`
with only `schema_version: 1`, `concept_manifest_path`, and `quality_coverage`.
Handoff coverage rows contain `requirement_id`, `implementation` and
`destination_ids`; their destinations cover the requirement's actual surfaces.

Each consequential destination retains `id`, `purpose`, `primary_action`,
`evidence`, `drill`, `return` and `responsive`, and resolves `focal_content`,
`composition`, `typography`, `chart_anatomy`, `controls`, `state_ownership` and
`journey_id`. A multi-surface design also identifies each row's `surface`.
Chart anatomy is `{applicable:true,details:"..."}` or
`{applicable:false,rationale:"..."}`; charts are not mandatory. Existing additional
design fields remain available. Canonical journeys have `id`, `destination_ids`,
`entry`, `action`, `detail`, `return`, `retained_state` and `recovery`.

When selected, imagery resolves `role`, `placement`, `crop`, `alternative_text`,
`fallback`, and `narrow`; motion resolves `trigger`, `purpose`, `continuity`,
`interruption`, and `reduced_motion`. A destination without that selected feature
uses `{applicable:false,rationale:"..."}`. At least one destination per affected
surface must realize the included feature. Explicit omission cannot coexist with
its implementation. Nothing requires imagery, motion, a hero or a universal shell.

The helpers return deterministic metadata and transitive `{path,sha256,bytes}`
dependencies. The stage owner binds the handoff's exact concept manifest to the
actual choice and checks freshness. This establishes declared design completeness,
not rendered craft, interaction, native behavior, user acceptance or publication
authority. Designers resolve real proportions, control behavior and state ownership;
nonempty field text is not an aesthetic certification.

## Generate and check the readable projection

After reconciling and selecting a version through the existing intent workflow:

```sh
python3 -I -S -B "$OAA_HELPER" product-brief --project "$OAA_RUN" \
  --output deliverables/north-star-v1.md
python3 -I -S -B "$OAA_HELPER" product-check --project "$OAA_RUN"
```

`OAA_HELPER` is the selected `analyst_project.py`; `OAA_RUN` is the existing private
engagement. Use a new output path for each projection. The generated North Star
names its source intent/version, SHA-256 and actual generation time. Its receipt is
stored in `project.json` as `product_brief` and `product_brief_history`.

`product-check` checks the current selection, pinned notes, projection receipt and
bytes, including recomputing the expected projection. It returns `consistent`,
`inconsistent` or `not_assessed`; consistency proves no product fit, visual quality,
source authenticity or approval. Treat an edited North Star as proposed new input:
retain the edit, reconcile a new canonical intent version and regenerate. Do not
refresh hashes to bless stale prose or overwrite historical decisions.

New packets include `product_context` and current projection dependencies when
enabled. The role slice suggests relevant requirements; the complete intent remains
in scope. All declared notes remain pinned for freshness, but automatic note-file
inputs are limited to the product owner. Other specialists receive the North Star
and role slices with source references, not blanket access to the private notes.
Include a note explicitly through `--input` or a declared delivery dependency only
after reviewing the destination host's disclosure boundary. Review the readable
projection itself for sensitive information before sharing it.

When intent already contains the decisions, use `delivery-project` to propose the
delivery annotation projection instead of reauthoring requirements. It preserves
selected requirements and only copies explicit facts or supplied annotations;
suggested roles never become assigned owners automatically. Select the reconciled
proposal through the normal intent workflow and regenerate this projection.

A product-owner packet may proceed to repair an inconsistent projection;
that exception does not make the projection current or authorize implementation
from stale context. Other dependent packets must wait for reconciliation.

## Handoff and three separate review questions

These three product/design/correctness questions remain distinct. New-product
iterations also require the separate security perspective specified in
[stage F](data-first-product-workflow.md#f-implement-cohesively-and-review-every-iteration);
do not interpret this section as permission to omit it.

The PO returns brief/intent pins, sources and decisions, priority, acceptance intent,
gaps and proposed specialist slices. The orchestrator creates actual assignments
through the unchanged schema-1 envelope. `product-owner` is a frontend
discovery/App/dashboard role, not a new DMA backend role or a second dispatcher.

For product-enabled scope other than `focused_repair`, `run-check` expects the
existing responsibilities plus `product_intent` owned by `product-owner` and
`creative_review` owned by `app-designer`, `dashboard-designer` or `design-systems`.
The creative reviewer must differ from both builder and originating designer.
One suitable independent worker may own creative and correctness reviews, but must
record separate findings. Missing independent observation remains pending; never
invent worker identities. Legacy seven-responsibility records remain valid.
`run-check` also reports `material_questions_open`; resolve or explicitly retain
the affected gap rather than claiming discovery is sufficient. Focused-repair
planning does not add a product-owner suggestion or restart discovery.

For a focused repair, use `plan --project "$OAA_RUN" --scope-id <existing-id>`
for each affected requirement. The helper proposes only relevant recorded owners,
capabilities and review; without scope IDs it returns an empty role plan with a
scope reminder, not the broad new-build team. This scopes advice, not the full
requirement inventory. On intent selection, known starter questions are replaced
with current intent questions; separately recorded questions are retained.

- **Product fit:** did the candidate preserve the requested outcomes, priorities
  and experience promise? PO gives a recommendation and remaining differences.
- **Creative craft:** does the composition and interaction realize that promise?
  A different reviewer critiques the exact candidate; originating designers revise.
- **Correctness:** are numbers, behavior, access and runtime claims supported?
  Independent QA retains its own evidence lanes.

Build one ambitious representative journey early: include the experience's defining
qualities, useful evidence/detail and return where relevant. A reduced technical
demo cannot qualify an omitted experience promise. Review before expanding, then
account for every consequential destination. Under CLI-only restrictions, repair
source-observable omissions and retain rendered/native/human lanes as unobserved.

Record clarification, correction of supplied requirements, new preferences/scope
and internal revision separately. No customer response means acceptance and need
for customer correction are unobserved. Neither low prompt counts nor passing
helpers establishes premium delivery. These additions do not activate installed
skills or change publication/runtime authority.
