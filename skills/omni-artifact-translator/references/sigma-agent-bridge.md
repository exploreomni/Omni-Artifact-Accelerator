# Sigma migration-agent bridge

SigmaMigrationAgent has a current local `sigma-migrate` prepush workflow and a retained advanced Phase-0 specialist workflow. They are separate runtimes with related evidence; do not report an integrated autonomous deployment path. The dedicated Sigma specialist coordinates their explicit saved artifacts and the new bounded source-operation extension within the existing OAA engagement. The reviewed converter session and terminal review remain owned by that package.

```sh
python3 scripts/translate_artifact.py /absolute/private/sigma-source.json \
  --format sigma-agent \
  --producer-revision f4eda45b0f49dc7335496d028665f7339ed82e8f \
  --output /absolute/private/new/source-inventory.json
```

The revision is the inspected repository HEAD; the visual-capture extension was qualified from local unpublished working-tree code on 2026-10-21. The pin does not authenticate production of the file or imply that extension exists at the committed revision. The pure translator imports no Sigma client or source engine. The local host and workflow additionally verify original attachment/package bytes through bounded file readers. The connected source extension requires its own reviewed runtime; see the [host guide](../../omni-artifact-accelerator/references/sigma-connected-host.md).

## Accepted shapes

| Discriminator | Source in SigmaMigrationAgent | Bounded import behavior |
|---|---|---|
| `_omnikit_acquisition.contract: sigma-api-v2` (actual API producer), or legacy `snapshotContract: sigma-api-v2` | `.../extractors/sigma/api.py`, `extractor.py`; `examples/retail-supported.json` | Preserves the acquisition marker, selected IDs, connections, model specifications, formulas/relationships, workbook pages and bulk elements, controls/grants/schedules and unknown fields. Checks marker consistency and selected workbook/model sets. Known `id` aliases must agree with named IDs. Model definitions remain separate from workbook experience evidence. |
| `schema_version: sigma-capability-spike-bundle.v1` | `.../extractors/sigma/capability_contracts.py`, `capability_spike.py` | Checks component content hashes, artifact/run/scope identity, ordered upstream references, shared workbook/model/principal/freeze bindings and evidence-mode consistency. Projects graph/model/behavior components with original nested locators; retains blockers and gate recommendations without running source runtime gates. |
| `schema_version: sigma-visual-capture.v1` | `.../extractors/sigma/visual_capture.py`, `visual_contracts.py` | Checks supplied envelope/request/snapshot/baseline/coherence/final-observation hashes; matches selected organization/user/workbook/page/element/model/tag, jobs and attachment pins. Retains source `complete`, `partial` or `blocked`, all gaps, and original tagged snapshot. The pure projection does not read files. OAA host/workflow additionally verify actual attachment bytes; journal history, native and privacy acceptance remain separate. |
| Nested `prepush_context.schema_version: sigma-prepush-context.v1` | `.../prepush/build.py`, `ReviewedSourceContext`, `source_context_hash` | Verifies its `source_sha256` against the snapshot excluding `prepush_context` and `_migration_scope`. Preserves element field locators/chart/layout/sorts and control target/default mappings; rejects missing referenced workbook/element/control targets. This is supplied observation context, not a self-issued approval. |
| Nested `_migration_scope.schema_version: sigma-migration-scope.v1` | `.../prepush/scope.py` | Checks original-source hash and retains selected/excluded/dependency IDs and issues. It never deletes source objects or treats exclusions as independently validated. Scope derivation/lineage closure remains with the Sigma package. |
| `schema_version: sigma-workbook-graph.v1` | `contracts/sigma/sigma-workbook-graph.v1.schema.json`; `.../extractors/sigma/capability_contracts.py` | Checks supplied artifact and exact node-set hashes; projects node/native IDs, parents, properties and edges; rejects orphan/duplicate edges. Retains unresolved behavior and declared source freeze. |
| `schema_version: sigma-data-model-snapshot.v1` | `contracts/sigma/sigma-data-model-snapshot.v1.schema.json` | Checks supplied artifact/specification hashes and bound model/version identity. Preserves sanitized specification, compound source bindings, omissions and unavailable-state reasons. Source-freeze approval is not authenticated. |
| `schema_version: sigma-behavior-manifest.v1` | `contracts/sigma/sigma-behavior-manifest.v1.schema.json` | Preserves control/action/input-table/schedule/saved-view/embed/layout/formatting/security evidence, disposition, owner and acceptance test. Checks that unresolved IDs and closed-denominator status agree with blocking items. Cannot upgrade observed behavior to target parity. |
| `schema_version: sigma-semantic-routing-decision-request.v1` or `sigma-semantic-routing-decision.v1` | Corresponding `contracts/sigma/` schemas; `SemanticRoutingPayload` | Retains the explicit human reference, decision record, source-context hashes, unit/scope and mode. Checks source scope, direct-versus-warehouse target topology and declared dbt route. A decision envelope also gets its supplied content hash checked. Human/source acceptance references remain unauthenticated. |
| `schema_version: sigma-prepush-package.v1` | `.../prepush/session.py`, `ReviewSession.build_package` | Imports the manifest only: selected route, source/target/file hashes, OS-local review declaration, proposed build and synthetic/live qualifiers. Checks that its route and hashes agree with the declared review. The pure projection does not read files. `sigma_check_package` separately verifies the entire directory, exact file set and source/target/proposal bindings. Supplied OS review is still not authenticated. |

Paths abbreviated `.../` mean `packages/omnikit-migration-engine/src/omni_migrator/`. Phase-0 artifact envelopes must use their full emitted serialization for the supplied-content-hash check. These are bounded projections, not a replacement for all validators in the Sigma package.

## Placements and capture boundaries

Nested Page membership is explicit placement evidence. A matching bulk element is not counted again; conflicting common definition fields reject. A bulk-only element with a valid `pageId` is retained under that Page. Without a Page reference, its placement stays unknown with a review gap. Repeated placement of one native element across Pages stays distinct. Missing control IDs remain unknown instead of generated native IDs; a referenced control still requires an explicit known identity.

A visual capture keeps `request.parameters`, requested timezone/data-as-of, principal references and the exact original/effective request. These are supplied context, not proof of effective query timezone, atomic data freshness or full-row completeness. `complete` means the source producer acquired its requested PNG and JSON under an unchanged configuration bracket; the analyst inventory **always remains `partial_evidence`**. A blocked capture can have no assets. Retain it for troubleshooting; it cannot establish a visual denominator. Attachment paths are checked as canonical relative paths and never followed by this importer. Independently verify the retained file bytes before comparison or display; partial/blocked files do not become accepted artifacts by import.

The envelope's self-seal and shared pins detect internal mismatch, not provenance authentication. Journal-chain continuity, source approval references, customer identity, runtime capability gates and effective access require their respective trusted owner. Bare tagged `workbook_snapshot()` output still has no directly accepted version marker: use its versioned visual-capture envelope, or retain it as supplemental evidence.

## Architecture choices, no default

Use `reuse_existing` when independently verified Omni Topics and field bindings
already satisfy the selected scope. OAA retains that standalone semantic baseline;
it does not manufacture a Sigma semantic-build package for this lane. The source
converter package has two reconstruction routes:

1. `omni_semantic_reconstruction`: preserve the accepted source boundaries and reconstruct semantics in Omni over existing accepted warehouse relations. **Do not request, generate or modify upstream dbt models under this route.** A data binding gap returns for source/Omni-model clarification; it does not silently switch routes.
2. `warehouse_first_refactor`: DMA can own a separately reviewed warehouse model/refactor and its tests. Omni BI and design consume the resulting accepted semantic/physical bindings. The route enables planning of that work, not warehouse writes.

A source snapshot and behavior manifest intentionally have no route. Their output has `route: null` and a target-design gap; inventory work can continue. A route artifact/manifest is imported separately so changing architecture does not rewrite source evidence. The coordinator must match the same unit/scope and exact source hashes before combining them. It must independently verify the real human decision/current local run; a JSON reference is not authentication.

## Experience and QA handoff

Preserve both `visualizationType` and any API-supplied `vizualizationType` spelling without rewriting source fields. An API element's existence and columns do not prove authoritative layout or control binding. Reuse source-bound observed context when present, then test responsive layout, formatting, default states, control targeting and propagation against a representative user session.

Actions, input tables/writeback, saved views, schedules and embedding can need redesign and a separate owner. Keep their behavior-manifest blocker open until its source/target acceptance evidence exists. Retain unavailable specifications, unresolved lineage and omitted query/grant information. Do not infer a join or field binding from a similar title, first matching column or generated SQL. Generated SQL is validation evidence, not automatically target SQL or metric authority.

QA receives exact source hashes, route, formulas/fields, model bindings, source and target query contexts, controls, persona tests and explicit differences. A synthetic fixture or local prepush pass cannot establish live permissions, source freeze, tenant parity, customer acceptance or target apply authority.

## Local producer qualification

`tests/test_sigma_visual_bridge.py` invokes actual `SigmaApi.snapshot()`, capability aggregate and visual-capture producers in an isolated subprocess using the source repository's HTTP transport fixtures and denied sockets. It covers actual emitted serialization, legacy/native aliases, bulk-only placement, partial/blocked/drift outcomes, changed hashes, resealed cross-component mismatch and cross-capture attachment substitution. It also composes actual source evidence into local visual requirements and a backend request/response journey. The production importer stays independent of the Sigma runtime and its dependencies.

Opt in only with an inspected trusted checkout and a Python runtime containing its dependencies:

```sh
OMNI_ARTIFACT_SIGMA_CHECKOUT=/absolute/trusted/SigmaMigrationAgent \
OMNI_ARTIFACT_SIGMA_PYTHON=/absolute/trusted/SigmaMigrationAgent/.venv/bin/python \
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_sigma_visual_bridge.py'
```

These fixtures qualify the local source contract and bridge, not a live tenant. Earlier production use of other migrator paths does not establish live qualification of this capture extension. Source export is separately authorized and can execute queries; this importer never submits jobs, polls, follows links or executes source code. Preserve unknown download outcomes and the source capture's non-atomic-data gap. Native layout, interaction, effective access and business acceptance remain separate evidence lanes.

## Connected and passive evidence contracts

The maintained [compatibility registry](../../omni-artifact-accelerator/references/sigma-compatibility.json)
recognizes `sigma-source-operations@0.1.0` as a versioned contract profile, not a Git
revision or released runtime. `sigma-source-operation.v1` binds request, observed
metadata principal, result, limits and retained gaps. A capture operation is a
receipt pointing to the actual visual envelope; its identity comes from that child,
not a fabricated outer observation. Snapshot locators retain the `/result` prefix.
Optional `_sigma_contents_beta` remains a separate current-workbook supplement.

`oaa-sigma-evidence@1` recognizes `sigma-source-evidence-bundle.v1`:

- `identity`: exact source origin, organization, principal reference and workbook.
- `selection`: published/tagged/draft/saved-view/unknown mode, version/tag/view and reference.
- `state`: filters, parameters, timezone, locale, cache observation and principal.
- `inventory`: independent reference and completeness, every node's stable key,
  kind/native ID, page/parent, disposition and original configuration. Optional
  source mapping binds an original JSON artifact and pointer to the node hash.
- `artifacts`: separate original REST, Beta contents, page/element renders, results
  or passive MCP responses, each with byte pin, source channel, exact state/selection,
  object keys and capture reference. Differing versions remain an explicit gap.
- `content_hash`: deterministic seal for internal consistency, never authentication.

File verification rejects missing/extra package files, symlinks, unsafe paths,
changed hashes/sizes, invalid PNG metadata and conflicting identity/state. It
checks original JSON-pointer mappings before allowing a supplied node hash to
support comparison. Unknown text stays inert; no response URL is followed.

`normalize_results(raw, profile, binding)` produces `sigma_normalized_results`.
The explicit CSV or JSON-object-row profile defines columns, ordinals, null tokens,
numeric separators and subtotal preservation. Binding keys are
`capture_content_hash`, `definition_fingerprint`, `object_key`, `attachment_id`,
`state_sha256` and `attachment_sha256`. Original bytes and exact precision remain
available. Known source errors cannot be erased by null mapping.

For qualified supplied-result comparison retain original definition mapping,
observed selection/state, execution completion, full-data scope, completeness
reference/count, population and freshness. Legacy capture `complete` means export
acquisition, not complete data. A page PNG is visual evidence only. Normalization,
checksums and self-reported evidence cannot establish independently authenticated
provenance or effective access.

For a v2 page visual case, `source_binding` must contain `workbook_id`, `page_id`,
`capture_content_hash`, `request_sha256` and `source_snapshot_sha256` matching the
actual envelope. Page IDs alone do not identify a workbook. Page PNGs cannot back
numeric comparisons. Metadata envelopes likewise require the exact selected
workbook/model sets and observed principal; a recomputed self-seal cannot authorize
different source scope.
