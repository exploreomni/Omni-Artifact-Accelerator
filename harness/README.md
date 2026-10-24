# Optional original 3D harness

This is a source implementation for bounded model creation and inspection. It is
separate from the portable skill bundle. **Customer-job execution and promotion
are disabled.** No approved isolated host is supplied or automatically installed.
Read [the security contract](SECURITY.md) and the shared
[package-use policy](../skills/omni-artifact-accelerator/references/dependency-policy.md).

## What is implemented

| Source | Responsibility | Current evidence boundary |
| --- | --- | --- |
| [model_core.py](model_core.py) | Strict editable SceneSpec to deterministic actual GLB bytes; boxes, cylinders, extrusions, pipes, revolved shapes, hierarchy and bounded instances | Original synthetic geometry checks |
| [asset_checks.py](asset_checks.py) | Independent structural parsing of the narrow GLB profile, limits, IDs, bounds and finite geometry | Format/profile checks; not proof against parser/driver vulnerabilities |
| [worker.py](worker.py) | Bounded JSON input and model/scene/manifest byte outputs with hashes | Pure callable code; no customer CLI |
| [quarantine.py](quarantine.py) | Recheck candidate bytes, bind hashes and copy exact allowlisted outputs to a fresh private directory | Copy/validation mechanics; no authorization or promotion |
| [launcher.py](launcher.py) | Prepare pinned requests; reject execute/promote | Host gate unavailable; no fallback runner |
| [viewer.js](viewer.js) | Original dependency-free WebGL scene inspection and lifecycle | Source/parser/math tests; browser/native performance and visual craft unobserved |
| [spatial controller](../skills/omni-app-engineer/scripts/spatial_controller.js) | Stable selection/view state, exact entity binding, explicit data outcomes and disposal | Synthetic controller checks; no Omni SDK or queries |

No Blender source, scripts, APIs or assets are used. No third-party engine is
vendored. The first profile deliberately omits textures, compressed assets,
external URIs, imported general GLB files, scripts, extensions, CSG and arbitrary
shaders. These are unsupported cases, not silently approximated imports.

## Source-only setup and examples

Use an already available, approved interpreter; no package setup is needed:

```sh
python3 -I -S scripts/check_package.py
python3 -I -S harness/launcher.py capabilities
python3 -I -S harness/launcher.py prepare --scene harness/fixtures/inspection-assembly.json
```

Run from the repository root. `prepare` hashes the bounded bytes without parsing
or compiling a supplied scene; its output is a **blocked request, not a grant**.
`execute` and `promote` always fail. There is no `--approved`, host-execution or
auto-download override. Do not call pure compiler functions on customer input
in the coordinator to bypass this boundary.

Study [SceneSpec](SCENE_SPEC.md), then compare the three original fixtures:

- [Inspection assembly](fixtures/inspection-assembly.json): layered product parts,
  different materials and explicit inspection landmarks.
- [Fictional courtyard](fixtures/fictional-courtyard.json): a spatial venue composed
  from bounded instances, without real venue accuracy claims.
- [Material transfer](fixtures/material-transfer.json): equipment and pipes for an
  operational environment, with geometry separated from future governed metrics.

The fixtures are illustrative. They contain no customer data or brand assets.
The compiler preserves editable parameters and stable IDs; changing geometry
does not authorize remapping business identity or inventing measured dimensions.
Use [the focused checks](../docs/TESTING.md) for author-owned synthetic source work.

## Handoff and limits

The worker creates `model.glb`, canonical `scene.json` and `manifest.json` in
memory. The candidate manifest records hashes and structural evidence only.
Human provenance, rights, fidelity and transformation decisions stay in the
[model brief](../skills/omni-3d-modeler/references/brief-handoff.md); the trusted
host must bind them to the exact input/output receipt before consumption.

Use [viewer integration](VIEWER.md) and the portable
[Omni integration contract](../skills/omni-app-engineer/references/spatial-integration.md).
The viewer has basic diffuse shading, not full physically based materials. It
does not fetch a model or connect to Omni. Governing metrics, credentials and
effective access stay in the separately authorized App query path.

The 16 MiB GLB workload cap is not a supported native App payload size. The
existing initial App adapter's 2 MiB HTML limit includes script and base64 bytes.
Fit the exact assembled artifact to its actual supported resource policy.

## Remaining activation gates

The [host qualification matrix](HOST_QUALIFICATION.md) maps each boundary to independent acceptance evidence. It is an operational specification; the host implementation and runtime approval remain unavailable.

1. Human sign-off for an exact isolation runtime/image and dependency closure.
2. Host-owned approval verification, disposable execution, resource enforcement,
   network denial, cancellation and cleanup, with independent adversarial tests.
3. Separate isolated validation and host-authenticated exact-byte promotion.
4. Authorized native loading and effective access, followed by permitted rendered
   device/interaction/craft review and user acceptance.

These gates are not satisfied by unit tests or a manifest flag. This repository
does not claim a working VM launcher, hardened service or production acceptance.
