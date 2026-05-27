#!/usr/bin/env python3
"""Import an Agent Foundry offline snapshot into a staging directory.

The default behavior is intentionally non-destructive: extract into
sync/imported/<snapshot-name>/ and report the manifest. Merge manually after review.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if dest_resolved not in target.parents and target != dest_resolved:
            raise SystemExit(f"Refusing unsafe archive member: {member.name}")
    tar.extractall(dest)


def find_manifest(extract_dir: Path) -> Path:
    matches = list(extract_dir.rglob("sync/snapshot-manifest.json"))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one snapshot manifest, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage an Agent Foundry offline snapshot for review.")
    parser.add_argument("snapshot", help="Path to agent-foundry snapshot .tar.gz")
    parser.add_argument("--out-dir", default=str(ROOT / "sync" / "imported"))
    args = parser.parse_args()

    snapshot = Path(args.snapshot).expanduser().resolve()
    if not snapshot.exists():
        raise SystemExit(f"Snapshot not found: {snapshot}")

    out_root = Path(args.out_dir).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)
    dest = out_root / snapshot.name.removesuffix(".tar.gz")
    if dest.exists():
        raise SystemExit(f"Import staging directory already exists: {dest}")

    with tarfile.open(snapshot, "r:gz") as tar:
        safe_extract(tar, dest)

    manifest_path = find_manifest(dest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"imported: {dest}")
    print(f"created_at: {manifest.get('created_at', '')}")
    print(f"files: {len(manifest.get('files', []))}")
    result = subprocess.run(
        ["python3", "scripts/sync_state.py", "record-imported", str(snapshot)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0 and result.stdout.strip():
        print(result.stdout.strip())
    elif result.returncode != 0:
        print(f"warning: unable to record sync state: {(result.stdout + result.stderr).strip()}")
    print("next: compare staged files with the working tree, then merge intentionally.")
    print(f"next: python3 scripts/compare_snapshot.py {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
