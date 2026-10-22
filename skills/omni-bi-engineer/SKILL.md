---
name: omni-bi-engineer
description: Bind reviewed analyst requirements to Omni topics, workbook queries, dashboard controls and native content candidates while preserving metric and migration behavior.
---

# BI engineer

Own the connection between accepted metrics and functioning Omni content. Consume the analyst contract, scoped semantic catalog, designer specification and migration crosswalk. Work standalone or from the coordinator's bounded packet. Read the [shared contract](../omni-artifact-accelerator/references/contracts.md) and selected [Omni capability](../omni-artifact-accelerator/references/omni-capabilities.md).

For Tableau, follow the [native construction and standalone baseline procedure](../omni-artifact-accelerator/references/tableau-visual-run.md). Preserve worksheet versus placement identities and reviewed filter/calculation semantics. In standalone `reuse_existing`, capture current regular-Topic/model definitions against the exact payload and query bindings; prepare/execute recheck that typed baseline. Missing fields or unsupported query structures return to the model owner. Keep source authorization, draft execution and exports separately scoped; no placeholder DMA catalog or inferred publication.

Inspect existing models/topics/workbooks before creating duplicates. Pin real identifiers and revisions. Reuse governed fields; propose new semantics to DMA or the model owner with precise grain, population and tests. A field label or successful parse is not proof of availability or access.

For Power BI, follow the [Power BI native workflow](../omni-artifact-accelerator/references/powerbi-visual-run.md). Preserve DAX filter context, totals, BLANK/null, source visual roles and dependent slicer/bookmark behavior. Standalone candidates require the typed current model/Topic baseline. Reuse an existing control only with exact inspected configuration, governed fields and affected-query bindings; missing controls or unsupported behavior remain explicit requirements. Send real semantic gaps to DMA without discarding visual obligations or treating a model query as the original visual's result.

For Domo/Sigma inputs, read [migration behavior coverage](../omni-qa-analyst/references/migration-behavior.md). Carry the complete Page/element/query/placement and behavior set, including non-query content, control propagation, personas and operational handoffs. Preserve original behavior separately from an accepted redesign. For Sigma, honor the explicit route and allowed-change scope; direct mode never generates dbt, and dashboard-only Topic reuse requires exact compatible bindings. Missing route or compatibility evidence blocks dependent implementation, not source inspection.

For every query/tile, specify exact fields, grouping, result shape, filters and evaluation order, parameters/defaults, totals, sorts/limits, timezone/currency, drill path, freshness and expected row completeness. Ratios and distinct counts require the correct aggregation scope. Separate filter UI state from row-level access enforcement. Keep hidden columns needed for bindings explicitly documented.

For dashboard candidates, implement supported layout, chart and control settings. Preserve original source IDs and map each source facet to exact/adapted/unsupported/unknown behavior. If a native feature cannot express the source behavior, propose a reviewed adaptation; do not silently substitute an app or remove the feature. Query names, filter listeners and tab references must survive translation without collisions.

For connected migrations, follow [native build and export](references/omni-build-export.md). Use the discovered MCP tools or current document v2 CLI/API schema, preserve source placement-to-target tile identities, and read back/export the actual candidate under matched state. Distinguish draft editing from immediate publication; do not use removed commands or delete-by-name sample builders. Return missing semantics through DMA and leave independently verified frontend results attached to the same migration context.

For Apps, supply the app engineer with a stable query contract and exact workbook/tab bindings, typed values, completeness, errors and allowed parameter domains. Keep analysis logic governed; the renderer owns display and interaction.

Preserve the designer's selected composition and complete chart specification. Return material implementation adaptations with actual native captures for designer review. A newly useful detail view needs a real query and independent analyst/QA expectations, not another rendering of the same row. For net-new tooling and complete presentation replacement, follow [native authoring](../omni-artifact-accelerator/references/native-authoring.md).

Use documented connectors/APIs/CLI/UI within current authorization. Inspect draft/published state and endpoint side effects before any write: some update routes publish. Reconcile conflicts rather than clearing existing drafts. Record payload/diff and returned IDs; reread the actual candidate and compare settings. Do not claim a local JSON file was imported.

Outputs: query contract, field/source crosswalk, native content candidate or explicitly labeled local specification, and validation evidence. Hand independent QA the original settings and expected cases. Stop affected implementation on missing bindings or unsupported security behavior; preserve a reviewable draft and explicit manual steps.

Use [backend cowork](../omni-backend-handoff/SKILL.md) for semantic/physical gaps and returned model changes. Include exact affected bindings and independent expected cases; reconcile returned pins and rerun affected query/behavior checks before wiring the result. An upstream local preflight or supplied acceptance field grants no target-apply authority here.

For Looker, follow [the run guide](../omni-artifact-accelerator/references/looker-visual-run.md). Require the typed current model/Topic baseline and exact inspected control bindings for reuse. Preserve content/placement obligations and unsupported behavior. Supply reviewed workbook query bindings to the App engineer; a missing model capability belongs in the DMA handoff, not in client JavaScript.

For Hex, use the [dashboard/App workflow](../omni-artifact-accelerator/references/hex-visual-run.md) and [experience mapping](../omni-app-designer/references/hex-experience-mapping.md). Bind only the requirements assigned to the selected surface, retaining repeated placements and exact input/filter scope. Share governed metrics across separate documents. Initial App queries and native bridge evidence must be inspected before the App engineer constructs the full body; do not invent a query SDK or hide notebook computation in browser code.
