# Qlik migration workflow

Invoke [omni-qlik-migrator](../../omni-qlik-migrator/SKILL.md) within the current
accelerator engagement. This workflow supports supplied evidence and optional
bounded source rendering; it does not install a Qlik client or publish targets.

1. Qualify the tenant, principal, product/Engine version, selected apps/sheets,
   native/embedded context and access. QlikView and client-managed environments
   cannot inherit Cloud qualification by name. Register the supplied source.
2. Preserve native property responses and a separately enumerated inventory.
   Map original bytes with the [source contract](../../omni-artifact-translator/references/qlik-source-contract.md).
   Keep customer artifacts in the private engagement, outside the repo.
3. Import originals and verify local integrity before projection. Reconcile
   objects, dependencies, repeated placements, controls, private and missing scope.
4. With an existing authorized official Qlik MCP connection, discover actual
   schemas, inspect selected objects and retain calls. The local checker is
   passive. Query and selection-change permissions are separate; read observed
   state after changes. No create/reload/delete/automation operations.
5. For original Engine definitions/results not provided by MCP, use supplied
   QIX responses or a separately approved transport. Isolate sessions, retain
   actual state and requalify after reconnect. Never auto-install a client.
6. If needed, enable the bounded Reports wrapper for selected existing charts
   and sheets. Import the source before startup. Pin exact request/source/runtime
   and journal continuity; render authority does not permit source authoring.
7. Complete A–C before the D interview. Preserve fidelity choices, visual ambition,
   branding, devices, exports and independent cache/refresh policy. At E present
   exactly three concrete viable concepts and record the real user's selection
   before design and F coding. Reuse valid existing decisions.
8. Use existing governed Omni bindings or exchange scoped backend requirements
   with DMA. No Qlik DMA adapter is assumed. Preserve route and source identity,
   grain/security obligations, unknown expressions and independent expectations.
9. Compare qualified source and target populations/state/freshness separately
   from rendering, interaction, effective access and customer acceptance. Deliver
   separate App/dashboard evidence; retain all unobserved lanes.

## Local setup and tools

From the repository root, using an existing Python runtime and private paths:

The capture journal uses the existing POSIX locking profile (macOS/Linux).
A Windows execution host needs separately qualified locking support; do not
disable locking to run it. This host limitation is separate from the source
Qlik deployment being Cloud or client-managed.

```sh
python3 -I -S -B skills/omni-artifact-translator/scripts/qlik_capture.py --help
python3 -I -S -B skills/omni-artifact-translator/scripts/qlik_capture.py import-local \
  --request /private-engagement/inputs/request.json \
  --source-root /private-engagement/inputs/supplied \
  --directory /private-engagement/inputs/capture --allow-source-read
python3 -I -S -B skills/omni-artifact-translator/scripts/qlik_capture.py check \
  --capture /private-engagement/inputs/capture
python3 -I -S -B skills/omni-artifact-translator/scripts/translate_artifact.py \
  --format qlik-api /private-engagement/snapshot.json \
  --output /private-engagement/inventory.json
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private-engagement
```

Default local tools: `qlik_import_local`, `qlik_import_evidence`, `qlik_translate`,
`qlik_import_capture`, `qlik_check_capture`, `qlik_normalize_results`,
`qlik_check_mcp`. They do not establish a remote Qlik connection.

For separately authorized Cloud Reports capture, provide `--qlik-request` and
`--qlik-directory` relative to the engagement, plus `--enable-qlik-capture` and
`--enable-qlik-render`. Credentials come from `QLIK_ACCESS_TOKEN` or an explicitly
selected `QLIK_...` environment variable. Never place credentials in requests,
source manifests, chat, fixtures or logs. These cooperating-host controls do not
isolate an operator controlling the interpreter or replace actual authorization.

After source import and explicit render authorization, the bounded host is:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private-engagement \
  --qlik-request inputs/request.json --qlik-directory inputs/capture \
  --enable-qlik-capture --enable-qlik-render
```

Supply credentials through the approved host environment. The request must select
the implemented Reports profile and operations before import. Do not edit an
imported request to widen scope; prepare a separately reviewed capture instead.
Whole-sheet rendering requires every native child occurrence to be selected and
qualified. A sheet containing a private/excluded chart or unresolved container
requires narrower selected-chart renders or supplied evidence.

An approved external MCP host owns live query/selection grants and OAuth setup;
see [official connection guidance](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/QlikMCP/Connecting-Qlik-MCP-server.htm).
Use vendor/client instructions for the actual deployed client. A repository
skill does not configure a connector automatically or authorize broader scopes.

## Validation

Run focused checks with `python3 -I -S -B scripts/validate_source.py --case NAME`:
`qlik-capture`, `qlik-projection`, `qlik-mcp`, `qlik-host`, `qlik-integration` and
`metadata`. Original synthetic fixtures exercise code and evidence boundaries;
they do not qualify a live migration.

A later pilot needs a selected source tenant/app, actual read/query/render grants,
an Omni development destination and independent expectations. Exercise multiple
sheets, reused master items, a changed selection and alternate state/bookmark
when present, straight/pivot results and an allowed/denied persona. Record a
skipped or unavailable lane as unqualified, not passed. Local package completion
and live tenant acceptance are separate milestones.
