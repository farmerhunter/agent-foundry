#!/usr/bin/env python3
"""Build a side-effect-free native bounded-collaboration onboarding plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any


VERSION = "bounded-collaboration-onboarding-v2"
DURABLE_ROLES = ("Coordinator", "Durable Architect")
TRANSIENT_ROLES = ("Implementer", "Reviewer", "Tester", "Harvester")
CAPABILITIES = ("list_projects", "list_threads", "create_thread", "read_thread", "wait_threads", "send_message_to_thread")
FORBIDDEN_KEYS = {"transcript", "raw_transcript", "messages", "prompt", "content", "notes", "tool_output", "raw_content", "raw_tool_output", "private_session", "session_path", "database_path"}
ALLOWED_ROOT_KEYS = {"onboarding_version", "request", "runtime_capabilities", "existing_roles", "repository_state", "operation_receipts"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def key_for(project_id: str, kind: str, subject: str, onboarding_key: str) -> str:
    value = {"project_id": project_id, "kind": kind, "subject": subject, "onboarding_key": onboarding_key, "version": VERSION}
    return "onboard:" + digest(value).split(":", 1)[1]


def contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in FORBIDDEN_KEYS or contains_forbidden(item) for key, item in value.items())
    return isinstance(value, list) and any(contains_forbidden(item) for item in value)


def has_unknown_input(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) - ALLOWED_ROOT_KEYS:
        return True
    request = value.get("request")
    identity = request.get("project_identity") if isinstance(request, dict) else None
    runtime = value.get("runtime_capabilities")
    repo = value.get("repository_state")
    if not isinstance(request, dict) or set(request) - {"project_identity", "onboarding_key", "apply_authorized", "reuse_policy", "handshake_requested", "role_display_names"}:
        return True
    if not isinstance(identity, dict) or set(identity) - {"project_id", "repository", "integration_branch"}:
        return True
    names = request.get("role_display_names", {})
    if not isinstance(names, dict) or set(names) - set(DURABLE_ROLES):
        return True
    if not isinstance(repo, dict) or set(repo) - {"dirty", "dirty_preserved"}:
        return True
    if not isinstance(runtime, dict) or set(runtime) != {"operations"}:
        return True
    capabilities = runtime.get("operations")
    if not isinstance(capabilities, dict) or set(capabilities) != set(CAPABILITIES):
        return True
    if any(not isinstance(item, dict) or set(item) != {"status"} for item in capabilities.values()):
        return True
    role_fields = {"project_id", "role", "thread_id", "state", "display_name"}
    existing = value.get("existing_roles")
    if not isinstance(existing, list) or any(not isinstance(item, dict) or set(item) - role_fields for item in existing):
        return True
    receipt_fields = {"idempotency_key", "status", "receipt_ref", "operation_fingerprint", "result_ref", "pending_task_id", "evidence"}
    receipts = value.get("operation_receipts", [])
    return not isinstance(receipts, list) or any(not isinstance(item, dict) or set(item) - receipt_fields or ("evidence" in item and not isinstance(item["evidence"], dict)) for item in receipts)


def operation(identity: dict[str, Any], onboarding_key: str, kind: str, subject: str, preimage: dict[str, Any], desired_state: dict[str, Any], depends_on: list[str] | None = None) -> dict[str, Any]:
    item = {"kind": kind, "subject": subject, "idempotency_key": key_for(identity["project_id"], kind, subject, onboarding_key), "preimage": preimage, "desired_state": desired_state}
    if depends_on:
        item["depends_on"] = depends_on
    item["operation_fingerprint"] = digest(item)
    return item


def receipt_by_key(receipts: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(receipts, list):
        return {}
    return {item.get("idempotency_key"): item for item in receipts if isinstance(item, dict) and isinstance(item.get("idempotency_key"), str)}


def validate_receipts(receipts: Any, operations: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if receipts is None:
        return {}, []
    if not isinstance(receipts, list) or len(receipts) > len(operations):
        return {}, ["invalid_receipt_sequence"]
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, item in enumerate(receipts):
        planned = operations[index]
        key = item.get("idempotency_key") if isinstance(item, dict) else None
        status = item.get("status") if isinstance(item, dict) else None
        if not isinstance(item, dict) or key != planned["idempotency_key"]:
            errors.append("invalid_receipt_sequence")
        elif key in found:
            errors.append("duplicate_receipt")
        elif status not in {"applied", "failed", "not_attempted", "setup_pending"}:
            errors.append("invalid_receipt_status")
        elif status in {"applied", "failed", "setup_pending"} and not item.get("receipt_ref"):
            errors.append("missing_receipt_ref")
        elif status == "applied" and not item.get("result_ref"):
            errors.append("missing_result_ref")
        elif status == "setup_pending" and (planned["kind"] != "create_thread" or not item.get("pending_task_id")):
            errors.append("invalid_setup_pending_receipt")
        elif status in {"applied", "failed", "setup_pending"} and item.get("operation_fingerprint") != planned["operation_fingerprint"]:
            errors.append("forged_receipt_fingerprint")
        else:
            found[key] = item
    return found, sorted(set(errors))


def required_capabilities(request: dict[str, Any], runtime: dict[str, Any]) -> list[str]:
    capabilities = runtime.get("operations") if isinstance(runtime.get("operations"), dict) else {}
    required = {"list_projects", "read_thread", "create_thread"}
    if request.get("reuse_policy") == "reuse_allowed":
        required.add("list_threads")
    if request.get("handshake_requested"):
        required.update({"wait_threads", "send_message_to_thread"})
    return [f"{name}_capability_unavailable" for name in sorted(required) if (capabilities.get(name) or {}).get("status") != "supported"]


def role_session_init(identity: dict[str, Any], role: str, peer: str, token: str, title: str) -> dict[str, Any]:
    return {"schema": "RoleSessionInit/v1", "project_identity": identity, "role": role, "title": title, "peer_role": peer, "onboarding_token": token, "initialization_only": True, "work_assigned": False, "required_readback": {"owner_role": role, "thread_id": "self", "initialized": True}}


def owner_receipt_valid(receipt: dict[str, Any] | None, role: str, thread_id: str) -> bool:
    evidence = receipt.get("evidence") if isinstance(receipt, dict) else None
    return bool(receipt and receipt.get("status") == "applied" and receipt.get("result_ref") == thread_id and isinstance(evidence, dict) and evidence.get("owner_role") == role and evidence.get("thread_id") == thread_id and evidence.get("initialized") is True and isinstance(evidence.get("cursor"), str) and evidence.get("cursor"))


def identity_receipt_valid(receipt: dict[str, Any] | None) -> bool:
    evidence = receipt.get("evidence") if isinstance(receipt, dict) else None
    return bool(receipt and receipt.get("status") == "applied" and isinstance(receipt.get("result_ref"), str) and receipt.get("result_ref") and isinstance(evidence, dict) and evidence.get("identity_kind") == "thread_id" and evidence.get("source") == "public_owner_surface")


def handshake_receipt_valid(receipt: dict[str, Any] | None, token: str, reply_to: str) -> bool:
    evidence = receipt.get("evidence") if isinstance(receipt, dict) else None
    return bool(receipt and receipt.get("status") == "applied" and isinstance(evidence, dict) and evidence.get("schema") == "PeerHandshake/v1" and evidence.get("token") == token and evidence.get("reply_to_thread_id") == reply_to and evidence.get("acknowledged") is True and isinstance(evidence.get("cursor"), str) and evidence.get("cursor"))


def lifecycle_summary(role_ops: dict[str, dict[str, Any]], owner_ops: dict[str, dict[str, Any]], handshake_ops: dict[str, dict[str, Any]], receipts: dict[str, dict[str, Any]], handshake_requested: bool) -> dict[str, dict[str, Any]]:
    result = {}
    for role in DURABLE_ROLES:
        accepted = receipts.get(role_ops[role]["idempotency_key"], {}).get("status") == "applied"
        initialized = receipts.get(owner_ops.get(role, {}).get("idempotency_key", ""), {}).get("status") == "applied"
        acknowledged: bool | str = "not_requested"
        if handshake_requested:
            acknowledged = receipts.get(handshake_ops.get(role, {}).get("idempotency_key", ""), {}).get("status") == "applied"
        result[role] = {"accepted": accepted, "initialized": initialized, "acknowledged": acknowledged, "ready": bool(accepted and initialized and (acknowledged is True or acknowledged == "not_requested"))}
    return result


def make_summary(identity: dict[str, Any], request: dict[str, Any], repo: dict[str, Any], held: list[str], lifecycle: dict[str, dict[str, Any]] | None = None, native_receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"project_identity": identity, "capability": "unavailable" if held else "complete", "reuse_policy": request.get("reuse_policy"), "roles": lifecycle or {role: {"accepted": False, "initialized": False, "acknowledged": "not_requested", "ready": False} for role in DURABLE_ROLES}, "held": sorted(set(held)), "role_hub": {"kind": "logical_read_only_projection", "native_thread": False, "required_for_readiness": False}, "historical_references": [], "dirty_state": {"dirty": repo.get("dirty"), "preserved": repo.get("dirty_preserved")}, "work_assigned": False, "private_history_scanned": False, "duplicate_create_allowed": False, "native_onboarding_receipt": native_receipt, "next_human_action": "None; native onboarding is ready." if native_receipt else "Resolve the reported hold or execute only the planned operation prefix."}


def hold(base: dict[str, Any], identity: dict[str, Any], request: dict[str, Any], repo: dict[str, Any], reasons: list[str], operations: list[dict[str, Any]] | None = None, state: str = "partial_hold", lifecycle: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    reasons = sorted(set(reasons))
    return {**base, "state": state, "transition_history": ["preflight", state], "stop_conditions": reasons, "operations": operations or [], "summary": make_summary(identity, request, repo, reasons, lifecycle)}


def _plan(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    identity = request.get("project_identity") if isinstance(request.get("project_identity"), dict) else {}
    repo = payload.get("repository_state") if isinstance(payload.get("repository_state"), dict) else {}
    runtime = payload.get("runtime_capabilities") if isinstance(payload.get("runtime_capabilities"), dict) else {}
    base = {"onboarding_version": VERSION, "read_only": True, "mutation_performed": False, "dispatch_performed": False}
    valid_request = payload.get("onboarding_version") == VERSION and all(identity.get(key) for key in ("project_id", "repository", "integration_branch")) and request.get("onboarding_key") and request.get("reuse_policy") in {"fresh_only", "reuse_allowed"} and isinstance(request.get("apply_authorized"), bool) and isinstance(request.get("handshake_requested"), bool)
    if not valid_request:
        return hold(base, identity, request, repo, ["invalid_onboarding_request"])
    if contains_forbidden(payload):
        return hold(base, identity, request, repo, ["privacy_exposure"])
    if has_unknown_input(payload):
        return hold(base, identity, request, repo, ["unknown_input_field"])
    if repo.get("dirty_preserved") is not True:
        return hold(base, identity, request, repo, ["dirty_state_not_proven_preserved"])
    existing = payload.get("existing_roles", [])
    if request["reuse_policy"] == "fresh_only" and existing:
        return hold(base, identity, request, repo, ["fresh_only_existing_role_input_forbidden"])
    missing = required_capabilities(request, runtime)
    if missing:
        return hold(base, identity, request, repo, missing)

    token = "onboard-token:" + digest({"identity": identity, "onboarding_key": request["onboarding_key"]}).split(":", 1)[1][:24]
    resolve = operation(identity, request["onboarding_key"], "resolve_saved_project", "Project", {"source": "list_projects"}, {"project_identity": identity})
    operations = [resolve]
    role_ops: dict[str, dict[str, Any]] = {}
    stops: list[str] = []
    names = request.get("role_display_names", {})
    for role in DURABLE_ROLES:
        peer = DURABLE_ROLES[1] if role == DURABLE_ROLES[0] else DURABLE_ROLES[0]
        all_matches = [item for item in existing if item.get("project_id") == identity["project_id"] and item.get("role") == role] if request["reuse_policy"] == "reuse_allowed" else []
        matches = [item for item in all_matches if item.get("state") == "active"]
        if any(item.get("state") != "active" for item in all_matches):
            stops.append(f"ambiguous_{role.lower().replace(' ', '_')}_history")
            continue
        if len(matches) > 1:
            stops.append(f"duplicate_{role.lower().replace(' ', '_')}_matches")
            continue
        if len(matches) == 1:
            item = matches[0]
            role_op = operation(identity, request["onboarding_key"], "reuse_thread", role, {"thread_id": item.get("thread_id")}, {"thread_id": item.get("thread_id"), "initialization_only": True}, [resolve["idempotency_key"]])
        else:
            preimage = {"policy": request["reuse_policy"], "historical_tasks_read": request["reuse_policy"] != "fresh_only"}
            role_op = operation(identity, request["onboarding_key"], "create_thread", role, preimage, role_session_init(identity, role, peer, token, names.get(role, role)), [resolve["idempotency_key"]])
        operations.append(role_op)
        role_ops[role] = role_op
    if stops:
        return hold(base, identity, request, repo, stops, operations)
    if not request["apply_authorized"]:
        return {**base, "state": "plan_ready", "transition_history": ["preflight", "plan_ready"], "stop_conditions": [], "operations": operations, "summary": make_summary(identity, request, repo, [])}

    raw_receipts = payload.get("operation_receipts", [])
    raw_by_key = receipt_by_key(raw_receipts)
    thread_ids = {role: raw_by_key[op["idempotency_key"]]["result_ref"] for role, op in role_ops.items() if identity_receipt_valid(raw_by_key.get(op["idempotency_key"]))}
    owner_ops: dict[str, dict[str, Any]] = {}
    if len(thread_ids) == len(DURABLE_ROLES) and len(set(thread_ids.values())) == len(DURABLE_ROLES):
        for role in DURABLE_ROLES:
            owner_op = operation(identity, request["onboarding_key"], "owner_readback", role, {"source": "read_thread"}, {"thread_id": thread_ids[role], "owner_role": role, "initialized": True}, [role_ops[role]["idempotency_key"]])
            operations.append(owner_op)
            owner_ops[role] = owner_op

    handshake_sends: dict[str, dict[str, Any]] = {}
    handshake_reads: dict[str, dict[str, Any]] = {}
    owners_valid = bool(owner_ops) and all(owner_receipt_valid(raw_by_key.get(owner_ops[role]["idempotency_key"]), role, thread_ids[role]) for role in DURABLE_ROLES)
    if request["handshake_requested"] and owners_valid:
        for role in DURABLE_ROLES:
            peer = DURABLE_ROLES[1] if role == DURABLE_ROLES[0] else DURABLE_ROLES[0]
            send_op = operation(identity, request["onboarding_key"], "peer_handshake_send", role, {"owner": "onboarding_executor"}, {"schema": "PeerHandshake/v1", "token": token, "source_thread_id": thread_ids[role], "target_thread_id": thread_ids[peer], "reply_to_thread_id": thread_ids[role], "owner": "onboarding_executor"}, [owner_ops[role]["idempotency_key"], owner_ops[peer]["idempotency_key"]])
            operations.append(send_op)
            handshake_sends[role] = send_op
        for role in DURABLE_ROLES:
            peer = DURABLE_ROLES[1] if role == DURABLE_ROLES[0] else DURABLE_ROLES[0]
            cursor = raw_by_key.get(owner_ops[peer]["idempotency_key"], {}).get("evidence", {}).get("cursor")
            read_op = operation(identity, request["onboarding_key"], "peer_handshake_readback", role, {"cursor": cursor}, {"schema": "PeerHandshake/v1", "token": token, "thread_id": thread_ids[peer], "reply_to_thread_id": thread_ids[role], "cursor_rule": "after_owner_readback"}, [handshake_sends[role]["idempotency_key"]])
            operations.append(read_op)
            handshake_reads[role] = read_op

    receipts, errors = validate_receipts(raw_receipts, operations)
    if errors:
        return hold(base, identity, request, repo, errors, operations)
    lifecycle = lifecycle_summary(role_ops, owner_ops, handshake_reads, receipts, request["handshake_requested"])
    invalid_identities = [role for role, op in role_ops.items() if receipts.get(op["idempotency_key"], {}).get("status") == "applied" and not identity_receipt_valid(receipts.get(op["idempotency_key"]))]
    if invalid_identities:
        return hold(base, identity, request, repo, ["durable_thread_identity_unproven"], operations, lifecycle=lifecycle)
    reused_mismatch = [role for role, op in role_ops.items() if op["kind"] == "reuse_thread" and thread_ids.get(role) != op["desired_state"].get("thread_id")]
    if reused_mismatch:
        return hold(base, identity, request, repo, ["reused_thread_identity_mismatch"], operations, lifecycle=lifecycle)
    if len(thread_ids) != len(DURABLE_ROLES) and any(item.get("status") == "setup_pending" for item in receipts.values()):
        return hold(base, identity, request, repo, ["thread_id_unresolved"], operations, "setup_pending", lifecycle)
    if len(thread_ids) == len(DURABLE_ROLES) and len(set(thread_ids.values())) != len(DURABLE_ROLES):
        return hold(base, identity, request, repo, ["duplicate_thread_identity"], operations, lifecycle=lifecycle)
    if any(item.get("status") == "failed" for item in receipts.values()):
        result = hold(base, identity, request, repo, ["partial_operation_failure"], operations, lifecycle=lifecycle)
        result["rollback_operations"] = [{"kind": "mark_setup_incomplete", "subject": role, "source_idempotency_key": op["idempotency_key"], "automatic": False, "never_delete_or_archive": True} for role, op in role_ops.items() if receipts.get(op["idempotency_key"], {}).get("status") == "applied"]
        return result
    invalid_owner = [role for role in owner_ops if receipts.get(owner_ops[role]["idempotency_key"], {}).get("status") == "applied" and not owner_receipt_valid(receipts.get(owner_ops[role]["idempotency_key"]), role, thread_ids[role])]
    if invalid_owner:
        return hold(base, identity, request, repo, ["invalid_owner_readback"], operations, lifecycle=lifecycle)
    invalid_handshake = [role for role in handshake_reads if receipts.get(handshake_reads[role]["idempotency_key"], {}).get("status") == "applied" and not handshake_receipt_valid(receipts.get(handshake_reads[role]["idempotency_key"]), token, thread_ids[role])]
    if invalid_handshake:
        return hold(base, identity, request, repo, ["invalid_peer_handshake_readback"], operations, lifecycle=lifecycle)

    if all(item["ready"] for item in lifecycle.values()):
        native_receipt = {"schema": "NativeOnboardingReceipt/v1", "onboarding_token": token, "reuse_policy": request["reuse_policy"], "roles": {role: {"thread_id": thread_ids[role], **lifecycle[role]} for role in DURABLE_ROLES}, "handshake": {"requested": request["handshake_requested"], "owner": "onboarding_executor", "token": token, "status": "acknowledged" if request["handshake_requested"] else "not_requested"}, "work_assigned": False}
        return {**base, "state": "ready", "transition_history": ["preflight", "plan_ready", "applying", "ready"], "stop_conditions": [], "operations": operations, "summary": make_summary(identity, request, repo, [], lifecycle, native_receipt)}
    return {**base, "state": "applying", "transition_history": ["preflight", "plan_ready", "applying"], "stop_conditions": [], "operations": operations, "summary": make_summary(identity, request, repo, [], lifecycle)}


def validate_plan_result(result: dict[str, Any]) -> dict[str, Any]:
    required = {"onboarding_version", "read_only", "mutation_performed", "dispatch_performed", "state", "transition_history", "stop_conditions", "operations", "summary"}
    allowed = required | {"rollback_operations"}
    if isinstance(result, dict) and required.issubset(result) and not (set(result) - allowed) and isinstance(result.get("operations"), list) and isinstance(result.get("summary"), dict) and result.get("onboarding_version") == VERSION:
        return result
    base = {"onboarding_version": VERSION, "read_only": True, "mutation_performed": False, "dispatch_performed": False}
    return hold(base, {}, {}, {}, ["invalid_plan_result"])


def plan(payload: dict[str, Any]) -> dict[str, Any]:
    return validate_plan_result(_plan(payload if isinstance(payload, dict) else {}))


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan native bounded-collaboration onboarding without side effects.")
    parser.add_argument("--input", help="JSON input; stdin when omitted")
    args = parser.parse_args()
    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("onboarding input must be a JSON object")
    print(json.dumps(plan(payload), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
