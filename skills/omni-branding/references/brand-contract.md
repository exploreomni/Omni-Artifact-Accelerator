# Brand interview and reusable contract

Inspect existing sources first and reuse accepted answers across subagents and later runs. Ask the smallest useful batch of questions; do not force the user through this entire list. Mark each decision as **provided, source-verified, accepted, proposed, or unresolved**, with provenance and version. Never manufacture approval.

| Decision | Ask when missing | Record |
| --- | --- | --- |
| Authority and identity | Which approved brand guide/assets should govern, and is this Omni, the customer, or a permitted co-brand? | Source links/files, brand owner if stated, logo versions/clear-space rules, permitted uses, and asset-rights evidence. |
| Company website | What is your company's official website URL, and should this experience follow a particular product, subsidiary or regional brand? | Supplied/canonical URL, intended brand, inspected pages/date, observed logo/colors/fonts, conflicting guidelines and unresolved reuse rights. Reuse a supplied URL; do not infer approval from public visibility. |
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
- Assets: reference, purpose, provenance, use permission status, appearance variants.
- Tokens: semantic role, candidate value, light/dark variant where relevant, contrast partner, target mapping, support status.
- Typography: roles, font source and rights, fallback, number formatting considerations, measured overflow/fallback findings.
- Data color: palette purpose, ordered categories, business semantics, non-color encodings, behavior for unknown/new categories.
- Experience: density, layout rhythm, component states, motion policy, accessibility target.
- Scope: proposed theme destination, intended users/documents, current settings snapshot if available, effects requiring review.
- Evidence: official product references, preview paths, QA results, unresolved decisions, and acceptance record when explicitly given.

## Applying choices to Omni

Consult the maintained [Omni capability reference](../../omni-artifact-accelerator/references/omni-capabilities.md). Treat these as separate mappings: application theme; dashboard/document theme; native App CSS variables; external host styles only when that surface is selected.

Do not distribute a fabricated theme-import payload. Confirm actual export/import shape and current field behavior. Preserve a snapshot before an authorized change and explicitly account for omitted fields, defaults, document propagation, and save effects. An unavailable font or chart-color feature is a documented gap, not permission to change surfaces or loosen network/security policy.
