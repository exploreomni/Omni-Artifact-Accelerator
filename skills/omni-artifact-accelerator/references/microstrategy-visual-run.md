# Strategy migration workflow

Use [omni-microstrategy-migrator](../../omni-microstrategy-migrator/SKILL.md)
inside the current engagement. This workflow retains original source evidence,
prepares target requirements and optionally runs explicitly scoped source capture.
It does not install software, configure a remote connector or publish an Omni target.

1. Qualify source origin/context path, project/principal, saved object GUID/type,
   Library and Intelligence Server versions, classic/Mosaic and Library/embedded
   context. Unknown versions use supplied evidence. Choose target surfaces
   independently of source naming.
2. Collect original definitions, an independent inventory and exact crosswalks
   using the [source contract](../../omni-artifact-translator/references/microstrategy-source-contract.md).
   Preserve shared definitions and every repeated placement, control, hidden,
   unavailable/private or unsupported obligation. Keep originals outside the repo.
3. Import and verify retained bytes. Project migration requirements and qualify
   query definitions, metric grain, prompts, filter stages and security. Metadata
   availability is not numerical completeness or effective-user access.
4. If using an existing authorized official MCP connection, discover actual
   schemas/version and retain selected metadata/query calls. Run the passive local
   checker. Do not infer layout/export support or set up a connector automatically.
5. For connected REST capture, retain the tenant API schema and version pins;
   prepare exact operations before import. Separately grant execution and render
   only when requested. Read actual prompt/selector state after changes. Uncertain
   POSTs/state updates require reconciliation rather than blind replay.
6. Preserve full-result evidence with definition, owned instance, observed state,
   principal, population and freshness. Rendered PDF/image evidence has its own
   lane. Unsupported lifecycle/cleanup operations remain explicit obligations;
   never improvise modeling-instance deletion for an analytics instance.
7. Finish A access, B analysis and C narrative before the D product interview.
   Preserve fidelity/redesign decisions, quality ambition, official branding,
   devices, exports, interactive/dimensional visuals and cache/refresh policy.
   At E produce exactly three concrete viable concepts and record the actual
   user choice before detailed design and F coding. Reuse valid prior answers.
8. Reuse existing Omni bindings; send genuine gaps through scoped DMA cowork.
   Preserve source pins, scope, route, grain, semantics/security and independent
   expectations. No MicroStrategy DMA producer or universal compiler is supplied.
9. Review numerical, interaction, visual, access, accessibility and performance
   evidence independently. Deliver separate dashboard/App candidates, adaptations
   and outstanding obligations. Source-only checks cannot establish live acceptance.

## Local entry points

Use an existing Python runtime and a private engagement directory. The journal
uses the existing POSIX locking profile on macOS/Linux; another host needs
qualified locking, not disabled locks. No dependency installation is needed.

```sh
python3 -I -S -B skills/omni-artifact-translator/scripts/microstrategy_capture.py --help
python3 -I -S -B skills/omni-artifact-translator/scripts/microstrategy_capture.py import-local \
  --request /private-engagement/inputs/request.json \
  --source-root /private-engagement/inputs/supplied \
  --directory /private-engagement/inputs/capture --allow-source-read
python3 -I -S -B skills/omni-artifact-translator/scripts/microstrategy_capture.py check \
  --capture /private-engagement/inputs/capture
python3 -I -S -B skills/omni-artifact-translator/scripts/translate_artifact.py \
  --format microstrategy-api /private-engagement/snapshot.json \
  --output /private-engagement/inventory.json
python3 -I -S -B skills/omni-artifact-accelerator/scripts/visual_mcp.py \
  --project /private-engagement
```

Default local tools are `microstrategy_import_local`, `microstrategy_import_evidence`,
`microstrategy_translate`, `microstrategy_import_capture`, `microstrategy_check_capture`,
`microstrategy_normalize_results`, `microstrategy_check_mcp`. They do not contact a
source tenant or grant target writes.

The optional connected host takes `--microstrategy-request` and
`--microstrategy-directory` relative to the engagement plus
`--enable-microstrategy-capture`. Execution and PDF need separate
`--enable-microstrategy-execution` and `--enable-microstrategy-render` switches.
A reserved `--enable-microstrategy-cleanup` grant does not enable unsupported
cleanup routes. The exact request must precede import; do not widen it later.

Supply `MICROSTRATEGY_AUTH_TOKEN` and `MICROSTRATEGY_COOKIES` through the authorized
host environment; `--microstrategy-token-env` and `--microstrategy-cookie-env`
select other `MICROSTRATEGY_...` variables. Keep the token and complete relevant
cookie bundle together. Never put credentials in chat, command arguments, request
JSON, evidence or repo fixtures. Borrowed sessions are not logged out. These
cooperating-host checks are not an isolation boundary against an operator who
controls Python or the host.

## Qualification

Focused first-party checks use `python3 -I -S -B scripts/validate_source.py --case NAME`:
`microstrategy-capture`, `microstrategy-projection`, `microstrategy-mcp`,
`microstrategy-host`, `microstrategy-integration`, `metadata`. Fixtures are
original and synthetic; no real customer data or brand examples belong in them.

A live pilot is a separate optional milestone: selected tenant/project and
multi-page dossier, changed selector, a supported prompt, shared metric,
allowed/denied personas, original visual references and Omni development target.
Qualify schema/version, complete results, current state, rendering and effective
access in that environment. If unavailable, record those lanes as unqualified.

## Current connected limits

The connected profile retains selected ordinary report and dossier definitions,
instance responses and bounded result pages. PDF export is dossier-only; report
PDFs use supplied evidence. Shared semantic definitions (metrics, attributes and
security filters) are retained through supplied original metadata. Actual
native state readback must expose the exact reviewed filter crosswalk and
completed execution evidence; absence blocks result/render acquisition. Synthetic
transport fixtures exercise this guard but do not establish that a particular
Library deployment supplies those fields. Supplied evidence remains available
for unsupported state shapes, documents, cubes and Mosaic.

Only the narrow supported prompt/selector payloads execute. Unresolved, omitted,
all, expression/level and other unsupported prompt modes stay obligations. No
analytics cleanup endpoint is qualified here; record owned instance IDs and
expiry/reconciliation work. Do not substitute Modeling API cleanup. The initial
session bundle is borrowed: any returned token/cookie header stops this profile
for host requalification, including reissued unchanged cookies.
