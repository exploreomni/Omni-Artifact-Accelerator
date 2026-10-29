# Semantic and behavioral handoff

Record each obligation by original project/object GUID, type/version, placement
and evidence pointer. Repeated visual placements retain their own scope and
interaction even when they share a definition. Dependency identity never comes
from a caption.

| Source concern | Preserve and ask | Target/QA obligation |
|---|---|---|
| Attributes and forms | Attribute ID, form ID/type, element ID and displayed form | Select the intended key and label; test duplicate labels, nulls and sorting. |
| Metrics | ID/order, raw `rv`, formatted `fv`, metric index `mi`, level/dimensionality, filtering/grouping, conditions, transformations, subtotal rules and thresholds | Analyst defines grain/population; BI/DMA translates only reviewed semantics. Test totals independently; no function-name substitution. |
| Prompts | Unique prompt key, repeatable ID/name, type, required/default, explicit/empty/all/omitted/unresolved answer state | Read actual answers after execution; required unanswered prompts block parity. |
| Filtering | Report/extraction and prompt, chapter, pre-aggregation view/template, post-aggregation metric limit | Retain each stage and affected visualization. Test changed/reset states and exclusions. |
| Navigation and placement | Chapters/pages, selectors, drill links, visualization-as-filter, object replacement, page-by, parameters, reused visual placements | Map supported behavior explicitly. Preserve alternative or deferred obligations where Omni differs. |
| Documents and exports | Overlap, page breaks, sections, conditional formatting, headers/footers, PDF export settings and static imagery | Separate data equivalence from print/pixel fidelity. Excel flattening is not an authoritative layout. |
| Security | Security-filter definition/levels, memberships/assignments if authorized, principal and selected project | Definitions are not effective access. Require allowed/denied persona cases; no security filters expressed only as UI controls. |
| Runtime | Definition version, source instance, observed state, total/current/offset/limit, partial flags, watermark and cache | Complete numbers only from a qualified shape and population. Source expiry/cache never chooses the target freshness policy. |

Existing governed Omni fields are the first reuse candidate. For gaps, send the
source pins, grain, relationship/formula/security requirements and independent
expectations through the current DMA request/response contract. Retain unresolved
status until validated responses return; a candidate response is not acceptance.
No dedicated MicroStrategy DMA producer format is available in this package.

Unsupported subtotal, consolidation, hierarchy, prompted-result or cube profiles
remain source evidence and explicit acceptance work. Never flatten a complex
result until it appears comparable. A query result and a screenshot/PDF need
separate evidence and cannot substitute for each other.
