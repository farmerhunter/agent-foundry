#!/usr/bin/env python3
"""Focused no-I/O regressions for bounded collaboration onboarding."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("onboarding", ROOT / "scripts" / "plan_bounded_collaboration_onboarding.py")
onboarding = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(onboarding)


def capability_set():
    return {"role_binding": {"status": "supported"}, "projections": {name: {"status": "supported"} for name in onboarding.PROJECTIONS}, "operations": {name: {"status": "supported"} for name in onboarding.CAPABILITIES}}


def fixture(**overrides):
    value = {"onboarding_version": onboarding.VERSION, "request": {"project_identity": {"project_id": "agent-foundry", "repository": "farmerhunter/agent-foundry", "integration_branch": "codex/integration"}, "onboarding_key": "onboard-agent-foundry-v1", "apply_authorized": False}, "runtime_capabilities": capability_set(), "role_hub": {"status": "missing"}, "existing_roles": [], "repository_state": {"dirty": True, "dirty_preserved": True}}
    value.update(overrides)
    return value


def expect(name, condition, value):
    if not condition:
        raise AssertionError(f"{name}: {value}")
    print(f"{name}: ok")


def receipt(item, status="applied", fingerprint=True):
    value = {"idempotency_key": item["idempotency_key"], "status": status, "receipt_ref": "adapter:receipt"}
    if fingerprint:
        value["operation_fingerprint"] = item["operation_fingerprint"]
    return value


def main():
    fresh = onboarding.plan(fixture())
    expect("fresh-rolehub-setup", fresh["state"] == "plan_ready" and {item["kind"] for item in fresh["operations"]} >= {"discover_role_hub", "create_role_hub", "create_durable_role", "navigate_role_hub"}, fresh)
    existing = [{"project_id": "agent-foundry", "role": "Coordinator", "role_ref": "opaque-coordinator", "durable_anchor": "issue:1", "state": "active", "legacy": False, "display_name": "old", "linked_to_role_hub": False}, {"project_id": "agent-foundry", "role": "Architect", "role_ref": "opaque-architect", "durable_anchor": "issue:2", "state": "active", "legacy": False, "display_name": "Architect", "linked_to_role_hub": True}]
    reuse = onboarding.plan(fixture(role_hub={"status": "active", "role_hub_ref": "opaque-hub"}, existing_roles=existing, request={**fixture()["request"], "role_display_names": {"Coordinator": "Project Coordinator"}}))
    expect("reuse-rename-link", reuse["state"] == "plan_ready" and {item["kind"] for item in reuse["operations"]} >= {"reuse_durable_role", "rename_role", "link_role", "navigate_role_hub"}, reuse)
    duplicate = onboarding.plan(fixture(existing_roles=[{"project_id": "agent-foundry", "role": "Coordinator", "role_ref": "a", "durable_anchor": "issue:1", "state": "active", "legacy": False}, {"project_id": "agent-foundry", "role": "Coordinator", "role_ref": "b", "durable_anchor": "issue:2", "state": "active", "legacy": False}]))
    expect("duplicate-hold", duplicate["state"] == "partial_hold" and "duplicate_coordinator_matches" in duplicate["stop_conditions"], duplicate)
    held = onboarding.plan(fixture(existing_roles=[{"project_id": "agent-foundry", "role": "Architect", "role_ref": "held", "durable_anchor": "issue:old", "state": "held", "legacy": False}]))
    expect("held-only-hold", held["state"] == "partial_hold" and "held_legacy_or_ambiguous_architect_match" in held["stop_conditions"], held)
    missing = onboarding.plan(fixture(runtime_capabilities={**capability_set(), "operations": {**capability_set()["operations"], "link": {"status": "unavailable"}}}))
    expect("required-capability-hold", missing["state"] == "partial_hold" and "link_capability_unavailable" in missing["stop_conditions"], missing)
    expect("retry-idempotence", fresh["operations"] == onboarding.plan(fixture())["operations"], fresh)
    all_receipts = [receipt(item) for item in fresh["operations"]]
    ready = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=all_receipts))
    expect("valid-receipts-ready", ready["state"] == "ready", ready)
    forged = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(item, fingerprint=False) for item in fresh["operations"]]))
    expect("forged-receipt-hold", forged["state"] == "partial_hold" and "forged_receipt_fingerprint" in forged["stop_conditions"], forged)
    unknown = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[{"idempotency_key": "forged", "status": "applied", "receipt_ref": "adapter:x", "operation_fingerprint": "sha256:x"}]))
    expect("unknown-receipt-hold", unknown["state"] == "partial_hold" and "unknown_receipt" in unknown["stop_conditions"], unknown)
    duplicate_receipt = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(fresh["operations"][0]), receipt(fresh["operations"][0])]))
    expect("duplicate-receipt-hold", duplicate_receipt["state"] == "partial_hold" and "duplicate_receipt" in duplicate_receipt["stop_conditions"], duplicate_receipt)
    missing_ref = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[{key: value for key, value in receipt(fresh["operations"][0]).items() if key != "receipt_ref"}]))
    expect("missing-receipt-ref-hold", missing_ref["state"] == "partial_hold" and "missing_receipt_ref" in missing_ref["stop_conditions"], missing_ref)
    successful = fresh["operations"][1]
    failed = fresh["operations"][2]
    partial = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(successful), receipt(failed, "failed")]))
    expect("success-then-failure-reverse-rollback", partial["state"] == "rollback_planned" and partial["rollback_operations"][0]["source_idempotency_key"] == successful["idempotency_key"] and partial["rollback_operations"][0]["kind"] == "mark_setup_incomplete", partial)
    rolled = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(successful), receipt(failed, "failed")], rollback_receipts=[{"source_idempotency_key": successful["idempotency_key"], "status": "applied", "receipt_ref": "adapter:rollback"}]))
    expect("rollback-readback", rolled["state"] == "rolled_back", rolled)
    privacy = onboarding.plan(fixture(extra={"transcript": "must-not-appear"}))
    expect("privacy-hold", privacy["state"] == "partial_hold" and privacy["summary"]["capability"] == "privacy_held", privacy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
