#!/usr/bin/env python3
"""Install Agent Foundry adapters according to runtime_manifest.yaml."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from foundry_config import CONFIG_PATH, parse_config, write_config
from runtime_manifest import parse_targets, read_manifest


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], apply: bool) -> int:
    print("$ " + " ".join(command), flush=True)
    if not apply:
        return 0
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def sync_command(target: str, install_path: str, adapter_root: Path, apply: bool) -> list[str]:
    command = ["python3", "scripts/sync_adapters.py", "--target", target]
    command.append("--apply" if apply else "--dry-run")
    if adapter_root:
        command.extend(["--adapter-root", str(adapter_root)])
    if install_path:
        command.extend(["--dest", install_path])
    return command


def configured_roots(core_root_arg: str, vault_root_arg: str) -> tuple[Path, Path]:
    if core_root_arg or vault_root_arg:
        core_root = Path(core_root_arg or ROOT).expanduser().resolve()
        vault_root = Path(vault_root_arg or core_root).expanduser().resolve()
        return core_root, vault_root
    data = parse_config(CONFIG_PATH)
    core_text = str(data.get("core_root", "")) or str(ROOT)
    vault_text = str(data.get("vault_root", "")) or core_text
    return Path(core_text).expanduser().resolve(), Path(vault_text).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Agent Foundry adapters from runtime manifest.")
    parser.add_argument("--apply", action="store_true", help="Write managed runtime files.")
    parser.add_argument("--target", default="", help="Install only one target from the manifest.")
    parser.add_argument("--skip-check", action="store_true", help="Skip consistency check.")
    parser.add_argument("--core-root", default="", help="Core root to validate and record in the local locator.")
    parser.add_argument("--vault-root", default="", help="Vault root to validate and record in the local locator.")
    parser.add_argument("--adapter-root", default="", help="Adapter output root to install from. Defaults to <core-root>/adapters.")
    args = parser.parse_args()
    core_root, vault_root = configured_roots(args.core_root, args.vault_root)
    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else core_root / "adapters"

    if not args.skip_check:
        code = run(["python3", "scripts/check_consistency.py"], apply=True)
        if code != 0:
            return code
    code = run(
        [
            "python3",
            "scripts/check_foundry_roots.py",
            "--core-root",
            str(core_root),
            "--vault-root",
            str(vault_root),
        ],
        apply=True,
    )
    if code != 0:
        return code

    if args.apply:
        write_config(CONFIG_PATH, core_root, core_root, vault_root)

    targets = parse_targets(read_manifest())
    selected = [args.target] if args.target else list(targets)
    for target in selected:
        if target not in targets:
            raise SystemExit(f"Unknown target: {target}")
        config = targets[target]
        status = config.get("status", "")
        if status == "manual":
            print(f"\n## {target}: manual import required", flush=True)
            print("Use adapter files under adapters/chatgpt/ or the target's documented import path.")
            continue
        if status != "enabled":
            print(f"\n## {target}: skipped status={status}", flush=True)
            continue
        print(f"\n## {target}: {'apply' if args.apply else 'dry-run'}", flush=True)
        code = run(sync_command(target, config.get("install_path", ""), adapter_root, args.apply), apply=args.apply)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
