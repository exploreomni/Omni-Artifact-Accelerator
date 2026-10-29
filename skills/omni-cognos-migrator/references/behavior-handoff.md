# Cognos behavior handoff

Every requirement retains its report/content identity, original XML hash, locator,
source name and evidence reference. A positional locator may change when the XML
changes; never treat it as a stable native ID or collapse repeated occurrences.

| Concern | Preserve | Target and QA decision |
|---|---|---|
| Query and model | Query names/bindings, data-item expressions, aggregate rules, model/package paths, joins and dimensional dependencies when supplied | Reuse reviewed Omni fields or request scoped backend work. No automatic SQL, MDX, macro or Framework Manager compilation. |
| Filter and parameter | Detail versus summary filters, slicers, use/display values, required/optional, default/empty/omitted/all, cascading and auto-submit behavior | Define grain and actual state; test reset/change/empty cases. Static prompt definitions are not observed answers. |
| Layout and repetition | Report/prompt pages, page sets, nested containers, repeated placements, headers/footers, conditional content, sorting and formatting | Distinguish analytical equivalence from interactive and print fidelity. Keep unsupported render behavior visible. |
| Navigation | Drill target identity/action and parameter/context mapping, links, master-detail relationships | Test target permission and state transfer. Never execute URLs or custom code merely because they occur in XML. |
| Distribution | Burst key/grouping, recipient-query and delivery references, saved views, schedules and export expectations when supplied | Retain explicit migration obligations. Delivery is not a dashboard filter; no automatic recipient, schedule or subscription creation. |
| Security and runtime | Principal, package/object/data restrictions, actual population, watermark, locale/timezone and source cache context | Separate intended access from effective persona tests. The user's target cache/refresh choice is an independent D-stage decision. |

Send missing grain, relationship, calculation and security requirements to the
existing DMA cowork request/response flow with source pins and independent
expectations. There is no Cognos `source_adapter_result` producer here; do not
invent one or import a third-party extractor as an implicit dependency.

The current report snapshot has no qualified result binding. Preserve supplied
results and renders in the private engagement, but keep automatic numerical
comparison inconclusive. A future result adapter must bind exact query/placement,
observed prompts/filters, principal, complete population and freshness before it
can support parity. Unknown XML constructs remain review obligations, not silent
successes or permission to lower the selected product's quality bar.
