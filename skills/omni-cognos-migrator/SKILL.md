---
name: omni-cognos-migrator
description: Inventory supplied IBM Cognos report XML and preserve query, layout, prompt and delivery obligations for migration to Omni dashboards or Apps. Use inside the Omni Artifact Accelerator; Cognos dashboards and connected acquisition require separate manual evidence and qualification.
---

# Cognos migration specialist

Work inside the existing [accelerator engagement](../omni-artifact-accelerator/SKILL.md).
Own Cognos source interpretation and coverage; reuse the product owner, analyst,
BI engineer, designers and independent QA. Do not create another orchestrator or
infer the Omni target from a source artifact's name.

Read [source competencies](references/source-competencies.md) for IBM behavior
and version boundaries, [assignments](references/subagent-assignments.md) for
bounded collaboration, and [behavior handoff](references/behavior-handoff.md) for
acceptance obligations. The [source contract](../omni-artifact-translator/references/cognos-source-contract.md)
and [run guide](../omni-artifact-accelerator/references/cognos-visual-run.md) describe
the implemented local path.

## Start with original evidence

Record the actual package revision, original request, Cognos product version,
source identity, report ID/content path and principal. Preserve approved source
and intended user choices. Keep the original UTF-8 report XML and independently
supplied expected inventory: queries, pages, containers, repeated placements,
prompts, navigation, conditional content and delivery requirements. An XML name
or positional locator is not a native content-store ID.

The current adapter inspects supplied report XML only. It does not connect to
Cognos, execute report queries, import a dashboard specification, run embedded
JavaScript or obtain credentials. Source dashboard JSON, Active Report runtime,
Framework Manager models and data modules remain separate evidence requiring
review; do not present them as parsed report XML or a supported connected API.

## Preserve analytical and delivery behavior

Keep query expressions, detail and summary filter stages, aggregate rules,
parameter use/display values, cascade/default/required behavior and query bindings
traceable to the original XML. Preserve unknown constructs and dependencies as
obligations; this is not an expression, SQL or dimensional-model compiler.

Treat drill-through, page sets, master-detail, conditional rendering, print/export
requirements and bursting as behavior to assess independently. A report export
does not prove its recipient population, delivery permissions or effective user
access. Do not copy email recipients, schedules or signons into target automation.

## Follow the existing A–F gates

For a new engagement, A verifies the selected data and user's access; static XML
alone cannot complete A. B establishes analysis and independent numerical
expectations; C produces a reusable evidence-linked narrative. At D resolve
fidelity/redesign, native dashboard/App/both, audience, ambition, branding, devices,
exports and interaction/visual preferences. Ask the independent target App
[cache/refresh policy](../omni-product-owner/references/data-refresh-policy.md)
question; source cache settings do not choose the answer. At E present exactly
three concrete viable concepts and record the actual user selection before
detailed design and F coding. Reuse valid prior decisions for an existing
engagement; migration is not a blanket exemption from the gates.

Reuse governed Omni bindings first. Send genuine grain, relationship, formula or
security gaps through [DMA cowork](../omni-backend-handoff/references/cowork-contract.md).
No Cognos DMA producer is supplied. A task packet or local hash cannot grant
source execution, dependency installation or native writes. Keep numerical,
visual, interaction, effective access, publication and business acceptance
separate, with unobserved lanes retained in the delivery.
