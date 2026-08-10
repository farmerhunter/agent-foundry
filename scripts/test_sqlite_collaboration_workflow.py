#!/usr/bin/env python3
"""Focused ORCH-02-2 SQLite bridge checks."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlite_collaboration_workflow import (
    accepted_backfill,
    discover,
    fresh_onboarding,
    local_action_batch,
    logical_event_uuid,
    read_events,
    accepted_backfill_existing,
)


def event(event_id: str, event_type: str = "assignment", owner: str = "implementer") -> dict:
    return {"event_id": event_id, "event_type": event_type, "occurred_at": "2026-01-01T00:00:00Z", "work_item": {"id": "issue:1"}, "actor_role": "architect", "confidence": "observed", "payload": {"owner_role": owner}}


def run_sqlite_action(root: Path, project_id: str, action_path: Path) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "github_collaboration_helper.py"
    return subprocess.run(
        [sys.executable, str(script), "local-ledger-action-apply", "--ledger-backend", "sqlite", "--projects-root", str(root), "--project-id", project_id, "--action-json", str(action_path), "--json"],
        text=True,
        capture_output=True,
        check=False,
        cwd=script.parents[1],
        env={**os.environ, "PYTHONPATH": str(script.parent)},
    )


def cli_action(action_id: str, *, occurred_at: object = "2026-01-01T00:00:00Z", owner: str = "implementer") -> dict:
    return {"action_id": action_id, "action_type": "assignment", "occurred_at": occurred_at, "work_item": {"id": "issue:1"}, "approved_by_role": "agent", "payload": {"owner_role": owner}}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects"
        first = fresh_onboarding(root, "repo", "farmerhunter/agent-foundry")
        assert first["status"] == "created"
        second = fresh_onboarding(root, "repo", "farmerhunter/agent-foundry")
        assert second["status"] == "reused" and second["project_id"] == first["project_id"]
        assert not list(root.rglob("*.jsonl"))
        pid = first["project_id"]
        a = event("legacy-1")
        result = accepted_backfill(root, "repo", "farmerhunter/agent-foundry", [a])
        assert result["status"] == "ok" and result["event_count"] == 1
        assert read_events(root, pid)[0]["event_id"] == "legacy-1"
        retry = accepted_backfill(root, "repo", "farmerhunter/agent-foundry", [a])
        assert retry["status"] == "ok" and retry["event_count"] == 1
        assert logical_event_uuid(pid, "legacy-1") == logical_event_uuid(pid, "legacy-1")
        divergent = accepted_backfill(root, "repo", "farmerhunter/agent-foundry", [event("legacy-1", owner="reviewer")])
        assert divergent["status"] == "hold"
        action = local_action_batch(root, pid, [event("action-1", "human_approval")])
        assert action["status"] == "ok"
        duplicate_batch = local_action_batch(root, pid, [event("batch-dup"), event("batch-dup")])
        assert duplicate_batch["status"] == "ok" and duplicate_batch["appended_count"] == 1 and duplicate_batch["duplicate_count"] == 1
        existing_migration = accepted_backfill_existing(root, pid, [event("migration-1")])
        assert existing_migration["status"] == "ok" and len(list(root.rglob("collaboration.db"))) == 1
        missing_migration = accepted_backfill_existing(root, "00000000-0000-0000-0000-000000000000", [event("migration-missing")])
        assert missing_migration["status"] == "hold" and len(list(root.rglob("collaboration.db"))) == 1
        assert len(read_events(root, pid)) == 4
        malformed = accepted_backfill(root, "repo", "farmerhunter/agent-foundry", [event("bad", owner="x"), {"event_type": "evidence", "payload": {}}])
        assert malformed["status"] == "hold"
        assert "detail" not in malformed
        assert len(read_events(root, pid)) == 4
        fresh_root = Path(tmp) / "fresh"
        malformed_fresh = accepted_backfill(fresh_root, "repo", "new-project", [{"event_type": "evidence", "payload": {}}])
        assert malformed_fresh["status"] == "hold" and not fresh_root.exists()
        invalid_type_root = Path(tmp) / "invalid-type"
        invalid_type = accepted_backfill(invalid_type_root, "repo", "invalid-type", [event("bad-type", "INVALID TYPE")])
        assert invalid_type["status"] == "hold" and not invalid_type_root.exists()
        oversized_root = Path(tmp) / "oversized"
        oversized = accepted_backfill(oversized_root, "repo", "oversized", [event("large", owner="x"), {**event("large-2"), "payload": {"blob": "x" * (70 * 1024)}}])
        assert oversized["status"] == "hold" and not oversized_root.exists()
        board = subprocess.run([sys.executable, "scripts/github_collaboration_helper.py", "foundry-board", "--ledger-backend", "sqlite", "--projects-root", str(root), "--project-id", pid, "--json"], text=True, capture_output=True, check=False)
        assert board.returncode == 0 and '"storage": "sqlite"' in board.stdout and '"accepted_count": 1' in board.stdout, (board.returncode, board.stdout, board.stderr)
        authority = root / pid / "collaboration.db"
        authority.write_bytes(authority.read_bytes()[:64])
        before_mtime = authority.stat().st_mtime_ns
        sidecars_before = {suffix: Path(str(authority) + suffix).exists() for suffix in ("-wal", "-shm")}
        corrupt_action = local_action_batch(root, pid, [event("corrupt-existing")])
        assert corrupt_action["status"] == "hold" and corrupt_action["reason"] == "integrity"
        assert authority.stat().st_mtime_ns == before_mtime
        assert sidecars_before == {suffix: Path(str(authority) + suffix).exists() for suffix in ("-wal", "-shm")}

        # SQLite action timestamps are validated before authority resolution or
        # any writable open.  Invalid input must not create a project or sidecars.
        invalid_root = Path(tmp) / "invalid-action"
        invalid_action = Path(tmp) / "invalid-action.json"
        invalid_action.write_text(json.dumps(cli_action("invalid", occurred_at="2026-01-01T00:00:00.000Z")), encoding="utf-8")
        invalid_run = run_sqlite_action(invalid_root, "00000000-0000-0000-0000-000000000000", invalid_action)
        assert invalid_run.returncode == 6
        invalid_output = invalid_run.stdout + invalid_run.stderr
        assert "sqlite_action_timestamp_invalid" in invalid_output and "2026-01-01" not in invalid_output
        assert "mutation_performed" in invalid_output and "true" not in invalid_output.lower()
        assert not invalid_root.exists()

        action_root = Path(tmp) / "cli-actions"
        onboard = fresh_onboarding(action_root, "repo", "example/tiny-ipa")
        action_pid = onboard["project_id"]
        action_path = Path(tmp) / "action.json"
        action_path.write_text(json.dumps(cli_action("cli-action")), encoding="utf-8")
        first_run = run_sqlite_action(action_root, action_pid, action_path)
        assert first_run.returncode == 0, (first_run.stdout, first_run.stderr)
        first_doc = json.loads(first_run.stdout)
        assert first_doc["status"] == "ok" and first_doc["appended_count"] == 1 and first_doc["duplicate_count"] == 0
        db_path = action_root / action_pid / "collaboration.db"
        db_mtime = db_path.stat().st_mtime_ns
        sidecars = {suffix: Path(str(db_path) + suffix).exists() for suffix in ("-wal", "-shm")}
        retry_run = run_sqlite_action(action_root, action_pid, action_path)
        assert retry_run.returncode == 0, (retry_run.stdout, retry_run.stderr)
        retry_doc = json.loads(retry_run.stdout)
        assert retry_doc["status"] == "ok" and retry_doc["appended_count"] == 0 and retry_doc["duplicate_count"] == 1
        changed_timestamp = Path(tmp) / "changed-timestamp.json"
        changed_timestamp.write_text(json.dumps(cli_action("cli-action", occurred_at="2026-01-01T00:00:01Z")), encoding="utf-8")
        changed_run = run_sqlite_action(action_root, action_pid, changed_timestamp)
        assert changed_run.returncode == 6
        changed_doc = json.loads(changed_run.stdout)
        assert changed_doc["status"] == "hold" and changed_doc["reason"] == "conflict" and changed_doc["mutation_performed"] is False
        changed_business = Path(tmp) / "changed-business.json"
        changed_business.write_text(json.dumps(cli_action("cli-action", owner="reviewer")), encoding="utf-8")
        business_run = run_sqlite_action(action_root, action_pid, changed_business)
        assert business_run.returncode == 6
        business_doc = json.loads(business_run.stdout)
        assert business_doc["status"] == "hold" and business_doc["reason"] == "conflict" and business_doc["mutation_performed"] is False
        invalid_existing = Path(tmp) / "invalid-existing.json"
        invalid_existing.write_text(json.dumps(cli_action("invalid-existing", occurred_at="2026-01-01T00:00:00+00:00")), encoding="utf-8")
        invalid_before_mtime = db_path.stat().st_mtime_ns
        invalid_before_sidecars = {suffix: Path(str(db_path) + suffix).exists() for suffix in ("-wal", "-shm")}
        invalid_existing_run = run_sqlite_action(action_root, action_pid, invalid_existing)
        assert invalid_existing_run.returncode == 6
        assert "sqlite_action_timestamp_invalid" in invalid_existing_run.stdout and "00:00+00:00" not in invalid_existing_run.stdout
        assert db_path.stat().st_mtime_ns == invalid_before_mtime
        assert invalid_before_sidecars == {suffix: Path(str(db_path) + suffix).exists() for suffix in ("-wal", "-shm")}
        print(json.dumps({"status": "ok", "project_id": pid, "events": 2}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
