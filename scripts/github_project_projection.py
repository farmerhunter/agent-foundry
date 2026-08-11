"""Hermetic optional GitHub Project projection.

This module is deliberately an in-memory fake boundary.  It plans or simulates
one Project effect; it never discovers a Project, opens a network connection,
persists projection state, or writes the ORCH ledger.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
import github_evidence_cache as evidence_cache
import github_materialization_adapter as materialization
import local_collaboration_scheduler as scheduler

VERSION = "GitHubProjectProjection-v1"
NAMESPACE = uuid.UUID("b5d55298-a05e-4f12-b89b-42a3c035ac4f")
OPERATIONS = {"project_item_add", "project_field_set"}
OUTCOMES = {"project_projection_not_required", "project_projection_plan_ready", "project_projection_approval_required", "project_projection_duplicate", "project_projection_readback_verified", "project_projection_recovery_readback_required", "project_projection_canceled", "hold_project_projection_conflict", "hold_project_projection_readback_unavailable"}
HOLDS = {"hold_project_projection_schema", "hold_project_projection_binding", "hold_project_projection_scheduler", "hold_project_projection_materialization", "hold_project_projection_cache", "hold_project_projection_gate", "hold_project_projection_connector", "hold_project_projection_conflict", "hold_project_projection_readback_unavailable", "hold_project_projection_privacy"}
HEX = re.compile(r"^[0-9a-f]{64}$")
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FORBIDDEN = {"url", "body", "prompt", "transcript", "token", "secret", "credential", "path", "exception", "metadata", "headers", "authorization"}

class ProjectProjectionError(ValueError):
    def __init__(self, classification: str):
        self.classification = classification if classification in HOLDS else "hold_project_projection_schema"
        super().__init__(self.classification)

class ProjectProjectionHold(ProjectProjectionError):
    pass

class CrashAfterWrite(Exception):
    pass

def _canon(value: Any) -> str:
    try: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError): raise ProjectProjectionHold("hold_project_projection_schema") from None

def _digest(value: Any) -> str: return hashlib.sha256(_canon(value).encode()).hexdigest()

def _hex(value: Any, code="hold_project_projection_binding") -> str:
    if not isinstance(value, str) or not HEX.fullmatch(value): raise ProjectProjectionHold(code)
    return value

def _uuid(value: Any) -> str:
    try: return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError): raise ProjectProjectionHold("hold_project_projection_binding") from None

def _time(value: Any) -> str:
    if not isinstance(value, str) or not TIME.fullmatch(value): raise ProjectProjectionHold("hold_project_projection_schema")
    try: datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: raise ProjectProjectionHold("hold_project_projection_schema") from None
    return value

def _walk(value: Any, depth=0, count=None) -> None:
    count = count or [0]; count[0] += 1
    if depth > 8 or count[0] > 256: raise ProjectProjectionHold("hold_project_projection_schema")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN: raise ProjectProjectionHold("hold_project_projection_privacy")
            _walk(child, depth + 1, count)
    elif isinstance(value, (list, tuple)):
        for child in value: _walk(child, depth + 1, count)
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise ProjectProjectionHold("hold_project_projection_schema")

def _schema(value: Mapping[str, Any]) -> None:
    try:
        import yaml, jsonschema
        schema = yaml.safe_load((Path(__file__).resolve().parent.parent / "schemas/github-project-projection.schema.yaml").read_text())
        jsonschema.Draft202012Validator(schema).validate(value)
    except ProjectProjectionHold: raise
    except Exception: raise ProjectProjectionHold("hold_project_projection_schema") from None

def _result(operation: str, outcome: str, **fields: Any) -> dict[str, Any]:
    if operation not in OPERATIONS or outcome not in OUTCOMES: raise ProjectProjectionHold("hold_project_projection_schema")
    result = {"schema_version": VERSION, "operation": operation, "outcome": outcome, "simulation_only": True, "production_eligibility": False, "network_capability": False, "remote_mutation_performed": False, "authoritative": False, "confirmation_eligible": False}
    result.update({k:v for k,v in fields.items() if v is not None}); _schema(result); return result

def _capability(request: Mapping[str, Any]) -> None:
    gate, cap = request["gate"], request["capability"]
    required_gate = {"kind", "production_eligibility", "project_id", "intent_id", "attempt_sequence", "operation", "repository_id", "remote_project_digest", "desired_effect_digest"}
    required_cap = {"trust_domain", "production_eligibility", "network_capability", "supported_operations"}
    if not isinstance(gate, Mapping) or set(gate) != required_gate or gate.get("kind") != "fixture_only" or gate.get("production_eligibility") is not False: raise ProjectProjectionHold("hold_project_projection_gate")
    expected = {"project_id":request["project_id"], "intent_id":request["intent_id"], "attempt_sequence":request["attempt_sequence"], "operation":request["operation"], "repository_id":request["repository_id"], "remote_project_digest":request["remote_project_digest"], "desired_effect_digest":request["desired_effect_digest"]}
    if any(gate.get(k) != v for k,v in expected.items()): raise ProjectProjectionHold("hold_project_projection_gate")
    if not isinstance(cap, Mapping) or set(cap) != required_cap or cap.get("trust_domain") != "same_process_reference" or cap.get("production_eligibility") is not False or cap.get("network_capability") is not False or not isinstance(cap.get("supported_operations"), list) or set(cap["supported_operations"]) - OPERATIONS or request["operation"] not in cap["supported_operations"]: raise ProjectProjectionHold("hold_project_projection_connector")

def _base(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping): raise ProjectProjectionHold("hold_project_projection_schema")
    allowed = {"schema_version","operation","project_id","work_id","intent_id","attempt_sequence","scheduler_generation","scheduler_head","desired_effect_digest","repository_id","repository_locator_digest","auth_scope_digest","remote_project_digest","source_materialization","item_basis","policy_digest","projection_mode","cache_max_age_seconds","cache_offline","occurred_at","readback_nonce","expected_remote_kind","expected_remote_ref","expected_remote_version","expected_remote_digest","field_digest","option_or_value_digest","readback_only","canceled","compensation","gate","capability"}
    if set(request) - allowed: raise ProjectProjectionHold("hold_project_projection_schema")
    _walk(request); _schema(request)
    if request.get("schema_version") != VERSION or request.get("operation") not in OPERATIONS: raise ProjectProjectionHold("hold_project_projection_schema")
    out=dict(request); out["project_id"]=_uuid(request.get("project_id")); out["intent_id"]=_uuid(request.get("intent_id"))
    if not isinstance(out.get("work_id"),str) or not out["work_id"] or len(out["work_id"].encode()) > 256: raise ProjectProjectionHold("hold_project_projection_binding")
    if not isinstance(out.get("attempt_sequence"),int) or isinstance(out["attempt_sequence"],bool) or out["attempt_sequence"] < 1 or not isinstance(out.get("scheduler_generation"),int) or isinstance(out["scheduler_generation"],bool): raise ProjectProjectionHold("hold_project_projection_binding")
    for key in ("scheduler_head","desired_effect_digest","repository_id","repository_locator_digest","auth_scope_digest","remote_project_digest","policy_digest"): _hex(out.get(key))
    _time(out.get("occurred_at"));
    if "readback_nonce" in out: _time(out["readback_nonce"])
    for flag in ("readback_only","canceled","compensation"):
        if flag in out and out[flag] is not True: raise ProjectProjectionHold("hold_project_projection_schema")
    if out["operation"] == "project_field_set":
        _hex(out.get("field_digest")); _hex(out.get("option_or_value_digest"))
    elif "field_digest" in out or "option_or_value_digest" in out: raise ProjectProjectionHold("hold_project_projection_schema")
    for key in ("expected_remote_ref","expected_remote_version","expected_remote_digest"):
        if key in out: _hex(out[key])
    if "expected_remote_kind" in out and (not isinstance(out["expected_remote_kind"],str) or not out["expected_remote_kind"]): raise ProjectProjectionHold("hold_project_projection_binding")
    if out.get("projection_mode", "enabled") not in {"enabled","disabled","local_only"}: raise ProjectProjectionHold("hold_project_projection_schema")
    if not isinstance(out.get("cache_max_age_seconds", 0), int) or isinstance(out.get("cache_max_age_seconds", 0), bool) or not 0 <= out.get("cache_max_age_seconds", 0) <= 604800 or "cache_offline" in out and type(out["cache_offline"]) is not bool: raise ProjectProjectionHold("hold_project_projection_schema")
    if not isinstance(out.get("source_materialization"),Mapping) or not isinstance(out.get("item_basis"),Mapping): raise ProjectProjectionHold("hold_project_projection_materialization")
    _capability(out)
    out["idempotency_key"] = str(uuid.uuid5(NAMESPACE, _canon([VERSION,out["project_id"],out["intent_id"],out["attempt_sequence"],out["operation"],out["remote_project_digest"],out["desired_effect_digest"],out.get("field_digest"),out.get("option_or_value_digest")])))
    return out

def _scheduler(req: Mapping[str,Any], state: Mapping[str,Any]) -> None:
    if not isinstance(state,Mapping) or state.get("remote_intent_state") != "pending_materialization": raise ProjectProjectionHold("hold_project_projection_scheduler")
    checks={"work_id":req["work_id"],"intent_id":req["intent_id"],"attempt_sequence":req["attempt_sequence"],"desired_effect_digest":req["desired_effect_digest"]}
    if any(state.get(k)!=v for k,v in checks.items()): raise ProjectProjectionHold("hold_project_projection_scheduler")
    generation=state.get("scheduler_generation",state.get("control_generation")); head=state.get("scheduler_head",state.get("control_head"))
    if generation != req["scheduler_generation"] or head != req["scheduler_head"]: raise ProjectProjectionHold("hold_project_projection_scheduler")

def _materialization(req: Mapping[str,Any], result: Mapping[str,Any]) -> None:
    try: materialization._schema_validate(result, "result")
    except Exception: raise ProjectProjectionHold("hold_project_projection_materialization") from None
    expected={"schema_version":"GitHubMaterializationAdapter-v1","project_id":req["project_id"],"intent_id":req["intent_id"],"attempt_sequence":req["attempt_sequence"],"desired_effect_digest":req["desired_effect_digest"],"authoritative":False,"confirmation_eligible":False,"simulation_only":True,"remote_mutation_performed":False}
    if not isinstance(result,Mapping) or any(result.get(k)!=v for k,v in expected.items()) or result.get("outcome") not in {"materialization_plan_ready","materialization_duplicate","materialization_readback_verified"}: raise ProjectProjectionHold("hold_project_projection_materialization")
    basis=req["item_basis"]
    if set(basis)!={"item_digest","materialization_receipt_digest","cache_selector_digest","cache_object_ref_digest"} or any(not isinstance(basis[k],str) or not HEX.fullmatch(basis[k]) for k in basis) or result.get("readback_digest") != basis["materialization_receipt_digest"]: raise ProjectProjectionHold("hold_project_projection_materialization")

def _cache(req: Mapping[str,Any], cache: Mapping[str,Any]|None) -> bool:
    if cache is None: return False
    required={"schema_version":"GitHubEvidenceCache-v1","operation":"project_cache_readout","outcome":"cache_hit","freshness":"fresh_as_of_fetch","coverage":"complete","authoritative":False,"confirmation_eligible":False}
    if not isinstance(cache,Mapping) or any(cache.get(k)!=v for k,v in required.items()): return False
    meta=cache.get("metadata")
    if not isinstance(meta,Mapping) or meta.get("project_id")!=req["project_id"] or meta.get("repository_id")!=req["repository_id"] or meta.get("repository_locator_digest")!=req["repository_locator_digest"] or meta.get("auth_scope_digest")!=req["auth_scope_digest"]: return False
    entries=cache.get("entries")
    return isinstance(entries,list) and len(entries)==1 and isinstance(entries[0],Mapping) and _digest(entries[0].get("opaque_object_ref"))==req["item_basis"].get("cache_object_ref_digest") and entries[0].get("selector_digest")==req["item_basis"].get("cache_selector_digest")

def plan_project_projection(*, projects_root: str, request: Mapping[str,Any], materialization_result: Mapping[str,Any]) -> dict[str,Any]:
    req=_base(request)
    if req.get("canceled") or req.get("compensation"): return _result(req["operation"],"project_projection_canceled",project_id=req["project_id"],intent_id=req["intent_id"])
    if req.get("projection_mode", "enabled") in {"disabled", "local_only"}: return _result(req["operation"],"project_projection_not_required",project_id=req["project_id"],intent_id=req["intent_id"],classification=req["projection_mode"])
    try: actual_state=scheduler.replay_scheduler_state(projects_root, req["project_id"])
    except Exception: raise ProjectProjectionHold("hold_project_projection_scheduler") from None
    _scheduler(req,actual_state); _materialization(req,materialization_result)
    try:
        cache_readout=evidence_cache.project_cache_readout(projects_root=projects_root, project_id=req["project_id"], repository_id=req["repository_id"], repository_locator_digest=req["repository_locator_digest"], auth_scope_digest=req["auth_scope_digest"], evaluated_at=req["occurred_at"], max_age_seconds=req.get("cache_max_age_seconds",0), offline=req.get("cache_offline",False))
    except Exception:
        return _result(req["operation"],"project_projection_approval_required",project_id=req["project_id"],intent_id=req["intent_id"],classification="cache_evidence_unavailable")
    if not _cache(req,cache_readout): return _result(req["operation"],"project_projection_approval_required",project_id=req["project_id"],intent_id=req["intent_id"],classification="cache_evidence_unavailable")
    return _result(req["operation"],"project_projection_plan_ready",project_id=req["project_id"],intent_id=req["intent_id"],request_digest=_digest(_request_receipt(req)))

def _request_receipt(req): return {k:req[k] for k in ("project_id","intent_id","attempt_sequence","operation","remote_project_digest","desired_effect_digest","scheduler_generation","scheduler_head","policy_digest","item_basis")}

class FakeProjectConnector:
    trust_domain="same_process_reference"; production_eligibility=False; network_capability=False
    def __init__(self,state=None,*,crash_after_write=False): self.state=dict(state or {}); self.calls=[]; self.crash_after_write=crash_after_write
    def readback(self, request): self.calls.append(("readback",request["idempotency_key"])); return dict(self.state.get(request["idempotency_key"],{}))
    def write(self, request):
        self.calls.append(("write",request["idempotency_key"])); self.state[request["idempotency_key"]]={"request_digest":_digest(_request_receipt(request)),"remote_project_digest":request["remote_project_digest"],"item_digest":request["item_basis"]["item_digest"],"field_digest":request.get("field_digest"),"option_or_value_digest":request.get("option_or_value_digest"),"nonce":request.get("readback_nonce")}
        if self.crash_after_write: raise CrashAfterWrite

def _matches(req, observed): return isinstance(observed,Mapping) and observed.get("request_digest")==_digest(_request_receipt(req)) and observed.get("remote_project_digest")==req["remote_project_digest"] and observed.get("item_digest")==req["item_basis"]["item_digest"] and observed.get("field_digest")==req.get("field_digest") and observed.get("option_or_value_digest")==req.get("option_or_value_digest")

def execute_project_projection(*, projects_root, request, materialization_result, connector):
    planned=plan_project_projection(projects_root=projects_root,request=request,materialization_result=materialization_result)
    if planned["outcome"] != "project_projection_plan_ready": return planned
    req=_base(request)
    if not isinstance(connector,FakeProjectConnector) or connector.trust_domain!="same_process_reference" or connector.production_eligibility is not False or connector.network_capability is not False: raise ProjectProjectionHold("hold_project_projection_connector")
    pre=connector.readback(req)
    if pre:
        if _matches(req,pre): return _result(req["operation"],"project_projection_duplicate",project_id=req["project_id"],intent_id=req["intent_id"],request_digest=_digest(_request_receipt(req)))
        return _result(req["operation"],"hold_project_projection_conflict",project_id=req["project_id"],intent_id=req["intent_id"],classification="pre_read_conflict")
    if req.get("readback_only"): return _result(req["operation"],"project_projection_recovery_readback_required",project_id=req["project_id"],intent_id=req["intent_id"])
    try: connector.write(req)
    except CrashAfterWrite: return _result(req["operation"],"project_projection_recovery_readback_required",project_id=req["project_id"],intent_id=req["intent_id"])
    post=connector.readback(req)
    if not _matches(req,post): return _result(req["operation"],"hold_project_projection_readback_unavailable",project_id=req["project_id"],intent_id=req["intent_id"],classification="post_read_mismatch")
    return _result(req["operation"],"project_projection_readback_verified",project_id=req["project_id"],intent_id=req["intent_id"],request_digest=_digest(_request_receipt(req)),desired_effect_digest=req["desired_effect_digest"],readback_digest=_digest(post),readback_nonce=req.get("readback_nonce"),remote_mutation_performed=True,confirmation_eligible=False,confirmed=True,adapter_id="github-project-projection-hermetic",adapter_version="1",expected_remote_kind=req.get("expected_remote_kind"),expected_remote_ref=req.get("expected_remote_ref"),expected_remote_version=req.get("expected_remote_version"),expected_remote_digest=req.get("expected_remote_digest"),occurred_at=req["occurred_at"],read_timestamp=req.get("readback_nonce") or req["occurred_at"],opaque_receipt_ref="fake:"+req["idempotency_key"])

__all__=["VERSION","FakeProjectConnector","ProjectProjectionError","ProjectProjectionHold","plan_project_projection","execute_project_projection"]
