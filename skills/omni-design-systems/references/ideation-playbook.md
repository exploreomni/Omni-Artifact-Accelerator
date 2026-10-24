# From need to a testable concept

Use for a new app/dashboard concept or a meaningful change to how people work. For net-new products or product reconception, the package's [data-first workflow](../../omni-artifact-accelerator/references/data-first-product-workflow.md) requires A–C evidence/narrative, artifact discovery, exactly three viable product options and the user's selection before detailed design. These are package workflow requirements, not vendor process rules. Reuse decisions and authorization for focused work or a continuation of an already selected product.

## Choose the amount of discovery

| Assignment | Useful next artifact |
| --- | --- |
| New product or explicit product reconception | A–C analytical handoff, artifact brief, three materially different viable options, then actual user selection and resolved design |
| Focused enhancement | The affected task, the uncertain choice, and a comparison only if alternatives would change the decision |
| Faithful migration | Source behavior and unknowns, plus target adaptation where necessary; do not manufacture a redesign exercise or retire source functionality |
| Specified design or small wording/style fix | Make the scoped change and perform relevant checks; reopen discovery only for a consequential conflict |

For migrations, an attractive concept is not authority to change calculations, interactions, layout intent, security, or operations. Preserve the [behavior contract](../../omni-qa-analyst/references/migration-behavior.md) and selected source route. Unknown Sigma layout stays unknown. A missing route holds dependent target work; source discovery can continue. Native dashboards and native Omni Apps stay distinct; an external application needs the user's explicit selection.

## Brief and assumptions

For a material experience, retain the [shared experience brief](experience-brief.md) in the current design/intent records. Separate missing context from stated expectations lost in translation. A user asking for an expressive frontend has supplied a requirement even when exact typography or geometry still needs design work; do not reset that ambition to the default analytical layout.

Start with the decision or task, not a list of screens. The designer states the evidence relationship, proposed task path and rationale before retrieving optional examples; a user-selected reference is the exception. Use actual conversations or supplied evidence to establish the workflow. If that evidence is absent, label the concept a hypothesis. Examples can test a choice, not dictate a shell; intentional similarity is acceptable when justified.

Reusable output card; shorten or omit fields that add no value:

```yaml
concept: <name and version>
scope: <new / enhancement / faithful migration / approved redesign>
surface: <native Omni dashboard / native Omni App / explicitly selected external app>
user_and_situation: <who, when, available attention, input context>
task_and_outcome: <what they need to decide or accomplish>
current_workflow_evidence: <source reference, observation, or unknown>
friction: <observed difficulty, separate from interpretation>
visual_direction: <reference qualities to borrow/avoid, focal element, density, brand authority>
essential_capabilities: <small set tied to the outcome>
constraints_and_exclusions: <access, definitions, source parity, branding, target limits>
open_assumptions: <id, claim, evidence, consequence if wrong, smallest useful test>
success_observation: <what an observer could see during the task>
status: proposed
```

Prioritize assumptions with both serious consequences and weak evidence. A semantic assumption goes to the analyst/BI engineer or [backend handoff](../../omni-backend-handoff/SKILL.md); a visual prototype cannot settle it. A selected runtime dependency such as a native callback, media player or remote refresh goes to engineering for a bounded qualification before composing the whole experience around it. A usability assumption may be explored with a task test. Do not conflate a user's requested feature, observed problem, inferred explanation, and selected solution.

## Compare concepts before polishing

If the uncertainty is frontend treatment, hold audience, question, data and key action constant while changing composition, navigation, type/image balance or disclosure. Comparing different business tasks can settle product scope, but cannot by itself resolve the original visual question. Use the [same-task context studio](experience-context-studio.md) to practice this distinction.

For new products/reconception, develop exactly three viable concepts with comparable quality and the same core analytical narrative. Vary experience structure, investigation path, focal visualization or interaction rather than merely colors. Present concrete comparable concepts, recommend with reasons and wait for the user's selection. Do not impose the same three archetypes across engagements. For focused work or an already selected product, direct exploration remains appropriate; retain the existing decision and affected scope. Neither route has a universal novelty score or fixed UI template.

Render the selected treatment, and any alternatives being compared, using representative data/context and relevant constrained layouts. Use [visual craft](visual-craft.md) to resolve the screen; preserve render references and distinguish prototype, native and human observations. The optional [design evidence record](../../omni-qa-analyst/references/design-evidence.md#specification) records the direct/compare choice. Prose and structure checks cannot establish typography, proportion, density or polish.

Use a comparison card: `concept → task path → advantages → tradeoffs → unsupported assumptions → prototype decision and rationale`. Assess the relevant criteria: task clarity, faithful coverage, inspection effort, accessibility, target feasibility, and maintainability. Selection for a local prototype is a working decision, not business acceptance or publication permission.

For new products, retain the actual user selection; an agent recommendation cannot replace it. After selection, resolve detailed design and follow the [first complete journey](experience-brief.md#build-the-first-complete-journey-early) through the assembled candidate. An attractive opening alone leaves the rest unresolved. Routine choices within an already selected product need no new concept vote. Under no-rendering constraints, source/interaction rehearsal can expose structural faults while visual judgment remains unobserved.

### Synthetic worked example: inventory investigation

**Synthetic stage-E teaching example, not a live engagement:** assume A–C have established scoped access, available-unit definitions, verified inventory comparisons and a refresh-safe narrative, and D identified the warehouse analyst's investigation task. Target: a read-only native Omni App. These assumed teaching inputs are not evidence of actual access, queries, interviews or runtime qualification. A real engagement must obtain its own evidence first.

| Concept | Task path and tradeoff | Decision |
| --- | --- | --- |
| A. Exception comparison with item dossiers | Compare inventory exceptions, inspect evidence alongside the list and return with context. Optimizes cross-item decisions; narrow layouts need staged detail. | Proposed; explain the tradeoff and request user selection. |
| B. Guided evidence investigation | Start from a supported question, follow scoped comparisons to affected items and inspect exact records. Optimizes explanation; repeated use needs a direct route. | Proposed; uses the same inventory claims through a different investigation path. |
| C. Inventory relationship explorer | Navigate supported location/category relationships, compare contributions and open item evidence. Optimizes relationship discovery; needs a readable table alternative. | Proposed; include only relationships qualified in A–C. |

**Annotation:** no option is selected. Recommend based on the actual audience and narrative, then wait for the user's choice. Changed or unresolved metric definitions reopen B/C. None of these teaching concepts adds purchasing/writeback, and their three structures are not a prescribed set for other products.

## Match fidelity to the question

| Uncertainty | Smallest useful artifact | What it cannot establish |
| --- | --- | --- |
| Purpose, features, or grouping | Brief, sketches, information map | User demand or agreement without evidence |
| Navigation, selection, or recovery | Clickable key path with relevant alternative/error states | Native runtime, effective access, or numerical correctness |
| Density, typography, long labels | Rendered representative screen at agreed sizes | End-to-end usability from a screenshot |
| Data bridge, permissions, or performance | Bounded implementation investigation owned by engineering/QA in the verified target | Production readiness from a local fixture |

If the user selects example A, prototype list selection, narrow-screen return, and a filter change that removes the selected item. Use labeled synthetic short/long labels and empty/partial results for bounded rehearsal. Ask independent QA to use [the usability-testing guide](../../omni-qa-analyst/references/usability-testing.md); record observations separately from proposals. Without participants, mark usability not tested. A prototype is not the complete selected product.

## Source basis and applicability

Checked **2026-10-21**. The workflow and cards above are our analytics adaptation. These sources establish design practices, not Omni features or asset rights.

| Source / evidence type | Guidance used and platform boundary |
| --- | --- |
| [Apple: Ask questions](https://developer.apple.com/tutorials/develop-in-swift/ask-questions?language=o_4) — official tutorial | Understand goals, routines, friction, and repeated observations. Transfer the discovery method; the example app and native implementation are not requirements. |
| [Apple: Create UI prototypes using agents in Xcode, WWDC26](https://developer.apple.com/videos/play/wwdc2026/227/) — official video transcript / demonstration | Constrain prompts, explore divergent options, and retain human judgment. Transfer those practices; Xcode, SwiftUI, and Apple assets are not Omni dependencies. |
| [Apple: 60-Second Prototyping, WWDC17](https://developer.apple.com/videos/play/wwdc2017/818/) — historical official process demonstration / transcript | Try interactions cheaply and learn in context. Its title is not a delivery-time promise. |
| [Google: Design Sprint methodology](https://designsprintkit.withgoogle.com/methodology), [assumptions mapping](https://designsprintkit.withgoogle.com/methodology/phase2-define/assumptions-mapping), and [Crazy 8s](https://designsprintkit.withgoogle.com/methodology/phase3-sketch/crazy-8s) — official process guidance | Use uncertainty to focus learning and rough alternatives to broaden ideas. This package does not require a fixed sprint, duration, or sketch count. Indexed text was reviewed; direct page extraction is limited by JavaScript. |
