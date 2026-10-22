# Looker visual migration: operator workflow

Use one captured Looker scope for a native Omni dashboard, an App, or both. Choose the surface during intake; `both` needs separate target documents and separate candidate/readback evidence. This guide describes the local v0.10.0 implementation. Live numerical, interaction, access and business qualification remain engagement work.

## Intake and source boundary

Record the dashboard URL/native ID, selected tabs, actual source deployment/API context, important tasks, personas, source filters and data timing. Preserve LookML IDs as opaque IDs. Reuse the existing route decision: `reuse_existing`, `omni_semantic_reconstruction`, `warehouse_first_refactor`, or unresolved `unselected`. Surface choice does not authorize warehouse work.

Ask missing brand context once: **“What is your company website URL, and are there approved logos, brand guidelines, fonts or reusable images we should use?”** Separate website observations from approved brand rules. Track origin, permission, intended use and fallbacks for supplied images. The broader automated internet asset catalog remains a planned extension.

Read the [source contract](../../omni-artifact-translator/references/looker-source-contract.md) for the complete request/envelope and limits. The maintained routes are supplied API JSON, supplied local definitions and fixed Looker API4.0 reads/renders/results. Official managed MCP is a separate **Preview** route: discover actual available tools and transfer files explicitly. This package does not install or administer a Looker connector or assume its responses include screenshots.

Keep private engagement files outside the skill bundle. Initialize an engagement with `analyst_project.py init`, then save a reviewed `looker-visual-capture-request.v1` request. Use actual paths and IDs; `/private/run` and `/installed` below are placeholders. Credentials belong in the operator's approved secret mechanism, never request JSON, commands, chat or captured artifacts.

```sh
python3 /installed/omni-artifact-translator/scripts/looker_capture.py import-api \
  --request /private/run/inputs/looker-request.json \
  --response /private/run/inputs/dashboard-response.json \
  --directory /private/run/inputs/looker-capture --allow-source-read
```

For a supplied directory, replace `import-api --response ...` with `import-local --source-root /private/run/inputs/supplied`. Offline service identities can be unknown; preserve the file-fingerprint namespace rather than inventing a tenant. Dashboard YAML uses an already approved PyYAML installation with aliases, duplicate keys, unsafe tags, depth and size limits. It is definition evidence, not LookML compilation or effective-user execution.

```sh
python3 /installed/omni-artifact-translator/scripts/looker_capture.py capture \
  --request /private/run/inputs/looker-request.json \
  --directory /private/run/inputs/looker-capture \
  --allow-source-read --allow-source-query --token-stdin
```

Supply the source access token on stdin. **Renders also require the query grant** because dashboard rendering executes queries. Metadata-only capture needs only source-read authority. The wrapper verifies actual source user ID through the fixed user endpoint; a reference label is not impersonation. It never changes dashboards, schedules, actions, workspace mode or PDT rebuild settings.

Retain the returned journal filename and entire capture directory. Resume only the same request/runtime with `--resume`; durable limits and intent prevent automatic replay of an uncertain render or inline-query submission. An unknown submission outcome requires reconciliation, not a new directory to bypass the journal. Requested filters/principal/timezone are distinct from independently observed state.

## Inventory and requirements

```sh
python3 /installed/omni-artifact-translator/scripts/looker_capture.py check \
  --capture /private/run/inputs/looker-capture/capture-000001.json
python3 /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/looker-capture/capture-000001.json \
  --format looker-capture --output /private/run/inputs/looker-inventory.json
python3 /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run prepare \
  --original inputs/looker-capture/capture-000001.json \
  --inventory inputs/looker-inventory.json \
  --website https://customer.example --output contracts/visual.json
```

Use the journal filename actually returned; the example suffix is illustrative. Capture check and requirements creation verify actual local bytes, not only embedded hashes. A valid local envelope does not authenticate its origin.

Other translator formats are explicit: legacy `looker-api`, DMA `looker-canonical` and DMA `looker-adapter`. Both DMA imports require the inspected `--producer-revision` declared by the operator. Do not change `kind` to fit another parser. Generic DMA dashboard-YAML omissions remain unknown-file obligations; use the separate supplied-file path for bounded YAML interpretation.

Review every object before implementation: data visuals, content, tabs, controls, repeated placements, query/Look/merge definitions, actions and unknown objects. Preserve dynamic fields, hidden calculation dependencies, listener exclusions, pivots/totals, limits, order and links. A text tile is not a query; a repeated placement is a separate visual obligation. Unsupported or manual-review treatment does not remove an object. Use explicit `migrate`, `defer` or `exclude` scope dispositions with rationale; exclusions are not migrated content.

Fill route/decision references, metric and query contracts, design parity decisions and required cases. Apply [Omni migration lessons](looker-guidance.md), [Looker dashboard mapping](../../omni-dashboard-designer/references/looker-mapping.md) and [Looker-to-App design](../../omni-app-designer/references/looker-to-app.md). Historical examples inform design; they do not justify skipping content, forcing one pivot chart, deleting by name or using beta import loops.

## Backend cooperation

Use [the cowork contract](../../omni-backend-handoff/references/cowork-contract.md): register original evidence and inventory, freeze source obligations, request only unresolved semantic/physical changes, receive an actual DMA candidate, inspect impact and select the current frontend candidate. Retain independent numerical expectations and unresolved responses. DMA continues to own its approval, validation and finalization gates.

Keep the aggregate 256 KiB selected-input limit. Large sources need dependency-complete slices tied to the frozen inventory, with every excluded/deferred object accounted for. A partial packet never establishes whole-dashboard completeness. Surface returns currently verify one dependency-complete inventory per selected surface; use explicit waves for multiple inventories.

Selecting a DMA candidate does not deploy it. The target baseline separately inspects current Omni model ancestry, Topics and query fields; reconcile that observed state with the selected backend candidate before treating bindings as delivered. Source, requirement or backend candidate drift invalidates affected frontend evidence.

## Dashboard construction

Use the [shared native build/export guide](../../omni-bi-engineer/references/omni-build-export.md) and a typed `analyst_existing_omni_baseline_spec`. Pin `requirements_path`, `payload_path`, `ownership_path`, review reference, and every query binding (`source_asset_keys`, `query_key`, `topic`, exact `query`, `field_ids`). Capture the current baseline with `omni_native.py baseline-capture` before preparing a candidate.

Every migrated Looker control needs an exact existing Omni control binding: native ID/config, config field pointers, affected query keys, scope pointer and retained compatibility evidence. Preserve its config/order. The bounded executor does not invent new control schemas or silently replace interactive controls with static query filters. Unsupported query grammar, new controls, merged-result behavior and custom visuals remain explicit implementation gaps.

Native preparation records ownership and before-state. Execution requires the exact reviewed candidate and authorization reference; it patches only the configured named draft, rechecks semantic/source context, preserves unrelated content and records readback. Unknown writes must be reconciled before any retry. Publishing is separate.

## App construction

Use [the native App contract](../../omni-app-engineer/references/native-app-contract.md). The first adapter edits reviewed HTML regions in an **existing query-backed named App draft**. It preserves existing workbook queries, App settings and inspected native runtime fragments. It does not invent an Omni JavaScript SDK or use mock arrays as live data. Query creation and a new native runtime/starter are separate BI/App engineering tasks using verified current tools.

Prepare an `analyst_app_runtime_contract` recording component-to-query bindings, source-control-to-filter/reset fragments, evidence, and loading/empty/error/restricted/stale/reset behavior. The baseline spec uses `analyst_existing_omni_app_baseline_spec`, `requirements_path`, `runtime_path`, bindings and review reference. The candidate spec uses `analyst_native_app_spec`, baseline/requirements/patch paths, owned region markers and review reference. The patch contains bounded exact `htmlEdits`; settings and query mutations are rejected.

```sh
python3 /installed/omni-app-engineer/scripts/omni_app_native.py \
  --workspace /private/run --target contracts/app-target.json baseline-capture \
  --spec contracts/app-baseline-spec.json --output evidence/app-baseline.json
python3 /installed/omni-app-engineer/scripts/omni_app_native.py \
  --workspace /private/run --target contracts/app-target.json prepare \
  --spec contracts/app-candidate-spec.json
```

After review, use `execute --candidate EXACT_RETURNED_HASH --authorization-ref EXISTING_REVIEW_REFERENCE`; use `reconcile --candidate EXACT_RETURNED_HASH` for an uncertain outcome. App evidence lives under `.omni-app-native`; dashboard evidence remains `.omni-native`. The pinned App API is **experimental** and CLI App commands are **alpha**. This adapter uses the inspected fixed API contract, retaining the installed CLI for supported read/identity operations.

No named-draft App image-export route is qualified here. Retain independent native preview evidence with explicit target/candidate/state identity; do not publish just to get an image or reuse dashboard export evidence. Matching HTML readback does not prove query events, accessibility, focus, responsive layout, stale-response handling or restricted-user behavior.

## Compare, cover and return

Numerical cases bind original result bytes, actual provider/dashboard/element/query identity, definition fingerprint and effective state. Normalize explicit typed JSON rows without losing decimal tokens, null/blank/zero or ordering. Record independent effective filters, persona equivalence, complete population, data/cache timing and source/target mapping. Truncation, unknown state, unsupported pivot/totals shapes or cache mismatch leaves comparison inconclusive. Merged queries are captured as dependencies; automatic merged execution is not supported.

Use `visual_workflow.py compare --spec ... --output ...`, then `coverage --requirements ... --candidate ... --evidence ... --output ...`. Required numerical, visual, interaction, accessibility, access and performance cases remain distinct. Every surface uses its own candidate hash and cases.

Freeze scope and create/check the return through `migration.py freeze`, `return` and `check` as described in [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md). A standalone App uses `analyst_standalone_migration_return_spec` with `surface:"app"`, frozen scope hash, baseline/requirements/candidate/execution-receipt/coverage paths and unresolved items. Standalone dashboard uses the existing specification without the App surface selector. For standalone `both`, use exactly `schema_version:1`, `kind:analyst_standalone_migration_return_spec`, `surface:"both"`, `scope_sha256`, `surface_deliveries` in the shape below, and `unresolved`. It recomputes both proofs against the same frozen scope with no fabricated DMA import. One proof yields an incomplete aggregate; both proofs still retain pending cases and source gaps.

DMA-backed `analyst_migration_return_spec` retains its existing asset/file/QA declarations and adds:

```json
{
  "surface_deliveries": {
    "dashboard": {
      "candidate_path": ".omni-native/candidates/ACTUAL_HASH.json",
      "execution_receipt_path": ".omni-native/executions/ACTUAL_HASH/receipt.json",
      "coverage_path": "evidence/dashboard-coverage.json"
    },
    "app": {
      "candidate_path": ".omni-app-native/candidates/ACTUAL_HASH.json",
      "execution_receipt_path": ".omni-app-native/executions/ACTUAL_HASH/receipt.json",
      "coverage_path": "evidence/app-coverage.json"
    }
  }
}
```

Include only selected surfaces and exact returned paths. The return recomputes baseline, source/DMA selection, candidate, intent/readback and coverage; requirements must match the frozen source obligations. Separate documents are enforced. Missing surface proofs and pending source/QA obligations remain incomplete. Reported lane claims and self-hashed files cannot grant native or business acceptance.

## Local host

`visual_mcp.py` is a local POSIX stdio host. Default tools provide `looker_import_local`, `looker_import_api`, `looker_translate`, `looker_check_capture` and `looker_import_capture`. Connected capture adds startup options:

```sh
python3 /installed/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private/run --looker-python /trusted/python3 \
  --looker-request inputs/looker-request.json \
  --looker-directory inputs/looker-capture \
  --enable-looker-capture --enable-looker-query
```

The host's `LOOKER_ACCESS_TOKEN` goes to the source child through stdin, with a reduced environment. Omni credentials are not inherited by that child. Optional `--looker-token-env` must use a `LOOKER_` variable. A finite `--looker-batch inputs/batch.json` replaces request/directory; it fixes `captures[{capture_id,request,directory}]`, `max_total_requests`, `max_invocations`, schema version1 and `kind:analyst_looker_capture_batch`. Request budgets are reserved before invocation, including uncertain failures.

Configure `--target` for dashboard and `--app-target` for App. Mutation tools require separate `--allow-candidate` / `--authorization-reference` and `--allow-app-candidate` / `--app-authorization-reference` grants. Tool arguments cannot broaden startup authority. Both adapters must target separate documents.

This host does not provision a cloud HTTP connector. Qualify actual Claude/ChatGPT process support, file transfers, discovery, secret handling, interrupted jobs and target execution. Where the account cannot run the local host, use a clearly recorded operator-assisted file workflow.

The connected pilot remains: one selected source scope, representative personas, actual state-bound results, native behavior and business review for every selected surface. Scale only after that evidence exists. No source retirement, schedules, outbound actions or publication is implicit.
