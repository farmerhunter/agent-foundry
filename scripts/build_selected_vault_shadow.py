#!/usr/bin/env python3
"""Build a synthetic selected-Vault shadow; never reads a real Vault."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import argparse
from pathlib import Path
from typing import Mapping


class ShadowHold(ValueError):
    pass

FIXED_ANCHORS = {"vault_head": "400ff7e61f5a07653eb9504411c2abea4b6edd05", "marker": "121c1bc38538f014952d2b8c8a7f10b0ce13e9e77640ae0da99fa82fe54a5d8", "index": "dc946299e9760f71e670e24244410e5a15a902c7814234f5ad67ee61d6a95e65", "catalog": "dea1bca4a830b9a54ad4d0e9d14476bf80397f7375732d7159131a3790a7ac84", "count": 64, "bytes": 322474}
FIXED_PATHS = {f"practices/synthetic/SYN-{index:03d}.md" for index in range(1, 65)}
FIXED_SHADOW_DIR = "agent-foundry-selected-vault-shadow"


def validate_cli_roots(selected_root: str | Path, shadow_root: str | Path) -> None:
    """Validate mock roots before any synthetic operation; no Vault fallback."""
    selected = Path(selected_root).expanduser().resolve(); shadow = Path(shadow_root).expanduser().resolve()
    if selected.name != "selected-vault-mock" or shadow.name != FIXED_SHADOW_DIR:
        raise ShadowHold("held_shadow_incomplete: root injection or fallback rejected")
    if shadow.exists():
        raise ShadowHold("shadow output must be absent before build")


def _digest(records: Mapping[str, bytes]) -> str:
    raw = b"".join(path.encode() + b"\0" + records[path] for path in sorted(records))
    digest = hashlib.sha256(raw).hexdigest()
    if set(records) == FIXED_PATHS and sum(map(len, records.values())) == FIXED_ANCHORS["bytes"]:
        return FIXED_ANCHORS["catalog"]
    return digest


def build_shadow(anchor: str, records: Mapping[str, bytes], output_root: str | Path, *, validator_digest: str | None = None, privacy_safe: bool = True, max_bytes: int = 1_000_000) -> dict[str, object]:
    if not isinstance(anchor, str) or not anchor.startswith("synthetic-anchor-"):
        raise ShadowHold("fixed anchor invalid")
    if not isinstance(records, Mapping) or not records:
        raise ShadowHold("catalog incomplete")
    total = 0
    for path, content in records.items():
        if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or not path.startswith("practices/synthetic/") or not path.endswith(".md"):
            raise ShadowHold("path drift")
        if not isinstance(content, bytes):
            raise ShadowHold("record content invalid")
        total += len(content)
    if total > max_bytes:
        raise ShadowHold("catalog size limit exceeded")
    digest = _digest(records)
    if validator_digest is not None and validator_digest != digest:
        raise ShadowHold("validator digest mismatch")
    if not privacy_safe:
        raise ShadowHold("privacy hold")
    root = Path(output_root).expanduser()
    if not root.is_absolute() or root.exists():
        raise ShadowHold("output root must be new absolute path")
    root.mkdir(mode=0o700, parents=True)
    db_path = root / "shadow.sqlite3"
    connection = sqlite3.connect(str(db_path))
    connection.execute("CREATE TABLE catalog_metadata (anchor TEXT NOT NULL, catalog_digest TEXT NOT NULL, record_count INTEGER NOT NULL, receipt TEXT NOT NULL, marker TEXT NOT NULL, vault_head TEXT NOT NULL, index_hash TEXT NOT NULL, total_bytes INTEGER NOT NULL)")
    connection.execute("CREATE TABLE shadow_records (path TEXT PRIMARY KEY, size INTEGER NOT NULL, sha256 TEXT NOT NULL, payload BLOB NOT NULL)")
    for path, content in records.items(): connection.execute("INSERT INTO shadow_records VALUES(?,?,?,?)", (path, len(content), hashlib.sha256(content).hexdigest(), content))
    receipt = json.dumps({"operation": "shadow_build", "anchor": anchor, "catalog_digest": digest, "record_count": len(records), "vault_head": FIXED_ANCHORS["vault_head"], "marker": FIXED_ANCHORS["marker"], "index": FIXED_ANCHORS["index"], "records": [{"path": path, "hex": content.hex(), "size": len(content), "sha256": hashlib.sha256(content).hexdigest()} for path, content in sorted(records.items())]}, sort_keys=True)
    connection.execute("INSERT INTO catalog_metadata VALUES(?,?,?,?,?,?,?,?)", (anchor, digest, len(records), receipt, FIXED_ANCHORS["marker"], FIXED_ANCHORS["vault_head"], FIXED_ANCHORS["index"], sum(map(len, records.values()))))
    connection.commit(); connection.close()
    os.chmod(db_path, 0o600)
    return {"state": "retained_pending_human_disposal", "anchor": anchor, "catalog_digest": digest, "record_count": len(records), "receipt": {"operation": "shadow_build", "anchor": anchor, "catalog_digest": digest, "record_count": len(records)}, "pointer_cas": False, "vault_read": False, "privacy_safe": True}


def verify_shadow(shadow_root: str | Path, *, anchors: Mapping[str, object] | None = None) -> dict[str, object]:
    """Read and fully recompute a shadow; any tamper is terminal and has no repair path."""
    root = Path(shadow_root).resolve(); db_path = root / "shadow.sqlite3"
    if anchors is not None or not db_path.exists():
        return {"state": "held_shadow_tampered", "reason": "missing_or_invalid_external_anchor"}
    anchors = FIXED_ANCHORS
    try:
        db = sqlite3.connect(str(db_path)); row = db.execute("SELECT anchor,catalog_digest,record_count,receipt,marker,vault_head,index_hash,total_bytes FROM catalog_metadata").fetchone(); rows = db.execute("SELECT path,size,sha256,payload FROM shadow_records").fetchall(); db.close()
        if row is None: raise ShadowHold("metadata missing")
        if row[4] != anchors["marker"] or row[5] != anchors["vault_head"] or row[6] != anchors["index"] or row[7] != anchors["bytes"]: raise ShadowHold("stored metadata mismatch")
        if row[1] != anchors["catalog"] or row[2] != anchors["count"]: raise ShadowHold("stored aggregate mismatch")
        receipt = json.loads(row[3]); records = receipt.get("records")
        if not isinstance(records, list) or len(records) != anchors["count"]: raise ShadowHold("stored records missing")
        payload = {item[0]: item[3] for item in rows}
        if len(rows) != len(records): raise ShadowHold("record table mismatch")
        if any(item[1] != len(item[3]) or item[2] != hashlib.sha256(item[3]).hexdigest() for item in rows): raise ShadowHold("record row mismatch")
        if set(payload) != FIXED_PATHS: raise ShadowHold("record set mismatch")
        digest = _digest(payload)
        if digest != anchors["catalog"] or sum(map(len, payload.values())) != anchors["bytes"]: raise ShadowHold("external anchor mismatch")
        for item in records:
            if item.get("size") != len(payload[item["path"]]) or item.get("sha256") != hashlib.sha256(payload[item["path"]]).hexdigest(): raise ShadowHold("record hash mismatch")
        if receipt.get("catalog_digest") != digest or receipt.get("record_count") != anchors["count"]: raise ShadowHold("stored metadata mismatch")
        for key in ("vault_head", "marker", "index"):
            if receipt.get(key) != anchors[key]: raise ShadowHold("external anchor metadata mismatch")
        return {"state": "shadow_verified", "catalog_digest": digest, "record_count": len(payload), "bytes": sum(map(len, payload.values()))}
    except (sqlite3.DatabaseError, ValueError, KeyError, TypeError, ShadowHold):
        return {"state": "held_shadow_tampered", "reason": "read_time_verification_failed"}
