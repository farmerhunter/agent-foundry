#!/usr/bin/env python3
"""Write and verify machine-local selected-output adapter install receipts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = ROOT / "runtime" / "local" / "adapter-install-receipt.yaml"
SKILL_FOLDER_TARGETS = {"codex", "hermes", "trae"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def source_files_for_target(adapter_root: Path, target: str) -> list[tuple[Path, Path]]:
    if target in SKILL_FOLDER_TARGETS:
        src = adapter_root / target / "skills"
        return [(path, path.relative_to(adapter_root)) for path in sorted(src.rglob("*")) if path.is_file()] if src.exists() else []
    if target == "claude-code":
        src_root = adapter_root / "claude-code"
        files: list[tuple[Path, Path]] = []
        claude = src_root / "CLAUDE.md"
        if claude.exists():
            files.append((claude, claude.relative_to(adapter_root)))
        commands = src_root / "commands"
        if commands.exists():
            files.extend((path, path.relative_to(adapter_root)) for path in sorted(commands.rglob("*")) if path.is_file())
        return files
    return []


def destination_for_source(target: str, source_rel: Path, install_path: Path) -> Path | None:
    if target in SKILL_FOLDER_TARGETS:
        prefix = Path(target) / "skills"
        rel = source_rel.relative_to(prefix)
        return install_path / rel
    if target == "claude-code":
        if source_rel == Path("claude-code") / "CLAUDE.md":
            return install_path / "agent-foundry" / "CLAUDE.md"
        prefix = Path("claude-code") / "commands"
        rel = source_rel.relative_to(prefix)
        return install_path / "commands" / "agent-foundry" / rel
    return None


def installed_file_entries(adapter_root: Path, target: str, install_path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for source, source_rel in source_files_for_target(adapter_root, target):
        dest = destination_for_source(target, source_rel, install_path)
        if dest is None or not dest.exists():
            continue
        entries.append(
            {
                "target": target,
                "source": str(source_rel),
                "destination": str(dest.expanduser()),
                "sha256": file_sha256(dest),
            }
        )
    return entries


def write_receipt(
    *,
    core_root: Path,
    vault_root: Path,
    adapter_root: Path,
    installed_targets: dict[str, Path],
    receipt_path: Path = RECEIPT_PATH,
) -> None:
    manifest = adapter_root / "adapter-publish-manifest.yaml"
    files: list[dict[str, str]] = []
    for target, install_path in installed_targets.items():
        files.extend(installed_file_entries(adapter_root, target, install_path.expanduser()))
    payload: dict[str, Any] = {
        "schema_version": 1,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "core_root": str(core_root),
        "core_commit": git_commit(core_root),
        "vault_root": str(vault_root),
        "vault_commit": git_commit(vault_root) if (vault_root / ".git").exists() else "unknown",
        "adapter_root": str(adapter_root),
        "adapter_manifest": str(manifest) if manifest.exists() else "",
        "adapter_manifest_sha256": file_sha256(manifest) if manifest.exists() else "",
        "installed_targets": sorted(installed_targets),
        "installed_files": files,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_receipt(receipt_path: Path = RECEIPT_PATH) -> dict[str, Any] | None:
    if not receipt_path.exists():
        return None
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": f"invalid receipt JSON/YAML subset: {receipt_path}"}
    return data if isinstance(data, dict) else {"error": f"invalid receipt payload: {receipt_path}"}


def receipt_status(receipt: dict[str, Any]) -> tuple[str, list[str]]:
    if "error" in receipt:
        return "selected-output-unknown", [str(receipt["error"])]
    files = receipt.get("installed_files")
    if not isinstance(files, list) or not files:
        return "selected-output-unknown", ["receipt has no installed files"]
    problems: list[str] = []
    manifest_text = str(receipt.get("adapter_manifest", ""))
    manifest_path = Path(manifest_text).expanduser()
    manifest_sha256 = str(receipt.get("adapter_manifest_sha256", ""))
    if manifest_text and manifest_sha256:
        if not manifest_path.exists():
            problems.append(f"missing adapter_manifest {manifest_path}")
        elif file_sha256(manifest_path) != manifest_sha256:
            problems.append(f"changed adapter_manifest {manifest_path}")
    for entry in files:
        if not isinstance(entry, dict):
            problems.append("receipt has invalid installed file entry")
            continue
        dest = Path(str(entry.get("destination", ""))).expanduser()
        expected = str(entry.get("sha256", ""))
        label = f"{entry.get('target', 'unknown')}:{dest}"
        if not dest.exists():
            problems.append(f"missing {label}")
        elif expected and file_sha256(dest) != expected:
            problems.append(f"changed {label}")
    return ("selected-output-drift", problems) if problems else ("selected-output-in-sync", [])


def receipt_target_statuses(receipt: dict[str, Any]) -> dict[str, tuple[str, list[str], int]]:
    if "error" in receipt:
        return {"unknown": ("selected-output-unknown", [str(receipt["error"])], 0)}
    files = receipt.get("installed_files")
    if not isinstance(files, list) or not files:
        return {"unknown": ("selected-output-unknown", ["receipt has no installed files"], 0)}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in files:
        if isinstance(entry, dict):
            grouped.setdefault(str(entry.get("target", "unknown")), []).append(entry)
    statuses: dict[str, tuple[str, list[str], int]] = {}
    for target, entries in grouped.items():
        problems: list[str] = []
        for entry in entries:
            dest = Path(str(entry.get("destination", ""))).expanduser()
            expected = str(entry.get("sha256", ""))
            if not dest.exists():
                problems.append(f"missing {dest}")
            elif expected and file_sha256(dest) != expected:
                problems.append(f"changed {dest}")
        statuses[target] = (
            "selected-output-drift" if problems else "selected-output-in-sync",
            problems,
            len(entries),
        )
    return statuses
