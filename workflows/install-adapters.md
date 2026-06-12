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

## Safety

- Never install proposed/candidate content directly.
- Do not disable native Hermes self-growth.
- Prefer explicit `--dest` for nonstandard runtime directories.
- Do not directly replace `~/.claude/CLAUDE.md`; install through the managed import block.
