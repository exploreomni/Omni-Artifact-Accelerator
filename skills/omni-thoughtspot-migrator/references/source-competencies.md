# ThoughtSpot source competencies

Official documentation reviewed 2026-10-28. Vendor capability, implemented local
support and a qualified tenant are different evidence. Pin the actual version.

| Area | Required interpretation | Primary reference |
|---|---|---|
| Definition | JSON/YAML TML, object GUIDs, references, model/worksheet schemas; keep original bytes | [TML](https://developers.thoughtspot.com/docs/tml), [export](https://developers.thoughtspot.com/docs/tml-export) |
| Answer | Search expression, local columns, formulas, table/chart configuration, `client_state` | [Answer TML](https://docs.thoughtspot.com/cloud/26.9.0.cl/tml-answers) |
| Composition | Inline Answers, visualization IDs, tab tiles, overrides and views | [Liveboard TML](https://docs.thoughtspot.com/cloud/26.9.0.cl/tml-liveboards) |
| Visual creation | Native versus classic chart generation, chart roles and styling | [Charts](https://docs.thoughtspot.com/cloud/26.10.0.cl/charts), [new library](https://docs.thoughtspot.com/cloud/26.10.0.cl/charts-library-new), [styles](https://docs.thoughtspot.com/cloud/26.10.0.cl/style-customization) |
| Evidence acquisition | Explicit selectors, paging, source result state and export formats | [Data APIs](https://developers.thoughtspot.com/docs/fetch-data-and-report-apis), [Report APIs](https://developers.thoughtspot.com/docs/report-apis), [REST reference](https://developers.thoughtspot.com/docs/rest-apiv2-reference) |
| Runtime behavior | Filter precedence, linked columns/exclusions, actions and embedded state | [Filters](https://developers.thoughtspot.com/docs/filters-overview), [actions](https://developers.thoughtspot.com/docs/customize-actions), [downloads/refresh](https://developers.thoughtspot.com/docs/liveboard-data-downloads) |
| Optional MCP | Versioned licensed capability, discovered schemas, discovery/session/write separation | [MCP integration](https://developers.thoughtspot.com/docs/mcp-integration), [Spotter 3](https://developers.thoughtspot.com/docs/mcp-server-spotter3) |

## Qualification traps

- TML export needs the documented data-management or administration privilege;
  data/visual downloads have distinct RBAC requirements. Export ability never
  substitutes for allowed/denied persona tests in either platform.
- Current Liveboard TML documentation says non-admin exports include only the
  exporting user's views, while admin exports include all users' public/private
  views. Visible public views owned by someone else may therefore be absent.
  R/Python visualizations are not TML-exportable. Preserve inventory gaps.
- Model export uses schema v2; Worksheet v1 is documented as **Deprecated**.
  `export_column_security_rules` and `export_with_column_aliases` are **Beta**;
  neither is enabled by the initial bounded profile. Their absence cannot prove
  that security or aliases do not exist. The `/tml/export/batch` API concerns
  users, groups and roles, not a generic Liveboard batch exporter.
- The new chart library is documented **GA**. Existing classic charts can remain
  classic. Verify the selected object instead of assuming every chart migrated
  to the newer rendering contract. Preserve unknown chart types as review work.
- Data APIs default to a small page. Explicit finite pagination and an independent
  completeness observation are required. Formatting, preview limits, hidden
  exported columns and totals can make a plausible result the wrong population.
- PNG Liveboard exports need an explicit selected tab. Note tile IDs are not
  visualization export selectors. Saved-filter overrides are distinct from runtime
  filters. Multi-visual CSV exports may be ZIPs; transferred archives are inspected
  within bounds and are never executed or indiscriminately extracted.
- The pinned Answer report documentation has conflicting identifier guidance.
  Its connected route is blocked until a verified version contract resolves it.
  Saved Answer and qualified Liveboard routes remain available.
- A requested MCP date may resolve to the nearest earlier release. Retain the
  actual schemas and effective version. Spotter MCP is an Enterprise/Embedded
  add-on; SpotterCode is a different surface and is not this package's executor.

## Mapping judgment

Translate business meaning, task flow and behavior, not just chart names. Native
Omni availability must be verified for the intended target. A custom layout may
need an App while a governed repeat-use analysis may fit a dashboard. Preserve
the same metric contract across both. Any adapted visual, unsupported behavior or
security dependency needs an explicit disposition and an observable target case.

Do not translate ThoughtSpot search/formula text by replacing function names.
Resolve source grain, joins, aggregation, parameters and filters with the analyst;
send real backend gaps to DMA. Keep undocumented group/tab runtime schema details
in supplied inventory rather than inventing native TML fields.
