# Native authoring preflight and existing-App enhancement

Use `scripts/native_authoring.py` for offline preparation and supplied-capture checks. It uses the existing Python standard library, writes a new private output, and never connects to Omni, reads secrets, executes SQL/HTML, creates drafts or publishes. These checks reduce repeated glue code; they do not authenticate evidence or grant a host permission to write.

## Select the real route

Discover configured MCP tools first. When unavailable or incomplete, inspect the installed CLI version and help, then use current official APIs for missing operations. Keep profile, HTTPS origin, key scope, principal/membership, model, document and named draft explicit. A missing MCP connector is a host capability gap; do not install one automatically.

All operations use `--input /private/input.json --output /private/new-result.json`; output must not exist. Paths inside an input record resolve relative to that file. Do not put credentials in any input/output.

```sh
python3 -I -S -B skills/omni-app-engineer/scripts/native_authoring.py route-check \
  --input "$OAA_RUN/inputs/route.json" --output "$OAA_RUN/evidence/route-check.json"
```

An original synthetic route record:

```json
{
  "cli_version": "1.0.6",
  "help_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "available_commands": ["documents list-drafts", "documents v2-get-draft", "query run"],
  "required_commands": ["documents list-drafts", "documents v2-get-draft", "query run"]
}
```

Replace the illustrative hash with the retained installed-help hash and record actual discovered commands. The checker assesses this supplied inventory; it does not discover a CLI itself. A command missing from this inventory needs discovery or an official API route, never a guessed alias. Validate saved CLI output with `cli-json --shape list` or `--shape object`. `[]` can be a valid empty list; an empty response, duplicate keys, wrong shape and nonfinite values are rejected. Shape checks alone do not establish correct source identity or complete pagination.

## Prepare and qualify a query

`query-body` takes `{"model_id":"reviewed-workbook-id","query":{...}}`, optionally `"user_id":"reviewed-membership-id"`. Supply the complete inspected query, including fields/SQL, filters, sorts, limits, calculations and fill/totals defaults. The result places `modelId` inside `query`, retains the remaining properties and selects JSON/unformatted export. A conflicting existing model ID is rejected. This does not execute the query or turn export labels into native field keys.

For `plan-check`, supply a documented projection of retained generated SQL, actual field metadata and rows:

```json
{
  "expected": {"database":"PRODUCTION","schema":"CURATED","fields":["jobs.id"]},
  "planned_sql":"SELECT ID FROM PRODUCTION.CURATED.JOBS",
  "columns":[{"name":"jobs.id","type":"STRING"}],
  "rows":[{"jobs.id":"job-1"}]
}
```

This synthetic shape is not an Omni response schema. Preserve raw captures/hashes and the exact projection; never manufacture metadata or re-key rows to pass. The helper screens explicit three-part references after skipping literals/comments. Missing references remain unresolved. SQL aliases, unqualified objects, dynamic identifiers, views and dialect-specific constructs still need physical plan/source review. Database/schema strings use the exact normalized identifiers from the actual plan (unquoted Snowflake identifiers are uppercase). Multiple authorized schemas need separate review; do not suppress a mismatch. Result counts, scalar/null types, completeness, grain and independently derived totals belong to [native query qualification](native-query-qualification.md).

## Prepare one existing App draft

For an enhancement, capture these values through the current official APIs/CLI:

1. `whoami` for the exact model; retain actual `keyScope` (`organization` or `user`) and user/membership IDs. Broad organization identity is not effective end-user access.
2. The selected item from `documents list-drafts`: matching published/document ID, active named draft, workbook ID, branch and `draftOutOfDate: false`.
3. Exact `documents v2-get-draft DOCUMENT DRAFT` output, including all queries and `app.url`.
4. Exact App GET for `/api/v2/documents/DOCUMENT/draft/DRAFT/app`, including HTML and settings.

Retain raw responses separately and compose `baseline.json` with keys `target`, `identity`, `draft`, `document`, `app`. `target` contains exactly:

```json
{
  "base_url":"https://example.omniapp.co",
  "document_id":"operations", "draft_id":"draft-1",
  "model_id":"model-1", "workbook_model_id":"workbook-1",
  "key_scope":"organization", "user_id":"user-1", "membership_id":"member-1"
}
```

This helper requires an already existing query-backed App on the selected draft. It does not provision documents, create a draft, acquire a credential or extend the model. Capture `current.json` again before preparation. Any change from the baseline needs reconciliation, including benign metadata changes; do not erase differences to pass.

`app-prepare --project "$OAA_RUN"` input is `{"target":{...},"baseline":"baseline.json","current":"current.json","html":"deliverables/candidate.html"}`. The HTML path is relative to the engagement. It requires a real project, current [stage gates](../../omni-artifact-accelerator/references/stage-gates.md), four consulting dispositions and exact recorded candidate bytes for gated work. It checks target, identity, draft status and exact snapshot equality, then generates one bounded `PUT` request containing **only HTML**, its hash, baseline hash and local engagement bindings. Settings, queries, permissions and shared models are outside this request. The stock CLI cannot verify a gated user choice; preparation needs the trusted in-process host route. Review the candidate's resource use and dependency authorization before execution; HTML hashing is not a script security audit.

The trusted host may execute the prepared fixed route within the user's existing authorization using its configured secret store and official transport. Pin the origin, reject redirects before credential forwarding, bound responses, redact errors and retain a durable attempt record before a mutation. Recheck the target immediately before writing; local checks cannot provide server-side compare-and-swap or eliminate a concurrent-editor race. On an uncertain response, read the known draft and reconcile before any retry. Never take an agent-writable receipt or flag as authorization.

After the host writes, capture the same five-part snapshot as `after.json`. `app-verify` takes `{"prepared":"request.json","baseline":"baseline.json","after":"after.json"}` and verifies exact HTML, unchanged settings/document/query definitions, identity and draft branch. A mismatch returns nonzero and must remain visible. It does not perform automatic rollback. Publication is a separate official operation with its own immediate whole-draft review and readback under existing user authorization.

## Qualification limits and sources

Retain source, constructed-input, numerical, native callback, rendered, access, human and publication outcomes separately. A prepared request or successful readback cannot establish that the App rendered or ran. CLI/API-only work leaves prohibited observation lanes unrun; do not use a headless workaround.

Contract reviewed 2026-10-24: [query envelope](https://docs.omni.co/api/queries/run-query), [identity](https://docs.omni.co/api/who-am-i/get-current-identity-and-permissions), [named App draft replacement](https://docs.omni.co/api/apps/replace-app-content-on-a-draft). App APIs are **currently in development and may change**. Recheck the schema when the host/version changes; package examples are not release guarantees.
