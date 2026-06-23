#!/usr/bin/env python3
"""Report Agent Foundry operation context before writes or installs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from check_foundry_roots import validate
from foundry_config import CONFIG_PATH, ROOT, parse_config
from runtime_manifest import LOCAL_MANIFEST, parse_targets


DEFAULT_GENERATED_ROOT = Path.home() / ".agent-foundry" / "generated" / "agent-foundry-adapters"
CONTEXT_PRODUCT = "product_project_evidence"
CONTEXT_CORE = "foundry_core_maintenance"
CONTEXT_VAULT = "foundry_vault_operation"
CONTEXT_GENERATED = "generated_adapter_output"
CONTEXT_RUNTIME = "runtime_install_state"
CONTEXT_LOCAL = "local_private_state"


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def configured_roots(core_root_arg: str = "", vault_root_arg: str = "") -> tuple[Path, Path]:
    data = parse_config(CONFIG_PATH)
    core_text = core_root_arg or str(data.get("core_root", "") or ROOT)
    vault_text = vault_root_arg or str(data.get("vault_root", "") or "")
    core_root = Path(core_text).expanduser().resolve()
    vault_root = Path(vault_text).expanduser().resolve() if vault_text else core_root
    return core_root, vault_root


def default_adapter_root(core_root: Path, vault_root: Path) -> Path:
    if core_root != vault_root:
        return DEFAULT_GENERATED_ROOT.resolve()
    return core_root / "adapters"


def runtime_paths() -> list[Path]:
    paths: list[Path] = []
    targets = read_runtime_targets()
    for config in targets.values():
        install_path = config.get("install_path", "")
        if install_path:
            paths.append(Path(install_path).expanduser().resolve())
    paths.extend(
        [
            Path.home() / ".codex",
            Path.home() / ".claude",
            Path.home() / ".hermes",
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def nearest_generated_root(cwd: Path, adapter_root: Path | None) -> Path | None:
    if adapter_root and adapter_root.exists() and is_relative_to(cwd, adapter_root):
        return adapter_root.resolve()
    for path in [cwd.resolve(), *cwd.resolve().parents]:
        if (path / "adapter-publish-manifest.yaml").exists():
            return path
    return None


def has_managed_runtime_marker(cwd: Path) -> bool:
    for path in [cwd.resolve(), *cwd.resolve().parents]:
        if (path / ".agent-foundry-managed").exists():
            return True
    return False


def classify_context(cwd: Path, core_root: Path, vault_root: Path, adapter_root: Path | None) -> str:
    cwd = cwd.resolve()
    if nearest_generated_root(cwd, adapter_root):
        return CONTEXT_GENERATED
    if has_managed_runtime_marker(cwd):
        return CONTEXT_RUNTIME
    for runtime_path in runtime_paths():
        if runtime_path.exists() and is_relative_to(cwd, runtime_path):
            return CONTEXT_RUNTIME
    if is_relative_to(cwd, vault_root):
        return CONTEXT_VAULT
    if is_relative_to(cwd, core_root):
        return CONTEXT_CORE
    local_root = Path.home() / ".agent-foundry"
    if local_root.exists() and is_relative_to(cwd, local_root):
        return CONTEXT_LOCAL
    if ".agent-foundry" in cwd.parts:
        return CONTEXT_LOCAL
    return CONTEXT_PRODUCT


def manual_targets() -> list[str]:
    targets = read_runtime_targets()
    return sorted(name for name, config in targets.items() if config.get("status") == "manual")


def read_runtime_targets() -> dict[str, dict[str, str]]:
    if not LOCAL_MANIFEST.exists():
        return {}
    return parse_targets(LOCAL_MANIFEST.read_text(encoding="utf-8").splitlines())


def operation_routes(operation: str, context: str, cwd: Path, core_root: Path, vault_root: Path, adapter_root: Path) -> dict[str, list[str] | str]:
    evidence_root = str(cwd.resolve()) if context == CONTEXT_PRODUCT else ""
    if operation == "harvest":
        return {
            "evidence_root": evidence_root or "explicit evidence source required when not invoked from product project",
            "allowed_reads": [
                "evidence root",
                str(core_root / "workflows"),
                str(core_root / "schemas"),
                str(vault_root / "indexes"),
            ],
            "allowed_writes": [
                str(vault_root / "practices"),
                str(vault_root / "assets"),
                str(vault_root / "indexes"),
                str(vault_root / "usage"),
            ],
            "forbidden_writes": [
                "product project files unless explicitly requested",
                "Core source files unless doing Core maintenance",
                "generated adapter output before approval",
                "runtime files before publish/install",
            ],
        }
    if operation == "publish":
        return {
            "evidence_root": "",
            "allowed_reads": [str(core_root / "adapters"), str(vault_root / "practices"), str(vault_root / "assets")],
            "allowed_writes": [str(adapter_root)],
            "forbidden_writes": [
                str(core_root / "adapters"),
                "runtime install paths",
                "product project files",
                "Vault canonical records",
            ],
        }
    if operation == "import":
        return {
            "evidence_root": "explicit runtime/source paths only",
            "allowed_reads": [
                "explicit runtime/source paths",
                str(core_root / "workflows" / "import-external-skills.md"),
                str(core_root / "workflows" / "discover-assets.md"),
                str(core_root / "schemas" / "asset-candidate.schema.yaml"),
                str(vault_root / "indexes"),
            ],
            "allowed_writes": [str(vault_root / "imports" / "inbox")],
            "forbidden_writes": [
                "runtime source files",
                "runtime adapter install paths",
                str(core_root / "adapters"),
                str(vault_root / "practices"),
                str(vault_root / "assets"),
                str(vault_root / "indexes"),
                "generated adapter output",
            ],
        }
    if operation in {"install", "refresh"}:
        return {
            "evidence_root": "",
            "allowed_reads": [str(core_root), str(vault_root), str(adapter_root), str(core_root / "runtime/local/runtime_manifest.yaml")],
            "allowed_writes": [
                "managed runtime files only",
                str(core_root / "runtime/local/adapter-install-receipt.yaml"),
                str(CONFIG_PATH),
            ],
            "forbidden_writes": [
                "unmanaged runtime files",
                "product project files",
                "Vault canonical records",
                "Core source files other than machine-local runtime receipt",
            ],
        }
    if operation == "status":
        return {
            "evidence_root": "",
            "allowed_reads": [str(core_root), str(vault_root), "runtime manifest", "adapter install receipt"],
            "allowed_writes": [],
            "forbidden_writes": ["all project, Vault, Core, generated, and runtime files"],
        }
    if operation == "core-maintenance":
        return {
            "evidence_root": "",
            "allowed_reads": [str(core_root), str(vault_root)],
            "allowed_writes": [str(core_root)],
            "forbidden_writes": ["Vault canonical records unless explicitly part of a harvest", "runtime files", "product project files"],
        }
    if operation == "vault-maintenance":
        return {
            "evidence_root": "",
            "allowed_reads": [str(core_root), str(vault_root)],
            "allowed_writes": [str(vault_root)],
            "forbidden_writes": ["Core source files", "runtime files", "product project files"],
        }
    return {
        "evidence_root": evidence_root,
        "allowed_reads": [str(core_root), str(vault_root)],
        "allowed_writes": [],
        "forbidden_writes": ["unknown operation: writes require explicit contract"],
    }


def build_context(
    operation: str,
    cwd: Path | None = None,
    core_root: Path | None = None,
    vault_root: Path | None = None,
    adapter_root: Path | None = None,
) -> dict[str, Any]:
    cwd = (cwd or Path.cwd()).expanduser().resolve()
    core_root = (core_root or ROOT).expanduser().resolve()
    vault_root = (vault_root or core_root).expanduser().resolve()
    adapter_root = (adapter_root or default_adapter_root(core_root, vault_root)).expanduser().resolve()
    context = classify_context(cwd, core_root, vault_root, adapter_root)
    root_errors = validate(core_root, vault_root)
    routes = operation_routes(operation, context, cwd, core_root, vault_root, adapter_root)
    warnings: list[str] = []
    if context == CONTEXT_PRODUCT and operation not in {"harvest", "import", "status"}:
        warnings.append("invoked from product project context; writes must go only to the declared Agent Foundry targets")
    if operation == "publish" and adapter_root == (core_root / "adapters").resolve():
        warnings.append("publish output points at Core adapters; apply should refuse Core template overwrite")
    if operation in {"install", "refresh"} and core_root != vault_root and adapter_root == (core_root / "adapters").resolve():
        warnings.append(
            "split-mode install points at Core reference adapters; use the selected generated adapter root from publish output"
        )
    if operation in {"install", "refresh"} and not (adapter_root / "adapter-publish-manifest.yaml").exists():
        warnings.append(
            "adapter_root has no adapter-publish-manifest.yaml; preserve one selected generated adapter root across "
            "publish, selected-output quality check, install dry-run/apply, and sync status"
        )
    return {
        "schema_version": 1,
        "operation": operation,
        "invocation_cwd": str(cwd),
        "work_context": context,
        "evidence_root": routes["evidence_root"],
        "core_root": str(core_root),
        "vault_root": str(vault_root),
        "adapter_root": str(adapter_root),
        "manual_targets": manual_targets(),
        "allowed_reads": routes["allowed_reads"],
        "allowed_writes": routes["allowed_writes"],
        "forbidden_writes": routes["forbidden_writes"],
        "root_validation": "passed" if not root_errors else "failed",
        "root_validation_errors": root_errors,
        "warnings": warnings,
        "safe_to_write": not root_errors,
    }


def text_report(report: dict[str, Any]) -> str:
    lines = [
        "Agent Foundry operation context:",
        f"operation: {report['operation']}",
        f"work_context: {report['work_context']}",
        f"invocation_cwd: {report['invocation_cwd']}",
        f"evidence_root: {report['evidence_root']}",
        f"core_root: {report['core_root']}",
        f"vault_root: {report['vault_root']}",
        f"adapter_root: {report['adapter_root']}",
        f"root_validation: {report['root_validation']}",
    ]
    manual = report.get("manual_targets") or []
    if manual:
        lines.append("manual_targets: " + ", ".join(manual))
    for key in ["allowed_reads", "allowed_writes", "forbidden_writes", "warnings", "root_validation_errors"]:
        values = report.get(key) or []
        lines.append(f"{key}:")
        if not values:
            lines.append("  - none")
        else:
            lines.extend(f"  - {value}" for value in values)
    lines.append(f"safe_to_write: {'yes' if report['safe_to_write'] else 'no'}")
    return "\n".join(lines)


def print_operation_context(
    operation: str,
    cwd: Path | None = None,
    core_root: Path | None = None,
    vault_root: Path | None = None,
    adapter_root: Path | None = None,
) -> dict[str, Any]:
    report = build_context(operation, cwd, core_root, vault_root, adapter_root)
    print(text_report(report), flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Agent Foundry operation context before writes or installs.")
    parser.add_argument(
        "operation",
        choices=["harvest", "import", "publish", "install", "refresh", "status", "core-maintenance", "vault-maintenance"],
        help="Operation type to preflight.",
    )
    parser.add_argument("--cwd", default="", help="Invocation directory. Defaults to current directory.")
    parser.add_argument("--core-root", default="", help="Agent Foundry Core root. Defaults to configured core_root.")
    parser.add_argument("--vault-root", default="", help="Selected Agent Foundry Vault root. Defaults to configured vault_root.")
    parser.add_argument("--adapter-root", default="", help="Generated adapter output root. Defaults to <core-root>/adapters.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    core_root, vault_root = configured_roots(args.core_root, args.vault_root)
    adapter_root = Path(args.adapter_root).expanduser().resolve() if args.adapter_root else default_adapter_root(core_root, vault_root)
    cwd = Path(args.cwd).expanduser().resolve() if args.cwd else Path.cwd()
    report = build_context(args.operation, cwd, core_root, vault_root, adapter_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(text_report(report))
    return 0 if report["root_validation"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
