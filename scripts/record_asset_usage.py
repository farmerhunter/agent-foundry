#!/usr/bin/env python3
"""Append asset usage evidence to usage/asset-usage-log.yaml.

This script is intentionally small and dependency-free so any local agent can call it.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "usage" / "asset-usage-log.yaml"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def main() -> int:
    parser = argparse.ArgumentParser(description="Record usage evidence for an asset.")
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--project", default="")
    parser.add_argument("--trigger", default="")
    parser.add_argument("--outcome", default="unknown", choices=["useful", "neutral", "not_useful", "unknown"])
    parser.add_argument("--note", default="")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args()

    if not LOG_PATH.exists():
        LOG_PATH.write_text("schema_version: 1\nupdated: \n\nentries: []\n", encoding="utf-8")

    text = LOG_PATH.read_text(encoding="utf-8")
    if "entries: []" in text:
        text = text.replace("entries: []", "entries:")

    lines = text.rstrip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("updated:"):
            lines[i] = f"updated: {args.date}"
            break

    entry = [
        f"  - asset_id: {args.asset_id}",
        f"    date: {args.date}",
        f"    agent: {yaml_quote(args.agent)}",
        f"    project: {yaml_quote(args.project)}",
        f"    trigger: {yaml_quote(args.trigger)}",
        f"    outcome: {args.outcome}",
        f"    note: {yaml_quote(args.note)}",
    ]
    lines.extend(entry)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Recorded usage for {args.asset_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

