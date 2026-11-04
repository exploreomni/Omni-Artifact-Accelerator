# Domo visual semantics and mapping

This is a review and mapping method, not a formula compiler or an automatic chart
conversion guarantee. Use the original Card/component configuration, query context
and result evidence; pixels alone cannot establish semantics. Keep source facts,
mapping proposals and accepted design changes distinct.

## Establish one analytical contract per output

Retain DataSet/field IDs and native names, Beast Mode IDs and unchanged formulas,
row/aggregate/window/FIXED or other scoped behavior, group keys, date grain,
timezone, units and population. Preserve calculation and filter order; do not move
a post-aggregation predicate into a row filter or average pre-aggregated averages.
Missing or unsupported expressions go to analyst/DMA review with original text.

Treat the **summary number as a separate analytical output**. Record its expression,
filters, comparison period, formatting and relation to the visible chart. Do not
derive it from displayed top-N rows or assume it is the sum of series. Validate its
numerator and denominator independently; the same applies to percent-of-total,
ratio-of-sums and period comparisons.

For each output retain:

- Grain and group membership; full population versus preview, sampled or limited
  output; limit stage and any aggregation performed after retrieval.
- Sort fields/directions and tie handling; top/bottom-N membership and other-category
  rules; null category placement and stable native identity.
- Totals/subtotals and whether they recompute the expression or aggregate displayed
  cells; hidden groups and whether totals include them.
- Null, blank, zero, suppressed and error states; division-by-zero and missing-date
  behavior; numeric precision before display rounding.
- Display versus calculation units, scale/axis origin, timezone and date boundaries.
  Do not infer currency from a logo or user geography.

## Map the encoding, not just the chart name

Use the shared [chart mapping guide](../../omni-dashboard-designer/references/migration-chart-mapping.md)
with the actual target capabilities. The following are review questions, not fixed
target templates:

| Source family | Preservation test before selecting an Omni design |
| --- | --- |
| KPI or summary Card | Same expression, population, comparison baseline and status thresholds; separate summary and detailed result cases |
| Bar, stacked or combo | Category/series roles, grouped versus stacked meaning, shared/secondary axes, percentage denominator and order |
| Line or area | Date grain, timezone, gap interpolation, missing periods, cumulative logic and comparable series scale |
| Table, pivot or heatmap | Row/column dimensions, pivot order, cell expression, totals, pagination and conditional formatting scope |
| Scatter, distribution or funnel | Entity grain, bin boundaries, stage definition and eligibility; no invented sequential/causal interpretation |
| Map or custom visual | Geographic identifiers, coordinate system, location precision, aggregation and actual interaction; retain an unresolved/custom implementation obligation where needed |

State whether a proposed target is preserved, adapted, unsupported or unknown and
attach the rationale. More elaborate 3D or motion is an optional design decision
after the analytical purpose is understood. It must not distort scale or replace
an accessible exact-value view.

## Preserve each placement and filter path

Maintain separate Page/App, Card/component and placement identities. A reused Card
may have different filters, visibility, controls or drill context at each location.
A placement also has layout order, size, title/text, theme and visible/hidden state.
Do not deduplicate placement obligations by Card ID or include only query-bearing
objects in the denominator.

For each control, record scope, target placements, exclusions, defaults, propagation
and reset semantics. Distinguish Page/App controls, Card filters, Variables,
interaction filters and drill predicates. Preserve requested versus observed state;
unknown precedence is a test requirement, not permission to choose a convenient
order. Record whether navigation carries, replaces or clears state and whether a
drill changes data, navigation or both.

The minimum useful behavior matrix includes default, representative filtered,
multi-filter, reset, drill/back, empty and denied-access states. Add boundary cases
driven by the source rather than a universal combinatorial suite. Reconcile values
and active-filter labels for each selected placement. A matching screenshot at the
default state cannot close filter or security coverage.

## Return to the engineers and QA

Return original-byte references, exact IDs, independent expected values, missing
semantic bindings, proposed chart/format/layout mapping and accepted difference
references. Designers improve hierarchy, responsive composition and task clarity
within the selected concept. Engineers retain source-to-target query/tile/component
crosswalks. QA checks the candidate against original evidence, including the summary
output and totals; arbitrary rows agreeing numerically are not source parity.
