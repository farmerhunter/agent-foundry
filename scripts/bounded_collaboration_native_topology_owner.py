#!/usr/bin/env python3
"""Fixture-only protected owner for the native bounded-collaboration topology."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from codex_host_rolehub_adapter import ThreadMetadata

VERSION = "bounded-collaboration-native-topology-owner-v2"
LEGACY_VERSION = "bounded-collaboration-native-topology-owner-v1"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ROLES = (("Coordinator", "AF18 Coordinator"), ("Architect", "AF18 Durable Architect"))


class _LegacyTopologyHold(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canon(value).encode()).hexdigest()


def _opaque(role: str, native_id: str) -> str:
    return role.lower() + ":" + hashlib.sha256((role + "\0" + native_id).encode()).hexdigest()[:24]


def _permit_claim(context: Mapping[str, Any], *, host_digest: str, runtime_digest: str) -> str:
    required = ("onboarding_key", "project_id", "project_binding_ref", "project_binding_digest", "root_digest", "scheduler_binding_digest", "topology_plan_digest", "topology_preimage_digest", "mapping_digest")
    return _digest({key: context[key] for key in required} | {"host_digest": host_digest, "runtime_digest": runtime_digest, "budget": context.get("create_budget")})


class TrustedRuntime:
    """Fixture issuer. Its permits are deliberately not JSON-serializable."""
    def __init__(self, runtime_digest: str = "sha256:" + "1" * 64):
        self._secret = object(); self.runtime_digest = runtime_digest

    def issue_permit(self, *, host_digest: str, nonce: str = "fixture-nonce", expires_at: float | None = None) -> "_Permit":
        return _Permit(self._secret, self.runtime_digest, host_digest, nonce, time.monotonic() + 60 if expires_at is None else expires_at)


class _Permit:
    __slots__ = ("_secret", "runtime_digest", "host_digest", "nonce", "expires_at", "_binding")
    def __init__(self, secret: object, runtime_digest: str, host_digest: str, nonce: str, expires_at: float):
        self._secret, self.runtime_digest, self.host_digest, self.nonce, self.expires_at = secret, runtime_digest, host_digest, nonce, expires_at
        self._binding: str | None = None
    def __reduce__(self): raise TypeError("permit_not_serializable")
    def __repr__(self): return "<opaque-native-topology-permit>"


@dataclass
class _Guard:
    consumed: bool = False


class NativeRoleTopologyOwner:
    """Unbound/read-only owner. Native creation is impossible until bound."""
    def __init__(self, projects_root: str | Path, project_root: str | Path, host: Any, *, runtime: TrustedRuntime | None = None, host_digest: str = "sha256:" + "2" * 64):
        self._projects_root = Path(projects_root); self._project_root = Path(project_root)
        self._host, self._runtime, self._host_digest = host, runtime, host_digest

    def _identity(self, binding: Mapping[str, Any]) -> tuple[dict[str, str] | None, str | None]:
        project_id = binding.get("project_id")
        if not isinstance(project_id, str): return None, "project_identity_invalid"
        try:
            if str(uuid.UUID(project_id)) != project_id: return None, "project_identity_invalid"
        except (ValueError, AttributeError, TypeError): return None, "project_identity_invalid"
        pd, rd = binding.get("project_binding_digest"), binding.get("root_digest")
        if not isinstance(pd, str) or not isinstance(rd, str) or not _DIGEST.fullmatch(pd) or not _DIGEST.fullmatch(rd): return None, "project_identity_invalid"
        try:
            root = self._projects_root.resolve(strict=True); project_dir = root / project_id
            if not self._projects_root.is_absolute() or self._projects_root.is_symlink() or root != self._projects_root or project_dir.is_symlink() or not project_dir.is_dir() or project_dir.resolve(strict=True).parent != root:
                return None, "project_identity_invalid"
            authority = project_dir / "collaboration.db"
            if authority.is_symlink() or not authority.is_file(): return None, "project_identity_invalid"
            store = project_dir / "role-topology.db"
            # SQLite follows a final symlink when opening a missing database;
            # reject it before constructing a connection or issuing host calls.
            if store.is_symlink() or (store.exists() and (not store.is_file() or store.resolve(strict=True).parent != project_dir.resolve(strict=True))):
                return None, "project_identity_invalid"
        except OSError: return None, "project_identity_invalid"
        mapping = _digest({"owner_version": VERSION, "project_id": project_id, "project_binding_digest": pd, "root_digest": rd})
        return {"project_id": project_id, "project_binding_digest": pd, "root_digest": rd, "mapping_digest": mapping, "store": str(store)}, None

    def _connect(self, identity: Mapping[str, str], *, create: bool) -> sqlite3.Connection | None:
        path = Path(identity["store"])
        if not create and not path.exists(): return None
        if create:
            os.chmod(path.parent, 0o700)
            con = sqlite3.connect(path, timeout=0.1)
            con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA synchronous=FULL")
            con.execute("PRAGMA trusted_schema=OFF"); con.execute("PRAGMA foreign_keys=ON")
            con.execute("CREATE TABLE IF NOT EXISTS topology (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
            os.chmod(path, 0o600)
            con.execute("INSERT OR IGNORE INTO topology(k,v) VALUES('schema_version',?)", (VERSION,))
        else:
            if (path.stat().st_mode & 0o777) != 0o600 or (path.parent.stat().st_mode & 0o777) != 0o700:
                raise ValueError("owner_store_permission_hold")
            con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True, timeout=0.1)
            con.execute("PRAGMA trusted_schema=OFF")
            if con.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal": con.close(); raise ValueError("owner_store_schema_unknown")
            if con.execute("PRAGMA synchronous").fetchone()[0] != 2: con.close(); raise ValueError("owner_store_schema_unknown")
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok": con.close(); raise ValueError("owner_store_integrity_hold")
            if not any(row[0] == "topology" for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")): con.close(); raise ValueError("owner_store_schema_unknown")
            schema = con.execute("SELECT v FROM topology WHERE k='schema_version'").fetchone()
            if schema is not None and schema[0] == LEGACY_VERSION:
                con.close(); raise _LegacyTopologyHold("legacy_topology_migration_required")
            if schema is None or schema[0] != VERSION: con.close(); raise ValueError("owner_store_schema_unknown")
        row = con.execute("SELECT v FROM topology WHERE k='mapping'").fetchone()
        if row is None:
            if not create: con.close(); raise ValueError("owner_store_schema_unknown")
            con.execute("INSERT INTO topology(k,v) VALUES('mapping',?)", (identity["mapping_digest"],)); con.commit()
        elif row[0] != identity["mapping_digest"]:
            con.close(); raise ValueError("project_binding_mismatch")
        return con

    def _record(self, con: sqlite3.Connection, key: str) -> Mapping[str, Any] | None:
        row = con.execute("SELECT v FROM topology WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def _read_target(self) -> tuple[Any, str]:
        return self._host, str(self._project_root.resolve(strict=True))

    def _verify_stored_host(self, record: Mapping[str, Any]) -> str | None:
        """Re-read private IDs without ever projecting them into public output."""
        topology, native_ids = record.get("topology"), record.get("native_ids")
        if not isinstance(topology, Mapping) or not isinstance(native_ids, Mapping) or set(native_ids) != {role for role, _ in _ROLES}:
            return "owner_store_integrity_hold"
        if not all(isinstance(native_ids[role], str) and native_ids[role] for role, _ in _ROLES) or len(set(native_ids.values())) != 2:
            return "owner_store_integrity_hold"
        project_id = topology.get("project_id")
        if not isinstance(project_id, str):
            return "owner_store_integrity_hold"
        try:
            host, root = self._read_target()
            for role, title in _ROLES:
                metadata = host.read_thread(native_ids[role], include_turns=False)
                if not isinstance(metadata, ThreadMetadata) or metadata.id != native_ids[role] or metadata.project_id != project_id or metadata.cwd != root or metadata.name != title or topology.get(role.lower() + "_ref") != _opaque(role, metadata.id):
                    return "native_metadata_mismatch"
        except Exception:
            return "native_readback_unavailable"
        return None

    def _final_inventory_attempt(self, attempt: Mapping[str, Any] | None, identity: Mapping[str, str], plan: Mapping[str, Any] | None = None) -> bool:
        if not isinstance(attempt, Mapping):
            return False
        required = {
            "state": "verifying",
            "pending_role": "final_inventory",
            "pending_title": None,
            "mapping_digest": identity["mapping_digest"],
            "project_id": identity["project_id"],
            "project_binding_digest": identity["project_binding_digest"],
            "root_digest": identity["root_digest"],
        }
        if any(attempt.get(key) != value for key, value in required.items()):
            return False
        if not isinstance(attempt.get("topology_plan_digest"), str) or not attempt["topology_plan_digest"]:
            return False
        if plan is not None and attempt["topology_plan_digest"] != plan.get("topology_plan_digest"):
            return False
        if attempt.get("operation_budget") != [role for role, _ in _ROLES] or attempt.get("roles") != [role for role, _ in _ROLES]:
            return False
        maps = (attempt.get("native_ids"), attempt.get("operation_refs"), attempt.get("readback_digests"), attempt.get("operations"))
        expected = {role for role, _ in _ROLES}
        if not all(isinstance(value, Mapping) and set(value) == expected for value in maps):
            return False
        native_ids, operation_refs, readback_digests, operations = maps
        if not all(isinstance(native_ids[role], str) and native_ids[role] for role, _ in _ROLES) or len(set(native_ids.values())) != 2:
            return False
        for role, title in _ROLES:
            expected_ref = "operation:" + hashlib.sha256((attempt["topology_plan_digest"] + role).encode()).hexdigest()[:24]
            operation = operations[role]
            if operation_refs[role] != expected_ref or not isinstance(readback_digests[role], str) or not _DIGEST.fullmatch(readback_digests[role]):
                return False
            if not isinstance(operation, Mapping) or set(operation) != {"native_id", "title", "project_id", "readback_digest", "operation_ref"}:
                return False
            if operation != {"native_id": native_ids[role], "title": title, "project_id": identity["project_id"], "readback_digest": readback_digests[role], "operation_ref": expected_ref}:
                return False
        return True

    def _completion_from_attempt(self, con: sqlite3.Connection, identity: Mapping[str, str], attempt: Mapping[str, Any], source: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, str | None]:
        if not self._final_inventory_attempt(attempt, identity, source):
            return None, "partial_native_apply"
        created: dict[str, ThreadMetadata] = {}
        try:
            host, root = self._read_target()
            for role, title in _ROLES:
                native_id = attempt["native_ids"][role]
                metadata = host.read_thread(native_id, include_turns=False)
                digest = _digest({"id": getattr(metadata, "id", None), "project_id": getattr(metadata, "project_id", None), "cwd": getattr(metadata, "cwd", None), "name": getattr(metadata, "name", None)})
                operation = attempt["operations"][role]
                if not isinstance(metadata, ThreadMetadata) or metadata.id != native_id or metadata.project_id != identity["project_id"] or metadata.cwd != root or metadata.name != title or digest != attempt["readback_digests"][role] or operation["readback_digest"] != digest:
                    return None, "native_metadata_mismatch"
                created[role] = metadata
        except Exception:
            return None, "native_readback_unavailable"
        record, binding = self._build_completion(identity, source, created)
        con.execute("INSERT OR REPLACE INTO topology(k,v) VALUES('completion',?)", (_canon(record),)); con.commit()
        return binding, None

    def _build_completion(self, identity: Mapping[str, str], source: Mapping[str, Any], created: Mapping[str, ThreadMetadata]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        refs = tuple("operation:" + hashlib.sha256((source["topology_plan_digest"] + role).encode()).hexdigest()[:24] for role, _ in _ROLES)
        topology_digest = _digest({role: _opaque(role, created[role].id) for role, _ in _ROLES})
        binding = {"topology_apply_binding_ref": "topology-apply:" + hashlib.sha256((source["topology_plan_digest"] + identity["mapping_digest"]).encode()).hexdigest()[:24], "topology_plan_digest": source["topology_plan_digest"], "onboarding_key": source["onboarding_key"], "project_binding_digest": source["project_binding_digest"], "scheduler_binding_digest": source["scheduler_binding_digest"], "operation_receipt_refs": list(refs), "operation_receipt_refs_digest": _digest(list(refs)), "requested_roles": ["Coordinator", "Architect"], "coordinator_ref": _opaque("Coordinator", created["Coordinator"].id), "architect_ref": _opaque("Architect", created["Architect"].id), "topology_readback_digest": topology_digest}
        binding["topology_apply_binding_digest"] = _digest(binding)
        topology = {"owner_version": VERSION, "project_id": identity["project_id"], "coordinator_ref": binding["coordinator_ref"], "architect_ref": binding["architect_ref"], "topology_readback_digest": topology_digest, "project_binding_digest": source["project_binding_digest"], "coordinator_count": 1, "architect_count": 1, "topology_apply_binding_ref": binding["topology_apply_binding_ref"], "topology_apply_binding_digest": binding["topology_apply_binding_digest"], "topology_apply_binding": binding}
        completion = {"owner_version": VERSION, "completion_receipt_ref": "completion:" + hashlib.sha256((source["onboarding_key"] + binding["topology_apply_binding_digest"]).encode()).hexdigest()[:24], "onboarding_key": source["onboarding_key"], "project_binding_ref": source["project_binding_ref"], "project_binding_digest": source["project_binding_digest"], "scheduler_binding_ref": source["scheduler_binding_ref"], "work_root_ref": source["work_root_ref"], "scheduler_binding_revision": source["scheduler_binding_revision"], "scheduler_binding_digest": source["scheduler_binding_digest"], "topology_plan_digest": source["topology_plan_digest"], "operation_receipt_refs": list(refs), "topology_apply_binding_ref": binding["topology_apply_binding_ref"], "topology_apply_binding_digest": binding["topology_apply_binding_digest"], "coordinator_ref": topology["coordinator_ref"], "architect_ref": topology["architect_ref"], "topology_readback_digest": topology_digest}
        return {"onboarding_key": source["onboarding_key"], "topology": topology, "completion": completion, "native_ids": {role: created[role].id for role, _ in _ROLES}}, binding

    def read_topology(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        identity, reason = self._identity(project_binding)
        if reason: return {"state": "held", "reason": reason}
        try: con = self._connect(identity, create=False)
        except _LegacyTopologyHold: return {"state": "held", "reason": "legacy_topology_migration_required"}
        except (OSError, sqlite3.Error, ValueError): return {"state": "held", "reason": "owner_store_unavailable"}
        if con is None: return {"state": "missing"}
        try:
            rec = self._record(con, "completion")
            if rec is None:
                return {"state": "missing"} if self._final_inventory_attempt(self._record(con, "attempt"), identity) else {"state": "held", "reason": "partial_native_apply"}
            reason = self._verify_stored_host(rec)
            if reason: return {"state": "held", "reason": reason}
            return {"state": "ready", **rec["topology"]}
        finally: con.close()

    def read_completion(self, onboarding_key: str, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        identity, reason = self._identity(project_binding)
        if reason: return {"state": "held", "reason": reason}
        try: con = self._connect(identity, create=False)
        except _LegacyTopologyHold: return {"state": "held", "reason": "legacy_topology_migration_required"}
        except (OSError, sqlite3.Error, ValueError): return {"state": "held", "reason": "owner_store_unavailable"}
        if con is None: return {"state": "absent"}
        try:
            rec = self._record(con, "completion")
            if rec is None:
                return {"state": "absent"} if self._final_inventory_attempt(self._record(con, "attempt"), identity) else {"state": "held", "reason": "partial_native_apply"}
            if rec.get("onboarding_key") != onboarding_key: return {"state": "absent"}
            reason = self._verify_stored_host(rec)
            if reason: return {"state": "held", "reason": reason}
            return {"state": "ready", **rec["completion"]}
        finally: con.close()

    def apply_topology(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"state": "held", "reason": "authorization_unavailable"}

    def bind_permit(self, permit: object, context: Mapping[str, Any]) -> "PermitBoundNativeRoleTopologyOwner | None":
        if not isinstance(permit, _Permit) or self._runtime is None or permit._secret is not self._runtime._secret or permit.expires_at <= time.monotonic() or permit.runtime_digest != self._runtime.runtime_digest or permit.host_digest != self._host_digest:
            return None
        required = ("onboarding_key", "project_id", "project_binding_ref", "project_binding_digest", "root_digest", "scheduler_binding_digest", "topology_plan_digest", "topology_preimage_digest", "mapping_digest")
        if not all(isinstance(context.get(key), str) and context[key] for key in required):
            return None
        identity, reason = self._identity({"project_id": context["project_id"], "project_binding_digest": context["project_binding_digest"], "root_digest": context["root_digest"]})
        if reason or identity is None or identity["mapping_digest"] != context["mapping_digest"] or not _DIGEST.fullmatch(str(context["scheduler_binding_digest"])) or not _DIGEST.fullmatch(str(context["topology_plan_digest"])):
            return None
        binding = _permit_claim(context, host_digest=self._host_digest, runtime_digest=self._runtime.runtime_digest)
        if permit._binding is not None:
            return None
        # Claim before producing a bound owner, so an interrupted caller cannot
        # replay the same opaque permit against another owner/project.
        permit._binding = binding
        return PermitBoundNativeRoleTopologyOwner(self, permit, MappingProxyType(dict(context)), MappingProxyType(dict(identity)), str(self._project_root.resolve(strict=True)), self._host, self._runtime, self._host_digest, binding, _Guard())


class ProtectedLocalTopologyProjectionOwner:
    """Host-free read-only projection of a protected completed topology."""

    def __init__(self, projects_root: str | Path, project_root: str | Path):
        self._reader = NativeRoleTopologyOwner(projects_root, project_root, None)

    def _validated_record(
        self,
        project_binding: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any] | None, str | None]:
        identity, reason = self._reader._identity(project_binding)
        if reason or identity is None:
            return None, reason or "project_identity_invalid"
        try:
            con = self._reader._connect(identity, create=False)
        except _LegacyTopologyHold:
            return None, "legacy_topology_migration_required"
        except (OSError, sqlite3.Error, ValueError):
            return None, "owner_store_unavailable"
        if con is None:
            return None, "owner_store_missing"
        try:
            record = self._reader._record(con, "completion")
        except (json.JSONDecodeError, sqlite3.Error, TypeError, ValueError):
            return None, "owner_store_integrity_hold"
        finally:
            con.close()
        if not isinstance(record, Mapping) or set(record) != {"onboarding_key", "topology", "completion", "native_ids"}:
            return None, "owner_store_integrity_hold"
        topology = record.get("topology")
        completion = record.get("completion")
        native_ids = record.get("native_ids")
        if not isinstance(topology, Mapping) or not isinstance(completion, Mapping) or not isinstance(native_ids, Mapping):
            return None, "owner_store_integrity_hold"
        topology_keys = {
            "owner_version", "project_id", "coordinator_ref", "architect_ref",
            "topology_readback_digest", "project_binding_digest", "coordinator_count",
            "architect_count", "topology_apply_binding_ref",
            "topology_apply_binding_digest", "topology_apply_binding",
        }
        completion_keys = {
            "owner_version", "completion_receipt_ref", "onboarding_key",
            "project_binding_ref", "project_binding_digest", "scheduler_binding_ref",
            "work_root_ref", "scheduler_binding_revision", "scheduler_binding_digest",
            "topology_plan_digest", "operation_receipt_refs",
            "topology_apply_binding_ref", "topology_apply_binding_digest",
            "coordinator_ref", "architect_ref", "topology_readback_digest",
        }
        binding = topology.get("topology_apply_binding")
        binding_keys = {
            "topology_apply_binding_ref", "topology_plan_digest", "onboarding_key",
            "project_binding_digest", "scheduler_binding_digest",
            "operation_receipt_refs", "operation_receipt_refs_digest",
            "requested_roles", "coordinator_ref", "architect_ref",
            "topology_readback_digest", "topology_apply_binding_digest",
        }
        roles = {role for role, _ in _ROLES}
        if set(topology) != topology_keys or set(completion) != completion_keys or not isinstance(binding, Mapping) or set(binding) != binding_keys or set(native_ids) != roles:
            return None, "owner_store_integrity_hold"
        if not all(isinstance(native_ids[role], str) and native_ids[role] for role in roles) or len(set(native_ids.values())) != len(roles):
            return None, "owner_store_integrity_hold"
        onboarding_key = record.get("onboarding_key")
        plan_digest = binding.get("topology_plan_digest")
        if not isinstance(onboarding_key, str) or not onboarding_key or not isinstance(plan_digest, str) or not _DIGEST.fullmatch(plan_digest):
            return None, "owner_store_integrity_hold"
        refs = ["operation:" + hashlib.sha256((plan_digest + role).encode()).hexdigest()[:24] for role, _ in _ROLES]
        opaque = {role: _opaque(role, native_ids[role]) for role, _ in _ROLES}
        topology_digest = _digest(opaque)
        apply_ref = "topology-apply:" + hashlib.sha256((plan_digest + identity["mapping_digest"]).encode()).hexdigest()[:24]
        apply_digest = _digest({key: value for key, value in binding.items() if key != "topology_apply_binding_digest"})
        expected_shared = {
            "onboarding_key": onboarding_key,
            "project_binding_digest": identity["project_binding_digest"],
            "topology_plan_digest": plan_digest,
            "operation_receipt_refs": refs,
            "topology_apply_binding_ref": apply_ref,
            "topology_apply_binding_digest": apply_digest,
            "coordinator_ref": opaque["Coordinator"],
            "architect_ref": opaque["Architect"],
            "topology_readback_digest": topology_digest,
        }
        if (
            topology.get("owner_version") != VERSION
            or topology.get("project_id") != identity["project_id"]
            or topology.get("project_binding_digest") != identity["project_binding_digest"]
            or topology.get("coordinator_count") != 1
            or topology.get("architect_count") != 1
            or completion.get("owner_version") != VERSION
            or binding.get("requested_roles") != ["Coordinator", "Architect"]
            or binding.get("operation_receipt_refs_digest") != _digest(refs)
            or any(binding.get(key) != value for key, value in expected_shared.items())
            or any(topology.get(key) != value for key, value in expected_shared.items() if key in topology)
            or any(completion.get(key) != value for key, value in expected_shared.items())
            or completion.get("scheduler_binding_digest") != binding.get("scheduler_binding_digest")
            or topology.get("topology_apply_binding") != binding
            or completion.get("project_binding_ref") != project_binding.get("project_binding_ref")
            or completion.get("completion_receipt_ref") != "completion:" + hashlib.sha256((onboarding_key + apply_digest).encode()).hexdigest()[:24]
        ):
            return None, "owner_completion_binding_mismatch"
        return record, None

    def read_topology(self, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        record, reason = self._validated_record(project_binding)
        if reason or record is None:
            return {"state": "held", "reason": reason or "owner_store_unavailable"}
        return {"state": "ready", **record["topology"]}

    def read_completion(self, onboarding_key: str, project_binding: Mapping[str, Any]) -> Mapping[str, Any]:
        record, reason = self._validated_record(project_binding)
        if reason or record is None:
            return {"state": "held", "reason": reason or "owner_store_unavailable"}
        if record["onboarding_key"] != onboarding_key:
            return {"state": "absent"}
        return {"state": "ready", **record["completion"]}

    def apply_topology(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"state": "held", "reason": "authorization_unavailable"}


class PermitBoundNativeRoleTopologyOwner(NativeRoleTopologyOwner):
    def __init__(self, base: NativeRoleTopologyOwner, permit: _Permit, context: Mapping[str, Any], identity: Mapping[str, str], project_root: str, host: Any, runtime: TrustedRuntime, host_digest: str, claim: str, guard: _Guard):
        self.__dict__.update(base.__dict__)
        self._permit, self._context, self._sealed_context, self._sealed_identity, self._sealed_project_root, self._sealed_host, self._sealed_runtime, self._sealed_host_digest, self._claimed_binding, self._guard = permit, context, MappingProxyType(dict(context)), identity, project_root, host, runtime, host_digest, claim, guard

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False) and name in {"_context", "_sealed_context", "_sealed_identity", "_sealed_project_root", "_sealed_host", "_sealed_runtime", "_sealed_host_digest", "_claimed_binding", "_permit", "_guard", "_project_root", "_host", "_host_digest", "_runtime"}:
            raise AttributeError("permit_bound_owner_immutable")
        object.__setattr__(self, name, value)

    def _valid(self, plan: Mapping[str, Any]) -> tuple[dict[str, str] | None, str | None]:
        self._sealed = True
        context = self._sealed_context
        if self._guard.consumed or self._permit.expires_at <= time.monotonic() or self._permit._binding != self._claimed_binding or _permit_claim(context, host_digest=self._sealed_host_digest, runtime_digest=self._sealed_runtime.runtime_digest) != self._claimed_binding: return None, "authorization_unavailable"
        if self._host is not self._sealed_host or self._runtime is not self._sealed_runtime or self._host_digest != self._sealed_host_digest or str(self._project_root) != self._sealed_project_root:
            return None, "authorization_mismatch"
        required = ("onboarding_key", "project_binding_ref", "project_binding_digest", "scheduler_binding_digest", "topology_plan_digest", "topology_preimage_digest")
        if not isinstance(plan, Mapping) or any(plan.get(k) != context.get(k) for k in required) or tuple(plan.get("requested_roles", ())) != ("Coordinator", "Architect"):
            return None, "authorization_mismatch"
        if context.get("create_budget") != {"Coordinator": 1, "DurableArchitect": 1}: return None, "authorization_mismatch"
        identity = self._sealed_identity
        store = Path(identity["store"]); authority = store.parent / "collaboration.db"
        if store.is_symlink() or (store.exists() and (not store.is_file() or store.resolve(strict=True).parent != store.parent.resolve(strict=True))) or authority.is_symlink() or not authority.is_file():
            return None, "project_identity_invalid"
        if identity["mapping_digest"] != context.get("mapping_digest") or identity["project_id"] != context.get("project_id"):
            return None, "project_binding_mismatch"
        return dict(identity), None

    def _read_target(self) -> tuple[Any, str]:
        return self._sealed_host, self._sealed_project_root

    def _preflight_unmanaged_topology(self, identity: Mapping[str, str]) -> str | None:
        """Reject native title evidence not created by this protected owner."""
        try:
            host, root = self._read_target()
            for _, title in _ROLES:
                entries = host.list_threads(root)
                if not isinstance(entries, list):
                    return "native_readback_unavailable"
                matches = []
                for item in entries:
                    if not isinstance(item, ThreadMetadata) or item.cwd != root or item.project_id != identity["project_id"] or not item.id or not item.name:
                        return "topology_ambiguous"
                    if item.name == title:
                        matches.append(item)
                if len(matches) > 1:
                    return "topology_ambiguous"
                if matches:
                    return "unmanaged_existing_topology"
        except Exception:
            return "native_readback_unavailable"
        return None

    def apply_topology(self, plan: Mapping[str, Any]) -> Mapping[str, Any]:
        identity, reason = self._valid(plan)
        if reason: return {"state": "held", "reason": reason}
        self._guard.consumed = True
        try: existing = self._connect(identity, create=False)
        except (OSError, sqlite3.Error, ValueError): return {"state": "held", "reason": "owner_store_unavailable"}
        if existing is not None:
            try:
                if self._record(existing, "completion") is not None:
                    return {"state": "held", "reason": "completion_drift"}
                attempt = self._record(existing, "attempt")
                if not self._final_inventory_attempt(attempt, identity, plan):
                    return {"state": "held", "reason": "partial_native_apply"}
            finally:
                existing.close()
            try: con = self._connect(identity, create=True)
            except (OSError, sqlite3.Error, ValueError): return {"state": "held", "reason": "owner_store_unavailable"}
            assert con is not None
            try:
                source = {**plan, "scheduler_binding_ref": self._sealed_context["scheduler_binding_ref"], "work_root_ref": self._sealed_context["work_root_ref"], "scheduler_binding_revision": self._sealed_context["scheduler_binding_revision"]}
                binding, reason = self._completion_from_attempt(con, identity, self._record(con, "attempt") or {}, source)
                if reason or binding is None:
                    return {"state": "held", "reason": reason or "partial_native_apply"}
                return {"state": "applied", "mutation_performed": True, "topology_plan_digest": plan["topology_plan_digest"], "operation_receipt_refs": tuple(binding["operation_receipt_refs"]), "topology_apply_binding": binding}
            finally:
                con.close()
        reason = self._preflight_unmanaged_topology(identity)
        if reason: return {"state": "held", "reason": reason}
        try: con = self._connect(identity, create=True)
        except (OSError, sqlite3.Error, ValueError): return {"state": "held", "reason": "owner_store_unavailable"}
        assert con is not None
        try:
            if self._record(con, "completion") is not None: return {"state": "held", "reason": "completion_drift"}
            con.execute("INSERT OR REPLACE INTO topology(k,v) VALUES('attempt',?)", (_canon({"state": "prepared", "mapping_digest": identity["mapping_digest"], "roles": []}),)); con.commit()
            created: dict[str, ThreadMetadata] = {}
            def partial_result(force_mutation: bool = False) -> Mapping[str, Any]:
                refs = tuple("operation:" + hashlib.sha256((plan["topology_plan_digest"] + item).encode()).hexdigest()[:24] for item in created)
                persisted = self._record(con, "attempt") or {}
                mutated = force_mutation or bool(created or persisted.get("operations"))
                if not mutated:
                    return {"state": "held", "reason": "native_create_unavailable", "mutation_performed": False}
                return {"state": "applied", "mutation_performed": True, "topology_plan_digest": plan["topology_plan_digest"], "operation_receipt_refs": refs or ("operation:partial",), "topology_apply_binding": {}}
            for role, title in _ROLES:
                previous = self._record(con, "attempt") or {}
                attempt = {"state": "verifying", "mapping_digest": identity["mapping_digest"], "project_id": identity["project_id"], "project_binding_digest": identity["project_binding_digest"], "root_digest": identity["root_digest"], "topology_plan_digest": plan["topology_plan_digest"], "operation_budget": [item[0] for item in _ROLES], "roles": list(created), "pending_role": role, "pending_title": title, "operation_refs": previous.get("operation_refs", {}), "native_ids": previous.get("native_ids", {}), "readback_digests": previous.get("readback_digests", {}), "operations": previous.get("operations", {})}
                con.execute("INSERT OR REPLACE INTO topology(k,v) VALUES('attempt',?)", (_canon(attempt),)); con.commit()
                try:
                    md = self._sealed_host.create_thread(self._sealed_project_root)
                except Exception:
                    return partial_result()
                if not isinstance(md, ThreadMetadata) or not isinstance(getattr(md, "id", None), str) or not md.id:
                    return partial_result(True)
                created_before_name = {**attempt, "state": "verifying", "pending_role": role, "pending_title": title, "native_ids": {**attempt.get("native_ids", {}), role: md.id}, "operations": {**attempt.get("operations", {}), role: {"native_id": md.id, "title": title, "project_id": md.project_id, "operation_ref": "operation:" + hashlib.sha256((plan["topology_plan_digest"] + role).encode()).hexdigest()[:24], "readback_digest": None}}}
                con.execute("INSERT OR REPLACE INTO topology(k,v) VALUES('attempt',?)", (_canon(created_before_name),)); con.commit()
                if md.project_id != identity["project_id"] or md.cwd != self._sealed_project_root:
                    return partial_result()
                try:
                    named = self._sealed_host.set_thread_name(md.id, title); read = self._sealed_host.read_thread(named.id, include_turns=False)
                except Exception:
                    return partial_result()
                if not isinstance(read, ThreadMetadata) or read.id != md.id or read.project_id != identity["project_id"] or read.cwd != self._sealed_project_root or read.name != title: return partial_result()
                created[role] = read
                con.execute("INSERT OR REPLACE INTO topology(k,v) VALUES('attempt',?)", (_canon({**attempt, "state": "applying", "roles": list(created), "operation_refs": {item: "operation:" + hashlib.sha256((plan["topology_plan_digest"] + item).encode()).hexdigest()[:24] for item in created}, "native_ids": {item: created[item].id for item in created}, "readback_digests": {item: _digest({"id": created[item].id, "project_id": created[item].project_id, "cwd": created[item].cwd, "name": created[item].name}) for item in created}, "operations": {item: {"native_id": created[item].id, "title": created[item].name, "project_id": created[item].project_id, "readback_digest": _digest({"id": created[item].id, "project_id": created[item].project_id, "cwd": created[item].cwd, "name": created[item].name}), "operation_ref": "operation:" + hashlib.sha256((plan["topology_plan_digest"] + item).encode()).hexdigest()[:24]} for item in created}}),)); con.commit()
            prior = self._record(con, "attempt") or {}
            con.execute("INSERT OR REPLACE INTO topology(k,v) VALUES('attempt',?)", (_canon({**prior, "state": "verifying", "pending_role": "final_inventory", "pending_title": None}),)); con.commit()
            source = {**plan, "scheduler_binding_ref": self._sealed_context["scheduler_binding_ref"], "work_root_ref": self._sealed_context["work_root_ref"], "scheduler_binding_revision": self._sealed_context["scheduler_binding_revision"]}
            binding, reason = self._completion_from_attempt(con, identity, self._record(con, "attempt") or {}, source)
            if reason or binding is None:
                return partial_result()
            refs = tuple(binding["operation_receipt_refs"])
            return {"state": "applied", "mutation_performed": True, "topology_plan_digest": plan["topology_plan_digest"], "operation_receipt_refs": refs, "topology_apply_binding": binding}
        finally: con.close()


__all__ = ["NativeRoleTopologyOwner", "PermitBoundNativeRoleTopologyOwner", "ProtectedLocalTopologyProjectionOwner", "TrustedRuntime", "VERSION"]
