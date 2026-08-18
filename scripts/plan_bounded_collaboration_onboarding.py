#!/usr/bin/env python3
"""Route legacy bounded-collaboration requests to owner-composed onboarding."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


LEGACY_VERSION = "bounded-collaboration-onboarding-v1"
VERSION = "bounded-collaboration-onboarding-v2"
DURABLE_ROLES = ("Coordinator", "Architect")
TRANSIENT_ROLES = ("Implementer", "Reviewer", "Tester", "Harvester")
CAPABILITIES = ("discover", "create", "rename", "link", "navigate")
PROJECTIONS = ("role_hub", "current_thread", "scheduler", "transient_template")
FORBIDDEN_KEYS = {
    "content", "credential", "messages", "native_thread_id", "notes", "path",
    "payload", "prompt", "raw_content", "raw_tool_output", "raw_transcript",
    "thread_id", "token", "tool_output", "transcript",
}
ROUTE = {
    "entrypoint": "scripts/bounded_collaboration_runtime_bridge.py",
    "mode": "read_only_preflight",
    "required_locators": ["projects_root", "project_root", "onboarding_key"],
    "fresh_owner_readback_required": True,
}
ROLE_HUB_PROJECTION = {
    "classification": "optional_read_only_projection",
    "affects_native_readiness": False,
}


def contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in FORBIDDEN_KEYS or contains_forbidden(item)
            for key, item in value.items()
        )
    return isinstance(value, list) and any(contains_forbidden(item) for item in value)


def _keys(value: Any, *, required: set[str], optional: set[str] | None = None) -> bool:
    optional = optional or set()
    return isinstance(value, dict) and required <= set(value) <= required | optional


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _capability(value: Any) -> bool:
    return _keys(value, required={"status"}) and value["status"] in {
        "supported", "unavailable", "unknown",
    }


def _valid_request(value: Any) -> bool:
    if not _keys(
        value,
        required={"project_identity", "onboarding_key", "apply_authorized"},
        optional={"role_display_names"},
    ):
        return False
    identity = value["project_identity"]
    if not _keys(identity, required={"project_id", "repository", "integration_branch"}):
        return False
    if not all(_string(identity[name]) for name in identity):
        return False
    if re.fullmatch(r"[^/]+/[^/]+", identity["repository"]) is None:
        return False
    if not _string(value["onboarding_key"]) or not isinstance(value["apply_authorized"], bool):
        return False
    names = value.get("role_display_names")
    return names is None or (
        isinstance(names, dict)
        and set(names) <= set(DURABLE_ROLES)
        and all(_string(item) for item in names.values())
    )


def _valid_runtime(value: Any) -> bool:
    if not _keys(value, required={"role_binding", "projections", "operations"}):
        return False
    if not _capability(value["role_binding"]):
        return False
    projections = value["projections"]
    operations = value["operations"]
    if not isinstance(projections, dict) or set(projections) != set(PROJECTIONS):
        return False
    if not isinstance(operations, dict) or set(operations) != set(CAPABILITIES):
        return False
    if not all(_capability(operations[name]) for name in CAPABILITIES):
        return False
    if not _capability(projections["role_hub"]) or not _capability(projections["current_thread"]):
        return False
    scheduler = projections["scheduler"]
    if not _keys(scheduler, required={"status", "binding_ref", "binding_status"}):
        return False
    if scheduler["status"] not in {"supported", "unavailable", "unknown"}:
        return False
    if not _string(scheduler["binding_ref"]) or scheduler["binding_status"] not in {"bound", "unavailable"}:
        return False
    transient = projections["transient_template"]
    if not _keys(transient, required={"status", "template_refs"}):
        return False
    refs = transient["template_refs"]
    return (
        transient["status"] in {"supported", "unavailable", "unknown"}
        and isinstance(refs, dict)
        and set(refs) == set(TRANSIENT_ROLES)
        and all(_string(refs[role]) for role in TRANSIENT_ROLES)
    )


def _valid_role_hub(value: Any) -> bool:
    return (
        _keys(value, required={"status"}, optional={"role_hub_ref"})
        and value["status"] in {"missing", "active", "held", "ambiguous"}
        and ("role_hub_ref" not in value or _string(value["role_hub_ref"]))
    )


def _valid_current_thread(value: Any) -> bool:
    return (
        _keys(value, required={"eligible", "current_thread_ref", "name"})
        and isinstance(value["eligible"], bool)
        and _string(value["current_thread_ref"])
        and _string(value["name"])
    )


def _valid_existing_role(value: Any) -> bool:
    if not _keys(
        value,
        required={"project_id", "role", "role_ref", "durable_anchor", "state", "legacy"},
        optional={"display_name", "linked_to_role_hub"},
    ):
        return False
    if not all(_string(value[name]) for name in ("project_id", "role_ref", "durable_anchor")):
        return False
    if value["role"] not in set(DURABLE_ROLES) | set(TRANSIENT_ROLES):
        return False
    if value["state"] not in {"active", "held", "historical_reference"}:
        return False
    if not isinstance(value["legacy"], bool):
        return False
    if "display_name" in value and not _string(value["display_name"]):
        return False
    return "linked_to_role_hub" not in value or isinstance(value["linked_to_role_hub"], bool)


def _valid_operation_receipt(value: Any) -> bool:
    if not _keys(
        value,
        required={"idempotency_key", "status"},
        optional={"receipt_ref", "operation_fingerprint", "result_ref"},
    ):
        return False
    if not _string(value["idempotency_key"]) or value["status"] not in {
        "applied", "failed", "not_attempted",
    }:
        return False
    if any(not _string(value[key]) for key in set(value) - {"status"}):
        return False
    if value["status"] in {"applied", "failed"} and not {
        "receipt_ref", "operation_fingerprint",
    } <= set(value):
        return False
    return value["status"] != "applied" or "result_ref" in value


def _valid_rollback_receipt(value: Any) -> bool:
    required = {
        "source_idempotency_key", "status", "receipt_ref",
        "source_operation_fingerprint", "rollback_fingerprint",
    }
    return (
        _keys(value, required=required)
        and value["status"] in {"applied", "failed"}
        and all(_string(value[key]) for key in required - {"status"})
    )


def valid_legacy_request(value: Any) -> bool:
    required = {
        "onboarding_version", "request", "runtime_capabilities", "role_hub",
        "current_thread", "existing_roles", "repository_state",
    }
    if not _keys(value, required=required, optional={"operation_receipts", "rollback_receipts"}):
        return False
    repo = value["repository_state"]
    roles = value["existing_roles"]
    operation_receipts = value.get("operation_receipts", [])
    rollback_receipts = value.get("rollback_receipts", [])
    return (
        value["onboarding_version"] == LEGACY_VERSION
        and _valid_request(value["request"])
        and _valid_runtime(value["runtime_capabilities"])
        and _valid_role_hub(value["role_hub"])
        and _valid_current_thread(value["current_thread"])
        and isinstance(roles, list)
        and all(_valid_existing_role(item) for item in roles)
        and _keys(repo, required={"dirty", "dirty_preserved"})
        and isinstance(repo["dirty"], bool)
        and isinstance(repo["dirty_preserved"], bool)
        and isinstance(operation_receipts, list)
        and all(_valid_operation_receipt(item) for item in operation_receipts)
        and isinstance(rollback_receipts, list)
        and all(_valid_rollback_receipt(item) for item in rollback_receipts)
    )


def _result(state: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "onboarding_version": VERSION,
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
        "state": state,
        "stop_conditions": reasons,
        "operations": [],
        "rollback_operations": [],
        "next_route": {
            **ROUTE,
            "required_locators": list(ROUTE["required_locators"]),
        },
        "role_hub": dict(ROLE_HUB_PROJECTION),
        "safe_next_action": (
            "Run the public locator-only owner-composed preflight with fresh owner locators."
            if state == "owner_composed_route_required"
            else "Repair the legacy compatibility request before using the owner-composed preflight."
        ),
    }


def plan(payload: Any) -> dict[str, Any]:
    if contains_forbidden(payload):
        return _result("partial_hold", ["privacy_sensitive_input"])
    if not valid_legacy_request(payload):
        return _result("partial_hold", ["invalid_legacy_request"])
    return _result("owner_composed_route_required", [])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Route a legacy onboarding request to owner-composed preflight without side effects."
    )
    parser.add_argument("--input", help="Legacy JSON input; stdin when omitted")
    args = parser.parse_args()
    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    payload = json.loads(raw)
    print(json.dumps(plan(payload), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
