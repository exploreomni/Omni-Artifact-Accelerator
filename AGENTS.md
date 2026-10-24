# Project execution boundaries

For substantial Omni artifact creation/redesign/migration, enter through
[the orchestrator](skills/omni-artifact-accelerator/SKILL.md) and its
[execution procedure](skills/omni-artifact-accelerator/references/execution-workflow.md).
Repository maintenance and focused repairs do not require a new artifact engagement.

Follow the workspace instructions and the [dependency policy](skills/omni-artifact-accelerator/references/dependency-policy.md).

- Never install, import/load, vendor, update or activate a third-party package, library, skill, runtime image or decoder without Austin's explicit sign-off covering that exact action and dependency closure. Prior availability is not approval. This applies to local tools, subagents, CI, MCP and browser/CDN imports.
- An implementation or push request does not authorize dependency acquisition or activation. Prepare the exact reviewable request first. Do not auto-repair missing dependencies.
- No Blender code, APIs, scripts, add-ons, copied node setups, dependencies or `.blend` processing. Conceptual learning is not implementation provenance.
- Source review and original first-party code using the existing runtime's standard library may proceed in scope. Use Python `-I -S` for source-only checks so site packages/startup hooks are not imported. Do not run the full dependency-backed suite until authorized.
- The optional spatial harness accepts declarative data. No arbitrary generated scripts, package names, plugin loading, tenant credentials or network access in a modeling worker. No host fallback when isolation is unavailable.
- An agent-writable file, boolean or approval reference cannot confer authority. Production execution and active skill installation remain disabled until a trusted host gate is qualified.
- Keep runtime, security, numerical, visual and native qualification distinct. Source checks and synthetic fixtures cannot certify isolation or visual quality.
- Preserve the user's CLI/API-only constraint. No browser/headless-render workaround. No live app changes or push without corresponding authorization.

Planning documents, customer assets, real query results and release archives belong outside this repository. Maintain useful product instructions and original fixtures inside it.
