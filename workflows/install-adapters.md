# Install Adapters Workflow

Use this workflow to install Agent Foundry adapters into local agent runtimes.

## Rule

Installed runtime files are downstream copies. The Agent Foundry repo remains source of truth.

Do not overwrite agent-owned or user-owned runtime files. Use managed blocks for central files and `.agent-foundry-managed` markers for generated skill directories.

The runtime template is portable and tracked:

```text
runtime/templates/runtime_manifest.template.yaml
```

The runtime manifest is machine-local and ignored by git:

```text
runtime/local/runtime_manifest.yaml
```

## Steps

1. Run consistency check:

   ```bash
   python3 scripts/check_consistency.py
   ```

2. Initialize the local runtime manifest if needed:

   ```bash
   python3 scripts/runtime_manifest.py init
   ```

3. Detect local runtimes:

   ```bash
   python3 scripts/runtime_manifest.py detect
   ```

4. Enable or configure the local targets you want:

   ```bash
   python3 scripts/runtime_manifest.py enable codex
   python3 scripts/runtime_manifest.py configure hermes --path ~/.hermes/skills
   ```

5. Review the install plan:

   ```bash
   python3 scripts/runtime_manifest.py plan
   ```

6. Dry run manifest-based install:

   ```bash
   python3 scripts/install_foundry.py
   ```

   The dry run prints an operation-context preflight. Confirm that Core, selected Vault, generated adapter output, managed runtime writes, manual targets, and forbidden writes are visible before applying.

7. Apply only when destinations are correct:

   ```bash
   python3 scripts/install_foundry.py --apply
   ```

8. For target-specific manual control, use:

   ```bash
   python3 scripts/sync_adapters.py --target codex --apply
   python3 scripts/sync_adapters.py --target claude-code --apply
   python3 scripts/sync_adapters.py --target hermes --apply --dest <hermes-skills-dir>
   ```

9. If sync refuses to overwrite an unmanaged skill directory, inspect the existing directory first. Use `--force` only when it is known to be an Agent Foundry runtime copy that should be adopted.

10. For ChatGPT, manually upload `adapters/chatgpt/knowledge/` and copy `custom-instructions.md`.

## Cross-Machine Restore

Use this path when a deployment must recreate runtime state from public Core plus a selected Vault, not from another machine's runtime copy.

1. Clone or update Core on the target machine.
2. Clone, pull, or initialize the selected Vault on the target machine.
3. Validate the pair before publishing or installing:

   ```bash
   python3 scripts/check_foundry_roots.py --core-root <core-root> --vault-root <vault-root>
   ```

4. Publish generated adapters from that selected Vault into a machine-local output directory:

   ```bash
   python3 scripts/publish_adapters.py --core-root <core-root> --vault-root <vault-root> --output-root <generated-root> --apply
   ```

5. Initialize and review the local runtime manifest on that machine:

   ```bash
   python3 scripts/runtime_manifest.py init
   python3 scripts/runtime_manifest.py detect
   python3 scripts/runtime_manifest.py plan
   ```

6. Dry-run install from the selected output and read the status report before applying:

   ```bash
   python3 scripts/install_foundry.py --core-root <core-root> --vault-root <vault-root> --adapter-root <generated-root>
   python3 scripts/sync_status.py --core-root <core-root> --vault-root <vault-root> --adapter-root <generated-root>
   ```

7. Apply only after the report names the expected Core root, Vault root, generated output, enabled runtimes, manual targets, and receipt status.

Do not copy `runtime/local/runtime_manifest.yaml`, `runtime/local/adapter-install-receipt.yaml`, `~/.agent-foundry/config.yaml`, managed runtime directories, or ChatGPT project imports from another machine as canonical truth. Recreate them locally from the selected Vault and generated output.

## Disable And Rollback

Disabling a target changes only the machine-local runtime manifest:

```bash
python3 scripts/runtime_manifest.py disable <target>
python3 scripts/runtime_manifest.py plan
python3 scripts/sync_status.py
```

Rollback helpers operate on managed runtime copies and Claude managed blocks. They do not delete or rewrite canonical Vault records:

```bash
python3 scripts/rollback_runtime.py status
python3 scripts/rollback_runtime.py remove-skill <skill-name> --target codex --dry-run
python3 scripts/rollback_runtime.py remove-block --target claude-code --dry-run
python3 scripts/rollback_runtime.py restore-claude --dry-run
```

Remove only directories that contain `.agent-foundry-managed`, unless the user explicitly approves `--force` after inspecting the path. If `sync_status.py` reports selected-output drift, stale runtime files, or missing receipts, treat that as cleanup work on the current machine; do not repair it by editing unrelated Vault records. ChatGPT remains manual import and manual cleanup.

## Safety

- Never install proposed/candidate content directly.
- Do not disable native Hermes self-growth.
- Prefer explicit `--dest` for nonstandard runtime directories.
- Do not directly replace `~/.claude/CLAUDE.md`; install through the managed import block.
