---
id: COLLAB-006
title: Verify task completion against the original task list, not implementation side effects
domain: agent-collaboration
type: anti-pattern
status: active
version: 1
created: 2026-06-03
updated: 2026-06-03
tags: [agent-collaboration, task-management, verification, completion, cross-agent]
aliases:
  - COLLAB-006
  - check original task list before declaring done
  - implementation momentum doesn't equal completion
  - side effects are not completion criteria
related: [COLLAB-002, META-006, GOV-003]
applies_when:
  - receiving a structured task list from another agent or user
  - working through a multi-item plan that includes both code and design/documentation tasks
  - nearing the end of a phase and preparing to report completion
provenance: "Harvested from token-panic Phase 5 execution (2026-06-03), where design/documentation tasks (structured provider review, ProviderConfigVM) were silently skipped because 'tests pass + build succeeds' gave a false completion signal. The missing tasks had no red/green indicator in the test runner."
---

## Principle

When executing a task list received from another agent (or user), verify completion against the original list item by item. Do not use implementation side effects — tests passing, build succeeding, app launching — as a proxy for completion of tasks that produce no executable output.

## Rationale

A task list often mixes code tasks with design, documentation, and review tasks. Code tasks produce executable artifacts (tests, builds, running apps) that give immediate green/red feedback. Design and documentation tasks produce no such signal.

When implementation momentum is high, the agent naturally gravitates toward the tasks that produce visible, satisfying feedback. Tasks without executable output get deprioritized, then forgotten. The agent then declares "done" based on the signals it can see — all tests pass, the build succeeds — without re-reading the original task list.

This is a specific failure mode of cross-agent handoff: the receiving agent substitutes observable implementation signals for explicit completion verification.

## Guidance

1. Keep the original task list visible and unchanged throughout execution. Do not rewrite or paraphrase it into a personal todo format that may drop items.
2. Before declaring any phase complete, re-read the original task list from the source document. Tick each item explicitly.
3. For items that produce no executable output (design documents, structured reviews, ViewModel interfaces), verify existence independently: check that the file exists, that it contains the content described, that it matches the spec's format requirements.
4. If any item is found incomplete, pause the "done" declaration, complete the item, then resume the cross-check from the top.
5. Do not batch-mark items as complete in a single action. Each item must be individually verified.

## Use This When

- You receive a numbered task list from another agent or the user.
- The task list includes items of different types (code, design, documentation, review).
- You are working through a multi-phase plan where phases build on each other.
- You feel ready to declare a phase complete and move to the next.

## Watch Out For

- Do not use "all tests pass" as a substitute for design review tasks. A structured provider review table has no test.
- Do not use "the app runs" as a substitute for documentation updates. An updated implementation plan section has no runtime behavior.
- Do not paraphrase the task list into a personal format that drops detail. Keep the original as the completion checklist.
- Do not confuse the user's approval of a deliverable with verification that all spec items are done. The user may not notice a missing structured review table.

## Example

In token-panic Phase 5, Codex provided a 7-item task list:

- Task 1: Structured 9-question provider review → **skipped** (no test, no build output)
- Task 2: ProviderConfigVM design → **skipped** (ConfigPanel was refactored ad-hoc without ViewModel contract)
- Tasks 3-6: All completed (had tests, builds, or visual output)

The agent declared "Phase 5 complete" based on 154 passing tests and a running app with three dashboard sections. But two tasks were silent gaps that would surface the next time someone tried to add a third provider and found no structured review table or config ViewModel to guide them.

The correct completion check would have been: re-read Codex's 7-item list → find Tasks 1 and 2 not done → complete them → re-verify → declare done.

## Related Practices

- [[COLLAB-002]] — issue review comments include completion and verification; similar "don't skip the verification step" pattern at the GitHub issue level
- [[META-006]] — memory is evidence, not source of truth; similarly, "tests pass" is evidence of implementation health, not evidence of task completion
- [[GOV-003]] — treat transient context as evidence; the feeling of "I think I'm done" is transient evidence, not durable verification
