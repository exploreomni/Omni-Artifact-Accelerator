# Metabase migration run

Use [omni-metabase-migrator](../../omni-metabase-migrator/SKILL.md) inside the existing
orchestrator. This route combines bounded source evidence with shared design,
semantic handoff, native build and independent QA. It does not automatically
convert a whole tenant or establish a successful live migration.

## Start and qualify the source

Follow [execution startup](execution-workflow.md), record the actual package source
and recover the existing engagement, target and user choices. All new engagements,
including migration mode, follow [A–F](stage-gates.md). Reuse valid prior evidence
in those checkpoints; obtain the actual choice among exactly three options before
detailed design and coding. A faithful option retains source obligations. Older
engagements keep their recorded policy rather than inventing past choices.

Confirm the Metabase origin, version/edition, source principal and selected
collection/dashboard/tab/question IDs. Inspect actual available read/query/export
capabilities and the relevant tool/tenant contract. Source discovery permission,
source query execution, target native writes and publication are separate scopes.
Do not enable authoring tools or create public links merely to obtain a reference.

Read the [source contract](../../omni-artifact-translator/references/metabase-source-contract.md)
before intake. Record the independent expected dashboard/tab/dashcard/control set
and obtain original definitions, card dependencies and parameter mappings. Use the
specialist's [source competencies](../../omni-metabase-migrator/references/source-competencies.md)
for MCP inclusion fields, REST drift, serialization and export limitations.

## Retain local evidence or use bounded source capture

Keep originals and capture records in a private engagement outside the package.
Examples use `/installed` and `/private/run` as placeholders for approved paths;
substitute actual paths. Do not place credentials, result files, source exports or
customer screenshots into the repository. Preserve immutable inputs and use new
output names.

For supplied evidence, prepare the exact snapshot, `metabase-originals.v1` mapping
manifest and capture request defined by the source contract. Retain original REST/
MCP files under the selected source root. Import into a new empty capture directory:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/metabase_capture.py \
  import-local --request /private/run/inputs/metabase-request.json \
  --source-root /private/run/inputs/supplied \
  --directory /private/run/inputs/metabase-capture --allow-source-read
python3 -I -S -B /installed/omni-artifact-translator/scripts/metabase_capture.py \
  check --capture /private/run/inputs/metabase-capture/capture-000001.json
```

To retain approved local PNG/PDF/CSV/JSON exports, create a
`metabase-supplied-evidence.v1` metadata file and use the current capture journal:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/metabase_capture.py \
  import-evidence --capture /private/run/inputs/metabase-capture/capture-000001.json \
  --spec /private/run/inputs/metabase-evidence.json \
  --source-root /private/run/inputs/exports
```

Each transfer appends an immutable journal. Keep all revisions and use the latest
record for further transfers. Supplied MCP normalization stays partial; original
tool response, tool-call identity and explicit mapping references remain evidence.
YAML serialization is retained inert, not parsed.

For connected REST capture, start with a separately reviewed request and a new
empty private directory. Do not resume a supplied-import journal as a connected
run. After the operator authorizes the exact source scope and configures credentials
in the approved environment/secret mechanism, start the local stdio host:

```sh
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private/run --metabase-request inputs/metabase-rest-request.json \
  --metabase-directory inputs/metabase-rest-capture --enable-metabase-capture
```

`--metabase-token-env` chooses a `METABASE_...` environment-variable name; the default
is `METABASE_API_KEY`. Its value never belongs in commands, requests or chat.
Requests containing saved-question queries additionally require the separately
reviewed `--enable-metabase-query` grant. Each query also needs the canonical
`definition_sha256` of its reviewed complete card and a `read_only_reference` for
query/credential scope. The captured definition must match before submission.
The request pins the compatible auth header and body; no credential login flow,
arbitrary SQL or broad catalog scan is provided. `ignore_cache` is included only
when explicitly chosen. These checks do not make sequential reads atomic.

A saved-question request can execute its stored native SQL through Metabase.
Retain evidence for the read-only source identity/query scope; a saved card ID alone
is not that evidence. Distinguish passive definition reads from authorized query
execution in the capture report. No arbitrary/ad-hoc SQL, imported code or source
authoring is permitted by this capture route.

Call the dynamic `metabase_capture` tool with `resume: false` once, then
`resume: true` to continue the same scope and journal. Tool arguments cannot change
tenant, selected IDs, query bodies or grants. Preserve denied/failed operations and
reconcile uncertain query submissions before retrying. Newly discovered dependencies
outside the request need a new reviewed scope. `acquired_requested_operations`
means only the bounded selected calls completed; it is not complete dashboard,
observed-state, numerical or access qualification.

The CLI has no connected capture command. Local MCP tools are
`metabase_import_local`, `metabase_import_evidence`, `metabase_translate`,
`metabase_import_capture`, `metabase_check_capture` and
`metabase_normalize_results`. They use engagement-relative paths and the same
contracts as the helpers. Discover their actual schemas through the host. This
local host is not a provisioned remote Metabase connector or a connected MCP client.

## Project the retained evidence

For a supplied typed API snapshot:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/metabase-snapshot.json --format metabase-api \
  --output /private/run/inputs/metabase-inventory.json
```

The input must be `metabase-api-snapshot.v1`; a bare dashboard response, arbitrary
MCP result or Domo bundle is not accepted as this contract. Preserve raw response
provenance when preparing the typed input. No producer-revision flag can turn it
into a DMA Metabase adapter report.

For a verified capture, retain its directory and use the actual journal returned
by the capture helper:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/metabase-capture/capture-000001.json \
  --format metabase-capture --output /private/run/inputs/metabase-captured-inventory.json
```

The journal name illustrates a returned record, not a promise that a particular
suffix is current. Do not rename supplied evidence to imply it was captured live.
Local imports and attached results retain their acquisition class. The bare
translation CLI checks envelope structure, not attachment files. Run the capture
check on the selected journal first; MCP import and the shared visual workflow also
verify those original bytes before continuation.

## Resolve source requirements

```sh
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run prepare \
  --original inputs/metabase-snapshot.json \
  --inventory inputs/metabase-inventory.json --output contracts/visual.json
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run check --requirements contracts/visual.json
```

For captured evidence, substitute the actual returned journal and inventory paths.
`prepare` creates requirements to resolve, not a complete migration. Preserve every
tab, placement, series, control and non-query object. Record migrate/defer/exclude
dispositions with real rationale. Unsupported query logic remains a requirement;
removing it to make the target runnable is not source-faithful conversion.

Resolve route, target surface, current query bindings, control mappings and design
differences. Follow the [behavior handoff](../../omni-metabase-migrator/references/behavior-handoff.md).
Map each dashboard parameter to its actual affected placement/card and preserve
unaffected controls, linked-filter dependencies, reset, click/drill and return
state. Simple MBQL interpretation yields analytical requirements only; the analyst
must resolve unsupported clauses and the BI engineer must bind exact Omni fields.

## Bind backend and design choices

Use a current typed Omni baseline when existing topics and controls satisfy the
requirements. Send genuine semantic/physical gaps through [DMA cowork](../../omni-backend-handoff/references/cowork-contract.md)
as normalized, bounded requirements with `source_platform: "metabase"`, original
assets, route and independent expected cases. There is no DMA Metabase parser
in this integration. Keep the existing request/response/receive/select lifecycle
and 256 KiB selected-input limit; use dependency-complete waves rather than silently
truncating scope. A selected candidate is not proof of deployed fields.

After A–C, the product owner conducts D discovery using real source behavior,
analysis and narrative. Reuse branding/website answers, retain quality ambition
and honor the selected native dashboard/App surface. If an App is selected, ask
the [cache/refresh/optional-expiry question](../../omni-product-owner/references/data-refresh-policy.md);
no custom policy is a valid actual answer. Preserve the choice in E's options and
resolved design, then F's implementation and QA. Source cache settings do not
silently choose bypass, periodic refresh or client expiry.

## Build and compare the selected candidate

The BI engineer uses the existing [native build/export](../../omni-bi-engineer/references/omni-build-export.md)
workflow; the App engineer uses the [native App contract](../../omni-app-engineer/references/native-app-contract.md).
The source specialist adds no target writer. Keep separate candidates and native
receipts when both surfaces are selected. Execute only the reviewed candidate
within granted authority; reconcile uncertain writes before retrying.

Retain native readback, actual query/interaction evidence and separately permitted
visual observations. CLI-only constraints do not authorize browser/headless work
or permit lowering the quality bar. Missing rendered evidence stays explicit.

Normalize supplied results with `metabase_normalize_results`, an explicit typed
profile and the exact capture binding from the source contract. Preserve raw
bytes beside the normalized output. Use `metabase-normalized` in comparisons;
normalization is recomputed from the pinned originals. It never establishes that
all source rows were exported.

Use `visual_workflow.py compare --spec ... --output ...` for candidate-bound
numerical cases and `coverage --requirements ... --candidate ... --evidence ...
--output ...` for the per-case evidence lanes. Bind result identity, actual filter/
parameter state, source population, principal, time zone and freshness context.
An independently run card cannot certify a dashboard placement's parameter wiring.
Per-card series results cannot certify combined-visual behavior. Missing source
evidence keeps the case inconclusive even if the displayed totals agree.

Freeze/check the scope and return through the existing [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md).
Retain deferred assets, unsupported differences, access/operational work and actual
business-review status. Source capture, native execution, rendered quality and
effective access are separate qualification lanes. Local checks and synthetic
fixtures alone do not establish a live Metabase-to-Omni migration.

## Local implementation checks

The maintained source-only cases are `metabase-capture`, `metabase-projection`,
`metabase-integration` and `metabase-host` in the repository's
[validation runner](../../../scripts/validate_source.py). Select affected cases
with the existing standard-library runtime, for example:

```sh
python3 -I -S -B scripts/validate_source.py --case metabase-capture
python3 -I -S -B scripts/validate_source.py --case metabase-projection
python3 -I -S -B scripts/validate_source.py --case metabase-integration
python3 -I -S -B scripts/validate_source.py --case metabase-host
```

Run these from the repository root after reviewing the current source. They cover
local capture contracts, projection/comparison, workflow continuity and host scope
boundaries using fixtures/doubles. They do not contact a Metabase or Omni tenant,
load third-party dependencies or certify native/rendered/effective-access behavior.
Keep live qualification explicitly unperformed when no live tenant is in scope;
do not substitute additional synthetic tests for that evidence.
