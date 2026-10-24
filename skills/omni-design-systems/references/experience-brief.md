# Carry the experience from brief to implementation

Use when creating a substantial experience, resolving a material redesign or responding to explicit design-quality feedback. For a focused edit or faithful migration, reuse the selected direction and inspect the affected part. This is a working view of the existing design/brand/intent contracts, not a new file requirement, schema, interview or approval stage.

## Preserve the user's meaning

Read the conversation's retained decisions and the [current design intent](../../omni-artifact-accelerator/references/design-intent.md) before asking questions. Distinguish context that is missing from context already supplied but not expressed in the design. “Website-quality” may already establish an ambition; it still needs a concrete composition. Never treat an analytical task as an implicit choice of a dashboard-shaped App.

Retain the user's relevant wording or attributable paraphrase, then translate it into observable choices. Keep `origin: user|reused|proposal`, the decision reference and unresolved/selected/omitted/deferred status. An agent may select a working proposal for reversible work; that does not make it a user-approved direction. When feedback changes a selection, version the existing record, preserve its history and name the superseded decision.

| Decision | Capture only what materially affects this task |
| --- | --- |
| Audience and outcome | Who is using this, the question they must answer, and the useful action or evidence gained. |
| Experience mode | For Apps: direct workspace, guided story, branded entry into a workspace, or another explicit choice. For dashboards: the monitoring/comparison/diagnostic reading path within supported native controls. |
| First encounter and repeat use | Opening promise, focal content, primary action and direct route back to work. A returning user should not have to repeat an introduction unless the actual task requires it. |
| Reference qualities | Qualities to borrow and avoid, their sources and evidence limits. Translate “elegant” into hierarchy, proportion, image/type relationship or interaction; a famous brand name is not a specification. |
| Art direction | Display/body/number hierarchy, composition, density, spacing rhythm, semantic colors, imagery role or deliberate omission, and narrow treatment. Resolve actual values in the chosen design. |
| Journey | Destinations, entry/exit, meaningful detail, scope and identity to retain, focus/return and recovery. Distinguish navigation from filtering and scrolling. |
| Motion | Primary-journey change explained, stable identity, interruption, immediate data commit and static/reduced equivalent. Select no motion when it adds no task value. |
| Constraints and observation | Native surface, source obligations, available data, tooling, asset/font/runtime budgets, usable content width **and height**, host-chrome/zoom assumptions and permitted review methods. Label assumed dimensions; do not report a nominal laptop screen as an observed App viewport. |

For branded work, reuse the supplied website and logo answer. If missing, ask for the official company website plus an approved logo or official-site sourcing authorization in the existing short question batch. Honor an explicit user decision to omit website research/use supplied authority through the existing `category: website` omission described in [design intent](../../omni-artifact-accelerator/references/design-intent.md#one-short-interview-persistent-decisions); do not invent a URL or keep asking. A logo answer alone does not waive the website question or settle the experience mode. Ask a separate experience question only if the unresolved choice materially changes the work; do not require the user to specify every spacing value or coordinate the specialists.

## Separate behavior from treatment

Keep these decisions distinct in the existing brief, not in a new framework document:

| Layer | Retain or choose |
| --- | --- |
| Essential correctness and usability | Truthful scope/units/missingness, stable identity, attributable current results, effective access, usable controls and exact evidence, focus/return/recovery, and readable adaptation. Verify the applicable behavior independently of its renderer. |
| Engagement-specific treatment | Composition, navigation form, type, density, imagery and motion follow the audience, task, brand and available space. Similar tasks may intentionally look similar; novelty is not a quality metric. |
| Optional capability patterns | Pinning, narrative steps, maps, camera/3D scenes, calendars, media and other patterns need a task benefit plus qualified data/runtime prerequisites. Omit them or choose a simpler alternative when they do not help. |

The App designer decides the task relationship and rationale before optional example retrieval, unless the user chose a reference. A reusable behavior contract must not prescribe a hero, cards, sidebar, tabs, scene, destination count or concept count. Native dashboards and faithful migrations retain their own supported controls and source obligations; App scaffolding is not their default implementation.

## Resolve the choices in one place

Use stable named requirements such as `experience-mode`, `entry-return-journey` and `art-direction` **when justified by the brief**. Record their structured values in existing `requirements[].value`, with surface-specific contexts and decision references. Keep detailed composition/state decisions in the selected design JSON and assets in the linked brand contract. Use the [requirement examples](../../omni-artifact-accelerator/references/design-intent.md#experience-requirements) rather than a second decision ledger.

Translate each material request into `source wording/decision → observable behavior → destination → responsible role → dependencies → expected evidence/disposition` in those existing records. A component name is insufficient: a requested calendar needs the selected date-navigation and event-inspection behavior; a camera needs the selected exploration/reset behavior; playback needs actual provider controls and playback evidence. Preserve an unresolved requested behavior when a useful fallback is supplied. Role ownership can stay with one worker; it does not require another agent or interview.

Use stable destination IDs in the resolved design. The optional existing-intent `requirements[].delivery` and [first-delivery coverage workflow](../../omni-artifact-accelerator/references/first-delivery.md) can retain explicit ownership, behavior and dependency paths. Its checker assesses declared coverage and pins; people still judge whether the behavior satisfies the original request and whether evidence supports completion. Do not duplicate that contract in a new ledger.

Unanswered required choices remain open. Optional imagery, a font preference or an agent-proposed transition does not automatically become a required obligation. Single-screen and imagery-free experiences are valid selections. Nothing here creates a hero, animation, image count or universal screen count requirement.

Selected design files are pinned by the existing intent chain. Arbitrary paths written inside `value` are not automatically discovered or pinned: keep decisions inline, or declare relevant design/brand/evidence dependencies through the existing mechanisms. Additional review reports must be explicit packet inputs or review evidence. Never imply that a link alone seals its target.

For example, a justified `usable-space` requirement can keep `{width: 1024, height: 600, basis: "proposed usable App area after host chrome", first_view: ["scope", "change", "inspect action"], scroll: "one content region; exact table remains reachable"}` inside its existing structured `value`. These are synthetic design choices, not a device matrix or new schema. Put applicable `[width, height]` cases in existing requirement contexts and record actual target dimensions separately when observed.

## Compare the same task

For new products/reconception, follow stage E of the [data-first workflow](../../omni-artifact-accelerator/references/data-first-product-workflow.md): after A–C and artifact discovery, present exactly three viable product options and obtain the user's selection. Hold the core analytical narrative and truthful evidence constant; vary experience structure, investigation path, focal visualization or interaction. Resolve task uncertainty separately from visual uncertainty. Direct choices remain appropriate for focused work or implementation within an already selected product; they do not bypass the new-product choice.

Record `reference quality → concrete choice → expected benefit → tradeoff → observation needed`. Compare rendered treatments when permitted; prose can establish structural intent but not visual quality. The original [context studio](experience-context-studio.md) demonstrates three different treatments of one task and an annotated failure. Reuse the reasoning, not its layout as a house style.

## Preserve context across roles and turns

For design, branding, App/BI engineering, storytelling, motion and QA, consume the current selected intent, design, brand and unresolved choices even when invoked directly. A generated packet exposes `design_context.selected_intent`; it is a pin, not a live subscription. On dispatch/resume, use `intent-check` and the existing [packet-check/current-context path](../../omni-artifact-accelerator/references/design-intent.md#current-context-and-resume) to reconcile the selection and declared inputs. Regenerate a stale packet before dependent work. These checks do not discover undeclared dependencies or decide which free-text statement is current. New user feedback takes precedence over an older packet and must be reflected in the next version. With no selection, retain available draft context as unassessed.

Keep historical proposals and reviews as evidence, but make the latest applicable decision easy to find in the existing current-context record: selected version/pin, superseded reference, decision source and affected scope. An old report's “current” heading does not outrank a later selected decision. Do not rewrite sealed history or import an old conclusion into a new candidate without checking its dependencies. Follow the orchestrator's current-context instructions rather than creating a parallel index format.

Do not load every role's full reference library. The orchestrator sends the relevant slice; the designer owns composition, branding owns identity/provenance, engineering owns supported implementation, storytelling owns truthful copy, motion owns transition behavior and QA owns independent observations. Analyst and backend work need the task and genuine data dependencies, not the complete visual asset bundle. A visual-context conflict does not by itself block independent numerical or backend work.

Packets retain the 256 KiB aggregate bound and disclosure rules. If a candidate or image exceeds it, use the existing explicit host-arranged, dependency-complete handoff with exact paths/hashes and appropriate access. Report what is unavailable; do not silently drop an asset, replace it, send unrelated customer files or raise the bound. Metadata is not proof that another host can access the bytes.

## Implement the selected experience

Resolve a compact **destination specimen** in the existing selected design before implementing a substantial working view. Name the dominant subject, one useful opening observation/action, supporting comparison, detail/return path and constrained-space treatment. Specify which content precedes the focal subject and why. A title, filter strip, summary strip and explanation can each be reasonable yet collectively bury the purpose of the page. Move secondary context beside the focal subject, into a later region or into disclosure when that serves the task; no universal header height, hero or above-the-fold chart is required.

Keep the useful first state separate from a hard-coded selection: identify its required inputs, selection rule, unknown/empty fallback and precedence of an existing user choice. Asynchronous data arriving later must not reset an investigation. For entity work, resolve eligible measures/actions by role and evidence before creating a generic detail component. Use the analyst's coverage map for unsupported roles rather than presenting irrelevant zeroes.

Where context persists, record its owner and reset rule: destination, entity, local filter, measure, time and camera are different scopes. Include a cross-entity return and a relevant exceptional-state return, such as an event with unknown time. On a narrow screen, choose whether index/detail becomes a focused navigation path or a stack from the task and available space; a stack is not automatically an adequate adaptation.

For each consequential destination, resolve its user question, dominant subject, first useful action, supporting evidence and default state. Carry these with `entry/exit → useful detail → retained state → entry focus → return focus/scroll → reset` in the selected design. Specify stable identity, period, filters, search, sorting and pins only where present. A useful detail adds evidence or an operation; repeating a row in a drawer is not sufficient by itself. Engineering implements actual destination state when selected, separates it from governed data state, and returns material substitutions to the designer with their reasons. The opening's visual quality does not establish the quality of working destinations.

Use the analyst's [analytical coverage](../../omni-data-analyst/references/analytical-coverage.md) before adding content: identify the valid comparison, population, timeframe, denominator and exact detail that each destination can support. More panels do not necessarily add understanding. Keep unsupported insight, unavailable dimensions and differently scoped populations explicit.

Resolve available space before freezing the composition: first-view priority; title/control wrapping; minimum readable chart/table region; deliberate vertical/horizontal scrolling; and what moves, collapses or becomes a destination when width **or height** is insufficient. Keep essential scope and qualification visible. Avoid universal no-scroll rules, viewport-sized heroes that ignore host chrome, and whole-interface scaling to rescue an oversized design. Use [App patterns](../../omni-app-designer/references/app-patterns.md#design-for-the-space-the-app-actually-gets) for a concrete handoff card.

Branding hands over imagery roles, source/use context, placement, crop/focal point, narrow behavior, alt/decorative treatment and fallback. Atmospheric images cannot silently identify data rows or imply operating results. Resolve fonts, loading paths and asset budgets with engineering before freezing an infeasible composition. Keep essential scope/qualifications visible across views.

Treat display aliases as a separate [authorized presentation mapping](../../omni-branding/references/demo-presentation.md), not permission implied by brand assets. Preserve source IDs/names and the original evidence path; never group, join or calculate by a display alias. For native Apps, require engineering's [data-input contract](../../omni-app-engineer/references/native-data-input.md) as an explicit relevant dependency: CLI export headers, local fixtures and native callback keys may differ. An unobserved callback remains unobserved even when a shape-compatible simulation succeeds.

For each apparently quantitative visual feature, name the source field, unit, scale and exact-value alternative. A pipe can represent a documented additive contribution, or be decoration clearly separate from the evidence; it cannot establish a physical process. A spatial scene cannot invent coordinates. If the chosen form obscures comparison, keep the expressive identity and replace the analytical encoding.

Native dashboards retain their own reading path, supported layout and control capabilities. A brand-led App introduction is not a dashboard requirement. Source-faithful migration obligations remain in force; visual preference is not a change in semantic or migration authority. Route actual missing grain, identity or measures through the existing backend handoff.

## Build the first complete journey early

For substantial new work, select one representative `entry → primary action → useful evidence/detail → return` path and assemble it before expanding the rest of the experience. Include the selected assets, real query contract and one consequential loading/error or constrained-layout state. Engineering qualifies the critical callback, asset, media or live-refresh path before the whole composition depends on it; metadata, configured allowlists and a local fixture are not observed target behavior. When a capability is unresolved, keep the path useful with its declared fallback and open requirement.

The experience owner critiques the assembled path; QA independently checks its relevant outcomes. Repair concrete findings within the existing authorization, then carry useful behavior to other destinations while choosing their treatment deliberately; consistent or repeated composition is valid when the task warrants it. Use only permitted observation methods. Internal comparison and reversible correction do not require a customer selection unless a consequential preference remains unresolved. A small edit reuses the current path and examines only affected behavior.

## Review against the original request

Trace `user requirement → selected design → implemented behavior → actual observation`. Begin with the first complete journey, then give every consequential destination a review disposition for its purpose, focal content, action, useful detail and return at relevant usable dimensions. Name specific deviations and affected cases; use the existing [experience review](experience-review.md) and [design evidence](../../omni-qa-analyst/references/design-evidence.md). A passing opening view cannot close an uninspected workspace or required media path.

When browser/rendering is prohibited, continue authorized implementation and have an independent reviewer trace those relationships in source. Retain the report as declared evidence; leave craft/native visual requirements `not_run` where their required observations were not made. No new source-only “polish pass” is created. Native readback proves saved content, not live control behavior; a screenshot supports composition, and interactions require actual exercise. Positive feedback records the response given, not full usability or production acceptance.

Close out with the selected choice, current implementation, observation and remaining difference for each required surface. Changing the selected experience reopens affected visual work without rewriting historical evidence or automatically restarting metric discovery.
