# Modeling judgment

Use the task to choose fidelity and structure. A vehicle inspection, a building orientation view and a product assembly can share identity/state rules without sharing a camera, palette, layout or introduction. Reuse a treatment when it fits; novelty is not a quality metric.

## Choose useful fidelity

| Need | Useful modeling decision | Evidence limit |
| --- | --- | --- |
| Locate or compare parts | Distinct silhouette, visible adjacency, stable parts and useful clearance; omit detail that hides the task. | Schematic geometry can preserve relationships without claiming exact shape. |
| Explain an assembly | Named components and an explicit assembly relationship; an exploded view only when it clarifies placement. | Exploded positions are illustrative offsets, separate from physical coordinates. |
| Inspect a product or vehicle | Resolve major proportions before seams, bevels or small repeated details; choose views that expose the relevant surfaces. | A supplied dimension or authorized reference supports only the measured/observed features. |
| Understand a building or venue | Model circulation, landmarks, levels and modular relationships needed for orientation; use cutaways only when useful. | A fictional layout is not a surveyed model, code-compliant design or validated evacuation plan. |
| Compare governed metrics spatially | Keep geometry identity and scale stable while labels/encodings reflect explicit scope and missingness. | Height, color or animation must not imply a measurement absent from the data. |

Use **schematic**, **illustrative** or **source-constrained** as descriptive fidelity choices, with a rationale. None is a quality score. Separate verified dimensions from chosen proportions and unknown measurements. Do not invent a required tolerance: obtain it when dimensional precision matters, otherwise state the design's limited purpose.

## Build from relationships

Resolve silhouette and bounding dimensions, then hierarchy and shared parts, then surfaces and selected detail. Define units, axes, origin, local transforms and parent relationships explicitly. Check that repeated pieces remain countable and edits do not change their identities. Avoid unnecessary hidden geometry and overlapping/copied surfaces. Curves, extrusions and repeated components are design intentions until an approved compiler confirms supported operations and limits.

For existing assets, retain original source bytes and their provenance. Describe transformations, scale changes, simplification and texture substitutions separately; do not silently discard a required component or relabel an approximate replacement as faithful. Unknown rights, dimensions or format support hold the affected adaptation while original design work can continue.

Materials express surface character and hierarchy. Specify roughness/reflectance intent, transparency needs and which surfaces must remain legible under the intended views; do not prescribe unsupported shader code or a renderer-specific node graph. Reserve semantic colors for governed meaning. Color, shadow, perspective and occlusion can distort comparison even when labels are numerically correct.

## Make inspection useful

Choose named views by purpose, such as connections, service access or level overview. State the subject and framing relationship; avoid universal camera coordinates or a mandatory orbit opening. A guided tour should reveal useful information at each stop and permit direct inspection, interruption, reset and a static alternative. Exact state and values must remain accessible while motion is stopped.

Ask whether the selected entity is visible, distinguishable and reachable without precise pointer aiming. Provide a keyboard/list route and selected evidence outside tiny mesh labels. Specify what happens when an entity is filtered out, absent from a partial result, restricted, renamed, or missing after an asset revision. A missing row is not automatically zero or evidence that a physical object disappeared.

For narrow or short-height hosts, prioritize the task's selected evidence and relevant view. Adapt the scene and companion information deliberately; shrinking the entire desktop composition is not a responsive design. Actual legibility, comfort, contrast and performance require permitted rendered/runtime observation.

## A focused critique

Inspect the most consequential part of the brief: recognizable proportions; coherent component relationships; units and fidelity; useful inspection; valid data meaning; rights; target feasibility. Record `intended → observed → impact → revision → affected retest` using existing design/QA records. A reviewer may choose a different treatment for good reasons; assess the task and evidence rather than resemblance to an example.

Correct one material weakness before adding decorative detail. When only a specification can be reviewed, state that the rationale was assessed and visual/runtime results remain unobserved. Consult the shared [dependency policy](../../omni-artifact-accelerator/references/dependency-policy.md) before any proposed toolchain operation; this reference grants none.
