# Prepare an explicit repository entry

Use a selected local checkout and an initialized sibling engagement. The package
stays in its repository; private briefs, contracts, entry records and delivery
evidence stay in the engagement. This route does not install a skill, configure a
host, clone/update a checkout or edit existing instruction files.

The host must explicitly read the generated reference. A file in a sibling
directory is not evidence that the host discovered or loaded it. Read the exact
repository orchestrator and follow [the execution procedure](execution-workflow.md).
Keep the existing A–F sequence, actual selection and candidate review boundaries.

## Inspect the host entry first

Invoke `scripts/host_entry.py` from the current trusted checkout before dispatching
through an installed copy. The request's `loaded_package_path` identifies the
reported package root, either the checkout or the directory containing installed
`omni-*` skills. This verifier reads that tree as inert bytes. A stale installed
skill needs this external entry check because its own shipped code may predate it.

The request has `schema_version: 1`, a lowercase `id`, the same `host` declaration
and `source_expectation` used by startup, `loaded_package_path`, and `routes`.
Each route row has `kind`, a concrete tool `name`, and `availability` set to
`available`, `unavailable` or `unknown`. Include every actual route that can
create, edit or publish content. Account for every kind in `package_helper`,
`cli`, `api`, `mcp`, `shell`, `file_write` and `other`, using an explicit unknown
row where the host inventory is incomplete. General shell access matters even
when the preferred publication helper is guarded.

```sh
python3 -I -S -B /absolute/trusted-checkout/skills/omni-artifact-accelerator/scripts/host_entry.py check \
  --project /absolute/private-engagement --request requests/host-entry.json
```

The report shows the verifier and reported loaded paths, observed revisions,
clean/dirty/unknown state, exact source agreement, requested release policy and
route inventory. Installed copies can match the verified checkout's skill bytes
while their own revision remains unknown. `current_checkout` records available
bytes. `offline_snapshot` requires `manifest_sha256` matching the full local
package manifest and reports `offline_bytes_verified`. Pinned and latest-main
expectations retain the existing clean-revision rules. A current-release test
also needs independently corroborated host loading. Review any mismatch and use
the existing approved update procedure before claiming that test.

Use operation `prepare` to retain this report as an immutable private record.
Pass its returned `{path, sha256}` as optional `host_entry` in the repository
entry request and `run-start`. Startup rechecks its source and brief/host
bindings before recording. Repeated preparation with the same ID preserves
the record. Resume rechecks bytes against that recorded entry and retains its
historical release observation. A fresh latest claim needs a new source check.
Preserve older entries without inventing a missing route inventory.

The default host boundary is `advisory`. Request JSON and saved receipts cannot
establish enforcement or authorize a write. The operator-owned integration in
[host execution](host-execution.md) can supply a current boundary observation.

## Prepare the entry

1. Initialize the engagement once through the existing `analyst_project.py init`
   route, or resume that same engagement. Its directory and the selected checkout
   must have the same parent. Preparation never creates a replacement engagement.
2. Save the actual original brief in `inputs/brief.txt`, without credentials, and
   the current responsibility contract in `contracts/execution.json`.
3. Supply the host name, execution mode, tools and restrictions actually known.
   These are declarations. Do not describe a requested or planned tool as observed.
4. Prepare a private entry with a new ID. Source expectations use the same rules
   as `run-start`: current working-tree bytes; an exact clean pinned revision; or
   an exact clean revision with this engagement's fresh existing source-check
   receipt. Entry preparation never performs the remote check itself.

`prepare(root, request)` accepts:

```json
{
  "schema_version": 1,
  "id": "initial-entry",
  "host": {
    "name": "Chosen local host",
    "execution_mode": "instruction_guided",
    "tools": ["Approved local file reading", "Approved first-party helper execution"],
    "constraints": ["No dependency activation or external writes"]
  },
  "startup": {
    "brief": "inputs/brief.txt",
    "execution": "contracts/execution.json",
    "source_expectation": {"kind": "current_checkout"}
  }
}
```

Host modes are `inline`, `delegated` and `instruction_guided`. An optional
`runtime_observation` is an exact `{ "path": "evidence/observation.txt", "sha256":
"<64 lowercase hexadecimal characters>" }` pin. It retains supplied evidence;
it does not authenticate a runtime, prove its freshness or qualify its permissions.
The checker does not infer tool availability from that file's prose.

The execution bridge exposes this as `execution_lifecycle` operation
`entry_prepare`, using the existing private JSON `request` path argument. The
generated directory is `evidence/entry-<id>/`:

The same operation is available through the existing CLI, without another server:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py execution-tool \
  --project /absolute/private-engagement \
  --tool execution_lifecycle \
  --request /absolute/private-engagement/requests/entry-arguments.json
```

The arguments file contains `{"operation":"entry_prepare","request":"requests/entry.json"}`;
the request file contains the shape above. For `entry_check`, use
`{"record":{"path":"evidence/entry-initial-entry/ENTRY.json","sha256":"<returned hash>"}}`
as its request. The returned check separates package binding, actual workflow
records and host authority; `entry_current` is not permission to build or publish.

| File | Purpose |
| --- | --- |
| `ENTRY.json` | Exact project identity, resolved sibling locations, source manifest/Git identity, source expectation, input pins and generated-file hashes. |
| `START_HERE.md` | Private reference to the exact repository entry and procedure for explicit host use. |
| `STARTUP_REQUEST.json` | A startup template with an empty `loaded_guidance` list; preparation cannot claim reading. |

These files are private and immutable. Preparation preserves the engagement's
existing `START_HERE.md` and every existing repository/host instruction file.
There is no automatic installation or apply step. The same ID and same request
reuse the saved entry and inspect it again; a different request needs a new ID.
A source or input change makes the retained entry stale rather than silently
rewriting it. The record is byte provenance, not an authenticated attestation.

## Record actual startup, then inspect

Explicitly read the referenced repository entry and required first-phase guidance.
Copy the startup template to a new file under `requests/`, fill `loaded_guidance`
with only the guidance actually read, and use the existing `run-start`. Do not
edit the immutable template. If a matching startup already exists, resume it;
preparation does not require another startup solely to manufacture a new record.

For `latest_main`, a new preparation and a new startup each retain the existing
ten-minute source-check requirement. Inspecting an already accepted entry compares
the exact retained source/verification pins; it does not renew that age rule or
follow later remote changes. An unstarted entry therefore cannot substitute for
the source check required when startup is eventually recorded.

`check(root, {"record": {"path": "evidence/entry-initial-entry/ENTRY.json",
"sha256": "<exact record hash>"}})` performs a fresh local inspection. The bridge
operation is `execution_lifecycle` / `entry_check`, with this object in the private
request file. It verifies generated files, source bytes, Git identity, original
brief, execution contract, supplied observation and source-verification pins.
The active startup must match the repository-only mode, host declaration, brief,
execution path and source expectation. An unrelated valid startup is insufficient.

| Result component | Meaning |
| --- | --- |
| `package_check` | Source manifest and entry files match. No package test suite was executed. |
| `initialized_engagement` | This existing project is the bound sibling engagement. |
| `workflow_observed` | Local startup, stage and phase records were inspected. Recorded reads are declarations, not proof of comprehension. |
| `host_authority` | Declared/supplied evidence is separate from actual loading and qualified enforcement, which remain unproven here. |

Missing startup, stale inputs/source, a mismatched startup or unresolved phase
requirements returns `not_ready` with a bounded recovery action. `entry_current`
means only that these entry bindings and current phase requirements match; it
does not approve a stage, dispatch a worker, validate a candidate or grant native
or publication permission. The normal stage and execution guards still apply.

After an intentional package change, preserve old records, prepare a new entry,
record the appropriate refreshed startup and use the existing same-journal
requalification procedure. Original selection and evidence retain their own
freshness requirements. Neither new entry files nor old compatible receipt
formats bypass implementation/source pins.

Raw CLI, file, API and alternate tool routes remain a host limitation. A trusted
host must independently qualify and constrain those routes; no bootstrap file,
boolean, receipt or supplied observation can establish that boundary.
