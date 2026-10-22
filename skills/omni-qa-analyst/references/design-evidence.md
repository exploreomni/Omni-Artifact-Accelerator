# Scoped design evidence and version checks

Use this optional record for substantial new experiences, material redesigns, or an affected-area review that needs reproducible file/version checks. It extends version-1 projects; it is not a second lifecycle or permission service. Existing projects remain readable. A missing record is `not_assessed`, never an inherited pass.

The design owner critiques composition, hierarchy, type, chart finish and task value against the selected design. QA independently checks outcomes and the evidence versions. The implementer supplies deviations and fixes; its own review cannot close an independent craft case. Keep numerical, craft, native behavior, responsive, accessibility, access, performance, participant and business evidence distinct. No numerical beauty score is used.

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

`design-check --record contracts/design-review-v1.json` checks a historical record explicitly; otherwise it checks the selected one. Exit 0 means recorded coverage is complete, 1 means incomplete/stale, and 2 means an invalid record. `verify` includes this result as `design_evidence` but retains its original structure/integrity semantics: missing design coverage alone does not make an older project unreadable or production-ready.

Library entrypoints in `analyst_project.py`: `design_pin(root,path)`, `design_freeze(root,spec_path,output_relative)`, `design_check(root,record_relative=None)`. The scripts make no network calls, execute no artifacts and perform no native writes.

**Coverage is not quality certification.** The checker validates declarations, references, image signatures and exact bytes. It does not decode/visually judge images, authenticate reviewers or origins, observe native behavior, verify that two concepts differ meaningfully, prove participant understanding, accept business requirements or authorize publication. PNG/JPEG/WebP signatures identify candidate image files; HTML/prose is not a concept render. Independently inspect the actual images and test the stated behaviors.

## Specification

Top level: `schema_version:1`, `kind:"analyst_design_review_spec"`, `id`, `scope`, `dependencies`, and optional `concepts`, `selection`, `captures`, `deviations`, `findings`, `cases` collections. Collections default empty, preserving visible missing coverage.

| Record | Exact fields / behavior |
| --- | --- |
| `scope` | `change`: `material_new`, `material_redesign`, `focused_edit`, or `faithful_migration`; `rationale`; `surfaces`: selected project surfaces; `required_lanes`: explicit selected completion scope, including `craft`. Available lanes: `craft`, `numerical`, `native_behavior`, `responsive`, `accessibility`, `access`, `performance`, `human_usability`, `business_acceptance`. |
| Dependency | Unique `id`, `kind`: `candidate`, `design`, `brand`, `query`, `source`, or `expectation`; `surface`: `app`, `dashboard`, or `shared`; `path`. Include exact resolved design, brand/query/semantic/source inputs relevant to the work, not an indiscriminate whole repository. Each surface needs exactly one candidate and a resolved-design dependency. A numerical pass also requires query and independently derived expectation dependencies. |
| Candidate target | Candidate dependencies additionally have `target:{surface,state,document_id,draft_id}`. `state` is `local`, `draft`, or `published`. Remote targets require `instance` as an HTTPS origin and real `document_id`; drafts also require the exact `draft_id`. For local candidates, IDs may be null. Non-drafts have null/absent `draft_id`. The candidate file hash supplies the exact retained content version; target declarations do not authenticate current remote state. |
| Concept | Unique `id`, `surface`, `task`, `composition`, `tradeoffs`, `render_paths:[...]`. Material new/redesign requires at least two rendered alternatives for each surface. Comparable data/context and materially different composition are human review obligations. Focused edits and faithful migrations need no invented alternatives. |
| Selection | `selection` is keyed by surface: `{concept_id,status:"proposed"|"user_accepted",rationale}`. Required for material new/redesign. Agent selection is proposed; a supplied accepted claim is not authenticated by the helper. |
| Capture | Unique `id`, `kind:"native"|"prototype"`, `candidate_id`, `candidate_sha256`, `path`, `context:{viewport:[width,height],appearance,state}`. Use exact candidate bytes, observed viewport/appearance/state and an actual retained image. Context is a declaration, not measured by the helper. |
| Case | Unique `id`, `surface`, `lane`, `candidate_id`, `target` matching that candidate exactly, `status`, `executed` boolean, `method`, `reviewer`, `observation`, `reviewed_dependencies:{dependency_id:sha256}`, `evidence_paths:[...]`, and `capture_ids:[...]` when visual. Pass requires executed evidence. `not_applicable` requires a substantive `rationale`; craft cannot be excluded from a design review. |
| Deviation | Unique `id`, `surface`, `candidate_id`, `candidate_sha256`, `intended`, `actual`, `reason`, `disposition`, `designer`, `designer_role`, `rationale`, `evidence_paths`. `disposition` is `unresolved`, `accepted`, or `corrected`. A correction additionally needs `retest_case_id` referencing a current passing craft case on the same surface. Unresolved/unsupported dispositions keep coverage incomplete. |
| Finding | Unique `id`, `surface`, `case_id`, `problem`, `impact:"material"|"minor"`, `owner`, `disposition`, `evidence_paths`; accepted minor findings need `rationale`, corrected findings need `retest_case_id` in the same lane/surface. Material findings stay open until corrected with a passing retest. Retain annotated capture and setup through the case/capture records. |

All case statuses use `pass|fail|blocked|not_run|not_applicable`. Cases represent the current review version; retain prior failed runs/specs as immutable historical records and evidence, then create a new spec/review for the retest. Do not erase earlier observations or turn a different lane's pass into a retest.

Craft passes require `method:"designer_critique"`, `reviewer_role` of `app-designer`, `dashboard-designer` or `design-systems`, `independence:"independent"`, and candidate-bound captures. Inline/self-review is useful but remains disclosed and cannot close the independent craft claim. Native behavior requires `method:"native_observation"` with native captures and a remote target. `human_usability` requires `participant_observation`; an agent rehearsal cannot substitute. Responsive/accessibility passes require captures, but a screenshot alone cannot support full accessibility conformance: independently inspect the execution notes and selected case scope.

A visual review of a remote draft or published candidate requires `kind:"native"` captures even when its method is `designer_critique`; a prototype supports only its local candidate. A native capture cannot support a local-only target. This validates the declared relationship, not the authenticity of a screenshot. Required review text and applicability rationales must contain non-whitespace text; the reviewer must still judge their substance.

App and dashboard candidates may intentionally share one Omni document and draft. Keep distinct surface-specific candidate IDs, target `surface`, case records and capture bindings. Sharing the document does not permit an App capture to close the dashboard's review or vice versa. A whole-window image may be referenced by separately bound captures only when each surface is actually visible and independently reviewed.

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

The checker cannot discover an omitted real dependency, undeclared deviation or narrower-than-required completion scope. QA must reconcile those against the actual assignment and implementation. Do not remove a required lane to obtain complete coverage. Full accessibility conformance and business acceptance require separately qualified evidence; recorded complete coverage never certifies either.
