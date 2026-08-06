#!/usr/bin/env python3
"""Validate one privacy-safe AF18 policy telemetry receipt without dispatching work."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


VERSION = "af18-policy-telemetry-v1"
PROFILE_TABLE = {
    "economy": ("cost_optimized", "gpt-5.6-luna", "low", 12000, 12, 6, 60000),
    "normal": ("general", "gpt-5.6-terra", "medium", 24000, 24, 12, 150000),
    "performance": ("high_capability", "gpt-5.6-sol", "medium", 48000, 24, 20, 300000),
}
OVERRIDES = {
    ("economy", "cost_optimized", "medium"): "low_risk_multi_step_execution_or_test",
    ("normal", "general", "low"): "small_time_sensitive_locally_ambiguous",
}
PRIVATE_KEYS = {"prompt", "messages", "message", "transcript", "tool_output", "tool_outputs", "log", "logs", "private", "secret", "content"}
SCALAR_FIELDS = {"latency_ms", "input_tokens", "cached_input_tokens", "output_tokens", "credit_scalars", "total_context_tokens", "context_age_hours", "root_budget_used_tokens"}


class TelemetryError(ValueError):
    pass


def parse_time(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise TelemetryError(f"missing_{field}")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TelemetryError(f"invalid_{field}") from error
    if parsed.tzinfo is None:
        raise TelemetryError(f"invalid_{field}")
    return parsed.astimezone(dt.timezone.utc)


def reject_private(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in PRIVATE_KEYS:
                raise TelemetryError("privacy_forbidden_field")
            reject_private(child)
    elif isinstance(value, list):
        for child in value:
            reject_private(child)


def require_keys(value: Any, allowed: set[str], required: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not required.issubset(value) or set(value) - allowed:
        raise TelemetryError(f"malformed_{label}")
    return value


def scalar(value: Any, field: str, context_only: bool, trusted: bool) -> dict[str, Any]:
    item = require_keys(value, {"provenance", "value", "source"}, {"provenance", "value", "source"}, field)
    provenance = item["provenance"]
    if provenance not in {"observed", "estimated", "unavailable"} or not isinstance(item["source"], str) or not item["source"]:
        raise TelemetryError(f"malformed_{field}")
    if provenance == "unavailable":
        if item["value"] is not None:
            raise TelemetryError(f"unavailable_not_null_{field}")
        return item
    if context_only and not trusted:
        raise TelemetryError(f"untrusted_context_measurement_{field}")
    if not isinstance(item["value"], (int, float)) or isinstance(item["value"], bool) or item["value"] < 0:
        raise TelemetryError(f"invalid_{field}")
    return item


def validate_route(receipt: dict[str, Any], profile: str, route: dict[str, Any]) -> None:
    logical, model_id, reasoning, *_ = PROFILE_TABLE[profile]
    require_keys(route, {"kind", "logical_model_class", "adapter_mapping", "override_evidence"}, {"kind", "logical_model_class", "adapter_mapping", "override_evidence"}, "route")
    mapping = require_keys(route["adapter_mapping"], {"adapter", "model_id", "reasoning"}, {"adapter", "model_id", "reasoning"}, "adapter_mapping")
    if mapping["adapter"] != "codex" or not isinstance(mapping["model_id"], str) or not isinstance(mapping["reasoning"], str):
        raise TelemetryError("malformed_adapter_mapping")
    key = (profile, route["logical_model_class"], mapping["reasoning"])
    if route["kind"] == "default":
        if route["logical_model_class"] != logical or mapping["model_id"] != model_id or mapping["reasoning"] != reasoning or route["override_evidence"] is not None:
            raise TelemetryError("route_model_mapping_mismatch")
        return
    classification = OVERRIDES.get(key)
    if route["kind"] != "permitted_work_reasoned_override" or classification is None or mapping["model_id"] != model_id:
        raise TelemetryError("unsupported_route_or_model_mapping")
    evidence = require_keys(route["override_evidence"], {"classification", "risk_level", "reason"}, {"classification", "risk_level", "reason"}, "override_evidence")
    if evidence["classification"] != classification or evidence["risk_level"] != "low" or not isinstance(evidence["reason"], str) or not evidence["reason"].strip():
        raise TelemetryError("invalid_override_evidence")
    safety = receipt["capability_validation"]
    if safety["risk_compliant"] is not True or safety["privacy_compliant"] is not True or safety["allowlist_compliant"] is not True:
        raise TelemetryError("override_safety_conflict")


def trusted_binding_error(producer: dict[str, Any], observed_at: dt.datetime, now: dt.datetime, trusted_bindings: dict[str, dict[str, str]] | None) -> str | None:
    if not isinstance(trusted_bindings, dict):
        return "missing_trusted_producer_binding"
    binding = trusted_bindings.get(producer["producer_id"])
    if not isinstance(binding, dict):
        return "missing_trusted_producer_binding"
    required = {"producer_id", "receipt_anchor", "valid_from", "valid_until"}
    if set(binding) != required or binding.get("producer_id") != producer["producer_id"]:
        return "mismatched_producer_binding"
    if binding.get("receipt_anchor") != producer["receipt_anchor"]:
        return "mismatched_receipt_anchor"
    try:
        valid_from = parse_time(binding["valid_from"], "binding_valid_from")
        valid_until = parse_time(binding["valid_until"], "binding_valid_until")
    except TelemetryError:
        return "malformed_trusted_producer_binding"
    if now.astimezone(dt.timezone.utc) > valid_until:
        return "stale_trusted_producer_binding"
    if valid_from > valid_until or observed_at < valid_from or observed_at > valid_until:
        return "binding_out_of_window"
    return None


def collect_receipt(receipt: dict[str, Any], now: dt.datetime, trusted_bindings: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    reject_private(receipt)
    required = {"event_id", "observed_at", "policy", "work", "route", "limits", "lifecycle_action", "outcome", "observations", "capability_validation", "producer"}
    root = require_keys(receipt, required, required, "receipt")
    if not isinstance(root["event_id"], str) or not root["event_id"]:
        raise TelemetryError("missing_event_id")
    observed_at = parse_time(root["observed_at"], "observed_at")
    policy = require_keys(root["policy"], {"version", "profile", "compatibility_mode"}, {"version", "profile", "compatibility_mode"}, "policy")
    if policy["version"] != "v0" or policy["profile"] not in PROFILE_TABLE or policy["compatibility_mode"] != "normal_profile":
        raise TelemetryError("unsupported_policy_profile")
    profile = policy["profile"]
    logical, model_id, reasoning, context_tokens, age_hours, turns, ceiling = PROFILE_TABLE[profile]
    if now.astimezone(dt.timezone.utc) - observed_at > dt.timedelta(hours=age_hours) or observed_at > now.astimezone(dt.timezone.utc) + dt.timedelta(minutes=5):
        raise TelemetryError("stale_or_out_of_window_event")
    work = require_keys(root["work"], {"work_id", "task_classification", "root_budget_tokens"}, {"work_id", "task_classification", "root_budget_tokens"}, "work")
    if not all(isinstance(work[key], str) and work[key] for key in ("work_id", "task_classification")) or not isinstance(work["root_budget_tokens"], int) or work["root_budget_tokens"] <= 0:
        raise TelemetryError("malformed_work")
    limits = require_keys(root["limits"], {"context_tokens", "context_age_hours", "context_turns", "profile_ceiling_tokens", "effective_work_cap_tokens"}, {"context_tokens", "context_age_hours", "context_turns", "profile_ceiling_tokens", "effective_work_cap_tokens"}, "limits")
    expected_limits = {"context_tokens": context_tokens, "context_age_hours": age_hours, "context_turns": turns, "profile_ceiling_tokens": ceiling, "effective_work_cap_tokens": min(work["root_budget_tokens"], ceiling)}
    if limits != expected_limits:
        raise TelemetryError("profile_limits_or_root_budget_mismatch")
    capability = require_keys(root["capability_validation"], {"status", "allowlist_compliant", "risk_compliant", "privacy_compliant", "compatibility_hold", "safety_hold"}, {"status", "allowlist_compliant", "risk_compliant", "privacy_compliant", "compatibility_hold", "safety_hold"}, "capability_validation")
    if any(not isinstance(capability[key], bool) for key in ("allowlist_compliant", "risk_compliant", "privacy_compliant", "compatibility_hold", "safety_hold")):
        raise TelemetryError("malformed_capability_validation")
    hold_active = any(capability[key] is not True for key in ("allowlist_compliant", "risk_compliant", "privacy_compliant")) or capability["compatibility_hold"] or capability["safety_hold"]
    if capability["status"] not in {"validated", "held"} or (hold_active and capability["status"] != "held") or (not hold_active and capability["status"] != "validated"):
        raise TelemetryError("capability_or_safety_hold")
    producer = require_keys(root["producer"], {"producer_id", "receipt_anchor", "runtime_owned"}, {"producer_id", "receipt_anchor", "runtime_owned"}, "producer")
    if producer["runtime_owned"] is not False or not isinstance(producer["producer_id"], str) or not producer["producer_id"] or not isinstance(producer["receipt_anchor"], str) or not producer["receipt_anchor"]:
        raise TelemetryError("forged_or_malformed_producer")
    validate_route(root, profile, root["route"])
    if root["lifecycle_action"] not in {"completed", "validated", "reviewed", "held"}:
        raise TelemetryError("invalid_lifecycle_action")
    require_keys(root["outcome"], {"acceptance", "quality"}, {"acceptance", "quality"}, "outcome")
    observations = require_keys(root["observations"], SCALAR_FIELDS, SCALAR_FIELDS, "observations")
    requires_trusted_binding = any(observations[field].get("provenance") in {"observed", "estimated"} for field in ("total_context_tokens", "context_age_hours") if isinstance(observations[field], dict))
    binding_error = trusted_binding_error(producer, observed_at, now, trusted_bindings)
    if requires_trusted_binding and binding_error:
        raise TelemetryError(binding_error)
    trusted = binding_error is None
    normalized = {field: scalar(observations[field], field, field in {"total_context_tokens", "context_age_hours"}, trusted) for field in SCALAR_FIELDS}
    if normalized["root_budget_used_tokens"]["provenance"] != "unavailable" and normalized["root_budget_used_tokens"]["value"] > limits["effective_work_cap_tokens"]:
        raise TelemetryError("root_budget_use_exceeds_effective_cap")
    return {"schema_version": VERSION, "event_id": root["event_id"], "observed_at": root["observed_at"], "policy": policy, "work": work, "route": root["route"], "limits": limits, "lifecycle_action": root["lifecycle_action"], "outcome": root["outcome"], "observations": normalized, "capability_validation": capability, "producer": {"producer_id": producer["producer_id"], "receipt_anchor": producer["receipt_anchor"], "trusted_binding": trusted}, "effective_decision": "hold_for_decision" if hold_active else "read_only_telemetry_ready", "mutation_performed": False, "dispatch_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one static AF18 policy telemetry receipt.")
    parser.add_argument("--receipt-json", type=Path, required=True)
    parser.add_argument("--now", default="2026-07-30T00:00:00Z")
    parser.add_argument("--trusted-bindings-json", type=Path)
    args = parser.parse_args()
    try:
        receipt = json.loads(args.receipt_json.read_text(encoding="utf-8"))
        bindings = json.loads(args.trusted_bindings_json.read_text(encoding="utf-8")) if args.trusted_bindings_json else None
        print(json.dumps(collect_receipt(receipt, parse_time(args.now, "now"), bindings), sort_keys=True))
    except (OSError, json.JSONDecodeError, TelemetryError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
