# Offline Sync

Agent Foundry should work without reliable GitHub access.

## Policy

Local workspace is primary. GitHub is an async remote backup and distribution channel.

```text
local Agent Foundry
  -> local edits
  -> local consistency check
  -> optional snapshot export
  -> optional remote sync when network is available
```

## Recommended Setup

Use multiple remotes if needed:

```text
origin-github
origin-gitee
origin-local-nas
origin-usb-bare
```

Network failures should not block:

- harvest practices;
- discover assets;
- publish adapters locally;
- record usage evidence;
- export snapshots.

## Snapshot Export

Create a portable offline archive:

```bash
python3 scripts/export_snapshot.py
```

Snapshots are written to:

```text
sync/snapshots/
```

Each snapshot contains `sync/snapshot-manifest.json` with file paths, sizes, and SHA-256 hashes. Snapshot archives are local transfer artifacts and are ignored by git.

Portable snapshots include `runtime/templates/` but exclude `runtime/local/`. Local runtime deployment state is machine-specific and should be initialized or reviewed on each machine.

`scripts/export_snapshot.py` also records the archive SHA-256 in machine-local `sync/local/state.yaml`.

Portable snapshots include sanitized `usage/usage-aggregate.yaml` but exclude raw local usage evidence under `usage/local/`. This lets multiple machines share review statistics without syncing project names, notes, prompts, or other local context.

## Snapshot Import

Import is staging-first and non-destructive:

```bash
python3 scripts/import_snapshot.py <snapshot.tar.gz>
```

The snapshot is extracted under:

```text
sync/imported/
```

Review staged files before merging into the working tree. Do not unpack a received snapshot directly over the live repository.

Compare a staged snapshot with the current working tree:

```bash
python3 scripts/compare_snapshot.py sync/imported/<snapshot-name>
```

After intentionally merging a staged snapshot, record it as applied:

```bash
python3 scripts/sync_state.py mark-applied <snapshot.tar.gz>
```

## Sync Status

Check local remote/snapshot status:

```bash
python3 scripts/sync_status.py
```

Use this before leaving a machine, before starting work on another machine, or after reconnecting to GitHub.

`sync_status.py` reports:

- git branch, remotes, and working tree status;
- latest local snapshot and manifest summary;
- machine-local sync state, including latest exported/imported/applied snapshot hashes;
- runtime manifest status;
- runtime adapter drift between repo adapters and installed managed runtime copies.

## Sync Queue

Use:

```text
sync/pending/
sync/applied/
sync/conflicts/
```

for manual or future scripted sync records. This keeps offline changes explicit even when GitHub is unreachable.

## Conflict Reduction

High-conflict files:

- `indexes/*.yaml`
- `usage/usage-aggregate.yaml`

Mitigations:

- run consistency checks after merges;
- regenerate aggregate rows from local raw logs when needed;
- keep raw usage notes under gitignored `usage/local/`;
- aggregate by month, agent, and hashed machine ID to reduce conflict scope.

## Usage Evidence Sync

Usage evidence has two layers:

- raw local evidence: `usage/local/usage-log.yaml`, gitignored and excluded from snapshots;
- shared aggregate evidence: `usage/usage-aggregate.yaml`, safe to sync and used by review scripts.

Record usage with:

```bash
python3 scripts/record_asset_usage.py --asset-id ASSET-META-001 --agent codex --outcome useful
```

Rebuild shared aggregate evidence from local and legacy logs:

```bash
python3 scripts/aggregate_usage.py --include-legacy
```

Shared aggregate rows include subject type, subject ID, month, agent, hashed machine ID, outcome counts, and last-used date. They intentionally exclude raw project names, notes, prompts, and transcripts.

## Multi-Machine Pattern

Preferred order:

1. Work locally and run `python3 scripts/check_consistency.py`.
2. Export a snapshot before switching machines.
3. Push to GitHub when the network is available.
4. If GitHub is unavailable, move the snapshot by USB, LAN, or another reliable channel.
5. On the receiving machine, stage with `scripts/import_snapshot.py`.
6. Compare with `scripts/compare_snapshot.py`.
7. Review and merge intentionally.
8. Mark the snapshot as applied with `scripts/sync_state.py mark-applied <snapshot.tar.gz>`.
9. Run consistency checks.
10. Initialize or review `runtime/local/runtime_manifest.yaml` before installing adapters on the receiving machine.
