---
id: COLLAB-013
title: Manual edit safety protocol
domain: agent-collaboration
type: playbook
status: active
version: 5
created: 2026-06-07
updated: 2026-08-27
tags: [agent-collaboration, manual-edit, git, vscode, safety, worktree, quarantine, cleanup, adaptive-isolation, single-writer]
aliases:
  - COLLAB-013
  - safe edit
  - manual edit safety
  - dirty worktree hides remote updates
  - local branch behind with dirty file
related: [COLLAB-004, COLLAB-005, COLLAB-007, COLLAB-008, COLLAB-009, COLLAB-011, RUNTIME-005]
applies_when:
  - the user wants to hand-edit files in a repository also used by agents
  - the user asks whether it is safe to edit a document or code file
  - local VSCode or another editor may create uncommitted changes during agent work
review_required: true
provenance: "Proposed from tiny-ipa workflow discussion on 2026-06-07. Activated after Agent Foundry v1.1 README release correction on 2026-07-07, where a local branch behind origin with a dirty tracked README caused the user to see an old file after the remote correction had already landed. Extended after AF18 worktree cleanup and Architect rehydration evidence on 2026-08-10. v4 harvests the qualified execution-state lifecycle and cleanup evidence from Agent Foundry #524, #562, and #563. v5 adds the approved Adaptive Isolation allocation and standing reclamation policy from Agent Foundry #568."
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
- staged changes;
- whether the branch is ahead of or behind its upstream;
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

For cleanup, enumerate exact worktree and temporary-directory targets first. Check whether each target is bound to a durable role thread, whether it contains uncommitted or audit evidence, and whether the exact branch/commit can recreate it. Prefer moving uncertain targets to a quarantine directory with a manifest. Removal requires either the adopted standing reclamation policy or a separate explicit target decision, plus confirmation that no role or evidence depends on it.

When a repository explicitly adopts bounded collaboration, use `adaptive_isolation` as the forward-only default workspace policy for new Work. Allocate by facts, not role count:

- read-only inspection uses the current checkout with no branch or worktree;
- a serial low-risk edit may use a task branch in a clean current checkout when no active Epic overlap exists;
- other writable, concurrent, or Epic child Work uses one task branch and one isolated worktree;
- live, privacy/security, destructive, external-effect, `main`, or release Work uses an isolated worktree plus only the evidence and Human gates justified by that boundary.

One logical Work has at most one writable branch/worktree owner. The Epic integration checkout is coordination/integration/readback-only while child Work is active, and Reviewer/Tester checkouts are ephemeral when they are needed. Reuse an exact existing Work binding idempotently; conflicting ownership holds that Work without blocking unrelated Work. Outside an adopted bounded-collaboration policy or explicit Work contract, do not impose these topology defaults on ordinary repositories.

In the adopted isolated mode, ephemeral execution state is reclaimable only after a durable receipt. Prefer `HOLD` as a committed recoverable branch or PR. Classify uncommitted-only, divergent, ambiguous, or owner-blocked state as `QUARANTINE`, recording exact path/ref, owner, reason, recovery anchor, and review trigger.

Use the lifecycle `PLANNED -> ALLOCATED -> ACTIVE -> REVIEW -> MERGED_RECLAIMABLE -> RECLAIMED`. Onboarding may establish a standing reclamation policy for exact system-created task state only. Automatic reclamation requires exact Work/root/branch ownership, accepted merge/readback or another durable recovery ref, no open PR or live owner/process, a clean tree or explicitly accepted disposable cache, non-force exact-target removal, and post-removal authority/absence readback. Historical, dirty, divergent, integration/release, open-PR, unknown-owner, or ambiguous state remains Human-gated. Adoption never authorizes retroactive cleanup.

Whenever worktree cleanup is performed in any mode, treat promotion and cleanup as separate transactions and verification steps. A standing policy may supply cleanup authority only for exact system-created task state that satisfies every listed precondition; all other state needs a separate approval. Before cleanup, preserve rescue material and an exact preimage sufficient for recovery, inspect tracked, untracked, and ignored-file state, resolve ownership, confirm there is no active or `HOLD` PR, and bind every target to an exact manifest and recovery anchor. A clean tree, containment, or tree equality is evidence, not deletion authority. Cache-only exceptions must be explicitly accepted; cache classes are classification/count evidence rather than byte-hash authority.

Execute cleanup reversibly when practical and fail closed per manifest row: one failed precondition holds that target without broadening, retrying, or reconstructing it another way. Destructive removal outside the standing policy still requires Human approval; every removal requires post-readback. Do not use wildcard cleanup, force removal, reset, clean, stash, inferred disposal, automatic prune, retry, or alternate reconstruction as fallback.

When a user reports that a file still looks old after a PR, merge, or release correction, check for this common state before making another content fix:

```text
local branch behind upstream + dirty/staged tracked file = local file may mask the remote fix
```

Compare the file against `origin/<branch>` and inspect both unstaged and staged diffs. If the local file already matches the remote target, a fast-forward pull may be enough. If the local file differs, preserve the user's edit by explaining the overlap and choosing stash, commit, branch, or coordinated PR before pulling or switching branches. Do not use destructive reset just to make the local view match the remote.

## Use This When

- The user says they want to "just write a few lines" in VSCode.
- The repository has active agent branches or an Implementer queue.
- A document or code file may be related to current Epic work.
- A user says a recently merged file still appears old locally.
- A checkout is behind upstream while a tracked file is dirty or staged.
- A Work explicitly adopts isolated multi-agent/worktree execution mode and needs recoverable promotion, HOLD, quarantine, or cleanup handling.

## Watch Out For

- Do not force every scratch note into a PR before the user knows whether it is worth keeping.
- Do not switch branches, pull, or merge with uncommitted manual edits unless they are intentionally stashed or committed.
- Do not treat unrelated docs and active-scope code the same way.
- Do not assume the remote correction failed until comparing the local file to the remote branch.
- Do not clean a dirty file with `reset --hard` unless the user explicitly authorizes discarding local changes.
- Do not apply Adaptive Isolation topology defaults to repositories that have not adopted bounded collaboration or to historical state retroactively.
- Do not allocate permanent worktrees by role or add a daemon, workspace manager, database, or periodic full-repository scan.
- Do not infer cleanup authority from containment, matching trees, clean status, or cache classification.

## Example

In tiny-ipa, editing the anecdote document was low-risk because active M3 work targeted content/audio/backend/frontend paths. Editing `content/core_100_words.json` would have overlapped #14 and required coordinated mode.

In Agent Foundry v1.1, the README correction had landed on `origin/main`, but the local checkout was eight commits behind and carried a staged tracked `README.md`. The right fix was to compare the file to `origin/main`, confirm the remote had the intended content, then fast-forward the local branch without discarding unrelated user work.

## Activation

- Tier: task_router
- Phases: before_edit, before_branch_switch, before_pull
- Signals: user asks to hand-edit; VSCode edits during multi-agent work; dirty worktree; staged tracked file; local branch behind upstream; active Epic overlap; recently merged file appears stale locally; an explicit isolated multi-agent/worktree execution-mode contract; worktree promotion, quarantine, or cleanup
- Evidence: report branch, upstream ahead/behind state, dirty, staged, untracked, and relevant ignored-file state, remote-file comparison when relevant, overlap assessment, chosen mode, and any issue/PR coordination needed; for isolated-mode cleanup, record durable receipt, owner, exact manifest/preimage, rescue and recovery anchor, approval, per-row result, and post-readback

## Related Practices

- [[COLLAB-004]]
- [[COLLAB-005]]
- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-009]]
- [[COLLAB-011]]
- [[RUNTIME-005]]
