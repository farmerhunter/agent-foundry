---
name: agent-foundry
description: Use in Trae CN when working with Agent Foundry practices, assets, adapters, GitHub issue workflows, multi-agent roles, runtime refresh, or capability lifecycle checks.
---

# Agent Foundry

Target runtime: Trae CN global Skill.

Agent Foundry turns reviewed practices and assets into runtime-ready agent capabilities. In Trae, prefer this global Skill path before project-specific configuration. Project `AGENTS.md` and `CLAUDE.md` remain the project contract when Trae imports them.

## Compact Preflight

Before substantial changes, check:

- Duplicate or derived truth source? Apply GOV-001.
- New machinery, layer, script, workflow, or integration? Apply GOV-002 and ARCH-001.
- Transient memory or chat summary used as fact? Apply GOV-003.
- Writing into user-owned runtime or agent configuration? Apply GOV-004 and RUNTIME-001.
- Syncing, publishing, or installing adapters? Apply RUNTIME-003.
- Producing rendered or converted output? Apply TEST-001.

## Commands

- harvest practices
- 做一次 harvest practice
- 提炼实践
- 沉淀经验
- discover assets
- 发现可打包资产
- import skill
- 导入这个 skill
- publish practices
- 发布 practices
- review practices
- 检查 skill rot
- review assets
- 检查 asset rot
- refresh practices and assets
- 刷新practices和assets

## Role Routing

- Architect: planning, architecture boundaries, Execution Contracts, and human-decision gates.
- Implementer: scoped code or docs changes with verification.
- Reviewer: bug/risk-first review against acceptance criteria.
- Verifier: status, command, install, and runtime freshness checks.
- Harvester: candidate extraction only; do not activate canonical records without review.

## Runtime Rules

- Treat canonical practices and assets in the selected User Vault as the source of truth.
- Treat Trae files under `~/.trae-cn/skills` as downstream runtime copies.
- Use global Trae Skills for reusable behavior.
- Use project overlays only when a project needs additional local contract text.
- Do not write Trae private application state or custom-agent database records.
- Before runtime writes, use dry-run output and resolve unmanaged or drifted files.
- Do not start memory-system work unless the user explicitly authorizes that separate stage.
