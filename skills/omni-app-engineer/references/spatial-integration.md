# Optional spatial integration

Use only when the selected task benefits from a model, assembly or environment.
The [modeler](../../omni-3d-modeler/SKILL.md) owns geometry; the App engineer owns
the renderer, native bridge, lifecycle and non-canvas alternative. Ordinary
dashboards retain their native chart/filter routes. Read the shared
[package-use policy](../../omni-artifact-accelerator/references/dependency-policy.md).

## Select the execution route

Use the smallest route that fits the task:

1. **Native App procedural scene:** author original bounded geometry and animation with reviewed inline HTML/JavaScript and supported browser primitives. This route can be prepared without a separate modeling VM or an external engine. Qualify the exact target's rendering capabilities, data callbacks, performance, recovery and resource settings before claiming native delivery. Use governed query results and stable IDs, with a non-canvas information path. Inline authored code still needs review; do not evaluate supplied strings, import arbitrary assets or weaken host policies.
2. **Approved library or supplied asset:** record exact library/asset bytes, source/rights, dependency closure and explicit package-use approval. Confirm the native host's supported loading path; a CDN allowlist is not package vetting or approval. Reject unsupported imports instead of disguising them as inline code.
3. **Off-browser model compilation:** use the optional fixed compiler, isolated worker, independent validator and promotion contract below when editable model assets or external processing are required. That harness remains disabled until its host gate is qualified. This gate does not apply to every authored native App scene.

Official documentation checked 2026-10-23 describes [Apps as HTML/JavaScript interfaces in a sandboxed iframe](https://docs.omni.co/visualize-present/apps#security), with governed query access, and [per-App resource controls](https://docs.omni.co/visualize-present/apps/settings) beneath organization policy. This supports selecting a native rendering route; it does not establish an arbitrary 3D library, decoder, WebGL extension or GPU budget. Inspect the actual target and exact code. Restricted resource settings and this package's narrower initial-construction profile remain in force.

## Optional compiler source and qualification boundary

The repository's optional `harness/` contains an original SceneSpec compiler,
narrow uncompressed/untextured GLB checker and first-party WebGL viewer. It is
separate from the installed skills and is not automatically acquired or loaded.
No external engine, decoder, custom shader, remote model URL or script belongs
in a scene. The viewer is a basic diffuse renderer, not a photorealistic engine.
Off-browser compiler activation and customer asset processing remain blocked until the host
approval and isolation gates are qualified. Source/unit checks do not qualify
the browser, GPU, Omni host or visual craft.

The portable [spatial controller](../scripts/spatial_controller.js) consumes an
already selected renderer and reviewed data contract. It has no network,
storage, query execution or asset promotion authority. It keeps camera and
selection across ordinary query refresh, rejects unknown identities, ignores
superseded results and clears values for restricted/error/empty states.

## Binding contract

For the separately versioned native-scene-v1 route, use the [native scene framework](native-scene-framework.md), its instance-owned session and optional data bridge. Only analytical entities require bindings; scene-only illustration has no query contract. The all-entity binding rule below belongs to the existing spatial controller and compiler viewer; pass only the analytical subset for a mixed native scene. Do not widen the strict GLB profile to fit native texture recipes.

For an authored native scene, retain its source/parameter hashes and reviewed identity mapping; no compiled GLB or worker promotion receipt is required. The promoted-asset and GLB requirements below apply when the compiler/asset route is selected. All routes require actual data, lifecycle, access and visual qualification.

Record these in existing selected intent/runtime dependencies, with exact hashes:

- Promoted asset and canonical SceneSpec, asset provenance and fidelity, toolchain
  version/hash, validated profile and independent validation evidence. A worker's
  manifest is not proof that a trusted host authorized promotion.
- Stable geometry entity IDs, entity labels and named view IDs. The renderer
  validates its own GLB identity; do not infer identity from mesh/row order.
- Complete one-to-one `bindings: [{entityId, dataKey}]` and explicit numeric
  `metrics` keys. This first adapter does not aggregate or support many-to-many
  mapping. Resolve grain/joins in governed queries and analyst review first.
- Exact draft/query IDs, observed native callback shape, effective access,
  freshness expectations and partial/missing data semantics. Unknown mappings
  need a corrected contract, not a best-effort label match.

The data analyst defines units, denominator, aggregation and independent expected
values. Route missing semantic fields through the existing backend handoff.
Keep warehouse credentials and sensitive rows out of geometry and model workers.

## Compiler viewer integration sequence

This sequence applies to the repository's optional GLB viewer. For an authored
native scene, implement the same selection, query-state, recovery and disposal
responsibilities through its reviewed renderer contract; do not invent a GLB or
promotion requirement for that route.

1. Confirm host authorization for exact viewer and validated asset bytes. The
   current source-only harness cannot produce a host promotion receipt.
2. Mount the renderer with `canvas`, `glb` bytes, its matching `manifest`,
   `onSelect(id)` and `onStatus(event)`. It exposes `entities`, `views`,
   `setSelection`, `setCamera`, `resize` and `dispose`. Wire user selection to the
   controller after initialization; map documented viewer statuses explicitly.
3. Create `OAASpatialController.create({entities, views, bindings, metrics,
   renderer, onState, reducedMotion})`. Render labels using `textContent`, never
   HTML. Render exact numeric values and missing states in semantic DOM.
4. Each authorized query cycle calls `begin()`; retain its returned token.
   Resolve that token with `{status, rows:[{key, values}], asOf}`. Acceptable
   outcomes are `ready`, `empty`, `restricted`, `error` or `stale`. Empty,
   restricted and error outcomes cannot contain rows. Null metrics stay null.
   Rejected malformed results leave state unchanged; the bridge must catch the
   error and call `invalidate('error')` so loading cannot remain indefinitely.
5. Bind semantic buttons/selects/list controls to `select`, `showView`, `reset`,
   `stepTour` and `stopTour`. Tours are explicit steps, without automatic motion.
   The current renderer changes named viewpoints immediately. Additional motion
   needs a motion contract, cancellation, reduced-motion behavior and validation.
6. Call `resize()` on available-space changes. On context loss expose the exact
   information outside the canvas, dispose and remount only through a deliberate
   recovery path. On navigation/unmount call `dispose()` once; cancel pending
   query subscriptions and host observers independently.

An entity list and companion values must remain usable when WebGL is unavailable.
Supply keyboard names, visible focus, selection indication, touch controls,
loading/error messages and a reset/return path. Do not encode business meaning
only with lighting, camera position, depth or color.

## Native constraints and evidence

The existing initial-construction adapter caps assembled HTML at 2 MiB and
rejects declared external resources. This is that adapter's limit, not a global
Omni limit. Include scripts, markup, CSS and base64 overhead in its budget.
Asset acceptance at 16 MiB in the isolated workload is **not** permission to
embed a 16 MiB model in that route. Measure the exact assembled candidate.

Inspect official/current target capabilities before choosing a resource path.
Keep locked settings and approved domains intact. If bytes or resource policy do
not fit, reduce the scene or prepare a separately authorized supported route.
Never claim an invented SDK, CDN exception or rewritten host setting is supported.

Pin checks to source, assembled bytes, renderer, model and bindings. A changed
mapping invalidates numerical/mapping evidence; a changed scene or renderer
invalidates affected visual/interaction/performance evidence. Retain unrelated
evidence with its original scope. Native callbacks, access, GPU performance,
responsive craft and user acceptance stay `not_run` until actually observed.
