# Qualify the runtime path the design actually uses

Read this for external assets/media, refreshable content, a new callback boundary or a capability on which the selected experience depends. Keep ordinary local copy/style edits narrow. This is a qualification workflow, not a new permission or publication gate.

## One small slice before assembly

Use the existing runtime contract's `evidence_paths` and the selected requirement's `delivery.dependency_paths` for the capability evidence file. Preserve target/draft identity, candidate and settings hashes, tool/runtime version, observed time, principal context when relevant, requested behavior, configured settings, actual result, method, evidence reference, remaining limitation and fallback. Record only selected capabilities. These are suggested contents of an evidence artifact, not additional fields in the native adapter's strict schema.

Distinguish `documented`, `configured`, `simulated`, `observed` and `blocked/unobserved` in the record. A URL, HTTP success, stored allowlist, successful iframe load event or matching readback cannot establish effective native behavior. An observation qualifies the exact tested path and state; it is not a global capability promise. Under CLI/source-only constraints, retain the unobserved native lane and continue a useful provisional design. Do not create browser activity to close it.

| Selected path | Small useful qualification | Keep separate |
| --- | --- | --- |
| Governed data input | One required-query sequence through the actual assembled receive boundary and one malformed/error case; use [native data input](native-data-input.md). | Query/export rows, constructed callback simulation, observed native callbacks, model/access acceptance. |
| Static/local asset | Exact bytes/type/dimensions, intended crop/size, supported packaged loading route, then visible load in the native target when allowed. | A valid image file and an actually visible/legible logo. Missing imagery follows its selected fallback, not an invented substitute. |
| Remote image/font | Selected exact origin/path, current permission/configuration, error handling and visible native result. | Reachable URL, configured domain and effective CSP/sandbox/network behavior. No silent permission changes. |
| Embedded media | Provider-supported embed route; effective outer/inner policies and identity; actual controls/readiness/error, followed by scoped user-started playback only when authorized. | Watch-page link, player-frame load, provider readiness and actual playback. Check current provider docs; do not infer behavior across providers. |
| Refreshable content | Source timestamp if available, client retrieval time, completeness, selected staleness threshold, one scoped failure/late-response path. | Client fetch time and source freshness. Unknown source time remains unknown. No SLA or continuous-live claim from a public endpoint. |
| Native authoring | Inspected exact installed command/schema, explicit target/draft, preserved complete query/settings state, exact candidate/readback. | Command success, published identity, native runtime behavior and business acceptance. |

For media, expose idle → loading → ready, or blocked/fallback, with the actual provider's qualified events. These are **application states**, not invented provider events. Set a selected finite loading timeout; a blank rectangle is not an acceptable fallback. Retain a descriptive reviewed source link when one exists. A direct `/embed` URL diagnostic can behave differently from a player within a host; don't carry its result across contexts without evidence. Do not use guessed origins, rewritten identity, proxying or broader sandbox grants to force compatibility. Route a host-level limitation to the host owner.

## Optional reusable utilities

[`experience_components.js`](../scripts/experience_components.js) is a dependency-free OAA utility, **not an Omni SDK**. Copy/include it only where the reviewed build permits; it cannot replace a retained native bridge or protected runtime fragment. It performs no requests, discovery, authentication or policy changes.

- `mapRows(rows, columns, maxRows=10000)` maps exact keys using `{key, as, type, nullable}`. Types are string, finite number, safe integer and boolean. Zero and null stay distinct. It does not coerce decimals, currency or dates; use the separately reviewed precision/date policy for those. Additional columns are not projected; retain original evidence. A row bound is a local safety limit, never proof of source completeness.
- `createResource({validate,onState,now,maxAgeMs})` returns `begin(contextKey)`, `accept(ticket,{data,completeness,evidenceRef,sourceAsOf?})`, `fail(ticket,phase,reason)`, `snapshot()`, `refreshAge()` and `dispose()`. A begin clears prior values; only the current ticket may commit once. Completeness is an explicit `complete|partial|unknown` assertion from the qualified adapter, not calculated by this helper. `ready` means locally accepted with declared complete coverage, not native/current/business acceptance. Client `fetchedAt` is separate from optional `sourceAsOf`. The caller invokes `refreshAge` at meaningful moments; there is no background timer or fetch.
- `createMediaState({onState,stop})` returns `begin(sourceKey)`, `frameLoaded(ticket)`, `ready(ticket,{method,reference})`, `unavailable(ticket,'blocked'|'fallback',reason)`, `snapshot()` and `dispose()`. `frameLoaded` remains loading. Readiness methods are `simulation|provider_event|native_observation`; they remain caller-supplied evidence declarations, not authentication or automated verification. Wire `stop` to the qualified provider's actual stop/pause/destroy behavior; the default no-op performs none. Reject/ignore obsolete events after source changes or disposal. This helper never starts playback.

Use opaque context keys from the selected query/filter generation, not captions. Tokens are local correlation only: if the real bridge cannot associate a response with that generation, the utility cannot invent that association. Constrain overlapping work or qualify the bridge first. Catch validation failures and explicitly fail the current ticket so the affected claim stays unavailable. Do not merge differently scoped resources merely because both say ready.

## Assembly and handoff

Retain the template/modules, exact built candidate, build command and native launch target separately. Register helper and evidence dependencies so a changed file invalidates the applicable review. Check actual classic-script/module scope and dependency order; `window === globalThis` belongs only to a labeled classic-script rehearsal, not a universal browser emulator. Do not bundle credentials or live fixtures.

On navigation/unmount, invalidate in-flight generations, remove listeners, cancel animation frames/timers and stop media through the qualified mechanism. On hidden pages, apply the selected pause policy; on return, evaluate freshness before reusing results. An engineer's utility check cannot close the experience owner's rendered critique or independent QA's native lane.
