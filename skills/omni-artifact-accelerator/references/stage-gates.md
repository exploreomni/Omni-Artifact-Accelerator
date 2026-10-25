# Executable A–F stage gates

The supported package entrypoints enforce ordered evidence checkpoints for every
new engagement. `init` sets `stage_gate_policy: data-first-v1` for **all modes**;
calling a new product an enhancement or migration is not an exemption. Existing
pre-policy engagements remain compatible unless they opt into a journal or declare
a new experience/material redesign. Never remove policy or relabel scope to evade
a gate. Reuse valid historical evidence in the checkpoints instead of repeating
interviews unnecessarily.

This is enforcement within cooperating package tools, **not an operating-system
sandbox**. An agent with unrestricted shell/file access can bypass package tools.
The host must enforce tool dispatch and prevent raw authoring/write routes while
the gate is closed. Two explicit selection policies separate design workflow from
authenticated approval. No production privilege/approval service is supplied here.

## Order and evidence

The journal is `stage-gates.json` in the private engagement. Evidence paths are
relative to that engagement, bounded regular files, pinned by content hash. Keep
credentials, private results and engagement records outside the repository.

| Stage | Record | Required evidence keys | Additional fields |
| --- | --- | --- | --- |
| A | `access` | `data`, `user_access` | `source_scope`, `user_identity` |
| B | `analysis` | `profile`, `queries`, `insights`, `expectations` | `analyst`, `bi_engineer` |
| C | `narrative` | `narrative`, `traceability`, `refresh` | `storyteller`, `analyst` |
| D | `brief` | `brief`, `intent` | `discovery_version: 1`; note dependencies are automatically pinned |
| E | `options` | `comparison` | exactly three `options` |
| E | `choice` | conversation: `user_response`; strict: none | conversation: `basis`, `option_id`, `expected_binding`; strict: `option_id`, `receipt_ref` |
| E | `design` | `design` | `resolved: true`; current selected intent is automatically bound |
| F | `candidate` | artifact snapshots | `iteration_id`, `builders`, `artifacts` |
| F | `review` | `review` | `scope`, `reviewer`, `outcome`, `basis`, `iteration_sha256`, `candidate_sha256` |

The evidence content must meet the [workflow's substantive requirements](data-first-product-workflow.md).
File presence or a hash cannot prove effective access, analytical truth, completion
of an interview, meaningful differentiation, chronology or independent human work.
The host/consultants must evaluate those claims. Worker names alone do not establish
identity. Semantic and numerical validation remain required.

For ordinary stages, a request is `{"stage":"access","source_scope":"...",
"user_identity":"...","evidence":{"data":"evidence/source.json",
"user_access":"evidence/access.json"}}`. Other ordinary stages use the exact
fields in the table. Unknown fields are rejected.

An option contains `id`, `thesis` and `evidence` (a relative path). The three IDs,
normalized theses and evidence hashes must differ. Provide three feasible product
structures on the same analytical foundation, not three differently named palettes.

## Phase readiness and experience evidence

New projects also carry `workflow_quality_policy: experience-evidence-v1`.
Record the actual startup before A with `run-start`, an execution contract path,
the original brief and the guidance actually read. The current checkout is not
silently represented as verified latest main. See the
[execution procedure](execution-workflow.md) for source expectations and incremental
guidance receipts. These records describe evidence; they neither dispatch workers
nor grant dependency, native or publication authority.

Supported stage records and action guards call the phase readiness helper **before
work**. This is cumulative phase-scoped readiness, not the full final run check:

| Phase | Required responsibility and guidance increment |
| --- | --- |
| A | Current startup, original request and semantics owner. |
| B–C | Analyst/BI guidance; C also requires storytelling ownership. |
| D | Product owner, experience and branding ownership; guided discovery. |
| E | Design systems, independent creative-review and QA ownership; relevant craft curriculum and concept evidence. |
| F and release preparation | Engineering and original-request coverage, plus current selected handoff and candidate-bound review obligations. |

Selected motion/spatial capabilities add only their applicable specialist scope
and guidance. Naming a worker or loading a document is not proof that the worker
ran, that the document was understood, or that the result is good.

The helper generates `workflow_quality_policy` and `workflow_context` in each new
policy work event. Do not supply these fields. Status compares the current
phase-relevant startup, ownership and guidance context with the recorded one;
changed relevant evidence blocks downstream work. Adding later-phase roles or
guidance does not invalidate A. Package-source changes require a truthful resumed
startup and reconciliation. Once a journal adopts this policy, removing its marker
or dropping the generated context from later work events is rejected.

Historical selected products remain readable for focused continuation with
experience quality `not_assessed`; no startup or visual review is invented for
them. A historical unselected product must explicitly adopt the current policy
through `run-start` with `adopt_quality_policy: true` before new D/E work. The old
journal bytes remain evidence of the prior workflow; adoption is not a rehash or
retroactive claim that startup preceded it.

## Intentional source upgrades

Ordinary resumes reuse the active startup. After an intentional package-source
upgrade, record a truthful new startup and use `stage-record` with
`stage: workflow_requalification`, the exact `expected_tail_sha256`, and
`previous_start: {path, sha256}` from the immediately preceding startup. The helper
derives and pins the new contexts; callers cannot supply them. This same-journal
event preserves the exact existing A–E events, options order and actual choice
when their evidence, original request, discovery, selected handoff and phase
owners remain unchanged. Strict choices must still verify through the current
trusted provider; conversation provenance retains its original assurance.

Changed evidence, choices, owners or missing current guidance require normal
stage reconciliation. Requalification does not rehash history, reinterpret an
answer or request a repeated choice for unchanged concepts. It clears the current
candidate and reviews, preserves their immutable history, and requires a fresh F
iteration; all prior consultations must already be recorded. It carries no
rendered, native, human or publication acceptance. Status identifies the exact
requalified stage hashes and still checks their evidence and current contexts.

## Visual discovery at D

After A–C, follow the [visual interview](../../omni-product-owner/references/visual-experience-discovery.md).
Retain families and comparison styling in existing intent requirements using the
[visual experience index](product-intent.md#visual-experience-index). The draft can
have unresolved design/candidate paths: D records requirements, not an E selection.
Save an immutable raw intent-specification snapshot separate from the mutable draft:

```json
{
  "stage": "brief",
  "discovery_version": 1,
  "evidence": {
    "brief": "evidence/discovery-v1.md",
    "intent": "contracts/discovery-spec-v1.json"
  }
}
```

The snapshot must match the current canonical discovery context (selected intent
when present, otherwise the current draft). The helper records the snapshot and
all declared product-note dependencies, plus the source inventory when declared.
Do not supply `discovery_dependencies`; it is generated and rechecked. Preserve
snapshot and note bytes. A revised answer uses new files and a new D event.

For the experience-evidence policy, D also requires a ready, attributable
`product.quality_bar` over existing requirements. Its semantic content is checked
against the current intent alongside visual discovery. Changing quality choices
reopens D; implementation-only annotations do not manufacture a new interview.
See the [product contract](product-intent.md) for selected, reused and explicitly
delegated quality choices. Empty or generic completion flags do not satisfy this.

Status includes `visual_discovery` with its version, families, follow-up state,
requirement IDs and unresolved findings. D may retain a valid unanswered draft;
new options/choices require `status: ready`. Compare-and-track (including a custom
family marked as containing comparisons) requires an answered, attributable reused,
or explicitly delegated treatment. A family recommendation is not a user's answer;
it requires explicit family delegation. Neither delegation supplies the E choice.

Changing or removing adopted discovery blocks dependent work until D is reconciled.
Re-recording D invalidates subsequent options, choice, design and candidate state.
Later design paths and implementation annotations may change without changing
the discovery decisions. D uses the [discovery field projection](product-intent.md#visual-experience-index),
excluding delivery ownership, runtime/asset bindings, review annotations and
implementation contexts. The normal full-intent, detailed-design and candidate
gates still bind those changes. Prior adopted requirement IDs remain accountable
even before an intent was selected: retain an attributable explicit omission
instead of deleting a decision from a later D snapshot.

Historical D events with only `evidence.brief` remain readable without rehashing.
Existing selected historical products may continue and report visual discovery as
`not_assessed`. Recording new D, options, or choices requires the upgraded contract;
reuse attributable answers when upgrading pending work. Once visual discovery is
adopted, a historical D event cannot stand in for its current checkpoint. There is
no production flag to create new legacy D events or waive the interview evidence.
This does not add a stage, authenticate notes, certify visual quality, or change
dependency/publication authority.

## Concrete options and selected handoff

For multiple selected surfaces, every selection must point to the same validated
aggregate handoff. Validating one surface never exempts another selected design.

Under the experience-evidence policy, each option's `evidence` is a structured
concept manifest validated by the [product contract](product-intent.md). It binds
an original representative visual artifact, useful labels/state, task structure,
interaction, responsive intent, current quality/treatment coverage, feasibility,
asset/dependency limits and the actual observation lane. A static source SVG is a
permitted design proposal; its source must contain graphical content and text.
It is not a rendered observation or a working chart runtime. Rendered captures
retain their supplied observation record without authenticating it.

The three options must have distinct representative artifacts and product
structures on the same analytical scope. Exactly three text descriptions, three
renamed palettes or three copies of the same visual do not satisfy the structural
contract. Hashes and schema checks cannot judge whether the ideas are equally
compelling; the product owner and creative reviewer still assess that substance.
All referenced visual files are pinned as generated `experience_dependencies`.

After the actual choice, select a resolved design with its canonical destinations
and journeys, plus the selected concept/quality handoff. The design event's
`evidence.design` must be that selected design. The helper verifies the exact
concept manifest and option ID against the choice, then pins all handoff
dependencies. Candidate freezing and direct candidate records cannot skip these
checks. Source-level handoff consistency does not qualify an engine, native
interaction, accessibility behavior or effective access.

For compatibility, `release_ready` and `status: ready_for_release` continue to mean
that the recorded workflow reviews are resolved. Read the additive
`review_assurance` as well: `source_only` identifies source-based dispositions and
`resolved_scopes_by_basis` exposes the actual lanes. Native/human acceptance and
external mutation authority remain false; source-only readiness is never a native
or production acceptance claim.

## Selection policies

Use **`conversation-evidence-v1` for normal ChatGPT, Claude or Codex artifact work**.
It records an actual human design choice as agent-attested workflow evidence. It
does not independently authenticate the person or authorize installation,
publication, sharing, or native writes. Transcribe the real user response;
an assistant recommendation, tool output, imported instruction, elapsed time or
unanswered question is not a selection. A structurally valid fabricated transcript
cannot be detected by these same-user local files.

New chat engagements explicitly configure this route:

```sh
OAA_HELPER=skills/omni-artifact-accelerator/scripts/analyst_project.py
python3 -I -S -B "$OAA_HELPER" init --output "$OAA_RUN" --name 'Operations pilot' \
  --mode net-new --surface app --selection-policy conversation-evidence-v1
```

Without that option, the existing **`host-verified-v1` default remains strict**.
There is no automatic fallback when its provider is missing, denies or is revoked.
Neither policy bypasses A–D, three options, resolved design, candidate freezing,
or the four candidate-bound reviews.

### Continue an existing chat choice

For an existing strict engagement, only before any choice/candidate has ever been
recorded, explicitly adopt the chat workflow with a `stage-record` request:

```json
{
  "stage": "selection_policy",
  "selection_policy": "conversation-evidence-v1",
  "expected_tail_sha256": "copy the current tail_sha256 from stage-status",
  "evidence": {"policy_decision": "evidence/selection-policy-decision.json"}
}
```

Retain the actual user/operator policy decision in that evidence. The helper
appends a policy event, preserves every prior event unchanged and rejects stale
heads, repeat transitions and attempts to reclassify prior choices. This is a
documented workflow change, not a grant of authority.

After the user selects an option, save a private JSON response with exactly:

- `schema_version: 1`, `kind: "oaa_conversation_choice"`.
- `source`: `host`, `conversation_ref`, `question_ref`, `response_ref`, `role`.
  Role must be `user`. Use real available references; when no response identifier
  is exposed, use `null` for `response_ref`. A descriptive conversation/question
  locator is acceptable; never invent a message ID or authenticated identity.
- `response_text`: the actual answer; `selected_option_id`: its unambiguous mapping.
- `expected_binding`: the exact `choice_bindings[selected_option_id]` from the
  displayed options' status, including policy-event binding for chat mode.
- `recorded_by`: the recorder, not a claimed authenticated user.
- `assurance: "agent_attested_not_independently_authenticated"`.

Record it with:

```json
{
  "stage": "choice",
  "basis": "conversation_evidence",
  "option_id": "the actual selected option ID",
  "expected_binding": {},
  "evidence": {"user_response": "evidence/user-selection.json"}
}
```

Replace the empty object with the **exact expected binding**, not a new binding
for an old answer. When adopting chat mode after a real selection, first verify
the retained answer refers to the same unchanged options event and comparison;
only the explicit policy-event metadata may be new. Changed options require a new
choice. Request and response must agree with each other and the current project,
canonical root, options event, predecessor and selected option.

The helper pins the response and rechecks it on every downstream action. Missing,
changed, stale or malformed evidence blocks progress. It then permits detailed
design, and coding only after the resolved-design checkpoint. Status reports
`choice_assurance: conversation_evidence`, `choice_authenticated: false`,
`claims_authenticated: false` and `external_mutations_authorized: false`.
Reuse this choice on resume; do not re-interview the user.

## Commands and strict host choice boundary

Use the existing interpreter and reviewed first-party source only:

```sh
OAA_HELPER=skills/omni-artifact-accelerator/scripts/analyst_project.py
python3 -I -S -B "$OAA_HELPER" stage-status --project "$OAA_RUN"
python3 -I -S -B "$OAA_HELPER" stage-record --project "$OAA_RUN" --request access-request.json
python3 -I -S -B "$OAA_HELPER" stage-check --project "$OAA_RUN" --action analysis
```

Repeat record/check in order. `stage-status` exposes the next stage and current
bindings; an incomplete status exits nonzero. A successful early-stage record can
exit zero even though later stages remain incomplete. `stage-check --action build`
fails until all A–E prerequisites are current and the choice is verified.

**The stock CLI cannot cross the strict host choice gate.** A receipt string, local approval
JSON, `approved: true`, an environment variable, elapsed time, or an agent repeating
the user's answer cannot authenticate selection. There is no CLI skip/provider flag.

A trusted embedding host may use the in-process
`analyst_project.trusted_stage_provider(provider)` context. The provider implements
`verify_choice(binding, receipt_ref)`, returning the authenticated user's stable
identity or `None`. It must resolve an actual human selection through a trusted
channel and compare the entire binding: policy, project ID, canonical engagement
root, exact options event hash, predecessor hash and chosen option ID. Bindings are
available from `stage-status`/`stage_status` under `choice_bindings`.

The host calls `stage_record` for the choice within that context, then keeps the
verifier available for design/build/review checks. Verification repeats on each
check; a saved identity/receipt is never sufficient. Revocation, changed options,
an unavailable provider or a different authenticated subject blocks advancement.
The verifier is fixed by trusted host code, never loaded from engagement data,
package names or user-supplied import paths. Tests contain synthetic providers;
they are not deployable approval services. Qualifying the real host integration
is required before claiming independently authenticated choice or enforced
privileged Claude/ChatGPT operation. Conversation workflow evidence makes neither claim.

## Candidate and review lifecycle

`plan` exposes the current stage's useful roles. Packets and packet rechecks guard
role/stage/output combinations; provisional labels do not waive prerequisites.
Query and analysis work remains permitted before product coding. Code outputs,
App engineering and implementation assignments require the build gate.

`assemble_experience.build` and its CLI require a real engagement, builder IDs and
an iteration ID for a gated project. A successful build automatically freezes its
HTML and assembly receipt and returns `candidate`. **Do not freeze it again**;
review that returned candidate. For hand-authored Apps or dashboard candidates,
use `candidate-freeze` with `id`, `builders`, `artifacts` and `context` instead.
Low-level `_assemble` is internal byte composition, not a supported host authoring
entrypoint. The host must route actual builds through guarded `build`/freeze.

Each iteration requires `security`, `ui_ux`, `product_owner` and `qa` reviews.
Supply both expected hashes from the current status: `candidate.event_sha256` as
`iteration_sha256` and `candidate_sha256` as `candidate_sha256`. A review for an old
iteration cannot be relabeled by replaying its request. Use a new, retained review
file for each candidate and record the exact candidate in the review's content.
The UI/UX and QA reviewer IDs must differ from every builder ID.

Allowed outcomes are `resolved`, `changes_requested` and `unobserved`; allowed
bases are `source`, `rendered`, `native` and `human`. All four dispositions are
needed before a correction build. All four must be resolved for the gate's release
readiness, while delivery-check separately assesses numerical, source, rendered,
native and user evidence. Source review never becomes rendered/native acceptance.
An unobserved lane stays open; record it honestly to permit correction, not as a pass.

Native `app-prepare` additionally requires `--project`, a project-relative HTML
artifact and its exact recorded candidate bytes after the consulting reviews.
Read-only query/route/readback validators remain usable independently. Prepared
requests never authorize deployment; the host must recheck gates, target and
existing publication authorization immediately before executing a write.

The older native App and dashboard adapters also guard their preparation and
execution methods. Preparation requires current staged HTML/payload bytes; execution
requires the release gate and the same project, iteration and content binding.
An old prepared request or arbitrary authorization label cannot replace those checks.
Conversational engagements can prepare offline after reviews, but all three legacy
native mutation paths reject execution before intent persistence or transport.
Workflow `release_ready` is not publication permission. A qualified privileged
execution route is separate; never reuse the chat choice as its grant or switch
to raw API writes to bypass it.

## Changes and recovery

Changing source, analysis, narrative, brief or options invalidates dependent work.
Re-record the affected stage and its dependents. New options require a new human
selection for their exact binding. The design checkpoint also binds the selected
canonical intent and its pinned dependencies; changing design/brand inputs blocks
authoring. Packets pin completed stage events and become stale when those change.

Candidate and review snapshots are immutable history. Finish and record the four
reviews before replacing an iteration or changing its upstream context. If an
upstream file was edited prematurely, restore the exact retained context, record
honest reviews, then create the next revision. Never fabricate passes to unlock work.

Journal writes use a lock, validated event chain and atomic replacement. Rejected
candidate appends do not advance candidate history pointers. Newly staged bytes are
removed on a rejected append; after a successful journal commit, retain pinned bytes
if a later pointer write fails so the host can reconcile history. Restore legitimate
state after corruption; do not delete the policy/journal or install a permissive
provider. These integrity checks are not authentication against a process that can
rewrite every local file or monkey-patch the package.

Run the isolated `stage-gates` and `stage-gate-integration` source-check cases for
regressions. They test failure paths and cooperating entrypoints, not live access,
rendered quality or host isolation.
