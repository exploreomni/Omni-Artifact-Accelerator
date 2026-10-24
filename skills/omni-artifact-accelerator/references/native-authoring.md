# Bounded native authoring

Use for net-new work or an enhancement when the migration-only adapter is not the right entrypoint. This is an operator/agent workflow using current official tools, not an automatic provisioning service. Select the native dashboard or App surface explicitly. Keep source acquisition, semantic deployment and frontend publication separate.

## Preflight and baseline

Record the exact tenant, principal/authentication type, profile, model/Topic, target document, tool version and authorized completion scope. Inspect CLI help and current official schemas. A profile name alone does not prove identity; keep credentials in the configured host/secret store, never engagement files. `omni config show` may mask secrets and is not a source of a usable token.

The packaged migration named-draft adapters intentionally require user-scoped credentials and migration requirements. For an existing query-backed App enhancement with an organization key or user key, use the [scoped preparation/readback helper](../../omni-app-engineer/references/authoring-preflight.md). It generates a fixed HTML-only request from exact current captures and checks the readback; the authorized host still performs the official API operation. For a new personal App, the same guide describes `app-create-prepare` and `app-create-verify`: freeze the exact HTML and create specification, finish the four candidate reviews, then prepare a fixed new-document POST with governed queries and locked resource settings. Creation publishes immediately and requires separate host-enforced authorization. Neither helper reads credentials, executes transport or grants authority. Do not relax migration adapters or invent a migration inventory to use them.

Read the current document and list drafts. Preserve content, controls, theme/settings, App content and their hashes before changes. Use a named draft read for an edited candidate; do not rely on a generic document read to return the draft. Reconcile another editor's changes and uncertain results before writing again.

## Document and query operations

CLI 1.0.6 exposes the following commands; inspect the installed version before use. Substitute reviewed IDs and private request files. Every authenticated command needs the explicit target profile and base URL.

```sh
omni --profile PROJECT --base-url https://TENANT.omniapp.co documents v2-get DOCUMENT
omni --profile PROJECT --base-url https://TENANT.omniapp.co documents list-drafts DOCUMENT
omni --profile PROJECT --base-url https://TENANT.omniapp.co documents v2-get-draft DOCUMENT DRAFT
omni --profile PROJECT --base-url https://TENANT.omniapp.co query run --body - < query.json
```

Freeze exact query fields, Topic, filters, sorts, limits, result shape and independent expected results. Preserve inspected query-envelope defaults such as calculations, totals and fill fields; a permissive public schema does not guarantee that a minimal payload executes. Keep the query model tied to the selected document/model. Distinguish local table search from a warehouse filter and disclose capped results.

The current query API places `modelId` **inside** `query`; a CLI example is not stronger evidence than the current API schema. `native_authoring.py query-body` wraps the inspected query without dropping its defaults. Use the explicit membership `userId` when the authorized organization-key query route requires it. Retain the installed CLI version/help and check exact command names before execution. Exit zero with empty output is not an empty inventory: `cli-json --shape list` accepts `[]` but rejects empty/invalid transport, and `route-check` reports missing commands. See [preflight examples](../../omni-app-engineer/references/authoring-preflight.md).

Requested SQL alone does not prove the physical source selected by semantic planning. Inspect the generated SQL, effective workbook/model, usable field metadata and exact output keys. The bounded `plan-check` catches explicit catalog/schema drift and empty metadata/row objects; it cannot resolve unqualified/dynamic dependencies or view expansion. If raw SQL resolves to another catalog or has no usable semantic fields, follow the [isolated workbook query-view route](../../omni-app-engineer/references/native-query-qualification.md#isolated-source-binding-fallback) within existing authorization, then re-run the plan, semantic query and independent reconciliation. Never repair this by silently selecting a similarly named development source.

For a new document, inspect `documents v2-create`: creation publishes immediately. Prepare a reviewable payload and use only the authorized destination. For an existing document, `v2-patch-draft` creates a draft and returns its ID; an existing main draft produces a conflict. Follow-up edits use `v2-patch-draft-by-identifier`. Never clear another draft to get past a conflict.

```sh
# Mutations: only after checking the concrete payload, target and existing authorization.
omni --profile PROJECT --base-url https://TENANT.omniapp.co documents v2-patch-draft DOCUMENT --body - < reviewed-patch.json
omni --profile PROJECT --base-url https://TENANT.omniapp.co documents v2-patch-draft-by-identifier DOCUMENT DRAFT --body - < reviewed-patch.json
```

`queryPresentations.data` merges by tile key; each supplied tile replaces its complete presentation. For a title or style change, copy the inspected presentation, edit it and submit the complete object. Retain its query, field/filter bindings, sorts, limits and visualization state. Omitted tile keys remain; a null tile deletes it. Containers are a complete replacement. Inspect filter propagation too: a restored chart can render correctly while remaining excluded from controls. [Official merge contract](https://docs.omni.co/api/documents-v2/create-draft-and-patch-document)

Read the exact named draft back, compare complete intended settings/bindings and verify queries and native rendering. A hash/readback match is structural evidence, not visual or numerical acceptance. The included adapter rejects a query replacement missing its fields or existing query properties before writing; it does not synthesize complete presentations.

Do not assume an empty control map removes existing exclusions, or that `true` is a valid replacement for an excluded tile. Reconcile the readback with the native mapping editor and the current schema, then observe the affected chart under the selected filters. Likewise, use inspected native typography and table-style values; a stored but unsupported font value can silently render at the default size. Keep these capability observations separate from portable API guarantees.

## Native Apps

Use the official App routes where the installed CLI lacks App commands. App content APIs are **currently in development and may change**; preserve this label and recheck the current contract. The named route `PUT /api/v2/documents/{documentId}/draft/{draftId}/app` replaces HTML on an existing draft. Read App content/settings separately from the document's `app.url`. A document PATCH's App field is not a substitute for this route. [App draft content](https://docs.omni.co/api/apps/replace-app-content-on-a-draft), [App read](https://docs.omni.co/api/apps/read-app-content)

Inspect the actual native starter/query bridge before implementation. Keep runtime evidence tied to the tested instance/version; do not package undocumented methods as a universal SDK. Preserve existing network/navigation/clipboard/download settings. Optional images and fonts need their own supported loading path and rights; a design repair does not expand permissions.

Qualify the selected high-risk boundary before full composition using [native capability checks](../../omni-app-engineer/references/native-capability-checks.md): exact callback input, actual asset loading, provider controls/playback or refresh/failure/freshness, as applicable. Retain the target/candidate/settings identity and observation method in existing runtime evidence; declare the file as a selected requirement dependency. Configured domains, a reachable URL, iframe load or readback are not effective-host verification. Under source-only restrictions, preserve the gap and fallback without browser activity or policy changes. Custom scenes/calendars/dossiers can reuse the [advanced visualization module](../../omni-app-engineer/references/advanced-visualization.md) without rewriting the governed data contract.

Use controlled local fixtures only in a clearly marked preview/test adapter. Production HTML must consume its governed queries. Test filter scope, pending/error/empty states, stale response handling, completeness, focus and responsive transitions in the actual App. An image export cannot establish interactive behavior.

## Publication and recovery

Retain the intended payload hash, before-state, exact draft ID and native checks. Within existing publication authorization, `documents v2-publish-draft DOCUMENT` promotes the main draft; inspect it immediately beforehand because the whole draft is published. Read published content and repeat the selected critical path. Never report a publish response as business acceptance.

On an ambiguous write, reconcile the known target instead of replaying. Keep a reviewed restore candidate; do not overwrite newer changes automatically. Maintain the engagement's query/brand/design contracts, source/artifact registry and entrypoint throughout execution. [Draft PATCH](https://docs.omni.co/api/documents-v2/patch-draft)
