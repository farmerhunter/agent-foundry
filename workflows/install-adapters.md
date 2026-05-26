# Install Adapters Workflow

Use this workflow to install Agent Foundry adapters into local agent runtimes.

## Rule

Installed runtime files are downstream copies. The Agent Foundry repo remains source of truth.

Do not overwrite agent-owned or user-owned runtime files. Use managed blocks for central files and `.agent-foundry-managed` markers for generated skill directories.

## Steps

1. Run consistency check:

   ```bash
   python3 scripts/check_consistency.py
   ```

2. Dry run adapter sync:

   ```bash
   python3 scripts/sync_adapters.py --target all --dry-run
   ```

3. Review destination paths.

4. Apply only when destinations are correct:

   ```bash
   python3 scripts/sync_adapters.py --target codex --apply
   python3 scripts/sync_adapters.py --target claude-code --apply
   python3 scripts/sync_adapters.py --target hermes --apply --dest <hermes-skills-dir>
   ```

5. If sync refuses to overwrite an unmanaged skill directory, inspect the existing directory first. Use `--force` only when it is known to be an Agent Foundry runtime copy that should be adopted.

6. For ChatGPT, manually upload `adapters/chatgpt/knowledge/` and copy `custom-instructions.md`.

## Safety

- Never install proposed/candidate content directly.
- Do not disable native Hermes self-growth.
- Prefer explicit `--dest` for nonstandard runtime directories.
- Do not directly replace `~/.claude/CLAUDE.md`; install through the managed import block.
