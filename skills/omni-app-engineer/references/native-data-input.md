# Native App data input and delivery evidence

Read when wiring or repairing an App's query input, adapting exported results, or preparing a build for native delivery. Use the existing `contracts/queries.json` items and [runtime contract](native-app-contract.md); this guide adds no Omni SDK, new mandatory project schema, credentials, or write authority.

## Qualify the boundary that will execute

A successful CLI/API query, a saved workbook query and an App callback are different evidence surfaces. They may carry the same values with different field keys, envelopes, types or status conventions. Display labels are not semantic field IDs. Inspect the current official contract and the actual native starter/bridge for the chosen target; retain the exact evidence and its limits. Do not infer a callback schema from a formatted export, another tenant's example, or a test double.

The BI engineer and App engineer should retain this compact information in the existing query item or a linked input-contract artifact:

| Boundary | Retain |
| --- | --- |
| Query identity | Current document/draft, effective query model/Topic, query key/tab name, exact fields, filters, sorts, limits and revision/hash. Bind by inspected identity, not a guessed title. |
| Envelope | Actual result location, status/error shape, subscription/run/reset behavior and available request/state correlation. Mark each supported behavior as documented, observed, or unresolved. Do not invent status strings. |
| Columns | Exact **selected query field** → transport key → application key, scalar representation, precision/units and nullability. Metadata can include filter-only fields; do not require those as result columns. Distinguish raw from formatted values. |
| Grain | Nonempty unique single/composite key, its identity types and safe-integer/string handling. Reject missing or duplicate grain before aggregation. Row position is not identity. |
| Dates | Date-only versus timestamp, serialization and timezone rules. Preserve calendar dates; do not use locale guessing or assume every timestamp is a date-only field. |
| Completeness | Pagination/caps, totals rows, missing columns, empty results, filtering and freshness. A terminal success status alone does not prove full population coverage. |
| Failure/recovery | Unknown/invalid shape, partial, denied, failed, stale and refreshing behavior for the affected UI, including which earlier results must be cleared or labeled stale. |
| Provenance | Evidence path/hash, method, query/state scope and candidate version. Say whether rows came from the native callback, query/export tooling, or a constructed simulation. |
| Source era and subset | Each query's period/season/version and population; allowed cross-query joins/comparisons; curated selection rule and participant/coordinate coverage for observed recordings. Never merge eras or claim full participation from a bounded sample. |

Link retained runtime qualification artifacts through the existing runtime `evidence_paths`; register/pin actual dependencies through the existing project/native workflow. A path written inside prose or arbitrary nested JSON is not automatically pinned. Keep protected data scoped and private; never retain tokens. If native observation is unavailable, keep that gap explicit while continuing a labeled local candidate.

## Normalize deliberately, then calculate

Use a small per-query adapter at the reviewed application boundary. Require the declared keys and types; preserve zero, null and stable identity distinctly. A renamed/missing key must produce an actionable input mismatch, not a guessed label, empty array or zero total. Permit alternate shapes only when independently qualified and explicitly selected; do not probe several unrelated key spellings until something works. Keep original values/evidence, and document any date, decimal or enum conversion. Never multiply an already extended amount by quantity or recalculate a governed distinct count to accommodate a transport change.

For example, these **original synthetic records** illustrate two different transports, not an Omni callback contract:

```json
{
  "export_row": {"Site": "s-17", "Eligible units": "240"},
  "qualified_runtime_row": {"service.site_id": "s-17", "service.eligible_units": 240},
  "application_row": {"site_id": "s-17", "eligible_units": 240}
}
```

An adapter for the qualified runtime row must not accept the export row merely because the values look familiar. A unit value of `0` remains zero; `null` remains unknown under the metric contract. A deliberately re-keyed export fixture is useful contract-shaped simulation, never a recorded native payload.

For a small reusable implementation, [experience utilities](native-capability-checks.md#optional-reusable-utilities) provide exact-key/type projection, optional qualified numeric-string normalization, composite-grain checks and generation-aware resource state. They do not discover field names, establish completeness, correlate an unqualified callback, or preserve arbitrary decimal precision. The qualified boundary must supply those decisions; preserve the immutable runtime fragments below.

### Executable handoff without a provider SDK

Reuse `experience_components.js` and `query_controller.js`; do not create another
application framework. `OAAQueryController.createQueryDelivery` consumes the
following bounded handoff. Retain its source/evidence with the existing query and
runtime records. This is an OAA interface, **not a vendor callback schema**:

```js
const delivery = OAAQueryController.createQueryDelivery({
  columns: [
    {key:"source.device_key", as:"device_id", type:"string", nullable:false},
    {key:"source.period", as:"period", type:"string", nullable:false},
    {key:"source.value", as:"value", type:"number", nullable:true,
     numericStrings:"decimal"} // Include only if this alternative was qualified.
  ],
  grain:["device_id", "period"], limit:1000,
  evidenceRef:"evidence/inspected-runtime.json",
  correlation:"serialized_unqualified",
  runSettlement:"after_terminal_delivery",
  run:runInspectedQuery,
  subscribe:subscribeInspectedQuery, // Returns a qualified synchronous cleanup.
  decode:decodeInspectedEnvelope,
  onState:renderDataState
});
```

`decode` maps only the inspected envelope into `{phase:"loading"}` or an explicit
`error`, `restricted` or `stale` phase, or `{phase:"complete", columns:[exactKeys],
rows:[rawRows], truncated:false, completeness:"complete"|"partial"|"unknown"}`.
It must not guess aliases/statuses, turn missing truncation evidence into `false`,
or equate terminal success with completeness. Query results at the saved limit or
declared truncated are rejected. `columns` contains only selected-field mappings;
every mapped field must appear in result metadata and every row. Extra metadata
is not automatically a required result field. Keep date/precision conversion in
its separately qualified adapter.

`mapRows(rows, columns, maxRows, {grain})` defaults to primitive types only.
Opt-in `numericStrings:"decimal"` accepts finite strict decimal/exponent strings
for `number`, with no whitespace, blanks, booleans, currency or locale separators.
For `integer`, only signed digit strings are accepted and the result must be a
safe integer; fractional/exponent identity strings are rejected to avoid rounding
an identity into another value. Nonzero strings that underflow to zero are
rejected; ordinary binary Number rounding still applies. Already numeric inputs
cannot recover precision lost upstream. Exact-decimal money/IDs outside that range
need an explicit string/precision policy, not this Number conversion. NULL stays NULL
only where nullable; a blank export value does not establish a native NULL rule.

`refresh()` subscribes, runs once, consumes both subscription results and the
awaited run-return fallback, then cleans up. Identical terminal payloads are
deduplicated; contradictory terminal results fail closed. The busy state remains
until the actual run settles, including after a failed or invalidated result.
An overlapping call returns `{started:false,reason:"busy"}` rather than starting
another request. `invalidate("stale"|"restricted"|"error")` clears affected rows
without pretending to cancel the native query. `dispose()` clears rows, releases
the subscription and ignores late delivery; bind it to the actual view/page
lifecycle. Also clear affected selected identifiers in the selection owner.
Independent query panels can use separate instances; combined claims require all
their qualified dependencies. This adapter does not provide a cross-query join.

## Bind every visible data consumer

New App engagements with `app_release_policy: "candidate-release-v1"` require
`contracts/native-data-consumers.json` before guarded native preparation. Historical
engagements without the marker remain explicitly unassessed; adopt the policy
deliberately through the existing engagement process. This contract supplements
the selected design, Topic/access checks and candidate reviews. It grants no
execution or publication permission.

Annotate each visible data-bearing element with its unique `id` and
`data-oaa-consumer="consumer-id"`. Include every KPI, chart, detail list, comparison
and data-derived narrative, including those on later views. The source checker
requires an exact match between declared markers and manifest rows. Reviewers
must still inspect the full candidate for unmarked claims, dynamically created
elements, hidden labels and the actual callback-to-display behavior; HTML markers
and source fragments cannot prove rendered coverage or JavaScript execution.

The manifest has exactly `schema_version: 1`, `kind: "native_data_consumers"`,
`document_id`, `html_sha256`, `presentations_sha256`, `refresh_policy` and
`consumers`. Hash the exact UTF-8 candidate and the canonical complete
`{data, order}` query presentations, including later tabs. `refresh_policy` is the
existing selected, normalized [refresh decision](../../omni-product-owner/references/data-refresh-policy.md),
not a new default. A missing answer returns the existing freshness question;
never add polling, cache bypass or expiry to make this contract pass.

Every consumer has `id`, `element_id`, `mode`, `expectation` and
`expectation_basis`. The expectation is an exact engagement-relative
`{path, sha256}` original evidence pin under `inputs/` or `evidence/`; its basis is
`independent_query` or `independent_calculation`. Pinning supplied evidence does
not establish its independence or numerical correctness. Use the existing
[native-query probe](native-query-qualification.md) and analytical evidence
comparators for those checks, retaining their stated evidence lanes.

| Mode | Additional exact fields | Required visible truth |
| --- | --- | --- |
| `live` | `sources`: one or more `{query_key, tile_sha256, fields, script_fragment}` rows | Each exact saved Topic query and selected fields has its own candidate source binding. Full tile hashes retain filters and query configuration. A single first-query handler cannot stand in for later queries. |
| `snapshot` | `label`, `period`, `source_label`, `source` pin | The element contains its Snapshot label, source attribution and period. Original snapshot and independent expectation bytes must differ. This is never an automatic substitute for a denied or failed live query. |
| `scenario` | `label`, `base_consumer_ids`, `assumptions` pin, `script_fragment` | The element visibly says Scenario or Estimate. Its bases are declared live or snapshot consumers, and its assumptions remain distinct from independent expectations. |

Each `script_fragment` must occur in an inline executable script of the exact
candidate and include the quoted consumer ID and each corresponding query key
(or base consumer ID for a scenario). This preserves the reviewed source site;
it does not infer that a vendor callback fired. Query keys retain their existing
exact identity, including named keys. A manifest with source-only checks returns
`runtime_verified`, `numerical_verified`, `visual_coverage_verified` and
`access_verified` as false.

Freeze the manifest as a supporting artifact with the HTML and native spec, then
include it in candidate review. Native guards compare the current manifest with
the retained frozen bytes, re-read original evidence pins, and reject changed
HTML, queries, evidence or selected refresh meaning. A retained snapshot of the
manifest is valid when its bytes are identical; its copied path need not equal
the mutable contract path. The synthetic
[contract tests](../../../tests/test_native_data_consumers.py) contain a complete
two-query, snapshot and scenario example without a tenant or runtime claim.

## Coordinate callback updates and refresh completion

`OAAQueryController.createConsumerDelivery({queries, consumers, onConsumer,
onRefresh})` composes the existing delivery boundary. `queries` contains unique
`{queryKey, delivery}` entries; each `delivery` supplies the same inspected
`run`, `subscribe`, `decode`, columns/grain, limit and correlation contract as
`createQueryDelivery`, leaving `onState` to the coordinator. Declare every used
query, not only the first saved tab. Its callbacks drive these consumer rows:

```js
const delivery = OAAQueryController.createConsumerDelivery({
  queries: [
    {queryKey: "summary", delivery: qualifiedSummaryBridge},
    {queryKey: "detail", delivery: qualifiedDetailBridge}
  ],
  consumers: [
    {id: "summary-panel", mode: "live", queryKeys: ["summary"]},
    {id: "detail-panel", mode: "live", queryKeys: ["detail"]},
    {id: "comparison", mode: "live", queryKeys: ["summary", "detail"]}
  ],
  onConsumer: renderExactConsumerState,
  onRefresh: renderRefreshState
});
// Bind initial/manual actions through the already selected refresh policy.
// Never use a timer to announce success.
await delivery.refresh();
```

The bridge and renderers above are reviewed application functions, not vendor
SDK names. Live renderers receive actual normalized `rowsByQuery` only when all
that consumer's dependencies have complete results from the current refresh.
They receive empty `rowsByQuery` on loading, partial, denied, error and invalidated
states. Replace or clear the visible element on every callback; never use
`rows || embeddedExampleRows`. Empty complete results remain an explicit empty
state. Source tests exercise the second query arriving first and stale callbacks
from an earlier subscription; native correlation still requires separate proof.

Scenario rows use `baseConsumerIds`, a visible `label`, `assumptionsRef` and a
synchronous `derive(bases)` function. They emit a separate scenario `value` only
when all bases are available. Snapshot rows use `label`, `period`, `sourceRef` and
an explicitly reviewed `value`; their phase is `snapshot`, never live. Any query
restriction, error or stale invalidation withholds retained snapshots and their
dependent estimates. An error-only hold clears only after an explicit refresh
finishes successfully for every required query and consumer. Restricted or stale
holds remain sticky through later errors and successful refreshes; reconstruct
the instance only after separately requalifying those snapshot sources and access.
Renderer exceptions make success false and leave the visual lane
unverified, because a failed renderer cannot prove that old pixels cleared.

`refresh()` runs once per relevant query, rejects overlap with a busy outcome,
and reports `success:true` only after every actual run has settled with complete
results and every consumer is usable. A snapshot-only view has no live refresh
and returns `no_live_queries`. Combined consumers never mix an earlier result
with the next generation. `invalidate()` clears values without claiming native
cancellation; `dispose()` clears consumers and releases subscriptions. The
coordinator adds no timers, polling, cache settings or source-time claims.

The exact candidate still needs authorized native callback observations,
independent numerical expectations, effective access tests and rendered review.
Query export, source simulation, readback and a refresh-state string cannot close
those separate lanes.

This route requires `runSettlement:"after_terminal_delivery"`: the inspected
`run` promise must settle after terminal subscription delivery or supply the
terminal result itself. A provider that acknowledges a run before later callbacks
does **not** satisfy this contract. Qualify a separate bounded completion bridge
for that provider; never relabel an acknowledgment as completion. An absent
terminal result at settlement becomes an error and a later callback is ignored.
The provider must also qualify synchronous subscription release. Failed
registration, cleanup failure or asynchronous cleanup marks the instance
`usable:false` and blocks later refresh; recover the underlying subscription
before constructing a replacement. Do not invent a no-op
cleanup for an unqualified subscription. A promise-only bridge can retain the
existing `createQueryController` route instead.

`correlation` is either `provider_correlated` (requires actual provider evidence)
or `serialized_unqualified`. Serialization and closed local callbacks do **not**
identify a delayed broadcast delivered to a newly registered listener. Retain
that native qualification gap; never turn the adapter's local ticket or a copied
evidence path into provider correlation or production acceptance.

Run `python3 -I -S -B -m unittest discover -s tests -p test_native_input_handoff.py -v`
for focused original-source checks of this handoff and related continuity. Those
checks use synthetic inputs, controlled promises and abstract focus targets;
they contain no browser, DOM emulation, native SDK or vendor execution.

Preserve the chosen result population. Only combine query results whose required state/freshness/completeness conditions agree; one missing required query must not produce a misleading combined KPI. Independent panels may remain usable when their contracts permit it. If the bridge cannot correlate refresh/filter generations, document and constrain overlapping work rather than inventing a request ID. Clear or visibly mark stale results according to the chosen state contract; late results must not overwrite a newer applied state.

For the bounded native helper, retained runtime/control fragments remain immutable. Place an adapter only where the reviewed construction/edit contract permits it. If the repair changes a protected fragment, stop that candidate and use a separately reviewed, supported authoring/baseline route; do not delete fragment requirements, broaden owned regions, or weaken the helper to force the patch through.

## Rehearse the assembled candidate, proportionately

For a new boundary or a repair, use the actual generated HTML/scripts and query bindings. A source module test alone misses missing build substitutions, script ordering and shared global-scope failures. Reuse the smallest existing harness: execute scripts in their actual order and scope, with browser-like `window === globalThis` for classic scripts, and a deliberately labeled bridge/DOM double when native execution is unavailable. Do not flatten module scripts into classic scripts or pretend a stub implements the browser.

Start with one successful required-query callback sequence reconciled against independently frozen expectations and one missing-field/error case that withholds the affected claims. Add date/null/refresh cases only where changed behavior or an unresolved concern warrants them. Test raw runtime keys and types, not only the adapter's expected output. Numerical consistency, source startup, rendered review, native callback behavior, effective access and publication remain separate results; a local pass closes only its stated check.

Keep three entrypoints explicit in the handoff: editable template/modules, exact assembled candidate and native launch target. Record the build command, candidate hash and any required source files. A template with unresolved substitutions is not the runnable App. A local preview uses a visibly synthetic/test adapter; outside Omni it must not claim a live data connection or embed production credentials. Do not replace the native launch link with the source template or a generic local HTML file.

After an authorized write, compare exact candidate/readback and unchanged query/settings identity. Observe the affected native path when allowed, retaining target/state/version and actual results. Readback or a publish receipt is not proof that callbacks fired or users saw the intended values. Under no-browser constraints, report native interaction as unobserved and return the actual launch target with the bounded evidence; do not manufacture a screenshot or test claim. Follow existing publication authorization without adding a redundant approval loop.

## Official-source note

Inspected **2026-10-22**: [Omni Apps](https://docs.omni.co/visualize-present/apps) documents workbook-query-fed Apps, sandboxing and a draft editor with a live preview. [Document CLI commands](https://docs.omni.co/developers/cli/commands/documents) labels App content commands **alpha**, describes draft-scoped writes and distinguishes published reads. These reviewed pages do **not** specify the exact browser callback envelope, row keys, status vocabulary or SDK methods used by a particular starter. Qualify those separately; this guide's synthetic rows and OAA controller are not vendor API documentation. Recheck current tools before execution.

## Executable offline qualification

Before substantial composition or a data-boundary repair, use the [offline native-query probe](native-query-qualification.md) on retained source/query captures and independently pinned population/aggregate evidence. It checks requested versus observed source identity, exact named query and scope, usable field metadata, strict row/NULL types, unique grain and cap/completeness. It cannot authenticate captures, infer the original brief, execute native callbacks or certify rendering. A raw SQL/export success with empty metadata is a qualification gap, not a valid native adapter. Keep modeled fields and the explicit requested database/schema together; never repair this by silently narrowing the cohort or switching source catalogs.

The same guide records bounded in-development payload observations and the smallest isolated workbook query-view proposal path. Requalify current tools before writes; no shared connection or model modification is implied. Unknown request correlation requires serialized refresh/query generations and an explicit terminal/recovery path, not invented callback correlation.
