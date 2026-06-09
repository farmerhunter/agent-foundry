#!/usr/bin/env python3
"""Read-only deployment migration planner for Agent Foundry Core/Vault split."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from check_foundry_roots import (
    CORE_LAYOUT_MARKER,
    VAULT_LAYOUT_MARKER,
    check_layout_compatibility,
    parse_marker,
    validate,
)
from foundry_config import CONFIG_PATH, ROOT, parse_config


RUNTIME_TEMPLATE = ROOT / "runtime" / "templates" / "runtime_manifest.template.yaml"
RUNTIME_LOCAL = ROOT / "runtime" / "local" / "runtime_manifest.yaml"


def yaml_scalar(value: str) -> str:
    return value.replace("\n", " ").strip()


def read_runtime_manifest() -> tuple[Path, str]:
    if RUNTIME_LOCAL.exists():
        return RUNTIME_LOCAL, RUNTIME_LOCAL.read_text(encoding="utf-8")
    return RUNTIME_TEMPLATE, RUNTIME_TEMPLATE.read_text(encoding="utf-8")


def runtime_targets(manifest_text: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_targets = False
    for line in manifest_text.splitlines():
        if line.startswith("targets:"):
            in_targets = True
            continue
        if not in_targets:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            if current:
                targets.append(current)
            current = {"id": line.strip().removesuffix(":")}
            continue
        if current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        targets.append(current)
    return targets


def layout_version(root: Path, marker_name: str) -> str:
    marker_path = root / marker_name
    if not marker_path.exists():
        return "missing"
    marker, errors = parse_marker(marker_path)
    if errors:
        return "unreadable"
    value = marker.get("layout_version")
    return str(value) if isinstance(value, str) else "missing"


def config_roots(config_path: Path) -> tuple[Path, Path, str]:
    data = parse_config(config_path)
    core_text = str(data.get("core_root", "")) or str(ROOT)
    vault_text = str(data.get("vault_root", "")) or core_text
    return Path(core_text).expanduser().resolve(), Path(vault_text).expanduser().resolve(), core_text


def stale_references(paths: list[Path], needles: list[str]) -> list[str]:
    refs: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle and needle in text:
                refs.append(f"{path}: contains {needle}")
    return refs


def classify_mode(core_root: Path, vault_root: Path, validation_errors: list[str]) -> str:
    if not core_root.exists():
        return "missing_core"
    if not vault_root.exists():
        return "missing_vault"
    if validation_errors:
        return "unknown"
    if core_root == vault_root:
        return "combined_compatibility"
    return "split"


def required_actions(mode: str, compatibility_errors: list[str]) -> list[str]:
    if mode == "combined_compatibility":
        return [
            "select or initialize a private Vault target",
            "validate selected Core/Vault roots before any apply step",
            "dry-run adapter publishing from the selected Vault",
            "keep runtime installs read-only until split roots are verified",
        ]
    if mode == "split" and not compatibility_errors:
        return [
            "run root validation before publishing",
            "dry-run selected-Vault adapter publishing",
            "dry-run runtime install and review stale path references",
            "apply runtime install only after reviewing destinations",
        ]
    if mode == "missing_core":
        return ["clone or locate the public Core root, then re-run this planner"]
    if mode == "missing_vault":
        return ["clone, sync, or initialize the private Vault root, then re-run this planner"]
    return ["fix marker, root, or runtime ambiguity before any apply step"]


def print_plan(
    config_path: Path,
    core_root: Path,
    vault_root: Path,
    mode: str,
    validation_errors: list[str],
    compatibility_errors: list[str],
    runtime_manifest: Path,
    runtime_manifest_text: str,
    stale_refs: list[str],
) -> int:
    safe_apply_candidate = mode == "split" and not validation_errors and not compatibility_errors and not stale_refs
    print("Agent Foundry deployment migration plan")
    print(f"config_path: {config_path}")
    print(f"mode: {mode}")
    print(f"core_root: {core_root}")
    print(f"vault_root: {vault_root}")
    print(f"core_layout_version: {layout_version(core_root, CORE_LAYOUT_MARKER)}")
    print(f"vault_layout_version: {layout_version(vault_root, VAULT_LAYOUT_MARKER)}")
    print(f"runtime_manifest: {runtime_manifest}")
    print("runtime_targets:")
    for target in runtime_targets(runtime_manifest_text):
        print(
            "- "
            + ", ".join(
                [
                    f"id={yaml_scalar(target.get('id', ''))}",
                    f"status={yaml_scalar(target.get('status', ''))}",
                    f"install_path={yaml_scalar(target.get('install_path', ''))}",
                ]
            )
        )
    print("validation_errors:")
    for error in validation_errors or ["none"]:
        print(f"- {error}")
    print("compatibility_errors:")
    for error in compatibility_errors or ["none"]:
        print(f"- {error}")
    print("stale_path_references:")
    for ref in stale_refs or ["none"]:
        print(f"- {ref}")
    print("required_user_actions:")
    for action in required_actions(mode, compatibility_errors):
        print(f"- {action}")
    print(f"safe_apply_candidate: {'yes' if safe_apply_candidate else 'no'}")
    return 0 if mode in {"combined_compatibility", "split"} and not validation_errors else 1


def plan(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    configured_config_core, configured_config_vault, _ = config_roots(config_path)
    if args.core_root or args.vault_root:
        core_root = Path(args.core_root or ROOT).expanduser().resolve()
        vault_root = Path(args.vault_root or args.core_root or ROOT).expanduser().resolve()
    else:
        core_root = configured_config_core
        vault_root = configured_config_vault
    validation_errors = validate(core_root, vault_root)
    compatibility_errors = check_layout_compatibility(core_root, vault_root) if core_root.exists() and vault_root.exists() else []
    runtime_manifest, runtime_manifest_text = read_runtime_manifest()
    stale_refs: list[str] = []
    if args.core_root or args.vault_root:
        if config_path.exists() and (configured_config_core != core_root or configured_config_vault != vault_root):
            stale_refs.append(f"{config_path}: locator differs from planned roots")
    if core_root != vault_root and configured_config_core == configured_config_vault and configured_config_core != core_root:
        stale_refs.extend(stale_references([runtime_manifest], [str(configured_config_core)]))
    mode = classify_mode(core_root, vault_root, validation_errors)
    return print_plan(
        config_path,
        core_root,
        vault_root,
        mode,
        validation_errors,
        compatibility_errors,
        runtime_manifest,
        runtime_manifest_text,
        stale_refs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan Agent Foundry deployment migration without writing files.")
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--config", default=str(CONFIG_PATH), help="Machine-local Foundry locator.")
    plan_parser.add_argument("--core-root", default="", help="Override Core root for planning.")
    plan_parser.add_argument("--vault-root", default="", help="Override Vault root for planning.")
    args = parser.parse_args()

    if args.command == "plan":
        return plan(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
