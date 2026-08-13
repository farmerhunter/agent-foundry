"""Bounded, owner-backed second-device onboarding facade."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from local_collaboration_handoff import apply_handoff_transition, plan_handoff_transition, read_handoff_state
from local_collaboration_handoff_bundle import (apply_owner_import, apply_owner_target_activation,
    inspect_manual_bundle, plan_owner_import, plan_owner_target_activation, prepare_manual_bundle)
from local_collaboration_handoff_experience import read_handoff_experience
from local_collaboration_ledger import (LedgerBusyError, LedgerIdentityError, LedgerIntegrityError,
    LedgerPermissionError, LedgerSchemaError, LocalCollaborationLedger)

VERSION = "LocalCollaborationOnboarding-v1"
HEX = set("0123456789abcdef")
OPAQUE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


class _FrozenDict(dict):
    def _blocked(self, *args, **kwargs): raise TypeError("immutable onboarding result")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


def _freeze(value):
    if isinstance(value, Mapping): return _FrozenDict({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)): return tuple(_freeze(v) for v in value)
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _uuid(value):
    try: return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc: raise ValueError("invalid identity") from exc


def _opaque(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(c not in OPAQUE for c in value): raise ValueError("invalid opaque")
    return value


def _hex(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value): raise ValueError("invalid digest")
    return value


def _summary(project_id, stage, operation, *, decision=True, reason=None, **extra):
    base = {"schema_version": VERSION, "project_id": project_id, "stage": stage,
            "next_operation": operation, "human_decision_required": decision,
            "mutation_performed": False, "data_movement_performed": False,
            "transport_performed": False, "target_activation_visibility": "not_exposed",
            "source_unlock_performed": False, "global_convergence_verified": False, **extra}
    if reason is not None: base["reason_code"] = reason
    base["summary_digest"] = _digest({k: v for k, v in base.items() if k != "summary_digest"})
    return _freeze(base)


def _hold(project_id, reason): return _summary(project_id, "held", "resolve_hold", decision=False, reason=reason)


def _source_fields(state):
    return {"source_generation": state.authority_generation, "source_head": state.authority_head,
            "source_state_digest": state.state_digest,
            **({"source_replica_id": state.active_replica_id} if state.active_replica_id else {})}


def _safe_project(value):
    try: return _uuid(value)
    except ValueError: return "00000000-0000-0000-0000-000000000000"


def read_second_device_onboarding(source_db_path, *, expected_project_id, target_db_path=None,
                                  bundle=None, proof_ref=None, activation_ref=None, **claims):
    """Read owners only; caller claims never advance the displayed stage."""
    project_id = _safe_project(expected_project_id)
    if claims: return _hold(project_id, "caller_claim_forbidden")
    try:
        source = read_handoff_state(source_db_path, expected_project_id=project_id)
        fields = _source_fields(source); handoff = dict(source.handoff or {})
        if source.phase == "uninitialized": return _summary(project_id, "source_ready", "none", decision=False, **fields)
        if source.phase == "active" and len(source.enrollments) < 2:
            return _summary(project_id, "target_enrollment_review", "enroll_target", **fields)
        if source.phase == "active":
            return _summary(project_id, "handoff_prepare_review", "prepare_handoff", **fields)
        if source.phase == "preparing":
            return _summary(project_id, "source_lock_review", "lock_source", handoff_id=handoff.get("handoff_id", "unknown"), **fields)
        if source.phase == "source_locked" and handoff.get("status") != "bundle_exported":
            return _summary(project_id, "bundle_export_ready", "export_bundle", handoff_id=handoff.get("handoff_id", "unknown"), **fields)
        if source.phase != "source_locked" or handoff.get("status") != "bundle_exported": return _hold(project_id, "source_state_unavailable")
        fields.update({"handoff_id": handoff.get("handoff_id", "unknown"), "target_replica_id": handoff.get("target_replica_id", "unknown")})
        if bundle is None:
            return _summary(project_id, "manual_transfer_required", "manual_transfer", decision=False, **fields)
        inspected = inspect_manual_bundle(bundle)
        if inspected.get("outcome") != "import_candidate" or inspected.get("project_id") != project_id:
            return _hold(project_id, "bundle_unavailable")
        fields["package_digest"] = inspected["package_digest"]
        if target_db_path is None: return _summary(project_id, "target_authority_create_review", "create_target_authority", **fields)
        if proof_ref is None: return _summary(project_id, "target_import_review", "import_bundle", **fields)
        exp = read_handoff_experience(target_db_path, expected_project_id=project_id, bundle=bundle, proof_ref=proof_ref,
                                      **({"activation_ref": activation_ref} if activation_ref is not None else {}))
        if exp.get("experience_state") == "target_active":
            return _summary(project_id, "target_active_source_locked", "none", decision=False, **fields,
                            target_generation=exp["target_generation"], target_head=exp["target_head"],
                            target_activation_visibility="owner_verified_target_local")
        if exp.get("experience_state") == "target_import_verified_activation_deferred":
            return _summary(project_id, "target_activation_review", "activate_target", **fields,
                            target_generation=exp["target_generation"], target_head=exp["target_head"],
                            target_activation_visibility="owner_verified_import_only")
        return _hold(project_id, "target_owner_state_unavailable")
    except (ValueError, TypeError, KeyError, LedgerBusyError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return _hold(project_id, "owner_state_unavailable")


@dataclass(frozen=True)
class OnboardingStepPlan:
    project_id: str
    operation: str
    summary_digest: str
    decision_id: str
    decision_digest: str
    parameters: Mapping[str, Any]
    fingerprint: str


_PARAMS = {
    "enroll_target": {"replica_id", "replica_epoch", "enrollment_id", "enrollment_digest"},
    "prepare_handoff": {"handoff_id", "source_replica_id", "target_replica_id", "frontier_digest"},
    "lock_source": {"handoff_id"}, "export_bundle": set(), "create_target_authority": set(),
    "import_bundle": set(), "activate_target": set(),
}


def plan_second_device_onboarding_step(summary, request):
    try:
        if not isinstance(summary, Mapping) or not isinstance(request, Mapping) or set(request) != {"operation", "decision_id", "decision_digest", "parameters"}:
            raise ValueError("closed request")
        project_id = _uuid(summary.get("project_id")); operation = request["operation"]
        if summary.get("stage") == "held" or operation != summary.get("next_operation") or operation not in _PARAMS:
            raise ValueError("operation unavailable")
        if not summary.get("human_decision_required") or _hex(summary.get("summary_digest")) != _digest({k: v for k, v in summary.items() if k != "summary_digest"}):
            raise ValueError("summary invalid")
        decision_id, decision_digest = _opaque(request["decision_id"]), _hex(request["decision_digest"])
        parameters = request["parameters"]
        if not isinstance(parameters, Mapping) or set(parameters) != _PARAMS[operation]: raise ValueError("parameters invalid")
        if any(isinstance(v, Mapping) or isinstance(v, (list, tuple)) for v in parameters.values()): raise ValueError("nested parameter")
        frozen = _freeze(dict(parameters)); fingerprint = _digest({"project_id": project_id, "operation": operation,
            "summary_digest": summary["summary_digest"], "decision_id": decision_id, "decision_digest": decision_digest, "parameters": dict(frozen)})
        return OnboardingStepPlan(project_id, operation, summary["summary_digest"], decision_id, decision_digest, frozen, fingerprint)
    except (ValueError, TypeError, KeyError):
        return {"schema_version": VERSION, "outcome": "held", "reason_code": "plan_schema_or_preimage_invalid"}


def _receipt(project_id, plan, before, after, owner, mutated):
    return _freeze({"schema_version": VERSION, "outcome": "onboarding_step_applied" if mutated else "onboarding_step_duplicate",
        "project_id": project_id, "operation": plan.operation, "operation_fingerprint": plan.fingerprint,
        "before_generation": before[0], "before_head": before[1], "after_generation": after[0], "after_head": after[1],
        "owner_outcome": owner, "mutation_performed": mutated, "duplicate": not mutated})


def _exact_a1_duplicate(source, plan):
    event_type = {"enroll_target": "replica_enrolled", "prepare_handoff": "handoff_prepared",
                  "lock_source": "handoff_source_locked"}.get(plan.operation)
    if event_type is None:
        return None
    snapshot = LocalCollaborationLedger.authority_snapshot(source.path, expected_project_id=plan.project_id)
    event = snapshot.events[-1] if snapshot.events else None
    payload = event.payload if event is not None else None
    if (event is not None and event.event_type == event_type and event.actor == "owner"
            and event.source == "orch05_handoff" and event.root == plan.project_id
            and isinstance(payload, Mapping) and payload.get("decision_digest") == plan.decision_digest):
        return _receipt(plan.project_id, plan, (snapshot.authority_generation - 1, event.previous_hash),
                        (snapshot.authority_generation, snapshot.authority_head), "owner_exact_duplicate", False)
    return None


def apply_second_device_onboarding_step(context, plan):
    """Freshly re-read then execute exactly one selected public owner mutation."""
    project_id = plan.project_id if isinstance(plan, OnboardingStepPlan) else "00000000-0000-0000-0000-000000000000"
    try:
        if not isinstance(context, Mapping) or not isinstance(plan, OnboardingStepPlan): raise ValueError("context")
        source = context.get("source_ledger"); target = context.get("target_ledger")
        if not isinstance(source, LocalCollaborationLedger) or source.project_id != project_id: raise ValueError("source")
        current = read_second_device_onboarding(source.path, expected_project_id=project_id,
            target_db_path=target.path if isinstance(target, LocalCollaborationLedger) else None,
            bundle=context.get("bundle"), proof_ref=context.get("proof_ref"), activation_ref=context.get("activation_ref"))
        if current.get("summary_digest") != plan.summary_digest or current.get("next_operation") != plan.operation:
            duplicate = _exact_a1_duplicate(source, plan)
            if duplicate is not None:
                return _freeze({"receipt": duplicate, "next_summary": current})
            return {"schema_version": VERSION, "outcome": "held", "reason_code": "stale_summary_or_plan"}
        source_before = read_handoff_state(source.path, expected_project_id=project_id)
        owner = None; mutated = False; before = (source_before.authority_generation, source_before.authority_head)
        if plan.operation in {"enroll_target", "prepare_handoff", "lock_source"}:
            transition = {"enroll_target": "enroll_target", "prepare_handoff": "prepare", "lock_source": "source_lock"}[plan.operation]
            req = {"transition": transition, "project_id": project_id, **dict(plan.parameters)}
            if transition == "enroll_target": req.update(decision_id=plan.decision_id, decision_digest=plan.decision_digest)
            planned = plan_handoff_transition(source_before, req)
            if isinstance(planned, Mapping): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_plan_held"}
            owner = apply_handoff_transition(source, planned, expected_before=source_before)
            if owner.get("outcome", "").startswith("hold_"): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_apply_held"}
            mutated = owner["flags"]["owner_persisted"]
        elif plan.operation == "export_bundle":
            owner = prepare_manual_bundle(source, expected_handoff_state=source_before)
            if "outcome" in owner: return {"schema_version": VERSION, "outcome": "held", "reason_code": "bundle_export_held"}
            context["_manual_bundle"] = owner
            mutated = True
        elif plan.operation == "create_target_authority":
            if target is not None or not isinstance(context.get("target_projects_root"), (str, Path)): raise ValueError("target create")
            target = LocalCollaborationLedger.create_project(projects_root=context["target_projects_root"], project_id=project_id)
            context["target_ledger"] = target; owner = {"outcome": "target_authority_created"}; mutated = True
        elif plan.operation == "import_bundle":
            if not isinstance(target, LocalCollaborationLedger) or not isinstance(context.get("bundle"), Mapping): raise ValueError("import")
            before_snapshot = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id); before = (before_snapshot.authority_generation, before_snapshot.authority_head)
            imported = plan_owner_import(before_snapshot, context["bundle"])
            if isinstance(imported, Mapping): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_import_plan_held"}
            owner = apply_owner_import(target, imported, expected_before=before_snapshot); mutated = owner.get("owner_import_performed", False)
            if owner.get("outcome", "").startswith("hold_"): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_import_held"}
            context["proof_ref"] = {key: owner[key] for key in ("project_id", "receipt_event_id", "receipt_event_hash", "package_digest")}
        elif plan.operation == "activate_target":
            if not isinstance(target, LocalCollaborationLedger): raise ValueError("activation")
            before_snapshot = LocalCollaborationLedger.authority_snapshot(target.path, expected_project_id=project_id); before = (before_snapshot.authority_generation, before_snapshot.authority_head)
            activation = plan_owner_target_activation(target.path, expected_project_id=project_id, bundle=context["bundle"], proof_ref=context["proof_ref"], decision={"decision_id": plan.decision_id, "decision_digest": plan.decision_digest})
            if isinstance(activation, Mapping): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_activation_plan_held"}
            owner = apply_owner_target_activation(target, activation, bundle=context["bundle"], proof_ref=context["proof_ref"], decision={"decision_id": plan.decision_id, "decision_digest": plan.decision_digest})
            mutated = owner.get("target_activation_performed", False)
            if owner.get("outcome", "").startswith("hold_"): return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_activation_held"}
            context["activation_ref"] = {key: owner[key] for key in ("project_id", "activation_receipt_event_id", "activation_receipt_event_hash", "package_digest")}
        else: raise ValueError("operation")
        observed = target if plan.operation in {"import_bundle", "activate_target"} else source
        after_snapshot = LocalCollaborationLedger.authority_snapshot(observed.path, expected_project_id=project_id)
        next_summary = read_second_device_onboarding(source.path, expected_project_id=project_id,
            target_db_path=target.path if isinstance(target, LocalCollaborationLedger) else None,
            bundle=context.get("bundle"), proof_ref=context.get("proof_ref"), activation_ref=context.get("activation_ref"))
        return _freeze({"receipt": _receipt(project_id, plan, before, (after_snapshot.authority_generation, after_snapshot.authority_head), owner.get("outcome", "unknown"), mutated), "next_summary": next_summary})
    except (ValueError, TypeError, KeyError, LedgerBusyError, LedgerPermissionError, LedgerIntegrityError, LedgerSchemaError, LedgerIdentityError):
        return {"schema_version": VERSION, "outcome": "held", "reason_code": "owner_or_context_unavailable"}


__all__ = ["OnboardingStepPlan", "apply_second_device_onboarding_step", "plan_second_device_onboarding_step", "read_second_device_onboarding"]
