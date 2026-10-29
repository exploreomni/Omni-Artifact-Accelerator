# Independent report QA

Treat report quality as multiple evidence lanes. Local structural checks cannot
certify native rendering, numerical equivalence, effective access or acceptance.
Use the original requirements/source exports and independent expected numbers;
do not derive every expectation from the builder's report.

Bind every observation to candidate bytes, native identity (when observed), query
definitions/results, parameter values, persona, locale/timezone, data-as-of,
paper/margins, fonts/assets and exact export configuration. Retain output hashes,
page count and images of inspected pages. Missing or changed inputs invalidate
the affected check. Report references are not authentication or write authority.

| Lane | Meaningful checks |
| --- | --- |
| Numbers | Dataset completeness/grain, sort and filters, null/error distinctions, group/sub/grand totals, conditional populations and parameter changes |
| Pagination | First/last page, exact-full and first-overflow page, group crossing a page, repeated headers, keep-together, row split, footer/page numbers and no blank trailing pages |
| Typography/layout | Long text, multilingual glyphs where applicable, font substitution, clipping, alignment, units, whitespace, minimum legibility and image crop |
| Outputs | PDF/print page geometry; Excel sheet names/order, types, repeated headers, merged cells and totals independently; all requested formats accounted for |
| Access | Actual intended user and restricted persona, parameter/recipient boundaries, resource loading and exported content; admin success is insufficient |
| Performance | Representative data volume, render/export time and bounded size; never invent an SLA from a local check |
| Accessibility/acceptance | Reading order, textual equivalents, applicable PDF accessibility requirements and actual owner acceptance; visual inspection alone does not prove tagged-PDF compliance |

Inspect all pages for a small report. For large reports, retain a complete page
inventory and explain representative sampling and its unobserved remainder.
Do not label the entire report verified from one screenshot. Compare the selected
design/source and the native output; a standalone prototype is a separate lane.

Source-only SVG and JSON remain unrendered. PDF bytes or a successful export status
are not proof of visual quality. Preserve CLI/API-only limits; request no automatic
renderer installation or browser workaround. Record `not_run`/blocked for missing
runtime evidence and continue the independent numerical and contract checks.

Review designer and builder work independently. Keep product-owner acceptance,
security review, design critique and QA findings separate. A must-have missing
section, concealed source error or unexplained total discrepancy blocks acceptance.

## Candidate-bound coverage

The version 2 report contract maps canonical requirements to real sections,
parameters, outputs and acceptance IDs. The local
[preparation/observation helper](../../omni-report-builder/references/local-preparation.md)
freezes those IDs and derives pending cases per output format. Recompute its
coverage before a frontend/DMA return; do not reuse a PDF observation to clear
Excel or one parameter population to clear another.

Retain the native readback, actual export bytes and context alongside independent
expectations. Same-byte readback is only definition agreement. A supplied export
receipt with a PDF/XLSX signature remains an unauthenticated observation; the
helper never renders it or executes Omni operations. Source-only passes cannot
clear pagination, typography, access or performance lanes. Keep unobserved
scenarios and version 1 mapping gaps visible rather than converting them to a
blanket pass. Do not treat declared requirement links as proof that the original
product request was fully understood; perform the original-request review too.
