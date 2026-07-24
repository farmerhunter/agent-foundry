#!/usr/bin/env python3
"""Focused tests for runtime-owned capability capture evidence."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_runtime_owned_capture.py"
spec = importlib.util.spec_from_file_location("validate_runtime_owned_capture", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


NOW = dt.datetime(2026, 7, 24, 4, 0, tzinfo=dt.timezone.utc)


def record(**overrides):
    base = {
        "schema_version": 1,
        "record_id": "capture-446-supported-create",
        "captured_at": "2026-07-24T03:55:00Z",
        "producer": {
            "producer_type": "runtime_control_surface",
            "producer_id": "codex-control-surface",
            "runtime_id": "codex",
            "capture_session_id": "capture-session-446",
            "runtime_owned": True,
            "caller_supplied": False,
        },
        "runtime_attestation": {
            "producer_bound": True,
            "capture_nonce": "nonce-446",
        },
        "route": {
            "category": "create",
            "support_status": "supported",
            "requested_envelope": {"model": "gpt-5.5", "reasoning": "medium"},
            "effective_envelope": {"status": "accepted", "model": "gpt-5.5", "reasoning": "medium"},
        },
        "evidence_metadata": {
            "route_id": "route-446",
            "target_id": "thread-446",
            "cursor": "cursor-446",
            "budget_anchor": "issue-446",
            "external_cost_possible": False,
            "duplicate_owner_detected": False,
            "evidence_ref": "https://github.com/farmerhunter/agent-foundry/issues/446#runtime-capture",
        },
        "privacy": {
            "contains_prompt_body": False,
            "redaction": "metadata_only",
        },
        "stop_conditions": [],
    }
    base.update(overrides)
    return base


def validate(value):
    return validator.validate(value, NOW)


def expect(name, condition, detail):
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")


def main() -> int:
    supported = validate(record())
    expect("supported-runtime-owned-record-valid", supported["valid"] is True, supported)
    expect("supported-route-visible", supported["support_status"] == "supported", supported)
    expect("supported-no-content", supported["content_redacted"] is True, supported)
    expect("supported-advisory-only", supported["mutation_performed"] is False and supported["dispatch_performed"] is False, supported)

    degraded = record(
        route={
            "category": "send",
            "support_status": "degraded",
            "requested_envelope": {"model": "gpt-5.5", "reasoning": "medium"},
            "effective_envelope": {"status": "unknown"},
            "missing_observations": ["effective_model"],
        }
    )
    degraded_result = validate(degraded)
    expect("degraded-runtime-owned-record-valid", degraded_result["valid"] is True, degraded_result)
    expect("degraded-status-visible", degraded_result["support_status"] == "degraded", degraded_result)

    unsupported = record(
        route={
            "category": "future",
            "support_status": "unsupported",
            "requested_envelope": {"model": "gpt-5.5", "reasoning": "medium"},
            "effective_envelope": {"status": "unknown"},
            "unsupported_reason": "future route has no runtime-owned capture contract",
        },
        stop_conditions=["unsupported_runtime_capture"],
    )
    unsupported_result = validate(unsupported)
    expect("unsupported-runtime-owned-record-valid", unsupported_result["valid"] is True, unsupported_result)
    expect("unsupported-status-visible", unsupported_result["support_status"] == "unsupported", unsupported_result)

    caller_supplied = record(producer={**record()["producer"], "runtime_owned": False, "caller_supplied": True})
    caller_result = validate(caller_supplied)
    expect("caller-supplied-invalid", caller_result["valid"] is False, caller_result)
    expect("caller-supplied-error", "caller_only_evidence" in caller_result["errors"], caller_result)

    forged = record(runtime_attestation={"producer_bound": False, "capture_nonce": "nonce-446"})
    forged_result = validate(forged)
    expect("forged-invalid", forged_result["valid"] is False, forged_result)
    expect("forged-error", "forged_evidence" in forged_result["errors"], forged_result)

    stale = record(captured_at="2026-07-20T03:55:00Z")
    stale_result = validate(stale)
    expect("stale-invalid", stale_result["valid"] is False, stale_result)
    expect("stale-error", "stale_evidence" in stale_result["errors"], stale_result)

    missing_producer = record(producer={})
    missing_producer_result = validate(missing_producer)
    expect("missing-producer-invalid", missing_producer_result["valid"] is False, missing_producer_result)
    expect("missing-producer-error", "missing_producer" in missing_producer_result["errors"], missing_producer_result)

    prompt_body = record(evidence_metadata={**record()["evidence_metadata"], "prompt": "private task body"})
    prompt_body_result = validate(prompt_body)
    expect("prompt-body-invalid", prompt_body_result["valid"] is False, prompt_body_result)
    expect("prompt-body-error", "prompt_body_content_present" in prompt_body_result["errors"], prompt_body_result)

    print("runtime-owned capture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
