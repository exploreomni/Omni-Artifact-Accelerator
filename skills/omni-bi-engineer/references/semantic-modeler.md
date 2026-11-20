# Standalone Omni Topic candidates

Use the project’s guarded semantic modeling route for a reviewed standalone authoring or translation request. The BI Engineer owns a regular Topic over existing physical views. An engagement already owned by DMA uses its existing semantic handoff and owner. Reuse a suitable governed Topic when discovery identifies one. Read the [source and license record](semantic-modeler/PROVENANCE.md) when maintaining the supported grammar.

## Build contract

The first-party pure function `build_candidate(spec)` in `scripts/semantic_modeler.py` accepts JSON values. The project workflow loads the pinned baseline and optional source inventory. The reviewable `files` dictionary contains UTF-8 native YAML. There is no standalone execution entrypoint. The function does not fetch, install, change a branch, grant access, execute warehouse SQL or deploy content.

A complete synthetic input follows. Counts, identities and evidence references belong to an invented fixture. For actual work, use the exact branch inventory and review references.

```json
{
  "schema_version": 1,
  "baseline": {
    "model_id": "workshop", "branch_id": "dev-branch", "evidence_ref": "branch-inventory-17",
    "topic_names": [], "relationships": [],
    "views": {
      "orders": {"physical_binding": "DEMO.GOLD.ORDERS", "dimensions": ["id", "account_id", "net_amount", "tenant_id"], "measures": []},
      "accounts": {"physical_binding": "DEMO.GOLD.ACCOUNTS", "dimensions": ["id", "region"], "measures": []}
    },
    "user_attributes": ["tenant"], "access_grants": ["analyst"]
  },
  "topic": {"name": "order_review", "base_view": "orders", "label": "Order review",
    "fields": ["orders.id", "orders.net_sales", "accounts.region"]},
  "joins": [{"from_field": "orders.account_id", "to_field": "accounts.id", "join_type": "left",
    "relationship_type": "many_to_one", "review_ref": "account-grain-review"}],
  "measures": [{"view": "orders", "name": "net_sales", "field": "orders.net_amount", "aggregate_type": "sum",
    "label": "Net sales", "description": "Sum of recorded net order amounts in the selected currency.",
    "review_ref": "net-sales-definition"}],
  "policy": {"review_ref": "tenant-and-entitlement-review", "access_filters": [{"field": "orders.tenant_id", "user_attribute": "tenant"}],
    "required_access_grants": ["analyst"]}
}
```

`baseline.topic_names` is the complete selected-branch inventory of regular Topic IDs. `baseline.views` records confirmed native view/field IDs and their existing warehouse bindings. All references are to exact known identities. Supply the branch’s existing global relationship inventory in `baseline.relationships` when requesting joins. For each relevant relationship use `from_field`, `to_field`, `join_type`, and `relationship_type`. Each physical mapping, definition, grain, cardinality, entitlement and policy review remains attributable to the original evidence. The helper checks declarations locally. A reference string cannot authenticate its observer.

The candidate has an explicit base view, selected fields and direct joins. Optional `topic.description` and `topic.path` preserve reviewed wording and model conventions. The default path is `<name>.topic`. A selected conventional path may end with `.topic`, `.topic.yml` or `.topic.yaml`. Lowercase identifier segments only. An existing name anywhere in the model or an existing equivalent path blocks creation. Existing global relationships with the exact requested operands, direction, type and cardinality are reused. A new single equality relationship stays local to the Topic. This writer supports `left`, `always_left` and `inner` with a reviewed `many_to_one` or `one_to_one` lookup. Multiple roles, temporal or composite keys, bridges, fanout and conflicting existing edges require owner review.

New measures live in Topic-scoped `views.<view>.measures`. Supported aggregations are `sum`, `count`, `count_distinct`, `average`, `min` and `max` over one existing dimension of that view. `count` counts non-null values of the specified dimension. Optional `filters` are maps of qualified same-view dimension names to `{"is": literal}`. No arithmetic is inferred for ratios, distinct-on measures, semi-additive facts, conversion, window functions, authored SQL or LODs. Freeze currency, nulls, aggregation grain, filter semantics, type expectations and independent results in the source definition and QA materials. Use the owning model workflow for reusable cross-Topic measures or new warehouse structures.

Every request carries an explicit `policy.review_ref` and lists of `access_filters` and `required_access_grants`. An empty list records a reviewed absence of that Topic-level rule. Existing user attributes and grant names must resolve against the branch baseline. Optional `always_where_filters` accept literal equality on reachable dimensions. Policies define different behaviors from dashboard filters or hidden fields. A new Topic does not inherit every rule of a separate Topic simply because both have the same base view. Preserve all required population and access restrictions; unsupported controls block generation. Test effective viewer and denied personas separately against the candidate’s branch.

## Source translation

Use the existing Artifact Translator adapter output, `kind: omni_analyst_source_inventory`, as `source_inventory`. Preserve the source route, inventory and full captured artifacts in the engagement. Add a `source_bindings` record for each reviewed selection:

```json
{"asset_key": "asset:actual-adapter-key", "target": "orders.net_sales", "semantics": "One currency at a time; sum recorded net amounts once per order after the source filters.", "review_ref": "source-and-result-review-7"}
```

A target can be the Topic ID, a selected field, a generated measure, `relationship:<base>-><joined>`, `access_filter:<view.field>:<attribute>`, `required_access_grant:<grant>`, or `population_filter:<view.field>`. Each emitted crosswalk row preserves the upstream asset key, native source ID when available, scoped identity, locator, source input SHA and exact projected payload SHA. The source snapshot retains the original formulas, filters, security, grain and dependency evidence behind those locators. A supplied mapping needs an actual source ID and a resolved target. The result keeps unmapped, ambiguous and ID-less inventory assets as unresolved. With no resolved reviewed mappings the translation emits a blocked result. An unmapped facet remains an open migration obligation even when another facet on that source asset has been mapped. Independent numerical and access comparisons are still required.

The modeler recalculates the adapter’s canonical upstream-payload and per-asset hashes. For the normalized inventory route it also compares each retained original row, scoped identity, adapter key, locator and asset count. Source adapters can use different object-key schemes. Expected-but-unobserved locators, review obligations and incomplete source definitions retain unresolved status even when a proposed target is supplied. Raw input-byte SHA values and source authenticity require retaining the original acquisition evidence.

## Changes, collision checks and rollback

The candidate’s `destination` preserves `model_id`, `branch_id`, `evidence_ref` and optional `model_version_id`. A `create` change requires absence of the logical name and file path at execution. Its `expected_sha256` is null. Every change includes `sha256` of the exact proposed file bytes. Its rollback record requires those same bytes before removal or restoration. Changes and rollback are inert data. Recheck the exact name, branch, file and expected digest immediately before any separately authorized operation. A changed readback requires a new plan.

For a native branch plan, follow the [Omni Automation operator runbook](omni-automation/README.md). Supply its exact pinned source for `baseline.evidence_ref`; an ordinary offline review reference cannot establish the branch snapshot required by that planner.

`matches_readback(expected_text, actual_text)` compares a generated candidate file with the complete native branch file. It first compares exact bytes. The bounded comparison then accepts equivalent YAML block mappings, flow identifier lists, lists of mappings, quoted scalars, wrapped plain prose/SQL and literal descriptions, or a strict JSON representation of the native file. It compares every key and typed value, preserving list order. A single final line terminator on a human description can vary with native block formatting. A changed SQL reference, join, grant, access rule, fixed-filter value, unknown extra key, ambiguous scalar or unsupported serialization fails the comparison. Supply original model-file bytes and their observed model/branch to the guarded verifier. A hand-written equivalent response cannot establish a native readback.

For a reviewed additive update, provide the exact native path in `topic.path`, raw original UTF-8 text at `baseline.topic_files[path]`, and `update` with its `expected_sha256` and `review_ref`. Supply the complete intended bounded Topic. Only explicit field and join scopes with recognized YAML block keys and strict JSON flow values are supported for editing. Previously generated Topics meet that grammar. Comments and unrelated unchanged blocks retain their exact bytes. Existing fields, measures, labels, join definitions and policies must be preserved. A stale digest, omitted previous setting, weakening policy, changed meaning, ambiguous alias or unfamiliar YAML requires manual owner review. Identical input bytes produce an empty changes/rollback list. A separately qualified native writer can support fewer operations than the local planner.

`status: candidate` means the offline change was constructed. `status: blocked` includes structured `gaps` and no proposed files. Every candidate retains pending native validation, independent data comparison and effective-access verification. The candidate digest binds the destination, full spec digest, proposed bytes and change preconditions. A byte hash authenticates neither provenance nor live deployment. Pass exact evidence to the guarded verifier and retain unresolved source items in downstream delivery.
