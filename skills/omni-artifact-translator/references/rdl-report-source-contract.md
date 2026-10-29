# Shared supplied RDL source contract

The standard-library `scripts/rdl_report.py` reader supports passive structural
inspection for SSRS and Power BI **paginated** reports. It never treats PBIR/PBIP
interactive report JSON as RDL, compiles expressions, runs queries, loads assemblies,
follows resources or validates a complete vendor schema. No DMA producer is implied.

## Snapshot and identity

`rdl-report-snapshot.v1` has exactly `schema_version`, `identity`, `report_xml`,
`inventory` and `gaps`.

- `identity`: `source_platform` (`ssrs` or `powerbi_paginated`), `source_origin`
  (HTTPS origin or null), `product_version`, `principal_ref`, `report_id`,
  `workspace_id`, `content_path`, `reference`. The three IDs/path fields may be
  null; SSRS workspace is always null. Unknown service IDs stay null. These are
  supplied assertions, not authenticated access or permission.
- `report_xml`: `encoding: utf-8`, original `content`, exact `bytes`, `sha256`,
  `reference`. Original UTF-8 bytes must agree; no source XML rewriting occurs.
- `inventory`: `reference`, `completeness: partial|selected_scope_declared`, and
  `items`. Each item has `key`, `kind`, `parent_key`, `native_id`, `locator`,
  `disposition`, `reference`, `configuration`. Locator is a positional XML path:
  `/` is root, `/0` its first element child. It is not XPath or a native catalog ID.
  Kinds cover report/page, dataset/data_source/field/query, parameter, visual/
  placement/layout/content, filter/sort/group/expression/action/subreport/resource/
  code/unknown. Dispositions are include/manual_review/unsupported/unavailable/
  out_of_scope. Parent, native-name and locator references are validated.
- `gaps`: supplied nonempty-text evidence gaps, preserved without conferring authority.

Independently enumerate expected scope. The reader retains every XML node and
emits additional obligations for unrepresented semantic/unknown occurrences.
Repeated placements keep independent keys even when they use the same dataset.
Names are case-sensitive and dataset name ambiguity does not become a valid binding.
Private/denied parent scope propagates; excluded or missing datasets cannot qualify
query-result comparison. `query_visual` means a source query obligation, not a
numerical, renderer, security or semantic-model pass.

Accepted root namespaces are the Microsoft reportdefinition namespaces for
2003/10, 2005/01, 2008/01, 2010/01 and 2016/01. Unknown dialects reject; extension
namespaces remain explicit unknown obligations. Namespace recognition does not
certify construct support in every dialect. Raw queries, expressions, custom code,
subreport/data source/shared dataset references and property order remain evidence.
No expression language conversion is performed.

## Bounds and interfaces

XML is bounded to 2 MiB, depth 64 and 12,000 nodes; the wrapper is bounded to
8 MiB and 2,000 independently supplied inventory entries. DTD/entities, non-UTF-8,
malformed XML, unsafe declarations and recognized credential material reject.
External schemas/images are never fetched. Recognized screening is not complete
DLP; supply only the approved private source scope.

Functions: `make_snapshot(raw,identity,inventory,reference,gaps=None)`,
`inspect_xml(raw)`, `validate_snapshot(value)`,
`translate(value, raw, helpers)` (alias `parse_snapshot`), `scope_item(value,key)`.
The shared translator supplies `base`, `add_asset`, `gap` and `FACETS` helpers.
Output format is `supplied_rdl_report_snapshot` with the original platform,
original bytes/hash, independent occurrence identities and unresolved obligations.

Neutral working fixtures live in `tests/test_rdl_report.py`; they are original
synthetic observations, not exports from a tenant or comprehensive schema tests.
Use the [capture contract](report-source-capture.md) for private files and evidence.
