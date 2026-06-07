---
id: COLLAB-008
title: Use GitHub Project as a lightweight agent scheduler
domain: agent-collaboration
type: pattern
status: active
version: 1
created: 2026-06-07
updated: 2026-06-07
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

Keep Epics as coordination containers. Do not put `needs:implementer` on an Epic merely because its child issues are ready. If an Epic-level concern requires code, tests, manual QA, data migration, or completion evidence from an Implementer, create a child issue for that executable work.

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

## Use This When

- Agents ask "what should I pick up next?"
- The user wants cross-agent interaction to happen through GitHub issues and comments.
- A workflow needs both a human Kanban view and a CLI-searchable agent inbox.

## Watch Out For

- Do not rely on Project status alone for agent pickup. Labels are easier for agents to query.
- Do not rely on labels alone for context. The latest durable comment must explain the next action.
- Do not let Epic coordination issues become fake implementation work. Split executable concerns into child issues.

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
