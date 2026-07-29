#!/usr/bin/env python3
"""Focused tests for AF18 MVP-1 lifecycle control-plane planning."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "scripts" / "plan_af18_mvp1_control.py"
spec = importlib.util.spec_from_file_location("plan_af18_mvp1_control", PLANNER)
planner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(planner)

NOW = dt.datetime(2026, 7, 29, 4, 0, tzinfo=dt.timezone.utc)


def packet(**overrides):
    base = {
        "work": {
            "work_id": "af18-450",
            "issue": 450,
            "issue_anchor": {
                "issue": 450,
                "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/450",
                "scope": "mvp1-control-plane",
                "risk": "high",
                "acceptance": "portable read-only control-plane proof",
                "human_gates": ["model_escalation", "external_side_effect"],
            },
            "role": "Implementer",
            "objective": "Implement AF18 MVP-1 control-plane contract",
            "stage": "needs:reviewer",
            "phase": "mvp1-control-plane",
            "current_owner": "Implementer",
            "root_budget_tokens": 7000,
            "remaining_budget_tokens": 6200,
            "durable_anchors": ["https://github.com/farmerhunter/agent-foundry/issues/450"],
            "stop_conditions": ["hold_on_missing_budget", "hold_on_stale_context", "hold_on_duplicate_dispatch"],
            "material_decisions": ["Option A approved for bounded MVP"],
            "accepted_evidence_refs": ["https://github.com/farmerhunter/agent-foundry/pull/453"],
            "material_risk_or_blocker": None,
            "next_action": "review PR #453",
        },
        "execution_run": {
            "run_id": "run-450-a",
            "work_id": "af18-450",
            "role": "Implementer",
            "state": "active",
            "context": {
                "source_timestamp": "2026-07-29T03:30:00Z",
                "threshold_band": "implementer_small_scoped_implementation",
                "resource_observations": {
                    "context_tokens": {
                        "provenance": "estimated",
                        "tokens": 5500,
                        "source": "compact_coordinator_packet",
                    }
                },
            },
            "model": {"name": "gpt-5.5", "reasoning": "medium"},
        },
        "dispatch_claim": {
            "idempotency_key": "issue-450-implementer-mvp1-control-v1",
            "work_id": "af18-450",
            "role": "Implementer",
            "decision_boundary": "issue-450-mvp1",
            "transition_semantics": "initial_control_plane_preflight",
            "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/450",
            "adapter_metadata": {"native_binding": "codex"},
        },
        "existing_dispatch_claims": [],
        "active_runs": [],
        "attention_events": [],
        "requested_route": "isolated_execution",
        "adapter_metadata": {"runtime_binding": "codex"},
    }
    base.update(overrides)
    return base


def plan(value):
    return planner.plan_preflight(value, NOW)


def expect(name, condition, detail):
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")


def forbidden_paths(value):
    return planner.find_forbidden(value)


def main() -> int:
    allowed = plan(packet())
    expect("allow-route", allowed["decision"] == "allow", allowed)
    expect("allow-policy-source", allowed["effective_control_snapshot"]["policy_source"] == "scripts/plan_collaboration_routes.py", allowed)
    expect(
        "allow-resource-provenance-visible",
        allowed["effective_control_snapshot"]["resource_observation"]["context_tokens"]["provenance"] == "estimated",
        allowed,
    )
    expect("allow-no-mutation", allowed["mutation_performed"] is False and allowed["dispatch_performed"] is False, allowed)
    expect("allow-no-human-attention", allowed["human_attention_required"] is False, allowed)

    issue_anchor_mismatch = packet(work={**packet()["work"], "issue_anchor": {**packet()["work"]["issue_anchor"], "issue": 449}})
    issue_anchor_mismatch_result = plan(issue_anchor_mismatch)
    expect("issue-anchor-mismatch-holds", "work_issue_anchor_mismatch" in issue_anchor_mismatch_result["stop_conditions"], issue_anchor_mismatch_result)

    cross_issue_without_anchor = packet(work={**packet()["work"], "cross_issue_work": True})
    cross_issue_result = plan(cross_issue_without_anchor)
    expect("cross-issue-requires-anchor", "missing_cross_issue_durable_anchors" in cross_issue_result["stop_conditions"], cross_issue_result)

    missing_budget = packet(work={**packet()["work"], "root_budget_tokens": None})
    missing_budget_result = plan(missing_budget)
    expect("missing-budget-holds", missing_budget_result["decision"] == "hold_required", missing_budget_result)
    expect("missing-budget-stop", "missing_budget" in missing_budget_result["stop_conditions"], missing_budget_result)

    stale = packet()
    stale["execution_run"] = {
        **stale["execution_run"],
        "context": {**stale["execution_run"]["context"], "source_timestamp": "2026-07-26T00:00:00Z"},
    }
    stale_result = plan(stale)
    expect("stale-context-holds", "stale_context" in stale_result["stop_conditions"], stale_result)

    oversized = packet()
    oversized["execution_run"] = {
        **oversized["execution_run"],
        "context": {
            **oversized["execution_run"]["context"],
            "resource_observations": {
                "context_tokens": {
                    "provenance": "observed",
                    "tokens": 9000,
                    "source": "runtime_control_surface",
                }
            },
        },
    }
    oversized_result = plan(oversized)
    expect("oversized-context-holds", "oversized_context" in oversized_result["stop_conditions"], oversized_result)

    missing_resource_observation = packet()
    missing_resource_observation["execution_run"] = {
        **missing_resource_observation["execution_run"],
        "context": {
            key: value
            for key, value in missing_resource_observation["execution_run"]["context"].items()
            if key != "resource_observations"
        },
    }
    missing_resource_result = plan(missing_resource_observation)
    expect("missing-resource-holds", "missing_resource_observation" in missing_resource_result["stop_conditions"], missing_resource_result)

    unavailable_resource = packet()
    unavailable_resource["execution_run"] = {
        **unavailable_resource["execution_run"],
        "context": {
            **unavailable_resource["execution_run"]["context"],
            "resource_observations": {"context_tokens": {"provenance": "unavailable", "source": "adapter_not_supported"}},
        },
    }
    unavailable_result = plan(unavailable_resource)
    expect("unavailable-resource-holds", "resource_measurement_unavailable" in unavailable_result["stop_conditions"], unavailable_result)

    missing_token_measurement = packet()
    missing_token_measurement["execution_run"] = {
        **missing_token_measurement["execution_run"],
        "context": {
            **missing_token_measurement["execution_run"]["context"],
            "resource_observations": {
                "context_tokens": {
                    "provenance": "observed",
                    "source": "runtime_control_surface",
                }
            },
        },
    }
    missing_token_result = plan(missing_token_measurement)
    expect(
        "missing-token-measurement-not-zero",
        "missing_context_token_measurement" in missing_token_result["stop_conditions"],
        missing_token_result,
    )

    unavailable_lower_capability = packet()
    unavailable_lower_capability["execution_run"] = {
        **unavailable_lower_capability["execution_run"],
        "context": {
            **unavailable_lower_capability["execution_run"]["context"],
            "resource_observations": {
                "context_tokens": {
                    "provenance": "unavailable",
                    "source": "adapter_not_supported",
                    "lower_capability_policy": "serial_execution_only",
                }
            },
        },
    }
    lower_capability_result = plan(unavailable_lower_capability)
    expect(
        "unavailable-lower-capability-not-zero",
        "resource_measurement_lower_capability_required" in lower_capability_result["stop_conditions"],
        lower_capability_result,
    )

    escalation = packet()
    escalation["execution_run"] = {**escalation["execution_run"], "model": {"name": "gpt-5.6", "reasoning": "high"}}
    escalation_result = plan(escalation)
    expect("model-ceiling-holds", "model_escalation_requires_human_approval" in escalation_result["stop_conditions"], escalation_result)
    expect("reasoning-ceiling-holds", "reasoning_escalation_requires_human_approval" in escalation_result["stop_conditions"], escalation_result)

    duplicate_claim = packet(
        existing_dispatch_claims=[
            {
                "idempotency_key": "issue-450-implementer-mvp1-control-v1",
                "work_id": "af18-450",
                "role": "Implementer",
                "decision_boundary": "issue-450-mvp1",
                "transition_semantics": "initial_control_plane_preflight",
            }
        ]
    )
    duplicate_claim_result = plan(duplicate_claim)
    expect("duplicate-claim-holds", "duplicate_dispatch_claim" in duplicate_claim_result["stop_conditions"], duplicate_claim_result)

    semantic_duplicate = packet(
        dispatch_claim={**packet()["dispatch_claim"], "idempotency_key": "changed-idempotency-key"},
        existing_dispatch_claims=[
            {
                "idempotency_key": "original-idempotency-key",
                "work_id": "af18-450",
                "role": "Implementer",
                "decision_boundary": "issue-450-mvp1",
                "transition_semantics": "initial_control_plane_preflight",
            }
        ],
    )
    semantic_duplicate_result = plan(semantic_duplicate)
    expect("semantic-duplicate-claim-holds", "duplicate_dispatch_claim" in semantic_duplicate_result["stop_conditions"], semantic_duplicate_result)

    boundary_duplicate_without_transition = packet(
        dispatch_claim={**packet()["dispatch_claim"], "idempotency_key": "changed-idempotency-key"},
        existing_dispatch_claims=[
            {
                "idempotency_key": "legacy-idempotency-key",
                "work_id": "af18-450",
                "role": "Implementer",
                "decision_boundary": "issue-450-mvp1",
            }
        ],
    )
    boundary_duplicate_result = plan(boundary_duplicate_without_transition)
    expect("boundary-duplicate-without-transition-holds", "duplicate_dispatch_claim" in boundary_duplicate_result["stop_conditions"], boundary_duplicate_result)

    active_run = packet(active_runs=[{"run_id": "run-450-other", "work_id": "af18-450", "role": "Implementer", "state": "active"}])
    active_run_result = plan(active_run)
    expect("one-active-run-holds", "duplicate_active_run" in active_run_result["stop_conditions"], active_run_result)

    interactive = plan(packet(requested_route="interactive_execution"))
    expect("interactive-successor-required", interactive["decision"] == "successor_required", interactive)
    expect("successor-keeps-work-id", interactive["successor_packet"]["work_id"] == "af18-450", interactive)
    expect("successor-keeps-issue-anchor", interactive["successor_packet"]["issue_anchor"]["issue"] == 450, interactive)
    expect("successor-keeps-root-budget", interactive["successor_packet"]["root_budget_tokens"] == 7000, interactive)
    expect("successor-keeps-remaining-budget", interactive["successor_packet"]["remaining_budget_tokens"] == 6200, interactive)
    expect("successor-privacy-safe", forbidden_paths(interactive["successor_packet"]) == [], interactive)

    serial = plan(packet(requested_route="serial_execution"))
    expect("serial-route-allowed", serial["decision"] == "allow", serial)

    external = plan(packet(requested_route="external_execution"))
    expect("external-holds", external["decision"] == "hold_required", external)
    expect("external-held-route-visible", external["held_route"] == "external_execution", external)

    readout = planner.active_policy_readout()
    expect("codex-route-not-core-canonical", "bounded_subagent" not in readout["route_permissions"], readout)
    expect("codex-visible-route-not-core-canonical", "visible_interactive" not in readout["route_permissions"], readout)
    expect("readout-source-visible", readout["policy_source"] == "scripts/plan_collaboration_routes.py", readout)
    expect("readout-resource-policy-visible", readout["resource_observation_policy"]["missing_counts_as_zero"] is False, readout)
    expect("readout-global-ceiling", readout["global_hard_context_ceiling"] == 12000, readout)
    expect("readout-effective-rule-visible", "effective_context_ceiling_rule" in readout, readout)
    expect("readout-band-visible", readout["threshold_bands"]["implementer_small_scoped_implementation"]["max_context_tokens"] == 8000, readout)
    expect("readout-no-dispatch", readout["mutation_performed"] is False and readout["dispatch_performed"] is False, readout)
    expect("readout-human-views-visible", "attention_summary" in readout["human_facing_views"], readout)
    expect(
        "ordinary-receipts-not-default-attention",
        readout["human_attention_policy"]["ordinary_control_plane_receipts_default_human_attention"] is False,
        readout,
    )
    expect("readout-privacy-safe", forbidden_paths(readout) == [], readout)

    explanation = planner.explain_work_policy(packet(), NOW)
    expect("explain-allow", explanation["decision"] == "allow", explanation)
    expect("explain-budget-visible", explanation["root_budget_tokens"] == 7000 and explanation["remaining_budget_tokens"] == 6200, explanation)
    expect("explain-attention-reason", explanation["human_attention_reason"] == "No policy-material attention event.", explanation)

    interactive_explanation = planner.explain_work_policy(packet(requested_route="interactive_execution"), NOW)
    expect("explain-interactive-successor", interactive_explanation["decision"] == "successor_required", interactive_explanation)
    expect("explain-interactive-route", interactive_explanation["selected_route"] == "interactive_execution", interactive_explanation)

    hold_explanation = planner.explain_work_policy(oversized, NOW)
    expect("explain-hold", hold_explanation["decision"] == "hold_required", hold_explanation)
    expect("explain-recovery-action", hold_explanation["one_recovery_action"] is not None, hold_explanation)

    unknown = plan(packet(requested_route="unclassified_route"))
    expect("unknown-classification-holds", unknown["decision"] == "hold_required", unknown)
    expect("unknown-classification-stop", "unknown_route_classification" in unknown["stop_conditions"], unknown)

    prompt_body = packet(prompt="private prompt body")
    prompt_body_result = plan(prompt_body)
    expect("prompt-body-holds", "privacy_exposure" in prompt_body_result["stop_conditions"], prompt_body_result)

    ordinary_receipt = planner.attention_summary_projection(
        packet(attention_events=[{"category": "transition_receipt", "reason": "ordinary run receipt"}]),
        NOW,
    )
    expect("ordinary-receipt-suppressed", ordinary_receipt["human_attention_required"] is False, ordinary_receipt)
    expect("ordinary-receipt-category-suppressed", "transition_receipt" in ordinary_receipt["suppressed_event_categories"], ordinary_receipt)

    attention_categories = {
        "hdc_approval": "Human approval needed",
        "risk_change": "Risk changed",
        "privacy_boundary": "Privacy boundary",
        "external_side_effect": "External side effect",
        "model_escalation": "Model escalation",
        "context_budget_strategy_change": "Budget strategy changed",
        "retry_claim_anomaly": "Claim anomaly",
        "acceptance_evidence_conflict": "Evidence conflict",
        "phase_completion": "Phase complete",
        "stale_no_owner_work": "No owner",
    }
    for category, reason in attention_categories.items():
        attention = planner.attention_summary_projection(
            packet(attention_events=[{"category": category, "reason": reason, "evidence_ref": "issue-450"}]),
            NOW,
        )
        expect(f"attention-{category}-required", attention["human_attention_required"] is True, attention)
        expect(f"attention-{category}-reason", attention["items"][0]["reason"] == reason, attention)

    work_summary = planner.work_summary_projection(packet(), NOW)
    expect("work-summary-valid", work_summary["valid"] is True, work_summary)
    expect("work-summary-fields", work_summary["objective"] == "Implement AF18 MVP-1 control-plane contract", work_summary)
    expect("work-summary-no-attention", work_summary["human_attention_required"] is False, work_summary)
    expect("work-summary-default-excludes-runs", "ExecutionRun" in work_summary["default_human_ux_excludes"], work_summary)

    work_summary_attention = planner.work_summary_projection(
        packet(attention_events=[{"category": "phase_completion", "reason": "Phase complete"}]),
        NOW,
    )
    expect("work-summary-attention-required", work_summary_attention["human_attention_required"] is True, work_summary_attention)
    expect("work-summary-attention-reason", work_summary_attention["human_attention_reason"] == "Phase complete", work_summary_attention)

    private_work_summary = planner.work_summary_projection(
        packet(work={**packet()["work"], "prompt": "private prompt body"}),
        NOW,
    )
    expect("work-summary-privacy-fail-closed", "privacy_exposure" in private_work_summary["stop_conditions"], private_work_summary)

    invalid_attention = planner.attention_summary_projection(packet(attention_events=[{"category": "unknown_policy_event"}]), NOW)
    expect("unknown-attention-fails-closed", invalid_attention["valid"] is False, invalid_attention)
    expect("unknown-attention-stop", "unknown_attention_category" in invalid_attention["stop_conditions"], invalid_attention)

    invalid_summary = planner.work_summary_projection(packet(work={**packet()["work"], "objective": ""}), NOW)
    expect("invalid-summary-fails-closed", invalid_summary["valid"] is False, invalid_summary)
    expect("invalid-summary-stop", "missing_work_summary_objective" in invalid_summary["stop_conditions"], invalid_summary)

    print("af18 mvp1 control-plane tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
