# WebFOCUS source contract

Use [omni-webfocus-migrator](../../omni-webfocus-migrator/SKILL.md) in the existing
engagement. The [run guide](../../omni-artifact-accelerator/references/webfocus-visual-run.md)
provides executable paths. These readers preserve evidence and requirements; they
do not interpret arbitrary procedures, execute source code or write native targets.

## Typed inputs and producer qualification

| Format | Input | Meaning |
| --- | --- | --- |
| `webfocus-adapter` | DMA schema 1, source_adapter_result, source webfocus, adapter_version 1 | Bounded original declaration evidence; no visual denominator |
| `webfocus-capture` | webfocus-visual-capture.v1 | Original files, independent enumeration/crosswalk, optional DMA report, state-bound supplied evidence and optional repository-read responses |

The bridge separately qualifies public producer revision
`fcec34fb8e83bf7b663ab5ed0e1e945224dd03fd` and private revision
`c513474e87af9c2c31deebd2ae675c8602955203`. Its `PRODUCERS` table retains the inspected
component-file hashes. The report's component_sha256 remains a supplied runtime
fingerprint, not authenticated Git identity. Identical WebFOCUS parser bytes do not
make the entire producer closure interchangeable. No DMA package is installed or
imported by this reader; an unknown revision requires source review before support.

Validate original source_files, object/expression/occurrence identities, owners,
locators, hashes, coverage and dependency references. Preserve full expression text.
Keep export_completeness not_established, native_validation not_run and
execution_performed false. Recognized report declarations remain definition/report
obligations; they are not fabricated chart or page instances.

`webfocus-adapter` retains supplied originals embedded by the producer, not evidence
that an upstream runtime ran here. `webfocus-capture` additionally pins actual local
files. The bare translation CLI validates structure and retains an attachment-byte
verification gap; MCP capture import and the shared workflow verify referenced
files before continuation. Hashes detect changes, not authenticity or business truth.

## Request and local input records

`webfocus-visual-capture-request.v1` requires:

- capture_id, product webfocus, source_origin, product_version, product_evidence_ref,
  principal_ref, authorization_ref and nullable credential_ref.
- evidence_mode synthetic_fixture/manual_transfer/live_tenant; the label cannot
  upgrade supplied evidence into a live observation.
- source_revision `{kind,value,reference}`: git_commit, supplied_snapshot or unknown.
- root_key, route, route_reference and target_surface app/dashboard/both. Routes use
  the shared unselected/reuse_existing/omni_semantic_reconstruction/warehouse_first_refactor vocabulary.
- state `{filters,parameters,timezone,locale,principal,cache,reference}`. Filters and
  parameters are objects; time/locale/principal/cache may be null. Cache records the
  source context only; it does not choose target App refresh policy.
- originals_path, inventory_path and crosswalk_path: distinct canonical paths under
  the supplied root. Optional adapter_report_path and producer_revision occur together.

The supported origin is an HTTPS hostname without credentials, port, path or query.
Local output uses a new private directory. No source-root URL is fetched. Default
budgets are 20 calls/invocation, 200 total calls, 32 MB total bytes, 8 MB/response,
21,600 seconds and three attempts/operation; hard caps remain in validate_request.

Supply these JSON records alongside original bytes:

| Record | Fields |
| --- | --- |
| webfocus-originals.v1 | reference; records with source_path, kind, encoding, sha256, reference |
| webfocus-source-enumeration.v1 | method separate_source_enumeration; reference; completeness partial/selected_scope_declared; objects |
| webfocus-identity-crosswalk.v1 | reference; rows with key, nullable resource_path, nullable source_object_id, reference |

Original kinds are fex, mas, acx, sty, html, js, cm_zip or opaque. Encodings are
utf-8, utf-8-sig, utf-16, windows-1252, iso-8859-1, binary or unknown. Preserve exact
bytes; never silently transcode them into a matching producer hash. Known text
encodings receive bounded credential screening; opaque binaries are not certified
secret-free. Credential-bearing inputs reject rather than being silently rewritten.

Each enumerated object contains key, kind, name, parent_key, source_object_id,
disposition, disposition_reference, evidence_reference and configuration. Keys are
local stable identifiers; native resource paths remain separate. Source_object_id
may refer only to a retained DMA object or be null. Kinds cover app/dashboard/page,
section/container, visual, control/parameter/action, placement, content and unknown.
Section/container project as layout while retaining native_kind. A standalone
visual/report can be the selected root; do not invent a page. Placements name their
referenced visual/content/unknown object through configuration.visual_key, or configuration.content_key for content. Repeated
placements stay distinct even when their source report and parameters are identical.
All objects must have an acyclic parent path to root_key. The crosswalk covers every
object, including unknown native identities represented by null resource_path.

Dispositions include include, manual_review, unsupported and out_of_scope, always
with a reference. They are source declarations, not authority to remove target
requirements: the shared workflow separately records migrate/defer/exclude decisions.
Keep denied and missing objects in the selected denominator instead of reducing it
to the set of parsed reports. selected_scope_declared is not tenant completeness.

## Passive interpretation and archives

Known-encoding FEX can yield bounded GRAPH FILE declarations, ordered STYLE records
and strict full-object GRAPH_JS JSON. Original text/locators remain authoritative.
Functions, malformed or duplicate-key JSON, legacy GRAPH_SCRIPT, includes, dynamic
variables and unsupported syntax stay opaque with explicit gaps. No code is evaluated
and no linked file, stylesheet, image or URL is fetched. A data bucket/type/layout
proposal still needs resolved semantics and target capability evidence.

CM ZIP handling inventories bounded member names, bytes and hashes without extracting
them onto disk or interpreting an unknown Change Management manifest. Reject unsafe
paths, symlinks, encrypted/unsupported members, collisions and excessive expansion.
Recognized text members receive bounded screening. A CM package alone does not
produce a complete visual inventory; supply the independent records and qualified
original files separately. Opaque XML/HTML is never rendered or executed.

## Connected repository reads

Optional operations contain operation_id, action, resource_path and reference.
Only get, getContent and properties are supported. Every resource must already be
in the imported crosswalk; discovery cannot expand scope. getContent is limited to
reviewed .fex/.url paths. api_contract contains exactly context_path /ibi_apps,
wrapper ibfsrpc.v1, auth_header Cookie or Authorization, and reference.

The helper builds the documented canonical route for the action. It rejects
unreviewed methods/actions/paths, query injection, credentials in URLs and redirects.
There is no run, runAdHocFex, source upload/edit, scheduling, describeFex/getDetails,
automatic login or cross-origin resource retrieval. An HTTP GET alone is never an
allowlist. The host supplies only the selected credential header; a request JSON or
chat design choice cannot grant network authority.

Connected capture enriches a pre-imported exact request and journal. It retains
response bytes, request fingerprint, HTTP status and separately interpreted XML
business status. Unknown wrappers remain opaque; returned paths are not followed.
Sequential reads are not an atomic snapshot and do not replace the imported
source definitions or prove their currentness. Review changed source manually and
start a new pinned capture when necessary. Successful requested operations do not
establish a complete page, current data, rendering or effective access.

## Supplied visual and numerical observations

`webfocus-supplied-evidence.v1` contains attachments. Each has attachment_id,
object_key, source_path, format csv/json/png/pdf, origin full/displayed/transformed/unknown,
result_scope query_result/transformed/displayed/unknown, observed_state, population,
freshness, completeness and reference. Imports append an immutable journal revision;
keep all revisions and use the returned latest path. PNG/PDF checks inspect bytes,
not rendered appearance; no browser or decoder is provisioned.

Observed_state is null or `{state,observed_at,reference}` with optional
placement_reference and result_context. Requested state and observed state remain
separate. Population is `{key,description,reference}`; freshness is
`{data_watermark,observed_at,reference}`; completeness is
`{status:complete|partial|unknown,row_count,reference}`. Complete numerical declarations
require actual state/principal, result origin, population/freshness references and
an observed row count. They remain supplied evidence rather than authenticated claims.

For numerical comparison, a visual's configuration.result_contract and the
attachment's observed_state.result_context record data_mode full_data/preview/test/unknown,
row_limit positive-or-null, row_limit_stage before_aggregation/after_aggregation/none/unknown,
aggregation_stage native_report/raw_query/in_document/unknown, and reference.
Missing or unknown stages remain inconclusive. Test/dummy values cannot qualify
numeric parity. A deliberate preview can compare only with the same supported
population and limit/aggregation evidence; in-document transformations require the
corresponding transformed result. These fields do not become target cache defaults.

## Cases, normalization and continuation

Each case binds object_key, nullable placement_key, state_sha256,
definition_fingerprint and attachment_id. The selected placement must actually point
to that visual; observed placement parameter evidence is separately required. Bind
source/target actual context, population, watermark, time zone and locale. Effective
principal equivalence is independent. Target caching may differ if independently
verified freshness and analytical scope agree.

`webfocus_normalize_results` supports explicit typed CSV/object-row JSON profiles.
Binding has capture_content_hash, definition_fingerprint, object_key, attachment_id,
state_sha256 and attachment_sha256. Retain raw bytes, profile and normalized output.
The shared comparison format webfocus-normalized recomputes normalization from the
pinned raw source; edited normalized numbers cannot substitute for original evidence.
Use explicit decimal, null, date and currency rules; no guessed types or completeness.

The existing DMA exchange reprojects originals and verifies attachments on round
trips. Keep frontend scope, route, source IDs and cases intact; use dependency-complete
waves within its input limits. Existing native baseline/query/control and separate
App/dashboard receipt requirements apply. A–F remains enforced before coding and
publication remains separately authorized. Local fixtures do not qualify real
WebFOCUS execution, native rendering, effective access or business acceptance.
