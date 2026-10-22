# Tableau visual migration: local implementation

The v0.8.0 local workflow captures or imports source evidence, retains separate worksheet placements, prepares requirements, reuses a governed Omni model or exchanges real gaps with DMA, and builds an existing Omni development draft. Local tests qualify the contracts and recovery behavior. Live Tableau/Omni behavior and actual Claude/ChatGPT account operation remain untested until an engagement supplies them.

## Select the route and scope

Use one private engagement created by `analyst_project.py init`. Keep the original capture directory intact. Select one dashboard and all required worksheet placements, controls, parameters, text, legends, images and actions. Every supplied object receives a disposition; repeated worksheet placements remain separate obligations. Freeze an independently reviewed expected manifest and explicit REST-view-to-XML mapping. Names alone do not establish identity.

Use `reuse_existing` for compatible existing Omni Topics, `omni_semantic_reconstruction` for actual semantic changes, or `warehouse_first_refactor` for reviewed upstream work. A missing route allows analysis but blocks target preparation. The [Tableau design mapping](../../omni-dashboard-designer/references/tableau-mapping.md) defines metric, filter, action, branding and improvement decisions.

## Acquire source evidence

Prefer the customer's available official Tableau MCP for supported reads. Inspect its actual tool schemas, version and permissions. The included `tableau_capture.py import-mcp` normalizes retained responses; it does not call a connector or download arbitrary response URLs. A remote temporary path or signed URL needs a separately approved file transfer into the local transfer directory. The intake records the reference hash and transfer provenance; those declarations are not authenticated identity proof.

The REST fallback uses an already-authorized session, fixed GET routes and one approved HTTPS origin/site/workbook. It checks `/sessions/current` against the expected user and site before and after capture, requests workbook content without extracts, and retains PNG plus individually selected worksheet CSV. API support, permissions and source freshness may still prevent completion. No sign-in or credential discovery is included.

```sh
python3 /installed/omni-artifact-translator/scripts/tableau_capture.py capture \
  --request /private/run/inputs/tableau-request.json \
  --directory /private/run/inputs/tableau-capture \
  --allow-source-read --allow-source-query --session-token-stdin
```

Supply the session token on standard input through the operator's approved secret mechanism; never put it in the request, command arguments or chat. Add `--resume` only for the same request and capture directory. The durable journal bounds requests, bytes, elapsed time and operation attempts across invocations. An uncertain operation is retained for review, not automatically replayed.

```sh
python3 /installed/omni-artifact-translator/scripts/tableau_capture.py import-mcp \
  --request /private/run/inputs/tableau-request.json \
  --response /private/run/inputs/tableau-mcp-intake.json \
  --transfer-directory /private/run/inputs/transferred \
  --directory /private/run/inputs/tableau-capture --allow-source-read
```

The request contract is `tableau-visual-capture-request.v1`; the retained capture is `tableau-visual-capture.v1`. Read the [source contract](../../omni-artifact-translator/references/tableau-source-contract.md) and `tableau_capture.py --help` for exact fields. API versions below 3.30 return legacy CSV; a legacy dashboard result covers only its first worksheet. The 3.30 MCP allData shape retains ordered parts, duplicate names and per-part failures. Missing/ambiguous parts cannot establish whole-dashboard parity. Requested locale, timezone, parameters and action state are not proof that the source applied them. Definition stability is not an atomic data snapshot.

## Import and prepare requirements

Use `tableau_check_capture` and `tableau_import_capture` through the local MCP bridge to check both the envelope and retained attachment bytes. The offline translator also accepts `--format tableau-capture`; downstream requirements recheck the files. A trusted DMA reader can supply `tableau_source_inventory` from the exact retained workbook. Preserve its revision, original hashes and gaps; the DMA billing example is not a general formula compiler.

```sh
python3 /installed/omni-artifact-translator/scripts/translate_artifact.py \
  /private/run/inputs/tableau-capture/capture-000001.json \
  --format tableau-capture --output /private/run/inputs/tableau-inventory.json
python3 /installed/omni-artifact-accelerator/scripts/visual_workflow.py \
  --project /private/run prepare \
  --original inputs/tableau-capture/capture-000001.json \
  --inventory inputs/tableau-inventory.json \
  --website https://customer.example --output contracts/visual.json
```

Use the actual capture path returned by acquisition; the filename above is illustrative. Fill the route, decision reference, target bindings, proposed design and every required case. When the website is unknown, the workflow retains the branding question. It does not scrape or acquire reusable internet images.

## Standalone existing-Topic path

Author the intended native payload, exact ownership and query bindings first. `analyst_existing_omni_baseline_spec` uses schema version 1 and requires `requirements_path`, `payload_path`, `ownership_path`, `review_ref` and `bindings`. Each binding identifies `source_asset_keys`, `query_key`, `topic`, the complete `query`, and `field_ids`. All paths are engagement-relative.

`omni_native.py baseline-capture --spec ... --output ...` or MCP `native_baseline` inspects the configured model, branch, workbook model, resolved YAML and regular Topics. The resulting `analyst_existing_omni_baseline` pins the current definitions and exact candidate inputs. Tenant identity is the verified HTTPS origin and principal; the adapter does not invent an organization UUID. Pass this baseline as `--semantic-file` when preparing the candidate. Preparation and execution require fresh inspections. Missing model ancestry or unsupported query/Topic structures stop this narrow path.

This first baseline supports explicit field/filter/sort/limit/table queries on regular Topics. Calculations, pivots, composite Topics and control edits require a supported extension or real backend handoff. No placeholder DMA catalog is created. Keep semantic gaps with the model owner.

## DMA collaboration

For actual backend changes use the existing [cowork contract](../../omni-backend-handoff/references/cowork-contract.md): register source evidence, freeze the complete source scope, request the specific gap, receive a real candidate, select it and revalidate affected consumers. Preserve original identifiers, allowed changes and unresolved cases. A direct semantic route does not authorize warehouse work.

The request's aggregate input limit remains 256 KiB. If the full source packet exceeds it, create a reviewed semantically closed engagement slice that the existing contract accepts, or retain the size blocker. A reference-only placeholder does not bypass the exchange, and a slice cannot certify the complete dashboard.

## Build, compare and return

Reuse [Omni build/export](../../omni-bi-engineer/references/omni-build-export.md). The target must be an existing named development draft. The BI engineer authors the supported native query/chart configuration; this package does not automatically compile every Tableau mark or expression. The adapter checks ownership, drift, durable intent and readback. Reconcile unknown write outcomes before retrying. No publication tool is exposed.

For each numerical case pin the exact worksheet/placement, capture, result attachment and state. Use the existing typed comparison contract plus Tableau's explicit result normalization profile when required. Raw CSV bytes remain authoritative; the validator replays normalization from ordinal columns and the raw-file pin. Duplicate headers, localized values, NULL/blank distinctions, totals and ordering require explicit treatment. Unknown effective state or completeness yields `inconclusive`, even if supplied values match.

Coverage independently accounts for numerical, visual, interaction, accessibility, access and performance cases. Native readback, effective access and business acceptance remain distinct. A supplied passing observation is not an authenticated acceptance.

For standalone work, `migration.py` accepts `analyst_standalone_migration_return_spec` with `scope_sha256`, `baseline_path`, `requirements_path`, `candidate_path`, `execution_receipt_path`, `coverage_path` and `unresolved`. Its return/check recompute the pinned scope, baseline, candidate readback and coverage without a DMA catalog. DMA-backed work retains its existing candidate-bound return and DMA finalizer.

## Local Claude/ChatGPT host access

The shipped host is local stdio on POSIX. It exposes no HTTP listener and does not install or provision a cloud connector. Start with local-only tools:

```sh
python3 /installed/omni-artifact-accelerator/scripts/visual_mcp.py --project /private/run
```

To enable source capture, add `--tableau-python /trusted/python3 --tableau-request inputs/tableau-request.json --tableau-directory inputs/tableau-capture --enable-tableau-capture`. The operator sets a source-only `TABLEAU_SESSION_TOKEN` environment variable; the bridge passes it to the child on stdin and excludes Omni credentials. A finite `--tableau-batch inputs/batch.json` may replace the single request/directory, with `kind: analyst_tableau_capture_batch`, schema version 1, fixed `captures[{capture_id,request,directory}]`, `max_total_requests` and `max_invocations`. Reservations survive failed runs and restart.

Add `--target /private/run/contracts/target.json` for the configured native inspection/preparation tools. Draft execution additionally needs `--allow-candidate <exact digest> --authorization-reference <existing authorization>`. Export/query is separately enabled with `--allow-export-candidate <exact digest> --native-export-request contracts/export.json --native-export-state contracts/export-state.json --export-authorization-reference <existing authorization>`. Tool arguments cannot change those source/target grants. Export tools return retained-file pins rather than raw results; saved export IDs support status/download recovery without resubmitting a job.

A host must actually support launching this local process, transferring files and reaching its configured CLI. For hosted-only Claude or ChatGPT deployments, use the supported artifact-transfer/execution route for that account; an authenticated remote OAA service is not supplied here. Qualify tool discovery, authorization, files, interruptions, source states and target results in each actual configuration before claiming end-to-end host support.
