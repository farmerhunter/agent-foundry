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

## Sync Status

Check local remote/snapshot status:

```bash
python3 scripts/sync_status.py
```

Use this before leaving a machine, before starting work on another machine, or after reconnecting to GitHub.

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
- `usage/asset-usage-log.yaml`

Mitigations:

- run consistency checks after merges;
- keep usage notes concise;
- consider future monthly/agent usage log sharding if conflicts become common.

## Multi-Machine Pattern

Preferred order:

1. Work locally and run `python3 scripts/check_consistency.py`.
2. Export a snapshot before switching machines.
3. Push to GitHub when the network is available.
4. If GitHub is unavailable, move the snapshot by USB, LAN, or another reliable channel.
5. On the receiving machine, stage with `scripts/import_snapshot.py`, review, merge, and run consistency checks.
6. Initialize or review `runtime/local/runtime_manifest.yaml` before installing adapters on the receiving machine.
