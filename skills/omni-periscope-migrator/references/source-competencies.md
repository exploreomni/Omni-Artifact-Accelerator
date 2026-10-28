# CDT source competencies

This reference guides source interpretation. It does not add endpoints, permissions
or executable capabilities. Use the [run guide](../../omni-artifact-accelerator/references/periscope-visual-run.md)
and current helper contracts for supported operations. Preserve version, tenant and
review date whenever relying on vendor behavior; an operation's documentation,
availability and successful exercise are separate observations.

## Product, identity and access

Identify CDT before choosing tools. The [Sisense documentation home](https://docs.sisense.com/main/Home.htm)
does not establish that a Linux/Fusion API or MCP feature applies to a CDT tenant.
Use CDT-specific documentation and inspect actual available operations. Lack of an
established CDT MCP is a capability gap, not permission to activate an unofficial
connector or use another product's API.

Pin tenant/Space, selected dashboards, source principal, permitted operations,
capture state and original files. Reconcile Git tokens and numeric dashboard IDs
using explicit source evidence. Similar titles are not identity proof. A source
admin export does not establish a viewer's effective rights; record access and
sharing obligations separately from layout and numerical results.

Space membership and role declarations are useful context, not effective-access
tests. Record a disabled or unavailable listing operation as a gap; an API 404
must not become an empty dashboard inventory. [Spaces](https://dtdocs.sisense.com/article/spaces),
[user and role management](https://dtdocs.sisense.com/article/user-and-role-management-api-rbac).
Connecting a Git repository is setup with synchronization effects, not passive
reading of a supplied snapshot. [Git connection](https://dtdocs.sisense.com/article/connecting-a-git-repository).

## Git definitions and analytical logic

CDT Git settings and code sidecars are separate evidence. Retain dashboard/chart
tokens, chart type, theme, position and size; encrypted definitions remain opaque.
Inherited configured filters may be absent from the settings. Preserve SQL,
Python/R and original configuration without executing them or inferring omitted
settings. [CDT Git configuration](https://dtdocs.sisense.com/article/git-configuration).

The pinned DMA adapter is the existing source-definition reader. OAA retains its
actual report plus original supplied evidence; it must not silently reimplement
the SQL/template dialect or import the DMA runtime. Recover views, snippets,
snippet parameters, custom modules and chart dependencies. Candidate references
remain candidates until resolved. Missing code, unknown language/version, template
substitution and ambiguous database bindings go to the analyst/DMA handoff.

Do not run source scripts, evaluate formulas to discover their behavior or install
packages listed by an export. Classify required custom-code outcomes: supported
governed-query equivalent, separately reviewed implementation, explicit accepted
adaptation, or unresolved/unsupported. The replacement requires numerical cases;
matching a rendered shape is insufficient.

SQL preview limits do not establish the population handed to Python/R. Preserve
the script's actual input/result scope separately; do not deserialize `.sav`/pickle
assets or import supplied custom modules. [R and Python](https://dtdocs.sisense.com/article/r-and-python),
[custom modules](https://dtdocs.sisense.com/article/custom-modules).
Direct replacements and parameterized snippets require original substitution and
filter context, not textual replacement with an assumed Omni field.
[Direct replacement filters](https://dtdocs.sisense.com/article/direct-replacement-filters),
[parameterized snippets](https://dtdocs.sisense.com/article/parameterized-sql-snippets).

## Visual, state and result evidence

Capture definition and visual evidence for the same source version and state. Keep
requested filters separate from observed filters and source results. Declare
widget coverage, export limits, hidden content, persona, timestamp, timezone,
watermark, result population and cache state; unknowns remain visible.

CDT's [Render API](https://dtdocs.sisense.com/article/render-api) returns a dashboard
PDF through a separate render request. Its defaults, expiring output, refresh
option and request limits require a bounded capture contract. A requested refresh
does not prove a fresh dataset or matching chart-result snapshot. Do not interpret
a ready PDF as proof that all source widgets were rendered.

Source CSV exports must retain their route and scope: internal full-data export and
shared displayed-data export cannot be treated as interchangeable populations.
No general authenticated CDT CSV-query API is established by this package's
research. Use an approved supplied export with explicit provenance when the helper
has no qualified retrieval method; never invent an endpoint or silently run source
SQL directly against the warehouse.
[CSV download](https://dtdocs.sisense.com/article/csv-download).
An existing public CSV URL is unauthenticated and user/filter-specific; its public
availability is not permission to widen sharing or automatically fetch it. This
workflow does not create public links. [Public CSV URLs](https://dtdocs.sisense.com/article/public-csv-url).
Record cache evidence using [CDT refresh mechanics](https://dtdocs.sisense.com/article/refresh-mechanics);
source freshness and target App refresh policy remain separate requirements.

## Metrics, behavior and design

Retain analytical grain, aggregation, filters and execution order; check totals,
NULL/blank/zero, sorting/top-N, date boundaries, timezone and currency. Treat chart
encodings, formatting, annotations and layout as design evidence. Classify native
Omni preservation or adaptation explicitly, keeping the accepted business question
constant. The selected target may be a dashboard, App or both; extra motion or 3D
is a user/task choice, not a migration default.
[Chart overview](https://dtdocs.sisense.com/article/chart-overview),
[mixed chart types](https://dtdocs.sisense.com/article/mixing-chart-types).
Drill navigation needs observed source and return-state behavior rather than a
copied URL. [Drilldowns](https://dtdocs.sisense.com/article/drilldowns).

## Coordination and acceptance

Follow the [behavior handoff](behavior-handoff.md) and existing scope/cowork/return
contracts. Reconcile source changes with shared-model consumers before scaling.
Do not retire source dashboards or transfer schedules, email recipients, embeds or
alerts automatically. Report unobserved runtime, visual, access and operational
lanes alongside delivered files; no single completeness flag replaces them.
