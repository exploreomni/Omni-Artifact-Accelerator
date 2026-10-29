# Supplied report capture, results and operation plans

`scripts/report_source_capture.py` uses only the existing Python standard library
and first-party helpers. It performs no network calls, login, query execution,
rendering, native write or distribution. `capture()` fails closed. Fixed source
operation plans are reviewable request descriptions, never executable grants.

## Immutable intake

`report-source-capture-request.v1` contains `schema_version`, `capture_id`,
`snapshot_path`, `definition_path`, `inventory_path`, `evidence_mode`
(synthetic_fixture/manual_transfer/live_tenant), `authorization_ref`, `route`
(unselected/reuse_existing/omni_semantic_reconstruction/warehouse_first_refactor),
`route_reference` (null only when unselected), `target_surface: report`, and `state`.
Paths are source-root-relative regular files. An evidence-mode or reference is
not provenance authentication. Request/source paths never direct a network call.

State contains `filters: {dataset:[],report:[],group:[]}`, `parameters`,
`timezone`, `locale`, `principal`, `cache`, `reference`. Each parameter has unique
`name`, `answer_mode` (explicit/default/null/blank/omitted/unresolved), and `values`.
Null is `[null]`, blank `[""]`; omitted/unresolved have no values. Context may be
null when unknown; unknown context cannot establish numeric parity.

`import_local(request, source_root, directory)` verifies the exact supplied
snapshot, definition and independent inventory before writing an initially empty
private directory. Supported snapshots are `rdl-report-snapshot.v1` and
`crystal-report-snapshot.v1`; the latter delegates to the distinct Crystal reader
and matches its original extraction bytes, without binary decoding. The envelope
`report-source-capture.v1` pins the three files, embedded snapshot, definition
fingerprint, request, attachments and previous revision. Append-only revisions
retain prior files; no overwrite is supported. Hashes detect drift, not a malicious
re-author or authenticated provenance. All results are private 0600 files.

`import_evidence(directory,evidence,source_root)` adds a separate CSV/JSON/PNG/PDF
attachment. Evidence fields: attachment_id, object_key, format, result_scope
(dataset_result/report_result/displayed/unknown), observed_state, population,
freshness, completeness, reference, source_path, parser_profile. Numeric evidence must
retain the exact parser profile; PNG/PDF use null. Stored records replace source_path
with the immutable file pin. Observed state includes state, observed_at, reference,
execution_status, placement_reference (nullable) and result_context (nullable).
Population is `{key,description,reference}`; freshness is
`{data_watermark,observed_at,reference}`; completeness is
`{status:complete|partial|unknown,row_count,reference}`.

A complete numeric declaration requires a completed observation, row count and
population/freshness references. This remains supplied evidence; flags do not
prove native execution. PNG structure and PDF signatures are bounded byte checks,
not rendering, safety certification or appearance QA. Files are limited to 8 MiB,
128 attachments/32 MiB total, and 64 revisions. No archive extraction occurs.

## Exact results and comparison

`normalize_results(raw,profile,binding)` supports explicit UTF-8 CSV and JSON
object rows only. The schema-1 profile has format, ordered headers, columns,
rows_pointer (null for CSV), subtotal_policy=preserve. Columns have ordinal,name,
type (string/decimal/integer/boolean), nullable and null_tokens. JSON pointers
traverse dictionary keys. Duplicate headers, ragged rows, localized display numbers,
nonfinite values and fractional integer mappings reject. Exact raw decimals and
int64 values are retained as decimal strings; no sums or subtotals are invented.

Binding is capture_content_hash, definition_fingerprint, state_sha256, object_key,
attachment_id and attachment_sha256. Result kind is report_source_normalized_results;
workflow format is report-normalized with separately pinned raw_file.
Recompute normalization from those raw bytes before comparison.

A numeric source item must be independently included and bind its dataset.
`configuration.result_contract` and observed `result_context` carry data_mode
(full_data/preview/test/unknown), row_limit, row_limit_stage
(before_aggregation/after_aggregation/none/unknown), aggregation_stage
(dataset/in_report/unknown), reference. Preview compares only the same explicit
population/limit semantics. Missing/test/unknown, partial execution, unresolved
parameters, row-count drift or mismatched freshness remains inconclusive. Report
placements additionally need report_result, in_report aggregation and an observed
placement reference; raw dataset CSV cannot certify report calculations or layout.
Target cache remains an independent choice; observed source cache must match its
own requested state. Effective target access is a separate lane.

Public helpers: validate_request, validate_envelope, verify_capture_files,
check_capture (alias check), load_latest(directory,config=None), parse_capture,
case_binding, comparison_gaps, normalize_results, verify_normalized_result.
The normalized projection format is supplied_report_source_capture.

## Fixed request planners, not connected capture

`plan_operation(profile,operation)` emits method, fixed URL/body, request/profile
hashes, declared budgets and explicit unresolved host/runtime gaps. Profile fields:
kind, source_origin, rest_path, runtime_version, qualification_ref, principal_ref,
report_id, workspace_id, execution_ref, max_bytes, max_polls. IDs are reviewed GUIDs;
bytes cap at 8 MiB and polls at 50. These limits are planned, not transport-enforced.

- `ssrs2017-rest-v2`: qualified HTTPS origin and actual REST base path; workspace
  null. Operations metadata and definition use GET `/Reports({Id})` and
  `/Reports({Id})/Content/$value`. Catalog GET `/Reports` additionally requires
  catalog_scope_reference. A returned catalog page cannot establish completeness.
- `powerbi-paginated-rest-v1`: fixed origin `https://api.powerbi.com`, path
  `/v1.0/myorg`, exact workspace/report GUID. Operations metadata, definition,
  export_submit, export_status and export_file use the documented report, Export,
  ExportTo and export-job paths. Export body allows only PDF/XLSX and
  paginatedReportConfiguration `{parameterValues:[{name,value}],locale}`. No
  identityBlob, credentials, arbitrary configuration or callbacks are accepted.

Export submission needs an execution_ref as retained review context, never as
permission. A future executor must externally authorize, bind status/file IDs to
actual submission receipts, reject redirects/token leakage, enforce byte/time/rate
budgets, record uncertainty before requests and avoid blind POST retries. No such
executor is provided here. Definition/download scope, report type, capacity and
actual server/API version remain to be qualified.

Official route references used for the bounded planners:
[SSRS REST overview](https://learn.microsoft.com/en-us/sql/reporting-services/developer/rest-api),
[report content](https://learn.microsoft.com/en-us/rest/api/power-bi-report/reports/get-report-content),
[Power BI report export](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/export-report-in-group),
[ExportTo](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/export-to-file-in-group),
[export status](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-export-to-file-status-in-group),
[export file](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-file-of-export-to-file-in-group).
These references do not qualify the current host or tenant.

## CLI

Run with `python3 -I -S -B skills/omni-artifact-translator/scripts/report_source_capture.py`:

- `import-local --request REQUEST --source-root SOURCE --directory PRIVATE_CAPTURE`
- `import-evidence --directory PRIVATE_CAPTURE --evidence RECORD --source-root SOURCE`
- `check --capture PRIVATE_CAPTURE_OR_ENVELOPE`
- `plan-operation --profile PROFILE --operation OPERATION --output PRIVATE_NEW_FILE`

Console output contains status/counts and the local output path, not raw source or
result rows. The CLI has no credential, network, execute, overwrite or send option.
