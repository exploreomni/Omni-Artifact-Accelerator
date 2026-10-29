# Migration behavior and peer handoff coverage

Use this reference when a specialist consumes Domo, Sigma, or DMA evidence. It adapts patterns from the repositories below; it is not their runtime, an approval interpreter, or an implementation of their schemas. Read only the sections relevant to the selected source and task. Net-new work does not need a fabricated migration inventory.

## Preserve behavior, intent, and accepted change separately

Record three distinct things: what the source demonstrably does; the business interpretation proposed by the analyst; and an accepted correction or redesign, with its actual decision reference. A matching screenshot does not establish formulas or filter behavior. Matching source totals does not prove that the source implements the intended metric. A redesigned layout cannot silently change either meaning.

Retain exact source IDs, parent/placement identity, revision/hash, evidence location, query/filter context, and unresolved coverage. Use original observations and independently defined expectations alongside producer output. When source layout, control, action, or responsive evidence is absent, mark it unknown; a proposed target arrangement is not reconstructed source evidence.

## Behavior ledger

Maintain a reviewable ledger per selected Page/workbook/page and its child assets. Derive the complete expected set independently from scoped source evidence, not from the subset that converted successfully. Keep one disposition for each applicable behavior instance, including repeated placements of the same Card. A parent-level pass cannot close every child case.

| Facet | Preserve and map | Independent check |
| --- | --- | --- |
| Identity and coverage | Page/workbook, Card/element, placement, query, consumer, and source evidence IDs/revisions | Reconcile selected scope and child sets; surface missing, duplicate, stale, and unexplained extra items. |
| Query and metric | Exact fields/measures, grain, aggregation, grouping, sort/top-N, totals, null/empty handling, units and date semantics | Compare independent examples and dimensional slices; check fanout and non-additivity. |
| Filters and controls | Defaults, parameters, evaluation order, context, propagation, affected/unaffected queries, reset behavior | Run each distinct context; don't infer equivalent scope from similar labels. |
| Interaction and drill | Selection, drill sequence, destination, links, actions, writeback, bookmarks where present | Compare user-visible effect and failure behavior; retain unsupported actions explicitly. |
| Presentation | Mark type, formatting, source order, every placement, layout and responsive intent, annotations | Review source-bound evidence against actual target rendering; distinguish accepted redesign from parity. |
| Persona and security | Allowed/denied roles, row/column policies, visibility and derived-field dependencies | Test allowed and denied access plus leakage through derived values, totals, tooltips, exports, and errors where applicable. Hidden metadata or UI filters are not access-policy proof. |
| Operations and consumers | Schedules, alerts, recipients, exports, embeds, workflows, refresh/freshness, support ownership | Verify only within authorized operational scope; otherwise retain a named handoff or unresolved owner and its acceptance condition. Never silently drop these because the chart works. |

Use the orchestrator's facet outcomes (`exact`, `adapted`, `unsupported`, `unknown`, `retire_proposed`) with evidence and decision references. `Exact` requires observed equivalence; proposal-stage mappings remain proposed. Keep translator action dispositions such as `rebuild` or `manual_review` separately—they describe work, not parity. Preserve any source runtime's original enum and meaning as upstream metadata; do not relabel it as this package's verified state.

## Domo source packages

The inspected Domo implementation requires one current dashboard rebuild plan per selected Page. Its denominator covers every Card, query, placement, behavior, Topic/component binding, persona/security rule and operation. Non-query content Cards still have placement, formatting, access and operational behavior. Carry the exact supplied plan, source context and Topic/profile/decision references into the analyst ledger; do not flatten them into a chart count.

Domo QA compares source and target under aligned watermarks/logical snapshots, parameters, filters, timezone, persona, sort, limits, execution context and tolerance policy. Keep each mapped query's formatting, layout, responsive, security and persona cases distinct. Include relevant negative consolidation controls when an accepted model change merges or reuses semantics; a broad Page visual test or Topic security test cannot stand in for omitted query behavior.

These are coverage requirements learned from the Domo design. **This offline package cannot independently establish `dashboard_plan_ready`, store registration, `qa_suite_validation`, or production acceptance.** A supplied attestation remains a source claim until the owning runtime/authorized reviewer verifies its origin, current bindings and scope. Carry unresolved readiness as a gap. Provisional analyst design may continue within its actual authorization without pretending a Domo build gate passed. Execute a Domo-managed change through its own workflow; do not duplicate its approval files, authorization broker, receipts, or store events here.

## Sigma source packages

Record whether the source is the current operator `sigma-migrate` prepush workflow or the retained advanced Phase 0 specialist workflow. They are not an integrated autonomous lifecycle. The inspected operator path performs local preparation and has no target apply command; the advanced catalog describes restricted source/proposal roles and separate unimplemented gates. Its disabled advanced AI path is not re-enabled by a handoff or local approval reference.

Preserve the human-selected route; there is **no default**:

- `omni_semantic_reconstruction`: use existing warehouse relations; do not generate upstream dbt changes.
- `warehouse_first_refactor`: prepare supported upstream changes plus dependent Omni candidates; this does not establish deployment or calculation coverage.

If that choice is missing, continue authorized source inspection and route-neutral requirements work, but hold dependent target design/build. Separately preserve whether scope permits assessment only, dashboard-only reuse of an existing Topic, or model/topic/dashboard proposals. A route does not expand allowed changes. Topic-only additions were unsupported in the inspected operator path; recheck the source version before assuming a broader scope.

For chosen existing-Topic reuse, require exact model/connection/topic/field identities and revisions, grain, metric/filter definitions, joins, security visibility and compatibility evidence. The inspected bounded reuse path is a reviewed single-base-view inventory; do not infer multi-view/join compatibility or widen scope to make it work.

API model/dataset metadata is not a complete workbook UX. Carry source-bound layout/control supplements and per-object blockers; do not invent absent layout. Preserve `offline_preflight_passed` and `blocked` as upstream local statuses. They do not establish native behavior, effective access, business acceptance, or target-write authority. The originating runtime owns its terminal review. A chat decision, imported JSON, or peer receipt here cannot impersonate that review; use its documented operator workflow when running it.

## Periscope / Sisense CDT

Use the [CDT behavior handoff](../../omni-periscope-migrator/references/behavior-handoff.md)
with the same ledger and independent cases. Reconcile native Git tokens with
numeric dashboard/API IDs using retained evidence; neither captions nor generated
adapter IDs establish that mapping. Compare the independent widget/control listing
with definitions and rendered output, preserving omitted and non-query content.

Check inherited/local filter scope, parameters, defaults/reset and drill behavior.
Keep full-result versus displayed-result exports, requested versus observed state,
cache timing, persona and data watermark explicit. Unresolved identity, population,
filter or custom-code evidence prevents a numerical parity claim. Python/R, modules
and serialized assets remain inert. Verify target controls, current baseline and
separate dashboard/App returns; a file-coverage pass cannot close these cases.

## Metabase

Use the [Metabase behavior handoff](../../omni-metabase-migrator/references/behavior-handoff.md)
within the same independent ledger. Reconcile the expected dashboard/tab/dashcard
set against original definitions, including repeated cards, series, content and
unsupported objects. Card-query success cannot close missing placement coverage.

Check the entire query AST/SQL and per-placement parameter targets, linked-filter
dependencies, required/default/reset values, click/drill destinations and return
state. Partial supported clauses do not establish parity for a query with an
unsupported measure, filter, stage or join. Compare matched source definition,
observed state, original result bytes, principal, population, pagination, time zone
and cache evidence. Unknown state or incomplete rows remain inconclusive.

Recheck current native bindings, every applicable control and separate App/dashboard
receipts. Preserve the actual App refresh choice across design, implementation and
QA. Serialized content and administrator visibility cannot prove effective viewer
access. Numerical/source checks do not replace target interaction, rendered design,
negative access cases or business acceptance. Follow the [source contract](../../omni-artifact-translator/references/metabase-source-contract.md)
for supported intake rather than assuming every export or MCP tool is qualified.

## Two-way model cowork

Use [the backend handoff skill](../../omni-backend-handoff/SKILL.md) for a bounded request to DMA or the owning model workflow. Send the analytical decision, exact affected source/query/field IDs and pins, observed behavior, competing interpretations, allowed route/scope, proposed grain/filter/security/freshness requirements, and independent expected cases. Do not send an entire customer workspace or invent owners, definitions, approvals, or target bindings.

On return, reconcile the requested change with exact returned versions, declared supported/unsupported coverage and evidence. Rebind affected queries, interactions, persona cases, visuals and claims; rerun only the affected checks plus justified regressions. Keep unaffected work reusable. A backend return is candidate evidence until its authority and target behavior are established; the analyst package does not approve the model owner's work on receipt.

## Documentation and evidence freshness

Separate local design/prototype guidance from accepted user/operational guidance. Drafts may explain proposals when clearly labeled. Final guidance must link the exact accepted behavior and target versions, known differences, role expectations, operational handoffs and supporting QA. Preserve evidence classes such as `synthetic_local`, `development`, `staging`, and `production` exactly when supplied; a new filename or environment label cannot upgrade them. Domo-governed production documentation remains subject to its actual production report and registration workflow.

Changed source/query/metric/filter/security/target evidence invalidates affected tests and derived narrative or training. A change to branding alone may require visual checks without numerical reruns. A repaired artifact receives a new version and independent retest; its producer must not certify the repair as independent QA. Do not invent a separate reviewer identity if the host executed all roles inline.

## Inspected source references

Checked **2026-10-21** against local repository contents, read-only. These commit-pinned links identify the inspected maintained documentation/contracts; they do not attest live runtime or tenant readiness. Uncommitted acquisition-code changes were present in both checkouts and were outside this review's scope.

- Domo `55eba0ca0690fbf14f39eddbc8a04c94a720c155`: [README](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/README.md), [Omni BI developer](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/agents/omni-bi-developer.md), [migration QA](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/agents/migration-qa.md), [documentation/training](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/agents/documentation-training.md).
- Domo contracts: [dashboard rebuild plan v1](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/contracts/dashboard-rebuild-plan.v1.schema.json), [QA fixture v2](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/contracts/qa-fixture.v2.schema.json), [QA result v2](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/contracts/qa-result.v2.schema.json), [acceptance suite v1](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/contracts/qa-acceptance-suite.v1.schema.json), [QA/release boundary](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/docs/qa-acceptance-and-release-boundaries.md).
- Sigma `f4eda45b0f49dc7335496d028665f7339ed82e8f`: [README](https://github.com/atx-omni/SigmaMigrationAgent/blob/f4eda45b0f49dc7335496d028665f7339ed82e8f/README.md), [operator skill](https://github.com/atx-omni/SigmaMigrationAgent/blob/f4eda45b0f49dc7335496d028665f7339ed82e8f/.agents/skills/sigma-to-omni-migration/SKILL.md), [advanced Phase 0 catalog](https://github.com/atx-omni/SigmaMigrationAgent/blob/f4eda45b0f49dc7335496d028665f7339ed82e8f/agents/sigma/README.md).

Upstream repository links are provenance references, not bundled dependencies or a promise of access. Some source-engine repositories may require separate permission; offline contract import remains available without that access.

## WebFOCUS cases

Use the [specialist handoff](../../omni-webfocus-migrator/references/behavior-handoff.md)
for source obligations. Independently check DEFINE versus COMPUTE, PRINT versus SUM,
BY/ACROSS grain, totals, JOIN fanout, ordered styles, repeated placements, prompts,
cascades, drill/Auto Linking and custom container behavior. Bind exports to actual
state, principal, population, preview mode/limit stage, watermark and freshness.
An interactive document export need not contain the browser's computed view.
Unknowns keep parity inconclusive; native readback does not prove effective access,
rendered quality or ReportCaster replacement. Report procedures remain inert during
package checks, and runtime execution requires separate qualification and authority.

## ThoughtSpot cases

Use the [specialist handoff](../../omni-thoughtspot-migrator/references/behavior-handoff.md).
Compare distinct saved/pinned/inline identities and repeated placements; verify
linked filters/exclusions, tab/group/private-view scope, runtime overrides,
parameters/reset, custom actions and export selection. Require observed population,
completeness, aggregation/limit stage and freshness as well as numerical equality.
Source cache declarations never override the selected target refresh policy.
Retain missing/unsupported obligations and separate App/dashboard acceptance.
MCP discovery is not native definition evidence; session completion is not saved
Answer identity. Fixture passes do not prove live effective access or rendering.

## Qlik

Use the [specialist handoff](../../omni-qlik-migrator/references/behavior-handoff.md).
Verify selection/alternate-state/bookmark populations, locked/excluded values,
master-item reuse, totals and expression scope. Require full qualified result
regions with straight/pivot mode and exact source/target state, freshness and
persona binding. Test Section Access row/column restrictions independently.
A private or unsupported item stays in scope accounting until explicitly resolved;
no screenshot, partial export, parser pass or successful publish closes acceptance.

## MicroStrategy / Strategy

Use the [behavior handoff](../../omni-microstrategy-migrator/references/behavior-handoff.md).
Check independent coverage, source-byte continuity, repeated placements, prompt
keys/defaults/unanswered states, selector readback and all four filter stages.
Bind source results to definition, instance, project/principal, observed state
and freshness. Test raw/formatted metric values, attribute forms, totals, nulls
and pagination independently. Unsupported result shapes are inconclusive.

Keep numerical, rendered, interaction, effective-access and business acceptance
lanes separate. Metadata success or a consistent MCP response is not query or
render authority. Exercise denied identities, drift, expired/uncertain instances,
credential echoes and owned-only cleanup in the qualified host. A source-only
fixture pass cannot certify a live tenant, a sandbox or actual user access.

## Cognos

Use the [behavior handoff](../../omni-cognos-migrator/references/behavior-handoff.md).
Test required/default/empty prompt states, detail versus summary filters,
aggregation and totals, conditional rendering, repeated query placements,
drill-through parameter transfer and return, pagination/export, and effective
package/data-module permissions. Preserve excluded, denied and unobserved source
scope. Report XML cannot establish result/state parity: the current comparison
path stays inconclusive with `source.cognos_result_binding_unqualified` until a
qualified result-evidence adapter exists. Do not relabel raw CSV equality as
Cognos acceptance or substitute a manual observation to bypass this finding.

## BusinessObjects

Use the [behavior handoff](../../omni-businessobjects-migrator/references/behavior-handoff.md).
Reconcile original inventory, provider scopes, merged dimensions, calculation
contexts, prompts/controls, report/section totals and exact state/result evidence.
Preserve unknowns and partial refresh. Check data-mode, row-limit and aggregation
context before claiming comparable populations. Separate Universe security and
Crystal print/delivery obligations from WebI visual correctness.

Source comparisons require a case-pinned capture, typed raw normalization and
complete observed provider/state evidence. Equal unbound files remain inconclusive.
Snapshots, metadata reads and rendering do not establish effective user access,
full source extraction or business acceptance. Target caching remains the user's
explicit policy, not an inherited source default.
