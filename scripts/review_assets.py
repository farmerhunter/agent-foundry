#!/usr/bin/env python3
"""Generate an Agent Foundry asset lifecycle review report."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_scalar(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def extract_list(text: str, key: str) -> list[str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            rest = line.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                return [v.strip().strip('"').strip("'") for v in rest[1:-1].split(",") if v.strip()]
            if rest:
                return [rest.strip().strip('"').strip("'")]
            values: list[str] = []
            for follow in lines[i + 1 :]:
                stripped = follow.strip()
                if stripped.startswith("- "):
                    values.append(stripped[2:].strip().strip('"').strip("'"))
                elif stripped and not follow.startswith(" "):
                    break
            return values
    return []


def load_assets() -> list[dict[str, object]]:
    assets: list[dict[str, object]] = []
    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        text = read(path)
        assets.append(
            {
                "id": extract_scalar(text, "id"),
                "title": extract_scalar(text, "title"),
                "status": extract_scalar(text, "status"),
                "path": str(path.relative_to(ROOT)),
                "review_after_days": int(extract_scalar(text, "review_after_days") or "90"),
                "triggers": extract_list(text, "usage_triggers"),
                "canonical_practices": extract_list(text, "canonical_practices"),
                "published_to": extract_list(text, "published_to"),
            }
        )
    return assets


def load_aggregate_usage() -> dict[str, list[dt.date]]:
    usage_path = ROOT / "usage" / "usage-aggregate.yaml"
    usage: dict[str, list[dt.date]] = {}
    current: str | None = None
    current_counts = 0
    if not usage_path.exists():
        return usage
    for line in read(usage_path).splitlines():
        stripped = line.strip()
        if stripped.startswith("- subject_type:"):
            current = None
            current_counts = 0
            subject_type = stripped.split(":", 1)[1].strip()
            if subject_type != "asset":
                continue
        elif stripped.startswith("subject_id:"):
            current = stripped.split(":", 1)[1].strip()
            usage.setdefault(current, [])
        elif current and any(stripped.startswith(f"{name}_count:") for name in ["useful", "neutral", "not_useful", "unknown"]):
            try:
                current_counts += int(stripped.split(":", 1)[1].strip() or "0")
            except ValueError:
                pass
        elif current and stripped.startswith("last_used:"):
            value = stripped.split(":", 1)[1].strip()
            try:
                usage[current].extend([dt.date.fromisoformat(value)] * max(current_counts, 1))
            except ValueError:
                pass
    return usage


def load_legacy_usage() -> dict[str, list[dt.date]]:
    usage_path = ROOT / "usage" / "asset-usage-log.yaml"
    usage: dict[str, list[dt.date]] = {}
    current: str | None = None
    if not usage_path.exists():
        return usage
    for line in read(usage_path).splitlines():
        stripped = line.strip()
        if stripped.startswith("- asset_id:"):
            current = stripped.split(":", 1)[1].strip()
            usage.setdefault(current, [])
        elif current and stripped.startswith("date:"):
            value = stripped.split(":", 1)[1].strip()
            try:
                usage[current].append(dt.date.fromisoformat(value))
            except ValueError:
                pass
    return usage


def load_usage() -> tuple[dict[str, list[dt.date]], str]:
    usage = load_aggregate_usage()
    if usage:
        return usage, "usage/usage-aggregate.yaml"
    return load_legacy_usage(), "usage/asset-usage-log.yaml"


def trigger_overlaps(assets: list[dict[str, object]]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for asset in assets:
        for trigger in asset["triggers"]:
            owners.setdefault(trigger, []).append(asset["id"])
    return {trigger: ids for trigger, ids in owners.items() if len(ids) > 1}


def recommendation(asset: dict[str, object], usage_dates: list[dt.date], today: dt.date) -> tuple[str, str]:
    status = str(asset["status"])
    if status == "archived":
        return ("skip", "archived asset")
    if status in {"candidate", "proposed"}:
        return ("needs approval", "not active yet")
    if status in {"deprecated", "retired"}:
        return ("confirm no active usage", f"status is {status}")
    if not usage_dates:
        return ("review", "no usage evidence")
    last_used = max(usage_dates)
    age = (today - last_used).days
    threshold = int(asset["review_after_days"])
    if status in ACTIVE_STATUSES and age > threshold:
        return ("review", f"last usage {age} days ago exceeds threshold {threshold}")
    return ("keep active", f"last usage {age} days ago")


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Agent Foundry assets for lifecycle and usage risk.")
    parser.add_argument("--today", default=dt.date.today().isoformat())
    args = parser.parse_args()
    today = dt.date.fromisoformat(args.today)

    assets = load_assets()
    usage, usage_source = load_usage()
    overlaps = trigger_overlaps(assets)

    print("# Asset Review")
    print(f"date: {today}")
    print(f"usage_source: {usage_source}")
    print()
    for asset in assets:
        aid = str(asset["id"])
        dates = usage.get(aid, [])
        decision, reason = recommendation(asset, dates, today)
        last_used = max(dates).isoformat() if dates else "never"
        print(f"- {aid} {asset['title']}")
        print(f"  status: {asset['status']}")
        print(f"  recommendation: {decision}")
        print(f"  reason: {reason}")
        print(f"  last_used: {last_used}")
        print(f"  usage_count: {len(dates)}")
        print(f"  canonical_practices: {', '.join(asset['canonical_practices'])}")
        print(f"  published_to: {', '.join(asset['published_to'])}")

    if overlaps:
        print()
        print("# Trigger Overlaps")
        for trigger, ids in sorted(overlaps.items()):
            print(f"- {trigger}: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
