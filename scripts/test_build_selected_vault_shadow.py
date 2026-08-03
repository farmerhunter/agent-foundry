#!/usr/bin/env python3
from __future__ import annotations
import tempfile, json, hashlib, sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_selected_vault_shadow import ShadowHold, build_shadow, verify_shadow, _digest, validate_cli_roots

def main() -> int:
    records={"practices/synthetic/SYN-001.md": b"synthetic one", "practices/synthetic/SYN-002.md": b"synthetic two"}
    errors=[]
    with tempfile.TemporaryDirectory(prefix="cli-") as temp:
        selected=Path(temp)/"selected-vault-mock"; selected.mkdir()
        validate_cli_roots(selected, Path(temp)/"agent-foundry-selected-vault-shadow")
        try: validate_cli_roots(selected, Path(temp)/"wrong-shadow"); errors.append("root-injection")
        except ShadowHold: pass
    with tempfile.TemporaryDirectory(prefix="shadow-test-") as temp:
        out=Path(temp)/"shadow"
        result=build_shadow("synthetic-anchor-001", records, out)
        if result["state"] != "retained_pending_human_disposal" or result["pointer_cas"] or not result["privacy_safe"]: errors.append("metadata")
        if out.stat().st_mode & 0o777 != 0o700 or (out/"shadow.sqlite3").stat().st_mode & 0o777 != 0o600: errors.append("permissions")
        if verify_shadow(out)["state"] != "held_shadow_tampered": errors.append("pre-validator-tamper-hold")
        complete={f"practices/synthetic/SYN-{i:03d}.md": (b"x" * (5038 + (42 if i == 64 else 0))) for i in range(1,65)}
        valid_root=Path(temp)/"valid"
        build_shadow("synthetic-anchor-001", complete, valid_root)
        if verify_shadow(valid_root)["state"] != "shadow_verified": errors.append("intact-fixed-anchor-fixture")
        for label in ("marker", "vault_head", "index", "count", "bytes", "catalog", "receipt", "path", "size", "sha", "payload", "delete", "add"):
            case_root = Path(temp) / f"case-{label}"; build_shadow("synthetic-anchor-001", complete, case_root)
            db=sqlite3.connect(str(case_root/"shadow.sqlite3")); before=db.execute("SELECT marker,vault_head,index_hash,total_bytes,catalog_digest,record_count,receipt FROM catalog_metadata").fetchone()
            if label == "marker": db.execute("UPDATE catalog_metadata SET marker='x'")
            elif label == "vault_head": db.execute("UPDATE catalog_metadata SET vault_head='x'")
            elif label == "index": db.execute("UPDATE catalog_metadata SET index_hash='x'")
            elif label == "count": db.execute("UPDATE catalog_metadata SET record_count=1")
            elif label == "bytes": db.execute("UPDATE catalog_metadata SET total_bytes=1")
            elif label == "catalog": db.execute("UPDATE catalog_metadata SET catalog_digest='0'*64")
            elif label == "receipt": db.execute("UPDATE catalog_metadata SET receipt='tampered'")
            elif label == "delete": db.execute("DELETE FROM shadow_records WHERE path='practices/synthetic/SYN-001.md'")
            elif label == "add": db.execute("INSERT INTO shadow_records VALUES('practices/synthetic/SYN-999.md',1,'0'*64,X'78')")
            elif label == "path": db.execute("UPDATE shadow_records SET path='practices/synthetic/SYN-999.md' WHERE path='practices/synthetic/SYN-001.md'")
            elif label == "size": db.execute("UPDATE shadow_records SET size=999 WHERE path='practices/synthetic/SYN-001.md'")
            elif label == "sha": db.execute("UPDATE shadow_records SET sha256='0'*64 WHERE path='practices/synthetic/SYN-001.md'")
            elif label == "payload": db.execute("UPDATE shadow_records SET payload=X'79' WHERE path='practices/synthetic/SYN-001.md'")
            db.commit(); after=db.execute("SELECT marker,vault_head,index_hash,total_bytes,catalog_digest,record_count,receipt FROM catalog_metadata").fetchone()
            if label in {"marker","vault_head","index","count","bytes","catalog","receipt"} and after == before: errors.append(f"{label}-field-not-changed")
            db.close()
            if verify_shadow(case_root)["state"] != "held_shadow_tampered": errors.append(f"{label}-tamper-not-held")
        db.close()
        for name, kwargs in [("drift", {"validator_digest":"0"*64}), ("privacy", {"privacy_safe":False}), ("size", {"max_bytes":1}), ("incomplete", {"records":{}}), ("anchor", {"anchor":"real-vault"})]:
            try: build_shadow(kwargs.pop("anchor", "synthetic-anchor-001"), kwargs.pop("records", records), Path(temp)/name, **kwargs); errors.append(name)
            except ShadowHold: pass
    print("shadow tests passed." if not errors else f"failed: {errors}")
    return 1 if errors else 0
if __name__ == "__main__": raise SystemExit(main())
