# Tableau source and comparison contract

This is the maintained local contract, not a statement that a customer tenant has passed qualification. Source acquisition is implemented by `tableau_capture.py`; the visual bridge and workflow never acquire or execute customer sources. The current acceptance boundary remains candidate preparation, recorded evidence and explicit gaps. Capture completion does not establish applied filters, atomic data time, effective access, parity, publication or business acceptance.

## Source packet and identities

`tableau-visual-capture-request.v1` selects one source state and one dashboard plus explicit worksheet REST views. Use the request schema in the capture helper; preserve its exact HTTPS origin, API version, site/workbook/view IDs, selected principal, authorization reference and finite budgets. Nonempty parameter execution is currently unqualified for direct REST capture and stops; supplied evidence can still be retained through the supported intake workflow. No source request grants a target write.

The capture envelope is `tableau-visual-capture.v1`. Its `request_sha256` and `content_hash` use UTF-8, `ensure_ascii=False`, sorted keys, compact separators, finite JSON; `content_hash` excludes itself. These seals detect changes, not origin or reviewer authenticity. `source.definition` contains `{path, sha256, bytes, content_utf8}` for exact bounded UTF-8 TWB bytes. TWBX bytes remain separately pinned in `source.original_definition`. XML/ZIP safety is shared with the maintained capture file boundary: no extraction, entities, credentials, ambiguous members or unbounded expansion.

The APIs have different identity domains:

- REST `site_id`, `workbook_id`, `view_id` identify published objects.
- Native worksheet UUID, repository ID and names remain separately retained evidence.
- `object_id` is an indexed XML locator scoped by the exact definition SHA, such as `/workbook[1]/worksheets[1]/worksheet[1]`. It is not a server-issued ID.
- Every zone placement has its own locator, parent, dashboard and device-layout identity. Three placements of one worksheet produce three placement obligations plus the shared worksheet definition. XML's exact declared worksheet reference resolves only when unique in that workbook; REST identity is never guessed from captions.

The independently supplied denominator and crosswalk are hashed inside the request:

```json
{
  "expected_manifest": {
    "schema_version": 1,
    "reference": "reviewed-source-listing-reference",
    "completeness": "selected_dashboard",
    "objects": [
      {"object_id": "/workbook[1]/worksheets[1]/worksheet[1]", "kind": "worksheet"},
      {"object_id": "/workbook[1]/dashboards[1]/dashboard[1]/zones[1]/zone[1]", "kind": "placement"}
    ]
  },
  "identity_map": {
    "schema_version": 1,
    "mappings": [{
      "view_id": "worksheet-view-id",
      "object_id": "/workbook[1]/worksheets[1]/worksheet[1]",
      "status": "matched",
      "evidence_reference": "reviewed-UUID-and-view-crosswalk"
    }]
  }
}
```

The example is a shape, not a complete dashboard manifest. Include the workbook, dashboard, worksheet definitions, placements, controls, parameters, layout/device containers, actions, filters, text/media and unsupported objects. `completeness: partial` is valid and remains partial. An unresolved map has `status: unresolved`, `object_id: null` and no fabricated match. Unknown zone types remain `unknown` assets. Missing expected objects become explicit unobserved obligations; unexpected observed objects remain in the projection with a gap. Workbook-level actions and parameters remain conservatively in a selected dashboard slice because unresolved dependencies must not disappear.

`tableau_visual.inspect_workbook(raw_twb, source_path)` is a bounded visual reader; it does not interpret formulas or generate a semantic model. `translate_artifact.py --format tableau-capture` produces the existing `omni_analyst_source_inventory`, with `source.platform: tableau` and `source.format: supplied_tableau_visual_capture`. The legacy `dma-inventory` path remains unchanged. File coverage, supplied-manifest reconciliation, requested capture coverage and behavior coverage are separate fields. Before a definition has been captured, a blocked journal is diagnostic evidence; it cannot yet be imported as a visual inventory.

## Actual files and semantic enrichment

Call `tableau_visual.validate_capture(envelope)` for structural/hash checks and `verify_capture_files(envelope, root)` for actual files, where `root` is the capture JSON's parent directory. Paths are canonical relative paths; symlinks, collisions, aliases and escapes reject. Every attachment, definition and retained operation response pin is checked against current bytes. PNG/CSV and TWBX safety is reapplied; extracted XML must match the original package. Workflow requirements reverify these files, so a later image, result or definition edit invalidates retained evidence.

For example, `inputs/capture/capture-000025.json` expects `definition.twb` and `view-001.csv` beneath `inputs/capture/`, not the frontend project root. Keep attachment paths stable when transferring the packet. Original MCP responses and allData part order/errors stay retained; ambiguous parts do not establish an identified sheet or a complete dashboard result.

DMA semantic interpretation stays with the trusted DMA runtime. Prefer the source helper's explicit `enrich_dma(capture_path, checkout=trusted_checkout, executable=trusted_python, expected_reader_sha256=exact_reader_hash, producer_revision=reviewed_revision)` API or `enrich-dma` CLI. It runs the maintained `tableau_source.inspect_repo` in an isolated local subprocess against only the pinned safe definition, records `source.semantic_producer`, and writes a new journal revision; existing journals remain unchanged. Retain its emitted `schema_version: 1`, `kind: tableau_source_inventory` unchanged, including all file hashes and gaps. A separately produced derived capture copy may instead add:

```text
source.semantic_inventory = exact DMA output object
source.semantic_inventory_sha256 = canonical UTF-8 JSON SHA-256 of that object
derivation = source journal reference + source content hash + trusted local enrichment provenance
```

The inventory must contain an asset SHA matching the exact embedded TWB. For a manual derivative, recompute its seal and save under a new derivative filename. Do not overwrite acquisition journals or imply a manual derivative was emitted by the REST capture producer. Keep producer/runtime provenance as supplied evidence; the bridge does not authenticate a checkout or execute a path named by customer input. An absent semantic inventory is a retained gap, not a reason to discard useful visual evidence. This enrichment does not choose `reuse_existing`, `omni_semantic_reconstruction` or `warehouse_first_refactor`; the analyst requirements record the separately reviewed route.

## Per-case state and result identity

Requirements keep the existing schema. A Tableau case that uses captured evidence supplies:

```json
{
  "source_capture": {"path": "inputs/capture/original.json", "sha256": "exact-file-sha256"},
  "source_binding": {
    "view_id": "worksheet-view-id",
    "worksheet_id": "/workbook[1]/worksheets[1]/worksheet[1]",
    "placement_id": "/workbook[1]/dashboards[1]/dashboard[1]/zones[1]/zone[1]",
    "state_sha256": "canonical-request-state-sha256"
  }
}
```

For a worksheet-definition case, `placement_id` is null. View identity must resolve through the capture crosswalk; definition/site/workbook, worksheet, placement and state must match exactly. A different state requires a separately captured and pinned source state. Default, changed filter, changed parameter, reset/empty/action behavior and allowed/denied personas remain separate obligations. Unknown or unsupported actions stay pending; do not simulate a successful capture.

Requested state is not observed state. Numerical comparison needs independently retained `source.state_observation` with `reference`, exact `filters`, `parameters`, `locale`, `timezone`, `principal` and `data_watermark`. If selected marks, action state or custom-view identity are present in the request, retain and compare them separately too. The present REST helper does not assert these applied-state observations automatically. Missing observations, wrong source context, incomplete capture or mismatched data time produce an inconclusive comparison even when caller-authored source and target context values agree. Source and target principals remain separate and need the existing reviewed persona-equivalence reference. Current comparisons remain recorded local evidence, not authenticated native validation.

## Explicit CSV normalization

Use `tableau_visual.normalize_results(raw_bytes, profile, binding)` to create a derivative only when formatting needs interpretation. Preserve original CSV bytes. Supported first-pass types are `string`, `number` and explicit-format `date`. The profile deliberately refuses guessed locale, implicit nulls, stripped subtotal rows and silently renamed duplicate headers:

```json
{
  "schema_version": 1,
  "format": "csv",
  "encoding": "utf-8",
  "headers": ["Team", "On time %"],
  "subtotal_policy": "preserve",
  "columns": [
    {"ordinal": 0, "name": "team", "type": "string", "nullable": false, "null_tokens": []},
    {"ordinal": 1, "name": "rate", "type": "number", "nullable": true, "null_tokens": ["NULL"],
     "decimal_separator": ",", "group_separator": ".", "percent": true}
  ]
}
```

The raw headers must match in exact order; ordinal mappings cover every column. If headers repeat, add `duplicate_header_resolution_reference` for the reviewed ordinal-to-name mapping; all output names must be unique. A date column supplies `date_format`, for example `%d/%m/%Y`; output is ISO text and compares as `string`. Numeric decimal separator is `.` or `,`; group separator is null, `.`, `,` or a space and must differ from the decimal separator. Explicit `percent: true` requires `%` and divides by 100 without rounding. `1.234,50%` therefore becomes decimal text `12.3450`. Empty string and `NULL` differ unless explicitly listed as null tokens. Totals remain rows and need a meaningful key or a separately reviewed scope decision.

The exact binding is:

```text
{capture_content_hash, view_id, worksheet_id, state_sha256, attachment_sha256}
```

The output is `schema_version: 1`, `kind: tableau_normalized_results`, with `raw_sha256`, `parser_profile`, `binding`, original `headers`, `row_count`, typed `rows`, `row_order: preserved`, and `completeness: not_established`. Completeness still requires separately retained evidence. Decimal values remain strings to avoid binary-float rounding.

In an existing `analyst_numeric_comparison_spec`, the source side uses `format: tableau-normalized`, `file: {path,sha256}` for the derivative, and `raw_file: {path,sha256}` for the original CSV, plus the ordinary context/completeness fields. Comparison columns refer to normalized output names. The verifier replays normalization from raw bytes and requires exact derivative equality, then checks the raw attachment, sheet, state and capture binding. Editing and rehashing the derivative cannot produce a pass. Raw unformatted CSV can use the existing `format: csv` path.

Keyed comparison defaults to unordered rows. For a reviewed ranking/display-order obligation, set top-level `row_order: exact` and a nonempty `order_basis`; a changed key order fails independently of numerical equality. Duplicate keys still reject. Large evidence remains in private files; current project and cowork limits remain unchanged. No reference-only workaround makes a semantically incomplete packet a complete dashboard migration.
