# Domo application behavior

Classify the source before designing a replacement: App Studio composition,
custom App, Brick, embedded experience, or a combination. Retain original manifests,
configuration, code, assets and wiring as inert evidence. Do not execute imported
JavaScript, install its packages or load its remote resources to discover behavior.

## Current vendor context

Official sources checked 2026-10-29. Recheck applicable tenant features before
delivery; this context does not qualify an acquisition or target execution route.

[App Studio](https://www.domo.com/docs/s/article/000005295) documents persistent
filters, dates and Variables; Variable persistence applies on pages containing that
control. Filter exceptions and component actions need separate capture. Charts can
be created within an app, so a standalone Card list is not a complete component
inventory. With Allow export enabled, embedded content supports CSV, PowerPoint,
Excel and print. A Workflow widget targets a specific workflow version. The linked
conditional-rendering, grouped-data and KPI-component articles carry **Beta** labels;
retain those labels rather than treating all components as universally available.

[Custom Apps](https://www.domo.com/docs/portal/Apps/Overview) can use App Framework
APIs and transactional storage; a custom JavaScript experience is not simply an
Analyzer Card layout. [AppDB](https://www.domo.com/docs/portal/API-Reference/app-framework-apis/AppDB-API)
stores app-owned JSON documents in collections and can synchronize collections to
DataSets. Capture store dependencies and synchronization separately from the
analytical data source; neither is an automatic native Omni replacement.

## Inventory behavior before choosing architecture

For every page, component and repeated placement record its native/source locator,
data binding, parent, visibility, content, layout and events. Keep text, assets,
inline charts, nested containers, tabs, forms and custom content visible even when
there is no standalone Card/query ID. If the source schema cannot represent one,
retain the original and an explicit mapping gap instead of inventing a native ID.

Produce a state/transition inventory covering:

- Navigation and entry/deep-link state; active tab, back behavior and state restored
  between pages, sessions or users.
- Control defaults, persistent versus local values, affected/exempt components,
  variables, reset behavior, conditional visibility and empty/error/loading states.
- DataSet aliases and column mappings; AppDB collections, schemas, record ownership,
  permissions and sync dependencies; files, documents and external service calls.
- Every action's trigger, inputs, actual effect, identity, destination and response
  handling. Separate read/navigation/filter actions from writes, submissions,
  workflow starts, code execution, messages and file mutations.
- Embed context, audience/authentication, responsive layout and permitted exports.
  Do not widen distribution or enable public sharing to acquire a visual reference.

Classify custom code by behavior and dependencies, not visual appearance. Preserve
unsupported functions and opaque bundles as unreviewed originals; source hashes do
not prove safety or completeness. Bricks may contain both analytical rendering and
operational code, so classify actual calls instead of granting them a read-only label.

## Read-only Apps are valid

For an analytical App, explicitly record that no side effects were observed or are
requested, with evidence and remaining unknowns. That statement does not prove the
absence of hidden code. Use ordinary source inventory/experience requirements for
the read-only portion. If the existing external assignment contract cannot express
an empty side-effect scope, retain that limitation; never add a fictional workflow
or writeback to make the handoff validate.

When side effects are real, record the workflow/function version, trigger, payload,
authorization, destination, validation, confirmation, retry/idempotency, audit and
failure/recovery requirements. Unknown details remain unresolved. Do not execute
the source action merely to observe it. A separately authorized safe test or
provided execution evidence may be needed.

## Hand off an honest target proposal

Choose a dashboard for dashboard work, a native App for an accepted application
experience, or another explicitly selected surface. The source product name does
not force the target architecture. Assign analytical queries to the BI/semantic
workflow and experience implementation to the App engineer. For persistent writes
or integrations, name the required external service and operational owner only
when established; keep unsupported native capabilities as gaps.

Return an action-by-action disposition and candidate-bound acceptance cases.
Preserved analysis does not establish operational equivalence. An App with working
charts but an unresolved required write or workflow remains partially migrated;
an intentionally read-only App needs no artificial operational feature to finish.
