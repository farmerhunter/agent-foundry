#!/usr/bin/env python3
"""Compare an available capability pack snapshot with selected Vault state."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import plan_capability_pack as planner
from foundry_config import ROOT


def pack_block(vault_root: Path, pack_id: str) -> str:
    path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    capture = False
    captured: list[str] = []
    for line in lines:
        if line.startswith("  - pack_id:"):
            if capture:
                break
            capture = line.split(":", 1)[1].strip().strip('"') == pack_id
        if capture:
            captured.append(line)
    return "\n".join(captured)


def block_scalar(block: str, key: str) -> str:
    match = re.search(rf"^\s+{re.escape(key)}:\s*\"?([^\"\n]+)\"?", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def compare_versions(current: str, available: str) -> str:
    def parts(value: str) -> tuple[int, ...]:
        raw = value.split("-", 1)[0]
        parsed: list[int] = []
        for part in raw.split("."):
            try:
                parsed.append(int(part))
            except ValueError:
                parsed.append(0)
        return tuple(parsed)

    current_parts = parts(current)
    available_parts = parts(available)
    if available_parts > current_parts:
        return "newer"
    if available_parts == current_parts:
        return "same"
    return "older"


def compare(core_root: Path, vault_root: Path, pack_root: Path) -> int:
    root_errors = planner.validate(core_root, vault_root)
    manifest, manifest_errors, manifest_text = planner.validate_manifest(core_root, vault_root, pack_root)
    records_raw, record_errors = planner.validate_records(pack_root, manifest_text) if manifest_text else ([], [])
    payloads, payload_errors = planner.validate_payloads(pack_root, manifest_text) if manifest_text else ([], [])
    records, planning_errors = planner.plan_records(vault_root, pack_root, manifest, records_raw) if manifest else ([], [])
    errors = root_errors + manifest_errors + record_errors + payload_errors + planning_errors

    print("Capability pack update comparison")
    print(f"pack_root: {pack_root}")
    print(f"vault_root: {vault_root}")
    if manifest:
        print(f"pack_id: {manifest.get('pack_id', '')}")
        print(f"available_version: {manifest.get('version', '')}")
        print(f"available_manifest_sha256: {planner.manifest_hash(pack_root)}")

    if errors:
        print("status: failed")
        for error in errors:
            print(f"- {error}")
        print("writes: none")
        return 1

    block = pack_block(vault_root, manifest.get("pack_id", ""))
    if not block:
        print("status: not_deployed")
        print("detail: use optional pack apply before update comparison")
        print("writes: none")
        return 1

    current_version = block_scalar(block, "version")
    current_manifest_sha = block_scalar(block, "manifest_sha256")
    available_manifest_sha = planner.manifest_hash(pack_root)
    relation = compare_versions(current_version, manifest.get("version", ""))
    print(f"current_version: {current_version}")
    print(f"current_manifest_sha256: {current_manifest_sha}")
    print(f"version_relation: {relation}")

    if relation == "same" and current_manifest_sha == available_manifest_sha:
        print("status: unchanged")
        print("writes: none")
        return 0
    if relation == "same" and current_manifest_sha != available_manifest_sha:
        print("status: failed")
        print("detail: same pack id and version has different manifest_sha256")
        print("writes: none")
        return 1
    if relation == "older":
        print("status: failed")
        print("detail: available pack version is older than deployed version; downgrade is unsupported")
        print("writes: none")
        return 1

    counts: dict[str, int] = {
        "clean_update": 0,
        "merge_required": 0,
        "add": 0,
        "skip": 0,
        "stage_only": 0,
        "fail": 0,
        "blocked_executable_install": 0,
    }
    print("records:")
    for record in records:
        if record.outcome == "update":
            outcome = "clean_update"
        else:
            outcome = record.outcome
        counts[outcome] = counts.get(outcome, 0) + 1
        print(f"- {record.item_id} {outcome}: {record.detail}")
    print("executable_payloads:")
    if not payloads:
        print("- none")
    for payload in payloads:
        counts[payload.outcome] = counts.get(payload.outcome, 0) + 1
        print(f"- {payload.payload_id} {payload.outcome}: {payload.detail}")
    print("summary:")
    for key in [
        "clean_update",
        "merge_required",
        "add",
        "skip",
        "stage_only",
        "fail",
        "blocked_executable_install",
    ]:
        print(f"{key}: {counts.get(key, 0)}")
    if counts.get("fail", 0):
        print("status: failed")
        print("writes: none")
        return 1
    if counts.get("blocked_executable_install", 0):
        print("status: blocked_executable_install")
        print("writes: none")
        return 1
    if counts.get("merge_required", 0):
        print("status: merge_required")
    elif counts.get("clean_update", 0) or counts.get("add", 0):
        print("status: clean_update_available")
    else:
        print("status: review_only")
    print("writes: none")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare an available capability pack snapshot with selected Vault state.")
    parser.add_argument("pack_root", help="Capability pack directory containing manifest.yaml.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    args = parser.parse_args()
    return compare(
        Path(args.core_root).expanduser().resolve(),
        Path(args.vault_root).expanduser().resolve(),
        Path(args.pack_root).expanduser().resolve(),
    )


if __name__ == "__main__":
    sys.exit(main())
