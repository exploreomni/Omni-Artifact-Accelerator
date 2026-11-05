# 4. Choose the experience

[Learning guide](README.md) · [Previous: data and story](03-data-and-story.md) · [Next: review](05-review.md)

**Outcome:** your chosen design expresses the intended task and quality bar before the product is coded.

## D — Answer a short, informed interview

The product owner uses the analysis and story to ask only for missing decisions. You can supply preferences earlier; they should be retained rather than requested again. Routine styling details can be delegated within your stated constraints.

| Topic | A useful answer explains |
| --- | --- |
| Outcome | The action a user should take, and how first and returning visits should work |
| Experience and quality | What “polished” or “immersive” means to you: reference qualities to borrow or avoid, information density, content depth and interaction ambition |
| Brand | Official website, approved logo/imagery or authorization to source them, font constraints and whether a logo is wanted |
| Visual exploration | Whether the task is comparison, tracking, spatial inspection, replay, storytelling or a combination |
| Devices and access | Phone, laptop or wide-screen needs; usable content area when known; keyboard and reduced-motion needs |
| Refresh and caching | Whether to retain existing Omni caching or request a specific refresh/expiry behavior |
| Delivery | Native surface, intended readers, export needs and permitted preview/publication actions |

A website URL alone does not choose a logo. An agent should retain the exact selected asset, its provenance and placement. Branding permission also does not authorize renaming source entities or relabeling demo data; those are separate decisions that must preserve original IDs and arithmetic.

## Make visual ambition explicit without prescribing a template

For comparison or tracking, expect a follow-up about treatment: precise flat charts, dimensional/futuristic treatment, or a task-appropriate blend. The choice should preserve readable scales, exact values, accessible alternatives and useful interaction.

For spatial exploration, explain what geometry represents and what users should learn by moving through it. A decorative scene needs no invented metrics. A faithful building or object model needs appropriate reference evidence. A 3D preference does not approve a renderer, asset import or dependency installation.

You can say:

> Keep exact comparison values easy to read. Explore an expressive visual treatment if it improves the investigation, and show a simpler alternative. Make the working views as polished as the opening. Avoid a fixed grid of generic tiles unless it genuinely serves this task.

The experience promise records the outcome and quality you agreed on. It is shared with specialists and reviewed across the entire journey, so a striking opening cannot stand in for unfinished detail screens.

## Choose refresh behavior deliberately

The starting policy is to preserve existing Omni caching. Automatic polling, bypassing query caches or expiring client-held results are opt-in decisions, not package defaults. You might choose:

> Keep the existing Omni cache policy, show the reporting period and data-as-of information, and let me rerun manually. Do not add automatic refresh or a client timeout.

If you need something else, state the expected cadence and user behavior. The agent should explain relevant source freshness, cost and runtime constraints before implementing it.

## E — Compare three concrete products

All three concepts must preserve the same accepted analytical scope and quality ambition. They should differ meaningfully in composition, journey or interaction rather than presenting one polished option against two weak ones.

Expect representative visual artifacts with enough behavior detail to judge the experience. Prose pitches, ASCII sketches or color tokens alone are insufficient. Source-only visual specimens must be labeled unrendered when rendering has not actually occurred.

Compare the concepts on:

1. How quickly the intended user can recognize and complete the main task.
2. Whether supporting comparisons, detail and return paths are clear.
3. Whether the brand and visual treatment feel deliberate throughout the product.
4. Whether the design can work with the actual data, runtime, devices and accessibility needs.

Reply with the concept identifier and any bounded changes. If you want to combine directions, have the agent resolve the hybrid and retain your actual decision against the presented options; it must not invent your selection or treat an earlier preference as one.

After selection, the designers resolve layout, controls, navigation, states, responsive behavior, assets and appropriate motion before implementation. Selecting a concept permits the normal local design/build workflow after its checks; it does not authorize installation, native writes or publication.

**Checkpoint:** you can describe the chosen experience, its main user journey and what makes it meet your quality bar. The agent can point to your actual selection and the resolved design rather than guessing what you approved.
