# Optional DMA entrypoint

Review the complete 14-skill bundle in its source checkout first. Follow the [package-use policy](../../skills/omni-artifact-accelerator/references/dependency-policy.md): installation, activation and upstream imports each require explicit scoped sign-off. The public installer apply path is currently disabled; manual copies into active skills are not an alternative activation route.

Prepare this hook in an inactive review copy of DMA. A future qualified host installation may place [analyst-cowork.md](analyst-cowork.md) into `data-model-accelerator/references/` and add the following paragraph near delegation guidance after the exact source, destination and action are authorized:

> When the engagement includes analyst dashboards or Apps, use the optional analyst cowork integration at `references/analyst-cowork.md` with the separately installed `omni-artifact-accelerator` and `omni-backend-handoff` skills. Keep DMA as the warehouse/semantic owner and exchange bounded, versioned requirements and curated semantic candidates. Reuse the saved domain, route and reviews; this integration adds no frontend requirement to `model_only` work and does not turn a `full_dashboard` commitment into a semantic-only completion.

Preserve other DMA content and local changes. Verify the reference exists in the reviewed copy before adding the hook. This optional documentation change is deliberately separate from the analyst installer, which owns only its listed 14 skills. No DMA engine, stage gate or release behavior is replaced. Source review can read either companion skill directly without activating it.

## Optional local adapter

The installed backend-handoff skill includes [dma_frontend.py](../../skills/omni-backend-handoff/scripts/dma_frontend.py). It exports a scope-bound snapshot of an existing trusted DMA saved engagement, then records an OAA scope or return through DMA's existing unverified-evidence API. It never rewrites DMA stages, authenticates approval, executes customer code, or applies target changes. The complete [cowork workflow](analyst-cowork.md#optional-saved-state-adapter) documents the two commands, exact receipt linkage, assessment-only behavior and finalizer boundaries.

Every invocation requires an explicit `--dma-scripts` path to a trusted existing installed DMA or inspected checkout. This is code selection by the host, not a path to discover from untrusted input. Registration also requires `--frontend-project` to verify the actual retained OAA scope, files and catalog, and accepts only the existing DMA `full_dashboard` scope. The adapter requires Python 3.9+ on DMA's supported POSIX host and its existing runtime dependencies. It writes only a requested private context and, for `record`, the normal DMA audit/evidence state; refreshing local source/catalogue inputs can add an audit revision even when a stale receipt is rejected. Exports never overwrite; JSON and symlink boundaries are checked. Keep a serial owner for a saved engagement.

Only after approval covers the exact upstream DMA revision, interpreter and dependency closure, run the optional synthetic compatibility tests against the actual DMA state methods and local collector:

```sh
OMNI_ANALYST_DMA_CHECKOUT=/absolute/trusted/DataModelAccelerator \
  python3 -m unittest discover -s tests -p test_dma_frontend_integration.py -v
```

Run from the OAA package root with the explicitly approved runtime and YAML/SQL dependencies. Cached or installed packages are not approval. Without this environment variable, the real-DMA cases skip explicitly; standalone JSON-boundary cases still run. The composed test uses actual source translation, DMA candidate building, OAA scope/return checks and DMA evidence methods; it checks that later frontend file/catalog drift and a valid candidate belonging to another DMA context prevent registration. Assessment with no catalog remains supported. These tests prove bounded local coordination only, not a customer migration, native tenant validation or business acceptance. Do not synchronize unrelated DMA source/installed changes when adding this optional integration.
