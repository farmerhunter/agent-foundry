import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
import shutil
from pathlib import Path

from local_collaboration_ledger import LocalCollaborationLedger
import local_collaboration_control_plane as cp
import local_collaboration_scheduler as sc


def _filesystem_snapshot(path):
    """Capture authority and SQLite sidecars for zero-side-effect probes."""
    snapshot = {}
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if candidate.exists():
            stat = candidate.stat()
            snapshot[str(candidate)] = (True, stat.st_mtime_ns, stat.st_size, candidate.read_bytes())
        else:
            snapshot[str(candidate)] = (False, None, None, None)
    return snapshot


def _assert_filesystem_unchanged(path, before):
    assert _filesystem_snapshot(path) == before


def _control_request(pid):
    return {"project_id": pid, "occurred_at": "2026-08-11T00:00:00Z", "timestamp_provenance": "explicit",
      "work": {"project_id": pid, "work_id": "w1", "issue": 404, "objective": "local scheduler", "stage": "implementation", "phase": "orch-03", "role": "Implementer", "root_budget_tokens": 100, "remaining_budget_tokens": 100, "issue_anchor": {"issue": 404, "scope": "local scheduler", "risk": "low", "acceptance": "bounded", "durable_anchor": "issue:404", "human_gates": ["none"]}, "durable_anchors": ["issue:404"], "stop_conditions": ["scope drift"]},
      "execution_run": {"run_id": "r1", "work_id": "w1", "role": "Implementer", "state": "active", "context": {"source_timestamp": "2026-08-11T00:00:00Z", "threshold_band": "implementer_small_scoped_implementation", "resource_observations": {"context_tokens": {"provenance": "estimated", "tokens": 100, "source": "test"}}}, "model": {"name": "gpt-5.5", "reasoning": "low"}},
      "dispatch_claim": {"idempotency_key": "k1", "work_id": "w1", "role": "Implementer", "decision_boundary": "local", "transition_semantics": "bounded", "durable_anchor": "issue:404"}, "requested_route": "isolated_execution"}


def _setup(root):
    pid = str(uuid.uuid4()); ledger = LocalCollaborationLedger.create_project(projects_root=root, project_id=pid); ledger.close(); cp.apply_control_request(root, pid, _control_request(pid)); return pid


def test_initialize_and_offline_transitions():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); first = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        assert first["mutation_performed"]
        for n, (a, b) in enumerate((("registered", "queued"), ("queued", "claimed"), ("claimed", "active")), 1):
            req = {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": a, "to_state": b, "transition_sequence": n, "occurred_at": f"2026-08-11T00:00:0{n+1}Z"}
            result = sc.apply_scheduler_request(root, pid, req)
            assert result["mutation_performed"]
            assert sc.apply_scheduler_request(root, pid, req)["decision"] == "duplicate"
        state = sc.replay_scheduler_state(root, pid); assert state["local_state"] == "active"


def test_exact_retry_and_divergence_hold():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); req = {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"}; assert sc.apply_scheduler_request(root, pid, req)["mutation_performed"]; assert sc.apply_scheduler_request(root, pid, req)["decision"] == "duplicate"
        bad = {**req, "occurred_at": "2026-08-11T00:00:02Z"}
        try: sc.apply_scheduler_request(root, pid, bad)
        except sc.SchedulerHold as exc: assert str(exc) in {"hold_duplicate_or_divergent", "hold_scheduler_not_enabled"}
        else: raise AssertionError("divergence must hold")


def test_remote_never_confirmed_by_observation():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"}); result = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": str(uuid.uuid4()), "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"}); assert result["mutation_performed"]; state = sc.replay_scheduler_state(root, pid); assert state["remote_intent_state"] == "accepted_local"


def test_remote_predecessor_guards():
    """Remote outcomes require the explicit pending materialization step."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        for operation, extra in (("observe", {"observed_remote_state": "open"}), ("failure", {}), ("conflict", {}), ("cancel", {})):
            try:
                sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": operation, "intent_id": intent, **extra, "occurred_at": "2026-08-11T00:00:03Z"})
            except sc.SchedulerHold as exc:
                assert str(exc) == "hold_transition_order"
            else:
                raise AssertionError(f"{operation} must require pending materialization")
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:04Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:05Z"})
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:06Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_transition_order"
        else:
            raise AssertionError("observed state must not silently re-enter pending")


def test_observation_and_terminal_use_current_attempt():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:03Z"})
        observed = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:04Z"})
        assert observed["event_batch"][0]["payload"]["payload"]["attempt_sequence"] == 1
        terminal = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "conflict", "intent_id": intent, "occurred_at": "2026-08-11T00:00:05Z"})
        assert terminal["event_batch"][0]["payload"]["payload"]["attempt_sequence"] == 1
        assert sc.replay_scheduler_state(root, pid)["remote_intent_state"] == "conflict"


def test_retry_requires_receipt_and_advances_only_after_failed_attempt():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "occurred_at": "2026-08-11T00:00:03Z"})
        # An outcome belongs to attempt 1; an arbitrary attempt 2 is not a retry.
        ledger_path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        before = len(ledger.list_events()); ledger.close()
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "attempt_sequence": 2, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:04Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_transition_order"
        else:
            raise AssertionError("observation cannot invent a new attempt")
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        assert len(ledger.list_events()) == before
        ledger.close()
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "failure", "intent_id": intent, "classification": "hold_readback_unavailable", "occurred_at": "2026-08-11T00:00:04Z"})
        assert sc.replay_scheduler_state(root, pid)["remote_intent_state"] == "readback_unavailable"
        retry = {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "attempt_sequence": 2, "occurred_at": "2026-08-11T00:00:05Z"}
        try:
            sc.apply_scheduler_request(root, pid, retry)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_retry_receipt_required"
        else:
            raise AssertionError("retry without authorization must hold")
        retry.update({"retry_receipt_ref": "issue:404/retry-1", "retry_receipt_digest": "a" * 64, "retry_authority": "Human"})
        result = sc.apply_scheduler_request(root, pid, retry)
        assert result["mutation_performed"]
        assert sc.replay_scheduler_state(root, pid)["attempt_sequence"] == 2


def test_readback_future_attempt_holds_before_append():
    """A readback for attempt N+1 cannot mutate an attempt-N authority."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        desired = sc.replay_scheduler_state(root, pid)["desired_effect_digest"]
        expected = {"kind": "issue", "ref": "opaque-issue", "digest": "a" * 64, "version": "v1"}
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "expected_remote_kind": expected["kind"], "expected_remote_ref": expected["ref"], "expected_remote_digest": expected["digest"], "expected_remote_version": expected["version"], "occurred_at": "2026-08-11T00:00:03Z"})
        ledger_path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        before = ledger.list_events(); before_head = before[-1].event_hash
        ledger.close()

        class Adapter:
            def readback(self, request):
                return {"project_id": pid, "intent_id": intent, "confirmed": True,
                    "adapter_id": "test-adapter", "adapter_version": "1",
                    "expected_remote_kind": expected["kind"], "expected_remote_ref": expected["ref"],
                    "expected_remote_digest": expected["digest"], "expected_remote_version": expected["version"],
                    "readback_digest": "b" * 64, "opaque_receipt_ref": "receipt:1",
                    "occurred_at": "2026-08-11T00:00:04Z", "read_timestamp": "2026-08-11T00:00:04Z",
                    "readback_nonce": "nonce-1", "request_digest": request["request_digest"],
                    "desired_effect_digest": desired}

        request = {"project_id": pid, "work_id": "w1", "operation": "readback", "intent_id": intent,
            "attempt_sequence": 2, "request_digest": "c" * 64, "occurred_at": "2026-08-11T00:00:04Z"}
        try:
            sc.apply_remote_readback(root, pid, intent, Adapter(), request)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_transition_order"
        else:
            raise AssertionError("future readback attempt must hold")
        ledger = LocalCollaborationLedger.open_existing(ledger_path, expected_project_id=pid)
        after = ledger.list_events(); assert len(after) == len(before); assert after[-1].event_hash == before_head
        ledger.close()


def test_closed_payload_and_resume_gate():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        try:
            sc._validate_envelope({"version": sc.VERSION, "project_id": pid, "kind": "scheduler_initialized", "occurred_at": "2026-08-11T00:00:01Z", "timestamp_provenance": "explicit", "payload": {"work_id": "w1", "unknown": True}})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_schema_or_version"
        else:
            raise AssertionError("unknown scheduler payload must hold")
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        for n, (a, b) in enumerate((("registered", "queued"), ("queued", "claimed"), ("claimed", "active"), ("active", "hold")), 1):
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": a, "to_state": b, "transition_sequence": n, "occurred_at": f"2026-08-11T00:00:0{n+1}Z"})
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "hold", "to_state": "queued", "transition_sequence": 5, "occurred_at": "2026-08-11T00:00:06Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_resume_receipt_required"
        else:
            raise AssertionError("resume without receipt must hold")


def test_caller_project_binding_and_disabled_gate():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); other = str(uuid.uuid4())
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": other, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_control_plane_unready"
        else:
            raise AssertionError("caller/project mismatch must hold")
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "disable", "occurred_at": "2026-08-11T00:00:02Z"})
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "enable", "occurred_at": "2026-08-11T00:00:03Z"})
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_disabled_enable_gate"
        else:
            raise AssertionError("disabled enable without gate must hold")

def _remote_setup(root, expected):
    pid = _setup(root)
    sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
    intent = str(uuid.uuid4())
    sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
    sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, **expected, "occurred_at": "2026-08-11T00:00:03Z"})
    return pid, intent


def test_reducer_version_mismatch_is_preappend_hold():
    """Reducer binding rejects a changed version without touching authority files."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        before_events = ledger.list_events(); before_head = before_events[-1].event_hash
        control_state = cp.reduce_control_events([e for e in before_events if e.event_type.startswith("control.")])
        scheduler_events = [e for e in before_events if e.event_type.startswith("scheduler.")]
        pending = scheduler_events[-1]
        altered = sc._event(pid, "remote_observation_recorded", {**pending.payload["payload"], "expected_remote_version": "v2", "observed_remote_state": "open", "classification": "observed_unverified"}, "2026-08-11T00:00:04Z")
        ledger.close()
        before_files = _filesystem_snapshot(path)
        try:
            sc.reduce_scheduler_state(control_state, scheduler_events + [altered])
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_readback_binding_conflict"
        else:
            raise AssertionError("reducer version mismatch must hold")
        check = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        after_events = check.list_events(); check.close()
        assert len(after_events) == len(before_events) and after_events[-1].event_hash == before_head
        _assert_filesystem_unchanged(path, before_files)


def test_planner_observation_version_mismatch_is_preappend_hold():
    """Observation planning rejects a changed expected version before append."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); before = ledger.list_events(); head = before[-1].event_hash; ledger.close()
        before_files = _filesystem_snapshot(path)
        try:
            sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", **{**expected, "expected_remote_version": "v2"}, "occurred_at": "2026-08-11T00:00:04Z"})
        except sc.SchedulerHold as exc: assert str(exc) == "hold_readback_binding_conflict"
        else: raise AssertionError("planner version mismatch must hold")
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); after = ledger.list_events(); assert len(after) == len(before) and after[-1].event_hash == head; ledger.close()
        _assert_filesystem_unchanged(path, before_files)


def test_privacy_binding_mismatch_is_preappend_hold():
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); before = ledger.list_events(); head = before[-1].event_hash; ledger.close()
        before_files = _filesystem_snapshot(path)
        for bad in ({"intent_id": str(uuid.uuid4())}, {"attempt_sequence": 2}, {"expected_remote_version": "v2"}, {"unknown": "x"}):
            request = {"project_id": pid, "work_id": "w1", "operation": "privacy_hold", "intent_id": intent, **expected, "occurred_at": "2026-08-11T00:00:04Z", **bad}
            try: sc.apply_scheduler_request(root, pid, request)
            except sc.SchedulerHold: pass
            else: raise AssertionError("invalid privacy payload must hold")
            ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); after = ledger.list_events(); assert len(after) == len(before) and after[-1].event_hash == head; ledger.close()
            _assert_filesystem_unchanged(path, before_files)


def test_adapter_version_mismatch_is_preappend_hold():
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected); path = Path(root) / pid / "collaboration.db"; desired = sc.replay_scheduler_state(root, pid)["desired_effect_digest"]
        class Adapter:
            def readback(self, request):
                return {"project_id": pid, "intent_id": intent, "confirmed": True, "adapter_id": "adapter", "adapter_version": "1", "expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v2", "readback_digest": "b" * 64, "opaque_receipt_ref": "receipt:1", "occurred_at": "2026-08-11T00:00:04Z", "read_timestamp": "2026-08-11T00:00:04Z", "readback_nonce": "nonce", "request_digest": request["request_digest"], "desired_effect_digest": desired}
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); before = ledger.list_events(); head = before[-1].event_hash; ledger.close()
        before_files = _filesystem_snapshot(path)
        try: sc.apply_remote_readback(root, pid, intent, Adapter(), {"project_id": pid, "work_id": "w1", "operation": "readback", "intent_id": intent, "attempt_sequence": 1, "request_digest": "c" * 64, "occurred_at": "2026-08-11T00:00:04Z"})
        except sc.SchedulerHold as exc: assert str(exc) == "hold_readback_binding_conflict"
        else: raise AssertionError("adapter version mismatch must hold")
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid); after = ledger.list_events(); assert len(after) == len(before) and after[-1].event_hash == head; ledger.close()
        _assert_filesystem_unchanged(path, before_files)


def test_observed_unverified_to_privacy_hold_preserves_all_bindings():
    """A valid observed attempt can become a durable privacy hold."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        observed = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent, "observed_remote_state": "open", **expected, "occurred_at": "2026-08-11T00:00:04Z"})
        assert observed["mutation_performed"]
        state = sc.replay_scheduler_state(root, pid)
        assert state["remote_intent_state"] == "observed_unverified"
        assert state["attempt_sequence"] == 1
        desired = state["desired_effect_digest"]
        result = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "privacy_hold", "intent_id": intent, "attempt_sequence": 1, "desired_effect_digest": desired, **expected, "occurred_at": "2026-08-11T00:00:05Z"})
        assert result["mutation_performed"]
        state = sc.replay_scheduler_state(root, pid)
        assert state["remote_intent_state"] == "privacy_held"
        assert state["local_state"] == "hold"
        assert state["intent_id"] == intent and state["attempt_sequence"] == 1
        assert state["desired_effect_digest"] == desired
        assert all(state[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))
        path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        privacy = [event for event in ledger.list_events() if event.event_type == "scheduler.privacy_hold_recorded"][-1]
        payload = privacy.payload["payload"]
        assert payload["intent_id"] == intent and payload["attempt_sequence"] == 1 and payload["desired_effect_digest"] == desired
        assert all(payload[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))
        ledger.close()


def test_pending_materialization_to_privacy_hold_preserves_all_bindings():
    """A pending attempt can become a durable privacy hold without observation."""
    expected = {"expected_remote_kind": "issue", "expected_remote_ref": "opaque-2", "expected_remote_digest": "c" * 64, "expected_remote_version": "v2"}
    with tempfile.TemporaryDirectory() as root:
        pid, intent = _remote_setup(root, expected)
        pending_state = sc.replay_scheduler_state(root, pid)
        assert pending_state["remote_intent_state"] == "pending_materialization"
        desired = pending_state["desired_effect_digest"]
        result = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "privacy_hold", "intent_id": intent, "attempt_sequence": 1, "desired_effect_digest": desired, **expected, "occurred_at": "2026-08-11T00:00:04Z"})
        assert result["mutation_performed"]
        path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        privacy = [event for event in ledger.list_events() if event.event_type == "scheduler.privacy_hold_recorded"][-1]
        payload = privacy.payload["payload"]
        assert payload["intent_id"] == intent
        assert payload["attempt_sequence"] == 1
        assert payload["desired_effect_digest"] == desired
        assert all(payload[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))
        ledger.close()
        replayed = sc.replay_scheduler_state(root, pid)
        assert replayed["remote_intent_state"] == "privacy_held"
        assert replayed["local_state"] == "hold"
        assert replayed["intent_id"] == intent
        assert replayed["attempt_sequence"] == 1
        assert replayed["desired_effect_digest"] == desired
        assert all(replayed[key] == expected[key] for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"))


def _ledger_authority(path, pid):
    ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
    try:
        events = ledger.list_events()
        return (events[-1].sequence if events else 0,
                events[-1].event_hash if events else "0" * 64)
    finally:
        ledger.close()


def test_replay_exposes_committed_authority_snapshot_without_side_effects():
    """The replay pair covers control+scheduler events, never event payload claims."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        path = Path(root) / pid / "collaboration.db"
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        pending_request = {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "expected_remote_kind": "issue", "expected_remote_ref": "opaque:404", "expected_remote_digest": "a" * 64, "expected_remote_version": "v1", "occurred_at": "2026-08-11T00:00:03Z"}
        pending = sc.apply_scheduler_request(root, pid, pending_request)
        expected = _ledger_authority(path, pid)
        assert (pending["replay"]["authority_generation"], pending["replay"]["authority_head"]) == expected
        before = _filesystem_snapshot(path)
        replay = sc.replay_scheduler_state(root, pid)
        assert (replay["authority_generation"], replay["authority_head"]) == expected
        assert replay["authority_generation"] > replay["events"]
        _assert_filesystem_unchanged(path, before)

        # A scheduler action after the pending intent has a normal append
        # receipt. Its exact duplicate is not a commit and preserves the pair.
        transition_request = {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "registered", "to_state": "queued", "transition_sequence": 1, "occurred_at": "2026-08-11T00:00:04Z"}
        action = sc.apply_scheduler_request(root, pid, transition_request)
        action_pair = _ledger_authority(path, pid)
        assert (action["replay"]["authority_generation"], action["replay"]["authority_head"]) == action_pair
        duplicate = sc.apply_scheduler_request(root, pid, transition_request)
        assert duplicate["decision"] == "duplicate"
        assert (duplicate["replay"]["authority_generation"], duplicate["replay"]["authority_head"]) == action_pair

        changed = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "queued", "to_state": "claimed", "transition_sequence": 2, "occurred_at": "2026-08-11T00:00:05Z"})
        assert changed["mutation_performed"]
        assert (changed["replay"]["authority_generation"], changed["replay"]["authority_head"]) == _ledger_authority(path, pid)
        assert (changed["replay"]["authority_generation"], changed["replay"]["authority_head"]) != expected

        # Prove a separate process observes the same committed pair.
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
        code = "import json,local_collaboration_scheduler as s; print(json.dumps(s.replay_scheduler_state(%r,%r)))" % (root, pid)
        output = subprocess.check_output([sys.executable, "-c", code], text=True, env=env)
        other = json.loads(output)
        assert (other["authority_generation"], other["authority_head"]) == _ledger_authority(path, pid)


def test_replay_authority_snapshot_negative_paths_hold_without_mutation():
    """Read-only replay never turns invalid authorities into a nullable snapshot."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); path = Path(root) / pid / "collaboration.db"
        missing_pid = str(uuid.uuid4()); missing = Path(root) / missing_pid / "collaboration.db"
        before = _filesystem_snapshot(missing)
        try:
            sc.replay_scheduler_state(root, missing_pid)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_ledger_integrity"
        else:
            raise AssertionError("missing/foreign authority must hold")
        _assert_filesystem_unchanged(missing, before)

        # A valid authority copied under a different project directory is not
        # a valid binding for that directory/project identity.
        foreign_pid = str(uuid.uuid4()); foreign_dir = Path(root) / foreign_pid
        foreign_dir.mkdir(mode=0o700)
        foreign = foreign_dir / "collaboration.db"; shutil.copy2(path, foreign); foreign.chmod(0o600)
        foreign_before = _filesystem_snapshot(foreign)
        try:
            sc.replay_scheduler_state(root, foreign_pid)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_ledger_integrity"
        else:
            raise AssertionError("valid but foreign project binding must hold")
        _assert_filesystem_unchanged(foreign, foreign_before)

        # A non-canonical metadata schema remains a schema hold without a
        # replay connection writing WAL/SHM or fixing it.
        connection = sqlite3.connect(path)
        connection.execute("UPDATE ledger_metadata SET value='unsupported' WHERE key='schema_version'")
        connection.commit(); connection.close()
        damaged_before = _filesystem_snapshot(path)
        try:
            sc.replay_scheduler_state(root, pid)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_ledger_schema"
        else:
            raise AssertionError("schema drift must hold")
        _assert_filesystem_unchanged(path, damaged_before)


def test_replay_authority_snapshot_corruption_and_permissions_hold():
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); path = Path(root) / pid / "collaboration.db"
        connection = sqlite3.connect(path)
        connection.execute("UPDATE events SET event_hash=? WHERE sequence=1", ("f" * 64,))
        connection.commit(); connection.close()
        before = _filesystem_snapshot(path)
        try:
            sc.replay_scheduler_state(root, pid)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_ledger_integrity"
        else:
            raise AssertionError("hash-chain corruption must hold")
        _assert_filesystem_unchanged(path, before)

    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); path = Path(root) / pid / "collaboration.db"
        path.chmod(0o644); before = _filesystem_snapshot(path)
        try:
            sc.replay_scheduler_state(root, pid)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_ledger_permission"
        else:
            raise AssertionError("permission drift must hold")
        _assert_filesystem_unchanged(path, before)


def test_replay_authority_snapshot_busy_and_symlink_holds():
    """Busy and symlink failures are classified, never downgraded to null data."""
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        path = Path(root) / pid / "collaboration.db"
        # Keep real WAL/SHM sidecars alive, then take an exclusive write lock
        # from a second SQLite connection. The production read-only open has a
        # bounded 5000ms timeout and must classify the actual lock as busy.
        writer = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        writer.append_event("test.busy_probe", {"probe": "busy"}, root=pid)
        writer._conn.execute("PRAGMA locking_mode=EXCLUSIVE")
        writer._conn.execute("BEGIN EXCLUSIVE")
        before = _filesystem_snapshot(path)
        try:
            started = time.monotonic()
            try:
                sc.replay_scheduler_state(root, pid)
            except sc.SchedulerHold as exc:
                assert str(exc) == "hold_ledger_busy"
            else:
                raise AssertionError("busy authority must hold")
            assert time.monotonic() - started < 6.5
        finally:
            _assert_filesystem_unchanged(path, before)
            writer._conn.execute("ROLLBACK"); writer.close()

    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root); path = Path(root) / pid / "collaboration.db"
        target = Path(root) / "authority-target.db"
        path.rename(target); path.symlink_to(target)
        before = _filesystem_snapshot(path)
        try:
            sc.replay_scheduler_state(root, pid)
        except sc.SchedulerHold as exc:
            assert str(exc) == "hold_ledger_integrity"
        else:
            raise AssertionError("symlink authority must hold")
        _assert_filesystem_unchanged(path, before)


def test_replay_db_wal_without_shm_holds_without_creating_sidecar():
    """A valid copied WAL cannot cause a read-only replay to manufacture SHM."""
    with tempfile.TemporaryDirectory() as source_root, tempfile.TemporaryDirectory() as target_root:
        pid = _setup(source_root); source = Path(source_root) / pid / "collaboration.db"
        writer = LocalCollaborationLedger.open_existing(source, expected_project_id=pid)
        try:
            writer.append_event("test.partial_wal", {"probe": "partial-wal"}, root=pid)
            assert Path(str(source) + "-wal").exists()
            assert Path(str(source) + "-shm").exists()
            target_dir = Path(target_root) / pid; target_dir.mkdir(mode=0o700)
            target = target_dir / "collaboration.db"
            shutil.copy2(source, target); target.chmod(0o600)
            shutil.copy2(Path(str(source) + "-wal"), Path(str(target) + "-wal"))
            Path(str(target) + "-wal").chmod(0o600)
            assert not Path(str(target) + "-shm").exists()
            before = _filesystem_snapshot(target)
            try:
                sc.replay_scheduler_state(target_root, pid)
            except sc.SchedulerHold as exc:
                assert str(exc) == "hold_ledger_integrity"
            else:
                raise AssertionError("DB+WAL without SHM must fail closed")
            _assert_filesystem_unchanged(target, before)
        finally:
            writer.close()


def test_authority_snapshot_schema_definition_is_closed():
    schema = Path(__file__).parent.parent / "schemas" / "local-collaboration-scheduler.schema.yaml"
    text = schema.read_text()
    assert "authority_snapshot:" in text
    assert "required: [authority_generation, authority_head]" in text
    assert "additionalProperties: false" in text


if __name__ == "__main__":
    test_initialize_and_offline_transitions(); test_exact_retry_and_divergence_hold(); test_remote_never_confirmed_by_observation(); test_remote_predecessor_guards(); test_observation_and_terminal_use_current_attempt(); test_closed_payload_and_resume_gate(); test_caller_project_binding_and_disabled_gate(); test_reducer_version_mismatch_is_preappend_hold(); test_planner_observation_version_mismatch_is_preappend_hold(); test_privacy_binding_mismatch_is_preappend_hold(); test_adapter_version_mismatch_is_preappend_hold(); test_observed_unverified_to_privacy_hold_preserves_all_bindings(); test_pending_materialization_to_privacy_hold_preserves_all_bindings(); test_replay_exposes_committed_authority_snapshot_without_side_effects(); test_replay_authority_snapshot_negative_paths_hold_without_mutation(); test_replay_authority_snapshot_corruption_and_permissions_hold(); test_replay_authority_snapshot_busy_and_symlink_holds(); test_replay_db_wal_without_shm_holds_without_creating_sidecar(); test_authority_snapshot_schema_definition_is_closed(); print("ok")
