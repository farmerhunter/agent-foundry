import hashlib
import uuid
import pytest

from github_materialization_adapter import FakeConnector, MaterializationHold, execute_materialization, plan_materialization

PID = str(uuid.uuid4()); INTENT = str(uuid.uuid4()); H = "a" * 64; C = "b" * 64

def req(**extra):
    base = {"project_id": PID, "work_id": "work-1", "intent_id": INTENT, "attempt_sequence": 1,
            "scheduler_generation": 4, "scheduler_head": H, "desired_effect_digest": H,
            "approved_content_digest": C, "classification": "must_publish", "operation": "issue_comment",
            "repository_id": H, "repository_locator_digest": H, "auth_scope_digest": H,
            "expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_version": "v1",
            "expected_remote_digest": H, "privacy_class": "metadata_only", "adapter_id": "fake",
            "adapter_version": "1", "timestamp_provenance": "explicit", "occurred_at": "2026-08-11T00:00:00Z",
            "gate": {"kind": "fixture_only", "production_eligibility": False, "project_id": PID, "intent_id": INTENT,
                     "attempt_sequence": 1, "operation": "issue_comment", "repository_id": H, "effect_digest": H, "content_digest": C},
            "capability": {"trust_domain": "same_process_reference", "production_eligibility": False, "network_capability": False,
                           "adapter_id": "fake", "adapter_version": "1", "supported_operations": ["issue_comment"]}}
    base.update(extra); return base

def state():
    return {"project_id": PID, "remote_intent_state": "pending_materialization", "intent_id": INTENT,
            "attempt_sequence": 1, "desired_effect_digest": H}

def test_local_only_zero_calls():
    r = req(classification="local_only"); r.pop("gate"); r.pop("capability")
    assert plan_materialization(r, state())["outcome"] == "materialization_not_required"

def test_optional_without_gate_plan_only():
    r = req(classification="optional_sync"); r.pop("gate"); r.pop("capability")
    assert plan_materialization(r, state())["outcome"] == "materialization_plan_ready"

def test_fake_pre_post_and_duplicate():
    c = FakeConnector(); first = execute_materialization(req(), state(), c)
    assert first["outcome"] == "materialization_readback_verified"; assert [x[0] for x in c.calls] == ["readback", "write", "readback"]
    second = execute_materialization(req(), state(), c)
    assert second["outcome"] == "materialization_duplicate"; assert len(c.calls) == 4

def test_conflict_and_crash_hold():
    c = FakeConnector({"".join([]): {}})
    c.state[plan_materialization(req(), state())["idempotency_key"]] = {"effect_digest": "c" * 64, "content_digest": C}
    with pytest.raises(MaterializationHold) as e: execute_materialization(req(), state(), c)
    assert str(e.value) == "hold_materialization_remote_conflict"
    assert execute_materialization(req(), state(), FakeConnector(crash_after_write=True))["outcome"] == "materialization_recovery_readback_required"

def test_wrong_state_and_unknown_operation_hold():
    with pytest.raises(MaterializationHold): plan_materialization(req(operation="delete_issue"), state())
    with pytest.raises(MaterializationHold): plan_materialization(req(), {**state(), "remote_intent_state": "confirmed"})
