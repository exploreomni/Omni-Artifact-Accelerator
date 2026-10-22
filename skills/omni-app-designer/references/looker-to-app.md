# Looker to a native Omni App

Use the App lane when the selected outcome is a guided analyst task, a focused workflow, or a richer interaction than the original dashboard. Do not require an intermediate dashboard. When both surfaces are selected, design and validate separate native documents and retain a source-to-surface mapping for each.

Start with the original Looker dashboard definition, content, dashboard filters/listeners, repeated placements, tabs, query/Look/merged-query dependencies, custom visual behavior and supplied state captures. Preserve immutable source asset IDs. Repeated placements remain independent layout and query-result obligations even when they refer to the same query. Text, images and buttons remain content or interaction obligations, not fabricated numeric queries.

Choose the task flow before styling: the decision to support, what the viewer must see first, the next meaningful action, what a control changes, and how the viewer returns to a known state. Reframe chart grids only when the reviewed intent supports it. Record changed navigation, grouping, annotation, defaults and interactions as adaptations with independent expectations. A screenshot is useful visual evidence but cannot establish filter, drill, access or metric equivalence.

Build against a current query-backed native App starter and its reviewed workbook queries. Hand off query and field semantics to the BI engineer; changes to warehouse/model behavior belong to the selected Data Model Accelerator route. The App engineer preserves the inspected runtime and exact query bindings through the [native App contract](../../omni-app-engineer/references/native-app-contract.md). No invented browser SDK, disconnected mock page, or unbound HTML chart counts as the target implementation.

For each screen or component, specify:

- Source assets and current Omni query keys/Topic fields; query-bearing placements must not disappear from the denominator.
- Intended decision, visual hierarchy, chart or content representation, labels and reviewed adaptations.
- Initial, loading, populated, empty, error, restricted and stale states; stable layout while loading and useful recovery text.
- Filter semantics, listener scope and exclusions, defaults, multi-select/null handling, reset, tabs and drill/navigation behavior.
- Keyboard focus order, names/labels, contrast, focus visibility, responsive/narrow behavior and reduced-motion equivalents.
- Independent numeric, access, interaction, visual and performance cases, including unsupported or deferred behaviors.

Retain compatible inspected controls only through exact field/query/runtime bindings. A source filter that has no supported current target implementation stays unresolved; do not mark it migrated by placing its label beside a chart. Merged results, custom visualizations, extension behavior, dynamic calculations and unsupported control semantics need an explicit implementation decision and evidence rather than silent approximation.

Apply the engagement brand contract consistently: ask for the company website URL, inspect permitted logo/theme/font references, record asset provenance and reuse rights, and preserve approved semantic colors. Use the shared design-system guidance for spacing, type, focus and feedback. Motion should explain state or orientation and remain optional under reduced motion; decorative animation is not a substitute for a usable loading or error state.

Review at representative desktop and narrow widths, then independently exercise the named App draft with the intended personas and states. The draft readback confirms persisted content; it does not confirm that JavaScript ran, data was correct, permissions were equivalent, or the customer accepted the experience. For a `both` migration, retain separate App and dashboard previews, state evidence, query comparisons and surface returns.
