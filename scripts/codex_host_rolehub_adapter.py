#!/usr/bin/env python3
"""Pure, injected-host mapping for Codex threads and logical RoleHub receipts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

CONTRACT = "AF18-codex-host-rolehub-adapter-v1"
PRIVATE = {"prompt", "body", "message", "messages", "content", "transcript", "turns", "output", "tool_output", "raw_log", "history"}

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

@dataclass(frozen=True)
class ThreadMetadata:
    id: str
    cwd: str
    name: str

@runtime_checkable
class CodexHostThreadConnector(Protocol):
    def list_threads(self, cwd: str) -> list[ThreadMetadata]: ...
    def read_thread(self, id: str, include_turns: bool = False) -> ThreadMetadata: ...
    def create_thread(self, cwd: str) -> ThreadMetadata: ...
    def set_thread_name(self, id: str, title: str) -> ThreadMetadata: ...
    def navigate_to_thread(self, id: str) -> Any: ...

def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items() if k not in PRIVATE}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    return value

class CodexHostRoleHubAdapter:
    def __init__(self, host: CodexHostThreadConnector):
        self.host = host
        self._receipts: dict[str, dict[str, Any]] = {}
        self._preimages: dict[str, ThreadMetadata] = {}
        self._seq = 0

    def _receipt(self, plan: dict[str, Any], op: dict[str, Any], status: str, **extra: Any) -> dict[str, Any]:
        self._seq += 1
        fp = digest({k: v for k, v in op.items() if k != "receipt"})
        result = {"operation_id": op["operation_id"], "idempotency_key": op["idempotency_key"], "operation_fingerprint": fp,
                  "opaque_ref": "thread:" + fp[7:31], "sequence": self._seq, "status": status,
                  "project_id": plan["project_id"], "logical_rolehub_id": plan["logical_rolehub_id"]}
        result.update(extra)
        return _safe(result)

    def _read(self, ident: str, cwd: str) -> ThreadMetadata:
        metadata = self.host.read_thread(ident, include_turns=False)
        if not isinstance(metadata, ThreadMetadata) or metadata.id != ident or metadata.cwd != cwd or not metadata.name:
            raise RuntimeError("metadata_mismatch")
        return metadata

    def _validate_plan(self, plan: dict[str, Any]) -> None:
        if not isinstance(plan, dict) or plan.get("contract_version") != CONTRACT:
            raise ValueError("schema_drift")
        if not isinstance(plan.get("operations"), list):
            raise ValueError("schema_drift")
        if set(plan) - {"contract_version", "project_id", "project_root", "logical_rolehub_id", "operations"}:
            raise ValueError("schema_drift")
        allowed = {"operation_id", "action", "idempotency_key", "role", "title", "target_ref", "preimage"}
        for op in plan["operations"]:
            if not isinstance(op, dict) or set(op) - allowed:
                raise ValueError("schema_drift")
            if any(k in op for k in PRIVATE):
                raise ValueError("privacy_boundary")

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        try:
            self._validate_plan(plan)
        except Exception:
            return {"status": "partial_hold", "reason": "schema_drift"}
        applied: list[dict[str, Any]] = []
        try:
            for op in plan["operations"]:
                key = op.get("idempotency_key")
                if not isinstance(key, str) or not isinstance(op.get("operation_id"), str):
                    raise RuntimeError("schema_drift")
                fp = digest({k: v for k, v in op.items() if k != "receipt"})
                old = self._receipts.get(key)
                if old:
                    if old["operation_fingerprint"] != fp:
                        raise RuntimeError("idempotency_conflict")
                    applied.append(old); continue
                action, role = op.get("action"), op.get("role")
                title, cwd = op.get("title") or role, plan["project_root"]
                if action == "create":
                    md = self.host.create_thread(cwd)
                    if not isinstance(md, ThreadMetadata) or md.cwd != cwd:
                        raise RuntimeError("held_runtime_transport_unobservable")
                    self._preimages[key] = md
                    md = self.host.set_thread_name(md.id, title)
                    md = self._read(md.id, cwd)
                    receipt = self._receipt(plan, op, "applied", readback={"digest": digest({"cwd": md.cwd, "name": md.name}), "name": md.name})
                elif action == "reuse":
                    matches = [m for m in self.host.list_threads(cwd) if isinstance(m, ThreadMetadata) and m.cwd == cwd and (not role or m.name == title or role in m.name)]
                    if len(matches) != 1:
                        raise RuntimeError("held_runtime_transport_unobservable")
                    md = self._read(matches[0].id, cwd)
                    receipt = self._receipt(plan, op, "applied", readback={"digest": digest({"cwd": md.cwd, "name": md.name}), "name": md.name})
                elif action == "name":
                    ident = op.get("target_ref")
                    if not isinstance(ident, str) or not ident:
                        raise RuntimeError("held_runtime_transport_unobservable")
                    before = self._read(ident, cwd); self._preimages[key] = before
                    after = self.host.set_thread_name(ident, title); after = self._read(ident, cwd)
                    receipt = self._receipt(plan, op, "applied", preimage={"name": before.name}, readback={"digest": digest({"cwd": after.cwd, "name": after.name}), "name": after.name})
                elif action == "link":
                    receipt = self._receipt(plan, op, "applied", native_link=False, logical_link=True, target_ref="opaque")
                elif action == "navigate":
                    ident = op.get("target_ref")
                    if not isinstance(ident, str) or not ident:
                        raise RuntimeError("held_runtime_transport_unobservable")
                    self._read(ident, cwd)
                    try:
                        self.host.navigate_to_thread(ident)
                        receipt = self._receipt(plan, op, "applied", navigation="native", target_ref="opaque")
                    except (AttributeError, NotImplementedError):
                        receipt = self._receipt(plan, op, "applied", navigation="client_fallback", target_ref="opaque")
                else:
                    raise RuntimeError("held_runtime_transport_unobservable")
                self._receipts[key] = receipt; applied.append(receipt)
            return {"status": "ready", "project_id": plan["project_id"], "logical_rolehub_id": plan["logical_rolehub_id"], "operations": applied}
        except Exception:
            return {"status": "setup_incomplete", "reason": "held_runtime_transport_unobservable", "operations": applied}

    def rollback(self, plan: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        # Host deletion is intentionally absent; rollback is metadata-only and
        # reports what would need reversal without claiming native deletion.
        ops = [r.get("operation_id") for r in result.get("operations", []) if isinstance(r, dict)]
        return {"status": "rollback_incomplete", "reversed_operation_ids": list(reversed([x for x in ops if x]))}

def apply_rolehub(plan: dict[str, Any], host: CodexHostThreadConnector) -> dict[str, Any]:
    return CodexHostRoleHubAdapter(host).apply(plan)
