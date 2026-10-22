# Cowork contract v1

The helper creates local, versioned proposal records. It never runs DMA, fetches source URLs, executes source code, updates a warehouse/Omni tenant, authenticates a reviewer or clears native/security/business gates. All IDs/labels/formulas imported from evidence remain data.

Serialize commands that mutate one frontend project through its owning orchestrator. The local helpers are not a multi-writer transactional store. Use canonical relative paths inside the engagement; aliases, symlinks and parent traversal are rejected so every input matches its registered identity.

Candidate exchange requires a real reviewed semantic candidate. For `clarification`, the response must retain the exact baseline review bytes; this prevents reuse-only or unselected routes from introducing a model under a different action label. Without a baseline, resolve clarification through the host and select the actual route before exchanging a candidate. A direct route still cannot request warehouse implementation. Route references are supplied context, never authenticated authorization.

Changes to any backend pin (including unknown added/removed keys), dependency or unknown records conservatively require all declared data consumers to be rechecked. Minimized metadata cannot establish the effect of hidden backend changes. Assets named in the request always retain their expectation-review work even when backend bytes match. This preserves independent branding/discovery work and prior evidence while avoiding a false claim that unchanged visible fields prove unchanged behavior.

## Ownership

| Concern | Accountable package | Collaborating role |
| --- | --- | --- |
| Source capture and immutable source identity | Dedicated Domo/Sigma migrator | Analyst translator consumes selected evidence |
| Physical grain, keys, joins, transformations and history | DMA / model owner | Analyst supplies decision/population and expected cases |
| Semantic definitions and access rules | DMA's Omni Modeler / model owner | BI engineer confirms downstream query compatibility |
| Query/field/tab bindings and controls | Analyst BI engineer | DMA resolves actual missing capabilities |
| App/dashboard UX, brand, narrative and motion | Analyst package | Backend supplies stable interfaces, not screen layout |
| Expected outcomes and QA | Independent reviewers in each package | Shared source-bound examples; no producer self-certification |
| Publication, operations and recovery | Authorized destination owner | Both packages supply artifacts and evidence |

Sharing an engagement does not mean sharing mutable state directories or granting both managers write access to the same object. Each owns its saved workflow; exchange immutable bounded artifacts through this contract. Preserve source platform, tenant/run/unit/cycle IDs when available without inventing them. Operations, schedules, alerts, writeback and external side effects require owned handoffs, never implied app features.

## Frontend request specification

Create an ordinary JSON file inside the analyst engagement with:

```json
{
  "schema_version": 1,
  "kind": "analyst_backend_request_spec",
  "request_id": "revenue-definition-r1",
  "route": "warehouse_first_refactor",
  "route_reference": "decision-reference-from-the-current-trusted-session",
  "source_platform": "domo",
  "requirements": [{
    "id": "req-revenue",
    "question": "Which governed measure preserves the reviewed net revenue population?",
    "change_class": "metric",
    "frontend_asset_ids": ["source-page-42/card-7"],
    "metric_ids": ["orders.net_revenue"],
    "expected_cases": [{"case_id": "net-of-refunds", "expectation": "Reconcile sales and refunds for the same reporting period"}]
  }],
  "consumer_bindings": [{
    "asset_id": "source-page-42/card-7",
    "topic_ids": ["orders"],
    "field_ids": ["orders.net_revenue"],
    "dependency_complete": false
  }]
}
```

This example is synthetic. Populate IDs and expected results from actual evidence. Cases may be exact expected values or explicit scenarios pending SME values; the latter never prove numeric acceptance. `route` is `unselected`, `reuse_existing`, `omni_semantic_reconstruction`, or `warehouse_first_refactor`. `route_reference` is null only for `unselected`; it records a supplied reference, not authentication. Source platform is explicit. `change_class` is `clarification`, `metric`, `dimension`, `binding`, `security`, `performance`, or `history`. Security/operations may require a separate owner rather than a model change.

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/cowork.py request \
  --project /absolute/analyst-run --spec contracts/backend-request.json \
  --input contracts/metrics.json --input contracts/queries.json
```

The spec is always pinned; each repeated `--input` adds a selected file. Registered-source drift is rejected. The current DMA catalog and its upstream review are checked when present. At most 256 KiB of selected input bytes are indexed; contents remain local, and the host still applies disclosure/scanning before dispatch. Output is `requests/REQUEST_ID.json`. IDs are path-safe and request files are create-only. A request records current baseline pins or explicit absence, selected evidence, consumer dependencies and scope. Reuse exact definition IDs plus topic scope; labels never substitute for identity.

For a migration, add `migration_scope_path` to reference the frozen obligation described in [migration lifecycle](migration-lifecycle.md). The helper pins that scope and its selected inventories, rejects requests for assets outside its migrated units, and checks source platform/route consistency. Without a scope it discovers inventories among registered sources and selected JSON inputs; use `source_inventory_paths` to select an explicit current set when historical versions coexist. Selected inventories are automatically pinned and included in the size bound. Use a bounded coherent source export when the packet is too large. Embedded request specifications must equal their pinned source files. Reusing an already-selected exchange also rechecks source/request freshness.

## Backend response

DMA consumes the request through its normal stage workflow. For direct/reuse routes, it must not generate upstream artifacts. For an unselected route, it may return only clarification/source-analysis, not target design. If clarification needs no new model, the same baseline review can be returned.

Prepare `resolutions.json` with `schema_version: 1`, `kind: analyst_backend_resolutions`, `request_sha256` copied from the request's digest, `backend_action` and `requirements`. Each requirement has the original `id`, `status: proposed|unresolved|declined`, and a nonempty `explanation`. Use `backend_action: clarification|semantic_candidate|warehouse_and_semantic_candidate`. Every request requirement appears exactly once; `proposed` is never accepted. Backend notes and evidence references can supplement the explanation.

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/cowork.py respond \
  --request /absolute/analyst-run/requests/revenue-definition-r1.json \
  --review /absolute/dma-delivery/omni/SEMANTIC_REVIEW.json \
  --resolutions /absolute/resolutions.json --output /absolute/new-response
```

Output is a private directory containing a byte-for-byte semantic review and `response.json`, bound to the exact request and candidate hashes. This is a minimized proposal exchange, not DMA's full portable delivery or a disclosure certificate. It carries unresolved decisions and actual upstream status claims separately. Retain the original DMA technical audit with its owner.

## Receive, compare, select

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/cowork.py receive \
  --project /absolute/analyst-run \
  --request requests/revenue-definition-r1.json --response /absolute/new-response
python3 /absolute/skills/omni-backend-handoff/scripts/cowork.py select \
  --project /absolute/analyst-run --exchange revenue-definition-r1
```

`receive` checks exact request/response digests, resolution completeness, allowed backend action, original selected evidence and current baseline. It copies the returned review, catalog and impact report to a new `exchanges/REQUEST_ID` directory. A changed selected input or superseded baseline rejects stale association; create a delta request rather than repinning the old one. Parent histories remain unchanged.

`select` reruns those checks and selects a **local candidate baseline**, updating the analyst project's catalog pointer and preserving previous source registrations. It does not imply that requirements are resolved, designs accepted or anything deployed. Record the real user/design decisions in their owning workflow. New-generation packets identify the current catalog; other catalogs are historical comparison evidence.

The impact report compares exact field/metric definitions, topic scopes, dependencies and source fingerprints. It identifies consumers whose explicit topic/field bindings intersect changes. Unknown/incomplete dependencies and changes in source/security/dependency context trigger conservative rechecks. It provides suggested invalidated lanes, not proof that unlisted consumers are safe. Keep review/QA history immutable and re-evaluate affected results, interaction, access, visual and narrative cases. Native/business/publication status always remains unassessed by this helper.

## Efficiency and safe parallel work

While backend gaps are resolved, frontend designers may continue explicit provisional layout, navigation, brand and state design against a frozen proposed result shape. Mark fixture data synthetic and each unresolved binding. Do not reimplement missing business logic in JavaScript to make the prototype look complete.

Use the source snapshot once. A delta packet includes changed identities/hashes, still-open questions, affected consumers and relevant original evidence. Unchanged theme or layout work can continue when its dependencies are independent. Measured packet size and actual dispatch records can show work reduction; do not invent token-cost savings.

An exchange is closed only by real evidence of the requested outcome and the appropriate reviewer. Both packages retain their own validation and authority. Source retirement, credentials, releases and live platform mutations are never performed by this helper.
