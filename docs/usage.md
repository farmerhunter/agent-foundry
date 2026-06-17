# Usage Guide / 使用指南

This guide is for day-to-day Agent Foundry use. You do not need to remember the internal workflows.

这份指南面向日常使用 Agent Foundry 的场景。你不需要记住内部 workflow 细节。

## How It Works / 工作方式

Agent Foundry is a local-first system with separate Core, selected User Vault, generated output, and runtime layers.

Agent Foundry 是 local-first 系统，并区分 Core、selected User Vault、generated output 和 runtime layers。

```text
work session or external skill
  -> harvest / import / discover
  -> human approval
  -> canonical practice or asset in selected User Vault
  -> publish adapters from Core plus selected Vault
  -> install to local runtimes
  -> use short commands to invoke assets
```

Core contains public workflows, schemas, scripts, templates, docs, adapter profiles, runtime templates, and validation tooling.

Core 保存 public workflows、schemas、scripts、templates、docs、adapter profiles、runtime templates 和 validation tooling。

The selected User Vault contains canonical `practices/`, `assets/`, `indexes/`, `imports/`, and shared sanitized usage aggregates.

selected User Vault 保存 canonical `practices/`、`assets/`、`indexes/`、`imports/` 和 shared sanitized usage aggregates。

Installed files under `~/.codex`, `~/.claude`, `~/.hermes`, and `~/.trae-cn` are downstream runtime copies.

`~/.codex`、`~/.claude`、`~/.hermes` 和 `~/.trae-cn` 下的已安装文件是下游 runtime copies。

## Core Rule / 核心规则

For daily use, prefer the short commands in `docs/commands.md`, such as `harvest practices`, `refresh practices and assets`, or `check Agent Foundry status`.

日常使用时，优先使用 `docs/commands.md` 中的短命令，例如 `harvest practices`、`refresh practices and assets` 或 `check Agent Foundry status`。

The agent may discover, draft, and recommend practices or assets. You approve each meaningful new item or change before it becomes active.

Agent 可以发现、起草并推荐 practices 或 assets。每个重要新增项或变更都需要你批准后才能 active。

After approval, the agent should apply the approved item, update the canonical Vault records, update indexes, publish relevant adapters, and report changed files.

批准后，agent 应应用已批准项目，更新 canonical Vault records，更新 indexes，发布相关 adapters，并汇报 changed files。

## First-Time Setup / 首次设置

On a new machine, use `docs/deployment.md` for the full split Core/Vault install flow.

新机器上，使用 `docs/deployment.md` 中完整的 Core/Vault 分离安装流程。

Short version:

简版流程：

```bash
python3 scripts/init_vault.py ~/.agent-foundry/vault/my-agent-foundry-vault --core-root . --apply
python3 scripts/foundry_config.py write --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
python3 scripts/foundry_config.py status
python3 scripts/runtime_manifest.py init
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py enable codex       # or claude-code, hermes, trae
python3 scripts/runtime_manifest.py plan
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
python3 scripts/install_foundry.py --apply             # only after reviewing dry-run/status output
python3 scripts/sync_status.py
```

Do not copy another machine's `runtime/local/`, `~/.agent-foundry/config.yaml`, runtime directories, or ChatGPT project files as canonical truth.

不要把另一台机器的 `runtime/local/`、`~/.agent-foundry/config.yaml`、runtime directories 或 ChatGPT project files 当作 canonical truth 复制。

Recreate local state from Core plus the selected Vault, then verify with `sync_status.py`.

应从 Core 加 selected Vault 重建本机状态，再用 `sync_status.py` 验证。

## Daily Workflow / 日常流程

Use `refresh practices and assets` at the start of a session, after switching machines, or when local agent rules may be stale.

在 session 开始、切换机器后，或本地 agent rules 可能 stale 时，使用 `refresh practices and assets`。

Use `check Agent Foundry status` or `python3 scripts/sync_status.py` when you only need a read-only answer to whether this machine is current.

只需要 read-only 检查这台机器是否 current 时，使用 `check Agent Foundry status` 或 `python3 scripts/sync_status.py`。

Use `harvest practices` after a session when you want to preserve reusable lessons.

想在一次 session 后沉淀可复用经验时，使用 `harvest practices`。

Use `discover assets` when repeated manual work should become a reusable skill, subagent, automation, or extension.

发现重复手工工作值得变成 reusable skill、subagent、automation 或 extension 时，使用 `discover assets`。

Use `review practices` and `review assets` periodically to prevent skill rot and asset rot.

定期使用 `review practices` 和 `review assets`，避免 skill rot 和 asset rot。

## Refresh Practices And Assets / 刷新 Practices 和 Assets

Command:

命令：

```text
refresh practices and assets
刷新practices和assets
```

Expected behavior:

预期行为：

- Check local state and avoid losing real work.
- 检查本地状态，避免丢失真实工作。
- Pull remote git updates when appropriate.
- 在合适时 pull remote git updates。
- Regenerate adapters if canonical practices or assets changed.
- 如果 canonical practices 或 assets 发生变化，重新生成 adapters。
- Dry-run or install to enabled local runtimes through the reviewed path.
- 通过 reviewed path 对 enabled local runtimes 做 dry-run 或 install。
- Report current commit, unpushed work, generated output state, runtime receipts, and updated runtimes.
- 汇报 current commit、未 push 工作、generated output state、runtime receipts 和已更新 runtimes。

## Status And Drift / Status 和 Drift

Run status before applying runtime writes, after long idle periods, after switching machines, or when a rule appears not to affect an agent.

在 apply runtime writes 前、长时间 idle 后、切换机器后，或某条 rule 看起来没有影响 agent 时，运行 status。

```bash
python3 scripts/sync_status.py
```

`sync_status.py` separates Core repo progress, selected Vault state, generated output, runtime receipt state, manual targets, and human-gated runtime writes.

`sync_status.py` 会分开报告 Core repo progress、selected Vault state、generated output、runtime receipt state、manual targets 和 human-gated runtime writes。

If generated output is missing or stale, publish adapters first. If runtime receipt is missing or drifted, review generated output, run install dry-run, read status, then apply only when the runtime write is expected.

如果 generated output missing 或 stale，先 publish adapters。如果 runtime receipt missing 或 drifted，先 review generated output，运行 install dry-run，读取 status，最后只有 runtime write 符合预期时才 apply。

Do not repair runtime drift by editing Vault records.

不要通过编辑 Vault records 来修复 runtime drift。

## Capability Pack Safety / Capability Pack 安全规则

Capability packs are reviewed bundles that can add or change practices, assets, generated output, and runtime-facing behavior.

Capability packs 是经过 review 的 bundles，可能新增或改变 practices、assets、generated output 和 runtime-facing behavior。

Use Skill-first requests for normal work:

正常工作优先使用 Skill-first 请求：

```text
discover capability packs
evaluate capability pack <pack-path>
preview capability pack deployment <pack-path>
apply reviewed capability pack <pack-path>
review capability pack lifecycle <pack-id>
preview capability pack transfer <pack-path>
```

These requests route through the relevant Agent Foundry workflows, preserve review gates, and keep raw scripts as implementation details or advanced/debug commands.

这些请求会路由到对应的 Agent Foundry workflows，保留 review gates，并把 raw scripts 作为 implementation details 或 advanced/debug commands。

Use plan commands before apply commands when operating manually or debugging:

手动操作或 debug 时，先使用 plan commands，再使用 apply commands：

```bash
python3 scripts/plan_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/apply_capability_pack.py <pack-path> --vault-root <vault-root>
python3 scripts/manage_capability_pack_lifecycle.py --vault-root <vault-root> --pack-id <pack-id> --action disable
```

The pack path is fail-closed. If metadata is malformed, duplicated, ambiguous, has a same-version hash mismatch, points outside allowed paths, or would overwrite local edits without a reviewed update flow, the system should refuse before writing Vault or runtime files.

Pack path 是 fail-closed 的。如果 metadata malformed、duplicated、ambiguous、出现 same-version hash mismatch、路径越界，或会在没有 reviewed update flow 的情况下覆盖本地改动，系统应在写 Vault 或 runtime files 前拒绝。

Runtime files still need the normal publish, dry-run install, status, and reviewed apply path. ChatGPT remains manual import.

Runtime files 仍然需要走正常的 publish、dry-run install、status 和 reviewed apply path。ChatGPT 仍然是 manual import。

## Harvest Practices / 沉淀 Practices

Use this after coding, design, debugging, or coordination work when reusable lessons should become durable practices.

在 coding、design、debugging 或 coordination 工作后，如果有可复用经验需要变成 durable practices，使用此流程。

Command:

命令：

```text
harvest practices
做一次 harvest practice
```

Long prompt:

较完整的 prompt：

```text
Harvest reusable practices from this session using Agent Foundry. Keep the details hidden and present a concise review list. For each new or changed practice, show the title, why it matters, whether it merges into an existing rule or creates a new one, and what adapters would be updated after approval. Wait for my approval per practice before applying.

用 Agent Foundry 从这次 session 中提炼可复用实践。隐藏内部细节，只给我一个简洁的 review list。对每条新增或变更的 practice，说明标题、为什么重要、会合并到已有规则还是创建新规则，以及批准后会更新哪些 adapters。每条 practice 等我批准后再应用。
```

Approval example:

批准示例：

```text
I approve practice 1 and 3. Apply them, promote them to active, update the index, and publish the relevant adapters.

我批准第 1 和第 3 条。请应用它们，提升为 active，更新 index，并发布相关 adapters。
```

## Import External Skills / 导入外部 Skills

Use this when you find a useful public skill, prompt pack, article, repo, or local skill folder.

发现有价值的 public skill、prompt pack、article、repo 或本地 skill folder 时，使用此流程。

Prompt:

Prompt：

```text
Evaluate this external skill for Agent Foundry: <URL or local path>. Use the import workflow, but keep the report concise. Show provenance, license/security concerns, useful candidate practices, duplicates found, and what would be imported after approval. Do not activate or publish anything until I approve each candidate.

请评估这个外部 skill 是否适合加入 Agent Foundry：<URL 或 local path>。使用 import workflow，但报告保持简洁。展示 provenance、license/security concerns、有价值的 candidate practices、duplicates found，以及批准后会导入什么。每个 candidate 未经我批准前不要 activate 或 publish。
```

Approval example:

批准示例：

```text
I approve candidate 2. Import it, promote it to active, update the index, and publish the relevant adapters.

我批准第 2 个 candidate。请导入它，提升为 active，更新 index，并发布相关 adapters。
```

## Discover Assets / 发现 Assets

Use this when repeated workflows should become reusable assets such as skills, subagents, automations, or extensions of existing assets.

当重复 workflows 应沉淀为 skills、subagents、automations 或已有 assets 的 extensions 时，使用此流程。

Command:

命令：

```text
discover assets
发现可打包资产
```

Approval example:

批准示例：

```text
I approve asset candidate 1. Create or extend the asset, update the asset index, and publish relevant adapters.

我批准第 1 个 asset candidate。请创建或扩展该 asset，更新 asset index，并发布相关 adapters。
```

## Review Practices / Review Practices

Use this periodically to prevent duplicated, stale, weak, or missed practice activation.

定期使用此流程，避免 duplicated、stale、weak 或 missed practice activation。

Prompt:

Prompt：

```text
Review Agent Foundry for skill rot. Run the practice review workflow, summarize the recommendations, and give me an approval list. Look for duplicates, stale entries, weak or missed activation, adapter drift, and proposed items that need decisions. Do not archive, supersede, change activation tiers, or publish anything without my approval.

请 review Agent Foundry，检查 skill rot。执行 practice review workflow，总结 recommendations，并给我一个可批准的清单。重点看 duplicates、stale entries、weak or missed activation、adapter drift，以及需要决策的 proposed items。未经我批准，不要 archive、supersede、修改 activation tiers 或 publish。
```

## Review Assets / Review Assets

Use this periodically to prevent unused skills, overlapping subagents, stale automations, weak triggers, or missing adapter coverage.

定期使用此流程，避免 unused skills、overlapping subagents、stale automations、weak triggers 或 missing adapter coverage。

Command:

命令：

```text
review assets
检查 asset rot
```

## Consistency Checks / Consistency Checks

If something feels off, run the consistency checker manually:

如果感觉状态不对，可以手动运行 consistency checker：

```bash
python3 scripts/check_consistency.py
```

It validates indexes, practice frontmatter, asset fields, cross-references, adapter ID references, and runtime manifest integrity.

它会验证 indexes、practice frontmatter、asset fields、cross-references、adapter ID references 和 runtime manifest integrity。

## Approval Style / 批准方式

Prefer approving by numbered items:

优先按编号批准：

```text
I approve 1, 3, and 4.

我批准第 1、3、4 条。
```

The agent should apply only approved practices or assets and publish relevant adapters automatically.

Agent 应只应用已批准的 practices 或 assets，并自动发布相关 adapters。

## What You Should See / 你应该看到什么

For harvest, import, discover, or review flows, the agent should show a compact review list.

对于 harvest、import、discover 或 review flows，agent 应展示简洁的 review list。

Example:

示例：

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

The agent should not force you to read the full internal workflow unless you ask.

除非你要求，agent 不应强迫你阅读完整内部 workflow。
