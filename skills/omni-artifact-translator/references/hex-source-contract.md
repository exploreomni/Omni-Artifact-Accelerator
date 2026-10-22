# Hex source and visual evidence contract

Implemented source-only intake, checked October 21, 2026. Local synthetic transport and maintained DMA composition tests qualify the code paths below; they do not establish live tenant behavior, native Omni execution, effective security, or customer acceptance.

## Supported intake and authority

`hex_capture.py` imports supplied schemaVersion 3 `.hex.yaml` exports and companion UTF-8 files, or captures a fixed, explicitly selected set of projects from a configured HTTPS origin. It preserves original bytes, `meta.projectId`, `meta.sourceVersionId`, cell UUIDs, code/configuration, layouts, shared filters, assets and `genAppFiles`. Files remain inert data. It never imports a customer Python module, installs an export's dependencies, runs a notebook/query, writes source objects, publishes, changes a project version, or creates an Omni document.

The structural reader is bounded safe YAML parsing, **not** validation against Hex's complete publisher schema or runtime semantics. It rejects aliases, anchors, explicit tags, duplicate keys, unsafe generated paths, credential-looking values and malformed native identity fields. Project/version IDs may be absent for offline intake; the definition hash and file locator remain the identity, and missing native IDs stay explicit gaps. API capture requires supplied project UUIDs. Companion binaries are not accepted as definitions; attach supported images/PDFs through evidence import.

Only these fixed API operations are implemented:

| Operation | Scope and interpretation |
| --- | --- |
| `GET /api/v1/projects/{projectId}` | Before/after metadata for each selected project. No workspace enumeration or implicit sharing expansion. |
| `POST /api/v1/projects/export` with `{projectId, version}` | Read-like export; explicit integer, `draft`, or `latest`. Retains response `{filename, content}` and UTF-8 YAML before and after images. No returned URL is fetched. |
| `GET /api/v1/projects/{projectId}/runs/{runId}` | Supplied existing run only. Requires `COMPLETED`, exact project/run/projectVersion and start/end fields before an API image. |
| `GET /api/v1/projects/{projectId}/runs/{runId}/cells/{staticId}/image` | Chart image of that completed published run. `includeTitle` is explicit; width/height are both absent or both 100–2000. Requires PNG response, exact project/run/static identity, decoded bytes and dimensions. |

`projectVersion` from run status and `sourceVersionId` from YAML are different fields. The request retains an explicit reviewed crosswalk; it does not infer equality. `staticId` is not substituted for YAML `cellId`. No fresh source run is implemented because exact-version execution freeze has not been qualified. The run can predate the capture; its state, inputs, result population and freshness remain unknown unless separately evidenced. Before/after export equality and metadata comparison detect observed drift, not an atomic source transaction.

These endpoints are documented in [Hex API reference](https://learn.hex.tech/docs/api-integrations/api/reference). Authentication is an operator-supplied bearer token. The wrapper does not discover credentials, authenticate the claimed principal, or infer token permission coverage. `principal_verification` remains `supplied_unverified`.

## Library and CLI

Use an explicitly trusted Python environment with reviewed PyYAML. No dependency is downloaded. Library entry points:

- `validate_request(value, require_service=False)` returns the exact normalized request.
- `import_local(request, source_root, directory, allow_source_read=False)` imports local files.
- `capture(request, directory, token=None, transport=None, resume=False, allow_source_read=False, now=None)` performs the fixed REST plan; injected transport is for qualified tests.
- `check_capture(path)` verifies the envelope and actual local evidence files.
- `import_evidence(capture_path, spec, source_root)` appends transferred files and independently supplied observations to the latest immutable journal.

Import/capture/evidence functions return `{status, output, capture}`, with an absolute output JSON path. CLI prints only `{status, output}` or a bounded rejection code:

```sh
python hex_capture.py import-local --request /absolute/request.json \
  --source-root /absolute/supplied --directory /absolute/private-capture --allow-source-read
python hex_capture.py check --capture /absolute/private-capture/capture-000001.json
python hex_capture.py capture --request /absolute/request.json \
  --directory /absolute/private-capture --allow-source-read --token-stdin
python hex_capture.py capture --request /absolute/request.json \
  --directory /absolute/private-capture --allow-source-read --token-stdin --resume
python hex_capture.py import-evidence --capture /absolute/private-capture/capture-000001.json \
  --spec /absolute/evidence-spec.json --source-root /absolute/transferred
```

`--token-stdin` accepts only a raw ASCII token, maximum 16,384 characters, with no newline. Do not put tokens in request files, argv, journals or examples. A host should bind the origin, request, capture directory, trusted executable, script hashes, token environment name and read grant at startup; child stdin is the credential channel. Capture never reads a token environment variable itself. Import/check do not need a token.

A new capture requires an empty private directory. Resumes pin the request and local runtime hashes. Every operation intent and request budget is durably written before I/O. An interrupted or uncertain request, including export POST, becomes unresolved and is never automatically repeated. A documented 429 with a bounded numeric Retry-After is retryable only after that time and within configured attempts; no generic 5xx replay. Each explicit resume is bounded; there is no background poll loop. HTTP redirects, proxy environment inheritance, unexpected media, oversized/incomplete bodies, secret echoes and unsafe paths fail closed. Default TLS verification stays enabled. Persisted receipts omit credential values.

Default bounds: 20 requests per invocation, 200 total requests, 64 MB cumulative response/evidence budget, 8 MB response bound, six-hour journal lifetime and three explicit attempts per operation. Operator requests may lower or raise these within hard caps. YAML is at most 2 MB/50,000 events/depth 28; supplied definitions total at most 4 MB/256 files; objects at most 5,000. PNG decoding is bounded and rejects invalid compression/chunks; interlaced PNG is unsupported by the shared reader.

## Request and capture shapes

`schema_version: "hex-visual-capture-request.v1"` requires:

- `capture_id`, exact `source_origin` (nullable offline), nullable `workspace_id`, `principal_ref`, `authorization_ref`.
- `evidence_mode`: `synthetic_fixture|manual_transfer|live_tenant`.
- `route`: `unselected|reuse_existing|omni_semantic_reconstruction|warehouse_first_refactor`, `route_reference`, and `target_surface: dashboard|app|both`. Supplied route is not backend authority.
- `exports[]`: `{project_id,version,expected_source_version_id,source_path}`. Paths end `.hex.yaml`; nullable IDs are permitted offline.
- `outputs[]`: `{output_id,project_id,source_version_id,cell_id,static_id,run_id,source_mode,expected_project_version,identity_reference}`. Native IDs are UUID or null; `source_mode` is `published|draft|offline`. Only fully identified published outputs with an existing run support API image capture.
- `images[]`: `{output_id,width,height,include_title}`.
- `state`: `{state_id,inputs,filters,timezone,locale,principal,data_time_policy}`. Typed `inputs` and `filters` are objects. Requested values are never treated as applied state.
- Optional `expected_manifest`: `{reference,completeness:"selected_scope"|"partial",objects:[{object_id,kind}]}`. This independent inventory is retained, never authenticated. Missing expected objects become unknown obligations.
- Optional bounds: `max_requests_per_invocation`, `max_total_requests`, `max_total_bytes`, `max_response_bytes`, `max_elapsed_seconds`, `max_attempts_per_operation`.

The named envelope is `hex-visual-capture.v1`. It contains the normalized request/hash, producer/runtime pins, definition files, projects, before/after metadata, run receipts, attachments, operation journal, budget, status/gaps and chain hashes. `source.definition_files[]` records `{path,source_path,sha256,bytes,content_utf8}`. `path` is packet-relative; `source_path` is the original logical export path. The fingerprint is canonical SHA-256 of sorted `{source_path,sha256,bytes}` rows. Canonical JSON uses sorted keys, compact separators, UTF-8, `ensure_ascii=False`, and disallows NaN. `content_hash` excludes only itself.

`complete` means the requested REST acquisition plan completed coherently; it does not close the source denominator, generated-interface behavior, state, security, numerical parity or native acceptance. Local supplied imports remain `partial`. `source_execution` and `target_write_authority` remain false, `native_validation` is `not_performed`, and `business_acceptance` is `not_assessed`.

## Transferred values and MCP images

Evidence import accepts exactly:

```json
{
  "schema_version": 1,
  "kind": "hex_evidence_import",
  "capture_content_hash": "CURRENT_CAPTURE_HASH",
  "attachments": [{
    "output_id": "SELECTED_OUTPUT",
    "path": "results.csv",
    "format": "csv",
    "provenance_reference": "REVIEWED_TRANSFER_RECEIPT",
    "result_completeness": {"status": "unknown", "reference": null, "flags": []}
  }],
  "state_observations": [],
  "render_state_observations": []
}
```

Formats: `csv`, `json`, `png`, `pdf`, or `mcp-image`. PDF validation is a bounded signature check and retained file pin, not document safety or content interpretation. CSV/JSON original bytes are retained without numeric reserialization. The completeness declaration is `complete|partial|unknown`; `complete` requires a reference and no flags. JSON error/truncation fields contradicting complete are rejected during file verification. CSV completeness cannot be inferred from reaching its final line.

`mcp-image` imports a transferred standard MCP CallToolResult JSON containing exactly one `type:image`, `mimeType:image/png`, Base64 data block and no `isError:true`. It preserves the original receipt and verifies decoded PNG pixels. It does not invoke a connector or fetch an image URL. The output must be explicitly `draft`; Hex documents `get_cell_image` as an already-executed draft chart. Draft run/session identity does not establish fresh execution. Hex MCP is **Beta**, available to Team/Enterprise; its tools and scope must be checked in the actual selected host. [Hex MCP server](https://learn.hex.tech/docs/api-integrations/mcp-server)

A value observation is stored in `source.state_observations`; render observations are separate in `source.render_state_observations`. Each retains `output_id`, `state_sha256`, `applied`, `reference`, `source_mode`, `project_id`, `source_version_id`, `cell_id`, `run_id`, typed inputs/filters, timezone/locale/principal, data watermark/cache reference and population. Numerical comparison additionally requires nonempty `execution_reference` and `output_freshness_reference`; these identify independently retained execution and output-age evidence, not requested state. Capture checks binding and identity; workflow checks full comparison context. A supplied reference is evidence attribution, not authentication. Numerical results do not require a screenshot, and a screenshot does not prove numeric completeness.

A comparison observation has this shape (replace template identities with the selected output; retain independently collected context):

```json
{
  "output_id": "SELECTED_OUTPUT",
  "state_sha256": "EXACT_REQUEST_STATE_HASH",
  "applied": true,
  "reference": "INDEPENDENT_STATE_RECEIPT",
  "source_mode": "published",
  "project_id": "PROJECT_UUID",
  "source_version_id": "SOURCE_VERSION_UUID",
  "cell_id": "CELL_UUID",
  "run_id": "EXISTING_RUN_UUID",
  "inputs": {"region": "West"},
  "filters": {},
  "timezone": "UTC",
  "locale": "en-US",
  "principal": "SOURCE_PERSONA_REFERENCE",
  "data_watermark": "OBSERVED_DATA_VERSION",
  "cache_reference": "OBSERVED_CACHE_CONTEXT",
  "population": "INDEPENDENT_COMPLETE_POPULATION_REFERENCE",
  "execution_reference": "INDEPENDENT_EXECUTION_RECEIPT",
  "output_freshness_reference": "INDEPENDENT_OUTPUT_FRESHNESS_RECEIPT"
}
```

If any context is unknown, retain that uncertainty and leave comparison inconclusive; do not copy the requested values into an observed-state declaration.

## Projection, DMA and comparison

`translate_artifact.py --format hex-capture` imports the capture; `--format hex-adapter --producer-revision c513474e87af9c2c31deebd2ae675c8602955203` imports DMA's actual schema-1 `source_adapter_result`, `source: hex`, `adapter_version: 1`. The generic adapter's exact `hex_yaml` original-export expression is the source of reconstruction. File/expression hashes, native project/cell IDs, locators and original properties must agree. Upstream candidate dependencies and gaps remain retained candidate evidence. No schema, engine or notebook executor is copied from DMA.

The legacy `dma-inventory` path still accepts schema-1 `hex_source_inventory` at that pin. It cannot recover absent generated-file bytes or establish a complete analyst denominator. It now identifies input/content/hidden dependencies as nonnumeric. Optional capture `source.semantic_inventory` and `source.adapter_result` remain distinct types with matching hashes, exact original file pins and `dma_producer_revision`; hash declarations do not authenticate the producer. The maintained producer is run only from a separately trusted checkout/environment, not from source customer directories. Existing code-fixture executors are not used.

`hex_visual.py` exports `validate_capture(value)` (pure), `verify_capture_files(value, capture_json.parent)` (actual bytes), `inspect_definitions(source.definition_files)`, `sha(value)`, and `normalize_results(raw, profile, binding)`. Verification must precede requirements/comparison; pure translation alone establishes only supplied structural evidence.

The structural inventory independently lists projects/components, all tabs, grid rows/columns, repeated placements, input/shared controls, source-only cells, content, action obligations, generated files and unknown fields. Source objects use immutable file-scoped locators such as `inventory.hex.yaml#/cells/0` and `inventory.hex.yaml#/appLayout/tabs/6/rows/0/columns/0/elements/0`; these are never described as vendor IDs. Original native IDs and definition hashes remain separate. Tab names and captions are not join keys. Unsupported cell types, unresolved component/version links, shared-filter/static-cell crosswalks and generated conditional screens remain gaps. Parsed source does not establish the reactive execution DAG, current input values, external dependencies or effective access.

`normalize_results` supports the existing typed CSV/JSON profile: schema 1; exact ordered headers; column ordinal/name/type/nullable/null tokens; explicit numeric decimal/group separator, percent and optional currency; explicit dates; subtotal policy `preserve`; UTF-8 CSV or JSON rows pointer. Exact binding is `{capture_content_hash,project_id,source_version_id,cell_id,output_id,state_sha256,attachment_sha256}`. Output kind is `hex_normalized_results` with original-byte hash, profile, binding and typed rows; exact decimals are preserved. Unknown native identity cannot produce a bound normalized numerical result. Full state and completeness evidence remains a separate workflow requirement.

Generated files are not rendered or executed to discover screens. An independently supplied interface inventory, observed input/action behavior, security validation, target App runtime tests and explicit per-surface disposition are still required. The source acquisition layer grants no DMA backend mutation authority and no Omni target write authority.
