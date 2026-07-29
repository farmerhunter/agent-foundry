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
    "total_context_tokens", "context_age_hours", "cumulative_resource_tokens", "packet_bytes",
    "callback_count", "compact_rehydration_count", "full_rehydration_count", "retry_count", "recovery_count", "elapsed_seconds",
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
    return tuple(str(scenario.get(key, "")) for key in (
        "complexity", "risk", "role_route", "model_class", "quality_rubric_version", "root_budget_unit", "anchor_type",
    ))


def validate_measurement(name: str, item: Any, errors: list[str]) -> dict[str, Any]:
    if not isinstance(item, dict):
        errors.append(f"missing_measurement:{name}")
        return {"availability": "unavailable", "value": None, "unit": None, "source": None, "observed_at": None}
    availability = item.get("availability")
    value = item.get("value")
    if availability not in AVAILABILITY:
        errors.append(f"invalid_measurement_availability:{name}")
    if availability == "unavailable":
        if value is not None or not item.get("reason"):
            errors.append(f"unavailable_measurement_must_be_null_with_reason:{name}")
    elif not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        errors.append(f"invalid_measurement_value:{name}")
    if not isinstance(item.get("unit"), str) or not item["unit"]:
        errors.append(f"missing_measurement_unit:{name}")
    if not isinstance(item.get("source"), str) or not item["source"]:
        errors.append(f"missing_measurement_source:{name}")
    if availability != "unavailable" and not isinstance(item.get("observed_at"), str):
        errors.append(f"missing_measurement_timestamp:{name}")
    return {key: item.get(key) for key in ("availability", "value", "unit", "source", "observed_at", "reason")}


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
    fields = ("scenario_id", "complexity", "risk", "role_route", "model_class", "quality_rubric_version", "root_budget_unit", "anchor_type")
    if not isinstance(scenario, dict) or any(not scenario.get(field) for field in fields):
        errors.append("invalid_scenario_comparability")
    else:
        reject_unknown(scenario, set(fields), "scenario", errors)
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
    if not isinstance(provenance, dict) or not is_anchor(provenance.get("evidence_anchor")) or provenance.get("collection_method") not in {"fixture", "manual_adapter_export"} or not provenance.get("source"):
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
    elif attention["outcome"] == "required" and not attention.get("category"):
        errors.append("material_attention_missing_category")
    resources = sample.get("resources")
    normalized_resources: dict[str, Any] = {}
    if not isinstance(resources, dict) or not resources:
        errors.append("missing_resources")
    else:
        for name, item in sorted(resources.items()):
            normalized_resources[name] = validate_measurement(name, item, errors)
        missing_resources = REQUIRED_RESOURCES - set(resources)
        if missing_resources:
            errors.append("missing_required_resources:" + ",".join(sorted(missing_resources)))
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
        "cohort_key": cohort_key(sample), "scenario_id": scenario["scenario_id"], "terminal_state": sample["terminal_state"],
        "quality": {"passed": quality["passed"], "reason": quality["reason"]}, "attention": dict(attention),
        "resources": normalized_resources, "anchors": dict(anchors), "root_budget": dict(budget), "remaining_budget": dict(remaining),
        "provenance": {key: provenance[key] for key in ("source", "collection_method", "captured_at", "evidence_anchor", "observation_kind")},
    }
    return normalized, []


def metric_summary(samples: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    observations = [sample["resources"].get(metric) for sample in samples if metric in sample["resources"]]
    counts = Counter(item["availability"] for item in observations)
    values = [float(item["value"]) for item in observations if item["availability"] == "observed" and item["value"] is not None]
    return {"n_observed": len(values), "n_estimated": counts["estimated"], "n_unavailable": counts["unavailable"], "median": percentile(values, .5), "p80": percentile(values, .8), "range": [min(values), max(values)] if values else [None, None], "p80_bootstrap_interval": bootstrap_p80_interval(values)}


def analyze(valid: list[dict[str, Any]], invalid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for sample in valid:
        groups[(sample["task_class"], sample["cohort_key"])].append(sample)
    cohorts: list[dict[str, Any]] = []
    for (task_class, key), rows in sorted(groups.items()):
        variants = {variant: [row for row in rows if row["variant"] == variant] for variant in sorted(VARIANTS)}
        metrics = sorted({name for row in rows for name in row["resources"]})
        summaries = {variant: {metric: metric_summary(variants[variant], metric) for metric in metrics} for variant in sorted(VARIANTS)}
        candidate_metrics = ("total_context_tokens", "context_age_hours", "cumulative_resource_tokens")
        holds: list[str] = []
        if any(len(variants[variant]) < 5 for variant in ("A", "B", "C")):
            holds.append("requires_at_least_five_valid_A_B_C_rows")
        for metric in candidate_metrics:
            for variant in ("A", "C"):
                if summaries[variant].get(metric, {}).get("n_observed", 0) < 5:
                    holds.append(f"requires_five_observed_{variant}_{metric}")
        attention_required = sum(row["attention"]["outcome"] == "required" for row in variants["C"])
        failed_or_held = sum(row["terminal_state"] in {"failed", "held"} for row in variants["C"])
        if any(not row["quality"]["passed"] for row in variants["C"]):
            holds.append("quality_guardrail_failed_C")
        if attention_required:
            holds.append("material_attention_guardrail_failed_C")
        if failed_or_held:
            holds.append("failed_or_held_guardrail_failed_C")
        if any(row["resources"]["recovery_count"]["value"] not in (0, None) for row in variants["C"]):
            holds.append("recovery_guardrail_failed_C")
        if holds:
            candidate = {"status": "candidate_hold", "candidate_hold_reasons": sorted(set(holds)), "confidence": "not_eligible"}
        else:
            def recommendation(metric: str) -> dict[str, Any]:
                summary = summaries["C"][metric]
                return {"value": summary["p80_bootstrap_interval"][1], "unit": next(row["resources"][metric]["unit"] for row in variants["C"]), "distribution": "C_observed_p80_with_bootstrap_upper", "uncertainty": summary["p80_bootstrap_interval"], "provenance": "explicit_adapter_evidence"}
            roots = [float(row["root_budget"]["value"]) for row in variants["C"]]
            candidate = {"status": "candidate", "max_context_tokens": recommendation("total_context_tokens"), "max_age_hours": recommendation("context_age_hours"), "root_budget_band": {"min": min(roots), "max": bootstrap_p80_interval(roots)[1], "unit": "tokens", "uncertainty": bootstrap_p80_interval(roots), "provenance": "explicit_adapter_evidence"}, "confidence": "small_n_bootstrap", "assumptions": ["A and C observed rows only; B is explicit estimated counterfactual", "quality, attention, failure, hold, and recovery guardrails passed", "#442 low_limit containment neither seeds nor caps this value"]}
        cohorts.append({"task_class": task_class, "comparability_key": list(key), "sample_counts": {variant: len(variants[variant]) for variant in sorted(VARIANTS)}, "metrics": summaries, "quality_pass_rate_C": sum(row["quality"]["passed"] for row in variants["C"]) / len(variants["C"]) if variants["C"] else None, "attention_required_rate_C": attention_required / len(variants["C"]) if variants["C"] else None, "terminal_state_counts_C": dict(sorted(Counter(row["terminal_state"] for row in variants["C"]).items())), "failed_or_held_C": failed_or_held, "outliers": [row["sample_id"] for row in rows if row["terminal_state"] in {"failed", "held"}], "candidate_recommendation": candidate})
    return cohorts


def run(packet: dict[str, Any], now: dt.datetime, max_age: int) -> dict[str, Any]:
    packet_errors: list[str] = []
    if forbidden_paths(packet):
        packet_errors.append("privacy_forbidden_raw_content")
    if packet.get("schema_version") != 1 or packet.get("protocol_version") != PROTOCOL_VERSION or packet.get("collection_mode") not in {"fixture", "manual_adapter_export"} or not isinstance(packet.get("samples"), list):
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
