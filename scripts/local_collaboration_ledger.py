"""Project-local SQLite collaboration authority (no transport or runtime routing)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1.0.0"
GENESIS = "0" * 64
_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_FORBIDDEN = {"transcript", "raw_transcript", "tool_output", "prompt", "secret", "native_history"}


class LedgerError(RuntimeError):
    pass


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
    root: str


def _canonical(value: Any) -> str:
    _validate_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value): raise ValueError("non-finite JSON number")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str): raise ValueError("JSON object keys must be strings")
            _validate_json(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value: _validate_json(item)
        return
    raise ValueError("payload contains a non-JSON value")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(k).lower() in _FORBIDDEN or _contains_forbidden(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden(v) for v in value)
    return False


def _json_depth(value, depth=0):
    if depth > 12: raise ValueError("JSON nesting exceeds 12 levels")
    if isinstance(value, Mapping):
        for item in value.values(): _json_depth(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value: _json_depth(item, depth + 1)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


class LocalCollaborationLedger:
    def __init__(self, project_id: str | None = None, *, projects_root: str | Path | None = None,
                 db_path: str | Path | None = None, create: bool = True):
        if db_path is not None and project_id is not None:
            raise ValueError("provide project_id or db_path, not both")
        if db_path is None:
            project_id = str(uuid.UUID(project_id or str(uuid.uuid4())))
            root = Path(projects_root or Path.home() / ".agent-foundry" / "projects")
            self.project_id, self.directory, self.path = project_id, root / project_id, root / project_id / "collaboration.db"
        else:
            self.path = Path(db_path).expanduser(); self.directory = self.path.parent; self.project_id = project_id
        if create:
            existed = self.directory.exists(); self.directory.mkdir(parents=True, exist_ok=True)
            if not existed: os.chmod(self.directory, 0o700)
            if not self.path.exists(): self.path.touch(mode=0o600)
        elif not self.path.exists() or self.path.is_symlink() or not self.path.is_file():
            raise LedgerIntegrityError("read-only discovery requires an existing regular database")
        self._assert_private()
        if not create:
            self._conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=5, isolation_level=None)
            self._conn.row_factory = sqlite3.Row
            self._read_only_validate()
            self.verify()
            return
        self._conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._configure()
        self._init_schema()
        self.verify()

    @classmethod
    def create_project(cls, *, projects_root=None, project_id=None):
        return cls(project_id, projects_root=projects_root)

    def close(self):
        self._conn.close()

    def _assert_private(self):
        if not self.directory.exists() or _mode(self.directory) != 0o700:
            raise LedgerPermissionError(f"project directory must be 0700: {self.directory}")
        if self.path.exists() and _mode(self.path) != 0o600:
            raise LedgerPermissionError(f"database must be 0600: {self.path}")

    def _enforce_sidecar_modes(self):
        for suffix in ("-wal", "-shm"):
            p = Path(str(self.path) + suffix)
            if p.exists() and _mode(p) != 0o600: raise LedgerPermissionError(f"sidecar must be 0600: {p}")

    def _configure(self):
        c = self._conn
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA foreign_keys=ON"); c.execute("PRAGMA trusted_schema=OFF")
        c.execute("PRAGMA busy_timeout=5000"); c.execute("PRAGMA wal_autocheckpoint=1000")
        expected = {"journal_mode": "wal", "synchronous": "2", "foreign_keys": "1", "trusted_schema": "0", "busy_timeout": "5000", "wal_autocheckpoint": "1000"}
        actual = {k: str(c.execute(f"PRAGMA {k}").fetchone()[0]).lower() for k in expected}
        if actual != expected: raise LedgerPermissionError(f"pragma capability mismatch: {actual}")
        self._pragma_receipt = actual
        self._enforce_sidecar_modes()

    def _read_only_validate(self):
        tables = {r[0] for r in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"ledger_metadata", "events", "project_bindings"}.issubset(tables):
            raise LedgerIntegrityError("candidate schema is incomplete")
        metadata = {r["key"]: r["value"] for r in self._conn.execute("SELECT key,value FROM ledger_metadata")}
        if metadata.get("schema_version") != SCHEMA_VERSION: raise LedgerIntegrityError("candidate schema version mismatch")
        if self.project_id and metadata.get("project_id") != self.project_id: raise LedgerIntegrityError("candidate project mismatch")
        self.project_id = metadata.get("project_id")
        self._pragma_receipt = {k: str(self._conn.execute(f"PRAGMA {k}").fetchone()[0]).lower() for k in ("journal_mode","synchronous","foreign_keys","trusted_schema","busy_timeout","wal_autocheckpoint")}

    def pragma_receipt(self):
        return dict(self._pragma_receipt)

    def _init_schema(self):
        c = self._conn; c.execute("BEGIN IMMEDIATE")
        try:
            statements = [
                "CREATE TABLE IF NOT EXISTS ledger_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS project_bindings (binding_id INTEGER PRIMARY KEY, binding_type TEXT NOT NULL, binding_value TEXT NOT NULL, active INTEGER NOT NULL, bound_at TEXT NOT NULL, decision_receipt TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS binding_decisions (decision_id TEXT PRIMARY KEY, binding_type TEXT NOT NULL, old_value TEXT, new_value TEXT NOT NULL, decided_at TEXT NOT NULL)",
                "CREATE UNIQUE INDEX IF NOT EXISTS active_binding_type_idx ON project_bindings(binding_type) WHERE active=1",
                "CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY,event_id TEXT NOT NULL UNIQUE,event_type TEXT NOT NULL,payload TEXT NOT NULL,payload_hash TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,actor TEXT,source TEXT,root TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS holds (event_id TEXT PRIMARY KEY,reason TEXT NOT NULL,payload_hash TEXT,identity_hash TEXT,observed_at TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS projections (name TEXT PRIMARY KEY,sequence INTEGER NOT NULL,payload TEXT NOT NULL,payload_hash TEXT NOT NULL,updated_at TEXT NOT NULL)",
                "CREATE INDEX IF NOT EXISTS events_type_idx ON events(event_type)",
            ]
            for statement in statements: c.execute(statement)
            row = c.execute("SELECT value FROM ledger_metadata WHERE key='schema_version'").fetchone()
            if row is None:
                pid = self.project_id or str(uuid.uuid4()); self.project_id = pid
                c.execute("INSERT INTO ledger_metadata VALUES('schema_version',?)", (SCHEMA_VERSION,))
                c.execute("INSERT INTO ledger_metadata VALUES('project_id',?)", (pid,))
            elif row[0] != SCHEMA_VERSION: raise LedgerIntegrityError(f"unsupported schema version: {row[0]}")
            stored = c.execute("SELECT value FROM ledger_metadata WHERE key='project_id'").fetchone()[0]
            if self.project_id and stored != self.project_id: raise LedgerIntegrityError("project identity mismatch")
            self.project_id = stored; c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK"); raise

    def metadata(self):
        return {r["key"]: r["value"] for r in self._conn.execute("SELECT key,value FROM ledger_metadata")}

    def bind_project(self, binding_type: str, binding_value: str, *, rebind=False):
        if not binding_type or not binding_value: raise ValueError("binding type/value required")
        c = self._conn; c.execute("BEGIN IMMEDIATE")
        try:
            rows = c.execute("SELECT binding_value FROM project_bindings WHERE binding_type=? AND active=1", (binding_type,)).fetchall()
            if any(r[0] == binding_value for r in rows): c.execute("COMMIT"); return {"binding_type": binding_type, "binding_value": binding_value, "decision_id": None}
            if rows and not rebind: c.execute("COMMIT"); self._record_hold("binding:" + binding_type, "ambiguous_binding", _hash(binding_value)); raise LedgerConflictError("binding requires explicit rebind")
            old = rows[0][0] if rows else None; decision = str(uuid.uuid4()); now = _now()
            if rebind: c.execute("UPDATE project_bindings SET active=0 WHERE binding_type=? AND active=1", (binding_type,))
            c.execute("INSERT INTO project_bindings(binding_type,binding_value,active,bound_at,decision_receipt) VALUES(?,?,?,?,?)", (binding_type, binding_value, 1, now, decision))
            c.execute("INSERT INTO binding_decisions VALUES(?,?,?,?,?)", (decision, binding_type, old, binding_value, now)); c.execute("COMMIT")
        except Exception:
            if c.in_transaction: c.execute("ROLLBACK")
            raise
        return {"binding_type": binding_type, "old_value": old, "new_value": binding_value, "project_id": self.project_id, "decision_id": decision, "decided_at": now}

    def binding_decision(self, decision_id):
        row = self._conn.execute("SELECT * FROM binding_decisions WHERE decision_id=?", (decision_id,)).fetchone()
        return None if row is None else dict(row)

    def resolve_binding(self, binding_type: str) -> str:
        rows = self._conn.execute("SELECT binding_value FROM project_bindings WHERE binding_type=? AND active=1", (binding_type,)).fetchall()
        if len(rows) != 1: raise LedgerConflictError("binding resolution is not exactly one")
        return rows[0][0]

    def _record_hold(self, event_id, reason, payload_hash, identity_hash=None):
        c = self._conn; c.execute("BEGIN IMMEDIATE")
        try:
            c.execute("INSERT OR IGNORE INTO holds VALUES(?,?,?,?,?)", (event_id, reason, payload_hash, identity_hash, _now())); c.execute("COMMIT")
        except Exception: c.execute("ROLLBACK"); raise

    def _validate(self, event_type, payload, event_id, actor, source, root):
        if not isinstance(event_type, str) or not _TYPE.fullmatch(event_type): raise ValueError("invalid event_type")
        if not isinstance(payload, Mapping) or _contains_forbidden(payload): raise ValueError("privacy-forbidden payload")
        if event_id is None: event_id = str(uuid.uuid4())
        uuid.UUID(event_id)
        for value, label in ((actor, "actor"), (source, "source")):
            if value is not None and (not isinstance(value, str) or not value or len(value) > 256 or any(token in value.lower() for token in _FORBIDDEN)): raise ValueError(f"invalid {label}")
        root = root or self.project_id
        if root != self.project_id: raise LedgerConflictError("event root does not match project")
        if len(_canonical(payload).encode()) > 64 * 1024: raise ValueError("payload exceeds 64 KiB")
        return event_id, root

    def _identity_hash(self, payload_hash, event_type, actor, source, root): return _hash([payload_hash, event_type, actor, source, root])

    def _event_hash(self, seq, eid, etype, ph, previous, created, actor, source, root): return _hash([seq,eid,etype,ph,previous,created,actor,source,root])

    def append_event(self, event_type, payload, *, event_id=None, actor=None, source=None, root=None):
        return self.append_batch([{"event_type":event_type,"payload":payload,"event_id":event_id,"actor":actor,"source":source,"root":root}])[0]

    def accept_compact_event(self, event_type, payload, *, event_id=None, actor=None, source=None, root=None):
        """Commit one privacy-safe compact onboarding event through the same authority."""
        return self.append_event(event_type, payload, event_id=event_id, actor=actor, source=source, root=root)

    def accept_compact_events(self, events):
        return self.append_batch(events)

    def append_batch(self, events: Iterable[Mapping[str, Any]]):
        events = list(events)
        if len(events) > 100: raise ValueError("batch exceeds 100 events")
        normalized = []
        for item in events:
            if not isinstance(item, Mapping) or set(item) - {"event_type","payload","event_id","actor","source","root"}: raise ValueError("unknown event input key")
            eid, root = self._validate(item.get("event_type"), item.get("payload"), item.get("event_id"), item.get("actor"), item.get("source"), item.get("root"))
            _json_depth(item["payload"])
            normalized.append((eid,item["event_type"],item["payload"],item.get("actor"),item.get("source"),root))
        if sum(len(_canonical(item["payload"]).encode()) for item in events) > 1024 * 1024: raise ValueError("batch exceeds 1 MiB")
        if not normalized: return []
        c = self._conn; c.execute("BEGIN IMMEDIATE")
        try:
            result=[]; last=c.execute("SELECT sequence,event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone(); seq,previous=(last["sequence"],last["event_hash"]) if last else (0,GENESIS)
            for eid,etype,payload,actor,source,root in normalized:
                ph=_hash(payload); ih=self._identity_hash(ph,etype,actor,source,root)
                if c.execute("SELECT 1 FROM holds WHERE event_id=?",(eid,)).fetchone(): raise LedgerConflictError(f"event is held: {eid}")
                existing=c.execute("SELECT * FROM events WHERE event_id=?",(eid,)).fetchone()
                if existing:
                    oldih=self._identity_hash(existing["payload_hash"],existing["event_type"],existing["actor"],existing["source"],existing["root"])
                    if oldih != ih: raise LedgerConflictError(f"divergent duplicate held: {eid}")
                    result.append(self._row(existing)); continue
                seq += 1; created=_now(); eh=self._event_hash(seq,eid,etype,ph,previous,created,actor,source,root)
                c.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",(seq,eid,etype,_canonical(payload),ph,previous,eh,created,actor,source,root)); result.append(self._row(c.execute("SELECT * FROM events WHERE sequence=?",(seq,)).fetchone())); previous=eh
            c.execute("COMMIT"); self._enforce_sidecar_modes(); return result
        except LedgerConflictError:
            c.execute("ROLLBACK")
            for eid,etype,payload,actor,source,root in normalized:
                row=c.execute("SELECT * FROM events WHERE event_id=?",(eid,)).fetchone()
                if row:
                    ph=_hash(payload); ih=self._identity_hash(ph,etype,actor,source,root); old=self._identity_hash(row["payload_hash"],row["event_type"],row["actor"],row["source"],row["root"])
                    if ih != old: self._record_hold(eid,"divergent_duplicate",ph,ih); break
                if c.execute("SELECT 1 FROM holds WHERE event_id=?",(eid,)).fetchone(): break
            raise
        except Exception: c.execute("ROLLBACK"); raise

    def _row(self,row):
        return LedgerEvent(row["sequence"],row["event_id"],row["event_type"],json.loads(row["payload"]),row["payload_hash"],row["previous_hash"],row["event_hash"],row["created_at"],row["actor"],row["source"],row["root"])

    def list_events(self, *, event_type=None):
        q="SELECT * FROM events"; args=()
        if event_type is not None: q += " WHERE event_type=?"; args=(event_type,)
        return [self._row(r) for r in self._conn.execute(q+" ORDER BY sequence",args)]

    def verify(self):
        previous=GENESIS; expected=1
        for r in self._conn.execute("SELECT * FROM events ORDER BY sequence"):
            if r["sequence"]!=expected or r["previous_hash"]!=previous or r["payload_hash"]!=_hash(json.loads(r["payload"])): raise LedgerIntegrityError("sequence or payload chain invalid")
            if self._event_hash(r["sequence"],r["event_id"],r["event_type"],r["payload_hash"],r["previous_hash"],r["created_at"],r["actor"],r["source"],r["root"])!=r["event_hash"]: raise LedgerIntegrityError("hash chain invalid")
            previous=r["event_hash"]; expected+=1
        return True

    def checkpoint_projection(self, name, sequence, payload):
        if not name or sequence < 0 or not isinstance(payload, Mapping) or _contains_forbidden(payload): raise ValueError("invalid projection")
        if sequence > (self._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]): raise LedgerConflictError("projection exceeds ledger")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute("INSERT OR REPLACE INTO projections VALUES(?,?,?,?,?)",(name,sequence,_canonical(payload),_hash(payload),_now())); self._conn.execute("COMMIT")
        except Exception: self._conn.execute("ROLLBACK"); raise

    def load_projection(self,name):
        r=self._conn.execute("SELECT * FROM projections WHERE name=?",(name,)).fetchone(); return None if r is None else {"name":r["name"],"sequence":r["sequence"],"payload":json.loads(r["payload"]),"payload_hash":r["payload_hash"]}

    def rebuild_projection(self, name, reducer=None):
        events = self.list_events()
        payload = reducer(events) if reducer is not None else {"events": [event.payload for event in events]}
        if not isinstance(payload, Mapping): raise ValueError("projection reducer must return a mapping")
        self.checkpoint_projection(name, events[-1].sequence if events else 0, payload)
        return self.load_projection(name)

    def delete_projection(self, name):
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            removed = self._conn.execute("DELETE FROM projections WHERE name=?", (name,)).rowcount > 0
            self._conn.execute("COMMIT"); return removed
        except Exception:
            self._conn.execute("ROLLBACK"); raise

    def verify_projection(self, name):
        projection = self.load_projection(name)
        if projection is None: return False
        if projection["payload_hash"] != _hash(projection["payload"]): raise LedgerIntegrityError("projection hash invalid")
        max_sequence = self._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]
        if projection["sequence"] > max_sequence: raise LedgerIntegrityError("projection sequence invalid")
        return True

    def backup(self, destination):
        dest=Path(destination).expanduser()
        if dest.exists(): raise LedgerConflictError("backup destination must be fresh")
        dest.parent.mkdir(parents=True,exist_ok=True)
        tmp=dest.with_name(f".{dest.name}.staging-{uuid.uuid4().hex}")
        try:
            with sqlite3.connect(tmp) as target: self._conn.backup(target)
            os.chmod(tmp,0o600); self._enforce_sidecar_modes()
            staged = type(self)(db_path=tmp, create=False)
            staged.integrity_check(); source_head = staged._conn.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone(); generation = staged._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]; staged.close()
            receipt={"schema_version":SCHEMA_VERSION,"project_id":self.project_id,"integrity":"ok","sha256":hashlib.sha256(tmp.read_bytes()).hexdigest(),"generation":generation,"source_head":source_head[0] if source_head else GENESIS}
            receipt_path=dest.with_name(dest.name+".receipt.json")
            if receipt_path.exists(): raise LedgerConflictError("backup receipt destination must be fresh")
            os.rename(tmp,dest); receipt_path.write_text(_canonical(receipt)+"\n"); os.chmod(receipt_path,0o600)
            return dest
        finally:
            if tmp.exists(): tmp.unlink()

    @classmethod
    def restore(cls, backup, destination, *, expected_project_id=None):
        """Restore only into a fresh target, validating identity before publish."""
        source, dest = Path(backup).expanduser(), Path(destination).expanduser()
        if not source.is_file() or dest.exists() or expected_project_id is None: raise LedgerConflictError("restore requires fresh target and expected project identity")
        if _mode(source) != 0o600: raise LedgerPermissionError("backup must be 0600")
        parent_existed = dest.parent.exists(); dest.parent.mkdir(parents=True, exist_ok=True)
        if parent_existed and _mode(dest.parent) != 0o700: raise LedgerPermissionError("restore directory must be 0700")
        if not parent_existed: os.chmod(dest.parent, 0o700)
        staged = dest.with_name(f".{dest.name}.restore-{uuid.uuid4().hex}")
        try:
            receipt_path = source.with_name(source.name + ".receipt.json")
            if not receipt_path.is_file(): raise LedgerIntegrityError("backup receipt missing")
            receipt = json.loads(receipt_path.read_text())
            if receipt.get("sha256") != hashlib.sha256(source.read_bytes()).hexdigest() or receipt.get("project_id") != expected_project_id or receipt.get("schema_version") != SCHEMA_VERSION: raise LedgerIntegrityError("backup receipt mismatch")
            shutil.copyfile(source, staged); os.chmod(staged, 0o600)
            restored = cls(db_path=staged, create=False)
            if restored.project_id != expected_project_id or restored.metadata().get("schema_version") != SCHEMA_VERSION:
                restored.close(); raise LedgerIntegrityError("restore identity/schema receipt mismatch")
            restored.integrity_check(); generation = restored._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]; head = restored._conn.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone(); restored.close()
            if generation != receipt.get("generation") or (head[0] if head else GENESIS) != receipt.get("source_head"): raise LedgerIntegrityError("backup generation/head mismatch")
            os.rename(staged, dest)
            return cls(db_path=dest, create=False)
        finally:
            if staged.exists(): staged.unlink()

    @classmethod
    def discover_by_binding(cls, projects_root, binding_type, binding_value):
        root = Path(projects_root).expanduser(); matches = []; holds = []
        if not root.exists(): return matches
        for directory in root.iterdir():
            db = directory / "collaboration.db"
            if not directory.is_dir() or db.is_symlink() or not db.is_file(): continue
            try:
                ledger = cls(db_path=db, create=False)
                found = ledger._conn.execute("SELECT 1 FROM project_bindings WHERE binding_type=? AND binding_value=? AND active=1", (binding_type, binding_value)).fetchone()
                if found: matches.append(ledger.project_id)
                ledger.close()
            except (LedgerError, sqlite3.DatabaseError) as exc:
                holds.append({"path": str(db), "reason": str(exc)})
        if len(matches) > 1: raise LedgerConflictError("binding resolves to multiple projects")
        if holds: raise LedgerConflictError(f"candidate holds require review: {holds}")
        return matches

    def integrity_check_path(self,path):
        with sqlite3.connect(path) as c:
            if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise LedgerIntegrityError("backup integrity failure")

    def integrity_check(self):
        self.integrity_check_path(self.path); self.verify(); return "ok"


__all__=["LocalCollaborationLedger","LedgerEvent","LedgerError","LedgerIntegrityError","LedgerConflictError","LedgerPermissionError"]
