# App caching and refresh preferences

Use at Stage D for a query-backed App, after A–C establish source coverage and
known update cadence. Reuse an attributable current choice for existing Apps and
focused repairs. An inherited migration policy is evidence to confirm, not a new
package default. Static illustrations need no query-refresh questionnaire.

## Sequence the interview and handoff

| Stage | Owner and retained evidence |
| --- | --- |
| A–C | BI/analyst establish accessible source scope, known update cadence and supported cache controls; storyteller records when claims remain valid or must be withheld. Unknown cadence stays unknown. These findings inform the interview, not an invented App refresh policy. |
| D | Product owner asks the cache/refresh/expiry question in the normal discovery batch, reuses attributable answers and records the actual decision in the required interaction requirement. “No custom policy” is a complete answer; an unanswered question remains open. |
| E | All three concepts honor that decision. Resolve its controls, triggers, timing, hidden/return behavior and stale/recovery presentation in the chosen design and linked query contract. Do not silently change the policy to suit a concept. |
| F | App engineer implements that same selected policy; BI qualifies the native cache behavior; QA compares query activity and display states with the recorded answer. Changed policy returns to the affected discovery/design record before implementation. |

The North Star and specialist handoffs project this one requirement. They are not
separate policy records that specialists may independently reinterpret.

## Ask in user language

Include this in the existing discovery batch when unanswered:

> How should this app keep its data up to date? We can keep Omni's existing caching
> and let you refresh manually, refresh when you return to the app, refresh at an
> interval while you're using it, or use a custom policy. Would you like any
> automatic refresh or expiry, or should we leave those off?

Recommend based on the actual source and task. A historical demo usually needs no
automatic expiry; a monitoring workflow may need a selected refresh cadence.
Explain that repeated queries can add latency and warehouse cost. A frequent
refresh cannot make an upstream dataset update more often.

Only ask the applicable follow-ups:

- Automatic refresh: what interval or return-after-inactivity threshold, and what
  should happen while the page is hidden? Default proposed behavior pauses hidden
  polling and coalesces a return into one request; it is not a standing schedule.
- Cache preference: keep the existing Omni query-cache policy, or request a fresh
  query on each selected refresh where the native bridge supports it? Explain the
  cost before recommending bypass. A requested cache duration must be qualified
  against the actual supported setting; a client timer cannot set Omni's cache TTL.
- Expiry: should older displayed results simply show their retrieval time, show an
  out-of-date indicator while updating, or be withheld after an agreed maximum age?
  Ask for an age only when expiry is wanted or a verified business rule requires it.

Clarify ambiguous “no caching”: it may mean fresh queries, no automatic refresh,
or no custom policy. These are different choices. Reuse explicit delegation with
its scope; silence is neither delegation nor acceptance of an interval.

## Keep the layers separate

| Layer | Decision and boundary |
| --- | --- |
| Source freshness | Source watermark/update cadence, if known. Retrieval time is not source time. |
| Omni query cache | Inherit existing behavior unless the user selects a qualified override. No model/connection/shared-cache changes from an App preference alone. |
| Refresh triggers | Initial load and manual refresh; return/interval triggers only when selected. An age check is not a query. |
| Display age | No automatic age-based expiry unless selected or required by a verified business rule. With no expiry, “ready” is a usable accepted snapshot, not a live-data guarantee. |
| Recovery | Retain-and-label versus withhold, retry/backoff, in-flight handling and preserved view/filter/selection. Never retain results across access loss or a different query/persona/filter scope. |

The package's neutral implementation posture is existing Omni cache behavior,
initial/manual loading, no added polling or focus refresh, and no client age cutoff.
Do not add `cache: false`, a five-minute expiry, or hide valid values solely because
time passed as a convenience default. No custom policy does not mean disabling
Omni caching, removing source-freshness rules, or suppressing errors/access checks.
Existing Apps retain their selected behavior until an authorized scoped update.

Three common answers must remain distinct:

- **No custom policy:** inherit Omni caching, initial/manual loading, no added
  polling/return refresh, and no age cutoff. Record the actual answer.
- **Periodic refresh without expiry:** record the chosen interval and hidden/return
  behavior, inherit caching unless separately changed, and keep maximum display
  age null. Periodic queries do not imply expiry or cache bypass.
- **Fresh queries with expiry:** qualify the bridge's supported cache override,
  record the selected refresh triggers and positive age limit, and implement the
  chosen stale/withhold and recovery behavior. This does not change shared cache
  settings or promise fresher upstream data.

## Record and hand off one decision

Use a required `interaction` requirement in the existing design intent for a new
query-backed App. Keep it unresolved with its question until there is an actual
answer or explicit scoped delegation; the neutral posture is not a fabricated
user decision. Reuse existing intent checks for unresolved required choices rather
than creating a separate approval ledger or versioning every historical engagement.

Index that row with `product.data_refresh: {"schema_version":1,
"requirement_id":"app-data-refresh"}`. Follow the
[data-refresh intent contract](../../omni-artifact-accelerator/references/product-intent.md#data-refresh-index)
for the exact value fields and scoped delegation. The index points to the answer;
it does not duplicate it. New App D checkpoints retain this context, and dependent
concept work waits for a resolved answer or justified not-applicable scope.

Record the decision reference and a structured `value` describing query-cache mode,
refresh triggers, optional interval/return threshold, hidden-page behavior, optional
maximum display age, stale display/recovery and source-time evidence. Explicitly
record “no custom policy” when chosen. Omitted/null maximum age means no client
time-based expiry; do not substitute a numeric sample. These fields are descriptive
intent, not an Omni API payload. Record `{"kind":"app_data_refresh",
"mode":"no_custom_policy"}` for that actual choice; custom values keep refresh,
cache and expiry separate. A data-free App uses `mode: "not_applicable"` with its
scope rationale, not a fabricated query policy.

Carry that requirement into the selected detailed design, linked query contract,
engineer assignment and QA cases. BI qualifies actual cache controls and update
evidence; engineering wires only selected triggers; QA verifies the actual policy.
The selected design's `data_refresh_handoff` binds the exact interview context to
its implementation explanation and concrete `qa_cases`. North Star and packets
carry current policy/readiness; a changed answer must be reconciled before they
can support the build. Implementation annotations alone do not reopen the interview.
If the user requests an unsupported cache TTL or freshness guarantee, record the
gap and offer supported alternatives without changing shared settings.

## Implementation and review

Use the qualified bridge's existing cache behavior when inheriting; do not invent
provider options. OAA's resource and scene-data helpers accept omitted/null
`maxAgeMs` for no age cutoff, or an explicitly selected positive supported limit.
They do not fetch, schedule, or change server cache settings. Both helpers mark
expired accepted results `stale` but retain their values; the App must implement
the selected stale indicator or withholding as well as recovery. Checking age on
return alone is not automatic recovery. The resource helper clears values on `begin` and `fail`; it
does not implement retain-while-refreshing. If retention is selected, implement it
explicitly at the App boundary with scope/access checks and honest status labels.

Verify only applicable paths: idle beyond the former cutoff with no expiry;
selected expiry; hidden/return triggers and query counts; one in-flight run;
manual refresh; error/denied and changed-scope clearing; source versus retrieval
time. Preserve view, selection and camera during a same-scope refresh. Pause and
dispose selected timers/listeners. Record source simulation and observed native
behavior separately; source review cannot prove effective server cache behavior.
