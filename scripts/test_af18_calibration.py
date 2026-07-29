#!/usr/bin/env python3
"""Focused tests for the AF18 offline calibration harness."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_af18_calibration.py"
FIXTURE = ROOT / "scripts" / "fixtures" / "af18_calibration" / "representative-fixture.json"
spec = importlib.util.spec_from_file_location("calibration", SCRIPT)
calibration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = calibration
spec.loader.exec_module(calibration)
NOW = calibration.utc("2026-07-29T10:00:00Z")


def expect(name, condition, detail):
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")


def sample(task_class, variant, index=0, **overrides):
    route = {
        "single_session_baseline": "Implementer",
        "compact_cross_role": "Coordinator>Reviewer",
        "independent_review_or_test_handoff": "Implementer>Tester",
        "bounded_successor_hold_recovery": "Coordinator>Successor",
        "attention_materiality": "Coordinator>Human",
    }[task_class]
    base = {
        "sample_id": f"{task_class}-{variant}-{index}", "protocol_version": calibration.PROTOCOL_VERSION,
        "task_class": task_class, "variant": variant,
        "scenario": {"scenario_id": task_class, "complexity": "small", "risk": "low", "role_route": route, "model_class": "standard", "quality_rubric_version": "v1", "root_budget_unit": "tokens", "anchor_type": "issue"},
        "work_id": f"work-{task_class}-{index}", "execution_id": f"run-{task_class}-{variant}-{index}",
        "anchors": {"work": "https://github.com/farmerhunter/agent-foundry/issues/457", "execution": f"https://github.com/farmerhunter/agent-foundry/issues/457#{task_class}-{variant}-{index}", "context": "https://github.com/farmerhunter/agent-foundry/issues/457#context", **({"predecessor":"https://github.com/farmerhunter/agent-foundry/issues/457#predecessor", "successor":"https://github.com/farmerhunter/agent-foundry/issues/457#successor"} if task_class == "bounded_successor_hold_recovery" else {})},
        "variant_declaration": {"route_kind": "counterfactual" if variant == "B" else "observed_normal_route"},
        "root_budget": {"value": 1000, "unit": "tokens"}, "remaining_budget": {"value": 800, "unit": "tokens"}, "policy_version": "normal-observation-v1",
        "provenance": {"source": "test-export", "collection_method": "manual_adapter_export", "captured_at": "2026-07-29T09:00:00Z", "evidence_anchor": "https://github.com/farmerhunter/agent-foundry/issues/457#evidence", "observation_kind": "counterfactual" if variant == "B" else "observed"},
        "terminal_state": "completed", "quality": {"passed": True, "reason": "test"},
        "attention": {"outcome": "suppressed" if task_class == "attention_materiality" and index % 2 == 0 else "not_required", "category": None},
        "resources": {name: {"availability": "estimated" if variant == "B" else "observed", "value": value + index, "unit": unit, "source": "adapter_counter" if variant != "B" else "counterfactual_model", "observed_at": "2026-07-29T09:00:00Z"} for name, value, unit in (("total_context_tokens", 100, "tokens"), ("context_age_hours", 1, "hours"), ("cumulative_resource_tokens", 300, "tokens"), ("packet_bytes", 200, "bytes"), ("callback_count", 1, "count"), ("compact_rehydration_count", 1, "count"), ("full_rehydration_count", 0, "count"), ("retry_count", 0, "count"), ("recovery_count", 0, "count"), ("elapsed_seconds", 10, "seconds"))},
    }
    if task_class == "bounded_successor_hold_recovery":
        base["successor_continuity"] = {"predecessor_work_id": base["work_id"], "successor_work_id": base["work_id"], "predecessor_root_budget": 1000, "successor_root_budget": 1000, "predecessor_remaining_budget": 900, "successor_remaining_budget": 800}
    base["resources"]["recovery_count"]["value"] = 0
    base.update(overrides)
    return base


def packet(rows):
    return {"schema_version": 1, "protocol_version": calibration.PROTOCOL_VERSION, "collection_mode": "manual_adapter_export", "samples": rows}


def main():
    rows = [sample(task, variant, index) for task in sorted(calibration.CLASSES) for variant in "ABC" for index in range(5)]
    result = calibration.run(packet(rows), NOW, 168)
    expect("all-five-classes", len(result["cohorts"]) == 5, result)
    expect("valid-A-B-C", all(c["sample_counts"] == {"A":5,"B":5,"C":5} for c in result["cohorts"]), result)
    expect("candidate-with-all-required-bands", all(c["candidate_recommendation"]["status"] == "candidate" and c["candidate_recommendation"]["max_age_hours"] and c["candidate_recommendation"]["root_budget_band"] for c in result["cohorts"]), result)
    expect("no-side-effects", result["mutation_performed"] is False and result["policy_write_performed"] is False and result["runtime_config_hook_mutation_performed"] is False, result)
    repeat = calibration.run(packet(rows), NOW, 168)
    expect("deterministic-output", json.dumps(result, sort_keys=True) == json.dumps(repeat, sort_keys=True), result)

    guarded = copy.deepcopy(rows)
    for row in guarded:
        if row["task_class"] == "attention_materiality" and row["variant"] == "C" and row["sample_id"].endswith("-1"):
            row["attention"] = {"outcome":"required", "category":"acceptance_evidence_conflict"}
        if row["task_class"] == "bounded_successor_hold_recovery" and row["variant"] == "C" and row["sample_id"].endswith("-4"):
            row["terminal_state"] = "held"; row["quality"] = {"passed":False,"reason":"declared outlier retained"}
    guarded_result = calibration.run(packet(guarded), NOW, 168)
    attention = next(c for c in guarded_result["cohorts"] if c["task_class"] == "attention_materiality")
    expect("attention-materiality", attention["attention_required_rate_C"] == .2, attention)
    expect("material-attention-holds-candidate", attention["candidate_recommendation"]["status"] == "candidate_hold", attention)
    recovery = next(c for c in guarded_result["cohorts"] if c["task_class"] == "bounded_successor_hold_recovery")
    expect("held-and-outlier-accounted", recovery["terminal_state_counts_C"]["held"] == 1 and recovery["outliers"], recovery)
    expect("failed-held-holds-candidate", recovery["candidate_recommendation"]["status"] == "candidate_hold", recovery)

    unavailable = copy.deepcopy(rows); unavailable[0]["resources"]["total_context_tokens"] = {"availability":"unavailable","value":None,"unit":"tokens","source":"adapter","observed_at":None,"reason":"not_exposed"}
    unavailable_result = calibration.run(packet(unavailable), NOW, 168)
    expect("unavailable-not-zero", unavailable_result["normalized_samples"][0]["resources"]["total_context_tokens"]["value"] is None, unavailable_result)
    expect("unavailable-accounted", next(c for c in unavailable_result["cohorts"] if c["task_class"] == rows[0]["task_class"])["metrics"]["A"]["total_context_tokens"]["n_unavailable"] == 1, unavailable_result)

    for name, mutate, error in [
        ("privacy", lambda x: x.update({"prompt":"secret"}), "privacy_forbidden_raw_content"),
        ("malformed-provenance", lambda x: x["provenance"].update({"evidence_anchor":"not-a-link"}), "malformed_provenance"),
        ("stale", lambda x: x["provenance"].update({"captured_at":"2026-07-01T00:00:00Z"}), "stale_provenance"),
        ("unbound-anchor", lambda x: x["anchors"].update({"work":"missing"}), "missing_or_unbound_durable_anchor"),
        ("root-budget", lambda x: x["root_budget"].update({"value":0}), "invalid_root_budget"),
        ("low-limit", lambda x: x.update({"policy_version":"low_limit_experiment"}), "low_limit_not_normal_policy_sample"),
        ("remaining-budget", lambda x: x["remaining_budget"].update({"value":1001}), "remaining_budget_exceeds_root_budget"),
    ]:
        bad = copy.deepcopy(rows); mutate(bad[0]); output = calibration.run(packet(bad), NOW, 168)
        expect(name, error in output["invalid_evidence"][0]["errors"], output)

    continuity = [sample("bounded_successor_hold_recovery", "C", 0)]
    continuity[0]["successor_continuity"]["successor_remaining_budget"] = 901
    continuity_result = calibration.run(packet(continuity), NOW, 168)
    expect("successor-continuity", "invalid_successor_budget_continuity" in continuity_result["invalid_evidence"][0]["errors"], continuity_result)
    counterfactual = [sample("single_session_baseline", "B", 0)]
    counterfactual[0]["resources"]["total_context_tokens"]["availability"] = "observed"
    counterfactual_result = calibration.run(packet(counterfactual), NOW, 168)
    expect("counterfactual-observed", "counterfactual_resources_must_not_be_observed:total_context_tokens" in counterfactual_result["invalid_evidence"][0]["errors"], counterfactual_result)

    incompatible = copy.deepcopy(rows); incompatible[1]["scenario"]["model_class"] = "different"
    incompatible_result = calibration.run(packet(incompatible), NOW, 168)
    expect("nonpooling", any(c["sample_counts"]["A"] < 5 for c in incompatible_result["cohorts"]), incompatible_result)
    insufficient = calibration.run(packet(rows[:3]), NOW, 168)
    expect("insufficient-n", insufficient["cohorts"][0]["candidate_recommendation"]["status"] == "candidate_hold", insufficient)

    absent_required = copy.deepcopy(rows); del absent_required[0]["resources"]["context_age_hours"]
    absent_result = calibration.run(packet(absent_required), NOW, 168)
    expect("missing-resource-fails-closed", "missing_required_resources:context_age_hours" in absent_result["invalid_evidence"][0]["errors"], absent_result)
    unknown = copy.deepcopy(rows); unknown[0]["unknown"] = True
    unknown_result = calibration.run(packet(unknown), NOW, 168)
    expect("schema-equivalent-unknown-rejected", "unknown_sample_field:unknown" in unknown_result["invalid_evidence"][0]["errors"], unknown_result)

    fixture = json.loads(FIXTURE.read_text())
    fixture_result = calibration.run(fixture, NOW, 168)
    expect("fixture-evidence-only", "fixture evidence only" in fixture_result["human_summary"], fixture_result)
    with tempfile.TemporaryDirectory() as directory:
        output_path = Path(directory) / "packet.json"
        completed = subprocess.run([sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--output", str(output_path), "--now", "2026-07-29T10:00:00Z"], text=True, capture_output=True, check=False)
        expect("explicit-output-only", completed.returncode == 0 and completed.stdout == "" and output_path.exists(), completed.stderr)
    print("af18 calibration tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
