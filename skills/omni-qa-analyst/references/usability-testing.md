# Usability tests and design critique

Use for a new analytical experience, a material redesign, or a demonstrated comprehension problem. For a focused change, test the affected task rather than repeating discovery. These are package recommendations informed by Apple's official [Test your app](https://developer.apple.com/tutorials/develop-in-swift/test-your-app) and [Validate your app](https://developer.apple.com/tutorials/develop-in-swift/validate-your-app) tutorials, reviewed 2026-10-21: observe task attempts, avoid coaching, distinguish observations from interpretations, and iterate. Their native development context does not establish Omni capabilities.

## Choose the question and evidence

Start with a consequential uncertainty: can the intended viewer identify the period, distinguish a percentage-point change, recover from a filter, or inspect a driver without losing context? Select the least expensive artifact that can answer it. A wireframe can test grouping; an interactive prototype can test transitions; only the actual target with real bindings can establish native behavior. Mark synthetic data and mocked actions visibly.

Keep these evidence categories separate:

| Evidence | Can support | Cannot establish |
| --- | --- | --- |
| Specialist critique | A reasoned design concern or proposed improvement | Observed user behavior |
| Agent rehearsal | Discoverability of instructions, internal inconsistencies, a testable hypothesis | Human comprehension, human task time, assistive-technology usability |
| Observed participant task | What those participants did on that exact version and setup | Population-wide success, correct metrics, native implementation if a mockup was tested |
| Numerical/native/access QA | Verified values, target behavior, or permissions in the tested context | That a user understands the decision or business acceptance |

No participants available: deliver the runnable test script, mark participant testing `not_run`, and continue authorized implementation with the limitation visible. Do not invent quotes, participants, timings, acceptance, or a pass rate. An agent role-playing a viewer is an agent rehearsal.

## Prepare and run a task

1. Link the candidate version, task, surface, metric/query versions, active filters, persona, fixture, viewport/input method and relevant migration source IDs. Freeze expected answers from original data and the analyst's definitions before comparing with the implementation. A designer's displayed total is not an oracle.
2. Write a realistic goal without naming the control or providing the answer. Example: “Find which team needs investigation this week and show the evidence you used.” Avoid “Click the red Harbor row.” Keep moderator answers separate from the participant prompt.
3. Observe the attempt without coaching. Record assistance if given, hesitation, errors, interpretation and outcome. Ask what the person expects or what the display means; avoid questions that suggest the desired response. Respect permission and privacy for recording or sharing participant material.
4. For consequential comprehension, ask the participant to explain the period, population, comparison and supporting evidence in their own words. Record whether the next action follows from the displayed evidence; do not require a causal explanation from a descriptive dashboard.
5. Separate observation, interpretation and proposed remedy. Change the owning design or implementation, pin the revision and retest affected tasks. When comparing concepts, keep task/data conditions comparable and record presentation order or prior exposure; do not call informal preference a controlled experiment.

Choose completion/error/assistance and comprehension measures appropriate to the task. Record elapsed task time only when actually measured, with the setup. Set any success criteria with the engagement; no universal time limit, participant count or pass threshold is implied.

## Reusable task and finding card

Store a scoped card in the engagement's `evidence/` or `deliverables/` and reference it from `contracts/qa.json`. The following is an authoring shape, not a new machine-validated schema. Use existing case statuses `pass|fail|blocked|not_run|not_applicable`; distinguish an execution outcome from participant completion.

| Field | Record |
| --- | --- |
| Identity and purpose | Case ID, user task, question/hypothesis, source asset/control IDs if migrating |
| Version and setup | Candidate path/hash, input/query/metric pins, persona, fixture, surface, viewport/zoom, input or assistive technology |
| Evidence category | Specialist critique, agent rehearsal, observed participant task, or native QA |
| Participant prompt | Goal and starting conditions without the answer or suggested control |
| Moderator expectation | Independently derived answer/allowed actions, criterion and original evidence reference; exclude from participant view |
| Execution | Status, actual observation, completion, help/errors, timing only if measured, evidence references |
| Finding | Observation → interpretation → proposed revision; severity tied to decision impact |
| Follow-through | Owning specialist, affected requirements/consumers, revision, retest result or `not_run` |

Keep personal information out of broadly shared deliverables. A pseudonymous participant identifier and relevant role/context normally suffice.

## Worked comprehension exercise — entirely synthetic

Scenario: an operations viewer compares completed orders delivered on time across two complete seven-day periods. The exercise defines rate as `sum(on_time) / sum(completed)`; the table is the raw fixture, not a tenant query result. These labels are not Omni field IDs. There is no approved business target or causal evidence.

| Team | Previous on time | Previous completed | Current on time | Current completed |
| --- | ---: | ---: | ---: | ---: |
| Cedar | 70 | 100 | 90 | 100 |
| Harbor | 8 | 10 | 1 | 10 |

**Participant prompt:** “How did overall on-time performance change? Which team would you investigate, and why? Show the evidence behind your answer.”

**Moderator expectations, hidden during the task:** overall current rate is `91/110 = 82.7%`; previous is `78/110 = 70.9%`. The change is **+11.8 percentage points** (or **+16.7% relative**, if explicitly labeled). Harbor fell from 80% to 10% despite the improving total. Averaging current team percentages gives 50%, which is the wrong aggregation for this definition. Investigation is warranted by the discrepancy; its cause and any contractual breach remain unknown.

**Critique hypothesis:** a green overall KPI without visible team context may conceal the local decline. Proposed refinement: identify the comparison period beside the KPI and make the team breakdown discoverable, using stable category identity and labeled change. Test whether this actually helps; no participant observation or preferred layout is asserted here.

**Starting result:** `not_run`. Candidate, participant, observation, duration and retest are unset. Correct fixture arithmetic alone cannot close the usability case.

## Additional fixtures and tasks

Select a small relevant subset rather than running every case for every wording change.

| Variation | Task or expected invariant |
| --- | --- |
| Long names, negative values, high precision, many categories | Find and compare an exact value without clipped meaning; verify sorting uses values rather than formatted strings |
| Missing period or NULL denominator; zero rows | Explain what is unknown; never read missing results as zero performance |
| Filter returning no matches | Recover using supported controls without losing unrelated scope; active filter context stays visible |
| Slow/error response after a newer selection | Newest selection owns the display; stale/partial results are labeled and do not masquerade as current totals |
| Selected item absent after filtering | Confirmed exclusion clears detail with a scope explanation; a partial/paginated result leaves membership unconfirmed rather than claiming exclusion; denied access protects content and identifiers |
| Narrow → wide layout, enlarged text, keyboard input | Selected item, filter scope, reading order and usable focus survive supported reflow; an expanded view recovers sensibly |
| Denied persona | Restricted information stays protected; availability of a recovery action does not imply permission to widen access |
| Migration with repeated placements and local filters | Find the same scoped answer in source and target; record intentional changes separately from parity |

Use supported controls only. Where a needed action is unavailable, record the capability gap and a scoped alternative; do not silently replace a native dashboard with an App.

## Critique and handoff

For repeatable file/version checks, use the optional [design evidence contract](design-evidence.md). Keep craft critique, native observation and participant testing in their own lanes. Compare the selected rendered design with the exact implemented version; retain annotated captures, actual versus intended behavior, designer disposition and affected retest. Material new/redesign work records a reasoned direct direction or a comparison where it resolves uncertainty; a title correction or faithful migration does not require a new concept exercise. A document or screenshot pin proves retained bytes, not reviewer independence or a successful task.

The designer explains the concept choice and tradeoff. The analyst reviews meaning and independent examples; the storyteller reviews claim strength and comparison wording; engineering reviews feasibility; QA owns observations and findings. Branding and motion participate when those choices affect the task. This review can run inline for small changes with its independence limitation stated; it does not require a new team or approval ceremony.

Record actionable findings against task, candidate, evidence and owner. Fixes to layout/copy reopen affected comprehension and accessibility checks; query/filter/metric changes reopen numerical and related interaction checks. Route actual semantic gaps through the existing backend handoff with affected consumers and independent cases. Maintain separate usability, native, access and business-acceptance results in `START_HERE.md`.

## Prompting and internal revision evidence

Use the engagement run log from [first delivery](../../omni-artifact-accelerator/references/first-delivery.md#transfer-and-qualification) to distinguish material clarification, a repeated question, correction of a supplied requirement, and a new customer preference. Preserve actual message references, the initial candidate and the internally reviewed first delivery. Count internal revisions separately. A synthetic trial with no customer follow-up provides no evidence of customer satisfaction or real-world prompting reduction.

Before recording a retest, match its requirement, destination/context or journey, candidate and target to the finding. A different viewport, endpoint capture or unrelated passing case cannot silently close that task. Keep scoped edits and unobserved participant/native lanes explicit.
