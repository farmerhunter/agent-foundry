# Agent Foundry

Agent Foundry turns useful lessons from real agent work into reviewed, reusable capabilities that can be carried across Codex, ChatGPT, Claude Code, Hermes, Trae, and similar environments.

Agent Foundry 会把真实 agent 工作中的有用经验，转成经过 review、可复用、可部署到 Codex、ChatGPT、Claude Code、Hermes、Trae 等环境的能力。

## Why This Exists

AI agents can generate useful insights while working, but insight is not the same as durable capability. A good lesson from one session can disappear into chat history, stay trapped in one agent's memory, or become a vague rule that future agents do not actually follow.

AI agent 在工作中会产生有用洞察，但洞察不等于 durable capability。一次 session 里的好经验可能留在聊天记录里、困在某个 agent memory 中，或变成未来 agent 不会真正遵守的模糊规则。

Agent Foundry exists to govern that transformation:

```text
work session
  -> insight
  -> canonical practice or reusable asset
  -> human approval
  -> agent-specific adapter
  -> runtime use
  -> usage evidence
  -> review and improvement
```

The goal is not to maintain a pile of prompts. The goal is to make hard-won working judgment portable across sessions, agents, machines, and projects without losing human review or source-of-truth discipline.

目标不是维护一堆 prompts，而是让来之不易的 working judgment 能跨 session、agent、machine 和 project 复用，同时保留 human review 和 source-of-truth discipline。

For the longer motivation, see [docs/philosophy.md](docs/philosophy.md).

## What It Does

Agent Foundry keeps Core tooling, User Vault records, and runtime delivery separate.

- Core contains workflows, schemas, scripts, templates, docs, adapter profiles, and validation tools.
- A User Vault contains canonical practices, reusable assets, indexes, imports, and sanitized usage aggregates.
- `adapters/`: downstream outputs for specific agent environments.
- Runtime installs under agent-specific home directories are downstream copies.

Agent memory, session summaries, and external skills are treated as evidence sources. They can suggest candidates, but they do not become durable rules until reviewed.

Agent memory、session summaries 和 external skills 都只是 evidence sources。它们可以提出 candidates，但必须经过 review 才能变成 durable rules。

## First Value Path / 第一次获得价值

Use this path when you are new. It avoids advanced choices until Agent Foundry is initialized and you have seen one reusable lesson become a reviewed item.

新用户先走这条路径。它会在完成初始化并看到一条可复用经验进入 review 之前，避免高级配置选择。

1. **Clone Core and ask your agent to initialize Agent Foundry.**

   **Clone Core，然后让 agent 初始化 Agent Foundry。**

   ```text
   Set up Agent Foundry for this machine using the default local Vault path. Show me what changed and stop before runtime writes.
   ```

   The expected setup outcome is a selected User Vault, a local Core/Vault locator, and a read-only status report. If you are doing the setup manually or need custom paths, use [Deployment](docs/deployment.md).

   预期 setup outcome 是 selected User Vault、本机 Core/Vault locator，以及 read-only status report。如果你要手动设置或使用自定义路径，请看 [Deployment](docs/deployment.md)。

2. **Run one representative core-value scenario.**

   **运行一个代表性核心价值场景。**

   After any real work session, ask:

   在任意真实工作 session 之后，告诉 agent：

   ```text
   Harvest reusable practices from this session. Show me a concise review list and wait for approval before changing canonical records.
   ```

   Visible outcome: the agent should show a review list of candidate lessons. After you approve an item, the selected User Vault records and relevant adapter outputs are the changed state; unapproved ideas remain review material only.

   Visible outcome：agent 应展示 candidate lessons 的 review list。你批准某一项后，selected User Vault records 和相关 adapter outputs 才是 changed state；未批准的想法只保留为 review material。

3. **Verify before the next step.**

   **进入下一步前先验证。**

   ```text
   Check Agent Foundry status.
   ```

   The status report should name the Core checkout, selected User Vault, generated output state, runtime receipt state, manual targets such as ChatGPT, and the next safe action. It should not require capability-pack maintenance, GitHub helper internals, advanced runtime repair, roadmap work, or memory-system planning.

   Status report 应说明 Core checkout、selected User Vault、generated output state、runtime receipt state、ChatGPT 等 manual targets，以及 next safe action。它不应要求你先理解 capability-pack maintenance、GitHub helper internals、advanced runtime repair、roadmap work 或 memory-system planning。

4. **Next safe step.**

   **下一步安全操作。**

   Use [Usage](docs/usage.md) for daily operation and [Commands](docs/commands.md) for short Skill-facing intents. Use [Deployment](docs/deployment.md) when you need full install, runtime target changes, Trae setup, status repair, or cross-machine restore.

   日常使用看 [Usage](docs/usage.md)，短命令和 Skill-facing intents 看 [Commands](docs/commands.md)。需要完整安装、runtime target 变更、Trae setup、status repair 或跨机器恢复时，看 [Deployment](docs/deployment.md)。

## Daily Use / 日常使用

Use short natural-language commands instead of remembering internal workflows:

日常使用时，用自然语言短命令，不需要记住内部 workflow：

| Command | Purpose | 中文 |
| --- | --- | --- |
| `refresh practices and assets` | Pull updates, regenerate adapters if needed, and install to enabled local runtimes through the reviewed path. | 拉取更新，必要时重新生成 adapters，并通过 reviewed path 安装到 enabled local runtimes。 |
| `check Agent Foundry status` | Read current Core, selected Vault, generated output, runtime receipt, and manual target state without writing. | 只读检查 Core、selected Vault、generated output、runtime receipt 和 manual target state。 |
| `harvest practices` | Extract reusable lessons from a work session as a review list before canonical changes. | 从工作 session 提炼可复用经验，先展示 review list，再进入 canonical changes。 |
| `discover assets` | Find repeated workflows worth packaging as a skill, subagent, automation, or extension. | 发现值得打包为 skill、subagent、automation 或 extension 的重复 workflow。 |
| `review practices` | Check for stale rules, duplicates, weak activation, adapter drift, and skill rot. | 检查过期规则、重复项、弱激活、adapter drift 和 skill rot。 |

Detailed prompts and Chinese equivalents are in [Usage](docs/usage.md) and [Commands](docs/commands.md).

详细 prompts 和中文版本见 [Usage](docs/usage.md) 与 [Commands](docs/commands.md)。

## Repository Map / 仓库结构

| Path | Purpose | 中文 |
| --- | --- | --- |
| `workflows/` | Procedures agents should follow for harvest, import, review, publish, and sync. | Agent 执行 harvest、import、review、publish、sync 时遵循的流程。 |
| `schemas/` | Canonical record shapes and validation rules. | Canonical records 的结构和验证规则。 |
| `scripts/` | Deterministic tooling for checks, install, sync, evidence, and review. | 用于 checks、install、sync、evidence、review 的 deterministic tooling。 |
| `templates/` | Blank practice, asset, and import templates for Vault records. | Vault records 的 practice、asset、import 空模板。 |
| `adapters/` | Adapter profiles and tracked distribution outputs. | Adapter profiles 和 tracked distribution outputs。 |
| `runtime/` | Machine-local deployment manifests and portable runtime templates. | Machine-local deployment manifests 和 portable runtime templates。 |
| `sync/` | Portable sync templates and ignored local sync state. | Portable sync templates 和 ignored local sync state。 |
| `docs/` | Human-readable philosophy, usage, design, deployment, and compatibility notes. | 面向人的 philosophy、usage、design、deployment、compatibility 文档。 |

Vault-owned paths such as `practices/`, `assets/`, `indexes/`, `imports/`, and `usage/usage-aggregate.yaml` live in the selected User Vault, not in the clean public Core checkout.

`practices/`、`assets/`、`indexes/`、`imports/`、`usage/usage-aggregate.yaml` 等 Vault-owned paths 位于 selected User Vault，不属于干净的 public Core checkout。

## Design Principles

- The repository is the canonical source of truth.
- Runtime files under `~/.codex`, `~/.claude`, `~/.hermes`, and similar locations are downstream copies.
- Agent memory is evidence, not authority.
- Human approval gates durable practices and assets.
- Adapters should preserve meaning while respecting each agent's native instruction mechanics.
- The smallest maintainable mechanism is preferred over heavier machinery.

See [docs/system-design.md](docs/system-design.md) and [docs/lifecycle-compatibility.md](docs/lifecycle-compatibility.md).

## Supported Targets / 支持目标

| Target | Status | 中文 |
| --- | --- | --- |
| Codex | Local `SKILL.md` adapter. | 本地 `SKILL.md` adapter。 |
| Claude Code | `CLAUDE.md` and related adapter files. | `CLAUDE.md` 和相关 adapter files。 |
| Hermes | Local `SKILL.md` adapter. | 本地 `SKILL.md` adapter。 |
| Trae | Local `SKILL.md` adapter under the Trae runtime path. | Trae runtime path 下的本地 `SKILL.md` adapter。 |
| ChatGPT | Manual import through custom/project instructions and knowledge files. | 通过 custom/project instructions 和 knowledge files 手动导入。 |

DeepSeek, MiniMax, and similar model providers are treated as underlying models used through programming agents, not direct Agent Foundry adapters.

## Documentation / 文档入口

Start with the tier that matches your task, then use complete references only when you need them.

先看与你任务匹配的层级；只有需要时再进入完整 reference。

| Tier | Start here | When to use it | 中文 |
| --- | --- | --- | --- |
| Beginner / first value | This README | Minimal onboarding, one representative harvest/review scenario, visible outcome, verification, and next safe step. | 新手 first value：最小 onboarding、一个 harvest/review 场景、可见结果、验证和下一步。 |
| Ordinary daily operation | [Usage](docs/usage.md), [Commands](docs/commands.md) | Daily status, refresh, harvest, review, publish, normal runtime/generated checks, and normal capability-pack consumption. | 普通日常：status、refresh、harvest、review、publish、runtime/generated 检查和普通 capability-pack 使用。 |
| Complete / power-user reference | [Deployment](docs/deployment.md), [System Design](docs/system-design.md), [Lifecycle Compatibility](docs/lifecycle-compatibility.md) | Full runtime setup/repair, architecture boundaries, lifecycle/governance, advanced/debug workflows, and maintainer decisions. | 完整/高级参考：runtime setup/repair、architecture boundaries、lifecycle/governance、advanced/debug workflows 和 maintainer decisions。 |

Additional references:

补充参考：

- [Offline Sync](docs/offline-sync.md): snapshot and remote sync strategy.
- [Runtime Adapter Framework And Trae](docs/runtime-adapter-framework-and-trae.md): runtime adapter framework and Trae support reference.
- [Standards and Sources](docs/standards-and-sources.md): external conventions and adapter standards.
- [Roadmap](docs/roadmap.md): project planning and milestone history.
- [Philosophy](docs/philosophy.md): why this project exists.

Planning/evidence docs such as [Memory System Handoff Dump](docs/memory-system-handoff-dump.md) are not beginner or ordinary-user operating guides.

[Memory System Handoff Dump](docs/memory-system-handoff-dump.md) 等 planning/evidence docs 不是 beginner 或 ordinary-user operating guides。
