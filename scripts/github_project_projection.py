"""Hermetic, non-authoritative GitHub Project projection adapter.

This boundary deliberately consumes the local scheduler, cache, and
materialization results without owning any of their durable state.  The only
connector it accepts is a same-process fake used to prove projection protocol
semantics.  It has no network, subprocess, environment, or GitHub capability.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import github_evidence_cache as cache
import local_collaboration_scheduler as scheduler

VERSION = "GitHubProjectProjection-v1"
HEX = re.compile(r"^[0-9a-f]{64}$")
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
OUTCOMES = {"project_projection_not_required", "project_projection_plan_ready", "project_projection_approval_required", "project_projection_duplicate", "hold_project_projection_stale_authority", "hold_project_projection_conflict", "hold_project_projection_dependency", "hold_project_projection_privacy", "project_projection_recovery_readback_required", "project_projection_readback_verified", "project_projection_canceled"}
FORBIDDEN = {"url", "body", "prompt", "transcript", "token", "credential", "secret", "path", "exception", "metadata", "raw", "name", "label"}


class ProjectProjectionHold(ValueError):
    def __init__(self, classification: str):
        self.classification = classification
        super().__init__(classification)


def _canon(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raise ProjectProjectionHold("hold_project_projection_dependency") from None


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode()).hexdigest()


def _result(operation: str, outcome: str, **fields: Any) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    value = {"schema_version": VERSION, "operation": operation, "outcome": outcome,
             "simulation_only": True, "production_eligibility": False,
             "network_capability": False, "remote_mutation_performed": False,
             "authoritative": False, "confirmed": outcome == "project_projection_readback_verified"}
    value.update({k: v for k, v in fields.items() if v is not None})
    _validate_schema(value)
    return value


def _validate_schema(value: Any) -> None:
    try:
        import yaml
        import jsonschema
        schema = yaml.safe_load((Path(__file__).resolve().parent.parent / "schemas" / "github-project-projection.schema.yaml").read_text())
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(value)
    except Exception:
        raise ProjectProjectionHold("hold_project_projection_dependency") from None


def _safe(value: Any) -> None:
    if isinstance(value, Mapping):
        if len(value) > 32:
            raise ProjectProjectionHold("hold_project_projection_privacy")
        for key, child in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN:
                raise ProjectProjectionHold("hold_project_projection_privacy")
            _safe(child)
    elif isinstance(value, list):
        if len(value) > 32:
            raise ProjectProjectionHold("hold_project_projection_privacy")
        for child in value:
            _safe(child)
    elif not isinstance(value, (str, int, bool)) or value is None:
        raise ProjectProjectionHold("hold_project_projection_dependency")


def _request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    _validate_schema(request)
    if request.get("schema_version") != VERSION:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    _safe({k: v for k, v in request.items() if k != "materialization_result"})
    for name in ("desired_effect_digest", "repository_locator_digest", "auth_scope_digest", "cache_entry_key", "expected_remote_digest"):
        if not isinstance(request.get(name), str) or not HEX.fullmatch(request[name]):
            raise ProjectProjectionHold("hold_project_projection_dependency")
    if not isinstance(request.get("repository_id"), str) or not request["repository_id"]:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    if not isinstance(request.get("evaluated_at"), str) or not TS.fullmatch(request["evaluated_at"]):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    try:
        datetime.fromisoformat(request["evaluated_at"].replace("Z", "+00:00"))
    except ValueError:
        raise ProjectProjectionHold("hold_project_projection_dependency") from None
    cap = request.get("fixture_capability")
    if cap != {"trust_domain": "same_process_reference", "simulation_only": True, "production_eligibility": False, "network_capability": False}:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    normalized = dict(request)
    _prevalidate_materialization(normalized)
    return normalized


def _pair(state: Mapping[str, Any]) -> tuple[int, str]:
    generation, head = state.get("authority_generation"), state.get("authority_head")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0 or not isinstance(head, str) or not HEX.fullmatch(head):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    return generation, head


def _scheduler_binding(req: Mapping[str, Any], state: Mapping[str, Any]) -> tuple[int, str]:
    pair = _pair(state)
    if (state.get("project_id") not in (None, req["project_id"]) or state.get("work_id") != req["work_id"] or
            str(state.get("intent_id")) != req["intent_id"] or state.get("attempt_sequence") != req["attempt_sequence"] or
            state.get("desired_effect_digest") != req["desired_effect_digest"] or state.get("remote_intent_state") != "pending_materialization"):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
        if state.get(key) != req[key]:
            raise ProjectProjectionHold("hold_project_projection_dependency")
    if state.get("scheduler_state") == "disabled" or state.get("local_state") in {"terminal", "hold", "disabled"}:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    return pair


def _prevalidate_materialization(req: Mapping[str, Any]) -> Mapping[str, Any]:
    result, material_request = req.get("materialization_result"), req.get("materialization_request")
    # Validate precisely against #403's published result envelope first.
    try:
        import github_materialization_adapter as materialization
        materialization._schema_validate(result, "result")
    except Exception:
        raise ProjectProjectionHold("hold_project_projection_dependency") from None
    required = {"schema_version": materialization.VERSION, "operation": "issue_comment", "outcome": "materialization_readback_verified",
                "simulation_only": True, "remote_mutation_performed": False,
                "authoritative": False, "confirmation_eligible": False,
                "project_id": req["project_id"], "intent_id": req["intent_id"],
                "attempt_sequence": req["attempt_sequence"], "desired_effect_digest": req["desired_effect_digest"],
                "expected_remote_kind": req["expected_remote_kind"], "expected_remote_ref": req["expected_remote_ref"],
                "expected_remote_digest": req["expected_remote_digest"], "expected_remote_version": req["expected_remote_version"]}
    if not isinstance(result, Mapping) or any(result.get(k) != v for k, v in required.items()):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    if req["opaque_item_ref"] != req["expected_remote_ref"]:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    # Re-execute the same closed, in-memory #403 fake boundary.  This binds
    # every receipt fact (including request/readback digests and timestamps)
    # without opening the #404 authority or #405 cache.
    if not isinstance(material_request, Mapping) or material_request.get("approved_remote_content") is not None:
        raise ProjectProjectionHold("hold_project_projection_privacy")
    for key in ("project_id", "intent_id", "attempt_sequence", "desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
        if material_request.get(key) != req.get(key):
            raise ProjectProjectionHold("hold_project_projection_dependency")
    if material_request.get("adapter_id") != result.get("adapter_id") or material_request.get("adapter_version") != result.get("adapter_version"):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    state = {"project_id": req["project_id"], "work_id": req["work_id"], "intent_id": req["intent_id"], "attempt_sequence": req["attempt_sequence"], "desired_effect_digest": req["desired_effect_digest"], "remote_intent_state": "pending_materialization", "scheduler_generation": material_request.get("scheduler_generation"), "scheduler_head": material_request.get("scheduler_head")}
    try:
        reproduced = materialization.execute_materialization(material_request, state, materialization.FakeConnector())
    except Exception:
        raise ProjectProjectionHold("hold_project_projection_dependency") from None
    if reproduced != result:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    return result


def _materialization(req: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the already prevalidated #403 public execution result."""
    return _prevalidate_materialization(req)


def _cache_basis(req: Mapping[str, Any], projects_root: str | Path) -> Mapping[str, Any]:
    try:
        readout = cache.project_cache_readout(projects_root=projects_root, project_id=req["project_id"], repository_id=req["repository_id"], repository_locator_digest=req["repository_locator_digest"], auth_scope_digest=req["auth_scope_digest"], evaluated_at=req["evaluated_at"], max_age_seconds=req["max_age_seconds"], offline=False)
    except Exception as exc:
        raise ProjectProjectionHold("hold_project_projection_dependency") from exc
    if (readout.get("outcome") != "cache_hit" or readout.get("freshness") != "fresh_as_of_fetch" or
            readout.get("coverage") != "complete" or readout.get("authoritative") is not False or readout.get("confirmation_eligible") is not False):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    matches = [entry for entry in readout.get("entries", []) if entry.get("opaque_object_ref") == req["opaque_item_ref"]]
    if len(matches) != 1 or matches[0].get("entry_key") != req["cache_entry_key"]:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    return {"entry_key": req["cache_entry_key"], "entry_digest": _digest(matches[0]), "cache_generation": readout.get("metadata", {}).get("generation")}


def _plan_digest(req: Mapping[str, Any], pair: tuple[int, str], cbasis: Mapping[str, Any], materialized: Mapping[str, Any]) -> str:
    return _digest({"request": {k: v for k, v in req.items() if k != "materialization_result"}, "authority_generation": pair[0], "authority_head": pair[1], "cache": cbasis, "materialization_digest": _digest(materialized)})


def plan_project_projection(*, projects_root: str | Path, request: Mapping[str, Any]) -> dict[str, Any]:
    req = _request(request)
    state = scheduler.replay_scheduler_state(projects_root, req["project_id"])
    pair = _scheduler_binding(req, state)
    cbasis = _cache_basis(req, projects_root)
    materialized = _materialization(req)
    digest = _plan_digest(req, pair, cbasis, materialized)
    return _result("plan_project_projection", "project_projection_plan_ready", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=pair[0], authority_head=pair[1], desired_effect_digest=req["desired_effect_digest"], opaque_item_ref=req["opaque_item_ref"], request_digest=_digest(req), plan_digest=digest, expected_remote_kind=req["expected_remote_kind"], expected_remote_ref=req["expected_remote_ref"], expected_remote_digest=req["expected_remote_digest"], expected_remote_version=req["expected_remote_version"], plan={"request": req, "cache_basis": cbasis, "materialization_result": materialized})


def _valid_plan(plan: Mapping[str, Any], projects_root: str | Path | None = None) -> tuple[Mapping[str, Any], tuple[int, str]]:
    if not isinstance(plan, Mapping):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    _validate_schema(plan)
    if (plan.get("operation") != "plan_project_projection" or plan.get("outcome") != "project_projection_plan_ready" or
            plan.get("simulation_only") is not True or plan.get("production_eligibility") is not False or
            plan.get("network_capability") is not False or plan.get("remote_mutation_performed") is not False or
            plan.get("authoritative") is not False or plan.get("confirmed") is not False):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    # plan has the one controlled extension required to execute it.
    allowed = {"schema_version", "operation", "outcome", "simulation_only", "production_eligibility", "network_capability", "remote_mutation_performed", "authoritative", "confirmed", "project_id", "work_id", "intent_id", "attempt_sequence", "authority_generation", "authority_head", "desired_effect_digest", "opaque_item_ref", "request_digest", "plan_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "plan"}
    if set(plan) - allowed or not isinstance(plan.get("plan"), Mapping):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    req = plan["plan"].get("request")
    req = _request(req)
    pair = (plan.get("authority_generation"), plan.get("authority_head"))
    materialized = _materialization(req)
    if plan["plan"].get("materialization_result") != materialized:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    if not isinstance(pair[0], int) or not isinstance(pair[1], str) or not HEX.fullmatch(pair[1]):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    # The materialization digest is intentionally only compared, never reconstructed from caller content.
    if plan.get("request_digest") != _digest(req):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    if plan.get("plan_digest") != _plan_digest(req, pair, plan["plan"].get("cache_basis", {}), materialized):
        raise ProjectProjectionHold("hold_project_projection_dependency")
    if projects_root is not None and _cache_basis(req, projects_root) != plan["plan"]["cache_basis"]:
        raise ProjectProjectionHold("hold_project_projection_dependency")
    return req, pair


class FakeProjectConnector:
    trust_domain = "same_process_reference"
    simulation_only = True
    production_eligibility = False
    network_capability = False
    def __init__(self, state: Mapping[str, Any] | None = None):
        self.state = dict(state or {})
        self.calls: list[str] = []
    def read(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append("read")
        return dict(self.state.get(request["desired_effect_digest"], {}))
    def write(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append("write")
        value = {"effect_kind": request["effect_kind"], "desired_effect_digest": request["desired_effect_digest"], "opaque_item_ref": request["opaque_item_ref"], "expected_remote_kind": request["expected_remote_kind"], "expected_remote_ref": request["expected_remote_ref"], "expected_remote_digest": request["expected_remote_digest"], "expected_remote_version": request["expected_remote_version"]}
        self.state[request["desired_effect_digest"]] = value
        return value


def _connector(connector: Any) -> None:
    if (getattr(connector, "trust_domain", None) != "same_process_reference" or getattr(connector, "simulation_only", None) is not True or getattr(connector, "production_eligibility", None) is not False or getattr(connector, "network_capability", None) is not False or not callable(getattr(connector, "read", None)) or not callable(getattr(connector, "write", None))):
        raise ProjectProjectionHold("hold_project_projection_dependency")


def _matches(req: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    return isinstance(observed, Mapping) and all(observed.get(key) == req.get(key) for key in ("desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "opaque_item_ref")) and observed.get("effect_kind") == req["effect_kind"]


def _receipt(req: Mapping[str, Any], plan: Mapping[str, Any], observed: Mapping[str, Any], outcome: str) -> dict[str, Any]:
    if outcome == "project_projection_duplicate":
        return _result("execute_project_projection", outcome, project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=plan["authority_generation"], authority_head=plan["authority_head"], desired_effect_digest=req["desired_effect_digest"], opaque_item_ref=req["opaque_item_ref"], request_digest=plan["request_digest"], plan_digest=plan["plan_digest"])
    materialized = plan["plan"]["materialization_result"]
    return _result("execute_project_projection", outcome, project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=plan["authority_generation"], authority_head=plan["authority_head"], desired_effect_digest=req["desired_effect_digest"], opaque_item_ref=req["opaque_item_ref"], request_digest=plan["request_digest"], plan_digest=plan["plan_digest"], readback_digest=_digest(observed), opaque_receipt_ref="fake-project:" + req["desired_effect_digest"], adapter_id=materialized["adapter_id"], adapter_version=materialized["adapter_version"], occurred_at=materialized["occurred_at"], read_timestamp=materialized["read_timestamp"], readback_nonce=materialized["readback_nonce"], expected_remote_kind=req["expected_remote_kind"], expected_remote_ref=req["expected_remote_ref"], expected_remote_digest=req["expected_remote_digest"], expected_remote_version=req["expected_remote_version"])


def execute_project_projection(*, projects_root: str | Path, plan: Mapping[str, Any], connector: Any) -> dict[str, Any]:
    req, planned_pair = _valid_plan(plan, projects_root)
    _connector(connector)
    initial = scheduler.replay_scheduler_state(projects_root, req["project_id"])
    if _scheduler_binding(req, initial) != planned_pair:
        return _result("execute_project_projection", "hold_project_projection_stale_authority", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=planned_pair[0], authority_head=planned_pair[1])
    observed = connector.read(req)
    if observed:
        if _matches(req, observed):
            return _receipt(req, plan, observed, "project_projection_duplicate")
        return _result("execute_project_projection", "hold_project_projection_conflict", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=planned_pair[0], authority_head=planned_pair[1])
    prewrite = scheduler.replay_scheduler_state(projects_root, req["project_id"])
    if _scheduler_binding(req, prewrite) != planned_pair:
        return _result("execute_project_projection", "hold_project_projection_stale_authority", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=planned_pair[0], authority_head=planned_pair[1])
    connector.write(req)
    post = connector.read(req)
    if not _matches(req, post):
        return _result("execute_project_projection", "hold_project_projection_conflict", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=planned_pair[0], authority_head=planned_pair[1])
    return _receipt(req, plan, post, "project_projection_readback_verified")


def recover_project_projection(*, plan: Mapping[str, Any], connector: Any) -> dict[str, Any]:
    req, pair = _valid_plan(plan)
    _connector(connector)
    observed = connector.read(req)
    if _matches(req, observed):
        materialized = plan["plan"]["materialization_result"]
        return _result("recover_project_projection", "project_projection_readback_verified", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=pair[0], authority_head=pair[1], desired_effect_digest=req["desired_effect_digest"], request_digest=plan["request_digest"], plan_digest=plan["plan_digest"], readback_digest=_digest(observed), opaque_receipt_ref="fake-project:" + req["desired_effect_digest"], adapter_id=materialized["adapter_id"], adapter_version=materialized["adapter_version"], occurred_at=materialized["occurred_at"], read_timestamp=materialized["read_timestamp"], readback_nonce=materialized["readback_nonce"], expected_remote_kind=req["expected_remote_kind"], expected_remote_ref=req["expected_remote_ref"], expected_remote_digest=req["expected_remote_digest"], expected_remote_version=req["expected_remote_version"])
    if observed:
        return _result("recover_project_projection", "hold_project_projection_conflict", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=pair[0], authority_head=pair[1])
    return _result("recover_project_projection", "project_projection_recovery_readback_required", project_id=req["project_id"], work_id=req["work_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], authority_generation=pair[0], authority_head=pair[1])


__all__ = ["FakeProjectConnector", "ProjectProjectionHold", "VERSION", "execute_project_projection", "plan_project_projection", "recover_project_projection"]
