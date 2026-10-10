---
id: COLLAB-001
title: Git autonomy follows workflow state
domain: agent-collaboration
type: playbook
status: active
version: 6
created: 2026-05-26
updated: 2026-08-31
tags: [github, issues, pull-requests, traceability, commits, workflow-state, approvals]
aliases:
  - COLLAB-001
  - issue code changes go through pull requests
  - bind issue work to PRs
  - commit autonomy follows workflow state
  - issue work may commit and open PRs
related: [COLLAB-002, COLLAB-003, COLLAB-004]
applies_when:
  - implementing code for a GitHub issue
  - making documentation or configuration changes for a GitHub issue
  - handing code work between local and remote agents
  - preparing an issue for review or closure
review_required: true
provenance: "Harvested from 2026AgentApp session involving issue #71/#73 traceability gaps. Revised on 2026-06-17 after tiny-ipa multi-agent dogfood showed agents need an explicit permission checkpoint and dispatch evidence checkpoint to avoid unnecessary approval prompts and false cross-thread handoff claims. Revised on 2026-07-06 after Agent Foundry AF15 showed role threads can block on ordinary GitHub tool approvals unless dispatch prompts distinguish runtime/tool approval from product Human gates."
---
## Principle

Authorization belongs to the current repository and Work, not to the tool or Skill. Once an issue/branch/PR task is authorized, verification, task commits, task-branch pushes and PR updates are normal delivery. Merge, closure and protected mutations require the authority for that particular transition.

## Rationale

Asking again for every already-delegated Git step interrupts useful work. Treating a general preference for automation as permission for every merge is equally wrong. Resolve authority once from current durable instructions, then carry it with the Work instead of reconstructing it from chat history or personal preferences.

This practice owns the permission boundary. COLLAB-009 owns the execution/handoff contract; COLLAB-003 owns verification before a delegated merge. Neither a Skill nor an agent can grant itself new authority.

## Guidance

### Resolve the next action

Read the latest user direction, applicable repository instructions, current issue/Epic contract and target branch. Refresh relevant state before a handoff, merge, closure or protected mutation; do not rescan the entire project for every command.

| Action | Proceed when | Otherwise |
| --- | --- | --- |
| Inspect, implement, verify, commit to task branch, push, open/update PR | Current Work authorizes that operation and its scope | Clarify the missing scope; do not invent it |
| Merge validated child PR into non-main Epic integration | Contract or user delegates acceptance/merge and required review is satisfied | Return to the named acceptance owner |
| Close an accepted child issue | Closure is delegated and its completion evidence is present | Keep it open at the correct handoff |
| Low-risk direct-to-main PR merge | Applicable repo policy and current Work explicitly permit this route, with no hold or remaining Human decision | Main merge is not inferred from non-main authority |
| Final main integration, Epic/stage/window closure, tag/release | The specific final transition is authorized | Present the remaining Human decision |
| Destructive action, force/reset, data migration, credential/security/privacy change, canonical promotion or installed-runtime change | An explicit applicable approval covers exact effects, targets and recovery, including any standing policy | Stop at that boundary |

An explicit user hold, do-not-merge instruction, requested manual review or unresolved blocking finding wins over a default auto-merge preference. If repo policy and Work instructions conflict, ask the responsible owner to correct the conflict durably. Lack of a written risk explanation is not permission to ignore a restriction. Conversely, do not manufacture a new Human gate when the existing approval already covers the action.

Keep runtime/tool permission separate from product authorization. A tool may require its own approval even for a delegated task; comply with that mechanism, but do not represent it as a new product decision or bypass it. Availability of a tool never grants authority to use it.

### Deliver inside the authorized boundary

1. Confirm the scope, current base/target, dependencies and intended handoff.
2. Use the workspace policy owned by COLLAB-011/COLLAB-013 and the Work contract. Do not create a branch per role or edit an integration checkout as a task workspace.
3. Make the scoped change, run relevant checks, commit and push the task branch, then open/update the PR.
4. Report the reviewed head, changed behavior, verification and residuals. Merge or close only as delegated; apply COLLAB-003 for merge verification.
5. Recheck authorization if the target, behavior or risk changes. Ordinary progress inside the same boundary does not require another approval phrase.

Exploratory work outside an authorized issue/branch/PR workflow does not inherit commit or merge permission. Show the diff before committing unless the user already authorized that workflow.

### Carry authority through handoff

State the authorized tool/GitHub operations, remaining Human gates, exact Work and next owner. GitHub issues/PRs/contracts retain durable meaning; a thread notification is not a replacement.

Report dispatch as performed only when the actual thread/subagent/automation tool accepted it. Otherwise name the portable prompt or durable fallback and say no live dispatch occurred. A sent message proves notification, not pickup, verification or completion. Delegate the session/automation-specific prompt to Role Automation Planner; do not load its entire workflow for ordinary issue work.

## Use This When

Use for permission decisions in an actual Issue/PR delivery, merge, handoff or closure. Merely mentioning GitHub in a technical question is not a trigger. Do not use this practice to authorize runtime deployment, canonical Harvest or a policy change.

## Watch Out For

- Do not turn ordinary commit/push/PR handling into repeated approval requests.
- Do not universalize one project's personal Vault merge policy.
- A low-risk merge grant does not grant parent Epic closure, release, installation or data cleanup.
- Preserve verification and requested independent review; structured self-review is not independent review.

## Example

A child fix has an authorized task branch and an Epic integration PR target. Complete the fix, checks, commit and PR without another prompt. Merge and close only if the current contract delegates both. If that contract says "do not merge", stop at review even when the repository usually auto-merges.

## Activation

- Tier: task_router
- Phases: pickup, delivery, handoff, merge, closure
- Signals: executing an authorized issue/PR task; resolving its next permission boundary
- Evidence: name applicable authority, current target and next permitted action; no routine comment-body hash required

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-003]]
- [[COLLAB-004]]
