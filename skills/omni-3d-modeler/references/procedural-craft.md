# Procedural modeling craft

Use these principles for original work. They describe decisions, not a universal
stadium, dashboard shell, camera sequence or asset style.

1. **Task before spectacle.** State what spatial understanding enables: inspect
   an assembly, trace a connection, compare physical context or orient in a
   venue. A purely illustrative scene can support a story without pretending to
   encode governed data. Keep a simpler diagram when it serves the task better.
2. **Silhouette before detail.** Establish recognizable proportions and a useful
   viewpoint with a few masses. For a reference reconstruction, trace dimensions,
   units, axis/origin and tolerance to supplied evidence. For an illustration,
   label approximation. Avoid precision-looking dimensions without a source.
3. **Hierarchy and adjacency.** Name durable parts, parent transforms and empty
   circulation/clearance spaces. Build the intended relationship before adding
   windows, seating, panels or small trim. Stable IDs survive parameter changes.
4. **Material contrast with purpose.** Separate structural, functional and
   focal parts through restrained roughness, value and scale. Texture repetition
   follows dimensions; avoid giant labels and toy-like gloss as defaults. Review
   brand color semantics with branding and keep analytical scales invariant.
5. **Context at the right fidelity.** Terrain, neighboring objects and people
   are optional scale cues. If synthesized, use deterministic seeds and stable
   identities and label them illustrative. Never invent survey accuracy, brand
   ownership, operating status or real-world occupancy.
6. **Camera as an inspection tool.** Give every view a useful purpose and
   readable target. Fit the actual container; preserve context on data refresh.
   Tours are optional, interruptible and resumable only by user intent. Supply
   static views and a stop transcript; animation cannot withhold exact evidence.
7. **Budget the assembly.** Count repetitions, shared geometry/materials,
   texture storage and framebuffer demand before creation. Spend complexity on
   meaningful detail. A triangle cap is not a device performance result.

The [native scene contract](../../omni-app-engineer/references/native-scene-framework.md)
supports boxes, cylinders, convex extrusions, bounded tubes and revolved
profiles. Compose terraces, junctions and repeated assemblies from these only
when that representation fits. It does not support arbitrary topology, boolean
union, photogrammetry, imported model loaders or dimensional certification.
Keep unsupported operations explicit; an engine change is not automatic authority
to acquire dependencies.

For a handoff, give engineering the task, fidelity/source pins, part hierarchy,
scene parameters, materials, named-view rationale, expected dimensions/counts,
data-bearing entities and non-canvas route. Give independent QA the original
expectations, not just the generated bounds. Reuse brand/website decisions and
the existing current intent; ask only a consequential missing question. Do not
make the customer select an engine, wire a query or debug a loading route.
