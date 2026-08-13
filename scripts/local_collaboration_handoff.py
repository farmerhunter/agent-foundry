"""Owner-verified, single-active-device handoff state over LedgerStore events.

This module has no device, bundle, transport, network, or runtime I/O.  It
reduces only its closed metadata events from a LedgerStore snapshot and uses
the public conditional append API for every state change.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from local_collaboration_ledger import (
    GENESIS, LedgerBusyError, LedgerConflictError, LedgerError,
    LedgerIdentityError, LedgerIntegrityError, LedgerPermissionError,
    LedgerSchemaError, LedgerStaleSnapshotError, LocalCollaborationLedger,
)

VERSION = "LocalCollaborationHandoff-v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PORTABLE_GENESIS = "0" * 64
OPAQUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output", "secret", "token", "credential", "native_history", "native_thread_id", "username", "hostname", "machine", "machine_label", "path", "exception", "trusted", "approved", "verified", "authorized"}
TRANSITIONS = {"enroll_initial", "enroll_target", "revoke_inactive", "prepare", "source_lock", "bundle_exported", "cancel", "takeover", "target_activate"}
OUTCOMES = {"enrolled", "prepared", "source_locked", "bundle_exported", "cancelled", "taken_over", "target_active", "hold_schema", "hold_privacy", "hold_project_identity", "hold_enrollment", "hold_revoked", "hold_epoch", "hold_transition", "hold_stale_snapshot", "hold_overlap_conflict", "hold_cancellation_unproven", "hold_owner_integrity", "hold_owner_busy", "hold_owner_permission", "hold_readback_ambiguous"}


class HandoffHold(ValueError):
    def __init__(self, outcome: str, reason_code: str):
        self.outcome, self.reason_code = outcome, reason_code
        super().__init__(outcome)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HandoffHold("hold_schema", "schema_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _walk(value: Any, depth: int = 0) -> None:
    if depth > 12:
        raise HandoffHold("hold_privacy", "privacy_or_depth_rejected")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise HandoffHold("hold_schema", "schema_invalid")
            if key.lower() in FORBIDDEN:
                raise HandoffHold("hold_privacy", "privacy_rejected")
            _walk(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, depth + 1)
    elif value is not None and (isinstance(value, bool) or isinstance(value, (str, int, float))):
        if isinstance(value, float) and value != value:
            raise HandoffHold("hold_schema", "schema_invalid")
    else:
        raise HandoffHold("hold_schema", "schema_invalid")


def _uuid(value: Any, outcome: str = "hold_schema") -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HandoffHold(outcome, "identity_invalid") from exc


def _opaque(value: Any, outcome: str = "hold_schema") -> str:
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise HandoffHold(outcome, "opaque_invalid")
    return value


def _hex(value: Any, outcome: str = "hold_schema") -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise HandoffHold(outcome, "digest_invalid")
    return value


def _positive(value: Any, outcome: str = "hold_epoch") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise HandoffHold(outcome, "epoch_invalid")
    return value


@dataclass(frozen=True)
class Enrollment:
    replica_id: str
    replica_epoch: int
    enrollment_id: str
    enrollment_digest: str
    revoked: bool = False


@dataclass(frozen=True)
class HandoffState:
    project_id: str
    authority_generation: int
    authority_head: str
    active_replica_id: str | None
    active_replica_epoch: int | None
    active_epoch: int
    phase: str
    enrollments: tuple[Enrollment, ...]
    handoff: Mapping[str, Any] | None
    state_digest: str
    portable_prefix_identity: str


@dataclass(frozen=True)
class TransitionPlan:
    transition: str
    project_id: str
    expected_generation: int
    expected_head: str
    before_state_digest: str
    after_state_digest: str
    expected_outcome: str
    request_digest: str
    event: Mapping[str, Any]


def _state_value(state: HandoffState) -> dict[str, Any]:
    return {
        "project_id": state.project_id,
        "authority_generation": state.authority_generation,
        "authority_head": state.authority_head,
        "active_replica_id": state.active_replica_id,
        "active_replica_epoch": state.active_replica_epoch,
        "active_epoch": state.active_epoch,
        "phase": state.phase,
        "enrollments": [{"replica_id": e.replica_id, "replica_epoch": e.replica_epoch, "enrollment_id": e.enrollment_id, "enrollment_digest": e.enrollment_digest, "revoked": e.revoked} for e in state.enrollments],
        "handoff": dict(state.handoff) if state.handoff is not None else None,
    }


def _make_state(project_id: str, generation: int, head: str, active_id: str | None, active_replica_epoch: int | None,
                active_epoch: int, phase: str, enrollments: Mapping[str, Enrollment], handoff: Mapping[str, Any] | None,
                portable_prefix_identity: str = PORTABLE_GENESIS) -> HandoffState:
    bare = {"project_id": project_id,
            "active_replica_id": active_id, "active_replica_epoch": active_replica_epoch, "active_epoch": active_epoch,
            "phase": phase, "enrollments": [{"replica_id": item.replica_id, "replica_epoch": item.replica_epoch,
            "enrollment_id": item.enrollment_id, "enrollment_digest": item.enrollment_digest, "revoked": item.revoked}
            for item in sorted(enrollments.values(), key=lambda item: item.replica_id)], "handoff": dict(handoff) if handoff else None}
    return HandoffState(project_id, generation, head, active_id, active_replica_epoch, active_epoch, phase,
                        tuple(Enrollment(**item) for item in bare["enrollments"]), bare["handoff"], _digest(bare),
                        _hex(portable_prefix_identity, "hold_owner_integrity"))


def _initial(snapshot) -> HandoffState:
    return _make_state(snapshot.project_id, 0, GENESIS, None, None, 0, "uninitialized", {}, None, PORTABLE_GENESIS)


def _semantic_event_identity(event) -> Mapping[str, Any]:
    required = ("sequence", "event_id", "event_type", "payload_hash", "actor", "source", "root")
    if not all(hasattr(event, field) for field in required):
        raise HandoffHold("hold_schema", "event_record_invalid")
    if not isinstance(event.sequence, int) or isinstance(event.sequence, bool) or event.sequence < 1:
        raise HandoffHold("hold_owner_integrity", "event_order_invalid")
    _uuid(event.event_id, "hold_owner_integrity")
    if not isinstance(event.event_type, str) or not event.event_type:
        raise HandoffHold("hold_owner_integrity", "event_identity_invalid")
    _hex(event.payload_hash, "hold_owner_integrity")
    if event.actor is not None and not isinstance(event.actor, str):
        raise HandoffHold("hold_owner_integrity", "event_identity_invalid")
    if event.source is not None and not isinstance(event.source, str):
        raise HandoffHold("hold_owner_integrity", "event_identity_invalid")
    if not isinstance(event.root, str):
        raise HandoffHold("hold_owner_integrity", "event_identity_invalid")
    return {field: getattr(event, field) for field in required}


def _advance_portable_prefix(state: HandoffState, event) -> HandoffState:
    identity = _digest({"prefix": state.portable_prefix_identity, "event": _semantic_event_identity(event)})
    return _make_state(state.project_id, state.authority_generation, state.authority_head,
                       state.active_replica_id, state.active_replica_epoch, state.active_epoch,
                       state.phase, _enrollment_map(state), state.handoff, identity)


def _event_payload(event) -> Mapping[str, Any] | None:
    if event.event_type not in {"replica_enrolled", "replica_revoked", "handoff_prepared", "handoff_source_locked", "handoff_bundle_exported", "handoff_cancelled", "handoff_takeover_approved", "handoff_target_activated"}:
        return None
    payload = event.payload
    if not isinstance(payload, Mapping) or payload.get("schema_version") != VERSION:
        raise HandoffHold("hold_owner_integrity", "handoff_event_invalid")
    _walk(payload)
    if payload.get("project_id") != event.root:
        raise HandoffHold("hold_project_identity", "event_root_mismatch")
    _uuid(payload.get("project_id"), "hold_project_identity")
    return payload


def _reduce_event(state: HandoffState, event) -> HandoffState:
    if event.root != state.project_id:
        raise HandoffHold("hold_project_identity", "event_project_mismatch")
    payload = _event_payload(event)
    if payload is None:
        return _advance_portable_prefix(_make_state(state.project_id, event.sequence, event.event_hash,
                                        state.active_replica_id, state.active_replica_epoch,
                                        state.active_epoch, state.phase, _enrollment_map(state), state.handoff,
                                        state.portable_prefix_identity), event)
    if payload.get("transition") == "target_activate":
        if payload.get("project_id") != state.project_id:
            raise HandoffHold("hold_project_identity", "event_project_mismatch")
        handoff = dict(state.handoff or {})
        handoff["status"] = "held_unverified_target_activation"
        return _advance_portable_prefix(_make_state(state.project_id, event.sequence, event.event_hash, state.active_replica_id,
                                        state.active_replica_epoch, state.active_epoch, "held", _enrollment_map(state), handoff,
                                        state.portable_prefix_identity), event)
    if payload["project_id"] != state.project_id:
        raise HandoffHold("hold_project_identity", "event_project_mismatch")
    transition = payload.get("transition")
    if transition not in TRANSITIONS or _opaque(payload.get("request_digest")) is None or _hex(payload.get("before_state_digest")) is None:
        raise HandoffHold("hold_owner_integrity", "handoff_event_invalid")
    # Replaying payloads uses the same state machine as planning.  Event IDs are
    # checked separately by LedgerStore; payload values are the durable inputs.
    return _advance_portable_prefix(
        _transition(state, payload, replay=True, event_generation=event.sequence, event_head=event.event_hash), event,
    )


def _enrollment_map(state: HandoffState) -> dict[str, Enrollment]:
    return {entry.replica_id: entry for entry in state.enrollments}


def _decision(request: Mapping[str, Any]) -> tuple[str, str]:
    return _opaque(request.get("decision_id")), _hex(request.get("decision_digest"))


def _enrollment_from(request: Mapping[str, Any]) -> Enrollment:
    return Enrollment(_opaque(request.get("replica_id"), "hold_enrollment"), _positive(request.get("replica_epoch")),
                      _opaque(request.get("enrollment_id"), "hold_enrollment"), _hex(request.get("enrollment_digest"), "hold_enrollment"))


def _require_keys(request: Mapping[str, Any], keys: set[str]) -> None:
    if set(request) != keys:
        raise HandoffHold("hold_schema", "closed_request_required")


def _transition(state: HandoffState, request: Mapping[str, Any], *, replay: bool = False,
                event_generation: int | None = None, event_head: str | None = None) -> HandoffState:
    if not isinstance(request, Mapping):
        raise HandoffHold("hold_schema", "schema_invalid")
    transition = request.get("transition")
    if transition not in TRANSITIONS:
        raise HandoffHold("hold_transition", "transition_invalid")
    if request.get("project_id") != state.project_id:
        raise HandoffHold("hold_project_identity", "project_mismatch")
    enrollments = _enrollment_map(state)
    active_id, active_replica_epoch, active_epoch, phase, handoff = state.active_replica_id, state.active_replica_epoch, state.active_epoch, state.phase, state.handoff
    if transition in {"enroll_initial", "enroll_target"}:
        keys = {"schema_version", "transition", "project_id", "replica_id", "replica_epoch", "enrollment_id", "enrollment_digest", "decision_id", "decision_digest", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "replica_id", "replica_epoch", "enrollment_id", "enrollment_digest", "decision_id", "decision_digest"}
        _require_keys(request, keys)
        entry = _enrollment_from(request); _decision(request)
        existing = enrollments.get(entry.replica_id)
        if transition == "enroll_initial":
            if phase != "uninitialized" or existing is not None:
                raise HandoffHold("hold_transition", "initial_enrollment_invalid")
            active_id, active_replica_epoch, active_epoch, phase = entry.replica_id, entry.replica_epoch, 1, "active"
        else:
            if phase != "active" or entry.replica_id == active_id:
                raise HandoffHold("hold_transition", "target_enrollment_invalid")
            if existing is not None and (not existing.revoked or entry.replica_epoch <= existing.replica_epoch):
                raise HandoffHold("hold_epoch", "reenrollment_epoch_invalid")
        enrollments[entry.replica_id] = entry
    elif transition == "revoke_inactive":
        keys = {"schema_version", "transition", "project_id", "replica_id", "decision_id", "decision_digest", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "replica_id", "decision_id", "decision_digest"}
        _require_keys(request, keys); _decision(request); rid = _opaque(request.get("replica_id"), "hold_enrollment")
        entry = enrollments.get(rid)
        if phase != "active" or entry is None or entry.revoked or rid == active_id:
            raise HandoffHold("hold_enrollment", "inactive_enrollment_required")
        enrollments[rid] = Enrollment(entry.replica_id, entry.replica_epoch, entry.enrollment_id, entry.enrollment_digest, True)
    elif transition == "prepare":
        keys = {"schema_version", "transition", "project_id", "handoff_id", "source_replica_id", "target_replica_id", "frontier_digest", "source_generation", "source_head", "source_prefix_identity", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "handoff_id", "source_replica_id", "target_replica_id", "frontier_digest"}
        _require_keys(request, keys); source, target = _opaque(request.get("source_replica_id"), "hold_enrollment"), _opaque(request.get("target_replica_id"), "hold_enrollment")
        target_entry = enrollments.get(target)
        if phase != "active" or source != active_id or target == source or target_entry is None or target_entry.revoked:
            raise HandoffHold("hold_enrollment", "prepare_enrollment_invalid")
        if replay:
            source_generation = request.get("source_generation")
            if not isinstance(source_generation, int) or isinstance(source_generation, bool) or source_generation < 0:
                raise HandoffHold("hold_owner_integrity", "source_frontier_generation_invalid")
            source_head = _hex(request.get("source_head"), "hold_owner_integrity")
            source_prefix_identity = _hex(request.get("source_prefix_identity"), "hold_owner_integrity")
            if source_generation != state.authority_generation or source_prefix_identity != state.portable_prefix_identity:
                raise HandoffHold("hold_owner_integrity", "source_frontier_not_event_local_prefix")
        else:
            source_generation, source_head, source_prefix_identity = state.authority_generation, state.authority_head, state.portable_prefix_identity
        handoff = {"handoff_id": _opaque(request.get("handoff_id")), "source_replica_id": source, "target_replica_id": target,
                   "source_replica_epoch": active_replica_epoch, "target_replica_epoch": target_entry.replica_epoch,
                   "prior_active_epoch": active_epoch, "source_generation": source_generation,
                   "source_head": source_head, "source_prefix_identity": source_prefix_identity,
                   "frontier_digest": _hex(request.get("frontier_digest")), "status": "preparing"}
        phase = "preparing"
    elif transition == "source_lock":
        keys = {"schema_version", "transition", "project_id", "handoff_id", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "handoff_id"}
        _require_keys(request, keys)
        if phase != "preparing" or not handoff or _opaque(request.get("handoff_id")) != handoff["handoff_id"]:
            raise HandoffHold("hold_transition", "source_lock_invalid")
        handoff = dict(handoff); handoff["status"] = "source_locked"; phase = "source_locked"
    elif transition == "bundle_exported":
        keys = {"schema_version", "transition", "project_id", "handoff_id", "bundle_id", "content_manifest_digest", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "handoff_id", "bundle_id", "content_manifest_digest"}
        _require_keys(request, keys)
        if phase != "source_locked" or not handoff or handoff.get("status") != "source_locked" or _opaque(request.get("handoff_id")) != handoff["handoff_id"]:
            raise HandoffHold("hold_transition", "bundle_export_invalid")
        handoff = dict(handoff)
        handoff.update(status="bundle_exported", bundle_id=_opaque(request.get("bundle_id")), content_manifest_digest=_hex(request.get("content_manifest_digest")))
    elif transition == "cancel":
        keys = {"schema_version", "transition", "project_id", "handoff_id", "cancellation_evidence", "decision_id", "decision_digest", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "handoff_id", "cancellation_evidence", "decision_id", "decision_digest"}
        _require_keys(request, keys); _decision(request)
        if phase not in {"preparing", "source_locked"} or not handoff or _opaque(request.get("handoff_id")) != handoff["handoff_id"]:
            raise HandoffHold("hold_transition", "cancel_invalid")
        evidence = request.get("cancellation_evidence")
        if evidence not in {"bundle_not_released", "target_non_activation_readback"}:
            raise HandoffHold("hold_cancellation_unproven", "cancellation_evidence_invalid")
        if handoff.get("status") == "bundle_exported" and evidence == "bundle_not_released":
            raise HandoffHold("hold_cancellation_unproven", "bundle_release_persisted")
        handoff = dict(handoff); handoff.update(status="cancelled", cancellation_evidence=evidence); phase = "active"
    elif transition in {"target_activate", "takeover"}:
        required = {"schema_version", "transition", "project_id", "target_replica_id", "decision_id", "decision_digest", "request_digest", "before_state_digest"} if replay else {"transition", "project_id", "target_replica_id", "decision_id", "decision_digest"}
        if transition == "target_activate":
            required |= {"handoff_id", "import_readback_generation", "import_readback_head"}
        else:
            required |= {"prior_frontier_digest"}
        _require_keys(request, required); _decision(request); target = _opaque(request.get("target_replica_id"), "hold_enrollment")
        target_entry = enrollments.get(target)
        if target_entry is None or target_entry.revoked:
            raise HandoffHold("hold_revoked", "target_not_active_enrollment")
        if transition == "target_activate":
            if phase != "source_locked" or not handoff or _opaque(request.get("handoff_id")) != handoff["handoff_id"] or target != handoff["target_replica_id"]:
                raise HandoffHold("hold_transition", "activation_invalid")
            if request.get("import_readback_generation") != state.authority_generation or _hex(request.get("import_readback_head")) != state.authority_head:
                raise HandoffHold("hold_readback_ambiguous", "target_readback_invalid")
            handoff = dict(handoff); handoff["status"] = "target_active"
        else:
            if phase not in {"active", "source_locked", "held"} or target == active_id:
                raise HandoffHold("hold_transition", "takeover_invalid")
            _hex(request.get("prior_frontier_digest")); handoff = {"handoff_id": _opaque(request.get("decision_id")), "source_replica_id": active_id,
                "target_replica_id": target, "source_replica_epoch": active_replica_epoch, "target_replica_epoch": target_entry.replica_epoch,
                "prior_active_epoch": active_epoch, "prior_frontier_digest": request["prior_frontier_digest"], "status": "target_active", "takeover": True}
        active_id, active_replica_epoch, active_epoch, phase = target, target_entry.replica_epoch, active_epoch + 1, "active"
    if replay:
        if request.get("before_state_digest") != state.state_digest:
            raise HandoffHold("hold_owner_integrity", "before_state_digest_invalid")
        generation = event_generation if event_generation is not None else state.authority_generation
        head = event_head if event_head is not None else state.authority_head
    else:
        generation, head = state.authority_generation, state.authority_head
    return _make_state(state.project_id, generation, head, active_id, active_replica_epoch, active_epoch, phase, enrollments, handoff)


def read_handoff_state(db_path, *, expected_project_id: str) -> HandoffState:
    snapshot = LocalCollaborationLedger.authority_snapshot(db_path, expected_project_id=expected_project_id)
    state = _initial(snapshot)
    for event in snapshot.events:
        state = _reduce_event(state, event)
    return _make_state(snapshot.project_id, snapshot.authority_generation, snapshot.authority_head,
                       state.active_replica_id, state.active_replica_epoch, state.active_epoch,
                       state.phase, _enrollment_map(state), state.handoff, state.portable_prefix_identity)


def reduce_handoff_events(project_id: str, events, authority_generation: int, authority_head: str) -> HandoffState:
    """Pure A1 reducer for an already-verified immutable event sequence.

    It deliberately does not open storage or assert that an external event
    sequence was enrolled, imported, or transported by an owner.
    """
    project_id = _uuid(project_id, "hold_project_identity")
    if not isinstance(authority_generation, int) or isinstance(authority_generation, bool) or authority_generation < 0:
        raise HandoffHold("hold_schema", "generation_invalid")
    _hex(authority_head)
    state = _make_state(project_id, 0, GENESIS, None, None, 0, "uninitialized", {}, None)
    prior = GENESIS
    expected_sequence = 1
    for event in events:
        if not all(hasattr(event, field) for field in ("sequence", "previous_hash", "event_hash", "root")):
            raise HandoffHold("hold_schema", "event_record_invalid")
        if event.sequence != expected_sequence or event.previous_hash != prior or event.root != project_id:
            raise HandoffHold("hold_owner_integrity", "event_order_invalid")
        state = _reduce_event(state, event)
        prior = event.event_hash
        expected_sequence += 1
    if authority_generation != expected_sequence - 1 or authority_head != prior:
        raise HandoffHold("hold_owner_integrity", "authority_pair_invalid")
    return _make_state(project_id, authority_generation, authority_head, state.active_replica_id,
                       state.active_replica_epoch, state.active_epoch, state.phase,
                       _enrollment_map(state), state.handoff, state.portable_prefix_identity)


def _hold(project_id: str, outcome: str, reason_code: str) -> dict[str, Any]:
    return {"schema_version": VERSION, "outcome": outcome, "project_id": project_id, "reason_code": reason_code,
            "flags": {"owner_persisted": False, "owner_readback_verified": False, "bundle_exported": False,
                      "owner_import_performed": False, "transport_performed": False}}


def _planned_payload(state: HandoffState, request: Mapping[str, Any]) -> tuple[dict[str, Any], HandoffState]:
    _walk(request)
    if not isinstance(request, Mapping):
        raise HandoffHold("hold_schema", "schema_invalid")
    if request.get("project_id") != state.project_id:
        raise HandoffHold("hold_project_identity", "project_mismatch")
    bound = dict(request)
    if bound.get("transition") == "prepare":
        if any(key in bound for key in ("source_generation", "source_head", "source_prefix_identity")):
            raise HandoffHold("hold_schema", "caller_source_frontier_forbidden")
        bound["source_generation"] = state.authority_generation
        bound["source_head"] = state.authority_head
        bound["source_prefix_identity"] = state.portable_prefix_identity
    bound["schema_version"] = VERSION
    bound["before_state_digest"] = state.state_digest
    bound["request_digest"] = _digest({key: value for key, value in bound.items() if key != "request_digest"})
    after = _transition(state, bound, replay=True, event_generation=state.authority_generation + 1, event_head="0" * 64)
    return bound, after


def plan_handoff_transition(state: HandoffState, request: Mapping[str, Any]) -> TransitionPlan | dict[str, Any]:
    try:
        if not isinstance(request, Mapping) or request.get("transition") == "target_activate":
            return _hold(state.project_id, "hold_a2_owner_proof_unavailable", "complete_a2_owner_verified_import")
        payload, after = _planned_payload(state, request)
        event_type = {"enroll_initial": "replica_enrolled", "enroll_target": "replica_enrolled", "revoke_inactive": "replica_revoked", "prepare": "handoff_prepared", "source_lock": "handoff_source_locked", "bundle_exported": "handoff_bundle_exported", "cancel": "handoff_cancelled", "takeover": "handoff_takeover_approved", "target_activate": "handoff_target_activated"}[payload["transition"]]
        event_id = str(uuid.uuid5(uuid.UUID(state.project_id), event_type + ":" + payload["request_digest"]))
        event = {"event_type": event_type, "event_id": event_id, "payload": payload, "actor": "owner", "source": "orch05_handoff", "root": state.project_id}
        expected_outcome = {"enroll_initial": "enrolled", "enroll_target": "enrolled", "prepare": "prepared", "source_lock": "source_locked", "bundle_exported": "bundle_exported", "cancel": "cancelled", "takeover": "taken_over", "revoke_inactive": "enrolled"}[payload["transition"]]
        return TransitionPlan(payload["transition"], state.project_id, state.authority_generation, state.authority_head,
                              state.state_digest, after.state_digest, expected_outcome, payload["request_digest"], event)
    except HandoffHold as exc:
        return _hold(state.project_id, exc.outcome, exc.reason_code)


def _owner_hold(project_id: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, LedgerStaleSnapshotError): return _hold(project_id, "hold_stale_snapshot", "stale_snapshot")
    if isinstance(exc, LedgerBusyError): return _hold(project_id, "hold_owner_busy", "owner_busy")
    if isinstance(exc, LedgerPermissionError): return _hold(project_id, "hold_owner_permission", "owner_permission")
    if isinstance(exc, (LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError)): return _hold(project_id, "hold_owner_integrity", "owner_integrity")
    if isinstance(exc, LedgerConflictError): return _hold(project_id, "hold_readback_ambiguous", "conditional_conflict")
    if isinstance(exc, HandoffHold): return _hold(project_id, exc.outcome, exc.reason_code)
    return _hold(project_id, "hold_readback_ambiguous", "owner_readback_ambiguous")


def apply_handoff_transition(ledger: LocalCollaborationLedger, plan: TransitionPlan, *, expected_before: HandoffState) -> dict[str, Any]:
    if not isinstance(plan, TransitionPlan) or not isinstance(expected_before, HandoffState) or plan.project_id != ledger.project_id:
        return _hold(plan.project_id if isinstance(plan, TransitionPlan) else ledger.project_id, "hold_schema", "plan_invalid")
    try:
        if plan.transition == "target_activate":
            return _hold(plan.project_id, "hold_a2_owner_proof_unavailable", "complete_a2_owner_verified_import")
        current = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
        if (expected_before.authority_generation, expected_before.authority_head, expected_before.state_digest) != (plan.expected_generation, plan.expected_head, plan.before_state_digest):
            return _hold(plan.project_id, "hold_stale_snapshot", "before_state_mismatch")
        expected_event_id = str(uuid.uuid5(uuid.UUID(plan.project_id), plan.event["event_type"] + ":" + plan.request_digest))
        if plan.event.get("event_id") != expected_event_id:
            return _hold(plan.project_id, "hold_readback_ambiguous", "event_id_mismatch")
        expected_ref = (plan.expected_generation + 1, plan.event["event_id"], _digest(plan.event["payload"]))
        normal = (current.authority_generation, current.authority_head, current.state_digest) == (plan.expected_generation, plan.expected_head, plan.before_state_digest)
        duplicate = False
        if not normal:
            snapshot = LocalCollaborationLedger.authority_snapshot(ledger.path, expected_project_id=ledger.project_id)
            tail = snapshot.events[-1:] if snapshot.authority_generation == plan.expected_generation + 1 else ()
            if len(tail) == 1:
                event = tail[0]
                duplicate = ((event.sequence, event.event_id, event.payload_hash) == expected_ref
                             and event.event_type == plan.event["event_type"] and event.actor == plan.event["actor"]
                             and event.source == plan.event["source"] and event.root == plan.event["root"]
                             and event.previous_hash == plan.expected_head and current.state_digest == plan.after_state_digest)
            if not duplicate:
                return _hold(plan.project_id, "hold_stale_snapshot", "fresh_before_mismatch")
        result = ledger.conditional_append_batch([plan.event], expected_generation=plan.expected_generation, expected_head=plan.expected_head)
        if normal and result.status != "appended":
            return _hold(plan.project_id, "hold_readback_ambiguous", "normal_append_not_appended")
        if duplicate and result.status != "duplicate":
            return _hold(plan.project_id, "hold_stale_snapshot", "duplicate_tail_changed")
        if result.status not in {"appended", "duplicate"} or len(result.event_refs) != 1 or result.event_refs[0][:3] != expected_ref:
            return _hold(plan.project_id, "hold_readback_ambiguous", "event_ref_mismatch")
        after = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
        if (after.authority_generation, after.authority_head, after.state_digest) != (result.generation, result.head, plan.after_state_digest):
            return _hold(plan.project_id, "hold_readback_ambiguous", "after_state_mismatch")
        return {"schema_version": VERSION, "outcome": plan.expected_outcome, "transition": plan.transition, "project_id": plan.project_id,
                "event_ids": [plan.event["event_id"]], "request_digest": plan.request_digest,
                "before_state_digest": plan.before_state_digest, "after_state_digest": plan.after_state_digest,
                "readback_generation": after.authority_generation, "readback_head": after.authority_head,
                "flags": {"owner_persisted": result.mutation_performed, "owner_readback_verified": True,
                          "bundle_exported": plan.transition == "bundle_exported", "owner_import_performed": False, "transport_performed": False},
                "cas_status": result.status}
    except Exception as exc:
        return _owner_hold(plan.project_id, exc)


def verify_a2_import_seam(state: HandoffState, bundle_header: Mapping[str, Any]) -> dict[str, Any]:
    try:
        _walk(bundle_header)
        required = {"project_id", "handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch", "target_replica_epoch", "source_generation", "source_head", "frontier_digest"}
        if not isinstance(bundle_header, Mapping) or set(bundle_header) != required:
            raise HandoffHold("hold_schema", "bundle_header_invalid")
        if state.phase != "source_locked" or not state.handoff or any(bundle_header[key] != state.handoff.get(key) for key in required - {"project_id"}) or bundle_header["project_id"] != state.project_id:
            raise HandoffHold("hold_transition", "a2_binding_invalid")
        return {"schema_version": VERSION, "outcome": "a2_import_candidate", "project_id": state.project_id,
                "handoff_id": state.handoff["handoff_id"], "state_digest": state.state_digest,
                "owner_import_performed": False, "import_authorized": False, "requires_owner_verification": True,
                "flags": {"owner_persisted": False, "owner_readback_verified": True, "bundle_exported": False,
                          "owner_import_performed": False, "transport_performed": False}}
    except HandoffHold as exc:
        return _hold(state.project_id, exc.outcome, exc.reason_code)


__all__ = ["A2AuthorizationCandidate", "HandoffHold", "HandoffState", "TransitionPlan", "apply_handoff_transition", "plan_handoff_transition", "read_handoff_state", "reduce_handoff_events", "verify_a2_import_seam"]

# Public name reserved by the contract; receipts are JSON mappings to preserve
# a closed portable boundary.
A2AuthorizationCandidate = dict[str, Any]
