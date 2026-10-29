# Local report preparation and supplied observations

`../scripts/report_native.py` is a standard-library local evidence helper. It
never connects to Omni, reads credentials, compiles a definition, evaluates an
expression, loads a renderer, creates a draft, saves or publishes a report.
Runtime/schema files and receipts are evidence declarations, never permissions.

Use the actual selected A–F engagement. `prepare` requires the build gate and a
version 2 [report contract](../../omni-report-designer/references/report-contract.md).
Its spec has exactly:

- `definition_path`: retained engagement-relative definition or handoff file.
- `definition_format`: `rdlx-json`, `rdl`, `rdlc` or `native_ai_handoff`. The last
  three do not imply compatibility with native Omni Reports.
- `requirements_path`: frozen visual requirements for migration; null is allowed
  for local preparation but cannot satisfy a DMA surface delivery.
- `builders`: nonempty worker IDs used to keep recorded QA independent.

```sh
python3 -I -S -B skills/omni-report-builder/scripts/report_native.py \
  --project /private-engagement prepare --spec contracts/report-build.json \
  --output deliverables/report-candidate.json
```

Preparation retains definition bytes, selected intent/design, query/decision pins,
capability gaps and the complete per-format acceptance denominator. It neither
loads nor validates an imported definition against a universal schema. `check
--kind candidate --path deliverables/report-candidate.json` recomputes those pins.
A legacy strict host-choice engagement still requires its qualified host verifier;
the CLI cannot invent one or fall back to a JSON approval flag.

## Runtime evidence and observations

`qualify` retains supplied target `{base_url, document_id}`, exact
`runtime_version`, `schema_version`, `definition_format`, `schema_evidence_path`,
`capability_evidence_path` and `reference`. Its result deliberately says
`native_execution_qualified: false`. An editor screenshot can establish observed
UI availability; it cannot establish an unknown runtime version or API contract.
Keep missing version evidence as a gap rather than inventing it to pass this step.
Only `rdlx-json` is admitted to this supplied native-observation path. RDL, RDLC
and native-AI instructions remain local evidence/handoffs. The RDLX-JSON label
itself still does not establish a deployed schema, valid definition or API.

`observe` takes `candidate_path`, `qualification_path`, `operation` (`readback` or
`export`), `status` (`completed`, `failed`, `uncertain`, `conflict`),
`definition_path`, `output_format`, `export_path`, `context_path`, `evidence_path`
and `reference`. Inapplicable path/format fields are null. A readback requires
actual definition bytes; export needs the requested PDF/print or XLSX bytes.
The published observation target and capability evidence must match the selected
intent. No draft lifecycle is inferred.

The context file records `principal_ref`, `locale`, `timezone`, `as_of`, exact
`parameter_values`, `query_results` and `asset_paths`. Query-result rows have
`dataset_id`, `path`, `population_reference`; every dataset must appear. Local
asset paths must match selected assets. These retain scope; completeness, query
correctness, effective access and source authentication remain QA obligations.

Same-byte readback is `readback_matched`; differing bytes become
`readback_conflict`. Failed/uncertain observations cannot satisfy delivery.
Receipts never authorize retry or execution. An external editor/host workflow
must stop on an uncertain save and reconcile actual native state before any retry;
this helper has no mutation to repeat and supplies no replay mechanism.

## Per-format QA and delivery

`coverage` takes a candidate, retained observation paths and QA case rows with
`id`, `outcome` (`pass`, `fail`, `not_run`), `basis` (`source`, `rendered`,
`native_behavior`, `access`), `observation_path`, `evidence_paths`, `reviewer`,
`notes`. IDs come from the frozen acceptance denominator. Reported passes need
same-candidate, same-format completed export observations and evidence. Pagination,
typography and accessibility require rendered evidence; access and performance
require their corresponding observation basis. A builder cannot be its own
recorded reviewer. None of these declarations authenticate a reviewer or prove
comprehensive accessibility compliance.

`check --kind coverage` recomputes every observation and case; missing, failed or
not-run cases remain pending. Keep the existing independent QA/review lanes too.
PDF signatures, hashes, valid JSON and source inspection do not prove rendering.

`verify_delivery(root, delivery)` accepts exactly `candidate_path`,
`execution_receipt_path`, `coverage_path`. It requires a matched **supplied**
published readback and frozen migration requirements, then returns the pins used
by the existing DMA/frontend return. It always retains native-execution and
source-authentication gaps, plus pending cases and capability gaps. A local-only
candidate cannot masquerade as a native delivery. No file authorizes publication,
distribution, scheduling or recipient access.

Migration delivery separately revalidates the original-backed visual requirements.
Every migrated source asset retains an unqualified binding gap and every source
case remains pending until a separately qualified source-to-report comparison
exists. Deferrals/exclusions and the rederived original inventory gaps remain in
the return. Completed report-format QA cannot erase these migration obligations;
it answers a different question from source semantic and behavioral parity.
