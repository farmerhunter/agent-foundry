#!/usr/bin/env python3
"""First-run command UX fixtures for AF8 capability hardening."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import runtime_manifest


ROOT = Path(__file__).resolve().parents[1]
FOUNDORY_CONFIG = ROOT / "scripts" / "foundry_config.py"
INIT_VAULT = ROOT / "scripts" / "init_vault.py"
INSTALL = ROOT / "scripts" / "install_foundry.py"
PUBLISH = ROOT / "scripts" / "publish_adapters.py"
SYNC_STATUS = ROOT / "scripts" / "sync_status.py"


def run(args: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def assert_contains(output: str, snippets: tuple[str, ...]) -> None:
    for snippet in snippets:
        assert snippet in output, f"missing {snippet!r} in:\n{output}"


def assert_not_exists(paths: tuple[Path, ...]) -> None:
    for path in paths:
        assert not path.exists(), f"unexpected write: {path}"


def first_run_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return env


def assert_locator_command_path(base: Path) -> None:
    home = base / "home"
    config = base / "home" / ".agent-foundry" / "config.yaml"
    vault = base / "vault"
    env = first_run_env(home)
    result = run(
        [
            str(FOUNDORY_CONFIG),
            "write",
            "--path",
            str(config),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault),
        ],
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert_contains(result.stdout, (f"wrote foundry locator: {config}",))

    status = run([str(FOUNDORY_CONFIG), "status", "--path", str(config)], env=env)
    assert status.returncode != 0
    assert_contains(
        status.stdout,
        (
            f"foundry locator: {config}",
            f"core_root: {ROOT}",
            f"vault_root: {vault.resolve()}",
            "validation: failed",
            "vault_root does not exist",
        ),
    )


def assert_vault_init_dry_run_and_apply(base: Path) -> Path:
    vault = base / "vault"
    dry_run = run([str(INIT_VAULT), str(vault), "--core-root", str(ROOT)])
    assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
    assert_contains(dry_run.stdout, ("Dry-run only. Re-run with --apply to create the blank Vault.",))
    assert_not_exists((vault / ".agent-foundry-vault.yaml", vault / "indexes" / "practice_index.yaml"))

    apply = run([str(INIT_VAULT), str(vault), "--core-root", str(ROOT), "--apply"])
    assert apply.returncode == 0, apply.stdout + apply.stderr
    assert_contains(apply.stdout, ("Blank Vault initialized and validated.",))
    assert (vault / ".agent-foundry-vault.yaml").exists()
    assert (vault / "indexes" / "asset_index.yaml").exists()
    return vault


def assert_runtime_manifest_temp_init(base: Path) -> None:
    template = base / "runtime" / "templates" / "runtime_manifest.template.yaml"
    local = base / "runtime" / "local" / "runtime_manifest.yaml"
    write(
        template,
        "\n".join(
            [
                "targets:",
                "  codex:",
                "    status: disabled",
                "    install_path: ~/.codex/skills",
                "    ownership_mode: managed-directories",
                "  chatgpt:",
                "    status: manual",
                '    install_path: ""',
                "    ownership_mode: manual-import",
                "",
            ]
        ),
    )
    original_local = runtime_manifest.LOCAL_MANIFEST
    original_template = runtime_manifest.TEMPLATE_MANIFEST
    repo_local = ROOT / "runtime" / "local" / "runtime_manifest.yaml"
    before = repo_local.read_bytes() if repo_local.exists() else None
    try:
        runtime_manifest.LOCAL_MANIFEST = local
        runtime_manifest.TEMPLATE_MANIFEST = template
        runtime_manifest.ensure_local_manifest()
        lines = "\n".join(runtime_manifest.status_lines())
        assert local.exists()
        assert_contains(lines, ("codex: status=disabled", "chatgpt: status=manual"))
    finally:
        runtime_manifest.LOCAL_MANIFEST = original_local
        runtime_manifest.TEMPLATE_MANIFEST = original_template
    after = repo_local.read_bytes() if repo_local.exists() else None
    assert after == before


def assert_fresh_install_dry_run_is_ordered_status(base: Path, vault: Path) -> None:
    generated = base / "generated"
    bootstrap = ROOT / "fixtures" / "capability-packs" / "bootstrap-minimal"
    result = run(
        [
            str(INSTALL),
            "--fresh-install",
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault),
            "--generated-root",
            str(generated),
            "--bootstrap-pack",
            str(bootstrap),
            "--no-write-locator",
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert_contains(
        result.stdout,
        (
            "Agent Foundry fresh install",
            f"core_root: {ROOT}",
            f"vault_root: {vault.resolve()}",
            "runtime_install: dry-run",
            "Dry-run only. Re-run with --apply to create/select the Vault, deploy bootstrap, and publish generated output.",
            "Agent Foundry setup/status report",
            "generated_output: missing",
            "status-only: no files were written by this report",
            "first_usable_command: python3 scripts/sync_status.py",
            "treat ChatGPT as manual import unless a future managed target is explicitly implemented",
        ),
    )
    assert_not_exists((generated / "adapter-publish-manifest.yaml", generated / "codex"))


def assert_publish_and_status_dry_runs(base: Path, vault: Path) -> None:
    generated = base / "generated-publish"
    publish = run(
        [
            str(PUBLISH),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault),
            "--output-root",
            str(generated),
        ]
    )
    assert publish.returncode == 0, publish.stdout + publish.stderr
    assert_contains(publish.stdout, ("would write:", str(generated / "adapter-publish-manifest.yaml")))
    assert_not_exists((generated / "adapter-publish-manifest.yaml",))

    status = run(
        [
            str(SYNC_STATUS),
            "--core-root",
            str(ROOT),
            "--vault-root",
            str(vault),
            "--adapter-root",
            str(generated),
            "--receipt-path",
            str(generated / "adapter-install-receipt.yaml"),
        ]
    )
    assert status.returncode == 0, status.stdout + status.stderr
    assert_contains(
        status.stdout,
        (
            "Agent Foundry setup/status report",
            "generated_output: missing",
            "receipt: missing",
            "regenerate selected Vault adapter output before runtime install or refresh",
            "run runtime install only after generated output dry-run/review; receipt is currently missing",
        ),
    )


def assert_manual_target_install_guidance(base: Path, vault: Path) -> None:
    generated = base / "manual-generated"
    write(generated / "chatgpt" / "custom-instructions.md", "# Manual import\n")
    write(generated / "chatgpt" / "knowledge" / "commands.md", "# Commands\n")
    result = run(
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
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert_contains(
        result.stdout,
        (
            "Agent Foundry operation context:",
            "operation: install",
            "## chatgpt: manual import required",
            "Use adapter files under",
        ),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-foundry-first-run-ux.") as raw:
        base = Path(raw)
        assert_locator_command_path(base / "locator")
        vault = assert_vault_init_dry_run_and_apply(base / "vault-init")
        assert_runtime_manifest_temp_init(base / "runtime-manifest")
        assert_fresh_install_dry_run_is_ordered_status(base / "fresh-install", vault)
        assert_publish_and_status_dry_runs(base / "publish-status", vault)
        assert_manual_target_install_guidance(base / "manual-target", vault)
    print("First-run UX command audit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
