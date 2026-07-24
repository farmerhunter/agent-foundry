#!/usr/bin/env python3
"""Validate runtime-owned collaboration capability capture evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


ROUTE_CATEGORIES = {"create", "send", "spawn", "fork", "automation", "future"}
SUPPORT_STATUSES = {"supported", "degraded", "unsupported"}
PRODUCER_TYPES = {"runtime_control_surface", "adapter_control_surface"}
FORBIDDEN_CONTENT_KEYS = {
    "prompt",
    "body",
    "message",
    "messages",
    "content",
    "raw_prompt",
    "raw_body",
    "raw_transcript",
    "transcript",
    "conversation",
    "payload_body",
}
STOP_CONDITIONS = {
    "missing_producer",
    "stale_evidence",
    "forged_evidence",
    "caller_only_evidence",
    "privacy_exposure",
    "duplicate_owner",
    "budget_breach",
    "external_cost_ambiguity",
    "missing_runtime_capture",
    "unsupported_runtime_capture",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate runtime-owned capture evidence JSON.")
    parser.add_argument("--input", help="Evidence JSON path. Defaults to stdin when provided.")
    parser.add_argument("--now", help="Current UTC timestamp for deterministic tests.")
    parser.add_argument("--max-age-hours", type=int, default=24)
    return parser.parse_args()


def read_record(path: str | None) -> dict[str, Any]:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        return {}
    if not text.strip():
        return {}
    value = json.loads(text)
    if not isinstance(value, dict):
        raise SystemExit("runtime capture evidence must be a JSON object")
    return value


def parse_timestamp(raw: Any) -> dt.datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def utc_now(raw: str | None) -> dt.datetime:
    if raw:
        parsed = parse_timestamp(raw)
        if parsed is None:
            raise SystemExit("--now must be an ISO timestamp")
        return parsed
    return dt.datetime.now(dt.timezone.utc)


def missing(value: Any) -> bool:
    return value in (None, "", [], {})


def find_forbidden_content(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if key in FORBIDDEN_CONTENT_KEYS:
                found.append(child)
            found.extend(find_forbidden_content(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_forbidden_content(item, f"{path}[{index}]"))
    return found


def validate(record: dict[str, Any], now: dt.datetime, max_age_hours: int = 24) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if record.get("schema_version") != 1:
        errors.append("unsupported_schema_version")
    for field in ("record_id", "captured_at", "producer", "route", "evidence_metadata", "privacy"):
        if missing(record.get(field)):
            errors.append(f"missing_{field}")

    producer = record.get("producer") if isinstance(record.get("producer"), dict) else {}
    if not producer:
        errors.append("missing_producer")
    if producer.get("producer_type") not in PRODUCER_TYPES:
        errors.append("missing_runtime_owned_producer")
    if producer.get("runtime_owned") is not True:
        errors.append("caller_only_evidence")
    if producer.get("caller_supplied") is not False:
        errors.append("caller_only_evidence")
    for field in ("producer_id", "runtime_id", "capture_session_id"):
        if missing(producer.get(field)):
            errors.append(f"missing_producer_{field}")

    attestation = record.get("runtime_attestation") if isinstance(record.get("runtime_attestation"), dict) else {}
    if attestation.get("producer_bound") is not True or missing(attestation.get("capture_nonce")):
        errors.append("forged_evidence")

    captured_at = parse_timestamp(record.get("captured_at"))
    if captured_at is None:
        errors.append("missing_capture_timestamp")
    elif now - captured_at > dt.timedelta(hours=max_age_hours):
        errors.append("stale_evidence")

    route = record.get("route") if isinstance(record.get("route"), dict) else {}
    category = route.get("category")
    support_status = route.get("support_status")
    if category not in ROUTE_CATEGORIES:
        errors.append("unknown_route_category")
    if support_status not in SUPPORT_STATUSES:
        errors.append("unknown_support_status")
    requested = route.get("requested_envelope") if isinstance(route.get("requested_envelope"), dict) else {}
    effective = route.get("effective_envelope") if isinstance(route.get("effective_envelope"), dict) else {}
    if missing(requested.get("model")) or missing(requested.get("reasoning")):
        errors.append("missing_requested_envelope")
    if support_status == "supported":
        if effective.get("status") != "accepted" or missing(effective.get("model")) or missing(effective.get("reasoning")):
            errors.append("missing_effective_envelope")
    elif support_status == "degraded":
        if not isinstance(route.get("missing_observations"), list) or not route.get("missing_observations"):
            errors.append("missing_degraded_observations")
    elif support_status == "unsupported":
        if missing(route.get("unsupported_reason")):
            errors.append("missing_unsupported_reason")

    metadata = record.get("evidence_metadata") if isinstance(record.get("evidence_metadata"), dict) else {}
    if metadata.get("external_cost_possible") is True and missing(metadata.get("budget_anchor")):
        errors.append("external_cost_ambiguity")
    if metadata.get("duplicate_owner_detected") is True:
        errors.append("duplicate_owner")

    privacy = record.get("privacy") if isinstance(record.get("privacy"), dict) else {}
    if privacy.get("contains_prompt_body") is not False or privacy.get("redaction") != "metadata_only":
        errors.append("privacy_exposure")
    forbidden_paths = find_forbidden_content(record)
    if forbidden_paths:
        errors.append("prompt_body_content_present")
        warnings.append("forbidden_content_paths:" + ",".join(forbidden_paths))

    declared_stops = record.get("stop_conditions", [])
    if not isinstance(declared_stops, list):
        errors.append("missing_stop_conditions")
        declared_stops = []
    unknown_stops = sorted({str(item) for item in declared_stops} - STOP_CONDITIONS)
    if unknown_stops:
        errors.append("unknown_stop_conditions")
        warnings.append("unknown_stop_conditions:" + ",".join(unknown_stops))

    status = support_status if support_status in SUPPORT_STATUSES else "invalid"
    return {
        "valid": not errors,
        "support_status": status,
        "route_category": category,
        "errors": sorted(set(errors)),
        "warnings": warnings,
        "runtime_owned": producer.get("runtime_owned") is True and producer.get("caller_supplied") is False,
        "content_redacted": not forbidden_paths and privacy.get("contains_prompt_body") is False,
        "mutation_performed": False,
        "dispatch_performed": False,
    }


def main() -> int:
    args = parse_args()
    result = validate(read_record(args.input), utc_now(args.now), args.max_age_hours)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
