# WebFOCUS source competencies

Official source research reviewed 2026-10-28. References are version-specific
(primarily 9.3); their existence does not qualify a customer's installed release.
Record the actual client/server version, authoring origin and available API contract.
This reference informs interpretation, not execution permission.

## Authoring and composition

Designer starts from a data source and assigns dimensions/measures to buckets:
axes, color, size, tooltip, matrix and animation. Capture aggregation (summary,
count or detail), ordering and layout mode independently of chart type. A color
bucket may be a category or measure; a size bucket is an encoding, not decoration.
Multipage/animation behavior must be checked in the actual authoring/runtime mode.
[Creating Charts, 9.3.6](https://docs.tibco.com/pub/wf-wf/9.3.6/doc/html/en-us/designer-user/Creating_Charts_900.htm)

Pages can create content in place or assemble existing repository content. Record
page, section, container and content occurrences separately. Multi-content
containers can change which item is visible; reusing one report twice does not
make the two placements interchangeable. Preserve supplied layout/responsive
intent, filters, embedded URLs and images; never fetch a source URL automatically.
[Creating Pages, 9.3.7](https://docs.tibco.com/pub/wf-wf/9.3.7/doc/html/en-us/designer-user/Creating_Pages_8207.htm)

Designer exposes content source syntax and page CSS/JavaScript. Capture custom code
as an inert dependency with owner/locator/hash. It can change style and runtime
behavior beyond the visible chart. Source snippets alone do not establish page
schema compatibility or actual rendered behavior.
[Designer structure, 9.3.3](https://docs.tibco.com/pub/wf-wf/9.3.3/doc/html/designer-user/framework_navigate_8207.htm)
[Custom page code, 9.3.6](https://docs.tibco.com/pub/wf-wf/9.3.6/doc/html/en-us/designer-user/CSS_and_JS_8207.htm)

## Procedure and style interpretation

Retain complete original FEX, not a reconstructed query. TABLE/GRAPH requests may
share virtual fields and include files; application-path resolution is separate
from file discovery. The DMA parser recognizes only a bounded literal subset.
DEFINE and COMPUTE evaluate at different stages; PRINT detail duplicates, SUM
aggregation, BY/ACROSS groups, subtotal recalculation, nulls and format conversion
need independent expected cases. USAGE/FORMAT is not ACTUAL physical precision.
HOLD/MATCH/MORE, multiline expressions, Dialogue Manager, amper variables and SQL
passthrough remain explicit semantic obligations.

GRAPH FILE requests can combine WebFOCUS styles with multiple GRAPH_JS and
GRAPH_SCRIPT blocks. Preserve order and duplicate/conflicting properties. For the
9.3.6 documented syntax, the last conflicting property in the style section wins;
do not generalize precedence across unknown releases or unresolved includes.
Parse only a declared strict JSON subset without functions/evaluation. Legacy
script API calls and conditional styles require review, not regex-based execution.
[HTML5 charts, 9.3.6](https://docs.tibco.com/pub/focus/9.3.6/doc/pdf/IBI_focus_9.3.6_html5_charts.pdf)

## Acquisition profiles

The initial connected reader is repository metadata/source acquisition, not a
renderer or FEX runner. The 9.3.3 API documents repository listing (`get`), textual
source (`getContent`), properties, parameter descriptions and execution as distinct
operations. Some execution operations use GET. Allow the exact approved action,
canonical path and method; deny ad hoc source, run, write, delete and scheduling.
Do not classify describeFex/getDetails as safe from their name: leave them disabled
until their installed-version behavior and authority are qualified.
[Repository REST API, 9.3.3](https://docs.tibco.com/pub/wf-wf/9.3.3/doc/html/embedded-bi-user/02REST_WS16.htm)

Credentials and session/CSRF values belong only in the operator's approved secret
mechanism. Never copy documentation passwords, log cookies, follow authenticated
redirects or accept response-supplied destinations. Keep XML business errors
separate from HTTP success. Retrieval can return source text or versioned wrappers;
retain bytes and declared encoding. Unknown wrappers are opaque, not a successful
source extraction. No official universal page screenshot endpoint or vendor MCP
contract is assumed by this package.

Change Management exports selected resources into a downloadable package. Qualify
its actual manifest, included extensions and dependency closure. Legacy handles,
styles, assets and external application files may need additional supplied evidence.
Safely unpacking an archive establishes file inventory, not an interpreted Designer
page or complete repository. Never run a Change Management import/CLI automatically.
[Change Management export, 9.2.1](https://docs.tibco.com/webfocus/921/doc/html/topic/com.ibi.help.admin/source/change_mgt71.htm)

## Runtime evidence

Record static filters, prompted filters, required selections, multi-select values,
cascades and per-content parameter application. Required prompts may prevent initial
execution. Preserve both requested and observed state, reset/empty/invalid behavior
and unaffected content. A global parameter name alone is insufficient binding.
[Filters, 9.3.2](https://docs.tibco.com/pub/wf-wf/9.3.2/doc/html/designer-user/Adding_Filters_8207.htm)

Explicit drill targets, multi-drill menus, hierarchy Auto Drill and Auto Linking
are different mechanisms. Auto Linking can discover destinations at runtime from
BY fields and parameter names, constrained by the current user's permissions.
Record actual destinations/parameters and persona; static source cannot prove the
runtime menu. Custom portalDispatch behavior can target named page containers and
switch visible tabs. Preserve code as evidence and require an explicit adaptation.
[Auto Linking, 9.3.7](https://docs.tibco.com/pub/wf-wf/9.3.7/doc/html/en-us/infoAssist/Nav_Rpt_Chart69.htm)
[Drilldowns, legacy 9.1.2](https://docs.tibco.com/webfocus/912/doc/html/topic/com.ibi.help.intro/source/Drilldowns_8207.htm)

Preview mode matters: Sample, Live and Test may represent different populations.
Record limits and whether applied before or after aggregation. Generic Test values
are not numeric expectations. Reference captures require the source revision,
parameters, principal, time/locale, result population and observation evidence.
[Sample/live/test data, 9.3.2](https://docs.tibco.com/pub/wf-wf/9.3.2/doc/html/designer-user/WFD_Sample_Data_8207.htm)

In-Document Analytics can calculate/filter in the browser or use server caching
and paging. Interactive transformations may not appear identically in exports.
Separate source cache, page limits, query freshness and target App refresh policy.
Disconnected HTML can contain both sensitive data and executable script; preserve
it privately and inertly, never open it to obtain a preview without authority.
[In-Document Analytics, 9.3.4](https://docs.tibco.com/pub/wf-wf/9.3.4/doc/html/in-doc-analytics/design_apps2.htm)

ReportCaster schedules, bursting, delivery channels, report libraries and consumers
remain operational requirements. Inventory them without running or recreating them.
A dashboard replacement does not establish schedule, export or access equivalence.
