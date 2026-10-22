# Looker source capture contract

Reviewed October 21, 2026 against official API 4.0 documentation, currently labeled 4.0.26.20. The implementation is locally tested using synthetic transports. No live instance, warehouse workload, rendering fidelity, effective access or business acceptance has been qualified by those tests.

## Entry points and runtime

`scripts/looker_capture.py` uses only the standard library and the existing passive `powerbi_capture_files.py` boundary for private file IO, bounded JSON and PNG checks. It does not invoke another platform's capture engine. A host must pin **both** runtime files; there is no Looker SDK, credential discovery, login, package installation or target client.

```python
validate_request(value, *, require_service=False)
capture(request, directory, *, token=None, transport=None, resume=False,
        allow_source_read=False, allow_source_query=False, now=None)
import_api(request, payload_bytes, directory, *, allow_source_read=False)
import_local(request, source_root, directory, *, allow_source_read=False)
check_capture(capture_path)
```

Capture and imports return `{status, output, capture}`. `output` is the absolute immutable envelope path. `check_capture` returns the checked envelope, re-reading original files. It does not authenticate the producer or grant readiness. CLI output has only `status` and `output`.

```sh
python3 looker_capture.py import-api --request /private/run/request.json \
  --response /private/run/dashboard.json --directory /private/run/capture \
  --allow-source-read
python3 looker_capture.py import-local --request /private/run/request.json \
  --source-root /private/run/supplied --directory /private/run/capture \
  --allow-source-read
python3 looker_capture.py capture --request /private/run/request.json \
  --directory /private/run/capture --allow-source-read --allow-source-query --token-stdin
python3 looker_capture.py check --capture /private/run/capture/capture-000001.json
```

Use the actual returned filename. The approved host injects the existing access token as raw ASCII stdin, at most 16,384 bytes, without a newline. Never put it in request files, shell arguments, logs or chat. `--allow-source-query` is required for query execution **and PNG rendering**, because rendering can execute dashboard queries. Metadata reads and offline imports require only `--allow-source-read`. Resume uses `--resume` with the same request, runtime and directory.

Looker's documented direct API scheme is `Authorization: token <access token>`; API credentials act as their Looker user. The wrapper consumes a token, never the client ID/secret, and never refreshes it. [Authentication](https://docs.cloud.google.com/looker/docs/api-auth). Connected capture reads only `GET /api/4.0/user?fields=id`, verifies optional `expected_user_id`, and requires the same observed ID across resumed invocations. This establishes the API principal observed by that call, not restricted-user or row-level parity. Full user/credential records are deliberately not requested. [Current user](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/User/me).

## Request v1

`looker-visual-capture-request.v1` contains:

| Field | Meaning |
| --- | --- |
| `capture_id` | Local operation ID, separate from vendor identity |
| `source_instance` | Exact approved HTTPS origin, port 443 or 19999; null is allowed offline |
| `api_version` | Exactly `4.0` |
| `dashboard_id` | Opaque native ID, including LookML `model::dashboard` IDs; null is allowed offline |
| `principal_ref`, `authorization_ref` | Supplied review references |
| `expected_user_id` | Optional actual Looker user ID; default null |
| `source_revision` | Optional supplied revision reference; no revision is invented |
| `evidence_mode` | `synthetic_fixture`, `live_tenant`, or `manual_transfer` |
| `route`, `route_reference` | `unselected`, `reuse_existing`, `omni_semantic_reconstruction`, or `warehouse_first_refactor`; selected routes require a reference |
| `target_surface` | `dashboard`, `app`, or `both`; this grants no target authority |
| `views` | Selected `{element_id,tab_id,layout_id}` rows; nullable component IDs retain unresolved mappings |
| `state` | `{state_id,filters,parameters,timezone,locale,principal,data_time_policy}`; requested context only |
| `renders` | `{render_id,tab_ids,width,height,dashboard_style,theme}`; style `tiled` or `single_column`, theme nullable |
| `queries` | `{binding_id,element_id,query_id,inline_query,context_reference,options}` plus optional `source_query_id` |
| `expected_manifest` | `{reference,completeness:selected_dashboard\|partial,objects:[{object_id,kind}]}`; defaults to partial and empty |

Exactly one of `query_id` and `inline_query` is supplied. Saved queries must resolve through that element's exact Look/query/merge dependency closure. A reviewed inline query may change the source query; `source_query_id` identifies its baseline when available and must belong to the element. Its default is the saved query ID, otherwise null. The attachment retains the baseline hash, exact effective definition, changed supplied fields and review reference. A missing baseline remains visible; context references are declarations, not authenticated approvals.

Query options are exactly `{limit,cache,cache_only,force_production,server_table_calcs}`. Limit is 1–100,000. The helper forces `apply_formatting:false`, `apply_vis:false`, `rebuild_pdts:false`; arbitrary options, unlimited results and lifecycle flags are rejected. Inline bodies accept the bounded documented model/Explore/field/filter/pivot/sort/totals/calculation/timezone subset; `filter_config` must be absent or null. Unsupported fields stop explicitly. No query is generated from a dashboard screenshot or filter name. The operator reviews source listener semantics and query context before execution.

Only `state.filters` is encoded into dashboard render filters. `parameters`, timezone, locale and principal remain retained context, not impersonation or a claim that the render API applied those settings. Query context is separately specified in the reviewed query. The renderer accepts selected tab IDs but the wrapper does not invent a tab-to-tile crosswalk or convert a dashboard image into a tile image.

Default bounds: 40 requests per invocation; 500 total requests; 64,000,000 cumulative response bytes; 21,600 seconds elapsed capture age; five attempts/polls per operation; 8,000,000 bytes per response; 100 dependency objects. There are at most 200 selected view rows, 20 renders and 100 query bindings. Embedded source metadata and repeated effective-query payloads each have a 4,000,000-byte cap so diagnostics remain readable within the journal boundary. Supplied files additionally have finite file-count, per-file and aggregate limits. Wider work must be explicitly scoped into separate dependency-complete captures.

## Fixed API operations

The source instance comes from operator configuration. Source links, HTML, visualization code and returned URLs never choose a destination. TLS verification remains enabled, redirects are refused, environment proxy discovery is disabled, and no arbitrary server `Location` is followed. Opaque IDs are validated and URL-encoded as one path component.

| Operation | Boundary |
| --- | --- |
| `GET /dashboards/{id}` | Full received dashboard retained without a field projection; missing element/filter/layout properties remain gaps |
| `GET /looks/{id}`, `/queries/{id}`, `/merge_queries/{id}` | Only explicit dependency IDs discovered in the selected dashboard and its dependencies; finite closure, no title joins |
| `POST /render_tasks/dashboards/{id}/png` | One reviewed dashboard/tab request with dimensions, filters, style and optional theme |
| `GET /render_tasks/{id}` and `/results` | Only a task ID returned by the retained submission; PNG validation before attachment |
| `GET /queries/{id}/run/json_bi` | Reviewed saved query associated with its selected element |
| `POST /queries/run/json_bi` | Reviewed inline query, with original body/options retained |

All paths have `/api/4.0` prefix. Dashboard and dependency responses preserve native IDs, formulas, result-maker strings and unknown fields. `merge_result_id` is a merge-query reference; a result-maker's own `id` is **not** substituted. Source-query IDs from merge metadata are followed. Missing or inaccessible dependencies stop the connected acquisition with retained diagnostic operations. Drill/action/URL links are not followed, and semantic models, imported projects, schedules, alerts and access-policy inventories are outside this closure. [Dashboard](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Dashboard/dashboard), [Look](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Look/look), [Query](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Query/query), [Merge Query](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Query/merge_query).

The documented render statuses are `enqueued_for_query`, `querying`, `enqueued_for_render`, `rendering`, `success` and `failure`. Pending status returns control after one poll; the caller resumes explicitly. Unknown statuses stop. A result endpoint's empty HTTP 202 response requires a bounded `Retry-After`; 404 remains ambiguous among inaccessible, missing and expired results, and never causes another submission. Theme selection can change rendering to the embedded dashboard version, so it remains part of the request fingerprint. [Create render](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/RenderTask/create_dashboard_render_task), [Task status](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/RenderTask/render_task), [Task results](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/RenderTask/render_task_results).

`json_bi` is the preferred structured result format. Query options explicitly retain limits, cache policy, production preference and server calculations. `force_production:false` does not establish development mode. No explicit PDT rebuild, workspace mutation, source action or merge-result execution is implemented; normal query workload/cache behavior remains vendor-controlled. [Run Query](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Query/run_query), [Run Inline Query](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Query/run_inline_query).

Query attachments preserve the **exact response bytes**, never a floating-point reserialization. Error/truncation signals and a reached requested row limit produce partial evidence; otherwise completeness remains unknown. The documented `JsonBi` type includes metadata and string rows, and metadata can report `columns_truncated`; a normalization profile must explicitly describe the received row form. A synthetic object-cell fixture is not native schema certification. [JsonBi](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/types/JsonBi), [JsonBiMetadata](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/types/JsonBiMetadata).

## Supplied evidence and envelope

`import-api` accepts bytes for the raw Dashboard API object or the existing schema-1 `looker_dashboard_export` wrapper. It preserves the entire original file and wrapper, without claiming dependency acquisition. `import-local` preserves supplied JSON, LookML/dashboard/YAML text and PNG/JPG/PDF files. It never executes LookML, Liquid, custom visualization code or a source repository. JSON keys/depth/size, UTF-8, path aliases, symlinks and recognized credential fields are checked. PNGs receive chunk/CRC/decompression/row validation; JPG/PDF receive signature checks only and remain unrendered reference bytes. Binary files are never executed. Unrecognized files and multiple API dashboard roots reject intake. Supplied LookML receives its bounded structural interpretation from the separate translator, not this capture layer.

`looker-visual-capture.v1` contains the normalized request/hash, producer file hashes, source identity, raw dashboard pin plus untouched parsed `dashboard_export`, canonical payload hash, dependency payloads/pins, supplied-file paths and content, request/result/render attachments, jobs, operation intents, budgets and a chained journal. Source-file names remain distinct from packet file names. When no service identity exists, the namespace is `definition:<fingerprint>`; no instance/dashboard ID is invented.

`definition_fingerprint` is canonical SHA-256 of sorted `{kind,id,sha256}` records: dashboard ID and original file hash, dependency kind/ID/file hash, and supplied-file original path/hash. Sorting is by `(kind,id)`. `query_fingerprint` is canonical SHA-256 of `query_request(row)`, the exact `{method,path,body}` with sorted encoded query options. The effective query and baseline hashes are separate from that HTTP-request fingerprint. All canonical hashes use sorted compact JSON, UTF-8, `ensure_ascii:false` and no NaN.

Every render attachment pins the request/state, dashboard, tab selection, task ID and render request. Every result attachment pins the request/state, element, query binding, HTTP request, effective query and completeness declaration. Renders cover dashboard/tab appearance only; a tile crop needs separate provenance. Automatic observed state stays unknown. A stable API principal and unchanged source definition do not prove the effective filters, relative-date anchor, cache/data watermark, complete population or restricted-user behavior of a particular render.

An immutable operation intent is written before each call. Uncertain submissions, interrupted intents and unexpected responses stop automatic replay. Known throttles can resume after their delay within budgets. Request, runtime, principal and retained-byte changes are checked. The capture brackets dashboard and dependency bytes before/after; differences block completion. Exact raw-response comparison is conservative and may stop on volatile metadata changes. It cannot detect a transient change that reverted or create an atomic data snapshot.

`complete` means requested acquisition finished and the retained configuration bracket matched. `partial` retains pending work, incomplete projection or query flags. `blocked` retains an unresolved contract, failure or coherence issue. None grants target writes, native validation, deployment or business acceptance. The invariant fields remain `target_write_authority:false`, `native_validation:not_performed`, `business_acceptance:not_assessed`. Hashes detect changed evidence; they do not authenticate a maliciously rewritten packet or an approval reference.

## Translation and numerical evidence

The companion `looker_visual.py` provides `validate_capture(value)`, `verify_capture_files(value, capture_json.parent)` and `normalize_results(raw_bytes, profile, binding)`. Validation checks declared consistency; file verification additionally checks the confined original bytes. Neither authenticates a supplied packet's origin.

A schema-1 normalization profile selects `format:json_bi|csv`, `rows_pointer`, `row_encoding:object|json_string`, `cell_mode:scalar|value_object`, exact ordered `headers`, `subtotal_policy:preserve` and ordered `columns`. Each column records `ordinal`, `name`, `type`, `nullable` and `null_tokens`; numeric columns also declare decimal/group separators, percentage treatment and optional currency context. Normalization is limited to flat rows. Pivot, subtotal and total reconciliation remains unresolved and cannot disappear through a flat-row comparison.

The normalized result binding is exactly `{capture_content_hash,element_id,binding_id,query_fingerprint,state_sha256,attachment_sha256}`. Requirements additionally retain `placement_id`, `layout_id` and `tab_id`. Independent `value_state_observation` and `render_state_observation` evidence requires an applied-state assertion and reference, exact element/binding/query/state identity, `effective_query_sha256`, `query_state_reference`, filters, parameters, locale, timezone, principal, data watermark, cache reference and execution mode. These are evidence assertions requiring review; the acquisition wrapper does not manufacture them from requested settings. Original result bytes, explicit completeness evidence and compatible source/target population remain necessary for a numerical comparison.

## Qualification

`tests/test_looker_capture.py` runs the actual producer against authored dashboard, Look, query, merge, render and result transport fixtures. It covers original bytes and IDs, multiple placements, content, dependency closure, reviewed inline changes, precision, private files, finite requests/bytes/polls, pending results, 404s, unknown statuses, uncertain POSTs, source/principal drift, invalid media, redirects and credentials. Its CLI tests use real subprocess intake/check with no tenant. Use separate native visual, numerical, interaction, accessibility and restricted-persona evidence for acceptance.
