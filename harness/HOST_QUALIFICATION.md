# Host qualification matrix

This is the acceptance specification for a future separately approved host integration. It is not an execution driver, approval store or completed qualification report. The [launcher](launcher.py) remains blocked and has no host fallback. See [security boundaries](SECURITY.md) and [dependency decision records](../docs/SECURITY.md#dependency-decision-record).

This matrix governs off-browser model processing. It is not a prerequisite for every authored 3D scene in Omni's existing App sandbox; use the [route selection guidance](../skills/omni-app-engineer/references/spatial-integration.md#select-the-execution-route) before introducing this infrastructure.

| Boundary | Required host implementation | Independent acceptance evidence |
| --- | --- | --- |
| Exact authorization | Operator-controlled grant binds action, source/input/toolchain/runtime hashes, permissions, expiry and revocation | Altered, stale, revoked, wrong-action and wrong-host grants reject before admission; agent-written files cannot grant access |
| Runtime | Separately approved disposable VM image and pinned worker/validator toolchains; no job-time acquisition | Exact image/closure records; substituted bytes reject; missing host returns blocked without local execution |
| Input transfer | Bounded bytes copied without mounting repo, home, SSH/cloud configuration, agent settings or host sockets | Host-side mount/handle inspection and synthetic canary-denial evidence |
| Network and credentials | Host-enforced network denial and empty credential boundary | DNS/HTTP attempts fail at the host boundary; no canary credential is visible; no real secrets used |
| Resources | Enforce the launcher's proposed CPU/wall/memory/PID/scratch/output budgets | Independently measured termination at limits using bounded synthetic fixtures; no claim from requested settings alone |
| Cancellation | Revoke admission, kill descendants, close handles and destroy ephemeral state | Cancel/timeout/revocation/crash/restart cases demonstrate cleanup; no worker reused across customers |
| Output quarantine | Host accepts the exact allowlisted files through descriptors, rejects path/link/device/extra-file tricks | Traversal, symlink/hardlink, rename and changed-byte fixtures reject; file size/type/hash bounds hold |
| Independent validation | Separate disposable validator with pinned code and no worker-controlled executable selection | Tampered scene, geometry, manifest and validator claims reject; worker self-report cannot authorize promotion |
| Promotion | Protected broker checks current grant, independent receipt and exact final bytes plus provenance/rights decision | Substitution/replay/revocation/wrong-destination cases reject; compiler/validator never sees tenant credentials |
| Viewer and Omni | Separately approved rendering/native integration and effective access | Device/GPU/input/cancellation/access results recorded separately; no browser workaround when inspection is prohibited |

Store actual runtime selection, operators, protected approval mechanism, measurements, receipts and decisions outside this source repository. Unknown fields remain unverified, never guessed. A synthetic source test can demonstrate request/denial behavior only. Native loading, visual quality, fidelity and user acceptance retain their own qualification records.

The sequence is runtime decision and explicit approval, host implementation, independent isolation/cleanup verification, independent validation/promotion verification, then separately authorized native and rendered qualification. No milestone is satisfied by changing a JSON status or exposing an `approved` flag.
