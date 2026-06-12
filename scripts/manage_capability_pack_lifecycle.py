#!/usr/bin/env python3
"""Plan or apply disable/retire lifecycle transitions for deployed packs."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from check_foundry_roots import validate
from foundry_config import ROOT


PRACTICE_RETIRE_STATUS = "archived"
ASSET_RETIRE_STATUS = "retired"


@dataclass(frozen=True)
class PackRecord:
    item_id: str
    kind: str
    path: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str, apply: bool) -> None:
    print(f"{'write' if apply else 'would write'}: {path}")
    if apply:
        path.write_text(text, encoding="utf-8")


def safe_vault_path(vault_root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute():
        raise SystemExit(f"Refusing absolute Vault record path: {relative}")
    target = (vault_root / rel).resolve()
    try:
        target.relative_to(vault_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"Refusing Vault record path outside Vault: {relative}") from exc
    return target


def pack_block_bounds(lines: list[str], pack_id: str) -> tuple[int, int]:
    start = -1
    for index, line in enumerate(lines):
        if line.startswith("  - pack_id:") and line.split(":", 1)[1].strip().strip('"') == pack_id:
            start = index
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("  - pack_id:"):
            end = index
            break
    return start, end


def deployed_pack_records(vault_root: Path, pack_id: str) -> tuple[list[PackRecord], list[str], int, int]:
    metadata_path = vault_root / "packs" / "deployed-pack-index.yaml"
    if not metadata_path.exists():
        return [], [], -1, -1
    lines = metadata_path.read_text(encoding="utf-8").splitlines()
    start, end = pack_block_bounds(lines, pack_id)
    if start == -1:
        return [], lines, -1, -1
    records: list[PackRecord] = []
    in_records = False
    current: dict[str, str] | None = None
    for raw in lines[start:end]:
        stripped = raw.strip()
        if raw.startswith("    records:"):
            in_records = True
            continue
        if in_records and raw.startswith("    ") and not raw.startswith("      "):
            if current and current.get("id"):
                records.append(PackRecord(current["id"], current.get("kind", ""), current.get("path", "")))
            current = None
            if stripped and not stripped.startswith("- "):
                in_records = False
            continue
        if in_records and raw.startswith("      - "):
            if current and current.get("id"):
                records.append(PackRecord(current["id"], current.get("kind", ""), current.get("path", "")))
            current = {}
            item = stripped[2:].strip()
            if ":" in item:
                key, value = item.split(":", 1)
                current[key.strip()] = value.strip().strip('"')
            continue
        if in_records and current is not None and raw.startswith("        ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = value.strip().strip('"')
    if current and current.get("id"):
        records.append(PackRecord(current["id"], current.get("kind", ""), current.get("path", "")))
    return records, lines, start, end


def set_markdown_frontmatter_status(text: str, status: str) -> str:
    if not text.startswith("---\n"):
        raise SystemExit("Practice record missing frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise SystemExit("Practice record frontmatter is malformed")
    prefix = text[:end]
    suffix = text[end:]
    lines = prefix.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("status:"):
            lines[index] = f"status: {status}"
            return "\n".join(lines) + suffix
    raise SystemExit("Practice record frontmatter missing status")


def set_yaml_status(text: str, status: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("status:"):
            lines[index] = f"status: {status}"
            return "\n".join(lines).rstrip() + "\n"
    raise SystemExit("Asset record missing status")


def set_index_status(text: str, item_id: str, status: str) -> str:
    lines = text.splitlines()
    in_entry = False
    found = False
    for index, line in enumerate(lines):
        if line.startswith("  - id: "):
            in_entry = line.split(":", 1)[1].strip().strip('"') == item_id
            found = found or in_entry
            continue
        if in_entry and line.startswith("    status:"):
            lines[index] = f"    status: {status}"
            return "\n".join(lines).rstrip() + "\n"
    if not found:
        raise SystemExit(f"Index entry not found for {item_id}")
    raise SystemExit(f"Index entry missing status for {item_id}")


def update_metadata(lines: list[str], start: int, end: int, action: str, state_by_id: dict[str, str]) -> str:
    updated = list(lines)
    current_record = ""
    for index in range(start, end):
        stripped = updated[index].strip()
        if updated[index].startswith("    lifecycle_status:"):
            updated[index] = f"    lifecycle_status: {action}d" if action == "disable" else "    lifecycle_status: retired"
            continue
        if updated[index].startswith("      - id:"):
            current_record = stripped.split(":", 1)[1].strip().strip('"')
            continue
        if current_record and updated[index].startswith("        current_state:") and current_record in state_by_id:
            updated[index] = f"        current_state: {state_by_id[current_record]}"
    return "\n".join(updated).rstrip() + "\n"


def retire_status(kind: str) -> tuple[str, str]:
    if kind == "practice":
        return PRACTICE_RETIRE_STATUS, "archived"
    if kind == "asset":
        return ASSET_RETIRE_STATUS, "retired"
    raise SystemExit(f"Unsupported pack record kind: {kind}")


def lifecycle(core_root: Path, vault_root: Path, pack_id: str, action: str, apply: bool) -> int:
    errors = validate(core_root, vault_root)
    if errors:
        print("Pack lifecycle refused:")
        for error in errors:
            print(f"- {error}")
        print("writes: none")
        return 1

    records, metadata_lines, start, end = deployed_pack_records(vault_root, pack_id)
    metadata_path = vault_root / "packs" / "deployed-pack-index.yaml"
    print("Capability pack lifecycle report")
    print(f"pack_id: {pack_id}")
    print(f"action: {action}")
    print(f"vault_root: {vault_root}")
    print(f"metadata: {metadata_path}")
    if start == -1:
        print("status: not_deployed")
        print("writes: none")
        return 1
    print("records:")
    if not records:
        print("- none")

    state_by_id: dict[str, str] = {}
    for record in records:
        path = safe_vault_path(vault_root, record.path)
        if not path.exists():
            print(f"- {record.item_id} missing: {record.path}")
            state_by_id[record.item_id] = "missing"
            continue
        if action == "disable":
            print(f"- {record.item_id} metadata_only: {record.path}")
            state_by_id[record.item_id] = "unchanged"
            continue
        status, state = retire_status(record.kind)
        print(f"- {record.item_id} {record.kind} -> {status}: {record.path}")
        text = read(path)
        updated = set_markdown_frontmatter_status(text, status) if record.kind == "practice" else set_yaml_status(text, status)
        if updated != text:
            write(path, updated, apply)
        index_path = vault_root / "indexes" / ("practice_index.yaml" if record.kind == "practice" else "asset_index.yaml")
        write(index_path, set_index_status(read(index_path), record.item_id, status), apply)
        state_by_id[record.item_id] = state

    updated_metadata = update_metadata(metadata_lines, start, end, action, state_by_id)
    if updated_metadata != "\n".join(metadata_lines).rstrip() + "\n":
        write(metadata_path, updated_metadata, apply)
    print("runtime_cleanup: use selected generated-output refresh and managed runtime receipt rollback; ChatGPT remains manual")
    print("restore: rebuild from public Core plus selected Vault; do not copy another machine's runtime files")
    print(f"writes: {'applied' if apply else 'none'}")
    if not apply:
        print("Dry-run only. Re-run with --apply to write Vault metadata or lifecycle states.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply deployed capability pack disable/retire transitions.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", required=True, help="Selected Agent Foundry Vault root.")
    parser.add_argument("--pack-id", required=True, help="Deployed capability pack id.")
    parser.add_argument("--action", choices=["disable", "retire"], required=True)
    parser.add_argument("--apply", action="store_true", help="Write lifecycle changes. Default is dry-run.")
    args = parser.parse_args()
    return lifecycle(
        Path(args.core_root).expanduser().resolve(),
        Path(args.vault_root).expanduser().resolve(),
        args.pack_id,
        args.action,
        args.apply,
    )


if __name__ == "__main__":
    sys.exit(main())
