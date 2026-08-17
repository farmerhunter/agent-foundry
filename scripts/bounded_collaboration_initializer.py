#!/usr/bin/env python3
"""Fixture-only owner composition for bounded-collaboration completion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


VERSION = "bounded-collaboration-initialization-v1"
ROLES = ("Coordinator", "Architect")
PRIVATE_KEYS = {
    "body", "content", "credential", "exception", "history", "message",
    "messages", "native_thread_id", "path", "prompt", "raw", "stderr",
    "stdout", "token", "tool_output", "transcript", "turns",
}


class _FrozenDict(dict):
    """A JSON-serializable dictionary that rejects recursive receipt mutation."""

    def __init__(self, value: Mapping[str, Any]):
        dict.__init__(self, value)

    def _immutable(self, *_: Any, **__: Any) -> None:
        raise TypeError("receipt_is_immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list) or isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _has_private(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key).lower() in PRIVATE_KEYS or _has_private(item) for key, item in value.items())
    return isinstance(value, (list, tuple)) and any(_has_private(item) for item in value)


class ProjectBindingOwner(Protocol):
    def read_binding(self) -> Mapping[str, Any]: ...


class SchedulerBindingOwner(Protocol):
    def read_binding(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]: ...


class RoleTopologyOwner(Protocol):
    def read_topology(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def apply_topology(self, plan: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def read_completion(self, onboarding_key: str, project_binding: Mapping[str, Any]) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class Owners:
    project: ProjectBindingOwner
    scheduler: SchedulerBindingOwner
    topology: RoleTopologyOwner


def _result(
    state: str,
    onboarding_key: str,
    *,
    attention_reason: str | None,
    safe_next_action: str,
    mutation_performed: bool = False,
    **fields: Any,
) -> _FrozenDict:
    value = {
        "contract_version": VERSION,
        "onboarding_key": onboarding_key,
        "completion_state": state,
        "mutation_performed": mutation_performed,
        "attention_reason": attention_reason,
        "safe_next_action": safe_next_action,
        **fields,
    }
    return _freeze(value)


def _call(owner: Any, method: str, *args: Any) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        value = getattr(owner, method)(*args)
    except Exception:
        return None, "owner_unavailable"
    if not isinstance(value, Mapping):
        return None, "owner_unavailable"
    if _has_private(value):
        return None, "privacy_held"
    return value, None


def _nonempty(value: Mapping[str, Any], *names: str) -> bool:
    return all(isinstance(value.get(name), str) and value[name] for name in names)


def _project(value: Mapping[str, Any]) -> str | None:
    if value.get("state") != "bound":
        return "project_binding_unavailable"
    required = ("project_binding_ref", "project_binding_digest", "project_id", "repository_digest", "root_digest")
    return None if _nonempty(value, *required) else "project_binding_invalid"


def _scheduler(value: Mapping[str, Any], project: Mapping[str, Any]) -> str | None:
    if value.get("state") != "bound":
        return "scheduler_or_work_root_unavailable"
    required = ("scheduler_binding_ref", "work_root_ref", "scheduler_binding_revision", "scheduler_binding_digest", "project_binding_digest")
    if not _nonempty(value, *required):
        return "scheduler_or_work_root_invalid"
    return None if value["project_binding_digest"] == project["project_binding_digest"] else "scheduler_project_binding_mismatch"


def _topology(value: Mapping[str, Any], project: Mapping[str, Any]) -> str | None:
    if value.get("state") == "missing":
        return None
    if value.get("state") != "ready":
        return "topology_unavailable"
    required = ("rolehub_ref", "coordinator_ref", "architect_ref", "topology_readback_digest", "project_binding_digest")
    if not _nonempty(value, *required):
        return "topology_invalid"
    if value.get("coordinator_count") != 1 or value.get("architect_count") != 1:
        return "duplicate_or_missing_durable_role"
    return None if value["project_binding_digest"] == project["project_binding_digest"] else "topology_project_binding_mismatch"


def _receipt(
    onboarding_key: str,
    project: Mapping[str, Any],
    scheduler: Mapping[str, Any],
    topology: Mapping[str, Any],
    *,
    mutation_performed: bool,
    operation_receipt_refs: tuple[str, ...],
    topology_apply_binding_ref: str | None = None,
    topology_apply_binding_digest: str | None = None,
) -> _FrozenDict:
    fields: dict[str, Any] = {
        "project_binding_ref": project["project_binding_ref"],
        "project_binding_digest": project["project_binding_digest"],
        "rolehub_ref": topology["rolehub_ref"],
        "coordinator_ref": topology["coordinator_ref"],
        "architect_ref": topology["architect_ref"],
        "topology_readback_digest": topology["topology_readback_digest"],
        "scheduler_binding_ref": scheduler["scheduler_binding_ref"],
        "work_root_ref": scheduler["work_root_ref"],
        "scheduler_binding_revision": scheduler["scheduler_binding_revision"],
        "scheduler_binding_digest": scheduler["scheduler_binding_digest"],
        "repo_contract_status": "not_authoritative",
        "operation_receipt_refs": operation_receipt_refs,
    }
    if topology_apply_binding_ref is not None and topology_apply_binding_digest is not None:
        fields["topology_apply_binding_ref"] = topology_apply_binding_ref
        fields["topology_apply_binding_digest"] = topology_apply_binding_digest
    receipt = _result(
        "native_ready",
        onboarding_key,
        attention_reason=None,
        safe_next_action="Create or reuse one approved Work through the durable scheduler.",
        mutation_performed=mutation_performed,
        **fields,
    )
    return receipt


def _same_fresh_binding(before: Mapping[str, Any], after: Mapping[str, Any], fields: tuple[str, ...]) -> bool:
    return all(before.get(name) == after.get(name) for name in fields)


def _binding_digest(value: Mapping[str, Any]) -> str:
    return _digest({key: item for key, item in value.items() if key != "topology_apply_binding_digest"})


def _validate_apply_binding(
    binding: Any,
    *,
    onboarding_key: str,
    project: Mapping[str, Any],
    scheduler: Mapping[str, Any],
    topology: Mapping[str, Any],
    plan: Mapping[str, Any] | None = None,
    operation_receipt_refs: tuple[str, ...] | None = None,
) -> tuple[str | None, str | None]:
    """Validate an owner commitment to the exact plan, receipts and readback."""
    if not isinstance(binding, Mapping) or _has_private(binding):
        return None, "topology_apply_readback_binding_missing"
    required = (
        "topology_apply_binding_ref", "topology_apply_binding_digest", "topology_plan_digest",
        "onboarding_key", "project_binding_digest", "scheduler_binding_digest",
        "operation_receipt_refs_digest", "rolehub_ref", "coordinator_ref",
        "architect_ref", "topology_readback_digest",
    )
    if not _nonempty(binding, *required) or not isinstance(binding.get("requested_roles"), (list, tuple)):
        return None, "topology_apply_readback_binding_missing"
    if binding["onboarding_key"] != onboarding_key or binding["project_binding_digest"] != project["project_binding_digest"] or binding["scheduler_binding_digest"] != scheduler["scheduler_binding_digest"] or tuple(binding["requested_roles"]) != ROLES:
        return None, "topology_apply_binding_context_mismatch"
    stored_refs = binding["operation_receipt_refs"]
    if not isinstance(stored_refs, (list, tuple)) or not all(isinstance(item, str) and item for item in stored_refs):
        return None, "topology_apply_readback_binding_missing"
    if binding["operation_receipt_refs_digest"] != _digest(list(stored_refs)):
        return None, "topology_apply_receipt_binding_mismatch"
    if plan is not None and binding["topology_plan_digest"] != plan["topology_plan_digest"]:
        return None, "topology_apply_plan_binding_mismatch"
    if operation_receipt_refs is not None and tuple(stored_refs) != operation_receipt_refs:
        return None, "topology_apply_receipt_binding_mismatch"
    if binding["topology_apply_binding_digest"] != _binding_digest(binding):
        return None, "topology_apply_readback_binding_forged"
    final_fields = ("rolehub_ref", "coordinator_ref", "architect_ref", "topology_readback_digest")
    if any(topology.get(name) != binding.get(name) for name in final_fields):
        return None, "topology_apply_readback_identity_mismatch"
    if topology.get("topology_apply_binding_ref") != binding["topology_apply_binding_ref"] or topology.get("topology_apply_binding_digest") != binding["topology_apply_binding_digest"]:
        return None, "topology_apply_readback_binding_mismatch"
    return binding["topology_apply_binding_ref"], None


def _completion_identity(
    onboarding_key: str,
    project: Mapping[str, Any],
    scheduler: Mapping[str, Any],
    topology: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "onboarding_key": onboarding_key,
        "project_binding_ref": project["project_binding_ref"],
        "project_binding_digest": project["project_binding_digest"],
        "scheduler_binding_ref": scheduler["scheduler_binding_ref"],
        "work_root_ref": scheduler["work_root_ref"],
        "scheduler_binding_revision": scheduler["scheduler_binding_revision"],
        "scheduler_binding_digest": scheduler["scheduler_binding_digest"],
        "topology_plan_digest": binding["topology_plan_digest"],
        "operation_receipt_refs": list(binding["operation_receipt_refs"]),
        "topology_apply_binding_ref": binding["topology_apply_binding_ref"],
        "topology_apply_binding_digest": binding["topology_apply_binding_digest"],
        "rolehub_ref": topology["rolehub_ref"],
        "coordinator_ref": topology["coordinator_ref"],
        "architect_ref": topology["architect_ref"],
        "topology_readback_digest": topology["topology_readback_digest"],
    }


def _validate_persistent_completion(record: Any, expected: Mapping[str, Any]) -> str | None:
    if not isinstance(record, Mapping) or _has_private(record):
        return "original_completion_unavailable"
    if record.get("state") != "ready" or not isinstance(record.get("completion_receipt_ref"), str) or not record["completion_receipt_ref"]:
        return "original_completion_unavailable"
    return None if all(record.get(name) == value for name, value in expected.items()) else "original_completion_identity_drift"


def initialize(
    owners: Owners,
    *,
    onboarding_key: str,
    apply_authorized: bool = False,
    caller_claims: Mapping[str, Any] | None = None,
) -> _FrozenDict:
    """Read owners in order and return the sole completion receipt shape.

    ``caller_claims`` is intentionally never authority.  It is accepted only so
    an integration can demonstrate that forged projections are held after owner
    preflight, rather than silently treated as a fallback.
    """
    if not isinstance(onboarding_key, str) or not onboarding_key:
        return _result("partial_hold", "invalid", attention_reason="invalid_onboarding_key", safe_next_action="Supply a new bounded onboarding key.")

    project, error = _call(owners.project, "read_binding")
    if error:
        return _result("unavailable" if error == "owner_unavailable" else "partial_hold", onboarding_key, attention_reason=error, safe_next_action="Restore the project binding owner before onboarding.")
    assert project is not None
    reason = _project(project)
    if reason:
        return _result("repo_contract_only", onboarding_key, attention_reason=reason, safe_next_action="Bind one project owner before native topology setup.")

    scheduler, error = _call(owners.scheduler, "read_binding", project)
    if error:
        return _result("unavailable" if error == "owner_unavailable" else "partial_hold", onboarding_key, attention_reason=error, safe_next_action="Restore the scheduler and Work-root owner before topology setup.")
    assert scheduler is not None
    reason = _scheduler(scheduler, project)
    if reason:
        return _result("repo_contract_only" if reason.startswith("scheduler_or_work_root") else "partial_hold", onboarding_key, attention_reason=reason, safe_next_action="Create or repair the durable scheduler/Work-root binding before topology setup.")

    topology, error = _call(owners.topology, "read_topology", project)
    if error:
        return _result("unavailable" if error == "owner_unavailable" else "partial_hold", onboarding_key, attention_reason=error, safe_next_action="Restore the role-topology owner before onboarding.")
    assert topology is not None
    reason = _topology(topology, project)
    if reason:
        return _result("partial_hold", onboarding_key, attention_reason=reason, safe_next_action="Resolve topology ambiguity before a new onboarding attempt.")
    if caller_claims is not None:
        return _result("partial_hold", onboarding_key, attention_reason="caller_claims_not_authoritative", safe_next_action="Remove caller-produced completion claims and use owner readbacks only.")

    retry_binding_seen = topology.get("state") == "ready" and isinstance(topology.get("topology_apply_binding"), Mapping) and topology["topology_apply_binding"].get("onboarding_key") == onboarding_key
    if retry_binding_seen:
        binding_ref, binding_error = _validate_apply_binding(
            topology["topology_apply_binding"],
            onboarding_key=onboarding_key,
            project=project,
            scheduler=scheduler,
            topology=topology,
        )
        if binding_error:
            return _result("partial_hold", onboarding_key, attention_reason=binding_error, safe_next_action="Resolve topology commitment drift before any follow-up.")
        assert binding_ref is not None

    if topology.get("state") == "missing" and not apply_authorized:
        plan = {
            "contract_version": VERSION,
            "onboarding_key": onboarding_key,
            "project_binding_ref": project["project_binding_ref"],
            "project_binding_digest": project["project_binding_digest"],
            "scheduler_binding_digest": scheduler["scheduler_binding_digest"],
            "requested_roles": ROLES,
            "topology_preimage_digest": _digest({"state": "missing", "project_binding_digest": project["project_binding_digest"]}),
        }
        plan["topology_plan_digest"] = _digest(plan)
        return _result("topology_plan_ready", onboarding_key, attention_reason=None, safe_next_action="Obtain bounded topology-apply authorization.", topology_plan=_freeze(plan))

    mutation_performed = False
    apply_invoked = False
    operation_receipt_refs: tuple[str, ...] = ()
    apply_binding: Mapping[str, Any] | None = None
    if topology.get("state") == "missing":
        apply_invoked = True
        plan = {
            "contract_version": VERSION,
            "onboarding_key": onboarding_key,
            "project_binding_ref": project["project_binding_ref"],
            "project_binding_digest": project["project_binding_digest"],
            "scheduler_binding_digest": scheduler["scheduler_binding_digest"],
            "requested_roles": ROLES,
            "topology_preimage_digest": _digest({"state": "missing", "project_binding_digest": project["project_binding_digest"]}),
        }
        plan["topology_plan_digest"] = _digest(plan)
        applied, error = _call(owners.topology, "apply_topology", _freeze(plan))
        if error:
            return _result("setup_incomplete", onboarding_key, attention_reason=error, safe_next_action="Read topology and scheduler state before any follow-up.")
        assert applied is not None
        refs = applied.get("operation_receipt_refs")
        if (
            applied.get("state") != "applied"
            or not isinstance(refs, (list, tuple))
            or not all(isinstance(item, str) and item for item in refs)
            or applied.get("topology_plan_digest") != plan["topology_plan_digest"]
            or not isinstance(applied.get("topology_apply_binding"), Mapping)
            or (bool(applied.get("mutation_performed")) and not refs)
        ):
            return _result("setup_incomplete", onboarding_key, attention_reason="topology_apply_incomplete", safe_next_action="Read topology and scheduler state before any follow-up.")
        mutation_performed = bool(applied.get("mutation_performed"))
        operation_receipt_refs = tuple(refs)
        apply_binding = applied["topology_apply_binding"]

    fresh_project, error = _call(owners.project, "read_binding")
    if error:
        return _result("setup_incomplete", onboarding_key, attention_reason=error, safe_next_action="Read all owners before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
    fresh_topology, topo_error = _call(owners.topology, "read_topology", fresh_project or {})
    fresh_scheduler, scheduler_error = _call(owners.scheduler, "read_binding", fresh_project or {})
    if error or topo_error or scheduler_error or fresh_project is None or fresh_topology is None or fresh_scheduler is None:
        return _result("setup_incomplete", onboarding_key, attention_reason="post_commit_readback_unavailable", safe_next_action="Read all owners before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
    if _project(fresh_project) or _topology(fresh_topology, fresh_project) or _scheduler(fresh_scheduler, fresh_project):
        return _result("setup_incomplete", onboarding_key, attention_reason="post_commit_owner_state_invalid", safe_next_action="Resolve owner drift before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
    if not _same_fresh_binding(project, fresh_project, ("project_binding_ref", "project_binding_digest", "project_id", "repository_digest", "root_digest")):
        return _result("setup_incomplete", onboarding_key, attention_reason="project_binding_drift", safe_next_action="Resolve project binding drift before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
    if not _same_fresh_binding(scheduler, fresh_scheduler, ("scheduler_binding_ref", "work_root_ref", "scheduler_binding_revision", "scheduler_binding_digest", "project_binding_digest")):
        return _result("setup_incomplete", onboarding_key, attention_reason="scheduler_binding_drift", safe_next_action="Resolve scheduler/Work-root drift before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
    if apply_invoked:
        assert apply_binding is not None
        binding_ref, binding_error = _validate_apply_binding(
            apply_binding,
            onboarding_key=onboarding_key,
            project=fresh_project,
            scheduler=fresh_scheduler,
            topology=fresh_topology,
            plan=plan,
            operation_receipt_refs=operation_receipt_refs,
        )
        if binding_error:
            return _result("setup_incomplete", onboarding_key, attention_reason=binding_error, safe_next_action="Read topology and scheduler state before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
        assert binding_ref is not None
        original, original_error = _call(owners.topology, "read_completion", onboarding_key, fresh_project)
        expected = _completion_identity(onboarding_key, fresh_project, fresh_scheduler, fresh_topology, apply_binding)
        if original_error or _validate_persistent_completion(original, expected):
            return _result("setup_incomplete", onboarding_key, attention_reason=original_error or _validate_persistent_completion(original, expected), safe_next_action="Resolve original completion evidence before any follow-up.", mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs)
        return _receipt(onboarding_key, fresh_project, fresh_scheduler, fresh_topology, mutation_performed=mutation_performed, operation_receipt_refs=operation_receipt_refs, topology_apply_binding_ref=binding_ref, topology_apply_binding_digest=apply_binding["topology_apply_binding_digest"])
    if retry_binding_seen:
        retry_binding = fresh_topology.get("topology_apply_binding")
        binding_ref, binding_error = _validate_apply_binding(
            retry_binding,
            onboarding_key=onboarding_key,
            project=fresh_project,
            scheduler=fresh_scheduler,
            topology=fresh_topology,
        )
        if binding_error:
            return _result("partial_hold", onboarding_key, attention_reason=binding_error, safe_next_action="Resolve topology commitment drift before any follow-up.")
        assert binding_ref is not None
        original, original_error = _call(owners.topology, "read_completion", onboarding_key, fresh_project)
        expected = _completion_identity(onboarding_key, fresh_project, fresh_scheduler, fresh_topology, retry_binding)
        original_reason = original_error or _validate_persistent_completion(original, expected)
        if original_reason:
            return _result("partial_hold", onboarding_key, attention_reason=original_reason, safe_next_action="Resolve original completion identity drift before any follow-up.")
        return _receipt(onboarding_key, fresh_project, fresh_scheduler, fresh_topology, mutation_performed=False, operation_receipt_refs=(), topology_apply_binding_ref=binding_ref, topology_apply_binding_digest=retry_binding["topology_apply_binding_digest"])
    return _receipt(onboarding_key, fresh_project, fresh_scheduler, fresh_topology, mutation_performed=False, operation_receipt_refs=operation_receipt_refs)


__all__ = ["Owners", "ProjectBindingOwner", "SchedulerBindingOwner", "RoleTopologyOwner", "VERSION", "initialize"]
