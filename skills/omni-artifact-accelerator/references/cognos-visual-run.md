# Cognos report migration workflow

Use [omni-cognos-migrator](../../omni-cognos-migrator/SKILL.md) under the current
orchestrator. This route converts supplied report evidence into migration
requirements. It does not capture a live tenant, execute source reports or publish
an Omni artifact.

1. Record the original request and actual package revision through the existing
   execution procedure. Identify Cognos version, source origin when known,
   principal, report ID/content path and requested scope. Select native Omni
   dashboard, App or both independently of the source artifact's name.
2. Obtain the original report specification through an authorized source owner,
   plus an independently enumerated expected inventory and identity references.
   Retain unmodified UTF-8 XML outside the repo. For dashboards, keep supplied
   specifications/screenshots/behavior notes as manual evidence; do not disguise
   them as report XML or invent a connected acquisition command.
3. Import using the [source contract](../../omni-artifact-translator/references/cognos-source-contract.md),
   then check the snapshot and project its requirements. Reconcile queries,
   pages, prompt pages, containers, repeated placements, controls and dependencies
   against the independent inventory. Missing/unknown scope stays visible.
4. Complete A access, B analysis and C narrative with actual permitted evidence.
   Static XML does not establish access or observed query results. Reuse governed
   Omni bindings and send genuine gaps through existing DMA cowork; no Cognos
   producer or model compiler is supplied.
5. At D resolve fidelity/redesign, audience, quality ambition, official brand
   assets, devices, exports, navigation and visualization preferences. For Apps,
   ask the user's cache/refresh/expiry policy, including a valid no-custom-policy
   answer. Carry the same resolved policy through E design and F implementation/QA.
6. Present exactly three concrete viable concepts and record the actual user
   choice before detailed design and coding. Use existing A–F gates in all new
   engagements; reuse current accepted evidence when continuing an existing one.
7. Review the candidate against the original request and source obligations.
   Keep numerical, interaction, visual, access, accessibility, performance,
   publication and business acceptance separate. Automatic numerical parity from
   this route remains inconclusive until a result binding is qualified.

## Local walkthrough

Use the existing local MCP bridge with a private engagement directory:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private-engagement
```

Prepare original XML and a metadata JSON file containing `identity`, `inventory`
and `reference`, following the source contract. Use `cognos_import_report` with
`source` (XML path), `metadata` (metadata JSON path), and `output` (snapshot path).
Paths are engagement-relative. Then call `cognos_check_snapshot` with the snapshot
`source`, and `cognos_translate` with `source` and an `output` inventory path.
These are local file operations, with no network authority or credentials.

For CLI-only intake, first retain the XML and then translate its snapshot. If a
valid snapshot was already supplied, skip the import command:

```sh
python3 -I -S -B skills/omni-artifact-translator/scripts/cognos_import.py \
  /private-engagement/inputs/report.xml \
  --metadata /private-engagement/inputs/report-metadata.json \
  --output /private-engagement/inputs/report-snapshot.json
python3 -I -S -B skills/omni-artifact-translator/scripts/translate_artifact.py \
  --format cognos-report /private-engagement/inputs/report-snapshot.json \
  --output /private-engagement/inputs/report-inventory.json
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project /private-engagement --kind sources \
  --path inputs/report-snapshot.json --id cognos-original
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project /private-engagement --kind sources \
  --path inputs/report-inventory.json --id cognos-inventory
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private-engagement prepare --original inputs/report-snapshot.json \
  --inventory inputs/report-inventory.json --output contracts/cognos-requirements.json
```

Use an already initialized engagement and existing output directories. The
importer never overwrites a file. Generated requirements start with an unselected
route: resolve it and retain its decision reference before continuation. Registering
source evidence selects the specialist; it does not satisfy access or design gates.
Unresolved source objects start deferred. Promoting one to migration requires a
specific `scope_decision` reason/reference; the generated deferral reference is
not a review decision. Unavailable, denied and unselected private scope remains
blocked until the original source evidence and scope are properly revised.

Continue through the existing [visual migration workflow](connected-visual-migration.md)
and [execution procedure](execution-workflow.md). Source scope, preparation,
comparison and coverage do not bypass stage gates or authorize a target write.
Retain `source.cognos_result_binding_unqualified` in comparison evidence; do not
substitute a matching screenshot or parser success for numerical parity.

A live pilot, connected source transport, dashboard specification adapter,
result normalization and native target validation are separate qualification
work. Keep those limits visible when delivering this local implementation.

Local source-only checks use the existing runtime and first-party fixtures:
`python3 -I -S -B scripts/validate_source.py --case NAME`, with
`cognos-projection`, `cognos-host`, `cognos-integration` or `metadata`.
They do not establish live access, rendered fidelity or business acceptance.
