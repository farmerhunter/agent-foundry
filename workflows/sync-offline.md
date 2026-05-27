# Offline Sync Workflow

Use this workflow when GitHub or another remote is unreliable.

## Steps

1. Continue working locally.
2. Run:

   ```bash
   python3 scripts/check_consistency.py
   ```

3. Export a snapshot:

   ```bash
   python3 scripts/export_snapshot.py
   ```

4. Check sync status:

   ```bash
   python3 scripts/sync_status.py
   ```

5. If a remote is available, push normally.
6. If not, copy the snapshot from `sync/snapshots/`.

## Conflict Handling

If changes arrive from another machine:

1. Stage the snapshot:

   ```bash
   python3 scripts/import_snapshot.py <snapshot.tar.gz>
   ```

2. Compare staged `practices/`, `assets/`, `indexes/`, `usage/`, and `adapters/`.
3. Run:

   ```bash
   python3 scripts/compare_snapshot.py <staged-dir>
   ```

4. Resolve conflicts.
5. Mark applied when the staged snapshot has been intentionally merged:

   ```bash
   python3 scripts/sync_state.py mark-applied <snapshot.tar.gz>
   ```

6. Run consistency check.
7. Record unresolved issues under `sync/conflicts/`.
