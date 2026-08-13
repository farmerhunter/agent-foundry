"""One-step, owner-backed ORCH-05 recovery and device-lifecycle facade.

This module never opens backup files, copies SQLite files, or performs
transport.  It composes the public A1/A2 owner APIs and keeps recovery actions
explicitly one-step and Human-decision-bound.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import read_owner_imported_handoff_projection, read_owner_target_activation
from local_collaboration_ledger import LocalCollaborationLedger

VERSION = "LocalCollaborationRecovery-v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
FORBIDDEN = {"prompt", "transcript", "token", "credential", "secret", "path", "hostname", "username", "verified", "authorized"}


class RecoveryHold(ValueError):
    def __init__(self, outcome: str, reason_code: str):
        self.outcome, self.reason_code = outcome, reason_code
        super().__init__(outcome)


class _FrozenDict(dict):
    def _blocked(self, *args, **kwargs):
        raise TypeError("immutable recovery result")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


class _FrozenList(list):
    def _blocked(self, *args, **kwargs):
        raise TypeError("immutable recovery result")
    __setitem__ = __delitem__ = __iadd__ = __imul__ = append = clear = extend = insert = pop = remove = reverse = sort = _blocked


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return _FrozenList(_freeze(item) for item in value)
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RecoveryHold("hold_schema", "schema_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _walk(value: Any, depth: int = 0) -> None:
    if depth > 10:
        raise RecoveryHold("hold_privacy", "privacy_or_depth_rejected")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise RecoveryHold("hold_schema", "schema_invalid")
            if key.lower() in FORBIDDEN:
                raise RecoveryHold("hold_privacy", "privacy_rejected")
            _walk(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, depth + 1)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise RecoveryHold("hold_schema", "schema_invalid")


def _opaque(value: Any, outcome: str = "hold_schema") -> str:
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise RecoveryHold(outcome, "opaque_invalid")
    return value


def _hex(value: Any, outcome: str = "hold_schema") -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise RecoveryHold(outcome, "digest_invalid")
    return value


def _flags(*, mutation_performed: bool = False, owner_readback_verified: bool = False,
           backup_performed: bool = False, restore_performed: bool = False) -> dict[str, bool]:
    return {"mutation_performed": mutation_performed, "owner_readback_verified": owner_readback_verified,
            "backup_performed": backup_performed, "restore_performed": restore_performed, "transport_performed": False,
            "source_unlock_performed": False, "target_activation_performed": False}


def _hold(project_id: str, outcome: str, reason_code: str) -> dict[str, Any]:
    return _freeze({"schema_version": VERSION, "outcome": outcome, "project_id": project_id,
                    "reason_code": reason_code, "flags": _flags()})


@dataclass(frozen=True)
class RecoveryPlan:
    action: str
    project_id: str
    decision_id: str
    decision_digest: str
    expected_generation: int
    expected_head: str
    request_digest: str
    owner_plan: Any
    target_replica_id: str | None = None
    locator_digest: str | None = None


def _decision(decision: Mapping[str, Any]) -> tuple[str, str]:
    if not isinstance(decision, Mapping) or set(decision) != {"decision_id", "decision_digest"}:
        raise RecoveryHold("hold_decision_invalid", "decision_shape_invalid")
    return _opaque(decision["decision_id"], "hold_decision_invalid"), _hex(decision["decision_digest"], "hold_decision_invalid")


def _projection_context(db_path, project_id: str, bundle: Mapping[str, Any], proof_ref: Mapping[str, Any], activation_ref: Mapping[str, Any] | None):
    projection = read_owner_imported_handoff_projection(db_path, expected_project_id=project_id, bundle=bundle, proof_ref=proof_ref)
    if projection.get("outcome") != "owner_import_verified":
        raise RecoveryHold("hold_owner_proof_unavailable", projection.get("reason_code", "owner_projection_unavailable"))
    target_state = read_handoff_state(db_path, expected_project_id=project_id)
    if (target_state.authority_generation, target_state.authority_head) != (projection["target_generation"], projection["target_head"]):
        raise RecoveryHold("hold_target_stale", "target_pair_drift")
    if target_state.phase != "source_locked" or not target_state.handoff:
        raise RecoveryHold("hold_owner_proof_unavailable", "target_handoff_unavailable")
    handoff = target_state.handoff
    for key in ("handoff_id", "source_replica_id", "target_replica_id", "frontier_digest", "source_generation", "source_head", "source_prefix_identity"):
        if handoff.get(key) != projection.get(key):
            raise RecoveryHold("hold_owner_proof_unavailable", "projection_binding_invalid")
    enrollments = {entry.replica_id: entry for entry in target_state.enrollments}
    for prefix in ("source", "target"):
        entry = enrollments.get(projection[prefix + "_replica_id"])
        if (entry is None or entry.revoked or entry.replica_epoch != projection[prefix + "_replica_epoch"]
                or entry.enrollment_id != projection[prefix + "_enrollment_id"]
                or entry.enrollment_digest != projection[prefix + "_enrollment_digest"]):
            raise RecoveryHold("hold_owner_proof_unavailable", "target_enrollment_binding_invalid")
    if activation_ref is not None:
        activation = read_owner_target_activation(db_path, expected_project_id=project_id, bundle=bundle, proof_ref=proof_ref, activation_ref=activation_ref)
        if activation.get("outcome") != "owner_target_activated":
            raise RecoveryHold("hold_owner_proof_unavailable", activation.get("reason_code", "activation_unavailable"))
    return projection, target_state


def read_recovery_summary(db_path, *, expected_project_id: str, bundle: Mapping[str, Any] | None = None,
                          proof_ref: Mapping[str, Any] | None = None, activation_ref: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    """Read only.  Caller evidence is a locator; owner APIs revalidate it."""
    try:
        state = read_handoff_state(db_path, expected_project_id=expected_project_id)
        result = {"schema_version": VERSION, "outcome": "recovery_ready", "project_id": expected_project_id,
                  "generation": state.authority_generation, "head": state.authority_head,
                  "phase": state.phase, "active_replica_id": state.active_replica_id,
                  "recovery_actions": ["fresh_backup", "fresh_target_restore", "pre_export_cancel", "inactive_revoke", "target_takeover"],
                  "flags": _flags(owner_readback_verified=True)}
        if bundle is not None or proof_ref is not None:
            if bundle is None or proof_ref is None:
                raise RecoveryHold("hold_schema", "bundle_proof_pair_required")
            projection, target = _projection_context(db_path, expected_project_id, bundle, proof_ref, activation_ref)
            result.update({"outcome": "target_import_recovery_ready", "target_replica_id": projection["target_replica_id"],
                           "source_replica_id": projection["source_replica_id"], "source_generation": projection["source_generation"],
                           "source_head": projection["source_head"], "source_prefix_identity": projection["source_prefix_identity"],
                           "frontier_digest": projection["frontier_digest"], "target_generation": target.authority_generation,
                           "target_head": target.authority_head, "import_receipt_event_id": projection["receipt_event_id"]})
        return _freeze(result)
    except RecoveryHold as exc:
        return _hold(expected_project_id, exc.outcome, exc.reason_code)
    except Exception:
        return _hold(expected_project_id, "hold_owner_read_unavailable", "owner_read_unavailable")


def plan_recovery_action(db_path, *, expected_project_id: str, action: str, decision: Mapping[str, Any],
                         bundle: Mapping[str, Any] | None = None, proof_ref: Mapping[str, Any] | None = None,
                         activation_ref: Mapping[str, Any] | None = None, replica_id: str | None = None,
                         backup_locator: str | None = None, restore_locator: str | None = None,
                         fresh_target_locator: str | None = None) -> RecoveryPlan | Mapping[str, Any]:
    """Plan exactly one owner action; backup/restore are intentionally HDC-only."""
    try:
        _walk(decision)
        decision_id, decision_digest = _decision(decision)
        if action not in {"fresh_backup", "fresh_target_restore", "pre_export_cancel", "inactive_revoke", "target_takeover"}:
            raise RecoveryHold("hold_schema", "action_invalid")
        if action in {"fresh_backup", "fresh_target_restore"}:
            locator = backup_locator if action == "fresh_backup" else restore_locator
            if not isinstance(locator, str) or not locator or (action == "fresh_target_restore" and (not isinstance(fresh_target_locator, str) or not fresh_target_locator)):
                raise RecoveryHold("hold_schema", "fresh_locator_required")
            # The locator itself remains caller-private: only its digest enters
            # the portable plan/receipt boundary.
            state = read_handoff_state(db_path, expected_project_id=expected_project_id)
            request_digest = _digest({"action": action, "project_id": expected_project_id, "decision_id": decision_id,
                                      "decision_digest": decision_digest, "generation": state.authority_generation,
                                      "head": state.authority_head, "locator_digest": _digest(locator),
                                      "target_locator_digest": _digest(fresh_target_locator) if action == "fresh_target_restore" else None})
            return RecoveryPlan(action, expected_project_id, decision_id, decision_digest, state.authority_generation,
                                state.authority_head, request_digest, None, None,
                                _digest(locator + "|" + (fresh_target_locator or "")))
        state = read_handoff_state(db_path, expected_project_id=expected_project_id)
        owner_plan = None
        target_id = None
        if action == "pre_export_cancel":
            if not state.handoff or state.handoff.get("status") == "bundle_exported":
                raise RecoveryHold("hold_cancellation_unproven", "post_export_return_proof_required")
            request = {"transition": "cancel", "project_id": expected_project_id, "handoff_id": state.handoff["handoff_id"],
                       "cancellation_evidence": "bundle_not_released", "decision_id": decision_id, "decision_digest": decision_digest}
            owner_plan = plan_handoff_transition(state, request)
        elif action == "inactive_revoke":
            target_id = _opaque(replica_id, "hold_enrollment")
            request = {"transition": "revoke_inactive", "project_id": expected_project_id, "replica_id": target_id,
                       "decision_id": decision_id, "decision_digest": decision_digest}
            owner_plan = plan_handoff_transition(state, request)
        else:
            if bundle is None or proof_ref is None:
                raise RecoveryHold("hold_schema", "bundle_proof_pair_required")
            projection, target_state = _projection_context(db_path, expected_project_id, bundle, proof_ref, activation_ref)
            target_id = projection["target_replica_id"]
            if replica_id is not None and _opaque(replica_id, "hold_enrollment") != target_id:
                raise RecoveryHold("hold_enrollment", "caller_target_mismatch")
            request = {"transition": "takeover", "project_id": expected_project_id, "target_replica_id": target_id,
                       "prior_frontier_digest": projection["frontier_digest"], "decision_id": decision_id, "decision_digest": decision_digest}
            state = target_state
            owner_plan = plan_handoff_transition(state, request)
        if isinstance(owner_plan, Mapping):
            raise RecoveryHold(owner_plan.get("outcome", "hold_owner_read_unavailable"), owner_plan.get("reason_code", "owner_plan_unavailable"))
        request_digest = _digest({"action": action, "project_id": expected_project_id, "decision_id": decision_id,
                                  "decision_digest": decision_digest, "generation": state.authority_generation, "head": state.authority_head,
                                  "owner_request": owner_plan.request_digest})
        return RecoveryPlan(action, expected_project_id, decision_id, decision_digest, state.authority_generation,
                            state.authority_head, request_digest, owner_plan, target_id)
    except RecoveryHold as exc:
        return _hold(expected_project_id, exc.outcome, exc.reason_code)
    except Exception:
        return _hold(expected_project_id, "hold_owner_read_unavailable", "owner_read_unavailable")


def apply_recovery_action(ledger: LocalCollaborationLedger, plan: RecoveryPlan, *, decision: Mapping[str, Any],
                          bundle: Mapping[str, Any] | None = None, proof_ref: Mapping[str, Any] | None = None,
                          activation_ref: Mapping[str, Any] | None = None, backup_locator: str | None = None,
                          restore_locator: str | None = None, fresh_target_locator: str | None = None) -> Mapping[str, Any]:
    try:
        if not isinstance(plan, RecoveryPlan) or plan.project_id != ledger.project_id or _decision(decision) != (plan.decision_id, plan.decision_digest):
            raise RecoveryHold("hold_schema", "plan_or_decision_invalid")
        if plan.action == "fresh_backup":
            if not isinstance(backup_locator, str) or _digest(backup_locator + "|") != plan.locator_digest:
                raise RecoveryHold("hold_schema", "backup_locator_mismatch")
            current = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
            if (current.authority_generation, current.authority_head) != (plan.expected_generation, plan.expected_head):
                raise RecoveryHold("hold_target_stale", "fresh_before_mismatch")
            receipt = ledger.backup(backup_locator)
            return _freeze({"schema_version": VERSION, "outcome": "recovery_action_applied", "project_id": ledger.project_id,
                            "action": plan.action, "request_digest": plan.request_digest, "decision_digest": plan.decision_digest,
                            "generation": current.authority_generation, "head": current.authority_head,
                            "flags": _flags(mutation_performed=True, owner_readback_verified=bool(receipt), backup_performed=True)})
        if plan.action == "fresh_target_restore":
            if (not isinstance(restore_locator, str) or not isinstance(fresh_target_locator, str)
                    or _digest(restore_locator + "|" + fresh_target_locator) != plan.locator_digest):
                raise RecoveryHold("hold_schema", "restore_locator_mismatch")
            current = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
            if (current.authority_generation, current.authority_head) != (plan.expected_generation, plan.expected_head):
                raise RecoveryHold("hold_target_stale", "fresh_before_mismatch")
            restored = LocalCollaborationLedger.restore(restore_locator, fresh_target_locator, expected_project_id=ledger.project_id)
            try:
                after = read_handoff_state(restored.path, expected_project_id=ledger.project_id)
                return _freeze({"schema_version": VERSION, "outcome": "recovery_action_applied", "project_id": ledger.project_id,
                                "action": plan.action, "request_digest": plan.request_digest, "decision_digest": plan.decision_digest,
                                "generation": after.authority_generation, "head": after.authority_head,
                                "flags": _flags(mutation_performed=True, owner_readback_verified=True, restore_performed=True)})
            finally:
                restored.close()
        if plan.action == "target_takeover":
            if bundle is None or proof_ref is None:
                raise RecoveryHold("hold_schema", "bundle_proof_pair_required")
            # The A2 import receipt is no longer the current tail after a
            # successful takeover.  The sole permitted retry is therefore
            # recognized from the exact immediate A1 tail, before reopening
            # the import proof path that correctly treats it as stale.
            snapshot = LocalCollaborationLedger.authority_snapshot(ledger.path, expected_project_id=ledger.project_id)
            tail = snapshot.events[-1] if snapshot.events else None
            expected_event = plan.owner_plan.event
            if (snapshot.authority_generation == plan.expected_generation + 1 and tail is not None
                    and tail.event_id == expected_event["event_id"] and tail.event_type == expected_event["event_type"]
                    and tail.payload == expected_event["payload"] and tail.actor == expected_event["actor"]
                    and tail.source == expected_event["source"] and tail.root == expected_event["root"]
                    and tail.previous_hash == plan.expected_head):
                after = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
                if after.active_replica_id == plan.target_replica_id:
                    return _freeze({"schema_version": VERSION, "outcome": "recovery_action_applied", "project_id": ledger.project_id,
                                    "action": plan.action, "request_digest": plan.request_digest, "decision_digest": plan.decision_digest,
                                    "generation": after.authority_generation, "head": after.authority_head,
                                    "active_replica_id": after.active_replica_id,
                                    "flags": _flags(mutation_performed=False, owner_readback_verified=True)})
            projection, current = _projection_context(ledger.path, ledger.project_id, bundle, proof_ref, activation_ref)
            if (current.authority_generation, current.authority_head) != (plan.expected_generation, plan.expected_head) or projection["target_replica_id"] != plan.target_replica_id:
                raise RecoveryHold("hold_target_stale", "fresh_target_pair_mismatch")
        else:
            current = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
            if (current.authority_generation, current.authority_head) != (plan.expected_generation, plan.expected_head):
                raise RecoveryHold("hold_target_stale", "fresh_target_pair_mismatch")
        receipt = apply_handoff_transition(ledger, plan.owner_plan, expected_before=current)
        if receipt.get("outcome") not in {"taken_over", "cancelled", "enrolled"}:
            return _freeze({**receipt, "schema_version": VERSION, "flags": _flags(mutation_performed=receipt.get("flags", {}).get("owner_persisted", False), owner_readback_verified=receipt.get("flags", {}).get("owner_readback_verified", False))})
        provisional = {"event_ids": receipt.get("event_ids", []), "request_digest": plan.request_digest,
                       "generation": receipt.get("readback_generation"), "head": receipt.get("readback_head")}
        after = read_handoff_state(ledger.path, expected_project_id=ledger.project_id)
        if (after.authority_generation, after.authority_head) != (receipt["readback_generation"], receipt["readback_head"]):
            raise RecoveryHold("setup_incomplete", "post_commit_readback_unavailable")
        return _freeze({"schema_version": VERSION, "outcome": "recovery_action_applied", "project_id": ledger.project_id,
                        "action": plan.action, "request_digest": plan.request_digest, "decision_digest": plan.decision_digest,
                        "generation": after.authority_generation, "head": after.authority_head,
                        "active_replica_id": after.active_replica_id, "flags": _flags(mutation_performed=receipt["flags"]["owner_persisted"], owner_readback_verified=True)})
    except RecoveryHold as exc:
        return _hold(ledger.project_id, exc.outcome, exc.reason_code)
    except Exception:
        # A1 may have committed before its or this facade's final readback
        # failed.  Retain only the bound, metadata-only provisional receipt.
        if "provisional" in locals():
            return _freeze({"schema_version": VERSION, "outcome": "setup_incomplete", "project_id": ledger.project_id,
                            "reason_code": "post_commit_readback_unavailable", "provisional_receipt": provisional,
                            "flags": _flags(mutation_performed=True, owner_readback_verified=False)})
        return _hold(ledger.project_id, "setup_incomplete", "post_commit_readback_unavailable")


__all__ = ["RecoveryPlan", "apply_recovery_action", "plan_recovery_action", "read_recovery_summary"]
