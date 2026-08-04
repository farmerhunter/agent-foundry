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
HELPER = ROOT / "scripts" / "github_collaboration_helper.py"
helper_spec = importlib.util.spec_from_file_location("github_collaboration_helper", HELPER)
helper = importlib.util.module_from_spec(helper_spec)
assert helper_spec.loader is not None
helper_spec.loader.exec_module(helper)

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

    cross_issue_malformed_anchor = packet(work={**packet()["work"], "cross_issue_work": True, "additional_issue_anchors": [{}]})
    cross_issue_malformed_result = plan(cross_issue_malformed_anchor)
    expect(
        "cross-issue-malformed-anchor-holds",
        "malformed_additional_issue_anchor" in cross_issue_malformed_result["stop_conditions"],
        cross_issue_malformed_result,
    )

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
    expect(
        "invalid-summary-corrective-reason",
        invalid_summary["human_attention_reason"] != "No policy-material attention event."
        and invalid_summary["human_attention_reason"].startswith("Invalid summary input:"),
        invalid_summary,
    )

    conversation = {
        "role_conversation_id": "role-conversation-459",
        "project_id": "project-459",
        "role": "Implementer",
        "state": "current",
        "work_id": "af18-459-460",
        "issue": 459,
        "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/459",
        "profile": "normal",
        "model": "gpt-5.6-terra",
        "reasoning": "medium",
        "root_budget_tokens": 120000,
        "max_age_hours": 24,
        "max_turns": 12,
    }
    lifecycle = {
        "role_lifecycle": {
            "action": "onboard_fresh",
            "onboarding_key": "project-459-implementer",
            "conversation": conversation,
            "existing_conversations": [],
        }
    }
    fresh = planner.role_lifecycle_projection(lifecycle, NOW)
    expect("fresh-onboarding-ready", fresh["decision"] == "ready" and fresh["materialization_required"] is True, fresh)
    repeated = planner.role_lifecycle_projection(
        {"role_lifecycle": {**lifecycle["role_lifecycle"], "existing_conversations": [{"project_id": "project-459", "role": "Implementer", "onboarding_key": "project-459-implementer", "role_conversation_id": "existing-role-conversation"}]}},
        NOW,
    )
    expect("fresh-onboarding-idempotent", repeated["idempotent_reuse"] is True and repeated["materialization_required"] is False, repeated)
    legacy = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "adopt_legacy", "conversation": {**conversation, "legacy": True}, "explicit_adoption": False}},
        NOW,
    )
    expect("legacy-default-historical-reference", legacy["legacy_disposition"] == "historical_reference" and legacy["operation_allowed"] is False, legacy)
    adopted = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "adopt_legacy", "conversation": {**conversation, "legacy": True}, "explicit_adoption": True, "compactness_preflight": "passed"}},
        NOW,
    )
    expect("legacy-explicit-adoption", adopted["decision"] == "ready" and adopted["legacy_disposition"] == "adoption_planned", adopted)
    successor = {
        "context_window_id": "window-459-b",
        "compact_capsule": {"evidence_refs": ["https://github.com/farmerhunter/agent-foundry/issues/460"]},
        "issue": 459,
        "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/459",
        "work_id": "af18-459-460",
        "root_budget_tokens": 120000,
        "remaining_budget_tokens": 110000,
        "max_age_hours": 24,
        "max_turns": 12,
        "ready": True,
    }
    successor_ready = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "request_successor", "conversation": conversation, "successor": successor, "recovery_attempts": 0}},
        NOW,
    )
    expect("successor-readiness-before-supersede", successor_ready["decision"] == "ready" and successor_ready["predecessor_state"] == "supersede_planned", successor_ready)
    expect("successor-anchor-budget-continuity", successor_ready["successor_packet"]["root_budget_tokens"] == 120000 and successor_ready["successor_packet"]["durable_anchor"] == conversation["durable_anchor"], successor_ready)
    failed_successor = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "request_successor", "conversation": conversation, "successor": {**successor, "compact_capsule": {}, "ready": False}, "recovery_attempts": 0}},
        NOW,
    )
    expect("successor-failure-keeps-predecessor", failed_successor["predecessor_state"] == "current" and failed_successor["one_recovery_remaining"] is True, failed_successor)
    exhausted_successor = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "recover_successor", "conversation": conversation, "successor": {**successor, "ready": False}, "recovery_attempts": 1}},
        NOW,
    )
    expect("successor-only-one-recovery", exhausted_successor["one_recovery_remaining"] is False, exhausted_successor)
    second_recovery = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "recover_successor", "conversation": conversation, "successor": successor, "recovery_attempts": 2}},
        NOW,
    )
    expect(
        "second-recovery-fails-closed",
        second_recovery["decision"] == "hold_required"
        and second_recovery["operation_allowed"] is False
        and second_recovery["predecessor_state"] == "current"
        and "successor_packet" not in second_recovery
        and second_recovery["root_budget_tokens"] == 120000
        and "invalid_recovery_attempts" in second_recovery["stop_conditions"],
        second_recovery,
    )
    boolean_recovery = planner.role_lifecycle_projection(
        {"role_lifecycle": {"action": "recover_successor", "conversation": conversation, "successor": successor, "recovery_attempts": True}},
        NOW,
    )
    expect("boolean-recovery-fails-closed", "invalid_recovery_attempts" in boolean_recovery["stop_conditions"], boolean_recovery)

    incident_base = {
        "event_time": "2026-07-29T03:40:00Z",
        "sequence": 1,
        "work_id": "af18-459-460",
        "issue": 459,
        "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/459",
        "root_budget_tokens": 120000,
        "remaining_budget_tokens": 110000,
        "evidence_ref": "issue-460",
    }
    expected_incidents = {
        "stale_no_owner": "hold",
        "evidence_conflict": "quarantine",
        "budget_breach": "stop",
        "unavailable_observation": "hold",
        "duplicate_dispatch": "reject_allocation",
        "successor_failure": "hold",
        "escalation_failure": "hold",
    }
    for category, decision in expected_incidents.items():
        incident = {**incident_base, "category": category}
        if category == "unavailable_observation":
            incident["observation"] = {"provenance": "unavailable"}
        if category == "successor_failure":
            incident["recovery_attempts"] = 0
        if category == "escalation_failure":
            incident.update({"requested_model": "gpt-5.6-terra", "effective_model": "gpt-5.6-terra", "requested_reasoning": "medium", "effective_reasoning": "medium"})
        projected = planner.incident_projection({"incident": incident}, NOW)
        expect(f"incident-{category}-material", projected["valid"] is True and projected["decision"] == decision and projected["attention_summary"]["human_attention_required"] is True, projected)
        expect(f"incident-{category}-privacy-safe-receipt", forbidden_paths(projected["incident_receipt"]) == [], projected)
    unavailable_with_value = planner.incident_projection({"incident": {**incident_base, "category": "unavailable_observation", "observation": {"provenance": "unavailable", "value": 0}}}, NOW)
    expect("unavailable-incident-never-zero", "unavailable_observation_must_not_supply_value" in unavailable_with_value["stop_conditions"], unavailable_with_value)
    silent_escalation = planner.incident_projection({"incident": {**incident_base, "category": "escalation_failure", "requested_model": "gpt-5.6-terra", "effective_model": "gpt-5.5", "requested_reasoning": "medium", "effective_reasoning": "low"}}, NOW)
    expect("incident-no-silent-model-effort-change", "silent_model_change_forbidden" in silent_escalation["stop_conditions"] and "silent_reasoning_change_forbidden" in silent_escalation["stop_conditions"], silent_escalation)
    private_incident = planner.incident_projection({"incident": {**incident_base, "category": "evidence_conflict", "prompt": "private"}}, NOW)
    expect("incident-privacy-holds", "privacy_exposure" in private_incident["stop_conditions"], private_incident)

    handoff = planner.build_work_terminal_handoff(
        "af18-450", "run-450-a", "https://github.com/farmerhunter/agent-foundry/issues/450", "sha256:abc",
        {"disposition": "candidate_hold", "summary": "bounded lesson"},
    )
    expect("terminal-handoff-valid", planner.validate_work_terminal_handoff(handoff)["valid"], handoff)
    none = planner.build_work_terminal_handoff("af18-450", "run-450-b", handoff["issue_url_anchor"], "sha256:none")
    expect("terminal-handoff-none", none["candidate"] is None and none["learning_signal"] == "none", none)
    private = {**handoff, "native_thread_id": "thread-secret"}
    expect("terminal-handoff-privacy", "privacy_exposure" in planner.validate_work_terminal_handoff(private)["stop_conditions"], private)
    malformed_anchor = {**handoff, "issue_url_anchor": handoff["issue_url_anchor"] + "\n"}
    expect("terminal-handoff-anchor-strict", "invalid_issue_url_anchor" in planner.validate_work_terminal_handoff(malformed_anchor)["stop_conditions"], malformed_anchor)

    class FakeComments:
        def __init__(self, comments=None, fail_add=False):
            self.comments = list(comments or [])
            self.fail_add = fail_add
        def list_comments(self, _anchor):
            return list(self.comments)
        def add_comment(self, _anchor, body):
            if self.fail_add:
                self.fail_add = False
                raise RuntimeError("uncertain")
            self.comments.append({"body": body})

    adapter = FakeComments()
    recorded = helper.write_work_terminal_handoff(adapter, handoff)
    expect("terminal-write", recorded["status"] == "recorded", recorded)
    repeated = helper.write_work_terminal_handoff(adapter, handoff)
    expect("terminal-idempotent", repeated["status"] == "already_recorded", repeated)
    conflict = helper.write_work_terminal_handoff(adapter, {**handoff, "payload_hash": "sha256:other"})
    expect("terminal-conflict", conflict["status"] == "held_handoff_conflict", conflict)
    uncertain = FakeComments(fail_add=True)
    uncertain_result = helper.write_work_terminal_handoff(uncertain, handoff)
    expect("terminal-uncertain-retry", uncertain_result["status"] == "recorded" and uncertain_result["attempts"] == 2, uncertain_result)
    recovered = helper.reconstruct_work_terminal_state(adapter.list_comments(handoff["issue_url_anchor"]), handoff["issue_url_anchor"])
    expect("terminal-restart-recovery", recovered["status"] == "complete" and recovered["handoff"]["payload_hash"] == "sha256:abc", recovered)
    disposition = helper.append_work_terminal_disposition(adapter, handoff, "disposed", "receipt-1")
    expect("terminal-disposition", disposition["status"] == "recorded" and disposition["state"]["dispositions"][0]["disposition"] == "disposed", disposition)
    expect("terminal-logical-dispose", len(adapter.comments) >= 2, adapter.comments)
    expect("terminal-no-runtime-side-effects", helper.WORK_TERMINAL_MARKER in adapter.comments[0]["body"] and "native_thread_id" not in adapter.comments[0]["body"], adapter.comments)

    print("af18 mvp1 control-plane tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
