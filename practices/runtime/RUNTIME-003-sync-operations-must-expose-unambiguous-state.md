---
id: RUNTIME-003
title: Sync operations must expose unambiguous state
domain: runtime
type: principle
status: active
version: 1
created: 2026-05-27
updated: 2026-05-27
tags: [runtime, sync, state, git, safety, visibility]
aliases:
  - report exact state after every sync
  - sync without ambiguity
  - unambiguous final report
  - status commands are read-only
related: [RUNTIME-001, RUNTIME-002, COLLAB-004]
applies_when:
  - syncing Agent Foundry with remote repositories
  - refreshing local runtimes after canonical changes
  - pushing or pulling across machines
  - reporting completion after multi-step sync workflows
  - implementing sync status, review, compare, or report commands
review_required: false
provenance: "Harvested from the refresh workflow redesign on 2026-05-27, where git push failures and ambiguous local-vs-remote state led to uncertainty about whether adapters and runtimes were actually in sync."
---

## Principle

Sync operations must expose unambiguous state. After every sync, report the exact commit hash, unpushed commits, runtime updates applied, and next actions required. Never leave the user guessing whether canonical files, generated adapters, and local runtimes are aligned.

## Rationale

Safety barriers like managed blocks and dry-runs prevent accidents, but they do not tell users whether their systems are in sync. A successful git pull does not mean adapters were regenerated. A successful adapter generation does not mean runtimes were updated. A successful runtime update does not mean changes were pushed to remote. Without explicit state reporting, users must manually infer alignment from scattered tool output, which leads to skipped steps, duplicate work, and silent drift.

## Guidance

After any sync or refresh workflow, produce an unambiguous Final Report that answers these questions explicitly:

1. **What is the canonical state?** Report the exact commit hash after any commit.
2. **What is the remote state?** Report whether local commits were pushed successfully, or if unpushed commits remain.
3. **What adapters changed?** List which adapters were regenerated and why.
4. **What runtime updates occurred?** List which runtime files were created, updated, or skipped.
5. **What should happen next?** State the exact next action the user must take, if any.

Use a structured, human-readable format. Do not rely on the user reading verbose command output. Do not report "done" when there are pending pushes or unreviewed changes.

When network issues prevent push, report the failure explicitly and preserve the knowledge that unpushed commits exist. Do not silently defer or hide the issue.

Status, report, check, review, and compare commands are read-only by default. If local state is missing, report that it has not been initialized and suggest the explicit initialization command. Do not create or mutate local state just to display status.

## Watch Out For

Do not assume that because a command succeeded, the overall sync is complete. A refresh workflow may involve git pull, conditional adapter regeneration, installation to runtimes, and git commit+push. Each step can succeed independently while the overall system remains out of sync. The Final Report is the only source of truth for the aggregate state.

Do not omit the commit hash. Relative terms like "latest" or "just now" lose meaning across interruptions, compaction, or multi-machine work.

Do not let a supposedly read-only status operation write machine-local manifests, sync state, usage logs, or adoption records. Read-only reporting must be safe to run repeatedly before install, after install, and on an unfamiliar machine.

## Example

After a refresh workflow, report:

```
Final Report
- Commit: abc1234
- Push: 1 commit pushed to origin/main
- Adapters regenerated: claude-code, codex, hermes (canonical practices changed)
- Runtime updates: claude-code managed block updated; codex skills copied; hermes skills copied
- Next action: none
```

If push failed:

```
Final Report
- Commit: abc1234
- Push: FAILED (network timeout). 1 commit remains unpushed.
- Adapters regenerated: claude-code, codex, hermes
- Runtime updates: claude-code managed block updated; codex skills copied; hermes skills copied
- Next action: retry push with `git push origin main` when network recovers
```
