#!/usr/bin/env python3
"""Print local Agent Foundry sync status for offline and remote workflows."""

from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path


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


def main() -> int:
    print(f"root: {ROOT}")
    print(f"git branch: {run_git(['branch', '--show-current'])}")
    print("git remotes:")
    print(run_git(["remote", "-v"]))
    print("git status:")
    print(run_git(["status", "--short"]))
    snapshot = latest_snapshot()
    print(f"latest snapshot: {snapshot_summary(snapshot) if snapshot else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
