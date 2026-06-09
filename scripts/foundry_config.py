#!/usr/bin/env python3
"""Manage the machine-local Agent Foundry locator config."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path.home() / ".agent-foundry" / "config.yaml"
CORE_MARKERS = [
    "workflows/harvest-practices.md",
    "schemas/practice-entry.schema.yaml",
    "scripts/foundry_config.py",
]
VAULT_MARKERS = [
    "indexes/practice_index.yaml",
    "indexes/asset_index.yaml",
    "usage/usage-aggregate.yaml",
]


def quote(value: Path | str) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def config_text(repo_root: Path = ROOT, core_root: Path | None = None, vault_root: Path | None = None) -> str:
    repo_root = repo_root.resolve()
    core_root = (core_root or repo_root).resolve()
    vault_root = (vault_root or repo_root).resolve()
    lines = [
        "schema_version: 1",
        f"repo_root: {quote(repo_root)}",
        f"core_root: {quote(core_root)}",
        f"vault_root: {quote(vault_root)}",
        "core_markers:",
    ]
    lines.extend(f"  - {marker}" for marker in CORE_MARKERS)
    lines.append("vault_markers:")
    lines.extend(f"  - {marker}" for marker in VAULT_MARKERS)
    lines.extend(
        [
            "",
            "# Machine-local locator for agents working outside the Agent Foundry repo.",
            "# Do not sync this file as canonical knowledge.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_config(path: Path = CONFIG_PATH) -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = {
        "core_markers": [],
        "vault_markers": [],
        "canonical_markers": [],
    }
    if not path.exists():
        return data
    current_list = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":"):
            current_list = stripped.removesuffix(":")
            data.setdefault(current_list, [])
            continue
        if current_list and stripped.startswith("- "):
            values = data.setdefault(current_list, [])
            if isinstance(values, list):
                values.append(stripped[2:].strip().strip('"'))
            continue
        current_list = ""
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def validate(path: Path = CONFIG_PATH) -> list[str]:
    errors: list[str] = []
    data = parse_config(path)
    repo_root_text = str(data.get("repo_root", ""))
    core_root_text = str(data.get("core_root", ""))
    vault_root_text = str(data.get("vault_root", ""))
    repo_root = Path(repo_root_text).expanduser()
    core_root = Path(core_root_text).expanduser()
    vault_root = Path(vault_root_text).expanduser()
    core_markers = data.get("core_markers", [])
    vault_markers = data.get("vault_markers", [])
    compatibility_markers = data.get("canonical_markers", [])
    if repo_root_text and not repo_root.exists():
        errors.append(f"repo_root does not exist: {repo_root}")
    if not core_root_text:
        errors.append("missing core_root")
    elif not core_root.exists():
        errors.append(f"core_root does not exist: {core_root}")
    if not vault_root_text:
        errors.append("missing vault_root")
    elif not vault_root.exists():
        errors.append(f"vault_root does not exist: {vault_root}")
    if not isinstance(core_markers, list) or not core_markers:
        if isinstance(compatibility_markers, list) and compatibility_markers:
            core_markers = compatibility_markers
        else:
            errors.append("missing core_markers")
    if not isinstance(vault_markers, list) or not vault_markers:
        if isinstance(compatibility_markers, list) and compatibility_markers:
            vault_markers = compatibility_markers
        else:
            errors.append("missing vault_markers")

    if isinstance(core_markers, list):
        for marker in core_markers:
            marker_path = core_root / marker
            if not marker_path.exists():
                errors.append(f"core marker missing: {marker_path}")
    if isinstance(vault_markers, list):
        for marker in vault_markers:
            marker_path = vault_root / marker
            if not marker_path.exists():
                errors.append(f"vault marker missing: {marker_path}")
    return errors


def write_config(
    path: Path = CONFIG_PATH,
    repo_root: Path = ROOT,
    core_root: Path | None = None,
    vault_root: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config_text(repo_root, core_root, vault_root), encoding="utf-8")
    print(f"wrote foundry locator: {path}")


def status(path: Path = CONFIG_PATH) -> int:
    if not path.exists():
        print(f"foundry locator: missing ({path})")
        return 1
    data = parse_config(path)
    print(f"foundry locator: {path}")
    for key in ["repo_root", "core_root", "vault_root"]:
        print(f"{key}: {data.get(key, '')}")
    for label in ["core_markers", "vault_markers", "canonical_markers"]:
        markers = data.get(label, [])
        if not isinstance(markers, list) or not markers:
            continue
        print(f"{label}:")
        for marker in markers:
            print(f"  - {marker}")
    errors = validate(path)
    if errors:
        print("validation: failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("validation: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the machine-local Agent Foundry locator config.")
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("--path", default=str(CONFIG_PATH), help="Config path to write.")
    write.add_argument("--repo-root", default="", help="Compatibility repo root. Defaults to core root.")
    write.add_argument("--core-root", default="", help="Agent Foundry Core root.")
    write.add_argument("--vault-root", default="", help="Agent Foundry Vault root.")
    stat = sub.add_parser("status")
    stat.add_argument("--path", default=str(CONFIG_PATH), help="Config path to inspect.")
    args = parser.parse_args()

    if args.command == "write":
        core_root = Path(args.core_root).expanduser() if args.core_root else ROOT
        vault_root = Path(args.vault_root).expanduser() if args.vault_root else core_root
        repo_root = Path(args.repo_root).expanduser() if args.repo_root else core_root
        write_config(Path(args.path).expanduser(), repo_root, core_root, vault_root)
    elif args.command == "status":
        return status(Path(args.path).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
