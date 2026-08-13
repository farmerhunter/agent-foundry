"""Read-only, privacy-safe handoff status projection for ORCH-04 UX."""
from __future__ import annotations

import uuid
import re
from typing import Any, Mapping

from local_collaboration_handoff import HandoffHold, read_handoff_state
from local_collaboration_handoff_bundle import read_owner_imported_handoff_projection
from local_collaboration_ledger import (
    LedgerBusyError, LedgerIdentityError, LedgerIntegrityError, LedgerPermissionError,
    LedgerSchemaError,
)

VERSION = "LocalCollaborationHandoffExperience-v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
BUNDLE_KEYS = {"schema_version", "project_id", "bundle_id", "handoff_id", "source_replica_id", "target_replica_id", "source_replica_epoch", "target_replica_epoch", "source_enrollment_id", "source_enrollment_digest", "target_enrollment_id", "target_enrollment_digest", "source_generation", "source_head", "source_state_digest", "frontier_digest", "content_manifest_digest", "events", "export_marker", "package_digest", "flags"}
PROOF_KEYS = {"project_id", "receipt_event_id", "receipt_event_hash", "package_digest"}


class _FrozenDict(dict):
    def _blocked(self, *args, **kwargs):
        raise TypeError("immutable handoff experience")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _base(project_id: str, state: str, next_action: str, **extra: Any) -> Mapping[str, Any]:
    return _freeze({"schema_version": VERSION, "project_id": project_id,
                    "experience_state": state, "next_action": next_action,
                    "status_only": True, "mutation_performed": False,
                    "transport_performed": False, "target_activation_performed": False,
                    "automatic_recovery_performed": False, **extra})


def _hold(project_id: str, reason_code: str) -> Mapping[str, Any]:
    return _base(project_id, "held", "resolve_conflict_or_recover_owner_state", reason_code=reason_code)


def _project_id(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("project_id_invalid") from exc


def _hex(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def _opaque(value: Any) -> bool:
    return isinstance(value, str) and bool(OPAQUE.fullmatch(value))


def _valid_proof_locator(proof_ref: Any, project_id: str) -> bool:
    if not isinstance(proof_ref, Mapping) or set(proof_ref) != PROOF_KEYS or proof_ref.get("project_id") != project_id:
        return False
    try:
        uuid.UUID(proof_ref["receipt_event_id"])
    except (ValueError, TypeError, AttributeError):
        return False
    return _hex(proof_ref.get("receipt_event_hash")) and _hex(proof_ref.get("package_digest"))


def _valid_bundle_shape(bundle: Any, project_id: str) -> bool:
    if not isinstance(bundle, Mapping) or set(bundle) != BUNDLE_KEYS or bundle.get("schema_version") != "LocalCollaborationHandoffBundle-v1" or bundle.get("project_id") != project_id:
        return False
    if not all(_opaque(bundle.get(key)) for key in ("bundle_id", "handoff_id", "source_replica_id", "target_replica_id", "source_enrollment_id", "target_enrollment_id")):
        return False
    if not all(_hex(bundle.get(key)) for key in ("source_enrollment_digest", "target_enrollment_digest", "source_head", "source_state_digest", "frontier_digest", "content_manifest_digest", "package_digest")):
        return False
    if any(not isinstance(bundle.get(key), int) or isinstance(bundle[key], bool) or bundle[key] < minimum
           for key, minimum in (("source_replica_epoch", 1), ("target_replica_epoch", 1), ("source_generation", 0))):
        return False
    return (isinstance(bundle.get("events"), (list, tuple)) and bool(bundle["events"])
            and isinstance(bundle.get("export_marker"), Mapping) and isinstance(bundle.get("flags"), Mapping))


def _local_projection(state) -> Mapping[str, Any]:
    handoff = state.handoff or {}
    common = {"authority_generation": state.authority_generation, "authority_head": state.authority_head,
              "state_digest": state.state_digest}
    if state.active_replica_id is not None:
        common["active_replica_id"] = state.active_replica_id
    if handoff.get("handoff_id") is not None:
        common["handoff_id"] = handoff["handoff_id"]
        for key in ("source_replica_id", "target_replica_id", "frontier_digest"):
            if handoff.get(key) is not None:
                common[key] = handoff[key]
    if state.phase == "uninitialized":
        return _hold(state.project_id, "active_device_enrollment_required")
    if state.phase == "active" and handoff.get("status") == "cancelled":
        return _base(state.project_id, "cancelled", "continue_single_device", **common)
    if state.phase == "active" and handoff.get("takeover") is True and handoff.get("status") == "target_active":
        return _base(state.project_id, "taken_over", "continue_single_device", **common)
    if state.phase == "active" and handoff.get("status") == "target_active":
        return _base(state.project_id, "target_active", "none", **common)
    if state.phase == "active":
        return _base(state.project_id, "single_device_active", "continue_single_device", **common)
    if state.phase == "preparing":
        return _base(state.project_id, "handoff_preparing", "lock_source_after_review", **common)
    if state.phase == "source_locked" and handoff.get("status") == "bundle_exported":
        return _base(state.project_id, "bundle_ready_for_manual_transfer", "transfer_and_owner_import_bundle", **common)
    if state.phase == "source_locked":
        return _base(state.project_id, "source_locked", "export_manual_bundle", **common)
    return _hold(state.project_id, "owner_handoff_held")


def read_handoff_experience(db_path, *, expected_project_id: str, bundle: Mapping[str, Any] | None = None,
                            proof_ref: Mapping[str, Any] | None = None, **claims: Any) -> Mapping[str, Any]:
    """Return local A1 state, or an A2 owner-verified imported projection.

    Presence of *both* bundle and proof locator selects imported mode.  Caller
    claims never select a mode or establish imported authority.
    """
    try:
        project_id = _project_id(expected_project_id)
    except ValueError:
        return _hold("00000000-0000-0000-0000-000000000000", "project_id_invalid")
    if claims or (bundle is None) != (proof_ref is None):
        return _hold(project_id, "selection_or_claim_invalid")
    try:
        if bundle is None:
            return _local_projection(read_handoff_state(db_path, expected_project_id=project_id))
        if not _valid_bundle_shape(bundle, project_id) or not _valid_proof_locator(proof_ref, project_id):
            return _hold(project_id, "import_bundle_or_locator_invalid")
        projection = read_owner_imported_handoff_projection(
            db_path, expected_project_id=project_id, bundle=bundle, proof_ref=proof_ref,
        )
        if not isinstance(projection, Mapping) or projection.get("outcome") != "owner_import_verified":
            return _hold(project_id, "owner_import_proof_unavailable")
        if projection.get("project_id") != project_id or projection.get("target_activation_authorized") is not False:
            return _hold(project_id, "owner_import_projection_invalid")
        return _base(project_id, "target_import_verified_activation_deferred", "request_later_target_activation_gate",
                     handoff_id=projection["handoff_id"], source_generation=projection["source_generation"],
                     source_head=projection["source_head"], source_state_digest=projection["source_state_digest"],
                     frontier_digest=projection["frontier_digest"], target_generation=projection["target_generation"],
                     target_head=projection["target_head"], owner_import_verified=True,
                     target_activation_authorized=False)
    except (HandoffHold, ValueError, TypeError, KeyError):
        return _hold(project_id, "owner_import_proof_unavailable" if bundle is not None else "owner_state_unavailable")
    except (LedgerBusyError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return _hold(project_id, "owner_state_unavailable")


__all__ = ["read_handoff_experience"]
