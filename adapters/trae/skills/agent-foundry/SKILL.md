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

## Commands

- harvest practices
- 做一次 harvest practice
- 提炼实践
- 沉淀经验
- discover assets
- 发现可打包资产
- discover capability packs
- evaluate capability pack
- preview capability pack deployment
- apply reviewed capability pack
- review capability pack lifecycle
- preview capability pack transfer
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

## Capability Pack Workflow

- Use natural-language Skill requests as the primary interface: discover or evaluate capability packs, preview deployment, apply a reviewed pack, review lifecycle transition, or preview transfer.
- Discovery and evaluation read `workflows/discover-capability-packs.md` and produce evidence or false-positive review only.
- Deployment preview runs the capability-pack planning workflow before any selected Vault write.
- Reviewed apply requires accepted review/approval evidence and keeps generated/runtime follow-up separate.
- Lifecycle review uses dry-run reports first; activation, exportability, split, merge, deprecation, disable, retire, and runtime writes keep their review or human gates.
- Transfer preview uses privacy-safe export/import validation and blocks local-private, runtime, executable, or memory-system material.
- Treat raw scripts for capability packs as implementation details or advanced/debug commands, not the primary user surface.

## Role Routing

- Architect: planning, architecture boundaries, Execution Contracts, and human-decision gates.
- Implementer: scoped code or docs changes with verification.
- Reviewer: bug/risk-first review against acceptance criteria.
- Verifier: status, command, install, and runtime freshness checks.
- Harvester: candidate extraction only; do not activate canonical records without review.

## Trae Multi-Agent Mode

- Use SOLO Agent for planning-first multi-role orchestration when the task needs Architect -> Implementer -> Reviewer separation.
- Prefer `.trae/subagents/*.md` for approved project-specific role prompts because they are selected per task.
- Do not use separate `.trae/rules/architect.md`, `.trae/rules/implementor.md`, and `.trae/rules/reviewer.md` as the default role model; Trae treats project rules as always-applied workspace rules, so all roles can see all role contracts.
- Use a single dispatcher or project contract reference in `.trae/rules` only when ambient project-wide wording is explicitly intended.
- Keep Single Chat role dispatch as the fallback when SOLO/SubAgents are unavailable, too costly, or unreliable.
- Keep durable coordination in GitHub issues, labels, comments, PRs, and explicit requested project artifacts.
- Do not create summary `.md`, `.txt`, or `.docx` artifacts unless the user asks or the issue acceptance criteria requires a document deliverable.

## Runtime Rules

- Treat canonical practices and assets in the selected User Vault as the source of truth.
- Treat Trae files under `~/.trae-cn/skills` as downstream runtime copies.
- Use global Trae Skills for reusable behavior.
- Use project overlays only when a project needs additional local contract text.
- Do not write Trae private application state or custom-agent database records.
- Before runtime writes, use dry-run output and resolve unmanaged or drifted files.
- For ordinary scratch file operations wholly inside `/tmp`, `/private/tmp`, or the current process temporary directory, apply RUNTIME-005 and do not request separate approval for that reason alone. This does not cover broad destructive deletes, secrets/private data export, runtime/global config writes, network/downloads, GitHub mutations, data migration, permission changes, or paths outside temporary scratch space.
- Do not start memory-system work unless the user explicitly authorizes that separate stage.
