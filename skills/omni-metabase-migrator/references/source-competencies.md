# Metabase source competencies

This reference guides interpretation, not new tool or permission grants. Vendor
documentation was reviewed 2026-10-28; qualify the actual tenant and client before
using an operation. Read the [source contract](../../omni-artifact-translator/references/metabase-source-contract.md)
for what this package accepts and the [run guide](../../omni-artifact-accelerator/references/metabase-visual-run.md)
for the bounded implementation. Documented capability, available tool and successful
capture are different observations.

## Product, tools and identity

Metabase's official MCP uses `/api/metabase-mcp`, OAuth and the caller's permissions,
subject to administrative enablement. Its `get_content` tool needs the requested
definition, visualization, parameter and layout inclusions; a search hit is not
a full object definition. Retain detailed IDs and the actual tool contract.
Query pagination and inline chart presentation depend on the operation/client;
an inline chart does not establish full-dashboard rendering. Use only approved
read/query operations, not authoring tools discovered alongside them.
[MCP](https://www.metabase.com/docs/latest/ai/mcp),
[MCP tools](https://www.metabase.com/docs/latest/ai/mcp-tools).

REST is unversioned. Pin the tenant version and inspect its `/api/docs` before
qualifying endpoint shapes. A route copied from another tenant or an old extractor
is not an API contract. API keys inherit their assigned group's permissions; keep
secrets in the approved host mechanism and retain the effective principal evidence
separately. [API](https://www.metabase.com/docs/latest/api),
[API keys](https://www.metabase.com/docs/latest/people-and-groups/api-keys).

Keep numeric runtime IDs, serialization entity IDs and OAA occurrence keys separate.
Use explicit source crosswalk evidence. Preserve collection hierarchy, dashboard
tabs, repeated dashcard placements, cards/models/metrics, source-card references,
database/table/field identities and unresolved references. Names and position
alone are insufficient for identity or dependency resolution.

## Definitions and query semantics

Retain raw `dataset_query`, source query type, complete MBQL stages, native SQL,
template tags, result metadata and all unknown fields. Classify supported simple
field/filter/aggregation evidence separately from multistage queries, joins,
nested saved questions, expressions, models, metrics and SQL parameters. Preserve
the exact unsupported clause and affected consumer. Do not silently use only the
final stage, discard filters or emit a dimensions-only query after losing a measure.

The sibling Domo engine's Metabase reader is useful inspected source precedent,
not an installed dependency or a complete compiler. Its converted tile count is
not a source denominator. The offline readers never execute query definitions or
compile arbitrary MBQL. Connected capture may execute an explicitly authorized
saved question, including its stored native SQL, through Metabase. That separate
grant binds the exact reviewed card definition and request body and requires
evidence of a read-only source identity/query scope. It does not permit arbitrary
or ad-hoc SQL, imported-code execution or query authoring. Ask the analyst/DMA to
resolve grain, metric definition, source-card dependencies and exact Omni bindings
before a target query is accepted.

Serialization is available on Pro/Enterprise and excludes users, groups and
permissions. Supplied serialization may retain otherwise missing content evidence,
but it cannot establish access parity. Preserve the original files; this integration
does not run Metabase import/export commands, parse arbitrary YAML or load an
archive to execute source content. Any added parser/runtime requires exact approval.
[Serialization](https://www.metabase.com/docs/latest/installation-and-operation/serialization).

## Visuals, behavior and results

Preserve original chart display and visualization settings, axes/series, formatting,
conditional styles, links, text/action content, tab ordering and per-placement
overrides. Unsupported settings remain obligations rather than a table fallback.
For every dashboard parameter, retain type/default/required state, per-dashcard
target, exclusions and affected queries. Linked filters and click behavior need
their own source observations; a global field list loses this wiring.
[Dashboard filters](https://www.metabase.com/docs/latest/dashboards/filters),
[linked filters](https://www.metabase.com/docs/latest/dashboards/linked-filters),
[interactive dashboards](https://www.metabase.com/docs/latest/dashboards/interactive).

Metabase documents PNG chart exports, CSV/XLSX/JSON result exports and dashboard/
current-tab PDF screenshots. Preserve the chosen export route, tabs, limits,
formatting and result population; none alone provides every definition or behavior.
This package's accepted evidence formats are narrower than the vendor export menu.
Use supplied approved files where a connected capture operation is unavailable;
do not invent a screenshot endpoint or a browser exception.
[Exporting results](https://www.metabase.com/docs/latest/questions/exporting-results).

Capture requested and observed filters separately, with principal, time zone,
locale, source watermark, cache evidence and complete pagination/result limits.
HTTP success, an empty array or a displayed total does not prove population
completeness. Bind original result bytes to the exact dashboard/tab/dashcard/card
definition and state. A mismatch keeps comparison inconclusive.

## Cache, access and operational ownership

Source caching configuration is evidence about source behavior, not a guarantee
of observed freshness or a prescription for Omni. Record available cache policy,
request intent, actual timestamps and unknowns. Ask the target App cache/refresh
question at D; no custom policy remains a valid choice. Avoid inventing a backend
TTL or automatically forcing fresh queries.
[Caching](https://www.metabase.com/docs/latest/configuring-metabase/caching).

Keep content access, data access, exports, public/embed use, scheduled delivery and
alerts as separate obligations. Declared permissions and admin exports cannot
replace allowed/denied persona tests. Do not create public links, change schedules
or transfer recipients during passive discovery. Follow the [behavior handoff](behavior-handoff.md)
and preserve all unqualified operational lanes in the return.
