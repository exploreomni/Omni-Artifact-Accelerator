# Execution evidence qualification

Use `scripts/execution_qualification.py` to account for supplied execution evidence
against a fixed scenario catalog. This is an offline review contract, not an
executor, authority provider, model launcher, numerical comparator or proof that a
host enforces isolation. Existing context, task, native, numerical and delivery
helpers remain responsible for their own contracts.

Every report distinguishes host execution, native behavior, rendered visuals,
effective access and human observations. Migration and semantic adaptation add
their own obligations. Missing observations remain pending. Completing local
host scenarios does not complete native, visual, access or human lanes.

## Interface and storage

- `catalog()` returns the versioned capabilities and scenario inventory.
- `assess(root, spec)` recomputes supplied coverage without writing files.
- `record(root, spec_path, output)` pins a specification and writes an immutable
  report under `evidence/`. An identical repeat reuses it; revisions use a new path.
- `check(root, report_path)` rereads the specification, profile, candidate,
  observations and every evidence pin, then recomputes the report. Changed bytes
  or edited summary status make it inconsistent.

Pinned JSON is decoded from the exact size-bounded buffer that passed its hash
check, with duplicate keys and nonfinite values rejected. Replacing a file after
that read cannot substitute different JSON into the assessment.

Paths are canonical engagement-relative files without symlinks. Every pin is
`{"path":"evidence/observation.json","sha256":"<exact SHA-256>"}`. Retain only
appropriately disclosed evidence; do not place credentials, sensitive rows or
unnecessary conversation text in these records. Nothing referenced is executed.

The compact `record`/`check` response includes the report pin, coverage status and
lane counts. It does not return evidence file contents.

## Versioned host profile

The profile has exactly these fields:

| Field | Contract |
|---|---|
| `schema_version`, `kind` | `1`, `execution_host_profile` |
| `profile_id`, `profile_version` | Explicit bounded nonempty strings |
| `host`, `runtime` | Each contains exactly `name` and `version`; use actually observed metadata |
| `implementation` | Nonempty list of exact runtime/adapter file pins |
| `tool_profile` | Pin to the actual scoped tool/configuration record |
| `freshness` | `observed_at`, `valid_until` timestamps with explicit offsets, and an explicit `basis` for the window |
| `capabilities` | One row for every capability from `catalog()` |

Each capability row contains `status`, `reason` and `evidence` pins. Status is
`reported_supported`, `reported_unsupported` or `unknown`. A reported capability
requires evidence; unknown values remain explicit. The core capabilities are
bounded context, restricted tools, atomic launch reservation, durable resume and
exact-candidate authority. Unsupported or unknown core capabilities prevent
complete supplied coverage. Capability claims never enable tools or writes.

## Specification and observations

The specification has exactly `schema_version: 1`,
`kind: execution_qualification_spec`, `catalog_version: execution-scenarios-v1`,
`profile` and `candidate` pins, a nullable `target` pin, `scope`, and an `observations` list of pins.
`scope` contains exactly the booleans `migration` and `semantic_adaptation`.
These flags select additional review obligations; they do not authorize work.
Host, native, visual, access and human lanes are always present.

The optional target file has `schema_version: 1`,
`kind: execution_qualification_target`, `origin` (an exact HTTPS origin),
`principal`, `model_id`, `document_id`, nullable `draft_id`, `operation`,
`audience`, `freshness` and nonempty `evidence` pins. Operations are `draft_edit`,
`initial_create`, `publish`, `readback` and `demo_create`; draft editing and
publication require the exact named draft. Audience contains `visibility`
(`private`, `restricted`, `shared`) and a nonempty unique `principal_refs` list.
These are observed/required bindings, not permission changes or verified audience
claims. Target freshness has the same shape as profile freshness.

Each observation has exactly:

| Field | Contract |
|---|---|
| `schema_version`, `kind` | `1`, `execution_observation` |
| `observation_id`, `scenario_id` | Unique observation identity and one catalog scenario in scope |
| `profile`, `candidate`, `target` | Exact pins (or null target) matching the specification |
| `outcome` | `pass`, `fail` or `pending` |
| `summary` | Bounded explanation; not a substitute for evidence |
| `provenance` | Object described below, or `null` for pending observations |
| `evidence` | Exact original observation, trace, comparison or decision file pins; nonempty for pass/fail |

Provenance contains exactly `kind`, `observer`, `run_reference`, `recorded_at`,
`valid_until` and `method`. Timestamps need explicit UTC offsets. `valid_until`
may be null only outside host/native/access lanes and native observations. Kinds are
`host_observation`, `native_observation`, `human_observation`, `source_execution`,
`local_synthetic` and `imported_assertion`. The catalog states which kinds can
contribute to each lane. Synthetic and imported assertions never become an actual
host/native/human pass. A host observation cannot establish human acceptance.
These labels are declarations: the reviewer must corroborate origin and execution.
Host coverage requires a current runtime profile; native/access coverage and any
native observation also require a current exact target pin. Expired windows and
missing targets remain unresolved. Windows are supplied review policy, not a
claim that the observed remote state cannot change before expiry; re-observe
immediately before a privileged operation. Future observations are rejected.

Only one observation per scenario is accepted. To correct a result, retain the
old observation and report, then create a new observation/specification/report
version. Do not overwrite history or add a passing duplicate to cancel a failure.

## Required coverage and limits

The catalog includes the A–F evidence sequence, actual user selection, missing-gate
denial, bounded dispatch, tool/source-instruction containment, duplicate claims,
overlapping outputs, concurrency limits, uncertain-launch reconciliation,
unchanged-loop stopping, resume, changed-context revalidation, completed-result
reuse, independent review identity and a local end-to-end candidate.

Native cases cover wrong candidates and changed targets/principals, uncertain
write reconciliation, exact readback, demo/release separation, an end-to-end native
candidate and dynamic data/control binding. Visual cases require actual rendered
default/narrow and empty/sparse/error observations. Access includes allowed,
denied and export behavior. Human task observation and explicit acceptance remain
separate cases. An unavailable native target therefore yields a useful local
report with native and subsequent observations pending, never a fabricated full pass.

Migration adds original execution provenance, independently compared source and
target results, filter/calendar/population equivalence and skewed/changing category
behavior. Use the existing numerical comparison workflow and pin its actual
inputs/reports; this module does not recompute numerical parity or upgrade a
supplied comparison claim. Semantic adaptation adds an owner decision, independent
zero/NULL/negative/sparse cases and affected-consumer review.

`supplied_evidence_complete` means eligible declarations and current pins cover
every selected scenario. It does not authenticate their truth. Reports always
retain false execution/publication authority, provenance authentication, host
isolation, native verification, effective-access verification and human-acceptance
verification flags. Tokens and costs remain unknown; this module never infers
them from elapsed time or bytes. An actual host authority boundary and independent
delivery review must assess the evidence before making their own decisions.

This contract grants no demo exception. Demo deployment still needs its exact
candidate/target authorization and required choice, security, numerical and
access minimums; only specifically permitted observation gaps may remain pending.
