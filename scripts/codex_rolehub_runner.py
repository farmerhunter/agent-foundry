#!/usr/bin/env python3
"""Bounded, privacy-safe native Codex RoleHub runner.

The runner accepts a JSON-RPC client supplied by the host.  It never starts an
app-server and deliberately has no shell, filesystem, history, or deletion
surface.  Native thread ids remain in process memory and receipts contain only
opaque references and digests.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover
    yaml = None
    Draft202012Validator = None

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "codex-rolehub-runner.schema.yaml"
CONTRACT = "AF18-codex-rolehub-runner-v1"
ALLOWED_METHODS = {"initialize", "initialized", "thread/list", "thread/read", "thread/start", "thread/name/set"}
FORBIDDEN_METHODS = {"history", "turn/list", "thread/archive", "thread/delete", "turn/start", "shell", "filesystem", "config", "plugin", "mcp"}
PRIVATE_KEYS = {"prompt", "body", "message", "messages", "content", "transcript", "turns", "tool_output", "raw_log"}


class RunnerHold(Exception):
    def __init__(self, status: str, reason: str):
        self.status, self.reason = status, reason


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if k not in PRIVATE_KEYS}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


class CodexRoleHubRunner:
    def __init__(self, rpc: Callable[[str, dict[str, Any] | None], Any], *, runtime_id: str):
        self.rpc = rpc
        self.runtime_id = runtime_id
        self.native_ids: dict[str, str] = {}
        self.role_native: dict[str, str] = {}
        self.receipts: dict[str, dict[str, Any]] = {}
        self._sequence = 0

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if method not in ALLOWED_METHODS:
            raise RunnerHold("partial_hold", "method_not_allowlisted")
        result = self.rpc(method, params or {})
        return scrub(result)

    def _readback(self, native_id: str) -> dict[str, Any]:
        # includeTurns is explicitly false; the runner never reads transcript history.
        value = self._call("thread/read", {"threadId": native_id, "includeTurns": False})
        if not isinstance(value, dict):
            raise RunnerHold("partial_hold", "readback_not_object")
        result = {"digest": digest(value), "opaque_ref": "native:" + digest(native_id)[:24]}
        # Titles are metadata needed for a bounded reverse receipt; no body or turns
        # are retained.  The native id itself is never put in a durable receipt.
        if isinstance(value.get("name"), str):
            result["title"] = value["name"]
        elif isinstance(value.get("title"), str):
            result["title"] = value["title"]
        return result

    def preflight(self) -> dict[str, Any]:
        try:
            init = self._call("initialize", {})
            self._call("initialized", {})
            listing = self._call("thread/list", {})
            return {"status": "ready", "runtime_id": self.runtime_id, "methods": sorted(ALLOWED_METHODS), "initialize_digest": digest(init), "thread_list_digest": digest(listing)}
        except RunnerHold as hold:
            return {"status": hold.status, "reason": hold.reason}
        except Exception:
            return {"status": "partial_hold", "reason": "native_preflight_error"}

    def _validate(self, plan: dict[str, Any]) -> None:
        if not isinstance(plan, dict) or plan.get("contract_version") != CONTRACT:
            raise RunnerHold("partial_hold", "schema_drift")
        if plan.get("runtime_id") and plan["runtime_id"] != self.runtime_id:
            raise RunnerHold("partial_hold", "foreign_runtime")
        if Draft202012Validator is None or yaml is None:
            raise RunnerHold("partial_hold", "schema_validator_unavailable")
        try:
            schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
            errors = list(Draft202012Validator(schema).iter_errors(plan))
        except Exception:
            raise RunnerHold("partial_hold", "schema_validator_error")
        if errors:
            raise RunnerHold("partial_hold", "schema_drift")
        evidence = plan.get("capability_evidence")
        if not isinstance(evidence, dict) or evidence.get("runtime_id") != self.runtime_id or evidence.get("trusted") is not True:
            raise RunnerHold("partial_hold", "untrusted_capability_evidence")
        methods = set(evidence.get("methods", []))
        if not ALLOWED_METHODS.issubset(methods):
            raise RunnerHold("partial_hold", "required_method_unavailable")
        if methods & FORBIDDEN_METHODS:
            raise RunnerHold("partial_hold", "forbidden_method_observed")

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        try:
            self._validate(plan)
            applied: list[dict[str, Any]] = []
            for operation in plan["operations"]:
                applied.append(self._operation(plan, operation))
            return {"status": "ready", "project_id": plan["project_id"], "logical_rolehub_id": plan["logical_rolehub_id"], "operations": applied}
        except RunnerHold as hold:
            return {"status": hold.status, "reason": hold.reason, "operations": []}

    def _operation(self, plan: dict[str, Any], op: dict[str, Any]) -> dict[str, Any]:
        key = op["idempotency_key"]
        fingerprint = digest({k: v for k, v in op.items() if k not in {"receipt"}})
        existing = self.receipts.get(key)
        if existing:
            if existing["operation_fingerprint"] != fingerprint:
                raise RunnerHold("partial_hold", "foreign_idempotency_key")
            return deepcopy(existing)
        action = op["action"]
        if action in {"link", "navigate"}:
            # Logical receipts only; never claim a native link/navigation.
            self._sequence += 1
            receipt = self._receipt(plan, op, "partial_hold", {"availability": "unavailable"})
            self.receipts[key] = receipt
            return receipt
        native_id = self.native_ids.get(key)
        created = False
        if action == "create":
            result = self._call("thread/start", {"cwd": plan.get("capability_evidence", {}).get("cwd", "")})
            if not isinstance(result, dict):
                raise RunnerHold("setup_incomplete", "thread_start_no_receipt")
            native_id = result.get("threadId") or result.get("id")
            if not isinstance(native_id, str) or not native_id:
                raise RunnerHold("setup_incomplete", "native_id_unavailable")
            self.native_ids[key] = native_id
            self.role_native[op["role"]] = native_id
            created = True
        elif action == "reuse":
            native_id = op.get("target_ref")
            if not isinstance(native_id, str) or not native_id.startswith("native:"):
                raise RunnerHold("partial_hold", "foreign_native_reference")
            native_id = self.native_ids.get(key)
            if not native_id:
                raise RunnerHold("partial_hold", "native_reference_not_in_process")
        elif action == "name":
            native_id = self.role_native.get(op["role"])
            if not native_id:
                raise RunnerHold("partial_hold", "native_reference_not_in_process")
        if not native_id:
            raise RunnerHold("partial_hold", "native_id_missing")
        self.native_ids[key] = native_id
        before = self._readback(native_id)
        expected = op.get("preimage_digest")
        if expected and expected != before["digest"]:
            raise RunnerHold("partial_hold", "stale_preimage")
        if action == "name":
            self._call("thread/name/set", {"threadId": native_id, "name": op.get("title", "")})
        after = self._readback(native_id)
        if action == "name" and isinstance(before.get("title"), str):
            after["previous_title"] = before["title"]
        self._sequence += 1
        receipt = self._receipt(plan, op, "applied", {**after, "created": created, "native_id_held_in_memory": True})
        self.receipts[key] = receipt
        return receipt

    def rollback(self, receipts: list[dict[str, Any]]) -> dict[str, Any]:
        """Reverse title changes in reverse sequence; never delete a new thread."""
        reversed_ids: list[str] = []
        for receipt in sorted(receipts, key=lambda item: item.get("sequence", 0), reverse=True):
            if receipt.get("status") != "applied":
                continue
            readback = receipt.get("readback", {})
            previous = readback.get("previous_title") if isinstance(readback, dict) else None
            key = receipt.get("idempotency_key")
            native_id = self.native_ids.get(key)
            if not isinstance(previous, str) or not native_id:
                return {"status": "rollback_incomplete", "reason": "reverse_receipt_unavailable", "reversed_operation_ids": reversed_ids}
            try:
                self._call("thread/name/set", {"threadId": native_id, "name": previous})
            except Exception:
                return {"status": "rollback_incomplete", "reason": "reverse_call_failed", "reversed_operation_ids": reversed_ids}
            reversed_ids.append(receipt.get("operation_id", ""))
        return {"status": "complete", "reversed_operation_ids": reversed_ids}

    def _receipt(self, plan: dict[str, Any], op: dict[str, Any], status: str, readback: dict[str, Any]) -> dict[str, Any]:
        return {"operation_id": op["operation_id"], "idempotency_key": op["idempotency_key"], "operation_fingerprint": digest({k: v for k, v in op.items() if k != "receipt"}), "opaque_ref": "receipt:" + digest(op["idempotency_key"])[:24], "project_id": plan["project_id"], "logical_rolehub_id": plan["logical_rolehub_id"], "role": op["role"], "readback": scrub(readback), "sequence": self._sequence, "status": status}
