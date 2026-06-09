#!/usr/bin/env python3
"""Initialize a blank Agent Foundry Vault."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from check_foundry_roots import validate
from foundry_config import ROOT


def write(path: Path, text: str, apply: bool) -> None:
    print(f"{'write' if apply else 'would write'}: {path}")
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def ensure_dir(path: Path, apply: bool) -> None:
    print(f"{'mkdir' if apply else 'would mkdir'}: {path}")
    if apply:
        path.mkdir(parents=True, exist_ok=True)


def fail_if_existing_vault(vault_root: Path, force: bool) -> None:
    markers = [
        vault_root / "indexes" / "practice_index.yaml",
        vault_root / "indexes" / "asset_index.yaml",
        vault_root / "usage" / "usage-aggregate.yaml",
    ]
    existing = [path for path in markers if path.exists()]
    if existing and not force:
        rels = "\n".join(f"- {path}" for path in existing)
        raise SystemExit(
            "Refusing to overwrite existing Vault marker files. "
            "Use --force only after backing up the target.\n"
            f"{rels}"
        )


def practice_index_text(today: str) -> str:
    return "\n".join(
        [
            "schema_version: 1",
            f"updated: {today}",
            "",
            "domains: {}",
            "",
            "practices: []",
            "",
        ]
    )


def asset_index_text(today: str) -> str:
    return "\n".join(
        [
            "schema_version: 1",
            f"updated: {today}",
            "",
            "asset_types: {}",
            "",
            "assets: []",
            "",
        ]
    )


def usage_aggregate_text(today: str) -> str:
    return "\n".join(
        [
            "schema_version: 1",
            f"updated: {today}",
            "",
            "aggregates: []",
            "",
        ]
    )


def initialize(vault_root: Path, apply: bool, force: bool) -> None:
    vault_root = vault_root.expanduser().resolve()
    fail_if_existing_vault(vault_root, force)
    today = date.today().isoformat()
    for rel in [
        "practices",
        "assets",
        "imports/inbox",
        "usage/local",
    ]:
        ensure_dir(vault_root / rel, apply)
    write(vault_root / "indexes" / "practice_index.yaml", practice_index_text(today), apply)
    write(vault_root / "indexes" / "asset_index.yaml", asset_index_text(today), apply)
    write(vault_root / "usage" / "usage-aggregate.yaml", usage_aggregate_text(today), apply)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a blank Agent Foundry Vault.")
    parser.add_argument("vault_root", help="Directory to initialize as a blank Vault.")
    parser.add_argument("--core-root", default=str(ROOT), help="Core root used for post-init validation.")
    parser.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing Vault marker files.")
    args = parser.parse_args()

    vault_root = Path(args.vault_root).expanduser().resolve()
    core_root = Path(args.core_root).expanduser().resolve()
    initialize(vault_root, args.apply, args.force)

    if args.apply:
        errors = validate(core_root, vault_root)
        if errors:
            print("Blank Vault initialized but validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Blank Vault initialized and validated.")
    else:
        print("Dry-run only. Re-run with --apply to create the blank Vault.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
