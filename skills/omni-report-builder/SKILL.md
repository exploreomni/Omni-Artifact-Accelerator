---
name: omni-report-builder
description: Prepare and implement reviewed native Omni Reports Beta designs using qualified report-definition and query-binding contracts. Use after report design selection; preserve native output fidelity and separate local candidates from rendering, publication and distribution.
---

# Omni report builder

Own report implementation under the [orchestrator](../omni-artifact-accelerator/SKILL.md).
Consume the [report designer](../omni-report-designer/SKILL.md)'s selected design,
BI query bindings and original source evidence. Use the explicit `report` surface;
never relabel a report as a dashboard or App to reach an available write tool.

Follow the shared dependency policy. Do not install or load ActiveReports, an SDK,
converter, font or rendering library without exact user sign-off. Omni's own
licensed runtime is a target capability to verify, not a dependency to reproduce
locally. No Blender or execution of imported scripts, macros or embedded code.

## Before authoring

Use the same A–F gates as every substantial artifact. Actual E selection and
detailed design are prerequisites for F, including JSON report definitions.
Capability inspection is read-only discovery; it must not become early coding.
Read [native report qualification](references/native-report-qualification.md),
then validate the selected [report contract](../omni-report-designer/references/report-contract.md).
Carry every unresolved requirement into the implementation handoff.

Confirm the exact destination, native Reports feature availability, report identity,
runtime/schema version, query field identifiers and available authoring interface.
Retain the current native definition before an authorized edit. Preserve sections,
IDs, expressions, query references and unknown properties; a broad AI rewrite
must not delete manually designed sections. Diff the whole selected definition.

## Build and reconcile

Use the reviewed data/query contract for each dataset, parameter and field. Bind
stable identifiers explicitly. Inspect grain, sort, filter order, grouping and
totals with the analyst/BI engineer; do not match fields by label or guess expression
equivalence. Source RDL, target RDLX-JSON and Crystal definitions are distinct.

When the native schema and authoring route are qualified, prepare the exact report
definition or bounded native-AI instructions from the chosen design. Tell native
AI which existing IDs/sections must survive, what may change and how to verify it.
Read back its output and compare bindings and layout intent. A prompt accepted by
Blobby is not evidence that the intended report was produced.

Use the guarded [local preparation and observation helpers](references/local-preparation.md)
to pin version 2 requirement/part mappings, definition bytes and per-format QA.
Supplied readback and export observations remain unauthenticated evidence; they
cannot grant execution authority or erase unknown native capabilities.

The current package supplies local report contracts, preparation, role routing and QA support;
it has no automatic native Reports API executor or universal report compiler.
If the requested host exposes no qualified CLI/API authoring path, return the
reviewable definition/design and binding handoff plus the exact missing operation.
Continue independent preparation; do not invent endpoints or bypass CLI-only
restrictions with browser automation, dashboard APIs or external hosting.

Freeze candidate bytes with the existing candidate history and record builder
identity. Apply security, UX/design, product-owner and independent QA feedback
after each iteration. Changes to paper, queries, parameters, fonts, sections or
export settings invalidate affected observations. Never overwrite accepted evidence.

## Evidence and delivery

Use [report QA](../omni-qa-analyst/references/report-qa.md) to reconcile values and
inspect actual rendered pages and requested exports. Check conditional sections,
group boundaries, labels, repeated headers, totals, page numbers, empty results,
font substitution and Excel sheets/types. A valid JSON file or visually plausible
first page cannot clear the complete report.

Keep local candidate, native authoring, export/render, effective access, publication,
scheduling and recipient distribution separate. Reuse actual authorization but
never infer sends or subscription creation from a report request. Report unobserved
lanes honestly. Existing source migrators and the supplied-source SSRS,
Power BI paginated and Crystal extraction readers provide evidence to this shared
target workflow. Reader coverage is bounded; it does not establish exact feature
parity, a Crystal binary decoder or automatic native Report publication.
