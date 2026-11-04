# Observation-limited native demonstration

The offline `native_authoring.py` helper has a distinct demonstration preparation
route for a new App document. It never creates a document, calls an API, reads
credentials, changes permissions or supplies authorization. Creation publishes an
initial version immediately, so the actual operator must qualify and authorize
the exact target, principal, audience, request and operation before any write.

Use `prepare_demo(project=..., artifact=..., spec_artifact=..., demo_artifact=...)`
or `app-demo-prepare`. Input paths are the selected `html`, the existing bounded
create `spec`, and a `demo` scope file. Freeze all three exact files in the current
candidate. The existing release-only `prepare_create` path is unchanged.
Guarded freeze uses retained snapshots: preparation verifies the current frozen
envelope's original-path/hash mapping and each snapshot's stage pin, then retains
that mapping as `reviewed_artifacts`. Original working bytes must still match;
a matching hash on an unrelated retained file cannot replace the mapping.

Prerequisites are current A–E evidence, an exact selected frozen App candidate,
zero stage-gate findings and all four current consultations. Security and product
owner must be resolved. UI/UX and QA must be resolved or explicitly unobserved on
a rendered/native/human basis. Any changes-requested result, source review gap,
missing consultation, stale source or changed candidate rejects preparation.

The demo scope has exactly:

| Field | Contract |
|---|---|
| `schema_version`, `kind` | `1`, `native_demo_scope` |
| `html`, `create_spec` | Exact `{path,sha256}` pins matching the supplied paths |
| `destination` | Exact origin, model, new document identity, operation, principal and audience |
| `minimums` | `security`, `numerical`, `permission`, `design`, all recorded resolved |
| `pending_observations` | One or two explicit UI/QA observation gaps matching current consultations |

`destination` contains `origin`, `model_id`, `document_id`,
`operation: initial_create`, `principal` and `audience`. Its origin/model/document
must match the create specification. Principal is exactly
`{key_scope: user, user_id: <ID>, membership_id: <ID>}`. Audience is exactly
`{kind: named_test_principal, membership_id: <same membership ID>}`. Organization
keys, expanded audiences, permission overrides and existing-document edits are
outside this path. Personal-folder defaults never establish privacy.

Each minimum has `status: resolved`, a bounded `scope` explanation and nonempty
original `evidence` pins. This records requirements and evidence integrity; it
does not independently verify numerical correctness, security or permissions.
The actual operator must corroborate these claims. In particular, unresolved
numerical, access or design defects cannot be reclassified as missing render
observations to obtain a demonstration.

Each pending observation contains `scope` (`ui_ux` or `qa`), `basis` (`rendered`,
`native` or `human`), `reason` and `required_observation`. Its scope and basis must
match an unobserved current consultation; every unobserved scope is accounted for.
All four consultation hashes and the stage tail are retained in the prepared
request, alongside HTML/spec/demo/candidate/query/request hashes and the exact
destination. No request is executed, and no source artifact is overwritten.

For supplied readback, use `verify_demo(prepared, created, document, app, identity,
project=..., artifact=..., spec_artifact=..., demo_artifact=...)` or
`app-demo-verify`. This rechecks the current demo preparation and shares exact
create/readback validation with the existing release route. The additional
identity capture must be a successful GET of
`/api/v1/whoami?modelId=<exact model>` at the same origin, reporting the exact
user-scoped principal. Capture data remains unauthenticated supplied evidence.

Even exact readback preserves `release_validated: false`,
`publication_authorized: false`, `execution_authorized: false`,
`native_verified: false`, `audience_verified: false` and the pending observations.
It establishes neither actual runtime behavior nor participant acceptance.
An uncertain create outcome requires reconciliation, never an automatic retry,
overwrite, or reinterpretation as an existing-document edit. Complete the missing
observations and normal release requirements before claiming validated delivery.
