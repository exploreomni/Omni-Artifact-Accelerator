# Use Omni Artifact Accelerator

Start with a business question, a migration source or an existing model. The orchestrator coordinates the relevant specialists and keeps a saved engagement with decisions, editable deliverables and evidence. You can stop at a design handoff or continue to a separately authorized native candidate.

## Installation and updates

Follow [the README quick start](../README.md#quick-start) to clone the repository and create a Python 3.12 virtual environment. Commands below run from the repository root with that environment active. The shell examples target macOS/Linux.

Install all 13 skills together. For Codex, use its skill directory. For another compatible host, choose the directory that host is configured and authorized to read:

```sh
OAA_SKILLS_DIR="$HOME/.codex/skills"
mkdir -p "$OAA_SKILLS_DIR"
python scripts/install_skills.py --destination "$OAA_SKILLS_DIR"
python scripts/install_skills.py --destination "$OAA_SKILLS_DIR" --apply
```

The first command is a preview. Apply leaves identical skills unchanged, installs missing skills and refuses an unrelated or customized existing folder. It does not install Data Model Accelerator or source-platform migrators, configure MCP servers or copy customer evidence.

If an update conflicts, retain the existing copy and inspect the differences. The installer's `--upgrade-from` option requires an exact prior package archive with its verified manifest; it is not a general force-overwrite option. If you do not have that archive, use a fresh approved host directory or reconcile the installation manually. Do not edit installed files while an apply is running. Caught replacement failures are rolled back; a process or machine crash is not an atomic bundle transaction.

Refresh the host's skill discovery. In hosts supporting named skills, start with `$omni-artifact-accelerator`; otherwise ask the agent to read `skills/omni-artifact-accelerator/SKILL.md` from the checkout and follow its sibling references. A role plan does not itself spawn workers—the host must support delegation, or the agent performs the roles inline and states that limitation.

## New dashboard or App

### 1. Create a private engagement

Keep the output outside both the repository and skill installation. The parent directory must exist, and the engagement directory must be new:

```sh
mkdir -p "$HOME/omni-artifact-runs"
OAA_RUN="$HOME/omni-artifact-runs/operations-pilot"
python skills/omni-artifact-accelerator/scripts/analyst_project.py init \
  --output "$OAA_RUN" --name 'Operations pilot' --mode net-new --surface both
python skills/omni-artifact-accelerator/scripts/analyst_project.py plan \
  --project "$OAA_RUN"
```

Choose `dashboard`, `app` or `both`. Use `--mode enhancement` for a change to an existing experience. Resume an engagement by reopening it; do not initialize over its existing files. Helpers reject symlink paths, so use canonical paths and keep all relative file references inside the engagement.

The initial structure is:

| Location | Purpose |
| --- | --- |
| `START_HERE.md` | Current decision, deliverable links, gaps and next action |
| `project.json` | Mode, selected surfaces, source/artifact register and decisions |
| `contracts/` | Working metric, query, design, brand and QA records |
| `inputs/` | Retained source material and imported evidence |
| `tasks/` and `requests/` | Scoped specialist work and backend exchanges |
| `deliverables/` | Editable design and implementation outputs |
| `evidence/` | Versioned checks, observations and findings |

### 2. Give the agent a concrete task

Supply the audience, decision, selected surface, available Omni model/Topics, known definitions and desired completion stage. Reuse prior answers; unresolved metrics need an owner, not an invented definition.

> Use $omni-artifact-accelerator in this engagement to design a native operations dashboard. Supervisors need to spot late orders, compare teams and inspect exceptions. Reuse our existing Omni Topics. Start with metric definitions, chart and filter specifications, brand choices and an independent QA plan. Keep unknown targets and data freshness explicit. Produce a local reviewable handoff; do not write to the tenant yet.

For an App:

> Use $omni-artifact-accelerator to design a native Omni App for capacity planning. Let a viewer choose a region, adjust a clearly hypothetical scenario, inspect the governed baseline and reset. Keep applied results separate from pending inputs. Identify which calculations belong in the model and which are presentation-only. Prepare the task flow and implementation contract before native construction.

For `both`, assign each requirement to dashboard, App or both. Shared metrics can use one governed definition; each surface still needs its own composition, target document and evidence.

### 3. Design and implement the selected scope

The analyst defines meaning and independent examples. Designers create the chart/layout or task/state specification. Branding and design systems establish shared visual roles; storytelling and motion participate when useful. BI and App engineers bind the approved requirements to actual available target capabilities.

Use the [ideation playbook](../skills/omni-design-systems/references/ideation-playbook.md) for material new concepts, [dashboard patterns](../skills/omni-dashboard-designer/references/dashboard-patterns.md) or [App patterns](../skills/omni-app-designer/references/app-patterns.md) for composition, and [usability testing](../skills/omni-qa-analyst/references/usability-testing.md) for task evaluation. A focused edit need not restart discovery. Mark mock data and unimplemented actions clearly; without participants, provide the test script and retain `not_run` status.

When native construction is requested, inspect the actual target and permissions first. Follow [native build/export](../skills/omni-bi-engineer/references/omni-build-export.md) for dashboards and [the native App contract](../skills/omni-app-engineer/references/native-app-contract.md) for Apps. Initial App construction starts from an operator-created workbook-only named draft, inspected governed queries and a reviewed runtime bridge. The helper does not create those prerequisites or certify an invented browser API.

## Migrate an existing experience

Begin with a bounded source scope: one report, Page, dashboard, workbook or analytical workflow. Preserve original files and IDs, independently list all selected objects and retain unsupported behavior. An image is useful appearance evidence; configuration, original results, observed state and permissions supply different evidence.

Create a separate migration engagement:

```sh
OAA_MIGRATION_RUN="$HOME/omni-artifact-runs/migration-pilot"
python skills/omni-artifact-accelerator/scripts/analyst_project.py init \
  --output "$OAA_MIGRATION_RUN" --name 'Migration pilot' \
  --mode migration --surface dashboard
```

Use the [parser coverage matrix](parser-coverage.md) to select the correct reader, then the source-specific guide:

- [Hex](../skills/omni-artifact-accelerator/references/hex-visual-run.md): reporting plus computational App tasks; Classic/Generative provenance, applied inputs and separate surface evidence. Source notebook execution is disabled.
- [Looker](../skills/omni-artifact-accelerator/references/looker-visual-run.md): API or bounded supplied definitions, query dependencies, content, controls and repeated placements.
- [Power BI](../skills/omni-artifact-accelerator/references/powerbi-visual-run.md): independent PBIR inventory, source state, DAX/result evidence and control obligations.
- [Tableau](../skills/omni-artifact-accelerator/references/tableau-visual-run.md): definition/view reconciliation, worksheet placements, actions and typed result evidence.
- [Sigma](../skills/omni-artifact-accelerator/references/sigma-visual-run.md): compatible separately obtained migration-engine output, explicit route and selected visual capture.
- [Domo](../skills/omni-artifact-translator/references/domo-visual-pilot.md): companion migrator evidence, complete Page/Card context and supported visual references.

### Try the offline reader with a synthetic example

This example demonstrates file intake only. It is a tiny supplied Looker API-shaped object, not a customer export or complete migration. It deliberately leaves query, filter, security and layout evidence unavailable.

```sh
cat > "$OAA_MIGRATION_RUN/inputs/sample-dashboard.json" <<'JSON'
{
  "id": "synthetic-dashboard",
  "title": "Synthetic operations overview",
  "dashboard_elements": [
    {
      "id": "synthetic-note",
      "type": "text",
      "title": "Scope note",
      "body_text": "Synthetic example. No customer data or live query."
    }
  ]
}
JSON
python skills/omni-artifact-translator/scripts/translate_artifact.py \
  "$OAA_MIGRATION_RUN/inputs/sample-dashboard.json" --format looker-api \
  --output "$OAA_MIGRATION_RUN/inputs/source-inventory.json"
python skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project "$OAA_MIGRATION_RUN" --kind sources \
  --path inputs/sample-dashboard.json --id source-original-v1
python skills/omni-artifact-accelerator/scripts/analyst_project.py register \
  --project "$OAA_MIGRATION_RUN" --kind sources \
  --path inputs/source-inventory.json --id source-inventory-v1
```

Inspect the inventory and its gaps. Translation saves a bounded projection; it does not create Omni content, establish export completeness or prove equivalent behavior. Use a fresh output filename for a new source version.

For a real pilot, ask:

> Use $omni-artifact-accelerator to migrate the selected source dashboard into a native Omni dashboard. Keep every selected placement, control, content item and unsupported action in the inventory. Preserve metric meaning and the observed source state. Propose clearer labels and layout separately from parity. Reuse our existing Topic where its bindings are compatible; send only actual model gaps to DMA. Start with source inventory, scope and a local candidate plan.

The normal sequence is **inventory → choose route → freeze scope → bind metrics → design/build → compare → review**. Every object receives an explicit migrate/defer/exclude disposition; unsupported does not mean completed. When both surfaces are selected, freeze and reconcile their assignments separately. Follow the [migration lifecycle](../skills/omni-backend-handoff/references/migration-lifecycle.md) for exact scope and return contracts.

Connected acquisition needs its own configured credentials and allowed operations. Retain the whole capture directory, not just its JSON envelope. Do not replace missing attachments with remote paths a host cannot access, execute extracted source code, or silently substitute a different chart interaction.

## Work with Data Model Accelerator

[Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator) owns warehouse and semantic design, implementation and backend validation. This package owns the analyst experience and can use an existing Omni model without requiring DMA.

For an existing DMA delivery, give the orchestrator its curated `omni/SEMANTIC_REVIEW.json`, the saved engagement context and any independent report inventory. Ask the agent to use the [DMA handoff contract](../skills/omni-artifact-accelerator/references/dma-handoff.md). The importer retains a pinned candidate and unresolved definitions; it does not execute the source project or deploy a model.

> Use $omni-artifact-accelerator with this Data Model Accelerator handoff. Preserve the selected domain, route and accepted decisions. Design the requested dashboard and App against the current definitions. Send missing grain, metric or field requirements back through $omni-backend-handoff, with affected assets and independent expected cases. Reconcile returned changes and reopen affected QA; keep backend deployment and frontend acceptance separate.

The exchange is `request → respond → receive → select`. A response accounts for each requirement as proposed, unresolved or declined; selecting it only chooses a local working candidate. Use the [cowork contract](../skills/omni-backend-handoff/references/cowork-contract.md) for exact commands. The [optional saved-state integration](../integrations/data-model-accelerator/README.md) records checked frontend scope/returns as supporting evidence in DMA without replacing its stages or finalizer.

Compatibility is explicit. Read the declared producer revision and schema in the source guide before importing a DMA source inventory. Do not spoof a revision to make a newer producer pass. The current DMA repository and a supported historical producer contract are not automatically interchangeable.

## Brand and reusable assets

The branding specialist reuses existing decisions and asks for the company website URL and approved guidelines, logos, fonts or images when missing. Website observations inform a proposal; they do not establish asset reuse rights or formal brand approval.

> Use $omni-branding for this customer dashboard and App. Use the company website URL and approved assets I supply. Separate observed styling from accepted brand rules, preserve image/font provenance and permissions, and map the shared colors and typography to each supported Omni surface. Keep category colors stable and provide a fallback where an asset cannot load. Produce the brand contract and previews without changing a shared theme.

Use the [brand interview and contract](../skills/omni-branding/references/brand-contract.md). Keep application theme, dashboard/document theme and App CSS mappings distinct. Check actual contrast, font fallback, logo legibility, keyboard focus and reduced motion. Public visibility does not authorize broad crawling or unrestricted asset downloads. Organization-wide theme changes are separate from a local design request.

## Give a specialist a bounded task

The packet helper freezes selected local files for a role. It does not dispatch an agent or inspect whether those files are appropriate to disclose:

```sh
python skills/omni-artifact-accelerator/scripts/analyst_project.py packet \
  --project "$OAA_RUN" --role data-analyst \
  --input contracts/metrics.json \
  --output "$OAA_RUN/tasks/analyst-v1.json"
```

Add `--input` for each relevant slice. Aggregate selected inputs are limited to 256 KiB. The host supplies concrete outputs, dependencies, allowed actions and acceptance conditions, then invokes an available worker or performs the role inline. Keep sensitive content out of unnecessary packets and preserve unavailable dependencies as gaps rather than silently dropping them.

## Verify and hand off

```sh
python skills/omni-artifact-accelerator/scripts/analyst_project.py verify \
  --project "$OAA_RUN"
```

`consistent` means checked structure and recorded file hashes agree. Empty working contracts are reported, and unregistered files are outside this check. It does not mean the design is complete, values are correct, permissions are equivalent, the App works or publication occurred.

A useful handoff contains the editable design/code, metric/query and brand contracts, source-to-target crosswalk, current candidate references, independent numerical and interaction evidence, known gaps and the next action. Keep `START_HERE.md` current. Freeze versioned deliverables before registering them; changing registered bytes is a freshness finding, not an invisible update.

Use [QA and delivery guidance](../skills/omni-artifact-accelerator/references/qa-release.md) to distinguish local checks, native behavior, effective access, usability, business acceptance and publication. A native draft is reviewable work; publication is a separate action. Reconcile uncertain writes before retrying and preserve unrelated editors' work.

## Host configuration and troubleshooting

The optional local stdio host is `skills/omni-artifact-accelerator/scripts/visual_mcp.py`. Discover its arguments locally:

```sh
python skills/omni-artifact-accelerator/scripts/visual_mcp.py --help
```

Configure only the source request, target documents and exact candidate operations authorized for the engagement. Dashboard writes, existing-App edits and initial App creation have separate grants. Tokens belong in approved secret channels, never prompts, source JSON, command arguments or committed files. See the [connected workflow](../skills/omni-artifact-accelerator/references/connected-visual-migration.md) and the selected source guide for host-specific steps.

| Symptom | Next step |
| --- | --- |
| Skill is not discovered | Check the host's configured skill directory, refresh discovery and confirm all sibling folders were installed. Reading the orchestrator directly is a local fallback. |
| Installer reports customization | Inspect and preserve the existing folder; use a supported exact-baseline upgrade or a fresh approved directory. |
| Helper rejects a path or existing output | Use canonical paths without symlinks and a new output filename; keep relative evidence paths inside the engagement. |
| YAML dependency is unavailable | Activate the prepared environment and install its reviewed requirements; do not install dependencies declared by customer exports. |
| Comparison is inconclusive | Inspect source state, identity, complete result coverage and persona/data-time evidence. Matching rows alone cannot fill missing provenance. |
| Native capability or runtime bridge is unavailable | Continue the local specification and provide an explicit operator handoff. Do not invent an API or change the requested surface. |
| Claude/ChatGPT cannot run the local host | Use a configuration with local process/file support or an explicit operator-assisted transfer. Installing this repository does not create a remote connector. |

For package checks, optional integration dependencies and contributor test commands, see [Testing](TESTING.md).
