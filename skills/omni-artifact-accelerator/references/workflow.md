# Workflow and ownership

The shared [package-use policy](dependency-policy.md) applies to every route and worker. Routing a responsibility grants no package, runtime, installation or publication authority.

All new engagements, including migration and enhancement modes, follow the authoritative
[data-first A–F sequence](data-first-product-workflow.md). Recover existing choices,
but finish scoped user-access verification, analysis and a reusable narrative
before artifact discovery. Three distinct viable options and the user's selection
precede detailed design and coding. Reuse valid evidence and choices in those
checkpoints; historical engagements retain their recorded policy. General
direct-design advice does not bypass a current gate.

## Select the route

| Entry | First work | Semantic dependency | End product |
| --- | --- | --- | --- |
| Standalone new dashboard | A–C: verify data/user access, qualify analysis/queries, create reusable narrative; then D–F | Reuse verified fields; request only real gaps | User-selected native dashboard specification/candidate and QA |
| Standalone new app | A–C: verify data/user access, qualify analysis/queries, create reusable narrative; then D–F | Same governed field bindings | User-selected native Omni App design/code candidate and QA |
| Migration / lift and shift | Frozen artifact inventory, independent scope denominator, original behavior | DMA handoff or existing Omni bindings | Original-ID crosswalk, facet parity matrix, selected target artifacts |
| DMA continuation | Check curated semantic review and exact hashes | Reuse definitions without silently changing them | Analyst presentation and behavior work, upstream gap requests |
| Enhancement | Capture current content, settings, consumers and authorization | Reuse current definitions | Focused change, regression evidence and recovery |

Apps suit guided tools and bespoke interactions. Dashboards suit monitoring, comparison and exploration that fit supported native controls. Recommend the simpler maintainable surface, but honor the user's native delivery constraint. Do not turn every dashboard into an app to express a visual preference. An external embedded shell adds a distinct runtime, hosting and authentication owner; choose it explicitly.

## Role routing

| Role / skill | Owns | Produces | Must not decide alone |
| --- | --- | --- | --- |
| Orchestrator / omni-artifact-accelerator | Scope, decisions, dependency order and final package | project, task packets, integrated review | Business truth, permission grants, publication |
| Product owner / omni-product-owner | Audience, outcomes, priorities, experience promise and product fit | Private discovery evidence, canonical intent proposals, derived North Star and bounded handoff | Composition, metric truth, independent QA, dispatch or permission grants |
| Data analyst / omni-data-analyst | Questions, populations, interpretation, expected results | metric contract, analysis, numerical cases | Redefining a governed metric |
| BI engineer / omni-bi-engineer | Omni query/field bindings, filters, controls, dashboard candidate | query contract, crosswalk, content candidate | Warehouse redesign or access widening |
| QA analyst / omni-qa-analyst | Independent expected behavior and findings | QA matrix, evidence, regression report | Approving its own implementation |
| App engineer / omni-app-engineer | Native app code and runtime integration | app code, query binding manifest, runbook | Inventing SDK methods or backend routes |
| 3D modeler / omni-3d-modeler | Task-justified geometry, units, materials, hierarchy and stable identity | model brief, editable SceneSpec, geometry/asset handoff | Installing/loading runtimes, approving asset promotion, redefining metrics or inventing verified dimensions |
| App designer / omni-app-designer | Task flow, states, responsive layout | screen and interaction specification | Changing data semantics |
| Dashboard designer / omni-dashboard-designer | Information hierarchy and supported visual behavior | tile/layout/control specification | Substituting unsupported native behavior |
| Data storyteller / omni-data-storyteller | Narrative, annotations and uncertainty | evidence-linked story and copy | Causal claims from association |
| Motion designer / omni-motion-designer | Purposeful transitions and reduced motion | motion/state contract | Animating numbers into false evidence |
| Branding / omni-branding | Brand interview, tokens, fonts, palettes, theme scope | brand contract and mappings | Organization-wide configuration changes |
| Design systems / omni-design-systems | Reusable frontend patterns and vendor guidance | component/state rules and a11y guidance | Importing native OS rules as web requirements |
| Translator / omni-artifact-translator | Source parsing, identity, behavior recovery | source inventory and facet mappings | Equating extraction with parity |
| Periscope migrator / omni-periscope-migrator | CDT product/source qualification, capture/state and source-specific behavior coordination | pinned CDT evidence, identity crosswalk, mapping obligations and handoff | Selecting a different product, executing source code, native writes or independent acceptance |
| Metabase migrator / omni-metabase-migrator | Metabase source qualification, query/placement/parameter preservation and migration coordination | pinned source scope, captured state, mapping obligations and handoff | Dropping unsupported semantics, source authoring, native writes or independent acceptance |
| Backend handoff / omni-backend-handoff | Frontend/backend request, response and impact reconciliation | pinned request, candidate exchange, consumer impact report | Model approval, production authorization, or backend implementation |

Workers can run concurrently when their inputs are stable. On every new engagement, parallel work must preserve A–F dependencies: analyst/BI work follows access evidence, narrative follows analysis, and artifact/brand discovery follows narrative. Supplied preferences can be retained at intake. App/dashboard designs share current metric, narrative and token contracts. BI bindings precede data wiring. Motion consumes named interaction states. QA can define cases early from original sources, then test outputs independently. The coordinator resolves conflicts with explicit decisions rather than a majority vote.

For CDT migrations, the [Periscope specialist](../../omni-periscope-migrator/SKILL.md)
owns only the source-specific slice. Recover the existing source run and use shared
translator, analyst, backend, design/build and QA contracts; do not create a parallel
lifecycle. Reuse valid accepted design evidence within the applicable checkpoints;
all new engagements follow A–F, and historical policy/journal records remain in
force. Source capture authority, user design selection and native publication are
separate decisions. Read the [run guide](periscope-visual-run.md) for supported routes.

For Metabase, the [source specialist](../../omni-metabase-migrator/SKILL.md) owns the
bounded source slice within this same lifecycle. Use the [run guide](metabase-visual-run.md)
and preserve every selected tab/placement/control independently of query conversion.
All new engagements, including migration mode, follow the current A–F checkpoints:
three viable options and actual user choice precede coding. Reuse valid historical
decisions under their recorded policy. The specialist cannot replace design
selection, source-query authorization, native grants or independent QA. Semantic
gaps use the existing normalized DMA request route, not a fabricated source adapter.

For substantial work, use the [product owner](product-intent.md) to recover answers
and federate requirements. For new products, the artifact interview follows A–C.
It resolves material gaps and returns
intent to the orchestrator; it does not dispatch another team. Brand/metric specialists
ask only their unresolved questions through shared intake. Focused repairs bypass
unnecessary discovery. The canonical intent and its checked North Star travel with
bounded packets; specialists return coverage, conflicts and feasible alternatives.

## Experience continuity

For substantial new experience work or a design-quality correction, apply the [shared experience brief](../../omni-design-systems/references/experience-brief.md). Reconcile the user's already stated quality expectations before asking for missing choices. Resolve first encounter, returning-user route, art direction, primary action and relevant constraints in the existing selected design and [named intent requirements](design-intent.md#experience-requirements). Optional imagery, motion and exact fonts remain optional unless the brief makes them consequential requirements.

Design, branding, engineering, storytelling, motion and QA use the same selected intent, including on direct invocation. At dispatch/resume compare the packet's `design_context.selected_intent` with the current `intent-check` selection and recheck its inputs; an old packet is not updated automatically. New feedback creates a versioned decision and affected work, not a second interview for every specialist. Independently useful analyst/backend work can proceed without the visual asset bundle.

Use the read-only [packet-check command](design-intent.md#current-context-and-resume) to perform that comparison for issued handoffs. Keep `START_HERE.md` aligned with the derived current-context index and list superseded proposals as historical. Supply runtime inputs, callback evidence and authorized demo aliases explicitly when the assigned task depends on them. A descriptive path is not a pinned input, and a consistent handoff is not proof that omitted dependencies are unnecessary.

Keep one trace in the design/review records: `user requirement → selected composition/behavior → implementation → observation/gap`. Hold task and data constant across frontend alternatives. Record material engineering substitutions and return them for designer critique. The [context studio](../../omni-design-systems/references/experience-context-studio.md) demonstrates this with original synthetic content; it is not the required layout for future work.

## Stages and evidence

For a new product or product reconception, use **A–C evidence/narrative → artifact brief → three distinct viable options → user selection → detailed design → cohesive implementation → security/UI/UX/PO/QA review → revision**. Use the [ideation playbook](../../omni-design-systems/references/ideation-playbook.md), designer's pattern library and [usability protocol](../../omni-qa-analyst/references/usability-testing.md). A known layout correction or faithful migration reuses existing decisions. Unavailable observation leaves an explicit testing gap; it does not supply a missing user selection.

The PO owns product priorities and fit; designers own alternatives, task structure and composition; the analyst owns numerical meaning and independent expectations; QA owns correctness observations and findings. A creative reviewer different from the builder and originating designer critiques the exact candidate. The app/BI engineer reviews feasibility before promising behavior, preserving the requested outcome when proposing a supported alternative. A needed backend field or definition follows the existing DMA handoff; a visual preference does not justify new warehouse work. Link decisions and evidence into existing working contracts and `START_HERE.md` rather than creating a parallel engagement lifecycle.

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

For new products/reconception, retain the three-option comparison and actual user selection from stage E. Use the same core narrative and representative evidence; vary experience structure and task flow rather than palette alone. For focused changes or an already selected product, a reasoned direct treatment is sufficient. Resolve the selected desktop/narrow design, chart encodings and states before calling the handoff complete. If feasibility requires changing the selected product materially, return that decision to the user. A working agent choice is not customer acceptance.

The implemented candidate returns to the designer with actual captures and deviations from the selected composition. The designer records specific hierarchy, type, spacing, alignment, chart-finish, brand and interaction-value findings. Engineering corrects them and provides a new version for retest. QA independently checks expected behavior; neither the implementer's self-review nor passing numerical tests closes this loop.

Choose completion wording from evidence, not from an overall success flag:

- **Candidate with named gaps:** required cases remain failed, blocked or not run; authorized provisional work can continue.
- **Design-quality complete:** selected craft, native readability, responsive and interaction cases pass for the exact candidate. This does not certify numbers or access.
- **Verified selected scope:** every required case in the selected scope passes or has a justified applicability exclusion. A failed required numerical case prevents this claim. Human usability, access, performance and business acceptance retain their own scope and results.

Use the existing contracts and QA lane records; these phrases are reporting guidance, not a second lifecycle. Reconcile every named required choice on each selected surface with its current implementation and observation. A broad craft pass cannot close an uninspected logo or primary-task requirement; publication does not resolve a missing choice. In final handoff, show fulfilled requirements, authorized omissions and remaining differences beside publication and DMA status. Legacy engagements without this record remain unassessed. Changed layout/tokens reopen affected visual checks; changed filters/queries also reopen numbers and interactions; changed candidate bytes stale its previous observations. Keep `START_HERE.md`, source/artifact pins and query bindings current as execution advances.

## User experience of the agent

Keep the analyst in control with small choices and a current artifact. Reuse already answered questions, show reasonable proposals when preferences are optional, and explain only material blockers. Each update should state what changed, what was learned, and the next useful action. Do not force the user to coordinate the specialists or answer twelve separate interviews.

## First-delivery integration

For substantial App work, use [requirement coverage and the first-delivery loop](first-delivery.md) before scaling the implementation. `plan` assigns applicable capabilities to existing roles; `experience-check` checks declared requirement/destination coverage, not visual quality. Bring the first assembled journey back to the designer, then review every consequential destination. Retain runtime limitations and unchanged migration/DMA authority.

The first slice must represent the intended ambition, not only a convenient query
and record drill. Product-fit recommendation, independent creative critique and
correctness remain separate. Under CLI-only constraints, fix source-observable
requirement loss while leaving rendered quality unobserved; more structural checks
cannot close that lane. No fixed layout or extra approval round is required.

WebFOCUS migrations assign [omni-webfocus-migrator](../../omni-webfocus-migrator/SKILL.md)
in the same engagement. Use the [run guide](webfocus-visual-run.md) to bind original
source, page occurrences and runtime obligations before backend/design continuation.
The source specialist adds neither a parallel orchestrator nor target-write authority.

ThoughtSpot migrations assign [omni-thoughtspot-migrator](../../omni-thoughtspot-migrator/SKILL.md)
inside the current engagement. Its [run guide](thoughtspot-visual-run.md) covers
source qualification, JSON TML/original mapping, independent denominator,
state-bound evidence and source-specific behavior. The specialist coordinates
with analyst/design/engineering/QA roles; it is not a second orchestrator or a
backend compiler. Typed source routing never authorizes early coding or writes.

Qlik migrations assign [omni-qlik-migrator](../../omni-qlik-migrator/SKILL.md)
inside the current engagement. The [run guide](qlik-visual-run.md) preserves
original definitions, independent scope, selected-state evidence and source
security obligations. The specialist cannot bypass A–F, redesign metrics,
activate dependencies or grant publication. Backend gaps use the normal DMA
requirements exchange; a native Qlik parser is not assumed.

Strategy/MicroStrategy migrations use
[omni-microstrategy-migrator](../../omni-microstrategy-migrator/SKILL.md) inside the
current engagement. Follow the [run guide](microstrategy-visual-run.md), with
independent inventory, original definitions, observed instance/prompt/selector
state and separate execution/export grants. Keep A–F, actual three-option choice,
existing Omni reuse and scoped DMA exchange intact. Unknown source profiles and
unperformed access/render/acceptance checks remain unresolved.

Cognos migrations use [omni-cognos-migrator](../../omni-cognos-migrator/SKILL.md)
inside this engagement. Follow the [run guide](cognos-visual-run.md) for retained
report XML, independent selected inventory and behavioral obligations. Dashboard
specifications, results and effective access require separate qualified evidence;
the report reader does not provide an execution or parity shortcut.

BusinessObjects migrations use [omni-businessobjects-migrator](../../omni-businessobjects-migrator/SKILL.md)
inside this engagement. Follow the [run guide](businessobjects-visual-run.md).
Preserve separate WebI, Universe and Crystal profiles, source/provider context,
independent inventory and traceable calculation obligations. Local source scope
cannot bypass A–F, select a target cache policy or authorize source/native writes.
