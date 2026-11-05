# 5. Review and deliver

[Learning guide](README.md) · [Previous: choose](04-choose.md) · [Next: continue](06-continue.md)

**Outcome:** you can review the complete experience and understand what has actually been verified.

## F — Build, critique and refine

The target builder implements the selected direction from reviewed query and interaction contracts. For an App, an ambitious representative journey is an early checkpoint. It should express the defining experience, but it does not close review of the remaining destinations or outcomes.

Every implementation iteration retains these four perspectives:

| Review | What it should establish |
| --- | --- |
| Security | Appropriate data/resource handling, approved dependencies and preserved access boundaries |
| UI/UX | Task-fit composition, readable controls, coherent navigation and observed visual quality where rendering is available |
| Product owner | Coverage of the promised outcomes and complete consequential journeys |
| Independent QA | Numerical correctness, source behavior, interaction states, responsiveness and other applicable checks |

Creative critique must be independent of the builder and originating designer. The optional incremental policy can carry proven unchanged source-review evidence forward; changed or unobserved rendered/native behavior still needs appropriate checks. It does not require rebuilding or rereading everything after a small correction.

## Review a real task from beginning to end

Use the agreed audience and task, not just the opening screen:

1. Enter in the expected first-use or returning-use state.
2. Change scope or filters and confirm the numbers, claims and selections agree.
3. Inspect a comparison or entity, open the supporting detail, and return without losing context.
4. Try an empty result or error/retry path appropriate to the artifact.
5. Check the working destinations at the agreed device sizes, including keyboard and reduced-motion behavior where applicable.
6. Review exports or printed pages if they are part of the promise.

For a 3D view, also confirm that data marks stay attached to the correct geometry, labels remain readable and exact values are available without relying on perspective. For a Report, inspect page breaks, totals and the actual requested PDF/Excel outputs separately; one output does not establish another's quality.

## Ask what the evidence proves

| Evidence | What it can support | What remains separate |
| --- | --- | --- |
| Source/helper checks | Structure, recorded requirements, known invariants and specific tested logic | Real rendering, effective access and business acceptance |
| Rendered review | Observed composition, readability and responsive appearance at inspected sizes | Live query correctness and unexercised interactions |
| Native runtime observations | Tested data loads, interactions and behavior in the actual destination | Unchecked accounts, devices or output modes |
| Numerical and migration comparison | Agreement with independent expectations for the checked scope | Unsupported source behavior and other populations |
| Human acceptance | Your explicit judgment about the delivered scope | Unreviewed scope or future rollout permissions |

If a CLI/API-only boundary prevents visual inspection, the handoff should retain that gap and propose a permitted way to obtain evidence. It should not claim polish from source checks or open a browser without authority.

## Publish only the reviewed, authorized scope

Track local preparation, preview purpose, verified scope and publication status separately. In the [documented new-document route](../../skills/omni-artifact-accelerator/references/native-authoring.md#document-and-query-operations), creation publishes immediately: calling it a preview does not make it private or unpublished. Authorize the exact destination and intended audience before that write. A preview may be necessary to obtain runtime evidence, but a concept choice alone does not grant native-write permission.

Ask the handoff to include:

- The current artifact or local candidate location and exact version being discussed.
- The selected requirements, query definitions and data-as-of/refresh behavior.
- What was actually checked, in which context, and which findings remain open.
- Any rollout access checks, dependency decisions or native capability limitations.
- How to resume the same engagement and make a bounded change.

For Reports Beta, local preparation is not proof of a qualified native authoring interface. The package does not imply a universal report compiler or automatic Reports API executor.

**Checkpoint:** you can distinguish “prepared,” “rendered,” “tested in Omni” and “accepted.” Your decision is based on the current artifact and explicit gaps, not a general claim that all checks passed.
