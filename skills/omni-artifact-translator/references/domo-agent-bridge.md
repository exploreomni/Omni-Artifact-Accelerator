# Domo migration-agent bridge

Inspect/reuse the Domo migration package's evidence before asking a customer to recapture it. Its architecture manager retains the run, selected scope, store-backed gates, write authority and release decisions; this analyst skill returns a bounded experience/design candidate.

```sh
python3 scripts/translate_artifact.py /absolute/private/domo-handoff.json \
  --format domo-agent \
  --producer-revision 55eba0ca0690fbf14f39eddbc8a04c94a720c155 \
  --output /absolute/private/new/source-inventory.json
```

The producer revision is a declaration constrained to the inspected contract pin. The CLI never imports, executes or fetches DomoMigrationAgent. A successful import does not authenticate the declaration.

## Accepted emitted contracts

| Discriminator | Source in DomoMigrationAgent | Bounded import behavior |
|---|---|---|
| `contract_version: omnikit.domo.evidence.v1` | `packages/omnikit-migration-engine/src/omni_migrator/extractors/domo/models.py`, `DomoEvidenceBundle` | Reads full serialized `mode`, `objects`, `edges`, `coverage`, `manual_capture_queue`, `checkpoints`, `diagnostics`, `bundle_fingerprint`. Objects retain exact `object_type:object_id`, native URNs, attributes/formulas, source references, definition/redaction states and visibility principal. Recomputes the supplied finalized bundle fingerprint with its documented sort order. |
| `contract_version: omnikit.domo.source-evidence.v1` | `.../extractors/domo/evidence.py`, `DomoSourceEvidenceEnvelope` | Parses canonical `payload_json`, checks envelope and inner bundle fingerprint bindings and evidence reference, and retains the decoded evidence alongside the unchanged envelope. Checks are local integrity only; sanitization labels and source revision cannot be authenticated. |
| `contract_version: domo-to-omni.dashboard-rebuild-plan.v1` | `contracts/dashboard-rebuild-plan.v1.schema.json`; `.../dashboards/rebuild_plan.py` | Projects source Page, Cards, placements, queries and special behaviors. Checks supplied membership/order identities and surfaces missing Card/query/behavior mappings, including filter context, security and personas. Retains accepted Topic/component/profile/decision references and target proposal separately. The source engine's normalized plan hash and store registration are retained, not recomputed or trusted here. |
| `contract_version: domo-to-omni.external-redesign-handoff.v1` | `contracts/external-redesign-handoff.v1.schema.json`; `.../control_plane/external_handoffs.py` | Preserves exact source/native IDs, analytic outputs, side-effect kinds, external owner, work-package/decision references and assignment-only status. Checks the supplied handoff hash; rejects an agent as the declared human approver and any contradictory `authorizes_*: true`. It cannot authenticate the human reference. |

Input is one full emitted JSON object, not an archive, a live API response, a Product Search result or the entire generic `MigrationBundle`. If source evidence is inside a generic migration bundle, ask the existing Domo package to export its `domo-source-evidence` requirement `config` through its typed accessor; do not guess a lookalike object from unrelated fields. The control-plane `domo-to-omni.evidence-bundle.v1` registry and portfolio-inventory records are distinct contracts and are not substitutes for `omnikit.domo.evidence.v1` definitions.

Unknown attributes remain raw evidence. New imports do not infer SQL from a chart, execute DataFlows, resolve undocumented Product APIs, implement Workflows or change PDP/sharing. Objects whose redaction state is pending may import only after their body/title have been withheld; credential-bearing values are rejected. Empty withheld definitions and manual-capture gaps remain incomplete.

## Analyst decisions that must survive

- **Formal membership and denominator:** a Page may reuse Cards at multiple placements. Preserve Page order, Card identity, placement identity and query set independently. A single screenshot cannot establish the complete selection or hidden content.
- **Query meaning:** field IDs, Beast Mode formula identity and scope, grouping, sort, limits, totals and subtotals; distinguish row, aggregate, window and FIXED/LOD behavior. Upstream transformations remain with the source analytics engineer and DMA.
- **Filter behavior:** global, Page, Card, variable and query contexts, default values, propagation and precedence. Preserve each query's context; one Page-level filter test does not cover all Card populations.
- **Experience:** drills, links, cross-filtering, text content, formatting, layout and responsive behavior. Approved redesign differences stay separate from captured source facts.
- **Security:** PDP/permission definitions, persona allow/deny and derived-field leakage tests require independent evidence. Visibility under the capturing principal is not effective-access proof.
- **Operational/app side effects:** Apps, embeds, schedules, alerts, exports, recipients, writeback, workflows and external writes retain explicit owners/dispositions/acceptance criteria. An `application_redesign` assignment hands work to app design/engineering; it does not authorize side effects or target writes.

Return an analyst proposal with the exact Page-plan and source hashes to the Domo manager. Its existing independent `StoreBackedDashboardEvidenceResolver` and `DashboardPlanValidationRegistration` establish its readiness gate. This import cannot create that registration. One selected Page must be covered by exactly one current plan in that originating workflow; this single-file bridge cannot prove cross-plan uniqueness or selected-portfolio completeness.

## Reviewed unpublished changes

On 2026-10-21, the Domo checkout had local changes to `extractors/domo/api.py` and `broker.py` adding documented Card `cardUrn`/`cardTitle` handling, `totalCardCount` reconciliation and stricter pagination, plus Product Developer Token header handling. These were read as unpublished implementation evidence, not executed or certified. The bridge already preserves arbitrary native URN strings and checkpoint warnings. It introduces no new API acquisition, tenant readiness or release claim from those changes.
