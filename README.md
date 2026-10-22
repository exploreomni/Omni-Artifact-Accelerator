# Omni Artifact Accelerator

An analyst's sidekick for designing, building and reviewing **native Omni dashboards and native Omni Apps**. The package brings together 13 specialist skills, source migration readers and local workflow helpers so an AI agent can carry a business question through design, implementation and independent QA.

Start with an existing Omni model, bring an exported BI experience, or continue from the companion [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator). Use only the specialists the task needs.

## What you can do

- **Design a new dashboard:** define the decision, metrics, charts, filters and brand, then prepare a native candidate and review evidence.
- **Build an analytical App:** design a task flow with governed queries, inputs, scenario state and recovery behavior.
- **Migrate an existing experience:** preserve source identities, calculations, controls, layout intent and unresolved behavior while making deliberate design improvements.
- **Coordinate frontend and backend work:** send specific model gaps to Data Model Accelerator and reconcile its versioned response without repeating discovery.
- **Create a consistent customer experience:** reuse approved logos, images, fonts and color semantics across the selected dashboard and App surfaces.

This is a skill bundle for an agent host, not a standalone BI service. Skills define roles; the host runs the agent and supplies its tools. The local helpers manage files, evidence and bounded operations—they do not launch a permanent team of agents or connect accounts automatically.

## Quick start

These commands use a macOS/Linux shell. **Python 3.12 is the recommended, tested runtime.** You also need Git and an agent host that can read skills and local files. Node.js is optional for ordinary Python helper use; controller testing needs Node.js 18 or later. No npm setup is required.

### 1. Get the package

```sh
git clone https://github.com/exploreomni/Omni-Artifact-Accelerator.git
cd Omni-Artifact-Accelerator
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

The dependency file installs the pinned PyYAML version used for YAML source definitions. Keep customer data, tokens and engagement outputs outside this repository.

### 2. Install the skills

For Codex, preview the changes and then apply them:

```sh
OAA_SKILLS_DIR="$HOME/.codex/skills"
mkdir -p "$OAA_SKILLS_DIR"
python scripts/install_skills.py --destination "$OAA_SKILLS_DIR"
python scripts/install_skills.py --destination "$OAA_SKILLS_DIR" --apply
```

For another compatible host, set `OAA_SKILLS_DIR` to its **approved skill directory** and use the same commands. Keep all 13 sibling folders together so their shared references resolve. Copying files alone does not configure a host's tool access or skill discovery.

Preview makes no installation changes. Apply installs missing skills, leaves identical copies unchanged and refuses conflicting or customized copies. Review the preview before applying; do not delete customizations to force an update. See [installation and updates](docs/HOW_TO.md#installation-and-updates).

Refresh your host's skill discovery or start a new conversation, then invoke `$omni-artifact-accelerator` in a host that supports that syntax. Otherwise, ask the agent to read [the orchestrator skill](skills/omni-artifact-accelerator/SKILL.md) from this checkout.

### 3. Create a local engagement

From the repository root with the virtual environment active:

```sh
python skills/omni-artifact-accelerator/scripts/analyst_project.py --help
mkdir -p "$HOME/omni-artifact-runs"
OAA_RUN="$HOME/omni-artifact-runs/operations-pilot"
python skills/omni-artifact-accelerator/scripts/analyst_project.py init \
  --output "$OAA_RUN" --name 'Operations pilot' --mode net-new --surface both
python skills/omni-artifact-accelerator/scripts/analyst_project.py plan \
  --project "$OAA_RUN"
```

Use a new output directory; initialization does not overwrite an existing engagement. Choose `dashboard`, `app` or `both`. Open the generated `START_HERE.md`, then give the agent a concrete task:

> Use $omni-artifact-accelerator for a service operations dashboard and App in this engagement. Reuse our existing Omni Topics. The dashboard should explain current performance; the App should help a viewer inspect an exception and its supporting data. Ask only for missing metric, audience, interaction and brand decisions. Start with a reviewable local design and QA plan. Do not write to the tenant yet.

The initial files and role plan are a starting point, not a built dashboard or App. Continue with [the step-by-step how-to](docs/HOW_TO.md).

## Choose a workflow

| Starting point | Next step |
| --- | --- |
| Business question and existing Omni model | [New dashboard or App](docs/HOW_TO.md#new-dashboard-or-app) |
| Existing report, dashboard or analytical App | [Migration workflow](docs/HOW_TO.md#migrate-an-existing-experience) |
| Reviewed backend model or a missing metric | [Data Model Accelerator collaboration](docs/HOW_TO.md#work-with-data-model-accelerator) |
| Customer website, brand guide or existing theme | [Brand and reusable assets](docs/HOW_TO.md#brand-and-reusable-assets) |
| Developer validation or contribution | [Testing](docs/TESTING.md) |

For migrations, choose the documented source path before exporting or running anything:

| Platform | Supported starting point | Guide |
| --- | --- | --- |
| Hex | Supplied native exports, bounded definition/existing-run image capture, transferred results and DMA producer evidence | [Hex dashboard and App workflow](skills/omni-artifact-accelerator/references/hex-visual-run.md) |
| Looker | Supplied API/dashboard definitions, bounded capture and typed DMA producer evidence | [Looker workflow](skills/omni-artifact-accelerator/references/looker-visual-run.md) |
| Power BI | Supplied PBIR/Fabric definitions, bounded source capture and DMA evidence | [Power BI workflow](skills/omni-artifact-accelerator/references/powerbi-visual-run.md) |
| Tableau | Supplied definitions, bounded REST or official-MCP evidence and DMA enrichment | [Tableau workflow](skills/omni-artifact-accelerator/references/tableau-visual-run.md) |
| Sigma | Outputs from a separately obtained, compatible migration engine and its visual capture | [Sigma workflow](skills/omni-artifact-accelerator/references/sigma-visual-run.md) |
| Domo | Selected companion-migrator evidence plus original configuration and visual references | [Domo pilot](skills/omni-artifact-translator/references/domo-visual-pilot.md) |
| Other sources | Explicitly reviewed manual evidence inventory | [Inventory contract](skills/omni-artifact-translator/references/inventory-contract.md#normalized-inventory) |

Read [parser coverage](docs/parser-coverage.md) for exact formats and limitations. A supported reader is not a universal chart or formula converter. Missing source objects, custom visualizations, interactions and security dependencies remain visible work.

## The 13 roles

| Skill | Owns |
| --- | --- |
| `omni-artifact-accelerator` | Orchestration, shared scope, decisions and integrated handoff |
| `omni-data-analyst` | Metric meaning, investigation and independent expected results |
| `omni-bi-engineer` | Governed query bindings, controls and native dashboard construction |
| `omni-app-engineer` | Native App implementation and runtime behavior |
| `omni-app-designer` | Task flows, screens, interaction states and responsive behavior |
| `omni-dashboard-designer` | Layout, chart selection, hierarchy and exploration |
| `omni-qa-analyst` | Independent numerical, interaction, visual, access and performance checks |
| `omni-data-storyteller` | Evidence-backed titles, annotations and decision guidance |
| `omni-motion-designer` | Purposeful feedback and reduced-motion equivalents |
| `omni-branding` | Customer identity, approved assets, fonts and theme mappings |
| `omni-design-systems` | Reusable design rules, tokens and accessibility expectations |
| `omni-artifact-translator` | Original source inventory, behavior mapping and migration gaps |
| `omni-backend-handoff` | Versioned DMA exchanges, current bindings and change-impact review |

Each specialist can also be invoked directly. Design guidance draws from official Apple, Google, Microsoft, Samsung and other primary sources, with platform-specific advice distinguished from package recommendations. See [design foundations](skills/omni-design-systems/references/vendor-guidance.md).

## From a local candidate to native delivery

Local planning and source inspection need no Omni credentials. Native work needs separately configured, authorized source/target access, verified API or CLI capabilities and an appropriate development draft. The native helpers and local stdio host use POSIX facilities; macOS/Linux is the supported execution environment described here.

The dashboard adapter works on an existing named development draft. The App path supports reviewed edits to an existing query-backed App, plus a separate initial-construction operation on an existing workbook-only named draft with inspected queries and a reviewed native runtime bridge. It does not automatically create documents, queries or a proprietary browser SDK. See [native dashboard construction](skills/omni-bi-engineer/references/omni-build-export.md) and [the App contract](skills/omni-app-engineer/references/native-app-contract.md).

Keep these outcomes distinct: **local consistency → native behavior and access checks → business acceptance → publication**. A screenshot cannot prove the numbers or permissions; an API readback cannot prove the App ran correctly. Selecting both surfaces requires distinct target documents and separate evidence. Publication and operational changes need their own authorization.

Claude and ChatGPT tool support depends on the actual host/account configuration. The included [local host workflow](skills/omni-artifact-accelerator/references/connected-visual-migration.md) does not provision a remote connector or give a web chat access to a local process. A clearly recorded operator-assisted file workflow remains available where direct integration is unavailable.

[How to use the package](docs/HOW_TO.md) · [Parser coverage](docs/parser-coverage.md) · [Testing](docs/TESTING.md) · [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator)
