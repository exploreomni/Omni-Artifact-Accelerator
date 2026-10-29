# Omni target capabilities and authoring boundaries

Checked 2026-10-21 against official documentation. Refresh the selected capability and actual tenant availability before implementation. Preserve any current GA, Beta, Preview, Experimental or deprecation label exactly; an absent label is not evidence for a GA assertion. The current Apps page does not display a Beta label. Old repository labels do not override current docs.

| Surface | Documented basis | Package application |
| --- | --- | --- |
| Native Apps | [Apps](https://docs.omni.co/visualize-present/apps): HTML/JavaScript presentation attached to workbook queries; governed access, filtering/drilling and bounded runtime capabilities | Inspect the current supported data bridge and real tab IDs; never invent SDK calls. Keep local prototypes distinct from native execution. Test all selected personas. |
| App theme | [Styling Apps](https://docs.omni.co/visualize-present/apps/styling): theme variables and default palettes available to the app | Use `--color-background`, `--color-surface`, `--color-text3`, `--color-primary` with `--color-text-on-primary`, `--font-body`, `--font-heading`. Recheck computed values and supported palette size; hardcoded styling does not inherit automatically. |
| App policy | [App settings](https://docs.omni.co/visualize-present/apps/settings) and [organization policy](https://docs.omni.co/administration/settings/app-policy) | Inspect per-app settings within the organization ceiling. Font/image failures do not authorize additional external domains, navigation or clipboard access. |
| Dashboard design | [Dashboard best practices](https://docs.omni.co/guides/dashboards/dashboarding-best-practices) | Start from audience questions; use supported chart/control semantics and guided exploration. Validate actual target behavior. |
| Dashboard document mutation | [Current document v2 commands](https://docs.omni.co/developers/cli/commands/documents) | Use the actual create/read/draft/patch/publish schema. The older `update`/`put` commands were removed; the former update-document reference returns 404. Preserve existing shared draft changes and verify creation/publication side effects. |
| Controls | [Document v2 content](https://docs.omni.co/developers/cli/commands/documents) and [dashboard commands](https://docs.omni.co/developers/cli/commands/dashboards) | Inspect current control/filter schema and scope before editing. Reread native control bindings and test propagation; a filter definition does not prove behavior. |
| Application brand | [Application theme](https://docs.omni.co/administration/themes/application) | Import resets omitted properties to defaults; saving affects internal and applicable embedded users. Treat a complete import differently from a patch. Theme Lab is **experimental**. |
| Document brand | [Document themes](https://docs.omni.co/administration/themes/documents) | Theme creation/editing, single-document application, default changes and bulk application have distinct effects. Inspect consumers before changing a shared theme. |

## Authoring routes

For native **Reports Beta**, use the [report qualification contract](../../omni-report-builder/references/native-report-qualification.md)
and [report workflow](report-workflow.md). This is a separately selected target.
The foundation records the supplied Beta status; the historical Apps/dashboard
documentation check above does not establish a Reports release or API contract.
Verify the exact tenant, native definition schema, query bindings and output
engine. A code editor or native-AI path does not prove external API availability.
The package supplies local design/routing checks, not a Reports mutation executor.
Do not reuse dashboard/App draft mechanics or claim engine-level export features
without runtime evidence. Preserve per-format qualification and acceptance gaps.

Use the best available documented connector, CLI/API or native UI for the selected operation. Read its actual capabilities before selecting it. Existing content-builder, query, embed or customer-customization skills may help when installed; they are optional adapters, not hidden dependencies. A tool name or endpoint in an old example does not establish current availability.

For Apps, native Omni editing is the target. If only local files can be created, produce a clearly labeled HTML/CSS/JS candidate plus query bindings, explicit runtime-integration gaps and a native verification checklist. Do not pretend a local data array is a live model. Do not embed API keys in client code. Current docs describe input-column writes and a limited read-only metadata API path; these are separate capabilities, not generic warehouse writeback or arbitrary REST access.

For dashboards, retain workbook tabs, exact query identities, layouts, filters/listeners, controls and theme references. Check the selected export/import/create/update contract. Native validation must cover results, interaction, rendering and access. No hidden endpoint discovery or unsupported payload guessing.

For connected builds and matched-state visual evidence, use [native build/export](../../omni-bi-engineer/references/omni-build-export.md). Its current MCP/CLI/API inventory distinguishes dashboard edits, immediately published new dashboards, App draft operations and actual target exports. App CLI mutation commands carry an **alpha** label even though Apps themselves are stable in that documentation. Capability and transport labels must remain separate.

For externally embedded experiences, separately select hosting, SSO session creation, allowed origins, server-side secret ownership and tenant isolation. Embedding a native Omni App is different from writing a separate frontend that calls analytics services.

Capture current docs URL, checked date, tenant feature/settings observations, chosen adapter version, target IDs and unresolved limitations in the engagement. A documented capability and this package's tested automation coverage are different records.
