# Short Commands / 短命令

Use these short commands in day-to-day agent work.

日常使用时直接说这些短命令即可。

## Ordinary User Intents / 普通用户意图

Start here for daily operation. Say the intent to the agent; the agent should map it to the reviewed workflow and show the visible outcome before durable changes.

日常操作从这里开始。直接把意图告诉 agent；agent 应把它映射到 reviewed workflow，并在 durable changes 前展示可见结果。

| Command | 中文 | Meaning / 说明 |
|---|---|---|
| `harvest practices` | `做一次 harvest practice` | Extract reusable practices from the current session and show a review list.<br>从当前 session 提炼可复用 practice，并展示 review list。 |
| `discover assets` | `发现可打包资产` | Find repeated workflows that should become skills, subagents, automations, or extensions.<br>发现值得沉淀为 skill、subagent、automation 或扩展项的重复 workflow。 |
| `refresh practices and assets` | `刷新practices和assets` | Pull remote updates, conditionally publish adapters, and install to local runtimes through the reviewed path.<br>拉取远端更新，必要时发布 adapters，并通过 reviewed path 安装到本地 runtimes。 |
| `check Agent Foundry status` | `检查 Agent Foundry 状态` | Run a read-only status pass for Core, selected Vault, generated output, runtime receipts, and manual targets.<br>对 Core、selected Vault、generated output、runtime receipts 和 manual targets 做 read-only status 检查。 |
| `review practices` | `review practices` / `检查 skill rot` | Review practices for duplicates, stale entries, weak or missed activation, and adapter drift.<br>检查 practices 中的重复项、过期项、弱激活/漏激活和 adapter drift。 |
| `review assets` | `review assets` / `检查 asset rot` | Review reusable assets for usage, overlap, stale triggers, and adapter coverage.<br>检查 reusable assets 的使用情况、重叠、过期 trigger 和 adapter 覆盖。 |

## Normal Capability-Pack Consumption / 普通 Capability Pack 使用

These requests consume reviewed packs. They do not create packs, run candidate discovery, export, publish, split, merge, or deploy runtime files by themselves.

这些请求用于使用 reviewed packs。它们本身不会创建 packs、运行 candidate discovery、export、publish、split、merge 或 deploy runtime files。

| Command | 中文 | Meaning / 说明 |
|---|---|---|
| `list capability packs` | `列出 capability packs` | Show reviewed or deployed packs and their display status without changing lifecycle state.<br>列出 reviewed 或 deployed packs 及 display status，不改变 lifecycle state。 |
| `recommend capability packs for my setup` | `推荐适合当前环境的 capability packs` | Recommend reviewed packs using compatibility, availability, generated output, and runtime status as display/report signals only.<br>根据 compatibility、availability、generated output 和 runtime status 推荐 reviewed packs；这些只是 display/report signals。 |
| `preview capability pack deployment <path>` | `预览 capability pack 部署 <路径>` | Plan selected Vault impact and review gates before any apply.<br>在任何 apply 前预览 selected Vault 影响和 review gates。 |
| `apply reviewed capability pack <path>` | `应用已 review 的 capability pack <路径>` | Apply only after the reviewed plan and required human gates are accepted; generated/runtime follow-up stays separate.<br>仅在 reviewed plan 和必要 human gate 被接受后 apply；generated/runtime 后续步骤保持分离。 |
| `verify capability pack <pack-id>` | `验证 capability pack <pack-id>` | Read pack metadata, selected Vault impact, generated output, runtime receipts, and manual target state before declaring the pack usable.<br>读取 pack metadata、selected Vault 影响、generated output、runtime receipts 和 manual target state，再判断 pack 是否可用。 |
| `update capability pack <pack-id-or-path>` | `更新 capability pack <pack-id-or-path>` | Compare a reviewed newer pack against deployed metadata and local edits; report clean update, merge required, blocked, or unsupported before writes.<br>把 reviewed newer pack 与 deployed metadata 和本地改动比较；写入前报告 clean update、merge required、blocked 或 unsupported。 |
| `disable capability pack <pack-id>` | `停用 capability pack <pack-id>` | Produce a dry-run lifecycle/rollback plan first; do not delete records or mutate runtime files silently.<br>先生成 dry-run lifecycle/rollback plan；不要静默删除 records 或修改 runtime files。 |

## Advanced Maintenance And Debug / 高级维护与 Debug

The commands below are secondary. Use them when you explicitly need power-user maintenance, transfer review, runtime repair, import review, or deterministic CLI/debug evidence.

下面的命令是 secondary。只有在你明确需要 power-user maintenance、transfer review、runtime repair、import review 或 deterministic CLI/debug evidence 时再使用。

For complete reference material, use the complete/power-user reference map in [Usage](usage.md), [Deployment](deployment.md), and the relevant workflow docs. Do not treat this section as the beginner or ordinary-user first path.

完整 reference material 请看 [Usage](usage.md) 中的 complete/power-user reference map、[Deployment](deployment.md) 和相关 workflow docs。不要把本节当作 beginner 或 ordinary-user first path。

| Command | 中文 | Meaning / 说明 |
|---|---|---|
| `discover capability packs` | `发现 capability pack` | Power-user diagnostic flow: find higher-level reusable capability bundles and produce candidates only.<br>power-user diagnostic flow：发现更高层的 reusable capability bundle；只产出 candidates。 |
| `evaluate capability pack <path>` | `评估 capability pack <路径>` | Inspect a pack or candidate boundary, false positives, privacy risks, and next reviewer without activating it.<br>检查 pack 或 candidate 的边界、false positive、隐私风险和下一位 reviewer，不激活。 |
| `scan capability pack candidate boundaries` | `扫描 capability pack candidate 边界` | Advanced maintenance flow: scan evidence for candidate boundaries and produce a review packet only.<br>advanced maintenance flow：扫描 evidence 中的 candidate boundaries，只产出 review packet。 |
| `assemble capability pack draft <candidate-id>` | `组装 capability pack draft <candidate-id>` | Advanced maintenance flow: assemble a draft proposal for review without creating, activating, exporting, publishing, or deploying a pack.<br>advanced maintenance flow：组装供 review 的 draft proposal，不创建、激活、export、publish 或 deploy pack。 |
| `review capability pack release <pack-id-or-path>` | `review capability pack release <pack-id-or-path>` | Advanced maintenance flow: review version, taxonomy, compatibility, distribution, and release gates before any later apply step.<br>advanced maintenance flow：在任何后续 apply 前 review version、taxonomy、compatibility、distribution 和 release gates。 |
| `review capability pack exportability <pack-id-or-path>` | `review capability pack exportability <pack-id-or-path>` | Advanced maintenance flow: review privacy and distribution readiness without exporting private Vault data.<br>advanced maintenance flow：review privacy 和 distribution readiness，不 export private Vault data。 |
| `review capability pack deprecation <pack-id>` | `review capability pack deprecation <pack-id>` | Advanced maintenance flow: review replacement, rationale, affected records, and downstream follow-up before deprecation.<br>advanced maintenance flow：在 deprecation 前 review replacement、rationale、affected records 和 downstream follow-up。 |
| `review capability pack split or merge <pack-id>` | `review capability pack split 或 merge <pack-id>` | Advanced maintenance flow: propose split/merge outcomes, membership diffs, and gates as a review packet only.<br>advanced maintenance flow：以 review packet 形式提出 split/merge outcomes、membership diffs 和 gates。 |
| `review capability pack lifecycle <pack-id>` | `review capability pack lifecycle <pack-id>` | Dry-run lifecycle transitions such as activate, exportable, split, merge, deprecate, disable, or retire.<br>dry-run 检查 activate、exportable、split、merge、deprecate、disable、retire 等 lifecycle transition。 |
| `preview capability pack transfer <path>` | `预览 capability pack transfer <路径>` | Validate export/import transfer material with privacy-safe, writes-none checks.<br>用 privacy-safe、writes-none 检查验证 export/import transfer material。 |
| `import skill <source>` | `导入这个 skill <source>` | Evaluate an external skill, repo, prompt pack, article, or local folder.<br>评估外部 skill、repo、prompt pack、文章或本地目录。 |
| `publish practices` | `发布 practices` | Publish adapters from current active practices. Usually not needed manually.<br>从当前 active practices 发布 adapters；通常不需要手动执行。 |
| `check operation context` | `检查操作上下文` | Show the current Agent Foundry Core/Vault/evidence/runtime context before writes.<br>在写入前显示当前 Agent Foundry Core/Vault/evidence/runtime 上下文。 |
| `check adapter drift` | `检查 adapter drift` | Inspect whether generated output or installed runtime files are stale before applying changes.<br>在 apply 前检查 generated output 或已安装 runtime files 是否 stale。 |
| `restore Agent Foundry on this machine` | `在这台机器恢复 Agent Foundry` | Recreate local config, generated output, and runtime install state from Core plus the selected Vault.<br>从 Core 加 selected Vault 重建本机 local config、generated output 和 runtime install state。 |

## Direct Status Command / 直接状态命令

When you are not sure whether local agent rules are current, first ask an agent `check Agent Foundry status`. If you need the direct CLI fallback, run:

当你不确定本机 agent rules 是否最新时，先让 agent 执行 `check Agent Foundry status`。如果需要直接 CLI fallback，再运行：

```bash
python3 scripts/sync_status.py
```

Use it at the start of a session, after a long idle period, after switching machines, or before applying runtime writes. It is read-only: it reports Core progress, selected Vault/generated output freshness, runtime receipt state, manual targets such as ChatGPT, and next safe actions.

建议在 session 开始、长时间 idle 后、切换机器后，或执行 runtime writes 前运行它。它是 read-only：会报告 Core progress、selected Vault/generated output freshness、runtime receipt state、ChatGPT 等 manual targets，以及 next safe actions。

## Approval / 批准

After `harvest practices`, `discover assets`, or `import skill`, approve by number:

在 `harvest practices`、`discover assets` 或 `import skill` 之后，按编号批准：

```text
I approve 1 and 3.
```

or:

```text
我批准第 1 和第 3 条。
```

After approval, the agent should apply the approved items and publish relevant adapters automatically.

批准后，agent 应自动应用已批准项目，并发布相关 adapters。
