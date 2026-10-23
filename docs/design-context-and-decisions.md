# Turning design intent into an App experience

This guide explains a design failure, the decisions that corrected it, and the context future engagements need to retain. It comes from a branded coffee-demo App that passed source/local-state checks and CLI content/query verification but felt like a generic dashboard inside an App. Native SDK and control behavior remained unverified. The revised experience received positive qualitative feedback after its opening, navigation and working views were redesigned.

**The main gap was translation, not a lack of design references.** The user had already asked for website-quality craft, expressive branding, useful animation and specialized interactions. Those requirements lost priority when the working specification became a compact analytical page. More reference material alone would not have corrected that decision.

This is a reusable rationale, not a universal layout or a claim of production acceptance. Engagement-specific assets, tenant information, query results and detailed evidence belong in the engagement workspace.

## Context that was available, missing or misinterpreted

| Context | What went wrong | Required design response |
| --- | --- | --- |
| Website-quality frontend, already requested | Treated as better typography and colors around an analytical layout | Resolve the opening composition, navigation, primary action and working experience explicitly. |
| Official website and logo, already supplied | Identity compliance became the practical endpoint of branding | Translate brand character into hierarchy, imagery roles, spacing and interaction choices as well as tokens. |
| Elegant, meaningful animation, already requested | A useful transition existed only in an optional comparison step | Consider motion along the primary journey; retain an immediately usable static equivalent. |
| An analytical App, already requested | A sequence of tasks became regions on one continuous page | Choose actual destinations when the task warrants them, and distinguish navigation from filtering or scrolling. |
| Immersive first encounter versus direct workspace, not yet resolved | The designer implicitly chose a compact workspace | Reuse stated intent or ask one short question that distinguishes workspace-first, story-first and branded entry into a workspace. |
| Concrete art direction, not resolved deeply enough | Logo, colors and fonts stood in for a complete composition | Resolve type/image balance, content density, focal point, action hierarchy, imagery treatment and narrow behavior. |
| CLI/MCP-only workflow with no browser, already known | Source checks left visual risk unresolved | Respect the tool boundary, review the source against the selected experience, and keep rendered quality unobserved. |
| Trustworthy analytical behavior, already implemented | Technical completeness risked becoming a proxy for design quality | Keep numerical, interaction, visual and human-review evidence separate. |

The user should not have to repeat a quality ambition every time a specialist takes over. The orchestrator must carry it into concrete decisions and the designer must show how the implementation expresses it.

## Why the first design missed

The first concept had a legitimate analytical task: explain monthly sales change, inspect product contributions and compare trajectories. It used an official logo, a coherent palette, useful filters, exact tables and pinning. Those were valuable foundations.

The specification nevertheless directed the engineer toward a compact identity strip, one large change statement, a contribution view, a product ledger and comparison beneath them. It explicitly discouraged a large editorial opening. The engineer therefore implemented a dashboard-like composition consistent with the selected specification.

The alternatives did not resolve that mismatch. One emphasized product contribution and another store comparison. Their business questions differed, so rejecting the store concept did not answer which frontend treatment best expressed the original brief. Future frontend alternatives should hold audience, question, data and key action constant while varying composition, navigation and disclosure.

The decisive clarification selected **an immersive branded entry with a focused analytical workspace**. That choice joined the expressive opening and the analytical task in one experience contract.

## Decisions that changed the experience

| Decision | Reason and tradeoff |
| --- | --- |
| Separate the entry, investigation and comparison destinations | Each view has a distinct job and composition. Additional navigation is justified only if it reduces competing content or supports a meaningful task. |
| Give the entry one concise promise and useful investigation actions | Brand expression leads into the actual work. Returning users can bypass the introduction through persistent navigation. |
| Use a deliberate editorial image and stronger type hierarchy | Imagery and scale establish character. The image is atmospheric, explicitly separate from the fictional data, and unnecessary to interpreting results. A typography-led entry is also valid. |
| Make investigation a discovery/list-detail workspace | Selecting an item adds a trajectory, exact observations and context. Detail earns its space through new evidence. |
| Give comparison its own zero-, one- and two-selection states | People can begin, continue and recover without encountering a large unexplained empty chart. |
| Preserve scope, selection and pins through navigation | Changing destination must not silently change the analytical question. View state and governed data state have separate responsibilities. |
| Adapt narrow screens into deliberate list/detail stages | Reflow preserves the task rather than stacking every desktop region into one long page. Exact evidence and a useful return remain available. |
| Use brief, interruptible destination/detail transitions | Motion explains what changed. Values update immediately; reduced motion reaches the same usable state without movement. |
| Preserve the existing calculation and query contracts | A frontend problem does not require a backend rebuild. Data Model Accelerator receives actual semantic gaps, not styling work. |

The revision changed several things together. Positive feedback supports the overall direction; it does not establish that the image, typography or navigation alone caused the improvement.

## Turning references into design choices

Famous brands communicate a quality ambition, not a reproducible specification. Record the qualities being borrowed and the decisions they affect. Examples include an editorial opening, a deliberate type/image relationship, restrained competing elements, recognizable actions, progressive disclosure and spatial continuity.

These are package recommendations. Do not describe them as a vendor certification or imply that an analytical App inherits a native platform's controls, capabilities or accessibility guarantees. The [vendor guidance](../skills/omni-design-systems/references/vendor-guidance.md) and [App patterns](../skills/omni-app-designer/references/app-patterns.md) retain source context and platform boundaries. This retrospective does not re-audit those external sources.

An effective reference note says: “Borrow the large editorial introduction and direct route into the task; avoid an obligatory tour and hidden filters.” “Make it premium” or “make it like a famous website” leaves the material design decisions open.

## Lessons from a spatial food-service demo

A later CLI-only demo made the remaining gaps more concrete. Its branded entry, map, analytical pipes and product investigation improved through explicit task composition, interaction repairs, usable laptop dimensions and authorized display aliases. These are implementation lessons, not a reusable mandate for four screens, 3D maps or physical props. Positive user feedback is qualitative evidence; native rendering and interaction were not independently observed in that workflow.

| Gap | Reusable correction | Owner and evidence boundary |
| --- | --- | --- |
| The query ran, but the frontend expected export column labels rather than the selected callback keys | Retain the exact transport envelope, field identities/types, result completeness and state behavior; exercise the assembled receive path with independent expectations. | BI/App engineering and QA; simulated callbacks remain simulation. See [native data input](../skills/omni-app-engineer/references/native-data-input.md). |
| An unbuilt template was opened as the experience | Distinguish template, assembled candidate, local teaching preview and authenticated native entry; supply the usable entry link. | App engineer; a local file does not carry a native host's runtime. |
| Width-only layout assumptions produced an oversized first screen | Specify available content width and height, surrounding controls, first-view priorities and deliberate scroll behavior. | Designer/engineer; source layout checks do not establish rendered fit. |
| Brand assets and source vocabulary described different worlds | Ask whether original, verified customer or authorized fictional names are intended. Apply aliases only as a presentation layer, with exact identity and numerical preservation. | Branding/analyst/storytelling; [demo naming](../skills/omni-branding/references/demo-presentation.md) does not establish product equivalence or actual store geography. |
| Expressive objects risked implying unsupported facts | State which properties encode a metric and which are props. Keep exact detail available; distinguish contribution pipes from physical transport and demo references from geocoded stores. | Designer/analyst/motion; no implied volume, throughput or routes without supporting data. |
| Navigation lost focus, changed selection or intercepted page scrolling | Specify entry/exit, retained scope/identity, focus return, explicit excluded-item states and opt-in map gestures. | App designer/engineer; real input and assistive behavior require observation. |
| Earlier notes still described superseded decisions as current | Derive orientation from selected intent, identify historical proposals in `START_HERE.md`, and recheck saved packets before resuming. | Orchestrator; [packet-check](../skills/omni-artifact-accelerator/references/design-intent.md#current-context-and-resume) validates declared inputs only. |

Keep private data, brand assets and detailed tenant receipts in the engagement. The original [context studio](../skills/omni-design-systems/references/experience-context-studio.md) transfers these lessons using a synthetic library task. Existing composition, identity and versioning guidance already covered part of the problem; concrete handoffs and affected-path checks make those instructions operational.

## A compact discovery and handoff record

Reuse existing answers first. Ask only for unresolved choices that materially affect the work. Do not turn this into a mandatory questionnaire for a small correction.

| Decision to retain | Useful question when missing |
| --- | --- |
| Audience and action | Who uses this, and what should they understand or do? |
| Experience mode | Should people enter the workspace immediately, follow a story, or start with a branded introduction? |
| Brand authority | What is the official website or brand guide, and which logo should be used? May the agent source it, or is no logo intended? |
| Reference qualities | Which aspects of the examples matter: composition, imagery, typography, navigation or interaction? What should be avoided? |
| Assets | Which images are approved, what role does each play, and what should appear if it is unavailable? |
| First and repeat use | What is the first useful action, and how does a returning user reach the work directly? |
| Scope and continuity | Which filters, identities and selections must persist through navigation and responsive changes? |
| Constraints and evidence | Which native surface, tool restrictions, usable content width and height, scroll behavior and review opportunities govern the result? |
| Presentation names | Should original source names remain, or are verified replacements or explicitly fictional demo aliases intended? Logo authorization does not answer this. |

Record the selected answers in the existing [design-intent record](../skills/omni-artifact-accelerator/references/design-intent.md) and resolved design; this guide adds no new required schema or approval stage. Include a destination table with visible content, primary action, entry/exit, retained state and focus return. For a single-screen App, document why that is the selected experience.

For an image, retain source, role, rights context, crop/focal point, narrow treatment, accessible description and fallback. For typography, retain display/body roles, permitted font assets and fallback. For motion, retain trigger, purpose, interruption and reduced-motion behavior. For charts, retain scale, units, exact evidence and the difference between selection and query scope.

## Specialist ownership

| Role | Context it must preserve |
| --- | --- |
| Orchestrator | User intent, selected experience, existing answers, completion scope and unresolved evidence. |
| Branding + design systems | Brand authority, assets and provenance; the bridge from brand qualities to composition, typography and semantic color. |
| App designer | Same-task alternatives, first encounter, destination map, narrow behavior and implemented-result critique. |
| Dashboard designer | A monitoring/exploration composition suited to the native dashboard; supported controls and hierarchy rather than an imported App landing page. |
| Data analyst + BI engineer | Metric meaning, population, units, exact identities, query bindings and independent expectations. |
| Data storyteller | A clear promise and evidence-backed findings without invented causes or operating claims. |
| Motion designer + App engineer | Useful transitions, actual view state, retained context, focus/recovery and runtime constraints. |
| QA analyst | Independent checks of affected behavior, separate evidence lanes and unresolved visual risks. |
| Artifact translator + backend handoff | Source behavior and approved migration departures; genuine semantic gaps routed to Data Model Accelerator with their evidence. |

These are responsibilities, not a requirement to launch every specialist on every task. Use the smallest useful team. A design handoff is incomplete if engineering still has to guess the main composition or silently substitute an entirely different experience.

## How to assess the result

For substantial design work, compare visibly different treatments of the same task when rendering is permitted, implement the selected direction, and review the actual result. Start with the opening, working view, meaningful transition and narrow state. Use the existing [experience review](../skills/omni-design-systems/references/experience-review.md) to identify a specific correction rather than adding decorative effects.

When rendering is prohibited, an independent reviewer can trace destinations, imagery roles, action outcomes, state continuity and the motion/static counterpart in the source. This improves the candidate but cannot establish visual polish or native usability. It also does not justify ignoring the user's tool restriction.

| Evidence | What it establishes |
| --- | --- |
| Numerical checks | Tested calculations and interpretation within the checked scope. |
| Source/local-state checks | Inspected or exercised implementation behavior, with mock and runtime limits retained. |
| Native content readback | What was saved or published; not whether every interaction worked. |
| Rendered review | Observed composition at the inspected states and widths; behavior only when the relevant interactions were actually exercised. |
| Positive user reaction | Direct qualitative feedback on the result; not full usability, accessibility or production acceptance. |

The case received an explicit positive reaction after revision. The agent had not performed a browser-rendered inspection. Both facts remain true; neither should be hidden by a generic “passed” label.

## Where the correction lives

The current guidance carries these lessons through [orchestration](../skills/omni-artifact-accelerator/SKILL.md), [App design](../skills/omni-app-designer/SKILL.md), [experience modes and destinations](../skills/omni-app-designer/references/app-patterns.md), [engineering](../skills/omni-app-engineer/SKILL.md), [visual craft](../skills/omni-design-systems/references/visual-craft.md) and [critique](../skills/omni-design-systems/references/experience-review.md). The [shared curriculum](../skills/omni-design-systems/references/experience-curriculum.md) supplies practice and references; these corrections make the selected experience harder to lose during handoff.

Preserve the boundaries: single-screen Apps can be excellent; focused workspaces may need no imagery; native dashboards should prioritize their analytical job; faithful migrations retain source behavior unless changes are selected. A hero, photograph, animation or three-view structure is not a universal requirement. The reusable standard is a deliberate experience whose composition and behavior express the user's intent.
