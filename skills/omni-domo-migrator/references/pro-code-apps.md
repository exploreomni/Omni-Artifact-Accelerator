# Migrate a Domo Pro Code App

Use this path when the original request, a reviewed design, or the selected instance identifies a Pro Code or custom JavaScript App. Domo supports authoring through the Pro-Code Editor and the App Framework. Capture the method used, the design ID and version, and each selected installed App or Card instance with its placement. A generic “App” label or the companion reader’s App Studio placeholder leaves the family unverified. A Pro Code component embedded in App Studio can require both the custom source and the surrounding page configuration. [Domo Apps overview](https://www.domo.com/docs/portal/Apps/Overview) · [Pro-Code Editor](https://www.domo.com/docs/portal/Apps/Pro-Code-Editor/getting-started-pro-code)

## Start with retained evidence

Reuse the current migration engagement, source selection, treatment and approved access. Check existing registered source files, verified typed captures and the customer’s approved project or design export. Use an existing connected route for any exact read it already supports. For a selected Pro Code App the companion’s general metadata reader can leave a manual placeholder. Request only the missing design files, instance wiring or source observation needed for the next decision. Domo documents a design download by ID and version using its Apps CLI. If an authorized operator supplies that export, retain the exact version and design ID with the originals. Domo’s default download version is `latest`. [Domo Apps CLI download](https://www.domo.com/docs/portal/Apps/App-Framework/Tools/domo-CLI#download)

For example, save the following as `inputs/domo-intake.json` in the private engagement. Replace the illustrative ID and paths with retained originals. If a file or the instance ID is unavailable, leave the corresponding asset or ID out. An empty `pro_code_assets` list starts a partial plan.

```json
{
  "schema_version": "oaa-domo-intake.v1",
  "app_family": "pro_code",
  "source": {},
  "scope": {"app_ids": ["selected-instance-id"], "include_portfolio": false},
  "target": {},
  "pro_code_assets": [
    {"app_id": "selected-instance-id", "kind": "manifest", "path": "inputs/design/manifest.json"},
    {"app_id": "selected-instance-id", "kind": "source", "path": "inputs/design/index.html"},
    {"app_id": "selected-instance-id", "kind": "source", "path": "inputs/design/app.js"}
  ]
}
```

Register the intake before preparing the generic project plan. Reuse its existing registration when it already identifies these bytes.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project "$OAA_MIGRATION_RUN" --kind sources --path inputs/domo-intake.json --id domo-app-intake
```

From a terminal in the checkout, run the local planner. This uses supplied files and works when the Accelerator’s visual MCP tools are absent from the chat.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py domo-plan-source \
  --project "$OAA_MIGRATION_RUN" --spec inputs/domo-intake.json --output contracts/domo-source-plan.json
```

Alternatively, call `domo_plan_source` through the engagement’s existing local visual MCP host. Both entry points use the same planner. Choose one and use a new output path when preparing a revision.

```json
{"spec":"inputs/domo-intake.json","output":"contracts/domo-source-plan.json"}
```

Read `pro_code_source` in the output. `assets` contains file hashes, bounded HTML control hints and manifest declarations. A `read_pinned_source_for_details` entry retains the original file and identifies the omitted sections for scoped inspection. `coverage` reports which of the four optional input kinds were supplied for each selected App. Add `instance_wiring` and `source_observation` using scoped JSON, text or CSV evidence when available. Use the [typed capture](../../omni-artifact-translator/references/domo-evidence-contract.md) for supported screenshots, original result files, detail and versioned component inventory. Keep an unknown operational assignment explicit on a partial capture until its scope is established.

## Recover the source behavior

| Evidence | What to inspect and retain |
| --- | --- |
| Design and installed instance | Pin the original manifest, authored HTML/JS/CSS, entry point and relevant assets. Map design version, placement, embed context and actual installed instance. Review dynamic UI construction and opaque bundles as source evidence. The local planner inspects individual supplied files and never executes them. |
| Data wiring | In `datasetsMapping`, retain each design alias, declared `dataSetId`, and field `alias` → `columnName`. Resolve the installed instance’s actual DataSets and columns separately. Inspect reads, queries, aggregation, ordering, limits, pagination, and date grain. Empty field mappings can expose original column names. [Manifest fields and wiring](https://www.domo.com/docs/portal/Apps/App-Framework/Guides/manifest) · [Getting data](https://www.domo.com/docs/portal/Apps/App-Framework/Guides/getting-data) |
| Controls and interactions | Trace each input from its visible label and initial state through its handler to affected queries and components. Capture exemptions, propagation, persistent state, navigation, reset and empty states. Check the installed SDK version and its actual calls. The documented `onFiltersUpdated` can clear page filters on its first registration, so passive inspection is appropriate even for apparent listeners. Capture declared broadcast channels and the installed publisher/subscriber wiring when sibling Apps respond. [Domo.js](https://www.domo.com/docs/portal/Apps/App-Framework/Tools/domo-js) · [Manifest channels](https://www.domo.com/docs/portal/Apps/App-Framework/Guides/manifest#channels) |
| Access and operational behavior | Retain the viewing principal, effective PDP/share restrictions, field exposure, and any denied, drill or export paths. Classify AppDB reads/writes, workflow starts, files, external services and failure/retry behavior individually. Keep actual operational ownership and supported target behavior explicit. [AppDB](https://www.domo.com/docs/portal/API-Reference/app-framework-apis/AppDB-API) |
| Target bindings | Bind the source behavior to inspected Omni fields, queries and native controls. Keep Domo runtime code inert and build against the selected target’s supported bridge. Use existing target documentation and evidence to prepare the candidate. If a material callback remains uncertain after inspection, identify that exact boundary and continue independent work. A dummy App or blanket console-log request adds no source evidence. |

## Verify the controls on the candidate

For a dealer selector and a date range, compare matched source/target totals under the default state, dealer only, date only, both controls, and reset. Retain actual IDs, interval boundaries and timezone, accessible dealer population, affected and exempt outputs, and the same source/target persona or documented mapping. A display label or HTML element only identifies a potential control. Its effect requires observed outputs. Include repeated placements, empty selections and any applicable denied case.

Carry the source views, named controls and independent expectations into the [migration fidelity baseline](../../omni-artifact-accelerator/references/migration-fidelity.md). Include each declared Pro Code input file in that baseline’s evidence paths. The engineering handoff rechecks those file pins against the approved baseline, forwards their identity and remaining coverage, and reopens source review when the bytes change. Preserve uses one source-matched specification. Redesign retains the same analytical scope and records each approved change. Missing evidence stays visible in the comparison, including when a dashboard or an App shell renders successfully.
