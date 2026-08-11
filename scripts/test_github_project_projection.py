import copy
import socket
import uuid

import pytest

from github_project_projection import (FakeProjectConnector, ProjectProjectionHold,
    execute_project_projection, plan_project_projection)

PID=str(uuid.uuid4()); IID=str(uuid.uuid4()); H="a"*64; I="b"*64

def materialization():
    return {"schema_version":"GitHubMaterializationAdapter-v1","operation":"issue_comment","outcome":"materialization_readback_verified","project_id":PID,"intent_id":IID,"attempt_sequence":1,"desired_effect_digest":H,"authoritative":False,"confirmation_eligible":False,"simulation_only":True,"remote_mutation_performed":False,"readback_digest":I}

def scheduler():
    return {"remote_intent_state":"pending_materialization","work_id":"work-1","intent_id":IID,"attempt_sequence":1,"desired_effect_digest":H,"scheduler_generation":4,"scheduler_head":H}

def request(**extra):
    data={"schema_version":"GitHubProjectProjection-v1","operation":"project_item_add","project_id":PID,"work_id":"work-1","intent_id":IID,"attempt_sequence":1,"scheduler_generation":4,"scheduler_head":H,"desired_effect_digest":H,"repository_id":H,"repository_locator_digest":H,"auth_scope_digest":H,"remote_project_digest":H,"source_materialization":materialization(),"item_basis":{"item_digest":I,"materialization_receipt_digest":I,"cache_selector_digest":H},"policy_digest":H,"occurred_at":"2026-08-11T00:00:00Z","readback_nonce":"2026-08-11T00:00:01Z","gate":{"kind":"fixture_only","production_eligibility":False,"project_id":PID,"intent_id":IID,"attempt_sequence":1,"operation":"project_item_add","repository_id":H,"remote_project_digest":H,"desired_effect_digest":H},"capability":{"trust_domain":"same_process_reference","production_eligibility":False,"network_capability":False,"supported_operations":["project_item_add"]}}
    data.update(extra); return data

def cache(**extra):
    data={"schema_version":"GitHubEvidenceCache-v1","operation":"project_cache_readout","outcome":"cache_hit","freshness":"fresh_as_of_fetch","coverage":"complete","authoritative":False,"confirmation_eligible":False,"metadata":{"project_id":PID,"repository_id":H,"repository_locator_digest":H,"auth_scope_digest":H},"entries":[{"opaque_object_ref":I,"selector_digest":H}]}
    data.update(extra); return data

def test_plan_execute_duplicate_conflict_and_recovery():
    c=FakeProjectConnector()
    first=execute_project_projection(request(),scheduler(),materialization(),cache(),c)
    assert first["outcome"]=="project_projection_readback_verified" and first["remote_mutation_performed"] is True
    duplicate=execute_project_projection(request(),scheduler(),materialization(),cache(),c)
    assert duplicate["outcome"]=="project_projection_duplicate" and [x[0] for x in c.calls]==["readback","write","readback","readback"]
    c.state[next(iter(c.state))]["item_digest"]="c"*64
    assert execute_project_projection(request(),scheduler(),materialization(),cache(),c)["outcome"]=="hold_project_projection_conflict"
    crash=execute_project_projection(request(),scheduler(),materialization(),cache(),FakeProjectConnector(crash_after_write=True))
    assert crash["outcome"]=="project_projection_recovery_readback_required"

def test_field_request_and_readback_only_do_not_write():
    r=request(operation="project_field_set",field_digest=H,option_or_value_digest=I,gate={**request()["gate"],"operation":"project_field_set"},capability={**request()["capability"],"supported_operations":["project_field_set"]},readback_only=True)
    c=FakeProjectConnector(); out=execute_project_projection(r,scheduler(),materialization(),cache(),c)
    assert out["outcome"]=="project_projection_recovery_readback_required" and c.calls==[("readback", next(iter([x[1] for x in c.calls])))]

def test_disabled_is_nonblocking_and_zero_calls():
    c=FakeProjectConnector()
    assert execute_project_projection(request(projection_mode="disabled"),{}, {}, None,c)["outcome"]=="project_projection_not_required"
    assert c.calls==[]

def test_invalid_corpus_has_no_connector_calls():
    bads=[request(project_id="not-a-uuid"),request(unknown=True),request(occurred_at="2026-08-11T00:00:00+08:00"),request(repository_id=True),request(source_materialization={}),request(item_basis={"item_digest":I}),request(gate=None),request(capability={}),request(readback_only=False)]
    for bad in bads:
        c=FakeProjectConnector()
        with pytest.raises(ProjectProjectionHold): execute_project_projection(bad,scheduler(),materialization(),cache(),c)
        assert c.calls==[]

def test_dependency_failures_and_cache_hold_do_not_call_connector():
    with pytest.raises(ProjectProjectionHold): plan_project_projection(request(),{"remote_intent_state":"confirmed"},materialization(),cache())
    with pytest.raises(ProjectProjectionHold): plan_project_projection(request(),scheduler(),{**materialization(),"project_id":str(uuid.uuid4())},cache())
    for read in (cache(outcome="cache_miss"),cache(entries=[]),cache(metadata={"project_id":PID,"repository_id":H,"repository_locator_digest":H,"auth_scope_digest":"c"*64})):
        assert plan_project_projection(request(),scheduler(),materialization(),read)["outcome"]=="project_projection_approval_required"

def test_no_network_capability_or_import_use():
    original=socket.socket
    def fail(*args,**kwargs): raise AssertionError("network must not be used")
    socket.socket=fail
    try: assert execute_project_projection(request(),scheduler(),materialization(),cache(),FakeProjectConnector())["outcome"]=="project_projection_readback_verified"
    finally: socket.socket=original
