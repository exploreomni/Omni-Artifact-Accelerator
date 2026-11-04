# Domo visual and App migration workflow

Use the [Domo specialist](../../omni-domo-migrator/SKILL.md) inside the existing
[orchestrator](../../omni-artifact-accelerator/SKILL.md). This workflow combines
local evidence preparation with an opt-in, separately qualified Domo source reader.
It does not provide a hosted ChatGPT connector, automatic App conversion or a
qualified image/Card-query/App-definition acquisition client.

## 1. Recover scope, access and architecture

Reuse the Domo manager/run, selected tenant/principal, Page/App/Card identities,
source state and original evidence. Retain an independent object denominator,
including components, repeated placements, non-query content and operational
dependencies. Discovery completeness, visible objects and effective viewer access
are different evidence. Missing scope stays unresolved.

Select the route explicitly:

| Route | Intended work |
| --- | --- |
| `reuse_existing` | Bind accepted behavior to inspected existing Omni semantics; no model reconstruction |
| `omni_semantic_reconstruction` | Reconstruct needed Omni semantics against accepted warehouse relations; no implicit upstream dbt work |
| `warehouse_first_refactor` | Request separately reviewed upstream modeling through the existing DMA exchange |

The route does not choose the target design or authorize deployment. Preserve
source behavior and backend gaps regardless of route. New engagements follow
[A–F](../../omni-artifact-accelerator/references/stage-gates.md); the actual user
chooses one of exactly three feasible concepts before detailed design and coding.
At D resolve branding, quality ambition, delivery contexts and the target App
[cache/refresh policy](../../omni-product-owner/references/data-refresh-policy.md).
Source freshness is not a default refresh policy.

## Local setup and tool contract

Use an existing local engagement and approved Python runtime. The standard-library
MCP wrapper can run with source operations disabled:

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /absolute/private/engagement
```

Configure that stdio command in the local host's supported tool mechanism; running
it does not create a remote connector. Save an initial `oaa-domo-intake.v1` JSON
with `source`, `scope` and `target` objects in the engagement. Empty objects are
allowed at planning time so the helper can identify missing answers. Reuse actual
answers and add `route`, `route_reference`, source timestamp and experience details
as their A–F stages resolve; do not fabricate context merely to generate a request.

All file/directory arguments below are relative to the engagement. Outputs are
new private artifacts, not files in the package checkout.

| Local tool | Exact arguments | Outcome |
| --- | --- | --- |
| `domo_plan_source` | `spec`, `output` | Checks intake and records missing questions and bounded source requests |
| `domo_materialize_requests` | `plan`, `directory` | Rechecks the intake pin and writes fixed requests once |
| `domo_check_capabilities` | `source` | Reads a supplied capability profile without activating the runtime |
| `domo_translate` | `source`, `producer_revision`, `output` | Projects a supported emitted contract with its actual producer pin |
| `domo_check_capture` | `source` | Verifies capture identity and all pinned original files |
| `domo_import_capture` | `source`, `output` | Verifies and projects the separate visual/App capture |
| `domo_normalize_results` | `source`, `profile`, `binding`, `output` | Normalizes original results under explicit types and capture binding |
| `domo_build_handoff` | `spec`, `output` | Prepares a gated engineering handoff from selected source and design |
| `domo_frontend_return` | `spec`, `output` | Rechecks an existing frontend delivery and prepares a return proposal |
| `domo_check_frontend_return` | `spec`, `receipt` | Rederives that proposal from its original inputs |

## 2. Plan and qualify source acquisition

The local host exposes only the tools implemented by its checked package version.
Use `domo_plan_source` to identify missing context and bounded requests;
`domo_materialize_requests` prepares local request files. These operations do not activate
the source engine or obtain credentials. Check supplied capabilities with
`domo_check_capabilities`; a matching manifest establishes recognized source
structure, not dependency approval or tenant access.

There are two distinct producer identities:

- The legacy four-contract bridge retains its immutable inspected revision
  `55eba0ca0690fbf14f39eddbc8a04c94a720c155`.
- The source extension is identified by `domo-source-operations@0.1.0` plus its
  actual implementation-file closure. This label is not a Git commit, release or
  evidence that the upstream checkout is clean/current. Pin the supplied exact
  files and approved runtime/dependency closure independently.

The optional `domo_source_operation` is available only when a trusted local host
starts with the selected read configuration and explicit runtime authorization.
Its tool arguments select a previously pinned operation, not arbitrary commands,
URLs or object IDs. Source reads are restricted to the selected exact HTTPS host,
request scope and finite budgets. DataFlow acquisition is a separate opt-in scope;
it reads definitions rather than executing transformations. Credentials stay in
host-selected environment channels and are not passed through chat or request JSON.

After separate approval of the exact runtime, closure and source-read scope, the
host may add `--domo-operations contracts/domo-host.json` and
`--enable-domo-source-operations` to the local stdio command. The
`oaa-domo-host.v1` configuration pins capability/request files, runtime executable
and optional interpreter, implementation/dependency closure, output directories,
credential environment names and finite invocation/request/time budgets. Inspect
the [host contract](../../omni-artifact-accelerator/scripts/domo_host.py) rather
than substituting a generic command runner. Add `--enable-domo-dataflows` only for
separately authorized definition reads with the required credential channel.

That startup exposes `domo_source_doctor` with no arguments and
`domo_source_operation` with `operation_id` and boolean `resume`. Doctor checks
pins without loading the upstream runtime. The startup flags configure operations;
they are not proof of human approval or a sandbox. A trusted host must enforce the
approval boundary outside agent-writable files and tool arguments.

The wrapper uses the existing source engine and its typed evidence accessor.
Its outcome explicitly retains `review_redaction_before_frontend_import`: raw
acquisition may contain pending-redaction definitions and is not immediately
importable frontend evidence. Keep raw evidence private and produce only a
separately reviewed sanitized/withheld evidence artifact through the source
workflow. Preserve its lineage; do not edit a redaction label to force acceptance.
The wrapper does not automatically call `domo-inventory` or close redaction review.
After sanitization, an operator may invoke the separately reviewed source runtime's
fixed `domo-inventory` command with its inspected inputs. This remains an explicit
operator step, not an automatic post-capture action.
An interrupted or uncertain invocation requires reconciliation; resume may return
an existing verified outcome but must not silently retry acquisition. A capability
probe or successful local fixture does not establish live tenant qualification.
Do not install, update or import a replacement runtime to clear a failed check.

This is a local stdio execution path for a configured host. It does not provision
network reachability, OAuth, a remote MCP service or account connections for
ChatGPT/Claude. A connected chat without a qualified execution bridge uses supplied
files and reports that boundary.

## 3. Bind supplied original evidence

Reuse a supported emitted source contract before recapture. `domo-agent` intake
preserves the four original formats described in the
[bridge](domo-agent-bridge.md). A search response or generic MigrationBundle is not
an emitted definition contract.

Use `oaa-domo-visual-capture.v1` to add supplied definitions, images, results and
App evidence with exact byte pins, state and independent inventory. Follow the
[evidence contract](domo-evidence-contract.md), then `domo_check_capture` and
`domo_import_capture`. The original files must be present; a JSON seal does not
prove their contents or source authenticity. Recheck bytes when using results or
preparing downstream work.

Image export, executed Card/component results and detailed App definitions remain
supplied/manual evidence in this release. Keep provenance, version, principal,
filters/Variables, placement, timing, viewport and unknown facets. A vendor export
feature does not establish a packaged acquisition route; use only accepted file
formats and preserve unsupported originals separately.

For Apps, retain all component behavior and operational obligations. The distinct
`oaa-domo-app-handoff.v1` supports `read_only` with empty operations/side-effect
arrays, or an operational assignment with exact scoped obligations. Neither
authorizes execution. Existing legacy external redesign assignments retain their
own original contract; do not fabricate a side effect to force a read-only App
through a different schema.

## 4. Normalize, analyze and preserve meaning

`domo_normalize_results` requires original bytes, an explicit typed parser profile
and the capture-derived binding. Retain exact decimal precision, errors/null rules,
complete columns and independent expectations. Compare Card summary metrics,
detail, totals and meaningful filtered slices separately. DataSet SQL alone does
not prove a Card's formulas, aggregation or visual state.

Use the existing [shared visual helper](../../omni-artifact-accelerator/scripts/visual_workflow.py)
for prepare/compare/coverage mechanics; Domo keeps its own source
format, identity, state and comparison checks. Missing execution originals,
incomplete populations, incompatible filters/Variables, stale definitions or
unqualified access remain gaps even when supplied arithmetic agrees. Generic
arithmetic is not qualified Domo parity.

## 5. Design and build through the current gates

`domo_build_handoff` prepares the source-bound local handoff after the required
A–F predecessors and actual design choice. It does not create a native artifact,
register a plan in the Domo store or confer native write authority. Retain the
selected route, exact source hashes, independent denominator, query requirements,
App obligations and current baseline.

`backend_evidence` contains pinned references only. The handoff's
`semantic_qualification: retained_references_only_candidate_adapter_must_validate`
does not certify an operational query binding; the selected candidate adapter must
validate the actual semantics and bindings before native delivery.

Resolve real semantic gaps through the [DMA exchange](../../omni-backend-handoff/references/cowork-contract.md).
Use the BI/App engineers and existing native adapters for the selected surface.
Dashboard, App and Report capabilities stay distinct. A model candidate or source
assignment cannot authorize publication, operational writes or dependency loading.
Obtain security, UI/UX, product-owner and independent QA consultations per iteration.

## 6. Return evidence without promoting acceptance

`domo_frontend_return` consumes an `oaa-domo-frontend-return-spec.v1` containing
`source_context`, `source_evidence` and `frontend_receipt` pins,
`producer_revision`, `source_revision_profile` and `source_portfolio`. Retain the
real original planning context, including its run/unit/cycle and source-scope
references; do not manufacture a reduced context from the frontend output.

Choose the revision profile that the original context actually uses:

| `source_revision_profile` | `source_portfolio` | Required identity check |
| --- | --- | --- |
| `native_content_hash` | `null` | Original object ID and fingerprint match the native evidence object's content hash |
| `portfolio_object_hash` | Original immutable portfolio file pin | Original stable ID and fingerprint match the portfolio object; its retained native-ID/definition-hash mapping matches native evidence |

A portfolio object hash and a native definition content hash are different
identities. Preserve both and the exact pinned mapping; never substitute one hash
for the other or infer native IDs from names.

The helper rechecks the delivery and selected
source membership before emitting `domo-frontend-return.v1`; raw candidate files
alone cannot satisfy this return path.
`domo_check_frontend_return` rechecks its pins and scope. Preserve all unresolved
requirements, deferred objects, accepted differences, source and target gaps and
untested lanes. Return the checked packet to the existing Domo manager and DMA
engagement rather than creating competing migration runs.

The return does not register readiness in DomoMigrationAgent, authenticate a human
review, accept the migration, publish or retire source content. Distinguish local
preparation, source captured, native candidate read back, independent verification
and business acceptance. A real pilot still requires original source/target
evidence and actual authorized observations for each selected lane.

When present in the separately reviewed source extension,
`domo-validate-frontend-return` takes `--request`, `--source-evidence`,
`--source-context`, `--evidence-root`, `--output` and `--source-portfolio` when the
portfolio profile is selected. It validates a supplied return
against retained source context; it is not an attach, registry-write, acceptance
or completion command. Use that exact runtime's inspected schema and preserve its
unverified identity/acceptance limits. This OAA wrapper does not silently invoke it.

The distinct `domo-attach-frontend-return` command requires `--request`,
`--source-evidence`, `--source-context`, `--evidence-root`, `--run-dir`,
`--control-root`, `--package`, `--reviewer`, `--approve-attach` and
`--redaction-status` (`redacted` or `not_required`), plus `--source-portfolio` when
needed. Use it only after actual attachment authorization and approval to activate
that exact source runtime. It validates the return against the canonical current
package and exact original context, then attaches proposal-validation evidence as
an `EvidenceInput`. It does not accept or complete the migration, publish a target
or retire source content. The approval flag records an authorized invocation; an
agent-written flag or reviewer string cannot independently confer authority.
Source-only tests qualify inspected local behavior, not runtime activation,
effective reviewer identity or a successful live migration.
