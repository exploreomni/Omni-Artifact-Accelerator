# Motion for evidence-bearing components

Use when the selected experience has camera, spatial, drill/return or media transitions. The App engineer owns projection/rendering/lifecycle; the analyst owns what the evidence can claim. Apply this alongside the selected experience brief and [advanced visualization contract](../../omni-app-engineer/references/advanced-visualization.md). Static dashboards and focused edits do not inherit an animation requirement.

## Small storyboard: inspect a sampling station

The [synthetic workbench](../../omni-app-engineer/assets/evidence-workbench.html) is a reusable implementation example, not a customer template. Its three schematic positions are decorative; all exact counts stay in the table/dossier.

| Transition | Meaning and commit point | Motion hypothesis | Interruption and static equivalent |
| --- | --- | --- | --- |
| Select station | Commit the original station ID and exact detail immediately; focus the detail heading. | A static selected mark is sufficient. Do not count up, morph the measured value or infer a route between stations. | A later selection replaces the earlier one. Back returns focus to the originating button; selection and population persist. |
| Camera preset | Change the view of the same evidence, not its scope. | Example: 180 ms ease-out on yaw/tilt, fitted to stable declared bounds. | New input starts from the currently displayed camera and cancels prior frames. Reduced motion jumps immediately to the final view. |
| Range adjustment | Expose direct camera control using normal keyboard input. | Immediate feedback; no lagging tween behind continuous input. | Escape resets the camera and focuses Reset. No capture of page scrolling. Drag/zoom, if separately selected, needs explicit engagement/exit and equivalent controls. |
| Filter/refresh | Pending state is not applied evidence. | Static loading text is sufficient; animation cannot imply progress or completion. | Invalidate earlier generations. Late data cannot overwrite the current state. Clear or explicitly label stale values according to the selected contract. |
| Media unavailable | Explain a provider/host limitation and preserve a useful path. | No perpetual spinner or decorative fake player. | Stop/pause through the qualified provider mechanism, then expose the selected fallback. A frame load event cannot trigger a playback-success transition. |

The sample duration/easing is an implementation hypothesis. Retain user-selected expressive requirements, but choose motion proportional to the task. No mandatory intro, parallax, multi-screen structure or camera effect follows from this guide.

## Lifecycle handoff

Specify the state owner, trigger, visible start/end, semantic commit, proposed timing, interruption priority, focus/return, reduced-motion change handling, hidden-page behavior and cleanup. Include the relevant width and height where travel or clipping matters. Ask engineering for the current view state when interrupting; do not animate from a remembered start that causes a jump.

Use a single finite animation loop for the selected transition; avoid per-frame query work and unnecessary DOM rebuilds for a large scene. Cancel frames/listeners/timers on unmount and pause media through an actual supported control. Under reduced motion, remove travel while retaining selection, status and exact information. A query response, not the end of an animation, commits governed results.

Propose a measured budget for the representative dataset/device, then record actual observations when allowed. Source counts, theoretical frame rates and a smooth local fixture are not native performance evidence. Rehearse one rapid reversal plus static/reduced behavior; add more cases only for changed or unresolved behavior. Keep source-only, rendered, native, accessibility and user-acceptance results distinct.
