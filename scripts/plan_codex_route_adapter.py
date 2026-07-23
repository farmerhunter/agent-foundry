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


def project(root: dict[str, Any]) -> dict[str, Any]:
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
