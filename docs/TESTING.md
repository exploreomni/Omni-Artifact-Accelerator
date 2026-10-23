# Testing and contribution checks

Run these commands from the repository root in the Python environment created during [setup](../README.md). Python 3.12 and Node.js 22 are used in CI. The native adapters and local MCP host require a POSIX system such as macOS or Linux.

```sh
python -m pip install -r requirements.txt
python scripts/check_package.py
python -m unittest discover -s tests -v
```

`check_package.py` checks declared skills, metadata, local documentation links and excluded repository artifacts. It is not a general secret scanner or an approval authenticator. The tests use synthetic fixtures and mock source/Omni transports. No customer credentials, live service connection or Omni CLI login is needed. Node.js is required for the App controller and template tests. Some older cases skip when Node is absent; the reusable behavior checks fail with an explicit runtime requirement.

The normal test run also skips optional integration cases that require separately obtained source engines. CI runs this self-contained configuration; a green job does not mean every optional producer was tested.

## Experience-context checks

For a focused experience-context change, start with `test_design_intent.py`, `test_design_review.py` and `test_project.py` using the same discovery command with `-p <filename>`. They cover selected decisions reaching motion/storytelling handoffs, pending choices, stale visual inputs, legacy projects and the separation of source evidence from native requirement fulfillment. Installer checks are relevant when validating an upgrade. Broaden testing when changed behavior or a failure warrants it; prose-only changes need metadata/link and affected-example checks rather than unrelated migration runs.

The context cases also exercise resume after a new selection, changed registered/unregistered inputs, explicit runtime/alias dependencies, a usable-height capture mismatch, legacy packets without the optional derived index, and the existing path/size boundaries. `packet-check` verifies declared bytes and decisions; it cannot discover arbitrary nested file references or authenticate source evidence. For a native input repair, independently provide the selected callback shape and exercise the assembled candidate; an export-shaped fixture or simulated callback cannot establish native runtime behavior. For presentation aliases, compare exact-key coverage and keyed totals/partitions before and after application, including duplicate display names and a changed/missing identity.

For a substantial skill change, an independent bounded rehearsal can use a different domain, a realistic request and minimal synthetic source files in a private output directory. Give the evaluator the request and relevant skills without prescribing the expected answer. Inspect the actual saved decisions and handoffs for transfer of context. A rehearsal without rendering or native execution cannot establish visual polish, live behavior or user acceptance; the original [context studio](../skills/omni-design-systems/references/experience-context-studio.md) remains a teaching specimen, not a qualification result.

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

`test_experience_quality.py` covers requirement-based routing, declared runtime dependency invalidation, provisional/incomplete destination coverage, CLI status and assigned/legacy packet compatibility. `test_experience_components.py` exercises the reusable local primitives and the synthetic lab using explicit simulated inputs; it does not render or verify Omni. Installer tests cover read-only parity and preservation of customizations. Run affected checks first; cross-cutting helper integration warrants the repository's self-contained suite once.

For behavioral qualification, use fresh-context workers on a few contrasting raw briefs and synthetic artifacts. Capture the candidate and actual decisions rather than matching headings. Keep private rehearsal outputs outside the repository. Distinguish the installed files exercised, source/local behavior, actual host rendering and customer acceptance; do not claim Claude/ChatGPT portability from a single host run.

## Reusable experience mechanics

`test_experience_assembly.py` checks actual local assembly from independently structured authored shells, source hashes, order/collision declarations, inert input handling, output budgets and non-overwrite behavior. `test_experience_behaviors.py` exercises the actual headless controllers and the original example's selected journey under a stated local harness. `test_design_review.py` checks reasoned direct versus comparison exploration without weakening candidate-bound craft evidence. Run focused cases during implementation and the repository suite for integration.

A shared mechanism should preserve identity, values and recovery in different presentations. Fresh-domain qualification must supply the raw brief and inputs without an expected layout. Evaluate task fitness and implemented behavior; color changes, similarity thresholds or novelty quotas cannot establish design flexibility. Local/controller checks do not establish rendered polish, native integration or human usability.

## Whole-experience review and qualification

Newly frozen reviews derive their destination/context/lane and journey obligations from the current selected design and intent, before considering submitted evidence. `test_destination_coverage.py` and the existing design-intent/review cases cover missing secondary destinations, wrong binding/context/target, exercised transitions versus still captures, matching correction retests, exact-byte staleness, shared numerical evidence, justified exclusions, historical reads, focused scope and faithful migrations. All fixture observations are explicitly synthetic declarations; their passing results test the checker, not the quality of an App.

Exercise the existing CLI case-generation and check/verify paths as part of these focused checks. `experience-check` remains structural. A historical complete review without destination bindings remains readable and unassessed at the destination level; a new freeze cannot opt into that behavior by omitting fields.

For a material qualification run, use three original raw briefs sequentially: an exploration App, a native operational dashboard, and a constrained migration/investigation. Retain one unseen holdout until the package is stable. Supply typed source data and independently derived expectations without a proposed layout. Verify installed/source parity first, then record which actual files the host read. Discover permitted observation routes; a dashboard must not become custom App HTML to obtain a preview, and a headless browser must not bypass a browser restriction.

Store brief/message references, source/helper/candidate hashes, initial and internally reviewed candidates, findings, corrections and matching retests outside the package. Track material clarification batches, repeated questions, customer corrective prompts, new scope and internal revisions separately. No customer follow-up in a synthetic run means customer correction/acceptance is unobserved, not evidence of zero real-world corrections. Report source/local execution, rendered craft, native behavior and participant evidence separately, including blocked observation routes. A failed or unavailable visual lane cannot be repaired by more unit tests.
