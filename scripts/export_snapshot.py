#!/usr/bin/env python3
"""Export an offline Agent Foundry snapshot as tar.gz with a manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import tempfile
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


DEFAULT_INCLUDE = [
    "AGENTS.md",
    "README.md",
    "docs",
    "workflows",
    "schemas",
    "indexes",
    "practices",
    "assets",
    "imports",
    "adapters",
    "templates",
    "usage",
    "runtime",
    "sync/templates",
    "scripts",
]


def should_include(path: Path) -> bool:
    parts = set(path.parts)
    if ".git" in parts:
        return False
    if path.parts[:2] == ("runtime", "local"):
        return False
    if path.parts[:2] == ("sync", "snapshots"):
        return False
    if "__pycache__" in parts:
        return False
    return True


def iter_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path] if should_include(path.relative_to(ROOT)) else []
    files: list[Path] = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            rel = item.relative_to(ROOT)
            if should_include(rel):
                files.append(item)
    return files


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files() -> list[Path]:
    files: list[Path] = []
    for rel in DEFAULT_INCLUDE:
        files.extend(iter_files(ROOT / rel))
    return sorted(set(files))


def build_manifest(files: list[Path], created_at: str, arc_prefix: str) -> dict:
    return {
        "schema_version": 1,
        "created_at": created_at,
        "source_root": str(ROOT),
        "archive_root": arc_prefix,
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in files
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Agent Foundry offline snapshot.")
    parser.add_argument("--out-dir", default=str(ROOT / "sync" / "snapshots"))
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = args.name or f"agent-foundry-snapshot-{stamp}.tar.gz"
    out_path = out_dir / base_name
    arc_prefix = f"agent-foundry-{stamp}"

    files = collect_files()
    manifest = build_manifest(files, created_at, arc_prefix)

    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "snapshot-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        with tarfile.open(out_path, "w:gz") as tar:
            tar.add(manifest_path, arcname=str(Path(arc_prefix) / "sync" / "snapshot-manifest.json"))
            for path in files:
                rel = path.relative_to(ROOT)
                tar.add(path, arcname=str(Path(arc_prefix) / rel))

    archive_hash = file_sha256(out_path)
    result = subprocess.run(
        ["python3", "scripts/sync_state.py", "record-exported", str(out_path)],
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
    print(out_path)
    print(f"archive_sha256: {archive_hash}")
    print(f"files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
