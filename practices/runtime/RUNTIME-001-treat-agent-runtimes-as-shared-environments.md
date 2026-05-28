---
id: RUNTIME-001
title: Treat agent runtimes as shared, user-owned environments
domain: runtime
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [runtime, adapters, deployment, ownership, safety]
aliases:
  - do not overwrite unmanaged runtime files
  - runtime directories are shared environments
  - publish through managed blocks and markers
  - RUNTIME-001
related: [META-001, META-002, META-006]
applies_when:
  - publishing Agent Foundry adapters into local agent runtimes
  - installing generated skills or commands
  - updating shared instruction files
  - syncing cross-agent practices into Codex, Claude Code, Hermes, or ChatGPT
review_required: false
provenance: "Harvested from the runtime sync conflict review on 2026-05-26, where direct writes to ~/.claude/CLAUDE.md and unmarked Codex/Hermes skill directories exposed ownership ambiguity."
---

## Principle

Treat agent runtime directories and shared configuration files as user-owned, tool-shared environments. Publish Agent Foundry content through managed blocks, namespaced files, ownership markers, backups, dry-runs, and human-approved adoption; never overwrite unmanaged runtime files by default.

## Rationale

Agent runtimes are not private output directories. Files such as `~/.claude/CLAUDE.md` may be edited by the user, the native agent, Agent Foundry, and other automation. Skill directories under `~/.codex/skills` or `~/.hermes/skills` look isolated, but a same-name directory can still belong to another system. Without explicit ownership boundaries, a publish step can silently erase or corrupt existing agent behavior.

## Guidance

Keep canonical practice entries and generated adapters inside the Agent Foundry repository. When installing into a real runtime:

- Use managed include blocks or imports for central shared files.
- Store generated runtime content in namespaced files or directories.
- Mark generated skill directories with `.agent-foundry-managed`.
- Refuse to overwrite unmarked files or directories by default.
- Run dry-runs before writes and show destination paths.
- Back up shared files before modifying a managed block.
- Require explicit human approval before adopting an existing unmanaged runtime path.

## Watch Out For

Do not treat "adapter output exists" as permission to overwrite runtime state. Adapter generation describes the desired package shape; the sync layer still owns merge safety, collision detection, backup, and adoption rules.

## Example

For Claude Code, write generated instructions to `~/.claude/agent-foundry/CLAUDE.md` and update only a bounded Agent Foundry import block in `~/.claude/CLAUDE.md`. For Codex or Hermes, update a skill directory only when it contains `.agent-foundry-managed`, unless the user explicitly approves adopting that directory.

## Related Practices

- [[META-001]]
- [[META-002]]
- [[META-006]]
