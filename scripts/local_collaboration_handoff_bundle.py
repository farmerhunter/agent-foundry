"""Manual, metadata-only ORCH-05 handoff bundles.

This module is deliberately in-memory.  Callers choose how a returned bundle
is carried; it never copies SQLite files or performs device/transport I/O.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from local_collaboration_handoff import (
    HandoffHold, apply_handoff_transition, plan_handoff_transition,
    read_handoff_state, reduce_handoff_events,
)
from local_collaboration_ledger import (
    GENESIS, LedgerBusyError, LedgerConflictError, LedgerEvent, LedgerIdentityError,
    LedgerIntegrityError, LedgerPermissionError, LedgerSchemaError,
    LedgerStaleSnapshotError, LocalCollaborationLedger,
)

VERSION = "LocalCollaborationHandoffBundle-v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output", "secret", "token", "credential", "native_history", "native_thread_id", "username", "hostname", "machine", "machine_label", "path", "exception", "trusted", "approved", "verified", "authorized", "import_completed"}
MAX_EVENTS, MAX_BYTES, MAX_DEPTH = 100, 1024 * 1024, 12


class BundleHold(ValueError):
    def __init__(self, outcome: str, reason_code: str):
        self.outcome, self.reason_code = outcome, reason_code
        super().__init__(outcome)


class _FrozenDict(dict):
    def _blocked(self, *args, **kwargs):
        raise TypeError("immutable bundle")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise BundleHold("hold_schema", "schema_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _hex(value: Any, outcome="hold_schema") -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise BundleHold(outcome, "digest_invalid")
    return value


def _opaque(value: Any, outcome="hold_schema") -> str:
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise BundleHold(outcome, "opaque_invalid")
    return value


def _walk(value: Any, depth=0) -> None:
    if depth > MAX_DEPTH:
        raise BundleHold("hold_privacy", "privacy_rejected")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise BundleHold("hold_schema", "schema_invalid")
            if key.lower() in FORBIDDEN:
                raise BundleHold("hold_privacy", "privacy_rejected")
            _walk(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, depth + 1)
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise BundleHold("hold_schema", "schema_invalid")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _flags(**extra: bool) -> dict[str, bool]:
    result = {"owner_import_performed": False, "owner_readback_verified": False,
              "target_activation_authorized": False, "transport_performed": False}
    result.update(extra)
    return result


def _hold(project_id: str, outcome: str, reason: str) -> dict[str, Any]:
    return {"schema_version": VERSION, "outcome": outcome, "project_id": project_id,
            "reason_code": reason, "flags": _flags()}


def _event_record(event: LedgerEvent) -> dict[str, Any]:
    return {"sequence": event.sequence, "event_id": event.event_id, "event_type": event.event_type,
            "payload": json.loads(_canonical(event.payload)), "payload_hash": event.payload_hash,
            "previous_hash": event.previous_hash, "event_hash": event.event_hash,
            "created_at": event.created_at, "actor": event.actor, "source": event.source, "root": event.root}


def _event_input(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _json_value(record[key]) for key in ("event_type", "event_id", "payload", "actor", "source", "root")}


def _identity_digest(records) -> str:
    return _digest([{key: record[key] for key in ("sequence", "event_id", "payload_hash", "event_type", "actor", "source", "root")}
                    for record in records])


def _target_state_digest(events) -> str:
    return _digest({"generation": len(events), "head": events[-1].event_hash if events else GENESIS,
                    "identity_digest": _identity_digest([_event_record(event) for event in events])})


def _record_to_event(record: Any) -> LedgerEvent:
    required = {"sequence", "event_id", "event_type", "payload", "payload_hash", "previous_hash", "event_hash", "created_at", "actor", "source", "root"}
    if not isinstance(record, Mapping) or set(record) != required:
        raise BundleHold("hold_schema", "event_record_invalid")
    _walk(record)
    if not isinstance(record["sequence"], int) or isinstance(record["sequence"], bool) or record["sequence"] < 1:
        raise BundleHold("hold_schema", "event_sequence_invalid")
    for key in ("event_id", "payload_hash", "previous_hash", "event_hash"):
        _hex(record[key], "hold_package_integrity") if key != "event_id" else str(uuid.UUID(record[key]))
    if _digest(record["payload"]) != record["payload_hash"]:
        raise BundleHold("hold_package_integrity", "payload_hash_invalid")
    if not isinstance(record["event_type"], str) or not isinstance(record["root"], str):
        raise BundleHold("hold_schema", "event_record_invalid")
    if record["actor"] is not None and not isinstance(record["actor"], str):
        raise BundleHold("hold_schema", "event_record_invalid")
    if record["source"] is not None and not isinstance(record["source"], str):
        raise BundleHold("hold_schema", "event_record_invalid")
    expected_hash = _digest([record["sequence"], record["event_id"], record["event_type"], record["payload_hash"], record["previous_hash"], record["created_at"], record["actor"], record["source"], record["root"]])
    if expected_hash != record["event_hash"]:
        raise BundleHold("hold_package_integrity", "event_hash_invalid")
    return LedgerEvent(record["sequence"], record["event_id"], record["event_type"], _freeze(record["payload"]),
                       record["payload_hash"], record["previous_hash"], record["event_hash"], record["created_at"],
                       record["actor"], record["source"], record["root"])


def _bundle_core(bundle: Mapping[str, Any], *, require_marker=True) -> tuple[dict[str, Any], list[LedgerEvent], LedgerEvent]:
    required = {"schema_version", "project_id", "bundle_id", "handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch", "target_replica_epoch", "source_enrollment_id", "source_enrollment_digest", "target_enrollment_id", "target_enrollment_digest", "source_generation", "source_head", "source_state_digest", "frontier_digest", "content_manifest_digest", "events", "export_marker", "package_digest", "flags"}
    if not isinstance(bundle, Mapping) or set(bundle) != required or bundle.get("schema_version") != VERSION:
        raise BundleHold("hold_schema", "bundle_shape_invalid")
    _walk(bundle)
    if bundle.get("flags") != _flags():
        raise BundleHold("hold_schema", "flags_invalid")
    for key in ("bundle_id", "handoff_id", "source_replica_id", "target_replica_id", "source_enrollment_id", "target_enrollment_id"):
        _opaque(bundle.get(key))
    for key in ("source_enrollment_digest", "target_enrollment_digest", "source_head", "source_state_digest", "frontier_digest", "content_manifest_digest", "package_digest"):
        _hex(bundle.get(key), "hold_package_integrity")
    if not isinstance(bundle["source_generation"], int) or bundle["source_generation"] < 0:
        raise BundleHold("hold_schema", "source_generation_invalid")
    if any(not isinstance(bundle[key], int) or isinstance(bundle[key], bool) or bundle[key] < 1 for key in ("source_replica_epoch", "target_replica_epoch")):
        raise BundleHold("hold_schema", "replica_epoch_invalid")
    if not isinstance(bundle["events"], (list, tuple)) or not bundle["events"] or len(bundle["events"]) > MAX_EVENTS:
        raise BundleHold("hold_schema", "events_invalid")
    if len(_canonical(bundle).encode("utf-8")) > MAX_BYTES:
        raise BundleHold("hold_schema", "bundle_too_large")
    events = [_record_to_event(item) for item in bundle["events"]]
    marker = _record_to_event(bundle["export_marker"])
    manifest = {key: bundle[key] for key in required - {"events", "export_marker", "content_manifest_digest", "package_digest", "flags"}}
    if _digest({"header": manifest, "events": [_event_record(event) for event in events]}) != bundle["content_manifest_digest"]:
        raise BundleHold("hold_package_integrity", "manifest_digest_invalid")
    without_digest = {key: bundle[key] for key in required - {"package_digest"}}
    if _digest(without_digest) != bundle["package_digest"]:
        raise BundleHold("hold_package_integrity", "package_digest_invalid")
    if require_marker and marker.sequence != len(events) + 1:
        raise BundleHold("hold_package_integrity", "marker_position_invalid")
    reduce_handoff_events(bundle["project_id"], events + [marker], marker.sequence, marker.event_hash)
    return dict(bundle), events, marker


def _source_header(state) -> dict[str, Any]:
    handoff = state.handoff or {}
    enrollments = {item.replica_id: item for item in state.enrollments}
    source, target = handoff.get("source_replica_id"), handoff.get("target_replica_id")
    source_entry, target_entry = enrollments.get(source), enrollments.get(target)
    if state.phase != "source_locked" or handoff.get("status") != "source_locked" or source_entry is None or target_entry is None or source_entry.revoked or target_entry.revoked:
        raise BundleHold("hold_handoff_state", "source_locked_required")
    source_generation = handoff.get("source_generation")
    if not isinstance(source_generation, int) or isinstance(source_generation, bool) or source_generation < 0:
        raise BundleHold("hold_handoff_state", "source_frontier_generation_invalid")
    source_head = _hex(handoff.get("source_head"), "hold_handoff_state")
    return {"project_id": state.project_id, "handoff_id": handoff["handoff_id"], "source_replica_id": source,
            "target_replica_id": target, "source_replica_epoch": source_entry.replica_epoch,
            "target_replica_epoch": target_entry.replica_epoch, "source_enrollment_id": source_entry.enrollment_id,
            "source_enrollment_digest": source_entry.enrollment_digest, "target_enrollment_id": target_entry.enrollment_id,
            "target_enrollment_digest": target_entry.enrollment_digest, "source_generation": source_generation,
            "source_head": source_head, "source_state_digest": state.state_digest,
            "frontier_digest": handoff["frontier_digest"]}


def prepare_manual_bundle(source_ledger: LocalCollaborationLedger, *, expected_handoff_state) -> Mapping[str, Any]:
    """CAS-persist one source export marker and return an immutable package."""
    project_id = source_ledger.project_id
    try:
        snapshot = LocalCollaborationLedger.authority_snapshot(source_ledger.path, expected_project_id=project_id)
        state = read_handoff_state(source_ledger.path, expected_project_id=project_id)
        if (state.authority_generation, state.authority_head, state.state_digest) != (expected_handoff_state.authority_generation, expected_handoff_state.authority_head, expected_handoff_state.state_digest):
            # Receipt-loss retry is the one permitted recovery path: the exact
            # marker is the current tail and was committed immediately after
            # the expected source-locked snapshot.
            marker = snapshot.events[-1] if snapshot.events else None
            handoff = state.handoff or {}
            if (marker is None or marker.event_type != "handoff_bundle_exported" or marker.previous_hash != expected_handoff_state.authority_head
                    or marker.sequence != expected_handoff_state.authority_generation + 1
                    or handoff.get("status") != "bundle_exported"):
                raise BundleHold("hold_export_stale", "expected_state_mismatch")
            header = _source_header(expected_handoff_state)
            if handoff.get("bundle_id") is None or handoff.get("content_manifest_digest") is None:
                raise BundleHold("hold_readback_ambiguous", "export_marker_invalid")
            header["bundle_id"] = handoff["bundle_id"]
            records = [_event_record(event) for event in snapshot.events[:-1]]
            manifest = _digest({"header": {"schema_version": VERSION, **header}, "events": records})
            if manifest != handoff["content_manifest_digest"]:
                raise BundleHold("hold_readback_ambiguous", "export_marker_binding_invalid")
            bundle = {"schema_version": VERSION, **header, "content_manifest_digest": manifest, "events": records,
                      "export_marker": _event_record(marker), "flags": _flags()}
            bundle["package_digest"] = _digest(bundle)
            _bundle_core(bundle)
            return _freeze(bundle)
        if (snapshot.authority_generation, snapshot.authority_head) != (state.authority_generation, state.authority_head):
            raise BundleHold("hold_export_stale", "source_snapshot_stale")
        header = _source_header(state)
        records = [_event_record(event) for event in snapshot.events]
        manifest_header = {"schema_version": VERSION, **header,
                           "bundle_id": "bundle-" + _digest({"handoff": header["handoff_id"], "state": state.state_digest})[:48]}
        manifest = _digest({"header": manifest_header, "events": records})
        plan = plan_handoff_transition(state, {"transition": "bundle_exported", "project_id": project_id,
                                                "handoff_id": header["handoff_id"], "bundle_id": manifest_header["bundle_id"],
                                                "content_manifest_digest": manifest})
        if isinstance(plan, Mapping):
            return plan
        receipt = apply_handoff_transition(source_ledger, plan, expected_before=state)
        if receipt.get("outcome") != "bundle_exported":
            return receipt
        after_snapshot = LocalCollaborationLedger.authority_snapshot(source_ledger.path, expected_project_id=project_id)
        after_state = read_handoff_state(source_ledger.path, expected_project_id=project_id)
        if after_snapshot.authority_generation != state.authority_generation + 1 or after_state.handoff is None or after_state.handoff.get("content_manifest_digest") != manifest:
            raise BundleHold("hold_readback_ambiguous", "export_readback_invalid")
        marker = _event_record(after_snapshot.events[-1])
        bundle = {**manifest_header, "content_manifest_digest": manifest,
                  "events": records, "export_marker": marker, "flags": _flags()}
        bundle["package_digest"] = _digest(bundle)
        _bundle_core(bundle)
        return _freeze(bundle)
    except BundleHold as exc:
        return _hold(project_id, exc.outcome, exc.reason_code)
    except (LedgerStaleSnapshotError, LedgerConflictError):
        return _hold(project_id, "hold_export_stale", "conditional_stale")
    except LedgerBusyError:
        return _hold(project_id, "hold_owner_busy", "owner_busy")
    except LedgerPermissionError:
        return _hold(project_id, "hold_owner_permission", "owner_permission")
    except (LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return _hold(project_id, "hold_owner_integrity", "owner_integrity")


def inspect_manual_bundle(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        normalized, events, marker = _bundle_core(bundle)
        full = events + [marker]
        state = reduce_handoff_events(normalized["project_id"], full, marker.sequence, marker.event_hash)
        handoff = state.handoff or {}
        if state.phase != "source_locked" or handoff.get("status") != "bundle_exported":
            raise BundleHold("hold_handoff_state", "export_state_invalid")
        for key in ("handoff_id", "source_replica_id", "target_replica_id", "frontier_digest", "bundle_id", "content_manifest_digest"):
            if handoff.get(key) != normalized.get(key):
                raise BundleHold("hold_package_integrity", "export_marker_binding_invalid")
        return {"schema_version": VERSION, "outcome": "import_candidate", "project_id": normalized["project_id"],
                "bundle_id": normalized["bundle_id"], "package_digest": normalized["package_digest"],
                "handoff_id": normalized["handoff_id"], "source_state_digest": normalized["source_state_digest"],
                "owner_import_performed": False, "target_activation_authorized": False,
                "flags": _flags(owner_readback_verified=True)}
    except BundleHold as exc:
        project_id = bundle.get("project_id", "00000000-0000-0000-0000-000000000000") if isinstance(bundle, Mapping) else "00000000-0000-0000-0000-000000000000"
        return _hold(project_id, exc.outcome, exc.reason_code)


@dataclass(frozen=True)
class OwnerImportPlan:
    project_id: str
    package_digest: str
    expected_generation: int
    expected_head: str
    expected_before_state_digest: str
    missing_events: tuple[Mapping[str, Any], ...]
    receipt_event: Mapping[str, Any]
    imported_identity_digest: str


def _portable_equal(event: LedgerEvent, record: Mapping[str, Any]) -> bool:
    return _event_input(_event_record(event)) == _event_input(record)


def plan_owner_import(target_snapshot, bundle: Mapping[str, Any]) -> OwnerImportPlan | Mapping[str, Any]:
    project_id = target_snapshot.project_id if hasattr(target_snapshot, "project_id") else "00000000-0000-0000-0000-000000000000"
    try:
        normalized, events, marker = _bundle_core(bundle)
        candidate = inspect_manual_bundle(normalized)
        if candidate.get("outcome") != "import_candidate":
            return candidate
        if target_snapshot.project_id != normalized["project_id"]:
            raise BundleHold("hold_project_identity", "target_project_mismatch")
        records = list(normalized["events"]) + [normalized["export_marker"]]
        current = list(target_snapshot.events)
        if len(current) > len(records) or any(not _portable_equal(event, record) for event, record in zip(current, records)):
            raise BundleHold("hold_target_not_prefix", "target_prefix_invalid")
        missing = tuple(_event_input(record) for record in records[len(current):])
        full_set_digest = _identity_digest(records)
        suffix_digest = _identity_digest(records[len(current):])
        receipt_id = str(uuid.uuid5(uuid.UUID(normalized["project_id"]), "handoff-import:" + normalized["package_digest"]))
        payload = {"schema_version": VERSION, "project_id": normalized["project_id"], "bundle_id": normalized["bundle_id"],
                   "handoff_id": normalized["handoff_id"], "source_replica_id": normalized["source_replica_id"], "target_replica_id": normalized["target_replica_id"],
                   "source_replica_epoch": normalized["source_replica_epoch"], "target_replica_epoch": normalized["target_replica_epoch"],
                   "source_enrollment_id": normalized["source_enrollment_id"], "source_enrollment_digest": normalized["source_enrollment_digest"],
                   "target_enrollment_id": normalized["target_enrollment_id"], "target_enrollment_digest": normalized["target_enrollment_digest"],
                   "package_digest": normalized["package_digest"], "content_manifest_digest": normalized["content_manifest_digest"],
                   "source_generation": normalized["source_generation"], "source_head": normalized["source_head"],
                   "source_state_digest": normalized["source_state_digest"], "frontier_digest": normalized["frontier_digest"],
                   "target_before_generation": target_snapshot.authority_generation, "target_before_head": target_snapshot.authority_head,
                   "target_before_state_digest": _target_state_digest(current),
                   "full_set_identity_digest": full_set_digest, "imported_suffix_identity_digest": suffix_digest}
        receipt = {"event_type": "handoff_import_committed", "event_id": receipt_id, "payload": payload,
                   "actor": "owner", "source": "orch05_handoff_bundle", "root": normalized["project_id"]}
        return OwnerImportPlan(normalized["project_id"], normalized["package_digest"], target_snapshot.authority_generation,
                               target_snapshot.authority_head, _digest({"generation": target_snapshot.authority_generation, "head": target_snapshot.authority_head}),
                               missing, _freeze(receipt), full_set_digest)
    except BundleHold as exc:
        return _hold(project_id, exc.outcome, exc.reason_code)


def _proof_from(plan: OwnerImportPlan, result, after) -> Mapping[str, Any]:
    ref = result.event_refs[-1]
    return {"schema_version": VERSION, "outcome": "owner_import_committed", "project_id": plan.project_id,
                    "package_digest": plan.package_digest, "receipt_event_id": plan.receipt_event["event_id"],
                    "receipt_event_hash": ref[3], "target_generation": after.authority_generation, "target_head": after.authority_head,
                    "full_set_identity_digest": plan.imported_identity_digest, "owner_import_performed": result.mutation_performed,
                    "target_activation_authorized": False, "flags": _flags(owner_import_performed=result.mutation_performed, owner_readback_verified=True)}


def apply_owner_import(target_ledger: LocalCollaborationLedger, plan: OwnerImportPlan, *, expected_before) -> Mapping[str, Any]:
    project_id = target_ledger.project_id
    try:
        if not isinstance(plan, OwnerImportPlan) or plan.project_id != project_id:
            raise BundleHold("hold_schema", "plan_invalid")
        if not hasattr(expected_before, "authority_generation") or not hasattr(expected_before, "authority_head") or (expected_before.authority_generation, expected_before.authority_head) != (plan.expected_generation, plan.expected_head):
            raise BundleHold("hold_target_stale", "expected_before_mismatch")
        current = LocalCollaborationLedger.authority_snapshot(target_ledger.path, expected_project_id=project_id)
        if (current.authority_generation, current.authority_head) != (plan.expected_generation, plan.expected_head):
            # Exact post-commit retry is intentionally delegated to LedgerStore only when its full batch is still the tail.
            batch = list(plan.missing_events) + [dict(plan.receipt_event)]
            result = target_ledger.conditional_append_batch(batch, expected_generation=plan.expected_generation, expected_head=plan.expected_head)
            if result.status != "duplicate":
                raise BundleHold("hold_target_stale", "target_before_mismatch")
        else:
            result = target_ledger.conditional_append_batch(list(plan.missing_events) + [dict(plan.receipt_event)], expected_generation=plan.expected_generation, expected_head=plan.expected_head)
        if result.status not in {"appended", "duplicate"} or len(result.event_refs) != len(plan.missing_events) + 1 or result.event_refs[-1][1] != plan.receipt_event["event_id"]:
            raise BundleHold("hold_readback_ambiguous", "import_receipt_invalid")
        after = LocalCollaborationLedger.authority_snapshot(target_ledger.path, expected_project_id=project_id)
        if (after.authority_generation, after.authority_head) != (result.generation, result.head) or after.events[-1].event_id != plan.receipt_event["event_id"]:
            raise BundleHold("hold_readback_ambiguous", "import_readback_invalid")
        return _proof_from(plan, result, after)
    except BundleHold as exc:
        return _hold(project_id, exc.outcome, exc.reason_code)
    except LedgerStaleSnapshotError:
        return _hold(project_id, "hold_target_stale", "conditional_stale")
    except LedgerBusyError:
        return _hold(project_id, "hold_owner_busy", "owner_busy")
    except LedgerPermissionError:
        return _hold(project_id, "hold_owner_permission", "owner_permission")
    except (LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError, LedgerConflictError):
        return _hold(project_id, "hold_owner_integrity", "owner_integrity")


def read_owner_imported_handoff_projection(db_path, *, expected_project_id: str, bundle: Mapping[str, Any], proof_ref: Mapping[str, Any]) -> Mapping[str, Any]:
    """Reconstruct an owner import proof from the bundle and current ledger.

    ``proof_ref`` is deliberately only a locator.  No caller-provided digest or
    claimed verification can replace revalidating the immutable package and the
    exact current target receipt tail.
    """
    try:
        if not isinstance(proof_ref, Mapping) or set(proof_ref) != {"project_id", "receipt_event_id", "receipt_event_hash", "package_digest"}:
            raise BundleHold("hold_schema", "proof_locator_invalid")
        if proof_ref["project_id"] != expected_project_id:
            raise BundleHold("hold_project_identity", "proof_project_mismatch")
        _hex(proof_ref["receipt_event_hash"], "hold_proof_missing_or_stale"); _hex(proof_ref["package_digest"], "hold_proof_missing_or_stale")
        str(uuid.UUID(proof_ref["receipt_event_id"]))
        normalized, source_events, marker = _bundle_core(bundle)
        candidate = inspect_manual_bundle(normalized)
        if candidate.get("outcome") != "import_candidate" or normalized["project_id"] != expected_project_id:
            raise BundleHold("hold_proof_missing_or_stale", "bundle_not_candidate")
        if normalized["package_digest"] != proof_ref["package_digest"]:
            raise BundleHold("hold_proof_missing_or_stale", "package_locator_mismatch")
        source_locked = reduce_handoff_events(expected_project_id, source_events,
                                              source_events[-1].sequence, source_events[-1].event_hash)
        exported = reduce_handoff_events(expected_project_id, source_events + [marker], marker.sequence, marker.event_hash)
        source_handoff, exported_handoff = source_locked.handoff or {}, exported.handoff or {}
        if (source_locked.phase != "source_locked" or source_handoff.get("status") != "source_locked"
                or source_handoff.get("source_generation") != normalized["source_generation"]
                or source_handoff.get("source_head") != normalized["source_head"]
                or source_locked.state_digest != normalized["source_state_digest"]
                or exported_handoff.get("status") != "bundle_exported"):
            raise BundleHold("hold_proof_missing_or_stale", "source_reduction_invalid")
        snapshot = LocalCollaborationLedger.authority_snapshot(db_path, expected_project_id=expected_project_id)
        if not snapshot.events or snapshot.events[-1].event_id != proof_ref["receipt_event_id"] or snapshot.events[-1].event_hash != proof_ref["receipt_event_hash"]:
            raise BundleHold("hold_proof_missing_or_stale", "proof_not_current_tail")
        receipt = snapshot.events[-1]
        if receipt.event_type != "handoff_import_committed" or receipt.root != expected_project_id or not isinstance(receipt.payload, Mapping):
            raise BundleHold("hold_proof_missing_or_stale", "receipt_invalid")
        payload = receipt.payload
        if payload.get("schema_version") != VERSION or payload.get("package_digest") != proof_ref["package_digest"] or payload.get("project_id") != expected_project_id:
            raise BundleHold("hold_proof_missing_or_stale", "receipt_binding_invalid")
        imported = list(snapshot.events[: -1])
        records = list(normalized["events"]) + [normalized["export_marker"]]
        before_generation = payload.get("target_before_generation")
        if (not isinstance(before_generation, int) or isinstance(before_generation, bool) or before_generation < 0
                or before_generation > len(records) or len(imported) != len(records)
                or any(not _portable_equal(event, record) for event, record in zip(imported, records))):
            raise BundleHold("hold_proof_missing_or_stale", "target_prefix_or_suffix_invalid")
        prefix = imported[:before_generation]
        prefix_head = prefix[-1].event_hash if prefix else GENESIS
        if (payload.get("target_before_head") != prefix_head
                or payload.get("target_before_state_digest") != _target_state_digest(prefix)):
            raise BundleHold("hold_proof_missing_or_stale", "target_before_binding_invalid")
        if payload.get("full_set_identity_digest") != _identity_digest(records):
            raise BundleHold("hold_proof_missing_or_stale", "full_set_identity_invalid")
        if payload.get("imported_suffix_identity_digest") != _identity_digest(records[before_generation:]):
            raise BundleHold("hold_proof_missing_or_stale", "imported_suffix_identity_invalid")
        required = {"bundle_id", "handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch",
                    "target_replica_epoch", "source_enrollment_id", "source_enrollment_digest", "target_enrollment_id",
                    "target_enrollment_digest", "content_manifest_digest", "source_generation", "source_head",
                    "source_state_digest", "frontier_digest", "target_before_generation", "target_before_head",
                    "target_before_state_digest", "full_set_identity_digest", "imported_suffix_identity_digest"}
        if set(payload) != required | {"schema_version", "project_id", "package_digest"}:
            raise BundleHold("hold_proof_missing_or_stale", "receipt_shape_invalid")
        for key in ("bundle_id", "handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch",
                    "target_replica_epoch", "source_enrollment_id", "source_enrollment_digest", "target_enrollment_id",
                    "target_enrollment_digest", "content_manifest_digest", "source_generation", "source_head",
                    "source_state_digest", "frontier_digest"):
            if payload.get(key) != normalized.get(key):
                raise BundleHold("hold_proof_missing_or_stale", "receipt_bundle_binding_invalid")
        if any(source_handoff.get(key) != normalized.get(key) for key in ("handoff_id", "source_replica_id", "target_replica_id", "frontier_digest")):
            raise BundleHold("hold_proof_missing_or_stale", "handoff_binding_invalid")
        enrollments = {entry.replica_id: entry for entry in source_locked.enrollments}
        for prefix_name, replica in (("source", normalized["source_replica_id"]), ("target", normalized["target_replica_id"])):
            entry = enrollments.get(replica)
            if entry is None or entry.revoked or entry.replica_epoch != normalized[prefix_name + "_replica_epoch"] or entry.enrollment_id != normalized[prefix_name + "_enrollment_id"] or entry.enrollment_digest != normalized[prefix_name + "_enrollment_digest"]:
                raise BundleHold("hold_proof_missing_or_stale", "enrollment_binding_invalid")
        return {"schema_version": VERSION, "outcome": "owner_import_verified", "project_id": expected_project_id,
                "bundle_id": normalized["bundle_id"], "handoff_id": normalized["handoff_id"],
                "phase": exported.phase, "handoff_status": exported_handoff["status"],
                "source_generation": normalized["source_generation"], "source_head": normalized["source_head"],
                "source_state_digest": normalized["source_state_digest"], "frontier_digest": normalized["frontier_digest"],
                "target_generation": snapshot.authority_generation, "target_head": snapshot.authority_head,
                "receipt_event_id": receipt.event_id, "package_digest": proof_ref["package_digest"],
                "owner_import_verified": True, "target_activation_authorized": False,
                "flags": _flags(owner_readback_verified=True)}
    except BundleHold as exc:
        return _hold(expected_project_id, exc.outcome, exc.reason_code)
    except (LedgerBusyError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return _hold(expected_project_id, "hold_proof_missing_or_stale", "owner_snapshot_failed")


def verify_owner_import_proof(db_path, *, expected_project_id: str, bundle: Mapping[str, Any], proof_ref: Mapping[str, Any]) -> Mapping[str, Any]:
    """Compatibility name for the one owner-backed imported-handoff projection."""
    return read_owner_imported_handoff_projection(
        db_path, expected_project_id=expected_project_id, bundle=bundle, proof_ref=proof_ref,
    )


__all__ = ["BundleHold", "OwnerImportPlan", "apply_owner_import", "inspect_manual_bundle", "plan_owner_import", "prepare_manual_bundle", "read_owner_imported_handoff_projection", "verify_owner_import_proof"]
