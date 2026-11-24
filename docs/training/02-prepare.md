# 2. Prepare your first engagement

[Learning guide](README.md) · [Previous: understand](01-understand.md) · [Next: data and story](03-data-and-story.md)

**Outcome:** your agent can identify the selected package, available tools and private working folder before starting artifact work.

Start with the [three-step local quick start](../../README.md#quick-start). Once you have opened your workspace and sent the starter message, the assistant takes care of project setup.

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

## Select the work

Start with migration or net-new. For an existing artifact, tell the agent whether to preserve it or redesign it. An explicit request answers the question. Existing work resumes from its saved choice. [Workflow and examples](../../skills/omni-artifact-accelerator/references/work-intent.md)

## Connect to Omni

Start with your task. The agent checks for a matching tool on your host’s Omni MCP
connection and looks for an existing Omni CLI if needed. You can also say **“Use
my Omni CLI”** or **“Use my Omni MCP connection.”** If neither is available, you
can connect MCP, review a CLI installation offer, or continue offline. A CLI
offer shows the exact version, source and destination before you approve it.
[Connection setup](../../skills/omni-artifact-accelerator/references/omni-cli-setup.md)

## What the assistant sets up

Your workspace holds the accelerator and each private project side by side. The assistant creates the project folder once it knows what you want to build. For returning work, open the same workspace and ask to continue the existing project. Your inputs, decisions and deliverables stay together there. For a Data Model Accelerator continuation, give the assistant the existing handoff. [Continue an engagement](06-continue.md)

The assistant runs the local helpers using an existing approved Python 3 runtime. If it can read the checkout but cannot write to the workspace or run local commands, it can discuss the brief and tell you exactly what access it needs to proceed. Operators can inspect the [setup commands](../HOW_TO.md#1-create-a-private-engagement).

## Send a first request

> Read `Omni-Artifact-Accelerator/AGENTS.md` and use the accelerator in that folder. Build an Omni App that helps our operations leads investigate late deliveries.

**Checkpoint:** the assistant can tell you which checkout it is using, where your project will live, and what it needs from you next.
