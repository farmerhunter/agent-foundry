from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path

import pytest

from local_collaboration_ledger import LocalCollaborationLedger
import local_collaboration_control_plane as control
import local_collaboration_scheduler as scheduler
import github_evidence_cache as cache
import github_project_projection as projection
import github_materialization_adapter as materialization

H = "a" * 64


class Producer:
    def __init__(self, entries=None, coverage="complete"):
        self.entries = [entry()] if entries is None else entries
        self.coverage = coverage
    def fetch_evidence(self, binding, selectors, capability):
        return {"trust_domain": "same_process_reference", "production_eligibility": False,
                "project_id": binding["project_id"], "repository_id": binding["repository_id"],
                "auth_scope_digest": binding["auth_scope_digest"], "producer_id": "fake",
                "producer_version": "1", "coverage": self.coverage, "entries": self.entries}


def entry():
    return {"evidence_kind": "issue_metadata", "opaque_object_ref": "opaque-issue", "selector_digest": "0" * 64,
            "representation_version": "1", "facts": {"state": "open"}, "summary": "bounded",
            "anchors": ["issue:1"], "source_revision": "r1", "fetched_at": "2026-08-11T00:00:00Z",
            "coverage": "complete", "privacy_class": "metadata_only"}


def control_request(pid):
    return {"project_id": pid, "occurred_at": "2026-08-11T00:00:00Z", "timestamp_provenance": "explicit",
            "work": {"project_id": pid, "work_id": "w1", "issue": 521, "objective": "projection", "stage": "implementation", "phase": "orch-03", "role": "Implementer", "root_budget_tokens": 100, "remaining_budget_tokens": 100, "issue_anchor": {"issue": 521, "scope": "projection", "risk": "low", "acceptance": "bounded", "durable_anchor": "issue:521", "human_gates": ["none"]}, "durable_anchors": ["issue:521"], "stop_conditions": ["scope drift"]},
            "execution_run": {"run_id": "r1", "work_id": "w1", "role": "Implementer", "state": "active", "context": {"source_timestamp": "2026-08-11T00:00:00Z", "threshold_band": "implementer_small_scoped_implementation", "resource_observations": {"context_tokens": {"provenance": "estimated", "tokens": 100, "source": "test"}}}, "model": {"name": "gpt-5.5", "reasoning": "low"}},
            "dispatch_claim": {"idempotency_key": "k1", "work_id": "w1", "role": "Implementer", "decision_boundary": "local", "transition_semantics": "bounded", "durable_anchor": "issue:521"}, "requested_route": "isolated_execution"}


def materialized(pid, intent, desired, state):
    request = {"schema_version": materialization.VERSION, "project_id": pid, "work_id": "w1", "intent_id": intent, "attempt_sequence": 1,
               "scheduler_generation": 4, "scheduler_head": H, "desired_effect_digest": desired,
               "approved_content_digest": H, "classification": "must_publish", "operation": "issue_comment", "repository_id": H,
               "repository_locator_digest": H, "auth_scope_digest": H, "expected_remote_kind": "issue", "expected_remote_ref": "opaque-issue",
               "expected_remote_version": "v1", "expected_remote_digest": H, "privacy_class": "metadata_only", "adapter_id": "fake", "adapter_version": "1",
               "timestamp_provenance": "explicit", "occurred_at": "2026-08-11T00:00:04Z",
               "gate": {"kind": "fixture_only", "production_eligibility": False, "project_id": pid, "intent_id": intent, "attempt_sequence": 1, "operation": "issue_comment", "repository_id": H, "effect_digest": desired, "content_digest": H},
               "capability": {"trust_domain": "same_process_reference", "production_eligibility": False, "network_capability": False, "adapter_id": "fake", "adapter_version": "1", "supported_operations": ["issue_comment"]}}
    result = materialization.execute_materialization(request, {**state, "scheduler_generation": 4, "scheduler_head": H}, materialization.FakeConnector())
    assert result["outcome"] == "materialization_readback_verified"
    return result, request


def setup():
    root = tempfile.mkdtemp(prefix="projection-")
    pid = str(uuid.uuid4())
    ledger = LocalCollaborationLedger.create_project(projects_root=root, project_id=pid)
    ledger.bind_project("github_repository", "repo-opaque")
    ledger.close()
    control.apply_control_request(root, pid, control_request(pid))
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
    intent = str(uuid.uuid4())
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent, "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
    state = scheduler.replay_scheduler_state(root, pid)
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent, "expected_remote_kind": "issue", "expected_remote_ref": "opaque-issue", "expected_remote_digest": H, "expected_remote_version": "v1", "occurred_at": "2026-08-11T00:00:03Z"})
    cache.initialize_cache(projects_root=root, project_id=pid, repository_id="repo-opaque", repository_locator_digest="repo-locator", auth_scope_digest=H, producer_contract="fake", producer_version="1")
    cache.refresh_cache(projects_root=root, project_id=pid, repository_id="repo-opaque", repository_locator_digest="repo-locator", auth_scope_digest=H, selectors=["1"], evaluated_at="2026-08-11T00:00:00Z", max_age_seconds=10, producer=Producer())
    readout = cache.project_cache_readout(projects_root=root, project_id=pid, repository_id="repo-opaque", repository_locator_digest="repo-locator", auth_scope_digest=H, evaluated_at="2026-08-11T00:00:00Z", max_age_seconds=10)
    state = scheduler.replay_scheduler_state(root, pid)
    result, material_request = materialized(pid, intent, state["desired_effect_digest"], state)
    request = {"schema_version": projection.VERSION, "project_id": pid, "work_id": "w1", "intent_id": intent, "attempt_sequence": 1, "effect_kind": "project_item_add", "desired_effect_digest": state["desired_effect_digest"], "repository_id": "repo-opaque", "repository_locator_digest": hashlib.sha256(json.dumps("repo-locator", separators=(",", ":")).encode()).hexdigest(), "auth_scope_digest": H, "cache_entry_key": readout["entries"][0]["entry_key"], "opaque_item_ref": "opaque-issue", "expected_remote_kind": "issue", "expected_remote_ref": "opaque-issue", "expected_remote_digest": H, "expected_remote_version": "v1", "materialization_request": material_request, "materialization_result": result, "evaluated_at": "2026-08-11T00:00:00Z", "max_age_seconds": 10, "fixture_capability": {"trust_domain": "same_process_reference", "simulation_only": True, "production_eligibility": False, "network_capability": False}}
    return root, pid, intent, request


def test_actual_dependencies_plan_execute_duplicate_and_recovery():
    root, _, _, request = setup()
    plan = projection.plan_project_projection(projects_root=root, request=request)
    assert plan["outcome"] == "project_projection_plan_ready"
    connector = projection.FakeProjectConnector()
    first = projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    assert first["outcome"] == "project_projection_readback_verified"
    assert connector.calls == ["read", "write", "read"]
    second = projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    assert second["outcome"] == "project_projection_duplicate" and connector.calls[-1] == "read"
    recovered = projection.recover_project_projection(plan=plan, connector=connector)
    assert recovered["outcome"] == "project_projection_readback_verified" and connector.calls[-1] == "read"


def test_authority_changed_between_plan_and_prewrite_is_zero_write():
    root, pid, _, request = setup()
    plan = projection.plan_project_projection(projects_root=root, request=request)
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "registered", "to_state": "queued", "transition_sequence": 1, "occurred_at": "2026-08-11T00:00:04Z"})
    connector = projection.FakeProjectConnector()
    result = projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    assert result["outcome"] == "hold_project_projection_stale_authority" and connector.calls == []


def test_prewrite_second_replay_stale_and_conflict_are_closed():
    root, pid, _, request = setup()
    plan = projection.plan_project_projection(projects_root=root, request=request)
    original = scheduler.replay_scheduler_state
    calls = 0
    def replay(r, p):
        nonlocal calls
        calls += 1
        state = original(r, p)
        if calls == 2:
            scheduler.replay_scheduler_state = original
            scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "transition", "from_state": "registered", "to_state": "queued", "transition_sequence": 1, "occurred_at": "2026-08-11T00:00:04Z"})
            return original(r, p)
        return state
    scheduler.replay_scheduler_state = replay
    try:
        connector = projection.FakeProjectConnector()
        result = projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    finally:
        scheduler.replay_scheduler_state = original
    assert result["outcome"] == "hold_project_projection_stale_authority" and connector.calls == ["read"]
    conflict = projection.FakeProjectConnector({request["desired_effect_digest"]: {"effect_kind": "project_item_add", "desired_effect_digest": request["desired_effect_digest"], "expected_remote_kind": "wrong"}})
    fresh_root, _, _, fresh_request = setup(); fresh = projection.plan_project_projection(projects_root=fresh_root, request=fresh_request)
    assert projection.execute_project_projection(projects_root=fresh_root, plan=fresh, connector=conflict)["outcome"] == "hold_project_projection_conflict"


def test_invalid_input_cache_and_materialization_hold_without_connector():
    root, _, _, request = setup()
    for bad in ({**request, "unknown": "x"}, {**request, "fixture_capability": {}}, {**request, "materialization_result": {}}):
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(projects_root=root, request=bad)
    stale = {**request, "evaluated_at": "2026-08-11T00:01:00Z", "max_age_seconds": 1}
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(projects_root=root, request=stale)


def test_forged_closed_plan_envelopes_hold_before_any_fake_call():
    root, _, _, request = setup()
    original = projection.plan_project_projection(projects_root=root, request=request)
    variants = []
    for key, value in (("network_capability", True), ("operation", "execute_project_projection"), ("confirmed", True), ("unknown", "x"), ("authority_head", None)):
        forged = deepcopy(original); forged[key] = value; variants.append(forged)
    cache_forged = deepcopy(original); cache_forged["plan"]["cache_basis"]["entry_digest"] = "f" * 64; variants.append(cache_forged)
    material_forged = deepcopy(original); material_forged["plan"]["materialization_result"]["expected_remote_ref"] = "wrong"; variants.append(material_forged)
    for forged in variants:
        connector = projection.FakeProjectConnector()
        with pytest.raises(projection.ProjectProjectionHold):
            projection.execute_project_projection(projects_root=root, plan=forged, connector=connector)
        assert connector.calls == []


def test_item_basis_mismatch_holds_before_projection_connector():
    root, _, _, request = setup()
    for key, value in (("opaque_item_ref", "wrong"), ("expected_remote_ref", "wrong")):
        bad = {**request, key: value}
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(projects_root=root, request=bad)


def test_invalid_timestamp_and_actual_404_state_negative_cases_hold_pre_connector(monkeypatch):
    root, pid, intent, request = setup()
    called = []
    original = scheduler.replay_scheduler_state
    monkeypatch.setattr(scheduler, "replay_scheduler_state", lambda *a, **k: called.append(a) or original(*a, **k))
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(projects_root=root, request={**request, "evaluated_at": "2026-99-99T99:99:99Z"})
    assert called == []
    monkeypatch.setattr(scheduler, "replay_scheduler_state", original)
    for bad in ({**request, "intent_id": str(uuid.uuid4())}, {**request, "attempt_sequence": 2}, {**request, "work_id": "foreign"}):
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(projects_root=root, request=bad)
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "conflict", "intent_id": intent, "occurred_at": "2026-08-11T00:00:04Z"})
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(projects_root=root, request=request)


def test_malformed_or_nonaccepted_403_result_stops_before_404_and_405(monkeypatch):
    root, _, _, request = setup()
    scheduler_calls, cache_calls = [], []
    monkeypatch.setattr(scheduler, "replay_scheduler_state", lambda *a, **k: scheduler_calls.append(a) or (_ for _ in ()).throw(AssertionError("scheduler must not run")))
    monkeypatch.setattr(cache, "project_cache_readout", lambda *a, **k: cache_calls.append(a) or (_ for _ in ()).throw(AssertionError("cache must not run")))
    result = request["materialization_result"]
    variants = [None, {}, {**result, "unknown": "x"}, {**result, "outcome": "materialization_plan_ready"}, {**result, "outcome": "materialization_recovery_readback_required"}, {**result, "expected_remote_ref": "wrong"}, {**result, "project_id": str(uuid.uuid4())}, {**result, "confirmed": False}, {key: value for key, value in result.items() if key != "confirmed"}, {key: value for key, value in result.items() if key != "readback_digest"}, {**result, "readback_digest": "f" * 64}, {**result, "opaque_receipt_ref": "fake:wrong"}, {**result, "adapter_version": "wrong"}, {**result, "occurred_at": "2026-08-11T00:00:05Z"}, {**result, "request_digest": "f" * 64}]
    for nested in variants:
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(projects_root=root, request={**request, "materialization_result": nested})
    assert scheduler_calls == [] and cache_calls == []


def test_closed_result_schema_rejects_operation_outcome_and_receipt_mismatches():
    root, _, _, request = setup(); plan = projection.plan_project_projection(projects_root=root, request=request)
    import yaml
    import jsonschema
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "github-project-projection.schema.yaml").read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    impossible = [
        {k: v for k, v in plan.items() if k != "plan"} | {"operation": "plan_project_projection", "outcome": "project_projection_duplicate"},
        {**plan, "operation": "recover_project_projection"},
        {**plan, "confirmed": None},
        {**plan, "readback_digest": "b" * 64},
        {**projection.execute_project_projection(projects_root=root, plan=plan, connector=projection.FakeProjectConnector()), "plan": plan["plan"]},
        {**projection.recover_project_projection(plan=plan, connector=projection.FakeProjectConnector()), "plan": plan["plan"]},
    ]
    for value in impossible:
        assert not validator.is_valid(value)


def test_outcome_field_matrix_accepts_only_runtime_emitted_fields():
    import yaml
    import jsonschema
    schema = yaml.safe_load((Path(__file__).parent.parent / "schemas" / "github-project-projection.schema.yaml").read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    root, _, _, request = setup(); plan = projection.plan_project_projection(projects_root=root, request=request)
    connector = projection.FakeProjectConnector()
    verified = projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    duplicate = projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    recovery_verified = projection.recover_project_projection(plan=plan, connector=connector)
    recovery_required = projection.recover_project_projection(plan=plan, connector=projection.FakeProjectConnector())
    recovery_conflict = projection.recover_project_projection(plan=plan, connector=projection.FakeProjectConnector({request["desired_effect_digest"]: {"wrong": True}}))
    stale_root, stale_pid, _, stale_request = setup(); stale_plan = projection.plan_project_projection(projects_root=stale_root, request=stale_request)
    scheduler.apply_scheduler_request(stale_root, stale_pid, {"project_id": stale_pid, "work_id": "w1", "operation": "transition", "from_state": "registered", "to_state": "queued", "transition_sequence": 1, "occurred_at": "2026-08-11T00:00:04Z"})
    execute_hold = projection.execute_project_projection(projects_root=stale_root, plan=stale_plan, connector=projection.FakeProjectConnector())
    values = [plan, duplicate, execute_hold, verified, recovery_required, recovery_conflict, recovery_verified]
    assert all(validator.is_valid(value) for value in values)
    all_fields = {key for value in values for key in value} - {"schema_version", "operation", "outcome", "simulation_only", "production_eligibility", "network_capability", "remote_mutation_performed", "authoritative", "confirmed"}
    prototypes = {key: next(value[key] for value in values if key in value) for key in all_fields}
    for value in values:
        for key in all_fields - set(value):
            forged = {**value, key: prototypes[key]}
            assert not validator.is_valid(forged), (value["operation"], value["outcome"], key)
            with pytest.raises(projection.ProjectProjectionHold):
                projection._validate_schema(forged)


def test_actual_cache_stale_miss_binding_and_multiple_basis_hold():
    root, pid, _, request = setup()
    for bad in ({**request, "evaluated_at": "2026-08-11T00:10:00Z", "max_age_seconds": 1}, {**request, "repository_id": "other-repository"}, {**request, "cache_entry_key": "f" * 64}):
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(projects_root=root, request=bad)
    # Two different cache rows claiming the same opaque item are ambiguous,
    # even though either row on its own is a valid cache entry.
    second = {**entry(), "selector_digest": "1" * 64, "source_revision": "r2", "summary": "bounded second"}
    cache.rebuild_cache(projects_root=root, project_id=pid, repository_id="repo-opaque", repository_locator_digest="repo-locator", auth_scope_digest=H, entries=[entry(), second], evaluated_at="2026-08-11T00:00:00Z", coverage="complete")
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(projects_root=root, request=request)


def test_fake_only_does_not_use_host_or_network(monkeypatch):
    root, _, _, request = setup()
    plan = projection.plan_project_projection(projects_root=root, request=request)
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(os, "system", lambda *a, **k: (_ for _ in ()).throw(AssertionError("host")))
    assert projection.execute_project_projection(projects_root=root, plan=plan, connector=projection.FakeProjectConnector())["outcome"] == "project_projection_readback_verified"


def test_schema_output_flags_and_recovery_empty_no_write():
    root, _, _, request = setup(); plan = projection.plan_project_projection(projects_root=root, request=request)
    connector = projection.FakeProjectConnector()
    result = projection.recover_project_projection(plan=plan, connector=connector)
    assert result["outcome"] == "project_projection_recovery_readback_required"
    assert result["remote_mutation_performed"] is False and connector.calls == ["read"]


def test_fresh_process_recovery_reads_caller_fixture_without_second_write():
    root, _, _, request = setup(); plan = projection.plan_project_projection(projects_root=root, request=request)
    connector = projection.FakeProjectConnector(); projection.execute_project_projection(projects_root=root, plan=plan, connector=connector)
    with tempfile.TemporaryDirectory() as fixture_root:
        plan_path = Path(fixture_root) / "plan.json"; state_path = Path(fixture_root) / "state.json"
        plan_path.write_text(json.dumps(plan)); state_path.write_text(json.dumps(connector.state))
        code = '''import json,sys; sys.path.insert(0,sys.argv[1]); import github_project_projection as p
plan=json.load(open(sys.argv[2])); state=json.load(open(sys.argv[3])); c=p.FakeProjectConnector(state); r=p.recover_project_projection(plan=plan,connector=c); print(json.dumps({"outcome":r["outcome"],"calls":c.calls}))'''
        run = subprocess.run([sys.executable, "-c", code, str(Path(__file__).parent), str(plan_path), str(state_path)], text=True, capture_output=True, check=True)
    assert json.loads(run.stdout) == {"outcome": "project_projection_readback_verified", "calls": ["read"]}


def test_verified_fixture_receipt_crosses_actual_404_readback_gate():
    root, pid, intent, request = setup()
    plan = projection.plan_project_projection(projects_root=root, request=request)
    receipt = projection.execute_project_projection(projects_root=root, plan=plan, connector=projection.FakeProjectConnector())
    class Adapter:
        def readback(self, readback_request):
            assert readback_request["request_digest"] == receipt["request_digest"]
            return receipt
    applied = scheduler.apply_remote_readback(root, pid, intent, Adapter(), {"project_id": pid, "work_id": "w1", "operation": "confirm", "intent_id": intent, "attempt_sequence": 1, "request_digest": receipt["request_digest"]})
    assert applied["decision"] == "confirmed"
