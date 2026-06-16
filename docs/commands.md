# Short Commands

Use these short commands in day-to-day agent work.

日常使用时直接说这些短命令即可。

## Commands

| Command | 中文 | Meaning |
|---|---|---|
| `harvest practices` | `做一次 harvest practice` | Extract reusable practices from the current session and show a review list. |
| `discover assets` | `发现可打包资产` | Find repeated workflows that should become skills, subagents, automations, or extensions. |
| `import skill <source>` | `导入这个 skill <source>` | Evaluate an external skill, repo, prompt pack, article, or local folder. |
| `publish practices` | `发布 practices` | Publish adapters from current active practices. Usually not needed manually. |
| `check operation context` | `检查操作上下文` | Show the current Agent Foundry Core/Vault/evidence/runtime context before writes. |
| `check Agent Foundry status` | `检查 Agent Foundry 状态` | Run a read-only status pass for Core, selected Vault, generated output, runtime receipts, and manual targets. |
| `check adapter drift` | `检查 adapter drift` | Inspect whether generated output or installed runtime files are stale before applying changes. |
| `restore Agent Foundry on this machine` | `在这台机器恢复 Agent Foundry` | Recreate local config, generated output, and runtime install state from Core plus the selected Vault. |
| `review practices` | `review practices` / `检查 skill rot` | Review the practice repo for duplicates, stale entries, weak or missed activation, and adapter drift. |
| `review assets` | `review assets` / `检查 asset rot` | Review reusable assets for usage, overlap, stale triggers, and adapter coverage. |
| `refresh practices and assets` | `刷新practices和assets` | Pull remote updates, conditionally publish adapters, and install to local runtimes. |

## Direct Status Command

When you are not sure whether local agent rules are current, ask an agent to run the status command or run it yourself:

```bash
python3 scripts/sync_status.py
```

Use it at the start of a session, after a long idle period, after switching machines, or before applying runtime writes. It is read-only: it reports Core progress, selected Vault/generated output freshness, runtime receipt state, manual targets such as ChatGPT, and next safe actions.

## Approval

After `harvest practices`, `discover assets`, or `import skill`, approve by number:

```text
I approve 1 and 3.
```

or:

```text
我批准第 1 和第 3 条。
```

After approval, the agent should apply the approved items and publish relevant adapters automatically.
