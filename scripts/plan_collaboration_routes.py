#!/usr/bin/env python3
"""Plan advisory collaboration routes with a hard low_limit gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


MODEL_ORDER = {
    "gpt-5": 50,
    "gpt-5.1": 51,
    "gpt-5.2": 52,
    "gpt-5.3": 53,
    "gpt-5.4": 54,
    "gpt-5.5": 55,
    "gpt-5.6": 56,
}
REASONING_ORDER = {"minimal": 0, "low": 1, "medium": 2, "high": 3}
DEFAULT_CEILING_MODEL = "gpt-5.5"
DEFAULT_CEILING_REASONING = "medium"
GLOBAL_HARD_CONTEXT_CEILING = 12000
THRESHOLD_BANDS = {
    "generic_default": {"max_context_tokens": 6000, "max_age_hours": 24},
    "coordinator_routing_status_readback": {"max_context_tokens": 4000, "max_age_hours": 12},
    "architect_design_gate": {"max_context_tokens": 6000, "max_age_hours": 24},
    "implementer_small_scoped_implementation": {"max_context_tokens": 8000, "max_age_hours": 24},
    "reviewer_exact_pr_review": {"max_context_tokens": 10000, "max_age_hours": 12},
    "tester_focused_validation": {"max_context_tokens": 8000, "max_age_hours": 12},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an advisory collaboration route packet and fail closed on low_limit breaches.",
    )
    parser.add_argument("--input", help="JSON packet path. Defaults to stdin when provided.")
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
        raise SystemExit("input packet must be a JSON object")
    return value


def utc_now(raw: str | None) -> dt.datetime:
    if raw:
        return parse_timestamp(raw, "now")
    return dt.datetime.now(dt.timezone.utc)


def parse_timestamp(raw: Any, field: str) -> dt.datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} missing")
    value = raw.strip().replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def model_rank(model: Any) -> int | None:
    if not isinstance(model, str):
        return None
    if model in MODEL_ORDER:
        return MODEL_ORDER[model]
    return None


def reasoning_rank(reasoning: Any) -> int | None:
    if not isinstance(reasoning, str):
        return None
    return REASONING_ORDER.get(reasoning)


def add_missing(stops: list[str], packet: dict[str, Any], field: str) -> Any:
    value = packet.get(field)
    if value in (None, "", [], {}):
        stops.append(f"missing_{field}")
    return value


def valid_escalation_approval(approval: Any) -> bool:
    if not isinstance(approval, dict):
        return False
    required = ("issue", "role", "model", "reasoning", "purpose", "budget")
    return all(approval.get(field) not in (None, "", [], {}) for field in required)


def valid_threshold_exception(exception: Any, now: dt.datetime, issue: Any, role: Any) -> bool:
    if not isinstance(exception, dict):
        return False
    required = ("issue", "role", "temporary_cap", "reason", "expiry")
    if not all(exception.get(field) not in (None, "", [], {}) for field in required):
        return False
    if exception.get("issue") != issue or exception.get("role") != role:
        return False
    if not isinstance(exception.get("temporary_cap"), int) or exception["temporary_cap"] > GLOBAL_HARD_CONTEXT_CEILING:
        return False
    try:
        expiry = parse_timestamp(exception.get("expiry"), "threshold_exception.expiry")
    except (TypeError, ValueError):
        return False
    return expiry > now


def resolve_threshold(context: dict[str, Any], now: dt.datetime, stops: list[str], issue: Any, role: Any) -> dict[str, Any]:
    band = context.get("threshold_band")
    if not isinstance(band, str) or not band.strip():
        stops.append("missing_threshold_band")
        band = "unknown"
    policy = THRESHOLD_BANDS.get(band)
    if policy is None:
        stops.append("unknown_threshold_band")
        policy = THRESHOLD_BANDS["generic_default"]

    effective = {
        "band": band,
        "max_context_tokens": policy["max_context_tokens"],
        "max_age_hours": policy["max_age_hours"],
        "global_hard_ceiling": GLOBAL_HARD_CONTEXT_CEILING,
        "exception_applied": False,
    }

    requested_max = context.get("max_context_tokens")
    requested_age = context.get("max_age_hours")
    max_override_requested = requested_max not in (None, policy["max_context_tokens"])
    age_override_requested = requested_age not in (None, policy["max_age_hours"])
    override_requested = max_override_requested or age_override_requested or "threshold_exception" in context
    if isinstance(requested_max, int) and requested_max > GLOBAL_HARD_CONTEXT_CEILING:
        stops.append("context_exceeds_global_hard_ceiling")
    if override_requested:
        exception = context.get("threshold_exception")
        if (
            not valid_threshold_exception(exception, now, issue, role)
            or age_override_requested
            or (max_override_requested and requested_max != exception.get("temporary_cap"))
        ):
            stops.append("malformed_threshold_override")
        else:
            effective["max_context_tokens"] = exception["temporary_cap"]
            effective["exception_applied"] = True
    return effective


def validate(packet: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    stops: list[str] = []
    warnings: list[str] = []

    issue = add_missing(stops, packet, "issue")
    role = add_missing(stops, packet, "role")
    dispatch_id = packet.get("dispatch_id")
    durable_anchor = packet.get("durable_anchor")
    if not dispatch_id and not durable_anchor:
        stops.append("missing_duplicate_dispatch_anchor")

    token_budget = packet.get("token_budget")
    if not isinstance(token_budget, dict):
        stops.append("missing_token_budget")
        token_budget = {}
    first_turn_words = token_budget.get("first_active_turn_words")
    total_tokens = token_budget.get("total_role_thread_tokens")
    if not isinstance(first_turn_words, int) or first_turn_words <= 0:
        stops.append("missing_first_active_turn_word_budget")
    elif first_turn_words > 1500:
        stops.append("first_active_turn_word_budget_exceeds_low_limit")
    if not isinstance(total_tokens, int) or total_tokens <= 0:
        stops.append("missing_total_role_thread_token_budget")
    elif total_tokens > 25000:
        stops.append("total_role_thread_token_budget_exceeds_low_limit")

    context = packet.get("context")
    if not isinstance(context, dict):
        stops.append("missing_context")
        context = {}
    try:
        source_ts = parse_timestamp(context.get("source_timestamp"), "context.source_timestamp")
    except (TypeError, ValueError):
        stops.append("missing_or_invalid_source_timestamp")
        source_ts = None
    threshold = resolve_threshold(context, now, stops, issue, role)
    if source_ts is not None and now - source_ts > dt.timedelta(hours=threshold["max_age_hours"]):
        stops.append("stale_context")

    readback = packet.get("readback")
    if not isinstance(readback, dict):
        stops.append("missing_readback")
        readback = {}
    if readback.get("mode") != "cursor_only_compact":
        stops.append("readback_not_cursor_only_compact")
    if readback.get("compact_readback_available") is not True:
        stops.append("compact_readback_unavailable")

    duplicate = packet.get("duplicate_dispatch")
    if not isinstance(duplicate, dict):
        stops.append("missing_duplicate_dispatch")
        duplicate = {}
    if "duplicate_owner_detected" not in duplicate:
        stops.append("missing_duplicate_owner_detected")
    if "same_issue_role_boundary_seen" not in duplicate:
        stops.append("missing_same_issue_role_boundary_seen")
    if duplicate.get("duplicate_owner_detected") is True:
        stops.append("duplicate_owner")
    if duplicate.get("same_issue_role_boundary_seen") is True:
        stops.append("duplicate_issue_role_boundary")

    hold_conditions = packet.get("hold_conditions")
    required_holds = {
        "missing_budget",
        "budget_breach",
        "stale_context",
        "oversized_context",
        "duplicate_owner",
        "compact_readback_unavailable",
        "escalation_need",
        "missing_required_fields",
    }
    if not isinstance(hold_conditions, list):
        stops.append("missing_hold_conditions")
    else:
        missing_holds = sorted(required_holds - {str(item) for item in hold_conditions})
        if missing_holds:
            stops.append("incomplete_hold_conditions")
            warnings.append(f"missing_hold_conditions:{','.join(missing_holds)}")

    model = packet.get("model", {})
    if not isinstance(model, dict):
        stops.append("missing_model")
        model = {}
    requested_model = model.get("name")
    requested_reasoning = model.get("reasoning")
    if model_rank(requested_model) is None:
        stops.append("missing_or_unknown_model")
    if reasoning_rank(requested_reasoning) is None:
        stops.append("missing_or_unknown_reasoning")
    approval = model.get("human_escalation_approval")
    if model_rank(requested_model) is not None and model_rank(requested_model) > model_rank(DEFAULT_CEILING_MODEL):
        if not valid_escalation_approval(approval):
            stops.append("model_escalation_requires_human_approval")
    if reasoning_rank(requested_reasoning) is not None and reasoning_rank(requested_reasoning) > reasoning_rank(DEFAULT_CEILING_REASONING):
        if not valid_escalation_approval(approval):
            stops.append("reasoning_escalation_requires_human_approval")

    context_size = context.get("estimated_context_tokens")
    if isinstance(context_size, int) and context_size > threshold["max_context_tokens"]:
        stops.append("oversized_context")

    decision = "hold_for_decision" if stops else packet.get("requested_route", "serial_current_session")
    return {
        "issue": issue,
        "role": role,
        "dispatch_id": dispatch_id,
        "durable_anchor": durable_anchor,
        "route_decision": decision,
        "stop_conditions": sorted(set(stops)),
        "warnings": warnings,
        "low_limit": {
            "first_active_turn_words": 1500,
            "total_role_thread_tokens": 25000,
            "model_ceiling": DEFAULT_CEILING_MODEL,
            "reasoning_ceiling": DEFAULT_CEILING_REASONING,
            "readback_default": "cursor_only_compact",
            "global_hard_context_ceiling": GLOBAL_HARD_CONTEXT_CEILING,
        },
        "effective_threshold": threshold,
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def main() -> int:
    args = parse_args()
    packet = read_packet(args.input)
    result = validate(packet, utc_now(args.now))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
