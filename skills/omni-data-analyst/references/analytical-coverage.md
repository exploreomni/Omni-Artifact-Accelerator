# Analytical depth that earns its place

Use for a substantial analytical experience, a request for richer insights, or a new detail/comparison path. For a small edit, reuse the accepted metric and evidence scope. Keep this map in existing metric/design/analysis records; it adds no project schema, dashboard count or mandatory analysis technique.

## Map questions before panels

For each consequential destination, retain `question → supported comparison → population/grain → units/timeframe → denominator or weighting → missingness/completeness → exact detail → claim limits → evidence and owner`. Use the stable destination IDs from the [experience brief](../../omni-design-systems/references/experience-brief.md). A supported measure alone does not establish that populations, periods or entities are comparable.

Select only the analytical depth useful to the task:

| User need | Resolve before presenting it |
| --- | --- |
| Change or trend | Period boundaries, available intervals, common units, missing observations and whether elapsed exposure differs. Do not label unequal periods normalized unless the accepted metric does that. |
| Contribution | Additive measure and complete partition; reconcile parts to the total. Two independent partitions of one total do not establish flows between their members. |
| Entity dossier or peer comparison | Stable entity identity, meaningful peer criteria and comparable coverage. Discovery search should not silently redefine the peer denominator; label any deliberately filtered peer scope. |
| Rate or average | Correct numerator/denominator or weights, exclusions and zero-denominator behavior. Do not average subgroup rates merely because their labels match. |
| Spatial or time-based scene | Measured coordinates/units, reference frame, observation grain and coverage. Name decorative dimensions; omit unsupported paths, interpolation, location precision and continuation. |
| Explanation or next action | Evidence supports description, association, hypothesis or cause at different strengths. State which applies; do not invent a cause, target, forecast or action owner to fill a screen. |

Treat missing rows, explicit NULL, observed zero and a separately qualified no-activity group distinctly. Keep presence/qualification when an additive zero is justified; it does not become a measured observation. Separate source periods and populations across sections rather than implying contemporaneous coverage. Result caps and unknown completeness constrain rankings and complete-total claims.

For a selectable entity directory, resolve `role → available measures → eligible denominator → useful comparison/action → unavailable treatment`. A field present in every row may still be meaningless for some roles. Do not fall through to a default role's performance panel. Rates require their actual denominator: a count of records cannot stand in for effort, exposure or attempts. Peer comparisons name the supplied cohort and each entity's coverage; they are not a wider-market rank. A highest-observed period needs a tie rule and does not establish an all-time record.

Give the designer a small set of supported next questions, not a quota of insight panels. A comparison should lead to its original observations while keeping the comparison population clear. If a selection filters its own comparison, specify whether alternatives remain visible and what reset restores. For media companions, confirm exact event identity and period before placing a historical result beside a current story; topical similarity is not a join key.

## Original synthetic worked example

A library operations analyst asks which branches explain a monthly circulation decline and selects a branch to inspect the evidence. The supplied monthly records are invented for this example:

| Branch | Previous loans | Current loans | Contribution to change |
| --- | ---: | ---: | ---: |
| Cedar | 1,200 | 1,100 | −100 |
| Harbor | 800 | 950 | +150 |
| Union | 1,000 | 850 | −150 |
| Total | 3,000 | 2,900 | −100 |

The supported finding is a 100-loan decline (3.33% of the previous total). Union contributes the largest decrease; Harbor offsets 150 of the 250 fewer loans across declining branches. A signed contribution comparison earns space; three additional copies of total loans do not. Branch detail may expose the two exact values and contribution. A six-month trajectory is unavailable, and neither staffing nor opening hours explains the change without more evidence. Do not synthesize either to make the detail richer. If a selected branch is merely absent from a partial result, its contribution is unknown rather than zero.

## Handoff and independent checks

Give design the usable evidence and missing dependencies; give storytelling `claim → source/result pin → scope → predicate → neutral fallback`. Specify how filtering, selection, refresh, empty/partial and failure states affect each claim. Neutral descriptions remain useful where a supported insight is unavailable. Engineering implements those conditions against the accepted metric contract; client-side convenience cannot redefine it.

Freeze a small independent expectation set before implementation: the primary result and decomposition, one consequential comparison or denominator case, and a changed-scope/missingness case when relevant. Derive expectations from original source or governed query evidence, not the candidate's calculation function. Reuse unchanged expectations during visual redesign. QA retains numerical, native execution, comprehension and craft as separate lanes; matching totals do not prove useful detail or truthful interpretation.

When a required question is unsupported, return the precise missing grain/field/population through the BI engineer and existing backend handoff. Continue the supported experience without silently substituting a different question or inventing data.
