"""Deterministic local Work scheduler over the ORCH-02 SQLite authority.

This module deliberately contains no network, GitHub, Project, or native-agent
operation.  Remote confirmation can only enter through ``apply_remote_readback``
with an injected adapter and a fresh local-head check.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from local_collaboration_ledger import (LedgerBusyError, LedgerConflictError,
    LedgerError, LedgerIntegrityError, LedgerPermissionError, LedgerSchemaError,
    LocalCollaborationLedger)
import local_collaboration_control_plane as control

VERSION = "LocalCollaborationScheduler-v1"
NAMESPACE = uuid.UUID("4d6c0b76-2ad1-4f5d-b00f-9d65e1f61a2e")
KINDS = {"scheduler_initialized", "work_transition_recorded", "scheduler_disabled",
         "remote_intent_recorded", "remote_materialization_pending",
         "remote_observation_recorded", "remote_confirmation_recorded",
         "remote_failure_recorded", "remote_conflict_recorded",
         "remote_intent_canceled", "privacy_hold_recorded"}
PROVENANCE = {"explicit", "estimated", "unavailable", "not_exposed"}
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output",
             "secret", "native_history", "native_thread_id", "body", "payload_raw", "exception"}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
LOCAL_STATES = {"registered", "queued", "claimed", "active", "hold", "successor_required", "completed", "canceled", "disabled"}
REMOTE_STATES = {"not_requested", "accepted_local", "pending_materialization", "observed_unverified", "readback_unavailable", "confirmed", "failed", "conflict", "privacy_held", "canceled"}
# The remote-intent lifecycle is deliberately explicit. A local intent must
# first be marked pending before any adapter observation or terminal outcome
# can be recorded. Observation/outcome events describe the current attempt by
# default; only an explicitly supplied next attempt number advances it.
REMOTE_PREDECESSORS = {
    "remote_materialization_pending": {"accepted_local", "failed", "readback_unavailable"},
    "remote_observation_recorded": {"pending_materialization"},
    "remote_confirmation_recorded": {"pending_materialization", "observed_unverified"},
    "remote_failure_recorded": {"pending_materialization", "observed_unverified"},
    "remote_conflict_recorded": {"pending_materialization", "observed_unverified"},
    "remote_intent_canceled": {"pending_materialization", "observed_unverified"},
    "privacy_hold_recorded": {"pending_materialization", "observed_unverified"},
}
LOCAL_TRANSITIONS = {
    "registered": {"queued"}, "queued": {"claimed", "canceled", "disabled", "hold"},
    "claimed": {"active", "hold", "canceled", "disabled"},
    "active": {"hold", "successor_required", "completed", "canceled", "disabled"},
    "hold": {"queued"}, "successor_required": {"active"},
    "completed": set(), "canceled": set(), "disabled": set(),
}
FAILURE_CODES = {"hold_scheduler_not_enabled", "hold_control_plane_unready", "hold_unknown_version_or_state",
    "hold_missing_work_root_owner", "hold_anchor_or_budget_conflict", "hold_duplicate_or_divergent",
    "hold_transition_order", "hold_terminal_or_disabled", "hold_stale_ledger_head", "hold_untrusted_readback",
    "hold_readback_binding_conflict", "hold_readback_unavailable", "hold_privacy", "hold_schema_or_version",
    "hold_resume_receipt_required", "hold_successor_readiness_required", "hold_disabled_enable_gate",
    "hold_retry_receipt_required",
    "hold_ledger_busy", "hold_ledger_integrity", "hold_ledger_permission", "hold_ledger_schema"}

# A confirmation is an authority transition.  The only currently available
# materialization boundary is deliberately hermetic, so it can never supply
# trusted confirmation evidence.  Keep the request/response envelopes closed
# nonetheless: this prevents malformed evidence from reaching an adapter and
# makes the future trust-boundary contract explicit rather than implicit.
READBACK_REQUEST_KEYS = {"project_id", "work_id", "operation", "intent_id", "attempt_sequence",
    "request_digest", "occurred_at", "desired_effect_digest", "expected_remote_kind",
    "expected_remote_ref", "expected_remote_digest", "expected_remote_version"}
READBACK_RESPONSE_KEYS = {"schema_version", "operation", "outcome", "simulation_only",
    "remote_mutation_performed", "authoritative", "confirmation_eligible", "classification",
    "project_id", "intent_id", "attempt_sequence", "idempotency_key", "readback_digest",
    "opaque_receipt_ref", "confirmed", "adapter_id", "adapter_version", "expected_remote_kind",
    "expected_remote_ref", "expected_remote_digest", "expected_remote_version",
    "desired_effect_digest", "request_digest", "occurred_at", "read_timestamp", "readback_nonce"}

COMMON_PAYLOAD_KEYS = {"work_id", "run_id", "owner_role", "control_generation", "control_head",
    "durable_anchor_digest", "budget_digest", "intent_id", "attempt_sequence", "classification",
    "next_action", "explicit_sequence", "request_digest", "resume_receipt_ref", "resume_receipt_digest",
    "resume_authority", "successor_readiness_ref", "successor_readiness_digest", "successor_id"}
COMMON_PAYLOAD_KEYS |= {"retry_receipt_ref", "retry_receipt_digest", "retry_authority"}
PAYLOAD_KEYS = {
    "scheduler_initialized": COMMON_PAYLOAD_KEYS | {"enable_gate_ref", "enable_gate_digest", "enable_gate_authority"},
    "scheduler_disabled": COMMON_PAYLOAD_KEYS,
    "work_transition_recorded": COMMON_PAYLOAD_KEYS | {"transition_sequence", "from_state", "to_state"},
    "remote_intent_recorded": COMMON_PAYLOAD_KEYS | {"intent_kind", "desired_effect_digest", "human_gate_class"},
    "remote_materialization_pending": COMMON_PAYLOAD_KEYS | {"desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"},
    "remote_observation_recorded": COMMON_PAYLOAD_KEYS | {"desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "observed_remote_state"},
    "remote_confirmation_recorded": COMMON_PAYLOAD_KEYS | {"desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "adapter_id", "adapter_version", "readback_digest", "read_timestamp", "readback_nonce", "opaque_receipt_ref"},
    "remote_failure_recorded": COMMON_PAYLOAD_KEYS | {"desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"},
    "remote_conflict_recorded": COMMON_PAYLOAD_KEYS | {"desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"},
    "remote_intent_canceled": COMMON_PAYLOAD_KEYS | {"desired_effect_digest"},
    "privacy_hold_recorded": COMMON_PAYLOAD_KEYS | {"intent_id", "attempt_sequence", "desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"},
}


class SchedulerError(ValueError):
    pass


class SchedulerHold(SchedulerError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _project(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SchedulerHold("hold_control_plane_unready") from exc


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise SchedulerHold("hold_unknown_version_or_state")
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchedulerHold("hold_unknown_version_or_state") from exc
    return value


def _walk(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    count = count or [0]
    count[0] += 1
    if depth > 12 or count[0] > 5000:
        raise SchedulerHold("hold_schema_or_version")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN:
                raise SchedulerHold("hold_privacy")
            _walk(item, depth + 1, count)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, depth + 1, count)


def _inner(envelope: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = envelope.get("payload", {})
    return payload if isinstance(payload, Mapping) else {}


def _validate_payload(kind: str, payload: Mapping[str, Any]) -> None:
    allowed = PAYLOAD_KEYS.get(kind)
    if allowed is None or not isinstance(payload, Mapping) or not set(payload).issubset(allowed):
        raise SchedulerHold("hold_schema_or_version")
    for key in ("transition_sequence", "attempt_sequence", "control_generation", "explicit_sequence"):
        if key in payload and payload[key] is not None and (not isinstance(payload[key], int) or isinstance(payload[key], bool) or payload[key] < 0):
            raise SchedulerHold("hold_schema_or_version")
    for key in ("desired_effect_digest", "expected_remote_digest", "readback_digest", "request_digest", "durable_anchor_digest", "budget_digest", "resume_receipt_digest", "retry_receipt_digest", "successor_readiness_digest", "enable_gate_digest"):
        if key in payload and payload[key] is not None and (not isinstance(payload[key], str) or not re.fullmatch(r"[0-9a-f]{64}", payload[key])):
            raise SchedulerHold("hold_schema_or_version")
    if kind == "work_transition_recorded":
        if not isinstance(payload.get("from_state"), str) or not isinstance(payload.get("to_state"), str):
            raise SchedulerHold("hold_schema_or_version")
    if kind in {"remote_intent_recorded", "remote_materialization_pending", "remote_observation_recorded", "remote_confirmation_recorded", "remote_failure_recorded", "remote_conflict_recorded", "remote_intent_canceled"}:
        try:
            uuid.UUID(str(payload.get("intent_id")))
        except (ValueError, TypeError, AttributeError):
            raise SchedulerHold("hold_schema_or_version")
    if kind == "privacy_hold_recorded":
        try:
            uuid.UUID(str(payload.get("intent_id")))
        except (ValueError, TypeError, AttributeError):
            raise SchedulerHold("hold_schema_or_version")
        if not isinstance(payload.get("attempt_sequence"), int) or payload.get("attempt_sequence") < 1:
            raise SchedulerHold("hold_schema_or_version")
        if not isinstance(payload.get("desired_effect_digest"), str) or not re.fullmatch(r"[0-9a-f]{64}", payload["desired_effect_digest"]):
            raise SchedulerHold("hold_schema_or_version")
        for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
            value = payload.get(key)
            if value is not None and (not isinstance(value, str) or not value):
                raise SchedulerHold("hold_schema_or_version")
        if payload.get("expected_remote_digest") is not None and not re.fullmatch(r"[0-9a-f]{64}", payload["expected_remote_digest"]):
            raise SchedulerHold("hold_schema_or_version")
    if kind == "remote_confirmation_recorded" and any(not isinstance(payload.get(k), str) or not payload.get(k) for k in ("adapter_id", "adapter_version", "read_timestamp", "readback_nonce", "opaque_receipt_ref")):
        raise SchedulerHold("hold_schema_or_version")


def _event_identity(kind: str, pid: str, payload: Mapping[str, Any]) -> str:
    p = _inner(payload)
    if kind == "scheduler_initialized": identity = f"init|{pid}|{p.get('enable_gate_digest', 'initial')}"
    elif kind == "work_transition_recorded": identity = f"transition|{pid}|{p.get('work_id')}|{p.get('transition_sequence')}"
    elif kind == "remote_intent_recorded": identity = f"intent|{pid}|{p.get('intent_id')}"
    elif kind in {"remote_materialization_pending", "remote_observation_recorded", "remote_confirmation_recorded", "remote_failure_recorded", "remote_conflict_recorded", "remote_intent_canceled"}:
        identity = f"attempt|{pid}|{p.get('intent_id')}|{p.get('attempt_sequence')}|{kind}"
    elif kind == "privacy_hold_recorded": identity = f"privacy|{pid}|{p.get('work_id') or p.get('intent_id')}|{p.get('explicit_sequence')}"
    else: identity = f"state|{pid}|{kind}|{p.get('explicit_sequence', 1)}"
    return str(uuid.uuid5(NAMESPACE, f"{VERSION}|{identity}"))


def _validate_envelope(envelope: Any) -> Mapping[str, Any]:
    if not isinstance(envelope, Mapping) or set(envelope) != {"version", "project_id", "kind", "occurred_at", "timestamp_provenance", "payload"}:
        raise SchedulerHold("hold_unknown_version_or_state")
    if envelope["version"] != VERSION or envelope["kind"] not in KINDS:
        raise SchedulerHold("hold_unknown_version_or_state")
    _project(envelope["project_id"]); _timestamp(envelope["occurred_at"])
    if envelope["timestamp_provenance"] not in PROVENANCE or not isinstance(envelope["payload"], Mapping):
        raise SchedulerHold("hold_unknown_version_or_state")
    _walk(envelope["payload"]); _validate_payload(envelope["kind"], envelope["payload"])
    return envelope


def _envelope(pid: str, kind: str, payload: Mapping[str, Any], occurred_at: str, provenance: str) -> dict[str, Any]:
    if kind not in KINDS or provenance not in PROVENANCE:
        raise SchedulerHold("hold_unknown_version_or_state")
    _walk(payload)
    if provenance in {"unavailable", "not_exposed"} and any(k in payload for k in ("observed_remote_state", "readback_digest", "observed_value")):
        raise SchedulerHold("hold_untrusted_readback")
    env = {"version": VERSION, "project_id": pid, "kind": kind, "occurred_at": occurred_at,
           "timestamp_provenance": provenance, "payload": dict(payload)}
    _validate_envelope(env)
    return env


def _event(pid: str, kind: str, payload: Mapping[str, Any], occurred_at: str, provenance: str = "explicit") -> dict[str, Any]:
    env = _envelope(pid, kind, payload, occurred_at, provenance)
    return {"event_type": "scheduler." + kind, "event_id": _event_identity(kind, pid, env),
            "payload": env, "actor": "local-scheduler-v1", "source": "orch-03-local-scheduler", "root": pid}


def _scheduler_event(event: Any) -> tuple[str, Mapping[str, Any]]:
    envelope = event.payload if hasattr(event, "payload") else event.get("payload", {})
    kind = envelope.get("kind") if isinstance(envelope, Mapping) else None
    if not kind:
        typ = event.event_type if hasattr(event, "event_type") else event.get("event_type", "")
        kind = str(typ).removeprefix("scheduler.")
    return kind, _validate_envelope(envelope)


def reduce_scheduler_state(control_state: Mapping[str, Any], scheduler_events: Iterable[Any]) -> dict[str, Any]:
    if not isinstance(control_state, Mapping) or not control_state.get("initialized"):
        raise SchedulerHold("hold_control_plane_unready")
    work = control_state.get("work") or {}
    if not work.get("work_id") or not work.get("role"):
        raise SchedulerHold("hold_missing_work_root_owner")
    state = {"scheduler_state": "not_enabled", "local_state": "registered", "remote_intent_state": "not_requested",
             "work_id": work.get("work_id"), "run_id": None, "owner_role": work.get("role"),
             "root_budget_tokens": work.get("root_budget_tokens"), "remaining_budget_tokens": work.get("remaining_budget_tokens"),
             "control_generation": None, "control_head": None, "durable_anchor_digest": work.get("durable_anchor_digest"),
             "budget_digest": _digest([work.get("root_budget_tokens"), work.get("remaining_budget_tokens")]),
             "transition_sequence": 0, "intent_id": None, "desired_effect_digest": None, "expected_remote_kind": None,
             "expected_remote_ref": None, "expected_remote_digest": None, "expected_remote_version": None,
             "attempt_sequence": 0, "holds": [], "events": 0, "identity_payloads": {}}
    seen_project_id: str | None = None
    for event in scheduler_events:
        kind, env = _scheduler_event(event); p = _inner(env); state["events"] += 1
        event_pid = str(env["project_id"])
        if seen_project_id is None: seen_project_id = event_pid
        elif event_pid != seen_project_id: raise SchedulerHold("hold_control_plane_unready")
        event_id = _event_identity(kind, event_pid, env); event_digest = _digest(env)
        prior = state["identity_payloads"].get(event_id)
        if prior is not None and prior != event_digest: raise SchedulerHold("hold_duplicate_or_divergent")
        state["identity_payloads"][event_id] = event_digest
        state["control_generation"] = p.get("control_generation", state["control_generation"]); state["control_head"] = p.get("control_head", state["control_head"])
        if kind == "scheduler_initialized":
            if state["scheduler_state"] == "disabled":
                if not all(p.get(k) for k in ("enable_gate_ref", "enable_gate_digest", "enable_gate_authority")): raise SchedulerHold("hold_disabled_enable_gate")
                state["local_state"] = "registered"
            elif state["scheduler_state"] != "not_enabled" or state["events"] != 1:
                raise SchedulerHold("hold_transition_order")
            state["scheduler_state"] = "enabled"
        elif kind == "scheduler_disabled":
            if state["scheduler_state"] != "enabled" or state["local_state"] in {"completed", "canceled", "disabled"}: raise SchedulerHold("hold_terminal_or_disabled")
            state["scheduler_state"] = "disabled"; state["local_state"] = "disabled"
        elif kind == "work_transition_recorded":
            if state["scheduler_state"] != "enabled" or state["local_state"] in {"completed", "canceled", "disabled"} or p.get("from_state") != state["local_state"] or p.get("transition_sequence") != state["transition_sequence"] + 1 or p.get("to_state") not in LOCAL_TRANSITIONS.get(state["local_state"], set()):
                raise SchedulerHold("hold_transition_order")
            if state["local_state"] == "hold" and p.get("to_state") == "queued" and not all(p.get(k) for k in ("resume_receipt_ref", "resume_receipt_digest", "resume_authority")):
                raise SchedulerHold("hold_resume_receipt_required")
            if state["local_state"] == "successor_required" and p.get("to_state") == "active" and not all(p.get(k) for k in ("successor_readiness_ref", "successor_readiness_digest", "successor_id")):
                raise SchedulerHold("hold_successor_readiness_required")
            state["local_state"] = p["to_state"]; state["transition_sequence"] = p["transition_sequence"]
        elif kind == "remote_intent_recorded":
            if state["scheduler_state"] != "enabled" or state["intent_id"] is not None or not p.get("desired_effect_digest"): raise SchedulerHold("hold_transition_order")
            state["intent_id"] = p.get("intent_id"); state["desired_effect_digest"] = p.get("desired_effect_digest"); state["remote_intent_state"] = "accepted_local"; state["attempt_sequence"] = 0
        elif kind in {"remote_materialization_pending", "remote_observation_recorded", "remote_confirmation_recorded", "remote_failure_recorded", "remote_conflict_recorded", "remote_intent_canceled"}:
            retrying = kind == "remote_materialization_pending" and state["remote_intent_state"] in {"failed", "readback_unavailable"}
            if state["intent_id"] is None or p.get("intent_id") != state["intent_id"] or (state["remote_intent_state"] in {"confirmed", "failed", "conflict", "canceled", "privacy_held"} and not retrying):
                raise SchedulerHold("hold_terminal_or_disabled")
            if state["remote_intent_state"] not in REMOTE_PREDECESSORS[kind]:
                raise SchedulerHold("hold_transition_order")
            attempt = p.get("attempt_sequence")
            if not isinstance(attempt, int):
                raise SchedulerHold("hold_transition_order")
            current_attempt = state["attempt_sequence"]
            if kind == "remote_materialization_pending":
                if attempt != current_attempt + 1:
                    raise SchedulerHold("hold_transition_order")
                if state["remote_intent_state"] in {"failed", "readback_unavailable"} and not all(p.get(k) for k in ("retry_receipt_ref", "retry_receipt_digest", "retry_authority")):
                    raise SchedulerHold("hold_retry_receipt_required")
            elif attempt != current_attempt:
                raise SchedulerHold("hold_transition_order")
            if p.get("desired_effect_digest") != state["desired_effect_digest"]: raise SchedulerHold("hold_readback_binding_conflict")
            for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
                if state.get(key) is not None and p.get(key) != state[key]: raise SchedulerHold("hold_readback_binding_conflict")
            state["expected_remote_kind"] = p.get("expected_remote_kind", state["expected_remote_kind"]); state["expected_remote_ref"] = p.get("expected_remote_ref", state["expected_remote_ref"]); state["expected_remote_digest"] = p.get("expected_remote_digest", state["expected_remote_digest"]); state["expected_remote_version"] = p.get("expected_remote_version", state["expected_remote_version"])
            state["attempt_sequence"] = attempt
            next_remote = {"remote_materialization_pending": "pending_materialization", "remote_observation_recorded": "observed_unverified", "remote_confirmation_recorded": "confirmed", "remote_failure_recorded": ("readback_unavailable" if p.get("classification") == "hold_readback_unavailable" else "failed"), "remote_conflict_recorded": "conflict", "remote_intent_canceled": "canceled"}[kind]
            state["remote_intent_state"] = next_remote
        elif kind == "privacy_hold_recorded":
            if state["intent_id"] is None or state["remote_intent_state"] not in REMOTE_PREDECESSORS[kind]:
                raise SchedulerHold("hold_transition_order")
            if p.get("intent_id") != state["intent_id"] or p.get("attempt_sequence") != state["attempt_sequence"]:
                raise SchedulerHold("hold_readback_binding_conflict")
            if p.get("desired_effect_digest") != state["desired_effect_digest"]:
                raise SchedulerHold("hold_readback_binding_conflict")
            for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
                if (state.get(key) is None and p.get(key) is not None) or (state.get(key) is not None and p.get(key) != state[key]):
                    raise SchedulerHold("hold_readback_binding_conflict")
            if p.get("classification") not in FAILURE_CODES: raise SchedulerHold("hold_schema_or_version")
            state["remote_intent_state"] = "privacy_held"; state["local_state"] = "hold"; state["holds"].append(p.get("classification", "hold_privacy"))
    return state


def _snapshot_value_for_reducer(value: Any) -> Any:
    """Detach an immutable LedgerStore value for legacy JSON reducers only."""
    if isinstance(value, Mapping):
        return {key: _snapshot_value_for_reducer(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_snapshot_value_for_reducer(item) for item in value]
    return value


def _snapshot_events_for_reducer(events: Iterable[Any]) -> list[dict[str, Any]]:
    return [{"event_type": event.event_type, "payload": _snapshot_value_for_reducer(event.payload)} for event in events]


def replay_scheduler_state(projects_root: str | Path, project_id: str) -> dict[str, Any]:
    pid = _project(project_id); path = Path(projects_root).expanduser() / pid / "collaboration.db"
    try:
        snapshot = LocalCollaborationLedger.authority_snapshot(path, expected_project_id=pid)
        events = _snapshot_events_for_reducer(snapshot.events)
        cstate = control.reduce_control_events([event for event in events if event["event_type"].startswith("control.")])
        state = reduce_scheduler_state(cstate, [event for event in events if event["event_type"].startswith("scheduler.")])
        state["authority_generation"] = snapshot.authority_generation
        state["authority_head"] = snapshot.authority_head
        return state
    except LedgerBusyError as exc: raise SchedulerHold("hold_ledger_busy") from exc
    except LedgerPermissionError as exc: raise SchedulerHold("hold_ledger_permission") from exc
    except LedgerSchemaError as exc: raise SchedulerHold("hold_ledger_schema") from exc
    except (LedgerIntegrityError, LedgerError, OSError) as exc: raise SchedulerHold("hold_ledger_integrity") from exc


def _request_base(request: Mapping[str, Any], cstate: Mapping[str, Any], sstate: Mapping[str, Any], caller_project_id: str | None = None) -> tuple[str, str]:
    allowed = {"project_id", "operation", "occurred_at", "timestamp_provenance", "work_id", "run_id", "owner_role", "control_generation", "control_head", "durable_anchor_digest", "root_budget_tokens", "remaining_budget_tokens", "from_state", "to_state", "transition_sequence", "intent_id", "intent_kind", "desired_effect", "desired_effect_digest", "human_gate_class", "attempt_sequence", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "adapter_id", "adapter_version", "request_digest", "readback_digest", "observed_remote_state", "opaque_receipt_ref", "classification", "next_action", "explicit_sequence", "adapter", "readback", "resume_receipt_ref", "resume_receipt_digest", "resume_authority", "retry_receipt_ref", "retry_receipt_digest", "retry_authority", "successor_readiness_ref", "successor_readiness_digest", "successor_id", "enable_gate_ref", "enable_gate_digest", "enable_gate_authority", "readback_nonce", "read_timestamp", "remote_version", "nonce"}
    if not isinstance(request, Mapping) or set(request) - allowed:
        raise SchedulerHold("hold_unknown_version_or_state")
    pid = _project(request.get("project_id")); _timestamp(request.get("occurred_at"))
    if caller_project_id is not None and pid != caller_project_id:
        raise SchedulerHold("hold_control_plane_unready")
    if request.get("timestamp_provenance", "explicit") != "explicit": raise SchedulerHold("hold_unknown_version_or_state")
    if not cstate.get("initialized"): raise SchedulerHold("hold_control_plane_unready")
    work = cstate.get("work") or {}
    if request.get("work_id", work.get("work_id")) != work.get("work_id") or request.get("owner_role", work.get("role")) != work.get("role"):
        raise SchedulerHold("hold_missing_work_root_owner")
    return pid, work.get("work_id")


def _binding_payload(request: Mapping[str, Any], cstate: Mapping[str, Any], sstate: Mapping[str, Any]) -> dict[str, Any]:
    work = cstate["work"]
    expected = {"control_generation": request.get("control_generation", sstate.get("control_generation")), "control_head": request.get("control_head", sstate.get("control_head")), "durable_anchor_digest": request.get("durable_anchor_digest", work.get("durable_anchor_digest")), "budget_digest": _digest([work.get("root_budget_tokens"), work.get("remaining_budget_tokens")])}
    for key in ("control_generation", "control_head", "durable_anchor_digest"):
        if request.get(key) is not None and sstate.get(key) is not None and request[key] != sstate[key]: raise SchedulerHold("hold_stale_ledger_head" if key != "durable_anchor_digest" else "hold_anchor_or_budget_conflict")
    return expected


def plan_scheduler_request(request: Mapping[str, Any], control_state: Mapping[str, Any], scheduler_state: Mapping[str, Any] | None = None, caller_project_id: str | None = None) -> dict[str, Any]:
    sstate = scheduler_state or reduce_scheduler_state(control_state, [])
    pid, work_id = _request_base(request, control_state, sstate, caller_project_id); op = request.get("operation")
    if not isinstance(op, str): raise SchedulerHold("hold_unknown_version_or_state")
    if sstate.get("scheduler_state") == "disabled" and op != "enable": raise SchedulerHold("hold_terminal_or_disabled")
    if op == "enable":
        if sstate.get("scheduler_state") != "disabled": raise SchedulerHold("hold_transition_order")
        if not all(isinstance(request.get(k), str) and request.get(k) for k in ("enable_gate_ref", "enable_gate_digest", "enable_gate_authority")):
            raise SchedulerHold("hold_disabled_enable_gate")
    base = _binding_payload(request, control_state, sstate); occurred = request["occurred_at"]; events: list[dict[str, Any]] = []
    if op in {"initialize", "enable"}:
        if op == "initialize" and sstate.get("scheduler_state") == "disabled":
            raise SchedulerHold("hold_terminal_or_disabled")
        init_payload = {"work_id": work_id, **base}
        if op == "enable": init_payload.update({"enable_gate_ref": request["enable_gate_ref"], "enable_gate_digest": request["enable_gate_digest"], "enable_gate_authority": request["enable_gate_authority"]})
        candidate = _event(pid, "scheduler_initialized", init_payload, occurred)
        prior = sstate.get("identity_payloads", {}).get(candidate["event_id"])
        if prior is not None:
            if prior != _digest(candidate["payload"]): raise SchedulerHold("hold_duplicate_or_divergent")
            return {"decision": "duplicate", "event_batch": [], "mutation_performed": False, "project_id": pid}
        events.append(candidate)
    elif op == "disable":
        if sstate["scheduler_state"] == "disabled": return {"decision": "duplicate", "event_batch": [], "mutation_performed": False, "project_id": pid}
        events.append(_event(pid, "scheduler_disabled", {"work_id": work_id, **base, "classification": "disabled", "next_action": "human_review"}, occurred))
    elif op == "transition":
        if sstate["scheduler_state"] != "enabled": raise SchedulerHold("hold_scheduler_not_enabled")
        from_state, to_state = request.get("from_state"), request.get("to_state"); seq = request.get("transition_sequence")
        # Check the stable sequence identity before state validation so an
        # exact retry after a fresh process is a duplicate, not an out-of-order
        # transition.  A changed payload at that identity is a conflict hold.
        if isinstance(seq, int):
            candidate_payload = {"work_id": work_id, "run_id": request.get("run_id"), "owner_role": control_state["work"].get("role"), **base, "transition_sequence": seq, "from_state": from_state, "to_state": to_state, "next_action": request.get("next_action", "")}
            for key in ("resume_receipt_ref", "resume_receipt_digest", "resume_authority", "successor_readiness_ref", "successor_readiness_digest", "successor_id"):
                if request.get(key) is not None: candidate_payload[key] = request[key]
            candidate = _event(pid, "work_transition_recorded", candidate_payload, occurred)
            prior = sstate.get("identity_payloads", {}).get(candidate["event_id"])
            if prior is not None:
                if prior != _digest(candidate["payload"]): raise SchedulerHold("hold_duplicate_or_divergent")
                return {"decision": "duplicate", "event_batch": [], "mutation_performed": False, "project_id": pid}
        if from_state != sstate["local_state"] or from_state not in LOCAL_STATES or to_state not in LOCAL_STATES: raise SchedulerHold("hold_transition_order")
        if to_state not in LOCAL_TRANSITIONS.get(from_state, set()): raise SchedulerHold("hold_transition_order")
        if not isinstance(seq, int) or seq != sstate["transition_sequence"] + 1: raise SchedulerHold("hold_transition_order")
        transition_payload = {"work_id": work_id, "run_id": request.get("run_id"), "owner_role": control_state["work"].get("role"), **base, "transition_sequence": seq, "from_state": from_state, "to_state": to_state, "next_action": request.get("next_action", "")}
        if from_state == "hold" and to_state == "queued":
            if not all(isinstance(request.get(k), str) and request.get(k) for k in ("resume_receipt_ref", "resume_receipt_digest", "resume_authority")):
                raise SchedulerHold("hold_resume_receipt_required")
            transition_payload.update({"resume_receipt_ref": request["resume_receipt_ref"], "resume_receipt_digest": request["resume_receipt_digest"], "resume_authority": request["resume_authority"]})
        if from_state == "successor_required" and to_state == "active":
            if not all(isinstance(request.get(k), str) and request.get(k) for k in ("successor_readiness_ref", "successor_readiness_digest", "successor_id")):
                raise SchedulerHold("hold_successor_readiness_required")
            transition_payload.update({"successor_readiness_ref": request["successor_readiness_ref"], "successor_readiness_digest": request["successor_readiness_digest"], "successor_id": request["successor_id"]})
        events.append(_event(pid, "work_transition_recorded", transition_payload, occurred))
    elif op in {"intent", "request_remote"}:
        if sstate["scheduler_state"] != "enabled": raise SchedulerHold("hold_scheduler_not_enabled")
        iid = request.get("intent_id") or str(uuid.uuid4())
        try: uuid.UUID(str(iid))
        except (ValueError, TypeError): raise SchedulerHold("hold_unknown_version_or_state")
        effect = request.get("desired_effect_digest") or _digest(request.get("desired_effect", {})); events.append(_event(pid, "remote_intent_recorded", {"work_id": work_id, **base, "intent_id": iid, "intent_kind": request.get("intent_kind"), "desired_effect_digest": effect, "human_gate_class": request.get("human_gate_class", "none"), "next_action": "materialize_when_adapter_available"}, occurred))
    elif op == "pending":
        if not sstate.get("intent_id"): raise SchedulerHold("hold_missing_work_root_owner")
        if sstate.get("remote_intent_state") not in REMOTE_PREDECESSORS["remote_materialization_pending"]:
            raise SchedulerHold("hold_transition_order")
        previous = sstate.get("remote_intent_state")
        attempt = request.get("attempt_sequence", sstate.get("attempt_sequence", 0) + 1)
        if attempt != sstate.get("attempt_sequence", 0) + 1:
            raise SchedulerHold("hold_transition_order")
        retry_payload = {}
        if previous in {"failed", "readback_unavailable"}:
            if not all(isinstance(request.get(k), str) and request.get(k) for k in ("retry_receipt_ref", "retry_receipt_digest", "retry_authority")):
                raise SchedulerHold("hold_retry_receipt_required")
            retry_payload = {k: request[k] for k in ("retry_receipt_ref", "retry_receipt_digest", "retry_authority")}
        events.append(_event(pid, "remote_materialization_pending", {"work_id": work_id, **base, **retry_payload, "intent_id": sstate["intent_id"], "desired_effect_digest": sstate.get("desired_effect_digest"), "attempt_sequence": attempt, "expected_remote_kind": request.get("expected_remote_kind"), "expected_remote_ref": request.get("expected_remote_ref"), "expected_remote_digest": request.get("expected_remote_digest"), "expected_remote_version": request.get("expected_remote_version"), "next_action": "adapter_readback"}, occurred))
    elif op in {"observe", "remote_observation"}:
        if request.get("observed_remote_state") is None: raise SchedulerHold("hold_readback_unavailable")
        if sstate.get("remote_intent_state") not in REMOTE_PREDECESSORS["remote_observation_recorded"]:
            raise SchedulerHold("hold_transition_order")
        attempt = request.get("attempt_sequence", sstate.get("attempt_sequence", 0))
        if attempt != sstate.get("attempt_sequence", 0):
            raise SchedulerHold("hold_transition_order")
        events.append(_event(pid, "remote_observation_recorded", {"work_id": work_id, **base, "intent_id": request.get("intent_id", sstate.get("intent_id")), "desired_effect_digest": sstate.get("desired_effect_digest"), "attempt_sequence": request.get("attempt_sequence", sstate.get("attempt_sequence", 0)), "expected_remote_kind": request.get("expected_remote_kind", sstate.get("expected_remote_kind")), "expected_remote_ref": request.get("expected_remote_ref", sstate.get("expected_remote_ref")), "expected_remote_digest": request.get("expected_remote_digest", sstate.get("expected_remote_digest")), "expected_remote_version": request.get("expected_remote_version", sstate.get("expected_remote_version")), "observed_remote_state": request.get("observed_remote_state"), "classification": "observed_unverified", "next_action": "trusted_adapter_readback"}, occurred))
    elif op in {"cancel", "privacy_hold", "failure", "conflict"}:
        if op == "privacy_hold": kind, cls = "privacy_hold_recorded", "hold_privacy"
        elif op == "cancel": kind, cls = "remote_intent_canceled", "canceled"
        elif op == "failure": kind, cls = "remote_failure_recorded", request.get("classification", "hold_readback_unavailable")
        else: kind, cls = "remote_conflict_recorded", "hold_readback_binding_conflict"
        if cls not in FAILURE_CODES and op != "cancel": raise SchedulerHold("hold_unknown_version_or_state")
        if sstate.get("remote_intent_state") not in REMOTE_PREDECESSORS[kind]:
            raise SchedulerHold("hold_transition_order")
        attempt = request.get("attempt_sequence", sstate.get("attempt_sequence", 0))
        if attempt != sstate.get("attempt_sequence", 0): raise SchedulerHold("hold_transition_order")
        events.append(_event(pid, kind, {"work_id": work_id, **base, "intent_id": request.get("intent_id", sstate.get("intent_id")), "desired_effect_digest": sstate.get("desired_effect_digest"), "attempt_sequence": attempt, "expected_remote_kind": request.get("expected_remote_kind", sstate.get("expected_remote_kind")), "expected_remote_ref": request.get("expected_remote_ref", sstate.get("expected_remote_ref")), "expected_remote_digest": request.get("expected_remote_digest", sstate.get("expected_remote_digest")), "expected_remote_version": request.get("expected_remote_version", sstate.get("expected_remote_version")), "classification": cls, "next_action": request.get("next_action", "human_review")}, occurred))
    else: raise SchedulerHold("hold_unknown_version_or_state")
    return {"project_id": pid, "decision": "allow", "event_batch": events, "mutation_performed": False, "dispatch_performed": False}


def apply_scheduler_request(projects_root: str | Path, project_id: str, request: Mapping[str, Any]) -> dict[str, Any]:
    pid = _project(project_id); path = Path(projects_root).expanduser() / pid / "collaboration.db"
    if not isinstance(request, Mapping) or _project(request.get("project_id")) != pid:
        raise SchedulerHold("hold_control_plane_unready")
    ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
    try:
        before = ledger.list_events(); cstate = control.reduce_control_events([e for e in before if e.event_type.startswith("control.")]); sstate = reduce_scheduler_state(cstate, [e for e in before if e.event_type.startswith("scheduler.")]); result = plan_scheduler_request(request, cstate, sstate, caller_project_id=pid); batch = result["event_batch"]
        if not batch:
            result["replay"] = replay_scheduler_state(projects_root, pid)
            return result
        # Recheck the source head immediately before the atomic LedgerStore append.
        current = ledger.list_events();
        if len(current) != len(before) or (current and before and current[-1].event_hash != before[-1].event_hash): raise SchedulerHold("hold_stale_ledger_head")
        # Validate the complete candidate batch against the current replay
        # before writing.  A malformed or out-of-order event must not leave a
        # durable hold or partial append behind when the reducer rejects it.
        reduce_scheduler_state(cstate, [e for e in before if e.event_type.startswith("scheduler.")] + batch)
        rows = ledger.append_batch(batch); after = ledger.list_events(); result["mutation_performed"] = len(after) > len(before); result["appended_count"] = len(after) - len(before); result["duplicate_count"] = len(batch) - result["appended_count"]; result["generation"] = len(after); result["replay"] = replay_scheduler_state(projects_root, pid); return result
    except SchedulerHold: raise
    except LedgerBusyError as exc: raise SchedulerHold("hold_ledger_busy") from exc
    except LedgerPermissionError as exc: raise SchedulerHold("hold_ledger_permission") from exc
    except LedgerSchemaError as exc: raise SchedulerHold("hold_ledger_schema") from exc
    except (LedgerIntegrityError, LedgerError, OSError) as exc: raise SchedulerHold("hold_ledger_integrity") from exc
    finally: ledger.close()


def _validate_readback_request(request: Any, pid: str, intent_id: str, sstate: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping) or set(request) - READBACK_REQUEST_KEYS:
        raise SchedulerHold("hold_readback_binding_conflict")
    required = {"project_id", "work_id", "operation", "intent_id", "attempt_sequence", "request_digest", "occurred_at",
        "desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"}
    if not required.issubset(request) or _project(request.get("project_id")) != pid:
        raise SchedulerHold("hold_readback_binding_conflict")
    if request.get("operation") not in {"confirm", "readback"} or request.get("intent_id") != intent_id:
        raise SchedulerHold("hold_readback_binding_conflict")
    if request.get("work_id") != sstate.get("work_id") or request.get("attempt_sequence") != sstate.get("attempt_sequence"):
        raise SchedulerHold("hold_readback_binding_conflict")
    _timestamp(request.get("occurred_at"))
    if not isinstance(request.get("request_digest"), str) or not re.fullmatch(r"[0-9a-f]{64}", request["request_digest"]):
        raise SchedulerHold("hold_readback_binding_conflict")
    for key in ("desired_effect_digest", "expected_remote_digest"):
        if not isinstance(request.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", request[key]):
            raise SchedulerHold("hold_readback_binding_conflict")
    for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_version"):
        if not isinstance(request.get(key), str) or not request[key]:
            raise SchedulerHold("hold_readback_binding_conflict")
    for key in ("desired_effect_digest", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
        if request[key] != sstate.get(key):
            raise SchedulerHold("hold_readback_binding_conflict")


def _validate_readback_response(response: Any, request: Mapping[str, Any], pid: str, intent_id: str, sstate: Mapping[str, Any]) -> None:
    """Validate a hermetic readback result without granting it authority."""
    if not isinstance(response, Mapping) or set(response) != READBACK_RESPONSE_KEYS:
        raise SchedulerHold("hold_schema_or_version")
    _walk(response)
    required_strings = ("schema_version", "operation", "outcome", "classification", "idempotency_key",
        "readback_digest", "opaque_receipt_ref", "adapter_id", "adapter_version", "expected_remote_kind",
        "expected_remote_ref", "expected_remote_digest", "expected_remote_version", "desired_effect_digest",
        "request_digest", "occurred_at", "read_timestamp", "readback_nonce")
    if any(not isinstance(response.get(key), str) or not response[key] for key in required_strings):
        raise SchedulerHold("hold_schema_or_version")
    if response.get("schema_version") != "GitHubMaterializationAdapter-v1" or response.get("outcome") != "materialization_readback_verified":
        raise SchedulerHold("hold_schema_or_version")
    if any(response.get(key) is not value for key, value in {
        "simulation_only": True, "remote_mutation_performed": False, "authoritative": False,
        "confirmation_eligible": False, "confirmed": True}.items()):
        raise SchedulerHold("hold_untrusted_readback")
    if response.get("project_id") != pid or response.get("intent_id") != intent_id or response.get("attempt_sequence") != sstate.get("attempt_sequence"):
        raise SchedulerHold("hold_readback_binding_conflict")
    for key in ("readback_digest", "expected_remote_digest", "desired_effect_digest", "request_digest"):
        if not re.fullmatch(r"[0-9a-f]{64}", response[key]):
            raise SchedulerHold("hold_schema_or_version")
    _timestamp(response["occurred_at"]); _timestamp(response["read_timestamp"])
    if response["request_digest"] != request["request_digest"] or response["desired_effect_digest"] != sstate.get("desired_effect_digest"):
        raise SchedulerHold("hold_readback_binding_conflict")
    for key in ("expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "expected_remote_version"):
        if response[key] != sstate.get(key):
            raise SchedulerHold("hold_readback_binding_conflict")


def apply_remote_readback(projects_root: str | Path, project_id: str, intent_id: str, adapter: Any, request: Mapping[str, Any]) -> dict[str, Any]:
    if not hasattr(adapter, "readback") or not callable(adapter.readback): raise SchedulerHold("hold_untrusted_readback")
    pid = _project(project_id)
    path = Path(projects_root).expanduser() / pid / "collaboration.db"
    ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
    try:
        all_events = ledger.list_events(); cstate = control.reduce_control_events([e for e in all_events if e.event_type.startswith("control.")]); sstate = reduce_scheduler_state(cstate, [e for e in all_events if e.event_type.startswith("scheduler.")]);
        if sstate.get("intent_id") != intent_id or sstate.get("remote_intent_state") not in REMOTE_PREDECESSORS["remote_confirmation_recorded"]: raise SchedulerHold("hold_readback_binding_conflict")
        _validate_readback_request(request, pid, intent_id, sstate)
        response = adapter.readback(dict(request))
        _validate_readback_response(response, request, pid, intent_id, sstate)
        # This is the complete current trust decision.  The adapter is a
        # same-process hermetic simulation and cannot authorize an authority
        # transition, even if it self-attests to stronger properties.
        raise SchedulerHold("hold_untrusted_readback")
    except SchedulerHold: raise
    except Exception as exc: raise SchedulerHold("hold_readback_unavailable") from exc
    finally: ledger.close()


def project_work_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    return {k: state.get(k) for k in ("work_id", "owner_role", "local_state", "remote_intent_state", "root_budget_tokens", "remaining_budget_tokens", "holds")}


def project_attention_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    attention = list(state.get("holds", [])); remote = state.get("remote_intent_state")
    if remote in {"failed", "conflict", "privacy_held", "readback_unavailable"}: attention.append("remote_" + remote)
    if state.get("local_state") in {"hold", "successor_required", "disabled"}: attention.append("local_" + str(state["local_state"]))
    return {"work_id": state.get("work_id"), "attention": sorted(set(attention)), "next_action": "human_review" if attention else "none"}
