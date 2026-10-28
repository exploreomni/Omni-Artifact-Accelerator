# Source behavior and cross-team handoff

Use the shared [migration behavior ledger](../../omni-qa-analyst/references/migration-behavior.md)
and [migration lifecycle](../../omni-backend-handoff/references/migration-lifecycle.md).
This adds CDT-specific questions to those records; it is not a second acceptance
system. Reuse retained answers and capture evidence instead of interviewing the
user independently for every role.

| Obligation | Preserve in the existing contract | If unavailable |
| --- | --- | --- |
| Scope and identity | Space, dashboard numeric ID, Git token, chart token, placement, revision and crosswalk evidence | Keep identifiers separate; hold identity-dependent capture/comparison |
| Data and custom logic | Database binding, SQL/views/snippets, parameters, code language and dependency closure | Route precise semantic gaps to DMA; keep source code inert |
| Global/chart filters | Inherited and local definitions, defaults, hidden/global scope, exclusions, reset and timezone | Retain unknown behavior and obtain source observation; do not infer from YAML alone |
| Controls and drill | Each applicable filter/parameter, affected queries, navigation destination and return state | Record exact target control bindings or explicit unsupported/adapted disposition |
| Visual coverage | Independent expected widgets, non-query content, repeated placements, visible/hidden state and render coverage | Missing/omitted widgets remain in the denominator |
| Numerical evidence | Original exported bytes, identity, filter/persona/watermark, full versus displayed population, types and tolerance | Comparison remains inconclusive; source rendering cannot substitute for results |
| Cache and refresh | Source cache/refresh evidence, requested/observed timestamps, target App policy from user discovery | Do not assume bypass, five-minute expiry or a backend TTL |
| Access and operations | Allowed/denied personas, sharing, database permissions, consumers, exports/schedules and ownership | Keep the lane pending or hand off explicitly; no implicit policy or schedule migration |

Return a dependency-complete source slice to the orchestrator. The translator
preserves the source-to-target crosswalk and original gaps; the analyst owns the
metric interpretation and independent expected examples. The BI engineer chooses
exact current fields and controls, and designers own approved presentation changes.
The source specialist may explain feasibility but must not select a new product
direction or certify its own migration as independently verified.

For backend work, retain the chosen `reuse_existing`,
`omni_semantic_reconstruction` or `warehouse_first_refactor` route and actual scope
decision. `unselected` is discovery only. Use the existing DMA request/response and
selected-candidate records; include affected source assets, grain/filter/security
needs and independent cases. Do not create a new backend engagement for every
chart. A returned candidate is not a deployed Topic.

For target work, use separate dashboard/App candidate and native-readback evidence.
Recheck baseline fields, controls, source hashes and selected backend candidate
before execution. A changed definition, filter, source export or candidate reopens
the affected cases. Treat an uncertain write as a reconciliation task, not a blind
retry. Publication and source retirement retain separate authority.

Before reporting selected-scope completion, reconcile each migrated/deferred/excluded
asset and every required numerical, interaction, access, visual/accessibility,
performance, native and operational case. Retain accepted differences and pending
business review. Manual capture and unobserved lanes remain explicit even when the
local workflow and native readback succeed.
