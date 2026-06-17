# Short Commands

Canonical source: `docs/commands.md`

Use these short commands:

| Command | 中文 | Meaning |
|---|---|---|
| `harvest practices` | `做一次 harvest practice` | Extract reusable practices from the current session and show a review list. |
| `discover capability packs` | `发现 capability pack` | Find higher-level reusable capability bundles from repeated practice, asset, workflow, and adapter evidence. Produces candidates only. |
| `evaluate capability pack <path>` | `评估 capability pack <路径>` | Inspect a pack or candidate boundary, false positives, privacy risks, and next reviewer without activating it. |
| `preview capability pack deployment <path>` | `预览 capability pack 部署 <路径>` | Plan selected Vault impact and review gates before any apply. |
| `apply reviewed capability pack <path>` | `应用已 review 的 capability pack <路径>` | Apply only after the reviewed plan and required human gates are accepted; generated/runtime follow-up stays separate. |
| `review capability pack lifecycle <pack-id>` | `review capability pack lifecycle <pack-id>` | Dry-run lifecycle transitions such as activate, exportable, split, merge, deprecate, disable, or retire. |
| `preview capability pack transfer <path>` | `预览 capability pack transfer <路径>` | Validate export/import transfer material with privacy-safe, writes-none checks. |
| `import skill <source>` | `导入这个 skill <source>` | Evaluate an external skill, repo, prompt pack, article, or local folder. |
| `publish practices` | `发布 practices` | Publish adapters from current active practices. Usually not needed manually. |
| `review practices` | `检查 skill rot` | Review the practice repo for duplicates, stale entries, weak or missed activation, and adapter drift. |
| `refresh practices and assets` | `刷新practices和assets` | Pull remote updates, conditionally publish adapters, and install to local runtimes. |

After approval, apply approved items and publish relevant adapters automatically.
