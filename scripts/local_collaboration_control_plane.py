"""Portable AF18 control-plane bridge over an existing SQLite LedgerStore."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from local_collaboration_ledger import (LedgerBusyError, LedgerConflictError,
    LedgerError, LedgerIdentityError, LedgerIntegrityError, LedgerPermissionError,
    LedgerSchemaError, LocalCollaborationLedger, GENESIS)

VERSION = "LocalCollaborationControlPlane-v1"
NAMESPACE = uuid.UUID("9a34d5a8-5f23-4e63-9bd7-0a6c4777f3b2")
KINDS = {"control_plane_initialized", "work_registered", "execution_run_registered",
         "dispatch_claim_registered", "transition_recorded", "control_hold_recorded",
         "control_disabled", "logical_successor_recorded", "work_summary_recorded",
         "attention_summary_recorded", "terminal_handoff_recorded"}
PROVENANCE = {"explicit", "estimated", "unavailable", "not_exposed"}
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output", "secret", "native_history", "native_thread_id"}
_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
_ENVELOPE_KEYS = {"version", "project_id", "kind", "occurred_at", "timestamp_provenance", "payload"}
_PAYLOAD_KEYS = {"operation", "work_id", "role", "root_budget_tokens", "remaining_budget_tokens",
                 "issue_anchor_digest", "durable_anchor_digest", "run_id", "state",
                 "decision_boundary", "transition_semantics", "hold_codes"}

class ControlPlaneError(ValueError): pass
class ControlPlaneHold(ControlPlaneError): pass

def _json(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def _walk(v: Any, depth=0) -> None:
    if depth > 12: raise ControlPlaneError("hold_schema_or_version")
    if isinstance(v, Mapping):
        for k, x in v.items():
            if not isinstance(k, str) or k.lower() in FORBIDDEN: raise ControlPlaneError("hold_privacy")
            _walk(x, depth + 1)
    elif isinstance(v, (list, tuple)):
        for x in v: _walk(x, depth + 1)
    elif isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        raise ControlPlaneError("hold_schema_or_version")

def _timestamp(v: Any) -> str:
    if not isinstance(v, str) or not _RFC3339.fullmatch(v): raise ControlPlaneError("hold_schema_or_version")
    try: dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc: raise ControlPlaneError("hold_schema_or_version") from exc
    return v

def _project(v: Any) -> str:
    try: return str(uuid.UUID(str(v)))
    except (ValueError, TypeError, AttributeError) as exc: raise ControlPlaneError("hold_project_identity") from exc

def _digest(v: Any) -> str: return hashlib.sha256(_json(v).encode()).hexdigest()

def _event_id(project_id: str, identity: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{VERSION}|{project_id}|{identity}"))

def _inner(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("payload")
    return value if isinstance(value, Mapping) else payload

def _identity(kind: str, project_id: str, payload: Mapping[str, Any]) -> str:
    payload = _inner(payload)
    work = payload.get("work_id", "none"); run = payload.get("run_id", "none")
    if kind == "control_plane_initialized": return f"init|{project_id}"
    if kind == "work_registered": return f"work|{work}"
    if kind == "execution_run_registered": return f"run|{work}|{run}"
    if kind == "dispatch_claim_registered": return f"claim|{work}|{payload.get('decision_boundary')}|{payload.get('transition_semantics')}"
    return f"{kind}|{work}|{run}|{payload.get('explicit_sequence', payload.get('sequence', 0))}"

def _payload_base(project_id: str, kind: str, payload: Mapping[str, Any], occurred_at: str, provenance: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping): raise ControlPlaneError("hold_schema_or_version")
    _walk(payload)
    if provenance not in PROVENANCE: raise ControlPlaneError("hold_schema_or_version")
    if provenance in {"unavailable", "not_exposed"} and any(k in payload for k in ("value", "tokens", "observed_value", "numeric_value")): raise ControlPlaneError("hold_untrusted_observation")
    return {"version": VERSION, "project_id": project_id, "kind": kind,
            "occurred_at": occurred_at, "timestamp_provenance": provenance,
            "payload": dict(payload)}

def _validate_envelope(envelope: Any) -> Mapping[str, Any]:
    if not isinstance(envelope, Mapping) or set(envelope) != _ENVELOPE_KEYS:
        raise ControlPlaneHold("hold_schema_or_version")
    if envelope.get("version") != VERSION or envelope.get("kind") not in KINDS:
        raise ControlPlaneHold("hold_schema_or_version")
    _project(envelope.get("project_id")); _timestamp(envelope.get("occurred_at"))
    if envelope.get("timestamp_provenance") not in PROVENANCE or not isinstance(envelope.get("payload"), Mapping):
        raise ControlPlaneHold("hold_schema_or_version")
    if set(envelope["payload"]) - _PAYLOAD_KEYS:
        raise ControlPlaneHold("hold_schema_or_version")
    _walk(envelope["payload"])
    return envelope

def _packet(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping): raise ControlPlaneError("hold_schema_or_version")
    if any(k in request for k in ("existing_dispatch_claims", "active_runs", "approved_plan", "trusted_observations", "prior_receipts")): raise ControlPlaneError("hold_untrusted_observation")
    allowed = {"project_id", "work", "execution_run", "dispatch_claim", "requested_route", "occurred_at", "timestamp_provenance", "operation"}
    if set(request) - allowed: raise ControlPlaneError("hold_schema_or_version")
    for name in ("work", "execution_run", "dispatch_claim"):
        if not isinstance(request.get(name), Mapping): raise ControlPlaneError("hold_missing_root_or_owner")
    work = request["work"]
    if not work.get("work_id") or not work.get("role") or not isinstance(work.get("root_budget_tokens"), int) or not isinstance(work.get("remaining_budget_tokens"), int): raise ControlPlaneError("hold_missing_root_or_owner")
    project = request.get("project_id") or work.get("project_id") or work.get("root_project_id")
    if not project: raise ControlPlaneError("hold_missing_root_or_owner")
    project = _project(project)
    occurred = _timestamp(request.get("occurred_at"))
    provenance = request.get("timestamp_provenance", "explicit")
    if provenance != "explicit": raise ControlPlaneError("hold_schema_or_version")
    return {"request": request, "project_id": project, "occurred_at": occurred, "timestamp_provenance": provenance}

def _replay_lists(state: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = state.get("claims", []) if isinstance(state, Mapping) else []
    runs = state.get("active_runs", []) if isinstance(state, Mapping) else []
    return list(claims), list(runs)

def _control_events(request: Mapping[str, Any], project_id: str, result: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    work = dict(request["work"]); run = dict(request["execution_run"]); claim = dict(request["dispatch_claim"])
    common = {"work_id": work["work_id"], "role": work["role"], "root_budget_tokens": work["root_budget_tokens"], "remaining_budget_tokens": work["remaining_budget_tokens"], "issue_anchor_digest": _digest(work.get("issue_anchor", {})), "durable_anchor_digest": _digest(work.get("durable_anchors", []))}
    out = []
    if result and result.get("decision") == "hold_required":
        stops = result.get("stop_conditions", [])
        if any(str(x).startswith(("missing_", "unknown_", "privacy_", "work_issue_anchor")) for x in stops):
            return []
    for kind, payload in (("control_plane_initialized", {"operation": "initialize"}), ("work_registered", common), ("execution_run_registered", {**common, "run_id": run.get("run_id"), "state": run.get("state")}), ("dispatch_claim_registered", {**common, "decision_boundary": claim.get("decision_boundary"), "transition_semantics": claim.get("transition_semantics")})):
        p = _payload_base(project_id, kind, payload, request["occurred_at"], request.get("timestamp_provenance", "explicit"))
        out.append({"event_type": "control." + kind, "event_id": _event_id(project_id, _identity(kind, project_id, p)), "payload": p, "actor": work["role"], "source": "af18-control-plane-v1", "root": project_id})
    if result and result.get("decision") == "hold_required":
        p = _payload_base(project_id, "control_hold_recorded", {**common, "run_id": run.get("run_id"), "hold_codes": result.get("stop_conditions", [])}, request["occurred_at"], "explicit")
        out.append({"event_type": "control.control_hold_recorded", "event_id": _event_id(project_id, _identity("control_hold_recorded", project_id, p)), "payload": p, "actor": work["role"], "source": "af18-control-plane-v1", "root": project_id})
    return out

def reduce_control_events(events: Iterable[Any]) -> dict[str, Any]:
    state = {"initialized": False, "work": {}, "claims": [], "active_runs": [], "holds": [], "disabled": False, "successors": [], "summaries": [], "attention": [], "terminal_handoff": None}
    for event in events:
        envelope = event.payload if hasattr(event, "payload") else event.get("payload", {})
        payload = _inner(envelope)
        event_type = event.event_type if hasattr(event, "event_type") else event.get("event_type", "")
        kind = payload.get("kind") or str(event_type).removeprefix("control.")
        _validate_envelope(envelope)
        if kind == "control_plane_initialized": state["initialized"] = True
        elif kind == "work_registered": state["work"] = dict(payload)
        elif kind == "dispatch_claim_registered":
            claim_state = dict(payload); claim_state["__occurred_at"] = envelope["occurred_at"]
            if claim_state not in state["claims"]: state["claims"].append(claim_state)
        elif kind == "execution_run_registered":
            if payload.get("state") == "active" and payload not in state["active_runs"]: state["active_runs"].append(dict(payload))
        elif kind == "control_hold_recorded": state["holds"].append(dict(payload))
        elif kind == "control_disabled": state["disabled"] = True
        elif kind == "logical_successor_recorded": state["successors"].append(dict(payload))
        elif kind == "work_summary_recorded": state["summaries"].append(dict(payload))
        elif kind == "attention_summary_recorded": state["attention"].append(dict(payload))
        elif kind == "terminal_handoff_recorded": state["terminal_handoff"] = dict(payload)
        elif str(kind).startswith("control."): raise ControlPlaneHold("hold_schema_or_version")
    return state

def replay_control_state(projects_root: str | Path, project_id: str) -> dict[str, Any]:
    pid = _project(project_id); path = Path(projects_root).expanduser() / pid / "collaboration.db"
    # The LedgerStore read-only constructor accepts a database path or a
    # project-id discovery root, but never both.  Opening by path keeps this
    # route read-only; identity is checked against the requested path after
    # the store has validated the existing authority metadata.
    ledger = LocalCollaborationLedger(db_path=path, create=False)
    try:
        if ledger.project_id != pid:
            raise ControlPlaneHold("hold_project_identity")
        return reduce_control_events([e for e in ledger.list_events() if e.event_type.startswith("control.")])
    finally: ledger.close()

def plan_control_request(request: Mapping[str, Any], replay_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    parsed = _packet(request); state = replay_state or {}
    if replay_state and any(request.get(k) for k in ("existing_dispatch_claims", "active_runs")): raise ControlPlaneHold("hold_untrusted_observation")
    claims, runs = _replay_lists(state)
    work = request["work"]; run = request["execution_run"]; claim = request["dispatch_claim"]
    candidate_events = _control_events(request, parsed["project_id"])
    candidate_claim = next((e for e in candidate_events if e["event_type"] == "control.dispatch_claim_registered"), None)
    candidate_claim_payload = _inner(candidate_claim["payload"]) if candidate_claim else {}
    candidate_occurred_at = candidate_claim["payload"]["occurred_at"] if candidate_claim else None
    exact_claim = any(isinstance(c, Mapping) and all(c.get(k) == candidate_claim_payload.get(k) for k in ("work_id", "decision_boundary", "transition_semantics", "root_budget_tokens", "remaining_budget_tokens", "issue_anchor_digest", "durable_anchor_digest")) and c.get("__occurred_at") == candidate_occurred_at for c in claims)
    exact_run = any(isinstance(r, Mapping) and r.get("run_id") == run.get("run_id") and r.get("work_id") == work.get("work_id") for r in runs)
    same_claim_identity = any(isinstance(c, Mapping) and all(c.get(k) == candidate_claim_payload.get(k) for k in ("work_id", "decision_boundary", "transition_semantics")) for c in claims)
    if same_claim_identity and not exact_claim:
        return {"project_id": parsed["project_id"], "decision": "hold_duplicate_or_divergent", "stop_conditions": ["hold_duplicate_or_divergent"], "event_batch": [], "mutation_performed": False, "dispatch_performed": False}
    if exact_claim and exact_run:
        return {"project_id": parsed["project_id"], "decision": "duplicate", "stop_conditions": [], "event_batch": [], "mutation_performed": False, "dispatch_performed": False}
    packet = dict(request); packet["existing_dispatch_claims"] = claims; packet["active_runs"] = runs
    try:
        from plan_af18_mvp1_control import plan_preflight
        now = dt.datetime.fromisoformat(parsed["occurred_at"].replace("Z", "+00:00"))
        result = plan_preflight(packet, now)
    except Exception:
        result = {"decision": "hold_required", "stop_conditions": ["hold_schema_or_version"]}
    result["event_batch"] = _control_events(request, parsed["project_id"], result)
    result["project_id"] = parsed["project_id"]; result["mutation_performed"] = False; result["dispatch_performed"] = False
    return result

def apply_control_request(projects_root: str | Path, project_id: str, request: Mapping[str, Any]) -> dict[str, Any]:
    parsed = _packet(request); pid = _project(project_id)
    if pid != parsed["project_id"]: raise ControlPlaneHold("hold_project_identity")
    path = Path(projects_root).expanduser() / pid / "collaboration.db"
    ledger = LocalCollaborationLedger.open_existing(path, expected_project_id=pid)
    try:
        replay = reduce_control_events([e for e in ledger.list_events() if e.event_type.startswith("control.")]); result = plan_control_request(request, replay)
        batch = result.get("event_batch", []); before_count = len(ledger.list_events()); ledger.append_batch(batch); after_count = len(ledger.list_events())
        result["mutation_performed"] = after_count > before_count; result["appended_count"] = after_count - before_count; result["duplicate_count"] = max(0, len(batch) - result["appended_count"]); result["generation"] = after_count; result["replay"] = reduce_control_events([e for e in ledger.list_events() if e.event_type.startswith("control.")]); return result
    except (LedgerError, OSError) as exc:
        raise ControlPlaneHold("hold_ledger_integrity") from exc
    finally: ledger.close()
