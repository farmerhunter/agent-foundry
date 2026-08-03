#!/usr/bin/env python3
"""Focused synthetic fixtures for the S0 practice catalog snapshot contract."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import practice_catalog_snapshot as catalog


def manifest(name: str = "one") -> dict[str, object]:
    return {"format": catalog.SNAPSHOT_FORMAT, "records": [{"path": f"fixtures/{name}.txt", "sha256": hashlib.sha256(name.encode()).hexdigest()}]}


def expect(name: str, condition: bool, detail: object = "") -> list[str]:
    print(f"{name}: {'ok' if condition else 'FAIL'}")
    return [] if condition else [f"{name}: {detail}"]


def main() -> int:
    errors: list[str] = []
    initial = catalog.snapshot("initial", manifest("initial"))
    candidate = catalog.snapshot("candidate", manifest("candidate"))
    snapshots = {initial["manifest_sha256"]: initial}
    store = catalog.PointerStore(initial["manifest_sha256"])

    held = catalog.commit_snapshot(store, snapshots, candidate, 0, "before_cas")
    errors += expect("held_interrupted_before_cas", held["state"] == "held_interrupted_before_cas" and candidate["manifest_sha256"] in snapshots and store.read().generation == 0 and store.read().snapshot_hash == initial["manifest_sha256"] and store.cas_calls == 0)

    conflict = catalog.commit_snapshot(store, snapshots, candidate, 9)
    errors += expect("held_cas_conflict", conflict["state"] == "held_cas_conflict" and store.read().snapshot_hash == initial["manifest_sha256"])

    interrupted = catalog.commit_snapshot(store, snapshots, candidate, 0, "after_cas_before_receipt")
    calls = store.cas_calls
    pinned_after_cas, after_cas_receipt = catalog.pinned_read(store, snapshots)
    errors += expect("after_cas_interruption_pinned_read", pinned_after_cas == candidate and after_cas_receipt.snapshot_hash == candidate["manifest_sha256"] and store.cas_calls == calls)
    recovered = catalog.recover_receipt(store, interrupted)
    errors += expect("committed_receipt_recovered", recovered["state"] == "committed_receipt_recovered" and store.read().snapshot_hash == candidate["manifest_sha256"] and store.cas_calls == calls)

    bad = dict(candidate)
    bad["manifest_sha256"] = "0" * 64
    invalid = catalog.commit_snapshot(store, snapshots, bad, 1)
    errors += expect("held_validation_failure", invalid["state"] == "held_validation_failure" and store.read().generation == 1)

    missing_auth = catalog.rollback(store, 1, initial["manifest_sha256"], None)
    errors += expect("held_rollback_authorization_missing", missing_auth["state"] == "held_rollback_authorization_missing" and store.read().snapshot_hash == candidate["manifest_sha256"])

    pinned, receipt = catalog.pinned_read(store, snapshots)
    errors += expect("pinned_read_no_fallback", pinned == candidate and receipt.snapshot_hash == candidate["manifest_sha256"])
    authorized = catalog.rollback(store, 1, initial["manifest_sha256"], "#426-G human authorization receipt")
    errors += expect("authorized_rollback_receipt", authorized["state"] == "rolled_back" and authorized["pointer"].operation == "rollback" and store.read().snapshot_hash == initial["manifest_sha256"])
    missing = catalog.PointerStore("f" * 64)
    try:
        catalog.pinned_read(missing, snapshots)
        errors.append("missing_pointer_target: accepted")
    except catalog.ValidationFailure:
        errors += expect("missing_pointer_target", True)
    try:
        catalog.pinned_read(object(), snapshots)  # type: ignore[arg-type]
        errors.append("unknown_pointer_capability: accepted")
    except catalog.ValidationFailure:
        errors += expect("unknown_pointer_capability", True)

    for label, malformed in [("bad_path", {"format": catalog.SNAPSHOT_FORMAT, "records": [{"path": "../escape", "sha256": "a" * 64}]}), ("bad_hash", {"format": catalog.SNAPSHOT_FORMAT, "records": [{"path": "ok", "sha256": "bad"}]})]:
        try:
            catalog.snapshot(label, malformed)
            errors.append(f"{label}: accepted")
        except catalog.ValidationFailure:
            errors += expect(label, True)
    retention = catalog.retain_snapshots(snapshots, {initial["manifest_sha256"]})
    errors += expect("retention_receipt_no_disposal", retention["operation"] == "retention" and retention["retained_hashes"] == [initial["manifest_sha256"]] and not retention["removed_hashes"] and not retention["disposed_hashes"] and initial["manifest_sha256"] in snapshots and candidate["manifest_sha256"] in snapshots)

    practice_text = "---\nid: SYN-001\n---\nSynthetic only.\n"
    index_text = "schema_version: 1\n\npractices:\n  - id: SYN-001\n    path: practices/synthetic/SYN-001.md\n"
    files = {
        "indexes/practice_index.yaml": index_text,
        "practices/synthetic/SYN-001.md": practice_text,
    }
    view_manifest = {
        "format": catalog.SNAPSHOT_FORMAT,
        "records": [
            {"path": path, "sha256": hashlib.sha256(text.encode()).hexdigest()}
            for path, text in files.items()
        ],
    }
    view = catalog.snapshot("synthetic-view", view_manifest, files)
    view_store = catalog.PointerStore(view["manifest_sha256"])
    view_result = catalog.injected_snapshot_view(view_store, {view["manifest_sha256"]: view}, "SYN-001")
    errors += expect("injected-view-pins-once", view_result["snapshot_hash"] == view["manifest_sha256"] and view_store.read_calls == 1 and view_result["practice"] == practice_text)
    for label, bad_store, bad_snapshots, bad_id in [
        ("injected-view-unknown-capability", object(), {view["manifest_sha256"]: view}, "SYN-001"),
        ("injected-view-missing-entry", view_store, {view["manifest_sha256"]: view}, "UNKNOWN"),
    ]:
        try:
            catalog.injected_snapshot_view(bad_store, bad_snapshots, bad_id)  # type: ignore[arg-type]
            errors.append(f"{label}: accepted")
        except catalog.ValidationFailure:
            errors += expect(label, True)
    bad_files = dict(files)
    bad_files["practices/synthetic/SYN-001.md"] = "working-tree fallback"
    bad_view = dict(view)
    bad_view["files"] = bad_files
    try:
        catalog.injected_snapshot_view(catalog.PointerStore(view["manifest_sha256"]), {view["manifest_sha256"]: bad_view}, "SYN-001")
        errors.append("injected-view-working-tree-fallback: accepted")
    except catalog.ValidationFailure:
        errors += expect("injected-view-working-tree-fallback", True)

    multi_files = {
        "indexes/practice_index.yaml": "schema_version: 1\npractices:\n  - id: SYN-001\n    path: practices/synthetic/SYN-001.md\n  - id: SYN-002\n    path: practices/synthetic/SYN-002.md\n",
        "practices/synthetic/SYN-001.md": "---\nid: SYN-001\n---\nSynthetic one.\n",
        "practices/synthetic/SYN-002.md": "---\nid: SYN-002\n---\nSynthetic two.\n",
    }
    multi_manifest = {"format": catalog.SNAPSHOT_FORMAT, "records": [{"path": path, "sha256": hashlib.sha256(text.encode()).hexdigest()} for path, text in multi_files.items()]}
    multi = catalog.snapshot("synthetic-multi", multi_manifest, multi_files)
    multi_store = catalog.PointerStore(multi["manifest_sha256"])
    full = catalog.pinned_catalog_view(multi_store, {multi["manifest_sha256"]: multi})
    errors += expect("pinned-catalog-multiple", len(full["records"]) == 2 and multi_store.read_calls == 1)
    try:
        catalog.pinned_catalog_view(catalog.PointerStoreCapability.__new__(catalog.PointerStoreCapability), {multi["manifest_sha256"]: multi})  # type: ignore[arg-type]
        errors.append("forged-capability: accepted")
    except catalog.ValidationFailure:
        errors += expect("forged-capability", True)
    class ForgedBackend:
        _capability_issuer = "sqlite_pointer_store_v1"

        def read(self):
            return None
        def compare_and_set(self, expected_generation: int, new_hash: str):
            return None
    try:
        catalog.issue_capability(ForgedBackend())
        errors.append("forged-readable-backend: accepted")
    except catalog.ValidationFailure:
        errors += expect("forged-readable-backend", True)
    class ForgedStore(catalog.PointerStore):
        def read(self):
            return catalog.PointerReceipt("read", 0, multi["manifest_sha256"], "forged")
    try:
        catalog.issue_capability(ForgedStore(multi["manifest_sha256"]))
        errors.append("forged-subclass: accepted")
    except catalog.ValidationFailure:
        errors += expect("forged-subclass", True)
    monkeypatched = catalog.PointerStore(multi["manifest_sha256"])
    monkeypatched.read = lambda: catalog.PointerReceipt("read", 0, multi["manifest_sha256"], "forged-valid")  # type: ignore[method-assign]
    try:
        catalog.pinned_catalog_view(catalog.issue_capability(monkeypatched), {multi["manifest_sha256"]: multi})
        errors.append("monkeypatched-receipt: accepted")
    except catalog.ValidationFailure:
        errors += expect("monkeypatched-receipt", True)
    captured_store = catalog.PointerStore(multi["manifest_sha256"])
    captured = captured_store.read()
    captured_store.read = lambda: catalog.PointerReceipt("read", captured.generation, "c" * 64, captured.receipt_id, signature=captured.signature)  # type: ignore[method-assign]
    try:
        catalog.pinned_catalog_view(catalog.issue_capability(captured_store), {multi["manifest_sha256"]: multi})
        errors.append("captured-receipt-rewrite: accepted")
    except catalog.ValidationFailure:
        errors += expect("captured-receipt-rewrite", True)
    non_read_store = catalog.PointerStore(multi["manifest_sha256"])
    non_read = non_read_store.compare_and_set(0, "d" * 64)
    non_read_store.read = lambda: non_read  # type: ignore[method-assign]
    try:
        catalog.pinned_catalog_view(catalog.issue_capability(non_read_store), {multi["manifest_sha256"]: multi})
        errors.append("signed-non-read-receipt: accepted")
    except catalog.ValidationFailure:
        errors += expect("signed-non-read-receipt", True)
    for label, mutate in [("duplicate-id", lambda f: f.update({"indexes/practice_index.yaml": f["indexes/practice_index.yaml"].replace("SYN-002", "SYN-001")})), ("tampered-entry", lambda f: f.update({"practices/synthetic/SYN-002.md": "---\nid: SYN-999\n---\nTampered.\n"}))]:
        altered = dict(multi_files)
        mutate(altered)
        altered_value = dict(multi)
        altered_value["files"] = altered
        try:
            catalog.pinned_catalog_view(catalog.PointerStore(multi["manifest_sha256"]), {multi["manifest_sha256"]: altered_value})
            errors.append(f"{label}: accepted")
        except catalog.ValidationFailure:
            errors += expect(label, True)
    if errors:
        print("Practice catalog snapshot tests failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Practice catalog snapshot tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
