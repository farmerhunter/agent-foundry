#!/usr/bin/env python3
"""Print local Agent Foundry sync status for offline and remote workflows."""

from __future__ import annotations

import json
import hashlib
import subprocess
import tarfile
from pathlib import Path
from adapter_install_receipt import RECEIPT_PATH, read_receipt, receipt_status, receipt_target_statuses
from deploy_capability_pack import parse_simple_yaml
from foundry_config import CONFIG_PATH, parse_config, validate as validate_config
from operation_context import text_report, build_context


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GENERATED_ROOT = Path.home() / ".agent-foundry" / "generated" / "agent-foundry-adapters"
SKILL_FOLDER_TARGETS = {"codex", "hermes", "trae"}


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


def run_git_status(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(["git", *args], 127, "", "git unavailable")


def repo_progress_status() -> str:
    branch = run_git(["branch", "--show-current"])
    upstream = run_git_status(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    if upstream.returncode != 0:
        return "\n".join(
            [
                "repo: upstream-unknown",
                f"branch: {branch}",
                "repair: set or fetch the upstream branch before assuming remote Core progress is current",
            ]
        )
    upstream_name = upstream.stdout.strip()
    counts = run_git_status(["rev-list", "--left-right", "--count", f"{upstream_name}...HEAD"])
    if counts.returncode != 0:
        return "\n".join(
            [
                "repo: upstream-unavailable",
                f"branch: {branch}",
                f"upstream: {upstream_name}",
                "repair: fetch remote Core progress before publishing or applying runtime changes",
            ]
        )
    left, right = (counts.stdout.strip().split() + ["0", "0"])[:2]
    behind = int(left)
    ahead = int(right)
    if behind and ahead:
        state = "diverged"
    elif behind:
        state = "behind"
    elif ahead:
        state = "ahead"
    else:
        state = "current"
    lines = [
        f"repo: {state} ahead={ahead} behind={behind}",
        f"branch: {branch}",
        f"upstream: {upstream_name}",
    ]
    if behind:
        lines.append("repair: fetch/pull remote Core progress before publishing generated output or applying runtime changes")
    return "\n".join(lines)


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
    local_manifest = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
    template_manifest = ROOT / "runtime" / "templates" / "runtime_manifest.template.yaml"
    manifest = local_manifest if local_manifest.exists() else template_manifest
    if not manifest.exists():
        return f"runtime manifest missing: {local_manifest}; template missing: {template_manifest}"
    targets = parse_runtime_manifest(manifest.read_text(encoding="utf-8"))
    lines = [
        f"local_manifest: {local_manifest}",
        f"template_manifest: {template_manifest}",
        f"manifest_source: {'local' if local_manifest.exists() else 'template-read-only'}",
    ]
    for name, config in targets.items():
        path = config.get("install_path", "")
        exists = "yes" if path and Path(path).expanduser().exists() else "no"
        lines.append(
            f"{name}: status={config.get('status', '')} path={path or '<manual>'} "
            f"exists={exists} ownership={config.get('ownership_mode', '')}"
        )
    return "\n".join(lines)


def runtime_status() -> str:
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


def parse_deployed_pack_index(path: Path) -> list[dict[str, str]]:
    index = parse_simple_yaml(path.read_text(encoding="utf-8"))
    raw_packs = index.get("deployed_packs", [])
    if not isinstance(raw_packs, list):
        raise ValueError("deployed_packs must be a list")
    packs: list[dict[str, str]] = []
    for raw_pack in raw_packs:
        if not isinstance(raw_pack, dict):
            raise ValueError("deployed_packs entries must be mappings")
        pack: dict[str, str] = {}
        for key, value in raw_pack.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if not isinstance(nested_value, (dict, list)):
                        pack[f"{key}.{nested_key}"] = str(nested_value)
            elif not isinstance(value, list):
                pack[key] = str(value)
        packs.append(pack)
    return packs


def legacy_pack_scan(vault_root: Path) -> list[str]:
    packs: set[str] = set()
    for base in [vault_root / "practices", vault_root / "assets"]:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8")
            if "pack.bootstrap.minimal" in text:
                packs.add("pack.bootstrap.minimal")
    return sorted(packs)


def deployed_packs(vault_root: Path) -> list[str]:
    index = vault_root / "packs" / "deployed-pack-index.yaml"
    legacy_packs = legacy_pack_scan(vault_root)
    if index.exists():
        packs = []
        seen: set[str] = set()
        try:
            parsed_entries = parse_deployed_pack_index(index)
        except ValueError as exc:
            return [f"metadata_parse_error ({exc})"] + legacy_packs
        for entry in parsed_entries:
            pack_id = entry.get("pack_id", "")
            if not pack_id:
                continue
            seen.add(pack_id)
            version = entry.get("version", "")
            status = entry.get("lifecycle_status", "")
            distribution = entry.get("distribution_type", "")
            source = entry.get("source.kind", "")
            suffix = []
            if version:
                suffix.append(f"version={version}")
            if status:
                suffix.append(f"status={status}")
            if distribution:
                suffix.append(f"type={distribution}")
            if source:
                suffix.append(f"source={source}")
            packs.append(f"{pack_id} ({', '.join(suffix)})" if suffix else pack_id)
        for pack_id in legacy_packs:
            if pack_id not in seen:
                packs.append(f"{pack_id} (legacy-detected)")
        return packs
    return legacy_packs


def generated_output_status(adapter_root: Path) -> tuple[str, int]:
    manifest = adapter_root / "adapter-publish-manifest.yaml"
    if not adapter_root.exists():
        return "missing", 0
    files = [path for path in adapter_root.rglob("*") if path.is_file()]
    if not manifest.exists():
        return "missing-manifest", len(files)
    return "ready", len(files)


def index_active_ids(path: Path, list_key: str) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except ValueError:
        return set()
    entries = data.get(list_key, [])
    if not isinstance(entries, list):
        return set()
    ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", ""))
        item_id = str(entry.get("id", ""))
        if item_id and status in {"active", "revised"}:
            ids.add(item_id)
    return ids


def manifest_list_ids(path: Path, list_key: str) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except ValueError:
        return set()
    values = data.get(list_key, [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if not isinstance(value, (dict, list))}


def activation_freshness_lines(vault_root: Path, adapter_root: Path) -> list[str]:
    manifest = adapter_root / "adapter-publish-manifest.yaml"
    active_practices = index_active_ids(vault_root / "indexes" / "practice_index.yaml", "practices")
    active_assets = index_active_ids(vault_root / "indexes" / "asset_index.yaml", "assets")
    generated_practices = manifest_list_ids(manifest, "active_practices")
    generated_assets = manifest_list_ids(manifest, "active_assets")
    missing_practices = sorted(active_practices - generated_practices)
    missing_assets = sorted(active_assets - generated_assets)
    extra_practices = sorted(generated_practices - active_practices)
    extra_assets = sorted(generated_assets - active_assets)
    if not manifest.exists():
        return [
            "activation: generated-output-missing",
            "activation repair: publish selected Vault generated output before runtime install or manual import",
        ]
    if missing_practices or missing_assets or extra_practices or extra_assets:
        lines = [
            "activation: stale-generated-output "
            f"missing_active_practices={len(missing_practices)} missing_active_assets={len(missing_assets)} "
            f"extra_generated_practices={len(extra_practices)} extra_generated_assets={len(extra_assets)}",
        ]
        for item_id in missing_practices[:5]:
            lines.append(f"activation missing practice: {item_id}")
        for item_id in missing_assets[:5]:
            lines.append(f"activation missing asset: {item_id}")
        lines.append("activation repair: publish selected Vault generated output, then dry-run runtime install before apply")
        return lines
    return ["activation: generated-output-current"]


def default_adapter_root(core_root: Path, vault_root: Path, receipt_path: Path) -> Path:
    if core_root != vault_root:
        receipt = read_receipt(receipt_path)
        if isinstance(receipt, dict):
            receipt_root = str(receipt.get("adapter_root", ""))
            if receipt_root:
                return Path(receipt_root).expanduser().resolve()
        return DEFAULT_GENERATED_ROOT.resolve()
    return core_root / "adapters"


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
        if target_state == "selected-output-drift":
            lines.append(
                f"receipt repair: {target} review generated output, run install dry-run, then apply only with runtime-write approval"
            )
            if target == "trae":
                lines.append("receipt repair: trae writes ~/.trae-cn/skills and requires durable human approval before --apply")
    for problem in problems[:10]:
        lines.append(f"receipt detail: {problem}")
    if len(problems) > 10:
        lines.append(f"receipt detail: ... {len(problems) - 10} more")
    return lines


def next_safe_actions(
    core_root: Path,
    vault_root: Path,
    adapter_root: Path,
    receipt_path: Path,
    output_state: str,
) -> list[str]:
    actions: list[str] = ["status-only: no files were written by this report"]
    config_errors = validate_config(CONFIG_PATH) if CONFIG_PATH.exists() else [f"locator missing: {CONFIG_PATH}"]
    if config_errors:
        actions.append("repair locator/root configuration before any publish, install, or pack apply")
    if not core_root.exists():
        actions.append("fix core_root before running Core maintenance commands")
    if not vault_root.exists():
        actions.append("select or initialize a Vault before harvesting, refreshing, or applying packs")
    if output_state != "ready":
        actions.append("regenerate selected Vault adapter output before runtime install or refresh")
    receipt = read_receipt(receipt_path)
    if receipt is None:
        actions.append("run runtime install only after generated output dry-run/review; receipt is currently missing")
    else:
        if isinstance(receipt, dict):
            receipt_state, _ = receipt_status(receipt)
            if receipt_state == "selected-output-drift":
                actions.append("review selected-output drift, regenerate generated output if needed, then dry-run runtime install before apply")
                actions.append("for Trae, do not write ~/.trae-cn/skills unless durable human approval explicitly authorizes that runtime apply")
            elif receipt_state == "selected-output-unknown":
                actions.append("repair or recreate runtime install receipt only through reviewed install apply after generated output is ready")
    actions.append("treat ChatGPT as manual import unless a future managed target is explicitly implemented")
    return actions


def setup_report(core_root: Path, vault_root: Path, adapter_root: Path, receipt_path: Path = RECEIPT_PATH) -> str:
    manifest_path = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
    template_path = ROOT / "runtime" / "templates" / "runtime_manifest.template.yaml"
    if manifest_path.exists():
        targets = parse_runtime_manifest(manifest_path.read_text(encoding="utf-8"))
    elif template_path.exists():
        targets = parse_runtime_manifest(template_path.read_text(encoding="utf-8"))
    else:
        targets = {}
    output_state, output_count = generated_output_status(adapter_root)
    packs = deployed_packs(vault_root)
    lines = [
        "Agent Foundry setup/status report",
        text_report(build_context("status", core_root=core_root, vault_root=vault_root, adapter_root=adapter_root)),
        "fresh install summary:",
        f"core_root: {core_root}",
        f"vault_root: {vault_root}",
        f"deployed_pack: {', '.join(packs) if packs else 'none detected'}",
        "deployed_packs:",
        *(f"- {pack}" for pack in packs),
        *(["- none detected"] if not packs else []),
        "adapter_root_rule: preserve this selected adapter root across publish, selected-output quality, install, and status",
        f"generated_output: {output_state} path={adapter_root} files={output_count}",
        *activation_freshness_lines(vault_root, adapter_root),
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
    lines.append("next_safe_actions:")
    lines.extend(f"- {action}" for action in next_safe_actions(core_root, vault_root, adapter_root, receipt_path, output_state))
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
        if name in SKILL_FOLDER_TARGETS:
            checked, missing, changed = compare_tree(ROOT / "adapters" / name / "skills", dest)
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
    parser.add_argument(
        "--adapter-root",
        default="",
        help="Generated adapter output root. Defaults to receipt/default generated root in split mode, otherwise <core-root>/adapters.",
    )
    parser.add_argument("--receipt-path", default="", help="Adapter install receipt path. Defaults to runtime/local receipt.")
    args = parser.parse_args()

    config = parse_config(CONFIG_PATH)
    core_root = Path(args.core_root or str(config.get("core_root", "") or ROOT)).expanduser().resolve()
    vault_root = Path(args.vault_root or str(config.get("vault_root", "") or core_root)).expanduser().resolve()
    receipt_path = Path(args.receipt_path).expanduser().resolve() if args.receipt_path else RECEIPT_PATH
    adapter_root = (
        Path(args.adapter_root).expanduser().resolve()
        if args.adapter_root
        else default_adapter_root(core_root, vault_root, receipt_path)
    )

    print(setup_report(core_root, vault_root, adapter_root, receipt_path))
    print(f"root: {ROOT}")
    print(f"git branch: {run_git(['branch', '--show-current'])}")
    print("git remotes:")
    print(run_git(["remote", "-v"]))
    print("git status:")
    print(run_git(["status", "--short"]))
    print("repo progress:")
    print(repo_progress_status())
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
