---
name: omni-backend-handoff
description: Coordinate versioned requirements and candidate responses between the Omni Artifact Accelerator frontend and Data Model Accelerator backend, preserving source routes, changes, dependencies and separate validation authority.
---

# Frontend and backend cowork

Use either from the analyst orchestrator or from Data Model Accelerator. The analyst owns decisions, experience and consumption; DMA owns warehouse/semantic design and implementation within its stage gates. Keep one owner per file/object, one active semantic baseline per analyst engagement, and one shared decision record. Do not make the user repeat discovery or coordinate workers manually.

For substantial new design, material redesign, explicit craft feedback or deliberate practice, apply the [curriculum role route](../omni-design-systems/references/experience-curriculum.md#role-routes) to the experience's actual data dependencies. Translate a [chosen encoding or interaction](../omni-design-systems/references/experience-patterns.md) into the minimum missing grain, stable identity or measure, with affected consumers and independent expectations in the existing bounded request; leave craft choices with the frontend.

Read [the cowork contract](references/cowork-contract.md). For a fresh frontend, accept DMA's curated semantic handoff through the analyst helper. For a frontend-originated requirement, freeze a bounded request with exact assets, metrics, source IDs and independent expected cases. For new work without a backend catalog, send an explicit unbound request; never invent a baseline. When DMA initiates frontend work, pass its existing decisions and the exact requested surfaces without reducing `full_dashboard` to semantic completion.

For end-to-end migrations, read [migration lifecycle](references/migration-lifecycle.md). Use `dma_frontend.py` to export the selected backend context, `migration.py` to freeze every supplied source-asset disposition, and scope-linked cowork requests for model gaps. Return candidate-bound frontend artifacts and separate QA lanes, then register the checked scope/return through DMA's existing supporting-evidence API. Assessment may proceed without a semantic candidate. Preserve backend-only scope; an independent frontend is not an implicit expansion of DMA's delivery.

## Scope and route first

Honor the source migrator's existing route and authority:

- Sigma `omni_semantic_reconstruction`: no dbt/upstream changes. `warehouse_first_refactor`: route actual upstream gaps to DMA. There is no default; a missing choice permits source analysis only. A declared route in imported metadata needs the host's actual decision evidence before dependent work.
- Existing-topic/dashboard-only scope: preserve exact definitions and bindings. Compatibility questions do not authorize model edits.
- Domo: preserve Page/unit/cycle, source object hashes, plan/Topic registrations, unresolved behavior, owner and side-effect handoffs. An external redesign assignment grants no build, write or release authority.
- Power BI: retain the independent PBIR visual inventory alongside the correctly typed DMA semantic evidence. A missing model or unsupported visual role must not remove page/visual obligations. Send exact DAX/filter-context/security gaps with affected consumers; retain the selected semantic-only or warehouse route and the existing packet budget. See the [Power BI workflow](../omni-artifact-accelerator/references/powerbi-visual-run.md).
- Net-new work: reuse existing warehouse/semantic assets where sound. Request only actual gaps; do not force a backend rebuild to improve a frontend.

## Round trip

1. Frontend creates a request with `scripts/cowork.py request`. Load only the relevant source inventory, metrics/query/design slice and expected cases. Keep unrelated customer data out of the packet. The host records existing route/decision evidence separately; generated records are not authorization.
2. Invoke the actual DMA stage skill/host for the requested work. Check the installed DMA version and reuse its saved engagement, domain selection, accepted decisions and task freshness. Local helpers do not spawn agents. A request to clarify semantics is not implementation approval.
3. DMA supplies its real curated `SEMANTIC_REVIEW.json` plus one proposed/unresolved/declined resolution per requirement. Use `respond` to bind this candidate to the exact request. Existing DMA checks, disclosure scans and review remain in force.
4. Frontend uses `receive` to check the response, request and selected-input freshness. It retains previous evidence and computes an affected-consumer report. Then use `select` only to choose the returned local candidate as the working baseline within the current task; this grants no approval or native status.
5. Dispatch bounded delta work to the relevant BI/designer/engineer and independent QA roles. Reuse unaffected assets only when dependency bindings justify it. Keep unresolved requirements, source changes and negative-control failures visible.

Generate one request/response cycle per coherent dependency change. Do not rescan the entire source estate on every exchange. Reuse a relevant worker; record actual host dispatch and results. Stop a repeated unresolved loop after one correction review and return the exact decision/evidence need, while independent work continues.

## Completion

Frontend and backend each return versioned files, current bindings, unresolved definitions, actual evidence and next owner. The integrated handoff exposes warehouse, semantic, query, UI, access, operational and business-acceptance lanes separately. Do not close a request because a response file arrived or a producer wrote `proposed`. Do not treat a local `select` as approval or overwrite prior QA.

Run `migration.py check` before returning frontend evidence. Candidate coverage counts retained files within declared scope; it does not verify their behavior. Changed source/domain/model inputs require a fresh scoped handoff and affected checks. Record results with `dma_frontend.py record` only against the current frontend project and DMA context; ordinary evidence revisions are allowed, material scope drift is not. DMA still uses its normal finalizer and assurance gates. Retain App source in the frontend package and provide inert summary/hash/dependency records to DMA.

Source registries, Domo control-plane policy, Sigma terminal review, DMA design gates and target publication controls remain with their owning runtimes. Do not emulate or bypass them in this bridge.

For standalone `reuse_existing`, follow the [typed existing-Omni baseline and return](../omni-artifact-accelerator/references/tableau-visual-run.md#standalone-existing-topic-path). `standalone.py` supports a separate `analyst_standalone_migration_return` through the existing migration CLI without inventing a DMA catalog. It recomputes source scope, definitions, candidate/readback and coverage; recorded remote inspection is not current remote freshness. Missing backend catalogs retain the previous assessment-only behavior unless this explicit standalone contract is selected. Genuine semantic changes still use real DMA or model-owner collaboration.

For Looker, retain the original canonical-dashboard and generic source-adapter contracts through [the visual workflow](../omni-artifact-accelerator/references/looker-visual-run.md). Reuse the actual source scope/request/candidate/return APIs and selected route. App and dashboard consumers can share semantic definitions but need distinct target candidates and surface evidence; never force warehouse work from a presentation choice.

For Hex, follow the [shared dashboard/App workflow](../omni-artifact-accelerator/references/hex-visual-run.md). Retain both typed DMA producer contracts and complete source dependencies. Each requirement’s reviewed `target_surfaces` assignment must agree with frozen scope units. A combined return requires distinct native documents and proofs; selecting a backend candidate does not establish deployed queries, App runtime behavior or either surface’s acceptance. Keep full source evidence privately available when dividing requests into dependency-complete 256 KiB waves.
