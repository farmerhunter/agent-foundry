#!/usr/bin/env python3
"""Project an AF18 portable plan into a dry-run Codex adapter envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from typing import Any


TOPOLOGY_TO_TOOL = {
    "durable_thread": ("send_message_to_thread", ("model", "thinking")),
    "fresh_thread": ("create_thread", ("model", "thinking")),
    "subagent": ("spawn_agent", ("model", "reasoning_effort")),
    "fork": ("fork_thread", ()),
}
ROUTE_DECISION_TO_TOPOLOGY = {
    "reuse_relevant_thread": "durable_thread",
    "fresh_bounded_thread": "fresh_thread",
    "bounded_subagent": "subagent",
}
NO_ADAPTER_ROUTES = {
    "no_dispatch",
    "human_stop",
    "serial_current_session",
    "batch_checkpoint",
    "hold_for_decision",
}
DISPATCH_ADVISORY_ROUTES = {"dispatch_advisory"} | set(ROUTE_DECISION_TO_TOPOLOGY)
VALID_STATUSES = {"supported", "unsupported", "unknown", "degraded", "not_available"}
HOST_COLLECTION_MODE = "host_collected"
ROLE_OPERATION_CAPABILITIES = {
    "create": "create",
    "link": "link",
    "navigate": "navigate",
    "measure": "measure",
}
FORBIDDEN_RECEIPT_KEYS = {"prompt", "body", "message", "messages", "content", "transcript", "tool_output", "raw_log"}
ROLEHUB_TERMINAL_FAILURE = {"partial_hold", "rolled_back", "rollback_incomplete"}
ROLEHUB_TERMINAL = ROLEHUB_TERMINAL_FAILURE | {"ready"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_input(path: str) -> dict[str, Any]:
    value = json.loads(open(path, encoding="utf-8").read())
    if not isinstance(value, dict):
        fail("adapter input must be a JSON object")
    return value


def require_object(root: dict[str, Any], name: str) -> dict[str, Any]:
    value = root.get(name)
    if not isinstance(value, dict):
        fail(f"missing object: {name}")
    return value


def forbidden_paths(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, item in value.items():
            child = f"{path}.{key}"
            if key in FORBIDDEN_RECEIPT_KEYS:
                found.append(child)
            found.extend(forbidden_paths(item, child))
        return found
    if isinstance(value, list):
        return [item for index, value_item in enumerate(value) for item in forbidden_paths(value_item, f"{path}[{index}]")]
    return []


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def schema_digest(tools: dict[str, Any]) -> str:
    encoded = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def validate_observation(root: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    observation = root.get("schema_observation")
    context = root.get("adapter_context")
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return None, {"status": "unknown", "reason": "host-collected schema observation and adapter context are required"}
    tools = observation.get("tools")
    provenance = observation.get("provenance")
    observed_at = parse_timestamp(observation.get("observed_at"))
    evaluated_at = parse_timestamp(context.get("evaluated_at"))
    max_age = context.get("max_observation_age_seconds")
    if not isinstance(tools, dict) or not isinstance(provenance, dict):
        return None, {"status": "unknown", "reason": "schema observation is incomplete"}
    if provenance.get("collection_mode") != HOST_COLLECTION_MODE:
        return None, {"status": "untrusted", "reason": "schema observation is not host-collected"}
    if not isinstance(provenance.get("evidence_ref"), str) or not provenance["evidence_ref"]:
        return None, {"status": "untrusted", "reason": "host-collected schema observation lacks an evidence reference"}
    if provenance.get("schema_digest") != schema_digest(tools):
        return None, {"status": "untrusted", "reason": "host-collected schema observation digest does not match tools"}
    if not isinstance(observation.get("runtime_id"), str) or observation.get("runtime_id") != context.get("runtime_id"):
        return None, {"status": "untrusted", "reason": "schema observation runtime does not match the executing runtime"}
    if observed_at is None or evaluated_at is None or not isinstance(max_age, int) or max_age < 0:
        return None, {"status": "unknown", "reason": "schema observation freshness is not auditable"}
    age_seconds = abs((evaluated_at - observed_at).total_seconds())
    if age_seconds > max_age:
        return None, {"status": "stale", "reason": f"schema observation is stale by {int(age_seconds)} seconds"}
    # This JSON-only adapter has no runtime-owned schema capture or verifier.
    # Caller-provided fields can be internally consistent without proving the
    # executing host currently exposes the reported tools.
    return None, {
        "status": "unknown",
        "reason": "runtime-owned Codex schema capture is unavailable; caller-supplied observation is unverified",
        "evidence_ref": provenance["evidence_ref"],
        "evidence_ref_status": "unverified",
        "reported_age_seconds": int(age_seconds),
    }


def tool_observation(schema: dict[str, Any], tool_name: str) -> dict[str, Any]:
    tools = schema.get("tools")
    if not isinstance(tools, dict):
        fail("schema_observation.tools must be an object")
    observed = tools.get(tool_name, {})
    if not isinstance(observed, dict):
        observed = {}
    status = observed.get("status", "not_available")
    if status not in VALID_STATUSES:
        status = "unknown"
    fields = observed.get("fields", [])
    if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
        fields = []
    return {
        "tool": tool_name,
        "status": status,
        "fields": fields,
        "observed_at": schema.get("observed_at", "not_available"),
        "schema_source": schema.get("schema_source", "not_available"),
    }


def resolve_envelope(root: dict[str, Any], tool_name: str, required_fields: tuple[str, ...], capability: str) -> tuple[dict[str, Any] | None, list[str]]:
    envelopes = root.get("adapter_envelopes", {})
    if not isinstance(envelopes, dict):
        fail("adapter_envelopes must be an object")
    envelope = envelopes.get(capability)
    if not isinstance(envelope, dict):
        return None, [f"adapter-local envelope for {capability} is absent"]
    mapped: dict[str, Any] = {}
    failures: list[str] = []
    for field in required_fields:
        value = envelope.get(field)
        if not isinstance(value, str) or not value:
            failures.append(f"adapter-local envelope is missing {field}")
        else:
            mapped[field] = value
    return (mapped if not failures else None), failures


def lifecycle_evidence(portable: dict[str, Any], topology: str) -> dict[str, Any]:
    work = portable.get("work_unit", {})
    return {
        "work_unit_id": work.get("work_unit_id", "not_available"),
        "scope": "one_work_unit",
        "reset_after_attempt": True,
        "topology": topology,
        "close_archive_resume": "not_executed_dry_run_only",
        "lifecycle_mutation_performed": False,
    }


def role_task_dispatch_evidence(portable: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    projection = portable.get("conversation_projection", {})
    policy = projection.get("role_task_dispatch_policy", {}) if isinstance(projection, dict) else {}
    if not isinstance(policy, dict):
        policy = {}
    requested = portable.get("dispatch_plan", {})
    adapter_context = root.get("adapter_context", {})
    project_id = policy.get("project_id") or adapter_context.get("project_id") or "not_available"
    project_root = policy.get("project_root") or adapter_context.get("project_root") or "not_available"
    project_scoped = policy.get("project_scoped_creation", "unknown") != "unavailable" and project_id != "not_available"
    fallback = policy.get("degraded_projectless_fallback", {})
    if not isinstance(fallback, dict):
        fallback = {}
    return {
        "mechanism": "dry_run_codex_adapter",
        "project_scoped_vs_projectless": "project_scoped" if project_scoped else "projectless_degraded",
        "model_thinking_envelope": {
            "capability_tier": requested.get("requested_capability_tier", "not_available"),
            "reasoning_tier": requested.get("requested_reasoning_tier", "not_available"),
        },
        "target_project": {"project_id": project_id, "project_root": project_root},
        "existing_healthy_role_task_preferred": policy.get("existing_healthy_role_task_preferred", True),
        "fallback": {
            "used": not project_scoped,
            "allowed": fallback.get("allowed", not project_scoped),
            "bounded_to": fallback.get("bounded_to", "one_work_unit"),
            "reason": "project-scoped task creation unavailable or unsafe" if not project_scoped else "not_used",
        },
    }


def project_role_operation(root: dict[str, Any]) -> dict[str, Any]:
    operation = root.get("role_operation")
    if not isinstance(operation, dict):
        fail("role_operation must be an object")
    action = operation.get("action")
    capability = ROLE_OPERATION_CAPABILITIES.get(action)
    receipt = operation.get("capability_receipt")
    forbidden = forbidden_paths(operation)
    status = "unsupported"
    provenance = "unavailable"
    native_metadata: dict[str, Any] = {}
    reasons: list[str] = []
    if forbidden:
        reasons.append("privacy-safe receipt contains forbidden raw content")
    if capability is None:
        reasons.append("unknown role operation")
    if not isinstance(receipt, dict):
        reasons.append("capability receipt is unavailable")
    else:
        status = receipt.get("status", "unsupported")
        provenance = receipt.get("provenance", "unavailable")
        metadata = receipt.get("native_metadata", {})
        if isinstance(metadata, dict):
            native_metadata = metadata
        if receipt.get("capability") != capability:
            reasons.append("capability receipt does not bind the requested operation")
        if status not in VALID_STATUSES:
            reasons.append("capability receipt has an unknown status")
        if provenance not in {"observed", "estimated", "unavailable"}:
            reasons.append("capability receipt has an unknown provenance")
    if status in {"unsupported", "not_available", "unknown"} or provenance == "unavailable":
        reasons.append("capability is unavailable or unsupported")
        decision = "hold_required"
    elif reasons:
        decision = "hold_required"
    elif status == "degraded":
        decision = "dry_run_degraded"
        reasons.append("capability is degraded; no live operation is proposed")
    else:
        decision = "dry_run_ready"
    return {
        "adapter": "codex",
        "adapter_plan": {
            "mode": "dry_run",
            "adapter_decision": decision,
            "role_operation": action,
            "capability": capability or "not_available",
            "capability_status": status,
            "provenance": provenance,
            "tool_call_proposed": "not_available",
            "native_ids_are_metadata_only": True,
            "adapter_metadata": native_metadata,
        },
        "attention": reasons,
        "next_action": "Keep the portable Core route unchanged; obtain supported capability evidence before separately authorized execution.",
        "mutation_performed": False,
        "dispatch_performed": False,
        "user_config_mutation_performed": False,
        "hook_or_custom_agent_mutation_performed": False,
    }


def project_rolehub(root: dict[str, Any]) -> dict[str, Any]:
    """Validate a portable RoleHub projection without invoking a native API."""
    project_id = root.get("project_id")
    identity = root.get("rolehub_identity")
    operations = root.get("operations")
    if not isinstance(project_id, str) or not project_id or not isinstance(identity, dict) or not isinstance(operations, list):
        fail("rolehub projection requires project_id, rolehub_identity and operations")
    logical_id = identity.get("logical_id")
    if not isinstance(logical_id, str) or not logical_id:
        fail("rolehub_identity.logical_id is required")
    capabilities = root.get("capabilities", {})
    if not isinstance(capabilities, dict):
        capabilities = {}
    evidence = root.get("capability_evidence")
    trusted_capabilities = isinstance(evidence, dict) and evidence.get("trusted") is True and isinstance(evidence.get("producer"), str) and isinstance(evidence.get("runtime_id"), str) and evidence.get("project_id") == project_id and evidence.get("logical_rolehub_id") == logical_id
    seen_keys: set[str] = set()
    receipts: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    attention: list[str] = []
    role_matches = root.get("role_matches")
    if role_matches is not None:
        if not isinstance(role_matches, list):
            attention.append("role_matches must be an array")
        else:
            for role in ("Coordinator", "Architect"):
                matches = [item for item in role_matches if isinstance(item, dict) and item.get("role") == role and item.get("project_id") == project_id]
                healthy = [item for item in matches if item.get("active") is True and item.get("legacy") is not True]
                if len(matches) > 1 or any(item.get("legacy") is True for item in matches):
                    attention.append(f"duplicate or legacy {role} match requires hold")
                elif len(healthy) == 0:
                    attention.append(f"no reusable {role}; creation must remain a plan")
    terminal_seen = False
    expected_sequence = 0
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            attention.append(f"operation {index} is not an object")
            continue
        key = operation.get("idempotency_key")
        action = operation.get("action")
        if not isinstance(key, str) or not key:
            attention.append(f"operation {index} is missing idempotency_key")
        elif key in seen_keys:
            attention.append(f"duplicate idempotency_key: {key}")
        else:
            seen_keys.add(key)
        forbidden = forbidden_paths(operation)
        if forbidden:
            attention.append(f"privacy violation at {forbidden[0]}")
        if action not in {"create", "reuse", "link", "navigate"}:
            attention.append(f"unsupported rolehub action: {action}")
            continue
        if operation.get("role") in {"Implementer", "Reviewer", "Tester", "Harvester"} and action in {"create", "reuse", "link"}:
            attention.append("Work roles are transient and cannot be persisted in RoleHub")
        if action in {"create", "link", "navigate"} and capabilities.get(action) not in {"supported"}:
            attention.append(f"capability unavailable for {action}")
        elif action in {"create", "link", "navigate"} and not trusted_capabilities:
            attention.append(f"trusted capability evidence unavailable for {action}")
        preimage = operation.get("preimage")
        receipt = operation.get("receipt")
        if action in {"link", "navigate"} and not isinstance(preimage, dict):
            attention.append(f"missing preimage for {operation.get('operation_id', index)}")
        if not isinstance(receipt, dict):
            attention.append(f"missing receipt for {operation.get('operation_id', index)}")
            continue
        fingerprint_payload = {key: value for key, value in operation.items() if key != "receipt"}
        fingerprint = f"sha256:{hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}"
        if receipt.get("project_id") != project_id or receipt.get("logical_rolehub_id") != logical_id:
            attention.append(f"cross-project or identity-mismatched receipt for {operation.get('operation_id', index)}")
        if receipt.get("operation_id") != operation.get("operation_id") or receipt.get("idempotency_key") != key or receipt.get("operation_fingerprint") != fingerprint or not isinstance(receipt.get("opaque_ref"), str) or not isinstance(receipt.get("readback"), dict):
            attention.append(f"receipt binding/readback mismatch for {operation.get('operation_id', index)}")
        if receipt.get("sequence") != expected_sequence:
            attention.append(f"out-of-order receipt for {operation.get('operation_id', index)}")
        expected_sequence += 1
        if terminal_seen:
            attention.append("receipt appears after terminal receipt")
        status = receipt.get("status")
        if status in ROLEHUB_TERMINAL:
            terminal_seen = True
        elif status not in {"applied", "ready"}:
            attention.append(f"invalid receipt status for {operation.get('operation_id', index)}")
        if status == "applied":
            applied.append(operation)
        receipts.append(receipt)
    if any(receipt.get("status") == "failed" for receipt in receipts):
        attention.append("operation failure requires partial_hold and reverse rollback")
    rollback = root.get("rollback", {})
    if not isinstance(rollback, dict):
        rollback = {}
    rollback_receipt = rollback.get("receipt")
    rollback_forbidden = forbidden_paths(rollback)
    if rollback_forbidden:
        attention.append(f"privacy violation at {rollback_forbidden[0]}")
    applied_ids = [op.get("operation_id") for op in applied]
    rollback_valid = not rollback_forbidden and isinstance(rollback_receipt, dict) and rollback_receipt.get("status") == "complete" and rollback_receipt.get("reversed_operation_ids") == list(reversed(applied_ids)) and all(isinstance(op.get("preimage"), dict) or op.get("action") == "create" for op in applied)
    if rollback.get("status") == "failed" or (rollback.get("status") in {"required", "complete"} and not rollback_valid):
        attention.append("rollback receipt missing or failed")
        rollback_state = "rollback_incomplete"
    elif rollback_valid:
        rollback_state = "rolled_back"
    else:
        rollback_state = "not_attempted"
    state = "ready" if not attention and not terminal_seen else "partial_hold"
    if rollback_state in {"rolled_back", "rollback_incomplete"}:
        state = rollback_state
    return {
        "adapter": "codex",
        "contract_version": root.get("contract_version", "not_available"),
        "project_id": project_id,
        "rolehub_identity": {"logical_id": logical_id},
        "state": state,
        "operations": [{"operation_id": op.get("operation_id", "not_available"), "action": op.get("action"), "status": "applied" if op in applied else "held"} for op in operations if isinstance(op, dict)],
        "applied_operations": [op.get("operation_id", "not_available") for op in applied],
        "rollback": {"status": rollback_state, "applied_only": True, "delete_or_archive": False},
        "attention": attention,
        "native_io_performed": False,
        "mutation_performed": False,
        "dispatch_performed": False,
        "next_action": "Hold for an independently authorized adapter execution receipt." if state == "partial_hold" else "Portable projection is ready; no native call is proposed.",
    }


def project(root: dict[str, Any]) -> dict[str, Any]:
    if "rolehub_identity" in root:
        return project_rolehub(root)
    if "role_operation" in root:
        return project_role_operation(root)
    portable = require_object(root, "portable_plan")
    dispatch_plan = require_object(portable, "dispatch_plan")
    require_object(portable, "conversation_projection")
    decision = dispatch_plan.get("route_decision")
    selected = dispatch_plan.get("selected_candidate")
    if decision not in NO_ADAPTER_ROUTES | DISPATCH_ADVISORY_ROUTES:
        fail("portable dispatch_plan.route_decision is invalid")
    if decision in NO_ADAPTER_ROUTES:
        return output(
            portable, None, None, "no_adapter_dispatch", [],
            "Continue the portable no-dispatch or Human-stop path; no Codex tool call is proposed.", root=root,
        )
    if not isinstance(selected, dict):
        fail("portable dispatch advisory requires selected_candidate")
    topology = selected.get("topology") or ROUTE_DECISION_TO_TOPOLOGY.get(str(decision))
    if topology not in TOPOLOGY_TO_TOOL:
        return output(
            portable, topology, None, "unsupported", [f"Codex adapter has no supported mapping for topology {topology}"],
            "Choose a supported fresh, durable, or subagent route, or stop for a Human decision.", root=root,
        )
    schema, provenance = validate_observation(root)
    if schema is None:
        return output(
            portable, topology, None, "unknown", [provenance["reason"]],
            "Obtain a verified runtime-owned Codex schema capture before proposing any envelope.", provenance=provenance, root=root,
        )
    tool_name, required_fields = TOPOLOGY_TO_TOOL[topology]
    observed = tool_observation(schema, tool_name)
    requested = dispatch_plan.get("requested_capability_tier", "not_available")
    requires_explicit = portable.get("work_unit", {}).get("requires_explicit_envelope", False) is True
    attention: list[str] = []
    if observed["status"] != "supported":
        attention.append(f"Codex tool {tool_name} is {observed['status']}")
    if not required_fields:
        attention.append(f"Codex tool {tool_name} has no explicit envelope fields")
    missing_fields = [field for field in required_fields if field not in observed["fields"]]
    if missing_fields:
        attention.append(f"Codex tool {tool_name} is missing observed fields: {', '.join(missing_fields)}")
    envelope, envelope_failures = resolve_envelope(root, tool_name, required_fields, requested)
    if envelope_failures:
        attention.extend(envelope_failures)
    if requires_explicit and attention:
        return output(
            portable, topology, observed, "unsupported", attention,
            "Provide a currently supported explicit Codex envelope or keep the portable plan at no dispatch.", provenance=provenance, root=root,
        )
    if attention:
        return output(
            portable, topology, observed, "human_stop", attention,
            "Do not inherit unknown Codex settings; provide an explicit envelope or stop for a Human decision.", provenance=provenance, root=root,
        )
    return output(
        portable, topology, observed, "dry_run_ready", [],
        "Review this dry-run Codex envelope before any separately authorized dispatch.", envelope, provenance, root=root,
    )


def output(portable: dict[str, Any], topology: str | None, observed: dict[str, Any] | None, decision: str, attention: list[str], next_action: str, envelope: dict[str, Any] | None = None, provenance: dict[str, Any] | None = None, root: dict[str, Any] | None = None) -> dict[str, Any]:
    dispatch_plan = portable["dispatch_plan"]
    adapter_root = root or {}
    requested = {
        "capability_tier": dispatch_plan.get("requested_capability_tier", "not_available"),
        "reasoning_tier": dispatch_plan.get("requested_reasoning_tier", "not_available"),
        "explicit_envelope": envelope or "not_available",
    }
    observable = {
        "tool_status": observed.get("status", "not_available") if observed else "not_available",
        "fields_observed": observed.get("fields", []) if observed else [],
        "effective_configuration": "unknown",
        "enforcement": "not_executed_dry_run_only",
    }
    return {
        "adapter": "codex",
        "schema_observation": observed or {"observed_at": "not_available", "schema_source": "not_available"},
        "schema_provenance": provenance or {"status": "not_available", "reason": "no adapter schema observation was needed"},
        "adapter_plan": {
            "mode": "dry_run",
            "adapter_decision": decision,
            "topology": topology or "not_available",
            "tool_call_proposed": observed.get("tool") if observed else "not_available",
            "explicit_envelope": envelope or {},
            "lifecycle_evidence": lifecycle_evidence(portable, topology or "not_available"),
            "role_task_dispatch_evidence": role_task_dispatch_evidence(portable, adapter_root),
        },
        "conversation_projection": {
            "portable": portable["conversation_projection"],
            "requested_vs_observable": {"requested": requested, "observable": observable},
            "attention": attention,
            "next_action": next_action,
        },
        "mutation_performed": False,
        "dispatch_performed": False,
        "user_config_mutation_performed": False,
        "hook_or_custom_agent_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", required=True, help="Portable plan plus current Codex schema observation.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. This is the default output format.")
    args = parser.parse_args()
    try:
        print(json.dumps(project(load_input(args.input_json)), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"codex_route_adapter_error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
