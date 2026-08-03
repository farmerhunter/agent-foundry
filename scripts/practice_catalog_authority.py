#!/usr/bin/env python3
"""Synthetic lifecycle authority readout; no Vault or backend I/O."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

WORKING_TREE = "working_tree_authority"
SNAPSHOT_SHADOW = "snapshot_shadow"
SNAPSHOT = "snapshot_authority"
ROLLBACK = "rollback_pending"
HELD = "held"


@dataclass(frozen=True)
class SyntheticAuthorityBackend:
    version: str
    generation: int
    snapshot_hash: str
    trusted: bool = True


def _hash(value: object) -> str | None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        return None
    return value


def authority_readout(mode: str = WORKING_TREE, backend: object | None = None, *, vault_dirty: bool = False, marker_drift: bool = False, replica_drift: bool = False, migration: str = "none", backup: str = "not_required", rollback: str = "not_required", receipt: str = "verified", expected_snapshot_hash: str | None = None, operations: tuple[str, ...] = ("read",)) -> dict[str, Any]:
    if mode == WORKING_TREE:
        return {"mode": mode, "authority_id": "working-tree", "backend_version": "n/a", "generation": None, "content_hash": None, "replica_drift": False, "migration": migration, "holds": [], "backup_rollback": {"backup": backup, "rollback": rollback}, "operations": list(operations)}
    holds: list[str] = []
    if backend is None:
        holds.append("held_backend_unavailable")
    elif not isinstance(backend, SyntheticAuthorityBackend) or not backend.trusted or not backend.version or type(backend.generation) is not int or backend.generation < 0 or _hash(backend.snapshot_hash) is None:
        holds.append("held_backend_untrusted")
    if vault_dirty:
        holds.append("dirty_vault")
    if marker_drift:
        holds.append("marker_path_hash_drift")
    if replica_drift:
        holds.append("replica_drift")
    if backend is not None and expected_snapshot_hash is not None and backend.snapshot_hash != expected_snapshot_hash:
        holds.append("snapshot_hash_mismatch")
    if backend is not None and backup == "failed":
        holds.append("backup_failed")
    if backend is not None and rollback == "pending":
        holds.append("rollback_pending")
    if backend is not None and receipt != "verified":
        holds.append("receipt_verification_failed")
    if any(operation not in {"read", "status"} for operation in operations):
        holds.append("write_operation_forbidden")
    if migration not in {"none", "complete"}:
        holds.append("legacy_or_partial_migration")
    if mode == SNAPSHOT and not holds:
        state = SNAPSHOT
    elif mode == SNAPSHOT_SHADOW and not holds:
        state = SNAPSHOT_SHADOW
    else:
        state = HELD
    return {"mode": state, "authority_id": "snapshot" if backend else None, "backend_version": getattr(backend, "version", None), "generation": getattr(backend, "generation", None), "content_hash": getattr(backend, "snapshot_hash", None), "replica_drift": replica_drift, "migration": migration, "holds": holds, "backup_rollback": {"backup": backup, "rollback": rollback}, "operations": list(operations), "qualification_state": "production_candidate", "production_eligibility": False}


def synthetic_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
