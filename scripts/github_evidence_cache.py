"""Disposable, rebuildable GitHub evidence projection.

This module deliberately has no GitHub client.  A caller supplies one bounded,
read-only producer for an explicit refresh; the SQLite file is never an
authority and is never written to the collaboration ledger.
"""
from __future__ import annotations

import hashlib, json, math, os, re, shutil, sqlite3, stat, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from local_collaboration_ledger import LocalCollaborationLedger, LedgerError

VERSION = "GitHubEvidenceCache-v1"
SCHEMA_VERSION = VERSION
KINDS = {"issue_metadata", "pull_request_metadata", "comment_summary", "project_item_summary"}
STATES = {"fresh_as_of_fetch", "stale", "partial", "unavailable", "privacy_held", "invalidated", "conflict"}
PRIVACY = {"public_metadata", "repository_internal_redacted", "metadata_only", "privacy_held"}
FORBIDDEN = {"prompt", "transcript", "raw_transcript", "tool_output", "raw_tool_output", "secret", "token", "credential", "password", "authorization", "cookie", "body", "raw_body", "comment_body", "history", "native_thread", "native_history", "absolute_path", "exception"}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HOLDS = {"hold_cache_authority_unready", "hold_cache_binding_mismatch", "hold_cache_schema", "hold_cache_permission", "hold_cache_integrity", "hold_cache_busy", "hold_cache_stale_basis", "hold_cache_divergent_revision", "hold_cache_generation_conflict", "hold_cache_clock_or_freshness", "hold_cache_scope", "hold_cache_privacy", "hold_cache_producer_untrusted", "hold_cache_cleanup_gate"}

class CacheError(RuntimeError): pass
class CacheHold(CacheError):
    def __init__(self, classification: str, message: str = "cache operation held"):
        self.classification = classification
        super().__init__(message)

class CacheIntegrityError(CacheHold): pass

def _walk(v: Any, depth=0, count=None):
    count = count or [0]; count[0] += 1
    if depth > 12 or count[0] > 10000: raise CacheHold("hold_cache_scope")
    if isinstance(v, Mapping):
        for k, x in v.items():
            if not isinstance(k, str) or k.lower() in FORBIDDEN: raise CacheHold("hold_cache_privacy")
            _walk(x, depth + 1, count)
    elif isinstance(v, (list, tuple)):
        for x in v: _walk(x, depth + 1, count)
    elif isinstance(v, float) and not math.isfinite(v): raise CacheHold("hold_cache_scope")
    elif v is not None and not isinstance(v, (str, int, bool)): raise CacheHold("hold_cache_scope")

def _canon(v):
    _walk(v); return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
def _hash(v): return hashlib.sha256(_canon(v).encode()).hexdigest()
def _ts(v):
    if not isinstance(v, str) or not RFC3339.fullmatch(v): raise CacheHold("hold_cache_clock_or_freshness")
    try: datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError: raise CacheHold("hold_cache_clock_or_freshness")
    return v
def _digest_locator(v):
    if isinstance(v, str) and HEX64.fullmatch(v): return v
    if not isinstance(v, str) or not v or len(v.encode()) > 2048: raise CacheHold("hold_cache_binding_mismatch")
    return _hash(v)
def _private(p, mode):
    if not p.is_file() or p.is_symlink() or stat.S_IMODE(p.stat().st_mode) != mode: raise CacheHold("hold_cache_permission")

def _authority(projects_root, project_id):
    try: pid = str(uuid.UUID(str(project_id)))
    except (ValueError, TypeError, AttributeError): raise CacheHold("hold_cache_authority_unready")
    root = Path(projects_root).expanduser(); db = root / pid / "collaboration.db"
    try: _private(db, 0o600)
    except CacheHold: raise CacheHold("hold_cache_authority_unready")
    try:
        ledger = LocalCollaborationLedger(db_path=db, create=False)
        if ledger.project_id != pid: raise CacheHold("hold_cache_binding_mismatch")
        ledger.verify(); meta = ledger.metadata(); head = ledger._conn.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone(); generation = ledger._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]
        return ledger, {"project_id": pid, "generation": generation, "head": head[0] if head else "0" * 64, "schema_version": meta.get("schema_version")}
    except CacheHold: raise
    except Exception: raise CacheHold("hold_cache_authority_unready")

def _cache_path(projects_root, project_id): return Path(projects_root).expanduser() / str(uuid.UUID(str(project_id))) / "github-evidence-cache.db"

def _key(project_id, repository_id, kind, ref, selector_digest, representation_version):
    if kind not in KINDS or not isinstance(repository_id, str) or not repository_id or not isinstance(ref, str) or not ref or not isinstance(representation_version, str) or not representation_version: raise CacheHold("hold_cache_scope")
    return _hash([VERSION, project_id, repository_id, kind, ref, selector_digest, representation_version])

def _entry(e, pid, repository_id):
    if not isinstance(e, Mapping): raise CacheHold("hold_cache_schema")
    required = {"evidence_kind", "opaque_object_ref", "selector_digest", "representation_version", "facts", "summary", "anchors", "source_revision", "fetched_at", "coverage", "privacy_class"}
    if set(e) - required or not required.issubset(e): raise CacheHold("hold_cache_schema")
    if e["evidence_kind"] not in KINDS or not isinstance(e["opaque_object_ref"], str) or not isinstance(e["representation_version"], str): raise CacheHold("hold_cache_schema")
    if e["privacy_class"] not in PRIVACY: raise CacheHold("hold_cache_privacy")
    _walk(e)
    if not isinstance(e["summary"], str) or len(e["summary"].encode()) > 1024: raise CacheHold("hold_cache_scope")
    if not isinstance(e["selector_digest"], str) or not HEX64.fullmatch(e["selector_digest"]): raise CacheHold("hold_cache_schema")
    _ts(e["fetched_at"])
    if not isinstance(e["coverage"], str) or e["coverage"] not in {"complete", "partial", "unavailable", "privacy_held"}: raise CacheHold("hold_cache_schema")
    payload = dict(e)
    payload["entry_key"] = _key(pid, repository_id, e["evidence_kind"], e["opaque_object_ref"], e["selector_digest"], e["representation_version"])
    if len(_canon(payload).encode()) > 16 * 1024: raise CacheHold("hold_cache_scope")
    payload["payload_hash"] = _hash(payload)
    return payload

@dataclass
class Readout:
    metadata: Mapping[str, Any]
    entries: list[Mapping[str, Any]]
    counters: Mapping[str, int]

class GitHubEvidenceCache:
    def __init__(self, path: str | Path, *, read_only=False):
        self.path = Path(path).expanduser(); self.read_only = read_only
        if read_only:
            _private(self.path, 0o600)
            # ``mode=ro`` is non-mutating while still allowing SQLite to read
            # a committed WAL snapshot; immutable mode would hide a live WAL.
            uri = f"file:{self.path}?mode=ro"
            self.db = sqlite3.connect(uri, uri=True, timeout=5)
        else:
            if self.path.exists() and self.path.is_symlink(): raise CacheHold("hold_cache_permission")
            self.path.parent.mkdir(parents=True, exist_ok=True); os.chmod(self.path.parent, 0o700)
            self.db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self._configure()
        if not read_only: self._init()
        self._validate()
    def _configure(self):
        try:
            self.db.execute("PRAGMA foreign_keys=ON"); self.db.execute("PRAGMA trusted_schema=OFF"); self.db.execute("PRAGMA busy_timeout=5000")
            if not self.read_only: self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA synchronous=NORMAL"); self.db.execute("PRAGMA wal_autocheckpoint=1000")
        except sqlite3.Error: raise CacheHold("hold_cache_schema")
    def _init(self):
        self.db.executescript("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS entries (entry_key TEXT PRIMARY KEY, payload TEXT NOT NULL, payload_hash TEXT NOT NULL, source_revision TEXT, fetched_at TEXT NOT NULL, state TEXT NOT NULL, invalidated INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS receipts (receipt_id TEXT PRIMARY KEY, operation TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL)")
        for k,v in {"schema_version":VERSION}.items(): self.db.execute("INSERT OR IGNORE INTO metadata VALUES (?,?)", (k,v))
        os.chmod(self.path, 0o600)
    def _validate(self):
        try:
            if self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] != VERSION: raise CacheHold("hold_cache_schema")
        except (sqlite3.Error, TypeError, IndexError): raise CacheHold("hold_cache_schema")
    def close(self): self.db.close()
    def _meta(self): return {r["key"]: r["value"] for r in self.db.execute("SELECT key,value FROM metadata")}
    def _setmeta(self, k,v): self.db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (k,str(v)))
    def _counter(self, n, delta=1): self.db.execute("INSERT INTO counters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=value+excluded.value", (n,delta))
    def _receipt(self, op, data):
        rid = str(uuid.uuid4()); self.db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (rid,op,_canon(data),datetime.now(timezone.utc).isoformat().replace("+00:00","Z"))); return rid
    def read(self, *, evaluated_at, max_age_seconds, offline=False):
        now = _ts(evaluated_at)
        if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds,bool) or not 0 <= max_age_seconds <= 604800: raise CacheHold("hold_cache_clock_or_freshness")
        rows=[]
        t = datetime.fromisoformat(now.replace("Z","+00:00"))
        for r in self.db.execute("SELECT payload,state,invalidated FROM entries ORDER BY entry_key"):
            p=json.loads(r["payload"]); fetched=datetime.fromisoformat(p["fetched_at"].replace("Z","+00:00")); age=int((t-fetched).total_seconds())
            if age < 0: state="invalidated" if r["invalidated"] else "conflict"
            elif r["invalidated"]: state="invalidated"
            elif p["coverage"] == "partial": state="partial"
            elif p["privacy_class"] == "privacy_held": state="privacy_held"
            elif p["coverage"] == "unavailable": state="unavailable"
            else: state="fresh_as_of_fetch" if age <= max_age_seconds else "stale"
            p.update({"freshness":state,"as_of":now,"age_seconds":age,"offline":bool(offline),"authoritative":False,"confirmation_eligible":False,"next_action":"refresh" if state in {"stale","unavailable","invalidated"} else "observe_unverified"})
            rows.append(p)
        return rows

def initialize_cache(*, projects_root, project_id, repository_id, repository_locator_digest, producer_contract="unknown", producer_version="unknown"):
    ledger, lm = _authority(projects_root, project_id); path=_cache_path(projects_root, project_id); locator=_digest_locator(repository_locator_digest)
    try:
        cache=GitHubEvidenceCache(path)
        old=cache._meta()
        binding={"project_id":lm["project_id"],"repository_id":repository_id,"repository_locator_digest":locator,"host_kind":"github","producer_contract":producer_contract,"producer_version":producer_version,"generation":lm["generation"],"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
        for k,v in binding.items():
            if k in old and old[k] != str(v): raise CacheHold("hold_cache_binding_mismatch")
            cache._setmeta(k,v)
        cache.db.commit(); return {"outcome":"cache_initialized","authoritative":False,"project_id":lm["project_id"],"cache_path_digest":_hash(str(path)),"generation":lm["generation"]}
    finally: ledger.close()

def read_cache(*, projects_root, project_id, evaluated_at, max_age_seconds, offline=False):
    ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        if not path.is_file(): return {"outcome":"cache_miss","entries":[],"authoritative":False,"offline":bool(offline),"counters":{}}
        cache=GitHubEvidenceCache(path,read_only=True); meta=cache._meta()
        if meta.get("project_id") != lm["project_id"]: raise CacheHold("hold_cache_binding_mismatch")
        return {"outcome":"cache_hit","entries":cache.read(evaluated_at=evaluated_at,max_age_seconds=max_age_seconds,offline=offline),"metadata":meta,"authoritative":False,"confirmation_eligible":False,"counters":{r["name"]:r["value"] for r in cache.db.execute("SELECT * FROM counters")}}
    finally: ledger.close()

def refresh_cache(*, projects_root, project_id, repository_id, repository_locator_digest, selectors, evaluated_at, max_age_seconds, producer, reason="targeted"):
    if not isinstance(selectors, Sequence) or isinstance(selectors,(str,bytes)) or not 1 <= len(selectors) <= 25: raise CacheHold("hold_cache_scope")
    _ts(evaluated_at)
    ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        if not path.is_file(): raise CacheHold("hold_cache_authority_unready")
        cache=GitHubEvidenceCache(path); meta=cache._meta()
        if meta.get("project_id") != lm["project_id"] or meta.get("repository_id") != str(repository_id) or meta.get("repository_locator_digest") != _digest_locator(repository_locator_digest): raise CacheHold("hold_cache_binding_mismatch")
        before=int(meta.get("generation","0")); result=producer.fetch_evidence({"project_id":lm["project_id"],"repository_id":repository_id},list(selectors),{"trust_domain":"same_process_reference","production_eligibility":False})
        if not isinstance(result,Mapping) or result.get("trust_domain") != "same_process_reference" or result.get("production_eligibility") is not False: raise CacheHold("hold_cache_producer_untrusted")
        entries=[_entry(e,lm["project_id"],str(repository_id)) for e in result.get("entries",[])];
        if len(entries)>25 or sum(len(_canon(e).encode()) for e in entries)>256*1024: raise CacheHold("hold_cache_scope")
        cache.db.execute("BEGIN IMMEDIATE")
        current=int(cache._meta().get("generation","0"));
        if current != before: cache.db.execute("ROLLBACK"); raise CacheHold("hold_cache_generation_conflict")
        changed=0; duplicates=0
        for e in entries:
            old=cache.db.execute("SELECT payload_hash,source_revision FROM entries WHERE entry_key=?",(e["entry_key"],)).fetchone()
            if old and old["source_revision"] == e.get("source_revision"):
                if old["payload_hash"] != e["payload_hash"]: cache.db.execute("ROLLBACK"); raise CacheHold("hold_cache_divergent_revision")
                duplicates += 1; continue
            cache.db.execute("INSERT OR REPLACE INTO entries VALUES (?,?,?,?,?,?,?)",(e["entry_key"],_canon(e),e["payload_hash"],e.get("source_revision"),e["fetched_at"],"partial" if e["coverage"]=="partial" else "fresh_as_of_fetch",0)); changed+=1
        newgen=before+changed; cache._setmeta("generation",newgen); cache._setmeta("updated_at",evaluated_at); cache._counter("producer_invocations"); cache._counter("refresh_requests"); rid=cache._receipt("refresh",{"generation":newgen,"changed":changed,"duplicates":duplicates,"producer_id":str(result.get("producer_id","unknown")),"production_eligibility":False}); cache.db.execute("COMMIT")
        return {"outcome":"cache_duplicate" if not changed else ("cache_partial" if any(e["coverage"]!="complete" for e in entries) else "cache_refreshed"),"generation":newgen,"changed_count":changed,"duplicate_count":duplicates,"receipt_id":rid,"authoritative":False,"confirmation_eligible":False}
    except CacheHold: 
        try:
            if cache.db.in_transaction: cache.db.execute("ROLLBACK")
        except Exception: pass
        raise
    finally: ledger.close()

def invalidate_cache_entries(*, projects_root, project_id, entry_keys, reason, evaluated_at):
    _ts(evaluated_at); ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        cache=GitHubEvidenceCache(path); keys=list(entry_keys); cache.db.execute("BEGIN IMMEDIATE")
        for key in keys: cache.db.execute("UPDATE entries SET invalidated=1,state='invalidated' WHERE entry_key=?",(key,))
        rid=cache._receipt("invalidate",{"count":len(keys),"reason_digest":_hash(reason)}); cache.db.commit(); return {"outcome":"cache_invalidated","count":len(keys),"receipt_id":rid}
    finally: ledger.close()

def rebuild_cache(*, projects_root, project_id, repository_id, repository_locator_digest, entries, evaluated_at):
    _ts(evaluated_at); ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        cache=GitHubEvidenceCache(path); meta=cache._meta()
        if meta.get("repository_id") != str(repository_id) or meta.get("repository_locator_digest") != _digest_locator(repository_locator_digest): raise CacheHold("hold_cache_binding_mismatch")
        normalized=[_entry(e,lm["project_id"],str(repository_id)) for e in entries]
        if len(normalized)>25 or sum(len(_canon(e).encode()) for e in normalized)>256*1024: raise CacheHold("hold_cache_scope")
        cache.db.execute("BEGIN IMMEDIATE"); cache.db.execute("DELETE FROM entries")
        for e in normalized: cache.db.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,?)",(e["entry_key"],_canon(e),e["payload_hash"],e.get("source_revision"),e["fetched_at"],"fresh_as_of_fetch",0))
        gen=int(meta.get("generation","0"))+1; cache._setmeta("generation",gen); rid=cache._receipt("rebuild",{"generation":gen,"count":len(normalized)}); cache.db.commit(); return {"outcome":"cache_rebuilt","generation":gen,"receipt_id":rid}
    finally: ledger.close()

def project_cache_readout(*, projects_root, project_id):
    ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        if not path.is_file(): return {"outcome":"cache_miss","authoritative":False,"counters":{}}
        cache=GitHubEvidenceCache(path,read_only=True)
        return {"outcome":"cache_hit","authoritative":False,"metadata":cache._meta(),"counters":{r["name"]:r["value"] for r in cache.db.execute("SELECT * FROM counters")}}
    finally: ledger.close()

def plan_cache_cleanup(*, projects_root, project_id, disposal_reason, owner_receipt):
    ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        if not isinstance(disposal_reason,str) or not disposal_reason or not isinstance(owner_receipt,str) or not owner_receipt: raise CacheHold("hold_cache_cleanup_gate")
        if not path.is_file(): return {"outcome":"cache_cleanup_planned","exists":False,"cache_path_digest":_hash(str(path)),"project_id":lm["project_id"]}
        return {"outcome":"cache_cleanup_planned","exists":True,"cache_path_digest":_hash(str(path)),"project_id":lm["project_id"],"reason_digest":_hash(disposal_reason),"owner_receipt_digest":_hash(owner_receipt)}
    finally: ledger.close()

def apply_cache_cleanup(*, projects_root, project_id, cache_path_digest, disposal_reason, owner_receipt):
    if not isinstance(owner_receipt,str) or not owner_receipt: raise CacheHold("hold_cache_cleanup_gate")
    ledger,lm=_authority(projects_root,project_id); path=_cache_path(projects_root,project_id)
    try:
        if _hash(str(path)) != cache_path_digest or not isinstance(disposal_reason,str) or not disposal_reason: raise CacheHold("hold_cache_cleanup_gate")
        if path.exists():
            for suffix in ("", "-wal", "-shm"):
                target=Path(str(path)+suffix)
                if target.exists(): target.unlink()
        return {"outcome":"cache_cleaned","project_id":lm["project_id"],"cache_path_digest":cache_path_digest,"owner_receipt_digest":_hash(owner_receipt)}
    finally: ledger.close()

__all__=["GitHubEvidenceCache","CacheError","CacheHold","CacheIntegrityError","initialize_cache","read_cache","refresh_cache","invalidate_cache_entries","rebuild_cache","project_cache_readout","plan_cache_cleanup","apply_cache_cleanup"]
