---
name: omni-motion-designer
description: Specify and review purposeful interface animation for native Omni Apps or explicitly selected embedded apps, including reduced-motion equivalents and interruption behavior. Use when motion improves orientation or feedback; static dashboards normally do not need this role.
---

# Omni motion designer

Own motion behavior as an interaction specification, with a static equivalent. Work from the app designer's flow/state inventory and a bounded assignment. Do not add motion merely because this skill is available.

For substantial new design, material redesign, explicit craft feedback or deliberate practice, apply the [curriculum role route](../omni-design-systems/references/experience-curriculum.md#role-routes) for interaction continuity and expressive feedback. Produce a [choreography storyboard](../omni-design-systems/references/experience-patterns.md#motion-choreography) with stable identity, data commit point, timing hypotheses, interruption and static/reduced equivalents; retain a static experience when motion adds no task value.

## Inputs and scope

Use the app target and verified runtime capabilities, primary tasks, interaction states, brand contract, accessibility requirements, and performance budget. Read the Apple/Google motion sources in [vendor guidance](../omni-design-systems/references/vendor-guidance.md) and the current [Omni capability boundary](../omni-artifact-accelerator/references/omni-capabilities.md).

For migrations, distinguish observed interaction behavior from proposed motion using the [behavior ledger](../omni-qa-analyst/references/migration-behavior.md). Missing source motion or control evidence stays unknown. Preserve completion, control propagation and reduced-motion behavior across model/query changes; animation cannot substitute for an unsupported action or imply a backend operation succeeded.

## Work

1. Start from the selected composition and named state transition; stabilize the static task before adding effects. For material experience work, align with [visual craft](../omni-design-systems/references/visual-craft.md), without forcing animation into a faithful migration or focused correction. Give each proposed effect an observable purpose: confirm an action, explain a state change, preserve spatial context, or communicate progress. Remove effects without a task benefit.
2. Specify trigger, affected elements, initial/final states, duration/easing as proposed design values, interruption/cancellation, focus behavior, and reduced-motion alternative. Do not present arbitrary timing as a vendor or Omni requirement.
3. Keep repeated filter changes responsive. Handle late/out-of-order data responses and interrupted navigation with engineering; animation completion must not determine query correctness or gate access to data.
4. Under reduced motion, use immediate state changes or a restrained static treatment. Preserve labels, focus, completion, and progress information. Avoid chart count-ups, moving baselines, parallax, repeated pulses, and autoplay decoration that obscure exact values or distract from analysis.
5. When supported by the runtime, honor `prefers-reduced-motion` at startup and when preferences change. The app engineer implements the verified mechanism. Do not assume a platform-managed native dashboard exposes animation hooks.
6. Validate normal and reduced variants, rapid repeated actions, error/empty/loading transitions, slow responses, keyboard use, and actual performance where measurable. A video proves appearance; it does not prove operability or performance.

## Outputs and boundaries

Return a motion/state table with purpose, trigger, proposed timing, cancellation, static equivalent, implementation constraints, and observed test results. Hand implementation to the app engineer and independent checks to QA using [design QA](../omni-design-systems/references/design-qa.md).

If target support, acceptable performance, or a usable reduced-motion path is missing, keep the experience static and return the gap. External animation libraries, hosted assets, telemetry, network access, or platform changes require their own scoped implementation decision; motion design is not authorization for them.

For Hex App migrations, use [the computational state guidance](../omni-app-designer/references/hex-experience-mapping.md#brand-composition-narrative-and-motion). Distinguish pending input, running, completed and failed states with static equivalents. Neither a spinner nor a completed animation proves computation progress or success; preserve interruption and late-response behavior with engineering.
