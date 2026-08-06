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
        "runtime_capabilities": {"observed_at": "2026-07-21T00:00:00Z", "mechanisms": {"create_thread": {"status": "supported", "supports_explicit_envelope": True, "effective_configuration": "unknown"}, "send_message_to_thread": {"status": "supported", "supports_explicit_envelope": True, "effective_configuration": "unknown"}, "spawn_agent": {"status": "supported", "supports_explicit_envelope": True, "effective_configuration": "unknown"}, "fork_thread": {"status": "supported", "supports_explicit_envelope": False, "effective_configuration": "unknown"}, "portable_prompt": {"status": "supported", "supports_explicit_envelope": False, "effective_configuration": "not_available"}, "worktree_batch": {"status": "supported", "supports_explicit_envelope": False, "effective_configuration": "unknown"}}},
    }


def run_fixture(data: dict) -> tuple[int, dict | str]:
    with tempfile.TemporaryDirectory(prefix="af18-route-") as tmp:
        path = Path(tmp) / "fixture.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([sys.executable, str(PLANNER), "--input-json", str(path), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            return result.returncode, result.stderr
        return 0, json.loads(result.stdout)


def run_fixture_with_tmp(data: dict) -> tuple[int, dict | str, Path]:
    with tempfile.TemporaryDirectory(prefix="af18-policy-lifecycle-") as raw:
        root = Path(raw)
        data = json.loads(json.dumps(data))
        lifecycle = data.setdefault("policy_lifecycle", {})
        paths = lifecycle.setdefault("paths", {})
        paths.setdefault("personal", str(root / "home" / ".agent-foundry" / "collaboration-routing-policy.yaml"))
        paths.setdefault("project_root", str(root / "project"))
        paths.setdefault("project", str(root / "project" / ".agent-foundry" / "collaboration-routing-policy.yaml"))
        path = root / "fixture.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([sys.executable, str(PLANNER), "--input-json", str(path), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            return result.returncode, result.stderr, root
        return 0, json.loads(result.stdout), root


def run_fixture_path(data: dict, fixture_path: Path) -> tuple[int, dict | str]:
    fixture_path.write_text(json.dumps(data), encoding="utf-8")
    completed = subprocess.run([sys.executable, str(PLANNER), "--input-json", str(fixture_path), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (completed.returncode, json.loads(completed.stdout)) if completed.returncode == 0 else (completed.returncode, completed.stderr)


def expect(name: str, condition: bool, detail: object) -> list[str]:
    if condition:
        print(f"{name}: ok")
        return []
    return [f"{name}: {detail}"]


def main() -> int:
    errors: list[str] = []
    schema = SCHEMA.read_text(encoding="utf-8")
    for anchor in ("PolicySet", "WorkUnit", "RoleContext", "RuntimeCapabilities", "RouteCandidate", "DispatchPlan", "OverrideGrant", "EvaluationRecord", "ConversationProjection", "policy_profile", "task_class", "provider, provider_slug, model, or model_slug"):
        errors.extend(expect(f"schema-{anchor}", anchor in schema, "missing schema anchor"))

    serial_fixture = base_fixture()
    code, output = run_fixture(serial_fixture)
    errors.extend(expect("serial-exit", code == 0, output))
    if code == 0:
        errors.extend(expect("serial-route", output["dispatch_plan"]["route_decision"] == "serial_current_session", output))
        errors.extend(expect("no-mutation", output["mutation_performed"] is False and output["dispatch_performed"] is False, output))
        errors.extend(expect("candidate-limit", len(output["route_candidates"]) <= 4, output))
        projection = output["conversation_projection"]
        errors.extend(expect("unsaved-normal-default", projection["effective_policy"]["profile"] == "normal" and projection["effective_policy"]["label"] == "正常" and projection["effective_policy"]["source"] == "unsaved_normal_default" and projection["effective_policy"]["fingerprint_or_unsaved_default"] == "unsaved-normal-default", projection))
        errors.extend(expect("fixed-profile-catalog", [item["label"] for item in projection["profile_catalog"]] == ["节俭", "正常", "高性能"], projection))
        errors.extend(expect("lifecycle-levels", {"collaboration_operating_mode", "execution_context_lifecycle", "bounded_work_unit_lifecycle", "policy_record_lifecycle", "next_action"}.issubset(set(projection["lifecycle"])), projection))
        errors.extend(expect("single-next-action", isinstance(projection["next_action"], str) and projection["next_action"] == projection["lifecycle"]["next_action"], projection))

    routine = base_fixture()
    routine["work_unit"].update({"task_class": "routine", "material_signals": []})
    code, output = run_fixture(routine)
    if code == 0:
        errors.extend(expect("routine-quiet", output["conversation_projection"]["emit_compact_marker"] is False and output["dispatch_plan"]["route_decision"] == "serial_current_session", output))

    setup_intent = base_fixture()
    setup_intent["policy_setup_requested"] = True
    code, output = run_fixture(setup_intent)
    if code == 0:
        intent = output["conversation_projection"]["policy_setup_intent"]
        errors.extend(expect("setup-intent-no-write", intent["requested"] is True and intent["apply_supported_now"] is False and intent["write_performed"] is False and output["conversation_projection"]["next_action"].startswith("Set up collaboration policy"), output))

    inspect_policy = base_fixture()
    inspect_policy["policy_lifecycle"] = {"action": "inspect", "scope": "project"}
    code, output, _ = run_fixture_with_tmp(inspect_policy)
    if code == 0:
        record = output["conversation_projection"]["policy_record"]
        errors.extend(expect("policy-inspect-read-only", output["mutation_performed"] is False and output["policy_lifecycle"]["write_performed"] is False and record["readback"]["validity"] == "missing", output))

    preview_policy = base_fixture()
    preview_policy["policy_lifecycle"] = {"action": "preview", "scope": "project", "profile": "performance"}
    code, output, _ = run_fixture_with_tmp(preview_policy)
    if code == 0:
        intent = output["conversation_projection"]["policy_setup_intent"]
        errors.extend(expect("policy-preview-no-write", intent["requested"] is True and intent["write_performed"] is False and output["policy_lifecycle"]["diff"]["after"]["profile"] == "performance", output))

    apply_policy = base_fixture()
    apply_policy["policy_lifecycle"] = {"action": "apply", "scope": "project", "profile": "economy", "confirmed": True}
    code, output, _ = run_fixture_with_tmp(apply_policy)
    if code == 0:
        lifecycle = output["policy_lifecycle"]
        projection = output["conversation_projection"]
        errors.extend(expect("policy-apply-one-write-readback", lifecycle["write_performed"] is True and lifecycle["readback"]["validity"] == "valid" and projection["effective_policy"]["source"] == "project" and projection["effective_policy"]["profile"] == "economy", output))
        errors.extend(expect("policy-effective-next-dispatch-project-scoped", projection["role_task_dispatch_policy"]["new_role_task_preference"] == "project_scoped_codex_task" and projection["role_task_dispatch_policy"]["project_id"] == "local-eb6e22ec0d00ef785d687022be1b433d", projection))

    unconfirmed_policy = base_fixture()
    unconfirmed_policy["policy_lifecycle"] = {"action": "apply", "scope": "personal", "profile": "normal", "confirmed": False}
    code, output, _ = run_fixture_with_tmp(unconfirmed_policy)
    if code == 0:
        errors.extend(expect("policy-apply-needs-one-confirmation", output["policy_lifecycle"]["write_performed"] is False and output["conversation_projection"]["policy_setup_intent"]["confirmation_required"] is True and output["conversation_projection"]["next_action"] == "Confirm once before writing the selected policy record.", output))

    invalid_lifecycle_profile = base_fixture()
    invalid_lifecycle_profile["policy_sources"] = {
        "personal": {
            "validity": "valid",
            "profile": "economy",
            "fingerprint": "sha256:prior-personal",
            "policy_set": invalid_lifecycle_profile["policy_set"],
        }
    }
    invalid_lifecycle_profile["policy_lifecycle"] = {"action": "apply", "scope": "project", "profile": "turbo", "confirmed": True}
    code, output, _ = run_fixture_with_tmp(invalid_lifecycle_profile)
    if code == 0:
        lifecycle = output["policy_lifecycle"]
        projection = output["conversation_projection"]
        errors.extend(
            expect(
                "policy-invalid-profile-preserves-prior",
                lifecycle["write_performed"] is False
                and lifecycle["failure"] == "invalid policy_lifecycle.profile"
                and lifecycle["invalid_input"]["field"] == "policy_lifecycle.profile"
                and lifecycle["diff"]["after"]["profile"] == "turbo"
                and lifecycle["diff"]["after"]["validity"] == "invalid"
                and lifecycle["readback"]["validity"] in {"missing", "valid", "invalid"}
                and projection["effective_policy"]["source"] == "personal"
                and projection["effective_policy"]["fingerprint_or_unsaved_default"] == "sha256:prior-personal"
                and projection["next_action"] == lifecycle["recovery_action"],
                output,
            )
        )
    else:
        errors.append(f"policy-invalid-profile-preserves-prior: {output}")

    with tempfile.TemporaryDirectory(prefix="af18-policy-write-fail-") as raw:
        root = Path(raw)
        blocked_path = root / "project" / ".agent-foundry" / "collaboration-routing-policy.yaml"
        blocked_path.mkdir(parents=True)
        failed_write = base_fixture()
        failed_write["policy_lifecycle"] = {
            "action": "apply",
            "scope": "project",
            "profile": "performance",
            "confirmed": True,
            "paths": {"project": str(blocked_path), "project_root": str(root / "project")},
        }
        code, output = run_fixture_path(failed_write, root / "fixture.json")
        if code == 0:
            projection = output["conversation_projection"]
            errors.extend(expect("policy-write-failure-preserves-prior", output["policy_lifecycle"]["write_performed"] is False and projection["effective_policy"]["source"] == "unsaved_normal_default" and "retry" in output["policy_lifecycle"]["next_action"], output))
        else:
            errors.append(f"policy-write-failure-preserves-prior: {output}")

    material = base_fixture()
    material["work_unit"].update({"task_class": "complex", "material_signals": ["cross_boundary", "contradictory_evidence"], "task_class_correction": {"task_class": "complex", "scope": "AF18-fixture", "expires_after_work_unit": True}})
    material["policy_sources"] = {"personal": {"validity": "valid", "profile": "performance", "fingerprint": "sha256:personal", "policy_set": material["policy_set"]}}
    code, output = run_fixture(material)
    if code == 0:
        projection = output["conversation_projection"]
        errors.extend(expect("material-correction", projection["work_unit"]["correction"]["applied"] is True and projection["recommendation"]["abstract_tier"] == {"capability": "frontier", "reasoning": "high"}, output))
        errors.extend(expect("material-marker", projection["emit_compact_marker"] is True, projection))

    retained = base_fixture()
    retained["policy_sources"] = {
        "project": {"validity": "drifted", "profile": "performance", "fingerprint": "sha256:drifted"},
        "personal": {"validity": "valid", "profile": "economy", "fingerprint": "sha256:prior", "policy_set": retained["policy_set"]},
    }
    code, output = run_fixture(retained)
    if code == 0:
        projection = output["conversation_projection"]
        errors.extend(expect("prior-policy-retention", projection["effective_policy"]["source"] == "personal" and projection["effective_policy"]["fingerprint_or_unsaved_default"] == "sha256:prior", output))
        errors.extend(expect("drifted-source-visible", any(item["validity"] == "drifted" for item in projection["evidence"]["policy_source_checks"]) and projection["recovery"]["writes_performed"] is False, output))
        errors.extend(expect("retained-policy-recovery-action", projection["next_action"] == "Inspect the invalid or drifted policy source; continue with the retained valid policy shown above", projection))

    invalid = base_fixture()
    invalid["policy_sources"] = {"project": {"validity": "invalid", "profile": "normal"}}
    code, output = run_fixture(invalid)
    if code == 0:
        errors.extend(expect("invalid-source-unsaved-recovery", output["conversation_projection"]["effective_policy"]["source"] == "unsaved_normal_default" and any("invalid or drifted" in attention for attention in output["conversation_projection"]["attention"]), output))

    precedence = base_fixture()
    precedence["policy_sources"] = {
        "current_work_unit_grant": {"validity": "valid", "profile": "performance", "fingerprint": "sha256:grant", "policy_set": precedence["policy_set"]},
        "project": {"validity": "valid", "profile": "economy", "fingerprint": "sha256:project", "policy_set": precedence["policy_set"]},
        "personal": {"validity": "valid", "profile": "normal", "fingerprint": "sha256:personal", "policy_set": precedence["policy_set"]},
    }
    code, output = run_fixture(precedence)
    if code == 0:
        errors.extend(expect("policy-precedence", output["conversation_projection"]["effective_policy"]["source"] == "current_work_unit_grant" and output["conversation_projection"]["effective_policy"]["fingerprint_or_unsaved_default"] == "sha256:grant", output))

    economy = base_fixture()
    economy["policy_sources"] = {"project": {"validity": "valid", "profile": "economy", "fingerprint": "sha256:economy", "policy_set": economy["policy_set"]}}
    economy["work_unit"].update({"task_class": "standard"})
    code, output = run_fixture(economy)
    if code == 0:
        errors.extend(expect("economy-mode", output["conversation_projection"]["effective_policy"]["profile"] == "economy" and output["conversation_projection"]["recommendation"]["abstract_tier"] == {"capability": "economy", "reasoning": "low"}, output))

    durable = base_fixture()
    durable["role_context"].update({"continuity_value": "high", "context_relevance": "high"})
    durable["work_unit"]["requires_explicit_envelope"] = True
    code, output = run_fixture(durable)
    if code == 0:
        errors.extend(expect("durable-route", output["dispatch_plan"]["route_decision"] == "reuse_relevant_thread" and output["dispatch_plan"]["selected_candidate"]["topology"] == "durable_thread", output))

    fresh = base_fixture()
    fresh["role_context"].update({"specialization_available": True, "continuity_value": "none", "context_relevance": "low"})
    code, output = run_fixture(fresh)
    if code == 0:
        errors.extend(expect("specialist-fresh-route", output["dispatch_plan"]["route_decision"] == "fresh_bounded_thread" and output["dispatch_plan"]["selected_candidate"]["topology"] == "fresh_thread", output))

    subagent = base_fixture()
    subagent["work_unit"]["safe_parallelism"] = True
    code, output = run_fixture(subagent)
    if code == 0:
        errors.extend(expect("bounded-subagent-route", output["dispatch_plan"]["route_decision"] == "bounded_subagent" and output["dispatch_plan"]["selected_candidate"]["topology"] == "subagent", output))
        errors.extend(expect("subagent-no-dispatch", output["mutation_performed"] is False and output["dispatch_performed"] is False, output))

    batch = base_fixture()
    batch["work_unit"]["batch_checkpoint_safe"] = True
    code, output = run_fixture(batch)
    if code == 0:
        errors.extend(expect("batch-checkpoint-route", output["dispatch_plan"]["route_decision"] == "batch_checkpoint" and output["conversation_projection"]["lifecycle"]["execution_context_lifecycle"]["eligible_actions"]["archive"] is True, output))

    unrelated = base_fixture()
    unrelated["role_context"].update({"continuity_value": "high", "context_relevance": "low"})
    code, output = run_fixture(unrelated)
    if code == 0:
        topologies = {item["topology"] for item in output["route_candidates"]}
        errors.extend(expect("unrelated-history-avoids-durable", "durable_thread" not in topologies and "fresh_thread" in topologies, output))
        errors.extend(expect("unrelated-history-serial", output["dispatch_plan"]["route_decision"] == "serial_current_session", output))

    review = base_fixture()
    review["role_context"].update({"required_role": "reviewer", "specialization_available": True, "independence_requirement": "separate_evidence"})
    code, output = run_fixture(review)
    if code == 0:
        errors.extend(expect("independent-review", output["dispatch_plan"]["route_decision"] == "fresh_bounded_thread" and output["dispatch_plan"]["selected_candidate"]["topology"] == "fresh_thread", output))

    omitted = base_fixture()
    omitted["role_context"].update({"specialization_available": True, "independence_requirement": "separate_context"})
    omitted["work_unit"]["requires_explicit_envelope"] = True
    omitted["runtime_capabilities"]["mechanisms"]["create_thread"]["supports_explicit_envelope"] = False
    code, output = run_fixture(omitted)
    if code == 0:
        errors.extend(expect("omitted-envelope-hold", output["dispatch_plan"]["route_decision"] == "hold_for_decision", output))
        errors.extend(expect("omitted-envelope-observable-unknown", output["conversation_projection"]["runtime_projection"]["observable"]["effective_configuration"] == "unknown", output))

    unknown_runtime = base_fixture()
    unknown_runtime["role_context"].update({"specialization_available": True})
    unknown_runtime["runtime_capabilities"]["mechanisms"]["create_thread"]["status"] = "unknown"
    code, output = run_fixture(unknown_runtime)
    if code == 0:
        errors.extend(expect("unknown-runtime-hold", output["dispatch_plan"]["route_decision"] == "hold_for_decision" and output["conversation_projection"]["runtime_projection"]["observable"]["status"] == "unknown", output))

    unsupported = base_fixture()
    unsupported["runtime_capabilities"]["mechanisms"]["fork_thread"]["status"] = "unsupported"
    code, output = run_fixture(unsupported)
    if code == 0:
        limitations = {item["mechanism"]: item for item in output["runtime_limitations"]}
        errors.extend(expect("heartbeat-non-enforcing", limitations["heartbeat"]["enforcement"] == "non_enforcing", limitations))
        errors.extend(expect("hook-unsupported", limitations["hook"]["enforcement"] == "unsupported", limitations))
        errors.extend(expect("custom-agent-unsupported", limitations["custom_agent"]["enforcement"] == "unsupported", limitations))

    escalation = base_fixture()
    escalation["role_context"].update({"specialization_available": True})
    escalation["work_unit"].update({"task_class": "complex", "material_signals": ["contradictory_evidence"]})
    escalation["attempt_state"] = {"outcome": "escalation_candidate", "escalation_count": 0, "evidence": "contradictory verification"}
    code, output = run_fixture(escalation)
    if code == 0:
        plan = output["dispatch_plan"]
        errors.extend(expect("escalation-reset", plan["requested_capability_tier"] == "frontier" and plan["reset"]["persists"] is False, plan))

    low_limit = base_fixture()
    low_limit["policy_sources"] = {"current_work_unit_grant": {"validity": "valid", "profile": "low_limit", "fingerprint": "sha256:low-limit", "policy_set": low_limit["policy_set"]}}
    low_limit["work_unit"].update({"task_class": "complex", "material_signals": ["cost_spike", "callback_recovery"]})
    code, output = run_fixture(low_limit)
    if code == 0:
        projection = output["conversation_projection"]
        errors.extend(expect("low-limit-mode", projection["effective_policy"]["profile"] == "low_limit" and projection["lifecycle"]["collaboration_operating_mode"]["temporary"] is True, output))
        errors.extend(expect("low-limit-tier", projection["recommendation"]["abstract_tier"] == {"capability": "economy", "reasoning": "low"}, output))

    human = base_fixture()
    human["work_unit"]["human_owned_actions"] = ["approve external cost"]
    code, output = run_fixture(human)
    if code == 0:
        errors.extend(expect("human-stop", output["dispatch_plan"]["route_decision"] == "hold_for_decision" and output["route_candidates"] == [], output))

    invalid_override = base_fixture()
    invalid_override["override_grant"] = {"active": True, "scope": "another-work-unit", "expires_after_work_unit": True, "reset_required": True}
    code, output = run_fixture(invalid_override)
    if code == 0:
        errors.extend(expect("override-scope-hold", output["dispatch_plan"]["route_decision"] == "hold_for_decision" and "scope does not match" in output["dispatch_plan"]["stop_conditions"][0], output))

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
