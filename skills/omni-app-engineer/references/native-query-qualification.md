# Offline native-query qualification

Use this small probe before composing a substantial query-backed App or repairing its data boundary. It validates supplied evidence; it does not connect to Omni, execute SQL, dispatch workers, mutate a model, grant authority or establish browser behavior. Use the existing query contract and runtime evidence paths; this is an optional linked qualification artifact, not a replacement engagement lifecycle.

## Capture first, select exact values

Retain the requested source identity separately from observed connection/model/query readback. Verify the physical database/schema from inspected bindings or generated/executed SQL, not the connection display name or default database. A model ID alone does not establish the physical source. For a multi-query/multi-source App, qualify each required query/source independently, then review their combined population and freshness rules.

A private evidence bundle may contain unmodified connection/model/query/result captures under separate keys. Use exact JSON pointers into that bundle, with a small observed binding object that cites where each identity was verified. Do not re-key rows, fill missing metadata, convert blank strings to NULL, or copy the requested binding into observed evidence to make a check pass. If a documented projection is necessary, retain the original capture and transformation separately; a reconstructed callback is `constructed_fixture`, never `native_callback`.

```sh
python3 -I -S -B skills/omni-app-engineer/scripts/native_query_probe.py \
  --contract /private/engagement/probe-contract.json \
  --evidence /private/engagement/captured-evidence.json \
  --expectations /private/engagement/expected.json \
  --evidence-root /private/engagement
```

The command only reads local JSON and writes its report to stdout. Exit codes: `0` = supplied evidence consistent, `1` = qualification findings, `2` = invalid input. The caller may retain stdout in the engagement. Python integration: `probe(contract, evidence, expectations, evidence_root=private_engagement_root)`. Without an evidence root, the API reports `expectation_source_not_loaded`; it does not pass a declaration-only count.

The input files and the independent source are bounded at 16 MiB each; rows/limits are bounded at 100,000. Symlinks (including parent links), duplicate JSON keys, nonfinite numbers and invalid/bounded pointers are rejected. No credentials belong in these files. Reports contain field-level findings, aggregate comparisons and input hashes, not raw records or token values.

## Small configurable contract

This **original synthetic example** uses invented field names and a deliberately simple capture envelope. It is not an Omni callback schema. Select paths, metadata types and complete-status spelling from the actual qualified transport. `requested` requires exact connection, database, schema, model and query name; add document/draft IDs when available (`draft_id: null` means the observed published target).

```json
{
  "schema_version": 1,
  "kind": "native_query_probe_contract",
  "requested": {
    "connection_id": "inspected-connection-id",
    "database": "REQUESTED_DATABASE",
    "schema": "REQUESTED_SCHEMA",
    "model_id": "inspected-effective-workbook-model-id",
    "query_name": "Observed items"
  },
  "query": {
    "fields": ["items.id", "items.amount"],
    "filters": {},
    "limit": 1000
  },
  "fields": [
    {"key": "items.id", "type": "string", "nullable": false, "metadata_type": "TEXT"},
    {"key": "items.amount", "type": "decimal_string", "nullable": true, "metadata_type": "DECIMAL"}
  ],
  "grain": ["items.id"],
  "complete_status": "complete",
  "metadata": {"layout": "list", "name_key": "name", "type_key": "type"},
  "selectors": {
    "binding": "/binding",
    "query": "/query",
    "status": "/result/status",
    "columns": "/result/columns",
    "rows": "/result/rows",
    "limit": "/result/limit",
    "truncated": "/result/truncated",
    "exhaustive": "/coverage/exhaustive",
    "total_rows": "/coverage/total_rows"
  },
  "concurrency": {"mode": "serialized", "max_in_flight": 1, "qualification": "unavailable"}
}
```

The `query` object must match the observed object exactly, including any extra contracted filters, sorts, limits, SQL or other population-affecting keys. Point at the exact query object appropriate to that contract; do not remove an observed cohort filter to match it. `fields` must match the selected field list/order. Metadata may be a list or an object keyed by field ID; object layout uses `type_key` and needs no `name_key`. Extra metadata for filter-only fields is allowed, but every selected field needs usable metadata of its exact declared type. Rows must contain exactly the selected keys, including for NULL values. Missing metadata fails even when there are zero rows.

Allowed value types are `string`, `integer`, `number`, `boolean` and `decimal_string`, with explicit nullability. Integers must be within the JavaScript safe-integer range (−9,007,199,254,740,991 to 9,007,199,254,740,991); use `decimal_string` for larger exact values. No coercion occurs. Boolean `true` is not numeric `1`; empty string is not NULL. Decimal strings preserve precision and use an explicit numeric grammar. Finite numbers are bounded to 100 significant digits and an adjusted exponent magnitude of 1,000; use a separately reviewed contract for larger values. Dates/timestamps remain exact strings here; timezone/calendar interpretation belongs to the reviewed adapter. Sums/counts and mean comparisons use decimal arithmetic; use an explicit absolute tolerance for a rounded mean.

Each evidence bundle additionally declares `lane` (`query_export`, `native_callback`, `constructed_fixture` or `source_contract`) and `provenance: {"reference": "retained capture/method reference"}`. Lane labels are supplied claims, not authenticated observations. A consistent `native_callback` capture still reports `native_execution_verified: false`, `native_callback: supplied_capture_only`, rendering/access unassessed and recovery unexecuted. The source/export/fixture lanes never become native proof.

## Independent population and aggregates

Prepare expectations from a separate source query/calculation before inspecting the implementation's computed result. Preserve its source, exact population filters, snapshot/watermark and method. The helper does not generate expectations from the candidate rows. An independent expected count plus exact query/filter equality is required in addition to terminal status, reported total and nontruncation. Flags alone cannot pass. Reaching the row limit fails conservatively even when the response claims completeness; increase the qualified limit or obtain a separately qualified pagination/completeness route. Do not narrow the requested cohort to fall below the cap.

The separate expectations manifest has this form; the SHA below must be replaced with the actual retained independent evidence file hash. Values here are invented.

```json
{
  "schema_version": 1,
  "kind": "native_query_probe_expectations",
  "provenance": {
    "method": "independent_query",
    "reference": "evidence/independent-count-and-sum.json",
    "sha256": "ACTUAL_SHA256_REQUIRED"
  },
  "requested": {
    "connection_id": "inspected-connection-id",
    "database": "REQUESTED_DATABASE",
    "schema": "REQUESTED_SCHEMA",
    "model_id": "inspected-effective-workbook-model-id",
    "query_name": "Observed items"
  },
  "filters": {},
  "rows": 3,
  "rows_pointer": "/row_count",
  "aggregates": [
    {"id": "amount-sum", "op": "sum", "field": "items.amount", "expected": "0.30",
     "non_null_rows": 2, "absolute_tolerance": "0",
     "expected_pointer": "/amount_sum", "non_null_pointer": "/amount_known"}
  ]
}
```

For this example, the separately retained evidence contains `{"row_count":3,"amount_sum":"0.30","amount_known":2}`. The referenced file must exist beneath the selected private evidence root, match its SHA, and contain the declared count/expected value/denominator at the exact pointers. Missing/stale source evidence fails. Counts may be represented as numeric strings in the source; values are compared without turning blanks into zero. Supported aggregate operations are `sum`, `mean`, `count_non_null` and `count_true`; NULL input is excluded explicitly, and `sum`/`mean` of no known values is NULL. Every expectation includes the known-value denominator. A nonempty composite `grain` rejects NULL/empty identities and duplicate keys.

Independence, authenticity, original-request completeness and equivalent snapshot scope still need reviewer judgment. A matching count cannot prove that two different cohorts contain the same records. Do not rewrite the contract, observed filters and expectations together merely to hide a source mismatch. Link the original requested population and exact evidence in the normal selected intent/query records.

## Isolated source-binding fallback

A read-only SQL result can contain rows while the native adapter has no usable semantic field metadata. Saving the same raw SQL may not fix that. First inspect the effective model, existing fields and actual result metadata; reuse a valid existing model route when it matches the requested source.

If the requested database is accessible but absent from the existing catalog/model inventory, report the smallest isolated proposal: exact new document/workbook model, one query-view, explicit fully qualified source and required dimensions, affected named query, verification and rollback. Resolve the model-write scope before writing. Do not change shared connection catalog settings, permissions, warehouse tables or existing shared views to repair an App. A query-view is a possible documented route, not an automatic entitlement or universal fix.

After an authorized isolated change, re-read the effective workbook identity and source SQL, run the exact semantic field/filter query, require usable metadata and reconcile the independent population/aggregates. A new draft can have a cloned workbook model ID: verify that new identity and binding before publication. Check unchanged shared model/connection state separately. Offline probe consistency is only one input to this process; this helper never performs a model change.

## Observed payload details — requalify before use

A bounded clean run on **2026-10-23** observed the current tenant App API, whose documentation said **“currently in development and may change.”** These details describe that qualified path, not a universal or permanent vendor contract:

- Initial document creation accepted `app: {"html": "..."}` alongside the normal creation fields and `queryPresentations`. This can publish immediately; inspect side effects and existing authorization. Do not create temporary existing-content mutations to discover the route.
- A semantic query presentation used `"type":"query"`, `"isSql":false` and required `"query":{"userEditedSQL":"", ...}` in the draft-write payload. Empty SQL here did not change the intended semantic query. The `...` denotes required inspected query fields, not valid JSON to submit.
- A string filter required its explicit type, for example `{"type":"string","kind":"EQUALS","values":["reviewed-value"]}` beneath the exact semantic field ID. This example does not qualify other filter types/operators.
- Successful raw-SQL exports had empty semantic `summary.fields`; a workbook-only SQL query-view produced usable field metadata. JSON exports also represented some absent values as empty strings, whereas inspected native adapter source preserved NULL. Never apply that conversion to production input without qualifying the actual boundary.

Inspect current official schemas/readback and retain tool/runtime revisions before executing. Official references: [Public OpenAPI](https://docs.omni.co/api/openapi.yaml), [Replace App draft content](https://docs.omni.co/api/apps/replace-app-content-on-a-draft). These links are reference routes to recheck, not proof that a later host has identical capabilities. No network call is made by this offline helper.

## Recovery and concurrency

When correlation is unavailable or only source-qualified, serialize: one in-flight query sequence, no overlapping refreshes, and no new applied query/filter generation until the previous sequence has a qualified terminal/reset path. A hung query requires an explicit supported recovery route; do not invent cancellation or a timeout that makes an older callback safe. Preserve or clear stale displays according to the selected state contract.

`concurrency.mode: correlated` requires declared `qualification: native_observed`, an engagement-relative `evidence_ref` with matching `evidence_sha256`, and the `native_callback` lane. The referenced JSON must exist and match its hash; missing evidence fails. Its behavioral meaning and authenticity still need independent review, and the helper reports recovery unexecuted. Native failure/empty/error/stale and competing completion sequences must be observed separately where allowed. A synthetic generation counter around a callback without request identity cannot establish correlation. If those semantics remain unsupported, retain serialized behavior and the limitation rather than simulating a native guarantee.
