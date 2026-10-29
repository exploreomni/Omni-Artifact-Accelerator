# Sigma visual migration

Use the [Sigma specialist](../../omni-sigma-migrator/SKILL.md) inside the existing
Artifact Accelerator engagement. Start with the [connected host guide](sigma-connected-host.md)
for guided intake, capability/version recognition, fixed source requests and
check/inventory/snapshot/capture tools. No dependency installation or activation
is automatic. Source and target credentials, query authorization and publication
remain separate.

The [compatibility registry](sigma-compatibility.json) distinguishes the legacy
Sigma revision, the unreleased source-operation extension and passive OAA evidence.
The earlier base SHA does not contain that extension. Capture supports page PNG
and element PNG/JSON with optional associated model under the v2 request. Original
configuration, independent inventory, behavior, state and results stay separate.
Optional workbook contents are Beta current-definition evidence, not tagged data.

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
| `source`, `target` | Each has `file`, `format`, `context`, `complete`, `completeness_reference`. Ordinary target formats are `csv` or `json`. For bound Sigma evidence use `source.format: sigma-normalized`, a `file` pin to the normalized result and a separate `raw_file` pin to the exact original result attachment. |
| `context` | Semantic `filters`, `timezone`, `data_watermark`, `population`, and actual `principal`. Bound Sigma comparison additionally retains explicit `parameters`, `locale`, `cache` and `freshness_reference`; preserve their exact observed values on the corresponding source/target state. |
| `persona_equivalence_reference` | Evidence identifying the corresponding source/target access personas |
| `keys` | Nonempty list of logical column names that uniquely identify each row |
| `columns` | Each has logical `name`, source field `source`, target field `target`, `type` (`string`, `number`, `boolean`), optional `nullable`, `empty_is_null` and `absolute_tolerance`/`tolerance_basis` |

JSON results are arrays of objects; CSV uses unique headers. No automatic string/date/currency coercion, empty-to-NULL conversion or relative tolerance is applied. Nonzero tolerance requires its metric-specific basis. Duplicate keys reject rather than collapse rows. Different/unknown populations, data times, filters, persona mapping or completeness produce `inconclusive`, even when supplied numbers match. Type/parse errors reject the input.

For Sigma, every numerical requirement pins its source capture. Legacy captures
verify actual PNG/JSON bytes but leave effective state and full-row completeness
unqualified. An arbitrary matching CSV is reported as arithmetic agreement with
Sigma parity inconclusive. The richer `sigma-source-evidence-bundle.v1` retains
original definitions, per-object mappings, observed state, complete population,
freshness and exact result attachment. `sigma-normalized` rows are recomputed
from original bytes and explicit parser profile; they cannot hide errors, truncate
precision or silently coerce formats. Bind `source_binding` to the selected object,
definition fingerprint, state and attachment. See the [evidence contract](../../omni-artifact-translator/references/sigma-agent-bridge.md).
Page PNGs never become numerical result evidence. Neither a passed comparison nor
a supplied principal reference authenticates effective access or business acceptance.

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

Follow [connected host setup](sigma-connected-host.md) rather than the retired
unpinned `--enable-sigma-capture` wrapper. Local tools remain available without
source credentials. External source tools appear only for startup-selected
operations with pinned runtime, capability manifest and finite durable budgets.
Source query/export permission does not grant native changes. Native authoring
continues through existing adapters and candidate-specific startup authority.
There is no Sigma publication tool or unauthenticated remote server.

## Qualification and operations

Source-only fixtures verify contract handling, original files, scope restrictions,
precision and negative cases. They do not establish deployed runtime dependencies,
source tenant access, native parity, visual quality or business acceptance. Host
qualification must separately cover actual tool discovery, reconnect/resume,
identity, secret routing and user/tenant isolation. Retain request/job IDs, original
file hashes, reservations, source state and target revision in private evidence.

Begin a separately authorized live pilot with one visual in page context, then
expand to the selected workbook only after independent acceptance evidence.
Deferred, unsupported and unobserved cases remain in the denominator. For timeouts,
resume the original source journal or reconcile the exact target intent; never
retry an uncertain mutation in a new directory to evade its journal.
