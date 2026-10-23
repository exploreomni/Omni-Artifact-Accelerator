# Scoped design evidence and version checks

Use this optional record for substantial new experiences, material redesigns, or an affected-area review that needs reproducible file/version checks. It extends version-1 projects; it is not a second lifecycle or permission service. Existing projects remain readable. A missing record is `not_assessed`, never an inherited pass.

The design owner critiques composition, hierarchy, type, chart finish and task value against the selected design. QA independently checks outcomes and the evidence versions. The implementer supplies deviations and fixes; its own review cannot close an independent craft case. Keep numerical, craft, native behavior, responsive, accessibility, access, performance, participant and business evidence distinct. No numerical beauty score is used.

## Early journey and whole-experience review

For substantial work, review one exact assembled `entry → primary action → useful detail/evidence → return` path before scaling to other destinations. Use original source expectations for the primary result and a consequential malformed/missing or changed-scope case. Record whether the receive path used an observed native payload or a labeled simulation. The experience owner critiques hierarchy and task usefulness; QA tests the relevant outcomes independently. Reuse accepted expectations when a revision changes only presentation.

Before claiming the whole experience complete, reconcile each consequential destination with its stable design ID and original requirement: purpose, dominant subject, primary action, supporting evidence, drill/return, retained state and relevant constrained layout. Use existing cases/deviations/evidence files, not a new evidence lane. The optional [delivery coverage check](../../omni-artifact-accelerator/references/first-delivery.md) finds declared omissions/pin issues; it cannot establish that a destination is useful or that the requirements are complete.

Inspect observable behavior, not component names or element existence. A calendar case exercises the selected date navigation and correct placement/detail, including unknown dates; an exploration case checks camera/selection/reset without altering measured values; a playback case requires actual provider controls and playback when authorized. An iframe load, nonzero dimensions, successful metadata response or configured allowlist does not prove playback. A dated snapshot or external watch link may satisfy its selected fallback while the original live/in-App requirement remains open. Engineering owns capability qualification and permitted recovery; QA must not widen policy to obtain a pass.

Choose a few task-relevant phone, short-laptop or wide contexts by usable width/height and permitted methods. Check a real drill/return journey, not just disconnected screenshots; native behavior requires actual exercise. Under prohibited rendering/native observation, retain independent assembled/source findings and leave the affected visual/native cases unrun. Fix material findings within existing authorization, retest only affected behavior, and name remaining differences in closeout rather than treating publication or matching readback as experience acceptance.

## Renderer and transfer review

When assessing a reusable App behavior framework, exercise the same source scope, identities, state transitions and expected outcomes through multiple materially different renderers. Check equivalent selection/filter/error/return behavior and usable exact evidence; inspect each renderer's actual composition, typography, density and constrained layout separately. A shared controller pass does not transfer visual or accessibility results between renderers.

Add a bounded fresh-context domain task using its raw brief and minimal sources, without a prescribed layout or previous engagement app. Judge its rationale and result against that brief. Intentional similarity is allowed; novelty and component-count differences are not quality measures. Use existing candidate/case records per renderer rather than adding a new lane or requiring every engagement to create alternatives. Native dashboards and faithful migrations retain their own evidence obligations.

Structure-only or CLI execution may expose coupling and behavioral defects; rendered polish, native behavior and participant understanding remain unobserved until their own checks run.

## Commands and authority

From an engagement, author a JSON specification using the schema below. All file references are canonical engagement-relative paths, confined to the engagement, without symlinks; files are bounded to 10 MiB each. Keep secrets and unnecessary personal information out of these records.

```bash
python3 /path/to/skills/omni-artifact-accelerator/scripts/analyst_project.py design-pin \
  --project "$ENGAGEMENT" --path deliverables/app-v2.html
python3 /path/to/skills/omni-artifact-accelerator/scripts/analyst_project.py design-freeze \
  --project "$ENGAGEMENT" --spec "$ENGAGEMENT/contracts/design-review-spec-v2.json" \
  --output contracts/design-review-v2.json
python3 /path/to/skills/omni-artifact-accelerator/scripts/analyst_project.py design-check \
  --project "$ENGAGEMENT"
```

`design-pin` reads a file and returns `{path,sha256,bytes}`. `design-freeze` creates a new immutable `analyst_design_review`, retains the original spec and all referenced file pins, and selects its `{path,sha256,bytes}` in `project.json.design_review`; prior selections remain in `design_review_history`. It never overwrites a review. Freeze succeeds with incomplete declared coverage, returning `{path,report}` so gaps remain visible. Missing named files or invalid schemas fail before writing. Missing *undeclared* concepts/cases are reported as coverage gaps.

`design-check --record contracts/design-review-v1.json` checks a historical record explicitly; otherwise it checks the selected one. Exit 0 means recorded coverage is complete for the declared whole or focused scope (inspect `coverage` and `destination_coverage.mode`), 1 means incomplete/stale, and 2 means an invalid record. `verify` includes this result as `design_evidence` but retains its original structure/integrity semantics: missing design coverage alone does not make an older project unreadable or production-ready.

Library entrypoints in `analyst_project.py`: `design_pin(root,path)`, `design_freeze(root,spec_path,output_relative)`, `design_check(root,record_relative=None)`. The scripts make no network calls, execute no artifacts and perform no native writes.

**Coverage is not quality certification.** The checker validates declarations, references, image signatures and exact bytes. It does not decode/visually judge images, authenticate reviewers or origins, observe native behavior, verify that two concepts differ meaningfully, prove participant understanding, accept business requirements or authorize publication. PNG/JPEG/WebP signatures identify candidate image files; HTML/prose is not a concept render. Independently inspect the actual images and test the stated behaviors.

## Specification

Top level: `schema_version:1`, `kind:"analyst_design_review_spec"`, `id`, `scope`, `dependencies`, and optional `concepts`, `selection`, `captures`, `deviations`, `findings`, `cases` collections. Collections default empty, preserving visible missing coverage.

| Record | Exact fields / behavior |
| --- | --- |
| `scope` | `coverage` names review extent with `mode` set to `whole_experience` or `focused`, and `affected_obligation_ids` only for focused. `change`: `material_new`, `material_redesign`, `focused_edit`, or `faithful_migration`; `rationale`; `surfaces`: selected project surfaces; `required_lanes`: explicit selected completion scope, including `craft`. Available lanes: `craft`, `numerical`, `native_behavior`, `responsive`, `accessibility`, `access`, `performance`, `human_usability`, `business_acceptance`. |
| Dependency | Unique `id`, `kind`: `candidate`, `design`, `brand`, `query`, `source`, or `expectation`; `surface`: `app`, `dashboard`, or `shared`; `path`. Include exact resolved design, brand/query/semantic/source inputs relevant to the work, not an indiscriminate whole repository. Each surface needs exactly one candidate and a resolved-design dependency. A numerical pass also requires query and independently derived expectation dependencies. |
| Candidate target | Candidate dependencies additionally have `target:{surface,state,document_id,draft_id}`. `state` is `local`, `draft`, or `published`. Remote targets require `instance` as an HTTPS origin and real `document_id`; drafts also require the exact `draft_id`. For local candidates, IDs may be null. Non-drafts have null/absent `draft_id`. The candidate file hash supplies the exact retained content version; target declarations do not authenticate current remote state. |
| Concept | Unique `id`, `surface`, `task`, `composition`, `tradeoffs`, `render_paths:[...]`. For material new/redesign, explicit direct exploration permits one selected rendered concept; compare requires at least two rendered concepts. Comparable data/context and meaningful comparison are human review obligations. Focused edits and faithful migrations need no invented alternatives. |
| Selection | `selection` is keyed by surface: `{concept_id,status:"proposed"|"user_accepted",rationale}`, optionally with `exploration:{mode:"direct"|"compare",rationale}` where rationale is nonempty. New material work records its reasoned direct or compare choice. Absent exploration preserves the legacy two-rendered-concept interpretation; it is not a universal design rule. Agent selection stays proposed; the helper does not authenticate acceptance. |
| Capture | Unique `id`, `kind:"native"|"prototype"`, `candidate_id`, `candidate_sha256`, `path`, `context:{viewport:[width,height],appearance,state}`, plus `destination_id`, `requirement_id`, `requirement_context`. Use exact candidate bytes, observed viewport/appearance/state and an actual retained image. Context is a declaration, not measured by the helper. |
| Case | Unique `id`, `surface`, `lane`, `candidate_id`, `target` matching that candidate exactly, `status`, `executed` boolean, `method`, `reviewer`, `observation`, `reviewed_dependencies:{dependency_id:sha256}`, `evidence_paths:[...]`, and `capture_ids:[...]` when visual, plus explicit `obligation_ids`. Share numerical evidence across named obligations without duplicating execution. Pass requires executed evidence. `not_applicable` requires a substantive `rationale`; craft cannot be excluded from a design review. |
| Deviation | Unique `id`, `surface`, `candidate_id`, `candidate_sha256`, `intended`, `actual`, `reason`, `disposition`, `designer`, `designer_role`, `rationale`, `evidence_paths`. `disposition` is `unresolved`, `accepted`, or `corrected`. Add `obligation_ids` for the affected scope. A correction additionally needs `retest_case_id` referencing a current passing craft case covering those same obligations, destination/context and candidate. Unresolved/unsupported dispositions keep coverage incomplete. |
| Finding | Unique `id`, `surface`, `case_id`, `problem`, `impact:"material"|"minor"`, `owner`, `disposition`, `evidence_paths`; accepted minor findings need `rationale`, add `obligation_ids`; corrected findings need `retest_case_id` covering the same obligations and lane/surface on the current candidate. Material findings stay open until corrected with a passing retest. Retain annotated capture and setup through the case/capture records. |

Direct exploration changes only the concept-coverage requirement. Candidate-bound rendered craft, independent review, native observations and other selected lanes retain their existing requirements; one reasoned concept is not a polish pass. When rendering is prohibited, keep those cases unrun rather than manufacturing alternatives or captures.

All case statuses use `pass|fail|blocked|not_run|not_applicable`. Cases represent the current review version; retain prior failed runs/specs as immutable historical records and evidence, then create a new spec/review for the retest. Do not erase earlier observations or turn a different lane's pass into a retest. Retaining a failing case and a passing retest together in the current review keeps that obligation incomplete; there is no implicit supersession. Keep the initial failed execution in its immutable prior review/evidence, and freeze a new local review record containing the current executed cases and matching correction references.

Craft passes require `method:"designer_critique"`, `reviewer_role` of `app-designer`, `dashboard-designer` or `design-systems`, `independence:"independent"`, and candidate-bound captures. Inline/self-review is useful but remains disclosed and cannot close the independent craft claim. Native behavior requires `method:"native_observation"` with native captures and a remote target. `human_usability` requires `participant_observation`; an agent rehearsal cannot substitute. Responsive/accessibility passes require captures, but a screenshot alone cannot support full accessibility conformance: independently inspect the execution notes and selected case scope.

A visual review of a remote draft or published candidate requires `kind:"native"` captures even when its method is `designer_critique`; a prototype supports only its local candidate. A native capture cannot support a local-only target. This validates the declared relationship, not the authenticity of a screenshot. Required review text and applicability rationales must contain non-whitespace text; the reviewer must still judge their substance.

App and dashboard candidates may intentionally share one Omni document and draft. Keep distinct surface-specific candidate IDs, target `surface`, case records and capture bindings. Sharing the document does not permit an App capture to close the dashboard's review or vice versa. A whole-window image may be referenced by separately bound captures only when each surface is actually visible and independently reviewed.

## Named design requirements

The existing requirement binding also supports named experience choices such as `experience-mode`, `entry-return-journey` and `art-direction`; see [examples](../../omni-artifact-accelerator/references/design-intent.md#experience-requirements). Inspect their intended outcome, not just an asset or control's existence. Keep `user requirement → selected design → implementation → observation/gap` in the case expectation, observation and linked deviation evidence. This does not add a new lane or relax native named-requirement rules.

Under a no-rendering constraint, retain the independent source-review report in the case's declared `evidence_paths` and as an explicit packet input when relevant. Keep craft/native cases `not_run` if their required observations were not performed. A report may identify architecture or continuity defects without establishing polish; no source-only pass category is introduced. Never fabricate a capture to satisfy coverage. For positive user feedback, retain the actual response and its scope separately from unperformed usability or acceptance cases.

When a [design-intent selection](../../omni-artifact-accelerator/references/design-intent.md) exists, bind this review with `intent: {path, sha256}` matching `project.design_intent`. Use `intent-cases --project "$ENGAGEMENT"` for not-run templates; these are not complete cases or observations. For new freezes, use the generated `obligation_ids`, a nonblank `expected` outcome and candidate-bound captures with explicit destination/requirement/context bindings. Visual cases retain the exact union of bound requirement asset IDs. Complete the ordinary case reviewer/method/evidence fields too. Historical named cases retain their original `requirement_id`/`requirement_context` interpretation.

Reconcile design/brand dependencies and the candidate path/target with the selected intent. Capture appearance/state, and viewport when declared, must match the named context. Inspect the actual target for the named outcome: selected logo/variant visible in its expected placement, intended typography or chart labels legible, or the primary task functioning. Mere image presence, an HTML tag or a general craft pass cannot establish it. Named requirement fulfillment requires a selected draft/published target and native captures; a prototype can support a local craft review but cannot close the named native requirement. Source/use authorization and reviewer claims remain unauthenticated.

The checker reports `intent_coverage` separately. Required unresolved/deferred choices remain open; a selected requirement needs matching current passing observations for every required surface/destination/context and applicable journey. Explicit omission retains its decision reference. Changed intent/assets or a mismatched design/brand/candidate chain cannot inherit old coverage. Keep historical findings, create new versioned records after affected retests, and do not convert a design summary into publication or DMA semantic acceptance. An older review without intent binding stays unassessed for named requirements rather than inheriting a pass.

## Destination and journey coverage

Every **new freeze** stamps the current destination-coverage policy internally. Missing intent, inventory, applicability, cases or scope bindings produce visible gaps; deleting fields cannot select historical interpretation. Historical immutable records retain their original checks and report destination coverage as `not_assessed`. That does not qualify them as newly reviewed whole experiences. `experience-check` continues to report structural readiness only.

Use the selected design's `destinations` and current requirements' `delivery.destinations` as the inventory. A destination may be a screen, dashboard page or meaningful panel. Repeated entities using one composition are representative data contexts; preserve separate source placements when query, behavior or access differs. In each selected requirement context, declare sparse applicability:

```json
{
  "id": "short-workspace", "appearance": "light", "state": "ready",
  "viewport": [1280, 640],
  "applicability": [{
    "kind": "destination", "id": "investigation",
    "lanes": {
      "craft": {"status": "required"},
      "numerical": {"status": "required"},
      "native_behavior": {
        "status": "not_applicable",
        "rationale": "This selected observation covers a static composition; behavior is covered by the separately named selection journey.",
        "decision_ref": "contracts/review-scope.md: observation allocation"
      }
    }
  }]
}
```

An applicability row may add `surface:"app"` or `surface:"dashboard"` to address different destination IDs under one cross-surface requirement; when omitted it applies to all of that requirement's surfaces. Account for every selected review lane at each selected destination/context through a required obligation or justified exclusion. Missing lane applicability is a gap; `craft` cannot be excluded. This example describes allocation, not permission to omit actual behavior. Never multiply every screen by every possible viewport/state or use exclusions to hide a required outcome. Keep unresolved/deferred required work open and user/reused explicit omissions distinguishable from passes.

Generate templates for the actual review scope:

```sh
python "$OAA_HELPER" intent-cases --project "$OAA_RUN" \
  --review-spec contracts/design-review-spec-v1.json
```

Without a review spec, generated templates cover craft only; they cannot establish coverage for lanes selected later. Obligation IDs consist of URL-escaped `requirement/surface/kind/target/context/lane` segments. Copy generated IDs instead of inventing a separate ledger. Each new passing case has a nonblank `expected` outcome and explicitly lists `obligation_ids`; visual cases retain the exact union of `asset_ids` from their bound requirements. Legacy `requirement_id`/`requirement_context` cases remain interpretable for historical reviews. Captures name the observed destination, requirement and context as well as exact candidate/target bindings. An image of one destination cannot close another destination's observation.

For an applicable journey, the selected design declares `journeys:[{id,path,action,start_state,end_state,retained_context,return_behavior}]`; `path` is an ordered list of selected destination IDs, including repeated IDs for same-screen transitions. Link IDs with `delivery.journeys` and context applicability `kind:"journey"`. The same requirement must also list its captured endpoint destination IDs in `delivery.destinations`, with destination applicability for those IDs; a journey-only link does not bind its endpoint captures. Reuse meaningful contexts or add the necessary start/end contexts rather than inventing more destinations. A static dashboard needs no invented journey. Case `journey_observations` rows bind `obligation_id`, the exact expected `path`, `action`, `start_state`, `end_state`, `retained_context` and `return_behavior`, plus `method` (`local_execution`, `native_execution` or `participant_observation`), actual `observation` and `evidence_paths`. Retain a nonempty UTF-8 `.txt`, `.md` or `.json` execution note in those evidence paths; image bytes cannot substitute. Visual journey cases also bind first/last destination captures to the requirement/context, selected appearance and viewport, and the journey's actual start/end states. Intermediate destination craft remains covered by its own applicable destination observations. Preserve actual setup and sequence evidence, not merely expected values copied into a record. Local execution stays local; an endpoint still cannot establish an exercised transition, filter/focus restoration, interruption or playback.

Journey `id`, `action`, `start_state`, `end_state`, `retained_context` and `return_behavior` are nonblank strings; only `path` is a list. For example, use `retained_context:"Selected entity, filters and originating panel remain selected"`, not an array of field names. Copy the selected candidate's complete target object into cases and captures, including any explicit null fields; an omitted field is not an exact target match.

Whole-experience reviews derive obligations from the complete selected inventory before considering cases. Focused reviews retain that inventory and explicitly name `affected_obligation_ids`; their result is scoped, never an implied whole-experience pass. Findings and deviations carry affected obligation IDs. A corrected finding requires a current passing retest for the same obligations; a different screen, context or journey cannot close it. Exact candidate freshness remains mandatory even when a visual region appears unchanged in source.

`design-check` exposes destination/journey obligations, recorded outcomes and gaps separately from named native requirement fulfillment. Local rendered craft can support its local coverage; it cannot fulfill a named native requirement. `verify` includes this report without changing publication, business acceptance or historical project readability. All observations and reviewer identities remain unauthenticated declarations that require independent inspection.

## Scope and dependency rules

For a faithful migration, pin `scope.source_obligations_path` and a `source` dependency. Preserve source controls, calculations, identities and accepted differences. A deviation declares `affects_source_behavior:false` if purely presentational; otherwise it needs `accepted_difference_path` pointing to the exact retained accepted-difference evidence. An optional `scope.accepted_differences_path` can pin the existing difference register. Changing a migration into material new/redesign requires explicit retained `scope.scope_change_path`; the helper records that evidence, it does not grant the scope change.

Every case must list the candidate hash. Additional relevant dependency pins are mandatory according to this map, scoped to its own surface or `shared`:

| Changed dependency | Reopened evidence |
| --- | --- |
| Candidate bytes | All candidate-specific cases |
| Resolved design | Craft, native behavior, responsive, accessibility, human usability |
| Brand/theme | Craft, responsive, accessibility, human usability |
| Query/metric/semantic binding | Numerical, native behavior, access, performance, human usability |
| Source snapshot/obligations | Numerical, native behavior, access, human usability |
| Independent expectations | Numerical, native behavior, human usability |

A changed capture/evidence file invalidates its associated case; stale files keep the review's overall coverage incomplete. A changed original spec invalidates the record's cases. Changed inputs do not erase valid observations in unrelated lanes; the report preserves each reported status separately from its current recorded status and lists the reasons it cannot support a pass. Freeze a new reviewed version deliberately after executing affected retests—never refresh hashes merely to make old observations appear current.

The checker cannot discover a real requirement omitted from both the original-brief translation and the selected inventory, an omitted real dependency or an undeclared deviation. QA must reconcile those against the actual assignment and implementation. Do not remove a required lane to obtain complete coverage. Full accessibility conformance and business acceptance require separately qualified evidence; recorded complete coverage never certifies either.
