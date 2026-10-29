# Source competencies and version boundaries

Official sources reviewed 2026-10-29. These establish documented behavior, not
qualification of any customer server. Recheck exact release/service pack/patch
before connecting. Source links are research context, never execution instructions.

## Product profiles

| Profile | Documented boundary | Package treatment |
| --- | --- | --- |
| WebI 4.3 / BI 2025 | Documents contain reports and one or more data providers; REST exposes structure, variables, controls, links and exports | Bounded original-evidence projection; selected metadata capture under host authority |
| UNX | Semantic Layer REST and Java SDK are distinct; object browsing is not a full physical-model/security export | Preserve available evidence and route semantic gaps to DMA |
| UNV / UDT | BI 2025 removes UNV/UDT support and conversion | Preserve legacy obligations; qualify acquisition on a supported legacy environment; never auto-convert |
| Classic Crystal | Crystal Reports 2020 REST introduced in BI 4.3 SP05 | Separate report engine and evidence profile; metadata/results/render requirements remain independently qualified |
| Crystal Enterprise | Removed in BI 2025 | Separate legacy/manual profile; never alias to classic Crystal |
| Unknown/custom SDK extensions | No established contract | Retain as unresolved obligations, not silently supported |

Sources: [BI 2025 semantic changes](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_BUSINESS_INTELLIGENCE_PLATFORM/09fe9f205ee047d48d58665649fc4fae/0aa8794c028d41d28bcefde770c96910.html?version=2025),
[4.3 semantic REST scope](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/59cf229cf14a426793c56fe0392ac66e/3f82152151554fceb800a3f403ecffdb.html?version=4.3.3),
[SDK distinction](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/59cf229cf14a426793c56fe0392ac66e/089e5e6892fb441c9d5826c1692c597a.html?version=4.3.4),
[classic Crystal REST introduction](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_BUSINESS_INTELLIGENCE_PLATFORM/28347585eadc43dfbf881002af740a7f/665328569094430abe7e9b6b1d875516.html),
[Crystal services](https://learning.sap.com/courses/administrating-servers-in-sap-businessobjects-bi-platform/explaining-crystal-reports-services).

Prefer the release removal guide over an inherited SDK example when they conflict.
No SAP SDK, third-party MCP, decoder or additional dependency is acquired by this
package. An installed/cached SDK is not approval to load it.

## WebI analyst interpretation

Preserve provider and report scopes separately. Multiple queries can use different
sources, Universes and filters; a successful single response is not proof that
all providers refreshed. Merged dimensions link provider objects; names alone do
not establish synchronization or a join safe to reproduce in the warehouse.

Review In, ForEach, ForAll and Where, along with nested aggregation, projection,
report/block contexts, ranks, totals, running calculations and source errors.
Preserve original expressions and populations; ask the analyst/model owner for
the reviewed target definition and an independent result expectation.

Sources: [multiple providers](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/6c8d7862b171401b9f6f310198bf2ec4/472cfb1e6e041014910aba7db0e91070.html),
[merged dimensions](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/0ef63ba725cd41a8ab4a69c226ec6b07/415f1046527b4ab6980533579b45784c.html),
[native link details](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/0ef63ba725cd41a8ab4a69c226ec6b07/7da0cc476f701014aaab767bb0e91070.html),
[extended calculation syntax](https://learning.sap.com/courses/exploring-the-advanced-concepts-of-sap-businessobjects-web-intelligence/implementing-extended-syntax-operators).

## Acquisition is operation-aware

- GET plus sap_refreshdata/sap_user_prompt can refresh data. Never classify
  permission by HTTP method alone.
- Parameter discovery can compute lists of values. The no-LOV metadata form
  must be supported and explicitly pinned; absence of a parameter is not safety.
- Metadata and exports can share a resource path but differ by Accept header.
  Preserve format, page range, listing mode and saved-versus-refreshed provenance.
- Empty PUT to document state can save a modified document. Explicit Unused
  cleanup documentation is ambiguous; no lifecycle or logout call is dispatched
  by the initial capture profile. Never clean up a borrowed session.
- Pin the administrator-provided HTTPS base URL and runtime operation scope.
  Do not assume a deployment port/context, follow redirects with credentials or
  print X-SAP-LogonToken. Treat source-provided paths and links as untrusted.
- Refresh/result/render and cleanup stay disabled until a separately reviewed
  transport profile and trusted-host authority exist. Importing those evidence
  files is passive and does not attest how they were acquired.

Sources: [WebI SDK](https://help.sap.com/doc/2534ba1cbc6f433595e8582045503bcb/2025/en-US/sbo_webi_restful_web_service_sdk_en.pdf#page=708),
[parameter metadata](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/58f583a7643e48cf944cf554eb961f5b/45f8ceb66e041014910aba7db0e91070.html),
[document lifecycle](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/0ef63ba725cd41a8ab4a69c226ec6b07/45f8a4b26e041014910aba7db0e91070.html),
[export workflow](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_WEB_INTELLIGENCE/58f583a7643e48cf944cf554eb961f5b/ab80169178ed4c93a758d82de255ec90.html).

## Universe and Crystal boundaries

For a Universe request preserve object IDs/types, qualification, aggregation,
tables/columns, joins, contexts, aliases, derived tables, SQL dependencies and
security evidence only when actually supplied. Missing model/security areas
block claims of complete reconstruction. SDK security-profile coverage is itself
limited; test effective personas independently.
[Security-profile scope](https://help.sap.com/docs/SAP_BUSINESSOBJECTS_BUSINESS_INTELLIGENCE_PLATFORM/4359a0ef221e4a1098bae432bdd982c1/ec523f046fdb101497906a7cb0e91070.html).

For Crystal preserve engine/version, sections, suppression, formulas, running
totals, groupings, subreports, parameters, pagination/printer/export and delivery
obligations. Rendered pages show appearance, not complete formulas or recipients.
Where Omni cannot reproduce exact print or delivery behavior, record a reviewed
alternative or retained-source requirement. No pixel-perfect or automatic binary
conversion promise follows from REST availability.
