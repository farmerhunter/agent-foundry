---
id: COLLAB-004
title: Sync repository before multi-agent issue work
domain: agent-collaboration
type: playbook
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [git, multi-agent, synchronization, github]
aliases:
  - pull before issue work
  - verify remote sync before coding
  - COLLAB-004
related: [COLLAB-001, COLLAB-002]
applies_when:
  - multiple agents work on the same repository
  - a VPS or remote machine may have pushed changes
  - an agent reports missing code changes
review_required: false
provenance: "Harvested from 2026AgentApp local/VPS synchronization investigation."
---

## Principle

Before starting or diagnosing GitHub issue work in a multi-agent repository, verify local and remote synchronization.

## Rationale

When local and remote agents push, squash, rebase, or reset at different times, a code change can exist in one history view but be invisible in another. Starting from stale state leads to duplicate work and misleading issue reports.

## Guidance

Fetch or pull before issue work, inspect branch status, and compare the relevant commits or PR merge commits. If an agent cannot see expected code, verify whether the code is absent, present under a squashed commit, or hidden by local branch divergence. Add an issue comment with the current code location and synchronization instructions when needed.

## Use This When

- The user says another machine or VPS just pushed.
- Another agent reports that code for an issue is missing.
- A PR was squash-merged after direct commits or force-like history changes.

## Watch Out For

- Do not assume missing commits mean missing code.
- Do not use destructive reset commands without explicit user confirmation.

## Example

If a VPS agent cannot see issue `#71` code, fetch remote, inspect current `origin/main`, identify whether the code is present in a squash merge, and comment on `#71` with the file paths and sync command.

## Related Practices

- [[COLLAB-001]]
- [[COLLAB-002]]
