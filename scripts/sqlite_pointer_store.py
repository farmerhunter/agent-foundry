#!/usr/bin/env python3
"""Disposable SQLite pointer capability for synthetic snapshot tests only."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from practice_catalog_snapshot import POINTER_FORMAT, PointerReceipt, PointerStoreCapability, ValidationFailure, _make_receipt, _register_receipt_backend, _valid_hash


class SQLitePointerStore:
    """Store only generation and snapshot_hash under an explicit temp path."""

    def __init__(self, db_path: str | Path, initial_hash: str, disposable_root: str | Path | None = None):
        path = Path(db_path).expanduser()
        if disposable_root is None:
            raise ValidationFailure("caller-supplied disposable root required")
        root = Path(disposable_root).expanduser()
        if not root.is_absolute() or not root.exists() or not root.is_dir() or not root.name.startswith("synthetic-pointer-"):
            raise ValidationFailure("invalid disposable TemporaryDirectory root")
        root = root.resolve()
        if not path.is_absolute():
            raise ValidationFailure("SQLite pointer path must be absolute")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValidationFailure("SQLite pointer must be under TemporaryDirectory") from exc
        lowered = str(resolved).lower()
        if any(token in lowered for token in ("vault", "candidate", "practices", "agent-foundry/config")):
            raise ValidationFailure("SQLite pointer path resembles persistent or Vault data")
        if not _valid_hash(initial_hash):
            raise ValidationFailure("invalid initial pointer hash")
        self.path = resolved
        _register_receipt_backend(self)
        self._connection = sqlite3.connect(str(resolved), timeout=2.0)
        self._connection.execute("CREATE TABLE IF NOT EXISTS pointer (slot INTEGER PRIMARY KEY CHECK (slot = 1), generation INTEGER NOT NULL, snapshot_hash TEXT NOT NULL)")
        row = self._connection.execute("SELECT generation, snapshot_hash FROM pointer WHERE slot = 1").fetchone()
        if row is None:
            self._connection.execute("INSERT INTO pointer(slot, generation, snapshot_hash) VALUES (1, 0, ?)", (initial_hash,))
            self._connection.commit()
        elif not isinstance(row[0], int) or not _valid_hash(row[1]):
            self._connection.close()
            raise ValidationFailure("invalid persisted pointer")
        self.read_calls = 0
        self.cas_calls = 0

    def read(self) -> PointerReceipt:
        row = self._connection.execute("SELECT generation, snapshot_hash FROM pointer WHERE slot = 1").fetchone()
        if row is None:
            raise ValidationFailure("pointer row missing")
        self.read_calls += 1
        generation, snapshot_hash = row
        receipt_id = f"read:{generation}:{snapshot_hash[:12]}"
        return _make_receipt(self, "read", generation, snapshot_hash, receipt_id)

    def compare_and_set(self, expected_generation: int, new_hash: str) -> PointerReceipt | None:
        if not isinstance(expected_generation, int) or not _valid_hash(new_hash):
            raise ValidationFailure("invalid CAS input")
        self.cas_calls += 1
        self._connection.execute("BEGIN IMMEDIATE")
        cursor = self._connection.execute(
            "UPDATE pointer SET generation = generation + 1, snapshot_hash = ? WHERE slot = 1 AND generation = ?",
            (new_hash, expected_generation),
        )
        if cursor.rowcount != 1:
            self._connection.rollback()
            return None
        self._connection.commit()
        row = self._connection.execute("SELECT generation, snapshot_hash FROM pointer WHERE slot = 1").fetchone()
        receipt_id = f"cas:{row[0]}:{row[1][:12]}"
        return _make_receipt(self, "cas", row[0], row[1], receipt_id)

    def close(self) -> None:
        self._connection.close()

    def as_capability(self) -> PointerStoreCapability:
        from practice_catalog_snapshot import issue_capability
        return issue_capability(self)

    def rollback(self, expected_generation: int, prior_hash: str, authorization: str | None) -> dict[str, object]:
        before = self.read()
        if not isinstance(authorization, str) or not authorization.strip():
            return {"state": "held_rollback_authorization_missing", "pointer": before}
        receipt = self.compare_and_set(expected_generation, prior_hash)
        if receipt is None:
            return {"state": "held_cas_conflict", "pointer": self.read()}
        return {"state": "rolled_back", "pointer": PointerReceipt("rollback", receipt.generation, receipt.snapshot_hash, f"rollback:{receipt.generation}:{receipt.snapshot_hash[:12]}")}

    @staticmethod
    def retention_receipt(keep_hashes: set[str]) -> dict[str, object]:
        if not keep_hashes or any(not _valid_hash(value) for value in keep_hashes):
            raise ValidationFailure("invalid retention set")
        return {"operation": "retention", "retained_hashes": sorted(keep_hashes), "removed_hashes": [], "disposed_hashes": []}


__all__ = ["SQLitePointerStore"]
