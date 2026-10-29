# ThoughtSpot source contract

The first-party readers use the existing Python standard library. They do not
install a TML/YAML decoder, vendor SDK, MCP client or chart runtime.

## Snapshot and original-file proof

`thoughtspot-api` accepts `thoughtspot-api-snapshot.v1`:

| Field | Meaning |
|---|---|
| `identity` | Exact `source_origin`, `org_id`, `product` (`cloud`/`software`), `version`, `principal_ref`, `chart_generation` (`classic`/`new`/`mixed`/`unknown`), `reference` |
| `root` | Selected `{kind: liveboard|answer, id}` |
| `objects` | `{kind,id,payload,evidence_ref}` records; original native JSON TML in `payload` |
| `inventory` | Independent `reference`, `completeness` and `items`; not inferred only from exported objects |
| `gaps` | Explicit unavailable or unresolved source facts |

Each inventory item has `key`, `kind`, `parent_key`, `native_id`, `definition_id`,
`disposition`, `reference`, `configuration` and `source_mapping`. A mapping is
`{object_kind,object_id,pointer}` into original object payload, or null for missing
or opaque obligations. Keys identify placements separately from reusable visual
definitions. Accepted dispositions are `include`, `manual_review`, `unsupported` and
`out_of_scope`; missing/denied details remain in configuration and referenced
evidence. The validator rejects cycles. Record embedded/native experience and
privilege observations in the root configuration and referenced qualification
evidence; do not extend the exact identity shape with guessed fields.

The native projection reconciles Liveboard visualizations, tabs/tiles, filters,
parameter overrides, views and logical dependencies with the independent list.
Native objects omitted from that list become explicit unresolved obligations.
Custom group metadata remains supplied evidence; no undocumented TML group shape
is invented. Native privacy cannot be relabeled public by the wrapper. A private
view requires an explicit selection reference before target use.

`thoughtspot-capture` accepts `thoughtspot-visual-capture.v1`. Its immutable
snapshot and `definition_fingerprint` are bound to retained source files. An
originals manifest (`thoughtspot-originals.v1`) contains `reference` and `records`:

```json
{
  "source_path": "board.json",
  "source_kind": "supplied_json",
  "source_pointer": "",
  "target_pointer": "/objects/0/payload",
  "mapping": "exact_json",
  "member_path": null,
  "reference": "Reviewed original transfer",
  "mcp_evidence": null
}
```

Every `/objects/N/payload` and `/inventory` requires an original mapping. Native
JSON objects must match the exact source pointer; encoded JSON TML uses the
explicit `native_json_tml` mapping, never an implicit YAML conversion. A ZIP member
requires a selected `member_path`; the original archive is retained, inspected
and bounded, without execution or broad extraction. YAML/opaque input can bind a
hash-bearing opaque placeholder or remain auxiliary evidence. It is not parsed
as a known native definition. MCP originals need their exact tool/schema/version,
call, Org, principal, timestamp and provenance references; they are not renamed
REST responses.

## Capture request and connected profile

`thoughtspot-visual-capture-request.v1` requires `capture_id`, `identity`, `root`,
`authorization_ref`, nullable `credential_ref`, `evidence_mode`, `route`,
`route_reference`, `target_surface`, `state`, `snapshot_path`, `originals_path`.
State has `filters`, `parameters`, `timezone`, `locale`, `principal`, `cache` and
`reference`. These are requested-state declarations, not observed execution.

Optional `api_profile`, `operations` and finite request/byte/time/retry budgets
select connected enrichment. `rest2-cloud-26.10.v1` requires Cloud `26.10.0.cl`.
Each operation is `{operation_id,kind,body,reference}`. The literal body, endpoint,
method, source origin, Org/principal declaration, imported source and package
runtime are pinned at host startup. The host also pins its latest observed
journal head; history cannot be truncated to repeat a dispatch. The imported inventory constrains all object selectors.

| Operation kind | Fixed REST v2 endpoint | Independent host grant |
|---|---|---|
| `metadata_search` | `/metadata/search` | Capture/metadata |
| `tml_export` | `/metadata/tml/export` | Capture/metadata |
| `liveboard_data` / `answer_data` | `/metadata/liveboard/data` / `/metadata/answer/data` | Query |
| `liveboard_render` / `answer_render` | `/report/liveboard` / `/report/answer` | Render |

All are POSTs to `/api/rest/2.0`; they are not a generic POST proxy. Metadata
selectors, schema flags, saved IDs, visual/tab selection, pagination and permitted
runtime overrides are validated by operation-specific allowlists. Query bodies
require finite offsets/page sizes. Liveboard data/render selectors use original `viz_guid` values, not local
visualization IDs; absent GUIDs require supplied evidence or a newly qualified
crosswalk. Renders exclude notes; PNG requires one explicit tab. The Answer renderer supports `SAVED` only. Existing filters,
custom SQL, arbitrary search text, source writes and unsaved/PINNED report paths
cannot be injected through an operation body.

Connected capture currently **enriches an imported scope**; it does not silently
replace its snapshot with a newer server response. Retain fresh response bytes,
review their exact crosswalk and create a new capture for changed definitions.
Version/privilege mismatch, authorization failures, redirects, malformed content,
budget exhaustion and interrupted requests remain explicit states. A new source
version or additional endpoint requires a reviewed profile implementation.

## Result and visual evidence

`thoughtspot-supplied-evidence.v1` imports selected attachments using the capture
helper. It supports bounded CSV/JSON, PNG/PDF and explicit ZIP members. Each entry
binds an `object_key`, format, source path/member, origin and result scope with
separately observed state, population, freshness and completeness records.
Expected contracts and observed evidence are different fields. Rendered PNG/PDF
bytes are never interpreted as complete numerical results.

The explicit parser profile selects columns/types and the retained raw structure
for CSV, JSON rows or COMPACT matrices. Supplied JSON matrix attachments require
`parser_profile` with `shape: compact_matrix`, `headers_pointer`, `rows_pointer`,
`header_id_key`, ordered `column_ids`, `headers`, typed `columns` and
`subtotal_policy: preserve`. Header IDs/order, rectangular scalar rows, numeric
precision and observed row count are validated; the same profile must be used
in normalization and comparison. `normalize_results` retains original hash,
profile and binding; workflow comparison recomputes the normalized output. A
numeric case binds `object_key`, optional `placement_key`, `attachment_id`,
`definition_fingerprint` and `state_sha256`. Wrong placement/state, private scope,
preview population, missing result semantics or stale evidence blocks a parity
pass. Large numeric values and decimal strings are preserved without float loss.

## Optional supplied Spotter MCP evidence

`thoughtspot_check_mcp` validates `thoughtspot-mcp-evidence.v1` locally. It retains
the requested/effective server version, actual schemas, exact arguments/responses,
schema and call hashes, Org/principal, references and explicit response pointers.
Only `search_objects`, `list_orgs`, `create_analysis_session`,
`send_session_message`, `get_session_updates` are classified. Session queries need
a recorded prior authorization reference and explicit data source. Updates must
belong to the recorded session, accumulate by message and reach boolean `is_done`.
Incomplete sessions stay incomplete. Known error envelopes, argument Org/source
drift, response-session mismatch and recognizable credential payloads reject. Locally counted message generations are not
REST `generation_number` values.

This checker performs no remote call and issues no authorization. An independently
configured MCP host must validate the vendor schemas and enforce any live grants.
`create_dashboard`, `switch_org`, unknown tools, implicit data sources and altered
schemas/Org are rejected. Search results do not replace TML, an independent source
inventory or observed result evidence. Do not automatically install a client.

## Handoff limits

There is no `thoughtspot-adapter` DMA producer. Use the existing scoped cowork
contract for identified backend gaps, preserving the selected reuse/semantic/
warehouse route. Current native baselines and separately bound App/dashboard
delivery evidence remain mandatory. A local pin proves continuity, not authentic
user identity, live access, native behavior or business acceptance.
