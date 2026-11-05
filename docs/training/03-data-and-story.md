# 3. Go from data to a story

[Learning guide](README.md) · [Previous: prepare](02-prepare.md) · [Next: choose](04-choose.md)

**Outcome:** you know what the data supports before committing to a product design.

## The A-F sequence

This is the text alternative to the [agent-flow diagram](assets/agent-flow.svg).

| Stage | Agent responsibilities | What you should see before moving on |
| --- | --- | --- |
| A — Verify data and access | Orchestrator, analyst and BI engineer establish source availability and the intended user's access | Named source, access evidence and explicit gaps |
| B — Analyze and qualify queries | Analyst and BI engineer examine grain, dates, completeness, definitions and useful comparisons | Supported questions, reviewed queries and independent numerical expectations |
| C — Create the analytical story | Storyteller and analyst connect claims to evidence and define update behavior | A reusable narrative that responds honestly to new data and changed filters |
| D — Discover the experience | Product owner brings in design, branding and relevant specialists | Sourced requirements covering audience, outcome, quality, interaction and constraints |
| E — Compare and choose | Designers propose three distinct viable visual concepts; you select one; specialists resolve its detailed design | The actual choice tied to its option set, with behavior and design decisions ready for implementation |
| F — Build and refine | Target engineer/builder implements; security, UI/UX, product owner and independent QA review each iteration | A current candidate with findings, fixes and clear evidence limits |

Publication has its own authorization and verification after candidate preparation. The package checks its managed routes; those helpers do not control arbitrary commands or API calls outside them. Host enforcement must be qualified separately.

Migration evidence enters through the translator and source specialist. Missing backend definitions go to Data Model Accelerator or the model owner; returned candidates are reconciled and affected access/query evidence is checked again before dependent work resumes.

## A — Can the right person access the right data?

The agent should establish the Omni instance, source and user identity relevant to the task. A list of available models is discovery evidence. Querying as an organization administrator is not proof that the eventual audience has access.

For a prototype you can explicitly choose your own account. The handoff should then preserve team access as a separate rollout check. If the requested data is unavailable, the agent should identify the exact missing source or permission rather than designing around invented results.

## B — What can we responsibly learn?

Suppose your question is: “Where are service delays increasing, and what should an operations lead inspect next?” The agent should investigate:

- What one row represents, which identifiers connect records, and which populations are included.
- Which time period is covered and whether records are complete enough for comparison.
- How delay, volume and completion are defined, including nulls and exclusions.
- Which segment, trend and entity-detail questions the available fields support.
- Which independent totals or samples can detect a wrong query or binding.

An average alone may hide volume differences or missing records. A difference between groups does not establish its cause. The output should distinguish supported findings, hypotheses and questions that need additional data.

## C — Make the story reusable

A useful narrative describes a decision path: notice a change, compare the relevant groups, inspect supporting detail, and decide what to investigate. It is not just a paragraph written around today's numbers.

For each important claim, retain the supporting query, population, filters, time period and limitations. Define what happens if the evidence changes: refresh the statement, replace it with a different supported finding, or suppress it when coverage is insufficient. Exact values and evidence should remain available beside expressive visuals.

This stage also supplies freshness facts for the later interview. Source update cadence, query-cache behavior and the age of a displayed result are different things; they should not be collapsed into one “live” label.

**Checkpoint:** ask the agent to explain one finding in plain language, show where it came from, and name something the data cannot establish. If that explanation is unclear, resolve it before moving to design.
