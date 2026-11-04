# Domo → Omni: first visual pilot

Use this for one Domo Card in its real Page/App context, then expand to the complete
selected experience. Current scope combines local preparation, supplied-evidence
verification, opt-in pinned source reads, gated native work through separately
qualified tools and independent comparison. Image capture, executed visual results
and detailed App definitions remain supplied/manual evidence. A hosted execution
service and live tenant qualification are not established.

Read the [specialist](../../omni-domo-migrator/SKILL.md),
[current run guide](domo-visual-run.md), [existing bridge](domo-agent-bridge.md)
and [visual/App evidence contract](domo-evidence-contract.md). Reuse the existing
Domo manager/run and accepted scope. Do not duplicate its engine or replace its
typed gates with conversational status. Every new pilot follows A–F; discovery and
source evidence can precede design, but target coding waits for the actual user's
choice among exactly three concepts and the resolved detailed handoff.

## 1. Establish the pilot and connections

Recover selected Domo Page/App/Card and tenant identities, available source/target
connections, representative viewer and intended decision. Use the local intake to
ask only missing stage-appropriate questions. After access, analysis and narrative,
resolve the Omni instance/development destination, audience, quality ambition,
website and approved brand assets, devices, fidelity and target cache/refresh
policy. A Card pilot does not exclude the remaining Page/App from a broader
migration: retain all obligations unless explicitly dispositioned.

Discover actual Domo MCP tools and schemas. Select scoped read operations for discovery/data; verify what the effective user can see. If the documented MCP toolset cannot return Card configuration or images, report the precise missing operation and use the existing migrator/native export path. Never treat connecting MCP as granting access to every tenant object or as approval for Domo mutations.

The legacy [operator runbook](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/docs/domo-supervised-pilot.md)
is pinned historical source-contract guidance. For active acquisition, follow the
current local [source wrapper](domo-visual-run.md) and its exact reviewed extension,
implementation closure, request schema and startup grants. A version label does
not authorize loading dependencies. Do not put passwords, tokens or signed links
in chat, request JSON or shared artifacts. App-session authentication, Platform
OAuth and Product access tokens are distinct channels.

## 2. Capture definitions and visual reference

Use only the source operations actually qualified for the selected runtime and
scope. Retain Page/Card/chart/drill/DataSet/PDP evidence and unavailable facets
without treating generic App/workflow inventory placeholders as full definitions.
Pin original IDs, runtime and file hashes, capture state and missing-evidence
queue. An accessible Page list is not a complete tenant inventory.

Retain a Page image for hierarchy and Card image for detail. Prefer an actually available documented renderer; otherwise use an authorized native export or scoped manual capture. Keep default, representative filtered and drill states separate. Capture viewport, theme, date range/timezone, filters/variables, sort, principal reference and effective data time alongside each image. Missing state stays unknown.

The OAA path uses `oaa-domo-visual-capture.v1` to bind supplied original files,
placement/state and independent scope; verify it before import. If evidence must
also enter the originating engine, use that engine's `domo-manifest.json` and
`parse_manual_evidence(paths)` for its accepted attachments. These are distinct
contracts. Preserve the API definition as configuration; never replace it with a
screenshot. The legacy binary parser retains provenance rather than visual
understanding. PDF/PPT remain outside this capture profile; retain them separately
and use a separately reviewed rendering route if needed. Do not rename formats or
silently load a decoder. Designers inspect permitted supplied pixels independently.

A distinct metadata attachment avoids replacing the Card definition. The following is an **entry template**, not a complete manifest or an executable capture. Replace placeholders with actual evidence; `object_id` identifies the attachment, not a new native Domo Card:

```json
{
  "path": "visuals/card-123-default.png",
  "object_type": "file_asset",
  "object_id": "visual-evidence-UNIQUE-CAPTURE-ID",
  "artifact_type": "sanitized_evidence",
  "definition_state": "metadata_only",
  "sha256": "sha256:ACTUAL-IMAGE-SHA256",
  "source_locator": "evidence-ref://capture/UNIQUE-CAPTURE-ID",
  "dependencies": [
    {"object_type": "card", "object_id": "123", "relation": "visual_reference_for"}
  ]
}
```

Retain the real manifest's capture tenant/environment/principal/time and truthful sensitivity/redaction fields. Add the exact Page dependency when relevant. The existing merge adds the unique attachment key without replacing the Card. OAA preserves its relationship/provenance as a generic definition asset and reports its metadata-only definition gap; that gap must not be cleared by falsely claiming a complete definition. Keep image state in the per-visual record below: `report_request_context` is reserved for inventory reports. Retain and inspect the actual file separately; importing its reference does not load pixels or satisfy the Card's missing executable definition.

Obtain supplied source values for the same view, including original execution
request/response evidence where required. This workflow does not supply a new
connected Card-result client. A separately authorized DataSet SQL result can aid
analysis, but does not prove Card formulas/Beast Modes, aggregation, filter order,
sorting/limits or null rules. Preserve completeness and independent expected cases.

## 3. Import the existing contract and create requirements

Project the emitted Domo evidence bundle/envelope using `translate_artifact.py --format domo-agent` as documented in the [bridge](domo-agent-bridge.md). The CLI consumes the typed JSON contract, not arbitrary MCP responses, screenshots or the generic migration bundle. It verifies local integrity and preserves unknowns; it does not authenticate the tenant or close coverage gaps.

For the new capture, use `domo_check_capture`, `domo_import_capture` and
`domo_normalize_results` with the original files and exact binding/profile. Keep
summary metrics separate from chart results. App components retain their full
behavior facets; a read-only App can use the separate assignment contract with
empty operations and side-effect arrays. No invented operation is required.

Create one working record per **placement**, linked to the inventory asset key and native Card ID. A repeated Card may have different contextual behavior. Save records in the private engagement's working contracts/design evidence; the following is a checklist, not a new accepted importer schema:

| Section | Record |
| --- | --- |
| Source | Tenant/Page/Card/placement/query/DataSet IDs, original definition hashes and captured version/state |
| Visual evidence | Image/file paths and hashes, media type, capture method/time/principal, viewport, theme and missing content |
| Behavior | Defaults, variables, Page/Card filters and propagation, drills/actions, reset/empty states, exports and dependencies |
| Query | Formula IDs and text, field bindings, grain/population, units, totals, timezone, observed rows/completeness and expected results |
| Design | Source chart/config, proposed Omni chart, preserved layout cues, theme/font/logo references, adaptations and improvement rationale |
| Backend | Existing compatible Omni bindings or exact DMA request and pending response pins |
| Target/QA | Native document/draft/query/tile IDs, actual readback/render, matched-state comparisons and unresolved cases |

The translator and analyst retain the source baseline and adaptation questions
for the later design choice. Use the [chart mapping guide](../../omni-dashboard-designer/references/migration-chart-mapping.md)
to classify feasibility. Unsupported drills, custom charts, App Studio behavior,
workflows or side effects remain explicit work, not omitted Cards.

## 4. Bind the backend and build natively

Select `reuse_existing`, `omni_semantic_reconstruction` or
`warehouse_first_refactor` explicitly. Reuse compatible Omni fields and Topics
where appropriate. For a real calculation, join, grain, freshness or access gap,
send the minimum versioned requirement through [backend handoff](../../omni-backend-handoff/SKILL.md).
Preserve the selected route and source scope; a visual change is not an upstream
warehouse requirement.

Carry the verified analysis and narrative into D's interview and E's three
concrete, equally scoped concepts. Record the actual user selection, detailed
design and target refresh policy. Then use the gated `domo_build_handoff` to
prepare engineering work. A successful handoff is local preparation, not native
write authorization. Keep all four consultant reviews after each build iteration.

The BI engineer uses the [native build/export workflow](../../omni-bi-engineer/references/omni-build-export.md). Retain exact source placement → target query/tile mappings. A local chart specification is useful preparation but does not count as an Omni visual. A tool that immediately publishes is not a candidate-only route unless publication is already authorized.

Inspect the actual target render. Improve title clarity, number formats, label legibility, spacing, theme consistency and active-filter visibility without changing the accepted meaning. For a material chart or interaction change, record its rationale and decision; do not claim source parity for an accepted difference.

## 5. Prove the selected slice, then expand

Independent QA compares:

- Values, totals, NULL/empty cases and a dimensional slice against original source expectations under matched filters/timezone/principal/data time.
- Default, filter/reset and drill scenarios; separate a same-picture state from a working interaction.
- Labels, scale, sorting, conditional color meaning, responsive layout, customer theme and usability at agreed viewports.
- Allowed and denied personas, PDP-to-Omni enforcement and possible derived-field leakage.
- Actual query/render performance and any source schedules/exports/app operations selected in scope.

Capture source and target files separately, with hashes and context. Record defects and accepted differences individually. Missing tenant access means `not_run`/`blocked` for affected native tests, never “migrated.” No automatic image-diff implementation is implied.

Return the candidate and QA through the existing [scope/return lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md).
When its verified frontend receipt and original planning context exist,
`domo_frontend_return` and `domo_check_frontend_return` prepare a checked proposal
for the originating manager; they do not register or accept it there. The first
acceptance milestone is one proven visual, then the complete selected Page/App
including controls, repeated content, navigation and operational dependencies.
Only then scale. Keep publication and source retirement separately authorized.

## Suggested customer instruction

> Use Omni Artifact Accelerator to migrate this Domo Card in its Page context to a native Omni dashboard. Discover my connected Domo and Omni tools, reuse the existing Domo/DMA run, and capture the source configuration, image, values and interaction state. Keep it familiar while proposing clear design improvements. Ask for my company website URL if branding context is missing. Reuse existing Omni semantics or send specific backend gaps to Data Model Accelerator. Build within my authorized scope, compare the actual target, and show preserved behavior, improvements and remaining gaps.

The dedicated source engine is obtained separately and may require repository access. This package imports its supported evidence contracts; it does not distribute or provision the Domo engine.
