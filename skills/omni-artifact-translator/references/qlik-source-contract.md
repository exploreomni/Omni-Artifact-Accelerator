# Qlik source contract

The first-party readers use the existing Python standard library. No SDK,
WebSocket client, QVF/QVW/QVD decoder, extension or remote MCP runtime is loaded.
References are evidence, not host authority or authenticated provenance.

## Supplied snapshots and original bytes

`qlik-api` accepts `qlik-api-snapshot.v1` with exact top-level fields:
`schema_version`, `identity`, `root`, `objects`, `inventory`, `gaps`.

| Field | Contract |
|---|---|
| identity | `source_origin`, `tenant_id`, `product` (`cloud` or `client_managed`), `version`, `principal_ref`, `engine_version`, `reference` |
| root | `{kind: "app", id: nativeAppId}` |
| objects | `{kind, id, payload, evidence_ref}` records with original native JSON payloads |
| inventory | Independent `reference`, `completeness`, and `items`; not inferred solely from successfully exported objects |
| gaps | Explicit unavailable, denied, unsupported or unresolved evidence |

Object kinds are app, sheet, visual, dimension, measure, variable, bookmark and
unknown. App layouts retain native `qFileName` matching the persistent app ID;
other typed definitions retain
`qInfo.qId` and `qInfo.qType`. Import original GetProperties payloads separately
from layouts/results, not a fabricated merge. Explicit source pointers can select
these payloads from original response envelopes. Transient `qHandle` values never
replace persistent identity. QlikView is not admitted as Qlik Sense.
The implemented app profile is the Enterprise/Cloud layout, not a Desktop file
path. Never invent `qAppId` in a GetAppLayout response; see the documented
[NxAppLayout contract](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/EngineJSONAPI/Content/models-nxapplayout.htm).

Inventory items retain `key`, `kind`, `parent_key`, `native_id`, `definition_id`,
`disposition`, `reference`, `configuration`, `source_mapping`. Mappings have
`object_kind`, `object_id`, `pointer`. Repeated placements use separate keys and
`visual_key` or `content_key` references. Keep native source names unchanged;
duplicate captions never establish identity. Unknown objects, missing children,
master dependencies and private-scope obligations remain visible.

`qlik-capture` accepts `qlik-visual-capture.v1`. Its immutable snapshot and
definition fingerprint bind retained source files. `qlik-originals.v1` maps every
`/objects/N/payload` and `/inventory` to original bytes, for example:

```json
{
  "source_path": "object-response.json",
  "source_kind": "supplied_json",
  "source_pointer": "/result/qProp",
  "target_pointer": "/objects/1/payload",
  "mapping": "exact_json",
  "member_path": null,
  "reference": "Reviewed original transfer",
  "mcp_evidence": null
}
```

Transfer archives only with explicit selected members and finite byte/count
bounds. Opaque scripts, binaries and extension resources remain auxiliary
evidence; hashes do not establish safety or authorize execution. Secret-bearing
text is rejected by bounded recognizable-pattern checks; binary safety is not
certified. Customer originals remain private and outside the repository.

## Requests, state and connected execution

`qlik-visual-capture-request.v1` records `capture_id`, `identity`, `root`,
`authorization_ref`, nullable `credential_ref`, `evidence_mode`, `route`,
`route_reference`, `target_surface`, `state`, `snapshot_path`, `originals_path`.
Optional profile/operation fields select the implemented Reports lifecycle.

State retains `filters`, `parameters`, `timezone`, `locale`, `principal`, `cache`
and `reference`. Use filters/parameters to retain explicit Qlik selections,
alternate states, bookmark and variable context. Requested state and observed
state are separate. Export TTL, source reload and target caching policy remain
different concepts.

Connected Reports accepts only the implemented existing-chart/sheet templates,
qualified Cloud profile and selected source identities. All job operations need
the separate render startup grant. Creation is journaled before dispatch; an
uncertain POST cannot be replayed automatically. Status/output/download requests
derive from retained successful responses and are independently rechecked by
the host. Redirects and unqualified output routes are rejected. Use supplied
transfer for unsupported output locations rather than sending a token elsewhere.
Reject selection failures even if the overall job reports completion.

No arbitrary `jsOpts`, patches, callback URL, session-generated visualization,
internal report template, reload or source authoring. Connected variables or
state shapes outside the implemented profile require supplied evidence or an
additional qualification; they cannot be silently dropped.

The implemented profile is `cloud-reports-v1-20261028`. Each operation has
`operation_id`, `kind: "report"`, `object_key`, `body`, `reference`. The object key
must resolve to the selected original chart/sheet; native ID and app ID must agree.
An existing chart PNG body has this shape (replace IDs with reviewed originals):

```json
{
  "type": "sense-image-1.0",
  "output": {
    "type": "image", "outputId": "selected-output",
    "imageOutput": {"outFormat": "png"}
  },
  "senseImageTemplate": {
    "appId": "selected-app-id",
    "selectionType": "selectionsByState",
    "selectionStrategy": "failOnErrors",
    "selectionsByState": {"$": []},
    "visualization": {
      "id": "selected-chart-id", "type": "visualization",
      "widthPx": 1200, "heightPx": 800
    }
  }
}
```

The corresponding request state has
`filters: {"selectionType":"selectionsByState","selectionsByState":{"$":[]}}`
and `parameters: {}`. Empty selections mean a requested cleared state, not proof
of the actual default-bookmark, expression or security population. A bookmark
profile replaces `selectionsByState` with `persistentBookmark: {"id": "..."}`
and uses `selectionType: "persistentBookmark"` in both template and state.

Sheet PDF uses `type: "sense-sheet-1.0"`, `senseSheetTemplate` and
`sheet: {"id": "...", "widthPx": 1200, "heightPx": 800}`. PDF output uses
`type: "pdf"` and `pdfOutput: {"size":"A4","orientation":"L","resizeType":"autofit"}`.
Every native sheet cell occurrence must map to an included placement and an
included, original-backed, nonrestricted query visual. Unresolved containers or
children cannot receive a whole-sheet rendering grant.

The host dispatches the fixed `/api/v1/reports` create endpoint, then derives
status/output requests from the retained request ID. Downloads are limited to
same-origin `/api/v1/temp-contents/{id}?inline=1` (the canonical query is optional).
No redirects, external output links or arbitrary API paths receive credentials.

QIX acquisition uses an already approved external host when available. Retain
method/arguments, original response, product/Engine version, app/principal,
isolated-session identity and observed state. No generic WebSocket client is
implemented or installed. Client-managed sources initially use supplied evidence.

## Numerical and visual evidence

`qlik-supplied-evidence.v1` imports bounded CSV/JSON/PNG/PDF or selected archive
members. Bind attachments to object and placement, definition fingerprint,
observed state, result population, freshness, scope and completeness evidence.
Source photos, charts and PDFs are reference pixels, never complete numbers.

Normalization has explicit parser profiles. Preserve Qlik numeric and display
values separately, including nulls, element/state metadata, totals and pivot axis
paths. Straight and pivot results are not interchangeable. Page rectangles must
cover the reviewed expected region without overlap or holes. Pivot completeness
is for an explicitly reviewed rectangle; it does not imply whole-cube coverage.
Unknown modes or semantics remain review gaps. Shared comparisons recompute the
normalized artifact from original bytes and the exact profile and case binding.

QIX profiles require all of these fields:

| Profile field | Meaning |
|---|---|
| `schema_version`, `format`, `shape` | `1`, `json`, and `qlik_straight` or `qlik_pivot` |
| `cube_pointer`, `pages_pointer` | JSON pointers into retained native response bytes |
| `metadata_sha256` | Hash of `cube_metadata(cube)` using the reader's canonical hash |
| `expected_area` | Explicit `qTop`, `qLeft`, `qWidth`, `qHeight`; straight mode must match all of `qSize` |
| `population_key`, `coverage_reference` | Reviewed population and evidence of expected coverage |
| `column_bindings` | Ordered `source_index`, `kind` (dimension/measure), and hash of each original metadata entry |
| `headers`, `columns` | Explicit output names and shared typed-column parser rules |
| `mappings` | Output components with `source_column` (or null for pivot coordinates/paths) |
| `subtotal_policy` | `preserve`; no silent filtering of totals |

Cell components include `number`, `text`, `is_null`, `element_number`,
`selection_state`, `cell_type`. Pivot profiles additionally require `row_index`,
`column_index`, `left_path`, `top_path`. Preserve original cell JSON and totals
even when a component is not selected for a comparison. Unsupported or collapsed
pivot axes stay unqualified; normalization is not a generic Qlik expression engine.

## Retained official MCP evidence

`qlik_check_mcp` accepts `qlik-mcp-evidence.v1` with exact fields:
`schema_version`, `server`, `identity`, `app_id`, `query_authorization_ref`,
`selection_authorization_ref`, `calls`.

Server fields are `endpoint`, `effective_version`, `schemas`, `reference`.
Endpoint must match the identity's HTTPS origin plus `/api/ai/mcp`. Identity has
`source_origin`, `tenant_id`, `principal_ref`, `reference`. Schemas retain exact
`name` and `inputSchema`; hashes pin each call's supplied schema.

Each call records `id`, `tool`, `arguments`, `response`, `schema_sha256`, `identity`,
`argument_pointers`, `response_pointers`, nullable `session_ref`, `reference`.
Argument mappings select `app_id` and where relevant `object_id` from retained
arguments. Response mappings can select `app_id`, `object_id`, `state`. This
declared crosswalk does not replace full vendor-schema or host scope validation.

The checker admits documented discovery/master-item/script/model reads, existing
chart/field queries, current-selection reads and explicitly recorded selection
changes. Queries require prior query authorization evidence and observed state
in the same session; changes invalidate prior state until a readback. Source
writes and ad-hoc temporary calculation creation are excluded. The checker
never calls the server or promotes a search hit to a complete native definition.

An imported capture, MCP check or local numerical pass cannot establish actual
permissions, source completeness, native quality, production readiness or
customer acceptance. Keep those lanes explicit in the specialist handoff.
