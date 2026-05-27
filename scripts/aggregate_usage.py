#!/usr/bin/env python3
"""Build sanitized usage aggregates from local and legacy usage logs."""

from __future__ import annotations

import argparse
import hashlib
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LOG = ROOT / "usage" / "local" / "usage-log.yaml"
LEGACY_ASSET_LOG = ROOT / "usage" / "asset-usage-log.yaml"
AGGREGATE = ROOT / "usage" / "usage-aggregate.yaml"
OUTCOMES = {"useful", "neutral", "not_useful", "unknown"}


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def machine_hash() -> str:
    return hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[:12]


def parse_entries(path: Path, legacy_asset: bool = False) -> list[dict[str, str]]:
    if not path.exists():
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                entries.append(current)
            current = {}
            stripped = stripped[2:]
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)

    normalized: list[dict[str, str]] = []
    for entry in entries:
        if legacy_asset:
            subject_id = entry.get("asset_id", "")
            subject_type = "asset"
        else:
            subject_id = entry.get("subject_id", "")
            subject_type = entry.get("subject_type", "")
        if not subject_id or not subject_type:
            continue
        normalized.append(
            {
                "subject_type": subject_type,
                "subject_id": subject_id,
                "date": entry.get("date", ""),
                "agent": entry.get("agent", "unknown"),
                "machine_hash": entry.get("machine_hash", machine_hash()),
                "outcome": entry.get("outcome", "unknown"),
            }
        )
    return normalized


def aggregate(entries: list[dict[str, str]]) -> dict[tuple[str, str, str, str, str], dict[str, str | int]]:
    rows: dict[tuple[str, str, str, str, str], dict[str, str | int]] = {}
    for entry in entries:
        date = entry["date"]
        if len(date) < 7:
            continue
        outcome = entry["outcome"] if entry["outcome"] in OUTCOMES else "unknown"
        key = (
            entry["subject_type"],
            entry["subject_id"],
            date[:7],
            entry["agent"],
            entry["machine_hash"],
        )
        row = rows.setdefault(
            key,
            {
                "subject_type": entry["subject_type"],
                "subject_id": entry["subject_id"],
                "period": date[:7],
                "agent": entry["agent"],
                "machine_hash": entry["machine_hash"],
                "useful_count": 0,
                "neutral_count": 0,
                "not_useful_count": 0,
                "unknown_count": 0,
                "last_used": date,
            },
        )
        row[f"{outcome}_count"] = int(row.get(f"{outcome}_count", 0)) + 1
        if str(row["last_used"]) < date:
            row["last_used"] = date
    return rows


def parse_existing_aggregate() -> dict[tuple[str, str, str, str, str], dict[str, str | int]]:
    if not AGGREGATE.exists():
        return {}
    rows: dict[tuple[str, str, str, str, str], dict[str, str | int]] = {}
    current: dict[str, str | int] | None = None
    for line in AGGREGATE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- subject_type:"):
            if current:
                rows[row_key(current)] = current
            current = {"subject_type": stripped.split(":", 1)[1].strip()}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            value = value.strip().strip('"')
            if key.endswith("_count"):
                current[key] = int(value or "0")
            else:
                current[key] = value
    if current:
        rows[row_key(current)] = current
    return rows


def merge_rows(
    base: dict[tuple[str, str, str, str, str], dict[str, str | int]],
    incoming: dict[tuple[str, str, str, str, str], dict[str, str | int]],
) -> dict[tuple[str, str, str, str, str], dict[str, str | int]]:
    for key, row in incoming.items():
        if key not in base:
            base[key] = row
            continue
        existing = base[key]
        for outcome in OUTCOMES:
            count_key = f"{outcome}_count"
            existing[count_key] = max(int(existing.get(count_key, 0)), int(row.get(count_key, 0)))
        if str(existing.get("last_used", "")) < str(row.get("last_used", "")):
            existing["last_used"] = row["last_used"]
    return base


def row_key(row: dict[str, str | int]) -> tuple[str, str, str, str, str]:
    return (
        str(row["subject_type"]),
        str(row["subject_id"]),
        str(row["period"]),
        str(row["agent"]),
        str(row["machine_hash"]),
    )


def write(rows: dict[tuple[str, str, str, str, str], dict[str, str | int]], updated: str) -> None:
    lines = ["schema_version: 1", f"updated: {updated}", "", "aggregates:"]
    for row in sorted(rows.values(), key=row_key):
        lines.extend(
            [
                f"  - subject_type: {row['subject_type']}",
                f"    subject_id: {row['subject_id']}",
                f"    period: {row['period']}",
                f"    agent: {yaml_quote(str(row['agent']))}",
                f"    machine_hash: {yaml_quote(str(row['machine_hash']))}",
                f"    useful_count: {row['useful_count']}",
                f"    neutral_count: {row['neutral_count']}",
                f"    not_useful_count: {row['not_useful_count']}",
                f"    unknown_count: {row['unknown_count']}",
                f"    last_used: {row['last_used']}",
            ]
        )
    AGGREGATE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build shared usage aggregates from usage logs.")
    parser.add_argument("--include-legacy", action="store_true", help="Include usage/asset-usage-log.yaml.")
    parser.add_argument("--replace", action="store_true", help="Replace the aggregate instead of preserving existing rows.")
    args = parser.parse_args()

    entries = parse_entries(LOCAL_LOG)
    if args.include_legacy:
        entries.extend(parse_entries(LEGACY_ASSET_LOG, legacy_asset=True))
    rows = aggregate(entries)
    if not args.replace:
        rows = merge_rows(parse_existing_aggregate(), rows)
    updated = max(
        [str(row.get("last_used", "")) for row in rows.values()] + [entry["date"] for entry in entries if entry.get("date")],
        default="",
    )
    write(rows, updated)
    print(f"wrote {AGGREGATE}")
    print(f"aggregates: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
