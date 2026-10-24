# Omni native build, readback and export

Official sources checked 2026-10-21; tenant exercise not performed. Use this with the [connected migration workflow](../../omni-artifact-accelerator/references/connected-visual-migration.md). Discover actual schemas and enabled tools at execution time. Documentation does not establish which tools the current host has connected.

## Select the transport

MCP can discover content, list saved queries, run queries and download dashboards through `searchContent`, `listDocumentQueries`, `runSavedQuery`, and the `startDashboardDownload` / `checkDashboardDownload` / `fetchDashboardDownload` sequence. `askOmni` can build dashboards: edits to existing dashboards land in drafts, but **new dashboards publish immediately**. App reads and draft writes have separate tools; MCP `publishDraft` is app-specific and publishes the entire shared draft. Do not use it as a generic dashboard publisher. [MCP tools](https://docs.omni.co/ai/mcp/tools)

For controlled dashboard construction, prefer the configured CLI's document v2 workflow or its corresponding documented API. Inspect `omni documents v2-get`, `v2-get-draft`, `v2-patch-draft`, `v2-create`, and `v2-publish-draft` schemas. Old `documents update` and `put` commands were removed. App CLI commands are explicitly **alpha**, although Apps themselves and other document commands are described as stable. [Document commands](https://docs.omni.co/developers/cli/commands/documents)

The instance's `/api-explorer` and `/openapi.json` expose the current API contract. Use them to resolve payload structure, allowed fields, effective identity and response semantics instead of copying old examples. [API Explorer](https://docs.omni.co/api/api-explorer)

## Preparation and execution

The included [native draft helper](../scripts/omni_native.py) implements the bounded named-draft path below. Other operations still require a separately qualified tool or operator handoff.

If an existing target has a shared draft and the available tools cannot reliably inspect/read back that draft, prepare a local specification and obtain a qualified execution path or operator handoff. Download availability alone does not establish a safe authoring path.

1. Verify tenant, principal, model, destination and authorization. Inspect an existing target's current published state and draft, including other editors' changes. Save a recoverable before-state with exact IDs. Choose a dedicated development target when that matches the requested work.
2. Freeze the source-to-field/query crosswalk. Validate source and target rows independently before styling. Use a stable source placement → target tile identifier map; names alone are unsafe identities.
3. Inspect the current command help and request schema. Draft a request containing only selected tiles, queries, containers/layout, controls and theme references. Use request files, not shell interpolation of source strings. Do not embed secrets or customer rows in reusable scripts.
4. For an existing target, use the appropriate draft mutation. For a new target, inspect creation/publication semantics before execution and honor the granted destination and visibility. No assumed dry-run, idempotency key, rollback or compare-and-swap guarantee.
5. Preserve unrelated content and shared draft changes. Reconcile a conflict or uncertain outcome by reading state before retry. Match retained identifiers/content hashes to avoid creating duplicates after a timeout. Never use delete-by-name cleanup.
6. Retain the actual response and native readback. Check fields, query IDs, controls/listeners, layout, formatting and source mapping. Feed current native validation errors to the responsible owner; do not silently drop unsupported payload properties.
7. Export the exact candidate, compare, and only then execute separately required publication. Reread the published content; a write response alone is not the entire verification.

## Export the candidate that was actually built

The dashboard download API supports published content, drafts and individual tiles. Request `POST /api/v1/dashboards/{dashboardId}/download`, retain the job ID, poll status, then retrieve its file. Bind `queryIdentifierMapKey` for a tile, `filterConfig` for state and `containerPages` for the intended page; page-selection rules differ by format. A whole-dashboard PNG/PDF otherwise defaults to its first page. PNG/PDF provide visual evidence; CSV/XLSX or single-tile JSON provide result evidence. Only one concurrent download per dashboard/user is allowed; reconcile its existing job instead of resubmitting. [Download contract](https://docs.omni.co/api/dashboard-downloads/initiate-download)

The CLI exposes `dashboards download`, `download-status`, `download-file`, and filter inspection. Inspect command help and schema for the installed version before constructing a request. Do not assume the MCP wrapper exposes every REST option; use CLI/API when exact draft, tile or filter selection requires it. [Dashboard commands](https://docs.omni.co/developers/cli/commands/dashboards)

For each export retain document/draft/tile IDs, revision, requested filters, principal, timestamp, data watermark, requested format, output hash and limits. A draft rendered against one branch must not be compared to queries against another. Render Apps in their actual supported runtime and test interactions; a dashboard download is not proof of App behavior.

## Reuse without inheriting unsafe assumptions

Omni publishes a [Looker migration guide](https://docs.omni.co/guides/migrations/looker-to-omni-skill) with inspection and builder examples. Its sample builder deletes documents by matching name across folders and uses **beta** unstable export/import routes; the guide points toward v2 documents as the successor. Treat it as a reference for field/filter mapping, not an approved execution dependency. Use stable IDs and the current v2 contract; review any reused code before running it.

Optional official Omni skills and the CLI are external dependencies, not bundled or installed by this package. Record their exact versions and actual capability checks. Keep model changes with DMA or the selected model owner; a dashboard authoring tool does not expand backend scope.

## Included named-draft execution helper

### Local CLI trust boundary

Real CLI-backed calls require operator-selected canonical absolute paths and SHA-256 pins in `OAA_OMNI_CLI_PATH` / `OAA_OMNI_CLI_SHA256`. A script entrypoint also requires its native interpreter in `OAA_OMNI_RUNTIME_PATH` / `OAA_OMNI_RUNTIME_SHA256`. A native CLI binary needs only the first pair. Symlinks, group/world-writable files, mismatches and implicit shebang/PATH interpreter discovery are rejected. Pins establish byte identity, not approval: the operator must separately approve the CLI, runtime and dependency closure under the [package-use policy](../../omni-artifact-accelerator/references/dependency-policy.md). Changing pins is not a way to grant execution.

The child receives a fresh private temporary home, configuration directory and working directory, fixed system PATH/locale, and only the configured Omni token for authenticated calls. Help/version calls receive no credential. Unrelated tokens, proxies, loader/preload variables and existing CLI profiles are not inherited. Environments needing custom certificates or runtime configuration require an explicit reviewed extension; do not restore ambient environment copying. The explicit `--base-url`/`--profile` flags remain in authenticated commands; any vendor dependence on saved profile state needs live qualification.

The first-party POSIX transport concurrently drains input/output, caps stdout at 8 MiB and stderr at 64 KiB, and enforces a 60-second deadline. Stderr is discarded, and failures never echo credentials or request bodies. On failure it kills the process group, closes pipes and reaps the leader. Process groups are cleanup for cooperating children, not isolation against a malicious executable that escapes its group. File pins assume a trusted private host; they do not eliminate every concurrent same-user filesystem race or authenticate loaded transitive code.

An interrupted write remains `outcome_unknown` with its existing durable intent. Reconcile the named draft; never replay automatically. Test runner injection is trusted in-process test/host code, not a user-supplied artifact field or approval mechanism. Source-only tests do not execute the vendor CLI or establish native compatibility.

`omni_native.py` supports capability inspection, target inspection, preparation, one authorized PATCH, reconciliation and draft exports. It never creates or publishes a document, changes a model, applies App HTML, deletes a document, or accepts arbitrary command/URL input. New documents must first be provisioned through a separately authorized workflow because `v2-create` publishes immediately.

The implementation was checked against installed CLI **1.0.6** help and current official schemas on 2026-10-21. The specific route is `documents v2-patch-draft-by-identifier`; it edits an existing named draft without creation/publication. It addresses tiles by `queryPresentations.data` record key, preserves unowned keys, and treats containers as a complete replacement. Server validation remains authoritative for nested query, visualization, filter and layout grammars. [PATCH contract](https://docs.omni.co/api/documents-v2/patch-draft), [merge rules](https://docs.omni.co/api/documents-v2/create-draft-and-patch-document)

Use a private engagement folder. The operator supplies an explicit target file containing no credentials:

```json
{
  "base_url": "https://customer.omniapp.co",
  "profile": "migration",
  "document_id": "sales-development",
  "draft_id": "sales-development-draft",
  "model_id": "MODEL_UUID",
  "principal_id": "USER_MEMBERSHIP_UUID",
  "branch_id": "BRANCH_UUID",
  "token_env": "OMNI_API_TOKEN"
}
```

`branch_id: null` explicitly selects the main unpublished workspace. Use actual IDs obtained from the target, not these placeholders. Supply a user-scoped PAT/OAuth token in the configured environment variable outside prompts and artifacts; the helper verifies its membership ID through `whoami`, and passes the same token to the CLI through its environment. Organization keys and impersonation are deliberately unsupported in this version. CLI profile/base URL are explicit on every authenticated invocation. [Identity contract](https://docs.omni.co/api/who-am-i/get-current-identity-and-permissions)

Preparation accepts a reviewed native PATCH file, source evidence files including exactly one `analyst_visual_requirements` file, the selected semantic handoff/candidate file, and this ownership shape. The package's visual-workflow validator rechecks the original source/inventory pins and complete requirement coverage; an explicit non-`unselected` route and decision reference are required before target inspection/preparation. The engagement must select the dashboard surface.

```json
{
  "query_keys": ["2"],
  "control_ids": [],
  "container_keys": [],
  "settings": [],
  "metadata": [],
  "tab_order": false,
  "control_order": false
}
```

Only the listed tile/control keys, container `instanceKey`s, settings keys and `name`/`description` metadata may change. Container updates retain unowned nodes, their parent/page placement and relative order. Adding/removing tiles or controls requires an explicit complete order. This helper supports semantic `query`, `blank` and `linked` presentations; foreign/model-editor/upload/raw-SQL/App conversions require a different qualified path. Nested payload fields must come from current readback or documented schemas; the helper does not synthesize a chart configuration from a chart name. Readback comparison is exact except for the documented server-managed `model_extension_id` on owned tiles. Added filters, limits, chart settings or other defaults require review and are never silently accepted.

From the package directory, substitute the actual private workspace and reviewed filenames:

```sh
python3 skills/omni-bi-engineer/scripts/omni_native.py --workspace /private/engagement --target target.json capabilities
python3 skills/omni-bi-engineer/scripts/omni_native.py --workspace /private/engagement --target target.json inspect
python3 skills/omni-bi-engineer/scripts/omni_native.py --workspace /private/engagement --target target.json prepare --payload reviewed-patch.json --source sigma-source.json --source contracts/visual.json --semantic selected-semantic.json --ownership ownership.json --review-ref review-record-1
python3 skills/omni-bi-engineer/scripts/omni_native.py --workspace /private/engagement --target target.json execute --candidate EXACT_SHA256 --authorization-ref approved-candidate-record
python3 skills/omni-bi-engineer/scripts/omni_native.py --workspace /private/engagement --target target.json reconcile --candidate EXACT_SHA256
```

Preparation writes a content-addressed candidate under `.omni-native/candidates/`, including exact source/semantic/payload/ownership hashes, before-state, selected branch, principal, capability fingerprint and expected readback. Execution rechecks all pins and current target state, persists an exclusive intent before sending the PATCH, then reads the named draft. It refuses a second write for the same candidate even after a timeout or failure. Reconciliation only reads the known target and writes a receipt; it never retries the PATCH. It can inspect an earlier mutation even after source drift, explicitly marking `source_evidence_current: false`; stale evidence still blocks writes and exports. Receipts distinguish `readback_matched`, `readback_mismatch`, `outcome_unknown`, `conflict_or_partial` and `before_state_observed`.

This helper requires Python 3.9+ on a POSIX worker and the sibling accelerator skill. It uses a local file lock and optimistic drift detection, not an atomic vendor version precondition: a concurrent editor can still race between inspection and PATCH. Use a dedicated development draft and coordinate editing during execution. Retained before-state enables a reviewed recovery proposal; the helper does not automatically overwrite later edits to restore it. The operator's approval reference is an audit reference, not cryptographic proof of remote-human approval. A chat-host bridge must bind a configured target and exact authorized candidate at startup and enforce its own authenticated user boundary.

### Durable draft export

`export-start --candidate EXACT_SHA256 --request export.json --state state.json --authorization-ref approved-export-record` starts one bounded job against the **draft ID**. `export-status --export-id EXPORT_SHA256` performs one status check, and `export-file --export-id EXPORT_SHA256` saves verified media bytes after a confirmed complete status. Poll externally at the documented interval; no tight loop is built into the helper.

The request uses the documented download schema. Supported formats are PNG/PDF and single-tile JSON/CSV; numerical exports require an explicit `maxRowLimit` from 1 to 100,000. The state file requires `state_id`, `filters`, `persona` (membership ID), `timezone`, `data_watermark` and `viewport`. Unknown watermark/viewport may be recorded explicitly; neither becomes verified evidence. Filters must exactly match the export request. CSV/JSON row-limit completeness and data-watermark equivalence remain independent QA obligations.

Exports use fixed REST routes at the same configured origin because the installed CLI's binary-file behavior was not qualified. Redirects are refused, output size/media signatures are checked, filenames are generated locally, and bytes plus receipts remain private. PNGs also require bounded valid non-interlaced pixel data. An existing-job conflict is retained without adopting the other job; an ambiguous start is never replayed automatically. Export identity depends on the candidate, target, actual request and readback, so changing an approval label, file alias or recorded viewport/watermark cannot bypass the intent guard. Repeating an identical export requires a separately reviewed recapture path; this helper only retrieves its existing job. Candidate content is checked before submission and again before/after file retrieval. This cannot prove that underlying data remained unchanged during the job, nor detect a draft changed and reverted between observations. [Export](https://docs.omni.co/api/dashboard-downloads/initiate-download), [status](https://docs.omni.co/api/dashboard-downloads/check-download-status), [file](https://docs.omni.co/api/dashboard-downloads/download-file)

Local fake-transport regression tests cover persisted intents/receipts, matching exports, source/semantic drift, wrong targets/principals/branches, concurrent draft changes, unowned content, ambiguous writes, no replay, invalid media and export conflicts. These checks establish adapter behavior only. No test fixture or `readback_matched` receipt sets `native_verified`, security acceptance, business acceptance or publication.

## Qualify native App consumers before handing off rows

For App-bound queries, use the [offline native-query qualification recipe](../../omni-app-engineer/references/native-query-qualification.md). Independently pin the requested connection/database/schema/model and named query, retain effective query readback and usable semantic metadata, and reconcile the whole requested population against a separate count/aggregate result. CLI JSON exports, native callbacks and contract-shaped fixtures are different lanes; empty metadata or exported blanks must not be silently patched into a claimed native capture. Query caps are not permission to narrow the cohort.

That guide includes observed in-development payload details (initial App HTML during document creation, the semantic draft payload's empty `userEditedSQL`, and typed filters). Recheck the current endpoint/schema and mutation side effects before use. If an accessible requested catalog is absent from model inventory, propose the exact smallest workbook-only SQL query-view and explicit source binding before an authorized write; do not change shared models/connection settings. Re-read cloned draft model identities and re-run the exact query. The offline helper never executes a query or grants native-write authority.
