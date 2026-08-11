import hashlib
import uuid
import pytest
import json
import socket
import tempfile
from pathlib import Path
import local_collaboration_scheduler as sc

from github_materialization_adapter import FakeConnector, MaterializationHold, execute_materialization, plan_materialization

PID = str(uuid.uuid4()); INTENT = str(uuid.uuid4()); H = "a" * 64; C = "b" * 64

def req(**extra):
    base = {"schema_version": "GitHubMaterializationAdapter-v1", "project_id": PID, "work_id": "work-1", "intent_id": INTENT, "attempt_sequence": 1,
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
            "attempt_sequence": 1, "desired_effect_digest": H, "scheduler_generation": 4, "scheduler_head": H}

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

def test_stale_scheduler_binding_and_closed_capability_hold():
    with pytest.raises(MaterializationHold) as e: plan_materialization(req(), {**state(), "scheduler_generation": 3})
    assert str(e.value) == "hold_materialization_stale_basis"
    bad = req(capability={**req()["capability"], "junk": True})
    with pytest.raises(MaterializationHold) as e: execute_materialization(bad, state(), FakeConnector())
    assert str(e.value) == "hold_materialization_connector_untrusted"

def test_bounded_approved_body_and_wrong_remote_identity():
    content = {"body": "synthetic comment", "summary": "short"}
    digest = hashlib.sha256(__import__("json").dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    r = req(approved_remote_content=content, approved_content_digest=digest)
    r["gate"] = {**r["gate"], "content_digest": digest}
    assert execute_materialization(r, state(), FakeConnector())["outcome"] == "materialization_readback_verified"
    c = FakeConnector(); first = execute_materialization(req(), state(), c); assert first["outcome"] == "materialization_readback_verified"
    c.state[first["idempotency_key"]]["remote_ref"] = "out-of-band"
    with pytest.raises(MaterializationHold) as e: execute_materialization(req(), state(), c)
    assert str(e.value) == "hold_materialization_remote_conflict"

def test_privacy_and_crash_do_not_confirm():
    with pytest.raises(MaterializationHold) as e: plan_materialization(req(approved_remote_content={"body": "prompt transcript"}), state())
    assert str(e.value) == "hold_materialization_privacy"
    result = execute_materialization(req(), state(), FakeConnector(crash_after_write=True))
    assert result["outcome"] == "materialization_recovery_readback_required" and result["remote_mutation_performed"] is False

def test_recovery_readback_only_and_closed_content_limits():
    connector = FakeConnector()
    first = execute_materialization(req(), state(), connector)
    calls = len(connector.calls)
    recovered = execute_materialization({**req(), "readback_only": True}, state(), connector)
    assert recovered["outcome"] == "materialization_duplicate" and len(connector.calls) == calls + 1
    with pytest.raises(MaterializationHold): plan_materialization(req(approved_remote_content={"title": "x" * 257}), state())

def test_readback_result_has_404_boundary_fields():
    result = execute_materialization(req(), state(), FakeConnector())
    for key in ("confirmed", "adapter_id", "adapter_version", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "request_digest", "desired_effect_digest", "occurred_at", "read_timestamp", "readback_nonce"):
        assert key in result
    assert result["confirmed"] is True and result["simulation_only"] is True

def test_real_404_injected_readback_boundary():
    """Use the accepted scheduler boundary in a disposable SQLite fixture."""
    from test_local_collaboration_scheduler import _setup
    class Adapter:
        def __init__(self, response): self.response = response
        def readback(self, request): return self.response
    with tempfile.TemporaryDirectory() as root:
        pid = _setup(root)
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
        intent = str(uuid.uuid4())
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
        sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "expected_remote_kind": "issue", "expected_remote_ref": "opaque-1", "expected_remote_digest": H, "expected_remote_version": "v1", "occurred_at": "2026-08-11T00:00:03Z"})
        current = sc.replay_scheduler_state(root, pid)
        request = req(project_id=pid, intent_id=intent, desired_effect_digest=current["desired_effect_digest"], approved_content_digest=C, expected_remote_kind="issue", expected_remote_ref="opaque-1", expected_remote_digest=H, expected_remote_version="v1", scheduler_generation=4, scheduler_head=H)
        request["gate"] = {**request["gate"], "project_id": pid, "intent_id": intent, "effect_digest": request["desired_effect_digest"]}
        request["gate"]["content_digest"] = C
        response = execute_materialization(request, {**current, "project_id": pid, "remote_intent_state": "pending_materialization", "intent_id": intent, "attempt_sequence": 1, "scheduler_generation": current.get("control_generation") or 4, "scheduler_head": current.get("control_head") or H}, FakeConnector())
        response["request_digest"] = response["request_digest"]
        result = sc.apply_remote_readback(root, pid, intent, Adapter(response), {"project_id": pid, "intent_id": intent, "operation": "confirm", "attempt_sequence": 1, "request_digest": response["request_digest"]})
        assert result["decision"] == "confirmed"

def test_integration_boundaries_and_cache_observations_are_non_confirming():
    # These are the accepted #522/#404/#405 replay shapes: the adapter sees a
    # read-only pending outbox and advisory cache, never a caller confirmation.
    scheduler = {**state(), "control_generation": 4, "control_head": H}
    fresh = {"outcome": "cache_hit", "freshness": "fresh_as_of_fetch", "coverage": "complete", "authoritative": False, "confirmation_eligible": False}
    assert execute_materialization(req(), scheduler, FakeConnector(), fresh)["outcome"] == "materialization_readback_verified"
    for observation in ({"outcome": "cache_hit", "freshness": "stale", "coverage": "complete", "authoritative": False, "confirmation_eligible": False}, {"outcome": "cache_hit", "freshness": "fresh_as_of_fetch", "coverage": "partial", "authoritative": False, "confirmation_eligible": False}, {"outcome": "cache_miss", "freshness": "unavailable", "coverage": "unavailable", "authoritative": False, "confirmation_eligible": False}):
        result = plan_materialization(req(), state(), observation)
        assert result["outcome"] == "materialization_approval_required" and result["simulation_only"]
    with pytest.raises(MaterializationHold): plan_materialization(req(project_id=str(uuid.uuid4())), state())

def test_zero_side_effect_invalid_bindings_and_crash_before_write():
    connector = FakeConnector(fail_pre_read=True)
    with pytest.raises(MaterializationHold) as e: execute_materialization(req(), state(), connector)
    assert str(e.value) == "hold_materialization_readback_unavailable" and connector.calls == [("readback", connector.calls[0][1])]
    for key, value, current in (("repository_id", "c" * 64, state()), ("expected_remote_version", "wrong", {**state(), "expected_remote_version": "v1"}), ("adapter_version", "2", state()), ("nonce", "2026-08-11T00:00:01Z", {**state(), "readback_nonce": "2026-08-11T00:00:00Z"})):
        with pytest.raises(MaterializationHold): execute_materialization(req(**{key: value}), current, FakeConnector())

def test_schema_and_nested_privacy_contract():
    try:
        import yaml
        schema = yaml.safe_load(open("schemas/github-materialization-adapter.schema.yaml"))
    except ImportError:
        pytest.skip("yaml validator unavailable")
    assert "request" in schema["$defs"] and "gate" in schema["$defs"] and "capability" in schema["$defs"] and "result" in schema["$defs"]
    with pytest.raises(MaterializationHold): plan_materialization(req(approved_remote_content={"body": "tool_output"}), state())

def test_schema_runtime_variants():
    try:
        import jsonschema
        import yaml
        schema = yaml.safe_load(open("schemas/github-materialization-adapter.schema.yaml"))
    except ImportError:
        pytest.skip("schema validator unavailable")
    local = req(classification="local_only"); local.pop("gate"); local.pop("capability")
    optional = req(classification="optional_sync"); optional.pop("gate"); optional.pop("capability")
    jsonschema.validate(local, schema); jsonschema.validate(optional, schema); jsonschema.validate(req(), schema)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({**optional, "gate": req()["gate"]}, schema)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({**optional, "capability": req()["capability"]}, schema)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({**optional, "capability": {"junk": True}}, schema)
    with pytest.raises(MaterializationHold): plan_materialization({**optional, "capability": req()["capability"]}, state())

def test_no_host_io_and_external_holds_fixture_stability(monkeypatch):
    def blocked(*args, **kwargs): raise AssertionError("host I/O invoked")
    monkeypatch.setattr(socket, "socket", blocked)
    assert execute_materialization(req(), state(), FakeConnector())["simulation_only"] is True
    external_holds = {
        "#546": "external_selected_vault_duplicate_hold_preexisting",
        "#547": "external_selected_vault_claude_fixture_drift_preexisting",
    }
    assert external_holds == {"#546": "external_selected_vault_duplicate_hold_preexisting", "#547": "external_selected_vault_claude_fixture_drift_preexisting"}
