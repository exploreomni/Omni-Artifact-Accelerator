# Build from a selected DMA Topic

For a DMA-bound App or dashboard, reuse the selected Topic through the saved workbook query behind each analytical consumer. Start with any suitable saved query. Create a new Topic-backed tab if the question requires another grouping, filter or measure. Verify a joined field in the Topic's returned views. Queries and query views that feed the Topic are separate sources when used independently. Creating a model object requires the model owner's existing workflow.

The BI engineer prepares the private files below from the chosen package and supplied/authorized read-only observations. Ask the user only about ambiguous source choices or changes in scope. A candidate with pending deployment can support provisional design. Leave its dependent queries pending. Preserve the distinction between a supplied observation, DMA validation, independently verified access, and authorization to publish.

## Stage A. Select the source once

Run the existing project helper from the orchestrator skill. Both file arguments are engagement-relative and outputs must be new:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py dma-topic-access \
  --project /absolute/private-engagement --request contracts/selection.json --output contracts/access.json
```

The selection spec has `kind: dma_topic_selection`, `schema_version: 1`, `topics`, `context`, and an `observation` pin or null. Every pin is `{path, sha256}` computed from exact file bytes inside the engagement. For an explicit selection outside a continuation include a `selection_evidence` pin to the original scoped request. Use `kind: dma_topic_choice`, `role: user`, a traceable `reference`, actual `request_text`, matching `topics` and `surfaces`, and the selected `destination` (origin in `base_url`, shared `model_id`, nullable `branch_id`; null when undecided). Continuation selections take precedence. A catalog with one Topic can resolve an otherwise unambiguous request. Multiple candidate Topics remain unselected until resolved. Optional `alternative_topics` identify additional Topics to inspect, never permission to use them.

Use the selected destination's HTTPS `base_url`, shared `model_id`, nullable `branch_id` and `workbook_model_id`, intended `principal_id`, and optional `model_version_id` in `context`. A null workbook is valid when observing the shared or branch model before a new workbook exists. Never substitute a branch for published context.

For connected work, retain these source records in the private engagement:

- An observation with `kind: dma_topic_observation`, `schema_version: 1`, `context`, the original review file's `review_sha256`, UTC `observed_at`, optional operator-defined `valid_until`, plus pins `identity`, `models`, `topics` and `trials`. The last two are maps from Topic name to individual file pins. The receipt retains exact Topic response fingerprints.
- Identity is the actual user-scoped whoami response with model membership. Models are the inspected model records keyed by ID, including shared/branch/workbook ancestry. A supplied model version must also be observed.
- Each Topic read file contains `context`, `effective_model_id`, `topic_name` and the original regular Topic response in `response`. Each trial file has `context`, `effective_model_id`, `topic`, `query_ref`, the actual structured `query`, `status: succeeded` and a pin to `result`. Record the completed result as `kind: omni_topic_trial_result`, same context/model/Topic/query reference, `query_sha256` (canonical JSON hash), `status: complete`, selected `columns` and keyed `rows`. Keep original captures, including restricted or empty observations, private. These local checks cannot authenticate the source.
- Record Stage A's `data` as the generated access file, `user_access` as the observation file when present, and `user_identity` as the intended principal. The normal gates continue to control the rest of the engagement.

## Stage B. Map consumers and surface gaps before design

Prepare `kind: dma_topic_consumer_plan`, `schema_version: 1`, the Stage A receipt pin in `access`, and `consumers`. For each consumer supply `consumer_id`, `surface`, `document_id` (exact published locator or planned slug), `topic`, `question`, `grain`, `population`, `access_case`, `expectation_text`, and a pin to the independent `expectation`.

- For `disposition: new`, include a document-scoped `query_key` and the full semantic `tile`. Set its type to query, `isSql` to false, `topicName` to the selected Topic and `query.join_paths_from_topic_name` to the same Topic. Set `query.table` to its actual base view and specify fields and limit. Qualify filters and sort fields too. This DMA authoring profile also requires the explicit query origin for an alternate-Topic exception. Unsupported calculations, composite/cross-model or SQL routes remain a gap.
- For `reuse`, also include `saved_query` pointing to the inspected `context`, `document_id`, `query_key` and exact original `tile`. For a historical query without an explicit Topic origin, retain its `query_ref` and a `result` pin to the scoped execution record described under Stage A. That result must additionally identify the exact document and saved query key. A successful run on another tab cannot qualify this one.
- For `request` or `defer`, give `fields`, `reason`, and null `query_key` and `tile`. Include a source `asset_id` when a frozen migration scope uses asset keys. Optional `change_class` follows the existing cowork vocabulary. These rows cannot enter native content until resolved.
- An `exception` uses a separately observed regular Topic. Its `decision` pin binds `kind: dma_topic_exception`, the access pin, exact consumer/surface/document/key/Topic, `query_sha256`, reason and a pin to the attributable user decision. That record repeats the binding tuple, has `role: user`, `response_text` and a conversation/decision `reference`. A matching record supports the local scope decision only. Raw SQL and model writes require a separate qualified route.
- Include every existing or new data control in `controls`, with `surface`, `document_id`, `control_key`, exact `config`, affected `query_keys` and `field_bindings` containing `topic`, `field_id` and RFC 6901 `pointer` into the config. A dashboard control also needs a `scope_pointer` to the affected query-key list in the original configuration. For an App, the reviewed config contains `component_id`, `query_keys`, `topic` and `field_ids`, and its pointer bindings must match the proposed scope. Missing consumer/control coverage blocks dependent authoring. Candidate and native fields must also agree on dimension versus measure, and on a declared aggregate when both sides return it.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py dma-topic-plan \
  --project /absolute/private-engagement --request contracts/consumer-plan.json --output contracts/analysis.json
```

Record the generated file as Stage B's `queries` evidence alongside the usual profile, insights and expectations. Communicate supported panels and blocked questions before Stage E. If the user requests a backend resolution, prepare it through the existing exchange:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py dma-topic-gap \
  --project /absolute/private-engagement --request contracts/analysis.json --output contracts/gap-spec.json
```

By default the request asks the model owner for clarification against the existing model. For an explicitly selected migration route, pass the existing `source_platform`, `route`, `route_reference` and any `migration_scope_path` or selected `source_inventory_paths` in the plan's `backend`. Receiving or selecting a changed DMA candidate follows the [cowork exchange](cowork-contract.md). Rebind affected sources and repeat A/B as necessary. The local MCP alternative for these operations is `dma_topic_prepare` with `operation` set to `access`, `queries` or `gap`.

## Candidate and readback

After the design choice, prepare the App's actual consumer-to-query bindings. Create a `dma_topic_panels` request with `html_path`, `document_id` and one `panels` row per supported consumer. Each row has `consumer_id`, `query_key`, the unique HTML `element_id` and an exact `script_fragment` from an inline script that references that element ID and query key as quoted literals. Include `controls` with `control_key`, `element_id` and an exact fragment referencing the affected keys for governed App controls outside native control maps. This verifies declared wiring in the exact source. Observe callback behavior separately in a qualified runtime.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py dma-topic-panels \
  --project /absolute/private-engagement --request contracts/panel-map.json
```

The helper chooses an immutable output path from the document and HTML digest; the MCP operation is `panels`. Validate complete saved presentations and effective controls against the Stage B plan before preparing or mutating the candidate. After readback, bind the actual document, principal and workbook model. Every readback requires its inspected workbook ancestry and current Topic definitions, including a newly created workbook. If these are unavailable, leave readback qualification pending. Existing stage, policy and publication controls apply independently.

Historical records remain reviewable. For an older DMA engagement with text-only Stage A/B evidence, prepare the two records above and re-record the affected stages through the normal workflow before a new write. Standalone, separately authorized source diagnostics keep their own routes.
