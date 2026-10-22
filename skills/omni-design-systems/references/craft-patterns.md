# Applied craft pattern cards

These are package recommendations using the previously reviewed sources in [vendor guidance](vendor-guidance.md), checked **2026-10-21**. They transfer principles, not proprietary assets, native OS dimensions, SDKs or promised Omni features. Refresh a feature-sensitive mapping before implementation. The [original HTML specimen](../assets/craft-specimen.html) uses explicitly synthetic service-request data and illustrates two different tasks; it is not a native Omni screenshot or usability result.

## Principal result with supporting evidence

- **Task / use:** a viewer needs the scale of a situation, then its composition. Give one result visual priority; group supporting counts and a useful comparison. Avoid forcing one hero when the real task requires equally weighted peer comparison.
- **Example:** synthetic open requests =42; assigned17 + unassigned25 =42; queues North18 + South16 + West8 =42. Large42 plus subordinate breakdown is an overview. Parallel queue rows are the better working surface when choosing a queue. Neither fixture has an accepted SLA or red/green status.
- **Why:** size, proximity and space distinguish the primary question from its supporting evidence without adding invented narrative.
- **Sources / evidence:** [Apple Charts](https://developer.apple.com/design/human-interface-guidelines/charts), HIG documentation; [Fluent layout](https://fluent2.microsoft.design/layout), design-system documentation; [Power BI dashboard design](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips), product guidance. Composition and numbers are our adaptation.
- **Omni mapping / limits:** verify native metric/text/tile geometry and number/axis formatting. If a composite background is unsupported, preserve unequal emphasis and grouping with supported native tiles. No HTML injection into a dashboard.
- **Verification:** capture opening viewport and chart detail; identify primary result, scope and evidence. Reconcile sums independently; evaluate interpretation separately from appearance.

## Persistent selection with useful detail

- **Task / use:** compare objects, select one, inspect evidence, return. Use a persistent list on wide screens and deliberate list/detail navigation on narrow screens. Avoid when selection would conceal an essential simultaneous comparison.
- **Example:** select synthetic North18, then see assigned7 and unassigned11, plus the scoped record list or an additional verified breakdown. Repeating only “North18” in a drawer adds no information. Preserve the same queue ID, sort, selection and meaningful focus on return.
- **Sources / evidence:** [Google canonical layouts](https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts), Android documentation; [Apple iPad design](https://developer.apple.com/videos/play/wwdc2025/208/), official platform session; [Carbon tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines), component guidelines. Transfer relationships and context preservation, not platform controls.
- **Omni mapping / limits:** native App query/selection contract is required; native dashboard drill must be separately verified. Detail cannot fabricate a query or replace a required migration action.
- **Verification:** select/sort/filter/return with long labels and no matching rows; retain context, restore focus, distinguish current results from pending inputs. Compare actual wide/narrow captures and changed-state behavior.

## Contextual controls and truthful transitions

- **Task / use:** a viewer changes scope and needs to know which results are current. Put controls near affected content; keep reset available and refresh secondary to the task. Avoid scattering duplicate controls without clear scope.
- **Example:** selecting South shows pending South while previous North evidence remains explicitly labeled or is hidden; only the matching completed result becomes current. Error is not zero. Reset restores documented scope and announces completion only when applied.
- **Sources / evidence:** [Apple UI tips](https://developer.apple.com/design/tips/), developer article; [Fluent onboarding](https://fluent2.microsoft.design/onboarding/), contextual-help pattern; [Apple Motion](https://developer.apple.com/design/human-interface-guidelines/motion), HIG documentation; [Google meaningful motion](https://design.google/library/making-motion-meaningful), design article. The analytical state rules are our adaptation.
- **Omni mapping / limits:** inspect actual query bridge and cancellation/state contract. Static feedback is sufficient; neither a spinner nor transition completion establishes query success. Document unavailable runtime behavior.
- **Verification:** rapid changes, late/error responses, reset, focus and reduced motion; local simulation remains separate from native observation.
