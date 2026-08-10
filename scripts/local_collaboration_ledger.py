"""Project-local, privacy-safe SQLite collaboration ledger.

This module deliberately contains no GitHub, adapter, runtime, or Vault routing.
It provides only the durable local ledger primitives used by later orchestration.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import stat
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "1.0.0"
GENESIS = "0" * 64


class LedgerError(RuntimeError):
    """Base error; callers must treat errors as fail-closed."""


class LedgerIntegrityError(LedgerError):
    pass


class LedgerConflictError(LedgerError):
    pass


class LedgerPermissionError(LedgerError):
    pass


@dataclass(frozen=True)
class LedgerEvent:
    sequence: int
    event_id: str
    event_type: str
    payload: Mapping[str, Any]
    payload_hash: str
    previous_hash: str
    event_hash: str
    created_at: str
    actor: str | None
    source: str | None


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


class LocalCollaborationLedger:
    """Own one project-local collaboration.db and its rebuildable metadata."""

    def __init__(self, project_id: str | None = None, *, projects_root: str | Path | None = None,
                 db_path: str | Path | None = None, create: bool = True):
        if db_path is not None and project_id is not None:
            raise ValueError("provide project_id or db_path, not both")
        if db_path is None:
            project_id = project_id or str(uuid.uuid4())
            try:
                project_id = str(uuid.UUID(project_id))
            except ValueError as exc:
                raise ValueError("project_id must be an opaque UUID") from exc
            root = Path(projects_root or (Path.home() / ".agent-foundry" / "projects"))
            self.project_id = project_id
            self.directory = root / project_id
            self.path = self.directory / "collaboration.db"
        else:
            self.path = Path(db_path).expanduser()
            self.directory = self.path.parent
            self.project_id = project_id
        if create:
            existed_directory = self.directory.exists()
            self.directory.mkdir(parents=True, exist_ok=True)
            if not existed_directory:
                os.chmod(self.directory, 0o700)
            if not self.path.exists():
                self.path.touch(mode=0o600)
            elif _mode(self.path) != 0o600:
                raise LedgerPermissionError(f"database must be 0600: {self.path}")
        self._assert_private()
        self._conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._configure()
        self._init_schema()
        self.verify()

    @classmethod
    def create_project(cls, *, projects_root: str | Path | None = None, project_id: str | None = None) -> "LocalCollaborationLedger":
        return cls(project_id, projects_root=projects_root)

    def close(self) -> None:
        self._conn.close()

    def _assert_private(self) -> None:
        if not self.directory.exists() or _mode(self.directory) != 0o700:
            raise LedgerPermissionError(f"project directory must be 0700: {self.directory}")
        if self.path.exists() and _mode(self.path) != 0o600:
            raise LedgerPermissionError(f"database must be 0600: {self.path}")

    def _configure(self) -> None:
        c = self._conn
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA trusted_schema=OFF")
        c.execute("PRAGMA busy_timeout=5000")
        c.execute("PRAGMA wal_autocheckpoint=1000")
        checks = {"foreign_keys": "1", "trusted_schema": "0", "busy_timeout": "5000"}
        for key, expected in checks.items():
            if str(c.execute(f"PRAGMA {key}").fetchone()[0]) != expected:
                raise LedgerIntegrityError(f"required pragma not active: {key}")
        self._enforce_sidecar_modes()

    def _enforce_sidecar_modes(self) -> None:
        """Keep SQLite's mutable sidecars within the same private directory policy."""
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(self.path) + suffix)
            if sidecar.exists():
                os.chmod(sidecar, 0o600)

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS ledger_metadata (
              key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
              sequence INTEGER PRIMARY KEY,
              event_id TEXT NOT NULL UNIQUE,
              event_type TEXT NOT NULL,
              payload TEXT NOT NULL,
              payload_hash TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL,
              actor TEXT,
              source TEXT
            );
            CREATE TABLE IF NOT EXISTS holds (
              event_id TEXT PRIMARY KEY, reason TEXT NOT NULL, payload_hash TEXT,
              observed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_type_idx ON events(event_type);
        """)
        row = self._conn.execute("SELECT value FROM ledger_metadata WHERE key='schema_version'").fetchone()
        if row is None:
            pid = self.project_id or str(uuid.uuid4())
            self.project_id = pid
            self._conn.execute("INSERT INTO ledger_metadata(key,value) VALUES('schema_version',?)", (SCHEMA_VERSION,))
            self._conn.execute("INSERT INTO ledger_metadata(key,value) VALUES('project_id',?)", (pid,))
        elif row[0] != SCHEMA_VERSION:
            raise LedgerIntegrityError(f"unsupported schema version: {row[0]}")
        stored = self._conn.execute("SELECT value FROM ledger_metadata WHERE key='project_id'").fetchone()[0]
        if self.project_id and stored != self.project_id:
            raise LedgerIntegrityError("project identity mismatch")
        self.project_id = stored

    def metadata(self) -> dict[str, str]:
        return {r["key"]: r["value"] for r in self._conn.execute("SELECT key,value FROM ledger_metadata")}

    def _event_hash(self, sequence: int, event_id: str, event_type: str, payload_hash: str,
                    previous_hash: str, created_at: str, actor: str | None, source: str | None) -> str:
        return _hash([sequence, event_id, event_type, payload_hash, previous_hash, created_at, actor, source])

    def _validate_event(self, event_type: str, payload: Mapping[str, Any], event_id: str | None) -> str:
        if not isinstance(event_type, str) or not event_type or len(event_type) > 128:
            raise ValueError("event_type must be a non-empty bounded string")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        if event_id is None:
            event_id = str(uuid.uuid4())
        try:
            uuid.UUID(event_id)
        except ValueError as exc:
            raise ValueError("event_id must be a UUID") from exc
        encoded = _canonical(payload)
        if len(encoded.encode("utf-8")) > 64 * 1024:
            raise ValueError("payload exceeds 64 KiB")
        forbidden = {"transcript", "raw_transcript", "tool_output", "prompt", "secret", "native_history"}
        if forbidden.intersection(payload):
            raise ValueError("privacy-forbidden payload field")
        return event_id

    def append_event(self, event_type: str, payload: Mapping[str, Any], *, event_id: str | None = None,
                     actor: str | None = None, source: str | None = None) -> LedgerEvent:
        return self.append_batch([{"event_type": event_type, "payload": payload, "event_id": event_id,
                                   "actor": actor, "source": source}])[0]

    def append_batch(self, events: Iterable[Mapping[str, Any]]) -> list[LedgerEvent]:
        items = list(events)
        if not items:
            return []
        normalized = []
        for item in items:
            eid = self._validate_event(item.get("event_type"), item.get("payload"), item.get("event_id"))
            normalized.append((eid, item["event_type"], item["payload"], item.get("actor"), item.get("source")))
        c = self._conn
        c.execute("BEGIN IMMEDIATE")
        try:
            result = []
            last = c.execute("SELECT sequence,event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
            seq, previous = (last["sequence"], last["event_hash"]) if last else (0, GENESIS)
            for eid, etype, payload, actor, source in normalized:
                ph = _hash(payload)
                existing = c.execute("SELECT * FROM events WHERE event_id=?", (eid,)).fetchone()
                if existing:
                    if existing["payload_hash"] != ph:
                        c.execute("INSERT OR REPLACE INTO holds VALUES(?,?,?,?)", (eid, "divergent_duplicate", ph, _now()))
                        raise LedgerConflictError(f"divergent duplicate held: {eid}")
                    result.append(self._row_event(existing)); continue
                if c.execute("SELECT 1 FROM holds WHERE event_id=?", (eid,)).fetchone():
                    raise LedgerConflictError(f"event is held: {eid}")
                seq += 1; created = _now()
                eh = self._event_hash(seq, eid, etype, ph, previous, created, actor, source)
                c.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (seq, eid, etype, _canonical(payload), ph, previous, eh, created, actor, source))
                row = c.execute("SELECT * FROM events WHERE sequence=?", (seq,)).fetchone()
                result.append(self._row_event(row)); previous = eh
            c.execute("COMMIT")
            self._enforce_sidecar_modes()
            return result
        except LedgerConflictError:
            # The event batch must roll back, but the conflict is durable evidence.
            # Record it in a separate transaction so reopening remains fail-closed.
            c.execute("ROLLBACK")
            for eid, _etype, payload, _actor, _source in normalized:
                existing = c.execute("SELECT payload_hash FROM events WHERE event_id=?", (eid,)).fetchone()
                if existing and existing["payload_hash"] != _hash(payload):
                    c.execute("BEGIN IMMEDIATE")
                    try:
                        c.execute("INSERT OR IGNORE INTO holds VALUES(?,?,?,?)",
                                  (eid, "divergent_duplicate", _hash(payload), _now()))
                        c.execute("COMMIT")
                    except Exception:
                        c.execute("ROLLBACK")
                        raise
                    break
            raise
        except Exception:
            c.execute("ROLLBACK")
            raise

    def _row_event(self, row: sqlite3.Row) -> LedgerEvent:
        return LedgerEvent(row["sequence"], row["event_id"], row["event_type"], json.loads(row["payload"]),
                            row["payload_hash"], row["previous_hash"], row["event_hash"], row["created_at"], row["actor"], row["source"])

    def list_events(self, *, event_type: str | None = None) -> list[LedgerEvent]:
        q = "SELECT * FROM events"; args: tuple[Any, ...] = ()
        if event_type is not None: q += " WHERE event_type=?"; args = (event_type,)
        q += " ORDER BY sequence"
        return [self._row_event(r) for r in self._conn.execute(q, args)]

    def verify(self) -> bool:
        previous = GENESIS; expected = 1
        for row in self._conn.execute("SELECT * FROM events ORDER BY sequence"):
            if row["sequence"] != expected or row["previous_hash"] != previous or row["payload_hash"] != _hash(json.loads(row["payload"])):
                raise LedgerIntegrityError("ledger sequence or payload chain is invalid")
            actual = self._event_hash(row["sequence"], row["event_id"], row["event_type"], row["payload_hash"], row["previous_hash"], row["created_at"], row["actor"], row["source"])
            if actual != row["event_hash"]: raise LedgerIntegrityError("ledger hash chain is invalid")
            previous = actual; expected += 1
        return True

    def backup(self, destination: str | Path) -> Path:
        dest = Path(destination); dest.parent.mkdir(parents=True, exist_ok=True); os.chmod(dest.parent, 0o700)
        if dest.exists(): os.chmod(dest, 0o600)
        with sqlite3.connect(dest) as target:
            self._conn.backup(target)
        os.chmod(dest, 0o600); return dest

    def integrity_check(self) -> str:
        result = self._conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok": raise LedgerIntegrityError(result)
        self.verify(); return result


__all__ = ["LocalCollaborationLedger", "LedgerEvent", "LedgerError", "LedgerIntegrityError", "LedgerConflictError", "LedgerPermissionError"]
