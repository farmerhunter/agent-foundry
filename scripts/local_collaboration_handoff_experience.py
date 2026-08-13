"""Read-only, privacy-safe handoff status projection for ORCH-04 UX."""
from __future__ import annotations

import uuid
from typing import Any, Mapping

from local_collaboration_handoff import HandoffHold, read_handoff_state
from local_collaboration_handoff_bundle import read_owner_imported_handoff_projection
from local_collaboration_ledger import (
    LedgerBusyError, LedgerIdentityError, LedgerIntegrityError, LedgerPermissionError,
    LedgerSchemaError,
)

VERSION = "LocalCollaborationHandoffExperience-v1"
MODES = {"local_source", "imported_target"}


def _flags(*, owner_import_verified: bool = False) -> dict[str, bool]:
    return {"projection_only": True, "owner_import_verified": owner_import_verified,
            "transport_performed": False, "target_activation_authorized": False}


def _hold(project_id: str, mode: str, outcome: str, reason_code: str) -> dict[str, Any]:
    return {"schema_version": VERSION, "outcome": outcome, "project_id": project_id,
            "mode": mode, "status": "held", "next_action": "human_conflict_resolution_required"
            if outcome == "hold_conflict" else "inspect_owner_import_proof",
            "reason_code": reason_code, "target_activation_authorized": False, "flags": _flags()}


def _project_id(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("project_id_invalid") from exc


def _closed_args(mode: Any, bundle: Any, proof_ref: Any) -> str | None:
    if mode not in MODES:
        return "mode_invalid"
    if mode == "local_source" and (bundle is not None or proof_ref is not None):
        return "local_mode_auxiliary_input_forbidden"
    if mode == "imported_target" and (not isinstance(bundle, Mapping) or not isinstance(proof_ref, Mapping)):
        return "imported_bundle_and_locator_required"
    return None


def _local_projection(state) -> dict[str, Any]:
    handoff = state.handoff or {}
    phase, handoff_status = state.phase, handoff.get("status")
    if phase == "uninitialized":
        status, action = "local_enrollment_required", "enroll_active_device"
    elif phase == "active" and handoff_status == "cancelled":
        status, action = "handoff_cancelled_active", "continue_on_current_active_device"
    elif phase == "active" and handoff.get("takeover") is True and handoff_status == "target_active":
        status, action = "handoff_taken_over_active", "continue_on_current_active_device"
    elif phase == "active":
        status, action = "local_active", "continue_local_work"
    elif phase == "preparing":
        status, action = "handoff_preparing", "lock_source_then_export_bundle"
    elif phase == "source_locked" and handoff_status == "bundle_exported":
        status, action = "source_locked_bundle_exported", "retain_bundle_and_resolve_handoff"
    elif phase == "source_locked":
        status, action = "source_locked_export_bundle", "export_manual_bundle"
    else:
        return _hold(state.project_id, "local_source", "hold_conflict", "owner_handoff_held")
    result = {"schema_version": VERSION, "outcome": "local_ready", "project_id": state.project_id,
              "mode": "local_source", "status": status, "next_action": action,
              "target_activation_authorized": False, "flags": _flags()}
    if handoff.get("handoff_id") is not None:
        result["handoff_id"] = handoff["handoff_id"]
        result["source_generation"] = state.authority_generation
        result["source_head"] = state.authority_head
    return result


def project_handoff_experience(db_path, *, expected_project_id: str, mode: str,
                               bundle: Mapping[str, Any] | None = None,
                               proof_ref: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    """Project either local owner state or an owner-reconstructed A2 import.

    This is intentionally a read-only UI boundary.  In imported mode no A1
    replay can substitute for the A2 bundle-and-owner-receipt reconstruction.
    """
    try:
        project_id = _project_id(expected_project_id)
    except ValueError:
        return _hold("00000000-0000-0000-0000-000000000000", "local_source", "hold_project_identity", "project_id_invalid")
    reason = _closed_args(mode, bundle, proof_ref)
    if reason:
        return _hold(project_id, mode if mode in MODES else "local_source", "hold_schema", reason)
    try:
        if mode == "local_source":
            return _local_projection(read_handoff_state(db_path, expected_project_id=project_id))
        projection = read_owner_imported_handoff_projection(
            db_path, expected_project_id=project_id, bundle=bundle, proof_ref=proof_ref,
        )
        if projection.get("outcome") != "owner_import_verified":
            return _hold(project_id, mode, "hold_import_proof", projection.get("reason_code", "owner_proof_unavailable"))
        if projection.get("project_id") != project_id or projection.get("target_activation_authorized") is not False:
            return _hold(project_id, mode, "hold_import_proof", "owner_projection_invalid")
        return {"schema_version": VERSION, "outcome": "target_import_verified_activation_deferred",
                "project_id": project_id, "mode": "imported_target",
                "status": "target_import_verified_activation_deferred", "next_action": "keep_target_inactive",
                "handoff_id": projection["handoff_id"], "source_generation": projection["source_generation"],
                "source_head": projection["source_head"], "target_generation": projection["target_generation"],
                "target_head": projection["target_head"], "target_activation_authorized": False,
                "flags": _flags(owner_import_verified=True)}
    except HandoffHold as exc:
        return _hold(project_id, mode, "hold_owner_state", exc.reason_code)
    except (LedgerBusyError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return _hold(project_id, mode, "hold_owner_state", "owner_state_unavailable")


__all__ = ["project_handoff_experience"]
