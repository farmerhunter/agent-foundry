---
id: GOV-004
title: Preserve maintainability and runtime capability
domain: governance
type: principle
status: active
version: 1
created: 2026-05-28
updated: 2026-05-28
tags: [governance, maintainability, runtime, degradation, safety]
aliases:
  - GOV-004
  - do not degrade native agent capability
  - preserve long-term runtime capability
related: [GOV-002, RUNTIME-001, META-007, META-009]
applies_when:
  - adding capability-management mechanisms, adapters, runtime files, scripts, or automations
  - deploying Agent Foundry content into Codex, Claude Code, Hermes, ChatGPT, or another agent runtime
  - changing rules that affect native memory, skills, project instructions, commands, or self-improvement
  - designing a system enhancement that must keep working across agents and machines
review_required: false
provenance: "Added from the user's explicit guardrail on 2026-05-28: Agent Foundry must preserve minimal maintainability and avoid degrading long-running agent runtimes."
---

## Principle

Preserve maintainability and runtime capability. A capability system must enhance agent runtimes without weakening their native skills, memory, instructions, self-improvement, or user-owned configuration.

## Rationale

Governance systems can become harmful when they add too much structure, overwrite runtime behavior, or force every agent into one uniform model. Long-term value depends on staying lightweight, reversible, and compatible with each runtime's native strengths.

## Guidance

Before adding or changing a capability mechanism, verify:

- it does not overwrite unmanaged runtime content;
- it does not disable native memory, skill creation, project instructions, or self-improvement;
- it has a clear maintenance path and validation check;
- it can fail safely or be rolled back;
- it avoids manual synchronization burden;
- it improves future agent behavior enough to justify its complexity.

Prefer managed blocks, namespaced files, dry-runs, adapter quality checks, and explicit local deployment manifests over direct runtime takeover.

## Watch Out For

Do not optimize one agent's adapter in a way that degrades another agent's native mode of operation. Do not make a rule global unless it can survive compaction, handoff, and multi-machine use without requiring hidden memory.

## Activation

- Tier: always_preflight
- Phases: planning, before_runtime_write, before_adapter_publish, review
- Signals: writing runtime files; changing agent skills, memory, project instructions, commands, hooks, or self-improvement behavior; introducing capability-management machinery
- Evidence: final report states how native runtime capability, rollback, and maintainability were preserved

## Related Practices

- [[GOV-002]]
- [[RUNTIME-001]]
- [[META-007]]
- [[META-009]]
