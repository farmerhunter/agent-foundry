import tempfile
import uuid
from pathlib import Path

from local_collaboration_ledger import LocalCollaborationLedger
import local_collaboration_control_plane as cp
import local_collaboration_scheduler as sc


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


if __name__ == "__main__":
    test_initialize_and_offline_transitions(); test_exact_retry_and_divergence_hold(); test_remote_never_confirmed_by_observation(); test_closed_payload_and_resume_gate(); test_caller_project_binding_and_disabled_gate(); print("ok")
