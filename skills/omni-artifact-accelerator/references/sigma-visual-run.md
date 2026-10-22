# Sigma visual migration: local implementation

**Source runtime prerequisite:** connected Sigma capture requires an independently obtained compatible SigmaMigrationAgent environment with the `capture-visual` command and its maintained producer fixtures. This source extension is not shipped in this repository and is not provided by the cited base revision alone. Confirm `sigma-migrate capture-visual --help` before following the capture steps. If it is unavailable, continue with supplied supported artifacts through the [Sigma bridge](../../omni-artifact-translator/references/sigma-agent-bridge.md); do not imply that source acquisition occurred.

Use this after selecting Sigma in the connected visual workflow. The package now includes an actual producer bridge, source-pinned requirements, keyed numerical comparison, evidence coverage, a local stdio MCP bridge and a named-draft Omni adapter. Source acquisition uses SigmaMigrationAgent's separate `capture-visual` command. None of these helpers turns a local test or supplied status into tenant acceptance.

## Execution paths

| Step | Owner/tool | Result |
| --- | --- | --- |
| Capture original evidence | SigmaMigrationAgent `capture-visual` or existing reviewed exports | Versioned private source packet and resumable export journal |
| Translate | `omni-artifact-translator/scripts/translate_artifact.py --format sigma-agent` | Original-ID inventory; retained source payload, scope and gaps |
| Requirements | `scripts/visual_workflow.py prepare` | One row for every supplied asset, brand intake, default/filtered/access/interaction QA cases |
| Backend gaps | Existing `omni-backend-handoff/scripts/cowork.py`, `migration.py`, `dma_frontend.py` | Versioned DMA requests/candidates/returns with unchanged route authority |
| Native candidate | `omni-bi-engineer/scripts/omni_native.py` | Existing development draft, scoped payload, before-state, intent and readback |
| Compare | `scripts/visual_workflow.py compare` and `coverage` | Recomputed keyed results and complete accounting of retained obligations |
| Host access | `scripts/visual_mcp.py` | Workspace-bound local tools; explicitly configured source/target operations |

Paths above are relative to the relevant installed skill. Run each script's `--help` for its exact interface. Keep one private engagement outside the skill installation. A complete coverage ledger can still describe a partial migration.

## Source capture and import

Reuse the existing Sigma run and acquisition authorization. The source command requires its own explicit request, source-read/query flags, principal, origin, scope, tag and finite budgets. It never loads Omni credentials. Start and resume the same journal rather than recreating an uncertain export. A tagged definition is not an atomic data snapshot. Undefined processing responses remain unresolved instead of being polled as though they prove progress.

```sh
sigma-migrate capture-visual --request /private/run/inputs/capture-request.json \
  --directory /private/run/inputs/sigma-capture \
  --allow-source-read --allow-source-query
# Resume a known capture; do not replace its request or journal.
sigma-migrate capture-visual --request /private/run/inputs/capture-request.json \
  --directory /private/run/inputs/sigma-capture \
  --allow-source-read --allow-source-query --resume
```

See the [Sigma bridge](../../omni-artifact-translator/references/sigma-agent-bridge.md) for accepted shapes and the source repository's operator guide for the request schema. Retain the full capture directory, including image/result files; importing its JSON alone cannot verify the attachment bytes. Keep source limitations and `complete`/`partial`/failed acquisition separate from numerical completeness and migration readiness.

## Prepare requirements and design

After creating an engagement with `analyst_project.py init` and retaining original/inventory JSON under `inputs/`:

```sh
python3 scripts/visual_workflow.py --project /private/run prepare \
  --original inputs/source.json --inventory inputs/source-inventory.json \
  --website https://customer.example --output contracts/visual.json
python3 scripts/visual_workflow.py --project /private/run check \
  --requirements contracts/visual.json
```

Fill the explicit route and its existing decision reference before target design. Choose `reuse_existing` only when no model changes are allowed, or retain the selected Sigma semantic/warehouse route. Capture the customer's website URL when missing; `prepare` records that question rather than silently guessing a brand. The helper does not scrape or download website assets.

Designers fill each business question, target binding, parity and design changes from source evidence. Preserve `source_*` fields. Use [chart mapping](../../omni-dashboard-designer/references/migration-chart-mapping.md), [dashboard patterns](../../omni-dashboard-designer/references/dashboard-patterns.md) and [brand contract](../../omni-branding/references/brand-contract.md). `native`, `custom` and `app` are implementation routes; `exact`, `adapted`, `unsupported` and `unknown` are parity outcomes. A screenshot cannot supply a missing formula, security rule or control binding.

Keep every supplied asset. Mark a later pilot item `defer` with a reason/reference; it remains pending. Use `exclude` only for an actual scope decision. Required default cases cannot be removed, and additional scenarios can be added before freezing expectations. Source definition/identity edits or changed original files invalidate the requirements.

## DMA collaboration

Use the existing [cowork contract](../../omni-backend-handoff/references/cowork-contract.md) for genuine missing fields, metrics, grain or binding decisions. Register the original inventory, requirements and narrow supporting files in the analyst project, then include them in the bounded request. For large sources, retain originals locally and use the contract's reviewed coherent scope slice rather than increasing the disclosure limit.

`omni_semantic_reconstruction` does not authorize dbt/warehouse work. `reuse_existing` does not authorize semantic changes. A received candidate remains a candidate. Recheck affected visual requirements and queries after selecting a new backend version; preserve unaffected brand decisions. Full engagements use the existing migration scope and candidate-bound frontend return, including the original nonvisual/control obligations.

## Native construction

Follow [Omni build/export](../../omni-bi-engineer/references/omni-build-export.md). The bounded adapter edits an **existing named development draft**. New-document creation publishes immediately in the inspected CLI, so creation/publication remains a separate, explicit operation through qualified tools. An unavailable draft is a target prerequisite, not permission to publish a replacement.

The BI engineer authors the native payload from inspected Omni schema and verified semantic field/query bindings. Ownership records identify the exact tile/control/container/settings keys the operation may change. The adapter validates the selected scope, retains a before-state, checks drift, persists intent before writing and reads back afterward. A timeout requires reconciliation; it never automatically replays the patch. The adapter is not a universal Sigma chart-code converter and does not implement App writeback/action chains.

## Numerical comparison contract

Author `analyst_numeric_comparison_spec` JSON with these fields. Paths are relative to the engagement; every file pin is `{ "path": "...", "sha256": "<actual file SHA-256>" }`.

| Field | Required value |
| --- | --- |
| `schema_version`, `kind` | `1`, `analyst_numeric_comparison_spec` |
| `case_id` | Exact numeric case ID from the requirements |
| `requirements`, `candidate` | Pins of the completed requirements and exact native candidate record |
| `source`, `target` | Each has `file`, `format` (`csv` or `json`), `context`, `complete`, `completeness_reference` |
| `context` | Semantic `filters`, `timezone`, `data_watermark`, `population`, and actual `principal` |
| `persona_equivalence_reference` | Evidence identifying the corresponding source/target access personas |
| `keys` | Nonempty list of logical column names that uniquely identify each row |
| `columns` | Each has logical `name`, source field `source`, target field `target`, `type` (`string`, `number`, `boolean`), optional `nullable`, `empty_is_null` and `absolute_tolerance`/`tolerance_basis` |

JSON results are arrays of objects; CSV uses unique headers. No automatic string/date/currency coercion, empty-to-NULL conversion or relative tolerance is applied. Nonzero tolerance requires its metric-specific basis. Duplicate keys reject rather than collapse rows. Different/unknown populations, data times, filters, persona mapping or completeness produce `inconclusive`, even when supplied numbers match. Type/parse errors reject the input.

For a captured Sigma visual, source context additionally includes the exact request `parameters`, its declared `timezone` and `principal` equal to the captured Sigma user ID. The comparison verifies the selected element/page, original JSON attachment hash, complete capture status and recorded data-as-of reference. Missing data time stays inconclusive. These checks do not prove that Sigma applied the declared timezone; qualify effective behavior separately. For another filter state or visual, pin its `sigma-visual-capture.v1` file in the corresponding requirement case as `source_capture`. The helper validates that capture and its placement; when the original is also a visual capture, changed configuration coherence is a comparison gap.

```sh
python3 scripts/visual_workflow.py --project /private/run compare \
  --spec contracts/numeric-default.json --output evidence/numeric-default.json
python3 scripts/visual_workflow.py --project /private/run coverage \
  --requirements contracts/visual.json --candidate evidence/native-candidate.json \
  --evidence evidence/numeric-default.json evidence/allowed-viewer.json \
  --output evidence/visual-coverage.json
```

For human/tool-observed cases, retain an `analyst_observed_case` object with `schema_version: 1`, `case_id`, `lane`, pinned `requirements`/`candidate`, `status`, `observer`, `expected`, `observed`, `execution_reference` and nonempty `files` pins. `not_applicable` additionally requires `decision_reference`. These are recorded observations, not authenticated approvals. Coverage recomputes numerical comparisons and checks current pins; stale or edited summary results reject. Other lanes remain independently reviewable evidence. Business acceptance and published-state verification are separate records.

## Local host bridge

Start one process per private engagement:

```sh
python3 scripts/visual_mcp.py --project /private/run
```

Local tools include source translation, requirements, numerical comparison, coverage and bounded artifact reads. They cannot run arbitrary shell commands, fetch arbitrary URLs or read another engagement. Configure the same program/arguments as a local stdio MCP server in a supporting host.

Optional source capture is fixed at operator startup:

```sh
python3 scripts/visual_mcp.py --project /private/run \
  --sigma-executable /absolute/venv/bin/sigma-migrate \
  --sigma-request inputs/capture-request.json --sigma-directory inputs/sigma-capture \
  --enable-sigma-capture
```

The request is hashed at startup and cannot change during that process. The tool can only start/resume that scope. Source credentials stay in the configured environment. The source command has a finite invocation timeout; interrupted capture resumes from its persisted journal.

For a selected page/workbook, use `--sigma-batch inputs/capture-batch.json` instead of `--sigma-request`/`--sigma-directory`. The batch has `kind: analyst_sigma_capture_batch`, `schema_version: 1`, explicit `max_total_requests` (at most 10,000), `max_invocations` (at most 200), and up to 100 `captures`, each containing `capture_id`, `request` and a unique `directory`. IDs must match their request files. Only configured IDs appear in the tool schema. Before each sequential invocation, the bridge durably reserves that request's full per-invocation budget, including failed calls, and preserves reservations across restarts. These are conservative upper bounds, not measured query/request counts. Keep the full source inventory in requirements, including items outside the current batch. Per-element captures are not page screenshots or an atomic workbook freeze; compare source versions/coherence across the batch before declaring a shared baseline.

Add `--target /private/run/inputs/omni-target.json` to enable the native adapter's inspection/preparation/reconciliation tools. The model cannot select a different target through a tool argument. To enable writing one already reviewed candidate, restart with `--allow-candidate <exact SHA-256> --authorization-reference <existing authorization reference>`. Reuse authorization already given; the startup value is an enforcement binding, not a new permission policy. There is no publish tool.

This is a single-user local bridge. [MCP stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) uses newline-delimited JSON-RPC. ChatGPT can connect custom MCP through an appropriately configured [Secure MCP Tunnel or HTTPS deployment](https://developers.openai.com/plugins/deploy/connect-chatgpt); [Claude remote connectors](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) run from its cloud and differ from local Desktop connections. A remote deployment must supply its own authenticated user/tenant boundary and approved network/storage setup. Do not expose this local OS trust boundary as an unauthenticated public endpoint. No tunnel, remote service or connector is provisioned by the bundle.

## Qualification and operations

Run package regressions, the actual Sigma-producer compatibility tests, source capture tests, native transport/readback tests and stdio protocol tests. Then record the chosen host's actual tool discovery, file handling, reconnect/resume and source/target identity behavior. Local protocol success does not establish Claude/ChatGPT account support.

Retain query/export counts, file sizes, elapsed time, request IDs, retry attempts, source state and exact target revision. Set finite source scope, export size/time budgets and retention at engagement setup. Keep customer images/results out of the repository and shared support bundles. Begin with one visual in context, then one page, then the selected workbook; deferred/unsupported items remain visible throughout.
