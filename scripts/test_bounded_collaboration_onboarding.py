#!/usr/bin/env python3
"""Focused no-I/O regressions for native bounded-collaboration onboarding."""

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


def capabilities(**overrides):
    values = {name: {"status": "supported"} for name in onboarding.CAPABILITIES}
    for name, status in overrides.items():
        values[name] = {"status": status}
    return {"operations": values}


def fixture(**overrides):
    value = {
        "onboarding_version": onboarding.VERSION,
        "request": {
            "project_identity": {"project_id": "agent-foundry", "repository": "farmerhunter/agent-foundry", "integration_branch": "main"},
            "onboarding_key": "native-onboarding-1",
            "apply_authorized": False,
            "reuse_policy": "fresh_only",
            "handshake_requested": True,
        },
        "runtime_capabilities": capabilities(),
        "existing_roles": [],
        "repository_state": {"dirty": True, "dirty_preserved": True},
    }
    value.update(overrides)
    return value


def expect(name, condition, value):
    if not condition:
        raise AssertionError(f"{name}: {value}")
    print(f"{name}: ok")


def receipt(item, result_ref, *, status="applied", evidence=None, pending_task_id=None, fingerprint=True):
    value = {"idempotency_key": item["idempotency_key"], "status": status, "receipt_ref": f"receipt:{item['subject']}"}
    if fingerprint:
        value["operation_fingerprint"] = item["operation_fingerprint"]
    if result_ref is not None:
        value["result_ref"] = result_ref
    if evidence is not None:
        value["evidence"] = evidence
    if pending_task_id is not None:
        value["pending_task_id"] = pending_task_id
    return value


def role_receipts(plan):
    return [
        receipt(plan["operations"][0], "project:saved"),
        receipt(plan["operations"][1], "thread:coordinator", evidence={"identity_kind": "thread_id", "source": "public_owner_surface"}),
        receipt(plan["operations"][2], "thread:architect", evidence={"identity_kind": "thread_id", "source": "public_owner_surface"}),
    ]


def owner_receipts(plan):
    result = []
    for item in plan["operations"][3:5]:
        thread_id = "thread:coordinator" if item["subject"] == "Coordinator" else "thread:architect"
        result.append(receipt(item, thread_id, evidence={"owner_role": item["subject"], "thread_id": thread_id, "initialized": True, "cursor": f"cursor:{item['subject']}"}))
    return result


def main():
    fresh = onboarding.plan(fixture())
    kinds = [item["kind"] for item in fresh["operations"]]
    expect("fresh-only-plan", fresh["state"] == "plan_ready" and kinds == ["resolve_saved_project", "create_thread", "create_thread"], fresh)
    expect("no-native-rolehub", all(item["subject"] != "RoleHub" for item in fresh["operations"]), fresh)
    expect("compact-init", all(item["desired_state"].get("schema") == "RoleSessionInit/v1" and item["desired_state"].get("work_assigned") is False for item in fresh["operations"][1:]), fresh)
    expect("retry-idempotence", fresh["operations"] == onboarding.plan(fixture())["operations"], fresh)

    apply_request = {**fixture()["request"], "apply_authorized": True}
    pending = onboarding.plan(fixture(request=apply_request, operation_receipts=[receipt(fresh["operations"][0], "project:saved"), receipt(fresh["operations"][1], None, status="setup_pending", pending_task_id="client:1"), receipt(fresh["operations"][2], None, status="setup_pending", pending_task_id="client:2")]))
    expect("pending-hold", pending["state"] == "setup_pending" and pending["stop_conditions"] == ["thread_id_unresolved"] and pending["summary"]["duplicate_create_allowed"] is False, pending)

    applying_owner = onboarding.plan(fixture(request=apply_request, operation_receipts=role_receipts(fresh)))
    expect("owner-readback-stage", applying_owner["state"] == "applying" and [item["kind"] for item in applying_owner["operations"][-2:]] == ["owner_readback", "owner_readback"], applying_owner)
    owners = role_receipts(fresh) + owner_receipts(applying_owner)
    applying_handshake = onboarding.plan(fixture(request=apply_request, operation_receipts=owners))
    expect("handshake-stage", [item["kind"] for item in applying_handshake["operations"][-4:]] == ["peer_handshake_send", "peer_handshake_send", "peer_handshake_readback", "peer_handshake_readback"], applying_handshake)
    sends = [receipt(item, f"message:{item['subject']}") for item in applying_handshake["operations"][5:7]]
    token = applying_handshake["operations"][5]["desired_state"]["token"]
    reads = []
    for item in applying_handshake["operations"][7:9]:
        reads.append(receipt(item, f"ack:{item['subject']}", evidence={"schema": "PeerHandshake/v1", "token": token, "reply_to_thread_id": item["desired_state"]["reply_to_thread_id"], "acknowledged": True, "cursor": f"cursor:ack:{item['subject']}"}))
    ready = onboarding.plan(fixture(request=apply_request, operation_receipts=owners + sends + reads))
    native = ready["summary"]["native_onboarding_receipt"]
    expect("ready-receipt", ready["state"] == "ready" and native["schema"] == "NativeOnboardingReceipt/v1" and all(value["ready"] for value in native["roles"].values()), ready)
    expect("explicit-reply-target", all(item["desired_state"].get("reply_to_thread_id") for item in ready["operations"] if item["kind"].startswith("peer_handshake")), ready)
    expect("single-owner-token-cursor", len({item["desired_state"].get("token") for item in ready["operations"] if item["kind"].startswith("peer_handshake")}) == 1 and all(item["desired_state"].get("owner") == "onboarding_executor" for item in ready["operations"] if item["kind"] == "peer_handshake_send") and all(item["desired_state"].get("cursor_rule") == "after_owner_readback" for item in ready["operations"] if item["kind"] == "peer_handshake_readback"), ready)

    no_handshake_request = {**apply_request, "handshake_requested": False}
    no_handshake_owner = onboarding.plan(fixture(request=no_handshake_request, operation_receipts=role_receipts(fresh)))
    no_handshake_ready = onboarding.plan(fixture(request=no_handshake_request, operation_receipts=role_receipts(fresh) + owner_receipts(no_handshake_owner)))
    expect("optional-handshake", no_handshake_ready["state"] == "ready" and no_handshake_ready["summary"]["native_onboarding_receipt"]["handshake"]["status"] == "not_requested", no_handshake_ready)

    old_input = onboarding.plan(fixture(existing_roles=[{"project_id": "agent-foundry", "role": "Coordinator", "thread_id": "old", "state": "active"}]))
    expect("fresh-only-no-history", old_input["state"] == "partial_hold" and "fresh_only_existing_role_input_forbidden" in old_input["stop_conditions"], old_input)
    missing = onboarding.plan(fixture(runtime_capabilities=capabilities(create_thread="unavailable")))
    expect("capability-hold", "create_thread_capability_unavailable" in missing["stop_conditions"], missing)
    private = onboarding.plan(fixture(private_session={"path": "forbidden"}))
    expect("privacy-hold", "privacy_exposure" in private["stop_conditions"], private)
    forged = onboarding.plan(fixture(request=apply_request, operation_receipts=[receipt(fresh["operations"][0], "project:saved", fingerprint=False)]))
    expect("forged-receipt", "forged_receipt_fingerprint" in forged["stop_conditions"], forged)
    duplicate_identity = onboarding.plan(fixture(request=apply_request, operation_receipts=[receipt(fresh["operations"][0], "project:saved"), receipt(fresh["operations"][1], "thread:same", evidence={"identity_kind": "thread_id", "source": "public_owner_surface"}), receipt(fresh["operations"][2], "thread:same", evidence={"identity_kind": "thread_id", "source": "public_owner_surface"})]))
    expect("duplicate-identity", "duplicate_thread_identity" in duplicate_identity["stop_conditions"], duplicate_identity)
    unproven = onboarding.plan(fixture(request=apply_request, operation_receipts=[receipt(fresh["operations"][0], "project:saved"), receipt(fresh["operations"][1], "client:not-a-thread"), receipt(fresh["operations"][2], "thread:architect", evidence={"identity_kind": "thread_id", "source": "public_owner_surface"})]))
    expect("pending-is-not-identity", "durable_thread_identity_unproven" in unproven["stop_conditions"], unproven)

    for name, value in (("plan", fresh), ("pending", pending), ("ready", ready), ("hold", old_input)):
        jsonschema.Draft202012Validator(SCHEMA).validate(value)
        print(f"schema-{name}: ok")
    jsonschema.Draft202012Validator(SCHEMA).validate(fixture())
    print("schema-input: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
