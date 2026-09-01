# Minimal Agent Foundry Bootstrap Pack

中文（默认） | English summary below

`pack.bootstrap.minimal` 是新 selected User Vault 的最小公开基础包。它先建立 harvest、
review、source-of-truth、runtime 边界和 capability-pack 分层判断，再让用户选择是否安装
其他可选能力。

## 它包含什么

0.3.0 保留原有 bootstrap/meta/governance/runtime 基础，刷新 `META-003`、`META-011`、
`META-012`、`META-013` 和公开安全版 `ASSET-META-001`，并加入该 asset 直接需要的
`GOV-007`。总成员数为 26。

`GOV-007` 明确 pack 是公开 transfer snapshot，不是导入后的第三个 source of truth。
`ASSET-META-001` 的公开快照不包含维护者个人 Vault 的 merge 权限。

## 它不做什么

- 不携带 optional collaboration、项目特定规则或私有 Vault 证据；
- 不安装 runtime，不发布 generated adapters；
- 不导出 credentials、raw sessions、usage rows、receipts 或本机路径；
- 不替用户批准后续 optional pack 或项目 onboarding。

## 安装

从 Agent Foundry Core checkout 使用真实 pack root，而不是 catalog 页面：

```bash
python3 scripts/plan_capability_pack.py fixtures/capability-packs/bootstrap-minimal --vault-root <vault-root>
python3 scripts/deploy_capability_pack.py fixtures/capability-packs/bootstrap-minimal --vault-root <vault-root> --apply
```

先检查 preview 的 selected Vault 目标，再执行已审阅的 apply。部署后 selected User Vault
是 canonical；Core fixture、generated output 和 runtime 都不是新的 authority。

## 升级与恢复

已部署旧版本时使用 `scripts/update_capability_pack.py`。预览默认零写入；apply 必须指定
全新的私有 backup 目录。工具遇到本地修改会在写入前返回 `merge_required`。恢复使用同一
backup receipt，并在任何文件被后续修改时整体停止。

版本 0.3.0 表示 pack 内容与兼容性快照；它与 Core git tag/release 是不同版本轴。

## English summary

`pack.bootstrap.minimal` 0.3.0 is the mandatory 26-member public baseline for
harvest, review, source-of-truth, runtime and package-layer boundaries. It adds
the directly required `GOV-007`, refreshes five public snapshots, excludes
repository-specific merge authority and performs no generated/runtime install.
Use the fixture directory as the pack root. Updates are dry-run first, preserve
local edits, require a private backup for apply and support drift-checked restore.

Review evidence: [issue #579](https://github.com/farmerhunter/agent-foundry/issues/579).
