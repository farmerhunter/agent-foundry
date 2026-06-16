# Usage Guide

This guide is for day-to-day use. You do not need to remember the internal workflows.

这是一份日常使用指南。你不需要记住内部 workflow 细节。

---

## How It Works

Agent Foundry is a **local-first** system with separate Core, User Vault, and runtime layers. The public Core checkout contains workflows, schemas, scripts, templates, docs, and adapter profiles. Canonical practices, assets, indexes, imports, and shared usage aggregates live in the selected User Vault. Installed agent files under `~/.claude`, `~/.codex`, `~/.hermes`, and `~/.trae-cn` are downstream copies.

```text
work session or external skill
  -> harvest / import / discover
  -> human approval
  -> canonical practice or asset (in selected User Vault)
  -> agent publishes adapters from Core plus selected Vault
  -> install to local runtimes
  -> use short commands to invoke assets
```

工作方式：Agent Foundry 是本地优先的系统，并区分 Core、User Vault、runtime 三层。public Core checkout 保存 workflows、schemas、scripts、templates、docs 和 adapter profiles。canonical practices、assets、indexes、imports 和共享 usage aggregate 存在选中的 User Vault。`~/.claude`、`~/.codex`、`~/.hermes`、`~/.trae-cn` 下的文件是下游副本。

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

On a new machine, see `docs/deployment.md` for the current split Core/Vault install flow. A clean public Core checkout needs a selected User Vault before canonical harvest, review, publish, or install workflows can operate. The Vault may be blank, restored from a private backup, or later populated through a reviewed capability pack.

The short version:

```bash
python3 scripts/init_vault.py ~/.agent-foundry/vault/my-agent-foundry-vault --core-root . --apply
python3 scripts/foundry_config.py write --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
python3 scripts/foundry_config.py status
python3 scripts/runtime_manifest.py init
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py enable claude-code   # or codex, hermes, trae
python3 scripts/runtime_manifest.py plan
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
python3 scripts/install_foundry.py --apply   # only after reviewing the dry-run/status output
python3 scripts/sync_status.py
```

新机器安装参见 `docs/deployment.md`。public Core checkout 不是 canonical Vault；先初始化或选择 User Vault，并写入 `~/.agent-foundry/config.yaml` 后，再执行 publish/install 类操作。

Do not copy another machine's `runtime/local/`, `~/.agent-foundry/config.yaml`, `~/.codex`, `~/.claude`, `~/.hermes`, `~/.trae-cn`, or ChatGPT project files as canonical truth. Recreate local state from Core plus the selected Vault, then verify with `sync_status.py`.

不要把另一台机器的 `runtime/local/`、`~/.agent-foundry/config.yaml`、`~/.codex`、`~/.claude`、`~/.hermes`、`~/.trae-cn` 或 ChatGPT project 文件当作 canonical truth 直接复制。应从 Core 加 selected Vault 重新生成本机状态，再用 `sync_status.py` 验证。

---

## Daily Workflow

Start your day with **`refresh practices and assets`** (or `刷新practices和assets`) when you want the agent to pull remote updates, regenerate adapters if needed, and install to enabled local runtimes.

每天需要更新本地 agent rules 时，用 **`refresh practices and assets`**（或 `刷新practices和assets`）。它会拉取远程更新，检查 adapters 是否需要重新生成，并安装到已启用的本地 agent runtime。

Use **`check Agent Foundry status`** (or run `python3 scripts/sync_status.py`) when you only need a read-only answer to "is this machine current?"

只想知道“这台机器现在是否是最新状态”时，用 **`check Agent Foundry status`**，或直接运行 `python3 scripts/sync_status.py`。它不会写文件。

Use the status path:

- at the start of a session after a long idle period;
- after switching machines or Core checkouts;
- when a practice or asset seems not to affect Codex, Claude Code, Hermes, Trae, or ChatGPT;
- before `install_foundry.py --apply` or any runtime write;
- after a runtime install to confirm receipts and manual targets.

建议在这些场景先走 status：

- 长时间不用后开始工作；
- 换机器或切换 Core checkout 后；
- 感觉 practice 或 asset 没有在 Codex、Claude Code、Hermes、Trae 或 ChatGPT 生效时；
- 执行 `install_foundry.py --apply` 或任何 runtime 写入前；
- runtime install 后确认 receipt 和 manual target 状态。

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

### Reading Status Output

`sync_status.py` separates the layers that often get confused:

- Core repo progress: whether this checkout is current, behind, ahead, or diverged.
- selected Vault: the canonical practices/assets source for this machine.
- generated output: adapter files produced from the selected Vault.
- runtime receipt: what generated output was installed to local runtimes.
- manual targets: ChatGPT remains manual import.
- human-gated runtime writes: Trae managed runtime writes require durable human approval before apply.

If generated output is missing or stale, publish adapters first. If the receipt is missing, review generated output and dry-run install before applying. If receipt status is selected-output drift, review the drift, regenerate generated output if needed, dry-run install, then apply only after the runtime write is expected. Do not repair runtime drift by editing Vault records.

`sync_status.py` 会分开报告容易混淆的层：

- Core repo progress：当前 checkout 是否 current、behind、ahead 或 diverged。
- selected Vault：这台机器选中的 canonical practices/assets 来源。
- generated output：从 selected Vault 生成的 adapter 文件。
- runtime receipt：哪些 generated output 被安装到了本地 runtime。
- manual targets：ChatGPT 仍然是 manual import。
- human-gated runtime writes：Trae managed runtime 写入需要 durable human approval 后才能 apply。

如果 generated output missing 或 stale，先 publish adapters。如果 receipt missing，先 review generated output 并 dry-run install。 如果 receipt 是 selected-output drift，先 review drift，必要时 regenerate generated output，再 dry-run install，确认 runtime write 后再 apply。不要通过编辑 Vault records 来修 runtime drift。

---

## Capability Pack Safety

Capability packs are reviewed bundles that can add or change practices, assets, generated output, and runtime-facing behavior. Treat them as higher risk than an ordinary status check.

Use plan commands before apply commands:

```bash
python3 scripts/plan_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/apply_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/manage_capability_pack_lifecycle.py --vault-root <vault-root> --pack-id <pack-id> --action disable
```

The pack path is fail-closed. If metadata is malformed, duplicated, ambiguous, has a same-version hash mismatch, points outside allowed paths, or would overwrite local edits without a reviewed update flow, the system should refuse before writing Vault or runtime files.

Capability pack lifecycle changes affect canonical Vault records and generated output; runtime files still need the normal publish, dry-run install, status, and reviewed apply path. ChatGPT remains manual import.

Capability pack 是经过 review 的 bundle，可能影响 practices、assets、generated output 和 runtime-facing 行为，风险高于普通 status check。

先 plan，再 apply：

```bash
python3 scripts/plan_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/apply_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/manage_capability_pack_lifecycle.py --vault-root <vault-root> --pack-id <pack-id> --action disable
```

Pack 路径是 fail-closed 的：metadata malformed、duplicated、ambiguous、same-version hash mismatch、路径越界，或需要未 review 的 update flow 时，系统应在写 Vault 或 runtime 文件前拒绝。

Capability pack lifecycle 会影响 canonical Vault records 和 generated output；runtime 文件仍然要走 publish、dry-run install、status、reviewed apply。ChatGPT 仍然是 manual import。

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
