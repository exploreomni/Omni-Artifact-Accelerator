# Dashboard patterns by audience and task

Use this reference when composing or reviewing a dashboard. Choose a pattern by the decision and evidence needed, then adapt it to the audience, density and target. These are **package recommendations**, not vendor mandates or proven user-test results. All layouts and numbers below are synthetic. They are design candidates, not screenshots of implemented Omni content.

For competing concepts, use the [ideation playbook](../../omni-design-systems/references/ideation-playbook.md). For observed comprehension and task performance, use [usability testing](../../omni-qa-analyst/references/usability-testing.md). A successful arithmetic check does not establish usability.

## Evidence and target boundary

Primary sources reviewed 2026-10-21:

| Source and platform | Evidence used here | Transfer boundary |
| --- | --- | --- |
| [Microsoft dashboard design tips](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips) — Power BI service guidance | Audience, display context, prominent information, comparison context, consistent periods, scales and sorting. | Its one-screen preference concerns a Power BI overview; it is not a universal no-scroll rule or an Omni tile-count limit. |
| [Tableau visual best practices](https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm) — Tableau Blueprint guidance | Task-dependent chart choice, contextual labels, logical flow and discoverable interactions. | Tableau chart types and actions do not establish Omni support. |
| [Carbon data table guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) — Carbon Core component guidance | Tables support precise lookup; allocate adequate width, associate controls with the table, and reveal supplementary detail progressively. | Carbon row expansion, pagination, actions and sizing are component capabilities, not native Omni guarantees. |
| [IBM visualization basics](https://www.ibm.com/design/language/data-visualization/design/basics/) — IBM Design Language | Clear chart anatomy, meaningful color and detail on demand without concealing essential information. | IBM palettes and motion are not the customer's brand or an Omni implementation contract. |

IBM page refresh was available through the search service's indexed primary-page text after direct fetch timed out; no new feature claim depends on that refresh. Preserve the source/platform distinction when quoting this guide.

For each selected layout, record the current [Omni capability](../../omni-artifact-accelerator/references/omni-capabilities.md), checked documentation and tenant observation for every required chart, control, drill, export or table feature. Composition principles apply to Omni; feature availability remains unverified until checked. An unsupported option produces a gap and a scoped alternative. Moving a native dashboard into an App requires the user's explicit scope change.

In migrations, retain source Page/dashboard, element/placement, query and control IDs, selected coverage denominator, security/personas, Sigma route and approved differences. A repeated source placement remains traceable even if two tiles use the same query. Moving detail, changing a default sort or consolidating filters is an explicit design difference to review, not automatic parity. Apply the [migration behavior contract](../../omni-qa-analyst/references/migration-behavior.md).

## Pattern cards

### Executive overview: assess outcome and choose the next question

**Audience/task:** a leader reviews a defined period and decides which result needs explanation. Use when the metrics and comparison basis are agreed. Avoid when the primary job is reconciling individual transactions or operating a queue.

**Synthetic worked layout — weekly revenue review:**

| Reading region | Candidate content | Why it is here |
| --- | --- | --- |
| Opening context | “Weekly revenue review”; current and prior week dates, USD, active segment scope, freshness | Establishes what the numbers describe before evaluation. |
| Primary answer | Actual $120k; +$20k (+20%) versus prior week; target $125k; $5k below target | Separates improvement from target achievement; all comparisons use the fixture below. |
| Explanation | Horizontal bars: North $60k, South $40k, West $20k; companion prior-period values | Makes segment magnitude and change inspectable without implying causality. |
| Evidence | Exact-value reconciliation table and metric definition | Lets the reviewer check the conclusion; may sit below the overview or in verified detail navigation. |

**Do not use this layout unchanged:** if executives must compare many business units precisely, give the table more space. If the question concerns seasonality, request sufficient comparable history; two weekly points are not evidence of a trend. Do not hide material scope or target exceptions in a tooltip.

**Source evidence/platform:** audience and comparison context from [Microsoft/Power BI](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips); purpose and chart choice from [Tableau Blueprint](https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm). The arrangement and fixture are our recommendation.

**Omni applicability/unknown support:** compose candidate KPI, bar and table tiles. Verify native comparison formatting, labels, responsive layout and detail navigation; separate text annotations are candidates if a native KPI cannot express both comparisons accurately.

**Verification:** independently reconcile the fixture totals; ask a representative viewer whether performance improved and whether target was reached. Record their actual answer and explanation, including any confusion between comparisons. Check native filters affect all intended figures, including target data.

### Operational monitoring: find the exception and identify its next owner

**Audience/task:** an operator needs to find work requiring attention at a particular snapshot. Use when source freshness and the action/ownership model are known. Avoid when the data arrives too slowly to support the stated operational decision or when the task requires transactional editing outside dashboard scope.

**Synthetic worked layout — service request backlog:**

| Reading region | Candidate content | Why it is here |
| --- | --- | --- |
| Persistent context | Snapshot timestamp/timezone; team and queue filters; data freshness | An old snapshot must not resemble live operational state. |
| Queue summary | Open request count and overdue request count, each with definition access | Separates workload from policy-based exceptions. |
| Main working area | Request ID, queue, owner, due time, age, overdue status; sort overdue items by due time then ID | Provides a reproducible action list, preserving identity and ties. |
| Supporting view | Open requests by queue; recent arrival/resolution history if available | Helps distinguish queue concentration from a temporary arrival spike. |

For this example, **open at snapshot** means created by the snapshot and not resolved by it; **overdue** means open with a known due timestamp earlier than the snapshot; **age** is elapsed time from creation to snapshot. Unknown due timestamps form an explicit “due time unknown” group. These fixture definitions are not a customer SLA. A real dashboard needs the analyst's accepted status history, business-calendar rules and policy source; do not invent an urgent/red threshold.

**Source evidence/platform:** contextual information from [Tableau Blueprint](https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm); table lookup from [Carbon](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines). Queue design and definitions are our recommendation.

**Omni applicability/unknown support:** native table and summary candidates; verify refresh behavior, sort stability, timezone formatting, row navigation and export permissions. A source assignment/writeback action is a preserved migration requirement, not assumed dashboard functionality.

**Verification:** use fixtures with an overdue item, a future due item, missing due time, a resolved item and a stale snapshot. Check count/list consistency under each filter. Ask an operator to identify the first item and its owner; observe any missing context. An inaccessible queue must not display as an empty queue.

### Diagnostic exploration: compare plausible explanations

**Audience/task:** an analyst asks where a change is concentrated and what evidence could explain it. Use when segment dimensions and query grain support investigation. Avoid presenting a relationship or segment difference as causal proof; route causal claims to an appropriate analysis.

**Synthetic worked layout — revenue change by segment:**

| Reading region | Candidate content | Why it is here |
| --- | --- | --- |
| Question and scope | “Which segments contributed to this week's $20k increase?”; period and segment controls | Names a bounded, answerable question. |
| Change decomposition | North +$10k, South +$10k, West $0 as bars; exact current/prior values beside them | Equal dollar contributions remain visible despite different percentage growth. |
| Exploration | Comparable weekly small multiples by segment, only after additional weekly evidence is supplied | Supports pattern comparison without inventing historical observations. |
| Detail | Source-backed segment/week table; selected filters and reset path | Makes each explored state reproducible. |

For distributions, replace an average-only view with a candidate histogram or box plot when record-level values and the question justify it. Specify the population, bin boundaries or quartile convention, excluded/missing rows and sample size. For relationships, specify a scatter plot's point grain and aggregation; overlapping points or mixed grains can conceal the story.

**Source evidence/platform:** chart-task mapping from [Tableau Blueprint](https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm); essential context before interaction from [IBM basics](https://www.ibm.com/design/language/data-visualization/design/basics/). The exploration sequence is our recommendation.

**Omni applicability/unknown support:** check each selected encoding, common axis range, small-multiple arrangement, filter propagation, drill path and reset behavior. No histogram, box plot or cross-filter support is established by this guide. A verified table of the same values can support review while a chart capability remains unresolved.

**Verification:** reconcile the contributions to the total change. Test a filter/change/reset sequence and reconstruct the final scope from visible context. Test missing periods and categories. Ask the analyst to distinguish largest dollar contribution from largest percentage growth; verify the answer against the fixture rather than the chart's color or order.

### Dense analytical table: reconcile and inspect exact values

**Audience/task:** an analyst or reviewer needs precise lookup, comparison and traceability. Use when row identity and exact values matter. Avoid when the intended task is spotting an overall shape that a chart would reveal more readily, or when spreadsheet-style editing is a required but unverified capability.

**Synthetic worked layout — segment reconciliation:**

| Reading region | Candidate content | Why it is here |
| --- | --- | --- |
| Table context | Periods, USD, grain “one row per segment”, active scope, row coverage and freshness | Distinguishes the full population from a filtered or limited result. |
| Primary table | Segment; current; prior; dollar change; percentage change; target; target gap | Puts comparable values together; exact values take priority over decorative charts. |
| Supporting detail | Metric formula and source/query IDs accessible through a verified detail route | Supports reconciliation without making metadata dominate the scan. |
| Footer/context | Totals, aggregation method, result-limit warning if applicable | Prevents a visible subset from masquerading as the full total. |

Give this table meaningful width. Preserve readable labels and values with the agreed native wrap/scroll behavior; do not shrink every column to fit. Align comparable numeric values consistently; identify units in headers. A total percentage must use the defined total numerator/denominator, not an average of row percentages. Keep a stable row key for tied sorts and exports.

**Source evidence/platform:** table space, lookup and supplementary detail from [Carbon](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines). This analytical column set is our recommendation; Carbon is not an Omni table library.

**Omni applicability/unknown support:** verify sorting, pagination/result limits, totals, wrapping, frozen columns, keyboard scrolling and export scope separately. Do not prescribe a Carbon toolbar, row expansion or row-height value as an available native setting.

**Verification:** locate an exact row, compare it with another row, then reconcile the total using the fixture. Test long labels, negatives, nulls and tied sorts. Compare displayed and exported coverage under the same persona and filters; label any unsupported export scenario. Test whether horizontal scrolling loses the user's ability to identify the row.

## Chart choice and misleading alternatives

The following are package decision rules to test, not a list of promised native chart types.

| Analytical task | Candidate and specification | Anti-pattern to challenge |
| --- | --- | --- |
| Rank categories | Sorted horizontal bars for long labels; specify rank metric, ties, excluded categories and any top-N remainder. | A decorative map when location is irrelevant; silently dropping the unshown categories; changing the sort metric between tiles. |
| Compare magnitudes | Bars with a zero baseline; signed values extend around zero. Preserve exact values in accessible detail. | A truncated bar baseline exaggerating small differences; decorative 3D marks. |
| Follow change over time | Line with an ordered, defined time grain; distinguish missing periods from observed zero. Disclose partial periods. | A line connecting unordered categories; comparing complete and incomplete periods as equivalent. |
| Compare repeated profiles | Small multiples with the same axes for absolute magnitude comparison and stable category order. If independently scaled, label it and restrict the claim to shape. | Automatic per-panel ranges that make unequal magnitudes appear equal. |
| Inspect distribution | Histogram with stated bin edges, or a box plot with stated summary rules; show missing count and population. | Reporting only the mean for a skewed population; changing bins between compared populations without explanation. |
| Explore association | Scatter plot with one stated entity per point, defined units and aggregation; inspect overlap and sample coverage. | Joining unrelated grains or implying correlation demonstrates causation. |
| Look up precise values | Table with defined grain, row identity and exact units; use an agreed stable sort. | Asking users to estimate exact values from unlabeled shapes. |

A line's range may narrow to reveal variation if its scale is explicit and the interpretation remains honest. For unrelated units or very different magnitudes, prefer separate aligned views or clearly defined normalization; if a dual axis is retained, label each unit/scale and test whether readers infer a false relationship. A normalized index needs a specified base period and formula; it cannot silently replace currency values.

## KPI and data-context contract

For each displayed metric, carry its agreed definition, source/query binding, grain, aggregation, population/exclusions, date field, timezone, period boundaries and data freshness. A comparison adds its own period, matching scope, completeness rule and formula. A target adds its origin, version, effective period, allocation grain and whether the active filters also apply to it. No target means no inferred “on track” status.

Specify units and display precision independently from computation precision. Abbreviated labels need an exact-value path; round at presentation, not before calculating totals. Distinguish percentage change from percentage-point difference. Define behavior for zero or negative comparison denominators instead of producing a misleading percentage. Null, no rows, not applicable, denied access and failed query are distinct states; do not convert them all to zero. Explain any intentional null-to-zero business rule in the metric contract.

Keep essential scope and uncertainty visible. Additional definitions and row detail can use supported progressive disclosure, but current filters, comparison periods, partial-data warnings and security restrictions cannot depend solely on hover or a hidden interaction. Evaluate scroll and density by the actual task, reading order and target viewport; there is no universal tile count or no-scroll requirement.

## Independently checkable comprehension fixture

**Synthetic only; not customer data or acceptance evidence.** Grain: one row per segment. Measure: sum of posted `revenue_usd` for included fixture rows; reversed rows are excluded upstream. USD only, no currency conversion. Current week is `[2026-10-12 00:00, 2026-10-19 00:00)` UTC; prior week is `[2026-10-05 00:00, 2026-10-12 00:00)` UTC. Both periods are complete. Targets below are fixture values for the current week, not real business targets.

| Segment | Current USD | Prior USD | Target USD |
| --- | ---: | ---: | ---: |
| North | 60,000 | 50,000 | 65,000 |
| South | 40,000 | 30,000 | 40,000 |
| West | 20,000 | 20,000 | 20,000 |
| Total | 120,000 | 100,000 | 125,000 |

Independent answer key:

- Total dollar change: `120,000 - 100,000 = +20,000`.
- Total percentage change: `(120,000 - 100,000) / 100,000 = +20%`.
- Target attainment: `120,000 / 125,000 = 96%`.
- Signed target gap: `120,000 - 125,000 = -5,000`; relative to target: `-5,000 / 125,000 = -4%`.
- North and South each contribute `$10,000` to the increase. South's percentage growth is `10,000 / 30,000 = 33.33…%`, versus North's `20%`; those are different questions.

Suggested comprehension prompts: “Did revenue improve, and was the target reached?” “Which segment contributed the most additional dollars?” “What dates and filters do these answers cover?” Keep this answer key separate from participant prompts. QA should calculate expected values from the original table before inspecting rendered outputs. No participants have been tested by publishing this example.

## Performance hypotheses and verification

Performance is a measured property of the selected tenant, data, queries, browser and access context. A simplified screenshot does not prove faster execution. Define the user operation, start/end event, population, sample count, cold/warm condition, concurrency and agreed budget before judging it. Leave unagreed budgets `TBD`; do not borrow arbitrary response-time thresholds.

| Hypothesis to test | Measurement and comparison | Correctness guard |
| --- | --- | --- |
| Deferring secondary detail reduces initial waiting. | Compare initial query count, query durations and time until required tiles are usable against the existing design. Record whether the target actually defers queries. | Hidden content might still query; do not claim savings without evidence. Essential context remains visible. |
| A summary plus targeted detail reduces table rendering cost. | Hold data/persona/filter conditions constant; measure returned rows, query time and browser render time separately. | Changed aggregation or limits must not alter required coverage; reconcile totals and detail access. |
| Fewer simultaneously active queries improve filter response. | Measure from committed filter action to all affected visible tiles settling; record errors, partial completion and repeated runs. | Do not silently remove migration tiles or narrow filter scope to meet the budget. |
| A revised layout improves comprehension. | Observe the same defined task with comparable fixtures; record correct/incorrect answers, completion time and needed assistance. | This is a usability hypothesis, separate from backend latency; report actual observations, not assumed improvement. |

Record median or tail latency only with a declared calculation and enough observations for the interpretation; retain raw timings and sample size. Check the slow scenario and failures as well as the happy path. Report design review, arithmetic reconciliation, measured performance, native behavior and participant evidence separately using [design QA](../../omni-design-systems/references/design-qa.md).
