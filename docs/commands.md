# Short Commands

Use these short commands in day-to-day agent work. English command text is canonical; Chinese triggers are convenience prompts for the same workflow.

**中文要点：** 英文命令是 canonical；中文触发语只是方便日常使用。

## Commands

| Command | 中文触发 | Use |
| --- | --- | --- |
| `harvest practices` | `做一次 harvest practice` | Extract reusable practices from the current session and show a review list. |
| `discover assets` | `发现可打包资产` | Find repeated workflows that should become skills, subagents, automations, or extensions. |
| `discover capability packs` | `发现 capability pack` | Find higher-level reusable capability bundles from repeated practice, asset, workflow, and adapter evidence; candidates only. |
| `evaluate capability pack <path>` | `评估 capability pack <路径>` | Inspect pack or candidate boundaries, false positives, privacy risks, and next reviewer without activating it. |
| `scan capability pack candidate boundaries` | `扫描 capability pack candidate 边界` | Advanced maintenance flow: scan evidence for candidate boundaries and produce a review packet only. |
| `assemble capability pack draft <candidate-id>` | `组装 capability pack draft <candidate-id>` | Advanced maintenance flow: assemble a draft proposal without creating, activating, exporting, publishing, or deploying a pack. |
| `review capability pack release <pack-id-or-path>` | `review capability pack release <pack-id-or-path>` | Advanced maintenance flow: review version, taxonomy, compatibility, distribution, and release gates before any later apply step. |
| `review capability pack exportability <pack-id-or-path>` | `review capability pack exportability <pack-id-or-path>` | Advanced maintenance flow: review privacy and distribution readiness without exporting private Vault data. |
| `review capability pack deprecation <pack-id>` | `review capability pack deprecation <pack-id>` | Advanced maintenance flow: review replacement, rationale, affected records, and downstream follow-up before deprecation. |
| `review capability pack split or merge <pack-id>` | `review capability pack split 或 merge <pack-id>` | Advanced maintenance flow: propose split/merge outcomes, membership diffs, and gates as a review packet only. |
| `list capability packs` | `列出 capability packs` | Show reviewed or deployed packs, including official starter packs, and their display status without changing lifecycle state. |
| `recommend capability packs for my setup` | `推荐适合当前环境的 capability packs` | Recommend reviewed packs using compatibility, availability, generated output, and runtime status as report signals only. |
| `preview capability pack deployment <path>` | `预览 capability pack 部署 <路径>` | Plan selected Vault impact and review gates before any apply; preview reports `writes: none`. |
| `apply reviewed capability pack <path>` | `应用已 review 的 capability pack <路径>` | Apply only after the reviewed plan and required gates are accepted. Selected Vault is canonical; generated/runtime follow-up stays separate. |
| `verify capability pack <pack-id>` | `验证 capability pack <pack-id>` | Read pack metadata, selected Vault impact, generated output, runtime receipts, and manual target state before declaring the pack usable. |
| `update capability pack <pack-id-or-path>` | `更新 capability pack <pack-id-or-path>` | Compare a reviewed newer pack against deployed metadata and local edits; report clean update, merge required, blocked, or unsupported before writes. |
| `disable capability pack <pack-id>` | `停用 capability pack <pack-id>` | Produce a dry-run lifecycle/rollback plan first; do not delete selected Vault records or mutate runtime files silently. |
| `review capability pack lifecycle <pack-id>` | `review capability pack lifecycle <pack-id>` | Dry-run lifecycle transitions such as activate, exportable, split, merge, deprecate, disable, or retire. |
| `preview capability pack transfer <path>` | `预览 capability pack transfer <路径>` | Validate export/import transfer material with privacy-safe, writes-none checks. |
| `import skill <source>` | `导入这个 skill <source>` | Review an external skill, repo, prompt pack, article, or local folder and return one safe outcome before activation or publish. |
| `plan tester evidence for this change` | `为这个变更规划 tester evidence` | Ask for a Testing Contract and small test matrix before accepting risky user-visible, stateful, runtime, Vault, generated, import, or scheduler work. |
| `run tester pass for this issue` | `对这个 issue 做 tester pass` | Gather or verify agreed test evidence, then route to Reviewer, Implementer, Architect, or Human based on the result. |
| `check collaboration readiness for this repo` | `检查这个 repo 的 collaboration readiness` | Return readiness status, summary, and action plan from labels, routing config, contracts, issue/PR routing, and optional Project mirror state. |
| `prepare this repo for multi-agent collaboration` | `为这个 repo 准备 multi-agent collaboration` | Start a new-repo setup action plan: role labels, routing template, optional Project mirror options, contracts, human gates, residual risks, and next safe action. |
| `audit existing collaboration setup` | `审计现有 collaboration setup` | Review drift in an existing project and group next actions as informational, agent-handled, human-gated, or unsupported/deferred. Read-only. |
| `check branch readiness for this issue or PR` | `检查这个 issue 或 PR 的 branch readiness` | Explain `Branch strategy`, `Target branch`, PR base, local branch state, and safe next action concepts such as split, switch context, forward-merge, or multi-line verification. Read-only. |
| `show Foundry Board` | `显示 Foundry Board` | Render a read-only local-first board/report from accepted ledger replay first, with GitHub/Project as mirror drift evidence. It does not write GitHub, Project, ledger, runtime, or Vault state. |
| `show local collaboration ledger report` | `显示 local collaboration ledger report` | Replay local append-only ledger events from `usage/local/collaboration-ledger/` or a supplied test root into derived work-item state. Read-only; no GitHub dependency or write-back. |
| `preview existing project ledger backfill` | `预览 existing project ledger backfill` | Convert bounded existing GitHub-first issue/PR/comment/label/milestone/Project evidence into candidate local ledger events for review only. No authoritative migration or writes. |
| `preview GitHub Project sync plan` | `预览 GitHub Project sync plan` | Generate a dry-run Project mirror plan from ledger-backed board state with before/after values, conflicts, Human gates, and readback requirements. No Project/GitHub writes. |
| `publish practices` | `发布 practices` | Publish adapters from current active practices; usually not needed manually. |
| `check operation context` | `检查操作上下文` | Show current Agent Foundry Core/Vault/evidence/runtime context before writes. |
| `check Agent Foundry status` | `检查 Agent Foundry 状态` | Run a read-only status pass for Core, selected Vault, generated output, runtime receipts, and manual targets. |
| `check adapter drift` | `检查 adapter drift` | Inspect whether generated output or installed runtime files are stale before applying changes. |
| `restore Agent Foundry on this machine` | `在这台机器恢复 Agent Foundry` | Recreate local config, generated output, and runtime install state from Core plus the selected Vault. |
| `review practices` | `review practices` / `检查 skill rot` | Review practices for duplicates, stale entries, weak or missed activation, and adapter drift. |
| `review assets` | `review assets` / `检查 asset rot` | Review reusable assets for usage, overlap, stale triggers, and adapter coverage. |
| `refresh practices and assets` | `刷新practices和assets` | Pull remote updates, conditionally publish adapters, and install to local runtimes through the reviewed path. |

## Direct Status Command

When you are not sure whether local agent rules are current, ask an agent to run the status command or run it yourself:

```bash
python3 scripts/sync_status.py
```

Use it at the start of a session, after a long idle period, after switching machines, or before applying runtime writes. It is read-only and reports Core progress, selected Vault/generated output freshness, runtime receipt state, manual targets such as ChatGPT, and next safe actions.

**中文要点：** 不确定本机 rules 是否最新时，先跑 status。它只读，不会写 runtime/Vault/generated files。

## Approval

After `harvest practices`, `discover assets`, or `import skill`, approve by number:

```text
I approve 1 and 3.
我批准第 1 和第 3 条。
```

After approval, the agent should apply only the approved items. For `import skill`, `reference_only` means keep safe review evidence for lookup or later review; it is not active behavior. Adapter publishing happens only as a post-approval action after an approved canonical practice or asset exists.

**中文要点：** 按编号批准。`reference_only` 只是安全证据，不是 active behavior；adapter publish 只能发生在 approved canonical item 之后。
