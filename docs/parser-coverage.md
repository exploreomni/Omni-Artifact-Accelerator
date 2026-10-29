# Analyst migration parser coverage

Historical source evidence reviewed 2026-10-22; Periscope/CDT, Metabase and WebFOCUS interfaces reviewed
2026-10-28. Compatibility and fixture results describe only their retained scope;
they do not establish a live source/Omni migration, native rendering, effective
access or business acceptance. CDT, Metabase and WebFOCUS real-tenant pilots remain unqualified.

## Producer compatibility

The following revisions identify the source contracts exercised by the package. They are compatibility pins, not a requirement that every user has access to every upstream repository.

| Producer | Compatible revision | Use |
| --- | --- | --- |
| Data Model Accelerator | `c513474e87af9c2c31deebd2ae675c8602955203` | Optional source inventory and backend handoff integration. |
| Data Model Accelerator, Periscope/CDT source report only | `a88f2a3b4dd0cfa596766f938961f37d673cf9b9` | Separate `periscope-adapter` compatibility pin; does not replace other producer pins. |
| DomoMigrationAgent | `55eba0ca0690fbf14f39eddbc8a04c94a720c155` | Supplied Domo evidence/rebuild/redesign contracts. Source-engine access is separate. |
| SigmaMigrationAgent | `f4eda45b0f49dc7335496d028665f7339ed82e8f` | Supplied Sigma snapshot/capability contracts. The connected `sigma-source-operations@0.1.0` profile, v2 page/element capture and OAA evidence bundle are separately maintained; the base revision alone does not include the extension. See the compatibility registry and host guide. |

`DMA/scripts/` below means `skills/data-model-accelerator/scripts/` in the companion [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator). `DMA/adapters/` means that directory's `source_adapters/`. Domo/Sigma engine paths refer to `packages/omnikit-migration-engine/src/omni_migrator/` in the separately obtained source engine. See [testing](TESTING.md) for optional compatibility checks. Offline imports do not install, authenticate or execute an upstream producer.

## What this package implements now

`skills/omni-artifact-translator/scripts/translate_artifact.py` is an independently authored, standard-library, offline projection CLI. It does not copy or import the migration engines. Its executable paths are:

1. **Looker**: `looker-api` accepts Dashboard API JSON or the schema-1 wrapper; `looker-capture` accepts the maintained bounded API/supplied-file producer, including optional safe dashboard YAML interpretation. Content, controls, tabs, layouts, repeated placements, actions, query/Look/merge definitions and unknown objects retain distinct identities. `looker-canonical` and `looker-adapter` import the two actual DMA producer contracts separately; original payloads and limitations survive.
2. **DMA supplied inventories**: schema-1 `tableau_source_inventory`, `powerbi_source_inventory`, and `hex_source_inventory`, pinned to the inspected DMA revision. `powerbi-adapter` separately accepts the actual Power BI `source_adapter_result` with its object/expression/dependency evidence; it does not spoof the legacy kind. Native/scoped/generated IDs remain distinct and upstream evidence/gaps survive. The revision is caller-declared; this import does not authenticate the producing checkout or re-read source files.
3. **Typed normalized manual inventory**: explicit asset identities, evidence references and observed/unobserved/unsupported facets for any named source. This is an import contract, not native support for every platform.
4. **Domo migration-agent emitted artifacts**: `omnikit.domo.evidence.v1`, `omnikit.domo.source-evidence.v1`, `domo-to-omni.dashboard-rebuild-plan.v1` and `domo-to-omni.external-redesign-handoff.v1`. Preserves source definitions/edges/coverage, Page/Card/query/placement/behavior denominators, target proposals and assignment boundaries.
5. **Sigma migration-agent emitted artifacts**: `sigma-api-v2` snapshots (actual `_omnikit_acquisition` marker or legacy fixture marker) with optional source-bound prepush context/scope; v1 capability aggregate, workbook graph, data-model snapshot, behavior manifest and semantic routing contracts; `sigma-visual-capture.v1` envelope; `sigma-prepush-package.v1` manifest. Preserves explicit routes separately from target-neutral source evidence; no default route or upstream dbt permission under direct reconstruction.

6. **Tableau visual capture:** `tableau-visual-capture.v1` from the source-only wrapper or official-MCP intake. Preserves exact definition bytes/hashes, explicit REST/XML identities, nested/repeated/device placements, controls/content/actions, result/image attachments and unresolved objects. Optional exact-source DMA semantic evidence is retained separately.

7. **Power BI visual capture:** `powerbi-visual-capture.v1` from bounded supplied PBIR/Fabric intake or fixed source REST operations. Independently enumerates retained report/page/visual files, controls, content, filters, actions/bookmarks, groups/mobile references and resources. Semantic-model absence or an unsupported chart role cannot stop the visual denominator. Original definitions and attachments are verified separately from their interpretation.

8. **Hex visual capture and generic adapter:** `hex-capture` accepts `hex-visual-capture.v1`, preserving original YAML and supporting files, tab/layout/placement denominators, input/control/content/action/code/generated-file obligations, version and state identities, and immutable supplied/API attachments. `hex-adapter` consumes the actual DMA `source_adapter_result` separately from legacy `hex_source_inventory`. Both producer enrichments retain their original evidence and cannot shrink the visual denominator. Safe YAML requires an approved PyYAML installation.

9. **Periscope / Sisense CDT:** `periscope-adapter` imports the separately pinned
actual DMA `source_adapter_result`. `periscope-capture` retains an independent
dashboard/chart/control denominator, explicit Git/API crosswalk, original files,
requested/observed state and transferred/rendered evidence. Source code stays
inert; declared hashes and runtime fingerprints are not authentication. The
[CDT source contract](../skills/omni-artifact-translator/references/periscope-source-contract.md)
describes bounded capture and comparison inputs; Linux/Fusion is outside its scope.

10. **Metabase:** `metabase-api` accepts the typed `metabase-api-snapshot.v1`;
`metabase-capture` projects `metabase-visual-capture.v1`; capture/MCP/shared-workflow
checks separately verify retained bytes.
Dashboard/tab/dashcard/card identities, repeated placements, controls, content,
raw query definitions and unknown clauses remain independent obligations. Bounded
capture and result normalization are separate from source interpretation. The
[Metabase source contract](../skills/omni-artifact-translator/references/metabase-source-contract.md)
defines the supported subset; no arbitrary MBQL compiler, YAML serialization
parser, Domo runtime import or DMA Metabase adapter is supplied.

11. **WebFOCUS:** `webfocus-adapter` accepts qualified DMA declaration reports;
`webfocus-capture` accepts the OAA original-file, independent visual inventory and
state-bound capture contract. Read the [WebFOCUS contract](../skills/omni-artifact-translator/references/webfocus-source-contract.md).
FEX/MAS/ACX declaration recognition is separate from page/visual completeness.
Bounded style interpretation retains opaque/dynamic blocks rather than evaluating
scripts; unknown wrappers/extensions and runtime behavior stay review obligations.

All parser outputs remain partial evidence. Read the skill's [input/output contract](../skills/omni-artifact-translator/references/inventory-contract.md), [Looker source contract](../skills/omni-artifact-translator/references/looker-source-contract.md), [Power BI source contract](../skills/omni-artifact-translator/references/powerbi-source-contract.md) and [Tableau source contract](../skills/omni-artifact-translator/references/tableau-source-contract.md) for exact shapes and limits. The offline translator has no live acquisition or target write behavior. Hex/Looker/Power BI/Tableau/CDT/Metabase/WebFOCUS acquisition uses separate bounded source wrappers; native candidate construction is separately configured. Parser support alone does not recreate charts, Apps, filters, actions, layouts or security in Omni.

## Existing BI capabilities and analyst gaps

| Source | Actual inspected export shape and code | Existing scope | Analyst route and outstanding gaps |
|---|---|---|---|
| Looker | Actual `canonical_dashboard` from `DMA/scripts/looker_source.py` and `source_adapter_result` from `DMA/adapters/looker.py`; raw API/wrapper and `looker-visual-capture.v1`. | Independent dashboard/placement/content/control inventory; fixed API4.0 definitions/dependencies, PNG renders and JSON result evidence; supplied dashboard YAML with safe bounded parsing and optional PyYAML. | LookML compilation/inheritance, Liquid/user attributes, imported projects, PDT/runtime behavior, merged execution, effective access and native parity remain unresolved. Unsupported YAML files in the generic DMA producer remain obligations even though OAA has a separate supplied-YAML path. |
| Tableau | Actual DMA `tableau_source_inventory`, plus OAA `tableau-visual-capture.v1` containing safe UTF-8 TWB or bounded no-extract TWBX definition evidence, PNG and worksheet results. | DMA source semantics; OAA visual XML projection with distinct worksheet/placement/device identities, controls, content/actions, expected manifest and crosswalk reconciliation. Original formulas and unknown XML remain evidence. | Local REST capture or retained official-MCP intake; attachment-byte verification and typed result normalization. No arbitrary formulas, extract execution or universal chart conversion. Effective action/filter/access behavior and native rendering require source evidence. Parsing is not official XSD validation or native acceptance. |
| Power BI | Actual DMA legacy `powerbi_source_inventory` and general `source_adapter_result`, plus OAA `powerbi-visual-capture.v1` with independently retained PBIR/PBIP definition parts. | Native page/visual identity, query roles, geometry/groups, filters/controls/bookmarks/actions, hidden/mobile references, model binding and original resources; DMA enriches DAX/M/relationships/roles. | Local supplied-file or fixed REST definition/PNG/query capture, verified attachments and explicit result normalization. No PBIX decoding, TOM/general DAX/M runtime, remote model acquisition or universal chart/action conversion. Unknown state, incomplete exports and effective RLS/OLS remain gaps. Legacy DMA can omit later visuals after an unsupported role and cannot traverse a TMDL-only project without BIM; OAA's visual inventory is independent. |
| Hex | SchemaVersion 3 `.hex.yaml` project/component exports; actual DMA `hex_source_inventory` and `source_adapter_result`; OAA `hex-visual-capture.v1`. | Independent cells, seven-or-more tabs, repeated/input/content placements, shared filters, generated files, component and code dependencies; bounded definition/existing-run-image capture and supplied PNG/PDF/MCP/CSV/JSON evidence. | State-bound typed comparison, both DMA bridges, dashboard and initial/existing App paths. No notebook/source execution, automatic query creation, general Python/JS translation or native-runtime claim. Conditional interfaces, incomplete results, unknown sharing/access and generated code remain explicit obligations. |
| Domo | `DMA/adapters/domo.py`: Platform v1 DataSet detail/list JSON, Product v1 Beast Mode template/search JSON, unversioned Magic ETL clipboard `domo/dataflow-actions` JSON. `Domo/engine/extractors/domo/{manual.py,models.py,dataflow_definition.py,evidence.py}`: typed customer manifest, serialized evidence bundle/envelope and bounded DataFlow graph/SQL analysis. | DMA captures datasets, schema/PDP declarations, expressions and selected ETL actions. Dedicated Domo engine has evidence types for cards, pages, app definitions, layout/interactions/visibility, workflows and policies. DataFlow definitions preserve graph IDs, dataset references, scripts/SQL and unsupported transforms. | New `domo-agent` bridge reads the four emitted contracts above. It does not parse raw live Product API responses, customer ZIP manifests or generic MigrationBundle envelopes. DMA still excludes card definitions/SQL DataFlow envelopes; use the dedicated Domo evidence owner. No automatic behavioral translation or store-backed acceptance. |
| Sigma | `DMA/adapters/sigma.py`: REST v2 workbook/page/element/column/query/dataset/grant and element-lineage JSON. `Sigma/engine/extractors/sigma/{extractor.py,source_contracts.py,dashboard.py,capability_contracts.py,visual_capture.py}` and `prepush/{build,scope,session}.py`: `sigma-api-v2`, Data Model `/spec`, workbook graph/behavior/routing artifacts, source-bound context and reviewed prepush manifest. | Source/element identities, formulas, scoped model bindings, metric/relationship declarations and workbook pages/elements. Dashboard code explicitly retains unsupported controls/actions/input tables/writeback and unresolved fields. | New `sigma-agent` bridge imports these explicit JSON shapes. It preserves full source even when a pilot excludes charts. Existing API layout/control gaps remain; generated SQL stays supplied evidence. Beta/Deprecated labels in the DMA profile require official refresh before a customer claim. Actual API acquisition markers, verified native aliases, bulk-only placements, capability aggregates and versioned visual-capture envelopes have bounded bridge coverage. A bare tagged snapshot remains unsupported. Pure projection does not read attachment bytes or journal history; the host/workflow now verifies actual capture and package files, scope/state bindings and normalized results. Journal history and source capture completeness remain separate from analyst parity. |
| Metabase | OAA `metabase-api-snapshot.v1` and `metabase-visual-capture.v1`; inspected Domo `extractors/metabase/` code remains design precedent, not an imported producer. | Dedicated specialist and independent visual inventory preserve tabs, placements, parameters/mappings, content, raw MBQL/SQL, dependencies and unresolved clauses. Capture and result evidence use explicit source/state bindings. | No complete MBQL compilation, automatic semantic model creation, YAML serialization parsing or effective-access equivalence. Native SQL, nested/multistage queries and unsupported expressions remain reviewed obligations. Original-byte verification and local checks do not establish a qualified tenant migration. |
| WebFOCUS | Qualified DMA FEX/MAS/ACX declaration report and OAA capture with independent expected hierarchy. | Specialist, original hashes, report obligations, chart/style declarations, pages/repeated placements/controls, supplied outputs and bounded repository-read enrichment. | No FEX/Dialogue Manager execution, arbitrary JS interpretation, universal CM manifest decoding, tenant render API or source-to-Omni compiler. Local qualification is not live migration acceptance. |

The [Looker Dashboard API](https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Dashboard/dashboard) was checked live on 2026-10-21 to confirm the direct input contract. The other rows describe inspected local code and its declared limitations; they are not freshly verified vendor support matrices.

Metabase official MCP/API, serialization, export and interaction references were
reviewed 2026-10-28; see [source competencies](../skills/omni-metabase-migrator/references/source-competencies.md).
The Domo Metabase source at the listed Domo revision has narrower and sometimes
lossy mapping: unresolved SQL tiles can disappear, parameter mappings flatten and
unsupported query clauses can yield partial candidates. Its conformance fixture's
coverage labels are not adopted as OAA completeness claims. Current DMA source
registries have no Metabase adapter; use normalized, scoped backend requirements.

## Other DMA adapters present

The registered sources come from `DMA/adapters/registry.py`; every corresponding file's `CAPABILITY` declaration was inspected. These support upstream evidence or future analyst extensions, not automatic dashboard conversion. CDT now has the dedicated OAA projection/capture route above; the remaining rows are not dedicated OAA BI adapters.

| Adapter file under `DMA/adapters/` | Declared supplied formats | Boundary relevant to analysts |
|---|---|---|
| `periscope.py` | CDT Git Configuration YAML and SQL/Python/R sidecars, custom modules | Reused through the separately pinned OAA bridge. CDT Git is not Sisense Fusion JSON; inherited filters, encrypted settings and effective security still need independent evidence. |
| `webfocus.py` | UTF-8 `.fex` literal report subset; `.mas` / `.acx` declarations | No Dialogue Manager, includes, remote requests or report execution; unsupported syntax remains gaps. |
| `bigquery.py` | GoogleSQL, REST v2 Table/Routine JSON, Dataform v1 compilationResults query JSON, SQLX preservation | No SQLX/JavaScript compilation or authenticated physical bindings. |
| `snowflake.py` | SQL, SQL API v2 ResultSet JSON, CLI JSON/JSON_EXT catalog-row candidates | Result headers are not physical schema; grants/policy attachments and runtime remain unverified. |
| `redshift.py` | SQL, Data API DescribeTable/ListTables/GetStatementResult, SVV_COLUMNS row arrays | Result columns, pagination, database identity and security require separate evidence. |
| `clickhouse.py` | SQL, native FORMAT JSON query responses/catalog candidates | Sorting/primary keys do not establish business uniqueness; distributed/runtime semantics unverified. |
| `motherduck.py` | DuckDB SQL and catalog JSON row arrays | Local parsing is not MotherDuck cloud/permission validation; no ATTACH/extensions executed. |
| `databricks.py` | SQL, Unity Catalog TableInfo/ListTables JSON | No notebooks, Spark sessions, jobs or streaming execution; masks/filters are declarations. |
| `dbt.py` | Manifest v12; project/properties/package YAML; SQL/Jinja/Python preservation; seed hashes | Supplied compiled code is not authenticated execution. No macro/hook/package execution in parsing. |
| `coalesce.py` | Git Node/NodeType/Environment/Macro YAML fileVersion 1; data.yml v3; locations.yml v1 | Git format is not REST/hydrated metadata; no Jinja runtime or authenticated storage mappings. |
| `fabric.py` | `.platform` v2, getDefinition `definition.parts` UTF-8 InlineBase64, Notebook, DataPipeline, Lakehouse, SemanticModel | Only bounded declared readers. Fabric Git logical IDs are not workspace IDs. No analyst report/App conversion inferred. |

## Extension decision

Reuse approved DMA inventories for source semantics and physical bindings; preserve the dedicated Domo/Sigma boundaries for their source acquisition. Add analyst adapters one format at a time when an actual pilot supplies a stable contract and independently specified expected behavior. Each extension must preserve original IDs/hashes and unknown fields, test malformed and unsupported inputs, expose export/permission gaps, and include native analyst acceptance scenarios before claiming lift-and-shift parity.

The focused tests are synthetic and establish parser/projection behavior only. Optional `test_sigma_visual_bridge.py` cases use actual Sigma producers behind in-memory transport and denied sockets (set `OMNI_ARTIFACT_SIGMA_CHECKOUT` and, when needed, `OMNI_ARTIFACT_SIGMA_PYTHON`); runtime imports are isolated to tests, never the offline importer. They check evidence retention, unresolved references, identity conflicts, DMA imports, bounded source-agent fingerprints, Domo membership/behavior/security omissions, Sigma route/context/graph consistency, unsupported claims, resource limits, unchanged inputs, private outputs and console-log boundaries. The Domo Page-plan/external-handoff examples and Sigma retail/routing examples from the inspected repositories were also projected read-only, without importing either runtime. None proves compatibility with all vendor exports or a customer production workflow.

The detailed producer contracts are [Domo](../skills/omni-artifact-translator/references/domo-agent-bridge.md) and [Sigma](../skills/omni-artifact-translator/references/sigma-agent-bridge.md).

## ThoughtSpot

`thoughtspot-api` reads `thoughtspot-api-snapshot.v1`; `thoughtspot-capture` reads
`thoughtspot-visual-capture.v1`. The dedicated specialist reconciles independent
scope with JSON TML, keeping Liveboard/saved Answer/pinned visualization/local ID/
placement identity distinct. Original-file mapping, retained state/results,
private-view obligations, explicit normalization and source-specific cases feed
the shared A–F, standalone and DMA paths. See the [source contract](../skills/omni-artifact-translator/references/thoughtspot-source-contract.md)
and [workflow](../skills/omni-artifact-accelerator/references/thoughtspot-visual-run.md).

Official interfaces reviewed 2026-10-28. The initial REST profile is Cloud26.10;
other versions use supplied evidence until qualified. Bounded enrichment supports
fixed metadata search/TML export, saved Answer/Liveboard results and PNG/PDF;
queries and renders require separate host grants. Retained Spotter schema/session
checks are local only. There is no general search/formula compiler, YAML decoder,
source authoring, arbitrary query endpoint, DMA ThoughtSpot adapter or qualified
live-tenant migration. PINNED Answer renders remain blocked because official
identifier guidance is inconsistent. Local fixtures do not establish native,
security, rendered or business acceptance.

## Qlik Cloud and Qlik Sense

`qlik-api` reads `qlik-api-snapshot.v1`; `qlik-capture` reads
`qlik-visual-capture.v1`. The [specialist](../skills/omni-qlik-migrator/SKILL.md)
reconciles original property definitions with independent app/sheet/object scope,
master dependencies, repeated placements, controls, private/missing content,
expressions and observed selection state. Straight/pivot normalization preserves
numeric/display distinctions, page coverage and source bindings. See the
[source contract](../skills/omni-artifact-translator/references/qlik-source-contract.md).

Official interfaces reviewed 2026-10-28. Optional bounded Cloud Reports capture
supports selected existing chart/sheet renders and their job lifecycle. Retained
MCP checks are passive; QIX acquisition belongs to an already approved external
host, not a bundled WebSocket transport. Client-managed sources use qualified
supplied evidence initially. QlikView, QVF/QVW/QVD decoding, extension execution,
source authoring, general expression compilation and a DMA Qlik producer are not
implemented. Local checks do not establish live tenant or business acceptance.

## MicroStrategy / Strategy

`microstrategy-api` accepts `microstrategy-api-snapshot.v1`;
`microstrategy-capture` accepts `microstrategy-visual-capture.v1`. The
[specialist](../skills/omni-microstrategy-migrator/SKILL.md) preserves original
definitions, an independent denominator, repeated placements, shared dependencies,
prompts/selectors, filter stages and unavailable/private/unsupported obligations.
See the [source contract](../skills/omni-artifact-translator/references/microstrategy-source-contract.md)
for supported raw response shapes and exact result bindings.

Optional connected operations require a version/schema-qualified selected-object
profile and separate metadata/execution/render/cleanup grants. Unknown deployments
use supplied evidence. Numerical normalization covers only the explicitly
qualified JSON Data tree or explicit CSV profile; it rejects incomplete/error
results and unsupported subtotals rather than flattening them. MCP validation is
passive and does not obtain dashboard layout or exports. No automatic connector
setup, package decoding, source authoring, arbitrary SQL, universal expression
compiler, pixel-perfect document converter or MicroStrategy DMA producer.
Live-tenant qualification remains separate from local package checks.

## IBM Cognos Analytics

`cognos-report` reads `cognos-report-snapshot.v1`. The
[specialist](../skills/omni-cognos-migrator/SKILL.md) and
[report importer](../skills/omni-artifact-translator/scripts/cognos_import.py)
retain exact supplied UTF-8 XML and identity/inventory metadata, then project
query, prompt, layout and dependency obligations. The parser rejects DTD/entity
inputs and bounds XML size, nesting and node count; it never resolves remote
schemas, includes, links or source code. Unknown vocabulary remains evidence.

See the [contract](../skills/omni-artifact-translator/references/cognos-source-contract.md)
and [workflow](../skills/omni-artifact-accelerator/references/cognos-visual-run.md).
Original and projection hashes are replayed through typed routing, A–F,
standalone bindings and DMA requests. Source-defined access remains unverified.

Connected acquisition/execution, dashboard specification decoding, deployment
archives, Framework Manager/data-module parsing, formula compilation, native
result normalization and live-tenant qualification are not implemented. Supplied
visual references support manual review, not automated parity. Numeric comparison
stays inconclusive until a qualified Cognos result/state binding exists.

## SAP BusinessObjects

The [specialist](../skills/omni-businessobjects-migrator/SKILL.md) uses
`businessobjects-api` and `businessobjects-capture`. The bounded snapshot reader
preserves original XML/JSON response bytes and independent inventory, recognizes
selected WebI structural shapes, and retains omitted/unknown obligations.
Modeled/unknown evidence cannot self-declare source-native support.

The capture helper embeds and rechecks originals, supplied raw results and
rendered evidence, with append-only journals and exact state/result bindings.
Numeric normalization preserves decimal precision and nulls, and rejects recognized source errors; it
does not infer full populations from preview data or format strings.

A separately injected trusted host can qualify selected metadata GETs. There is
no default connected activation, query/refresh/render/save/cleanup dispatch,
SDK/decoder installation, general formula compiler, complete Universe extraction,
Crystal binary parser or universal print-fidelity claim. Unknown engine/version,
missing security/provider state and unsupported behavior remain explicit gaps.
Local checks are not live-tenant or native/business acceptance. See the
[contract](../skills/omni-artifact-translator/references/businessobjects-source-contract.md)
and [workflow](../skills/omni-artifact-accelerator/references/businessobjects-visual-run.md).

## SSRS, Power BI paginated and Crystal Reports

`rdl-report` accepts the package's `rdl-report-snapshot.v1` wrapper around original
UTF-8 Microsoft RDL. The passive bounded XML reader preserves queries, expressions,
page/section geometry, tablix/group structures, prompts, code and references as
evidence. It does not execute them, resolve remote resources or validate complete
vendor schemas. Unknown/extension occurrences remain obligations. SSRS and Power BI
paginated identities/routes remain distinct from interactive PBIR/PBIP.

`crystal-report` accepts `crystal-report-snapshot.v1`: a supplied package-owned
extraction with exact original bytes, engine/version and independent inventory.
It does not open `.rpt` binaries, install SDKs, refresh saved data, evaluate formulas
or guarantee classic/Enterprise equivalence. Repeated placements and unresolved
subreport/formula dependencies are retained.

`rdl-report-capture` accepts the shared `report-source-capture.v1` for either source
family. Capture is supplied-file only; original definition and inventory must
match exactly. Numeric attachments pin parser profile, requested/observed state,
parameters, principal, population and completeness. Normalization alone is not
parity. Native Report candidate/readback/export/QA is a distinct local evidence
lane; automatic native execution and live source pilots remain unqualified.

See [RDL](../skills/omni-artifact-translator/references/rdl-report-source-contract.md),
[Crystal](../skills/omni-artifact-translator/references/crystal-report-source-contract.md)
and [capture](../skills/omni-artifact-translator/references/report-source-capture.md)
for exact schemas, bounds and current support limits.


## Connected Sigma qualification

The Sigma specialist supplies guided source intake, versioned runtime recognition,
bounded source operations and complete file/state validation. The local stdlib
suite includes neutral source-operation, capture, normalization and package tests.
A runtime-manifest match is integrity evidence, not dependency sign-off or live
qualification. Source runtime release, installed dependency-backed producer tests,
live tenant parity and local/remote host qualification remain separate milestones.
See [connected workflow](../skills/omni-artifact-accelerator/references/sigma-connected-host.md).
