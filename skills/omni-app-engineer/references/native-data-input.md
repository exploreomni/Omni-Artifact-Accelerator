# Native App data input and delivery evidence

Read when wiring or repairing an App's query input, adapting exported results, or preparing a build for native delivery. Use the existing `contracts/queries.json` items and [runtime contract](native-app-contract.md); this guide adds no Omni SDK, new mandatory project schema, credentials, or write authority.

## Qualify the boundary that will execute

A successful CLI/API query, a saved workbook query and an App callback are different evidence surfaces. They may carry the same values with different field keys, envelopes, types or status conventions. Display labels are not semantic field IDs. Inspect the current official contract and the actual native starter/bridge for the chosen target; retain the exact evidence and its limits. Do not infer a callback schema from a formatted export, another tenant's example, or a test double.

The BI engineer and App engineer should retain this compact information in the existing query item or a linked input-contract artifact:

| Boundary | Retain |
| --- | --- |
| Query identity | Current document/draft, effective query model/Topic, query key/tab name, exact fields, filters, sorts, limits and revision/hash. Bind by inspected identity, not a guessed title. |
| Envelope | Actual result location, status/error shape, subscription/run/reset behavior and available request/state correlation. Mark each supported behavior as documented, observed, or unresolved. Do not invent status strings. |
| Columns | Exact transport key → semantic field → application key, value type, precision/units, nullability and identity role. Distinguish raw from formatted values. |
| Dates | Date-only versus timestamp, serialization and timezone rules. Preserve calendar dates; do not use locale guessing or assume every timestamp is a date-only field. |
| Completeness | Pagination/caps, totals rows, missing columns, empty results, filtering and freshness. A terminal success status alone does not prove full population coverage. |
| Failure/recovery | Unknown/invalid shape, partial, denied, failed, stale and refreshing behavior for the affected UI, including which earlier results must be cleared or labeled stale. |
| Provenance | Evidence path/hash, method, query/state scope and candidate version. Say whether rows came from the native callback, query/export tooling, or a constructed simulation. |

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

For a small reusable implementation, [experience utilities](native-capability-checks.md#optional-reusable-utilities) provide exact-key/type projection and generation-aware resource state. They do not parse provider envelopes, discover field names, establish completeness, correlate an unqualified callback, or coerce precise decimal/date values. The qualified boundary must supply those decisions; preserve the immutable runtime fragments below.

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
