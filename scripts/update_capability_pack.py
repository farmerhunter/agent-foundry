#!/usr/bin/env python3
"""Apply or restore one reviewed capability-pack update without overwriting local edits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import apply_capability_pack as apply_pack
import compare_capability_pack_update as compare
import plan_capability_pack as planner
from deploy_capability_pack import (
    deployed_record_text,
    deployment_status,
    destination_for,
    read,
    update_index_text,
)
from foundry_config import ROOT
from manage_capability_pack_lifecycle import pack_block_bounds


RECEIPT_NAME = "receipt.json"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def safe_target(vault_root: Path, relative: str) -> Path:
    candidate = (vault_root / relative).resolve()
    try:
        candidate.relative_to(vault_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"Refusing receipt path outside selected Vault: {relative}") from exc
    return candidate


def vault_relative(vault_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(vault_root.resolve()))
    except ValueError as exc:
        raise SystemExit(f"Refusing update path outside selected Vault: {path}") from exc


def set_index_status(text: str, item_id: str, status: str) -> str:
    lines = text.splitlines()
    in_entry = False
    for index, line in enumerate(lines):
        if line.startswith("  - id: "):
            in_entry = line.split(":", 1)[1].strip().strip('"') == item_id
            continue
        if in_entry and line.startswith("    status:"):
            lines[index] = f"    status: {status}"
            return "\n".join(lines).rstrip() + "\n"
    raise SystemExit(f"Index entry missing status for {item_id}")


def replace_pack_metadata(current: str, pack_id: str, replacement: str) -> str:
    lines = current.splitlines()
    start, end = pack_block_bounds(lines, pack_id)
    if start < 0:
        raise SystemExit(f"Deployed pack metadata missing for {pack_id}")
    updated = [*lines[:start], *replacement.rstrip().splitlines(), *lines[end:]]
    return "\n".join(updated).rstrip() + "\n"


def planned_writes(
    vault_root: Path,
    pack_root: Path,
    manifest: dict[str, str],
    records_raw: list[dict[str, str]],
    records: list[planner.PlannedRecord],
) -> dict[Path, bytes]:
    writes: dict[Path, bytes] = {}
    by_id = apply_pack.record_entry_by_id(records_raw)
    added_by_kind: dict[str, list[object]] = {"practice": [], "asset": []}
    status_updates: dict[str, list[tuple[str, str]]] = {"practice": [], "asset": []}

    for record in records:
        if record.outcome not in {"add", "update"} or record.import_action == "stage_only":
            continue
        raw = by_id[record.item_id]
        activation_default = raw.get("activation_default", "")
        text = deployed_record_text(
            record.kind,
            read(record.source_path),
            manifest,
            activation_default,
        )
        writes[record.destination_path] = text.encode("utf-8")
        destination_path, index_entry, errors = destination_for(vault_root, record.kind, record.source_path)
        if errors:
            raise SystemExit("; ".join(errors))
        if destination_path != record.destination_path:
            raise SystemExit(f"{record.item_id}: destination changed during update planning")
        target_status = deployment_status(index_entry.get("status", ""), activation_default)
        index_entry["status"] = target_status
        if record.outcome == "add":
            added_by_kind[record.kind].append(
                type("IndexRecord", (), {"kind": record.kind, "index_entry": index_entry, "item_id": record.item_id})()
            )
        else:
            status_updates[record.kind].append((record.item_id, target_status))

    for kind, filename in [("practice", "practice_index.yaml"), ("asset", "asset_index.yaml")]:
        index_path = vault_root / "indexes" / filename
        text = read(index_path)
        if added_by_kind[kind]:
            text = update_index_text(text, kind, added_by_kind[kind])
        for item_id, status in status_updates[kind]:
            text = set_index_status(text, item_id, status)
        if text != read(index_path):
            writes[index_path] = text.encode("utf-8")

    metadata_path = vault_root / "packs" / "deployed-pack-index.yaml"
    replacement = apply_pack.metadata_text(
        vault_root=vault_root,
        pack_root=pack_root,
        manifest=manifest,
        records_raw=records_raw,
        records=records,
    )
    writes[metadata_path] = replace_pack_metadata(
        read(metadata_path), manifest.get("pack_id", ""), replacement
    ).encode("utf-8")
    return writes


def atomic_write(path: Path, data: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.af-pack-{os.getpid()}")
    try:
        temporary.write_bytes(data)
        os.chmod(temporary, mode if mode is not None else (path.stat().st_mode & 0o777 if path.exists() else 0o644))
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_backup(
    backup_root: Path,
    vault_root: Path,
    pack_id: str,
    from_version: str,
    to_version: str,
    writes: dict[Path, bytes],
) -> tuple[dict[str, object], dict[Path, bytes | None]]:
    if not backup_root.is_absolute():
        raise SystemExit("--backup-root must be an absolute path")
    if backup_root.exists():
        raise SystemExit(f"Backup root already exists: {backup_root}")
    if not backup_root.parent.exists():
        raise SystemExit(f"Backup parent does not exist: {backup_root.parent}")
    backup_root.mkdir(mode=0o700)
    preimages: dict[Path, bytes | None] = {}
    entries: list[dict[str, object]] = []
    for target in sorted(writes, key=lambda item: vault_relative(vault_root, item)):
        relative = vault_relative(vault_root, target)
        preimage = target.read_bytes() if target.exists() else None
        preimages[target] = preimage
        backup_relative = f"files/{relative}" if preimage is not None else ""
        if preimage is not None:
            backup_path = backup_root / backup_relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(backup_path.parent, 0o700)
            backup_path.write_bytes(preimage)
            os.chmod(backup_path, 0o600)
        entries.append(
            {
                "path": relative,
                "preimage_exists": preimage is not None,
                "preimage_sha256": digest_bytes(preimage) if preimage is not None else None,
                "postimage_sha256": digest_bytes(writes[target]),
                "backup_path": backup_relative,
            }
        )
    receipt: dict[str, object] = {
        "schema_version": 1,
        "operation": "capability_pack_update",
        "pack_id": pack_id,
        "from_version": from_version,
        "to_version": to_version,
        "vault_marker_sha256": digest_path(vault_root / ".agent-foundry-vault.yaml"),
        "files": entries,
    }
    receipt_path = backup_root / RECEIPT_NAME
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(receipt_path, 0o600)
    return receipt, preimages


def restore_preimages(preimages: dict[Path, bytes | None]) -> None:
    for path, preimage in reversed(list(preimages.items())):
        if preimage is None:
            if path.exists():
                path.unlink()
        else:
            atomic_write(path, preimage)


def apply_update(
    core_root: Path,
    vault_root: Path,
    pack_root: Path,
    backup_root: Path | None,
    apply: bool,
) -> int:
    manifest, _manifest_text, records_raw, records, payloads, errors = apply_pack.build_plan(
        core_root, vault_root, pack_root
    )
    planner.print_plan(pack_root, vault_root, manifest, records, payloads, errors)
    if not manifest:
        print("status: failed")
        return 1
    pack_id = manifest.get("pack_id", "")
    deployed, metadata_error = compare.deployed_pack_metadata(vault_root, pack_id)
    if metadata_error or not deployed:
        print("status: failed")
        print(f"detail: {metadata_error or 'pack is not deployed; use the fresh apply path'}")
        return 1
    current_version = str(deployed.get("version", ""))
    available_version = manifest.get("version", "")
    if compare.compare_versions(current_version, available_version) != "newer":
        print("status: failed")
        print(f"detail: update requires a newer version; deployed={current_version} available={available_version}")
        return 1
    blockers = list(errors)
    blockers.extend(
        f"{record.item_id}: {record.outcome}"
        for record in records
        if record.outcome in {"fail", "merge_required"}
    )
    blockers.extend(
        f"{payload.payload_id}: {payload.outcome}"
        for payload in payloads
        if payload.outcome == "blocked_executable_install"
    )
    if blockers:
        print("status: merge_required" if any("merge_required" in item for item in blockers) else "status: failed")
        for blocker in blockers:
            print(f"- {blocker}")
        print("writes: none")
        return 1
    writes = planned_writes(vault_root, pack_root, manifest, records_raw, records)
    print(f"from_version: {current_version}")
    print(f"to_version: {available_version}")
    print(f"touched_files: {len(writes)}")
    if not apply:
        print("status: update_ready")
        print("writes: none")
        return 0
    if backup_root is None:
        print("status: failed")
        print("detail: --backup-root is required with --apply")
        print("writes: none")
        return 1
    _receipt, preimages = create_backup(
        backup_root, vault_root, pack_id, current_version, available_version, writes
    )
    try:
        for path, data in writes.items():
            atomic_write(path, data)
    except Exception:
        restore_preimages(preimages)
        raise
    for path, data in writes.items():
        if not path.exists() or digest_path(path) != digest_bytes(data):
            restore_preimages(preimages)
            raise SystemExit(f"Post-update readback failed; restored preimages: {path}")
    print("status: updated")
    print(f"backup_receipt: {backup_root / RECEIPT_NAME}")
    print("activation: unchanged; optional manual-review members are proposed")
    return 0


def restore_update(vault_root: Path, backup_root: Path, apply: bool) -> int:
    receipt_path = backup_root / RECEIPT_NAME
    if not receipt_path.exists():
        print("status: failed")
        print(f"detail: receipt missing: {receipt_path}")
        return 1
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != 1 or receipt.get("operation") != "capability_pack_update":
        print("status: failed")
        print("detail: unsupported backup receipt")
        return 1
    marker_path = vault_root / ".agent-foundry-vault.yaml"
    if not marker_path.exists() or digest_path(marker_path) != receipt.get("vault_marker_sha256"):
        print("status: restore_blocked")
        print("- selected Vault marker does not match the update receipt")
        print("writes: none")
        return 1
    entries = receipt.get("files", [])
    if not isinstance(entries, list):
        print("status: failed")
        print("detail: receipt files must be a list")
        return 1
    planned: list[tuple[Path, bytes | None]] = []
    errors: list[str] = []
    for raw in entries:
        if not isinstance(raw, dict):
            errors.append("receipt contains a non-mapping file entry")
            continue
        relative = str(raw.get("path", ""))
        target = safe_target(vault_root, relative)
        expected_post = str(raw.get("postimage_sha256", ""))
        current = digest_path(target) if target.exists() else ""
        if current != expected_post:
            errors.append(f"{relative}: current postimage drifted")
            continue
        preimage: bytes | None = None
        if raw.get("preimage_exists") is True:
            backup_relative = str(raw.get("backup_path", ""))
            backup_path = (backup_root / backup_relative).resolve()
            try:
                backup_path.relative_to(backup_root.resolve())
            except ValueError:
                errors.append(f"{relative}: backup path escapes backup root")
                continue
            if not backup_path.exists():
                errors.append(f"{relative}: backup preimage missing")
                continue
            preimage = backup_path.read_bytes()
            if digest_bytes(preimage) != raw.get("preimage_sha256"):
                errors.append(f"{relative}: backup preimage hash mismatch")
                continue
        planned.append((target, preimage))
    if errors:
        print("status: restore_blocked")
        for error in errors:
            print(f"- {error}")
        print("writes: none")
        return 1
    print(f"pack_id: {receipt.get('pack_id', '')}")
    print(f"restore_from_version: {receipt.get('to_version', '')}")
    print(f"restore_to_version: {receipt.get('from_version', '')}")
    print(f"touched_files: {len(planned)}")
    if not apply:
        print("status: restore_ready")
        print("writes: none")
        return 0
    for target, preimage in planned:
        if preimage is None:
            target.unlink()
        else:
            atomic_write(target, preimage)
    for target, preimage in planned:
        if preimage is None and target.exists():
            raise SystemExit(f"Restore readback failed: {target} should be absent")
        if preimage is not None and digest_path(target) != digest_bytes(preimage):
            raise SystemExit(f"Restore readback failed: {target}")
    print("status: restored")
    print(f"backup_retained: {backup_root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack_root", nargs="?", help="Newer capability pack directory.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    parser.add_argument("--backup-root", help="Fresh absolute backup directory required for update apply.")
    parser.add_argument("--restore", help="Backup directory containing receipt.json to restore.")
    parser.add_argument("--apply", action="store_true", help="Write the reviewed update or restore. Default is dry-run.")
    args = parser.parse_args()
    vault_root = Path(args.vault_root).expanduser().resolve()
    if args.restore:
        if args.pack_root or args.backup_root:
            parser.error("--restore cannot be combined with pack_root or --backup-root")
        return restore_update(vault_root, Path(args.restore).expanduser().resolve(), args.apply)
    if not args.pack_root:
        parser.error("pack_root is required unless --restore is used")
    return apply_update(
        Path(args.core_root).expanduser().resolve(),
        vault_root,
        Path(args.pack_root).expanduser().resolve(),
        Path(args.backup_root).expanduser() if args.backup_root else None,
        args.apply,
    )


if __name__ == "__main__":
    sys.exit(main())
