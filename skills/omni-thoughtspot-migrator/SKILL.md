---
name: omni-thoughtspot-migrator
description: Preserve ThoughtSpot Liveboard, Answer, TML, visual and interaction evidence when migrating to Omni dashboards or Apps. Use for ThoughtSpot source qualification, bounded capture, identity mapping and source-specific QA within the Omni Artifact Accelerator; not a query compiler or independent orchestrator.
---

# ThoughtSpot migration specialist

Work inside the current [accelerator engagement](../omni-artifact-accelerator/SKILL.md).
Own source interpretation and migration obligations. The analyst owns verified
meaning and expectations; designers own the target experience; engineers own
target candidates; QA owns independent validation; DMA owns backend candidates.

Read the [source competencies](references/source-competencies.md),
[source contract](../omni-artifact-translator/references/thoughtspot-source-contract.md)
and [run guide](../omni-artifact-accelerator/references/thoughtspot-visual-run.md).
Use the [behavior handoff](references/behavior-handoff.md) before design or QA.

## Qualify before interpreting

Record the selected tenant origin, Org, Cloud/Software version, principal,
native/embedded experience, chart generation, export privileges and evidence
reference. Names alone are not identifiers. Record unavailable capabilities and
denied/missing artifacts. A service account's visibility does not establish the
customer's effective access. Enterprise/Embedded Spotter MCP availability is a
licensed capability, not assumed by the presence of a URL.

Start an independent inventory of Liveboards, tabs, groups, visualizations,
repeated placements, notes, filters, parameters, views, saved Answers and model
dependencies. Reconcile that denominator with native JSON TML. Keep every missing,
unsupported or private item as an obligation. A successful export is not evidence
that every visible view or visualization was included.

## Preserve source truth

Keep Liveboard GUIDs, saved Answer GUIDs, pinned visualization/container GUIDs,
local visualization IDs, placement keys and tab paths distinct. Inline Answer
definitions in a Liveboard do not imply a saved Answer GUID. Never match by title
alone. Use exact JSON pointers and original-file hashes for the crosswalk.

Keep search strings, formulas, aggregation properties, table/model references,
axis roles, sorting, totals, conditional styles, number formats and raw unknown
fields. Strict JSON `client_state` can inform a proposal; it is never executed.
YAML, R/Python visuals, extensions and unknown binaries remain opaque evidence
unless an exact additional decoder/runtime has been separately approved.

Preserve security/model/runtime/Liveboard/search filters as separate layers;
retain linked columns, exclusions, crossfilters, tab/group scope and parameter
overrides. Observe actual applied behavior rather than equating a requested
filter with a result. Custom actions and embedded callback/URL definitions stay
inert during discovery.

## Use bounded acquisition

The local importer accepts transferred originals and explicitly mapped JSON.
The optional source host exposes fixed, reviewed REST operations only. Metadata
reads, saved-result queries and PNG/PDF renders have separate startup grants.
Source query/render requests may execute analytics and are journaled before
dispatch. An interrupted POST is not silently replayed. Known credential keys, recognizable text patterns and exact credential values are
screened; opaque binary payloads are not a complete secret audit. Response URLs
do not become fetch instructions.

The initial connected profile is Cloud `26.10.0.cl`,
`rest2-cloud-26.10.v1`. Other releases can use supplied evidence; qualify an exact
profile before adding live operations. Do not widen a profile because another
release looks similar. Ambiguous pinned-Answer report identifiers are deliberately
unsupported; use a qualified Liveboard render or a real saved Answer instead.

For optional Spotter evidence, use the retained MCP checker. Pin actual tool
schemas, requested/effective versions, Org and principal. Discovery is separate
from analytical sessions. Explicitly select the data source, retain every update
and complete each message generation. A session Answer ID is not automatically a
saved Answer, TML definition or REST generation number. No automatic `switch_org`,
`create_dashboard`, session query or installation. An approved host performs any
remote MCP operations; this package's MCP checker is passive.

## Continue through A–F

Follow [the existing stage gates](../omni-artifact-accelerator/references/stage-gates.md).
Access and analysis precede narrative and the product interview. At D ask about
faithful migration versus redesign, official branding, devices, interaction,
visual ambition, exports and the desired [cache/refresh/expiry policy](../omni-product-owner/references/data-refresh-policy.md).
“No custom cache policy” is a valid answer. Source cache settings, export pagination or a
metadata-only environment cannot silently dictate target behavior or lower craft.

Offer exactly three concrete viable concepts at E, preserve analytical scope and
quality across them, and record the actual user's selection before coding. Existing
engagements preserve their valid decisions. A source specialist never overrides
the orchestrator's gates or grants itself target-write permission.

Use an existing governed Omni model when it meets the evidence-backed contract.
Send actual semantic or physical gaps through [DMA cowork](../omni-backend-handoff/references/cowork-contract.md),
including original pins, source IDs, scope, selected route and independent cases.
There is no DMA ThoughtSpot producer in this package: use scoped backend
requirements, never fabricate a `thoughtspot-adapter` report.

Deliver separate App/dashboard candidates and evidence. Preserve source coverage,
adaptations and unresolved behavior. Local integrity, numerical parity, rendered
quality, effective access, publication and customer acceptance are separate results.
Unperformed live checks remain unqualified.
