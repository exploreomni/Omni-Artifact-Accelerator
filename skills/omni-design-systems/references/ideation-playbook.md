# From need to a testable concept

Use for a new app/dashboard concept or a meaningful change to how people work. These are package recommendations, not mandatory vendor process gates. Reuse discovery, decisions, brand answers, and authorizations already available. Scale the exercise to the uncertainty; continue authorized local sketches and prototypes without inventing another approval step.

## Choose the amount of discovery

| Assignment | Useful next artifact |
| --- | --- |
| New concept or substantial workflow redesign | Brief, important assumptions and a reasoned direct prototype choice, or comparative treatments when they resolve a material uncertainty |
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

Choose direct or comparative exploration with a brief rationale. A direct choice still needs rendered review of the selected candidate when permitted. When uncertainty warrants comparison, vary information grouping, composition or interaction rather than merely colors, using only enough alternatives to resolve that uncertainty. State required features, source constraints and excluded behavior; preserve rejected choices briefly. There is no fixed concept count or novelty score.

Render the selected treatment, and any alternatives being compared, using representative data/context and relevant constrained layouts. Use [visual craft](visual-craft.md) to resolve the screen; preserve render references and distinguish prototype, native and human observations. The optional [design evidence record](../../omni-qa-analyst/references/design-evidence.md#specification) records the direct/compare choice. Prose and structure checks cannot establish typography, proportion, density or polish.

Use a comparison card: `concept → task path → advantages → tradeoffs → unsupported assumptions → prototype decision and rationale`. Assess the relevant criteria: task clarity, faithful coverage, inspection effort, accessibility, target feasibility, and maintainability. Selection for a local prototype is a working decision, not business acceptance or publication permission.

Make a reasoned working selection when the brief supports it; do not turn every internal alternative into a customer question. Before expanding a substantial App, follow the [first complete journey](experience-brief.md#build-the-first-complete-journey-early) through the actual assembled candidate. This tests how the entry, working view and detail connect; an attractive opening alone leaves the rest of the experience unresolved. Under no-rendering constraints, source/interaction rehearsal can expose structural faults while visual judgment remains unobserved.

### Synthetic worked example: inventory investigation

**Illustrative net-new request:** a warehouse analyst needs to inspect low-stock exceptions and understand the evidence before using an existing purchasing process. Target: native Omni App, read-only. No interviews or runtime checks have occurred. The definition of “available units” is pending analyst review; fixture values are synthetic.

| Concept | Task path and tradeoff | Decision |
| --- | --- | --- |
| A. Exception list with item detail | Scan comparable items, select one, inspect supporting values. Preserves the surrounding list at wide sizes; density needs testing. | Choose for a provisional interaction prototype because the stated task centers on comparing exceptions. |
| B. Guided item lookup | Enter an item, then inspect its evidence. Direct when the item is known; poor fit for discovering unknown exceptions. | Retain as an alternative if discovery shows that analysts usually start with an item ID. |
| C. Overview followed by investigation | Start with aggregates, then navigate to exceptions. Useful for monitoring; adds a step and depends on unsettled KPI definitions. | Defer the summary claims; do not invent a headline metric to complete the design. |

**Annotation:** this selection follows the illustrative task, not user-test evidence. Assumption A1 is that comparing several items matters more than finding one known item. A small task test can challenge A1. Assumption A2 is the meaning of available units; route that to the model/metric owner. Neither a successful prototype nor a preferred layout resolves A2. No concept adds purchasing/writeback.

## Match fidelity to the question

| Uncertainty | Smallest useful artifact | What it cannot establish |
| --- | --- | --- |
| Purpose, features, or grouping | Brief, sketches, information map | User demand or agreement without evidence |
| Navigation, selection, or recovery | Clickable key path with relevant alternative/error states | Native runtime, effective access, or numerical correctness |
| Density, typography, long labels | Rendered representative screen at agreed sizes | End-to-end usability from a screenshot |
| Data bridge, permissions, or performance | Bounded implementation investigation owned by engineering/QA in the verified target | Production readiness from a local fixture |

For example A, prototype list selection, narrow-screen return, and a filter change that removes the selected item. Use synthetic short/long labels and empty/partial results. There is no need to build a complete application to learn whether this flow is understandable. Ask independent QA to use [the usability-testing guide](../../omni-qa-analyst/references/usability-testing.md); record observed findings separately from proposed changes. Without participants, deliver the test plan and mark usability not tested.

## Source basis and applicability

Checked **2026-10-21**. The workflow and cards above are our analytics adaptation. These sources establish design practices, not Omni features or asset rights.

| Source / evidence type | Guidance used and platform boundary |
| --- | --- |
| [Apple: Ask questions](https://developer.apple.com/tutorials/develop-in-swift/ask-questions?language=o_4) — official tutorial | Understand goals, routines, friction, and repeated observations. Transfer the discovery method; the example app and native implementation are not requirements. |
| [Apple: Create UI prototypes using agents in Xcode, WWDC26](https://developer.apple.com/videos/play/wwdc2026/227/) — official video transcript / demonstration | Constrain prompts, explore divergent options, and retain human judgment. Transfer those practices; Xcode, SwiftUI, and Apple assets are not Omni dependencies. |
| [Apple: 60-Second Prototyping, WWDC17](https://developer.apple.com/videos/play/wwdc2017/818/) — historical official process demonstration / transcript | Try interactions cheaply and learn in context. Its title is not a delivery-time promise. |
| [Google: Design Sprint methodology](https://designsprintkit.withgoogle.com/methodology), [assumptions mapping](https://designsprintkit.withgoogle.com/methodology/phase2-define/assumptions-mapping), and [Crazy 8s](https://designsprintkit.withgoogle.com/methodology/phase3-sketch/crazy-8s) — official process guidance | Use uncertainty to focus learning and rough alternatives to broaden ideas. This package does not require a fixed sprint, duration, or sketch count. Indexed text was reviewed; direct page extraction is limited by JavaScript. |
