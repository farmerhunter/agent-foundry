#!/usr/bin/env python3
"""Manage Agent Foundry runtime deployment manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_MANIFEST = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
TEMPLATE_MANIFEST = ROOT / "runtime" / "templates" / "runtime_manifest.template.yaml"
ENABLED_STATUSES = {"enabled"}


def ensure_local_manifest() -> None:
    if LOCAL_MANIFEST.exists():
        return
    if not TEMPLATE_MANIFEST.exists():
        raise SystemExit(f"Runtime manifest template not found: {TEMPLATE_MANIFEST}")
    LOCAL_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_MANIFEST.write_text(TEMPLATE_MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"initialized local runtime manifest: {LOCAL_MANIFEST}")


def read_manifest() -> list[str]:
    ensure_local_manifest()
    lines = LOCAL_MANIFEST.read_text(encoding="utf-8").splitlines()
    if TEMPLATE_MANIFEST.exists():
        return merge_template_targets(lines, TEMPLATE_MANIFEST.read_text(encoding="utf-8").splitlines())
    return lines


def target_blocks(lines: list[str]) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    current_lines: list[str] = []
    in_targets = False
    for line in lines:
        if line == "targets:":
            in_targets = True
            continue
        if not in_targets:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            if current is not None:
                blocks[current] = current_lines
            current = line.strip().removesuffix(":")
            current_lines = [line]
            continue
        if current is not None:
            current_lines.append(line)
    if current is not None:
        blocks[current] = current_lines
    return blocks


def merge_template_targets(local_lines: list[str], template_lines: list[str]) -> list[str]:
    if "targets:" not in local_lines:
        return local_lines
    local_targets = parse_targets(local_lines)
    additions = [block for name, block in target_blocks(template_lines).items() if name not in local_targets]
    if not additions:
        return local_lines
    merged = list(local_lines)
    if merged and merged[-1].strip():
        merged.append("")
    for block in additions:
        merged.extend(block)
        if merged[-1].strip():
            merged.append("")
    while merged and not merged[-1].strip():
        merged.pop()
    return merged


def write_manifest(lines: list[str]) -> None:
    for i, line in enumerate(lines):
        if line.startswith("updated:"):
            lines[i] = f"updated: {dt.date.today().isoformat()}"
            break
    LOCAL_MANIFEST.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_targets(lines: list[str]) -> dict[str, dict[str, str]]:
    targets: dict[str, dict[str, str]] = {}
    current: str | None = None
    in_targets = False
    for line in lines:
        if line == "targets:":
            in_targets = True
            continue
        if not in_targets:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            current = line.strip().removesuffix(":")
            targets[current] = {}
            continue
        if current and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            targets[current][key] = value.strip().strip('"')
    return targets


def expand(path: str) -> Path | None:
    if not path:
        return None
    return Path(path).expanduser()


def detected(target: dict[str, str]) -> bool:
    path = expand(target.get("install_path", ""))
    return bool(path and path.exists())


def status_lines() -> list[str]:
    targets = parse_targets(read_manifest())
    output = [
        f"local_manifest: {LOCAL_MANIFEST}",
        f"template_manifest: {TEMPLATE_MANIFEST}",
    ]
    for name, config in targets.items():
        path = config.get("install_path", "")
        status = config.get("status", "")
        exists = "yes" if detected(config) else "no"
        output.append(f"{name}: status={status} path={path or '<manual>'} exists={exists} ownership={config.get('ownership_mode', '')}")
    return output


def set_target_status(target: str, status: str) -> None:
    lines = read_manifest()
    in_target = False
    found = False
    for i, line in enumerate(lines):
        if line == f"  {target}:":
            in_target = True
            found = True
            continue
        if in_target and line.startswith("  ") and not line.startswith("    "):
            in_target = False
        if in_target and line.strip().startswith("status:"):
            lines[i] = f"    status: {status}"
            write_manifest(lines)
            return
    if not found:
        raise SystemExit(f"Unknown target: {target}")
    raise SystemExit(f"No status field found for target: {target}")


def set_target_path(target: str, path: str) -> None:
    lines = read_manifest()
    in_target = False
    found = False
    for i, line in enumerate(lines):
        if line == f"  {target}:":
            in_target = True
            found = True
            continue
        if in_target and line.startswith("  ") and not line.startswith("    "):
            in_target = False
        if in_target and line.strip().startswith("install_path:"):
            lines[i] = f"    install_path: {path}"
            write_manifest(lines)
            return
    if not found:
        raise SystemExit(f"Unknown target: {target}")
    raise SystemExit(f"No install_path field found for target: {target}")


def enabled_targets() -> list[str]:
    targets = parse_targets(read_manifest())
    return [name for name, config in targets.items() if config.get("status") in ENABLED_STATUSES]


def plan() -> int:
    targets = parse_targets(read_manifest())
    for name, config in targets.items():
        status = config.get("status", "")
        if status == "enabled":
            command = ["python3", "scripts/sync_adapters.py", "--target", name, "--dry-run"]
            path = config.get("install_path", "")
            if path:
                command.extend(["--dest", path])
            print(f"\n## {name}", flush=True)
            print(" ".join(command), flush=True)
            subprocess.run(command, cwd=ROOT, check=False)
        elif status == "manual":
            print(f"\n## {name}", flush=True)
            print("manual import required; no local runtime sync")
        else:
            print(f"\n## {name}", flush=True)
            print(f"skipped: status={status}")
    return 0


def detect() -> int:
    targets = parse_targets(read_manifest())
    for name, config in targets.items():
        path = expand(config.get("install_path", ""))
        if not path:
            print(f"{name}: manual/no local path")
        elif path.exists():
            print(f"{name}: detected at {path}")
        else:
            print(f"{name}: not found at {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Agent Foundry runtime manifest.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("detect")
    sub.add_parser("plan")
    sub.add_parser("enabled-targets")
    enable = sub.add_parser("enable")
    enable.add_argument("target")
    disable = sub.add_parser("disable")
    disable.add_argument("target")
    configure = sub.add_parser("configure")
    configure.add_argument("target")
    configure.add_argument("--path", required=True)
    args = parser.parse_args()

    if args.command == "init":
        ensure_local_manifest()
    elif args.command == "status":
        print("\n".join(status_lines()))
    elif args.command == "detect":
        return detect()
    elif args.command == "plan":
        return plan()
    elif args.command == "enabled-targets":
        print("\n".join(enabled_targets()))
    elif args.command == "enable":
        set_target_status(args.target, "enabled")
    elif args.command == "disable":
        set_target_status(args.target, "disabled")
    elif args.command == "configure":
        set_target_path(args.target, args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
