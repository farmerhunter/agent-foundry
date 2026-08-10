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
        assert len(read_events(root, pid)) == 2
        malformed = accepted_backfill(root, "repo", "farmerhunter/agent-foundry", [event("bad", owner="x"), {"event_type": "evidence", "payload": {}}])
        assert malformed["status"] == "hold"
        assert len(read_events(root, pid)) == 2
        fresh_root = Path(tmp) / "fresh"
        malformed_fresh = accepted_backfill(fresh_root, "repo", "new-project", [{"event_type": "evidence", "payload": {}}])
        assert malformed_fresh["status"] == "hold" and not fresh_root.exists()
        board = subprocess.run([sys.executable, "scripts/github_collaboration_helper.py", "foundry-board", "--ledger-backend", "sqlite", "--projects-root", str(root), "--project-id", pid, "--json"], text=True, capture_output=True, check=False)
        assert board.returncode == 0 and '"storage": "sqlite"' in board.stdout and '"accepted_count": 1' in board.stdout, (board.returncode, board.stdout, board.stderr)
        print(json.dumps({"status": "ok", "project_id": pid, "events": 2}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
