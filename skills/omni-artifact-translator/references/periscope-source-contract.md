# Periscope / Sisense CDT source contract

`periscope-adapter` projects an existing Data Model Accelerator (DMA) JSON report
into the analyst inventory. This format remains **offline source evidence intake**:
it does not acquire a source tenant, parse a Git checkout directly, execute source
code, capture images/results, or build native Omni content. The separate
`periscope-capture` format retains source-capture evidence; it does not change the
offline producer contract. Use the [CDT specialist](../../omni-periscope-migrator/SKILL.md)
and [shared run guide](../../omni-artifact-accelerator/references/periscope-visual-run.md)
for coordinated migration. Sisense Linux/Fusion, ElastiCube and Live JSON exports
are outside this CDT contract.

## Input and producer pin

Supply the actual schema-1 `source_adapter_result` with `source: "periscope"` and
`adapter_version: 1`, produced by the inspected DMA revision
`a88f2a3b4dd0cfa596766f938961f37d673cf9b9`. This is a separate compatibility pin;
it does not update the existing Looker/Power BI/Hex/Tableau producer contracts.

```sh
python3 -I -S -B scripts/translate_artifact.py /absolute/private/periscope-adapter.json \
  --format periscope-adapter \
  --producer-revision a88f2a3b4dd0cfa596766f938961f37d673cf9b9 \
  --output /absolute/private/new/source-inventory.json
```

Run from the translator skill directory. The output parent must already exist;
choose a new private output path outside the preserved source snapshot. The
[shared inventory contract](inventory-contract.md) supplies file, structure and
output bounds. No credentials, vendor package or DMA runtime import is needed for
this JSON projection. Acquiring or running a producer remains separately scoped.

The report contains:

- `source_files`: relative paths, SHA-256 declarations, parsed/partial/unsupported
  status and reasons; `coverage_summary` counts supplied files.
- `objects`: generated adapter identity, separate nullable `native_id`, kind/name,
  evidence locator/hash, original configuration and other details.
- `expressions`: original text, language, owner, content hash and source evidence.
- `dependencies` and `gaps`: declared/candidate/unresolved relationships and
  limitations, with source evidence and occurrence identities.
- `component_sha256`, when supplied by the registry route: a producer runtime/code
  fingerprint declaration, **not a JSON seal or authenticated checkout identity**.
- `export_completeness: "not_established"`, `native_validation: "not_run"` and
  `execution_performed: false`; import must not upgrade these claims.

Compatibility is grounded in DMA's `source_adapters/periscope.py`,
`source_adapters/base.py` and `source_adapters/registry.py` under
`skills/data-model-accelerator/scripts/` at the pin above. The full supplied report
remains evidence. An operator-declared revision and internally consistent hashes
do not re-read the original source files or authenticate producer execution.

## Analyst meaning and limits

The source format separates chart settings and SQL/Python/R sidecars. Settings can
declare type, theme, position and size; encrypted definitions remain opaque, and
inherited configured filters may be absent. Native token identity must remain
separate from captions and file-derived IDs. These are reasons to retain original
configuration and gaps instead of inferring a complete dashboard from file coverage.
[Official Git configuration](https://dtdocs.sisense.com/article/git-configuration).

Keep dashboard/chart containment, filter/parameter declarations, view/snippet/module
dependencies, source language and original formulas distinct. A dependency marked
candidate is not proven lineage. A missing native ID is not repaired by inventing
one. Unknown settings, unsupported files and opaque content remain obligations.
Python/R text, SQL templates and source instructions stay inert; neither this
bridge nor an imported report authorizes execution or package loading.

The inventory can inform BI requirements and a proposed source-to-target mapping.
It cannot establish effective global filters, compiled SQL, result completeness,
rendered layout, interaction behavior, sharing/row security or migration parity.
Preserve those gaps when asking DMA for semantic work or designers for a candidate.

## Continue from the evidence

Use the existing analyst workflow to review scope, analytical questions, source
bindings and unknown behavior. Request missing visual/result/access evidence
explicitly and retain its source revision, persona and filter state. This slice
does not acquire that evidence merely by importing the DMA report. Use the separate
Periscope capture contract and shared workflow for supported operations; do not
route a CDT request through another platform's capture engine.

CDT's [official Render API](https://dtdocs.sisense.com/article/render-api) is a
separate PDF-rendering route. Its existence does not make rendering part of this
bridge. Live capture and an independently reconciled visual/control denominator
need the separately scoped capture request and authorization before use.

An imported inventory is useful partial evidence, not a completed migration.
Numerical, visual, interaction, effective-access and business acceptance remain
separate observations against the actual selected source and native Omni candidate.

## Capture request and source files

`scripts/periscope_capture.py` has local `import-local`, `import-evidence` and `check`
commands. Connected execution is a separate host-injected `capture()` operation;
there is no CLI token/grant switch that authorizes it. Use the shared run guide for
commands. Local validation and synthetic checks do not qualify a real tenant.

The request uses `schema_version: "periscope-visual-capture-request.v1"` and
`product: "sisense_cdt"`. It requires these groups:

| Group | Fields and meaning |
| --- | --- |
| Identity | `capture_id`, `product_evidence_ref`, `site_name`, nullable `space_id`, `space_reference`, `dashboard_key` |
| Source revision | `source_revision` with `kind`, `value`, `reference`; kind is `git_commit`, `supplied_snapshot` or `unknown` |
| Authority/context | `principal_ref`, `authorization_ref`, nullable `credential_ref`; references are not tokens or authenticated grants |
| Scope | `evidence_mode` (`synthetic_fixture`, `manual_transfer`, `live_tenant`), `route`, `route_reference`, `target_surface` (`dashboard`, `app`, `both`) |
| Requested state | `state` containing `filters`, `parameters`, `daterange`, `aggregation`, `timezone`, `locale`, `principal`, `reference`; unknown context stays null where allowed |
| Supplied records | Relative `adapter_report_path`, `inventory_path`, `crosswalk_path`, plus the exact `producer_revision` above |

The source directory must contain those three distinct JSON files and every
`source_files` path declared by the DMA report. Local capture rereads and hashes
the originals before retaining them as inert bytes. This stronger file check is
separate from the report-only adapter's declared-hash validation.

The independent inventory is `periscope-source-enumeration.v1`, with
`method: "separate_source_enumeration"`, `reference`, `completeness` (`partial` or
`selected_scope_declared`) and `objects`. Every object has `key`, `kind`, `name`,
`parent_key`, nullable `source_object_id`, `disposition`, `disposition_reference`,
`evidence_reference` and `configuration`. Kinds are dashboard, visual, control,
placement, content or unknown; dispositions are include, manual_review, unsupported
or out_of_scope. A placement names `configuration.visual_key`. These declarations
retain a separate denominator; they do not authenticate export completeness.

The crosswalk is `periscope-identity-crosswalk.v1`, with `reference` and `rows`.
Each dashboard/visual has one row: `key`, nullable `git_token`, nullable `api_id`,
nullable positive `numeric_id`, and `reference`. Supplied Git tokens must match
the bound adapter object. Null identity is an explicit limitation: listing needs
the selected dashboard's API ID and rendering needs its numeric ID.

Optional `list_dashboards` defaults false; `render` defaults null. A render names
`render_id`, nullable `dashboard_ts`, `refresh_intent`, `widget_limit` and
`limit_reference`. A timestamp is paired with
`allow_refresh_older_than_dashboard_ts`; null uses
`no_freshness_refresh_requested`. This does not assert that rendering never runs
queries. Nonempty parameter maps are unsupported by the render route. Reviewed
`render_download_hosts` are explicit; no arbitrary response URL is fetched.

Budget fields bound requests per invocation, total requests, total bytes, response
bytes, elapsed seconds and attempts per operation. Defaults are 20 requests per
invocation, 200 total, 64,000,000 total bytes, 8,000,000 response bytes, 21,600 seconds
and three attempts. Local original-file intake is additionally limited to 512
files and 32,000,000 bytes. These are package limits, not vendor entitlements.
Do not create a fresh capture directory to bypass a spent or uncertain journal.

## Transferred results and visual evidence

`periscope-supplied-evidence.v1` contains an `attachments` list. Each entry supplies
a relative `source_path`, `attachment_id`, `object_key`, `format` (CSV, PNG or PDF),
`origin`, `result_scope`, `observed_state`, `population`, `freshness`, `completeness`
and `reference`. Keep full, displayed, transformed and unknown origins distinct.
Do not label a displayed export complete for the entire underlying population.

Observed state is null or `{state, observed_at, reference}`. Population uses
`{key, description, reference}`; freshness uses
`{data_watermark, observed_at, reference}`; completeness uses
`{status, reference, row_count}` with complete/partial/unknown status. A complete
CSV declaration requires observed state, population, freshness and row-count
evidence. These are supplied claims until independently corroborated.

The helper bounds attachment bytes and CSV structure; it does not render PDFs or
execute embedded content. PDF checking is signature-level only. Keep original
bytes and recorded transfer provenance. Rendering, numerical normalization,
accessibility and effective-access checks remain separate observations.

Capture journals use `periscope-visual-capture.v1`. Retain the entire directory and
the exact current journal path, including immutable source pins, attachments,
operations, request/definition fingerprints and predecessor history. Checking a
seal is neither producer authentication nor a permission grant. Unknown source
state, failed operations, omitted widgets and code-execution gaps must survive
projection into requirements and the final handoff.

## Numerical normalization and case binding

The local `periscope_normalize_results` host tool takes `source`, `profile`,
`binding` and `output` project-relative paths. It reads original CSV bytes and
calls the shared first-party typed normalizer; it does not run a CDT query or
import a vendor SDK. The output kind is `periscope_normalized_results`.

The profile requires `schema_version: 1`, `format: "csv"`, `encoding: "utf-8"`,
`subtotal_policy: "preserve"`, exact `headers` and an ordinal `columns` mapping
with unique output names. Declare type, null tokens/nullable behavior, date format,
decimal/group separators, percent behavior and any currency formatting explicitly
as applicable. Duplicate source headers need a resolution reference. Version 1
accepts comma-delimited CSV only; retain original bytes when a separately reviewed
conversion is needed. Normalization limits include 100,000 rows, 512 columns and
1,000,000 cells. No inferred currency, locale or silent NULL/blank/zero collapse.

The normalization binding has exactly `capture_content_hash`,
`definition_fingerprint`, `object_key`, `attachment_id`, `state_sha256` and
`attachment_sha256`. The workflow re-normalizes original bytes before accepting a
saved result; an edited output or an unrelated capture cannot substitute for them.

Each case retains its pinned `source_capture` and `source_binding`. The latter
contains `object_key`, nullable `placement_key`, `state_sha256`,
`definition_fingerprint` and, for numeric cases, the CSV `attachment_id`.
Original source identity and definition fingerprint must agree. Use a capture
projection for connected cases; the report-only format has no such captured state.

Comparison source records use `format: "periscope-normalized"` with both `file`
(normalized JSON) and `raw_file` (original CSV) pins. The independently observed
source and target contexts retain filters, parameters, date range, aggregation,
timezone, locale, principal, population, data watermark, result scope and attributable
freshness evidence. Source freshness references come from the retained attachment;
target freshness has its own evidence. Persona equivalence, population completeness
and currency mapping remain explicit requirements. Unknown or mismatched context
leaves comparison inconclusive even when displayed numbers agree.

When a chart has attached Python/R expressions or a Python/R `code_language`, its
numeric cases require both `origin: "transformed"` and `result_scope: "transformed"`.
The same rule applies to its placements. A complete raw SQL CSV cannot establish
parity for that chart's transformed output. Unbound Python/R module files remain
dependency obligations and do not automatically change another chart's population.
This check reads retained declarations; it never executes the source code.
