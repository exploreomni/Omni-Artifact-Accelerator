# Testing and contribution checks

Use the [package-use policy](../skills/omni-artifact-accelerator/references/dependency-policy.md) before every runtime/import path. No automatic installation or unapproved imports. The current manual CI workflow records the selected revision only; **it does not run code validation**. A dependency-backed CI job remains disabled until its host-enforced human approval gate is qualified. Existing remote required-check settings are not changed by this source work.

For source-only package review with an existing Python runtime:

```sh
python3 -I -S scripts/check_package.py
```

For the maintained security lane, use the same existing interpreter with bytecode writes disabled:

```sh
python3 -I -S -B scripts/validate_source.py
```

This runs a fixed set of package, CLI environment/output, App resource, file/CSV intake and public-denial checks in isolated Python startup mode. It refuses ordinary imports outside the standard library or the explicitly reviewed first-party harness. Explicit first-party file loading still trusts the checkout; this is not a sandbox for hostile source. Children receive a minimal environment and bounded output/deadlines. No YAML decoder, producer engine, vendor CLI, browser, live tenant or package manager is invoked. The original synthetic fixtures include early parser rejection and valid-input controls.

Use `--report /absolute/private/output/source-check.json` for a new report outside the repository. It records exact source hashes, per-check results, interpreter identity and separate unqualified host/native/rendered outcomes. It does not overwrite an existing receipt. Failed checks or source drift produce a nonzero exit. Run affected cases first during repair; repeat the complete lane when integrating changes to these boundaries. See [security operations](SECURITY.md) for pending CI and host activation gates.

The checker uses a narrow scalar metadata profile and the standard library, not a general YAML parser. It checks declared skills, metadata, local links and excluded files; it does not authenticate approvals or scan all secrets. The full historical suite loads optional PyYAML/source engines and must not be run without scoped approval. Do not interpret historical commands below as authorization to install or load dependencies.

For the new original spatial implementation, run only the focused synthetic checks:

```sh
python3 -I -S tests/test_spatial_core.py -v
python3 -I -S tests/test_spatial_boundary.py -v
python3 -I -S -m unittest discover -s tests -p test_install.py -v
env -u NODE_OPTIONS -u NODE_PATH node tests/test_spatial_controller.js
env -u NODE_OPTIONS -u NODE_PATH node tests/test_spatial_viewer.js
```

These require only the existing runtimes, their standard libraries and reviewed first-party files. They do not open a browser or process customer models. Installer tests exercise copy/rollback mechanics in temporary fixtures; the public activation path remains blocked. Core tests verify independently derived geometry expectations. Controller/parser doubles are not evidence of rendered WebGL, GPU limits, native callbacks, screen-reader behavior or host isolation.

The [harness qualification contract](../harness/SECURITY.md) identifies those outstanding gates. Broaden checks only for changed behavior, failures or remaining integration concerns; no test run installs missing dependencies.

## Report foundation checks

Use `python3 -I -S -B scripts/validate_source.py --case report-contract` and
`--case report-routing` for changed report contracts and routing. They cover
physical page bounds, field/parameter/section references, output obligations,
retained evidence, distinct report targets, one-page lifecycle coverage and A–F
build gates. The `experience-contract` case checks shared concept/handoff behavior.
These source-only checks do not render, load an engine, call native Reports APIs
or certify print/PDF/Excel fidelity. Keep that qualification explicit.

## Experience-context checks

The `stage-gates` and `stage-gate-integration` source cases cover A–F ordering,
exactly three options, host-verifier absence/revocation, stale evidence, role/output
bypasses, automatic candidate freezing, candidate-bound reviews and interrupted
commit recovery. The `conversation-choice` case checks actual-response record shape,
exact option binding, explicit policy adoption, evidence freshness and design/review
ordering. `native-stage-gates` also proves conversation mode cannot reach the
three legacy native mutation transports. Synthetic host providers stay in tests. Passing these cases does
not qualify a production host, prove that evidence claims are true or constrain
agents with unrestricted access outside the guarded entrypoints.

For a focused experience-context change, start with `test_design_intent.py`, `test_design_review.py` and `test_project.py` using the same discovery command with `-p <filename>`. They cover selected decisions reaching motion/storytelling handoffs, pending choices, stale visual inputs, legacy projects and the separation of source evidence from native requirement fulfillment. Installer checks are relevant when validating an upgrade. Broaden testing when changed behavior or a failure warrants it; prose-only changes need metadata/link and affected-example checks rather than unrelated migration runs.

The context cases also exercise resume after a new selection, changed registered/unregistered inputs, explicit runtime/alias dependencies, a usable-height capture mismatch, legacy packets without the optional derived index, and the existing path/size boundaries. `packet-check` verifies declared bytes and decisions; it cannot discover arbitrary nested file references or authenticate source evidence. For a native input repair, independently provide the selected callback shape and exercise the assembled candidate; an export-shaped fixture or simulated callback cannot establish native runtime behavior. For presentation aliases, compare exact-key coverage and keyed totals/partitions before and after application, including duplicate display names and a changed/missing identity.

For a substantial skill change, an independent bounded rehearsal can use a different domain, a realistic request and minimal synthetic source files in a private output directory. Give the evaluator the request and relevant skills without prescribing the expected answer. Inspect the actual saved decisions and handoffs for transfer of context. A rehearsal without rendering or native execution cannot establish visual polish, live behavior or user acceptance; the original [context studio](../skills/omni-design-systems/references/experience-context-studio.md) remains a teaching specimen, not a qualification result.

## Native procedural scene checks

Run the focused first-party source lane with the existing Node runtime:

```sh
env -u NODE_OPTIONS -u NODE_PATH node --test tests/test_native_scene_geometry.js tests/test_native_scene_session.js tests/test_native_scene_integration.js
```

It checks geometry winding/normal/UV and independent dimensional expectations;
whole-scene input/geometry/texture/backing budgets; initialization failure/retry
and late-result disposal; independent sessions; interruption/visibility/reduced
motion; exact query identity, supersession, stale/partial/restricted state; host
observer cleanup; and renderer protocol/resource ownership with original doubles.
The geometry file reports its own focused case count within one Node file case.
No third-party engine, browser, native query or live asset is loaded. These are
source/math/controller checks, not shader compilation or actual WebGL results.

Keep a source-pinned receipt outside the repo. Before native qualification,
approve exact renderer bytes/closure and verify the target loading/resource path
with a tiny candidate. Exercise responsive space, context-loss recovery, actual
selection/return, accessible controls and exact native callback/access behavior.
Do not treat passing doubles as that evidence. Freeze raw pilot briefs and
prompt categories before rehearsals; label source-only worker results and
unobserved customer corrections honestly. See the
[framework guide](../skills/omni-app-engineer/references/native-scene-framework.md#transfer-and-evidence).

## Control craft checks

For changes to search, native choices, control state or the optional query fields, run `python -m unittest discover -s tests -p test_control_primitives.py -v`. These cases exercise bounded text, composition and clear deduplication, out-of-order results, retry against a newer draft, atomic restoration, cancellation and disposal. They also execute both original [control studio](../skills/omni-app-engineer/assets/control-studio.html) structures with a minimal DOM and controlled timers. Keep the legacy controller case in `test_hex_app.py` when changing `query_controller.js`; preserving its event shape matters to existing callers.

For an actual App, check the assembled candidate's affected search/filter/inspect/return flow, including listener cleanup, stable selection and the selected theme's CSS cascade. Pin the source and candidate bytes. A shared helper passing in isolation cannot establish that the host uses it correctly. Review semantic token overrides and selector precedence together so example colors cannot silently override a customer theme. Recheck the same failed path after correction, rather than adding unrelated tests.

Use [control craft](../skills/omni-design-systems/references/control-craft.md) to review task fit, native dashboard limits, migration fidelity, page columns versus table columns, and supplied-result scope. A design exercise or DOM double cannot qualify real keyboard/focus behavior, responsive rendering, screen readers, native query callbacks or usability. Record those outcomes separately. Course completion is optional and is never a release requirement.

## Optional producer compatibility tests

Use an inspected, trusted checkout. These tests load upstream code and its maintained fixtures, so do not point the variables at customer projects or arbitrary downloaded repositories.

For the [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator), use a Python environment with that checkout's required YAML and SQL dependencies:

```sh
OMNI_ANALYST_DMA_CHECKOUT=/absolute/trusted/Data-Model-Accelerator \
  python -m unittest discover -s tests -v
```

The declared DMA producer contract was exercised at `c513474e87af9c2c31deebd2ae675c8602955203`. Check compatibility before changing producer revisions. See [parser coverage](parser-coverage.md) for the distinct accepted formats.

Sigma compatibility needs its separately obtained engine environment and visual-capture extension, including `test_sigma_visual_capture.py`. The extension is not included in this repository or implied by the base revision alone. Importing supplied Sigma artifacts remains available without it.

```sh
OMNI_ANALYST_DMA_CHECKOUT=/absolute/trusted/Data-Model-Accelerator \
OMNI_ARTIFACT_SIGMA_CHECKOUT=/absolute/trusted/SigmaMigrationAgent \
OMNI_ARTIFACT_SIGMA_PYTHON=/absolute/trusted/SigmaMigrationAgent/.venv/bin/python \
  python -m unittest discover -s tests -v
```

Use the final test summary to distinguish passed, failed and skipped cases. The optional suites exercise actual producers behind synthetic transports; they do not establish live source completeness or tenant acceptance.

## Before proposing a change

1. Keep changes focused on the skill, helper or contract being changed. Preserve source IDs, original evidence and unresolved behavior.
2. Run the relevant tests and package checker. Broaden to the local suite for cross-cutting executable changes or unresolved regressions; run optional producer tests when changing a producer bridge and the trusted dependency is available.
3. Document changed setup or contract behavior in the maintained run guide. Use synthetic examples; keep customer evidence, credentials, generated engagements, internal plans and release archives outside this repository.
4. Describe what changed and the actual checks performed. Identify any skipped producer or native verification explicitly.

Local checks, candidate readback, native rendering/query behavior, effective access, business acceptance and publication are separate outcomes. A passing test suite does not authorize source execution or a target write.

## First-delivery checks

`test_experience_quality.py` covers requirement-based routing, declared runtime dependency invalidation, provisional/incomplete destination coverage, CLI status and assigned/legacy packet compatibility. `test_experience_components.py` exercises the reusable local primitives and the synthetic lab using explicit simulated inputs; it does not render or verify Omni. Installer tests cover read-only parity and preservation of customizations. Run affected checks first; cross-cutting helper integration warrants the relevant affected suite after verifying its imports are authorized.

For behavioral qualification, use fresh-context workers on a few contrasting raw briefs and synthetic artifacts. Capture the candidate and actual decisions rather than matching headings. Keep private rehearsal outputs outside the repository. Distinguish the installed files exercised, source/local behavior, actual host rendering and customer acceptance; do not claim Claude/ChatGPT portability from a single host run.

## Product intent and premium experience transfer

For the additive [product-intent workflow](../skills/omni-artifact-accelerator/references/product-intent.md),
run the focused original-source case after its implementation is stable:

```sh
python3 -I -S -B scripts/validate_source.py --case product-intent
```

Assess the helper's boundaries: optional legacy behavior, valid priority/provenance,
private note pins without automatic disclosure to other roles, generated projection
receipts/recomputed bytes, stale selection or edited notes/brief, repair-only
product-owner handoff, unresolved discovery, current packet context and independent
creative-review ownership. These checks establish structural behavior,
not expert judgment, product fit, actual host dispatch or aesthetic competence.

Use bounded behavioral cases that expose those differences:

| Case | Meaningful acceptance evidence |
| --- | --- |
| Short ambiguous premium request | Material clarification or a defensible working proposal; no forced questionnaire or invented user decisions. |
| Existing answers / focused repair | Reuses current intent, closes relevant no-logo/supplied-brand questions and avoids another discovery ceremony. |
| New preference on resume | Preserves historical decisions, selects the revised intent and propagates only current context. |
| Edited North Star or notes | Detects stale evidence, treats edits as proposals and regenerates from reconciled canonical intent. |
| Unsupported requested method | Preserves the intended outcome, compares feasible treatments and retains the remaining gap; no silent scope reduction. |
| Demanding fresh experience brief | First slice embodies the supplied experience promise; exact first/final artifacts receive distinct product-fit, creative and correctness findings. |

Withhold historical implementations and expected layouts from fresh workers, but
retain the user's actual quality requirements and benchmark qualities. Include a
different actual creative reviewer from builder and originating designer. Inspect
the candidate and decisions, not keywords or component counts. Under no-render
constraints, repair observable source omissions and leave aesthetic acceptance open.

Record material clarification, repeated questions, correction of supplied requirements,
new preference/scope and internal revision separately. Include whether any actual
user feedback occurred. A synthetic run with no customer messages cannot establish
zero customer correction, satisfaction or premium first delivery. No test authorizes
active installation, browser workarounds, new dependencies or publication.

## Reusable experience mechanics

`test_experience_assembly.py` checks actual local assembly from independently structured authored shells, source hashes, order/collision declarations, inert input handling, output budgets and non-overwrite behavior. `test_experience_behaviors.py` exercises the actual headless controllers and the original example's selected journey under a stated local harness. `test_design_review.py` checks reasoned direct versus comparison exploration without weakening candidate-bound craft evidence. Run focused cases during implementation and relevant integration checks within approved dependency scope.

A shared mechanism should preserve identity, values and recovery in different presentations. Fresh-domain qualification must supply the raw brief and inputs without an expected layout. Evaluate task fitness and implemented behavior; color changes, similarity thresholds or novelty quotas cannot establish design flexibility. Local/controller checks do not establish rendered polish, native integration or human usability.

## Whole-experience review and qualification

Newly frozen reviews derive their destination/context/lane and journey obligations from the current selected design and intent, before considering submitted evidence. `test_destination_coverage.py` and the existing design-intent/review cases cover missing secondary destinations, wrong binding/context/target, exercised transitions versus still captures, matching correction retests, exact-byte staleness, shared numerical evidence, justified exclusions, historical reads, focused scope and faithful migrations. All fixture observations are explicitly synthetic declarations; their passing results test the checker, not the quality of an App.

Exercise the existing CLI case-generation and check/verify paths as part of these focused checks. `experience-check` remains structural. A historical complete review without destination bindings remains readable and unassessed at the destination level; a new freeze cannot opt into that behavior by omitting fields.

For a material qualification run, use three original raw briefs sequentially: an exploration App, a native operational dashboard, and a constrained migration/investigation. Retain one unseen holdout until the package is stable. Supply typed source data and independently derived expectations without a proposed layout. In installed mode, verify installed/source parity; in a repository-only blind trial, retain the checkout manifest without consulting installed copies. Record which actual files the host read. Discover permitted observation routes; a dashboard must not become custom App HTML to obtain a preview, and a headless browser must not bypass a browser restriction.

Store brief/message references, source/helper/candidate hashes, initial and internally reviewed candidates, findings, corrections and matching retests outside the package. Track material clarification batches, repeated questions, customer corrective prompts, new scope and internal revisions separately. No customer follow-up in a synthetic run means customer correction/acceptance is unobserved, not evidence of zero real-world corrections. Report source/local execution, rendered craft, native behavior and participant evidence separately, including blocked observation routes. A failed or unavailable visual lane cannot be repaired by more unit tests.
# Execution workflow qualification

The startup and delivery helpers are local consistency checks. A repository link,
host instruction file or passing fixture does not qualify Claude, ChatGPT or Codex
execution. Keep a per-host record of source revision/dirty manifest, actually read
guidance, available tools, action constraints and the candidate evaluated.

Run only the affected original-source cases with the existing interpreter:

```sh
python3 -I -S -B scripts/validate_source.py --case workflow
python3 -I -S -B scripts/validate_source.py --case native-query
python3 -I -S -B scripts/validate_source.py --case native-authoring
python3 -I -S -B scripts/validate_source.py --case native-create
python3 -I -S -B tests/test_native_input_handoff.py -v
python3 -I -S -B scripts/validate_source.py --case assembly
python3 -I -S -B scripts/validate_source.py --case metadata
```

These cover role-stage compatibility, startup/brief drift, responsibility coverage,
candidate preservation, stale evidence, native field/population contracts, NULLs,
caps and independent expectations. None loads a renderer or connects to Omni. Do
not run additional dependency-backed checks without the required exact sign-off.

The authoring cases cover empty/invalid CLI transport, command inventory, nested
query envelopes, explicit catalog drift, missing metadata, and existing-App
HTML-only preparation/readback for supplied organization/user identities. The
new-App cases check frozen HTML/specification binding, all four reviews, fixed
new-document routes, locked settings, model/Topic distinction, tamper rejection
and exact supplied-capture comparisons. They contain no live transport or approval
provider; creation/publication and native behavior require separate evidence. The
handoff cases run separately with the existing Node runtime on PATH (the bounded
Python security lane intentionally strips that host PATH). They use original package sources to check
qualified numeric strings, grain, refresh/run/subscription semantics, failure
clearing, ordered return, focus fallbacks and per-context choices. These doubles
do not qualify a native SDK or a rendered interaction. Source-inventory,
annotation-projection, optional specialist and unobserved-evidence template cases
remain in the workflow lane; actual creative observations stay separate.

Qualify behavior with two contrasting original briefs and minimal typed inputs,
then an unseen holdout after concrete findings are repaired. Useful categories are
a lifecycle investigation, a branded partial-data exploration, and an operational
dashboard or faithful migration. Supply no expected layout or previous generated
app. Use different domains; a color swap or similarity score is not design freedom.
For a native dashboard, keep native specifications and candidates distinct from
custom HTML. If the allowed tools cannot create native content, report that gap.

Freeze the first candidate bytes before critique and retain the internally reviewed
revision. Compare the original request independently. Record clarification batches,
repeated questions, dropped requirements, corrective prompts, internal findings and
matching retests separately from scope changes. Targets are zero silent omissions,
zero repeated questions and at most one material initial question batch where
feasible, not guarantees. Unavailable human feedback is unobserved, not a zero.

Maintain separate host results: source-only rehearsal, real native callback,
rendered critique at relevant width/height, effective principal access, publication
readback and human acceptance. A CLI-only trial must not invoke a headless browser.
If Claude/ChatGPT access, approved dependencies or rendering is unavailable, retain
the runnable qualification procedure and mark those milestones pending.

Before release, reconcile all selected changes with the starting dirty manifest,
review the exact diff, run affected checks and verify package metadata/links. Preserve
preexisting work. Follow current publication authorization; implementation is not a
request to activate installed skills or push a release. After an authorized release,
verify the published SHA; compare installed copies only in an authorized installed
workflow. Never claim a disabled CI job ran validation.

## MicroStrategy migration checks

The source-only runner exposes `microstrategy-capture`, `microstrategy-projection`,
`microstrategy-mcp`, `microstrategy-host` and `microstrategy-integration`. Use the
[run guide](../skills/omni-artifact-accelerator/references/microstrategy-visual-run.md)
for current supported shapes and qualification limits. Native-shaped projection
fixtures validate documented contracts; injected transport state fixtures test
fail-closed host behavior and do not certify a deployed server's response shape.
Keep original scope/pin, prompt/filter, precision/pagination, credential/redirect,
uncertain execution, A–F, DMA and separate target-surface checks focused.

## Cognos source-only checks

Run the fixed `cognos-projection`, `cognos-host` and `cognos-integration` cases
through `python3 -I -S -B scripts/validate_source.py --case CASE`.
Save any logs outside the checkout. Original synthetic XML exercises bounded
parsing, scope/identity preservation, local MCP import, path rejection, A–F
routing, projection drift and DMA handoff. Numeric comparisons must not pass
from matching unqualified files. These checks neither execute Cognos nor verify
actual report rendering, dashboard compatibility or effective tenant access.

## BusinessObjects source-only checks

Use `python3 -I -S -B scripts/validate_source.py --case NAME` with
`businessobjects-projection`, `businessobjects-capture`, `businessobjects-host`,
`businessobjects-integration` and `metadata`. These use original neutral fixtures
and the existing standard library; no SDK, browser, source or target tenant.

Check independent source denominators and hashes, repeated placements/provider
contexts, version/profile limits, malformed XML/JSON and credential handling,
operation-aware denial and journal resume boundaries, precise normalization,
state-bound comparisons, source-pinned routing, A–F enforcement, DMA route
restrictions and native-reuse obligations. A successful local result establishes
only those checks. Preserve pending real-source access, provider completeness,
Universe security, Crystal fidelity, native rendering and acceptance evidence.

## Report migration qualification

Run affected fixed cases `report-contract`, `report-routing`, `report-native`,
`rdl-report`, `crystal-report`, `report-source-capture`, `report-source-host` and
`report-source-integration`, followed by `metadata`. Fixtures are neutral and
original. They exercise explicit requirement mappings, A–F denial, restricted
source scope, inert XML/extraction, original-byte tamper rejection, state-bound
precision-preserving comparisons and distinct Report delivery.

They do not authenticate supplied observations, execute a source query or native
Report API, decode Crystal binaries, render PDF/XLSX, prove effective tenant access
or establish production acceptance. Keep live pilot results outside the repo;
record actual versions, allowed/denied principals, empty/large data, parameter
defaults/null/blank/multivalue, group totals, page overflow, PDF pagination and
Excel row/type/sheet fidelity against independent original evidence.
