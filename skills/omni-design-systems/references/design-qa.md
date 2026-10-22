# Design QA evidence

Select checks relevant to the artifact and its risk. A wording-only change does not require a full application test suite. For a new interface, test the important decision path using representative data and real target rendering.

| Area | What to verify | Evidence and failure handling |
| --- | --- | --- |
| Data clarity | Metric identity, units, date/timezone, period comparison, grain, active filters, denominators, precision, totals, null versus zero, and freshness are understandable. | Reconcile representative displayed values with the analyst/BI contract. A mismatch blocks the affected claim. |
| Hierarchy | A viewer can find the question, answer, and next action; an analyst can inspect supporting detail. | Capture full-size screens plus a page overview. Avoid a visually impressive overview that hides truncation in individual tiles. |
| Visual craft | Focal hierarchy, grouping/proportion, optical alignment, whitespace, type relationships, chart finish, brand expression and useful detail. | Apply [craft review](visual-craft.md) to substantial new/redesigned experiences or explicit quality problems. Bind annotated captures, deviations and revised-candidate retests to exact versions; a palette match or numerical pass does not close this case. |
| Usability | Intended users can interpret the question, scope, comparison and evidence and complete the selected task. | Use [non-leading task tests](../../omni-qa-analyst/references/usability-testing.md); retain observations, assistance, misinterpretations and retests. A critique or agent rehearsal is not human testing. |
| State coverage | Loading, empty, no matching rows, no permission, stale, partial, error, and success remain distinct where applicable. | Verify that a failed or inaccessible query cannot appear as zero or a successful empty result. |
| Responsive | Content remains usable at agreed widths, zoom/text settings, orientation, and browser context. Supported selection/filter context and usable focus survive reflow and return to a larger layout. | Record exact viewport, scale, target, and content fixture. Resolve clipping or overlap; a dense table may need a clear, keyboard-operable scroll region rather than disappearing columns. |
| Input and accessibility | Controls have names, meaningful order, visible focus, keyboard operation, clear errors, and non-color cues. Charts have a usable data/text alternative. | Combine automated checks with manual keyboard and appropriate assistive-technology use. Label checks not performed. Apply the project's accessibility standard and relevant exceptions from [vendor guidance](vendor-guidance.md). |
| Theme | Approved colors/fonts/assets work in each supported appearance, including actual hover, focus, disabled, and selected states. | Check foreground/background pairs, category identity across filters, logo visibility, font loading/fallback, and long/negative values. |
| Motion | Static and reduced-motion experiences preserve information, operation, focus, and completion signals. | Test preference changes, interrupted transitions, rapid filter changes, delayed/error responses, and an actual constrained target device where performance matters. |
| Security context | Restricted users cannot infer forbidden records from counts, annotations, exports, tooltips, caches, or error details. | Route data/security checks to QA and engineering. A presentation-level filter is not an authorization boundary. |
| Migration parity | Source identifiers, calculation/aggregation, filter defaults, interactions, and explicit accepted differences are traceable. | Compare source and target under the same representative scenarios; screenshots alone do not prove parity. |

Report each relevant result as **passed, failed, blocked, not run, or not applicable**, with artifact/version, scenario, evidence, and limitations. Separate design review, local prototype, native Omni verification, performance evidence, accessibility audit, and business acceptance. Do not collapse these into “validated.”

Designers return to the actual implementation and reconcile material deviations against the selected composition. Independent QA checks applicable expectations separately from the producer. An unresolved material craft defect keeps that case open; human usability, native behavior, access and business acceptance retain their own statuses.

The independent QA analyst owns acceptance evidence; specialists fix their own findings and provide reproducible verification material. The orchestrator resolves scope changes and conflicting requirements.
