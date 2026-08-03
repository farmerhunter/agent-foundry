#!/usr/bin/env python3
"""Portable, synthetic-only reference contract for practice catalog snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


SNAPSHOT_FORMAT = "practice_catalog_snapshot_v1"
POINTER_FORMAT = "practice_catalog_pointer_v1"


class ValidationFailure(ValueError):
    pass


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    validate_manifest(manifest)
    return json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_hash(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()


def _valid_path(path: object) -> bool:
    return isinstance(path, str) and path and not path.startswith("/") and "\\" not in path and all(part not in {"", ".", ".."} for part in path.split("/"))


def _valid_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def validate_manifest(manifest: object) -> None:
    if not isinstance(manifest, dict) or manifest.get("format") != SNAPSHOT_FORMAT:
        raise ValidationFailure("invalid manifest format")
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValidationFailure("manifest records must be a list")
    paths: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not _valid_path(record.get("path")) or not _valid_hash(record.get("sha256")):
            raise ValidationFailure("invalid manifest record")
        if record["path"] in paths:
            raise ValidationFailure("duplicate manifest path")
        paths.add(record["path"])


def snapshot(snapshot_id: str, manifest: dict[str, Any], files: Mapping[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise ValidationFailure("invalid snapshot id")
    digest = manifest_hash(manifest)
    value: dict[str, Any] = {"format": SNAPSHOT_FORMAT, "snapshot_id": snapshot_id, "manifest": manifest, "manifest_sha256": digest}
    if files is not None:
        if not isinstance(files, Mapping) or any(not _valid_path(path) or not isinstance(content, str) for path, content in files.items()):
            raise ValidationFailure("invalid snapshot files")
        value["files"] = dict(files)
    return value


def validate_snapshot(value: object) -> None:
    if not isinstance(value, dict) or value.get("format") != SNAPSHOT_FORMAT:
        raise ValidationFailure("invalid snapshot format")
    if not isinstance(value.get("snapshot_id"), str) or not value["snapshot_id"]:
        raise ValidationFailure("invalid snapshot id")
    validate_manifest(value.get("manifest"))
    if value.get("manifest_sha256") != manifest_hash(value["manifest"]):
        raise ValidationFailure("manifest hash mismatch")
    files = value.get("files")
    if files is not None and (not isinstance(files, dict) or any(not _valid_path(path) or not isinstance(content, str) for path, content in files.items())):
        raise ValidationFailure("invalid snapshot files")


@dataclass(frozen=True)
class PointerReceipt:
    operation: str
    generation: int
    snapshot_hash: str
    receipt_id: str


class PointerStore:
    """Deterministic fake capability; no filesystem or network behavior."""

    def __init__(self, initial_hash: str):
        if not _valid_hash(initial_hash):
            raise ValidationFailure("invalid initial pointer hash")
        self._generation = 0
        self._snapshot_hash = initial_hash
        self.cas_calls = 0
        self.read_calls = 0

    def _receipt(self, operation: str) -> PointerReceipt:
        return PointerReceipt(operation, self._generation, self._snapshot_hash, f"{operation}:{self._generation}:{self._snapshot_hash[:12]}")

    def read(self) -> PointerReceipt:
        self.read_calls += 1
        return self._receipt("read")

    def compare_and_set(self, expected_generation: int, new_hash: str) -> PointerReceipt | None:
        self.cas_calls += 1
        if not isinstance(expected_generation, int) or not _valid_hash(new_hash):
            raise ValidationFailure("invalid CAS input")
        if expected_generation != self._generation:
            return None
        self._generation += 1
        self._snapshot_hash = new_hash
        return self._receipt("cas")


def _require_store(store: object) -> PointerStore:
    if not isinstance(store, PointerStore):
        raise ValidationFailure("unknown pointer capability")
    return store


def pinned_read(store: PointerStore, snapshots: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], PointerReceipt]:
    store = _require_store(store)
    receipt = store.read()
    value = snapshots.get(receipt.snapshot_hash)
    if value is None:
        raise ValidationFailure("pointer target snapshot missing")
    validate_snapshot(value)
    if value["manifest_sha256"] != receipt.snapshot_hash:
        raise ValidationFailure("pointer target hash mismatch")
    return value, receipt


def _manifest_file_hashes(value: dict[str, Any]) -> dict[str, str]:
    records = value["manifest"]["records"]
    return {record["path"]: record["sha256"] for record in records}


def _index_entries(index_text: str) -> list[dict[str, str]]:
    current: dict[str, str] | None = None
    entries: list[dict[str, str]] = []
    in_practices = False
    for line in index_text.splitlines():
        if line.startswith("practices:"):
            in_practices = True
            continue
        if in_practices and line and not line.startswith(" "):
            in_practices = False
        if not in_practices:
            continue
        if line.startswith("  - id: "):
            if current is not None:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip().strip('"')}
        elif current is not None and line.startswith("    ") and ":" in line:
            key, item = line.strip().split(":", 1)
            current[key] = item.strip().strip('"')
    if current is not None:
        entries.append(current)
    return entries


def _index_entry(index_text: str, practice_id: str) -> dict[str, str]:
    matches = [entry for entry in _index_entries(index_text) if entry.get("id") == practice_id]
    if len(matches) != 1:
        raise ValidationFailure("practice entry missing or duplicated")
    return matches[0]


def pinned_catalog_view(store: PointerStore, snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Validate the complete synthetic catalog through one pinned in-memory view."""
    store = _require_store(store)
    if not isinstance(snapshots, dict):
        raise ValidationFailure("unknown snapshot-view capability")
    receipt = store.read()
    if not isinstance(receipt, PointerReceipt) or receipt.operation != "read":
        raise ValidationFailure("invalid pinned pointer receipt")
    value = snapshots.get(receipt.snapshot_hash)
    if value is None:
        raise ValidationFailure("pointer target snapshot missing")
    validate_snapshot(value)
    if value["manifest_sha256"] != receipt.snapshot_hash:
        raise ValidationFailure("snapshot receipt hash mismatch")
    files = value.get("files")
    if not isinstance(files, dict):
        raise ValidationFailure("snapshot view files missing")
    hashes = _manifest_file_hashes(value)
    if set(files) != set(hashes):
        raise ValidationFailure("manifest and snapshot paths mismatch")
    for path, content in files.items():
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != hashes[path]:
            raise ValidationFailure("snapshot file hash mismatch")
    index_path = "indexes/practice_index.yaml"
    if index_path not in files:
        raise ValidationFailure("practice index missing")
    entries = _index_entries(files[index_path])
    if not entries:
        raise ValidationFailure("practice catalog entries missing")
    ids: set[str] = set()
    records: list[dict[str, str]] = []
    for entry in entries:
        practice_id = entry.get("id", "")
        path = entry.get("path")
        if not practice_id.startswith("SYN-") or practice_id in ids:
            raise ValidationFailure("synthetic catalog duplicate or non-synthetic id")
        if not _valid_path(path) or not path.startswith("practices/synthetic/"):
            raise ValidationFailure("practice entry path mismatch")
        if path != f"practices/synthetic/{practice_id}.md":
            raise ValidationFailure("practice entry filename mismatch")
        if path not in files or path not in hashes:
            raise ValidationFailure("practice record missing")
        practice = files[path]
        lines = practice.splitlines()
        if not lines or lines[0] != "---":
            raise ValidationFailure("practice frontmatter missing")
        end = next((index for index, line in enumerate(lines[1:], 1) if line == "---"), None)
        if end is None:
            raise ValidationFailure("practice frontmatter malformed")
        front_ids = [line.split(":", 1)[1].strip() for line in lines[1:end] if line.startswith("id:")]
        if len(front_ids) != 1:
            raise ValidationFailure("practice frontmatter id must be unique")
        front_id = front_ids[0]
        if front_id != practice_id:
            raise ValidationFailure("tampered practice entry")
        ids.add(practice_id)
        records.append({"id": practice_id, "path": path, "content": practice})
    return {"receipt": receipt, "snapshot_hash": receipt.snapshot_hash, "index": files[index_path], "records": records}


def injected_snapshot_view(store: PointerStore, snapshots: dict[str, dict[str, Any]], practice_id: str) -> dict[str, Any]:
    """Read a synthetic practice index and record through one pinned view.

    This is deliberately an injected in-memory capability. It resolves the pointer
    once, pins the returned receipt/hash, and never falls back to a working tree.
    """
    if not isinstance(practice_id, str) or not practice_id:
        raise ValidationFailure("invalid practice id")
    view = pinned_catalog_view(store, snapshots)
    matches = [record for record in view["records"] if record["id"] == practice_id]
    if len(matches) != 1:
        raise ValidationFailure("practice entry missing or duplicated")
    record = matches[0]
    return {
        "practice_id": practice_id,
        "index_path": "indexes/practice_index.yaml",
        "practice_path": record["path"],
        "index": view["index"],
        "practice": record["content"],
        "receipt": view["receipt"],
        "snapshot_hash": view["snapshot_hash"],
    }


validate_injected_snapshot_view = injected_snapshot_view


def commit_snapshot(store: PointerStore, snapshots: dict[str, dict[str, Any]], candidate: dict[str, Any], expected_generation: int, interrupt: str | None = None) -> dict[str, Any]:
    store = _require_store(store)
    before = store.read()
    try:
        validate_snapshot(candidate)
        candidate_hash = candidate["manifest_sha256"]
    except ValidationFailure:
        return {"state": "held_validation_failure", "pointer": before}
    snapshots[candidate_hash] = candidate
    if interrupt == "before_cas":
        return {"state": "held_interrupted_before_cas", "pointer": before}
    receipt = store.compare_and_set(expected_generation, candidate_hash)
    if receipt is None:
        return {"state": "held_cas_conflict", "pointer": store.read()}
    if interrupt == "after_cas_before_receipt":
        return {"state": "interrupted_after_cas_before_receipt", "pointer": receipt}
    return {"state": "committed", "pointer": receipt}


def recover_receipt(store: PointerStore, interrupted: dict[str, Any]) -> dict[str, Any]:
    store = _require_store(store)
    pointer = interrupted.get("pointer")
    if interrupted.get("state") != "interrupted_after_cas_before_receipt" or not isinstance(pointer, PointerReceipt):
        raise ValidationFailure("no recoverable interrupted commit")
    current = store.read()
    if current.generation != pointer.generation or current.snapshot_hash != pointer.snapshot_hash:
        raise ValidationFailure("interrupted pointer no longer current")
    return {"state": "committed_receipt_recovered", "pointer": PointerReceipt("recovery", current.generation, current.snapshot_hash, f"recovery:{current.generation}:{current.snapshot_hash[:12]}")}


def rollback(store: PointerStore, expected_generation: int, prior_hash: str, human_authorization: str | None) -> dict[str, Any]:
    store = _require_store(store)
    before = store.read()
    if not isinstance(human_authorization, str) or not human_authorization.strip():
        return {"state": "held_rollback_authorization_missing", "pointer": before}
    receipt = store.compare_and_set(expected_generation, prior_hash)
    if receipt is None:
        return {"state": "held_cas_conflict", "pointer": store.read()}
    return {"state": "rolled_back", "pointer": PointerReceipt("rollback", receipt.generation, receipt.snapshot_hash, f"rollback:{receipt.generation}:{receipt.snapshot_hash[:12]}")}


def retain_snapshots(snapshots: dict[str, dict[str, Any]], keep_hashes: set[str]) -> dict[str, Any]:
    """Return a receipt only; S0 retention never disposes synthetic snapshots."""
    if not keep_hashes or any(not _valid_hash(value) for value in keep_hashes):
        raise ValidationFailure("invalid retention set")
    missing = keep_hashes.difference(snapshots)
    if missing:
        raise ValidationFailure("retention target snapshot missing")
    return {"operation": "retention", "retained_hashes": sorted(keep_hashes), "removed_hashes": [], "disposed_hashes": [], "receipt_id": "retention:" + hashlib.sha256("|".join(sorted(keep_hashes)).encode()).hexdigest()[:12]}
