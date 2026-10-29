---
name: omni-crystal-reports-migrator
description: Inventory and migrate Crystal report requirements into native Omni Reports using supplied extraction, formula, layout and export evidence. Use for Crystal classic or Enterprise reports; target composition belongs to the shared report designer and builder.
---

# Crystal Reports migration

Work through the [orchestrator](../omni-artifact-accelerator/SKILL.md) using the
distinct `report` surface and existing A–F gates. Reuse source evidence from the
[BusinessObjects specialist](../omni-businessobjects-migrator/SKILL.md) when it
identifies Crystal; WebI metadata capture does not qualify Crystal extraction.

Read the [source contract](../omni-artifact-translator/references/crystal-report-source-contract.md)
for the bounded supplied-extraction reader. Identify the exact engine, version,
hosting model and selected source scope first. An RPT filename is not an engine
version or a usable report definition. The package does not decode binary RPT,
install SAP software or run source formulas. An extraction marked SDK-produced
is still supplied evidence, not authenticated execution or complete coverage.

Retain sections, field placements, grouping, sorting, parameters/defaults,
suppression, record/group selection, commands, formulas, running-total reset and
evaluation order, shared variables, subreport links, printer settings and export
behavior. Preserve unresolved objects and external dependencies in the inventory.
PDF appearance, exported XML data and screenshots alone cannot establish all of
these semantics. Keep saved report data distinct from refreshed data.

Classify each calculation with the analyst/BI engineer: existing Omni reuse,
semantic or warehouse work via [DMA](../omni-backend-handoff/SKILL.md), target
report-runtime behavior, or explicit manual review. Print-time calculations and
suppressed records cannot be translated into SQL by name or appearance alone.
Do not evaluate formulas to discover their meaning.

After analytical understanding, the product owner resolves required formats,
exact-match obligations, approved design changes, access and freshness. The
[report designer](../omni-report-designer/SKILL.md) owns the three feasible target
concepts; the [report builder](../omni-report-builder/SKILL.md) owns the selected
native implementation. This specialist owns source evidence and mapping, not
publication, schedules or recipient sends.

Compare original and target numbers under matching parameters, principal,
locale and freshness. Inspect PDF/print and spreadsheet exports separately,
including section suppression, subreport totals, page footers and Excel types.
Retain incomplete extraction, missing dependencies, unsupported formulas and
unobserved native rendering as gaps. Source inspection is not migration parity.
