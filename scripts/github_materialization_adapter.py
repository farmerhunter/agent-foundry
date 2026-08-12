"""Hermetic selective GitHub materialization boundary.

This module is intentionally a planner and an injected same-process fake
connector.  It never opens a socket, invokes a host command, reads a
credential, or writes a ledger.  The scheduler's ``pending_materialization``
event remains the sole durable outbox; callers must pass its replay state.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from collections.abc import Mapping
from typing import Any

VERSION = "GitHubMaterializationAdapter-v1"
BRIDGE_VERSION = "GitHubLabelMaterializationBridge-v1"
ADAPTER_ID = "github-materialization-hermetic"
ADAPTER_VERSION = "1"
# This literal names the separately implemented production-capable seam.  It
# is deliberately not added to the hermetic planner's OPERATIONS: callers
# cannot turn FakeConnector into a live connector by changing a request.
REAL_CONNECTOR_OPERATION = "add_existing_label"
NAMESPACE = uuid.UUID("f5c27bf1-0c2e-4f96-b87f-7dc4a43e1bf1")
OPERATIONS = {"issue_create", "issue_comment", "pull_request_comment"}
CLASSIFICATIONS = {"local_only", "must_publish", "optional_sync"}
OUTCOMES = {"materialization_not_required", "materialization_plan_ready",
            "materialization_approval_required", "materialization_duplicate",
            "materialization_simulated", "materialization_readback_verified",
            "materialization_readback_unavailable",
            "materialization_recovery_readback_required", "materialization_canceled"}
HOLDS = {"hold_materialization_policy", "hold_materialization_scheduler_state",
         "hold_materialization_binding", "hold_materialization_approval",
         "hold_materialization_connector_untrusted", "hold_materialization_operation_unsupported",
         "hold_materialization_privacy", "hold_materialization_duplicate_or_divergent",
         "hold_materialization_remote_conflict", "hold_materialization_readback_unavailable",
         "hold_materialization_retry_required", "hold_materialization_stale_basis",
         "hold_materialization_schema"}
BRIDGE_HOLD_REASONS = {
    "schema_or_privacy", "scheduler_or_authority_drift", "repository_or_target_binding",
    "authorization_evidence", "capability_unavailable_or_untrusted",
    "capability_broader_or_unobservable", "stale_preimage", "duplicate_forward_attempt",
    "provider_write_or_readback_unavailable", "unexpected_connector_result",
}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output",
             "secret", "credential", "token", "native_history", "body", "raw_response",
             "response_body", "exception", "path", "absolute_path", "local_path"}


class MaterializationError(ValueError):
    def __init__(self, classification: str):
        self.classification = classification if classification in HOLDS else "hold_materialization_schema"
        super().__init__(self.classification)


class MaterializationHold(MaterializationError):
    pass


def _canon(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise MaterializationHold("hold_materialization_schema") from None


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode()).hexdigest()


def _walk(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    count = count or [0]; count[0] += 1
    if depth > 10 or count[0] > 2000:
        raise MaterializationHold("hold_materialization_schema")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN:
                raise MaterializationHold("hold_materialization_privacy")
            if isinstance(child, str) and any(word in child.lower() for word in FORBIDDEN):
                raise MaterializationHold("hold_materialization_privacy")
            _walk(child, depth + 1, count)
    elif isinstance(value, (list, tuple)):
        for child in value: _walk(child, depth + 1, count)
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise MaterializationHold("hold_materialization_schema")


def _walk_content(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    """Validate synthetic content separately; raw content never enters results."""
    count = count or [0]; count[0] += 1
    if depth > 5 or count[0] > 500: raise MaterializationHold("hold_materialization_privacy")
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) or k not in {"title", "body", "summary", "labels"} for k in value):
            raise MaterializationHold("hold_materialization_privacy")
        for child in value.values(): _walk_content(child, depth + 1, count)
    elif isinstance(value, list):
        for child in value: _walk_content(child, depth + 1, count)
    elif isinstance(value, str):
        if len(value.encode()) > 8192 or any(word in value.lower() for word in {"password", "token", "credential", "secret", "transcript", "tool_output"}):
            raise MaterializationHold("hold_materialization_privacy")
    elif value is not None and not isinstance(value, (int, bool)):
        raise MaterializationHold("hold_materialization_privacy")
def _uuid(value: Any) -> str:
    try: return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError): raise MaterializationHold("hold_materialization_binding") from None


def _ts(value: Any) -> str:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise MaterializationHold("hold_materialization_schema")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MaterializationHold("hold_materialization_schema") from None
    return value


def _hex(value: Any, classification: str = "hold_materialization_binding") -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value): raise MaterializationHold(classification)
    return value


def _result(operation: str, outcome: str, *, classification: str | None = None, **fields: Any) -> dict[str, Any]:
    if outcome not in OUTCOMES: raise MaterializationHold("hold_materialization_schema")
    out = {"schema_version": VERSION, "operation": operation, "outcome": outcome,
           "simulation_only": True, "remote_mutation_performed": False,
           "authoritative": False, "confirmation_eligible": False}
    if classification: out["classification"] = classification
    out.update({key: value for key, value in fields.items() if value is not None}); _schema_validate(out, "result"); return out


def _schema_validate(value: Any, definition: str) -> None:
    try:
        import yaml, jsonschema
        schema = yaml.safe_load((Path(__file__).resolve().parent.parent / "schemas" / "github-materialization-adapter.schema.yaml").read_text())
        checker = jsonschema.FormatChecker()
        @checker.checks("strict-rfc3339")
        def strict(value):
            if not isinstance(value, str) or not RFC3339.fullmatch(value): return False
            try: datetime.fromisoformat(value.replace("Z", "+00:00")); return True
            except ValueError: return False
        @checker.checks("utf8-256")
        def f256(value): return isinstance(value, str) and len(value.encode()) <= 256
        @checker.checks("utf8-8192")
        def f8192(value): return isinstance(value, str) and len(value.encode()) <= 8192
        @checker.checks("utf8-128")
        def f128(value): return isinstance(value, str) and len(value.encode()) <= 128
        @checker.checks("utf8-content")
        def fcontent(value): return isinstance(value, Mapping) and len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()) <= 8192
        jsonschema.Draft202012Validator(schema, format_checker=checker).validate(value)
    except Exception:
        raise MaterializationHold("hold_materialization_schema") from None


def _base(request: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"schema_version", "project_id", "work_id", "intent_id", "attempt_sequence",
                   "scheduler_generation", "scheduler_head", "desired_effect_digest",
               "classification", "operation", "repository_id", "repository_locator_digest",
               "auth_scope_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_version",
               "expected_remote_digest", "approved_content_digest", "privacy_class", "adapter_id",
               "adapter_version", "gate", "capability", "occurred_at", "timestamp_provenance",
               "nonce", "approved_remote_content", "readback_only", "canceled", "compensation"}
    if not isinstance(request, Mapping) or set(request) - allowed:
        raise MaterializationHold("hold_materialization_schema")
    _schema_validate(request, "request")
    safe_request = dict(request); safe_request.pop("approved_remote_content", None); _walk(safe_request)
    if request.get("schema_version") != VERSION: raise MaterializationHold("hold_materialization_schema")
    for flag in ("canceled", "compensation", "readback_only"):
        if flag in request and request[flag] is not True: raise MaterializationHold("hold_materialization_schema")
    pid = _uuid(request.get("project_id")); intent = _uuid(request.get("intent_id"))
    if not isinstance(request.get("work_id"), str) or not request["work_id"]: raise MaterializationHold("hold_materialization_binding")
    attempt = request.get("attempt_sequence")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1: raise MaterializationHold("hold_materialization_binding")
    if not isinstance(request.get("scheduler_generation"), int) or isinstance(request.get("scheduler_generation"), bool) or request["scheduler_generation"] < 0: raise MaterializationHold("hold_materialization_stale_basis")
    _hex(request.get("scheduler_head")); _hex(request.get("desired_effect_digest")); _hex(request.get("approved_content_digest"))
    if request.get("classification") not in CLASSIFICATIONS: raise MaterializationHold("hold_materialization_policy")
    if request.get("operation") not in OPERATIONS: raise MaterializationHold("hold_materialization_operation_unsupported")
    for key in ("repository_id", "repository_locator_digest", "auth_scope_digest"):
        _hex(request.get(key))
    if request.get("privacy_class") not in {"public_metadata", "metadata_only", "repository_internal_redacted"}:
        raise MaterializationHold("hold_materialization_privacy")
    _ts(request.get("occurred_at"))
    if "nonce" in request: _ts(request.get("nonce"))
    if request.get("timestamp_provenance") != "explicit": raise MaterializationHold("hold_materialization_schema")
    for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_version"):
        if key in request and (not isinstance(request[key], str) or not request[key]): raise MaterializationHold("hold_materialization_binding")
    if "expected_remote_digest" in request: _hex(request["expected_remote_digest"])
    content = request.get("approved_remote_content")
    if "approved_remote_content" in request and content is None: raise MaterializationHold("hold_materialization_privacy")
    if content is not None:
        if not isinstance(content, Mapping): raise MaterializationHold("hold_materialization_privacy")
        for field in ("body", "summary"):
            if field in content and not isinstance(content[field], str): raise MaterializationHold("hold_materialization_privacy")
        _walk_content(content); encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if hashlib.sha256(encoded).hexdigest() != request["approved_content_digest"]:
            raise MaterializationHold("hold_materialization_binding")
        if len(encoded) > 8192 or sum(len(item) for item in content.values() if isinstance(item, str)) > 8192: raise MaterializationHold("hold_materialization_privacy")
        if "title" in content and (not isinstance(content["title"], str) or len(content["title"].encode()) > 256): raise MaterializationHold("hold_materialization_privacy")
        if "labels" in content and (not isinstance(content["labels"], list) or len(content["labels"]) > 10 or any(not isinstance(label, str) or len(label.encode()) > 128 for label in content["labels"])): raise MaterializationHold("hold_materialization_privacy")
    idem_input = [VERSION, pid, intent, attempt, request["operation"], request["repository_id"], request["desired_effect_digest"], request["approved_content_digest"]]
    normalized = dict(request); normalized["project_id"] = pid; normalized["intent_id"] = intent
    if isinstance(normalized.get("gate"), Mapping):
        gate = dict(normalized["gate"])
        gate["project_id"] = _uuid(gate.get("project_id")); gate["intent_id"] = _uuid(gate.get("intent_id")); normalized["gate"] = gate
    return {**normalized, "project_id": pid, "intent_id": intent, "attempt_sequence": attempt,
            "idempotency_key": str(uuid.uuid5(NAMESPACE, _canon(idem_input)))}


def _state_check(req: Mapping[str, Any], scheduler_state: Mapping[str, Any]) -> None:
    if not isinstance(scheduler_state, Mapping): raise MaterializationHold("hold_materialization_scheduler_state")
    if scheduler_state.get("project_id") not in (None, req["project_id"]): raise MaterializationHold("hold_materialization_binding")
    if scheduler_state.get("remote_intent_state") != "pending_materialization": raise MaterializationHold("hold_materialization_scheduler_state")
    state_generation = scheduler_state.get("scheduler_generation", scheduler_state.get("control_generation"))
    state_head = scheduler_state.get("scheduler_head", scheduler_state.get("control_head"))
    if state_generation != req["scheduler_generation"] or state_head != req["scheduler_head"]: raise MaterializationHold("hold_materialization_stale_basis")
    if str(scheduler_state.get("intent_id")) != req["intent_id"] or scheduler_state.get("attempt_sequence") != req["attempt_sequence"]: raise MaterializationHold("hold_materialization_stale_basis")
    if scheduler_state.get("desired_effect_digest") != req["desired_effect_digest"]: raise MaterializationHold("hold_materialization_stale_basis")
    if req.get("nonce") is not None and scheduler_state.get("readback_nonce") not in (None, req["nonce"]): raise MaterializationHold("hold_materialization_stale_basis")
    for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_version", "expected_remote_digest"):
        state_key = scheduler_state.get(key)
        if state_key is not None and state_key != req.get(key): raise MaterializationHold("hold_materialization_binding")


def _gate_capability(req: Mapping[str, Any]) -> None:
    gate, cap = req.get("gate"), req.get("capability")
    if not isinstance(gate, Mapping) or set(gate) != {"kind", "production_eligibility", "project_id", "intent_id", "attempt_sequence", "operation", "repository_id", "effect_digest", "content_digest"}:
        raise MaterializationHold("hold_materialization_approval")
    if gate.get("kind") != "fixture_only" or type(gate.get("production_eligibility")) is not bool or gate.get("production_eligibility") is not False: raise MaterializationHold("hold_materialization_approval")
    if not isinstance(gate.get("attempt_sequence"), int) or isinstance(gate.get("attempt_sequence"), bool): raise MaterializationHold("hold_materialization_approval")
    if any(gate.get(k) != v for k, v in {"project_id": req["project_id"], "intent_id": req["intent_id"], "attempt_sequence": req["attempt_sequence"], "operation": req["operation"], "repository_id": req["repository_id"], "effect_digest": req["desired_effect_digest"], "content_digest": req["approved_content_digest"]}.items()): raise MaterializationHold("hold_materialization_approval")
    required = {"trust_domain": "same_process_reference", "production_eligibility": False, "network_capability": False}
    if not isinstance(cap, Mapping) or set(cap) != {"trust_domain", "production_eligibility", "network_capability", "adapter_id", "adapter_version", "supported_operations"} or cap.get("trust_domain") != "same_process_reference" or type(cap.get("production_eligibility")) is not bool or cap.get("production_eligibility") is not False or type(cap.get("network_capability")) is not bool or cap.get("network_capability") is not False: raise MaterializationHold("hold_materialization_connector_untrusted")
    if not isinstance(cap.get("supported_operations"), list) or not cap["supported_operations"] or len(set(cap["supported_operations"])) != len(cap["supported_operations"]) or any(not isinstance(item, str) or item not in OPERATIONS for item in cap["supported_operations"]): raise MaterializationHold("hold_materialization_connector_untrusted")
    if cap.get("adapter_id") != req.get("adapter_id") or cap.get("adapter_version") != req.get("adapter_version") or req["operation"] not in set(cap.get("supported_operations", [])): raise MaterializationHold("hold_materialization_connector_untrusted")


def plan_materialization(request: Mapping[str, Any], scheduler_state: Mapping[str, Any], cache_observation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    req = _base(request)
    if req.get("canceled") is True or req.get("compensation") is True:
        return _result(req["operation"], "materialization_canceled", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], idempotency_key=req["idempotency_key"])
    if req["classification"] == "local_only":
        if "gate" in req or "capability" in req:
            if req.get("gate") is None or req.get("capability") is None: raise MaterializationHold("hold_materialization_schema")
            _gate_capability(req)
        return _result(req["operation"], "materialization_not_required", classification="local_only", project_id=req["project_id"], intent_id=req["intent_id"], idempotency_key=req["idempotency_key"])
    _state_check(req, scheduler_state)
    if isinstance(cache_observation, Mapping) and (cache_observation.get("outcome") not in {"cache_hit", "cache_miss"} or cache_observation.get("freshness") != "fresh_as_of_fetch" or cache_observation.get("coverage") != "complete" or cache_observation.get("authoritative") is not False or cache_observation.get("confirmation_eligible") is not False):
        return _result(req["operation"], "materialization_approval_required", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], idempotency_key=req["idempotency_key"], hold="hold_materialization_stale_basis")
    if req["classification"] == "must_publish" or "gate" in req or "capability" in req:
        _gate_capability(req)
    elif req["classification"] == "optional_sync":
        return _result(req["operation"], "materialization_plan_ready", classification="optional_sync", project_id=req["project_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], idempotency_key=req["idempotency_key"], desired_effect_digest=req["desired_effect_digest"])
    return _result(req["operation"], "materialization_plan_ready", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], idempotency_key=req["idempotency_key"], desired_effect_digest=req["desired_effect_digest"])


class FakeConnector:
    """Deterministic in-memory connector used only by tests and callers."""
    trust_domain = "same_process_reference"; production_eligibility = False; network_capability = False
    def __init__(self, state: Mapping[str, Any] | None = None, *, crash_after_write: bool = False, fail_pre_read: bool = False):
        self.state = dict(state or {}); self.calls: list[tuple[str, str]] = []; self.crash_after_write = crash_after_write; self.fail_pre_read = fail_pre_read
    def readback(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(("readback", request["idempotency_key"]))
        if self.fail_pre_read and not self.state.get(request["idempotency_key"]): raise OSError("unavailable")
        return dict(self.state.get(request["idempotency_key"], {}))
    def write(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(("write", request["idempotency_key"]))
        self.state[request["idempotency_key"]] = {"operation": request["operation"], "effect_digest": request["desired_effect_digest"], "content_digest": request["approved_content_digest"], "remote_kind": request.get("expected_remote_kind"), "remote_ref": request.get("expected_remote_ref"), "remote_version": request.get("expected_remote_version"), "remote_digest": request.get("expected_remote_digest")}
        if self.crash_after_write: raise CrashAfterWrite
        return self.state[request["idempotency_key"]]


class CrashAfterWrite(Exception):
    """Test-only boundary representing process loss after the fake write."""


def _remote_matches(req: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    expected = {
        "operation": req["operation"], "remote_kind": req.get("expected_remote_kind"),
        "remote_ref": req.get("expected_remote_ref"), "remote_version": req.get("expected_remote_version"),
        "remote_digest": req.get("expected_remote_digest"),
    }
    return all(observed.get(key) == value for key, value in expected.items())


def execute_materialization(request: Mapping[str, Any], scheduler_state: Mapping[str, Any], connector: Any, cache_observation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    planned = plan_materialization(request, scheduler_state, cache_observation)
    if planned["outcome"] != "materialization_plan_ready": return planned
    req = _base(request)
    if req["classification"] == "optional_sync" and req.get("gate") is None:
        return planned
    _gate_capability(req)
    if not isinstance(connector, FakeConnector) and not (getattr(connector, "trust_domain", None) == "same_process_reference" and getattr(connector, "production_eligibility", True) is False and getattr(connector, "network_capability", True) is False): raise MaterializationHold("hold_materialization_connector_untrusted")
    if not hasattr(connector, "readback") or not hasattr(connector, "write"): raise MaterializationHold("hold_materialization_connector_untrusted")
    try: pre = connector.readback(req)
    except Exception: raise MaterializationHold("hold_materialization_readback_unavailable") from None
    if isinstance(pre, Mapping) and pre:
        if _remote_matches(req, pre) and pre.get("effect_digest") == req["desired_effect_digest"] and pre.get("content_digest") == req["approved_content_digest"]: return _result(req["operation"], "materialization_duplicate", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], idempotency_key=req["idempotency_key"])
        raise MaterializationHold("hold_materialization_remote_conflict")
    if req.get("readback_only") is True:
        return _result(req["operation"], "materialization_recovery_readback_required", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], idempotency_key=req["idempotency_key"])
    try: connector.write(req)
    except CrashAfterWrite:
        return _result(req["operation"], "materialization_recovery_readback_required", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], idempotency_key=req["idempotency_key"])
    except MaterializationHold: raise
    except Exception: raise MaterializationHold("hold_materialization_readback_unavailable") from None
    try: post = connector.readback(req)
    except Exception: raise MaterializationHold("hold_materialization_retry_required") from None
    if not isinstance(post, Mapping) or not _remote_matches(req, post) or post.get("effect_digest") != req["desired_effect_digest"] or post.get("content_digest") != req["approved_content_digest"]: raise MaterializationHold("hold_materialization_remote_conflict")
    request_digest = _digest({k: req[k] for k in ("project_id", "intent_id", "attempt_sequence", "operation", "repository_id", "desired_effect_digest", "approved_content_digest")})
    read_at = req.get("nonce") or req["occurred_at"]
    return _result(req["operation"], "materialization_readback_verified", classification=req["classification"], project_id=req["project_id"], intent_id=req["intent_id"], attempt_sequence=req["attempt_sequence"], idempotency_key=req["idempotency_key"], readback_digest=_digest(post), opaque_receipt_ref="fake:" + req["idempotency_key"], confirmed=True, adapter_id=req["adapter_id"], adapter_version=req["adapter_version"], expected_remote_kind=req.get("expected_remote_kind"), expected_remote_ref=req.get("expected_remote_ref"), expected_remote_digest=req.get("expected_remote_digest"), expected_remote_version=req.get("expected_remote_version"), desired_effect_digest=req["desired_effect_digest"], request_digest=request_digest, occurred_at=req["occurred_at"], read_timestamp=read_at, readback_nonce=req.get("nonce") or req["occurred_at"])


def _bridge_hold(request: Any, reason: str, *, connector_called: bool = False,
                 mutation_count: int | None = None) -> dict[str, Any]:
    """Return only fixed classifications; never carry exception or auth text."""
    safe = request if isinstance(request, Mapping) else {}
    out: dict[str, Any] = {
        "schema_version": BRIDGE_VERSION,
        "outcome": "real_label_materialization_hold",
        "reason": reason if reason in BRIDGE_HOLD_REASONS else "schema_or_privacy",
        "connector_called": connector_called,
        "authoritative": False,
        "confirmation_eligible": False,
        "scheduler_confirmation_performed": False,
        "observation_state": "not_observed",
        "retry_count": 0,
    }
    # Invalid input need not claim identity fields.  Valid bridge input can
    # safely identify its public metadata binding without leaking auth facts.
    for key in ("project_id", "intent_id", "attempt_sequence", "scheduler_generation", "scheduler_head", "target", "label"):
        if key in safe:
            out[key if key not in {"scheduler_generation", "scheduler_head"} else key.replace("scheduler_", "authority_")] = safe[key]
    if mutation_count is not None:
        out["mutation_count"] = mutation_count
    _schema_validate(out, "github_cli_label_bridge_result")
    return out


def _bridge_request(request: Any) -> dict[str, Any]:
    required = {"schema_version", "human_authorization_ref", "project_id", "work_id", "intent_id",
                "attempt_sequence", "scheduler_generation", "scheduler_head", "desired_effect_digest",
                "repository_id", "repository_locator_digest", "target", "label", "preimage_digest",
                "expected_capability_version", "expected_capability_digest", "privacy_class", "write_budget",
                "retry_budget", "occurred_at", "timestamp_provenance"}
    if not isinstance(request, Mapping) or set(request) != required:
        raise MaterializationHold("hold_materialization_schema")
    _schema_validate(request, "github_cli_label_bridge_request")
    _walk(request)
    if request.get("schema_version") != BRIDGE_VERSION or request.get("privacy_class") != "metadata_only":
        raise MaterializationHold("hold_materialization_privacy")
    if request.get("write_budget") != 1 or request.get("retry_budget") != 0:
        raise MaterializationHold("hold_materialization_binding")
    project_id, intent_id = _uuid(request.get("project_id")), _uuid(request.get("intent_id"))
    if not isinstance(request.get("work_id"), str) or not request["work_id"] or len(request["work_id"].encode()) > 128:
        raise MaterializationHold("hold_materialization_binding")
    if (not isinstance(request.get("human_authorization_ref"), str) or not request["human_authorization_ref"]
            or len(request["human_authorization_ref"].encode()) > 256):
        raise MaterializationHold("hold_materialization_approval")
    if not isinstance(request.get("attempt_sequence"), int) or isinstance(request["attempt_sequence"], bool) or request["attempt_sequence"] < 1:
        raise MaterializationHold("hold_materialization_binding")
    if not isinstance(request.get("scheduler_generation"), int) or isinstance(request["scheduler_generation"], bool) or request["scheduler_generation"] < 0:
        raise MaterializationHold("hold_materialization_stale_basis")
    for key in ("scheduler_head", "desired_effect_digest", "repository_id", "repository_locator_digest", "preimage_digest", "expected_capability_digest"):
        _hex(request.get(key))
    if request.get("expected_capability_version") != "1":
        raise MaterializationHold("hold_materialization_connector_untrusted")
    _ts(request.get("occurred_at"))
    if request.get("timestamp_provenance") != "explicit":
        raise MaterializationHold("hold_materialization_schema")
    target = request.get("target")
    if not isinstance(target, Mapping) or set(target) != {"owner", "repository", "number", "kind"}:
        raise MaterializationHold("hold_materialization_binding")
    owner, repository, number, kind = target.get("owner"), target.get("repository"), target.get("number"), target.get("kind")
    if (not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,37}", owner)
            or not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repository)
            or not isinstance(number, int) or isinstance(number, bool) or number < 1 or kind not in {"issue", "pull_request"}):
        raise MaterializationHold("hold_materialization_binding")
    if not isinstance(request.get("label"), str) or not request["label"] or len(request["label"].encode()) > 128 or any(ord(char) < 32 or ord(char) == 127 for char in request["label"]):
        raise MaterializationHold("hold_materialization_privacy")
    normalized = dict(request)
    normalized.update({"project_id": project_id, "intent_id": intent_id,
                       "target": {"owner": owner, "repository": repository, "number": number, "kind": kind}})
    return normalized


def _bridge_scheduler_state(request: Mapping[str, Any], state: Any) -> dict[str, Any]:
    if not isinstance(state, Mapping) or state.get("remote_intent_state") != "pending_materialization":
        raise MaterializationHold("hold_materialization_scheduler_state")
    required = {"project_id": request["project_id"], "intent_id": request["intent_id"],
                "attempt_sequence": request["attempt_sequence"], "desired_effect_digest": request["desired_effect_digest"],
                "scheduler_generation": request["scheduler_generation"], "scheduler_head": request["scheduler_head"]}
    if any(state.get(key) != value for key, value in required.items()):
        raise MaterializationHold("hold_materialization_stale_basis")
    return {"authority_generation": state["scheduler_generation"], "authority_head": state["scheduler_head"]}


def _bridge_effect_digest(request: Mapping[str, Any]) -> str:
    return _digest({"version": BRIDGE_VERSION, "operation": "add_existing_label", "target": request["target"],
                    "label": request["label"], "preimage_digest": request["preimage_digest"],
                    "project_id": request["project_id"], "intent_id": request["intent_id"],
                    "attempt_sequence": request["attempt_sequence"], "repository_id": request["repository_id"],
                    "repository_locator_digest": request["repository_locator_digest"]})


def _bridge_reason(reason: str) -> str:
    if reason in {"hold_capability_unavailable", "hold_capability_untrusted", "hold_scope_unavailable", "hold_scope_insufficient", "hold_auth_mismatch"}:
        return "capability_unavailable_or_untrusted"
    if reason == "hold_capability_broader_or_unobservable": return "capability_broader_or_unobservable"
    if reason in {"hold_authority_pair_stale"}: return "scheduler_or_authority_drift"
    if reason in {"hold_target_invalid", "hold_target_type_invalid"}: return "repository_or_target_binding"
    if reason in {"hold_preimage_stale"}: return "stale_preimage"
    if reason in {"hold_second_forward_attempt"}: return "duplicate_forward_attempt"
    if reason in {"hold_provider_conflict", "hold_provider_rate_limited", "hold_provider_unavailable", "hold_write_failed", "hold_readback_mismatch", "hold_label_absent"}:
        return "provider_write_or_readback_unavailable"
    return "unexpected_connector_result"


def execute_real_label_materialization(request: Mapping[str, Any], scheduler_state: Mapping[str, Any], connector: Any) -> dict[str, Any]:
    """The sole public production-capable bridge, intentionally non-confirming."""
    try:
        req = _bridge_request(request)
        authority_pair = _bridge_scheduler_state(req, scheduler_state)
    except MaterializationHold as held:
        return _bridge_hold({}, "scheduler_or_authority_drift" if str(held) in {"hold_materialization_scheduler_state", "hold_materialization_stale_basis"} else "schema_or_privacy")
    try:
        from github_materialization_github_cli_connector import CONNECTOR_VERSION, GitHubCliConnectorHold, GitHubCliIssueLabelConnector
        if type(connector) is not GitHubCliIssueLabelConnector:
            return _bridge_hold(req, "authorization_evidence")
        if connector.repository_capability_required is not True:
            return _bridge_hold(req, "capability_broader_or_unobservable")
        binding = connector.repository_binding
        if binding != {"owner": req["target"]["owner"], "repository": req["target"]["repository"]}:
            return _bridge_hold(req, "repository_or_target_binding")
        if req["repository_locator_digest"] != _digest(binding) or req["desired_effect_digest"] != _bridge_effect_digest(req):
            return _bridge_hold(req, "repository_or_target_binding")
        if req["expected_capability_version"] != CONNECTOR_VERSION:
            return _bridge_hold(req, "capability_unavailable_or_untrusted")
        plan = {"schema_version": "GitHubCliIssueLabelConnector-v1", "human_authorization_ref": req["human_authorization_ref"],
                "operation": "add_existing_label", "target": req["target"], "label": req["label"],
                "preimage_digest": req["preimage_digest"], **authority_pair,
                "expected_capability_version": req["expected_capability_version"], "expected_capability_digest": req["expected_capability_digest"]}
        receipt = connector.add_existing_label(plan, authority_pair=authority_pair)
    except GitHubCliConnectorHold as held:
        return _bridge_hold(req, _bridge_reason(held.reason), connector_called=True)
    except Exception:
        return _bridge_hold(req, "unexpected_connector_result", connector_called=True)
    if not isinstance(receipt, Mapping) or receipt.get("outcome") not in {"duplicate_no_mutation", "label_added"} or receipt.get("mutation_count") not in {0, 1}:
        return _bridge_hold(req, "unexpected_connector_result", connector_called=True)
    outcome = "real_label_duplicate_observed_unverified" if receipt["outcome"] == "duplicate_no_mutation" else "real_label_added_observed_unverified"
    result = {"schema_version": BRIDGE_VERSION, "outcome": outcome, "project_id": req["project_id"], "intent_id": req["intent_id"],
            "attempt_sequence": req["attempt_sequence"], **authority_pair, "target": req["target"], "label": req["label"],
            "connector_receipt_id": receipt["receipt_id"], "readback_digest": receipt["readback_digest"],
            "mutation_count": receipt["mutation_count"], "connector_called": True, "retry_count": 0,
            "authoritative": False, "confirmation_eligible": False, "scheduler_confirmation_performed": False,
            "observation_state": "observed_unverified"}
    _schema_validate(result, "github_cli_label_bridge_result")
    return result


__all__ = ["VERSION", "BRIDGE_VERSION", "REAL_CONNECTOR_OPERATION", "FakeConnector", "MaterializationError", "MaterializationHold", "plan_materialization", "execute_materialization", "execute_real_label_materialization"]
