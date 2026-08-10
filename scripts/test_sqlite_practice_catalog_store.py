#!/usr/bin/env python3
from __future__ import annotations
import hashlib, tempfile
from pathlib import Path
from sqlite_practice_catalog_store import SQLitePracticeCatalogStore
from practice_catalog_snapshot import ValidationFailure

def main() -> int:
    errors=[]
    with tempfile.TemporaryDirectory(prefix="synthetic-catalog-") as root:
        path=Path(root)/"catalog.sqlite3"; store=SQLitePracticeCatalogStore(path,root)
        manifest="synthetic-manifest"; digest=hashlib.sha256(manifest.encode()).hexdigest(); blobs={"practices/synthetic/SYN-001.md": b"synthetic"}
        committed=store.commit(0,digest,manifest,"synthetic-index",blobs,"tx-1")
        if committed["state"] != "committed": errors.append("commit")
        if store.commit(0,digest,manifest,"synthetic-index",blobs,"tx-1")["state"] != "committed_idempotent": errors.append("idempotency")
        backup=store.backup_receipt()
        store.close(); reopened=SQLitePracticeCatalogStore(path,root)
        if reopened.read_catalog()["snapshot_hash"] != digest: errors.append("restart")
        if reopened.commit(0,digest,manifest,"synthetic-index",blobs,"tx-2")["state"] != "held_cas_conflict": errors.append("cas")
        if reopened.restore_receipt(backup)["operation"] != "restore": errors.append("restore")
        if reopened.rollback(1, digest, None)["state"] != "held_rollback_authorization_missing": errors.append("rollback-auth")
        if reopened.rollback(1, digest, "synthetic-auth")["state"] != "committed": errors.append("rollback")
        try: reopened.restore_receipt(backup); errors.append("stale-backup-accepted")
        except ValidationFailure: pass
        reopened._db.execute("DELETE FROM snapshots WHERE hash=?", (digest,)); reopened._db.commit()
        try: reopened.read_catalog(); errors.append("missing-blob-accepted")
        except ValidationFailure: pass
        reopened._db.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (digest, manifest, "synthetic-index", '{"practices/synthetic/SYN-001.md":"73796e746865746963"}')); reopened._db.commit()
        reopened._db.execute("UPDATE snapshots SET blobs=? WHERE hash=?", ("{\"practices/synthetic/SYN-001.md\":\"zz\"}", digest)); reopened._db.commit()
        try: reopened.read_catalog(); errors.append("corrupt-payload-accepted")
        except (ValidationFailure, ValueError): pass
        reopened._db.execute("UPDATE pointer SET generation=-1 WHERE slot=1"); reopened._db.commit()
        try: reopened.read_pointer(); errors.append("generation-corruption-accepted")
        except ValidationFailure: pass
        if reopened.retention_receipt({digest})["removed_hashes"]: errors.append("retention")
        reopened.close()
    try:
        SQLitePracticeCatalogStore(Path("/tmp/escape.sqlite3"), root)
        errors.append("escape")
    except (ValidationFailure, NameError): pass
    print("SQLite catalog store tests passed." if not errors else f"failed: {errors}")
    return 1 if errors else 0
if __name__ == "__main__": raise SystemExit(main())
