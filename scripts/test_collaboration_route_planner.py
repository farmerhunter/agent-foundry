#!/usr/bin/env python3
"""Focused regression tests for the collaboration route planner."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "scripts" / "plan_collaboration_routes.py"
spec = importlib.util.spec_from_file_location("plan_collaboration_routes", PLANNER)
planner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(planner)


def packet(**overrides):
    base = {
        "issue": 440,
        "role": "Implementer",
        "dispatch_id": "issue-440-implementer-low-limit-v1",
        "durable_anchor": "https://github.com/farmerhunter/agent-foundry/issues/440#issuecomment-5065248122",
        "requested_route": "fresh_bounded_thread",
        "token_budget": {
            "first_active_turn_words": 1500,
            "total_role_thread_tokens": 25000,
        },
        "context": {
            "source_timestamp": "2026-07-24T01:33:07Z",
            "threshold_band": "implementer_small_scoped_implementation",
            "estimated_context_tokens": 1000,
        },
        "readback": {
            "mode": "cursor_only_compact",
            "compact_readback_available": True,
        },
        "duplicate_dispatch": {
            "duplicate_owner_detected": False,
            "same_issue_role_boundary_seen": False,
        },
        "hold_conditions": [
            "missing_budget",
            "budget_breach",
            "stale_context",
            "oversized_context",
            "duplicate_owner",
            "compact_readback_unavailable",
            "escalation_need",
            "missing_required_fields",
        ],
        "model": {
            "name": "gpt-5.5",
            "reasoning": "medium",
        },
    }
    base.update(overrides)
    return base


def validate(value):
    now = dt.datetime(2026, 7, 24, 2, 0, tzinfo=dt.timezone.utc)
    return planner.validate(value, now)


def expect(name, condition, detail):
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")


def main() -> int:
    ok = validate(packet())
    expect("valid-packet-routes", ok["route_decision"] == "fresh_bounded_thread", ok)
    expect("valid-packet-does-not-mutate", ok["mutation_performed"] is False and ok["dispatch_performed"] is False, ok)
    expect("valid-band-max", ok["effective_threshold"]["max_context_tokens"] == 8000, ok)
    expect("valid-band-age", ok["effective_threshold"]["max_age_hours"] == 24, ok)

    missing_budget = validate(packet(token_budget={}))
    expect("missing-budget-holds", missing_budget["route_decision"] == "hold_for_decision", missing_budget)
    expect("missing-budget-stop-visible", "missing_first_active_turn_word_budget" in missing_budget["stop_conditions"], missing_budget)

    stale = packet()
    stale["context"] = {**stale["context"], "source_timestamp": "2026-07-20T01:33:07Z"}
    stale_result = validate(stale)
    expect("stale-context-holds", "stale_context" in stale_result["stop_conditions"], stale_result)

    readback = packet(readback={"mode": "full_rehydrate", "compact_readback_available": True})
    readback_result = validate(readback)
    expect("non-compact-readback-holds", "readback_not_cursor_only_compact" in readback_result["stop_conditions"], readback_result)

    duplicate = packet(duplicate_dispatch={"duplicate_owner_detected": True})
    duplicate_result = validate(duplicate)
    expect("duplicate-owner-holds", "duplicate_owner" in duplicate_result["stop_conditions"], duplicate_result)
    expect(
        "duplicate-boundary-subfield-required",
        "missing_same_issue_role_boundary_seen" in duplicate_result["stop_conditions"],
        duplicate_result,
    )

    missing_duplicate_subfield = packet(duplicate_dispatch={"duplicate_owner_detected": False})
    missing_duplicate_subfield_result = validate(missing_duplicate_subfield)
    expect(
        "missing-duplicate-subfield-holds",
        missing_duplicate_subfield_result["route_decision"] == "hold_for_decision",
        missing_duplicate_subfield_result,
    )
    expect(
        "missing-duplicate-subfield-visible",
        "missing_same_issue_role_boundary_seen" in missing_duplicate_subfield_result["stop_conditions"],
        missing_duplicate_subfield_result,
    )

    escalation = packet(model={"name": "gpt-5.6", "reasoning": "high"})
    escalation_result = validate(escalation)
    expect("model-escalation-holds", "model_escalation_requires_human_approval" in escalation_result["stop_conditions"], escalation_result)
    expect("reasoning-escalation-holds", "reasoning_escalation_requires_human_approval" in escalation_result["stop_conditions"], escalation_result)

    incomplete_approval = packet(model={"name": "gpt-5.6", "reasoning": "high", "human_escalation_approval": {"purpose": "x"}})
    incomplete_approval_result = validate(incomplete_approval)
    expect(
        "incomplete-approval-model-holds",
        "model_escalation_requires_human_approval" in incomplete_approval_result["stop_conditions"],
        incomplete_approval_result,
    )
    expect(
        "incomplete-approval-reasoning-holds",
        "reasoning_escalation_requires_human_approval" in incomplete_approval_result["stop_conditions"],
        incomplete_approval_result,
    )

    complete_approval = packet(
        model={
            "name": "gpt-5.6",
            "reasoning": "high",
            "human_escalation_approval": {
                "issue": 440,
                "role": "Implementer",
                "model": "gpt-5.6",
                "reasoning": "high",
                "purpose": "bounded review fix",
                "budget": "25000 tokens",
            },
        }
    )
    complete_approval_result = validate(complete_approval)
    expect("complete-approval-does-not-hold", complete_approval_result["route_decision"] == "fresh_bounded_thread", complete_approval_result)

    oversized = packet()
    oversized["context"] = {**oversized["context"], "estimated_context_tokens": 9000}
    oversized_result = validate(oversized)
    expect("oversized-context-holds", "oversized_context" in oversized_result["stop_conditions"], oversized_result)

    missing_anchor = packet(dispatch_id="", durable_anchor="")
    missing_anchor_result = validate(missing_anchor)
    expect("missing-anchor-holds", "missing_duplicate_dispatch_anchor" in missing_anchor_result["stop_conditions"], missing_anchor_result)

    generic = validate(packet(context={**packet()["context"], "threshold_band": "generic_default"}))
    expect("generic-band-max", generic["effective_threshold"]["max_context_tokens"] == 6000, generic)
    expect("generic-band-age", generic["effective_threshold"]["max_age_hours"] == 24, generic)

    coordinator = validate(packet(context={**packet()["context"], "threshold_band": "coordinator_routing_status_readback"}))
    expect("coordinator-band-max", coordinator["effective_threshold"]["max_context_tokens"] == 4000, coordinator)
    expect("coordinator-band-age", coordinator["effective_threshold"]["max_age_hours"] == 12, coordinator)

    reviewer = validate(packet(context={**packet()["context"], "threshold_band": "reviewer_exact_pr_review"}))
    expect("reviewer-band-max", reviewer["effective_threshold"]["max_context_tokens"] == 10000, reviewer)
    expect("reviewer-band-age", reviewer["effective_threshold"]["max_age_hours"] == 12, reviewer)

    missing_threshold = packet()
    missing_threshold["context"] = {key: value for key, value in missing_threshold["context"].items() if key != "threshold_band"}
    missing_threshold_result = validate(missing_threshold)
    expect("missing-threshold-holds", "missing_threshold_band" in missing_threshold_result["stop_conditions"], missing_threshold_result)

    unknown_threshold = validate(packet(context={**packet()["context"], "threshold_band": "wide_open"}))
    expect("unknown-threshold-holds", "unknown_threshold_band" in unknown_threshold["stop_conditions"], unknown_threshold)

    global_breach = validate(packet(context={**packet()["context"], "max_context_tokens": 12001}))
    expect("global-ceiling-holds", "context_exceeds_global_hard_ceiling" in global_breach["stop_conditions"], global_breach)

    malformed_override = validate(packet(context={**packet()["context"], "max_context_tokens": 9000}))
    expect("malformed-override-holds", "malformed_threshold_override" in malformed_override["stop_conditions"], malformed_override)

    malformed_age_override = validate(
        packet(
            context={
                **packet()["context"],
                "max_age_hours": 48,
                "threshold_exception": {
                    "issue": 442,
                    "role": "Implementer",
                    "temporary_cap": 8000,
                    "reason": "age overrides are not authorized",
                    "expiry": "2026-07-25T00:00:00Z",
                },
            }
        )
    )
    expect("malformed-age-override-holds", "malformed_threshold_override" in malformed_age_override["stop_conditions"], malformed_age_override)

    mismatched_cap_exception = validate(
        packet(
            context={
                **packet()["context"],
                "max_context_tokens": 9000,
                "threshold_exception": {
                    "issue": 442,
                    "role": "Implementer",
                    "temporary_cap": 8500,
                    "reason": "mismatched cap",
                    "expiry": "2026-07-25T00:00:00Z",
                },
            }
        )
    )
    expect("mismatched-cap-exception-holds", "malformed_threshold_override" in mismatched_cap_exception["stop_conditions"], mismatched_cap_exception)

    valid_exception = validate(
        packet(
            context={
                **packet()["context"],
                "max_context_tokens": 9000,
                "threshold_exception": {
                    "issue": 442,
                    "role": "Implementer",
                    "temporary_cap": 9000,
                    "reason": "bounded temporary exception",
                    "expiry": "2026-07-25T00:00:00Z",
                },
            }
        )
    )
    expect("valid-threshold-exception-routes", valid_exception["route_decision"] == "fresh_bounded_thread", valid_exception)
    expect("valid-threshold-exception-visible", valid_exception["effective_threshold"]["exception_applied"] is True, valid_exception)

    print("collaboration route planner tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
