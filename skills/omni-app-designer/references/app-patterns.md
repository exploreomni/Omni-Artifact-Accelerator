# App patterns for analytical tasks

Use for screen composition, navigation, adaptive interaction, and recovery choices. For new concepts or substantial redesigns, first use the [ideation playbook](../../omni-design-systems/references/ideation-playbook.md). Do not restart discovery for a small edit or faithful migration. Patterns below are proposed design behavior until [Omni capabilities](../../omni-artifact-accelerator/references/omni-capabilities.md), workbook/query bindings, and the actual target confirm support.

## Make an information map

Map `task → information needed → destination → contextual action → return path`. A destination changes where someone is; an action changes scope or performs a command. Use clear, task-specific labels and avoid a home screen that repeats every function without context. A dashboard overview can still be appropriate when its job is monitoring; this is not a ban on overview screens.

For each screen, answer: where am I, what is in scope, what can I do here, and how do I return? Decide which information must remain visible and which detail can be disclosed when requested. Essential filters, permission context, and qualifications must not disappear merely to simplify a screen.

| Pattern | Fits when | Avoid or adapt when | Design decision to expose |
| --- | --- | --- | --- |
| List and detail | People scan comparable records, then inspect one | The task is only population monitoring, or selecting one item would conceal required side-by-side comparisons | Selection identity, comparison columns, detail relationship, and return context |
| Overview and investigation | People monitor a known population before examining exceptions | Users already know the item and the overview adds an unnecessary step; summary definitions remain unresolved | Which observation leads to which detail; whether filters and populations match |
| Main view and supporting pane | People need definitions or supporting evidence alongside a primary task | Both panes become unreadable, or essential qualifications would disappear when the pane collapses | What can collapse without hiding the decision context; keyboard route between areas |
| Guided sequence | A task has a meaningful order or branching choices | Analysis is exploratory and forcing a sequence blocks comparison or return | Progress, reversibility, skipped/unavailable steps, and what completion actually means |

Choose by the task and source behavior, not because a platform example looks attractive. Do not force migration controls into another pattern without recording the proposed departure. Existing source-route, scope, and acceptance decisions remain in force.

## Reusable interaction card

This is a design handoff shape, not an importable API schema. Populate exact identities from the engagement; use explicit unresolved values instead of invented tab IDs.

```yaml
interaction: <stable local ID and artifact version>
user_task: <task, persona, and analytical context>
pattern_and_destinations: <chosen pattern, screen titles, information map>
navigation: <entry, selection/detail, return; supported URL behavior if relevant>
commands_and_scope: <action label, affected query/content, reset/refresh meaning>
bindings: <query contract, exact workbook/tab/field IDs or unresolved>
context_to_preserve: <filters, selected identity, sorting, focus, relevant scroll position>
adaptation: <when space is insufficient, what rearranges, what remains available>
result_transitions: <loading, latest result, selection invalidation, stale/partial evidence>
recovery_and_help: <state-specific message, safe next action, definition/help location>
capability_gaps: <unverified or unsupported behavior and affected scope>
verification: <scenario, artifact version, expected observation, actual evidence/status>
```

## Synthetic worked example: exceptions to evidence

Continue the inventory example in the ideation playbook. All names, records, and values here are invented for design exploration; KPI acceptance and native implementation remain pending.

```text
Exceptions [destination]
  Warehouse scope [filter] + active scope summary
  Comparable item list [item identity, available units, evidence timestamp]
    Select item → Item evidence [detail destination]
      Show metric definition [contextual help]
      Back to exceptions → prior list context
  Clear warehouse filter [scope action]
  Refresh results [query action, capability to verify]
```

**Why this map:** selecting an item reveals evidence; it does not imply changing inventory. Metric definitions belong next to their use, and their status remains visible if unresolved. “Refresh results” is a proposed interaction, not proof of a supported native command. The BI engineer supplies the query contract and exact bindings; engineering supplies verified runtime behavior. No export, purchasing, or writeback operation is implied.

**Wide presentation:** show the list and selected detail together if content remains readable. **Narrow presentation:** show the current detail with a labeled return to the list; keep the warehouse scope understandable. Choose the transition based on content fit, long labels, and text zoom rather than copying an Android breakpoint or an iOS device size.

**Context invariants:** resizing alone must not reset the selected item or filters. Returning should preserve the meaningful list state and focus, where supported. If the query contract confirms that a deliberate filter change excludes the selected item, clear its detail and explain that it is outside the current scope; do not leave old detail appearing current. Absence from a partial, paginated or limited result does not prove exclusion. When membership is unknown, remove any claim that old detail is current and show a neutral “Selected item not confirmed in these results” state; verify membership through a supported query if available. Retain old values only under the authorized, clearly labeled stale-data policy. If the selected item remains, reconcile by stable identity rather than row position. Treat changes in permissions as access changes, never as ordinary filter-empty results; protect identifiers as well as values.

**Example test:** choose synthetic item `ITEM-17`, narrow the viewport, open its definition, return to the list, then change warehouse scope with confirmed exclusion of that item. Expected design behavior: no unexplained selection loss during resizing; confirmed exclusion invalidates the old selection. Repeat with incomplete results that omit the item: show unconfirmed membership rather than asserting exclusion. A permission-change variant must protect restricted content. These are test scenarios, not test results. Independent QA records actual observations using [usability testing](../../omni-qa-analyst/references/usability-testing.md).

## Dense analysis without losing meaning

Keep the comparison columns needed for the task together; use aligned values, explicit units, and readable labels. Do not turn every table row into a large card when that impairs comparison. On constrained screens, disclose lower-priority detail or use a labeled, keyboard-operable scroll region; do not silently drop critical fields. State whether sorting/filtering applies to the whole governed result or only a loaded subset. A partial result cannot support a complete-population total or ranking claim.

Specify when filters apply, which regions they affect, what reset restores, and which values remain visible while a new result is pending. Distinguish selection from filter scope. The app engineer owns request/result coordination; a late result must not be presented under a newer scope. A designer must not repair missing metric logic in client-side calculations. Route the binding or semantic gap to the BI engineer and [backend handoff](../../omni-backend-handoff/SKILL.md).

## Recovery and help at the point of need

| Situation | Synthetic copy / behavior proposal | Annotation |
| --- | --- | --- |
| No rows match the current filter | “No items match these filters.” Offer a supported clear-filter action and show the active scope. | Different from no data existing or insufficient access. Avoid arbitrary default changes. |
| Query fails | “Results could not be loaded.” Keep the selected scope visible; offer a verified retry path. | Do not display zero inventory or silently broaden access. Retain old data only if authorized and clearly marked stale. |
| Result is partial | “Showing a partial result.” Explain the known limitation in plain language and the available next step. | Do not invent a total row count, coverage percentage, or completion time. |
| User lacks permission | Use the approved access message and support path. | No hidden counts, names, or security-sensitive error details; do not simulate access with a UI filter. |
| Definition is unfamiliar or unresolved | Place concise definition help near the measure; label a pending definition visibly. | Help must be reachable without hover alone. A tutorial cannot substitute for an accepted metric. |

Keep help optional and recoverable when it teaches use; do not put mandatory tours in front of routine analysis. Required warnings or consent retain their real workflow rules. Help links, external navigation, copy actions, and dismiss-state persistence require target support; a blocked capability is not permission to widen app policy. Use [design QA](../../omni-design-systems/references/design-qa.md) for rendered, keyboard, accessibility, and data-state checks. Usability, numerical correctness, native execution, effective access, and business acceptance remain separate evidence.

## Source basis and applicability

Checked **2026-10-21**. These sources inform the pattern choices; the cards and analytical examples are this package's recommendations.

| Source / evidence type | Transferable guidance and platform boundary |
| --- | --- |
| [Apple: Design foundations from idea to interface, WWDC25](https://developer.apple.com/videos/play/wwdc2025/359/) — official illustrative case study / video transcript | Organize essential information and distinguish navigation from contextual actions. Its native tab bars, toolbars, icons, and materials are not prescribed for Omni. |
| [Apple: Explore navigation design for iOS, WWDC22](https://developer.apple.com/videos/play/wwdc2022/10001/) — official video transcript | Clear grouping and labels support orientation; redundant commands can confuse structure. Transfer the reasoning rather than all iOS placement rules. |
| [Apple: Elevate the design of your iPad app, WWDC25](https://developer.apple.com/videos/play/wwdc2025/208/) — official platform guidance / video transcript | Adapt to available space without destructive layout changes. Native window controls and pointer treatments are not web requirements. |
| [Google: Canonical layouts](https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts?hl=en) — official Android documentation | List/detail and supporting panes provide useful relationships across available widths. Preserve task context; do not import Compose APIs, native breakpoints, or their release labels as Omni functionality. |
| [Microsoft: Fluent 2 onboarding](https://fluent2.microsoft.design/onboarding/) — official design-system guidance | Contextual, optional teaching and explanatory empty states help people proceed. Apply that purpose without requiring Fluent components or assuming unsupported actions. |

Use customer-authorized assets and the accepted theme contract. These references grant no permission to redistribute vendor fonts, symbols, artwork, or native design resources.
