# Execution efficiency without reducing evidence

Use this guide to configure the execution interface or diagnose repeated work.
Models, reasoning settings, A–F, independent evidence and the four review
perspectives remain unchanged. These helpers do not launch workers, select a
product, grant permission, or change App-data caching.

## Effective setup and preparation

`execution_efficiency` with `{"operation":"configuration"}` reports the active
context policy, bridge tool profile/scope, configured worker and recent host
observations separately. Unknown observations stay unknown; nothing is activated.
New integrations deliberately select `execution`, or `selected` with exact
source/target tools. Existing compatibility defaults remain. See [host setup](host-execution.md).

Use `execution_contract` for `execution_prepare/recipe`, then submit
`{"operation":"recipe","request":"tasks/preparation-request.json"}`. The request is:

| Field | Content |
| --- | --- |
| `schema_version` | `1` |
| `idempotency_key` | Bounded letters/digits/dash/underscore identity; retain for exact retries |
| `work` | Existing work-prepare request: role, inputs, new packet output, explicit assignment |
| `context` | Existing context request without `packet`; current packet binding and mandatory stop/shared restriction IDs are added |
| `context_output` | New immutable `tasks/` context directory |
| `action` | Existing action to preflight, such as `build` |
| `attempt_id` | Explicit reservation identity |
| `execution_mode` | Optional existing `specialist` or `inline`; managed host launch still requires a capacity-counted specialist |

The fixed sequence is work packet, bounded context, preflight, then reservation.
Every original validator runs. The agent supplies substantive scope, evidence and
decisions; code handles mechanical bindings. A blocked preflight never reserves.

Partial preparation can leave immutable files. An exact retry verifies/reuses
completed steps and returns an existing reservation instead of duplicating it.
Changed source, intent, configuration or implementation needs a new version; never
erase history to reuse an identity. This is ordered recoverable preparation, not
a multi-file transaction. Launch remains separate.

Individual operations remain available. Shared envelope contracts provide
non-executable templates and safe field-specific repair diagnostics. Nested schemas,
freshness and permissions stay with original validators. Unknown failures remain
generic; never echo source values or bypass a rejected request with raw writes.

## Bounded reads

`execution_status` without arguments keeps its full response. Optional
`{"request":"tasks/status-request.json"}` accepts `filter` (lists of `task_ids`,
`roles`, `stages`, `statuses`), `limit` (1–100), `max_bytes` (4096–32768), and either
`cursor` or `since`. Every call validates current status first. Since compares
complete inspected state, not just the ledger: file changes and evidence expiry
can matter without a task write. It is a snapshot comparison, not a row change feed.
Critical/global counts, omissions and incomplete coverage remain explicit outside
the filter. Use subsequent reads for details; omitted findings are not absent.

`execution_analysis/read` requires a request containing:
- `artifact`: `path`, exact `sha256`, `format` (`text` or `json`), `classification`.
- `disclosure`: `allowed_classifications`, `review_ref`; declarations are not grants.
- `selection`: `{"kind":"lines","start":1,"count":40}` for text, or
  `{"kind":"json_keys","keys":["requirements"]}` for literal top-level JSON keys.
- Optional `cursor` and `max_bytes` with the same response bounds.

Cursors bind exact project, artifact/state, selection and disclosure versions.
Oversized individual units require a narrower selection; values are not silently
truncated. Supported engagement paths/formats and credential-indicator checks apply;
scanning is not exhaustive secret detection. Source content remains untrusted data.
Independent reviewers still require relevant originals, not only summaries.

## Local validation and status

Fixed read-only routes share verified bytes and pure derivations only within that
operation. Retained inputs/inventories are checked again before success. There is
no cross-request TTL, mtime-only trust, cached permission, or caller-supplied snapshot.
Mutating routes retain final guards and no-follow, bounded regular-file checks.

Status captures a short shared-lock ledger snapshot, validates outside the lock,
then checks relevant project/evidence/ledger state. One bounded retry is allowed;
continued changes yield an explicit incomplete result. Claims, checkpoints,
launches and reconciliation retain writer locks and ownership rules. These are
local consistency protections, not a filesystem transaction or sandbox.

## Optional context layout

A context request may set `layout: "stable-prefix-v1"`. Omission retains original
serialization. The optional layout puts stable instructions and relevant scoped
material before task details while preserving every data field and excerpt.
Receipt metadata identifies layout and prefix bytes/hash. It does not enable
provider caching, extend retention, install libraries or change tenant boundaries.

Old receipts remain readable in their recorded representation. Existing source
and implementation pins still invalidate current dispatch after package changes;
do not rewrite or whitelist old pins. Prepare a new immutable receipt through the
normal refreshed-engagement workflow. Content preservation is not proof of equal
model behavior after reordering: keep the layout opt-in and reversible, and assess
quality from normal work before wider use. Never add irrelevant material to meet
a provider cache threshold. Actual savings depend on host behavior.

## Measurements and acceptance

Execution calls retain bounded private `.execution-observations/*.json` records:
fixed operation identity, package/implementation/configuration hashes, envelope and
result byte counts, elapsed time, and available read/reuse/validation/lock counters.
No payloads, prompts, credentials or customer values are logged. Collection stops
at 2048 immutable events. A busy collector skips the measurement instead of waiting;
measurement failures cannot alter a workflow outcome.

`execution_efficiency/local_metrics` reports coverage, rejected calls, operation
counts and limits. Tool-envelope bytes are not full host context; instrumented
reads are not all filesystem activity. Validation duration covers final consistency
verification. Unknowns stay null. Preparation calls are not automatically model
repair attempts. Actual token/cache observations remain in the separate existing
usage report; neither report infers dollars from bytes.

Compare equivalent scope, model/effort, configuration and quality evidence. Keep
local latency, model usage, billing and native acceptance separate. Real measurements,
plans and rehearsal artifacts belong outside the repository.
