#!/usr/bin/env python3
"""Synthetic backend-neutral conformance harness; never creates durable state."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import practice_catalog_snapshot as catalog
from practice_catalog_snapshot import PointerStore, PointerStoreCapability, ValidationFailure, issue_capability
from sqlite_pointer_store import SQLitePointerStore

REQUIRED = ("read_receipt", "cas_success", "cas_conflict", "generation_monotonic")
def _capability_service():
    issued: list[PointerStoreCapability] = []
    def register(capability: PointerStoreCapability) -> None:
        issued.append(capability)
    def is_issued(capability: PointerStoreCapability) -> bool:
        return any(item is capability for item in issued)
    return register, is_issued


_register_capability, _is_issued = _capability_service()


def _result(adapter_id: str, capability: str, executed: list[str], skipped: list[str], evidence: list[str], holds: list[str]) -> dict[str, Any]:
    return {"adapter_id": adapter_id, "adapter_class": "reference", "capability": capability, "trust_domain": "same_process_reference", "receipt_binding_level": "reference_integrity_only", "same_process_arbitrary_code_or_introspection": "out_of_scope", "same_process_adversarial_forgery_resistance": "unsupported", "executed_test_ids": executed, "skipped_test_ids": skipped, "evidence_summary": evidence, "production_eligibility": False, "hold_reasons": holds, "privacy_safe": True}


def _read(capability: PointerStoreCapability):
    if not _is_issued(capability):
        raise ValidationFailure("unissued capability")
    backend = catalog._require_store(capability)
    return catalog._validate_receipt(backend.read(), backend)


def _cas(capability: PointerStoreCapability, generation: int, snapshot_hash: str):
    if not _is_issued(capability):
        raise ValidationFailure("unissued capability")
    backend = catalog._require_store(capability)
    receipt = backend.compare_and_set(generation, snapshot_hash)
    if receipt is None:
        return None
    return catalog._validate_receipt(receipt, backend, "cas")


def run_pointer_suite(adapter_id: str, backend: object) -> dict[str, Any]:
    executed: list[str] = []
    evidence: list[str] = []
    try:
        capability = issue_capability(backend)
        _register_capability(capability)
        first = _read(capability)
        if first.operation != "read" or first.generation != 0:
            raise ValidationFailure("read receipt mismatch")
        executed.append("read_receipt")
        new_hash = "b" * 64
        committed = _cas(capability, 0, new_hash)
        if committed is None or committed.generation != 1 or committed.snapshot_hash != new_hash:
            raise ValidationFailure("CAS receipt mismatch")
        executed.append("cas_success")
        if _cas(capability, 0, "c" * 64) is not None:
            raise ValidationFailure("CAS conflict accepted")
        executed.append("cas_conflict")
        reopened = _read(capability)
        if reopened.generation != 1:
            raise ValidationFailure("generation regression")
        executed.append("generation_monotonic")
        evidence.append("trusted capability and generation/hash receipts verified")
        return _result(adapter_id, "supported", executed, [], evidence, [])
    except (ValidationFailure, AttributeError, TypeError) as exc:
        return _result(adapter_id, "unavailable", executed, [test for test in REQUIRED if test not in executed], evidence, [f"held_backend_unqualified:{exc}"])


def run_reference_conformance() -> list[dict[str, Any]]:
    in_memory = run_pointer_suite("synthetic-memory", PointerStore("a" * 64))
    with tempfile.TemporaryDirectory(prefix="synthetic-pointer-") as temp:
        sqlite = SQLitePointerStore(Path(temp) / "pointer.sqlite3", "a" * 64, temp)
        try:
            sqlite_result = run_pointer_suite("synthetic-sqlite", sqlite)
        finally:
            sqlite.close()
    blob = _result("synthetic-blob", "unsupported", [], list(REQUIRED), ["SnapshotBlobStore capability not implemented"], ["held_backend_unqualified:blob_capability_unavailable"])
    return [in_memory, sqlite_result, blob]


def qualify_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return a defensive copy; qualification can never rewrite eligibility true."""
    qualified = dict(result)
    qualified["production_eligibility"] = False
    qualified["trust_domain"] = "same_process_reference"
    qualified["receipt_binding_level"] = "reference_integrity_only"
    qualified["same_process_arbitrary_code_or_introspection"] = "out_of_scope"
    qualified["same_process_adversarial_forgery_resistance"] = "unsupported"
    if not set(REQUIRED).issubset(set(qualified.get("executed_test_ids", []))) and qualified.get("capability") == "supported":
        qualified["capability"] = "unavailable"
        qualified.setdefault("hold_reasons", []).append("held_required_test_missing")
    return qualified
