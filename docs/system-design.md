# Agent Foundry System Design

## Purpose

Agent Foundry, short for Agent Capability Foundry, is a personal system for turning real work experience into reusable, deployable agent capabilities across environments such as Codex, ChatGPT, Claude Code, Hermes, and similar tools.

The goal is not to maintain a pile of prompts. The goal is to run a closed loop:

```text
discover repeated work and reusable lessons
  -> distill canonical practices
  -> package reusable assets
  -> publish heterogeneous adapters
  -> record usage evidence
  -> aggregate safe usage statistics
  -> review and improve
```

See docs/lifecycle-compatibility.md for how this loop adapts across Codex, Claude Code, Hermes, and ChatGPT from harvest through activation, evidence, and review.

## Core Principle

Canonical practices are the source of truth. Agent-specific skills, prompts, commands, and instructions are adapters.

```text
project session experience
  -> candidate lesson
  -> canonical practice entry
  -> reviewed active rule
  -> agent adapters
```

Repeated work can also become user-facing reusable assets:

```text
work history
  -> asset candidate
  -> human approval
  -> active skill / subagent / automation
  -> agent adapters
  -> local usage evidence
  -> shared usage aggregate
  -> review and improvement
```

Adapters can be regenerated, rewritten, or discarded. Canonical practice entries should preserve the durable content, rationale, lifecycle state, and relationships.

Assets are not canonical practices. They are tools governed by canonical practices and tracked in `assets/` plus `indexes/asset_index.yaml`.

Memory, session summaries, and activity logs are evidence sources. They can suggest candidates, but they are not the source of truth for durable practices, assets, workflows, or adapters.

Native agent learning should remain useful. For agents such as Hermes that can remember, create skills, or improve local skills, Agent Foundry should not disable those native capabilities. Native outputs are upstream candidate inputs when they should become durable or cross-agent.

`docs/memory-system-handoff-dump.md` is preserved evidence for a proposed future memory and knowledge subsystem. It records research, corrections, open questions, and possible future architecture, but it does not make `memory/`, `knowledge/`, `research_memos/`, or project-memory directories current Agent Foundry capabilities.

`docs/roadmap.md` coordinates the readiness work needed before deciding whether that memory system should become an Agent Foundry extension, a sibling repository, a monorepo package, a forked experiment, or a user-vault convention.

## Practice Domains

`meta` is reserved for Agent Foundry capability governance: how practices, assets, adapters, imports, harvesting, routing, publishing, and review work inside this system.

`governance` is for cross-project operating constraints that agents should apply in any repository or task. These include protecting source of truth, avoiding unnecessary machinery, treating transient context as evidence, and preserving long-term runtime capability.

Do not put a practice under `meta` only because it is abstract or broadly useful. A practice belongs in `meta` only when it governs the Agent Foundry capability lifecycle itself. If it constrains general project work, durable records, maintainability, or runtime capability across projects, use `governance` or another domain that matches the work surface.

## Repository Layers

```text
Foundry Core:
  workflows/     Strict procedures agents should follow
  schemas/       Canonical entry shape and lifecycle rules
  scripts/       Deterministic tooling
  templates/     Record templates

Foundry Vault:
  practices/     Canonical practice source of truth
  assets/        Registry of reusable skills, subagents, and automations
  indexes/       Searchable registry for dedupe and routing
  usage/         Shared usage aggregates plus gitignored local raw evidence
  docs/          Long-form explanations for humans and future agents
  imports/       Staging area for external skills and ideas

Downstream:
  adapters/      Outputs for specific agent environments
  runtime/       Machine-local deployment manifests and portable templates
```

Core and Vault currently live in one repository for maintainability. They are separate logical units so agents can distinguish the canonical destination from the current project they are harvesting from.

Machine-local locator:

```text
~/.agent-foundry/config.yaml
```

This file records `repo_root`, `core_root`, `vault_root`, and canonical markers. It is written during install and is not canonical knowledge. Agents working in another repository should locate Agent Foundry through this config or `AGENT_FOUNDRY_HOME`, then validate the markers before writing canonical records.

## Generated Artifact Policy

Generated artifacts are downstream projections from canonical records, not independent sources of truth.

Use these categories:

| Category | Current examples | Git behavior | Source of truth |
| --- | --- | --- | --- |
| Canonical source | `practices/`, `assets/`, `workflows/`, `schemas/`, `templates/`, source scripts, `adapters/adapter_profiles.yaml`, adapter quality rules | Tracked | Human-reviewed canonical records and source-maintained tooling |
| Tracked generated distribution output | `adapters/codex/`, `adapters/hermes/`, `adapters/claude-code/`, `adapters/chatgpt/` | Tracked when needed for runtime install, manual import, review, or distribution | Canonical practices/assets plus adapter profiles |
| Runtime copy | Installed files under `~/.codex`, `~/.claude`, `~/.hermes`, and manual ChatGPT imports | Not tracked here | Regenerated or installed from `adapters/` |
| Local private/generated operational state | `runtime/local/`, `usage/local/`, `usage/adoption-log.yaml`, `sync/local/`, `sync/imported/`, `sync/pending/`, `sync/applied/`, `sync/conflicts/`, `sync/snapshots/` | Gitignored by default | Local runtime, sync, or evidence workflows |
| Shared aggregate or derived metadata | `usage/usage-aggregate.yaml`; future derived indexes if approved | Tracked only when sanitized and reviewable | Raw local evidence or canonical records, depending on artifact |

Rules:

1. Edit canonical records first. Practice, asset, workflow, schema, template, or source-tool changes must be made upstream before regenerating downstream artifacts.
2. Track generated artifacts only when they serve a durable review, distribution, install, manual-import, or offline-sync purpose. Otherwise prefer regeneration or ignore them.
3. Tracked generated artifacts must have an explicit regeneration path or a documented manual-target rationale. Adapter outputs are tracked because local runtimes and ChatGPT manual import need concrete files.
4. Runtime copies are never canonical. If a runtime copy drifts, regenerate or reinstall from repository adapters rather than treating the runtime file as policy.
5. Local private or sensitive generated state stays ignored unless a later policy explicitly defines a sanitized shared form.
6. Shared aggregate files may be tracked when they avoid raw evidence and support review. They are still user-vault metadata, not Core default content for a blank external-user vault.
7. Future memory indexes, knowledge packs, graph indexes, or retrieval bundles should be derived from approved current capability records. Do not create `memory/`, top-level `knowledge/`, `research_memos/`, or `project_memory` outputs until reviewed architecture introduces them.
8. Adapter packaging paths such as `adapters/chatgpt/knowledge/` are generated/manual-import adapter outputs. They do not imply that a current top-level memory subsystem `knowledge/` directory exists.

Cleanup and regeneration expectations:

- If canonical records change, publish relevant adapters, run adapter quality checks, then install to enabled runtimes.
- If generated tracked files are hand-edited in an emergency, back-propagate the durable rule to canonical records or document why the generated artifact is intentionally source-maintained.
- If a generated artifact cannot be reproduced or checked, treat that as a policy gap before relying on it for external-user setup.
- If generated files include local paths, raw evidence, secrets, or sensitive content, move them to ignored local/private paths or replace them with sanitized aggregates/templates.

## Usage Evidence Boundary

Usage evidence is split by sensitivity and sync behavior.

Raw evidence is local. Agents write concise raw entries to `usage/local/usage-log.yaml`, which is gitignored and excluded from portable snapshots. Raw entries may include project names, triggers, short notes, and local audit context.

Aggregate evidence is shared. `usage/usage-aggregate.yaml` contains sanitized counts by subject type, subject ID, month, agent, hashed machine ID, outcome counts, and last-used date. Review workflows use the aggregate so multiple machines and agents can contribute statistics without syncing raw notes or session context.

Legacy `usage/asset-usage-log.yaml` remains migration input. New recording should go through `scripts/record_asset_usage.py`, and aggregate rebuilds should use `scripts/aggregate_usage.py`.

## Practice Types

- `principle`: durable design or engineering rule.
- `pattern`: reusable solution shape for a recurring problem.
- `heuristic`: decision aid or question that guides judgment.
- `playbook`: multi-step procedure for a task.
- `checklist`: compact verification list.
- `example`: concrete grounding for a broader rule.
- `anti-pattern`: recurring mistake to avoid.

## Lifecycle

```text
candidate -> proposed -> active -> revised -> superseded -> archived
```

- `candidate`: captured from a session or external source, not yet trusted.
- `proposed`: normalized and deduped, waiting for human approval.
- `active`: approved for use and publication into adapters.
- `revised`: active entry with material updates.
- `superseded`: replaced by another entry; keep for traceability.
- `archived`: no longer recommended and not published.

## Human Review Gate

Human review is mandatory before a practice becomes `active`. After approval, relevant adapters should be published automatically unless the user asks to stage without publishing.

Agents may:

- extract candidates;
- classify them;
- search for duplicates;
- propose merges;
- draft canonical entries;
- update adapters after approval.

Agents should not:

- silently promote new practices to `active`;
- import public skills directly into adapters;
- execute external scripts without explicit permission;
- overwrite canonical entries without explaining the merge decision.

## Adapter Strategy

Each agent environment gets its own adapter because each has different instruction mechanics:

- Codex: `SKILL.md` folders with references.
- Claude Code: `CLAUDE.md` and optional slash commands.
- ChatGPT: custom/project instructions plus knowledge files.
- Hermes: `SKILL.md` folders with references.
- DeepSeek, MiniMax, and similar systems: underlying model providers used through direct programming agents, not direct adapters here.

Adapter entry points should be compact, task-triggered, and operational. Full fidelity is provided through references, command files, or knowledge files rather than one large prompt.

## External Skill Borrowing Strategy

External skills are treated as inputs, not authorities.

Borrowing path:

```text
external skill/repo/article
  -> provenance record in imports/inbox/
  -> security and quality review
  -> candidate practices
  -> dedupe against index
  -> proposed canonical entries
  -> human approval
  -> active practices
  -> adapters
```

Good external material may contribute wording, workflows, trigger descriptions, schemas, or examples. It should not be copied wholesale unless the license permits it and the content passes review.

## Skill Rot Controls

This repository avoids skill rot through:

- stable IDs for practices;
- lifecycle states;
- alias and related-entry metadata;
- dedupe before creation;
- human approval before activation;
- adapter outputs generated from active practices only;
- periodic reviews of stale, conflicting, or too-generic entries;
- separation between long-form docs and compact agent instructions.
- cross-project governance rules that keep derived views, transient context, and runtime integrations from becoming hidden maintenance burdens.
