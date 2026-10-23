# Pattern atlas for distinctive data experiences

Use with the [curriculum](experience-curriculum.md). These are adaptable design recommendations, not a native chart availability matrix. Select the analytical question first. Resolve the exact grain, fields, scales, ordering, controls and accessible evidence before implementation. An advanced chart earns its place by making a useful relationship easier to see.

The designer chooses the task and rationale before optional pattern/example retrieval unless the user selected a reference. Each entry records useful context, data/runtime prerequisites, poor fit, an alternative, a tradeoff and the evidence needed. Select only what helps; no entry prescribes an App shell, hero, cards, sidebar, tabs, 3D scene or number of concepts. Intentional similarity is valid; novelty is not a metric.

## Visual structures

| Pattern | Useful context and prerequisites | Design and tradeoff | Poor fit / alternative | Evidence needed |
| --- | --- | --- | --- | --- |
| **Comparison atlas** | Compare entity trajectories; same metric, comparable periods, stable IDs and declared population. | Aligned small multiples, direct endpoints and deliberate ordering; trades space for parallel comparison. | Too many tiny panels: scoped filtering/table. Independent scales can imply equal magnitude; label shape-only scaling. | Reconcile keyed endpoints and scales; inspect readable panel size and scope after filtering. |
| **Change ladder** | Compare two periods; paired values, consistent population and missing-pair policy. | Slope/dumbbell with endpoints and delta; crossings cost readability. Retain ties and negatives. | Rank alone is not magnitude or improvement; dense crossings favor a sorted delta plot/table. Missing is not zero. | Verify pairs/deltas; observe label separation and selection with ties/missing endpoints. |
| **Position trail** | Follow an entity across two measures; stable ID and ordered comparable observations. | Connected scatter, explicit direction and exact-value companion; paths require more reading than separate trends. | No inferred cause, missing-step interpolation or unrelated connections. Use paired time series for dense trails. | Check identity/order/axes; exercise selected-path and static evidence access. |
| **Distribution lens** | Examine unequal outcomes; raw observations or verified distribution statistics at the right grain. | Bins, dots or intervals with sample size and method; detail costs space and explanation. | Aggregate means cannot supply distributions. Show aggregate comparisons until adequate evidence exists. | Reproduce bin/quantile method and counts; inspect labels, missingness and exact evidence. |
| **Rhythm matrix** | Find intensity across meaningful dimensions; ordered row/column keys and exposure definition. | Legible matrix, honest color scale and distinct missing state; overview sacrifices precise comparison. | Monthly aggregates do not justify daily calendars; use grouped bars/table when exposure or cells are unclear. | Verify denominators/cells; inspect scale, selected-cell values and narrow layout. |
| **Cohort horizon** | Compare age since a start event; cohort IDs, start dates, eligible counts and censoring. | Align elapsed time and disclose cohort sizes; delayed observation complicates interpretation. | Calendar month is not cohort age. Use calendar trends until start-event semantics exist. | Reconcile age/population; verify not-yet-observed cells and raw-count access. |
| **Contribution bridge** | Reconcile totals; additive, exhaustive signed parts in the same scope. | Waterfall or diverging contributions with zero/endpoints; reconciliation is clearer than individual trends. | Rates, distinct counts and overlapping segments generally do not add. Use separate comparisons with a non-additivity note. | Parts reconcile to endpoints; inspect signed/zero values, scope and noncausal annotations. |
| **Flow ledger** | Follow measured movement; source/target IDs, edge weights, time and reconciliation rules. | Direction and width encode edges with a table; complex networks cost legibility. | Category totals are not flows. Use ranked edges or an origin×destination matrix for dense networks. | Reconcile entries/exits/cycles; inspect path selection and exact edge values. |
| **Spatial evidence map** | Answer a geographic task; verified coordinates, normalization, uncertainty and asset rights. | Map with ranked comparison and selected labels; geography can dominate quantitative differences. | Named places alone do not justify invented coordinates. Use regional bars/small multiples if location adds little. | Verify locations/denominators; inspect scale, narrow layout and equivalent exact comparison. |
| **Uncertainty field** | Show strength or variation; documented intervals, sample sizes, missingness or method confidence. | Interval/dot plot with method and exact table; explanation adds density. | A band is not a statistical method. Show a known estimate and explicitly absent uncertainty when necessary. | Reproduce interval meaning; inspect missingness and distinguish variation from model uncertainty. |
| **Equal-space regional atlas** | Compare regions without land-area weighting; region IDs and comparable time series. | Equal panels and shared grammar, optionally schematic geography; loses geographic scale. | Poor for distance/adjacency. Use a real map or nonspatial small multiples; tile size implies neither population nor real area. | Verify shared scales and identities; inspect schematic labels and row reflow. |
| **Evidence ribbon** | Inspect ordered verification states; stable unit IDs, complete population and independent evidence. | Categorical strip with text/symbols and detail; compactness hides reasoning until inspected. | Unknown is not success/failure; cells are not effort/duration. Use a labeled status table when detail dominates. | Reconcile all units including unknowns; exercise selected evidence and non-color reading. |

## Experience structures

### Annotated evidence essay

Use when a reader needs to understand a complex result before exploring. Organize a supported finding, focal visualization, targeted annotation and counterexample or limitation. Each chapter answers one question with a deliberate visual change. A native dashboard can express this as a static reading sequence with verified filters; an App can provide accessible step navigation or, when justified, scroll-linked steps.

Prerequisites are evidence-bound claims and qualified step/scroll behavior when selected. The tradeoff is narrative guidance versus direct inspection; a comparison workspace is better for rapid repeat analysis. Keep evidence available without playing a sequence, parameterize or withhold stale prose, and never hijack scrolling or require animation to read labels. Verify claims after scope changes and exercise direct entry, step navigation and static evidence access.

### Pinned comparison workspace

Use when users repeatedly compare a few entities against a larger population. Keep a stable overview and let users pin a bounded selection into aligned comparison views. Show pinned identity, scope and the cost of adding another item. Provide keyboard equivalents, remove/reset, a limit explained by readable capacity, and a narrow-screen comparison route.

Prerequisites include comparable metrics, stable IDs and qualified pin/save behavior. Simultaneous comparison trades screen space and selection complexity for fewer context switches. Use list/detail when one known record is the task. Verify pin/remove/reset, denominator consistency and narrow/keyboard comparison; persistent or cross-query state is not assumed. A dashboard may use supported small multiples or a verified comparison filter.

### Scenario workshop

Use for an explicitly requested hypothetical calculation with accepted formulas. Keep actual evidence and scenario inputs visually distinct; show assumptions, unit-aware controls, a comparison result and reset. An App can make immediate, bounded input feedback feel responsive. Do not animate observed values into hypothetical values without changing their labels.

Accepted formulas, input bounds and model versions are prerequisites owned by the analyst/model owner. The tradeoff is exploratory power versus risk of confusing actual and hypothetical results. Use a static sensitivity table or supported dashboard parameter when fewer controls suffice; do not silently change surfaces. Verify known formula cases, invalid ranges, reset and unmistakable actual/scenario labeling. Widgets grant no writeback authority.

### Semantic zoom

Use when changing level adds explanatory information: portfolio→region→entity, or summary→distribution→records. Maintain a visual or textual anchor, breadcrumb, scope and useful return. Keep stable IDs through the transition. Zoom is a change of analytical level, not merely enlarging a decorative card.

Prerequisites are aggregation/access rules and qualified queries at every level. Deeper context costs orientation; use a flat comparison or exact table when levels add little evidence. Verify totals, effective access, stable IDs and scope/focus restoration through drill and return. A supported dashboard drill may suffice; an App viewport/pane requires its own qualified state contract.

## Art-direction recipes

These are starting points, not templates or industry stereotypes. The brand interview, task and data decide which qualities survive.

| Direction | Useful context / prerequisites | Treatment and tradeoff | Poor fit / alternative | Evidence needed |
| --- | --- | --- | --- | --- |
| **Editorial evidence** | Explain a supported result; attributable narrative and brand permission. | Unequal headline/evidence balance, generous focal chart and precise notes; uses more space. | Repeated dense lookup may favor a precision workspace. Do not bury controls or exact values. | Render hierarchy, long copy and constrained layouts; verify claims across scope changes. |
| **Precision instrument** | Frequent comparisons; stable units, definitions and dense-data need. | Alignment, tabular numerals and restrained surfaces; density demands careful labeling. | Exploration needing explanation may favor editorial grouping. Do not invent thresholds or shrink text. | Render realistic density/long labels; exercise keyboard and exact-value lookup. |
| **Expressive field guide** | Explore identifiable objects; authorized useful imagery and meaningful categories. | Strong identity, open grouping and selected imagery; imagery increases loading and attention costs. | Decoration or missing assets favor a text-led treatment; categories cannot depend on color alone. | Observe actual asset loading, identity and evidence access in narrow/static states. |
| **Comparative atlas** | Compare repeated measures; comparable populations and shared scales. | Repeated grammar, quiet labels and sparse accent; many panels consume space. | Too many tiny plots favor a ranked table or selected comparison. | Reconcile common scales; render panel legibility and exercise selection/return. |

Specify type by role: question, supporting sentence, metric, axis, annotation, control and source note. Resolve line length, line height, numeric alignment, long labels and fallback fonts in a real specimen. Use whitespace to mark relationships, not to make every panel equally empty. Limit competing accents; a muted comparison series can make a selected trace feel intentional without a new visual effect.

## Motion choreography

Motion has three useful jobs here: orient a navigation change, preserve identity during comparison, and make an action/result legible. Brand expression can enrich those jobs. The motion designer should propose a meaningful candidate for an App when the task benefits, rather than stopping at a spinner or adding a decorative entrance to every element.

These timing ranges are **initial package hypotheses**, not vendor specifications, a performance SLA or an accessibility test. Tune to the actual distance, content and target. Useful starting points: 100–160 ms for restrained control feedback; 180–280 ms for a local disclosure; 240–400 ms for a reader-controlled comparison transition. Frequent actions should never wait for a decorative effect before becoming operable.

| Motion pattern | Useful context / prerequisites | Choreography and tradeoff | Poor fit / static alternative | Evidence needed |
| --- | --- | --- | --- | --- |
| **Selection continuity** | Reveal related evidence; stable ID and known origin/target. | Preserve identity while content/focus update immediately; motion can distract during rapid selection. | Unrelated records or frequent switching favor immediate detail with explicit selection and return. | Exercise interruption, focus/return and reduced-motion equivalents. |
| **Comparison reordering** | Explain order changes; completed comparable states, stable scale and deterministic ties. | Move stable marks while exact readouts commit atomically; crossing paths cost clarity. | Dense or incomparable states favor final order with prior/current deltas. Never interpolate business facts. | Reconcile endpoints; observe rapid changes, ties and static comparison. |
| **Narrative emphasis** | Explain a user-selected step; valid scoped annotations and readable surrounding evidence. | Coordinate one focal change; sequencing costs direct access. | Repeat lookup favors immediate emphasis and direct evidence navigation. | Observe step/reverse access and verify prose under scope changes. |
| **Scope settlement** | Explain pending versus current results; trustworthy request/result attribution. | Immediate input feedback and atomic current-result reveal; animation adds no completion authority. | Uncorrelated responses require a simpler qualified request flow, not a transition. Static status is sufficient. | Exercise late/error responses and interruption; motion never decides query completion. |
| **Spatial continuity** | Change analytical level in a qualified map/plot; stable selection and level semantics. | Retain identity during movement; camera travel risks disorientation and scroll conflict. | Flat comparison or an immediate breadcrumb jump is preferable when movement adds little. | Observe reset, interruption, keyboard/page-scroll behavior and equivalent static evidence. |

Motion specification fields: `purpose`, `trigger`, `stable identity`, `from/to states`, `data commit point`, `duration/easing hypothesis`, `choreography`, `interruption/reversal`, `focus`, `reduced/static equivalent`, `performance observation`. Use actual runtime primitives; if cancellation or reliable response attribution is unavailable, simplify the transition and record the gap.

Avoid decorative count-up numbers presented as live facts, endless chart races, broad parallax, bouncing KPI cards, long cascades that delay reading, and multiple unrelated moving focal points. A deliberate timeline can be useful when the temporal process is the question; include direct period selection, pause/stop, exact values and a static comparison. Animation alone is weak evidence for comparing many entities.

## Omni adaptation

For a native dashboard, qualify the actual chart type, layout, formatting, annotations, filter and drill behavior before promising the pattern. Preserve a static, well-composed experience when custom choreography is unavailable. Do not inject CSS/DOM or replace the requested surface. For a native App, qualify the query bridge, allowed scripts/assets and runtime before implementing custom SVG/HTML interactions. An external embedded app remains a separately selected target.

When a desired form is unsupported, record `analytical intent → desired form → verified native form → difference`. Let the analyst confirm that meaning survives, and the designer resolve the actual visual alternative. Asking DMA for an absent field is appropriate; rebuilding a warehouse merely to obtain a fashionable chart is not.

## Guidance basis

The atlas and recipes are original analytics adaptations. [Meaningful motion](https://design.google/library/making-motion-meaningful) supports focusing attention and simplifying complex movement; [motion principles and choreography](https://fluent2.microsoft.design/motion/) support purposeful, coherent transitions. Neither source specifies these timing ranges or establishes Omni support. Checked 2026-10-22; public documentation was read, not its interactive/video demonstrations. Accessibility and assessment details live in the [review guide](experience-review.md).
