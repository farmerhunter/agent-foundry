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
SCHEMA = ROOT / "schemas" / "af18-calibration-protocol.schema.yaml"
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


def measurement(name, value, unit, variant, index, components=None):
    item = {"observation_id": f"{variant}-{index}-{name}", "availability": "estimated" if variant == "B" else "observed", "value": value + index, "unit": unit, "source": "counterfactual_model" if variant == "B" else "adapter_counter", "observed_at": "2026-07-29T09:00:00Z"}
    if components:
        item["observation_basis"] = "derived"
        item["derived_total_component_ids"] = [f"{variant}-{index}-{component}" for component in components]
    return item


def sample(task_class, variant, index=0, **overrides):
    route = {"single_session_baseline": "Implementer", "compact_cross_role": "Coordinator>Reviewer", "independent_review_or_test_handoff": "Implementer>Tester", "bounded_successor_hold_recovery": "Coordinator>Successor", "attention_materiality": "Coordinator>Human"}[task_class]
    pair_id = f"attention-{index}" if task_class == "attention_materiality" and variant in {"A", "C"} else None
    attention = {"outcome": "not_required", "category": None, "acknowledgement": {"availability": "unavailable", "value": None}, "pairing": {"pair_id": None, "evidence_anchor": None}}
    if task_class == "attention_materiality" and variant == "A":
        attention = {"outcome": "suppressed", "category": "attention-summary", "acknowledgement": {"availability": "unavailable", "value": None}, "pairing": {"pair_id": pair_id, "evidence_anchor": f"https://github.com/farmerhunter/agent-foundry/issues/457#pair-{index}"}}
    if task_class == "attention_materiality" and variant == "C":
        attention = {"outcome": "required", "category": "attention-summary", "acknowledgement": {"availability": "observed", "value": True}, "pairing": {"pair_id": pair_id, "evidence_anchor": f"https://github.com/farmerhunter/agent-foundry/issues/457#pair-{index}"}}
    resources = {name: measurement(name, value, unit, variant, index) for name, value, unit in (("input_tokens", 100, "tokens"), ("cached_input_tokens", 20, "tokens"), ("output_tokens", 40, "tokens"), ("reasoning_tokens", 30, "tokens"), ("tool_output_bytes", 80, "bytes"), ("context_age_hours", 1, "hours"), ("packet_bytes", 200, "bytes"), ("callback_count", 1, "count"), ("compact_rehydration_count", 1, "count"), ("full_rehydration_count", 0, "count"), ("retry_count", 0, "count"), ("recovery_count", 0, "count"), ("elapsed_seconds", 10, "seconds"))}
    resources["total_context_tokens"] = measurement("total_context_tokens", 120, "tokens", variant, index, ("input_tokens", "cached_input_tokens"))
    resources["cumulative_resource_tokens"] = measurement("cumulative_resource_tokens", 300, "tokens", variant, index, ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens"))
    base = {"sample_id": f"{task_class}-{variant}-{index}", "protocol_version": calibration.PROTOCOL_VERSION, "task_class": task_class, "variant": variant, "variant_declaration": {"route_kind": "counterfactual" if variant == "B" else "observed_normal_route"}, "scenario": {"scenario_id": task_class, "scenario_variant": "default", "objective_or_acceptance_fixture_id": f"fixture-{task_class}", "complexity": "small", "risk": "low", "role_route": route, "model_class": "standard", "quality_rubric_version": "v1", "canonical_allowed_tools": ["gh", "python3"], "measurement_window": {"definition": "execution-to-terminal"}, "root_budget_unit": "tokens", "anchor_type": "issue"}, "work_id": f"work-{task_class}-{index}", "execution_id": f"run-{task_class}-{variant}-{index}", "anchors": {"work": "https://github.com/farmerhunter/agent-foundry/issues/457", "execution": f"https://github.com/farmerhunter/agent-foundry/issues/457#{task_class}-{variant}-{index}", "context": "https://github.com/farmerhunter/agent-foundry/issues/457#context", **({"predecessor": "https://github.com/farmerhunter/agent-foundry/issues/457#predecessor", "successor": "https://github.com/farmerhunter/agent-foundry/issues/457#successor"} if task_class == "bounded_successor_hold_recovery" else {})}, "root_budget": {"value": 1000, "unit": "tokens"}, "remaining_budget": {"value": 800, "unit": "tokens"}, "policy_version": "normal-observation-v1", "provenance": {"source": "test-export", "collection_method": "manual_adapter_export", "captured_at": "2026-07-29T09:00:00Z", "evidence_anchor": "https://github.com/farmerhunter/agent-foundry/issues/457#evidence", "observation_kind": "counterfactual" if variant == "B" else "observed"}, "terminal_state": "completed", "quality": {"passed": True, "reason": "test"}, "attention": attention, "resources": resources}
    if task_class == "bounded_successor_hold_recovery":
        base["successor_continuity"] = {"predecessor_work_id": base["work_id"], "successor_work_id": base["work_id"], "predecessor_root_budget": 1000, "successor_root_budget": 1000, "predecessor_remaining_budget": 900, "successor_remaining_budget": 800}
    base.update(overrides)
    return base


def packet(rows):
    return {"schema_version": 1, "protocol_version": calibration.PROTOCOL_VERSION, "collection_mode": "manual_adapter_export", "samples": rows}


def cohort(result, task_class):
    return next(item for item in result["cohorts"] if item["task_class"] == task_class)


def main():
    rows = [sample(task, variant, index) for task in sorted(calibration.CLASSES) for variant in "ABC" for index in range(5)]
    result = calibration.run(packet(rows), NOW, 168)
    expect("all-five-classes", len(result["cohorts"]) == 5, result)
    expect("candidate-names-only", all(item["candidate_recommendation"]["candidate_status"] == "candidate" and item["candidate_recommendation"]["candidate_root_budget_band"] for item in result["cohorts"]), result)
    expect("no-side-effects", result["mutation_performed"] is False and result["policy_write_performed"] is False and result["runtime_config_hook_mutation_performed"] is False, result)
    attention = cohort(result, "attention_materiality")
    expect("paired-suppressed-material-rate", attention["attention_required_rate_C"] == 1 and attention["attention_pair_count"] == 5 and attention["attention_material_pair_count"] == 5, attention)
    expect("material-does-not-hold", attention["candidate_recommendation"]["candidate_status"] == "candidate", attention)
    recovery = cohort(result, "bounded_successor_hold_recovery")
    expect("recovery-count-reported-no-hold", recovery["metrics"]["C"]["recovery_count"]["n_observed"] == 5 and recovery["candidate_recommendation"]["candidate_status"] == "candidate", recovery)
    expect("deterministic-output", json.dumps(result, sort_keys=True) == json.dumps(calibration.run(packet(rows), NOW, 168), sort_keys=True), result)

    declared_roots = copy.deepcopy(rows)
    for index, row in enumerate(item for item in declared_roots if item["task_class"] == "single_session_baseline" and item["variant"] == "C"):
        row["root_budget"]["value"] = 21000 + index * 1000
    root_candidate = cohort(calibration.run(packet(declared_roots), NOW, 168), "single_session_baseline")["candidate_recommendation"]["candidate_root_budget_band"]
    expect("candidate-root-budget-from-C-cumulative", root_candidate["max"] == 304 and root_candidate["max"] != 25000, root_candidate)

    unavailable = copy.deepcopy(rows)
    unavailable[0]["resources"]["tool_output_bytes"] = {"observation_id": "unavailable-tool", "availability": "unavailable", "value": None, "unit": "bytes", "source": "adapter", "observed_at": None, "reason": "not_exposed"}
    unavailable_result = calibration.run(packet(unavailable), NOW, 168)
    expect("unavailable-not-zero-counted", cohort(unavailable_result, rows[0]["task_class"])["metrics"]["A"]["tool_output_bytes"]["n_unavailable"] == 1, unavailable_result)

    unavailable_cumulative = copy.deepcopy(rows)
    cumulative_target = next(row for row in unavailable_cumulative if row["task_class"] == rows[0]["task_class"] and row["variant"] == "C")
    cumulative_target["resources"]["cumulative_resource_tokens"].update({"availability": "unavailable", "value": None, "observed_at": None, "reason": "not_exposed"})
    unavailable_cumulative_result = calibration.run(packet(unavailable_cumulative), NOW, 168)
    unavailable_cumulative_cohort = cohort(unavailable_cumulative_result, rows[0]["task_class"])
    expect("unavailable-cumulative-counted", unavailable_cumulative_cohort["metrics"]["C"]["cumulative_resource_tokens"]["n_unavailable"] == 1 and unavailable_cumulative_cohort["metrics"]["C"]["cumulative_resource_tokens"]["n_observed"] == 4, unavailable_cumulative_result)
    expect("unavailable-cumulative-holds-explicitly", unavailable_cumulative_cohort["candidate_recommendation"]["candidate_status"] == "candidate_hold" and "insufficient_observed_C_cumulative_resource_tokens" in unavailable_cumulative_cohort["candidate_recommendation"]["candidate_hold_reasons"], unavailable_cumulative_result)

    for name, mutate, error in [
        ("absent-resource-key", lambda x: x["resources"].pop("input_tokens"), "missing_required_resources:input_tokens"),
        ("malformed-resource-key", lambda x: x["resources"].update({"unexpected_tokens": {}}), "unknown_resources_field:unexpected_tokens"),
        ("absent-derived-components", lambda x: x["resources"]["cumulative_resource_tokens"].pop("derived_total_component_ids"), "missing_derived_total_component_ids:cumulative_resource_tokens"),
        ("unknown-derived-component", lambda x: x["resources"]["cumulative_resource_tokens"].update({"derived_total_component_ids": ["not-an-observation"]}), "unknown_derived_total_component_ids:cumulative_resource_tokens"),
        ("unavailable-with-zero", lambda x: x["resources"]["input_tokens"].update({"availability": "unavailable", "value": 0, "observed_at": None, "reason": "not_exposed"}), "unavailable_measurement_must_be_null_with_reason:input_tokens"),
        ("unavailable-without-reason", lambda x: x["resources"]["input_tokens"].update({"availability": "unavailable", "value": None, "observed_at": None, "reason": None}), "unavailable_measurement_must_be_null_with_reason:input_tokens"),
        ("derived-unavailable", lambda x: (x["resources"]["input_tokens"].update({"availability": "unavailable", "value": None, "observed_at": None, "reason": "not_exposed"}), x["resources"]["cumulative_resource_tokens"].update({"availability": "estimated"})), "derived_total_must_be_unavailable_with_unavailable_component:cumulative_resource_tokens"),
        ("independent-with-components", lambda x: x["resources"]["cumulative_resource_tokens"].update({"observation_basis": "independent_observed"}), "derived_components_require_derived_basis:cumulative_resource_tokens"),
        ("privacy", lambda x: x.update({"prompt": "secret"}), "privacy_forbidden_raw_content"),
        ("low-limit", lambda x: x.update({"policy_version": "low_limit_experiment"}), "low_limit_not_normal_policy_sample"),
    ]:
        bad = copy.deepcopy(rows); mutate(bad[0]); output = calibration.run(packet(bad), NOW, 168)
        expect(name, error in output["invalid_evidence"][0]["errors"], output)

    for name, mutate, reason in [
        ("missing-pair", lambda x: x["attention"]["pairing"].update({"pair_id": "missing"}), "attention_pairing_missing_required_pair"),
        ("mismatched-pair", lambda x: x["attention"]["pairing"].update({"evidence_anchor": "https://github.com/farmerhunter/agent-foundry/issues/457#different"}), "attention_pairing_anchor_conflict"),
        ("category-conflict", lambda x: x["attention"].update({"category": "different-summary"}), "attention_category_conflict"),
        ("acknowledgement-conflict", lambda x: x["attention"].update({"acknowledgement": {"availability": "unavailable", "value": None}}), "attention_acknowledgement_conflict"),
    ]:
        conflicted = copy.deepcopy(rows)
        target = next(row for row in conflicted if row["task_class"] == "attention_materiality" and row["variant"] == ("A" if name == "category-conflict" else "C"))
        mutate(target)
        candidate = cohort(calibration.run(packet(conflicted), NOW, 168), "attention_materiality")["candidate_recommendation"]
        expect(name, candidate["candidate_status"] == "candidate_hold" and reason in candidate["candidate_hold_reasons"], candidate)

    protocol_mismatch = copy.deepcopy(rows)
    protocol_mismatch[0]["protocol_version"] = "other-protocol"
    protocol_result = calibration.run(packet(protocol_mismatch), NOW, 168)
    expect("comparability-protocol-mismatch-rejected", "protocol_version_mismatch" in protocol_result["invalid_evidence"][0]["errors"], protocol_result)
    expect("comparability-protocol-not-split", len(protocol_result["cohorts"]) == 5, protocol_result)

    task_class_mismatch = copy.deepcopy(rows)
    task_class_mismatch[0]["task_class"] = "not-a-declared-class"
    task_class_result = calibration.run(packet(task_class_mismatch), NOW, 168)
    expect("comparability-task-class-rejected", "unknown_task_class" in task_class_result["invalid_evidence"][0]["errors"], task_class_result)
    expect("comparability-task-class-not-split", len(task_class_result["cohorts"]) == 5, task_class_result)

    root_unit_mismatch = copy.deepcopy(rows)
    root_unit_mismatch[0]["scenario"]["root_budget_unit"] = "bytes"
    root_unit_result = calibration.run(packet(root_unit_mismatch), NOW, 168)
    expect("comparability-root-budget-unit-mismatch-rejected", "root_budget_unit_mismatch" in root_unit_result["invalid_evidence"][0]["errors"], root_unit_result)
    expect("comparability-root-budget-unit-not-split", len(root_unit_result["cohorts"]) == 5, root_unit_result)

    expect("comparability-boundary-encoded", set(calibration.PACKET_GLOBAL_OR_VALIDITY_CONSTRAINED) == {"task_class", "protocol_version", "root_budget_unit"}, calibration.PACKET_GLOBAL_OR_VALIDITY_CONSTRAINED)

    independent_total = copy.deepcopy(rows)
    independent_total[0]["resources"]["total_context_tokens"].pop("derived_total_component_ids")
    independent_total[0]["resources"]["total_context_tokens"]["observation_basis"] = "independent_observed"
    independent_result = calibration.run(packet(independent_total), NOW, 168)
    expect("independent-total-valid", not independent_result["invalid_evidence"], independent_result)

    schema_text = SCHEMA.read_text(encoding="utf-8")
    expect("schema-unavailable-null-reason", "value: {type: 'null'}" in schema_text and "reason: {enum: [not_exposed, redacted, not_collected, invalid]}" in schema_text, schema_text)
    expect("schema-derived-total-reference", "total_context_tokens: {$ref: '#/$defs/derived_total_measurement'}" in schema_text and "cumulative_resource_tokens: {$ref: '#/$defs/derived_total_measurement'}" in schema_text, schema_text)
    expect("schema-independent-total-excludes-components", "observation_basis: {enum: [derived, independent_observed]}" in schema_text and "not: {required: [derived_total_component_ids]}" in schema_text, schema_text)

    for dimension in ("scenario_id", "scenario_variant", "objective_or_acceptance_fixture_id", "complexity", "risk", "role_route", "model_class", "quality_rubric_version", "policy_version", "canonical_allowed_tools", "measurement_window", "anchor_type"):
        split = copy.deepcopy(rows)
        target = next(row for row in split if row["task_class"] == "single_session_baseline" and row["variant"] == "A")
        if dimension == "policy_version":
            target[dimension] = "normal-observation-v2"
        elif dimension == "canonical_allowed_tools":
            target["scenario"][dimension] = ["gh"]
        elif dimension == "measurement_window":
            target["scenario"][dimension]["definition"] = "other-window"
        else:
            target["scenario"][dimension] = "different"
        split_result = calibration.run(packet(split), NOW, 168)
        expect(f"comparability-splits-{dimension}", len([item for item in split_result["cohorts"] if item["task_class"] == "single_session_baseline"]) == 2, split_result)

    fixture = json.loads(FIXTURE.read_text())
    fixture_result = calibration.run(fixture, NOW, 168)
    expect("fixture-evidence-only", "fixture evidence only" in fixture_result["human_summary"], fixture_result)
    fixture_candidate = fixture_result["cohorts"][0]["candidate_recommendation"]
    expect("fixture-hold-only-insufficient-sample", fixture_candidate["candidate_status"] == "candidate_hold" and fixture_candidate["candidate_hold_reasons"] == ["insufficient_observed_C_cumulative_resource_tokens", "requires_at_least_five_valid_A_B_C_rows"], fixture_candidate)
    with tempfile.TemporaryDirectory() as directory:
        output_path = Path(directory) / "packet.json"
        completed = subprocess.run([sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--output", str(output_path), "--now", "2026-07-29T10:00:00Z"], text=True, capture_output=True, check=False)
        expect("explicit-output-only", completed.returncode == 0 and completed.stdout == "" and output_path.exists(), completed.stderr)
    print("af18 calibration tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
