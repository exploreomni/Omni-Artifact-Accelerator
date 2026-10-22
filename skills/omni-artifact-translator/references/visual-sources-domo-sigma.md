# Domo and Sigma visual migration sources

Reviewed **2026-10-21**. This is a source capability and implementation audit, with **Domo selected for the first visual migration workflow**. No source tenant calls, credentials, videos, source writes, or native migration tests were used. Confidence is high for the inspected code and quoted documentation boundaries; actual tenant tool availability and output fidelity remain unverified.

Both vendors now document official product MCP servers. That establishes an assistant connection, not a complete migration export. A useful migration capture combines **visual reference + executable configuration + observed data + interaction/security context**, tied to the same source identity and state. An image alone cannot establish formulas, effective access, filter propagation, or completeness.

## Domo: selected first slice

### Official assistant connection and scope

Domo documents tenant-hosted MCP at `https://<tenant>.domo.com/mcp` or `/mcp/toolkits/domo`. Its OAuth guide requires AI Chat or AI Library and the **Use MCP** grant, and shows a Claude remote connector. Account permissions constrain access. This is a hosted service; do not substitute an unrelated community package bearing a similar name. [Standard OAuth](https://www.domo.com/docs/s/article/MCP-Standard-OAuth).

The AI Library overview also names **Use AI Services** and **Use AI Chat** grants and notes consumption-agreement availability/trial arrangements. Toolkits can expose operations that mutate Domo. The migration capture should select only the scoped read operations actually available. [Connect AI Tools to Domo](https://www.domo.com/docs/s/article/Connect-AI-Tools-to-Domo-Using-MCP).

The explicit Domo MCP tool catalog lists **Search, SQL Query, Domo Documentation Query, List Document Collection Files, Read File, Query Document Collection**. It does not enumerate a chart-image renderer, Page-definition exporter, or full dashboard export. Broad prose about building cards/apps is not a substitute for a tool schema. [Domo MCP](https://www.domo.com/docs/s/article/Domo-MCP).

The manual guide supports an access token in `X-DOMO-DEVELOPER-TOKEN` and names ChatGPT among compatible clients. It still says card/dashboard summarization is coming soon, while newer overview prose is broader; it also contains older Claude connection instructions. Prefer the current OAuth flow and inspect the connected tenant's actual tool names, argument schemas and permissions before prescribing a capability. No verified official ChatGPT marketplace distribution was established in this review. [Manual connection](https://www.domo.com/docs/s/article/MCP-Manually-Connect).

### Reusable acquisition already present

All paths below are relative to `DomoMigrationAgent/packages/omnikit-migration-engine/src/omni_migrator/`. These are **implemented local routes**, not claims that their current public reference pages or a live tenant were verified here. The developer portal could not be retrieved during this audit; do not silently promote a code route into a currently qualified API contract.

| Need | Existing function and route | Boundary |
|---|---|---|
| Page/Card inventory | `extractors/domo/api.py`: `DomoPlatformClient.list_pages`, `list_cards`, `list_datasets`; GET `/v1/pages`, `/v1/cards`, `/v1/datasets` | Pagination checkpoints and exact IDs; permission-visible inventory is not tenant completeness. Unpublished code recognizes `cardUrn`, `cardTitle`, `totalCardCount` and conflicting/changing totals. |
| Page membership/configuration | `page(page_id)` → GET `/v1/pages/{id}` | Preserve raw response and Page→Card identities. Layout, visibility and interaction gaps remain explicit. |
| One visual definition | `card(card_id)` → GET `/v1/cards/{id}`; `card_chart(card_id)` → GET `/v1/cards/chart/{id}` | Metadata and chart configuration are separate captures. Do not reconstruct missing formulas from pixels. |
| Drill chain | `card_drillpath(card_id)` → GET `/v1/cards/chart/{id}/drillpath` | Preserve child Card identities and unresolved drill behavior. |
| Data/security configuration | `dataset(id)` and `dataset_policies(id)` → GET `/v1/datasets/{id}` and `/policies` | PDP definitions do not prove effective access for a target viewer. |
| Extended metadata | `DomoProductClient.search`, `beast_mode`, `dataset_core`, `dataset_schema`, `dataset_permissions`, `dataset_cards` | Separate opt-in tenant Product API client and Developer Token; allowlisted endpoints. It is not an arbitrary HTTP proxy or query renderer. |
| Bounded dependency capture | `extractors/domo/broker.py`: `DomoAcquisitionBroker.acquire_selected_scope(...)` | Selected Page/Card/DataSet IDs, independent dependency budgets, explicit manual-capture queue. `include_portfolio=False` avoids a full inventory in a tightly scoped pilot; it makes no complete-portfolio claim. |

`DomoPlatformClient` currently defaults to OAuth scopes `data` and `dashboard` using client credentials, or an explicitly supplied bearer token. This differs from MCP user OAuth and the Product API Developer Token. Keep capture principal/context separate for each channel; a broadly privileged token cannot stand in for viewer-parity evidence.

### Images, files, results and state

The official legacy support article documents **UI** Dashboard Page export to PDF/PowerPoint, not a REST rendering endpoint. It excludes card descriptions and describes export limitations for tall layouts. Its searchable content is dated 2022-11-22; direct retrieval currently returned a support-site CSS error, so current tenant behavior must be checked. No supported Domo image/PDF/PPT REST endpoint was verified here. Do not invent a private browser route from a community renderer. [Exporting Dashboards to PDF or PowerPoint](https://domo-support.domo.com/minasan/s/article/360043437893?language=en_US).

The existing `extractors/domo/manual.py` already accepts manifested **PNG/JPG/JPEG/WebP**, JSON/SQL/TXT/CSV and bounded ZIP bundles through `parse_manual_evidence(paths)`. Its `domo-manifest.json` preserves object ID/type, hash, acquisition timestamp, tenant, principal, permission reference, source locator, sensitivity, redaction and validation. Relevant artifact types include `page_layout_interactions_visibility`, `card_definition` and `sanitized_evidence`. **PDF/PPT are not allowlisted.** Binary files produce a hash, byte size and provenance reference; the parser does not read pixels or derive chart configuration. A screenshot must not be labeled a complete executable definition.

`broker.merge_evidence(api, manual, accepted_validation_refs=...)` reconciles separately validated evidence. Adding a screenshot of an existing Card can create a definition conflict if treated as replacement configuration: keep visual attachments distinguishable and preserve the API definition. An imported validation claim is not independent acceptance.

MCP's SQL Query is a documented data access option, but its response schema and query context were not live inspected. Neither inspected Domo API client implements a general result-query or image-rendering method. For the pilot, retain an authorized, bounded observed result with the exact SQL/metric contract, filters, time range/timezone, sort, limits, null treatment, principal and execution time. A dataset-level SQL result without the Card's calculation/filter semantics is not Card parity.

### Smallest complete workflow increment

**Recommendation:** reuse the broker and manual parser, with a per-visual requirements record accompanying the existing OAA inventory. Associate an approved image with a Page/Card key and source-definition hash, carry the observed view state and evidence gaps, and make the image available to the designer as a reference. This increment needs a skill workflow and reviewable evidence records, not a new acquisition runtime. There is no automated Domo rendering connector in this package; do not imply that OAA's current translator already ingests raw images/PDF/PPT.

Required record fields: source platform/tenant reference; exact native Page/Card/DataSet IDs and parent/placement relation; API capture hash/revision; attachment path/hash/media type; capture time and principal reference; state (filter values, date range/timezone, sort, drill depth, selected points, viewport); result artifact hash/row-limit status; state completeness; missing facets; separately approved visual differences. Unknown state stays unknown. Keep secrets out of locators, and use reference-only handling for restricted evidence.

First end-to-end slice:

1. Select one existing Card on one Page, one documented default/filter state and an approved viewer context. Retain the rest of the Page as pending in any broader migration scope; explicitly retain dependencies and drill destinations. Exclusion requires an explicit scope decision.
2. Use the existing selected-scope broker for Page, Card, chart, drills, datasets, calculations and PDP evidence. Record its code pin and missing-capture queue. Obtain an approved visual reference and numerical result for that same state; use the existing manual manifest for supported image files.
3. Project the existing Domo evidence bundle into OAA. Keep native identities, source hashes, Page-plan denominator and unresolved behavior. Ask DMA only for missing model/query work; usable existing Omni semantics can be bound directly.
4. Create a reviewable native Omni visual with the verified target MCP/CLI capabilities. Improve readability and theme only through recorded design differences; preserve metric/filter/drill/access behavior unless the user approves a change. Target implementation and product capability verification belong to the target workflow.
5. Compare independent numeric expectations, displayed labels/units/scale, filter/drill behavior and viewer access. Save target readback and screenshots separately from source references. A successful capture or local candidate is not native verification, business acceptance or authorization to publish.

## Sigma: documented capability and later slice

### MCP and authentication

Sigma documents a hosted HTTP/OAuth MCP URL from Profile → Integrations, an official Claude Connectors Directory entry and an official Sigma ChatGPT plugin. The **Use Sigma MCP with OAuth** account permission and underlying operation permissions apply. Its current documented features include search/describe/query, workbook building and screenshots of a workbook **page or element**. Tool availability depends on permissions; cached tools may require refresh. Agent tools can have write effects and are not identically available through the ChatGPT plugin. Discover actual tools before promising a capture. The documentation-only `help.sigmacomputing.com/mcp` is a different server. [Use Sigma MCP server](https://help.sigmacomputing.com/docs/use-sigma-mcp-server).

REST credentials select the **REST API** scope and inherit the associated member's account permissions. Admins can create credentials; non-admin **Create API keys** is described as **public beta**. Bearer tokens last one hour. Use the organization's displayed regional API base URL, not a presumed universal hostname. [Client credentials](https://help.sigmacomputing.com/reference/generate-client-credentials), [REST API overview](https://help.sigmacomputing.com/reference/get-started-sigma-api).

### Definition, render and result paths

| Need | Official/implemented evidence | Boundary |
|---|---|---|
| Visual/layout snapshot | Local `SigmaApi` methods in `extractors/sigma/api.py` capture workbook metadata, pages, elements, columns, controls, query SQL, sources, grants, lineage, bookmarks, tags and version history; data-model `spec` supports `documentVersion` | These methods do not establish complete workbook design serialization. Record each endpoint's success and missing facets; do not equate SQL retrieval with query execution. |
| Tagged capture | Unpublished `workbook_snapshot(workbook_id, tag=...)` calls tagged pages/page-elements/elements and compares workbook/tag metadata before/after | Reports `unchanged_before_after_not_atomic`. Deliberately excludes untagged queries/controls/grants/sources. Tag existence/effective version still needs tenant validation. |
| Render/data export | Official POST `/v2/workbooks/{workbookId}/export`, then GET `/v2/query/{queryId}/download` | Export executes queries. Scope can be workbook/page/element; do not assume every format works at every scope. |
| Existing export implementation | Unpublished `export_workbook(workbook_id, tag=..., format=..., page_id=... OR element_id=..., parameters=...)`; `download_export(query_id)` | Supports requested types PNG/PDF/CSV/JSON/XLSX. No PPT implementation. Caller retains processing/error/expiry state; it does not automatically replay ambiguous POSTs or implement a polling/saving pipeline. |

The export reference documents `elementId`, `tag`, `parameters`, `exportAs`, `offset`, `rowLimit`, `timeout`, and format options. CSV/XLSX/JSON exports cap at one million rows/request; offset batches may overlap if ordering changes. PNG dimensions are best effort. Export query IDs expire after the validity window (default one hour; configurable up to six hours). Export creation is limited to 400 requests/minute. The existing local wrapper does **not** expose all documented options, including `exportAs`, offsets or row limits; do not claim it does. The expanded page-format union was not available in the retrieved reference text; validate that schema before constructing a new page-level request. [Export workbook](https://help.sigmacomputing.com/reference/export-workbook).

Download returns the originally requested format when ready and fails for pending/invalid/expired queries; its documented limit is 400 requests/minute. Preserve status and query ID; a 404 alone cannot tell expiry from an unknown ID. [Download query](https://help.sigmacomputing.com/reference/download-query).

Saved views, version tags, control parameters and export user context must be captured explicitly. A PNG does not preserve interactive actions. Sigma also notes that PDF/PNG control values may enter URL trace logs; use approved evidence handling for sensitive parameter values. [Workbook export behavior](https://help.sigmacomputing.com/docs/send-or-schedule-workbook-exports).

First Sigma slice: one tagged element plus same-state image and bounded result, exact workbook/page/element/control IDs, formula/query evidence and documented control values. Use existing runtime capture rather than an engine copy. The new tagged-only snapshot currently lacks the `snapshotContract: sigma-api-v2` envelope expected by OAA's direct importer; add an explicit projection before importing it, preserving omissions. Keep `sigma-prepush-context.v1` behavior evidence source-bound. A human must choose **direct semantic** or **warehouse** route; never default, and never let direct mode silently introduce dbt/warehouse work.

## Pins and verification boundary

Inspected checkouts (both contain unpublished API/test changes):

| Repository | HEAD | Inspected current file SHA-256 |
|---|---|---|
| DomoMigrationAgent | `55eba0ca0690fbf14f39eddbc8a04c94a720c155` | `extractors/domo/api.py`: `d816be35e64258555ba23a4f035fc29188d150d3b7bf35475f5a68c04c20a7a1`; `extractors/domo/broker.py`: `383ac4d86fe5c8f08dc4b0eaf0bb5467ed81b056198d88c6f5dfbe73c066fd36` |
| SigmaMigrationAgent | `f4eda45b0f49dc7335496d028665f7339ed82e8f` | `extractors/sigma/api.py`: `cfffe9d5d8bf4fd5226f50a81d7167421c04bff325c0ef15937e1abee20f9cf0`; `security/transport.py`: `ade855e2bd0213d61b889fd925fc3737d69b0ed631c800f83c1cd2a1bd23748a` |

Paths in the table start at each repository's `packages/omnikit-migration-engine/src/omni_migrator/`. Also inspected Domo `manual.py`, source repository instructions and OAA's translator skill. This review did not execute source clients or tests. Existing synthetic tests and local code establish bounded implementation evidence only. Source freshness must be rechecked before reuse: capture hashes, effective data time, metadata revisions and principal/state together; a matching image does not establish an unchanged dataset or security policy.

Related: [Domo bridge](domo-agent-bridge.md), [inventory contract](inventory-contract.md), [artifact translator skill](../SKILL.md). Native behavior, effective security, performance, operational ownership and business acceptance remain separate evidence lanes.
