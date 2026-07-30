#!/usr/bin/env python3
"""Aggregate validated AF18 policy telemetry receipts deterministically."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from collect_af18_policy_telemetry import TelemetryError, collect_receipt, parse_time


def aggregate(receipts: list[dict], now_text: str, trusted_bindings: dict[str, dict[str, str]] | None = None) -> dict:
    if not isinstance(receipts, list):
        raise TelemetryError("telemetry_events_must_be_list")
    now = parse_time(now_text, "now")
    events = [collect_receipt(receipt, now, trusted_bindings) for receipt in receipts]
    ids = [event["event_id"] for event in events]
    if len(ids) != len(set(ids)):
        raise TelemetryError("duplicate_event")
    bindings = [(event["work"]["work_id"], event["lifecycle_action"], event["observed_at"]) for event in events]
    if len(bindings) != len(set(bindings)):
        raise TelemetryError("duplicate_work_lifecycle_binding")
    events.sort(key=lambda event: event["event_id"])
    profiles = {name: sum(event["policy"]["profile"] == name for event in events) for name in ("economy", "normal", "performance")}
    unavailable = sum(item["provenance"] == "unavailable" for event in events for item in event["observations"].values())
    holds = sum(event["effective_decision"] == "hold_for_decision" for event in events)
    return {"schema_version": "af18-policy-telemetry-aggregate-v1", "event_count": len(events), "profiles": profiles, "unavailable_measurement_count": unavailable, "hold_event_count": holds, "events": events, "policy_readout": {"normal_profile_historic_12k_cap": False, "low_limit": "emergency_only", "fixed_reasoning_multiplier": None, "auto_tuning_performed": False}, "mutation_performed": False, "dispatch_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate static AF18 policy telemetry receipts.")
    parser.add_argument("--events-json", type=Path, required=True)
    parser.add_argument("--now", default="2026-07-30T00:00:00Z")
    parser.add_argument("--trusted-bindings-json", type=Path)
    args = parser.parse_args()
    try:
        bindings = json.loads(args.trusted_bindings_json.read_text(encoding="utf-8")) if args.trusted_bindings_json else None
        print(json.dumps(aggregate(json.loads(args.events_json.read_text(encoding="utf-8")), args.now, bindings), sort_keys=True))
    except (OSError, json.JSONDecodeError, TelemetryError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
