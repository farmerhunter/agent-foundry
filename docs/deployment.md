# Deployment

Agent Foundry is local-first. The repository is the canonical workspace; installed agent runtime files are downstream copies.

```text
Agent Foundry repo
  -> generated adapters
  -> machine-local runtime manifest
  -> installed runtime copies
  -> real agent usage
  -> usage evidence back into Agent Foundry
```

## Boundaries

- `practices/`, `assets/`, `indexes/`, `usage/`: canonical vault.
- `workflows/`, `schemas/`, `scripts/`, `templates/`: Foundry system.
- `adapters/`: generated or maintained adapter outputs.
- `runtime/templates/runtime_manifest.template.yaml`: portable deployment template, tracked in git.
- `runtime/local/runtime_manifest.yaml`: this machine's private deployment state, ignored by git and portable snapshots.
- Installed runtime locations such as `~/.codex`, `~/.claude`, and `~/.hermes`: downstream copies, not source of truth.

## Fresh Install

Use this on a new machine after cloning or unpacking Agent Foundry.

1. Initialize the machine-local runtime manifest:

   ```bash
   python3 scripts/runtime_manifest.py init
   ```

2. Detect local agent runtimes:

   ```bash
   python3 scripts/runtime_manifest.py detect
   ```

3. Enable only agents that exist and should receive Agent Foundry content:

   ```bash
   python3 scripts/runtime_manifest.py enable codex
   python3 scripts/runtime_manifest.py enable claude-code
   python3 scripts/runtime_manifest.py enable hermes
   ```

4. If a runtime uses a non-default path, configure it:

   ```bash
   python3 scripts/runtime_manifest.py configure hermes --path <hermes-skills-dir>
   ```

5. Review the install plan:

   ```bash
   python3 scripts/runtime_manifest.py plan
   ```

6. Dry-run the full install:

   ```bash
   python3 scripts/install_foundry.py
   ```

7. Apply after reviewing destinations:

   ```bash
   python3 scripts/install_foundry.py --apply
   ```

8. Verify status:

   ```bash
   python3 scripts/sync_status.py
   ```

## Daily Update

Use this after practices, assets, or adapters change.

1. Check consistency:

   ```bash
   python3 scripts/check_consistency.py
   ```

2. Dry-run runtime sync:

   ```bash
   python3 scripts/install_foundry.py
   ```

3. Apply to enabled local targets:

   ```bash
   python3 scripts/install_foundry.py --apply
   ```

4. For ChatGPT, manually update project/custom GPT instructions and knowledge files from `adapters/chatgpt/`.

## Add An Agent

Use this after installing a new local agent or deciding to deploy Agent Foundry into an existing one.

1. Detect runtimes:

   ```bash
   python3 scripts/runtime_manifest.py detect
   ```

2. Enable the target:

   ```bash
   python3 scripts/runtime_manifest.py enable <target>
   ```

3. Configure a custom path if needed:

   ```bash
   python3 scripts/runtime_manifest.py configure <target> --path <runtime-path>
   ```

4. Review and dry-run only that target:

   ```bash
   python3 scripts/install_foundry.py --target <target>
   ```

5. Apply after review:

   ```bash
   python3 scripts/install_foundry.py --target <target> --apply
   ```

Supported local targets: `codex`, `claude-code`, `hermes`. `chatgpt` is `manual`.

## Remove Or Pause An Agent

Use this when an agent is uninstalled, temporarily disabled, or should stop receiving updates.

1. Disable it in the local manifest:

   ```bash
   python3 scripts/runtime_manifest.py disable <target>
   ```

2. Confirm it is skipped:

   ```bash
   python3 scripts/runtime_manifest.py status
   python3 scripts/install_foundry.py
   ```

3. Do not delete runtime files automatically. If cleanup is needed, inspect the managed runtime paths first and remove only Agent Foundry managed files or blocks.

## Change An Agent Path

Use this when a runtime moves, a profile changes, or Hermes/Codex uses a custom skill directory.

1. Configure the new path:

   ```bash
   python3 scripts/runtime_manifest.py configure <target> --path <new-runtime-path>
   ```

2. Review the plan:

   ```bash
   python3 scripts/install_foundry.py --target <target>
   ```

3. Apply:

   ```bash
   python3 scripts/install_foundry.py --target <target> --apply
   ```

4. If the old path should be cleaned, do it manually after verifying ownership markers or managed blocks.

## Online Sync

Use GitHub when available. GitHub is an async remote backup and distribution channel, not the only source of truth.

1. Before switching machines or pushing:

   ```bash
   python3 scripts/check_consistency.py
   python3 scripts/sync_status.py
   ```

2. Pull before work on another machine:

   ```bash
   git pull --ff-only
   ```

3. Push committed changes when network is available:

   ```bash
   git push
   ```

4. After pulling on a machine, review local deployment status and sync enabled runtimes:

   ```bash
   python3 scripts/runtime_manifest.py status
   python3 scripts/install_foundry.py
   python3 scripts/install_foundry.py --apply
   ```

## Offline Sync

Use snapshots when GitHub is unavailable or unreliable.

1. On the source machine, check and export:

   ```bash
   python3 scripts/check_consistency.py
   python3 scripts/export_snapshot.py
   ```

2. Move the generated archive from `sync/snapshots/` by USB, LAN, or another reliable channel.

3. On the receiving machine, stage it without overwriting the live repo:

   ```bash
   python3 scripts/import_snapshot.py <snapshot.tar.gz>
   ```

4. Review staged files under `sync/imported/` and merge intentionally.

5. Run checks after merging:

   ```bash
   python3 scripts/check_consistency.py
   python3 scripts/sync_status.py
   ```

6. Initialize or review the receiving machine's local runtime manifest before installing:

   ```bash
   python3 scripts/runtime_manifest.py init
   python3 scripts/runtime_manifest.py status
   python3 scripts/install_foundry.py
   ```

Portable snapshots include `runtime/templates/` but exclude `runtime/local/`, because local runtime deployment state is machine-specific.

## Target Notes

Codex:

```text
adapter: adapters/codex/skills/
default runtime: ~/.codex/skills/
ownership: managed skill directories with .agent-foundry-managed
```

Claude Code:

```text
adapter: adapters/claude-code/CLAUDE.md
adapter: adapters/claude-code/commands/
default runtime: ~/.claude
ownership: ~/.claude/agent-foundry/ plus managed import block in ~/.claude/CLAUDE.md
```

Hermes:

```text
adapter: adapters/hermes/skills/
default runtime: ~/.hermes/skills/
ownership: managed skill directories with .agent-foundry-managed
```

ChatGPT:

```text
adapter: adapters/chatgpt/custom-instructions.md
adapter: adapters/chatgpt/knowledge/
runtime: manual project/custom GPT import
```

## Safety Rules

- Run `python3 scripts/check_consistency.py` before installing.
- Use dry-runs before writes.
- Treat runtime files as shared user-owned environments.
- Central files use managed blocks or imports, not full replacement.
- Skill directories use `.agent-foundry-managed` markers.
- Refuse unmanaged runtime paths by default.
- Use `--force` only after confirming an existing path should be adopted by Agent Foundry.
- Keep `runtime/local/` out of git and portable snapshots.
