"""Fixture-only checks for the locator-only bounded collaboration bridge."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import jsonschema
import yaml

import bounded_collaboration_runtime_bridge as bridge
import local_collaboration_control_plane as control
import local_collaboration_scheduler as scheduler
from local_collaboration_ledger import LocalCollaborationLedger


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = yaml.safe_load((ROOT / "schemas" / "bounded-collaboration-runtime-bridge.schema.yaml").read_text(encoding="utf-8"))


def _request(project_id: str) -> dict:
    return {
        "project_id": project_id, "occurred_at": "2026-08-17T00:00:00Z", "timestamp_provenance": "explicit",
        "work": {"project_id": project_id, "work_id": "work-bridge", "issue": 548, "objective": "bridge", "stage": "implementation", "phase": "orch-04", "role": "Coordinator", "root_budget_tokens": 100, "remaining_budget_tokens": 100, "issue_anchor": {"issue": 548, "scope": "bridge", "risk": "low", "acceptance": "fixture", "durable_anchor": "issue:548", "human_gates": ["none"]}, "durable_anchors": ["issue:548"], "stop_conditions": ["scope drift"]},
        "execution_run": {"run_id": "run-bridge", "work_id": "work-bridge", "role": "Coordinator", "state": "active", "context": {"source_timestamp": "2026-08-17T00:00:00Z", "threshold_band": "implementer_small_scoped_implementation", "resource_observations": {"context_tokens": {"provenance": "estimated", "tokens": 1, "source": "fixture"}}}, "model": {"name": "gpt-5.5", "reasoning": "low"}},
        "dispatch_claim": {"idempotency_key": "bridge-key", "work_id": "work-bridge", "role": "Coordinator", "decision_boundary": "fixture", "transition_semantics": "bounded", "durable_anchor": "issue:548"}, "requested_route": "isolated_execution",
    }


def _fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, Path, str]:
    temp = tempfile.TemporaryDirectory(); root = Path(temp.name) / "projects"; root.mkdir(); os.chmod(root, 0o700)
    selected = Path(temp.name) / "selected-project"; selected.mkdir(); os.chmod(selected, 0o700)
    project_id = str(uuid.uuid4())
    ledger = LocalCollaborationLedger.create_project(projects_root=root, project_id=project_id)
    ledger.bind_project("path", str(selected.resolve())); ledger.bind_project("repo", "repo-fixture-opaque")
    ledger.close()
    control.apply_control_request(root, project_id, _request(project_id))
    scheduler.apply_scheduler_request(root, project_id, {"project_id": project_id, "work_id": "work-bridge", "operation": "initialize", "occurred_at": "2026-08-17T00:00:01Z"})
    return temp, root.resolve(), selected.resolve(), project_id


def _walk_no_raw(value, forbidden: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert str(key).lower() not in {"path", "repository", "database", "payload", "event", "native", "thread", "stderr", "stdout", "exception"}
            _walk_no_raw(item, forbidden)
    elif isinstance(value, list):
        for item in value: _walk_no_raw(item, forbidden)
    elif isinstance(value, str):
        assert value not in forbidden


def test_real_owner_fixture_reaches_plan_without_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        db = root / project_id / "collaboration.db"; before = hashlib.sha256(db.read_bytes()).hexdigest()
        before_events = len(LocalCollaborationLedger.authority_snapshot(db, expected_project_id=project_id).events)
        receipt = bridge.run(root, selected, "onboard-bridge")
        jsonschema.Draft202012Validator(SCHEMA).validate(json.loads(json.dumps(receipt)))
        assert receipt["terminal_classification"] == "topology_plan_ready"
        assert receipt["mutation_performed"] is False and receipt["production_eligible"] is False and receipt["evidence_class"] == "fixture_only"
        assert hashlib.sha256(db.read_bytes()).hexdigest() == before
        assert len(LocalCollaborationLedger.authority_snapshot(db, expected_project_id=project_id).events) == before_events
        _walk_no_raw(json.loads(json.dumps(receipt)), {str(root), str(selected), "repo-fixture-opaque", str(db)})
    finally:
        temp.cleanup()


def test_duplicate_path_and_missing_scheduler_hold_without_topology() -> None:
    temp, root, selected, _ = _fixture()
    try:
        duplicate = LocalCollaborationLedger.create_project(projects_root=root)
        duplicate.bind_project("path", str(selected.resolve())); duplicate.bind_project("repo", "repo-other"); duplicate.close()
        receipt = bridge.run(root, selected, "onboard-duplicate")
        assert receipt["terminal_classification"] == "unavailable" and receipt["initialization"]["attention_reason"] == "owner_unavailable"
    finally:
        temp.cleanup()
    temp, root, selected, project_id = _fixture()
    try:
        db = root / project_id / "collaboration.db"
        # A fresh authority has bindings but no control/scheduler event history.
        fresh = Path(temp.name) / "fresh"; fresh.mkdir(); os.chmod(fresh, 0o700)
        ledger = LocalCollaborationLedger.create_project(projects_root=root)
        ledger.bind_project("path", str(fresh.resolve())); ledger.bind_project("repo", "repo-fresh"); ledger.close()
        held = bridge.run(root, fresh.resolve(), "onboard-no-scheduler")
        assert held["terminal_classification"] == "unavailable"
        assert db.exists()
    finally:
        temp.cleanup()


def test_cli_rejects_injection_and_preserves_closed_json() -> None:
    temp, root, selected, _ = _fixture()
    try:
        command = [sys.executable, str(ROOT / "scripts" / "bounded_collaboration_runtime_bridge.py"), "--projects-root", str(root), "--project-root", str(selected), "--onboarding-key", "onboard-cli", "--apply"]
        result = subprocess.run(command, env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")}, text=True, capture_output=True, check=False)
        assert result.returncode == 3 and result.stderr == ""
        value = json.loads(result.stdout); assert value["terminal_classification"] == "schema_or_privacy_failure"
        assert str(root) not in result.stdout and str(selected) not in result.stdout
    finally:
        temp.cleanup()


def test_fixture_topology_is_never_production_eligible() -> None:
    temp, root, selected, _ = _fixture()
    try:
        receipt = bridge.run(root, selected, "onboard-fixture", topology_owner=bridge.UnavailableTopologyOwner())
        assert receipt["terminal_classification"] == "topology_plan_ready"
        assert receipt["evidence_class"] == "fixture_only" and receipt["production_eligible"] is False
    finally:
        temp.cleanup()


if __name__ == "__main__":
    test_real_owner_fixture_reaches_plan_without_mutation()
    test_duplicate_path_and_missing_scheduler_hold_without_topology()
    test_cli_rejects_injection_and_preserves_closed_json()
    test_fixture_topology_is_never_production_eligible()
    print("ok")
