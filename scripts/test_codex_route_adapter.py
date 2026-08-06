#!/usr/bin/env python3
"""Fixture regressions for the AF18 optional Codex route adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "plan_codex_route_adapter.py"


def portable(topology: str = "fresh_thread", decision: str = "dispatch_advisory", explicit: bool = True) -> dict:
    selected = None if decision in {"no_dispatch", "human_stop", "serial_current_session", "batch_checkpoint", "hold_for_decision"} else {"topology": topology, "context_mode": "fresh", "route": decision}
    return {
        "work_unit": {"work_unit_id": "AF18-421-fixture", "requires_explicit_envelope": explicit},
        "dispatch_plan": {"route_decision": decision, "selected_candidate": selected, "requested_capability_tier": "balanced", "requested_reasoning_tier": "medium"},
        "conversation_projection": {
            "effective_policy": {"profile": "normal"},
            "next_action": "Review portable plan",
            "role_task_dispatch_policy": {
                "existing_healthy_role_task_preferred": True,
                "new_role_task_preference": "project_scoped_codex_task",
                "project_scoped_creation": "preferred",
                "project_id": "local-eb6e22ec0d00ef785d687022be1b433d",
                "project_root": "/Users/jinghuliu/Desktop/Code/Personal Projects/agent-foundry",
                "degraded_projectless_fallback": {"allowed": False, "bounded_to": "one_work_unit", "default_policy": False},
            },
        },
    }


def digest(tools: dict) -> str:
    encoded = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def schemas() -> dict:
    tools = {
        "create_thread": {"status": "supported", "fields": ["model", "thinking"]},
        "send_message_to_thread": {"status": "supported", "fields": ["model", "thinking"]},
        "spawn_agent": {"status": "supported", "fields": ["model", "reasoning_effort", "fork_context"]},
        "fork_thread": {"status": "supported", "fields": []},
    }
    return {
        "observed_at": "2026-07-22T00:00:00Z",
        "schema_source": "current_codex_tool_schema",
        "runtime_id": "codex-desktop-current-session",
        "provenance": {
            "collection_mode": "host_collected",
            "evidence_ref": "codex-app://current-session/tool-schema",
            "schema_digest": digest(tools),
        },
        "tools": tools,
    }


def envelopes() -> dict:
    return {
        "balanced": {"model": "gpt-5.4", "thinking": "medium", "reasoning_effort": "medium"},
        "frontier": {"model": "gpt-5.5", "thinking": "high", "reasoning_effort": "high"},
        "economy": {"model": "gpt-5.4-mini", "thinking": "low", "reasoning_effort": "low"},
    }


def adapter_context() -> dict:
    return {
        "runtime_id": "codex-desktop-current-session",
        "evaluated_at": "2026-07-22T00:05:00Z",
        "max_observation_age_seconds": 300,
        "project_id": "local-eb6e22ec0d00ef785d687022be1b433d",
        "project_root": "/Users/jinghuliu/Desktop/Code/Personal Projects/agent-foundry",
    }


def input_for(portable_plan: dict, observation: dict | None = None, adapter_envelopes: dict | None = None) -> dict:
    return {
        "portable_plan": portable_plan,
        "schema_observation": schemas() if observation is None else observation,
        "adapter_context": adapter_context(),
        "adapter_envelopes": envelopes() if adapter_envelopes is None else adapter_envelopes,
    }


def binding(kind: str = "local_folder_project", context: str = "fresh", *, runtime: bool = False) -> dict:
    return {
        "project_binding_observation": {
            "project_kind": kind,
            "context_mode": context,
            "identity": {"project_id": "git-seres", "project_root": "/projects/git.seres.cn", "cwd": "/projects/git.seres.cn"},
            "target": {"project_id": "git-seres", "project_root": "/projects/git.seres.cn", "cwd": "/projects/git.seres.cn"},
            "fresh_context": True,
            "runtime_owned_proof": runtime,
        }
    }


def provenance_recovery(output: dict, status: str) -> bool:
    conversation = output["conversation_projection"]
    return (
        output["adapter_plan"]["adapter_decision"] in {"unknown", "unsupported"}
        and output["adapter_plan"]["adapter_decision"] != "dry_run_ready"
        and output["adapter_plan"]["explicit_envelope"] == {}
        and output["schema_provenance"]["status"] == status
        and len(conversation["attention"]) == 1
        and conversation["next_action"] == "Obtain a verified runtime-owned Codex schema capture before proposing any envelope."
        and output["mutation_performed"] is False
        and output["dispatch_performed"] is False
    )


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
    code, output = run(binding())
    expect("non-git-invalid-arguments-hold", code == 0 and output["state"] == "held_same_project_fresh_unavailable" and output["human_ui_fallback_required"] is True and output["mutation_performed"] is False and output["dispatch_performed"] is False, output, errors)
    for kind in ("git_repository_project", "git_worktree_project"):
        code, output = run(binding(kind, runtime=True))
        expect(f"{kind}-fresh-ready", code == 0 and output["state"] == "same_project_fresh_ready" and output["mutation_performed"] is False, output, errors)
    code, output = run(binding("fork_inherited_context", "fork", runtime=True))
    expect("fork-inherited-held", code == 0 and output["state"] == "held_inherited_context_rejected" and output["dispatch_performed"] is False, output, errors)
    code, output = run(binding("projectless_fresh_context", "projectless", runtime=True))
    expect("projectless-held", code == 0 and output["state"] == "held_projectless_fallback_rejected" and output["mutation_performed"] is False, output, errors)
    mismatch = binding(runtime=True); mismatch["project_binding_observation"]["target"]["cwd"] = "/projects/git.seres.cn/worktree"
    code, output = run(mismatch)
    expect("child-root-mismatch-held", code == 0 and output["state"] == "held_project_binding_mismatch", output, errors)
    for field in ("project_id", "project_root", "cwd"):
        missing = binding(runtime=True); missing["project_binding_observation"]["identity"].pop(field)
        code, output = run(missing)
        expect(f"missing-{field}-held", code == 0 and output["state"] == "held_project_binding_mismatch", output, errors)
    stale = binding(runtime=True); stale["project_binding_observation"]["fresh_context"] = False
    code, output = run(stale)
    expect("missing-freshness-held", code == 0 and output["state"] == "held_project_binding_mismatch", output, errors)
    forged = binding(runtime=True); forged["project_binding_observation"]["runtime_owned_proof"] = False
    code, output = run(forged)
    expect("missing-runtime-proof-held", code == 0 and output["state"] == "held_same_project_fresh_unavailable", output, errors)

    base = input_for(portable("subagent"))
    code, output = run(base)
    expect("runtime-capture-unavailable", code == 0 and provenance_recovery(output, "unknown") and output["schema_provenance"]["evidence_ref_status"] == "unverified", output, errors)
    expect("runtime-capture-no-write", code == 0 and output["mutation_performed"] is False and output["dispatch_performed"] is False and output["adapter_plan"]["lifecycle_evidence"]["close_archive_resume"] == "not_executed_dry_run_only", output, errors)
    expect("project-scoped-dispatch-evidence", code == 0 and output["adapter_plan"]["role_task_dispatch_evidence"]["project_scoped_vs_projectless"] == "project_scoped" and output["adapter_plan"]["role_task_dispatch_evidence"]["target_project"]["project_id"] == "local-eb6e22ec0d00ef785d687022be1b433d", output, errors)

    degraded = portable("fresh_thread")
    degraded["conversation_projection"]["role_task_dispatch_policy"]["project_scoped_creation"] = "unavailable"
    degraded["conversation_projection"]["role_task_dispatch_policy"]["degraded_projectless_fallback"]["allowed"] = True
    code, output = run(input_for(degraded))
    expect("projectless-fallback-degraded-bounded", code == 0 and output["adapter_plan"]["role_task_dispatch_evidence"]["project_scoped_vs_projectless"] == "projectless_degraded" and output["adapter_plan"]["role_task_dispatch_evidence"]["fallback"]["bounded_to"] == "one_work_unit", output, errors)

    no_dispatch = input_for(portable(decision="no_dispatch"))
    code, output = run(no_dispatch)
    expect("no-dispatch-remains-no-call", code == 0 and output["adapter_plan"]["adapter_decision"] == "no_adapter_dispatch" and output["adapter_plan"]["tool_call_proposed"] == "not_available", output, errors)

    serial_route = input_for(portable(decision="serial_current_session"))
    code, output = run(serial_route)
    expect("serial-route-remains-no-call", code == 0 and output["adapter_plan"]["adapter_decision"] == "no_adapter_dispatch" and output["mutation_performed"] is False and output["dispatch_performed"] is False, output, errors)

    bounded_subagent = input_for(portable("subagent", decision="bounded_subagent"))
    code, output = run(bounded_subagent)
    expect("bounded-subagent-new-route-fails-closed", code == 0 and provenance_recovery(output, "unknown"), output, errors)

    absent = input_for(portable("subagent"))
    absent.pop("schema_observation")
    code, output = run(absent)
    expect("spawn-agent-absent-observation", code == 0 and provenance_recovery(output, "unknown"), output, errors)

    stale_spawn = schemas()
    stale_spawn["observed_at"] = "2026-07-21T00:00:00Z"
    code, output = run(input_for(portable("subagent"), observation=stale_spawn))
    expect("spawn-agent-stale-observation", code == 0 and provenance_recovery(output, "stale"), output, errors)

    untrusted_spawn = schemas()
    untrusted_spawn["provenance"]["schema_digest"] = "sha256:tampered"
    code, output = run(input_for(portable("subagent"), observation=untrusted_spawn))
    expect("spawn-agent-untrusted-observation", code == 0 and provenance_recovery(output, "untrusted"), output, errors)

    fixture_spawn = schemas()
    fixture_spawn["provenance"]["collection_mode"] = "fixture"
    code, output = run(input_for(portable("subagent"), observation=fixture_spawn))
    expect("spawn-agent-fixture-only-observation", code == 0 and provenance_recovery(output, "untrusted"), output, errors)

    forged_spawn = schemas()
    forged_spawn["runtime_id"] = "claimed-current-runtime"
    forged_spawn["provenance"]["evidence_ref"] = "https://example.invalid/forged-current-schema"
    context = adapter_context()
    context["runtime_id"] = "claimed-current-runtime"
    code, output = run({
        "portable_plan": portable("subagent"),
        "schema_observation": forged_spawn,
        "adapter_context": context,
        "adapter_envelopes": envelopes(),
    })
    expect("spawn-agent-forged-host-collected-is-unverified", code == 0 and provenance_recovery(output, "unknown") and output["schema_provenance"]["evidence_ref_status"] == "unverified", output, errors)

    for action in ("create", "link", "navigate", "measure"):
        code, output = run(
            {
                "role_operation": {
                    "action": action,
                    "capability_receipt": {
                        "capability": action,
                        "status": "supported",
                        "provenance": "observed",
                        "native_metadata": {"native_thread_id": f"codex-{action}-fixture"},
                    },
                }
            }
        )
        expect(
            f"role-operation-{action}-supported-dry-run",
            code == 0
            and output["adapter_plan"]["adapter_decision"] == "dry_run_ready"
            and output["adapter_plan"]["tool_call_proposed"] == "not_available"
            and output["adapter_plan"]["native_ids_are_metadata_only"] is True
            and output["mutation_performed"] is False
            and output["dispatch_performed"] is False,
            output,
            errors,
        )

    degraded_operation = {
        "role_operation": {
            "action": "measure",
            "capability_receipt": {"capability": "measure", "status": "degraded", "provenance": "estimated"},
        }
    }
    code, output = run(degraded_operation)
    expect("role-operation-degraded-no-call", code == 0 and output["adapter_plan"]["adapter_decision"] == "dry_run_degraded" and output["adapter_plan"]["tool_call_proposed"] == "not_available", output, errors)

    unsupported_operation = {
        "role_operation": {
            "action": "create",
            "capability_receipt": {"capability": "create", "status": "unsupported", "provenance": "observed"},
        }
    }
    code, output = run(unsupported_operation)
    expect("role-operation-unsupported-fails-closed", code == 0 and output["adapter_plan"]["adapter_decision"] == "hold_required", output, errors)

    unavailable_operation = {
        "role_operation": {
            "action": "navigate",
            "capability_receipt": {"capability": "navigate", "status": "supported", "provenance": "unavailable"},
        }
    }
    code, output = run(unavailable_operation)
    expect("role-operation-unavailable-fails-closed", code == 0 and output["adapter_plan"]["adapter_decision"] == "hold_required", output, errors)

    private_operation = {
        "role_operation": {
            "action": "link",
            "prompt": "private",
            "capability_receipt": {"capability": "link", "status": "supported", "provenance": "observed"},
        }
    }
    code, output = run(private_operation)
    expect("role-operation-privacy-fails-closed", code == 0 and output["adapter_plan"]["adapter_decision"] == "hold_required", output, errors)

    def rolehub(ops, capabilities=None, rollback=None):
        normalized = []
        for sequence, original in enumerate(ops):
            op = dict(original)
            receipt = dict(op.get("receipt") or {})
            payload = {key: value for key, value in op.items() if key != "receipt"}
            fingerprint = f"sha256:{hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}"
            receipt.setdefault("project_id", "tiny-ipa")
            receipt.setdefault("logical_rolehub_id", "tiny-ipa-rolehub")
            receipt.setdefault("operation_id", op.get("operation_id"))
            receipt.setdefault("idempotency_key", op.get("idempotency_key"))
            receipt.setdefault("operation_fingerprint", fingerprint)
            receipt.setdefault("opaque_ref", "opaque:fixture")
            receipt.setdefault("readback", {"status": "observed"})
            receipt.setdefault("sequence", sequence)
            op["receipt"] = receipt
            normalized.append(op)
        return {
            "contract_version": "AF18-rolehub-adapter-v1",
            "project_id": "tiny-ipa",
            "rolehub_identity": {"logical_id": "tiny-ipa-rolehub"},
            "capabilities": capabilities or {"create": "supported", "link": "supported", "navigate": "supported"},
            "capability_evidence": {"trusted": True, "producer": "fixture-adapter", "runtime_id": "fixture", "project_id": "tiny-ipa", "logical_rolehub_id": "tiny-ipa-rolehub"},
            "operations": normalized,
            **({"rollback": rollback} if rollback is not None else {}),
        }

    base_op = {"operation_id": "create-hub", "action": "create", "idempotency_key": "tiny-ipa:create-hub", "receipt": {"project_id": "tiny-ipa", "logical_rolehub_id": "tiny-ipa-rolehub", "status": "applied"}}
    code, output = run(rolehub([base_op]))
    expect("rolehub-fresh-ready-no-io", code == 0 and output["state"] == "ready" and output["native_io_performed"] is False, output, errors)
    missing_version = rolehub([base_op]); missing_version.pop("contract_version")
    code, output = run(missing_version)
    expect("rolehub-missing-version-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    wrong_version = rolehub([base_op]); wrong_version["contract_version"] = "AF18-rolehub-adapter-v0"
    code, output = run(wrong_version)
    expect("rolehub-wrong-version-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    malformed = rolehub([{**base_op, "operation_id": ""}])
    code, output = run(malformed)
    expect("rolehub-missing-operation-id-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    unknown_root = rolehub([base_op]); unknown_root["secret_field"] = "x"
    code, output = run(unknown_root)
    expect("rolehub-unknown-root-field-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    unknown_op = rolehub([{**base_op, "unexpected": "x"}])
    code, output = run(unknown_op)
    expect("rolehub-unknown-operation-field-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    unknown_receipt = rolehub([{**base_op, "receipt": {"unexpected": "x"}}])
    code, output = run(unknown_receipt)
    expect("rolehub-unknown-receipt-field-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    malformed_nested = rolehub([base_op]); malformed_nested["role_matches"] = [{"role": "Architect", "project_id": "tiny-ipa"}]
    code, output = run(malformed_nested)
    expect("rolehub-malformed-role-match-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    duplicate = dict(base_op)
    code, output = run(rolehub([base_op, duplicate]))
    expect("rolehub-duplicate-idempotency-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    forged = dict(base_op)
    forged["receipt"] = {"project_id": "other-project", "logical_rolehub_id": "tiny-ipa-rolehub", "status": "applied"}
    code, output = run(rolehub([forged]))
    expect("rolehub-cross-project-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    missing_preimage = dict(base_op)
    missing_preimage.update({"operation_id": "link", "action": "link"})
    code, output = run(rolehub([missing_preimage]))
    expect("rolehub-missing-preimage-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    terminal = {"operation_id": "hold", "action": "navigate", "idempotency_key": "tiny-ipa:hold", "preimage": {}, "receipt": {"project_id": "tiny-ipa", "logical_rolehub_id": "tiny-ipa-rolehub", "status": "partial_hold"}}
    late = dict(base_op)
    code, output = run(rolehub([terminal, late]))
    expect("rolehub-late-receipt-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    rollback = {"status": "failed"}
    code, output = run(rolehub([base_op], rollback=rollback))
    expect("rolehub-rollback-incomplete", code == 0 and output["state"] == "rollback_incomplete", output, errors)

    raw_sentinel = "RAW_SCHEMA_SENTINEL_SHOULD_NOT_LEAK"
    invalid_schema = rolehub([base_op])
    invalid_schema["unexpected_private_field"] = raw_sentinel
    code, output = run(invalid_schema)
    expect(
        "rolehub-schema-validation-redacts-input",
        code == 0
        and raw_sentinel not in json.dumps(output, sort_keys=True)
        and output["attention"] == ["ROLEHUB_SCHEMA_VALIDATION_FAILED"],
        output,
        errors,
    )
    reuse = rolehub([base_op]); reuse["role_matches"] = [{"role": "Architect", "project_id": "tiny-ipa", "active": True, "legacy": False}, {"role": "Coordinator", "project_id": "tiny-ipa", "active": True, "legacy": False}]
    code, output = run(reuse)
    expect("rolehub-reuse-single-active", code == 0 and output["state"] == "ready", output, errors)
    duplicate_match = rolehub([base_op]); duplicate_match["role_matches"] = [{"role": "Architect", "project_id": "tiny-ipa", "active": True}, {"role": "Architect", "project_id": "tiny-ipa", "active": True}]
    code, output = run(duplicate_match)
    expect("rolehub-duplicate-match-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    unavailable = rolehub([base_op], capabilities={"create": "unavailable", "link": "unavailable", "navigate": "unavailable"})
    code, output = run(unavailable)
    expect("rolehub-unavailable-capability-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    transient = dict(base_op); transient["role"] = "Implementer"
    code, output = run(rolehub([transient]))
    expect("rolehub-work-role-transient", code == 0 and output["state"] == "partial_hold", output, errors)
    ready = dict(base_op); ready["receipt"] = {"status": "ready"}
    code, output = run(rolehub([ready]))
    expect("rolehub-ready-receipt-ready", code == 0 and output["state"] == "ready", output, errors)
    after_ready = dict(base_op); after_ready["operation_id"] = "late"
    code, output = run(rolehub([ready, after_ready]))
    expect("rolehub-after-ready-hold", code == 0 and output["state"] == "partial_hold", output, errors)
    first = dict(base_op); first["operation_id"] = "first"; first["preimage"] = {}
    second = dict(base_op); second["operation_id"] = "second"; second["preimage"] = {}
    code, output = run(rolehub([first, second], rollback={"status": "complete", "receipt": {"status": "complete", "reversed_operation_ids": ["first", "second"]}}))
    expect("rolehub-rollback-forward-order-rejected", code == 0 and output["state"] == "rollback_incomplete", output, errors)
    code, output = run(rolehub([first, second], rollback={"status": "complete", "receipt": {"status": "complete", "reversed_operation_ids": ["second", "first"]}}))
    expect("rolehub-rollback-reverse-order-accepted", code == 0 and output["state"] == "rolled_back", output, errors)
    private_rollback = {"status": "complete", "receipt": {"status": "complete", "reversed_operation_ids": ["second", "first"], "prompt": "SECRET"}}
    code, output = run(rolehub([first, second], rollback=private_rollback))
    expect("rolehub-rollback-privacy-hold", code == 0 and output["state"] == "partial_hold", output, errors)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
