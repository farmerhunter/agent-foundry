#!/usr/bin/env python3
"""Project an AF18 portable plan into a dry-run Codex adapter envelope."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


TOPOLOGY_TO_TOOL = {
    "durable_thread": ("send_message_to_thread", ("model", "thinking")),
    "fresh_thread": ("create_thread", ("model", "thinking")),
    "subagent": ("spawn_agent", ("model", "reasoning_effort")),
    "fork": ("fork_thread", ()),
}
VALID_STATUSES = {"supported", "unsupported", "unknown", "degraded", "not_available"}


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


def project(root: dict[str, Any]) -> dict[str, Any]:
    portable = require_object(root, "portable_plan")
    schema = require_object(root, "schema_observation")
    dispatch_plan = require_object(portable, "dispatch_plan")
    conversation = require_object(portable, "conversation_projection")
    decision = dispatch_plan.get("route_decision")
    selected = dispatch_plan.get("selected_candidate")
    if decision not in {"no_dispatch", "dispatch_advisory", "human_stop"}:
        fail("portable dispatch_plan.route_decision is invalid")
    if decision != "dispatch_advisory":
        return output(
            portable, None, None, "no_adapter_dispatch", [],
            "Continue the portable no-dispatch or Human-stop path; no Codex tool call is proposed.",
        )
    if not isinstance(selected, dict):
        fail("portable dispatch advisory requires selected_candidate")
    topology = selected.get("topology")
    if topology not in TOPOLOGY_TO_TOOL:
        return output(
            portable, topology, None, "unsupported", [f"Codex adapter has no supported mapping for topology {topology}"],
            "Choose a supported fresh, durable, or subagent route, or stop for a Human decision.",
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
            "Provide a currently supported explicit Codex envelope or keep the portable plan at no dispatch.",
        )
    if attention:
        return output(
            portable, topology, observed, "human_stop", attention,
            "Do not inherit unknown Codex settings; provide an explicit envelope or stop for a Human decision.",
        )
    return output(
        portable, topology, observed, "dry_run_ready", [],
        "Review this dry-run Codex envelope before any separately authorized dispatch.", envelope,
    )


def output(portable: dict[str, Any], topology: str | None, observed: dict[str, Any] | None, decision: str, attention: list[str], next_action: str, envelope: dict[str, Any] | None = None) -> dict[str, Any]:
    dispatch_plan = portable["dispatch_plan"]
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
        "adapter_plan": {
            "mode": "dry_run",
            "adapter_decision": decision,
            "topology": topology or "not_available",
            "tool_call_proposed": observed.get("tool") if observed else "not_available",
            "explicit_envelope": envelope or {},
            "lifecycle_evidence": lifecycle_evidence(portable, topology or "not_available"),
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
