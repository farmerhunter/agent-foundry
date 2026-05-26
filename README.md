# Agent Foundry

Agent Capability Foundry: a personal system for turning real work experience into reusable, deployable agent capabilities across Codex, ChatGPT, Claude Code, Hermes, and similar environments.

## Core Idea

Agent Foundry discovers repeated work, distills reusable knowledge into canonical practices, packages reusable assets, publishes them through agent-specific adapters, and improves them with usage evidence.

Canonical practices live in `practices/`. Reusable assets live in `assets/`. Agent-specific skills and prompts under `adapters/` are downstream outputs.

```text
work session or external skill
  -> candidate lesson
  -> dedupe and review
  -> canonical practice
  -> human approval
  -> agent adapter
  -> usage evidence
  -> review and improvement
```

## Main Workflows

- Short commands: `docs/commands.md`
- End-user usage guide: `docs/usage.md`
- Harvest lessons from a session: `workflows/harvest-practices.md`
- Borrow external skills safely: `workflows/import-external-skills.md`
- Discover reusable assets: `workflows/discover-assets.md`
- Create or extend assets: `workflows/create-asset.md`
- Publish adapters: `workflows/publish-adapters.md`
- Install adapters: `workflows/install-adapters.md`
- Offline sync: `workflows/sync-offline.md`
- Periodic cleanup: `workflows/review-practices.md`
- Asset cleanup: `workflows/review-assets.md`

## Install On A Machine

```bash
python3 scripts/runtime_manifest.py init
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py plan
python3 scripts/install_foundry.py
python3 scripts/install_foundry.py --apply
```

The install script reads the machine-local `runtime/local/runtime_manifest.yaml`, syncs only enabled local targets, and uses managed runtime writes. The tracked template is `runtime/templates/runtime_manifest.template.yaml`; ChatGPT remains a manual import target.

## Human Review Gate

New/imported practices and discovered assets should be reviewed per item. After human approval, the agent should apply the approved item, promote it to `active`, update the relevant index, and publish relevant adapters automatically.

## Standards Followed

- `SKILL.md` skill folders for Codex-style adapters.
- `AGENTS.md` as repository-level agent instructions.
- `CLAUDE.md` and command files for Claude Code adapters.
- Full-fidelity `SKILL.md` folders for Codex and Hermes.
- ChatGPT instructions plus knowledge files.
- DeepSeek and similar model providers are not direct programming-agent adapters.

See `docs/standards-and-sources.md`.

## Initial Domains

- `meta`: maintaining Agent Foundry itself.
- `architecture`: boundaries, domain models, failure states, MVP scope.
- `implementation`: coding and refactoring rules.
- `testing`: validation and test design.
- `debugging`: diagnosis workflows.
- `product`: UX and product judgment.
- `agent-collaboration`: human-agent working patterns.

## Asset Registry

Reusable user-facing assets live under `assets/` and are indexed in `indexes/asset_index.yaml`. Assets include skills, subagents, and automations. They are governed by canonical practices but are not themselves canonical practices.
