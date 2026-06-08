---
id: COLLAB-010
title: Ready queues use dependency gates
domain: agent-collaboration
type: playbook
status: active
version: 2
created: 2026-06-07
updated: 2026-06-08
tags: [agent-collaboration, queue, dependencies, github-project, handoff]
aliases:
  - COLLAB-010
  - Ready queue dependency gates
  - Ready does not mean immediately codable
related: [COLLAB-007, COLLAB-008, COLLAB-009, COLLAB-011]
applies_when:
  - an Architect wants to hand off a dependent sequence of issues at once
  - an Implementer inbox contains multiple Ready issues from the same Epic
  - issue dependencies should reduce human relay rather than force repeated handoff
provenance: "Harvested from tiny-ipa M3 queue design on 2026-06-07, where #14-#17 were moved to Ready together but gated by explicit `Depends on` contracts."
---

## Principle

`Ready + needs:implementer` can represent an ordered Implementer queue. It does not mean every issue can be coded immediately.

## Rationale

If the Architect only releases one issue at a time, the user remains a message broker between agents. If the Architect releases every issue without dependency gates, the Implementer may start work too early. The scalable middle ground is to make a coherent batch visible while using explicit `Depends on` conditions as the start gate.

Small issues should not automatically create small handoffs. When a set of issues belongs to the same Epic-level objective and has clear dependency gates, batching the handoff reduces coordination overhead and lets the Implementer proceed without returning to the Architect after every child issue.

## Guidance

Architects may move a dependent issue sequence to `Ready` and label it `needs:implementer` when:

- every issue has an execution contract;
- dependencies are explicit and checkable;
- dependent issues share the same integration branch unless an exception is documented;
- the Implementer can continue the queue without another Architect handoff;
- the batch has a natural checkpoint where Architect or Reviewer can review the combined output.

Prefer an Epic or sub-Epic batch handoff when the work is low-risk, tightly related, and the dependencies are clear. Do not split handoff into one Architect interaction per child issue merely because the work is represented as multiple issues.

Implementers should:

1. Query the Implementer inbox.
2. Read all ready issues in the queue.
3. Sort them by each issue's `Depends on` contract.
4. Start only issues whose dependencies are satisfied.
5. Leave waiting issues in `Ready`.
6. Use `Pickup confirmed` only when actually starting work.

For a waiting issue, optionally comment:

```markdown
## Queued by Implementer

Dependency not satisfied yet.
Waiting for #... to merge into `epic/...`.
```

## Use This When

- A sequence of issues is already planned and should not require repeated Architect release.
- Dependencies are linear or otherwise easy to check from issue/PR state.
- The Implementer can continue after prior PRs merge into the agreed base branch.
- A batch of small related issues should be executed before a meaningful Architect or Reviewer checkpoint.

## Watch Out For

- Do not create a working branch or PR for a dependent issue before its `Depends on` condition is true.
- Do not use Ready queues when dependencies are vague, circular, or need a user decision.
- Do not assume GitHub Project order is the dependency graph. The execution contract is the gate.
- Do not force a handoff or review checkpoint after every child issue when the Epic can be reviewed as a coherent batch.

## Example

In tiny-ipa M3, #14, #15, #16, and #17 were all moved to `Ready + needs:implementer`. #15 still waited for #14 to merge into the Epic branch, #16 waited for #14 and #15, and #17 waited for #16. This let DeepSeek manage the queue without another Architect handoff after each issue.

## Activation

- Tier: workflow_embedded
- Phases: issue_queue_planning, pickup, before_edit
- Signals: multiple Ready issues; `needs:implementer` on dependent issues; `Depends on` contract; user wants less manual relay
- Evidence: report queue order and which dependencies are satisfied before starting work

## Related Practices

- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-009]]
- [[COLLAB-011]]
