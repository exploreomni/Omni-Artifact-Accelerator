# Native App draft contract

Use `scripts/omni_app_native.py` for bounded changes to an **existing query-backed native Omni App**, or a separately authorized **first App on an existing workbook-only named development draft**. It does not create a document, convert a dashboard, create workbook queries, publish, or render supplied code. Governed workbook queries are prerequisites for both operations. The App design lane does not require an intermediate dashboard.

## Reviewed official contract

Reviewed 2026-10-22 against [Omni document CLI documentation](https://docs.omni.co/developers/cli/commands/documents), [Omni Apps](https://docs.omni.co/visualize-present/apps), and the [public OpenAPI](https://docs.omni.co/api/openapi.yaml). The downloaded OpenAPI SHA-256 was `c5f4f13c96901e8a749bb5520e229f2583467841c262f9ede4e18bb55115e26f`. The App endpoints carry `x-experimental: true`; the CLI documentation calls App commands **alpha**. These labels apply to the automation contract, not a claim that all Omni Apps have that release status.

The installed CLI inspected during implementation was 1.0.6 and had no App commands. The helper uses fixed, reviewed REST App routes plus the already qualified CLI document/model reads. It never accepts a free-form command or URL from model tool arguments.

| Method and fixed route | Supported shape and use |
| --- | --- |
| `GET /api/v2/documents/{documentId}/draft/{draftId}/app` | `AppHTMLSettings`: `{html, settings}`; inspect the exact existing App. |
| `PATCH /api/v2/documents/{documentId}/draft/{draftId}/app` | `AppPatchBody`: `htmlEdits` array of 1–20 exact `search`/`replace` operations. Optional vendor `replaceAll` is restricted to false here. |
| `PUT /api/v2/documents/{documentId}/draft/{draftId}/app` | `AppPutBody`: complete `{html, settings?}`; creates the first App if the existing draft has none. This helper requires explicit locked settings. |
| PATCH/PUT response | `AppPatchResponse` / `AppPutResponse`: document `identifier`, `draftIdentifier`, name/description, `app: {settings}`, optional warnings. Identity is checked, then GET is independently repeated. |

The vendor PATCH also accepts settings, but replacing them replaces the settings object. This adapter omits settings and requires readback to preserve all current settings. Initial PUT is a separate operation and refuses an existing App or dashboard. Auto-draft, document creation, query creation, delete, publish and dashboard export are unavailable through this adapter. The public contract does not establish a named App draft export route, so use separately captured native preview evidence with its exact App/draft/state identity. Do not relabel a dashboard export or local HTML screenshot as an App preview.

Exact HTML searches are all-or-nothing according to the API contract. The API is last-write-wins and exposes no reviewed atomic version precondition. Use an exclusively assigned draft during inspection and execution. Local locks, preflight checks and readback detect many changes but cannot eliminate an external editor racing the write. Retain ambiguous intent and reconcile; never automatically repeat PATCH or PUT.

## Current-model and source binding

The target config is the same explicit engagement-local config as the dashboard adapter: `base_url`, `profile`, `document_id`, `draft_id`, `model_id`, `principal_id`, `branch_id`, optional `token_env`. No credential belongs in a JSON artifact or command argument. The named draft must be active, current, and on the exact configured branch. Inspection requires its App subresource, document identity, workbook model and query collection.

Every source query visual and query-bearing repeated placement migrated to this surface must appear in `bindings`. Explicit `target_surfaces` assignments narrow this denominator only with a recorded assignment decision. App-only inputs do not become dashboard control obligations. Hidden upstream Hex definitions and non-query placements do not invent query obligations. Text-only placements do not invent query obligations. Each binding identifies one current workbook query key, the complete supported query, a regular Topic, exact field IDs, and the source asset keys. Supported query grammar is fields, filters, sorts, limit and table. Composite Topics, calculations, unsupported query grammar and unresolvable fields block the helper.

Current shared model, selected branch, effective workbook model, resolved YAML, Topic definitions, query fields, control fields and access-related context are inspected before baseline capture, preparation, execution and reconciliation. For a Data Model Accelerator route, the selected exchange and catalog are also revalidated and pinned. **A selected DMA candidate is not proof of deployment.** The separately observed current Omni model must already provide the reviewed queries and field definitions. This helper neither deploys nor silently substitutes a DMA model.

## Baseline and runtime contract

Baseline spec (`schema_version: 1`, `kind: analyst_existing_omni_app_baseline_spec`) requires:

- `requirements_path`: source-pinned visual requirements with App selected, a decided route and decision reference.
- `runtime_path`: reviewed runtime contract described below.
- `review_ref`: the review reference.
- `bindings`: `{source_asset_keys, query_key, topic, query, field_ids}` entries.

The runtime contract (`schema_version: 1`, `kind: analyst_app_runtime_contract`) requires `review_reference`, nonempty `evidence_paths`, and `state_contract` references for loading, empty, error, restricted, stale and reset states. `components` entries contain `{component_id, query_key, runtime_fragment, query_reference}`. Each query reference must name the exact bound query key and appear in a unique, inspected inline-script fragment. Each bound query must have a component.

Use [native data input](native-data-input.md) for the linked qualification evidence: exact callback/export distinction, transport field keys/types, status/error envelope, completeness and current state. Retain details in existing query items or local artifacts referenced by `evidence_paths`; do not add invented fields to this helper's strict runtime schema. Label constructed fixtures separately from observed native payloads.

When the selected design depends on an asset, media, live-content or custom-visualization path, use [native capability checks](native-capability-checks.md) early in the actual permitted host. Link the scoped record through existing `evidence_paths` and declare its file in the requirement's `delivery.dependency_paths`; neither metadata nor a URL/load event proves effective behavior. Optional [experience utilities](advanced-visualization.md) belong only in reviewed owned regions or the qualified initial build. They are not an Omni SDK and do not alter this helper's strict schema, query authority or protected fragments.

`controls` entries contain `{source_asset_keys, component_id, query_keys, topic, field_ids, runtime_fragment, reset_fragment, contract_reference}`. Every migrated source control must be represented. Query keys and fields must match the inspected query scope and current Topic definitions. Both control and reset fragments must be present exactly once and explicitly reference their query keys. Preserve source default/null/multi-select behavior, listener exclusions, drill navigation and reset expectations in the independent cases. A missing compatible control remains blocked or explicitly deferred; a query mapping alone does not migrate it.

Fragments are extracted from the actual inspected native starter; this package does not define a speculative Omni browser SDK. Fragment checks establish retained reviewed code, not execution or security correctness. Code review and independent native runtime cases remain required. A mock page, copied screenshot, or static fragment is never native verification. Test fixtures intentionally use synthetic JavaScript names and do not document a vendor API.

The assembled candidate must retain those exact fragments. A data-adapter repair does not permit editing a protected fragment or removing its baseline requirement. If it changes that boundary, use a separately qualified supported authoring/review route and establish fresh evidence; the bounded edit helper remains unchanged. Rehearse the built HTML's actual script order/scope and an affected result/error path, then retain native observation as a separate lane.

## Preparation and execution

Candidate spec (`schema_version: 1`, `kind: analyst_native_app_spec`) requires `requirements_path`, `baseline_path`, `patch_path`, `review_ref`, and `owned_regions: [{start, end}]`. Region markers must be unique and nonoverlapping in the inspected HTML. The patch file has exactly `{htmlEdits: [{search, replace}]}`. Searches must occur once and lie fully within a reviewed region; edits cannot inject the boundary markers. Retained runtime/control fragments, all query definitions and unrelated content remain intact. Native HTML is bounded to 2 MiB; evidence records are also bounded.

Commands, with all paths relative to the engagement except `--workspace`:

```sh
python omni_app_native.py --workspace /absolute/engagement --target app-target.json capabilities
python omni_app_native.py --workspace /absolute/engagement --target app-target.json inspect
python omni_app_native.py --workspace /absolute/engagement --target app-target.json baseline-capture --spec app-baseline-spec.json --output app-baseline.json
python omni_app_native.py --workspace /absolute/engagement --target app-target.json prepare --spec app-spec.json
python omni_app_native.py --workspace /absolute/engagement --target app-target.json execute --candidate EXACT_SHA256 --authorization-ref REVIEW_REFERENCE
python omni_app_native.py --workspace /absolute/engagement --target app-target.json reconcile --candidate EXACT_SHA256
```

Preparation returns the immutable candidate path and digest. Execution requires an explicit authorization reference and the exact candidate digest, rechecks all current source/model/runtime pins, persists intent before PATCH, and reads the App and model back. Unknown outcomes cannot be replayed. Reconcile reads only the known target. CLI command failures return a bounded error class; sensitive source text is not printed in error messages.

The MCP host separately grants App execution to an operator-selected exact candidate digest; a dashboard execution grant cannot authorize App writes. Do not share dashboard and App document identities in a `both` migration. Evidence and journals are isolated under `.omni-app-native` and `.omni-native` respectively.

## First App construction on an existing workbook draft

An operator must first create or choose an **App-only destination workbook** with the reviewed query tabs, create the named development draft on the exact selected branch, and assign the draft exclusively for this operation. Do this through the qualified Omni UI/workflow; this helper does not create documents, drafts, Topics or queries. A dashboard destination is rejected rather than removed. A separate known native App may supply a reviewed bridge/runtime example. Do not copy its document/query IDs blindly: qualify the bridge against this workbook's exact query keys and current access context. If the actual native bridge cannot be established, construction is blocked by the missing runtime review; do not substitute invented SDK calls or ship the synthetic test bridge.

`inspect-initial` reads the exact named draft, query collection and identity. The document must have no dashboard containers, controls or dashboard settings; its App subresource must return 404 while the document also has no App. An inconsistent 404 is rejected. The first PUT body is `{html, settings}` with nonempty UTF-8 HTML up to 2 MiB and exactly these documented locked defaults:

```json
{"allowClipboard":false,"allowDefaultMapProviders":false,"allowDownloads":false,"allowExternalNavigation":false,"allowFullscreen":false,"allowInternalNavigation":false,"externalNavOpensInNewTab":true,"navAllowedDomains":[],"navAllowedDomainsEnabled":false,"safeDomains":[],"safeDomainsEnabled":false}
```

No resource-policy widening is available in this lane. Declared external `src`/`href` and CSS URL resources are blocked locally. This check is not a JavaScript security scanner: code review, browser policy and native restricted/error-state tests remain required. The vendor may omit default keys in readback; only the audited defaults above are normalized, and unexpected settings or permission widening fail readback.

Initial baseline spec (`schema_version: 1`, `kind: analyst_initial_omni_app_baseline_spec`) has `requirements_path`, `runtime_path`, `body_path`, `construction_review_path`, `bindings` and `review_ref`. The existing runtime/query/control schema above applies to the reviewed new body. `construction_review_path` must contain exactly:

- `schema_version: 1`, `kind: analyst_app_construction_review`.
- Nonempty `exclusive_draft_reference`, `native_bridge_reference`, `resource_policy_reference`, and `behavior_reference`.
- Nonempty `evidence_paths` pointing to engagement-local review/qualification artifacts, pinned byte for byte.
- `state_fragments`: unique inline-script fragments keyed `loading`, `empty`, `error`, `restricted`, `stale`, `reset`, `run`.
- `input_bindings`: one entry per runtime control, each containing `input_id`, `source_asset_keys`, `query_keys`, `mode`, `value_type`, `default`, `allowed_values`, `minimum`, `maximum`, `change_fragment`, `reset_fragment`, `review_reference`. Source/query lists must exactly match one runtime control; the input ID must exist in the body and both fragments. For `governed_filter`, the existing runtime control pins Topic fields. `enum` inputs require a nonempty string domain containing the default, with minimum/maximum null. `number` inputs require finite min/default/max within bounds, with allowed_values null.

A reviewed local scenario is explicitly separate from a governed metric. Optional runtime `scenario_controls` entries have exactly `source_asset_keys`, `component_id`, `query_keys`, `input_id`, `minimum`, `maximum`, `default`, `formula_reference`, `runtime_fragment`, `reset_fragment`. They use `mode: local_scenario` and numeric input bindings with identical bounds/defaults; they do not invent a Topic field. Preserve source formula/rounding/null behavior in the review and independently test the resulting output. A scenario must not relabel a locally computed value as an independently verified governed measure. Operational actions and writeback remain independent unresolved obligations unless separately qualified.

Initial candidate spec (`schema_version: 1`, `kind: analyst_native_app_initial_spec`) has `requirements_path`, `baseline_path`, `body_path`, `review_ref`. Preparation pins the full body, source, model, exact query definitions, bridge, input domains and review evidence. The immutable candidate uses `operation: initial_put`; its approval is separate from bounded edits:

```sh
python omni_app_native.py --workspace /absolute/engagement --target app-target.json inspect-initial
python omni_app_native.py --workspace /absolute/engagement --target app-target.json baseline-capture-initial --spec app-initial-baseline-spec.json --output app-initial-baseline.json
python omni_app_native.py --workspace /absolute/engagement --target app-target.json prepare-initial --spec app-initial-spec.json
python omni_app_native.py --workspace /absolute/engagement --target app-target.json execute-initial --candidate EXACT_SHA256 --authorization-ref INITIAL_REVIEW_REFERENCE
python omni_app_native.py --workspace /absolute/engagement --target app-target.json reconcile-initial --candidate EXACT_SHA256
```

The MCP host uses the same methods with independently configured `--allow-app-initial-candidate` and `--app-initial-authorization-reference`. Ordinary App authorization cannot execute an initial candidate and initial authorization cannot execute an edit. Intent is durable before PUT; an unknown result is reconciled without replay. Readback must add only the expected App subresource/body/settings, preserve all query definitions and unrelated workbook state, and retain the exact model/draft/branch/principal context. These checks cannot eliminate the documented last-write-wins race; exclusive draft use is an operating requirement. Subsequent edits need a fresh existing-App baseline and the ordinary bounded edit workflow.

### Reusable input controller

[`../scripts/query_controller.js`](../scripts/query_controller.js) is package-owned browser JavaScript with **an OAA adapter interface, not an Omni SDK**. Inline the reviewed controller in the candidate and supply `bridge({queryKey, filters})` using a separately qualified native bridge for the exact query. The bridge returns `{rows:[...]}` and classifies denied access with `code: FORBIDDEN`; credentials, arbitrary URLs, SQL and query definition changes are not accepted by the controller. Input IDs are reviewed mappings, not automatically inferred Omni filter field names.

`createQueryController({queryKey,bridge,inputs,onState,deriveScenario?})` returns `run()`, `change(inputId,value)`, `reset()`. Inputs specify `id`, `mode` (`governed_filter` or `local_scenario`), `type` (`enum` or `number`), `default`, and `allowedValues` or finite `minimum`/`maximum`. `onState` receives loading/ready/empty/error/restricted/stale/reset; the UI must use safe text rendering and wire visible controls plus Run/Reset actions. Invalid domains reject locally; edits invalidate outstanding results; late responses are ignored. `deriveScenario` receives a copy of governed results and local scenario inputs, so scenario display does not overwrite the original governed result. No automatic network/SQL/credential access exists in the controller. Package tests execute only its own synthetic template and transport; they do not execute supplied Hex code or establish native runtime acceptance.

## Return and acceptance boundary

`verify_delivery(root, spec)` recomputes a surface proof from `candidate_path`, `execution_receipt_path`, and `coverage_path`, including current source and selected DMA pins, baseline, stored intent, exact App/query/settings readback and independently recomputed case coverage. It performs no tenant call. A standalone return adds `surface: app` to the usual standalone return spec and requires an explicit standalone scope with no DMA import. A combined migration needs separate surface proofs and distinct documents. A standalone combined spec has exactly `schema_version`, `kind: analyst_standalone_migration_return_spec`, `surface: both`, `scope_sha256`, `surface_deliveries`, and `unresolved`. The `surface_deliveries` map has `app` and `dashboard` entries, each with the three proof paths above. One supplied proof may produce an incomplete partial record; both are recomputed for the aggregate. Source, deferred-unit, independent-listing and QA gaps remain incomplete, and a selected DMA import is rejected on this standalone path.

Native runtime, keyboard/accessibility, reduced-motion behavior, security/access, results, filter/reset, denied/empty/error/stale states, responsive layout and performance remain separate case obligations. Missing or deferred cases remain gaps. Recorded readback never sets `native_verified`, `business_accepted` or `migration_accepted` true and never grants publication. Local consistency proves retained evidence, not remote freshness or authenticated business acceptance.
