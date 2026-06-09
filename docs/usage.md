# Usage Guide

This guide is for day-to-day use. You do not need to remember the internal workflows.

这是一份日常使用指南。你不需要记住内部 workflow 细节。

---

## How It Works

Agent Foundry is a **local-first** system. The git repository is the canonical workspace. Installed agent files under `~/.claude`, `~/.codex`, and `~/.hermes` are downstream copies.

```text
work session or external skill
  -> harvest / import / discover
  -> human approval
  -> canonical practice or asset (in repo)
  -> agent publishes adapters
  -> install to local runtimes
  -> use short commands to invoke assets
```

工作方式：Agent Foundry 是本地优先的系统。git 仓库是 canonical workspace。`~/.claude`、`~/.codex`、`~/.hermes` 下的文件是下游副本。

---

## Core Rule

For daily use, prefer short commands from `docs/commands.md`, such as `harvest practices` or `做一次 harvest practice`.

日常使用优先使用 `docs/commands.md` 里的短命令。

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

## First Time Setup

On a new maintainer machine, see `docs/deployment.md` for the current single-repo install flow. This is not a complete external-user onboarding path yet; public Core plus separate User Vault setup is AF-3/AF-4 work.

The short version for the current maintainer setup:

```bash
python3 scripts/runtime_manifest.py init
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py enable claude-code   # or codex, hermes
python3 scripts/install_foundry.py --apply
```

新机器安装参见 `docs/deployment.md`。

---

## Daily Workflow

Start your day with **`refresh practices and assets`** (or `刷新practices和assets`). This pulls remote updates, checks whether adapters need regeneration, and installs them to your local agent runtimes.

每天以 **`refresh practices and assets`**（或 `刷新practices和assets`）开始。它会拉取远程更新，检查 adapters 是否需要重新生成，并安装到本地 agent runtime。

Use **`harvest practices`** after a session when you want to preserve reusable lessons.

想沉淀经验时用 **`harvest practices`**。

Use **`discover assets`** when you notice repeated manual work that should become reusable.

发现重复手动工作值得打包时用 **`discover assets`**。

Use **`review practices`** periodically (e.g., monthly) to prevent skill rot.

定期（如每月）用 **`review practices`** 防止规则过期。

---

## 1. Refresh Practices And Assets

Use this at the start of a work session, after switching machines, or when adapters feel stale.

用于开始工作前、换机器后、或感觉 adapters 可能过期时。

### English Prompt

```text
refresh practices and assets
```

The agent will:
1. Check local state:
   - If you have unpublished canonical or adapter changes, it offers to **commit and push** first (never stash real work).
   - If you have unrelated changes only, it offers to **stash** them before pulling.
2. Pull remote git updates.
3. Regenerate adapters if canonical practices or assets changed.
4. Install to enabled local runtimes.
5. Report the exact sync state: current commit, whether anything is unpushed, which runtimes were updated.

### 中文 Prompt

```text
刷新practices和assets
```

Agent 会：
1. 检查本地状态：
   - 如果你有未提交的 canonical 或 adapter 改动，它会先提议**commit 并 push**（真正的作品不会被 stash）。
   - 如果只有无关改动，它会提议**stash**后再拉取。
2. 拉取远程 git 更新。
3. 如有必要，重新生成 adapters。
4. 安装到已启用的本地 runtimes。
5. 汇报精确同步状态：当前 commit、是否有未 push 的内容、哪些 runtimes 被更新。

---

## 2. Harvest Practices

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

## 3. Import External Skills

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

## 4. Discover Assets

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
Review Agent Foundry for skill rot. Run the practice review workflow, summarize the recommendations, and give me an approval list. Look for duplicates, stale entries, weak or missed activation, adapter drift, and proposed items that need decisions. Do not archive, supersede, change activation tiers, or publish anything without my approval.
```

### 中文 Prompt

```text
请 review Agent Foundry，检查 skill rot。执行 practice review workflow，总结 recommendations，并给我一个可批准的清单。重点看重复规则、过期 entries、弱 activation 或 missed activation、adapter drift，以及需要决策的 proposed items。未经我批准，不要 archive、supersede、修改 activation tier 或 publish。
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

## Consistency Checks

If something feels off, run the consistency checker manually:

```bash
python3 scripts/check_consistency.py
```

This validates indexes, practice frontmatter, asset fields, cross-references, adapter ID references, and runtime manifest integrity.

感觉不对劲时可以手动运行 consistency check。

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

2. Keep derived indexes generated
   Action: merge into GOV-001
   Why: reinforces the source-of-truth boundary for generated views
   After approval: update GOV-001, update index, publish relevant adapters
```

It should not force you to read the full internal workflow unless you ask.
