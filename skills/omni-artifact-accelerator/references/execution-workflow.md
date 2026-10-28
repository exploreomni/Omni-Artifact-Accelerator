# Enter, build and assess an artifact engagement

Use for substantial new design, redesign and migration. This procedure connects
the existing project, selected intent, specialist assignments and design review.

For net-new products and explicit product reconception, the
[data-first A–F workflow](data-first-product-workflow.md) governs execution order.
Record startup first, then verify source/user access, analyze governed queries and
complete the reusable narrative before artifact discovery. Present three viable
options and obtain the user's selection before detailed design/full implementation.
The [executable stage gates](stage-gates.md) enforce that sequence at supported
entrypoints. For ordinary chat, initialize with `--selection-policy conversation-evidence-v1`
and record the actual reply against the exact option set. Existing strict host
engagements never fall back automatically. This is workflow evidence, not
independently authenticated approval; hosts must also guard
raw authoring routes, and local evidence does not authenticate effective access.
It adds no universal layout, approval interview or permanent agent team. Focused
repairs retain their current engagement and inspect only affected obligations.

## Select the actual host route

| Route | Entry | Evidence and limitations |
| --- | --- | --- |
| Repository in Claude Code | Read root CLAUDE.md, then this skill | Record working-tree bytes, host tools and constraints; the file is guidance, not enforcement. |
| Repository in Codex | Read root AGENTS.md, then this skill | Same portable contracts; no assumption that a plan dispatched specialists. |
| Approved installed skills | Invoke the orchestrator from the installed location | Read-only compare with the selected source when available. Cached host loading remains unproven. |
| Claude/ChatGPT connected chat or repository link | Explicitly retrieve the orchestrator and applicable sibling guidance | Confirm tool access and consumed revision. No local file auto-loading or hosted MCP provisioning is implied. |

Use only already authorized tools and original helpers. An inaccessible repository
is a startup gap; do not improvise a design-complete claim from engineering snippets.
If local helper execution is unavailable, retain the same records as attachments
and label checks `not_run`. Do not install a runtime or connector to close the gap.
Gated implementation requires a host that can execute the checks and retain the
actual choice through the explicit conversation or strict verification route.
Attachments and prose are not a bypass for an unrun check.

For a repository-only blind trial, use only the selected checkout and supplied
inputs. Do not compare installed copies or read previous apps, outputs or memory.
For each supported host, qualify actual behavior separately. No bootstrap file,
boolean or self-authored receipt can grant authority or govern unrelated MCP calls.

## Record startup and ownership

Initialize a new engagement with `analyst_project.py init`, or resume the existing
one. New projects record `workflow_quality_policy: experience-evidence-v1`; its
phase checks complement the existing A–F journal rather than creating a second
workflow. Preserve the original
request verbatim in `inputs/brief.txt`, redacting credentials before saving. Recover
existing answers; use one material question batch where feasible. Resolve routine
design choices internally. Create `contracts/execution.json` with the responsibilities
known so far. Read the guidance needed for the first phase, then record startup
**before the first new artifact stage**:

```json
{
  "id": "first-run",
  "source_mode": "repository_only",
  "host": {
    "name": "Actual host name",
    "execution_mode": "inline",
    "tools": ["Describe the actually available approved tools"],
    "constraints": ["CLI/API only; no dependency activation"]
  },
  "entrypoint": "Explicit repository orchestrator invocation",
  "brief": "inputs/brief.txt",
  "execution": "contracts/execution.json",
  "source_expectation": {"kind": "current_checkout"},
  "loaded_guidance": [
    "skills/omni-artifact-accelerator/SKILL.md",
    "skills/omni-data-analyst/SKILL.md"
  ]
}
```

Use `installed` only from the installed helper (guidance paths then omit `skills/`).
`connected_reference` records a locally available package used from a connected
host; it does not fetch or prove remote loading. Record only guidance actually read.
Append relevant guidance as the work reaches each phase; do not predeclare unread
files to satisfy a check. Host execution modes
are `inline`, `delegated`, or `instruction_guided`; actual worker invocation still
uses [scoped task records](task-routing.md).

For substantial product decisions, follow the [product-intent front door](product-intent.md)
and record the product-owner plus assigned creative-review guidance actually read.
Notes stay in private engagement inputs/evidence. Recover existing answers before
interviewing; a focused repair does not restart discovery. Select the canonical
intent, then use `product-brief` and `product-check` for its readable North Star.

For query-backed Apps, sequence [cache/refresh discovery](../../omni-product-owner/references/data-refresh-policy.md)
with that intake: A–C supplies source cadence and claim constraints; D captures the
actual cache, refresh and optional expiry answer; E resolves the chosen behavior;
F implements and reviews the same requirement. Record an explicit no-custom-policy
answer rather than inventing a timeout. Reuse current answers for focused repairs.

```sh
python3 -I -S -B "$OAA_HELPER" run-start --project "$OAA_RUN" --request startup.json
```

The immutable `evidence/run-first-run.json` includes source hashes, Git identity
when available, reported reads, constraints and the original-request hash. Keep
the selected checkout stable during a trial; changing the package requires a new
run ID, preserving the prior record. The current project points to that startup;
resumes retain its predecessor and stage-tail reference. A first startup recorded
after work is labeled late and cannot retrospectively establish timely entry.
Older engagements may explicitly adopt the quality policy through
`adopt_quality_policy:true` in a new startup request; retained records keep their
historical interpretation. Do not rewrite the old journal or restart discovery
merely to resume a selected product. Startup does not compare installed copies in
repository mode, run agents, authenticate host claims or confer publication rights.

An ordinary resume reuses the active startup. After an intentional source change,
record a new startup and use the [same-journal requalification procedure](stage-gates.md)
to revalidate A–E with current helpers. It can preserve the exact original options
and actual choice only while their evidence, analytical scope, quality decisions,
original request and applicable ownership remain unchanged. It does not rewrite
the user reply or mint another selection. Changed choice inputs reopen the affected
stages. F reviews and rendered/native/human passes never carry forward merely
because requalification succeeded.

Select the source expectation that matches the actual request:

| `source_expectation` | Required evidence |
| --- | --- |
| `{"kind":"current_checkout"}` | Records the actual working-tree manifest, including local changes. It makes no latest-release claim. |
| `{"kind":"pinned_revision","revision":"<full revision>"}` | HEAD must equal the requested full revision and the working checkout must be clean. |
| `{"kind":"latest_main","revision":"<full revision>","verification_path":"evidence/source-check-entry.json"}` | A matching source-check receipt from this project/package, captured within ten minutes before startup, plus the matching clean checkout. |

When a latest-main check is requested and read-only network access is permitted,
`source-check --request source-check.json` takes `{"id":"entry"}`. It reads
`refs/heads/main` from the checkout's configured HTTPS `origin` and writes the
receipt; it does not fetch, reset, install, activate code or contact an Omni tenant.
An origin URL containing credentials is rejected. Keep the receipt and any private
repository identity inside the engagement. If verification is unavailable or the
checkout differs, report that gap and obtain/use the appropriate authorized source;
do not quietly relabel the current checkout as latest. A valid startup pins the
verified source for the run; it does not expire every ten minutes or follow later
remote changes automatically. These are local workflow records, not authenticated
supply-chain attestations or a security boundary against their author.

After reading more guidance, append a receipt with `run-guidance`:

```json
{"id":"analysis-reading","loaded_guidance":[
  "skills/omni-bi-engineer/SKILL.md"
]}
```

Receipts pin files from the startup manifest and link to the active run and prior
receipt. They preserve reported read provenance, not proof of comprehension or
dispatch. Avoid retaining credentials, unnecessary customer rows or personal data
in briefs, receipts or review evidence.

Use `contracts/execution.json` only for ownership and original-request review.
Keep design choices in the existing selected intent and resolved design. Its shape:

```json
{
  "responsibilities": {
    "experience": {"role":"app-designer","worker":"lead","mode":"inline","rationale":"Owns task-fit composition and critique"},
    "brand": {"role":"branding","worker":"lead","mode":"inline","rationale":"Reuses selected identity"},
    "semantics": {"role":"data-analyst","worker":"lead","mode":"inline","rationale":"Owns populations and expected results"},
    "engineering": {"role":"app-engineer","worker":"lead","mode":"inline","rationale":"Implements the selected native contract"},
    "verification": {"role":"qa-analyst","worker":"reviewer","mode":"delegated","rationale":"Independent review of original request and output"},
    "design_systems": {"role":"design-systems","worker":"lead","mode":"inline","rationale":"Defines task-fit composition, type and control rules for this new experience"},
    "storytelling": {"role":"data-storyteller","worker":"analyst","mode":"inline","rationale":"Creates the traceable, refresh-safe narrative after query analysis and before artifact design"}
  },
  "request_review": {
    "reviewer":"reviewer",
    "brief_sha256":"replace with the retained brief hash",
    "requirement_ids":["use actual selected requirement IDs"],
    "evidence_path":"evidence/original-request-review.md"
  }
}
```

These are illustrative choices, not default dispositions. Applicable insight or
control work must have an owner, possibly the same worker wearing another role.
For dashboards, use dashboard-designer and BI engineering. The verification worker
must differ from the builder for independent claims. No delegation tool means
independent review pending, not an invented worker identity.

When the selected intent has product context with scope other than `focused_repair`,
add `product_intent` and `creative_review` to those responsibilities. For example:

```json
{
  "product_intent": {"role":"product-owner","worker":"lead","mode":"inline","rationale":"Recovers answers and preserves prioritized product intent"},
  "creative_review": {"role":"design-systems","worker":"reviewer","mode":"delegated","rationale":"Independently critiques the experience promise on the exact candidate"}
}
```

These are additions inside `responsibilities`, not a replacement execution file.
Creative review may use `app-designer`, `dashboard-designer` or `design-systems`;
its actual worker must differ from engineering and the originating experience owner.
Product fit, creative craft and correctness remain separate findings. A suitable
independent worker can cover both review disciplines. Historical seven-role records
remain readable. For work under the quality policy, the applicable phase requires
its named duties; a `not_required` rationale cannot waive them. A focused repair
retains its original scope and existing applicable evidence rather than forcing a
new engagement or three new concepts.

Optional specialist ownership belongs in a sibling `specialists` object, not an
invented core responsibility. For example, a selected spatial task may use:

```json
{"specialists":{"geometry":{"role":"3d-modeler","worker":"actual-worker",
  "mode":"delegated","rationale":"Authors the selected original geometry proposal",
  "requirement_ids":["inspect-object"]}}}
```

Use an existing package role, actual worker, `inline`/`delegated`/`not_required`
mode, rationale and existing requirement IDs. Active slots require that role's
guidance in the run's actual-read inventory. These slots do not replace the core
experience/engineering/verification owners, prove dispatch or require 3D.

The reviewer compares the original request against every material requirement,
including deferred/omitted work and the full question→population→grain→denominator
mapping. Preserve evidence and explain any gap. All recorded requirement IDs must
be accounted for, but matching IDs cannot discover a requirement omitted from both
records. Never fix a result cap by quietly narrowing the requested population.

Use `phase-check --request phase.json` with `{"action":"analysis"}` before
the applicable action. The phase check assesses current startup/source, declared
responsibilities and guidance, without requiring later design or build records.
The A–F stage gate remains responsible for predecessor order and actual choice.
Do not use the full `run-check` as an early A/D gate: it also needs implementation
readiness and would create a circular requirement.

Responsibilities accumulate with the phase: semantics for access/analysis,
storytelling for narrative, product intent/experience/brand for discovery,
design systems/creative review/verification for concepts, and engineering plus
original-request review for the candidate. Conditional selected capabilities add
their relevant guidance and scoped specialists. The returned findings identify
missing reads or owners. This is scope-aware responsibility routing, not a command
to create another agent or a license to load a renderer. Several duties may share
one worker when the independent review requirements permit it.

Carry the refresh-policy requirement through the canonical intent/North Star and
existing worker packets: BI owns qualified cache controls and source-time evidence,
the designer owns refresh/recovery presentation, engineering owns selected triggers,
and QA owns policy-specific observations. Do not create a separate policy ledger
or let an example timer become a specialist's default.

Run `run-check` with a request containing `run` and `execution` paths once its
implementation-readiness prerequisites exist. It checks
current package/brief bytes, declared role guidance, ownership, original-request
review presence, enabled product context and existing `experience-check` coverage. Exit 1 means incomplete;
exit 2 means invalid input. Independent provisional work remains possible.

## Qualify and build one journey

**Inventory usable source capabilities before final destination selection.** Begin
with the requested questions and experience promise, then inspect the relevant
available sources beyond the first saved query. Do not equate one existing query
with the intended product scope. Record populations/eras, grains, supported depth,
missingness and constraints; distinguish observed source evidence from an inference.
Preserve useful task depth and explain expansions or exclusions before freezing the
destination scope. An inventory is bounded evidence, not proof that every source
has been discovered.

`source-inventory --project "$OAA_RUN" --request inventory.json` accepts this shape:

```json
{
  "id":"qualification-v1",
  "inputs":["evidence/source-profile.json"],
  "scope_rationale":"Compare periods and inspect observations; unavailable forecasts remain a gap.",
  "capabilities":[{
    "id":"collection-demand", "requirement_ids":["investigate"],
    "question":"Which collection changed and which observations explain it?",
    "source_refs":["evidence/source-profile.json#collections"],
    "population":"Supplied observations for the recorded periods", "grain":"Collection and period",
    "available_depth":["period comparison","exact observations"],
    "selected_depth":["period comparison","exact observations"], "disposition":"selected",
    "rationale":"Comparison and exact evidence serve the original decision.",
    "remaining_gap":"Native completeness has not been observed."
  }]
}
```

All commands here use `python3 -I -S -B "$OAA_HELPER"`. Capability dispositions
are `selected`, `unsupported` or `deferred`. Selected depth must be a nonempty
subset of available depth; other dispositions have empty selected depth and retain
their reason/gap. Unsupported evidence may name an inspected contract or failed
qualification rather than nonexistent results. Keep actual customer data outside
the package. Store a minimal source profile; no credentials or unrelated data.

The command writes a new `evidence/source-capabilities-<id>.json`, pinning its
inputs and the intent current at capture. Reference that path as
`product.source_inventory_path` in the next canonical intent selection. This
documents the sequence without certifying when a person actually made decisions.
The intent pins the inventory; checks also recheck its source inputs. Changed or
invalid evidence cannot claim readiness. Unsupported/deferred capabilities linked
to active requirements remain gaps unless an optional `alternative_id` names a
selected capability covering those same requirement IDs. Use that link when the
selected alternative preserves the outcome: keep the unavailable method and its
remaining difference visible, without turning a rejected implementation option
into an approval wait. The link declares a scope choice, not user acceptance or
proof of equivalent quality; unresolved outcome gaps must remain separate rows.
Legacy records and small focused repairs do
not require a new inventory; retained inventory still must be current. An existing
inventory cannot silently disappear from later intent versions.

Use the [native data-input procedure](../../omni-app-engineer/references/native-data-input.md)
before making the full design depend on a query. Keep connection/database/catalog,
metadata, population and NULL behavior explicit. Query exports and reconstructed
callbacks are different evidence. Reuse governed definitions; send actual missing
semantics through the existing DMA handoff, not an unnecessary warehouse rebuild.

The [first-delivery workflow](first-delivery.md) and [experience brief](../../omni-design-systems/references/experience-brief.md)
own design decisions. New products require stage E's three options and user choice;
direct selection is reserved for focused work or an already selected product. Preserve
brand authorization, first/return use, dominant evidence, control states, responsive
width **and height**, and useful detail/return. Review the complete first journey,
then every consequential destination. No fixed KPI count, tabs, animation, imagery,
3D is required. New products require exactly three options; their content is not
a fixed template. Each uses the same accepted analytical scope and quality bar,
with a representative visual and traceable quality coverage in its versioned
concept manifest. Do not make one option the only complete or ambitious offer.
Use the [current concept and handoff schema](stage-gates.md), retaining actual
user selection before detailed implementation. Original static SVG specimens are
the source-only route; actual PNG/JPEG captures need their observation evidence.
Neither structural validation nor three prose pitches establish rendered craft.

Make the first journey representative of the ambition, not just a thin technical
path. Preserve defining brand/interaction qualities and useful evidence. When a
method is unsupported, record its preserved outcome, feasible alternative and
remaining gap; do not let feasibility silently redefine the requested experience.

The original assembler automatically stores exact first HTML bytes and each changed
assembly under `evidence/assembled-history/` before review. Gated assembler builds
also freeze the candidate automatically; use their returned `candidate` path.
For hand-authored candidates, run `candidate-freeze` immediately after the first
candidate, before fixes, then again for each reviewed revision. All four reviews
must be recorded before the next build/freeze:

```json
{
  "id":"initial",
  "builders":["actual-engineer-id"],
  "artifacts":["deliverables/app.html"],
  "context":["evidence/run-first-run.json","contracts/execution.json",
    "evidence/original-request-review.md","contracts/queries.json","contracts/runtime.json"]
}
```

List all material query/model/settings/target dependencies explicitly. Selected
intent files and current phase evidence are added automatically for quality-policy
work. Keep execution ownership, guidance and original-request review current before
freezing; do not add missing context after review and pretend it was inspected.
The command creates new, never-overwritten
candidate records and copies exact artifact bytes. Hash history is tamper-evident
when checked, not immutable storage or proof that no earlier candidate existed.

For a required companion such as an App create specification, include its path in
`artifacts` and in the optional `supporting_artifacts` list. Supporting paths must
be a distinct proper subset of the frozen artifacts; the remaining primary set
must match the selected surface candidates exactly. A selected App HTML path cannot
be relabeled supporting to hide it from coverage. Supporting bytes remain fully
frozen, hash-pinned and covered by the candidate reviews and freshness checks;
this distinction does not exempt create metadata, queries or settings from review.
Historical candidates without roles keep their original primary-only interpretation.
The first assembly may precede selecting its newly produced artifact bytes. It can
be frozen as a provisional candidate, but it cannot pass delivery coverage or new
App creation preparation until the actual App artifact is bound into selected
intent and its current design/candidate reviews are complete. This does not reopen
the user's product-option choice or permit coding before that choice.

## Assess delivery without upgrading claims

Use existing case-bound design review and independent numerical expectations.
Prepare a delivery evidence file with `candidate_sha256` (the frozen candidate
JSON hash) and `lanes`. Account for `source`, `synthetic`, `numerical`, `native`,
`rendered`, `access`, `publication`, and `human`. Each lane has:

```json
{
  "status":"not_run",
  "method":"",
  "observer":"",
  "bindings":{},
  "reason":"Native rendering was unavailable under the selected tool constraints"
}
```

Avoid retyping the lane boilerplate. `delivery-evidence-template` takes
`{"candidate":"evidence/candidate-history/final/candidate.json","output":"evidence/delivery-v1.json"}`
as its request. It checks the current selection and retained candidate bytes and
writes a new evidence file with every lane `not_run`. Replace only observations
actually obtained, supplying their method, observer, bindings and limitations.
The generated file is a recording aid, never a pass receipt.

Statuses: `reported_pass`, `failed`, `not_run`, `not_applicable`. A reported pass
requires an actual observer, a nonempty map of engagement evidence paths to their
SHA-256 hashes, and the lane-specific method:

| Lane | Method |
| --- | --- |
| source | source_review |
| synthetic | constructed_fixture |
| numerical | independent_reconciliation |
| native | native_observation |
| rendered | rendered_observation |
| access | principal_observation |
| publication | exact_readback |
| human | attributable_acceptance |

Retain actual target/principal/observation context inside linked evidence; omit
credentials. Exact readback must reconcile HTML, named queries, workbook model,
settings and destination. A rendered observation includes applicable screens,
sizes and states; interactions require actual exercise. A fetch timestamp is not
source freshness. A simulated reviewer is not a human participant. An exclusion
needs task-specific rationale; rendered quality cannot be excluded to claim polish.

```json
{
  "run":"evidence/run-first-run.json",
  "execution":"contracts/execution.json",
  "candidate":"evidence/candidate-history/final/candidate.json",
  "evidence":"evidence/delivery.json"
}
```

Pass that request to `delivery-check`. It rechecks startup, original brief, current
intent, frozen artifact/context bytes, retained copies, lane evidence hashes and
existing design requirement coverage. Exit 1 reports `candidate_with_gaps`; exit 0
is only `ready_for_review`, never verified completion or permission. Changes reopen
affected evidence. Scope a review honestly rather than declaring unrelated screens
passed. Missing actual rendering stays missing under CLI-only execution.

`review_assessments.source_critique` and `review_assessments.requirement_context_design`
are separate. A real independent source critique can be recorded as a source-lane
pass while formal requirement-by-context design coverage remains `not_assessed`.
Do not manufacture rendered cases to make the latter green. The existing
`intent-cases`/design-review flow derives applicable destination/context/lane
obligations from selected intent; actual observations close only the lanes they
establish. Link the source findings and corrections, retain unobserved contexts,
and deliver the candid gaps when publication is separately authorized.

Use precise delivery language:

- **Local candidate prepared:** exact files and source/synthetic evidence are ready
  for the stated next step; native and rendered claims remain separate.
- **Authorized candidate preview:** the actual external action was authorized and
  its result is retained. A preview can be needed to observe native behavior; some
  creation routes publish immediately, so disclose that side effect before acting.
- **Verified selected scope:** only the named, executed current-candidate cases
  support this claim. Unrun access, responsive or human cases remain explicit gaps.
- **Published/read back:** the confirmed remote target matches the exact candidate
  within the documented verification scope. This says nothing by itself about
  polish, participant understanding or effective access.

Four resolved source consultations do not mean every lane is clean. Reconcile
carried warnings and unresolved findings against current retests before summarizing
them; do not hide the delivery assessment behind a stage-release status. Actual
rendering, host trials and user acceptance remain unrun when permission, tools or
access are absent. A CLI-only constraint never authorizes a headless workaround.

The helper neither invokes a provider nor wraps arbitrary native writes. A host may
use its exit status in a separately qualified managed delivery route; it cannot
claim universal enforcement. An authorized candidate may be delivered with visible
gaps. Update START_HERE with exact artifact links, evidence lanes and next action.
