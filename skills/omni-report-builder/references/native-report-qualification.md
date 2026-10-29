# Native Reports qualification

Reports is the selected native target and is treated as **Beta** in this package.
Recheck product release truth and the actual tenant before promising behavior.
An underlying reporting engine can support features that Omni has not exposed,
enabled or qualified. A merged product change does not establish tenant availability.

Retain bounded evidence of:

1. Exact Omni instance, intended principal, feature availability and native report
   identity. Administrator access is not evidence for a recipient's access.
2. Native runtime/schema version and supplied definition shape. Determine whether
   the exposed format is RDLX-JSON and how Omni binds datasets/fields. Do not treat
   it as SSRS RDL XML or infer a schema from a filename.
3. Available authoring route: native editor, native AI, or an independently verified
   API/CLI contract. Record exact request/readback semantics and supported changes.
   Code-editor availability alone does not establish an external write API.
4. Current-state retrieval, conflict detection, save/publication lifecycle and
   recovery. Do not assume App or dashboard draft mechanics also apply to Reports.
5. Supported output formats, renderer/exporter versions, fonts, page settings,
   resource loading and result-size limits. Inspect PDF and Excel separately.
6. Query and parameter semantics, dataset completeness, cache/refresh policy,
   intended user access and any distribution/recipient isolation requirements.

This foundation permits local report candidates and evidence-bound published
observations. Native report draft state and automatic writes remain unqualified.
No report-specific network executor is exposed. A local capability file is retained
evidence, never an authority token or permission to execute an endpoint.

Treat imported definitions as untrusted. Preserve originals privately; flag embedded
code, connection strings, credentials, external URLs, expressions, extensions and
subreports before any runtime load. Do not fetch assets or evaluate formulas while
inspecting structure. Use existing reviewed Omni query references; no credentials
or raw customer rows belong in distributable definitions or repository fixtures.

Vendor learning references, reviewed 2026-10-29:
[layouts](https://developer.mescius.com/activereportsjs/docs/ReportAuthorGuide/report-configuration/Report-Layouts),
[export interfaces](https://developer.mescius.com/activereportsjs/docs/DeveloperGuide/ActiveReportsJSViewer/Export),
[release information](https://developer.mescius.com/activereportsjs/releases).
Use the documentation matching the observed runtime. These references do not
authorize library acquisition, license use or claim Omni API compatibility.

## Observed native editor route

A supplied native Reports Beta inspection on 2026-10-29 showed an ActiveReportsJS
visual designer, an editable Report JSON view with Apply, a Connected queries
panel referring to workbook query tabs, Preview and a native draft bar. The
observed evaluation banner did not establish licensing or the deployed runtime
version. This is tenant-specific UI evidence, not a released external API contract.

For an authorized native-editor build, inspect available workbook query tabs and
connect the selected reviewed queries, author the selected layout in the designer
or Report JSON view, Apply, then Preview. Retain the actual resulting definition
and native identity before evaluating pagination/export. Inspect draft/save and
publication behavior separately; the presence of a draft bar alone does not
qualify lifecycle, conflict resolution or recovery. An empty editor has no saved
schema or query binding to reuse. Do not fabricate either from its controls.

Under CLI/API-only constraints this UI route is unavailable without an explicit
exception. Continue [local preparation](local-preparation.md) and return the
missing runtime/authoring evidence. No fallback report network adapter is provided.
