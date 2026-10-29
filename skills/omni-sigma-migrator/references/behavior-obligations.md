# Sigma source review and handoff

Use the selected source objects as the denominator. The number of successfully
exported queries is not the number of migrated requirements.

| Source concern | Preserve and qualify | Owner after source review |
| --- | --- | --- |
| Workbook, page and placement | Native IDs, repeated placements, layout, responsive intent, text/images and unknown nodes | Designer and translator |
| Data/model dependency | Connection/model/table/column identity, grain, joins, formula AST, null behavior, aggregates, sort and totals | Analyst, BI engineer, scoped DMA |
| Controls and drill | Actual target elements, defaults, parameter encoding, dependency/reset/clear behavior and each selected state | BI engineer and QA |
| Input tables and actions | Write target, identity, validation, transaction/error semantics and approval path | App engineer and security owner; block unsupported writes |
| Saved views, schedules and embeds | Version, audience, state, delivery/scheduling parameters and effective embedded principal | Product owner and platform owner |
| Branding and media | Source assets/rights, loading policy, accessibility and authentic customer website/logo choices | Branding and designer |
| Access | Allowed and denied personas, effective query identity, row/column restrictions | Independent QA and security owner |
| Refresh and export | Source cache observation, target policy decision, data-as-of, export limits and expiry | Analyst, engineer and QA |

For every concern retain observed, supplied, unknown, unsupported, deferred or
excluded status, evidence reference, source object ID, target expectation and
owner. Exclusion requires an attributable scope decision; it never deletes the
source evidence. An unresolved required behavior remains a blocker even if every
converted chart looks correct.

Official references, checked 2026-10-29:

- [Workbook export API](https://help.sigmacomputing.com/reference/export-workbook): element PNG/data exports and page PNG; query expiry and format-specific limits apply.
- [Manage workbooks as code](https://help.sigmacomputing.com/docs/manage-workbooks-as-code): Beta definitions and documented omissions; current contents do not establish tagged/saved-view identity.
- [Sigma MCP](https://help.sigmacomputing.com/docs/use-sigma-mcp-server): user permissions and published-content limitations; transferred results remain evidence, not target authority.
- [Official REST schema](https://assets.sigmacomputing.com/openapi/public-rest-api/sigma-computing-public-rest-api.json): exact request fields must be requalified when changing supported profiles.
