# Omni Artifact Accelerator

An analyst's sidekick for designing, building and reviewing **native Omni dashboards and native Omni Apps**. The package brings together 13 specialist skills, source migration readers and local workflow helpers so an AI agent can carry a business question through design, implementation and independent QA.

Start with an existing Omni model, bring an exported BI experience, or continue from the companion [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator). Use only the specialists the task needs.

## What you can do

- **Design a new dashboard:** define the decision, metrics, charts, filters and brand, then prepare a native candidate and review evidence.
- **Build an analytical App:** design a task flow with governed queries, inputs, scenario state and recovery behavior.
- **Migrate an existing experience:** preserve source identities, calculations, controls, layout intent and unresolved behavior while making deliberate design improvements.
- **Coordinate frontend and backend work:** send specific model gaps to Data Model Accelerator and reconcile its versioned response without repeating discovery.
- **Create a consistent customer experience:** reuse approved logos, images, fonts and color semantics across the selected dashboard and App surfaces. Supply your official website and preferred logo file/URL, authorize sourcing its logo, or explicitly choose no logo; the package reuses that decision.

This is a skill bundle for an agent host, not a standalone BI service. Skills define roles; the host runs the agent and supplies its tools. The local helpers manage files, evidence and bounded operations—they do not launch a permanent team of agents or connect accounts automatically.

## Control quality without a fixed template

The [control-craft guide](skills/omni-design-systems/references/control-craft.md) helps specialists choose buttons, selects, search, navigation and responsive columns by task. Shared behavior and semantic tokens preserve consistency; each engagement retains its own composition and brand treatment.

1. Reuse the audience, brand, data scope and chosen experience. Identify the affected controls.
2. Record their purpose, hierarchy, applicable states, scope, keyboard/return behavior and available-space rules in the existing design contract.
3. Use the [original control studio](skills/omni-app-engineer/assets/control-studio.html) and [implementation reference](skills/omni-app-engineer/references/control-primitives.md) selectively. The examples contain synthetic data and do not connect to Omni.
4. Bind real queries through the reviewed native adapter; review one complete affected journey before expanding. Retain separate source, rendered and native evidence.

For example: “Build a branded operations App where I can search supplied records, narrow the scope, inspect evidence and return without losing my selection. Choose controls and layout for that task; preserve partial-data and access boundaries.” The same principles guide native dashboard filter placement and labels through supported settings; custom App CSS is not a dashboard extension.

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

The initial files and role plan are a starting point, not a built dashboard or App. Add `--branding requested --website https://example.com` for a branded engagement, `--branding none` when branding is out of scope, or leave it unknown. The editable design-intent record retains missing required choices; a website alone does not choose a logo. See [saving intent and reviewing named requirements](skills/omni-artifact-accelerator/references/design-intent.md) for current design/brand/asset selection and per-surface completion. Continue with [the step-by-step how-to](docs/HOW_TO.md).

Material new designs include a reasoned direction, comparison where it resolves uncertainty, a resolved design handoff, and designer review of the actual implementation. The optional [design evidence checker](skills/omni-qa-analyst/references/design-evidence.md) tracks which observations still match the current candidate; it does not certify visual quality or customer acceptance.

For an App, describe the intended experience as well as the metrics. For example: “Create an immersive branded entry that leads into a focused product investigation workspace, with persistent scope and a separate comparison view.” The [experience-mode guide](skills/omni-app-designer/references/app-patterns.md#choose-the-experience-mode) helps distinguish this from a direct workspace or a guided data story. If rendering is unavailable, the agent should retain that visual-review gap explicitly.

Give the usable App width **and height** when known, including space occupied by Omni controls. For branded demos, specify whether source names should remain original or may use explicitly fictional aliases; logo permission alone does not decide that. The [data-input guide](skills/omni-app-engineer/references/native-data-input.md) keeps exported rows distinct from the native callback contract, while [presentation naming](skills/omni-branding/references/demo-presentation.md) preserves original IDs and arithmetic. See [context and resume](docs/HOW_TO.md#keep-context-current) for checking an older handoff before work continues.

## Start from one useful brief

> Create a polished investigation App from our existing Omni model for regional operations leaders. Use our supplied company website and approved assets. Give returning users a direct path to investigate a change and inspect its evidence. Choose an appropriate visual direction, preserve data scope through navigation, and adapt to phone, laptop and wide screens. Reuse our prior answers; ask one short batch only for material missing context. Build and critique a complete journey before expanding it, then review every working destination. Keep unavailable runtime capabilities explicit. Prepare the candidate in our existing development workflow.

The [first-delivery workflow](skills/omni-artifact-accelerator/references/first-delivery.md) turns that brief into named behavior, owners and dependencies. The agent refines the result internally; a single prompt does not mean a single generation. `experience-check` reports declared coverage and `plan` routes capabilities to existing roles. The App engineer can load an [advanced visualization module](skills/omni-app-engineer/references/advanced-visualization.md) for custom scenes. It is conditional, not a requirement to use 3D or add more agents.

A new design review checks the selected destinations, applicable contexts and journeys against the full declared scope. A polished opening cannot hide an unreviewed working area. Focused edits report their bounded scope; historical reviews without these bindings remain readable with destination coverage unassessed. The checker tracks evidence coverage, while actual rendered critique establishes visual observations.

For each substantial working view, the designer resolves its dominant subject, useful first state, supporting comparison and detail/return path. The review checks whether controls and explanatory text bury the main evidence, whether entity roles receive appropriate measures, and whether selections survive both ordinary and exceptional return paths. [Craft review](skills/omni-design-systems/references/visual-craft.md) keeps these decisions distinct from a fixed template and from passing numerical checks.

Reusable behavior does not impose a visual template. The [interaction controllers](skills/omni-app-engineer/references/experience-behaviors.md) provide identity, selection/return, recorded-time and calendar mechanics; each engagement owns its layout, typography, imagery, density and choreography. The [original behavior studio](skills/omni-app-engineer/assets/behavior-studio.html) presents one investigation through two different structures. Use [portable assembly](skills/omni-app-engineer/references/portable-assembly.md) to combine chosen sources without inheriting a tenant, query count, page structure or brand.

> Build a useful analytical experience for our stated audience and task. Choose the composition from our data and brand requirements; reuse interaction mechanics where helpful. Record why the chosen form fits. Compare alternatives only where they resolve uncertainty, and review the actual implementation. An existing example is guidance, not the required layout.

Before evaluating a new package version, verify the installed files:

```sh
python scripts/install_skills.py --destination "$OAA_SKILLS_DIR" --verify
```

A matching result identifies the compared source version and file manifest. Missing, changed and extra files stay visible; the command makes no changes and does not prove the host has reloaded cached skills.

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

## Develop distinctive data experiences

The [Data Experience Design Studio](skills/omni-design-systems/references/experience-curriculum.md) gives all 13 roles a shared curriculum for analytical judgment, art direction, advanced visual encoding, storytelling, dashboard composition, App interactions, motion, branding, implementation and critique. It teaches agents through worked choices and revision instead of prescribing one house layout.

The installed [experience brief](skills/omni-design-systems/references/experience-brief.md) carries quality expectations into named design choices, first/returning-use journeys and specialist handoffs. Try the [context-transfer studio](skills/omni-design-systems/references/experience-context-studio.md) and its [interactive synthetic specimen](skills/omni-design-systems/assets/experience-context-studio.html) to compare three frontend treatments of the same library investigation. These are original local teaching artifacts, not native Omni content or a required house layout.

Start with one relevant exercise:

1. Read the curriculum's role route and choose the competency the task needs.
2. Work through an [original studio](skills/omni-design-systems/references/experience-studios.md), or use the same method on an authorized engagement. The [interactive teaching specimen](skills/omni-design-systems/assets/experience-studio.html) runs locally with invented data and no external dependencies; download/open the file to explore it. It is not a native Omni artifact.
3. Select a visual structure from the [pattern atlas](skills/omni-design-systems/references/experience-patterns.md), state its data prerequisites and compare it with a simpler alternative.
4. Resolve the design, implement the relevant slice, and use the [critique rubric](skills/omni-design-systems/references/experience-review.md) to make a specific revision. Keep the designer involved through the actual target where permitted.
5. For deliberate training, repeat in a different domain and record the work actually reviewed. Installing lessons makes them available; it does not certify every agent or guarantee native quality.

> Use the Data Experience Design Studio for a performance dashboard and an investigation App. Develop distinct tasks and compositions from the same governed metrics. Compare a change-and-contribution design with a comparison atlas, resolve a clear visual direction, and propose one useful App interaction with purposeful motion and a reduced-motion equivalent. Reuse our brand answers. Keep native capability gaps explicit and have the designer critique the implemented result.

The curriculum uses neutral pattern names and original practice data. Its guidance supports polished static dashboards and expressive Apps without treating animation or unusual chart types as requirements. Load only the relevant lessons for normal work. If a user limits the workflow to CLI/MCP and prohibits browser rendering, continue the authorized work and report visual/native interaction checks as unrun.

Read [design context and decisions](docs/design-context-and-decisions.md) for a worked account of why a branded App still felt like a generic dashboard, how an explicit experience choice changed its composition and navigation, and what every specialist needs to preserve. It distinguishes missing decisions from requirements that were already supplied but lost during the handoff.

## From a local candidate to native delivery

For a substantial new experience, expect **direction → comparison when useful → a resolved screen design → native implementation → designer critique → revision**. The dashboard and App should serve distinct tasks even when they share metrics. Reuse the supplied website, brand authority and any explicit no-research decision. Ask for a website only when a material branding need remains unresolved; turn the selected brand characteristics into composition choices and retain image/font provenance and fallback behavior. A small correction uses focused checks; a faithful migration keeps its original behavior obligations.

> Create a native service-performance dashboard and an exception-investigation App from our existing Omni model. Use our supplied website and brand guide. Compare compositions where the direction is unresolved, resolve desktop and narrow views, and keep the designer involved through the native render. Make detail interactions add useful evidence. Report numerical, craft, native interaction and human-testing results separately.

See [design and implementation](docs/HOW_TO.md#3-design-and-implement-the-selected-scope) for the review workflow and evidence checks. Correct numbers, a saved screenshot and a published document establish different things; none alone establishes a polished, usable experience.

Local planning and source inspection need no Omni credentials. Native work needs separately configured, authorized source/target access, verified API or CLI capabilities and an appropriate development draft. The native helpers and local stdio host use POSIX facilities; macOS/Linux is the supported execution environment described here.

The dashboard adapter works on an existing named development draft. The App path supports reviewed edits to an existing query-backed App, plus a separate initial-construction operation on an existing workbook-only named draft with inspected queries and a reviewed native runtime bridge. It does not automatically create documents, queries or a proprietary browser SDK. See [native dashboard construction](skills/omni-bi-engineer/references/omni-build-export.md) and [the App contract](skills/omni-app-engineer/references/native-app-contract.md).

For new documents or a configured credential type outside those adapters, follow the [bounded native authoring guide](skills/omni-artifact-accelerator/references/native-authoring.md). It documents the official tool route, draft/readback requirements, complete tile replacement and App API limits without weakening existing adapter safeguards.

Close out with the selected requirements, what is visible/working on each surface, and any unresolved choice or difference. Publication does not erase an unmet design requirement, and a frontend design summary does not accept DMA semantics. Keep these outcomes distinct: **local consistency → native behavior and access checks → business acceptance → publication**. A screenshot cannot prove the numbers or permissions; an API readback cannot prove the App ran correctly. Selecting both surfaces requires distinct target documents and separate evidence. Publication and operational changes need their own authorization.

Claude and ChatGPT tool support depends on the actual host/account configuration. The included [local host workflow](skills/omni-artifact-accelerator/references/connected-visual-migration.md) does not provision a remote connector or give a web chat access to a local process. A clearly recorded operator-assisted file workflow remains available where direct integration is unavailable.

[How to use the package](docs/HOW_TO.md) · [Parser coverage](docs/parser-coverage.md) · [Testing](docs/TESTING.md) · [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator)
