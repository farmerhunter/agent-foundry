#!/usr/bin/env python3
"""Focused fail-closed tests for AF18 policy telemetry receipts and aggregation."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "scripts" / "collect_af18_policy_telemetry.py"
AGGREGATOR = ROOT / "scripts" / "aggregate_af18_policy_telemetry.py"
FIXTURE = ROOT / "scripts" / "fixtures" / "af18_policy_telemetry" / "normal-unavailable.json"
SCHEMA = ROOT / "schemas" / "af18-policy-telemetry.schema.yaml"
collect_spec = importlib.util.spec_from_file_location("collector", COLLECTOR)
collector = importlib.util.module_from_spec(collect_spec)
assert collect_spec and collect_spec.loader
collect_spec.loader.exec_module(collector)
aggregate_spec = importlib.util.spec_from_file_location("aggregate", AGGREGATOR)
aggregate_module = importlib.util.module_from_spec(aggregate_spec)
assert aggregate_spec and aggregate_spec.loader
aggregate_spec.loader.exec_module(aggregate_module)
NOW = collector.parse_time("2026-07-30T00:00:00Z", "now")


def expect(name: str, value: bool, detail: object) -> list[str]:
    if value:
        print(f"{name}: ok")
        return []
    return [f"{name}: {detail}"]


def receipt(**changes: object) -> dict:
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    value.update(changes)
    return value


def holds(value: dict, reason: str, trusted: set[str] | None = None) -> bool:
    try:
        collector.collect_receipt(value, NOW, trusted)
    except (collector.TelemetryError, aggregate_module.TelemetryError) as error:
        return str(error) == reason
    return False


def main() -> int:
    errors: list[str] = []
    base = receipt()
    normal = collector.collect_receipt(base, NOW)
    errors += expect("unavailable-normal-receipt", normal["observations"]["total_context_tokens"]["value"] is None and normal["observations"]["context_age_hours"]["provenance"] == "unavailable" and normal["mutation_performed"] is False, normal)
    held = receipt()
    held["capability_validation"] = {"status": "held", "allowlist_compliant": False, "risk_compliant": True, "privacy_compliant": True, "compatibility_hold": False, "safety_hold": True}
    held_event = collector.collect_receipt(held, NOW)
    errors += expect("safety-hold-recorded", held_event["effective_decision"] == "hold_for_decision", held_event)
    observed = receipt()
    observed["observations"]["total_context_tokens"] = {"provenance": "observed", "value": 8000, "source": "trusted_adapter_receipt"}
    observed["observations"]["context_age_hours"] = {"provenance": "estimated", "value": 2, "source": "trusted_adapter_receipt"}
    trusted = collector.collect_receipt(observed, NOW, {"adapter-control-plane-v1"})
    errors += expect("trusted-observed-estimated", trusted["producer"]["trusted_binding"] is True and trusted["observations"]["total_context_tokens"]["value"] == 8000, trusted)
    errors += expect("untrusted-context-holds", holds_prefix(observed, "untrusted_context_measurement_"), observed)
    unavailable_zero = receipt()
    unavailable_zero["observations"]["total_context_tokens"]["value"] = 0
    errors += expect("unavailable-not-zero", holds(unavailable_zero, "unavailable_not_null_total_context_tokens"), unavailable_zero)
    forged = receipt()
    forged["producer"]["runtime_owned"] = True
    errors += expect("forged-runtime-owned", holds(forged, "forged_or_malformed_producer"), forged)
    private = receipt()
    private["prompt"] = "do not retain"
    errors += expect("privacy-rejects-prompt", holds(private, "privacy_forbidden_field"), private)
    unknown = receipt()
    unknown["undeclared"] = "not allowed"
    errors += expect("unknown-field-rejects", holds(unknown, "malformed_receipt"), unknown)
    route_mismatch = receipt()
    route_mismatch["route"]["adapter_mapping"]["model_id"] = "gpt-5.5"
    errors += expect("route-model-mapping", holds(route_mismatch, "route_model_mapping_mismatch"), route_mismatch)
    normal_12k = receipt()
    normal_12k["limits"]["context_tokens"] = 12000
    errors += expect("no-normal-historic-12k", holds(normal_12k, "profile_limits_or_root_budget_mismatch"), normal_12k)
    root_budget = receipt()
    root_budget["observations"]["root_budget_used_tokens"]["value"] = 100001
    errors += expect("root-budget-cap", holds(root_budget, "root_budget_use_exceeds_effective_cap"), root_budget)
    luna = receipt()
    luna["policy"]["profile"] = "economy"
    luna["work"]["root_budget_tokens"] = 60000
    luna["route"] = {"kind": "permitted_work_reasoned_override", "logical_model_class": "cost_optimized", "adapter_mapping": {"adapter": "codex", "model_id": "gpt-5.6-luna", "reasoning": "medium"}, "override_evidence": {"classification": "low_risk_multi_step_execution_or_test", "risk_level": "low", "reason": "bounded test"}}
    luna["limits"] = {"context_tokens": 12000, "context_age_hours": 12, "context_turns": 6, "profile_ceiling_tokens": 60000, "effective_work_cap_tokens": 60000}
    errors += expect("permitted-luna-override", collector.collect_receipt(luna, NOW)["route"]["kind"] == "permitted_work_reasoned_override", luna)
    luna_bad = copy.deepcopy(luna)
    luna_bad["route"]["override_evidence"]["classification"] = "anything"
    errors += expect("override-semantics", holds(luna_bad, "invalid_override_evidence"), luna_bad)
    duplicate = copy.deepcopy(base)
    errors += expect("duplicate-event", _aggregate_holds([base, duplicate], "duplicate_event"), duplicate)
    duplicate_binding = copy.deepcopy(base)
    duplicate_binding["event_id"] = "telemetry-470-normal-002"
    errors += expect("duplicate-work-lifecycle-binding", _aggregate_holds([base, duplicate_binding], "duplicate_work_lifecycle_binding"), duplicate_binding)
    stale = receipt(observed_at="2026-07-28T00:00:00Z")
    errors += expect("stale-event", holds(stale, "stale_or_out_of_window_event"), stale)
    aggregate_one = aggregate_module.aggregate([base], "2026-07-30T00:00:00Z")
    aggregate_two = aggregate_module.aggregate([base], "2026-07-30T00:00:00Z")
    errors += expect("deterministic-readout-preservation", aggregate_one == aggregate_two and aggregate_one["events"][0]["limits"]["context_tokens"] == 24000 and aggregate_one["policy_readout"]["normal_profile_historic_12k_cap"] is False and aggregate_one["policy_readout"]["auto_tuning_performed"] is False, aggregate_one)
    schema = SCHEMA.read_text(encoding="utf-8")
    errors += expect("schema-privacy-and-provenance", all(term in schema for term in ("trusted producer", "unavailable measurements", "low_limit", "fixed reasoning multiplier")), schema)
    if errors:
        print("\n".join(errors))
        return 1
    print("af18 policy telemetry tests passed")
    return 0


def _aggregate_holds(receipts: list[dict], reason: str) -> bool:
    try:
        aggregate_module.aggregate(receipts, "2026-07-30T00:00:00Z")
    except (collector.TelemetryError, aggregate_module.TelemetryError) as error:
        return str(error) == reason
    return False


def holds_prefix(value: dict, prefix: str) -> bool:
    try:
        collector.collect_receipt(value, NOW)
    except (collector.TelemetryError, aggregate_module.TelemetryError) as error:
        return str(error).startswith(prefix)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
