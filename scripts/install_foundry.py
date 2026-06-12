#!/usr/bin/env python3
"""Install Agent Foundry adapters according to runtime_manifest.yaml."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from adapter_install_receipt import write_receipt
from deploy_capability_pack import deploy as deploy_capability_pack, top_level_scalars
from foundry_config import CONFIG_PATH, parse_config, write_config
from init_vault import initialize
from operation_context import print_operation_context
from publish_adapters import publish as publish_adapters
from runtime_manifest import parse_targets, read_manifest
from sync_status import setup_report


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP_PACK = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"
DEFAULT_GENERATED_ROOT = Path.home() / ".agent-foundry" / "generated" / "agent-foundry-adapters"


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


def install(
    *,
    core_root: Path,
    vault_root: Path,
    adapter_root: Path,
    apply: bool,
    target: str = "",
    skip_check: bool = False,
    write_locator: bool = True,
) -> int:
    print_operation_context("install", core_root=core_root, vault_root=vault_root, adapter_root=adapter_root)

    if not skip_check:
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

    if apply and write_locator:
        write_config(CONFIG_PATH, core_root, core_root, vault_root)

    targets = parse_targets(read_manifest())
    selected = [target] if target else list(targets)
    installed_targets: dict[str, Path] = {}
    for selected_target in selected:
        if selected_target not in targets:
            raise SystemExit(f"Unknown target: {selected_target}")
        config = targets[selected_target]
        status = config.get("status", "")
        if status == "manual":
            print(f"\n## {selected_target}: manual import required", flush=True)
            print(f"Use adapter files under {adapter_root / 'chatgpt'} or the target's documented import path.")
            continue
        if status != "enabled":
            print(f"\n## {selected_target}: skipped status={status}", flush=True)
            continue
        print(f"\n## {selected_target}: {'apply' if apply else 'dry-run'}", flush=True)
        code = run(sync_command(selected_target, config.get("install_path", ""), adapter_root, apply), execute=True)
        if code != 0:
            return code
        if apply:
            installed_targets[selected_target] = Path(config.get("install_path", "")).expanduser()
    if apply and installed_targets:
        write_receipt(core_root=core_root, vault_root=vault_root, adapter_root=adapter_root, installed_targets=installed_targets)
        print(f"wrote adapter install receipt: {ROOT / 'runtime' / 'local' / 'adapter-install-receipt.yaml'}")
    return 0


def has_vault_markers(vault_root: Path) -> bool:
    return all(
        (vault_root / marker).exists()
        for marker in [
            ".agent-foundry-vault.yaml",
            "indexes/practice_index.yaml",
            "indexes/asset_index.yaml",
            "usage/usage-aggregate.yaml",
        ]
    )


def pack_label(pack_root: Path) -> str:
    manifest_path = pack_root / "manifest.yaml"
    if not manifest_path.exists():
        return str(pack_root)
    manifest = top_level_scalars(manifest_path.read_text(encoding="utf-8"))
    pack_id = manifest.get("pack_id", str(pack_root))
    version = manifest.get("version", "")
    return f"{pack_id} {version}".strip()


def fresh_install(args: argparse.Namespace) -> int:
    core_root = Path(args.core_root or ROOT).expanduser().resolve()
    if not args.vault_root:
        raise SystemExit("--vault-root is required with --fresh-install")
    vault_root = Path(args.vault_root).expanduser().resolve()
    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else DEFAULT_GENERATED_ROOT
    bootstrap_pack = Path(args.bootstrap_pack).expanduser().resolve()

    print("Agent Foundry fresh install")
    print(f"core_root: {core_root}")
    print(f"vault_root: {vault_root}")
    print(f"bootstrap_pack: {pack_label(bootstrap_pack)}")
    print(f"generated_output: {adapter_root}")
    print(f"runtime_install: {'apply' if args.runtime_apply else 'dry-run'}")

    if not args.apply:
        print("Dry-run only. Re-run with --apply to create/select the Vault, deploy bootstrap, and publish generated output.")
        print(setup_report(core_root, vault_root, adapter_root, adapter_root / "adapter-install-receipt.yaml"))
        return 0

    if has_vault_markers(vault_root):
        print("Selected Vault already has required markers; skipping blank Vault initialization.")
    else:
        initialize(vault_root, apply=True, force=args.force)

    code = deploy_capability_pack(core_root, vault_root, bootstrap_pack, apply=True)
    if code != 0:
        return code

    code = publish_adapters(core_root, vault_root, adapter_root, apply=True)
    if code != 0:
        return code

    if not args.no_write_locator:
        write_config(CONFIG_PATH, core_root, core_root, vault_root)

    code = install(
        core_root=core_root,
        vault_root=vault_root,
        adapter_root=adapter_root,
        apply=args.runtime_apply,
        target=args.target,
        skip_check=args.skip_check,
        write_locator=False,
    )
    if code != 0:
        return code

    receipt_path = ROOT / "runtime" / "local" / "adapter-install-receipt.yaml"
    if not args.runtime_apply:
        receipt_path = adapter_root / "adapter-install-receipt.yaml"
    print(setup_report(core_root, vault_root, adapter_root, receipt_path))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Agent Foundry adapters from runtime manifest.")
    parser.add_argument("--fresh-install", action="store_true", help="Run the Fresh Install setup workflow before runtime install.")
    parser.add_argument("--apply", action="store_true", help="Write managed runtime files, or Fresh Install Vault/generated setup.")
    parser.add_argument("--runtime-apply", action="store_true", help="With --fresh-install, write managed runtime files and receipt.")
    parser.add_argument("--target", default="", help="Install only one target from the manifest.")
    parser.add_argument("--skip-check", action="store_true", help="Skip consistency check.")
    parser.add_argument("--core-root", default="", help="Core root to validate and record in the local locator.")
    parser.add_argument("--vault-root", default="", help="Vault root to validate and record in the local locator.")
    parser.add_argument("--adapter-root", default="", help="Adapter output root to install from. Defaults to <core-root>/adapters.")
    parser.add_argument("--generated-root", dest="adapter_root", default="", help="Fresh Install generated adapter output root.")
    parser.add_argument("--bootstrap-pack", default=str(DEFAULT_BOOTSTRAP_PACK), help="Mandatory bootstrap capability pack root.")
    parser.add_argument("--force", action="store_true", help="Allow blank Vault initialization over existing marker files.")
    parser.add_argument("--no-write-locator", action="store_true", help="With --fresh-install, do not write the machine-local locator.")
    args = parser.parse_args()
    if args.fresh_install:
        return fresh_install(args)

    core_root, vault_root = configured_roots(args.core_root, args.vault_root)
    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else core_root / "adapters"
    return install(
        core_root=core_root,
        vault_root=vault_root,
        adapter_root=adapter_root,
        apply=args.apply,
        target=args.target,
        skip_check=args.skip_check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
