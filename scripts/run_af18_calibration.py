#!/usr/bin/env python3
"""Analyze explicit, privacy-safe AF18 calibration evidence offline."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "af18-calibration-protocol-v1"
CLASSES = {
    "single_session_baseline",
    "compact_cross_role",
    "independent_review_or_test_handoff",
    "bounded_successor_hold_recovery",
    "attention_materiality",
}
VARIANTS = {"A", "B", "C"}
AVAILABILITY = {"observed", "estimated", "unavailable"}
TERMINAL_STATES = {"completed", "failed", "held", "recovered"}
REQUIRED_RESOURCES = {
    "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens", "tool_output_bytes",
    "total_context_tokens", "context_age_hours", "cumulative_resource_tokens", "packet_bytes",
    "callback_count", "compact_rehydration_count", "full_rehydration_count", "retry_count", "recovery_count", "elapsed_seconds",
}
DERIVED_TOTALS = {"cumulative_resource_tokens", "total_context_tokens"}
PACKET_GLOBAL_OR_VALIDITY_CONSTRAINED = {
    "task_class": "declared class enum; invalid values are evidence rejects, not cohort splits",
    "protocol_version": "packet and sample protocol must match; mismatches are evidence rejects, not cohort splits",
    "root_budget_unit": "tokens is schema-constrained and must match the budget; mismatches are evidence rejects, not cohort splits",
}
FORBIDDEN_KEYS = {
    "prompt", "raw_prompt", "prompt_body", "body", "transcript", "raw_transcript",
    "tool_content", "tool_output", "tool_history", "conversation", "messages",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Explicit evidence JSON path; stdin is used otherwise.")
    parser.add_argument("--output", help="Explicit JSON output path; stdout is used otherwise.")
    parser.add_argument("--now", help="UTC timestamp used for deterministic freshness validation.")
    parser.add_argument("--max-evidence-age-hours", type=int, default=168)
    return parser.parse_args()


def utc(value: str | None) -> dt.datetime:
    if value is None:
        return dt.datetime.now(dt.timezone.utc)
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp_must_include_timezone")
    return parsed.astimezone(dt.timezone.utc)


def read_packet(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("packet_must_be_json_object")
    return value


def forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if key.lower() in FORBIDDEN_KEYS:
                found.append(child)
            found.extend(forbidden_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(forbidden_paths(item, f"{path}[{index}]"))
    return found


def is_anchor(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://github.com/")


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def bootstrap_p80_interval(values: list[float]) -> list[float | None]:
    if not values:
        return [None, None]
    generator = random.Random(457)
    boot = [percentile([generator.choice(values) for _ in values], 0.8) for _ in range(256)]
    return [percentile([value for value in boot if value is not None], 0.1), percentile([value for value in boot if value is not None], 0.9)]


def cohort_key(sample: dict[str, Any]) -> tuple[str, ...]:
    scenario = sample.get("scenario", {})
    return (
        str(sample.get("protocol_version", "")), str(sample.get("task_class", "")),
        str(scenario.get("scenario_id", "")), str(scenario.get("scenario_variant", "")),
        str(scenario.get("objective_or_acceptance_fixture_id", "")), str(scenario.get("complexity", "")),
        str(scenario.get("risk", "")), str(scenario.get("route_family", "")),
        str(scenario.get("model_class", "")), str(scenario.get("quality_rubric_version", "")),
        str(sample.get("policy_version", "")), json.dumps(sorted(scenario.get("canonical_allowed_tools", []))),
        str(scenario.get("measurement_window", {}).get("definition", "")),
        str(scenario.get("root_budget_unit", "")), str(scenario.get("anchor_type", "")),
    )


def validate_measurement(name: str, item: Any, errors: list[str]) -> dict[str, Any]:
    if not isinstance(item, dict):
        errors.append(f"missing_measurement:{name}")
        return {"observation_id": None, "availability": "unavailable", "value": None, "unit": None, "source": None, "observed_at": None}
    reject_unknown(item, {"observation_id", "availability", "value", "unit", "source", "observed_at", "reason", "observation_basis", "derived_total_component_ids", "invocation_ids"}, f"measurement_{name}", errors)
    availability = item.get("availability")
    value = item.get("value")
    if not isinstance(item.get("observation_id"), str) or not item["observation_id"]:
        errors.append(f"missing_measurement_observation_id:{name}")
    if availability not in AVAILABILITY:
        errors.append(f"invalid_measurement_availability:{name}")
    if availability == "unavailable":
        if value is not None or item.get("reason") not in {"not_exposed", "redacted", "not_collected", "invalid"}:
            errors.append(f"unavailable_measurement_must_be_null_with_reason:{name}")
    elif not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        errors.append(f"invalid_measurement_value:{name}")
    if not isinstance(item.get("unit"), str) or not item["unit"]:
        errors.append(f"missing_measurement_unit:{name}")
    if not isinstance(item.get("source"), str) or not item["source"]:
        errors.append(f"missing_measurement_source:{name}")
    if availability != "unavailable" and not isinstance(item.get("observed_at"), str):
        errors.append(f"missing_measurement_timestamp:{name}")
    component_ids = item.get("derived_total_component_ids")
    if component_ids is not None and (not isinstance(component_ids, list) or not component_ids or any(not isinstance(value, str) or not value for value in component_ids) or len(component_ids) != len(set(component_ids))):
        errors.append(f"invalid_derived_total_component_ids:{name}")
    basis = item.get("observation_basis")
    if basis not in {None, "derived", "independent_observed"}:
        errors.append(f"invalid_observation_basis:{name}")
    if component_ids and basis != "derived":
        errors.append(f"derived_components_require_derived_basis:{name}")
    if basis == "independent_observed" and component_ids is not None:
        errors.append(f"independent_observation_must_not_have_components:{name}")
    invocation_ids = item.get("invocation_ids")
    if invocation_ids is not None and (not isinstance(invocation_ids, list) or not invocation_ids or any(not isinstance(value, str) or not value for value in invocation_ids) or len(invocation_ids) != len(set(invocation_ids))):
        errors.append(f"invalid_invocation_ids:{name}")
    return {key: item.get(key) for key in ("observation_id", "availability", "value", "unit", "source", "observed_at", "reason", "observation_basis", "derived_total_component_ids", "invocation_ids")}


def reject_unknown(value: Any, allowed: set[str], label: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        unknown = sorted(set(value) - allowed)
        if unknown:
            errors.append(f"unknown_{label}_field:" + ",".join(unknown))


def validate_sample(sample: Any, packet: dict[str, Any], now: dt.datetime, max_age: int) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not isinstance(sample, dict):
        return None, ["sample_not_object"]
    if forbidden_paths(sample):
        errors.append("privacy_forbidden_raw_content")
    required = ("sample_id", "protocol_version", "task_class", "variant", "variant_declaration", "scenario", "work_id", "execution_id", "anchors", "root_budget", "remaining_budget", "policy_version", "provenance", "terminal_state", "quality", "attention", "resources")
    for key in required:
        if key not in sample:
            errors.append(f"missing:{key}")
    if sample.get("protocol_version") != packet.get("protocol_version") or sample.get("protocol_version") != PROTOCOL_VERSION:
        errors.append("protocol_version_mismatch")
    if sample.get("task_class") not in CLASSES:
        errors.append("unknown_task_class")
    if sample.get("variant") not in VARIANTS:
        errors.append("unknown_variant")
    reject_unknown(sample, set(required) | {"successor_continuity"}, "sample", errors)
    if sample.get("terminal_state") not in TERMINAL_STATES:
        errors.append("unknown_terminal_state")
    if "low_limit" in str(sample.get("policy_version", "")).lower() or "low_limit" in json.dumps(sample).lower():
        errors.append("low_limit_not_normal_policy_sample")
    scenario = sample.get("scenario")
    fields = ("scenario_id", "scenario_variant", "objective_or_acceptance_fixture_id", "complexity", "risk", "actual_role_route", "route_family", "model_class", "quality_rubric_version", "root_budget_unit", "anchor_type")
    if not isinstance(scenario, dict) or any(not scenario.get(field) for field in fields) or not isinstance(scenario.get("canonical_allowed_tools"), list) or not scenario["canonical_allowed_tools"] or any(not isinstance(tool, str) or not tool for tool in scenario["canonical_allowed_tools"]) or not isinstance(scenario.get("measurement_window"), dict) or not isinstance(scenario["measurement_window"].get("definition"), str) or not scenario["measurement_window"]["definition"] or scenario["measurement_window"].get("fixed_execution_window") is not True:
        errors.append("invalid_scenario_comparability")
    else:
        reject_unknown(scenario, set(fields) | {"canonical_allowed_tools", "measurement_window"}, "scenario", errors)
        reject_unknown(scenario["measurement_window"], {"definition", "fixed_execution_window"}, "measurement_window", errors)
    declaration = sample.get("variant_declaration")
    expected_route = "counterfactual" if sample.get("variant") == "B" else "observed_normal_route"
    if not isinstance(declaration, dict) or declaration.get("route_kind") != expected_route:
        errors.append("invalid_variant_route_declaration")
    else:
        reject_unknown(declaration, {"route_kind"}, "variant_declaration", errors)
    anchors = sample.get("anchors")
    if not isinstance(anchors, dict) or any(not is_anchor(anchors.get(key)) for key in ("work", "execution", "context")):
        errors.append("missing_or_unbound_durable_anchor")
    if sample.get("task_class") == "bounded_successor_hold_recovery" and (not is_anchor(anchors.get("predecessor")) or not is_anchor(anchors.get("successor"))):
        errors.append("missing_successor_anchor_continuity")
    budget = sample.get("root_budget")
    if not isinstance(budget, dict) or budget.get("unit") != "tokens" or not isinstance(budget.get("value"), int) or budget["value"] <= 0:
        errors.append("invalid_root_budget")
    elif isinstance(scenario, dict) and budget["unit"] != scenario.get("root_budget_unit"):
        errors.append("root_budget_unit_mismatch")
    remaining = sample.get("remaining_budget")
    if not isinstance(remaining, dict) or remaining.get("unit") != "tokens" or not isinstance(remaining.get("value"), int) or remaining["value"] < 0:
        errors.append("invalid_remaining_budget")
    elif isinstance(budget, dict) and isinstance(budget.get("value"), int) and remaining["value"] > budget["value"]:
        errors.append("remaining_budget_exceeds_root_budget")
    provenance = sample.get("provenance")
    if not isinstance(provenance, dict) or not is_anchor(provenance.get("evidence_anchor")) or provenance.get("collection_method") not in {"fixture", "manual_adapter_export", "codex_jsonl_export"} or not provenance.get("source"):
        errors.append("malformed_provenance")
    else:
        try:
            if now - utc(provenance.get("captured_at")) > dt.timedelta(hours=max_age):
                errors.append("stale_provenance")
        except (TypeError, ValueError):
            errors.append("malformed_provenance")
    if provenance and provenance.get("collection_method") != packet.get("collection_mode"):
        errors.append("collection_mode_provenance_mismatch")
    if isinstance(provenance, dict):
        expected_observation_kind = "counterfactual" if sample.get("variant") == "B" else "observed"
        if provenance.get("observation_kind") != expected_observation_kind:
            errors.append("variant_provenance_mismatch")
        reject_unknown(provenance, {"source", "collection_method", "captured_at", "evidence_anchor", "observation_kind"}, "provenance", errors)
    quality = sample.get("quality")
    if not isinstance(quality, dict) or not isinstance(quality.get("passed"), bool) or not isinstance(quality.get("reason"), str):
        errors.append("invalid_quality")
    attention = sample.get("attention")
    if not isinstance(attention, dict) or attention.get("outcome") not in {"suppressed", "not_required", "required"}:
        errors.append("invalid_attention")
    else:
        reject_unknown(attention, {"outcome", "category", "acknowledgement", "pairing"}, "attention", errors)
        acknowledgement = attention.get("acknowledgement")
        pairing = attention.get("pairing")
        if not isinstance(acknowledgement, dict) or acknowledgement.get("availability") not in {"observed", "unavailable"} or (acknowledgement.get("availability") == "observed" and not isinstance(acknowledgement.get("value"), bool)) or (acknowledgement.get("availability") == "unavailable" and acknowledgement.get("value") is not None):
            errors.append("invalid_attention_acknowledgement")
        if not isinstance(pairing, dict) or pairing.get("pair_id") is not None and (not isinstance(pairing.get("pair_id"), str) or not pairing["pair_id"]) or pairing.get("evidence_anchor") is not None and not is_anchor(pairing.get("evidence_anchor")):
            errors.append("invalid_attention_pairing")
        if attention["outcome"] == "required" and (not attention.get("category") or not isinstance(pairing, dict) or not pairing.get("pair_id") or not is_anchor(pairing.get("evidence_anchor"))):
            errors.append("material_attention_missing_category_or_pairing")
    resources = sample.get("resources")
    normalized_resources: dict[str, Any] = {}
    if not isinstance(resources, dict) or not resources:
        errors.append("missing_resources")
    else:
        reject_unknown(resources, REQUIRED_RESOURCES, "resources", errors)
        for name, item in sorted(resources.items()):
            normalized_resources[name] = validate_measurement(name, item, errors)
        missing_resources = REQUIRED_RESOURCES - set(resources)
        if missing_resources:
            errors.append("missing_required_resources:" + ",".join(sorted(missing_resources)))
        observation_ids = [item["observation_id"] for item in normalized_resources.values() if item["observation_id"]]
        if len(observation_ids) != len(set(observation_ids)):
            errors.append("duplicate_resource_observation_id")
        known_ids = set(observation_ids)
        input_item = normalized_resources.get("input_tokens", {})
        cached_item = normalized_resources.get("cached_input_tokens", {})
        output_item = normalized_resources.get("output_tokens", {})
        reasoning_item = normalized_resources.get("reasoning_tokens", {})
        if (input_item.get("availability") != "unavailable" and cached_item.get("availability") != "unavailable"
                and isinstance(input_item.get("value"), (int, float)) and isinstance(cached_item.get("value"), (int, float))
                and cached_item["value"] > input_item["value"]):
            errors.append("cached_input_tokens_exceeds_input_tokens")
        if (output_item.get("availability") != "unavailable" and reasoning_item.get("availability") != "unavailable"
                and isinstance(output_item.get("value"), (int, float)) and isinstance(reasoning_item.get("value"), (int, float))
                and reasoning_item["value"] > output_item["value"]):
            errors.append("reasoning_tokens_exceeds_output_tokens")
        for name in DERIVED_TOTALS:
            item = normalized_resources.get(name, {})
            component_ids = item.get("derived_total_component_ids")
            if item.get("availability") != "unavailable" and not component_ids and item.get("observation_basis") != "independent_observed":
                errors.append(f"missing_derived_total_component_ids:{name}")
            if component_ids:
                if item.get("observation_id") in component_ids or not set(component_ids).issubset(known_ids):
                    errors.append(f"unknown_derived_total_component_ids:{name}")
                unavailable_component = any(
                    resource.get("observation_id") in component_ids and resource.get("availability") == "unavailable"
                    for resource in normalized_resources.values()
                )
                if unavailable_component and item.get("availability") != "unavailable":
                    errors.append(f"derived_total_must_be_unavailable_with_unavailable_component:{name}")
        cumulative = normalized_resources.get("cumulative_resource_tokens", {})
        cumulative_components = cumulative.get("derived_total_component_ids")
        required_components = {normalized_resources.get(name, {}).get("observation_id") for name in ("input_tokens", "output_tokens")}
        if cumulative.get("availability") != "unavailable":
            if set(cumulative_components or []) != required_components or len(cumulative_components or []) != 2:
                errors.append("cumulative_resource_tokens_must_derive_input_plus_output_only")
            input_value = normalized_resources.get("input_tokens", {}).get("value")
            output_value = normalized_resources.get("output_tokens", {}).get("value")
            if (not isinstance(input_value, (int, float)) or isinstance(input_value, bool)
                    or not isinstance(output_value, (int, float)) or isinstance(output_value, bool)
                    or normalized_resources.get("input_tokens", {}).get("availability") == "unavailable"
                    or normalized_resources.get("output_tokens", {}).get("availability") == "unavailable"
                    or cumulative.get("value") != input_value + output_value):
                errors.append("invalid_cumulative_resource_tokens_derivation")
            if not cumulative.get("invocation_ids"):
                errors.append("cumulative_resource_tokens_requires_invocation_ids")
        if sample.get("variant") == "B":
            observed = sorted(name for name, item in normalized_resources.items() if item["availability"] == "observed")
            if observed:
                errors.append("counterfactual_resources_must_not_be_observed:" + ",".join(observed))
    if sample.get("task_class") == "bounded_successor_hold_recovery":
        continuity = sample.get("successor_continuity")
        required_continuity = {"predecessor_work_id", "successor_work_id", "predecessor_root_budget", "successor_root_budget", "predecessor_remaining_budget", "successor_remaining_budget"}
        if not isinstance(continuity, dict) or not required_continuity.issubset(continuity):
            errors.append("missing_successor_budget_continuity")
        elif (continuity["predecessor_work_id"] != sample.get("work_id") or continuity["successor_work_id"] != sample.get("work_id") or continuity["predecessor_root_budget"] != budget.get("value") or continuity["successor_root_budget"] != budget.get("value") or continuity["successor_remaining_budget"] > continuity["predecessor_remaining_budget"] or continuity["successor_remaining_budget"] != remaining.get("value")):
            errors.append("invalid_successor_budget_continuity")
    if errors:
        return None, sorted(set(errors))
    normalized = {
        "sample_id": sample["sample_id"], "task_class": sample["task_class"], "variant": sample["variant"],
        "cohort_key": cohort_key(sample), "scenario_id": scenario["scenario_id"], "actual_role_route": scenario["actual_role_route"], "route_family": scenario["route_family"], "terminal_state": sample["terminal_state"],
        "quality": {"passed": quality["passed"], "reason": quality["reason"]}, "attention": dict(attention),
        "resource_observations": normalized_resources, "resources": normalized_resources, "anchors": dict(anchors), "root_budget": dict(budget), "remaining_budget": dict(remaining),
        "provenance": {key: provenance[key] for key in ("source", "collection_method", "captured_at", "evidence_anchor", "observation_kind")},
    }
    return normalized, []


def metric_summary(samples: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    observations = [sample["resources"].get(metric) for sample in samples if metric in sample["resources"]]
    counts = Counter(item["availability"] for item in observations)
    values = [float(item["value"]) for item in observations if item["availability"] == "observed" and item["value"] is not None]
    return {"n_observed": len(values), "n_estimated": counts["estimated"], "n_unavailable": counts["unavailable"], "median": percentile(values, .5), "p80": percentile(values, .8), "range": [min(values), max(values)] if values else [None, None], "p80_bootstrap_interval": bootstrap_p80_interval(values)}


def attention_pairing_conflicts(variants: dict[str, list[dict[str, Any]]]) -> tuple[list[str], int, int]:
    suppressed = [row for row in variants["A"] if row["attention"]["outcome"] == "suppressed"]
    material = [row for row in variants["C"] if row["attention"]["outcome"] == "required"]
    suppressed_by_pair = {row["attention"]["pairing"]["pair_id"]: row for row in suppressed}
    material_by_pair = {row["attention"]["pairing"]["pair_id"]: row for row in material}
    conflicts: list[str] = []
    if len(suppressed_by_pair) != len(suppressed) or len(material_by_pair) != len(material):
        conflicts.append("attention_pairing_duplicate_pair_id")
    pair_ids = set(suppressed_by_pair) | set(material_by_pair)
    complete_pair_count = 0
    for pair_id in pair_ids:
        suppressed_row = suppressed_by_pair.get(pair_id)
        material_row = material_by_pair.get(pair_id)
        if not pair_id or not suppressed_row or not material_row:
            conflicts.append("attention_pairing_missing_required_pair")
            continue
        suppressed_attention = suppressed_row["attention"]
        material_attention = material_row["attention"]
        if suppressed_attention["pairing"]["evidence_anchor"] != material_attention["pairing"]["evidence_anchor"]:
            conflicts.append("attention_pairing_anchor_conflict")
        if suppressed_attention.get("category") != material_attention.get("category"):
            conflicts.append("attention_category_conflict")
        acknowledgement = material_attention["acknowledgement"]
        if acknowledgement["availability"] != "observed" or acknowledgement["value"] is not True:
            conflicts.append("attention_acknowledgement_conflict")
        complete_pair_count += 1
    if not suppressed or not material:
        conflicts.append("attention_pairing_missing_required_pair")
    return sorted(set(conflicts)), complete_pair_count, len(material)


def analyze(valid: list[dict[str, Any]], invalid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for sample in valid:
        groups[(sample["task_class"], sample["cohort_key"])].append(sample)
    cohorts: list[dict[str, Any]] = []
    for (task_class, key), rows in sorted(groups.items()):
        variants = {variant: [row for row in rows if row["variant"] == variant] for variant in sorted(VARIANTS)}
        metrics = sorted({name for row in rows for name in row["resources"]})
        summaries = {variant: {metric: metric_summary(variants[variant], metric) for metric in metrics} for variant in sorted(VARIANTS)}
        holds: list[str] = []
        if any(len(variants[variant]) < 5 for variant in ("A", "B", "C")):
            holds.append("requires_at_least_five_valid_A_B_C_rows")
        for metric in ("cumulative_resource_tokens", "total_context_tokens", "context_age_hours"):
            if summaries["C"].get(metric, {}).get("n_observed", 0) < 5:
                holds.append(f"insufficient_observed_C_{metric}")
        attention_required = sum(row["attention"]["outcome"] == "required" for row in variants["C"])
        attention_conflicts, attention_pair_count, attention_material_count = attention_pairing_conflicts(variants) if task_class == "attention_materiality" else ([], 0, 0)
        failed_or_held = sum(row["terminal_state"] in {"failed", "held"} for row in variants["C"])
        if any(not row["quality"]["passed"] for row in variants["C"]):
            holds.append("quality_guardrail_failed_C")
        if attention_conflicts:
            holds.extend(attention_conflicts)
        if failed_or_held:
            holds.append("failed_or_held_guardrail_failed_C")
        if holds:
            candidate = {"candidate_status": "candidate_hold", "candidate_hold_reasons": sorted(set(holds)), "candidate_confidence": "not_eligible", "candidate_assumptions": ["offline evidence only; no policy is written or activated"]}
        else:
            def recommendation(metric: str) -> dict[str, Any]:
                summary = summaries["C"][metric]
                return {"value": summary["p80_bootstrap_interval"][1], "unit": next(row["resources"][metric]["unit"] for row in variants["C"]), "distribution": "C_observed_p80_with_bootstrap_upper", "uncertainty": summary["p80_bootstrap_interval"], "provenance": "explicit_adapter_evidence"}
            cumulative_values = [
                float(row["resources"]["cumulative_resource_tokens"]["value"])
                for row in variants["C"]
                if row["resources"]["cumulative_resource_tokens"]["availability"] == "observed"
                and row["resources"]["cumulative_resource_tokens"]["value"] is not None
            ]
            cumulative_interval = bootstrap_p80_interval(cumulative_values)
            candidate = {"candidate_status": "candidate", "candidate_max_context_tokens": recommendation("total_context_tokens"), "candidate_max_age_hours": recommendation("context_age_hours"), "candidate_root_budget_band": {"min": cumulative_interval[0], "max": cumulative_interval[1], "unit": "tokens", "distribution": "C_observed_p80_with_bootstrap_interval", "uncertainty": cumulative_interval, "provenance": "explicit_adapter_evidence"}, "candidate_confidence": "small_n_bootstrap", "candidate_assumptions": ["A and C observed rows only; B is explicit estimated counterfactual", "quality and failure/hold guardrails passed; recovery count is reported without a normal-policy threshold; attention rate is reported for Human HDC review", "#442 low_limit containment neither seeds nor caps this value"]}
        cohorts.append({"task_class": task_class, "comparability_key": list(key), "sample_counts": {variant: len(variants[variant]) for variant in sorted(VARIANTS)}, "metrics": summaries, "quality_pass_rate_C": sum(row["quality"]["passed"] for row in variants["C"]) / len(variants["C"]) if variants["C"] else None, "attention_required_rate_C": attention_required / len(variants["C"]) if variants["C"] else None, "attention_pair_count": attention_pair_count, "attention_material_pair_count": attention_material_count, "terminal_state_counts_C": dict(sorted(Counter(row["terminal_state"] for row in variants["C"]).items())), "failed_or_held_C": failed_or_held, "outliers": [row["sample_id"] for row in rows if row["terminal_state"] in {"failed", "held"}], "candidate_recommendation": candidate})
    return cohorts


def run(packet: dict[str, Any], now: dt.datetime, max_age: int) -> dict[str, Any]:
    packet_errors: list[str] = []
    if forbidden_paths(packet):
        packet_errors.append("privacy_forbidden_raw_content")
    if packet.get("schema_version") != 1 or packet.get("protocol_version") != PROTOCOL_VERSION or packet.get("collection_mode") not in {"fixture", "manual_adapter_export", "codex_jsonl_export"} or not isinstance(packet.get("samples"), list):
        packet_errors.append("invalid_protocol_packet")
    reject_unknown(packet, {"schema_version", "protocol_version", "collection_mode", "samples"}, "packet", packet_errors)
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    if not packet_errors:
        seen: set[str] = set()
        for index, sample in enumerate(packet["samples"]):
            normalized, errors = validate_sample(sample, packet, now, max_age)
            if normalized and normalized["sample_id"] in seen:
                errors = ["duplicate_sample_id"]
                normalized = None
            if normalized:
                seen.add(normalized["sample_id"])
                valid.append(normalized)
            else:
                invalid.append({"index": index, "sample_id": sample.get("sample_id") if isinstance(sample, dict) else None, "errors": errors})
    else:
        invalid.append({"index": None, "sample_id": None, "errors": sorted(packet_errors)})
    cohorts = analyze(valid, invalid)
    held_classes = sorted(CLASSES - {cohort["task_class"] for cohort in cohorts})
    summary = f"{len(valid)} valid sample(s), {len(invalid)} invalid evidence row(s), {len(cohorts)} comparable cohort(s); fixture evidence only." if packet.get("collection_mode") == "fixture" else f"{len(valid)} valid sample(s), {len(invalid)} invalid evidence row(s), {len(cohorts)} comparable cohort(s); no policy written."
    return {"protocol_version": PROTOCOL_VERSION, "generated_at": now.isoformat().replace("+00:00", "Z"), "offline": True, "mutation_performed": False, "runtime_config_hook_mutation_performed": False, "policy_write_performed": False, "normal_policy_effective": False, "raw_content_accepted": False, "invalid_evidence": invalid, "normalized_samples": valid, "cohorts": cohorts, "held_classes_without_valid_cohort": held_classes, "human_summary": summary}


def main() -> int:
    args = parse_args()
    try:
        result = run(read_packet(args.input), utc(args.now), args.max_evidence_age_hours)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc), "mutation_performed": False}, sort_keys=True), file=sys.stderr)
        return 2
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
