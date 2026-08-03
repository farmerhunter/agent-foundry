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
    if errors:
        print("Practice catalog snapshot tests failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Practice catalog snapshot tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
