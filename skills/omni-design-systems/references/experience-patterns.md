# Pattern atlas for distinctive data experiences

Use with the [curriculum](experience-curriculum.md). These are adaptable design recommendations, not a native chart availability matrix. Select the analytical question first. Resolve the exact grain, fields, scales, ordering, controls and accessible evidence before implementation. An advanced chart earns its place by making a useful relationship easier to see.

For every choice, state **why this pattern, why this audience, why this data, and what simpler alternative was rejected**. Do not replace one generic layout with a rule that every artifact must contain a novel chart.

## Visual structures

| Pattern | Question and data requirements | Resolve the design | Misuse to reject / practical alternative |
| --- | --- | --- | --- |
| **Comparison atlas** | Which entities follow different trajectories? Same metric, comparable periods, stable entity IDs, an agreed population. | Aligned small multiples, shared axes when comparing magnitude, direct endpoint labels, intentional ordering, one accent for the selected entity. Give each panel enough room for its variation. | Independently scaled panels can falsely suggest equal magnitude; label scaling explicitly if shape-only comparison is intentional. Too many tiny panels: filter or paginate with population scope retained. |
| **Change ladder** | Who moved, and by how much, between two periods? Paired values, consistent population, missing-pair policy. | Slope/dumbbell structure, label both endpoints and delta, use color selectively, preserve negative values and ties. Pair rank movement with absolute values when both matter. | Rank is not magnitude or improvement. Crowded crossing lines: highlight one entity or use a sorted delta plot/table. Missing endpoints are not zero. |
| **Position trail** | How does one entity move between two meaningful measures over time? Stable identity, ordered observations, two comparable measures. | Connected scatter with sparse time labels, explicit direction, a highlighted entity, stable axes and an exact-value companion. Use a user-controlled stepper for dense paths. | Do not imply cause from the path, animate absent observations or connect unrelated entities. A time-series pair is better when the trail is hard to follow. |
| **Distribution lens** | Is an average concealing unequal outcomes? Raw observations or verified distribution statistics at the right grain. | Histogram, dot distribution or interval plot; disclose bins, units, median/quantiles and sample size. Use an observed benchmark only if it exists. | An aggregate mean cannot manufacture a distribution. Decorative density curves without a defensible method mislead. Use explicit aggregate comparisons while requesting missing evidence. |
| **Rhythm matrix** | When or where does intensity concentrate? A meaningful row/column pairing such as hour×weekday, stage×cohort or category×period. | Ordered matrix, legible headers, honest color scale, separate missing-state texture/label, selection outline and exact-cell evidence. Provide row/column summaries when useful. | Calendar shape is decoration if only six monthly rows exist. Raw counts can disguise different exposure; choose denominator deliberately. Alternative: grouped bars or an accessible table. |
| **Cohort horizon** | How does behavior differ at the same age since a starting event? Cohort identity, start date, elapsed interval, eligible population and censoring. | Align by elapsed time, show cohort size, distinguish not-yet-observed cells, keep retention and absolute counts available. | Calendar month is not cohort age. Recent cohorts must not appear worse because future periods are absent. Alternative: calendar trends until start-event semantics exist. |
| **Contribution bridge** | What reconciles a starting total to an ending total? Additive, exhaustive signed components at the same scope. | Waterfall or aligned diverging contributions with a visible zero baseline, reconciled endpoints and exact values. Annotate material contributions without attributing causality beyond the data. | Percent changes, distinct counts and overlapping segments generally do not add. Alternative: separate comparisons with an explicit non-additivity note. |
| **Flow ledger** | Where does a quantity or population move? Source/target IDs, measured edge weights, time window and reconciliation rules. | Flow diagram for a manageable network, clear direction, consistent width mapping, selected-path emphasis and a corresponding edge table. Explain entries, exits, cycles and leakage. | A set of category totals does not establish flow. Crossing spaghetti and unexplained nonconservation defeat the task. Alternative: ranked edge table or origin×destination matrix. |
| **Spatial evidence map** | Does location explain a pattern or support an actual geographic task? Verified geography, appropriate normalization, uncertainty and licensing. | Coordinate geographic marks with a ranked comparison, label the selected area, expose scale and denominator, adapt on narrow screens. | Area size can dominate perception; raw population totals often need a rate. Never invent store coordinates or use a map merely because locations have names. Alternative: region bars/small multiples. |
| **Uncertainty field** | How strong or variable is the evidence? Documented intervals, sample sizes, missingness or method confidence. | Interval/dot plots, explicit ranges, no-data treatment, direct method note and an alternative exact-value table. Separate observed variation from model uncertainty. | A shaded band cannot stand in for a statistical method; never generate confidence intervals from a single aggregate. Alternative: show the known estimate and explicitly missing uncertainty. |
| **Equal-space regional atlas** | How do regional trajectories differ when land area is irrelevant? Region IDs and comparable time series; geographic arrangement only if useful for orientation. | Give each region equal display space and a shared chart grammar. Explain schematic geography; reflow to labeled rows on narrow layouts. | Tile size does not represent population, business weight or real area. Avoid for distance/adjacency questions; a nonspatial small-multiple array may be clearer. |
| **Evidence ribbon** | Which ordered checks or stages are verified, adapted, unsupported or unknown? Stable unit IDs, order, independent state/evidence and a complete population. | Compact categorical strip/matrix with text or symbols plus color; selected-unit evidence reveals the reason and any disagreement. | Unknown is neither success nor failure; keep it in the denominator. Equal cells represent units, not duration/effort. Avoid a decorative completion score that hides unresolved evidence. |

## Experience structures

### Annotated evidence essay

Use when a reader needs to understand a complex result before exploring. Organize a supported finding, focal visualization, targeted annotation and counterexample or limitation. Each chapter answers one question with a deliberate visual change. A native dashboard can express this as a static reading sequence with verified filters; an App can provide accessible step navigation or, when justified, scroll-linked steps.

Keep the evidence available without playing a sequence. Headings and annotations must remain truthful under the selected scope; parameterize them or withhold stale prose. Avoid an oversized marketing introduction before the useful evidence. Do not hijack scrolling, require animation to reveal labels, or invent an affirmative business story because the design needs a headline.

### Pinned comparison workspace

Use when users repeatedly compare a few entities against a larger population. Keep a stable overview and let users pin a bounded selection into aligned comparison views. Show pinned identity, scope and the cost of adding another item. Provide keyboard equivalents, remove/reset, a limit explained by readable capacity, and a narrow-screen comparison route.

This differs from a list/detail workspace: simultaneous comparison is the valuable action. Avoid it when selecting one known record is the task. Persistent pinning, cross-query selection and saved state are capability checks, not assumed native features. A dashboard may use supported small multiples or a verified comparison filter; preserve the analytical question when adaptation is necessary.

### Scenario workshop

Use for an explicitly requested hypothetical calculation with accepted formulas. Keep actual evidence and scenario inputs visually distinct; show assumptions, unit-aware controls, a comparison result and reset. An App can make immediate, bounded input feedback feel responsive. Do not animate observed values into hypothetical values without changing their labels.

Calculation ownership stays with the analyst/model owner. Input widgets do not grant writeback authority. Missing formulas, invalid ranges and model-version changes are explicit gaps. A supported native dashboard parameter may suffice; otherwise retain the selected surface and propose a feasible alternative instead of silently converting it into an App.

### Semantic zoom

Use when changing level adds explanatory information: portfolio→region→entity, or summary→distribution→records. Maintain a visual or textual anchor, breadcrumb, scope and useful return. Keep stable IDs through the transition. Zoom is a change of analytical level, not merely enlarging a decorative card.

Specify aggregation rules for every level. Do not add together non-additive measures or let a frontend drill bypass access rules. A supported native dashboard drill can provide this; an App may use a coordinated viewport or pane only when its query/state contract supports it.

## Art-direction recipes

These are starting points, not templates or industry stereotypes. The brand interview, task and data decide which qualities survive.

| Direction | Composition, type and chart finish | Interaction/motion character | Failure to avoid |
| --- | --- | --- | --- |
| **Editorial evidence** | Asymmetric headline/evidence balance, a generous primary chart, compact source/method notes, typographic contrast and intentional annotation. | Reader-controlled chapters; one focal change at a time. | Magazine styling that makes exact values or controls hard to find. |
| **Precision instrument** | Tight alignment, calm surfaces, tabular numerals, dense but legible comparison rows, explicit thresholds/units and restrained color. | Fast selection, stable context and concise confirmation. | Small gray text, overloaded controls, or assumed business thresholds. |
| **Expressive field guide** | Strong branded navigation, open spatial grouping, distinctive category markers and carefully selected imagery that explains real objects. | Orientation transitions and playful, brief feedback within the brand's tone. | Borrowed icons/photos implying unsupported product identity, decoration competing with data, or color carrying the entire meaning. |
| **Comparative atlas** | Repeating visual grammar, precise common scales, quiet labels, sparse accent and deliberate ordering. | Pin, compare, isolate and return. | Repetitive miniature charts that cannot be read or compared. |

Specify type by role: question, supporting sentence, metric, axis, annotation, control and source note. Resolve line length, line height, numeric alignment, long labels and fallback fonts in a real specimen. Use whitespace to mark relationships, not to make every panel equally empty. Limit competing accents; a muted comparison series can make a selected trace feel intentional without a new visual effect.

## Motion choreography

Motion has three useful jobs here: orient a navigation change, preserve identity during comparison, and make an action/result legible. Brand expression can enrich those jobs. The motion designer should propose a meaningful candidate for an App when the task benefits, rather than stopping at a spinner or adding a decorative entrance to every element.

These timing ranges are **initial package hypotheses**, not vendor specifications, a performance SLA or an accessibility test. Tune to the actual distance, content and target. Useful starting points: 100–160 ms for restrained control feedback; 180–280 ms for a local disclosure; 240–400 ms for a reader-controlled comparison transition. Frequent actions should never wait for a decorative effect before becoming operable.

| Motion pattern | Choreography and data invariant | Static/reduced-motion version |
| --- | --- | --- |
| **Selection continuity** | Retain one item's identity while revealing supporting evidence. Let focus/content update without waiting for motion. Keep origin and destination recognizable; reverse/replace cleanly if selection changes. | Immediate detail change, explicit selected state, useful focus and return. |
| **Comparison reordering** | Move stable entity marks between completed comparable states on a stable scale. Label intermediate geometry as transition; exact readouts switch to a completed result, not interpolated business facts. Handle ties deterministically. | Jump to final order with prior/current values or deltas available. |
| **Narrative emphasis** | A user-selected step emphasizes a subset while the surrounding context remains legible. Coordinate annotation and mark changes around one focal event. | Same step controls and full evidence, with instant emphasis. |
| **Scope settlement** | Respond to input immediately, indicate pending scope, and reveal only results attributable to that request. Motion completion never means query completion. | Clear pending/current status and an immediate, atomic result replacement. |
| **Spatial continuity** | If a map/plot supports it, retain selected identity while changing analytical level; avoid unnecessary long-distance camera movement. | Jump with a visible breadcrumb and selected label; retain equivalent data access. |

Motion specification fields: `purpose`, `trigger`, `stable identity`, `from/to states`, `data commit point`, `duration/easing hypothesis`, `choreography`, `interruption/reversal`, `focus`, `reduced/static equivalent`, `performance observation`. Use actual runtime primitives; if cancellation or reliable response attribution is unavailable, simplify the transition and record the gap.

Avoid decorative count-up numbers presented as live facts, endless chart races, broad parallax, bouncing KPI cards, long cascades that delay reading, and multiple unrelated moving focal points. A deliberate timeline can be useful when the temporal process is the question; include direct period selection, pause/stop, exact values and a static comparison. Animation alone is weak evidence for comparing many entities.

## Omni adaptation

For a native dashboard, qualify the actual chart type, layout, formatting, annotations, filter and drill behavior before promising the pattern. Preserve a static, well-composed experience when custom choreography is unavailable. Do not inject CSS/DOM or replace the requested surface. For a native App, qualify the query bridge, allowed scripts/assets and runtime before implementing custom SVG/HTML interactions. An external embedded app remains a separately selected target.

When a desired form is unsupported, record `analytical intent → desired form → verified native form → difference`. Let the analyst confirm that meaning survives, and the designer resolve the actual visual alternative. Asking DMA for an absent field is appropriate; rebuilding a warehouse merely to obtain a fashionable chart is not.

## Guidance basis

The atlas and recipes are original analytics adaptations. [Meaningful motion](https://design.google/library/making-motion-meaningful) supports focusing attention and simplifying complex movement; [motion principles and choreography](https://fluent2.microsoft.design/motion/) support purposeful, coherent transitions. Neither source specifies these timing ranges or establishes Omni support. Checked 2026-10-22; public documentation was read, not its interactive/video demonstrations. Accessibility and assessment details live in the [review guide](experience-review.md).
