# Domo → Omni: first visual pilot

Use this when the user connects Domo and Omni or supplies a Domo migration run. It is the package's first source-specific visual workflow. Current scope is **supervised capture, requirements, native build through available tools, and independent comparison**. Automated Domo image capture, a packaged remote execution service and live tenant qualification remain outstanding.

Read the [Domo source audit](visual-sources-domo-sigma.md), [existing bridge](domo-agent-bridge.md), and [connected workflow](../../omni-artifact-accelerator/references/connected-visual-migration.md). Reuse the existing Domo manager/run and accepted authorization. Do not duplicate its engine or replace its typed gates with conversational status.

## 1. Establish the pilot and connections

Start with one Card in its Page context. Get the selected Domo Page/Card and tenant, target Omni model/topic or destination, available source/target connections, representative viewer, and intended result. Ask for the customer's website URL and authoritative brand assets if missing. A Card pilot does not exclude the remaining Page from a broader migration: retain all remaining obligations as pending unless explicitly dispositioned.

Discover actual Domo MCP tools and schemas. Select scoped read operations for discovery/data; verify what the effective user can see. If the documented MCP toolset cannot return Card configuration or images, report the precise missing operation and use the existing migrator/native export path. Never treat connecting MCP as granting access to every tenant object or as approval for Domo mutations.

The existing source runtime provides `domo-acquire` and `domo-inventory`; the [Domo operator runbook](https://github.com/atx-omni/DomoMigrationAgent/blob/55eba0ca0690fbf14f39eddbc8a04c94a720c155/docs/domo-supervised-pilot.md) describes their request and credential-reference contracts. Use that inspected runtime's help/schema and current source capture implementation. Do not put passwords, tokens or signed links in chat, request JSON or shared artifacts. MCP OAuth, public API client credentials and the Product API token are distinct channels.

## 2. Capture definitions and visual reference

Use the existing selected-scope acquisition for Page/Card/chart/drill/DataSet/PDP evidence. Pin source IDs, runtime revision plus any local-change hashes, raw artifacts, capture state and the missing-evidence queue. An accessible Page list is not a complete tenant inventory.

Retain a Page image for hierarchy and Card image for detail. Prefer an actually available documented renderer; otherwise use an authorized native export or scoped manual capture. Keep default, representative filtered and drill states separate. Capture viewport, theme, date range/timezone, filters/variables, sort, principal reference and effective data time alongside each image. Missing state stays unknown.

Reuse Domo's `domo-manifest.json` and `parse_manual_evidence(paths)` for its supported image attachments. Preserve the API definition as authoritative configuration; avoid merging a screenshot as a replacement `card_definition`. Its binary parser retains provenance/hash/size, not visual understanding. Designers must inspect the supplied pixels separately. Use only artifact/object types accepted by the inspected runtime and retain `definition_partial`/review gaps where appropriate. The runtime currently rejects PDF/PPT; retain such originals as separate engagement references, and use a separately supported rendering/export step if images are needed. Never rename a PDF to PNG or claim the translator reads it.

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

Acquire bounded source values for the same view. A generic SQL query over the DataSet can be useful, but verify Card formulas/Beast Modes, aggregate context, filter precedence, sorting/limits and null rules before treating its output as the Card result. Preserve result completeness and independent expected cases.

## 3. Import the existing contract and create requirements

Project the emitted Domo evidence bundle/envelope using `translate_artifact.py --format domo-agent` as documented in the [bridge](domo-agent-bridge.md). The CLI consumes the typed JSON contract, not arbitrary MCP responses, screenshots or the generic migration bundle. It verifies local integrity and preserves unknowns; it does not authenticate the tenant or close coverage gaps.

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

The analyst and designer produce a faithful baseline plus a difference ledger. Use the [chart mapping guide](../../omni-dashboard-designer/references/migration-chart-mapping.md). Unsupported drills, custom charts, App Studio behavior, workflows or side effects remain explicit work, not omitted Cards.

## 4. Bind the backend and build natively

Reuse compatible Omni fields and Topics first. If a calculation, join, grain, freshness or access dependency is missing, send the minimum versioned requirement to DMA through [backend handoff](../../omni-backend-handoff/SKILL.md). Preserve the selected Domo route and source scope. Do not start warehouse work merely because the frontend needs a new color or layout.

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

Return the per-visual candidate and QA to the originating Domo manager and, for full migrations, the same DMA engagement via the existing [scope/return lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md). The first acceptance milestone is one proven visual; the next is a complete Page including controls, repeated Cards, text, navigation and operational dependencies. Only then scale to additional Pages. Keep publication and source retirement tied to actual authorization and readback.

## Suggested customer instruction

> Use Omni Artifact Accelerator to migrate this Domo Card in its Page context to a native Omni dashboard. Discover my connected Domo and Omni tools, reuse the existing Domo/DMA run, and capture the source configuration, image, values and interaction state. Keep it familiar while proposing clear design improvements. Ask for my company website URL if branding context is missing. Reuse existing Omni semantics or send specific backend gaps to Data Model Accelerator. Build within my authorized scope, compare the actual target, and show preserved behavior, improvements and remaining gaps.

The dedicated source engine is obtained separately and may require repository access. This package imports its supported evidence contracts; it does not distribute or provision the Domo engine.
