#!/usr/bin/env python3
"""Focused tests for AF18 MVP-2 runtime-owned observation bridge."""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts" / "plan_af18_mvp2_observation_bridge.py"
spec = importlib.util.spec_from_file_location("plan_af18_mvp2_observation_bridge", BRIDGE)
bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bridge)

NOW = dt.datetime(2026, 7, 29, 8, 30, tzinfo=dt.timezone.utc)


def capture(**overrides):
    base = {
        "schema_version": 1,
        "record_id": "capture-451",
        "captured_at": "2026-07-29T08:20:00Z",
        "producer": {
            "producer_type": "runtime_control_surface",
            "producer_id": "codex-control-surface",
            "runtime_id": "codex",
            "capture_session_id": "coord-session-451",
            "runtime_owned": True,
            "caller_supplied": False,
        },
        "runtime_attestation": {"producer_bound": True, "capture_nonce": "nonce-451"},
        "route": {
            "category": "spawn",
            "support_status": "supported",
            "requested_envelope": {"model": "gpt-5.5", "reasoning": "medium"},
            "effective_envelope": {"status": "accepted", "model": "gpt-5.5", "reasoning": "medium"},
            "category_evidence": {
                "child_owner": "Coordinator",
                "isolation_boundary": "coordination_window",
                "inherited_context_policy": "compact_issue_packet",
                "budget_anchor": "issue-451",
            },
        },
        "evidence_metadata": {
            "route_id": "coordinator_internal_route",
            "target_id": "coord-window-451-a",
            "cursor": "cursor-451",
            "budget_anchor": "issue-451",
            "external_cost_possible": False,
            "duplicate_owner_detected": False,
            "evidence_ref": "https://github.com/farmerhunter/agent-foundry/issues/451#runtime-owned-observation",
        },
        "privacy": {"contains_prompt_body": False, "redaction": "metadata_only"},
        "stop_conditions": [],
    }
    base.update(overrides)
    return base


def telemetry(total=3200, tool_bytes=300):
    return {
        "input_tokens": {"availability": "observed", "value": total, "source": "runtime_usage"},
        "cached_input_tokens": {"availability": "observed", "value": 0, "source": "runtime_usage"},
        "output_tokens": {"availability": "observed", "value": 0, "source": "runtime_usage"},
        "reasoning_tokens": {"availability": "observed", "value": 0, "source": "runtime_usage"},
        "tool_output_bytes": {"availability": "observed", "value": tool_bytes, "source": "runtime_usage"},
        "route": "interactive_execution",
        "transition_reason": "after compact durable readback",
        "cumulative_work_totals": {
            "input_tokens": total,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "tool_output_bytes": tool_bytes,
        },
    }


def snapshot(**overrides):
    base = {
        "source": "#442 low_limit containment",
        "version": "af18-451-option-a-literal-v1",
        "band": "low_limit_experiment",
        "label": "low_limit_experiment",
        "coordinator_lifecycle_model": "CoordinatorSession -> CoordinationWindow -> coordination operation",
        "threshold_band": "coordinator_routing_status_readback",
        "max_context_tokens": 4000,
        "max_age_hours": 12,
        "root_budget_tokens": 7000,
        "window_id": "coord-window-451-a",
        "measurement_unavailable_policy": "hold_required",
        "normal_threshold_breach": "successor_required",
        "allowed_route": "isolated_execution",
        "stop_conditions": ["hold_on_missing_observation", "hold_on_external_route", "hold_on_privilege_escalation"],
    }
    base.update(overrides)
    return base


def packet(**overrides):
    base = {
        "effective_control_snapshot": snapshot(),
        "coordinator_event_type": "after_compact_durable_readback",
        "observed_at": "2026-07-29T08:20:00Z",
        "evidence_ref": "https://github.com/farmerhunter/agent-foundry/issues/451#runtime-owned-observation",
        "runtime_capture": capture(),
        "runtime_telemetry": telemetry(),
        "work": {
            "work_id": "af18-451",
            "issue": 451,
            "issue_anchor": {
                "issue": 451,
                "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/451",
                "scope": "mvp2-runtime-owned-observation-bridge",
                "risk": "high",
                "acceptance": "runtime-owned low_limit_experiment observation bridge",
                "human_gates": ["external_side_effect", "runtime_config_mutation", "model_escalation"],
            },
            "role": "Coordinator",
            "objective": "Implement AF18 MVP-2 runtime-owned observation bridge",
            "stage": "needs:reviewer",
            "phase": "mvp2-observation-bridge",
            "current_owner": "Implementer",
            "root_budget_tokens": 7000,
            "remaining_budget_tokens": 6600,
            "durable_anchors": ["https://github.com/farmerhunter/agent-foundry/issues/451"],
            "stop_conditions": ["hold_on_missing_observation", "hold_on_privacy_boundary"],
            "material_decisions": ["#451 Option A approved"],
            "accepted_evidence_refs": [],
            "material_risk_or_blocker": None,
            "next_action": "review MVP-2 bridge PR",
        },
        "execution_run": {
            "run_id": "run-451-a",
            "work_id": "af18-451",
            "role": "Coordinator",
            "state": "active",
            "context": {"source_timestamp": "2026-07-29T08:20:00Z"},
            "model": {"name": "gpt-5.5", "reasoning": "medium"},
        },
        "dispatch_claim": {
            "idempotency_key": "issue-451-coordinator-mvp2-bridge-v1",
            "work_id": "af18-451",
            "role": "Coordinator",
            "decision_boundary": "issue-451-mvp2",
            "transition_semantics": "runtime_owned_observation_bridge",
            "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/451",
            "adapter_metadata": {"native_binding": "codex"},
        },
        "existing_dispatch_claims": [],
        "active_runs": [],
        "attention_events": [],
        "native_session_id": "codex-session-metadata-only",
    }
    base.update(overrides)
    return base


def decide(value):
    return bridge.bridge_decision(value, NOW)


def expect(name, condition, detail):
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")


def main() -> int:
    allowed = decide(packet())
    expect("literal-low-limit-label", allowed["experiment_label"] == "low_limit_experiment", allowed)
    expect("runtime-owned-observation", allowed["runtime_owned_observation"] is True, allowed)
    expect("no-external-action", allowed["external_action_performed"] is False, allowed)
    expect("no-runtime-config-mutation", allowed["runtime_config_hook_mutation_performed"] is False, allowed)
    expect("bounded-event", allowed["bounded_meaningful_event"] is True, allowed)
    expect("raw-receipts-suppressed", allowed["raw_receipt_default_suppressed"] is True, allowed)
    expect("ordinary-attention-suppressed", allowed["attention_summary"]["human_attention_required"] is False, allowed)
    expect("work-summary-emitted", allowed["work_summary"]["projection_type"] == "WorkSummary", allowed)
    expect("attention-summary-emitted", allowed["attention_summary"]["projection_type"] == "AttentionSummary", allowed)
    expect("native-id-adapter-metadata", allowed["lifecycle_evaluator"]["effective_control_snapshot"]["threshold"]["band"] == "coordinator_routing_status_readback", allowed)
    expect("within-limit-continues", allowed["decision"] == "allow", allowed)

    missing_model_packet = copy.deepcopy(packet())
    del missing_model_packet["execution_run"]["model"]
    missing_model = decide(missing_model_packet)
    expect("missing-run-model-fails-closed", missing_model["decision"] == "hold_required", missing_model)
    expect("missing-run-model-stop", "missing_execution_run_model" in missing_model["stop_conditions"], missing_model)
    expect("unknown-model-stop", "missing_or_unknown_model" in missing_model["stop_conditions"], missing_model)

    mismatched_work_id_packet = copy.deepcopy(packet())
    mismatched_work_id_packet["execution_run"]["work_id"] = "af18-451-other"
    mismatched_work_id = decide(mismatched_work_id_packet)
    expect("mismatched-run-work-id-fails-closed", mismatched_work_id["decision"] == "hold_required", mismatched_work_id)
    expect("mismatched-run-work-id-stop", "run_work_role_mismatch" in mismatched_work_id["stop_conditions"], mismatched_work_id)

    mismatched_role_packet = copy.deepcopy(packet())
    mismatched_role_packet["execution_run"]["role"] = "Reviewer"
    mismatched_role = decide(mismatched_role_packet)
    expect("mismatched-run-role-fails-closed", mismatched_role["decision"] == "hold_required", mismatched_role)
    expect("mismatched-run-role-stop", "run_work_role_mismatch" in mismatched_role["stop_conditions"], mismatched_role)

    missing_work_role_packet = copy.deepcopy(packet())
    del missing_work_role_packet["work"]["role"]
    missing_work_role = decide(missing_work_role_packet)
    expect("missing-work-role-fails-closed", missing_work_role["decision"] == "hold_required", missing_work_role)
    expect("missing-work-role-stop", "missing_work_role" in missing_work_role["stop_conditions"], missing_work_role)
    expect("missing-work-role-mismatch-stop", "run_work_role_mismatch" in missing_work_role["stop_conditions"], missing_work_role)

    breached = decide(packet(runtime_telemetry=telemetry(total=4100)))
    expect("threshold-breach-successor", breached["decision"] == "successor_required", breached)
    expect("successor-root-budget-preserved", breached["successor_packet"]["root_budget_tokens"] == 7000, breached)
    expect("successor-remaining-budget-preserved", breached["successor_packet"]["remaining_budget_tokens"] == 6600, breached)
    expect("successor-labelled", breached["experiment_label"] == "low_limit_experiment", breached)
    expect("attention-material-successor", breached["attention_summary"]["human_attention_required"] is True, breached)

    caller_only = decide(packet(runtime_capture=capture(producer={**capture()["producer"], "runtime_owned": False, "caller_supplied": True})))
    expect("caller-only-fails-closed", caller_only["decision"] == "hold_required", caller_only)
    expect("caller-only-stop", "caller_only_evidence" in caller_only["stop_conditions"], caller_only)

    forged = decide(packet(runtime_capture=capture(runtime_attestation={"producer_bound": False, "capture_nonce": "nonce-451"})))
    expect("forged-fails-closed", forged["decision"] == "hold_required", forged)
    expect("forged-stop", "forged_evidence" in forged["stop_conditions"], forged)

    stale = decide(packet(runtime_capture=capture(captured_at="2026-07-28T08:00:00Z")))
    expect("stale-fails-closed", stale["decision"] == "hold_required", stale)
    expect("stale-stop", "stale_evidence" in stale["stop_conditions"], stale)

    missing_capture = decide(packet(runtime_capture={}))
    expect("missing-capture-fails-closed", missing_capture["decision"] == "hold_required", missing_capture)
    expect("missing-capture-stop", "missing_runtime_capture" in missing_capture["stop_conditions"], missing_capture)

    unavailable = telemetry()
    unavailable["input_tokens"] = {"availability": "unavailable", "source": "runtime_usage_unavailable"}
    unavailable_result = decide(packet(runtime_telemetry=unavailable))
    expect("unavailable-fails-closed", unavailable_result["decision"] == "hold_required", unavailable_result)
    expect("unavailable-not-zero", unavailable_result["telemetry"]["total_context_tokens"]["value"] is None, unavailable_result)
    expect("unavailable-stop", "input_tokens_unavailable" in unavailable_result["stop_conditions"], unavailable_result)

    privacy = decide(packet(prompt="private prompt body"))
    expect("privacy-fails-closed", privacy["decision"] == "hold_required", privacy)
    expect("privacy-stop", "privacy_exposure" in privacy["stop_conditions"], privacy)

    unbounded_event = decide(packet(coordinator_event_type="continuous_polling_probe"))
    expect("unbounded-event-holds", unbounded_event["decision"] == "hold_required", unbounded_event)
    expect("unbounded-event-stop", "unbounded_or_unknown_lifecycle_event" in unbounded_event["stop_conditions"], unbounded_event)

    bad_snapshot = decide(packet(effective_control_snapshot=snapshot(band="normal", label="normal")))
    expect("normal-policy-not-invented", bad_snapshot["decision"] == "hold_required", bad_snapshot)
    expect("literal-snapshot-stop", "literal_snapshot_band_mismatch" in bad_snapshot["stop_conditions"], bad_snapshot)

    material = decide(packet(attention_events=[{"category": "privacy_boundary", "reason": "Privacy boundary", "evidence_ref": "issue-451"}]))
    expect("material-category-attention", material["attention_summary"]["human_attention_required"] is True, material)
    expect("material-category-reason", material["attention_summary"]["items"][0]["category"] == "privacy_boundary", material)

    print("af18 mvp2 observation bridge tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
