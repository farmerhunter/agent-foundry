#!/usr/bin/env python3
"""Compare a staged Agent Foundry snapshot with the current working tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_manifest(staged: Path) -> Path:
    matches = list(staged.rglob("sync/snapshot-manifest.json"))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one snapshot manifest, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare staged snapshot files with the working tree.")
    parser.add_argument("staged_dir", help="Directory created by scripts/import_snapshot.py")
    parser.add_argument("--show-unchanged", action="store_true")
    args = parser.parse_args()

    staged = Path(args.staged_dir).expanduser().resolve()
    manifest_path = find_manifest(staged)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_root = manifest["archive_root"]
    staged_root = staged / archive_root

    missing: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    for item in manifest["files"]:
        rel = item["path"]
        current = ROOT / rel
        if not current.exists():
            missing.append(rel)
        elif file_sha256(current) != item["sha256"]:
            changed.append(rel)
        else:
            unchanged.append(rel)

    print(f"staged_root: {staged_root}")
    print(f"manifest: {manifest_path}")
    print(f"missing_in_worktree: {len(missing)}")
    print(f"changed: {len(changed)}")
    print(f"unchanged: {len(unchanged)}")
    for label, values in [("missing", missing), ("changed", changed)]:
        if values:
            print(f"\n# {label}")
            for rel in values:
                print(f"- {rel}")
    if args.show_unchanged and unchanged:
        print("\n# unchanged")
        for rel in unchanged:
            print(f"- {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
