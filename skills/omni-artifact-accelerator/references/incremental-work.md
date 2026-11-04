# Incremental work and bounded context

The [host execution interface](host-execution.md) exposes these existing operations
without loading unrelated source tools. The optional operator-supplied worker
adapter fences launch/reconciliation and retains output ownership until observed
termination. Supplied dispatch records remain declarations, not authenticated execution.

Use this workflow to reduce repeated source ingestion, duplicate dispatch and
unchanged review work. It preserves A–F, the selected experience and the separate
source, rendered, native, human and publication boundaries. Skills describe
responsibilities; they are not a requirement to launch one agent per skill.

## Adoption and compatibility

New CLI `init` projects use `--context-policy bounded-context-v1`. Python callers
retain the legacy default unless they supply `context_policy='bounded-context-v1'`.
Existing engagements retain their policy. Adopt explicitly with:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py efficiency-configure --project /absolute/engagement --request /absolute/context-policy.json
```

The request is `{"policy":"bounded-context-v1","reason":"Use bounded specialist context"}`.
Checkpoint active workers before changing policy. The project retains prior
policy transitions. `legacy-index-v1` is an explicit compatibility rollback;
neither policy changes authorization, deletes history or installs anything.
Context migration does not automatically adopt review reuse.

## Prepare once, dispatch only necessary work

1. Inventory/extract each source version once and retain original evidence and
   parser/version pins. Reuse unchanged verified outputs with `claim-work`.
   A changed source, parser or relevant requirement needs affected extraction,
   not an automatic rescan of every platform guide and historical artifact.
2. Use `work-prepare --project PROJECT --request REQUEST.json` for schema-aware
   packet preparation. Supply `role`, `inputs`, `output` (a new `tasks/*.json`),
   and the existing assignment fields, replacing `input_bindings`/`dependencies`
   with `dependency_paths`. Current hashes are computed locally. Same requests
   reuse the packet; changed work requires a new path. The command does not
   choose scope, create an approval or dispatch a model.
3. Build bounded context using `context-build --project PROJECT --request
   CONTEXT.json --output tasks/context-v1`. It writes immutable `TASK.md` and
   `CONTEXT_RECEIPT.json`. Use `context-check --project PROJECT --receipt
   tasks/context-v1` before use. The assignment index still has its existing
   256 KiB whole-input limit; the dispatched briefing has a separate 32 KiB
   default and a justified 64 KiB maximum. Neither is a token or billing limit.
4. Claim the task with its existing fields plus
   `context_receipt: "tasks/context-v1/CONTEXT_RECEIPT.json"`. Managed dispatch
   requires a current receipt under the bounded policy. `prepare-dispatch` and
   `record-dispatch` recheck exact packet, briefing and source pins. A receipt
   does not prove that the host actually sent only that briefing.
5. Send `TASK.md` once through the available host dispatcher. Keep mandatory
   system/workspace/security instructions. Request fresh context for new tasks
   when supported, and reuse a relevant running worker for corrections. Do not
   repeatedly attach the full conversation, complete HTML, inline images,
   all skills or tool logs. Return assigned artifacts plus concise findings and
   evidence references; never echo the entire artifact into chat.

The orchestrator retains full requirement coverage. Packets carry assigned
requirements and shared restrictions, with original evidence available through
specific context requests. Do not treat a missing excerpt as absent source logic.
Complete metric expressions, access restrictions and affected dependencies must
remain available. If they do not fit, split coherent work or explain an expansion;
never silently truncate evidence to satisfy a budget.

### Context request contract

`schema_version: 1`, `kind: "analyst_context_request"`, and:

| Field | Content |
| --- | --- |
| `packet` | Relative `path` and current `sha256` of the assigned task packet |
| `mode` | `initial` or `delta` |
| `summary` | Evidence-backed task briefing, at most 8 KiB; distinguish facts and inferences |
| `decisions`, `constraints` | Arrays of scoped text; include applicable shared rules |
| `stop_conditions` | Include the assignment packet's mandatory stop conditions |
| `evidence` | Entries with `id`, `path`, `sha256`, `classification`, `purpose`, ordered inclusive one-based `ranges`, and `review_original` boolean |
| `classification` | `public`, `internal` or `confidential`, covering the complete briefing |
| `disclosure` | `allowed_classifications` and `review_ref`; declared handling, not authorization |
| `shared_constraint_ids` | Required cross-role restriction IDs from the current intent |
| `max_packet_bytes`, `budget_reason` | Optional bounded expansion; reason required above 32 KiB |
| `delta` | For corrections: `baseline_receipt: {path, sha256}`, `changed_ids`, `open_findings`, `reason` |

The actual pinned baseline is supplied, not merely its hash. Revised source
evidence is independently pinned; historical baseline content is labeled as such.
Prepare a new bounded initial packet when a long correction history stops fitting.
Retain original evidence and all unresolved findings when compacting it.
Independent review requires relevant originals, not solely the builder's summary.

## Stable decisions and incremental review

The full candidate hash remains authoritative. Product choices and operational
ownership have separate continuity rules under the explicit review policy. Adding
a qualified owner can preserve unchanged A–E evidence; changing scope, source
requirements, selected visual treatment or policy cannot. Reviewer independence
and current responsibility readiness are always rechecked. Old user replies are
never rewritten to look like new approvals.

Use `review-policy --project PROJECT --request POLICY.json` to append an
`incremental-review-v1` adoption record. Request fields are `policy`, `mode`
(`observe` by default; `enforce` requires an explicit selection), `expected_tail_sha256`, and
`evidence: {policy_decision: "evidence/policy-decision.json"}`. Take the tail
from current stage status. Observation mode reports eligible reuse but still
requires ordinary reviews. Policy changes are local workflow decisions, not
native-write or dependency authorization. Historical journal entries remain.

Prepare a manifest with `review-manifest --project PROJECT --request INPUT.json`.
Retain the returned JSON at a new project-relative path and pass it as
`review_manifest` when freezing a candidate. The input has `dependencies`, each
with `id`, `kind`, `scopes`, `path`, and `freshness`; current file hashes and sizes
are added locally. Kinds include `artifact`, `context`, `data`, `runtime`, `access`
and `unknown`. Use sorted review scopes (`product_owner`, `qa`, `security`, `ui_ux`).
Freshness is `{mode: "immutable"|"until", checked_at: ISO8601, expires_at: ISO8601|null}`.
Data/runtime/access evidence requires an explicit observation window; there is
no universal TTL and no change to the user's app-data caching policy.

The manifest must account for the candidate artifacts and all required safety
context. Artifact changes always affect security, UI/UX and QA. Unknown impact, missing
dependencies, changed scope contracts or expired evidence require broader review.
The helper verifies declared pins and coverage; it does not infer semantic
dependencies or authenticate live observations.

Run `review-impact --project PROJECT` after freeze. For eligible source-review
reuse, `review-carry` accepts `scope`, `source_review_sha256`, `iteration_sha256`,
`candidate_sha256`, `expected_tail_sha256`, and `assessed_by`. The helper creates
current-candidate coverage with the original reviewer, outcome, basis, evidence
and origin. The caller cannot substitute a new pass. All four coverage dispositions
remain required; unobserved or requested changes remain unresolved. Current
candidate/dependency versions are rechecked while recording the event.

Conservative boundary: modular candidates can retain unaffected source reviews.
Use [deterministic assembly provenance](assembly-provenance.md) to retain exact
component/query/asset/runtime inputs and generate bounded correction evidence.
Its dependency comparison does not automatically narrow existing review scopes.
An arbitrary change to one large assembled HTML file generally requires broader
review. A generated envelope and unqualified assembly mapping are not proof that
only CSS changed. Rendered/native/human acceptance is never carried across changed
artifact bytes. Do not claim universal semantic diffing or host qualification.

## One preflight and bounded correction

`work-preflight --request REQUEST.json` accepts `action`, `packet`, `attempt_id`,
and/or `context_receipt`. It returns relevant blockers together without writing
or dispatching. This complements the guarded action's final checks; preflight
does not authorize it. Use existing staged commands for the required records,
not raw schema guessing or gate bypasses.

Consolidate compatible findings before a correction and use the existing
`review-work` correction reservation. Do not launch duplicate workers or turn
every review perspective into another agent. Independent creative/QA workers
must remain independent of their authors; preserve product-fit findings separately.

`work-blocker` records `{attempt_id,event_id,error_family,detail}`. A second
distinct failure event on the same input/output state stops redispatch until
relevant evidence changes. Replaying an event is idempotent. Renaming a task does
not reset the counter. Report one concrete evidence/decision gap and continue
unaffected work. Host cooperation is required to observe failures; no helper can
detect every out-of-band model loop. A stop is not permission to bypass a gate.

## Usage and qualification

`work-usage` records one immutable observation for a recorded invocation:
`attempt_id`, `observation_id`, `host_run_reference`, `context_mode`
(`fresh`, `inherited`, `unknown`), pinned `evidence: {path,sha256}`, and optional
`usage`, `elapsed_ms`, `host_instruction_bytes`. Usage may contain observed
`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`; unknown
values remain null. Use a unique invocation reference, not a reusable worker/chat identity. Host-reported values are not authenticated billing.

`efficiency-report --project PROJECT` reports task/dispatch/reuse counts, bounded
briefing bytes, correction expansions, blockers and available usage coverage.
It never converts bytes into tokens or dollars. Keep token categories separate
unless the provider's documented accounting supports combining them. Retain
baseline and optimized reports outside the repo with equivalent scope and quality
criteria; do not claim savings from a smaller prompt alone.

For each actual host, record requested versus observed context, model and effort,
resume behavior and usage availability. Keep the configured model. An unqualified
host remains unqualified; unsupported isolation does not waive independent QA.
Provider prompt caching is optional host behavior, not a dependency of this design.
No browser, live pilot, dependency activation or publication is implied here.

Release checks use original synthetic cases, not customer rehearsals. Compare
requirement coverage, numbers, visual ambition, accessibility, native observations
and acceptance separately from resource usage. New source-only tests prove local
workflow behavior; they do not establish native quality or a measured dollar saving.
