---
name: omni-report-designer
description: Design page-precise tabular and paginated Omni Reports, including print, PDF and spreadsheet output requirements. Use for native Reports Beta composition and report migration target design, distinct from interactive dashboards and Apps.
---

# Omni report designer

Own report composition under the existing [orchestrator](../omni-artifact-accelerator/SKILL.md).
Use the explicit `report` surface; an App print stylesheet or dashboard export is
not a substitute for a requested native Report. Reuse analyst, BI, branding and
product-owner decisions. The [report workflow](../omni-artifact-accelerator/references/report-workflow.md)
defines the common handoff to the [builder](../omni-report-builder/SKILL.md).

Follow the existing dependency policy and A–F sequence. Read-only feasibility can
inform access/analysis; product composition starts after A–C and the D interview.
At E offer exactly three concrete, feasible report directions with the same data
scope and quality bar. Retain the actual selection before detailed design and F.
For a source-faithful migration vary appropriate typography/density or approved
composition choices without removing required fields, page rules or delivery.
A focused repair reuses the accepted selection.

## Design for the delivered page

Resolve the [report interview](../omni-product-owner/references/report-interview.md)
through the product owner. Use [page craft](references/page-craft.md) for the
selected layout. Capture physical units, paper size/orientation, printable body,
margins, running headers/footers, page numbering, group/section boundaries,
repeating table headers, totals and conditional visibility. Distinguish grouping
in a query from presentation grouping and repeat totals from recalculated totals.

Specify long-text wrapping, blank/null/error presentation, zero-row output,
large groups, row splitting, keep-together rules and deliberate continuation.
Record exact field/parameter IDs and source grain with the BI engineer. A column
label is not a field binding. Responsive viewer zoom must not change physical
page dimensions or silently shrink text to fit.

PDF/print and Excel are separate deliverables. Define whether Excel is a visual
facsimile or analyzable data, expected sheets/names, data types, repeated headers
and totals. Never infer worksheet behavior from PDF page breaks. Ask which output
takes priority when their requirements conflict; retain any approved difference.

Keep the accepted decisions in the existing design-intent requirements. The
selected design adds `report_contract` according to the
[contract reference](references/report-contract.md); this is an implementation
projection, not another interview or approval ledger. Destinations represent
actual report pages/sections. A one-page report needs no fictional second screen;
its journey can be parameter selection, rendering, inspection and export.

## Native fit and independent review

Treat Reports as Beta until the product's release status is verified otherwise.
Pin tenant/version, available authoring interface, output format and supported
features; use [capability qualification](../omni-report-builder/references/native-report-qualification.md).
Vendor engine documentation is learning material, not proof of Omni's deployed
version, license, API, exporter or field-binding contract.

Deliver page/section specifications, representative visuals, query/field mapping,
format-specific acceptance cases and unresolved native requirements. Static SVG
can explain a proposal under CLI-only constraints but is unrendered evidence.
Independent QA must inspect actual rendered boundary cases and final exports for
pagination, clipping, font substitution and correct values. Source validation
cannot certify pixel-perfect output. Never silently drop a subreport, section,
legal footer or mandatory field to make a report fit.
