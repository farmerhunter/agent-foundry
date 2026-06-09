---
id: COLLAB-008
title: Use GitHub Project as a lightweight agent scheduler
domain: agent-collaboration
type: pattern
status: active
version: 3
created: 2026-06-07
updated: 2026-06-09
tags: [agent-collaboration, github-project, scheduler, labels, epics]
aliases:
  - COLLAB-008
  - GitHub Project as agent scheduler
  - labels as agent inbox
related: [COLLAB-002, COLLAB-004, COLLAB-007, COLLAB-009, COLLAB-010, COLLAB-012]
applies_when:
  - using GitHub Project with multiple agents
  - agents need to discover their own next work
  - issue state, review state, and PR state must remain durable across sessions
provenance: "Harvested from tiny-ipa workflow design on 2026-06-07, where Project status, labels, Epics, comments, PRs, and CI formed a minimal agent scheduler."
---

## Principle

Use GitHub's existing durable objects as a lightweight scheduler before inventing a custom agent-management system.

## Rationale

Two or more agents need shared state. Chat context and human clipboard relay do not scale: they are transient, incomplete, and invisible to other agents. A GitHub Project, with issues, labels, comments, PRs, and CI, already provides the minimum scheduler loop for many small projects.

The key is to distinguish human-readable state from agent-readable routing. Project status is good for a board. Labels are better as queryable inboxes. Comments carry the message body. PRs carry the deliverable and review. CI carries automatic validation.

## Guidance

Map collaboration surfaces explicitly:

```text
GitHub issue = task object
Epic issue = cross-issue coordination memory
Child issue = executable work and acceptance unit
Project status = human-visible state
needs:* label = agent inbox / routing key
issue or PR comment = durable message body
PR = deliverable and review surface
CI = automated validation gate
```

This is a lightweight scheduler substrate, not a full coordinator. It does not maintain an independent Manager/Coordinator entity, persistent session ownership model, or automatic role assignment. Keep the simple mode robust by making the session, role, and task binding explicit whenever work moves between states.

Use these meanings:

```text
task = issue, PR, batch checkpoint, or Epic acceptance unit
role = Architect, Implementer, Reviewer, Harvester, user, or CI responsibility
session = the current agent conversation or runtime instance that may perform one or more roles
owner role = the role currently responsible for the next action on the task
review target = who or what must validate the task before Done
```

Roles are responsibilities, not identities. A single session may perform multiple roles over time, and the same human account may drive several roles. When a session changes role for a task, say so explicitly in the issue comment, PR comment, or final report.

Keep Epics as coordination containers. Do not put `needs:implementer` on an Epic merely because its child issues are ready. If an Epic-level concern requires code, tests, manual QA, data migration, or completion evidence from an Implementer, create a child issue for that executable work.

Keep issue type semantically honest. Use an Epic for coordination across child issues, dependencies, or exit criteria. If the remaining work has collapsed into one concrete deliverable, classify it as a Task even when the Architect performs it directly.

Use exactly one primary next-action label on an active issue unless the work is genuinely blocked:

```text
needs:architect
needs:implementer
needs:user
needs:ci
needs:merge
blocked
```

When changing handoff ownership, change both the label and the durable comment. The label routes the next agent; the comment explains what to do.

`needs:*` labels route the next role. They do not automatically require a different session or a new conversation. If the current session can satisfy the next role, state that explicitly, for example: `Next action: current Architect session will perform structured self-review`.

Keep scheduler state coherent across surfaces:

- `Ready` means available for pickup, not completed.
- `In Progress` means an agent is actively executing or holding the work.
- `Review` means the producing agent has posted completion evidence and the next owner must validate or decide.
- `Done` means the work has been accepted and closed, or the Epic exit criteria are satisfied.

Do not leave one status surface saying `Ready` while another says `Done`. If a repository uses both GitHub's built-in Project `Status` and a custom roadmap status field, update both to represent the same lifecycle phase.

When a task enters `Review`, its durable comment or contract should name the review target: current session structured self-review, user review, separate Reviewer agent, CI/automation, or batch/Epic checkpoint.

## Use This When

- Agents ask "what should I pick up next?"
- The user wants cross-agent interaction to happen through GitHub issues and comments.
- A workflow needs both a human Kanban view and a CLI-searchable agent inbox.

## Watch Out For

- Do not rely on Project status alone for agent pickup. Labels are easier for agents to query.
- Do not rely on labels alone for context. The latest durable comment must explain the next action.
- Do not let Epic coordination issues become fake implementation work. Split executable concerns into child issues.
- Do not keep a completed or closed issue in `Ready`; move it to `Review` for validation or `Done` after acceptance.
- Do not keep a single-deliverable policy or implementation issue labeled as an Epic merely because it came from roadmap planning.
- Do not confuse role with session identity. `needs:architect` or `needs:reviewer` routes the next role; it does not always require a different agent or conversation.
- Do not leave `Review` without a review target. The scheduler cannot be checked if no one can tell whether review means current-session self-review, user review, separate reviewer, CI, or batch checkpoint.

## Example

In tiny-ipa, `Backlog -> Ready -> In progress -> In Review -> Done` remained the human board, while `needs:implementer` and `needs:architect` became the agent inboxes. An Implementer could search labels, read issue contracts, and pick up work without the user copying a message between agent windows.

## Activation

- Tier: workflow_embedded
- Phases: planning, pickup, review, verification
- Signals: GitHub Project board; issue labels for role routing; multi-agent handoff; Epic/child issue hierarchy
- Evidence: report which Project/status, labels, issue comments, and PRs form the scheduler state

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-004]]
- [[COLLAB-007]]
- [[COLLAB-009]]
- [[COLLAB-010]]
- [[COLLAB-012]]
