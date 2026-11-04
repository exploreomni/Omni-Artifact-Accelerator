# Domo source competencies

Use these competencies as responsibilities, not a requirement to spawn six agents.
Assign only work needed for the selected scope; the orchestrator keeps one run and
one decision history. A specialist may prepare evidence but cannot independently
accept its own implementation.

| Competency | Inspect and produce | Responsible handoff |
| --- | --- | --- |
| Source identity and acquisition | Actual tenant/principal, Page/App/Card IDs and native URNs, scoped inventory, original files, methods, versions and capability gaps | Orchestrator and translator |
| Analytical interpretation | DataSet/field and Beast Mode identities, expressions and execution scope, grain/population, summary metrics, filters and numerical expectations | Analyst, BI engineer and DMA |
| Visual and interaction mapping | Each placement, chart encodings, totals, formatting, controls, navigation, drill state and accepted differences | Dashboard/App designers and BI engineer |
| Application architecture | App Studio composition or custom App/Brick source, wiring, state, assets, external services and read/write classification | Product owner and App engineer |
| Security and operations | PDP/sharing/personas, embeds, AppDB, workflows, schedules, exports, secrets boundary and operational owner | Security review and backend/operations owner |
| Independent acceptance | Source-bound numerical, behavior, access, visual and operational cases; defects, gaps and scoped return evidence | QA and originating manager |

## Learn from evidence, then apply it

For a Card/Page slice, read [visual semantics](visual-semantics.md), inspect original
configuration and values, and produce a placement-to-query mapping with a separate
summary-metric check. For an App slice, additionally read [App behavior](app-behavior.md)
and produce a component/action/state inventory. For either, use
[acquisition and QA](acquisition-security-qa.md) to explain which observations remain
unverified and why. A useful readiness check is whether another analyst can locate
each original, reconstruct the intended population and identify the evidence needed
to disprove the proposed mapping.

Keep these evidence levels separate:

1. Vendor-documented behavior, with source date and applicable product context.
2. Behavior supported by the inspected source engine/helper contract and revision.
3. Available operations in this host and this principal's selected tenant.
4. Actual captured definitions, results, renders and observed interactions.
5. Independently verified target behavior and accepted differences.

A missing level cannot be supplied by a prose assertion from another level. In
particular, a UI export feature does not prove a packaged export client, and a
successful source query does not prove Card-result equivalence.

## Reuse the existing source engine

The [bridge](../../omni-artifact-translator/references/domo-agent-bridge.md) pins the
inspected producer at `55eba0ca0690fbf14f39eddbc8a04c94a720c155` and defines four
passive inputs: evidence bundle, source-evidence envelope, dashboard rebuild plan
and external redesign handoff. Keep their discriminator, original hashes and
assignment-only limits intact. A generic MigrationBundle, search response or
screenshot is not a substitute for an emitted contract.

Do not import/install the source engine to read those contracts. When a later
source revision is needed, require its separate source-contract and runtime review;
do not silently broaden the pin. Existing DataFlow evidence may inform lineage,
but upstream execution, warehouse implementation and target modeling remain scoped
backend work. The [run guide](../../omni-artifact-translator/references/domo-visual-run.md)
owns current executable commands and qualification limits.

## Keep incomplete work in the return

Every included source object and operational obligation needs a disposition:
preserved, proposed adaptation, accepted difference, excluded by actual scope
decision, blocked or unverified. Retain owner and next evidence when known, without
inventing commitments. Repeated placement, empty definitions, redaction, unavailable
PDP evidence and unsupported custom code must not disappear because the simple
Cards translated. Report the selected denominator and observed coverage separately.
