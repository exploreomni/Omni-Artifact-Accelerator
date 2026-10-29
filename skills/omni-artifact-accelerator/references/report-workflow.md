# Native report foundation

Use the `report` surface for native **Reports Beta**, distinct from `dashboard`
and `app`. The existing `both` shorthand continues to mean dashboard plus App.
This package adds report design/build responsibilities and local contracts; it
does not install an engine, provide a universal compiler or expose report writes.

| Responsibility | Owner | Handoff |
| --- | --- | --- |
| Intent and acceptance | Existing product owner | Report interview, actual decisions and quality bar |
| Data and metric meaning | Existing analyst and BI engineer | Qualified queries, fields, parameters, totals and independent expectations |
| Page composition | [Report designer](../../omni-report-designer/SKILL.md) | Three concepts, selected page/section design and output rules |
| Native preparation | [Report builder](../../omni-report-builder/SKILL.md) | Version-qualified definition/binding handoff, preserved scope and gaps |
| Brand and craft | Existing branding/design systems | Approved assets, typography and format-specific adaptations |
| Independent verification | Existing QA, security and creative review responsibilities | Candidate-bound numbers, page/export observations, access and acceptance |

Use one orchestrator and the smallest useful team. Source migrators supply source
evidence; they do not own target design, publication or customer acceptance.

1. Initialize with `analyst_project.py init --output /private-engagement --name
   'Operations report' --mode net-new --surface report`. Add the normal run-start
   evidence and preserve the original request and package revision.
2. Complete A data/access, B queries/analysis and C traceable narrative. Reuse
   existing Omni semantics first; route model gaps through the existing DMA handoff.
3. At D use the [report interview](../../omni-product-owner/references/report-interview.md).
   Preserve outputs, physical page constraints, layout semantics, branding,
   parameter context and separate cache/refresh/distribution decisions.
4. At E retain exactly three concrete report options and the actual selection.
   Resolve the selected design with `report_contract`; use the
   [contract reference](../../omni-report-designer/references/report-contract.md).
   A static one-page report needs no invented interactive screens.
5. F authoring remains gated even for JSON/RDLX files. Reuse candidate freezing and
   four independent review responsibilities. The builder validates actual native
   interfaces before any authorized write; unknown endpoints remain unavailable.
6. Inspect the returned report/exports with [report QA](../../omni-qa-analyst/references/report-qa.md).
   Distinguish declared design, native execution, rendered fidelity, access,
   publication and distribution. Retain unsupported/missing behavior explicitly.

Existing dashboard/App native executors cannot publish a Report. A read-only
published report observation uses its actual content ID, instance and retained
capability evidence; it never grants API authority. A source-only handoff is a
useful deliverable when a qualified authoring interface is unavailable, but it
must not be presented as a deployed or pixel-perfect report.

## Source migration routes

Use [SSRS](../../omni-ssrs-migrator/SKILL.md),
[Power BI paginated](../../omni-powerbi-paginated-migrator/SKILL.md) or
[Crystal Reports](../../omni-crystal-reports-migrator/SKILL.md) for their separate
source responsibilities. Shared RDL inspection is passive; Crystal uses a
supplied explicit extraction, not a binary RPT decoder. Inventory independently,
retain original bytes and classify every unsupported expression, dependency,
parameter, subreport and rendering obligation. Source expressions never execute.

The [shared capture contract](../../omni-artifact-translator/references/report-source-capture.md)
pins original definitions, independent inventory, parameter/principal state,
results and rendered exports. Dataset equality cannot prove page layout or report
calculations. Choose an explicit reuse, semantic reconstruction or warehouse/DMA
route; propagate model gaps through the existing backend handoff. Each selected
report requires its own candidate/readback/coverage evidence; dashboard and App
receipts cannot satisfy report delivery. Local receipts remain unauthenticated
and preserve unknown access, native fidelity and acceptance.

## Native editor qualification

An authorized browser pilot may inspect the actual designer, connected workbook
queries, report JSON controls, preview, draft/save behavior and export controls.
Record the actual report and workbook IDs separately, selected parameters,
principal, data watermark and exact definition bytes before/after. An observed
control is evidence for that tenant only; it is not an external API contract.
Do not copy an undocumented route into the executor, infer engine/schema versions
from branding, suppress evaluation notices or change licensing. Empty connected
queries are a data-binding gap, not a zero-sales result.

The [native helper](../../omni-report-builder/scripts/report_native.py) prepares
an opaque definition only after A–F design gates. `qualify` retains exact supplied
runtime/schema evidence; it never authorizes execution. `observe` binds supplied
readback/export evidence to the same candidate, data, assets and parameter context.
`coverage` recomputes report QA cases, and `verify-delivery` supplies the separate
report lane for migration returns. Neither JSON syntax nor a matching supplied
readback is authenticated native execution. Report contract v2 requires explicit
requirement-to-section/parameter/output/acceptance bindings; v1 remains readable
with its mapping gap and must be upgraded for new native preparation.

MCP equivalents are `report_prepare`, `report_qualify`, `report_observe`,
`report_check`, `report_coverage` and `report_verify_delivery`. They are local tools.
No `report_execute`, publish, subscription or distribution tool is enabled.
