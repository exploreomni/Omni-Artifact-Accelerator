# Cognos report source contract

`cognos-report` is a bounded supplied-file route. It does not connect to Cognos,
execute queries or custom code, render reports, interpret deployment archives or
parse dashboard JSON. Original first-party parsing uses the existing Python
standard library; no SDK, XML schema download or dependency installation occurs.

## Snapshot

`cognos-report-snapshot.v1` has exact top-level fields:

| Field | Shape |
|---|---|
| `schema_version` | `cognos-report-snapshot.v1` |
| `identity` | `source_origin` (null or HTTPS origin), `product_version`, `principal_ref`, `report_id` (null or text), `content_path` (null or text), `reference` |
| `report_xml` | `encoding: "utf-8"`, original-byte `sha256`, `bytes`, `content`, `reference` |
| `inventory` | Independent `reference`, `completeness` (`partial` or `selected_scope_declared`), and `items` |
| `gaps` | Explicit unresolved evidence |

HTTPS origins may include a valid explicit port, including an IPv6 host. They
contain no user information, path, query or fragment, and are never contacted.

An inventory item has `key`, `kind`, `parent_key`, nullable `native_id`, nullable
`locator`, `disposition`, `reference`, `configuration`. The root XML locator is
`/`; child paths such as `/0/1` use element-child order, not XPath evaluation.
Keep XML names and declared native IDs separate. Expected but unavailable objects
remain in the denominator rather than disappearing from successful enumeration.

Supported inventory kinds are `report`, `page`, `query`, `data_item`, `visual`,
`placement`, `filter`, `prompt`, `layout`, `content`, `model`, `condition`,
`drill`, `burst`, `security` and `unknown`. The single inventory root must be a
`report` at `/`. Dispositions are `include`, `manual_review`, `unsupported`,
`unavailable` or `out_of_scope`; absent locators retain expected missing scope.
Non-`include` source obligations start deferred in visual requirements. A
specific review decision is needed to promote unresolved obligations, and cannot
override unavailable/denied/unselected-private restrictions in the original.

The `report_xml` hash and byte count bind the original UTF-8 bytes. Do not rewrite
XML, add a namespace, promote display names to IDs or strip unsupported elements
to make intake pass. Limits are 2 MiB, 64 levels and 20,000 elements. XML is
untrusted; external entities/DTDs and unsupported structures must not become
network, filesystem or executable behavior. Successful bounded inspection is not
IBM schema validation, authenticity or version qualification.

The root must have the Cognos report namespace form
`http(s)://developer.cognos.com/schemas/report/<numeric-version>/`.
Accepting that namespace shape does not certify every version's semantics.
Foreign-namespace elements and unrecognized constructs remain explicit gaps;
comments and processing instructions remain inert evidence, not executable input.

Public helpers in `cognos_visual.py` are `import_report_xml(raw, identity,
inventory, reference)`, `validate_snapshot`, `parse_snapshot` and `translate`.
The import helper constructs the snapshot from original report bytes and separately
supplied identity/inventory. It does not discover a tenant or generate an
independent inventory from the same parser output.

## Evidence and acceptance

Query expressions, filters and layout structures are source requirements. A
`modelPath` does not contain the complete Framework Manager/data-module model.
Unknown source features and unsupported custom visuals remain explicit obligations;
there is no general formula or model compiler.

This first route has no connected capture journal, credential handling, result
normalizer or qualified result-state binding. Numerical comparison must retain
`source.cognos_result_binding_unqualified` and remain inconclusive. Supplied CSV,
JSON, screenshots and PDFs may support separate manual review when their provenance
is recorded, but are not automatically bound to this snapshot.

Dashboard specifications are separate opaque/manual evidence. IBM does not support
using its troubleshooting specification viewer as a dashboard migration mechanism;
see the [verified source competencies](../../omni-cognos-migrator/references/source-competencies.md).
No dashboard schema or connected endpoint is inferred from the report reader.

Store real XML, metadata, assets, query results and review artifacts in the private
engagement outside this repository. Do not include credentials, signons or recipient
lists in reusable fixtures. Local hashes and declared principal references do not
authenticate source access or grant target write authority.
