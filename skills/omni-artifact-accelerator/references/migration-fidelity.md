# Source baseline and control parity

Use the same source baseline for a faithful migration and an explicit redesign. A redesign can change the presentation while retaining the source analytical behavior. Record any agreed scope changes against the original control IDs. Work in the existing private engagement, outside the package checkout.

## Capture the source

Write one source manifest with `schema_version: 1` and the fields below. All file references are paths relative to the engagement. Use source definitions, inert assets, screen captures, query results and recorded observations appropriate to the artifact. For a Pro-code App, include the applicable manifest, source code and assets, plus evidence of what the controls actually did. An opaque asset or unexplained control belongs in `unresolved`.

| Field | Content |
| --- | --- |
| `source_evidence` | Original files identifying the selected artifact, version and audience. |
| `views` | Each view has an `id`, `title`, human-readable `layout`, `components` containing source placement/output IDs, `controls` containing source control IDs and `evidence` paths. Use placement-specific IDs when behavior differs between placements. |
| `controls` | Each entry has an `id`, `label`, `kind`, `default`, `affected` and `exempt` component IDs, and `evidence` paths. Preserve which outputs remain fixed as well as those that change. |
| `cases` | Each entry has an `id`, the `controls` exercised, a repeatable `action`, a comparable `persona`, the source `state` keyed by control ID, expected `outputs` keyed by placement/output ID, and original `evidence` paths. Include a default and changed state for each control. Add material combined, reset, navigation, empty and access cases. Include a case-level `context` object for consequential comparison settings such as reporting timezone, grain, population or snapshot watermark. Use exact, consistently typed values on both sides, including canonical strings for exact decimals and dates. |
| `deviations` | Use an empty array when there are none. Each entry requires a `control_id`, `disposition` of `adapt` or `omit`, a `reason` and `decision_evidence` paths pointing to the actual scoped decision. An adaptation retains all analytical obligations. An omission can excuse missing cases exercising only omitted controls. Mixed cases retain their output expectations. |
| `unresolved` | Optional array of uncertainties, each with an `id`, `reason` and `evidence` paths. These keep the comparison partial. |
| `no_controls_evidence` | For a static report or other confirmed noninteractive surface, supply the evidence for that observation, empty control lists, and at least one case with the expected displayed outputs. |

For example, a dealer selector can change a dealer subtotal while the all-dealers total holds. A date range may affect both. Capture both totals with defaults, with only the dealer changed, with only the date changed, with both applied, and after reset. Preserve the reporting timezone, selections, persona and grain in the original observations. The [synthetic fixture](../../../tests/test_migration_fidelity.py) shows the full two-control input.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/migration_fidelity.py \
  --project /absolute/private/engagement baseline --baseline contracts/source-baseline.json
```

The command prints the views, controls, cases, exceptions, `baseline_sha256`, and the exact file pins. Revisions to any referenced source or decision evidence change the baseline identity.

## Compare the frozen candidate

After candidate freeze, create a separate observations JSON with `schema_version: 1`, the reviewed `baseline_sha256`, the frozen `candidate_sha256`, `controls` and `cases`. Use the candidate digest reported by the stage journal. Each observed control contains its source `id`, a distinct actual `target_locator` and target `evidence` paths. For a repeated control, list each actually observed source view in `source_views`, retaining its corresponding target location in the evidence. Each case contains its source case `id`, `persona`, observed `state`, observed `outputs`, the matching `context` when specified, and target `evidence` paths. Translate native locators to the baseline IDs, preserve the mapping in target evidence, and retain the actual native values. Record how the two principals and query states correspond. A missing observation stays absent.

```sh
python3 -I -S -B skills/omni-artifact-accelerator/scripts/migration_fidelity.py \
  --project /absolute/private/engagement parity \
  --baseline contracts/source-baseline.json --observations evidence/target-observations.json
```

The CLI replays the engagement journal and verifies the frozen candidate files. Inside a gate, call `baseline(project_root, baseline_relpath)` or `parity(project_root, baseline_relpath, observations_relpath, candidate_sha256)` and pass the gate's current frozen digest. Pin the returned dependencies with the review. A stale baseline or candidate binding fails validation. Missing controls, missing cases, components lacking source expectations, state/role/value mismatches, and unresolved source behavior produce `partial`. If all cases are excused and no target case is compared, the result also stays `partial`. A `matched` report covers the supplied observations and lists any explicit exceptions. Verify native behavior, visual fidelity, effective access, publication and business acceptance under their respective checks.
