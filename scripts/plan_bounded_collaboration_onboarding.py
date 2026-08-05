#!/usr/bin/env python3
"""Plan metadata-only bounded-collaboration project onboarding without I/O."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any


VERSION = "bounded-collaboration-onboarding-v1"
DURABLE_ROLES = ("Coordinator", "Architect")
TRANSIENT_ROLES = ("Implementer", "Reviewer", "Tester", "Harvester")
FORBIDDEN_KEYS = {"transcript", "raw_transcript", "messages", "prompt", "content", "thread_id", "native_thread_id"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def key_for(project_id: str, role: str, onboarding_key: str) -> str:
    material = canonical({"project_id": project_id, "role": role, "onboarding_key": onboarding_key, "version": VERSION})
    return "onboard:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in FORBIDDEN_KEYS or contains_forbidden(item) for key, item in value.items())
    return isinstance(value, list) and any(contains_forbidden(item) for item in value)


def fail_summary(request: dict[str, Any], repository_state: dict[str, Any], reason: str, historical: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "project_identity": request.get("project_identity", {}),
        "capability": "privacy_held" if reason == "privacy_exposure" else "unavailable" if reason == "role_binding_unavailable" else "partial",
        "reused": [], "created": [], "unchanged": list(TRANSIENT_ROLES), "held": [reason],
        "active_navigation": {"authority": "adapter", "value": "unavailable"},
        "historical_references": historical or [],
        "dirty_state": {"dirty": repository_state.get("dirty"), "preserved": repository_state.get("dirty_preserved")},
        "next_human_action": "Resolve the hold and run a new read-only preflight; do not reuse a partial plan.",
    }


def plan(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    identity = request.get("project_identity") if isinstance(request.get("project_identity"), dict) else {}
    repository_state = payload.get("repository_state") if isinstance(payload.get("repository_state"), dict) else {}
    base = {"onboarding_version": VERSION, "read_only": True, "mutation_performed": False, "dispatch_performed": False}
    if payload.get("onboarding_version") != VERSION or not all(identity.get(item) for item in ("project_id", "repository", "integration_branch")) or not request.get("onboarding_key"):
        return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": ["invalid_onboarding_request"], "summary": fail_summary(request, repository_state, "invalid_onboarding_request"), "operations": []}
    if contains_forbidden(payload):
        return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": ["privacy_exposure"], "summary": fail_summary(request, repository_state, "privacy_exposure"), "operations": []}
    if repository_state.get("dirty_preserved") is not True:
        return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": ["dirty_state_not_proven_preserved"], "summary": fail_summary(request, repository_state, "dirty_state_not_proven_preserved"), "operations": []}
    capability = ((payload.get("runtime_capabilities") or {}).get("role_binding") or {}).get("status")
    if capability != "supported":
        return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": ["role_binding_unavailable"], "summary": fail_summary(request, repository_state, "role_binding_unavailable"), "operations": []}

    existing = payload.get("existing_roles")
    if not isinstance(existing, list):
        return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": ["invalid_existing_roles"], "summary": fail_summary(request, repository_state, "invalid_existing_roles"), "operations": []}
    operations, reused, created, historical, stops = [], [], [], [], []
    for role in DURABLE_ROLES:
        matching = [item for item in existing if isinstance(item, dict) and item.get("project_id") == identity["project_id"] and item.get("role") == role]
        legacy = [item for item in matching if item.get("legacy") is True or item.get("state") == "historical_reference"]
        active = [item for item in matching if item.get("legacy") is not True and item.get("state") == "active"]
        historical.extend({"role": item.get("role"), "durable_anchor": item.get("durable_anchor"), "reason": "legacy_or_historical_reference"} for item in legacy)
        if legacy:
            stops.append("legacy_adoption_requires_explicit_human_review")
        if len(active) > 1:
            stops.append(f"duplicate_{role.lower()}_matches")
        op_key = key_for(identity["project_id"], role, request["onboarding_key"])
        if len(active) == 1:
            item = active[0]
            operations.append({"kind": "reuse_durable_role", "role": role, "idempotency_key": op_key, "preimage": {"match_count": 1, "durable_anchor": item.get("durable_anchor")}, "receipt": None})
            reused.append({"role": role, "durable_anchor": item.get("durable_anchor")})
        elif not matching:
            operations.append({"kind": "create_durable_role", "role": role, "idempotency_key": op_key, "preimage": {"match_count": 0}, "receipt": None})
            created.append({"role": role, "status": "planned"})
    if stops:
        return {**base, "state": "partial_hold", "transition_history": ["preflight", "partial_hold"], "stop_conditions": sorted(set(stops)), "summary": fail_summary(request, repository_state, sorted(set(stops))[0], historical), "operations": operations}

    receipts = {item.get("idempotency_key"): item for item in payload.get("operation_receipts", []) if isinstance(item, dict)}
    if not request.get("apply_authorized"):
        state = "plan_ready"
    elif any(receipts.get(item["idempotency_key"], {}).get("status") == "failed" for item in operations):
        failed = [item for item in operations if receipts.get(item["idempotency_key"], {}).get("status") == "failed"]
        rollback = [{"kind": "rollback_created_role", "role": item["role"], "idempotency_key": item["idempotency_key"], "automatic": False} for item in failed if item["kind"] == "create_durable_role"]
        rollback_receipts = {item.get("idempotency_key"): item for item in payload.get("rollback_receipts", []) if isinstance(item, dict)}
        if rollback and all(rollback_receipts.get(item["idempotency_key"], {}).get("status") == "applied" for item in rollback):
            rollback_state = "rolled_back"
        elif any(rollback_receipts.get(item["idempotency_key"], {}).get("status") == "failed" for item in rollback):
            rollback_state = "rollback_incomplete"
        else:
            rollback_state = "rollback_planned"
        history = ["preflight", "plan_ready", "applying", "partial_hold", "rollback_planned"]
        if rollback_state != "rollback_planned":
            history.append(rollback_state)
        return {**base, "state": rollback_state, "transition_history": history, "stop_conditions": ["partial_operation_failure"], "operations": operations, "rollback_operations": rollback, "summary": {**fail_summary(request, repository_state, "partial_operation_failure", historical), "created": created}}
    elif all(receipts.get(item["idempotency_key"], {}).get("status") == "applied" for item in operations):
        state = "ready"
    else:
        state = "applying"
    navigation = next((item["durable_anchor"] for item in reused if item["role"] == "Coordinator"), "adapter_create_receipt_required")
    summary = {"project_identity": identity, "capability": "complete", "reused": reused, "created": created, "unchanged": list(TRANSIENT_ROLES), "held": [], "active_navigation": {"authority": "adapter", "value": navigation}, "historical_references": historical, "dirty_state": {"dirty": repository_state.get("dirty"), "preserved": True}, "next_human_action": "Approve adapter execution of the planned operation keys." if state == "plan_ready" else "Read back adapter receipts and preserve any partial setup."}
    history = ["preflight", "plan_ready"]
    if state in {"applying", "ready"}:
        history.append("applying")
    if state == "ready":
        history.append("ready")
    return {**base, "state": state, "transition_history": history, "stop_conditions": [], "operations": operations, "summary": summary}


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
