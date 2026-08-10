#!/usr/bin/env python3
"""Focused ORCH-02-2 SQLite bridge checks."""
from __future__ import annotations

import json
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
        print(json.dumps({"status": "ok", "project_id": pid, "events": 2}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
