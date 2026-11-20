# Develop an Omni Topic for an App or dashboard

Use this lane when warehouse relations already exist and the user chooses Omni-only semantic work. An analyst can bring existing metrics and security definitions from a source tool or start with just the business question. Keep the existing engagement, narrative, design interview and release process.

1. Check for a supplied DMA continuation or semantic review before doing any standalone work. Import it through the [existing handoff](../../omni-backend-handoff/references/dma-continuation.md). The selected branch, domain, unresolved items and model owner remain authoritative. Return missing metrics, joins or security via [cowork](../../omni-backend-handoff/references/cowork-contract.md).
2. Otherwise inspect the current connection, model, branch, available Topics and the caller's actual visibility. Compare grain, available measures, fixed filters, and audience. Reuse a suitable Topic. If visibility is limited, resolve access. If data is ready and no suitable Topic exists, offer a scoped development-branch Topic. Obtain an attributable choice before creating or extending model definitions. Return a missing warehouse relation or upstream transformation as a portable request.
3. Ask who may discover or open the content, which fields and rows each audience may see, and which controls viewers can change. Reuse existing grants and group mappings. If changes are needed, return a scoped proposal to the model or content owner. Record the operating principal separately from intended viewers.
4. The BI engineer uses the [bounded modeler](../../omni-bi-engineer/references/semantic-modeler.md) and the relevant source specialist. Retain source IDs, definitions and reviewed target mappings. Qualify each operation and source adapter separately. Draft one regular Topic against existing physical views. Production merge, document publication, user attribute provisioning and sharing have their own authorization.
5. After the owner applies the branch change, collect its original readback, model validation, independent total and sliced results, and audience checks. At A pin the actual Topic. At B bind every saved query, panel and control to it. At F check the delivered document and controls under the intended identities. With limited host capabilities return the prepared change, exact target and pending checks, then resume the same engagement.

## Project and host commands

From the installed orchestrator skill or its checkout, start an engagement with the additional lane option. Existing App/dashboard engagements can adopt the lane by recording their first route. Use fresh versioned input paths under the private engagement for new evidence.

```sh
python3 -I -S -B scripts/analyst_project.py init --output /absolute/new-engagement \
  --name "Operations review" --mode net-new --surface app --modeling-lane omni-only
python3 -I -S -B scripts/analyst_project.py semantic-model --project /absolute/new-engagement \
  --operation route --request inputs/discovery-v1.json
python3 -I -S -B scripts/analyst_project.py semantic-model --project /absolute/new-engagement \
  --operation candidate --request inputs/candidate-v1.json --output contracts/topic-candidate-v1.json
```

The local MCP tool is `semantic_model_prepare` with `operation`, `request` and an optional `output`. It shares the CLI handlers. A host supplies observed records and retains the original bytes. A pin in these contracts is `{"path":"evidence/filename.json","sha256":"<SHA-256 of file bytes>"}`. The returned pin identifies a private output. Repeated identical operations reuse the receipt. Preserve earlier inputs when preparing a newer version. The native Agents and Skills mapping is separately [included in the skill bundle](../../omni-bi-engineer/references/omni-automation/README.md).

| Operation | Input and result |
| --- | --- |
| `route` | Discovery shape below. Returns a pin to a numbered route. Supply the prior route pin in `previous` to supersede it. A pending decision or incomplete inventory keeps the user in discovery. For a DMA-bound engagement it returns the existing owner directly. |
| `governance` | `{route, policy_request}` pins a proposed [access plan](../../omni-qa-analyst/references/semantic-access.md). It can identify reusable rules and prepare model or document grant proposals for the owner. |
| `candidate` | `{route, definition}`. The definition follows the [v1 modeler](../../omni-bi-engineer/references/semantic-modeler.md). The coordinator attaches the original inventory baseline. For translation add `source_scope` pointing to `{inventory,reference,required,deferred}`. Required source asset keys plus explicitly deferred keys and reasons must cover the entire scoped input. A required unmapped item blocks the candidate. |
| `branch-plan` | `{route,candidate,snapshot}` pins the candidate wrapper and the branch preflight. Returns reviewed per-file requests or a reconciliation state. Use the native host's branch workflow or give the change to a model owner. |
| `verify` | Run the [model and audience evidence checks](../../omni-qa-analyst/references/semantic-access.md) before binding. Retain status for each tested or unavailable case. |
| `access` | Same verification spec with `kind: omni_modeling_access`, `observation` and the explicit list of usable `fields`. When the model checks pass, record this receipt as Stage A's `data`, the observation as `user_access`, and the actual viewer's membership as `user_identity`. |
| `queries` | Use `kind: omni_topic_consumer_plan`, schema 1, the Stage A access pin and each document-scoped consumer and control. The shape is the existing [Topic-first Stage B contract](../../omni-backend-handoff/references/topic-first.md#stage-b-map-consumers-and-surface-gaps-before-design). Bind the resulting receipt as Stage B's `queries`. |
| `panels` | Use the existing Topic-first App panel contract to bind the selected saved queries to rendered consumers in the exact HTML. Desktop, phone, drill and export evidence remain scoped to the actual surface. |
| `delivery` | After freezing the artifact, supply `{access,queries,artifact_sha256,checks}`. Reuse the Stage A model policy and attach any later document-specific supplement. The document and control coverage must match the selected consumers. The command saves a fixed receipt for that artifact revision. The release check replays it. |
| `gap` | For a confirmed upstream dependency, supply `{route,requirements}`. The latter pins a scoped `analyst_backend_request_spec` with affected assets, metrics and independent expectations. Pass the returned spec through the normal cowork request command. |

### Discovery and evidence shapes

Use `kind: omni_modeling_discovery`, schema 1, `topic_name`, `context`, `inventory` pin, optional `choice`, `source_inventory` and `previous` pins. Context carries `base_url`, shared `model_id`, nullable `branch_id` and `workbook_model_id`, intended `principal_id` and optional `model_version_id`.

The `omni_modeling_inventory` carries that context, `connection_id`, pinned raw `identity` and `models`, full observed `topic_names`, `complete`, `model_visibility` (complete or limited), `physical_status` (ready, missing or unknown), and `suitability` keyed by Topic with `status` (suitable, unsuitable or unknown) and `reason`. Attach a scoped modeling `baseline` pin for authoring. A complete read requires visibility across the model. For an authorized organization credential, also attach a `branch_author` pin identifying a scoped branch edit. It may establish branch authorship under the specific host checks. Effective viewer evidence uses the viewer's own context.

An attributable choice carries `role: user`, `reference`, `response_text`, `context`, `topic_name` and `action` (reuse_existing, translate_semantics, create_topic, extend_topic or defer). If the development branch still needs to be created, retain the initial choice as interview history, then bind the actual resolved destination and authority on the next route. Existing Topic updates are limited to additive, reviewed changes with exact source bytes. Do not broaden a policy or overwrite another owner's changes.

For `verify` or `access`, supply `route`, `checks`, and one of the following:

- **Existing Topic:** its full original resolved response fingerprint in `topic_response_sha256`.
- **Authored Topic:** `candidate` and `application` pins. The application record has `kind: omni_branch_file_readback`, the verified `context`, branch model ID in `model_id`, candidate digest, `source_ref`, and `yaml_response` pointing to the native combined response with `version`, `files` and `checksums`. Name the digest `candidate_sha256`. Local comparison checks the generated file against that readback. Unknown normalization requires model-owner review.

Supply a new `context` in the verification request when a viewer or post-write model version differs from the discovery actor. Keep the same origin, shared model, branch and workbook ancestry. The Stage A observation follows the existing Topic readback/identity/trial shape with `kind: omni_topic_observation` and `review_sha256` equal to the candidate digest or existing Topic fingerprint. Guarded draft preparation and native readback use the Topic receipt for every saved consumer.

### When ownership changes

Use the continuation importer first when starting from a DMA packet. When a packet arrives in an existing standalone project, compare its Topic, branch, source identities and differences with that project's current route. Adopt the packet in the same engagement using the installed backend-handoff skill:

```sh
python3 -I -S -B scripts/continuation.py initiate --packet /absolute/incoming/continuation.json \
  --project /absolute/existing-engagement --decision contracts/packet-adoption-v1.json
```

The decision records `action: adopt_dma_continuation`, `role: user`, the engagement's `project_id`, a traceable `reference` and `response_text`, its prior `route` pin and `prior_context` (both null if discovery has yet to start), the packet's `packet_sha256` self-seal, its exact `topics` list, and the reviewed `destination`. Keep the incoming packet outside the engagement. For an integrated packet supply the existing trusted DMA runtime and saved run through the normal continuation command. Adoption retains the project's mode, surfaces and earlier work. A packet without a deployed Topic reserves DMA ownership immediately. Receive the missing semantic review or scoped cowork response and re-establish access before dependent native work.

If the first incoming DMA artifact is a semantic review or cowork response by itself, pass `--decision contracts/adoption-v1.json` to `import-dma` or cowork `select`. Record the attributable user decision with `role`, `reference`, `response_text`, `action: adopt_dma`, prior `route` pin, `prior_context`, intended full `destination` context, selected `topics` and original `handoff_sha256`. The previous branch candidate stays in the engagement. DMA ownership invalidates standalone source evidence and disables standalone authoring for that engagement. Re-establish current access through the DMA Topic-first path.
