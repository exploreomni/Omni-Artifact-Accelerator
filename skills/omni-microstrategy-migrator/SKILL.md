---
name: omni-microstrategy-migrator
description: Preserve Strategy and MicroStrategy dashboard/dossier, report, document, metric, prompt and selector evidence for migration to native Omni dashboards or Apps. Use for source qualification, guarded capture, semantic behavior mapping and source-specific QA within the Omni Artifact Accelerator.
---

# MicroStrategy migration specialist

Work inside the current [accelerator engagement](../omni-artifact-accelerator/SKILL.md).
Own source interpretation, coverage and migration obligations. Reuse the analyst,
BI engineer, designers, product owner and independent QA; do not create another
orchestrator. A source dashboard or document does not choose the Omni target:
resolve native dashboard, native App or both independently.

Read [source competencies](references/source-competencies.md) for version/API
qualification, [subagent assignments](references/subagent-assignments.md) when
parallel work helps, [behavior handoff](references/behavior-handoff.md) for
semantics, and the [run guide](../omni-artifact-accelerator/references/microstrategy-visual-run.md)
for capture and evidence commands. Exact shapes live in the
[source contract](../omni-artifact-translator/references/microstrategy-source-contract.md).

## Scope before capture

Pin HTTPS origin and Library application context path, Library and Intelligence
Server versions separately, project, principal, source GUID/type, API profile
and native Library versus embedded context. Classic and Mosaic semantics are
separate. Unknown versions use supplied evidence only. Do not infer all-source
coverage from one successfully exported dashboard.

Reconcile independent inventory with immutable originals: chapters, pages,
visuals, repeated placements, selectors, prompts, metrics, attributes, shared
cubes, content and export behavior. Retain hidden/private/denied/missing,
unsupported and excluded objects as explicit obligations. Private scope needs
explicit selection; source administrators do not prove target-user access.

## Preserve behavior

Keep report/extraction filters and prompts, chapter selectors, pre-aggregation
view/template filters and post-aggregation metric limits distinct. Prompt keys
are unique even when IDs or names repeat. Required unanswered, omitted, default,
all, empty and explicit answers must not collapse into the same state.

Preserve raw native expressions and attribute forms/elements, metric identity,
level/conditional metrics, transformations, derived elements, totals and security
filters. These are reviewable evidence, not executable code or a general formula
compiler. Bind numerical results to the exact definition, instance, principal,
observed state, complete pagination and freshness. Display text is not a raw
number; a successful export is not proof of full data.

## Execution boundaries

Use supplied originals first. Optional connected acquisition separates metadata,
saved-instance execution/state changes, rendering and cleanup grants. Keep the
auth token and all relevant session/load-balancer cookies together at the host,
out of artifacts/logs. Never log out a borrowed session. Creating or modifying an
instance can execute queries; HTTP GET alone does not prove safety.

Only qualified ordinary analytical objects may execute. Datamart reports,
transaction-enabled documents, authoring changesets, arbitrary SQL, schema reload,
ACL changes, subscriptions and publishing are outside this capture path. Modeling
instances and analytics instances are different; never delete one using the
other's API because their IDs look similar. Journal before dispatch and reconcile
ambiguous outcomes rather than replaying execution automatically.

PDF is a documented export route. PNG/JPEG and unsupported document/cube profiles
use supplied evidence unless a separate exact route is qualified. Do not install
an SDK, decoder, renderer or MCP client. Apply the existing
[dependency policy](../omni-artifact-accelerator/references/dependency-policy.md).
MCP catalog/query evidence does not supply dashboard layout or rendered exports.

## Continue through A–F

A verifies data and the relevant user's access. B reviews semantics and builds
analysis; C creates a reusable traceable narrative. At D resolve fidelity versus
redesign, audience, quality ambition, official branding/assets, devices, exports,
interaction and 2D/2.5D/3D preferences, and the user's independent
[cache/refresh policy](../omni-product-owner/references/data-refresh-policy.md).
Preserve valid answers. At E present exactly three concrete viable concepts with
the same analytical scope and quality bar. Record the actual user choice before
detailed design and F coding. Use existing gates, not a source-specific shortcut.

Reuse governed Omni bindings first. Send genuine gaps to
[DMA cowork](../omni-backend-handoff/references/cowork-contract.md) with source
pins, grain, formulas, security and acceptance cases. No MicroStrategy DMA
producer is supplied; never invent a `microstrategy-adapter` report or expand a
frontend route into warehouse changes. Keep dashboard and App delivery evidence
separate. Local checks, rendered quality, effective access, publication and
business acceptance are independent outcomes.
