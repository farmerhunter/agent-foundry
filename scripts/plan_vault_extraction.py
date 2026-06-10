#!/usr/bin/env python3
"""Print a dry-run User Vault extraction inventory."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

VAULT_MOVE_PATHS = [
    "practices",
    "assets",
    "indexes",
    "usage/usage-aggregate.yaml",
    "Agent Foundry.md",
    "docs/obsidian.md",
]

VAULT_OPTIONAL_PATHS = [
    "imports",
    "usage/adoption-log.yaml",
    "usage/asset-usage-log.yaml",
]

LOCAL_PRIVATE_PATHS = [
    "usage/local",
    "runtime/local",
    "sync/local",
    "sync/imported",
    "sync/pending",
    "sync/applied",
    "sync/conflicts",
    "sync/snapshots",
    ".claude/settings.local.json",
]

CORE_STAY_PATHS = [
    "README.md",
    "AGENTS.md",
    "workflows",
    "schemas",
    "scripts",
    "templates",
    "runtime/templates",
    "adapters/adapter_profiles.yaml",
    "adapters/quality",
    "docs/deployment.md",
    "docs/system-design.md",
    "docs/usage.md",
    "docs/roadmap.md",
    "docs/lifecycle-compatibility.md",
    "docs/offline-sync.md",
    "docs/standards-and-sources.md",
]


def file_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return sum(1 for item in path.rglob("*") if item.is_file())


def print_group(root: Path, title: str, paths: list[str], required: bool) -> list[str]:
    missing: list[str] = []
    print(f"\n## {title}")
    for rel in paths:
        path = root / rel
        count = file_count(path)
        if path.exists():
            print(f"- {rel}: present ({count} files)")
        else:
            state = "missing required" if required else "absent optional"
            print(f"- {rel}: {state}")
            if required:
                missing.append(rel)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a dry-run User Vault extraction inventory.")
    parser.add_argument("--repo-root", default=str(ROOT), help="Current combined repository root.")
    args = parser.parse_args()

    root = Path(args.repo_root).expanduser().resolve()
    print("User Vault extraction dry-run inventory")
    print("No files are moved, copied, deleted, or uploaded.")
    print("Paths are relative to the current combined repository root.")

    missing: list[str] = []
    missing += print_group(root, "Move To Active User Vault", VAULT_MOVE_PATHS, required=True)
    print_group(root, "Move If Present Or Review", VAULT_OPTIONAL_PATHS, required=False)
    print_group(root, "Keep Local Private And Ignored", LOCAL_PRIVATE_PATHS, required=False)
    missing += print_group(root, "Keep In Public Core", CORE_STAY_PATHS, required=True)

    print("\n## Required Pre-Migration Gates")
    print("- Create a local backup of the current combined checkout before moving records.")
    print("- Verify the backup can be listed or restored before moving records.")
    print("- Initialize or select the active User Vault target.")
    print("- Default local pattern: ~/.agent-foundry/vault/agent-foundry-vault-<account>.")
    print("- Validate the private Vault after copying records.")
    print("- Update ~/.agent-foundry/config.yaml only after Core and Vault validate separately.")
    print("- Do not create a private remote or move private records without explicit user approval.")

    if missing:
        print("\nInventory failed; required paths are missing:")
        for rel in missing:
            print(f"- {rel}")
        return 1
    print("\nInventory passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
