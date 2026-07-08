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

Use this on a new machine after cloning or unpacking the Agent Foundry Core checkout.

1. Initialize or select a User Vault.

   ```bash
   python3 scripts/init_vault.py ~/.agent-foundry/vault/my-agent-foundry-vault --core-root . --apply
   ```

2. Write and verify the machine-local Core/Vault locator.

   ```bash
   python3 scripts/foundry_config.py write --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
   python3 scripts/foundry_config.py status
   ```

3. Initialize and inspect the runtime manifest.

   ```bash
   python3 scripts/runtime_manifest.py init
   python3 scripts/runtime_manifest.py detect
   python3 scripts/runtime_manifest.py plan
   ```

4. Enable only the runtimes that should receive Agent Foundry content.

   ```bash
   python3 scripts/runtime_manifest.py enable codex
   python3 scripts/runtime_manifest.py enable claude-code
   python3 scripts/runtime_manifest.py enable hermes
   python3 scripts/runtime_manifest.py enable trae
   ```

5. Dry-run install, then read status.

   ```bash
   python3 scripts/install_foundry.py
   python3 scripts/sync_status.py
   ```

   In split Core/Vault mode, `install_foundry.py` defaults to the selected generated adapter root and refuses Core reference adapters as a runtime source. When in doubt, pass the generated root printed by `publish_adapters.py` explicitly with `--adapter-root`.

6. Apply only after the dry-run and status report identify the expected Core, selected Vault, generated output, manual targets, receipt state, and runtime-write approval needs.

   ```bash
   python3 scripts/install_foundry.py --apply
   python3 scripts/sync_status.py
   ```

**中文要点：** 新机器先建/选 Vault，再写 locator、配置 runtime manifest、dry-run install、读 status。只有 dry-run/status 明确目标和写入需求后才 apply。

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
