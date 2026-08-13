"""Bounded, disposable GitHub evidence projection.

The cache is deliberately not an authority.  It is a small SQLite projection
whose only producer boundary is an injected, read-only fake/adapter contract.
All public writes validate the complete envelope before opening a writable
connection and re-check both cache and ledger snapshots immediately before
commit.
"""
from __future__ import annotations

import hashlib, json, math, os, re, sqlite3, stat, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from local_collaboration_ledger import LocalCollaborationLedger

VERSION = "GitHubEvidenceCache-v1"
KINDS = {"issue_metadata", "pull_request_metadata", "comment_summary", "project_item_summary"}
STATES = {"fresh_as_of_fetch", "stale", "partial", "unavailable", "privacy_held", "invalidated", "conflict"}
COVERAGE = {"complete", "partial", "unavailable", "privacy_held"}
PRIVACY = {"public_metadata", "repository_internal_redacted", "metadata_only", "privacy_held"}
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output", "secret", "secrets", "token", "tokens", "credential", "credentials", "password", "authorization", "cookie", "body", "raw_body", "comment_body", "full_comment", "history", "full_history", "native_thread", "native_thread_id", "native_history", "absolute_path", "local_path", "user_identity", "exception", "stacktrace"}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HOLDS = {"hold_cache_authority_unready", "hold_cache_binding_mismatch", "hold_cache_schema", "hold_cache_permission", "hold_cache_integrity", "hold_cache_busy", "hold_cache_stale_basis", "hold_cache_divergent_revision", "hold_cache_generation_conflict", "hold_cache_clock_or_freshness", "hold_cache_scope", "hold_cache_privacy", "hold_cache_producer_untrusted", "hold_cache_cleanup_gate"}
DURABILITY = "wal_synchronous_normal"
META_REQUIRED = {"schema_version", "project_id", "repository_id", "repository_locator_digest", "auth_scope_digest", "host_kind", "producer_contract", "producer_version", "generation", "ledger_head", "created_at", "timestamp_provenance", "durability"}
RECEIPT_DATA_KEYS = {
    "refresh": {"generation", "changed", "duplicates", "producer_id", "coverage"},
    "invalidate": {"generation", "count", "reason_digest"},
    "rebuild": {"generation", "count", "coverage"},
}
CLEANUP_DECISION_KEYS = {
    "schema_version", "operation", "decision_id", "decision", "authorized_by",
    "project_id", "repository_id", "repository_locator_digest", "auth_scope_digest",
    "cache_path_digest", "metadata_digest", "reason_digest", "decided_at",
}
OPERATION_OUTCOMES = {
    "read_cache": {"cache_hit", "cache_miss"},
    "project_cache_readout": {"cache_hit", "cache_miss"},
    "initialize_cache": {"cache_initialized"},
    "refresh_cache": {"cache_unavailable", "cache_privacy_held", "cache_duplicate", "cache_partial", "cache_refreshed"},
    "invalidate_cache_entries": {"cache_invalidated"},
    "rebuild_cache": {"cache_rebuilt"},
    "plan_cache_cleanup": {"cache_cleanup_planned"},
    "apply_cache_cleanup": {"cache_cleaned"},
}


class CacheError(RuntimeError):
    pass


class CacheHold(CacheError):
    def __init__(self, classification: str, message: str = "cache operation held"):
        if classification not in HOLDS:
            classification = "hold_cache_schema"
        self.classification = classification
        super().__init__(message)


class CacheIntegrityError(CacheHold):
    pass


def _receipt_data(operation: str, data: Any) -> dict[str, Any]:
    """Validate the intentionally small durable receipt payload.

    Receipts are a projection audit trail, not an escape hatch for arbitrary
    producer output.  Keeping this separate from the outer envelope makes a
    reopened database fail closed if an old or tampered receipt grows fields.
    """
    if operation not in RECEIPT_DATA_KEYS or not isinstance(data, Mapping) or set(data) != RECEIPT_DATA_KEYS[operation]:
        raise CacheHold("hold_cache_schema")
    out = dict(data)
    for key in ("generation", "changed", "duplicates", "count"):
        if key in out and (not isinstance(out[key], int) or isinstance(out[key], bool) or out[key] < 0):
            raise CacheHold("hold_cache_schema")
    if "producer_id" in out and (not isinstance(out["producer_id"], str) or not out["producer_id"] or len(out["producer_id"].encode()) > 256):
        raise CacheHold("hold_cache_schema")
    if "coverage" in out and out["coverage"] not in COVERAGE:
        raise CacheHold("hold_cache_schema")
    if "reason_digest" in out and (not isinstance(out["reason_digest"], str) or not HEX64.fullmatch(out["reason_digest"])):
        raise CacheHold("hold_cache_schema")
    return out


def _walk(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    count = count or [0]
    count[0] += 1
    if depth > 12 or count[0] > 10000:
        raise CacheHold("hold_cache_scope")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN:
                raise CacheHold("hold_cache_privacy")
            # Sentinels are rejected even when hidden in an otherwise innocent
            # key.  This prevents raw content from reaching a durable payload.
            if isinstance(child, str) and any(token in child.lower() for token in FORBIDDEN):
                raise CacheHold("hold_cache_privacy")
            _walk(child, depth + 1, count)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _walk(child, depth + 1, count)
    elif isinstance(value, float) and not math.isfinite(value):
        raise CacheHold("hold_cache_scope")
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise CacheHold("hold_cache_scope")


def _canon(value: Any) -> str:
    _walk(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise CacheHold("hold_cache_scope") from None


def _hash(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _ts(value: Any) -> str:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise CacheHold("hold_cache_clock_or_freshness")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CacheHold("hold_cache_clock_or_freshness") from None
    if parsed.tzinfo is None:
        raise CacheHold("hold_cache_clock_or_freshness")
    return value


def _digest_locator(value: Any) -> str:
    if isinstance(value, str) and HEX64.fullmatch(value):
        return value
    if not isinstance(value, str) or not value or len(value.encode()) > 2048:
        raise CacheHold("hold_cache_binding_mismatch")
    return _hash(value)


def _auth_scope_digest(value: Any) -> str:
    """Accept an already-opaque scope binding, never a credential or header."""
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise CacheHold("hold_cache_scope")
    return value


def _metadata_digest(metadata: Mapping[str, Any]) -> str:
    """Bind disposal to the exact, privacy-safe metadata snapshot."""
    if not isinstance(metadata, Mapping) or set(metadata) != META_REQUIRED:
        raise CacheHold("hold_cache_integrity")
    return _hash(dict(metadata))


def _cleanup_decision(value: Any, *, project_id: str, repository_id: str,
                      repository_locator_digest: str, auth_scope_digest: str,
                      cache_path_digest: str, metadata_digest: str) -> dict[str, Any]:
    """Validate a closed Human/authorized-owner disposal decision.

    This is deliberately an opaque, pre-authorized receipt boundary.  It does
    not accept a free-form owner string and it never persists the decision in
    the disposable cache immediately before deleting it.
    """
    if not isinstance(value, Mapping) or set(value) != CLEANUP_DECISION_KEYS:
        raise CacheHold("hold_cache_cleanup_gate")
    if value.get("schema_version") != VERSION or value.get("operation") != "cache_cleanup_disposal":
        raise CacheHold("hold_cache_cleanup_gate")
    if value.get("decision") != "dispose" or value.get("authorized_by") not in {"human", "authorized_owner"}:
        raise CacheHold("hold_cache_cleanup_gate")
    if not isinstance(value.get("decision_id"), str) or not value["decision_id"] or len(value["decision_id"].encode()) > 128:
        raise CacheHold("hold_cache_cleanup_gate")
    try:
        _ts(value.get("decided_at"))
        expected = {
            "project_id": project_id, "repository_id": repository_id,
            "repository_locator_digest": repository_locator_digest,
            "auth_scope_digest": auth_scope_digest, "cache_path_digest": cache_path_digest,
            "metadata_digest": metadata_digest,
        }
        if any(value[key] != expected[key] for key in expected):
            raise CacheHold("hold_cache_cleanup_gate")
        if not isinstance(value.get("reason_digest"), str) or not HEX64.fullmatch(value["reason_digest"]):
            raise CacheHold("hold_cache_cleanup_gate")
    except (TypeError, KeyError):
        raise CacheHold("hold_cache_cleanup_gate") from None
    return dict(value)


def _result(*, operation: str, outcome: str, **fields: Any) -> dict[str, Any]:
    """Closed outer result shared by all public operation APIs."""
    if operation not in OPERATION_OUTCOMES or outcome not in OPERATION_OUTCOMES[operation]:
        raise CacheHold("hold_cache_schema")
    return {
        "schema_version": VERSION, "operation": operation, "outcome": outcome,
        "authoritative": False, "confirmation_eligible": False, **fields,
    }


def _private(path: Path, mode: int) -> None:
    try:
        if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != mode:
            raise CacheHold("hold_cache_permission")
    except OSError:
        raise CacheHold("hold_cache_permission") from None


def _authority(projects_root: str | Path, project_id: str):
    try:
        pid = str(uuid.UUID(str(project_id)))
    except (ValueError, TypeError, AttributeError):
        raise CacheHold("hold_cache_authority_unready") from None
    root = Path(projects_root).expanduser()
    db = root / pid / "collaboration.db"
    try:
        ledger = LocalCollaborationLedger(db_path=db, create=False)
        if ledger.project_id != pid:
            ledger.close()
            raise CacheHold("hold_cache_binding_mismatch")
        ledger.verify()
        meta = ledger.metadata()
        head_row = ledger._conn.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        generation = int(ledger._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0])
        snap = {"project_id": pid, "generation": generation, "head": head_row[0] if head_row else "0" * 64, "schema_version": meta.get("schema_version")}
        return ledger, snap
    except CacheHold:
        raise
    except Exception:
        try:
            ledger.close()
        except Exception:
            pass
        raise CacheHold("hold_cache_authority_unready") from None


def _cache_path(projects_root: str | Path, project_id: str) -> Path:
    try:
        pid = str(uuid.UUID(str(project_id)))
    except (ValueError, TypeError, AttributeError):
        raise CacheHold("hold_cache_authority_unready") from None
    return Path(projects_root).expanduser() / pid / "github-evidence-cache.db"


def _key(project_id: str, repository_id: str, kind: str, ref: str, selector_digest: str, representation_version: str) -> str:
    if kind not in KINDS or not all(isinstance(x, str) and x for x in (project_id, repository_id, ref, representation_version)) or not isinstance(selector_digest, str) or not HEX64.fullmatch(selector_digest):
        raise CacheHold("hold_cache_scope")
    return _hash([VERSION, project_id, repository_id, kind, ref, selector_digest, representation_version])


def _entry(entry: Any, project_id: str, repository_id: str) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        raise CacheHold("hold_cache_schema")
    allowed = {"evidence_kind", "opaque_object_ref", "selector_digest", "representation_version", "facts", "summary", "anchors", "source_revision", "source_updated_at", "fetched_at", "coverage", "privacy_class", "producer_id", "producer_version", "provenance", "metadata"}
    required = {"evidence_kind", "opaque_object_ref", "selector_digest", "representation_version", "facts", "summary", "anchors", "source_revision", "fetched_at", "coverage", "privacy_class"}
    if set(entry) - allowed or not required.issubset(entry):
        raise CacheHold("hold_cache_schema")
    if entry["evidence_kind"] not in KINDS or not isinstance(entry["opaque_object_ref"], str) or not entry["opaque_object_ref"]:
        raise CacheHold("hold_cache_schema")
    if not isinstance(entry["representation_version"], str) or not entry["representation_version"] or not isinstance(entry["selector_digest"], str) or not HEX64.fullmatch(entry["selector_digest"]):
        raise CacheHold("hold_cache_schema")
    if not isinstance(entry["facts"], Mapping) or not isinstance(entry["anchors"], (list, tuple)) or not isinstance(entry["summary"], str):
        raise CacheHold("hold_cache_schema")
    fact_allowed = {"state", "number", "title", "labels", "disposition", "category", "count", "updated_at"}
    unknown_facts = set(entry["facts"]) - fact_allowed
    if unknown_facts:
        raise CacheHold("hold_cache_privacy" if any(str(k).lower() in FORBIDDEN for k in unknown_facts) else "hold_cache_schema")
    if len(entry["anchors"]) > 16 or not all(isinstance(anchor, str) and anchor and len(anchor) <= 256 for anchor in entry["anchors"]):
        raise CacheHold("hold_cache_schema")
    if "\n" in entry["summary"] or "\r" in entry["summary"]:
        raise CacheHold("hold_cache_schema")
    for fact_key, fact_value in entry["facts"].items():
        if fact_key in {"title"} and (not isinstance(fact_value, str) or len(fact_value) > 256):
            raise CacheHold("hold_cache_schema")
        if fact_key in {"disposition", "category"} and (not isinstance(fact_value, str) or len(fact_value) > 128):
            raise CacheHold("hold_cache_schema")
        if fact_key == "number" and (not isinstance(fact_value, int) or isinstance(fact_value, bool) or fact_value < 1):
            raise CacheHold("hold_cache_schema")
        if fact_key == "count" and (not isinstance(fact_value, int) or isinstance(fact_value, bool) or fact_value < 0):
            raise CacheHold("hold_cache_schema")
    if "state" in entry["facts"] and entry["facts"]["state"] not in {"open", "closed", "merged", "draft", "unknown"}:
        raise CacheHold("hold_cache_schema")
    if "labels" in entry["facts"] and (not isinstance(entry["facts"]["labels"], list) or len(entry["facts"]["labels"]) > 25 or not all(isinstance(x, str) and len(x) <= 128 for x in entry["facts"]["labels"])):
        raise CacheHold("hold_cache_schema")
    if "updated_at" in entry["facts"]: _ts(entry["facts"]["updated_at"])
    metadata = entry.get("metadata")
    if metadata is not None and (not isinstance(metadata, Mapping) or set(metadata) - {"scope", "selector_count"}):
        raise CacheHold("hold_cache_schema")
    if entry.get("provenance") is not None and entry["provenance"] not in {"same_process_reference", "adapter_receipt"}:
        raise CacheHold("hold_cache_schema")
    for key in ("producer_id", "producer_version"):
        if key in entry and (not isinstance(entry[key], str) or not entry[key]): raise CacheHold("hold_cache_schema")
    if len(entry["summary"].encode("utf-8")) > 1024 or entry["privacy_class"] not in PRIVACY or entry["coverage"] not in COVERAGE:
        raise CacheHold("hold_cache_scope" if entry["privacy_class"] in PRIVACY else "hold_cache_schema")
    if not isinstance(entry["source_revision"], str) or not entry["source_revision"] or len(entry["source_revision"].encode()) > 512:
        raise CacheHold("hold_cache_schema")
    _ts(entry["fetched_at"])
    if entry.get("source_updated_at") is not None:
        _ts(entry["source_updated_at"])
    _walk(entry)
    out = dict(entry)
    out["entry_key"] = _key(project_id, repository_id, out["evidence_kind"], out["opaque_object_ref"], out["selector_digest"], out["representation_version"])
    out["payload_hash"] = _hash(out)
    if len(_canon(out).encode("utf-8")) > 16 * 1024:
        raise CacheHold("hold_cache_scope")
    return out


class GitHubEvidenceCache:
    def __init__(self, path: str | Path, *, read_only: bool = False, create: bool = True):
        self.path = Path(path).expanduser()
        self.read_only = read_only
        if read_only:
            _private(self.path, 0o600)
            try:
                # immutable prevents SQLite from creating read-lock sidecars
                # during preflight/read paths.  A reader therefore never
                # performs recovery or changes cache file timestamps.
                self.db = sqlite3.connect(f"file:{self.path}?mode=ro&immutable=1", uri=True, timeout=5)
                self.db.row_factory = sqlite3.Row
                self._configure(read_only=True)
                self._validate()
            except CacheHold:
                raise
            except sqlite3.Error:
                raise CacheHold("hold_cache_integrity") from None
        else:
            if self.path.exists() and self.path.is_symlink():
                raise CacheHold("hold_cache_permission")
            if self.path.exists() and not self.path.is_file():
                raise CacheHold("hold_cache_permission")
            if not create:
                _private(self.path, 0o600)
            else:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                os.chmod(self.path.parent, 0o700)
            try:
                target = self.path if create else f"file:{self.path}?mode=rw"
                self.db = sqlite3.connect(target, uri=not create, timeout=5, isolation_level=None)
                self.db.row_factory = sqlite3.Row
                self._configure(read_only=False)
                if create:
                    self._init()
                self._validate()
                if create:
                    os.chmod(self.path, 0o600)
            except CacheHold:
                try: self.db.close()
                except Exception: pass
                raise
            except sqlite3.OperationalError as exc:
                try: self.db.close()
                except Exception: pass
                cls = "hold_cache_busy" if "locked" in str(exc).lower() or "busy" in str(exc).lower() else "hold_cache_schema"
                raise CacheHold(cls) from None
            except sqlite3.DatabaseError:
                try: self.db.close()
                except Exception: pass
                raise CacheHold("hold_cache_integrity") from None

    def _configure(self, *, read_only: bool) -> None:
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA trusted_schema=OFF")
        self.db.execute("PRAGMA busy_timeout=5000")
        if not read_only:
            mode = self.db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if str(mode).lower() != "wal": raise CacheHold("hold_cache_schema")
            self.db.execute("PRAGMA synchronous=NORMAL")
            if int(self.db.execute("PRAGMA synchronous").fetchone()[0]) != 1: raise CacheHold("hold_cache_schema")
            if int(self.db.execute("PRAGMA wal_autocheckpoint").fetchone()[0]) != 1000: raise CacheHold("hold_cache_schema")

    def _init(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS entries (entry_key TEXT PRIMARY KEY, payload TEXT NOT NULL, payload_hash TEXT NOT NULL, source_revision TEXT NOT NULL, fetched_at TEXT NOT NULL, state TEXT NOT NULL, invalidated INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS receipts (receipt_id TEXT PRIMARY KEY, operation TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT, provenance TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
        """)
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('schema_version',?)", (VERSION,))
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('durability',?)", (DURABILITY,))

    def _validate(self) -> None:
        try:
            meta = self._meta()
            row = self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if row is None or row[0] != VERSION:
                raise CacheHold("hold_cache_schema")
            # A just-created cache has no binding yet; only initialize_cache may
            # turn it into a usable authority-bound projection.
            if set(meta) != {"schema_version", "durability"}:
                if set(meta) != META_REQUIRED or meta.get("durability") != DURABILITY or meta.get("host_kind") != "github":
                    raise CacheHold("hold_cache_schema")
                str(uuid.UUID(meta["project_id"]))
                if not meta["repository_id"] or not HEX64.fullmatch(meta["repository_locator_digest"]) or not HEX64.fullmatch(meta["auth_scope_digest"]) or not meta["producer_contract"] or not meta["producer_version"]:
                    raise CacheHold("hold_cache_schema")
                if not meta["generation"].isdigit() or not HEX64.fullmatch(meta["ledger_head"]) or meta["timestamp_provenance"] not in {"caller_supplied", "caller_evaluated_at", "not_collected"}:
                    raise CacheHold("hold_cache_schema")
                if meta["created_at"]:
                    _ts(meta["created_at"])
            for row in self.db.execute("SELECT entry_key,payload,payload_hash,state FROM entries"):
                payload = json.loads(row[1]); claimed = payload.pop("payload_hash", None)
                entry_key = payload.pop("entry_key", None)
                normalized = _entry(payload, meta["project_id"], meta["repository_id"])
                if row[3] not in STATES or entry_key != row[0] or normalized["entry_key"] != row[0] or claimed != row[2] or normalized["payload_hash"] != row[2]:
                    raise CacheHold("hold_cache_integrity")
            for row in self.db.execute("SELECT receipt_id,operation,payload,created_at,provenance FROM receipts"):
                body = json.loads(row[2])
                if not isinstance(body, Mapping) or set(body) != {"schema_version", "operation", "data", "created_at", "provenance", "durability"} or body["schema_version"] != VERSION or body["operation"] != row[1] or body["created_at"] != row[3] or body["provenance"] != row[4] or body["durability"] != DURABILITY:
                    raise CacheHold("hold_cache_integrity")
                if row[1] not in {"refresh", "invalidate", "rebuild"} or row[4] not in {"caller_supplied", "caller_evaluated_at"} or (row[3] is not None and _ts(row[3]) != row[3]):
                    raise CacheHold("hold_cache_integrity")
                try:
                    _receipt_data(row[1], body["data"])
                except CacheHold:
                    raise CacheHold("hold_cache_integrity") from None
        except CacheHold:
            raise
        except (sqlite3.Error, ValueError, TypeError):
            raise CacheHold("hold_cache_integrity") from None

    def close(self):
        self.db.close()

    def _meta(self):
        return {r["key"]: r["value"] for r in self.db.execute("SELECT key,value FROM metadata")}

    def _setmeta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, str(value)))

    def _counter(self, name, delta=1):
        self.db.execute("INSERT INTO counters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=value+excluded.value", (name, delta))

    def _receipt(self, operation, data, *, created_at=None, provenance="caller_supplied"):
        if created_at is not None: _ts(created_at)
        if not isinstance(provenance, str) or not provenance or provenance in {"wall_clock", "implicit"}: raise CacheHold("hold_cache_clock_or_freshness")
        data = _receipt_data(operation, data)
        payload = _canon({"schema_version": VERSION, "operation": operation, "data": data, "created_at": created_at, "provenance": provenance, "durability": DURABILITY})
        rid = str(uuid.uuid4())
        self.db.execute("INSERT INTO receipts VALUES (?,?,?,?,?)", (rid, operation, payload, created_at, provenance))
        return rid

    def read(self, *, evaluated_at, max_age_seconds, offline=False):
        now = _ts(evaluated_at)
        if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or not 0 <= max_age_seconds <= 604800:
            raise CacheHold("hold_cache_clock_or_freshness")
        at = datetime.fromisoformat(now.replace("Z", "+00:00")); rows = []
        try:
            source = self.db.execute("SELECT payload,state,invalidated FROM entries ORDER BY entry_key").fetchall()
            for row in source:
                payload = json.loads(row["payload"])
                fetched = datetime.fromisoformat(payload["fetched_at"].replace("Z", "+00:00"))
                age = int((at - fetched).total_seconds())
                if age < 0: raise CacheHold("hold_cache_clock_or_freshness")
                if row["invalidated"]: state = "invalidated"
                elif payload["coverage"] == "partial": state = "partial"
                elif payload["privacy_class"] == "privacy_held": state = "privacy_held"
                elif payload["coverage"] == "unavailable": state = "unavailable"
                else: state = "fresh_as_of_fetch" if age <= max_age_seconds else "stale"
                payload.update({"freshness": state, "as_of": now, "age_seconds": age, "offline": bool(offline), "authoritative": False, "confirmation_eligible": False, "next_action": "refresh" if state in {"stale", "unavailable", "invalidated"} else "observe_unverified"})
                rows.append(payload)
            return rows
        except CacheHold:
            raise
        except (ValueError, KeyError, sqlite3.Error):
            raise CacheHold("hold_cache_integrity") from None


def _binding(meta: Mapping[str, Any], pid: str, repository_id: str, locator: str, auth_scope_digest: str | None = None) -> None:
    if meta.get("project_id") != pid or meta.get("repository_id") != str(repository_id) or meta.get("repository_locator_digest") != locator:
        raise CacheHold("hold_cache_binding_mismatch")
    if auth_scope_digest is not None and meta.get("auth_scope_digest") != auth_scope_digest:
        raise CacheHold("hold_cache_scope")


def _ledger_recheck(projects_root, project_id, snapshot):
    ledger, current = _authority(projects_root, project_id)
    ledger.close()
    if current != snapshot:
        raise CacheHold("hold_cache_stale_basis")


def _open_existing(path: Path) -> GitHubEvidenceCache:
    if not path.is_file() or path.is_symlink(): raise CacheHold("hold_cache_authority_unready")
    return GitHubEvidenceCache(path, create=False)


def _read_preflight(path: Path, lm: Mapping[str, Any], repository_id: str, locator: str, auth_scope_digest: str) -> tuple[dict[str, str], int]:
    """Validate all durable bindings without changing DB, WAL, SHM, or mtime."""
    if not path.is_file() or path.is_symlink():
        raise CacheHold("hold_cache_authority_unready")
    cache = GitHubEvidenceCache(path, read_only=True)
    try:
        meta = cache._meta()
        _binding(meta, lm["project_id"], repository_id, locator, auth_scope_digest)
        return meta, int(meta.get("generation", "0"))
    finally:
        cache.close()


def initialize_cache(*, projects_root, project_id, repository_id, repository_locator_digest, auth_scope_digest, producer_contract="unknown", producer_version="unknown", receipt_at=None):
    # Complete caller validation is intentionally before `GitHubEvidenceCache`
    # construction: a malformed binding must never create an orphan DB/WAL/SHM.
    repository_id, locator, scope = _required_binding(
        repository_id, repository_locator_digest, auth_scope_digest)
    if not isinstance(producer_contract, str) or not producer_contract or not isinstance(producer_version, str) or not producer_version:
        raise CacheHold("hold_cache_schema")
    if receipt_at is not None:
        _ts(receipt_at)
    ledger, lm = _authority(projects_root, project_id); path = _cache_path(projects_root, project_id)
    try:
        cache = GitHubEvidenceCache(path)
        try:
            old = cache._meta(); fresh_projection = set(old) == {"schema_version", "durability"}
            if not fresh_projection and old.get("auth_scope_digest") != scope:
                raise CacheHold("hold_cache_scope")
            _binding({**old, "project_id": lm["project_id"], "repository_id": repository_id, "repository_locator_digest": locator, "auth_scope_digest": scope}, lm["project_id"], repository_id, locator, scope)
            values = {"project_id": lm["project_id"], "repository_id": str(repository_id), "repository_locator_digest": locator, "auth_scope_digest": scope, "host_kind": "github", "producer_contract": str(producer_contract), "producer_version": str(producer_version), "generation": old.get("generation", "0"), "ledger_head": lm["head"], "created_at": receipt_at or old.get("created_at", ""), "timestamp_provenance": "caller_supplied" if receipt_at else "not_collected"}
            for key, value in values.items():
                if key in old and old[key] != str(value) and key not in {"ledger_head", "created_at", "timestamp_provenance"}: raise CacheHold("hold_cache_binding_mismatch")
                cache._setmeta(key, value)
            # A cache cannot durably observe a miss until it exists.  The
            # successful first initialization is that single durable miss.
            if fresh_projection:
                cache._counter("cache_miss")
            cache.db.commit()
            return _result(operation="initialize_cache", outcome="cache_initialized", project_id=lm["project_id"], cache_path_digest=_hash(str(path)), generation=int(values["generation"]))
        finally: cache.close()
    finally: ledger.close()


def _read_envelope(*, outcome, entries, evaluated_at, offline, metadata, counters, coverage, freshness, age_seconds, next_action):
    return _result(operation="read_cache", outcome=outcome, entries=entries, as_of=evaluated_at,
        age_seconds=age_seconds, coverage=coverage, freshness=freshness,
        offline=bool(offline), next_action=next_action, metadata=metadata, counters=counters)


def _required_binding(repository_id: Any, repository_locator_digest: Any,
                      auth_scope_digest: Any) -> tuple[str, str, str]:
    """Require all public cache operations to state the opaque authority binding."""
    if not isinstance(repository_id, str) or not repository_id:
        raise CacheHold("hold_cache_binding_mismatch")
    return repository_id, _digest_locator(repository_locator_digest), _auth_scope_digest(auth_scope_digest)


def read_cache(*, projects_root, project_id, evaluated_at, max_age_seconds, offline=False, repository_id=None, repository_locator_digest=None, auth_scope_digest=None):
    # Validate caller freshness policy before even deciding whether this is a miss.
    _ts(evaluated_at)
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or not 0 <= max_age_seconds <= 604800:
        raise CacheHold("hold_cache_clock_or_freshness")
    repository_id, repository_locator_digest, auth_scope_digest = _required_binding(
        repository_id, repository_locator_digest, auth_scope_digest)
    ledger, lm = _authority(projects_root, project_id); path = _cache_path(projects_root, project_id); cache = None
    try:
        if not path.is_file():
            return _read_envelope(outcome="cache_miss", entries=[], evaluated_at=evaluated_at, offline=offline, metadata=None, counters={"cache_miss": 1}, coverage="unavailable", freshness="unavailable", age_seconds=None, next_action="initialize_cache")
        cache = GitHubEvidenceCache(path, read_only=True); meta = cache._meta()
        try:
            _binding(meta, lm["project_id"], repository_id, repository_locator_digest, auth_scope_digest)
            entries = cache.read(evaluated_at=evaluated_at, max_age_seconds=max_age_seconds, offline=offline)
            freshness = "unavailable" if not entries else ("stale" if any(e["freshness"] == "stale" for e in entries) else entries[0]["freshness"])
            coverage = "unavailable" if not entries else ("partial" if any(e["coverage"] == "partial" for e in entries) else entries[0]["coverage"])
            ages = [e["age_seconds"] for e in entries]
            next_action = "refresh" if freshness in {"stale", "unavailable", "invalidated"} else "observe_unverified"
            return _read_envelope(outcome="cache_hit", entries=entries, evaluated_at=evaluated_at, offline=offline, metadata=meta, counters={r["name"]: r["value"] for r in cache.db.execute("SELECT * FROM counters")}, coverage=coverage, freshness=freshness, age_seconds=max(ages) if ages else None, next_action=next_action)
        finally: cache.close()
    finally: ledger.close()


def _producer_result(result: Any, project_id: str, repository_id: str, selectors: list[Any], auth_scope_digest: str) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    if not isinstance(result, Mapping) or result.get("trust_domain") != "same_process_reference" or result.get("production_eligibility") is not False:
        raise CacheHold("hold_cache_producer_untrusted")
    allowed = {"trust_domain", "production_eligibility", "project_id", "repository_id", "auth_scope_digest", "producer_id", "producer_version", "coverage", "entries", "source_revision", "fetched_at"}
    if set(result) - allowed:
        raise CacheHold("hold_cache_schema")
    required = {"trust_domain", "production_eligibility", "project_id", "repository_id", "auth_scope_digest", "producer_id", "producer_version", "coverage", "entries"}
    if not required.issubset(result) or result["coverage"] not in COVERAGE:
        raise CacheHold("hold_cache_schema")
    for key in ("producer_id", "producer_version"):
        if not isinstance(result[key], str) or not result[key]: raise CacheHold("hold_cache_schema")
    if result.get("fetched_at") is not None: _ts(result["fetched_at"])
    if result["project_id"] != project_id or result["repository_id"] != repository_id:
        raise CacheHold("hold_cache_binding_mismatch")
    if _auth_scope_digest(result["auth_scope_digest"]) != auth_scope_digest:
        raise CacheHold("hold_cache_scope")
    if not isinstance(result.get("entries"), list): raise CacheHold("hold_cache_schema")
    entries = [_entry(e, project_id, repository_id) for e in result["entries"]]
    if len(entries) > 25 or sum(len(_canon(e).encode()) for e in entries) > 256 * 1024: raise CacheHold("hold_cache_scope")
    coverage = result["coverage"]
    if coverage in {"unavailable", "privacy_held"} and entries:
        raise CacheHold("hold_cache_schema")
    if coverage in {"complete", "partial"} and not entries:
        raise CacheHold("hold_cache_schema")
    if any(entry["coverage"] != coverage for entry in entries):
        raise CacheHold("hold_cache_schema")
    return entries, result


def refresh_cache(*, projects_root, project_id, repository_id, repository_locator_digest, auth_scope_digest, selectors, evaluated_at, max_age_seconds, producer, reason="targeted"):
    if not isinstance(selectors, Sequence) or isinstance(selectors, (str, bytes)) or not 1 <= len(selectors) <= 25: raise CacheHold("hold_cache_scope")
    _ts(evaluated_at)
    _walk(list(selectors))
    if len(_canon(list(selectors)).encode("utf-8")) > 16 * 1024: raise CacheHold("hold_cache_scope")
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or not 0 <= max_age_seconds <= 604800: raise CacheHold("hold_cache_clock_or_freshness")
    scope = _auth_scope_digest(auth_scope_digest)
    ledger, lm = _authority(projects_root, project_id); path = _cache_path(projects_root, project_id); cache = None
    try:
        locator = _digest_locator(repository_locator_digest)
        # This is intentionally a real read-only preflight.  Bad producer data
        # therefore cannot create WAL/SHM or touch the cache mtime.
        meta, before = _read_preflight(path, lm, repository_id, locator, scope)
        try:
            result = producer.fetch_evidence({"project_id": lm["project_id"], "repository_id": str(repository_id), "auth_scope_digest": scope}, list(selectors), {"trust_domain": "same_process_reference", "production_eligibility": False, "auth_scope_digest": scope})
        except CacheHold:
            raise
        except Exception:
            raise CacheHold("hold_cache_producer_untrusted") from None
        entries, result = _producer_result(result, lm["project_id"], str(repository_id), list(selectors), scope)
        if result["producer_id"] != meta["producer_contract"] or result["producer_version"] != meta["producer_version"]:
            raise CacheHold("hold_cache_producer_untrusted")
        evaluated_dt = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
        for entry in entries:
            if datetime.fromisoformat(entry["fetched_at"].replace("Z", "+00:00")) > evaluated_dt:
                raise CacheHold("hold_cache_clock_or_freshness")
        _ledger_recheck(projects_root, project_id, lm)
        # Reopen only after all producer data has passed validation. `mode=rw`
        # refuses missing paths and never recreates an authority projection.
        cache = _open_existing(path)
        cache.db.execute("BEGIN IMMEDIATE")
        current = cache._meta();
        _binding(current, lm["project_id"], repository_id, locator, scope)
        if int(current.get("generation", "0")) != before: raise CacheHold("hold_cache_generation_conflict")
        _ledger_recheck(projects_root, project_id, lm)
        changed = duplicates = preserved_complete = 0
        producer_coverage = result["coverage"]
        if producer_coverage in {"unavailable", "privacy_held"}:
            cache._counter("cache_hit"); cache._counter("refresh_requests"); cache._counter("producer_invocations")
            rid = cache._receipt("refresh", {"generation": before, "changed": 0, "duplicates": 0, "producer_id": result["producer_id"], "coverage": producer_coverage}, created_at=evaluated_at, provenance="caller_evaluated_at")
            cache.db.execute("COMMIT")
            return _result(operation="refresh_cache", outcome="cache_unavailable" if producer_coverage == "unavailable" else "cache_privacy_held", generation=before, changed_count=0, duplicate_count=0, receipt_id=rid)
        for entry in entries:
            old = cache.db.execute("SELECT payload_hash,source_revision,payload FROM entries WHERE entry_key=?", (entry["entry_key"],)).fetchone()
            if old and old["source_revision"] == entry["source_revision"]:
                if old["payload_hash"] != entry["payload_hash"]: raise CacheHold("hold_cache_divergent_revision")
                duplicates += 1; continue
            if old:
                old_payload = json.loads(old["payload"])
                # A partial observation is not evidence that a complete record
                # disappeared. Keep the complete projection until a complete
                # replacement arrives.
                if entry["coverage"] == "partial" and old_payload.get("coverage") == "complete":
                    preserved_complete += 1; continue
            cache.db.execute("INSERT OR REPLACE INTO entries VALUES (?,?,?,?,?,?,0)", (entry["entry_key"], _canon(entry), entry["payload_hash"], entry["source_revision"], entry["fetched_at"], "partial" if entry["coverage"] == "partial" else "fresh_as_of_fetch")); changed += 1
        if not changed:
            # A duplicate proves the producer was invoked, but does not advance
            # generation or change entries.  Counters are the sole durable
            # observation of this request.
            cache._counter("cache_hit"); cache._counter("refresh_requests"); cache._counter("producer_invocations")
            cache.db.execute("COMMIT")
            return _result(operation="refresh_cache", outcome="cache_partial" if preserved_complete else "cache_duplicate", generation=before, changed_count=0, duplicate_count=duplicates, receipt_id=None)
        newgen = before + changed; cache._setmeta("generation", newgen); cache._setmeta("ledger_head", lm["head"])
        cache._counter("cache_hit"); cache._counter("refresh_requests"); cache._counter("producer_invocations")
        rid = cache._receipt("refresh", {"generation": newgen, "changed": changed, "duplicates": duplicates, "producer_id": result["producer_id"], "coverage": producer_coverage}, created_at=evaluated_at, provenance="caller_evaluated_at")
        cache.db.execute("COMMIT")
        return _result(operation="refresh_cache", outcome="cache_duplicate" if not changed else ("cache_partial" if any(e["coverage"] != "complete" for e in entries) else "cache_refreshed"), generation=newgen, changed_count=changed, duplicate_count=duplicates, receipt_id=rid)
    except CacheHold:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise
    except sqlite3.OperationalError as exc:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise CacheHold("hold_cache_busy" if "locked" in str(exc).lower() or "busy" in str(exc).lower() else "hold_cache_schema") from None
    except sqlite3.DatabaseError:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise CacheHold("hold_cache_integrity") from None
    finally:
        try:
            if cache is not None: cache.close()
        except Exception: pass
        ledger.close()


def invalidate_cache_entries(*, projects_root, project_id, entry_keys, reason, evaluated_at, repository_id=None, repository_locator_digest=None, auth_scope_digest=None):
    _ts(evaluated_at)
    if not isinstance(entry_keys, Sequence) or isinstance(entry_keys, (str, bytes)) or len(entry_keys) > 25: raise CacheHold("hold_cache_scope")
    if not isinstance(reason, str) or not reason or len(reason.encode("utf-8")) > 1024:
        raise CacheHold("hold_cache_scope")
    keys = list(entry_keys)
    if not all(isinstance(key, str) and HEX64.fullmatch(key) for key in keys):
        raise CacheHold("hold_cache_schema")
    repository_id, locator, auth_scope_digest = _required_binding(
        repository_id, repository_locator_digest, auth_scope_digest)
    ledger, lm = _authority(projects_root, project_id); path = _cache_path(projects_root, project_id); cache = None
    try:
        # Binding is deliberately proven through immutable read-only mode
        # before opening `mode=rw`; a wrong caller cannot create WAL/SHM or
        # alter mtime merely by attempting an invalidation.
        _, before = _read_preflight(path, lm, repository_id, locator, auth_scope_digest)
        _ledger_recheck(projects_root, project_id, lm)
        cache = _open_existing(path)
        cache.db.execute("BEGIN IMMEDIATE")
        current = cache._meta()
        _binding(current, lm["project_id"], repository_id, locator, auth_scope_digest)
        if int(current.get("generation", "0")) != before: raise CacheHold("hold_cache_generation_conflict")
        _ledger_recheck(projects_root, project_id, lm)
        for key in keys:
            cache.db.execute("UPDATE entries SET invalidated=1,state='invalidated' WHERE entry_key=?", (key,))
        rid = cache._receipt("invalidate", {"count": len(keys), "reason_digest": _hash(reason), "generation": before}, created_at=evaluated_at, provenance="caller_evaluated_at"); cache.db.execute("COMMIT")
        return _result(operation="invalidate_cache_entries", outcome="cache_invalidated", count=len(keys), receipt_id=rid, generation=before)
    except CacheHold:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise
    except sqlite3.OperationalError as exc:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise CacheHold("hold_cache_busy" if "locked" in str(exc).lower() or "busy" in str(exc).lower() else "hold_cache_schema") from None
    except sqlite3.DatabaseError:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise CacheHold("hold_cache_integrity") from None
    finally:
        try:
            if cache is not None: cache.close()
        except Exception: pass
        ledger.close()


def rebuild_cache(*, projects_root, project_id, repository_id, repository_locator_digest, auth_scope_digest, entries, evaluated_at, coverage="complete"):
    _ts(evaluated_at)
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)) or len(entries) > 25: raise CacheHold("hold_cache_scope")
    if coverage not in COVERAGE: raise CacheHold("hold_cache_schema")
    ledger, lm = _authority(projects_root, project_id); path = _cache_path(projects_root, project_id); cache = None
    try:
        normalized = [_entry(e, lm["project_id"], str(repository_id)) for e in entries]
        if len(normalized) > 25 or sum(len(_canon(e).encode()) for e in normalized) > 256 * 1024: raise CacheHold("hold_cache_scope")
        if len({entry["entry_key"] for entry in normalized}) != len(normalized): raise CacheHold("hold_cache_divergent_revision")
        if any(entry["coverage"] != coverage for entry in normalized): raise CacheHold("hold_cache_schema")
        evaluated_dt = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
        if any(datetime.fromisoformat(entry["fetched_at"].replace("Z", "+00:00")) > evaluated_dt for entry in normalized):
            raise CacheHold("hold_cache_clock_or_freshness")
        locator = _digest_locator(repository_locator_digest); scope = _auth_scope_digest(auth_scope_digest)
        # Validate the existing projection in URI read-only mode before the
        # rebuild's already-normalized input can reach a writable connection.
        meta, before = _read_preflight(path, lm, repository_id, locator, scope)
        cache = _open_existing(path); meta = cache._meta(); _binding(meta, lm["project_id"], repository_id, locator, scope)
        before = int(meta.get("generation", "0")); _ledger_recheck(projects_root, project_id, lm); cache.db.execute("BEGIN IMMEDIATE")
        if int(cache._meta().get("generation", "0")) != before: raise CacheHold("hold_cache_generation_conflict")
        cache.db.execute("DELETE FROM entries")
        for entry in normalized: cache.db.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,0)", (entry["entry_key"], _canon(entry), entry["payload_hash"], entry["source_revision"], entry["fetched_at"], "partial" if entry["coverage"] == "partial" else "fresh_as_of_fetch"))
        generation = before + 1; cache._setmeta("generation", generation); cache._setmeta("ledger_head", lm["head"]); rid = cache._receipt("rebuild", {"generation": generation, "count": len(normalized), "coverage": coverage}, created_at=evaluated_at, provenance="caller_evaluated_at"); cache.db.execute("COMMIT")
        return _result(operation="rebuild_cache", outcome="cache_rebuilt", generation=generation, receipt_id=rid)
    except CacheHold:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise
    except sqlite3.OperationalError as exc:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise CacheHold("hold_cache_busy" if "locked" in str(exc).lower() or "busy" in str(exc).lower() else "hold_cache_schema") from None
    except sqlite3.DatabaseError:
        try:
            if cache is not None and cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise CacheHold("hold_cache_integrity") from None
    finally:
        try:
            if cache is not None: cache.close()
        except Exception: pass
        ledger.close()


def project_cache_readout(*, projects_root, project_id, repository_id, repository_locator_digest,
                          auth_scope_digest, evaluated_at, max_age_seconds, offline=False):
    """Binding-checked projection readout, never a second unbound cache view."""
    readout = read_cache(
        projects_root=projects_root, project_id=project_id, repository_id=repository_id,
        repository_locator_digest=repository_locator_digest, auth_scope_digest=auth_scope_digest,
        evaluated_at=evaluated_at, max_age_seconds=max_age_seconds, offline=offline,
    )
    readout["operation"] = "project_cache_readout"
    return readout


def _cleanup_binding(*, projects_root, project_id, repository_id, repository_locator_digest,
                     auth_scope_digest):
    locator = _digest_locator(repository_locator_digest)
    scope = _auth_scope_digest(auth_scope_digest)
    ledger, lm = _authority(projects_root, project_id)
    path = _cache_path(projects_root, project_id)
    cache = None
    try:
        if not path.is_file():
            raise CacheHold("hold_cache_cleanup_gate")
        cache = GitHubEvidenceCache(path, read_only=True)
        metadata = cache._meta()
        _binding(metadata, lm["project_id"], repository_id, locator, scope)
        return ledger, lm, path, locator, scope, metadata
    except Exception:
        if cache is not None:
            cache.close()
        ledger.close()
        raise
    finally:
        if cache is not None:
            cache.close()


def plan_cache_cleanup(*, projects_root, project_id, repository_id, repository_locator_digest,
                       auth_scope_digest, disposal_decision):
    ledger, lm, path, locator, scope, metadata = _cleanup_binding(
        projects_root=projects_root, project_id=project_id, repository_id=repository_id,
        repository_locator_digest=repository_locator_digest, auth_scope_digest=auth_scope_digest,
    )
    try:
        path_digest = _hash(str(path)); metadata_digest = _metadata_digest(metadata)
        decision = _cleanup_decision(
            disposal_decision, project_id=lm["project_id"], repository_id=str(repository_id),
            repository_locator_digest=locator, auth_scope_digest=scope, cache_path_digest=path_digest,
            metadata_digest=metadata_digest,
        )
        return _result(operation="plan_cache_cleanup", outcome="cache_cleanup_planned", exists=True,
            project_id=lm["project_id"], repository_id=str(repository_id),
            repository_locator_digest=locator, auth_scope_digest=scope, cache_path_digest=path_digest,
            metadata_digest=metadata_digest, decision_id=decision["decision_id"],
            decision_digest=_hash(decision))
    finally:
        ledger.close()


def apply_cache_cleanup(*, projects_root, project_id, repository_id, repository_locator_digest,
                        auth_scope_digest, cache_path_digest, metadata_digest, disposal_decision):
    """Delete only the exact, disposable projection after a closed gate check."""
    ledger, lm, path, locator, scope, metadata = _cleanup_binding(
        projects_root=projects_root, project_id=project_id, repository_id=repository_id,
        repository_locator_digest=repository_locator_digest, auth_scope_digest=auth_scope_digest,
    )
    try:
        expected_path = _hash(str(path)); expected_metadata = _metadata_digest(metadata)
        if cache_path_digest != expected_path or metadata_digest != expected_metadata:
            raise CacheHold("hold_cache_cleanup_gate")
        decision = _cleanup_decision(
            disposal_decision, project_id=lm["project_id"], repository_id=str(repository_id),
            repository_locator_digest=locator, auth_scope_digest=scope, cache_path_digest=expected_path,
            metadata_digest=expected_metadata,
        )
        for suffix in ("", "-wal", "-shm"):
            target = Path(str(path) + suffix)
            if target.exists():
                if target.is_symlink() or (target.is_file() and stat.S_IMODE(target.stat().st_mode) != 0o600):
                    raise CacheHold("hold_cache_permission")
                target.unlink()
        return _result(operation="apply_cache_cleanup", outcome="cache_cleaned",
            project_id=lm["project_id"], repository_id=str(repository_id),
            repository_locator_digest=locator, auth_scope_digest=scope,
            cache_path_digest=expected_path, metadata_digest=expected_metadata,
            decision_id=decision["decision_id"], decision_digest=_hash(decision))
    finally:
        ledger.close()


__all__ = ["GitHubEvidenceCache", "CacheError", "CacheHold", "CacheIntegrityError", "initialize_cache", "read_cache", "refresh_cache", "invalidate_cache_entries", "rebuild_cache", "project_cache_readout", "plan_cache_cleanup", "apply_cache_cleanup"]
