"""Invocation-scoped SQLite bridge for the collaboration helper.

This module is deliberately a thin adapter over ``LocalCollaborationLedger``.
It owns discovery and the deterministic legacy-event identity bridge only; the
ledger remains the sole storage and replay authority.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from local_collaboration_ledger import (
    LedgerConflictError,
    LedgerError,
    LocalCollaborationLedger,
    _canonical,
    _contains_forbidden,
    _json_depth,
    _TYPE,
)

ADAPTER_VERSION = "orch-02-2.v1"
ADAPTER_NAMESPACE = uuid.UUID("f1f6d6f8-0b2b-5f8f-9cb3-2d1f0dfebf43")
DEFAULT_PROJECTS_ROOT = Path.home() / ".agent-foundry" / "projects"


class SQLiteWorkflowError(RuntimeError):
    pass


def logical_event_uuid(project_id: str, logical_event_id: str) -> str:
    """Return stable UUIDv5 for the canonical tuple [project_id, logical_id]."""
    if not project_id or not logical_event_id:
        raise ValueError("project_id and logical_event_id are required")
    canonical = json.dumps([str(project_id), str(logical_event_id)], ensure_ascii=False, separators=(",", ":"))
    return str(uuid.uuid5(ADAPTER_NAMESPACE, canonical))


def _root(projects_root: str | os.PathLike[str] | None) -> Path:
    path = Path(projects_root or DEFAULT_PROJECTS_ROOT).expanduser().resolve()
    if path.exists() and (not path.is_dir() or path.is_symlink()):
        raise SQLiteWorkflowError("projects_root must be a regular directory")
    return path


def _hold(reason: str, *, detail: str | None = None, mutation_performed: bool = False) -> dict[str, Any]:
    return {"status": "hold", "reason": reason, "detail": detail, "mutation_performed": mutation_performed}


def discover(projects_root: str | os.PathLike[str], binding_type: str, binding_value: str) -> dict[str, Any]:
    """Discover exactly one healthy authority without creating or mutating."""
    root = _root(projects_root)
    try:
        matches = LocalCollaborationLedger.discover_by_binding(root, binding_type, binding_value)
    except Exception as exc:  # corruption, permission, schema, or ambiguity is a hold
        return _hold("discovery_failed", detail=str(exc))
    if len(matches) > 1:
        return _hold("binding_ambiguous", detail="multiple matching SQLite authorities")
    if not matches:
        return {"status": "zero_match", "projects_root": str(root), "binding_type": binding_type, "binding_value": binding_value}
    project_id = matches[0]
    path = root / project_id / "collaboration.db"
    try:
        ledger = LocalCollaborationLedger(db_path=path, create=False)
        metadata = ledger.metadata()
        receipt = {"project_id": ledger.project_id, "path": str(path), "metadata": metadata, "pragma": ledger.pragma_receipt()}
        ledger.close()
        return {"status": "reused", "project_id": project_id, "receipt": receipt}
    except Exception as exc:
        return _hold("authority_open_failed", detail=str(exc))


def _open_existing(projects_root: Path, project_id: str, *, writable: bool = False) -> LocalCollaborationLedger:
    if not project_id:
        raise ValueError("project_id is required")
    path = projects_root / project_id / "collaboration.db"
    if not path.is_file() or path.is_symlink() or path.parent.name != project_id:
        raise FileNotFoundError("existing SQLite authority is required")
    if not writable:
        return LocalCollaborationLedger(db_path=path, create=False)
    probe = LocalCollaborationLedger(db_path=path, create=False)
    if probe.project_id != project_id:
        probe.close(); raise ValueError("project identity mismatch")
    probe.close()
    return LocalCollaborationLedger(db_path=path, create=True)


def _create(projects_root: Path, binding_type: str, binding_value: str) -> tuple[LocalCollaborationLedger, dict[str, Any]]:
    ledger = LocalCollaborationLedger.create_project(projects_root=projects_root)
    try:
        decision = ledger.bind_project(binding_type, binding_value)
        return ledger, {"project_id": ledger.project_id, "path": str(ledger.path), "binding": decision, "metadata": ledger.metadata()}
    except Exception:
        ledger.close()
        raise


def _compact(event: Mapping[str, Any], project_id: str) -> dict[str, Any]:
    logical_id = str(event.get("event_id") or "")
    if not logical_id:
        raise ValueError("event_id is required")
    payload = dict(event.get("payload") if isinstance(event.get("payload"), Mapping) else {})
    payload["logical_event_id"] = logical_id
    payload["helper_event"] = dict(event)
    return {
        "event_type": str(event.get("event_type") or "evidence"),
        "event_id": logical_event_uuid(project_id, logical_id),
        "payload": payload,
        "actor": str(event.get("actor_role") or "adapter"),
        "source": "orch-02-2",
        "root": project_id,
    }


def _validate_legacy_batch(events: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    values = list(events)
    if not values:
        raise ValueError("at least one event is required")
    if len(values) > 100:
        raise ValueError("batch exceeds 100 events")
    total_size = 0
    for event in values:
        if not isinstance(event, Mapping) or not str(event.get("event_id") or ""):
            raise ValueError("event_id is required")
        event_type = str(event.get("event_type") or "evidence")
        if not _TYPE.fullmatch(event_type):
            raise ValueError("invalid event_type")
        if not isinstance(event.get("payload", {}), Mapping):
            raise ValueError("event payload must be an object")
        payload = dict(event.get("payload") or {})
        compact = dict(payload)
        compact["logical_event_id"] = str(event["event_id"])
        compact["helper_event"] = dict(event)
        if _contains_forbidden(compact):
            raise ValueError("privacy-forbidden payload")
        _json_depth(compact)
        encoded = _canonical(compact).encode()
        if len(encoded) > 64 * 1024:
            raise ValueError("payload exceeds 64 KiB")
        total_size += len(encoded)
        for field in ("actor_role",):
            value = event.get(field)
            if value is not None and (not isinstance(value, str) or not value or len(value) > 256 or any(token in value.lower() for token in ("transcript", "raw_transcript", "tool_output", "prompt", "secret", "native_history"))):
                raise ValueError(f"invalid {field}")
    if total_size > 1024 * 1024:
        raise ValueError("batch exceeds 1 MiB")
    return values


def _receipt(ledger: LocalCollaborationLedger, *, operation: str, count: int, mutation: bool) -> dict[str, Any]:
    return {"status": "ok", "operation": operation, "project_id": ledger.project_id, "event_count": count, "mutation_performed": mutation, "receipt": {"path": str(ledger.path), "metadata": ledger.metadata()}}


def fresh_onboarding(projects_root: str | os.PathLike[str], binding_type: str, binding_value: str) -> dict[str, Any]:
    root = _root(projects_root)
    found = discover(root, binding_type, binding_value)
    if found["status"] == "reused":
        return found
    if found["status"] != "zero_match":
        return found
    try:
        ledger, receipt = _create(root, binding_type, binding_value)
        ledger.close()
        return {"status": "created", "project_id": receipt["project_id"], "mutation_performed": True, "receipt": receipt, "jsonl_fallback": False}
    except Exception as exc:
        return _hold("onboarding_failed", detail=str(exc))


def accepted_backfill(projects_root: str | os.PathLike[str], binding_type: str, binding_value: str, events: Iterable[Mapping[str, Any]], *, accepted: bool = True) -> dict[str, Any]:
    if not accepted:
        return _hold("backfill_not_accepted", detail="explicit accepted=True is required")
    try:
        validated_events = _validate_legacy_batch(events)
    except Exception as exc:
        return _hold("backfill_validation_failed", detail=str(exc))
    root = _root(projects_root); found = discover(root, binding_type, binding_value)
    if found["status"] == "zero_match":
        try:
            ledger, _ = _create(root, binding_type, binding_value)
        except Exception as exc:
            return _hold("onboarding_failed", detail=str(exc))
    elif found["status"] == "reused":
        try: ledger = _open_existing(root, found["project_id"], writable=True)
        except Exception as exc: return _hold("authority_open_failed", detail=str(exc))
    else: return found
    try:
        batch = [_compact(event, ledger.project_id) for event in validated_events]
        before = len(ledger.list_events())
        rows = ledger.accept_compact_events(batch)
        appended = len(ledger.list_events()) - before
        return {**_receipt(ledger, operation="accepted_backfill", count=len(rows), mutation=bool(appended)), "appended_count": appended, "duplicate_count": len(rows) - appended, "logical_event_ids": [str(e.get("event_id")) for e in validated_events], "jsonl_fallback": False}
    except Exception as exc:
        return _hold("backfill_failed", detail=str(exc))
    finally:
        ledger.close()


def local_action_batch(projects_root: str | os.PathLike[str], project_id: str, events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    root = _root(projects_root)
    try:
        validated_events = _validate_legacy_batch(events)
    except Exception as exc:
        return _hold("local_action_validation_failed", detail=str(exc))
    try: ledger = _open_existing(root, project_id, writable=True)
    except Exception as exc: return _hold("authority_open_failed", detail=str(exc))
    try:
        before = len(ledger.list_events())
        batch = [_compact(event, ledger.project_id) for event in validated_events]
        rows = ledger.accept_compact_events(batch)
        after = len(ledger.list_events())
        appended = after - before
        return {**_receipt(ledger, operation="local_action", count=len(rows), mutation=bool(appended)), "appended_count": appended, "duplicate_count": len(rows) - appended, "logical_event_ids": [str(e.get("event_id")) for e in validated_events], "jsonl_fallback": False}
    except Exception as exc: return _hold("local_action_failed", detail=str(exc))
    finally: ledger.close()


def append_event(projects_root: str | os.PathLike[str], project_id: str, event: Mapping[str, Any]) -> dict[str, Any]:
    return local_action_batch(projects_root, project_id, [event])


def accepted_backfill_existing(projects_root: str | os.PathLike[str], project_id: str, events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    root = _root(projects_root)
    try:
        validated_events = _validate_legacy_batch(events)
        ledger = _open_existing(root, project_id, writable=True)
    except Exception as exc:
        return _hold("authority_open_failed", detail=str(exc))
    try:
        before = len(ledger.list_events())
        rows = ledger.accept_compact_events([_compact(event, ledger.project_id) for event in validated_events])
        appended = len(ledger.list_events()) - before
        return {**_receipt(ledger, operation="accepted_backfill", count=len(rows), mutation=bool(appended)), "appended_count": appended, "duplicate_count": len(rows) - appended, "logical_event_ids": [str(e.get("event_id")) for e in validated_events], "jsonl_fallback": False}
    except Exception as exc:
        return _hold("backfill_failed", detail=str(exc))
    finally:
        ledger.close()


def read_events(projects_root: str | os.PathLike[str], project_id: str) -> list[dict[str, Any]]:
    ledger = _open_existing(_root(projects_root), project_id)
    try:
        result = []
        for event in ledger.list_events():
            payload = dict(event.payload)
            helper = payload.get("helper_event")
            if isinstance(helper, dict):
                item = dict(helper); item["event_id"] = payload.get("logical_event_id", item.get("event_id")); item["validation_status"] = "valid"
            else:
                item = {"event_id": payload.get("logical_event_id", event.event_id), "event_type": event.event_type, "payload": payload, "occurred_at": event.created_at}
            work_item = item.get("work_item") if isinstance(item.get("work_item"), dict) else {}
            item.setdefault("work_item_key", str(work_item.get("id") or f"{work_item.get('repo', 'unknown')}#{work_item.get('type', 'issue')}:{work_item.get('number', 'unknown')}"))
            result.append(item)
        return result
    finally: ledger.close()


__all__ = ["ADAPTER_NAMESPACE", "ADAPTER_VERSION", "SQLiteWorkflowError", "logical_event_uuid", "discover", "fresh_onboarding", "accepted_backfill", "accepted_backfill_existing", "local_action_batch", "append_event", "read_events"]
