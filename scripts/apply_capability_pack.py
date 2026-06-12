#!/usr/bin/env python3
"""Apply a reviewed capability pack plan into the selected Vault."""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import plan_capability_pack as planner
from deploy_capability_pack import (
    deployed_record_text,
    destination_for as deploy_destination_for,
    read,
    update_index_text,
    write,
    yaml_string,
)
from foundry_config import ROOT


BLOCKING_RECORD_OUTCOMES = {"fail", "merge_required", "update"}
BLOCKING_PAYLOAD_OUTCOMES = {"blocked_executable_install"}


def build_plan(core_root: Path, vault_root: Path, pack_root: Path):
    root_errors = planner.validate(core_root, vault_root)
    manifest, manifest_errors, manifest_text = planner.validate_manifest(core_root, vault_root, pack_root)
    records_raw, record_errors = planner.validate_records(pack_root, manifest_text) if manifest_text else ([], [])
    payloads, payload_errors = planner.validate_payloads(pack_root, manifest_text) if manifest_text else ([], [])
    records, planning_errors = planner.plan_records(vault_root, pack_root, manifest, records_raw) if manifest else ([], [])
    errors = root_errors + manifest_errors + record_errors + payload_errors + planning_errors
    if manifest and planner.same_version_hash_mismatch(vault_root, manifest, planner.manifest_hash(pack_root)):
        errors.append("same pack id and version has different manifest_sha256 in deployed-pack-index.yaml")
    return manifest, manifest_text, records_raw, records, payloads, errors


def blocking_reasons(records: list[planner.PlannedRecord], payloads: list[planner.PlannedPayload], errors: list[str]) -> list[str]:
    reasons = list(errors)
    for record in records:
        if record.outcome in BLOCKING_RECORD_OUTCOMES:
            reasons.append(f"{record.item_id}: blocking record outcome {record.outcome}")
    for payload in payloads:
        if payload.outcome in BLOCKING_PAYLOAD_OUTCOMES:
            reasons.append(f"{payload.payload_id}: blocking payload outcome {payload.outcome}")
    return reasons


def existing_pack_metadata_state(vault_root: Path, pack_id: str, manifest_sha256: str) -> str:
    path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not path.exists():
        return "absent"
    text = path.read_text(encoding="utf-8")
    if f"  - pack_id: {pack_id}" not in text:
        return "absent"
    if manifest_sha256 in text:
        return "same"
    return "different"


def record_entry_by_id(records_raw: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {entry.get("id", ""): entry for entry in records_raw if entry.get("id", "")}


def metadata_text(
    *,
    vault_root: Path,
    pack_root: Path,
    manifest: dict[str, str],
    records_raw: list[dict[str, str]],
    records: list[planner.PlannedRecord],
) -> str:
    manifest_sha = planner.manifest_hash(pack_root)
    by_id = record_entry_by_id(records_raw)
    lines = [
        f"  - pack_id: {manifest.get('pack_id', '')}",
        f"    title: {yaml_string(manifest.get('title', ''))}",
        f"    version: {yaml_string(manifest.get('version', ''))}",
        "    lifecycle_status: deployed",
        f"    distribution_type: {manifest.get('distribution_type', '')}",
        f"    deployed_at: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}",
        "    source:",
        "      kind: local_path",
        f"      locator: {yaml_string(str(pack_root))}",
        f"      manifest_sha256: {manifest_sha}",
        "      reviewed_by: architect",
        "    records:",
    ]
    if not records:
        lines.append("      []")
    for record in records:
        raw = by_id.get(record.item_id, {})
        deployed_sha = record.current_sha256
        if record.outcome == "add":
            deployed_sha = hashlib.sha256(
                deployed_record_text(record.kind, read(record.source_path), manifest).encode("utf-8")
            ).hexdigest()
        current_state = "unchanged" if record.outcome in {"add", "skip"} else "unknown"
        lines.extend(
            [
                f"      - id: {record.item_id}",
                f"        kind: {record.kind}",
                f"        path: {planner.rel(record.destination_path, vault_root)}",
                f"        imported_version: {yaml_string(raw.get('source_version', ''))}",
                f"        imported_sha256: {record.source_sha256}",
                f"        deployed_sha256: {deployed_sha}",
                f"        lifecycle_status_at_import: {raw.get('lifecycle_status', '')}",
                f"        current_state: {current_state}",
                f"        membership_role: {raw.get('membership_role', '')}",
                f"        activation_default: {raw.get('activation_default', '')}",
            ]
        )
    lines.append("    executable_payloads: []")
    lines.append("    decisions:")
    lines.append("      conflict_policy: fail_closed")
    lines.append("      notes: []")
    return "\n".join(lines) + "\n"


def update_deployed_pack_index(
    vault_root: Path,
    pack_root: Path,
    manifest: dict[str, str],
    records_raw: list[dict[str, str]],
    records: list[planner.PlannedRecord],
    apply: bool,
) -> None:
    path = vault_root / "packs" / "deployed-pack-index.yaml"
    state = existing_pack_metadata_state(vault_root, manifest.get("pack_id", ""), planner.manifest_hash(pack_root))
    if state == "same":
        print(f"pack metadata already present: {manifest.get('pack_id', '')}")
        return
    if state == "different":
        raise SystemExit("Refusing to overwrite existing pack metadata with a different manifest hash; use #101 update flow")
    if path.exists():
        text = path.read_text(encoding="utf-8").rstrip() + "\n" + metadata_text(
            vault_root=vault_root,
            pack_root=pack_root,
            manifest=manifest,
            records_raw=records_raw,
            records=records,
        )
    else:
        today = datetime.now(timezone.utc).date().isoformat()
        text = "\n".join(["schema_version: 1", f"updated: {today}", "deployed_packs:"]) + "\n" + metadata_text(
            vault_root=vault_root,
            pack_root=pack_root,
            manifest=manifest,
            records_raw=records_raw,
            records=records,
        )
    write(path, text, apply)


def apply_records(vault_root: Path, manifest: dict[str, str], records: list[planner.PlannedRecord], apply: bool) -> None:
    added = [record for record in records if record.outcome == "add" and record.import_action != "stage_only"]
    for record in added:
        text = deployed_record_text(record.kind, read(record.source_path), manifest)
        write(record.destination_path, text, apply)

    practice_adds = []
    asset_adds = []
    for record in added:
        destination_path, index_entry, errors = deploy_destination_for(vault_root, record.kind, record.source_path)
        if errors:
            raise SystemExit("; ".join(errors))
        if destination_path != record.destination_path:
            raise SystemExit(f"{record.item_id}: destination changed during apply planning")
        if record.kind == "practice":
            practice_adds.append(index_entry)
        elif record.kind == "asset":
            asset_adds.append(index_entry)

    if practice_adds:
        index_path = vault_root / "indexes" / "practice_index.yaml"
        fake_records = [
            type("IndexRecord", (), {"kind": "practice", "index_entry": entry, "item_id": entry["id"]})()
            for entry in practice_adds
        ]
        write(index_path, update_index_text(read(index_path), "practice", fake_records), apply)
    if asset_adds:
        index_path = vault_root / "indexes" / "asset_index.yaml"
        fake_records = [
            type("IndexRecord", (), {"kind": "asset", "index_entry": entry, "item_id": entry["id"]})()
            for entry in asset_adds
        ]
        write(index_path, update_index_text(read(index_path), "asset", fake_records), apply)


def apply_pack(core_root: Path, vault_root: Path, pack_root: Path, apply: bool) -> int:
    manifest, _manifest_text, records_raw, records, payloads, errors = build_plan(core_root, vault_root, pack_root)
    planner.print_plan(pack_root, vault_root, manifest, records, payloads, errors)
    blockers = blocking_reasons(records, payloads, errors)
    if blockers:
        print("Apply refused:")
        for reason in blockers:
            print(f"- {reason}")
        return 1
    if not manifest:
        print("Apply refused: manifest unavailable")
        return 1
    metadata_state = existing_pack_metadata_state(vault_root, manifest.get("pack_id", ""), planner.manifest_hash(pack_root))
    if metadata_state == "different":
        print("Apply refused:")
        print("- existing pack metadata has a different manifest hash; use #101 update flow")
        return 1

    apply_records(vault_root, manifest, records, apply)
    update_deployed_pack_index(vault_root, pack_root, manifest, records_raw, records, apply)
    print("Apply summary:")
    print(f"added: {sum(1 for record in records if record.outcome == 'add')}")
    print(f"skipped: {sum(1 for record in records if record.outcome == 'skip')}")
    print(f"stage_only: {sum(1 for record in records if record.outcome == 'stage_only')}")
    print(f"metadata: {'written' if apply else 'would write'}")
    if not apply:
        print("Dry-run only. Re-run with --apply to write Vault records and pack metadata.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a reviewed capability pack plan into the selected Vault.")
    parser.add_argument("pack_root", help="Capability pack directory containing manifest.yaml.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    parser.add_argument("--apply", action="store_true", help="Write Vault records and pack metadata. Default is dry-run.")
    args = parser.parse_args()
    return apply_pack(
        Path(args.core_root).expanduser().resolve(),
        Path(args.vault_root).expanduser().resolve(),
        Path(args.pack_root).expanduser().resolve(),
        args.apply,
    )


if __name__ == "__main__":
    sys.exit(main())
