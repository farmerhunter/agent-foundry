#!/usr/bin/env python3
"""Focused no-I/O regressions for bounded collaboration onboarding."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = yaml.safe_load((ROOT / "schemas" / "bounded-collaboration-onboarding.schema.yaml").read_text(encoding="utf-8"))
spec = importlib.util.spec_from_file_location("onboarding", ROOT / "scripts" / "plan_bounded_collaboration_onboarding.py")
onboarding = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(onboarding)


def capability_set():
    projections = {name: {"status": "supported"} for name in onboarding.PROJECTIONS}
    projections["scheduler"] = {"status": "supported", "binding_ref": "scheduler:bound", "binding_status": "bound"}
    projections["transient_template"] = {"status": "supported", "template_refs": {role: f"template:{role}" for role in onboarding.TRANSIENT_ROLES}}
    return {"role_binding": {"status": "supported"}, "projections": projections, "operations": {name: {"status": "supported"} for name in onboarding.CAPABILITIES}}


def fixture(**overrides):
    value = {"onboarding_version": onboarding.VERSION, "request": {"project_identity": {"project_id": "agent-foundry", "repository": "farmerhunter/agent-foundry", "integration_branch": "codex/integration"}, "onboarding_key": "onboard-agent-foundry-v1", "apply_authorized": False}, "runtime_capabilities": capability_set(), "role_hub": {"status": "missing"}, "current_thread": {"eligible": False, "current_thread_ref": "opaque-current", "name": "Current"}, "existing_roles": [], "repository_state": {"dirty": True, "dirty_preserved": True}}
    value.update(overrides)
    return value


def expect(name, condition, value):
    if not condition:
        raise AssertionError(f"{name}: {value}")
    print(f"{name}: ok")


def receipt(item, status="applied", fingerprint=True):
    value = {"idempotency_key": item["idempotency_key"], "status": status, "receipt_ref": "adapter:receipt", "result_ref": f"adapter:{item['subject']}"}
    if fingerprint:
        value["operation_fingerprint"] = item["operation_fingerprint"]
    return value


def rollback_receipt(item, status="applied"):
    return {"source_idempotency_key": item["source_idempotency_key"], "status": status, "receipt_ref": "adapter:rollback", "source_operation_fingerprint": item["source_operation_fingerprint"], "rollback_fingerprint": item["rollback_fingerprint"]}


def schema_expect(name, value):
    jsonschema.Draft202012Validator(SCHEMA).validate(value)
    print(f"schema-{name}: ok")


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
    expect("valid-receipts-ready", ready["state"] == "ready" and ready["summary"]["active_navigation"]["coordinator_ref"] == "adapter:Coordinator" and set(ready["summary"]["projections"]["transient_templates"]) == set(onboarding.TRANSIENT_ROLES), ready)
    active_missing_ref = onboarding.plan(fixture(role_hub={"status": "active"}))
    expect("active-rolehub-ref-hold", active_missing_ref["state"] == "partial_hold" and "active_role_hub_ref_missing" in active_missing_ref["stop_conditions"], active_missing_ref)
    current_hub = onboarding.plan(fixture(current_thread={"eligible": True, "current_thread_ref": "opaque-current", "name": "Project"}))
    expect("rename-current-rolehub", "rename_current_to_role_hub" in {item["kind"] for item in current_hub["operations"]}, current_hub)
    current_failure = onboarding.plan(fixture(current_thread={"eligible": True, "current_thread_ref": "opaque-current", "name": "Project"}, request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(current_hub["operations"][0]), receipt(current_hub["operations"][1]), receipt(current_hub["operations"][2], "failed")]))
    expect("rename-current-restore", current_failure["state"] == "rollback_planned" and current_failure["rollback_operations"][0]["kind"] == "restore_preimage", current_failure)
    forged = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(item, fingerprint=False) for item in fresh["operations"]]))
    expect("forged-receipt-hold", forged["state"] == "partial_hold" and "forged_receipt_fingerprint" in forged["stop_conditions"], forged)
    unknown = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[{"idempotency_key": "forged", "status": "applied", "receipt_ref": "adapter:x", "operation_fingerprint": "sha256:x"}]))
    expect("unknown-receipt-hold", unknown["state"] == "partial_hold" and "invalid_receipt_sequence" in unknown["stop_conditions"], unknown)
    duplicate_receipt = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(fresh["operations"][0]), receipt(fresh["operations"][0])]))
    expect("duplicate-receipt-hold", duplicate_receipt["state"] == "partial_hold" and "invalid_receipt_sequence" in duplicate_receipt["stop_conditions"], duplicate_receipt)
    missing_ref = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[{key: value for key, value in receipt(fresh["operations"][0]).items() if key != "receipt_ref"}]))
    expect("missing-receipt-ref-hold", missing_ref["state"] == "partial_hold" and "missing_receipt_ref" in missing_ref["stop_conditions"], missing_ref)
    successful = fresh["operations"][1]
    failed = fresh["operations"][2]
    partial_receipts = [receipt(fresh["operations"][0]), receipt(successful), receipt(failed, "failed")]
    partial = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=partial_receipts))
    expect("success-then-failure-reverse-rollback", partial["state"] == "rollback_planned" and partial["rollback_operations"][0]["source_idempotency_key"] == successful["idempotency_key"] and partial["rollback_operations"][0]["kind"] == "mark_setup_incomplete", partial)
    rolled = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=partial_receipts, rollback_receipts=[rollback_receipt(partial["rollback_operations"][0])]))
    expect("rollback-readback", rolled["state"] == "rolled_back", rolled)
    rollback_failed = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=partial_receipts, rollback_receipts=[rollback_receipt(partial["rollback_operations"][0], "failed")]))
    expect("rollback-failure-incomplete", rollback_failed["state"] == "rollback_incomplete", rollback_failed)
    rollback_forged = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=partial_receipts, rollback_receipts=[{**rollback_receipt(partial["rollback_operations"][0]), "rollback_fingerprint": "sha256:forged"}]))
    expect("rollback-forgery-incomplete", rollback_forged["state"] == "rollback_incomplete", rollback_forged)
    privacy = onboarding.plan(fixture(extra={"transcript": "must-not-appear"}))
    expect("privacy-hold", privacy["state"] == "partial_hold" and privacy["summary"]["capability"] == "privacy_held", privacy)
    notes = onboarding.plan(fixture(notes={"tool_output": "must-not-appear"}))
    expect("notes-privacy-hold", notes["state"] == "partial_hold" and notes["summary"]["capability"] == "privacy_held", notes)
    unknown_field = onboarding.plan(fixture(unexpected="reject"))
    expect("unknown-field-hold", unknown_field["state"] == "partial_hold" and "unknown_input_field" in unknown_field["stop_conditions"], unknown_field)
    sparse = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(fresh["operations"][2])]))
    expect("receipt-prefix-hold", sparse["state"] == "partial_hold" and "invalid_receipt_sequence" in sparse["stop_conditions"], sparse)
    after_terminal = onboarding.plan(fixture(request={**fixture()["request"], "apply_authorized": True}, operation_receipts=[receipt(fresh["operations"][0]), receipt(fresh["operations"][1], "failed"), receipt(fresh["operations"][2], "failed")]))
    expect("receipt-after-terminal-hold", after_terminal["state"] == "partial_hold" and "invalid_receipt_sequence" in after_terminal["stop_conditions"], after_terminal)
    schema_expect("ready", ready)
    schema_expect("hold", active_missing_ref)
    schema_expect("rollback", partial)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
