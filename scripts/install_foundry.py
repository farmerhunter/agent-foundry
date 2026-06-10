#!/usr/bin/env python3
"""Install Agent Foundry adapters according to runtime_manifest.yaml."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from adapter_install_receipt import write_receipt
from foundry_config import CONFIG_PATH, parse_config, write_config
from runtime_manifest import parse_targets, read_manifest


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], execute: bool) -> int:
    print("$ " + " ".join(command), flush=True)
    if not execute:
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
        code = run(["python3", "scripts/check_consistency.py"], execute=True)
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
        execute=True,
    )
    if code != 0:
        return code

    if args.apply:
        write_config(CONFIG_PATH, core_root, core_root, vault_root)

    targets = parse_targets(read_manifest())
    selected = [args.target] if args.target else list(targets)
    installed_targets: dict[str, Path] = {}
    for target in selected:
        if target not in targets:
            raise SystemExit(f"Unknown target: {target}")
        config = targets[target]
        status = config.get("status", "")
        if status == "manual":
            print(f"\n## {target}: manual import required", flush=True)
            print(f"Use adapter files under {adapter_root / 'chatgpt'} or the target's documented import path.")
            continue
        if status != "enabled":
            print(f"\n## {target}: skipped status={status}", flush=True)
            continue
        print(f"\n## {target}: {'apply' if args.apply else 'dry-run'}", flush=True)
        code = run(sync_command(target, config.get("install_path", ""), adapter_root, args.apply), execute=True)
        if code != 0:
            return code
        if args.apply:
            installed_targets[target] = Path(config.get("install_path", "")).expanduser()
    if args.apply and installed_targets:
        write_receipt(core_root=core_root, vault_root=vault_root, adapter_root=adapter_root, installed_targets=installed_targets)
        print(f"wrote adapter install receipt: {ROOT / 'runtime' / 'local' / 'adapter-install-receipt.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
