# Power BI source capture contract

Reviewed 2026-10-21. This is an implemented source acquisition boundary with synthetic transport qualification. It has not been qualified against a live tenant. It does not modify a source report/model, publish content, create an Omni artifact, or establish native/business acceptance.

## Reuse and entry points

`scripts/powerbi_capture.py` is standard-library only and imports its sibling `powerbi_capture_files.py`. Pin both files when exposing the fixed command to an agent host. The caller supplies a reviewed request, a new private capture directory and explicit read/query grants. Source credentials come only from injected arguments or bounded standard input; the script does not discover accounts, read credentials, sign in or refresh tokens.

Library calls:

```python
capture(request, directory, *, fabric_token=None, powerbi_token=None,
        transport=None, resume=False, allow_source_read=False,
        allow_source_query=False, now=None)
import_local(request, definition_root, directory, *, allow_source_read=False)
import_fabric_definition(request, payload, directory, *, allow_source_read=False)
```

All return `{status, output, capture}`; `output` is an absolute path to an immutable envelope inside the private directory. CLI output contains only `status` and `output`.

```sh
python3 powerbi_capture.py import-local --request /approved/request.json \
  --definition-root /approved/supplied-project --directory /private/new-capture \
  --allow-source-read
python3 powerbi_capture.py import-fabric --request /approved/request.json \
  --response /approved/get-definition-response.json --directory /private/new-capture \
  --allow-source-read
python3 powerbi_capture.py capture --request /approved/request.json \
  --directory /private/new-capture --tokens-stdin --allow-source-read \
  --allow-source-query
```

The host sends bounded JSON `{ "fabric_token": "<injected>", "powerbi_token": "<injected>" }` to stdin without shell arguments, logging or copying it into the request. Do not type literal credentials into saved examples. `--allow-source-query` is required only when the reviewed request contains queries. Explicit `--resume` continues the same directory/request/runtime; it does not repeat an uncertain POST. There is no overwrite option.

Local intake accepts a directory containing exactly one report definition, including a supplied PBIP/PBIR project or a report folder. It retains JSON, TMDL and resource bytes independently of DMA semantic parsing. It does not resolve `byPath` outside that supplied directory, follow `byConnection`, download resource URLs, decode PBIX/PBIT, run Desktop tooling, or execute M/DAX/SQL. A Fabric response must be the actual `{definition:{parts:[{path,payload,payloadType:"InlineBase64"}]}}` shape. Remote/resource-reference payload types are unsupported. No Desktop CLI dependency is introduced; independently transferred Desktop artifacts can be retained through this supplied-file route, with their provenance handled separately.

## Request version 1

Required fields of `powerbi-visual-capture-request.v1`:

| Field | Meaning |
|---|---|
| `capture_id` | Local operation identity, not a vendor ID |
| `workspace_id`, `report_id`, `dataset_id` | Live capture requires exact reviewed workspace/report UUIDs. Offline intake permits both workspace/report IDs null and uses the definition hash as namespace; never invent service IDs. Dataset may be null when no query is requested |
| `principal_ref`, `authorization_ref` | Supplied evidence references; never authenticated identity or scope proof |
| `evidence_mode` | `synthetic_fixture`, `live_tenant`, or `manual_transfer` |
| `route`, `route_reference` | Human selection: `unselected`, `reuse_existing`, `omni_semantic_reconstruction`, or `warehouse_first_refactor`; no inferred route |
| `views` | Up to 100 `{page_id,visual_id,export_png}` rows. Page IDs are native page names, visual ID is native name or null for a page; captions are not identity |
| `state` | `{state_id,filters,bookmark,locale,timezone,principal,data_time_policy}`; values are requested context, not observed state |
| `queries` | Up to 50 `{query_id,query,page_id,visual_id,context_reference}` reviewed DAX requests, each mapped to a selected view |

`state.filters` is at most one documented export filter object `{filter: "Table/Field eq 'value'"}`. `bookmark` is null or exactly `{name}` or `{state}`. A bookmark with a single-visual PNG is rejected: that vendor combination is not supported. Page exports may carry the bookmark. Locale is passed to export settings; timezone and principal remain supplied context and are **not** sent as impersonation/effective identity. No RLS role or dynamic dataset-binding override is implemented. Queries are separate reviewed DAX, not generated from or automatically synchronized with the render request.

Optional `expected_manifest` is `{reference,completeness:"selected_report"|"partial",objects:[{object_id,kind}]}`. Its default is partial/empty; it cannot prove tenant completeness. All supplied definition files remain in the envelope, including pages outside the selected render list. Selection does not imply exclusion approval.

For standalone files with no authenticated service crosswalk, use null workspace/report IDs. The producer emits `source.identity.identity_scope:definition_only` and `namespace:definition:<fingerprint>`. A later service crosswalk is new evidence, not a reason to rewrite the original identity. `validate_request(..., require_service=True)` enforces the live-only identity rule.

Defaults: 20 HTTP requests per invocation, 200 total requests, 64,000,000 cumulative response bytes, 21,600 seconds capture age, three attempts/polls per operation, 8,000,000 bytes per response. Limits are validated and finite. Deadline enforcement uses a real wall-clock timer per request plus elapsed invocation time. Requests are sequential. Polling performs at most one status request per pending job per invocation; the operator explicitly resumes. `Retry-After` is retained and enforced without blocking sleeps.

## Fixed source REST routes

Only these routes are constructed; no server URL is fetched generically:

| Audience | Operations |
|---|---|
| `api.fabric.microsoft.com` | `POST /v1/workspaces/{workspace}/reports/{report}/getDefinition?format=PBIR`; exact returned operation UUID bound to `GET /v1/operations/{id}` and `/result` |
| `api.powerbi.com` | Report and pages GET under `/v1.0/myorg/groups/{workspace}/reports/{report}`; PNG `ExportTo` POST; scoped `/exports/{encoded-id}` status and `/file` GET; `POST /v1.0/myorg/datasets/{dataset}/executeQueries` |

Fabric token and Power BI token are separate. The helper does not verify token claims, tenant configuration, consent, identity, or audience; it only confines where each supplied token is sent. Sovereign-cloud origins are not supported. Redirects, alternate hosts and unexpected LRO/download locations are rejected. Export IDs are encoded as a single path component; dot segments are rejected. Signed/query-bearing download URLs are not followed or retained as working access links.

Fabric definition retrieval is a read-like POST but requires report read/write permission and delegated `Report.ReadWrite.All` or `Item.ReadWrite.All`. Its definition excludes sensitivity labels. Responses are 200 definitions or 202 operation receipts. [Get Report Definition](https://learn.microsoft.com/en-us/rest/api/fabric/report/items/get-report-definition). LRO state is retrieved separately; only documented pending/success states advance and unknown states stop. [Get Operation State](https://learn.microsoft.com/en-us/rest/api/fabric/core/long-running-operations/get-operation-state), [Get Operation Result](https://learn.microsoft.com/en-us/rest/api/fabric/core/long-running-operations/get-operation-result).

Power BI export requires report and dataset read scopes (or their write variants). The implementation submits one exact page or visual per job and binds later downloads to its returned export ID. [Export To File](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/export-to-file-in-group), [Export Status](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-export-to-file-status-in-group), [Export File](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-file-of-export-to-file-in-group). Capacity and tenant settings apply; PNG export is not supported by PPU, and personal bookmarks/persistent filters are unsupported. A multiple-image response to one selected export is retained only as a diagnostic response and blocks mapping; no filename/caption guess assigns images to visuals. [Export guidance](https://learn.microsoft.com/en-us/power-bi/developer/embedded/export-to).

ExecuteQueries uses one query with `includeNulls:true`. The service requires read/build permission and its tenant setting, supports DAX rather than arbitrary source programs, and may return HTTP 200 with partial rows plus an error. The helper checks result/table errors, row/value counts and its tighter byte bound. Query attachments retain the original response bytes, including numeric tokens; shape checking never rewrites them through floating-point serialization. It preserves column keys exactly and never converts returned rows into proof of render-state equivalence. Service principals have RLS/SSO restrictions. [Execute Queries](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries).

## Envelope, persistence and completion

`powerbi-visual-capture.v1` includes the normalized request and canonical hash, producer file hashes, original source identities, `source.definition_files`, definition fingerprint, metadata before/after, capture rows, pinned attachments, operation receipts, jobs, cumulative budgets and a chained journal hash. Each definition row separates captured `path` from original `source_path` and stores SHA-256/byte count plus exact UTF-8 content when applicable. Binary resources have `content_utf8:null`. The fingerprint hashes sorted `{source_path,sha256,bytes}` entries; packet filenames do not change source identity. The translator checks native page/visual IDs separately and retains unsupported objects.

Responses and artifacts use immutable private files. The helper rejects symlinks, path traversal/collisions, malformed/duplicate-key JSON, recognized credential-bearing metadata, unbounded files and forbidden model archives. Known injected token bytes must never appear in retained responses. These checks are a bounded guard, not a guarantee that arbitrary source text contains no sensitive data; the operator must supply the approved private export scope. PNG checks validate chunks/CRCs, bounded decompression and row filters. Only 8-bit noninterlaced grayscale/RGB/alpha encodings are supported; unsupported images stop explicitly. PNG ZIPs are inspected in memory, with path/member/type/size/expansion bounds and no extraction or execution.

Before each HTTP call, an immutable intent and request reservation are written. An exception or ambiguous response leaves an unresolved operation and blocks automatic replay, including after restart. Known 429 responses may retry after the saved delay within attempt budgets. Unknown response-byte usage is conservatively reserved. Changes to request, source evidence or runtime hashes reject resume. A hash chain detects changed bytes, not a malicious authorized re-author or authenticated provenance.

`complete` means requested acquisition finished and the before/after report definition and metadata bracket agree. It does not mean atomic data snapshot, effective access, applied filter/bookmark state, semantic conversion or acceptance. Definition/query errors, unsupported states and source drift remain explicit partial/blocked outcomes. Automatic `source.state_observation` stays unknown; query attachments carry `result_completeness.status:unknown|partial`, never automatic `complete`. Refresh time, data watermark, RLS/OLS and effective principal remain unverified. `target_write_authority:false`, `native_validation:not_performed`, `business_acceptance:not_assessed` are invariant.

The producer does not invoke DMA. Reuse a separately trusted/pinned DMA reader to attach exact `powerbi_source_inventory` or `source_adapter_result` evidence without changing either kind. PBIR object coverage must remain independent: the legacy reader can omit later visuals after an unsupported query and cannot traverse a TMDL-only PBIP report without `model.bim`.

## Analyst reader and result normalization

`powerbi_visual.py` exposes `validate_capture(value)`, `verify_capture_files(value, capture_json_parent)`, `inspect_definitions(source.definition_files)` and `normalize_results(raw_bytes, profile, binding)`. Projection preserves file-scoped object IDs and native page/visual identities separately. Actual file verification belongs before requirements or comparison; self-hashes alone do not authenticate origin.

Normalization binding contains exactly `capture_content_hash`, `page_id`, `visual_id`, `state_sha256`, `query_id` and `attachment_sha256`. The schema-1 profile specifies `format:csv|json`, exact ordered `headers`, `columns` with ordinal/name/type/nullable/null_tokens, and `subtotal_policy:preserve`. CSV requires UTF-8; duplicate headers require an explicit resolution reference. JSON requires `rows_pointer`. Numbers require explicit decimal/group separators and percent handling; currency additionally declares code/prefix/suffix/negative-parentheses behavior, and dates require a format. No sums or subtotals are recomputed from appearance. Output `powerbi_normalized_results` retains raw hash, profile, binding and typed rows.

The visual workflow uses source format `powerbi-normalized` with a separately pinned `raw_file`. Independent `value_state_observation` and `render_state_observation` must match applied state and reference, page/visual/state IDs, principal, filters, bookmark, locale, timezone and data watermark; value state also matches query ID. Query completeness requires its own `complete` assertion and evidence reference. Those are separately supplied review assertions, not facts inferred by the capture layer; its automatic unknown/partial statuses remain unchanged.

## Offline qualification

`tests/test_powerbi_capture.py` provides authored production-shaped PBIR with two equally captioned pages, three different visual types, repeated native visual names scoped to pages, bookmarks/interactions, TMDL without BIM, and resource bytes. Transport fixtures emit the actual definition, LRO, export and query response contracts. They test persisted bytes, source drift, grants/audiences, retries, uncertain POSTs, bounded jobs, malformed payloads, paths/media and secret boundaries. These tests neither open Power BI nor certify native JSON schemas, render fidelity, customer security or business correctness.
