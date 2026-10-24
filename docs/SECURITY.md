# Security operations and qualification

Follow the [dependency policy](../skills/omni-artifact-accelerator/references/dependency-policy.md). No Blender source or runtime is supported. No package, runtime, decoder, CI toolchain or installed skill may be acquired, loaded or activated without exact scoped human sign-off. Existing availability is not approval. Local development, tenant publication and operational host activation are separate actions.

## Maintained local boundaries

- **CLI:** [configuration and limits](../skills/omni-bi-engineer/references/omni-build-export.md#local-cli-trust-boundary). Real invocations require explicitly pinned executable/interpreter paths. A private temporary configuration replaces ambient credentials and loader settings. Output/deadline failures retain ambiguous-write reconciliation semantics.
- **Initial App resources:** [initial App adapter](../skills/omni-app-engineer/scripts/omni_app_native.py) validates static declarations before the locked candidate is prepared. The [resource policy](../skills/omni-app-engineer/scripts/app_resource_policy.py) permits a narrow self-contained HTML/CSS/SVG profile, local fragments and checked base64 raster image declarations. Unsupported resource forms require separate qualification. Source checks do not supply a browser sandbox or replace native CSP enforcement; inline JavaScript remains authored executable code requiring review.
- **File intake:** regular-file checks occur after a nonblocking/no-follow descriptor open. Link, size and change checks remain in place. The workspace must remain private; this is not proof against every hostile same-user race.
- **CSV:** the Power BI, Looker and Tableau normalizers share a streaming reader; Hex retains Power BI delegation. Limits are 100,000 data rows, 512 columns, 1,000,000 data cells and 1,000,000 characters per logical record. Existing file byte caps still apply. Excess, ragged and malformed records fail without consuming the remainder; data is never silently truncated. Original evidence and explicit ordinal/null/locale mappings remain required. Whole input/decoded buffers and JSON branches retain their existing separate byte limits.
- **Activation:** public skill installation and optional modeling-harness execute/promote remain denied. A self-asserted approval reference or agent-writable JSON cannot enable them.

Run the [source validation lane](TESTING.md) after affected changes. Preserve the exact source hashes, original failure, correction and matching retest outside the repository. Close a finding only for its actual exercised path; keep live host, tenant, access and visual outcomes separately marked.

## Dependency decision record

Prepare one reviewable record per requested package/runtime action outside the repository:

| Required information | Evidence to retain |
| --- | --- |
| Identity | Exact source URL, version/revision, artifact digest, platform/architecture, immutable runtime image if used |
| Closure | All transitive packages, native/WASM components, decoders, lifecycle/build hooks and implicit runtime imports |
| Purpose | Requested capability, alternatives and reason the source-only path cannot satisfy it |
| Provenance | Maintainer/source identity, license, artifact attestations or explicit gaps, dated vulnerability review and coverage limits |
| Actions | Acquisition, installation, import, build, execution, update and activation distinguished individually |
| Environment | Host/operator, filesystem/network/credential/GPU permissions, telemetry/egress, repeat-use scope |
| Recovery | Removal, rollback, expiry/revocation handling and exact evidence retention |
| Decision | Trusted operator-held sign-off tied to those bytes/actions; never a worker/agent-written approval boolean |

`requirements.txt` records PyYAML 6.0.3 only. It does not choose an artifact, prove provenance or authorize imports. Complete artifact/closure selection before requesting its use. An unavailable or incomplete record stays blocked; a version pin or a previous successful import is insufficient.

## CI activation contract

The checked-in manual workflow is a **notice only**, not a required validation result. Keep it that way until the operator has qualified the exact runner/toolchain and repository protections. The local source lane is available without enabling remote execution.

A future qualified CI configuration must:

1. Use an approved disposable runner with exact runtime/toolchain identities and a reviewed source-acquisition mechanism. Pin any actions by immutable commit and review their dependencies/actions separately. Do not put untrusted pull-request code on a persistent privileged self-hosted runner.
2. Check out the exact reviewed revision without persisting credentials. Use read-only repository permissions, no tenant/cloud secrets, no package cache restores or package setup commands, bounded execution and no publication steps.
3. Run `python3 -I -S -B scripts/validate_source.py --report <private-new-path>` and retain revision/source hashes plus actual success/failure. The receipt is local evidence, not host authorization.
4. Configure trusted approval outside repository-editable files where required, then verify branch rules and the exact required check name. A workflow/environment name alone does not demonstrate protected approval or enforced merge checks.
5. Exercise a failing fixture and a valid fixture on that exact approved runner before enabling release reliance. Changes to runtime, actions, permissions or dependency closure need renewed coverage.

The inactive CI specification and current decision records belong with the operator's external review evidence until approved. No live branch protection or CI environment is configured by these instructions.

## Isolated 3D activation

First select the [execution route](../skills/omni-app-engineer/references/spatial-integration.md#select-the-execution-route). Original procedural scenes authored inside native Apps use the App's qualified browser boundary and reviewed code; they do not universally require a separate modeling VM. Library/decoder use, external assets and native writes still need explicit approval and target qualification. The following gate governs the optional off-browser compiler service.

Use the [harness security contract](../harness/SECURITY.md) and [host qualification matrix](../harness/HOST_QUALIFICATION.md). No runtime/image has been selected or approved by this source package. Keep worker execution, validation service and promotion broker disabled until exact dependencies, trusted authorization and measured host boundaries are qualified. A container, interpreter flag, process group or successful synthetic test is not equivalent to that qualification.

## Native scene security

The [native scene framework](../skills/omni-app-engineer/references/native-scene-framework.md)
is separate from off-browser execution. Its passive contract rejects executable
fields/resource URLs, accounts aggregate geometry/texture/framebuffer demand and
limits hierarchy/coordinates. Fixed Canvas2D recipes accept no callback or remote
font/image. The renderer adapter has no importer, downloader, asset loader or
global engine discovery. It accepts an engine only from its caller; that is a
code interface, **not an authenticated approval gate**. The trusted host must
verify exact bytes/actions before it loads or calls dependency code.

The revision check cannot distinguish a malicious replacement with the same
revision string. Local doubles do not qualify the engine or isolate supplied
JavaScript. Driver memory, GPU timing and target policy remain unmeasured.
The module loading route has not been qualified against the classic assembler
and initial static resource profile. Do not weaken them, introduce a hidden
dynamic loader or activate a browser to turn source checks into a native pass.

## Release and recovery

The release owner reviews the final diff, exact source validation receipt, independent finding retests, dependency approvals and remaining gaps. A source-only release can include the explicitly disabled harness without claiming operational 3D support. Enabling execution requires the separate host milestone. Do not silently turn unavailable tests into passes or repeat an unknown native write.

For a regression, stop affected operations, preserve private evidence and restore only the reviewed affected source after checking local modifications. Reconcile any target intent before resuming. Keep approval/activation denials in place during rollback. Source review, tests and hashes do not grant permission to push, publish, install or mutate a live tenant.
