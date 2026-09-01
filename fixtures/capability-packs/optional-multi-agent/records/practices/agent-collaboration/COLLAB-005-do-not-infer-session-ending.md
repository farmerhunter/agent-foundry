---
id: COLLAB-005
title: Do not infer session ending
domain: agent-collaboration
type: anti-pattern
status: active
version: 3
created: 2026-05-26
updated: 2026-08-10
tags: [conversation, continuity, interruption, compaction, rehydration, worktree, binding, cleanup]
aliases:
  - COLLAB-005
  - do not assume work is done
  - no premature wrap-up
related: [META-006, COLLAB-002, COLLAB-013, RUNTIME-005]
applies_when:
  - a conversation is interrupted or compacted
  - a long task finishes one sub-step
  - the user has not explicitly ended the session
review_required: false
provenance: "Harvested from 2026AgentApp session where premature wrap-up was corrected by the user; extended from AF18 worktree cleanup and Architect rehydration evidence on 2026-08-10."
---

## Principle

Do not infer that the user is ending the session unless they explicitly say so. After interruption, idleness, or context compaction, rehydrate from durable sources before making risky workflow transitions.

## Rationale

Premature wrap-up interrupts ongoing work and can make the agent appear to ignore the newest request. In long engineering sessions, completing one task often means the next task should begin, not that the session is over.

## Guidance

After interruptions, context compaction, idleness, or completing a subtask, re-check the latest user request and continue from there. If there is no pending task, give a concise status only when useful. Avoid invented sign-off language or assumptions about the user's intent.

Before applying or removing `needs:*` labels, merging a PR, closing an issue, accepting work as done, syncing runtime state, writing private config, or switching roles inside a session, perform a compact rehydration checkpoint. Read the durable sources that govern the action: repo instructions, relevant Skill or asset guidance, issue or PR body/comments, Execution Contract, labels, Project/Roadmap state when available, branch/PR state, and explicit latest user instruction. Then state the current role, task, allowed actions, forbidden actions, next owner, and residual risks before acting.

A thread is durable role context; a worktree is replaceable execution state. Before removing, reusing, or rebinding a worktree, verify the path, repository, branch, exact HEAD, dirty state, active or durable thread binding, and audit value. If the binding is uncertain, preserve the directory in a quarantine location and record a manifest instead of deleting it. If a directory is missing, recreate the exact branch/commit or perform an explicit durable handoff before continuing.

## Use This When

- The conversation resumes from compacted context.
- A long-running or idle session resumes before a workflow state transition.
- A session changes roles, such as Architect to Reviewer or Harvester.
- A background task completes.
- The user corrects or redirects the workflow.

## Watch Out For

- Do not say the equivalent of signing off unless the user requested it.
- Do not let an older task override a newer user message.
- Do not rely on remembered Skill, AGENTS, issue, or label state when the next step changes durable workflow state.
- Do not treat a `needs:*` label as a passive marker; it is a request to route work and must have transition evidence.
- Do not infer that an old branch name means no thread is using its worktree.

## Example

If a session resumes after compaction and the latest request is to inspect an issue, read the issue and continue rather than summarizing the session as complete.

If an idle Architect session is about to remove `needs:reviewer`, first reread the issue, PR, reviewer evidence, and collaboration Skill; then record whether the reviewer dispatch or fallback evidence exists before changing labels.

## Related Practices

- [[META-006]]
- [[COLLAB-002]]
- [[COLLAB-013]]
- [[RUNTIME-005]]
