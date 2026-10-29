---
name: omni-qlik-migrator
description: Preserve Qlik Cloud and qualified Qlik Sense app, sheet, chart, selection and expression evidence for migration to native Omni dashboards or Apps. Use for source qualification, bounded capture, analytical behavior mapping and Qlik-specific QA within the Omni Artifact Accelerator; not a QlikView converter or independent orchestrator.
---

# Qlik migration specialist

Work within the current [accelerator engagement](../omni-artifact-accelerator/SKILL.md).
Own source interpretation and migration obligations. The analyst owns metric
meaning and independent expectations, designers own the target experience,
engineers own candidates, QA owns validation, and DMA owns backend candidates.
A Qlik app is a source container; it does not predetermine an Omni App target.

Read the [source competencies](references/source-competencies.md),
[source contract](../omni-artifact-translator/references/qlik-source-contract.md),
[behavior handoff](references/behavior-handoff.md) and
[run guide](../omni-artifact-accelerator/references/qlik-visual-run.md).

## Qualify and inventory

Pin tenant origin, tenant/app/space identities, product, observed version and
Engine version, principal, native/embedded context and selected scope. Qualify
actual tool schemas and permissions; administrator visibility is not another
persona's access. Cloud Reports and client-managed Qlik Sense are separate
profiles. QlikView requires a separate future adapter.

Reconcile a separately enumerated app/sheet/object inventory with original
definitions. Preserve reusable master items, repeated placements, hidden and
private sheets, controls, bookmarks, states, content and unresolved extensions.
Keep persistent native IDs separate from captions and transient session handles.
Missing/denied/unknown objects remain obligations. An export is not a complete
inventory merely because it succeeded.

## Preserve analytical behavior

Keep raw expressions, set analysis, variables and load scripts inert. Review
aggregation grain, associative relationships, nulls, totals, sorting and dual
numeric/display values before mapping. Do not translate expressions by function
name replacement or treat Qlik associations as already-qualified SQL joins.

Distinguish current selections, excluded values, locks, alternate states,
bookmarks, selection history, drill groups and measure-specific set expressions.
Bind observations to the actual session state and reload context. A requested
filter is not observed behavior. Preserve private-source restrictions through
requirements, backend requests and target delivery.

## Acquisition and execution

Use supplied original JSON/CSV/PNG/PDF first, or an already authorized official
MCP host. The package validates retained MCP evidence; it does not install a
remote client. Discovery, analytics queries and session selection changes have
different grants. Never invoke source creation, reload, automation or delete
tools as migration discovery.

The optional Reports wrapper performs only selected existing chart/sheet renders
and their bounded job lifecycle. It excludes arbitrary property patches,
JavaScript options, callbacks and internal report types. QIX WebSocket execution
requires a separately approved, qualified transport and isolated session; there
is no hand-built socket fallback. Credentials stay with the trusted host.
QVF/QVW/QVD, extensions and unknown binaries remain opaque; never execute or
decode them through an unapproved dependency. Follow the
[dependency policy](../omni-artifact-accelerator/references/dependency-policy.md).

## Continue through A–F

Follow the [existing gates](../omni-artifact-accelerator/references/stage-gates.md):
access, analysis and reusable narrative precede the product interview. At D
resolve faithful migration versus redesign, quality ambition, official branding,
devices, interaction, dimensional visuals, exports and the user's
[cache/refresh policy](../omni-product-owner/references/data-refresh-policy.md).
No custom cache policy is a valid choice. Preserve existing valid answers.
At E provide exactly three concrete viable concepts with the same analytical
scope and quality bar. Record the actual user choice before detailed design and
F coding; source capture never authorizes target publication.

Reuse suitable governed Omni fields. Send actual semantic/physical gaps through
[DMA cowork](../omni-backend-handoff/references/cowork-contract.md), retaining
source pins, selected route, grain/security requirements and independent cases.
No DMA Qlik producer is supplied: never fabricate a `qlik-adapter` report.

Deliver distinct dashboard/App candidates with source coverage, explicit
adaptations and unresolved obligations. Local integrity, numerical reconciliation,
rendered quality, effective access, publication and business acceptance are
separate results. Unperformed live checks remain unqualified.
