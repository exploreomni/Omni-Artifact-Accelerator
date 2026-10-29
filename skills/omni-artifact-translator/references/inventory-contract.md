# Offline inventory contract

The JSON/API projection helper is a Python 3 standard-library program. Supplied Hex and LookML dashboard YAML additionally need an already approved PyYAML runtime; the helper does not install it. Resolve `scripts/translate_artifact.py` relative to this skill's folder. No credentials, vendor SDK or network access is needed.

```sh
python3 scripts/translate_artifact.py /absolute/private/source.json \
  --format looker-api --output /absolute/private/new/source-inventory.json
```

The parent output directory must already exist. Choose an output outside the preserved source snapshot. Existing outputs are rejected; provide a fresh output name for a changed snapshot. Files are created with mode `0600`. Symlinks, including ancestor symlinks, are rejected, so use canonical absolute paths (for example `/private/tmp`, not the `/tmp` symlink on macOS). The CLI reads only its one input file. Paths and URLs inside the input are never dereferenced.

Limits: 8 MiB input, JSON depth 32, 150,000 JSON nodes, 5,000 projected assets, and 48 MiB output. Inputs with duplicate JSON keys, nonfinite numbers, conflicting identities or malformed declared collections fail closed. Split large source scopes coherently outside the parser; do not truncate inputs and claim completeness. Console output contains counts only. The saved JSON retains source expressions and potentially confidential metadata; use approved storage and disclosure boundaries, not a shared public artifact directory.

Exit `0` means a bounded projection was saved **with review gaps**. Exit `1` means rejection; no successful projection was established. Neither exit code is a native validation or migration success flag. Projection version 1.1.0 adds source-agent bridges without changing the output schema version.

## Supported input profiles

### `looker-api`

A single Dashboard API object with `id` and `dashboard_elements: [...]`. `dashboard_filters` and `dashboard_layouts` may be supplied; missing collections create gaps. Nested query/Look definitions and layout components are retained. Alternatively:

```json
{
  "schema_version": 1,
  "kind": "looker_dashboard_export",
  "api_version": "4.0",
  "dashboard": {"id": "d-1", "dashboard_elements": []},
  "queries": [],
  "looks": []
}
```

This wrapper follows the inspected DMA export convention, not an official Looker export format. Query/Look IDs are matched only against supplied embedded definitions; conflicting definitions reject the import. Merged-result and SQL-query dependencies remain unresolved. Missing native IDs become explicit gaps and never invented native IDs. Dashboard assets are not relabeled as pages. Unknown visual types and all HTML/dynamic expressions are preserved as data without target translation.

The [Looker Get Dashboard API reference](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Dashboard/dashboard), checked 2026-10-21, documents dashboard elements, filters, layouts and an optional requested-fields parameter. A selected-fields response may omit behavior. The adapter does not verify the request, API provenance, export completeness or effective access. No chart, formula, responsive-layout or drill parity is claimed.

### `looker-capture`, `looker-canonical` and `looker-adapter`

`looker-capture` accepts the maintained `looker-visual-capture.v1` envelope. It validates definition, dependency and attachment identities/hashes before independently enumerating visuals, content, controls, tabs, layouts, repeated placements and actions. Early partial captures retain expected objects as missing obligations. Supplied dashboard YAML is bounded definition evidence; Liquid, inheritance and effective-access behavior remain unresolved. Original bytes are retained, and capture checks/requirements additionally re-read local files. See the [source contract](looker-source-contract.md).

`looker-canonical` accepts the actual DMA `canonical_dashboard` producer; `looker-adapter` accepts the actual generic `source_adapter_result`. Both require `--producer-revision c513474e87af9c2c31deebd2ae675c8602955203`. They retain upstream payloads and independently reconcile the original visual denominator. Generic unsupported dashboard files become explicit unknown-file obligations. A caller-supplied revision is not authentication. The legacy `looker-api` format remains supported.

Follow the [Looker workflow](../../omni-artifact-accelerator/references/looker-visual-run.md) for source capture, frozen scope, actual DMA exchange and separate dashboard/App evidence. Parsing does not confer native conversion or completion.

### `dma-inventory`

```sh
python3 scripts/translate_artifact.py /absolute/private/dma-inventory.json \
  --format dma-inventory \
  --producer-revision c513474e87af9c2c31deebd2ae675c8602955203 \
  --output /absolute/private/new/source-inventory.json
```

Accepted `schema_version: 1` inventory kinds and projected collections:

| Kind | Projected analyst assets | Boundaries |
|---|---|---|
| `tableau_source_inventory` | workbooks, dashboards, worksheets, parameters | Zones, shelves, filters and table-calculation evidence retained; actions, stories, live permissions and rendering still require source review. |
| `powerbi_source_inventory` | projects, pages, visuals, filters | Pinned enhanced PBIR inventory; the inspected extractor profiles `tableEx`, not every chart. PBIX, bookmarks, field parameters and hidden interactions are not added by this importer. |
| `hex_source_inventory` | projects, cells | App layout, data-app cell IDs, cell types/configuration and chart specifications retained; reactive execution, components, app inputs and access remain unverified. |

All require their `assets` file-hash inventory and `gaps` array. This is a projection of a **supplied report**; the CLI does not import or execute the DMA checkout. The producer SHA is a caller declaration, not authenticated provenance. It is pinned to the inspected schema; changing it requires checking the source and updating tests. To establish source parity, separately rerun DMA on the approved source snapshot and compare exact source hashes, parser component fingerprints and results. The analyst package must not treat this import as that re-verification.

Original DMA IDs, scoped IDs and native IDs are distinguished. Tableau worksheet/dashboard names are explicitly `native_name` identities. A generated file-based identifier is not upgraded to a native source ID. Upstream file hashes, gaps, metadata, formulas, graph edges and unprojected fields remain in the original `upstream_payload`; nothing there becomes a target model automatically.

### `powerbi-adapter` and `powerbi-capture`

`powerbi-adapter` accepts DMA's actual schema-1 Power BI `source_adapter_result`, with the same explicit inspected `--producer-revision` as above. It checks source-file/evidence identities and retains objects, expressions, dependencies and gaps. This is a different contract from legacy `powerbi_source_inventory`; do not change its `kind` to pass the legacy importer. Generated adapter IDs are not automatically service IDs. The runner's separate untyped `inventory.json` is neither accepted contract.

`powerbi-capture` accepts `powerbi-visual-capture.v1` from the source wrapper or supplied definition intake. It enumerates PBIR objects independently of model availability or semantic-parser success, retains all original files and distinguishes query visuals from non-query content. Workspace/report IDs can be null for a local definition-only source; its namespace uses the definition fingerprint. The projection checks embedded hashes and identities; requirements and local capture-check/import tools additionally verify actual retained files.

```sh
python3 scripts/translate_artifact.py /absolute/private/powerbi-capture/capture-000001.json \
  --format powerbi-capture --output /absolute/private/new/source-inventory.json
```

Read the [Power BI source contract](powerbi-source-contract.md) for exact request/envelope, file limits, normalization and observed-state boundaries. Supplied manifests, state references and successful model queries do not establish complete report coverage, applied interaction state, effective RLS/OLS or native parity. Keep the whole evidence directory and the source gaps.

### `tableau-capture`

Accepts `tableau-visual-capture.v1` from the separately authorized source wrapper or retained official-MCP intake. The parser checks its structure, definition bytes/hash and source identities; it does not fetch local paths or remote URLs. The downstream workflow and MCP capture-check/import tools verify retained attachment files against their hashes. Keep the full source directory, not only the envelope JSON.

The [Tableau source contract](tableau-source-contract.md) defines explicit view/XML reconciliation, independently supplied expected objects, separate worksheet and placement identities, nested/device layouts, controls, parameters, content, actions and unknown-object preservation. Original source payloads and unsupported semantics remain visible. A coherent capture is not proof of effective filter/parameter state, native rendering, permissions or migration parity. The actual DMA reader can supply source-matched semantic evidence; a supplier revision/hash is not producer authentication.

### `metabase-api` and `metabase-capture`

`metabase-api` accepts `metabase-api-snapshot.v1`, not a bare dashboard, arbitrary
MCP response or generic Domo migration bundle. `metabase-capture` projects the
separate `metabase-visual-capture.v1` envelope; the capture check, MCP import and
shared visual workflow separately verify its retained attachment bytes.
Read the [Metabase source contract](metabase-source-contract.md) for exact shape,
identity and state requirements and the [run guide](../../omni-artifact-accelerator/references/metabase-visual-run.md)
for local intake and separately authorized capture.

Preserve dashboard/tab/dashcard/card identities, original definitions, every
placement, parameter mapping, non-query object and unsupported query clause.
Simple interpreted clauses do not establish complete MBQL translation or target
binding. No `metabase-adapter` or DMA Metabase `source_adapter_result` exists in
this integration; normalized semantic requirements use the existing DMA exchange.

### `periscope-adapter` and `periscope-capture`

Accepts DMA's actual schema-1 `source_adapter_result`, `source: "periscope"`,
`adapter_version: 1`, with `--producer-revision a88f2a3b4dd0cfa596766f938961f37d673cf9b9`.
This separate compatibility pin leaves other producer contracts unchanged.
Original configuration, object/native/occurrence identities, expressions,
dependency declarations and upstream gaps remain evidence. File coverage is not
export completeness; `component_sha256` is not a JSON seal or producer authentication.

Read the [Periscope/CDT source contract](periscope-source-contract.md) for intake,
mapping boundaries and continuation. The adapter format is supplied-JSON intake
only. The separate `periscope-capture` format retains captured definitions and
transferred/rendered evidence with attachment checks in the workflow. Neither
parser executes code/queries or creates native content. The source specialist uses
the [run guide](../../omni-artifact-accelerator/references/periscope-visual-run.md)
for separately authorized capture. Sisense Linux/Fusion exports are different
surfaces and are not accepted by these CDT formats.

### `normalized-inventory`

Use this supplier-declared format for explicit manual evidence from any named source or reviewed screenshot/live-behavior captures that do not match a supported typed reader. It is **not a native parser for those products**; prefer a source-specific format when its actual contract is available.

```json
{
  "schema_version": 1,
  "kind": "omni_analyst_inventory_input",
  "platform": "domo",
  "assets": [{
    "kind": "dashboard",
    "source_id": "source-page-52",
    "scope": "workspace-7",
    "title": "Service performance",
    "evidence_refs": ["captures/source-page-52.json"],
    "facets": {
      "visual": {"status": "observed", "value": {"chart": "bar"}},
      "security": {"status": "unsupported", "value": "PDP policy evidence pending"}
    }
  }]
}
```

Allowed kinds: `dashboard`, `page`, `visual`, `filter`, `layout`, `app`, `project`, `cell`, `workbook`, `worksheet`, `query`, `definition`, `parameter`, `placement`, `control`, `content`, `action`, `device_layout`, `unknown`. Each asset requires an explicit `source_id` (string/integer or `null` for unknown), nonempty `evidence_refs`, and a `facets` object. Optional `scope` distinguishes repeated IDs in different containers. Facets are `visual`, `query`, `layout`, `filters`, `interactions`, `security`, `content`; each has `status` and `value`. Status is `observed`, `declared`, `unobserved`, `unsupported` or `needs_review`. Missing facets become unobserved gaps. A caller cannot set `verified` to gain native acceptance. References are retained declarations and never fetched or independently authenticated.

### `domo-agent` and `sigma-agent`

These read emitted contracts from the independent migration packages and require the exact inspected `--producer-revision`. Read [Domo formats and boundaries](domo-agent-bridge.md) or [Sigma formats and routes](sigma-agent-bridge.md) before use. They preserve native/source graph IDs, upstream coverage and behavior, with `migration_context` carrying the original contract, source lineage, declared route and explicit non-authority status. They do not invoke either source runtime or its live clients.

Hash checks validate only the supplied representations for the specifically documented contracts. They are not complete source-engine JSON Schema/Pydantic validation, proof of a current source tenant, authentication of a producer or independent store validation. Source-agent imports reject obvious credential-bearing fields; this limited structural check is not a general sanitization certification.

## Output v1

`kind: omni_analyst_source_inventory`, `schema_version: 1`:

- `source`: platform, input format, exact input byte SHA-256, canonical JSON payload SHA-256, projection version, acquisition mode; optional declared producer and source-file hashes.
- `assets`: occurrence-based `asset_key`, kind, original `source_id`, `source_identity` with raw/native/derived distinction and scope, source JSON pointer, canonical source-payload SHA-256, full `source_payload`, and facets. `asset_key` is local occurrence identity, not a vendor ID; reordering arrays may change it.
- `dependencies`: supplied Looker references with `embedded_evidence` or `unresolved` status. Embedded evidence does not establish executable semantics.
- `gaps`: code, source pointer, review status and optional detail. DMA `upstream_gaps` also remain verbatim.
- `upstream_payload`: the decoded original document, including unknown fields. Exact byte formatting is bound by input hash and remains in the unchanged source file; JSON key order/whitespace are not recreated.
- `migration_context` when a source-agent profile is used: preserved source contract, run/scope/unit, explicit route or `null`, source declarations, hash-check limits, and `store_backed_readiness: not_verified`, `build_authority: false`, `target_write_authority: false`, `upstream_write_permitted: false`, `acceptance: not_established`. These values never inherit caller-supplied acceptance/readiness flags.
- Domo nested source envelopes also carry `decoded_source_payload`. Asset source pointers then address this decoded evidence tree, identified by `source.projection_payload_root`; the original envelope and its JSON string remain in `upstream_payload`.
- `coverage`: counts for the supplied artifact only, always `partial_evidence`.
- `evidence_level: static_supplied_evidence`, `export_completeness: not_established`, `native_validation: not_run`, `source_execution: false`, `network_calls: 0`.

Every facet has `interpretation: preserved_only`. `observed` means a field was present, not that its meaning or security enforcement was verified. Store proposed Omni bindings and redesign choices separately from this immutable evidence artifact.

Looker projections now declare `source.projection_version: "1.2.0"`. The existing `looker-api` input interface remains supported, but query tiles, nonquery content, controls, dependency definitions and repeated placements have distinct obligations. Stored Looker inventories from an earlier projection must be deliberately regenerated from their immutable original bytes, then their requirements and dependent evidence re-created; deterministic replay rejects stale inventories. Other providers retain their existing projection versions. This migration does not upgrade local evidence to native validation or acceptance.

## Hex visual capture and generic DMA producer

Use `--format hex-capture` for `hex-visual-capture.v1` and `--format hex-adapter --producer-revision c513474e87af9c2c31deebd2ae675c8602955203` for the actual Hex `source_adapter_result`. The legacy `hex_source_inventory` continues to use `dma-inventory` at the same declared revision. These are separate contracts, not renamed equivalents. Read [the Hex source contract](hex-source-contract.md) for exact shapes and byte verification.

Complete original definitions retain tabs, repeated placements, controls, content, shared filters, actions, code/component dependencies and generated files independently of semantic parsing. Unknown generated screens remain obligations; generated source is never executed. The capture preserves selected source origin/workspace/project/version/cell/output and state, plus actual supplied/API attachment bytes. Preview rows, unknown state or incomplete result populations cannot establish numerical parity. Imported identities and compatibility pins remain supplied evidence, not authenticated provenance.

## WebFOCUS evidence

`webfocus-adapter` projects the explicitly qualified DMA `source_adapter_result`;
`webfocus-capture` projects the OAA visual capture. Read the
[WebFOCUS source contract](webfocus-source-contract.md) for producer/version pins,
original-file verification, page occurrence identity, result binding and limits.
Source procedures and executable style/page code remain inert. An adapter report
is not a complete visual inventory, and structural translation is not native parity.

## ThoughtSpot evidence

The [ThoughtSpot contract](thoughtspot-source-contract.md) specifies the typed
JSON snapshot, independent inventory, original pointer mappings, capture and
state-bound result evidence. Select `thoughtspot-api` or `thoughtspot-capture`
explicitly; no schema guessing or `thoughtspot-adapter` producer exists. Native
TML and inventory omissions remain obligations. Separate scoped source acquisition,
interpretation, target design and independent acceptance.

## Qlik supplied contracts

`qlik-api` and `qlik-capture` preserve typed original Qlik definitions and
independent visual scope; see the [source contract](qlik-source-contract.md).
Each original payload and independent inventory requires byte-bound mapping.
Keep repeated placement identity, master references, private/source omissions,
expression text, states and unresolved extension behavior. Capture validation
verifies retained bytes; it does not authenticate the source or qualify a tenant.
No `qlik-adapter` DMA format is registered.

## MicroStrategy supplied contracts

`microstrategy-api` and `microstrategy-capture` project original definitions and
independently enumerated scope. See the [source contract](microstrategy-source-contract.md).
Keep project/object/type/version, prompt keys, attribute forms/elements, metric
identity, page/visual/placement pointers and shared dependencies. Unknown, denied,
private and unsupported obligations stay in the denominator. No
`microstrategy-adapter` DMA format is registered.

## Cognos report snapshots

`--format cognos-report` reads `cognos-report-snapshot.v1` under the
[Cognos contract](cognos-source-contract.md). The local importer wraps original
UTF-8 report XML with reviewed identity and independent inventory metadata.
Reprojection revalidates the exact XML fingerprint. Source expressions, external
references, unknown XML and behavior remain inert evidence or review obligations.
No connected acquisition, dashboard-spec schema or result binding is qualified.

## BusinessObjects snapshots and captures

`--format businessobjects-api` reads `businessobjects-api-snapshot.v1`;
`--format businessobjects-capture` reads `businessobjects-visual-capture.v1`.
See the [source contract](businessobjects-source-contract.md). Original bytes,
independent inventory, provider/report identities, element occurrences and
unresolved dependencies remain pinned. Incomplete exports retain their missing
obligations. Self-declared REST provenance is not authenticated source evidence;
result/capture normalization and host authority have separate contracts.
