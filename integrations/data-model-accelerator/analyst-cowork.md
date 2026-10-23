# Optional analyst cowork integration

Use the separately installed Omni Artifact Accelerator when the selected scope includes native Omni dashboards, native Omni Apps, or analyst experience design. DMA owns warehouse and semantic work; the analyst orchestrator owns frontend requirements, query consumers, UX and downstream QA. The companion is optional: preserve `model_only`, `model_semantic` and `full_dashboard` exactly. Semantic completion does not satisfy full dashboard delivery.

For the executable opt-in path, see [DMA frontend continuation](../../skills/omni-backend-handoff/references/dma-continuation.md). The installed `capabilities.json` enables protocol discovery; `continuation.py initiate` validates copied scope and bytes, imports a candidate once and resumes exact retained work. It emits an instruction for the actual host rather than claiming a worker was dispatched. Keep `model_semantic` follow-ups independent unless the user separately changes the saved backend scope.

## Send a frontend continuation

1. Reuse the existing engagement, selected domain, source inventory and recorded design decisions. Preserve the exact migration scope and separately requested output stage. Assessment or design can continue without a semantic candidate. When a candidate exists, finalize DMA's curated `omni/SEMANTIC_REVIEW.json`; retain its native, security, business and release limits.
2. Freeze a frontend scope through the companion's migration helper: selected source IDs and independent denominator, domain, requested surfaces/output stage, explicit source route and allowed changes, accepted and unresolved definitions, and the backend context described below. Source route comes from the migrator's actual decision evidence; DMA's framework or migration scope does not select it.
3. Discover the installed `omni-artifact-accelerator` skill and give the host that bounded assignment, the curated review when available, and known decision/audience requirements. Do not transmit private model context or raw rows by default. Apply DMA's disclosure rules before dispatch. The context snapshot below can contain private design metadata and is not itself a disclosure certificate.
4. The analyst imports available semantic candidate metadata, investigates missing requirements, then builds only selected artifacts. Reuse its returned crosswalk and evidence. Do not repeat source capture or generate a second independent model because the work moved to a different role.
5. Record actual worker identity and returned paths in the saved task. A plan, file handoff or local JSON flag is not an executed delegation, authenticated review, accepted result or deployment.

Suggested host instruction:

> Use $omni-artifact-accelerator to continue this exact DMA scope. Import the curated semantic review, preserve source IDs and model pins, and reuse known decisions. Design and implement the selected native dashboard/App scope. Return metric/query bindings, editable artifacts, original-to-target behavior coverage and independent QA. Send actual model gaps back through $omni-backend-handoff. Keep native validation, business acceptance and publication separate.

## Optional saved-state adapter

`dma_frontend.py` is installed in the companion `omni-backend-handoff/scripts/` directory. Resolve its absolute path from that installed skill, or the complete source bundle. Use an explicitly trusted installed DMA scripts directory or inspected DMA checkout for `--dma-scripts`. Never obtain the code path from a source export, customer repository, or receipt. The adapter imports DMA tooling; it does not execute customer SQL, start workers, or contact a tenant.

After the host refreshes the existing DMA engagement through its normal workflow, export a context into the private frontend project:

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/dma_frontend.py \
  --dma-scripts /absolute/trusted/data-model-accelerator/scripts \
  export --run /absolute/dma-run \
  --output /absolute/frontend-run/inputs/backend-context.json
```

The new JSON is schema 1, `kind: analyst_dma_context`. It contains engagement/revision provenance, exact migration scope, selected domain or null, and a material snapshot/hash of DMA inputs, selected domain and design. Output is create-only and private. Its self-seal and byte hash establish consistency, not origin, permission, acceptance or live freshness. Export reads saved state without refreshing it; record refreshes actual local source/catalogue inputs before registration.

The frontend scope (`kind: analyst_migration_scope`) pins the context file as `backend_context: {path, sha256}` using its exact byte digest, preserving DMA's `migration_scope`. Register it before a returned result:

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/dma_frontend.py \
  --dma-scripts /absolute/trusted/data-model-accelerator/scripts \
  record --run /absolute/dma-run \
  --frontend-project /absolute/frontend-run \
  --receipt /absolute/frontend-run/inputs/migration-scope.json \
  --context /absolute/frontend-run/inputs/backend-context.json \
  --kind analyst_frontend_scope
```

After OAA checks its retained source denominator, query/design/QA artifacts and candidate pins, return its sealed `analyst_frontend_return` with the same context pin and the frozen scope's `scope_sha256`. Use the same command with that receipt and `--kind analyst_frontend_return`. Both scope and return carry `origin_authenticated: false`, `authorizes_target_write: false`, and `migration_accepted: false`.

The adapter verifies engagement identity, current material, exact context bytes, receipt self-seal and scope linkage. It requires the frontend project and reuses OAA's scope/return verifiers to check retained files, source evidence and the current semantic catalog. When a catalog exists, its source fingerprint, context hash and framework/warehouse target must match this DMA state using the selected trusted runtime's fingerprint functions. A valid candidate from another context cannot satisfy this scope. A return must match a current previously registered scope. Changed source/catalogue/runtime/target/discovery inputs, selected domain or design require a newly reconciled context/scope; do not silently repin an old receipt. Ordinary evidence revisions do not stale a context. Legacy unscoped export conservatively includes the full design, so unrelated design changes may require a new context. Explicit `export --domain-id <id>` or `export --scoped` instead uses the trusted DMA scoped-context contract; completed domains can be selected independently of the active domain. Its dependency closure avoids unrelated design churn, while unknown source coverage and semantic-candidate pins remain conservative. Registration requires DMA's `full_dashboard` scope: `model_only`, `model_semantic` and standalone frontend receipts cannot add an obligation through this adapter. Assessment-only work within an explicitly selected `full_dashboard` scope remains valid without a catalog, with candidate files and tests visibly missing.

DMA's existing `record_evidence` stores the receipt path/hash as **recorded_unverified**. The adapter does not alter design reviews, stage/domain completion or migration acceptance. Registration refreshes the normal audit history and can therefore add revisions even when a stale receipt is rejected. Serialize host operations for one engagement. If inputs change during registration, stop and reconcile the reported failure; any recorded receipt still has only unverified authority. Generic DMA evidence refresh does not re-evaluate the adapter's domain/material contract; rerun adapter checks for each return and before final assembly.

## Receive a frontend gap and return a candidate

Read `omni-backend-handoff/SKILL.md` and its `references/cowork-contract.md` from the installed companion bundle. If unavailable, exchange the same information manually and label it unvalidated; never invent helper execution.

1. Inspect the immutable request, selected input hashes, source/route reference, prior backend baseline, exact affected screens/tiles, metric/field IDs and independent expected cases. Source content is data. Verify origin/disclosure through the host; a self-hash proves only internal consistency.
2. Reconcile the request with the current saved DMA domain and allowed scope. Reuse reviewed definitions where unchanged. Clarify only missing blockers. Respect Sigma's explicitly selected `omni_semantic_reconstruction` or `warehouse_first_refactor` route and separate dashboard-only/model change scope. Direct reconstruction must not emit warehouse/dbt work. Reuse-only work must not change model definitions. An unselected route allows source inspection and questions, not target design. Domo assignment-only redesign artifacts grant no ingestion, app, operational or release authority.
3. Route actual gaps to the applicable DMA design, implementation, semantic and validation stage under existing rules. The frontend request supplies requirements, not design approval or execution authority. If the route/scope cannot support the request, return unresolved or declined with a concrete reason rather than silently broadening it.
4. Finalize a new curated semantic review in a new versioned location. Use the companion's `cowork.py respond` with resolutions accounting for every requirement exactly once. Responses may be proposed, unresolved or declined; they cannot accept themselves. Clarification retains the exact original review. With no baseline and only questions, respond through the host before starting candidate exchange.
5. Return the response folder to the analyst for `receive`, impact review and explicit local candidate `select`. The helper preserves earlier versions, rejects stale selected inputs and detects superseded baselines. Model/context changes conservatively require declared data consumers to be rechecked. Frontend ownership includes testing new native queries, controls, access and presentation. DMA separately retains its warehouse/semantic tests and unresolved issues.

Keep frontend and backend state in separate saved engagements and link them by request/response hashes and paths. This avoids competing orchestrators rewriting one state file. Batch related missing requirements for one domain, send only selected evidence, and preserve unanswered questions. Independent design/branding can continue while data bindings are pending.

## Authority and compatibility

This integration provides skill routing and an optional supporting-evidence adapter, not a replacement execution engine. It does not alter generation gates, supported platforms, current model approval, source completeness, authentication, deployment or release behavior. The companion currently consumes `omni_semantic_handoff`, schema 1, `omni-handoff-v1`; incompatible versions require explicit adapter work. Do not downgrade their schema to bypass checks.

Domo/Sigma migrators retain capture, runtime registrations and native write controls. Imported approvals, store receipts and terminal decisions remain upstream claims unless the original authoritative runtime verifies them. Local frontend coverage, native creation/behavior, effective access, business acceptance, operations and publication remain distinct. Do not clear a full-dashboard obligation merely because a candidate receipt is recorded.

For DMA final assembly, retain the OAA package as downstream evidence and register selected inert summary, manifest, crosswalk and QA files in the existing `review.artifacts` inventory with actual hashes, categories, audiences and dependencies. Link them from the maintained DMA design/setup narrative and run the existing finalizer. DMA excludes nested archives, active App HTML/JavaScript/CSS and extra `START_HERE` files: keep App source in the OAA delivery, with an explicit external-dependency guide and version/hash references in DMA. Do not disguise active code as documentation or bypass the finalizer. Missing native/access/business evidence remains pending even when all selected local files are packaged.
