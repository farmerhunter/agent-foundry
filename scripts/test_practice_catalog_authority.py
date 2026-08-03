#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from practice_catalog_authority import *


def main() -> int:
    errors: list[str] = []
    def ok(name: str, condition: bool) -> None:
        print(f"{name}: {'ok' if condition else 'FAIL'}")
        if not condition: errors.append(name)
    default = authority_readout()
    ok("default-working-tree", default["mode"] == WORKING_TREE and default["holds"] == [])
    held = authority_readout(SNAPSHOT)
    ok("backend-unavailable-held", held["mode"] == HELD and held["holds"] == ["held_backend_unavailable"])
    backend = SyntheticAuthorityBackend("sqlite-pointer-v1", 3, "a" * 64)
    ready = authority_readout(SNAPSHOT, backend)
    ok("trusted-snapshot", ready["mode"] == SNAPSHOT and ready["generation"] == 3 and "Synthetic" not in str(ready))
    for name, kwargs, hold in [("dirty", {"vault_dirty": True}, "dirty_vault"), ("drift", {"marker_drift": True}, "marker_path_hash_drift"), ("replica", {"replica_drift": True}, "replica_drift"), ("migration", {"migration": "partial"}, "legacy_or_partial_migration")]:
        result = authority_readout(SNAPSHOT, backend, **kwargs)
        ok(name, result["mode"] == HELD and hold in result["holds"])
    for name, kwargs, hold in [("missing-snapshot", {"expected_snapshot_hash": "b" * 64}, "snapshot_hash_mismatch"), ("backup-failure", {"backup": "failed"}, "backup_failed"), ("rollback-pending", {"rollback": "pending"}, "rollback_pending"), ("receipt-failure", {"receipt": "failed"}, "receipt_verification_failed"), ("write-operation", {"operations": ("write",)}, "write_operation_forbidden")]:
        result = authority_readout(SNAPSHOT, backend, **kwargs)
        ok(name, result["mode"] == HELD and hold in result["holds"])
    for value in (-1, True, "1", None):
        invalid_generation = authority_readout(SNAPSHOT, SyntheticAuthorityBackend("v", value, "a" * 64))
        ok(f"invalid-generation-{value!r}", invalid_generation["mode"] == HELD and "held_backend_untrusted" in invalid_generation["holds"])
    forged = authority_readout(SNAPSHOT, object())
    ok("untrusted-held", forged["mode"] == HELD)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
