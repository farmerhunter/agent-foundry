#!/usr/bin/env python3
"""Synthetic-only SQLite pointer adapter fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

sys_path = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(sys_path))
from practice_catalog_snapshot import ValidationFailure
import practice_catalog_snapshot as catalog
from sqlite_pointer_store import SQLitePointerStore


def expect(name: str, condition: bool, errors: list[str]) -> None:
    print(f"{name}: {'ok' if condition else 'FAIL'}")
    if not condition:
        errors.append(name)


def main() -> int:
    errors: list[str] = []
    first_hash = "a" * 64
    second_hash = "b" * 64
    with tempfile.TemporaryDirectory(prefix="synthetic-pointer-") as temp:
        db = Path(temp) / "pointer.sqlite3"
        try:
            SQLitePointerStore(Path(temp).parent / "candidate-vault" / "pointer.sqlite3", first_hash, Path(temp))
            errors.append("persistent-path-rejected: accepted")
        except ValidationFailure:
            expect("persistent-path-rejected", True, errors)
        with tempfile.TemporaryDirectory(prefix="ordinary-s1c-review-") as generic_temp:
            generic_root = Path(generic_temp)
            try:
                SQLitePointerStore(generic_root / "pointer.sqlite3", first_hash, generic_root)
                errors.append("generic-temp-root-rejected: accepted")
            except ValidationFailure:
                expect("generic-temp-root-rejected", True, errors)
        one = SQLitePointerStore(db, first_hash, Path(temp))
        two = SQLitePointerStore(db, first_hash, Path(temp))
        capability = one.as_capability()
        expect("versioned-capability", capability.format == catalog.CAPABILITY_FORMAT and capability.version == 1 and capability.backend is one, errors)
        receipt = one.read()
        expect("read-receipt", receipt.operation == "read" and receipt.generation == 0 and receipt.snapshot_hash == first_hash, errors)
        committed = one.compare_and_set(receipt.generation, second_hash)
        expect("first-cas", committed is not None and committed.snapshot_hash == second_hash, errors)
        conflict = two.compare_and_set(0, first_hash)
        expect("failed-cas-leaves-new-pointer", conflict is None and two.read().snapshot_hash == second_hash, errors)
        one.close()
        two.close()
        reopened = SQLitePointerStore(db, first_hash, Path(temp))
        expect("reopen-reads-committed-pointer", reopened.read().snapshot_hash == second_hash and reopened.read().generation == 1, errors)
        lost_receipt = reopened.compare_and_set(1, first_hash)
        reopened.close()
        recovered = SQLitePointerStore(db, first_hash, Path(temp))
        expect("cas-before-receipt-recovery", lost_receipt is not None and recovered.read().snapshot_hash == first_hash, errors)
        held = recovered.rollback(2, second_hash, None)
        expect("rollback-requires-authorization", held["state"] == "held_rollback_authorization_missing", errors)
        rolled = recovered.rollback(2, second_hash, "synthetic authorization reference")
        expect("authorized-rollback", rolled["state"] == "rolled_back" and recovered.read().snapshot_hash == second_hash, errors)
        retention = recovered.retention_receipt({second_hash})
        expect("retention-receipt-only", retention["removed_hashes"] == [] and retention["disposed_hashes"] == [] and db.exists(), errors)
        recovered.close()
    if errors:
        print("SQLite pointer store tests failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("SQLite pointer store tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
