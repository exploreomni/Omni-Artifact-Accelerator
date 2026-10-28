# Metabase source contract

Use [omni-metabase-migrator](../../omni-metabase-migrator/SKILL.md) within the current
engagement. The offline readers preserve source evidence; they do not acquire a
tenant, execute SQL/MBQL, compile Omni queries, create native documents or establish
business acceptance. The [run guide](../../omni-artifact-accelerator/references/metabase-visual-run.md)
separates supplied intake, connected capture, requirements and target work.

## Two distinct inputs

| Reader | Accepted envelope | Boundary |
| --- | --- | --- |
| `metabase-api` | `metabase-api-snapshot.v1` | Typed, supplied single-dashboard snapshot with original card definitions, metadata, declared coverage and gaps |
| `metabase-capture` | `metabase-visual-capture.v1` | Structural projection of snapshot, request, file pins and state; capture checks/shared workflow separately verify retained bytes. Independent scope enumeration remains separate engagement evidence |

Neither format accepts arbitrary JSON merely because it contains `dashcards`.
Retain original API/MCP response bytes and provenance when preparing the supported
snapshot. An MCP tool response is not automatically this envelope. Do not rename a
Domo MigrationBundle or a DMA result to pass the reader. There is no
`metabase-adapter` or DMA Metabase producer in this integration.

The snapshot has exactly `schema_version`, `identity`, `dashboard`, `cards`,
`metadata`, `coverage` and `gaps`. `identity` contains `source_origin`, `version`
and `principal_ref`. The origin is HTTPS without a path/query or embedded credentials;
native IDs are positive integers. Each metadata record is `{kind, id, payload}`
for `database`, `table` or `field`, with the same ID in its payload. Coverage carries
`dashboard`, `cards`, `metadata` as `complete`/`partial` plus a `reference`; `gaps`
is a list of explicit findings. Complete dashboard declarations include `tabs`,
`dashcards` and `parameters`. Supplied cards must belong to the selected dashboard's
dependency closure. Complete card declarations cannot omit referenced cards.

The snapshot binds source origin, version and principal reference to one dashboard;
its full card definitions and supplied metadata remain separate objects. The
capture envelope retains the exact snapshot and definition fingerprint. Keep the
capture directory intact and verify all referenced bytes before projection or
comparison. Hashes detect changed evidence; they do not authenticate its origin or
prove effective access, requested state or export completeness.

The bare `translate_artifact.py` CLI reads the envelope, not its attachment files;
it retains `actual_files_require_verification` as a gap. Run the capture check first.
The `metabase_import_capture` MCP tool and shared visual workflow verify the files
before continuation. Successful structural projection alone is not byte validation.

Use the helper's current request/snapshot validators as the executable contract.
Keep source evidence in a private engagement outside this repository. Duplicate
keys, malformed IDs, conflicting definitions, oversized structures and unsafe
paths are rejected rather than repaired by inference. Preserve unknown vendor
fields inside accepted original definitions and expose unresolved meaning.

## Identity and denominator

The inventory separates dashboard, tab/page, dashcard placement, card/question,
parameter/control and metadata definitions. Runtime IDs are distinct from
serialization `entity_id` and OAA object/asset keys. Source origin and dashboard ID
scope the inventory; a card can occur more than once without becoming one
placement. Preserve all tabs, repeated cards, additional series, text/heading/link/
image/action content, parameter mappings and local visualization overrides.

Reconcile an independently specified expected set with original definitions before
claiming coverage. Missing card/tab references, unknown placement types, source
actions and unsupported displays remain explicit gaps. Query interpretation never
reduces that denominator. Source actions are retained without execution authority.

## Query interpretation is not compilation

The first-party reader retains every complete original `dataset_query`. It may
label a conservative **legacy, single-stage MBQL subset** `interpreted_subset`:
positive numeric database/table IDs, direct field references, row/field counts,
sum/average/minimum/maximum/distinct, direct breakouts/selection, basic boolean
comparisons, field sorts and a positive limit. The result is an analytical
requirement with physical bindings still unverified; it is not target SQL or an
executable Omni query.

Modern MBQL, multiple stages, native SQL, saved-question sources, joins, unsupported
expressions/options/clauses or unresolved parameters remain `needs_review`. Keep
their exact original text/AST, dependencies and reasons. Never drop an unsupported
measure or filter and accept the remaining fields as an equivalent query. Retain
template tags and source-card references for analyst/backend resolution.

Known source display types are not a promise of native visual support. Series and
placement overrides stay in the inventory; per-card results do not prove combined
series/placement behavior. Serialization files can be supporting evidence but no
YAML/archive decoder or Metabase serialization runtime is bundled here. No upstream
Domo engine or third-party parser is imported by these readers.

## Capture and authorization

The `metabase-visual-capture-request.v1` profile contains:

| Fields | Meaning |
| --- | --- |
| `capture_id`, `source_origin`, `version`, `dashboard_id`, `principal_ref` | One selected tenant/dashboard and claimed principal/version; not authenticated by the file |
| `authorization_ref`, `credential_ref`, `api_contract` | Review references; contract is `{reference, version, auth_header}` with matching version and `x-api-key` or `X-Metabase-Session`; no credential values |
| `evidence_mode` | `synthetic_fixture`, `manual_transfer` or `live_tenant`; the label cannot upgrade supplied evidence |
| `route`, `route_reference`, `target_surface` | Existing route vocabulary and `app`/`dashboard`/`both`; a selected route requires a real decision reference |
| `state` | Exact `filters` object, `parameters` list, nullable `timezone`/`locale`/`principal` and nonempty `reference` |
| `snapshot_path`, `originals_path` | Distinct relative supplied-file paths for local import; connected runs keep this same request profile |
| `card_ids`, `metadata` | Explicit bounded object scope: at most 200 card IDs and 200 `{kind,id}` metadata selections; discovery cannot expand this automatically |
| `queries` | At most 50 records containing `query_id`, `card_id`, `body`, `definition_sha256` and `read_only_reference`. Pin the reviewed complete card definition; body requires `parameters` and permits explicit boolean `ignore_cache`. No arbitrary SQL or dataset-query body |

Optional budgets bound requests per invocation/total, total and per-response bytes,
elapsed time and attempts per operation. Defaults are 20/500 requests, 64,000,000
total bytes, 8,000,000 per response, 21,600 seconds and three attempts. A budget is
not authorization to query; source cache bypass remains an explicit request choice.

Local import requires `metabase-originals.v1` with `records`. Each record supplies
`source_path`, `source_kind`, `source_pointer`, `target_pointer`, `mapping`,
`reference`, `tool_name` and `tool_call_id`. Every retained dashboard, card and
metadata payload needs an original mapping. REST responses use `exact_json`;
MCP responses require tool identity and may use `explicit_normalized` with a
review reference, but all snapshot coverage declarations remain `partial`.
`serialization_yaml` is retained only as `inert_unsupported`, without interpretation.
Paths are bounded local files, not URLs to fetch.

The source helper separates local import/evidence transfer from host-authorized
connected work. A request file, claimed grant or chat design choice cannot confer
source-query permission. The host pins source origin, object scope, operation and
request bytes; target native grants and publication remain independent.

`definition_sha256` is the helper's canonical hash of the complete reviewed card,
not merely its SQL string. `read_only_reference` retains the review of query and
credential scope; it is not a privilege grant. Captured definitions must match the
reviewed pin before submitting the saved-question query. Sequential source reads
are not an atomic configuration/data snapshot, so concurrent source changes remain
a qualification risk.

Connected capture reads only the selected dashboard, card and metadata detail
routes and optionally executes the separately authorized saved-question requests.
Those saved questions can execute their stored native SQL on the source; retain
read-only source identity/query evidence as well as the exact definition/body pins.
Do not describe such a run as having no source query execution. Arbitrary/ad-hoc
SQL, imported-code execution and source authoring remain outside the helper.
There is no whole-tenant listing/search, connected MCP client, screenshot endpoint,
arbitrary query or automatic dependency expansion. Discovered out-of-scope IDs need
a new reviewed request. Resume only the exact journal/request; uncertain query
submission is reconciled before another attempt. Redirects are rejected.

Supplied evidence uses `metabase-supplied-evidence.v1` with `attachments`. Each
attachment binds an ID, source `object_key`, card/dashcard/tab identity, local
`source_path`, format (`png`, `pdf`, `csv`, `json`), origin/result scope and reference.
Observed state, population, freshness and completeness are separate records;
unknowns remain explicit. PNG/PDF checks are byte/signature checks, not rendering.
XLSX and arbitrary HTML are outside this evidence parser.

Preserve requested filters/parameters, time zone, locale and principal separately
from observed values. Record result origin/scope, completeness evidence, population,
source watermark, actual observation time and cache/freshness evidence. An omitted
field is unknown, not an inferred default. A requested fresh query does not prove
fresh source data. Errors, denied objects, limits, incomplete pagination and unknown
outcomes remain visible; an empty response is not a complete empty source.

Retained PNG/PDF evidence represents the recorded source state and coverage, not
query or permission truth. Source capture does not create public links, change
sharing, execute source actions or run arbitrary supplied SQL. Follow the exact
supported local and host interfaces in the run guide; unavailable operations stay
manual/pending rather than being replaced by an unofficial connector.

## Numerical normalization and case binding

`metabase_normalize_results` accepts supplied CSV, explicit object-row JSON, or
`metabase-json` REST results through the shared typed profile. CSV is comma-delimited
UTF-8. `metabase-json` requires `status: "completed"`, no reported errors and exact
`data.cols`/`data.rows` header alignment; decimal values retain exact text before
typed conversion. Ragged rows and duplicate/mismatched headers are rejected.
Use explicit column types, NULL tokens, date/time and currency rules; no locale,
denominator or type guessing. Normalization preserves rows, not export completeness.

The normalization binding contains exactly `capture_content_hash`,
`definition_fingerprint`, `object_key`, `attachment_id`, `state_sha256` and
`attachment_sha256`. Retain the normalized JSON, original bytes and profile. The
comparison uses `format: "metabase-normalized"` with both file pins and recomputes
normalization; edited normalized values cannot replace the raw source.

Each case uses the exact source object, definition fingerprint and requested-state
hash; numerical cases also select an attached CSV/JSON result. Attachment identity
must agree with card/dashcard/tab identity. Placement comparisons need observed
placement/parameter evidence; an independent saved-card query is not proof that a
dashboard parameter affected it. Supplied `observed_state.placement_reference`
records that evidence. Individual card results in a multiseries visual remain usable
as card evidence; combined multiseries placement parity stays inconclusive in this
version. No `series` result-scope value is accepted.

Unknown or mismatched observed state, population, freshness, result scope, origin,
completeness or required currency context keeps the case inconclusive. Generic
comparison checks and independent target evidence still apply; equal totals cannot
override a missing source binding. Source file integrity, numerical equivalence,
rendered interaction and effective access remain separate lanes.

## Continuation and qualification

Use a current typed Omni baseline for compatible existing topics/controls. For
real semantic gaps, the existing DMA cowork request accepts normalized requirements
with `source_platform: "metabase"`, selected asset IDs, route, source pins and
independent expected cases. Keep the existing request/response/receive/select
sequence and scope limits. A returned semantic candidate is not deployment.

All new engagements retain A–F and actual selection among three options before
coding. At D, record the desired App cache/refresh/optional-expiry policy when App
scope applies; carry it unchanged through design, build and QA. No custom policy
is a valid answer. Source cache metadata never creates a target default.

Use existing BI/App builders and separate native receipts. The specialist and
source helpers do not add a target writer. Local validation and synthetic fixtures
establish only their tested contracts. Real source capture, native target
execution/rendering, effective access and business acceptance require separately
retained evidence; the Metabase live pilot remains unqualified until those lanes run.
