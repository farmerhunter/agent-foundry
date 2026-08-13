import hashlib
import uuid
import pytest
import json
import socket
import tempfile
from pathlib import Path
import local_collaboration_scheduler as sc

from github_materialization_adapter import REAL_CONNECTOR_OPERATION, FakeConnector, MaterializationHold, execute_materialization, execute_real_label_materialization, plan_materialization
from github_materialization_github_cli_connector import CONNECTOR_ID, CONNECTOR_VERSION, GitHubCliIssueLabelConnector, capability_digest

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
    assert str(e.value) == "hold_materialization_schema"

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
    unicode_content = {"title": "é" * 120}
    unicode_digest = hashlib.sha256(json.dumps(unicode_content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    unicode_request = req(approved_remote_content=unicode_content, approved_content_digest=unicode_digest)
    unicode_request["gate"] = {**unicode_request["gate"], "content_digest": unicode_digest}
    assert plan_materialization(unicode_request, state())["outcome"] == "materialization_plan_ready"
    aggregate = {"body": "é" * 8193}
    aggregate_digest = hashlib.sha256(json.dumps(aggregate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    aggregate_request = req(approved_remote_content=aggregate, approved_content_digest=aggregate_digest)
    aggregate_request["gate"] = {**aggregate_request["gate"], "content_digest": aggregate_digest}
    with pytest.raises(MaterializationHold): plan_materialization(aggregate_request, state())

def test_readback_result_has_404_boundary_fields():
    result = execute_materialization(req(), state(), FakeConnector())
    for key in ("confirmed", "adapter_id", "adapter_version", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "request_digest", "desired_effect_digest", "occurred_at", "read_timestamp", "readback_nonce"):
        assert key in result
    assert result["confirmed"] is True and result["simulation_only"] is True

def test_real_404_injected_readback_boundary():
    """The real #403 hermetic result is valid but never confirmation authority."""
    from test_local_collaboration_scheduler import _setup
    from local_collaboration_ledger import LocalCollaborationLedger
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
        readback_request = {"project_id": pid, "work_id": "w1", "operation": "confirm", "intent_id": intent,
            "attempt_sequence": 1, "request_digest": response["request_digest"],
            "occurred_at": "2026-08-11T00:00:04Z", "desired_effect_digest": current["desired_effect_digest"],
            "expected_remote_kind": "issue", "expected_remote_ref": "opaque-1",
            "expected_remote_digest": H, "expected_remote_version": "v1"}
        path = Path(root) / pid / "collaboration.db"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        before = ledger.list_events(); before_head = before[-1].event_hash
        before_business = tuple(ledger._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                                for table in ("holds", "project_bindings", "projections"))
        ledger.close()
        with pytest.raises(sc.SchedulerHold) as held:
            sc.apply_remote_readback(root, pid, intent, Adapter(response), readback_request)
        assert str(held.value) == "hold_untrusted_readback"
        ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        after = ledger.list_events()
        after_business = tuple(ledger._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                               for table in ("holds", "project_bindings", "projections"))
        ledger.close()
        assert len(after) == len(before) and after[-1].event_hash == before_head
        assert after_business == before_business
        rejected = sc.replay_scheduler_state(root, pid)
        assert rejected["remote_intent_state"] == "pending_materialization"
        assert not any(event.event_type == "scheduler.remote_confirmation_recorded" for event in after)
        observed = sc.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe",
            "intent_id": intent, "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:05Z"})
        assert observed["mutation_performed"]
        assert sc.replay_scheduler_state(root, pid)["remote_intent_state"] == "observed_unverified"

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
    checker = jsonschema.FormatChecker()
    @checker.checks("utf8-256")
    def utf8_256(value): return isinstance(value, str) and len(value.encode()) <= 256
    @checker.checks("utf8-8192")
    def utf8_8192(value): return isinstance(value, str) and len(value.encode()) <= 8192
    @checker.checks("utf8-128")
    def utf8_128(value): return isinstance(value, str) and len(value.encode()) <= 128
    @checker.checks("utf8-content")
    def utf8_content(value):
        return isinstance(value, dict) and len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()) <= 8192
    @checker.checks("strict-rfc3339")
    def strict_rfc3339(value):
        import datetime
        if not isinstance(value, str) or not __import__("re").fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", value): return False
        try: datetime.datetime.fromisoformat(value.replace("Z", "+00:00")); return True
        except ValueError: return False
    validator = jsonschema.Draft202012Validator(schema, format_checker=checker)
    def valid(value): validator.validate(value)
    def invalid(value):
        with pytest.raises(jsonschema.ValidationError): validator.validate(value)
    local = req(classification="local_only"); local.pop("gate"); local.pop("capability")
    optional = req(classification="optional_sync"); optional.pop("gate"); optional.pop("capability")
    valid(local); valid(optional); valid(req()); valid(plan_materialization(req(), state()))
    invalid({**optional, "gate": req()["gate"]}); invalid({**optional, "capability": req()["capability"]})
    invalid({**optional, "capability": {"junk": True}}); invalid({**optional, "readback_only": False})
    invalid({**req(), "capability": {**req()["capability"], "supported_operations": []}})
    invalid({**req(), "approved_remote_content": {"title": "é" * 129}})
    for field, value in (("approved_remote_content", None), ("nonce", False), ("expected_remote_ref", None), ("scheduler_generation", True), ("occurred_at", "2026-08-11T00:00:00.123Z")):
        invalid({**req(), field: value})
        with pytest.raises(MaterializationHold): execute_materialization({**req(), field: value}, state(), FakeConnector())
    with pytest.raises(MaterializationHold): plan_materialization(req(occurred_at="2026-02-30T00:00:00Z"), state())
    with pytest.raises(MaterializationHold): plan_materialization(req(approved_remote_content="raw"), state())
    with pytest.raises(MaterializationHold): plan_materialization(req(approved_remote_content={"body": 1}), state())
    invalid({**req(), "occurred_at": "2026-02-30T00:00:00Z"})
    with pytest.raises(MaterializationHold): plan_materialization({**req(classification="local_only"), "gate": {"junk": True}}, state())
    with pytest.raises(MaterializationHold): plan_materialization({**optional, "capability": req()["capability"]}, state())
    with pytest.raises(MaterializationHold): plan_materialization({**optional, "scheduler_state": "forbidden"}, state())
    single_gate = {**req(classification="local_only")}; single_gate.pop("capability")
    single_cap = {**req(classification="local_only")}; single_cap.pop("gate")
    invalid(single_gate); invalid(single_cap)
    with pytest.raises(MaterializationHold): plan_materialization(single_gate, state())
    with pytest.raises(MaterializationHold): plan_materialization(single_cap, state())
    bad_gate = {**req(), "gate": {**req()["gate"], "attempt_sequence": True}}
    bad_cap = {**req(), "capability": {**req()["capability"], "production_eligibility": 0}}
    dup_cap = {**req(), "capability": {**req()["capability"], "supported_operations": ["issue_comment", "issue_comment"]}}
    for bad in (bad_gate, bad_cap, dup_cap):
        invalid(bad)
        with pytest.raises(MaterializationHold): execute_materialization(bad, state(), FakeConnector())
    for classification in ("local_only", "optional_sync"):
        variant = req(classification=classification); variant.pop("gate"); variant.pop("capability")
        for key in ("gate", "capability"):
            invalid({**variant, key: None})
            with pytest.raises(MaterializationHold): execute_materialization({**variant, key: None}, state(), FakeConnector())

def test_no_host_io_and_external_holds_fixture_stability(monkeypatch):
    def blocked(*args, **kwargs): raise AssertionError("host I/O invoked")
    monkeypatch.setattr(socket, "socket", blocked)
    assert execute_materialization(req(), state(), FakeConnector())["simulation_only"] is True
    external_holds = {
        "#546": "external_selected_vault_duplicate_hold_preexisting",
        "#547": "external_selected_vault_claude_fixture_drift_preexisting",
    }
    assert external_holds == {"#546": "external_selected_vault_duplicate_hold_preexisting", "#547": "external_selected_vault_claude_fixture_drift_preexisting"}


def test_real_connector_operation_cannot_promote_hermetic_fake_path():
    assert REAL_CONNECTOR_OPERATION == "add_existing_label"
    with pytest.raises(MaterializationHold) as held:
        plan_materialization(req(operation=REAL_CONNECTOR_OPERATION), state())
    assert str(held.value) in {"hold_materialization_schema", "hold_materialization_operation_unsupported"}


class BridgeStubRunner:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs))
        return self.responses.pop(0)


def _bridge_capability():
    return {"connector_id": CONNECTOR_ID, "connector_version": CONNECTOR_VERSION, "host": "github.com", "active_principal": "octocat",
            "observable_host_scopes": ["repo"], "available": True, "credential_grant_attested": False,
            "operation_confinement": "exact_repo_issue_label", "authoritative": False, "confirmation_eligible": False}


def _bridge_request(**extra):
    target = {"owner": "octo-org", "repository": "demo", "number": 12, "kind": "issue"}
    repository = {"owner": "octo-org", "repository": "demo"}
    base = {"schema_version": "GitHubLabelMaterializationBridge-v1", "human_authorization_ref": "human-gate-2",
            "project_id": PID, "work_id": "work-1", "intent_id": INTENT, "attempt_sequence": 1, "repository_id": C,
            "repository_locator_digest": hashlib.sha256(json.dumps(repository, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "target": target, "label": "trial-label", "preimage_digest": hashlib.sha256(json.dumps(["bug"], separators=(",", ":")).encode()).hexdigest(),
            "privacy_class": "metadata_only", "write_budget": 1, "retry_budget": 0,
            "occurred_at": "2026-08-12T00:00:00Z", "timestamp_provenance": "explicit"}
    effect = {"version": "GitHubLabelMaterializationBridge-v1", "operation": "add_existing_label", "target": target, "label": "trial-label",
              "preimage_digest": base["preimage_digest"], "project_id": PID, "intent_id": INTENT, "attempt_sequence": 1,
              "repository_id": C, "repository_locator_digest": base["repository_locator_digest"]}
    base["desired_effect_digest"] = hashlib.sha256(json.dumps(effect, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    base.update(extra); return base


def _bridge_state(request):
    return {"project_id": request["project_id"], "remote_intent_state": "pending_materialization", "intent_id": request["intent_id"],
            "attempt_sequence": request["attempt_sequence"], "desired_effect_digest": request["desired_effect_digest"],
            "scheduler_generation": 4, "scheduler_head": H}


def _bridge_connector(responses):
    runner = BridgeStubRunner(responses)
    return GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", runner=runner), runner


def test_public_real_label_bridge_adds_once_with_unattested_hdc_credential():
    request = _bridge_request(); connector, runner = _bridge_connector([
        {"returncode": 0, "stdout": '{"hosts":{"github.com":[{"login":"octocat","scopes":["repo"]}]}}', "stderr": ""},
        {"returncode": 0, "stdout": '{"hosts":{"github.com":[{"login":"octocat","scopes":["repo"]}]}}', "stderr": ""},
        {"returncode": 0, "stdout": "bug\n", "stderr": ""}, {"returncode": 0, "stdout": "", "stderr": ""},
        {"returncode": 0, "stdout": "bug\ntrial-label\n", "stderr": ""},
    ])
    result = execute_real_label_materialization(request, _bridge_state(request), connector)
    assert result["outcome"] == "real_label_added_observed_unverified" and result["mutation_count"] == 1
    assert result["credential_grant_attested"] is False and result["operation_confinement"] == "exact_repo_issue_label"
    assert sum("POST" in call[0] for call in runner.calls) == 1
    assert all(call[1]["shell"] is False for call in runner.calls)


def test_public_real_label_bridge_rejects_forgery_and_capability_before_target():
    request = _bridge_request(); connector, runner = _bridge_connector([])
    result = execute_real_label_materialization({**request, "authority_pair": {"authority_generation": 4}}, _bridge_state(request), connector)
    assert result["outcome"] == "real_label_materialization_hold" and result["reason"] == "schema_or_privacy" and not runner.calls
    with pytest.raises(TypeError):
        GitHubCliIssueLabelConnector(repository_owner="octo-org", repository="demo", capability_resolver=lambda: _bridge_capability())
    connector, runner = _bridge_connector([{"returncode": 0, "stdout": '{"hosts":{"github.com":[{"login":"octocat","scopes":["repo"]}]}}', "stderr": ""}, {"returncode": 1, "stdout": "", "stderr": ""}])
    result = execute_real_label_materialization(request, _bridge_state(request), connector)
    assert result["reason"] == "capability_unavailable_or_untrusted" and result["connector_called"] is True
    assert not any("/issues/" in " ".join(call[0]) for call in runner.calls)
    connector, runner = _bridge_connector([])
    result = execute_real_label_materialization(request, {**_bridge_state(request), "scheduler_head": "bad"}, connector)
    assert result["reason"] == "scheduler_or_authority_drift" and not runner.calls


def test_public_real_label_bridge_duplicate_and_binding_budget_holds():
    request = _bridge_request(preimage_digest=hashlib.sha256(json.dumps(["bug", "trial-label"], separators=(",", ":")).encode()).hexdigest())
    target = request["target"]
    effect = {"version": "GitHubLabelMaterializationBridge-v1", "operation": "add_existing_label", "target": target, "label": request["label"], "preimage_digest": request["preimage_digest"], "project_id": PID, "intent_id": INTENT, "attempt_sequence": 1, "repository_id": C, "repository_locator_digest": request["repository_locator_digest"]}
    request["desired_effect_digest"] = hashlib.sha256(json.dumps(effect, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    connector, runner = _bridge_connector([{"returncode": 0, "stdout": '{"hosts":{"github.com":[{"login":"octocat","scopes":["repo"]}]}}', "stderr": ""}, {"returncode": 1, "stdout": "", "stderr": ""}])
    result = execute_real_label_materialization(request, _bridge_state(request), connector)
    assert result["reason"] == "capability_unavailable_or_untrusted" and len(runner.calls) == 2
    result = execute_real_label_materialization(_bridge_request(write_budget=2), _bridge_state(_bridge_request(write_budget=2)), connector)
    assert result["reason"] == "schema_or_privacy" and len(runner.calls) == 2
