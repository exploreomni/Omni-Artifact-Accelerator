---
name: omni-powerbi-paginated-migrator
description: Interpret Power BI paginated RDL reports and preserve parameters, page behavior and export evidence for migration to Omni Reports Beta. Use for paginated reports; interactive PBIR/PBIP reports use the separate Power BI visual capture workflow.
---

# Power BI paginated migration specialist

Own paginated source interpretation within the existing
[accelerator](../omni-artifact-accelerator/SKILL.md). Partner with the shared
[Report designer](../omni-report-designer/SKILL.md) and
[Report builder](../omni-report-builder/SKILL.md); do not create a parallel target
workflow. Reuse actual user decisions and A–F gates.

Read [RDL intake](../omni-artifact-translator/references/rdl-report-source-contract.md)
and [capture/results](../omni-artifact-translator/references/report-source-capture.md).
Confirm the actual source item is a paginated report. A workspace/report GUID or
`.rdl` filename alone does not prove that. Interactive PBIR/PBIP, dataset DAX results
and page PNGs are not interchangeable with paginated RDL definitions or exports.

Preserve original definition bytes, independent inventory, workspace/report IDs
when actually known, source principal, data source bindings, parameters, report
sections and repeated placements. A supplied definition without a verified service
crosswalk keeps service IDs unknown. The shared inert reader retains namespace
versions, query/parameter/group semantics, expressions and custom code; it does
not compile RDL into target RDLX-JSON or evaluate either.

Keep default, blank, null and repeated parameter selections distinct. Capture
source execution context, effective principal, locale/timezone, cache observation,
freshness and population separately from the requested values. Source cache
behavior never supplies the user's independent target cache/refresh decision.

Treat definition retrieval and PDF/Excel export as distinct operations. Export may
execute source queries and needs its own scope and side-effect review. Pure local
request plans do not establish permissions, capacity, parameter application,
completion or a valid export job. Never serialize identity tokens into a saved
plan. Any future executor must bind returned job IDs to the exact submitted body,
validate status/file responses, reject redirects and avoid replaying uncertain
submissions. Capacity, tenant settings and runtime versions require current
qualification; no live capture is certified by this package's fixtures.

For parity, retain each exact output and parameter state. Compare dataset results
only as dataset evidence; report calculations, groups, visibility and pagination
need report-level results and rendered exports. PDF and Excel require separate
acceptance. Keep missing dependencies and unsupported behavior in the denominator,
route semantic changes through DMA when needed, and leave publication/distribution
and effective-user acceptance explicitly separate.
