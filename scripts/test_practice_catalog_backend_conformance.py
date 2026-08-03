#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from practice_catalog_backend_conformance import qualify_result, run_pointer_suite, run_reference_conformance
from practice_catalog_snapshot import PointerReceipt, PointerStoreCapability, ValidationFailure, issue_capability
import practice_catalog_snapshot as catalog
import practice_catalog_backend_conformance as harness
from sqlite_pointer_store import SQLitePointerStore
import tempfile
from pathlib import Path

def main() -> int:
    results = run_reference_conformance()
    errors = []
    for result in results:
        print(f"{result['adapter_id']}: {result['capability']}")
        if result["production_eligibility"] or result["adapter_class"] != "reference" or not result["privacy_safe"]:
            errors.append(result["adapter_id"])
        if result["trust_domain"] != "same_process_reference" or result["receipt_binding_level"] != "reference_integrity_only" or result["same_process_adversarial_forgery_resistance"] != "unsupported":
            errors.append(result["adapter_id"] + ":threat-model")
        if result["adapter_id"] != "synthetic-blob" and result["capability"] != "supported":
            errors.append(result["adapter_id"] + ":unsupported")
        if result["adapter_id"] == "synthetic-blob" and result["capability"] != "unsupported":
            errors.append("blob:claimed-supported")
    forged = {"adapter_id": "forged", "adapter_class": "reference", "capability": "supported", "executed_test_ids": [], "production_eligibility": True}
    rewritten = qualify_result(forged)
    if rewritten["production_eligibility"] or rewritten["capability"] == "supported":
        errors.append("qualification-rewrite")
    class SelfAttesting:
        _capability_issuer = "sqlite_pointer_store_v1"
        def read(self): return None
        def compare_and_set(self, generation, snapshot_hash): return None
    try:
        issue_capability(SelfAttesting())
        errors.append("self-attestation-accepted")
    except ValidationFailure:
        pass
    try:
        PointerStoreCapability(object())
        errors.append("forged-capability-accepted")
    except ValidationFailure:
        pass
    with tempfile.TemporaryDirectory(prefix="synthetic-pointer-") as temp:
        outside = Path(temp).parent / "escape.sqlite3"
        try:
            SQLitePointerStore(outside, "a" * 64, temp)
            errors.append("temp-escape-accepted")
        except ValidationFailure:
            pass
    missing = qualify_result({"adapter_id": "missing", "adapter_class": "reference", "capability": "supported", "executed_test_ids": []})
    if missing["capability"] != "unavailable" or "held_required_test_missing" not in missing["hold_reasons"]:
        errors.append("missing-required-test")
    rewritten_backend = catalog.PointerStore("a" * 64)
    original = rewritten_backend.read()
    rewritten_backend.read = lambda: PointerReceipt("read", original.generation, "b" * 64, original.receipt_id, signature=original.signature)  # type: ignore[method-assign]
    rewritten_result = run_pointer_suite("rewritten-receipt", rewritten_backend)
    if rewritten_result["capability"] != "unavailable" or not any("held_backend_unqualified" in reason for reason in rewritten_result["hold_reasons"]):
        errors.append("rewritten-receipt-not-held")
    forged_capability = PointerStoreCapability.__new__(PointerStoreCapability)
    object.__setattr__(forged_capability, "backend", catalog.PointerStore("a" * 64))
    object.__setattr__(forged_capability, "format", "practice_catalog_capability_v1")
    object.__setattr__(forged_capability, "version", 1)
    try:
        from practice_catalog_backend_conformance import _read
        _read(forged_capability)
        errors.append("forged-new-capability-accepted")
    except ValidationFailure:
        pass
    real = issue_capability(catalog.PointerStore("a" * 64))
    clone = PointerStoreCapability.__new__(PointerStoreCapability)
    for field in ("backend", "format", "version", "_seal"):
        object.__setattr__(clone, field, getattr(real, field))
    registry = getattr(harness, "_ISSUED_CAPABILITIES", None)
    if isinstance(registry, list):
        registry.append(clone)
    try:
        harness._read(clone)
        errors.append("forged-clone-registry-tamper-accepted")
    except ValidationFailure:
        pass
    if errors:
        print("errors:", errors)
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
