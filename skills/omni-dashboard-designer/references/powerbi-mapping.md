# Power BI report mapping

Use with [chart mapping](migration-chart-mapping.md), the [source contract](../../omni-artifact-translator/references/powerbi-source-contract.md) and [run guide](../../omni-artifact-accelerator/references/powerbi-visual-run.md). This is a review workflow for ordinary PBIR reports, not a general DAX, custom-visual or PBIX compiler. Vendor references were checked October 21, 2026; the rules below are package recommendations unless a linked source says otherwise.

## Preserve identity and the complete report

Use internal page and visual names, scoped by report and definition fingerprint. Captions are presentation labels: two pages can share a caption and two different pages can contain the same visual name. An offline PBIR import can have null service IDs and a `definition:<fingerprint>` namespace; do not invent workspace/report IDs. Preserve the original file path and JSON locator alongside native IDs.

Inventory report/page/visual definitions independently of the semantic reader. Keep query-bearing visuals even when their type or query role is unsupported. Textboxes, shapes, images and buttons remain content obligations; slicers remain control obligations. Preserve groups, positions, hidden states, mobile layouts, report/page/visual filters, interactions, bookmarks, themes and static resources. Unsupported properties remain in the raw source and have explicit review gaps. A missing requested object remains an obligation. Microsoft's [PBIR structure documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report) describes the separate definition files; the parser's actual limits are in the source contract.

| Source behavior | Required mapping decision and proof |
| --- | --- |
| Bar/column, line, card/KPI and table | Establish fields, aggregation, grain, sort, categories, axis scale, units and independent totals before selecting a compatible native chart. A recognized chart family is not automatic parity. |
| DAX measures, calculation groups, implicit aggregation and field parameters | Preserve raw expression and evaluation context. Route reusable semantic gaps to the BI engineer and DMA. Do not replace an unresolved calculation with a similarly named field or assume visible-row sums equal a context-dependent total. |
| Slicer, synced slicer, cross-filter and cross-highlight | Record selected/default/reset state, source and target visual IDs, interaction mode and affected fields. A static query filter does not replace the control. The current executor can reuse inspected compatible controls with exact bindings; new or changed controls require an explicit operator build/validation path. |
| Bookmark, button, navigation, drill-through and tooltip page | Record the action trigger, destination, retained/reset context and visibility. Treat hidden dependent pages as scope. A screenshot cannot establish that the action works; keep external URLs inert during extraction. |
| Matrix/pivot, subtotal, grand total, BLANK/null and missing categories | Preserve row/column grain, sort and subtotal identity. Keep null distinct from zero and an absent row distinct from a present blank. Never silently drop totals or fill missing categories. |
| Custom/R/Python visuals, maps and dynamic formatting | Retain configuration and rendered evidence when available. Separate target capability, semantic behavior and interaction gaps. Native Omni dashboard remains the selected surface unless the user explicitly chooses another. |
| Hidden/grouped content, mobile layout, logos and theme | Keep visibility, parent group, intended reading order, meaningful colors and accessible labels. Improve spacing, contrast and narrow-screen hierarchy through a recorded design decision; source coordinates are evidence, not a pixel-perfect target requirement. |

For each facet record parity `exact`, `adapted`, `unsupported` or `unknown`; separately record implementation route `native`, `custom` or an explicitly selected alternative. A custom picture cannot silently satisfy a required native drill. Use the shared chart guide for current Omni capability references.

## Bind the rendered state before comparing

An ExecuteQueries result is a model query, not proof of the visual's actual filter, bookmark, locale, timezone or access context. The capture records requested state separately from observed state. Require independent value and render observations plus complete-result evidence before a numerical pass. Preserve the original response bytes and an explicit normalization profile, including currency code, null mapping, date format, decimal/group separators and ordering. Currency conversion is not supplied. The [ExecuteQueries contract](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries) documents endpoint limits and response errors; successful HTTP transport does not establish complete rows.

Export state has its own restrictions. Personal bookmarks and persistent filters are unsupported by the documented API; a single-visual export does not support the same bookmark option as a page export. Retain source capture gaps rather than claiming an unsupported state was applied. See [Power BI export behavior](https://learn.microsoft.com/en-us/power-bi/developer/embedded/export-to). Administrator/source-author exports do not establish restricted-viewer RLS or OLS parity.

## Review card: familiar source, clearer candidate

```yaml
source: {page_id: ReportSectionOps, visual_id: available_by_site}
task: Find sites with low available stock, then inspect their exceptions
source_meaning: Available units by site; East filter; source sort retained
implementation_route: native
parity: {numbers: unknown, appearance: adapted, drill: unknown}
proposed_change: Use horizontal bars and direct unit labels for long site names
semantic_effect: None intended; independent aggregation and population checks pending
controls: Exact existing Site control binding required; reset and cross-filter cases not run
brand: Reuse approved product palette; website observation is not asset-use permission
acceptance: Default/changed/reset states, zero/BLANK, totals, drill and restricted persona
status: Local candidate specification; no native or business acceptance
```

Keep the faithful baseline and improvement ledger separately reviewable. Reuse the known company website answer; if absent, ask for the URL and approved logos, fonts and guidelines through the [brand contract](../../omni-branding/references/brand-contract.md). Assets require a recorded source and usage permission. QA owns independent expected results and observed outcomes. A locally valid mapping does not establish publication, native behavior or customer acceptance.
