# Cognos source competencies

Official sources checked **2026-10-28**. These explain evidence obligations;
they do not qualify a tenant, namespace version or connected route. The current
implementation remains supplied-report inspection. Recheck the selected deployment
before relying on version-sensitive behavior.

| Competency | Source fact and migration consequence |
|---|---|
| Report structure | A report specification separates queries from layouts, with model references and additional behavior. Preserve both; an attractive page alone does not recover its query semantics. [IBM report structure](https://www.ibm.com/docs/en/cognos-analytics/11.2.x?topic=specifications-basic-structure-report-specification) |
| Query semantics | Query definitions include data items and aggregates; detail filters, summary filters and slicers have distinct roles. Retain original expressions and filter stage rather than translating by function name. [IBM queries element](https://www.ibm.com/docs/en/cognos-analytics/11.2.x?topic=specification-queries-element) |
| Layout and prompts | Layouts can differ by condition/language and include report pages, prompt pages and page sets. Record repeated container occurrences and conditional visibility. Prompt use values differ from display labels; capture actual answers separately from their definitions. [IBM layouts](https://www.ibm.com/docs/en/cognos-analytics/11.2.x?topic=specification-layouts-element), [IBM prompted reports](https://www.ibm.com/docs/en/cognos-analytics/11.2.x?topic=prompts-running-report) |
| Navigation and distribution | Drill-through specifications identify a target and how source context maps to it. Burst groups and recipients can come from distinct queries, including a query absent from the visible layout. Inventory these dependencies without navigating links or sending outputs. [IBM drill-through](https://www.ibm.com/docs/en/cognos-analytics/12.0.x?topic=developer-drill-through-specification-examples), [IBM burst options](https://www.ibm.com/docs/en/cognos-analytics/12.1.x?topic=reports-set-burst-options) |
| Semantic security | Framework Manager separates data, object and package security. Data-module security filters have their own applicability; IBM specifically excludes typed-in SQL tables from those filters. Report XML is insufficient evidence of effective security. Obtain authorized model/assignment evidence and persona tests; do not change connection settings automatically. [IBM Framework Manager security](https://www.ibm.com/docs/en/cognos-analytics/11.2.x?topic=packages-security), [IBM data-module security](https://www.ibm.com/docs/en/cognos-analytics/12.0.x?topic=sources-securing-data) |
| Surface and runtime qualification | IBM's dashboard specification viewer is for troubleshooting; modifying or copying/importing those specifications as environment migration is unsupported. Treat supplied dashboard specifications as opaque evidence, not this report XML format. Exact REST contracts must be checked against the selected deployment's API documentation before a future connector is qualified. [IBM dashboard specification guidance](https://www.ibm.com/support/pages/how-importexport-dashboard-specification-ibm-Cognos-analytics), [IBM 12.1 API introduction](https://developer.ibm.com/apis/catalog/cognosanalytics--cognos-analytics-12-1-x/Introduction) |

## Evidence to request only when relevant

- Original report specification and its exported identity/version, plus an independent scope inventory. Preserve report views and saved prompt variants as distinct obligations where they are in scope.
- Authorized package/model or data-module definitions and dependency references for unresolved semantics. Preserve model paths, joins/cardinality, aggregation, dimensional hierarchies, calculations and security as review material; the report parser does not compile these models.
- Supplied rendered references, prompt/drill-through observations, complete query results and delivery requirements. Record principal, actual parameters, population, time/locale, watermark, output format and whether results are full, displayed or transformed. These are separate evidence, not parser-certified parity.
- Source cache and data-update cadence if available. Data-module cache behavior is contextual; record it without imposing a target expiry or bypass policy. [IBM data caching](https://www.ibm.com/docs/en/cognos-analytics/12.0.x?topic=sources-setting-up-data-caching)

Keep unknowns explicit. A deployment archive, report XML, dashboard specification,
rendered output and result dataset are different source artifacts. Do not unpack
an archive, load a decoder/SDK or execute embedded content outside an approved
implementation and the existing dependency policy.
