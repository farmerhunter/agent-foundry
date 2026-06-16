# Short Commands / 短命令

Use these short commands in day-to-day agent work.

日常使用时直接说这些短命令即可。

## Commands / 命令

| Command | 中文 | Meaning / 说明 |
|---|---|---|
| `harvest practices` | `做一次 harvest practice` | Extract reusable practices from the current session and show a review list.<br>从当前 session 提炼可复用 practice，并展示 review list。 |
| `discover assets` | `发现可打包资产` | Find repeated workflows that should become skills, subagents, automations, or extensions.<br>发现值得沉淀为 skill、subagent、automation 或扩展项的重复 workflow。 |
| `import skill <source>` | `导入这个 skill <source>` | Evaluate an external skill, repo, prompt pack, article, or local folder.<br>评估外部 skill、repo、prompt pack、文章或本地目录。 |
| `publish practices` | `发布 practices` | Publish adapters from current active practices. Usually not needed manually.<br>从当前 active practices 发布 adapters；通常不需要手动执行。 |
| `check operation context` | `检查操作上下文` | Show the current Agent Foundry Core/Vault/evidence/runtime context before writes.<br>在写入前显示当前 Agent Foundry Core/Vault/evidence/runtime 上下文。 |
| `check Agent Foundry status` | `检查 Agent Foundry 状态` | Run a read-only status pass for Core, selected Vault, generated output, runtime receipts, and manual targets.<br>对 Core、selected Vault、generated output、runtime receipts 和 manual targets 做 read-only status 检查。 |
| `check adapter drift` | `检查 adapter drift` | Inspect whether generated output or installed runtime files are stale before applying changes.<br>在 apply 前检查 generated output 或已安装 runtime files 是否 stale。 |
| `restore Agent Foundry on this machine` | `在这台机器恢复 Agent Foundry` | Recreate local config, generated output, and runtime install state from Core plus the selected Vault.<br>从 Core 加 selected Vault 重建本机 local config、generated output 和 runtime install state。 |
| `review practices` | `review practices` / `检查 skill rot` | Review the practice repo for duplicates, stale entries, weak or missed activation, and adapter drift.<br>检查 practice repo 中的重复项、过期项、弱激活/漏激活和 adapter drift。 |
| `review assets` | `review assets` / `检查 asset rot` | Review reusable assets for usage, overlap, stale triggers, and adapter coverage.<br>检查 reusable assets 的使用情况、重叠、过期 trigger 和 adapter 覆盖。 |
| `refresh practices and assets` | `刷新practices和assets` | Pull remote updates, conditionally publish adapters, and install to local runtimes.<br>拉取远端更新，必要时发布 adapters，并安装到本地 runtimes。 |

## Direct Status Command / 直接状态命令

When you are not sure whether local agent rules are current, ask an agent to run the status command or run it yourself:

当你不确定本机 agent rules 是否最新时，可以让 agent 运行 status command，也可以自己执行：

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
