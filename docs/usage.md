# Usage Guide

This guide is for day-to-day use. You do not need to remember the internal workflows.

这是一份日常使用指南。你不需要记住内部 workflow 细节。

---

## Core Rule

For daily use, prefer short commands from `docs/commands.md`, such as `harvest practices` or `做一次 harvest practice`.

日常使用优先使用 `docs/commands.md` 里的短命令，例如 `harvest practices` 或 `做一次 harvest practice`。

The agent may discover, draft, and recommend practices. You approve each meaningful new or changed practice.

After you approve a practice, the agent should automatically complete the remaining steps:

```text
approve
  -> merge or create canonical entry
  -> promote to active
  -> update index
  -> publish relevant adapters
  -> report changed files
```

核心规则：

Agent 可以发现、整理、推荐 practice。每一条重要的新 practice 或变更都需要你批准。

你批准后，agent 应自动完成后续步骤：

```text
批准
  -> 合并或创建 canonical entry
  -> 提升为 active
  -> 更新 index
  -> 发布相关 adapters
  -> 汇报改动文件
```

---

## 1. Harvest Practices

Use this after a coding/design/debugging session when you want to preserve reusable lessons.

用于一次开发、设计、debug 结束后，把可复用经验沉淀下来。

### English Prompt

```text
Harvest reusable practices from this session using Agent Foundry. Keep the details hidden and present a concise review list. For each new or changed practice, show the title, why it matters, whether it merges into an existing rule or creates a new one, and what adapters would be updated after approval. Wait for my approval per practice before applying.
```

After reviewing:

```text
I approve practice 1 and 3. Apply them, promote them to active, update the index, and publish the relevant adapters.
```

### 中文 Prompt

```text
用 Agent Foundry 从这次 session 中提炼可复用实践。隐藏内部细节，只给我一个简洁的 review list。对每条新增或变更的 practice，说明标题、为什么重要、会合并到已有规则还是创建新规则，以及批准后会更新哪些 adapters。每条 practice 等我批准后再应用。
```

批准后：

```text
我批准第 1 和第 3 条。请应用它们，提升为 active，更新 index，并发布相关 adapters。
```

---

## 2. Import External Skills

Use this when you find a useful public skill, prompt pack, article, repo, or local skill folder.

用于你发现一个外部 skill、prompt pack、文章、repo 或本地 skill 目录，想借鉴其中有价值的内容。

### English Prompt

```text
Evaluate this external skill for Agent Foundry: <URL or local path>. Use the import workflow, but keep the report concise. Show provenance, license/security concerns, useful candidate practices, duplicates found, and what would be imported after approval. Do not activate or publish anything until I approve each candidate.
```

After reviewing:

```text
I approve candidate 2. Import it, promote it to active, update the index, and publish the relevant adapters.
```

### 中文 Prompt

```text
请评估这个外部 skill 是否适合加入我的 agent-practices 系统：<URL 或本地路径>。使用 import workflow，但报告保持简洁。展示来源、license/security 风险、有价值的候选 practices、发现的重复项，以及批准后会导入什么。每个 candidate 未经我批准前不要 activate 或 publish。
```

批准后：

```text
我批准第 2 个 candidate。请导入它，提升为 active，更新 index，并发布相关 adapters。
```

---

## 3. Discover Assets

Use this when you want the agent to look across recent work and find repeated workflows worth packaging as a skill, subagent, automation, or extension of an existing asset.

用于让 agent 回顾近期工作，发现值得打包成 skill、subagent、automation 或扩展已有 asset 的重复工作流。

### English Prompt

```text
discover assets
```

After reviewing:

```text
I approve asset candidate 1. Create or extend the asset, update the asset index, and publish relevant adapters.
```

### 中文 Prompt

```text
发现可打包资产
```

批准后：

```text
我批准第 1 个 asset candidate。请创建或扩展该 asset，更新 asset index，并发布相关 adapters。
```

---

## 4. Publish Adapters

Usually you do not need to run this manually. Publishing should happen automatically after you approve a practice.

通常不需要手动运行。你批准某条 practice 后，agent 应自动发布相关 adapters。

Use manual publish only when adapters may be stale or you changed canonical files by hand.

只有当 adapters 可能过期，或者你手动改过 canonical files 时，才需要手动 publish。

### English Prompt

```text
Publish adapters from the current active practices. Do not include candidate, proposed, superseded, or archived entries. Report which adapters changed and which canonical IDs they include.
```

### 中文 Prompt

```text
请基于当前 active practices 发布 adapters。不要包含 candidate、proposed、superseded 或 archived entries。汇报哪些 adapters 被更新，以及包含了哪些 canonical IDs。
```

---

## 5. Review Practices

Use this periodically to prevent skill rot.

定期使用它，避免 rules 变重复、变泛、变过期。

Recommended timing:

- monthly;
- after several harvest/import sessions;
- before installing adapters into a new agent environment;
- when adapter files feel too long or generic;
- when a domain has many similar entries.

建议时机：

- 每月一次；
- 多次 harvest/import 之后；
- 准备把 adapters 安装到新的 agent 环境前；
- adapter 文件变得太长或太泛时；
- 某个 domain 出现很多相似 entries 时。

### English Prompt

```text
Review Agent Foundry for skill rot. Look for duplicates, stale entries, weak generic rules, adapter drift, and proposed items that need decisions. Give me a concise review list with recommended actions. Do not archive, supersede, or publish anything without my approval.
```

### 中文 Prompt

```text
请 review Agent Foundry，检查 skill rot。重点看重复规则、过期 entries、太泛的规则、adapter drift，以及需要决策的 proposed items。给我一个简洁的 review list 和建议动作。未经我批准，不要 archive、supersede 或 publish。
```

---

## 6. Review Assets

Use this periodically to prevent asset rot: unused skills, overlapping subagents, stale automations, weak triggers, or missing adapter coverage.

定期使用它，避免 asset rot：没人用的 skills、重叠的 subagents、过期 automations、触发词不清、adapter 覆盖缺失。

### English Prompt

```text
review assets
```

### 中文 Prompt

```text
检查 asset rot
```

---

## Approval Style

Prefer approving by numbered items:

```text
I approve 1, 3, and 4.
```

or:

```text
我批准第 1、3、4 条。
```

The agent should then apply only those approved practices or assets and publish relevant adapters automatically.

Agent 应只应用你批准的 practice 或 asset，并自动发布相关 adapters。

---

## What You Should See From The Agent

For harvest/import/review, the agent should show a compact list like:

```text
1. Boundaries before tools
   Action: merge into ARCH-001
   Why: strengthens the existing rule with a new heuristic
   After approval: update ARCH-001, update index, publish architecture-design adapter

2. Avoid direct external skill import
   Action: create META-004
   Why: new safety rule for imported skills
   After approval: create META-004, promote active, update index, publish practice-harvester adapter
```

It should not force you to read the full internal workflow unless you ask.
