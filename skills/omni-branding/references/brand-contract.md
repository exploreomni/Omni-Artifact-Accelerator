# Brand interview and reusable contract

Inspect existing sources first and reuse accepted answers across subagents and later runs. Ask the smallest useful batch of questions; do not force the user through this entire list. Mark each decision as **provided, source-verified, accepted, proposed, or unresolved**, with provenance and version. Never manufacture approval.

| Decision | Ask when missing | Record |
| --- | --- | --- |
| Authority and identity | Which approved brand guide/assets should govern, and is this Omni, the customer, or a permitted co-brand? | Source links/files, brand owner if stated, logo versions/clear-space rules, permitted uses, and asset-rights evidence. |
| Company website and logo | What is the official website, and should we use an approved logo file/URL or source the logo from that website? Ask only the missing parts; retain an explicit no-logo preference. | Website, intended product/regional brand, selected logo/variant, source, sourcing/use authorization and unresolved restrictions. Reuse prior answers; public visibility alone is not authorization or endorsement. |
| Audience and task | Who uses this, for which decisions, on which screens, and at what density? | Viewer/analyst roles, executive/operational use, primary tasks, supported widths and input methods, density preference. |
| Surface and scope | Is the target a native dashboard, native Omni App, both, or an explicitly requested external embedded application? Which instance/document/scope? | Selected target(s), identifiers when supplied, internal/embed context, organization/default/single-document impact. Never infer external hosting from “app.” |
| Color semantics | Which brand colors are required, and which colors already mean good/bad, selected, risk, or forecast? | Brand accents; foreground/background pairs; neutral/status/focus roles; categorical, sequential, and diverging palettes; category mappings. |
| Typography | Which fonts/weights are approved and available, and what fallback is acceptable? | Family/weights; licensing confirmation; source/load mechanism; fallback stack; headings/body/labels/numbers; locale and numeral requirements. Mark absent evidence unresolved. |
| Appearance | Light, dark, both, or a fixed appearance for a stated reason? | Supported modes, user preference behavior where supported, chart/background pairs, logo variants, and relevant high-contrast needs. |
| Accessibility | What standard, accommodations, and user needs must the experience support? | Target standard/level if stated, keyboard/assistive-technology scenarios, large text, color-vision and motion requirements, known platform constraints. |
| Voice and interaction | What should the experience sound and feel like? | Plain-language vocabulary, formality, terminology, desired motion restraint, error/empty-state tone. Avoid importing marketing tone into analytical claims. |

## Candidate contract

Use the engagement's existing schema if available; otherwise record these fields in a small human-readable file. This is a design contract, **not an Omni import schema**.

- Identity: engagement, version, chosen surface(s), source authority, accepted/proposed status.
- Website: supplied URL, canonical domain when verified, brand/product context, scoped page references, review date and observed-versus-approved findings. No website supplied means discovery unavailable, not invented branding.
- Assets: specific selected logo or explicit omission; reference, variant, purpose, provenance, use authorization, loading path, expected placement and target visibility evidence. Keep temporary placeholders labeled and unresolved.
- Tokens: semantic role, candidate value, light/dark variant where relevant, contrast partner, target mapping, support status.
- Typography: roles, font source and rights, fallback, number formatting considerations, measured overflow/fallback findings.
- Data color: palette purpose, ordered categories, business semantics, non-color encodings, behavior for unknown/new categories.
- Experience: density, layout rhythm, component states, motion policy, accessibility target.
- Scope: proposed theme destination, intended users/documents, current settings snapshot if available, effects requiring review.
- Evidence: official product references, preview paths, QA results, unresolved decisions, and acceptance record when explicitly given.

## Applying choices to Omni

Consult the maintained [Omni capability reference](../../omni-artifact-accelerator/references/omni-capabilities.md). Treat these as separate mappings: application theme; dashboard/document theme; native App CSS variables; external host styles only when that surface is selected.

Do not distribute a fabricated theme-import payload. Confirm actual export/import shape and current field behavior. Preserve a snapshot before an authorized change and explicitly account for omitted fields, defaults, document propagation, and save effects. An unavailable font or chart-color feature is a documented gap, not permission to change surfaces or loosen network/security policy.

## Logo decision and handoff

A requested branded experience needs an explicit logo decision, not an inferred substitution. Combine missing website and approved-file/URL or official-site sourcing authorization into the existing short interview. Reuse an answer across roles and later turns. If sourcing is already authorized, select a suitable official variant and record it; do not ask again merely because the file was not supplied. Record any actual conflicting restriction without claiming third-party endorsement or legal approval. If the user wants no logo, record that omission and skip unrelated logo research.

Hand engineering the selected asset ID, exact file/URL and hash when retained, variant (for example, symbol versus wordmark and light/dark), source page, authorization reference, loading path, aspect ratio, intended size/placement, alternative text and fallback. A temporary text/monogram placeholder may support provisional work only when visibly labeled and retained as unresolved; it cannot satisfy the requested logo or become the final choice silently. An unavailable native loading path returns a specific gap, not a generic replacement. Verify the chosen asset appears correctly in the actual target; color-only QA does not establish brand identity.

## Brand-to-composition specimen

For substantial new work or redesign, add `brand characteristic → concrete visual/interaction choice → specimen → target mapping → finding`. For example, a proposed calm editorial identity can mean concise selected-object headings, exact aligned values, thin grouping rules and generous space around the primary result. It need not mean a large marketing hero or green on every surface. Demonstrate the choice using representative labels and states; retain proposed versus accepted status. Use [visual craft](../../omni-design-systems/references/visual-craft.md). A focused correction reuses the existing direction.

## Purposeful asset manifest

Keep a bounded human-readable manifest in the engagement. This records selected candidates; it does not crawl sites or automate downloads. Reuse the official website/brand answer, inspect only relevant authorized pages, and distinguish source observations from reusable bytes. A publicly visible logo, photo or font does not establish usage rights.

```yaml
asset_id: <stable local ID>
source: <official page URL / supplied file / original work>
brand_and_purpose: <identity, orientation, analytical explanation; omit decoration with no value>
evidence_type: <observed reference / supplied approved asset / original candidate>
permission: {status: unresolved, evidence_ref: null, permitted_use: null}
file: {path: null, sha256: null, media_type: null, dimensions: null}
composition: {focal_point: null, crop: null, aspect_ratio: null, appearance_variant: null, expected_placement: null}
accessibility: {alt_text: null, decorative: false}
runtime: {loading_source: null, network_requirement: none, fallback: null}
decision: <reference_only / proposed_for_use / eligible_for_scoped_use / rejected>
```

Retain local bytes/hash only when actually obtained within scope; do not invent a download or permission record. Preserve aspect ratio and relevant crop/focal detail. Include font family/weight, licensing evidence and loading/fallback separately. New hosted assets or external network requirements remain explicit implementation decisions; a useful local/system-font design can proceed without them. Reference screenshots are research evidence, not assets to embed into the customer's App. Public package specimens must be original/synthetic or have suitable redistribution rights.

Return the selected manifest and a rendered brand specimen with actual theme/font/focus/selected-state findings. A brand-source update may invalidate assets/tokens and affected visual checks; it does not automatically reopen unrelated metric definitions or authorize a shared-theme mutation.
