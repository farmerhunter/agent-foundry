"""One-step, owner-backed recovery guidance for the single-active-device lane."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from local_collaboration_ledger import (GENESIS, LedgerBusyError, LedgerConflictError,
    LedgerIdentityError, LedgerIntegrityError, LedgerPermissionError, LedgerSchemaError,
    LocalCollaborationLedger)
from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import read_owner_imported_handoff_projection

VERSION = "LocalCollaborationRecovery-v1"
OPS = {"status_only", "create_backup", "restore_fresh_target", "cancel_pre_export_handoff", "revoke_inactive_replica", "takeover_from_accepted_frontier"}
FORBIDDEN = {"path", "hostname", "token", "secret", "credential", "bundle", "events", "transcript", "exception", "verified", "authorized"}


class _FrozenDict(dict):
    def _blocked(self, *args, **kwargs): raise TypeError("immutable recovery result")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


def _freeze(value):
    if isinstance(value, Mapping): return _FrozenDict({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)): return tuple(_freeze(v) for v in value)
    return value


def _canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
def _digest(value): return hashlib.sha256(_canonical(value).encode()).hexdigest()
def _safe_project(value):
    try: return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError): return "00000000-0000-0000-0000-000000000000"
def _hex(value): return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
def _opaque(value): return isinstance(value, str) and 1 <= len(value) <= 128 and all(c.isalnum() or c in "._-" for c in value)
def _locator(project_id, value):
    if not isinstance(value, (str, Path)): raise ValueError("locator")
    return _digest({"project_id": project_id, "locator": str(Path(value).expanduser().resolve(strict=False))})


def _summary(project_id, state, intent, *, reason=None, **extra):
    base = {"schema_version": VERSION, "project_id": project_id, "state": state,
            "next_action": intent, "mutation_performed": False, "source_unlock_performed": False,
            "automatic_recovery": False, "deletion_performed": False, "transport_performed": False,
            "global_convergence_verified": False, **extra}
    if reason: base["reason_code"] = reason
    base["summary_digest"] = _digest({k: v for k, v in base.items() if k != "summary_digest"})
    return _freeze(base)


def _hold(project_id, reason): return _summary(project_id, "held", "resolve_hold", reason=reason)
def _pair(state): return {"before_generation": state.authority_generation, "before_head": state.authority_head, "before_state_digest": state.state_digest}


def read_recovery_summary(db_path, *, expected_project_id, intent="status_only", bundle=None, proof_ref=None, selected_replica_id=None, **claims):
    """Read public owners only.  Caller claims never establish recovery authority."""
    project_id = _safe_project(expected_project_id)
    if claims or intent not in OPS: return _hold(project_id, "caller_claim_or_operation_forbidden")
    try:
        state = read_handoff_state(db_path, expected_project_id=project_id)
        fields = _pair(state)
        if intent == "status_only":
            label = "target_active_source_locked" if state.handoff and state.handoff.get("status") == "target_active" else ("source_locked_target_not_exposed" if state.phase == "source_locked" else "healthy_active")
            return _summary(project_id, label, "none", **fields)
        if intent == "cancel_pre_export_handoff":
            if state.phase not in {"preparing", "source_locked"} or not state.handoff: return _hold(project_id, "preexport_cancel_unavailable")
            if state.handoff.get("status") == "bundle_exported": return _hold(project_id, "return_proof_unavailable")
            return _summary(project_id, "recovery_action_ready", intent, handoff_id=state.handoff["handoff_id"], **fields)
        if intent == "revoke_inactive_replica":
            candidates = [e.replica_id for e in state.enrollments if not e.revoked and e.replica_id != state.active_replica_id]
            if not _opaque(selected_replica_id) or selected_replica_id not in candidates or len(candidates) != 1: return _hold(project_id, "inactive_replica_ambiguous")
            return _summary(project_id, "recovery_action_ready", intent, selected_replica_id=selected_replica_id, **fields)
        if intent == "takeover_from_accepted_frontier":
            if not isinstance(bundle, Mapping) or not isinstance(proof_ref, Mapping): return _hold(project_id, "owner_import_proof_missing")
            projection = read_owner_imported_handoff_projection(db_path, expected_project_id=project_id, bundle=bundle, proof_ref=proof_ref)
            if projection.get("outcome") != "owner_import_verified" or projection.get("target_activation_authorized"):
                return _hold(project_id, "owner_import_projection_unavailable")
            target = projection.get("target_replica_id")
            if selected_replica_id not in (None, target): return _hold(project_id, "target_enrollment_mismatch")
            return _summary(project_id, "recovery_action_ready", intent, selected_replica_id=target,
                bundle_locator_digest=_digest(bundle), proof_locator_digest=_digest(proof_ref), projection_digest=_digest(dict(projection)),
                target_generation=projection["target_generation"], target_head=projection["target_head"],
                frontier_digest=projection["frontier_digest"], **fields)
        return _summary(project_id, "recovery_action_ready", intent, **fields)
    except (ValueError, TypeError, KeyError, LedgerBusyError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return _hold(project_id, "owner_read_unavailable")


@dataclass(frozen=True)
class RecoveryActionPlan:
    project_id: str; operation: str; summary_digest: str; decision_id: str; decision_digest: str; parameters: Mapping[str, Any]; bindings: Mapping[str, Any]; fingerprint: str


_PARAMS = {"create_backup": {"destination"}, "restore_fresh_target": {"backup", "destination"},
           "cancel_pre_export_handoff": set(), "revoke_inactive_replica": set(),
           "takeover_from_accepted_frontier": {"bundle", "proof_ref", "rpo_warning_digest"}}


def plan_recovery_action(summary, request):
    try:
        if not isinstance(summary, Mapping) or not isinstance(request, Mapping) or set(request) != {"operation", "decision_id", "decision_digest", "parameters"}: raise ValueError()
        project_id = _safe_project(summary["project_id"]); operation = request["operation"]
        if operation not in _PARAMS or summary.get("state") != "recovery_action_ready" or summary.get("next_action") != operation: raise ValueError()
        if not _opaque(request["decision_id"]) or not _hex(request["decision_digest"]): raise ValueError()
        if not isinstance(request["parameters"], Mapping) or set(request["parameters"]) != _PARAMS[operation]: raise ValueError()
        if summary.get("summary_digest") != _digest({k: v for k, v in summary.items() if k != "summary_digest"}): raise ValueError()
        params = dict(request["parameters"])
        # Retain only privacy-safe locator digests in the persistent plan.
        if operation == "create_backup": params = {"destination_digest": _locator(project_id, params["destination"])}
        elif operation == "restore_fresh_target": params = {"backup_digest": _locator(project_id, params["backup"]), "destination_digest": _locator(project_id, params["destination"])}
        elif operation == "takeover_from_accepted_frontier":
            if _digest(params["bundle"]) != summary.get("bundle_locator_digest") or _digest(params["proof_ref"]) != summary.get("proof_locator_digest"): raise ValueError()
            if not _hex(params["rpo_warning_digest"]): raise ValueError()
            params = {"bundle_digest": _digest(request["parameters"]["bundle"]), "proof_digest": _digest(request["parameters"]["proof_ref"]), "projection_digest": summary["projection_digest"], "rpo_warning_digest": params["rpo_warning_digest"]}
        bindings = {key: summary[key] for key in ("before_generation", "before_head", "before_state_digest", "selected_replica_id", "bundle_locator_digest", "proof_locator_digest", "projection_digest") if key in summary}
        fingerprint = _digest({"project_id": project_id, "operation": operation, "summary_digest": summary["summary_digest"], "decision_id": request["decision_id"], "decision_digest": request["decision_digest"], "parameters": params, "bindings": bindings})
        return RecoveryActionPlan(project_id, operation, summary["summary_digest"], request["decision_id"], request["decision_digest"], _freeze(params), _freeze(bindings), fingerprint)
    except (ValueError, TypeError, KeyError):
        return {"schema_version": VERSION, "outcome": "held", "reason_code": "plan_schema_or_preimage_invalid"}


def _receipt(plan, before, after, owner_outcome, mutated, **extra):
    locator_digests = {key: value for key, value in plan.parameters.items() if key.endswith("_digest")}
    locator_digests.update({key: value for key, value in plan.bindings.items() if key in {"bundle_locator_digest", "proof_locator_digest"}})
    return _freeze({"schema_version": VERSION, "outcome": "recovery_action_applied" if mutated else "recovery_action_duplicate",
        "project_id": plan.project_id, "operation": plan.operation, "operation_fingerprint": plan.fingerprint,
        "decision_id": plan.decision_id, "decision_digest": plan.decision_digest, "before_generation": before[0], "before_head": before[1],
        "before_state_digest": plan.bindings["before_state_digest"], "after_generation": after[0], "after_head": after[1], "after_state_digest": after[2],
        "locator_digests": locator_digests, "owner_outcome": owner_outcome, "mutation_performed": mutated,
        "duplicate": not mutated, "source_unlock_performed": False, "automatic_recovery": False, "deletion_performed": False,
        "transport_performed": False, "global_convergence_verified": False,
        **({"selected_replica_id": plan.bindings["selected_replica_id"]} if "selected_replica_id" in plan.bindings else {}), **extra})


def _post_commit_result(project_id, receipt, db_path):
    """A committed owner action is incomplete until its facade readback succeeds."""
    try:
        next_summary = read_recovery_summary(db_path, expected_project_id=project_id)
        if not isinstance(next_summary, Mapping) or next_summary.get("state") == "held":
            raise ValueError("post-commit owner readback unavailable")
        return _freeze({"receipt": receipt, "next_summary": next_summary})
    except Exception:
        return _freeze({"schema_version": VERSION, "outcome": "setup_incomplete", "receipt": receipt,
                        "next_summary": _hold(project_id, "post_commit_readback_unavailable")})


def apply_recovery_action(context, plan):
    """Freshly revalidate, execute one public owner action, and return a metadata receipt."""
    project_id = plan.project_id if isinstance(plan, RecoveryActionPlan) else "00000000-0000-0000-0000-000000000000"
    provisional = None
    try:
        if not isinstance(context, Mapping) or not isinstance(plan, RecoveryActionPlan): raise ValueError()
        ledger = context.get("ledger")
        if not isinstance(ledger, LocalCollaborationLedger) or ledger.project_id != project_id: raise ValueError()
        intent_kwargs = {"selected_replica_id": context.get("selected_replica_id")}
        if plan.operation == "takeover_from_accepted_frontier": intent_kwargs.update(bundle=context.get("bundle"), proof_ref=context.get("proof_ref"))
        current = read_recovery_summary(ledger.path, expected_project_id=project_id, intent=plan.operation, **intent_kwargs)
        if current.get("summary_digest") != plan.summary_digest: return {"schema_version": VERSION, "outcome": "held", "reason_code": "stale_owner_preimage"}
        before_state = read_handoff_state(ledger.path, expected_project_id=project_id); before = (before_state.authority_generation, before_state.authority_head)
        if plan.operation == "create_backup":
            destination = context.get("destination")
            if _locator(project_id, destination) != plan.parameters["destination_digest"]: raise ValueError()
            if Path(destination).expanduser().exists(): return {"schema_version": VERSION, "outcome": "held", "reason_code": "backup_destination_exists"}
            ledger.backup(destination); provisional = _receipt(plan, before, (before[0], before[1], before_state.state_digest), "backup_created", True)
            return _post_commit_result(project_id, provisional, ledger.path)
        if plan.operation == "restore_fresh_target":
            backup, destination = context.get("backup"), context.get("destination")
            if _locator(project_id, backup) != plan.parameters["backup_digest"] or _locator(project_id, destination) != plan.parameters["destination_digest"]: raise ValueError()
            if Path(destination).expanduser().exists(): return {"schema_version": VERSION, "outcome": "held", "reason_code": "restore_destination_exists"}
            restored = LocalCollaborationLedger.restore(backup, destination, expected_project_id=project_id)
            try:
                after = restored.authority_snapshot(restored.path, expected_project_id=project_id)
                after_state = read_handoff_state(restored.path, expected_project_id=project_id)
                provisional = _receipt(plan, before, (after.authority_generation, after.authority_head, after_state.state_digest), "fresh_target_restored", True)
                return _post_commit_result(project_id, provisional, restored.path)
            finally: restored.close()
        if plan.operation in {"cancel_pre_export_handoff", "revoke_inactive_replica"}:
            req = {"transition": "cancel" if plan.operation.startswith("cancel") else "revoke_inactive", "project_id": project_id,
                   "decision_id": plan.decision_id, "decision_digest": plan.decision_digest}
            if plan.operation.startswith("cancel"): req.update(handoff_id=current["handoff_id"], cancellation_evidence="bundle_not_released")
            else: req.update(replica_id=current["selected_replica_id"])
            owner_plan = plan_handoff_transition(before_state, req)
            if isinstance(owner_plan, Mapping): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_plan_held"}
            owner = apply_handoff_transition(ledger, owner_plan, expected_before=before_state)
            if owner.get("outcome", "").startswith("hold_"): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_apply_held"}
            after_state = read_handoff_state(ledger.path, expected_project_id=project_id)
            provisional = _receipt(plan, before, (owner["readback_generation"], owner["readback_head"], after_state.state_digest), owner["outcome"], owner["flags"]["owner_persisted"])
        elif plan.operation == "takeover_from_accepted_frontier":
            bundle, proof = context.get("bundle"), context.get("proof_ref")
            if _digest(bundle) != plan.parameters["bundle_digest"] or _digest(proof) != plan.parameters["proof_digest"]: raise ValueError()
            projection = read_owner_imported_handoff_projection(ledger.path, expected_project_id=project_id, bundle=bundle, proof_ref=proof)
            if projection.get("outcome") != "owner_import_verified" or projection.get("target_activation_authorized") or _digest(dict(projection)) != plan.parameters["projection_digest"]: return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_projection_drift"}
            target_state = read_handoff_state(ledger.path, expected_project_id=project_id)
            if (target_state.authority_generation, target_state.authority_head) != (projection["target_generation"], projection["target_head"]):
                return {"schema_version": VERSION, "outcome": "held", "reason_code": "target_authority_pair_drift"}
            req = {"transition": "takeover", "project_id": project_id, "target_replica_id": projection["target_replica_id"], "prior_frontier_digest": projection["frontier_digest"], "decision_id": plan.decision_id, "decision_digest": plan.decision_digest}
            owner_plan = plan_handoff_transition(target_state, req)
            if isinstance(owner_plan, Mapping): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_plan_held"}
            owner = apply_handoff_transition(ledger, owner_plan, expected_before=target_state)
            if owner.get("outcome", "").startswith("hold_"): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_apply_held"}
            after_state = read_handoff_state(ledger.path, expected_project_id=project_id)
            provisional = _receipt(plan, (target_state.authority_generation, target_state.authority_head), (owner["readback_generation"], owner["readback_head"], after_state.state_digest), owner["outcome"], owner["flags"]["owner_persisted"])
        else: raise ValueError()
        return _post_commit_result(project_id, provisional, ledger.path)
    except (ValueError, TypeError, KeyError, LedgerBusyError, LedgerConflictError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        if provisional is not None:
            return _freeze({"schema_version": VERSION, "outcome": "setup_incomplete", "receipt": provisional, "next_summary": _hold(project_id, "post_commit_readback_unavailable")})
        return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_or_context_unavailable"}


__all__ = ["RecoveryActionPlan", "apply_recovery_action", "plan_recovery_action", "read_recovery_summary"]
