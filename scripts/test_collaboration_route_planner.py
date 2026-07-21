#!/usr/bin/env python3
"""Fixture regressions for the AF18 portable route planner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "scripts" / "plan_collaboration_routes.py"
SCHEMA = ROOT / "schemas" / "collaboration-routing-policy.schema.yaml"


def base_fixture() -> dict:
    return {
        "policy_set": {
            "schema_version": 1,
            "policy_id": "af18-test",
            "quality_floor": {"required_verification": "task_risk_based"},
            "automatic_budget": {"max_escalations_per_work_unit": 1},
            "allowed_tiers": {"capability": ["economy", "balanced", "frontier"], "reasoning": ["low", "medium", "high"]},
            "enforcement": {"mode": "advisory"},
        },
        "work_unit": {"work_unit_id": "AF18-fixture", "purpose": "bounded planner fixture", "risk": "medium", "ambiguity": "low", "verification_oracle": "fixture assertions", "stop_conditions": ["contract drift"]},
        "role_context": {"required_role": "implementer", "specialization_available": False, "continuity_value": "none", "context_relevance": "low", "independence_requirement": "none"},
        "runtime_capabilities": {"observed_at": "2026-07-21T00:00:00Z", "mechanisms": {"create_thread": {"status": "supported", "supports_explicit_envelope": True, "effective_configuration": "unknown"}, "send_message_to_thread": {"status": "supported", "supports_explicit_envelope": True, "effective_configuration": "unknown"}, "spawn_agent": {"status": "supported", "supports_explicit_envelope": True, "effective_configuration": "unknown"}, "fork_thread": {"status": "supported", "supports_explicit_envelope": False, "effective_configuration": "unknown"}, "portable_prompt": {"status": "supported", "supports_explicit_envelope": False, "effective_configuration": "not_available"}}},
    }


def run_fixture(data: dict) -> tuple[int, dict | str]:
    with tempfile.TemporaryDirectory(prefix="af18-route-") as tmp:
        path = Path(tmp) / "fixture.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([sys.executable, str(PLANNER), "--input-json", str(path), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            return result.returncode, result.stderr
        return 0, json.loads(result.stdout)


def expect(name: str, condition: bool, detail: object) -> list[str]:
    if condition:
        print(f"{name}: ok")
        return []
    return [f"{name}: {detail}"]


def main() -> int:
    errors: list[str] = []
    schema = SCHEMA.read_text(encoding="utf-8")
    for anchor in ("PolicySet", "WorkUnit", "RoleContext", "RuntimeCapabilities", "RouteCandidate", "DispatchPlan", "OverrideGrant", "EvaluationRecord", "provider, provider_slug, model, or model_slug"):
        errors.extend(expect(f"schema-{anchor}", anchor in schema, "missing schema anchor"))

    no_dispatch = base_fixture()
    code, output = run_fixture(no_dispatch)
    errors.extend(expect("no-dispatch-exit", code == 0, output))
    if code == 0:
        errors.extend(expect("no-dispatch", output["dispatch_plan"]["route_decision"] == "no_dispatch", output))
        errors.extend(expect("no-mutation", output["mutation_performed"] is False and output["dispatch_performed"] is False, output))
        errors.extend(expect("candidate-limit", len(output["route_candidates"]) <= 4, output))

    durable = base_fixture()
    durable["role_context"].update({"continuity_value": "high", "context_relevance": "high"})
    durable["work_unit"]["requires_explicit_envelope"] = True
    code, output = run_fixture(durable)
    if code == 0:
        errors.extend(expect("durable-route", output["dispatch_plan"]["selected_candidate"]["topology"] == "durable_thread", output))

    fresh = base_fixture()
    fresh["role_context"].update({"specialization_available": True, "continuity_value": "none", "context_relevance": "low"})
    code, output = run_fixture(fresh)
    if code == 0:
        errors.extend(expect("specialist-fresh-route", output["dispatch_plan"]["selected_candidate"]["topology"] == "fresh_thread", output))

    unrelated = base_fixture()
    unrelated["role_context"].update({"continuity_value": "high", "context_relevance": "low"})
    code, output = run_fixture(unrelated)
    if code == 0:
        topologies = {item["topology"] for item in output["route_candidates"]}
        errors.extend(expect("unrelated-history-avoids-durable", "durable_thread" not in topologies and "fresh_thread" in topologies, output))
        errors.extend(expect("unrelated-history-no-dispatch", output["dispatch_plan"]["route_decision"] == "no_dispatch", output))

    review = base_fixture()
    review["role_context"].update({"required_role": "reviewer", "specialization_available": True, "independence_requirement": "separate_evidence"})
    code, output = run_fixture(review)
    if code == 0:
        errors.extend(expect("independent-review", output["dispatch_plan"]["selected_candidate"]["topology"] == "fresh_thread", output))

    omitted = base_fixture()
    omitted["role_context"].update({"specialization_available": True, "independence_requirement": "separate_context"})
    omitted["work_unit"]["requires_explicit_envelope"] = True
    omitted["runtime_capabilities"]["mechanisms"]["create_thread"]["supports_explicit_envelope"] = False
    code, output = run_fixture(omitted)
    if code == 0:
        errors.extend(expect("omitted-envelope-human-stop", output["dispatch_plan"]["route_decision"] == "human_stop", output))

    unsupported = base_fixture()
    unsupported["runtime_capabilities"]["mechanisms"]["fork_thread"]["status"] = "unsupported"
    code, output = run_fixture(unsupported)
    if code == 0:
        fork = next(item for item in output["route_candidates"] if item["topology"] == "fork")
        errors.extend(expect("fork-non-enforcing", fork["eligible"] is False and fork["runtime_mapping"]["enforcement"] == "enforcement_not_available", fork))
        limitations = {item["mechanism"]: item for item in output["runtime_limitations"]}
        errors.extend(expect("heartbeat-non-enforcing", limitations["heartbeat"]["enforcement"] == "non_enforcing", limitations))
        errors.extend(expect("hook-unsupported", limitations["hook"]["enforcement"] == "unsupported", limitations))
        errors.extend(expect("custom-agent-unsupported", limitations["custom_agent"]["enforcement"] == "unsupported", limitations))

    escalation = base_fixture()
    escalation["role_context"].update({"specialization_available": True})
    escalation["attempt_state"] = {"outcome": "escalation_candidate", "escalation_count": 0, "evidence": "contradictory verification"}
    code, output = run_fixture(escalation)
    if code == 0:
        plan = output["dispatch_plan"]
        errors.extend(expect("escalation-reset", plan["requested_capability_tier"] == "frontier" and plan["reset"]["persists"] is False, plan))

    human = base_fixture()
    human["work_unit"]["human_owned_actions"] = ["approve external cost"]
    code, output = run_fixture(human)
    if code == 0:
        errors.extend(expect("human-stop", output["dispatch_plan"]["route_decision"] == "human_stop" and output["route_candidates"] == [], output))

    invalid_override = base_fixture()
    invalid_override["override_grant"] = {"active": True, "scope": "another-work-unit", "expires_after_work_unit": True, "reset_required": True}
    code, output = run_fixture(invalid_override)
    if code == 0:
        errors.extend(expect("override-scope-human-stop", output["dispatch_plan"]["route_decision"] == "human_stop" and "scope does not match" in output["dispatch_plan"]["stop_conditions"][0], output))

    forbidden = base_fixture()
    forbidden["policy_set"]["model_slug"] = "not-portable"
    code, output = run_fixture(forbidden)
    errors.extend(expect("portable-policy-rejects-model", code != 0 and "forbids provider/model identifiers" in str(output), output))

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
