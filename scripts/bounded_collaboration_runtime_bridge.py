#!/usr/bin/env python3
"""Read-only owner composition bridge for bounded collaboration onboarding."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from bounded_collaboration_initializer import Owners, initialize
from local_collaboration_ledger import LedgerError, LocalCollaborationLedger
from local_collaboration_scheduler import SchedulerHold, replay_scheduler_state


VERSION = "bounded-collaboration-runtime-bridge-v1"
_PRIVATE = {"path", "root", "repository", "repo", "database", "event", "payload", "native", "thread", "transcript", "tool_output", "stderr", "stdout", "credential", "token", "exception", "message"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class _FrozenDict(dict):
    def __init__(self, value: Mapping[str, Any]):
        dict.__init__(self, value)

    def _immutable(self, *_: Any, **__: Any) -> None:
        raise TypeError("receipt_is_immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _private(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key).lower() in _PRIVATE or _private(item) for key, item in value.items())
    return isinstance(value, (list, tuple)) and any(_private(item) for item in value)


def _receipt(terminal: str, *, attention_reason: str | None, safe_next_action: str, initialization: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    value: dict[str, Any] = {
        "bridge_version": VERSION,
        "mode": "read_only_preflight",
        "mutation_performed": False,
        "production_eligible": False,
        "evidence_class": "fixture_only",
        "terminal_classification": terminal,
        "attention_reason": attention_reason,
        "safe_next_action": safe_next_action,
    }
    if initialization is not None and not _private(initialization):
        value["initialization"] = dict(initialization)
    return _freeze(value)


class ProjectBindingOwner:
    """Only LedgerStore can turn the two locators into a project binding."""

    def __init__(self, projects_root: str | Path, project_root: str | Path):
        self._projects_root = projects_root
        self._project_root = project_root

    def read_binding(self) -> Mapping[str, Any]:
        view = LocalCollaborationLedger.active_path_repo_binding_snapshot(self._projects_root, self._project_root)
        return _freeze({
            "state": "bound",
            "project_id": view.project_id,
            "project_binding_ref": view.project_binding_ref,
            "project_binding_digest": view.project_binding_digest,
            "repository_digest": "sha256:" + view.repository_digest,
            "root_digest": "sha256:" + view.root_digest,
            "authority_generation": view.authority_generation,
            "authority_head": view.authority_head,
        })


class SchedulerBindingOwner:
    """Derive a Work-root binding exclusively from public scheduler replay."""

    def __init__(self, projects_root: str | Path):
        self._projects_root = projects_root

    def read_binding(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        state = replay_scheduler_state(self._projects_root, str(project_binding.get("project_id", "")))
        if state.get("project_id") != project_binding.get("project_id"):
            return {"state": "held", "reason": "scheduler_project_binding_mismatch"}
        if (state.get("authority_generation"), state.get("authority_head")) != (project_binding.get("authority_generation"), project_binding.get("authority_head")):
            return {"state": "held", "reason": "scheduler_project_binding_mismatch"}
        if state.get("scheduler_state") != "enabled" or state.get("local_state") in {"completed", "canceled", "disabled"}:
            return {"state": "held", "reason": "scheduler_or_work_root_unavailable"}
        work_id = state.get("work_id"); owner = state.get("owner_role"); anchor = state.get("durable_anchor_digest")
        if not all(isinstance(item, str) and item for item in (work_id, owner, anchor)):
            return {"state": "held", "reason": "scheduler_or_work_root_invalid"}
        source = {
            "project_binding_digest": project_binding["project_binding_digest"],
            "work_id": work_id,
            "owner_role": owner,
            "durable_anchor_digest": anchor,
            "scheduler_state": state["scheduler_state"],
            "authority_generation": state["authority_generation"],
            "authority_head": state["authority_head"],
        }
        digest = _digest(source)
        return _freeze({
            "state": "bound",
            "project_binding_digest": project_binding["project_binding_digest"],
            "scheduler_binding_ref": "scheduler-binding:" + digest,
            "work_root_ref": "work-root:" + _digest({"work_id": work_id, "owner_role": owner, "durable_anchor_digest": anchor}),
            "scheduler_binding_revision": str(state["authority_generation"]) + ":" + str(state["authority_head"]),
            "scheduler_binding_digest": digest,
        })


class UnavailableTopologyOwner:
    """Ordinary CLI deliberately has no native topology authority."""

    def read_topology(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("topology_owner_unavailable")

    def apply_topology(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("topology_apply_unavailable")

    def read_completion(self, onboarding_key: str, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("topology_owner_unavailable")


class FixtureMissingTopologyOwner:
    """Test-only in-process owner used to exercise I1 planning semantics."""

    def read_topology(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        return _freeze({"state": "missing"})

    def apply_topology(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("fixture_apply_not_authorized")

    def read_completion(self, onboarding_key: str, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        return _freeze({"state": "absent"})


def _validate_locator(value: str | Path, *, directory: bool) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("invalid_locator")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("invalid_locator") from exc
    if str(path) != str(resolved) or (not resolved.is_dir() if directory else not resolved.exists()):
        raise ValueError("invalid_locator")
    return str(resolved)


def run(projects_root: str | Path, project_root: str | Path, onboarding_key: str, *, topology_owner: Any | None = None) -> Mapping[str, Any]:
    """Run the one read-only surface; fixture topology injection is in-process only."""
    try:
        root = _validate_locator(projects_root, directory=True)
        selected = _validate_locator(project_root, directory=True)
        if not isinstance(onboarding_key, str) or not onboarding_key or len(onboarding_key) > 256 or any(ch.isspace() for ch in onboarding_key):
            raise ValueError("invalid_onboarding_key")
    except ValueError:
        return _receipt("schema_or_privacy_failure", attention_reason="invalid_locator_or_onboarding_key", safe_next_action="Use canonical locator-only inputs.")
    try:
        owners = Owners(ProjectBindingOwner(root, selected), SchedulerBindingOwner(root), topology_owner or UnavailableTopologyOwner())
        result = initialize(owners, onboarding_key=onboarding_key, apply_authorized=False)
    except (LedgerError, SchedulerHold):
        return _receipt("owner_unavailable", attention_reason="owner_binding_unavailable", safe_next_action="Restore the owner-backed project and scheduler bindings.")
    except Exception:
        return _receipt("owner_unavailable", attention_reason="owner_binding_unavailable", safe_next_action="Restore the owner-backed project and scheduler bindings.")
    if _private(result):
        return _receipt("schema_or_privacy_failure", attention_reason="owner_privacy_hold", safe_next_action="Remove private owner output before another preflight.")
    terminal = str(result.get("completion_state", "partial_hold"))
    if terminal not in {"topology_plan_ready", "native_ready", "repo_contract_only", "partial_hold", "unavailable", "setup_incomplete"}:
        terminal = "schema_or_privacy_failure"
    return _receipt(terminal, attention_reason=result.get("attention_reason"), safe_next_action=str(result.get("safe_next_action", "Read owner state before any follow-up.")), initialization=result)


def _arguments(argv: list[str]) -> tuple[str, str, str] | None:
    expected = {"--projects-root", "--project-root", "--onboarding-key"}
    if len(argv) != 6 or any(argv[index] not in expected for index in range(0, 6, 2)) or len(set(argv[::2])) != 3:
        return None
    return argv[1], argv[3], argv[5]


def main(argv: list[str] | None = None) -> int:
    parsed = _arguments(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        value = _receipt("schema_or_privacy_failure", attention_reason="invalid_locator_only_arguments", safe_next_action="Use only the three documented locator arguments.")
        print(_canonical(value)); return 3
    value = run(*parsed)
    print(_canonical(value))
    return 0 if value["terminal_classification"] in {"topology_plan_ready", "native_ready"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
