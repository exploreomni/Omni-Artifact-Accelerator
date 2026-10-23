# Saved design intent and named review

Use this additive record when carrying design decisions through an App/dashboard engagement. It does not change the version-1 project lifecycle, grant permission or replace the detailed design, brand, query and QA contracts. Direct specialists use the same selection as the orchestrator. A focused edit reuses it and reviews only affected requirements; a faithful migration retains source identity and accepted differences without a new redesign interview.

## One short interview, persistent decisions

Read existing decisions first. Ask only the missing consequential choices together: intended task/audience, selected surfaces, required identity and the requested completion stage. Separate required choices from optional preferences. For branded work, combine the missing company website with an approved logo file/URL, authorization to source the official website, or an explicit no-logo choice. Reuse prior answers and authorization. A website does not select a logo; authorization to source one is not the asset selection itself.

Keep each required unanswered or deferred choice open. A working recommendation can guide reversible prototyping but remains `origin: proposal`; it must not become a user decision by implication. A placeholder is visibly provisional and cannot satisfy the requested identity. Optional photography, exact corporate fonts or animation are not universal requirements. If the user chooses no logo, record an explicit omission with its decision reference and skip unrelated asset research.

If the user explicitly excludes website research or chooses a supplied brand authority without a website, retain that choice as a requirement with `category: website`, `disposition: explicitly_omitted`, `origin: user` or `reused`, its actual `decision_ref` and affected `surfaces`. Omission records covering every selected surface suppress the generic missing-website question. An agent proposal, partial-surface omission, supplied logo alone or missing URL does not. This changes the interview prompt only; logo selection, provenance, unresolved required choices and native evidence still apply. A free-text note or arbitrary ID is not a structured website omission.

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

An untouched unknown-branding starter can follow a surface change during initial migration setup; the checker reports that projection without rewriting the draft. Once a draft contains a website, authorization, asset or design decision, reconcile its scope explicitly. Selected records always retain their recorded surface scope.

## Current context and resume

`intent-check` includes a derived `current_context`: the selected intent pin, historical intent pins, unresolved required IDs and integrity status. The actual decisions remain in `requirements` and `selections`; the index is not a second authority or a claim that all linked documents are current. It does not read historical files or authenticate user decisions.

Maintain a concise current-context section in the engagement's `START_HERE.md`: selected intent/design, source/query/runtime references, brand and content mode, usable viewport, tooling and remaining verification gaps. Identify older proposals by path and the selection that supersedes them. Frozen reviews and evidence remain unchanged; a historical document saying “current” does not outrank the selected record or new user feedback. Record new consequential feedback in a new intent version before dependent work resumes.

After preparing a task packet, and again before resuming it, run:

```sh
python "$OAA_HELPER" packet-check --project "$OAA_RUN" --packet tasks/app-engineer-v1.json
```

The read-only check compares the saved packet's selected intent, decisions, current DMA catalog, fixed generated fields and declared input hashes/sizes with the current engagement. It reuses path, registration, DMA freshness and aggregate-size checks. Both declared input bytes and serialized packet metadata have a 256 KiB ceiling; history entries retain compact path/hash/size pins. Host-specific objectives, outputs and acceptance notes can be added as separate fields such as `host_context`; do not rewrite the generated role, authority or trust fields. Those additions remain untrusted descriptive context, not permission. Exit 1 reports inconsistent/stale context; regenerate a new packet after reconciling the affected dependencies. Malformed paths/inputs may exit 2. It never dispatches a worker, rewrites the packet, grants permission or establishes native behavior. Older packets without the optional derived index remain usable if their actual decisions and inputs are current. Independent numerical/backend work can continue when its own inputs are unaffected.

Declare runtime, callback evidence, aliases and other required files explicitly with repeated packet `--input` arguments and applicable review dependencies. Register reviewed versions with the existing `register` helper when appropriate. Descriptive paths inside `requirements[].value`, and nested runtime `evidence_paths`, are **not** crawled by the packet helper. A consistent packet only verifies declared inputs; dependency completeness and source authenticity still require scoped review. The optional `delivery.dependency_paths` field is an explicit alternative to repeated inputs for required files; it is pinned and automatically carried to relevant specialists. Retain the 256 KiB bound and existing host-arranged handoff for larger dependencies.

## Specification contract

For substantial experiences, optional `requirements[].delivery` adds observable behavior, responsibility, named destinations and explicit dependency paths. See [first-delivery coverage](first-delivery.md). These declared paths are pinned and carried into packets; arbitrary nested prose links remain uncrawled. Existing records without these annotations remain valid.

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

## Experience requirements

For substantial new work or material design correction, apply the [shared experience brief](../../omni-design-systems/references/experience-brief.md). Preserve the user's quality expectations and translate them into concrete choices. Add only requirements warranted by the task; do not change every starter or reopen discovery for a faithful migration or focused edit. Version 1 already accepts structured `value` content, so no new lifecycle or schema is needed.

The following are illustrative entries inside an existing specification's `requirements` list. They are proposals for an original library investigation, not real user decisions, an import payload or a mandatory layout. Change their origins/references only when actual evidence warrants it. A selected proposal remains a proposal.

```json
[
  {
    "id": "experience-mode", "category": "experience",
    "purpose": "Resolve how a library operations analyst first enters the branch-change investigation.",
    "surfaces": ["app"], "required": true, "origin": "proposal", "disposition": "selected",
    "value": {"mode": "branded_entry_to_workspace", "opening_promise": "Find which branches explain the monthly circulation change.", "primary_action": "Inspect branch changes", "repeat_use": "Open the investigation directly from persistent navigation"},
    "asset_ids": [], "decision_ref": "Synthetic studio working direction; not user approval",
    "contexts": [{"id": "entry", "appearance": "light", "state": "ready-entry"}]
  },
  {
    "id": "entry-return-journey", "category": "interaction",
    "purpose": "Keep the selected branch and period while moving between introduction, investigation and evidence.",
    "surfaces": ["app"], "required": true, "origin": "proposal", "disposition": "selected",
    "value": {"destinations": ["Introduction", "Investigation"], "useful_detail": "Selected branch monthly observations and contribution to total change", "retain": ["comparison months", "selected branch"], "return": "Restore the selected branch trigger or the list heading", "narrow": "Stage list and detail when both no longer fit", "motion": "Brief interruptible detail transition; exact values immediate; static reduced-motion equivalent"},
    "asset_ids": [], "decision_ref": "Synthetic studio working direction; not user approval",
    "contexts": [{"id": "return", "appearance": "light", "state": "detail-return"}]
  },
  {
    "id": "art-direction", "category": "composition",
    "purpose": "Express an editorial library identity while keeping exact branch evidence readable.",
    "surfaces": ["app"], "required": true, "origin": "proposal", "disposition": "selected",
    "value": {"reference_quality": "Clear editorial hierarchy with a direct route into work", "avoid": "Equal emphasis on every summary and an obligatory tour", "typography": "Display hierarchy for the invitation; system body and aligned tabular values", "imagery": {"decision": "omitted", "reason": "Typography and an original abstract motif establish the selected character"}, "density": "Spacious introduction; focused branch list and evidence workspace", "resolved_geometry": "Values and responsive rules live inline in the selected design JSON"},
    "asset_ids": [], "decision_ref": "Synthetic studio working direction; not user approval",
    "contexts": [{"id": "workspace", "appearance": "light", "state": "ready-investigation"}]
  }
]
```

An unresolved consequential requirement keeps `value: null`, `disposition: unresolved` and no invented decision reference; the existing checker then surfaces its purpose as an open question. Reuse an explicit user/reused answer before asking. A direct single-screen workspace can resolve `experience-mode` without adding an introduction, image or motion obligation. `art-direction` being required does not make every optional image or font required.

Keep detailed choices inline or inside the selected design JSON. Paths nested within `value` are descriptive only and are not automatically pinned; declare additional references through selected files, explicit packet inputs and review dependencies/evidence. Preserve earlier required IDs/dispositions when versioning rather than dropping inconvenient requirements. The checker validates structure and freshness, not the aesthetic merit of these choices.

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

For `branding`, `design-systems`, App/dashboard designers, App/BI engineers, `motion-designer`, `data-storyteller` and QA, `packet` adds the selected intent, spec, design/brand/candidate files and declared local assets to the named inputs. `design_context.selected_intent` exposes the exact governing selection pin, or null while unselected. Missing selections/decisions are exposed; stale/conflicting selections reject the packet. On dispatch or resume, reconcile that pin with the current `intent-check` result and recheck input hashes; packets do not update or revalidate themselves after creation. Regenerate stale handoffs. Files remain subject to disclosure review and the existing **256 KiB aggregate packet bound**. An index does not sanitize contents or bypass that bound. If a required asset makes a packet too large, report the dependency and arrange a reviewed bounded handoff through the host; never silently omit it or invent a smaller replacement. Legacy projects without a selection stay readable and receive available working design/brand contracts with unassessed intent coverage.

## Review and closeout

`intent-cases` emits **not-run templates**, one per selected required requirement/surface/context. Complete the candidate ID, target, dependency pins, actual reviewer/method and observation. Bind a [design review](../../omni-qa-analyst/references/design-evidence.md) with `intent: {path, sha256}` for the current selected record. Each named case adds `requirement_id`, `requirement_context` (context ID), the requirement's exact `asset_ids`, a concrete `expected` outcome and candidate-bound `capture_ids`.

Inspect the actual image and relevant behavior. A required logo case verifies the chosen variant is loaded, visible, legible and placed as intended for that surface/state; an image tag, capture's existence or general craft pass cannot do this. Named requirement fulfillment requires a selected draft/published target and native captures. A local prototype may support its local craft review, but cannot fulfill the named native requirement. Compare against both the original customer requirement and selected design. Reconcile current design/brand/candidate dependencies, declared asset bytes and capture context before recording a pass. Correct the affected implementation and retain a new review after retest; never relabel an older capture to fit a new asset or candidate.

Close out concisely, per required requirement and surface:

| Requirement | Selected choice / implementation | Current observation | Remaining difference |
| --- | --- | --- | --- |
| Required mark · App | Selected asset and current App candidate | Native capture inspected / not run / failed | Exact gap or none observed in this case |
| Required mark · dashboard | Its supported placement and current candidate | Separate dashboard observation | Adaptation, missing evidence or none observed |

The completion rows retain requirement purpose/origin/disposition, selected value/assets and observation/evidence/capture references. Report recorded requirement fulfillment separately from structural consistency, overall craft, native behavior/access, participant/business acceptance and publication. Explicit authorized omission is preserved; unresolved/deferred required choices remain open. A candidate can be delivered provisionally with named gaps under existing authorization. Migration return/check command results expose a current `design_completion` summary separately from the historical sealed receipt. This keeps current design gaps visible without rewriting historical migration evidence, altering DMA's semantic stage meanings or accepting the model. The helper checks consistency and declared coverage, not visual quality, reviewer authenticity, legal rights or native execution.
