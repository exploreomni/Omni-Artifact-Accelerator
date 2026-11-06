# Omni Artifact Accelerator

An analyst's sidekick for designing, building and reviewing **native Omni dashboards and native Omni Apps**, with a design and implementation-preparation foundation for **native Reports Beta**. The package brings together role-specific skills, source migration readers and local workflow helpers so an AI agent can carry a business question through design, implementation and independent QA.

Start with an existing Omni model, bring an exported BI experience, or continue from the companion [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator). Use only the specialists the task needs.

**Current package: [0.40.0](package.json), with 30 registered skills.** Run it through
your approved AI host using a repository checkout or an already approved skill
installation. The host supplies model execution, connections and native-write
authorization; this repository supplies the workflow, specialist guidance and
local helpers.

When DMA has already built the Topic, [start the artifact from that Topic](skills/omni-backend-handoff/references/topic-first.md). The accelerator verifies the user and destination, maps supported panels to saved workbook queries and returns missing measures to the model owner.

**New to the tool? [Take the self-guided introduction](docs/training/README.md)** — six short lessons covering setup, the agent workflow, design choices, delivery review and migrations. Each lesson ends with an observable checkpoint; you can start learning without installing anything.

| Your goal | Start here |
| --- | --- |
| Set up a local engagement | [Quick start](#quick-start) |
| See what the current release adds | [Current App release workflow](#current-app-release-workflow) |
| Understand what the agents do | [Meet the responsibilities](docs/training/01-understand.md#meet-the-responsibilities) |
| Start your first engagement | [Prepare your source, access and brief](docs/training/02-prepare.md) |
| Choose a design or review a result | [Choose the experience](docs/training/04-choose.md) · [Review and deliver](docs/training/05-review.md) |
| Resume, migrate or use a backend handoff | [Continue the work](docs/training/06-continue.md) |
| Find source migration coverage | [Choose a workflow](#choose-a-workflow) |
| Prepare or publish native content | [Native delivery routes](#from-a-local-candidate-to-native-delivery) |

## See the agent flow

![Agent flow: your approved AI host runs the orchestrator through A access, B analysis, C narrative, D discovery, E three visual concepts and your selection, then F implementation with security, UI/UX, product-owner and independent QA review. Migration and backend handoffs are conditional; publication requires separate authorization and verification.](docs/training/assets/agent-flow.svg)

[Open the full-size diagram](docs/training/assets/agent-flow.svg) · [Read the text walkthrough](docs/training/03-data-and-story.md#the-a-f-sequence)

The boxes represent responsibilities, not a mandatory agent swarm. The orchestrator keeps the current engagement and gives specialists only the context their tasks need. Your actual concept selection and resolved design precede product coding; dependency activation and native publication retain separate controls.

## Current App release workflow

New engagements containing an App use the [candidate release contract](skills/omni-artifact-accelerator/references/app-release.md):

| Area | Current behavior |
| --- | --- |
| Loaded package and host | [Entry preflight](skills/omni-artifact-accelerator/references/engagement-entry.md#inspect-the-host-entry-first) compares the reported loaded source with the requested release and inventories write routes. The default host status is advisory; real enforcement needs independent host verification. |
| Experience selection | Three visual concepts show a first view, primary action and useful result. The actual choice, including requested elements from other options, follows the engineer into the selected design. A deliberate monitoring overview remains valid. |
| Visible data | A reviewed manifest binds live values to queries and callbacks, labels snapshots and scenarios, and retains independent expectations. Refresh completion follows query outcomes and the user's selected freshness policy. |
| Native release | The reviewed candidate includes the HTML and relevant query/settings evidence. Whole-draft publication checks the complete frozen draft; an optional operator-integrated write gate requires exact-action authorization and retains uncertain outcomes for reconciliation. |

These checks preserve the chosen experience without prescribing a layout. Source
checks, rendered critique, exercised interactions, effective access and publication
readback have separate results. A passing source check does not establish visual
quality or host-wide enforcement, and this package does not change Omni's own
App/dashboard routing.

Existing engagements retain their recorded policies. To adopt these App checks,
follow the [explicit adoption procedure](skills/omni-artifact-accelerator/references/app-release.md):
retain the analytical evidence and refresh affected design/review checkpoints.
Updating the checkout alone does not upgrade an old engagement or reload a host's
cached skills.

## Reduce repeated context and review work

New CLI engagements use bounded specialist briefings by default. The orchestrator
retains the complete requirements; workers receive their scoped evidence and shared
constraints. Saved results and active tasks are reused when their bindings remain
current. Corrections carry a usable baseline and changed evidence without nesting
the entire conversation again.

The optional incremental review policy preserves unchanged product choices across
staffing changes and allows proven unchanged source-review coverage to carry forward.
It starts in observation mode; existing engagements keep their recorded rules.
All four review perspectives remain accountable. Unknown impact, changed data/access,
and unobserved rendered/native behavior still require the appropriate checks.

Follow the [incremental work guide](skills/omni-artifact-accelerator/references/incremental-work.md)
for adoption, packet preparation, preflight, correction limits and usage reporting.
Byte counts are not token bills; actual host savings require attributable usage.

The [host-neutral execution interface](skills/omni-artifact-accelerator/references/host-execution.md)
provides a small MCP/CLI surface for the existing lifecycle. Select only the tools
needed for the engagement. An operator-supplied adapter can launch and reconcile
bounded workers with durable attempt tracking; the package does not automatically
install an adapter or connect accounts. Local tests do not establish host isolation.

[Execution efficiency](skills/omni-artifact-accelerator/references/execution-performance.md)
adds effective-configuration reporting, recoverable task preparation, bounded result
reads and local measurements. Read-only checks reuse verified inputs within one
operation and shorten status locking. Models, reasoning settings and quality gates
remain unchanged; the alternative context layout is opt-in, and measured savings
are separate from local correctness checks.

Use the [qualification catalog](skills/omni-artifact-accelerator/references/execution-qualification.md)
to keep actual host, native, visual, access and human evidence separate.
[Explicit result bindings](skills/omni-artifact-accelerator/references/analytical-evidence.md)
prevent positional field guesses and require independent source provenance for
migration comparison. [Assembly provenance](skills/omni-artifact-accelerator/references/assembly-provenance.md)
retains reproducible component inputs and exact final bytes for scoped corrections.
The [demo preparation route](skills/omni-artifact-accelerator/references/native-demo-qualification.md)
retains pending observation gaps without granting publication or weakening release checks.

## What you can do

- **Design a new dashboard:** define the decision, metrics, charts, filters and brand, then prepare a native candidate and review evidence.
- **Build an analytical App:** design a task flow with governed queries, inputs, scenario state and recovery behavior.
- **Prepare a page-precise Report:** specify physical pages, grouping, totals and distinct PDF/Excel outputs; qualify the beta native authoring interface before implementation. See the [report workflow](skills/omni-artifact-accelerator/references/report-workflow.md).
- **Migrate an existing experience:** preserve source identities, calculations, controls, layout intent and unresolved behavior while making deliberate design improvements.
- **Coordinate frontend and backend work:** send specific model gaps to Data Model Accelerator and reconcile its versioned response without repeating discovery.
- **Create a consistent customer experience:** reuse approved logos, images, fonts and color semantics across the selected dashboard and App surfaces. Supply your official website and preferred logo file/URL, authorize sourcing its logo, or explicitly choose no logo; the package reuses that decision.

This is a skill bundle for an agent host, not a standalone BI service. Skills define roles; the host runs the agent and supplies its tools. The local helpers manage files, evidence and bounded operations—they do not launch a permanent team of agents or connect accounts automatically.

## How a new product is created

The [data-first product workflow](skills/omni-artifact-accelerator/references/data-first-product-workflow.md)
sets the order, while leaving the product's visual design open:

1. **Verify data and access.** Establish that the requested data exists and the user can access it.
2. **Analyze.** Profile relevant sources, build governed queries and derive supported insights and questions.
3. **Create the analytical story.** Link claims to evidence and define how they update or disappear when data, filters or freshness change.
4. **Discover the artifact requirements.** Use those findings for product/brand needs, the first useful action, returning-user needs, visual treatment, devices and data freshness. Reuse answers already supplied; ask the comparison-style follow-up only when relevant.
5. **Choose among three products.** Review three distinct, feasible visual concepts with the same analytical scope and accepted quality ambition. App concepts show the first view and action outcome. Select a direction, including any requested combination; specialists preserve that choice and resolve its detailed design.
6. **Build and refine.** Implement a cohesive candidate and obtain security, UI/UX, product-owner and independent QA coverage after every iteration, with scoped reuse under the optional incremental policy.

Existing selected products and focused fixes reuse prior evidence and decisions.
Publication follows its own authorization and verification. The [executable stage gates](skills/omni-artifact-accelerator/references/stage-gates.md)
block missing/stale predecessors in package entrypoints. In the explicit
**conversation-evidence workflow**, your actual chat reply is recorded against the
exact three options; resolved design is still required before coding. This is
agent-attested workflow evidence, not independently authenticated approval. The
strict host-verifier policy remains available and never falls back automatically.
Conversation evidence cannot authorize installations or native writes. Hosts must also
control direct shell/file/API routes; these helpers are not a sandbox or proof of
visual quality. Using Omni's CLI/API does not implicitly invoke
Omni AI/Blobby.

## Start in your agent host

For **Claude Code**, read [CLAUDE.md](CLAUDE.md); for **Codex**, read [AGENTS.md](AGENTS.md).
Both enter the same orchestrator. For **Claude or ChatGPT connected chat**, explicitly
ask the host to retrieve the orchestrator and relevant sibling guidance:

> Use the Omni Artifact Accelerator from this repository for my requested artifact.
> Start with its orchestrator and execution entry procedure. Confirm which revision
> and files you can read, preserve my original request, and assign experience,
> branding, semantics, implementation and independent review responsibilities.
> Follow the data-first A–F workflow: verify my data/access, analyze governed queries
> and create a reusable narrative before artifact discovery. Present three viable
> product options and wait for my selection before detailed design and coding.
> Build cohesively, retain all four review perspectives each iteration, and report
> actual evidence separately from unobserved behavior.

A repository URL alone does not activate skills. Missing repository/tool access is
a stated limitation, not permission to install anything. See the [execution procedure](skills/omni-artifact-accelerator/references/execution-workflow.md)
for repository-only, installed and connected routes. No host-specific route has
universal enforcement or implied qualification.

For a local repository-only start, use [explicit engagement entry](skills/omni-artifact-accelerator/references/engagement-entry.md)
to bind the exact checkout, declared host and existing sibling engagement. The host
must read that entry explicitly. Missing access can remain a recorded blocker;
preparation does not install code, configure tools or grant execution authority.

The local `run-start`, `run-guidance`, `phase-check`, `candidate-freeze` and
`delivery-check` commands preserve source provenance, stage-appropriate
responsibilities, first candidate bytes and current evidence. Record startup before
the first new stage. Choose the actual checkout, a pinned clean revision or verified
latest main explicitly, or an explicit offline snapshot bound to its manifest;
`source-check` can read the configured HTTPS origin without
fetching or activating code. A source mismatch never triggers installation or an
automatic update. See the [exact entry procedure](skills/omni-artifact-accelerator/references/execution-workflow.md#record-startup-and-ownership).
These augment existing intent and QA records. They do not run
specialists, approve a dependency, or turn a published candidate into a polished,
runtime-verified artifact. A host without gate execution can collect evidence and
present options; a host with the helpers can continue local implementation using
the recorded chat-choice workflow. Native execution retains separate controls. An unrun gate is
not a passing gate.

## Preserve product intent through the workflow

The [product owner](skills/omni-product-owner/SKILL.md) recovers existing answers at
intake. For new products, artifact questions follow verified access, analysis and
the reusable narrative. It keeps attributable notes in the private engagement,
coordinates the three-option decision and hands prioritized requirements back to
the orchestrator. Focused repairs reuse current intent without another interview.

New non-report `init` engagements require a sourced or explicitly delegated D
experience promise through [experience continuity](skills/omni-artifact-accelerator/references/experience-continuity.md).
Creative mode proposals can remain open until the existing E choice; no second
interview is required. A dashboard or single-view workspace is valid when it fits
the task. PO and UI/UX fit review cover all promised outcomes and consequential
destinations/journeys; the representative slice is an early checkpoint, not complete
coverage. Bounded packets retain relevant promises and dependencies without changing
the configured model, team size or dependency authority.

The readable **North Star** is generated from the existing selected design intent;
it is not a second authoritative brief. `product-brief` creates its versioned view,
and `product-check` detects stale or edited projections. See the
[product-intent guide](skills/omni-artifact-accelerator/references/product-intent.md).
Product-fit, independent creative critique, security and correctness reviews remain
separate. After user selection, build an ambitious representative journey as part
of the cohesive implementation; unsupported technology must not silently reduce
the intended outcome. The product choice does not confer installation or
publication authority, and no fixed visual template or visual certification is implied.

## Guide the visual experience

After analysis and narrative, the [guided interview](skills/omni-product-owner/references/visual-experience-discovery.md)
asks how people should explore the supported data: compare/track, locations, objects
or environments, movement/flow, imagery, or a useful mix. If comparisons or trends
are included and styling is unanswered, it asks about dimensional styling, interactive
3D, refined 2D, or an explicitly designer-recommended mix. You need not choose an
engine or prescribe every chart. Existing answers are reused; a family recommendation
alone does not delegate styling.

For example:

- “Create an operations App for comparing service delays and monthly trends. Use a light, futuristic dimensional treatment with exact values and visible missing observations.” This supplies a treatment preference before discovery; the agent should reuse it.
- “Recommend the experience families and choose all visual treatments within our brand and native dashboard capabilities. Bring me three product concepts.” This explicitly delegates treatment while retaining the actual product-choice step.
- “Use refined 2D for the comparisons. Prioritize typography, annotation and quick drill/return.” Depth and camera controls are not required for a premium result.

The agent shows **exactly three distinct feasible products**, each honoring current
preferences, the same analytical scope and quality ambition, then waits for your choice before detailed
design and coding. A styling answer does not choose the product, install a renderer
or authorize a different surface. The selected experience receives the existing four
candidate reviews. Each concept includes a representative visual and explicit
quality coverage; three prose pitches do not meet this requirement. Under CLI-only
constraints, an original static SVG can make a concept concrete while remaining
unrendered evidence. Human judgment still determines whether the alternatives are
meaningfully different and well crafted.

[Dimensional craft](skills/omni-design-systems/references/dimensional-visualization-craft.md)
and [original SVG/JSON specimens](skills/omni-design-systems/assets/dimensional-specimens/specimens.json)
make the options concrete through signed bars, gapped trends, layered series and
inspection storyboards in different art directions. These are source-only synthetic
illustrations, not built chart runtimes or observed visual/native quality. CLI/API-only
work retains those unobserved lanes; no browser, package or Blender workaround is implied.

## Control quality without a fixed template

The [control-craft guide](skills/omni-design-systems/references/control-craft.md) helps specialists choose buttons, selects, search, navigation and responsive columns by task. Shared behavior and semantic tokens preserve consistency; each engagement retains its own composition and brand treatment.

1. Reuse the audience, brand, data scope and chosen experience. Identify the affected controls.
2. Record their purpose, hierarchy, applicable states, scope, keyboard/return behavior and available-space rules in the existing design contract.
3. Use the [original control studio](skills/omni-app-engineer/assets/control-studio.html) and [implementation reference](skills/omni-app-engineer/references/control-primitives.md) selectively. The examples contain synthetic data and do not connect to Omni.
4. Bind real queries through the reviewed native adapter; review one complete affected journey before expanding. Retain separate source, rendered and native evidence.

For example: “Build a branded operations App where I can search supplied records, narrow the scope, inspect evidence and return without losing my selection. Choose controls and layout for that task; preserve partial-data and access boundaries.” The same principles guide native dashboard filter placement and labels through supported settings; custom App CSS is not a dashboard extension.

## Keep live data and freshness explicit

New App candidates include a [visible-data manifest](skills/omni-app-engineer/references/native-data-input.md)
with the reviewed HTML. It distinguishes three kinds of displayed evidence:

| Displayed evidence | Required connection |
| --- | --- |
| Live value | Exact saved query, selected Topic/fields, query state and callback binding, plus an independent expectation |
| Snapshot | Visible snapshot label, period and source; it cannot silently replace a failed live result |
| Scenario or estimate | Visible label, declared base data and explicit assumptions |

At discovery, record the user's cache and refresh preferences; keeping ordinary
Omni caching with no custom policy is valid. The package adds no default polling,
expiry timer or cache bypass. The query coordinator updates declared consumers,
including later panels, and reports refresh success only when required results
have completed. Real callbacks, numerical comparisons, access and visible updates
still need observation in the target App; a source manifest alone cannot prove them.

## Model objects and environments

The [3D specialist](skills/omni-3d-modeler/SKILL.md) and [eight-module curriculum](skills/omni-design-systems/references/3d-curriculum.md) support product inspection, fictional venues, buildings, vehicles and operational systems through task-driven geometry and interaction. They do not impose a stadium, brand, camera tour or page template.

Try: “Design an illustrative equipment inspection App using our governed asset IDs. Compare a useful spatial treatment with a simpler diagram. Preserve exact values, keyboard access and missing-data states. Prepare the model brief and bounded original SceneSpec; do not acquire packages or execute customer assets.”

The separate [modeling harness](harness/README.md) supplies original procedural geometry, strict untextured GLB validation, a dependency-free WebGL viewer and a portable data/state adapter. Three synthetic fixtures demonstrate an assembly, courtyard and material-transfer environment. Geometry source and structural checks are implemented; **host isolation, asset promotion, native integration and rendered visual qualification remain pending**. Execution fails closed until an approved isolated host exists. The harness is not installed with the skills.

That optional off-browser harness is not required for every 3D App. The [execution-route guide](skills/omni-app-engineer/references/spatial-integration.md#select-the-execution-route) also supports original procedural scenes authored in Omni's native App sandbox, with reviewed code and target qualification. Loading external libraries or model assets still follows explicit package approval and resource policy.

The [native procedural scene framework](skills/omni-app-engineer/references/native-scene-framework.md) includes original geometry and texture recipes, camera/session lifecycle, responsive host wiring, plain inspection controls and an optional governed-data bridge. Use it for an environment, product inspection or operational network without prescribing one App template. Decorative scenes need no dummy metrics. The Three.js adapter is **source only**: dependency acquisition/loading and native rendering remain unqualified and require exact approvals. Nothing installs or loads an engine automatically.

Try: “Create an illustrative equipment inspection App using our existing brand and governed asset query. Give geometry stable part IDs, show exact readings outside the canvas, preserve the view on refresh, and make camera movement optional. Use the simplest useful spatial treatment and identify missing dimension or runtime evidence.” Follow the [native scene workflow](docs/HOW_TO.md#native-procedural-scene-workflow); unobserved outcomes remain unrun.

## Quick start

Use an existing approved Python runtime for source-only work. **Package installation,
third-party imports, updates and skill activation require explicit scoped sign-off.
No Blender code or execution is permitted.** Read the
[package-use policy](skills/omni-artifact-accelerator/references/dependency-policy.md).
Setup in this release is guided through the steps below and your host's connection
mechanism; an automatic first-launch wizard or credential-file generator is not included.

### 1. Review the source

Obtain an authorized checkout, then run the original standard-library package checker:

```sh
cd Omni-Artifact-Accelerator
python3 -I -S -B scripts/check_package.py
```

`-I -S` prevents user/site package startup in this source-only path. It is not an OS sandbox. The checker does not need PyYAML. `requirements.txt` still records PyYAML 6.0.3 for optional YAML readers; it is neither an installation instruction nor a grandfathered approval. Keep customer data, tokens and outputs outside this repository.

The package checker is enough for this source/setup step. Developers can run
affected cases through `scripts/validate_source.py --case <case>` using the same
isolated Python flags; see [testing](docs/TESTING.md). Those checks exercise local
contracts, without installing packages or contacting a tenant. The current GitHub
workflow is manual-only and records a revision; it does not run validation.

### 2. Choose a repository or installed-skill entry

For repository-only use, have the host read [AGENTS.md](AGENTS.md) or
[CLAUDE.md](CLAUDE.md), then [the orchestrator skill](skills/omni-artifact-accelerator/SKILL.md)
in this checkout. This route requires no skill installation.

If you use an existing approved skill directory, you can preview its differences:

```sh
OAA_SKILLS_DIR="$HOME/.codex/skills"
python3 -I -S -B scripts/install_skills.py --destination "$OAA_SKILLS_DIR"
```

Preview and `--verify` are read-only. **`--apply` is disabled** until a qualified host approval gate is supplied. Do not bypass it by copying into an active skills directory. Installation/update approval must cover the exact source and target; an agent-written approval flag is insufficient. The registered sibling skill folders belong together once activation is authorized. See [installation and updates](docs/HOW_TO.md#installation-and-updates).

Configure the tools needed for your chosen route; native writes require separate authorization.

### 3. Create a local engagement

Run these commands from the repository root. The example creates a private sibling
folder, as required by the [repository entry helper](skills/omni-artifact-accelerator/references/engagement-entry.md).
These commands use original source and the Python standard library:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py --help
OAA_RUN="$(dirname "$PWD")/operations-pilot"
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py init \
  --output "$OAA_RUN" --name 'Operations pilot' --mode net-new --surface both \
  --selection-policy conversation-evidence-v1
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py plan \
  --project "$OAA_RUN"
```

Use a new sibling directory name; initialization does not overwrite an existing
engagement. Choose `dashboard`, `app`, `report` or `both`. Here `both` means a
dashboard and an App; Reports Beta uses its [separate preparation workflow](skills/omni-artifact-accelerator/references/report-workflow.md).
Open the generated `START_HERE.md`, then give the agent a concrete task:

> Use $omni-artifact-accelerator for a service operations dashboard and App in this engagement. Reuse our existing Omni Topics. The dashboard should explain current performance; the App should help a viewer inspect an exception and its supporting data. Ask only for missing metric, audience, interaction and brand decisions. Start with a reviewable local design and QA plan. Do not write to the tenant yet.

The initial files and role plan are a starting point, not a built dashboard or App. Add `--branding requested --website https://example.com` for a branded engagement, `--branding none` when branding is out of scope, or leave it unknown. The editable design-intent record retains missing required choices; a website alone does not choose a logo. See [saving intent and reviewing named requirements](skills/omni-artifact-accelerator/references/design-intent.md) for current design/brand/asset selection and per-surface completion. Continue with [the step-by-step how-to](docs/HOW_TO.md).

### 4. Establish source and access before starting A–F

Ask the host to prepare the [engagement entry](skills/omni-artifact-accelerator/references/engagement-entry.md)
and record `run-start` before the first artifact stage. Supply your original brief,
Omni instance, model/Topic references and whose access should be verified. The host
records the actual package, available tools and task responsibilities; `plan` above
only proposes role assignments.

Local planning needs no Omni credentials. For source or native calls, configure
credentials through your approved CLI/MCP/API or secret mechanism. Share identifiers
in chat and keep secret values and generated evidence outside the repository.
The package does not create accounts, issue API keys or configure remote connectors.
See [access preparation](docs/training/02-prepare.md) and the
[CLI configuration boundary](skills/omni-bi-engineer/references/omni-build-export.md#local-cli-trust-boundary).

All new engagements, including migrations, include the A–C analytical handoff, artifact discovery, three viable options, actual user selection, a resolved design and all four review perspectives on each implementation iteration. Focused continuation reuses existing valid decisions under its recorded policy. The optional [design evidence checker](skills/omni-qa-analyst/references/design-evidence.md) tracks which observations still match the current candidate; it does not enforce A–F, certify visual quality or authenticate customer acceptance.

For an App, describe the intended experience as well as the metrics. For example: “Create an immersive branded entry that leads into a focused product investigation workspace, with persistent scope and a separate comparison view.” The [experience-mode guide](skills/omni-app-designer/references/app-patterns.md#choose-the-experience-mode) helps distinguish this from a direct workspace or a guided data story. If rendering is unavailable, the agent should retain that visual-review gap explicitly.

Give the usable App width **and height** when known, including space occupied by Omni controls. For branded demos, specify whether source names should remain original or may use explicitly fictional aliases; logo permission alone does not decide that. The [data-input guide](skills/omni-app-engineer/references/native-data-input.md) keeps exported rows distinct from the native callback contract, while [presentation naming](skills/omni-branding/references/demo-presentation.md) preserves original IDs and arithmetic. See [context and resume](docs/HOW_TO.md#keep-context-current) for checking an older handoff before work continues.

## Start from one useful brief

> Create a polished investigation App from our existing Omni model for regional operations leaders. Use our supplied company website and approved assets. Give returning users a direct path to investigate a change and inspect its evidence. Choose an appropriate visual direction, preserve data scope through navigation, and adapt to phone, laptop and wide screens. Reuse our prior answers; ask one short batch only for material missing context. Build and critique a complete journey before expanding it, then review every working destination. Keep unavailable runtime capabilities explicit. Prepare the candidate in our existing development workflow.

The [first-delivery workflow](skills/omni-artifact-accelerator/references/first-delivery.md) turns that brief into named behavior, owners and dependencies. The agent refines the result internally; a single prompt does not mean a single generation. `experience-check` reports declared coverage and `plan` routes capabilities to existing roles. The App engineer can load an [advanced visualization module](skills/omni-app-engineer/references/advanced-visualization.md) for custom scenes. Actual object or environment modeling routes to `omni-3d-modeler` through the optional `spatial-modeling` capability. Neither custom visualization nor a premium brief automatically requires 3D.

Before fixing the scope of a substantial design, the agent inventories useful source depth, dates/populations, comparisons and details rather than stopping at the first working query. `source-inventory` retains that evidence; `delivery-project` produces an unselected requirement-coverage proposal from explicit decisions; `delivery-evidence-template` keeps unobserved checks visible. See the [execution steps and examples](skills/omni-artifact-accelerator/references/execution-workflow.md). These helpers preserve the requested ambition without prescribing pages, charts or a visual template.

A new design review checks the selected destinations, applicable contexts and journeys against the full declared scope. A polished opening cannot hide an unreviewed working area. Focused edits report their bounded scope; historical reviews without these bindings remain readable with destination coverage unassessed. The checker tracks evidence coverage, while actual rendered critique establishes visual observations.

For each substantial working view, the designer resolves its dominant subject, useful first state, supporting comparison and detail/return path. The review checks whether controls and explanatory text bury the main evidence, whether entity roles receive appropriate measures, and whether selections survive both ordinary and exceptional return paths. [Craft review](skills/omni-design-systems/references/visual-craft.md) keeps these decisions distinct from a fixed template and from passing numerical checks.

Reusable behavior does not impose a visual template. The [interaction controllers](skills/omni-app-engineer/references/experience-behaviors.md) provide identity, selection/return, recorded-time and calendar mechanics; each engagement owns its layout, typography, imagery, density and choreography. The [original behavior studio](skills/omni-app-engineer/assets/behavior-studio.html) presents one investigation through two different structures. Use [portable assembly](skills/omni-app-engineer/references/portable-assembly.md) to combine chosen sources without inheriting a tenant, query count, page structure or brand.

> Build a useful analytical experience for our stated audience and task. Choose the composition from our data and brand requirements; reuse interaction mechanics where helpful. Record why the chosen form fits. Compare alternatives only where they resolve uncertainty, and review the actual implementation. An existing example is guidance, not the required layout.

For an installed-skill evaluation, verify the installed files. For a repository-only
blind test, use its working-tree manifest and do not consult installed copies:

```sh
python3 -I -S -B scripts/install_skills.py --destination "$OAA_SKILLS_DIR" --verify
```

A matching result identifies the compared source version and file manifest. Missing, changed and extra files stay visible; the command makes no changes and does not prove the host has reloaded cached skills.

## Choose a workflow

| Starting point | Next step |
| --- | --- |
| Business question and existing Omni model | [New dashboard or App](docs/HOW_TO.md#new-dashboard-or-app) |
| Existing report, dashboard or analytical App | [Migration workflow](docs/HOW_TO.md#migrate-an-existing-experience) |
| Reviewed backend model or a missing metric | [Data Model Accelerator collaboration](docs/HOW_TO.md#work-with-data-model-accelerator) |
| A page-precise newsletter or paginated report | [Native Reports Beta preparation](skills/omni-artifact-accelerator/references/report-workflow.md) |
| Customer website, brand guide or existing theme | [Brand and reusable assets](docs/HOW_TO.md#brand-and-reusable-assets) |
| Developer validation or contribution | [Testing](docs/TESTING.md) |

For migrations, choose the documented source path before exporting or running anything:

| Platform | Supported starting point | Guide |
| --- | --- | --- |
| Hex | Supplied native exports, bounded definition/existing-run image capture, transferred results and DMA producer evidence | [Hex dashboard and App workflow](skills/omni-artifact-accelerator/references/hex-visual-run.md) |
| Looker | Supplied API/dashboard definitions, bounded capture and typed DMA producer evidence | [Looker workflow](skills/omni-artifact-accelerator/references/looker-visual-run.md) |
| Power BI | Supplied PBIR/Fabric definitions, bounded source capture and DMA evidence | [Power BI workflow](skills/omni-artifact-accelerator/references/powerbi-visual-run.md) |
| Tableau | Supplied definitions, bounded REST or official-MCP evidence and DMA enrichment | [Tableau workflow](skills/omni-artifact-accelerator/references/tableau-visual-run.md) |
| Sigma | Dedicated specialist, guided API discovery/capture, verified evidence and reviewed Sigma converter reuse; qualified runtime required | [Sigma workflow](skills/omni-artifact-accelerator/references/sigma-visual-run.md) |
| Domo | Dedicated specialist, supplied source/visual/App evidence and opt-in pinned source reads; images, results and detailed App definitions remain supplied evidence | [Domo workflow](skills/omni-artifact-translator/references/domo-visual-run.md) |
| Periscope / Sisense CDT | Dedicated source specialist, pinned DMA evidence and bounded capture/result handoff; Linux/Fusion is a separate product | [CDT migration workflow](skills/omni-artifact-accelerator/references/periscope-visual-run.md) |
| Metabase | Dedicated source specialist, typed API snapshots and bounded capture; preserved dashboard/tab/question identity, controls and query gaps | [Metabase migration workflow](skills/omni-artifact-accelerator/references/metabase-visual-run.md) |
| WebFOCUS | Dedicated specialist, pinned DMA declarations, independent visual/page inventory and bounded repository reads; source procedures remain inert | [WebFOCUS migration workflow](skills/omni-artifact-accelerator/references/webfocus-visual-run.md) |
| ThoughtSpot | Dedicated specialist, JSON TML and independent scope, bounded saved-result/render capture, retained MCP checks and explicit identity/behavior gaps | [ThoughtSpot migration workflow](skills/omni-artifact-accelerator/references/thoughtspot-visual-run.md) |
| Qlik Cloud / Sense | Dedicated specialist, original object definitions and scope, retained selection/result evidence, bounded Cloud Reports and explicit source gaps | [Qlik migration workflow](skills/omni-artifact-accelerator/references/qlik-visual-run.md) |
| MicroStrategy / Strategy | Dedicated specialist, original definitions and inventory, guarded instance/export capture, prompt/selector semantics and passive MCP checks | [Strategy migration workflow](skills/omni-artifact-accelerator/references/microstrategy-visual-run.md) |
| SSRS / Power BI paginated | Separate specialists, passive RDL inspection, state-bound supplied results/exports and guarded native Report preparation | [Report workflow](skills/omni-artifact-accelerator/references/report-workflow.md) |
| Crystal Reports | Supplied version-specific extraction, formula/subreport obligations and original evidence; no binary decoder or SDK execution | [Crystal specialist](skills/omni-crystal-reports-migrator/SKILL.md) |
| SAP BusinessObjects | WebI evidence, Universe/DMA obligations, version-specific Crystal review, supplied results and externally qualified metadata capture | [BusinessObjects migration workflow](skills/omni-artifact-accelerator/references/businessobjects-visual-run.md) |
| IBM Cognos Analytics | Dedicated specialist, bounded report XML import, independent inventory and behavior/DMA obligations; dashboards use reviewed manual evidence | [Cognos migration workflow](skills/omni-artifact-accelerator/references/cognos-visual-run.md) |
| SQL Server / T-SQL | Coordinate database/model requirements through the backend handoff or reviewed manual evidence; no dedicated SQL Server reader or general T-SQL compiler in this package | [Backend collaboration](docs/HOW_TO.md#work-with-data-model-accelerator) |
| Other sources | Explicitly reviewed manual evidence inventory | [Inventory contract](skills/omni-artifact-translator/references/inventory-contract.md#normalized-inventory) |

Read [parser coverage](docs/parser-coverage.md) for exact formats and limitations. A supported reader is not a universal chart or formula converter. Missing source objects, custom visualizations, interactions and security dependencies remain visible work.

Keep database migration separate from report migration: SQL Server model/ETL work
belongs with the backend owner, while SSRS report definitions use the RDL route
above. This does not imply SSIS or SSAS conversion. Reuse a validated Omni Topic
when one is supplied; return genuine missing measures or model behavior through
the [Topic-first handoff](skills/omni-backend-handoff/references/topic-first.md).

For Domo, start with the [source specialist](skills/omni-domo-migrator/SKILL.md)
and [first visual pilot](skills/omni-artifact-translator/references/domo-visual-pilot.md).
For example: “Migrate this Domo Page and its App Studio context. Preserve Card
summary metrics, repeated placements, filters and operational dependencies; reuse
my existing migration evidence and propose three scoped Omni experiences before
coding.” Choose `reuse_existing`, `omni_semantic_reconstruction` or
`warehouse_first_refactor` explicitly. Local helpers prepare and verify evidence;
the optional source wrapper needs an approved exact runtime and selected read
scope. It is a local stdio host, not a hosted ChatGPT connector. No live migration,
automatic App conversion or new source-image/query client is claimed.

An existing companion migration run is optional when compatible Omni semantics
can be reused. The Domo-specific build handoff still requires verified visual
capture and backend references. Imports accept the [four companion contracts](docs/parser-coverage.md#what-this-package-implements-now)
plus the [OAA visual-capture contract](skills/omni-artifact-translator/references/domo-visual-run.md),
not arbitrary DMA adapter output. Preserve Beast Mode, filter and security
requirements with the visual scope; route warehouse transformations and physical
model gaps to the backend owner instead of rebuilding them in App code.

## Specialist roles

| Skill | Owns |
| --- | --- |
| `omni-artifact-accelerator` | Orchestration, shared scope, decisions and integrated handoff |
| `omni-product-owner` | Adaptive discovery, audience/outcomes, prioritized experience intent and product-fit recommendation |
| `omni-data-analyst` | Metric meaning, investigation and independent expected results |
| `omni-bi-engineer` | Governed query bindings, controls and native dashboard construction |
| `omni-app-engineer` | Native App implementation and runtime behavior |
| `omni-3d-modeler` | Original geometry, scale, materials, hierarchy and stable spatial identity |
| `omni-app-designer` | Task flows, screens, interaction states and responsive behavior |
| `omni-dashboard-designer` | Layout, chart selection, hierarchy and exploration |
| `omni-report-designer` | Native Reports Beta page composition, pagination and output design |
| `omni-report-builder` | Reviewed report definitions, query bindings and native qualification |
| `omni-qa-analyst` | Independent numerical, interaction, visual, access and performance checks |
| `omni-data-storyteller` | Evidence-backed titles, annotations and decision guidance |
| `omni-motion-designer` | Purposeful feedback and reduced-motion equivalents |
| `omni-branding` | Customer identity, approved assets, fonts and theme mappings |
| `omni-design-systems` | Reusable design rules, tokens and accessibility expectations |
| `omni-artifact-translator` | Original source inventory, behavior mapping and migration gaps |
| `omni-domo-migrator` | Domo Card/Page/App identity, analytical and operational behavior, original evidence and coordinated migration |
| `omni-sigma-migrator` | Sigma workbook identity, source capture, converter reuse and explicit architecture decisions |
| `omni-periscope-migrator` | CDT source identity, capture/state, custom-logic obligations and coordinated migration evidence |
| `omni-metabase-migrator` | Metabase source identity, query/placement/control evidence and coordinated migration obligations |
| `omni-webfocus-migrator` | Procedure semantics, ordered visual styles, page composition and runtime migration obligations |
| `omni-thoughtspot-migrator` | Liveboard/Answer identity, TML semantics, source-state evidence and migration coordination |
| `omni-qlik-migrator` | Qlik sheet/object identity, selections, expressions, visual references and migration obligations |
| `omni-microstrategy-migrator` | Strategy chapters, visual placements, report semantics, prompts/selectors and migration obligations |
| `omni-businessobjects-migrator` | WebI providers, report contexts, Universe handoff and separate Crystal obligations |
| `omni-cognos-migrator` | Cognos report queries, prompts, layouts and dependency obligations; separate dashboard evidence |
| `omni-ssrs-migrator` | RDL reports, catalog identity, parameters, pagination and source evidence |
| `omni-powerbi-paginated-migrator` | Power BI paginated RDL and separately qualified export evidence |
| `omni-crystal-reports-migrator` | Explicit Crystal extractions, evaluation-order and subreport obligations |
| `omni-backend-handoff` | Versioned DMA exchanges, current bindings and change-impact review |

Each specialist can also be invoked directly. Design guidance draws from official Apple, Google, Microsoft, Samsung and other primary sources, with platform-specific advice distinguished from package recommendations. See [design foundations](skills/omni-design-systems/references/vendor-guidance.md).

## Develop distinctive data experiences

The [Data Experience Design Studio](skills/omni-design-systems/references/experience-curriculum.md) provides a shared curriculum for analytical judgment, art direction, advanced visual encoding, storytelling, dashboard composition, App interactions, motion, branding, implementation and critique. It teaches agents through worked choices and revision instead of prescribing one house layout.

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

For a substantial new experience, expect **A–C evidence → D requirements → three E concepts and your selection → detailed design → F implementation and review → separately authorized native delivery**. A dashboard and App should serve their selected tasks even when they share metrics. Reuse the supplied website, brand authority and any explicit no-research decision. Ask for a website only when a material branding need remains unresolved; turn the selected brand characteristics into composition choices and retain image/font provenance and fallback behavior. A small correction uses focused checks; a faithful migration keeps its original behavior obligations.

> Create a native service-performance dashboard and an exception-investigation App from our existing Omni model. Use our supplied website and brand guide. Compare compositions where the direction is unresolved, resolve desktop and narrow views, and keep the designer involved through the native render. Make detail interactions add useful evidence. Report numerical, craft, native interaction and human-testing results separately.

See [design and implementation](docs/HOW_TO.md#3-design-and-implement-the-selected-scope) for the review workflow and evidence checks. Correct numbers, a saved screenshot and a published document establish different things; none alone establishes a polished, usable experience.

Local planning and source inspection need no Omni credentials. Native work needs separately configured, authorized source/target access, verified API or CLI capabilities and an appropriate development draft. The native helpers and local stdio host use POSIX facilities; macOS/Linux is the supported execution environment described here.

| Intended operation | Implemented route and boundary |
| --- | --- |
| Build or update a native dashboard | [Dashboard adapter](skills/omni-bi-engineer/references/omni-build-export.md) on an existing named development draft |
| Add an App to an existing workbook | [Initial App adapter](skills/omni-app-engineer/references/native-app-contract.md), using inspected queries and a reviewed runtime bridge on a workbook-only named draft |
| Update existing App HTML | [Authoring preflight](skills/omni-app-engineer/references/authoring-preflight.md) prepares and verifies an exact named-draft HTML-only change; queries and security settings stay outside that request |
| Create a new App document | [Bounded native authoring](skills/omni-artifact-accelerator/references/native-authoring.md) prepares reviewed HTML, semantic queries, model, new identifier and locked resource settings after A–F review |
| Publish the complete main App draft | `app-publish-prepare` checks the previously frozen and reviewed whole draft, including queries, controls, metadata, settings and HTML; `app-publish-verify` compares supplied publication/readback captures. Branch-attached drafts are outside this route. See [publication preflight](skills/omni-app-engineer/references/authoring-preflight.md#publish-the-complete-reviewed-main-draft). |
| Prepare a native Report | [Reports Beta helpers](skills/omni-artifact-accelerator/references/report-workflow.md) prepare definitions and retain qualification/readback/export evidence; no report execution, publication or distribution tool is enabled |

The App preparation helpers do not read credentials or send requests. An authorized
host performs the call, optionally through the operator-integrated
`native_write_gate.execute` boundary, which rechecks the request and persists its
attempt before sending. That integration is not automatically active in any host.
Unknown write outcomes require reconciliation before another attempt. **Creating a
new document publishes its initial version immediately**; a design choice does not
authorize that write. See [the write boundary](skills/omni-app-engineer/references/authoring-preflight.md#operator-integrated-write-boundary)
for the supported integration.

Keep source dates, partial populations and recorded-position coverage visible.
Close out with the selected requirements, what is working on each surface and
unresolved differences. Track **local consistency, authorized preview, native
behavior/access, business acceptance and publication** separately. Preview can
enable later visual review; successful publication does not close an unobserved
lane or accept DMA semantics. A screenshot cannot prove numbers or permissions,
and API readback cannot prove the App ran correctly. Selecting both surfaces
requires distinct target documents and separate evidence.

Claude and ChatGPT tool support depends on the actual host/account configuration. The included [local host workflow](skills/omni-artifact-accelerator/references/connected-visual-migration.md) does not provision a remote connector or give a web chat access to a local process. A clearly recorded operator-assisted file workflow remains available where direct integration is unavailable.

[How to use the package](docs/HOW_TO.md) · [Parser coverage](docs/parser-coverage.md) · [Testing](docs/TESTING.md) · [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator)
