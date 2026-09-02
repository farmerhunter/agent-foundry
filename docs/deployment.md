# Deployment

Agent Foundry is local-first. Core tooling, User Vault records, generated output, runtime receipts, and installed runtime files are separate layers.

**中文要点：** Agent Foundry 是 local-first。Core、User Vault、generated output、runtime receipt 和 installed runtime files 是不同层。

## Layers

- **Core checkout**: public repo with `workflows/`, `schemas/`, `scripts/`, `templates/`, `docs/`, adapter profiles, runtime templates, and validation tooling.
- **Selected User Vault**: canonical `practices/`, `assets/`, `indexes/`, `imports/`, and shared sanitized usage aggregate.
- **Generated output**: selected-Vault adapter output, usually under a machine-local generated root.
- **Runtime manifest**: `runtime/local/runtime_manifest.yaml`, machine-local and ignored by git.
- **Runtime receipt**: `runtime/local/adapter-install-receipt.yaml`, machine-local evidence of what generated output was installed.
- **Installed runtimes**: downstream copies under paths such as `~/.codex`, `~/.claude`, `~/.hermes`, and `~/.trae-cn`.
- **ChatGPT**: manual import target, not a managed local runtime.

Do not copy another machine's `runtime/local/`, `~/.agent-foundry/config.yaml`, runtime directories, or ChatGPT project files as canonical truth.

**中文要点：** 不要把另一台机器的 runtime/local、config、runtime directories 或 ChatGPT project files 当作 canonical truth。

## Fresh Install

这是新工作站唯一 canonical onboarding 路径。先读当前 checkout 的 `AGENTS.md`、本节、两个 pack 的 `manifest.yaml`，再运行相关 CLI 的 `--help`。不要用旧会话记忆、另一台机器的路径或维护者自己的 Vault/runtime 代替当前接口。

### 完成后会得到什么

四层各自就绪，但不会混成一个 authority：

| 层 | 作用 | 完成标志 |
| --- | --- | --- |
| Core | 公共工具、schema、文档和 first-party pack | 当前 checkout 可验证 |
| selected Vault | 使用者自己拥有的 canonical practices/assets | locator 指向该 Vault，starter pack metadata 可读 |
| Generated | 从 selected Vault 生成、可审查的 adapter output | selected-output quality 通过 |
| Runtime | 从同一个 Generated root 安装的受管副本 | managed marker、receipt 和 `sync_status` 一致 |

这只表示 **Agent Foundry 工作站层** 就绪；不表示某个项目已经 onboarding，也不表示 SQLite ledger、scheduler、native roles、跨设备协作或 release 已启用。

### 三个 Human 决策

Agent 只在有真实后果时暂停：

1. **Vault 归属**：选择使用者自己的 Vault 位置，以及是否连接使用者控制的 private remote。不要复制维护者 Vault。
2. **Optional pack adoption**：使用者审阅 dry-run 列出的 exact version/members，决定是否采用并激活 `pack.multi-agent.optional`。`review_token` 只防 drift，不代表批准。
3. **Runtime 写入**：使用者确认具体 enabled targets 和 install paths 后，才执行 runtime `--apply`。

已授权阶段内的机械 validation、Generated publish 和 readback 不重复索要批准。以后只有新增操作引入新的实质权限、隐私边界、持久写入或不可逆风险时，才增加同类 gate。

### 确定执行顺序

以下占位符在一次执行中保持不变：`<vault-root>` 是使用者自己的 selected Vault；`<generated-root>` 是 machine-local Generated；`<private-backup-parent>` 已存在且 mode 为 `0700`，而 `<activation-backup-root>` 必须尚不存在。

1. Clone/update Core，确认 checkout 与接口。

   ```bash
   git clone <public-core-url> agent-foundry-core
   cd agent-foundry-core
   git pull --ff-only
   python3 scripts/foundry_config.py status
   python3 scripts/manage_capability_pack_lifecycle.py --help
   ```

2. 在 Human 决定的位置 preview，然后建立 blank Vault；写 locator 并 read back。

   ```bash
   python3 scripts/init_vault.py <vault-root> --core-root .
   python3 scripts/init_vault.py <vault-root> --core-root . --apply
   python3 scripts/foundry_config.py write --core-root . --vault-root <vault-root>
   python3 scripts/foundry_config.py status
   python3 scripts/check_foundry_roots.py --core-root . --vault-root <vault-root>
   ```

3. Preview/apply mandatory `pack.bootstrap.minimal`。

   ```bash
   python3 scripts/deploy_capability_pack.py fixtures/capability-packs/bootstrap-minimal \
     --core-root . --vault-root <vault-root>
   python3 scripts/deploy_capability_pack.py fixtures/capability-packs/bootstrap-minimal \
     --core-root . --vault-root <vault-root> --apply
   ```

4. 如果使用者考虑 GitHub multi-agent collaboration，先 preview/import optional pack。Import 只产生 `proposed` members。

   ```bash
   python3 scripts/plan_capability_pack.py fixtures/capability-packs/optional-multi-agent \
     --core-root . --vault-root <vault-root>
   python3 scripts/apply_capability_pack.py fixtures/capability-packs/optional-multi-agent \
     --core-root . --vault-root <vault-root> --apply
   ```

5. Dry-run activation，向使用者解释输出中的 pack version、完整 member 列表和采用后行为。使用者批准后，原样使用当前 `review_token`，并指定 fresh private backup root。

   ```bash
   python3 scripts/manage_capability_pack_lifecycle.py \
     --core-root . --vault-root <vault-root> \
     --pack-id pack.multi-agent.optional --action activate

   python3 scripts/manage_capability_pack_lifecycle.py \
     --core-root . --vault-root <vault-root> \
     --pack-id pack.multi-agent.optional --action activate \
     --review-token <review-token> \
     --backup-root <activation-backup-root> --apply
   ```

   任何 token、member、hash、path、status、index 或 metadata drift 都在写入前 HOLD。成功 apply 保留 `0700` backup root、`0600` preimages/receipt；不自动 publish 或 install。

6. 从 selected Vault preview/publish 到同一个 Generated root，并做 selected-output quality readback。

   ```bash
   python3 scripts/publish_adapters.py \
     --core-root . --vault-root <vault-root> --output-root <generated-root>
   python3 scripts/publish_adapters.py \
     --core-root . --vault-root <vault-root> --output-root <generated-root> --apply
   python3 scripts/check_adapter_quality.py \
     --core-root . --vault-root <vault-root> \
     --surface selected-output --generated-root <generated-root>
   ```

7. Detect runtime，启用且只配置使用者选择的 targets。Codex 只是示例；实际 target 从当前 manifest/CLI 读取。

   ```bash
   python3 scripts/runtime_manifest.py init
   python3 scripts/runtime_manifest.py detect
   python3 scripts/runtime_manifest.py status
   python3 scripts/runtime_manifest.py enable <target>
   python3 scripts/runtime_manifest.py configure <target> --path <runtime-path>
   python3 scripts/runtime_manifest.py plan
   ```

8. 从步骤 6 的同一个 Generated root dry-run install。向使用者列明 targets/paths；经第三个 Human 决策后 apply，并做最终 readback。

   ```bash
   python3 scripts/install_foundry.py \
     --core-root . --vault-root <vault-root> --adapter-root <generated-root>
   python3 scripts/sync_status.py \
     --core-root . --vault-root <vault-root> --adapter-root <generated-root>

   python3 scripts/install_foundry.py \
     --core-root . --vault-root <vault-root> --adapter-root <generated-root> --apply
   python3 scripts/sync_status.py \
     --core-root . --vault-root <vault-root> --adapter-root <generated-root>
   ```

### Stop、恢复与成功标准

遇到 incompatible schema/layout/pack、错误 authority、missing marker、local edit、hash/status drift、unmanaged runtime target、异常 CLI 输出或缺失批准时立即停止；报告一个具体恢复条件，不猜测迁移、不覆盖现状。版本、member 数、runtime 列表、默认路径和 receipt 字段均以当前 checkout 的 manifest/config/CLI 输出为准。

Activation apply 失败会从 fresh backup 自动补偿。若成功后需要恢复，先 dry-run；只有所有当前文件仍等于 receipt postimages 时才允许 restore：

```bash
python3 scripts/manage_capability_pack_lifecycle.py \
  --core-root . --vault-root <vault-root> --restore-backup <activation-backup-root>
python3 scripts/manage_capability_pack_lifecycle.py \
  --core-root . --vault-root <vault-root> --restore-backup <activation-backup-root> --apply
```

成功条件是：root validation passed；optional pack（若采用）的 exact members/indexes 为 `active`；Generated quality passed；enabled runtime 具有 managed marker 和 receipt；最终 `sync_status` 报告 Generated ready、installed selected-output in sync，并明确 ChatGPT 等 manual targets。随后如要把某个项目接入 bounded collaboration，另走该项目的 onboarding contract；它不是本工作站流程的隐式下一步。

### 可直接交给 AI agent 的入口 prompt

```text
请读取当前 checkout 的 AGENTS.md 和 docs/deployment.md#fresh-install，严格按 canonical fresh-workstation 顺序执行。先读取当前 manifests、foundry_config.py status 和相关 CLI --help，只询问三个有实质后果的 Human 决策：我的 selected Vault 位置/private remote、是否采用并激活 optional collaboration pack、是否向列出的 runtime targets 写入。每个写阶段先 dry-run 并回读；在已授权阶段内自动完成机械 validation/publish/readback。任何 authority、schema、member/hash/status、local edit、unmanaged target 或异常输出 drift 都 HOLD，并告诉我一个恢复条件。不要把工作站 Skill install 声称为项目 onboarding、SQLite、scheduler、native role、cross-device 或 release readiness。
```

## Cross-Machine Restore

Restore local state from public Core plus the selected Vault. Do not restore by copying runtime directories from another machine.

1. Clone or update Core.

   ```bash
   git clone <public-core-url> agent-foundry-core
   cd agent-foundry-core
   git pull --ff-only
   ```

2. Clone, pull, or initialize the selected Vault through the private channel you control.

   ```bash
   git clone <private-vault-url> ~/.agent-foundry/vault/agent-foundry-vault-<account>
   ```

3. Write and verify the locator.

   ```bash
   python3 scripts/foundry_config.py write \
     --repo-root <public-core-path> \
     --core-root <public-core-path> \
     --vault-root <private-vault-path>
   python3 scripts/foundry_config.py status
   python3 scripts/check_foundry_roots.py --core-root <public-core-path> --vault-root <private-vault-path>
   ```

4. Publish selected-Vault generated output into a machine-local generated root.

   ```bash
   python3 scripts/publish_adapters.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --output-root <generated-root> \
     --apply
   ```

5. Dry-run install and read status before applying.

   ```bash
   python3 scripts/install_foundry.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --adapter-root <generated-root>
   python3 scripts/sync_status.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --adapter-root <generated-root>
   ```

6. Apply only after status confirms the intended selected Vault, generated output, manual targets, receipt state, and runtime-write approval requirements.

   ```bash
   python3 scripts/install_foundry.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --adapter-root <generated-root> \
     --apply
   ```

**中文要点：** 跨机器恢复从 Core + selected Vault 重建。不要复制 runtime directories；publish、dry-run、status 都确认后才 apply runtime writes。

## Daily Update

Use this after practices, assets, generated output, or runtime adapters may have changed.

Preserve the same selected adapter root across publish, selected-output quality check, install dry-run/apply, and sync status. Do not refresh managed runtimes from Core reference adapters in split mode.

```bash
python3 scripts/check_consistency.py
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
```

Apply only after the status report names the expected generated output, receipt state, manual targets, and any Trae/runtime write approval requirement.

```bash
python3 scripts/install_foundry.py --apply
python3 scripts/sync_status.py
```

For ChatGPT, manually update project/custom GPT instructions and knowledge files from reviewed selected-Vault generated output, not from Core adapter templates.

**中文要点：** 日常更新保持同一个 selected adapter root。ChatGPT 是 manual target，应从 reviewed generated output 更新。

## Status And Drift

`sync_status.py` is the safe first command when a machine may be stale.

```bash
python3 scripts/sync_status.py
```

Use it after long idle periods, after switching machines, after pulling Core or Vault changes, before runtime apply, and when a rule appears not to affect an agent.

Read the report by layer:

| Layer | What to check |
| --- | --- |
| Core remote progress | If the checkout is behind or diverged, fetch/pull before publishing generated output or applying runtime changes. |
| selected Vault | Canonical source for practices and assets. |
| generated output | Selected-Vault adapter files that can be reviewed before install. |
| activation freshness | Whether active practice/asset IDs are represented in generated output. |
| runtime receipt | Evidence of which generated output was installed to local runtimes. |
| selected-output drift | Installed runtime files no longer match selected generated output. |
| manual targets | ChatGPT requires manual import. |
| runtime write gates | Trae and other managed runtime writes require explicit approval before apply. |

Repair stale state in this order: bring Core and Vault to the intended versions, publish generated output, run install dry-run, read status, then apply only when runtime writes are expected.

**中文要点：** status 先看 Core/Vault/generated/runtime receipt/manual targets。修复顺序是 Core/Vault 到位、publish generated output、dry-run install、读 status、最后 apply。

## Add, Pause, Or Move A Runtime

Detect and enable a new runtime before installing to it.

```bash
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py enable <target>
python3 scripts/runtime_manifest.py configure <target> --path <runtime-path>
python3 scripts/install_foundry.py --target <target>
python3 scripts/sync_status.py
```

Apply only after status confirms the selected generated output, receipt state, manual targets, and any Trae/runtime write approval requirement.

```bash
python3 scripts/install_foundry.py --target <target> --apply
```

To pause a runtime, disable it in the local manifest and verify status. Do not delete runtime files automatically.

```bash
python3 scripts/runtime_manifest.py disable <target>
python3 scripts/runtime_manifest.py status
python3 scripts/sync_status.py
```

**中文要点：** 新 runtime 先 detect/enable/configure，再 dry-run/status。暂停 runtime 时 disable manifest，不自动删除 runtime files。

## Online And Offline Sync

Use GitHub when available. GitHub is an async remote backup and distribution channel, not the only source of truth.

```bash
python3 scripts/check_consistency.py
python3 scripts/sync_status.py
./sync.sh pull
./sync.sh push
```

After pulling on another machine, dry-run install and read status before applying runtime writes.

```bash
python3 scripts/runtime_manifest.py status
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
```

Use snapshots only when GitHub is unavailable or unreliable. Snapshots include `runtime/templates/` but exclude `runtime/local/`.

```bash
python3 scripts/export_snapshot.py
python3 scripts/import_snapshot.py <snapshot.tar.gz>
python3 scripts/check_consistency.py
python3 scripts/sync_status.py
```

**中文要点：** 有 GitHub 时优先用 GitHub；snapshot 只在 GitHub 不可用或不可靠时使用，且不包含 runtime/local。

## Target Notes

Codex:

```text
generated output: <generated-root>/codex/skills/
default runtime: ~/.codex/skills/
ownership: managed skill directories with .agent-foundry-managed
```

Claude Code:

```text
generated output: <generated-root>/claude-code/CLAUDE.md
generated output: <generated-root>/claude-code/commands/
default runtime: ~/.claude
ownership: ~/.claude/agent-foundry/ plus managed import block in ~/.claude/CLAUDE.md
```

Hermes:

```text
generated output: <generated-root>/hermes/skills/
default runtime: ~/.hermes/skills/
ownership: managed skill directories with .agent-foundry-managed
```

Trae CN:

```text
generated output: <generated-root>/trae/skills/
default runtime: ~/.trae-cn/skills/
ownership: managed skill directories with .agent-foundry-managed
```

ChatGPT:

```text
generated output: <generated-root>/chatgpt/custom-instructions.md
generated output: <generated-root>/chatgpt/knowledge/
runtime: manual project/custom GPT import
```

## Safety

- Never install proposed/candidate content directly.
- Use dry-runs and `sync_status.py` before writes.
- Treat runtime files as shared user-owned environments.
- Use managed blocks or imports for central files, not full replacement.
- Refuse unmanaged runtime paths by default.
- Use `--force` only after confirming an existing path should be adopted by Agent Foundry.

**中文要点：** 不直接安装 candidate content；写入前 dry-run/status；runtime files 是 shared user-owned environment；默认拒绝 unmanaged runtime paths。
