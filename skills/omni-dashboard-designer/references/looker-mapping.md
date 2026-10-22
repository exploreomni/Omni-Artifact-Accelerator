# Looker dashboard mapping

Use with [chart mapping](migration-chart-mapping.md), the [source contract](../../omni-artifact-translator/references/looker-source-contract.md) and [run guide](../../omni-artifact-accelerator/references/looker-visual-run.md). These are package recommendations. Source acquisition and local checks do not establish native behavior, effective access or acceptance. The approved implementation plan records the official references and their review date.

## Preserve analytical tasks and the denominator

Choose the native dashboard, native App or both explicitly. Keep the source tile, query/Look, tab, layout and placement identities, scoped to the source instance and dashboard. A missing service identity uses a definition fingerprint; captions never become service IDs. Repeated placements are separate composition obligations over the same query. The App lane may reorganize those tasks into screens; it does not silently remove the dashboard lane when both were selected.

Retain every query tile, text/Markdown/image/button, control, placement, tab, custom/unknown element and operational dependency. Query definitions are dependencies, not duplicate charts. Text and nonquery placements do not need invented numerical queries. A merged/custom query tile still needs numerical and behavioral evidence or an explicit scope decision. The reader preserves unsupported properties in the original source; structural enumeration does not interpret those properties.

Record presentation treatment (`preserve`, `rebuild`, `redesign`, `manual_review`, `unsupported`, `out_of_scope`) separately from executable scope (`migrate`, `defer`, `exclude`). Manual review or unsupported does not complete an obligation. A defer/exclude needs the reason and decision reference; report it separately from migrated scope. Native versus custom implementation and exact/adapted/unsupported/unknown parity are independent decisions.

| Source behavior | Mapping and evidence required |
| --- | --- |
| KPI, bar/column, trend, table | Bind exact model/Explore fields, grain, aggregation, sorts, units, axes and category population. Select the target chart after those choices; a familiar shape does not prove equivalent numbers. |
| Look-backed, inline and result-maker queries | Preserve the actual resolved query and source ID. A result-maker ID is not a merge-query ID. Keep hidden computational fields and filter exclusions even when they are not displayed. |
| Dynamic fields, table calculations, pivots and totals | Preserve original expression strings, calculation order, row/column grain, null/blank/zero, total semantics and limits. Classify with the analyst and DMA before choosing a semantic, workbook or expressly selected App calculation. The first numeric normalizer handles explicit flat result profiles; pivots and totals retain a separate reconciliation gap. |
| Dashboard filters and listener exclusions | Record default/changed/reset values, intended query targets, fixed query restrictions, listener names/fields and explicit exclusions. Reuse only inspected compatible controls with exact field/query/config bindings. Static query filters are not a working control. |
| Drill links, navigation, buttons and actions | Retain source trigger, destination and retained/reset filter context. Treat a required drill as behavioral scope. URLs, HTML and source action code stay inert during extraction; outbound actions require their own authorized implementation. |
| Tabs, layout components and repeated tiles | Preserve IDs, reading order, groupings and each placement. Keep a source layout baseline alongside deliberate spacing, density or responsive improvements. Missing tabs or components remain visible acquisition gaps. |
| Custom visual, merged results, Liquid/inheritance, embedded content | Retain evidence and dependencies. No generic compiler, custom code execution or automatic merged-result equivalence is provided. Choose a supported faithful route or an explicit incomplete/deferred/excluded disposition. |
| Folder access, schedules, alerts and embeds | Inventory separately. A source author's results or dashboard screenshot cannot prove restricted-user access or operational cutover. No automatic publication, sends or source retirement. |

## Bind data and appearance to the same state

Looker's [query execution interface](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Query/run_query) and [dashboard render interface](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/RenderTask/create_dashboard_render_task) are separate evidence sources. A query run is not proof that the rendered tile used that query's effective filters, principal, cache or production/development context. A dashboard/tab PNG is not a per-tile export.

Require a source case capture and exact element/query/state association. Numerical comparison needs independently recorded value and render observations, query-state reference, equivalent population/persona, timezone/locale, cache/data-time context and explicit complete-result evidence. False, partial or unknown completeness cannot pass. Row/column truncation and query errors remain failures/gaps even if HTTP succeeded. A local pass says only that supplied results and recorded context matched.

`json_bi` normalization is explicitly profiled: raw file hash; rows pointer; object or JSON-string row encoding; scalar or `{value: ...}` cells; exact header-to-column mapping; typed null rules; decimal/group separators; currency code and percentage rules. The [JsonBi type](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/types/JsonBi) describes metadata and string rows; actual response shape must be observed. Synthetic fixtures qualify the parser, not every native response variant. Decimal tokens are preserved as exact strings in derivatives. Never substitute formatted values for typed values or silently discard totals/pivots.

## Review card: familiar, clearer, accountable

```yaml
source:
  instance: supplied source origin
  dashboard_id: inventory::exceptions
  element_id: tile-kpi
  placements: [place1, place2]
task: Identify stock exceptions and inspect their causes
source_behavior: Site default, reset and explicit listener exclusions retained
surface: dashboard
implementation_route: native
parity: {numbers: unknown, appearance: adapted, filter: unknown, drill: unknown}
change: Direct units and clearer comparison label; retain the source KPI definition
semantic_effect: None intended; source calculations and totals still require review
controls: Existing Site control needs exact binding and native reset/propagation evidence
branding: Reuse approved palette, logos and fonts; website-derived suggestions need provenance
scope: migrate
status: Reviewable candidate specification; no native/business acceptance
```

Reuse prior brand answers. If absent, ask for the company website URL and approved logos, guidelines, fonts and reusable images; record provenance and usage rights through the [brand contract](../../omni-branding/references/brand-contract.md). Keep the faithful baseline and improvement ledger separately reviewable. Independent QA owns expectations, numerical reconciliation, interactions and access evidence; publication remains a separate action.
