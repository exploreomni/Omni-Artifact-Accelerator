# Enter, build and assess an artifact engagement

Use for substantial new design, redesign and migration. This procedure connects
the existing project, selected intent, specialist assignments and design review.

For net-new products and explicit product reconception, the
[data-first A–F workflow](data-first-product-workflow.md) governs execution order.
Record startup first, then verify source/user access, analyze governed queries and
complete the reusable narrative before artifact discovery. Present three viable
options and obtain the user's selection before detailed design/full implementation.
The [executable stage gates](stage-gates.md) enforce that sequence at supported
entrypoints and require a trusted host verifier for actual option selection. The
stock CLI stops at choice. No production host adapter ships; hosts must also guard
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
Gated implementation remains blocked until a capable trusted host can execute the
checks and verify the actual choice; attachments and prose are not a bypass.

For a repository-only blind trial, use only the selected checkout and supplied
inputs. Do not compare installed copies or read previous apps, outputs or memory.
For each supported host, qualify actual behavior separately. No bootstrap file,
boolean or self-authored receipt can grant authority or govern unrelated MCP calls.

## Record startup and ownership

Initialize the existing project with `analyst_project.py init`. Preserve the original
request verbatim in `inputs/brief.txt`, redacting credentials before saving. Recover
existing answers; use one material question batch where feasible. Resolve routine
design choices internally. Read the relevant skills, then create a startup request:

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
  "loaded_guidance": [
    "skills/omni-artifact-accelerator/SKILL.md",
    "skills/omni-app-designer/SKILL.md",
    "skills/omni-branding/SKILL.md",
    "skills/omni-data-analyst/SKILL.md",
    "skills/omni-app-engineer/SKILL.md",
    "skills/omni-qa-analyst/SKILL.md"
  ]
}
```

Use `installed` only from the installed helper (guidance paths then omit `skills/`).
`connected_reference` records a locally available package used from a connected
host; it does not fetch or prove remote loading. Record only guidance actually read.
Add relevant design-systems/storyteller guidance when assigned. Host execution modes
are `inline`, `delegated`, or `instruction_guided`; actual worker invocation still
uses [scoped task records](task-routing.md).

For substantial product decisions, follow the [product-intent front door](product-intent.md)
and record the product-owner plus assigned creative-review guidance actually read.
Notes stay in private engagement inputs/evidence. Recover existing answers before
interviewing; a focused repair does not restart discovery. Select the canonical
intent, then use `product-brief` and `product-check` for its readable North Star.

```sh
python3 -I -S -B "$OAA_HELPER" run-start --project "$OAA_RUN" --request startup.json
```

The immutable `evidence/run-first-run.json` includes source hashes, Git identity
when available, reported reads, constraints and the original-request hash. Keep
the selected checkout stable during a trial; changing the package requires a new
run ID, preserving the prior record. Startup does not compare installed copies in
repository mode, run agents, authenticate host claims or confer publication rights.

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
    "design_systems": {"role":"design-systems","worker":"","mode":"not_required","rationale":"Existing reviewed controls are unchanged"},
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
independent worker can cover both review disciplines. Legacy seven-role records
remain supported; focused repairs need no extra interview or review ceremony.

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

Run `run-check` with a request containing `run` and `execution` paths. It checks
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
a fixed template. More prose cannot replace actual critique.

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
intent files are added automatically. The command creates new, never-overwritten
candidate records and copies exact artifact bytes. Hash history is tamper-evident
when checked, not immutable storage or proof that no earlier candidate existed.

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

The helper neither invokes a provider nor wraps arbitrary native writes. A host may
use its exit status in a separately qualified managed delivery route; it cannot
claim universal enforcement. An authorized candidate may be delivered with visible
gaps. Update START_HERE with exact artifact links, evidence lanes and next action.
