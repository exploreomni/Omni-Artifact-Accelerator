# 2. Prepare your first engagement

[Learning guide](README.md) · [Previous: understand](01-understand.md) · [Next: data and story](03-data-and-story.md)

**Outcome:** your agent can identify the selected package, available tools and private working folder before starting artifact work.

If DMA supplied the Topic, start with its [Topic handoff](../../skills/omni-backend-handoff/references/topic-first.md). At Stage A, verify access in the intended model. At Stage B, map each panel to a saved query on that Topic and return missing measures to the model owner.

## Bring a small, useful brief

You do not need all the design answers yet. Start with:

| Input | What to provide |
| --- | --- |
| Decision and audience | Who will use this, what they need to decide, and what action follows |
| Data location | Omni instance plus a model, Topic or workbook reference when known; otherwise ask for read-only discovery |
| Access context | Whose account should be verified; an administrator's access does not prove everyone else's |
| Starting material | A new question, existing artifact, source export or backend handoff |
| Boundaries | Approved tools, read-only versus write scope, and any browser, dependency or publication restrictions |
| Known preferences | Experience, brand, devices or refresh choices you already have; the agent should retain them for later discovery |

Share URLs and IDs, not credentials. Configure secrets through your organization's approved connection mechanism. Keep customer data and generated outputs outside the package repository.

## Select one source and host

Use an authorized checkout or an already approved installation. Have your agent identify the exact path and revision it can read. “Latest main” requires a current source check and a matching clean checkout; a folder named after the project is not enough.

| Route | Start here |
| --- | --- |
| Local repository in Codex | Read root [AGENTS.md](../../AGENTS.md), then the [orchestrator](../../skills/omni-artifact-accelerator/SKILL.md) |
| Local repository in Claude Code | Read root [CLAUDE.md](../../CLAUDE.md), then the same orchestrator |
| Another connected host | Explicitly retrieve the orchestrator and relevant supporting files; report which tools and helper execution are actually available |
| Existing approved skill installation | Identify the loaded location and compare it with the selected source; file identity alone does not prove cached host loading |

A host that can read instructions but cannot run the required gates can help gather evidence and present options. It must report unrun checks and cannot claim a completed gated build.

**No installation is required to read this guide.** The package's skill installer currently supports read-only preview and verification; `--apply` is disabled pending a qualified host approval gate. Do not copy files into an active skills directory as a workaround. Installing, importing/loading, updating or activating dependencies or skills requires explicit scoped sign-off under the [dependency policy](../../skills/omni-artifact-accelerator/references/dependency-policy.md). No Blender code or execution is permitted.

## Optional local setup for a technical partner

Use an existing approved Python runtime. From the repository root, this original standard-library check reads package structure without installing dependencies:

```sh
python3 -I -S -B scripts/check_package.py
```

`-I -S` avoids user/site startup packages; it is not an operating-system sandbox. A successful package check does not verify a tenant, host enforcement or visual quality.

For a **new repository-only engagement**, initialize a private sibling folder. In this example the checkout and engagement share a parent; choose a new folder name and the surface appropriate to your task:

```sh
OAA_RUN="$(dirname "$PWD")/artifact-learning"
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py init \
  --output "$OAA_RUN" --name 'Artifact learning' --mode net-new --surface app \
  --selection-policy conversation-evidence-v1
python3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py plan \
  --project "$OAA_RUN"
```

Initialization creates records and a role plan. It does not run agents, connect Omni or build an App. Valid surfaces are `dashboard`, `app`, `both` and `report`. If an engagement already exists, resume it instead. If you received a Data Model Accelerator continuation, follow [lesson 6](06-continue.md#continue-from-data-model-accelerator) before generic initialization.

Next, ask the agent to follow [explicit engagement entry](../../skills/omni-artifact-accelerator/references/engagement-entry.md): retain the original brief, prepare the execution responsibilities, explicitly read the generated entry and record `run-start` before the first artifact stage. The entry's sibling-folder rule belongs to this repository-only route. You do not need to hand-author its JSON records to use the guide.

The conversation-evidence policy records your actual design choice against the exact concepts. It is workflow evidence, not independently authenticated approval or permission to install dependencies or write native content. Existing stricter engagements never switch policies automatically.

## Send a first request

Replace the bracketed descriptions with your actual context; these are learning placeholders.

> Use the Omni Artifact Accelerator from [selected checkout or approved installed path]. Help [audience] investigate [decision] using [Omni instance and data reference]. Start with read-only data and my account's access. Keep work in [private engagement folder]. Follow A–F: understand the data and create a traceable story before design discovery, show three concrete visual concepts, and wait for my choice before detailed design and product coding. Reuse answers I already gave. Report missing tools or access; do not install dependencies or write to the tenant yet.

**Checkpoint:** the agent can name the source copy, private engagement, actual tool access, source expectation and next allowed stage. A missing connection is a stated setup gap, not permission to substitute sample data silently.
