---
name: omni-branding
description: Establish a reusable brand and theme contract for Omni dashboards and native Apps, covering assets, semantic colors, typography, appearances, and surface-specific settings. Use for customer-facing product themes; Omni corporate documents belong to the artifact-branding workflow.
---

# Omni branding

Own the brand interview, decision record, and consistent application across selected surfaces. Reuse accepted answers; ask only for consequential missing or conflicting choices. A generic task does not authorize changing organization-wide themes.

## Inputs and interview

Read the existing engagement brief, brand guidelines/assets, prior accepted theme, target surfaces, audience, and deployment scope before asking questions. Use [the interview and contract](references/brand-contract.md) to consolidate choices. For a standalone request, establish the intended brand and target first. A brand owner's approved source overrides inspiration; use a public site as evidence of observed styling, not proof of licensing or formal brand approval.

For a branded deliverable, ask for the missing company website and logo choice in the smallest relevant question batch: an approved logo file/URL, or authorization to source it from the official website. Reuse prior answers and sourcing authorization; record an explicit no-logo choice when requested. Review only relevant authorized pages for the selected logo/wordmark, colors, typography and imagery, recording source URLs and proposed theme implications. Reconcile observations with approved guidelines and existing Omni theme choices; keep unresolved fonts, assets and permissions visible. Use the bounded [asset manifest](references/brand-contract.md#purposeful-asset-manifest) for selected reusable assets; research references and eligible assets stay distinct. This is not an automated crawler or permission to collect every image.

For migrations, use the presentation and persona facets in [behavior coverage](../omni-qa-analyst/references/migration-behavior.md). Keep observed source formatting separate from the proposed brand treatment, preserving status/category meanings, units, number formats, and audience differences. Reuse accepted brand answers across peer handoffs; a model return does not reset theme decisions or approve a branding change.

## Work

1. Identify the authority for logos, color, typography, and tone; retain asset provenance and unresolved rights. Record the specific selected logo/variant, source, loading path and expected placement using [the logo handoff](references/brand-contract.md#logo-decision-and-handoff). Do not silently replace a requested brand logo with a generic monogram. A temporary placeholder must be labeled and unresolved; optional missing styling choices need not stop provisional design.
2. Define semantic colors and categorical/sequential/diverging chart palettes separately. Preserve category identity across charts and filters. Brand accent does not automatically mean success, loss, risk, or selected state.
3. Establish type roles, available weights, loading source, licensing confirmation, fallback, and numerical behavior. Verify the target's font controls and runtime network policy before promising a custom font.
4. Read [Omni capabilities](../omni-artifact-accelerator/references/omni-capabilities.md). Keep application theme, dashboard/document theme, and App CSS bindings distinct. Produce a field-by-field mapping with target scope, current value if known, candidate value, evidence, and unsupported gaps.
5. Demonstrate the brand on a representative screen: translate identity into type relationships, spacing, content grouping, asset roles and action vocabulary, not only colors. Use [visual craft](../omni-design-systems/references/visual-craft.md) for substantial new work or redesign. Give shared roles to [design systems](../omni-design-systems/SKILL.md), then inspect the actual app/dashboard at representative density and every supported appearance. Use [design QA](../omni-design-systems/references/design-qa.md), including contrast, focus, chart distinctions, font fallback, and logo legibility.

## Outputs and boundaries

Return the versioned brand contract, compact unanswered-question list, theme mapping, asset references, preview, and QA evidence. Distinguish approved brand choices, observed source styling, and recommendations.

Theme import/save behavior and organization/default/bulk scope must be checked before an authorized write. A design request alone does not authorize applying, replacing, or publishing a shared theme. Stop the affected asset or setting for a conflicting usage restriction, unresolved action scope or unsupported loading path; continue unaffected design. Do not request authorization again when the user has already authorized sourcing/use within this scope. Verify the selected logo is actually visible in the target; palette checks establish neither brand identity nor full accessibility conformance.

For Looker migrations, share the brand contract across the selected dashboard and App without changing metric semantics. Reuse the company website URL and approved assets already supplied; ask for them when missing. Track source identity, approved improvements, image/font origin and permission separately. See [the Looker run guide](../omni-artifact-accelerator/references/looker-visual-run.md).

For Hex, use [the shared experience treatment](../omni-app-designer/references/hex-experience-mapping.md#brand-composition-narrative-and-motion). Reconcile supplied themes, generated styles and imagery with the company website and approved assets. Keep their provenance/rights and observed-versus-approved status; reuse one brand contract across both targets without assuming identical theme controls.
