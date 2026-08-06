#!/usr/bin/env python3
"""Capability-aware, in-memory thread harvest review contract."""

from __future__ import annotations

from typing import Any

ALLOWED_COVERAGE = {"complete", "partial", "unavailable", "privacy_held"}
ALLOWED_OUTPUTS = {"candidate_hold", "deferred", "rejected"}
FORBIDDEN_KEYS = {"page_size", "cursor", "cross_thread", "raw_transcript", "prompt", "tool_output", "identity", "secret"}


def review(request: dict[str, Any]) -> dict[str, Any]:
    holds: list[str] = []
    if not isinstance(request, dict) or request.keys() & FORBIDDEN_KEYS:
        return result("rejected", "privacy_or_navigation_forbidden")
    if request.get("human_intent_confirmed") is not True: holds.append("human_intent_required")
    if not isinstance(request.get("thread_ref"), str) or not request["thread_ref"]: holds.append("opaque_thread_ref_required")
    if request.get("coverage") not in ALLOWED_COVERAGE: return result("rejected", "unknown_coverage")
    if request.get("adapter_history") not in {"available", "unavailable"}: holds.append("adapter_history_unknown")
    output = request.get("output", "candidate_hold")
    if output not in ALLOWED_OUTPUTS: return result("rejected", "output_not_allowed")
    if holds: return result("deferred", ";".join(holds), request.get("coverage"))
    coverage = request["coverage"]
    if coverage == "partial": return result("deferred", "thread_harvest_partial", coverage)
    if coverage == "unavailable": return result("deferred", "held_thread_history_unavailable", coverage)
    if coverage == "privacy_held": return result("deferred", "held_thread_history_privacy", coverage)
    return result(output, "validated_bounded_request", coverage)


def result(output: str, reason: str, coverage: str | None = None) -> dict[str, Any]:
    return {"outcome": output, "reason": reason, "coverage": coverage, "terminal": output in {"rejected", "deferred"}, "mutation_flags": {"filesystem": False, "network": False, "github": False, "vault": False, "publish": False, "activate": False}, "persisted_raw_data": False, "privacy_safe": True}
