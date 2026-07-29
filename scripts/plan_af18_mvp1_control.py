#!/usr/bin/env python3
"""Plan AF18 MVP-1 lifecycle control-plane decisions without dispatch."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import plan_collaboration_routes as cost_policy


POLICY_SOURCE = "scripts/plan_collaboration_routes.py"
POLICY_VERSION = "af18-cost-policy-440-442"
CONTROL_VERSION = "af18-mvp1-control-plane-v1"
ROUTE_PERMISSIONS = {
    "isolated_execution": "allow",
    "interactive_execution": "successor_required",
    "serial_execution": "allow",
    "external_execution": "hold_required",
    "privileged_execution": "hold_required",
}
RESOURCE_PROVENANCE = {"observed", "estimated", "unavailable"}
FORBIDDEN_PACKET_KEYS = {
    "prompt",
    "body",
    "message",
    "messages",
    "content",
    "tool_history",
    "raw_tool_history",
    "raw_large_diff",
    "large_diff",
    "raw_log",
    "log",
    "full_history",
    "transcript",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan AF18 MVP-1 lifecycle control-plane readouts and preflights.")
    parser.add_argument("--input", help="Control-plane packet JSON path. Defaults to stdin when provided.")
    parser.add_argument("--mode", choices=("preflight", "readout", "explain"), default="preflight")
    parser.add_argument("--now", help="Current UTC timestamp for deterministic tests.")
    return parser.parse_args()


def read_packet(path: str | None) -> dict[str, Any]:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        return {}
    if not text.strip():
        return {}
    value = json.loads(text)
    if not isinstance(value, dict):
        raise SystemExit("control-plane packet must be a JSON object")
    return value


def utc_now(raw: str | None) -> dt.datetime:
    if raw:
        return cost_policy.parse_timestamp(raw, "now")
    return dt.datetime.now(dt.timezone.utc)


def missing(value: Any) -> bool:
    return value in (None, "", [], {})


def find_forbidden(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if key in FORBIDDEN_PACKET_KEYS:
                found.append(child)
            found.extend(find_forbidden(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_forbidden(item, f"{path}[{index}]"))
    return found


def active_policy_readout() -> dict[str, Any]:
    return {
        "control_version": CONTROL_VERSION,
        "policy_source": POLICY_SOURCE,
        "policy_version": POLICY_VERSION,
        "read_only": True,
        "readback_default": "cursor_only_compact",
        "threshold_bands": cost_policy.THRESHOLD_BANDS,
        "global_hard_context_ceiling": cost_policy.GLOBAL_HARD_CONTEXT_CEILING,
        "effective_context_ceiling_rule": "min(threshold_band.max_context_tokens, global_hard_context_ceiling)",
        "model_ceiling": cost_policy.DEFAULT_CEILING_MODEL,
        "reasoning_ceiling": cost_policy.DEFAULT_CEILING_REASONING,
        "route_permissions": ROUTE_PERMISSIONS,
        "override_requirements": {
            "threshold_exception": ["issue", "role", "temporary_cap", "reason", "expiry"],
            "model_escalation": ["issue", "role", "model", "reasoning", "purpose", "budget"],
        },
        "fail_closed_on": [
            "missing_policy",
            "unknown_classification",
            "missing_budget",
            "stale_context",
            "oversized_context",
            "model_ceiling_breach",
            "duplicate_dispatch_claim",
            "duplicate_active_run",
            "missing_resource_observation",
            "missing_context_token_measurement",
            "resource_measurement_unavailable",
            "privacy_exposure",
        ],
        "resource_observation_policy": {
            "accepted_provenance": sorted(RESOURCE_PROVENANCE),
            "missing_or_unavailable": "hold_required_or_explicit_lower_capability_policy",
            "missing_counts_as_zero": False,
        },
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def effective_snapshot(packet: dict[str, Any], now: dt.datetime, stops: list[str]) -> dict[str, Any]:
    work = packet.get("work") if isinstance(packet.get("work"), dict) else {}
    run = packet.get("execution_run") if isinstance(packet.get("execution_run"), dict) else {}
    context = run.get("context") if isinstance(run.get("context"), dict) else {}
    model = run.get("model") if isinstance(run.get("model"), dict) else {}
    observations = context.get("resource_observations") if isinstance(context.get("resource_observations"), dict) else {}
    context_tokens = observations.get("context_tokens") if isinstance(observations.get("context_tokens"), dict) else {}
    issue = work.get("issue")
    role = work.get("role")
    threshold = cost_policy.resolve_threshold(context, now, stops, issue, role)
    return {
        "policy_source": POLICY_SOURCE,
        "policy_version": POLICY_VERSION,
        "threshold": threshold,
        "effective_context_ceiling_rule": "min(threshold_band.max_context_tokens, global_hard_context_ceiling)",
        "model_ceiling": cost_policy.DEFAULT_CEILING_MODEL,
        "reasoning_ceiling": cost_policy.DEFAULT_CEILING_REASONING,
        "requested_model": model.get("name"),
        "requested_reasoning": model.get("reasoning"),
        "resource_observation": {
            "context_tokens": {
                "provenance": context_tokens.get("provenance"),
                "tokens": context_tokens.get("tokens") if isinstance(context_tokens.get("tokens"), int) else None,
                "source": context_tokens.get("source"),
                "lower_capability_policy": context_tokens.get("lower_capability_policy"),
            }
        },
        "route_permissions": ROUTE_PERMISSIONS,
    }


def validate_required(work: dict[str, Any], run: dict[str, Any], claim: dict[str, Any], stops: list[str]) -> None:
    for field in ("work_id", "issue", "role", "phase", "root_budget_tokens", "remaining_budget_tokens", "durable_anchors", "stop_conditions"):
        if missing(work.get(field)):
            stops.append(f"missing_work_{field}")
    for field in ("run_id", "work_id", "role", "state", "context", "model"):
        if missing(run.get(field)):
            stops.append(f"missing_execution_run_{field}")
    for field in ("idempotency_key", "work_id", "role", "decision_boundary", "transition_semantics", "durable_anchor"):
        if missing(claim.get(field)):
            stops.append(f"missing_dispatch_claim_{field}")

    if not isinstance(work.get("root_budget_tokens"), int) or work.get("root_budget_tokens", 0) <= 0:
        stops.append("missing_budget")
    if not isinstance(work.get("remaining_budget_tokens"), int) or work.get("remaining_budget_tokens", 0) < 0:
        stops.append("missing_budget")
    if isinstance(work.get("remaining_budget_tokens"), int) and isinstance(work.get("root_budget_tokens"), int):
        if work["remaining_budget_tokens"] > work["root_budget_tokens"]:
            stops.append("budget_breach")
    if run.get("work_id") not in (None, work.get("work_id")) or run.get("role") not in (None, work.get("role")):
        stops.append("run_work_role_mismatch")
    if claim.get("work_id") not in (None, work.get("work_id")) or claim.get("role") not in (None, work.get("role")):
        stops.append("claim_work_role_mismatch")


def context_token_count(context: dict[str, Any], stops: list[str]) -> int | None:
    observations = context.get("resource_observations")
    if not isinstance(observations, dict):
        stops.append("missing_resource_observation")
        return None
    context_tokens = observations.get("context_tokens")
    if not isinstance(context_tokens, dict):
        stops.append("missing_resource_observation")
        return None
    provenance = context_tokens.get("provenance")
    if provenance not in RESOURCE_PROVENANCE:
        stops.append("unknown_resource_observation_provenance")
        return None
    if provenance == "unavailable":
        if context_tokens.get("lower_capability_policy") == "serial_execution_only":
            stops.append("resource_measurement_lower_capability_required")
        else:
            stops.append("resource_measurement_unavailable")
        return None
    tokens = context_tokens.get("tokens")
    if not isinstance(tokens, int) or tokens < 0:
        stops.append("missing_context_token_measurement")
        return None
    return tokens


def validate_context(run: dict[str, Any], snapshot: dict[str, Any], now: dt.datetime, stops: list[str]) -> None:
    context = run.get("context") if isinstance(run.get("context"), dict) else {}
    try:
        source_ts = cost_policy.parse_timestamp(context.get("source_timestamp"), "execution_run.context.source_timestamp")
    except (TypeError, ValueError):
        stops.append("missing_or_invalid_source_timestamp")
        source_ts = None
    if source_ts is not None and now - source_ts > dt.timedelta(hours=snapshot["threshold"]["max_age_hours"]):
        stops.append("stale_context")
    context_size = context_token_count(context, stops)
    if isinstance(context_size, int) and context_size > snapshot["threshold"]["max_context_tokens"]:
        stops.append("oversized_context")


def validate_model(run: dict[str, Any], stops: list[str]) -> None:
    model = run.get("model") if isinstance(run.get("model"), dict) else {}
    requested_model = model.get("name")
    requested_reasoning = model.get("reasoning")
    if cost_policy.model_rank(requested_model) is None:
        stops.append("missing_or_unknown_model")
    elif cost_policy.model_rank(requested_model) > cost_policy.model_rank(cost_policy.DEFAULT_CEILING_MODEL):
        if not cost_policy.valid_escalation_approval(model.get("human_escalation_approval")):
            stops.append("model_escalation_requires_human_approval")
    if cost_policy.reasoning_rank(requested_reasoning) is None:
        stops.append("missing_or_unknown_reasoning")
    elif cost_policy.reasoning_rank(requested_reasoning) > cost_policy.reasoning_rank(cost_policy.DEFAULT_CEILING_REASONING):
        if not cost_policy.valid_escalation_approval(model.get("human_escalation_approval")):
            stops.append("reasoning_escalation_requires_human_approval")


def duplicate_claim_seen(claim: dict[str, Any], existing: Any) -> bool:
    if not isinstance(existing, list):
        return False
    for item in existing:
        if not isinstance(item, dict):
            continue
        same_boundary = all(item.get(key) == claim.get(key) for key in ("work_id", "role", "decision_boundary"))
        same_transition = item.get("transition_semantics") in (None, claim.get("transition_semantics"))
        if same_boundary and same_transition:
            return True
    return False


def duplicate_active_run(work: dict[str, Any], run: dict[str, Any], active_runs: Any) -> bool:
    if not isinstance(active_runs, list):
        return False
    for item in active_runs:
        if not isinstance(item, dict):
            continue
        if item.get("state") == "active" and item.get("work_id") == work.get("work_id") and item.get("role") == work.get("role"):
            if item.get("run_id") != run.get("run_id"):
                return True
    return False


def successor_packet(work: dict[str, Any], run: dict[str, Any], route: str, now: dt.datetime) -> dict[str, Any]:
    return {
        "packet_type": "SuccessorPacket",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "work_id": work.get("work_id"),
        "role": work.get("role"),
        "phase": work.get("phase"),
        "root_budget_tokens": work.get("root_budget_tokens"),
        "remaining_budget_tokens": work.get("remaining_budget_tokens"),
        "durable_anchors": work.get("durable_anchors", []),
        "stop_conditions": work.get("stop_conditions", []),
        "predecessor_run_id": run.get("run_id"),
        "requested_route": route,
        "context_policy": "cursor_only_compact_no_prompt_body_no_full_history",
        "exclusions": sorted(FORBIDDEN_PACKET_KEYS),
    }


def plan_preflight(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    stops: list[str] = []
    warnings: list[str] = []
    work = packet.get("work") if isinstance(packet.get("work"), dict) else {}
    run = packet.get("execution_run") if isinstance(packet.get("execution_run"), dict) else {}
    claim = packet.get("dispatch_claim") if isinstance(packet.get("dispatch_claim"), dict) else {}
    route = packet.get("requested_route")
    validate_required(work, run, claim, stops)
    if route not in ROUTE_PERMISSIONS:
        stops.append("unknown_route_classification")
        route = "unknown"
    snapshot = effective_snapshot(packet, now, stops)
    validate_context(run, snapshot, now, stops)
    validate_model(run, stops)
    if duplicate_claim_seen(claim, packet.get("existing_dispatch_claims")):
        stops.append("duplicate_dispatch_claim")
    if duplicate_active_run(work, run, packet.get("active_runs")):
        stops.append("duplicate_active_run")
    forbidden = find_forbidden(packet)
    if forbidden:
        stops.append("privacy_exposure")
        warnings.append("forbidden_content_paths:" + ",".join(forbidden))

    permission = ROUTE_PERMISSIONS.get(route, "hold_required")
    if stops:
        decision = "hold_required"
    elif permission == "allow":
        decision = "allow"
    elif permission == "successor_required":
        decision = "successor_required"
    else:
        decision = "hold_required"
        stops.append(f"route_not_permitted:{route}")

    result = {
        "control_version": CONTROL_VERSION,
        "decision": decision,
        "classification": route,
        "matched_routing_rule": permission,
        "selected_route": route if decision in {"allow", "successor_required"} else None,
        "held_route": route if decision == "hold_required" else None,
        "work_id": work.get("work_id"),
        "role": work.get("role"),
        "root_budget_tokens": work.get("root_budget_tokens"),
        "remaining_budget_tokens": work.get("remaining_budget_tokens"),
        "effective_control_snapshot": snapshot,
        "stop_conditions": sorted(set(stops)),
        "warnings": warnings,
        "reason": "preflight passed" if decision == "allow" else "successor context required" if decision == "successor_required" else "fail-closed hold required",
        "one_recovery_action": None if decision != "hold_required" else "ask Coordinator for a compact issue-specific packet or Human approval",
        "mutation_performed": False,
        "dispatch_performed": False,
    }
    if decision == "successor_required":
        result["successor_packet"] = successor_packet(work, run, route, now)
        result["transition_receipt"] = {
            "receipt_type": "TransitionReceipt",
            "from_run_id": run.get("run_id"),
            "work_id": work.get("work_id"),
            "role": work.get("role"),
            "decision": decision,
            "root_budget_tokens": work.get("root_budget_tokens"),
            "remaining_budget_tokens": work.get("remaining_budget_tokens"),
            "mutation_performed": False,
            "dispatch_performed": False,
        }
    return result


def explain_work_policy(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    preflight = plan_preflight(packet, now)
    return {
        "control_version": CONTROL_VERSION,
        "classification": preflight["classification"],
        "matched_routing_rule": preflight["matched_routing_rule"],
        "effective_control_snapshot": preflight["effective_control_snapshot"],
        "selected_route": preflight["selected_route"],
        "held_route": preflight["held_route"],
        "work_id": preflight["work_id"],
        "role": preflight["role"],
        "root_budget_tokens": preflight["root_budget_tokens"],
        "remaining_budget_tokens": preflight["remaining_budget_tokens"],
        "decision": preflight["decision"],
        "reason": preflight["reason"],
        "stop_conditions": preflight["stop_conditions"],
        "one_recovery_action": preflight["one_recovery_action"],
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def main() -> int:
    args = parse_args()
    packet = read_packet(args.input)
    now = utc_now(args.now)
    if args.mode == "readout":
        result = active_policy_readout()
    elif args.mode == "explain":
        result = explain_work_policy(packet, now)
    else:
        result = plan_preflight(packet, now)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
