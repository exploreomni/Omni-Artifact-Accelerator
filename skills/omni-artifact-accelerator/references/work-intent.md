# Choose the artifact workflow

Start a new engagement by asking **“Are you migrating an existing artifact or building something new in Omni?”** Offer **Migrate an existing App, dashboard or report** and **Build a new artifact**. An explicit opening request counts as the answer. If a user names an existing Omni artifact to fix, continue its focused enhancement. On resume read the saved mode, treatment and stage.

For a migration ask **“Should we preserve the existing experience, or redesign it while retaining its required capabilities?”** A request to reproduce the source selects preservation. If “make it better” leaves scope unclear, show the two choices before committing to either. Record the actual answer in the private brief. A source system or a DMA Topic identifies data, not the user's intended artifact. A new App on an existing Topic is net-new development unless the user identifies an artifact to migrate.

| Work | Stage E decision | Evidence for completion |
| --- | --- | --- |
| Migrate and preserve | Review one source-matched specification with its views, controls, behavior and proposed deviations. Confirm that exact specification under the engagement's selection policy. | Map source views and controls to target destinations and verify the frozen candidate against matched source states. |
| Migrate and redesign | Review three distinct concepts against the same pinned source scope. Choose one, then resolve detailed design. | Retain the accepted source obligations across all concepts, target mappings and QA. |
| Build new | Qualify data, create a narrative and interview for the product before presenting three concepts. Resolve the selected concept before building. | Verify the chosen experience, its governed queries and original product requirements. |

### Start or resume

From the selected checkout, use the existing standard-library helper. With missing work intent it returns the question and choices. A choice prompt creates no engagement.

```sh
OAA_PROJECT=skills/omni-artifact-accelerator/scripts/analyst_project.py
python3 -I -S -B "$OAA_PROJECT" init
python3 -I -S -B "$OAA_PROJECT" init --mode migration
```

After the answer, initialize once with a private sibling directory. For redesigned migrations use `--migration-treatment redesign`. For new development use `--mode net-new` and omit the treatment. Under the strict host policy use the qualified verifier. For ordinary chat explicitly configure the conversation-evidence selection policy shown below.

```sh
python3 -I -S -B "$OAA_PROJECT" init --output "$OAA_RUN" --name 'Service reporting' \
  --mode migration --migration-treatment preserve --surface app --selection-policy conversation-evidence-v1
```

A continuation initialized from a handoff may already have a migration project with a pending treatment. From that project, record the user’s answer with `migration-select --project "$OAA_RUN" --migration-treatment preserve` (or `redesign`). Connected hosts can submit the same answer through `execution_lifecycle/migration_select` with a request containing `migration_treatment`. A repeated identical selection is safe. Existing engagements without a treatment keep their recorded workflow. Reuse the selected DMA Topic and the host's [CLI or MCP connection](omni-cli-setup.md) on either route.

### Review and build a migration

1. At A–D, identify the exact source App, dashboard or report, revision and audience. Collect authorized source definitions and state observations, verify the intended Omni Topic, analyze results, and confirm the user’s requested treatment. A screen capture can identify visible controls. Source configuration or observed changes establish which queries and outputs they affect. Keep open questions explicit.
2. Prepare the [source baseline](migration-fidelity.md) in the private engagement. For preservation, use the ordinary E `stage-record` with `{"stage":"options","migration_treatment":"preserve","evidence":{"source_baseline":"contracts/source-baseline.json"}}`. Show its views, control behavior, assumptions and deviations. Use the returned `choice_bindings["source-baseline"]` and actual user confirmation for the existing `choice` checkpoint. For redesign, add `migration_treatment: "redesign"` and the source baseline evidence to the usual three-option request. Each concept declares `migration_scope` with the baseline digest, source view IDs and retained control IDs.
3. Resolve design against the confirmed baseline. The migration experience handoff (schema version 2) records `source_baseline_path`, `source_baseline_sha256`, `view_coverage`, `control_coverage` and `quality_coverage`. Provide `treatment_coverage` for applicable selected visual treatments in preservation. Redesign also binds the chosen concept manifest. Retain target destinations and concrete control bindings through the build. A changed baseline requires review and confirmation of the changed scope.
4. During F compare default, changed, combined, reset and other material states for the frozen candidate. The QA review can attach `evidence.migration_observations`. A resolved QA review needs matching observations. Missing controls, unavailable source behavior or unobserved results remain visible to the user. A user may explicitly adapt or omit scope with retained evidence. Track native execution, effective access, visual quality and publication under their existing separate checks.

### Run the same workflow in Cursor

Open the checkout as the workspace and start from its root `AGENTS.md`. For a blind test give only the business request and authorized source material. Inspect the resulting mode and treatment, retained source coverage and QA result at the end. Use the packaged [App creation preflight](../../omni-app-engineer/references/authoring-preflight.md) for a request-format question. For an uncertain runtime event, explain the missing observation and request only its redacted evidence. A disposable native App requires its own authorization.
