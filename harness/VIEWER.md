# Original narrow WebGL viewer

`viewer.js` is first-party JavaScript with fixed first-party shaders and no dependencies, imports, network requests or dynamic code evaluation. It renders the compiler's strict `oaa-glb-untextured-v1` profile using browser WebGL 1. It is an optional renderer source, not an installed service, isolation runner, general glTF loader or enterprise renderer.

No browser or native Omni rendering was performed during this implementation. Node tests exercise synthetic parser/math cases and the actual mount API through small WebGL/canvas doubles. Those checks cannot establish GPU compatibility, visual craft, accessibility, performance, native support or security isolation.

## Host contract

Load the reviewed script only under the project's [dependency/activation policy](../skills/omni-artifact-accelerator/references/dependency-policy.md). It exposes `OAA3DViewer` in a browser and first-party CommonJS exports for bounded local tests. It never acquires a package or model. The host supplies already promoted **bytes**, not a URL:

```js
const viewer = OAA3DViewer.mount({
  canvas,
  glb: promotedBytes,
  manifest: compilerManifest,
  onSelect: entityId => hostSelectionChanged(entityId),
  onStatus: state => hostRendererStatus(state)
});
```

The names `promotedBytes`, `hostSelectionChanged` and `hostRendererStatus` illustrate host responsibilities, not supplied helpers. The host must independently authorize loading, validate/promote exact bytes and verify their cryptographic digest before mount. A caller boolean, manifest hash or `ready` callback supplies no authority. The viewer checks structural consistency but does **not** authenticate the manifest or compute its declared SHA-256. The profile's generator text is a format discriminator, not a trust signal.

Supply the compiler manifest defined by the current [SceneSpec contract](SCENE_SPEC.md), not the different validator-summary shape. Its required `asset_sha256`, `scene_sha256` and `input_sha256` values must each be lowercase 64-character hexadecimal digests. `input_sha256` identifies the canonical original declarative input, distinct from the normalized editable scene; the viewer validates its presence/format but does not receive that input or recompute its digest. Preserve the original compiler qualification fields; later visual/native evidence belongs in separate current QA records. Browser-facing inputs are data records, not arbitrary JavaScript objects/Proxies from an untrusted program. Manifest getters and non-plain values are rejected; this API cannot sandbox hostile caller JavaScript.

| API | Behavior |
| --- | --- |
| `mount({canvas, glb, manifest, onSelect?, onStatus?})` | Copies bounded `ArrayBuffer`/`Uint8Array` input, validates before WebGL allocation and returns the methods below. Invalid data or unavailable WebGL throws a bounded error. No fetch/URI input. |
| `setCamera(viewId)` | Applies an exact named landmark from asset extras. No interpolation or tour is started. |
| `setCamera('fit' \| 'reset')` | Fits the model bounds at the current aspect unless the asset itself has that exact named view ID. `setCamera(null)` always fits/resets framing, avoiding reserved-name ambiguity. Selection is retained. |
| `setSelection(entityId \| null)` | Validates stable identity and updates highlight without emitting `onSelect`; host/controller remains the state owner. Unknown IDs throw. |
| `resize()` | Reads the canvas CSS rectangle, caps DPR at 2 and each backing dimension at 4096. Re-fits only while in fit mode; named/orbited camera context is retained. Returns false for zero size, disposal or context loss. Host calls after layout/visibility changes; no observer/timer is installed. |
| `dispose()` | Idempotently releases owned GPU resources when valid, event listeners and pointer capture. Restores a tabindex it added. No further drawing. |
| `entities`, `views` | Frozen ID/label inventories for host controls. Use labels as text, never HTML. No business metric or live query content is loaded. |

`onSelect` receives a stable entity ID or null after pointer picking or keyboard selection. Programmatic selection is silent to prevent controller feedback loops. `onStatus` reports `ready`, `unsupported`, `error`, `context_lost`, `remount_required` or `disposed`, with rendered/native qualification still explicitly `unqualified`. `ready` means source setup and draw commands were issued, not that the image was observed.

Context loss stops work and releases active pointer interaction. Restoration requires the host to dispose and remount the same independently checked bytes, then restore its selected ID/view as appropriate; the viewer does not retry silently. A failed initialization cleans up partial allocations. The host owns its canvas, composition, status messaging and current data lifecycle, and should not share this WebGL context with another renderer.

## Input profile and rendering limits

The parser accepts exactly one GLB JSON chunk and one embedded BIN chunk, with bounded JSON size/depth/value count and duplicate-key rejection. It checks allowed keys, buffer spans, tightly packed float32 position/normal and sequential uint32 index accessors, triangle winding, finite/unit normals, opaque materials, references, hierarchy, stable IDs, manifest counts/bounds and named views. Unknown keys, extensions, external URIs, images/textures, compression, scripts, animations, skins, imported-mesh features and arbitrary shaders are rejected. Allowed manifest metadata never instructs the viewer to execute an action.

Limits follow the narrow compiler profile: 16 MiB asset, 2 MiB JSON, 1,024 entities, 128 geometries, 64 materials, 32 views, 100,000 unique and 200,000 expanded triangles, hierarchy depth 32, bounded finite coordinates/transforms. The viewer also rejects degenerate transformed triangles whose cross-product magnitude is at most `1e-10`; extreme tiny scaled geometry may therefore be rejected even when a compiler structurally emits it. These are acceptance/resource limits, not measured performance guarantees.

Positive hierarchical TRS is baked into retained world coordinates. GPU positions are recentered around the scene bounds for precision; flat face normals are transformed through the resulting triangles. Rendering uses depth testing and basic two-sided directional diffuse shading, with the material's base color and a selection tint. Metallic/roughness factors are validated but **not** rendered as physically based materials. There are no textures, shadows, environment lighting, transparency, postprocessing, cutaway/exploded transforms or animations. Analytical meaning must remain available outside decorative shading/highlight.

Perspective fit accounts for aspect ratio. Drag orbits the current target, wheel dollies within bounded distance, named views use the supplied position/target/up, and reset fits scene bounds. Pointer selection intersects actual triangles and selects the nearest hit; it is a bounded linear scan without acceleration. Rendering happens only on setup, explicit state/resize changes or user input. No animation loop, autoplay, background tour or automatic asset load exists.

## Accessible and application integration

Provide a visible named entity selector/list, named-view controls and Fit action from the returned inventories. Wire host selection changes to `setSelection` and renderer `onSelect` back to the controller using stable IDs. Keep exact metrics and missing/restricted scope in accessible DOM content, not mesh color alone. The canvas supports focus, left/right entity selection and Home to fit; the host supplies its accessible name, instructions, focus/return policy and equivalent non-canvas task path. The viewer adds `tabindex=0` only when absent and removes only that addition on disposal.

The host chooses touch/scroll policy and canvas sizing; `touch-action` behavior must be qualified for the selected layout. There is no automatic focus transfer to a detail panel. No spatial data event authorizes a query, writeback, navigation or publication. A native Omni adapter must separately establish allowed script/model loading and actual callbacks; this file does not invent those capabilities.

## Focused checks

After authorization, run only the first-party synthetic tests using the existing Node executable with inherited module-loading options removed:

```sh
env -u NODE_OPTIONS -u NODE_PATH node --test tests/test_spatial_viewer.js
```

The tests cover strict parsing/references, hierarchy, camera framing and picking math, stable-ID API behavior, bounded backing size, context-loss handling and cleanup. One integration case invokes the existing Python executable with `-I -S -B`, a minimal environment and a timeout to compile an original synthetic box through the actual first-party producer; its GLB and unmodified manifest then enter the viewer parser. This exercises the real metadata boundary and checks independent expected bounds/counts plus required input-digest handling. Interpreter isolation flags do not establish OS worker isolation. The tests use only built-in Node/Python modules and this repository's source, write no generated artifacts and never start a browser or renderer host. Actual rendering, user interaction, accessibility and native/performance checks remain pending until an authorized real target is available.
