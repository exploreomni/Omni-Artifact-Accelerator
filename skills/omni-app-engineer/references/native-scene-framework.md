# Native procedural scene framework

Use this original, optional framework for a task that benefits from spatial
inspection, an environment or a data-linked assembly. It supplies mechanics,
not a page layout. Keep navigation, composition, branding and storytelling
specific to the task. A normal dashboard or a better 2D diagram remains valid.

## Capability and authority

| Component | Implemented source | Qualification boundary |
| --- | --- | --- |
| Scene contract, geometry, texture recipes | Strict declarative input, finite geometry, UVs/normals, fixed Canvas2D recipes | Local math/contract checks; no rendered claim |
| Session | Retry, named views, interruptible tours, visibility/reduced-motion handling, teardown | Synthetic clock/renderer checks |
| Data bridge | Exact query/field IDs, analytical entities only, stable selection and failure clearing | Synthetic snapshots; no Omni SDK or access claim |
| DOM wiring | Container sizing, visibility, observers, preference changes, plain controls | Local doubles; actual keyboard/screen-reader behavior unrun |
| Renderer adapter | Explicit injected Three.js/OrbitControls interface, shared resources, selection, render-on-demand | Source candidate; actual dependency/native/rendering not qualified |
| Existing isolated compiler | Separate SceneSpec 1 / untextured GLB profile | Host execution/promotion remains disabled |

No file in this framework installs, downloads or imports an engine. The renderer
candidate targets the documented r186 APIs with `three@0.186.1` and its matching
OrbitControls. Version/revision checks are compatibility checks, not approval or
integrity verification. A trusted operator must approve exact bytes and the
resolved module closure before loading them. Do not adopt a preexisting `THREE`
global or use an agent-written `approved` field. See the
[dependency policy](../../omni-artifact-accelerator/references/dependency-policy.md).

The existing portable assembler accepts classic scripts and the initial native
App resource profile rejects declared external modules. This framework does not
change either policy. Modern module loading, bundling or a host-provided engine
requires a separately inspected, supported and authorized route. Dynamic script
injection, copying a fetched dependency inline and broadening safe domains are
not workarounds. No tiny candidate has established native compatibility yet.

## Scene data

[native_scene_contract.js](../scripts/native_scene_contract.js) exposes
`OAANativeSceneContract.validate(spec) → {scene, budget}` with frozen outputs.
Use `schema_version: "oaa-native-scene-v1"`, `units: "m"` and
`axes: "right-handed-y-up"`. This is a new native contract, not an extension of
the isolated compiler's SceneSpec 1. Do not feed one into the other implicitly.

Required records:

- `fidelity: {kind, source, notes}`. Kind is `illustrative` or `reference-based`.
  Retain dimension sources and tolerances in the model brief; the word
  `reference-based` alone never establishes fidelity.
- `materials`: `id`, `label`, six-digit hex `color`, `roughness` and `metalness`
  in `[0,1]`, optional fixed `texture` recipe.
- `geometries`: stable `id`, supported `kind` and shape-specific numeric fields.
- `entities`: stable `id`, `label`, geometry/material IDs, local `position`,
  `rotation` (radians), positive `scale`, `role` (`decorative` or `analytical`),
  optional parent ID. Preserve IDs through changes; never use array indexes.
- `views`: stable `id`, meaningful `label`, three-number `position` and `target`.
- `render`: positive CSS `width`, `height`, admitted `dpr` and `shadows: false`.

IDs use `[A-Za-z][A-Za-z0-9_-]{0,63}`; labels are at most 120 characters.
Unknown fields, callbacks, resource URLs, scripts, custom shaders, unsupported
extensions and non-data objects fail. Bound raw JSON before parsing; validation
of an already-created object is not a hostile JavaScript sandbox.

| Geometry | Fields beyond `id`, `kind` | Meaning |
| --- | --- | --- |
| `box` | `width`, `height`, `depth` | Centered at origin |
| `cylinder` | `radiusTop`, `radiusBottom`, `height`, `radialSegments`, `capped` | Centered on Y |
| `extrusion` | `points: [[x,z],…]`, `height` | Strictly convex counterclockwise footprint, base Y=0 |
| `tube` | `path: [[x,y,z],…]`, `radius`, `radialSegments`, `capped` | Bounded open path; no arbitrary curve evaluator |
| `revolution` | `profile: [[radius,y],…]`, `radialSegments`, `capped` | Increasing Y profile around Y |

Use repeated entities for terraces, panels and modular assemblies; use shared
geometry/material IDs. A junction may be a separate bounded component. This
profile does not promise boolean unions, holes, concave extrusions, arbitrary
asset import or manufacturing geometry. Request or label an approximation when
the chosen geometry cannot express the requirement.

`OAANativeSceneGeometry.build(descriptor)` returns typed positions, normals, UVs
and indices. `OAANativeSceneTextures.paint(recipe, canvas)` paints only `stripes`,
`grid`, `panels` or `label` with `size`, `background`, `foreground`, `repeat`
and a label only for the label recipe. Plain material color supplies solid
surfaces. Texture text uses system fonts; remote fonts/images and custom drawing
callbacks are outside this profile. Branding approval is separate from runtime
approval. Image textures remain a future independently reviewed asset route.

## Admission and performance

Validation counts the whole scene before geometry/texture/GPU allocation:
1,024 entities, 128 geometries, 64 materials, 32 views, 100,000 unique triangles,
200,000 expanded triangles, 64 MiB geometry, 32 MiB decoded textures including
mipmaps, DPR at most 2 and backing dimensions at most 4,096. Hierarchy depth and
cumulative world extent/scale are bounded too.

The initial combined estimate is capped at 192 MiB with color/depth backing
storage, geometry, textures and a small reserved selection outline. Shadows,
postprocessing and extra render targets are disabled. Driver overhead, internal
engine allocations, program caches and actual device memory are not measured by
this estimate. These are provisional admission ceilings, **not performance
guarantees**. Qualify one tiny shape/material/camera candidate first, measure the
target device, and tighten limits before escalating complexity.

The adapter shares geometry and materials; it does not yet batch instances into
instanced draw calls. Repetition can therefore be draw-call limited well before
the triangle cap. The renderer draws on demand; there is no idle autorotation or
second animation clock. Resize fits the available aspect ratio within the
initial admitted backing-pixel area. A large display does not silently increase
the scene's resource allowance.

Initial automatic framing uses the narrower horizontal/vertical field of view.
Oversized fits fail before controls can silently clamp the requested distance;
choose a bounded inspection view for those scenes. The adapter's explicit
`fit()` action frames current bounds at the current aspect ratio. Ordinary
resize preserves the inspected view; it does not undo a user's camera choice.

## Compose the modules

Load only reviewed first-party sources, in order: contract; geometry; textures;
session; spatial controller; data bridge; renderer adapter; optional host wiring.
The engine is supplied separately through an authorized host path. The source
adapter has no authority to acquire it.

```javascript
// Host code after exact dependency and native-route qualification.
const accepted = OAANativeSceneContract.validate(sceneSpec);
let renderer;
const session = OAANativeSceneSession.create({
  views: accepted.scene.views,
  reducedMotion: true,
  initialize: async () => {
    renderer = OAANativeSceneRenderer.mount({
      canvas, scene: accepted.scene, THREE: approvedEngine,
      OrbitControls: approvedControls,
      onInterrupt: () => session.interrupt(),
      onContextLost: () => session.contextLost(),
      onSelect: id => selectObject(id) // route decoration vs analytical selection
    });
    return renderer;
  },
  onState: state => showStatusWithTextNodes(state)
});
const host = OAANativeSceneHost.connect({session, canvas, container});
await session.start();
// Bind user-owned buttons to named views, tour, stop, retry and explicit resume.
// On unmount: detach query subscriptions, dispose the data bridge and controls,
// then host.dispose(), which owns session/renderer disposal.
```

The functions named `selectObject` and `showStatusWithTextNodes` are the App's
own reviewed UI functions, not an Omni SDK. Give the canvas an accessible name
and described controls. `OAANativeSceneHost.controls` optionally creates plain
entity/view buttons in a caller-supplied container. Style them with the current
control system; preserve labels, visible focus and selection state. Render exact
evidence, missing states and the camera-stop transcript outside the canvas.

Session states are idle, loading, ready, paused, error, context-lost and disposed.
Initialization failure permits retry; a late result after disposal is disposed.
One session owns one renderer and one cancellable camera timeline. Wheel, pointer
or key activity interrupts motion. Hide/offscreen/navigation cancels it; return
stays paused until explicit start/view/tour intent. Reduced-motion changes are
live: cancel movement, offer instant named views, never autorotate. Context loss
requires deliberate recovery; show the non-canvas path meanwhile.

## Optional governed data

Decoration alone requires no query, dummy metric or fabricated binding.
`OAANativeSceneData.create({scene, contract: null})` returns `null` when the
scene has no analytical entities. Otherwise provide:

```javascript
const contract = {
  queryId: "exact_saved_query_id",
  keyField: "assets.entity_key",
  grain: "one row per asset in the current filter scope",
  maxAgeMs: 60000,
  fields: [{id: "telemetry.pressure", type: "number", unit: "kPa",
            aggregation: "latest observation in the selected window"}],
  bindings: [{entityId: "pump_a", dataKey: "asset_a"}]
};
```

Supply exactly one binding per **analytical** entity. The existing spatial
controller remains the selection/value authority; session owns camera/lifetime.
Metric fields keep complete source IDs, with no prefix stripping or aggregation
inside the scene. Unknown IDs, duplicate keys, nonfinite numbers, changed query
identity and incomplete snapshots fail visibly. Missing values remain unknown.

Each reviewed native query generation calls `bridge.begin()`. Resolve its token
with `{queryId, status, complete, capturedAt, rows}`. Ready data requires a
complete snapshot and timestamp. Expired ready data becomes stale. Restricted,
error or malformed current results clear previous values. Superseded results
cannot overwrite newer state. The host must convert real callbacks into this
contract and invalidate on timeout, unsubscribe, changed access or filter scope;
there is no hidden query API or automatic access verification.

Snapshot reads and emitted state evaluate freshness against the current clock,
so old values do not stay labeled ready merely because no new result arrived.
The host owns a cancellable freshness deadline and calls `checkFreshness()` on
that deadline and on resume to update visible UI. The bridge owns no background
timer. Detach that deadline with query subscriptions on unmount. Observer errors
are bounded diagnostics and cannot turn a valid result into a query failure.

Refresh does not reset the viewpoint/selection. Feed the selected object's exact
values and units into semantic DOM. Do not shade an analytical scale differently
without preserving its documented meaning and a plain-value/legend route.
Route missing fields/grain to the existing versioned DMA handoff. A scene needs
no DMA engagement when existing governed queries already satisfy its contract.

## Transfer and evidence

The original [geometry examples](../assets/native-scene-examples.js) are three
unrelated source fixtures: fictional venue, branched operational network and
dimensioned synthetic product. They demonstrate different topology/data needs;
they are not default screen templates, production datasets or rendered pilots.

Before a fresh-context trial, freeze its task, fidelity evidence, first candidate
and prompt-count categories outside the repository. Record necessary business
questions separately from avoidable technical wiring, corrective user prompts,
internal repair and manual code intervention. Target zero end-user technical
wiring questions, no unresolved critical **observed** task failures and at most
one avoidable design correction round. Unobserved customer corrections are not
zero corrections. Judge meaningful selection/evidence/return, dimensions,
materials, responsive controls and motion only in lanes actually observed.

Register source, scene, brand asset, engine closure, query and assembled-candidate
hashes in existing runtime dependencies/current intent. Changed scene/engine
invalidates affected visual, interaction and performance evidence; changed
bindings invalidate affected numerical/access evidence. A source check cannot
promote native, visual or business acceptance. Keep acquisition approval,
source implementation, native readback, rendered behavior and acceptance separate.
