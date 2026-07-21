#!/usr/bin/env python3
"""Plan portable collaboration routes without dispatching work."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


CAPABILITY_TIERS = {"economy", "balanced", "frontier"}
REASONING_TIERS = {"low", "medium", "high"}
RUNTIME_STATUSES = {"supported", "unsupported", "unknown", "degraded", "not_available"}
TOPOLOGY_MECHANISMS = {
    "durable_thread": "send_message_to_thread",
    "fresh_thread": "create_thread",
    "subagent": "spawn_agent",
    "fork": "fork_thread",
    "team": "team",
    "batch": "worktree_batch",
    "portable": "portable_prompt",
}
FORBIDDEN_POLICY_KEYS = {"provider", "provider_slug", "model", "model_slug"}
COST_RANK = {"low": 1, "medium": 2, "high": 3}


def fail(message: str) -> None:
    raise ValueError(message)


def load_input(path: str) -> dict[str, Any]:
    value = json.loads(open(path, encoding="utf-8").read())
    if not isinstance(value, dict):
        fail("planner input must be a JSON object")
    return value


def nested_forbidden_keys(value: Any, path: str = "") -> list[str]:
    if not isinstance(value, dict):
        return []
    findings: list[str] = []
    for key, child in value.items():
        child_path = f"{path}.{key}" if path else key
        if key in FORBIDDEN_POLICY_KEYS:
            findings.append(child_path)
        findings.extend(nested_forbidden_keys(child, child_path))
    return findings


def require_object(root: dict[str, Any], name: str) -> dict[str, Any]:
    value = root.get(name)
    if not isinstance(value, dict):
        fail(f"missing object: {name}")
    return value


def validate_input(root: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    policy = require_object(root, "policy_set")
    work = require_object(root, "work_unit")
    role = require_object(root, "role_context")
    runtime = require_object(root, "runtime_capabilities")
    if policy.get("schema_version") != 1:
        fail("policy_set.schema_version must be 1")
    forbidden = nested_forbidden_keys(policy)
    if forbidden:
        fail(f"portable policy forbids provider/model identifiers: {', '.join(forbidden)}")
    allowed = policy.get("allowed_tiers", {})
    if not set(allowed.get("capability", [])).issubset(CAPABILITY_TIERS):
        fail("policy_set allowed capability tiers are invalid")
    if not set(allowed.get("reasoning", [])).issubset(REASONING_TIERS):
        fail("policy_set allowed reasoning tiers are invalid")
    if not work.get("work_unit_id") or not work.get("purpose"):
        fail("work_unit requires work_unit_id and purpose")
    if not isinstance(work.get("stop_conditions", []), list):
        fail("work_unit.stop_conditions must be a list")
    if role.get("independence_requirement", "none") not in {"none", "separate_context", "separate_evidence"}:
        fail("role_context.independence_requirement is invalid")
    if not isinstance(runtime.get("mechanisms"), dict):
        fail("runtime_capabilities.mechanisms must be an object")
    return policy, work, role, runtime


def mechanism(runtime: dict[str, Any], name: str) -> dict[str, Any]:
    value = runtime.get("mechanisms", {}).get(name, {})
    if not isinstance(value, dict):
        value = {}
    status = value.get("status", "not_available")
    if status not in RUNTIME_STATUSES:
        status = "unknown"
    return {
        "name": name,
        "status": status,
        "supports_explicit_envelope": value.get("supports_explicit_envelope", False) is True,
        "effective_configuration": value.get("effective_configuration", "unknown"),
    }


def escalation(policy: dict[str, Any], root: dict[str, Any]) -> tuple[str, str, dict[str, Any], str | None]:
    attempt = root.get("attempt_state", {})
    if not isinstance(attempt, dict):
        attempt = {}
    state = attempt.get("outcome", "planned")
    count = attempt.get("escalation_count", 0)
    max_count = policy.get("automatic_budget", {}).get("max_escalations_per_work_unit", 0)
    if state == "human_owned":
        return "balanced", "medium", {"required": True, "persists": False}, "Human-owned action requires a Human decision"
    if state == "escalation_candidate":
        if not attempt.get("evidence"):
            return "balanced", "medium", {"required": True, "persists": False}, "Escalation lacks explicit evidence"
        if not isinstance(count, int) or count >= max_count:
            return "balanced", "medium", {"required": True, "persists": False}, "Escalation budget exhausted; Human decision required"
        return "frontier", "high", {"required": True, "persists": False, "after_work_unit": True}, None
    if state == "downgrade_candidate":
        return "economy", "low", {"required": True, "persists": False, "after_work_unit": True}, None
    return "balanced", "medium", {"required": True, "persists": False, "after_work_unit": True}, None


def candidate(
    candidate_id: str,
    topology: str,
    context_mode: str,
    reason: str,
    cost: str,
    quality: int,
    tier: str,
    reasoning: str,
    runtime_mapping: dict[str, Any],
    eligible: bool = True,
    failures: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "topology": topology,
        "context_mode": context_mode,
        "reason": reason,
        "eligible": eligible,
        "ineligible_reasons": failures or [],
        "expected_cost_band": cost,
        "expected_quality_band": {1: "low", 2: "medium", 3: "high"}[quality],
        "expected_evidence_strength": {1: "low", 2: "medium", 3: "high"}[quality],
        "requested_capability_tier": tier,
        "requested_reasoning_tier": reasoning,
        "runtime_mapping": runtime_mapping,
        "confidence": "low" if runtime_mapping.get("effective_configuration") != "observed" else "medium",
    }


def route_runtime(runtime: dict[str, Any], topology: str, envelope_required: bool) -> tuple[dict[str, Any], list[str]]:
    if topology == "serial":
        return {"mechanism": "current_session", "status": "supported", "effective_configuration": "unknown", "enforcement": "not_required"}, []
    found = mechanism(runtime, TOPOLOGY_MECHANISMS[topology])
    failures: list[str] = []
    if found["status"] != "supported":
        failures.append(f"runtime mechanism {found['name']} is {found['status']}")
    if topology in {"fork"}:
        failures.append("fork is non-enforcing under the current capability evidence")
    if envelope_required and not found["supports_explicit_envelope"]:
        failures.append("explicit runtime envelope required but unsupported")
    found["enforcement"] = "requested_explicit_envelope" if found["supports_explicit_envelope"] else "enforcement_not_available"
    if found["effective_configuration"] not in {"observed", "unknown", "not_available"}:
        found["effective_configuration"] = "unknown"
    return found, failures


def runtime_limitations(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    limitations: list[dict[str, Any]] = []
    for mechanism_name, posture in (
        ("fork_thread", "non_enforcing"),
        ("heartbeat", "non_enforcing"),
        ("hook", "unsupported"),
        ("custom_agent", "unsupported"),
    ):
        found = mechanism(runtime, mechanism_name)
        limitations.append(
            {
                "mechanism": mechanism_name,
                "runtime_status": found["status"],
                "enforcement": posture,
                "effective_configuration": found["effective_configuration"],
            }
        )
    return limitations


def validate_override(root: dict[str, Any], work: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    override = root.get("override_grant")
    if override is None:
        return {"active": False, "scope": "not_available", "expires_after_work_unit": True, "reset_required": True}, None
    if not isinstance(override, dict):
        fail("override_grant must be an object")
    normalized = {
        "active": override.get("active", False) is True,
        "scope": override.get("scope", "not_available"),
        "expires_after_work_unit": override.get("expires_after_work_unit", True) is True,
        "reset_required": override.get("reset_required", True) is True,
    }
    if not normalized["active"]:
        return normalized, None
    if normalized["scope"] != work["work_unit_id"]:
        return normalized, "Active override grant scope does not match this work unit"
    if not normalized["expires_after_work_unit"] or not normalized["reset_required"]:
        return normalized, "Active override grant must expire and reset after this work unit"
    return normalized, None


def plan(root: dict[str, Any]) -> dict[str, Any]:
    policy, work, role, runtime = validate_input(root)
    override, override_stop = validate_override(root, work)
    tier, reasoning, reset, early_stop = escalation(policy, root)
    human_actions = work.get("human_owned_actions", [])
    if not isinstance(human_actions, list):
        fail("work_unit.human_owned_actions must be a list")
    if human_actions or work.get("requires_human_decision") is True or early_stop or override_stop:
        reason = early_stop or override_stop or "Human-owned action requires a Human decision"
        return result(root, [], "human_stop", None, [reason], reset, tier, reasoning, override)

    required_independence = role.get("independence_requirement", "none")
    envelope_required = work.get("requires_explicit_envelope", False) is True
    quality_floor = 3 if required_independence != "none" or role.get("specialization_available") is True else 2
    candidates: list[dict[str, Any]] = []
    serial_quality = 1 if required_independence != "none" else 2
    serial = candidate(
        "serial-current-session", "serial", "compact", "No material dispatch benefit is assumed by default.", "low", serial_quality,
        tier, reasoning, {"mechanism": "current_session", "status": "supported", "effective_configuration": "unknown", "enforcement": "not_required"},
        eligible=serial_quality >= quality_floor,
        failures=[] if serial_quality >= quality_floor else ["required independent context/evidence cannot be provided by serial work"],
    )
    candidates.append(serial)

    continuity = role.get("continuity_value", "none")
    relevance = role.get("context_relevance", "low")
    if continuity in {"medium", "high"} and relevance in {"medium", "high"}:
        mapping, failures = route_runtime(runtime, "durable_thread", envelope_required)
        candidates.append(candidate("durable-relevant-role-context", "durable_thread", "filtered_history", "Relevant durable continuity can reduce rehydration cost.", "low", 3, tier, reasoning, mapping, not failures, failures))

    needs_fresh = role.get("specialization_available") is True or required_independence != "none" or relevance == "low"
    if needs_fresh:
        mapping, failures = route_runtime(runtime, "fresh_thread", envelope_required)
        quality = 3 if role.get("specialization_available") is True or required_independence != "none" else 2
        candidates.append(candidate("fresh-specialized-or-independent", "fresh_thread", "fresh", "Fresh context avoids unrelated retained history and supports specialization or independence.", "medium", quality, tier, reasoning, mapping, not failures and quality >= quality_floor, failures + ([] if quality >= quality_floor else ["quality floor not met"])))

    if work.get("safe_parallelism") is True:
        mapping, failures = route_runtime(runtime, "subagent", envelope_required)
        candidates.append(candidate("bounded-subagent", "subagent", "artifact_reference", "Safe disjoint side work may reduce critical-path latency.", "medium", 2, tier, reasoning, mapping, not failures and 2 >= quality_floor, failures + ([] if 2 >= quality_floor else ["quality floor not met"])))

    for topology, reason in (("fork", "Fork route is recorded as non-enforcing."), ("portable", "Portable fallback cannot enforce runtime settings.")):
        mapping, failures = route_runtime(runtime, topology, envelope_required)
        candidates.append(candidate(f"{topology}-negative-control", topology, "full_continuity" if topology == "fork" else "artifact_reference", reason, "medium", 1, tier, reasoning, mapping, False, failures or ["unsupported advisory fallback below quality floor"]))

    candidates = candidates[:4]
    eligible = [item for item in candidates if item["eligible"]]
    if not eligible:
        return result(root, candidates, "human_stop", None, ["No route meets the authority, evidence, and runtime quality floor."], reset, tier, reasoning, override)
    material_benefit = any((role.get("specialization_available") is True, continuity in {"medium", "high"} and relevance in {"medium", "high"}, required_independence != "none", work.get("safe_parallelism") is True))
    selected = sorted(eligible, key=lambda item: (COST_RANK[item["expected_cost_band"]], -{"low": 1, "medium": 2, "high": 3}[item["expected_quality_band"]], item["candidate_id"]))[0]
    decision = "dispatch_advisory" if material_benefit and selected["topology"] != "serial" else "no_dispatch"
    if decision == "no_dispatch":
        selected = next(item for item in eligible if item["topology"] == "serial")
    return result(root, candidates, decision, selected, [], reset, tier, reasoning, override)


def result(root: dict[str, Any], candidates: list[dict[str, Any]], decision: str, selected: dict[str, Any] | None, stops: list[str], reset: dict[str, Any], tier: str, reasoning: str, override: dict[str, Any]) -> dict[str, Any]:
    runtime = root["runtime_capabilities"]
    confidence = "low" if any(item.get("runtime_mapping", {}).get("effective_configuration") == "unknown" for item in candidates) else "medium"
    return {
        "policy_set": root["policy_set"],
        "work_unit": root["work_unit"],
        "role_context": root["role_context"],
        "runtime_capabilities": {"observed_at": runtime.get("observed_at", "not_available"), "mechanisms": runtime.get("mechanisms", {})},
        "runtime_limitations": runtime_limitations(runtime),
        "route_candidates": candidates,
        "dispatch_plan": {
            "route_decision": decision,
            "selected_candidate": selected,
            "explanation": pareto_explanation(candidates, selected, decision),
            "runtime_mapping": selected.get("runtime_mapping") if selected else {"enforcement": "not_available"},
            "requested_capability_tier": tier,
            "requested_reasoning_tier": reasoning,
            "reset": reset,
            "stop_conditions": stops + root["work_unit"].get("stop_conditions", []),
            "confidence": confidence,
        },
        "override_grant": override,
        "evaluation_record": {
            "work_unit_id": root["work_unit"]["work_unit_id"],
            "outcome": "not_executed",
            "estimate_band": selected.get("expected_cost_band") if selected else "not_available",
            "confidence": confidence,
            "quality_guardrails": ["authority", "verification", "independence", "runtime_capability"],
            "prior_records_considered": len(root.get("evaluation_records", [])) if isinstance(root.get("evaluation_records", []), list) else "not_available",
        },
        "mutation_performed": False,
        "dispatch_performed": False,
        "enforcement_posture": root["policy_set"].get("enforcement", {}).get("mode", "advisory"),
    }


def pareto_explanation(candidates: list[dict[str, Any]], selected: dict[str, Any] | None, decision: str) -> list[str]:
    eligible = [item for item in candidates if item["eligible"]]
    explanation = [f"candidate_set={len(candidates)}; eligible={len(eligible)}; limit=4"]
    if decision == "human_stop":
        explanation.append("No eligible advisory route clears the required authority/evidence/runtime floor.")
    elif decision == "no_dispatch":
        explanation.append("Serial is selected because no material dispatch benefit clears its handoff and context cost.")
    elif selected:
        explanation.append(f"Selected {selected['candidate_id']} as the least-cost eligible route that clears the quality floor.")
    return explanation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", required=True, help="Portable route-planning input JSON.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. This is the default output format.")
    args = parser.parse_args()
    try:
        output = plan(load_input(args.input_json))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"route_planner_error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
