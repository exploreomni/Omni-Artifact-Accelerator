# Qlik source competencies

Official references reviewed 2026-10-28. Documentation, implemented support and
qualified tenant behavior are different evidence. Pin the actual profile.

| Competency | Required interpretation | Primary reference |
|---|---|---|
| Native visual composition | Sheets, object definitions, master items, dimensions/measures, instances and containers | [Visualizations](https://help.qlik.com/en-US/sense/November2025/Subsystems/Hub/Content/Sense_Hub/Visualizations/visualizations.htm), [master dependencies](https://help.qlik.com/en-US/sense/May2026/Subsystems/Hub/Content/Sense_Hub/Visualizations/change-data-of-visualization.htm) |
| Definitions and sessions | Enhanced JSON-RPC, persistent IDs versus handles, isolated selection sessions | [QIX](https://qlik.dev/apis/json-rpc/), [property tree](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/EngineJSONAPI/Content/service-genericobject-getfullpropertytree.htm) |
| Result shapes | Straight/pivot modes, page rectangles, dual values, axis paths, totals and completeness | [Straight data](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/EngineJSONAPI/Content/service-genericobject-gethypercubedata.htm), [pivot data](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/EngineJSONAPI/Content/service-genericobject-gethypercubepivotdata.htm) |
| Analytical context | Selection overrides, set identifiers/modifiers/operators, inner/outer sets and alternate states | [Set analysis](https://help.qlik.com/en-US/sense/November2025/Subsystems/Hub/Content/Sense_Hub/ChartFunctions/SetAnalysis/set-analysis-expressions.htm), [alternate states](https://help.qlik.com/en-US/sense/May2025/Subsystems/Hub/Content/Sense_Hub/Visualizations/alternate-states-comparative-analysis.htm) |
| Visual references | Existing chart/sheet exports, selected state, async status, output expiry and selection failures | [Reports API](https://qlik.dev/apis/rest/reports/), [reporting overview](https://qlik.dev/manage/reports/) |
| Optional official MCP | Discovered schemas, bounded chart data, readback after selection changes; no source writes | [Tools](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/QlikMCP/Qlik-MCP-server-tools.htm), [connections](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/QlikMCP/Connecting-Qlik-MCP-server.htm) |
| Effective access | Space permissions, application exclusion, row reduction, OMIT fields and identity | [Section Access](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Scripting/Security/manage-security-with-section-access.htm), [MCP permissions](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/QlikMCP/Qlik-MCP-Permissions.htm) |

## Qualification traps

- MCP tool availability depends on tenant licensing, user/space permissions and
  the connected catalog. Documentation contains naming inconsistencies; use
  actual schemas and retain the effective version rather than guessing aliases.
  The documented catalog has chart metadata/data tools; this implementation does
  not infer an image-export tool from their presence.
- QIX sessions may share selections. A reconnect or reused session is not proof
  of the previous population. Retain isolated-session evidence and fresh state
  readback; restarting a connection invalidates affected observations.
- GetHyperCubeData is for straight mode; the documented May2026 limit is 10,000
  cells across requested pages. Pivot modes need separate axis/rectangle logic.
  A page-sized response is not full data and display text is not a numeric value.
- Reports can complete while reporting selection errors. Preserve and reject
  errors for parity evidence. Do not silently retry an uncertain creation POST.
  Qlik marks some report types internal-only; exclude them from public capture.
- A default bookmark, locked selection, alternate state, variable or expression
  can change a chart's population. Target date/time/locale and freshness rules
  must be explicit. Source cache and export TTL do not set target app policy.
- Source model associations, synthetic/link keys, resident/preceding loads,
  mappings, incremental logic and data islands need backend review. A static
  script is evidence, not execution or a universal SQL translation.
- Section Access is not a display filter. Test allowed and denied identities,
  row reduction and omitted fields independently in the target. Secrets and
  security-table contents require private handling; logs/repo fixtures stay neutral.
- Exported custom themes/extensions may not match live rendering. Keep original
  visual references and unresolved behavior; never load extension JavaScript,
  external images/fonts or binary decoders during intake.

Windows documentation describes version-specific Engine/visual semantics; it
does not automatically qualify a Cloud tenant or the inverse. A QlikView app in
a Cloud catalog remains QlikView and is not admitted to this Sense adapter.
