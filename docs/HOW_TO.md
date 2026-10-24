# Use Omni Artifact Accelerator

Start with a business question, a migration source or an existing model. The orchestrator coordinates the relevant specialists and keeps a saved engagement with decisions, editable deliverables and evidence. You can stop at a design handoff or continue to a separately authorized native candidate.

## Installation and updates

Follow the [source-only quick start](../README.md#quick-start) and [package-use policy](../skills/omni-artifact-accelerator/references/dependency-policy.md). Do not install/import dependencies or activate skills without explicit scoped human sign-off. Existing installations and pinned versions are not automatic approval.

All 15 skills form one portable bundle. Preview an existing directory without writing:

```sh
OAA_SKILLS_DIR="$HOME/.codex/skills"
python3 -I -S scripts/install_skills.py --destination "$OAA_SKILLS_DIR"
python3 -I -S scripts/install_skills.py --destination "$OAA_SKILLS_DIR" --verify
```

The public `--apply` path is disabled pending a qualified host approval gate. Do not use manual copies as a bypass. A reviewed `--upgrade-from` archive can support a read-only comparison; its manifest proves integrity only, not approval or publisher authenticity. Preserve customizations and resolve any conflict before a future authorized activation.

The agent can review the orchestrator directly in the checkout. Role planning does not launch workers or install tools. Once separately authorized activation is implemented and verified, refresh the host's discovery and retain the exact installed-source evidence.

## New dashboard or App

Follow the [data-first A–F workflow](../skills/omni-artifact-accelerator/references/data-first-product-workflow.md):
verify data and the user's access, analyze/query, create the reusable narrative,
conduct artifact discovery, present three viable product options for user selection,
then resolve design and implement with security/UI/UX/PO/QA feedback each iteration.
The setup commands create a gated engagement; they do not perform the analysis or
authenticate access. [Executable gates](../skills/omni-artifact-accelerator/references/stage-gates.md)
enforce order at package entrypoints. All new modes are gated, including enhancement
and migration. Existing evidence can be reused when current. For normal chat,
explicitly configure `--selection-policy conversation-evidence-v1` at initialization
and follow the [chat-choice handoff](../skills/omni-artifact-accelerator/references/stage-gates.md#continue-an-existing-chat-choice).
It retains the actual reply for local design/coding without claiming authenticated
approval. Strict engagements never fall back automatically; native writes and
dependency use retain separate controls.

### 1. Create a private engagement

Keep the output outside both the repository and skill installation. The parent directory must exist, and the engagement directory must be new:

```sh
mkdir -p "$HOME/omni-artifact-runs"
OAA_RUN="$HOME/omni-artifact-runs/operations-pilot"
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py init \
  --output "$OAA_RUN" --name 'Operations pilot' --mode net-new --surface both \
  --selection-policy conversation-evidence-v1
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py plan \
  --project "$OAA_RUN"
```

Choose `dashboard`, `app` or `both`. Use `--mode enhancement` for a change to an existing experience. Resume an engagement by reopening it; do not initialize over its existing files. Helpers reject symlink paths, so use canonical paths and keep all relative file references inside the engagement.

After each A–F checkpoint, use `stage-record --project "$OAA_RUN" --request <request.json>`
and `stage-status --project "$OAA_RUN"`. Before coding, the host must pass
`stage-check --project "$OAA_RUN" --action build` through its configured selection policy; native mutation authority remains separate.
See the [record schemas and host contract](../skills/omni-artifact-accelerator/references/stage-gates.md).
Do not work around a blocked gate by using a raw file writer or another authoring helper.

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

Supply what you already know about the audience, decision, requested surface, available Omni model/Topics and completion stage. A short request starts source/access qualification and analysis. After the storyteller creates the reusable narrative, the product owner asks only missing artifact questions and coordinates three distinct product options for your choice. You do not need to specify a layout or coordinate specialist interviews. Unresolved metrics need an owner, not an invented definition.

> Use $omni-artifact-accelerator to design a native operations dashboard. Supervisors need to spot late orders, compare teams and inspect exceptions. Verify access to our existing Topics, qualify the analysis and create a refresh-safe narrative, then clarify artifact requirements and show me three viable product options. After I choose, resolve the design and prepare a local reviewable handoff. Keep unknown targets and freshness explicit; do not write to the tenant yet.

For an App:

> Use $omni-artifact-accelerator to design a native Omni App for capacity planning. Let a viewer choose a region, adjust a clearly hypothetical scenario, inspect the governed baseline and reset. Keep applied results separate from pending inputs. Identify which calculations belong in the model and which are presentation-only. Prepare the task flow and implementation contract before native construction.

For `both`, assign each requirement to dashboard, App or both. Shared metrics can use one governed definition; each surface still needs its own composition, target document and evidence.

For a substantial App, carry the intended experience alongside the metrics:

> Use our existing audience, metric, website and logo decisions. Create a branded introduction leading into a focused investigation workspace; returning users should be able to enter the work directly. Keep the selected period and entity through navigation. Compare frontend treatments of this same task and resolve type/image hierarchy, useful detail, narrow behavior and purposeful motion. Use CLI/MCP only; retain rendered checks as unrun.

Use the [shared experience brief](../skills/omni-design-systems/references/experience-brief.md) and [named requirement examples](../skills/omni-artifact-accelerator/references/design-intent.md#experience-requirements) to retain these choices in existing contracts. Reuse supplied answers; ask only about consequential missing choices. A direct workspace without imagery is equally valid when selected. The [context-transfer studio](../skills/omni-design-systems/references/experience-context-studio.md) demonstrates contrasting original treatments of the same task.

### 3. Design and implement the selected scope

For substantial work, use the [product-intent guide](../skills/omni-artifact-accelerator/references/product-intent.md)
to add product context to the existing intent specification and select it. Keep
attributable notes inside the private engagement. Then generate its readable view:

```sh
python3 -I -S -B "$OAA_HELPER" product-brief --project "$OAA_RUN" \
  --output deliverables/north-star-v1.md
python3 -I -S -B "$OAA_HELPER" product-check --project "$OAA_RUN"
```

Here `OAA_HELPER` is the selected `analyst_project.py`. The North Star is a versioned
projection, not another authority; edits become proposals for a new selected intent.
Packets carry current product context. Focused repairs reuse existing decisions and
need no extra interview. Product fit, independent creative critique and correctness
are separate reviews; neither these commands nor role planning activates skills.

Analyst and BI engineering establish meaning, queries and evidence before design. Storytelling is required for the new-product narrative; it feeds the artifact interview and three-option comparison. After user selection, designers, branding and design systems resolve the product, with motion and other specialists for relevant selected behavior. Engineering implements the resolved handoff against available target capabilities.

Use the [Data Experience Design Studio](../skills/omni-design-systems/references/experience-curriculum.md) when developing a substantial design, addressing craft feedback or practicing a new technique. Select the relevant role lessons, write a concrete design thesis and compare suitable visual structures from the pattern atlas. The worked studios demonstrate how to diagnose and revise a generic starting composition; ordinary engagements need only the lessons that improve the actual task.

For a substantial new experience or material redesign:

1. Complete A–C access, analysis and reusable narrative, then retain the D artifact brief: audience/task, website/brand authority, experience ambition and target constraints.
2. For new products/reconception, present exactly three viable, materially different options on the same core narrative/evidence and wait for the user's selection. Change experience structure or interaction, not only palette. Prose alone is not rendered evidence. Focused work or an already selected product reuses the current direction.
3. Resolve type/spacing roles, native grid or App geometry, chart axes/labels/units, states, keyboard path and exact query dependencies. Check native feasibility before committing to an unsupported interaction.
4. Implement a cohesive candidate, then obtain security, UI/UX, PO and independent QA feedback on each iteration. Return permitted captures and material deviations to the designer; correct findings and repeat affected checks.
5. Keep independent numerical, craft, native behavior and human-usability evidence separate. Update the engagement index and artifact/query records; missing testing remains visible.

Use a focused review for a narrow correction. Preserve a faithful migration's source obligations and record adaptations rather than imposing a redesign.

Respect explicit tool constraints. If browser/rendering work is prohibited or unavailable, continue with supported specifications, code and CLI/MCP checks. Mark rendered alternatives, native appearance and native interactions as `not_run` where unobserved; do not claim prose alternatives or an API readback close those lanes. This limitation does not create a new permission gate for already authorized work.

For reproducible review evidence, author the scoped specification described in [design evidence](../skills/omni-qa-analyst/references/design-evidence.md), then freeze it after the selected checks:

```sh
python skills/omni-artifact-accelerator/scripts/analyst_project.py design-freeze \
  --project "$OAA_RUN" --spec "$OAA_RUN/contracts/design-review-spec-v2.json" \
  --output contracts/design-review-v2.json
python skills/omni-artifact-accelerator/scripts/analyst_project.py design-check \
  --project "$OAA_RUN"
```

The checker detects missing or stale recorded evidence. It cannot judge visual quality, authenticate a reviewer, or grant customer acceptance. Keep unfinished lanes visible and create a new review after changed inputs and affected retests.

Use the [ideation playbook](../skills/omni-design-systems/references/ideation-playbook.md) for material new concepts, [dashboard patterns](../skills/omni-dashboard-designer/references/dashboard-patterns.md) or [App patterns](../skills/omni-app-designer/references/app-patterns.md) for composition, and [usability testing](../skills/omni-qa-analyst/references/usability-testing.md) for task evaluation. A focused edit need not restart discovery. Mark mock data and unimplemented actions clearly; without participants, provide the test script and retain `not_run` status.

When native construction is requested, inspect the actual target and permissions first. Follow [native build/export](../skills/omni-bi-engineer/references/omni-build-export.md) for dashboards and [the native App contract](../skills/omni-app-engineer/references/native-app-contract.md) for Apps. Initial App construction starts from an operator-created workbook-only named draft, inspected governed queries and a reviewed runtime bridge. The helper does not create those prerequisites or certify an invented browser API.

For net-new provisioning or a tool/authentication configuration outside the migration adapters, use [bounded native authoring](../skills/omni-artifact-accelerator/references/native-authoring.md). Record the exact official tools and capabilities used so the workflow is reproducible. Preserve complete tile definitions for styling/title updates and inspect the exact draft before publishing.

## Keep context current

When feedback changes the design, create a new intent version and select it through the existing [design-intent workflow](../skills/omni-artifact-accelerator/references/design-intent.md). `intent-check` exposes a derived current/historical intent index. Update the engagement's `START_HERE.md` with the selected experience, source/query/runtime references, brand/content mode, usable content width and height, and remaining verification gaps. List replaced proposals as historical; do not rewrite frozen review evidence.

For an App, the BI and App engineers resolve the [exact data-input contract](../skills/omni-app-engineer/references/native-data-input.md). Mark each payload as observed or simulated and distinguish CLI exports, source templates, assembled HTML and the native runtime. For a demo, branding resolves [original, verified or fictional presentation names](../skills/omni-branding/references/demo-presentation.md); geography and source identity retain their own evidence. These choices fit existing structured requirement values and query/runtime records.

Prepare a bounded handoff with explicit dependencies. In this example the four files have already been authored and reviewed inside the private engagement; they are not generated by the packet command. The assignment file supplies the concrete task, output paths, acceptance conditions and allowed local scope. Keep generated packet fields unchanged; include the assignment as a pinned input rather than replacing the generated objective/action fields after creation:

```sh
python skills/omni-artifact-accelerator/scripts/analyst_project.py packet \
  --project "$OAA_RUN" --role app-engineer \
  --input contracts/queries.json \
  --input contracts/runtime-v1.json \
  --input evidence/callback-v1.json \
  --input tasks/assignment-v1.json \
  --output "$OAA_RUN/tasks/app-engineer-v1.json"
python skills/omni-artifact-accelerator/scripts/analyst_project.py packet-check \
  --project "$OAA_RUN" --packet tasks/app-engineer-v1.json
```

Add the alias manifest as another `--input` only when selected for the task. Register reviewed versions with `register` where appropriate. Paths mentioned inside other JSON files do not automatically include their bytes. Recheck before dispatch/resume; a stale packet returns nonzero and must be regenerated against the resolved selection. This checks declared input consistency, not complete dependency coverage, permissions or native execution. Keep the existing 256 KiB packet limit and reviewed host handoff for larger assets.

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

If you explicitly choose a supplied brand authority and no website research, the agent records a `website` requirement as explicitly omitted with your decision reference and selected surfaces. The helper then preserves that answer instead of repeating the generic website question. Supplying a logo alone does not imply this omission. See [saved interview decisions](../skills/omni-artifact-accelerator/references/design-intent.md#one-short-interview-persistent-decisions).

> Use $omni-branding for this customer dashboard and App. Use the company website URL and approved assets I supply. Separate observed styling from accepted brand rules, preserve image/font provenance and permissions, and map the shared colors and typography to each supported Omni surface. Keep category colors stable and provide a fallback where an asset cannot load. Produce the brand contract and previews without changing a shared theme.

Use the [brand interview and contract](../skills/omni-branding/references/brand-contract.md). Keep application theme, dashboard/document theme and App CSS mappings distinct. Check actual contrast, font fallback, logo legibility, keyboard focus and reduced motion. Public visibility does not authorize broad crawling or unrestricted asset downloads. Organization-wide theme changes are separate from a local design request.

## Give a specialist a bounded task

Design-context packets now include motion and storytelling roles, and expose `design_context.selected_intent`. Before dispatch or resume, reconcile this pin with the current `intent-check` result and recheck the declared input hashes. Regenerate a stale packet; it is not a live connection to later user decisions. Direct specialist calls use the same current selection. Large assets/candidates still need the existing explicit bounded host handoff when they exceed packet limits; do not silently exclude them.

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

## First-delivery quality

For substantial Apps and dashboards, follow the [first-delivery workflow](../skills/omni-artifact-accelerator/references/first-delivery.md). Extend the existing selected intent with optional delivery annotations and use stable destination IDs in the resolved design. Run `experience-check --project PROJECT`, then `plan --project PROJECT`; reconcile uncovered requirements before claiming completion. The roles are responsibilities, not a request to spawn every specialist. Use the existing scoped assignment route for actual parallel work.

Generate review obligations from the selected design/intent before collecting cases. Include each selected destination/context and applicable lane; missing applicability remains open. For a focused change, name the affected obligations and retain the full inventory. Follow the typed fields and example in [design evidence](../skills/omni-qa-analyst/references/design-evidence.md).

Build one complete task slice, including detail/return where selected, and qualify selected data/media/asset boundaries early. The designer reviews the assembled result across all consequential destinations. Keep CLI-only restrictions and unobserved lanes explicit. `ready_for_review` is structural coverage, not native or aesthetic approval. New frozen reviews enforce destination/journey bindings. Historical reviews remain readable with unassessed destination coverage; omitted fields cannot make a new review historical. A retest closes only the matching obligation and current candidate, and endpoint screenshots do not establish interaction.

Keep the initial candidate, internally revised first delivery and a compact prompting/revision log outside the repository. Distinguish necessary clarification, repeated questions, corrections to supplied requirements and new scope. Internal critique should repair routine design gaps before delivery; it must not fabricate rendering or customer feedback to meet a prompting target.

From the repository checkout, `python scripts/install_skills.py --destination "$OAA_SKILLS_DIR" --verify` compares the active directory to the source package without changing it. Exit 0 means exact package-skill parity; exit 1 reports missing/changed/extra files. Retain the version and source manifest hash with rehearsal evidence, and ensure the host loads those files. Do not overwrite customized skills to force parity; retain the conflict for a separately authorized upgrade; activation is currently disabled.

## Reuse behavior without inheriting a layout

Use the A–C evidence and D brief before selecting example treatments for a new product; retain the three-option comparison and user's selection in the existing per-surface design-review context. Follow the [principle/choice/pattern distinction](../skills/omni-design-systems/references/experience-brief.md). Direct treatment is appropriate for a focused change or an already selected product. All routes still need appropriate implemented-result evidence; native dashboards and faithful migrations retain their own scope.

For Apps, [behavior controllers](../skills/omni-app-engineer/references/experience-behaviors.md) can supply state and lifecycle while the engagement renderer supplies presentation. The [portable assembly walkthrough](../skills/omni-app-engineer/references/portable-assembly.md) creates a local candidate from explicit source pins without a prescribed shell or native SDK. Keep the manifest and applicable contract files in current-intent dependencies. Use a fresh output directory for each candidate; inspect the resulting journey and bind the actual native inputs separately.

The original [behavior studio](../skills/omni-app-engineer/assets/behavior-studio.html) is an optional same-task comparison. Similarity is acceptable when justified by the user/task; novelty, extra motion and extra screens are not completion criteria. Under CLI-only/no-rendering constraints, report structural and simulated behavior separately from unobserved visual/native quality.

## Improve buttons, search and columns

Use the [control-craft guide](../skills/omni-design-systems/references/control-craft.md) for a substantial interface or a named quality gap. Reuse the current selected design rather than repeating intake. Choose control semantics first, then resolve brand tokens and anatomy; a command menu, form selection, destination link and in-page tab are different tasks even when visually similar.

The [control studio](../skills/omni-app-engineer/assets/control-studio.html) provides original synthetic examples. Copy only selected primitives into the engagement, keep their exact hashes with the existing assembly inputs, and write the renderer for the chosen task. It does not supply a native bridge, remote search service, durable preferences or a universal App shell. See [control implementation](../skills/omni-app-engineer/references/control-primitives.md) for binding, lifecycle and limits.

For remote search, inspect the actual query/filter route and callback identity before connecting a text field. Declare draft, applied and displayed-result scope, whether restoration runs a query, and reset semantics. A locally filtered partial result is not a complete warehouse search. In a migration, preserve source defaults, field identities and accepted behavior; route genuine model gaps through the existing DMA handoff.

Qualify only the affected task and conditions. CLI-only work can establish source behavior and saved API state, while visual fit, browser focus and actual host execution remain unobserved. Keep pilot evidence and private planning outside the package. Optional reading is linked from the control guide; no course enrollment or completion is needed to use the skills.

## Spatial modeling

Choose `spatial-modeling` in a selected App requirement only when modeling helps the task. The role plan adds the modeler and App designer/engineer; ordinary dashboards and custom charts keep their established routes. Read the [3D curriculum](../skills/omni-design-systems/references/3d-curriculum.md), [model brief](../skills/omni-3d-modeler/references/brief-handoff.md) and [spatial integration contract](../skills/omni-app-engineer/references/spatial-integration.md).

For harness source review, follow [its runbook](../harness/README.md). The compiler and viewer sources are available; processing customer input and promoting assets requires a separately qualified isolated host. A missing runtime yields a brief and blocked request, never a host-execution fallback. Native and visual evidence stay separate from synthetic source checks.

## Native procedural scene workflow

1. **Describe the task and fidelity.** Give the existing orchestrator the audience,
   inspection/decision, App surface and references. Reuse current brand decisions.
   State whether dimensions are measured or illustrative. A logo authorization
   does not authorize a font/engine import.
2. **Choose the route.** Use a scene-only illustration, governed spatial analysis,
   or separately isolated asset processing. Stay in 2D when it answers the task
   more clearly. The native procedural route needs no artificial backend project.
3. **Prepare bounded original scene data.** The modeler follows
   [procedural craft](../skills/omni-3d-modeler/references/procedural-craft.md) and
   the [native contract](../skills/omni-app-engineer/references/native-scene-framework.md).
   Supply stable part IDs, materials, useful named views and original dimensional
   expectations. The three included synthetic geometry fixtures illustrate
   different topologies; they do not prescribe customer layouts.
4. **Review runtime before loading it.** First-party validators/builders/session
   code can be checked locally with the existing runtime. The renderer adapter
   accepts an explicitly supplied engine, but supplies no dependency acquisition
   or approval. Prepare exact package/closure/action permission and qualify the
   supported loading route. The current classic assembler and resource policy
   have not qualified the candidate module engine.
5. **Compose one useful path.** Bind container sizing, semantic entity/view
   controls, selection/evidence/return and optional camera motion. Use one session
   for initialization, cancellation, reduced motion and teardown. Preserve the
   exact-value/list route if graphics fail. For analysis, use the existing query
   contract and the optional native scene data bridge; for decoration, omit it.
6. **Check only what you can observe.** Run the focused source checks below.
   After runtime and native write authorization, qualify one small original
   textured shape before complex scenes. Native readback, rendered interaction,
   access, performance and user acceptance are separate lanes. CLI-only runs do
   not qualify visual polish. Keep receipts and pilot histories outside the repo.

For developers working on trusted first-party source:

```sh
env -u NODE_OPTIONS -u NODE_PATH node --test tests/test_native_scene_geometry.js tests/test_native_scene_session.js tests/test_native_scene_integration.js
python3 -I -S -B scripts/check_package.py
```

These commands use existing runtimes and standard-library facilities; they do
not install/load Three.js, contact Omni or render a browser. Installing the skill
bundle, loading dependencies, publishing an App and pushing the repository each
retain their existing authorization boundaries.
# Host startup and delivery assessment

For substantial artifact work, use the [execution procedure](../skills/omni-artifact-accelerator/references/execution-workflow.md)
before full implementation. It provides exact startup/ownership/candidate/evidence
request shapes. The helpers below use only original code and the existing Python
standard library; `$OAA_HELPER` points at the selected `analyst_project.py` and
`$OAA_RUN` at the existing engagement outside this repository.

```sh
python3 -I -S -B "$OAA_HELPER" run-start --project "$OAA_RUN" --request startup.json
python3 -I -S -B "$OAA_HELPER" run-check --project "$OAA_RUN" --request readiness.json
python3 -I -S -B "$OAA_HELPER" candidate-freeze --project "$OAA_RUN" --request candidate.json
python3 -I -S -B "$OAA_HELPER" delivery-check --project "$OAA_RUN" --request delivery.json
```

`run-check` takes `run` and `execution` paths. `delivery-check` adds `candidate` and
`evidence` paths. Paths inside requests are engagement-relative. Exit 0 means
structural readiness, exit 1 identifies gaps and exit 2 rejects invalid input.
These are local assessments, not native writes or authorization. Candidate requests
include actual `builders`. Gated assembler builds already freeze and return their
candidate; do not duplicate that freeze. Retain the first candidate before review
and obtain all four consulting dispositions before creating a revision. No rendering
permission means visual quality remains unobserved even when publication succeeds.
