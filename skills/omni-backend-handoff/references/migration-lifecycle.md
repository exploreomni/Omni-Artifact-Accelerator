# End-to-end migration coordination

Use this workflow when the selected delivery includes the backend and a native dashboard or App. It connects saved work; it does not automate source acquisition, native conversion or acceptance. The host orchestrator dispatches specialists and owns the shared decisions. DMA owns its model workflow and finalizer. The source migrator retains its capture, route and release controls.

## Start or resume one domain

1. Reuse the original engagement, selected domain, source platform, target, decisions and authorization. Select a bounded pilot before scaling. Preserve DMA's `model_only`, `model_semantic`, `full_dashboard` and assessment execution mode. A semantic-only engagement may inform an independent frontend project without acquiring a new DMA obligation. Register an integrated frontend obligation only for explicitly selected `full_dashboard` scope. An App must also be an explicitly selected frontend surface; DMA's dashboard checks do not qualify Apps.
2. Capture through the source owner; translate the selected exports. Retain original IDs, occurrences, formulas, filters, interactions, access, unsupported features and source hashes. Compare the supplied inventory to an independent source listing. A complete disposition of an export does not prove a complete export.
3. Export a readable DMA context using `dma_frontend.py export` from this skill's scripts directory and an explicitly trusted DMA scripts path. See the package's optional DMA integration guide for the commands. It reads saved state, preserving engagement/revision, source/catalog/target/runtime/discovery inputs, selected domain and design. It does not invent a migration route. A later `record` refreshes local source assessment and adds evidence revisions through DMA's existing APIs; it does not run customer SQL or advance stages.
4. Freeze the frontend obligation below, with the exact context copied into `inputs/`. Register it with DMA as `analyst_frontend_scope`. The record remains `recorded_unverified`. A standalone frontend uses a null backend context and does not register a DMA obligation.
5. Import a real curated semantic review when one exists. Assessment and provisional design may start without it; keep candidate-dependent work unresolved. Never fabricate `SEMANTIC_REVIEW.json` for assessment. When a real model is needed, DMA performs its normal design, implementation, semantic and validation stages.

## Freeze a complete supplied denominator

Author a scope specification inside the frontend engagement. Example values below are placeholders for existing evidence, not source IDs to reuse:

```json
{
  "schema_version": 1,
  "kind": "analyst_migration_scope_spec",
  "scope_id": "sales-r1",
  "decision_reference": "the-existing-engagement-scope-decision",
  "backend_context_path": "inputs/dma-context-r1.json",
  "inventory_paths": ["inputs/source-inventory.json"],
  "independent_source_listing_path": "inputs/source-listing.json",
  "units": [{
    "unit_id": "sales-overview",
    "inventory_path": "inputs/source-inventory.json",
    "asset_keys": ["exact-translator-asset-key"],
    "disposition": "migrate",
    "rationale": "Selected pilot business decision",
    "frontend_asset_ids": ["sales-overview"],
    "surfaces": ["dashboard"]
  }]
}
```

Every supplied inventory asset appears in exactly one unit. Several source assets can form one unit. A unit maps its frontend IDs to each listed surface; use the same logical ID across surfaces only when both implementations are required. `exclude` and `defer` require rationale and empty frontend IDs/surfaces. Excluded and deferred assets remain visible; deferral is not delivery. Occurrence-based `asset_key` identifies this exact inventory version; retain its original native identity and path separately. A reordered or replaced inventory requires a new scope version, not silent remapping.

`backend_context_path` may be null for standalone work. The independent listing is optional for preliminary work; its absence is a reported gap. Its contents require the translator/QA owner's reconciliation—file presence is not proof of completeness.

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/migration.py freeze \
  --project /absolute/frontend-run --spec contracts/scope-spec-r1.json \
  --output contracts/migration-scope-r1.json
```

The create-only record pins the specification, inventories, independent listing and DMA context. It retains the source identity crosswalk, route declarations, unknowns and dispositions. The host verifies actual route/allowed-change decisions against trusted session evidence; a self-hash does not authenticate a decision maker.

## Work across the boundary

Use the existing `cowork.py request → respond → receive → select` cycle. Add `migration_scope_path: "contracts/migration-scope-r1.json"` to requests for this scope. That binds requested frontend IDs and source inventory selection to the frozen obligation. Without a scope, the helper discovers registered/selected source inventories. For multiple versions, explicitly name the current `source_inventory_paths`; retain older versions for comparison. A contradictory platform or Sigma direct/warehouse route fails before request creation. `unselected` permits discovery and `reuse_existing` narrows work to the exact baseline; neither authorizes a route switch.

Reuse the backend engagement and selected domain; do not launch an unrelated model rebuild for every request. The backend supplies one resolution per requirement and an actual curated candidate. The frontend keeps prior evidence, selects the new local baseline and rechecks affected consumers. Both top-level return and each asset's role return carry the exact semantic-review byte hash. Old query/design/QA files cannot satisfy the new return just because they still exist: revise their candidate-bound return after doing the relevant checks.

Provisional design, branding, storytelling and motion work can continue independently of unresolved data bindings. Metrics stay in the governed model/query layer. Operations, schedules, alerts, writeback and other side effects retain explicit owners and evidence.

When backend source, design or selected-domain material changes, export a new context and freeze/register a new frontend scope. Reuse unchanged source dispositions deliberately. Ordinary evidence/task revisions do not require a new context. Do not refresh hashes to hide drift or silently change the requested scope.

## Return artifacts and gaps together

Author `analyst_migration_return_spec` with `schema_version: 1`:

- `scope_sha256`: the frozen scope's self-seal.
- `candidate_review_sha256`: exact current semantic-review byte hash, or null for assessment without a baseline.
- `assets`: one row per `(asset_id, surface)` with `unit_ids`, the role's `candidate_review_sha256`, and `files` containing the four lists `query`, `design`, `implementation`, `qa`. Paths point to retained files inside the engagement; use immutable versions. Empty lists report incomplete candidate coverage. Query contracts and QA evidence must identify their actual inputs, independent expectations, worker and run details; the helper does not infer content correctness from a file name.
- `lanes`: rows with `lane`, `status`, `evidence_paths` and `rationale`. Lanes are `query_binding`, `numeric`, `interaction`, `access`, `visual`, `narrative`, `performance`, `native`, `operations`, `business`. Status is `pass`, `fail`, `blocked`, `not_run` or `not_applicable`. Pass/not-applicable claims require retained evidence; all claims remain `reported_unverified` here. Declare genuinely inapplicable lanes with evidence and rationale; never manufacture a test run to fill the record.
- `unresolved`: explicit remaining decisions or work. Empty means the producer reported none, not proven acceptance.

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/migration.py return \
  --project /absolute/frontend-run --scope contracts/migration-scope-r1.json \
  --spec contracts/frontend-return-spec-r1.json --output deliverables/frontend-return-r1.json
python3 /absolute/skills/omni-backend-handoff/scripts/migration.py check \
  --project /absolute/frontend-run --receipt deliverables/frontend-return-r1.json
```

Incomplete returns are useful: they preserve missing assets/files, deferred units, source gaps, missing/failed/unrun lanes and unresolved backend responses. `candidate_coverage: complete` means only that every selected frontend obligation has retained candidate files against the selected baseline. It never means content correctness, native validation, full migration completion or business acceptance. A changed pinned source, specification, output file or semantic baseline rejects stale evidence.

Record the checked return in DMA as `analyst_frontend_return` using the same context and previously registered scope. The adapter rechecks both packages' current material before using DMA's supporting-evidence API. Nothing in this path advances DMA stages or clears its delivery-assurance lanes.

### Looker surface evidence

Looker returns additionally require `surface_deliveries`, keyed by every selected `dashboard` or `app`. Each value has exactly `candidate_path`, `execution_receipt_path`, and `coverage_path`. The helper derives the current baseline and requirements from the candidate, rechecks original files/current DMA selection, validates retained intent/readback and recomputes coverage. Each surface currently covers one dependency-complete inventory; its migrated requirement keys must equal the frozen scope's source obligations. Missing surfaces, declared unresolved work, missing/failed QA, deferred units and retained source-inventory gaps keep coverage incomplete. The local return does not clear original parser warnings; it retains them for independent review. Other platforms can opt into the same stronger proof contract; their legacy file-only returns remain backward compatible.

Use separate target documents for dashboard and App. The App verifier accepts only `.omni-app-native` candidates/receipts; the dashboard verifier accepts its own native contract. Swapped receipt paths, stale backend selection and changed source evidence reject the return. Surface readback is retained execution evidence, not authentication, interaction/access verification or business acceptance. Standalone App returns use `analyst_standalone_migration_return_spec` with `surface:"app"`. A standalone aggregate uses exactly `schema_version:1`, that same kind, `surface:"both"`, `scope_sha256`, the `surface_deliveries` map and `unresolved`. It requires a frozen both-surface scope and no DMA import; one surface's proof leaves the other incomplete. Both proofs retain unresolved source and QA obligations.

The [Looker run guide](../../omni-artifact-accelerator/references/looker-visual-run.md) gives the executable workflow and exact App boundary. The first App helper preserves an existing inspected native runtime and governed workbook queries while applying reviewed HTML edits; new query/runtime construction is separate work.

## Integrated delivery and cutover

Maintain one human review entrypoint linking source coverage, backend delivery, frontend artifacts and lane-specific evidence. Include original-ID and behavior crosswalks, accepted redesign decisions, unresolved requirements, operational ownership, rollback/cutover and source-retirement criteria where in scope. The DMA owner adds inert frontend summary/manifest/crosswalk files to its normal review manifest and runs its existing finalizer. Keep executable App assets in the frontend delivery; link their version/hash and dependency instructions rather than relabeling them to bypass DMA's file policy.

Run a target pilot with independent numerical, filter/interaction, effective-access, visual/accessibility, performance and operational checks. Obtain actual business review of the selected version. Only those owners' verified evidence can establish delivery and acceptance. Scale domain by domain, tracking shared-model impact. Publication, cutover and source retirement follow the existing authorized release workflow; a local receipt is not that authority.
