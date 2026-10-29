# ThoughtSpot migration workflow

Invoke [omni-thoughtspot-migrator](../../omni-thoughtspot-migrator/SKILL.md) within
the accelerator. This guide uses source-only first-party tooling; no package
installation, browser automation, source authoring or target publication.

1. Enter the existing execution workflow and qualify the tenant/Org, version,
   principal, licensed capabilities and selected Liveboards/Answers. Register
   source evidence in the engagement. Preserve unavailable and denied objects.
2. Transfer JSON TML and a separately enumerated scope. Build the typed snapshot
   and explicit originals crosswalk described in the [source contract](../../omni-artifact-translator/references/thoughtspot-source-contract.md).
   Keep customer files outside the repository. YAML/unknown input stays opaque.
3. Import originals, check local byte integrity and project the source inventory.
   `thoughtspot_translate` handles a typed supplied snapshot;
   `thoughtspot_import_capture` verifies all retained files before translation.
4. If needed, configure only the reviewed REST operations at source-host startup.
   Metadata enrichment, saved-result queries and renders are different grants.
   Retain outputs, qualify the actual state and reconcile fresh definitions into
   a new capture. Do not retry an uncertain POST or fetch response URLs.
5. Prepare visual requirements, preserving notes, controls, private/missing
   obligations and repeated placements. Assign the source specialist through
   typed evidence, not a product name in a prompt.
6. Complete A–C with access, analysis and a traceable narrative. At D record the
   target experience, quality bar, behavior adaptations and cache/refresh choice.
   At E present exactly three concrete options and obtain the actual user's
   selection before detailed design and F implementation.
7. Reuse current governed Omni fields where suitable. Route actual semantic or
   physical gaps through DMA's normal requirement exchange. No ThoughtSpot DMA
   adapter is assumed. Build separate reviewed native dashboard/App candidates.
8. Bind each comparison to original files, definition, placement, actual state,
   population and freshness. Complete independent visual, interaction, access,
   operational and business checks; retain unobserved lanes in the return.

## Local commands

From the repository root, substitute absolute paths in a private engagement:

```sh
python3 -I -S -B skills/omni-artifact-translator/scripts/thoughtspot_capture.py --help
python3 -I -S -B skills/omni-artifact-translator/scripts/translate_artifact.py \
  --format thoughtspot-api /private-engagement/snapshot.json \
  --output /private-engagement/inventory.json
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private-engagement
```

The default MCP host exposes local `thoughtspot_import_local`,
`thoughtspot_import_evidence`, `thoughtspot_translate`,
`thoughtspot_import_capture`, `thoughtspot_check_capture`,
`thoughtspot_normalize_results` and `thoughtspot_check_mcp`. It exposes no remote
ThoughtSpot capture tool or target-write tool by default.

For reviewed connected enrichment, configure `--thoughtspot-request` and
`--thoughtspot-directory` relative to the engagement, then explicitly enable
`--enable-thoughtspot-capture`. The operator can separately enable
`--enable-thoughtspot-query` and/or `--enable-thoughtspot-render`. Credentials use
the source-only `THOUGHTSPOT_ACCESS_TOKEN` environment variable or an explicitly
selected `THOUGHTSPOT_...` variable; never put secrets in the request or chat.
The host checks the exact request and runtime pins before dispatch. These are
cooperating-host controls, not isolation from an operator controlling Python.

For an existing authorized Spotter connection, retain actual tool schemas and
responses and run `thoughtspot_check_mcp`. The package does not connect, install a
client, choose a model, query a session or create a source dashboard automatically.

## Verification and qualification

Run focused stdlib checks individually:

```sh
python3 -I -S -B scripts/validate_source.py --case thoughtspot-capture
python3 -I -S -B scripts/validate_source.py --case thoughtspot-projection
python3 -I -S -B scripts/validate_source.py --case thoughtspot-host
python3 -I -S -B scripts/validate_source.py --case thoughtspot-mcp
python3 -I -S -B scripts/validate_source.py --case thoughtspot-integration
```

These use original synthetic fixtures and fake transports. They exercise routing,
scope, continuity, numerical context and native guards, not a live migration. A
later pilot needs an actual source tenant, explicit read/query/render permissions,
an Omni development destination and independent acceptance evidence. Skipping
that pilot leaves it unqualified; it does not block source-only package use.
