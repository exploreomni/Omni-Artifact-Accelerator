# Connected Sigma source host

The specialist and local tools prepare work without installing or importing the
Sigma runtime. Actual source operations require a separately reviewed runtime and
a host that can keep source secrets outside agent-authored files. The new source
extension is versioned separately from SigmaMigrationAgent's base version. See
[compatibility registry](sigma-compatibility.json); a recognized contract is not a
released binary or an activation approval.

## 1. Recover intake and generate requests

Use one existing private analyst engagement. Save an `oaa-sigma-intake.v1` JSON:

```json
{
  "schema_version": "oaa-sigma-intake.v1",
  "source": {},
  "scope": {"workbook_ids": [], "data_model_ids": []},
  "route": null,
  "route_reference": null,
  "target": {},
  "include_contents_beta": false,
  "evidence_mode": "live_tenant",
  "max_requests": 100
}
```

Run `sigma_plan_source` with `spec` and a new `output` path. It returns a pinned plan
whose questions identify only missing fields. Source requires `api_base_url`,
`approved_api_host`, `expected_organization_id`, `expected_user_id`, `principal_ref`
and `authorization_ref`. References start with `principal-ref://` and
`human-authorization-ref://`; they cite real retained evidence, not self-approval.
Never include a credential. Target records `origin`, `surface` and
`destination_reference`. `existing_run` preserves the earlier source run reference.

With source identity supplied, the plan contains check/inventory requests. Selected
workbook IDs enable snapshot. Optional `capture_requests` are exact inspected
v1/v2 visual requests; no tag, page, element, model or persona is guessed. Use
`sigma_materialize_requests` with `plan` and a new `directory` to write pinned
requests and return operation entries. Changing intake needs a new plan; reusing
an existing request directory is rejected. CLI equivalents:

```sh
python3 -I -S -B scripts/sigma_workflow.py --project /private/run plan \
  --spec inputs/sigma-intake.json --output contracts/sigma-plan.json
python3 -I -S -B scripts/sigma_workflow.py --project /private/run materialize \
  --spec contracts/sigma-plan.json --output inputs/sigma-requests
```

## 2. Review the exact source runtime

Prepare the dependency review before loading an unapproved runtime. The separately
reviewed Sigma source extension exposes `sigma-migrate capabilities` and
`sigma-migrate source-operation`. Its capability manifest names supported request
and result schemas, version, limits, original implementation file hashes and
unqualified lanes. The source CLI capability path is dependency-free, but this
does not waive approval for a newly acquired runtime or its other operations.

Use `sigma_check_capabilities` on the saved manifest. Unknown extension versions
require review, not a guessed producer SHA or automatic update. Maintain the
exact executable SHA, native Python interpreter SHA when a script is used,
source-package root and complete reviewed source/dependency file closure. A script
cannot resolve an interpreter through PATH or a shebang. Symlinked, changed or
group/world-writable files reject. No import smoke test runs during a static check.

Save `oaa-sigma-host.v1` with these fields in the engagement:

| Field | Contract |
| --- | --- |
| `runtime.executable` | Absolute canonical `path`, actual `sha256` |
| `runtime.interpreter` | Same pin shape for the native interpreter, if needed |
| `runtime.interpreter_kind` | `python` when the interpreter is supplied; launched with `-I` |
| `runtime.source_root` | Absolute reviewed `omni_migrator` package directory |
| `runtime.closure` | Nonempty list of absolute file pins, including every capability `implementation_files` entry and reviewed dependency closure |
| `capabilities` | Engagement-relative file pin for the reviewed capability manifest |
| `operations` | Entries returned by `sigma_materialize_requests`: `id`, request pin, unique private `directory` |
| `max_invocations` | Integer 1–200 |
| `max_total_requests` | Integer 1–10,000; conservative reservations survive failures/restarts |
| `timeout_seconds` | Integer 1–300 for each bounded child process |

Hashes detect drift; they do not authenticate approval, prove closure completeness
against malicious same-account code or isolate a compromised child. The trusted
host owns those boundaries. Local stdio is not a remote multi-tenant service.

## 3. Activate only the selected source operations

After runtime approval, the local host supplies `SIGMA_CLIENT_ID` and
`SIGMA_CLIENT_SECRET` through its secret mechanism and starts:

```sh
python3 -I -S -B scripts/visual_mcp.py --project /private/run \
  --sigma-operations inputs/sigma-host.json --enable-sigma-source-operations
```

Add `--enable-sigma-source-query` only for the separately authorized render/result
capture scope. Source capture can execute warehouse queries. Neither flag grants
Omni writes or dependency approval. The earlier `--enable-sigma-capture` wrapper
is disabled; migrate its request into the new pinned operation contract.

`sigma_source_doctor` checks pins without executing the source runtime.
`sigma_source_operation` accepts only a configured operation ID and `resume`.
Before a credentialed child runs, the adapter checks credential-free capabilities
against the pinned manifest. Children receive a private HOME/config/temp directory,
bounded streaming output/deadline and Sigma credentials only. Omni tokens, ambient
Python paths and general shell commands are not forwarded. Requests and runtime
closure are rechecked before execution. Source transport enforces exact origin/TLS,
bounded requests/downloads and redirect rejection.

Every operation writes a `sigma-source-operation.v1` envelope. Capture receipts pin
the original visual envelope under its existing immutable journal. Unknown export
POST outcomes are reconciled/resumed; never retry by changing the output directory
or generating a new capture ID. A new scope or source version requires an explicit
new reviewed run. Save old artifacts and reservations.

## 4. Import, qualify and build

Use `sigma_translate` with the source envelope and producer profile
`sigma-source-operations@0.1.0`. This denotes contract compatibility, not a release
commit. Import the referenced visual envelope with its retained directory;
`sigma_check_capture` verifies actual images/results. `sigma_normalize_results`
requires explicit parser profile and original-byte/state binding. A passive
`sigma-source-evidence-bundle.v1` uses profile `oaa-sigma-evidence@1` for separately
retained REST, Beta contents, page/element renders, results and official MCP inputs.
Do not combine differing published/tagged/saved-view states as one capture.

Proceed through [A–F](stage-gates.md). An independent full source inventory controls
scope, including unsupported and non-query objects. Source discovery must not
prematurely choose a product, library, layout or cache policy.

Reuse upstream deterministic converters through their existing local terminal
review/build workflow. Preserve that human review; no host-authenticated review
adapter is enabled by this release. `sigma_check_package` reads every manifested
file, rejects extras/changed files, and checks source, target and proposal bindings.
It reports supplied OS review rather than authenticating the person who approved it.

After actual E selection/design, `sigma_package_handoff` accepts a spec with
`schema_version: oaa-sigma-package-handoff.v1`, the exact `manifest` pin,
`requirements` path and `target_context` path. Requirements must retain the exact
package source JSON as their original; retain other captures as supplements.
The helper verifies route/source/target and returns original converter file pins.
It does not copy a native payload across incompatible APIs or generate a second
converter. The BI engineer inspects those outputs and current Omni schema, then
uses [native preparation](../../omni-bi-engineer/references/omni-build-export.md)
with semantic bindings, owned keys, before-state and candidate-bound reviews.
`reuse_existing` uses the verified standalone semantic baseline path rather than
manufacturing a Sigma semantic-build package.

Native named-draft modification, initial creation and App action behavior have
separate qualified routes. Initial creation may publish immediately: it is not a
fallback for an unavailable draft. Unknown write outcomes require readback and
reconciliation; publication and business acceptance remain separate.

## Host qualification and release

Source-only checks qualify local contracts, not live Sigma/Omni or a chat host.
Before a live pilot, verify one selected workbook and its effective principal,
source state, dependency loading authorization and exact Omni development target.
Test reconnect/resume, a changed source version, allowed/denied personas, numerical
completeness, visual behavior and target readback. Retain all unobserved lanes.

Local Codex/Claude Code/Cortex use requires a supported process/stdio integration;
availability is not inferred from a successful Python test. ChatGPT remote access
requires a separately qualified authenticated HTTPS host with tenant isolation,
secret handling and storage policy. This package provisions no service or tunnel.

Release the Sigma extension first, record its reviewed release revision/runtime
manifest, then update the accelerator compatibility registry and qualify that
pair. The compatibility registry records the published extension commit separately
from the earlier base commit. Source publication does not qualify a runtime or host.
Keep plans, live captures, credentials, runtime archives and rehearsal outputs
outside both repositories. A clean source release may retain explicit live gaps.
