# Enter, build and assess an artifact engagement

Use for substantial new design, redesign and migration. This procedure connects
the existing project, selected intent, specialist assignments and design review.
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
    "storytelling": {"role":"data-storyteller","worker":"","mode":"not_required","rationale":"No interpretive narrative is in scope"}
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

Use the [native data-input procedure](../../omni-app-engineer/references/native-data-input.md)
before making the full design depend on a query. Keep connection/database/catalog,
metadata, population and NULL behavior explicit. Query exports and reconstructed
callbacks are different evidence. Reuse governed definitions; send actual missing
semantics through the existing DMA handoff, not an unnecessary warehouse rebuild.

The [first-delivery workflow](first-delivery.md) and [experience brief](../../omni-design-systems/references/experience-brief.md)
own design decisions. Select a direct direction or compare where useful; preserve
brand authorization, first/return use, dominant evidence, control states, responsive
width **and height**, and useful detail/return. Review the complete first journey,
then every consequential destination. No fixed KPI count, tabs, animation, imagery,
3D or number of concepts is required. More prose cannot replace actual critique.

Make the first journey representative of the ambition, not just a thin technical
path. Preserve defining brand/interaction qualities and useful evidence. When a
method is unsupported, record its preserved outcome, feasible alternative and
remaining gap; do not let feasibility silently redefine the requested experience.

The original assembler automatically stores exact first HTML bytes and each changed
assembly under `evidence/assembled-history/` before review. For custom assembly and
complete delivery context, run `candidate-freeze` immediately after first assembly,
before fixes, then again for the delivered revision:

```json
{
  "id":"initial",
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

The helper neither invokes a provider nor wraps arbitrary native writes. A host may
use its exit status in a separately qualified managed delivery route; it cannot
claim universal enforcement. An authorized candidate may be delivered with visible
gaps. Update START_HERE with exact artifact links, evidence lanes and next action.
