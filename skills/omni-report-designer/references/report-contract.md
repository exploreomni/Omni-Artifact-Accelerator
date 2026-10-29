# Selected report design contract

Store `report_contract` within the existing selected design JSON. Reference the
canonical requirement IDs, destinations, assets and attributable interview notes.
The first-party `report_contract.py` checker validates this bounded design shape;
it is not an RDL/RDLX schema, compiler, renderer or native API payload.

| Field | Required contents |
| --- | --- |
| schema_version | Integer 2 for new candidate preparation; integer 1 remains readable with an explicit mapping gap. Version 2 additions are below. |
| profile | release_label `Beta`, runtime_version (use `unverified` when unknown), authoring_route (`unverified`, `native_editor`, `native_ai`, `qualified_api`), evidence_path or null |
| paper | unit (`mm`, `in`, `pt`), numeric width/height, orientation, margins with top/right/bottom/left, header_height/footer_height, page_numbering description, layout_mode (`fixed`, `flow`) |
| datasets | Rows with id, query_path, grain, sort, filter_scope, totals, fields. Field rows have exact source id, report_name and type. A query path is retained local evidence, never automatically executed. |
| parameters | Rows with id, dataset_ids, value_policy, query_binding, required and multi_value booleans. Empty when genuinely not applicable. |
| sections | Rows with id, destination_id, dataset_id, width, columns, grouping, repeat_headers, keep_together, page_breaks, overflow and empty_state. Columns contain id, field_id, width, format and long_text policy. All widths use the paper unit. A static cover/text section uses dataset_id null and columns empty; its actual content stays in the canonical destination. |
| outputs | Rows with id, format (`pdf`, `print`, `xlsx`), capability_id, pagination, sheet_policy and filename_policy. Use an explicit not-applicable explanation for irrelevant sheet policy. |
| data_policy | locale, timezone, as_of, caching, refresh, distribution and decision_ref. Decisions are retained user notes, not authorization for queries, sends or schedules. |
| asset_ids | Existing selected brand/font/image asset IDs; empty when none. |
| capabilities | Rows with id, requirement_ids, behavior, status (`observed`, `documented`, `unverified`, `unsupported`), evidence_path or null, disposition (`native`, `approved_alternative`, `deferred`), decision_ref or null. Documented/observed needs evidence; alternative/deferred needs the actual decision reference. |
| acceptance | Rows with id, output_format, lane, scenario and expected. Lanes: numerical, pagination, typography, export, access, performance, accessibility. Each format needs numerical and export cases; PDF/print also need pagination cases. These are expected cases, not recorded passes. |

Describe real boundaries in acceptance: empty data, long names, exact/full page,
first overflow page, multi-page group, totals, changed parameters, restricted
persona and alternate output formats as relevant. Preserve outstanding capability
gaps. An observed feature still requires candidate-specific independent QA.

Every active required Report requirement must appear in the capability matrix;
unverified or deferred behavior remains explicit rather than silently excluded.
The checker rejects impossible printable dimensions, column overflow, missing
dataset/field/destination bindings, duplicated names and uncovered output formats.
It pins referenced query/capability/decision bytes into the existing E handoff,
so changed inputs invalidate downstream gate evidence. It does not verify free-text
formula semantics, source authenticity, every row's height or actual pagination.

Run an offline design check with the existing runtime:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/report_contract.py \
  --project /private-engagement --design contracts/report-design.json \
  --intent contracts/design-intent.json
```

All referenced paths are engagement-relative, bounded regular files. Keep raw
customer data and designs outside the package. A successful structural check does
not advance A–F, grant native access or qualify a report API.

## Version 2: concrete requirement coverage

Use `schema_version: 2` for new candidate preparation. Version 1 stays readable
for historical selections, with `legacy_report_contract_mapping_unqualified`;
it does not silently acquire version 2 coverage or native qualification.

Version 2 adds `requirement_bindings`. Each row has `id`, `requirement_id`,
`section_ids`, `parameter_ids`, `output_ids`, `acceptance_ids`, `disposition`
(`implemented`, `deferred`, `explicitly_omitted`) and `decision_ref`. IDs reference
actual rows in this contract and canonical Report requirements. An implemented
requirement must identify concrete parts, outputs and their acceptance cases.
Every active section, parameter and output must be mapped. Every required Report
requirement must be accounted for. Deferral/omission must exactly match the
existing attributable user/reused requirement decision; a local capability flag
cannot remove work.

Each version 2 acceptance row also contains `section_ids` and `parameter_ids`.
For **each** requested output format, cases must collectively cover every section
and parameter, with numerical/export checks and pagination for PDF/print.
Acceptance IDs must belong to mapped requirements. These links make missing
content visible; free-text scenarios still require independent professional review.
They do not prove semantic equivalence, layout quality or source authenticity.

The builder's [local preparation and observations](../../omni-report-builder/references/local-preparation.md)
freeze this denominator with the candidate. Keep field, paper, asset and query
changes in the selected design before preparing a replacement candidate.
