#!/usr/bin/env python3
"""Qualification-only embedded SQLite catalog store for synthetic fixtures."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Mapping

from practice_catalog_snapshot import ValidationFailure, _valid_hash


class SQLitePracticeCatalogStore:
    qualification_state = "production_candidate"

    def __init__(self, db_path: str | Path, sandbox_root: str | Path):
        root = Path(sandbox_root).expanduser()
        path = Path(db_path).expanduser()
        if not root.is_absolute() or not root.exists() or not root.is_dir() or not root.name.startswith("synthetic-catalog-"):
            raise ValidationFailure("invalid caller sandbox root")
        if not path.is_absolute():
            raise ValidationFailure("catalog path must be absolute")
        self.root = root.resolve(); self.path = path.resolve()
        try: self.path.relative_to(self.root)
        except ValueError as exc: raise ValidationFailure("catalog path escapes sandbox") from exc
        self._db = sqlite3.connect(str(self.path), timeout=2.0)
        self._db.execute("CREATE TABLE IF NOT EXISTS snapshots (hash TEXT PRIMARY KEY, manifest TEXT NOT NULL, index_text TEXT NOT NULL, blobs TEXT NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS pointer (slot INTEGER PRIMARY KEY CHECK(slot=1), generation INTEGER NOT NULL, hash TEXT NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS transactions (txid TEXT PRIMARY KEY, generation INTEGER NOT NULL, hash TEXT NOT NULL)")
        if self._db.execute("SELECT 1 FROM pointer WHERE slot=1").fetchone() is None:
            self._db.execute("INSERT INTO pointer VALUES(1,0,?)", ("0" * 64,)); self._db.commit()

    @staticmethod
    def _check_snapshot(snapshot_hash: str, manifest: str, index_text: str, blobs: Mapping[str, bytes]) -> None:
        if not _valid_hash(snapshot_hash) or hashlib.sha256(manifest.encode()).hexdigest() != snapshot_hash:
            raise ValidationFailure("snapshot manifest hash mismatch")
        if not isinstance(index_text, str) or not isinstance(blobs, Mapping): raise ValidationFailure("invalid snapshot payload")
        for path, content in blobs.items():
            if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or not isinstance(content, bytes): raise ValidationFailure("invalid blob path/content")

    def read_pointer(self) -> tuple[int, str]:
        row = self._db.execute("SELECT generation,hash FROM pointer WHERE slot=1").fetchone()
        if row is None or type(row[0]) is not int or row[0] < 0 or not _valid_hash(row[1]): raise ValidationFailure("pointer corruption")
        return row[0], row[1]

    def read_catalog(self) -> dict[str, object]:
        generation, snapshot_hash = self.read_pointer()
        if snapshot_hash == "0" * 64: raise ValidationFailure("snapshot missing")
        row = self._db.execute("SELECT manifest,index_text,blobs FROM snapshots WHERE hash=?", (snapshot_hash,)).fetchone()
        if row is None: raise ValidationFailure("snapshot blob missing")
        manifest, index_text, blobs = row
        decoded = {path: bytes.fromhex(value) for path, value in json.loads(blobs).items()}
        self._check_snapshot(snapshot_hash, manifest, index_text, decoded)
        return {"generation": generation, "snapshot_hash": snapshot_hash, "manifest": manifest, "index": index_text, "blobs": decoded}

    def commit(self, expected_generation: int, snapshot_hash: str, manifest: str, index_text: str, blobs: Mapping[str, bytes], txid: str) -> dict[str, object]:
        if type(expected_generation) is not int or expected_generation < 0 or not isinstance(txid, str) or not txid: raise ValidationFailure("invalid transaction")
        self._check_snapshot(snapshot_hash, manifest, index_text, blobs)
        self._db.execute("BEGIN IMMEDIATE")
        prior = self._db.execute("SELECT generation,hash FROM pointer WHERE slot=1").fetchone()
        existing = self._db.execute("SELECT generation,hash FROM transactions WHERE txid=?", (txid,)).fetchone()
        if existing is not None:
            self._db.commit(); return {"state": "committed_idempotent", "generation": existing[0], "snapshot_hash": existing[1], "txid": txid}
        if prior[0] != expected_generation:
            self._db.rollback(); return {"state": "held_cas_conflict", "generation": prior[0], "snapshot_hash": prior[1]}
        self._db.execute("INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?)", (snapshot_hash, manifest, index_text, json.dumps({p: c.hex() for p,c in blobs.items()}, sort_keys=True)))
        self._db.execute("UPDATE pointer SET generation=?,hash=? WHERE slot=1", (expected_generation + 1, snapshot_hash))
        self._db.execute("INSERT INTO transactions VALUES(?,?,?)", (txid, expected_generation + 1, snapshot_hash)); self._db.commit()
        return {"state": "committed", "generation": expected_generation + 1, "snapshot_hash": snapshot_hash, "txid": txid}

    def rollback(self, expected_generation: int, snapshot_hash: str, authorization: str | None) -> dict[str, object]:
        if not authorization or not authorization.strip(): return {"state": "held_rollback_authorization_missing"}
        if not _valid_hash(snapshot_hash): raise ValidationFailure("invalid rollback hash")
        row = self._db.execute("SELECT manifest,index_text,blobs FROM snapshots WHERE hash=?", (snapshot_hash,)).fetchone()
        if row is None: raise ValidationFailure("rollback snapshot missing")
        manifest, index_text, encoded = row
        blobs = {path: bytes.fromhex(value) for path, value in json.loads(encoded).items()}
        return self.commit(expected_generation, snapshot_hash, manifest, index_text, blobs, "rollback:" + authorization)

    def backup_receipt(self) -> dict[str, object]:
        generation, snapshot_hash = self.read_pointer()
        return {"operation": "backup", "generation": generation, "snapshot_hash": snapshot_hash, "receipt_id": f"backup:{generation}:{snapshot_hash[:12]}"}

    def restore_receipt(self, backup: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(backup, Mapping) or backup.get("operation") != "backup" or not _valid_hash(backup.get("snapshot_hash")):
            raise ValidationFailure("invalid backup receipt")
        generation, snapshot_hash = self.read_pointer()
        if snapshot_hash != backup["snapshot_hash"] or generation != backup.get("generation"):
            raise ValidationFailure("backup restore pointer mismatch")
        return {"operation": "restore", "generation": generation, "snapshot_hash": snapshot_hash, "receipt_id": f"restore:{generation}:{snapshot_hash[:12]}"}

    def retention_receipt(self, keep_hashes: set[str]) -> dict[str, object]:
        if not keep_hashes or any(not _valid_hash(h) for h in keep_hashes): raise ValidationFailure("invalid retention set")
        return {"operation": "retention", "retained_hashes": sorted(keep_hashes), "removed_hashes": [], "disposed_hashes": []}

    def close(self) -> None: self._db.close()
