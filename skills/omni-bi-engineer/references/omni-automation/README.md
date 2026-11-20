# Native Omni semantic development

These portable Automation definitions extend an installed Omni Artifact Accelerator. They support OAA alone or alongside a Data Model Accelerator handoff. Review and apply the configuration in the intended instance using the customer's existing administration workflow.

## Native configuration

| Surface | Change |
| --- | --- |
| Skills | Add [oaa-dev-semantic-router](oaa-dev-semantic-router.md) and [oaa-dev-semantic-modeler](oaa-dev-semantic-modeler.md) by their exact handles. Use each file's frontmatter as metadata and its Markdown as the body. Keep the existing coordinator, Topic handoff, UX and QA skills. |
| Agents | Create or reuse an **OAA Omni Modeler** with the agent context below. Bind actual available read, development-branch editing, validation and query tools appropriate to that role. Check the actual target origin, branch, identity and effective access. An operator can provision the modeler read-only and use the reviewed patch handoff. |
| Agent alias | If the instance uses slash alias skills, add the [manual agent alias](agent-oaa-omni-modeler.md). Select the intended **OAA Omni Modeler** in the editor/toolbox. Leave its identity and privilege scope under the operator's control. |
| Coordinator | Add the modeler to the existing Omni Artifact Accelerator's assigned agents. Add the coordinator context below as a scoped addition to its existing instructions. Select the Skill and Agent matches in the editor so their references bind to this instance's actual IDs. |
| Dual installation | An operator can bind an existing qualified modeling agent instead of deploying a second writer. Substitute that actual assigned agent reference throughout the hook and alias. Route DMA-owned changes to its existing workflow; document the owner of each object. |

**Coordinator context to add**

> During Stage A for an App or dashboard, load /oaa-dev-semantic-router and follow its ownership decision. For authorized standalone modeling dispatch /"OAA Omni Modeler" using the assigned Agent tool, with /agent-oaa-omni-modeler as its selectable alias. Resume this same engagement when it returns. Keep /oaa-dev-topic-handoff for the selected Topic and saved-query evidence. A supplied DMA handoff takes precedence over standalone authoring.

**Modeler agent context**

> Load /oaa-dev-semantic-modeler on entry. Accept a single scoped assignment from the Artifact Accelerator. Return the branch-specific Topic and supporting evidence, an exact reviewable patch, or the unresolved dependency. For an existing DMA-owned object return the change request to its owner. Call native tools only as needed for the selected route. Preserve the actual origin, model, branch, principal, source definition and policy. Report the evidence for each completed step.

On upgrade, compare owner, existing body and target identity before saving. Preserve unrelated instructions, tool assignments, visibility and existing slash references. After saving, verify the Skill lookup, the assigned Agent tool, its resolved references and a recorded child invocation. A missing skill reference and a missing write capability are different conditions. The second can still return a candidate patch.

## From a prepared candidate to a development branch

Native chat uses the verified, branch-aware tools assigned to the modeling role. An external OAA host can also prepare a branch request offline with the project command below. Both follow the same route and scope. See the [coordinator](../../../omni-artifact-accelerator/SKILL.md), [modeler](../semantic-modeler.md) and [effective-access review](../../../omni-qa-analyst/references/semantic-access.md).

The native combined-YAML API names a regular Topic file `<topic_name>.topic`. Local export paths can include folders or end in `.topic.yaml` or `.topic.yml`. For those candidates, map the reviewed source path to the native filename, reread the native baseline and regenerate the candidate and its pin. Send that exact native file to the API. [Omni model YAML filenames](https://docs.omni.co/guides/api/bulk-update-model-yaml)

1. Record the reviewed shared model, branch and operator membership. Compare the branch record's ID, `modelKind`, `baseModelId` and `connectionId` with the intended shared model. Capture combined YAML for the shared model and that branch with checksums. When creating a branch is authorized, record the returned per-model branch ID. An organization branch ID, shared model ID or workbook ID cannot substitute for it.
2. Retain the original reviewed inventories. For each raw YAML response, `semantic_branch.inventory` returns its version and a SHA-256 digest over canonical JSON containing the complete `files` and `checksums` dictionaries. Keep these original digests in the model-review evidence. For a branch request, pin them before modeling by setting the baseline’s `evidence_ref` to `sha256:` followed by the SHA-256 of the canonical JSON object `{shared: shared_summary, branch: branch_summary}` (sorted keys, compact separators, ASCII escapes). An offline candidate with a descriptive baseline reference can still be reviewed. Preparing a live-target request requires the exact original inventory pin. Before a proposed write, reread the same two inventories, identity and model ancestry. Reconcile any concurrent change with the owner. Branch-only requests use the shared model ID in the endpoint and the branch ID in the body. [Omni branch YAML procedure](https://docs.omni.co/guides/api/bulk-update-model-yaml)
3. In the private engagement prepare a pinned snapshot with kind `omni_semantic_branch_snapshot`, integer `schema_version: 1`, candidate `context`, `candidate_sha256`, and `baseline_ref` matching the candidate's `destination.evidence_ref`. Include `identity` (the actual whoami response), `models` (the shared and branch model records keyed by actual ID), `reviewed_baseline` (the two original inventory summaries keyed by `shared` and `branch`), and `current` (the two new raw combined YAML responses under those same keys). Specify the observed boolean `git_enabled` and, when enabled, a reviewed `commit_message`. A previous write attempt additionally carries `previous_attempt` with its `context`, `candidate_sha256`, `file_name` and retained `reference`. Prefer a user-scoped identity. For an explicitly authorized organization-key branch author, also include the original `branch_author` record (`kind: omni_branch_authorization`, `role: user`, exact `context`, `topic_name`, `reference` and actual `response_text`). Supply the model connection admin role and its edit/IDE permissions, plus the branch creation record with matching user ID, membership ID, connection and parent. The returned `organization_branch_author` scope supports only preparation for that branch. Obtain separate viewer-scoped evidence for artifact access. Captures are operator-supplied evidence. Keep them private.
4. Prepare the local request spec with three file pins, `route`, `candidate` and `snapshot`. Each pin has engagement-relative `path` and an exact file-byte SHA-256. The project command rebuilds the candidate against its current route and checks its branch before producing a fixed request body. A prepared request has no execution authority.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py semantic-model \
  --project /absolute/private-engagement --operation branch-plan \
  --request contracts/branch-request.json --output contracts/branch-plan.json
```

5. An authorized model operator reviews the file, branch, rollback and planned request. For a current, reviewed `prepared_for_review` result, use its exact `requests[0].body` as JSON stdin to the qualified `omni -p PROFILE models yaml-create SHARED_MODEL_ID --body -` operation on that same origin. Coordinate exclusive branch editing where the transport cannot enforce a conditional write. For `unchanged` proceed to readback. For `reconcile_prior_attempt` first compare the branch and shared inventories to the original before/after expectations, including normalized native YAML. A different or indeterminate result stays open. Keep the earlier attempt and its readback before considering a newly approved action.
6. Re-read both complete inventories. Check the expected scoped change and that the shared baseline is intact. Validate both the branch model and any affected saved consumers. Read the exact regular Topic and run the independent total, grouped slices and intended access cases on this branch. The CLI operations below illustrate the applicable read surfaces. Use the installed CLI's help and an already-qualified profile to verify the available flags. Keep separate outcomes for model validation, numerical evidence, viewer access, document controls, and render. [Validate model](https://docs.omni.co/api/models/validate-model) · [Validate content](https://docs.omni.co/api/content-validator/validate-content)

```sh
omni -p PROFILE models yaml-get SHARED_MODEL_ID --mode combined --includechecksums true
omni -p PROFILE models yaml-get SHARED_MODEL_ID --branchid BRANCH_ID --mode combined --includechecksums true
omni -p PROFILE models validate SHARED_MODEL_ID --branchid BRANCH_ID
omni -p PROFILE models get-topic SHARED_MODEL_ID TOPIC_NAME --branch-id BRANCH_ID
omni -p PROFILE query run --body - < reviewed-branch-query.json
```

## Instance qualification

In an authorized private development destination, start a fresh chat with the Artifact Accelerator and an ordinary request over existing physical data. Confirm a suitable Topic reuses the model with zero model writes. For a confirmed missing Topic, select the Omni-only lane, observe the modeler invocation and verify one branch-only change. Give a separate run a DMA-owned Topic with a missing metric and confirm the scoped request returns to DMA. Check the actual branch query outcome and restricted-viewer evidence for each supported surface. Record a read-only host's exact patch handoff and its verification after an operator returns the branch readback. Record host/tool versions and outstanding access limitations. A software fixture, a deployed instruction body and a live customer-identity check support different claims.
