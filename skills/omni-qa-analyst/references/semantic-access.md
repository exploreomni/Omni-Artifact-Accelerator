# Verify a standalone Omni Topic and its effective access

Use the [semantic verification helper](../../omni-bi-engineer/scripts/semantic_verification.py) with original evidence from the engagement. It compares what each intended user could actually query, see and operate on the selected model or branch. The helper runs offline. The host remains responsible for acquisition, authenticated identity, freshness, retention and permission to act.

## Two decisions

- **Model ready** requires the intended user, model ancestry, completed validation, whole Topic readback, independent numerical total and slice, and observed Topic query rights and returned rows for the applicable audiences. An access-constrained or unavailable session stays pending. Do not substitute an organization's key, an administrator, a guessed role or an analyst's successful query for a restricted user's observation.
- **Delivery ready** additionally requires the actual artifact SHA-256, exact destination documents, applicable controls, and persona observations on that revision. A model can be ready before the App or dashboard exists. Later observations can supplement the original model policy with the destination-specific review. Keep model QA, effective document access, business acceptance and permission to publish separate.

Both decisions are scoped to the captured observations. A content digest detects changed bytes. It does not authenticate who captured them or prove that access remains current.

## Verifier input

Call `verify_topic(spec, *, context, topic_name, candidate_sha256, originals, artifact_sha256=None, document_ids=None)`. `originals` maps confined engagement-relative paths to their **original bytes**. The caller resolves registered paths with its existing safe loader. A pin is exactly `{"path": "evidence/...", "sha256": "<64 lowercase hex>"}`. Recipe text, a URL, a declared success flag or a file hash without its original cannot establish a result.

```json
{
  "schema_version": 1,
  "policy": {"path": "evidence/reviewed-policy.json", "sha256": "..."},
  "identity": {"path": "evidence/intended-user-and-models.json", "sha256": "..."},
  "validation": {"path": "evidence/completed-validation.json", "sha256": "..."},
  "readback": {"path": "evidence/whole-topic.json", "sha256": "..."},
  "queries": [],
  "access": []
}
```

Fill the two arrays with pins to each actual query and persona capture. The optional `delivery_policy` is another pin. Each pinned JSON original has `kind`, `source_ref`, a timezone-aware `observed_at`, and the same `scope`. The scope has the tenant `base_url`, shared `model_id`, `branch_id` (null for shared reuse), `topic_name` and `candidate_sha256`. Include the observed `workbook_model_id` and `model_version_id` when present in the caller's context. Use the actual candidate fingerprint for authored work. For existing Topic reuse, the caller binds the whole observed Topic fingerprint to the candidate field and cross-checks it against the independent access observation.

| Original kind | Required material |
|---|---|
| `policy` | Independently reviewed `topic_response_sha256`, `comparisons`, `personas` and later `surfaces` if known. Keep the source of the expected values and explicit filters, grain, denominator, forecast exclusions and time window in the comparison's query or original source reference as applicable. |
| `identity` | Intended author/analyst `identity` from the signed-in user response and `models` indexed by native model ID. Records include shared connection, branch parent and workbook ancestry where applicable. |
| `validation` | Intended user `identity`, validation `run_id`, owning `model_id` (branch for authored work), final `status: "complete"` and actual `errors` list. A failed run or error remains a failure. |
| `readback` | Intended user `identity`, exact effective `model_id`, and complete native `response` containing `success` and `topic` with its exact name and inspected views. |
| `query` | Comparison `id`, intended user `identity`, native `query_id`, full `query`, complete concrete `result` and a separate observation source from the independent policy. |
| `access` | Persona `id` (`allowed`, `restricted`, `default`), actual `identity`, observed effective `attributes` and `probes`. A missing attribute observation differs from a returned empty attribute map. |
| `delivery_policy` | For a destination created after Stage A, bind `policy_sha256` to the unchanged model-policy pin and `artifact_sha256` to the landed revision. Supply `surfaces` and `personas`, mapping each applicable role to an array of additional document/control probes. It may supplement a model-only plan. |

The whole Topic fingerprint is `sha256(analyst_project.canonical(response))` over the regular response object, including the `success` key and the complete `topic` payload. The return key is `topic_response_sha256`. Compact sorted JSON uses ASCII escaping. Do not hash a projection, extracted name, proposed Topic file, or UI summary as the native response.

## Numerical evidence

Each policy comparison has a unique `id`, `level` (`total` or `slice`), concrete `query`, and independently sourced `expected`. Require at least one total and one distinct slice. Retain the actual modeled fields and query filters in the matching observed query. Normalize native output to the same typed columns on both sides, preserving scope, numeric precision and duplicate rows. A comparison result uses this shape.

```json
{"status":"complete","truncated":false,"columns":["region","n"],"rows":[{"region":"north","n":23}]}
```

A total supplies one row. Compare the scoped rows as a multiset. A row limit, partial page, missing result, bare assertion or empty baseline cannot establish numerical equivalence.

## Persona and document evidence

Each reviewed persona entry contains `principal_id`, the expected effective `attributes` and a `probes` array. The actual session must have user-scoped credentials, its matching membership ID, and evidence that it is an ordinary account (`identity.user.isOrgAdmin` is false). Where the native identity surface cannot establish that condition, keep it pending. For a differential policy, exercise three distinct intended users. When a policy explicitly grants uniform access, supply `audience: {"mode":"uniform","basis_ref":"...","reason":"..."}` in the reviewed policy. A nonexistent restricted cohort can then be recorded as `{"not_applicable_reason":"..."}`. Exercise the actual default/unprovisioned behavior. The same ordinary account can stand for the same public/default audience only when both expectations specify empty attributes. Unknown provisioning stays pending.

Each planned probe has `id`, `kind`, `request` and `expected`. The actual probe has the same `id` and exact `request`, an executed `operation_id` and a native-derived `response`.

| Probe kind | Expectations and observations |
|---|---|
| `rights` | Use the Topic name as `request.resource` and `query` as its operation. Expect `allowed` or `denied`. A successful allowed response identifies the returned resource. Add more rights probes for governed fields or operations as relevant. |
| `rows` | Use the Topic as resource and `query-rows` as operation. Retain meaningful query filters/fields, eligibility boundaries and the exact expected set of authorized rows or aggregate witnesses. Expect a complete result object or a denial. |
| `document` | Identify the actual document ID as resource and use the exercised operation such as `open`. Expect `visible` or `denied`. A successful response identifies the document. |
| `control` | Include its resource ID, parent `document_id` and actual operation (for example, listing allowed values or applying a value). Include state, field and input where consequential. Compare a scoped result or an expected denial. |

The response includes an integer `http_status`. An explicit 403 can satisfy an expected denial. An unavailable endpoint, 401, ambiguous 404, timeout or missing persona session leaves the relevant check pending. A successful row/control operation carries `response.result`. A returned empty result can verify an explicitly expected empty set when it is complete. Each delivery observation additionally records its `document_id` and `artifact_sha256` on the probe. Include all intended documents and controls in `surfaces`, for example `{"document":{"resources":["doc-a"]},"control":{"resources":[],"not_applicable_reason":"This document has no input control"}}`. Every applicable persona needs a probe for each surface. At least one actual visible observation must identify each delivery document.

The verifier returns `model_ready`, `delivery_ready`, matched `documents`, `topic_response_sha256`, `checks`, `gaps` and `failures`. A contradiction produces `failed`; absent or limited evidence produces `pending`. `write_authorized` and `origin_authenticated` remain false. See the [synthetic cases](../../../tests/test_semantic_verification.py) for a complete offline example.

## Plan missing access before verification

Use [the offline governance planner](../../omni-bi-engineer/scripts/semantic_governance.py) when a requested audience lacks a reviewed binding or document grant. Pin the inspected current policy and the attributable audience request in the engagement. Call `plan_access(spec, *, context, topic_name)`. The result contains reusable matches, reviewable model fragments, document-specific grant proposals, control scopes and outstanding gaps. It never changes a model, creates attributes or groups, assigns values, or shares content.

For example, a business group needs one existing order dashboard. Its `tier` attribute carries the observed value `business`; `region` carries its allowed row keys. The user requests a Topic grant named `business_users`, a row filter binding `orders.area` to `region`, and a direct view grant for one document. These are three separate changes. The planner can return the following merge fragments if the inspected policy supports all three.

```json
{
  "model": {"access_grants": {"business_users": {"user_attribute": "tier", "allowed_values": ["business"]}}},
  "topic": {
    "required_access_grants": ["business_users"],
    "access_filters": [{"field": "orders.area", "user_attribute": "region"}]
  }
}
```

The model fragment adds one named definition while preserving every other grant. Topic and optional field fragments identify the exact binding location. Merge reviewed keys in the authorized branch. A content proposal names the actual document ID, group ID, captured native read-only role and inspection reference. Treat it as an intent for the content owner to review. The output is neither a native API payload nor confirmation of the effective audience.

**Input contract.** Supply `schema_version: 1`, `current` and `request`. The [complete synthetic example](../../../tests/test_semantic_governance.py) also exercises the existing-policy route.

| Current inspection | Expected evidence |
|---|---|
| `context`, `topic_name`, `evidence_ref` | Exact caller context including tenant origin, shared model, branch or null, principal, and selected Topic. |
| `groups`, `attributes` | One requested existing ID with value `scoped_group` in the inspected group map. For each used attribute, capture its evidence ref, complete `group_values`, `individual_values`, `default_values`, observed `value_mode: "exact"` and `missing_value_behavior: "deny"`. Use scoped assignment summaries. An omitted value, wildcard, unknown default or overlapping entitlement cannot establish a group-exclusive grant. |
| `fields`, `topic`, `access_grants` | Reachable field IDs with kind, existing field grant requirements, and `equality_attributes` identifying validated semantic key and type compatibility for row filters. Capture the Topic's existing grant and row filter lists and model-level grant definitions. A new field binding also needs `bound_topics` to establish its impact. |
| `model_grant_syntax_ref`, `grant_usage` | For a missing grant, identify the inspected native model parameter contract and complete model-wide references to the grant name. The usage record contains `complete`, `evidence_ref` and `bindings`, indexed by grant name with targets such as `topic:orders` or `field:orders.area`. Unsupported grant shapes, combined policies or collateral bindings require owner review. |
| `documents` | For each requested ID, capture its evidence ref, inspection completeness, native `read_only_roles`, `direct` and `inherited` grants by group ID, and `effective` access for the group (explicit null when no grant applies). Account for public, nested-group and other inherited access. Inspect existing controls by stable ID, field and affected `consumer_ids`. |

The request identifies its `request_ref`, one `group_id`, `grant`, `row_filter` and `documents`. Explicit null for a model grant or row filter leaves that policy untouched. A grant identifies its `name`, `user_attribute`, exact `allowed_values` and `target` (the literal `topic` or one qualified field). Each requested document supplies `document_id`, `source` (`direct` or `inherited`), the inspected exact role string and `controls`. Each control supplies its stable `id`, `field` and precise `consumer_ids`. A control can narrow a view and cannot establish row security.

An exact existing match returns `reuse_existing`. A missing scoped element returns `proposal` when all required inputs resolve. An unresolved group, field, attribute, grant definition, effective ACL, parent impact or consumer scope returns `pending` and withholds the patch. Missing inherited access requires a separate review of the parent and its affected documents. Broader roles, organization-wide delivery, changes to other users' assignments, and unsupported native forms need an independently reviewed plan. Validate the model and exercise actual allowed, restricted and default users and target documents after any separately authorized change.
