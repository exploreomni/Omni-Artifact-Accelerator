# Hex dashboard and App migration workflow

Use one retained Hex source scope to create native Omni dashboards and Apps with shared governed metrics. This guide describes the local v0.11.0 implementation. Synthetic tests qualify code paths; actual Hex/Omni behavior, host accounts and customer acceptance require separate evidence.

## Intake and source scope

Initialize a private migration engagement with `analyst_project.py init --output /absolute/new-run --name 'Hex migration' --mode migration --surface both`. Keep customer evidence outside the installed package. Select Classic reporting views, interactive App tasks and any Generative App files explicitly. Hex dashboard-like experiences are published Apps; do not search for an assumed separate dashboard API object.

Record the source project and resolved version, important tabs/screens, defaults and changed-input states, personas, refresh/cache expectations and upstream dependencies. Reuse the accepted backend route; `both` does not authorize a warehouse rewrite. Ask missing brand context once: **“What is your company website URL, and are there approved brand guidelines, logos, fonts or reusable images we should use?”** Separate website observations from approved rules and retain asset origins, reuse rights and fallbacks.

Read the [source contract](../../omni-artifact-translator/references/hex-source-contract.md) for the exact request, output crosswalk, transferred evidence and limits. The primary structure is `.hex.yaml`, supplemented by supplied dependencies/generated files, images, results and state observations. Unknown offline IDs remain unknown. File hashes and locators identify supplied definitions; they do not authenticate a tenant or published version.

## Capture and retain evidence

Prepare a `hex-visual-capture-request.v1` request. Set each export's explicit version selector, record any expected native source-version ID, and use an independent expected-object manifest. Outputs bind native project/cell/version/run identities through a reviewed crosswalk; an exported version ID is not automatically the API run's `projectVersion`.

The following paths are illustrative installation and private engagement locations; replace them with actual paths.

```sh
python3 /installed/omni-artifact-translator/scripts/hex_capture.py import-local \
  --request /private/run/inputs/hex-request.json \
  --source-root /private/run/inputs/supplied \
  --directory /private/run/inputs/hex-capture --allow-source-read
```

For connected acquisition, use `capture` with the same request/directory, `--allow-source-read --token-stdin`, and provide the token through the approved secret mechanism on stdin. The fixed source reader exports definitions and retrieves chart PNGs from already completed selected runs. It does not execute notebooks, refresh published results, create Threads, edit source cells or administer permissions. Opening or interacting with a Hex App can run code; passive acquisition does not authorize that.

Automatic source execution is deliberately unavailable because the published-run endpoint selects the latest version and this package has no qualified publication lock. A before/after check cannot prevent side effects from a concurrent publication. Use existing run evidence or an explicitly reviewed operator execution procedure. Never bypass this restriction by creating a fresh capture directory.

Keep the entire returned directory and exact returned capture filename. Resume with the same request and `--resume`; retained operation state and budgets govern retries. Captures are immutable versions. Import transferred image/CSV/JSON evidence using `import_evidence(capture_path, spec, source_root)` or the local host's `hex_import_evidence`; it returns a new capture version. Files must exist in the approved local transfer directory. Tool response URLs and remote filesystem paths are not file transfers.

Draft MCP images cannot be labeled published-run images. A chart image does not establish an entire Classic App layout or a custom Generative screen. Classic PDFs can omit tabs; inspect the complete selected tab/screen inventory. Retain explicit native preview observations for unsupported capture paths.

## Inventory and reviewed requirements

```sh
python3 /installed/omni-artifact-translator/scripts/hex_capture.py check \
  --capture /private/run/inputs/hex-capture/ACTUAL_RETURNED_CAPTURE.json
python3 /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/hex-capture/ACTUAL_RETURNED_CAPTURE.json \
  --format hex-capture --output /private/run/inputs/hex-inventory.json
python3 /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run prepare \
  --original inputs/hex-capture/ACTUAL_RETURNED_CAPTURE.json \
  --inventory inputs/hex-inventory.json --website https://customer.example \
  --output contracts/visual.json
```

`hex-adapter` imports the actual generic DMA `source_adapter_result`; legacy `dma-inventory` still accepts `hex_source_inventory`. Both require the inspected declared producer revision `c513474e87af9c2c31deebd2ae675c8602955203`. Those are different contracts. The legacy inventory alone lacks generated interface files and a complete layout denominator. Keep original exports and prefer complete `hex-capture` evidence for visual implementation. Producer pins are compatibility declarations, not authenticated provenance.

Review every retained source object: projects, cells, tabs, repeated placements, controls, shared-filter exclusions, content, code/dependencies, generated files and unknown actions. Follow [Hex experience mapping](../../omni-app-designer/references/hex-experience-mapping.md). Generated files are source evidence, not executable plugins or an inventory of all conditional screens. Preserve unresolved runtime and component-version dependencies.

Each requirement defaults to all engagement surfaces. To assign it to one, set `target_surfaces` to `["dashboard"]` or `["app"]` in JSON list form and provide `assignment_reference`. Keep `["dashboard", "app"]` for shared obligations. Scope units must use the same assignments. Removing a requirement, unsupported control or hidden dependency is not assignment. `defer`/`exclude` require their existing explicit scope decisions; neither counts as migrated.

Fill route, business question, metric contract, target bindings, parity treatment and independent acceptance cases. Inputs receive control/state cases; query visuals receive numerical cases. SQL/Python business logic must be placed in a reviewed governed computation layer. Local scenario values must be clearly hypothetical, bounded and separate from authoritative metrics. Required writeback, services, uploads or ML behavior remain incomplete until implemented and independently verified.

## Shared backend and target baseline

Use the [cowork contract](../../omni-backend-handoff/references/cowork-contract.md) and [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md). Register original evidence, freeze the full selected source scope, send dependency-complete requirements to DMA, receive its actual candidate and record the frontend selection. Keep the 256 KiB aggregate selected-input limit; large engagements need explicit waves and a complete source register. Referenced file hashes do not make unavailable bytes accessible to DMA.

DMA retains warehouse/semantic implementation, validation and deployment authority. Candidate selection is not deployment. Standalone reuse still inspects current Omni Topics, model ancestry, queries and exact field bindings. Source, requirements, backend candidate or target model changes invalidate affected evidence on both surfaces.

## Build the dashboard

Use [native build/export](../../omni-bi-engineer/references/omni-build-export.md). Prepare reviewed query/chart mappings, ownership and a baseline spec with exact source asset/query/Topic/field bindings. Map all assigned placements and content, including repeated cells. Retain inspected native control bindings and exclusions. Unsupported control/chart schemas require a reviewed native implementation or visible gap; do not invent API shapes or replace them silently.

Use the shared native adapter's baseline capture, candidate preparation and exact-candidate execution. Keep a separate development document and exclusive named draft. Preserve unrelated content, record intent/readback and reconcile uncertain writes. Source images guide appearance; source and independent expected results guide numerical checks. Neither substitutes for the other.

## Construct the native App

Read the [native App contract](../../omni-app-engineer/references/native-app-contract.md) and its initial-construction section. Begin with an operator-created **workbook-only document, exclusive named draft and inspected governed queries**. Establish those queries using verified native tools; the bounded App writer does not create documents or queries. Retain their actual readback and a reviewed native query bridge/runtime. A declared fragment or mock array does not establish a working native connection.

The initial operation creates an App from a reviewed full HTML body and settings on that workbook draft. It has a distinct candidate and authorization from subsequent bounded edits. Bind each component to the exact query and each input to a reviewed field/filter or explicitly labeled local scenario. Supply the required runtime, behavior and security contracts; preserve reset, pending, empty, error, restricted and stale states. Do not paste Hex-generated JavaScript expecting its notebook bridge to exist in Omni.

Use the initial inspect, baseline, prepare, execute and reconcile commands documented in the App contract. Execution requires the exact initial candidate hash and review reference. The operator's native runtime evidence remains a prerequisite; local controller tests do not qualify a proprietary runtime bridge. Validate actual input-to-query-to-render behavior in Omni before calling the App migrated.

App API authoring retains its experimental qualification and CLI App commands are **alpha**. Writes are last-write-wins, so exclusive draft coordination and readback do not create an atomic concurrency guarantee. Keep recovery evidence; no blind replay or resource-policy expansion. A named-draft image-export route remains unqualified: use explicitly recorded native preview evidence without publishing merely to take a screenshot.

## Compare and return both surfaces

Use typed retained CSV/JSON results and an explicit parser profile with `hex_visual.normalize_results`. Keep original result bytes beside the normalized derivative; the workflow recomputes normalization. A numeric case's `source_binding` includes `object_id`, `project_id`, `source_version_id`, `cell_id`, `output_id` and `state_sha256`, with its exact `source_capture` file pin.

Imported `state_observations` must bind the frozen output identity, input/filter values, timezone/locale, principal, run, population, cache/data timing and independent `execution_reference` and `output_freshness_reference` values. Supply `persona_equivalence_reference` in the comparison specification. Target context uses the same canonical business inputs/population, with its own principal and cache evidence. Unknown provenance, missing native/run identity, truncated outputs and stale state remain inconclusive even when rows match. Numeric proof and rendered-state proof remain separate.

Run `visual_workflow.py compare --spec ... --output ...`, then `coverage --requirements ... --candidate ... --evidence ... --output ...`. Coverage selects the requirements assigned to that candidate's surface. App and dashboard evidence must pin their respective candidates; never reuse one surface's screenshot or receipt as the other's proof.

Return the existing three proof paths per surface: `candidate_path`, `execution_receipt_path`, `coverage_path`. DMA-backed returns use `migration.py`; standalone returns use the existing standalone contract. `both` requires distinct documents, both proofs and the union of assignments matching the frozen scope. The finalizer rechecks candidate/baseline/source/backend pins and case coverage. Missing surface evidence, deferred items and source gaps retain incomplete status.

Report local consistency, native readback, native runtime/access/visual validation, business acceptance and publication separately. A successful local test or HTML readback never grants customer acceptance. Publishing, schedules, source retirement and operational actions remain separately authorized steps.

## Claude and ChatGPT host setup

The local stdio host exposes `hex_import_local`, `hex_import_evidence`, `hex_translate`, `hex_check_capture` and `hex_import_capture` without live source access. To enable only a fixed source request:

```sh
python3 /installed/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private/run --hex-python /trusted/python3 \
  --hex-request inputs/hex-request.json --hex-directory inputs/hex-capture \
  --enable-hex-capture
```

Set `HEX_ACCESS_TOKEN` through the approved secret channel. The source child receives it on stdin with a reduced environment, excluding Omni credentials. Optional `--hex-token-env` must name a `HEX_` variable. Tool arguments cannot change the startup source scope or enable execution.

Configure `--target` for the dashboard and `--app-target` for a distinct App document. Dashboard writes use `--allow-candidate` plus `--authorization-reference`; existing-App edits use `--allow-app-candidate` plus `--app-authorization-reference`. Initial App creation separately requires `--allow-app-initial-candidate` plus `--app-initial-authorization-reference`. No publication tools are exposed.

This package does not provision a remote connector. Qualify actual tool discovery, account permissions, attachment transfer, process support, interrupted-job recovery and native writes separately in each Claude/ChatGPT configuration. An operator-assisted file path is valid when clearly recorded; it is not evidence of an automatic hosted integration.
