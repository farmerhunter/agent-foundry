"""Hermetic portable event-set convergence for local collaboration replicas.

This Core never opens a database, network connection, process, queue, or file.
Each project keeps SQLite as its operational authority; this module consumes only
the owner's already-verified snapshot and returns immutable, in-memory plans.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import is_dataclass
from typing import Any

VERSION = "LocalCollaborationReplica-v1"
GENESIS = "0" * 64
MAX_EVENTS = 100
MAX_BYTES = 1024 * 1024
MAX_DEPTH = 12
MAX_PARENTS = 32
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output", "secret", "credential", "token", "native_history", "hostname", "username", "path", "native_thread_id", "hardware", "exception"}
FLAGS = {"simulation_only": True, "network_capability": False, "authoritative": False,
         "confirmation_eligible": False, "remote_mutation_performed": False}
OUTCOMES = {"replica_export_ready", "replica_import_plan_ready", "replica_converged", "replica_duplicate", "replica_offline", "hold_replica_identity", "hold_transport_integrity", "hold_missing_dependency", "hold_semantic_conflict", "hold_privacy", "hold_schema", "hold_recovery_readback"}


class ReplicaHold(ValueError):
    def __init__(self, outcome: str, reason_code: str):
        self.outcome = outcome
        self.reason_code = reason_code
        super().__init__(outcome)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReplicaHold("hold_schema", "schema_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _uuid(value: Any, *, identity: bool = False) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ReplicaHold("hold_replica_identity" if identity else "hold_schema", "replica_identity_invalid" if identity else "schema_invalid") from exc


def _opaque(value: Any, *, identity: bool = False) -> str:
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise ReplicaHold("hold_replica_identity" if identity else "hold_privacy", "replica_identity_invalid" if identity else "privacy_rejected")
    return value


def _hex(value: Any, outcome: str = "hold_schema", reason: str = "schema_invalid") -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ReplicaHold(outcome, reason)
    return value


def _walk(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ReplicaHold("hold_privacy", "privacy_rejected")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN:
                raise ReplicaHold("hold_privacy", "privacy_rejected")
            _walk(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, depth + 1)
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise ReplicaHold("hold_schema", "schema_invalid")


def _identity(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: event[key] for key in ("replica_id", "replica_epoch", "origin_sequence", "event_id")}


def _identity_key(identity: Mapping[str, Any]) -> tuple[str, int, int, str]:
    if not isinstance(identity, Mapping) or set(identity) != {"replica_id", "replica_epoch", "origin_sequence", "event_id"}:
        raise ReplicaHold("hold_schema", "schema_invalid")
    rid = _opaque(identity["replica_id"], identity=True)
    epoch, sequence = identity["replica_epoch"], identity["origin_sequence"]
    if (not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1 or not isinstance(sequence, int)
            or isinstance(sequence, bool) or sequence < 1):
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    return rid, epoch, sequence, _uuid(identity["event_id"], identity=True)


def _enrollment_receipt(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"receipt_id", "receipt_digest", "outcome"}:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    if value.get("outcome") != "enrollment_accepted":
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    return {"receipt_id": _opaque(value["receipt_id"], identity=True), "receipt_digest": _hex(value["receipt_digest"], "hold_replica_identity", "replica_identity_invalid"), "outcome": "enrollment_accepted"}


def _human_decision_receipt(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"receipt_id", "receipt_digest", "outcome"}:
        raise ReplicaHold("hold_semantic_conflict", "semantic_conflict")
    if value.get("outcome") != "human_decision_accepted":
        raise ReplicaHold("hold_semantic_conflict", "semantic_conflict")
    return {"receipt_id": _opaque(value["receipt_id"]), "receipt_digest": _hex(value["receipt_digest"], "hold_semantic_conflict", "semantic_conflict"), "outcome": "human_decision_accepted"}


def _replica_identity(value: Any, project_id: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"project_id", "replica_id", "replica_epoch", "enrollment_receipt"}:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    pid = _uuid(value["project_id"], identity=True)
    if project_id is not None and pid != project_id:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    epoch = value["replica_epoch"]
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    return {"project_id": pid, "replica_id": _opaque(value["replica_id"], identity=True), "replica_epoch": epoch, "enrollment_receipt": _enrollment_receipt(value["enrollment_receipt"])}


def _event(value: Any, project_id: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReplicaHold("hold_schema", "schema_invalid")
    _walk(value)
    allowed = {"project_id", "replica_id", "replica_epoch", "origin_sequence", "event_id", "event_type", "work_id", "decision", "resolution", "human_decision_receipt", "conflict_references", "causal_parents", "event_digest"}
    required = {"project_id", "replica_id", "replica_epoch", "origin_sequence", "event_id", "event_type", "causal_parents", "event_digest"}
    if not required.issubset(value) or not set(value).issubset(allowed):
        raise ReplicaHold("hold_schema", "schema_invalid")
    pid = _uuid(value["project_id"])
    if project_id is not None and pid != project_id:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    identity = _identity_key(_identity(value))
    typ = value["event_type"]
    if typ not in {"work_decision", "work_resolution", "replica_note"}:
        raise ReplicaHold("hold_schema", "schema_invalid")
    parents = value["causal_parents"]
    if not isinstance(parents, list) or len(parents) > MAX_PARENTS:
        raise ReplicaHold("hold_missing_dependency", "missing_dependency")
    normalized = {"project_id": pid, "replica_id": identity[0], "replica_epoch": identity[1], "origin_sequence": identity[2], "event_id": identity[3], "event_type": typ,
                  "causal_parents": [dict(zip(("replica_id", "replica_epoch", "origin_sequence", "event_id"), _identity_key(parent))) for parent in parents]}
    if typ == "work_decision":
        if set(value) - {"project_id", "replica_id", "replica_epoch", "origin_sequence", "event_id", "event_type", "work_id", "decision", "causal_parents", "event_digest"} or not isinstance(value.get("work_id"), str) or value.get("decision") not in {"accept", "reject", "hold"}:
            raise ReplicaHold("hold_schema", "schema_invalid")
        normalized.update(work_id=_opaque(value["work_id"]), decision=value["decision"])
    elif typ == "work_resolution":
        if set(value) - {"project_id", "replica_id", "replica_epoch", "origin_sequence", "event_id", "event_type", "work_id", "resolution", "human_decision_receipt", "conflict_references", "causal_parents", "event_digest"} or not isinstance(value.get("work_id"), str) or value.get("resolution") not in {"accept", "reject", "hold"} or not isinstance(value.get("conflict_references"), list) or not value["conflict_references"] or len(value["conflict_references"]) > MAX_PARENTS:
            raise ReplicaHold("hold_schema", "schema_invalid")
        normalized.update(work_id=_opaque(value["work_id"]), resolution=value["resolution"], human_decision_receipt=_human_decision_receipt(value.get("human_decision_receipt")), conflict_references=[dict(zip(("replica_id", "replica_epoch", "origin_sequence", "event_id"), _identity_key(ref))) for ref in value["conflict_references"]])
    elif set(value) - {"project_id", "replica_id", "replica_epoch", "origin_sequence", "event_id", "event_type", "causal_parents", "event_digest"}:
        raise ReplicaHold("hold_schema", "schema_invalid")
    supplied = _hex(value["event_digest"], "hold_transport_integrity", "transport_integrity_invalid")
    if _digest(normalized) != supplied:
        raise ReplicaHold("hold_transport_integrity", "transport_integrity_invalid")
    normalized["event_digest"] = supplied
    return normalized


def _snapshot(value: Any) -> tuple[str, int, str]:
    if is_dataclass(value):
        value = {key: getattr(value, key) for key in ("project_id", "authority_generation", "authority_head")}
    if not isinstance(value, Mapping):
        raise ReplicaHold("hold_recovery_readback", "recovery_readback_required")
    pid = _uuid(value.get("project_id"))
    generation = value.get("authority_generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        raise ReplicaHold("hold_recovery_readback", "recovery_readback_required")
    return pid, generation, _hex(value.get("authority_head"), "hold_recovery_readback", "recovery_readback_required")


def _validate_event_set(events: Any, project_id: str | None = None) -> list[dict[str, Any]]:
    if not isinstance(events, (list, tuple)) or len(events) > MAX_EVENTS:
        raise ReplicaHold("hold_schema", "schema_invalid")
    if len(_canonical(events).encode()) > MAX_BYTES:
        raise ReplicaHold("hold_schema", "schema_invalid")
    normalized = [_event(event, project_id) for event in events]
    if len(_canonical(normalized).encode()) > MAX_BYTES:
        raise ReplicaHold("hold_schema", "schema_invalid")
    identities: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for event in normalized:
        key = _identity_key(_identity(event))
        prior = identities.get(key)
        if prior is not None and prior["event_digest"] != event["event_digest"]:
            raise ReplicaHold("hold_transport_integrity", "transport_integrity_invalid")
        identities[key] = event
    if len(identities) != len(normalized):
        normalized = list(identities.values())
    keys = set(identities)
    for event in normalized:
        key = _identity_key(_identity(event))
        for parent in event["causal_parents"]:
            parent_key = _identity_key(parent)
            if parent_key == key or parent_key not in keys:
                raise ReplicaHold("hold_missing_dependency", "missing_dependency")
    colors: dict[tuple[str, int, int, str], int] = {}
    def visit(key: tuple[str, int, int, str]) -> None:
        state = colors.get(key, 0)
        if state == 1:
            raise ReplicaHold("hold_missing_dependency", "missing_dependency")
        if state == 2:
            return
        colors[key] = 1
        for parent in identities[key]["causal_parents"]:
            visit(_identity_key(parent))
        colors[key] = 2
    for key in sorted(keys):
        visit(key)
    return normalized


def _receipt(outcome: str, project_id: str, **extra: Any) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise AssertionError(outcome)
    result = {"schema_version": VERSION, "outcome": outcome, "project_id": project_id, "flags": dict(FLAGS)}
    result.update({key: value for key, value in extra.items() if value is not None})
    return result


def _hold(exc: ReplicaHold, project_id: str | None = None, **extra: Any) -> dict[str, Any]:
    return _receipt(exc.outcome, project_id or str(uuid.UUID(int=0)), reason_code=exc.reason_code, **extra)


def _enrollments(value: Any, project_id: str) -> dict[tuple[str, int], dict[str, Any]]:
    if isinstance(value, Mapping) and "replica_id" in value:
        values = [value]
    elif isinstance(value, Mapping):
        values = list(value.values())
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        values = list(value)
    else:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    result = {}
    for item in values:
        identity = _replica_identity(item, project_id)
        key = identity["replica_id"], identity["replica_epoch"]
        if key in result and result[key] != identity:
            raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
        result[key] = identity
    return result


def _inspection_context(project_id: str, identity: Mapping[str, Any], bundle_digest: str) -> str:
    """Bind a verified external enrollment receipt to this exact bundle."""
    return _digest({"project_id": project_id, "replica_id": identity["replica_id"],
                    "replica_epoch": identity["replica_epoch"], "receipt_digest": identity["enrollment_receipt"]["receipt_digest"],
                    "bundle_digest": bundle_digest})


def _validated_inspection(value: Any, *, project_id: str, identity: Mapping[str, Any], bundle_digest: str) -> None:
    """Consume, but never issue, a caller-provided prior inspection receipt."""
    if not isinstance(value, Mapping) or set(value) != {"schema_version", "outcome", "project_id", "bundle_digest", "enrollment_context_digest", "flags"}:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    if value.get("schema_version") != VERSION or value.get("outcome") != "replica_export_ready" or value.get("project_id") != project_id or value.get("bundle_digest") != bundle_digest or value.get("flags") != FLAGS:
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
    if value.get("enrollment_context_digest") != _inspection_context(project_id, identity, bundle_digest):
        raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")


def _bundle(value: Any) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Validate immutable transport syntax without deciding enrollment trust."""
    if not isinstance(value, Mapping) or set(value) != {"schema_version", "outcome", "project_id", "replica_identity", "authority_generation", "authority_head", "frontier", "events", "bundle_digest", "flags"} or value.get("schema_version") != VERSION or value.get("outcome") != "replica_export_ready" or value.get("flags") != FLAGS:
        raise ReplicaHold("hold_schema", "schema_invalid")
    if len(_canonical(value).encode()) > MAX_BYTES:
        raise ReplicaHold("hold_schema", "schema_invalid")
    project_id = _uuid(value["project_id"])
    identity = _replica_identity(value["replica_identity"], project_id)
    if not isinstance(value["authority_generation"], int) or isinstance(value["authority_generation"], bool) or value["authority_generation"] < 0:
        raise ReplicaHold("hold_schema", "schema_invalid")
    _hex(value["authority_head"])
    events = _validate_event_set(value["events"], project_id)
    if not isinstance(value["frontier"], list) or len(value["frontier"]) > MAX_EVENTS:
        raise ReplicaHold("hold_schema", "schema_invalid")
    frontier = [dict(zip(("replica_id", "replica_epoch", "origin_sequence", "event_id"), _identity_key(item))) for item in value["frontier"]]
    keys = {_identity_key(_identity(event)) for event in events}
    if any(_identity_key(item) not in keys for item in frontier):
        raise ReplicaHold("hold_missing_dependency", "missing_dependency")
    base = {"schema_version": VERSION, "outcome": "replica_export_ready", "project_id": project_id, "replica_identity": identity, "authority_generation": value["authority_generation"], "authority_head": value["authority_head"], "frontier": frontier, "events": sorted(events, key=lambda event: _identity_key(_identity(event))), "flags": dict(FLAGS)}
    if _hex(value["bundle_digest"], "hold_transport_integrity", "transport_integrity_invalid") != _digest(base):
        raise ReplicaHold("hold_transport_integrity", "transport_integrity_invalid")
    return project_id, identity, events


def export_bundle(authority_snapshot: Any, events: Any, replica_identity: Any, frontier: Any) -> dict[str, Any]:
    """Create a portable immutable envelope from an owner-provided snapshot.

    The snapshot is data already read by ``LocalCollaborationLedger``; this
    function intentionally has no path/project-root arguments and cannot open
    or write SQLite.
    """
    try:
        project_id, generation, head = _snapshot(authority_snapshot)
        identity = _replica_identity(replica_identity, project_id)
        event_set = _validate_event_set(events, project_id)
        if not isinstance(frontier, list) or len(frontier) > MAX_EVENTS:
            raise ReplicaHold("hold_schema", "schema_invalid")
        normalized_frontier = [dict(zip(("replica_id", "replica_epoch", "origin_sequence", "event_id"), _identity_key(item))) for item in frontier]
        keys = {_identity_key(_identity(event)) for event in event_set}
        if any(_identity_key(item) not in keys for item in normalized_frontier):
            raise ReplicaHold("hold_missing_dependency", "missing_dependency")
        ordered = sorted(event_set, key=lambda event: _identity_key(_identity(event)))
        base = {"schema_version": VERSION, "outcome": "replica_export_ready", "project_id": project_id, "replica_identity": identity, "authority_generation": generation, "authority_head": head, "frontier": normalized_frontier, "events": ordered, "flags": dict(FLAGS)}
        if len(_canonical(base).encode()) > MAX_BYTES:
            raise ReplicaHold("hold_schema", "schema_invalid")
        return {**base, "bundle_digest": _digest(base)}
    except ReplicaHold as exc:
        return _hold(exc)


def inspect_bundle(bundle: Any, enrolled_replicas: Any) -> dict[str, Any]:
    """Validate a received immutable envelope against prior enrollment receipts."""
    try:
        project_id, identity, events = _bundle(bundle)
        enrollment = _enrollments(enrolled_replicas, project_id).get((identity["replica_id"], identity["replica_epoch"]))
        if enrollment is None or enrollment["enrollment_receipt"] != identity["enrollment_receipt"]:
            raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
        return {"schema_version": VERSION, "outcome": "replica_export_ready", "project_id": project_id,
                "bundle_digest": bundle["bundle_digest"], "enrollment_context_digest": _inspection_context(project_id, identity, bundle["bundle_digest"]),
                "flags": dict(FLAGS)}
    except ReplicaHold as exc:
        pid = bundle.get("project_id") if isinstance(bundle, Mapping) and isinstance(bundle.get("project_id"), str) else None
        return _hold(exc, pid)


def plan_import(local_snapshot: Any, local_event_set: Any, bundle: Any, inspection_receipt: Any = None, *, transport_available: bool = True) -> dict[str, Any]:
    """Produce a read-only import plan; no event is appended or persisted."""
    try:
        project_id, generation, head = _snapshot(local_snapshot)
        local = _validate_event_set(local_event_set, project_id)
        if not transport_available:
            return _receipt("replica_offline", project_id, authority_generation=generation, authority_head=head, reason_code="replica_offline")
        if not isinstance(bundle, Mapping):
            raise ReplicaHold("hold_recovery_readback", "recovery_readback_required")
        bundle_project, identity_receipt, remote = _bundle(bundle)
        if bundle_project != project_id:
            raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
        _validated_inspection(inspection_receipt, project_id=project_id, identity=identity_receipt, bundle_digest=bundle["bundle_digest"])
        local_by_id = {_identity_key(_identity(event)): event for event in local}
        accepted, duplicates = [], []
        for event in remote:
            key = _identity_key(_identity(event)); prior = local_by_id.get(key)
            if prior is None:
                accepted.append(_identity(event))
            elif prior["event_digest"] == event["event_digest"]:
                duplicates.append(_identity(event))
            else:
                raise ReplicaHold("hold_transport_integrity", "transport_integrity_invalid")
        outcome = "replica_duplicate" if not accepted else "replica_import_plan_ready"
        return _receipt(outcome, project_id, authority_generation=generation, authority_head=head, bundle_digest=bundle["bundle_digest"], accepted_identities=accepted or None, duplicate_identities=duplicates or None)
    except ReplicaHold as exc:
        try:
            pid, generation, head = _snapshot(local_snapshot)
        except ReplicaHold:
            return _hold(exc)
        return _hold(exc, pid, authority_generation=generation, authority_head=head)


def reduce_converged_view(valid_event_set: Any) -> dict[str, Any]:
    """Derive the stable causal projection; it never changes a local ledger."""
    try:
        events = _validate_event_set(valid_event_set)
        if not events:
            return _receipt("replica_converged", str(uuid.UUID(int=0)), shared_view_digest=_digest([]))
        project_ids = {event["project_id"] for event in events}
        if len(project_ids) != 1:
            raise ReplicaHold("hold_replica_identity", "replica_identity_invalid")
        project_id = project_ids.pop()
        by_id = {_identity_key(_identity(event)): event for event in events}
        ready = sorted((key for key, event in by_id.items() if not event["causal_parents"])); ordered = []
        emitted = set()
        while ready:
            key = ready.pop(0)
            if key in emitted: continue
            emitted.add(key); ordered.append(by_id[key])
            for child_key, child in by_id.items():
                if child_key not in emitted and all(_identity_key(parent) in emitted for parent in child["causal_parents"]):
                    if child_key not in ready: ready.append(child_key)
            ready.sort()
        if len(ordered) != len(events):
            raise ReplicaHold("hold_missing_dependency", "missing_dependency")
        decisions: dict[str, list[dict[str, Any]]] = {}
        resolutions: dict[str, list[dict[str, Any]]] = {}
        for event in ordered:
            if event["event_type"] == "work_decision": decisions.setdefault(event["work_id"], []).append(event)
            elif event["event_type"] == "work_resolution": resolutions.setdefault(event["work_id"], []).append(event)
        def ancestors(key: tuple[str, int, int, str]) -> set[tuple[str, int, int, str]]:
            result: set[tuple[str, int, int, str]] = set()
            stack = [_identity_key(parent) for parent in by_id[key]["causal_parents"]]
            while stack:
                candidate = stack.pop()
                if candidate in result:
                    continue
                result.add(candidate)
                stack.extend(_identity_key(parent) for parent in by_id[candidate]["causal_parents"])
            return result
        conflicts = []
        for work_id, choices in decisions.items():
            if len({item["decision"] for item in choices}) > 1:
                required = {_identity_key(_identity(item)) for item in choices}
                resolved = any(required.issubset({_identity_key(ref) for ref in resolution["conflict_references"]})
                               and required.issubset(ancestors(_identity_key(_identity(resolution))))
                               for resolution in resolutions.get(work_id, []))
                if not resolved: conflicts.extend(_identity(item) for item in choices)
        if conflicts:
            return _receipt("hold_semantic_conflict", project_id, held_identities=conflicts, reason_code="semantic_conflict")
        view = [{"identity": _identity(event), "event_digest": event["event_digest"]} for event in ordered]
        return _receipt("replica_converged", project_id, shared_view_digest=_digest(view), accepted_identities=[_identity(event) for event in ordered])
    except ReplicaHold as exc:
        return _hold(exc)


class FakeReplicaTransport:
    """Explicit in-memory delivery seam; it has no retry or I/O behavior."""
    def __init__(self, available: bool = True):
        self.available = bool(available)

    def plan_delivery(self, local_snapshot: Any, local_event_set: Any, bundle: Any, inspection_receipt: Any = None) -> dict[str, Any]:
        return plan_import(local_snapshot, local_event_set, bundle, inspection_receipt, transport_available=self.available)
