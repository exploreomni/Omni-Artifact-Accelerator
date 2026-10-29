# Qlik behavior handoff

Attach each obligation to its source app/object/placement, original definition
hash, observed state and selected target surface. Use explicit `preserve`,
`rebuild`, `redesign`, `manual_review`, `unsupported` or selected exclusion.
Missing evidence remains a gap; a plausible replacement does not close it.

| Source obligation | Target decision and proof owner |
|---|---|
| Current selections, exclusions and locked values | BI/app engineer proposes filtering behavior; QA observes narrowing, reset, empty-result and return paths |
| Bookmark/default bookmark and alternate states | Designer explains preserved/adapted comparison workflow; analyst verifies each measure population |
| Set analysis, Aggr/TOTAL, variables and inter-record calculations | Analyst records independent cases; BI/DMA resolves grain and formula mapping; QA verifies totals and changed states |
| Master items and repeated placements | Preserve one definition identity with separate placement/layout/state obligations; designer reviews each placement |
| Drill groups, containers, buttons and conditional visibility | App/dashboard designer resolves navigation and unsupported actions; app engineer implements only selected actions |
| Section Access, omitted columns and private sheets | Security/QA verify actual allowed/denied personas; frontend filtering never substitutes for access enforcement |
| Associations and load-script dependencies | DMA receives scoped backend requirements with original code inert and source identities intact |
| Theme, labels, media and extensions | Branding/design retain visual intent and approved assets; unknown extension code remains unexecuted |
| Source reload and result freshness | Product owner records independent target refresh/cache/expiry choice; QA checks stale/reconnect behavior |
| Export and responsive behavior | Preserve requested content/filter scope and accessible alternatives; verify separately for App/dashboard |

The handoff records original expression text, field/master dependencies,
aggregation grain, null/zero/totals rules, source formatting, state lineage,
security dependencies and a concrete expected outcome for each selected case.
No generic compiler, copied page template or automatic model redesign is assumed.

Selection cases should include an intentionally selection-independent measure,
an alternate-state comparison when present, a bookmark restore, a master-item
reuse and a restricted persona. Generate only cases relevant to the real source;
neutral synthetic coverage does not imply these exist in every engagement.

Numerical, interaction, visual, operational, access and customer acceptance lanes
remain independent. A successful import or native publish cannot close them.
