import hashlib
import tempfile
import uuid

import pytest
import github_materialization_adapter as ma
import github_project_projection as pp

PID=str(uuid.uuid4()); IID=str(uuid.uuid4()); H="a"*64; I="b"*64
def dig(value): return pp._digest(value)

def source():
    request={"schema_version":"GitHubMaterializationAdapter-v1","project_id":PID,"work_id":"work-1","intent_id":IID,"attempt_sequence":1,"scheduler_generation":4,"scheduler_head":H,"desired_effect_digest":H,"approved_content_digest":I,"classification":"must_publish","operation":"issue_comment","repository_id":H,"repository_locator_digest":H,"auth_scope_digest":H,"privacy_class":"metadata_only","adapter_id":"fake","adapter_version":"1","timestamp_provenance":"explicit","occurred_at":"2026-08-11T00:00:00Z","gate":{"kind":"fixture_only","production_eligibility":False,"project_id":PID,"intent_id":IID,"attempt_sequence":1,"operation":"issue_comment","repository_id":H,"effect_digest":H,"content_digest":I},"capability":{"trust_domain":"same_process_reference","production_eligibility":False,"network_capability":False,"adapter_id":"fake","adapter_version":"1","supported_operations":["issue_comment"]}}
    state={"project_id":PID,"remote_intent_state":"pending_materialization","intent_id":IID,"attempt_sequence":1,"desired_effect_digest":H,"scheduler_generation":4,"scheduler_head":H}
    return ma.execute_materialization(request,state,ma.FakeConnector())

def request(**extra):
    s=source(); data={"schema_version":"GitHubProjectProjection-v1","operation":"project_item_add","project_id":PID,"work_id":"work-1","intent_id":IID,"attempt_sequence":1,"scheduler_generation":4,"scheduler_head":H,"desired_effect_digest":H,"repository_id":H,"repository_locator_digest":H,"auth_scope_digest":H,"remote_project_digest":H,"source_materialization":s,"item_basis":{"item_digest":I,"materialization_receipt_digest":s["readback_digest"],"cache_selector_digest":H,"cache_object_ref_digest":dig("item-ref")},"policy_digest":H,"occurred_at":"2026-08-11T00:00:00Z","readback_nonce":"2026-08-11T00:00:01Z","expected_remote_kind":"project_item","expected_remote_ref":H,"expected_remote_version":H,"expected_remote_digest":H,"gate":{"kind":"fixture_only","production_eligibility":False,"project_id":PID,"intent_id":IID,"attempt_sequence":1,"operation":"project_item_add","repository_id":H,"remote_project_digest":H,"desired_effect_digest":H},"capability":{"trust_domain":"same_process_reference","production_eligibility":False,"network_capability":False,"supported_operations":["project_item_add"]}}
    data.update(extra); return data

def replay(): return {"remote_intent_state":"pending_materialization","work_id":"work-1","intent_id":IID,"attempt_sequence":1,"desired_effect_digest":H,"scheduler_generation":4,"scheduler_head":H}
def readout(): return {"schema_version":"GitHubEvidenceCache-v1","operation":"project_cache_readout","outcome":"cache_hit","freshness":"fresh_as_of_fetch","coverage":"complete","authoritative":False,"confirmation_eligible":False,"metadata":{"project_id":PID,"repository_id":H,"repository_locator_digest":H,"auth_scope_digest":H},"entries":[{"opaque_object_ref":"item-ref","selector_digest":H}],"as_of":"2026-08-11T00:00:00Z","age_seconds":0,"offline":False,"next_action":"observe_unverified","counters":{}}

@pytest.fixture
def boundary(monkeypatch):
    calls=[]
    monkeypatch.setattr(pp.scheduler,"replay_scheduler_state",lambda root,pid: calls.append(("scheduler",root,pid)) or replay())
    monkeypatch.setattr(pp.evidence_cache,"project_cache_readout",lambda **kw: calls.append(("cache",kw)) or readout())
    return calls

def test_actual_public_dependency_calls_plan_execute_duplicate(boundary):
    c=pp.FakeProjectConnector(); out=pp.execute_project_projection(projects_root="fixture",request=request(),materialization_result=source(),connector=c)
    assert out["outcome"]=="project_projection_readback_verified" and [x[0] for x in boundary]==["scheduler","cache"]
    assert pp.execute_project_projection(projects_root="fixture",request=request(),materialization_result=source(),connector=c)["outcome"]=="project_projection_duplicate"

def test_disabled_nonblocking_and_no_dependency_calls(monkeypatch):
    monkeypatch.setattr(pp.scheduler,"replay_scheduler_state",lambda *a: (_ for _ in ()).throw(AssertionError()))
    assert pp.plan_project_projection(projects_root="fixture",request=request(projection_mode="disabled"),materialization_result={})["outcome"]=="project_projection_not_required"

def test_cache_failures_are_nonconfirming_plan_holds(boundary,monkeypatch):
    for bad in (readout()|{"outcome":"cache_miss"},readout()|{"freshness":"stale"},readout()|{"coverage":"partial"},readout()|{"entries":[]},readout()|{"entries":[{"opaque_object_ref":"other","selector_digest":H}]},readout()|{"metadata":{}}):
        monkeypatch.setattr(pp.evidence_cache,"project_cache_readout",lambda **kw: bad)
        assert pp.plan_project_projection(projects_root="x",request=request(),materialization_result=source())["outcome"]=="project_projection_approval_required"

def test_prevalidation_and_dependency_negatives_zero_fake_calls(boundary):
    for bad in (request(project_id="bad"),request(unknown=True),request(item_basis={}),request(source_materialization={}),request(gate={}),request(cache_max_age_seconds=True)):
        c=pp.FakeProjectConnector()
        with pytest.raises(pp.ProjectProjectionHold): pp.execute_project_projection(projects_root="x",request=bad,materialization_result=source(),connector=c)
        assert c.calls==[]
    with pytest.raises(pp.ProjectProjectionHold): pp.plan_project_projection(projects_root="x",request=request(),materialization_result={**source(),"readback_digest":"c"*64})

def test_conflict_crash_and_readonly_recovery(boundary):
    crashed=pp.execute_project_projection(projects_root="x",request=request(),materialization_result=source(),connector=pp.FakeProjectConnector(crash_after_write=True))
    assert crashed["outcome"]=="project_projection_recovery_readback_required"
    c=pp.FakeProjectConnector(); assert pp.execute_project_projection(projects_root="x",request=request(readback_only=True),materialization_result=source(),connector=c)["outcome"]=="project_projection_recovery_readback_required" and [x[0] for x in c.calls]==["readback"]
