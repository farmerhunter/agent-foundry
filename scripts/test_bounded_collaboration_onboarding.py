#!/usr/bin/env python3
"""Focused, no-I/O regression tests for bounded collaboration onboarding."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("onboarding", ROOT / "scripts" / "plan_bounded_collaboration_onboarding.py")
onboarding = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(onboarding)


def fixture(**overrides):
    value = {"onboarding_version": onboarding.VERSION, "request": {"project_identity": {"project_id": "agent-foundry", "repository": "farmerhunter/agent-foundry", "integration_branch": "codex/integration"}, "onboarding_key": "onboard-agent-foundry-v1", "apply_authorized": False}, "runtime_capabilities": {"role_binding": {"status": "supported"}}, "existing_roles": [], "repository_state": {"dirty": True, "dirty_preserved": True}}
    value.update(overrides)
    return value


def expect(name, condition, value):
    if not condition:
        raise AssertionError(f"{name}: {value}")
    print(f"{name}: ok")


def main():
    fresh = onboarding.plan(fixture())
    expect("fresh-setup", fresh["state"] == "plan_ready" and [x["role"] for x in fresh["operations"]] == ["Coordinator", "Architect"], fresh)
    reuse = onboarding.plan(fixture(existing_roles=[{"project_id": "agent-foundry", "role": "Coordinator", "role_ref": "opaque-coordinator", "durable_anchor": "issue:1", "state": "active", "legacy": False}, {"project_id": "agent-foundry", "role": "Architect", "role_ref": "opaque-architect", "durable_anchor": "issue:2", "state": "active", "legacy": False}]))
    expect("unique-reuse", reuse["state"] == "plan_ready" and len(reuse["summary"]["reused"]) == 2, reuse)
    duplicate = onboarding.plan(fixture(existing_roles=[{"project_id": "agent-foundry", "role": "Coordinator", "role_ref": "a", "durable_anchor": "issue:1", "state": "active", "legacy": False}, {"project_id": "agent-foundry", "role": "Coordinator", "role_ref": "b", "durable_anchor": "issue:2", "state": "active", "legacy": False}]))
    expect("duplicate-hold", duplicate["state"] == "partial_hold" and "duplicate_coordinator_matches" in duplicate["stop_conditions"], duplicate)
    legacy = onboarding.plan(fixture(existing_roles=[{"project_id": "agent-foundry", "role": "Architect", "role_ref": "legacy", "durable_anchor": "issue:old", "state": "historical_reference", "legacy": True}]))
    expect("legacy-hold", legacy["state"] == "partial_hold" and "legacy_adoption_requires_explicit_human_review" in legacy["stop_conditions"], legacy)
    unavailable = onboarding.plan(fixture(runtime_capabilities={"role_binding": {"status": "unavailable"}}))
    expect("missing-capability", unavailable["state"] == "partial_hold" and unavailable["summary"]["capability"] == "unavailable", unavailable)
    expect("retry-idempotence", fresh["operations"] == onboarding.plan(fixture())["operations"], fresh)
    failed_key = fresh["operations"][0]["idempotency_key"]
    partial = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[{"idempotency_key": failed_key, "status": "failed"}]))
    expect("partial-failure", partial["state"] == "rollback_planned" and partial["rollback_operations"], partial)
    rolled_back = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[{"idempotency_key": failed_key, "status": "failed"}], rollback_receipts=[{"idempotency_key": failed_key, "status": "applied"}]))
    expect("rollback-readback", rolled_back["state"] == "rolled_back", rolled_back)
    dirty = onboarding.plan(fixture(repository_state={"dirty": True, "dirty_preserved": False}))
    expect("dirty-preservation", dirty["state"] == "partial_hold", dirty)
    privacy = onboarding.plan(fixture(extra={"transcript": "must-not-appear"}))
    expect("privacy-hold", privacy["state"] == "partial_hold" and privacy["summary"]["capability"] == "privacy_held", privacy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
