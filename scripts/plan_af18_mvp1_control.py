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
ROLE_LIFECYCLE_VERSION = "af18-role-lifecycle-v1"
NORMAL_WORK_RESOURCES = {
    "profile": "normal",
    "model": "gpt-5.6-terra",
    "reasoning": "medium",
    "root_budget_tokens": 120000,
    "max_age_hours": 24,
    "max_turns": 12,
}
ROUTE_PERMISSIONS = {
    "isolated_execution": "allow",
    "interactive_execution": "successor_required",
    "serial_execution": "allow",
    "external_execution": "hold_required",
    "privileged_execution": "hold_required",
}
RESOURCE_PROVENANCE = {"observed", "estimated", "unavailable"}
ATTENTION_CATEGORIES = {
    "hdc_approval": "Human decision or approval is required.",
    "risk_change": "Material risk changed or needs explicit owner attention.",
    "privacy_boundary": "Privacy boundary is affected or needs review.",
    "external_side_effect": "External side effect is possible or requested.",
    "model_escalation": "Model or reasoning escalation needs Human approval.",
    "context_budget_strategy_change": "Context or budget strategy changed materially.",
    "retry_claim_anomaly": "Retry or claim anomaly is beyond policy.",
    "acceptance_evidence_conflict": "Acceptance and evidence conflict.",
    "phase_completion": "Phase completed and needs next-owner acknowledgement.",
    "stale_no_owner_work": "Work is stale or lacks a current owner.",
}
SUPPRESSED_EVENT_CATEGORIES = {
    "execution_run",
    "dispatch_claim",
    "transition_receipt",
    "resource_observation",
    "successor_retry_mechanic",
    "ordinary_receipt",
}
INCIDENT_RULES = {
    "stale_no_owner": ("hold", "Coordinator", "assign an owner or request a Human decision", False),
    "evidence_conflict": ("quarantine", "Coordinator", "review the durable evidence anchor", False),
    "budget_breach": ("stop", "Human", "preserve the receipt and request an explicit budget decision", False),
    "unavailable_observation": ("hold", "Coordinator", "obtain a trusted observation without inference", False),
    "duplicate_dispatch": ("reject_allocation", "Coordinator", "retain the canonical active Work", False),
    "successor_failure": ("hold", "current_owner", "attempt the single bounded recovery", True),
    "escalation_failure": ("hold", "Human", "request explicit model or reasoning approval", False),
}
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
    parser.add_argument(
        "--mode",
        choices=("preflight", "readout", "explain", "work-summary", "attention-summary", "role-lifecycle", "incident"),
        default="preflight",
    )
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
        "human_facing_views": ["active_policy", "work_explain", "work_summary", "attention_summary"],
        "human_attention_policy": {
            "attention_categories": ATTENTION_CATEGORIES,
            "suppressed_default_event_categories": sorted(SUPPRESSED_EVENT_CATEGORIES),
            "ordinary_control_plane_receipts_default_human_attention": False,
        },
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
    for field in (
        "work_id",
        "issue",
        "issue_anchor",
        "role",
        "objective",
        "stage",
        "phase",
        "root_budget_tokens",
        "remaining_budget_tokens",
        "durable_anchors",
        "stop_conditions",
    ):
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
    validate_issue_work_anchor(work, stops)


def validate_issue_work_anchor(work: dict[str, Any], stops: list[str]) -> None:
    issue_anchor = work.get("issue_anchor") if isinstance(work.get("issue_anchor"), dict) else {}
    if not issue_anchor:
        stops.append("missing_issue_anchor")
        return
    if issue_anchor.get("issue") != work.get("issue"):
        stops.append("work_issue_anchor_mismatch")
    validate_durable_issue_anchor(issue_anchor, "issue_anchor", stops)
    if work.get("cross_issue_work") is True or work.get("multiple_issue_work") is True:
        anchors = work.get("additional_issue_anchors")
        if not isinstance(anchors, list) or not anchors:
            stops.append("missing_cross_issue_durable_anchors")
        else:
            for index, anchor in enumerate(anchors):
                if not isinstance(anchor, dict) or not anchor:
                    stops.append("malformed_additional_issue_anchor")
                    continue
                validate_durable_issue_anchor(anchor, f"additional_issue_anchor_{index}", stops)


def validate_durable_issue_anchor(anchor: dict[str, Any], prefix: str, stops: list[str]) -> None:
    if not isinstance(anchor.get("issue"), int) or anchor.get("issue", 0) <= 0:
        stops.append(f"missing_{prefix}_issue")
    for field in ("durable_anchor", "scope", "risk", "acceptance", "human_gates"):
        if missing(anchor.get(field)):
            stops.append(f"missing_{prefix}_{field}")


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
        "issue_anchor": work.get("issue_anchor"),
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


def role_lifecycle_projection(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    request = packet.get("role_lifecycle")
    stops: list[str] = []
    if not isinstance(request, dict):
        request = {}
        stops.append("missing_role_lifecycle")
    action = request.get("action")
    conversation = request.get("conversation") if isinstance(request.get("conversation"), dict) else {}
    for field in ("role_conversation_id", "project_id", "role", "work_id", "issue", "durable_anchor", "root_budget_tokens"):
        if missing(conversation.get(field)):
            stops.append(f"missing_role_conversation_{field}")
    for field, expected in NORMAL_WORK_RESOURCES.items():
        if conversation.get(field) != expected:
            stops.append(f"role_conversation_{field}_does_not_match_normal_work")
    if find_forbidden(request):
        stops.append("privacy_exposure")

    result: dict[str, Any] = {
        "projection_type": "RoleLifecyclePlan",
        "lifecycle_version": ROLE_LIFECYCLE_VERSION,
        "action": action,
        "role_conversation_id": conversation.get("role_conversation_id"),
        "logical_identity": {
            "project_id": conversation.get("project_id"),
            "role": conversation.get("role"),
        },
        "work_id": conversation.get("work_id"),
        "issue": conversation.get("issue"),
        "durable_anchor": conversation.get("durable_anchor"),
        "root_budget_tokens": conversation.get("root_budget_tokens"),
        "operation_allowed": False,
        "materialization_required": False,
        "legacy_disposition": "not_legacy",
        "predecessor_state": conversation.get("state", "current"),
        "successor_state": "not_requested",
        "one_recovery_remaining": False,
        "stop_conditions": [],
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
    }

    if action == "onboard_fresh":
        onboarding_key = request.get("onboarding_key")
        if missing(onboarding_key):
            stops.append("missing_onboarding_key")
        existing = request.get("existing_conversations")
        if not isinstance(existing, list):
            stops.append("invalid_existing_conversations")
            existing = []
        match = next(
            (
                item
                for item in existing
                if isinstance(item, dict)
                and item.get("project_id") == conversation.get("project_id")
                and item.get("role") == conversation.get("role")
                and item.get("onboarding_key") == onboarding_key
            ),
            None,
        )
        result["materialization_required"] = match is None and not stops
        result["idempotent_reuse"] = match is not None
        result["effective_role_conversation_id"] = (
            match.get("role_conversation_id") if isinstance(match, dict) else conversation.get("role_conversation_id")
        )
        result["operation_allowed"] = not stops
    elif action == "adopt_legacy":
        if conversation.get("legacy") is not True:
            stops.append("adoption_requires_legacy_conversation")
        if request.get("explicit_adoption") is not True:
            result["legacy_disposition"] = "historical_reference"
            stops.append("legacy_adoption_not_explicit")
        elif request.get("compactness_preflight") != "passed":
            result["legacy_disposition"] = "historical_reference"
            stops.append("legacy_adoption_compactness_not_proven")
        else:
            result["legacy_disposition"] = "adoption_planned"
            result["operation_allowed"] = not stops
    elif action in {"request_successor", "recover_successor"}:
        successor = request.get("successor") if isinstance(request.get("successor"), dict) else {}
        recovery_attempts = request.get("recovery_attempts", 0)
        if type(recovery_attempts) is not int or recovery_attempts not in {0, 1}:
            stops.append("invalid_recovery_attempts")
            recovery_attempts = 1
        for field in (
            "context_window_id",
            "compact_capsule",
            "issue",
            "durable_anchor",
            "work_id",
            "root_budget_tokens",
            "remaining_budget_tokens",
            "ready",
            "max_age_hours",
            "max_turns",
        ):
            if missing(successor.get(field)):
                stops.append(f"missing_successor_{field}")
        capsule = successor.get("compact_capsule")
        if not isinstance(capsule, dict) or not capsule.get("evidence_refs") or find_forbidden(capsule):
            stops.append("invalid_or_private_successor_capsule")
        for field in ("issue", "durable_anchor", "work_id", "root_budget_tokens"):
            if successor.get(field) != conversation.get(field):
                stops.append(f"successor_{field}_continuity_mismatch")
        for field in ("max_age_hours", "max_turns"):
            if successor.get(field) != NORMAL_WORK_RESOURCES[field]:
                stops.append(f"successor_{field}_does_not_match_normal_work")
        remaining = successor.get("remaining_budget_tokens")
        if not isinstance(remaining, int) or remaining < 0 or remaining > conversation.get("root_budget_tokens", -1):
            stops.append("successor_remaining_budget_invalid")
        if successor.get("ready") is not True:
            stops.append("successor_not_ready")
        if stops:
            result["predecessor_state"] = "current"
            result["successor_state"] = "failed"
            result["one_recovery_remaining"] = recovery_attempts < 1
            result["recovery_action"] = (
                "prepare one corrected compact successor packet" if recovery_attempts < 1 else None
            )
        else:
            result["predecessor_state"] = "supersede_planned"
            result["successor_state"] = "ready"
            result["operation_allowed"] = True
            result["successor_packet"] = {
                "context_window_id": successor.get("context_window_id"),
                "compact_capsule": capsule,
                "issue": successor.get("issue"),
                "durable_anchor": successor.get("durable_anchor"),
                "work_id": successor.get("work_id"),
                "root_budget_tokens": successor.get("root_budget_tokens"),
                "remaining_budget_tokens": successor.get("remaining_budget_tokens"),
                "max_age_hours": successor.get("max_age_hours"),
                "max_turns": successor.get("max_turns"),
            }
    else:
        stops.append("unknown_role_lifecycle_action")

    result["stop_conditions"] = sorted(set(stops))
    result["decision"] = "ready" if result["operation_allowed"] and not stops else "hold_required"
    result["human_attention_required"] = bool(stops)
    result["reason"] = (
        "Role lifecycle dry-run is ready."
        if not stops
        else f"Role lifecycle held: {sorted(set(stops))[0]}."
    )
    return result


def incident_projection(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    incident = packet.get("incident")
    stops: list[str] = []
    if not isinstance(incident, dict):
        incident = {}
        stops.append("missing_incident")
    category = incident.get("category")
    rule = INCIDENT_RULES.get(category)
    if rule is None:
        stops.append("unknown_incident_category")
        rule = ("hold", "Coordinator", "provide a supported incident category", False)
    required = ("event_time", "sequence", "work_id", "issue", "durable_anchor", "root_budget_tokens", "remaining_budget_tokens")
    for field in required:
        if missing(incident.get(field)):
            stops.append(f"missing_incident_{field}")
    try:
        event_time = cost_policy.parse_timestamp(incident.get("event_time"), "incident.event_time")
    except (TypeError, ValueError):
        event_time = None
        stops.append("invalid_incident_event_time")
    if event_time is not None and event_time > now:
        stops.append("incident_event_from_future")
    if not isinstance(incident.get("sequence"), int) or incident.get("sequence", 0) < 1:
        stops.append("invalid_incident_sequence")
    root_budget = incident.get("root_budget_tokens")
    remaining = incident.get("remaining_budget_tokens")
    if not isinstance(root_budget, int) or root_budget <= 0 or not isinstance(remaining, int) or remaining < 0:
        stops.append("invalid_incident_budget")
    if isinstance(root_budget, int) and isinstance(remaining, int) and remaining > root_budget:
        stops.append("incident_budget_continuity_breach")
    if category == "unavailable_observation":
        observation = incident.get("observation") if isinstance(incident.get("observation"), dict) else {}
        if observation.get("provenance") != "unavailable" or "value" in observation:
            stops.append("unavailable_observation_must_not_supply_value")
    if category == "successor_failure" and incident.get("recovery_attempts") not in (0, 1):
        stops.append("successor_recovery_limit_invalid")
    if category == "escalation_failure":
        if incident.get("requested_model") != incident.get("effective_model"):
            stops.append("silent_model_change_forbidden")
        if incident.get("requested_reasoning") != incident.get("effective_reasoning"):
            stops.append("silent_reasoning_change_forbidden")
    forbidden = find_forbidden(incident)
    if forbidden:
        stops.append("privacy_exposure")

    action, owner, corrective_action, recovery_allowed = rule
    if category == "successor_failure" and incident.get("recovery_attempts") == 1:
        recovery_allowed = False
    receipt = {
        "receipt_type": "IncidentReceipt",
        "category": category,
        "state": action,
        "event_time": incident.get("event_time"),
        "sequence": incident.get("sequence"),
        "work_id": incident.get("work_id"),
        "issue": incident.get("issue"),
        "durable_anchor": incident.get("durable_anchor"),
        "root_budget_tokens": root_budget,
        "remaining_budget_tokens": remaining,
        "owner": incident.get("owner") or owner,
        "corrective_action": corrective_action,
        "capability": incident.get("capability"),
        "provenance": incident.get("observation", {}).get("provenance")
        if isinstance(incident.get("observation"), dict)
        else None,
    }
    attention = {
        "projection_type": "AttentionSummary",
        "human_attention_required": True,
        "category": category,
        "reason": compact_reason(incident.get("reason"), corrective_action),
        "owner": owner,
        "evidence_ref": incident.get("evidence_ref"),
        "read_only": True,
    }
    return {
        "projection_type": "IncidentPlan",
        "valid": not stops,
        "decision": action if not stops else "hold",
        "incident_receipt": receipt,
        "attention_summary": attention,
        "predecessor_state": "current" if category == "successor_failure" else "not_applicable",
        "successor_allowed": category == "successor_failure" and recovery_allowed and not stops,
        "recovery_attempts_remaining": 1 if category == "successor_failure" and recovery_allowed else 0,
        "stop_conditions": sorted(set(stops)),
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def compact_reason(raw: Any, fallback: str) -> str:
    if isinstance(raw, str) and raw.strip():
        words = raw.strip().split()
        return " ".join(words[:16])
    return fallback


def corrective_reason(stops: list[str]) -> str:
    if not stops:
        return "No policy-material attention event."
    return f"Invalid summary input: {sorted(set(stops))[0]}. Provide compact corrected evidence."


def attention_summary_projection(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    del now
    stops: list[str] = []
    warnings: list[str] = []
    events = packet.get("attention_events")
    if events is None:
        events = []
    if not isinstance(events, list):
        stops.append("invalid_attention_events")
        events = []
    items: list[dict[str, Any]] = []
    suppressed: list[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            stops.append("invalid_attention_event")
            continue
        category = event.get("category")
        if category in SUPPRESSED_EVENT_CATEGORIES:
            suppressed.append(str(category))
            continue
        if category not in ATTENTION_CATEGORIES:
            stops.append("unknown_attention_category")
            continue
        reason = compact_reason(event.get("reason"), ATTENTION_CATEGORIES[category])
        items.append(
            {
                "category": category,
                "reason": reason,
                "evidence_ref": event.get("evidence_ref"),
                "requires_human": True,
                "index": index,
            }
        )
    forbidden = find_forbidden(packet.get("attention_events", []))
    if forbidden:
        stops.append("privacy_exposure")
        warnings.append("forbidden_attention_paths:" + ",".join(forbidden))
    if stops:
        items.append(
            {
                "category": "invalid_attention_input",
                "reason": "Attention input is invalid; hold for compact corrected evidence.",
                "requires_human": True,
            }
        )
    return {
        "projection_type": "AttentionSummary",
        "control_version": CONTROL_VERSION,
        "valid": not stops,
        "human_attention_required": bool(items),
        "reason": compact_reason(items[0]["reason"], "Human attention is required.") if items else "No policy-material attention event.",
        "items": items,
        "suppressed_event_categories": sorted(set(suppressed)),
        "stop_conditions": sorted(set(stops)),
        "warnings": warnings,
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def work_summary_projection(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    work = packet.get("work") if isinstance(packet.get("work"), dict) else {}
    stops: list[str] = []
    validate_issue_work_anchor(work, stops)
    for field in ("work_id", "objective", "stage", "role"):
        if missing(work.get(field)):
            stops.append(f"missing_work_summary_{field}")
    attention = attention_summary_projection(packet, now)
    if not attention["valid"]:
        stops.append("invalid_attention_summary")
    forbidden = find_forbidden(work)
    warnings: list[str] = []
    if forbidden:
        stops.append("privacy_exposure")
        warnings.append("forbidden_work_summary_paths:" + ",".join(forbidden))
    return {
        "projection_type": "WorkSummary",
        "control_version": CONTROL_VERSION,
        "valid": not stops,
        "issue_anchor": work.get("issue_anchor"),
        "work_id": work.get("work_id"),
        "objective": work.get("objective"),
        "stage": work.get("stage"),
        "current_owner": work.get("current_owner", work.get("role")),
        "material_decisions": work.get("material_decisions", []),
        "accepted_evidence_refs": work.get("accepted_evidence_refs", []),
        "material_risk_or_blocker": work.get("material_risk_or_blocker"),
        "next_action": work.get("next_action"),
        "human_attention_required": attention["human_attention_required"] or bool(stops),
        "human_attention_reason": attention["reason"] if attention["human_attention_required"] else corrective_reason(stops),
        "default_human_ux_excludes": [
            "ExecutionRun",
            "DispatchClaim",
            "TransitionReceipt",
            "raw_token_context_observations",
            "successor_retry_mechanics",
        ],
        "stop_conditions": sorted(set(stops)),
        "warnings": warnings,
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
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
        "human_attention_required": decision == "hold_required",
        "human_attention_reason": "Hold requires Human or Coordinator attention." if decision == "hold_required" else "No policy-material attention event.",
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
    attention = attention_summary_projection(packet, now)
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
        "human_attention_required": preflight["human_attention_required"] or attention["human_attention_required"],
        "human_attention_reason": preflight["human_attention_reason"]
        if preflight["human_attention_required"]
        else attention["reason"],
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
    elif args.mode == "work-summary":
        result = work_summary_projection(packet, now)
    elif args.mode == "attention-summary":
        result = attention_summary_projection(packet, now)
    elif args.mode == "role-lifecycle":
        result = role_lifecycle_projection(packet, now)
    elif args.mode == "incident":
        result = incident_projection(packet, now)
    else:
        result = plan_preflight(packet, now)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
