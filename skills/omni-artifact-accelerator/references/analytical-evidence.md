# Analytical evidence across implementation and refinement

`execution_analysis` reuses the existing numerical comparator and preserves its
source/context/principal/completeness requirements. Comparing a target bridge with
its target base establishes self-consistency, not independent migration proof.

## Explicit result identity

The `normalize` request contains exactly `source` (path/hash pin), `layout`
(`objects` or `columnar`), `source_fields`, `bindings`, and a new `output` JSON
path under private `evidence/` or `deliverables/`. Each binding has explicit
`source` and `target` field IDs; every source field needs a unique target.
Object rows must contain declared keys. Columnar input contains exactly `columns`
(unique field IDs) and `rows` (equal-width arrays).

Mapping uses field identity and explicit column metadata, never `row.values()`,
guessed aliases or silently dropped fields. Values are preserved: zero, null,
negative and empty remain distinct. Type conversion and tolerances belong to the
existing explicit comparison contract.
Expanded output is checked against the byte budget before writing. JSON decimal
tokens that would lose precision during normalization are rejected; retain them
through an explicit decimal-string contract. The numerical comparator preserves
JSON decimal tokens as decimal values rather than comparing rounded binary floats.

## Independent comparisons

The `compare` request contains `comparison` and `provenance` pins plus `output`.
The existing `analyst_numeric_comparison_spec` retains the same provenance pin
under `independence_provenance`; the core comparator rechecks it on reuse.
Provenance contains exactly:

- `source_basis`: `original_results` or `independent_source_execution`.
- `source` and `target`: distinct identities, each with `system_ref`, `artifact_id`, `version`.
- `original_results`: pin to the actual source result, or its raw file for a source-specific normalized format.
- `execution_evidence`: nonempty list of original evidence pins supporting that source provenance.

Matching exports may have identical bytes but must be separately retained results.
Target self-consistency cannot enter this migration route. Supplied provenance
remains declared evidence, not authenticated execution. Preserve original source
IDs, query logic, filters, timezone, period, population, access and completeness.

## Presentation and semantics

For label/color/spacing repairs, preserve reusable business measures. Use display
formatting or separate presentation fields; never suppress labels by converting
legitimate zeros into nulls in shared metrics. A genuine semantic change routes
its original expression, requested difference, independent expectations and affected
consumers through the existing backend handoff. Revalidate the returned exact model
version; successful rendering is not semantic acceptance.

Classify source behavior as retained, explicitly accepted adaptation, unsupported
or unverified. A fixed arrangement is not a dynamic treemap. Resolve date-filter
identity and propagation from evidence rather than guessing. Missing source
evidence remains inconclusive.

## Changing-data review

Exercise affected journeys with empty and single-category results, skewed values,
changing ranks, long labels, negatives, null/zero distinctions, partial and new
periods, and supported category counts. Filters, details, exports and narrative
claims must retain the intended scope. Perspective/spatial views need exact-value
alternatives. These are scoped obligations, not a universal chart/layout template.

Preserve accepted quality ambition and purposeful interaction through corrections.
Source review cannot certify visual polish. Team rollout needs actual allowed/denied
principal and export observations; owner-only access proves no audience readiness.
Retain a confirmed maintainer, chosen refresh policy, failure behavior and recovery
instructions in delivery evidence.
