# Deployment

Agent Foundry is local-first. The repository is the canonical workspace; installed agent runtime files are downstream copies.

Current scope: this document describes the current single-repo maintainer setup, where Foundry Core and the maintainer's User Vault share one repository root. It is not a complete external-user quickstart. External-user setup requires the AF-3 physical Core/Vault split and AF-4 onboarding work described in `docs/roadmap.md`.

```text
Agent Foundry repo
  -> generated adapters
  -> machine-local runtime manifest
  -> installed runtime copies
  -> real agent usage
  -> local raw usage evidence
  -> shared usage aggregate back into Agent Foundry
```

## Boundaries

- `practices/`, `assets/`, `indexes/`: canonical vault.
- `usage/usage-aggregate.yaml`: shared sanitized usage statistics for review.
- `usage/local/`: machine-local raw usage evidence, ignored by git and portable snapshots.
- `workflows/`, `schemas/`, `scripts/`, `templates/`: Foundry system.
- `adapters/`: generated or maintained adapter outputs.
- `runtime/templates/runtime_manifest.template.yaml`: portable deployment template, tracked in git.
- `runtime/local/runtime_manifest.yaml`: this machine's private deployment state, ignored by git and portable snapshots.
- `~/.agent-foundry/config.yaml`: this machine's private Foundry locator for agents working outside the repo.
- Installed runtime locations such as `~/.codex`, `~/.claude`, and `~/.hermes`: downstream copies, not source of truth.

Run repo scripts from the Agent Foundry repo root unless a workflow explicitly says otherwise:

```bash
cd "/path/to/agent-foundry"
```

## Fresh Install

Use this on a new maintainer machine after cloning or unpacking the current combined Agent Foundry repository.

Do not use this flow to claim a clean external-user installation: it installs adapters from the currently selected Vault, which is still the maintainer Vault in the AF-2 staging repository.

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
   python3 scripts/foundry_config.py status
   ```

The apply step writes `~/.agent-foundry/config.yaml`. In the current AF-2 repository, `core_root`, `vault_root`, and `repo_root` still point to the same combined checkout. After AF-3, those fields must support a public Core path and a separate user-owned Vault path.

## Maintainer Vault Migration Gate

Do not move the maintainer Vault or create a private Vault remote from this deployment flow. Before any extraction, run:

```bash
python3 scripts/plan_vault_extraction.py
```

Then create and verify a local backup, initialize or select the private Vault target, validate it with `scripts/check_foundry_roots.py`, and dry-run adapter publishing from the selected Vault. Moving records, deleting public copies, creating a private remote, or repointing installed runtimes from the combined repo requires explicit user approval at execution time.

During the actual migration window, pause ordinary harvest, asset discovery, publish, refresh, and runtime install operations unless they explicitly use verified split `core_root` and `vault_root`. The normal end of that window is the successful completion of AF-3 runtime deployment migration (#33), where split Core plus private maintainer Vault can validate, publish, refresh/install or dry-run, detect stale paths, and roll back if needed. AF-3 external-user readiness review (#34) is a post-window audit, not the normal window close point.

## Cross-Machine Split Refresh

Use this on another deployed machine after the public Core and private Vault have been split.

The public Core cannot fetch, clone, or repair a private Vault automatically. Clone or sync the private Vault through the private channel you control before running Core scripts.

1. Refresh or clone the public Core:

   ```bash
   git clone <public-core-url> agent-foundry-core
   cd agent-foundry-core
   git pull --ff-only
   ```

2. Clone or sync the private Vault into a separate local path:

   ```bash
   git clone <private-vault-url> <private-vault-path>
   cd <private-vault-path>
   git pull --ff-only
   cd <public-core-path>
   ```

3. Write and verify the machine-local locator:

   ```bash
   python3 scripts/foundry_config.py write \
     --repo-root <public-core-path> \
     --core-root <public-core-path> \
     --vault-root <private-vault-path>
   python3 scripts/foundry_config.py status
   ```

4. Validate the selected roots and layout markers:

   ```bash
   python3 scripts/check_foundry_roots.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path>
   ```

5. Review the read-only deployment migration plan:

   ```bash
   python3 scripts/migrate_deployment.py plan \
     --core-root <public-core-path> \
     --vault-root <private-vault-path>
   ```

6. Publish selected-Vault adapter outputs into a review directory:

   ```bash
   python3 scripts/publish_adapters.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --output-root /tmp/agent-foundry-adapters \
     --apply
   ```

7. Review local runtime targets:

   ```bash
   python3 scripts/runtime_manifest.py status
   python3 scripts/runtime_manifest.py plan
   ```

8. Dry-run runtime install from the verified Core checkout:

   ```bash
   python3 scripts/install_foundry.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --adapter-root /tmp/agent-foundry-adapters
   ```

9. Apply runtime install only after the dry-run destinations, selected Vault, generated adapter output, and stale path report are clean:

   ```bash
   python3 scripts/install_foundry.py \
     --core-root <public-core-path> \
     --vault-root <private-vault-path> \
     --adapter-root /tmp/agent-foundry-adapters \
     --apply
   python3 scripts/sync_status.py
   python3 scripts/foundry_config.py status
   ```

ChatGPT remains a manual runtime. Refresh it from `adapters/chatgpt/` after adapter publishing has been reviewed.

Fail closed if the private Vault is absent, its `.agent-foundry-vault.yaml` marker is missing or incompatible with the Core marker, the Core marker is missing, runtime targets are ambiguous, or stale combined-root paths remain in local deployment state. Do not let a public Core checkout infer or fetch private Vault content.

## External-User Boundary

AF-2 defines the setup boundary but does not implement the public setup path.

A future external-user setup needs:

- public Core that does not require maintainer Vault content;
- a user-owned Vault location, private by default;
- an implemented blank Vault initializer and validation checks;
- locator support for distinct `core_root` and `vault_root`;
- adapter generation from the selected user's Vault, not the maintainer Vault;
- runtime install that can verify split Core/Vault state before writing managed runtime files;
- onboarding choices for empty Vault, starter capability packs, runtime-asset imports, or mixed setup.

Until that work is complete, deployment commands in this file are safe for the maintainer workflow and useful as implementation evidence, but they are not a tested new-user onboarding path.

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

5. Verify the locator still points at this repo:

   ```bash
   python3 scripts/foundry_config.py status
   ```

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
   ./sync.sh pull
   ```

3. Push committed changes when network is available:

   ```bash
   ./sync.sh push
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

6. If the staged snapshot was merged, record it as applied:

   ```bash
   python3 scripts/sync_state.py mark-applied <snapshot.tar.gz>
   ```

7. Initialize or review the receiving machine's local runtime manifest before installing:

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
