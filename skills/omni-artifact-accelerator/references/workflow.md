# Workflow and ownership

## Select the route

| Entry | First work | Semantic dependency | End product |
| --- | --- | --- | --- |
| Standalone new dashboard | Decision interview, existing topic inventory, metric contract | Reuse verified fields; request only real gaps | Native dashboard specification/candidate and QA |
| Standalone new app | User tasks, states, decision flow, workbook query contract | Same governed field bindings | Native Omni App design/code candidate and QA |
| Migration / lift and shift | Frozen artifact inventory, independent scope denominator, original behavior | DMA handoff or existing Omni bindings | Original-ID crosswalk, facet parity matrix, selected target artifacts |
| DMA continuation | Check curated semantic review and exact hashes | Reuse definitions without silently changing them | Analyst presentation and behavior work, upstream gap requests |
| Enhancement | Capture current content, settings, consumers and authorization | Reuse current definitions | Focused change, regression evidence and recovery |

Apps suit guided tools and bespoke interactions. Dashboards suit monitoring, comparison and exploration that fit supported native controls. Recommend the simpler maintainable surface, but honor the user's native delivery constraint. Do not turn every dashboard into an app to express a visual preference. An external embedded shell adds a distinct runtime, hosting and authentication owner; choose it explicitly.

## Role routing

| Role / skill | Owns | Produces | Must not decide alone |
| --- | --- | --- | --- |
| Orchestrator / omni-artifact-accelerator | Scope, decisions, dependency order and final package | project, task packets, integrated review | Business truth, permission grants, publication |
| Data analyst / omni-data-analyst | Questions, populations, interpretation, expected results | metric contract, analysis, numerical cases | Redefining a governed metric |
| BI engineer / omni-bi-engineer | Omni query/field bindings, filters, controls, dashboard candidate | query contract, crosswalk, content candidate | Warehouse redesign or access widening |
| QA analyst / omni-qa-analyst | Independent expected behavior and findings | QA matrix, evidence, regression report | Approving its own implementation |
| App engineer / omni-app-engineer | Native app code and runtime integration | app code, query binding manifest, runbook | Inventing SDK methods or backend routes |
| App designer / omni-app-designer | Task flow, states, responsive layout | screen and interaction specification | Changing data semantics |
| Dashboard designer / omni-dashboard-designer | Information hierarchy and supported visual behavior | tile/layout/control specification | Substituting unsupported native behavior |
| Data storyteller / omni-data-storyteller | Narrative, annotations and uncertainty | evidence-linked story and copy | Causal claims from association |
| Motion designer / omni-motion-designer | Purposeful transitions and reduced motion | motion/state contract | Animating numbers into false evidence |
| Branding / omni-branding | Brand interview, tokens, fonts, palettes, theme scope | brand contract and mappings | Organization-wide configuration changes |
| Design systems / omni-design-systems | Reusable frontend patterns and vendor guidance | component/state rules and a11y guidance | Importing native OS rules as web requirements |
| Translator / omni-artifact-translator | Source parsing, identity, behavior recovery | source inventory and facet mappings | Equating extraction with parity |
| Backend handoff / omni-backend-handoff | Frontend/backend request, response and impact reconciliation | pinned request, candidate exchange, consumer impact report | Model approval, production authorization, or backend implementation |

Workers can run concurrently when their inputs are stable. Analyst and brand discovery can overlap; app/dashboard designs share a frozen metric and token contract. BI bindings precede data wiring. Motion consumes named interaction states. QA can define tests early from original sources, then test final outputs independently. Coordinator resolves conflicts with explicit decisions rather than a majority vote.

## Stages and evidence

For a new experience or material redesign, the preferred design loop is **brief → distinct concepts → reasoned selection → prototype the critical task → observe → revise**. Use the [ideation playbook](../../omni-design-systems/references/ideation-playbook.md), the selected designer's pattern library and [usability protocol](../../omni-qa-analyst/references/usability-testing.md). Adapt the effort to the uncertainty; a known layout correction or faithful migration does not require a new concept exercise. Unavailable participants leave an explicit testing gap while authorized work continues.

Designers own alternatives, task structure and composition; the analyst owns numerical meaning and independent expectations; QA owns observations and findings. The app/BI engineer reviews feasibility before promising behavior. A needed backend field or definition follows the existing DMA handoff; a visual preference does not justify new warehouse work. Link decisions and evidence into existing working contracts and `START_HERE.md` rather than creating a parallel engagement lifecycle.

- **Discover:** decision, audience, sources, target, unknowns. Inventory can continue without full business acceptance.
- **Specify:** metrics, data/query contract, branding, screens/tiles, source-to-target facets, acceptance cases. Record review of consequential choices.
- **Build:** requested candidate files or authorized native draft. A local mockup remains a local mockup; show its bindings and missing native adapter.
- **Verify:** separate local consistency, numerical results, native rendering/behavior, effective access, performance, and business review.
- **Handoff:** one navigable entrypoint with selected artifacts, source crosswalk, evidence and remaining steps. Include maintainer, refresh/cost assumptions and recovery.
- **Publish:** only under an actual authorized destination workflow; verify final IDs, definitions, sharing and observed behavior. Do not retire source content automatically.

Resume from current saved contracts and the [current design-intent selection](design-intent.md). Persist missing required decisions rather than clearing them when one interview answer arrives. Reuse provided authorization and explicit omissions; optional styling may proceed as a proposal. Direct specialists read the same requirement/dependency chain as orchestrated workers. A changed source hash or definition requires impact analysis and rerunning affected checks, not repeating all intake. A changed token can require visual checks without rerunning numerical fixtures. A changed filter or query invalidates both results and affected interaction checks.

For a backend dependency, use the [cowork contract](../../omni-backend-handoff/references/cowork-contract.md). DMA owns the selected warehouse/semantic stages; the analyst orchestrator owns query consumers and UX. Send one coherent domain request and retain unresolved/declined responses. Use existing DMA scope/review records rather than repeating intake. Updated context/model hashes conservatively invalidate all declared data consumers because minimized catalog metadata cannot prove every backend effect. Independent branding or layout work can continue. In a stable baseline, complete declared dependencies support a narrower change review. Host delegation remains explicit and bounded; these scripts never launch a second orchestrator themselves.

## Analyst-lens migration coverage

For every page, visual, control, calculation, drill, link, action, bookmark, input and export in scope, record `exact`, `adapted`, `unsupported`, `unknown`, or `retire_proposed`. `Adapted` includes its meaning change and the real decision reference; `retire_proposed` is never deletion authority. Preserve filter scope/evaluation order, totals, sort/top-N, NULL versus zero, formats, timezone/currency, and role-specific behavior. Use screenshot/layout evidence for presentation and source/native tests for behavior. An export cannot certify its own completeness.

## Design completion

For material new work/redesign, retain a short visual-direction brief and at least two visibly different compositions using the same representative data. Compare grouping/task flow rather than palette alone. Resolve the chosen desktop/narrow design, chart encodings and states before calling the handoff complete. Feasibility review can alter the direction; record why. A working agent choice is not customer acceptance.

The implemented candidate returns to the designer with actual captures and deviations from the selected composition. The designer records specific hierarchy, type, spacing, alignment, chart-finish, brand and interaction-value findings. Engineering corrects them and provides a new version for retest. QA independently checks expected behavior; neither the implementer's self-review nor passing numerical tests closes this loop.

Choose completion wording from evidence, not from an overall success flag:

- **Candidate with named gaps:** required cases remain failed, blocked or not run; authorized provisional work can continue.
- **Design-quality complete:** selected craft, native readability, responsive and interaction cases pass for the exact candidate. This does not certify numbers or access.
- **Verified selected scope:** every required case in the selected scope passes or has a justified applicability exclusion. A failed required numerical case prevents this claim. Human usability, access, performance and business acceptance retain their own scope and results.

Use the existing contracts and QA lane records; these phrases are reporting guidance, not a second lifecycle. Reconcile every named required choice on each selected surface with its current implementation and observation. A broad craft pass cannot close an uninspected logo or primary-task requirement; publication does not resolve a missing choice. In final handoff, show fulfilled requirements, authorized omissions and remaining differences beside publication and DMA status. Legacy engagements without this record remain unassessed. Changed layout/tokens reopen affected visual checks; changed filters/queries also reopen numbers and interactions; changed candidate bytes stale its previous observations. Keep `START_HERE.md`, source/artifact pins and query bindings current as execution advances.

## User experience of the agent

Keep the analyst in control with small choices and a current artifact. Reuse already answered questions, show reasonable proposals when preferences are optional, and explain only material blockers. Each update should state what changed, what was learned, and the next useful action. Do not force the user to coordinate the specialists or answer twelve separate interviews.
