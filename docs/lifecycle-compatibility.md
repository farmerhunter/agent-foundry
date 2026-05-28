# End-to-End Lifecycle Compatibility

This document defines how the Agent Foundry loop works across Codex, Claude Code, Hermes, and ChatGPT.

It is a design contract, not a user prompt. Daily commands remain in `docs/commands.md` and `docs/usage.md`.

## Goal

Agent Foundry must preserve one closed loop:

```text
harvest / discover / import
  -> human approval
  -> canonical records
  -> adapter publish
  -> runtime install or manual import
  -> task-time activation
  -> usage and missed-activation evidence
  -> review and lifecycle adjustment
```

This loop must work across heterogeneous agents without pretending they have identical runtime capabilities.

## Design Constraints

- Canonical records stay in the repo. Runtime files are downstream adapters.
- Human approval is required before activating new or materially changed practices or assets.
- After approval, adapter publishing should be automatic when the runtime supports it.
- ChatGPT is manual-import by default; do not design local automation that ChatGPT cannot run.
- Native agent capabilities must not be degraded. Agent Foundry should augment Codex, Claude Code, Hermes, and ChatGPT rather than replacing their memory, skills, project instructions, hooks, or self-improvement paths.
- Activation is soft by default. Only runtimes with hook support can add hard pre-tool checks, and those checks must remain optional and reversible.

## Agent Capability Matrix

| Capability | Codex | Claude Code | Hermes | ChatGPT |
|---|---|---|---|---|
| Local repo editing | yes | yes | yes | no direct local runtime |
| Skill/procedure packaging | `SKILL.md` folders | `CLAUDE.md` plus slash commands | `SKILL.md` folders and native skills | Project instructions plus files |
| Progressive loading | skills and references | imports, commands, referenced files | skills and references | project files / knowledge |
| Runtime install | managed copy to `~/.codex/skills` | managed block plus files under `~/.claude` | managed copy to `~/.hermes/skills` | manual import |
| Local scripts | yes | yes | yes | no |
| Hard pre-tool guard | no generic Foundry hook assumed | possible with Claude Code hooks | no generic Foundry hook assumed | no |
| Evidence recording | local script | local script or optional hook | local script | manual/exported summary |
| Best fit | full local loop | full local loop plus optional hook experiments | full local loop while preserving native learning | soft consumption and manual sync |

## Lifecycle Stages

### 1. Harvest, Discover, Import

Purpose: identify reusable practices, assets, or external material.

| Agent | Adaptation |
|---|---|
| Codex | Use `practice-harvester` skill with references. Can edit canonical repo and run scripts. |
| Claude Code | Use `CLAUDE.md` routing and slash commands. Can edit canonical repo and run scripts. |
| Hermes | Use managed `practice-harvester` skill. Native Hermes memory or generated skills are candidate inputs, not replacements for canonical records. |
| ChatGPT | Use project instructions and knowledge files to produce candidates. A local agent or human must apply repo changes. |

Invariant: candidates are not active records until the user approves them.

### 2. Human Approval

Approval is chat-level and per meaningful item. After approval, local-capable agents continue the chain automatically. ChatGPT should output a precise change plan for a local agent or human to apply.

The agent should show title, decision, reason, canonical files affected, and adapters affected after approval.

### 3. Canonical Record Update

Canonical updates include `practices/`, `assets/`, `indexes/`, `schemas/`, `workflows/`, and `usage/usage-aggregate.yaml`.

Codex, Claude Code, and Hermes can edit the repo directly. ChatGPT cannot be assumed to write the repo or run checks, so it should not claim completion unless a local agent or human has applied the changes.

### 4. Adapter Publish

Publishing converts active canonical practices and assets into agent-specific downstream files.

| Agent | Publish path |
|---|---|
| Codex | `adapters/codex/skills/*` then managed copy to `~/.codex/skills`. |
| Claude Code | `adapters/claude-code/CLAUDE.md` and commands, then managed block/files under `~/.claude`. |
| Hermes | `adapters/hermes/skills/*` then managed copy to `~/.hermes/skills`. |
| ChatGPT | `adapters/chatgpt/custom-instructions.md` and `adapters/chatgpt/knowledge/*`; user manually imports into a Project or Custom GPT. |

Publish checks include `scripts/check_consistency.py`, `scripts/check_adapter_quality.py`, and `scripts/check_activation.py`.

### 5. Runtime Install Or Manual Import

Local runtimes are installed through the machine-local runtime manifest:

```text
repo adapters
  -> runtime/local/runtime_manifest.yaml
  -> scripts/install_foundry.py --apply
  -> managed runtime files
```

ChatGPT remains manual:

```text
repo adapters/chatgpt/
  -> user imports instructions and knowledge files
  -> ChatGPT Project consumes them
```

Do not treat ChatGPT as in-sync merely because repo adapters changed.

### 6. Task-Time Activation

Activation is how a practice is remembered during real work.

Activation should use tiers, not a new practice domain:

- `always_preflight`: very small cross-project kernel, always visible in direct programming adapters.
- `task_router`: activated by explicit task type, such as architecture design or GitHub issue work.
- `workflow_embedded`: activated inside a workflow, such as publish adapters or review assets.
- `review_only`: activated during review/check workflows.
- `reference_only`: available for search or manual lookup.

Only `always_preflight` belongs in compact adapter text. It should stay short enough to survive long sessions and compaction.

Initial preflight kernel:

```text
Before substantial changes, check:
- Duplicate or derived truth source? Apply GOV-001.
- New machinery, layer, script, workflow, or integration? Apply GOV-002 and ARCH-001.
- Transient memory or chat summary used as fact? Apply GOV-003.
- Writing into user-owned runtime or agent configuration? Apply GOV-004 and RUNTIME-001.
- Syncing, publishing, or installing adapters? Apply RUNTIME-003.
- Producing rendered or converted output? Apply TEST-001.
```

This is not a rule engine. It is a compact trigger index. If a line matches the task, the agent should read or apply the full practice.

### 7. Evidence Recording

Evidence has two forms:

- usage evidence: an active asset or practice was materially used;
- missed-activation evidence: a practice should likely have triggered but did not.

Codex, Claude Code, and Hermes can write evidence with `scripts/record_asset_usage.py --evidence-type applied|missed`.

ChatGPT should summarize evidence for later import:

```text
Evidence to record:
- practice: GOV-002
- trigger: avoided adding manual generated index
- outcome: useful
- note: chose schema/check update instead
```

Do not require user approval for ordinary non-sensitive usage evidence. Do require human review before using evidence to change lifecycle state, activation tier, or adapter behavior.

### 8. Review Practices And Assets

Review closes the loop. It should inspect duplicates, weak activation signals, missed activations, asset overlap, adapter drift, and runtime drift.

Review may recommend merging or revising a practice, changing activation tier, promoting or demoting a preflight rule, updating asset boundaries, or changing asset lifecycle state. Human approval is required before lifecycle or activation-tier changes.

## Closed-Loop Checks

Current static checks:

- `check_consistency.py`
- `check_adapter_quality.py`
- `sync_status.py`
- `check_activation.py`

`check_activation.py` should start narrow:

- active practices with `## Activation` use a valid tier;
- all `always_preflight` practices appear in Codex, Claude Code, Hermes, and ChatGPT adapter text;
- each adapter mentions the IDs that its profile includes;
- no inactive practice is injected into preflight.

Runtime checks are heterogeneous:

- Codex/Hermes: soft instruction plus local evidence scripts.
- Claude Code: soft instruction; optional hooks can enforce selected pre-tool checks.
- ChatGPT: soft instruction plus manual evidence export.

Do not claim runtime enforcement uniformly across all agents.

## Rollout Plan

### Phase 1: Design And Pilot

- Write this lifecycle design.
- Define activation tiers.
- Add `## Activation` to a small pilot set: GOV-001, GOV-002, GOV-003, GOV-004, ARCH-001, RUNTIME-001, RUNTIME-003, TEST-001.
- Add compact preflight kernel to adapters.
- Add `check_activation.py` for `always_preflight` only.

### Phase 2: Evidence Loop

- Record practice usage evidence for material applications.
- Add missed-activation evidence format.
- Include activation findings in `review practices`.

### Phase 3: Broader Coverage

- Add Activation sections to more practices only when they need better triggering.
- Move practices between tiers based on evidence.
- Keep preflight small; do not add every practice to always-visible adapters.

### Phase 4: Optional Runtime Enforcement

- Explore Claude Code hooks only for narrow, high-confidence checks.
- Keep hooks reversible and disabled by default unless the user explicitly installs them.
- Do not attempt equivalent hard enforcement in ChatGPT.

## Non-Goals

- A cross-agent rule engine.
- Full automatic enforcement in ChatGPT.
- Putting every practice into global preflight.
- Replacing native memory, skills, project instructions, or self-improvement.
- Treating runtime adapters as canonical truth.

## Sources

- Claude Code memory and `CLAUDE.md`: https://docs.claude.com/en/docs/claude-code/memory
- Claude Code slash commands: https://docs.claude.com/en/docs/claude-code/slash-commands
- Claude Code hooks: https://docs.claude.com/en/docs/claude-code/hooks
- ChatGPT Projects: https://help.openai.com/en/articles/10169521-chatgpt-projects
- OpenAI memory FAQ: https://help.openai.com/en/articles/8590148-memory-faq
