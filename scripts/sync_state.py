#!/usr/bin/env python3
"""Maintain machine-local sync state for Agent Foundry."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "sync" / "local" / "state.yaml"
TEMPLATE = ROOT / "sync" / "templates" / "sync_state.template.yaml"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_state() -> None:
    if STATE.exists():
        return
    if not TEMPLATE.exists():
        raise SystemExit(f"Missing sync state template: {TEMPLATE}")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")


def read_state(init_if_missing: bool = False) -> str:
    if init_if_missing:
        ensure_state()
    elif not STATE.exists():
        return f"not initialized: {STATE}\n"
    return STATE.read_text(encoding="utf-8")


def update_block(text: str, block: str, values: dict[str, str]) -> str:
    lines = text.splitlines()
    output: list[str] = []
    in_block = False
    for line in lines:
        if line == f"{block}:":
            in_block = True
            output.append(line)
            continue
        if in_block and line and not line.startswith("  "):
            in_block = False
        if in_block and line.startswith("  ") and ":" in line:
            key = line.strip().split(":", 1)[0]
            if key in values:
                output.append(f"  {key}: {values[key]}")
                continue
        output.append(line)
    return "\n".join(output).rstrip() + "\n"


def record(block: str, snapshot: Path, timestamp_key: str) -> None:
    ensure_state()
    snapshot = snapshot.expanduser().resolve()
    if not snapshot.exists():
        raise SystemExit(f"Snapshot not found: {snapshot}")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    text = read_state(init_if_missing=True)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("updated:"):
            lines[i] = f"updated: {now}"
            break
    text = "\n".join(lines) + "\n"
    text = update_block(
        text,
        block,
        {
            "path": str(snapshot),
            "archive_sha256": file_sha256(snapshot),
            timestamp_key: now,
        },
    )
    try:
        STATE.write_text(text, encoding="utf-8")
    except PermissionError as exc:
        raise SystemExit(f"Unable to write sync state {STATE}: {exc}") from exc
    print(f"recorded {block}: {snapshot}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage machine-local Agent Foundry sync state.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    exported = sub.add_parser("record-exported")
    exported.add_argument("snapshot")
    imported = sub.add_parser("record-imported")
    imported.add_argument("snapshot")
    applied = sub.add_parser("mark-applied")
    applied.add_argument("snapshot")
    args = parser.parse_args()

    if args.command == "init":
        ensure_state()
        print(STATE)
    elif args.command == "status":
        print(read_state(), end="")
    elif args.command == "record-exported":
        record("latest_exported_snapshot", Path(args.snapshot), "created_at")
    elif args.command == "record-imported":
        record("latest_imported_snapshot", Path(args.snapshot), "created_at")
    elif args.command == "mark-applied":
        record("last_applied_snapshot", Path(args.snapshot), "applied_at")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
