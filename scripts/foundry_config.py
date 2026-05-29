#!/usr/bin/env python3
"""Manage the machine-local Agent Foundry locator config."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path.home() / ".agent-foundry" / "config.yaml"
VAULT_MARKERS = [
    "indexes/practice_index.yaml",
    "indexes/asset_index.yaml",
    "workflows/harvest-practices.md",
]


def quote(value: Path | str) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def config_text(repo_root: Path = ROOT) -> str:
    repo_root = repo_root.resolve()
    lines = [
        "schema_version: 1",
        f"repo_root: {quote(repo_root)}",
        f"core_root: {quote(repo_root)}",
        f"vault_root: {quote(repo_root)}",
        "canonical_markers:",
    ]
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
    data: dict[str, str | list[str]] = {"canonical_markers": []}
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
    repo_root = Path(str(data.get("repo_root", ""))).expanduser()
    vault_root = Path(str(data.get("vault_root", ""))).expanduser()
    core_root = Path(str(data.get("core_root", ""))).expanduser()
    markers = data.get("canonical_markers", [])
    if not repo_root:
        errors.append("missing repo_root")
    elif not repo_root.exists():
        errors.append(f"repo_root does not exist: {repo_root}")
    if not core_root:
        errors.append("missing core_root")
    elif not core_root.exists():
        errors.append(f"core_root does not exist: {core_root}")
    if not vault_root:
        errors.append("missing vault_root")
    elif not vault_root.exists():
        errors.append(f"vault_root does not exist: {vault_root}")
    if not isinstance(markers, list) or not markers:
        errors.append("missing canonical_markers")
    else:
        for marker in markers:
            marker_path = vault_root / marker
            if not marker_path.exists():
                errors.append(f"canonical marker missing: {marker_path}")
    return errors


def write_config(path: Path = CONFIG_PATH, repo_root: Path = ROOT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config_text(repo_root), encoding="utf-8")
    print(f"wrote foundry locator: {path}")


def status(path: Path = CONFIG_PATH) -> int:
    if not path.exists():
        print(f"foundry locator: missing ({path})")
        return 1
    data = parse_config(path)
    print(f"foundry locator: {path}")
    for key in ["repo_root", "core_root", "vault_root"]:
        print(f"{key}: {data.get(key, '')}")
    markers = data.get("canonical_markers", [])
    if isinstance(markers, list):
        print("canonical_markers:")
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
    write.add_argument("--repo-root", default=str(ROOT), help="Agent Foundry repo root.")
    stat = sub.add_parser("status")
    stat.add_argument("--path", default=str(CONFIG_PATH), help="Config path to inspect.")
    args = parser.parse_args()

    if args.command == "write":
        write_config(Path(args.path).expanduser(), Path(args.repo_root).expanduser())
    elif args.command == "status":
        return status(Path(args.path).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
