# Strategy source competencies

Official documentation reviewed 2026-10-28. Vendor capability, implemented
parser support and qualification in a customer's tenant are separate facts.

| Competency | Migration decision | Official reference |
|---|---|---|
| Stateful authentication | Keep token and all session/load-balancer cookies at the authorized host; pin origin/context/project/principal. | [Authentication](https://microstrategy.github.io/rest-api-docs/getting-started/authentication/) |
| Dashboard structure and selectors | Record chapters/pages, selector types, dataset links and visualization state. Pin Library and Intelligence Server independently. | [Selectors](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/manage-selectors/) |
| Prompt semantics | Identify occurrences by unique key, not repeated prompt ID/name. Preserve required/default/explicit/empty answers and actual execution state. | [Answer prompts](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/use-prompts-objects/answer-prompts/) |
| Filtering | Separate extraction/report, chapter, pre-aggregation view/template and post-aggregation metric filtering. | [Applied visualization filters](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/filter-data/retrieve-filters-applied-to-a-visualization/) |
| Metrics | Capture expression, dimensionality, conditions, subtotals, formatting and object versions; review semantics before target translation. | [Metric definition](https://microstrategy.github.io/rest-api-docs/common-workflows/modeling/manage-metric-objects/retrieve-a-metrics-definition/) |
| Reports | Preserve data template and view template independently. Modeling instances are not analytics execution instances. | [Report definition](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/manage-reports/manage-report-objects/retrieve-a-reports-definition/) |
| Numerical evidence | Preserve definition IDs/forms, metric index, raw/formatted values, paging and partial flags; reject unsupported shape/profile. | [JSON Data workflow](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/retrieve-data-from-the-intelligence-server/workflow-retrieve-data-from-the-intelligence-server/), [limitations](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/retrieve-data-from-the-intelligence-server/supported-features-and-considerations/) |
| Rendering | PDF is separate executed-instance evidence; do not infer an image API. | [PDF export](https://microstrategy.github.io/rest-api-docs/common-workflows/analytics/export-to-pdf/) |
| Classic security | Definitions and top/bottom-level rules are requirements, not proof of effective access. | [Security-filter definition](https://microstrategy.github.io/rest-api-docs/common-workflows/modeling/manage-security-filter-objects/retrieve-a-security-filter-definition/) |
| Mosaic security | Model membership/assignment differs from classic security-filter lookup. | [Mosaic members](https://microstrategy.github.io/rest-api-docs/common-workflows/mosaic/manage-data-model-security-filters/retrieve-a-security-filters-member-in-data-model/) |
| MCP | Discover actual schemas at the Agent or Mosaic endpoint. Keep metadata and query grants separate; retain raw call evidence. | [MCP overview](https://www2.strategy.com/producthelp/Current/NextGenAI/en-us/Content/agent_mcpserverintegration.htm) |
| Modeling writes | Project-scoped reads do not grant changeset creation/commit; changeset headers alter project resolution. | [Changesets](https://microstrategy.github.io/rest-api-docs/common-workflows/modeling/changesets/) |

## Version and fidelity traps

- Parameter selectors require both Library and Intelligence Server 2021 Update
  12 or later. Older/mixed versions can omit visualization-as-filter or dataset
  detail. Missing fields are unresolved coverage, not proof of no behavior.
- The documented JSON Data route has limitations for prompts, subtotals,
  consolidations, compound attributes, hierarchies and page-by. Other routes can
  have different capabilities; qualify the exact response instead of expanding
  one parser's promise. `limit=-1` still needs full pagination/partial checks.
- PDFs can arrive as bytes or base64 JSON. Keep bounded originals; no automatic
  PDF rendering, image conversion or third-party decoder. Supplied screenshots
  remain explicit observations, not a substitute for the source denominator.
- September 2026 separates Agent and Mosaic MCP privileges. March 2026 Mosaic
  availability replaced the February 2026 preview. Actual access still depends
  on deployment, certification and user privileges. Retain those statuses; no
  connector setup or server configuration is implied by the skill.
- [Datamart execution](https://microstrategy.github.io/rest-api-docs/common-workflows/modeling/manage-datamart-objects/execute-a-datamart/)
  can write warehouse data; it is explicitly excluded from ordinary report capture.
- Source SQL/formulas/extensions are untrusted evidence. Never execute them
  while interpreting or infer that every saved report is read-only. Datamart,
  transaction or other write-capable source types require exclusion or a
  separately authorized and qualified workflow.
- There is no universal Strategy-to-Omni expression compiler or automatic
  pixel-perfect document converter in this package. Preserve unresolved
  semantics and fidelity obligations for deliberate review.
