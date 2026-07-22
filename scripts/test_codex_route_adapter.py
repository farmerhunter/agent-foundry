#!/usr/bin/env python3
"""Fixture regressions for the AF18 optional Codex route adapter."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "plan_codex_route_adapter.py"


def portable(topology: str = "fresh_thread", decision: str = "dispatch_advisory", explicit: bool = True) -> dict:
    selected = None if decision != "dispatch_advisory" else {"topology": topology, "context_mode": "fresh"}
    return {
        "work_unit": {"work_unit_id": "AF18-421-fixture", "requires_explicit_envelope": explicit},
        "dispatch_plan": {"route_decision": decision, "selected_candidate": selected, "requested_capability_tier": "balanced", "requested_reasoning_tier": "medium"},
        "conversation_projection": {"effective_policy": {"profile": "normal"}, "next_action": "Review portable plan"},
    }


def schemas() -> dict:
    return {
        "observed_at": "2026-07-22T00:00:00Z",
        "schema_source": "current_codex_tool_schema",
        "tools": {
            "create_thread": {"status": "supported", "fields": ["model", "thinking"]},
            "send_message_to_thread": {"status": "supported", "fields": ["model", "thinking"]},
            "spawn_agent": {"status": "supported", "fields": ["model", "reasoning_effort", "fork_context"]},
            "fork_thread": {"status": "supported", "fields": []},
        },
    }


def envelopes() -> dict:
    return {
        "balanced": {"model": "gpt-5.4", "thinking": "medium", "reasoning_effort": "medium"},
        "frontier": {"model": "gpt-5.5", "thinking": "high", "reasoning_effort": "high"},
        "economy": {"model": "gpt-5.4-mini", "thinking": "low", "reasoning_effort": "low"},
    }


def run(data: dict) -> tuple[int, dict | str]:
    with tempfile.TemporaryDirectory(prefix="af18-codex-adapter-") as raw:
        path = Path(raw) / "fixture.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        completed = subprocess.run([sys.executable, str(ADAPTER), "--input-json", str(path), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (completed.returncode, json.loads(completed.stdout)) if completed.returncode == 0 else (completed.returncode, completed.stderr)


def expect(name: str, condition: bool, detail: object, errors: list[str]) -> None:
    if condition:
        print(f"{name}: ok")
    else:
        errors.append(f"{name}: {detail}")


def main() -> int:
    errors: list[str] = []
    base = {"portable_plan": portable(), "schema_observation": schemas(), "adapter_envelopes": envelopes()}
    code, output = run(base)
    expect("fresh-explicit-envelope", code == 0 and output["adapter_plan"]["adapter_decision"] == "dry_run_ready" and output["adapter_plan"]["explicit_envelope"] == {"model": "gpt-5.4", "thinking": "medium"}, output, errors)
    expect("fresh-no-write", code == 0 and output["mutation_performed"] is False and output["dispatch_performed"] is False and output["adapter_plan"]["lifecycle_evidence"]["close_archive_resume"] == "not_executed_dry_run_only", output, errors)

    durable = {"portable_plan": portable("durable_thread"), "schema_observation": schemas(), "adapter_envelopes": envelopes()}
    code, output = run(durable)
    expect("durable-envelope", code == 0 and output["adapter_plan"]["tool_call_proposed"] == "send_message_to_thread" and output["adapter_plan"]["explicit_envelope"]["thinking"] == "medium", output, errors)

    subagent = {"portable_plan": portable("subagent"), "schema_observation": schemas(), "adapter_envelopes": envelopes()}
    code, output = run(subagent)
    expect("subagent-envelope", code == 0 and output["adapter_plan"]["explicit_envelope"] == {"model": "gpt-5.4", "reasoning_effort": "medium"}, output, errors)

    fork = {"portable_plan": portable("fork"), "schema_observation": schemas(), "adapter_envelopes": envelopes()}
    code, output = run(fork)
    expect("fork-unsupported", code == 0 and output["adapter_plan"]["adapter_decision"] == "unsupported" and output["mutation_performed"] is False, output, errors)

    omitted = {"portable_plan": portable("durable_thread", explicit=False), "schema_observation": schemas(), "adapter_envelopes": {}}
    code, output = run(omitted)
    expect("omitted-inheritance-human-stop", code == 0 and output["adapter_plan"]["adapter_decision"] == "human_stop" and output["conversation_projection"]["requested_vs_observable"]["observable"]["effective_configuration"] == "unknown", output, errors)

    stale = {"portable_plan": portable("durable_thread"), "schema_observation": schemas(), "adapter_envelopes": {}}
    code, output = run(stale)
    expect("stale-explicit-envelope-unsupported", code == 0 and output["adapter_plan"]["adapter_decision"] == "unsupported", output, errors)

    no_dispatch = {"portable_plan": portable(decision="no_dispatch"), "schema_observation": schemas(), "adapter_envelopes": envelopes()}
    code, output = run(no_dispatch)
    expect("no-dispatch-remains-no-call", code == 0 and output["adapter_plan"]["adapter_decision"] == "no_adapter_dispatch" and output["adapter_plan"]["tool_call_proposed"] == "not_available", output, errors)

    unsupported = schemas()
    unsupported["tools"]["create_thread"]["status"] = "unsupported"
    code, output = run({"portable_plan": portable(), "schema_observation": unsupported, "adapter_envelopes": envelopes()})
    expect("unsupported-runtime-visible", code == 0 and output["adapter_plan"]["adapter_decision"] == "unsupported" and "is unsupported" in output["conversation_projection"]["attention"][0], output, errors)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
