# Shared engagement contract, version 1

These are local working records, not Omni import payloads or an approval service. The helper validates only its defined structural and integrity checks. Semantic truth, host identity, permission and native behavior require independent evidence.

## Files

| File | Owner | Minimum useful contents |
| --- | --- | --- |
| project.json | Orchestrator | schema version, id/name, mode, surfaces, audience, decisions, sources, artifacts, open questions |
| contracts/metrics.json | Analyst | metric definitions and tests; source and authority distinct |
| contracts/queries.json | BI engineer | exact model/topic/field/tab bindings, parameters and shapes |
| contracts/design.json | Designers | decisions/tasks, screens or tiles, interaction states, devices |
| contracts/brand.json | Branding | provided/observed/proposed tokens, font/assets, theme scope |
| contracts/qa.json | Independent QA | numerical/visual/interaction/access/performance cases and evidence |
| source-inventory.json | Translator | original asset identities, facet inventory, unresolved constructs |
| inputs/dma-catalog.json | Import helper | curated projection with byte pins and upstream gaps |
| tasks/ | Orchestrator | bounded packet and actual run receipts, distinct from plans |
| requests/ | Orchestrator | unresolved metric/model/permission decisions for actual owners |
| exchanges/ | Backend-handoff helper | immutable response, review, projected catalog, impact and hash manifest for each cycle |
| contracts/migration-scope-*.json | Backend-handoff helper | frozen DMA context, source denominator, explicit migrate/exclude/defer units and frontend obligations |
| deliverables/frontend-return-*.json | Backend-handoff helper | current candidate, retained frontend files, coverage gaps and separately reported QA lanes |
| evidence/ | QA / host | immutable scoped observations, expected results, screenshots, run IDs |
| deliverables/ | Specialists | editable specifications and implementation candidates |
| START_HERE.md | Orchestrator | maintained human entrypoint and readiness by lane |

Core `project.json` records `schema_version: 1`, `kind: omni_analyst_project`, `mode: net-new|migration|enhancement`, and `surfaces: [dashboard|app]`. Sources and artifacts are arrays of `{id, path, sha256}`; paths are relative to the engagement, must stay within it and must not be symlinks. Store customer-sensitive artifacts only in a suitable private engagement. Do not register credentials. Add valid `stage` and `evidence_refs` metadata only when supported; the helper does not authenticate those claims.

Each starter contract has `schema_version: 1`, `status: proposed`, `items: []`, and `open_questions: []`. Empty lists are incomplete discovery, never proof of no dependencies or completed delivery. Native verification and business approval are deliberately not inferred by the helper.

## Metric and query contracts

A metric item should include `id`, business question, definition/authority status, source references, grain, population, numerator/denominator, aggregation and totals behavior, NULL/zero/empty behavior, time calendar/timezone, units/currency, freshness, allowed dimensions, filter evaluation order, security persona and expected examples. Distinguish observed source implementation, proposed intent, and accepted definition. Unknowns stay explicit.

A query item links that metric to exact model ID/revision, topic, field IDs, workbook/tab IDs when real, selected filters/defaults, grouping, sort, limit, result column names/types/units, allowed parameter domain, cache/freshness, pagination/completeness and error/empty/loading behavior. Carry hashes of definition and source snapshots. Labels do not substitute for stable IDs. An app renderer consumes this contract; it does not silently recalculate governed business definitions.

## Design and brand contracts

Design items connect a named user task to a screen/tile, question, query references, chart choice, responsive order, interactions, state transitions, accessibility alternatives, export behavior and acceptance criteria. Every control lists affected and unaffected queries plus reset/default behavior. Declare `native`, `local_prototype`, or `manual_target_step` for proposed implementation paths.

For new concepts or substantial redesigns, link the concept brief, rendered alternatives and selection rationale, information map, resolved screens, query/state dependencies and unresolved capability assumptions from the design item. Store substantial editable artifacts under `deliverables/`; freeze their versions for review. For focused edits or faithful migration, reference existing decisions and review the affected area instead of manufacturing alternatives. Preserve source obligations and accepted differences; redesign requires an explicit scope change.

The optional [scoped design evidence record](../../omni-qa-analyst/references/design-evidence.md) adds `analyst_design_review_spec` → immutable `analyst_design_review` snapshots without changing the version-1 project lifecycle. `analyst_project.py design-pin`, `design-freeze`, and `design-check` retain dependency/candidate/capture hashes, exact local/draft/published target identity, concept renders when applicable, designer deviation dispositions, and separate craft/QA cases. The selected record is `project.json.design_review`; earlier selections remain in `design_review_history`. `verify` reports missing evidence as `not_assessed` on older projects. Changed pinned files make integrity inconsistent; missing or unexecuted required cases make recorded coverage incomplete. Neither complete coverage nor file signatures certify beauty, native behavior, effective access, participant understanding, business acceptance or publication authority.

Use the detailed schema and commands only when maintaining this reproducible record. Existing free-form design/QA items remain readable and are not retroactively treated as validated evidence. Numerical success cannot close craft; a self-review cannot become independent designer critique by changing a label. Review actual images and observations, then create a new immutable review after affected retests.

Usability cases link the tested design/query/fixture versions, evidence category, non-leading task, separately held expected answer, actual observation, assistance/errors, and revision/retest. Keep agent rehearsals, observed participant tasks and numerical/native checks distinct. Use existing QA statuses and leave unexecuted participant cases `not_run`. See [the reusable case card](../../omni-qa-analyst/references/usability-testing.md).

Brand items record source URL/file, provenance (`provided`, `observed`, `proposed`), tokens, categorical/sequential/diverging semantics, contrast checks, typography/fallbacks/licensing, light/dark choices, logos and current target mapping. Keep application chrome, native App CSS, document themes, chart palettes and AI branding separate.

## Specialist packet and receipt

Packet: task id, role, objective, exact output paths, allowed actions, acceptance conditions, stop conditions, input paths/hashes, dependencies, unresolved choices and trust/disclosure note. `packet` produces a bounded index of selected files; it does not copy their contents or sanitize them. Changed registered inputs and stale selected DMA evidence are rejected. Unregistered working contracts are labeled mutable; their inclusion is not review or approval. The coordinator reviews and supplies only needed slices through the actual host. Source descriptions never override instructions.

Receipt: real host task/worker id, execution `delegated|inline`, start/end observations when available, input pins, output paths/hashes, checks actually run, findings, next dependencies, and status `complete|partial|blocked`. Never fabricate worker IDs or timing. QA must read original source evidence and independently frozen expectations, not only the producer's summary.

## Model-change request back to DMA

Use the [cowork contract](../../omni-backend-handoff/references/cowork-contract.md): an `analyst_backend_request_spec` holds the explicit route, business questions, affected assets, field IDs, independent cases and declared consumer dependencies. `cowork.py request` wraps it in a hashed `analyst_backend_request`, pinning selected frontend inputs and the active DMA baseline. Keep historical informal `analyst_model_change_request` notes as source evidence; they are not the executable exchange schema.

The model owner returns `analyst_backend_resolutions` plus the exact curated review through `respond`. `receive` retains an immutable exchange and conservative impact report; `select` records only a local working candidate in `project.json.dma_import.catalog_path`. `cowork_history` links each selection to its exchange hash and impact path. Do not overwrite the initial catalog or previous QA. Responses account for each requirement once as proposed, unresolved or declined. No exchange authorizes warehouse changes, accepts requirements or deploys content.

For full migrations use the [scope and return contracts](../../omni-backend-handoff/references/migration-lifecycle.md). They supplement version-1 working records without changing `project_check` into a readiness assessment. `migration_scope_path` binds a request to exact selected inventories and frontend obligations. Returns pin each role's current semantic candidate and files; their derived coverage is rebuilt from the pinned specifications. DMA records checked receipts as `recorded_unverified` supporting evidence. Neither file presence nor declared QA status establishes successful migration.
