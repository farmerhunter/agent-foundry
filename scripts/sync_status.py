#!/usr/bin/env python3
"""Print local Agent Foundry sync status for offline and remote workflows."""

from __future__ import annotations

import json
import hashlib
import subprocess
import tarfile
from pathlib import Path
from foundry_config import CONFIG_PATH, parse_config, validate as validate_config


ROOT = Path(__file__).resolve().parents[1]


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return "git unavailable"
    text = result.stdout.strip() or result.stderr.strip()
    return text or "none"


def latest_snapshot() -> Path | None:
    snapshots = sorted((ROOT / "sync" / "snapshots").glob("*.tar.gz"), key=lambda p: p.stat().st_mtime)
    return snapshots[-1] if snapshots else None


def snapshot_summary(snapshot: Path) -> str:
    try:
        with tarfile.open(snapshot, "r:gz") as tar:
            member = next((m for m in tar.getmembers() if m.name.endswith("sync/snapshot-manifest.json")), None)
            if member is None:
                return f"{snapshot} (no manifest)"
            fh = tar.extractfile(member)
            if fh is None:
                return f"{snapshot} (manifest unreadable)"
            manifest = json.loads(fh.read().decode("utf-8"))
            return f"{snapshot} ({manifest.get('created_at', '')}, files={len(manifest.get('files', []))})"
    except (tarfile.TarError, json.JSONDecodeError):
        return f"{snapshot} (invalid snapshot)"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_runtime_manifest(text: str) -> dict[str, dict[str, str]]:
    targets: dict[str, dict[str, str]] = {}
    current: str | None = None
    in_targets = False
    for line in text.splitlines():
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


def runtime_manifest_text() -> str:
    script = ROOT / "scripts" / "runtime_manifest.py"
    result = subprocess.run(
        ["python3", str(script), "status"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip() or result.stderr.strip() or "none"


def runtime_status() -> str:
    if not (ROOT / "scripts" / "runtime_manifest.py").exists():
        return "runtime manifest tooling unavailable"
    return runtime_manifest_text()


def sync_state() -> str:
    script = ROOT / "scripts" / "sync_state.py"
    if not script.exists():
        return "sync state tooling unavailable"
    result = subprocess.run(
        ["python3", str(script), "status"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip() or result.stderr.strip() or "none"


def compare_tree(src: Path, dest: Path) -> tuple[int, int, int]:
    missing = 0
    changed = 0
    checked = 0
    if not src.exists() or not dest.exists():
        return (0, 0, 0)
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        target = dest / rel
        checked += 1
        if not target.exists():
            missing += 1
        elif file_sha256(path) != file_sha256(target):
            changed += 1
    return checked, missing, changed


def locator_mode() -> tuple[str, str]:
    if not CONFIG_PATH.exists():
        return "unknown", f"locator missing: {CONFIG_PATH}"
    errors = validate_config(CONFIG_PATH)
    if errors:
        return "invalid", "locator invalid: " + "; ".join(errors)
    data = parse_config(CONFIG_PATH)
    core_root = Path(str(data.get("core_root", ""))).expanduser().resolve()
    vault_root = Path(str(data.get("vault_root", ""))).expanduser().resolve()
    if core_root == vault_root:
        return "combined_compatibility", "runtime comparison uses tracked Core adapters"
    return (
        "split",
        "selected-Vault generated adapter manifest unavailable; comparing installed runtime against tracked Core adapters as reference only",
    )


def runtime_drift_status() -> str:
    manifest_path = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
    if not manifest_path.exists():
        return "no local runtime manifest"
    targets = parse_runtime_manifest(manifest_path.read_text(encoding="utf-8"))
    mode, note = locator_mode()
    lines: list[str] = [
        f"mode: {mode}",
        f"comparison: {note}",
    ]
    for name, config in targets.items():
        if config.get("status") != "enabled":
            lines.append(f"{name}: skipped status={config.get('status')}")
            continue
        dest = Path(config.get("install_path", "")).expanduser()
        if name == "codex":
            checked, missing, changed = compare_tree(ROOT / "adapters" / "codex" / "skills", dest)
        elif name == "hermes":
            checked, missing, changed = compare_tree(ROOT / "adapters" / "hermes" / "skills", dest)
        elif name == "claude-code":
            managed = dest / "agent-foundry" / "CLAUDE.md"
            commands = dest / "commands" / "agent-foundry"
            checked1, missing1, changed1 = compare_tree(ROOT / "adapters" / "claude-code" / "commands", commands)
            checked = checked1 + 1
            missing = missing1
            changed = changed1
            if not managed.exists():
                missing += 1
            elif file_sha256(ROOT / "adapters" / "claude-code" / "CLAUDE.md") != file_sha256(managed):
                changed += 1
        else:
            lines.append(f"{name}: manual or unsupported drift check")
            continue
        if mode == "split":
            state = "reference-in-sync" if missing == 0 and changed == 0 else "reference-drift"
        else:
            state = "in-sync" if missing == 0 and changed == 0 else "drift"
        lines.append(f"{name}: {state} checked={checked} missing={missing} changed={changed}")
    return "\n".join(lines)


def main() -> int:
    print(f"root: {ROOT}")
    print(f"git branch: {run_git(['branch', '--show-current'])}")
    print("git remotes:")
    print(run_git(["remote", "-v"]))
    print("git status:")
    print(run_git(["status", "--short"]))
    snapshot = latest_snapshot()
    print(f"latest snapshot: {snapshot_summary(snapshot) if snapshot else 'none'}")
    print("sync state:")
    print(sync_state())
    print("runtime manifest:")
    print(runtime_status())
    print("runtime adapter drift:")
    print(runtime_drift_status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
