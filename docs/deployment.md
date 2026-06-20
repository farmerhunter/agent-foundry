# Deployment / 部署

Agent Foundry is local-first. Core tooling, User Vault records, generated output, runtime receipts, and installed runtime files are separate layers.

Agent Foundry 是 local-first 系统。Core tooling、User Vault records、generated output、runtime receipts 和已安装的 runtime files 是不同层。

## Layers / 分层

- Core checkout: public repo with `workflows/`, `schemas/`, `scripts/`, `templates/`, `docs/`, adapter profiles, runtime templates, and validation tooling.
- Core checkout：public repo，包含 `workflows/`、`schemas/`、`scripts/`、`templates/`、`docs/`、adapter profiles、runtime templates 和 validation tooling。
- selected User Vault: canonical `practices/`, `assets/`, `indexes/`, `imports/`, and shared sanitized usage aggregate.
- selected User Vault：canonical `practices/`、`assets/`、`indexes/`、`imports/` 和 shared sanitized usage aggregate。
- generated output: selected-Vault adapter output, usually under a machine-local generated root.
- generated output：从 selected Vault 生成的 adapter output，通常位于本机 generated root。
- runtime manifest: `runtime/local/runtime_manifest.yaml`, machine-local and ignored by git.
- runtime manifest：`runtime/local/runtime_manifest.yaml`，machine-local，且被 git ignore。
- runtime receipt: `runtime/local/adapter-install-receipt.yaml`, machine-local evidence of what generated output was installed.
- runtime receipt：`runtime/local/adapter-install-receipt.yaml`，记录本机安装了哪些 generated output。
- installed runtimes: downstream copies under paths such as `~/.codex`, `~/.claude`, `~/.hermes`, and `~/.trae-cn`.
- installed runtimes：`~/.codex`、`~/.claude`、`~/.hermes`、`~/.trae-cn` 等路径下的下游副本。
- ChatGPT: manual import target, not a managed local runtime.
- ChatGPT：manual import target，不是 managed local runtime。

Do not copy another machine's `runtime/local/`, `~/.agent-foundry/config.yaml`, runtime directories, or ChatGPT project files as canonical truth.

不要把另一台机器的 `runtime/local/`、`~/.agent-foundry/config.yaml`、runtime directories 或 ChatGPT project files 当作 canonical truth 复制。

## Fresh Install / 首次安装

Use this on a new machine after cloning or unpacking the Agent Foundry Core checkout.

在新机器 clone 或 unpack Agent Foundry Core checkout 后，使用此流程。

1. Initialize or select a User Vault.

   初始化或选择 User Vault。

   ```bash
   python3 scripts/init_vault.py ~/.agent-foundry/vault/my-agent-foundry-vault --core-root . --apply
   ```

2. Write and verify the machine-local Core/Vault locator.

   写入并验证本机 Core/Vault locator。

   ```bash
   python3 scripts/foundry_config.py write --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
   python3 scripts/foundry_config.py status
   ```

3. Initialize and inspect the runtime manifest.

   初始化并检查 runtime manifest。

   ```bash
   python3 scripts/runtime_manifest.py init
   python3 scripts/runtime_manifest.py detect
   python3 scripts/runtime_manifest.py plan
   ```

4. Enable only the runtimes that should receive Agent Foundry content.

   只启用应该接收 Agent Foundry content 的 runtimes。

   ```bash
   python3 scripts/runtime_manifest.py enable codex
   python3 scripts/runtime_manifest.py enable claude-code
   python3 scripts/runtime_manifest.py enable hermes
   python3 scripts/runtime_manifest.py enable trae
   ```

5. Dry-run install, then read status.

   先 dry-run install，再读取 status。

   ```bash
   python3 scripts/install_foundry.py
   python3 scripts/sync_status.py
   ```

   In split Core/Vault mode, `install_foundry.py` defaults to the selected generated adapter root and refuses Core reference adapters as a runtime source. When in doubt, pass the generated root printed by `publish_adapters.py` explicitly with `--adapter-root`.

   在 Core/Vault split 模式下，`install_foundry.py` 默认使用 selected generated adapter root，并拒绝把 Core reference adapters 当作 runtime 来源。不确定时，显式传入 `publish_adapters.py` 打印的 generated root：`--adapter-root`。

6. Apply only after the dry-run and status report identify the expected Core, selected Vault, generated output, manual targets, receipt state, and runtime-write approval needs.

   只有当 dry-run 和 status report 明确 expected Core、selected Vault、generated output、manual targets、receipt state 和 runtime-write approval needs 后，才 apply。

   ```bash
   python3 scripts/install_foundry.py --apply
   python3 scripts/sync_status.py
   ```

## Cross-Machine Restore / 跨机器恢复

Restore local state from public Core plus the selected Vault. Do not restore by copying runtime directories from another machine.

从 public Core 加 selected Vault 恢复本机状态。不要通过复制另一台机器的 runtime directories 来恢复。

1. Clone or update Core.

   Clone 或 update Core。

   ```bash
   git clone <public-core-url> agent-foundry-core
   cd agent-foundry-core
   git pull --ff-only
   ```

2. Clone, pull, or initialize the selected Vault through the private channel you control.

   通过你控制的 private channel clone、pull 或 initialize selected Vault。

   ```bash
   git clone <private-vault-url> ~/.agent-foundry/vault/agent-foundry-vault-<account>
   ```

3. Write and verify the locator.

   写入并验证 locator。

   ```bash
   python3 scripts/foundry_config.py write \
     --repo-root <public-core-path> \
     --core-root <public-core-path> \
     --vault-root <private-vault-path>
   python3 scripts/foundry_config.py status
   python3 scripts/check_foundry_roots.py --core-root <public-core-path> --vault-root <private-vault-path>
   ```

4. Publish selected-Vault generated output into a machine-local generated root.

   将 selected Vault 的 generated output 发布到本机 generated root。

   ```bash
   python3 scripts/publish_adapters.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --output-root <generated-root> \
     --apply
   ```

5. Dry-run install and read status before applying.

   Apply 前先 dry-run install 并读取 status。

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

   只有当 status 确认 selected Vault、generated output、manual targets、receipt state 和 runtime-write approval requirements 符合预期后，才 apply。

   ```bash
   python3 scripts/install_foundry.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --adapter-root <generated-root> \
     --apply
   ```

## Daily Update / 日常更新

Use this after practices, assets, generated output, or runtime adapters may have changed.

当 practices、assets、generated output 或 runtime adapters 可能变化后，使用此流程。

Preserve the same selected adapter root across publish, selected-output quality check, install dry-run/apply, and sync status. Do not refresh managed runtimes from Core reference adapters in split mode.

在 publish、selected-output quality check、install dry-run/apply 和 sync status 中保持同一个 selected adapter root。split 模式下不要从 Core reference adapters 刷新 managed runtimes。

```bash
python3 scripts/check_consistency.py
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
```

Apply only after the status report names the expected generated output, receipt state, manual targets, and any Trae/runtime write approval requirement.

只有当 status report 明确 expected generated output、receipt state、manual targets 以及 Trae/runtime write approval requirement 后，才 apply。

```bash
python3 scripts/install_foundry.py --apply
python3 scripts/sync_status.py
```

For ChatGPT, manually update project/custom GPT instructions and knowledge files from reviewed selected-Vault generated output, not from Core adapter templates.

对 ChatGPT，从 reviewed selected-Vault generated output 手动更新 project/custom GPT instructions 和 knowledge files，不要从 Core adapter templates 更新。

## Status And Drift / Status 和 Drift

`sync_status.py` is the safe first command when a machine may be stale.

当一台机器可能 stale 时，`sync_status.py` 是安全的第一条命令。

```bash
python3 scripts/sync_status.py
```

Use it after long idle periods, after switching machines, after pulling Core or Vault changes, before runtime apply, and when a rule appears not to affect an agent.

在长时间 idle 后、切换机器后、pull Core 或 Vault changes 后、runtime apply 前，或某条 rule 看起来没有影响 agent 时，运行它。

Read the report by layer:

按 layer 读取报告：

- Core remote progress: fetch/pull before publishing generated output or applying runtime changes if the checkout is behind or diverged.
- Core remote progress：如果 checkout behind 或 diverged，先 fetch/pull，再 publish generated output 或 apply runtime changes。
- selected Vault: canonical source for practices and assets.
- selected Vault：practices 和 assets 的 canonical source。
- generated output: selected-Vault adapter files that can be reviewed before install.
- generated output：从 selected Vault 生成、可在 install 前 review 的 adapter files。
- activation freshness: whether active practice/asset IDs are represented in generated output.
- activation freshness：active practice/asset IDs 是否已经体现在 generated output 中。
- runtime receipt: evidence of which generated output was installed to local runtimes.
- runtime receipt：哪些 generated output 已安装到本地 runtimes 的 evidence。
- selected-output drift: installed runtime files no longer match selected generated output.
- selected-output drift：已安装 runtime files 不再匹配 selected generated output。
- manual targets: ChatGPT requires manual import.
- manual targets：ChatGPT 需要 manual import。
- runtime write gates: Trae and other managed runtime writes require explicit approval before apply.
- runtime write gates：Trae 和其他 managed runtime writes 在 apply 前需要 explicit approval。

Repair stale state in this order: bring Core and Vault to the intended versions, publish generated output, run install dry-run, read status, then apply only when runtime writes are expected.

修复 stale state 的顺序是：先让 Core 和 Vault 到达预期版本，再 publish generated output，运行 install dry-run，读取 status，最后只有 runtime writes 符合预期时才 apply。

## Add, Pause, Or Move A Runtime / 添加、暂停或迁移 Runtime

Detect and enable a new runtime before installing to it.

安装到新 runtime 前，先 detect 并 enable。

```bash
python3 scripts/runtime_manifest.py detect
python3 scripts/runtime_manifest.py enable <target>
python3 scripts/runtime_manifest.py configure <target> --path <runtime-path>
python3 scripts/install_foundry.py --target <target>
python3 scripts/sync_status.py
```

Apply only after status confirms the selected generated output, receipt state, manual targets, and any Trae/runtime write approval requirement.

只有当 status 确认 selected generated output、receipt state、manual targets 和 Trae/runtime write approval requirement 后，才 apply。

```bash
python3 scripts/install_foundry.py --target <target> --apply
```

To pause a runtime, disable it in the local manifest and verify status. Do not delete runtime files automatically.

暂停 runtime 时，在 local manifest 中 disable，然后验证 status。不要自动删除 runtime files。

```bash
python3 scripts/runtime_manifest.py disable <target>
python3 scripts/runtime_manifest.py status
python3 scripts/sync_status.py
```

## Online And Offline Sync / 在线与离线同步

Use GitHub when available. GitHub is an async remote backup and distribution channel, not the only source of truth.

有 GitHub 时优先使用 GitHub。GitHub 是 async remote backup 和 distribution channel，不是唯一 source of truth。

```bash
python3 scripts/check_consistency.py
python3 scripts/sync_status.py
./sync.sh pull
./sync.sh push
```

After pulling on another machine, dry-run install and read status before applying runtime writes.

在另一台机器 pull 后，先 dry-run install 并读取 status，再 apply runtime writes。

```bash
python3 scripts/runtime_manifest.py status
python3 scripts/install_foundry.py
python3 scripts/sync_status.py
```

Use snapshots only when GitHub is unavailable or unreliable. Snapshots include `runtime/templates/` but exclude `runtime/local/`.

只有在 GitHub 不可用或不可靠时才使用 snapshots。Snapshots 包含 `runtime/templates/`，但排除 `runtime/local/`。

```bash
python3 scripts/export_snapshot.py
python3 scripts/import_snapshot.py <snapshot.tar.gz>
python3 scripts/check_consistency.py
python3 scripts/sync_status.py
```

## Target Notes / Target 说明

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

## Safety / 安全规则

- Never install proposed/candidate content directly.
- 不要直接安装 proposed/candidate content。
- Use dry-runs and `sync_status.py` before writes.
- 写入前先使用 dry-run 和 `sync_status.py`。
- Treat runtime files as shared user-owned environments.
- 将 runtime files 视为 shared user-owned environments。
- Use managed blocks or imports for central files, not full replacement.
- central files 使用 managed blocks 或 imports，不要 full replacement。
- Refuse unmanaged runtime paths by default.
- 默认拒绝 unmanaged runtime paths。
- Use `--force` only after confirming an existing path should be adopted by Agent Foundry.
- 只有确认 existing path 应由 Agent Foundry 接管后，才使用 `--force`。
