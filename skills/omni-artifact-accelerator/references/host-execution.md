# Host-neutral execution integration

Use the existing engagement as the workflow state. A host adapter binds actual
capabilities to it, without another orchestrator, product template, model choice
or permanent team. Read this guide when integrating a host or diagnosing repeated
dispatch and context ingestion.

## Small tool surface

For effective setup, fixed task preparation, selective reads and local measurement,
use [execution efficiency](execution-performance.md). Existing defaults and individual
operations remain compatible; prompt-layout changes are explicitly optional.

With an already approved interpreter and the selected package checkout:

```sh
python3 -I -S -B /absolute/package/skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /absolute/private-engagement --tool-profile execution
```

This starts a local stdio server. It does not install a plugin, activate a library,
connect accounts, launch workers, open a browser or authorize publication. Register
it through the actual host's approved process interface. The default `legacy`
profile preserves existing integrations. New integrations explicitly select
`execution`, or `selected` with repeated `--enable-tool EXACT_EXISTING_NAME` for
needed source/target tools. Selection cannot grant native authority. Hidden tools
are rejected on invocation, not just omitted from discovery.

| Tool | Purpose |
| --- | --- |
| `execution_status` | Current stage, choice bindings, blockers and task progress |
| `execution_contract` | Small request contract for one fixed operation |
| `execution_prepare` | Work packet, bounded context, preflight or reservation |
| `execution_record` | Supplied dispatch, checkpoint, usage, blocker or review |
| `execution_lifecycle` | Existing startup, guidance, phase, stage, intent selection/check, product brief/check and freeze |
| `execution_review` | Explicit review policy, impact, carry or manifest |
| `execution_analysis` | Explicit result identity and independent comparison intake |
| `execution_efficiency` | Context policy and measured usage report |
| `execution_assembly` | Reproducible assembly and dependency comparison |
| `execution_qualification` | Scenario catalog and supplied-evidence coverage |

Most calls take `operation` and a project-relative JSON `request`. Context build
and qualification record also take a new relative `output`. Read
`execution_contract` first; nested contracts remain in their scoped references.
Example arguments: `{"operation":"preflight","request":"tasks/preflight.json"}`;
request: `{"action":"build","packet":"tasks/work-v1.json","context_receipt":"tasks/context-v1"}`.
CLI equivalent: `analyst_project.py execution-tool --project PROJECT --tool TOOL
--request ARGUMENTS.json`. Neither path accepts arbitrary commands, modules or
credential selection. A rejected request is not permission to use a raw write.
Generate the current product brief through `execution_lifecycle/product_brief`
before preparing scoped implementation work; `product_check` reports whether that
projection and its source intent remain current.
Use `intent_select` with `{"spec":"contracts/intent-v1.json","output":"contracts/selected-v1.json"}`
to bind an existing reviewed design specification through the same selection helper;
`intent_check` checks its current pins. This is distinct from the actual user choice
record in Stage E. It cannot replace or manufacture that reply. Status includes
`review_assurance` alongside readiness so source-only review is not mistaken for
native or human acceptance.

## Actual worker integration

Before first dispatch, call `host_entry.check(project, request, provider=provider)`
from the trusted package entry. The ordinary CLI and file-based calls use advisory
mode. For enforcement reporting, the operator constructs an independently
qualified provider with `verify_entry(binding)`. The binding includes project,
host, loaded/verifier package identities, requested release, complete route
inventory and a fresh challenge. It changes on each invocation.

The provider returns exactly `binding_sha256`, `loaded_package_path`, `routes`,
`denied_probes` and `qualification_reference`. It must verify the actual loaded
path and tool inventory independently, then authenticate the exact current
binding. Each available route needs a denied-write observation with `kind`,
`name`, `outcome: denied` and an original `evidence_reference`. Bind the canonical
JSON SHA-256 of the complete challenge-bearing binding. A changed or unknown
route, missing probe, stale response or unavailable observer produces advisory
mode. The provider's actual capability or credential boundary must deny those
writes. This package ships the interface and synthetic contract fixtures.

No provider is selected through request JSON, a module path or an environment
variable. `prepare` may retain its observation for specialists through an existing
startup pin. Retained enforcement observations are historical. Actual mutations
still require current host participation and the action's existing candidate,
stage and authorization checks.

An operator-owned integration constructs `execution_runtime.Runtime(project,
driver, binding)` and passes it to `visual_mcp.Bridge(...,
tool_profile='execution', execution_runtime=runtime)`. This adds `execution_host`
with `status`, `launch` and `reconcile`. No request-file/CLI driver loader exists.

The binding contains `adapter_id`, `adapter_version`, `host_version`,
`configuration_sha256`, `tool_scope`, `context_mode`, `model`, and `effort`.
Use actual settings. Null model/effort mean unavailable observations, not permission
to downgrade; explicit settings must match observed execution.

The operator supplies bounded `launch(payload)` and `reconcile(launch_id)` calls.
Launch receives generated launch/attempt/project identities, actual bounded
`task_utf8` and hash, packet hash, assigned output paths and configured binding.
Invoke the real supported worker mechanism once. Reconciliation never starts a
replacement. Missing lookup permissions, eventual consistency and timeouts mean
`unknown`; `absent` requires definitive evidence the launch cannot begin later.

Both calls return exactly `launch_id`, `status`, `host_run_reference`,
`context_mode`, `task_sha256`, `observed_model`, `observed_effort`, `tool_scope`,
and `evidence_reference`. Status is `active`, `unknown`, `completed`, `failed`,
`cancelled`, or `absent`. Retain originals behind evidence references. A hash echo
or host report does not authenticate isolation or actual tool enforcement.

Preserve mandatory system/workspace/security instructions while avoiding inherited
engagement history where supported. Report inherited or unknown context honestly.
A small briefing is not proof of fresh context. Record invocation usage once;
do not infer token cost or billing from bytes.

## Recovery and permission

Managed launch requires a capacity-counted specialist reservation. A per-attempt
process lock fences launch and reconciliation. Pending intent is atomically saved
and synchronized before invoking the driver. Duplicate launch requests require
reconciliation. Unknown/active workers retain output ownership; cancellation must
be observed before replacement. Completed-output checkpoints require observed
completion and current pins. Raw receipts cannot replace managed invocation IDs.

The actual host must protect its configuration/credentials and qualify alternate
file, shell, API and tool routes. This cooperating library does not sandbox them.
If that boundary is unavailable, label execution instruction-guided and keep
privileged operations unavailable. Agent-authored policies, approval references
and qualification files cannot grant authority.

Native mutations retain the existing guarded target path. An uncertain outcome
requires exact readback before retry. The separately requested
[demo preparation route](native-demo-qualification.md)
retains pending observations without weakening release gates or authorizing writes.
If creation publishes immediately, describe it as publication, not an unpublished draft.

## Qualification and refinement

Use the [qualification catalog](execution-qualification.md) for the actual host,
version, source and destination. Early bounded probes establish query identities,
callback shapes/types, filters, errors and refresh behavior; do not scan unrelated
tenant apps. Diagnostic probes do not permit product coding before A–E selection.

Keep local synthetic checks, host execution, native readback, rendered behavior,
access and human acceptance separate. Missing native observations remain pending
even when local tests pass. Honor permitted observation tools without a browser
workaround. Maintain supported/unsupported/unknown capabilities for the exact profile.

Use [analytical evidence](analytical-evidence.md) and
[assembly provenance](assembly-provenance.md) for scoped corrections. Preserve all
four review perspectives and unknown impact. Compare equivalent scope/model/quality
when measuring efficiency; do not reproduce an expensive failure loop to manufacture
a baseline. App query caching remains the user's separate interview decision.

Keep real host profiles, telemetry, captures, decisions and pilots outside this
repository. Commit maintained code/guidance and original fixtures only. Host and
dependency activation and publication retain their separate authorization.
