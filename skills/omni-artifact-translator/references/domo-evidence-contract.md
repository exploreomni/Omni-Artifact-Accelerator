# Domo visual and app evidence contract

`oaa-domo-visual-capture.v1` is an Artifact Accelerator intake contract, **not a
Domo API response schema or a replacement for DomoMigrationAgent contracts**.
It binds original supplied files to an independent selected-scope inventory,
visual placement, application context and result state. It does not connect to
Domo, execute source code, authenticate provenance or grant migration acceptance.

Implementation: [domo_visual.py](../scripts/domo_visual.py).
Original neutral executable fixtures: [test_domo_evidence.py](../../../tests/test_domo_evidence.py).

## Compatibility and authority

The producer file retains one of the following emitted contracts unchanged:

- `omnikit.domo.evidence.v1`
- `omnikit.domo.source-evidence.v1`
- `domo-to-omni.dashboard-rebuild-plan.v1`
- `domo-to-omni.external-redesign-handoff.v1`

The declared producer revision is pinned to
`55eba0ca0690fbf14f39eddbc8a04c94a720c155` or the versioned source extension profile
`domo-source-operations@0.1.0`. The latter is a compatibility label, not a Git
revision; the host separately pins its runtime closure. File verification invokes the existing
passive parser with that revision; it never imports the upstream runtime. This
checks supplied structure and byte consistency, **not** provenance, registry
registration, effective permissions or the source store's readiness rules.
Changing the pin requires a separately reviewed compatibility update.

The new capture profile is `oaa-domo-evidence@1`. It must never be passed as the
producer revision for an old emitted contract. Existing contracts retain their
existing validation behavior.

All captures require `target_write_authority: false`,
`native_validation: "not_performed"`, and `business_acceptance: "not_assessed"`.
Nested self-asserted build, write, publication and acceptance authority is
rejected. Actual A–F decisions, source registry acceptance and privileged target
execution remain outside this supplied evidence contract.

## Capture envelope

| Field | Required meaning |
|---|---|
| `schema_version` | `oaa-domo-visual-capture.v1` |
| `content_hash` | SHA-256 of canonical JSON excluding `content_hash` |
| `status` | `complete`, `partial`, or `blocked`; never business acceptance |
| `evidence_mode` | `synthetic_fixture` or `supplied_capture`; neither claims live validation |
| `identity` | Exact `source_origin`, `tenant_ref`, `principal_ref`; no credentials |
| `selection` | `scope_id`, nullable `version`, and evidence `reference` |
| `state` | `filters`, `variables`, `timezone`, `locale`, `cache`, `principal` |
| `producer` | Original `contract_version`, declared `revision`, pinned `file` |
| `inventory` | Independent reference, completeness, expected counts and item denominator |
| `artifacts` | Original bounded files and their state, scope and execution bindings |
| `app_handoff` | Required for selected apps; assignment-only responsibilities |
| `gaps` | Explicit retained unresolved evidence gaps |

`source_origin` must be an HTTPS origin without credentials, path, query or
fragment. A safe origin is identification only, not permission to send it data.
Use non-secret references for the actual principal and source requests.

State keys are all explicit. `null` means unknown, not empty filters or default
settings. Only an observed empty object establishes an empty control context.
Capture the effective filter precedence inside `filters` and actual variable
values inside `variables`. Retain formulas, aggregate definitions, sorting,
limits, totals, currencies and other source semantics in the original definition.
Source and target cache policies are separately owned; matching their cache
implementation is not required, but source freshness must be known.

## Independent inventory and placement identities

Inventory completeness is `selected_scope_declared` or `partial`. The former
requires exact `expected_counts` for all enumerated kinds. It remains a supplied
declaration, not a claim that the reader queried Domo independently. A partial
denominator stays a gap even if every supplied result matches.

Supported item kinds are `page`, `app`, `app_page`, `component`, `card`, `query`,
`placement`, `dataset`, `asset`, and `operation`. Each item requires:

- Unique `key`, original `native_id`, `kind`, nullable `parent_key`, and reference.
- `disposition`: `include`, `out_of_scope`, `deferred`, or `unknown`.
- `configuration`, preserving source information without executing it.
- `required_evidence_kinds`; included objects cannot declare an empty requirement.
- Applicable `app_id`, `page_id`, `card_id`, `query_id`, and `placement_id`.
- When a definition is available: `source_mapping` with `artifact_id` and JSON
  `pointer`, plus `configuration.definition_sha256` for that original object.

`source_mapping.artifact_id` can be `producer` or a definition attachment. The
reader resolves the pointer against verified original JSON and recomputes the
definition hash. Missing definitions remain gaps rather than invented content.

Every repeated Card placement has a separate item and original placement ID.
Its `configuration.target_key` points to the Card or app component. Page identity
must agree with its ancestors. A Card ID is never a placement denominator.

A query item has its original `query_id` and
`configuration.result_owner_key`, pointing to a Card, component, or DataSet.
For a Card query, retain `card_id`. A captured result must match exactly one query
and its source owner. Numeric comparisons use the Card/component or its particular
placement, not a detached query asset.

App records preserve `configuration.app_family`: `app_studio`, `pro_code`,
`brick`, or `unknown`, plus `configuration.version`. Asset records preserve
`app_id` and their own version. Unknown versions remain explicit gaps; an asset
revision and an app release are not assumed equivalent.

## Files and attachments

Every file pin is `{path, sha256, bytes}`. Paths are relative, case-collision-safe,
bounded and traversed without following links. A maximum of 512 pinned files,
8 MiB per file and 32 MiB aggregate applies. Original files are never rewritten.

Every attachment includes `artifact_id`, `kind`, `source_channel`, `format`,
`file`, `object_keys`, `selection`, `state_sha256`, `principal_ref`, `captured_at`
and `reference`. Supported kinds:

- `definition`, `request`, `response`, `results`
- `page_render`, `component_render`
- `source_asset`, `mcp_capture`

Channels distinguish `platform_api`, `product_api`, `app_framework_api`,
`passive_mcp`, `native_export`, `supplied`, and `unknown`. A channel declaration
does not establish that an API operation is documented or implemented.

Source JSON is duplicate-key checked, bounded and inspected for credentials.
Text, HTML, CSS, JavaScript and SQL remain UTF-8 inert source evidence. Archives,
compressed packages and `.blend` containers are rejected; do not unpack them
through this reader or quietly acquire a decoder. PDF/PPT are not supported by
this profile and require a separately reviewed capture route.

PNG verification checks structural integrity, CRCs, bounded decompression and
dimensions using the existing original helper. JPEG/WebP are size/signature
checked and screened for obvious plaintext credentials; decoding, metadata
sanitization and visual quality remain unqualified. Do not serve imported assets
to users merely because their hashes verify. Rendering attachments require their
viewport width, height and device scale plus a `theme_ref`.

MCP captures retain `server_ref`, `tool_name`, `tool_schema_ref`, and `session_ref`.
They are passive evidence; they do not confer source execution authority.

## Results and numerical comparison

Result attachments require a single object key, original `query_id`, explicit
JSON/CSV parser profile, completeness, population and freshness evidence.
Completeness retains status, row count, flags and reference. Freshness retains
observation time, data watermark and reference. A missing or unknown field cannot
be upgraded from the fact that supplied rows happen to match.

`observed_state` records:

- Actual state, selection, definition hash, query ID, and placement ID if applicable.
- Execution status, `full_data`/`preview`/`sample`/`unknown` scope, and row limit.
- Execution kind: `card`, `app_component`, `dataset`, or `unknown`.
- Original request/response attachment IDs and an evidence reference.

Request/response attachments must bind the same query, object and state. The
response pin must match the exact result bytes. Use the parser profile to select
the rows from the original response; do not substitute reconstructed rows.
Separate pinned copies can carry the two roles without changing the original
bytes. Missing originals are retained as gaps.

`normalize_results(raw, profile, binding)` uses the existing bounded exact-decimal
normalizer. It rejects error tokens before null conversion. It does not evaluate
Beast Modes, compile SQL, authenticate execution or calculate acceptance.

The result and comparison case binding has exactly these six fields:

```json
{
  "capture_content_hash": "<sha256>",
  "definition_fingerprint": "<sha256>",
  "object_key": "<independent-inventory-key>",
  "attachment_id": "<result-artifact-id>",
  "state_sha256": "<sha256>",
  "attachment_sha256": "<sha256>"
}
```

`result_binding(capture, artifact)` produces that binding. Numeric source format
is `domo-normalized`; retain the raw file pin alongside normalized results.
`case_binding` checks exact source identity, scope, state, definition and result
bytes. `comparison_gaps` additionally checks population, complete column mapping,
currency, freshness, original execution evidence and observed Card/component
state. A DataSet result cannot prove Card parity. A different placement or variable
state invalidates the comparison even when the arithmetic is identical.

An empty gap list is **supplied-evidence consistency**, never live tenant
acceptance. Effective access, rendered fidelity and source registry acceptance
remain independent lanes.

## App behavior and assignment contract

Each app component must explicitly disposition all 16 facets:

`query`, `visual`, `formatting`, `layout`, `responsive`, `filters`, `variables`,
`drill`, `navigation`, `security`, `freshness`, `export`, `actions`, `motion`,
`accessibility`, and `state`.

Each facet has `disposition`, `owner_ref`, nonempty `evidence_refs`, and nonempty
`acceptance_refs`. Dispositions are `preserved`, `adapted`, `deferred`,
`unsupported`, `unverified`, or `not_applicable`. An adaptation also requires a
`decision_ref`. These references are declarations, not authenticated approvals.
Deferred, unsupported and unverified facets remain unresolved gaps.

`oaa-domo-app-handoff.v1` is a separate **assignment-only** contract. It requires
owner, handoff and evidence references, exact selected `app_keys`, `mode`,
`side_effect_kinds` and `operations`. All four authority flags are false:
`build_authority`, `target_write_authority`, `publish_authority`,
`acceptance_authority`.

A genuinely read-only app uses `mode: "read_only"` with empty side-effect and
operation arrays. No fabricated side effect is required. The selected inventory
must also contain no operational items hidden from that handoff.

An operational app uses `mode: "operational"`. Its operation list must match the
independent operation inventory exactly. Every operation binds its component,
side-effect kind, owner, source evidence, target, authorization requirement, retry
policy, failure behavior and acceptance case. `execution_authorized` is false.
Unresolved target/service requirements can be explicit references; they are not
an authorization or an automatic reconstruction of source writes.

## Python integration surface

- `validate_capture(value)` — structural/context validation; returns the capture.
- `verify_capture_files(value, folder)` — reads pinned files, returns consistency
  evidence and remaining gaps; performs no writes or network requests.
- `project_assets(value)` — generic asset descriptors with independent scopes;
  original placement/component identities are retained.
- `evidence_gaps(value)` — manifest-only missing/unresolved evidence.
- `definition_fingerprint(value)` and `result_binding(value, artifact)` — exact
  source and comparison identities.
- `normalize_results(raw, profile, binding)` — exact-decimal normalization.
- `case_binding(asset, case, capture)` and
  `comparison_gaps(capture, asset, case, source, target, normalized, columns)` —
  source-specific comparison checks.
- `validate_app_handoff(value, inventory=None)` — assignment-only app obligations;
  pass the inventory when qualifying captured scope.

Run focused original fixtures with the existing standard-library runtime:

```sh
python3 -I -S -B tests/test_domo_evidence.py
```

These fixtures establish local contract behavior only. Live Domo capture, native
Omni rendering, application service replacements and host permission enforcement
must be qualified separately.
