# Runtime Adapter Framework And Trae Support

Status: proposed AF-7 design  
Updated: 2026-06-16

## Purpose

AF-7 makes Agent Foundry runtime adapters more explicit and adds first-class Trae CN support. The user experience goal is that Trae can use reviewed Agent Foundry practices and assets with minimal manual setup, while Core and the selected User Vault remain the source of truth.

This stage does not start memory-system work.

## Design Goals

- Make runtime setup simple: publish once, then refresh or repair with clear status.
- Prefer global runtime configuration when the runtime supports it.
- Preserve project-level contracts through `AGENTS.md`, `CLAUDE.md`, and project overlays when needed.
- Support multi-agent role behavior without requiring users to hand-maintain runtime-specific prompts.
- Keep canonical practices and assets compatible with future updates.
- Make stale, drifted, unmanaged, or partially installed runtime state visible before writes.

## Verified Trae CN Facts

Local experiments on 2026-06-15 verified:

- Trae CN uses `~/.trae-cn` as a global configuration root.
- Trae CN discovers global skills from `~/.trae-cn/skills`.
- A global Skill placed at `~/.trae-cn/skills/<skill-id>/SKILL.md` was loaded by Trae SOLO Agent and executed successfully.
- Trae CN also scans `.agents/skills` style skill locations, making a portable shared skill layer plausible.
- Trae CN imports project instruction files such as `AGENTS.md` and `CLAUDE.md` when that feature is enabled.
- Trae custom agent definitions appear to live in private application state, not a stable public file schema.

Follow-up validation on 2026-06-16 verified:

- Trae SOLO Agent can consume a planning-only Agent Foundry prompt and return a useful Orchestrator -> role-subagent flow without file edits when explicitly constrained.
- Trae recognizes Agent Foundry global Skill concepts such as `role-automation-planner` and `agent-collaboration`.
- Trae project `.trae/rules/*.md` files behave as always-applied workspace rules; separate role rule files expose all role contracts to all agents and create authority-mixing risk.
- `.trae/subagents/*.md` is the better project-specific overlay candidate for isolated role prompts selected per task.

Implication: Agent Foundry should publish Trae support primarily as generated global Skills plus optional project overlays, and should not write Trae private application state until Trae exposes a supported import/export contract.

## User Experience Model

The normal Trae flow should be:

1. User installs or updates Agent Foundry Core and selects a User Vault.
2. Agent Foundry publishes generated adapters from active canonical practices and assets.
3. Agent Foundry installs or refreshes Trae global Skills under `~/.trae-cn/skills` after a dry-run shows planned writes.
4. In a project, Trae reads project contracts from `AGENTS.md` and `CLAUDE.md`.
5. The user works through Trae SOLO Agent or a Trae custom agent that invokes the installed Agent Foundry Skills.
6. Agent Foundry status reports whether canonical records, generated adapters, installed Trae files, and project overlays are fresh.

The user should not need to copy large prompts into every Trae project. Project-level setup should be limited to contracts that are genuinely project-specific.

## Architecture

Agent Foundry should treat adapters as runtime projections with four layers:

```text
canonical practice or asset
  -> portable adapter intermediate representation
  -> runtime-specific generated adapter
  -> machine-local installed runtime copy
```

The portable adapter intermediate representation should describe:

- source canonical ids and versions;
- target capability type, such as instruction, skill, command, role prompt, helper script, or project overlay;
- activation semantics, such as global, project, manual import, or runtime-managed;
- required human review gates;
- privacy and local-write constraints;
- generated file ownership markers;
- compatibility and migration metadata.

Runtime publishers then map that representation into Codex, Claude Code, Hermes, ChatGPT/manual import, Trae, or future targets.

## Trae Adapter Shape

Trae should have three output scopes:

- **Global native scope**: generated Trae Skills under `~/.trae-cn/skills`. This is the preferred path for reusable Agent Foundry behavior.
- **Portable shared scope**: generated `.agents/skills` output when a skill should remain usable across runtimes that understand the shared skill convention.
- **Project overlay scope**: generated `.trae/` or project contract snippets only for project-specific behavior that cannot safely live globally.

Trae global Skills should be thin wrappers around canonical Agent Foundry content. They can include Trae-specific activation text, examples, and command wiring, but they should not fork canonical practice logic.

## Multi-Agent Role Mapping

Trae currently works best as a coordinator runtime rather than as a fully file-backed multi-agent registry. Agent Foundry should map roles this way:

| Agent Foundry role | Trae mapping |
| --- | --- |
| Architect | Trae Skill or role instruction invoked by SOLO Agent for planning, contracts, issue shaping, and human-decision gates. |
| Implementer | Trae Skill or task prompt for scoped implementation with validation expectations. |
| Reviewer | Trae Skill for bug/risk-first review and acceptance-gate checking. |
| Verifier | Trae Skill for local command, UI, and runtime freshness verification. |
| Harvester | Trae Skill for proposing candidates, never directly activating canonical records. |

If Trae later exposes a stable custom-agent file schema or CLI import path, Agent Foundry can add a custom-agent publisher. Until then, generated Skills are the safer integration point.

For complex multi-role work, prefer a SOLO Agent plan that dispatches isolated role prompts from `.trae/subagents` when a project overlay is explicitly approved. Do not generate multiple default `.trae/rules/<role>.md` files. Use `.trae/rules` only for a single dispatcher or project-wide contract reference when ambient always-applied wording is safe and intentional.

## Asset Compatibility

Existing runtime-neutral multi-agent assets remain useful if they avoid Codex-only assumptions. The Trae adapter should add only the runtime-specific layer needed to activate those assets:

- Trae-facing `SKILL.md` wrappers;
- launcher instructions that call existing helper scripts;
- status and repair guidance that names Trae install paths;
- role-specific prompt packaging for Trae's interaction model.
- anti-summary-document instructions so Trae does not create summary files unless requested or required by acceptance criteria.

Trae-specific assets are justified only when Trae has unique behavior that cannot be represented by the portable adapter layer, such as Skill discovery, UI activation wording, or future custom-agent import formats.

## Canonical Update Compatibility

Generated Trae files must stay compatible with future canonical asset updates:

- Every generated file should include a managed marker, source canonical ids, source version or hash, generator version, and target runtime.
- Status should distinguish fresh, stale, drifted, unmanaged, missing, blocked, and unknown states.
- Refresh should support dry-run, diff, and apply.
- Local edits to managed files should be detected before overwrite.
- Adapter generation should tolerate additive canonical metadata changes and fail closed on ambiguous or malformed metadata.

Canonical content remains authoritative. Runtime copies are replaceable projections.

## Sync And Long-Running Use

Trae support must handle long-running agent usage where Core, Vault, generated output, or runtime installs changed elsewhere:

- report whether the local repo is behind remote progress when that evidence is available;
- report whether generated adapters are stale relative to canonical records;
- report whether installed Trae files are stale relative to generated output;
- separate project overlay freshness from global Skill freshness;
- give repair actions in user terms: pull, publish adapters, dry-run install, apply install, or reopen Trae.

This is part of capability-system hardening, not memory-system work.

## Human Decision Points

AF-7 requires human decisions for:

- approving writes to `~/.trae-cn/skills` on the current machine;
- approving any project-specific `.trae/` output;
- accepting unmanaged-file overwrite or local-edit conflict resolution;
- approving any future attempt to write Trae private application state;
- approving activation of new or changed canonical practices/assets before publishing;
- deciding whether a Trae-specific asset is warranted instead of a portable wrapper.

## Risks

- Trae's public extension surface may change without a stable schema.
- Trae custom-agent state may remain private and unsafe to automate.
- Global Skills may not cover every desired multi-agent UX.
- `.agents/skills` portability is promising but still needs cross-runtime compatibility checks.
- Runtime hot reload behavior may require user-visible restart or refresh guidance.
- Generated wrappers can drift from canonical assets if source metadata and receipt checks are weak.

## AF-7 Acceptance Model

AF-7 is complete when:

- the adapter framework has a documented portable intermediate model;
- Trae is represented as a target runtime in profiles, docs, validation, and status;
- a generated Trae global Skill can be dry-run, installed, detected, refreshed, and repaired;
- project overlays are optional and clearly separated from global setup;
- existing multi-agent assets can be projected into Trae without duplicating canonical logic;
- runtime status distinguishes canonical, generated, installed, project, unmanaged, stale, and conflict states;
- the old capability-system hardening Epic is renumbered and held for AF-8.
