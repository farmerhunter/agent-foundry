#!/usr/bin/env python3
"""Fixture-only ORCH-04 front-door evidence harness.

This script owns the evidence interpretation for the disposable #543-D1
walkthrough.  It deliberately uses only public owner APIs and emits a small,
privacy-safe receipt; it is not a product API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping

from local_collaboration_ledger import LocalCollaborationLedger
from sqlite_collaboration_workflow import fresh_onboarding, local_action_batch


VERSION = "orch04-d1-fixture-evidence-v1"
PRIVATE_TMP = Path("/private/tmp")
ACTION_OCCURRED_AT = "2026-08-14T00:00:00Z"


class _Hold(RuntimeError):
    def __init__(self, outcome: str):
        super().__init__(outcome)
        self.outcome = outcome


def _token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _stage(outcome: str = "not_entered", **values: Any) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "appended_count": 0,
        "duplicate_count": 0,
        "mutation_performed": False,
        **values,
    }


def _empty_receipt(root: Path, project_binding: str) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "source_binding": "external_execution_preflight_required",
        "fixture_token": _token(str(root)),
        "project_token": _token(project_binding),
        "outcome": "held_preflight",
        "stages": {
            "onboarding": _stage(),
            "action": _stage(),
            "duplicate": _stage(),
            "timestamp_hold": _stage(),
        },
        "human_walkthrough": {
            "recovery_explanation": "not_collected_by_harness",
            "scores": "not_collected_by_harness",
        },
        "cleanup": "not_started",
    }


def _validate_inputs(root: Path, project_binding: str) -> Path:
    if not root.is_absolute() or root.parent != PRIVATE_TMP or not root.name.startswith("orch-04-4-"):
        raise _Hold("held_preflight")
    if root.exists() or root.is_symlink() or os.path.lexists(root):
        raise _Hold("held_preflight")
    try:
        uuid.UUID(project_binding)
    except (ValueError, TypeError, AttributeError) as exc:
        raise _Hold("held_preflight") from exc
    if not project_binding.startswith("b21487d3-"):
        raise _Hold("held_preflight")
    return root


def _owned_root(root: Path) -> tuple[int, int]:
    root.mkdir(mode=0o700)
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise _Hold("held_preflight")
    return info.st_dev, info.st_ino


def _cleanup(root: Path, identity: tuple[int, int] | None) -> str:
    if identity is None:
        return "not_started"
    try:
        info = root.lstat()
        if (info.st_dev, info.st_ino) != identity or stat.S_ISLNK(info.st_mode):
            return "held_cleanup"
        shutil.rmtree(root)
        return "complete" if not os.path.lexists(root) else "held_cleanup"
    except OSError:
        return "held_cleanup"


def _snapshot(root: Path, project_id: str) -> tuple[int, str, int]:
    snapshot = LocalCollaborationLedger.authority_snapshot(
        root / project_id / "collaboration.db", expected_project_id=project_id
    )
    generation = getattr(snapshot, "authority_generation", None)
    head = getattr(snapshot, "authority_head", None)
    events = getattr(snapshot, "events", None)
    if (not isinstance(generation, int) or isinstance(generation, bool) or generation < 0
            or not isinstance(head, str) or len(head) != 64
            or not isinstance(events, tuple)):
        raise _Hold("held_owner_api_contract_mismatch")
    return generation, head, len(events)


def _action() -> dict[str, Any]:
    return {
        "event_id": "orch04-d1-synthetic-action",
        "event_type": "assignment",
        "occurred_at": ACTION_OCCURRED_AT,
        "work_item": {"id": "synthetic:orch04-d1"},
        "actor_role": "human",
        "confidence": "observed",
        "payload": {"owner_role": "synthetic-adopter"},
    }


def _decode_action(result: Mapping[str, Any], expected: tuple[int, int]) -> tuple[str, int, int, bool]:
    status = result.get("status")
    appended = result.get("appended_count")
    duplicate = result.get("duplicate_count")
    mutation = result.get("mutation_performed")
    logical_ids = result.get("logical_event_ids")
    if (status != "ok" or not isinstance(appended, int) or isinstance(appended, bool)
            or not isinstance(duplicate, int) or isinstance(duplicate, bool)
            or not isinstance(mutation, bool) or not isinstance(logical_ids, list)
            or logical_ids != ["orch04-d1-synthetic-action"]
            or (appended, duplicate) != expected):
        raise _Hold("held_action_semantics")
    return status, appended, duplicate, mutation


def _public_timestamp_hold(root: Path, project_id: str) -> Mapping[str, Any]:
    """Exercise the public CLI action route with a missing timestamp.

    The action document is short-lived inside the invocation-owned fixture
    root.  CLI stdout is decoded in memory and never becomes receipt data.
    """
    action_path = root / "invalid-action.json"
    action = {
        "action_id": "orch04-d1-invalid-timestamp",
        "action_type": "assignment",
        "work_item": {"id": "synthetic:orch04-d1"},
        "approved_by_role": "agent",
        "payload": {"owner_role": "synthetic-adopter"},
    }
    action_path.write_text(json.dumps(action, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    helper = Path(__file__).resolve().parent / "github_collaboration_helper.py"
    try:
        completed = subprocess.run(
            [sys.executable, str(helper), "local-ledger-action-apply", "--ledger-backend", "sqlite",
             "--projects-root", str(root), "--project-id", project_id,
             "--action-json", str(action_path), "--json"],
            cwd=helper.parent.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        try:
            value = json.loads(completed.stdout)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise _Hold("held_timestamp_hold_semantics") from exc
        if (completed.returncode != 6 or not isinstance(value, Mapping)
                or set(value) != {"status", "error", "mutation_performed"}
                or value.get("status") != "hold"
                or value.get("error") != "sqlite_action_timestamp_invalid"
                or value.get("mutation_performed") is not False):
            raise _Hold("held_timestamp_hold_semantics")
        return value
    except (OSError, subprocess.SubprocessError):
        raise _Hold("held_timestamp_hold_semantics") from None
    finally:
        try:
            action_path.unlink(missing_ok=True)
        except OSError:
            raise _Hold("held_cleanup") from None


def run(private_root: str | Path, project_binding: str) -> dict[str, Any]:
    root = Path(private_root)
    receipt = _empty_receipt(root, project_binding)
    identity: tuple[int, int] | None = None
    try:
        root = _validate_inputs(root, project_binding)
        identity = _owned_root(root)
        onboarding = fresh_onboarding(root, "synthetic_fixture", "orch04-d1:" + project_binding)
        if onboarding.get("status") != "created" or onboarding.get("mutation_performed") is not True:
            receipt["stages"]["onboarding"] = _stage("held_onboarding")
            raise _Hold("held_onboarding")
        project_id = onboarding.get("project_id")
        if not isinstance(project_id, str):
            receipt["stages"]["onboarding"] = _stage("held_owner_api_contract_mismatch")
            raise _Hold("held_owner_api_contract_mismatch")
        before = _snapshot(root, project_id)
        receipt["stages"]["onboarding"] = _stage("created", event_count=before[2], mutation_performed=True)

        receipt["stages"]["action"] = _stage("entered")
        action = _decode_action(local_action_batch(root, project_id, [_action()]), (1, 0))
        after_action = _snapshot(root, project_id)
        if after_action[0] != before[0] + 1 or after_action[2] != before[2] + 1 or after_action[1] == before[1]:
            raise _Hold("held_action_semantics")
        receipt["stages"]["action"] = _stage("appended", status=action[0], appended_count=action[1], duplicate_count=action[2], mutation_performed=action[3])

        receipt["stages"]["duplicate"] = _stage("entered")
        duplicate = _decode_action(local_action_batch(root, project_id, [_action()]), (0, 1))
        after_duplicate = _snapshot(root, project_id)
        if after_duplicate != after_action or duplicate[3]:
            raise _Hold("held_duplicate_semantics")
        receipt["stages"]["duplicate"] = _stage("duplicate", status=duplicate[0], appended_count=duplicate[1], duplicate_count=duplicate[2], mutation_performed=duplicate[3], authority_unchanged=True)

        receipt["stages"]["timestamp_hold"] = _stage("entered")
        timestamp_hold = _public_timestamp_hold(root, project_id)
        after_timestamp = _snapshot(root, project_id)
        if after_timestamp != after_duplicate:
            raise _Hold("held_timestamp_hold_semantics")
        receipt["stages"]["timestamp_hold"] = _stage("hold", **timestamp_hold, authority_unchanged=True)
        receipt["outcome"] = "fixture_evidence_complete"
    except _Hold as exc:
        receipt["outcome"] = exc.outcome
        for stage in receipt["stages"].values():
            if stage["outcome"] == "entered":
                stage["outcome"] = exc.outcome
    except Exception:
        receipt["outcome"] = "held_owner_api_contract_mismatch"
        for stage in receipt["stages"].values():
            if stage["outcome"] == "entered":
                stage["outcome"] = "held_owner_api_contract_mismatch"
    finally:
        cleanup = _cleanup(root, identity)
        receipt["cleanup"] = cleanup
        if cleanup == "held_cleanup":
            receipt["outcome"] = "held_cleanup"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--synthetic-project-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.private_root, args.synthetic_project_id), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
