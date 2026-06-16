# Install Adapters Workflow / 安装 Adapters Workflow

Use this workflow to install Agent Foundry adapters into local agent runtimes.

使用这个 workflow 将 Agent Foundry adapters 安装到本地 agent runtimes。

## Rule / 规则

Installed runtime files are downstream copies. The Agent Foundry repo remains source of truth.

已安装的 runtime files 是下游副本。Agent Foundry repo 仍然是 source of truth。

Do not overwrite agent-owned or user-owned runtime files. Use managed blocks for central files and `.agent-foundry-managed` markers for generated skill directories.

不要覆盖 agent-owned 或 user-owned runtime files。central files 使用 managed blocks，generated skill directories 使用 `.agent-foundry-managed` markers。

The runtime template is portable and tracked:

runtime template 是 portable 且进入 git tracking 的文件：

```text
runtime/templates/runtime_manifest.template.yaml
```

The runtime manifest is machine-local and ignored by git:

runtime manifest 是 machine-local 文件，并被 git ignore：

```text
runtime/local/runtime_manifest.yaml
```

## Steps / 步骤

1. Run consistency check.

   运行 consistency check。

   ```bash
   python3 scripts/check_consistency.py
   ```

2. Initialize the local runtime manifest if needed.

   如有需要，初始化本机 runtime manifest。

   ```bash
   python3 scripts/runtime_manifest.py init
   ```

3. Detect local runtimes.

   检测本机 runtimes。

   ```bash
   python3 scripts/runtime_manifest.py detect
   ```

4. Enable or configure the local targets you want.

   启用或配置你需要的本机 targets。

   ```bash
   python3 scripts/runtime_manifest.py enable codex
   python3 scripts/runtime_manifest.py configure hermes --path ~/.hermes/skills
   python3 scripts/runtime_manifest.py enable trae
   ```

5. Review the install plan.

   Review install plan。

   ```bash
   python3 scripts/runtime_manifest.py plan
   ```

6. Dry-run manifest-based install.

   对 manifest-based install 做 dry-run。

   ```bash
   python3 scripts/install_foundry.py
   ```

   The dry-run prints an operation-context preflight. Confirm that Core, selected Vault, generated adapter output, managed runtime writes, manual targets, and forbidden writes are visible before applying.

   Dry-run 会打印 operation-context preflight。Apply 前确认 Core、selected Vault、generated adapter output、managed runtime writes、manual targets 和 forbidden writes 都清楚可见。

7. Read status before applying.

   Apply 前读取 status。

   ```bash
   python3 scripts/sync_status.py
   ```

   Treat this as the safe status gate. It should name the Core root, selected Vault, generated output, enabled runtime targets, manual targets, receipt state, and next safe actions.

   将它视为安全 status gate。它应明确 Core root、selected Vault、generated output、enabled runtime targets、manual targets、receipt state 和 next safe actions。

8. Apply only when destinations are correct.

   只有在 destinations 正确时才 apply。

   ```bash
   python3 scripts/install_foundry.py --apply
   ```

9. For target-specific manual control, use target-specific sync.

   如需 target-specific manual control，使用 target-specific sync。

   ```bash
   python3 scripts/sync_adapters.py --target codex --apply
   python3 scripts/sync_adapters.py --target claude-code --apply
   python3 scripts/sync_adapters.py --target hermes --apply --dest <hermes-skills-dir>
   ```

10. If sync refuses to overwrite an unmanaged skill directory, inspect the existing directory first. Use `--force` only when it is known to be an Agent Foundry runtime copy that should be adopted.

    如果 sync 拒绝覆盖 unmanaged skill directory，先检查现有目录。只有确认它是应被 Agent Foundry 接管的 runtime copy 时，才使用 `--force`。

11. For ChatGPT, manually upload generated ChatGPT knowledge files and copy `custom-instructions.md`. ChatGPT has no managed local runtime install.

    对 ChatGPT，手动上传 generated ChatGPT knowledge files，并复制 `custom-instructions.md`。ChatGPT 没有 managed local runtime install。

12. For Trae, treat writes under `~/.trae-cn` as managed runtime writes. Dry-run and review first; apply only after durable human approval confirms the path and write intent.

    对 Trae，将 `~/.trae-cn` 下的写入视为 managed runtime writes。先 dry-run 和 review；只有 durable human approval 确认 path 和 write intent 后才 apply。

## Status And Drift Interpretation / Status 和 Drift 解读

Run this whenever adapters feel stale, after a long idle period, after switching machines, or before applying runtime writes:

当 adapters 可能 stale、长时间 idle 后、切换机器后，或执行 runtime writes 前，运行：

```bash
python3 scripts/sync_status.py
```

Interpret the report by layer:

按 layer 解读报告：

- `repo: behind` or `repo: diverged`: fetch/pull or resolve Core repo state before publishing generated output or applying runtime changes.
- `repo: behind` 或 `repo: diverged`：publish generated output 或 apply runtime changes 前，先 fetch/pull 或修复 Core repo state。
- `generated_output: missing` or missing manifest: publish adapters from the selected Vault before install.
- `generated_output: missing` 或 missing manifest：install 前先从 selected Vault publish adapters。
- `activation: stale-generated-output`: active practice or asset IDs in the selected Vault are not represented in generated output; publish adapters, then dry-run install.
- `activation: stale-generated-output`：selected Vault 中 active practice 或 asset IDs 没有体现在 generated output 中；先 publish adapters，再 dry-run install。
- `receipt: missing`: no runtime install evidence exists yet; review generated output and run install dry-run before apply.
- `receipt: missing`：还没有 runtime install evidence；先 review generated output，并在 apply 前 run install dry-run。
- `receipt: selected-output-drift`: installed runtime files no longer match selected generated output; review drift, regenerate output if needed, dry-run install, then apply only when the runtime write is expected.
- `receipt: selected-output-drift`：已安装 runtime files 不再匹配 selected generated output；先 review drift，必要时 regenerate output，再 dry-run install，只有确认 runtime write 符合预期后才 apply。
- `receipt: selected-output-unknown`: repair or recreate the receipt only through a reviewed install apply.
- `receipt: selected-output-unknown`：只能通过 reviewed install apply 修复或重建 receipt。
- `chatgpt: manual import required`: manually update ChatGPT project/custom GPT state from generated ChatGPT output.
- `chatgpt: manual import required`：从 generated ChatGPT output 手动更新 ChatGPT project/custom GPT state。
- Trae repair guidance: do not write `~/.trae-cn/skills` unless durable human approval explicitly authorizes that runtime apply.
- Trae repair guidance：除非 durable human approval 明确授权 runtime apply，否则不要写入 `~/.trae-cn/skills`。

Do not edit canonical Vault records to hide a runtime drift signal. Fix the selected generated output or local runtime install state instead.

不要通过编辑 canonical Vault records 来隐藏 runtime drift signal。应修复 selected generated output 或本机 runtime install state。

## Cross-Machine Restore / 跨机器恢复

Use this path when a deployment must recreate runtime state from public Core plus a selected Vault, not from another machine's runtime copy.

当 deployment 必须从 public Core 加 selected Vault 重建 runtime state，而不是复制另一台机器的 runtime copy 时，使用此路径。

1. Clone or update Core on the target machine.

   在目标机器 clone 或 update Core。

2. Clone, pull, or initialize the selected Vault on the target machine.

   在目标机器 clone、pull 或 initialize selected Vault。

3. Validate the pair before publishing or installing.

   Publish 或 install 前，验证 Core/Vault pair。

   ```bash
   python3 scripts/check_foundry_roots.py --core-root <core-root> --vault-root <vault-root>
   ```

4. Publish generated adapters from that selected Vault into a machine-local output directory.

   从 selected Vault publish generated adapters 到 machine-local output directory。

   ```bash
   python3 scripts/publish_adapters.py --core-root <core-root> --vault-root <vault-root> --output-root <generated-root> --apply
   ```

5. Initialize and review the local runtime manifest on that machine.

   初始化并 review 该机器的 local runtime manifest。

   ```bash
   python3 scripts/runtime_manifest.py init
   python3 scripts/runtime_manifest.py detect
   python3 scripts/runtime_manifest.py plan
   ```

6. Dry-run install from the selected output and read the status report before applying.

   从 selected output dry-run install，并在 apply 前读取 status report。

   ```bash
   python3 scripts/install_foundry.py --core-root <core-root> --vault-root <vault-root> --adapter-root <generated-root>
   python3 scripts/sync_status.py --core-root <core-root> --vault-root <vault-root> --adapter-root <generated-root>
   ```

7. Apply only after the report names the expected Core root, Vault root, generated output, enabled runtimes, manual targets, receipt status, and any runtime-write approval requirement.

   只有当报告明确 expected Core root、Vault root、generated output、enabled runtimes、manual targets、receipt status 和 runtime-write approval requirement 后，才 apply。

Do not copy `runtime/local/runtime_manifest.yaml`, `runtime/local/adapter-install-receipt.yaml`, `~/.agent-foundry/config.yaml`, managed runtime directories, or ChatGPT project imports from another machine as canonical truth. Recreate them locally from the selected Vault and generated output.

不要把另一台机器的 `runtime/local/runtime_manifest.yaml`、`runtime/local/adapter-install-receipt.yaml`、`~/.agent-foundry/config.yaml`、managed runtime directories 或 ChatGPT project imports 当作 canonical truth 复制。应从 selected Vault 和 generated output 在本机重建。

## Disable And Rollback / 禁用与回滚

Disabling a target changes only the machine-local runtime manifest:

Disable target 只改变 machine-local runtime manifest：

```bash
python3 scripts/runtime_manifest.py disable <target>
python3 scripts/runtime_manifest.py plan
python3 scripts/sync_status.py
```

Rollback helpers operate on managed runtime copies and Claude managed blocks. They do not delete or rewrite canonical Vault records:

Rollback helpers 只作用于 managed runtime copies 和 Claude managed blocks。它们不会删除或改写 canonical Vault records：

```bash
python3 scripts/rollback_runtime.py status
python3 scripts/rollback_runtime.py remove-skill <skill-name> --target codex --dry-run
python3 scripts/rollback_runtime.py remove-block --target claude-code --dry-run
python3 scripts/rollback_runtime.py restore-claude --dry-run
```

Remove only directories that contain `.agent-foundry-managed`, unless the user explicitly approves `--force` after inspecting the path. If `sync_status.py` reports selected-output drift, stale runtime files, or missing receipts, treat that as cleanup work on the current machine; do not repair it by editing unrelated Vault records. ChatGPT remains manual import and manual cleanup.

只有包含 `.agent-foundry-managed` 的目录才可移除，除非用户检查路径后明确批准 `--force`。如果 `sync_status.py` 报告 selected-output drift、stale runtime files 或 missing receipts，把它视为当前机器的 cleanup 工作；不要通过编辑无关 Vault records 来修复。ChatGPT 仍然是 manual import 和 manual cleanup。

## Safety / 安全规则

- Never install proposed/candidate content directly.
- 不要直接安装 proposed/candidate content。
- Do not disable native Hermes self-growth.
- 不要禁用 Hermes 原生 self-growth。
- Prefer explicit `--dest` for nonstandard runtime directories.
- 非标准 runtime directories 优先显式传入 `--dest`。
- Do not directly replace `~/.claude/CLAUDE.md`; install through the managed import block.
- 不要直接替换 `~/.claude/CLAUDE.md`；应通过 managed import block 安装。
- Refuse unmanaged runtime paths by default.
- 默认拒绝 unmanaged runtime paths。
- Use `--force` only after confirming an existing path should be adopted by Agent Foundry.
- 只有确认 existing path 应由 Agent Foundry 接管后，才使用 `--force`。
