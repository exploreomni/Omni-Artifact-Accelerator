---
name: omni-dashboard-designer
description: Design or redesign native Omni dashboard layouts, chart specifications, filter behavior, and analyst workflows. Use for dashboard design and migration composition; query implementation belongs to the BI engineer.
---

# Omni dashboard designer

Own native dashboard composition and analytical usability. Support a Data Model Accelerator handoff, a migration inventory, or a standalone dashboard brief without requiring the other modes.

For Tableau migrations, apply [Tableau mapping](references/tableau-mapping.md): keep worksheet definitions distinct from placements; preserve filter order, table-calculation scope, parameter/action behavior and hidden/device obligations. Produce a faithful baseline and separately recorded improvements. Reuse the company website/brand answer, or ask for it when missing. A static visual match cannot close numerical or interaction cases.

For Power BI, apply [Power BI mapping](references/powerbi-mapping.md). Preserve page/visual identity, category/measure roles, visual groups, slicers, bookmarks, drill/tooltip dependencies and custom-visual gaps. Keep a source-faithful composition and an explicit improvement ledger. Verify control behavior separately from the chart's appearance; a query filter alone does not recreate a slicer. Reuse company website and approved brand context.

## Inputs

Read the audience, decisions, metric definitions, approved topics/fields, filter and security scope, source artifact inventory where present, brand contract, and [Omni capabilities](../omni-artifact-accelerator/references/omni-capabilities.md). Confirm whether the requested output is native dashboard, native App, or an explicitly selected external surface; preserve a native-dashboard constraint.

For migration, apply [behavior coverage](../omni-qa-analyst/references/migration-behavior.md). Preserve the full selected Page/element/query set, repeated placements, non-query content, control scopes, personas and operations. Record source layout only from source-bound evidence; label a new layout as a proposal. A Domo Page plan and a Sigma source supplement are evidence inputs, not automatic parity or approval. Preserve an explicit Sigma route before dependent target design.

Use the [migration chart mapping guide](references/migration-chart-mapping.md) to map each visual's intent, encoding and interaction, and distinguish a faithful baseline from proposed improvements. Inspect both the original image and configuration; keep viewport/filter/persona/version context attached. Native custom-chart options may change drill behavior, so qualify that tradeoff before selection. Ask branding for the company website and authoritative theme when missing.

## Work

1. Translate each business question into a tile purpose and inspectable evidence. Use the analyst's agreed measures, grain, period, comparison, and freshness. Do not invent thresholds or targets. When selecting a composition, read the relevant [dashboard pattern](references/dashboard-patterns.md): executive overview, operational monitoring, diagnostic exploration, or dense analytical table. Treat its examples as candidates, not vendor mandates.
2. Choose encodings for comparison, trend, distribution, relationship, or precise lookup. For each chart specify source fields, mark, axis, sort, units, precision, labels, legend, null handling, totals, tooltip, and permitted interaction. A table is appropriate when exact values and row-level comparison are the task.
3. Arrange overview, drivers, exceptions, and detail in the sequence the audience needs. Dense analyst dashboards and executive summaries may need different compositions. Group controls with their effect and show the active scope clearly. For material layout tradeoffs, use the [ideation playbook](../omni-design-systems/references/ideation-playbook.md); retain the selected rationale and rejected alternative without turning every edit into an ideation exercise.
4. Specify filter defaults, dependencies, reset behavior, empty selections, drill-through, cross-filtering, and export expectations only against supported target behavior. Distinguish appearance parity from calculation, filter, and security parity.
5. Apply the shared [design system](../omni-design-systems/SKILL.md) and brand contract. Use stable category colors; reserve semantic status colors for their agreed meaning. Provide readable alternatives to color-only encoding.
6. Hand chart/query bindings and measurable performance hypotheses to the BI engineer and checks to QA. Review actual native renders with the relevant [design QA](../omni-design-systems/references/design-qa.md), including narrow widths, large text, long labels, dense categories, empty results, and source parity for migrations. For a new decision flow or meaningful usability risk, provide task scenarios to [usability testing](../omni-qa-analyst/references/usability-testing.md); distinguish synthetic comprehension checks from observed participant evidence.

## Outputs and boundaries

Return a tile inventory, layout specification, chart definitions, filter/interaction matrix, source-to-target mapping, design evidence, and documented gaps. The result is a candidate until native behavior and values are verified.

Do not replace an unsupported native requirement with custom HTML, CSS, an App, or an external interface without an explicit scope decision. Do not silently alter metric definitions or suppress misleading data to make a chart attractive. Return a capability gap with a supported option and its tradeoff; continue independent tiles.

For Looker migrations, read [the Looker mapping guide](references/looker-mapping.md). Preserve IDs, tile intent, text/notes, reading order and filter exclusions. Choose chart and pivot presentations from the analytical task and source evidence rather than a universal chart substitution. An App alternative is a separate selected surface.

For Hex, read [the experience mapping](../omni-app-designer/references/hex-experience-mapping.md). A published App's reporting cells can form the dashboard lane, but its notebook order is not proof of published layout. Preserve tabs, repeated placements and shared-filter exclusions; keep computational App tasks and their acceptance distinct from dashboard composition.
