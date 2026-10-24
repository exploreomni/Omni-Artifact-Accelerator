# SceneSpec 1 and the untextured GLB profile

This optional original core uses Python's standard library only. It implements declarative geometry, not a renderer, dependency manager, worker launcher or permission system. No third-party code, package, Blender implementation/API, asset, URL resolver or decoder is included. Only trusted first-party synthetic checks may run directly as described below. Customer/untrusted workload execution still requires the separate approved isolated worker; these functions are not a sandbox and must not become a host fallback.

## Functions

- `model_core.validate_scene(spec)` returns `{"scene": normalized_dict, "cost": counts, "world_matrices": {entity_id: row_major_matrix}}` or raises `SceneError`. All grammar, finite ranges, references, hierarchy and expansion costs are checked before triangle arrays are constructed. This function performs no mesh construction.
- `model_core.compile_scene(spec)` returns `{"glb": bytes, "scene": normalized_editable_dict, "manifest": dict}`. It writes nothing and accepts no filenames. The source is canonicalized and instance sets expand to ordinary explicitly identified entities; geometry definitions remain reusable and editable.
- `asset_checks.validate_glb(blob)` takes exact immutable `bytes`, returns a structural summary, or raises `AssetError`. It does not load files, follow URIs or repair unsupported content. Header/JSON structure, all schema fields, references, buffer spans, instance budgets and hierarchy are admitted before decoded vertex/index arrays; geometry values are then independently checked from bytes.

Diagnostics describe the rejected rule, not supplied labels/values. Callers own bounded intake, separate-worker validation, immutable output promotion, attribution and authorization. A matching hash or generator string is not approval or proof of origin.

## Grammar

The root has exactly these fields:

```json
{
  "schema_version": 1,
  "units": "m",
  "axes": "right-handed-y-up",
  "materials": [
    {"id":"clay","base_color":[0.6,0.4,0.3,1],"metallic":0,"roughness":0.7}
  ],
  "geometries": [
    {"id":"block","type":"box","size":[2,1,3]}
  ],
  "entities": [
    {"id":"specimen","label":"Original specimen","geometry":"block","material":"clay",
     "transform":{"translation":[0,0,0],"rotation":[0,0,0,1],"scale":[1,1,1]}}
  ],
  "views": [
    {"id":"overview","label":"Overview","position":[5,4,6],"target":[0,0,0],"up":[0,1,0]}
  ]
}
```

Only `instance_sets` is an optional additional root field. Unknown keys fail at every object, including executable fields, paths, URLs, package names, shaders, imported mesh references and approval flags. Labels are plain text, not executable markup or resource references. Do not inject them as HTML in consumers.

IDs are explicit ASCII `[A-Za-z][A-Za-z0-9_-]{0,63}`. Material, geometry, entity and view namespaces each require unique IDs; expanded instance IDs share the entity namespace. Labels are 1–120 characters without control characters. References must resolve. Every declared material and geometry must be used; unused/unmapped definitions fail instead of being silently omitted. JSON accepts ordinary dict/list/scalar data only, rejects cycles and nonfinite numbers, and bounds depth/size before canonical serialization. Booleans are not numeric values.

### Geometry definitions

Each geometry has exactly `id`, `type` and the fields in its row. No implicit dimensions or segment defaults exist.

| Type | Fields | Result |
| --- | --- | --- |
| `box` | `size: [x,y,z]` | Centered rectangular solid; 12 triangles. |
| `cylinder` | `radius`, `height`, `segments` | Capped polygonal cylinder centered at origin, along Y; `4 × segments` triangles. |
| `extrusion` | `outline: [[x,z],…]`, `height` | Capped solid from Y=0 to height; a simple original outline may be concave. No repeated closing point, duplicate points, self-intersections or collinear consecutive edges. Either winding is accepted and canonicalized; no holes. `4 × point_count − 4` triangles. |
| `tube` | `path: [[x,y,z],…]`, `radius`, `segments` | Capped circular tube on the supplied polyline. Rings use endpoint/averaged tangents and transported radial frames; no spline interpolation. `2 × path_count × segments` triangles. |
| `revolution` | `profile: [[radius,y],…]`, `segments` | Capped solid of revolution around Y. All radii are positive and heights strictly increase; no axis tips, hollow/returning profiles or arbitrary lathe topology. `2 × profile_count × segments` triangles. |

Dimensions/radii are 0.0001–10,000 meters. Geometry point coordinates are within ±10,000 meters. Radial segments are integers 3–64; path/profile/outline arrays have at most 128 points (minimum three for outline, two otherwise). Each tube segment must be at least twice its radius long; immediate near-reversal (neighbor direction dot product ≤ −0.95) is unsupported. Revolution heights increase by at least 0.0001. Geometric zero-area/collinear checks use bounded numerical tolerances; coordinate quantization that collapses a triangle at float32 output precision fails.

These are original construction operations, not exact CAD/NURBS, boolean or fabrication tools. Tube self-intersection and global solid/manifold certification are not provided. Large radii, close nonadjacent path portions or sharp bends require design review; do not claim guaranteed nonintersecting geometry. Flat face normals make the supplied polygonal geometry explicit. Smooth shading, UVs, bevels, subdivision, arbitrary curves, holes, imported models and general-purpose asset conversion are deferred.

### Entities, hierarchy and instances

An entity requires `id`, `label`, `geometry` and `material`; optional fields are `parent` (another entity ID) and `transform`. The transform accepts only:

- `translation`: three coordinates, each within ±10,000; default `[0,0,0]`.
- `rotation`: unit quaternion `[x,y,z,w]`, norm-squared tolerance 1e-6; default `[0,0,0,1]`.
- `scale`: three positive values 0.0001–10,000; default `[1,1,1]`.

Transforms apply scale, rotation, translation in that order, in the parent's coordinates. Negative/reflection scales are unsupported. Parent references may be forward references; cycles, duplicate parenting and more than 32 levels fail. Transformed conservative bounds and matrix components must remain finite within ±1,000,000 before mesh allocation. Conservative bound admission may reject near-limit rotated geometry that would narrowly fit; it never expands limits silently.

An optional instance set is shorthand, not an executable repetition expression:

```json
{"geometry":"block","material":"clay","parent":"existing-parent",
 "instances":[
   {"id":"left-block","label":"Left block","transform":{"translation":[-3,0,0]}},
   {"id":"right-block","label":"Right block","transform":{"translation":[3,0,0]}}
 ]}
```

`parent` is optional; each instance requires its own `id` and `label`, with an optional transform. Expansion is bounded before construction. There are no count expressions, random seeds, code callbacks or array-index identities. The canonical expanded scene sorts definitions, entities and views by stable ID; source reordering does not change GLB bytes. Changing a dimension preserves IDs while changing geometry/source digests. The manifest maps every entity ID to its node, mesh, geometry, material and actual transformed vertex bounds. Repeated geometry/material pairs share a mesh; different materials may reuse one geometry's accessors.

### Named views

Each view requires `id`, `label`, `position`, `target`, `up`. Position/target are world-space meter vectors within ±1,000,000. They must differ; up must be a unit vector not parallel to the viewing direction. Views are declarative landmarks stored in manifest and scene extras, not glTF camera nodes, tours, animation or evidence of camera/render behavior. A viewer owns projection, fit, transitions, reduced motion and effective interaction qualification.

## Limits and cost admission

| Resource | Limit |
| --- | ---: |
| Canonical input JSON bytes | 1,048,576 |
| JSON values / nested container depth | 100,000 / 12 |
| Geometries / materials / named views | 128 / 64 / 32 |
| Entities after explicit instance expansion | 1,024 |
| Instance sets | 128 |
| Unique triangles / flat vertices | 100,000 / 300,000 |
| Triangles across expanded entities | 200,000 |
| GLB bytes / JSON chunk bytes | 16,777,216 / 2,097,152 |
| GLB JSON nesting / hierarchy levels | 16 / 32 |

A flat triangle uses 84 binary bytes: three float32 positions, three float32 normals and three uint32 indices. Input preflight also reserves bounded metadata overhead before mesh allocation; final bytes are checked again. The validator admits aggregate float and index counts, exact spans, mesh/instance expansion and hierarchy before decoding. Workload bounds are not measured frame-rate, CPU, memory or device-performance guarantees. The trusted worker must separately enforce CPU/RAM/process/disk/time limits and termination.

## Strict GLB profile: `oaa-glb-untextured-v1`

Output is actual GLB 2.0: 12-byte header, aligned JSON chunk, aligned embedded BIN chunk, exact total length. It is not JSON renamed `.glb`. The validator accepts this narrow profile rather than arbitrary glTF:

- One default scene, one embedded buffer, no URI fields, no extra chunks or unclaimed binary bytes.
- Nonoverlapping tightly packed buffer views. Position and normal accessors use float32 `VEC3`, array-buffer target 34962. Indices use uint32 `SCALAR`, element-buffer target 34963. No strides, sparse accessors, offsets within views, normalized integers or compression.
- Exactly one triangle primitive per mesh (`mode:4`), with `POSITION`, `NORMAL`, indices and one material. Indices are sequential; every triangle has its own three vertices. Position accessor min/max exactly match the emitted float32 values. Normals are finite/unit and agree with nondegenerate triangle winding.
- Opaque untextured PBR factors only: material `name` is its stable ID; `pbrMetallicRoughness` contains only `baseColorFactor:[r,g,b,1]`, `metallicFactor`, `roughnessFactor`. Factors are 0–1.
- Each node has `name`, `mesh`, translation/rotation/scale, `extras:{entity_id}` and optional children. Mesh extras contain only `geometry_id`. Every node, mesh, material, accessor and buffer view must be reachable/used consistently.
- Scene extras contain only units, axes and the named views described above. No scripts, images, textures, samplers, extensions (required or optional), animation, morph targets, skins, lights, arbitrary extras or decoder hints are accepted. Unknown fields fail, including otherwise legitimate glTF features outside this profile.
- Duplicate JSON keys, malformed UTF-8, nonfinite constants, excessive nesting, duplicate IDs, bad references, mismatched counts, out-of-range/nonsequential indices and forged position bounds fail. External URI rejection requires no fetch attempt because the validator has no loading path.

The manifest includes exact GLB SHA-256/bytes, canonical editable scene SHA-256, original declarative input SHA-256, counts, bounds, entities and views. Hashes identify bytes/data; they do not prove rights, source authorship, authorization or promotion. Generated flags do not grant authority. Root-level operating controls must quarantine, independently validate and promote only exact bytes. Output file/link/path safety is outside these pure functions and belongs to the trusted output broker.

## Original fixtures and focused evidence

- [inspection-assembly.json](fixtures/inspection-assembly.json): fictional object inspection with a base, cylindrical support and revolved head; parent transforms matter.
- [fictional-courtyard.json](fixtures/fictional-courtyard.json): an original concave terrace, repeated columns and canopy; no real venue dimensions or customer assets.
- [material-transfer.json](fixtures/material-transfer.json): an unrelated illustrative vessel and routed tube on a platform; no operational or engineering-safety claims.

Run only the authorized first-party checks with `python3 -I -S tests/test_spatial_core.py -v`. They assert independent primitive/extrusion/tube/frustum counts and signed volumes, transformed bounds, deterministic GLB roundtrip, stable IDs under source reordering and parameter changes, all fixtures, pre-allocation expansion rejection, duplicate/NaN/giant-number/cyclic inputs, hostile URI/extension/range/identity/chunk/JSON structures, and rejection before vertex decode. They establish local numerical/structural behavior only. Browser/render/GPU/native interaction, OS isolation, texture safety, operational load and visual quality remain unassessed.
