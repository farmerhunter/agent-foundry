"""Hermetic, optional Project projection built solely from public Core APIs.

The fake connector is a test boundary, not a GitHub client.  This module never
opens a network connection, invokes a subprocess, persists state, or writes a
local collaboration authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import github_evidence_cache as evidence_cache
import github_materialization_adapter as materialization
from local_collaboration_scheduler import SchedulerHold, replay_scheduler_state

VERSION = "GitHubProjectProjection-v1"
OPERATIONS = {"project_item_add", "project_field_set"}
OUTCOMES = {
    "project_projection_not_required", "project_projection_plan_ready",
    "project_projection_approval_required", "project_projection_duplicate",
    "project_projection_stale_authority_hold", "project_projection_dependency_hold",
    "project_projection_conflict_hold", "project_projection_privacy_hold",
    "project_projection_recovery_readback_required",
    "project_projection_fixture_readback_verified", "project_projection_canceled",
}
HOLDS = {"hold_stale_authority", "hold_dependency", "hold_conflict", "hold_privacy", "hold_schema"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FLAGS = {"simulation_only": True, "production_eligibility": False, "network_capability": False,
         "authoritative": False, "confirmation_eligible": False, "remote_mutation_performed": False}
FORBIDDEN = {"prompt", "transcript", "tool_output", "token", "secret", "credential", "url", "path", "exception", "metadata"}


class ProjectProjectionHold(ValueError):
    def __init__(self, classification: str):
        self.classification = classification if classification in HOLDS else "hold_schema"
        super().__init__(self.classification)


class CrashAfterFakeWrite(Exception):
    """Test-only representation of interruption after a fake in-memory write."""


def _canon(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise ProjectProjectionHold("hold_schema") from None


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode()).hexdigest()


def _uuid(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ProjectProjectionHold("hold_schema") from None


def _hex(value: Any, hold: str = "hold_schema") -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ProjectProjectionHold(hold)
    return value


def _opaque(value: Any) -> str:
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise ProjectProjectionHold("hold_privacy")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise ProjectProjectionHold("hold_schema")
    return value


def _schema(value: Any, definition: str) -> None:
    try:
        import jsonschema
        import yaml
        schema = yaml.safe_load((Path(__file__).resolve().parent.parent / "schemas" / "github-project-projection.schema.yaml").read_text())
        jsonschema.Draft202012Validator(schema).validate(value)
    except Exception:
        raise ProjectProjectionHold("hold_schema") from None


def _result(operation: str, outcome: str, **extra: Any) -> dict[str, Any]:
    if operation not in OPERATIONS or outcome not in OUTCOMES:
        raise ProjectProjectionHold("hold_schema")
    result = {"schema_version": VERSION, "operation": operation, "outcome": outcome, "flags": dict(FLAGS)}
    result.update({key: value for key, value in extra.items() if value is not None})
    _schema(result, "result")
    return result


def _request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise ProjectProjectionHold("hold_schema")
    _schema(request, "request")
    if request.get("schema_version") != VERSION:
        raise ProjectProjectionHold("hold_schema")
    normalized = dict(request)
    normalized["project_id"] = _uuid(request.get("project_id"))
    normalized["intent_id"] = _uuid(request.get("intent_id"))
    if not isinstance(request.get("work_id"), str) or not request["work_id"] or len(request["work_id"].encode()) > 128:
        raise ProjectProjectionHold("hold_schema")
    if not isinstance(request.get("attempt_sequence"), int) or isinstance(request["attempt_sequence"], bool) or request["attempt_sequence"] < 1:
        raise ProjectProjectionHold("hold_schema")
    for key in ("desired_effect_digest", "repository_id", "repository_locator_digest", "auth_scope_digest", "expected_value_digest"):
        _hex(request.get(key))
    if request.get("operation") not in OPERATIONS or request.get("disposition") not in {"required", "not_required", "approval_required", "canceled"}:
        raise ProjectProjectionHold("hold_schema")
    _timestamp(request.get("evaluated_at"))
    if not isinstance(request.get("max_age_seconds"), int) or isinstance(request["max_age_seconds"], bool) or not 0 <= request["max_age_seconds"] <= 86400:
        raise ProjectProjectionHold("hold_schema")
    normalized["opaque_item_basis"] = _opaque(request.get("opaque_item_basis"))
    normalized["expected_revision"] = _opaque(request.get("expected_revision"))
    return normalized


def _validate_external(value: Any, schema_name: str, hold: str = "hold_dependency") -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectProjectionHold(hold)
    try:
        import jsonschema
        import yaml
        schema = yaml.safe_load((Path(__file__).resolve().parent.parent / "schemas" / schema_name).read_text())
        jsonschema.Draft202012Validator(schema).validate(value)
    except Exception:
        raise ProjectProjectionHold(hold) from None
    return value


def _materialization_basis(request: Mapping[str, Any]) -> Mapping[str, Any]:
    result = _validate_external(request.get("materialization_result"), "github-materialization-adapter.schema.yaml")
    if result.get("schema_version") != materialization.VERSION or result.get("authoritative") is not False or result.get("confirmation_eligible") is not False or result.get("simulation_only") is not True or result.get("remote_mutation_performed") is not False:
        raise ProjectProjectionHold("hold_dependency")
    if result.get("project_id") != request["project_id"] or result.get("intent_id") != request["intent_id"] or result.get("attempt_sequence") != request["attempt_sequence"] or result.get("desired_effect_digest") != request["desired_effect_digest"]:
        raise ProjectProjectionHold("hold_dependency")
    if result.get("expected_remote_ref") != request["opaque_item_basis"]:
        raise ProjectProjectionHold("hold_dependency")
    if result.get("outcome") not in {"materialization_readback_verified", "materialization_duplicate"}:
        raise ProjectProjectionHold("hold_dependency")
    return result


def _state_binding(request: Mapping[str, Any], state: Mapping[str, Any], *, pair: tuple[int, str] | None = None) -> tuple[int, str]:
    if not isinstance(state, Mapping):
        raise ProjectProjectionHold("hold_dependency")
    generation, head = state.get("authority_generation"), state.get("authority_head")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        raise ProjectProjectionHold("hold_dependency")
    _hex(head, "hold_dependency")
    actual = (generation, head)
    if pair is not None and actual != pair:
        raise ProjectProjectionHold("hold_stale_authority")
    if state.get("remote_intent_state") != "pending_materialization":
        raise ProjectProjectionHold("hold_dependency")
    if state.get("work", {}).get("work_id") not in (None, request["work_id"]) and state.get("work_id") != request["work_id"]:
        raise ProjectProjectionHold("hold_dependency")
    for key in ("intent_id", "attempt_sequence", "desired_effect_digest"):
        if state.get(key) != request[key]:
            raise ProjectProjectionHold("hold_dependency")
    if state.get("project_id") not in (None, request["project_id"]):
        raise ProjectProjectionHold("hold_dependency")
    return actual


def _cache_basis(request: Mapping[str, Any], cache: Mapping[str, Any]) -> str:
    cache = _validate_external(cache, "github-evidence-cache.schema.yaml")
    if cache.get("operation") != "project_cache_readout" or cache.get("outcome") != "cache_hit" or cache.get("freshness") != "fresh_as_of_fetch" or cache.get("coverage") != "complete" or cache.get("authoritative") is not False or cache.get("confirmation_eligible") is not False:
        raise ProjectProjectionHold("hold_dependency")
    meta = cache.get("metadata")
    if not isinstance(meta, Mapping) or any(meta.get(k) != request[k] for k in ("project_id", "repository_id", "repository_locator_digest", "auth_scope_digest")):
        raise ProjectProjectionHold("hold_dependency")
    entries = cache.get("entries")
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], Mapping):
        raise ProjectProjectionHold("hold_dependency")
    entry = entries[0]
    if entry.get("opaque_object_ref") != request["opaque_item_basis"] or not isinstance(entry.get("entry_key"), str):
        raise ProjectProjectionHold("hold_dependency")
    return _hex(entry["entry_key"], "hold_dependency")


def _read_cache(request: Mapping[str, Any], projects_root: str | Path) -> Mapping[str, Any]:
    try:
        return evidence_cache.project_cache_readout(projects_root=projects_root, project_id=request["project_id"], repository_id=request["repository_id"], repository_locator_digest=request["repository_locator_digest"], auth_scope_digest=request["auth_scope_digest"], evaluated_at=request["evaluated_at"], max_age_seconds=request["max_age_seconds"], offline=False)
    except Exception:
        raise ProjectProjectionHold("hold_dependency") from None


def _replay(request: Mapping[str, Any], projects_root: str | Path, pair: tuple[int, str] | None = None) -> tuple[int, str]:
    try:
        return _state_binding(request, replay_scheduler_state(projects_root, request["project_id"]), pair=pair)
    except SchedulerHold:
        raise ProjectProjectionHold("hold_dependency") from None


def _plan_payload(request: Mapping[str, Any], pair: tuple[int, str], cache_key: str, materialization_result: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema_version": VERSION, "operation": request["operation"], "outcome": "project_projection_plan_ready", "project_id": request["project_id"], "work_id": request["work_id"], "intent_id": request["intent_id"], "attempt_sequence": request["attempt_sequence"], "desired_effect_digest": request["desired_effect_digest"], "opaque_item_basis": request["opaque_item_basis"], "expected_revision": request["expected_revision"], "expected_value_digest": request["expected_value_digest"], "authority_generation": pair[0], "authority_head": pair[1], "cache_entry_key": cache_key, "materialization_result_digest": _digest(materialization_result), "flags": dict(FLAGS)}


def plan_project_projection(request: Mapping[str, Any], *, projects_root: str | Path) -> dict[str, Any]:
    """Build one optional fake projection plan from public #403/#404/#405 APIs."""
    req = _request(request)
    common = {"project_id": req["project_id"], "intent_id": req["intent_id"], "attempt_sequence": req["attempt_sequence"]}
    if req["disposition"] == "canceled":
        return _result(req["operation"], "project_projection_canceled", **common)
    if req["disposition"] == "not_required":
        return _result(req["operation"], "project_projection_not_required", **common)
    if req["disposition"] == "approval_required":
        return _result(req["operation"], "project_projection_approval_required", **common)
    mat = _materialization_basis(req)
    pair = _replay(req, projects_root)
    cache_key = _cache_basis(req, _read_cache(req, projects_root))
    plan = _plan_payload(req, pair, cache_key, mat)
    plan["plan_digest"] = _digest(plan)
    _schema(plan, "plan")
    return plan


def _plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise ProjectProjectionHold("hold_schema")
    _schema(plan, "plan")
    if plan.get("flags") != FLAGS:
        raise ProjectProjectionHold("hold_schema")
    calculated = dict(plan); supplied = calculated.pop("plan_digest", None)
    if supplied != _digest(calculated):
        raise ProjectProjectionHold("hold_schema")
    return dict(plan)


def _request_from_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {key: plan[key] for key in ("project_id", "work_id", "intent_id", "attempt_sequence", "desired_effect_digest")}


class FakeProjectConnector:
    """In-memory test connector; no host, network, or filesystem capability."""
    trust_domain = "same_process_reference"
    production_eligibility = False
    network_capability = False

    def __init__(self, state: Mapping[str, Any] | None = None, *, crash_after_write: bool = False, on_pre_read: Any = None):
        self.state = dict(state or {})
        self.calls: list[str] = []
        self.crash_after_write = crash_after_write
        self.on_pre_read = on_pre_read

    def read(self, plan: Mapping[str, Any], *, pre: bool = False) -> Mapping[str, Any]:
        self.calls.append("pre_read" if pre else "post_read")
        if pre and self.on_pre_read:
            self.on_pre_read()
        return dict(self.state.get(plan["plan_digest"], {}))

    def write(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append("write")
        value = {"opaque_item_basis": plan["opaque_item_basis"], "expected_revision": plan["expected_revision"], "expected_value_digest": plan["expected_value_digest"], "plan_digest": plan["plan_digest"]}
        self.state[plan["plan_digest"]] = value
        if self.crash_after_write:
            raise CrashAfterFakeWrite()
        return value


def _connector(connector: Any) -> Any:
    if not isinstance(connector, FakeProjectConnector) or connector.trust_domain != "same_process_reference" or connector.production_eligibility is not False or connector.network_capability is not False:
        raise ProjectProjectionHold("hold_dependency")
    return connector


def _expected(plan: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    return isinstance(observed, Mapping) and all(observed.get(key) == plan[key] for key in ("opaque_item_basis", "expected_revision", "expected_value_digest", "plan_digest"))


def execute_project_projection(plan: Mapping[str, Any], connector: Any, *, projects_root: str | Path) -> dict[str, Any]:
    """Make at most one fake in-memory effect after two public #404 replays."""
    p = _plan(plan); fake = _connector(connector); req = _request_from_plan(p); pair = (p["authority_generation"], p["authority_head"])
    try:
        _replay(req, projects_root, pair)
        pre = fake.read(p, pre=True)
        if pre:
            if _expected(p, pre):
                return _result(p["operation"], "project_projection_duplicate", project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"])
            return _result(p["operation"], "project_projection_conflict_hold", classification="hold_conflict", project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"])
        _replay(req, projects_root, pair)
    except ProjectProjectionHold as exc:
        if exc.classification == "hold_stale_authority":
            return _result(p["operation"], "project_projection_stale_authority_hold", classification=exc.classification, project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"])
        return _result(p["operation"], "project_projection_dependency_hold", classification=exc.classification, project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"])
    try:
        fake.write(p)
    except CrashAfterFakeWrite:
        return _result(p["operation"], "project_projection_recovery_readback_required", project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"])
    post = fake.read(p)
    if not _expected(p, post):
        return _result(p["operation"], "project_projection_conflict_hold", classification="hold_conflict", project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"])
    return _result(p["operation"], "project_projection_fixture_readback_verified", project_id=p["project_id"], intent_id=p["intent_id"], attempt_sequence=p["attempt_sequence"], plan_digest=p["plan_digest"], fixture_readback_digest=_digest(post))


def recover_project_projection(plan: Mapping[str, Any], connector: Any) -> dict[str, Any]:
    """Read fake state only after an interrupted fake effect; never write."""
    p = _plan(plan); fake = _connector(connector)
    observed = fake.read(p)
    common = {"project_id": p["project_id"], "intent_id": p["intent_id"], "attempt_sequence": p["attempt_sequence"], "plan_digest": p["plan_digest"]}
    if not observed:
        return _result(p["operation"], "project_projection_recovery_readback_required", **common)
    if not _expected(p, observed):
        return _result(p["operation"], "project_projection_conflict_hold", classification="hold_conflict", **common)
    return _result(p["operation"], "project_projection_fixture_readback_verified", fixture_readback_digest=_digest(observed), **common)


__all__ = ["VERSION", "ProjectProjectionHold", "CrashAfterFakeWrite", "FakeProjectConnector", "plan_project_projection", "execute_project_projection", "recover_project_projection"]
