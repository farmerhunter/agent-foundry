#!/usr/bin/env python3
"""Plan AF18 MVP-2 runtime-owned controlled observation bridge decisions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import plan_af18_mvp1_control as control
import validate_runtime_owned_capture as capture_validator


BRIDGE_VERSION = "af18-mvp2-observation-bridge-v1"
SNAPSHOT_SOURCE = "#442 low_limit containment"
SNAPSHOT_VERSION = "af18-451-option-a-literal-v1"
SNAPSHOT_BAND = "low_limit_experiment"
COORDINATOR_EVENT_TYPES = {
    "before_new_issue_work",
    "after_compact_durable_readback",
    "after_material_input_or_tool_output_increase",
    "before_role_dispatch",
    "after_role_dispatch",
    "before_callback",
    "after_callback",
    "before_human_hdc_output",
    "after_human_hdc_output",
    "policy_anomaly",
    "evidence_anomaly",
    "budget_anomaly",
}
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")
TELEMETRY_FIELDS = TOKEN_FIELDS + ("tool_output_bytes",)
AVAILABILITY = {"observed", "estimated", "unavailable"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan AF18 MVP-2 runtime-owned observation bridge decisions.")
    parser.add_argument("--input", help="Bridge packet JSON path. Defaults to stdin when provided.")
    parser.add_argument("--now", help="Current UTC timestamp for deterministic tests.")
    parser.add_argument("--max-capture-age-hours", type=int, default=12)
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
        raise SystemExit("bridge packet must be a JSON object")
    return value


def utc_now(raw: str | None) -> dt.datetime:
    if raw:
        return control.cost_policy.parse_timestamp(raw, "now")
    return dt.datetime.now(dt.timezone.utc)


def missing(value: Any) -> bool:
    return value in (None, "", [], {})


def literal_snapshot(packet: dict[str, Any], stops: list[str]) -> dict[str, Any]:
    snapshot = packet.get("effective_control_snapshot")
    if not isinstance(snapshot, dict):
        stops.append("missing_literal_effective_control_snapshot")
        return {}
    required = {
        "source": SNAPSHOT_SOURCE,
        "version": SNAPSHOT_VERSION,
        "band": SNAPSHOT_BAND,
        "label": SNAPSHOT_BAND,
        "coordinator_lifecycle_model": "CoordinatorSession -> CoordinationWindow -> coordination operation",
        "threshold_band": "coordinator_routing_status_readback",
        "max_context_tokens": 4000,
        "max_age_hours": 12,
        "measurement_unavailable_policy": "hold_required",
        "normal_threshold_breach": "successor_required",
    }
    for key, expected in required.items():
        if snapshot.get(key) != expected:
            stops.append(f"literal_snapshot_{key}_mismatch")
    for field in ("root_budget_tokens", "window_id", "stop_conditions", "allowed_route"):
        if missing(snapshot.get(field)):
            stops.append(f"missing_literal_snapshot_{field}")
    if snapshot.get("allowed_route") != "isolated_execution":
        stops.append("literal_snapshot_allowed_route_mismatch")
    return snapshot


def validate_event(packet: dict[str, Any], stops: list[str]) -> str:
    event_type = packet.get("coordinator_event_type")
    if event_type not in COORDINATOR_EVENT_TYPES:
        stops.append("unbounded_or_unknown_lifecycle_event")
        return "unknown"
    return str(event_type)


def telemetry_projection(packet: dict[str, Any], stops: list[str]) -> dict[str, Any]:
    telemetry = packet.get("runtime_telemetry")
    if not isinstance(telemetry, dict):
        stops.append("missing_runtime_telemetry")
        telemetry = {}
    projection: dict[str, Any] = {}
    total_context_tokens = 0
    total_context_available = True
    for field in TELEMETRY_FIELDS:
        item = telemetry.get(field)
        if not isinstance(item, dict):
            stops.append(f"missing_{field}")
            projection[field] = {"availability": "unavailable", "value": None}
            total_context_available = False
            continue
        availability = item.get("availability")
        if availability not in AVAILABILITY:
            stops.append(f"unknown_{field}_availability")
            availability = "unavailable"
        value = item.get("value")
        if availability == "unavailable":
            stops.append(f"{field}_unavailable")
            total_context_available = False
            value = None
        elif not isinstance(value, int) or value < 0:
            stops.append(f"missing_{field}_value")
            total_context_available = False
            value = None
        projection[field] = {
            "availability": availability,
            "value": value,
            "source": item.get("source"),
        }
        if field in TOKEN_FIELDS and isinstance(value, int):
            total_context_tokens += value
    projection["total_context_tokens"] = {
        "availability": "observed" if total_context_available else "unavailable",
        "value": total_context_tokens if total_context_available else None,
        "missing_counts_as_zero": False,
    }
    for field in ("route", "transition_reason"):
        if missing(telemetry.get(field)):
            stops.append(f"missing_runtime_telemetry_{field}")
        projection[field] = telemetry.get(field)
    cumulative = telemetry.get("cumulative_work_totals")
    if not isinstance(cumulative, dict):
        stops.append("missing_cumulative_work_totals")
        cumulative = {}
    projection["cumulative_work_totals"] = cumulative
    return projection


def validate_runtime_capture(packet: dict[str, Any], now: dt.datetime, max_age_hours: int, stops: list[str]) -> dict[str, Any]:
    record = packet.get("runtime_capture")
    if not isinstance(record, dict) or not record:
        stops.append("missing_runtime_capture")
        return {"valid": False, "errors": ["missing_runtime_capture"]}
    result = capture_validator.validate(record, now, max_age_hours)
    if result["valid"] is not True:
        for error in result.get("errors", []):
            if error in {"caller_only_evidence", "forged_evidence", "stale_evidence", "missing_producer"}:
                stops.append(error)
            else:
                stops.append(f"runtime_capture_{error}")
    if result.get("runtime_owned") is not True:
        stops.append("caller_only_evidence")
    return result


def threshold_breached(snapshot: dict[str, Any], telemetry: dict[str, Any]) -> bool:
    value = telemetry.get("total_context_tokens", {}).get("value")
    limit = snapshot.get("max_context_tokens")
    return isinstance(value, int) and isinstance(limit, int) and value > limit


def control_plane_packet(packet: dict[str, Any], snapshot: dict[str, Any], telemetry: dict[str, Any]) -> dict[str, Any]:
    work = dict(packet.get("work") if isinstance(packet.get("work"), dict) else {})
    run = dict(packet.get("execution_run") if isinstance(packet.get("execution_run"), dict) else {})
    context = dict(run.get("context") if isinstance(run.get("context"), dict) else {})
    model = dict(run.get("model") if isinstance(run.get("model"), dict) else {})
    work.setdefault("role", "Coordinator")
    work.setdefault("phase", "mvp2-observation-bridge")
    run["work_id"] = work.get("work_id")
    run["role"] = work.get("role")
    total_context_value = telemetry["total_context_tokens"]["value"]
    context_tokens_value = total_context_value
    if threshold_breached(snapshot, telemetry):
        context_tokens_value = snapshot["max_context_tokens"]
    context.update(
        {
            "threshold_band": "coordinator_routing_status_readback",
            "resource_observations": {
                "context_tokens": {
                    "provenance": telemetry["total_context_tokens"]["availability"],
                    "tokens": context_tokens_value,
                    "source": "runtime_owned_observation_bridge",
                }
            },
        }
    )
    if "source_timestamp" not in context:
        context["source_timestamp"] = packet.get("observed_at")
    run["context"] = context
    run["model"] = model or {"name": "gpt-5.5", "reasoning": "medium"}
    return {
        "work": work,
        "execution_run": run,
        "dispatch_claim": packet.get("dispatch_claim", {}),
        "existing_dispatch_claims": packet.get("existing_dispatch_claims", []),
        "active_runs": packet.get("active_runs", []),
        "requested_route": "interactive_execution" if threshold_breached(snapshot, telemetry) else snapshot.get("allowed_route", "isolated_execution"),
        "attention_events": packet.get("attention_events", []),
        "adapter_metadata": {
            "runtime_binding": "codex",
            "native_ids_are_adapter_metadata": True,
            "native_session_id": packet.get("native_session_id"),
            "coordination_window_id": snapshot.get("window_id"),
        },
    }


def bridge_decision(packet: dict[str, Any], now: dt.datetime, max_age_hours: int = 12) -> dict[str, Any]:
    stops: list[str] = []
    warnings: list[str] = []
    event_type = validate_event(packet, stops)
    snapshot = literal_snapshot(packet, stops)
    capture_result = validate_runtime_capture(packet, now, max_age_hours, stops)
    telemetry = telemetry_projection(packet, stops)
    forbidden = control.find_forbidden(packet)
    if forbidden:
        stops.append("privacy_exposure")
        warnings.append("forbidden_content_paths:" + ",".join(forbidden))

    planner_packet = control_plane_packet(packet, snapshot, telemetry)
    lifecycle = control.plan_preflight(planner_packet, now)
    if lifecycle["decision"] == "hold_required":
        stops.extend(lifecycle["stop_conditions"])
    elif stops:
        lifecycle["decision"] = "hold_required"
        lifecycle["selected_route"] = None
        lifecycle["held_route"] = planner_packet["requested_route"]
        lifecycle["reason"] = "fail-closed hold required"
    elif threshold_breached(snapshot, telemetry) and lifecycle["decision"] == "successor_required":
        lifecycle["reason"] = "low_limit_experiment threshold breach requires automatic successor"

    effective_stops = sorted(set(stops))
    if effective_stops:
        decision = "hold_required"
    else:
        decision = lifecycle["decision"]

    policy_material_events = list(packet.get("attention_events", [])) if isinstance(packet.get("attention_events"), list) else []
    if decision == "successor_required":
        policy_material_events.append(
            {
                "category": "context_budget_strategy_change",
                "reason": "low_limit_experiment successor_required with inherited root budget",
                "evidence_ref": packet.get("evidence_ref"),
            }
        )
    elif decision == "hold_required":
        policy_material_events.append(
            {
                "category": "acceptance_evidence_conflict",
                "reason": "runtime observation bridge failed closed",
                "evidence_ref": packet.get("evidence_ref"),
            }
        )
    summary_packet = {**planner_packet, "attention_events": policy_material_events}
    work_summary = control.work_summary_projection(summary_packet, now)
    attention_summary = control.attention_summary_projection(summary_packet, now)

    result = {
        "bridge_version": BRIDGE_VERSION,
        "decision": decision,
        "experiment_label": SNAPSHOT_BAND,
        "coordinator_lifecycle_model": snapshot.get("coordinator_lifecycle_model"),
        "coordinator_event_type": event_type,
        "bounded_meaningful_event": event_type in COORDINATOR_EVENT_TYPES,
        "effective_control_snapshot": snapshot,
        "runtime_capture_validation": capture_result,
        "runtime_owned_observation": capture_result.get("runtime_owned") is True and not effective_stops,
        "telemetry": telemetry,
        "lifecycle_evaluator": lifecycle,
        "work_summary": work_summary,
        "attention_summary": attention_summary,
        "raw_receipt_default_suppressed": "TransitionReceipt" in work_summary["default_human_ux_excludes"],
        "stop_conditions": effective_stops,
        "warnings": warnings,
        "mutation_performed": False,
        "dispatch_performed": False,
        "external_action_performed": False,
        "runtime_config_hook_mutation_performed": False,
    }
    if decision == "successor_required":
        result["successor_packet"] = lifecycle.get("successor_packet")
        result["transition_receipt"] = lifecycle.get("transition_receipt")
    return result


def main() -> int:
    args = parse_args()
    result = bridge_decision(read_packet(args.input), utc_now(args.now), args.max_capture_age_hours)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
