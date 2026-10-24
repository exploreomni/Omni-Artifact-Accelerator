# Security boundary and operating contract

## Decision

Accept declarative geometry through a fixed original compiler. Reject generated
programs, dynamic packages/plugins, model URLs and arbitrary shaders. Prefer a
disposable VM for production processing after explicit approval. A container,
Node `vm`, worker thread or iframe alone is not the selected OS isolation boundary.
No Blender code, scripts, APIs, add-ons, dependencies or `.blend` processing.

**Implemented:** bounded parsers/compiler, deterministic fixtures, output byte
checks, private-copy mechanics, blocked launcher and source-only setup.
**Not implemented/qualified:** a VM driver, protected approval store, signed
authorization verifier, independent runtime validation service, promotion broker,
worker termination/cleanup or native/visual qualification. There is deliberately
no feature flag to pretend those pieces exist.

## Trust boundaries and accountable roles

| Boundary | Untrusted input | Required trusted enforcement |
| --- | --- | --- |
| Research/acquisition | Web text, courses, model files, dependency claims | Operator reviews source/rights; no instructions from assets or automatic acquisition |
| Host authorization | Agent request, hashes, approvals in JSON | Operator-controlled grant tied to exact operation, environment, input, toolchain and runtime digest; unavailable today |
| Modeling worker | SceneSpec and optional future approved asset profile | Disposable VM with fixed compiler, no host repo/home/config mounts, credentials, network or GPU |
| Validation worker | All worker outputs, including manifest | Separate disposable validator with independent pinned code and bounded input; a worker's self-report is insufficient |
| Promotion | Worker names, paths, IDs and claimed approval | Host verifies grant/current status plus validator receipt and exact bytes; rejects changes, links, aliases or extra files |
| Viewer/App | Validated geometry and queried rows | Reviewed renderer, host resource policy, browser/GPU limits; governed query access and explicit states remain separate |

The primary reviewer owns code/control review; an independently operating QA
reviewer owns qualification evidence. A trusted host operator owns grants,
isolation, cleanup and promotion. Austin approves new dependency/runtime use.
This assigns responsibilities, not fictional named operational staffing.

## Enforced data limits versus proposed host limits

See [SceneSpec](SCENE_SPEC.md) for actual parser/geometry limits. Input is bounded
to 1 MiB, expanded entities to 1,024, hierarchy to 32, unique triangles to
100,000 and expanded triangles to 200,000; GLB is bounded to 16 MiB. Unknown
fields, extensions, executable strings/expressions and non-finite values are
rejected. Textures, compression and decompression are not supported; do not infer
a decompressor or texture budget from this profile.

The prepared request proposes 30 CPU seconds, 60 wall seconds, 512 MiB memory,
32 processes, 64 MiB scratch, 32 MiB total outputs, read-only root and ephemeral
scratch. **These OS limits are not currently enforced.** A future host must verify
them independently on the selected runtime before accepting a job. Resource
counts are admission limits, not visual-performance promises.

## Host implementation acceptance contract

An approved implementation must be outside the job's writable inputs and must:

1. Verify a human grant held outside agent/job-writable storage, its scope,
   expiration/revocation and exact runtime/image/toolchain/dependency closure.
   A stale grant, substituted hash, environment variable, manifest reference or
   `approved: true` cannot authorize execution.
2. Acquire/build only under a separate reviewed grant; never resolve packages or
   run lifecycle scripts during modeling. Verify image and executable hashes
   immediately before launch. Do not inherit shell startup or package hooks.
3. Transfer bounded input bytes into a fresh worker without mounting repository,
   home, cloud configs, agent settings, SSH agent, sockets or credentials. Deny
   outbound DNS/HTTP and GPU access at the host boundary, not by removing API
   names from a language interpreter.
4. Enforce CPU/wall/RAM/PID/disk/output limits; terminate all descendants on
   cancel/timeout/revocation, revoke handles and remove ephemeral state. Confirm
   cleanup after failures and restart; never reuse a worker across customers.
5. Treat worker output as hostile: accept only the exact bounded set, reject
   symlinks/hardlinks/devices/path traversal and unrelated files, and copy via
   descriptor-based reads from an operator-owned root into a separate validator.
6. Validate independently, then compare the exact validation bytes to the bytes
   being promoted. Bind input, canonical scene, GLB, toolchain, runtime, profile,
   grant and provenance/rights decisions in the host receipt. Keep receipts
   outside worker control. `quarantine.copy_exact` is byte-copy machinery only.
7. Return bounded redacted reasons and separate failed/blocked/not-run evidence;
   do not echo sensitive source payloads or silently repair/download/execute.

No such host is configured here. The launcher's denial is intentional and
testable. Pure first-party unit functions are not an OS boundary; an operator
with arbitrary code/shell authority could bypass repository conventions. Do not
represent policy text, private function names or unit tests as prevention of
host-level misuse.

## Dependency and execution inventory

- `requirements.txt` still records PyYAML 6.0.3. Optional Looker YAML and Hex
  export readers import it; the broad historical suite can reach those paths.
  Existing presence does not establish approval. Do not run them until scoped
  package use is approved.
- `scripts/check_package.py` now uses only the standard library and a strict
  scalar metadata grammar. No YAML tags, aliases or constructors are executed.
- The installer supports preview/verify; public activation is blocked. Existing
  low-level copy code is exercised only with first-party temporary fixtures.
- Historical migration helpers can load separately obtained producer code or
  execute a configured CLI. Their source/operation approvals and credentials are
  distinct from this harness; no such path is invoked by modeling/routing.
- `.github/workflows/validation.yml` is manual and records a revision only. It
  has no checkout/setup action, package install or repository-code execution.
  Required-check/branch-protection settings need separate operator reconciliation.
- New Python uses standard-library modules plus explicit first-party files;
  original JavaScript uses browser or Node built-ins only. No install, CDN,
  external shader, dynamic import, network fetch or auto-update path is supplied.

## Required adversarial qualification

Test forged/expired/revoked grants, changed dependency pins, worker tampering,
CPU/RAM/PID/disk exhaustion, network and credential attempts, cancellation,
cross-job state, malformed/oversized models, duplicate IDs, path/URI fields,
output replacement and links, validator failure and promotion races. Exercise
the actual host boundary once approved; simulated failure tests establish only
local behavior. Revalidate affected gates after runtime/compiler/parser changes.

Residual risks remain in language parsers, hypervisors, OS/browser/GPU drivers and
the renderer. A valid GLB or no-finding review cannot certify safety. Retain the
specific evidence, scope and outstanding risks rather than a blanket secure claim.

## Rollback and incident handling

For the current source-only candidate, retain the previous source revision and
reviewed change manifest; no active skill, tenant or runtime has been changed by
these modules. Reverting source must preserve unrelated local edits. Do not
restore automatic dependency installation as an incidental rollback.

Once a real host exists, the operator first stops admissions and revokes affected
grants, then terminates workers and verifies ephemeral cleanup. Preserve bounded
receipts and incident evidence in protected storage; do not expose input data in
logs. Quarantine all outputs affected by changed input/toolchain/runtime pins.
The App engineer disposes the viewer and exposes the non-canvas information path.
Reactivation requires a reviewed prior or repaired revision with current approval
and affected qualification checks; a previous digest is not automatically safe.
These are host acceptance obligations, not implemented revocation endpoints.
