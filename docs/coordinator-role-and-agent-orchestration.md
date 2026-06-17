# Coordinator Role And Agent Orchestration Design Notes

Status: design discussion record  
Updated: 2026-06-17  
Scope: Agent Foundry multi-agent collaboration, Coordinator role, context economy, model-tier aware orchestration.  
Non-scope: implementation plan, memory-system work, runtime mutation, GitHub Project mutation.

## Purpose

本文记录 Agent Foundry 从简单 multi-agent collaboration 走向更高效智能体调度的设计思路。

当前 Agent Foundry 已经形成以 Human、Architect、Implementer、Reviewer、Harvester 为核心的协作模型，并通过 GitHub issues、PRs、labels、Project fields、Execution Contracts 和 durable comments 维持工作状态。AF7/AF8 之后，系统暴露出一个新的设计问题：当目标变长、线程变多、runtime 能力差异变大时，Architect 同时承担技术判断和 workflow 运转职责，会带来上下文膨胀、handoff 成本、状态漂移和角色污染。

本文讨论是否应从现有 Architect 职责中拆分出 Coordinator role，以及如何避免 Coordinator 变成过窄的 summary 工具或过重的 PM 层。

## External Implementation Patterns

当前主流 multi-agent systems 大致有五种调度模式。

| Pattern | Representative systems | Control shape | Design signal for Agent Foundry |
| --- | --- | --- | --- |
| Manager / supervisor | CrewAI hierarchical process, LangGraph supervisor | Central manager delegates and validates specialist work. | Coordinator 可以作为 centralized control plane，但不能取代 Architect 的技术判断。 |
| Agents as tools | OpenAI Agents SDK | Orchestrator keeps response ownership and invokes specialists as bounded tools. | 适合 AF 的 bounded review、evidence extraction、implementation packet。 |
| Handoffs | OpenAI Agents SDK, LangGraph handoffs, AutoGen Swarm | Active agent transfers control to another specialist. | 适合 role transition，但必须由 durable GitHub state 防止 transient handoff 丢失。 |
| Group chat / selector | AutoGen SelectorGroupChat | Shared conversation with manager selecting next speaker. | 适合 brainstorming，不适合作为 AF baseline，因为 shared history 容易膨胀并混合 authority。 |
| Lead agent with parallel subagents | Anthropic multi-agent research system | Lead agent plans, spawns parallel agents, synthesizes results. | 适合宽搜索和 evidence gathering；对 tightly coupled coding 或 architecture work 要谨慎。 |

外部实践的共同趋势是：复杂 multi-agent 系统需要一个明确的 orchestration surface，但 orchestration 不一定等同于专业决策。OpenAI Agents SDK 区分 LLM-driven orchestration 和 code-driven orchestration，也支持 handoffs 和 agents-as-tools 两类 specialist 调用模式。CrewAI hierarchical process 明确 manager agent 负责 delegation 和 result validation。AutoGen SelectorGroupChat 用 manager 根据 context 和 agent descriptions 选择下一位 agent。Anthropic 的研究系统显示 lead agent 加 subagents 能提升宽搜索覆盖，但 token 成本会明显上升。

这些模式支持一个结论：Agent Foundry 可以引入 Coordinator，但 Coordinator 应该是 durable workflow control plane，而不是仅依赖某个 runtime 的 native thread/subagent API。

## Current Agent Foundry Baseline

Agent Foundry 当前协作基线包括：

- Human：产品方向、human decision gates、final merge、Epic closure、高风险授权。
- Architect：架构判断、Epic/Decision issue、Execution Contract、acceptance、human-decision technical framing。
- Implementer：在明确 contract 下做 bounded implementation。
- Reviewer：独立 review，优先 bugs、risks、regressions、missing tests。
- Harvester：从完成工作中提取 reusable practices / assets。

已有 durable coordination substrate：

- GitHub issue / PR / comments。
- `needs:*` labels。
- GitHub Project fields。
- Roadmap Status。
- Execution Contract。
- Human Decision Contract。
- Post-merge acceptance comments。
- Role dispatch prompts and callback records。

这个基线的优势是 tool-agnostic：Codex、Claude Code、Trae、ChatGPT/manual import 或其他 agent runtime 都可以通过 GitHub durable state 和 prompt handoff 协作。

它的限制是：Architect 已经承担了过多运行时协调工作。AF7/AF8 中出现过的 governance drift、Project state drift、stale `needs:*` labels、old HDC 被 supersede 后仍需人工追踪、idle/resume 后 rules 遵守退化等问题，都更像 workflow control 问题，而不是 architecture reasoning 问题。

## Proposed Coordinator Role

Coordinator 的核心定义：

```text
Coordinator owns operational coherence and context economy.
Architect owns technical judgment.
```

Coordinator 不应被定义为“能调用其他 agents 的 agent”。更准确的定义是：

> Coordinator maintains durable coordination state, prepares role-specific context packets, routes work across roles and runtimes, and uses runtime-native dispatch only when available.

### Coordinator Responsibilities

Coordinator 应负责：

- Goal intake：承接 `/goal` 或长目标，把目标转成 durable work structure。
- Scheduler state：维护 issue/PR/Project/label/Roadmap Status 的一致性。
- Role routing：判断下一步是 Architect、Implementer、Reviewer、Harvester 还是 Human。
- Durable session setup：建立或恢复 role sessions；若 runtime 不支持 native thread control，则生成 handoff packet。
- Context economy：生成 role-specific rehydration packet，减少重复读取和旧历史污染。
- Control loop：检查 blocked state、human gates、review gates、merge gates、closure gates。
- State drift repair：发现 stale labels、closed issue 残留 `needs:*`、superseded HDC、Project mismatch。
- Model-tier assignment：根据 task ambiguity/risk 决定使用 leading model 还是 standard model。

Coordinator 不应负责：

- 技术方案最终判断。
- 架构边界裁决。
- 是否接受 technical debt。
- high-risk PR acceptance。
- Reviewer 的独立质量信号。
- Harvester 的 canonical practice 决策。
- human-only authorization。

## Role Boundary

引入 Coordinator 后，建议角色边界如下：

| Role | Owns | Does not own |
| --- | --- | --- |
| Human | Product direction, explicit authorization, final high-risk decisions. | Routine state cleanup unless human gate is truly required. |
| Coordinator | Goal intake, role routing, durable state, context packets, model-tier assignment, workflow closure checks. | Technical acceptance, architecture policy, independent review. |
| Architect | Architecture, technical decomposition, Execution Contracts, acceptance, high-risk technical decisions. | Mechanical Project sync, repeated handoff formatting, routine label cleanup. |
| Implementer | Bounded code/docs/test changes under contract. | Scope expansion, policy decisions, final acceptance. |
| Reviewer | Independent quality check against criteria. | Work planning, implementation, human authorization. |
| Harvester | Reusable practice/asset extraction. | Direct activation without approval, workflow scheduling. |

The key rule:

```text
Coordinator owns flow.
Architect owns judgment.
Reviewer owns independent quality signal.
Implementer owns bounded change.
Human owns authorization.
```

## Tool-Agnostic Orchestration

Agent Foundry must remain tool-agnostic. Coordinator cannot depend on Codex desktop thread tools, Claude Code internals, Trae private state, or any single runtime's subagent API.

Coordinator support should have three execution tiers:

| Tier | Mechanism | Baseline status | Example |
| --- | --- | --- | --- |
| Durable orchestration | GitHub issues, PRs, labels, comments, Project fields, local files. | Required AF baseline. | Coordinator posts issue handoff and label transition. |
| Manual bridge | Copyable role prompt / handoff packet. | Required fallback. | User copies Reviewer packet into Claude Code or Trae. |
| Runtime-native dispatch | Codex thread tools, native subagents, Trae SOLO orchestration, future APIs. | Optional acceleration. | Coordinator sends message to existing Reviewer thread. |

This means Coordinator design must degrade gracefully:

- If native dispatch exists, use it.
- If it does not exist, write durable state and produce a portable handoff packet.
- If even GitHub mutation is unavailable, produce a read-only packet and ask the human to apply it.

The durable state remains source of truth; runtime-native dispatch is optimization, not architecture foundation.

## Context Economy Model

Coordinator should reduce token cost by controlling context shape, not merely by summarizing prose.

A more accurate token model for complex projects is:

```text
role_run_tokens =
  static_role_instructions
+ runtime/system instructions
+ project governance context
+ repository/domain context
+ issue/PR contract
+ evidence payload
+ recent conversation
+ tool outputs
+ reasoning/output tokens
```

For Agent Foundry, the expensive parts are often:

- project governance context: `AGENTS.md`, generated Skills, collaboration practices;
- domain architecture context: `docs/system-design.md`, `docs/roadmap.md`, adapter design docs;
- issue/PR history: Epic comments, superseded HDCs, rejection comments, review comments;
- codebase search context: `rg`, file reads, diffs, test outputs;
- runtime state context: Core/Vault/generated/runtime/local-private boundaries;
- error recovery context: rejected heads, failed reviews, stale labels.

Coordinator should turn this into layered context:

| Layer | Content | Typical consumer |
| --- | --- | --- |
| L0 Stable global rules | AGENTS, core skills, safety boundaries. | All roles, ideally cached. |
| L1 Project architecture summary | Core/Vault/Generated/Runtime/Local Private, roadmap stage, current boundaries. | Coordinator, Architect, Reviewer. |
| L2 Epic checkpoint | Current child state, accepted gates, superseded gates, residual risks. | Coordinator, Architect. |
| L3 Issue contract | Acceptance criteria, Execution Contract, branch/merge rules. | Implementer, Reviewer, Architect. |
| L4 PR/head evidence | Exact head, changed files, latest comments, diff summary. | Implementer, Reviewer. |
| L5 Role ask | Specific role instructions and forbidden actions. | Target role. |
| L6 Verification evidence | Commands run, outputs, test coverage map. | Reviewer, Architect. |

The design goal is not minimal context; it is bounded sufficient context. A standard model may need more explicit checklist context than a leading model, even if both receive fewer raw historical comments.

## Token And Cost Implications

External data supports caution. Anthropic reports that agent interactions can use about 4x tokens compared with chat interactions, and multi-agent systems can use about 15x tokens compared with chats. This does not mean multi-agent is bad; it means it must buy coverage, parallelism, review independence, or reduced rework.

Coordinator can improve token economics when it prevents:

- every role rereading full Epic history;
- every role reading old rejected heads;
- every handoff reconstructing `AGENTS.md`, skills, roadmap, PR comments, and diff from scratch;
- ordinary state cleanup being routed through high-context Architect turns;
- weak models making incorrect transitions that later require expensive correction.

Coordinator can worsen token economics when it adds ceremonial routing for simple tasks or forces every task through an extra discussion layer.

Prompt caching and compaction are relevant but not sufficient. OpenAI prompt caching can reduce cost/latency when repeated prefixes stay stable. OpenAI compaction is intended to preserve long-running conversation state while reducing context size. Anthropic also supports prompt caching. Agent Foundry should design Coordinator packets so stable context appears as stable prefix where runtime supports it, but should not depend on any one provider's cache behavior.

## Model-Tier Aware Collaboration

Agent Foundry should not assume all models have equal planning or review quality. A practical design should support at least two model tiers:

| Tier | Strength | Risk |
| --- | --- | --- |
| Leading model | Handles ambiguity, tradeoffs, architecture, nuanced review, long context. | Expensive; can still be slowed by unnecessary context. |
| Standard model | Executes explicit steps, local edits, mechanical verification, checklist review. | More likely to miss implicit constraints, stale state, and broad risks. |

Coordinator should classify each task by:

```text
ambiguity: low | medium | high
risk: low | medium | high
context breadth: narrow | project | cross-project
model tier: leading-required | standard-ok | standard-preferred
packet shape: full | focused | evidence-only | checklist-review
```

Suggested mapping:

| Work type | Preferred model tier | Coordinator packet |
| --- | --- | --- |
| Architecture decision, policy boundary, privacy/runtime write decision | Leading required | Full / Architect packet |
| Epic decomposition and Execution Contract drafting | Leading preferred | Focused + project context |
| Bounded implementation with clear files/tests | Standard OK | Focused implementation packet |
| Evidence extraction, issue/PR state audit, grep/test inventory | Standard preferred | Evidence-only packet |
| Low-risk docs-only review | Standard OK | Checklist-review packet |
| Final readiness / high-risk review / acceptance | Leading preferred or required | Full evidence + risk packet |
| Harvest proposal | Leading or standard depending on ambiguity | Focused harvest packet |

### Standard Model Guardrails

Standard models should receive harder contracts:

- exact role;
- exact issue/PR/head;
- exact files to read;
- exact acceptance checklist;
- exact regression checklist;
- forbidden actions;
- expected output schema;
- escalation conditions.

Example packet shape:

```text
Role: Reviewer
Task: review PR #156 at exact head e751c70
Read:
- Issue #155 acceptance criteria
- PR #156 diff
- latest Implementer comment
Check:
1. bilingual paired format
2. no `English Prompt` / `中文 Prompt` headings
3. no `adapters/chatgpt` regression
4. `sync_status.py` remains before apply paths
Forbidden:
- do not merge
- do not close issue or Epic
Return:
- blocking findings with file/line, or acceptance comment
Escalate if:
- issue body conflicts with latest comments
- rejected head appears current
- technical policy decision is needed
```

This is not simply shorter context; it is more structured context.

## Workflow Modes

Coordinator should support multiple workflow modes instead of forcing one pattern.

### Simple Task Mode

Use when a single low-risk task can be handled by one role.

```text
Human -> Implementer -> Reviewer -> Architect acceptance if needed -> Human only if gated
```

Coordinator may remain implicit or only provide context packet generation.

### Goal Mode

Use when user enters a durable objective such as `/goal`.

```text
Human goal
  -> Coordinator intake
  -> durable checkpoint
  -> role routing
  -> bounded packets
  -> review/acceptance gates
  -> closure audit
```

Coordinator is explicit here because goal completion requires state continuity.

### Evidence-First Mode

Use when the task is broad, ambiguous, or potentially high-risk.

```text
Coordinator
  -> Standard model evidence packet
  -> Architect decision packet
  -> Implementer task packet
```

This lets cheaper or less capable models gather facts while leading models make decisions.

### Native Dispatch Mode

Use when the current runtime exposes thread or subagent controls.

```text
Coordinator
  -> create/send to role thread
  -> durable GitHub comment
  -> callback reconciliation
```

This is efficient but optional.

### Manual Bridge Mode

Use when runtime cannot dispatch another agent.

```text
Coordinator
  -> durable GitHub state
  -> copyable role prompt
  -> human or external runtime executes
  -> callback comment
```

This preserves tool-agnostic behavior.

## Design Risks

| Risk | Failure mode | Mitigation |
| --- | --- | --- |
| Coordinator becomes weak Architect | Coordinator makes technical acceptance without expertise. | Hard role boundary: technical judgment routes to Architect. |
| Coordinator becomes summary bot | It only summarizes context and does not own workflow state. | Give Coordinator ownership of routing, packet shape, and state coherence. |
| Process overhead | Simple tasks become ceremony-heavy. | Coordinator required only for goal mode, multi-role work, stale-state recovery, or high-risk gates. |
| Tool lock-in | Design assumes Codex thread tools or Trae private state. | Durable GitHub/file/prompt baseline; native dispatch optional. |
| Standard model overreach | Lower-tier model makes broad decisions from narrow evidence. | Task tiering, checklist packets, evidence-only mode, escalation rules. |
| Token cost increase | More agents means more prompts and tool calls. | Use Coordinator to reduce repeated rehydration and avoid unnecessary multi-agent paths. |
| Stale durable state | Coordinator relies on outdated labels/comments. | Rehydration checkpoint before risky transitions. |
| Authority mixing | Project rules, role prompts, and runtime always-applied rules expose all roles to all agents. | Isolated role packets; avoid always-applied multi-role prompts where unsafe. |

## Evaluation Criteria

Coordinator is worth introducing only if it improves at least one of these outcomes without weakening the others:

- fewer stale or contradictory Project/label/issue states;
- lower repeated rehydration cost per role handoff;
- fewer incorrect transitions after idle/resume;
- clearer human decision gates;
- better use of standard models for bounded work;
- better preservation of Architect attention for real design decisions;
- compatible operation across Codex, Claude Code, Trae, and manual handoff workflows.

It should not be considered successful merely because a new role exists.

## Recommended Direction

Introduce Coordinator as an optional orchestration role with a strong durable baseline:

```text
Coordinator:
  owns goal intake, role routing, durable state, context packets,
  model-tier assignment, escalation gates, and workflow closure checks.

Architect:
  owns architecture, technical decomposition, Execution Contracts,
  acceptance, and high-risk technical decisions.
```

Design priority should be:

1. Coordinator rehydration protocol and packet shapes.
2. Durable scheduler state coherence.
3. Model-tier aware role dispatch.
4. Optional runtime-native dispatch adapters.

This order keeps the work aligned with Agent Foundry's tool-agnostic positioning. It also makes token efficiency and collaboration quality concrete before introducing heavier automation.

## Open Questions

- Should `Coordinator` become a first-class `Owner Role` value in GitHub Project fields, or remain an implicit role inside `agent-collaboration` until proven?
- Should `needs:coordinator` exist, or should Coordinator operate on existing `needs:*` transitions without adding a new label?
- What is the minimum durable packet schema: Markdown comment, YAML block, or generated artifact?
- Which transitions require leading-model Coordinator rather than standard-model Coordinator?
- How should packet generation interact with provider-native prompt caching and compaction without depending on a single provider?
- Should Trae SOLO mode use Coordinator as its default multi-role entry point, while Codex uses native thread dispatch when available?

## References

- OpenAI Agents SDK, Agent orchestration: https://openai.github.io/openai-agents-python/multi_agent/
- OpenAI Agents guide: https://developers.openai.com/api/docs/guides/agents
- OpenAI prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- OpenAI compaction: https://developers.openai.com/api/docs/guides/compaction
- CrewAI hierarchical process: https://docs.crewai.com/en/learn/hierarchical-process
- CrewAI processes: https://docs.crewai.com/en/concepts/processes
- CrewAI custom manager agent: https://docs.crewai.com/en/learn/custom-manager-agent
- AutoGen SelectorGroupChat: https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/selector-group-chat.html
- AutoGen group chat pattern: https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/group-chat.html
- LangGraph supervisor reference: https://reference.langchain.com/python/langgraph-supervisor
- Anthropic multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
