#!/usr/bin/env python3
"""Print local Agent Foundry sync status for offline and remote workflows."""

from __future__ import annotations

import json
import hashlib
import subprocess
import tarfile
from pathlib import Path
from adapter_install_receipt import RECEIPT_PATH, read_receipt, receipt_status, receipt_target_statuses
from foundry_config import CONFIG_PATH, parse_config, validate as validate_config
from operation_context import text_report, build_context


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


def deployed_packs(vault_root: Path) -> list[str]:
    packs: set[str] = set()
    for base in [vault_root / "practices", vault_root / "assets"]:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8")
            if "pack.bootstrap.minimal" in text:
                packs.add("pack.bootstrap.minimal")
    return sorted(packs)


def generated_output_status(adapter_root: Path) -> tuple[str, int]:
    manifest = adapter_root / "adapter-publish-manifest.yaml"
    if not adapter_root.exists():
        return "missing", 0
    files = [path for path in adapter_root.rglob("*") if path.is_file()]
    if not manifest.exists():
        return "missing-manifest", len(files)
    return "ready", len(files)


def receipt_summary(receipt_path: Path) -> list[str]:
    receipt = read_receipt(receipt_path)
    if receipt is None:
        return [f"receipt: missing ({receipt_path})"]
    state, problems = receipt_status(receipt)
    installed = receipt.get("installed_targets", [])
    installed_text = ", ".join(str(item) for item in installed) if isinstance(installed, list) else ""
    lines = [
        f"receipt: {state} ({receipt_path})",
        f"receipt adapter_root: {receipt.get('adapter_root', '')}",
        f"receipt installed_targets: {installed_text}",
    ]
    for target, (target_state, target_problems, checked) in sorted(receipt_target_statuses(receipt).items()):
        lines.append(f"receipt target: {target} {target_state} checked={checked} problems={len(target_problems)}")
    for problem in problems[:10]:
        lines.append(f"receipt detail: {problem}")
    if len(problems) > 10:
        lines.append(f"receipt detail: ... {len(problems) - 10} more")
    return lines


def setup_report(core_root: Path, vault_root: Path, adapter_root: Path, receipt_path: Path = RECEIPT_PATH) -> str:
    manifest_path = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
    targets = parse_runtime_manifest(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    output_state, output_count = generated_output_status(adapter_root)
    packs = deployed_packs(vault_root)
    lines = [
        "Agent Foundry setup/status report",
        text_report(build_context("status", core_root=core_root, vault_root=vault_root, adapter_root=adapter_root)),
        "fresh install summary:",
        f"core_root: {core_root}",
        f"vault_root: {vault_root}",
        f"deployed_pack: {', '.join(packs) if packs else 'none detected'}",
        f"generated_output: {output_state} path={adapter_root} files={output_count}",
        "runtime targets:",
    ]
    if not targets:
        lines.append("- none")
    for name, config in targets.items():
        status = config.get("status", "")
        path = config.get("install_path", "") or "<manual>"
        mode = config.get("ownership_mode", "")
        if status == "manual":
            lines.append(f"- {name}: manual import required path={path} ownership={mode}")
        elif status == "enabled":
            lines.append(f"- {name}: enabled path={path} ownership={mode}")
        else:
            lines.append(f"- {name}: skipped status={status} path={path} ownership={mode}")
    lines.extend(receipt_summary(receipt_path))
    lines.append("first_usable_command: python3 scripts/sync_status.py")
    lines.append("chatgpt_manual_import: explicit; import generated ChatGPT files manually when desired")
    return "\n".join(lines)


def runtime_drift_status(receipt_path: Path = RECEIPT_PATH) -> str:
    manifest_path = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
    if not manifest_path.exists():
        return "no local runtime manifest"
    targets = parse_runtime_manifest(manifest_path.read_text(encoding="utf-8"))
    mode, note = locator_mode()
    lines: list[str] = [
        f"mode: {mode}",
    ]
    if mode == "split":
        receipt = read_receipt(receipt_path)
        if receipt is None:
            lines.append(f"comparison: {note}")
            lines.append("selected-output: selected-output-unknown reason=install receipt missing")
        else:
            lines.append("comparison: selected-output install receipt is authoritative; Core adapters are secondary reference diagnostics")
            state, problems = receipt_status(receipt)
            installed_at = receipt.get("installed_at", "unknown") if isinstance(receipt, dict) else "unknown"
            manifest_sha = receipt.get("adapter_manifest_sha256", "") if isinstance(receipt, dict) else ""
            files = receipt.get("installed_files", []) if isinstance(receipt, dict) else []
            count = len(files) if isinstance(files, list) else 0
            suffix = f" installed_at={installed_at} files={count}"
            if manifest_sha:
                suffix += f" manifest_sha256={str(manifest_sha)[:12]}"
            lines.append(f"selected-output: {state}{suffix}")
            for target, (target_state, target_problems, checked) in sorted(receipt_target_statuses(receipt).items()):
                lines.append(f"{target}: {target_state} checked={checked} missing_changed={len(target_problems)}")
            for problem in problems[:10]:
                lines.append(f"selected-output detail: {problem}")
            if len(problems) > 10:
                lines.append(f"selected-output detail: ... {len(problems) - 10} more")
        lines.append("core-reference:")
    else:
        lines.append(f"comparison: {note}")
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
    import argparse

    parser = argparse.ArgumentParser(description="Print local Agent Foundry sync status for offline and remote workflows.")
    parser.add_argument("--core-root", default="", help="Agent Foundry Core root. Defaults to configured core_root.")
    parser.add_argument("--vault-root", default="", help="Selected Agent Foundry Vault root. Defaults to configured vault_root.")
    parser.add_argument("--adapter-root", default="", help="Generated adapter output root. Defaults to <core-root>/adapters.")
    parser.add_argument("--receipt-path", default="", help="Adapter install receipt path. Defaults to runtime/local receipt.")
    args = parser.parse_args()

    config = parse_config(CONFIG_PATH)
    core_root = Path(args.core_root or str(config.get("core_root", "") or ROOT)).expanduser().resolve()
    vault_root = Path(args.vault_root or str(config.get("vault_root", "") or core_root)).expanduser().resolve()
    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else core_root / "adapters"
    receipt_path = Path(args.receipt_path).expanduser().resolve() if args.receipt_path else RECEIPT_PATH

    print(setup_report(core_root, vault_root, adapter_root, receipt_path))
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
    print(runtime_drift_status(receipt_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
