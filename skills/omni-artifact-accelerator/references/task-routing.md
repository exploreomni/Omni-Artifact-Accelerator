# Scoped specialist work

Use this route for new tracked work while retaining the existing project,
design-intent, DMA handoff and native release contracts. It reserves local work;
the host still invokes the worker. No model selection, billing estimates, native
validation or external mutations are added.

## Assignment and execution

1. Inspect/reuse active workers. Keep the configured model and effort and use the
   smallest team, at most two specialists by default. Review disciplines can
   share one independent worker. Capacity limits are not permission to downgrade.
2. Use `analyst_project.py packet-bindings --project PROJECT --role ROLE --input
   PATH` (repeat `--input`) to obtain current selected hashes without another file.
   The helper includes relevant design-intent inputs. Keep the selected evidence
   within the existing 256 KiB limit and review disclosure before sending it.
3. Prepare an assignment JSON with `schema_version: 1`, stable `task_id`,
   `domain_id`, `stage`, `role`, nonempty `scope_ids`, bounded `objective`, exact
   relative `outputs`, checkable `acceptance`, exact `input_bindings`,
   `dependencies` (named hashes represented in selected inputs), `unknowns`, and
   `authoring_mode` (`provisional` or `reviewed_candidate`). Stages include
   `discovery`, `design`, `implementation`, `semantic`, `dashboard`, `app`,
   `validation`, `packaging`, `migration_plan`; role must fit the stage.
   Assignment metadata has a separate 64 KiB ceiling; split overlarge tasks
   without silently dropping required scope.
4. Build `packet --project PROJECT --role ROLE --input PATH --assignment
   ASSIGNMENT.json --output PROJECT/tasks/TASK.json`. This is an immutable local
   index; provide only selected evidence plus the assignment to the host worker.
   Candidate paths cannot overwrite selected inputs, coordinator state, source
   evidence, task packets, contracts or evidence directories. Draft contract
   candidates elsewhere; the coordinator adopts reviewed versions explicitly.
5. `claim-work --project PROJECT --request REQUEST.json` accepts `attempt_id`,
   project-relative `packet`, optional `execution_mode` (`specialist` or `inline`).
   `dispatch` is a reservation, `already_active` points to existing work, and
   `reuse` returns unchanged completed files. Concurrent duplicate claims cannot
   reserve a second worker. Do not infer interruption from missing host status.
6. Call `prepare-dispatch` with `attempt_id` immediately before host invocation.
   Then invoke the host and `record-dispatch` with `attempt_id`,
   `host_run_reference`, `observed_model`, `observed_effort`, `requested_model`,
   `requested_effort`, `execution_mode`, `fallback_reason`. Unobservable values
   stay null; inline execution needs its reason. Receipts are host-reported, not
   proof of isolation or model identity.
7. `checkpoint-work` accepts `attempt_id`, `status` (`interrupted` or
   `outputs_recorded`), `reason`, and `outputs`. Completion needs all assigned
   files; interrupted work can retain partial output. Confirm a worker stopped
   before releasing its reservation. Restart with a new attempt ID and the same
   logical task ID. Revised inputs need a new packet; unrelated task pins survive.

Unknown context stays visible and requested provisional artifacts remain allowed.
The local assignment does not sandbox the worker. Sources and imported DMA
evidence remain read-only. Existing legacy packets still work but are explicitly
untracked and cannot masquerade as tracked execution; rebuild a bounded assigned
packet only when opting into this route, without rewriting old evidence.

## Consolidated review

`review-work --project PROJECT --request REQUEST.json` uses `attempt_id` plus:

| `action` | Additional fields / result |
| --- | --- |
| `start` | Optional `changes`, `dependency_state` (`known`/`unknown`); returns candidate hash and required review IDs |
| `record` | `result`: `review_id`, `candidate_sha256`, `verdict` (`pass`/`changes`/`unknown`), `findings`, `reviewer_reference`, `execution_mode` |
| `status` | Pending reviews or one consolidated decision |
| `correct` | `correction_attempt_id`; reserves that attempt before edits, preserving the original checkpoint |
| `revise` | After correction preflight/invocation/receipt and edits, pins new files and the actual correction builder |

Each finding has `id`, `severity` (`blocking`/`warning`), `message`, nonempty
`evidence` and `affected_ids`, and an actionable `acceptance`. Give reviewers
original requirements and independent expected results, not only author summaries.
The helper selects model, logic, semantic, security and experience disciplines
from declared changes, stage and executable paths. Unknown dependencies expand
review and request evidence; the selector is not a universal semantic diff engine.
Do not turn each discipline into a separate agent by default.

Wait for all applicable reviews on the same candidate, then issue one correction.
Reserve it with `correct`, run the actual worker, `revise`, collect the verification
pass, and checkpoint the updated candidate. Further failures become explicit
questions/follow-up scope. Never reset correction limits silently. Changed files
invalidate earlier reviews; inline/self-review and unknown evidence cannot be
independent approval. `reviews_complete` is not native validation or authority
to publish, merge or accept a migration.

## User-visible progress

`work-status --project PROJECT --html TASK_PROGRESS.html` creates an offline
snapshot and links it from existing `START_HERE.md`. It lists domain, task, stage,
role, reservation/execution state, candidate qualification, review, next action,
recorded file links and open questions. Refresh explicitly; it is not a live
heartbeat. Native QA and publication remain in their existing evidence lanes.
The local reservation lock uses POSIX `flock`; qualify a native Windows runner
separately instead of claiming equivalent coordination there.

`scripts/task_routing.py` must stay byte-identical to DMA's shared contract.
No third-party runtime dependencies are added by this route.
