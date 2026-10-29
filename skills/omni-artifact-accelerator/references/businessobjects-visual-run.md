# BusinessObjects migration workflow

Use [omni-businessobjects-migrator](../../omni-businessobjects-migrator/SKILL.md)
under the existing orchestrator. Identify WebI, Universe and Crystal profiles
before choosing an acquisition path. Follow the
[source contract](../../omni-artifact-translator/references/businessobjects-source-contract.md);
a report name or source URL does not select a target or grant access.

1. Start/resume the engagement with its actual package revision and original
   request. Record version, principal, scope, IDs/CUIDs, evidence and constraints.
2. Retain unmodified UTF-8 responses and an independent selected inventory.
   Build the bounded snapshot with exact raw bytes/hashes and source locators.
   Keep binary files opaque. Reconcile missing elements and provider/model gaps.
3. Import/check/translate locally. Connected metadata is optional and needs a
   trusted host with a qualified exact operation profile; never bypass a denial
   through a browser, downloaded SDK or arbitrary HTTP.
4. Complete A access, B analysis/query expectations and C traceable narrative.
   Select governed Omni reuse or send genuine semantic gaps through
   [DMA cowork](../../omni-backend-handoff/references/cowork-contract.md). Retain
   every affected frontend consumer and unresolved backend requirement.
5. At D resolve fidelity/redesign, target surfaces, audience, quality ambition,
   branding, devices, navigation, print/export/delivery, optional spatial/3D
   visualizations and the independent target caching/refresh question.
6. At E provide exactly three viable concrete concepts and retain the actual
   user's choice. Then complete detailed design and F implementation with
   security, UX, product-owner and QA feedback. A migration role cannot bypass gates.
7. Compare the candidate to the original scope using exact result/state bindings.
   Keep unobserved lanes, unsupported source behavior and release authorization
   separate. Do not retire source reports or create schedules from this workflow.

## Supplied snapshot route

Use an initialized private engagement and existing inputs/contracts folders.
Prepare report-snapshot.json according to the source contract, then:

```sh
python3 -I -S -B skills/omni-artifact-translator/scripts/translate_artifact.py \
  --format businessobjects-api /private-engagement/inputs/report-snapshot.json \
  --output /private-engagement/inputs/report-inventory.json
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project /private-engagement --kind sources \
  --path inputs/report-snapshot.json --id businessobjects-original
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project /private-engagement --kind sources \
  --path inputs/report-inventory.json --id businessobjects-inventory
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private-engagement prepare --original inputs/report-snapshot.json \
  --inventory inputs/report-inventory.json --output contracts/businessobjects-requirements.json
```

Resolve the generated unselected route explicitly. Unknown source obligations
start deferred; unavailable/denied/private scope cannot be migrated. Registering
evidence selects the specialist but does not prove user access or complete A–F.

## Retain original files and add results

With a capture request and originals manifest already prepared:

```sh
python3 -I -S -B skills/omni-artifact-translator/scripts/businessobjects_capture.py import-local \
  /private-engagement/inputs/capture-request.json \
  --source-root /private-engagement/inputs/originals \
  --directory /private-engagement/inputs/source-capture --allow-source-read
python3 -I -S -B skills/omni-artifact-translator/scripts/businessobjects_capture.py check \
  /private-engagement/inputs/source-capture/capture-000001.json
```

The import destination must be new. Retain all numbered revisions.
Use import-evidence with the current capture, a reviewed evidence spec and selected
local source-root to attach existing raw results or images. No URLs are fetched.
Translate the selected revision with --format businessobjects-capture; register
that original and its projection as the selected source pair.

Local MCP tools are businessobjects_import_local, businessobjects_import_evidence,
businessobjects_translate, businessobjects_check_snapshot,
businessobjects_import_capture, businessobjects_check_capture and
businessobjects_normalize_results. All file arguments are engagement-relative.
The normalization tool takes source, profile, binding and output paths.
Use the [connected visual workflow](connected-visual-migration.md) to prepare
source_capture/source_binding and numeric comparison specifications. A raw export
without observed state remains inconclusive.

## Connected metadata host integration

An external trusted host can construct BusinessObjectsCommand(project, request,
directory, authority=callback) and inject it into Bridge(..., businessobjects=...).
The callback receives the exact operation and fingerprints including runtime
source hashes. It must independently qualify the real server/build, user and
allowed side effects before returning X-SAP-LogonToken. Keep credentials out of
files, logs, responses and target Apps. The default CLI exposes no activation flag.

This initial profile does not perform source refresh, rendering, save, cleanup,
schedule changes, folder discovery or Crystal execution. Qualify any added
operation separately; do not reinterpret a file reference as an authority grant.
No live tenant, native target acceptance or full Universe extraction is claimed.

## Source-only verification

Use the existing interpreter:
`python3 -I -S -B scripts/validate_source.py --case NAME`.
Focused cases are businessobjects-projection, businessobjects-capture,
businessobjects-host, businessobjects-integration and metadata.
Neutral fixtures exercise evidence continuity, request denial, source semantics,
numeric binding and DMA/A–F integration; they do not certify a live tenant.
