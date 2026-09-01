# Optional Multi-Agent Collaboration Pack

中文（默认） | English summary below

`pack.multi-agent.optional` 为确实通过 GitHub Issues/PRs 分工的项目提供公开、可审阅的
bounded collaboration 与 role-dispatch 指导。它不是 scheduler、runtime installer 或
自动项目管理器。

## 0.5.0 实际内容

旧 0.4.0 虽然描述了大量能力，实际只携带两个示例 candidate。0.5.0 用当前已验收的真实
内容替换这种占位关系：

- practices：`COLLAB-001` 至 `COLLAB-017`；
- 最小直接依赖：`GOV-005`、`GOV-006`、`IMPL-001`、`PROD-002`、
  `TEST-001`、`TEST-004`、`TEST-005`；
- assets：`ASSET-COLLAB-001` 与 `ASSET-COLLAB-002`。

`META-004`、`META-005`、`GOV-002`、`GOV-004`、`RUNTIME-001` 和
`RUNTIME-003` 已由必需的 bootstrap pack 提供，因此不在 optional pack 中重复。
本包没有 executable payload。

这些内容支持普通 Issue/PR 交付、durable handoff、lean Execution Contract、review、
Epic/branch/workspace 判断，以及明确请求时的 role dispatch/onboarding 规划。它不会凭
pack 安装创建原生 threads、SQLite ledger、RoleHub、Project 状态或 runtime capability。

## 首次导入

先安装 bootstrap，然后运行：

```bash
python3 scripts/plan_capability_pack.py fixtures/capability-packs/optional-multi-agent --vault-root <vault-root>
python3 scripts/apply_capability_pack.py fixtures/capability-packs/optional-multi-agent --vault-root <vault-root> --apply
```

首次导入的 optional 成员状态为 `proposed`。这一步不会自动 activate、publish generated
output 或安装 runtime。用户审阅并接受 selected Vault 内容后，再按 canonical lifecycle
完成激活和下游发布。

## 从 0.4.0 升级

```bash
python3 scripts/update_capability_pack.py fixtures/capability-packs/optional-multi-agent --vault-root <vault-root>
python3 scripts/update_capability_pack.py fixtures/capability-packs/optional-multi-agent --vault-root <vault-root> --backup-root <fresh-private-backup-path> --apply
```

预览默认零写入。apply 只接受更高版本，并在写入前确认所有将被覆盖的旧成员仍与部署记录
一致；否则返回 `merge_required`。0.4.0 的 `COLLAB-PACK-001` 与
`ASSET-COLLAB-PACK-001` 会作为非成员 candidate 证据保留，不删除、不激活，也不再是
当前 owner。

恢复前先 preview；真正恢复需要 `--apply`：

```bash
python3 scripts/update_capability_pack.py --restore <backup-path> --vault-root <vault-root>
python3 scripts/update_capability_pack.py --restore <backup-path> --vault-root <vault-root> --apply
```

如果升级后任一目标文件发生变化，恢复整体 HOLD，避免覆盖用户后续修改。backup 保留，
不会自动清理。

## English summary

Version 0.5.0 replaces two illustrative candidates with 24 accepted practice
records and the two current collaboration assets. Bootstrap owns six shared
dependencies. Fresh imports remain `proposed`; no runtime or generated output is
activated. The bounded update path requires a newer version, stops on touched
local edits, creates a private exact backup and restores only when every expected
postimage still matches. Legacy 0.4.0 candidates are retained as non-member
evidence.

Review evidence: [issue #579](https://github.com/farmerhunter/agent-foundry/issues/579),
[issue #576](https://github.com/farmerhunter/agent-foundry/issues/576), and
[Core PR #583](https://github.com/farmerhunter/agent-foundry/pull/583).
