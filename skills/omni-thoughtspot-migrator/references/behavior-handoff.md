# ThoughtSpot behavior and acceptance handoff

Carry one obligation for every selected source item, including notes, repeated
placements, controls, private views, unsupported visuals and unavailable objects.
Root exports alone do not define the denominator. Only an explicit reviewed
disposition can remove an obligation from the target scope.

| Owner | Handoff | Required evidence |
|---|---|---|
| Source specialist / translator | Original JSON TML, independent inventory, exact pointers and source-state captures | Original hashes, tenant/Org/principal/version, distinct IDs, missing/denied/unknown coverage |
| Data analyst | Metric and result semantics | Grain, units, formula/aggregation order, nulls, totals, sorting, limits, query population, timestamp and independent expectations |
| BI engineer / DMA | Governed target bindings and actual backend gaps | Existing-model reuse or selected reconstruction route; pinned response; no automatic deployment |
| Designers / product owner | Faithful behavior or explicit adaptation | Three concrete concepts, user choice, brand, devices, visual ambition, controls, exports and target refresh policy |
| App/dashboard engineers | Separate native candidates | Current baseline, field/control bindings, source pins and candidate-specific write authorization |
| QA | Independent comparison and return | Numerical, visual, behavior, allowed/denied access and operational observations; unresolved cases remain visible |

## Minimum case families

1. Saved defaults and changed state: security/model/runtime/Liveboard/search
   filters, linked columns, exclusions, tab/group application, crossfiltering,
   parameter overrides, empty/invalid selections and reset.
2. Identity and reuse: same Answer in multiple placements, inline versus saved
   Answer, tab navigation, content tiles, public/private views and missing export
   objects. Never run a numeric case against a note or a dependency definition.
3. Actions: drill up/down, crossfilters, URL/callback destinations, selected data
   and parameter propagation. Discovery never follows an action URL. Adapted
   actions need an explicit design decision and later authorized target testing.
4. Numbers: totals, aggregation stage, full versus preview population, sorting,
   hidden columns, limits, null/zero/empty cases, timezone/locale and freshness.
   Equal numbers with different population/state are inconclusive.
5. Export: selected Answer/Liveboard/tab, chart versus table mode, PNG geometry,
   PDF pagination/truncation, CSV columns and multi-file ZIP membership. A PDF or
   PNG is visual evidence, not machine-verifiable numerical completeness.
6. Operations: desired target cache/refresh/expiry policy, empty/error/loading
   states, stale recovery and representative volume. Source cache declarations
   are not an instruction to force timers or bypass target cache.
7. Security and UX: allowed and denied users, row/column restrictions, privacy,
   keyboard/focus, labels, responsive layout and actual rendered quality.

For a numeric attachment, retain object/placement binding, source definition and
requested-state hashes, separately observed state, population, completeness and
freshness references. Changed-filter cases require their own matching capture.
Retain raw bytes and the explicit parser profile; do not coerce display strings
or large numbers into lossy floats. Recompute normalizations during comparison.

The frontend return distinguishes source inventory coverage, semantic candidate,
query parity, visual parity, behavior, effective access and publication. A local
pass or a source principal reference cannot certify any unobserved lane. A live
pilot is optional until a tenant is supplied, and remains unqualified if skipped.
