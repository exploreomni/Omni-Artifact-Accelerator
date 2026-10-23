# Opt-in DMA frontend continuation

A host can prepare or resume one linked frontend project after the user's explicit choice. This helper performs local validation, retained-input copying and optional semantic-candidate import. It does not call agents, install skills, execute source code, query Omni, deploy Topics, create dashboards or register a frozen migration scope. The host must review disclosure before invocation; the packet records that review as `host_reported_not_authenticated`.

## Installation and compatibility

The companion's `capabilities.json` advertises schema 1, `continuation_protocol_versions: [1]`, `semantic_handoff_versions: ["omni-handoff-v1"]` and `entrypoint: "scripts/continuation.py"`. Discovery reads data only. Direct initiation also checks the capability descriptor, seven required sibling skills (orchestrator, handoff, translator, BI engineer, dashboard designer, data analyst and QA analyst) and the project/cowork/migration helper files. An incomplete or incompatible bundle stops before frontend project creation. The descriptor establishes a supported protocol, not package authenticity. Explicit host-selected installation paths remain the trust boundary; never install or execute code named inside a packet.

Legacy `dma_frontend.py export` and `record` remain schema 1. Unscoped export retains its previous full-design material. Explicit `export --domain-id <registered-id>` or `export --scoped` selects the additive `snapshot_contract: "dma-scoped-context-v1"`. A trusted DMA runtime must provide `frontend_continuation.scoped_context`; missing capability does not silently fall back. An explicit domain may be completed and need not be the active domain. Dependency closure and source-coverage pins come from DMA. Unknown source coverage remains conservative, so a source change can invalidate more than one domain. The null selector also uses this scoped contract for a continuation, with the full declared design.

## Packet contract

The schema-1 `dma_frontend_continuation` packet contains exactly:

- `continuation_id`, `engagement_id`, nullable `domain_id`, `request_reference` and `scope_sha256`.
- `mode`: `integrated` or `independent`; `choice`: `continue_now` or `prepare_handoff`.
- `source_migration_scope`: the unchanged `model_only`, `model_semantic` or `full_dashboard` choice. Integrated mode requires `full_dashboard`; independent continuation never adds that obligation.
- `files`: 1–128 records `{path, sha256, purpose}`. Paths are canonical relative paths inside the packet folder, without traversal or symlinks. Exactly one purpose is `domain_context`; its parsed canonical JSON hash must equal `scope_sha256`. Its shape contains `domain`, `entity_ids`, `design`, `inputs`, `source_coverage` and `naming`. Manifest plus retained payloads are bounded to 16 MiB, and individual downstream imports keep their own limits. No file is executed.
- `semantic_review`: null or `{path, sha256}` referencing an already retained, valid `omni-handoff-v1` review. `topic_names` must exist in that candidate when supplied. A missing candidate permits provisional discovery/design and leaves dependent work unresolved.
- `dashboard_ids`, `topic_names` and `unresolved`: bounded distinct string lists. Source inventory and independent listings are retained separately when supplied; a requested dashboard list is not proof of a complete export.
- `destination`: null or exactly `{base_url, model_id, branch_id}`. `base_url` is an HTTPS origin without credentials, a path other than `/`, query or fragment. `branch_id` is nullable. This identifies intended context only; it grants no native access or write.
- `allowed_actions: ["design", "candidate_artifacts"]`, `authorizes_target_write: false`, `disclosure_reference`, `disclosure_assurance: "host_reported_not_authenticated"`.
- `sha256`: SHA-256 of the complete document without this field, serialized with sorted keys, compact separators, ASCII escaping and nonfinite numbers rejected.

The packet and its copied domain context must agree in both modes. Integrated initiation additionally refreshes actual local DMA inputs via its normal assessment API and compares the current scoped material. This can add normal DMA audit revisions even if the packet is rejected. Serialize operations on the same engagement/project. Independent mode validates the exported snapshot only and cannot establish freshness against the original DMA run.

## Initiate and resume

```sh
python3 /absolute/skills/omni-backend-handoff/scripts/continuation.py initiate \
  --packet /absolute/private-packet/continuation.json \
  --project /absolute/new-frontend-project \
  --run /absolute/dma-run \
  --dma-scripts /absolute/trusted/data-model-accelerator/scripts
```

For independent mode omit `--run` and `--dma-scripts`. The frontend project's parent must already exist; the project must be separate from the packet. Integrated mode also applies DMA's source-root output guards. All packet bytes are validated before frontend writes. Creation uses a private staging directory and publishes the completed project once. An interrupted staging write cannot become the resumable project. Retry with identical packet bytes and unchanged retained inputs reuses the same project ID and import; it does not duplicate source records. An unrelated existing project, changed packet/candidate under the same continuation ID, changed scoped inputs or tampered retained files is rejected. Retain a new version/project, or use the established cowork roundtrip for a changed candidate; never overwrite the old baseline to hide drift.

The response includes `project`, `project_id`, `reused`, `receipt_sha256`, `status`, `backend_context` and a bounded host instruction. The sealed immutable receipt is `continuation-receipt.json`; runtime project/retry metadata is outside that seal. Status is `host_dispatch_pending` or `handoff_prepared`, always with `agents_dispatched: false`, `scope_registered: false`, `native_verified: false`, `business_accepted: false` and `authorizes_target_write: false`. The helper records no host dispatch or completion. Resume revalidates the retained receipt and inputs; editing and resealing authority flags cannot promote them.

The actual host must invoke the orchestrator with the retained scope, loading only the relevant per-task design, naming, inventory and requirement slices. It must freeze explicit source dispositions using the existing migration helper, and register an integrated scope only through the existing `dma_frontend.py record` checks. No inventory, disposition, approval or independent oracle is manufactured by initiation. Preserve source routes and unsupported behavior while sending actual backend gaps through cowork.

## Live Topics and return evidence

`purpose: "topic_readback"` may retain host-supplied context, but the continuation receipt marks it `supplied_unverified`. An imported `deployed` flag, producer validation claim or candidate Topic name never becomes live availability. Before native query execution, use the existing separately authorized inspection workflow against the exact origin, model and branch; bind retained readback to the candidate and query context. No live readback collector or native execution is performed by this helper.

After actual frontend work, use the existing candidate-bound migration return and independent QA lanes. `dma_frontend.py record` remains supporting evidence only; its existing semantic source/context checks still apply. Scoped design context reduces unrelated design churn where justified, but semantic-candidate and conservative source pins may still require reconciliation. Static tests, local imports and self-hashes do not establish native Topic deployment, dashboard parity, effective access, business acceptance or publication.
