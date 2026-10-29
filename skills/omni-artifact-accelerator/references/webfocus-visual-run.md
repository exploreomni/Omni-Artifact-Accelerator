# WebFOCUS migration run

Use [omni-webfocus-migrator](../../omni-webfocus-migrator/SKILL.md) in the existing
engagement. This route joins passive source evidence with shared analysis, design,
backend handoff and native QA. It is not a whole-tenant converter or procedure runner.

## Qualify and prepare

Follow [execution startup](execution-workflow.md) and [A–F](stage-gates.md). Record
the actual package source, target, installed WebFOCUS version, authoring origin,
principal, selected resources and prior decisions. Separate source reads, source
execution, native writes and publication. All new migrations still require exactly
three concrete design options and the actual user selection before code.

Read the [source contract](../../omni-artifact-translator/references/webfocus-source-contract.md)
and selected [competencies](../../omni-webfocus-migrator/references/source-competencies.md).
Obtain original files plus independently enumerated expected content, placements and
controls. Preserve standalone reports, pages/sections/containers, reused reports,
custom code and operational outputs. Ask only for missing facts. A customer need
not rebuild a warehouse when existing Omni bindings satisfy the requirements.

Keep source material in a private engagement outside this package. The commands
below use /installed and /private/run as placeholders for approved paths. They do
not authorize installing or loading a dependency. Source-only helpers use the
existing Python standard library and bundled first-party code.

Prepare a request plus originals, inventory and crosswalk records using the source
contract. An optional DMA report must match the exact supported producer revision
and original-file hashes. Example minimal original manifest entry:

```json
{
  "source_path": "application/operations.fex",
  "kind": "fex",
  "encoding": "utf-8",
  "sha256": "<actual SHA-256 of the supplied original bytes>",
  "reference": "<source export evidence>"
}
```

This is an illustrative entry, not a ready-to-run capture. Use real IDs/references,
never replace unknown source facts with the example. The executable validators
reject missing shapes, conflicting scope and malformed pins. Opaque CM ZIP inventory
does not supply a decoded page manifest; retain its independent scope separately.

## Import and verify original evidence

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/webfocus_capture.py \
  import-local --request /private/run/inputs/webfocus-request.json \
  --source-root /private/run/inputs/supplied \
  --directory /private/run/inputs/webfocus-capture --allow-source-read
python3 -I -S -B /installed/omni-artifact-translator/scripts/webfocus_capture.py \
  check --capture /private/run/inputs/webfocus-capture
```

This retains original bytes in a new private directory. No source code, included
procedure or HTML is executed. Use the actual journal path returned by the helper.
The following examples illustrate a returned capture-000001.json; do not overwrite
or rename journals or assume that suffix remains current.

Attach approved local reference outputs with webfocus-supplied-evidence.v1:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/webfocus_capture.py \
  import-evidence --capture /private/run/inputs/webfocus-capture/capture-000001.json \
  --spec /private/run/inputs/webfocus-evidence.json \
  --source-root /private/run/inputs/exports
```

Record actual prompt/filter state, principal, preview/aggregation/limit context,
population, freshness and completeness. PNG/PDF appearance and CSV/JSON numbers are
separate evidence. Missing observations remain unknown; never open imported scripts
or invoke a report merely to fill a capture gap.

## Optional bounded repository enrichment

Before local import, include separately reviewed operations in the request. Each
operation identifies one canonical /WFC/Repository path and one allowed action.
The initial host supports only get, getContent and properties under /ibi_apps. It
does not bootstrap broad discovery or decode every vendor export format. Imported
crosswalk and selected operations must match; new scope requires a new request.

After the operator configures the source credential in the approved environment,
start the local stdio host with that exact imported request:

```sh
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private/run --webfocus-request inputs/webfocus-request.json \
  --webfocus-directory inputs/webfocus-capture --enable-webfocus-capture
```

WEBFOCUS_SESSION is the default environment-variable name; --webfocus-token-env
selects another WEBFOCUS_... name. Its value is the approved Cookie or Authorization
header value chosen in api_contract, never a CLI argument, source file or chat value.
No automatic login, third-party client or remote vendor MCP is installed.

Call webfocus_capture with resume true. This reads only the fixed startup scope;
tool arguments cannot change paths, actions or credentials. Success means requested
operations were acquired, not that the exported visual inventory is complete or
current. Responses enrich evidence and never silently replace imported definitions.
Source run/runAdHocFex and metadata-description operations with unqualified behavior
remain disabled. A GET method is not authorization to execute a procedure.

Local tools are webfocus_import_local, webfocus_import_evidence, webfocus_translate,
webfocus_import_capture, webfocus_check_capture and webfocus_normalize_results.
Discover schemas from the host. They use engagement-relative paths. The local
helper CLI exposes no connected capture command.

## Project and resolve requirements

For a supplied DMA report, use webfocus-adapter and the actual qualified producer
revision. For a capture, verify it first and preserve its complete directory:

```sh
python3 -I -S -B /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/webfocus-capture/capture-000001.json \
  --format webfocus-capture --output /private/run/inputs/webfocus-inventory.json
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run prepare \
  --original inputs/webfocus-capture/capture-000001.json \
  --inventory inputs/webfocus-inventory.json --output contracts/visual.json
python3 -I -S -B /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run check --requirements contracts/visual.json
```

prepare creates work to resolve, not a complete migration. It preserves report
obligations, the independent object set and repeated placements, even when parsing
is partial. The bare translator only checks structure; shared workflow and MCP
capture import also reverify original files. Explicitly resolve migrate/defer/exclude
scope, route, query/control bindings and target surfaces.

Use [DMA cowork](../../omni-backend-handoff/references/cowork-contract.md) for actual
semantic/physical gaps with source_platform webfocus, original pins, frontend IDs
and independent cases. Keep the selected producer and dependency-complete slice;
do not execute dynamic procedures to manufacture a model. Existing Omni topics can
be reused through a current typed baseline. A returned candidate is not deployment.

## Design, build and assess

After access, analysis and narrative, conduct product discovery. Preserve the
quality bar, official branding/website answers, native surface and selected visual
ambition. Ask the App [refresh/cache/expiry question](../../omni-product-owner/references/data-refresh-policy.md)
at D and retain the actual choice in E/F. Source cache and preview settings do not
impose target timers. All three options share the accepted analytical scope.

The [BI engineer](../../omni-bi-engineer/SKILL.md) and
[App engineer](../../omni-app-engineer/SKILL.md) own target implementation. Use current
native query/control contracts and separate dashboard/App candidates and receipts.
The source specialist has no target writer and cannot waive the design-selection
gate. Browser/rendering restrictions do not lower the design bar or authorize a
headless workaround; unobserved lanes stay pending.

Normalize results using explicit profiles and exact capture bindings, then use
visual_workflow compare and coverage for candidate-bound evidence. Include preview
mode and limit stage, DEFINE/COMPUTE totals, original rows, applied prompts,
Auto Linking/drills, page navigation, exports, allowed/denied personas and stale-data
recovery. Read [behavior handoff](../../omni-webfocus-migrator/references/behavior-handoff.md).
Equal numbers cannot override missing source context or placement application.

Freeze/return through the existing [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md).
Retain adaptations, opaque dependencies, operational/ReportCaster work and actual
business-review status. Source retirement, scheduling and publication need separate
authority. No live tenant is required for package implementation; real source/native,
rendering, effective access and business acceptance remain separately unqualified.

## Maintained local checks

From the repository root, use the existing interpreter without third-party startup
imports. These original fixtures/fake transports do not contact live services:

```sh
python3 -I -S -B scripts/validate_source.py --case webfocus-bridge
python3 -I -S -B scripts/validate_source.py --case webfocus-capture
python3 -I -S -B scripts/validate_source.py --case webfocus-integration
python3 -I -S -B scripts/validate_source.py --case webfocus-host
```

Check package metadata/links and affected Metabase/Periscope paths when shared
integration changes. Additional synthetic tests do not replace a tenant pilot.
