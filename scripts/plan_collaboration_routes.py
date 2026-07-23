#!/usr/bin/env python3
"""Plan portable collaboration routes without dispatching work."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


CAPABILITY_TIERS = {"economy", "balanced", "frontier"}
REASONING_TIERS = {"low", "medium", "high"}
POLICY_PROFILES = {"economy", "normal", "performance", "low_limit"}
TASK_CLASSES = {"routine", "standard", "complex", "human_owned"}
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
BOUNDED_ROUTES = {
    "serial_current_session",
    "reuse_relevant_thread",
    "fresh_bounded_thread",
    "bounded_subagent",
    "batch_checkpoint",
    "hold_for_decision",
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
    if not isinstance(root.get("policy_sources", {}), dict):
        fail("policy_sources must be an object")
    return policy, work, role, runtime


def validate_policy(policy: dict[str, Any]) -> None:
    forbidden = nested_forbidden_keys(policy)
    if forbidden:
        fail(f"portable policy forbids provider/model identifiers: {', '.join(forbidden)}")
    allowed = policy.get("allowed_tiers", {})
    if not set(allowed.get("capability", [])).issubset(CAPABILITY_TIERS):
        fail("policy_set allowed capability tiers are invalid")
    if not set(allowed.get("reasoning", [])).issubset(REASONING_TIERS):
        fail("policy_set allowed reasoning tiers are invalid")


def resolve_policy(root: dict[str, Any], fallback_policy: dict[str, Any]) -> dict[str, Any]:
    sources = root.get("policy_sources", {})
    checks: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for source_name in ("current_work_unit_grant", "project", "personal"):
        record = sources.get(source_name)
        if record is None:
            checks.append({"source": source_name, "validity": "missing"})
            continue
        if not isinstance(record, dict):
            checks.append({"source": source_name, "validity": "invalid", "reason": "record is not an object"})
            continue
        validity = record.get("validity", "invalid")
        profile = record.get("profile")
        fingerprint = record.get("fingerprint")
        if validity != "valid" or profile not in POLICY_PROFILES or not isinstance(fingerprint, str) or not fingerprint:
            checks.append({"source": source_name, "validity": validity if validity in {"invalid", "drifted", "missing"} else "invalid", "reason": "profile or fingerprint is unavailable"})
            continue
        source_policy = record.get("policy_set", fallback_policy)
        if not isinstance(source_policy, dict):
            checks.append({"source": source_name, "validity": "invalid", "reason": "policy_set is not an object"})
            continue
        validate_policy(source_policy)
        checks.append({"source": source_name, "validity": "valid", "fingerprint": fingerprint})
        if selected is None:
            selected = {
                "profile": profile,
                "source": source_name,
                "validity": "valid",
                "fingerprint_or_unsaved_default": fingerprint,
                "policy_set": source_policy,
            }
    if selected is not None:
        selected["source_checks"] = checks
        return selected
    return {
        "profile": "normal",
        "source": "unsaved_normal_default",
        "validity": "unsaved_default",
        "fingerprint_or_unsaved_default": "unsaved-normal-default",
        "policy_set": fallback_policy,
        "source_checks": checks,
    }


def resolve_task_class(work: dict[str, Any]) -> tuple[str, dict[str, Any], str | None]:
    task_class = work.get("task_class", "standard")
    if task_class not in TASK_CLASSES:
        fail("work_unit.task_class is invalid")
    signals = work.get("material_signals", [])
    if not isinstance(signals, list) or not all(isinstance(signal, str) and signal for signal in signals):
        fail("work_unit.material_signals must be a list of strings")
    correction = work.get("task_class_correction")
    state = {"applied": False, "bounded_to_work_unit": True, "material_signals": signals[:3]}
    if correction is None:
        return task_class, state, None
    if not isinstance(correction, dict):
        fail("work_unit.task_class_correction must be an object")
    corrected_class = correction.get("task_class")
    if corrected_class not in TASK_CLASSES:
        return task_class, state, "Task-class correction is invalid; inspect and correct the current work-unit input"
    if correction.get("scope") != work["work_unit_id"] or correction.get("expires_after_work_unit") is not True:
        return task_class, state, "Task-class correction is not bounded to this work unit; Human decision required"
    state.update({"applied": True, "from": task_class, "to": corrected_class, "bounded_to_work_unit": True})
    return corrected_class, state, None


def profile_tier(policy: dict[str, Any], profile: str, task_class: str, signal_count: int, root: dict[str, Any]) -> tuple[str, str, dict[str, Any], str | None]:
    thresholds = policy.get("material_thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}
    economy_complex = thresholds.get("economy_complex", 2)
    performance_complex = thresholds.get("performance_complex", 1)
    reset = {"required": True, "persists": False, "after_work_unit": True, "mode": profile}
    if task_class == "human_owned":
        return "balanced", "medium", reset, "Human-owned task class requires a Human decision"
    if profile == "low_limit":
        return "economy", "low", reset, None
    if task_class == "routine":
        return "economy", "low", reset, None
    if task_class == "standard":
        return ("economy", "low", reset, None) if profile == "economy" else ("balanced", "medium", reset, None)
    if profile == "economy":
        return ("balanced", "medium", reset, None) if signal_count >= economy_complex else ("economy", "low", reset, None)
    if profile == "performance" and signal_count >= performance_complex:
        return "frontier", "high", reset, None
    attempt = root.get("attempt_state", {})
    if isinstance(attempt, dict) and attempt.get("outcome") == "escalation_candidate":
        if not attempt.get("evidence"):
            return "balanced", "medium", reset, "Escalation lacks explicit evidence"
        if not isinstance(attempt.get("escalation_count", 0), int) or attempt.get("escalation_count", 0) >= policy.get("automatic_budget", {}).get("max_escalations_per_work_unit", 0):
            return "balanced", "medium", reset, "Escalation budget exhausted; Human decision required"
        return "frontier", "high", reset, None
    return "balanced", "medium", reset, None


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


def candidate(
    candidate_id: str,
    route: str,
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
    if route not in BOUNDED_ROUTES:
        fail(f"unsupported bounded route: {route}")
    return {
        "candidate_id": candidate_id,
        "route": route,
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


def next_action_for(decision: str, setup_requested: bool, source_attention: list[dict[str, Any]], policy_resolution: dict[str, Any]) -> str:
    if setup_requested:
        return "Set up collaboration policy requires the later lifecycle write/readback flow; this planner will not write a record"
    if decision == "hold_for_decision":
        return "Resolve the listed decision before creating, reusing, or dispatching any context"
    if source_attention:
        if policy_resolution["source"] == "unsaved_normal_default":
            return "Inspect the invalid or drifted policy source; ordinary work may continue only with the labelled unsaved normal default"
        return "Inspect the invalid or drifted policy source; continue with the retained valid policy shown above"
    if decision == "serial_current_session":
        return "Continue serial work in the current session; record a compact callback at the work-unit checkpoint"
    if decision == "reuse_relevant_thread":
        return "Send only compact rehydration and callback instructions to the relevant durable thread after the normal dispatch gate"
    if decision == "fresh_bounded_thread":
        return "Create a fresh bounded thread only through a later approved dispatch step with compact rehydration"
    if decision == "bounded_subagent":
        return "Use a bounded subagent only through a later approved dispatch step with artifact-scoped instructions"
    if decision == "batch_checkpoint":
        return "Batch related evidence into one checkpoint before any further role dispatch"
    return "Hold for Architect review of the unsupported route"


def lifecycle_projection(decision: str, selected: dict[str, Any] | None, policy_resolution: dict[str, Any], task_class: str, next_action: str) -> dict[str, Any]:
    lifecycle_state = {
        "serial_current_session": "current_session_active",
        "reuse_relevant_thread": "reuse_candidate",
        "fresh_bounded_thread": "create_candidate",
        "bounded_subagent": "bounded_work_unit_candidate",
        "batch_checkpoint": "checkpoint_candidate",
        "hold_for_decision": "blocked_waiting_for_decision",
    }[decision]
    eligibility = {
        "create": decision == "fresh_bounded_thread",
        "reuse": decision == "reuse_relevant_thread",
        "compact_rehydrate": decision in {"reuse_relevant_thread", "fresh_bounded_thread", "bounded_subagent"},
        "callback": decision != "hold_for_decision",
        "cooldown": decision in {"serial_current_session", "batch_checkpoint"},
        "archive": decision == "batch_checkpoint",
    }
    return {
        "collaboration_operating_mode": {
            "effective_mode": policy_resolution["profile"],
            "temporary": policy_resolution["profile"] == "low_limit",
            "source": policy_resolution["source"],
        },
        "execution_context_lifecycle": {
            "state": lifecycle_state,
            "route": decision,
            "context_mode": selected.get("context_mode") if selected else "not_available",
            "eligible_actions": eligibility,
        },
        "bounded_work_unit_lifecycle": {
            "task_class": task_class,
            "state": "advisory_planned" if decision != "hold_for_decision" else "held",
            "mutation_scope": "none",
            "dispatch_scope": "none",
        },
        "next_action": next_action,
    }


def conversation_projection(policy_resolution: dict[str, Any], task_class: str, task_state: dict[str, Any], decision: str, selected: dict[str, Any] | None, candidates: list[dict[str, Any]], stops: list[str], tier: str, reasoning: str, setup_requested: bool) -> dict[str, Any]:
    source_attention = [check for check in policy_resolution["source_checks"] if check["validity"] in {"invalid", "drifted"}]
    observed_candidate = selected or next((item for item in candidates if item["topology"] != "serial"), None)
    runtime_mapping = observed_candidate.get("runtime_mapping") if observed_candidate else {"status": "not_available", "effective_configuration": "unknown", "enforcement": "not_available"}
    attention = list(stops)
    if source_attention:
        attention.append("One or more explicit policy sources are invalid or drifted; no persisted policy is assumed valid")
    if decision not in {"serial_current_session", "hold_for_decision"} and (runtime_mapping.get("status") != "supported" or runtime_mapping.get("effective_configuration") != "observed"):
        attention.append("Runtime projection is requested versus observable evidence; retained settings are not assumed")
    next_action = next_action_for(decision, setup_requested, source_attention, policy_resolution)
    emit = not (task_class == "routine" and decision == "serial_current_session" and not attention and not task_state["applied"])
    return {
        "effective_policy": {
            "profile": policy_resolution["profile"],
            "source": policy_resolution["source"],
            "validity": policy_resolution["validity"],
            "fingerprint_or_unsaved_default": policy_resolution["fingerprint_or_unsaved_default"],
        },
        "work_unit": {"task_class": task_class, "material_signals": task_state["material_signals"], "correction": task_state},
        "recommendation": {
            "route_decision": decision,
            "route": selected.get("route") if selected else decision,
            "role": selected.get("topology") if selected else "not_available",
            "topology": selected.get("topology") if selected else "not_available",
            "context_mode": selected.get("context_mode") if selected else "not_available",
            "abstract_tier": {"capability": tier, "reasoning": reasoning},
        },
        "lifecycle": lifecycle_projection(decision, selected, policy_resolution, task_class, next_action),
        "runtime_projection": {
            "requested": {"capability_tier": tier, "reasoning_tier": reasoning},
            "observable": {
                "status": runtime_mapping.get("status", "not_available"),
                "effective_configuration": runtime_mapping.get("effective_configuration", "unknown"),
                "enforcement": runtime_mapping.get("enforcement", "not_available"),
            },
        },
        "attention": attention,
        "evidence": {"policy_source_checks": policy_resolution["source_checks"], "json_is_secondary_debug": True},
        "next_action": next_action,
        "policy_setup_intent": {"requested": setup_requested, "apply_supported_now": False, "write_performed": False},
        "emit_compact_marker": emit,
        "recovery": {"writes_performed": False, "retains_prior_valid_policy": policy_resolution["source"] in {"current_work_unit_grant", "project", "personal"}},
    }


def plan(root: dict[str, Any]) -> dict[str, Any]:
    policy, work, role, runtime = validate_input(root)
    policy_resolution = resolve_policy(root, policy)
    policy = policy_resolution["policy_set"]
    task_class, task_state, correction_stop = resolve_task_class(work)
    override, override_stop = validate_override(root, work)
    tier, reasoning, reset, early_stop = profile_tier(policy, policy_resolution["profile"], task_class, len(task_state["material_signals"]), root)
    human_actions = work.get("human_owned_actions", [])
    if not isinstance(human_actions, list):
        fail("work_unit.human_owned_actions must be a list")
    if human_actions or work.get("requires_human_decision") is True or early_stop or override_stop or correction_stop:
        reason = early_stop or override_stop or correction_stop or "Human-owned action requires a Human decision"
        return result(root, policy_resolution, task_class, task_state, [], "hold_for_decision", None, [reason], reset, tier, reasoning, override)

    required_independence = role.get("independence_requirement", "none")
    envelope_required = work.get("requires_explicit_envelope", False) is True
    quality_floor = 3 if required_independence != "none" or role.get("specialization_available") is True else 2
    candidates: list[dict[str, Any]] = []
    serial_quality = 1 if required_independence != "none" else 2
    serial = candidate(
        "serial-current-session", "serial_current_session", "serial", "compact", "No material dispatch benefit is assumed by default.", "low", serial_quality,
        tier, reasoning, {"mechanism": "current_session", "status": "supported", "effective_configuration": "unknown", "enforcement": "not_required"},
        eligible=serial_quality >= quality_floor,
        failures=[] if serial_quality >= quality_floor else ["required independent context/evidence cannot be provided by serial work"],
    )
    candidates.append(serial)

    continuity = role.get("continuity_value", "none")
    relevance = role.get("context_relevance", "low")
    if continuity in {"medium", "high"} and relevance in {"medium", "high"}:
        mapping, failures = route_runtime(runtime, "durable_thread", envelope_required)
        candidates.append(candidate("durable-relevant-role-context", "reuse_relevant_thread", "durable_thread", "filtered_history", "Relevant durable continuity can reduce rehydration cost.", "low", 3, tier, reasoning, mapping, not failures, failures))

    needs_fresh = role.get("specialization_available") is True or required_independence != "none" or relevance == "low"
    if needs_fresh:
        mapping, failures = route_runtime(runtime, "fresh_thread", envelope_required)
        quality = 3 if role.get("specialization_available") is True or required_independence != "none" else 2
        candidates.append(candidate("fresh-specialized-or-independent", "fresh_bounded_thread", "fresh_thread", "fresh", "Fresh context avoids unrelated retained history and supports specialization or independence.", "medium", quality, tier, reasoning, mapping, not failures and quality >= quality_floor, failures + ([] if quality >= quality_floor else ["quality floor not met"])))

    if work.get("safe_parallelism") is True:
        mapping, failures = route_runtime(runtime, "subagent", envelope_required)
        candidates.append(candidate("bounded-subagent", "bounded_subagent", "subagent", "artifact_reference", "Safe disjoint side work may reduce critical-path latency.", "medium", 2, tier, reasoning, mapping, not failures and 2 >= quality_floor, failures + ([] if 2 >= quality_floor else ["quality floor not met"])))

    if work.get("batch_checkpoint_safe") is True:
        mapping, failures = route_runtime(runtime, "batch", False)
        candidates.append(candidate("batch-checkpoint", "batch_checkpoint", "batch", "artifact_reference", "Related findings can be reviewed together without losing exact-head safety.", "low", 2, tier, reasoning, mapping, not failures and 2 >= quality_floor, failures + ([] if 2 >= quality_floor else ["quality floor not met"])))

    candidates = candidates[:4]
    eligible = [item for item in candidates if item["eligible"]]
    if not eligible:
        return result(root, policy_resolution, task_class, task_state, candidates, "hold_for_decision", None, ["No route meets the authority, evidence, and runtime quality floor."], reset, tier, reasoning, override)
    material_benefit = any((role.get("specialization_available") is True, continuity in {"medium", "high"} and relevance in {"medium", "high"}, required_independence != "none", work.get("safe_parallelism") is True, work.get("batch_checkpoint_safe") is True))
    selection_pool = [item for item in eligible if item["route"] != "serial_current_session"] if material_benefit else eligible
    if not selection_pool:
        selection_pool = eligible
    selected = sorted(selection_pool, key=lambda item: (COST_RANK[item["expected_cost_band"]], -{"low": 1, "medium": 2, "high": 3}[item["expected_quality_band"]], item["candidate_id"]))[0]
    decision = selected["route"] if material_benefit and selected["route"] != "serial_current_session" else "serial_current_session"
    if decision == "serial_current_session":
        selected = next(item for item in eligible if item["topology"] == "serial")
    return result(root, policy_resolution, task_class, task_state, candidates, decision, selected, [], reset, tier, reasoning, override)


def result(root: dict[str, Any], policy_resolution: dict[str, Any], task_class: str, task_state: dict[str, Any], candidates: list[dict[str, Any]], decision: str, selected: dict[str, Any] | None, stops: list[str], reset: dict[str, Any], tier: str, reasoning: str, override: dict[str, Any]) -> dict[str, Any]:
    runtime = root["runtime_capabilities"]
    confidence = "low" if any(item.get("runtime_mapping", {}).get("effective_configuration") == "unknown" for item in candidates) else "medium"
    return {
        "policy_set": root["policy_set"],
        "work_unit": root["work_unit"],
        "role_context": root["role_context"],
        "runtime_capabilities": {"observed_at": runtime.get("observed_at", "not_available"), "mechanisms": runtime.get("mechanisms", {})},
        "runtime_limitations": runtime_limitations(runtime),
        "policy_resolution": {key: value for key, value in policy_resolution.items() if key != "policy_set"},
        "conversation_projection": conversation_projection(policy_resolution, task_class, task_state, decision, selected, candidates, stops, tier, reasoning, root.get("policy_setup_requested") is True),
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
    if decision == "hold_for_decision":
        explanation.append("No eligible advisory route clears the required authority/evidence/runtime floor.")
    elif decision == "serial_current_session":
        explanation.append("Serial is selected because no material dispatch benefit clears its handoff and context cost.")
    elif selected:
        explanation.append(f"Selected {selected['route']} via {selected['candidate_id']} as the least-cost eligible route that clears the quality floor.")
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
