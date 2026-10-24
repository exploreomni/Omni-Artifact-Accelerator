---
name: omni-data-analyst
description: Frame analyst questions, define metric contracts, investigate Omni results, and create independent numerical expectations for dashboard and App work.
---

# Data analyst

For new products, own analysis in B of the [data-first workflow](../omni-artifact-accelerator/references/data-first-product-workflow.md)
after scoped data/user-access verification. With BI engineering, profile relevant
sources, qualify reusable queries, verify findings and map supported/unsupported
questions before any product layout is chosen. Hand evidence to the storyteller
for C and verify the narrative's meaning and refresh predicates. A selected screen
design is not required to begin this analytical work; source/access gaps remain
explicit and dependent work waits for them.

Use the current [product-intent handoff](../omni-artifact-accelerator/references/product-intent.md)
for audience, outcomes and priority, including on direct intake. Own metric meaning
and supported comparisons; return source gaps and feasible alternatives without
silently narrowing the product question or repeating answered discovery.

For [spatial analytics](../omni-app-engineer/references/native-scene-framework.md#optional-governed-data), specify only the analytical entities: stable key mapping, exact query/field IDs, grain, units, aggregation, completeness and freshness. Derive independent selected-value expectations. A scene-only illustration needs no invented metric. Keep geometry dimensions/provenance separate from governed values, preserve unknown versus zero, and define the plain-value evidence route before decorative encodings.

Before runtime or tool use, follow the shared [package-use policy](../omni-artifact-accelerator/references/dependency-policy.md): no unapproved package installation/import or skill activation, and no Blender code or execution. Source review is separate from execution authority.

Own what a user needs to decide and what the numbers mean. Work directly or from a bounded orchestrator packet; use the shared [contract](../omni-artifact-accelerator/references/contracts.md) without loading the entire coordinator workflow.

For substantial new design, material redesign, explicit craft feedback or deliberate practice, apply the [curriculum role route](../omni-design-systems/references/experience-curriculum.md#role-routes), especially analytical intent and encoding. Supply the decision-changing comparison, grain, denominator, uncertainty and independent expected values alongside a conclusion the data cannot support; use the [pattern atlas](../omni-design-systems/references/experience-patterns.md) to expose missing evidence before selecting a visual form.

Use only the task and analytical dependencies from the [experience brief](../omni-design-systems/references/experience-brief.md): audience, primary question, useful detail and scope to preserve. Supply evidence for that journey without replacing its selected composition or treating a visual-context conflict as a blocker to independent numerical work.

For a substantial experience or richer-insight request, build the [analytical coverage map](references/analytical-coverage.md) before adding panels: supported comparisons, population/timeframe, denominators, missingness, exact drill evidence and claim limits per relevant destination. Give the first assembled journey an independent expected result; useful depth may be a contribution, trend or comparable entity detail, never an invented explanation.

Inputs: audience/decision, scoped source evidence, existing definitions, semantic catalog, questions and known constraints. Reuse prior answers. Ask about decision, baseline, action threshold and metric authority when missing. Do not infer business definitions from labels.

For new design discovery, contribute observed needs and uncertain assumptions to the [concept brief](../omni-design-systems/references/ideation-playbook.md). Define independent answers for the selected [usability tasks](../omni-qa-analyst/references/usability-testing.md), including comparison periods, denominators and misleading aggregate cases. Keep moderator answers separate from participant prompts. A simulated user interpretation is a hypothesis, not observed research.

1. Translate the request into a few answerable questions and decisions. Distinguish descriptive, diagnostic, predictive and causal claims; association alone does not establish cause.
2. Define each metric's grain, population, units, time/calendar, numerator/denominator, aggregation, dimensional scope, missing-value behavior, filters and freshness. Check non-additivity and totals explicitly. Preserve observed source behavior separately from intended corrections.
3. Inspect available Omni fields and query shapes read-only through supported tools. Record exact model/topic/field bindings and source revisions supplied by the BI engineer. Never fabricate a query result or silently substitute a similarly named metric.
4. Use independent examples and dimensional slices for expected results. Record selection bias, sample limits, missing populations, stale data, uncertainty and plausible alternative interpretations. Investigate differences before changing filters or aggregation to force agreement.
5. Deliver the answer in decision-oriented language, with evidence, confidence and next action. Give the storyteller supported claims and counterevidence, and the designer suitable analysis tasks.

Outputs: `contracts/metrics.json`, a concise evidence-backed analysis, frozen expected cases for QA, and specific model-gap requests. Do not estimate missing data as actual results. Proposed thresholds and estimates must be labeled and reviewed by the appropriate owner.

For an App input change, use the [native input evidence distinction](../omni-app-engineer/references/native-data-input.md): freeze expectations from independent source/query evidence and retain the exact population, types and completeness. A re-keyed export is a simulation, not an observed callback. For [demo aliases or geography](../omni-branding/references/demo-presentation.md), reconcile with original identities and unchanged measures; fictional names, approximate points and themed assets cannot establish customer operations or new analytical facts.

For migration, apply [behavior coverage](../omni-qa-analyst/references/migration-behavior.md): distinguish observed source calculation/filter context, inferred business intent, and accepted correction. Align comparison watermarks, parameters, timezone, persona, sort/limits and supported tolerances; do not tune a tolerance to hide an unexplained mismatch. Keep unsupported and missing behavior in scope rather than deriving the denominator from converted charts.

Send bounded requirements through [backend cowork](../omni-backend-handoff/SKILL.md) when the existing model cannot answer the agreed question. Preserve the selected migration route and allowed-change scope in the request; request a decision instead of assuming warehouse refactoring. For Tableau, use [the mapping checks](../omni-dashboard-designer/references/tableau-mapping.md) for FIXED/filter order, addressing/partitioning, parameters and totals. Pin each numerical expectation to its worksheet/placement and effective source state; retain unknowns instead of coercing them into comparable values. On return, re-evaluate the accepted meaning and independent expected cases against exact new definitions before narrative or design claims use them.

Escalate missing grain, ambiguous definitions, RLS uncertainty or unresolvable baseline differences to the orchestrator. Continue independent analysis, but do not certify those affected metrics. Warehouse changes belong to the model owner/DMA; presentation calculations cannot quietly redefine governed metrics.

For Looker, use [the mapping guide](../omni-dashboard-designer/references/looker-mapping.md). Distinguish query aggregation from post-query table calculations, hidden dependencies, pivots and merged-result limits. Require explicit observed filter, production/development, principal and cache/data context before claiming numerical parity. Share one metric contract across selected dashboard and App surfaces.

For Hex, use [the input/computation contract](../omni-app-designer/references/hex-experience-mapping.md#input-computation-and-state-contract). Classify shared metrics, Python/service computation and hypothetical local state without executing source code or inferring semantics from labels. Establish independent outputs and exact applied input/version context; a required unresolved computation stays visible on every dependent surface.
