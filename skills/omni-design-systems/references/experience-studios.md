# Original practice studios

Use these exercises to practice the [curriculum](experience-curriculum.md), then transfer the reasoning to a different domain. They are invented teaching problems, not customer requirements, accepted metrics or native product demonstrations. Keep submissions and reviewer observations in a private engagement workspace. Use the [critique guide](experience-review.md) to assess a particular artifact and revision.

## Studio A — Same data, two different experiences

**Brief.** A regional lead wants to understand whether portfolio growth is broad-based. An analyst wants to compare a location's trajectory against its peers. Build a native dashboard concept for the first task and an App concept for the second. The selected surface cannot be silently changed to obtain a preferred interaction.

**Fixture.** The [machine-readable fixture](../assets/experience-studio-fixtures.json) contains these invented monthly sales in **thousands of USD**:

| Location | January | February | March | April |
| --- | ---: | ---: | ---: | ---: |
| Alder | 100 | 110 | 145 | 180 |
| Bay | 80 | 90 | 100 | 110 |
| Cedar | 160 | 150 | 135 | 120 |

No visits, costs, targets, profit, customer identities or causal explanation are supplied. January total is 340; April total is 410; the change is +70, or approximately +20.6%. Alder changes +80, Bay +30 and Cedar −40. Growth is not shared by every location. A label such as “profit improved” or “the campaign worked” would be unsupported.

**Weak starting artifact.** Four equal metric cards, a pie chart of April share, an undifferentiated monthly line chart and a large “View details” button. Every number can be correct while the composition fails to explain who contributed to the change.

**Diagnosis.** Equal visual weight hides the question. The share chart answers a different question. A generic detail button promises no specific information. A palette change cannot repair the information structure.

**Dashboard direction: change and contribution.** Give a supported sentence and an aligned change plot the main area: “Portfolio sales rose; Cedar declined.” Label both endpoints and signed changes. Show the common-scale monthly comparison as supporting evidence. Put exact values and fixed scope within reach. Contrast this with a comparison-atlas alternative before selecting; retain the reason for preferring one. Verify native encoding support; a supported grouped-bar/delta-table composition is an acceptable translation when an exact form is unavailable.

**App direction: trajectory investigation.** Let the analyst select a location and a comparison period. Keep peer context visible, highlight the selected identity and show the values contributing to the comparison. A useful signature interaction is period-to-period comparison with identity-preserving movement and an exact-value table. A user-controlled narrative step can explain the portfolio result, its divergent contributors and the remaining unknowns. It must remain useful with motion off.

**Art direction.** Try an editorial composition with a large signed change and sparse annotations versus a comparative atlas with strict common scales and repeated chart grammar. Resolve title/body/axis/annotation roles, number formatting, line weight and spacing. These alternatives should still differ in grayscale. Use a restrained, original practice theme; do not borrow a real company's identity to substitute for design judgment.

**Revision prompt.** A reviewer says the selected line looks good but the remaining lines are impossible to distinguish and “growth” lacks a comparison period. Preserve the focal selection, add direct identity labels/non-color cues, restore useful peer contrast and state January→April beside the change. Recheck long labels and narrow layout; do not add a legend when direct labeling solves the problem more clearly.

**Acceptance evidence.** Reconcile totals and signed changes; verify common scale; show that a selected entity remains identifiable; demonstrate current scope, keyboard period control, reset and static/reduced equivalence when runnable. No motion frames are treated as new observations. Separate rendered evidence from local code checks and native verification.

The [interactive teaching specimen](../assets/experience-studio.html) illustrates a possible original interpretation using synthetic data. It is a local learning artifact, not an Omni dashboard import or a native-runtime pass. Its inclusion does not mean its rendering has been reviewed in the current host.

## Studio B — The denominator changes the priority

**Brief.** A fulfillment lead asks which region deserves investigation for returns. Data: North 30 returns / 1,000 orders; South 12 / 200; West 9 / 300. These are the only supplied facts. Rates are 3%, 6% and 3%; the combined rate is 51/1,500 =3.4%, not the unweighted mean of the regional rates.

**Weak start.** A dramatic red map and a ranked count chart declare North the worst performer. No geography, approved target or loss severity exists in the fixture.

**Two credible directions.** A paired count/rate comparison makes operational volume and incidence visible together. A rate-focused dot plot with counts/denominators supports an incidence question. Either can be right; the brief must establish whether workload, rate or cost is the decision. A geographic design would need a real spatial question and verified boundaries.

**Resolved revision.** Keep rate and count labels explicit; show the denominator near a selected region, equal-rate ties and the combined-rate method. Use a neutral accent until a target or adverse threshold is established. Do not claim a statistically significant difference from these aggregates alone.

**Transfer.** Apply the same reasoning to support tickets per active account, defects per production unit, or missed appointments per scheduled appointment. Preserve the denominator at the selected scope. Do not present invented training records as evidence about any real organization.

## Studio C — A narrative that survives exploration

**Brief.** Explain a portfolio change, then allow a reader to investigate. Use Studio A's data. Design three purposeful states: total change, contributors, and selected trajectory. Each state should contribute a new understanding.

**Weak start.** A scroll animation reveals the same total repeatedly, then announces “every location grew.” The claim is false, and the interaction adds no analytical evidence.

**Resolution.** The first state establishes +70 across the supplied period. The second shows +80 +30 −40. The third lets a reader inspect one entity and the unresolved reasons for its result. Keep exact values, period controls and a direct route to all evidence. If a location filter is applied, recompute or withhold the portfolio statement; do not leave a beautifully styled stale headline.

**Motion exercise.** Storyboard one coordinated emphasis transition with identity and completed values preserved. Explain why an easing/sequence choice helps orientation. Include interrupted navigation, rapid step changes and reduced motion. Avoid a sequence that forces users to sit through chapters to access evidence. Build a static native dashboard equivalent using sections and supported filters.

## Studio D — Evidence shape before visual novelty

**Brief.** A customer asks for a flowing customer journey, a retention cohort heatmap and a distribution of purchase sizes. Their export contains only monthly revenue totals.

**Weak start.** Generate a flow from category totals, repeat months into a heatmap and draw a smooth curve around the mean. These forms fabricate relationships and observations.

**Resolution.** Offer a well-composed monthly trajectory now. For each desired investigation, identify the minimum missing contract: journey edges/event ordering and population; cohort start/elapsed interval and eligible denominator; transaction-level values or valid histogram/quantile statistics. Route only those specific gaps through the existing backend exchange. Preserve independent expected cases and the selected surface. Continue authorized art direction while waiting for data.

**Design challenge.** Make the truthful, simpler interim view feel intentional through precise labels, typography, scale, annotation and useful comparison. Strong visual craft should not depend on inventing a richer dataset.

## Studio E — Identity without a palette swap

**Brief.** Two fictional brands use the same Studio A data. One wants calm precision for frequent operational work; the other wants an expressive exploration experience for occasional internal presentations. No real brand assets or font rights are supplied.

**Weak start.** Apply blue to one copy and orange to the other; retain the identical layout, typography and interaction.

**Resolution.** Develop different information rhythms and interaction tone while preserving metric meanings. A precision instrument may use compact aligned evidence, strong tabular numerals and immediate comparisons. An editorial exploration may use a dominant annotated chart, broader whitespace and reader-controlled steps. Specify what remains invariant: units, scales, values, access, focus and category identity. For actual customers, reuse their website/asset answers or ask for the missing website and authorized logo; a fictional wordmark is acceptable only in this explicitly fictional exercise.

**Review.** Remove color from the two specimens. The intended distinction should still be perceptible through proportion, type, grouping and interaction. That is a useful critique exercise, not a claim of measured brand recognition. Restore color and verify contrast, selected/focus states and actual logo treatment where relevant.

## Studio F — Preserve meaning while changing platform

**Brief.** Migrate a source experience with an animated ranking, hover-only commentary and a monthly detail view. The requested target is a native dashboard. Native support for the custom ranking animation is unverified.

**Weak start.** Replace it with an App, omit the commentary or declare screenshot parity sufficient.

**Resolution.** Inventory ranking rules, ties, population, temporal controls, annotation scope and exact detail behavior. Classify what is analytically essential versus a presentation choice. Qualify native support and propose a static ranked-change comparison plus accessible annotations if supported. Record every material difference; ask for a surface change only if the unmet behavior requires it. A local working choice does not accept migration parity or semantics.

**Transfer exercise.** Repeat with a source map without licensed boundary assets or an interactive scenario without its formulas. Preserve requirements and unresolved dependencies; use the translator, BI engineer, designer and backend role for their respective decisions.

## Capstone and reuse

For deliberate training, choose a brief in a different domain from the first studio. Deliver a dashboard and an App for distinct tasks using the same governed metric contract, or limit to one surface when that is the training objective. Include a design thesis, meaningful alternatives, resolved specimens, one useful interaction/motion proposal, a faithful static counterpart, implementation mapping and a critique/revision record. Use source code only when implementation is in scope.

Keep originality, correctness and evidence separate. A candidate may demonstrate better design reasoning while native rendering remains untested. Record the actual competency demonstrated, not “all agents trained.”
