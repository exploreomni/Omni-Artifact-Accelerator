# MicroStrategy source contract

Readers use first-party Python and the existing standard library. Inputs are
untrusted evidence. Hashes establish local continuity, not source authenticity,
execution authority, effective access or tenant qualification.

## Snapshot and originals

`microstrategy-api-snapshot.v1` has exact top-level fields `schema_version`,
`identity`, `root`, `objects`, `inventory`, `gaps`.

| Field | Contract |
|---|---|
| identity | `source_origin`, `context_path`, `project_id`, `principal_ref`, `library_version`, `intelligence_server_version`, `model_generation` (`classic`/`mosaic`), `delivery_context` (`library`/`embedded`), `reference` |
| root | `{kind, id}`: dossier, report, document or cube; saved root ID is a native GUID |
| objects | Original `{kind, id, payload, evidence_ref}` definitions/responses; separately retained visualization responses use their native key |
| inventory | Independent `reference`, `completeness`, `items`; every expected occurrence stays visible even if capture failed |
| gaps | Explicit unresolved, inaccessible or unsupported evidence |

Inventory items have `key`, `kind`, `parent_key`, `native_id`, `definition_id`,
`disposition`, `reference`, `configuration`, `source_mapping`. The mapping has
`object_kind`, `object_id`, `pointer` (JSON Pointer). A placement references a
`visual_key` or `content_key`, not a display caption. Do not merge response shapes
or fabricate fields to fit the parser. Native `information.objectId`, object IDs,
chapter/page/visual keys and prompt keys keep their actual distinct meanings.

`microstrategy-originals.v1` contains `reference` and `records`, mapping every
`/objects/N/payload` and `/inventory` back to immutable original files. A record:

```json
{
  "source_path": "native-response.json",
  "source_kind": "supplied_json",
  "source_pointer": "",
  "target_pointer": "/objects/0/payload",
  "mapping": "exact_json",
  "member_path": null,
  "reference": "Reviewed original transfer",
  "mcp_evidence": null
}
```

Selected archive members use bounded intake; unknown code and binaries remain
opaque. Originals, actual customer names/results and captures stay outside the
repository. Separate definitions from results, render references and independent
inventory. Unknown fields are retained inert, never executed as SQL or scripts.

## Request and state

`microstrategy-visual-capture-request.v1` records `capture_id`, `identity`, `root`,
`authorization_ref`, nullable `credential_ref`, `evidence_mode`, `route`,
`route_reference`, `target_surface`, `state`, `snapshot_path`, `originals_path`.
The reader supplies finite default request/byte/attempt/time bounds; selected
budgets can reduce them. A reference is not a host grant.

State has `filters`, `parameters`, `timezone`, `locale`, `principal`, `cache`,
`reference`. Preserve stages, even when empty:

```json
{
  "filters": {"report": [], "chapter": [], "view": [], "metric_limit": []},
  "parameters": {"prompts": []},
  "timezone": "UTC", "locale": "en-US", "principal": "reviewed-principal",
  "cache": null, "reference": "Requested state; observation still required"
}
```

Prompt entries have `key`, `id`, `answer_mode`, `value`; duplicate IDs can be
valid, duplicate keys cannot. Explicit, default, empty, all, omitted and unresolved
states differ. Only the exact supported connected answer shapes may execute.
Unknown state does not become a default automatically. Source cache/expiry and
the user's target App cache/refresh policy are separate decisions.

A connected `api_profile` pins `id`, both deployment versions, `api_schema_path`,
`api_schema_sha256` and `reference`. The retained schema file is checked against
its hash. The profile is `strategy-rest-selected-instance-v1-20261028`; unknown
versions, Mosaic and unsupported source lifecycles remain supplied-evidence only.
Operations retain exact `operation_id`, `kind`, `object_key`, `instance_from`,
`body`, `reference`. Dependent instance IDs derive from successful owned creation,
never a user-edited arbitrary URL. Route/body/query/header/profile pins are checked
again before releasing session credentials. Source identity and definition changes
require a separately reviewed capture, not edits to retained history.

The connected definition operation reads selected root dossier/report definitions;
shared semantic dependencies use supplied original metadata. Connected PDF uses
the qualified dossier/document-instance family with `orientation: "AUTO"`; ordinary
report PDF remains supplied-only.

The host separately grants metadata, instance execution/state changes, render and
cleanup. No login, logout, source authoring, changesets, arbitrary SQL, schema
reload, ACL changes, subscriptions or publishing. Do not confuse modeling report
instances with analytics instances. Unsupported cleanup is a retained obligation;
it does not permit a guessed DELETE route. Never log out borrowed sessions.

## Captures and numerical evidence

`microstrategy-visual-capture.v1` holds immutable snapshot/original/schema pins,
request identity, append-only journal revisions, operation responses and supplied
attachments. Source execution and target write authority are different fields.
A metadata response never upgrades a capture to numerical or visual acceptance.

`microstrategy-supplied-evidence.v1` attaches explicit CSV/JSON/PNG/PDF evidence
with `attachment_id`, `object_key`, format/path/member, origin/result scope,
observed state, population, freshness, completeness and reference. Rendered files
are not executed or decoded using a new dependency. PDF responses may be binary
or base64 JSON and are bounded/signature checked; that does not certify PDF safety.

Numeric observed state retains `instance_id`, `result_definition_sha256`,
`definition_reference`, `execution_status`, `execution_reference`, and the actual
state. Repeated placements also require placement-state evidence. Normalize only
an explicit profile; raw values and text labels are distinct.

The JSON Data profile uses `shape: "microstrategy_json_data"` and explicit
`response_kind`, `response_pointer`, `definition_sha256`, `object_id`,
`instance_id`, headers/columns/mappings, `subtotal_policy: "reject"`,
`population_key`, `coverage_reference`. It recognizes the documented
`result.definition` and `result.data.paging/root` tree, attributes on rows and
metrics on columns. Metric `mi` binds to the definition; `rv` is raw and `fv` is
formatted. Int64 and decimal precision are retained. Original paths, element IDs,
forms and formatted values stay available.

A visualization response can lack status/instance fields; never invent them.
Require separate observed completed-instance evidence. Full single-response row
coverage requires offset zero, current=total, terminal paging, no partial flags
and matching leaves. `limit=-1` alone is insufficient. Multiple partial captures
remain partial; do not concatenate them into a fabricated vendor response.
Unsupported subtotal/hierarchy/consolidation/page-by/prompted-result variants need
another qualified profile. CSV uses an explicit separate column profile.

Normalization binding fields are `capture_content_hash`, `definition_fingerprint`,
`object_key`, `attachment_id`, `state_sha256`, `attachment_sha256`, `instance_id`,
`result_definition_sha256`. Shared comparison rebuilds normalization from raw
bytes and requires exact population/state/freshness and independent target evidence.
The neutral fixtures in `tests/test_microstrategy_visual.py` are executable shape
examples, not a live source or tenant acceptance record.

## Passive MCP evidence

`microstrategy-mcp-evidence.v1` retains `server`, `identity`, `tool_policy`,
`query_authorization_ref`, `calls`. Server has exact endpoint/effective version,
original `schemas` from tools/list and reference. Endpoints are
`/collaboration/mcp/agent` or `/collaboration/mcp/mosaic` on the pinned source.
No hardcoded guessed tool names or automatic connector setup.

Each reviewed tool policy pins its actual schema hash and metadata/query class.
Calls retain arguments/response, identity, selected project/model/cube/agent/state,
response pointers and references. Source-writing classifications are rejected.
These references record past decisions; they do not authorize future calls or
prove tool-schema authenticity. A qualified external host owns real connection,
full schema validation and query authority. MCP prose/results do not replace
layout, export or independently qualified numerical evidence.
