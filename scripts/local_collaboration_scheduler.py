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
    "hold_readback_binding_conflict", "hold_readback_unavailable", "hold_privacy", "hold_ledger_busy",
    "hold_ledger_integrity", "hold_ledger_permission", "hold_ledger_schema"}


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


def _event_identity(kind: str, pid: str, payload: Mapping[str, Any]) -> str:
    p = _inner(payload)
    if kind == "scheduler_initialized": identity = f"init|{pid}"
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
    _walk(envelope["payload"])
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
             "transition_sequence": 0, "intent_id": None, "attempt_sequence": 0, "holds": [], "events": 0, "identity_payloads": {}}
    for event in scheduler_events:
        kind, env = _scheduler_event(event); p = _inner(env); state["events"] += 1
        state["identity_payloads"][_event_identity(kind, str(env["project_id"]), env)] = _digest(env)
        state["control_generation"] = p.get("control_generation", state["control_generation"]); state["control_head"] = p.get("control_head", state["control_head"])
        if kind == "scheduler_initialized": state["scheduler_state"] = "enabled"
        elif kind == "scheduler_disabled": state["scheduler_state"] = "disabled"; state["local_state"] = "disabled"
        elif kind == "work_transition_recorded":
            state["local_state"] = p.get("to_state", "hold"); state["transition_sequence"] = p.get("transition_sequence", state["transition_sequence"])
        elif kind == "remote_intent_recorded": state["intent_id"] = p.get("intent_id"); state["remote_intent_state"] = "accepted_local"; state["attempt_sequence"] = 0
        elif kind == "remote_materialization_pending": state["remote_intent_state"] = "pending_materialization"; state["attempt_sequence"] = p.get("attempt_sequence", state["attempt_sequence"])
        elif kind == "remote_observation_recorded": state["remote_intent_state"] = "observed_unverified"; state["attempt_sequence"] = p.get("attempt_sequence", state["attempt_sequence"])
        elif kind == "remote_confirmation_recorded": state["remote_intent_state"] = "confirmed"; state["attempt_sequence"] = p.get("attempt_sequence", state["attempt_sequence"])
        elif kind == "remote_failure_recorded": state["remote_intent_state"] = "failed"; state["attempt_sequence"] = p.get("attempt_sequence", state["attempt_sequence"])
        elif kind == "remote_conflict_recorded": state["remote_intent_state"] = "conflict"; state["attempt_sequence"] = p.get("attempt_sequence", state["attempt_sequence"])
        elif kind == "remote_intent_canceled": state["remote_intent_state"] = "canceled"; state["attempt_sequence"] = p.get("attempt_sequence", state["attempt_sequence"])
        elif kind == "privacy_hold_recorded": state["remote_intent_state"] = "privacy_held"; state["local_state"] = "hold"; state["holds"].append(p.get("classification", "hold_privacy"))
    return state


def _control_events(ledger: LocalCollaborationLedger) -> list[Any]:
    return [e for e in ledger.list_events() if e.event_type.startswith("control.")]


def _scheduler_events(ledger: LocalCollaborationLedger) -> list[Any]:
    return [e for e in ledger.list_events() if e.event_type.startswith("scheduler.")]


def replay_scheduler_state(projects_root: str | Path, project_id: str) -> dict[str, Any]:
    pid = _project(project_id); path = Path(projects_root).expanduser() / pid / "collaboration.db"
    ledger = LocalCollaborationLedger(db_path=path, create=False)
    try:
        if ledger.project_id != pid: raise SchedulerHold("hold_control_plane_unready")
        cstate = control.reduce_control_events(_control_events(ledger)); return reduce_scheduler_state(cstate, _scheduler_events(ledger))
    finally: ledger.close()


def _request_base(request: Mapping[str, Any], cstate: Mapping[str, Any], sstate: Mapping[str, Any]) -> tuple[str, str]:
    if not isinstance(request, Mapping) or set(request) - {"project_id", "operation", "occurred_at", "timestamp_provenance", "work_id", "run_id", "owner_role", "control_generation", "control_head", "durable_anchor_digest", "root_budget_tokens", "remaining_budget_tokens", "from_state", "to_state", "transition_sequence", "intent_id", "intent_kind", "desired_effect", "desired_effect_digest", "human_gate_class", "attempt_sequence", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "adapter_id", "adapter_version", "request_digest", "readback_digest", "observed_remote_state", "opaque_receipt_ref", "classification", "next_action", "explicit_sequence", "adapter", "readback"}:
        raise SchedulerHold("hold_unknown_version_or_state")
    pid = _project(request.get("project_id")); _timestamp(request.get("occurred_at"))
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


def plan_scheduler_request(request: Mapping[str, Any], control_state: Mapping[str, Any], scheduler_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    sstate = scheduler_state or reduce_scheduler_state(control_state, [])
    pid, work_id = _request_base(request, control_state, sstate); op = request.get("operation")
    if not isinstance(op, str): raise SchedulerHold("hold_unknown_version_or_state")
    if sstate.get("scheduler_state") == "disabled" and op != "enable": raise SchedulerHold("hold_terminal_or_disabled")
    base = _binding_payload(request, control_state, sstate); occurred = request["occurred_at"]; events: list[dict[str, Any]] = []
    if op in {"initialize", "enable"}:
        candidate = _event(pid, "scheduler_initialized", {"work_id": work_id, **base}, occurred)
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
            candidate = _event(pid, "work_transition_recorded", candidate_payload, occurred)
            prior = sstate.get("identity_payloads", {}).get(candidate["event_id"])
            if prior is not None:
                if prior != _digest(candidate["payload"]): raise SchedulerHold("hold_duplicate_or_divergent")
                return {"decision": "duplicate", "event_batch": [], "mutation_performed": False, "project_id": pid}
        if from_state != sstate["local_state"] or from_state not in LOCAL_STATES or to_state not in LOCAL_STATES: raise SchedulerHold("hold_transition_order")
        if to_state not in LOCAL_TRANSITIONS.get(from_state, set()): raise SchedulerHold("hold_transition_order")
        if not isinstance(seq, int) or seq != sstate["transition_sequence"] + 1: raise SchedulerHold("hold_transition_order")
        events.append(_event(pid, "work_transition_recorded", {"work_id": work_id, "run_id": request.get("run_id"), "owner_role": control_state["work"].get("role"), **base, "transition_sequence": seq, "from_state": from_state, "to_state": to_state, "next_action": request.get("next_action", "")}, occurred))
    elif op in {"intent", "request_remote"}:
        if sstate["scheduler_state"] != "enabled": raise SchedulerHold("hold_scheduler_not_enabled")
        iid = request.get("intent_id") or str(uuid.uuid4())
        try: uuid.UUID(str(iid))
        except (ValueError, TypeError): raise SchedulerHold("hold_unknown_version_or_state")
        effect = request.get("desired_effect_digest") or _digest(request.get("desired_effect", {})); events.append(_event(pid, "remote_intent_recorded", {"work_id": work_id, **base, "intent_id": iid, "intent_kind": request.get("intent_kind"), "desired_effect_digest": effect, "human_gate_class": request.get("human_gate_class", "none"), "next_action": "materialize_when_adapter_available"}, occurred))
    elif op == "pending":
        if not sstate.get("intent_id"): raise SchedulerHold("hold_missing_work_root_owner")
        events.append(_event(pid, "remote_materialization_pending", {"work_id": work_id, **base, "intent_id": sstate["intent_id"], "attempt_sequence": request.get("attempt_sequence", 1), "expected_remote_kind": request.get("expected_remote_kind"), "expected_remote_ref": request.get("expected_remote_ref"), "expected_remote_digest": request.get("expected_remote_digest"), "next_action": "adapter_readback"}, occurred))
    elif op in {"observe", "remote_observation"}:
        if request.get("observed_remote_state") is None: raise SchedulerHold("hold_readback_unavailable")
        events.append(_event(pid, "remote_observation_recorded", {"work_id": work_id, **base, "intent_id": request.get("intent_id", sstate.get("intent_id")), "attempt_sequence": request.get("attempt_sequence", 1), "observed_remote_state": request.get("observed_remote_state"), "classification": "observed_unverified", "next_action": "trusted_adapter_readback"}, occurred))
    elif op in {"cancel", "privacy_hold", "failure", "conflict"}:
        if op == "privacy_hold": kind, cls = "privacy_hold_recorded", "hold_privacy"
        elif op == "cancel": kind, cls = "remote_intent_canceled", "canceled"
        elif op == "failure": kind, cls = "remote_failure_recorded", request.get("classification", "hold_readback_unavailable")
        else: kind, cls = "remote_conflict_recorded", "hold_readback_binding_conflict"
        if cls not in FAILURE_CODES and op != "cancel": raise SchedulerHold("hold_unknown_version_or_state")
        events.append(_event(pid, kind, {"work_id": work_id, **base, "intent_id": request.get("intent_id", sstate.get("intent_id")), "attempt_sequence": request.get("attempt_sequence", 1), "classification": cls, "next_action": request.get("next_action", "human_review")}, occurred))
    else: raise SchedulerHold("hold_unknown_version_or_state")
    return {"project_id": pid, "decision": "allow", "event_batch": events, "mutation_performed": False, "dispatch_performed": False}


def apply_scheduler_request(projects_root: str | Path, project_id: str, request: Mapping[str, Any]) -> dict[str, Any]:
    pid = _project(project_id); path = Path(projects_root).expanduser() / pid / "collaboration.db"
    ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
    try:
        before = ledger.list_events(); cstate = control.reduce_control_events([e for e in before if e.event_type.startswith("control.")]); sstate = reduce_scheduler_state(cstate, [e for e in before if e.event_type.startswith("scheduler.")]); result = plan_scheduler_request(request, cstate, sstate); batch = result["event_batch"]
        if not batch: result["replay"] = sstate; return result
        # Recheck the source head immediately before the atomic LedgerStore append.
        current = ledger.list_events();
        if len(current) != len(before) or (current and before and current[-1].event_hash != before[-1].event_hash): raise SchedulerHold("hold_stale_ledger_head")
        rows = ledger.append_batch(batch); after = ledger.list_events(); result["mutation_performed"] = len(after) > len(before); result["appended_count"] = len(after) - len(before); result["duplicate_count"] = len(batch) - result["appended_count"]; result["generation"] = len(after); result["replay"] = reduce_scheduler_state(cstate, [e for e in after if e.event_type.startswith("scheduler.")]); return result
    except SchedulerHold: raise
    except LedgerBusyError as exc: raise SchedulerHold("hold_ledger_busy") from exc
    except LedgerPermissionError as exc: raise SchedulerHold("hold_ledger_permission") from exc
    except LedgerSchemaError as exc: raise SchedulerHold("hold_ledger_schema") from exc
    except (LedgerIntegrityError, LedgerError, OSError) as exc: raise SchedulerHold("hold_ledger_integrity") from exc
    finally: ledger.close()


def apply_remote_readback(projects_root: str | Path, project_id: str, intent_id: str, adapter: Any, request: Mapping[str, Any]) -> dict[str, Any]:
    if not hasattr(adapter, "readback") or not callable(adapter.readback): raise SchedulerHold("hold_untrusted_readback")
    if not isinstance(request, Mapping) or request.get("intent_id", intent_id) != intent_id or request.get("operation") not in {"confirm", "readback"}: raise SchedulerHold("hold_untrusted_readback")
    pid = _project(project_id); path = Path(projects_root).expanduser() / pid / "collaboration.db"
    ledger = LocalCollaborationLedger(db_path=path, create=False)
    try:
        all_events = ledger.list_events(); cstate = control.reduce_control_events([e for e in all_events if e.event_type.startswith("control.")]); sstate = reduce_scheduler_state(cstate, [e for e in all_events if e.event_type.startswith("scheduler.")]);
        if sstate.get("intent_id") != intent_id or sstate.get("remote_intent_state") not in {"accepted_local", "pending_materialization", "observed_unverified", "readback_unavailable"}: raise SchedulerHold("hold_readback_binding_conflict")
        response = adapter.readback(dict(request))
        if not isinstance(response, Mapping) or response.get("project_id") != pid or response.get("intent_id") != intent_id or response.get("confirmed") is not True: raise SchedulerHold("hold_untrusted_readback")
        required = ("adapter_id", "adapter_version", "expected_remote_kind", "expected_remote_ref", "expected_remote_digest", "readback_digest", "opaque_receipt_ref", "occurred_at")
        if any(not response.get(k) for k in required): raise SchedulerHold("hold_readback_binding_conflict")
        payload = {"work_id": sstate["work_id"], "intent_id": intent_id, "attempt_sequence": int(request.get("attempt_sequence", sstate.get("attempt_sequence", 0) + 1)), "expected_remote_kind": response["expected_remote_kind"], "expected_remote_ref": response["expected_remote_ref"], "expected_remote_digest": response["expected_remote_digest"], "adapter_id": response["adapter_id"], "adapter_version": response["adapter_version"], "readback_digest": response["readback_digest"], "opaque_receipt_ref": response["opaque_receipt_ref"], "classification": "confirmed", "next_action": "none"}
        event = _event(pid, "remote_confirmation_recorded", payload, _timestamp(response["occurred_at"]))
        before = ledger.list_events(); before_head = before[-1].event_hash if before else None
        ledger.close(); ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
        current = ledger.list_events()
        if len(current) != len(before) or (current and current[-1].event_hash != before_head):
            raise SchedulerHold("hold_stale_ledger_head")
        ledger.append_batch([event]); after = ledger.list_events(); return {"decision": "confirmed", "project_id": pid, "mutation_performed": len(after) > len(before), "appended_count": len(after) - len(before), "replay": replay_scheduler_state(projects_root, pid)}
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
