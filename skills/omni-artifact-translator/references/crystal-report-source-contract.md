# Crystal report extraction

[crystal_report.py](../scripts/crystal_report.py) is a standard-library, passive
reader. Its schemas are package-owned interchange contracts, **not** a SAP
native JSON format or a general RPT decoder. No SDK, formulas, database queries,
external resources or binary report files are executed. Keep original customer
exports outside the repository; supplied evidence is not authenticated origin.

## Original extraction and snapshot

The UTF-8 extraction is `crystal-report-extract.v1` with exactly:

- `schema_version`, `report` (nonempty metadata object), `objects`, `dependencies`.
- Each object: `id`, `parent_id` (null or another object), `kind`, `name` (null
  allowed), `properties` (all supplied properties retained inertly).
- Each dependency: `from_id`, `target_id` (null for external/unresolved), `kind`,
  `reference`. Preserve shared-variable and subreport relationships explicitly.

Kinds are report, section, field, parameter, group, formula, running_total,
subreport, query, table, command, filter, image, chart, crosstab, action, security,
schedule and unknown. Extractor IDs are not assumed to be server-native IDs.
Repeated placements are separate objects even if they display the same field.
Unknown source properties remain in original bytes, never discarded to fit a schema.

`make_snapshot(raw, identity, inventory, reference, method, extractor_version)`
produces `crystal-report-snapshot.v1`. Its exact fields are `schema_version`,
`identity`, `extraction`, `inventory`, `gaps`.

Identity contains `source_platform: crystal`, `source_origin` (null or canonical HTTPS origin),
`product_version`, `engine` (`crystal_classic`, `crystal_enterprise`, `unknown`),
`principal_ref`, `report_id`, `cuid`, `content_path`, `reference`. Null is allowed
for the three server/path identifiers when unavailable. Unknown identity remains
unknown; a local extraction cannot invent a service identity.

Extraction retains exact `content`, `encoding: utf-8`, byte count, SHA-256,
`reference`, `method` (`supplied_sdk_extract` or `supplied_manual_extract`) and
`extractor_version`. Method labels do not qualify an SDK/runtime or extraction.

Inventory has `reference`, `completeness` (`partial` or `selected_scope_declared`)
and `items`. Each item has `key`, `object_id` (null for an expected missing object),
`kind`, `disposition`, `reference`, `configuration`. Dispositions are include,
manual_review, defer, exclude, unavailable or out_of_scope. Configuration can
retain `access`, `private`, `selection_reference` and source-specific obligations.
Every original object omitted from this inventory becomes an additional obligation.
Unavailable/private parent scope propagates to its children. All formulas and
unresolved behaviors need reviewed disposition, even when inventory says include.

Use `translate_artifact.py --format crystal-report` for snapshots. The local host
also exposes `crystal_prepare_snapshot`, `crystal_check_snapshot` and
`crystal_translate`; no connected SAP operation is exposed. Source definitions are
bounded to 2 MiB, snapshots to 8 MiB and collections to 2,000 items. Exceeding a
bound fails rather than silently truncating. Known secret screening is not a DLP
guarantee. Never put credentials in definitions, examples or command arguments.

## Qualification and evidence

Start with customer-supplied extracts plus original PDF/spreadsheet/raw numerical
exports. Retain record and group selection, parameters, data-as-of, saved-versus-
refreshed data, effective principal, locale, printer/font settings and source
engine version for each observation. Missing extraction coverage or outputs stay
explicit. No claim of full fidelity may be made from the normalized inventory.

An optional future SDK extractor requires a reviewed exact runtime/license,
dependency closure, isolation and explicit installation/activation authorization.
Use an approved customer environment when available; this package never installs
or discovers SAP credentials. Do not mistake an XML data export for a full editable
report definition. Exporting an existing report can invoke queries; qualify that
separately from reading its metadata.

Official references reviewed 2026-10-29:
[Crystal services and RAS](https://learning.sap.com/courses/administrating-servers-in-sap-businessobjects-bi-platform/explaining-crystal-reports-services),
[print/export options](https://help.sap.com/doc/1eb6ed2630b940d49d85e22ba94c35bc/4.3.2/en-US/Printingandexportingareport.html),
[Crystal 2020 guide](https://help.sap.com/doc/37c8938b12384f399940e22b7315979f/2020.4/en-US/cr20sp2_usergde_en.pdf).
Select documentation matching the actual engine; classic and Enterprise versions
must not be treated as interchangeable. Vendor support does not establish Omni
target support or authorize a local runtime.
