from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import github_evidence_cache as cache
import github_materialization_adapter as materialization
import github_project_projection as projection
import local_collaboration_scheduler as scheduler
from test_local_collaboration_scheduler import _setup

H = "a" * 64
C = "b" * 64


class Producer:
    def fetch_evidence(self, binding, selectors, capability_receipt):
        return {"trust_domain": "same_process_reference", "production_eligibility": False,
                "project_id": binding["project_id"], "repository_id": binding["repository_id"],
                "auth_scope_digest": binding["auth_scope_digest"], "producer_id": "fake", "producer_version": "1",
                "coverage": "complete", "entries": [{"evidence_kind": "issue_metadata", "opaque_object_ref": "item001",
                "selector_digest": "0" * 64, "representation_version": "1", "facts": {"state": "open"},
                "summary": "bounded", "anchors": ["issue:1"], "source_revision": "r1",
                "fetched_at": "2026-08-11T00:00:00Z", "coverage": "complete", "privacy_class": "metadata_only"}]}


def _materialization_request(pid, intent, state):
    effect = state["desired_effect_digest"]
    return {"schema_version": materialization.VERSION, "project_id": pid, "work_id": "w1", "intent_id": intent,
            "attempt_sequence": 1, "scheduler_generation": state["authority_generation"], "scheduler_head": state["authority_head"],
            "desired_effect_digest": effect, "approved_content_digest": C, "classification": "must_publish",
            "operation": "issue_comment", "repository_id": H, "repository_locator_digest": H, "auth_scope_digest": H,
            "expected_remote_kind": "issue", "expected_remote_ref": "item001", "expected_remote_version": "v1",
            "expected_remote_digest": H, "privacy_class": "metadata_only", "adapter_id": "fake", "adapter_version": "1",
            "timestamp_provenance": "explicit", "occurred_at": "2026-08-11T00:00:00Z",
            "gate": {"kind": "fixture_only", "production_eligibility": False, "project_id": pid, "intent_id": intent,
                     "attempt_sequence": 1, "operation": "issue_comment", "repository_id": H, "effect_digest": effect, "content_digest": C},
            "capability": {"trust_domain": "same_process_reference", "production_eligibility": False,
                           "network_capability": False, "adapter_id": "fake", "adapter_version": "1",
                           "supported_operations": ["issue_comment"]}}


def setup():
    root = tempfile.mkdtemp(prefix="project-projection-")
    pid = _setup(root)
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "initialize", "occurred_at": "2026-08-11T00:00:01Z"})
    intent = str(uuid.uuid4())
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "intent", "intent_id": intent,
        "intent_kind": "issue", "desired_effect": {"kind": "issue"}, "occurred_at": "2026-08-11T00:00:02Z"})
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "pending", "intent_id": intent,
        "expected_remote_kind": "issue", "expected_remote_ref": "item001", "expected_remote_digest": H,
        "expected_remote_version": "v1", "occurred_at": "2026-08-11T00:00:03Z"})
    state = scheduler.replay_scheduler_state(root, pid)
    cache.initialize_cache(projects_root=root, project_id=pid, repository_id=H, repository_locator_digest=H, auth_scope_digest=H,
                           producer_contract="fake", producer_version="1")
    cache.refresh_cache(projects_root=root, project_id=pid, repository_id=H, repository_locator_digest=H, auth_scope_digest=H,
                        selectors=["item001"], evaluated_at="2026-08-11T00:00:00Z", max_age_seconds=10, producer=Producer())
    materialized = materialization.execute_materialization(_materialization_request(pid, intent, state),
        {**state, "project_id": pid, "scheduler_generation": state["authority_generation"], "scheduler_head": state["authority_head"]}, materialization.FakeConnector())
    request = {"schema_version": projection.VERSION, "project_id": pid, "work_id": "w1", "intent_id": intent,
               "attempt_sequence": 1, "desired_effect_digest": state["desired_effect_digest"], "operation": "project_item_add",
               "repository_id": H, "repository_locator_digest": H, "auth_scope_digest": H,
               "evaluated_at": "2026-08-11T00:00:00Z", "max_age_seconds": 10, "opaque_item_basis": "item001",
               "expected_revision": "rev1", "expected_value_digest": C, "disposition": "required",
               "materialization_result": materialized}
    return root, pid, intent, request


def test_actual_public_dependencies_produce_one_fake_effect_and_duplicate():
    root, pid, _, request = setup()
    plan = projection.plan_project_projection(request, projects_root=root)
    connector = projection.FakeProjectConnector()
    first = projection.execute_project_projection(plan, connector, projects_root=root)
    assert first["outcome"] == "project_projection_fixture_readback_verified"
    assert connector.calls == ["pre_read", "write", "post_read"]
    again = projection.execute_project_projection(plan, connector, projects_root=root)
    assert again["outcome"] == "project_projection_duplicate" and connector.calls[-1] == "pre_read"
    assert first["flags"] == {"simulation_only": True, "production_eligibility": False, "network_capability": False,
                              "authoritative": False, "confirmation_eligible": False, "remote_mutation_performed": False}
    assert scheduler.replay_scheduler_state(root, pid)["remote_intent_state"] == "pending_materialization"


def test_public_terminal_plan_outcomes_are_closed():
    root, _, _, request = setup()
    expected = {"not_required": "project_projection_not_required", "approval_required": "project_projection_approval_required", "canceled": "project_projection_canceled"}
    for disposition, outcome in expected.items():
        assert projection.plan_project_projection({**request, "disposition": disposition}, projects_root=root)["outcome"] == outcome


def test_invalid_envelopes_fail_before_any_dependency_or_fake_call(monkeypatch):
    root, _, _, request = setup()
    calls = []
    monkeypatch.setattr(projection, "replay_scheduler_state", lambda *_args: calls.append("scheduler"))
    monkeypatch.setattr(projection.evidence_cache, "project_cache_readout", lambda **_kwargs: calls.append("cache"))
    variants = [
        {key: value for key, value in request.items() if key != "work_id"},
        {**request, "unknown": True},
        {**request, "attempt_sequence": "1"},
        {**request, "opaque_item_basis": "bad/raw"},
        {**request, "max_age_seconds": 86401},
    ]
    for bad in variants:
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(bad, projects_root=root)
    assert calls == []


def test_cache_and_materialization_binding_fail_closed_before_fake(monkeypatch):
    root, _, _, request = setup()
    for mutation in (
        lambda value: value.update({"repository_id": "b" * 64}),
        lambda value: value["materialization_result"].update({"intent_id": str(uuid.uuid4())}),
        lambda value: value["materialization_result"].update({"confirmation_eligible": True}),
    ):
        bad = copy.deepcopy(request); mutation(bad)
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(bad, projects_root=root)
    stale = projection.plan_project_projection(request, projects_root=root)
    badcache = {"schema_version": "GitHubEvidenceCache-v1", "operation": "project_cache_readout", "outcome": "cache_hit", "entries": [],
                "as_of": request["evaluated_at"], "age_seconds": 0, "coverage": "complete", "freshness": "fresh_as_of_fetch", "offline": False,
                "authoritative": False, "confirmation_eligible": False, "next_action": "none", "metadata": None, "counters": {}}
    monkeypatch.setattr(projection.evidence_cache, "project_cache_readout", lambda **_kwargs: badcache)
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(request, projects_root=root)
    assert stale["outcome"] == "project_projection_plan_ready"


def test_representative_cache_holds_and_actual_scheduler_negative_states(monkeypatch):
    root, pid, intent, request = setup()
    original_readout = cache.project_cache_readout
    positive = cache.project_cache_readout(projects_root=root, project_id=pid, repository_id=H,
        repository_locator_digest=H, auth_scope_digest=H, evaluated_at=request["evaluated_at"], max_age_seconds=10)
    variants = []
    for key, value in (("freshness", "stale"), ("coverage", "partial"), ("coverage", "unavailable"),
                       ("coverage", "privacy_held")):
        altered = copy.deepcopy(positive); altered[key] = value; variants.append(altered)
    zero = copy.deepcopy(positive); zero["entries"] = []; variants.append(zero)
    many = copy.deepcopy(positive); many["entries"] = many["entries"] * 2; variants.append(many)
    binding = copy.deepcopy(positive); binding["metadata"]["auth_scope_digest"] = "c" * 64; variants.append(binding)
    for value in variants:
        monkeypatch.setattr(projection.evidence_cache, "project_cache_readout", lambda **_kwargs: value)
        with pytest.raises(projection.ProjectProjectionHold):
            projection.plan_project_projection(request, projects_root=root)

    monkeypatch.setattr(projection.evidence_cache, "project_cache_readout", original_readout)
    foreign = copy.deepcopy(request); foreign["project_id"] = str(uuid.uuid4()); foreign["materialization_result"]["project_id"] = foreign["project_id"]
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(foreign, projects_root=root)
    cache_calls = []
    monkeypatch.setattr(projection.evidence_cache, "project_cache_readout", lambda **_kwargs: cache_calls.append("cache"))
    wrong_work = copy.deepcopy(request); wrong_work["work_id"] = "wrong-work"
    with pytest.raises(projection.ProjectProjectionHold) as held:
        projection.plan_project_projection(wrong_work, projects_root=root)
    assert held.value.classification == "hold_dependency" and cache_calls == []
    monkeypatch.setattr(projection.evidence_cache, "project_cache_readout", original_readout)
    wrong_attempt = copy.deepcopy(request); wrong_attempt["attempt_sequence"] = 2; wrong_attempt["materialization_result"]["attempt_sequence"] = 2
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(wrong_attempt, projects_root=root)
    forged = copy.deepcopy(request); forged["materialization_result"]["expected_remote_ref"] = "forged-item"
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(forged, projects_root=root)
    scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent,
        "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:04Z"})
    with pytest.raises(projection.ProjectProjectionHold):
        projection.plan_project_projection(request, projects_root=root)


def test_immediate_authority_drift_holds_before_fake_write():
    root, pid, intent, request = setup()
    plan = projection.plan_project_projection(request, projects_root=root)
    def commit():
        scheduler.apply_scheduler_request(root, pid, {"project_id": pid, "work_id": "w1", "operation": "observe", "intent_id": intent,
            "observed_remote_state": "open", "occurred_at": "2026-08-11T00:00:04Z"})
    connector = projection.FakeProjectConnector(on_pre_read=commit)
    result = projection.execute_project_projection(plan, connector, projects_root=root)
    assert result["outcome"] == "project_projection_stale_authority_hold" and connector.calls == ["pre_read"]


def test_execute_rechecks_top_level_work_binding_before_each_effect_boundary(monkeypatch):
    root, _, _, request = setup()
    plan = projection.plan_project_projection(request, projects_root=root)
    original = projection.replay_scheduler_state
    calls = []
    def replay(projects_root, project_id):
        state = original(projects_root, project_id)
        calls.append(state)
        if len(calls) == 2:
            state = {**state, "work_id": "wrong-work"}
        return state
    monkeypatch.setattr(projection, "replay_scheduler_state", replay)
    connector = projection.FakeProjectConnector()
    held = projection.execute_project_projection(plan, connector, projects_root=root)
    assert held["outcome"] == "project_projection_dependency_hold"
    assert connector.calls == ["pre_read"] and len(calls) == 2


def test_conflict_and_recovery_are_readback_only():
    root, _, _, request = setup(); plan = projection.plan_project_projection(request, projects_root=root)
    conflict = projection.FakeProjectConnector({plan["plan_digest"]: {"opaque_item_basis": "item001", "expected_revision": "wrong", "expected_value_digest": C, "plan_digest": plan["plan_digest"]}})
    assert projection.execute_project_projection(plan, conflict, projects_root=root)["outcome"] == "project_projection_conflict_hold"
    crashed = projection.FakeProjectConnector(crash_after_write=True)
    assert projection.execute_project_projection(plan, crashed, projects_root=root)["outcome"] == "project_projection_recovery_readback_required"
    calls = list(crashed.calls)
    recovered = projection.recover_project_projection(plan, crashed)
    assert recovered["outcome"] == "project_projection_fixture_readback_verified" and crashed.calls == calls + ["post_read"]


def test_schema_outcome_fixtures_and_no_real_io(monkeypatch):
    schema = yaml.safe_load(Path("schemas/github-project-projection.schema.yaml").read_text())
    validator = Draft202012Validator(schema)
    root, _, _, request = setup()
    fixtures = [projection.plan_project_projection({**request, "disposition": kind}, projects_root=root)
                for kind in ("not_required", "approval_required", "canceled")]
    plan = projection.plan_project_projection(request, projects_root=root)
    connector = projection.FakeProjectConnector()
    fixtures += [plan, projection.execute_project_projection(plan, connector, projects_root=root), projection.execute_project_projection(plan, connector, projects_root=root)]
    for fixture in fixtures:
        assert not list(validator.iter_errors(fixture))
        if "flags" in fixture:
            assert fixture["flags"]["authoritative"] is False and fixture["flags"]["confirmation_eligible"] is False
    monkeypatch.setattr(socket, "socket", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("subprocess")))
    assert projection.recover_project_projection(plan, connector)["outcome"] == "project_projection_fixture_readback_verified"


def test_outcome_specific_schema_runtime_parity_and_representative_rejections():
    root, _, _, request = setup()
    plan = projection.plan_project_projection(request, projects_root=root)
    terminal = {"project_id": plan["project_id"], "intent_id": plan["intent_id"], "attempt_sequence": plan["attempt_sequence"]}
    effect = {**terminal, "plan_digest": plan["plan_digest"]}
    fixtures = [
        projection._result(plan["operation"], "project_projection_not_required", **terminal),
        projection._result(plan["operation"], "project_projection_approval_required", **terminal),
        projection._result(plan["operation"], "project_projection_canceled", **terminal),
        projection._result(plan["operation"], "project_projection_duplicate", **effect),
        projection._result(plan["operation"], "project_projection_stale_authority_hold", classification="hold_stale_authority", **effect),
        projection._result(plan["operation"], "project_projection_dependency_hold", classification="hold_dependency", **effect),
        projection._result(plan["operation"], "project_projection_conflict_hold", classification="hold_conflict", **effect),
        projection._result(plan["operation"], "project_projection_privacy_hold", classification="hold_privacy", **effect),
        projection._result(plan["operation"], "project_projection_recovery_readback_required", **effect),
        projection._result(plan["operation"], "project_projection_fixture_readback_verified", fixture_readback_digest=C, **effect),
    ]
    for fixture in fixtures:
        projection._schema(fixture, "result")
    invalid = [
        {key: value for key, value in fixtures[-1].items() if key != "fixture_readback_digest"},
        {key: value for key, value in fixtures[4].items() if key != "classification"},
        {**fixtures[2], "plan_digest": H},
        {**fixtures[0], "unexpected": True},
        {**fixtures[3], "attempt_sequence": "1"},
    ]
    for envelope in invalid:
        with pytest.raises(projection.ProjectProjectionHold) as held:
            projection._schema(envelope, "result")
        assert held.value.classification == "hold_schema"


def test_fresh_process_recovery_only_reads_fake_state(tmp_path):
    root, _, _, request = setup(); plan = projection.plan_project_projection(request, projects_root=root)
    connector = projection.FakeProjectConnector(crash_after_write=True)
    assert projection.execute_project_projection(plan, connector, projects_root=root)["outcome"] == "project_projection_recovery_readback_required"
    encoded = json.dumps({"plan": plan, "state": connector.state})
    code = "import json,sys; import github_project_projection as p; x=json.loads(sys.argv[1]); c=p.FakeProjectConnector(x['state']); r=p.recover_project_projection(x['plan'],c); assert r['outcome']=='project_projection_fixture_readback_verified'; assert c.calls==['post_read']"
    env = {"PYTHONPATH": str(Path(__file__).parent)}
    completed = subprocess.run([sys.executable, "-c", code, encoded], env=env, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
