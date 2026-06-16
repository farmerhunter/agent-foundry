# Deployment

Agent Foundry is local-first. Core tooling, User Vault records, and installed runtime files are separate layers.

Current scope: this document describes the AF-8 Core/Vault deployment lifecycle. A clean public Core checkout contains workflows, schemas, scripts, templates, docs, adapter profiles, validation tooling, install orchestration, pack planning/apply/update/lifecycle helpers, and runtime status/rollback helpers. Canonical practice and asset records live in a selected User Vault, typically outside the Core checkout. AF-8 keeps the AF-6 install and pack lifecycle baseline, adds runtime adapter/Trae awareness from AF-7, and hardens multi-machine restore, long-running status, selected-output receipt drift, manual targets, and first-run command UX.

```text
Agent Foundry Core + selected User Vault
  -> generated adapters
  -> machine-local runtime manifest
  -> installed runtime copies
  -> real agent usage
  -> local raw usage evidence
  -> shared usage aggregate back into the selected User Vault
```

## Boundaries

- Core checkout: `workflows/`, `schemas/`, `scripts/`, `templates/`, `docs/`, adapter profiles, runtime templates, and sync templates.
- User Vault: `practices/`, `assets/`, `indexes/`, `imports/`, and shared sanitized usage aggregates.
- `usage/usage-aggregate.yaml` in the selected Vault: shared sanitized usage statistics for review.
- `usage/local/`: machine-local raw usage evidence, ignored by git and portable snapshots.
- `adapters/`: generated or maintained adapter outputs.
- `runtime/templates/runtime_manifest.template.yaml`: portable deployment template, tracked in git.
- `runtime/local/runtime_manifest.yaml`: this machine's private deployment state, ignored by git and portable snapshots.
- `~/.agent-foundry/config.yaml`: this machine's private Foundry locator for agents working outside the repo.
- Installed runtime locations such as `~/.codex`, `~/.claude`, `~/.hermes`, and `~/.trae-cn`: downstream copies, not source of truth.

Run Core scripts from the Agent Foundry Core checkout unless a workflow explicitly says otherwise:

```bash
cd "/path/to/agent-foundry"
```

## Fresh Install

Use this on a new machine after cloning or unpacking the Agent Foundry Core checkout.

This flow creates or selects a local User Vault. The Vault may be blank, restored from a private backup, or later populated through a reviewed capability pack.

1. Initialize or select a User Vault:

   ```bash
   python3 scripts/init_vault.py ~/.agent-foundry/vault/my-agent-foundry-vault --core-root . --apply
   ```

2. Write and verify the machine-local Core/Vault locator:

   ```bash
   python3 scripts/foundry_config.py write --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
   python3 scripts/foundry_config.py status
   ```

3. Initialize the machine-local runtime manifest:

   ```bash
   python3 scripts/runtime_manifest.py init
   ```

4. Detect local agent runtimes:

   ```bash
   python3 scripts/runtime_manifest.py detect
   ```

5. Enable only agents that exist and should receive Agent Foundry content:

   ```bash
   python3 scripts/runtime_manifest.py enable codex
   python3 scripts/runtime_manifest.py enable claude-code
   python3 scripts/runtime_manifest.py enable hermes
   python3 scripts/runtime_manifest.py enable trae
   ```

6. If a runtime uses a non-default path, configure it:

   ```bash
   python3 scripts/runtime_manifest.py configure hermes --path <hermes-skills-dir>
   ```

7. Review the install plan:

   ```bash
   python3 scripts/runtime_manifest.py plan
   ```

8. Dry-run the full install:

   ```bash
   python3 scripts/install_foundry.py
   ```

9. Read the status report before applying:

   ```bash
   python3 scripts/sync_status.py
   ```

   Confirm that Core, selected Vault, generated output, runtime targets, manual targets, and receipt state match the machine you intend to update.

10. Apply after reviewing destinations:

   ```bash
   python3 scripts/install_foundry.py --apply
   ```

11. Verify status:

   ```bash
   python3 scripts/sync_status.py
   python3 scripts/foundry_config.py status
   ```

The locator step writes `~/.agent-foundry/config.yaml`. `core_root` points to the public Core checkout; `vault_root` points to the selected user-owned Vault.

## Existing Combined Deployment Migration

Use this only when upgrading an older combined Core/Vault checkout. A clean public Core checkout should not contain active User Vault records. Before extracting records from an older combined deployment, run:

```bash
python3 scripts/plan_vault_extraction.py
```

Then create and verify a local backup, initialize or select the active User Vault target, copy records into that Vault, validate it with `scripts/check_foundry_roots.py`, and dry-run adapter publishing from the selected Vault. The default local pattern is `~/.agent-foundry/vault/agent-foundry-vault-<account>`. Moving records, deleting public copies, creating a private remote, or repointing installed runtimes from a combined repo requires explicit user approval at execution time.

During the actual migration window, pause ordinary harvest, asset discovery, publish, refresh, and runtime install operations unless they explicitly use verified split `core_root` and `vault_root`. The normal end of that window is the successful completion of AF-3 runtime deployment migration (#33), where split Core plus active User Vault can validate, publish, refresh/install or dry-run, detect stale paths, and roll back if needed. AF-3 external-user readiness review (#34) is a post-window audit, not the normal window close point.

## Cross-Machine Split Refresh

Use this on another deployed machine after the public Core and active User Vault have been split.

The public Core cannot fetch, clone, or repair a private Vault automatically. Clone or sync the active User Vault through the private channel you control before running Core scripts. Use the same local path pattern on each deployment, normally `~/.agent-foundry/vault/agent-foundry-vault-<account>`.

1. Refresh or clone the public Core:

   ```bash
   git clone <public-core-url> agent-foundry-core
   cd agent-foundry-core
   git pull --ff-only
   ```

2. Clone or sync the active User Vault into the standard local path:

   ```bash
   git clone <private-vault-url> ~/.agent-foundry/vault/agent-foundry-vault-<account>
   cd ~/.agent-foundry/vault/agent-foundry-vault-<account>
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

ChatGPT remains a manual runtime. Refresh it from `/tmp/agent-foundry-adapters/chatgpt/` after selected-Vault adapter publishing has been reviewed. Do not treat a ChatGPT project or Custom GPT upload as managed local runtime state.

Trae can be represented as a managed local runtime target, but writes under `~/.trae-cn` remain runtime writes. Apply them only after durable human approval confirms the target path and write intent.

Fail closed if the private Vault is absent, its `.agent-foundry-vault.yaml` marker is missing or incompatible with the Core marker, the Core marker is missing, runtime targets are ambiguous, or stale combined-root paths remain in local deployment state. Do not let a public Core checkout infer or fetch private Vault content.

## Status And Drift

`sync_status.py` is the safe first command when a machine may be stale:

```bash
python3 scripts/sync_status.py
```

Use it after long idle periods, after switching machines, after pulling Core or Vault changes, before runtime apply, and when a rule appears not to affect an agent.

The report distinguishes:

- Core remote progress: fetch/pull before publishing or applying if this checkout is behind.
- selected Vault: the canonical practice/asset source.
- generated output: selected-Vault adapter files that can be reviewed before install.
- activation freshness: whether active practice/asset IDs are represented in generated output.
- runtime receipt: which generated output was installed to local runtimes.
- selected-output drift: installed files no longer match the selected generated output.
- manual targets: ChatGPT requires manual import.
- runtime write gates: Trae and other managed runtime writes require explicit approval before apply.

Repair stale state in this order:

1. Bring Core and the selected Vault to the intended versions.
2. Publish selected-Vault generated output.
3. Run `install_foundry.py` as a dry-run.
4. Read `sync_status.py`.
5. Apply runtime install only after the expected runtime destinations and manual targets are clear.

Do not repair generated-output or runtime drift by editing unrelated Vault records. Do not copy another machine's local runtime receipt, local manifest, agent runtime directories, or ChatGPT project state as canonical truth.

## External-User Boundary

AF-8 provides a tested local-first setup baseline for a new user or machine: clone Core, initialize or select a Vault, deploy the mandatory bootstrap pack, publish selected generated output, inspect status, and then explicitly dry-run or apply managed runtime installs. It also verifies multi-machine restore, selected-output drift reporting, first-run command UX, and capability pack fail-closed behavior. This is not yet a marketplace, hosted installer, or fully polished product wizard, but it is no longer only maintainer implementation evidence.

The supported public setup baseline expects:

- public Core that does not require current-user Vault content;
- a user-owned Vault location, private by default;
- an implemented blank Vault initializer and validation checks;
- locator support for distinct `core_root` and `vault_root`;
- adapter generation from the selected user's Vault, not a bundled current-user Vault;
- runtime install that can verify split Core/Vault state before writing managed runtime files;
- mandatory bootstrap pack deployment followed by optional capability pack deployment when the user selects a known pack;
- ChatGPT manual import boundaries and managed runtime receipt/status reporting for Codex, Claude Code, Hermes, and Trae.

Remaining productization work includes friendlier command wrapping, broader pack distribution/update UX, remote trust policy, and physical multi-machine onboarding evidence.

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

3. Review status before writing runtime files:

   ```bash
   python3 scripts/sync_status.py
   ```

   Confirm receipt state, manual targets, selected generated output, and any Trae/runtime write approval requirement.

4. Apply to enabled local targets only after the status report matches the intended machine:

   ```bash
   python3 scripts/install_foundry.py --apply
   ```

5. For ChatGPT, manually update project/custom GPT instructions and knowledge files from reviewed selected-Vault generated output, not from Core adapter templates.

6. Verify the locator still points at this repo and status remains clean:

   ```bash
   python3 scripts/foundry_config.py status
   python3 scripts/sync_status.py
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

5. Review status for that target before applying:

   ```bash
   python3 scripts/sync_status.py
   ```

   For Trae or any managed runtime path, confirm durable human approval exists before writing runtime files.

6. Apply after review:

   ```bash
   python3 scripts/install_foundry.py --target <target> --apply
   ```

Supported local targets: `codex`, `claude-code`, `hermes`, `trae`. `chatgpt` is `manual`.

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

3. Review status before writing to the new path:

   ```bash
   python3 scripts/sync_status.py
   ```

   Confirm the selected generated output, receipt state, manual targets, and any Trae/runtime write approval requirement.

4. Apply:

   ```bash
   python3 scripts/install_foundry.py --target <target> --apply
   ```

5. If the old path should be cleaned, do it manually after verifying ownership markers or managed blocks.

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
   python3 scripts/sync_status.py
   ```

5. Apply runtime install only after the dry-run and status report identify the expected selected Vault, generated output, runtime receipt state, manual targets, and any Trae/runtime write approval requirement:

   ```bash
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
   python3 scripts/sync_status.py
   ```

   Apply runtime install only after the dry-run and status report identify the intended selected Vault, generated output, runtime receipt state, manual targets, and any runtime-write approval requirement.

Portable snapshots include `runtime/templates/` but exclude `runtime/local/`, because local runtime deployment state is machine-specific.

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

## Safety Rules

- Run `python3 scripts/check_consistency.py` before installing.
- Use dry-runs before writes.
- Treat runtime files as shared user-owned environments.
- Central files use managed blocks or imports, not full replacement.
- Skill directories use `.agent-foundry-managed` markers.
- Refuse unmanaged runtime paths by default.
- Use `--force` only after confirming an existing path should be adopted by Agent Foundry.
- Keep `runtime/local/` out of git and portable snapshots.
