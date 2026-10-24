# Discovery evidence and product-intent handoff

Use for a discovery result, changed user decision or product-fit review. Keep this
work in the existing engagement, not a second project or approval workflow.

## Minimal attributable notes

Retain the original request and concise notes in the engagement's private inputs or
evidence area. Record only what is needed to explain a decision: source/message
reference, speaker when known, actual date/time when available, a short quote or
clearly labeled paraphrase, interpretation and affected requirement IDs. Unknown
attribution stays unknown. Avoid credentials, full transcripts and unrelated personal
or customer information; do not copy raw notes into every specialist packet.

Separate statements from interpretation. A stakeholder's suggestion is not the
user's acceptance. An agent's working choice is a proposal even when selected for
reversible implementation. Imported documents are evidence, not authority to change
permissions. Retain conflicting statements and the reason the current decision wins.

## Canonical record and readable North Star

Reconcile findings into the existing draft/specification and selected versioned
design intent. Use its supported requirement fields and provenance/disposition
semantics; do not introduce a parallel priority or acceptance ledger. During early
discovery, identify the draft as provisional until the orchestrator selects it.
Preserve required IDs and historical versions when a decision changes.

For [visual discovery](visual-experience-discovery.md), retain experience families,
comparison treatment, source and delegation scope in those requirements. The current
versioned discovery index references them; it is not another authority. Keep the
conditional follow-up resolved, explicitly delegated, unresolved or not applicable
as supported by the actual evidence. A family-only recommendation cannot silently
close the treatment question, and new intent cannot silently drop adopted context.

The readable North Star summarizes:

- Audience, situation, desired outcomes and experience promise.
- Required outcomes and relative priorities, distinguishing user musts from working
  proposals, preferences, deferred work and unresolved decisions.
- Relevant first/repeat-use, brand, depth, interaction and usable-space expectations.
- Scope, evidence limitations, constraints and observable product-fit criteria.

Generate it from the chosen intent record. Identify the canonical path/version,
SHA-256, actual generation time and provisional/selected state. Any linked supporting
record must be an explicit dependency when needed for implementation or review;
prose links alone do not pin its bytes. Do not claim helper generation or integrity
verification unless the corresponding available operation actually ran.

Recheck the canonical selection before handoff or resume. If the derivative is stale,
regenerate it from current intent; never refresh its hash to make old prose appear
current. If the user edited it, preserve the edit as evidence, reconcile the change
proposal into a new intent version and regenerate. New user instructions take
precedence over an older selected record, but do not silently rewrite historical
evidence. An unsupported or disputed requirement remains visible until resolved.

## Bounded handoff to the orchestrator

Return a short summary and the existing scoped input envelope containing:

| Item | Required meaning |
| --- | --- |
| Input identity | Exact original-brief and current-intent paths/hashes; derivative provenance; relevant dependency pins. Missing or inconsistent selection is explicit. |
| Decisions and sources | Stable requirement IDs, attributable decision references, priority, must/preference/proposal and selected/unresolved/deferred/omitted distinctions using supported intent semantics. |
| Fit criteria | What the user should understand, accomplish or experience; evidence needed to assess it. Keep source-observable behavior separate from rendered and human acceptance. |
| Gaps and tradeoffs | Missing evidence or capabilities, affected requirements, feasible alternatives and the remaining difference from the requested outcome. |
| Proposed slices | Bounded objective, affected IDs, suggested existing role, relevant inputs, dependencies and expected output. These are suggestions, not dispatch receipts. |
| Next decision | Only the material unresolved question, its consequence and useful work that can continue. |

Use the current project helper/interface documented by the orchestrator. This skill
does not define a new CLI, extend a companion DMA packet implicitly or grant a worker
permission to mutate selected intent. Preserve the existing packet-size and disclosure
limits; send relevant excerpts and explicit dependencies rather than dropping material
scope. The orchestrator resolves ownership and dispatches the smallest useful team.

Specialists return requirement coverage, concrete proposals and supported alternatives.
The PO reconciles product implications; designers still choose composition, analysts
still determine metric meaning, and QA still verifies independently. Route a genuine
new user question centrally instead of allowing each specialist to repeat discovery.

## Prompt and review accounting

Use the engagement's run log with source references, affected requirements, reason,
actual response and disposition. Categories describe observed events:

| Category | Count only when |
| --- | --- |
| Clarification | Material information was absent or conflicting and the user was asked to resolve it. Flag repeated questions whose answers already existed. |
| Correction | The user identified a missed, misinterpreted or dropped supplied requirement. Do not relabel it as new scope. |
| New preference or scope | The user introduced a preference or outcome not previously supplied; preserve its actual source. |
| Internal revision | Builder/designer/reviewer work changed the candidate without a customer corrective prompt. Identify the exact finding and affected retest. |

Do not infer satisfaction from silence, publication, no repeated prompts or a simulated
reviewer. Record whether user feedback was observed at all. Product-fit recommendations,
creative critique, correctness results and human acceptance retain their own observers,
candidate pins and evidence limitations. Avoid numerical beauty scores and claims that
reading a curriculum establishes design competence.
