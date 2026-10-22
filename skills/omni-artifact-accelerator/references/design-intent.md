# Saved design intent and named review

Use this additive record when carrying design decisions through an App/dashboard engagement. It does not change the version-1 project lifecycle, grant permission or replace the detailed design, brand, query and QA contracts. Direct specialists use the same selection as the orchestrator. A focused edit reuses it and reviews only affected requirements; a faithful migration retains source identity and accepted differences without a new redesign interview.

## One short interview, persistent decisions

Read existing decisions first. Ask only the missing consequential choices together: intended task/audience, selected surfaces, required identity and the requested completion stage. Separate required choices from optional preferences. For branded work, combine the missing company website with an approved logo file/URL, authorization to source the official website, or an explicit no-logo choice. Reuse prior answers and authorization. A website does not select a logo; authorization to source one is not the asset selection itself.

Keep each required unanswered or deferred choice open. A working recommendation can guide reversible prototyping but remains `origin: proposal`; it must not become a user decision by implication. A placeholder is visibly provisional and cannot satisfy the requested identity. Optional photography, exact corporate fonts or animation are not universal requirements. If the user chooses no logo, record an explicit omission with its decision reference and skip unrelated asset research.

## Record and select

Run the helper from an installed bundle or this checkout. `OAA_HELPER` below points to its `skills/omni-artifact-accelerator/scripts/analyst_project.py`; `OAA_RUN` is a private engagement outside the package.

```sh
python "$OAA_HELPER" init --output "$OAA_RUN" --name 'Operations pilot' \
  --mode net-new --surface both --branding requested --website https://example.com
python "$OAA_HELPER" intent-check --project "$OAA_RUN"
```

`example.com` is a documentation placeholder, not a discovered company. Initialization writes editable `contracts/design-intent.json`, linked as `project.design_intent_draft`. Branding defaults to `requested` with a website, otherwise `unknown`; use `--branding none` when out of scope. Requested branding starts with an unresolved required logo across the selected surfaces. Unknown branding remains a discovery question for the agent, not an invented logo obligation.

Retain a versioned specification inside the engagement, then select it:

```sh
python "$OAA_HELPER" intent-select --project "$OAA_RUN" \
  --spec "$OAA_RUN/contracts/design-intent-spec-v1.json" \
  --output contracts/design-intent-v1.json
python "$OAA_HELPER" intent-check --project "$OAA_RUN"
python "$OAA_HELPER" intent-cases --project "$OAA_RUN"
```

Selection creates immutable `analyst_design_intent` with byte pins and selects it at `project.design_intent`; history remains in `design_intent_history`. Keep the spec and referenced files unchanged after selection: author new versions and select a new record for a revision. A missing candidate can remain null during discovery; selection is not completion. `intent-check` reports consistency, missing selections, unresolved decisions and remote-only asset limitations. A consistent record or exit 0 is not a fulfilled-design or native pass.

## Specification contract

Top level: `schema_version: 1`, `kind: analyst_design_intent_spec`, `branding`, `website`, `logo_sourcing`, `surfaces`, `selections`, `assets`, `requirements`.

| Record | Fields and decisions |
| --- | --- |
| Scope | `branding`: `requested`, `none`, `unknown`; `website`: HTTPS URL or null; `surfaces`: exactly the project's selected surfaces. |
| Logo sourcing | `{mode: unresolved\|supplied\|official_site, authorization_ref, source}`. Official-site mode needs the retained sourcing authorization. It lets subsequent roles continue selection without asking again. |
| Selection | One per surface: `{surface, design_path, brand_path, candidate_path, target}`. Paths may be null while pending. The selected design JSON must declare `brand_contract` equal to `brand_path`; do not silently combine an older design/brand pair. |
| Target | When a candidate exists: `{surface, state: local\|draft\|published, instance, document_id, draft_id}`. Remote targets need the real HTTPS instance origin and document ID; drafts need their draft ID. A local candidate can have null IDs. Target declarations do not authenticate remote state. |
| Asset | `{id, source, authorization_ref, sourcing_mode, local_path, remote_url, variant, placement, appearance, loading_method}`. Exactly one local path or HTTPS remote URL. `sourcing_mode`: `supplied`, `official_site`, `original`; the other descriptive fields must be nonblank. Assets bound to selected logo requirements also need nonblank `size`, `accessible_name` (including explicit decorative handling if appropriate), and `fallback`. Keep additional dimensions and usage limitations in the linked brand contract. |
| Requirement | `{id, category, purpose, surfaces, required, origin, disposition, value, asset_ids, decision_ref, contexts}`. `origin`: `user`, `reused`, `proposal`; `disposition`: `unresolved`, `selected`, `explicitly_omitted`, `deferred`. IDs remain stable across revisions. |
| Context | `{id, appearance, state, viewport?: [width,height]}`. Name relevant appearances/states; add actual intended dimensions when material rather than a universal device matrix. |

A selected requirement needs a decision reference, value or asset IDs, and at least one context. A selected logo needs assets. Explicit omission needs `user` or `reused` origin and its decision reference. Requested branding needs a required logo obligation covering every surface, even if the user explicitly omits it. A previously required obligation cannot simply disappear in the next selection; retain its explicit disposition.

All file paths are canonical engagement-relative regular files, no symlinks or path traversal, within existing file bounds. The helper pins declared local bytes only; it does not crawl, fetch remote assets or execute them. Remote-only assets retain an unverified-byte limitation. Source/use authorization is recorded evidence, not authenticated rights or endorsement. Do not widen App network permissions to repair an asset-loading problem.

## Representative treatment and bounded handoff

Show identity, typography/fallback, color roles, density/spacing, imagery decision and action vocabulary in the existing representative concept or affected component. Use the selected asset, realistic labels/values, one useful primary action and a consequential state. For substantial new/redesign work retain the existing [distinct-concept loop](../../omni-design-systems/references/visual-craft.md), not an extra exercise. Engineering confirms supported native asset loading, font/layout/chart controls and runtime behavior before the mapping is called resolved.

For example, the original [Harbor Works specimen](../../omni-design-systems/assets/craft-specimen.html) uses an original [mark](../../omni-design-systems/assets/harbor-works-mark.svg), a compact identity row, aligned service-request counts, and an “Inspect North queue” link to useful assignment detail. Its warm neutral surface and system type are working design choices; the mark is selected deliberately, not a customer-logo substitute. Its fixtures and local navigation establish no native or customer acceptance. An example requirement fragment is:

```json
{
  "id": "brand-logo",
  "category": "logo",
  "purpose": "Show the selected Harbor Works mark beside the workspace name without hiding the primary task.",
  "surfaces": ["app", "dashboard"],
  "required": true,
  "origin": "proposal",
  "disposition": "selected",
  "value": "Original fictional specimen identity; native mapping pending",
  "asset_ids": ["harbor-mark"],
  "decision_ref": "Original package specimen, working design choice",
  "contexts": [{"id": "light-default", "appearance": "light", "state": "default"}]
}
```

This fragment belongs in `requirements`, not a standalone specification. In a private example engagement, copy the original SVG to a declared local asset path; set its asset metadata to `sourcing_mode: original`, `variant: symbol`, `placement: beside workspace name`, `appearance: light`, the actual chosen loading method, `size: 40 × 40 CSS pixels`, `accessible_name: adjacent Harbor Works text names identity; symbol decorative`, and `fallback: none; retain unresolved identity gap if unavailable`. Record the original-work provenance and scoped use reference; do not invent a customer website or claim approval. A native dashboard may use a supported identity placement different from the App; preserve the purpose and record the adaptation.

For `branding`, `design-systems`, App/dashboard designers, App/BI engineers and QA, `packet` adds the selected intent, spec, design/brand/candidate files and declared local assets to the named inputs. Missing selections/decisions are exposed; stale/conflicting selections reject the packet. Files remain subject to disclosure review and the existing **256 KiB aggregate packet bound**. An index does not sanitize contents or bypass that bound. If a required asset makes a packet too large, report the dependency and arrange a reviewed bounded handoff through the host; never silently omit it or invent a smaller replacement. Legacy projects without a selection stay readable and receive available working design/brand contracts with unassessed intent coverage.

## Review and closeout

`intent-cases` emits **not-run templates**, one per selected required requirement/surface/context. Complete the candidate ID, target, dependency pins, actual reviewer/method and observation. Bind a [design review](../../omni-qa-analyst/references/design-evidence.md) with `intent: {path, sha256}` for the current selected record. Each named case adds `requirement_id`, `requirement_context` (context ID), the requirement's exact `asset_ids`, a concrete `expected` outcome and candidate-bound `capture_ids`.

Inspect the actual image and relevant behavior. A required logo case verifies the chosen variant is loaded, visible, legible and placed as intended for that surface/state; an image tag, capture's existence or general craft pass cannot do this. Named requirement fulfillment requires a selected draft/published target and native captures. A local prototype may support its local craft review, but cannot fulfill the named native requirement. Compare against both the original customer requirement and selected design. Reconcile current design/brand/candidate dependencies, declared asset bytes and capture context before recording a pass. Correct the affected implementation and retain a new review after retest; never relabel an older capture to fit a new asset or candidate.

Close out concisely, per required requirement and surface:

| Requirement | Selected choice / implementation | Current observation | Remaining difference |
| --- | --- | --- | --- |
| Required mark · App | Selected asset and current App candidate | Native capture inspected / not run / failed | Exact gap or none observed in this case |
| Required mark · dashboard | Its supported placement and current candidate | Separate dashboard observation | Adaptation, missing evidence or none observed |

The completion rows retain requirement purpose/origin/disposition, selected value/assets and observation/evidence/capture references. Report recorded requirement fulfillment separately from structural consistency, overall craft, native behavior/access, participant/business acceptance and publication. Explicit authorized omission is preserved; unresolved/deferred required choices remain open. A candidate can be delivered provisionally with named gaps under existing authorization. Migration return/check command results expose a current `design_completion` summary separately from the historical sealed receipt. This keeps current design gaps visible without rewriting historical migration evidence, altering DMA's semantic stage meanings or accepting the model. The helper checks consistency and declared coverage, not visual quality, reviewer authenticity, legal rights or native execution.
