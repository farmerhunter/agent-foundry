---
id: COLLAB-013
title: Manual edit safety protocol
domain: agent-collaboration
type: playbook
status: proposed
version: 1
created: 2026-06-07
updated: 2026-06-07
tags: [agent-collaboration, manual-edit, git, vscode, safety]
aliases:
  - COLLAB-013
  - safe edit
  - manual edit safety
related: [COLLAB-004, COLLAB-007, COLLAB-008, COLLAB-009, COLLAB-011]
applies_when:
  - the user wants to hand-edit files in a repository also used by agents
  - the user asks whether it is safe to edit a document or code file
  - local VSCode or another editor may create uncommitted changes during agent work
review_required: true
provenance: "Proposed from tiny-ipa workflow discussion on 2026-06-07. The protocol was designed but has not yet been exercised enough to promote to active."
---

## Principle

User hand-editing should remain easy, but agents should provide a safety check before edits collide with active agent work.

## Rationale

Vibe coding often includes casual human edits in VSCode while agents manage branches, PRs, and issue queues. Without a lightweight protocol, local edits can disappear from view during branch switches, conflict with an active Implementer issue, or remain uncommitted while another agent assumes the workspace is clean.

The goal is not to block manual writing. The goal is to choose the right safety mode before or immediately after the user starts editing.

## Guidance

When the user asks for safe manual editing, inspect:

- current branch;
- dirty worktree state;
- whether the target files overlap the active Epic or `needs:implementer` issue scope;
- related open PRs or integration branches;
- whether the edit changes implementation behavior, acceptance criteria, or only prose.

Recommend one of three modes:

```text
Scratch: direct local notes or draft edits; safe only until branch/pull/merge operations need a clean tree.
Safe Edit: create a user branch from latest main, then commit/PR the manual edit when ready.
Coordinated Edit: for active Epic scope, comment on the relevant Epic or child issue, use the correct base branch, and PR into the active integration branch.
```

If the target overlaps an active issue owned by another agent, do not silently edit the same files. Either coordinate through the issue or wait for the active PR to merge.

## Use This When

- The user says they want to "just write a few lines" in VSCode.
- The repository has active agent branches or an Implementer queue.
- A document or code file may be related to current Epic work.

## Watch Out For

- Do not force every scratch note into a PR before the user knows whether it is worth keeping.
- Do not switch branches, pull, or merge with uncommitted manual edits unless they are intentionally stashed or committed.
- Do not treat unrelated docs and active-scope code the same way.

## Example

In tiny-ipa, editing the anecdote document was low-risk because active M3 work targeted content/audio/backend/frontend paths. Editing `content/core_100_words.json` would have overlapped #14 and required coordinated mode.

## Activation

- Tier: review_only
- Phases: before_edit, before_branch_switch, before_pull
- Signals: user asks to hand-edit; VSCode edits during multi-agent work; dirty worktree; active Epic overlap
- Evidence: report branch, dirty state, overlap assessment, chosen mode, and any issue/PR coordination needed

## Related Practices

- [[COLLAB-004]]
- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-009]]
- [[COLLAB-011]]
