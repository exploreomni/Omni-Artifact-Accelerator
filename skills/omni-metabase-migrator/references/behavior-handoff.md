# Metabase behavior and handoff

Use the shared [migration ledger](../../omni-qa-analyst/references/migration-behavior.md)
and [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md).
The source specialist contributes Metabase-specific evidence to those records;
it does not certify its own build or create another coordinator.

| Obligation | Preserve | When evidence is missing |
| --- | --- | --- |
| Scope and identity | Tenant/version, collection, dashboard/tab, dashcard occurrence, card and explicit crosswalk; independent expected set | Keep unknown/denied/omitted objects in scope; no title-based joins |
| Query and model | Raw MBQL/SQL, all stages, source cards/models/metrics, field IDs, tags, grain, units, aggregations and dependencies | Retain complete clauses; block equivalence until semantics and bindings are resolved |
| Controls | Parameter ID/type/default, each placement's target, affected/unaffected queries, linked filters, URL values, required/reset behavior | Require exact inspected target bindings or an explicit adaptation; never flatten mappings into one field |
| Presentation | Tabs, repeated cards, non-query content, series, local visualization overrides, conditional formats and order | Preserve the denominator independently of parser/query success |
| Interaction | Click/filter/drill/link actions, destination parameters, return state and source actions with write effects | Record unsupported/pending behavior; never execute a source action to discover it |
| Numerical evidence | Raw export, definition/state hashes, result types, population, pagination, watermark, time zone and tolerance | Keep comparison inconclusive; rendering is not a numerical oracle |
| Cache and refresh | Source intent/observations plus actual user-selected target App policy | Do not inherit a guessed server TTL, automatic bypass or default expiry |
| Access and operations | Source principal, separate allowed/denied observations, sharing/embed/export/schedule consumers and owners | Retain pending lanes; metadata and serialization cannot certify effective rights |

The translator owns original identity and facet retention; the analyst owns metric
interpretation and independent expected cases. The BI engineer resolves current
Omni topics/fields and control bindings. Designers preserve the selected quality
bar and actual user choices. Source familiarity is not permission to downgrade
the experience or impose one reusable layout on every migration.

Use the existing `reuse_existing`, `omni_semantic_reconstruction` or
`warehouse_first_refactor` route decision; `unselected` permits clarification only.
For DMA work, prepare bounded normalized requirements with `source_platform:
"metabase"`, affected frontend IDs, semantic/security dependencies and independent
cases. Keep the dependency-complete selected slice within the existing exchange
limit. There is no DMA Metabase `source_adapter_result` in this integration and no
permission to relabel Domo output as one. Use request/response/receive/select and
retain the actual selected backend candidate; a candidate is not deployed fields.

All new engagements use A–F, even when the intended outcome is faithful migration.
Reuse valid existing answers in those checkpoints. Carry the approved source
preservation/adaptation obligations and App refresh policy through options,
selected design, build and QA. Retain historical policy rather than manufacturing
old choices or silently restarting an existing accepted engagement.

Keep dashboard and App candidates, native receipts and observations separate.
Changes to source definitions/state, selected backend or target code reopen affected
cases. Reconcile unknown writes rather than blindly retrying. Native publication,
source retirement and schedule changes require their own authority.

Before reporting completion, reconcile every migrated/deferred/excluded object and
the required query, numerical, interaction, access, visual/accessibility,
performance and operational lanes. Report accepted differences and actual business
review status. Local checks, source capture and native readback are separate
evidence levels; none automatically closes the rest.
