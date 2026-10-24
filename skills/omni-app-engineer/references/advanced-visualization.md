# Advanced visualization, as a bounded engineering assignment

Use when a selected requirement needs custom projection, camera interaction, an entity dossier, a calendar or other behavior beyond ordinary charts. App engineering owns implementation and lifecycle. Actual object/environment geometry, materials and stable spatial identity can use the optional [3D modeler](../../omni-3d-modeler/SKILL.md) and [spatial integration contract](spatial-integration.md). A custom chart alone does not need that role. Do not add a scene, animation, image or extra destination to faithful migration or simple work without a selected requirement.

## Contract before geometry

Consume the selected intent/experience brief and analyst's analytical coverage. Identify the requirement and `delivery` owner, observable behavior, destinations, capabilities and explicitly pinned dependency files. The component contract should resolve:

| Boundary | Concrete content |
| --- | --- |
| Evidence | Query/field identities, grain, units, source population/time, completeness, valid comparisons, nulls, provenance and which claims remain unsupported. |
| Meaning | Every coordinate, dimension, size, color and connector: measured, derived by a named reviewed formula, or decorative. No fabricated geography, trajectory, duration, causality or interpolation. |
| State | Domain IDs separate from display labels; selected/filter generation, pending/applied state, empty/partial/error/restricted/stale outcomes, drill/return and reset scope. |
| Geometry | Coordinate system, fixed measured/schematic bounds, camera limits, available width **and height**, label/mark budget, first-view priorities and intentional scroll. |
| Interaction | Public methods/events, opt-in gestures if useful, keyboard/range alternatives, focus/return behavior and Escape. Page scroll remains normal before explicit scene engagement. |
| Ownership | Owned DOM region/style namespace, authoritative upstream data, component-local view/camera state, dependencies and cleanup. No rewriting parent business logic. |
| Qualification | Proposed performance budget and measurement method, reduced/static equivalent, local tests versus actual rendered/native evidence and known limits. |

Use an exact text/table companion for marks that are too small, overlapping or perspective-distorted. A camera changes the view, never the metric. Fit against stable declared bounds; filtering to one item should not silently change the apparent scale. Refit deliberately on a viewport change. If zoom/pan can move evidence offscreen, expose reset and a recoverable overview. Decorative scenery may crop; required data labels and controls need a readable route.

For layered scenes, qualify each layer's coordinate frame independently: origin, axes/direction, units, raw versus already-normalized values, transformation order and meaningful landmarks. In-bounds coordinates can still be combined incorrectly. Pin an independent landmark expectation for a transformed case and an unchanged case; do not validate only the renderer's own formula. Apply any normalization once, then project markers, guides and paths in the same frame. Decorative depth does not authorize measured-height or physical-model claims.

Resolve initial focus from source roles when the task needs it, with a neutral fallback when the role is unknown. Camera presets and direct gestures are engagement choices; preserve keyboard/static access, an explicit entry/exit for captured gestures and reset. Neither a more elaborate scene nor additional controls is required when it obscures the evidence.

Compute a weighted rate from aligned numerators and denominators, never the average of displayed percentages. A cohort with missing numerator does not become zero or disappear from the coverage statement. Respect governed non-additive measures: this example's count arithmetic cannot substitute for distinct counts, medians or source-specific business definitions.

For reusable selection/return, per-entity choices, recorded-time progression and event navigation, use the separate [behavior controllers](experience-behaviors.md). They expose state and callbacks without supplying markup, domain rules or colors. The existing projection and camera utilities below remain available; recorded time and a chosen projection do not require a spatial renderer. [Assembly](portable-assembly.md) can combine the selected components and engagement renderer.

## Composable synthetic example

[`evidence-workbench.html`](../assets/evidence-workbench.html) and [`experience_components.js`](../scripts/experience_components.js) form an offline example. Keep their `assets/` and `scripts/` relationship when copying locally, or incorporate the reviewed helper into the real build with explicit script order. The example is not a deployable native App and contains no Omni bridge, remote assets, media or fetch. Its global `OAAWorkbenchExample.destroy()` cancels frames and removes listeners. Copy only the pieces the selected task needs.

The fictional sampling-station fixture demonstrates four composable pieces:

1. **Schematic scene + exact dossier.** Positions are explicitly decorative grid coordinates. Select Aster/Beryl/Cedar by accessible table buttons, focus the exact detail, and return to the same button without changing population or camera. Color is supplemented by the word Unknown. Front/angled presets and a keyboard range expose rotation; there is no hidden drag or scroll interception.
2. **Weighted evidence and peers.** Aster has 72 passed of 90 eligible (80%); Beryl 9 of 10 (90%); Cedar 20 eligible with unknown passed. Measured subset is 81/100 = **81%**, not the unweighted 85%. Measured denominator coverage is 100/120 = **83.33%**. The full-population rate is unknown. Beryl's other measured peers are 72/90 = 80%, while their full rate remains unknown. These are independently checkable synthetic expectations, not user research.
3. **Month calendar.** Real month navigation, weekday placement, leap-year handling and exact date labels use UTC date-only arithmetic. Aster/Beryl appointments are separate fixture records, not inferred from outcomes. The calendar does not label unseen dates as complete source data. For a live schedule, add the separately qualified source/timezone/refresh contract.
4. **Media state companion.** Simulated frame load remains loading; simulated denial exposes blocked state and a fallback explanation. No fake poster or invented URL is presented as actual playback. Use [native capability checks](native-capability-checks.md) for a real provider.

`projectScene(points,{width,height,yaw,tilt,padding,bounds})` is bounded **orthographic 2.5D**, not a 3D engine or physical model. Points are `{id,x,y}`, bounds `{xMin,xMax,yMin,yMax}`; coordinates and camera values must be finite. It returns screen positions under stable bounds, rejects duplicate/out-of-bounds IDs and limits the point count to 1,000. The example is qualified locally with three marks only; the guard is not a performance claim for 1,000 labels. Prefer aggregation or a readable table when dense overlap defeats the task.

`weightedRate(rows)` expects `{id,eligible,passed}` with distinct IDs and nonnegative safe-integer counts; passed may be null. It returns eligible/measuredEligible/passed/missingIds/rate/measuredRate/coverage. Unknowns and zero denominators produce null rates. It is a synthetic count-pattern utility, not a semantic-layer replacement. `monthCells(year,month)` returns Sunday-first ISO date strings and padding nulls for years 1900–2200; use a separately selected locale/week-start policy where needed.

## Motion and lifecycle

Read [scene choreography](../../omni-motion-designer/references/scene-choreography.md) for camera, selection and interruption. `createCameraMotion({frame,cancelFrame,now,onFrame,durationMs=180})` takes injected animation-clock functions and returns `move(from,to,reducedMotion)`, `cancel()` and `dispose()`. It animates **camera properties only**. A new move cancels the previous one, reduced motion commits the final camera immediately, and disposal cancels outstanding work. The 180 ms default is a sample hypothesis, not a vendor recommendation; no query or exact value waits for it. The example listens for preference changes and tears down on page hide. A production route must also call cleanup on component unmount and implement its visibility/resume policy.

## Meaningful verification and remaining gaps

Use the focused package check:

```sh
python -m unittest discover -s tests -p test_experience_components.py -v
```

It executes the actual helper and assembled classic scripts under a minimal DOM double: exact input keys/null/zero, current-generation commits, missingness, stable projection, interruption, selection/return, calendar and teardown. It does not render pixels, emulate layout/focus scrolling, test a screen reader, measure native performance or establish host/provider access.

For an actual selected component, inspect one representative narrow/short and normal working frame, the exact-value path, rapid interruption and return, plus the affected native boundary when permitted. Record actual sizes, candidate hash and concrete corrections. No exhaustive device matrix or aesthetic score is implied. If rendered/native inspection is prohibited, keep that lane unobserved and do not call this example's local checks visual acceptance.
