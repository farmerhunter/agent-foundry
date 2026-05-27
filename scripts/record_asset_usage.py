#!/usr/bin/env python3
"""Append local usage evidence and update the shared usage aggregate.

This script is intentionally small and dependency-free so any local agent can call it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LOG_PATH = ROOT / "usage" / "local" / "usage-log.yaml"
AGGREGATE_PATH = ROOT / "usage" / "usage-aggregate.yaml"


OUTCOMES = ["useful", "neutral", "not_useful", "unknown"]


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def machine_hash() -> str:
    return hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[:12]


def append_local_entry(args: argparse.Namespace, subject_type: str, subject_id: str) -> None:
    LOCAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOCAL_LOG_PATH.exists():
        LOCAL_LOG_PATH.write_text("schema_version: 1\nupdated: \n\nentries:\n", encoding="utf-8")

    text = LOCAL_LOG_PATH.read_text(encoding="utf-8")
    lines = text.rstrip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("updated:"):
            lines[i] = f"updated: {args.date}"
            break

    entry = [
        f"  - subject_type: {subject_type}",
        f"    subject_id: {subject_id}",
        f"    date: {args.date}",
        f"    agent: {yaml_quote(args.agent)}",
        f"    machine_hash: {yaml_quote(machine_hash())}",
        f"    project: {yaml_quote(args.project)}",
        f"    trigger: {yaml_quote(args.trigger)}",
        f"    outcome: {args.outcome}",
        f"    note: {yaml_quote(args.note)}",
    ]
    lines.extend(entry)
    LOCAL_LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_aggregate() -> dict[tuple[str, str, str, str, str], dict[str, str | int]]:
    rows: dict[tuple[str, str, str, str, str], dict[str, str | int]] = {}
    if not AGGREGATE_PATH.exists():
        return rows
    current: dict[str, str | int] | None = None
    for line in AGGREGATE_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- subject_type:"):
            if current:
                key = aggregate_key(current)
                rows[key] = current
            current = {"subject_type": stripped.split(":", 1)[1].strip()}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            value = value.strip().strip('"')
            if key.endswith("_count"):
                current[key] = int(value or "0")
            else:
                current[key] = value
    if current:
        rows[aggregate_key(current)] = current
    return rows


def aggregate_key(row: dict[str, str | int]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("subject_type", "")),
        str(row.get("subject_id", "")),
        str(row.get("period", "")),
        str(row.get("agent", "")),
        str(row.get("machine_hash", "")),
    )


def write_aggregate(rows: dict[tuple[str, str, str, str, str], dict[str, str | int]], updated: str) -> None:
    AGGREGATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["schema_version: 1", f"updated: {updated}", "", "aggregates:"]
    for row in sorted(rows.values(), key=aggregate_key):
        lines.extend(
            [
                f"  - subject_type: {row['subject_type']}",
                f"    subject_id: {row['subject_id']}",
                f"    period: {row['period']}",
                f"    agent: {yaml_quote(str(row['agent']))}",
                f"    machine_hash: {yaml_quote(str(row['machine_hash']))}",
                f"    useful_count: {row.get('useful_count', 0)}",
                f"    neutral_count: {row.get('neutral_count', 0)}",
                f"    not_useful_count: {row.get('not_useful_count', 0)}",
                f"    unknown_count: {row.get('unknown_count', 0)}",
                f"    last_used: {row['last_used']}",
            ]
        )
    AGGREGATE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_aggregate(args: argparse.Namespace, subject_type: str, subject_id: str) -> None:
    rows = parse_aggregate()
    period = args.date[:7]
    key = (subject_type, subject_id, period, args.agent, machine_hash())
    row = rows.setdefault(
        key,
        {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "period": period,
            "agent": args.agent,
            "machine_hash": machine_hash(),
            "useful_count": 0,
            "neutral_count": 0,
            "not_useful_count": 0,
            "unknown_count": 0,
            "last_used": args.date,
        },
    )
    count_key = f"{args.outcome}_count"
    row[count_key] = int(row.get(count_key, 0)) + 1
    if str(row.get("last_used", "")) < args.date:
        row["last_used"] = args.date
    write_aggregate(rows, args.date)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record usage evidence for an asset or practice.")
    parser.add_argument("--asset-id", default="")
    parser.add_argument("--practice-id", default="")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--project", default="")
    parser.add_argument("--trigger", default="")
    parser.add_argument("--outcome", default="unknown", choices=OUTCOMES)
    parser.add_argument("--note", default="")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--no-aggregate", action="store_true", help="Record raw local evidence only.")
    args = parser.parse_args()

    subjects: list[tuple[str, str]] = []
    if args.asset_id:
        subjects.append(("asset", args.asset_id))
    if args.practice_id:
        subjects.append(("practice", args.practice_id))
    if not subjects:
        raise SystemExit("Provide --asset-id or --practice-id.")

    for subject_type, subject_id in subjects:
        append_local_entry(args, subject_type, subject_id)
        if not args.no_aggregate:
            update_aggregate(args, subject_type, subject_id)
        print(f"Recorded usage for {subject_type} {subject_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
