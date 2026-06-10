#!/usr/bin/env python3
"""Read-only deployment inspection helpers for AF-4 migration checks."""

from __future__ import annotations

import hashlib
import platform
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from check_foundry_roots import validate as validate_roots
from foundry_config import CONFIG_PATH, parse_config, validate as validate_locator


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CommandResult:
    code: int
    output: str


def run(command: list[str], cwd: Path, timeout: int = 20) -> CommandResult:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError:
        return CommandResult(127, f"command unavailable: {command[0]}")
    except subprocess.TimeoutExpired:
        return CommandResult(124, f"command timed out: {' '.join(command)}")
    text = (result.stdout.strip() or result.stderr.strip() or "none").strip()
    return CommandResult(result.returncode, text)


def short(text: str) -> str:
    return text.replace("\n", " | ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_runtime_manifest(path: Path) -> dict[str, dict[str, str]]:
    targets: dict[str, dict[str, str]] = {}
    if not path.exists():
        return targets
    current = ""
    in_targets = False
    for line in path.read_text(encoding="utf-8").splitlines():
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


def runtime_manifest_path(core_root: Path) -> Path:
    local = core_root / "runtime" / "local" / "runtime_manifest.yaml"
    template = core_root / "runtime" / "templates" / "runtime_manifest.template.yaml"
    return local if local.exists() else template


def machine_lines(alias: str) -> list[str]:
    return [
        f"- alias: {alias}",
        f"- host: {socket.gethostname()}",
        f"- os: {platform.platform()}",
    ]


def git_lines(label: str, path: Path) -> tuple[list[str], list[str]]:
    lines = [f"### {label} git"]
    stops: list[str] = []
    if not path.exists():
        return lines + [f"- path: {path}", "- status: missing"], [f"{label} root missing: {path}"]
    inside = run(["git", "rev-parse", "--is-inside-work-tree"], path)
    if inside.code != 0 or inside.output != "true":
        return lines + [f"- path: {path}", "- status: not a git repo"], [f"{label} root is not a git repo: {path}"]

    branch = run(["git", "branch", "--show-current"], path)
    head = run(["git", "rev-parse", "--short", "HEAD"], path)
    status = run(["git", "status", "--short"], path)
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], path)
    remote = run(["git", "remote", "get-url", "origin"], path)
    reachable = run(["git", "ls-remote", "--exit-code", "origin", "HEAD"], path, timeout=30)

    dirty = bool(status.output != "none")
    lines.extend(
        [
            f"- path: {path}",
            f"- branch: {branch.output if branch.code == 0 else 'unknown'}",
            f"- head: {head.output if head.code == 0 else 'unknown'}",
            f"- upstream: {upstream.output if upstream.code == 0 else 'none'}",
            f"- origin: {remote.output if remote.code == 0 else 'missing'}",
            f"- status: {'dirty' if dirty else 'clean'}",
            f"- remote_reachable: {'yes' if reachable.code == 0 else 'no'}",
        ]
    )
    if dirty:
        lines.append(f"- dirty_files: {short(status.output)}")
        stops.append(f"{label} git state is dirty")
    if branch.code != 0 or head.code != 0:
        stops.append(f"{label} git state is unknown")
    if remote.code != 0:
        stops.append(f"{label} origin remote missing")
    if reachable.code != 0:
        stops.append(f"{label} origin remote unreachable: {short(reachable.output)}")
    return lines, stops


def locator_lines(core_root: Path, vault_root: Path) -> tuple[list[str], list[str]]:
    lines = ["### Locator"]
    stops: list[str] = []
    if not CONFIG_PATH.exists():
        return lines + [f"- config: missing ({CONFIG_PATH})"], [f"locator missing: {CONFIG_PATH}"]
    data = parse_config(CONFIG_PATH)
    config_core = Path(str(data.get("core_root", ""))).expanduser().resolve()
    config_vault = Path(str(data.get("vault_root", ""))).expanduser().resolve()
    errors = validate_locator(CONFIG_PATH)
    lines.extend(
        [
            f"- config: {CONFIG_PATH}",
            f"- core_root: {config_core}",
            f"- vault_root: {config_vault}",
            f"- validation: {'passed' if not errors else 'failed'}",
        ]
    )
    if errors:
        stops.extend(f"locator invalid: {error}" for error in errors)
    if config_core != core_root:
        stops.append(f"locator core_root differs from requested core root: {config_core}")
    if config_vault != vault_root:
        stops.append(f"locator vault_root differs from requested vault root: {config_vault}")
    return lines, stops


def root_validation_lines(core_root: Path, vault_root: Path) -> tuple[list[str], list[str]]:
    errors = validate_roots(core_root, vault_root)
    lines = [
        "### Core/Vault validation",
        f"- core_root: {core_root}",
        f"- vault_root: {vault_root}",
        f"- validation: {'passed' if not errors else 'failed'}",
    ]
    stops = [f"Core/Vault validation failed: {error}" for error in errors]
    return lines, stops


def runtime_lines(core_root: Path) -> tuple[list[str], list[str]]:
    manifest = runtime_manifest_path(core_root)
    targets = parse_runtime_manifest(manifest)
    lines = ["### Runtime"]
    stops: list[str] = []
    if not targets:
        return lines + [f"- manifest: missing or empty ({manifest})"], [f"runtime manifest missing or empty: {manifest}"]
    lines.append(f"- manifest: {manifest}")
    for name, config in targets.items():
        status = config.get("status", "")
        install_path = config.get("install_path", "")
        ownership = config.get("ownership_mode", "")
        expanded = Path(install_path).expanduser() if install_path else None
        exists = bool(expanded and expanded.exists())
        managed = runtime_managed_state(name, expanded, status)
        lines.append(
            f"- {name}: status={status} path={install_path or '<manual>'} exists={'yes' if exists else 'no'} "
            f"ownership={ownership} managed={managed}"
        )
        if status == "enabled":
            if not expanded or not exists:
                stops.append(f"runtime target {name} enabled but install path is missing")
            elif managed != "yes":
                stops.append(f"runtime target {name} is unmanaged or ambiguous: {managed}")
    return lines, stops


def runtime_managed_state(name: str, path: Path | None, status: str) -> str:
    if status == "manual":
        return "manual"
    if not path or not path.exists():
        return "missing"
    if name in {"codex", "hermes"}:
        markers = list(path.glob("*/.agent-foundry-managed"))
        return "yes" if markers else "no-managed-markers"
    if name == "claude-code":
        managed_file = path / "agent-foundry" / "CLAUDE.md"
        user_file = path / "CLAUDE.md"
        if not managed_file.exists():
            return "missing-managed-file"
        if not user_file.exists() or "AGENT-FOUNDRY-START" not in user_file.read_text(encoding="utf-8", errors="ignore"):
            return "missing-managed-block"
        return "yes"
    return "unsupported"


def publish_dry_run_lines(core_root: Path, vault_root: Path) -> tuple[list[str], list[str]]:
    if not core_root.exists():
        return (
            ["### Selected-Vault adapter publish dry-run", f"- skipped: Core root missing ({core_root})"],
            [f"selected-Vault adapter publish dry-run skipped because Core root is missing: {core_root}"],
        )
    if not vault_root.exists():
        return (
            ["### Selected-Vault adapter publish dry-run", f"- skipped: Vault root missing ({vault_root})"],
            [f"selected-Vault adapter publish dry-run skipped because Vault root is missing: {vault_root}"],
        )
    command = [
        "python3",
        "scripts/publish_adapters.py",
        "--core-root",
        str(core_root),
        "--vault-root",
        str(vault_root),
        "--output-root",
        "/tmp/agent-foundry-deployment-check-adapters",
    ]
    result = run(command, core_root, timeout=60)
    lines = ["### Selected-Vault adapter publish dry-run", f"- command: {' '.join(command)}", f"- exit: {result.code}"]
    if result.output:
        lines.append(f"- output: {short(result.output)}")
    stops = [] if result.code == 0 else [f"selected-Vault adapter publish dry-run failed: {short(result.output)}"]
    return lines, stops


def stale_reference_lines(core_root: Path, vault_root: Path) -> tuple[list[str], list[str]]:
    scan_paths = [runtime_manifest_path(core_root)]
    refs: list[str] = []
    needles = [str(core_root)]
    if core_root != vault_root:
        needles.append(str(vault_root))
    for path in scan_paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle and needle in text:
                refs.append(f"{path}: contains {needle}")
    lines = ["### Local path reference scan"]
    if refs:
        lines.extend(f"- {ref}" for ref in refs)
    else:
        lines.append("- none")
    return lines, []


def stop_lines(stops: list[str]) -> list[str]:
    lines = ["### Stop conditions"]
    if stops:
        lines.extend(f"- {stop}" for stop in stops)
    else:
        lines.append("- none")
    return lines


def resolve_roots(core_arg: str, vault_arg: str) -> tuple[Path, Path]:
    core_root = Path(core_arg).expanduser().resolve() if core_arg else ROOT
    if vault_arg:
        vault_root = Path(vault_arg).expanduser().resolve()
    elif CONFIG_PATH.exists():
        data = parse_config(CONFIG_PATH)
        vault_root = Path(str(data.get("vault_root", ""))).expanduser().resolve()
    else:
        vault_root = core_root
    return core_root, vault_root


def report_header(title: str) -> list[str]:
    return [f"## {title}", ""]
