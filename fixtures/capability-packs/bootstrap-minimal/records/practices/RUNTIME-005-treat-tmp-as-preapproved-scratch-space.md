---
id: RUNTIME-005
title: Treat /tmp as preapproved scratch space
domain: runtime
type: principle
status: active
version: 2
created: 2026-06-23
updated: 2026-06-23
tags: [runtime, approvals, sandbox, tmp, scratch-space, safety]
aliases:
  - RUNTIME-005
  - tmp is preapproved scratch space
  - no approval needed for ordinary /tmp file operations
  - temporary scratch files do not need explicit approval
related: [RUNTIME-001, RUNTIME-002, GOV-004, IMPL-003]
applies_when:
  - creating temporary files for command input, diagnostics, patches, comments, reports, or test artifacts
  - reading or writing files wholly inside /tmp, /private/tmp, or the current process temporary directory
  - using temporary body files for CLI commands
review_required: false
provenance: "Added from the user's explicit global rule on 2026-06-23: file operations within /tmp do not require separate explicit approval."
---

## Principle

Treat ordinary file operations wholly inside `/tmp`, `/private/tmp`, or the current process temporary directory as preapproved scratch-space activity. Do not ask for separate explicit approval merely to create, read, update, or use temporary files there.

## Rationale

Temporary scratch files are often the safest way to avoid shell quoting mistakes, preserve bounded command input, capture transient diagnostics, or stage review text before a durable write. Requiring approval for every `/tmp` scratch file creates ceremony without protecting canonical records, runtime configuration, or user-owned project files.

## Guidance

Agents may use `/tmp` for ordinary scratch-space work without an additional approval round when all of the following are true:

- every file path written or modified is wholly inside `/tmp`, `/private/tmp`, or the current process temporary directory;
- the operation is temporary support for the current task, such as body files, logs, diagnostics, generated previews, local test artifacts, or patch staging;
- the operation does not write secrets, private raw evidence, credentials, or user data that should not be stored even temporarily;
- the operation does not affect runtime/global configuration, canonical Agent Foundry records, Git state, remote services, or non-temporary project outputs.

This rule does not override the user's current filesystem sandbox or platform approval mechanism. If the environment requires an explicit tool approval to access `/tmp`, request that approval accurately; do not reinterpret this practice as technical capability.

## Watch Out For

Do not use `/tmp` approval to hide risky work. Broad destructive deletes, recursive cleanup outside a task-owned temporary directory, data migration, private data export, network downloads, runtime installs, GitHub mutations, permission changes, or writes that cross out of `/tmp` still follow the normal approval and risk gates.

Do not persist important project state only in `/tmp`. Durable decisions belong in canonical project records, issues, PRs, commits, or selected Vault entries.

## Example

Creating `/tmp/pr-comment.md` and passing it to `gh pr comment --body-file /tmp/pr-comment.md` does not need a separate approval just because the body file is in `/tmp`. Posting the comment may still require the normal GitHub mutation permission.

Creating `/tmp/agent-foundry-check/report.txt` for a validation summary is ordinary scratch work. Removing the task-owned directory afterward is acceptable if the command is narrowly scoped to that directory; deleting broad patterns such as `/tmp/*` is not covered by this rule.

## Activation

- Tier: task_router
- Phases: before_file_write, before_command_approval, verification
- Signals: tool approval is requested only because a command writes or reads a temporary file; body-file, diagnostic, report, or patch staging paths under `/tmp`
- Evidence: final report names any meaningful temporary artifact only when it affected verification, durable comments, or follow-up work

## Related Practices

- [[RUNTIME-001]]
- [[RUNTIME-002]]
- [[GOV-004]]
- [[IMPL-003]]
