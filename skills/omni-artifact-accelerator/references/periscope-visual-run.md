# Periscope / Sisense CDT migration run

Use [omni-periscope-migrator](../../omni-periscope-migrator/SKILL.md) for CDT source
expertise inside the existing orchestrator. This workflow combines bounded source
evidence with existing translation, DMA, native candidate and QA contracts. It is
not an automatic whole-tenant conversion or a qualified real-tenant pilot.

## Start with the existing engagement

Follow [execution startup](execution-workflow.md) and recover the selected source,
user decisions, target and allowed operations. Confirm CDT; Sisense Linux/Fusion,
JAQL and their MCP/authoring features are outside this contract. Ask only for missing
Space/dashboard scope, principal, supplied Git/export evidence, Omni destination,
audience and preserve-versus-improve intent. Reuse brand/website answers.

All new engagements, including faithful migrations, follow [A–F](stage-gates.md),
including the actual choice among three concepts before code. Reuse valid historical
scope, answers and accepted designs within their recorded policy rather than
repeating discovery unnecessarily. Existing journals and candidate reviews remain
in force. Source acquisition may proceed only within its own authorization; a chat
design choice does not grant capture or native writes.

Store evidence in a private engagement outside the package. Examples use
`/installed` and `/private/run` as placeholders for actual approved paths. Preserve
original bytes and use new output names; do not put credentials, private CSVs,
screenshots or customer definitions into the source repository.

## Collect a coherent source slice

Read the [source contract](../../omni-artifact-translator/references/periscope-source-contract.md)
before preparing a request. Keep the actual DMA `source_adapter_result` and its
separate producer revision. Reconcile an independent expected dashboard/chart set,
the Git snapshot and the numeric dashboard-ID crosswalk before dependent work.
Raw tokens, captions and numeric IDs are not interchangeable.

Select source operations separately: supplied files, source listing, requested
renders and transferred results have different evidence and authority. Use bounded
helpers or an explicitly labeled manual export when an operation is unavailable.
Do not invent a general source query endpoint, fetch public CSV links automatically,
activate an unofficial connector or execute exported SQL/Python/R.

Retain every failed/missing capture in the denominator. Preserve requested and
observed filters, principal, timezone, watermark and source cache/refresh state.
Definitions and images captured at different revisions need reconciliation; a
matching filename is not proof. Original CSV/PDF bytes remain evidence even when
their population or render completeness is unknown.

Create the request, independent enumeration and identity crosswalk described by the
source contract. Place them with the pinned DMA report and its original source
files under the selected source root, then retain the bounded snapshot:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/periscope_capture.py \
  import-local --request /private/run/inputs/cdt-request.json \
  --source-root /private/run/inputs/supplied \
  --directory /private/run/inputs/cdt-capture --allow-source-read
python3 -I -S -B /installed/omni-artifact-translator/scripts/periscope_capture.py \
  check --capture /private/run/inputs/cdt-capture/capture-000001.json
```

The new directory must be empty. The filename above illustrates the initial journal;
use the current journal for subsequent operations. To transfer an approved local
CSV/PNG/PDF export, prepare `periscope-supplied-evidence.v1` metadata and run:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/periscope_capture.py \
  import-evidence --capture /private/run/inputs/cdt-capture/capture-000001.json \
  --spec /private/run/inputs/cdt-evidence.json \
  --source-root /private/run/inputs/exports
```

This creates a new immutable journal; preserve both versions. Connected listing,
render submission and render-file retrieval require an explicitly configured host
authority callable. The CLI has no connected `capture` command or token/grant flags.
Request references are not that authority. Reuse the exact journal on resume, retain
unknown submission outcomes and reconcile them before retrying. Downloads do not
receive the partner credential, and arbitrary response URLs/redirects are rejected.

After the operator has authorized the exact request and configured credentials
through the approved environment/secret mechanism, the local stdio host can expose
the fixed source capture:

```sh
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private/run --periscope-request inputs/cdt-request.json \
  --periscope-directory inputs/cdt-capture --enable-periscope-capture
```

`--periscope-token-env` selects a `PERISCOPE_...` environment-variable name; its
default is `PERISCOPE_API_KEY`. Do not put the value in the command or request.
If the selected request includes rendering, its separately reviewed authority also
requires `--enable-periscope-render`. The host offers `periscope_capture` with
`resume: true`; tool arguments cannot select a new tenant, request or grant.
This is a local single-user host, not an installed remote CDT connector.

Local tools are `periscope_import_local`, `periscope_import_evidence`,
`periscope_translate`, `periscope_import_capture`, `periscope_check_capture` and
`periscope_normalize_results`. They use project-relative paths and preserve the
same contracts as the helpers. Discover their actual schemas through the host;
the availability of local tools does not enable network capture automatically.

## Project and review requirements

For a supplied DMA report, the offline route remains:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/periscope-adapter.json --format periscope-adapter \
  --producer-revision a88f2a3b4dd0cfa596766f938961f37d673cf9b9 \
  --output /private/run/inputs/periscope-inventory.json
```

Use `periscope-capture` only for the corresponding capture envelope, retaining its
directory and verified attachments. Do not rename a DMA report to the capture
format or claim a supplied render was fetched by the wrapper. The parser itself
does not perform source-network or native operations.

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/cdt-capture/capture-000002.json \
  --format periscope-capture --output /private/run/inputs/cdt-captured-inventory.json
```

Use the actual journal produced by the preceding transfer, not an assumed suffix.

```sh
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run prepare \
  --original inputs/periscope-adapter.json \
  --inventory inputs/periscope-inventory.json --output contracts/visual.json
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run check --requirements contracts/visual.json
```

For captured evidence, substitute the actual returned capture and its inventory
paths. `prepare` creates requirements to resolve; a successful projection does not
make them ready. Review every source object/file and explicitly migrate, defer or
exclude it with the required rationale. Evidence-only SQL/module files are not
automatically target visuals. Missing rendered widgets and unknown definitions
remain obligations; do not drop them to obtain a complete-looking result.

Resolve route, original behavior, target surface assignment, metric/query bindings,
design differences and acceptance cases. Apply the [CDT behavior handoff](../../omni-periscope-migrator/references/behavior-handoff.md).
Preserve each applicable filter/parameter as a source-control obligation, including
scope, affected/unaffected queries and reset. Opaque settings and custom-code
behavior need a disposition supported by evidence, not inferred equivalence.

## Bind the backend and selected design

Use the existing [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md)
to freeze the complete supplied denominator and independent listing. Reuse compatible
Omni Topics through a current typed baseline. Send actual semantic/physical gaps
through [DMA cowork](../../omni-backend-handoff/references/cowork-contract.md), with
original IDs, selected domain/route, source hashes and independent expected cases.
The 256 KiB selected-input limit still applies; use dependency-complete waves rather
than truncating source obligations. A DMA candidate is not proof of deployed fields.

For a new or redesigned App, the product owner carries the source findings into
artifact discovery, including the user's [data refresh policy](../../omni-product-owner/references/data-refresh-policy.md).
No custom policy is a valid answer. Do not turn a source cache setting into a fixed
target expiry or assume fresh-query bypass. Keep the same chosen policy in detailed
design, implementation and QA. Preserve quality ambition without forcing a fixed
layout, dimensional chart or App surface.

## Build, compare and return

The BI engineer uses [native build/export](../../omni-bi-engineer/references/omni-build-export.md)
and an inspected current baseline. The App engineer uses the [native App contract](../../omni-app-engineer/references/native-app-contract.md).
Reuse these bounded helpers; the source specialist does not introduce its own
target writer. Query/runtime creation and unsupported controls require their own
qualified engineering work. Keep dashboard and App documents, candidates and
execution receipts separate when both are selected.

Execute only the exact reviewed candidate within granted authority. Reconcile an
unknown write before retrying. Retain native readback, observed query/interaction
behavior and separately authorized visual evidence; saved source is not a render.

Use `visual_workflow.py compare --spec ... --output ...` for candidate-bound numerical
cases and `coverage --requirements ... --candidate ... --evidence ... --output ...`
for independent lane evidence. Comparison requires actual source/result identity,
observed state and population—not merely a source CSV and target total that happen
to agree. Unknown filters, cache mismatch, displayed-only rows or missing identity
keep the relevant case inconclusive.

For typed CSV results, use `periscope_normalize_results` with the original file,
explicit profile, capture binding and new output path. Version 1 accepts comma-
delimited UTF-8 CSV; other delimiters/encodings require an explicit reviewed
conversion with originals retained. There is no locale/type inference. Bind the
normalized result and raw bytes in the comparison as `format: "periscope-normalized"`.
The [source contract](../../omni-artifact-translator/references/periscope-source-contract.md#numerical-normalization-and-case-binding)
defines the exact context fields. Normalization preserves rows; it does not prove
that the source exported the entire intended population.

Freeze/check the return through `migration.py` and the existing standalone or DMA
surface-delivery contract. Include unsupported behavior, deferred assets, incomplete
cases and operational handoffs. Real source capture, native target execution,
rendered quality, effective access and business acceptance remain separate evidence.
Publication, cutover, schedules and source retirement require their own authorization.
