#!/usr/bin/env python3
"""Focused no-I/O regressions for the legacy onboarding diagnostic router."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = yaml.safe_load(
    (ROOT / "schemas" / "bounded-collaboration-onboarding.schema.yaml").read_text(
        encoding="utf-8"
    )
)
spec = importlib.util.spec_from_file_location(
    "onboarding", ROOT / "scripts" / "plan_bounded_collaboration_onboarding.py"
)
onboarding = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(onboarding)


def capability_set():
    projections = {name: {"status": "supported"} for name in onboarding.PROJECTIONS}
    projections["scheduler"] = {
        "status": "supported",
        "binding_ref": "scheduler:legacy",
        "binding_status": "bound",
    }
    projections["transient_template"] = {
        "status": "supported",
        "template_refs": {
            role: f"template:{role}" for role in onboarding.TRANSIENT_ROLES
        },
    }
    return {
        "role_binding": {"status": "supported"},
        "projections": projections,
        "operations": {
            name: {"status": "supported"} for name in onboarding.CAPABILITIES
        },
    }


def fixture(**overrides):
    value = {
        "onboarding_version": onboarding.LEGACY_VERSION,
        "request": {
            "project_identity": {
                "project_id": "legacy-project",
                "repository": "farmerhunter/agent-foundry",
                "integration_branch": "codex/integration",
            },
            "onboarding_key": "legacy-onboarding-key",
            "apply_authorized": False,
        },
        "runtime_capabilities": capability_set(),
        "role_hub": {"status": "missing"},
        "current_thread": {
            "eligible": False,
            "current_thread_ref": "opaque-current",
            "name": "Current",
        },
        "existing_roles": [],
        "repository_state": {"dirty": True, "dirty_preserved": True},
    }
    value.update(overrides)
    return value


def role(role_name, *, state="active", role_ref="opaque-role"):
    return {
        "project_id": "legacy-project",
        "role": role_name,
        "role_ref": role_ref,
        "durable_anchor": "issue:548",
        "state": state,
        "legacy": False,
    }


def receipt(key, status="applied"):
    value = {
        "idempotency_key": key,
        "status": status,
        "receipt_ref": "opaque-receipt",
        "operation_fingerprint": "sha256:caller-claim",
    }
    if status == "applied":
        value["result_ref"] = "opaque-result"
    return value


def expect_route(name, value):
    result = onboarding.plan(value)
    assert result["state"] == "owner_composed_route_required", (name, result)
    assert result["operations"] == [] and result["rollback_operations"] == [], result
    assert result["read_only"] is True
    assert result["mutation_performed"] is False
    assert result["dispatch_performed"] is False
    assert result["next_route"] == onboarding.ROUTE
    assert result["role_hub"] == onboarding.ROLE_HUB_PROJECTION
    assert result["stop_conditions"] == []
    jsonschema.Draft202012Validator(SCHEMA).validate(result)
    print(f"{name}: ok")
    return result


def expect_hold(name, value, reason):
    result = onboarding.plan(value)
    assert result["state"] == "partial_hold", (name, result)
    assert result["stop_conditions"] == [reason]
    assert result["operations"] == [] and result["rollback_operations"] == []
    assert result["mutation_performed"] is False
    assert result["dispatch_performed"] is False
    jsonschema.Draft202012Validator(SCHEMA).validate(result)
    print(f"{name}: ok")
    return result


def main():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    schema = jsonschema.Draft202012Validator(SCHEMA)
    schema.validate(fixture())

    expect_route("missing-rolehub-routes", fixture())
    expect_route(
        "active-rolehub-routes",
        fixture(role_hub={"status": "active", "role_hub_ref": "opaque-hub"}),
    )
    expect_route("held-rolehub-does-not-block", fixture(role_hub={"status": "held"}))
    expect_route(
        "eligible-current-thread-is-not-adopted",
        fixture(
            current_thread={
                "eligible": True,
                "current_thread_ref": "opaque-current",
                "name": "Legacy RoleHub",
            }
        ),
    )

    caller_receipts = [
        receipt("caller-operation"),
        receipt("caller-operation"),
        receipt("partial-operation", "failed"),
    ]
    apply_claim = expect_route(
        "apply-and-receipts-cannot-authorize",
        fixture(
            request={**fixture()["request"], "apply_authorized": True},
            operation_receipts=caller_receipts,
            rollback_receipts=[
                {
                    "source_idempotency_key": "caller-operation",
                    "status": "applied",
                    "receipt_ref": "opaque-rollback",
                    "source_operation_fingerprint": "sha256:caller-claim",
                    "rollback_fingerprint": "sha256:caller-rollback",
                }
            ],
        ),
    )
    assert "ready" not in json.dumps(apply_claim, sort_keys=True)

    duplicate_and_held = [
        role("Coordinator", role_ref="opaque-a"),
        role("Coordinator", role_ref="opaque-b"),
        role("Architect", state="held", role_ref="opaque-held"),
    ]
    expect_route(
        "duplicate-and-held-role-metadata-has-no-authority",
        fixture(existing_roles=duplicate_and_held),
    )

    privacy = expect_hold(
        "privacy-input-holds",
        fixture(extra={"tool_output": "secret-tool-output"}),
        "privacy_sensitive_input",
    )
    assert "secret-tool-output" not in json.dumps(privacy, sort_keys=True)
    expect_hold("unknown-input-holds", fixture(unexpected="caller-text"), "invalid_legacy_request")
    expect_hold(
        "invalid-legacy-version-holds",
        fixture(onboarding_version=onboarding.VERSION),
        "invalid_legacy_request",
    )

    old_ready = {
        "onboarding_version": onboarding.LEGACY_VERSION,
        "read_only": True,
        "mutation_performed": False,
        "dispatch_performed": False,
        "state": "ready",
        "transition_history": ["preflight", "ready"],
        "stop_conditions": [],
        "operations": [{"kind": "create_role_hub"}],
        "summary": {},
    }
    try:
        schema.validate(old_ready)
    except jsonschema.ValidationError:
        print("schema-rejects-v1-ready-mutation-envelope: ok")
    else:
        raise AssertionError("v1 ready/mutation envelope unexpectedly validated")

    docs = " ".join(
        (ROOT / "docs" / "multi-agent-collaboration.md")
        .read_text(encoding="utf-8")
        .split()
    )
    required_docs = (
        "public locator-only runtime bridge",
        "legacy compatibility diagnostic/router",
        "optional logical read-only projection",
        "not a global thread limit",
    )
    assert all(text in docs for text in required_docs), required_docs
    print("docs-route-and-thread-budget: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
