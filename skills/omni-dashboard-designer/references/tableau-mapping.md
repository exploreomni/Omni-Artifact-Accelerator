# Tableau dashboard mapping

Use with [chart mapping](migration-chart-mapping.md) and the [Tableau run guide](../../omni-artifact-accelerator/references/tableau-visual-run.md). This is a reviewed mapping workflow, not an automatic Tableau chart compiler. Official references were checked October 21, 2026; qualify the selected source and Omni versions.

## Preserve analytical meaning

Keep worksheet definitions and their dashboard placements separate. The same worksheet can appear repeatedly, including inside different device layouts. Preserve each placement's control scope, parent container, visibility, size intent and navigation context. Native XML paths are scoped to a definition hash; a caption is not a REST view identifier.

| Tableau behavior | Required decision and proof |
| --- | --- |
| Context filters, ordinary dimension filters and FIXED expressions | Preserve the population at each stage. Check totals before and after each relevant filter; do not replace a FIXED expression with a normally filtered aggregate without an explicit semantic decision. |
| Table calculations | Retain addressing, partitioning, sort, restart behavior and densification assumptions. Compare ordered rows as well as values. A reusable business metric belongs with the model owner; a calculation dependent on the view needs an explicit frontend mapping. |
| Parameters and parameter actions | Record type, domain, current/default value, source selection and clearing behavior. Requested API parameters remain unverified until source evidence confirms their effect. |
| Filter/highlight/set/URL/navigation actions | Record trigger, source and target sheets, mapped fields, clearing behavior and execution order. Static screenshots do not close action cases. Keep external URLs inert during extraction. |
| Nulls, missing periods, subtotals and totals | Retain distinct meanings. Never silently turn blank strings into NULL, drop subtotal rows, fill missing dates or equate a sum of visible rows with a differently scoped total. |
| Hidden sheets, custom views, device layouts and dynamic visibility | Preserve the obligation even when the REST listing omits it. Require separate evidence or an explicit deferred/unsupported disposition. |

Tableau documents its [order of operations](https://help.tableau.com/current/pro/desktop/en-us/order_of_operations.htm), [table calculations](https://help.tableau.com/current/pro/desktop/en-us/functions_functions_tablecalculation.htm) and [actions](https://help.tableau.com/current/pro/desktop/en-us/actions.htm). Apply these as semantic checks; no arbitrary expression execution is supplied by this package.

## Design the first native candidate

Start with bar, line, KPI and table specifications whose fields, aggregations and behaviors have compatible governed bindings. Preserve source terminology, category order, comparison periods, units and color meaning. Dual axes, maps, reference lines, custom shapes, extensions and writeback require their own capability-backed mapping; retaining their XML does not establish target support.

Keep the faithful baseline and proposed improvements separately reviewable. Improve hierarchy, spacing, labels, contrast and narrow-screen order against the user's tasks. Record each material change, its semantic effect, rationale and decision reference. Source coordinates supply layout evidence; they do not prescribe target pixel coordinates.

Reuse the existing company website answer. If absent, ask: **“What is your company website URL, and are there approved brand guidelines, logos or fonts we should use?”** Branding records observed site patterns separately from approved tokens, with source and usage permission for assets. Follow the [brand contract](../../omni-branding/references/brand-contract.md); broad internet-image discovery remains a separate planned extension.

For default, changed filter, changed parameter, reset, empty result and denied persona cases, specify expected numbers, ordering, visible content, control behavior and access. QA owns the independent expectations and observed outcome. A visually improved draft is still a candidate until those cases are exercised.
