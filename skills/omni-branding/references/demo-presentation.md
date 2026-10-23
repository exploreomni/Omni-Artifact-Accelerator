# Presentation identity, aliases and demo geography

Read when a user asks to rename source entities, make sample data customer-themed, or place it in a different geography. Reuse the current [brand contract](brand-contract.md) and [saved intent](../../omni-artifact-accelerator/references/design-intent.md). These are descriptive engagement decisions and evidence, not a new import schema or automatic permission service.

## Select the mode from the actual request

| Mode | Meaning |
| --- | --- |
| Original source | Preserve original entity names, categories and locations. Apply selected visual branding without implying the data belongs to that brand. This is the default for faithful migration. |
| Verified customer | Use customer identity/location mappings supported by supplied authoritative evidence. Retain the crosswalk and uncertainty; similar names or a logo do not prove an entity match. |
| Authorized fictional demo | Apply user-authorized invented presentation labels or locations to the specified sample population. Disclose the fiction and preserve original lineage/calculations. It is neither an official catalog nor business equivalence. |

Capture the chosen mode, affected surfaces/entities, purpose and actual decision reference in the existing brand/design items. Reuse the official website, selected logo and sourcing authorization already supplied; follow an explicit website/no-research or no-logo choice. Ask only for a consequential unresolved distinction. Permission to use a logo or website is **not** permission to relabel data, relocate stores or invent a product catalog. Conversely, an explicit in-scope demo rename already authorizes those presentation changes; do not ask again. It grants no source-model mutation or unrelated publication authority.

## Keep a reversible identity map

Retain aliases as a separate versioned artifact, with source definition/inventory pins, the scoped identity denominator, mapping version, qualification and decision reference. Use original stable IDs at their actual scope. When no single stable ID distinguishes the entity, declare an ordered composite identity with exact encoding; never join by a display caption or generate identity from the new name. Keep source values intact and return display fields separately.

This **original synthetic fragment** illustrates a local presentation map, not a required helper schema:

```json
{
  "mode": "authorized_fictional_demo",
  "decision_ref": "decisions/demo-names-v1.json",
  "identity_fields": ["source_code", "source_name", "source_category"],
  "identity_encoding": "JSON array string, original values in declared order",
  "products": {
    "[\"p-17\",\"Original lunch roll\",\"Lunch\"]": {
      "name": "Cinder Garden Sandwich",
      "category": "Demo Lunch",
      "source_code": "p-17",
      "source_name": "Original lunch roll",
      "source_category": "Lunch"
    }
  }
}
```

Cover the complete selected population, including relevant groups/categories and non-product entries; state any explicitly excluded scope. Repeated labels must not merge source keys. Prefer distinct category/group labels when they identify separate partitions; if display names collide, keep original keys in selectors/calculations and show a stable disambiguator such as code. Record collisions and their handling. Do not invent a meaning for an unknown original category to make the theme more attractive.

Aliases change presentation only: preserve query IDs/fields, joins, grouping keys, filters, sorting semantics, quantities, extended amounts, distinct populations and all numerical results. Search may intentionally include display aliases, but selecting an alias must still bind the original identity. An alias never supplies missing metrics, customer attributes, business equivalence or semantic authorization. Changing the grouping or meaning is a separate analyst/model-owner decision.

Check current source pins and exact identity coverage before applying the map. Missing keys, changed definitions, ambiguous duplicates or a stale map block the affected branded handoff; do not silently assign the first alias, drop rows or fabricate a replacement. Refresh the map against the changed scope. An explicitly labeled original/unmapped preview may remain useful without claiming complete demo treatment. Pin selected map bytes through the existing artifact/intent dependency mechanism; arbitrary nested paths are not automatically tracked. Changed map bytes reopen affected identity/copy/visual checks, not unrelated metric definitions.

Keep original identity available in scoped lineage/evidence and, where appropriate, an accessible source-details view. Give users a concise visible disclosure that names/locations are fictional aliases and measures retain the source population. Avoid dumping private lineage into public UI. Customer-themed sample data must not be described as that customer's observed sales, sites, current catalog, prices or operating performance.

## Geography is a separate evidence decision

Record each location's source, precision and mode independently of the decorative map:

- **Verified location:** authoritative entity-to-coordinate/address evidence; retain its date and resolution.
- **Approximate reference:** city/region/postal centroid or another general reference. Label that precision; never call it the exact facility or derive unsupported distance, coverage or demographics from it.
- **Manual fictional placement:** user-authorized demo city/coordinates linked to the unchanged source entity ID. Label the location as invented; it is not a relocated warehouse record or observed business footprint.

Renaming a city does not relocate existing coordinates. Reconcile map points, labels, tooltips, regions, rankings, detail views and accessibility text against the selected location map. Keep region membership tied to declared source identity unless a separate presentation grouping was explicitly selected and labeled. Do not infer demographics, routes, service radius or physical product movement from decorative geography. If placement evidence is absent, retain a non-geographic view or a disclosed unresolved placement rather than manufacturing real coordinates.

## Handoff and affected review

Give engineering the selected mode, decision reference, exact map/pins, lookup key, disclosure, collision policy and fallback. Give the analyst original keys and unchanged independent expectations; give storytelling the distinction between renamed presentation and actual source evidence. For migration, retain the original denominator and accepted differences; no alias resets DMA authority, selected routes, access checks or source acceptance.

Use a bounded check: exact selected-key coverage, collision policy, one unchanged numerical reconciliation and the affected labels/locations under selection. Inspect native display when allowed; source-only lookup checks do not establish visible correctness. Avoid a new broad test matrix for a simple authorized rename. Return a specific unresolved mapping instead of silently laundering it into verified customer data.
