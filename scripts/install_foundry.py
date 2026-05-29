#!/usr/bin/env python3
"""Install Agent Foundry adapters according to runtime_manifest.yaml."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from runtime_manifest import parse_targets, read_manifest


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], apply: bool) -> int:
    print("$ " + " ".join(command), flush=True)
    if not apply:
        return 0
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def sync_command(target: str, install_path: str, apply: bool) -> list[str]:
    command = ["python3", "scripts/sync_adapters.py", "--target", target]
    command.append("--apply" if apply else "--dry-run")
    if install_path:
        command.extend(["--dest", install_path])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Agent Foundry adapters from runtime manifest.")
    parser.add_argument("--apply", action="store_true", help="Write managed runtime files.")
    parser.add_argument("--target", default="", help="Install only one target from the manifest.")
    parser.add_argument("--skip-check", action="store_true", help="Skip consistency check.")
    args = parser.parse_args()

    if not args.skip_check:
        code = run(["python3", "scripts/check_consistency.py"], apply=True)
        if code != 0:
            return code

    if args.apply:
        code = run(["python3", "scripts/foundry_config.py", "write"], apply=True)
        if code != 0:
            return code

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
        code = run(sync_command(target, config.get("install_path", ""), args.apply), apply=args.apply)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
