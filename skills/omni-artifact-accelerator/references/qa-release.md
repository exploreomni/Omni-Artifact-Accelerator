# Independent QA and delivery evidence

The QA analyst owns expected behavior before seeing implementation output when practical. Freeze source settings, watermark, timezone, populations and personas. A source report is a comparison baseline, not automatic metric authority. Approved business corrections need a separate expected result and difference explanation.

| Lane | Meaningful cases | Evidence limit |
| --- | --- | --- |
| Numerical | detail and totals, ratio recomputation, distinct counts, duplicated/unmatched keys, negative values, NULL/zero/empty, sparse periods, currency/calendar boundaries, filters before/after aggregation | Grand totals alone can hide wrong segmentation |
| Migration | every scoped page/tile/control/action mapped; source counts independently reconciled; parameters, listeners, top-N, totals and exports | Parsed JSON or a matching screenshot is not behavior parity |
| Native interactions | default/filter/reset, cross-filter/drill, URL reload/history, sort/pagination, app input states where selected, stale/error/retry | Tests must run in the actual target, with actual result bindings |
| Access | allowed and denied personas, RLS, hidden fields, content permissions, drill/export, restricted query tabs | Hiding a UI component is not access enforcement |
| Accessibility | keyboard traversal and visible focus, semantic labels, non-color cues, screen-reader/chart/table alternative, zoom/reflow, reduced motion | Automated scans complement manual tasks; do not claim universal compliance |
| Visual/brand | representative small/large viewports, long labels, many categories, empty/error/loading, light/dark when selected, actual font/logo loading | Token equality does not prove rendered readability |
| Visual craft | focal hierarchy, proportion, alignment, whitespace, type relationships, chart finish, brand expression and useful detail, compared with the chosen composition | Require concrete findings on actual captures; a screenshot's existence or a numerical pass cannot establish craft quality |
| Usability | non-leading decision tasks, explanation of scope/comparison, finding evidence, filter recovery, observed errors/assistance and retests | Critique and agent rehearsal are distinct from participant observation; a small observed sample is not population-wide proof |
| Performance | representative data/cardinality, first useful render, interaction latency, query count/cost, pagination/completeness and stale response cancellation | Record measured environment and budgets; do not invent universal SLOs |
| App security | client secret scan, untrusted text rendering, link/protocol validation, allowlisted network/settings, untrusted input and stale/racing responses | Source inspection does not establish sandbox or tenant isolation |

Each case records id, requirement/asset, source pins, independent expected outcome, actual outcome, method/tool, environment/persona, run observation, evidence path/hash, and `pass|fail|blocked|not_run|not_applicable`. Applicability exclusions need a reason. Gaps remain in the denominator. Only executed cases have pass rates.

Local helper verification, native results, access verification, human acceptance and publication are separate lanes. Imported receipts are assertions until independently corroborated. No generated JSON status can authorize a live write.

Check the assembled experience, including custom controls outside shared primitives.
Exercise hidden-to-visible transitions under the final CSS, scope changes across
destinations, warning/headline agreement and long labels at relevant small and large
sizes. A DOM `hidden` property check cannot establish that author styles leave the
element hidden. See the [bounded control cases](../../omni-app-engineer/references/control-primitives.md#assembled-control-regressions)
and bind actual rendered results to the exact candidate, viewport and state.

For new or materially redesigned experiences, use the [usability protocol and synthetic comprehension example](../../omni-qa-analyst/references/usability-testing.md). Record the evidence category and exact tested candidate; a local prototype may be task-tested while its native behavior remains unverified. Unavailable participants leave human testing `not_run` and do not prevent authorized provisional work.

Capture design deviations and the designer's disposition, then retest the revised native version. Do not assign a numerical beauty score. Before reporting verified selected scope, identify its required cases and check that none remain failed, blocked or not run. A narrow correction need not reopen unrelated numerical cases, and fidelity-preserving migration must not lose a source requirement in pursuit of a new composition.

For release handoff, provide exact candidate versions and target IDs, selected scope, diff, numerical and visual evidence, unresolved findings, permissions/settings impact, maintainer, refresh/cost assumptions, and recovery to previous content. Reuse existing authorization; request only genuinely missing authorization for the concrete external action. After a permitted mutation, reread actual content and test a bounded critical path. An ambiguous timeout needs reconciliation, not blind retry.

Use the existing delivery assessment to distinguish **prepared local candidate**,
**authorized candidate preview**, **verified selected scope** and **published/read
back**. Native preview can be necessary to obtain native observations; do not create
a circular demand for those observations before a separately authorized preview.
Some create routes publish immediately, so the actual authorization and description
must cover that side effect. A preview is not a lower-risk synonym for publication.
Missing rendering/access/participants remain gaps in the claim, not fabricated
passes. Preserve CLI-only restrictions without browser/headless workarounds.

Four resolved source consultations establish only their recorded review scope.
Carry warnings and unresolved findings into closeout, linked to current retests;
do not call the work clean merely because a stage is release-ready. Positive story
feedback does not silently accept visual quality, permissions or every destination.

Reconcile the current QA entrypoint as part of that handoff. Preserve the prior QA record, then make `contracts/qa.json` identify the selected candidate path/hash, current scoped review and publication evidence when available. Reopen affected findings until their exact-candidate retest passes. Check agreement with the project's selected artifact/design intent and `START_HERE.md`; updating only the narrative entrypoint leaves standalone QA resumes stale. Retained checks from an earlier candidate stay labeled historical, even when unchanged dependencies make them useful background. Never refresh their hashes or counts to imply execution on the new candidate. This is an agent handoff check, not an automatic capability of the existing helper.

Operational ownership matters: name a maintainer only when stated, document how queries/tokens are updated, preserve source IDs, and identify which upstream changes invalidate which evidence. Keep source retirement and wider rollout as separate decisions.
