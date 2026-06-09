#!/usr/bin/env python3
"""Validate Agent Foundry Core and Vault roots.

This check is intentionally narrower than check_consistency.py. It validates
that a selected Vault can be checked against the selected Core without relying
on repo-relative same-root paths.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from foundry_config import CORE_MARKERS, ROOT, VAULT_MARKERS


PRACTICE_STATUSES = {
    "candidate",
    "proposed",
    "active",
    "revised",
    "superseded",
    "archived",
}
ASSET_STATUSES = {
    "candidate",
    "proposed",
    "active",
    "revised",
    "deprecated",
    "retired",
    "archived",
}
CORE_LAYOUT_MARKER = ".agent-foundry-core.yaml"
VAULT_LAYOUT_MARKER = ".agent-foundry-vault.yaml"


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


def simple_yaml_entries(index_text: str, list_key: str) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_list = False
    saw_key = False

    for line in index_text.splitlines():
        if line.startswith(f"{list_key}:"):
            saw_key = True
            rest = line.split(":", 1)[1].strip()
            if rest == "[]":
                in_list = False
                continue
            in_list = True
            continue
        if in_list and line and not line.startswith(" ") and not line.startswith("-"):
            in_list = False
        if not in_list:
            continue
        if line.startswith("  - id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip().strip('"')}
            continue
        if current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')

    if current:
        entries.append(current)
    if not saw_key:
        errors.append(f"index missing required list: {list_key}")
    return entries, errors


def scan_yaml_field(path: Path, field: str) -> str | None:
    for line in read(path).splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def parse_marker(path: Path) -> tuple[dict[str, str | list[str]], list[str]]:
    data: dict[str, str | list[str]] = {}
    errors: list[str] = []
    for line in read(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            errors.append(f"{path.name} contains unsupported YAML line: {stripped}")
            continue
        key, value = stripped.split(":", 1)
        value = value.strip().strip('"')
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip('"') for item in value[1:-1].split(",") if item.strip()]
            data[key.strip()] = items
        else:
            data[key.strip()] = value
    return data, errors


def int_field(marker: dict[str, str | list[str]], field: str, label: str) -> tuple[int | None, list[str]]:
    value = marker.get(field)
    if not isinstance(value, str):
        return None, [f"{label} layout marker missing {field}"]
    try:
        return int(value), []
    except ValueError:
        return None, [f"{label} layout marker has non-integer {field}: {value}"]


def list_field(marker: dict[str, str | list[str]], field: str, label: str) -> tuple[list[str], list[str]]:
    value = marker.get(field)
    if not isinstance(value, list) or not value:
        return [], [f"{label} layout marker missing {field}"]
    return value, []


def check_layout_compatibility(core_root: Path, vault_root: Path) -> list[str]:
    errors: list[str] = []
    core_marker_path = core_root / CORE_LAYOUT_MARKER
    vault_marker_path = vault_root / VAULT_LAYOUT_MARKER
    if not core_marker_path.exists() or not vault_marker_path.exists():
        return errors

    core_marker, core_errors = parse_marker(core_marker_path)
    vault_marker, vault_errors = parse_marker(vault_marker_path)
    errors.extend(f"core {error}" for error in core_errors)
    errors.extend(f"vault {error}" for error in vault_errors)
    if errors:
        return errors

    if core_marker.get("layout_kind") != "core":
        errors.append("core layout marker layout_kind must be core")
    if vault_marker.get("layout_kind") != "vault":
        errors.append("vault layout marker layout_kind must be vault")
    if not isinstance(core_marker.get("identity"), str) or not core_marker.get("identity"):
        errors.append("core layout marker missing non-sensitive identity")
    if not isinstance(vault_marker.get("identity"), str) or not vault_marker.get("identity"):
        errors.append("vault layout marker missing non-sensitive identity")

    core_version, core_version_errors = int_field(core_marker, "layout_version", "core")
    vault_version, vault_version_errors = int_field(vault_marker, "layout_version", "vault")
    errors.extend(core_version_errors)
    errors.extend(vault_version_errors)
    core_supported_vault, core_supported_vault_errors = list_field(
        core_marker, "supported_vault_layout_versions", "core"
    )
    vault_supported_core, vault_supported_core_errors = list_field(
        vault_marker, "supported_core_layout_versions", "vault"
    )
    core_supported_modes, core_modes_errors = list_field(core_marker, "supported_modes", "core")
    vault_supported_modes, vault_modes_errors = list_field(vault_marker, "supported_modes", "vault")
    errors.extend(core_supported_vault_errors)
    errors.extend(vault_supported_core_errors)
    errors.extend(core_modes_errors)
    errors.extend(vault_modes_errors)
    if errors:
        return errors

    mode = "combined" if core_root == vault_root else "split"
    if str(vault_version) not in core_supported_vault:
        errors.append(f"layout compatibility failed: core does not support vault layout version {vault_version}")
    if str(core_version) not in vault_supported_core:
        errors.append(f"layout compatibility failed: vault does not support core layout version {core_version}")
    if mode not in core_supported_modes:
        errors.append(f"layout compatibility failed: core does not support {mode} mode")
    if mode not in vault_supported_modes:
        errors.append(f"layout compatibility failed: vault does not support {mode} mode")
    return errors


def check_markers(root: Path, markers: list[str], label: str) -> list[str]:
    errors: list[str] = []
    if not root.exists():
        return [f"{label} root does not exist: {root}"]
    for marker in markers:
        marker_path = root / marker
        if not marker_path.exists():
            errors.append(f"{label} marker missing: {marker}")
    return errors


def check_index(vault_root: Path, relative_path: str, list_key: str, label: str) -> tuple[list[dict[str, str]], list[str]]:
    path = vault_root / relative_path
    errors: list[str] = []
    if not path.exists():
        return [], [f"missing {relative_path}"]
    text = read(path)
    if "schema_version:" not in text:
        errors.append(f"{relative_path} missing schema_version")
    entries, parse_errors = simple_yaml_entries(text, list_key)
    errors.extend(f"{relative_path} {error}" for error in parse_errors)
    seen: set[str] = set()
    for entry in entries:
        item_id = entry.get("id", "")
        rel = entry.get("path", "")
        if not item_id:
            errors.append(f"{relative_path} contains {label} entry without id")
        elif item_id in seen:
            errors.append(f"{relative_path} contains duplicate {label} id: {item_id}")
        else:
            seen.add(item_id)
        if not rel:
            errors.append(f"{relative_path} {label} {item_id or '<unknown>'} has no path")
            continue
        if not (vault_root / rel).exists():
            errors.append(f"{relative_path} {label} {item_id or '<unknown>'} path missing in vault: {rel}")
    return entries, errors


def check_practice_records(vault_root: Path) -> list[str]:
    errors: list[str] = []
    practices_root = vault_root / "practices"
    if not practices_root.exists():
        return errors
    for path in sorted(practices_root.glob("*/*.md")):
        rel = path.relative_to(vault_root)
        fm = frontmatter(path)
        if not fm:
            errors.append(f"practice missing frontmatter: {rel}")
            continue
        pid = fm.get("id")
        status = fm.get("status")
        if not pid:
            errors.append(f"practice missing id: {rel}")
        elif not path.name.startswith(pid):
            errors.append(f"practice filename/id mismatch: {rel} has id {pid}")
        if status not in PRACTICE_STATUSES:
            errors.append(f"practice {pid or rel} has invalid status: {status}")
    return errors


def check_asset_records(vault_root: Path) -> list[str]:
    errors: list[str] = []
    assets_root = vault_root / "assets"
    if not assets_root.exists():
        return errors
    for path in sorted(assets_root.glob("*/*.yaml")):
        rel = path.relative_to(vault_root)
        asset_id = scan_yaml_field(path, "id")
        status = scan_yaml_field(path, "status")
        if not asset_id:
            errors.append(f"asset missing id: {rel}")
        elif not path.name.startswith(asset_id):
            errors.append(f"asset filename/id mismatch: {rel} has id {asset_id}")
        if status not in ASSET_STATUSES:
            errors.append(f"asset {asset_id or rel} has invalid status: {status}")
    return errors


def check_usage_aggregate(vault_root: Path) -> list[str]:
    path = vault_root / "usage" / "usage-aggregate.yaml"
    if not path.exists():
        return ["missing usage/usage-aggregate.yaml"]
    text = read(path)
    errors: list[str] = []
    if "schema_version:" not in text:
        errors.append("usage/usage-aggregate.yaml missing schema_version")
    if "aggregates:" not in text:
        errors.append("usage/usage-aggregate.yaml missing aggregates")
    for line in text.splitlines():
        if line.strip().startswith("machine_hash:") and "hostname" in line.lower():
            errors.append("usage/usage-aggregate.yaml appears to contain an unhashed machine name")
    return errors


def validate(core_root: Path, vault_root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(check_markers(core_root, CORE_MARKERS, "core"))
    errors.extend(check_markers(vault_root, VAULT_MARKERS, "vault"))
    if errors:
        return errors
    errors.extend(check_layout_compatibility(core_root, vault_root))
    if errors:
        return errors

    practice_entries, practice_errors = check_index(vault_root, "indexes/practice_index.yaml", "practices", "practice")
    asset_entries, asset_errors = check_index(vault_root, "indexes/asset_index.yaml", "assets", "asset")
    errors.extend(practice_errors)
    errors.extend(asset_errors)
    errors.extend(check_usage_aggregate(vault_root))
    errors.extend(check_practice_records(vault_root))
    errors.extend(check_asset_records(vault_root))

    if not practice_entries and any((vault_root / "practices").glob("*/*.md")):
        errors.append("indexes/practice_index.yaml is empty but practice records exist")
    if not asset_entries and any((vault_root / "assets").glob("*/*.yaml")):
        errors.append("indexes/asset_index.yaml is empty but asset records exist")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate selected Agent Foundry Core and Vault roots.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", default=str(ROOT), help="Agent Foundry Vault root.")
    args = parser.parse_args()

    core_root = Path(args.core_root).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve()
    errors = validate(core_root, vault_root)
    if errors:
        print("Foundry root validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Foundry root validation passed.")
    print(f"core_root: {core_root}")
    print(f"vault_root: {vault_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
