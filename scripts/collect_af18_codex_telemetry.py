#!/usr/bin/env python3
"""Export privacy-safe AF18 calibration evidence from completed Codex JSONL."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "scripts" / "run_af18_calibration.py"
spec = importlib.util.spec_from_file_location("af18_calibration", CALIBRATION)
calibration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = calibration
spec.loader.exec_module(calibration)

EVENT_KEYS = {"type", "invocation_id", "execution_id", "completed_at", "usage"}
USAGE_KEYS = {"input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens"}
METADATA_KEYS = {"schema_version", "protocol_version", "sample", "captured_at", "evidence_anchor", "invocation_ids", "execution_id", "execution_window"}
RAW_KEYS = calibration.FORBIDDEN_KEYS | {"response", "request", "event", "error", "model", "instructions"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Completed-event JSONL input.")
    parser.add_argument("--metadata", required=True, help="Explicit allowlisted metadata JSON.")
    parser.add_argument("--output", help="Output JSON path; stdout is used otherwise.")
    return parser.parse_args()


def reject_unknown(value: Any, allowed: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError(f"invalid_{label}_fields")
    if calibration.forbidden_paths(value) or any(key.lower() in RAW_KEYS for key in value):
        raise ValueError("raw_content_or_unknown_field_rejected")


def read_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("metadata_must_be_object")
    return value


def unavailable(name: str) -> dict[str, Any]:
    return {"observation_id": f"codex-jsonl-{name}", "availability": "unavailable", "value": None, "unit": "tokens" if "tokens" in name else "count" if name.endswith("count") else "bytes" if name.endswith("bytes") else "hours" if name.endswith("hours") else "seconds", "source": "codex_jsonl_completed_export", "observed_at": None, "reason": "not_exposed"}


def observed(name: str, value: int, captured_at: str) -> dict[str, Any]:
    return {"observation_id": f"codex-jsonl-{name}", "availability": "observed", "value": value, "unit": "tokens", "source": "codex_jsonl_completed_export", "observed_at": captured_at}


def read_events(path: str, invocation_ids: list[str], execution_id: str, execution_window: dict[str, str]) -> list[dict[str, Any]]:
    window_start = calibration.utc(execution_window["started_at"])
    window_end = calibration.utc(execution_window["ended_at"])
    if window_end < window_start:
        raise ValueError("invalid_execution_window")
    events: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        reject_unknown(value, EVENT_KEYS, "completed_event")
        if value.get("type") != "codex.completed" or not isinstance(value.get("invocation_id"), str) or not value["invocation_id"] or value.get("execution_id") != execution_id or not isinstance(value.get("completed_at"), str):
            raise ValueError(f"invalid_completed_event:{line_number}")
        completed_at = calibration.utc(value["completed_at"])
        if not window_start <= completed_at <= window_end:
            raise ValueError(f"completed_event_outside_execution_window:{line_number}")
        usage = value.get("usage")
        reject_unknown(usage, USAGE_KEYS, "usage")
        if any(not isinstance(usage.get(key), int) or isinstance(usage.get(key), bool) or usage[key] < 0 for key in ("input_tokens", "output_tokens")):
            raise ValueError(f"missing_completed_turn_usage:{line_number}")
        if usage.get("cached_input_tokens") is not None and (not isinstance(usage["cached_input_tokens"], int) or usage["cached_input_tokens"] < 0 or usage["cached_input_tokens"] > usage["input_tokens"]):
            raise ValueError(f"invalid_cached_input_tokens:{line_number}")
        if usage.get("reasoning_tokens") is not None and (not isinstance(usage["reasoning_tokens"], int) or usage["reasoning_tokens"] < 0 or usage["reasoning_tokens"] > usage["output_tokens"]):
            raise ValueError(f"invalid_reasoning_tokens:{line_number}")
        if value["invocation_id"] in events:
            raise ValueError(f"duplicate_invocation_id:{value['invocation_id']}")
        events[value["invocation_id"]] = value
    if set(events) != set(invocation_ids):
        raise ValueError("invocation_ids_must_match_completed_jsonl")
    return [events[item] for item in invocation_ids]


def collect(metadata: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    reject_unknown(metadata, METADATA_KEYS, "metadata")
    invocation_ids = metadata.get("invocation_ids")
    if not isinstance(invocation_ids, list) or not invocation_ids or any(not isinstance(item, str) or not item for item in invocation_ids) or len(invocation_ids) != len(set(invocation_ids)):
        raise ValueError("invalid_invocation_ids")
    sample = metadata.get("sample")
    if not isinstance(sample, dict) or "resources" in sample or "provenance" in sample or sample.get("variant") == "B":
        raise ValueError("invalid_observed_sample_metadata")
    if calibration.forbidden_paths(sample):
        raise ValueError("raw_content_or_unknown_field_rejected")
    execution_id = metadata.get("execution_id")
    execution_window = metadata.get("execution_window")
    if not isinstance(execution_id, str) or not execution_id:
        raise ValueError("invalid_execution_id")
    if not isinstance(execution_window, dict) or set(execution_window) != {"started_at", "ended_at"}:
        raise ValueError("invalid_execution_window")
    if sample.get("execution_id") != execution_id or sample.get("anchors", {}).get("execution") != metadata.get("evidence_anchor"):
        raise ValueError("execution_anchor_binding_mismatch")
    if sample.get("scenario", {}).get("measurement_window", {}).get("fixed_execution_window") is not True:
        raise ValueError("fixed_execution_window_required")
    captured_at = metadata.get("captured_at")
    if not isinstance(captured_at, str) or not calibration.is_anchor(metadata.get("evidence_anchor")):
        raise ValueError("invalid_metadata_provenance")
    totals = {key: sum(event["usage"].get(key, 0) for event in events) for key in USAGE_KEYS}
    resources = {name: unavailable(name) for name in calibration.REQUIRED_RESOURCES}
    for name in ("input_tokens", "output_tokens"):
        resources[name] = observed(name, totals[name], captured_at)
    for name in ("cached_input_tokens", "reasoning_tokens"):
        if all(name in event["usage"] for event in events):
            resources[name] = observed(name, totals[name], captured_at)
    resources["cumulative_resource_tokens"] = {"observation_id": "codex-jsonl-cumulative_resource_tokens", "availability": "observed", "value": totals["input_tokens"] + totals["output_tokens"], "unit": "tokens", "source": "codex_jsonl_completed_export", "observed_at": captured_at, "observation_basis": "derived", "derived_total_component_ids": [resources["input_tokens"]["observation_id"], resources["output_tokens"]["observation_id"]], "invocation_ids": invocation_ids}
    output_sample = dict(sample)
    output_sample["provenance"] = {"source": "codex_jsonl_completed_export", "collection_method": "codex_jsonl_export", "captured_at": captured_at, "evidence_anchor": metadata["evidence_anchor"], "observation_kind": "observed"}
    output_sample["resources"] = resources
    packet = {"schema_version": metadata.get("schema_version"), "protocol_version": metadata.get("protocol_version"), "collection_mode": "codex_jsonl_export", "samples": [output_sample]}
    result = calibration.run(packet, calibration.utc(captured_at), 24 * 365 * 10)
    if result["invalid_evidence"]:
        raise ValueError("invalid_calibration_export:" + ",".join(result["invalid_evidence"][0]["errors"]))
    return packet


def main() -> int:
    args = parse_args()
    try:
        metadata = read_json(args.metadata)
        invocation_ids = metadata.get("invocation_ids")
        events = read_events(args.input, invocation_ids if isinstance(invocation_ids, list) else [], metadata.get("execution_id", ""), metadata.get("execution_window", {}))
        output = json.dumps(collect(metadata, events), indent=2, sort_keys=True) + "\n"
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc), "mutation_performed": False}, sort_keys=True), file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
