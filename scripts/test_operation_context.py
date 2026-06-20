#!/usr/bin/env python3
"""Regression fixtures for operation-context preflight."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import operation_context


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_vault.py"
CONTEXT = ROOT / "scripts" / "operation_context.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
INSTALL = ROOT / "scripts" / "install_foundry.py"
STATUS = ROOT / "scripts" / "sync_status.py"


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def init_blank(vault_root: Path) -> subprocess.CompletedProcess[str]:
    return run([str(INIT), str(vault_root), "--core-root", str(ROOT), "--apply"], ROOT)


def context_json(operation: str, cwd: Path, vault: Path, adapter: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            str(CONTEXT),
            operation,
            "--cwd",
            str(cwd),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault),
            "--adapter-root",
            str(adapter),
            "--json",
        ],
        cwd,
    )


def expect_context(name: str, result: subprocess.CompletedProcess[str], expected: str) -> list[str]:
    if result.returncode != 0:
        return [f"{name}: context command failed\n{result.stdout}{result.stderr}"]
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [f"{name}: invalid json {exc}\n{result.stdout}"]
    errors: list[str] = []
    if data.get("work_context") != expected:
        errors.append(f"{name}: expected {expected}, got {data.get('work_context')}")
    if data.get("core_root") != str(ROOT.resolve()):
        errors.append(f"{name}: wrong core_root {data.get('core_root')}")
    if data.get("root_validation") != "passed":
        errors.append(f"{name}: root validation failed {data.get('root_validation_errors')}")
    return errors


def expect_text(name: str, result: subprocess.CompletedProcess[str], expected: str) -> list[str]:
    output = result.stdout + result.stderr
    if result.returncode == 0 and expected in output:
        print(f"{name}: ok")
        return []
    return [f"{name}: expected pass containing {expected!r}, got {result.returncode}\n{output}"]


def write_locator(home: Path, core: Path, vault: Path) -> dict[str, str]:
    config = home / ".agent-foundry" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "\n".join(
            [
                "schema_version: 1",
                f'repo_root: "{core}"',
                f'core_root: "{core}"',
                f'vault_root: "{vault}"',
                "core_markers:",
                "  - .agent-foundry-core.yaml",
                "  - workflows/harvest-practices.md",
                "  - schemas/practice-entry.schema.yaml",
                "  - scripts/foundry_config.py",
                "vault_markers:",
                "  - .agent-foundry-vault.yaml",
                "  - indexes/practice_index.yaml",
                "  - indexes/asset_index.yaml",
                "  - usage/usage-aggregate.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HOME"] = str(home)
    return env


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-foundry-operation-context-") as tmp:
        base = Path(tmp)
        vault = base / "vault"
        product = base / "product-project"
        generated = base / "generated-adapters"
        runtime = base / "runtime" / "skills" / "agent-collaboration"
        local_private = base / ".agent-foundry" / "local"
        fake_home = base / "home"
        for path in [product, generated, runtime, local_private]:
            path.mkdir(parents=True)
        (product / "README.md").write_text("# Product fixture\n", encoding="utf-8")
        (generated / "adapter-publish-manifest.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        (runtime / ".agent-foundry-managed").write_text("managed by fixture\n", encoding="utf-8")

        init = init_blank(vault)
        errors.extend(expect_text("init-blank-vault", init, "Blank Vault initialized and validated."))

        original_manifest = operation_context.LOCAL_MANIFEST
        missing_manifest = base / "missing-runtime" / "runtime_manifest.yaml"
        operation_context.LOCAL_MANIFEST = missing_manifest
        try:
            report = operation_context.build_context("status", product, ROOT.resolve(), vault.resolve(), generated.resolve())
            if missing_manifest.exists():
                errors.append("missing-runtime-manifest: operation context created a runtime manifest")
            if report.get("manual_targets") != []:
                errors.append(f"missing-runtime-manifest: expected no manual targets, got {report.get('manual_targets')}")
        finally:
            operation_context.LOCAL_MANIFEST = original_manifest

        for name, operation, cwd, expected in [
            ("product-harvest", "harvest", product, "product_project_evidence"),
            ("runtime-import", "import", runtime, "runtime_install_state"),
            ("core-status", "status", ROOT, "foundry_core_maintenance"),
            ("vault-maintenance", "vault-maintenance", vault, "foundry_vault_operation"),
            ("generated-publish", "publish", generated, "generated_adapter_output"),
            ("runtime-install", "install", runtime, "runtime_install_state"),
            ("local-private-status", "status", local_private, "local_private_state"),
        ]:
            errors.extend(expect_context(name, context_json(operation, cwd, vault, generated), expected))

        publish = run(
            [
                str(PUBLISH),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--output-root",
                str(generated),
            ],
            product,
        )
        errors.extend(expect_text("publish-context-banner", publish, "work_context: product_project_evidence"))
        errors.extend(expect_text("publish-context-route", publish, f"allowed_writes:\n  - {generated.resolve()}"))
        errors.extend(expect_text("publish-followup-root", publish, f"--adapter-root {generated.resolve()}"))

        default_generated = base / "default-locator-generated"
        default_env = write_locator(fake_home, ROOT.resolve(), vault.resolve())
        default_publish = run(
            [
                str(PUBLISH),
                "--output-root",
                str(default_generated),
            ],
            product,
            env=default_env,
        )
        errors.extend(expect_text("publish-default-locator-context", default_publish, "work_context: product_project_evidence"))
        errors.extend(expect_text("publish-default-locator-vault", default_publish, f"vault_root: {vault.resolve()}"))

        default_install_root = fake_home / ".agent-foundry" / "generated" / "agent-foundry-adapters"
        (default_install_root / "adapter-publish-manifest.yaml").parent.mkdir(parents=True, exist_ok=True)
        (default_install_root / "adapter-publish-manifest.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        default_install = run(
            [
                str(INSTALL),
                "--skip-check",
                "--target",
                "chatgpt",
            ],
            product,
            env=default_env,
        )
        errors.extend(expect_text("install-default-generated-root", default_install, f"adapter_root: {default_install_root.resolve()}"))

        core_adapter_install = run(
            [
                str(INSTALL),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(ROOT / "adapters"),
                "--skip-check",
                "--target",
                "chatgpt",
            ],
            product,
        )
        output = core_adapter_install.stdout + core_adapter_install.stderr
        if core_adapter_install.returncode == 0 or "Refusing split-mode install from Core reference adapters." not in output:
            errors.append(
                "install-refuses-core-adapters: expected split-mode refusal for Core adapters\n"
                f"{core_adapter_install.returncode}\n{output}"
            )

        install = run(
            [
                str(INSTALL),
                "--core-root",
                str(ROOT),
                "--vault-root",
                str(vault),
                "--adapter-root",
                str(generated),
                "--skip-check",
                "--target",
                "chatgpt",
            ],
            product,
        )
        errors.extend(expect_text("install-context-banner", install, "operation: install"))
        errors.extend(expect_text("install-context-route", install, "managed runtime files only"))

        status = run([str(STATUS)], product)
        errors.extend(expect_text("status-context-banner", status, "Agent Foundry operation context:"))
        errors.extend(expect_text("status-context-readonly", status, "operation: status"))

    if errors:
        print("Operation-context fixture failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Operation-context fixture passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
