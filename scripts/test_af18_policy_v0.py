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
        "economy": ("gpt-5.6-luna", "low", 12000, 12, 6, 60000),
        "normal": ("gpt-5.5", "medium", 24000, 24, 12, 150000),
        "performance": ("gpt-5.6-terra", "medium", 48000, 24, 20, 300000),
    }
    for name, values in expected.items():
        profile = source["profiles"][name]
        errors += expect(f"table-{name}", tuple(profile[field] for field in ("logical_model", "reasoning", "context_tokens", "context_age_hours", "context_turns", "work_ceiling_tokens")) == values, profile)
    normal = policy.effective_snapshot(source, work())
    errors += expect("inherits-normal", normal["route_decision"] == "read_only_policy_ready" and normal["effective_controls"]["profile"]["state"] == "inherits" and normal["effective_controls"]["profile"]["value"] == "normal", normal)
    economy = policy.effective_snapshot(source, work(profile="economy", root_budget_tokens=90000))
    errors += expect("explicit-profile-min-cap", economy["effective_work_cap_tokens"] == 60000 and economy["effective_controls"]["profile"]["state"] == "explicit", economy)
    performance = policy.effective_snapshot(source, work(profile="performance", root_budget_tokens=70000, human_escalation_approval={"work_id": "AF18-469-fixture", "issue": 469, "role": "implementer", "model": "gpt-5.6-terra", "reasoning": "medium", "reason": "approved fixture", "expiry": "2026-08-01T00:00:00Z"}))
    errors += expect("stricter-ceiling-human-approval", performance["route_decision"] == "read_only_policy_ready" and performance["effective_work_cap_tokens"] == 70000, performance)
    escalation_hold = policy.effective_snapshot(source, work(profile="performance"))
    errors += expect("escalation-hold", "human_approval_required_for_model_or_reasoning_escalation" in escalation_hold["stop_conditions"], escalation_hold)
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
    errors += expect("schema-boundaries", all(text in schema for text in ("root_budget_tokens", "emergency-only", "adapter metadata", "unavailable")), schema)
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
        errors += expect("deterministic-privacy-safe-readout", one.returncode == 0 and one.stdout == two.stdout and all(key not in json.dumps(readout).lower() for key in ("prompt", "transcript", "secret", "native_provider_id")) and readout["mutation_performed"] is False and readout["dispatch_performed"] is False, readout)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("af18 policy-v0 tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
