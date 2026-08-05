#!/usr/bin/env python3
"""Build and validate a metadata-only bounded-collaboration onboarding plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any


VERSION = "bounded-collaboration-onboarding-v1"
DURABLE_ROLES = ("Coordinator", "Architect")
TRANSIENT_ROLES = ("Implementer", "Reviewer", "Tester", "Harvester")
CAPABILITIES = ("discover", "create", "rename", "link", "navigate")
PROJECTIONS = ("role_hub", "current_thread", "scheduler", "transient_template")
FORBIDDEN_KEYS = {"transcript", "raw_transcript", "messages", "prompt", "content", "thread_id", "native_thread_id", "notes", "tool_output", "raw_content", "raw_tool_output"}
ALLOWED_ROOT_KEYS = {"onboarding_version", "request", "runtime_capabilities", "role_hub", "current_thread", "existing_roles", "repository_state", "operation_receipts", "rollback_receipts"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def key_for(project_id: str, kind: str, subject: str, onboarding_key: str) -> str:
    return "onboard:" + digest({"project_id": project_id, "kind": kind, "subject": subject, "onboarding_key": onboarding_key, "version": VERSION}).split(":", 1)[1]


def contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in FORBIDDEN_KEYS or contains_forbidden(item) for key, item in value.items())
    return isinstance(value, list) and any(contains_forbidden(item) for item in value)


def has_unknown_input(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) - ALLOWED_ROOT_KEYS:
        return True
    expected = {
        "request": {"project_identity", "onboarding_key", "apply_authorized", "role_display_names"},
        "project_identity": {"project_id", "repository", "integration_branch"},
        "repository_state": {"dirty", "dirty_preserved"},
        "role_hub": {"status", "role_hub_ref"},
        "current_thread": {"eligible", "current_thread_ref", "name"},
        "role": {"project_id", "role", "role_ref", "durable_anchor", "state", "legacy", "display_name", "linked_to_role_hub"},
        "capability": {"status"},
    }
    request = value.get("request")
    runtime = value.get("runtime_capabilities")
    if not isinstance(request, dict) or set(request) - expected["request"] or not isinstance(request.get("project_identity"), dict) or set(request["project_identity"]) - expected["project_identity"]:
        return True
    if "role_display_names" in request and (not isinstance(request["role_display_names"], dict) or set(request["role_display_names"]) - set(DURABLE_ROLES)):
        return True
    if not isinstance(value.get("repository_state"), dict) or set(value["repository_state"]) - expected["repository_state"]:
        return True
    if not isinstance(value.get("role_hub"), dict) or set(value["role_hub"]) - expected["role_hub"] or not isinstance(value.get("current_thread"), dict) or set(value["current_thread"]) - expected["current_thread"]:
        return True
    if not isinstance(runtime, dict) or set(runtime) - {"role_binding", "projections", "operations"}:
        return True
    for section, required in (("projections", PROJECTIONS), ("operations", CAPABILITIES)):
        items = runtime.get(section)
        allowed_items = {name: expected["capability"] for name in required}
        if section == "projections":
            allowed_items["scheduler"] = {"status", "binding_ref", "binding_status"}
            allowed_items["transient_template"] = {"status", "template_refs"}
        if not isinstance(items, dict) or set(items) != set(required) or any(not isinstance(items.get(name), dict) or set(items[name]) - allowed_items[name] for name in required):
            return True
    if not isinstance(runtime.get("role_binding"), dict) or set(runtime["role_binding"]) - expected["capability"]:
        return True
    return not isinstance(value.get("existing_roles"), list) or any(not isinstance(item, dict) or set(item) - expected["role"] for item in value["existing_roles"])


def operation(identity: dict[str, Any], onboarding_key: str, kind: str, subject: str, preimage: dict[str, Any], desired_state: dict[str, Any], depends_on: list[str] | None = None) -> dict[str, Any]:
    item = {"kind": kind, "subject": subject, "idempotency_key": key_for(identity["project_id"], kind, subject, onboarding_key), "preimage": preimage, "desired_state": desired_state}
    if depends_on:
        item["depends_on"] = depends_on
    item["operation_fingerprint"] = digest(item)
    return item


def hold(base: dict[str, Any], request: dict[str, Any], repo: dict[str, Any], reasons: list[str], historical: list[dict[str, Any]] | None = None, operations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    capability = "privacy_held" if "privacy_exposure" in reasons else "unavailable" if any("capability" in item for item in reasons) else "partial"
    return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": sorted(set(reasons)), "operations": operations or [], "summary": {"project_identity": request.get("project_identity", {}), "capability": capability, "reused": [], "created": [], "unchanged": list(TRANSIENT_ROLES), "held": sorted(set(reasons)), "active_navigation": {"authority": "adapter", "value": "unavailable"}, "historical_references": historical or [], "dirty_state": {"dirty": repo.get("dirty"), "preserved": repo.get("dirty_preserved")}, "next_human_action": "Resolve the hold and run a new read-only preflight; do not reuse a partial plan."}}


def required_capabilities(payload: dict[str, Any]) -> list[str]:
    runtime = payload.get("runtime_capabilities") if isinstance(payload.get("runtime_capabilities"), dict) else {}
    missing = []
    if ((runtime.get("role_binding") or {}).get("status")) != "supported":
        missing.append("role_binding_capability_unavailable")
    projections = runtime.get("projections") if isinstance(runtime.get("projections"), dict) else {}
    for name in PROJECTIONS:
        if ((projections.get(name) or {}).get("status")) != "supported":
            missing.append(f"{name}_projection_unavailable")
    scheduler = projections.get("scheduler") if isinstance(projections.get("scheduler"), dict) else {}
    templates = projections.get("transient_template") if isinstance(projections.get("transient_template"), dict) else {}
    if not scheduler.get("binding_ref") or scheduler.get("binding_status") != "bound":
        missing.append("scheduler_binding_unavailable")
    refs = templates.get("template_refs")
    if not isinstance(refs, dict) or set(refs) != set(TRANSIENT_ROLES) or not all(isinstance(refs.get(role), str) and refs[role] for role in TRANSIENT_ROLES):
        missing.append("transient_templates_unavailable")
    operations = runtime.get("operations") if isinstance(runtime.get("operations"), dict) else {}
    for name in CAPABILITIES:
        if ((operations.get(name) or {}).get("status")) != "supported":
            missing.append(f"{name}_capability_unavailable")
    return missing


def validate_receipts(receipts: Any, operations: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if receipts is None:
        return {}, []
    if not isinstance(receipts, list):
        return {}, ["invalid_receipts"]
    expected = {item["idempotency_key"]: item["operation_fingerprint"] for item in operations}
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    terminal_seen = False
    for index, item in enumerate(receipts):
        key = item.get("idempotency_key") if isinstance(item, dict) else None
        status = item.get("status") if isinstance(item, dict) else None
        if not isinstance(item, dict) or index >= len(operations) or key != operations[index]["idempotency_key"]:
            errors.append("invalid_receipt_sequence")
        elif key not in expected:
            errors.append("unknown_receipt")
        elif key in found:
            errors.append("duplicate_receipt")
        elif status not in {"applied", "failed", "not_attempted"}:
            errors.append("invalid_receipt_status")
        elif terminal_seen and status == "applied":
            errors.append("invalid_receipt_sequence")
        elif status in {"applied", "failed"} and (not isinstance(item.get("receipt_ref"), str) or not item["receipt_ref"]):
            errors.append("missing_receipt_ref")
        elif status == "applied" and (not isinstance(item.get("result_ref"), str) or not item["result_ref"]):
            errors.append("missing_result_ref")
        elif status in {"applied", "failed"} and item.get("operation_fingerprint") != expected[key]:
            errors.append("forged_receipt_fingerprint")
        else:
            found[key] = item
            terminal_seen = terminal_seen or status in {"failed", "not_attempted"}
    return found, sorted(set(errors))


def rollback_plan(operations: list[dict[str, Any]], receipts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for item in reversed(operations):
        if receipts.get(item["idempotency_key"], {}).get("status") != "applied":
            continue
        if item["kind"] in {"create_role_hub", "create_durable_role"}:
            kind = "mark_setup_incomplete"
        elif item["kind"] in {"rename_role", "link_role"}:
            kind = "restore_preimage"
        else:
            continue
        reverse = {"kind": kind, "subject": item["subject"], "source_idempotency_key": item["idempotency_key"], "source_operation_fingerprint": item["operation_fingerprint"], "preimage": item["preimage"], "automatic": False, "never_delete_or_archive": True}
        reverse["rollback_fingerprint"] = digest(reverse)
        result.append(reverse)
    return result


def _plan(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    identity = request.get("project_identity") if isinstance(request.get("project_identity"), dict) else {}
    repo = payload.get("repository_state") if isinstance(payload.get("repository_state"), dict) else {}
    current = payload.get("current_thread") if isinstance(payload.get("current_thread"), dict) else {}
    base = {"onboarding_version": VERSION, "read_only": True, "mutation_performed": False, "dispatch_performed": False}
    if payload.get("onboarding_version") != VERSION or not all(identity.get(key) for key in ("project_id", "repository", "integration_branch")) or not request.get("onboarding_key"):
        return hold(base, request, repo, ["invalid_onboarding_request"])
    if contains_forbidden(payload):
        return hold(base, request, repo, ["privacy_exposure"])
    if has_unknown_input(payload):
        return hold(base, request, repo, ["unknown_input_field"])
    if repo.get("dirty_preserved") is not True:
        return hold(base, request, repo, ["dirty_state_not_proven_preserved"])
    missing = required_capabilities(payload)
    if missing:
        return hold(base, request, repo, missing)
    hub = payload.get("role_hub") if isinstance(payload.get("role_hub"), dict) else {}
    if hub.get("status") not in {"missing", "active"}:
        return hold(base, request, repo, ["role_hub_ambiguous_or_held"])
    if hub.get("status") == "active" and not hub.get("role_hub_ref"):
        return hold(base, request, repo, ["active_role_hub_ref_missing"])
    existing = payload.get("existing_roles")
    if not isinstance(existing, list):
        return hold(base, request, repo, ["invalid_existing_roles"])

    operations = [operation(identity, request["onboarding_key"], "discover_role_hub", "RoleHub", {"status": hub.get("status")}, {"project_id": identity["project_id"]})]
    if hub["status"] == "missing":
        if current.get("eligible") is True and current.get("current_thread_ref") and current.get("name"):
            operations.append(operation(identity, request["onboarding_key"], "rename_current_to_role_hub", "RoleHub", {"current_thread_ref": current["current_thread_ref"], "name": current["name"]}, {"project_id": identity["project_id"], "role": "RoleHub", "name": "RoleHub"}, [operations[0]["idempotency_key"]]))
        else:
            operations.append(operation(identity, request["onboarding_key"], "create_role_hub", "RoleHub", {"status": "missing"}, {"project_id": identity["project_id"], "role": "RoleHub", "name": "RoleHub"}, [operations[0]["idempotency_key"]]))
    else:
        operations.append(operation(identity, request["onboarding_key"], "reuse_role_hub", "RoleHub", {"role_hub_ref": hub["role_hub_ref"]}, {"project_id": identity["project_id"], "role": "RoleHub"}, [operations[0]["idempotency_key"]]))
    historical: list[dict[str, Any]] = []
    stops: list[str] = []
    reused, created = [], []
    names = request.get("role_display_names") if isinstance(request.get("role_display_names"), dict) else {}
    for role in DURABLE_ROLES:
        matches = [item for item in existing if isinstance(item, dict) and item.get("project_id") == identity["project_id"] and item.get("role") == role]
        active = [item for item in matches if item.get("state") == "active" and item.get("legacy") is False]
        nonactive = [item for item in matches if item not in active]
        for item in nonactive:
            historical.append({"role": role, "durable_anchor": item.get("durable_anchor"), "reason": "held_legacy_or_historical_match"})
        if len(active) > 1:
            stops.append(f"duplicate_{role.lower()}_matches")
        if nonactive:
            stops.append(f"held_legacy_or_ambiguous_{role.lower()}_match")
        if len(active) == 1 and not nonactive:
            item = active[0]
            operations.append(operation(identity, request["onboarding_key"], "reuse_durable_role", role, {"match_count": 1, "durable_anchor": item.get("durable_anchor")}, {"project_id": identity["project_id"], "role": role, "role_hub_link": "RoleHub"}, [operations[1]["idempotency_key"]]))
            reused.append({"role": role, "durable_anchor": item.get("durable_anchor")})
            desired = names.get(role)
            if desired and item.get("display_name") != desired:
                operations.append(operation(identity, request["onboarding_key"], "rename_role", role, {"display_name": item.get("display_name")}, {"name": desired, "role_hub_link": "RoleHub"}, [operations[-1]["idempotency_key"]]))
            if item.get("linked_to_role_hub") is not True:
                operations.append(operation(identity, request["onboarding_key"], "link_role", role, {"linked_to_role_hub": item.get("linked_to_role_hub")}, {"role_hub_link": "RoleHub"}, [operations[-1]["idempotency_key"]]))
        elif not matches:
            operations.append(operation(identity, request["onboarding_key"], "create_durable_role", role, {"match_count": 0}, {"project_id": identity["project_id"], "role": role, "role_hub_link": "RoleHub"}, [operations[1]["idempotency_key"]]))
            created.append({"role": role, "status": "planned"})
    operations.append(operation(identity, request["onboarding_key"], "navigate_role_hub", "RoleHub", {"current_navigation": "adapter_owned"}, {"active_navigation": "RoleHub"}, [operations[1]["idempotency_key"]]))
    if stops:
        return hold(base, request, repo, stops, historical, operations)

    receipts, receipt_errors = validate_receipts(payload.get("operation_receipts"), operations)
    if receipt_errors:
        return hold(base, request, repo, receipt_errors, historical, operations)
    if not request.get("apply_authorized"):
        state, history = "plan_ready", ["preflight", "plan_ready"]
    elif any(item.get("status") == "failed" for item in receipts.values()):
        rollback = rollback_plan(operations, receipts)
        rollback_errors: list[str] = []
        # Rollback receipts are independently checked against only planned reverse operations.
        rollback_keys = {item["source_idempotency_key"] for item in rollback}
        raw_rollback = payload.get("rollback_receipts", [])
        planned_rollback = {item["source_idempotency_key"]: item for item in rollback}
        if raw_rollback and (not isinstance(raw_rollback, list) or len(raw_rollback) != len(rollback_keys) or {item.get("source_idempotency_key") for item in raw_rollback if isinstance(item, dict)} != rollback_keys or any(not isinstance(item, dict) or item.get("source_idempotency_key") not in rollback_keys or item.get("status") not in {"applied", "failed"} or not item.get("receipt_ref") or item.get("source_operation_fingerprint") != planned_rollback[item["source_idempotency_key"]]["source_operation_fingerprint"] or item.get("rollback_fingerprint") != planned_rollback[item["source_idempotency_key"]]["rollback_fingerprint"] for item in raw_rollback)):
            rollback_errors.append("invalid_rollback_receipt")
        if rollback_errors:
            rollback_state = "rollback_incomplete"
        elif rollback and raw_rollback and any(item.get("status") == "failed" for item in raw_rollback):
            rollback_state = "rollback_incomplete"
        elif rollback and raw_rollback and all(item.get("status") == "applied" for item in raw_rollback):
            rollback_state = "rolled_back"
        else:
            rollback_state = "rollback_planned"
        history = ["preflight", "plan_ready", "applying", "partial_hold", "rollback_planned"] + ([] if rollback_state == "rollback_planned" else [rollback_state])
        return {**base, "state": rollback_state, "transition_history": history, "stop_conditions": ["partial_operation_failure"], "operations": operations, "rollback_operations": rollback, "summary": {**hold(base, request, repo, ["partial_operation_failure"], historical)["summary"], "created": created}}
    elif len(receipts) == len(operations) and all(item.get("status") == "applied" for item in receipts.values()):
        state, history = "ready", ["preflight", "plan_ready", "applying", "ready"]
    else:
        state, history = "applying", ["preflight", "plan_ready", "applying"]
    final_receipts = {item["subject"]: receipts.get(item["idempotency_key"], {}) for item in operations if item["kind"] in {"create_role_hub", "rename_current_to_role_hub", "reuse_role_hub", "create_durable_role", "reuse_durable_role"}}
    projections = ((payload.get("runtime_capabilities") or {}).get("projections") or {})
    if state == "ready":
        navigation = {"role_hub_ref": final_receipts["RoleHub"]["result_ref"], "coordinator_ref": final_receipts["Coordinator"]["result_ref"], "architect_ref": final_receipts["Architect"]["result_ref"]}
        next_action = "Bounded collaboration is ready; create transient roles only for an approved Work."
        created = [{"role": item["subject"], "status": "created", "role_ref": receipts[item["idempotency_key"]]["result_ref"]} for item in operations if item["kind"] == "create_durable_role"]
    else:
        navigation = {"authority": "adapter", "value": "adapter_create_receipt_required"}
        next_action = "Approve adapter execution of the planned operation keys." if state == "plan_ready" else "Read back adapter receipts and preserve any partial setup."
    summary = {"project_identity": identity, "capability": "complete", "reused": reused, "created": created, "unchanged": list(TRANSIENT_ROLES), "held": [], "active_navigation": navigation, "historical_references": historical, "dirty_state": {"dirty": repo.get("dirty"), "preserved": True}, "next_human_action": next_action, "projections": {"scheduler": {"binding_ref": projections["scheduler"].get("binding_ref"), "binding_status": projections["scheduler"].get("binding_status")}, "transient_templates": projections["transient_template"].get("template_refs")}}
    return {**base, "state": state, "transition_history": history, "stop_conditions": [], "operations": operations, "summary": summary}


def validate_plan_result(result: dict[str, Any]) -> dict[str, Any]:
    required = {"onboarding_version", "read_only", "mutation_performed", "dispatch_performed", "state", "transition_history", "stop_conditions", "operations", "summary"}
    allowed = required | {"rollback_operations"}
    summary_required = {"project_identity", "capability", "reused", "created", "unchanged", "held", "active_navigation", "historical_references", "dirty_state", "next_human_action"}
    summary_allowed = summary_required | {"projections"}
    operation_required = {"kind", "subject", "idempotency_key", "preimage", "desired_state", "operation_fingerprint"}
    operation_allowed = operation_required | {"depends_on"}
    rollback_required = {"kind", "subject", "source_idempotency_key", "source_operation_fingerprint", "preimage", "automatic", "never_delete_or_archive", "rollback_fingerprint"}
    valid = isinstance(result, dict) and required.issubset(result) and not (set(result) - allowed) and isinstance(result.get("operations"), list) and isinstance(result.get("summary"), dict) and summary_required.issubset(result["summary"]) and not (set(result["summary"]) - summary_allowed) and all(isinstance(item, dict) and operation_required.issubset(item) and not (set(item) - operation_allowed) for item in result["operations"]) and ("rollback_operations" not in result or isinstance(result["rollback_operations"], list) and all(isinstance(item, dict) and rollback_required == set(item) for item in result["rollback_operations"]))
    if valid:
        return result
    return {"onboarding_version": VERSION, "read_only": True, "mutation_performed": False, "dispatch_performed": False, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": ["invalid_plan_result"], "operations": [], "summary": {"project_identity": {}, "capability": "partial", "reused": [], "created": [], "unchanged": list(TRANSIENT_ROLES), "held": ["invalid_plan_result"], "active_navigation": {"authority": "adapter", "value": "unavailable"}, "historical_references": [], "dirty_state": {"dirty": None, "preserved": False}, "next_human_action": "Repair the Core planning contract before apply."}}


def plan(payload: dict[str, Any]) -> dict[str, Any]:
    return validate_plan_result(_plan(payload if isinstance(payload, dict) else {}))


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan bounded collaboration onboarding without side effects.")
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
