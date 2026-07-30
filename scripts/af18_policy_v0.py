#!/usr/bin/env python3
"""Validate the static AF18 policy-v0 source and render read-only effective controls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "policies" / "af18-policy-v0.yaml"
PROFILE_NAMES = {"economy", "normal", "performance"}
MODEL_RANK = {"gpt-5.5": 55, "gpt-5.6-luna": 56, "gpt-5.6-terra": 56}
REASONING_RANK = {"low": 1, "medium": 2, "high": 3}
PRIVATE_KEYS = {"prompt", "body", "transcript", "secret", "token", "native_provider_id", "provider_id"}


class PolicyError(ValueError):
    pass


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyError(f"malformed {label}") from error
    if not isinstance(value, dict):
        raise PolicyError(f"{label} must be an object")
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("policy_id") != "af18-policy-v0" or policy.get("policy_version") != "v0":
        raise PolicyError("unsupported policy identity")
    if policy.get("default_profile") not in PROFILE_NAMES:
        raise PolicyError("missing or unsupported default_profile")
    profiles = policy.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != PROFILE_NAMES:
        raise PolicyError("policy profiles must be exactly economy, normal, performance")
    required = {"logical_model", "reasoning", "context_tokens", "context_age_hours", "context_turns", "work_ceiling_tokens"}
    for name, profile in profiles.items():
        if not isinstance(profile, dict) or not required.issubset(profile):
            raise PolicyError(f"malformed profile: {name}")
        if profile["logical_model"] not in MODEL_RANK or profile["reasoning"] not in REASONING_RANK:
            raise PolicyError(f"unsupported profile envelope: {name}")
        if any(not isinstance(profile[field], int) or profile[field] <= 0 for field in required - {"logical_model", "reasoning"}):
            raise PolicyError(f"invalid profile limits: {name}")
    safety = policy.get("safety")
    if not isinstance(safety, dict) or safety.get("model_ceiling") != "gpt-5.5" or safety.get("reasoning_ceiling") != "medium":
        raise PolicyError("malformed safety ceiling")
    low_limit = policy.get("compatibility", {}).get("low_limit")
    if not isinstance(low_limit, dict) or low_limit.get("status") != "emergency_only" or low_limit.get("normal_path_cap") is not False:
        raise PolicyError("malformed low_limit compatibility boundary")


def control(value: Any, inherited: Any, provenance: str) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("state") == "unavailable":
        return {"state": "unavailable", "value": None, "provenance": value.get("provenance", provenance)}
    if isinstance(value, dict) and value.get("state") == "inherits":
        return {"state": "inherits", "value": inherited, "provenance": value.get("provenance", provenance)}
    if value is None:
        return {"state": "inherits", "value": inherited, "provenance": provenance}
    return {"state": "explicit", "value": value, "provenance": provenance}


def complete_human_approval(approval: Any, work_id: Any) -> bool:
    if not isinstance(approval, dict):
        return False
    required = ("issue", "role", "model", "reasoning", "reason", "expiry")
    return approval.get("work_id") == work_id and all(approval.get(field) not in (None, "", [], {}) for field in required)


def request_exceeds_ceiling(model: str, reasoning: str) -> bool:
    return MODEL_RANK.get(model, 999) > MODEL_RANK["gpt-5.5"] or REASONING_RANK.get(reasoning, 999) > REASONING_RANK["medium"]


def effective_snapshot(policy: dict[str, Any], work: dict[str, Any]) -> dict[str, Any]:
    work_id = work.get("work_id")
    root_budget = work.get("root_budget_tokens")
    if not isinstance(work_id, str) or not work_id or not isinstance(root_budget, int) or root_budget <= 0:
        raise PolicyError("Work requires work_id and literal positive root_budget_tokens")
    raw_profile = work.get("profile")
    if isinstance(raw_profile, dict) and raw_profile.get("state") not in {"inherits", "unavailable"}:
        return hold_snapshot(policy, work_id, ["malformed_profile_control"], {})
    profile_control = control(raw_profile, policy["default_profile"], "policy.default_profile")
    if profile_control["state"] == "unavailable":
        return hold_snapshot(policy, work_id, ["profile_unavailable"], {"profile": profile_control})
    profile_name = profile_control["value"]
    if profile_name not in PROFILE_NAMES:
        return hold_snapshot(policy, work_id, ["unsupported_profile"], {"profile": profile_control})
    profile = policy["profiles"][profile_name]
    requested = work.get("requested_envelope", {})
    if not isinstance(requested, dict):
        return hold_snapshot(policy, work_id, ["malformed_requested_envelope"], {"profile": profile_control})
    model = control(requested.get("logical_model"), profile["logical_model"], f"profiles.{profile_name}.logical_model")
    reasoning = control(requested.get("reasoning"), profile["reasoning"], f"profiles.{profile_name}.reasoning")
    context = control(requested.get("context_tokens"), profile["context_tokens"], f"profiles.{profile_name}.context_tokens")
    if any(item["state"] == "unavailable" for item in (model, reasoning, context)):
        return hold_snapshot(policy, work_id, ["requested_envelope_unavailable"], {"profile": profile_control, "logical_model": model, "reasoning": reasoning, "context_tokens": context})
    stops: list[str] = []
    envelope_valid = isinstance(model["value"], str) and isinstance(reasoning["value"], str) and isinstance(context["value"], int) and context["value"] > 0
    if not envelope_valid or model["value"] not in MODEL_RANK or reasoning["value"] not in REASONING_RANK:
        stops.append("malformed_requested_envelope")
    if isinstance(context["value"], int) and context["value"] > profile["context_tokens"]:
        stops.append("context_exceeds_selected_profile")
    safety = work.get("safety")
    if not isinstance(safety, dict):
        stops.append("malformed_safety")
        safety = {}
    if safety.get("allowlist_compliant") is not True:
        stops.append("allowlist_not_confirmed")
    if safety.get("risk_compliant") is not True:
        stops.append("risk_not_confirmed")
    if safety.get("privacy_compliant") is not True:
        stops.append("privacy_not_confirmed")
    if envelope_valid and request_exceeds_ceiling(model["value"], reasoning["value"]) and not complete_human_approval(work.get("human_escalation_approval"), work_id):
        stops.append("human_approval_required_for_model_or_reasoning_escalation")
    controls = {"profile": profile_control, "logical_model": model, "reasoning": reasoning, "context_tokens": context}
    output = hold_snapshot(policy, work_id, stops, controls)
    output["effective_work_cap_tokens"] = min(root_budget, profile["work_ceiling_tokens"])
    output["root_budget_tokens"] = root_budget
    output["profile_ceiling_tokens"] = profile["work_ceiling_tokens"]
    return output


def hold_snapshot(policy: dict[str, Any], work_id: str, stops: list[str], controls: dict[str, Any]) -> dict[str, Any]:
    return {"policy_id": policy["policy_id"], "policy_version": policy["policy_version"], "work_id": work_id, "route_decision": "hold_for_decision" if stops else "read_only_policy_ready", "stop_conditions": stops, "effective_controls": controls, "mutation_performed": False, "dispatch_performed": False}


def human_readout(snapshot: dict[str, Any]) -> dict[str, Any]:
    controls = snapshot.get("effective_controls", {})
    return {
        "policy": f"{snapshot['policy_id']} {snapshot['policy_version']}",
        "work_id": snapshot["work_id"],
        "profile": controls.get("profile"),
        "effective_envelope": {key: controls.get(key) for key in ("logical_model", "reasoning", "context_tokens")},
        "effective_work_cap_tokens": snapshot.get("effective_work_cap_tokens"),
        "decision": snapshot["route_decision"],
        "why": snapshot["stop_conditions"] or ["Selected profile and stricter controls are satisfied."],
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate static AF18 policy-v0 and render a read-only effective-control snapshot.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--work-json", type=Path, required=True)
    parser.add_argument("--mode", choices=("snapshot", "readout"), default="snapshot")
    args = parser.parse_args()
    try:
        policy = load_json_object(args.policy, "policy")
        work = load_json_object(args.work_json, "Work")
        validate_policy(policy)
        snapshot = effective_snapshot(policy, work)
        print(json.dumps(human_readout(snapshot) if args.mode == "readout" else snapshot, ensure_ascii=False, sort_keys=True))
    except PolicyError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
