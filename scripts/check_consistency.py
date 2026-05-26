#!/usr/bin/env python3
"""Consistency checks for agent-practices.

No third-party dependencies. Intended to be callable by any local agent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_STATUSES = {"active", "revised"}
INACTIVE_PRACTICE_STATUSES = {"candidate", "proposed", "superseded", "archived"}
INACTIVE_ASSET_STATUSES = {"candidate", "proposed", "deprecated", "retired"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> dict[str, str]:
    text = read(path)
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def simple_yaml_entries(index_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in index_text.splitlines():
        if line.startswith("  - id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
            continue
        if current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def scan_yaml_status(path: Path) -> str | None:
    for line in read(path).splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return None


def check_index_paths(index_path: Path, label: str) -> list[str]:
    errors: list[str] = []
    for entry in simple_yaml_entries(read(index_path)):
        rel = entry.get("path")
        if not rel:
            errors.append(f"{label} {entry.get('id')} has no path")
            continue
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{label} {entry.get('id')} path missing: {rel}")
    return errors


def check_practice_frontmatter() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "practices").glob("*/*.md")):
        fm = frontmatter(path)
        if not fm:
            errors.append(f"Practice missing frontmatter: {path.relative_to(ROOT)}")
            continue
        pid = fm.get("id")
        if not pid:
            errors.append(f"Practice missing id: {path.relative_to(ROOT)}")
        elif not path.name.startswith(pid):
            errors.append(f"Practice filename/id mismatch: {path.relative_to(ROOT)} has id {pid}")
        status = fm.get("status")
        if status not in ACTIVE_STATUSES | INACTIVE_PRACTICE_STATUSES:
            errors.append(f"Practice {pid} has invalid status: {status}")
    return errors


def check_asset_files() -> list[str]:
    errors: list[str] = []
    required = [
        "id:",
        "title:",
        "asset_type:",
        "status:",
        "purpose:",
        "responsibility:",
        "non_responsibility:",
        "inputs:",
        "process:",
        "outputs:",
        "canonical_practices:",
        "published_to:",
        "usage_triggers:",
        "success_criteria:",
    ]
    for path in sorted((ROOT / "assets").glob("*/*.yaml")):
        text = read(path)
        asset_id = None
        for line in text.splitlines():
            if line.startswith("id:"):
                asset_id = line.split(":", 1)[1].strip()
                break
        if not asset_id:
            errors.append(f"Asset missing id: {path.relative_to(ROOT)}")
        elif not path.name.startswith(asset_id):
            errors.append(f"Asset filename/id mismatch: {path.relative_to(ROOT)} has id {asset_id}")
        status = scan_yaml_status(path)
        if status not in ACTIVE_STATUSES | INACTIVE_ASSET_STATUSES:
            errors.append(f"Asset {asset_id} has invalid status: {status}")
        for key in required:
            if key not in text:
                errors.append(f"Asset {asset_id} missing required field {key.rstrip(':')}")
    return errors


def check_no_inactive_leakage() -> list[str]:
    errors: list[str] = []
    adapter_files = [p for p in (ROOT / "adapters").rglob("*") if p.is_file()]
    bad_statuses = {"proposed", "candidate", "superseded", "archived", "deprecated", "retired"}
    for path in adapter_files:
        for line in read(path).splitlines():
            match = re.match(r"^\s*status:\s*([A-Za-z_-]+)\s*$", line)
            if match and match.group(1) in bad_statuses:
                errors.append(
                    f"Inactive status leaked into adapter {path.relative_to(ROOT)}: status {match.group(1)}"
                )
    return errors


def check_no_deepseek_direct_adapter() -> list[str]:
    if (ROOT / "adapters" / "deepseek").exists():
        return ["Direct DeepSeek adapter exists; DeepSeek should be an underlying model provider only"]
    return []


def check_asset_usage_log() -> list[str]:
    path = ROOT / "usage" / "asset-usage-log.yaml"
    if not path.exists():
        return ["Missing usage/asset-usage-log.yaml"]
    text = read(path)
    if "entries:" not in text:
        return ["asset-usage-log.yaml missing entries"]
    return []


def main() -> int:
    errors: list[str] = []
    errors += check_index_paths(ROOT / "indexes" / "practice_index.yaml", "Practice")
    errors += check_index_paths(ROOT / "indexes" / "asset_index.yaml", "Asset")
    errors += check_practice_frontmatter()
    errors += check_asset_files()
    errors += check_no_inactive_leakage()
    errors += check_no_deepseek_direct_adapter()
    errors += check_asset_usage_log()

    if errors:
        print("Consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
