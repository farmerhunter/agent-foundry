#!/usr/bin/env python3
"""Focused regressions for the static, read-only AF18 policy-v0 implementation."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "af18_policy_v0.py"
POLICY_PATH = ROOT / "policies" / "af18-policy-v0.yaml"
SCHEMA = ROOT / "schemas" / "af18-policy-v0.schema.yaml"
SPEC = importlib.util.spec_from_file_location("policy", SCRIPT)
policy = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(policy)


def expect(name: str, value: bool, detail: object) -> list[str]:
    if value:
        print(f"{name}: ok")
        return []
    return [f"{name}: {detail}"]


def work(**overrides: object) -> dict:
    value = {
        "work_id": "AF18-469-fixture",
        "root_budget_tokens": 100000,
        "profile": {"state": "inherits"},
        "requested_envelope": {"logical_model": {"state": "inherits"}, "reasoning": {"state": "inherits"}, "context_tokens": {"state": "inherits"}},
        "safety": {"allowlist_compliant": True, "risk_compliant": True, "privacy_compliant": True},
    }
    value.update(overrides)
    return value


def main() -> int:
    errors: list[str] = []
    source = policy.load_json_object(POLICY_PATH, "policy")
    policy.validate_policy(source)
    expected = {
        "economy": ("cost_optimized", "low", "gpt-5.6-luna", 12000, 12, 6, 60000),
        "normal": ("general", "medium", "gpt-5.6-terra", 24000, 24, 12, 150000),
        "performance": ("high_capability", "medium", "gpt-5.6-sol", 48000, 24, 20, 300000),
    }
    for name, values in expected.items():
        profile = source["profiles"][name]
        actual = (profile["logical_model"], profile["reasoning"], profile["adapter_mapping"]["codex"]["model_id"], profile["context_tokens"], profile["context_age_hours"], profile["context_turns"], profile["work_ceiling_tokens"])
        errors += expect(f"table-{name}", actual == values, profile)
    normal = policy.effective_snapshot(source, work())
    errors += expect("inherits-normal", normal["route_decision"] == "read_only_policy_ready" and normal["effective_controls"]["profile"]["state"] == "inherits" and normal["effective_controls"]["profile"]["value"] == "normal", normal)
    economy = policy.effective_snapshot(source, work(profile="economy", root_budget_tokens=90000))
    errors += expect("explicit-profile-min-cap", economy["effective_work_cap_tokens"] == 60000 and economy["effective_controls"]["profile"]["state"] == "explicit", economy)
    performance = policy.effective_snapshot(source, work(profile="performance", root_budget_tokens=70000))
    errors += expect("performance-default-min-cap", performance["route_decision"] == "read_only_policy_ready" and performance["effective_work_cap_tokens"] == 70000 and performance["adapter_metadata"]["model_id"] == "gpt-5.6-sol", performance)
    luna_evidence = {"classification": "low_risk_multi_step_execution_or_test", "risk_level": "low", "reason": "bounded low-risk test sequence"}
    luna_override = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_evidence=luna_evidence))
    errors += expect("luna-medium-override", luna_override["route_decision"] == "read_only_policy_ready" and luna_override["adapter_metadata"]["model_id"] == "gpt-5.6-luna" and luna_override["override_evidence"] == luna_evidence, luna_override)
    terra_evidence = {"classification": "small_time_sensitive_locally_ambiguous", "risk_level": "low", "reason": "time-sensitive local ambiguity"}
    terra_override = policy.effective_snapshot(source, work(requested_envelope={"logical_model": "general", "reasoning": "low", "context_tokens": 24000}, override_evidence=terra_evidence))
    errors += expect("terra-low-override", terra_override["route_decision"] == "read_only_policy_ready" and terra_override["adapter_metadata"]["model_id"] == "gpt-5.6-terra", terra_override)
    arbitrary_reason = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_reason="anything"))
    errors += expect("arbitrary-reason-holds", "missing_override_evidence" in arbitrary_reason["stop_conditions"], arbitrary_reason)
    wrong_category = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_evidence=terra_evidence))
    errors += expect("wrong-override-category-holds", "override_classification_mismatch" in wrong_category["stop_conditions"], wrong_category)
    missing_evidence = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}))
    errors += expect("missing-override-evidence-holds", "missing_override_evidence" in missing_evidence["stop_conditions"], missing_evidence)
    high_risk = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_evidence={**luna_evidence, "risk_level": "high"}))
    errors += expect("high-risk-override-holds", "override_risk_conflict" in high_risk["stop_conditions"], high_risk)
    privacy_conflict = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_evidence=luna_evidence, safety={"allowlist_compliant": True, "risk_compliant": True, "privacy_compliant": False}))
    errors += expect("privacy-conflict-override-holds", "privacy_not_confirmed" in privacy_conflict["stop_conditions"], privacy_conflict)
    conflicting_policy = policy.effective_snapshot(source, work(profile="economy", requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_evidence=luna_evidence, policy_constraints={"allow_work_reasoned_overrides": False}))
    errors += expect("conflicting-policy-override-holds", "override_conflicts_with_policy" in conflicting_policy["stop_conditions"], conflicting_policy)
    profile_mismatch = policy.effective_snapshot(source, work(requested_envelope={"logical_model": "cost_optimized", "reasoning": "medium", "context_tokens": 12000}, override_evidence=luna_evidence))
    errors += expect("override-profile-mismatch-holds", "override_profile_mismatch" in profile_mismatch["stop_conditions"], profile_mismatch)
    for label, envelope in (("high", {"logical_model": "general", "reasoning": "high", "context_tokens": 24000}), ("xhigh", {"logical_model": "general", "reasoning": "xhigh", "context_tokens": 24000}), ("pro", {"logical_model": "pro", "reasoning": "medium", "context_tokens": 24000}), ("gpt55", {"logical_model": "gpt-5.5", "reasoning": "medium", "context_tokens": 24000})):
        held = policy.effective_snapshot(source, work(requested_envelope=envelope, override_evidence=terra_evidence))
        errors += expect(f"unlisted-{label}-holds", held["route_decision"] == "hold_for_decision" and "human_attention_required_for_unlisted_model_or_effort" in held["stop_conditions"], held)
    unavailable = policy.effective_snapshot(source, work(requested_envelope={"logical_model": {"state": "unavailable"}}))
    errors += expect("unavailable-holds", unavailable["route_decision"] == "hold_for_decision", unavailable)
    unsafe = policy.effective_snapshot(source, work(safety={"allowlist_compliant": False, "risk_compliant": True, "privacy_compliant": True}))
    errors += expect("stricter-safety-prevails", "allowlist_not_confirmed" in unsafe["stop_conditions"], unsafe)
    risk = policy.effective_snapshot(source, work(safety={"allowlist_compliant": True, "risk_compliant": False, "privacy_compliant": True}))
    errors += expect("risk-prevails", "risk_not_confirmed" in risk["stop_conditions"], risk)
    malformed_mapping = policy.effective_snapshot(source, work(safety="not-an-object"))
    errors += expect("malformed-mapping-holds", "malformed_safety" in malformed_mapping["stop_conditions"], malformed_mapping)
    try:
        policy.effective_snapshot(source, work(root_budget_tokens=None))
        errors.append("missing-root-budget: accepted missing literal root budget")
    except policy.PolicyError:
        print("missing-root-budget: ok")
    schema = SCHEMA.read_text(encoding="utf-8")
    errors += expect("schema-boundaries", all(text in schema for text in ("root_budget_tokens", "emergency-only", "adapter metadata", "cost_optimized", "unavailable")), schema)
    malformed = copy.deepcopy(source)
    malformed["profiles"].pop("normal")
    try:
        policy.validate_policy(malformed)
        errors.append("malformed-policy: accepted malformed policy")
    except policy.PolicyError:
        print("malformed-policy: ok")
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "work.json"
        path.write_text(json.dumps(work()), encoding="utf-8")
        one = subprocess.run([sys.executable, str(SCRIPT), "--work-json", str(path), "--mode", "readout"], text=True, capture_output=True)
        two = subprocess.run([sys.executable, str(SCRIPT), "--work-json", str(path), "--mode", "readout"], text=True, capture_output=True)
        readout = json.loads(one.stdout)
        errors += expect("deterministic-privacy-safe-readout", one.returncode == 0 and one.stdout == two.stdout and all(key not in json.dumps(readout).lower() for key in ("prompt", "transcript", "secret")) and readout["adapter_mapping"]["model_id"] == "gpt-5.6-terra" and readout["mutation_performed"] is False and readout["dispatch_performed"] is False, readout)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("af18 policy-v0 tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
