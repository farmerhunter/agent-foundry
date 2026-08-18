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
import codex_app_server_thread_connector as app_server
import local_collaboration_control_plane as control
import local_collaboration_scheduler as scheduler
from codex_app_server_thread_connector import PostDispatchHold
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


def test_ordinary_owner_fixture_holds_without_topology_owner_or_mutation() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        db = root / project_id / "collaboration.db"; before = hashlib.sha256(db.read_bytes()).hexdigest()
        before_events = len(LocalCollaborationLedger.authority_snapshot(db, expected_project_id=project_id).events)
        receipt = bridge.run(root, selected, "onboard-bridge")
        jsonschema.Draft202012Validator(SCHEMA).validate(json.loads(json.dumps(receipt)))
        assert receipt["terminal_classification"] == "unavailable"
        assert "topology_plan" not in json.dumps(receipt)
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


def test_corrupt_candidate_holds_before_topology_without_mutating_valid_authority() -> None:
    temp, root, selected, project_id = _fixture()
    try:
        duplicate = LocalCollaborationLedger.create_project(projects_root=root)
        duplicate.bind_project("path", str(selected)); duplicate.bind_project("repo", "repo-corrupt")
        duplicate_path = duplicate.path; duplicate.close(); duplicate_path.write_bytes(b"corrupt authority"); os.chmod(duplicate_path, 0o600)
        valid_path = root / project_id / "collaboration.db"; before = hashlib.sha256(valid_path.read_bytes()).hexdigest()

        class CountingTopology:
            def __init__(self): self.calls = 0
            def read_topology(self, project): self.calls += 1; return {"state": "missing"}
            def apply_topology(self, plan): self.calls += 1; raise AssertionError("apply must not run")
            def read_completion(self, key, project): self.calls += 1; return {"state": "absent"}

        topology = CountingTopology()
        receipt = bridge.run(root, selected, "onboard-corrupt", topology_owner=topology)
        assert receipt["terminal_classification"] == "unavailable" and topology.calls == 0
        assert hashlib.sha256(valid_path.read_bytes()).hexdigest() == before
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
        ordinary = subprocess.run([sys.executable, str(ROOT / "scripts" / "bounded_collaboration_runtime_bridge.py"), "--projects-root", str(root), "--project-root", str(selected), "--onboarding-key", "onboard-cli"], env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")}, text=True, capture_output=True, check=False)
        ordinary_value = json.loads(ordinary.stdout)
        assert ordinary.returncode == 2 and ordinary.stderr == ""
        assert ordinary_value["terminal_classification"] == "unavailable" and "topology_plan" not in ordinary.stdout
    finally:
        temp.cleanup()


def test_in_process_fixture_topology_can_plan_but_is_never_production_eligible() -> None:
    temp, root, selected, _ = _fixture()
    try:
        receipt = bridge.run(root, selected, "onboard-fixture", topology_owner=bridge.FixtureMissingTopologyOwner())
        assert receipt["terminal_classification"] == "topology_plan_ready"
        assert receipt["evidence_class"] == "fixture_only" and receipt["production_eligible"] is False
    finally:
        temp.cleanup()


class _FakeAppServer:
    def __init__(self, root: str):
        self.root = root
        self.items: list[dict] = []
        self.creates = 0
        self.names = 0
        self.fail_start_after_dispatch = False
        self.malformed_start_return = False
        self.fail_read_after_name = False
        self.page_size = 100

    def transport(self, _identity):
        server = self
        class Transport:
            def request(self, method, params):
                if method == "initialize":
                    return {"userAgent": "fixture", "platformFamily": "unix", "platformOs": "macos", "codexHome": "/private"}
                if method == "thread/list":
                    assert params["cwd"] == [server.root]
                    assert params["sourceKinds"] == list(app_server.SOURCE_KINDS)
                    offset = int(params.get("cursor", "0"))
                    page = server.items[offset:offset + server.page_size]
                    following = offset + server.page_size
                    return {"data": [dict(item) for item in page], "nextCursor": str(following) if following < len(server.items) else None}
                if method == "thread/start":
                    server.creates += 1
                    item = {"id": f"native-{server.creates}", "cwd": server.root, "name": None}
                    server.items.append(item)
                    if server.fail_start_after_dispatch:
                        raise PostDispatchHold("response_lost")
                    if server.malformed_start_return:
                        return {"thread": {"id": item["id"], "name": None}}
                    return {"thread": dict(item)}
                if method == "thread/name/set":
                    server.names += 1
                    target = next(item for item in server.items if item["id"] == params["threadId"])
                    target["name"] = params["name"]
                    return {}
                if method == "thread/read":
                    if server.fail_read_after_name and server.names:
                        raise PostDispatchHold("readback_lost")
                    target = next(item for item in server.items if item["id"] == params["threadId"])
                    assert params["includeTurns"] is False
                    return {"thread": dict(target)}
                raise AssertionError(method)
            def notify(self, method, params):
                assert (method, params) == ("initialized", {})
            def close(self):
                pass
        return Transport()


def _production_run(root: Path, selected: Path, server: _FakeAppServer, binary: Path, digest: str, key: str):
    app_server.SUPPORTED_RELEASES[digest] = "codex-cli fixture"
    try:
        return bridge.trusted_initialize_local_host(
            root, selected, key,
            codex_binary=binary,
            expected_binary_sha256=digest,
            expected_binary_version="codex-cli fixture",
            _transport_factory=server.transport,
        )
    finally:
        app_server.SUPPORTED_RELEASES.pop(digest, None)


def test_owner_verified_production_happy_path_and_exact_retry_are_closed() -> None:
    temp, root, selected, _ = _fixture()
    try:
        binary = Path(temp.name) / "codex-fixture"; binary.write_bytes(b"fixture codex"); os.chmod(binary, 0o700)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        server = _FakeAppServer(str(selected))
        first = _production_run(root, selected, server, binary, digest, "production-happy")
        jsonschema.Draft202012Validator(SCHEMA).validate(json.loads(json.dumps(first)))
        assert first["terminal_classification"] == "native_ready"
        assert first["mode"] == "trusted_local_host_apply" and first["production_eligible"] is True
        assert first["evidence_class"] == "owner_verified_local_host" and first["mutation_performed"] is True
        assert (server.creates, server.names) == (3, 3)
        _walk_no_raw(json.loads(json.dumps(first)), {str(root), str(selected), str(binary), *(item["id"] for item in server.items)})
        before = (server.creates, server.names)
        retry = _production_run(root, selected, server, binary, digest, "production-happy")
        jsonschema.Draft202012Validator(SCHEMA).validate(json.loads(json.dumps(retry)))
        assert retry["terminal_classification"] == "native_ready" and retry["mutation_performed"] is False
        assert (server.creates, server.names) == before
    finally:
        temp.cleanup()


def test_production_post_dispatch_create_ambiguity_is_truthful_and_not_retried() -> None:
    temp, root, selected, _ = _fixture()
    try:
        binary = Path(temp.name) / "codex-fixture"; binary.write_bytes(b"fixture codex failure"); os.chmod(binary, 0o700)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        server = _FakeAppServer(str(selected)); server.fail_start_after_dispatch = True
        result = _production_run(root, selected, server, binary, digest, "production-ambiguous")
        jsonschema.Draft202012Validator(SCHEMA).validate(json.loads(json.dumps(result)))
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert (server.creates, server.names) == (1, 0)
        before = (server.creates, server.names)
        retry = _production_run(root, selected, server, binary, digest, "production-ambiguous")
        assert retry["terminal_classification"] == "partial_hold" and retry["mutation_performed"] is False
        assert (server.creates, server.names) == before
    finally:
        temp.cleanup()


def test_production_malformed_successful_create_is_truthful_and_not_retried() -> None:
    temp, root, selected, _ = _fixture()
    try:
        binary = Path(temp.name) / "codex-fixture"; binary.write_bytes(b"fixture codex malformed create"); os.chmod(binary, 0o700)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        server = _FakeAppServer(str(selected)); server.malformed_start_return = True
        result = _production_run(root, selected, server, binary, digest, "production-malformed-create")
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert result["initialization"]["mutation_performed"] is True
        assert (server.creates, server.names) == (1, 0)
        before = (server.creates, server.names)
        retry = _production_run(root, selected, server, binary, digest, "production-malformed-create")
        assert retry["terminal_classification"] == "partial_hold" and retry["mutation_performed"] is False
        assert (server.creates, server.names) == before
    finally:
        temp.cleanup()


def test_production_post_name_readback_failure_is_truthful() -> None:
    temp, root, selected, _ = _fixture()
    try:
        binary = Path(temp.name) / "codex-fixture"; binary.write_bytes(b"fixture codex read failure"); os.chmod(binary, 0o700)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        server = _FakeAppServer(str(selected)); server.fail_read_after_name = True
        result = _production_run(root, selected, server, binary, digest, "production-read-failure")
        assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is True
        assert (server.creates, server.names) == (1, 1)
    finally:
        temp.cleanup()


def test_binary_mismatch_holds_before_transport_factory() -> None:
    temp, root, selected, _ = _fixture()
    try:
        binary = Path(temp.name) / "codex-fixture"; binary.write_bytes(b"fixture codex mismatch"); os.chmod(binary, 0o700)
        calls = []
        result = bridge.trusted_initialize_local_host(
            root, selected, "production-binary-hold",
            codex_binary=binary,
            expected_binary_sha256="0" * 64,
            expected_binary_version="codex-cli fixture",
            _transport_factory=lambda identity: calls.append(identity),
        )
        assert result["terminal_classification"] == "schema_or_privacy_failure"
        assert calls == [] and result["mutation_performed"] is False
    finally:
        temp.cleanup()


def test_paginated_unmanaged_duplicate_and_returned_cwd_drift_hold_before_create() -> None:
    for drift in (False, True):
        temp, root, selected, _ = _fixture()
        try:
            binary = Path(temp.name) / "codex-fixture"; binary.write_bytes(("fixture" + str(drift)).encode()); os.chmod(binary, 0o700)
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            server = _FakeAppServer(str(selected)); server.page_size = 1
            if drift:
                server.items = [{"id": "foreign", "cwd": "/foreign", "name": "unmanaged"}]
            else:
                server.items = [
                    {"id": "one", "cwd": str(selected), "name": "AF18 RoleHub"},
                    {"id": "two", "cwd": str(selected), "name": "AF18 RoleHub"},
                ]
            result = _production_run(root, selected, server, binary, digest, "production-held")
            assert result["terminal_classification"] == "setup_incomplete" and result["mutation_performed"] is False
            assert (server.creates, server.names) == (0, 0)
        finally:
            temp.cleanup()


def test_fixture_receipt_cannot_validate_as_production_branch() -> None:
    temp, root, selected, _ = _fixture()
    try:
        fixture = json.loads(json.dumps(bridge.run(root, selected, "fixture-only")))
        jsonschema.Draft202012Validator(SCHEMA).validate(fixture)
        forged = {**fixture, "mode": "trusted_local_host_apply", "production_eligible": True, "evidence_class": "fixture_only"}
        assert list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(forged))
    finally:
        temp.cleanup()


if __name__ == "__main__":
    test_ordinary_owner_fixture_holds_without_topology_owner_or_mutation()
    test_duplicate_path_and_missing_scheduler_hold_without_topology()
    test_corrupt_candidate_holds_before_topology_without_mutating_valid_authority()
    test_cli_rejects_injection_and_preserves_closed_json()
    test_in_process_fixture_topology_can_plan_but_is_never_production_eligible()
    test_owner_verified_production_happy_path_and_exact_retry_are_closed()
    test_production_post_dispatch_create_ambiguity_is_truthful_and_not_retried()
    test_production_malformed_successful_create_is_truthful_and_not_retried()
    test_production_post_name_readback_failure_is_truthful()
    test_binary_mismatch_holds_before_transport_factory()
    test_paginated_unmanaged_duplicate_and_returned_cwd_drift_hold_before_create()
    test_fixture_receipt_cannot_validate_as_production_branch()
    print("ok")
