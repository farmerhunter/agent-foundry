#!/usr/bin/env python3
"""Publish adapter outputs from a selected Agent Foundry Vault."""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

from check_foundry_roots import validate
from foundry_config import ROOT


ACTIVE_STATUSES = {"active", "revised"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def simple_yaml_entries(index_text: str, list_key: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_list = False
    for line in index_text.splitlines():
        if line.startswith(f"{list_key}:"):
            rest = line.split(":", 1)[1].strip()
            if rest == "[]":
                return []
            in_list = True
            continue
        if in_list and line and not line.startswith(" "):
            in_list = False
        if not in_list:
            continue
        if line.startswith("  - id: "):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip().strip('"')}
        elif current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def active_entries(vault_root: Path, index_rel: str, list_key: str) -> list[dict[str, str]]:
    entries = simple_yaml_entries(read(vault_root / index_rel), list_key)
    return [entry for entry in entries if entry.get("status") in ACTIVE_STATUSES]


def copytree_contents(src: Path, dest: Path, apply: bool) -> list[Path]:
    copied: list[Path] = []
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        if rel.as_posix() == "adapter-publish-manifest.yaml":
            continue
        target = dest / rel
        copied.append(target)
        print(f"{'copy' if apply else 'would copy'}: {src.name}/{rel} -> {target}")
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return copied


def manifest_text(active_practices: list[dict[str, str]], active_assets: list[dict[str, str]]) -> str:
    lines = [
        "schema_version: 1",
        f"updated: {date.today().isoformat()}",
        "source: selected_vault",
        "private_paths_recorded: false",
        "",
    ]
    if active_practices:
        lines.append("active_practices:")
        for entry in active_practices:
            lines.append(f"  - {entry['id']}")
    else:
        lines.append("active_practices: []")
    lines.append("")
    if active_assets:
        lines.append("active_assets:")
        for entry in active_assets:
            lines.append(f"  - {entry['id']}")
    else:
        lines.append("active_assets: []")
    lines.append("")
    return "\n".join(lines)


def write_manifest(output_root: Path, text: str, apply: bool) -> None:
    path = output_root / "adapter-publish-manifest.yaml"
    print(f"{'write' if apply else 'would write'}: {path}")
    if apply:
        output_root.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def publish(core_root: Path, vault_root: Path, output_root: Path, apply: bool) -> int:
    errors = validate(core_root, vault_root)
    if errors:
        print("Adapter publish failed root validation:")
        for error in errors:
            print(f"- {error}")
        return 1

    active_practices = active_entries(vault_root, "indexes/practice_index.yaml", "practices")
    active_assets = active_entries(vault_root, "indexes/asset_index.yaml", "assets")
    if not active_practices and not active_assets:
        print("Selected Vault has no active or revised practices/assets. Nothing to publish.")
        write_manifest(output_root, manifest_text(active_practices, active_assets), apply)
        return 0

    source_adapters = core_root / "adapters"
    if not source_adapters.exists():
        print(f"Core adapter template root missing: {source_adapters}")
        return 1

    if source_adapters.resolve() == output_root.resolve():
        print("Output root is the Core adapter template root; retaining existing adapter files.")
        copied: list[Path] = []
    else:
        copied = copytree_contents(source_adapters, output_root, apply)
    write_manifest(output_root, manifest_text(active_practices, active_assets), apply)
    print(f"Adapter publish {'wrote' if apply else 'planned'} {len(copied)} files.")
    print(f"Active practices selected: {len(active_practices)}")
    print(f"Active assets selected: {len(active_assets)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish adapters from a selected Agent Foundry Vault.")
    parser.add_argument("--core-root", default=str(ROOT), help="Agent Foundry Core root.")
    parser.add_argument("--vault-root", default=str(ROOT), help="Selected Agent Foundry Vault root.")
    parser.add_argument("--output-root", default="", help="Adapter output directory. Defaults to <core-root>/adapters.")
    parser.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
    args = parser.parse_args()

    core_root = Path(args.core_root).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else core_root / "adapters"
    return publish(core_root, vault_root, output_root, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
