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

# This is a static, checked-in description of the codex-cli 0.133.0 v2
# app-server contract.  It is data for diagnosis, not a transport client.
START_CONTRACT = {
    "cli_version": "codex-cli 0.133.0",
    "protocol_variant": "v2",
    "start_method": "thread/start",
    "start_request": {
        "required": ["cwd"],
        "optional": [
            "approvalPolicy", "approvalsReviewer", "baseInstructions", "config",
            "developerInstructions", "sandbox", "serviceName", "ephemeral",
            "sessionStartSource", "personality", "model", "modelProvider",
            "serviceTier", "threadSource",
        ],
    },
    "start_response": {
        "required": ["approvalPolicy", "approvalsReviewer", "cwd", "model", "modelProvider", "sandbox", "thread"],
        "extract": "thread",
        # The protocol requires id/cwd for correlation; name is optional and
        # may be null in the upstream Thread object.
        "thread_required": ["id", "cwd"],
        "thread_optional": ["name"],
    },
    "read_method": "thread/read",
    "read_request": {"required": ["threadId"], "optional": ["includeTurns"], "includeTurns": False},
    "correlation": ["thread.id", "thread.cwd"],
}


def diagnose_thread_start_contract(sample: Any) -> dict[str, Any]:
    """Validate a captured, metadata-only protocol sample without I/O.

    The sample is intentionally a plain fixture: callers must provide the
    static contract evidence and sanitized response objects.  No app-server,
    filesystem, transcript, or raw error access occurs here.
    """
    safe = {"status": "held_start_contract_unresolved", "contract": "AF18-codex-rolehub-runner-v1"}
    def hold(reason: str, status: str = "held_start_contract_unresolved") -> dict[str, Any]:
        safe["status"], safe["reason"] = status, reason
        return safe
    if not isinstance(sample, dict):
        return hold("sample_not_object")
    if sample.get("cli_version") != START_CONTRACT["cli_version"] or sample.get("protocol_variant") != START_CONTRACT["protocol_variant"]:
        return hold("version_or_protocol_mismatch")
    if sample.get("start_method") != START_CONTRACT["start_method"] or sample.get("read_method") != START_CONTRACT["read_method"]:
        return hold("method_mismatch")
    request = sample.get("start_request")
    if not isinstance(request, dict) or not isinstance(request.get("cwd"), str) or not request["cwd"]:
        return hold("start_required_cwd_missing")
    allowed_request = set(START_CONTRACT["start_request"]["required"] + START_CONTRACT["start_request"]["optional"])
    if set(request) - allowed_request or any(not isinstance(k, str) for k in request):
        return hold("start_request_unknown_field")
    string_fields = allowed_request - {"config", "ephemeral"}
    if any(field in request and not isinstance(request[field], str) for field in string_fields):
        return hold("start_request_type_error")
    if "config" in request and not isinstance(request["config"], dict):
        return hold("start_request_type_error")
    if "ephemeral" in request and not isinstance(request["ephemeral"], bool):
        return hold("start_request_type_error")
    response = sample.get("start_response")
    if not isinstance(response, dict):
        return hold("start_response_missing", "setup_incomplete")
    if response.get("protocol_error") is True or "error" in response:
        return hold("protocol_error", "setup_incomplete")
    allowed_response = set(START_CONTRACT["start_response"]["required"] + ["serviceTier", "instructionSources", "reasoningEffort"])
    if set(response) - allowed_response:
        return hold("start_response_unknown_field", "setup_incomplete")
    required = START_CONTRACT["start_response"]["required"]
    if any(field not in response for field in required):
        return hold("start_response_required_missing", "setup_incomplete")
    thread = response.get("thread")
    if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
        return hold("nested_thread_id_missing", "setup_incomplete")
    if not isinstance(thread.get("cwd"), str) or ("name" in thread and thread["name"] is not None and not isinstance(thread["name"], str)):
        return hold("nested_thread_metadata_type_error", "setup_incomplete")
    if not isinstance(thread.get("cwd"), str) or thread["cwd"] != request["cwd"]:
        return hold("foreign_cwd", "setup_incomplete")
    read = sample.get("readback")
    if not isinstance(read, dict) or not isinstance(read.get("thread"), dict):
        return hold("readback_missing", "setup_incomplete")
    read_thread = read["thread"]
    if read_thread.get("id") != thread["id"] or read_thread.get("cwd") != request["cwd"]:
        return hold("readback_correlation_mismatch", "setup_incomplete")
    safe.update({"status": "ready", "method": START_CONTRACT["start_method"], "response_path": "thread", "opaque_ref": "native:" + digest(thread["id"])[8:32]})
    return safe


# Short alias for callers that use the contract's noun rather than the RPC
# method name.
diagnose_start_contract = diagnose_thread_start_contract


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
        self.native_cwds: dict[str, str] = {}
        self.role_native: dict[str, str] = {}
        self.receipts: dict[str, dict[str, Any]] = {}
        self.rollback_records: dict[str, dict[str, Any]] = {}
        self._sequence = 0

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if method not in ALLOWED_METHODS:
            raise RunnerHold("partial_hold", "method_not_allowlisted")
        result = self.rpc(method, params or {})
        return scrub(result)

    def _readback(self, native_id: str) -> dict[str, Any]:
        # includeTurns is explicitly false; the runner never reads transcript history.
        value = self._call("thread/read", {"threadId": native_id, "includeTurns": False})
        metadata = self._decode_thread(value, expected_id=native_id, expected_cwd=self.native_cwds.get(native_id), reason_prefix="readback")
        result = {"digest": digest(metadata), "opaque_ref": "native:" + digest(native_id)[:24]}
        # Titles are metadata needed for a bounded reverse receipt; no body or turns
        # are retained.  The native id itself is never put in a durable receipt.
        result["title"] = metadata["name"]
        return result

    def _decode_thread(
        self,
        value: Any,
        *,
        expected_id: str | None = None,
        expected_cwd: str | None = None,
        reason_prefix: str,
    ) -> dict[str, str]:
        """Decode app-server 0.133.0 nested Thread*Response metadata only."""
        if not isinstance(value, dict) or not isinstance(value.get("thread"), dict):
            raise RunnerHold("setup_incomplete", reason_prefix + "_malformed")
        thread = value["thread"]
        thread_id, cwd, name = thread.get("id"), thread.get("cwd"), thread.get("name")
        if not all(isinstance(item, str) and item for item in (thread_id, cwd)) or not isinstance(name, str):
            raise RunnerHold("setup_incomplete", reason_prefix + "_missing_metadata")
        if expected_id is not None and thread_id != expected_id:
            raise RunnerHold("partial_hold", reason_prefix + "_foreign_id")
        if expected_cwd is not None and cwd != expected_cwd:
            raise RunnerHold("partial_hold", reason_prefix + "_foreign_cwd")
        return {"id": thread_id, "cwd": cwd, "name": name}

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
        applied: list[dict[str, Any]] = []
        try:
            self._validate(plan)
            for operation in plan["operations"]:
                try:
                    applied.append(self._operation(plan, operation))
                except RunnerHold as hold:
                    if operation.get("action") == "create" and hold.status == "setup_incomplete":
                        applied.append(self._failure_receipt(plan, operation, "setup_incomplete", hold.reason))
                    raise
                except Exception:
                    if operation.get("action") == "create":
                        applied.append(self._failure_receipt(plan, operation, "setup_incomplete", "native_call_error"))
                        raise RunnerHold("setup_incomplete", "native_call_error")
                    raise RunnerHold("partial_hold", "native_call_error")
            return {"status": "ready", "project_id": plan["project_id"], "logical_rolehub_id": plan["logical_rolehub_id"], "operations": applied}
        except RunnerHold as hold:
            return {"status": hold.status, "reason": hold.reason, "operations": applied}
        except Exception:
            # Do not surface host errors, RPC payloads, or exception text in a
            # durable receipt.  The Coordinator can request an independent retry.
            return {"status": "partial_hold", "reason": "native_call_error", "operations": applied}

    def _failure_receipt(self, plan: dict[str, Any], op: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
        receipt = self._receipt(plan, op, status, {"availability": "unknown", "reason": reason})
        self.receipts[op["idempotency_key"]] = deepcopy(receipt)
        return receipt

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
            cwd = plan.get("capability_evidence", {}).get("cwd")
            if not isinstance(cwd, str) or not cwd:
                raise RunnerHold("partial_hold", "cwd_unproven")
            result = self._call("thread/start", {"cwd": cwd})
            metadata = self._decode_thread(result, expected_cwd=cwd, reason_prefix="thread_start")
            native_id = metadata["id"]
            self.native_ids[key] = native_id
            self.native_cwds[native_id] = cwd
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
        if action == "create" and isinstance(op.get("title"), str) and op["title"]:
            self._call("thread/name/set", {"threadId": native_id, "name": op["title"]})
        elif action == "name":
            self._call("thread/name/set", {"threadId": native_id, "name": op.get("title", "")})
        after = self._readback(native_id)
        if action == "name" and isinstance(before.get("title"), str):
            after["previous_title"] = before["title"]
        self._sequence += 1
        receipt = self._receipt(plan, op, "applied", {**after, "created": created, "native_id_held_in_memory": True})
        self.receipts[key] = deepcopy(receipt)
        if action == "name":
            self.rollback_records[key] = {"fingerprint": receipt["operation_fingerprint"], "previous_title": before.get("title"), "native_id": native_id, "operation_id": op["operation_id"]}
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
            stored_receipt = self.receipts.get(key)
            stored = self.rollback_records.get(key)
            if not stored_receipt or receipt != stored_receipt or not stored or receipt.get("operation_fingerprint") != stored.get("fingerprint") or previous != stored.get("previous_title"):
                return {"status": "rollback_incomplete", "reason": "reverse_receipt_mismatch", "reversed_operation_ids": reversed_ids}
            native_id = stored.get("native_id")
            if not isinstance(previous, str) or not native_id:
                return {"status": "rollback_incomplete", "reason": "reverse_receipt_unavailable", "reversed_operation_ids": reversed_ids}
            try:
                current = self._readback(native_id)
            except Exception:
                return {"status": "rollback_incomplete", "reason": "current_readback_unavailable", "reversed_operation_ids": reversed_ids}
            expected_readback = stored_receipt.get("readback", {})
            if not isinstance(expected_readback, dict) or current.get("digest") != expected_readback.get("digest") or current.get("title") != expected_readback.get("title"):
                return {"status": "rollback_incomplete", "reason": "current_preimage_changed", "reversed_operation_ids": reversed_ids}
            try:
                self._call("thread/name/set", {"threadId": native_id, "name": previous})
            except Exception:
                return {"status": "rollback_incomplete", "reason": "reverse_call_failed", "reversed_operation_ids": reversed_ids}
            reversed_ids.append(receipt.get("operation_id", ""))
        return {"status": "complete", "reversed_operation_ids": reversed_ids}

    def _receipt(self, plan: dict[str, Any], op: dict[str, Any], status: str, readback: dict[str, Any]) -> dict[str, Any]:
        return {"operation_id": op["operation_id"], "idempotency_key": op["idempotency_key"], "operation_fingerprint": digest({k: v for k, v in op.items() if k != "receipt"}), "opaque_ref": "receipt:" + digest(op["idempotency_key"])[:24], "project_id": plan["project_id"], "logical_rolehub_id": plan["logical_rolehub_id"], "role": op["role"], "readback": scrub(readback), "sequence": self._sequence, "status": status}
