# Migration chart mapping and improvement

Checked against official Omni chart documentation on 2026-10-21. This is an analyst/design decision guide, not a Domo chart-code converter. Preserve the source chart identifier and raw configuration; choose target configuration from the actual tenant schema.

## Map intent and behavior

For every source placement record chart family, fields and aggregation, encodings, sort, axis bounds/scale, stacking, series, labels, units, totals, tooltip, filters, drill/action behavior, viewport and theme. Assign each facet `exact`, `adapted`, `unsupported`, or `unknown` with evidence. Record the implementation route separately, such as native chart or custom Vega-Lite; `custom` is not a parity outcome. Matching a chart family does not prove matching behavior.

Omni documents built-in bar, line, area, KPI, pie/donut, scatter, heatmap, funnel, boxplot, map, Sankey and table families. Verify configuration and interactions separately for the chosen type. [Chart catalog](https://docs.omni.co/visualize-present/visualizations/types)

| Source intent/family | Initial target candidate | Evidence and improvement questions |
| --- | --- | --- |
| Category comparison: bar/column | Native bar | Preserve grouping/stacking and category order. Would horizontal labels improve readability? Keep value-axis choices explicit. |
| Trend: line/area | Native line or area | Match time grain, timezone, missing-period behavior and stacking. Never interpolate absent observations without a decision. |
| Headline value or variance | Native KPI | Preserve aggregation, comparison period, target and percentage-point versus percent change. Label stale values and absent comparisons. |
| Exact lookup: table/pivot | Native table with verified pivot/totals settings | Compare totals independently; preserve sort, hidden binding fields, conditional meaning and export completeness. |
| Part-to-whole: donut/pie/stacked | Same native family initially | Check complete denominator, negative values, “Other” and omitted categories. A proposed bar redesign needs a recorded reason. |
| Relationship/distribution: scatter/boxplot | Matching native family | Preserve point identity, outliers, bin/quartile rules, scale and overplotting behavior. |
| Stage/process: funnel/Sankey | Matching native family | Establish ordered stages and population rules. Do not present separate cohort counts as a conversion journey. |
| Heatmap | Native heatmap | Preserve bins, color domain, null treatment and a legible non-color cue. |
| Geography | Native map if supported data/geometry matches | Retain geographic keys, aggregation, projection, boundary source and access restrictions. Test sparse and unmapped regions. |
| Gauge, waterfall, bullet, Gantt, custom chart | Verify native support; otherwise evaluate documented custom visualization | Capture the business task and every lost interaction before choosing custom. A plausible picture is insufficient. |
| Text, logo, image, link or filter Card | Native content/control candidate | Preserve placement and accessible meaning. Do not drop it because it has no query. Brand assets need source and use permission. |
| App Studio, workflow, writeback or custom app | Explicit App/operational design workstream | Preserve side-effect ownership. A dashboard or static mockup cannot satisfy an action or writeback requirement. |

The custom Vega-Lite documentation includes examples for several specialized charts, but conversion through the advanced editor removes native drill functionality. Work on a copy and record this behavior difference. A native dashboard request does not automatically authorize an external iframe/App workaround. [Custom visualizations](https://docs.omni.co/visualize-present/visualizations/types/custom)

## “Similar but better” review

Keep two linked views: the faithful source requirements and the proposed design changes. For each improvement record source issue, proposed change, affected users/tasks, semantic effect, measurement and decision status. Examples: shorten a redundant title while preserving units; align number formats; replace ambiguous color with text plus color; group controls with affected charts; improve small-screen ordering.

Use the existing [dashboard patterns](dashboard-patterns.md), [design-system guidance](../../omni-design-systems/references/vendor-guidance.md), and customer brand contract. Ask for the company website URL if missing; compare website identity with the approved product theme rather than copying all website styling into an analytical interface.

QA compares matching source/target states at agreed viewports and checks readable labels, category colors, hierarchy, filter scope, data truth and actual interaction. Pixel difference is diagnostic only: an intentional improvement may differ visually, and a nearly identical picture may have incorrect data. No automatic visual-diff or chart-conversion engine is shipped in this guide.
