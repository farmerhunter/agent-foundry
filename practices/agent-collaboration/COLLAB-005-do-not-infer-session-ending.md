---
id: COLLAB-005
title: Do not infer session ending
domain: agent-collaboration
type: anti-pattern
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [conversation, continuity, interruption, compaction]
aliases:
  - do not assume work is done
  - no premature wrap-up
  - COLLAB-005
related: [META-006, COLLAB-002]
applies_when:
  - a conversation is interrupted or compacted
  - a long task finishes one sub-step
  - the user has not explicitly ended the session
review_required: false
provenance: "Harvested from 2026AgentApp session where premature wrap-up was corrected by the user."
---

## Principle

Do not infer that the user is ending the session unless they explicitly say so.

## Rationale

Premature wrap-up interrupts ongoing work and can make the agent appear to ignore the newest request. In long engineering sessions, completing one task often means the next task should begin, not that the session is over.

## Guidance

After interruptions, context compaction, or completing a subtask, re-check the latest user request and continue from there. If there is no pending task, give a concise status only when useful. Avoid invented sign-off language or assumptions about the user's intent.

## Use This When

- The conversation resumes from compacted context.
- A background task completes.
- The user corrects or redirects the workflow.

## Watch Out For

- Do not say the equivalent of signing off unless the user requested it.
- Do not let an older task override a newer user message.

## Example

If a session resumes after compaction and the latest request is to inspect an issue, read the issue and continue rather than summarizing the session as complete.

## Related Practices

- [[META-006]]
- [[COLLAB-002]]
