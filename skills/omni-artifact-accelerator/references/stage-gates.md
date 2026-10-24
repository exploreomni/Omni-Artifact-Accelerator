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
The trusted host must own the verifier, project/policy binding, evidence journal
and tool dispatch boundary, and must prevent raw authoring/write routes while the
gate is closed. No production host adapter is supplied or qualified here.

## Order and evidence

The journal is `stage-gates.json` in the private engagement. Evidence paths are
relative to that engagement, bounded regular files, pinned by content hash. Keep
credentials, private results and engagement records outside the repository.

| Stage | Record | Required evidence keys | Additional fields |
| --- | --- | --- | --- |
| A | `access` | `data`, `user_access` | `source_scope`, `user_identity` |
| B | `analysis` | `profile`, `queries`, `insights`, `expectations` | `analyst`, `bi_engineer` |
| C | `narrative` | `narrative`, `traceability`, `refresh` | `storyteller`, `analyst` |
| D | `brief` | `brief` | none |
| E | `options` | `comparison` | exactly three `options` |
| E | `choice` | none | `option_id`, `receipt_ref`, verified by host |
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

## Commands and host choice boundary

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

**The stock CLI cannot cross the choice gate.** A receipt string, local approval
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
is required before claiming enforced Claude/ChatGPT end-to-end operation.

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
