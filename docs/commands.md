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
| `review practices` | `review practices` / `检查 skill rot` | Review the practice repo for duplicates, stale entries, weak rules, and adapter drift. |
| `review assets` | `review assets` / `检查 asset rot` | Review reusable assets for usage, overlap, stale triggers, and adapter coverage. |

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
